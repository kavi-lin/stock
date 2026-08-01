"""Audited, range-only peer cohorts for sparse provider peer universes.

LLM/manual discovery may propose tickers in config/peer_cohorts.json.  This
module never accepts an LLM-provided multiple: every live observation comes
from the shared deterministic ratio adapter and must pass numeric gates.
"""
from __future__ import annotations

import datetime as dt
import json
import statistics
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR.parent / "config" / "peer_cohorts.json"
MIN_RANGE_PEERS = 3
SUPPORTED_SCHEMA = "valuation_peer_cohorts.v1"


def _pos(value):
    return (float(value) if isinstance(value, (int, float))
            and not isinstance(value, bool) and value > 0 else None)


def load_cohort(ticker: str, path: Path = CONFIG_PATH) -> tuple[dict | None, str | None]:
    """Returns (cohort, reason). A schema this module cannot read is reported,
    not treated as "no cohort configured"."""
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None, "peer_cohort_config_unreadable"
    schema = str(payload.get("schema") or "")
    if schema != SUPPORTED_SCHEMA:
        return None, f"unsupported_cohort_schema:{schema or 'missing'}"
    cohort = (payload.get("cohorts") or {}).get(ticker.upper())
    if not isinstance(cohort, dict):
        return None, "no_curated_peer_cohort"
    return dict(cohort), None


def build_pe_cohort(ticker: str, *, ratios_loader=None, profile_loader=None,
                    as_of: str | None = None) -> dict:
    """Resolve a configured cohort into an auditable P/E scenario."""
    cohort, load_reason = load_cohort(ticker)
    if not cohort:
        return {"eligible": False, "reason": load_reason or "no_curated_peer_cohort",
                "scope": "range_only", "peer_count": 0, "peers": {}}
    if ratios_loader is None or profile_loader is None:
        from skills._shared.company_context import get_profile, get_ratios_ttm
        ratios_loader = ratios_loader or get_ratios_ttm
        profile_loader = profile_loader or get_profile

    peers, excluded = {}, []
    for candidate in cohort.get("candidates") or []:
        symbol = str(candidate.get("ticker") or "").upper()
        if not symbol:
            continue
        ratios = ratios_loader(symbol) or {}
        pe = _pos(ratios.get("pe_ttm"))
        if pe is None:
            excluded.append({"ticker": symbol, "reason": "missing_or_nonpositive_pe"})
            continue
        profile = profile_loader(symbol) or {}
        peers[symbol] = {
            "name": profile.get("companyName") or symbol,
            "role": candidate.get("role"),
            "pe_ttm": round(pe, 4),
            "metric_source": "company_context.get_ratios_ttm",
        }

    eligible = len(peers) >= MIN_RANGE_PEERS
    observed = [p["pe_ttm"] for p in peers.values()]
    median_pe = statistics.median(observed) if eligible else None
    return {
        "eligible": eligible,
        "reason": None if eligible else f"fewer_than_{MIN_RANGE_PEERS}_positive_pe_observations",
        "scope": "range_only",
        "cohort": cohort.get("name"),
        "peer_count": len(peers),
        "median_pe": round(median_pe, 4) if median_pe is not None else None,
        # A 3-name cohort is too small to winsorize; publishing the spread lets
        # a reader see how much one cycle-peak multiple moves the median.
        "pe_min": round(min(observed), 4) if observed else None,
        "pe_max": round(max(observed), 4) if observed else None,
        "peers": peers,
        "excluded": excluded,
        "as_of": as_of or dt.date.today().isoformat(),
        "candidate_provenance": {
            "approved_at": cohort.get("approved_at"),
            "approved_by": cohort.get("approved_by"),
            "discovery_method": cohort.get("discovery_method"),
        },
        "rationale": cohort.get("rationale"),
        "limitations": cohort.get("limitations") or [],
        "reference_only": cohort.get("reference_only") or [],
    }


def _implied_from_pe(subject: dict, peer_pe) -> float | None:
    price, self_pe, peer_pe = (_pos(subject.get("price")), _pos(subject.get("pe")),
                               _pos(peer_pe))
    if not (price and self_pe and peer_pe):
        return None
    return round((price / self_pe) * peer_pe, 2)


def implied_pe_value(subject: dict, cohort: dict) -> float | None:
    """Peer median P/E × subject TTM EPS; never eligible as primary FV."""
    if not cohort.get("eligible"):
        return None
    return _implied_from_pe(subject, cohort.get("median_pe"))


def implied_pe_range(subject: dict, cohort: dict) -> tuple[float | None, float | None]:
    """Implied values at the cohort's lowest and highest observed P/E."""
    if not cohort.get("eligible"):
        return None, None
    return (_implied_from_pe(subject, cohort.get("pe_min")),
            _implied_from_pe(subject, cohort.get("pe_max")))
