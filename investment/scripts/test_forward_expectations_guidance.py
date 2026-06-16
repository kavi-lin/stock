#!/usr/bin/env python3
"""Golden fixtures for ticker-neutral management guidance extraction."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_guidance as gd  # noqa: E402

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


def doc(content, **extra):
    return {
        "document_id": "ir:guidance",
        "source_type": "company_ir",
        "source_ref": "https://example.com/ir",
        "published_at": "2026-05-01",
        "content": content,
        **extra,
    }


print("Fixture A (revenue range preserves range and midpoint helper):")
result = gd.extract_guidance_from_documents([
    doc("For FY2026, management expects revenue in the range of $10 billion to $12 billion."),
])
check("range.promoted", result["summary"]["promoted_count"], 1)
item = result["promoted"][0]
check("range.metric", item["metric"], "revenue")
check("range.low", item["value"]["low"], 10_000_000_000)
check("range.high", item["value"]["high"], 12_000_000_000)
check("range.mid", item["value"]["midpoint"], 11_000_000_000)
check("range.kind", item["guidance_kind"], "range")
check("range.value_type", item["value_type"], "guided")

print("Fixture B (EPS point guidance):")
eps = gd.extract_guidance_from_documents([
    doc("The company expects diluted EPS of $4.25 for FY2026."),
])
check("eps.promoted", eps["summary"]["promoted_count"], 1)
check("eps.metric", eps["promoted"][0]["metric"], "eps")
check("eps.point", eps["promoted"][0]["value"]["point"], 4.25)
check("eps.unit", eps["promoted"][0]["unit"], "currency")

print("Fixture C (margin percentage range):")
margin = gd.extract_guidance_from_documents([
    doc("For Q1 FY2026, our outlook calls for gross margin between 56 percent and 58 percent."),
])
check("margin.metric", margin["promoted"][0]["metric"], "gross_margin")
check("margin.low", margin["promoted"][0]["value"]["low"], 0.56, tol=1e-9)
check("margin.high", margin["promoted"][0]["value"]["high"], 0.58, tol=1e-9)
check("margin.unit", margin["promoted"][0]["unit"], "ratio")

print("Fixture D (missing date/source remains provisional):")
bad = gd.extract_guidance_from_documents([
    doc("FY2026 guidance expects revenue of $10 billion.", published_at=None, source_ref=None, source_url=None),
])
check("bad.promoted", bad["summary"]["promoted_count"], 0)
check("bad.provisional", bad["summary"]["provisional_count"], 1)
check("bad.missing_date", "published_at" in bad["provisional"][0]["missing_for_promotion"], True)
check("bad.missing_source", "source_ref" in bad["provisional"][0]["missing_for_promotion"], True)

print("Fixture E (unsupported narrative source cannot promote):")
narrative = gd.extract_guidance_from_documents([
    doc("FY2026 guidance expects revenue of $10 billion.", source_type="investment_report"),
])
check("narrative.promoted", narrative["summary"]["promoted_count"], 0)
check("narrative.unsupported",
      "supported_primary_source_type" in narrative["provisional"][0]["missing_for_promotion"], True)

print("Fixture F (historical result without guidance words does not extract):")
hist = gd.extract_guidance_from_documents([
    doc("Revenue was $10 billion in FY2026 and gross margin was 58 percent."),
])
check("historical.candidates", hist["summary"]["candidate_count"], 0)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
