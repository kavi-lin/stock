"""Royalty/IP business-model adapter.

This adapter builds an auditable exposure map and driver tree from company-disclosed
product segments. It does not invent royalty units, penetration, or royalty rates.
External-theme transmission remains qualitative until a numeric conversion method is
supplied with evidence.
"""
from __future__ import annotations

import math

ADAPTER_ID = "royalty_ip"
ADAPTER_VERSION = "1.0"

ROYALTY_TOKENS = ("royalty", "royalties")
LICENSE_TOKENS = ("license", "licence", "licensing")
REQUIRED_NUMERIC_DRIVERS = (
    "royalty_bearing_units",
    "royalty_rate_or_value_per_unit",
    "license_pipeline_conversion",
    "data_center_segment_exposure",
    "revenue_cagr",
)


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _cagr(old, new, years):
    if not (_num(old) and _num(new)) or old <= 0 or new <= 0 or years <= 0:
        return None
    return (new / old) ** (1 / years) - 1


def _classify_product(name: str):
    lowered = name.lower()
    if any(token in lowered for token in ROYALTY_TOKENS):
        return "royalty"
    if any(token in lowered for token in LICENSE_TOKENS):
        return "license"
    return "other"


def _product_rows(earnings_cache: dict):
    rows = ((earnings_cache.get("segments") or {}).get("product_fy") or [])
    valid = []
    for row in rows:
        products = row.get("products")
        if row.get("date") and isinstance(products, dict):
            valid.append(row)
    return sorted(valid, key=lambda row: row["date"])


def match(earnings_cache: dict) -> dict:
    rows = _product_rows(earnings_cache)
    if not rows:
        return {"status": "unknown", "score": 0, "reasons": ["product_segment_history_missing"]}
    latest = rows[-1]["products"]
    categories = {_classify_product(name) for name in latest}
    reasons = []
    score = 0
    if "royalty" in categories:
        score += 60
        reasons.append("royalty_product_segment_present")
    if "license" in categories:
        score += 40
        reasons.append("license_product_segment_present")
    if score == 100:
        return {"status": "matched", "score": score, "reasons": reasons}
    if score:
        return {"status": "partial", "score": score, "reasons": reasons}
    return {"status": "generic", "score": 0, "reasons": ["no_royalty_or_license_segment"]}


def revenue_exposure_map(earnings_cache: dict) -> dict:
    rows = _product_rows(earnings_cache)
    if not rows:
        return {"available": False, "segments": [], "reason": "product_segment_history_missing"}
    latest = rows[-1]
    previous = rows[-2] if len(rows) >= 2 else None
    latest_grouped = {"royalty": 0, "license": 0, "other": 0}
    previous_grouped = {"royalty": 0, "license": 0, "other": 0}
    product_sources = {"royalty": [], "license": [], "other": []}
    for name, value in latest["products"].items():
        category = _classify_product(name)
        if _num(value) is not None:
            latest_grouped[category] += value
            product_sources[category].append(name)
    if previous:
        for name, value in previous["products"].items():
            category = _classify_product(name)
            if _num(value) is not None:
                previous_grouped[category] += value
    total = sum(latest_grouped.values())
    segments = []
    for category in ("royalty", "license", "other"):
        value = latest_grouped[category]
        if value <= 0:
            continue
        prior = previous_grouped[category] if previous else None
        growth = _cagr(prior, value, 1) if prior else None
        segments.append({
            "segment": category,
            "revenue": value,
            "revenue_share": round(value / total, 4) if total else None,
            "historical_growth": round(growth, 4) if growth is not None else None,
            "source_products": product_sources[category],
            "source_ref": "earnings-analyst cache segments.product_fy",
            "as_of": latest["date"],
        })
    return {
        "available": bool(segments),
        "as_of": latest["date"],
        "total_segment_revenue": total,
        "segments": segments,
        "reason": None if segments else "no_numeric_product_segments",
    }


def driver_tree() -> dict:
    return {
        "royalty_revenue": {
            "equation": "royalty_bearing_units × royalty_rate_or_value_per_unit × mix",
            "observable_drivers": ["reported royalty revenue", "product launches", "production milestones"],
            "required_numeric_drivers": ["royalty_bearing_units", "royalty_rate_or_value_per_unit"],
        },
        "license_revenue": {
            "equation": "license_pipeline × conversion × revenue_recognition",
            "observable_drivers": ["reported license revenue", "signed licenses", "product launch milestones"],
            "required_numeric_drivers": ["license_pipeline_conversion"],
        },
    }


def _transmission_paths(explicit_input: dict) -> list[dict]:
    paths = explicit_input.get("transmission_paths")
    if not isinstance(paths, list) or not paths:
        return [{
            "external_driver": "ai_infrastructure_growth",
            "transmission_target": "data_center_royalty_revenue",
            "direction": "positive",
            "lag_range_quarters": None,
            "evidence_refs": [],
            "conversion_method": None,
            "confidence": "unknown",
        }]
    return paths


def transmission_graph(explicit_input: dict) -> dict:
    evaluated = []
    numeric_paths = 0
    for path in _transmission_paths(explicit_input):
        missing = [
            key for key in (
                "external_driver", "transmission_target", "direction",
                "lag_range_quarters", "evidence_refs", "conversion_method", "confidence",
            )
            if path.get(key) in (None, "", [])
        ]
        numeric_eligible = not missing and path.get("conversion_method") not in ("qualitative", "unknown")
        if numeric_eligible:
            numeric_paths += 1
        evaluated.append({
            **path,
            "status": "numeric_eligible" if numeric_eligible else "qualitative_only",
            "missing_for_numeric": missing,
        })
    return {
        "paths": evaluated,
        "numeric_eligible_count": numeric_paths,
        "policy": "Only numeric_eligible paths may change an Independent forecast.",
    }


def independent_lane(explicit_input: dict, graph: dict) -> dict:
    drivers = dict(explicit_input.get("independent_drivers") or {})
    evidence_refs = dict(explicit_input.get("independent_driver_evidence_refs") or {})
    inventory = explicit_input.get("evidence_inventory") or {}
    for record in inventory.get("accepted") or []:
        metric = record.get("metric")
        if metric in REQUIRED_NUMERIC_DRIVERS and record.get("numeric_eligible"):
            evidence_refs.setdefault(metric, []).append(record.get("evidence_id"))
            if _num(record.get("value")) is not None:
                drivers.setdefault(metric, record["value"])
    missing = [name for name in REQUIRED_NUMERIC_DRIVERS if _num(drivers.get(name)) is None]
    missing_evidence = [
        name for name in REQUIRED_NUMERIC_DRIVERS
        if not isinstance(evidence_refs.get(name), list) or not evidence_refs.get(name)
    ]
    if missing or missing_evidence or graph["numeric_eligible_count"] == 0:
        return {
            "available": False,
            "revenue_cagr": None,
            "reason": "insufficient_evidence",
            "missing_numeric_drivers": missing,
            "missing_driver_evidence": missing_evidence,
            "numeric_transmission_paths": graph["numeric_eligible_count"],
            "note": "Exposure map is usable; numeric Independent forecast is blocked.",
        }
    revenue_cagr = _num(drivers.get("revenue_cagr"))
    if revenue_cagr is None:
        return {
            "available": False,
            "revenue_cagr": None,
            "reason": "revenue_cagr_not_derived",
            "missing_numeric_drivers": [],
            "missing_driver_evidence": [],
            "numeric_transmission_paths": graph["numeric_eligible_count"],
        }
    return {
        "available": True,
        "revenue_cagr": round(revenue_cagr, 4),
        "reason": None,
        "missing_numeric_drivers": [],
        "missing_driver_evidence": [],
        "driver_values": {name: drivers.get(name) for name in REQUIRED_NUMERIC_DRIVERS},
        "driver_evidence_refs": evidence_refs,
        "numeric_transmission_paths": graph["numeric_eligible_count"],
    }


def driver_model(lane: dict, exposure: dict) -> dict:
    if not lane.get("available"):
        return {
            "available": False,
            "reason": lane.get("reason") or "independent_lane_unavailable",
            "drivers": {},
            "case_driver_keys": [],
        }
    values = dict(lane.get("driver_values") or {})
    refs = dict(lane.get("driver_evidence_refs") or {})
    drivers = {}
    for key in REQUIRED_NUMERIC_DRIVERS:
        value = _num(values.get(key))
        if value is None:
            continue
        drivers[key] = {
            "value": round(value, 4) if abs(value) < 10 else value,
            "unit": "ratio" if key in {
                "royalty_rate_or_value_per_unit",
                "license_pipeline_conversion",
                "data_center_segment_exposure",
                "revenue_cagr",
            } else "units",
            "evidence_refs": refs.get(key) or [],
        }
    return {
        "available": all(key in drivers for key in REQUIRED_NUMERIC_DRIVERS),
        "business_model": ADAPTER_ID,
        "drivers": drivers,
        "case_driver_keys": [
            "royalty_bearing_units",
            "royalty_rate_or_value_per_unit",
            "license_pipeline_conversion",
            "data_center_segment_exposure",
            "revenue_cagr",
        ],
        "revenue_exposure_map_ref": {
            "available": bool(exposure.get("available")),
            "as_of": exposure.get("as_of"),
        },
        "policy": "Driver-level scenario cases may only use numeric_eligible driver evidence.",
    }


def evaluate(ticker: str, earnings_cache: dict, explicit_input: dict) -> dict:
    adapter_input = dict((explicit_input.get("adapter_inputs") or {}).get(ADAPTER_ID) or {})
    if explicit_input.get("evidence_inventory"):
        adapter_input["evidence_inventory"] = explicit_input["evidence_inventory"]
    adapter_match = match(earnings_cache)
    exposure = revenue_exposure_map(earnings_cache)
    graph = transmission_graph(adapter_input)
    lane = independent_lane(adapter_input, graph) if adapter_match["status"] == "matched" else {
        "available": False,
        "revenue_cagr": None,
        "reason": "adapter_not_matched",
    }
    model = driver_model(lane, exposure)
    return {
        "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "ticker": ticker,
        "match": adapter_match,
        "revenue_exposure_map": exposure,
        "driver_tree": driver_tree(),
        "transmission_graph": graph,
        "independent_lane": lane,
        "driver_model": model,
        "evidence_acquisition_targets": (adapter_input.get("evidence_inventory") or {}).get("missing_drivers") or [],
        "supported_valuation_methods": ["forward_earnings", "forward_revenue", "scenario_range"],
        "unsupported_valuation_methods": ["trailing_fcf_as_sole_value_base"],
        "shadow_only": True,
    }
