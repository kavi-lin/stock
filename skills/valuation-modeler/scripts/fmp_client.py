#!/usr/bin/env python3
"""
valuation-modeler · thin FMP /stable client with 24h per-endpoint cache.

All HTTP goes through scripts/_shared/fmp_pool (cross-process 250/min budget);
this module only adds the skill-local cache layer and the endpoint set the
DCF / comps engines need. Return contract mirrors company_context: parsed
JSON on success, None on any failure (caller degrades gracefully).

Source cache: skills/earnings-analyst/cache/sources/{financial,market,quote}/
Financial 7d, market 24h, quote 5m; payload compatibility files remain skill-local.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
CACHE_DIR = SKILL_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
BASE_DIR = SKILL_DIR.parent.parent  # project root

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
from scripts._shared import fmp_pool  # noqa: E402

CACHE_TTL_SEC = 24 * 3600


def _cache_path(ticker: str, kind: str) -> Path:
    return CACHE_DIR / f"{ticker.upper()}_{kind}.json"


def _read_cache(ticker: str, kind: str, max_age: float = CACHE_TTL_SEC) -> Any | None:
    p = _cache_path(ticker, kind)
    if not p.exists():
        return None
    if time.time() - p.stat().st_mtime > max_age:
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _write_cache(ticker: str, kind: str, data: Any) -> None:
    try:
        _cache_path(ticker, kind).write_text(json.dumps(data, ensure_ascii=False, indent=1))
    except Exception as e:
        print(f"WARN: cache write failed {ticker}_{kind}: {e}", file=sys.stderr)


_SOURCE_CLIENTS = {}


def source_client(ticker):
    from skills._shared.investment_data import SourceCache, active_cache
    ticker = ticker.upper()
    if active_cache() is not None:
        _SOURCE_CLIENTS[ticker] = active_cache()
        return _SOURCE_CLIENTS[ticker]
    if ticker not in _SOURCE_CLIENTS:
        cache = SourceCache(BASE_DIR / "skills/earnings-analyst/cache/sources")
        income = cache.get("/stable/income-statement", {"symbol": ticker, "period": "quarter", "limit": 8}, refresh=True)
        cache.period = income[0].get("date") if income else None
        _SOURCE_CLIENTS[ticker] = cache
    return _SOURCE_CLIENTS[ticker]


def source_provenance(ticker):
    cache = _SOURCE_CLIENTS.get(ticker.upper())
    if cache is None:
        return {"source_fetched_at": None, "financial_period": None, "source_records": {}}
    # A calculation can be new while its source data is old. Keep the oldest
    # market retrieval clock, and retain every underlying source separately.
    times = [r["fetched_at"] for r in cache.sources.values() if r.get("status") == "ok" and r["kind"] != "financial"]
    return {"source_fetched_at": min(times) if times else None,
            "financial_period": cache.period, "source_records": dict(cache.sources)}


def _fetch(ticker: str, kind: str, path: str, params: dict, *, no_cache: bool = False) -> Any | None:
    cache = source_client(ticker)
    return cache.get("/stable/" + path, {"symbol": ticker.upper(), **params}, refresh=no_cache)


# ── endpoint set ──────────────────────────────────────────────────────────
def income_annual(ticker: str, *, no_cache: bool = False) -> list | None:
    return _fetch(ticker, "income_annual", "income-statement",
                  {"period": "annual", "limit": 5}, no_cache=no_cache)


def cashflow_annual(ticker: str, *, no_cache: bool = False) -> list | None:
    return _fetch(ticker, "cashflow_annual", "cash-flow-statement",
                  {"period": "annual", "limit": 5}, no_cache=no_cache)


def balance_annual(ticker: str, *, no_cache: bool = False) -> list | None:
    return _fetch(ticker, "balance_annual", "balance-sheet-statement",
                  {"period": "annual", "limit": 2}, no_cache=no_cache)


def analyst_estimates(ticker: str, *, no_cache: bool = False) -> list | None:
    return _fetch(ticker, "analyst_estimates", "analyst-estimates",
                  {"period": "annual", "limit": 4}, no_cache=no_cache)


def quote(ticker: str, *, no_cache: bool = False) -> dict | None:
    data = _fetch(ticker, "quote", "quote", {}, no_cache=no_cache)
    return data[0] if isinstance(data, list) and data else None


# ── FRED risk-free (read-only, no HTTP — reuses fred-macro's cache) ──────
FRED_CACHE_CANDIDATES = [
    BASE_DIR / "skills" / "fred-macro" / "cache" / "fred_latest.json",
]
RF_DEFAULT = 0.042


def risk_free_rate() -> tuple[float, str]:
    """10Y treasury from fred-macro cache. Returns (rate_decimal, provenance)."""
    for p in FRED_CACHE_CANDIDATES:
        try:
            d = json.loads(p.read_text())
            v = (d.get("series") or {}).get("DGS10", {}).get("value")
            if v is None:
                v = d.get("DGS10", {}).get("value") if isinstance(d.get("DGS10"), dict) else d.get("DGS10")
            if isinstance(v, (int, float)) and 0 < v < 20:
                return round(v / 100.0, 5), f"fred:{p.name}"
        except Exception:
            continue
    return RF_DEFAULT, "default"
