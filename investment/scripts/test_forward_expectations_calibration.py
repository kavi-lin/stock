#!/usr/bin/env python3
"""Golden fixtures for Forward Expectations calibration scaffold (v2: same-basis realized
window CAGR + elapsed-window gate + latest-snapshot-per-ticker dedup)."""
import json
import os
import sys
import tempfile

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


# A consensus forecast over the [2024, 2026] window: revenue CAGR +20%, EPS CAGR -10%.
SNAPSHOT = {
    "ticker": "TEST",
    "run_id": "RUN1",
    "generated_at": "2026-01-01T00:00:00+00:00",
    "consensus_lane": {
        "revenue_cagr": 0.20,
        "eps_cagr": -0.10,
        "window_from": "2024-12-31",
        "window_to": "2026-12-31",
    },
    "estimate_revision_snapshot": {
        "latest_year": {"date": "2027-12-31", "revenue_avg": 1000, "eps_avg": 5},
    },
}

# Realized per-FY growth. Window steps are FY2025 + FY2026.
#   revenue: geomean(1.10, 1.30) - 1 = 0.1958  (vs forecast 0.20)
#   netinc : geomean(0.95, 0.85) - 1 = -0.1014 (vs forecast -0.10)
EARNINGS = {
    "as_of_date": "2027-03-31",
    "annual_growth": [
        {"date": "2024-12-31", "fiscalYear": "2024", "revenueGrowth": 0.50, "netIncomeGrowth": 0.40},
        {"date": "2025-12-31", "fiscalYear": "2025", "revenueGrowth": 0.10, "netIncomeGrowth": -0.05},
        {"date": "2026-12-31", "fiscalYear": "2026", "revenueGrowth": 0.30, "netIncomeGrowth": -0.15},
    ],
}

print("Fixture geomean / realized-window helpers:")
check("geomean(1.1,1.3)", cal._geomean_cagr([0.10, 0.30]), 0.1958, tol=0.001)
check("geomean sign-flip → None", cal._geomean_cagr([0.10, -1.20]), None)
rcagr, rstatus = cal._realized_window_cagr(EARNINGS, "2024-12-31", "2026-12-31", "revenue_growth")
check("realized rev status", rstatus, "comparable")
check("realized rev cagr", rcagr, 0.1958, tol=0.001)

print("Fixture A (comparable: forecast CAGR vs realized SAME-window CAGR):")
evaluation = cal.evaluate_snapshot(SNAPSHOT, EARNINGS)
rows = evaluation["rows"]
cagr_rows = [r for r in rows if r["forecast_basis"] == "estimate_window_cagr"]
rev = [r for r in cagr_rows if r["metric"] == "revenue_growth"][0]
eps = [r for r in cagr_rows if r["metric"] == "eps_growth"][0]
check("rev.status", rev["status"], "comparable")
check("rev.actual_basis", rev["actual_basis"], "realized_window_cagr")
check("rev.actual ~0.196", rev["actual_value"], 0.1958, tol=0.001)
check("rev.ape small", rev["absolute_pct_error"], 0.021, tol=0.005)
check("rev.direction", rev["direction_hit"], True)
check("eps.status", eps["status"], "comparable")
check("eps.actual ~-0.101", eps["actual_value"], -0.1014, tol=0.001)
check("eps.direction (both down)", eps["direction_hit"], True)

print("Fixture B (forecast horizon not elapsed → not_comparable_yet, NOT scored):")
future = {**SNAPSHOT, "consensus_lane": {**SNAPSHOT["consensus_lane"], "window_to": "2030-12-31"}}
fut_rows = [r for r in cal.evaluate_snapshot(future, EARNINGS)["rows"]
            if r["forecast_basis"] == "estimate_window_cagr"]
check("future.status", fut_rows[0]["status"], "actual_not_comparable_yet")
check("future.no error", fut_rows[0]["absolute_pct_error"], None)
check("future.no actual", fut_rows[0]["actual_value"], None)

print("Fixture C (elapsed but a window FY missing → actual_basis_unavailable, no YoY fallback):")
gap_earn = {"as_of_date": "2027-03-31", "annual_growth": [
    {"date": "2024-12-31", "fiscalYear": "2024", "revenueGrowth": 0.50},
    {"date": "2026-12-31", "fiscalYear": "2026", "revenueGrowth": 0.30},  # 2025 missing
]}
gap_rows = [r for r in cal.evaluate_snapshot(SNAPSHOT, gap_earn)["rows"]
            if r["metric"] == "revenue_growth"]
check("gap.status", gap_rows[0]["status"], "actual_basis_unavailable")
check("no annual_growth → unavailable",
      cal._realized_window_cagr({}, "2024-12-31", "2026-12-31", "revenue_growth")[1],
      "actual_basis_unavailable")

print("Fixture D (future-level snapshots remain not_comparable_yet):")
level_rows = [r for r in rows if r["forecast_basis"] == "future_level_snapshot"]
check("level.count", len(level_rows), 2)
check("level.status", level_rows[0]["status"], "actual_not_comparable_yet")

print("Fixture E (summarize: insufficient sample / calibratable threshold):")
comparable_rows = [r for r in cagr_rows if r["status"] == "comparable"]
summary = cal.summarize(comparable_rows, min_n=3)
check("summary.comparable", summary["comparable_count"], 2)
check("summary.status", summary["status"], "insufficient_sample")
many = comparable_rows * 3
summary_many = cal.summarize(many, min_n=3)
check("many.status", summary_many["status"], "calibratable")
rev_summary = [s for s in summary_many["lane_summaries"] if s["metric"] == "revenue_growth"][0]
check("many.rev.n", rev_summary["n"], 3)

print("Fixture F (dedup: latest snapshot per ticker, re-runs don't inflate n):")
with tempfile.TemporaryDirectory() as tmp:
    for run, stamp in (("R1", "2026-01-01T00:00:00+00:00"),
                       ("R2", "2026-02-01T00:00:00+00:00"),
                       ("R3", "2026-03-01T00:00:00+00:00")):
        snap = {**SNAPSHOT, "run_id": run, "generated_at": stamp}
        with open(os.path.join(tmp, f"TEST_{run}.json"), "w", encoding="utf-8") as fh:
            json.dump(snap, fh)
    with open(os.path.join(tmp, "OTHER_R1.json"), "w", encoding="utf-8") as fh:
        json.dump({**SNAPSHOT, "ticker": "OTHER", "run_id": "R1", "generated_at": "2026-01-15T00:00:00+00:00"}, fh)
    kept = cal._latest_snapshot_per_ticker(tmp)
    check("dedup → 2 tickers (not 4 files)", len(kept), 2)
    test_keep = [s for s in kept if s["ticker"] == "TEST"][0]
    check("dedup keeps latest TEST run", test_keep["run_id"], "R3")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
