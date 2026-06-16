"""Point-in-time evidence inventory for Forward Expectations.

The inventory classifies locally available evidence without inventing missing values.
Only sourced company/structured facts are accepted. Nexus relations and narrative
artifacts remain provisional unless they carry a corroborated causal relation.
"""
from __future__ import annotations

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NEXUS_PATH = os.path.join(BASE_DIR, "Dashboard", "nexus_graph.json")

REQUIRED_ROYALTY_IP_DRIVERS = {
    "royalty_bearing_units": {
        "preferred_sources": ["company_filing", "company_ir", "earnings_transcript"],
        "purpose": "Convert product adoption and shipments into royalty revenue.",
    },
    "royalty_rate_or_value_per_unit": {
        "preferred_sources": ["company_filing", "company_ir", "earnings_transcript"],
        "purpose": "Convert royalty-bearing units into royalty revenue.",
    },
    "license_pipeline_conversion": {
        "preferred_sources": ["company_filing", "company_ir", "earnings_transcript"],
        "purpose": "Convert signed licenses and launches into recognized license revenue.",
    },
    "data_center_segment_exposure": {
        "preferred_sources": ["company_filing", "company_ir", "earnings_transcript"],
        "purpose": "Limit AI-infrastructure transmission to the exposed segment.",
    },
}


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def _record(evidence_id, metric, value, unit, source_type, source_ref, as_of,
            status, numeric_eligible, reason, confidence="medium", metadata=None):
    return {
        "evidence_id": evidence_id,
        "metric": metric,
        "value": value,
        "unit": unit,
        "source_type": source_type,
        "source_ref": source_ref,
        "as_of": as_of,
        "status": status,
        "numeric_eligible": numeric_eligible,
        "reason": reason,
        "confidence": confidence,
        "metadata": metadata or {},
    }


def _company_evidence(ticker: str, earnings_cache: dict) -> list[dict]:
    as_of = earnings_cache.get("as_of_date") or earnings_cache.get("last_earnings_date") or "unknown"
    records = []
    product_rows = sorted(
        ((earnings_cache.get("segments") or {}).get("product_fy") or []),
        key=lambda row: row.get("date") or "",
        reverse=True,
    )
    for row in product_rows[:1]:
        for product, value in (row.get("products") or {}).items():
            slug = product.lower().replace(" ", "_")
            records.append(_record(
                f"company_segment:{ticker}:{slug}:{row.get('date')}",
                f"segment_revenue:{slug}",
                value,
                "currency",
                "structured_company_segment",
                "earnings-analyst cache segments.product_fy",
                row.get("date") or as_of,
                "accepted",
                True,
                "company segment value from structured provider",
                "high",
                {"product": product},
            ))
    for metric, value in (
        ("revenue_yoy", ((earnings_cache.get("derived") or {}).get("yoy_growth") or {}).get("revenue_yoy")),
        ("gross_margin_latest", (((earnings_cache.get("derived") or {}).get("margins_8q") or [{}])[0]).get("gross")),
    ):
        if value is not None:
            records.append(_record(
                f"company_derived:{ticker}:{metric}:{as_of}",
                metric,
                value,
                "ratio",
                "structured_company_financials",
                "earnings-analyst cache derived",
                as_of,
                "accepted",
                True,
                "deterministic calculation from structured financial statements",
            ))
    for row in earnings_cache.get("annual_estimates") or []:
        if row.get("date") and row.get("revenue_avg") is not None:
            records.append(_record(
                f"consensus:{ticker}:revenue:{row['date']}",
                "consensus_revenue",
                row["revenue_avg"],
                "currency",
                "analyst_consensus",
                "earnings-analyst cache annual_estimates",
                row["date"],
                "accepted",
                True,
                "analyst consensus is an independent lane input",
            ))
    if earnings_cache.get("transcript") is None:
        records.append(_record(
            f"missing_source:{ticker}:transcript:{as_of}",
            "earnings_transcript",
            None,
            None,
            "company_transcript",
            "earnings-analyst cache transcript",
            as_of,
            "missing",
            False,
            "transcript unavailable",
            "unknown",
        ))
    return records


def _nexus_evidence(ticker: str, nexus_data: dict | None) -> list[dict]:
    records = []
    if not nexus_data:
        return records
    ticker_id = f"ticker:{ticker.upper()}"
    for index, edge in enumerate(nexus_data.get("edges") or []):
        if edge.get("source") != ticker_id and edge.get("target") != ticker_id:
            continue
        edge_type = edge.get("type") or "unknown"
        metadata = edge.get("metadata") or {}
        causal = edge_type in {"SUPPLIES_TO", "CUSTOMER_OF", "CONTRACT_MFG_FOR"}
        corroborated = (
            int(metadata.get("support_count") or 0) >= 2
            or int(metadata.get("cross_item_count") or 0) >= 2
        )
        numeric_eligible = causal and corroborated and bool(metadata.get("conversion_method"))
        status = "accepted" if numeric_eligible else "provisional"
        if edge_type == "CO_THEME":
            reason = "co-theme relation is association, not causal transmission evidence"
        elif not causal:
            reason = "relation type is not an approved causal supply-chain relation"
        elif not corroborated:
            reason = "causal relation lacks independent corroboration"
        elif not metadata.get("conversion_method"):
            reason = "causal relation lacks numeric conversion method"
        else:
            reason = "corroborated causal relation with conversion method"
        records.append(_record(
            f"nexus:{ticker}:{index}",
            "external_transmission_relation",
            None,
            None,
            "nexus_relation",
            ",".join(edge.get("sources") or []) or "Dashboard/nexus_graph.json",
            edge.get("last_seen") or "unknown",
            status,
            numeric_eligible,
            reason,
            "medium" if causal else "low",
            {
                "source": edge.get("source"),
                "target": edge.get("target"),
                "relation_type": edge_type,
                "support_count": metadata.get("support_count"),
                "cross_item_count": metadata.get("cross_item_count"),
            },
        ))
    return records


def _primary_source_evidence(primary_acquisition: dict | None) -> list[dict]:
    records = []
    for status_key, status in (("promoted", "accepted"), ("provisional", "provisional")):
        for candidate in (primary_acquisition or {}).get(status_key) or []:
            records.append(_record(
                f"primary:{candidate['candidate_id']}",
                candidate.get("driver"),
                candidate.get("value"),
                candidate.get("unit"),
                candidate.get("source_type"),
                candidate.get("source_ref"),
                candidate.get("published_at") or "unknown",
                status,
                bool(candidate.get("numeric_eligible")),
                candidate.get("promotion_reason") or "primary-source candidate",
                "high" if status == "accepted" else "medium",
                {
                    "period": candidate.get("period"),
                    "evidence_snippet": candidate.get("evidence_snippet"),
                    "missing_for_promotion": candidate.get("missing_for_promotion") or [],
                    "document_id": candidate.get("document_id"),
                },
            ))
    for status_key, status in (("guidance_promoted", "accepted"), ("guidance_provisional", "provisional")):
        for candidate in (primary_acquisition or {}).get(status_key) or []:
            records.append(_record(
                f"guidance:{candidate['candidate_id']}",
                f"guidance:{candidate.get('metric')}",
                candidate.get("value"),
                candidate.get("unit"),
                candidate.get("source_type"),
                candidate.get("source_ref"),
                candidate.get("published_at") or "unknown",
                status,
                bool(candidate.get("numeric_eligible")),
                candidate.get("promotion_reason") or "management guidance candidate",
                "high" if status == "accepted" else "medium",
                {
                    "value_type": candidate.get("value_type"),
                    "guidance_kind": candidate.get("guidance_kind"),
                    "period": candidate.get("period"),
                    "evidence_snippet": candidate.get("evidence_snippet"),
                    "missing_for_promotion": candidate.get("missing_for_promotion") or [],
                    "document_id": candidate.get("document_id"),
                },
            ))
    return records


def _discovered_source_evidence(source_discovery: dict | None) -> list[dict]:
    records = []
    for candidate in (source_discovery or {}).get("candidates") or []:
        records.append(_record(
            f"discovered:{candidate['source_id']}",
            "primary_source_candidate",
            None,
            None,
            candidate.get("source_type"),
            candidate.get("source_ref"),
            candidate.get("published_at") or "unknown",
            "provisional",
            False,
            candidate.get("reason") or "source metadata requires document acquisition",
            "medium",
            {
                "channel": candidate.get("channel"),
                "form": candidate.get("form"),
                "filing_family": candidate.get("filing_family"),
                "period": candidate.get("period"),
                "discovery_status": candidate.get("status"),
                "discovery_origin": candidate.get("discovery_origin"),
            },
        ))
    return records


def _revision_evidence(revision_snapshot: dict | None) -> list[dict]:
    if not revision_snapshot:
        return []
    records = []
    latest = revision_snapshot.get("latest_year") or {}
    as_of = revision_snapshot.get("generated_at") or "unknown"
    for metric in ("revenue", "eps"):
        avg = latest.get(f"{metric}_avg")
        if avg is None:
            continue
        records.append(_record(
            f"revision:{revision_snapshot.get('ticker')}:{metric}:{latest.get('date')}",
            f"consensus_revision:{metric}",
            {
                "avg": avg,
                "low": latest.get(f"{metric}_low"),
                "high": latest.get(f"{metric}_high"),
                "spread_pct": latest.get(f"{metric}_spread_pct"),
            },
            "currency" if metric == "revenue" else "currency_per_share",
            "analyst_consensus",
            "earnings-analyst cache annual_estimates",
            latest.get("date") or as_of,
            "accepted",
            True,
            "point-in-time analyst consensus estimate snapshot; revision delta requires future snapshots",
            "medium",
            {
                "value_type": "consensus",
                "estimate_revision_delta_available": revision_snapshot.get("estimate_revision_delta_available"),
                "estimate_revision_delta_reason": revision_snapshot.get("estimate_revision_delta_reason"),
                "num_analysts": latest.get(f"num_analysts_{metric if metric == 'revenue' else 'eps'}"),
            },
        ))
    rating = revision_snapshot.get("rating_momentum") or {}
    if rating.get("available"):
        records.append(_record(
            f"revision:{revision_snapshot.get('ticker')}:rating_momentum:{rating.get('to')}",
            "consensus_revision:rating_momentum",
            {
                "direction": rating.get("direction"),
                "delta": rating.get("delta"),
                "net_bull_from": rating.get("net_bull_from"),
                "net_bull_to": rating.get("net_bull_to"),
            },
            "score_delta",
            "analyst_consensus",
            "earnings-analyst cache analyst_grades",
            rating.get("to") or as_of,
            "accepted",
            True,
            "analyst rating momentum from dated analyst_grades snapshots",
            "medium",
            {"value_type": "consensus", "from": rating.get("from"), "to": rating.get("to")},
        ))
    return records


def _missing_drivers(adapter_id: str, records: list[dict]) -> list[dict]:
    if adapter_id != "royalty_ip":
        return []
    accepted_metrics = {
        record["metric"] for record in records
        if record["status"] == "accepted" and record["numeric_eligible"]
    }
    missing = []
    for driver, spec in REQUIRED_ROYALTY_IP_DRIVERS.items():
        if driver not in accepted_metrics:
            missing.append({
                "driver": driver,
                "status": "missing",
                "purpose": spec["purpose"],
                "preferred_sources": spec["preferred_sources"],
                "promotion_requirement": "point-in-time primary evidence with numeric value and source reference",
            })
    return missing


def build_inventory(ticker: str, earnings_cache: dict, adapter_id: str | None,
                    generated_at: str, nexus_data: dict | None = None,
                    primary_acquisition: dict | None = None,
                    source_discovery: dict | None = None,
                    revision_snapshot: dict | None = None) -> dict:
    if nexus_data is None:
        nexus_data = _read_json(NEXUS_PATH)
    records = (
        _company_evidence(ticker, earnings_cache)
        + _nexus_evidence(ticker, nexus_data)
        + _primary_source_evidence(primary_acquisition)
        + _discovered_source_evidence(source_discovery)
        + _revision_evidence(revision_snapshot)
    )
    accepted = [record for record in records if record["status"] == "accepted"]
    provisional = [record for record in records if record["status"] == "provisional"]
    missing_sources = [record for record in records if record["status"] == "missing"]
    missing_drivers = _missing_drivers(adapter_id or "", records)
    return {
        "ticker": ticker,
        "generated_at": generated_at,
        "adapter_id": adapter_id,
        "summary": {
            "accepted_count": len(accepted),
            "provisional_count": len(provisional),
            "missing_source_count": len(missing_sources),
            "missing_driver_count": len(missing_drivers),
            "numeric_transmission_evidence_count": sum(
                1 for record in accepted if record["metric"] == "external_transmission_relation"
            ),
        },
        "accepted": accepted,
        "provisional": provisional,
        "missing_sources": missing_sources,
        "missing_drivers": missing_drivers,
        "primary_acquisition_summary": (primary_acquisition or {}).get("summary") or {
            "candidate_count": 0, "promoted_count": 0, "provisional_count": 0,
        },
        "source_discovery_summary": {
            "candidate_count": (source_discovery or {}).get("candidate_count", 0),
            "filing_family_counts": (source_discovery or {}).get("filing_family_counts") or {},
        },
        "revision_snapshot_summary": {
            "available": bool((revision_snapshot or {}).get("available")),
            "estimate_revision_delta_available": bool(
                (revision_snapshot or {}).get("estimate_revision_delta_available")
            ),
            "rating_momentum_direction": (
                ((revision_snapshot or {}).get("rating_momentum") or {}).get("direction")
            ),
        },
        "promotion_policy": (
            "Association, narrative, or uncorroborated relation evidence remains provisional. "
            "Numeric drivers require point-in-time primary evidence."
        ),
    }
