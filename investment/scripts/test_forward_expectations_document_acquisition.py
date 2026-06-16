#!/usr/bin/env python3
"""Golden fixtures for bounded document acquisition."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_document_acquisition as da  # noqa: E402
import forward_expectations_primary_sources as ps  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}: got {got!r}, want {want!r}")


def sec_candidate(url="https://www.sec.gov/Archives/edgar/data/1/filing.htm"):
    return {
        "source_id": "filing:TEST:0",
        "source_type": "company_filing",
        "source_url": url,
        "source_ref": url,
        "status": "metadata_only",
        "form": "10-K",
        "filing_family": "annual_report",
        "published_at": "2026-02-01",
        "period": "FY2025",
    }


print("Fixture A (URL policy allowlist):")
allowed, reason = da.url_policy(sec_candidate())
check("allow.sec", allowed, True)
check("allow.reason", reason, "allowlisted_sec_filing_document")
blocked, reason_b = da.url_policy({**sec_candidate("https://example.com/filing.htm")})
check("block.host", blocked, False)
check("block.reason", reason_b, "host_not_allowlisted")
manifest, reason_m = da.url_policy({
    **sec_candidate("https://data.sec.gov/submissions/CIK0000000001.json"),
})
check("block.manifest", manifest, False)
check("block.manifest_reason", reason_m, "sec_manifest_metadata_only")

print("Fixture B (HTML normalizes to text):")
html = "<html><head><style>x</style><script>bad()</script></head><body><h1>Risk</h1><p>Revenue grew</p></body></html>"
text = da.normalize_document_text(html, "text/html")
check("html.contains", "Risk\nRevenue grew" in text, True)
check("html.no_script", "bad()" in text, False)

print("Fixture C (no-fetch skips allowed URL):")
discovery = {"ticker": "TEST", "candidates": [sec_candidate()]}
result = da.acquire_documents(discovery, no_fetch=True)
check("nofetch.docs", result["summary"]["document_count"], 0)
check("nofetch.skip", result["skipped"][0]["reason"], "fetch_disabled")
check("nofetch.network", result["network_fetch_used"], False)

print("Fixture D (cache hit avoids network):")
old_cache = da.CACHE_DIR
old_fetch = da._fetch_url
with tempfile.TemporaryDirectory() as tmp:
    da.CACHE_DIR = tmp
    cached_doc = {
        "document_id": "cached",
        "source_type": "company_filing",
        "source_ref": sec_candidate()["source_url"],
        "source_url": sec_candidate()["source_url"],
        "published_at": "2026-02-01",
        "content": "cached text",
        "status": "normalized_text",
        "numeric_eligible": False,
    }
    da._cache_put(sec_candidate()["source_url"], cached_doc)
    da._fetch_url = lambda url: (_ for _ in ()).throw(AssertionError("network called"))
    cached = da.acquire_documents(discovery, no_fetch=False)
    check("cache.docs", cached["summary"]["document_count"], 1)
    check("cache.hit", cached["summary"]["cache_hit_count"], 1)
    check("cache.network", cached["network_fetch_used"], False)
da.CACHE_DIR = old_cache
da._fetch_url = old_fetch

print("Fixture E (normalized text still needs promotion gate):")
bundle = {
    "documents": [{
        **cached_doc,
        "content": "Risk factors and strategy discussion with no explicit driver metrics.",
    }],
}
acquired = ps.acquire_primary_evidence({"ticker": "TEST", "transcript": None}, bundle)
check("promotion.none", acquired["summary"]["promoted_count"], 0)
check("promotion.candidates", acquired["summary"]["candidate_count"], 0)

print("Fixture F (fetched document becomes primary bundle text, not evidence):")
with tempfile.TemporaryDirectory() as tmp:
    da.CACHE_DIR = tmp
    da._fetch_url = lambda url: (
        "<html><body>In FY2026, 10 billion royalty-bearing units shipped.</body></html>",
        {"http_status": 200, "content_type": "text/html", "truncated": False},
    )
    fetched = da.acquire_documents(discovery, no_fetch=False)
    check("fetch.docs", fetched["summary"]["document_count"], 1)
    check("fetch.network_count", fetched["summary"]["network_fetch_count"], 1)
    check("fetch.non_numeric", fetched["documents"][0]["numeric_eligible"], False)
da.CACHE_DIR = old_cache
da._fetch_url = old_fetch

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
