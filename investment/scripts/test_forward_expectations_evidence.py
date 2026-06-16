#!/usr/bin/env python3
"""Golden-fixture regression for point-in-time Forward Expectations evidence."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_evidence as ev  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}: got {got!r}, want {want!r}")


EARNINGS = {
    "as_of_date": "2026-05-07",
    "segments": {
        "product_fy": [
            {"date": "2024-03-31", "products": {"Royalty": 100, "License": 50}},
            {"date": "2025-03-31", "products": {"Royalty": 130, "License": 70}},
        ],
    },
    "derived": {
        "yoy_growth": {"revenue_yoy": 0.25},
        "margins_8q": [{"gross": 0.94}],
    },
    "annual_estimates": [{"date": "2028-03-31", "revenue_avg": 500}],
    "transcript": None,
}

NEXUS = {
    "edges": [
        {
            "source": "ticker:ARM",
            "target": "ticker:MSFT",
            "type": "CO_THEME",
            "sources": ["co_theme:narrative:info"],
            "metadata": {},
        },
        {
            "source": "ticker:ARM",
            "target": "ticker:CLIENT",
            "type": "SUPPLIES_TO",
            "sources": ["break_news:a"],
            "metadata": {"support_count": 1},
        },
        {
            "source": "ticker:ARM",
            "target": "ticker:VERIFIED",
            "type": "SUPPLIES_TO",
            "sources": ["company_ir:a", "customer_ir:b"],
            "metadata": {
                "support_count": 2,
                "conversion_method": "units_times_value_per_unit",
            },
            "last_seen": "2026-06-01",
        },
    ],
}

print("Fixture A (company facts accepted, missing transcript retained):")
inventory = ev.build_inventory("ARM", EARNINGS, "royalty_ip", "2026-06-16T00:00:00+00:00", NEXUS)
accepted_metrics = {record["metric"] for record in inventory["accepted"]}
check("company.royalty", "segment_revenue:royalty" in accepted_metrics, True)
check("company.latest_only", len([m for m in accepted_metrics if m == "segment_revenue:royalty"]), 1)
check("company.revenue_yoy", "revenue_yoy" in accepted_metrics, True)
check("company.consensus", "consensus_revenue" in accepted_metrics, True)
check("missing.transcript", inventory["missing_sources"][0]["metric"], "earnings_transcript")

print("Fixture B (Nexus association and weak relation remain provisional):")
provisional = inventory["provisional"]
check("nexus.provisional_count", len(provisional), 2)
check("nexus.co_theme_numeric", provisional[0]["numeric_eligible"], False)
check("nexus.co_theme_reason", "association" in provisional[0]["reason"], True)
check("nexus.weak_causal_numeric", provisional[1]["numeric_eligible"], False)

print("Fixture C (corroborated causal relation with conversion is accepted):")
numeric_transmission = [
    record for record in inventory["accepted"]
    if record["metric"] == "external_transmission_relation"
]
check("nexus.numeric_count", len(numeric_transmission), 1)
check("nexus.numeric_eligible", numeric_transmission[0]["numeric_eligible"], True)
check("summary.numeric_transmission", inventory["summary"]["numeric_transmission_evidence_count"], 1)

print("Fixture D (required Royalty/IP drivers stay explicitly missing):")
missing = {item["driver"] for item in inventory["missing_drivers"]}
check("missing.units", "royalty_bearing_units" in missing, True)
check("missing.rate", "royalty_rate_or_value_per_unit" in missing, True)
check("missing.license_conversion", "license_pipeline_conversion" in missing, True)
check("missing.data_center_exposure", "data_center_segment_exposure" in missing, True)
check("summary.missing_driver_count", inventory["summary"]["missing_driver_count"], 4)

print("Fixture E (promoted primary evidence enters accepted inventory):")
primary = {
    "summary": {"candidate_count": 2, "promoted_count": 1, "provisional_count": 1},
    "promoted": [{
        "candidate_id": "ir:units",
        "driver": "royalty_bearing_units",
        "value": 10_000_000_000,
        "unit": "royalty-bearing units",
        "period": "FY2026",
        "source_type": "company_ir",
        "source_ref": "https://example.com/ir",
        "published_at": "2026-05-06",
        "evidence_snippet": "In FY2026, 10 billion royalty-bearing units shipped.",
        "numeric_eligible": True,
        "promotion_reason": "complete",
    }],
    "provisional": [{
        "candidate_id": "notes:rate",
        "driver": "royalty_rate_or_value_per_unit",
        "value": 0.02,
        "unit": "ratio",
        "period": None,
        "source_type": "company_ir",
        "source_ref": None,
        "published_at": None,
        "evidence_snippet": "Royalty rate was 2 percent.",
        "numeric_eligible": False,
        "promotion_reason": "incomplete",
        "missing_for_promotion": ["period", "published_at", "source_ref"],
    }],
}
inventory_e = ev.build_inventory("ARM", EARNINGS, "royalty_ip",
                                 "2026-06-16T00:00:00+00:00", NEXUS, primary)
check("primary.accepted", any(r["metric"] == "royalty_bearing_units" for r in inventory_e["accepted"]), True)
check("primary.provisional", any(r["metric"] == "royalty_rate_or_value_per_unit"
                                 for r in inventory_e["provisional"]), True)
check("primary.units_not_missing", any(m["driver"] == "royalty_bearing_units"
                                       for m in inventory_e["missing_drivers"]), False)

print("Fixture F (discovered sources remain provisional and non-numeric):")
discovery = {
    "candidate_count": 1,
    "filing_family_counts": {"annual_report": 1},
    "candidates": [{
        "source_id": "filing:GENERIC:0",
        "source_type": "company_filing",
        "source_ref": "https://sec/filing",
        "published_at": "2026-05-01",
        "channel": "regulatory_filing",
        "form": "20-F",
        "filing_family": "annual_report",
        "period": "2025",
        "status": "metadata_only",
        "numeric_eligible": False,
        "discovery_origin": "explicit",
        "reason": "metadata only",
    }],
}
inventory_f = ev.build_inventory("GENERIC", EARNINGS, None,
                                 "2026-06-16T00:00:00+00:00", {}, None, discovery)
discovered = [r for r in inventory_f["provisional"] if r["metric"] == "primary_source_candidate"]
check("discovery.provisional", len(discovered), 1)
check("discovery.non_numeric", discovered[0]["numeric_eligible"], False)
check("discovery.summary", inventory_f["source_discovery_summary"]["candidate_count"], 1)

print("Fixture G (promoted guidance enters accepted inventory as guided evidence):")
guidance_primary = {
    "summary": {"candidate_count": 1, "promoted_count": 1, "provisional_count": 0},
    "guidance_promoted": [{
        "candidate_id": "ir:guidance:revenue:0",
        "metric": "revenue",
        "value_type": "guided",
        "guidance_kind": "range",
        "value": {"low": 10, "high": 12, "midpoint": 11},
        "unit": "currency",
        "period": "FY2026",
        "source_type": "company_ir",
        "source_ref": "https://example.com/ir",
        "published_at": "2026-05-06",
        "document_id": "ir",
        "evidence_snippet": "expects revenue in the range",
        "numeric_eligible": True,
        "promotion_reason": "complete guidance",
    }],
    "guidance_provisional": [],
}
inventory_g = ev.build_inventory("GENERIC", EARNINGS, None,
                                 "2026-06-16T00:00:00+00:00", {}, guidance_primary)
guided = [r for r in inventory_g["accepted"] if r["metric"] == "guidance:revenue"]
check("guidance.accepted", len(guided), 1)
check("guidance.value_type", guided[0]["metadata"]["value_type"], "guided")
check("guidance.kind", guided[0]["metadata"]["guidance_kind"], "range")

print("Fixture H (revision snapshot enters accepted consensus evidence):")
revision = {
    "ticker": "GENERIC",
    "generated_at": "2026-06-16T00:00:00+00:00",
    "available": True,
    "estimate_revision_delta_available": False,
    "estimate_revision_delta_reason": "latest forward curve only",
    "latest_year": {
        "date": "2027-12-31",
        "revenue_avg": 100,
        "revenue_low": 90,
        "revenue_high": 110,
        "revenue_spread_pct": 20,
        "eps_avg": 5,
        "eps_low": 4,
        "eps_high": 6,
        "eps_spread_pct": 40,
        "num_analysts_revenue": 12,
        "num_analysts_eps": 10,
    },
    "rating_momentum": {
        "available": True,
        "from": "2026-01-01",
        "to": "2026-05-01",
        "direction": "UP",
        "delta": 0.1,
        "net_bull_from": 0.5,
        "net_bull_to": 0.6,
    },
}
inventory_h = ev.build_inventory("GENERIC", EARNINGS, None,
                                 "2026-06-16T00:00:00+00:00", {}, None, None, revision)
rev_metrics = {r["metric"] for r in inventory_h["accepted"] if r["metric"].startswith("consensus_revision:")}
check("revision.revenue", "consensus_revision:revenue" in rev_metrics, True)
check("revision.eps", "consensus_revision:eps" in rev_metrics, True)
check("revision.rating", "consensus_revision:rating_momentum" in rev_metrics, True)
check("revision.summary_direction", inventory_h["revision_snapshot_summary"]["rating_momentum_direction"], "UP")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
