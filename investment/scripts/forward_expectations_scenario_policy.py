"""Scenario policy gates for Forward Expectations.

This module decides which scenario modes are allowed from the evidence currently
available. It does not generate bear/base/bull numbers. Its job is to prevent
future scenario builders from inventing drivers, conversion methods, or precise
assumptions when the evidence gates are not met.
"""
from __future__ import annotations

import argparse
import json
import sys

FORBIDDEN_METHODS = [
    "fixed_pct_eps_pe_haircut",
    "fixed_pct_revenue_haircut_without_driver",
    "llm_invented_tam_or_penetration",
    "cross_metric_gap_as_numeric_driver",
    "single_point_guidance_range_collapse",
]


def _has_value(value):
    return value is not None and value != "" and value != []


def _numeric_transmission_count(adapter_evaluation: dict, independent: dict):
    selected = (adapter_evaluation or {}).get("selected_adapter") or {}
    graph = selected.get("transmission_graph") or {}
    count = graph.get("numeric_eligible_count")
    if isinstance(count, int):
        return count
    count = independent.get("numeric_transmission_paths")
    return count if isinstance(count, int) else 0


def _has_promoted_guidance(guidance: dict):
    promoted = (guidance or {}).get("promoted") or []
    return bool(promoted), promoted


def _has_range_guidance(promoted: list[dict]):
    for item in promoted:
        value = item.get("value") or {}
        if isinstance(value, dict) and value.get("low") is not None and value.get("high") is not None:
            return True
    return False


def _driver_gate(independent: dict, adapter_evaluation: dict):
    selected = (adapter_evaluation or {}).get("selected_adapter") or {}
    missing = independent.get("missing_numeric_drivers") or selected.get("missing_numeric_drivers") or []
    has_independent = independent.get("available") is True and independent.get("revenue_cagr") is not None
    if has_independent and not missing:
        return {"status": "pass", "reason": "independent_lane_numeric_available", "missing": []}
    if missing:
        return {"status": "fail", "reason": "missing_numeric_drivers", "missing": missing}
    return {"status": "fail", "reason": independent.get("reason") or "independent_lane_unavailable", "missing": []}


def _conversion_gate(independent: dict, adapter_evaluation: dict):
    count = _numeric_transmission_count(adapter_evaluation, independent)
    if count > 0:
        return {"status": "pass", "reason": "numeric_transmission_paths_available", "numeric_transmission_paths": count}
    return {"status": "fail", "reason": "no_numeric_transmission_conversion", "numeric_transmission_paths": 0}


def _base_metric_gate(consensus: dict, financial_bridge: dict):
    if consensus.get("revenue_cagr") is not None or consensus.get("eps_cagr") is not None:
        return {"status": "pass", "reason": "consensus_growth_available"}
    if financial_bridge.get("available") and financial_bridge.get("rows"):
        return {"status": "pass", "reason": "forward_financial_bridge_available"}
    return {"status": "fail", "reason": "no_forward_base_metric"}


def _bridge_gate(financial_bridge: dict):
    if financial_bridge.get("available") and financial_bridge.get("rows"):
        return {"status": "pass", "reason": "forward_bridge_available"}
    return {
        "status": "fail",
        "reason": financial_bridge.get("status") or "forward_bridge_unavailable",
        "missing": financial_bridge.get("missing_inputs") or [],
    }


def _allowed_modes(gates: dict, has_guidance: bool, has_range: bool):
    modes = [{
        "mode": "qualitative_driver_watchlist",
        "status": "allowed",
        "reason": "Always allowed when clearly marked qualitative-only.",
    }]
    if gates["base_metric"]["status"] == "pass" and gates["bridge"]["status"] == "pass":
        modes.append({
            "mode": "consensus_range_bridge",
            "status": "allowed",
            "reason": "Consensus annual estimates can be rendered through financial bridge ranges.",
        })
    if has_guidance:
        modes.append({
            "mode": "management_guidance_overlay",
            "status": "allowed",
            "reason": "Promoted management guidance can be displayed as overlay evidence.",
            "range_required": has_range,
        })
    if (
        gates["base_metric"]["status"] == "pass"
        and gates["driver_evidence"]["status"] == "pass"
        and gates["conversion_method"]["status"] == "pass"
    ):
        modes.append({
            "mode": "driver_numeric_bear_base_bull",
            "status": "allowed",
            "reason": "Driver values and numeric transmission conversion are available.",
        })
    return modes


def _policy_status(gates: dict, modes: list[dict]):
    if any(mode["mode"] == "driver_numeric_bear_base_bull" for mode in modes):
        return "numeric_scenario_allowed"
    if any(mode["mode"] in {"consensus_range_bridge", "management_guidance_overlay"} for mode in modes):
        return "range_or_overlay_only"
    if gates["base_metric"]["status"] == "pass":
        return "qualitative_only"
    return "insufficient_inputs"


def build_scenario_policy(consensus: dict, independent: dict, adapter_evaluation: dict,
                          financial_bridge: dict, guidance_extraction: dict) -> dict:
    has_guidance, promoted_guidance = _has_promoted_guidance(guidance_extraction or {})
    has_range = _has_range_guidance(promoted_guidance)
    gates = {
        "base_metric": _base_metric_gate(consensus or {}, financial_bridge or {}),
        "driver_evidence": _driver_gate(independent or {}, adapter_evaluation or {}),
        "conversion_method": _conversion_gate(independent or {}, adapter_evaluation or {}),
        "bridge": _bridge_gate(financial_bridge or {}),
        "range_discipline": {
            "status": "pass",
            "reason": "ranges_must_remain_ranges",
            "range_guidance_present": has_range,
        },
    }
    modes = _allowed_modes(gates, has_guidance, has_range)
    status = _policy_status(gates, modes)
    return {
        "available": status != "insufficient_inputs",
        "status": status,
        "gates": gates,
        "allowed_modes": modes,
        "forbidden_methods": FORBIDDEN_METHODS,
        "scenario_requirements": [
            "Bear/base/bull numeric scenarios must change explicit operating drivers.",
            "Driver values require point-in-time evidence and source lineage.",
            "Transmission from external trend to company revenue requires lag, exposure, and conversion method.",
            "Guidance ranges must remain ranges; midpoint is only a derived helper.",
            "Scenarios must not alter live fair value, verdict, thresholds, or sizing.",
        ],
        "policy": (
            "Scenario policy is shadow-only. It authorizes scenario modes but does not generate "
            "valuation outputs or live decisions."
        ),
    }


def main():
    ap = argparse.ArgumentParser(description="Evaluate Forward Expectations scenario policy from a snapshot")
    ap.add_argument("--snapshot-file", required=True)
    args = ap.parse_args()
    try:
        with open(args.snapshot_file, encoding="utf-8") as handle:
            snapshot = json.load(handle)
    except Exception as exc:
        print(json.dumps({"error": f"unparseable snapshot: {exc}"}))
        sys.exit(1)
    result = build_scenario_policy(
        snapshot.get("consensus_lane") or {},
        snapshot.get("independent_lane") or {},
        snapshot.get("adapter_evaluation") or {},
        snapshot.get("forward_financial_bridge") or {},
        snapshot.get("guidance_extraction") or {},
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
