#!/usr/bin/env python3
"""Golden fixtures for Forward Expectations markdown renderer."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_report as rpt  # noqa: E402

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}")


SNAPSHOT = {
    "ticker": "ARM",
    "generated_at": "2026-06-16T01:18:18+00:00",
    "consensus_lane": {"revenue_cagr": 0.3842, "eps_cagr": 0.3999},
    "market_implied_lane": {"required_fcf_cagr": None, "out_of_range": False},
    "base_rate_lane": {"peer_rev_cagr_median": None},
    "independent_lane": {
        "available": False,
        "reason": "insufficient_evidence",
        "missing_numeric_drivers": ["royalty_bearing_units", "royalty_rate_or_value_per_unit"],
    },
    "forward_financial_bridge": {"available": True, "status": "available"},
    "operating_driver_scenarios": {
        "mode": "qualitative_driver_watchlist",
        "cases": [],
        "guidance_overlays": [],
        "qualitative_watchlist": [
            {"item": "royalty_bearing_units", "reason": "required_numeric_driver_or_evidence_missing"}
        ],
    },
    "future_price_range": {
        "available": True,
        "status": "available",
        "method": "eps_x_pe",
        "horizon_date": "2028-12-31",
        "range": {"low": 60.0, "base": 100.0, "high": 150.0},
        "cases": {
            "bear": {"target_price": 60.0, "upside_pct": -40.0, "metric": "eps_consensus", "metric_value": 4.0, "multiple": 15.0},
            "base": {"target_price": 100.0, "upside_pct": 0.0, "metric": "eps_consensus", "metric_value": 5.0, "multiple": 20.0},
            "bull": {"target_price": 150.0, "upside_pct": 50.0, "metric": "eps_consensus", "metric_value": 6.0, "multiple": 25.0},
        },
    },
    "expectations_gap": {
        "summary": {"status": "bridge_risk_only", "same_metric_gap_count": 0},
        "same_metric_gaps": [],
        "unavailable_same_metric": [
            {"metric": "revenue_cagr", "status": "no_same_metric_comparator"},
            {"metric": "eps_cagr", "status": "no_same_metric_comparator"},
        ],
        "financial_bridge_risks": [
            {
                "source": "forward_financial_bridge",
                "date": "2028-03-31",
                "check": "eps_vs_margin_net_income",
                "status": "wide_gap",
                "gap_pct": 1.377,
                "severity": "high",
            }
        ],
    },
}

print("Fixture A (bridge-risk-only report):")
md = rpt.render_markdown(SNAPSHOT)
check("has heading", "## Forward Expectations Shadow" in md)
check("has ticker", "Ticker: `ARM`" in md)
check("has consensus revenue", "Consensus revenue CAGR**: 38.4%" in md)
check("has independent blocked", "blocked (insufficient_evidence)" in md)
check("has gap status", "Status**: bridge_risk_only" in md)
check("has bridge risk", "2028-03-31: eps_vs_margin_net_income = wide_gap (138% gap)" in md)
check("has scenario section", "### Operating-Driver Scenarios" in md)
check("has scenario watchlist", "royalty_bearing_units: required_numeric_driver_or_evidence_missing" in md)
check("has future price section", "### Future Price Range" in md)
check("has future price row", "| bull | $150.00 | +50.0% | eps_consensus 6.00x | 25.00x |" in md)
check("has policy", "Does not alter fair value" in md)

print("Fixture B (same-metric gap table):")
snap_gap = {
    **SNAPSHOT,
    "expectations_gap": {
        "summary": {"status": "same_metric_gap_available", "same_metric_gap_count": 1},
        "same_metric_gaps": [
            {
                "metric": "revenue_cagr",
                "left": "consensus",
                "right": "base_rate",
                "left_value": 0.30,
                "right_value": 0.12,
                "delta": 0.18,
                "ratio": 2.5,
                "verdict": "consensus_above_base_rate",
            }
        ],
        "financial_bridge_risks": [],
    },
    "base_rate_lane": {"peer_rev_cagr_median": 0.12},
}
md_gap = rpt.render_markdown(snap_gap)
check("has table header", "| Metric | Left | Right | Delta | Ratio | Verdict |" in md_gap)
check("has revenue row", "| revenue_cagr | consensus 30.0% | base_rate 12.0% | 18.0% | 2.50x | consensus_above_base_rate |" in md_gap)
check("no bridge risk", "No bridge risk flags emitted." in md_gap)

print("Fixture B2 (numeric driver scenario table):")
snap_scenario = {
    **SNAPSHOT,
    "operating_driver_scenarios": {
        "mode": "driver_numeric_bear_base_bull",
        "cases": [
            {
                "case": "bear",
                "operating_drivers": {"revenue_cagr": 0.19},
                "driver_changes": [{"method": "bounded_driver_sensitivity"}],
            },
            {
                "case": "base",
                "operating_drivers": {"revenue_cagr": 0.24},
                "driver_changes": [{"method": "bounded_driver_sensitivity"}],
            },
            {
                "case": "bull",
                "operating_drivers": {"revenue_cagr": 0.29},
                "driver_changes": [{"method": "bounded_driver_sensitivity"}],
            },
        ],
    },
}
md_scenario = rpt.render_markdown(snap_scenario)
check("has scenario table", "| Case | Revenue CAGR Driver | Method |" in md_scenario)
check("has base scenario row", "| base | 24.0% | bounded_driver_sensitivity |" in md_scenario)
check("scenario no target price", "no fair value or target price is produced" in md_scenario)

print("Fixture B3 (driver-level scenario render):")
snap_driver = {
    **SNAPSHOT,
    "operating_driver_scenarios": {
        "mode": "driver_numeric_bear_base_bull",
        "cases": [{
            "case": "base",
            "operating_drivers": {
                "royalty_bearing_units": 100,
                "royalty_rate_or_value_per_unit": 0.025,
                "license_pipeline_conversion": 0.40,
                "data_center_segment_exposure": 0.18,
                "revenue_cagr": 0.24,
            },
            "driver_changes": [{"method": "driver_level_bounded_sensitivity"}],
        }],
    },
}
md_driver = rpt.render_markdown(snap_driver)
check("has driver-level table", "| Case | Drivers | Method |" in md_driver)
check("has driver-level values", "royalty_bearing_units=100" in md_driver)
check("has driver-level method", "driver_level_bounded_sensitivity" in md_driver)

print("Fixture C (bridge unavailable):")
snap_missing = {
    **SNAPSHOT,
    "forward_financial_bridge": {"available": False, "status": "insufficient_inputs", "missing_inputs": ["fcf_margin"]},
    "expectations_gap": {"summary": {"status": "comparison_unavailable"}, "financial_bridge_risks": []},
}
md_missing = rpt.render_markdown(snap_missing)
check("bridge unavailable", "Bridge unavailable: insufficient_inputs (fcf_margin)" in md_missing)
check("same metric unavailable", "Same-metric gap**: unavailable" in md_missing)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
