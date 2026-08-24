#!/usr/bin/env python3
"""test_compute_price_framework.py — V4.88.0 golden-fixture regression test.

鎖定 engine 數學 baseline（3.45.3–3.48.0 全部人工驗算過）。任何未來改動若無意間
改變輸出，這裡先炸。純 stdlib、零網路（直接 call functions 或 --no-fetch CLI）。
V4.88.0 起另鎖 staged mode：quant（Phase 1.5）+ mhp（Phase 2.4）合併輸出必須與
單發模式逐位元一致。

Run: python3 investment/scripts/test_compute_price_framework.py   # rc=0 全過 / rc=1 fail
"""
import copy
import json
import os
import subprocess
import sys
import tempfile
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from compute_price_framework import (  # noqa: E402
    MHP_QUALITATIVE_KEYS,
    QUANT_BLOCK_KEYS,
    QUANT_STAGE_SCHEMA,
    EngineInputError,
    build_full_output,
    build_quant_stage,
    build_valuation_pack,
    _block_manual_anchor_overrides,
    _supersede_vendor_dcf,
    build_explained_valuation_range,
    compute_archetype_shadow,
    compute_fair_value_range,
    compute_fair_value_summary,
    compute_forward_validation,
    compute_implied_expectations,
    compute_mhp,
    load_quant_stage,
    reconcile_confidence,
    resolve_effective_input,
    write_quant_artifact,
)

FAILS = []


def eq(label, got, want, tol=0.01):
    ok = (got == want) if not isinstance(want, float) else (
        got is not None and abs(got - want) <= tol)
    if not ok:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


# ── V4.131.13: extreme DCF must be tested against forward evidence ──────────
FV_PACK = {
    "current_price": 100.0,
    "score": -3.0,
    "anchors": {
        "dcf_self_built": {"value": 40.0, "status": "eligible"},
        "fwd_earnings_discounted": {
            "value": 95.0, "status": "ineligible",
            "reason": "cashflow_intrinsic_anchors_live:dcf_self_built",
            "calibration": {"analyst_count": 5, "horizon_years": 2.5},
        },
    },
}
FV_IMPLIED = {
    "implied_out_of_range": False,
    "market_implied_revenue": {
        "applicable": True, "implied_revenue_cagr": 0.25,
        "analyst_revenue_cagr": 0.22, "analyst_horizon_years": 3.0,
    },
}
FV_SHADOW = {"vs_current_pct_shadow": -5.0, "anchors_used_n": 3}
fv_pass = compute_forward_validation(FV_PACK, FV_IMPLIED, FV_SHADOW)
eq("forward.pass.status", fv_pass["status"], "PASS")
eq("forward.pass.softens", fv_pass["valuation_score_effective"], -1.0)
eq("forward.pass.no_t5", fv_pass["t5_hard_downgrade_eligible"], False)

fv_stretched = compute_forward_validation(
    FV_PACK,
    {**FV_IMPLIED, "market_implied_revenue": {
        **FV_IMPLIED["market_implied_revenue"], "implied_revenue_cagr": 0.40}},
    {"vs_current_pct_shadow": -35.0, "anchors_used_n": 3},
)
eq("forward.stretched.status", fv_stretched["status"], "STRETCHED")
eq("forward.stretched.one_support", fv_stretched["support_count"], 1)
eq("forward.stretched.softens", fv_stretched["valuation_score_effective"], -1.0)

fv_fail = compute_forward_validation(
    {**FV_PACK, "anchors": {**FV_PACK["anchors"], "fwd_earnings_discounted": {
        **FV_PACK["anchors"]["fwd_earnings_discounted"], "value": 60.0}}},
    {**FV_IMPLIED, "market_implied_revenue": {
        **FV_IMPLIED["market_implied_revenue"], "implied_revenue_cagr": 0.40}},
    {"vs_current_pct_shadow": -35.0, "anchors_used_n": 3},
)
eq("forward.fail.status", fv_fail["status"], "FAIL")
eq("forward.fail.keeps_raw", fv_fail["valuation_score_effective"], -3.0)
eq("forward.fail.t5", fv_fail["t5_hard_downgrade_eligible"], True)

fv_no_data = compute_forward_validation(
    {**FV_PACK, "anchors": {**FV_PACK["anchors"], "fwd_earnings_discounted": {
        "value": None, "status": "ineligible", "reason": "missing_or_nonpositive_value"}}},
    {"market_implied_revenue": {}},
    {"vs_current_pct_shadow": -35.0, "anchors_used_n": 3},
)
eq("forward.no_data.status", fv_no_data["status"], "NO_DATA")
eq("forward.no_data.no_false_kill", fv_no_data["t5_hard_downgrade_eligible"], False)


# ── Fixture 1: hypergrowth（3.46.0 實測 + #8a 折扣後 baseline） ────────────────
HYPER = {
    "ticker": "HYPER", "current_price": 300.0,
    "anchors": {"dcf_unlevered": 150.0, "dcf_levered": 140.0, "analyst_pt_consensus": 380.0,
                "peer_pe_implied": None, "owner_earnings_mult": None, "forecaster_blend": 320.0},
    "archetype_inputs": {"sector": "Technology", "revenue_yoy": 0.32, "fcf_margin": 0.03,
                         "eps_ttm": -0.5, "margin_sigma_pp": 2.0},
    "peer_ratios": {"peer_ev_ebitda_median": 25.0, "peer_ev_sales_median": 12.0, "peer_pb_median": 8.0},
    "self_ratios": {"ev_to_ebitda_ttm": 40.0, "ev_to_sales_ttm": 15.0, "roe_ttm": -0.05,
                    "book_value_per_share_ttm": 12.0},
    "ev_block": {"enterprise_value": 75e9, "net_debt": -3e9, "shares": 250e6},
    "beta": 1.2, "fred": {"treasury_10y": 0.041, "treasury_10y_real": 0.018},
    "key_levels": {"support": 270.0, "resistance": 340.0},
    "pattern_taxonomy": "consolidation", "smart_money_label": "neutral",
    "immediate_catalyst_5d": None,
    "volatility": {"sigma_daily": 0.035, "atr_14": 11.0, "momentum_20d_pct": 5.0},
}

# V4.69.0 8-anchor 權重下重驗算：available = dcf_u 150(.20) dcf_l 140(.10)
# analyst 380(.20) forecaster 320(.05)，Σw=0.55 → (30+14+76+16)/0.55 = 247.27
fvs = compute_fair_value_summary(HYPER["anchors"], 300.0)
eq("hyper.live_wfv", fvs["weighted_fair_value"], 265.0)
eq("hyper.live_verdict", fvs["verdict_band"], "overvalued")

rng = compute_fair_value_range(HYPER["anchors"], 300.0, HYPER["fred"])
eq("hyper.p25", rng["p25"], 145.83)
eq("hyper.p50", rng["p50"], 252.0)
eq("hyper.p75", rng["p75"], 362.0)
eq("hyper.range_method", rng["range_method"], "weighted_percentile")
eq("hyper.oe_linked", rng["owner_earnings_multiple_shadow"]["oe_mult_rate_linked"], 17.24)

mhp = compute_mhp(HYPER, fvs)
eq("hyper.band_lower", mhp["short_term_5d"]["band"][0], 269.95)
eq("hyper.band_upper", mhp["short_term_5d"]["band"][2], 330.05)
eq("hyper.mid_target", mhp["mid_term_60d"]["mid_target"], 308.8)        # 含 #8a 60/250 折扣
eq("hyper.mhp_signal", mhp["convergence"]["mhp_signal"], "wait_for_pullback")

sh = compute_archetype_shadow(HYPER, fvs)
eq("hyper.archetype", sh["archetype"], "hypergrowth")
eq("hyper.ev_ebitda_implied", sh["new_anchors"]["peer_ev_ebitda_implied"], 199.5)
eq("hyper.ev_sales_implied", sh["new_anchors"]["peer_ev_sales_implied"], 252.0)
eq("hyper.pb_roe", sh["new_anchors"]["pb_roe_justified"], None)          # ROE<0 → null
# V4.69.0 hypergrowth 新權重：dcf_u .10 dcf_l .05 analyst .20 forecaster .10
# ev_ebitda .15(199.5) ev_sales .20(252.0)，Σw=0.80 → 210.325/0.8 = 262.91
eq("hyper.shadow_wfv", sh["weighted_fair_value_shadow"], 262.91)
# live 247.27(-17.6% overvalued) vs shadow 262.91(-12.4% overvalued) → 同 band 不翻轉
eq("hyper.flip", sh["flip_vs_live"], False)

# ── Fixture 2: financial（pb_roe 手算 baseline） ──────────────────────────────
FIN = {
    "ticker": "BANK", "current_price": 60.0,
    "anchors": {"dcf_unlevered": 40.0, "analyst_pt_consensus": 70.0,
                "peer_pe_implied": 65.0, "forecaster_blend": 68.0},
    "archetype_inputs": {"sector": "Financial Services", "revenue_yoy": 0.06,
                         "fcf_margin": 0.20, "eps_ttm": 5.5, "margin_sigma_pp": 1.5},
    "self_ratios": {"roe_ttm": 0.13, "book_value_per_share_ttm": 48.0},
    "beta": 1.1, "fred": {"treasury_10y": 0.041},
}
fvs2 = compute_fair_value_summary(FIN["anchors"], 60.0)
sh2 = compute_archetype_shadow(FIN, fvs2)
eq("fin.archetype", sh2["archetype"], "financial")
eq("fin.pb_roe", sh2["new_anchors"]["pb_roe_justified"], 76.95)
eq("fin.shadow_verdict", sh2["verdict_band_shadow"], "undervalued")

# ── Fixture 3: reverse DCF（3.45.3 實測 baseline） ────────────────────────────
RD = {"current_price": 455.07, "fred": {"treasury_10y": 0.041},
      "reverse_dcf": {"fcf_base_per_share": 14.2, "actual_3y_fcf_cagr": 0.14,
                      "lane_fcf_estimate": 0.18}}
ie = compute_implied_expectations(RD)
eq("rdcf.implied", ie["implied_5y_fcf_cagr"], 0.1811, tol=0.001)
eq("rdcf.oor", ie["implied_out_of_range"], False)
eq("rdcf.wacc_source", ie["wacc_source"], "fred_10y")

# FCF ≤ 0 → null
ie2 = compute_implied_expectations({"current_price": 50.0, "fred": {},
                                    "reverse_dcf": {"fcf_base_per_share": -2.1}})
eq("rdcf.neg_fcf_null", ie2["implied_5y_fcf_cagr"], None)
eq("rdcf.fallback_wacc", ie2["wacc_source"], "fallback_fixed")

# ── Fixture 4: degraded（1 anchor / 無 vol / NEUTRAL catalyst） ───────────────
DEG = {"current_price": 50.0,
       "anchors": {"analyst_pt_consensus": 80.0},
       "key_levels": {}, "pattern_taxonomy": "downtrend", "smart_money_label": "distributing",
       "immediate_catalyst_5d": {"event": "FOMC", "date": "2026-06-12",
                                 "direction_lean": "NEUTRAL", "expected_move_pct": 4.0},
       "fred": {}}
fvs4 = compute_fair_value_summary(DEG["anchors"], 50.0)
rng4 = compute_fair_value_range(DEG["anchors"], 50.0, {})
mhp4 = compute_mhp(DEG, fvs4)
eq("deg.confidence", fvs4["confidence"], "low")
eq("deg.range_method", rng4["range_method"], None)
eq("deg.band", mhp4["short_term_5d"]["band"], [48.0, 50.0, 52.0])       # catalyst-only width
eq("deg.5d_conf", mhp4["short_term_5d"]["confidence"], "low")
eq("deg.low_conf_note", "僅供參考" in mhp4["convergence"]["signal_note"], True)

# ── Fixture 5: V4.46.0 confidence ← anchor dispersion (two-tier cv cap) ──────
# Tier LOW — ARM-shaped: 6 anchors span 50x, cv=1.20 (>= 0.60) -> cap to "low".
ARM_ANCHORS = {"dcf_unlevered": 8.0, "dcf_levered": 12.08, "analyst_pt_consensus": 163.75,
               "peer_pe_implied": 40.62, "owner_earnings_mult": 3.17, "forecaster_blend": 122.76}
fvs5 = compute_fair_value_summary(ARM_ANCHORS, 374.52)
rng5 = compute_fair_value_range(ARM_ANCHORS, 374.52, {})
eq("agree.count_conf_high", fvs5["confidence"], "high")          # before reconcile (6 anchors)
eq("agree.cv_extreme", rng5["anchor_dispersion_cv"] >= 0.60, True)
eq("agree.dispersion_ratio", rng5["dispersion_ratio"], round(163.75 / 3.17, 2))
reconcile_confidence(fvs5, rng5)
eq("agree.capped_low", fvs5["confidence"], "low")                # after reconcile
eq("agree.kept_count_based", fvs5["confidence_count_based"], "high")
eq("agree.capped_by_set", fvs5["confidence_capped_by"].startswith("anchor_dispersion"), True)

# Tier MEDIUM — AAPL-shaped: cv≈0.45 (0.35 <= cv < 0.60) -> cap high to "medium".
AAPL_ANCHORS = {"dcf_unlevered": 152.4, "dcf_levered": 145.7, "analyst_pt_consensus": 326.5,
                "peer_pe_implied": 226.3, "owner_earnings_mult": 29.2, "forecaster_blend": 208.3}
fvs7 = compute_fair_value_summary(AAPL_ANCHORS, 250.0)
rng7 = compute_fair_value_range(AAPL_ANCHORS, 250.0, {})
eq("agree.cv_moderate", 0.35 <= rng7["anchor_dispersion_cv"] < 0.60, True)
reconcile_confidence(fvs7, rng7)
eq("agree.capped_medium", fvs7["confidence"], "medium")
eq("agree.med_kept_count_based", fvs7["confidence_count_based"], "high")

# Tier NONE — converging anchors (cv < 0.35) keep their count-based confidence.
# V4.69.0：high 門檻升為 ≥6，補第 6 個 tight anchor 保持測試意圖（tight → high 不被 cap）
TIGHT = {"dcf_unlevered": 100.0, "dcf_levered": 102.0, "analyst_pt_consensus": 105.0,
         "peer_pe_implied": 98.0, "owner_earnings_mult": 101.0, "forecaster_blend": 103.0}
fvs6 = compute_fair_value_summary(TIGHT, 100.0)
rng6 = compute_fair_value_range(TIGHT, 100.0, {})
eq("agree.tight_cv_low", rng6["anchor_dispersion_cv"] < 0.35, True)
reconcile_confidence(fvs6, rng6)
eq("agree.tight_conf_kept", fvs6["confidence"], "high")
eq("agree.tight_no_cap", fvs6.get("confidence_capped_by"), None)

# ── Fixture 7 (V4.69.0): 全 8 anchor 齊備 — 新權重直算 + 門檻 ────────────────
FULL8 = {"dcf_unlevered": 100.0, "dcf_levered": 110.0, "dcf_self_built": 120.0,
         "analyst_pt_consensus": 130.0, "peer_pe_implied": 140.0, "comps_implied": 150.0,
         "owner_earnings_mult": 160.0, "forecaster_blend": 170.0}
fvs8 = compute_fair_value_summary(FULL8, 100.0)
# 20+11+18+26+21+15+8+8.5 = 127.5（Σw=1.0 無重分配）
eq("full8.wfv", fvs8["weighted_fair_value"], 128.25)
eq("full8.available", fvs8["anchors_available"], 8)
eq("full8.confidence", fvs8["confidence"], "high")
eq("full8.note", fvs8["methodology_note"].startswith("canonical family aggregation"), True)
eq("full8.verdict", fvs8["verdict_band"], "undervalued")
# 5 anchors → medium（新門檻 4-5）；3 → low
eq("mid5.confidence", compute_fair_value_summary(
    {k: FULL8[k] for k in list(FULL8)[:5]}, 100.0)["confidence"], "high")
eq("low3.confidence", compute_fair_value_summary(
    {k: FULL8[k] for k in list(FULL8)[:3]}, 100.0)["confidence"], "low")
# 權重表配平守恆。V4.108.0 起 fwd_earnings_discounted 是**條件錨**，刻意留在 1.0
# 預算之外：它的 live 資格只在 cashflow_intrinsic 整組（raw 合計 0.50）結構性缺席時
# 才開，所以它永遠擠不掉既有錨的權重；shadow 池同理（既有 11 根相對權重不動）。
# 這兩條斷言就是「新錨沒有偷偷改動舊配平」的守衛。
from compute_price_framework import (  # noqa: E402
    ANCHOR_WEIGHTS, ARCHETYPE_WEIGHTS, FWD_EARNINGS_RAW_WEIGHT, LEGACY_ANCHOR_WEIGHTS,
)
for _name, _w in ARCHETYPE_WEIGHTS.items():
    eq(f"archetype.{_name}.legacy_sum",
       round(sum(v for k, v in _w.items() if k != "fwd_earnings_discounted"), 6), 1.0)
eq("archetype.hypergrowth.conditional_anchor",
   ARCHETYPE_WEIGHTS["hypergrowth"]["fwd_earnings_discounted"], FWD_EARNINGS_RAW_WEIGHT)
for _name in ("mature_cashflow", "cyclical", "financial", "balanced"):
    eq(f"archetype.{_name}.no_conditional_anchor",
       ARCHETYPE_WEIGHTS[_name]["fwd_earnings_discounted"], 0.0)
eq("live_weights.legacy_sum", round(sum(LEGACY_ANCHOR_WEIGHTS.values()), 6), 1.0)
eq("live_weights.conditional_outside_budget",
   round(sum(ANCHOR_WEIGHTS.values()) - sum(LEGACY_ANCHOR_WEIGHTS.values()), 6),
   FWD_EARNINGS_RAW_WEIGHT)

# ── Fixture 8 (V4.70.0): anchor outlier trim（P0-3 審計修正）─────────────────
from compute_price_framework import trim_anchor_outliers  # noqa: E402

# NVDA-like：owner_earnings $31.80 遠低於錨中位數 → 剔除；其餘保留
NVDA_LIKE = {"dcf_unlevered": 247.42, "dcf_levered": 258.14, "dcf_self_built": None,
             "analyst_pt_consensus": None, "peer_pe_implied": 369.30, "comps_implied": None,
             "owner_earnings_mult": 31.80, "forecaster_blend": 347.15}
eff, trimmed = trim_anchor_outliers(NVDA_LIKE)
eq("trim.n_trimmed", len(trimmed), 1)
eq("trim.which", trimmed[0]["anchor"], "owner_earnings_mult")
eq("trim.eff_null", eff["owner_earnings_mult"], None)
eq("trim.eff_keep", eff["dcf_unlevered"], 247.42)
# 修剪後加權：dcf_u .20(247.42) dcf_l .10(258.14) peer_pe .15(369.30) fcast .05(347.15)
# Σw=0.50 → (49.484+25.814+55.395+17.3575)/0.50 = 296.10
fvs_t = compute_fair_value_summary(eff, 197.64)
eq("trim.wfv", fvs_t["weighted_fair_value"], 313.72)
eq("trim.available", fvs_t["anchors_available"], 4)
# 未修剪對照（含 $31.80，Σw=0.55）→ 272.07：壞錨拉低 $24
fvs_raw = compute_fair_value_summary(NVDA_LIKE, 197.64)
eq("trim.raw_wfv_contrast", fvs_raw["weighted_fair_value"], 311.04)

# 全體錨一致偏低（真高估）→ 中位數同步下移，不誤剪
LOW_ALL = {"dcf_unlevered": 90.0, "dcf_levered": 95.0, "dcf_self_built": 100.0,
           "analyst_pt_consensus": 110.0, "peer_pe_implied": None, "comps_implied": None,
           "owner_earnings_mult": None, "forecaster_blend": None}
_, trimmed_low = trim_anchor_outliers(LOW_ALL)
eq("trim.consensus_low_no_trim", len(trimmed_low), 0)

# n<4 不修剪（即使離群）
SPARSE = {"dcf_unlevered": 100.0, "dcf_levered": None, "dcf_self_built": None,
          "analyst_pt_consensus": 900.0, "peer_pe_implied": 105.0, "comps_implied": None,
          "owner_earnings_mult": None, "forecaster_blend": None}
_, trimmed_sparse = trim_anchor_outliers(SPARSE)
eq("trim.sparse_no_trim", len(trimmed_sparse), 0)

# 既有 fixtures 錨值都在 median×3 內 → 修剪為 no-op（HYPER 驗證）
eff_h, trimmed_h = trim_anchor_outliers(HYPER["anchors"])
eq("trim.hyper_noop", len(trimmed_h), 0)

# ── Fixture 9: canonical pack eligibility / provenance / shift gates ────────
STRICT_META = {
    name: {"provenance": "fixture", "as_of": dt.date.today().isoformat(),
           "correlation_key": "cashflow-fixture" if name.startswith("dcf_") else name}
    for name in FULL8
}
for _peer_anchor in ("peer_pe_implied", "comps_implied"):
    STRICT_META[_peer_anchor]["peer_count"] = 4
STRICT_META["forecaster_blend"].update({"confidence": "LOW", "usable_methods": 3})
pack = build_valuation_pack(FULL8, 100.0, anchor_meta=STRICT_META)
eq("pack.schema", pack["schema"], "valuation_pack.v1")
eq("pack.forecaster_gate", pack["anchors"]["forecaster_blend"]["status"], "ineligible")
eq("pack.forecaster_reason", pack["anchors"]["forecaster_blend"]["reason"],
   "low_forecast_confidence")
eq("pack.families", pack["families_present"],
   ["external_expectations", "fundamental", "relative"])

# ── V4.116.0: "the script never ran" vs "it ran and had nothing usable" ──────
# Both used to arrive as `missing_or_nonpositive_value`. That conflation is what
# let the 2026-08-09 NOW session skip Phase 1.5's two mandatory valuation scripts
# unnoticed: the engine correctly redistributed the ineligible anchors' weight,
# `owner_earnings_mult` went from a raw 0.05 to an effective 0.275, and it
# produced the `extreme_overvalued` verdict on its own. Nothing downstream could
# tell the two cases apart, so nothing could refuse the run.
import os as _os                                                    # noqa: E402
import tempfile as _tempfile                                        # noqa: E402
import time as _time                                                # noqa: E402
import json as _json                                                # noqa: E402
from compute_price_framework import (                               # noqa: E402
    ANCHOR_DROPPED_VALUE, SCRIPT_NOT_RUN, SCRIPT_SOURCED_ANCHORS,
    mark_unrun_anchor_scripts)

with _tempfile.TemporaryDirectory() as _fake_root:
    def _payload(anchor, ticker, value=None):
        """A credibly-shaped payload: this script's own keys, for this ticker."""
        spec = SCRIPT_SOURCED_ANCHORS[anchor]
        body = {k: None for k in spec["required_keys"]}
        body.update({"ticker": ticker, "asof": "2026-08-09", "degraded": value is None,
                     spec["value_key"]: value})
        return body

    def _artifact(anchor, ticker, age_days, body=None):
        rel = SCRIPT_SOURCED_ANCHORS[anchor]["artifact"].format(t=ticker)
        path = _os.path.join(_fake_root, rel)
        _os.makedirs(_os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fp:
            _json.dump(body if body is not None else _payload(anchor, ticker), fp)
        stamp = _time.time() - age_days * 86400
        _os.utime(path, (stamp, stamp))
        return path

    def _mark(ticker, anchors, meta=None):
        return mark_unrun_anchor_scripts(ticker, anchors, meta or {},
                                         base_dir=_fake_root)

    # No artifact at all — the real NOW case.
    _m = _mark("NOW", {"dcf_unlevered": 115.2})
    eq("script_gate.absent_dcf", _m["dcf_self_built"]["reason"], SCRIPT_NOT_RUN)
    eq("script_gate.absent_comps", _m["comps_implied"]["reason"], SCRIPT_NOT_RUN)
    # The validator's message names the fix; the command lives in the spec table
    # so the marker and the gate cannot drift to different commands.
    for _a, _spec in SCRIPT_SOURCED_ANCHORS.items():
        for _k in ("artifact", "command", "value_key", "required_keys"):
            if not _spec.get(_k):
                raise AssertionError(f"script_gate.spec_complete.{_a}: missing {_k}")
        if "{t}" not in _spec["command"] or "{t}" not in _spec["artifact"]:
            raise AssertionError(f"script_gate.spec_templated.{_a}: needs a {{t}} placeholder")
        if _spec["value_key"] not in _spec["required_keys"]:
            raise AssertionError(
                f"script_gate.value_key_required.{_a}: the value key must be one of the "
                f"keys a credible artifact has to carry")

    # V4.116.1 — presence is not enough. The shipped V4.116.0 check passed on
    # `echo '{}' > <T>_dcf_payload.json`, which matters because the behaviour this
    # gate exists to catch is an agent that answers a blocked gate by making the
    # input fit. A gate satisfiable by `touch` just picks a cheaper bypass.
    _artifact("dcf_self_built", "FAKE", age_days=0, body={})
    eq("script_gate.empty_json_rejected",
       _mark("FAKE", {})["dcf_self_built"]["reason"], SCRIPT_NOT_RUN)
    _artifact("dcf_self_built", "MISM", age_days=0,
              body=_payload("dcf_self_built", "SOMEONE_ELSE"))
    eq("script_gate.ticker_mismatch_rejected",
       _mark("MISM", {})["dcf_self_built"]["reason"], SCRIPT_NOT_RUN)

    # Ran and produced a usable number the anchor never received: a wiring bug,
    # reported separately because the fix is not "go run the script".
    _artifact("dcf_self_built", "DROP", age_days=0,
              body=_payload("dcf_self_built", "DROP", value=142.5))
    eq("script_gate.value_dropped",
       _mark("DROP", {})["dcf_self_built"]["reason"], ANCHOR_DROPPED_VALUE)

    # Artifact present and fresh: the script ran and had nothing usable to say,
    # which is a legitimate ineligibility and must NOT be reported as skipped.
    _artifact("dcf_self_built", "FRESH", age_days=0)
    _m = _mark("FRESH", {})
    eq("script_gate.fresh_artifact_not_flagged",
       _m.get("dcf_self_built", {}).get("reason"), None)
    eq("script_gate.other_anchor_still_flagged",
       _m["comps_implied"]["reason"], SCRIPT_NOT_RUN)

    # Stale artifact proves nothing about this session.
    _artifact("dcf_self_built", "STALE", age_days=9)
    eq("script_gate.stale_artifact_flagged",
       _mark("STALE", {})["dcf_self_built"]["reason"], SCRIPT_NOT_RUN)

    # A value present means it ran, whatever the artifact looks like.
    eq("script_gate.value_present_untouched",
       _mark("NOW", {"dcf_self_built": 120.0, "comps_implied": 88.0}), {})

    # An upstream reason is more specific and must survive.
    eq("script_gate.upstream_reason_wins",
       _mark("NOW", {}, {"dcf_self_built": {"reason": "low_confidence"}})
       ["dcf_self_built"]["reason"], "low_confidence")

    # Pure-function callers pass no ticker and must be unaffected.
    eq("script_gate.no_ticker_noop", _mark("", {}), {})

    # End to end: the marking has to reach the pack's anchor detail, or the
    # validator gate reads a reason that was never written.
    _pack = build_valuation_pack(
        {"dcf_unlevered": 100.0}, 100.0,
        anchor_meta=_mark("NOW", {"dcf_unlevered": 100.0}))
    eq("script_gate.reaches_pack",
       _pack["anchors"]["dcf_self_built"]["reason"], SCRIPT_NOT_RUN)


# Missing provenance/as_of cannot enter live.
pack_missing = build_valuation_pack({"dcf_unlevered": 100.0}, 100.0)
eq("pack.provenance_required", pack_missing["weighted_fair_value"], None)
eq("pack.provenance_reason", pack_missing["anchors"]["dcf_unlevered"]["reason"],
   "missing_provenance")

# Confirmed shift suppresses only PT that predates evidence; incomplete shift is advisory.
recent_pt = (dt.date.today() - dt.timedelta(days=32)).isoformat()
shift_date = (dt.date.today() - dt.timedelta(days=18)).isoformat()
pt_meta = {"analyst_pt_consensus": {"provenance": "fixture", "as_of": recent_pt}}
shift = {"status": "CONFIRMED", "evidence_date": shift_date, "provenance": "filing"}
pack_shift = build_valuation_pack({"analyst_pt_consensus": 150.0}, 100.0,
                                  anchor_meta=pt_meta, structural_shift=shift)
eq("pack.shift_suppressed", pack_shift["anchors"]["analyst_pt_consensus"]["reason"],
   "predates_structural_shift")
pack_advisory = build_valuation_pack({"analyst_pt_consensus": 150.0}, 100.0,
                                     anchor_meta=pt_meta,
                                     structural_shift={"status": "CONFIRMED"})
eq("pack.incomplete_shift_advisory", pack_advisory["anchors"]["analyst_pt_consensus"]["status"],
   "eligible")

stale_pt = (dt.date.today() - dt.timedelta(days=181)).isoformat()
pack_stale_pt = build_valuation_pack(
    {"analyst_pt_consensus": 150.0}, 100.0,
    anchor_meta={"analyst_pt_consensus": {"provenance": "fixture", "as_of": stale_pt}},
)
eq("pack.stale_pt_gate", pack_stale_pt["anchors"]["analyst_pt_consensus"]["reason"],
   "stale_analyst_pt")

pack_peer_missing_n = build_valuation_pack(
    {"comps_implied": 120.0}, 100.0,
    anchor_meta={"comps_implied": {"provenance": "fixture", "as_of": dt.date.today().isoformat()}},
)
eq("pack.peer_count_fail_closed", pack_peer_missing_n["anchors"]["comps_implied"]["reason"],
   "missing_peer_count")

# --self-assemble owns all live anchor values/meta; input-file injections are removed.
manual = {
    "anchors": {"dcf_self_built": 9999.0, "comps_implied": 8888.0},
    "anchor_meta": {
        "dcf_self_built": {"provenance": "fabricated", "as_of": dt.date.today().isoformat()},
        "comps_implied": {"provenance": "fabricated", "as_of": dt.date.today().isoformat(),
                          "peer_count": 99},
    },
}
blocked = _block_manual_anchor_overrides(manual)
eq("pack.manual_override_names", blocked, ["dcf_self_built", "comps_implied"])
eq("pack.manual_override_value_removed", manual["anchors"]["dcf_self_built"], None)
eq("pack.manual_override_meta_removed", manual["anchor_meta"]["comps_implied"], {})

# A live structural through-cycle DCF retains but supersedes opaque vendor DCFs.
vendor_meta = {
    "dcf_unlevered": {"provenance": "earnings_analyst_bundle", "as_of": "2026-06-25"},
    "dcf_levered": {"provenance": "earnings_analyst_bundle", "as_of": "2026-06-25"},
}
superseded = _supersede_vendor_dcf(vendor_meta, {
    "model_eligibility": {"eligible": True},
    "dcf": {"projection_mode": "structural_shift_through_cycle"},
})
eq("pack.vendor_dcf_superseded", superseded, ["dcf_unlevered", "dcf_levered"])
eq("pack.vendor_dcf_reason", vendor_meta["dcf_unlevered"]["reason"],
   "superseded_by_auditable_through_cycle_dcf")

# Legacy or failed self-built models cannot suppress an otherwise usable source.
legacy_meta = {"dcf_unlevered": {"provenance": "fixture"}}
eq("pack.vendor_dcf_legacy_kept", _supersede_vendor_dcf(legacy_meta, {
    "model_eligibility": {"eligible": True}, "dcf": {"projection_mode": "legacy_constant_ratio"},
}), [])
eq("pack.vendor_dcf_legacy_eligible_untouched", legacy_meta["dcf_unlevered"].get("eligible"), None)

# Eligible structural DCF owns primary FV; other methods explain the interval.
primary_meta = {
    "dcf_self_built": {
        "provenance": "valuation_modeler.dcf", "as_of": dt.date.today().isoformat(),
        "projection_mode": "structural_shift_through_cycle",
        "sensitivity_low": 693.74, "sensitivity_high": 853.60,
    },
    "owner_earnings_mult": {
        "provenance": "fixture.owner", "as_of": dt.date.today().isoformat(),
    },
}
primary_pack = build_valuation_pack(
    {"dcf_self_built": 762.13, "owner_earnings_mult": 832.50}, 812.0,
    anchor_meta=primary_meta,
)
eq("primary.method", primary_pack["primary_method"], "dcf_self_built")
eq("primary.fv", primary_pack["weighted_fair_value"], 762.13)
eq("primary.family_shadow", primary_pack["family_blended_fair_value"], 797.32)
eq("primary.dcf_weight", primary_pack["anchors"]["dcf_self_built"]["weight_effective"], 1.0)
eq("primary.owner_weight", primary_pack["anchors"]["owner_earnings_mult"]["weight_effective"], 0.0)

explained = build_explained_valuation_range(primary_pack, {
    "peer_pe_range": {
        "value": 1785.39, "eligible": True, "scope": "range_only", "peer_count": 3,
        "peers": {"SNDK": {}, "WDC": {}, "STX": {}},
        "limitations": ["adjacent storage mix"],
    },
})
eq("range.primary", explained["primary_fv"], 762.13)
eq("range.without_peer", explained["scenario_without_peer"], 797.32)
eq("range.with_peer", explained["scenario_with_peer"], 1291.35)
eq("range.low", explained["range_low"], 693.74)
eq("range.high", explained["range_high"], 1291.35)
eq("range.peers", explained["peer_symbols"], ["SNDK", "STX", "WDC"])

range_with_pt_meta = dict(primary_meta, analyst_pt_consensus={
    "provenance": "fixture.pt", "as_of": dt.date.today().isoformat(),
})
range_with_pt_pack = build_valuation_pack(
    {"dcf_self_built": 762.13, "owner_earnings_mult": 832.50,
     "analyst_pt_consensus": 1468.26}, 812.0,
    anchor_meta=range_with_pt_meta,
)
range_with_pt = build_explained_valuation_range(range_with_pt_pack, {
    "peer_pe_range": {
        "value": 1785.39, "eligible": True, "scope": "range_only", "peer_count": 3,
        "peers": {"SNDK": {}, "WDC": {}, "STX": {}},
    },
})
eq("range.external_anchor_extends_high", range_with_pt["range_high"], 1468.26)
eq("range.external_anchor_driver", range_with_pt["range_high_driver"],
   "anchor:analyst_pt_consensus")
eq("range.external_anchor_listed",
   range_with_pt["other_eligible_anchors"]["analyst_pt_consensus"], 1468.26)

# MHP may not resurrect a PT/forecaster anchor that canonical eligibility rejected.
gated_meta = {
    "analyst_pt_consensus": {"provenance": "fixture", "as_of": recent_pt},
    "forecaster_blend": {"provenance": "fixture", "as_of": dt.date.today().isoformat(),
                         "confidence": "LOW", "usable_methods": 3},
}
gated_pack = build_valuation_pack(
    {"analyst_pt_consensus": 150.0, "forecaster_blend": 160.0}, 100.0,
    anchor_meta=gated_meta, structural_shift=shift,
)
from compute_price_framework import fair_value_summary_from_pack  # noqa: E402
gated_fvs = fair_value_summary_from_pack(gated_pack)
gated_mhp = compute_mhp({"current_price": 100.0, "volatility": {}}, gated_fvs)
eq("pack.mhp_pt_suppressed", gated_mhp["mid_term_60d"]["pt_60d"], None)
eq("pack.mhp_forecaster_suppressed", gated_mhp["mid_term_60d"]["earnings_revision"], None)

# ── Fixture 10 (V4.88.0): staged mode — quant (Phase 1.5) + mhp (Phase 2.4) ──
# 驗收核心：固定輸入下「staged 兩段合併輸出 == 單發輸出」逐位元一致。唯一豁免欄位
# 是 valuation_pack.built_at（quant 段的時戳；兩次單發跑也不會相同）。
TODAY = dt.date.today().isoformat()
STAGED_META = {
    name: {"provenance": "fixture", "as_of": TODAY, "correlation_key": f"fixture:{name}"}
    for name in ("dcf_unlevered", "dcf_self_built", "analyst_pt_consensus",
                 "peer_pe_implied", "comps_implied", "owner_earnings_mult",
                 "forecaster_blend")
}
STAGED_META["peer_pe_implied"]["peer_count"] = 5
STAGED_META["comps_implied"]["peer_count"] = 4

# Phase 1.5 可得的部分（engine-owned quant，全部不需要 Phase 2 lane）
STAGED_QUANT_INPUT = {
    "ticker": "STAGE", "current_price": 100.0,
    "anchors": {"dcf_unlevered": 108.0, "dcf_levered": None, "dcf_self_built": 121.0,
                "analyst_pt_consensus": 132.0, "peer_pe_implied": 96.0,
                "comps_implied": 114.0, "owner_earnings_mult": 88.0,
                "forecaster_blend": 126.0},
    "anchor_meta": STAGED_META,
    "fred": {"treasury_10y": 0.041, "treasury_10y_real": 0.018},
    "reverse_dcf": {"fcf_base_per_share": 4.2, "actual_3y_fcf_cagr": 0.12,
                    "lane_fcf_estimate": 0.15},
    "archetype_inputs": {"sector": "Technology", "revenue_yoy": 0.11, "fcf_margin": 0.21,
                         "eps_ttm": 4.4, "margin_sigma_pp": 1.8},
    "peer_ratios": {"peer_ev_ebitda_median": 18.0, "peer_ev_sales_median": 6.0,
                    "peer_pb_median": 5.0},
    "self_ratios": {"ev_to_ebitda_ttm": 20.0, "ev_to_sales_ttm": 7.0, "roe_ttm": 0.19,
                    "book_value_per_share_ttm": 22.0, "pe_ttm": 22.7},
    "ev_block": {"enterprise_value": 26e9, "net_debt": 1.5e9, "shares": 250e6},
    "beta": 1.1,
    "volatility": {"sigma_daily": 0.022, "atr_14": 2.4, "momentum_20d_pct": 6.0},
}
# Phase 2 lane 才有的 qualitative（MHP 專用）
STAGED_QUALITATIVE = {
    "key_levels": {"support": 92.0, "resistance": 118.0},
    "pattern_taxonomy": "pullback_in_uptrend",
    "smart_money_label": "accumulating",
    "immediate_catalyst_5d": {"event": "Q3 earnings", "date": "2026-08-20",
                              "direction_lean": "BULLISH", "expected_move_pct": 4.0},
}
STAGED_SINGLE_INPUT = {**copy.deepcopy(STAGED_QUANT_INPUT), **copy.deepcopy(STAGED_QUALITATIVE)}

ENGINE_PATH = os.path.join(HERE, "compute_price_framework.py")


def run_engine(args, stdin_text=None):
    """CLI runner — (rc, parsed stdout JSON)。零網路（一律帶 --no-fetch）。"""
    proc = subprocess.run([sys.executable, ENGINE_PATH, "--no-fetch", *args],
                          input=stdin_text or "", capture_output=True, text=True)
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"_unparseable_stdout": proc.stdout, "_stderr": proc.stderr}
    return proc.returncode, payload


def normalized(out):
    """逐位元比較用：抹掉唯一的 wall-clock 欄位，其餘（含 key 順序）全保留。"""
    clone = copy.deepcopy(out)
    if isinstance(clone.get("valuation_pack"), dict):
        clone["valuation_pack"]["built_at"] = "<normalized>"
    return json.dumps(clone, ensure_ascii=False, sort_keys=False)


with tempfile.TemporaryDirectory() as tmp:
    single_path = os.path.join(tmp, "single.json")
    quant_in_path = os.path.join(tmp, "quant_in.json")
    qual_path = os.path.join(tmp, "qual.json")
    artifact_path = os.path.join(tmp, "artifact.json")
    for path, payload in ((single_path, STAGED_SINGLE_INPUT),
                          (quant_in_path, STAGED_QUANT_INPUT),
                          (qual_path, STAGED_QUALITATIVE)):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    rc_single, single_out = run_engine(["--from-file", single_path])
    eq("staged.single_rc", rc_single, 0)
    rc_quant, quant_art = run_engine(
        ["--from-file", quant_in_path, "--stage", "quant", "--out", artifact_path])
    eq("staged.quant_rc", rc_quant, 0)
    rc_mhp, staged_out = run_engine(
        ["--from-file", qual_path, "--stage", "mhp", "--from-quant", artifact_path])
    eq("staged.mhp_rc", rc_mhp, 0)

    # 非退化守衛：等價比對不能是兩個空殼相等
    eq("staged.fv_not_null", single_out["fair_value_summary"]["weighted_fair_value"] is not None,
       True)
    eq("staged.mhp_signal_present",
       single_out["multi_horizon_price_framework"]["convergence"]["mhp_signal"] is not None, True)
    eq("staged.equivalent_bitwise", normalized(staged_out), normalized(single_out))

    # quant artifact：schema / 七個 block / 不含 MHP（結構證明 quant 不吃 lane 輸入）
    eq("staged.artifact_schema", quant_art["schema"], QUANT_STAGE_SCHEMA)
    eq("staged.artifact_blocks", sorted(quant_art["quant_blocks"]), sorted(QUANT_BLOCK_KEYS))
    eq("staged.artifact_no_mhp", "multi_horizon_price_framework" in quant_art["quant_blocks"],
       False)
    eq("staged.artifact_persisted", quant_art["persisted_to"], artifact_path)
    eq("staged.artifact_on_disk", os.path.exists(artifact_path), True)
    with open(artifact_path, encoding="utf-8") as fh:
        eq("staged.artifact_file_matches_stdout", json.load(fh), quant_art)
    # 現價/sigma 凍結在 Phase 1.5：MHP 段不得重抓
    eq("staged.frozen_price", quant_art["effective_input"]["current_price"], 100.0)
    eq("staged.frozen_sigma", quant_art["effective_input"]["volatility"]["sigma_daily"], 0.022)

    # quant block 在 MHP 段 verbatim 併回（不是重算後剛好相等）
    for _block in QUANT_BLOCK_KEYS:
        eq(f"staged.verbatim.{_block}", staged_out[_block], quant_art["quant_blocks"][_block])

    # qualitative 全缺 → MHP 段降級不擋（drift=0、無 key level cap），quant block 照舊
    rc_bare, bare_out = run_engine(["--stage", "mhp", "--from-quant", artifact_path])
    eq("staged.bare_rc", rc_bare, 0)
    eq("staged.bare_drift", bare_out["multi_horizon_price_framework"]["short_term_5d"]["drift_sigma"],
       0.0)
    eq("staged.bare_no_cap",
       bare_out["multi_horizon_price_framework"]["short_term_5d"]["key_level_note"],
       "帶未觸及 key levels")
    eq("staged.bare_quant_intact", bare_out["valuation_pack"],
       quant_art["quant_blocks"]["valuation_pack"])

    # --from-quant 檔壞掉 → rc=1（絕不靜默 fallback 成「用 Phase 2.4 價格重算」）
    broken_path = os.path.join(tmp, "broken.json")
    with open(broken_path, "w", encoding="utf-8") as fh:
        fh.write("{not json")
    rc_broken, broken_out = run_engine(
        ["--from-file", qual_path, "--stage", "mhp", "--from-quant", broken_path])
    eq("staged.broken_rc", rc_broken, 1)
    eq("staged.broken_error", "unreadable" in broken_out.get("error", ""), True)

    wrong_schema_path = os.path.join(tmp, "wrong_schema.json")
    with open(wrong_schema_path, "w", encoding="utf-8") as fh:
        json.dump({"schema": "something_else.v1", "quant_blocks": {}}, fh)
    rc_wrong, wrong_out = run_engine(
        ["--stage", "mhp", "--from-quant", wrong_schema_path])
    eq("staged.wrong_schema_rc", rc_wrong, 1)
    eq("staged.wrong_schema_error", QUANT_STAGE_SCHEMA in wrong_out.get("error", ""), True)

    truncated_path = os.path.join(tmp, "truncated.json")
    truncated = copy.deepcopy(quant_art)
    truncated["quant_blocks"].pop("valuation_pack")
    with open(truncated_path, "w", encoding="utf-8") as fh:
        json.dump(truncated, fh)
    rc_trunc, trunc_out = run_engine(["--stage", "mhp", "--from-quant", truncated_path])
    eq("staged.truncated_rc", rc_trunc, 1)
    eq("staged.truncated_error", "valuation_pack" in trunc_out.get("error", ""), True)

    # 旗標誤用
    rc_no_quant, no_quant_out = run_engine(["--from-file", qual_path, "--stage", "mhp"])
    eq("staged.mhp_without_artifact_rc", rc_no_quant, 1)
    eq("staged.mhp_without_artifact_error",
       "requires --from-quant" in no_quant_out.get("error", ""), True)
    rc_stray, stray_out = run_engine(["--from-file", single_path, "--from-quant", artifact_path])
    eq("staged.stray_from_quant_rc", rc_stray, 1)
    eq("staged.stray_from_quant_error", "only applies" in stray_out.get("error", ""), True)

    # 無 ticker 且無 --out → 不寫檔但照樣輸出 artifact（測試/一次性用法）
    no_ticker = {k: v for k, v in STAGED_QUANT_INPUT.items() if k != "ticker"}
    rc_nt, nt_art = run_engine(["--stage", "quant"], stdin_text=json.dumps(no_ticker))
    eq("staged.no_ticker_rc", rc_nt, 0)
    eq("staged.no_ticker_not_persisted", nt_art["persisted_to"], None)

    # 單發模式輸出 shape 未變（向後相容：舊 key 一個不少、順序不變）
    eq("staged.single_shot_keys", list(single_out),
       ["engine", "ticker", "valuation_pack", "fair_value_summary", "fair_value_range",
        "multi_horizon_price_framework", "implied_expectations",
        "valuation_archetype_shadow", "forward_validation", "valuation_explained_range"])

    # In-process 等價（同一組函式，不經 CLI）：單發 == build_quant_stage → build_full_output
    inproc_single = copy.deepcopy(STAGED_SINGLE_INPUT)
    resolve_effective_input(inproc_single, no_fetch=True)
    inproc_quant = copy.deepcopy(STAGED_QUANT_INPUT)
    resolve_effective_input(inproc_quant, no_fetch=True)
    inproc_artifact = os.path.join(tmp, "inproc.json")
    write_quant_artifact(build_quant_stage(inproc_quant), inproc_artifact)
    eq("staged.inproc_equivalent",
       normalized(build_full_output(load_quant_stage(inproc_artifact), STAGED_QUALITATIVE)),
       normalized(build_full_output(build_quant_stage(inproc_single), inproc_single)))

    # current_price 缺 → 兩個 stage 都 rc=1（原有守衛不因分段而鬆掉）
    try:
        resolve_effective_input({"ticker": "X"}, no_fetch=True)
        eq("staged.missing_price_raises", "no_raise", "EngineInputError")
    except EngineInputError as exc:
        eq("staged.missing_price_raises", "current_price" in str(exc), True)

# MHP_QUALITATIVE_KEYS 是 compute_mhp 真正讀的 lane 欄位——名單漂掉會讓分段悄悄漏餵
eq("staged.qualitative_key_list", sorted(MHP_QUALITATIVE_KEYS),
   ["immediate_catalyst_5d", "key_levels", "pattern_taxonomy", "smart_money_label"])

# ── Fixture 11 (V4.108.0): anchor 9 — fwd_earnings_discounted ────────────────
# 真實回歸案例：AAOI 2026-08-07。八根 live anchor 全滅（DCF 為負、無可比同業、虧損
# 中所以 owner earnings / P/E 皆無定義）→ anchors_available=0 → insufficient_anchors
# 封死決策。第 9 根用分析師覆蓋足夠的最遠獲利年度把「市場在追的未來」折回今天。
from compute_price_framework import (  # noqa: E402
    FWD_BETA_FALLBACK,
    FWD_DISCOUNT_CLAMP,
    FWD_MAX_HORIZON_YEARS,
    FWD_MIN_ANALYSTS,
    TERMINAL_EV_SALES,
    TERMINAL_EV_SALES_SECTOR_TYPICAL,
    compute_fwd_earnings_anchor,
    compute_market_implied_revenue,
    evaluate_fwd_anchor_scope,
)

FIXED_TODAY = dt.date(2026, 8, 7)          # 固定日期：horizon 是天數差，不能隨執行日漂
AAOI_EST = [
    {"date": "2025-12-31", "epsAvg": -0.32563, "revenueAvg": 452665557,
     "numAnalystsEps": 4, "numAnalystsRevenue": 4},
    {"date": "2026-12-31", "epsAvg": 1.03327, "revenueAvg": 1040370400,
     "numAnalystsEps": 3, "numAnalystsRevenue": 3},
    {"date": "2027-12-31", "epsAvg": 5.72687, "revenueAvg": 2801711860,
     "numAnalystsEps": 3, "numAnalystsRevenue": 3},
    {"date": "2028-12-31", "epsAvg": 11.6, "revenueAvg": 4166800000,
     "numAnalystsEps": 1, "numAnalystsRevenue": 1},          # 單一分析師 → 不可用
]
fwd = compute_fwd_earnings_anchor(AAOI_EST, today=FIXED_TODAY, beta=3.687, treasury_10y=0.0463)
# 手算：FY27 EPS 5.72687 × justified PE 35（成長 455% 觸頂 clamp）
#       ÷ (1 + 0.2122)^1.39904 = 200.4405 / 1.30899 = 153.13
eq("fwd.value", fwd["value"], 153.13)
eq("fwd.target_year", fwd["target_fiscal_year"], "2027-12-31")   # 最遠的合格年度，非最近
eq("fwd.analysts", fwd["analyst_count"], 3)
eq("fwd.horizon", fwd["horizon_years"], 1.399)
eq("fwd.pe_clamped", fwd["justified_pe"], 35.0)
eq("fwd.growth_source", fwd["growth_source"], "eps_cagr")
eq("fwd.discount_rate", fwd["discount_rate"], 0.2122)           # 高 beta → 21% 門檻
# 校準原料：pre-profit 標的成長率必然爆表 → 上限恆綁。留下未夾前的值與綁定端，
# shadow_report 的 FWD_PE_CLAMP 校準才能用 grep 回答「上限綁到的頻率」
eq("fwd.pe_clamp_binding", fwd["pe_clamp_binding"], "upper")
eq("fwd.pe_raw_kept", fwd["justified_pe_raw"], 454.63, tol=0.5)

# 目標年退回第一個未來年度時，成長率的分母是最近的**已實現**年度（EPS 為負）→
# 自動退回營收 CAGR，而不是放棄
thin_fy27 = copy.deepcopy(AAOI_EST)
thin_fy27[2]["numAnalystsEps"] = 2
fwd_thin = compute_fwd_earnings_anchor(thin_fy27, today=FIXED_TODAY, beta=3.687,
                                       treasury_10y=0.0463)
eq("fwd.thin_target_steps_back", fwd_thin["target_fiscal_year"], "2026-12-31")
eq("fwd.thin_growth_source", fwd_thin["growth_source"], "revenue_cagr")
eq("fwd.thin_has_value", fwd_thin["value"] is not None, True)

# Gates：全部薄覆蓋 / 無未來預估 / 全年度虧損 → null + reason（不是例外）
eq("fwd.gate_thin_all", compute_fwd_earnings_anchor(
    [dict(r, numAnalystsEps=1) for r in AAOI_EST], today=FIXED_TODAY)["reason"],
   f"no_estimate_year_with_positive_eps_and_{FWD_MIN_ANALYSTS}_analysts"
   f"_within_{FWD_MAX_HORIZON_YEARS:g}y")
eq("fwd.gate_no_future", compute_fwd_earnings_anchor(
    AAOI_EST[:1], today=FIXED_TODAY)["reason"], "no_future_analyst_estimates")
eq("fwd.gate_all_loss", compute_fwd_earnings_anchor(
    [dict(r, epsAvg=-1.0) for r in AAOI_EST], today=FIXED_TODAY)["value"], None)
# horizon 上限：只剩 3.5 年外的年度合格 → 不可用（沒人預測那麼遠）
far = [{"date": "2030-12-31", "epsAvg": 20.0, "revenueAvg": 9e9, "numAnalystsEps": 5}]
eq("fwd.gate_horizon", compute_fwd_earnings_anchor(far, today=FIXED_TODAY)["value"], None)
# 折現率下限：低 beta 的題材股也不得低於 10%
eq("fwd.discount_floor", compute_fwd_earnings_anchor(
    AAOI_EST, today=FIXED_TODAY, beta=0.2, treasury_10y=0.01)["discount_rate"], 0.10)
eq("fwd.discount_floor_flagged", compute_fwd_earnings_anchor(
    AAOI_EST, today=FIXED_TODAY, beta=0.2, treasury_10y=0.01)["discount_clamp_binding"], "lower")
# 高 beta 觸頂（CRWV 實測 beta 7.41）→ 記錄綁定端，讓「0.30 上限在處理什麼」可查
eq("fwd.discount_cap_flagged", compute_fwd_earnings_anchor(
    AAOI_EST, today=FIXED_TODAY, beta=7.41, treasury_10y=0.0463)["discount_clamp_binding"], "upper")

# 無效 beta 不得被當成「市場級風險」。SPCX 實測 beta=0（IPO 2026-06-12，歷史不足兩
# 個月）——舊行為讓它吃到 10% 折現率下限，是整組樣本裡最寬鬆的一檔；那是把資料缺陷
# 渲染成低風險，與 v4.106.0「靜默 fail closed 在最新資料上」同一個形狀。
for _label, _beta in (("zero", 0.0), ("missing", None), ("negative", -1.2)):
    _d = compute_fwd_earnings_anchor(AAOI_EST, today=FIXED_TODAY, beta=_beta,
                                     treasury_10y=0.0463)
    eq(f"fwd.beta_{_label}_falls_back", _d["beta_used"], FWD_BETA_FALLBACK)
    eq(f"fwd.beta_{_label}_source", _d["beta_source"], "population_median_fallback")
    # 關鍵斷言：fallback 必須比下限**嚴格**（否則等於沒修）
    eq(f"fwd.beta_{_label}_not_floor", _d["discount_rate"] > FWD_DISCOUNT_CLAMP[0], True)
_valid = compute_fwd_earnings_anchor(AAOI_EST, today=FIXED_TODAY, beta=3.687,
                                     treasury_10y=0.0463)
eq("fwd.beta_valid_source", _valid["beta_source"], "profile")
eq("fwd.beta_valid_used", _valid["beta_used"], 3.687)

# Scope gate — 只填真空、不排擠
eq("fwd.scope_vacuum", evaluate_fwd_anchor_scope(
    {"anchors": {"analyst_pt_consensus": 160.0}}), (True, None))
eq("fwd.scope_blocked_by_dcf", evaluate_fwd_anchor_scope(
    {"anchors": {"dcf_self_built": 88.0}})[0], False)
eq("fwd.scope_blocked_reason", evaluate_fwd_anchor_scope(
    {"anchors": {"dcf_self_built": 88.0}})[1], "cashflow_intrinsic_anchors_live:dcf_self_built")
# 值存在但來源自己判定不合格的 DCF 不算「還活著」→ 真空成立
eq("fwd.scope_ineligible_dcf_is_vacuum", evaluate_fwd_anchor_scope(
    {"anchors": {"dcf_self_built": 88.0},
     "anchor_meta": {"dcf_self_built": {"model_eligibility": {"eligible": False}}}})[0], True)
eq("fwd.scope_profitable_issuer", evaluate_fwd_anchor_scope(
    {"anchors": {}, "archetype_inputs": {"eps_ttm": 4.4}}),
   (False, "profitable_issuer_shadow_only"))

# strict metadata：覆蓋數 / horizon 缺 → fail closed（與 peer_count 同一紀律）
AAOI_META_OK = {
    "analyst_pt_consensus": {"provenance": "earnings_analyst_bundle.pt_news",
                             "as_of": dt.date.today().isoformat()},
    # 與 assemble_inputs 實際寫入的 meta 同形（校準欄位一起帶，否則 pack 的
    # calibration 投影不會被這組 fixture 測到）
    "fwd_earnings_discounted": {"provenance": "fmp_analyst_estimates.annual",
                                "as_of": dt.date.today().isoformat(),
                                "analyst_count": 3, "horizon_years": 1.399,
                                "target_fiscal_year": "2027-12-31", "target_eps": 5.7269,
                                "justified_pe": 35.0, "justified_pe_raw": 454.63,
                                "pe_clamp_binding": "upper", "discount_rate": 0.2122,
                                "growth_source": "eps_cagr"},
}
eq("fwd.strict_missing_count", build_valuation_pack(
    {"fwd_earnings_discounted": 153.13}, 135.12,
    anchor_meta={"fwd_earnings_discounted": {"provenance": "f",
                                             "as_of": dt.date.today().isoformat()}},
)["anchors"]["fwd_earnings_discounted"]["reason"], "missing_analyst_count")
eq("fwd.strict_thin_count", build_valuation_pack(
    {"fwd_earnings_discounted": 153.13}, 135.12,
    anchor_meta={"fwd_earnings_discounted": {"provenance": "f", "analyst_count": 2,
                                             "as_of": dt.date.today().isoformat(),
                                             "horizon_years": 1.4}},
)["anchors"]["fwd_earnings_discounted"]["reason"],
   f"fewer_than_{FWD_MIN_ANALYSTS}_analysts_on_target_year")

# AAOI 端到端：0 根 → 2 根、1 family → 2 family、cap 解除但標記 sell_side_only
aaoi_pack = build_valuation_pack({"analyst_pt_consensus": 160.0,
                                  "fwd_earnings_discounted": 153.13}, 135.12,
                                 anchor_meta=AAOI_META_OK)
aaoi_fvs = fair_value_summary_from_pack(aaoi_pack)
eq("aaoi.anchors_available", aaoi_fvs["anchors_available"], 2)      # ≥2 → cap 不再觸發
eq("aaoi.families", aaoi_pack["families_present"],
   ["external_expectations", "fundamental"])
eq("aaoi.confidence", aaoi_pack["confidence"], "medium")            # 2 family → medium
eq("aaoi.fv", aaoi_pack["weighted_fair_value"], 156.56)
eq("aaoi.verdict", aaoi_pack["verdict_band"], "undervalued")
eq("aaoi.sell_side_only", aaoi_pack["evidence_independence"]["sell_side_only"], True)
eq("aaoi.fvs_sell_side_only", aaoi_fvs["sell_side_only"], True)
eq("aaoi.fvs_pre_profit_live", aaoi_fvs["pre_profit_anchor_live"], True)
# calibration 進 pack（export 只帶 pack；沒有這格，未來要從 history.json 做結果
# 回測就得回頭重算輸入）。八根常規錨沒有校準原料 → None，不污染 entry
eq("aaoi.calibration_in_pack",
   aaoi_pack["anchors"]["fwd_earnings_discounted"]["calibration"]["target_eps"], 5.7269)
eq("aaoi.calibration_absent_elsewhere",
   aaoi_pack["anchors"]["analyst_pt_consensus"]["calibration"], None)
# |score| ≥ 2 需要兩個同向 family；賣方依賴不改分數，只改籌碼（governor 的事）
eq("aaoi.score", aaoi_pack["score"], 1.0)

# 一根獨立錨進來 → 不再是 sell-side-only（旗標不是「有沒有 pre-profit 錨」的別名）
mixed_meta = dict(AAOI_META_OK, comps_implied={
    "provenance": "valuation_modeler.comps", "as_of": dt.date.today().isoformat(),
    "peer_count": 4})
mixed_pack = build_valuation_pack(
    {"analyst_pt_consensus": 160.0, "fwd_earnings_discounted": 153.13,
     "comps_implied": 120.0}, 135.12, anchor_meta=mixed_meta)
eq("aaoi.mixed_not_sell_side_only",
   mixed_pack["evidence_independence"]["sell_side_only"], False)

# 獲利股不受影響：fwd 值存在但 scope 判 shadow → live blend 與沒有第 9 根時逐位元相同
PROFITABLE = {"dcf_self_built": 120.0, "analyst_pt_consensus": 130.0,
              "peer_pe_implied": 140.0}
prof_meta = {
    "dcf_self_built": {"provenance": "valuation_modeler.dcf",
                       "as_of": dt.date.today().isoformat()},
    "analyst_pt_consensus": {"provenance": "fixture", "as_of": dt.date.today().isoformat()},
    "peer_pe_implied": {"provenance": "fixture", "as_of": dt.date.today().isoformat(),
                        "peer_count": 5},
}
prof_base = build_valuation_pack(PROFITABLE, 100.0, anchor_meta=prof_meta)
prof_shadowed = build_valuation_pack(
    {**PROFITABLE, "fwd_earnings_discounted": 999.0}, 100.0,
    anchor_meta={**prof_meta, "fwd_earnings_discounted": {
        "provenance": "fmp_analyst_estimates.annual", "as_of": dt.date.today().isoformat(),
        "analyst_count": 5, "horizon_years": 1.2,
        "eligible": False, "reason": "cashflow_intrinsic_anchors_live:dcf_self_built"}})
eq("fwd.profitable_live_fv_unchanged", prof_shadowed["weighted_fair_value"],
   prof_base["weighted_fair_value"])
eq("fwd.profitable_shadow_reason",
   prof_shadowed["anchors"]["fwd_earnings_discounted"]["reason"],
   "cashflow_intrinsic_anchors_live:dcf_self_built")
eq("fwd.profitable_not_sell_side_only",
   prof_shadowed["evidence_independence"]["sell_side_only"], False)

# 市場隱含營收路徑（reverse DCF 對 FCF ≤ 0 無定義時的替代 diagnostic）
mir = compute_market_implied_revenue({
    "self_ratios": {"ev_to_sales_ttm": 16.33062489219256},
    "revenue_path": {"analyst_revenue_cagr": 1.4894, "horizon_years": 2.0}})
eq("mir.multiple", mir["required_revenue_multiple"], 4.08)     # 16.33 / 4.0
eq("mir.cagr", mir["implied_revenue_cagr"], 0.3249)            # 4.0827^(1/5) − 1
eq("mir.verdict", mir["verdict"], "market_below_sell_side")    # 32% ≪ 賣方 149%
eq("mir.kill_seed_present", "32%" in mir["red_team_kill_seed"], True)
# 雙 terminal：這個假設的槓桿極大（4x 需 32% / 8x 需 15%），藏在單一常數裡等於把結論
# 藏起來。2026-08-07 量測成熟獲利公司 median EV/S：半導體 13.9 / 通訊設備 8.3 /
# 軟體 8.0 / 工業 2.8——4.0 是刻意保守的規範性假設，不是實測中樞。
eq("mir.sector_terminal_reported", mir["terminal_ev_to_sales_sector_typical"],
   TERMINAL_EV_SALES_SECTOR_TYPICAL)
eq("mir.sector_cagr", mir["implied_revenue_cagr_sector"], 0.1533, tol=0.001)
eq("mir.sector_easier_than_conservative",
   mir["implied_revenue_cagr_sector"] < mir["implied_revenue_cagr"], True)
eq("mir.both_in_note", "8x 則需 15%" in mir["note"], True)
# EV/S 已在科技中樞之下 → sector 情境不要求任何營收擴張（倍數不得被要求「反向擴張」）
_mid = compute_market_implied_revenue({"self_ratios": {"ev_to_sales_ttm": 6.0}})
eq("mir.sector_floor_at_one", _mid["required_revenue_multiple_sector"], 1.0)
eq("mir.sector_floor_zero_cagr", _mid["implied_revenue_cagr_sector"], 0.0)
eq("mir.conservative_still_positive", _mid["implied_revenue_cagr"] > 0, True)
eq("mir.terminal_ordering", TERMINAL_EV_SALES < TERMINAL_EV_SALES_SECTOR_TYPICAL, True)
eq("mir.below_terminal", compute_market_implied_revenue(
    {"self_ratios": {"ev_to_sales_ttm": 2.5}})["implied_revenue_cagr"], 0.0)
eq("mir.unavailable", compute_market_implied_revenue({})["reason"],
   "ev_to_sales_ttm_unavailable")
# FCF ≤ 0 的 implied_expectations 不再空手而歸：改掛營收 kill seed
ie_pre_profit = compute_implied_expectations({
    "current_price": 135.12, "fred": {"treasury_10y": 0.0463},
    "reverse_dcf": {"fcf_base_per_share": -2.1},
    "self_ratios": {"ev_to_sales_ttm": 16.33062489219256}})
eq("mir.ie_fallback_cagr", ie_pre_profit["implied_5y_fcf_cagr"], None)
eq("mir.ie_revenue_mode",
   ie_pre_profit["market_implied_revenue"]["implied_revenue_cagr"], 0.3249)
eq("mir.ie_kill_seed", ie_pre_profit["red_team_kill_seed"].startswith("IF 未來 2 季營收"), True)

# ──────────────────────────────────────────────────────────────────────────────
if FAILS:
    print(f"✗ {len(FAILS)} regression(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ all golden + canonical valuation-pack fixtures pass")
