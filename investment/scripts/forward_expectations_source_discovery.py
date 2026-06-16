"""Ticker-neutral primary-source discovery for Forward Expectations.

Discovery identifies where evidence may exist. It never downloads document text,
extracts driver values, or promotes metadata into numeric evidence. Filing forms
are classified from returned metadata rather than inferred from ticker, country,
industry, or adapter.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROFILE_CACHE_DIR = os.path.join(BASE_DIR, "skills", "_shared", "cache")
SOURCE_CACHE_DIR = os.path.join(
    BASE_DIR, "investment", "invest_logs", "forward_expectations_source_discovery_cache",
)
SOURCE_CACHE_TTL_HOURS = 24

FORM_FAMILIES = {
    "annual_report": {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"},
    "interim_report": {"10-Q", "10-Q/A"},
    # A 6-K can contain interim results or a material event. Metadata alone cannot
    # distinguish those cases, so discovery keeps the classification neutral.
    "foreign_issuer_report": {"6-K", "6-K/A"},
    "current_report": {"8-K", "8-K/A"},
    "proxy": {"DEF 14A", "DEFA14A"},
    "registration": {"S-1", "S-1/A", "F-1", "F-1/A", "S-3", "F-3"},
}


def classify_form(form: str | None) -> str:
    normalized = re.sub(r"\s+", " ", (form or "").strip().upper())
    for family, forms in FORM_FAMILIES.items():
        if normalized in forms:
            return family
    return "other_or_unknown"


def _read_json(path: str):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def _cached_profile(ticker: str) -> dict:
    data = _read_json(os.path.join(PROFILE_CACHE_DIR, f"{ticker.upper()}_profile.json"))
    return data if isinstance(data, dict) else {}


def _filing_cache_path(ticker: str) -> str:
    return os.path.join(SOURCE_CACHE_DIR, f"{ticker.upper()}_filing_metadata.json")


def _cached_filings(ticker: str) -> list[dict] | None:
    path = _filing_cache_path(ticker)
    try:
        if (time.time() - os.path.getmtime(path)) / 3600 > SOURCE_CACHE_TTL_HOURS:
            return None
    except OSError:
        return None
    data = _read_json(path)
    return data if isinstance(data, list) else None


def _write_filing_cache(ticker: str, rows: list[dict]) -> None:
    try:
        os.makedirs(SOURCE_CACHE_DIR, exist_ok=True)
        with open(_filing_cache_path(ticker), "w", encoding="utf-8") as handle:
            json.dump(rows, handle, ensure_ascii=False, indent=2, allow_nan=False)
    except Exception:
        pass


def _fetch_profile(ticker: str) -> dict:
    try:
        from skills._shared.company_context import get_profile
        return get_profile(ticker) or {}
    except Exception:
        return {}


def _fetch_filing_metadata(ticker: str) -> list[dict]:
    try:
        from scripts._shared import fmp_pool
        rows = fmp_pool.get(
            "sec-filings-financials",
            {"symbol": ticker, "limit": 40},
            stable=True,
            retries=1,
            timeout=15,
            hard_fail=False,
        )
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


def _filing_candidate(ticker: str, row: dict, origin: str, index: int) -> dict | None:
    form = row.get("formType") or row.get("form") or row.get("type")
    url = row.get("finalLink") or row.get("link") or row.get("reportUrl") or row.get("source")
    published = (
        row.get("filingDate") or row.get("filedDate") or row.get("acceptedDate")
        or row.get("date")
    )
    period = row.get("periodOfReport") or row.get("period") or row.get("calendarYear")
    if not any((form, url, published, period)):
        return None
    return {
        "source_id": f"filing:{ticker}:{index}",
        "source_type": "company_filing",
        "channel": "regulatory_filing",
        "form": form,
        "filing_family": classify_form(form),
        "published_at": published,
        "period": period,
        "source_url": url,
        "source_ref": url or f"{ticker} {form or 'filing'} metadata",
        "status": "metadata_only",
        "numeric_eligible": False,
        "discovery_origin": origin,
        "reason": "Filing metadata identifies a candidate source; document content is not acquired.",
    }


def _profile_candidates(ticker: str, profile: dict) -> list[dict]:
    candidates = []
    website = profile.get("website")
    if website:
        candidates.append({
            "source_id": f"website:{ticker}",
            "source_type": "company_ir",
            "channel": "company_website_root",
            "form": None,
            "filing_family": None,
            "published_at": None,
            "period": None,
            "source_url": website,
            "source_ref": website,
            "status": "metadata_only",
            "numeric_eligible": False,
            "discovery_origin": "company_profile",
            "reason": "Company website is a discovery root, not a verified IR document.",
        })
    cik = str(profile.get("cik") or "").strip()
    digits = re.sub(r"\D", "", cik)
    if digits:
        submissions_url = f"https://data.sec.gov/submissions/CIK{digits.zfill(10)}.json"
        candidates.append({
            "source_id": f"sec-submissions:{ticker}",
            "source_type": "company_filing",
            "channel": "sec_submissions_manifest",
            "form": None,
            "filing_family": None,
            "published_at": None,
            "period": None,
            "source_url": submissions_url,
            "source_ref": submissions_url,
            "status": "metadata_only",
            "numeric_eligible": False,
            "discovery_origin": "company_profile_cik",
            "reason": "SEC submissions manifest can enumerate filings; it contains no driver evidence.",
        })
    return candidates


def _transcript_candidate(ticker: str, earnings_cache: dict) -> dict | None:
    transcript = earnings_cache.get("transcript")
    if not isinstance(transcript, dict):
        return None
    year = transcript.get("year")
    quarter = transcript.get("quarter")
    return {
        "source_id": f"transcript:{ticker}:{year}:Q{quarter}",
        "source_type": "earnings_transcript",
        "channel": "earnings_transcript",
        "form": None,
        "filing_family": None,
        "published_at": transcript.get("date") or earnings_cache.get("as_of_date"),
        "period": f"{year}Q{quarter}" if year and quarter else None,
        "source_url": transcript.get("url"),
        "source_ref": transcript.get("url") or f"earnings transcript {ticker} {year}Q{quarter}",
        "status": "content_available" if transcript.get("content") else "metadata_only",
        "numeric_eligible": False,
        "discovery_origin": "earnings_cache",
        "reason": "Transcript discovery does not promote any statement without extraction gates.",
    }


def _deduplicate(candidates: list[dict]) -> list[dict]:
    output = []
    seen = set()
    for candidate in candidates:
        key = (
            candidate.get("source_url") or candidate.get("source_ref"),
            candidate.get("form"),
            candidate.get("published_at"),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(candidate)
    return output


def discover_sources(ticker: str, earnings_cache: dict, explicit: dict | None = None,
                     no_fetch: bool = True) -> dict:
    """Return a point-in-time discovery manifest without acquiring document text."""
    ticker = ticker.upper()
    explicit = explicit or {}
    profile = explicit.get("profile")
    profile_origin = "explicit"
    if not isinstance(profile, dict):
        profile = _cached_profile(ticker)
        profile_origin = "profile_cache"
    if not profile and not no_fetch:
        profile = _fetch_profile(ticker)
        profile_origin = "provider_fetch"

    filings = explicit.get("filing_metadata")
    filings_origin = "explicit"
    if not isinstance(filings, list):
        filings = _cached_filings(ticker)
        filings_origin = "filing_metadata_cache"
        if filings is None and not no_fetch:
            filings = _fetch_filing_metadata(ticker)
            filings_origin = "fmp_sec_filings_financials"
            if filings:
                _write_filing_cache(ticker, filings)
        elif filings is None:
            filings = []
            filings_origin = "not_fetched"

    candidates = _profile_candidates(ticker, profile)
    for index, row in enumerate(filings):
        if isinstance(row, dict):
            candidate = _filing_candidate(ticker, row, filings_origin, index)
            if candidate:
                candidates.append(candidate)
    transcript = _transcript_candidate(ticker, earnings_cache)
    if transcript:
        candidates.append(transcript)
    candidates = _deduplicate(candidates)

    filing_family_counts = {}
    for candidate in candidates:
        family = candidate.get("filing_family")
        if family:
            filing_family_counts[family] = filing_family_counts.get(family, 0) + 1
    return {
        "ticker": ticker,
        "profile_origin": profile_origin,
        "filing_metadata_origin": filings_origin,
        "network_fetch_used": filings_origin == "fmp_sec_filings_financials",
        "candidate_count": len(candidates),
        "filing_family_counts": filing_family_counts,
        "candidates": candidates,
        "policy": (
            "Ticker-neutral discovery classifies observed metadata only. "
            "No document text, driver value, or numeric evidence is promoted."
        ),
    }


def main():
    ap = argparse.ArgumentParser(description="Ticker-neutral primary-source discovery manifest")
    ap.add_argument("ticker")
    ap.add_argument("--from-file", help="optional JSON containing earnings_cache/source_discovery")
    ap.add_argument("--no-fetch", action="store_true", help="use local caches and explicit metadata only")
    args = ap.parse_args()
    payload = {}
    if args.from_file:
        try:
            payload = _read_json(args.from_file)
            if not isinstance(payload, dict):
                raise ValueError("input must be a JSON object")
        except Exception as exc:
            print(json.dumps({"error": f"unparseable input: {exc}"}))
            sys.exit(1)
    result = discover_sources(
        args.ticker,
        payload.get("earnings_cache") or {},
        payload.get("source_discovery"),
        no_fetch=args.no_fetch,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
