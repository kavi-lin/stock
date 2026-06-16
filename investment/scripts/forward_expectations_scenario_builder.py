"""Operating-driver scenario builder for Forward Expectations.

This module consumes the scenario policy gate. It produces shadow-only
bear/base/bull operating-driver cases only when the policy explicitly allows
numeric driver scenarios. It never emits a fair value, target price, verdict,
threshold, or sizing recommendation.
"""
from __future__ import annotations

import argparse
import json
import math
import sys

BUILDER_VERSION = "forward_expectations_scenario_builder.py v1.1"
SCENARIO_CASES = ("bear", "base", "bull")
SENSITIVITY_STEP = 0.05
DRIVER_LEVEL_STEP = 0.10
MIN_REVENUE_CAGR = -0.50
MAX_REVENUE_CAGR = 1.50
RATIO_DRIVERS = {
    "royalty_rate_or_value_per_unit",
    "license_pipeline_conversion",
    "data_center_segment_exposure",
    "revenue_cagr",
}


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _clamp(value, lo=MIN_REVENUE_CAGR, hi=MAX_REVENUE_CAGR):
    return max(lo, min(hi, value))


def _allowed_mode_names(policy: dict) -> set[str]:
    return {mode.get("mode") for mode in (policy or {}).get("allowed_modes") or []}


def _selected_adapter(adapter_evaluation: dict) -> dict:
    return (adapter_evaluation or {}).get("selected_adapter") or {}


def _driver_refs(independent: dict, selected: dict) -> dict:
    refs = dict(independent.get("driver_evidence_refs") or {})
    inventory_targets = selected.get("evidence_acquisition_targets") or []
    for target in inventory_targets:
        if not isinstance(target, dict):
            continue
        metric = target.get("metric")
        evidence_id = target.get("evidence_id")
        if metric and evidence_id:
            refs.setdefault(metric, []).append(evidence_id)
    return refs


def _qualitative_watchlist(policy: dict, independent: dict, selected: dict) -> list[dict]:
    gates = (policy or {}).get("gates") or {}
    driver_gate = gates.get("driver_evidence") or {}
    conversion_gate = gates.get("conversion_method") or {}
    missing = list(driver_gate.get("missing") or independent.get("missing_numeric_drivers") or [])
    missing += list(independent.get("missing_driver_evidence") or [])
    graph = selected.get("transmission_graph") or {}
    paths = graph.get("paths") or []
    watchlist = []
    for name in dict.fromkeys(missing):
        watchlist.append({
            "item": name,
            "reason": "required_numeric_driver_or_evidence_missing",
            "needed_for": "driver_numeric_bear_base_bull",
        })
    if conversion_gate.get("status") != "pass":
        watchlist.append({
            "item": "numeric_transmission_conversion",
            "reason": conversion_gate.get("reason") or "no_numeric_transmission_conversion",
            "needed_for": "driver_numeric_bear_base_bull",
        })
    for path in paths[:5]:
        if path.get("status") != "numeric_eligible":
            watchlist.append({
                "item": path.get("transmission_target") or path.get("external_driver") or "transmission_path",
                "reason": "transmission_path_not_numeric_eligible",
                "missing": path.get("missing_for_numeric") or [],
                "needed_for": "driver_numeric_bear_base_bull",
            })
    return watchlist


def _guidance_overlays(guidance_extraction: dict) -> list[dict]:
    overlays = []
    for item in (guidance_extraction or {}).get("promoted") or []:
        value = item.get("value")
        overlay = {
            "metric": item.get("metric"),
            "value": value,
            "unit": item.get("unit"),
            "source_ref": item.get("source_ref"),
            "published_at": item.get("published_at"),
            "policy": "preserve_range" if isinstance(value, dict) and value.get("low") is not None and value.get("high") is not None else "display_only",
        }
        overlays.append(overlay)
    return overlays


def _numeric_cases(independent: dict, selected: dict) -> list[dict]:
    driver_level = _driver_level_cases(selected)
    if driver_level:
        return driver_level
    base_cagr = _num(independent.get("revenue_cagr"))
    if base_cagr is None:
        return []
    refs = _driver_refs(independent, selected)
    cases = []
    for case, delta in (("bear", -SENSITIVITY_STEP), ("base", 0.0), ("bull", SENSITIVITY_STEP)):
        cagr = round(_clamp(base_cagr + delta), 4)
        cases.append({
            "case": case,
            "operating_drivers": {
                "revenue_cagr": cagr,
            },
            "driver_changes": [
                {
                    "driver": "revenue_cagr",
                    "change_vs_base": round(delta, 4),
                    "method": "bounded_driver_sensitivity",
                    "evidence_refs": refs.get("revenue_cagr") or [],
                }
            ],
            "interpretation": (
                "Base uses the evidenced Independent revenue CAGR."
                if case == "base"
                else "Sensitivity case changes the evidenced revenue CAGR driver; no valuation math is produced."
            ),
        })
    return cases


def _bounded_driver_value(driver: str, value: float, direction: int):
    if driver == "revenue_cagr":
        return round(_clamp(value + direction * SENSITIVITY_STEP), 4)
    if driver in RATIO_DRIVERS:
        return round(max(0.0, min(1.0, value * (1 + direction * DRIVER_LEVEL_STEP))), 4)
    return round(max(0.0, value * (1 + direction * DRIVER_LEVEL_STEP)), 4)


def _driver_level_cases(selected: dict) -> list[dict]:
    model = selected.get("driver_model") or {}
    if not model.get("available"):
        return []
    drivers = model.get("drivers") or {}
    keys = [key for key in model.get("case_driver_keys") or [] if key in drivers]
    if not keys:
        return []
    cases = []
    for case, direction in (("bear", -1), ("base", 0), ("bull", 1)):
        operating = {}
        changes = []
        for key in keys:
            spec = drivers.get(key) or {}
            value = _num(spec.get("value"))
            if value is None:
                continue
            adjusted = _bounded_driver_value(key, value, direction)
            operating[key] = adjusted
            changes.append({
                "driver": key,
                "change_vs_base": 0 if direction == 0 else round((adjusted - value) / value, 4) if value else 0,
                "method": "driver_level_bounded_sensitivity",
                "evidence_refs": spec.get("evidence_refs") or [],
            })
        if operating:
            cases.append({
                "case": case,
                "business_model": model.get("business_model"),
                "operating_drivers": operating,
                "driver_changes": changes,
                "interpretation": (
                    "Base uses evidenced Royalty/IP driver values."
                    if case == "base"
                    else "Sensitivity case changes explicit Royalty/IP operating drivers; no valuation math is produced."
                ),
            })
    return cases if len(cases) == 3 else []


def build_operating_driver_scenarios(
    scenario_policy: dict,
    independent: dict,
    adapter_evaluation: dict,
    financial_bridge: dict,
    guidance_extraction: dict,
) -> dict:
    selected = _selected_adapter(adapter_evaluation)
    modes = _allowed_mode_names(scenario_policy)
    status = (scenario_policy or {}).get("status") or "insufficient_inputs"
    overlays = _guidance_overlays(guidance_extraction)
    watchlist = _qualitative_watchlist(scenario_policy or {}, independent or {}, selected)
    base = {
        "builder": BUILDER_VERSION,
        "available": False,
        "status": status,
        "mode": None,
        "shadow_only": True,
        "valuation_output": False,
        "changes_live_decision": False,
        "cases": [],
        "guidance_overlays": overlays,
        "qualitative_watchlist": watchlist,
        "policy": (
            "Operating-driver scenarios are advisory shadow output only. They do not "
            "alter fair value, verdict, decision lock, thresholds, or sizing."
        ),
    }
    if status == "numeric_scenario_allowed" and "driver_numeric_bear_base_bull" in modes:
        cases = _numeric_cases(independent or {}, selected)
        if cases:
            return {
                **base,
                "available": True,
                "mode": "driver_numeric_bear_base_bull",
                "cases": cases,
                "qualitative_watchlist": [],
            }
        return {
            **base,
            "status": "numeric_inputs_incomplete",
            "mode": "qualitative_driver_watchlist",
            "qualitative_watchlist": watchlist or [{
                "item": "independent_revenue_cagr",
                "reason": "numeric_policy_allowed_but_base_driver_missing",
                "needed_for": "driver_numeric_bear_base_bull",
            }],
        }
    if "management_guidance_overlay" in modes or "consensus_range_bridge" in modes:
        return {**base, "available": bool(overlays), "mode": "range_or_overlay_only"}
    if status == "qualitative_only":
        return {**base, "mode": "qualitative_driver_watchlist"}
    return {**base, "mode": "insufficient_inputs"}


def main():
    ap = argparse.ArgumentParser(description="Build shadow operating-driver scenarios from a Forward Expectations snapshot")
    ap.add_argument("--snapshot-file", required=True)
    args = ap.parse_args()
    try:
        with open(args.snapshot_file, encoding="utf-8") as handle:
            snapshot = json.load(handle)
    except Exception as exc:
        print(json.dumps({"error": f"unparseable snapshot: {exc}"}))
        sys.exit(1)
    result = build_operating_driver_scenarios(
        snapshot.get("scenario_policy") or {},
        snapshot.get("independent_lane") or {},
        snapshot.get("adapter_evaluation") or {},
        snapshot.get("forward_financial_bridge") or {},
        snapshot.get("guidance_extraction") or {},
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
