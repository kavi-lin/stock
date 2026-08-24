#!/usr/bin/env python3
"""test_session_export_schema.py — V4.81.0 schema-version gate contract.

What this locks down, in order of how easily it rots:

1. **The doc is the fixture.** Every case is built from the `FULL EXAMPLE` block in
   `phase5_export_schema.md`, so an example that drifts out of schema compliance turns
   this test red instead of silently teaching the next Phase 5 export a broken shape.
   (It has drifted before: through v4.80.1 the header said V5.0 while the JSON stamped
   `V4.8` and carried `valuation_lane` — copying it verbatim tripped the §2b guard.)

2. **The version gate cuts both ways.** A `V5.1` entry missing either half of the engine
   block fails; the same entry stamped `V5.0` and dated before the cutover passes. That
   asymmetry is the whole point of keying on schema version rather than `export_date` —
   backfilling an old analysis must not be held to today's bar.

3. **The bypasses stay shut.** Three of them: stamp an old version to dodge the version
   gate (date backstop), stamp `V5.0` while carrying `decision_engine_version` (§2c),
   stamp `V4.8` while carrying V5.0-only fields (§2b).

4. **§13 catches lies, not just typos.** The tamper battery mutates a valid chain one
   field at a time — including the *labels* (`cascade_rule_applied`, polarization) and
   not only the arithmetic, since a mislabelled chain re-derives perfectly.

Usage:  python3 investment/scripts/test_session_export_schema.py
        rc=0 → contract holds;  rc=1 → see the failure list on stdout
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apply_det_shadow import build_lane_contract  # noqa: E402
from decision_engine import SPECULATIVE_CONFIDENCE_CAP, run_phase3  # noqa: E402
from compute_price_framework import compute_forward_validation  # noqa: E402
import append_session_export  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCHEMA_MD = os.path.join(ROOT, "investment/phase5_export_schema.md")
VALIDATOR = os.path.join(ROOT, "investment/scripts/validate_session_export.py")

FAILS: list[str] = []

# The FULL EXAMPLE is what the PM writes; `det_shadow` is appended afterwards by
# apply_det_shadow.py (the doc marks it "post-processor 寫入，LLM 不寫"). Inject a block
# consistent with the example's lane scores so the fixture represents a post-processed
# entry — otherwise every case would fail on "det_shadow missing" instead of on the
# thing it is testing.
DET_SHADOW = {
    "version": "V3.45.4",
    "signal_polarization": "ALIGNED",
    "polarization_detail": {"label": "ALIGNED", "range": 3.0, "max": 4.0, "min": 1.0,
                            "pos_strong": 5, "neg_strong": 0, "missing_lanes": []},
    "valuation_score_det": 1.0,
    "val_agreement": "AGREE",
    "valuation_source": "valuation_pack",
    "red_team_verdict_det": "STRONG_COUNTER",
    "red_team_agreement": "AGREE",
    "red_team_basis": "unclassified",
    "news_pt_leakage": False,
}


def extract_full_example() -> dict:
    text = open(SCHEMA_MD, encoding="utf-8").read()
    start = text.index("## FULL EXAMPLE")
    fence = text.index("```json", start) + len("```json")
    end = text.index("```", fence)
    entry = json.loads(text[fence:end])
    entry["ticker"] = "FIXTURE_MU"
    trade = entry["trades_this_session"][0]
    trade["ticker"] = "FIXTURE_MU"
    trade.setdefault("technical_lane", {})["rubric_override_reason"] = (
        "historical example replay / stage transition"
    )
    trade.setdefault("det_shadow", copy.deepcopy(DET_SHADOW))
    # C1 (V5.3) — same story as det_shadow, one step later in the same post-process.
    # Built by the **real** producer rather than a literal, so a contract shape change
    # cannot pass this test while breaking the validator: both sides import the same
    # constants. `val_det` is seeded from the fixture shadow so §15's absorb gate
    # (contract shadow_score == det_shadow.valuation_score_det) holds by construction.
    trade.setdefault("lane_contract", build_lane_contract(
        trade, val_det=trade["det_shadow"]["valuation_score_det"]))
    return entry


def as_version(entry: dict, ver: str, *, keep_contract: bool = False) -> dict:
    """Restamp a fixture and (by default) drop `lane_contract`.

    A back-compat case is meant to prove that a V5.0/V5.1 entry still validates, not to
    trip §2e on a contract block it would never have carried. `keep_contract=True` is for
    the one test that targets §2e itself.
    """
    e = copy.deepcopy(entry)
    e["session_export_version"] = ver
    if not keep_contract:
        e["trades_this_session"][0].pop("lane_contract", None)
    return e


def run(entry: dict, label: str, want_rc: int, want_substr: str | None = None) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as fp:
        json.dump([entry], fp, ensure_ascii=False)
        path = fp.name
    try:
        p = subprocess.run([sys.executable, VALIDATOR, "--history", path],
                           capture_output=True, text=True)
        out = (p.stdout + p.stderr).strip()
        if p.returncode != want_rc:
            FAILS.append(f"{label}: rc={p.returncode}, want {want_rc}\n      {out[:300]}")
        elif want_substr and want_substr not in out:
            FAILS.append(f"{label}: rc ok but message missing {want_substr!r}\n      {out[:300]}")
        else:
            print(f"  ok  {label} (rc={p.returncode})")
    finally:
        os.unlink(path)


def run_commit_gate(entry: dict, *, committed: bool, want_rc: int) -> None:
    isolated = copy.deepcopy(entry)
    append_session_export._stamp_provenance(isolated)
    with tempfile.TemporaryDirectory() as tmp:
        session_path = os.path.join(tmp, "session.json")
        history_path = os.path.join(tmp, "history.json")
        with open(session_path, "w", encoding="utf-8") as fp:
            json.dump(isolated, fp, ensure_ascii=False)
        with open(history_path, "w", encoding="utf-8") as fp:
            json.dump([isolated] if committed else [], fp, ensure_ascii=False)
        p = subprocess.run([
            sys.executable, VALIDATOR, "--history", session_path,
            "--require-committed-to", history_path,
        ], capture_output=True, text=True)
        label = f"isolated commit gate ({'present' if committed else 'missing'})"
        if p.returncode != want_rc:
            FAILS.append(
                f"{label}: rc={p.returncode}, want {want_rc}\n"
                f"      {(p.stdout + p.stderr)[:300]}")
        else:
            print(f"  ok  {label} (rc={p.returncode})")


def without(entry: dict, *keys: str) -> dict:
    e = copy.deepcopy(entry)
    for k in keys:
        e["trades_this_session"][0].pop(k, None)
    return e


def without_ra(entry: dict, *keys: str) -> dict:
    """Drop keys from `risk_audit` (the §14 block) rather than the trade root."""
    e = copy.deepcopy(entry)
    for k in keys:
        (e["trades_this_session"][0].get("risk_audit") or {}).pop(k, None)
    return e


# A STAGED_ENTRY fixture whose score genuinely bands to STAGED_ENTRY, so §13's
# band-reachability rule does not mask what §14 is being tested for. Built from a live
# engine run rather than hand-written numbers, for the same reason as `bonus_entry`.
STAGED_INPUT = {
    "ticker": "MU",
    "lane_scores": {"fundamentals": 2.0, "sentiment": 1.0, "news": 1.0,
                    "technical": 2.0, "valuation": 1.0},
    "lane_confidence": {k: 0.7 for k in ("fundamentals", "sentiment", "news",
                                         "technical", "valuation")},
    "structural_shift": {"tier": "NONE"},
    "red_team": {"verdict": "MODERATE_COUNTER", "basis": "unclassified"},
    "macro": {"macro_multiplier": 0.9, "macro_backdrop_score": -1.0,
              "market_regime": "SIDEWAYS"},
    "burry": {"score": 37.1, "veto_flag": False},
    "gates": {"proceed_to_phase3": True, "mandatory_risk_flags": [],
              "phase2_fanout_mode": "PARALLEL_SUBAGENT", "risk_reward_ratio": 2.27},
    "hot_zone": {"industry_top_30pct": False},
    "decision_cap": {"anchors_available": 6, "fair_value_confidence": "high",
                     "lane_data_quality_low": False},
}


def attach_forward_validation(tr: dict) -> dict:
    """Upgrade a doc-derived trade to the engine-1.1 forward contract."""
    pack = tr["valuation_pack"]
    raw_pack = dict(pack)
    raw_pack["score"] = pack.get("score_before_forward_validation", pack.get("score"))
    implied = tr.setdefault("implied_expectations", {})
    shadow = tr.setdefault("valuation_archetype_shadow", {})
    fv = compute_forward_validation(
        raw_pack, implied, shadow)
    pack["score_before_forward_validation"] = fv["valuation_score_before"]
    pack["score"] = fv["valuation_score_effective"]
    pack["forward_validation_status"] = fv["status"]
    fvs = tr.setdefault("fair_value_summary", {})
    fvs["score_before_forward_validation"] = fv["valuation_score_before"]
    fvs["score"] = fv["valuation_score_effective"]
    fvs["forward_validation_status"] = fv["status"]
    tr["forward_validation"] = fv
    tr.setdefault("lane_scores", {})["valuation"] = fv["valuation_score_effective"]
    return fv


def staged_entry_fixture(ex: dict) -> dict:
    e = copy.deepcopy(ex)
    tr = e["trades_this_session"][0]
    forward = attach_forward_validation(tr)
    r = run_phase3({**copy.deepcopy(STAGED_INPUT), "forward_validation": forward})
    if r["final_decision"] != "STAGED_ENTRY":
        FAILS.append(f"staged fixture: engine returned {r['final_decision']!r}, "
                     "expected STAGED_ENTRY — the escape-direction cases need a score "
                     "that genuinely bands to STAGED_ENTRY")
    tr["calculation_steps"] = r["calculation_steps"]
    tr["decision_engine_version"] = r["decision_engine_version"]
    for k in ("final_score", "avg_confidence", "hot_zone_probe", "hot_zone_eval",
              "decision_cap_active"):
        if k in r:
            tr[k] = r[k]
    tr["consensus_bonus_applied"] = r["calculation_steps"].get("bonus_applied", False)
    tr["final_decision"] = "STAGED_ENTRY"
    tr["final_action"] = e["final_action"] = "STAGED"
    tr["staged_split"] = {"aggressive_pct": 50.0, "conservative_pct": 50.0}
    ra = tr["risk_audit"]
    ra["sized_for_decision"] = "STAGED_ENTRY"
    ra["staged_entry_split"] = {"aggressive_pct": 50.0, "conservative_pct": 50.0}
    halved = round(ra["sizing_chain"]["polar_adj"] * 0.5, 6)
    ra["sizing_chain"]["final_position_size"] = halved
    ra["position_size_pct"] = halved
    tr["position_size_pct"] = halved
    return e


# The doc example is a *penalised* chain (rule_5 × 0.95), so it can only exercise the
# penalty half of the cascade-label check. Generate the bonus half from the engine rather
# than hand-writing it — a hardcoded chain would go stale the moment the rules move.
BONUS_INPUT = {
    "ticker": "MU",
    "lane_scores": {"fundamentals": 4.0, "sentiment": 3.0, "news": 3.0,
                    "technical": 4.0, "valuation": 1.0},
    "lane_confidence": {"fundamentals": 0.8, "sentiment": 0.75, "news": 0.7,
                        "technical": 0.8, "valuation": 0.7},
    "structural_shift": {"tier": "NONE"},
    "red_team": {"verdict": "NO_VIABLE_COUNTER", "basis": "unclassified"},
    "macro": {"macro_multiplier": 0.9, "macro_backdrop_score": -1.0, "market_regime": "RISK_ON"},
    "burry": {"score": 37.1, "veto_flag": False},
    "gates": {"proceed_to_phase3": True, "mandatory_risk_flags": [],
              "phase2_fanout_mode": "PARALLEL_SUBAGENT", "risk_reward_ratio": 2.13},
    "hot_zone": {"industry_top_30pct": True},
    "decision_cap": {"anchors_available": 6, "fair_value_confidence": "high",
                     "lane_data_quality_low": False},
}


def bonus_entry(ex: dict) -> dict:
    """The doc example re-scored as a consensus-bonus chain (engine output spliced in)."""
    e = copy.deepcopy(ex)
    tr = e["trades_this_session"][0]
    forward = attach_forward_validation(tr)
    r = run_phase3({**copy.deepcopy(BONUS_INPUT), "forward_validation": forward})
    tr["calculation_steps"] = r["calculation_steps"]
    tr["decision_engine_version"] = r["decision_engine_version"]
    for k in ("final_score", "final_decision", "avg_confidence", "hot_zone_probe",
              "hot_zone_eval", "decision_cap_active"):
        if k in r:
            tr[k] = r[k]
    tr["consensus_bonus_applied"] = r["calculation_steps"].get("bonus_applied", False)
    return e


def main() -> int:
    ex = extract_full_example()
    ver = ex.get("session_export_version")
    print(f"[fixture] phase5_export_schema.md FULL EXAMPLE — version={ver!r}")
    if ver != "V5.3":
        FAILS.append(f"FULL EXAMPLE stamps {ver!r}; the doc's Schema Version is V5.3")

    print("[version gate — §13 Phase 3 engine]")
    run(ex, "V5.3 full example", 0)
    run_commit_gate(ex, committed=True, want_rc=0)
    run_commit_gate(ex, committed=False, want_rc=1)
    run(without(ex, "calculation_steps", "decision_engine_version"),
        "V5.3 minus calculation_steps", 1, "calculation_steps missing")
    run(without(ex, "decision_engine_version"),
        "V5.3 minus decision_engine_version", 1, "decision_engine_version missing")

    print("[version gate — §14 Phase 4 engine]")
    run(without(ex, "risk_audit", "trade_plan_builder_version"),
        "V5.3 minus risk_audit", 1, "risk_audit missing")
    run(without(ex, "trade_plan_builder_version"),
        "V5.3 minus trade_plan_builder_version", 1, "trade_plan_builder_version missing")
    run(without(ex, "mandatory_risk_flags"),
        "V5.3 minus mandatory_risk_flags", 1, "mandatory_risk_flags missing")

    print("[version gate — §15 C1 lane contract]")
    run(without(ex, "lane_contract"), "V5.3 minus lane_contract", 1, "lane_contract missing")

    # Back-compat: the pre-existing V5.0 / V5.1 / V5.2 entries must never need a backfill.
    legacy = as_version(without(ex, "calculation_steps", "decision_engine_version",
                                "risk_audit", "trade_plan_builder_version",
                                "mandatory_risk_flags"), "V5.0")
    run(legacy, "V5.0 legacy, pre-cutover, no engine block", 0)

    legacy51 = as_version(without(ex, "risk_audit", "trade_plan_builder_version",
                                  "mandatory_risk_flags"), "V5.1")
    run(legacy51, "V5.1 legacy, Phase 3 engine only, no Phase 4 block", 0)

    legacy52 = as_version(ex, "V5.2")
    run(legacy52, "V5.2 legacy, both engine blocks, no lane contract", 0)

    print("[bypass guards]")
    # Backstop: stamping an old version after the cutover must not open the gate.
    e = copy.deepcopy(legacy)
    e["export_date"] = e["date"] = "2026-08-05"
    run(e, "V5.0 stamp after cutover (date backstop)", 1, "2026-08-03")

    e = as_version(without(ex, "risk_audit", "trade_plan_builder_version",
                           "mandatory_risk_flags"), "V5.0")
    run(e, "V5.0 stamp carrying decision_engine_version (§2c)", 1,
        "entry carries decision_engine_version")

    e = as_version(ex, "V4.8")
    run(e, "V4.8 stamp carrying V5.0-only fields (§2b)", 1, "stamping bug")

    # §2d — the same bypass one version up: keep the Phase 4 engine block but stamp V5.1
    # so §14's version gate never fires.
    e = as_version(ex, "V5.1")
    run(e, "V5.1 stamp carrying trade_plan_builder_version (§2d)", 1,
        "entry carries trade_plan_builder_version")

    # §2e — one more version up: keep the contract but stamp V5.2 so §15 never fires.
    e = as_version(ex, "V5.2", keep_contract=True)
    run(e, "V5.2 stamp carrying lane_contract (§2e)", 1, "entry carries lane_contract")

    e = copy.deepcopy(ex)
    e["session_export_version"] = "V6.0"
    run(e, "unknown version rejected", 1, "expected one of")

    # ── §13 tamper battery ──────────────────────────────────────────────────
    # NB on the band cases: banded-BUY → HOLD is a *legal* path (Auto REJECT / decision
    # cap), so the out-of-band tamper has to claim BUY off a below-threshold chain.
    tampers = [
        ("step product wrong",
         lambda tr: tr["calculation_steps"].__setitem__("fund", "0.25 × 4 × 0.72 = 0.9000")),
        ("raw_total wrong",
         lambda tr: tr["calculation_steps"].__setitem__("raw_total", 3.0)),
        ("raw_after_bonus wrong",
         lambda tr: tr["calculation_steps"].__setitem__("raw_after_bonus", 2.5)),
        ("final_score mirror drift",
         lambda tr: tr.__setitem__("final_score", 1.9)),
        ("penalty_value off the rule table",
         lambda tr: tr["calculation_steps"].__setitem__("penalty_value", 0.77)),
        ("cascade label vs penalty_applied",
         lambda tr: tr["calculation_steps"].__setitem__("cascade_rule_applied", "no_penalty")),
        ("C_eff not quantised",
         lambda tr: tr["calculation_steps"].__setitem__("fund", "0.25 × 4 × 0.69 = 0.6900")),
        ("threshold off the matrix",
         lambda tr: tr["calculation_steps"]["dynamic_threshold"].__setitem__("buy_threshold", 0.5)),
        ("effective_macro_mult ignores floor",
         lambda tr: tr["calculation_steps"].__setitem__("effective_macro_mult", 1.2)),
        ("polarization label lie",
         lambda tr: tr["calculation_steps"]["polarization_modulation"].__setitem__("label", "BIPOLAR")),
        ("decision above band", lambda tr: (
            tr["calculation_steps"].__setitem__(
                "dynamic_threshold", {"buy_threshold": 2.5, "staged_threshold": 2.0,
                                      "rationale": "tampered"}),
            tr.__setitem__("final_decision", "BUY"))),
    ]
    print("[§13 tamper battery]")
    for name, mutate in tampers:
        e = copy.deepcopy(ex)
        mutate(e["trades_this_session"][0])
        run(e, f"tamper: {name}", 1)

    # ── §14 tamper battery ──────────────────────────────────────────────────
    # Same shape as §13's: mutate a valid chain one field at a time, including the
    # *labels* (fragility, FTD stage, approval), because a mislabelled chain still
    # re-derives perfectly and only the rule tables can catch it.
    p4_tampers = [
        ("tail_adj ignores fragility",
         lambda tr: tr["risk_audit"]["sizing_chain"].__setitem__("tail_adj", 0.0406)),
        ("macro_cap invented",
         lambda tr: tr["risk_audit"]["sizing_chain"].__setitem__("macro_cap", 0.03)),
        ("binary link wrong",
         lambda tr: tr["risk_audit"]["sizing_chain"].__setitem__("binary_adj", 0.019)),
        ("burry link wrong",
         lambda tr: tr["risk_audit"]["sizing_chain"].__setitem__("burry_override_adj", 0.018)),
        ("ftd link wrong",
         lambda tr: tr["risk_audit"]["sizing_chain"].__setitem__("ftd_adj", 0.017)),
        ("f1 link wrong",
         lambda tr: tr["risk_audit"]["sizing_chain"].__setitem__("f1_adj", 0.016)),
        ("chain tail vs position_size_pct drift",
         lambda tr: tr.__setitem__("position_size_pct", 0.05)),
        ("fragility label off the table",
         lambda tr: (tr["risk_audit"]["tail_risk"].__setitem__("fragility_label", "RESILIENT"),
                     tr.__setitem__("fragility_label", "RESILIENT"))),
        ("fragility label projection drift",
         lambda tr: tr.__setitem__("fragility_label", "ROBUST")),
        ("ftd gate inert but multiplier ≠ 1.0",
         lambda tr: tr["risk_audit"]["ftd_timeline_gate"].__setitem__("multiplier", 0.75)),
        ("ftd stage vs multiplier off the table",
         lambda tr: tr["risk_audit"]["ftd_timeline_gate"].update(
             {"applied": True, "stage": "prime", "sector_class": "cyclical",
              "multiplier": 0.5})),
        ("F1 applied without a count",
         lambda tr: tr["risk_audit"]["sector_concentration_f1"].update(
             {"applied": True, "active_same_sector_confirmed": None})),
        ("F1 multiplier off the two-value set",
         lambda tr: tr["risk_audit"]["sector_concentration_f1"].__setitem__("multiplier", 0.8)),
        ("REJECTED with a live position",
         lambda tr: tr["risk_audit"].update({"approval": "REJECTED",
                                             "rejection_reason": "R/R"})),
        ("position_size_method projection drift",
         lambda tr: tr.__setitem__("position_size_method", "RULE_BASED")),
        ("RULE_BASED with a vol cap present",
         lambda tr: (tr["risk_audit"].__setitem__("position_size_method", "RULE_BASED"),
                     tr.__setitem__("position_size_method", "RULE_BASED"))),
        ("stop loss past the -10% limit",
         lambda tr: (tr["risk_audit"].__setitem__("final_stop_loss_pct", -14.0),
                     tr.__setitem__("final_stop_loss_pct", -14.0))),
        ("stop loss mirror drift",
         lambda tr: tr.__setitem__("final_stop_loss_pct", -4.0)),
    ]
    print("[§14 tamper battery]")
    for name, mutate in p4_tampers:
        e = copy.deepcopy(ex)
        mutate(e["trades_this_session"][0])
        run(e, f"tamper: {name}", 1)

    # ── §14 × Phase 4.6 decision cap (V4.86.0 regression) ───────────────────
    # The cap runs AFTER Phase 4 sizing, clamps the position to 30bps and may rewrite
    # BUY into HOLD / STAGED_ENTRY. §14 shipped without modelling any of that and so
    # rejected every capped export — a hard stop at Phase 5 with no legal way out,
    # since the PM is forbidden from hand-editing the numbers.
    print("[§14 × Phase 4.6 cap]")

    def _capped(**over):
        e = copy.deepcopy(ex)
        tr = e["trades_this_session"][0]
        fields = {"decision_cap_active": True, "avg_confidence": 0.65,
                  "position_size_pct": 0.003}
        fields.update(over)
        tr.update(fields)
        e["final_action"] = tr["final_action"]
        return e

    run(_capped(decision_cap_reason="insufficient_anchors", final_decision="HOLD",
                final_action="CANCEL"),
        "cap, no override: BUY → HOLD @30bps", 0)
    run(_capped(decision_cap_reason="low_valuation_confidence",
                cap_override_reason="major catalyst", final_decision="STAGED_ENTRY",
                final_action="STAGED",
                staged_split={"aggressive_pct": 50.0, "conservative_pct": 50.0}),
        "cap + override: STAGED_ENTRY @30bps", 0)

    # The cap only ever shrinks — it can never justify a size above the chain tail.
    run(_capped(decision_cap_reason="low_data_quality", final_decision="HOLD",
                final_action="CANCEL", position_size_pct=0.05),
        "tamper: cap used to justify an ENLARGED position", 1)
    # ...and an uncapped HOLD still has to be flat.
    e = copy.deepcopy(ex)
    e["trades_this_session"][0].update(final_decision="HOLD", final_action="CANCEL",
                                       position_size_pct=0.02)
    e["final_action"] = "CANCEL"
    run(e, "tamper: uncapped HOLD carrying a live position", 1)
    # sized_for_decision is what drives the halving check, not final_decision.
    e = copy.deepcopy(ex)
    e["trades_this_session"][0]["risk_audit"]["sized_for_decision"] = "STAGED_ENTRY"
    run(e, "tamper: sized_for STAGED_ENTRY but chain not halved", 1)

    # ── sized_for_decision, ESCAPE direction (V4.86.1) ──────────────────────
    # The cases above only exercise the direction that TRIPS the halving check. The
    # field overrides that check, so the direction that matters more is the one that
    # switches it off: declaring "BUY" on a STAGED_ENTRY export waves through a chain
    # at twice the correct size. That shipped passing in 4.86.0 — a new field was
    # added and only the failing direction was tested.
    print("[sized_for_decision — escape direction]")
    staged = staged_entry_fixture(ex)
    run(staged, "STAGED_ENTRY, chain honestly halved", 0)

    e = copy.deepcopy(staged)
    e["trades_this_session"][0]["risk_audit"]["sizing_chain"]["final_position_size"] = \
        e["trades_this_session"][0]["risk_audit"]["sizing_chain"]["polar_adj"]
    e["trades_this_session"][0]["position_size_pct"] = \
        e["trades_this_session"][0]["risk_audit"]["sizing_chain"]["polar_adj"]
    e["trades_this_session"][0]["risk_audit"]["sized_for_decision"] = "BUY"
    run(e, "tamper: sized_for spoofed BUY to skip the halving (2× size)", 1,
        "without approval=REJECTED or decision_cap_active=true")

    e = copy.deepcopy(staged)
    e["trades_this_session"][0]["risk_audit"]["sized_for_decision"] = "NOT_A_DECISION"
    run(e, "tamper: sized_for outside the decision enum", 1)

    run(without_ra(ex, "sized_for_decision"),
        "V5.2 minus risk_audit.sized_for_decision", 1, "sized_for_decision missing")

    # The two legitimate divergences must survive the new equality rule.
    e = copy.deepcopy(ex)
    tr = e["trades_this_session"][0]
    tr["risk_audit"].update(approval="REJECTED", rejection_reason="R/R 1.2 < 2.0")
    tr.update(final_decision="HOLD", final_action="CANCEL", position_size_pct=0.0)
    e["final_action"] = "CANCEL"
    run(e, "legit divergence: approval=REJECTED → HOLD", 0)

    # ── §10b × §14 — V4.108.0 speculative governor ──────────────────────────
    # 第 9 根錨（fwd_earnings_discounted）讓虧損題材股重新拿得到估值、decision cap
    # 解除。這組案例鎖住兩件事：(a) governor 縮小的倉位在 §14 有合法出路（否則決策
    # 放行了卻卡在 Phase 5），(b) 用新錨解鎖決策卻不掛 governor 會被擋下。
    print("[§10b speculative governor]")

    def _spec(*, grade=True, sell_side_only=True, fwd_status="eligible", **over):
        e = copy.deepcopy(ex)
        tr = e["trades_this_session"][0]
        pack = tr.setdefault("valuation_pack", {})
        pack.setdefault("anchors", {})["fwd_earnings_discounted"] = {
            "value": 153.13, "status": fwd_status, "family": "fundamental",
            "provenance": "fmp_analyst_estimates.annual", "as_of": "2026-08-07",
        }
        pack["evidence_independence"] = {
            "eligible_anchors": ["analyst_pt_consensus", "fwd_earnings_discounted"],
            "sell_side_only": sell_side_only,
        }
        if grade:
            tr["speculative_grade"] = True
            tr["speculative_reasons"] = ["pre_profit_fwd_earnings_anchor",
                                         "sell_side_only_evidence"]
            tr["avg_confidence"] = 0.70
            tr["position_size_pct"] = 0.01      # governor 壓過 sizing_chain 鏈尾
        tr.update(over)
        return e

    run(_spec(), "speculative export @1% below the chain tail", 0)
    run(_spec(position_size_pct=0.03),
        "tamper: speculative_grade used to justify a 3% position", 1,
        "position_size_pct ≤ 0.01")
    run(_spec(avg_confidence=0.82),
        "tamper: speculative_grade with confidence 0.82", 1,
        f"avg_confidence ≤ {SPECULATIVE_CONFIDENCE_CAP}")
    run(_spec(speculative_reasons=[]),
        "tamper: speculative_grade without reasons", 1, "non-empty speculative_reasons")
    run(_spec(speculative_reasons=["gut_feel"]),
        "tamper: speculative reason outside the enum", 1, "must be a subset")
    # Integrity：用新錨解鎖決策卻不掛 governor
    run(_spec(grade=False), "tamper: pre-profit anchor live without speculative_grade", 1,
        "必須同時設 speculative_grade=true")
    run(_spec(grade=False, fwd_status="ineligible"),
        "tamper: sell-side-only evidence without speculative_grade", 1,
        "必須同時設 speculative_grade=true")
    # 影子狀態的第 9 根 + 有獨立證據 → 不是 speculative，既有 session 一位元不動
    run(_spec(grade=False, fwd_status="ineligible", sell_side_only=False),
        "shadow-only 9th anchor on a normal export", 0)

    # ── cascade label, bonus side ───────────────────────────────────────────
    # Mirror of "cascade label vs penalty_applied". Relabelling a ×1.15 consensus chain
    # `no_penalty` leaves both the arithmetic and `bonus_applied` intact, so only the
    # label check can catch it — it passed until V4.81.0.
    print("[cascade label — bonus side]")
    bonus = bonus_entry(ex)
    bcs = bonus["trades_this_session"][0]["calculation_steps"]
    if bcs.get("bonus_applied") is not True or bcs.get("cascade_rule_applied") != "consensus_bonus":
        FAILS.append("bonus fixture: engine did not produce a consensus_bonus chain "
                     f"(bonus_applied={bcs.get('bonus_applied')!r}, "
                     f"rule={bcs.get('cascade_rule_applied')!r})")
    run(bonus, "consensus_bonus chain (engine output)", 0)

    e = copy.deepcopy(bonus)
    e["trades_this_session"][0]["calculation_steps"]["cascade_rule_applied"] = "no_penalty"
    run(e, "tamper: bonus chain relabelled no_penalty", 1, "bonus_applied=true")

    e = copy.deepcopy(bonus)
    e["trades_this_session"][0]["calculation_steps"]["bonus_applied"] = False
    run(e, "tamper: consensus_bonus label without the flag", 1, "bonus_applied=False")

    print()
    if FAILS:
        print(f"✗ {len(FAILS)} failure(s):")
        for f in FAILS:
            print("  - " + f)
        return 1
    print("✓ session export schema contract holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
