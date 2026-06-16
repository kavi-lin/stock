"""Semiconductor (product/chip) business-model adapter.

Builds an auditable end-market exposure map and driver tree from company-disclosed
product segments (Data Center / Gaming / Client / Automotive / Memory / ...). It does
NOT invent unit volumes, ASPs, utilization, or node mix; the numeric Independent lane
stays blocked until those drivers arrive with evidence. External-cycle transmission
(AI capex, datacenter demand, cycle phase) remains qualitative until a numeric
conversion method is supplied with evidence.

Deliberately defers IP-licensing names (royalty/license segments) to the royalty_ip
adapter — a chip vendor ships physical units; an IP licensor collects royalties.
"""
from __future__ import annotations

import math

ADAPTER_ID = "semiconductor"
ADAPTER_VERSION = "1.0"

# segment-name token -> semiconductor end-market category
END_MARKET_TOKENS = {
    "data_center": ("data center", "datacenter", "data-center"),
    "gaming": ("gaming", "graphics", "gpu"),
    "client": ("client", "pc", "desktop", "notebook", "consumer"),
    "automotive": ("automotive", "auto"),
    "embedded": ("embedded", "iot"),
    "dram": ("dram", "hbm"),
    "nand": ("nand", "flash"),
    "memory_other": ("memory", "storage"),
    "networking": ("networking", "ethernet", "switch"),
    "professional_visualization": ("professional visualization", "workstation", "visualization"),
    "mobile_wireless": ("mobile", "wireless", "handset", "rf", "5g"),
    "industrial_analog": ("analog", "industrial", "power management"),
    "oem_other": ("oem",),
}
ROYALTY_LICENSE_TOKENS = ("royalty", "royalties", "license", "licence", "licensing")
REQUIRED_NUMERIC_DRIVERS = (
    "unit_or_wafer_volume",
    "asp_or_content_per_unit",
    "capacity_utilization",
    "data_center_segment_mix",
    "revenue_cagr",
)
RATIO_DRIVERS = {"capacity_utilization", "data_center_segment_mix", "revenue_cagr"}


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _cagr(old, new, years):
    if not (_num(old) and _num(new)) or old <= 0 or new <= 0 or years <= 0:
        return None
    return (new / old) ** (1 / years) - 1


def _classify_segment(name: str):
    lowered = name.lower()
    if any(token in lowered for token in ROYALTY_LICENSE_TOKENS):
        return "royalty_license"
    for market, tokens in END_MARKET_TOKENS.items():
        if any(token in lowered for token in tokens):
            return market
    return "other"


def _product_rows(earnings_cache: dict):
    rows = ((earnings_cache.get("segments") or {}).get("product_fy") or [])
    valid = [row for row in rows if row.get("date") and isinstance(row.get("products"), dict)]
    return sorted(valid, key=lambda row: row["date"])


def match(earnings_cache: dict) -> dict:
    rows = _product_rows(earnings_cache)
    if not rows:
        return {"status": "unknown", "score": 0, "reasons": ["product_segment_history_missing"]}
    latest = rows[-1]["products"]
    end_markets, has_royalty = set(), False
    for name, value in latest.items():
        category = _classify_segment(name)
        if category == "royalty_license":
            has_royalty = True
        elif category != "other" and _num(value) is not None:
            end_markets.add(category)
    n = len(end_markets)
    reasons = [f"end_markets:{','.join(sorted(end_markets))}"] if end_markets else ["no_semiconductor_end_market_segments"]
    # Defer IP-licensing names to royalty_ip: cap at partial when royalty/license segments exist.
    if has_royalty:
        reasons.append("royalty_or_license_segment_present_defer_to_royalty_ip")
        return {"status": "partial" if n >= 1 else "generic", "score": min(40, 20 * n), "reasons": reasons}
    if n >= 2:
        return {"status": "matched", "score": min(100, 60 + 20 * n), "reasons": reasons}
    if n == 1:
        return {"status": "partial", "score": 40, "reasons": reasons}
    return {"status": "generic", "score": 0, "reasons": reasons}


def revenue_exposure_map(earnings_cache: dict) -> dict:
    rows = _product_rows(earnings_cache)
    if not rows:
        return {"available": False, "segments": [], "reason": "product_segment_history_missing"}
    latest = rows[-1]
    previous = rows[-2] if len(rows) >= 2 else None

    def _grouped(node):
        grouped, sources = {}, {}
        for name, value in (node.get("products") or {}).items():
            category = _classify_segment(name)
            if category in ("royalty_license",) or _num(value) is None:
                continue
            grouped[category] = grouped.get(category, 0) + value
            sources.setdefault(category, []).append(name)
        return grouped, sources

    latest_grouped, product_sources = _grouped(latest)
    previous_grouped = _grouped(previous)[0] if previous else {}
    total = sum(latest_grouped.values())
    segments = []
    for category, value in sorted(latest_grouped.items(), key=lambda kv: -kv[1]):
        if value <= 0:
            continue
        prior = previous_grouped.get(category)
        growth = _cagr(prior, value, 1) if prior else None
        segments.append({
            "segment": category,
            "revenue": value,
            "revenue_share": round(value / total, 4) if total else None,
            "historical_growth": round(growth, 4) if growth is not None else None,
            "source_products": product_sources.get(category, []),
            "source_ref": "earnings-analyst cache segments.product_fy",
            "as_of": latest["date"],
        })
    return {
        "available": bool(segments),
        "as_of": latest["date"],
        "total_segment_revenue": total,
        "segments": segments,
        "reason": None if segments else "no_numeric_semiconductor_segments",
    }


def driver_tree() -> dict:
    return {
        "product_revenue": {
            "equation": "unit_or_wafer_volume × asp_or_content_per_unit × segment_mix",
            "observable_drivers": ["reported segment revenue", "unit shipments", "ASP/content trends", "node ramp"],
            "required_numeric_drivers": ["unit_or_wafer_volume", "asp_or_content_per_unit"],
        },
        "capacity": {
            "equation": "capacity × utilization − capex_cycle_constraints",
            "observable_drivers": ["fab utilization", "capex intensity", "lead times", "inventory days"],
            "required_numeric_drivers": ["capacity_utilization"],
        },
        "mix": {
            "equation": "data_center_segment_mix shift drives blended ASP and growth",
            "observable_drivers": ["data center revenue share", "segment growth divergence"],
            "required_numeric_drivers": ["data_center_segment_mix"],
        },
    }


def _transmission_paths(explicit_input: dict) -> list[dict]:
    paths = explicit_input.get("transmission_paths")
    if not isinstance(paths, list) or not paths:
        return [{
            "external_driver": "ai_datacenter_capex_cycle",
            "transmission_target": "data_center_segment_revenue",
            "direction": "positive",
            "lag_range_quarters": None,
            "evidence_refs": [],
            "conversion_method": None,
            "confidence": "unknown",
        }]
    return paths


def transmission_graph(explicit_input: dict) -> dict:
    evaluated, numeric_paths = [], 0
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
        evaluated.append({**path,
                          "status": "numeric_eligible" if numeric_eligible else "qualitative_only",
                          "missing_for_numeric": missing})
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
            "note": "End-market exposure map is usable; numeric Independent forecast is blocked.",
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
        return {"available": False, "reason": lane.get("reason") or "independent_lane_unavailable",
                "drivers": {}, "case_driver_keys": []}
    values = dict(lane.get("driver_values") or {})
    refs = dict(lane.get("driver_evidence_refs") or {})
    drivers = {}
    for key in REQUIRED_NUMERIC_DRIVERS:
        value = _num(values.get(key))
        if value is None:
            continue
        drivers[key] = {
            "value": round(value, 4) if abs(value) < 10 else value,
            "unit": "ratio" if key in RATIO_DRIVERS else "units",
            "evidence_refs": refs.get(key) or [],
        }
    return {
        "available": all(key in drivers for key in REQUIRED_NUMERIC_DRIVERS),
        "business_model": ADAPTER_ID,
        "drivers": drivers,
        "case_driver_keys": list(REQUIRED_NUMERIC_DRIVERS),
        "revenue_exposure_map_ref": {"available": bool(exposure.get("available")), "as_of": exposure.get("as_of")},
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
        "available": False, "revenue_cagr": None, "reason": "adapter_not_matched",
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
