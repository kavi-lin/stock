#!/usr/bin/env python3
"""test_compose.py — Compose deterministic renderer tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
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
compose_mod = _load("compose")
validate_mod = _load("validate_ic_memo")


def _synthetic_fact_pack():
    trade = json.loads((FIXTURES / "nvda_history_minimal.json").read_text())[0]["trades_this_session"][0]
    lock = build_mod.compute_decision_lock(trade)
    fp = {
        "schema_version": "1.0",
        "composer_version": "V1.0.0",
        "ticker": "NVDA",
        "as_of": "2026-05-27",
        "composed_at": "2026-05-27T10:30:00Z",
        "sources": {
            "profile": {"path": "live:fmp/profile/NVDA", "type": "profile.live"},
            "protocol_history": {"path": "test:fixture#entry[0]", "type": "protocol.history"},
            "earnings_cache": {"path": None, "available": False, "type": "earnings_analyst.cache"},
            "peers": {"path": "test", "count": 0, "type": "peers.shared"},
            "peer_descriptor": {"path": "test", "status": "stub_no_llm", "type": "llm_synth.peer_descriptor"},
        },
        "facts": {
            "sec_1": {
                "ticker": "NVDA", "company_name": "NVIDIA Corporation",
                "current_price": 217.03, "range": "132.92-236.54", "market_cap": 5256562525000,
                "sector": "Technology", "industry": "Semiconductors",
                "final_action": trade.get("final_action"),
                "final_decision": trade.get("final_decision"),
                "verdict_band": (trade.get("fair_value_summary") or {}).get("verdict_band"),
                "weighted_fair_value": (trade.get("fair_value_summary") or {}).get("weighted_fair_value"),
                "fv_vs_current_pct": (trade.get("fair_value_summary") or {}).get("vs_current_pct"),
                "decision_confidence_pct": trade.get("decision_confidence_pct"),
                "position_size_pct": trade.get("position_size_pct"),
                "entry_aggressive": trade.get("entry_aggressive"),
                "entry_conservative": trade.get("entry_conservative"),
                "stop_loss": trade.get("stop_loss"),
                "take_profit": trade.get("take_profit"),
                "risk_reward_ratio": trade.get("risk_reward_ratio"),
                "time_horizon": trade.get("time_horizon"),
                "fragility_label": trade.get("fragility_label"),
            },
            "sec_2": {"description": "test company", "ceo": "Test CEO"},
            "sec_3": {"_stub": True},
            "sec_4": {
                "moat_level": "WIDE", "peers": ["AMD", "INTC"],
                "peer_descriptor": {"status": "stub_no_llm", "peers": {}},
            },
            "sec_5": {"_stub": True},
            "sec_6": {"_stub": True},
            "sec_7": {"_stub": True},
            "sec_8": {"fair_value_summary": trade.get("fair_value_summary") or {}, "pt_news": []},
            "sec_9": {"key_risks": trade.get("key_risks") or [], "near_term_catalysts": []},
            "sec_10": {"scenario_odds": trade.get("scenario_odds") or {},
                        "red_team_counter_thesis": "", "red_team_kill_conditions": []},
            "sec_11": {
                "final_action": trade.get("final_action"),
                "final_decision": trade.get("final_decision"),
                "position_size_pct": trade.get("position_size_pct"),
                "watch_conditions": trade.get("watch_conditions") or {},
                "entry_aggressive": trade.get("entry_aggressive"),
                "entry_conservative": trade.get("entry_conservative"),
                "stop_loss": trade.get("stop_loss"),
                "take_profit": trade.get("take_profit"),
            },
            "sec_12": {
                "lane_scores": trade.get("lane_scores") or {},
                "decision_confidence_pct": trade.get("decision_confidence_pct"),
                "provenance": {},
                "degraded_sections": [],
            },
        },
        "degraded_sections": [],
        "_protocol_decision_lock": lock,
    }
    fp["fact_pack_hash"] = validate_mod.compute_fact_pack_hash(fp)
    return fp


def test_compose_produces_all_12_sections():
    fp = _synthetic_fact_pack()
    md = compose_mod.compose(fp)
    for i in range(1, 13):
        assert f"§{i}" in md, f"missing §{i} in composed MD"


def test_compose_is_deterministic():
    fp = _synthetic_fact_pack()
    a = compose_mod.compose(fp)
    b = compose_mod.compose(fp)
    assert hashlib.sha256(a.encode()).hexdigest() == hashlib.sha256(b.encode()).hexdigest()


def test_compose_includes_provenance_comments():
    fp = _synthetic_fact_pack()
    md = compose_mod.compose(fp)
    src_count = md.count("<!-- src:")
    assert src_count >= 10, f"expected >=10 provenance tags, got {src_count}"


def test_compose_llm_polish_raises():
    fp = _synthetic_fact_pack()
    with pytest.raises(NotImplementedError):
        compose_mod.compose(fp, llm_polish=True)


def test_compose_rejects_wrong_schema_version():
    fp = _synthetic_fact_pack()
    fp["schema_version"] = "0.9"
    with pytest.raises(ValueError):
        compose_mod.compose(fp)


def test_compose_sec_11_contains_final_action():
    fp = _synthetic_fact_pack()
    md = compose_mod.compose(fp)
    fa = fp["facts"]["sec_11"]["final_action"]
    sec_11_block = md[md.find("## §11"):md.find("## §12")]
    assert fa in sec_11_block, f"final_action '{fa}' not found verbatim in §11 block"


def test_compose_stub_sections_render_placeholder():
    fp = _synthetic_fact_pack()
    md = compose_mod.compose(fp)
    for sec_idx in (3, 5, 6, 7):
        sec_header = f"## §{sec_idx}"
        assert sec_header in md
        idx = md.find(sec_header)
        # Stub should mention "資料待補"
        body = md[idx:idx + 500]
        assert "資料待補" in body, f"§{sec_idx} stub body should contain '資料待補'"


def test_compose_provenance_roster_table_present():
    fp = _synthetic_fact_pack()
    md = compose_mod.compose(fp)
    assert "Provenance Roster" in md


def test_compose_footer_includes_fact_pack_hash():
    fp = _synthetic_fact_pack()
    md = compose_mod.compose(fp)
    hsh = fp["fact_pack_hash"][:16]
    assert hsh in md


def test_fmt_price_range_supports_list_dict_scalar_and_null():
    assert compose_mod.fmt_price_range(["668", "692"]) == "$668.00 - $692.00"
    assert compose_mod.fmt_price_range({"low": 620, "high": 650}) == "$620.00 - $650.00"
    assert compose_mod.fmt_price_range(721.62) == "$721.62"
    assert compose_mod.fmt_price_range(None) == "—"


def test_compose_header_renders_dual_price_basis():
    fp = _synthetic_fact_pack()
    fp["facts"]["sec_1"]["analysis_price"] = 721.62
    fp["facts"]["sec_1"]["live_spot"] = 895.88
    fp["facts"]["sec_1"]["fv_vs_analysis_pct"] = -42.04
    fp["facts"]["sec_1"]["fv_vs_live_pct"] = -53.31
    md = compose_mod.compose(fp)
    assert "Live Spot" in md
    assert "Analysis Price" in md
    assert "vs analysis" in md
    assert "vs live" in md


def test_compose_entry_ranges_are_rendered_in_sec1_and_sec11():
    fp = _synthetic_fact_pack()
    fp["facts"]["sec_1"]["entry_aggressive"] = ["668", "692"]
    fp["facts"]["sec_1"]["entry_conservative"] = ["620", "650"]
    fp["facts"]["sec_11"]["entry_aggressive"] = ["668", "692"]
    fp["facts"]["sec_11"]["entry_conservative"] = ["620", "650"]
    md = compose_mod.compose(fp)
    assert "$668.00 - $692.00 / $620.00 - $650.00" in md
    assert "Entry (aggressive): $668.00 - $692.00" in md


def test_compose_splits_segment_discontinuity():
    fp = _synthetic_fact_pack()
    fp["facts"]["sec_3"] = {
        "product_fy": [
            {"date": "2025-08-28", "fiscal_year": 2025, "products": {"DRAM Products": 28, "NAND Products": 8}},
            {"date": "2024-08-29", "fiscal_year": 2024, "products": {"CNBU": 9, "MBU": 6, "EBU": 4, "SBU": 4}},
        ],
        "geographic_fy": [],
        "business_mix_overlay": {},
    }
    md = compose_mod.compose(fp)
    assert "Current Structure" in md
    assert "Legacy Segments" in md
    assert "Segment presentation changed" in md


def test_compose_structural_shift_narrative_not_raw_json():
    fp = _synthetic_fact_pack()
    fp["facts"]["sec_7"] = {
        "annual_growth": [],
        "annual_estimates": [{"date": "2030-08-28", "revenue_avg": 278062000000, "eps_avg": 77.08}],
        "transition_signature": None,
        "structural_shift": {
            "tier": "CONFIRMED",
            "signals": {"eps_qoq_jump": True, "gm_breakout": True, "rev_accel": True},
            "metrics": {"gm_z_score": 4.18, "eps_qoq": 1.6261},
        },
    }
    md = compose_mod.compose(fp)
    assert "tier=CONFIRMED" in md
    assert "gm_z=4.18" in md
    assert '{"tier"' not in md
    assert "$278.06B" in md
    assert "77.08" in md


def test_compose_peer_roster_renders_name_and_role():
    fp = _synthetic_fact_pack()
    fp["facts"]["sec_4"]["peers"] = [
        {"ticker": "WDC", "name": "Western Digital", "role": "NAND / storage competitor"},
        {"ticker": None, "name": "SK Hynix", "role": "DRAM / HBM competitor"},
    ]
    md = compose_mod.compose(fp)
    assert "| Ticker | Name | Role |" in md
    assert "Western Digital" in md
    assert "SK Hynix" in md


def test_compose_sec10_has_no_dead_consensus_headers():
    fp = _synthetic_fact_pack()
    md = compose_mod.compose(fp)
    assert "Consensus View" not in md
    assert "Differentiated View" not in md
