#!/usr/bin/env python3
"""Golden fixtures for Forward Expectations Gap."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_gap as gap  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want, tol=None):
    global PASS, FAIL
    ok = (abs(got - want) <= tol) if (tol is not None and got is not None) else (got == want)
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}: got {got!r}, want {want!r}")


CONSENSUS = {"available": True, "revenue_cagr": 0.30, "eps_cagr": 0.40}
MARKET = {"available": True, "required_fcf_cagr": 0.60, "out_of_range": True}
BASE = {"available": True, "peer_rev_cagr_median": 0.12}
INDEPENDENT = {"available": True, "revenue_cagr": 0.20}
BRIDGE = {
    "available": True,
    "warnings": ["negative_observed_tax_and_other_rate_non_operating_items_or_timing_effects"],
    "rows": [
        {"date": "2028-12-31", "consistency_checks": [
            {"check": "eps_vs_margin_net_income", "status": "wide_gap", "gap_pct": 1.2},
            {"check": "fcf_margin_sign", "status": "ok", "fcf_margin": 0.1},
        ]},
        {"date": "2029-12-31", "consistency_checks": [
            {"check": "fcf_margin_sign", "status": "negative_fcf", "fcf_margin": -0.05},
        ]},
    ],
}

print("Fixture A (same-metric revenue gaps):")
out = gap.build_expectations_gap(CONSENSUS, MARKET, INDEPENDENT, BASE, BRIDGE)
check("available", out["available"], True)
check("status", out["summary"]["status"], "same_metric_gap_available")
check("gap.count", out["summary"]["same_metric_gap_count"], 3)
check("consensus_base.metric", out["same_metric_gaps"][0]["metric"], "revenue_cagr")
check("consensus_base.delta", out["same_metric_gaps"][0]["delta"], 0.18)
check("ind_cons.delta", out["same_metric_gaps"][1]["delta"], -0.10)
check("ind_base.delta", out["same_metric_gaps"][2]["delta"], 0.08)

print("Fixture B (cross metric stays observation only):")
check("cross.count", len(out["cross_metric_observations"]), 2)
check("cross.policy", "no numeric gap" in out["cross_metric_observations"][0]["policy"], True)
fcf_gaps = [row for row in out["same_metric_gaps"] if row["metric"] == "fcf_cagr"]
check("fcf.no_same_metric_gap", fcf_gaps, [])

print("Fixture C (bridge risks are not valuation verdicts):")
check("bridge.risk.count", out["summary"]["bridge_risk_count"], 3)
check("bridge.warning", out["financial_bridge_risks"][0]["risk"], "negative_observed_tax_and_other_rate_non_operating_items_or_timing_effects")
check("bridge.wide_gap.severity", out["financial_bridge_risks"][1]["severity"], "high")
check("bridge.negative_fcf", out["financial_bridge_risks"][2]["status"], "negative_fcf")

print("Fixture D (independent unavailable degrades cleanly):")
no_ind = gap.build_expectations_gap(CONSENSUS, {}, {"available": False}, BASE, {})
check("no_ind.gap.count", no_ind["summary"]["same_metric_gap_count"], 1)
check("no_ind.unavailable.fcf", no_ind["unavailable_same_metric"][1]["metric"], "fcf_cagr")
check("no_ind.status", no_ind["summary"]["status"], "same_metric_gap_available")

print("Fixture E (bridge risk only):")
bridge_only = gap.build_expectations_gap({}, {}, {}, {}, BRIDGE)
check("bridge_only.available", bridge_only["available"], True)
check("bridge_only.status", bridge_only["summary"]["status"], "bridge_risk_only")
check("bridge_only.gaps", bridge_only["same_metric_gaps"], [])

print("Fixture F (nothing comparable):")
empty = gap.build_expectations_gap({}, {}, {}, {}, {})
check("empty.available", empty["available"], False)
check("empty.status", empty["summary"]["status"], "comparison_unavailable")
check("empty.unavailable.count", empty["summary"]["unavailable_metric_count"], 3)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
