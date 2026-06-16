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

BUILDER_VERSION = "forward_expectations_scenario_builder.py v2.0 (evidence-dispersion spread)"
SCENARIO_CASES = ("bear", "base", "bull")
MIN_REVENUE_CAGR = -0.50
MAX_REVENUE_CAGR = 1.50


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _pos(value):
    value = _num(value)
    return value if value is not None and value > 0 else None


def _clamp(value, lo=MIN_REVENUE_CAGR, hi=MAX_REVENUE_CAGR):
    return max(lo, min(hi, value))


def _years_between(d_old: str, d_new: str):
    import datetime as _dt
    try:
        a = _dt.date.fromisoformat((d_old or "")[:10])
        b = _dt.date.fromisoformat((d_new or "")[:10])
    except Exception:
        return None
    days = (b - a).days
    return days / 365.25 if days > 0 else None


def _cagr(v0, v1, years):
    v0, v1, years = _pos(v0), _pos(v1), _num(years)
    if v0 is None or v1 is None or years is None or years <= 0:
        return None
    return (v1 / v0) ** (1 / years) - 1


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


def _consensus_cagr_band(financial_bridge: dict):
    """EXP-R3: bear/base/bull revenue CAGR from the analyst consensus low/high envelope —
    a real dispersion source, NOT a fixed +/- step. Needs >=2 forward rows spanning time
    and a genuine low<high spread on the terminal revenue. Returns None to force degradation."""
    rows = [r for r in (financial_bridge or {}).get("rows") or []
            if isinstance(r, dict) and _pos((r.get("revenue") or {}).get("point"))]
    rows = sorted(rows, key=lambda r: r.get("date") or "")
    if len(rows) < 2:
        return None
    near, far = rows[0], rows[-1]
    years = _years_between(near.get("date"), far.get("date"))
    rev = far.get("revenue") or {}
    pt, lo, hi = _pos(rev.get("point")), _pos(rev.get("low")), _pos(rev.get("high"))
    near_pt = _pos((near.get("revenue") or {}).get("point"))
    if not (years and pt and lo and hi and near_pt) or not (hi > lo):
        return None
    base = _cagr(near_pt, pt, years)
    bear = _cagr(near_pt, lo, years)
    bull = _cagr(near_pt, hi, years)
    if base is None or bear is None or bull is None:
        return None
    return {
        "bear": round(_clamp(bear), 4),
        "base": round(_clamp(base), 4),
        "bull": round(_clamp(bull), 4),
        "window_years": round(years, 2),
        "near_date": near.get("date"),
        "far_date": far.get("date"),
        "dispersion_source": "consensus_revenue_low_high_envelope",
    }


def _base_driver_values(selected: dict) -> dict:
    """Disclose the evidenced base driver values WITHOUT fabricating per-driver spread.
    Driver specs carry only a point value + evidence_refs, so they cannot legitimately
    drive bear/bull moves (no per-driver dispersion evidence). They are held at base."""
    model = selected.get("driver_model") or {}
    if not model.get("available"):
        return {}
    drivers = model.get("drivers") or {}
    keys = [key for key in model.get("case_driver_keys") or [] if key in drivers]
    out = {}
    for key in keys:
        value = _num((drivers.get(key) or {}).get("value"))
        if value is not None:
            out[key] = round(value, 6)
    return out


def _numeric_cases(independent: dict, selected: dict, financial_bridge: dict) -> list[dict]:
    band = _consensus_cagr_band(financial_bridge)
    if band is None:
        return []
    refs = _driver_refs(independent, selected)
    base_drivers = _base_driver_values(selected)
    model = selected.get("driver_model") or {}
    cases = []
    for case in SCENARIO_CASES:
        cagr = band[case]
        cases.append({
            "case": case,
            "business_model": model.get("business_model"),
            "operating_drivers": {"revenue_cagr": cagr},
            "base_operating_drivers_held": base_drivers,
            "driver_changes": [{
                "driver": "revenue_cagr",
                "value": cagr,
                "change_vs_base": round(cagr - band["base"], 4),
                "method": "consensus_low_high_envelope",
                "dispersion_source": band["dispersion_source"],
                "window": {"from": band["near_date"], "to": band["far_date"], "years": band["window_years"]},
                "evidence_refs": refs.get("revenue_cagr") or [],
            }],
            "interpretation": (
                "Base uses the consensus point revenue CAGR over the estimate window."
                if case == "base" else
                "Bear/bull use the analyst low/high revenue envelope (evidence dispersion), "
                "not a fixed step. Per-driver values are held at base — no per-driver dispersion "
                "evidence exists to spread them. No valuation math is produced."
            ),
        })
    return cases


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
        cases = _numeric_cases(independent or {}, selected, financial_bridge or {})
        if cases:
            return {
                **base,
                "available": True,
                "mode": "driver_numeric_bear_base_bull",
                "dispersion_source": "consensus_revenue_low_high_envelope",
                "cases": cases,
                "qualitative_watchlist": [],
            }
        # EXP-R3: policy allows numeric, but no evidence-based dispersion exists to spread
        # bear/bull. Do NOT fabricate a fixed +/- step — degrade to qualitative.
        return {
            **base,
            "status": "numeric_inputs_incomplete",
            "mode": "qualitative_driver_watchlist",
            "qualitative_watchlist": (watchlist or []) + [{
                "item": "consensus_revenue_dispersion",
                "reason": "no_evidence_based_dispersion_for_scenario_spread",
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
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
