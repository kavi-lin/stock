#!/usr/bin/env python3
"""Golden fixtures for ticker-neutral primary-source discovery."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_source_discovery as sd  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}: got {got!r}, want {want!r}")


print("Fixture A (US issuer forms are classified from metadata):")
us = sd.discover_sources("TESTUS", {}, {
    "profile": {"cik": "0000123456", "website": "https://example.com"},
    "filing_metadata": [
        {"formType": "10-K", "filingDate": "2026-02-01", "finalLink": "https://sec/10k"},
        {"formType": "10-Q", "filingDate": "2026-05-01", "finalLink": "https://sec/10q"},
        {"formType": "8-K", "filingDate": "2026-05-02", "finalLink": "https://sec/8k"},
    ],
})
check("us.annual", us["filing_family_counts"]["annual_report"], 1)
check("us.interim", us["filing_family_counts"]["interim_report"], 1)
check("us.current", us["filing_family_counts"]["current_report"], 1)
check("us.sec_manifest", any(c["channel"] == "sec_submissions_manifest" for c in us["candidates"]), True)
check("us.all_non_numeric", all(not c["numeric_eligible"] for c in us["candidates"]), True)

print("Fixture B (foreign issuer forms require no ticker-specific rule):")
foreign = sd.discover_sources("ANYFPI", {}, {
    "profile": {"cik": "1973239", "country": "GB"},
    "filing_metadata": [
        {"formType": "20-F", "filingDate": "2026-05-01", "finalLink": "https://sec/20f"},
        {"formType": "6-K", "filingDate": "2026-05-10", "finalLink": "https://sec/6k"},
    ],
})
check("foreign.annual", foreign["filing_family_counts"]["annual_report"], 1)
check("foreign.report", foreign["filing_family_counts"]["foreign_issuer_report"], 1)
check("foreign.no_arm_rule", foreign["ticker"], "ANYFPI")

print("Fixture C (unknown forms remain discoverable, not guessed):")
unknown = sd.discover_sources("FUND", {}, {
    "profile": {},
    "filing_metadata": [{"formType": "N-CSR", "filingDate": "2026-01-01", "finalLink": "https://sec/ncsr"}],
})
check("unknown.family", unknown["filing_family_counts"]["other_or_unknown"], 1)
check("unknown.metadata_only", unknown["candidates"][0]["status"], "metadata_only")

print("Fixture D (missing CIK/website degrades cleanly):")
empty = sd.discover_sources("PRIVATE", {}, {"profile": {}, "filing_metadata": []})
check("empty.count", empty["candidate_count"], 0)
check("empty.network", empty["network_fetch_used"], False)

print("Fixture E (duplicate metadata rows are deduplicated):")
dupe = sd.discover_sources("DUPE", {}, {
    "profile": {},
    "filing_metadata": [
        {"formType": "10-K", "filingDate": "2026-02-01", "finalLink": "https://sec/same"},
        {"formType": "10-K", "filingDate": "2026-02-01", "finalLink": "https://sec/same"},
    ],
})
check("dupe.count", dupe["candidate_count"], 1)

print("Fixture F (transcript content is discovered but not promoted):")
transcript = sd.discover_sources("CALL", {
    "as_of_date": "2026-05-01",
    "transcript": {"year": 2026, "quarter": 1, "date": "2026-05-01", "content": "Prepared remarks"},
}, {"profile": {}, "filing_metadata": []})
check("transcript.status", transcript["candidates"][0]["status"], "content_available")
check("transcript.numeric", transcript["candidates"][0]["numeric_eligible"], False)

print("Fixture G (fresh filing cache avoids provider quota):")
old_cache_dir = sd.SOURCE_CACHE_DIR
old_fetch = sd._fetch_filing_metadata
with tempfile.TemporaryDirectory() as tmp:
    sd.SOURCE_CACHE_DIR = tmp
    sd._write_filing_cache("CACHE", [
        {"formType": "10-Q", "filingDate": "2026-05-01", "finalLink": "https://sec/cached"},
    ])
    sd._fetch_filing_metadata = lambda ticker: (_ for _ in ()).throw(AssertionError("provider called"))
    cached = sd.discover_sources("CACHE", {}, {"profile": {}}, no_fetch=False)
    check("cache.origin", cached["filing_metadata_origin"], "filing_metadata_cache")
    check("cache.no_network", cached["network_fetch_used"], False)
    check("cache.interim", cached["filing_family_counts"]["interim_report"], 1)
sd.SOURCE_CACHE_DIR = old_cache_dir
sd._fetch_filing_metadata = old_fetch

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
