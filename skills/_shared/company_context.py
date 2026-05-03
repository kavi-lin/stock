"""
skills/_shared/company_context — single-source FMP company-level metadata access.

Consumed by:
  - skills/earnings-analyst/scripts/fetch.py     (profile)
  - sector/scripts/fetch_earnings_pulse.py       (SECTOR_UNIVERSE / TICKER_TO_SECTOR)
  - sector/scripts/fetch_sector_news.py          (SECTOR_UNIVERSE)
  - sector/scripts/fetch_smart_money.py          (SECTOR_UNIVERSE / TICKER_TO_SECTOR)
  - investment_protocol_v4_8 PEER_BUNDLE step    (get_peers + get_profile)

Cache:
  skills/_shared/cache/<TICKER>_<KIND>.json   TTL = 24h

Public API:
  SECTOR_UNIVERSE        constant dict[sector → list[ticker]]
  TICKER_TO_SECTOR       reverse map (auto-built)
  get_profile(ticker)              → dict | None
  get_peers(ticker)                → list[str]   (returns [] on failure)
  get_market_cap_history(ticker, limit=20) → list[dict]
  get_employee_history(ticker)     → list[dict]
  get_profiles_bulk(tickers)       → dict[ticker → dict]   (cache-aware)

Fail behaviour:
  - FMP_API_KEY missing → sys.exit(1)  (matches sector script pattern)
  - 402 paid blocker    → return None / [] (graceful)
  - network / 5xx       → log to stderr, return None / [] (caller decides fallback)
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "skills", "_shared", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

FMP_BASE = "https://financialmodelingprep.com"
CACHE_TTL_HOURS = 24

# ---------------------------------------------------------------------------
# Sector universe — single source of truth shared by sector/* scripts.
# Mega-cap rosters per project sector (SPDR ETF top-10ish + obvious peers).
# Designed to capture sentiment / earnings / smart-money signal without small-cap noise.
# Update here once; sector scripts import from this module.
# ---------------------------------------------------------------------------
SECTOR_UNIVERSE: dict[str, list[str]] = {
    "Technology":             ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "ADBE",
                                "AMD", "INTC", "CSCO", "IBM", "QCOM", "TXN", "NOW", "INTU", "AMAT"],
    "Healthcare":             ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "PFE",
                                "DHR", "BMY", "AMGN", "ELV", "GILD"],
    "Energy":                 ["XOM", "CVX", "COP", "EOG", "SLB", "OXY", "PXD", "PSX",
                                "MPC", "VLO", "KMI", "WMB"],
    "Financials":             ["BRK-B", "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK",
                                "SCHW", "AXP", "SPGI", "PGR", "CB"],
    "Consumer_Discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "TJX", "SBUX",
                                "BKNG", "CMG", "F", "GM"],
    "Consumer_Staples":       ["PG", "COST", "KO", "PEP", "WMT", "PM", "MO", "MDLZ",
                                "CL", "KMB", "GIS", "TGT"],
    "Industrials":            ["GE", "CAT", "RTX", "HON", "UNP", "BA", "LMT", "DE",
                                "UPS", "ETN", "ADP", "MMM"],
    "Materials":              ["LIN", "SHW", "FCX", "APD", "ECL", "NEM", "DOW", "DD",
                                "NUE", "PPG"],
    "Utilities":              ["NEE", "SO", "DUK", "AEP", "SRE", "D", "EXC", "XEL",
                                "PCG", "WEC"],
    "Real_Estate":            ["PLD", "AMT", "EQIX", "WELL", "CCI", "PSA", "SPG", "O",
                                "DLR", "EXR"],
    "Communication":          ["GOOGL", "GOOG", "META", "NFLX", "DIS", "CMCSA", "TMUS",
                                "VZ", "T", "CHTR", "WBD"],
}

TICKER_TO_SECTOR: dict[str, str] = {
    sym: sec for sec, syms in SECTOR_UNIVERSE.items() for sym in syms
}

# Sector news fetcher uses a tighter top-5 (hand-tuned for headline density —
# differs from SECTOR_UNIVERSE[:5] for Communication: prefers TMUS over GOOG to
# avoid GOOGL/GOOG dual-class headline duplication).
SECTOR_TOP_5: dict[str, list[str]] = {
    "Technology":             ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL"],
    "Healthcare":             ["LLY", "UNH", "JNJ", "ABBV", "MRK"],
    "Energy":                 ["XOM", "CVX", "COP", "EOG", "SLB"],
    "Financials":             ["BRK-B", "JPM", "BAC", "WFC", "GS"],
    "Consumer_Discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE"],
    "Consumer_Staples":       ["PG", "COST", "KO", "PEP", "WMT"],
    "Industrials":            ["GE", "CAT", "RTX", "HON", "UNP"],
    "Materials":              ["LIN", "SHW", "FCX", "APD", "ECL"],
    "Utilities":              ["NEE", "SO", "DUK", "AEP", "SRE"],
    "Real_Estate":            ["PLD", "AMT", "EQIX", "WELL", "CCI"],
    "Communication":          ["GOOGL", "META", "NFLX", "DIS", "TMUS"],
}


# ---------------------------------------------------------------------------
# FMP HTTP wrapper (kept local to avoid import coupling with sector scripts).
# ---------------------------------------------------------------------------
def _fmp_get(path: str, params: dict, *, retries: int = 2, timeout: int = 20) -> Any:
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        sys.exit("[ERROR] FMP_API_KEY not set — skills/_shared/company_context cannot run.")
    url = f"{FMP_BASE}{path}"
    full = {**params, "apikey": api_key}
    last_exc = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=full, timeout=timeout)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 402:
                return None
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_exc = e
            time.sleep(0.5)
    print(f"[company_context] WARN: FMP {path} failed after {retries+1} tries: {last_exc}",
          file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------
def _cache_path(ticker: str, kind: str) -> str:
    return os.path.join(CACHE_DIR, f"{ticker.upper()}_{kind}.json")


def _read_cache(ticker: str, kind: str) -> Any | None:
    p = _cache_path(ticker, kind)
    if not os.path.exists(p):
        return None
    age_h = (time.time() - os.path.getmtime(p)) / 3600
    if age_h > CACHE_TTL_HOURS:
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_cache(ticker: str, kind: str, payload: Any) -> None:
    if payload is None:
        return
    p = _cache_path(ticker, kind)
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except Exception as e:
        print(f"[company_context] WARN: cache write {p} failed: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_profile(ticker: str) -> dict | None:
    """Return single profile dict or None. 24h cache."""
    cached = _read_cache(ticker, "profile")
    if cached is not None:
        return cached if cached else None
    raw = _fmp_get("/stable/profile", {"symbol": ticker})
    if not raw:
        return None
    profile = raw[0] if isinstance(raw, list) and raw else (raw if isinstance(raw, dict) else None)
    if profile:
        _write_cache(ticker, "profile", profile)
    return profile


def get_peers(ticker: str) -> list[str]:
    """Return list of same-industry peer tickers. Returns [] on failure / sparse."""
    cached = _read_cache(ticker, "peers")
    if cached is not None:
        return cached
    raw = _fmp_get("/stable/stock-peers", {"symbol": ticker})
    if not raw:
        _write_cache(ticker, "peers", [])
        return []
    peers: list[str] = []
    if isinstance(raw, list):
        for row in raw:
            if isinstance(row, dict):
                sym = row.get("symbol") or row.get("peer")
                if sym and sym != ticker:
                    peers.append(sym)
            elif isinstance(row, str) and row != ticker:
                peers.append(row)
    _write_cache(ticker, "peers", peers)
    return peers


def get_market_cap_history(ticker: str, limit: int = 20) -> list[dict]:
    cached = _read_cache(ticker, "marketcap_hist")
    if cached is not None:
        return cached
    raw = _fmp_get("/stable/historical-market-capitalization",
                   {"symbol": ticker, "limit": limit})
    if not isinstance(raw, list):
        raw = []
    _write_cache(ticker, "marketcap_hist", raw)
    return raw


def get_employee_history(ticker: str) -> list[dict]:
    cached = _read_cache(ticker, "employee_hist")
    if cached is not None:
        return cached
    raw = _fmp_get("/stable/historical-employee-count", {"symbol": ticker})
    if not isinstance(raw, list):
        raw = []
    _write_cache(ticker, "employee_hist", raw)
    return raw


def get_profiles_bulk(tickers: list[str]) -> dict[str, dict]:
    """Returns {ticker: profile_dict}. Reads cache first; only un-cached tickers hit FMP."""
    out: dict[str, dict] = {}
    for t in tickers:
        prof = get_profile(t)
        if prof:
            out[t] = prof
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="company_context smoke test")
    ap.add_argument("ticker", help="ticker e.g. AAPL")
    ap.add_argument("--peers", action="store_true")
    ap.add_argument("--marketcap-history", action="store_true")
    ap.add_argument("--employees", action="store_true")
    args = ap.parse_args()

    profile = get_profile(args.ticker)
    print(f"profile.sector = {profile.get('sector') if profile else None}")
    print(f"profile.marketCap = {profile.get('marketCap') if profile else None}")
    if args.peers:
        print(f"peers = {get_peers(args.ticker)}")
    if args.marketcap_history:
        hist = get_market_cap_history(args.ticker, limit=5)
        print(f"market_cap_history (5 latest) = {hist[:5]}")
    if args.employees:
        emp = get_employee_history(args.ticker)
        print(f"employee_history = {emp[:3]}")
