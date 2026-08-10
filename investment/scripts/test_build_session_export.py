#!/usr/bin/env python3
"""test_build_session_export.py — V4.126.0 Phase 5 assembler contract.

Every assertion here is a seeded regression: break the corresponding rule in
`build_session_export.py` and the named case goes red. The cases mirror the two
real 2026-08-10 META failures and the drift the bring-up itself produced.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_session_export as B  # noqa: E402

FAILS = []


def eq(label, got, want):
    if got != want:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


def raises(label, fn, needle):
    """Assert fn() exits with a message containing `needle`."""
    try:
        fn()
    except SystemExit as e:
        msg = str(e)
        if needle not in msg:
            FAILS.append(f"{label}: wrong error — {msg[:160]!r} (want {needle!r})")
        return
    except Exception as e:  # noqa: BLE001
        FAILS.append(f"{label}: raised {type(e).__name__} not SystemExit: {e}")
        return
    FAILS.append(f"{label}: did NOT raise (expected {needle!r})")


TICKER, DATE = "ZZBUILD", "2026-08-10"

ENGINE = {
    "ticker": TICKER, "decision_engine_version": "V5.3", "engine": "test",
    "final_score": 0.1718, "final_decision": "HOLD", "avg_confidence": 0.764,
    "hot_zone_probe": False, "hot_zone_probe_tier": None, "hot_zone_eval": "not_qualifying",
    "decision_cap_active": False, "decision_cap_reason": None,
    "transition_data_stale_or_inconsistent": False,
    "calculation_steps": {
        "fund": "0.25 × 1 × 0.72 = 0.1800", "sent": "0.15 × 0.58 × 0.72 = 0.0626",
        "news": "0.20 × 0.5 × 0.72 = 0.0720", "tech": "0.25 × 0 × 0.72 = 0.0000",
        "val": "0.15 × -1 × 0.60 = -0.0900",
        "bonus_applied": False, "macro_alignment": "NEUTRAL", "final_score": 0.1718},
}
P3_IN = {"ticker": TICKER,
         "lane_scores": {"fundamentals": 1.0, "sentiment": 0.58, "news": 0.5,
                         "technical": 0.0, "valuation": -1.0},
         "lane_confidence": {"fundamentals": 0.82, "sentiment": 0.88, "news": 0.74,
                             "technical": 0.78, "valuation": 0.6},
         "burry": {"score": 44.4, "veto_flag": False}}
QUANT = {"quant_blocks": {
    "valuation_pack": {"score": -1.0, "current_price": 592.1},
    "fair_value_summary": {}, "fair_value_range": {}, "implied_expectations": {},
    "valuation_archetype_shadow": {}, "valuation_explained_range": {}}}
PHASE0 = {"macro_summary": {"market_regime": "RISK_ON", "macro_backdrop_score": 2.0,
                            "regime_confidence": 0.71, "key_themes": ["a"],
                            "hot_sectors": ["X"], "cold_sectors": ["Y"]},
          "_market_signals": {"market_top_zone": "Yellow", "ftd_status": "FTD_CONFIRMED",
                              "breadth_composite": 76, "vix_current": 14.9},
          "fred_snapshot": {"regime_label": "Soft Landing", "real_rate_10y_estimate": 2.41},
          "phase3_macro_multiplier": 0.9}
PLAN = {"trade_plan_builder_version": "V1", "mandatory_risk_flags": [],
        "trade_plan": {"entry_aggressive": 1, "entry_conservative": 2, "take_profit": 3,
                       "stop_loss": 4, "risk_reward_ratio": 2.0, "time_horizon": "3M",
                       "entry_reference_price": 596.55},
        "risk_audit": {"position_size_pct": 0.0, "position_size_method": "VOL_ADJUSTED",
                       "staged_entry_split": None, "final_stop_loss_pct": 8.0,
                       "tail_risk": {"fragility_label": "MODERATE"},
                       "binary_classification": "positive", "ftd_timeline_gate": "ok"}}
GATE = {"schema": "vrg/1", "ticker": TICKER, "would_invoke": True,
        "mandatory_fired": [], "triggers_fired": ["no_peer_cohort"], "shadow_only": True}


def base_qual(**over):
    q = {
        "schema": "p5-qualitative/1.0", "ticker": TICKER, "date": DATE,
        "lanes": {n: {"signal": "HOLD", "key_factors": ["k"], "risk_flags": ["r"]}
                  for n in B.LANES},
        "red_team": {"verdict": "STRONG_COUNTER", "counter_thesis": "x",
                     "kill_conditions": ["IF a THEN b"],
                     "counter_evidence_strength": 5, "thesis_break_probability": 0.68},
        "burry_narrative": "n", "conflict_bias": {"tentative_decision": "HOLD"},
        "macro_context": "m",
        "watch_conditions": {"a": "1", "b": "2", "c": "3"},
        "key_risks": ["kr"], "bias_notes": "bn",
        "phase2_fanout_mode": "PARALLEL_SUBAGENT", "degraded_analysts": [],
        "decision_point_days": 21, "devils_advocate_filed": True,
        "trade_metadata": {"event_tag": "none"}, "last_outcome": "UNKNOWN",
    }
    q.update(over)
    return q


def write(tmp, name, obj):
    p = os.path.join(tmp, name)
    with open(p, "w", encoding="utf-8") as fp:
        json.dump(obj, fp)
    return p


def load_q(tmp, qual):
    return B.load_qualitative(write(tmp, "q.json", qual), TICKER, DATE)


P4_IN = {"multi_horizon_price_framework": {"short_term_5d": {"band": [1, 2, 3]}}}

ART = {"engine": ENGINE, "p3": P3_IN, "p4": P4_IN, "quant": QUANT, "phase0": PHASE0,
       "phase0_path": "/x/investment/invest_logs/p0.json", "plan": PLAN, "gate": GATE}

with tempfile.TemporaryDirectory() as tmp:
    # ── closed schema ────────────────────────────────────────────────────────
    raises("reject.derived_key",
           lambda: load_q(tmp, base_qual(final_score=1.23)),
           "script 導得出來的欄位")
    raises("reject.derived_calculation_steps",
           lambda: load_q(tmp, base_qual(calculation_steps={})),
           "script 導得出來的欄位")
    raises("reject.unknown_key",
           lambda: load_q(tmp, base_qual(some_new_field=1)),
           "未知欄位")

    # The 2026-08-10 drift: lane numbers retyped instead of taken from the engine input.
    bad_lane = base_qual()
    bad_lane["lanes"]["technical"]["score"] = -1.5
    raises("reject.lane_score_retyped", lambda: load_q(tmp, bad_lane),
           "由 phase-3 engine 輸入決定")
    bad_conf = base_qual()
    bad_conf["lanes"]["technical"]["confidence"] = 0.65
    raises("reject.lane_confidence_retyped", lambda: load_q(tmp, bad_conf),
           "由 phase-3 engine 輸入決定")

    raises("reject.watch_conditions_list",
           lambda: load_q(tmp, base_qual(watch_conditions=["a", "b", "c"])),
           "watch_conditions 必須是 object")
    raises("reject.watch_conditions_too_few",
           lambda: load_q(tmp, base_qual(watch_conditions={"a": "1"})),
           "至少 3 條")
    raises("reject.trade_metadata_null",
           lambda: load_q(tmp, base_qual(trade_metadata=None)),
           "trade_metadata 必填")
    raises("reject.ticker_mismatch",
           lambda: load_q(tmp, base_qual(ticker="OTHER")), "與 --ticker")
    raises("reject.bad_schema",
           lambda: load_q(tmp, base_qual(schema="nope")), "schema 必須是")
    missing_rt = base_qual()
    del missing_rt["red_team"]["counter_evidence_strength"]
    raises("reject.red_team_incomplete", lambda: load_q(tmp, missing_rt), "red_team 缺")

    # ── artifact gating ──────────────────────────────────────────────────────
    raises("artifact.missing_named",
           lambda: B._read_json(os.path.join(tmp, "nope.json"), "pf_quant artifact"),
           "pf_quant artifact 不存在")

    # ── assembly ─────────────────────────────────────────────────────────────
    qual = load_q(tmp, base_qual())
    entry = B.build_entry(qual, ART, TICKER, DATE)
    bundle = B.build_bundle(qual, ART, TICKER, DATE)
    trade = entry["trades_this_session"][0]

    # lane numbers come from the engine input, NOT the qualitative file
    eq("lane_scores.from_engine_input", trade["lane_scores"], P3_IN["lane_scores"])
    eq("bundle.lane_conf.from_engine_input",
       bundle["lanes"]["technical"]["confidence"], 0.78)
    eq("bundle.lane_score.from_engine_input",
       bundle["lanes"]["valuation"]["score"], -1.0)

    # valuation_lane must equal the pack (validator hard rule) — derived, not retyped
    eq("valuation_lane.score_matches_pack",
       trade["valuation_lane"]["score"], QUANT["quant_blocks"]["valuation_pack"]["score"])

    # single-source: bundle and entry must agree on analysis_price. Bring-up produced
    # 596.55 (entry_reference_price) vs 592.10 (valuation_pack) and render rejected it.
    eq("analysis_price.single_sourced",
       bundle["phase4"]["analysis_price"], trade["analysis_price"])
    eq("analysis_price.from_pack", trade["analysis_price"], 592.1)

    # signals single-sourced into conflict_bias
    eq("conflict_bias.lane_signals",
       trade["conflict_bias"]["lane_signals"],
       {n: "HOLD" for n in B.LANES})

    # risk_audit-derived fields the validator requires non-null
    eq("derived.fragility_label", trade["fragility_label"], "MODERATE")
    eq("derived.position_size_method", trade["position_size_method"], "VOL_ADJUSTED")
    eq("derived.binary_classification", trade["binary_classification"], "positive")

    # from the phase inputs — the values the decision math consumed
    eq("derived.burry_score_from_p3_input", trade["burry_score"], 44.4)
    eq("derived.mhp_from_p4_input", trade["multi_horizon_price_framework"],
       P4_IN["multi_horizon_price_framework"])
    raises("reject.mhp_handwritten",
           lambda: load_q(tmp, base_qual(multi_horizon_price_framework={})),
           "script 導得出來的欄位")

    # engine-derived
    eq("derived.avg_confidence", trade["avg_confidence"], 0.764)
    eq("derived.final_score", trade["final_score"], 0.1718)

    # weights recovered from the engine's own step strings, not a restated constant
    eq("weights.from_calculation_steps", entry["active_weights_end_of_session"],
       {"Fundamentals": 0.25, "Sentiment": 0.15, "News": 0.20,
        "Technical": 0.25, "Valuation": 0.15})

    # canonical shapes
    eq("entry.key_count", len(entry), 11)
    eq("bundle.version", bundle["bundle_version"], B.BUNDLE_VERSION)

    # ── stale / mismatched engine artifact ───────────────────────────────────
    six_key = {k: ENGINE[k] for k in ("ticker", "decision_engine_version", "engine",
                                      "final_score", "final_decision", "calculation_steps")}
    write(tmp, "q2.json", base_qual())
    os.makedirs(os.path.join(tmp, "investment/invest_logs/decision_engine"), exist_ok=True)

    def _load_with_engine(eng):
        real_root = B.ROOT
        B.ROOT = tmp
        try:
            write(tmp, f"investment/invest_logs/decision_engine/{TICKER}_decision_engine.json",
                  eng)
            return B.load_artifacts(TICKER, DATE, p3_input="x", p4_input="y")
        finally:
            B.ROOT = real_root

    raises("engine.pre_v4126_subset_rejected", lambda: _load_with_engine(six_key),
           "V4.126.0 之前的舊檔")
    raises("engine.wrong_ticker_rejected",
           lambda: _load_with_engine({**ENGINE, "ticker": "OTHER"}),
           "被別支股票蓋掉")

if FAILS:
    print(f"✗ {len(FAILS)} failure(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ test_build_session_export: closed schema, single-sourcing and artifact gates hold")
