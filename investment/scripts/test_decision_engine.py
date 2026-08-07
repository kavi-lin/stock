#!/usr/bin/env python3
"""test_decision_engine.py — V4.80.0 spec-parity suite for the Phase 3 decision engine.

Every assertion here is traceable to a line of `investment/investment_protocol_v5_0.md`
§PHASE 3 / §決策閾值 / §Auto REJECT / §PHASE 4.6. If the protocol prose changes, this
file must change with it — that is the whole point: the engine is the executor, the
protocol is the spec, and this suite is the contract between them.

Fixture Z is a golden replay of the stored 2026-08-02 MU entry (the only production
entry carrying a full `calculation_steps` block) — byte-for-byte on all five Step 1
strings plus every downstream number.

Run: python3 investment/scripts/test_decision_engine.py   # rc=0 全過 / rc=1 fail
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decision_engine import (  # noqa: E402
    apply_decision_cap,
    c_eff,
    compute_dynamic_threshold,
    compute_step1,
    compute_step1_5,
    compute_step1_7,
    compute_step2,
    compute_step3,
    compute_transition_gate,
    decision_band,
    evaluate_auto_reject,
    evaluate_decision_cap_triggers,
    evaluate_hot_zone,
    run_phase3,
    DEFAULT_WEIGHTS,
)

FAILS = []


def eq(label, got, want, tol=1e-9):
    if isinstance(want, float) and isinstance(got, (int, float)) and not isinstance(got, bool):
        ok = abs(got - want) <= tol
    else:
        ok = got == want
    if not ok:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


def _rt(verdict="STRONG_COUNTER", basis="unclassified", strength=None, sig=None):
    return {"verdict": verdict, "basis": basis, "counter_evidence_strength": strength,
            "_transition_signature": sig}


_NO_TRANSITION = {"valuation_confirmed_transition": False,
                  "transition_softening_disabled": False}


# ── Fixture A: C_eff three-tier quantisation (V4.70.0 P0-4) ──────────────────
eq("c_eff.below_low", c_eff(0.4499), 0.35)
eq("c_eff.low_edge", c_eff(0.45), 0.60)            # 0.45 is NORMAL, not LOW
eq("c_eff.normal_top", c_eff(0.6749), 0.60)
eq("c_eff.high_edge", c_eff(0.675), 0.72)          # 0.675 is HIGH
eq("c_eff.high", c_eff(0.95), 0.72)
eq("c_eff.zero", c_eff(0.0), 0.35)
eq("c_eff.none", c_eff(None), None)


# ── Fixture B: Step 1 weighting ──────────────────────────────────────────────
b_scores = {"fundamentals": 2.0, "sentiment": 1.0, "news": -1.0,
            "technical": 3.0, "valuation": -2.0}
b_conf = {"fundamentals": 0.7, "sentiment": 0.4, "news": 0.6,
          "technical": 0.8, "valuation": 0.5}
b = compute_step1(b_scores, b_conf, DEFAULT_WEIGHTS)
# 0.25×2×0.72 + 0.15×1×0.35 + 0.20×-1×0.60 + 0.25×3×0.72 + 0.15×-2×0.60
eq("step1.raw_total", round(b["raw_total"], 6), round(0.36 + 0.0525 - 0.12 + 0.54 - 0.18, 6))
eq("step1.fund_string", b["steps"]["fund"], "0.25 × 2 × 0.72 = 0.3600")
eq("step1.sent_string", b["steps"]["sent"], "0.15 × 1 × 0.35 = 0.0525")
eq("step1.avg_conf_raw", round(b["avg_confidence_raw"], 4), 0.6)
eq("step1.no_missing", b["missing_lanes"], [])

# Missing lane: weight is NOT redistributed (spec-faithful) and it is reported.
b2 = compute_step1({**b_scores, "news": None}, b_conf, DEFAULT_WEIGHTS)
eq("step1.missing_lane_reported", b2["missing_lanes"], ["news"])
eq("step1.missing_no_redistribution", round(b2["raw_total"], 6),
   round(b["raw_total"] + 0.12, 6))
eq("step1.missing_conf_excluded", round(b2["avg_confidence_raw"], 4), 0.6)

# Step 1 strings must never carry scientific notation — the validator and the replay
# harness re-parse them, and `4e-05` reads as unparseable.
b3 = compute_step1({**b_scores, "sentiment": 0.00004}, b_conf, DEFAULT_WEIGHTS)
eq("step1.no_scientific_notation", "e" in b3["steps"]["sent"].lower(), False)


# ── Fixture C: Step 1.5 structural shift ─────────────────────────────────────
c_conf = compute_step1_5("CONFIRMED")
eq("step1_5.confirmed.floor", c_conf["shift_macro_floor"], 1.00)
eq("step1_5.confirmed.cap", c_conf["position_size_cap_pct"], 100)
eq("step1_5.confirmed.mr_blocked", c_conf["red_team_mean_reversion_blocked"], True)
c_cand = compute_step1_5("CANDIDATE")
eq("step1_5.candidate.floor", c_cand["shift_macro_floor"], 0.95)
eq("step1_5.candidate.cap", c_cand["position_size_cap_pct"], 50)
eq("step1_5.candidate.mr_blocked", c_cand["red_team_mean_reversion_blocked"], False)
for t in (None, "NONE", "INSUFFICIENT_DATA"):
    n = compute_step1_5(t)
    eq(f"step1_5.none[{t}].floor", n["shift_macro_floor"], 0.0)
    eq(f"step1_5.none[{t}].cap", n["position_size_cap_pct"], 100)


# ── Fixture D: Step 1.7 polarization 4-tier ──────────────────────────────────
D_BIPOLAR = {"fundamentals": 3.0, "sentiment": 2.0, "news": -2.0, "technical": -1.5}
D_OUTLIER = {"fundamentals": 3.0, "sentiment": 2.0, "news": 2.0, "technical": 1.0}
D_MIXED = {"fundamentals": 1.5, "sentiment": 1.0, "news": 0.5, "technical": -1.5}
D_ALIGNED = {"fundamentals": 2.0, "sentiment": 2.0, "news": 1.0, "technical": 1.0}

d1 = compute_step1_7(D_BIPOLAR, -1.0, "NONE", "SIDEWAYS")
eq("step1_7.bipolar.label", d1["label"], "BIPOLAR")
eq("step1_7.bipolar.mult", d1["confidence_multiplier"], 0.5)
eq("step1_7.bipolar.cap", d1["position_cap_after"], 25)
eq("step1_7.bipolar.downgrade", d1["force_buy_downgrade"], True)

# BIPOLAR exception — CONFIRMED shift during a bull regime softens 0.5 → 0.7
d1b = compute_step1_7(D_BIPOLAR, -1.0, "CONFIRMED", "BULL")
eq("step1_7.bipolar.confirmed_bull_mult", d1b["confidence_multiplier"], 0.7)
eq("step1_7.bipolar.confirmed_bull_cap", d1b["position_cap_after"], 25)
d1c = compute_step1_7(D_BIPOLAR, -1.0, "CONFIRMED", "VOLATILE")
eq("step1_7.bipolar.confirmed_nonbull_mult", d1c["confidence_multiplier"], 0.5)
d1d = compute_step1_7(D_BIPOLAR, -1.0, "CANDIDATE", "RISK_ON")
eq("step1_7.bipolar.candidate_bull_no_exception", d1d["confidence_multiplier"], 0.5)

d2 = compute_step1_7(D_OUTLIER, -1.5, "NONE", "BULL")
eq("step1_7.outlier.label", d2["label"], "OUTLIER")
eq("step1_7.outlier.mult", d2["confidence_multiplier"], 0.85)
eq("step1_7.outlier.cap_untouched", d2["position_cap_after"], 100)
eq("step1_7.outlier.downgrade", d2["force_buy_downgrade"], False)
eq("step1_7.outlier.lane_id", d2["outlier_lane_id"], "Valuation")

d3 = compute_step1_7(D_MIXED, 0.0, "NONE", "BULL")
eq("step1_7.mixed.label", d3["label"], "MIXED")
eq("step1_7.mixed.mult", d3["confidence_multiplier"], 0.75)
eq("step1_7.mixed.cap_untouched", d3["position_cap_after"], 100)

d4 = compute_step1_7(D_ALIGNED, 1.5, "NONE", "BULL")
eq("step1_7.aligned.label", d4["label"], "ALIGNED")
eq("step1_7.aligned.mult", d4["confidence_multiplier"], 1.0)
eq("step1_7.aligned.no_outlier_id", d4["outlier_lane_id"], None)

# Insufficient lanes → no label, no modulation (never a crash)
d5 = compute_step1_7({"fundamentals": 1.0}, None, "NONE", "BULL")
eq("step1_7.insufficient.label", d5["label"], None)
eq("step1_7.insufficient.mult", d5["confidence_multiplier"], 1.0)


# ── Fixture E: Step 2 cascade — 5 rules, first match wins ────────────────────
E_SAME = {"fundamentals": 2.0, "sentiment": 1.0, "news": 1.5, "technical": 2.0}

# Consensus bonus: all 5 same direction + no Burry veto + NO_VIABLE_COUNTER
e_bonus = compute_step2(1.0, E_SAME, 1.0, _rt("NO_VIABLE_COUNTER"), "NONE",
                        _NO_TRANSITION, burry_veto=False)
eq("step2.bonus.applied", e_bonus["bonus_applied"], True)
eq("step2.bonus.value", round(e_bonus["raw_after_bonus"], 6), 1.15)
eq("step2.bonus.rule", e_bonus["cascade_rule_applied"], "consensus_bonus")

# Burry veto kills the bonus
e_veto = compute_step2(1.0, E_SAME, 1.0, _rt("NO_VIABLE_COUNTER"), "NONE",
                       _NO_TRANSITION, burry_veto=True)
eq("step2.bonus.burry_veto_blocks", e_veto["bonus_applied"], False)
eq("step2.bonus.burry_veto_passthrough", e_veto["raw_after_bonus"], 1.0)

# A zero lane breaks "same direction"
e_zero = compute_step2(1.0, {**E_SAME, "sentiment": 0.0}, 1.0, _rt("NO_VIABLE_COUNTER"),
                       "NONE", _NO_TRANSITION, burry_veto=False)
eq("step2.bonus.zero_breaks_direction", e_zero["bonus_applied"], False)

# Non-STRONG_COUNTER verdicts pass through untouched
e_mod = compute_step2(1.0, D_MIXED, -1.0, _rt("MODERATE_COUNTER"), "NONE",
                      _NO_TRANSITION, burry_veto=False)
eq("step2.moderate.no_penalty", e_mod["penalty_applied"], False)
eq("step2.moderate.rule", e_mod["cascade_rule_applied"], "no_penalty")
eq("step2.moderate.passthrough", e_mod["raw_after_bonus"], 1.0)

# Rule 1 — CONFIRMED + mean-reversion/contaminated → auto-downgrade to MODERATE, 0.925
for basis in ("pure_mean_reversion", "contaminated"):
    r1 = compute_step2(2.0, D_MIXED, -1.0, _rt(basis=basis), "CONFIRMED",
                       _NO_TRANSITION, burry_veto=False)
    eq(f"step2.rule1[{basis}].rule", r1["cascade_rule_applied"],
       "rule_1_paradigm_confirmed_mr_downgrade")
    eq(f"step2.rule1[{basis}].penalty", r1["penalty_value"], 0.925)
    eq(f"step2.rule1[{basis}].downgrade", r1["red_team_auto_downgrade"], True)
    eq(f"step2.rule1[{basis}].effective", r1["effective_verdict"], "MODERATE_COUNTER")
    eq(f"step2.rule1[{basis}].value", round(r1["raw_after_bonus"], 6), 1.85)

# CONFIRMED + pure_forward does NOT hit rule 1 — falls through to rule 4
r1_fwd = compute_step2(2.0, D_MIXED, -1.0, _rt(basis="pure_forward", strength=5),
                       "CONFIRMED", _NO_TRANSITION, burry_veto=False)
eq("step2.confirmed_pure_forward.rule", r1_fwd["cascade_rule_applied"], "rule_4_pure_forward")
eq("step2.confirmed_pure_forward.penalty", r1_fwd["penalty_value"], 0.85)

# Rule 2 — mix transition + valuation-confirmed + purely mean-reversion → 0.95
GATE_OK = {"valuation_confirmed_transition": True, "transition_softening_disabled": False}
for sig in ("mix_only", "both"):
    r2 = compute_step2(2.0, D_MIXED, -1.0, _rt(basis="pure_mean_reversion", sig=sig),
                       "NONE", GATE_OK, burry_veto=False)
    eq(f"step2.rule2[{sig}].rule", r2["cascade_rule_applied"],
       "rule_2_transition_signature_mr_soften")
    eq(f"step2.rule2[{sig}].penalty", r2["penalty_value"], 0.95)

# margin_only signature is not eligible for rule 2 → falls to rule 5
r2_margin = compute_step2(2.0, D_MIXED, -1.0,
                          _rt(basis="pure_mean_reversion", sig="margin_only"),
                          "NONE", GATE_OK, burry_veto=False)
eq("step2.rule2.margin_only_falls_through", r2_margin["cascade_rule_applied"],
   "rule_5_default_strong_counter")

# Staleness disables rule 2 ONLY — the other four still apply
GATE_STALE = {"valuation_confirmed_transition": True, "transition_softening_disabled": True}
r2_stale = compute_step2(2.0, D_MIXED, -1.0,
                         _rt(basis="pure_mean_reversion", sig="mix_only"),
                         "NONE", GATE_STALE, burry_veto=False)
eq("step2.rule2.stale_disables", r2_stale["cascade_rule_applied"],
   "rule_5_default_strong_counter")
r1_stale = compute_step2(2.0, D_MIXED, -1.0,
                         _rt(basis="pure_mean_reversion", sig="mix_only"),
                         "CONFIRMED", GATE_STALE, burry_veto=False)
eq("step2.rule1.survives_stale", r1_stale["cascade_rule_applied"],
   "rule_1_paradigm_confirmed_mr_downgrade")

# Rule 3 — CANDIDATE outranks rule 4 even for a pure_forward strength-5 attack
r3 = compute_step2(2.0, D_MIXED, -1.0, _rt(basis="pure_forward", strength=5),
                   "CANDIDATE", _NO_TRANSITION, burry_veto=False)
eq("step3.rule3.rule", r3["cascade_rule_applied"], "rule_3_paradigm_candidate")
eq("step3.rule3.penalty", r3["penalty_value"], 0.925)

# Rule 4 — strength grading (V4.70.0 P0-2)
r4_5 = compute_step2(2.0, D_MIXED, -1.0, _rt(basis="pure_forward", strength=5),
                     "NONE", _NO_TRANSITION, burry_veto=False)
eq("step2.rule4.strength5", r4_5["penalty_value"], 0.85)
for s in (4, 3, 1, None):
    r4 = compute_step2(2.0, D_MIXED, -1.0, _rt(basis="pure_forward", strength=s),
                       "NONE", _NO_TRANSITION, burry_veto=False)
    eq(f"step2.rule4.strength{s}", r4["penalty_value"], 0.925)
    eq(f"step2.rule4.strength{s}.rule", r4["cascade_rule_applied"], "rule_4_pure_forward")

# Rule 5 — unclassified / mr-without-transition default to the light penalty
for basis in ("unclassified", "pure_mean_reversion", "contaminated"):
    r5 = compute_step2(2.0, D_MIXED, -1.0, _rt(basis=basis), "NONE",
                       _NO_TRANSITION, burry_veto=False)
    eq(f"step2.rule5[{basis}].rule", r5["cascade_rule_applied"],
       "rule_5_default_strong_counter")
    eq(f"step2.rule5[{basis}].penalty", r5["penalty_value"], 0.95)

# Basis defaults to the apply_det_shadow classifier when not supplied
r_cls = compute_step2(2.0, D_MIXED, -1.0,
                      {"verdict": "STRONG_COUNTER",
                       "counter_thesis": "估值終將回到歷史均值，週期見頂",
                       "kill_conditions": []},
                      "CONFIRMED", _NO_TRANSITION, burry_veto=False)
eq("step2.classifier.basis", r_cls["red_team_basis"], "pure_mean_reversion")
eq("step2.classifier.rule", r_cls["cascade_rule_applied"],
   "rule_1_paradigm_confirmed_mr_downgrade")


# ── Fixture F: transition gate + staleness cross-check ───────────────────────
f_ok = compute_transition_gate(
    {"transition_signature": "mix_only", "forecaster_transition_case": True,
     "valuation_cited_transition_overlay": True,
     "valuation_transition_dissent_basis": "peer_multiple"}, -1.0)
eq("gate.confirmed", f_ok["valuation_confirmed_transition"], True)
eq("gate.not_stale", f_ok["transition_softening_disabled"], False)

f_thesis = compute_transition_gate(
    {"transition_signature": "mix_only", "forecaster_transition_case": True,
     "valuation_cited_transition_overlay": True,
     "valuation_transition_dissent_basis": "thesis_fundamental"}, -1.0)
eq("gate.thesis_fundamental_blocks", f_thesis["valuation_confirmed_transition"], False)

# null dissent basis with a negative valuation lane → conservative default
f_null_neg = compute_transition_gate(
    {"transition_signature": "both", "forecaster_transition_case": True,
     "valuation_cited_transition_overlay": True}, -0.5)
eq("gate.null_dissent_negative_lane", f_null_neg["valuation_confirmed_transition"], False)
eq("gate.null_dissent_effective", f_null_neg["dissent_basis_effective"], "thesis_fundamental")
f_null_pos = compute_transition_gate(
    {"transition_signature": "both", "forecaster_transition_case": True,
     "valuation_cited_transition_overlay": True}, 1.0)
eq("gate.null_dissent_positive_lane", f_null_pos["valuation_confirmed_transition"], True)

# lane_score is NOT the gate — a negative Valuation lane still confirms when
# the dissent basis is non-thesis (V3.17 Round 3 rejection of the score gate)
eq("gate.lane_score_not_gate", f_ok["valuation_confirmed_transition"], True)

f_skew = compute_transition_gate(
    {"transition_signature": "mix_only", "forecaster_transition_case": True,
     "transition_signature_mtime": "2026-08-02T00:00:00",
     "forecaster_transition_case_mtime": "2026-08-02T07:00:01",
     "valuation_cited_transition_overlay": True,
     "valuation_transition_dissent_basis": "peer_multiple"}, -1.0)
eq("gate.mtime_skew_stale", f_skew["transition_softening_disabled"], True)
eq("gate.mtime_skew_alert", f_skew["alerts"][0]["kind"], "transition_mtime_skew")
f_within = compute_transition_gate(
    {"transition_signature": "mix_only", "forecaster_transition_case": True,
     "transition_signature_mtime": "2026-08-02T00:00:00",
     "forecaster_transition_case_mtime": "2026-08-02T05:59:00",
     "valuation_cited_transition_overlay": True,
     "valuation_transition_dissent_basis": "peer_multiple"}, -1.0)
eq("gate.mtime_within_6h", f_within["transition_softening_disabled"], False)
f_incon = compute_transition_gate(
    {"transition_signature": None, "forecaster_transition_case": True}, -1.0)
eq("gate.inconsistent_stale", f_incon["transition_softening_disabled"], True)
eq("gate.inconsistent_kind", f_incon["alerts"][0]["kind"],
   "transition_signature_inconsistent")


# ── Fixture G: Step 3 directional macro multiplier ───────────────────────────
g1 = compute_step3(2.0, 1.05, 3.0, 0.0)
eq("step3.aligned.label", g1["macro_alignment"], "ALIGNED")
eq("step3.aligned.score", round(g1["final_score"], 6), 2.1)
g2 = compute_step3(2.0, 0.9, -3.0, 0.0)
eq("step3.contrarian.label", g2["macro_alignment"], "CONTRARIAN")
eq("step3.contrarian.score", g2["final_score"], 2.0)
g3 = compute_step3(-2.0, 0.9, -3.0, 0.0)
eq("step3.both_negative_aligned", g3["macro_alignment"], "ALIGNED")
eq("step3.both_negative_score", round(g3["final_score"], 6), -1.8)
g4 = compute_step3(2.0, 0.85, 3.0, 0.95)
eq("step3.shift_floor_wins", g4["effective_macro_mult"], 0.95)
g5 = compute_step3(2.0, 1.05, 3.0, 0.95)
eq("step3.multiplier_wins", g5["effective_macro_mult"], 1.05)
g6 = compute_step3(2.0, 0.9, 0.0, 0.0)
eq("step3.zero_backdrop_is_contrarian", g6["macro_alignment"], "CONTRARIAN")
eq("step3.zero_backdrop_score", g6["final_score"], 2.0)
g7 = compute_step3(2.0, None, 3.0, 0.0)
eq("step3.null_multiplier_defaults_1", g7["effective_macro_mult"], 1.0)


# ── Fixture H: dynamic threshold matrix (V2.20.0) ────────────────────────────
eq("thr.confirmed_aligned", compute_dynamic_threshold("CONFIRMED", "ALIGNED")["buy_threshold"], 1.0)
eq("thr.candidate_aligned", compute_dynamic_threshold("CANDIDATE", "ALIGNED")["buy_threshold"], 1.1)
eq("thr.bipolar", compute_dynamic_threshold("NONE", "BIPOLAR")["buy_threshold"], 1.5)
eq("thr.outlier", compute_dynamic_threshold("NONE", "OUTLIER")["buy_threshold"], 1.3)
eq("thr.default", compute_dynamic_threshold("NONE", "ALIGNED")["buy_threshold"], 1.2)
eq("thr.confirmed_mixed_default", compute_dynamic_threshold("CONFIRMED", "MIXED")["buy_threshold"], 1.2)
eq("thr.candidate_outlier_takes_outlier",
   compute_dynamic_threshold("CANDIDATE", "OUTLIER")["buy_threshold"], 1.3)
eq("thr.confirmed_bipolar_takes_bipolar",
   compute_dynamic_threshold("CONFIRMED", "BIPOLAR")["buy_threshold"], 1.5)
# staged is always buy − 0.4 with a 0.6 floor
eq("thr.staged_floor", compute_dynamic_threshold("CONFIRMED", "ALIGNED")["staged_threshold"], 0.6)
eq("thr.staged_1_1", compute_dynamic_threshold("CANDIDATE", "ALIGNED")["staged_threshold"], 0.7)
eq("thr.staged_default", compute_dynamic_threshold("NONE", "ALIGNED")["staged_threshold"], 0.8)
eq("thr.staged_outlier", compute_dynamic_threshold("NONE", "OUTLIER")["staged_threshold"], 0.9)
eq("thr.staged_bipolar", compute_dynamic_threshold("NONE", "BIPOLAR")["staged_threshold"], 1.1)


# ── Fixture I: decision band, including the negative mirror ──────────────────
eq("band.buy", decision_band(1.25, 1.2, 0.8), "BUY")
eq("band.buy_exact", decision_band(1.2, 1.2, 0.8), "BUY")
eq("band.staged_entry", decision_band(1.0, 1.2, 0.8), "STAGED_ENTRY")
eq("band.staged_entry_exact", decision_band(0.8, 1.2, 0.8), "STAGED_ENTRY")
eq("band.hold_pos", decision_band(0.79, 1.2, 0.8), "HOLD")
eq("band.hold_zero", decision_band(0.0, 1.2, 0.8), "HOLD")
eq("band.hold_neg", decision_band(-0.79, 1.2, 0.8), "HOLD")
eq("band.staged_exit_exact", decision_band(-0.8, 1.2, 0.8), "STAGED_EXIT")
eq("band.staged_exit", decision_band(-1.0, 1.2, 0.8), "STAGED_EXIT")
eq("band.sell_exact", decision_band(-1.2, 1.2, 0.8), "SELL")
eq("band.sell", decision_band(-2.0, 1.2, 0.8), "SELL")


# ── Fixture J: Rec 11 hot-zone judgment tree (TODO-015) ──────────────────────
HZ_ON = {"industry_top_30pct": True}
j_fired = evaluate_hot_zone(0.5, 0.8, HZ_ON, "RISK_ON", False, [], False)
eq("hz.fired.eval", j_fired["hot_zone_eval"], "fired")
eq("hz.fired.probe", j_fired["hot_zone_probe"], True)
eq("hz.fired.tier", j_fired["hot_zone_probe_tier"], "t2_30bps")
eq("hz.fired.cap", j_fired["hot_zone_position_size_cap"], 0.003)

# tier split at exactly 0.4
eq("hz.tier_boundary_upper",
   evaluate_hot_zone(0.4, 0.8, HZ_ON, "BULL", False, [], False)["hot_zone_probe_tier"], "t2_30bps")
j_low = evaluate_hot_zone(0.3999, 0.8, HZ_ON, "BULL", False, [], False)
eq("hz.tier_boundary_lower", j_low["hot_zone_probe_tier"], "t1_15bps")
eq("hz.tier_boundary_lower_cap", j_low["hot_zone_position_size_cap"], 0.0015)
eq("hz.zero_score_qualifies",
   evaluate_hot_zone(0.0, 0.8, HZ_ON, "BULL", False, [], False)["hot_zone_eval"], "fired")

# Not qualifying: score outside [0, staged), wrong industry, wrong regime
eq("hz.negative_score_not_qualifying",
   evaluate_hot_zone(-0.1, 0.8, HZ_ON, "BULL", False, [], False)["hot_zone_eval"], "not_qualifying")
eq("hz.at_staged_not_qualifying",
   evaluate_hot_zone(0.8, 0.8, HZ_ON, "BULL", False, [], False)["hot_zone_eval"], "not_qualifying")
eq("hz.cold_industry_not_qualifying",
   evaluate_hot_zone(0.5, 0.8, {"industry_top_30pct": False}, "BULL", False, [], False)["hot_zone_eval"],
   "not_qualifying")
for reg in ("SIDEWAYS", "VOLATILE", "RISK_OFF", None):
    eq(f"hz.regime_guard[{reg}]",
       evaluate_hot_zone(0.5, 0.8, HZ_ON, reg, False, [], False)["hot_zone_eval"],
       "not_qualifying")

# Suppression order: cap outranks risk flags
j_cap = evaluate_hot_zone(0.5, 0.8, HZ_ON, "BULL", True, ["systemic_event"], False)
eq("hz.cap_outranks_flags", j_cap["hot_zone_eval"], "suppressed_by_cap")
eq("hz.cap_no_probe", j_cap["hot_zone_probe"], False)
eq("hz.risk_flag",
   evaluate_hot_zone(0.5, 0.8, HZ_ON, "BULL", False, ["burry_veto"], False)["hot_zone_eval"],
   "suppressed_by_risk_flag")
eq("hz.auto_reject_suppresses",
   evaluate_hot_zone(0.5, 0.8, HZ_ON, "BULL", False, [], True)["hot_zone_eval"],
   "suppressed_by_risk_flag")
# probe=true ⟺ eval='fired' (validator §11 mutual proof)
for case in (j_fired, j_cap, j_low):
    eq(f"hz.probe_iff_fired[{case['hot_zone_eval']}]",
       case["hot_zone_probe"], case["hot_zone_eval"] == "fired")


# ── Fixture K: Auto REJECT hard gates ────────────────────────────────────────
eq("reject.rr_below_2",
   evaluate_auto_reject({"risk_reward_ratio": 1.9}, {}, "BUY")["triggered"], True)
eq("reject.rr_ok",
   evaluate_auto_reject({"risk_reward_ratio": 2.0}, {}, "BUY")["triggered"], False)
eq("reject.rr_irrelevant_for_hold",
   evaluate_auto_reject({"risk_reward_ratio": 1.0}, {}, "HOLD")["triggered"], False)
eq("reject.proceed_false",
   evaluate_auto_reject({"proceed_to_phase3": False}, {}, "HOLD")["triggered"], True)
eq("reject.binary_unknown_48h",
   evaluate_auto_reject({"binary_classification": "unknown", "binary_event_within_48h": True},
                        {}, "BUY")["triggered"], True)
eq("reject.binary_positive_48h",
   evaluate_auto_reject({"binary_classification": "positive", "binary_event_within_48h": True},
                        {}, "BUY")["triggered"], False)
eq("reject.binary_unknown_no_event",
   evaluate_auto_reject({"binary_classification": "unknown", "binary_event_within_48h": False},
                        {}, "BUY")["triggered"], False)
eq("reject.systemic_flag",
   evaluate_auto_reject({"mandatory_risk_flags": ["systemic_credit_event"]}, {}, "BUY")["triggered"],
   True)
eq("reject.non_systemic_flag_not_a_gate",
   evaluate_auto_reject({"mandatory_risk_flags": ["insider_selling"]}, {}, "BUY")["triggered"], False)
eq("reject.full_fallback_buy",
   evaluate_auto_reject({"phase2_fanout_mode": "FULL_FALLBACK"}, {}, "STAGED_ENTRY")["triggered"], True)
eq("reject.full_fallback_hold_ok",
   evaluate_auto_reject({"phase2_fanout_mode": "FULL_FALLBACK"}, {}, "HOLD")["triggered"], False)
eq("reject.burry_t4_veto", evaluate_auto_reject({}, {"score": 19.9}, "BUY")["triggered"], True)
eq("reject.burry_warning_zone", evaluate_auto_reject({}, {"score": 27.6}, "BUY")["triggered"], False)
eq("reject.burry_veto_flag", evaluate_auto_reject({}, {"veto_flag": True}, "BUY")["triggered"], True)


# ── Fixture L: Phase 4.6 decision cap ────────────────────────────────────────
eq("cap.trigger.anchors",
   evaluate_decision_cap_triggers({"anchors_available": 1})["decision_cap_reason"],
   "insufficient_anchors")
eq("cap.trigger.anchors_ok",
   evaluate_decision_cap_triggers({"anchors_available": 2})["decision_cap_active"], False)
eq("cap.trigger.low_conf",
   evaluate_decision_cap_triggers({"anchors_available": 5,
                                   "fair_value_confidence": "low"})["decision_cap_reason"],
   "low_valuation_confidence")
eq("cap.trigger.low_dq",
   evaluate_decision_cap_triggers({"anchors_available": 5, "fair_value_confidence": "medium",
                                   "lane_data_quality_low": True})["decision_cap_reason"],
   "low_data_quality")
# precedence: anchors before confidence before data quality
eq("cap.trigger.precedence",
   evaluate_decision_cap_triggers({"anchors_available": 0, "fair_value_confidence": "low",
                                   "lane_data_quality_low": True})["decision_cap_reason"],
   "insufficient_anchors")
eq("cap.trigger.absent_block_not_evaluated",
   evaluate_decision_cap_triggers(None)["evaluated"], False)

l_buy = apply_decision_cap({
    "decision_cap": {"anchors_available": 1}, "final_decision": "BUY",
    "avg_confidence": 0.82, "position_size_pct": 0.02, "final_action": "EXECUTE"})
eq("cap.buy_to_hold", l_buy["final_decision"], "HOLD")
eq("cap.buy_conf", l_buy["avg_confidence"], 0.65)
eq("cap.buy_size", l_buy["position_size_pct"], 0.003)
eq("cap.buy_action", l_buy["final_action"], "CANCEL")
eq("cap.buy_reason", l_buy["decision_cap_reason"], "insufficient_anchors")

l_over = apply_decision_cap({
    "decision_cap": {"anchors_available": 1}, "final_decision": "BUY",
    "avg_confidence": 0.82, "position_size_pct": 0.02, "final_action": "EXECUTE",
    "cap_override_reason": "結構性 thesis + 監管利多"})
eq("cap.override_keeps_staged", l_over["final_decision"], "STAGED_ENTRY")
eq("cap.override_action", l_over["final_action"], "STAGED")
eq("cap.override_still_caps_conf", l_over["avg_confidence"], 0.65)
eq("cap.override_still_caps_size", l_over["position_size_pct"], 0.003)
eq("cap.override_recorded", l_over["cap_override_reason"], "結構性 thesis + 監管利多")

l_staged = apply_decision_cap({
    "decision_cap": {"anchors_available": 5, "fair_value_confidence": "low"},
    "final_decision": "STAGED_ENTRY", "avg_confidence": 0.6,
    "position_size_pct": 0.001, "final_action": "STAGED"})
eq("cap.staged_survives", l_staged["final_decision"], "STAGED_ENTRY")
eq("cap.staged_conf_untouched", l_staged["avg_confidence"], 0.6)
eq("cap.staged_size_untouched", l_staged["position_size_pct"], 0.001)
eq("cap.staged_action_untouched", l_staged["final_action"], "STAGED")

l_off = apply_decision_cap({
    "decision_cap": {"anchors_available": 5, "fair_value_confidence": "high"},
    "final_decision": "BUY", "avg_confidence": 0.82,
    "position_size_pct": 0.02, "final_action": "EXECUTE"})
eq("cap.inactive_passthrough_decision", l_off["final_decision"], "BUY")
eq("cap.inactive_passthrough_conf", l_off["avg_confidence"], 0.82)
eq("cap.inactive_passthrough_size", l_off["position_size_pct"], 0.02)
eq("cap.inactive_override_nulled", l_off["cap_override_reason"], None)

# The rule-6 hot-zone exception can never fire inside an active cap (validator §11)
l_probe = apply_decision_cap({
    "decision_cap_active": True, "decision_cap_reason": "low_data_quality",
    "final_decision": "STAGED_ENTRY", "avg_confidence": 0.6,
    "position_size_pct": 0.0015, "final_action": "STAGED", "hot_zone_probe": True})
eq("cap.hot_zone_exception_inapplicable", l_probe["hot_zone_exception_applicable"], False)
eq("cap.hot_zone_conflict_warned", len(l_probe["warnings"]) >= 1, True)


# ── Fixture L2 (V4.108.0): speculative governor — 煞車改調速器 ───────────────
# 第 9 根錨（fwd_earnings_discounted）讓虧損題材股重新拿得到估值 → decision cap 解除。
# Governor 的職責是確保「解除」不等於「正常倉位」：verdict 放行，籌碼壓到 1%。
from decision_engine import evaluate_speculative_grade  # noqa: E402

eq("spec.absent_block_not_evaluated", evaluate_speculative_grade(None)["evaluated"], False)
eq("spec.clean_valuation_not_speculative", evaluate_speculative_grade(
    {"pre_profit_anchor_live": False, "sell_side_only": False})["speculative_grade"], False)
eq("spec.reasons_both", evaluate_speculative_grade(
    {"pre_profit_anchor_live": True, "sell_side_only": True})["speculative_reasons"],
   ["pre_profit_fwd_earnings_anchor", "sell_side_only_evidence"])
eq("spec.sell_side_alone_triggers", evaluate_speculative_grade(
    {"sell_side_only": True})["speculative_grade"], True)

# AAOI 形狀：cap 未觸發（2 根錨、confidence medium），governor 接手壓倉位與信心
l2_aaoi = apply_decision_cap({
    "decision_cap": {"anchors_available": 2, "fair_value_confidence": "medium"},
    "speculative": {"pre_profit_anchor_live": True, "sell_side_only": True},
    "final_decision": "BUY", "avg_confidence": 0.82,
    "position_size_pct": 0.025, "final_action": "EXECUTE"})
eq("spec.verdict_survives", l2_aaoi["final_decision"], "BUY")      # 放行，不是拒絕
eq("spec.action_survives", l2_aaoi["final_action"], "EXECUTE")
eq("spec.size_capped", l2_aaoi["position_size_pct"], 0.01)
eq("spec.conf_capped", l2_aaoi["avg_confidence"], 0.70)
eq("spec.grade_flagged", l2_aaoi["speculative_grade"], True)
eq("spec.cap_not_active", l2_aaoi["decision_cap_active"], False)

# 已經比 1% 小的倉位不被放大（governor 只收不放）
l2_small = apply_decision_cap({
    "decision_cap": {"anchors_available": 2, "fair_value_confidence": "medium"},
    "speculative": {"pre_profit_anchor_live": True},
    "final_decision": "STAGED_ENTRY", "avg_confidence": 0.55,
    "position_size_pct": 0.002, "final_action": "STAGED"})
eq("spec.small_size_untouched", l2_small["position_size_pct"], 0.002)
eq("spec.low_conf_untouched", l2_small["avg_confidence"], 0.55)

# decision cap 與 governor 同時成立 → 較嚴的 30bps / 0.65 勝出（不得被 1% 放寬）
l2_both = apply_decision_cap({
    "decision_cap": {"anchors_available": 1},
    "speculative": {"pre_profit_anchor_live": True, "sell_side_only": True},
    "final_decision": "BUY", "avg_confidence": 0.82,
    "position_size_pct": 0.025, "final_action": "EXECUTE"})
eq("spec.cap_wins_size", l2_both["position_size_pct"], 0.003)
eq("spec.cap_wins_conf", l2_both["avg_confidence"], 0.65)
eq("spec.cap_still_forces_hold", l2_both["final_decision"], "HOLD")
eq("spec.both_flags_recorded", l2_both["speculative_grade"], True)

# 無 speculative block 的既有 session：欄位存在但為 false，數值一位元不動
l2_legacy = apply_decision_cap({
    "decision_cap": {"anchors_available": 5, "fair_value_confidence": "high"},
    "final_decision": "BUY", "avg_confidence": 0.82,
    "position_size_pct": 0.02, "final_action": "EXECUTE"})
eq("spec.legacy_grade_false", l2_legacy["speculative_grade"], False)
eq("spec.legacy_size_untouched", l2_legacy["position_size_pct"], 0.02)
eq("spec.legacy_conf_untouched", l2_legacy["avg_confidence"], 0.82)


# ── Fixture M: end-to-end precedence — hard gates outrank the probe ──────────
M_BASE = {
    "ticker": "TEST",
    "lane_scores": {"fundamentals": 1.0, "sentiment": 0.5, "news": 0.5, "technical": 0.5,
                    "valuation": 0.5},
    "lane_confidence": {"fundamentals": 0.6, "sentiment": 0.6, "news": 0.6,
                        "technical": 0.6, "valuation": 0.6},
    "structural_shift": {"tier": "NONE"},
    "red_team": {"verdict": "MODERATE_COUNTER", "basis": "unclassified"},
    "macro": {"macro_multiplier": 1.0, "macro_backdrop_score": 2.0, "market_regime": "RISK_ON"},
    "burry": {"score": 50.0, "veto_flag": False},
    "gates": {"proceed_to_phase3": True, "mandatory_risk_flags": [],
              "phase2_fanout_mode": "PARALLEL_SUBAGENT"},
    "hot_zone": {"industry_top_30pct": True},
    "decision_cap": {"anchors_available": 5, "fair_value_confidence": "medium",
                     "lane_data_quality_low": False},
}
m = run_phase3(M_BASE)
# (0.25×1 + 0.15×0.5 + 0.20×0.5 + 0.25×0.5 + 0.15×0.5) = 0.625 → ×0.60 C_eff = 0.375
eq("e2e.raw_total", m["calculation_steps"]["raw_total"], 0.375)
eq("e2e.final_score", m["final_score"], 0.375)
eq("e2e.probe_fired", m["hot_zone_eval"], "fired")
eq("e2e.probe_tier", m["hot_zone_probe_tier"], "t1_15bps")
eq("e2e.decision", m["final_decision"], "STAGED_ENTRY")
eq("e2e.band_before", m["decision_band_before_adjustments"], "HOLD")

# --- Hard gates outrank the probe even when the BAND is HOLD ---------------------
# Regression: R/R and FULL_FALLBACK are conditional on a BUY-side decision, so evaluating
# them against the pre-probe HOLD let the probe open a position through a closed gate.
m_rr = run_phase3({**M_BASE, "gates": {**M_BASE["gates"], "risk_reward_ratio": 1.5}})
eq("e2e.probe.rr_below_2_suppresses", m_rr["hot_zone_eval"], "suppressed_by_risk_flag")
eq("e2e.probe.rr_below_2_decision", m_rr["final_decision"], "HOLD")
eq("e2e.probe.rr_prospective_flagged",
   m_rr["auto_reject"]["probe_prospective_triggered"], True)
eq("e2e.probe.rr_band_gate_untouched", m_rr["auto_reject"]["triggered"], False)

m_ff = run_phase3({**M_BASE, "gates": {**M_BASE["gates"],
                                       "phase2_fanout_mode": "FULL_FALLBACK"}})
eq("e2e.probe.full_fallback_suppresses", m_ff["hot_zone_eval"], "suppressed_by_risk_flag")
eq("e2e.probe.full_fallback_decision", m_ff["final_decision"], "HOLD")

# R/R ≥ 2.0 must still let the probe fire — the gate is a gate, not a blanket veto
m_rr_ok = run_phase3({**M_BASE, "gates": {**M_BASE["gates"], "risk_reward_ratio": 2.5}})
eq("e2e.probe.rr_ok_still_fires", m_rr_ok["hot_zone_eval"], "fired")

m_flag = run_phase3({**M_BASE, "gates": {**M_BASE["gates"],
                                         "mandatory_risk_flags": ["valuation_sell"]}})
eq("e2e.risk_flag_suppresses", m_flag["hot_zone_eval"], "suppressed_by_risk_flag")
eq("e2e.risk_flag_decision", m_flag["final_decision"], "HOLD")

m_cap = run_phase3({**M_BASE, "decision_cap": {"anchors_available": 1}})
eq("e2e.cap_suppresses", m_cap["hot_zone_eval"], "suppressed_by_cap")
eq("e2e.cap_active", m_cap["decision_cap_active"], True)
eq("e2e.cap_decision", m_cap["final_decision"], "HOLD")

m_veto = run_phase3({**M_BASE, "burry": {"score": 15.0, "veto_flag": False}})
eq("e2e.burry_veto_suppresses", m_veto["hot_zone_eval"], "suppressed_by_risk_flag")
eq("e2e.burry_veto_reject", m_veto["auto_reject"]["triggered"], True)

# BIPOLAR forced downgrade of a genuine BUY, end to end
M_BIPOLAR = {**M_BASE,
             "lane_scores": {"fundamentals": 5.0, "sentiment": 5.0, "news": 5.0,
                             "technical": -2.0, "valuation": -2.0},
             "lane_confidence": {k: 0.7 for k in
                                 ("fundamentals", "sentiment", "news", "technical", "valuation")},
             "gates": {**M_BASE["gates"], "risk_reward_ratio": 3.0}}
mb = run_phase3(M_BIPOLAR)
eq("e2e.bipolar.label", mb["calculation_steps"]["polarization_modulation"]["label"], "BIPOLAR")
eq("e2e.bipolar.threshold", mb["calculation_steps"]["dynamic_threshold"]["buy_threshold"], 1.5)
eq("e2e.bipolar.band_before", mb["decision_band_before_adjustments"], "BUY")
eq("e2e.bipolar.decision", mb["final_decision"], "STAGED_ENTRY")
eq("e2e.bipolar.polar_cap", mb["polar_position_cap_pct"], 25)
eq("e2e.bipolar.conf", mb["avg_confidence"], round(0.7 * 0.5, 4))

# FULL_FALLBACK forces a BUY-side decision to HOLD
mf = run_phase3({**M_BIPOLAR, "gates": {**M_BIPOLAR["gates"],
                                        "phase2_fanout_mode": "FULL_FALLBACK"}})
eq("e2e.full_fallback.decision", mf["final_decision"], "HOLD")
eq("e2e.full_fallback.forced", mf["auto_reject"]["forced_decision"], "HOLD")

# An incomplete lane set is a broken decision, not a degraded one — fail loudly rather
# than emit a `MISSING` step string the PM would copy into the export.
for bad in ({**M_BASE, "lane_scores": {**M_BASE["lane_scores"], "news": None}},
            {**M_BASE, "lane_confidence": {**M_BASE["lane_confidence"], "technical": None}}):
    try:
        run_phase3(bad)
        FAILS.append("e2e.missing_lane_should_raise: run_phase3 returned instead of raising")
    except ValueError as exc:
        eq("e2e.missing_lane_message", "lane inputs incomplete" in str(exc), True)

# Phase 4.6 cap + override on a genuine BUY — the path the validator band check must allow
m_cap_override = apply_decision_cap({
    "decision_cap_active": True, "decision_cap_reason": "low_valuation_confidence",
    "final_decision": "BUY", "avg_confidence": 0.8, "position_size_pct": 0.02,
    "final_action": "EXECUTE", "cap_override_reason": "結構性 catalyst"})
eq("e2e.cap_override.decision", m_cap_override["final_decision"], "STAGED_ENTRY")
eq("e2e.cap_override.action", m_cap_override["final_action"], "STAGED")


# ── Fixture Z: golden replay of the stored 2026-08-02 MU entry ───────────────
Z = {
    "ticker": "MU",
    "lane_scores": {"fundamentals": 1.5, "sentiment": -0.04, "news": -0.5,
                    "technical": -2.5, "valuation": -1.5},
    "lane_confidence": {"fundamentals": 0.6, "sentiment": 0.5, "news": 0.55,
                        "technical": 0.65, "valuation": 0.5},
    "structural_shift": {"tier": "CONFIRMED"},
    "red_team": {"verdict": "STRONG_COUNTER", "basis": "pure_forward",
                 "counter_evidence_strength": 5, "thesis_break_probability": 0.68},
    "macro": {"macro_multiplier": 0.9, "macro_backdrop_score": 0.5,
              "market_regime": "SIDEWAYS"},
    "burry": {"score": 47.1, "veto_flag": False},
    "gates": {"proceed_to_phase3": True, "mandatory_risk_flags": [],
              "phase2_fanout_mode": "PARALLEL_SUBAGENT"},
    "hot_zone": {"industry_top_30pct": True},
    "decision_cap": {"anchors_available": 5, "fair_value_confidence": "medium",
                     "lane_data_quality_low": False},
}
z = run_phase3(Z)
zc = z["calculation_steps"]
eq("MU.fund", zc["fund"], "0.25 × 1.5 × 0.60 = 0.2250")
eq("MU.sent", zc["sent"], "0.15 × -0.04 × 0.60 = -0.0036")
eq("MU.news", zc["news"], "0.20 × -0.5 × 0.60 = -0.0600")
eq("MU.tech", zc["tech"], "0.25 × -2.5 × 0.60 = -0.3750")
eq("MU.val", zc["val"], "0.15 × -1.5 × 0.60 = -0.1350")
eq("MU.raw_total", zc["raw_total"], -0.3486)
eq("MU.shift_tier", zc["structural_shift_modulation"]["tier"], "CONFIRMED")
eq("MU.shift_floor", zc["structural_shift_modulation"]["shift_macro_floor"], 1.0)
eq("MU.shift_cap", zc["structural_shift_modulation"]["position_size_cap_pct"], 100)
eq("MU.mr_blocked", zc["structural_shift_modulation"]["red_team_mean_reversion_blocked"], True)
eq("MU.polar_label", zc["polarization_modulation"]["label"], "OUTLIER")
eq("MU.polar_range", zc["polarization_modulation"]["lane_range"], 4.0)
eq("MU.polar_pos_strong", zc["polarization_modulation"]["pos_strong"], 1)
eq("MU.polar_neg_strong", zc["polarization_modulation"]["neg_strong"], 2)
eq("MU.polar_outlier_id", zc["polarization_modulation"]["outlier_lane_id"], "Fundamentals")
eq("MU.polar_mult", zc["polarization_modulation"]["confidence_multiplier"], 0.85)
eq("MU.polar_cap", zc["polarization_modulation"]["position_cap_after"], 100)
eq("MU.basis", zc["red_team_basis"], "pure_forward")
eq("MU.auto_downgrade", zc["red_team_auto_downgrade"], False)
eq("MU.cascade", zc["cascade_rule_applied"], "rule_4_pure_forward")
eq("MU.buy_threshold", zc["dynamic_threshold"]["buy_threshold"], 1.3)
eq("MU.staged_threshold", zc["dynamic_threshold"]["staged_threshold"], 0.9)
eq("MU.bonus", zc["bonus_applied"], False)
eq("MU.penalty", zc["penalty_applied"], True)
eq("MU.penalty_value", zc["penalty_value"], 0.85)
eq("MU.raw_after_bonus", zc["raw_after_bonus"], -0.29631)
eq("MU.macro_mult", zc["macro_multiplier"], 0.9)
eq("MU.macro_alignment", zc["macro_alignment"], "CONTRARIAN")
eq("MU.effective_macro_mult", zc["effective_macro_mult"], 1.0)
eq("MU.final_score", zc["final_score"], -0.2963)
eq("MU.avg_confidence", z["avg_confidence"], 0.476)
eq("MU.final_decision", z["final_decision"], "HOLD")
eq("MU.hot_zone_eval", z["hot_zone_eval"], "not_qualifying")
eq("MU.hot_zone_probe", z["hot_zone_probe"], False)
eq("MU.decision_cap", z["decision_cap_active"], False)


# ──────────────────────────────────────────────────────────────────────────────
if FAILS:
    print(f"✗ {len(FAILS)} spec-parity failure(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ all decision-engine spec-parity fixtures pass (A–M + MU golden replay)")
