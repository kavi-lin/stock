#!/usr/bin/env python3
"""Golden-fixture regression for cache-first primary-source acquisition."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_primary_sources as ps  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want, tol=None):
    global PASS, FAIL
    ok = (abs(got - want) <= tol) if (tol is not None and got is not None) else (got == want)
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}: got {got!r}, want {want!r}")


print("Fixture A (complete primary statements promote):")
cache = {"ticker": "ARM", "transcript": None}
bundle = {
    "documents": [{
        "document_id": "ir:arm:fy2026",
        "source_type": "company_ir",
        "source_url": "https://example.com/arm-fy2026",
        "published_at": "2026-05-06",
        "content": (
            "In FY2026, 35 billion royalty-bearing units shipped. "
            "Royalty rate was 2.5 percent in FY2026. "
            "In FY2026, 40 percent of signed licenses converted to production. "
            "In FY2026, 18 percent of royalty revenue came from data center infrastructure."
        ),
    }],
}
result = ps.acquire_primary_evidence(cache, bundle)
check("complete.documents", result["document_count"], 1)
check("complete.promoted_count", result["summary"]["promoted_count"], 4)
promoted = {candidate["driver"]: candidate for candidate in result["promoted"]}
check("units.value", promoted["royalty_bearing_units"]["value"], 35_000_000_000)
check("units.unit", promoted["royalty_bearing_units"]["unit"], "royalty-bearing units")
check("rate.value", promoted["royalty_rate_or_value_per_unit"]["value"], 0.025, tol=1e-9)
check("license.value", promoted["license_pipeline_conversion"]["value"], 0.40, tol=1e-9)
check("dc.value", promoted["data_center_segment_exposure"]["value"], 0.18, tol=1e-9)
check("network.false", result["network_fetch_used"], False)

print("Fixture B (missing URL/date/period stays provisional):")
bad = {
    "documents": [{
        "document_id": "notes",
        "source_type": "company_ir",
        "content": "Royalty rate was 3 percent.",
    }],
}
result_b = ps.acquire_primary_evidence(cache, bad)
check("bad.promoted", result_b["summary"]["promoted_count"], 0)
check("bad.provisional", result_b["summary"]["provisional_count"], 1)
missing = result_b["provisional"][0]["missing_for_promotion"]
check("bad.missing_period", "period" in missing, True)
check("bad.missing_published", "published_at" in missing, True)
check("bad.missing_source", "source_ref" in missing, True)

print("Fixture C (unsupported narrative source cannot promote):")
narrative = {
    "documents": [{
        "document_id": "report",
        "source_type": "investment_report",
        "source_url": "https://example.com/report",
        "published_at": "2026-05-06",
        "content": "In FY2026, 80 percent of revenue came from data center infrastructure.",
    }],
}
result_c = ps.acquire_primary_evidence(cache, narrative)
check("narrative.promoted", result_c["summary"]["promoted_count"], 0)
check("narrative.unsupported",
      "supported_primary_source_type" in result_c["provisional"][0]["missing_for_promotion"], True)

print("Fixture D (cached transcript is reused):")
with_transcript = {
    "ticker": "ARM",
    "as_of_date": "2026-05-06",
    "transcript": {
        "year": 2026,
        "quarter": 4,
        "date": "2026-05-06",
        "content": "In FY2026, 22 billion royalty-bearing units shipped.",
    },
}
result_d = ps.acquire_primary_evidence(with_transcript)
check("transcript.documents", result_d["document_count"], 1)
check("transcript.promoted", result_d["summary"]["promoted_count"], 1)
check("transcript.source_type", result_d["promoted"][0]["source_type"], "earnings_transcript")

print("Fixture E (irrelevant numeric prose does not extract):")
irrelevant = {
    "documents": [{
        "document_id": "ir:irrelevant",
        "source_type": "company_ir",
        "source_url": "https://example.com/irrelevant",
        "published_at": "2026-05-06",
        "content": "Revenue grew 35 percent in FY2026 and gross margin was 95 percent.",
    }],
}
result_e = ps.acquire_primary_evidence(cache, irrelevant)
check("irrelevant.candidates", result_e["summary"]["candidate_count"], 0)

print("Fixture F (management guidance is separate from driver evidence):")
guidance_bundle = {
    "documents": [{
        "document_id": "ir:guidance",
        "source_type": "company_ir",
        "source_url": "https://example.com/guidance",
        "published_at": "2026-05-06",
        "content": "For FY2026, management expects revenue in the range of $10 billion to $12 billion.",
    }],
}
result_f = ps.acquire_primary_evidence(cache, guidance_bundle)
check("guidance.total_candidates", result_f["summary"]["candidate_count"], 1)
check("guidance.driver_candidates", result_f["summary"]["driver_candidate_count"], 0)
check("guidance.promoted", result_f["summary"]["guidance_promoted_count"], 1)
check("guidance.metric", result_f["guidance_promoted"][0]["metric"], "revenue")
check("guidance.not_driver_promoted", len(result_f["promoted"]), 0)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
