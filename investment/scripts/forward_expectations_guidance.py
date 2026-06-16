"""Ticker-neutral management guidance extraction.

Extracts only explicit company guidance / outlook statements from primary-source
documents. Guidance ranges stay ranges; midpoint is a derived helper, not a
management-stated value. No LLM inference is used.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

METRIC_ALIASES = {
    "revenue": r"(?:revenue|sales|net sales)",
    "eps": r"(?:eps|earnings per share|diluted eps)",
    "gross_margin": r"(?:gross margin)",
    "operating_margin": r"(?:operating margin|operating profit margin)",
    "free_cash_flow": r"(?:free cash flow|fcf)",
    "capex": r"(?:capex|capital expenditures|capital expenditure)",
}

GUIDANCE_WORDS = r"(?:guidance|outlook|expects?|expected|forecast|projects?|projected|sees|anticipates?)"
PERIOD_RE = re.compile(r"\b(FY ?20\d{2}|fiscal ?20\d{2}|20\d{2}|Q[1-4](?: FY)? ?20\d{2})\b", re.I)


def _range_pattern(metric: str) -> re.Pattern:
    alias = METRIC_ALIASES[metric]
    return re.compile(
        rf"(?P<period>FY ?20\d{{2}}|fiscal ?20\d{{2}}|20\d{{2}}|Q[1-4](?: FY)? ?20\d{{2}})?"
        rf".{{0,80}}?(?:{GUIDANCE_WORDS}).{{0,80}}?"
        rf"(?P<metric>{alias}).{{0,80}}?"
        rf"(?:range|between|of|to be|at)?\s*"
        rf"(?P<prefix1>\$)?(?P<low>\d+(?:\.\d+)?)\s*(?P<unit1>%|percent|bps|basis points|billion|million|bn|m)?"
        rf"\s*(?:-|–|—|to|and)\s*"
        rf"(?P<prefix2>\$)?(?P<high>\d+(?:\.\d+)?)\s*(?P<unit2>%|percent|bps|basis points|billion|million|bn|m)?",
        re.I,
    )


def _single_pattern(metric: str) -> re.Pattern:
    alias = METRIC_ALIASES[metric]
    return re.compile(
        rf"(?P<period>FY ?20\d{{2}}|fiscal ?20\d{{2}}|20\d{{2}}|Q[1-4](?: FY)? ?20\d{{2}})?"
        rf".{{0,80}}?(?:{GUIDANCE_WORDS}).{{0,80}}?"
        rf"(?P<metric>{alias}).{{0,80}}?"
        rf"(?:of|to be|at|approximately|about|around)?\s*"
        rf"(?P<prefix>\$)?(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>%|percent|bps|basis points|billion|million|bn|m)?",
        re.I,
    )


RANGE_PATTERNS = {metric: _range_pattern(metric) for metric in METRIC_ALIASES}
SINGLE_PATTERNS = {metric: _single_pattern(metric) for metric in METRIC_ALIASES}


def _snippet(content: str, start: int, end: int, radius: int = 180) -> str:
    return " ".join(content[max(0, start - radius):min(len(content), end + radius)].split())


def _unit(groups: dict) -> str | None:
    raw = (
        groups.get("unit") or groups.get("unit2") or groups.get("unit1")
        or ("currency" if groups.get("prefix") or groups.get("prefix1") or groups.get("prefix2") else None)
    )
    if raw is None:
        return None
    lowered = raw.lower()
    if lowered in {"%", "percent"}:
        return "ratio"
    if lowered in {"bps", "basis points"}:
        return "basis_points"
    if lowered in {"billion", "bn", "million", "m"}:
        return "currency"
    if lowered == "currency":
        return "currency"
    return lowered


def _scale(value: float, groups: dict, unit_key: str | None = None) -> float:
    raw = (groups.get(unit_key) if unit_key else None) or groups.get("unit") or groups.get("unit2") or groups.get("unit1")
    raw = (raw or "").lower()
    if raw in {"%", "percent"}:
        return value / 100
    if raw in {"billion", "bn"}:
        return value * 1_000_000_000
    if raw in {"million", "m"}:
        return value * 1_000_000
    return value


def _period(match, snippet: str) -> str | None:
    if match.groupdict().get("period"):
        return match.group("period")
    found = PERIOD_RE.search(snippet)
    return found.group(0) if found else None


def _candidate(document: dict, metric: str, match, content: str, index: int, kind: str) -> dict:
    groups = match.groupdict()
    snippet = _snippet(content, match.start(), match.end())
    unit = _unit(groups)
    if kind == "range":
        low = _scale(float(groups["low"]), groups, "unit1")
        high = _scale(float(groups["high"]), groups, "unit2")
        if low > high:
            low, high = high, low
        value = {"low": low, "high": high, "midpoint": (low + high) / 2}
    else:
        raw = _scale(float(groups["value"]), groups)
        value = {"point": raw}
    source_ref = document.get("source_url") or document.get("source_ref")
    period = _period(match, snippet)
    missing = []
    for field, current in (
        ("unit", unit),
        ("period", period),
        ("published_at", document.get("published_at")),
        ("source_ref", source_ref),
    ):
        if current in (None, ""):
            missing.append(field)
    promoted = not missing and document.get("source_type") in {"company_filing", "company_ir", "earnings_transcript"}
    if document.get("source_type") not in {"company_filing", "company_ir", "earnings_transcript"}:
        missing.append("supported_primary_source_type")
    return {
        "candidate_id": f"{document.get('document_id', 'document')}:guidance:{metric}:{index}",
        "metric": metric,
        "value_type": "guided",
        "guidance_kind": kind,
        "value": value,
        "unit": unit,
        "period": period,
        "source_type": document.get("source_type"),
        "source_ref": source_ref,
        "published_at": document.get("published_at"),
        "document_id": document.get("document_id"),
        "evidence_snippet": snippet,
        "status": "promoted" if promoted else "provisional",
        "numeric_eligible": promoted,
        "missing_for_promotion": missing,
        "promotion_reason": (
            "explicit company guidance with metric, value/range, unit, period, date, and primary source"
            if promoted else "guidance candidate lacks required promotion fields"
        ),
    }


def extract_guidance_from_documents(documents: list[dict]) -> dict:
    candidates = []
    range_metrics_by_document = {}
    for document in documents:
        content = document.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        for metric, pattern in RANGE_PATTERNS.items():
            for index, match in enumerate(pattern.finditer(content)):
                range_metrics_by_document.setdefault(document.get("document_id"), set()).add(metric)
                candidates.append(_candidate(document, metric, match, content, index, "range"))
        for metric, pattern in SINGLE_PATTERNS.items():
            if metric in range_metrics_by_document.get(document.get("document_id"), set()):
                continue
            for index, match in enumerate(pattern.finditer(content)):
                candidates.append(_candidate(document, metric, match, content, index, "point"))
    promoted = [candidate for candidate in candidates if candidate["status"] == "promoted"]
    provisional = [candidate for candidate in candidates if candidate["status"] == "provisional"]
    return {
        "summary": {
            "candidate_count": len(candidates),
            "promoted_count": len(promoted),
            "provisional_count": len(provisional),
        },
        "promoted": promoted,
        "provisional": provisional,
        "policy": "Guidance ranges remain ranges; midpoint is derived helper only.",
    }


def main():
    ap = argparse.ArgumentParser(description="Extract explicit management guidance from a primary bundle")
    ap.add_argument("--primary-source-file", required=True)
    args = ap.parse_args()
    try:
        with open(args.primary_source_file, encoding="utf-8") as handle:
            bundle = json.load(handle)
    except Exception as exc:
        print(json.dumps({"error": f"unparseable primary-source file: {exc}"}))
        sys.exit(1)
    result = extract_guidance_from_documents((bundle or {}).get("documents") or [])
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
