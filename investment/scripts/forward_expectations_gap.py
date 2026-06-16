"""Expectations Gap builder for Forward Expectations.

Compares market-implied, analyst consensus, committee independent, and base-rate
views without crossing metric boundaries. Bridge consistency checks are surfaced as
financial narrative risks, not valuation verdicts.
"""
from __future__ import annotations

import argparse
import json
import math
import sys


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _round(value, digits=4):
    value = _num(value)
    return round(value, digits) if value is not None else None


def _metric_values(consensus: dict, market: dict, independent: dict, base_rate: dict):
    ind_rev = independent.get("revenue_cagr") if independent.get("available") else None
    return {
        "revenue_cagr": {
            "market_implied": None,
            "consensus": _num(consensus.get("revenue_cagr")),
            "independent": _num(ind_rev),
            "base_rate": _num(base_rate.get("peer_rev_cagr_median")),
        },
        "eps_cagr": {
            "market_implied": None,
            "consensus": _num(consensus.get("eps_cagr")),
            "independent": None,
            "base_rate": None,
        },
        "fcf_cagr": {
            "market_implied": _num(market.get("required_fcf_cagr")),
            "consensus": None,
            "independent": None,
            "base_rate": None,
        },
    }


def _compare(metric: str, left_name: str, left_value, right_name: str, right_value):
    left_value = _num(left_value)
    right_value = _num(right_value)
    if left_value is None or right_value is None:
        return None
    delta = left_value - right_value
    ratio = left_value / right_value if right_value not in (None, 0) else None
    if abs(delta) < 0.005:
        verdict = "near"
    elif delta > 0:
        verdict = f"{left_name}_above_{right_name}"
    else:
        verdict = f"{left_name}_below_{right_name}"
    return {
        "metric": metric,
        "left": left_name,
        "right": right_name,
        "left_value": _round(left_value),
        "right_value": _round(right_value),
        "delta": _round(delta),
        "ratio": _round(ratio),
        "verdict": verdict,
    }


def _same_metric_gaps(metrics: dict):
    comparisons = []
    for metric, values in metrics.items():
        pairs = (
            ("market_implied", "consensus"),
            ("market_implied", "independent"),
            ("market_implied", "base_rate"),
            ("consensus", "base_rate"),
            ("independent", "consensus"),
            ("independent", "base_rate"),
        )
        for left, right in pairs:
            comparison = _compare(metric, left, values.get(left), right, values.get(right))
            if comparison:
                comparisons.append(comparison)
    return comparisons


def _unavailable_same_metric(metrics: dict):
    unavailable = []
    for metric, values in metrics.items():
        available = [name for name, value in values.items() if _num(value) is not None]
        if len(available) >= 2:
            continue
        if len(available) == 1:
            unavailable.append({
                "metric": metric,
                "available_sources": available,
                "status": "no_same_metric_comparator",
            })
        else:
            unavailable.append({
                "metric": metric,
                "available_sources": [],
                "status": "no_metric_values",
            })
    return unavailable


def _cross_metric_observations(metrics: dict, market: dict):
    observations = []
    market_fcf = metrics["fcf_cagr"].get("market_implied")
    consensus_rev = metrics["revenue_cagr"].get("consensus")
    consensus_eps = metrics["eps_cagr"].get("consensus")
    if market_fcf is not None and (consensus_rev is not None or consensus_eps is not None):
        observations.append({
            "observation": "market_implied_fcf_vs_consensus_growth_available_but_not_comparable",
            "market_implied_fcf_cagr": _round(market_fcf),
            "consensus_revenue_cagr": _round(consensus_rev),
            "consensus_eps_cagr": _round(consensus_eps),
            "policy": "FCF CAGR, revenue CAGR, and EPS CAGR are different metrics; no numeric gap or verdict is emitted.",
        })
    if market.get("out_of_range") is True:
        observations.append({
            "observation": "market_implied_growth_out_of_range",
            "metric": "fcf_cagr",
            "value": _round(market_fcf),
            "policy": "Out-of-range reverse DCF is a pressure signal, not a cross-metric verdict.",
        })
    return observations


def _bridge_risks(financial_bridge: dict):
    risks = []
    for warning in financial_bridge.get("warnings") or []:
        risks.append({
            "source": "forward_financial_bridge",
            "risk": warning,
            "severity": "medium",
            "policy": "Bridge warning is a financial narrative risk, not a valuation verdict.",
        })
    for row in financial_bridge.get("rows") or []:
        for check in row.get("consistency_checks") or []:
            status = check.get("status")
            if status in {"wide_gap", "negative_fcf"}:
                risks.append({
                    "source": "forward_financial_bridge",
                    "date": row.get("date"),
                    "check": check.get("check"),
                    "status": status,
                    "gap_pct": check.get("gap_pct"),
                    "fcf_margin": check.get("fcf_margin"),
                    "severity": "high" if status == "wide_gap" else "medium",
                    "policy": "Consistency checks describe forecast bridge risk only.",
                })
    return risks


def _summary(comparisons: list[dict], unavailable: list[dict], bridge_risks: list[dict]):
    if comparisons:
        status = "same_metric_gap_available"
    elif bridge_risks:
        status = "bridge_risk_only"
    else:
        status = "comparison_unavailable"
    return {
        "status": status,
        "same_metric_gap_count": len(comparisons),
        "unavailable_metric_count": len(unavailable),
        "bridge_risk_count": len(bridge_risks),
    }


def build_expectations_gap(consensus: dict, market: dict, independent: dict,
                           base_rate: dict, financial_bridge: dict) -> dict:
    metrics = _metric_values(consensus or {}, market or {}, independent or {}, base_rate or {})
    same_metric_gaps = _same_metric_gaps(metrics)
    unavailable = _unavailable_same_metric(metrics)
    bridge_risks = _bridge_risks(financial_bridge or {})
    return {
        "available": bool(same_metric_gaps or bridge_risks),
        "summary": _summary(same_metric_gaps, unavailable, bridge_risks),
        "metrics": metrics,
        "same_metric_gaps": same_metric_gaps,
        "unavailable_same_metric": unavailable,
        "cross_metric_observations": _cross_metric_observations(metrics, market or {}),
        "financial_bridge_risks": bridge_risks,
        "policy": (
            "Expectations Gap is shadow-only. Numeric gaps require the same metric; "
            "bridge risks do not alter fair value, decisions, thresholds, or sizing."
        ),
    }


def main():
    ap = argparse.ArgumentParser(description="Build expectations gap from a forward_expectations snapshot")
    ap.add_argument("--snapshot-file", required=True)
    args = ap.parse_args()
    try:
        with open(args.snapshot_file, encoding="utf-8") as handle:
            snapshot = json.load(handle)
    except Exception as exc:
        print(json.dumps({"error": f"unparseable snapshot: {exc}"}))
        sys.exit(1)
    result = build_expectations_gap(
        snapshot.get("consensus_lane") or {},
        snapshot.get("market_implied_lane") or {},
        snapshot.get("independent_lane") or {},
        snapshot.get("base_rate_lane") or {},
        snapshot.get("forward_financial_bridge") or {},
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
