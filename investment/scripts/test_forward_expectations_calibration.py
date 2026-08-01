#!/usr/bin/env python3
"""Golden fixtures for Forward Expectations calibration scaffold (v2: same-basis realized
window CAGR + elapsed-window gate + latest-snapshot-per-ticker dedup)."""
import ast
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

print("Fixture D (future-level snapshots wait for complete same-basis FY actual):")
level_rows = [r for r in rows if r["forecast_basis"] == "future_level_snapshot"]
check("level.count", len(level_rows), 2)
check("level.status", level_rows[0]["status"], "actual_not_comparable_yet")

print("Fixture D2 (completed Q1-Q4 FY level becomes comparable):")
level_snapshot = {
    **SNAPSHOT,
    "generated_at": "2025-06-01T00:00:00+00:00",
    "estimate_revision_snapshot": {
        "latest_year": {"date": "2026-12-31", "revenue_avg": 1000, "eps_avg": 5},
    },
}
level_earnings = {
    "as_of_date": "2027-02-01",
    "quarterly_pnl": [
        {"fiscalYear": "2026", "period": q, "revenue": 250, "epsDiluted": 1.25}
        for q in ("Q1", "Q2", "Q3", "Q4")
    ],
}
realized_levels = cal._realized_fiscal_levels(level_earnings)
check("level.actual revenue sum", realized_levels[2026]["revenue_level"], 1000)
check("level.actual eps sum", realized_levels[2026]["eps_level"], 5.0)
level_eval = cal.evaluate_snapshot(level_snapshot, level_earnings)["rows"]
level_rev = [r for r in level_eval if r["metric"] == "revenue_level"][0]
check("level comparable", level_rev["status"], "comparable")
check("level same-basis actual", level_rev["actual_basis"], "quarterly_pnl_q1_q4_fiscal_sum")
check("level exact APE", level_rev["absolute_pct_error"], 0.0)
late_snapshot = {**level_snapshot, "generated_at": "2027-01-01T00:00:00+00:00"}
late_rev = [r for r in cal.evaluate_snapshot(late_snapshot, level_earnings)["rows"]
            if r["metric"] == "revenue_level"][0]
check("post-period snapshot rejected", late_rev["status"], "not_point_in_time_forecast")

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

print("Fixture G (calibration row dedup keeps earliest vintage, not latest rerun):")
vintage_rows = [
    {"ticker": "TEST", "lane": "consensus_revision", "metric": "revenue_level",
     "forecast_basis": "future_level_snapshot", "window_from": None, "window_to": "2027-12-31",
     "snapshot_generated_at": stamp, "forecast_value": value}
    for stamp, value in (("2026-01-01", 100), ("2026-06-01", 120))
]
kept_rows = cal._dedupe_forecast_rows(vintage_rows)
check("vintage dedup one row", len(kept_rows), 1)
check("vintage keeps earliest value", kept_rows[0]["forecast_value"], 100)

print("Fixture H (calibration index is a cache: same answer, never authoritative):")
with tempfile.TemporaryDirectory() as tmp:
    snap_dir = os.path.join(tmp, "forward_expectations")
    os.makedirs(snap_dir)
    for run, stamp in (("R1", "2026-01-01T00:00:00+00:00"), ("R2", "2026-02-01T00:00:00+00:00")):
        with open(os.path.join(snap_dir, f"TEST_{run}.json"), "w", encoding="utf-8") as fh:
            # Padding stands in for the evidence/provenance bulk the index drops.
            json.dump({**SNAPSHOT, "run_id": run, "generated_at": stamp,
                       "evidence_inventory": {"filler": "x" * 5000}}, fh)

    index_path = cal.default_index_path(snap_dir)
    check("index sits beside the dir, not inside it",
          os.path.dirname(index_path) == os.path.dirname(snap_dir.rstrip(os.sep)), True)

    raw = cal.run_calibration(snap_dir, tmp, 3, use_index=False)
    check("no index written when disabled", os.path.exists(index_path), False)

    first = cal.run_calibration(snap_dir, tmp, 3)
    check("index file created", os.path.exists(index_path), True)
    second = cal.run_calibration(snap_dir, tmp, 3)
    canon = lambda r: json.dumps(r, sort_keys=True, allow_nan=False)
    check("indexed run equals raw scan", canon(first), canon(raw))
    check("second indexed run is stable", canon(second), canon(raw))

    # The index must only carry the scored fields — never the audit bulk.
    with open(index_path, encoding="utf-8") as fh:
        index = json.load(fh)
    entry = index["entries"]["TEST_R1.json"]["snapshot"]
    check("index keeps only scored fields", sorted(entry) == sorted(
        k for k in cal.INDEX_FIELDS if k in entry), True)
    check("index drops evidence bulk", "evidence_inventory" in entry, False)

    # A rewritten snapshot must invalidate its entry, or calibration would score
    # a forecast that no longer exists on disk.
    edited = {**SNAPSHOT, "run_id": "R1", "generated_at": "2026-01-01T00:00:00+00:00"}
    edited["consensus_lane"] = {**SNAPSHOT["consensus_lane"], "revenue_cagr": 0.99}
    path = os.path.join(snap_dir, "TEST_R1.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(edited, fh)
    os.utime(path, (0, 0))  # force a signature change even on a fast filesystem
    refreshed = cal.run_calibration(snap_dir, tmp, 3)
    values = {row["forecast_value"] for ev in refreshed["evaluations"] for row in ev["rows"]}
    check("edited snapshot invalidates its entry", 0.99 in values, True)

    # An index this version cannot read is rebuilt, not trusted.
    with open(index_path, "w", encoding="utf-8") as fh:
        json.dump({"schema": "fe_calibration_index.v0", "fields": ["ticker"],
                   "entries": {"TEST_R1.json": {"sig": [1, 1.0], "snapshot": {"ticker": "GHOST"}}}}, fh)
    rebuilt = cal.run_calibration(snap_dir, tmp, 3)
    check("stale schema ignored", canon(rebuilt), canon(refreshed))

print("Fixture J (point-in-time gate on the window-CAGR path):")
# Written after the whole window closed — not a forecast, must never be scored.
hindsight = {**SNAPSHOT, "generated_at": "2027-06-01T00:00:00+00:00"}
rows_hindsight = cal.evaluate_snapshot(hindsight, EARNINGS)["rows"]
cagr_rows = [r for r in rows_hindsight if r["forecast_basis"] == "estimate_window_cagr"]
check("elapsed-window CAGR rejected", {r["status"] for r in cagr_rows},
      {"not_point_in_time_forecast"})
check("rejected row carries no actual", {r["actual_value"] for r in cagr_rows}, {None})
check("rejected row is not scored", {r["absolute_pct_error"] for r in cagr_rows}, {None})

# Written mid-window: the base FY had closed, the far end had not. Still scored, but the
# caveat has to travel with the row or the sample looks fully out-of-sample.
mid = {**SNAPSHOT, "generated_at": "2025-06-01T00:00:00+00:00"}
mid_rev = [r for r in cal.evaluate_snapshot(mid, EARNINGS)["rows"]
           if r["metric"] == "revenue_growth"][0]
check("mid-window forecast still comparable", mid_rev["status"], "comparable")
check("mid-window forecast flagged partially in-sample",
      mid_rev["point_in_time_caveat"], "base_fiscal_year_elapsed_at_forecast_time")
check("mid-window forecast still scored", mid_rev["absolute_pct_error"] is not None, True)

# A genuinely out-of-sample forecast keeps a clean record. Note this needs its own
# snapshot: the shared SNAPSHOT is dated 2026-01-01 against a window opening 2024-12-31,
# so it is itself a base-elapsed forecast and would not prove the clean path.
clean = {**SNAPSHOT, "generated_at": "2024-06-01T00:00:00+00:00"}
clean_rev = [r for r in cal.evaluate_snapshot(clean, EARNINGS)["rows"]
             if r["metric"] == "revenue_growth"][0]
check("out-of-sample forecast has no caveat", clean_rev["point_in_time_caveat"], None)
check("out-of-sample forecast still comparable", clean_rev["status"], "comparable")
check("scored caveat count surfaces in summary",
      cal.summarize([mid_rev, clean_rev], 1)["scored_with_point_in_time_caveat"], 1)
check("rejected count surfaces in summary",
      cal.summarize(cagr_rows, 1)["not_point_in_time_count"], len(cagr_rows))
# A caveated row that has not matured must not read as "no caveats" in the summary.
pending = {**mid_rev, "status": "actual_not_comparable_yet"}
pending_summary = cal.summarize([pending], 1)
check("pending caveat counted separately",
      pending_summary["pending_with_point_in_time_caveat"], 1)
check("pending caveat not counted as scored",
      pending_summary["scored_with_point_in_time_caveat"], 0)

print("Fixture K (CLI prints the scored set, not the whole ledger):")
with tempfile.TemporaryDirectory() as tmp:
    snap_dir = os.path.join(tmp, "snapshots")
    os.makedirs(snap_dir)
    for run, stamp in (("R1", "2026-01-01T00:00:00+00:00"), ("R2", "2026-02-01T00:00:00+00:00")):
        with open(os.path.join(snap_dir, f"TEST_{run}.json"), "w", encoding="utf-8") as fh:
            json.dump({**SNAPSHOT, "run_id": run, "generated_at": stamp}, fh)
    full = cal.run_calibration(snap_dir, tmp, 3)
    check("in-process result keeps evaluations", "evaluations" in full, True)
    check("scored points exposed alongside their count",
          len(full["forecast_points"]), full["forecast_point_count"])

    cli = cal.cli_payload(full)
    check("CLI drops per-snapshot rows", "evaluations" in cli, False)
    check("CLI keeps the scored set", len(cli["forecast_points"]), full["forecast_point_count"])
    check("CLI keeps the verdict", cli["summary"]["status"], full["summary"]["status"])
    check("CLI discloses what it dropped and how to get it",
          cli["evaluations_omitted"]["row_count"],
          sum(len(ev["rows"]) for ev in full["evaluations"]))
    check("CLI output is smaller than the full payload",
          len(json.dumps(cli)) < len(json.dumps(full)), True)
    check("--full-evaluations restores the untrimmed payload",
          json.dumps(cal.cli_payload(full, include_evaluations=True), sort_keys=True),
          json.dumps(full, sort_keys=True))

print("Fixture I (guard: INDEX_FIELDS must cover every snapshot field the module reads):")


def snapshot_fields_read(source: str) -> set:
    """Keys read off a variable named `snapshot`, via .get("k") or ["k"]."""
    found = set()
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get" and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "snapshot" and node.args
                and isinstance(node.args[0], ast.Constant)):
            found.add(node.args[0].value)
        elif (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
                and node.value.id == "snapshot" and isinstance(node.slice, ast.Constant)):
            found.add(node.slice.value)
    return found


# The detector itself must work, or this guard is decoration.
probe = snapshot_fields_read(
    'def f(snapshot):\n'
    '    a = snapshot.get("base_rate_lane")\n'
    '    b = snapshot["ticker"]\n'
    '    return a, b\n'
)
check("detector finds .get() key", "base_rate_lane" in probe, True)
check("detector finds [] key", "ticker" in probe, True)
check("detector flags a field missing from INDEX_FIELDS",
      bool(probe - set(cal.INDEX_FIELDS)), True)

# A field read here but absent from the index would silently return None for
# every indexed run — the lane would score nothing and report no error. Adding
# a field means adding it to INDEX_FIELDS and bumping INDEX_SCHEMA.
with open(cal.__file__, encoding="utf-8") as fh:
    module_fields = snapshot_fields_read(fh.read())
uncovered = sorted(module_fields - set(cal.INDEX_FIELDS))
check("no snapshot field read outside INDEX_FIELDS", uncovered, [])
check("INDEX_FIELDS has no unused entries",
      sorted(set(cal.INDEX_FIELDS) - module_fields), [])

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
