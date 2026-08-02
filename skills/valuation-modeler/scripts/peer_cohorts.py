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

# ── V4.89.0 — discovered peer cache (L4b gate 用) ────────────────────────────
# config/peer_cohorts.json 是**人工核准區**（entry 帶 approved_by/approved_at），
# 任何 agent 不得寫入。reviewer 發現的 peers 一律進這個獨立 cache，兩者永不混檔。
# 消費端只有 valuation_reviewer_gate（判斷「有沒有可用 peers」）——**不**餵
# build_pe_cohort，否則 LLM 發現的 peer 會流進 valuation_explained_range 這條 live 數字路徑。
DISCOVERY_CACHE_PATH = SCRIPT_DIR.parent / "cache" / "peer_discovery.json"
DISCOVERY_SCHEMA = "valuation_peer_discovery.v1"
DISCOVERY_TTL_DAYS = 30          # 區間下限取保守值；覆蓋率收斂後再議放寬


def _pos(value):
    return (float(value) if isinstance(value, (int, float))
            and not isinstance(value, bool) and value > 0 else None)


def load_cohort(ticker: str, path: Path = CONFIG_PATH) -> tuple[dict | None, str | None]:
    """Returns (cohort, reason). A schema this module cannot read is reported,
    not treated as "no cohort configured"."""
    try:
        payload = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return None, "peer_cohort_config_unreadable"
    schema = str(payload.get("schema") or "")
    if schema != SUPPORTED_SCHEMA:
        return None, f"unsupported_cohort_schema:{schema or 'missing'}"
    cohort = (payload.get("cohorts") or {}).get(ticker.upper())
    if not isinstance(cohort, dict):
        return None, "no_curated_peer_cohort"
    return dict(cohort), None


def _parse_date(value) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def load_discovered_cohort(ticker: str, *, path: Path = DISCOVERY_CACHE_PATH,
                           today: dt.date | None = None,
                           ttl_days: int = DISCOVERY_TTL_DAYS) -> tuple[dict | None, str | None]:
    """Returns (entry, reason) for a non-expired discovered cohort.

    Missing cache is a normal cold-start ("no_discovered_peer_cohort"); an
    unreadable or wrong-schema cache is reported so it cannot masquerade as
    "nothing discovered yet".
    """
    today = today or dt.date.today()
    if not Path(path).exists():
        return None, "no_discovered_peer_cohort"
    try:
        payload = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return None, "peer_discovery_cache_unreadable"
    if str(payload.get("schema") or "") != DISCOVERY_SCHEMA:
        return None, f"unsupported_discovery_schema:{payload.get('schema') or 'missing'}"
    entry = (payload.get("cohorts") or {}).get(ticker.upper())
    if not isinstance(entry, dict):
        return None, "no_discovered_peer_cohort"
    discovered_on = _parse_date(entry.get("discovered_at"))
    if discovered_on is None:
        return None, "discovered_cohort_missing_discovered_at"
    age = (today - discovered_on).days
    if age > ttl_days:
        return None, f"discovered_cohort_expired:{age}d>{ttl_days}d"
    entry = dict(entry)
    entry["age_days"] = age
    entry["expires_on"] = (discovered_on + dt.timedelta(days=ttl_days)).isoformat()
    return entry, None


def record_discovered_cohort(ticker: str, candidates: list, *, rationale: str | None = None,
                             limitations: list | None = None, source: str = "valuation_specialist",
                             path: Path = DISCOVERY_CACHE_PATH,
                             config_path: Path = CONFIG_PATH,
                             today: dt.date | None = None) -> dict:
    """Persist reviewer-discovered peers. Refuses to shadow a curated cohort.

    A human-approved cohort always wins: silently caching a discovered set for
    the same ticker would let it drift away from the approved one with no
    signal that the two disagree.
    """
    symbol = str(ticker).upper()
    curated, _ = load_cohort(symbol, path=config_path)
    if curated:
        return {"written": False, "reason": "curated_cohort_exists", "ticker": symbol}
    clean = []
    for candidate in candidates or []:
        cand_ticker = str((candidate or {}).get("ticker") or "").upper()
        if cand_ticker:
            clean.append({"ticker": cand_ticker, "role": (candidate or {}).get("role")})
    if not clean:
        return {"written": False, "reason": "no_usable_candidates", "ticker": symbol}

    payload = {"schema": DISCOVERY_SCHEMA, "cohorts": {}}
    if Path(path).exists():
        try:
            existing = json.loads(Path(path).read_text())
            if str(existing.get("schema") or "") == DISCOVERY_SCHEMA:
                payload = existing
                payload.setdefault("cohorts", {})
        except (OSError, json.JSONDecodeError):
            pass          # 壞檔就重建，不讓一次寫壞永久卡住 discovery
    entry = {
        "discovered_at": (today or dt.date.today()).isoformat(),
        "source": source,
        "provenance": "discovered",
        "comparison_scope": "range_only",
        "candidates": clean,
        "rationale": rationale,
        "limitations": limitations or [],
    }
    payload["cohorts"][symbol] = entry
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return {"written": True, "reason": None, "ticker": symbol, "entry": entry,
            "path": str(path)}


def resolve_cohort_availability(ticker: str, *, config_path: Path = CONFIG_PATH,
                                discovery_path: Path = DISCOVERY_CACHE_PATH,
                                today: dt.date | None = None,
                                ttl_days: int = DISCOVERY_TTL_DAYS) -> dict:
    """curated > discovered > none — the gate's `no_curated_peers` input."""
    curated, curated_reason = load_cohort(ticker, path=config_path)
    if curated:
        return {"available": True, "provenance": "curated",
                "peer_count": len(curated.get("candidates") or []),
                "cohort_name": curated.get("name"), "reason": None, "expires_on": None}
    discovered, disc_reason = load_discovered_cohort(
        ticker, path=discovery_path, today=today, ttl_days=ttl_days)
    if discovered:
        return {"available": True, "provenance": "discovered",
                "peer_count": len(discovered.get("candidates") or []),
                "cohort_name": None, "reason": None,
                "expires_on": discovered.get("expires_on"),
                "age_days": discovered.get("age_days")}
    return {"available": False, "provenance": None, "peer_count": 0, "cohort_name": None,
            "reason": curated_reason or disc_reason or "no_peer_cohort",
            "discovery_reason": disc_reason, "expires_on": None}


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
