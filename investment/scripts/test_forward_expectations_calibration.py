#!/usr/bin/env python3
"""Golden fixtures for Forward Expectations calibration scaffold."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_calibration as cal  # noqa: E402

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


SNAPSHOT = {
    "ticker": "TEST",
    "run_id": "RUN1",
    "generated_at": "2026-01-01T00:00:00+00:00",
    "consensus_lane": {
        "revenue_cagr": 0.20,
        "eps_cagr": -0.10,
        "window_to": "2028-12-31",
    },
    "estimate_revision_snapshot": {
        "latest_year": {
            "date": "2027-12-31",
            "revenue_avg": 1000,
            "eps_avg": 5,
        },
    },
}

EARNINGS = {
    "as_of_date": "2026-03-31",
    "derived": {
        "yoy_growth": {
            "revenue_yoy": 0.10,
            "earnings_yoy": -0.20,
        },
    },
}

print("Fixture A (comparable consensus CAGR vs actual latest YoY):")
evaluation = cal.evaluate_snapshot(SNAPSHOT, EARNINGS)
rows = evaluation["rows"]
check("rows.count", len(rows), 4)
rev = rows[0]
check("rev.status", rev["status"], "comparable")
check("rev.ape", rev["absolute_pct_error"], 1.0)
check("rev.direction", rev["direction_hit"], True)
eps = rows[1]
check("eps.status", eps["status"], "comparable")
check("eps.ape", eps["absolute_pct_error"], 0.5)
check("eps.direction", eps["direction_hit"], True)

print("Fixture B (future level snapshots are not compared to latest YoY):")
level_rows = [row for row in rows if row["forecast_basis"] == "future_level_snapshot"]
check("level.count", len(level_rows), 2)
check("level.status", level_rows[0]["status"], "actual_not_comparable_yet")
check("level.actual", level_rows[0]["actual_value"], None)

print("Fixture C (missing actual degrades cleanly):")
missing = cal.evaluate_snapshot(SNAPSHOT, {})
comparable = [row for row in missing["rows"] if row["forecast_basis"] == "estimate_window_cagr"]
check("missing.status", comparable[0]["status"], "actual_not_available")
check("missing.error", comparable[0]["absolute_pct_error"], None)

print("Fixture D (summary insufficient sample):")
summary = cal.summarize(rows, min_n=3)
check("summary.status", summary["status"], "insufficient_sample")
check("summary.comparable", summary["comparable_count"], 2)
lane = summary["lane_summaries"][0]
check("lane.status", lane["status"], "insufficient_sample")

print("Fixture E (summary calibratable when n threshold met):")
many = rows[:2] * 3
summary_many = cal.summarize(many, min_n=3)
check("many.status", summary_many["status"], "calibratable")
rev_summary = [s for s in summary_many["lane_summaries"] if s["metric"] == "revenue_growth"][0]
check("many.rev.n", rev_summary["n"], 3)
check("many.rev.wape", rev_summary["wape_proxy"], 1.0)
check("many.rev.directional", rev_summary["directional_accuracy"], 1.0)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
