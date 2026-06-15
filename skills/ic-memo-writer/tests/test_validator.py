#!/usr/bin/env python3
"""test_validator.py — Validator integrity + 11-field decision-lock breach tests.

Each LOCK_FIELDS entry has a sub-test that mutates that single field in the
fact_pack.payload and asserts validator returns rc=1 fatal with code F-1.1
(hash self-inconsistent) OR F-1.2 (history mismatch when --no-history-check off).
We use --no-history-check style here (history check disabled via fixture).
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = ROOT / "skills" / "ic-memo-writer"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build_mod = _load("build_fact_pack")
validate_mod = _load("validate_ic_memo")
compose_mod = _load("compose")


# -------- helpers --------

def _load_fixture_trade() -> dict:
    hist_path = FIXTURES / "nvda_history_minimal.json"
    h = json.loads(hist_path.read_text())
    return h[0]["trades_this_session"][0]


def _synthetic_fact_pack(trade: dict, *, ticker: str = "NVDA") -> dict:
    """Build a minimal fact_pack with valid hash for given trade."""
    lock = build_mod.compute_decision_lock(trade)
    fp = {
        "schema_version": "1.0",
        "composer_version": "V1.0.0",
        "ticker": ticker,
        "as_of": "2026-05-27",
        "composed_at": "2026-05-27T10:30:00Z",
        "sources": {
            "profile": {"path": f"live:fmp/profile/{ticker}", "type": "profile.live"},
            "protocol_history": {"path": "test:fixture#entry[0]", "type": "protocol.history"},
            "earnings_cache": {"path": None, "available": False, "type": "earnings_analyst.cache"},
            "peers": {"path": "test", "count": 0, "type": "peers.shared"},
            "peer_descriptor": {"path": "test", "status": "stub_no_llm", "type": "llm_synth.peer_descriptor"},
        },
        "facts": {
            "sec_1": {
                "ticker": ticker, "final_action": trade.get("final_action"),
                "final_decision": trade.get("final_decision"),
                "weighted_fair_value": (trade.get("fair_value_summary") or {}).get("weighted_fair_value"),
            },
            "sec_2": {"description": "test"},
            "sec_3": {"_stub": True},
            "sec_4": {"peers": [], "peer_descriptor": {"status": "stub_no_llm"}},
            "sec_5": {"_stub": True},
            "sec_6": {"_stub": True},
            "sec_7": {"_stub": True},
            "sec_8": {"fair_value_summary": trade.get("fair_value_summary") or {}},
            "sec_9": {"key_risks": trade.get("key_risks") or []},
            "sec_10": {"scenario_odds": trade.get("scenario_odds") or {}},
            "sec_11": {
                "final_action": trade.get("final_action"),
                "final_decision": trade.get("final_decision"),
                "position_size_pct": trade.get("position_size_pct"),
                "watch_conditions": trade.get("watch_conditions") or {},
            },
            "sec_12": {"lane_scores": trade.get("lane_scores") or {}},
        },
        "degraded_sections": [],
        "_protocol_decision_lock": lock,
    }
    fp["fact_pack_hash"] = validate_mod.compute_fact_pack_hash(fp)
    return fp


# -------- baseline --------

def test_baseline_unmodified_passes():
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    findings = validate_mod.validate_fact_pack(fp, check_history=False)
    fatals = [f for f in findings if f.severity == "fatal"]
    assert fatals == [], f"baseline should have no fatals, got: {fatals}"


def test_fact_pack_hash_self_consistent():
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    recomputed = validate_mod.compute_fact_pack_hash(fp)
    assert recomputed == fp["fact_pack_hash"]


def test_decision_lock_determinism_repeated():
    trade = _load_fixture_trade()
    a = build_mod.compute_decision_lock(trade)
    b = build_mod.compute_decision_lock(copy.deepcopy(trade))
    assert a["hash"] == b["hash"]


# -------- 11-field hash breach sub-cases --------

LOCK_FIELDS = build_mod.LOCK_FIELDS


@pytest.mark.parametrize("field_name", LOCK_FIELDS)
def test_breach_each_lock_field(field_name):
    """Mutating ANY of the 11 lock fields in payload must trigger F-1.1 fatal."""
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)

    payload = fp["_protocol_decision_lock"]["payload"]
    original = payload.get(field_name)

    # Apply a type-aware mutation
    if isinstance(original, (int, float)):
        payload[field_name] = (original or 0) + 99.99
    elif isinstance(original, str):
        payload[field_name] = (original or "") + " TAMPERED"
    elif isinstance(original, list):
        payload[field_name] = (original or []) + ["TAMPERED"]
    elif isinstance(original, dict):
        payload[field_name] = {**(original or {}), "_tampered": True}
    else:
        payload[field_name] = "INJECTED"

    findings = validate_mod.validate_fact_pack(fp, check_history=False)
    codes = {f.code for f in findings if f.severity == "fatal"}
    assert "F-1.1" in codes, (
        f"breaching field '{field_name}' should trigger F-1.1; got codes={codes}"
    )


def test_fact_pack_hash_tamper():
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    fp["fact_pack_hash"] = "0" * 64
    findings = validate_mod.validate_fact_pack(fp, check_history=False)
    codes = {f.code for f in findings if f.severity == "fatal"}
    assert "F-1.3" in codes


# -------- sec_11 verbatim breach --------

def test_sec_11_verbatim_mismatch_triggers_fatal():
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    # Mutate sec_11.final_action AFTER lock is sealed
    fp["facts"]["sec_11"]["final_action"] = "BUY"  # change
    findings = validate_mod.validate_fact_pack(fp, check_history=False)
    codes = {f.code for f in findings if f.severity == "fatal"}
    assert "F-2" in codes, f"expected F-2; got {codes}"


# -------- MD-level checks --------

def test_md_missing_section_11_is_fatal():
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    md = compose_mod.compose(fp)
    # Strip §11 entirely
    md_no_11 = md.replace("§11", "§XX")
    findings = validate_mod.validate_markdown(md_no_11, fp)
    fatals = [f for f in findings if f.severity == "fatal"]
    assert any(f.code in ("F-3",) for f in fatals)


def test_md_missing_other_sections_is_degraded():
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    md = compose_mod.compose(fp)
    md_no_3 = md.replace("§3", "§XX")
    findings = validate_mod.validate_markdown(md_no_3, fp)
    # missing only sec_3, sec_11 still there → should be degraded not fatal
    fatals = [f for f in findings if f.severity == "fatal"]
    assert not fatals or all(f.code != "F-3" for f in fatals)


def test_md_forbidden_phrase_triggers_fatal():
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    md = compose_mod.compose(fp)
    md_polluted = md + "\n\n_assistant 重新評估 score 為 +5._\n"
    findings = validate_mod.validate_markdown(md_polluted, fp)
    fatals = [f for f in findings if f.severity == "fatal"]
    assert any(f.code == "F-4" for f in fatals)


def test_md_weighted_fv_mismatch_triggers_fatal():
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    md = compose_mod.compose(fp)
    # Replace one of the Weighted FV numbers with a wildly different value
    import re
    md_bad = re.sub(r"Weighted FV.*?\$[\d,\.]+", "Weighted FV**: $99999.99", md, count=1)
    findings = validate_mod.validate_markdown(md_bad, fp)
    fatals = [f for f in findings if f.severity == "fatal"]
    assert any(f.code == "F-5" for f in fatals)


def test_md_provenance_roster_missing_degraded():
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    md = compose_mod.compose(fp)
    md_no_roster = md.replace("Provenance Roster", "—")
    findings = validate_mod.validate_markdown(md_no_roster, fp)
    codes = [f.code for f in findings]
    assert "D-5" in codes


def test_rc_pass_on_clean_synthetic_md():
    """Build minimal MD with everything in place — rc must be 2 (peer stub) not 1."""
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    md = compose_mod.compose(fp)
    findings = validate_mod.validate_fact_pack(fp, check_history=False) + validate_mod.validate_markdown(md, fp)
    rc = validate_mod.determine_rc(findings)
    assert rc in (0, 2), f"expected rc=0 or 2 on clean synthetic, got rc={rc}: {findings}"


def test_history_check_off_does_not_fail_without_history():
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    findings = validate_mod.validate_fact_pack(fp, check_history=False)
    fatals = [f for f in findings if f.severity == "fatal"]
    assert not fatals


# -------- rc tier ladder --------

def test_rc_ladder():
    assert validate_mod.determine_rc([]) == 0
    assert validate_mod.determine_rc(
        [validate_mod.Finding("degraded", "D-1", "x")]
    ) == 2
    assert validate_mod.determine_rc(
        [validate_mod.Finding("fatal", "F-1.1", "x"),
         validate_mod.Finding("degraded", "D-1", "x")]
    ) == 1


def test_md_dual_price_basis_missing_is_fatal():
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    fp["facts"]["sec_1"]["analysis_price"] = 721.62
    fp["facts"]["sec_1"]["live_spot"] = 895.88
    md = compose_mod.compose(fp)
    md_bad = md.replace("Analysis Price", "Protocol Price")
    findings = validate_mod.validate_markdown(md_bad, fp)
    assert any(f.code == "F-7" for f in findings if f.severity == "fatal")


def test_md_entry_range_regression_is_fatal():
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    fp["facts"]["sec_1"]["entry_aggressive"] = ["668", "692"]
    fp["facts"]["sec_1"]["entry_conservative"] = ["620", "650"]
    fp["facts"]["sec_11"]["entry_aggressive"] = ["668", "692"]
    fp["facts"]["sec_11"]["entry_conservative"] = ["620", "650"]
    md = compose_mod.compose(fp)
    md_bad = md.replace("Entry (aggressive): $668.00 - $692.00", "Entry (aggressive): —")
    findings = validate_mod.validate_markdown(md_bad, fp)
    assert any(f.code == "F-8" for f in findings if f.severity == "fatal")


def test_md_entry_range_sec1_finding_not_duplicated():
    """F-8 §1 check must fire once even when both entry keys are non-null."""
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    fp["facts"]["sec_1"]["entry_aggressive"] = ["668", "692"]
    fp["facts"]["sec_1"]["entry_conservative"] = ["620", "650"]
    fp["facts"]["sec_11"]["entry_aggressive"] = ["668", "692"]
    fp["facts"]["sec_11"]["entry_conservative"] = ["620", "650"]
    md = compose_mod.compose(fp)
    # Break only §1 row to —/— so both per-key loop iterations would trigger old code
    md_bad = re.sub(
        r"Entry \(aggr / cons\) \| [^\|]+ \|",
        "Entry (aggr / cons) | — / — |",
        md,
        count=1,
    )
    findings = validate_mod.validate_markdown(md_bad, fp)
    sec_1_f8 = [
        f for f in findings
        if f.code == "F-8" and "§1 renders entry ranges" in f.msg
    ]
    assert len(sec_1_f8) == 1, (
        f"§1 F-8 should fire exactly once, got {len(sec_1_f8)}: {sec_1_f8}"
    )


def test_md_raw_structural_shift_json_is_degraded():
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    md = compose_mod.compose(fp)
    md = md.replace(
        "## §7 盈利能力與 2-3 年模型",
        '## §7 盈利能力與 2-3 年模型\n\n- **Structural shift**: {"tier": "CONFIRMED"}',
        1,
    )
    findings = validate_mod.validate_markdown(md, fp)
    assert any(f.code == "D-6" for f in findings if f.severity == "degraded")


def test_md_dead_consensus_headers_are_degraded():
    trade = _load_fixture_trade()
    fp = _synthetic_fact_pack(trade)
    md = compose_mod.compose(fp)
    md = md.replace("## §10 Bull / Bear / Base case", "## §10 Bull / Bear / Base case\n\n### Consensus View", 1)
    findings = validate_mod.validate_markdown(md, fp)
    assert any(f.code == "D-7" for f in findings if f.severity == "degraded")
