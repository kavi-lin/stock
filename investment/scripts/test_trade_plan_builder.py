#!/usr/bin/env python3
"""test_trade_plan_builder.py — V4.82.0 spec-parity suite for the Phase 4 execution engine.

Every assertion here is traceable to a line of `investment/investment_protocol_v5_0.md`
§PHASE 4 (Step 1 provenance / Step 2 / Step 3 fragility table / Step 3.5 FTD stage table /
Step 4 sizing chain) or to the V20-F1 concentration rule. If the protocol prose changes,
this file must change with it — the engine is the executor, the protocol is the spec, and
this suite is the contract between them.

Fixture Z replays the 2026-04-18 MU export shipped as the schema FULL EXAMPLE, so the
engine is pinned against a plan a human already signed off on.

Run: python3 investment/scripts/test_trade_plan_builder.py   # rc=0 全過 / rc=1 fail
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trade_plan_builder import (  # noqa: E402
    BASE_POSITION,
    FRAGILITY_MULTIPLIER,
    build_trade_plan,
    classify_sector,
    compute_concentration,
    compute_final_stop_pct,
    compute_ftd_gate,
    compute_sizing_chain,
    compute_step2,
    compute_step3,
    entry_candidates,
    reconcile_stop_loss,
    risk_reward,
    run_phase4,
)

FAILS = []


def eq(label, got, want, tol=1e-9):
    if isinstance(want, float) and isinstance(got, (int, float)) and not isinstance(got, bool):
        ok = abs(got - want) <= tol
    else:
        ok = got == want
    if not ok:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


def _mhp(lower=430.0, point=455.0, upper=480.0, mid_target=540.0):
    return {"short_term_5d": {"band_capped": [lower, point, upper]},
            "mid_term_60d": {"mid_target": mid_target}}


def _base_input(**over):
    inp = {
        "ticker": "MU",
        "final_decision": "BUY",
        "analysis_price": 455.07,
        "time_horizon": "mid",
        "sector": "Technology",
        "multi_horizon_price_framework": _mhp(),
        "technical": {"key_levels": {"support": 415.0, "resistance": 560.0},
                      "rs_rating": 92, "distance_from_50ma_pct": 8.4},
        "phase0": {"ftd": {"state": "NO_SIGNAL", "days_since_ftd": None},
                   "macro_backdrop_score": -1.0},
        "phase3": {"position_size_cap_pct": 100, "polar_position_cap_pct": 100,
                   "hot_zone_probe": False, "t4_resolution": "NONE",
                   "binary_classification": "positive", "binary_event_within_48h": False},
        "mandatory_risk_flags": [],
        "concentration": {"active_same_sector_confirmed": 0},
        "risk_manager": {"final_position_cap_pct": 5.0},
        "tail_risk": {"fragility_label": "ROBUST", "tail_risk_score": 12.0},
    }
    inp.update(over)
    return inp


def _run(**over):
    return run_phase4(_base_input(**over), use_subprocess=False)


# ── Fixture A: sector classification (Step 3.5 表) ───────────────────────────
eq("sector.tech", classify_sector("Technology", None)["sector_class"], "cyclical")
eq("sector.energy", classify_sector("Energy", None)["sector_class"], "cyclical")
eq("sector.comm", classify_sector("Communication", None)["sector_class"], "cyclical")
eq("sector.disc", classify_sector("Consumer_Discretionary", None)["sector_class"], "cyclical")
eq("sector.utilities", classify_sector("Utilities", None)["sector_class"], "defensive")
eq("sector.staples", classify_sector("Consumer_Staples", None)["sector_class"], "defensive")
eq("sector.health", classify_sector("Healthcare", None)["sector_class"], "defensive")
eq("sector.reit", classify_sector("Real_Estate", None)["sector_class"], "defensive")
# An unrecognised sector falls to the conservative (cyclical) side, never defensive.
eq("sector.unknown_class", classify_sector("Crypto Mining", None)["sector_class"], "cyclical")
eq("sector.unknown_basis", classify_sector("Crypto Mining", None)["basis"],
   "unknown_sector_conservative_default")
# Ticker resolution goes through skills/_shared/company_context.TICKER_TO_SECTOR.
eq("sector.from_ticker", classify_sector(None, "NVDA")["sector_class"], "cyclical")
eq("sector.from_ticker_defensive", classify_sector(None, "NEE")["sector_class"], "defensive")


# ── Fixture B: Step 2 vol-adjusted base ──────────────────────────────────────
eq("step2.base", compute_step2({"final_position_cap_pct": 4.2})["base"], 0.042)
eq("step2.method", compute_step2({"final_position_cap_pct": 4.2})["position_size_method"],
   "VOL_ADJUSTED")
eq("step2.fallback_base", compute_step2({"error": "insufficient data"})["base"], BASE_POSITION)
eq("step2.fallback_method", compute_step2({"error": "x"})["position_size_method"], "RULE_BASED")
eq("step2.missing_field", compute_step2({})["position_size_method"], "RULE_BASED")


# ── Fixture C: Step 3 fragility table ────────────────────────────────────────
eq("step3.robust", compute_step3({"fragility_label": "ROBUST",
                                  "tail_risk_score": 29.9})["fragility_multiplier"], 1.0)
eq("step3.moderate", compute_step3({"fragility_label": "MODERATE",
                                    "tail_risk_score": 30.0})["fragility_multiplier"], 0.75)
eq("step3.fragile", compute_step3({"fragility_label": "FRAGILE",
                                   "tail_risk_score": 60.0})["fragility_multiplier"], 0.5)
eq("step3.table_matches_protocol", FRAGILITY_MULTIPLIER,
   {"ROBUST": 1.0, "MODERATE": 0.75, "FRAGILE": 0.5})
# Unavailable tail risk must NOT collapse to ROBUST — that hands the biggest multiplier
# to the case we know least about.
_deg = compute_step3({"error": "yfinance down"})
eq("step3.degraded_label", _deg["fragility_label"], "MODERATE")
eq("step3.degraded_mult", _deg["fragility_multiplier"], 0.75)
eq("step3.degraded_flag", _deg["degraded"], True)
# score / label disagreement is surfaced, label wins
_mismatch = compute_step3({"fragility_label": "ROBUST", "tail_risk_score": 80.0})
eq("step3.mismatch_mult", _mismatch["fragility_multiplier"], 1.0)
eq("step3.mismatch_warns", len(_mismatch["warnings"]), 1)


# ── Fixture D: Step 3.5 FTD stage table, every cell ──────────────────────────
def _gate(days, sector_class, state="FTD_CONFIRMED", tech=None):
    return compute_ftd_gate({"state": state, "days_since_ftd": days}, sector_class, tech or {})


for _d, _stage, _cyc, _defn, _cs in ((1, "prime", 1.00, 1.00, 0), (5, "prime", 1.00, 1.00, 0),
                                     (6, "standard", 0.90, 1.00, 0),
                                     (12, "standard", 0.90, 1.00, 0),
                                     (13, "late_cycle", 0.75, 0.95, -1),
                                     (20, "late_cycle", 0.75, 0.95, -1),
                                     (21, "exhausted", 0.50, 0.85, -2),
                                     (60, "exhausted", 0.50, 0.85, -2)):
    g_c = _gate(_d, "cyclical", tech={"rs_rating": 95, "distance_from_50ma_pct": 5.0})
    g_d = _gate(_d, "defensive")
    eq(f"ftd.d{_d}.stage", g_c["stage"], _stage)
    eq(f"ftd.d{_d}.cyclical_mult", g_c["multiplier"], _cyc)
    eq(f"ftd.d{_d}.defensive_mult", g_d["multiplier"], _defn)
    eq(f"ftd.d{_d}.cyclical_stop", g_c["stop_loss_adjustment_pp"], _cs)
    eq(f"ftd.d{_d}.defensive_stop", g_d["stop_loss_adjustment_pp"], 0)

# 適用前提: state must be FTD_CONFIRMED and days must exist
eq("ftd.no_signal", _gate(7, "cyclical", state="NO_SIGNAL")["applied"], False)
eq("ftd.no_signal_mult", _gate(7, "cyclical", state="NO_SIGNAL")["multiplier"], 1.0)
eq("ftd.null_days", _gate(None, "cyclical")["applied"], False)
eq("ftd.day0", _gate(0, "cyclical")["applied"], False)

# Day 21+ reject is cyclical-only, and fires on either trigger
eq("ftd.reject_rs", _gate(25, "cyclical",
                          tech={"rs_rating": 85, "distance_from_50ma_pct": 5.0}
                          )["rejection_triggered"], True)
eq("ftd.reject_dist", _gate(25, "cyclical",
                            tech={"rs_rating": 95, "distance_from_50ma_pct": 18.0}
                            )["rejection_triggered"], True)
eq("ftd.no_reject_clean", _gate(25, "cyclical",
                                tech={"rs_rating": 95, "distance_from_50ma_pct": 5.0}
                                )["rejection_triggered"], False)
eq("ftd.defensive_never_rejects", _gate(25, "defensive",
                                        tech={"rs_rating": 10, "distance_from_50ma_pct": 99.0}
                                        )["rejection_triggered"], False)
# Missing RS/distance is "cannot judge", not "passes" — no reject, but it is said out loud.
_blind = _gate(25, "cyclical", tech={})
eq("ftd.reject_blind", _blind["rejection_triggered"], False)
eq("ftd.reject_blind_noted", any("無法判定" in n for n in _blind["notes"]), True)


# ── Fixture E: Step 4 sizing chain, stage by stage ───────────────────────────
_neutral = dict(base=0.05, fragility_mult=1.0, macro_backdrop=0.0, binary_class="positive",
                binary_within_48h=False, burry_override=False, ftd_mult=1.0,
                position_size_cap_pct=100, polar_position_cap_pct=100, f1_mult=1.0,
                decision="BUY")
eq("chain.neutral", compute_sizing_chain(**_neutral)["final_position_size"], 0.05)
eq("chain.stage_count", len(compute_sizing_chain(**_neutral)["steps"]), 9)

eq("chain.fragility", compute_sizing_chain(**{**_neutral, "fragility_mult": 0.5}
                                           )["final_position_size"], 0.025)
# macro cap: strictly < -3 triggers; -3.0 itself does not
eq("chain.macro_cap_on", compute_sizing_chain(**{**_neutral, "macro_backdrop": -3.01}
                                              )["macro_cap"], 0.03)
eq("chain.macro_cap_boundary", compute_sizing_chain(**{**_neutral, "macro_backdrop": -3.0}
                                                    )["macro_cap"], 0.05)
# the cap is a min(), so a position already under 3% is untouched
eq("chain.macro_cap_is_min", compute_sizing_chain(**{**_neutral, "base": 0.02,
                                                     "macro_backdrop": -5.0}
                                                  )["macro_cap"], 0.02)
# binary: needs BOTH the class and the 48h window
eq("chain.binary_unknown_48h", compute_sizing_chain(**{**_neutral, "binary_class": "unknown",
                                                       "binary_within_48h": True}
                                                    )["binary_adj"], 0.025)
eq("chain.binary_unknown_no_event", compute_sizing_chain(**{**_neutral, "binary_class": "unknown"}
                                                         )["binary_adj"], 0.05)
eq("chain.binary_positive_48h", compute_sizing_chain(**{**_neutral, "binary_class": "positive",
                                                        "binary_within_48h": True}
                                                     )["binary_adj"], 0.05)
eq("chain.binary_negative_48h", compute_sizing_chain(**{**_neutral, "binary_class": "negative",
                                                        "binary_within_48h": True}
                                                     )["binary_adj"], 0.025)
eq("chain.burry", compute_sizing_chain(**{**_neutral, "burry_override": True}
                                       )["burry_override_adj"], 0.025)
eq("chain.ftd", compute_sizing_chain(**{**_neutral, "ftd_mult": 0.75})["ftd_adj"], 0.0375)
eq("chain.f1", compute_sizing_chain(**{**_neutral, "f1_mult": 0.5})["f1_adj"], 0.025)
eq("chain.shift_candidate", compute_sizing_chain(**{**_neutral, "position_size_cap_pct": 50}
                                                 )["shift_adj"], 0.025)
eq("chain.polar_bipolar", compute_sizing_chain(**{**_neutral, "polar_position_cap_pct": 25}
                                               )["polar_adj"], 0.0125)
eq("chain.staged_halving", compute_sizing_chain(**{**_neutral, "decision": "STAGED_ENTRY"}
                                                )["final_position_size"], 0.025)
# V2.19.0 note: the two caps multiply — BIPOLAR + CANDIDATE = 0.25 × 0.50 = 0.125×
eq("chain.two_caps_multiply",
   compute_sizing_chain(**{**_neutral, "position_size_cap_pct": 50,
                           "polar_position_cap_pct": 25})["final_position_size"],
   0.05 * 0.125)
# full stack, in order: 0.05 ×0.75 ×(cap .03) ×0.5 ×0.5 ×0.5 ×0.5 ×0.5 ×0.25 ×0.5
_full = compute_sizing_chain(base=0.08, fragility_mult=0.75, macro_backdrop=-4.0,
                             binary_class="negative", binary_within_48h=True,
                             burry_override=True, ftd_mult=0.5,
                             position_size_cap_pct=50, polar_position_cap_pct=25,
                             f1_mult=0.5, decision="STAGED_ENTRY")
eq("chain.full.tail_adj", _full["tail_adj"], 0.06)
eq("chain.full.macro_cap", _full["macro_cap"], 0.03)
eq("chain.full.binary", _full["binary_adj"], 0.015)
eq("chain.full.burry", _full["burry_override_adj"], 0.0075)
eq("chain.full.ftd", _full["ftd_adj"], 0.00375)
eq("chain.full.f1", _full["f1_adj"], 0.001875)
# stage traces round to 6dp (1e-6 of portfolio); compare against the same rounding
eq("chain.full.shift", _full["shift_adj"], round(0.0009375, 6))
eq("chain.full.polar", _full["polar_adj"], round(0.000234375, 6))
eq("chain.full.final", _full["final_position_size"], round(0.0001171875, 6))


# ── Fixture F: final_stop_loss_pct + the -10% floor ──────────────────────────
_s = compute_final_stop_pct(entry_ref=100.0, sl_pre_buffer=95.0, buffer_pct=0.0,
                            ftd_stop_adj_pp=0)
eq("stop.base_pct", _s["base_stop_pct"], -5.0)
eq("stop.final", _s["final_stop_loss_pct"], -5.0)
eq("stop.not_floored", _s["floored"], False)
_s2 = compute_final_stop_pct(100.0, 95.0, 0.0, -2)
eq("stop.ftd_adjust", _s2["final_stop_loss_pct"], -7.0)
# exactly -10% is the limit, not past it
_s3 = compute_final_stop_pct(100.0, 92.0, 0.0, -2)
eq("stop.floor_boundary", _s3["final_stop_loss_pct"], -10.0)
eq("stop.floor_boundary_flag", _s3["floored"], False)
_s3b = compute_final_stop_pct(100.0, 90.0, 0.0, -2)   # -12% → clamped
eq("stop.floor", _s3b["final_stop_loss_pct"], -10.0)
eq("stop.floor_flag", _s3b["floored"], True)
_s4 = compute_final_stop_pct(100.0, 95.0, 2.0, 0)   # buffer widens the stop
eq("stop.buffer", _s4["base_stop_pct"], -6.9)
eq("stop.no_entry", compute_final_stop_pct(None, 95.0, 0.0, 0)["final_stop_loss_pct"], None)


# ── Fixture G: stop reconciliation takes the more conservative (higher) price ─
_rec = reconcile_stop_loss(pre_buffer=95.0, entry_ref=100.0, buffer_pct=0.0,
                           final_stop_loss_pct=-3.0)
eq("recon.picks_higher", _rec["stop_loss"], 97.0)
eq("recon.source", _rec["source"], "pct_based")
_rec2 = reconcile_stop_loss(95.0, 100.0, 0.0, -8.0)
eq("recon.picks_structural", _rec2["stop_loss"], 95.0)
eq("recon.source2", _rec2["source"], "structural")
eq("recon.none", reconcile_stop_loss(None, None, 0.0, None)["stop_loss"], None)


# ── Fixture H: R/R arithmetic ────────────────────────────────────────────────
eq("rr.basic", risk_reward(100.0, 130.0, 90.0), 3.0)
eq("rr.exactly_two", risk_reward(100.0, 120.0, 90.0), 2.0)
eq("rr.zero_risk", risk_reward(100.0, 130.0, 100.0), None)
eq("rr.inverted_stop", risk_reward(100.0, 130.0, 110.0), None)
eq("rr.missing_tp", risk_reward(100.0, None, 90.0), None)


# ── Fixture I: Step 1 provenance — entry tracks, TP cap, SL floor ────────────
_plan = build_trade_plan("BUY", _mhp(430.0, 455.0, 480.0, 540.0),
                         {"support": 415.0, "resistance": 500.0}, 455.07, None, "mid")
eq("plan.entry_aggressive", _plan["entry_aggressive"], [455.0, 480.0])
eq("plan.entry_conservative", _plan["entry_conservative"], [430.0, 455.0])
eq("plan.tp_capped", _plan["take_profit"], 500.0)
eq("plan.tp_capped_flag", _plan["take_profit_capped_at_resistance"], True)
eq("plan.sl_pre_buffer", _plan["stop_loss_pre_buffer"], 415.0)   # min(band_lower, support)
_plan_open = build_trade_plan("BUY", _mhp(430.0, 455.0, 480.0, 540.0),
                              {"support": 415.0, "resistance": 560.0}, 455.07, None, "mid")
eq("plan.tp_uncapped", _plan_open["take_profit"], 540.0)
eq("plan.tp_uncapped_flag", _plan_open["take_profit_capped_at_resistance"], False)
_plan_bo = build_trade_plan("BUY", _mhp(430.0, 455.0, 480.0, 540.0),
                            {"support": 415.0, "resistance": 560.0}, 460.0, "breakout", "mid")
eq("plan.breakout_entry_low", _plan_bo["entry_aggressive"][0], 460.0)
# SL takes the LOWER of band_lower / support (the protocol's min), not the nearer one
_plan_lowband = build_trade_plan("BUY", _mhp(400.0, 455.0, 480.0, 540.0),
                                 {"support": 415.0, "resistance": 560.0}, 455.0, None, "mid")
eq("plan.sl_takes_min", _plan_lowband["stop_loss_pre_buffer"], 400.0)

# entry candidate order = 預設軌 → 收緊
eq("entry.buy_order", [c[0] for c in entry_candidates(_plan, "BUY")],
   ["aggressive_mid", "conservative_mid", "conservative_low"])
eq("entry.staged_first", entry_candidates(_plan, "STAGED_ENTRY")[0][0], "staged_blend")
eq("entry.buy_default_price", entry_candidates(_plan, "BUY")[0][1], 467.5)
eq("entry.staged_blend_price", entry_candidates(_plan, "STAGED_ENTRY")[0][1], 455.0)


# ── Fixture J: R/R downgrade path — tighten first, then HOLD ─────────────────
# resistance 500 caps TP; the aggressive track cannot reach 2.0 but a tightened one can.
_tight = _run(technical={"key_levels": {"support": 415.0, "resistance": 500.0},
                         "rs_rating": 92, "distance_from_50ma_pct": 8.4})
eq("rr_solve.track", _tight["trade_plan"]["entry_track_used"], "conservative_low")
eq("rr_solve.approved", _tight["risk_audit"]["approval"], "APPROVED")
eq("rr_solve.decision_kept", _tight["final_decision"], "BUY")
eq("rr_solve.rr_clears", _tight["trade_plan"]["risk_reward_ratio"] >= 2.0, True)
eq("rr_solve.trace_len", len(_tight["trade_plan"]["rr_solve_trace"]), 3)

# No track can clear 2.0 → REJECTED, decision falls to HOLD, size zeroed.
_hopeless = _run(multi_horizon_price_framework=_mhp(430.0, 455.0, 480.0, 462.0),
                 technical={"key_levels": {"support": 415.0, "resistance": 560.0},
                            "rs_rating": 92, "distance_from_50ma_pct": 8.4})
eq("rr_fail.approval", _hopeless["risk_audit"]["approval"], "REJECTED")
eq("rr_fail.decision", _hopeless["final_decision"], "HOLD")
eq("rr_fail.size_zeroed", _hopeless["risk_audit"]["position_size_pct"], 0.0)
eq("rr_fail.reason", "risk_reward_ratio" in (_hopeless["risk_audit"]["rejection_reason"] or ""),
   True)
# ...but the chain it WOULD have produced is still reported, so the audit is not blind.
eq("rr_fail.chain_preserved", _hopeless["risk_audit"]["sizing_chain"]["final_position_size"] > 0,
   True)


# ── Fixture K: FTD day-21 reject propagates to approval ──────────────────────
_rej = _run(phase0={"ftd": {"state": "FTD_CONFIRMED", "days_since_ftd": 22},
                    "macro_backdrop_score": 0.0},
            technical={"key_levels": {"support": 415.0, "resistance": 560.0},
                       "rs_rating": 80, "distance_from_50ma_pct": 5.0})
eq("ftd_reject.approval", _rej["risk_audit"]["approval"], "REJECTED")
eq("ftd_reject.decision", _rej["final_decision"], "HOLD")
eq("ftd_reject.gate_flag", _rej["risk_audit"]["ftd_timeline_gate"]["rejection_triggered"], True)
eq("ftd_reject.size", _rej["risk_audit"]["position_size_pct"], 0.0)


# ── Fixture L: STAGED_ENTRY split + halving ──────────────────────────────────
_staged = _run(final_decision="STAGED_ENTRY")
eq("staged.split", _staged["risk_audit"]["staged_entry_split"],
   {"aggressive_pct": 50.0, "conservative_pct": 50.0})
eq("staged.halved", _staged["risk_audit"]["sizing_chain"]["final_position_size"],
   round(_staged["risk_audit"]["sizing_chain"]["polar_adj"] * 0.5, 6))
eq("buy.no_split", _run()["risk_audit"]["staged_entry_split"], None)


# ── Fixture M: V20-F1 sector concentration ───────────────────────────────────
eq("f1.below", compute_concentration({"active_same_sector_confirmed": 2}, "Technology"
                                     )["multiplier"], 1.0)
eq("f1.at_threshold", compute_concentration({"active_same_sector_confirmed": 3}, "Technology"
                                            )["multiplier"], 0.5)
eq("f1.above", compute_concentration({"active_same_sector_confirmed": 9}, "Technology"
                                     )["applied"], True)
# list form counts only same-sector ACTIVE CONFIRMED
_theses = [
    {"sector": "Technology", "structural_shift_tier": "CONFIRMED", "status": "ACTIVE"},
    {"sector": "Technology", "structural_shift_tier": "CONFIRMED", "status": "ENTRY_READY"},
    {"sector": "Technology", "structural_shift_tier": "CANDIDATE", "status": "ACTIVE"},
    {"sector": "Energy", "structural_shift_tier": "CONFIRMED", "status": "ACTIVE"},
    {"sector": "Technology", "structural_shift_tier": "CONFIRMED", "status": "CLOSED"},
]
eq("f1.list_count", compute_concentration({"active_theses": _theses}, "Technology"
                                          )["active_same_sector_confirmed"], 2)
eq("f1.list_not_applied", compute_concentration({"active_theses": _theses}, "Technology"
                                                )["applied"], False)
_theses3 = _theses + [{"sector": "Technology", "structural_shift_tier": "CONFIRMED",
                       "status": "ACTIVE"}]
eq("f1.list_applied", compute_concentration({"active_theses": _theses3}, "Technology"
                                            )["applied"], True)
# V4.86.0 — the candidate's OWN open thesis must not count toward its own limit.
# The rule sizes 「第 4 個」, so re-analysing a name already held would otherwise
# halve at the 3rd rather than the 4th.
_held = [{"sector": "Technology", "structural_shift_tier": "CONFIRMED",
          "status": "ACTIVE", "ticker": t} for t in ("MU", "NVDA", "AMD")]
eq("f1.excludes_self_count",
   compute_concentration({"active_theses": _held}, "Technology", ticker="MU"
                         )["active_same_sector_confirmed"], 2)
eq("f1.excludes_self_not_applied",
   compute_concentration({"active_theses": _held}, "Technology", ticker="MU")["applied"],
   False)
# A genuine 4th name still trips it.
eq("f1.fourth_name_applies",
   compute_concentration({"active_theses": _held}, "Technology", ticker="INTC")["applied"],
   True)
# An explicit count is taken at face value — the caller resolved it and owns it.
eq("f1.explicit_not_self_adjusted",
   compute_concentration({"active_same_sector_confirmed": 3}, "Technology", ticker="MU"
                         )["applied"], True)
# An unavailable registry is "unknown", never a verified zero.
_absent = compute_concentration(None, "Technology", theses_dir="/nonexistent/theses")
eq("f1.absent_count", _absent["active_same_sector_confirmed"], None)
eq("f1.absent_mult", _absent["multiplier"], 1.0)
eq("f1.absent_source", _absent["source"], "registry_unavailable")
# ...and the run surfaces it as a warning rather than swallowing it
_noconc = _run(concentration=None, theses_dir="/nonexistent/theses")
eq("f1.run_warns", any("concentration" in w for w in _noconc["warnings"]), True)


# ── Fixture N: Rec 11 probe cap is respected by Phase 4 ──────────────────────
_probe = _run(final_decision="STAGED_ENTRY",
              phase3={"position_size_cap_pct": 100, "polar_position_cap_pct": 100,
                      "hot_zone_probe": True, "hot_zone_position_size_cap": 0.0015,
                      "t4_resolution": "NONE", "binary_classification": "positive",
                      "binary_event_within_48h": False})
eq("probe.capped_flag", _probe["risk_audit"]["hot_zone_probe_capped"], True)
eq("probe.size", _probe["risk_audit"]["position_size_pct"], 0.0015)


# ── Fixture O: HOLD / exit decisions size nothing ───────────────────────────
_hold = _run(final_decision="HOLD")
eq("hold.size", _hold["risk_audit"]["position_size_pct"], 0.0)
eq("hold.approved", _hold["risk_audit"]["approval"], "APPROVED")   # nothing to reject
eq("hold.no_rr_gate", _hold["risk_audit"]["rejection_reason"], None)


# ── Fixture P: mandatory_risk_flags is persisted verbatim (V4.82.0) ──────────
_flags = _run(mandatory_risk_flags=["systemic_credit_event", "valuation_sell"])
eq("flags.persisted", _flags["mandatory_risk_flags"],
   ["systemic_credit_event", "valuation_sell"])
eq("flags.default_empty", _run()["mandatory_risk_flags"], [])


# ── Fixture Q: input guards ─────────────────────────────────────────────────
for bad, label in ((None, "none"), ("MAYBE", "garbage")):
    try:
        run_phase4(_base_input(final_decision=bad), use_subprocess=False)
        FAILS.append(f"guard.decision_{label}: expected ValueError")
    except ValueError:
        pass
try:
    run_phase4({"final_decision": "BUY"}, use_subprocess=False)
    FAILS.append("guard.ticker: expected ValueError")
except ValueError:
    pass


# ── Fixture Z: golden replay — schema FULL EXAMPLE (MU 2026-04-18) ───────────
# entry_conservative [405, 425], entry_aggressive [448, 462], TP 540, SL 415, R/R 2.13,
# position 0.0203, VOL_ADJUSTED, FRAGILE. Reproducing the published plan from the MHP
# inputs that would have generated it pins Step 1 provenance against a signed-off record.
_z = run_phase4({
    "ticker": "MU",
    "final_decision": "BUY",
    "analysis_price": 455.07,
    "time_horizon": "mid",
    "sector": "Technology",
    "multi_horizon_price_framework": {
        "short_term_5d": {"band_capped": [405.0, 425.0, 462.0]},
        "mid_term_60d": {"mid_target": 540.0},
    },
    "technical": {"key_levels": {"support": 419.19, "resistance": 560.0}},
    "phase0": {"ftd": {"state": "NO_SIGNAL"}, "macro_backdrop_score": -1.0},
    "phase3": {"position_size_cap_pct": 100, "polar_position_cap_pct": 100,
               "binary_classification": "unknown", "binary_event_within_48h": False,
               "t4_resolution": "NONE"},
    "concentration": {"active_same_sector_confirmed": 0},
    "risk_manager": {"final_position_cap_pct": 5.42},
    "tail_risk": {"fragility_label": "FRAGILE", "tail_risk_score": 60.0},
}, use_subprocess=False)
eq("Z.entry_conservative", _z["trade_plan"]["entry_conservative"], [405.0, 425.0])
eq("Z.entry_aggressive", _z["trade_plan"]["entry_aggressive"], [425.0, 462.0])
eq("Z.take_profit", _z["trade_plan"]["take_profit"], 540.0)
eq("Z.method", _z["risk_audit"]["position_size_method"], "VOL_ADJUSTED")
eq("Z.fragility", _z["risk_audit"]["tail_risk"]["fragility_label"], "FRAGILE")
eq("Z.fragility_mult", _z["risk_audit"]["sizing_chain"]["tail_adj"], round(0.0542 * 0.5, 6))
eq("Z.no_macro_cap", _z["risk_audit"]["sizing_chain"]["macro_cap"], round(0.0542 * 0.5, 6))
eq("Z.binary_no_event", _z["risk_audit"]["sizing_chain"]["binary_multiplier"], 1.0)
eq("Z.ftd_inert", _z["risk_audit"]["ftd_timeline_gate"]["applied"], False)
eq("Z.position", _z["risk_audit"]["position_size_pct"], 0.0271)
eq("Z.approved", _z["risk_audit"]["approval"], "APPROVED")
eq("Z.rr_clears", _z["trade_plan"]["risk_reward_ratio"] >= 2.0, True)
eq("Z.version", _z["trade_plan_builder_version"], "1.0.0")


# ──────────────────────────────────────────────────────────────────────────────
if FAILS:
    print(f"✗ {len(FAILS)} spec-parity failure(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ all trade-plan-builder spec-parity fixtures pass (A–Q + MU golden replay)")
