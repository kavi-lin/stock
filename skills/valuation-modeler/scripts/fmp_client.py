#!/usr/bin/env python3
"""
valuation-modeler · thin FMP /stable client with 24h per-endpoint cache.

All HTTP goes through scripts/_shared/fmp_pool (cross-process 250/min budget);
this module only adds the skill-local cache layer and the endpoint set the
DCF / comps engines need. Return contract mirrors company_context: parsed
JSON on success, None on any failure (caller degrades gracefully).

Cache: skills/valuation-modeler/cache/<TICKER>_<KIND>.json  TTL = 24h
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


def _fetch(ticker: str, kind: str, path: str, params: dict, *, no_cache: bool = False) -> Any | None:
    """Cache-aware fetch. Failures are cached as None-marker {} to avoid
    hammering FMP on repeated degraded runs within the TTL window."""
    if not no_cache:
        cached = _read_cache(ticker, kind)
        if cached is not None:
            return cached if cached != {} else None
    data = fmp_pool.get(path, {"symbol": ticker.upper(), **params})
    if data:
        _write_cache(ticker, kind, data)
        return data
    _write_cache(ticker, kind, {})
    return None


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
    BASE_DIR / "fred.json",
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
