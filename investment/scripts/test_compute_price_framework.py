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
# archetype 權重表配平守恆：每個 archetype Σ=1.0
from compute_price_framework import ARCHETYPE_WEIGHTS, ANCHOR_WEIGHTS  # noqa: E402
for _name, _w in ARCHETYPE_WEIGHTS.items():
    eq(f"archetype.{_name}.sum", round(sum(_w.values()), 6), 1.0)
eq("live_weights.sum", round(sum(ANCHOR_WEIGHTS.values()), 6), 1.0)

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

    # quant artifact：schema / 六個 block / 不含 MHP（結構證明 quant 不吃 lane 輸入）
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
        "valuation_archetype_shadow", "valuation_explained_range"])

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

# ──────────────────────────────────────────────────────────────────────────────
if FAILS:
    print(f"✗ {len(FAILS)} regression(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ all golden + canonical valuation-pack fixtures pass")
