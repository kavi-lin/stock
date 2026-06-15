#!/usr/bin/env python3
"""test_compute_price_framework.py — V3.48.0 golden-fixture regression test.

鎖定 engine 數學 baseline（3.45.3–3.48.0 全部人工驗算過）。任何未來改動若無意間
改變輸出，這裡先炸。純 stdlib、零網路（直接 call functions，不走 FMP fetch）。

Run: python3 investment/scripts/test_compute_price_framework.py   # rc=0 全過 / rc=1 fail
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compute_price_framework import (  # noqa: E402
    compute_archetype_shadow,
    compute_fair_value_range,
    compute_fair_value_summary,
    compute_implied_expectations,
    compute_mhp,
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

fvs = compute_fair_value_summary(HYPER["anchors"], 300.0)
eq("hyper.live_wfv", fvs["weighted_fair_value"], 225.71)
eq("hyper.live_verdict", fvs["verdict_band"], "overvalued")

rng = compute_fair_value_range(HYPER["anchors"], 300.0, HYPER["fred"])
eq("hyper.p25", rng["p25"], 144.44)
eq("hyper.p50", rng["p50"], 198.57)
eq("hyper.p75", rng["p75"], 344.0)
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
eq("hyper.shadow_wfv", sh["weighted_fair_value_shadow"], 270.52)
eq("hyper.flip", sh["flip_vs_live"], True)

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

# ──────────────────────────────────────────────────────────────────────────────
if FAILS:
    print(f"✗ {len(FAILS)} regression(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ all golden fixtures pass (4 fixtures, 26 asserts)")
