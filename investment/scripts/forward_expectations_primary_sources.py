"""Cache-first primary-source acquisition for Forward Expectations.

Inputs are existing earnings-call transcript caches or explicit filing/IR text bundles.
No web fetch and no LLM inference occurs here. Extraction is deliberately narrow:
only Royalty/IP driver statements with explicit numeric value, unit, period, source
date, and source URL/ref can be promoted.
"""
from __future__ import annotations

import re

from forward_expectations_guidance import extract_guidance_from_documents

SUPPORTED_SOURCE_TYPES = {"company_filing", "company_ir", "earnings_transcript"}

DRIVER_PATTERNS = {
    "royalty_bearing_units": [
        re.compile(
            r"(?P<value>\d+(?:\.\d+)?)\s*(?P<scale>billion|million|bn|m)\s+"
            r"(?P<unit>royalty[- ]bearing units|chips|units)",
            re.I,
        ),
    ],
    "royalty_rate_or_value_per_unit": [
        re.compile(
            r"(?:royalty rate|royalty per (?:chip|unit)|value per (?:chip|unit))"
            r"\s*(?:was|is|of|=|:)?\s*(?P<currency>\$|usd\s*)?"
            r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>%|percent|cents?|dollars?|usd)?",
            re.I,
        ),
    ],
    "license_pipeline_conversion": [
        re.compile(
            r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>%|percent)\s+"
            r"(?:of\s+)?(?:licenses?|license pipeline|signed licenses?)"
            r".{0,80}?(?:converted|conversion|recognized|entered production)",
            re.I,
        ),
    ],
    "data_center_segment_exposure": [
        re.compile(
            r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>%|percent)\s+"
            r"(?:of\s+)?(?:revenue|royalty revenue|royalties).{0,80}?"
            r"(?:data center|datacenter|infrastructure)",
            re.I,
        ),
    ],
}

PERIOD_RE = re.compile(r"\b(FY ?20\d{2}|20\d{2}|Q[1-4](?: FY)? ?20\d{2})\b", re.I)


def transcript_document(earnings_cache: dict) -> dict | None:
    transcript = earnings_cache.get("transcript")
    if not isinstance(transcript, dict) or not transcript.get("content"):
        return None
    ticker = earnings_cache.get("ticker") or "UNKNOWN"
    year = transcript.get("year")
    quarter = transcript.get("quarter")
    return {
        "document_id": f"transcript:{ticker}:{year}:Q{quarter}",
        "source_type": "earnings_transcript",
        "source_ref": f"FMP earning-call-transcript {ticker} {year}Q{quarter}",
        "source_url": f"https://discountingcashflows.com/company/{ticker}/transcripts/",
        "published_at": transcript.get("date") or earnings_cache.get("as_of_date"),
        "content": transcript["content"],
    }


def build_primary_bundle(earnings_cache: dict, explicit_bundle: dict | None = None) -> dict:
    documents = []
    cached_transcript = transcript_document(earnings_cache)
    if cached_transcript:
        documents.append(cached_transcript)
    for document in (explicit_bundle or {}).get("documents") or []:
        if isinstance(document, dict):
            documents.append(document)
    return {
        "ticker": earnings_cache.get("ticker"),
        "documents": documents,
        "document_count": len(documents),
        "cache_first": True,
        "network_fetch_used": False,
    }


def _number(match) -> tuple[float | None, str | None]:
    try:
        value = float(match.group("value"))
    except Exception:
        return None, None
    groups = match.groupdict()
    scale = (groups.get("scale") or "").lower()
    if scale in {"billion", "bn"}:
        value *= 1_000_000_000
    elif scale in {"million", "m"}:
        value *= 1_000_000
    unit = (groups.get("unit") or "").lower() or None
    if unit in {"%", "percent"}:
        value /= 100
        unit = "ratio"
    elif groups.get("currency"):
        unit = "USD_per_unit"
    return value, unit


def _snippet(content: str, start: int, end: int, radius: int = 140) -> str:
    return " ".join(content[max(0, start - radius):min(len(content), end + radius)].split())


def _candidate(document: dict, driver: str, match, content: str, index: int) -> dict:
    value, unit = _number(match)
    snippet = _snippet(content, match.start(), match.end())
    period_match = PERIOD_RE.search(snippet)
    period = period_match.group(0) if period_match else None
    source_type = document.get("source_type")
    source_ref = document.get("source_url") or document.get("source_ref")
    missing = []
    for field, current in (
        ("value", value),
        ("unit", unit),
        ("period", period),
        ("published_at", document.get("published_at")),
        ("source_ref", source_ref),
    ):
        if current in (None, ""):
            missing.append(field)
    if source_type not in SUPPORTED_SOURCE_TYPES:
        missing.append("supported_primary_source_type")
    promoted = not missing
    return {
        "candidate_id": f"{document.get('document_id', 'document')}:{driver}:{index}",
        "driver": driver,
        "value": value,
        "unit": unit,
        "period": period,
        "source_type": source_type,
        "source_ref": source_ref,
        "published_at": document.get("published_at"),
        "document_id": document.get("document_id"),
        "evidence_snippet": snippet,
        "status": "promoted" if promoted else "provisional",
        "numeric_eligible": promoted,
        "missing_for_promotion": missing,
        "promotion_reason": (
            "explicit metric, value, unit, period, date, and primary source"
            if promoted else "candidate lacks required promotion fields"
        ),
    }


def acquire_primary_evidence(earnings_cache: dict, explicit_bundle: dict | None = None) -> dict:
    bundle = build_primary_bundle(earnings_cache, explicit_bundle)
    candidates = []
    for document in bundle["documents"]:
        content = document.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        for driver, patterns in DRIVER_PATTERNS.items():
            for pattern in patterns:
                for index, match in enumerate(pattern.finditer(content)):
                    candidates.append(_candidate(document, driver, match, content, index))
    promoted = [candidate for candidate in candidates if candidate["status"] == "promoted"]
    provisional = [candidate for candidate in candidates if candidate["status"] == "provisional"]
    guidance = extract_guidance_from_documents(bundle["documents"])
    guidance_promoted = guidance["promoted"]
    guidance_provisional = guidance["provisional"]
    return {
        "ticker": bundle.get("ticker"),
        "cache_first": True,
        "network_fetch_used": False,
        "document_count": bundle["document_count"],
        "summary": {
            "candidate_count": len(candidates) + guidance["summary"]["candidate_count"],
            "promoted_count": len(promoted) + guidance["summary"]["promoted_count"],
            "provisional_count": len(provisional) + guidance["summary"]["provisional_count"],
            "driver_candidate_count": len(candidates),
            "guidance_candidate_count": guidance["summary"]["candidate_count"],
            "guidance_promoted_count": guidance["summary"]["promoted_count"],
        },
        "promoted": promoted,
        "provisional": provisional,
        "guidance_promoted": guidance_promoted,
        "guidance_provisional": guidance_provisional,
        "documents": [
            {
                "document_id": document.get("document_id"),
                "source_type": document.get("source_type"),
                "source_ref": document.get("source_url") or document.get("source_ref"),
                "published_at": document.get("published_at"),
            }
            for document in bundle["documents"]
        ],
        "policy": (
            "No web fetch; no narrative inference; incomplete candidates remain provisional. "
            "Driver and guidance candidates are separate evidence types."
        ),
    }
