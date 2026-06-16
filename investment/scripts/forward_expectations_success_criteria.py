#!/usr/bin/env python3
"""Forward Expectations success-criteria evaluator (EXP-0.4).

Defines the falsifiable yardstick for the forward layer. Success is NOT "valuation
went up" — it is driver explainability, forecast error, directional hit rate, bias,
source completeness, and expectations-gap verifiability. This is the read-only gate
that EXP-4.5 (shadow -> live) must clear before any live wiring.

It consumes:
  - a calibration result (forward_expectations_calibration.py) for error/directional/bias/sample;
  - optionally a Forward Expectations snapshot for explainability/source/gap/governance checks.

Read-only. It never changes fair value, decision_lock, thresholds, or sizing.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

ENGINE_VERSION = "forward_expectations_success_criteria.py v1.0"

# Falsifiable thresholds. Tightened only with evidence; never to make valuation look better.
MAX_WAPE = 0.30              # mean absolute percent error ceiling
MIN_DIRECTIONAL = 0.60       # directional hit-rate floor
MAX_ABS_BIAS = 0.20          # |mean signed relative error| ceiling (no systematic over/under)
MIN_SAMPLE_N = 15            # minimum comparable forecast-vs-actual rows before any "pass"


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _signed_bias(calibration: dict):
    """Mean signed relative error (forecast - actual)/|actual| over comparable rows.
    Positive = systematically optimistic. Returns (bias, n)."""
    errors = []
    for ev in (calibration or {}).get("evaluations") or []:
        for row in ev.get("rows") or []:
            if row.get("status") != "comparable":
                continue
            f, a = _num(row.get("forecast_value")), _num(row.get("actual_value"))
            if f is None or a is None or abs(a) < 1e-9:
                continue
            errors.append((f - a) / abs(a))
    if not errors:
        return None, 0
    return round(sum(errors) / len(errors), 4), len(errors)


def _criterion(name, status, detail, **extra):
    return {"criterion": name, "status": status, "detail": detail, **extra}


def _error_criteria(calibration: dict):
    summary = (calibration or {}).get("summary") or {}
    lanes = summary.get("lane_summaries") or []
    comparable = _num(summary.get("comparable_count")) or 0
    min_n = summary.get("min_required_n") or MIN_SAMPLE_N
    out = []

    # C4 sample sufficiency gates everything error-based.
    sample_ok = comparable >= min_n
    out.append(_criterion(
        "sample_sufficiency",
        "pass" if sample_ok else "insufficient_sample",
        f"comparable_rows={comparable} vs min_required_n={min_n}",
        comparable_count=comparable, min_required_n=min_n,
    ))

    # C1 forecast error (WAPE) — worst usable lane must clear the ceiling.
    wapes = [(l.get("lane"), l.get("metric"), _num(l.get("wape_proxy"))) for l in lanes if _num(l.get("wape_proxy")) is not None]
    if not wapes:
        out.append(_criterion("forecast_error_wape", "insufficient_data", "no comparable lane WAPE yet"))
    elif not sample_ok:
        worst = max(w for _, _, w in wapes)
        out.append(_criterion("forecast_error_wape", "insufficient_sample",
                              f"worst_wape={worst} (≤{MAX_WAPE} required) but sample below min", worst_wape=worst))
    else:
        worst = max(w for _, _, w in wapes)
        out.append(_criterion("forecast_error_wape", "pass" if worst <= MAX_WAPE else "fail",
                              f"worst_wape={worst} vs ceiling {MAX_WAPE}", worst_wape=worst))

    # C2 directional accuracy — worst usable lane must clear the floor.
    dirs = [_num(l.get("directional_accuracy")) for l in lanes if _num(l.get("directional_accuracy")) is not None]
    if not dirs:
        out.append(_criterion("directional_accuracy", "insufficient_data", "no directional data yet"))
    elif not sample_ok:
        out.append(_criterion("directional_accuracy", "insufficient_sample",
                              f"worst_directional={min(dirs)} (≥{MIN_DIRECTIONAL} required) but sample below min",
                              worst_directional=min(dirs)))
    else:
        worst = min(dirs)
        out.append(_criterion("directional_accuracy", "pass" if worst >= MIN_DIRECTIONAL else "fail",
                              f"worst_directional={worst} vs floor {MIN_DIRECTIONAL}", worst_directional=worst))

    # C3 bias — no systematic optimism/pessimism.
    bias, bias_n = _signed_bias(calibration)
    if bias is None:
        out.append(_criterion("forecast_bias", "insufficient_data", "no comparable rows for bias"))
    elif not sample_ok:
        out.append(_criterion("forecast_bias", "insufficient_sample",
                              f"mean_signed_rel_error={bias} (|·|≤{MAX_ABS_BIAS}) but sample below min", bias=bias, n=bias_n))
    else:
        out.append(_criterion("forecast_bias", "pass" if abs(bias) <= MAX_ABS_BIAS else "fail",
                              f"mean_signed_rel_error={bias} vs |{MAX_ABS_BIAS}|", bias=bias, n=bias_n))
    return out


def _snapshot_criteria(snapshot: dict):
    out = []
    if not snapshot:
        out.append(_criterion("driver_explainability", "insufficient_data", "no snapshot provided"))
        out.append(_criterion("source_completeness", "insufficient_data", "no snapshot provided"))
        out.append(_criterion("expectations_gap_verifiability", "insufficient_data", "no snapshot provided"))
        out.append(_criterion("not_valuation_inflation", "insufficient_data", "no snapshot provided"))
        return out

    # C5 driver explainability + source completeness from the evidence contract.
    contract = snapshot.get("evidence_contract") or {}
    accepted = _num(contract.get("accepted_count")) or 0
    rejected = _num(contract.get("rejected_count")) or 0
    out.append(_criterion(
        "driver_explainability",
        "pass" if (accepted > 0 and rejected == 0) else ("fail" if rejected > 0 else "insufficient_data"),
        f"accepted={accepted}, rejected={rejected} (numeric inputs must trace to accepted evidence)",
        accepted=accepted, rejected=rejected,
    ))
    inv = (snapshot.get("evidence_inventory") or {}).get("summary") or {}
    missing_sources = _num(inv.get("missing_source_count"))
    out.append(_criterion(
        "source_completeness",
        "pass" if (contract.get("status") == "pass" and (missing_sources or 0) == 0) else "fail"
        if contract.get("status") == "degraded" else "insufficient_data",
        f"evidence_contract={contract.get('status')}, missing_sources={missing_sources}",
        missing_source_count=missing_sources,
    ))

    # C6 expectations-gap verifiability: at least one auditable same-metric comparison.
    gap = (snapshot.get("expectations_gap") or {}).get("summary") or {}
    same = _num(gap.get("same_metric_gap_count")) or 0
    out.append(_criterion(
        "expectations_gap_verifiability",
        "pass" if same >= 1 else "fail",
        f"same_metric_gap_count={same} (need ≥1 auditable same-metric comparison)",
        same_metric_gap_count=same,
    ))

    # C7 governance: success must NOT be defined by valuation inflation. Shadow flags must hold.
    fpr = snapshot.get("future_price_range") or {}
    scen = snapshot.get("operating_driver_scenarios") or {}
    shadow_ok = (snapshot.get("shadow_only") is True
                 and fpr.get("changes_live_decision") is not True
                 and scen.get("changes_live_decision") is not True)
    out.append(_criterion(
        "not_valuation_inflation",
        "pass" if shadow_ok else "fail",
        "shadow_only flags intact; success is not measured by higher fair value",
    ))
    return out


def evaluate_success_criteria(calibration: dict, snapshot: dict | None = None) -> dict:
    criteria = _error_criteria(calibration) + _snapshot_criteria(snapshot)
    statuses = [c["status"] for c in criteria]
    if "fail" in statuses:
        verdict = "fail"
    elif any(s in ("insufficient_sample", "insufficient_data") for s in statuses):
        verdict = "insufficient_evidence"
    else:
        verdict = "pass"
    return {
        "engine": ENGINE_VERSION,
        "verdict": verdict,
        "shadow_to_live_gate": verdict == "pass",
        "criteria": criteria,
        "thresholds": {
            "max_wape": MAX_WAPE, "min_directional": MIN_DIRECTIONAL,
            "max_abs_bias": MAX_ABS_BIAS, "min_sample_n": MIN_SAMPLE_N,
        },
        "policy": (
            "Read-only acceptance yardstick. 'pass' is necessary (not sufficient) for EXP-4.5 "
            "shadow->live. Success is never defined as a higher valuation; insufficient evidence "
            "blocks promotion. This evaluator changes no live decision."
        ),
    }


def main():
    ap = argparse.ArgumentParser(description="Forward Expectations success-criteria gate (EXP-0.4)")
    ap.add_argument("--calibration-file", help="calibration JSON (default: run calibration)")
    ap.add_argument("--snapshot-file", help="a Forward Expectations snapshot for explainability/source/gap checks")
    args = ap.parse_args()

    if args.calibration_file:
        with open(args.calibration_file, encoding="utf-8") as handle:
            calibration = json.load(handle)
    else:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from forward_expectations_calibration import run_calibration
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        calibration = run_calibration(
            os.path.join(base, "investment", "invest_logs", "forward_expectations"),
            os.path.join(base, "skills", "earnings-analyst", "cache"),
            MIN_SAMPLE_N,
        )
    snapshot = None
    if args.snapshot_file:
        with open(args.snapshot_file, encoding="utf-8") as handle:
            snapshot = json.load(handle)
    print(json.dumps(evaluate_success_criteria(calibration, snapshot), ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
