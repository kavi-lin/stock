"""Shared news-source taxonomy and deterministic dedupe preference."""

SOURCE_KIND_PRIORITY = {
    "official_regulator": 60,
    "official_macro": 60,
    "company_filing": 55,
    "wire": 50,
    "publisher": 40,
    "aggregator": 30,
    "press_release": 20,
    "social": 10,
    "unknown": 0,
}

SOURCE_KIND_BY_NAME = {
    "Fed Press": "official_macro",
    "SEC Press": "official_regulator",
    "SEC EDGAR": "company_filing",
    "FTC Competition": "official_regulator",
    "Census Indicators": "official_macro",
    "EIA Press": "official_macro",
    "Reuters": "wire",
    "PR Newswire": "press_release",
    "PRNewsWire": "press_release",
    "GlobeNewsWire": "press_release",
    "Business Wire": "press_release",
    "Accesswire": "press_release",
    "Newsfile Corp": "press_release",
    "Yahoo Finance": "aggregator",
    "Finnhub": "aggregator",
    "FMP": "aggregator",
    "Futu Push": "aggregator",
}

_CREDIBILITY_PRIORITY = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}


def infer_source_kind(source_name: str) -> str:
    """Return the stable source class; unlisted editorial outlets are publishers."""
    if source_name in SOURCE_KIND_BY_NAME:
        return SOURCE_KIND_BY_NAME[source_name]
    return "publisher" if source_name else "unknown"


def source_priority(item: dict) -> tuple[int, int]:
    """Rank origin before provider credibility when choosing duplicate coverage."""
    kind = item.get("source_kind")
    if not kind and item.get("_social_source"):
        kind = "social"
    if not kind:
        kind = infer_source_kind(item.get("source", ""))
    credibility = item.get("source_credibility", "MEDIUM")
    return (
        SOURCE_KIND_PRIORITY.get(kind, SOURCE_KIND_PRIORITY["unknown"]),
        _CREDIBILITY_PRIORITY.get(credibility, 0),
    )
