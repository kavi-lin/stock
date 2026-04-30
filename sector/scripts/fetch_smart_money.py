"""
Sector Smart Money Fetcher (V1.4 P3 hard-required)

Aggregates two smart-money signals per project sector:
  1. insider_acquired_disposed_ratio_q — most-recent-quarter insider acquired/disposed
     ratio across mega-cap universe (FMP /stable/insider-trading/statistics)
  2. senate_net_buy_30d — net (purchases − sales) of US senators in the last 30d
     mapped to project sector via SECTOR_UNIVERSE

Both signals support Phase 4b Devil's Advocate "smart money divergence" check —
HOT consensus + insider_ratio < 0.5 + senate_net_buy < 0 ⇒ flag divergence.

Note: V1.4 P3 ships without form13F signal (FMP plan does not authorize the
industry-summary endpoint — 402). Future P3.5 work to integrate when paid plan
is available; until then, `form13f_top10_delta` is null in output.

Output: sector/cache/sector_smart_money_<DATE>.json

Hard fail (sys.exit(1)) on FMP error per V1.4 protocol.

Usage:
    python3 sector/scripts/fetch_smart_money.py [--date YYYY-MM-DD] [--lookback-days 30]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "sector", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

FMP_BASE = "https://financialmodelingprep.com"

# Reuse the earnings-pulse universe (kept synced manually for V1.4).
# Top mega-caps per sector — captures dominant insider / senate activity.
SECTOR_UNIVERSE = {
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

TICKER_TO_SECTOR: dict = {}
for sec, syms in SECTOR_UNIVERSE.items():
    for s in syms:
        TICKER_TO_SECTOR[s] = sec


def _fmp_get(path: str, params: dict, *, retries: int = 2, timeout: int = 20):
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        sys.exit("[ERROR] FMP_API_KEY not set — smart-money signal cannot be computed.")
    url = f"{FMP_BASE}{path}"
    full = {**params, "apikey": api_key}
    last_exc = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=full, timeout=timeout)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_exc = e
            time.sleep(0.5)
    sys.exit(f"[ERROR] FMP {path} failed after {retries+1} tries: {last_exc}")


def fetch_insider_stats_for_sector(symbols: list) -> dict:
    """Aggregate most-recent-quarter acquired/disposed counts for each symbol."""
    acquired = 0
    disposed = 0
    sample_size = 0
    for sym in symbols:
        rows = _fmp_get("/stable/insider-trading/statistics", {"symbol": sym})
        if not isinstance(rows, list) or not rows:
            continue  # ticker may have no insider history; skip silently
        # Most recent quarter is rows[0] (FMP returns newest-first).
        latest = rows[0]
        try:
            a = int(latest.get("acquiredTransactions") or 0)
            d = int(latest.get("disposedTransactions") or 0)
        except (TypeError, ValueError):
            continue
        acquired += a
        disposed += d
        sample_size += 1
    return {"acquired": acquired, "disposed": disposed, "sample_size": sample_size}


def fetch_senate_window(lookback_days: int) -> list:
    """Pull senate-latest pages until we exceed the lookback window. Returns raw rows."""
    cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()
    out = []
    for page in range(0, 10):  # cap at 10 pages
        rows = _fmp_get("/stable/senate-latest", {"page": page, "limit": 100})
        if not isinstance(rows, list) or not rows:
            break
        out.extend(rows)
        # Stop early if oldest row in this page is already older than cutoff
        oldest = min((r.get("transactionDate") or "") for r in rows)
        if oldest and oldest < cutoff:
            break
    return out


def aggregate_senate_by_sector(rows: list, lookback_days: int) -> dict:
    cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()
    by_sector: dict = {sec: {"purchases": 0, "sales": 0} for sec in SECTOR_UNIVERSE}
    for r in rows:
        sym = r.get("symbol")
        sec = TICKER_TO_SECTOR.get(sym)
        if not sec:
            continue
        td = r.get("transactionDate") or ""
        if td < cutoff:
            continue
        ttype = (r.get("type") or "").lower()
        if "purchase" in ttype:
            by_sector[sec]["purchases"] += 1
        elif "sale" in ttype:
            by_sector[sec]["sales"] += 1
    return by_sector


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--lookback-days", type=int, default=30)
    args = ap.parse_args()

    as_of = args.date
    print(f"[fetch_smart_money] as_of={as_of} lookback={args.lookback_days}d", file=sys.stderr)

    # Pass 1: insider stats per sector
    print("[fetch_smart_money] fetching insider-trading/statistics for "
          f"{sum(len(v) for v in SECTOR_UNIVERSE.values())} mega-cap tickers...",
          file=sys.stderr)
    insider_by_sector = {}
    for sec, syms in SECTOR_UNIVERSE.items():
        insider_by_sector[sec] = fetch_insider_stats_for_sector(syms)

    # Pass 2: senate trades windowed
    print("[fetch_smart_money] fetching senate-latest...", file=sys.stderr)
    senate_rows = fetch_senate_window(args.lookback_days)
    senate_by_sector = aggregate_senate_by_sector(senate_rows, args.lookback_days)

    # Combine
    sectors_out: dict = {}
    for sec in SECTOR_UNIVERSE:
        ins = insider_by_sector.get(sec, {})
        a = ins.get("acquired", 0)
        d = ins.get("disposed", 0)
        ratio = round(a / d, 3) if d > 0 else (None if a == 0 else 99.99)

        sen = senate_by_sector.get(sec, {})
        purchases = sen.get("purchases", 0)
        sales = sen.get("sales", 0)
        net_buy = purchases - sales

        sectors_out[sec] = {
            "insider_acquired_q":              a,
            "insider_disposed_q":              d,
            "insider_acquired_disposed_ratio_q": ratio,  # < 0.5 = bearish, > 1.0 = bullish
            "insider_sample_size":             ins.get("sample_size", 0),
            "senate_purchases_30d":            purchases,
            "senate_sales_30d":                sales,
            "senate_net_buy_30d":              net_buy,
            "form13f_top10_delta":             None,  # V1.4 P3.5 future work — paid plan
        }

    payload = {
        "as_of_date":     as_of,
        "schema_version": "V1.4",
        "lookback_days":  args.lookback_days,
        "universe_size":  sum(len(v) for v in SECTOR_UNIVERSE.values()),
        "senate_rows_in_window": len(senate_rows),
        "sectors":        sectors_out,
    }

    out_path = os.path.join(CACHE_DIR, f"sector_smart_money_{as_of}.json")
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"[fetch_smart_money] wrote {out_path} — {len(sectors_out)} sectors",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
