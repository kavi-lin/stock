#!/usr/bin/env python3
"""Golden fixtures for the Forward Expectations success-criteria gate (EXP-0.4)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_success_criteria as sc  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}: got {got!r}, want {want!r}")


def _by(name, result):
    return next(c for c in result["criteria"] if c["criterion"] == name)


def calibration(comparable, wape, directional, rows):
    return {
        "summary": {
            "comparable_count": comparable,
            "min_required_n": 15,
            "lane_summaries": [{"lane": "consensus", "metric": "revenue_growth",
                                "wape_proxy": wape, "directional_accuracy": directional}],
        },
        "evaluations": [{"rows": rows}],
    }


GOOD_SNAPSHOT = {
    "shadow_only": True,
    "evidence_contract": {"status": "pass", "accepted_count": 4, "rejected_count": 0},
    "evidence_inventory": {"summary": {"missing_source_count": 0}},
    "expectations_gap": {"summary": {"same_metric_gap_count": 1}},
    "future_price_range": {"changes_live_decision": False},
    "operating_driver_scenarios": {"changes_live_decision": False},
}

# ── insufficient sample blocks promotion even when metrics look good ────────────
small = calibration(3, 0.20, 1.0, [
    {"status": "comparable", "forecast_value": 0.22, "actual_value": 0.20},
])
r1 = sc.evaluate_success_criteria(small, GOOD_SNAPSHOT)
check("small: verdict insufficient_evidence", r1["verdict"], "insufficient_evidence")
check("small: not a shadow->live gate pass", r1["shadow_to_live_gate"], False)
check("small: sample criterion insufficient", _by("sample_sufficiency", small and r1)["status"], "insufficient_sample")
check("small: wape held insufficient_sample", _by("forecast_error_wape", r1)["status"], "insufficient_sample")
check("small: gap verifiable passes (snapshot)", _by("expectations_gap_verifiability", r1)["status"], "pass")
check("small: governance passes", _by("not_valuation_inflation", r1)["status"], "pass")

# ── sufficient sample + good metrics + clean snapshot -> pass ───────────────────
big_rows = [{"status": "comparable", "forecast_value": 0.21, "actual_value": 0.20} for _ in range(16)]
big = calibration(16, 0.18, 0.75, big_rows)
r2 = sc.evaluate_success_criteria(big, GOOD_SNAPSHOT)
check("big: verdict pass", r2["verdict"], "pass")
check("big: shadow->live gate true", r2["shadow_to_live_gate"], True)
check("big: wape pass", _by("forecast_error_wape", r2)["status"], "pass")
check("big: directional pass", _by("directional_accuracy", r2)["status"], "pass")
check("big: bias pass", _by("forecast_bias", r2)["status"], "pass")

# ── sufficient sample but WAPE over ceiling -> fail ─────────────────────────────
bad = calibration(16, 0.45, 0.75, big_rows)
r3 = sc.evaluate_success_criteria(bad, GOOD_SNAPSHOT)
check("bad_wape: verdict fail", r3["verdict"], "fail")
check("bad_wape: wape fail", _by("forecast_error_wape", r3)["status"], "fail")

# ── systematic optimism (bias) over ceiling -> fail ────────────────────────────
opt_rows = [{"status": "comparable", "forecast_value": 0.40, "actual_value": 0.20} for _ in range(16)]
opt = calibration(16, 0.20, 0.75, opt_rows)  # WAPE proxy still ok in summary, bias computed from rows
r4 = sc.evaluate_success_criteria(opt, GOOD_SNAPSHOT)
check("bias: fail on systematic optimism", _by("forecast_bias", r4)["status"], "fail")
check("bias: verdict fail", r4["verdict"], "fail")

# ── rejected evidence -> explainability fail ───────────────────────────────────
bad_snap = {**GOOD_SNAPSHOT, "evidence_contract": {"status": "degraded", "accepted_count": 2, "rejected_count": 1}}
r5 = sc.evaluate_success_criteria(big, bad_snap)
check("explainability fail on rejected evidence", _by("driver_explainability", r5)["status"], "fail")
check("verdict fail when explainability fails", r5["verdict"], "fail")

# ── no snapshot -> snapshot criteria insufficient_data, never silent pass ───────
r6 = sc.evaluate_success_criteria(big, None)
check("no snapshot: explainability insufficient_data", _by("driver_explainability", r6)["status"], "insufficient_data")
check("no snapshot: verdict insufficient_evidence", r6["verdict"], "insufficient_evidence")

# ── bias scores the deduped set: re-running the engine must not move the gate ────
def rerun_row(stamp, forecast):
    """One forecast, archived under a different snapshot vintage each re-run."""
    return {"ticker": "MU", "lane": "consensus", "metric": "revenue_growth",
            "forecast_basis": "estimate_window_cagr", "window_from": "2026-08-28",
            "window_to": "2030-08-28", "snapshot_generated_at": stamp,
            "status": "comparable", "forecast_value": forecast, "actual_value": 0.20}


# An optimistic call re-run 20 times, against one accurate call. Un-deduped, the
# optimistic forecast outvotes the accurate one 20:1 purely by re-run count.
skewed = [rerun_row(f"2026-{m:02d}-01", 0.60) for m in range(1, 21)]
skewed.append({**rerun_row("2026-01-01", 0.20), "ticker": "AAPL"})
one_per_forecast = {"summary": {"comparable_count": 16, "min_required_n": 15,
                                "lane_summaries": []},
                    "forecast_points": sc._bias_rows({"evaluations": [{"rows": skewed}]})[0],
                    "evaluations": [{"rows": skewed}]}
bias_dedup, n_dedup, basis_dedup = sc._signed_bias(one_per_forecast)
check("dedup keeps one row per distinct forecast", n_dedup, 2)
check("dedup basis reported", basis_dedup, "deduped_forecast_points")
check("re-runs no longer dominate the bias", bias_dedup, 1.0)  # mean of (+2.0, 0.0)

# The old behaviour averaged all 21 rows: 20 copies of the optimistic call at +2.0
# against one accurate call at 0.0, i.e. 1.905 — nearly double the deduped 1.0, moved
# entirely by how often the engine was re-run. No code path produces that any more.
raw_bias = round(sum((r["forecast_value"] - 0.20) / 0.20 for r in skewed) / len(skewed), 4)
check("un-deduped average was inflated by re-runs", raw_bias, 1.9048)
check("dedup pulls the bias back toward the evidence", bias_dedup < raw_bias, True)

# Rows without identity cannot be deduped — scoring them raw is correct, but the
# basis has to say so rather than collapsing 16 forecasts into one.
anon = [{"status": "comparable", "forecast_value": 0.21, "actual_value": 0.20} for _ in range(16)]
anon_bias, anon_n, anon_basis = sc._signed_bias({"evaluations": [{"rows": anon}]})
check("identity-less rows are not collapsed", anon_n, 16)
check("identity-less rows disclose their basis", anon_basis, "raw_evaluations_not_deduped")

# The gate must carry the basis so a legacy payload cannot pass as a deduped one.
check("bias criterion reports its basis",
      _by("forecast_bias", sc.evaluate_success_criteria(one_per_forecast, GOOD_SNAPSHOT))["bias_basis"],
      "deduped_forecast_points")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
