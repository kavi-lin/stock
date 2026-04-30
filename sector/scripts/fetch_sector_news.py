"""
Sector News Fetcher (V1.4 P4 — replaces WebSearch ≤5-query budget)

Pulls structured sector-tagged news via FMP /stable/news/stock (search by mega-cap
symbols per sector) over a configurable lookback window. Designed to give Phase 3
deterministic, citable headline coverage rather than narrative-only WebSearch.

Output: sector/cache/sector_news_<DATE>.json

Per Phase 3 Step 5 rewrite: protocol consumes this file first; WebSearch falls
back to ≤2 queries only for narrative-class context (broader market sentiment,
breaking events not yet indexed by FMP).

Usage:
    python3 sector/scripts/fetch_sector_news.py [--date YYYY-MM-DD] [--lookback-days 2]
                                                [--max-per-sector 10]
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

# Top 5 mega-caps per sector — enough headline density without bloating the call count.
SECTOR_TOP_5 = {
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


def _fmp_get(path: str, params: dict, *, retries: int = 2, timeout: int = 20):
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        sys.exit("[ERROR] FMP_API_KEY not set — sector news cannot be fetched.")
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


def fetch_sector_news(symbols: list, from_d: str, to_d: str, limit: int) -> list:
    rows = _fmp_get(
        "/stable/news/stock",
        {"symbols": ",".join(symbols), "from": from_d, "to": to_d, "limit": limit},
    )
    if not isinstance(rows, list):
        sys.exit(f"[ERROR] FMP news/stock non-list response for {symbols}")
    return rows


def slim(article: dict) -> dict:
    text = article.get("text") or ""
    return {
        "symbol":        article.get("symbol"),
        "publishedDate": article.get("publishedDate"),
        "publisher":     article.get("publisher"),
        "title":         article.get("title"),
        "excerpt":       text[:280] if text else None,
        "url":           article.get("url"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--lookback-days", type=int, default=2)
    ap.add_argument("--max-per-sector", type=int, default=10)
    args = ap.parse_args()

    as_of = args.date
    from_d = (datetime.strptime(as_of, "%Y-%m-%d").date() - timedelta(days=args.lookback_days)).isoformat()

    print(f"[fetch_sector_news] window={from_d}..{as_of}", file=sys.stderr)

    sectors_out: dict = {}
    total = 0
    for sec, syms in SECTOR_TOP_5.items():
        rows = fetch_sector_news(syms, from_d, as_of, limit=args.max_per_sector * 3)
        # Sort newest first, dedupe by URL, cap at max-per-sector
        seen = set()
        deduped = []
        for r in sorted(rows, key=lambda x: x.get("publishedDate") or "", reverse=True):
            url = r.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            deduped.append(slim(r))
            if len(deduped) >= args.max_per_sector:
                break
        sectors_out[sec] = deduped
        total += len(deduped)

    payload = {
        "as_of_date":     as_of,
        "schema_version": "V1.4",
        "lookback_days":  args.lookback_days,
        "max_per_sector": args.max_per_sector,
        "total_articles": total,
        "sectors":        sectors_out,
    }

    out_path = os.path.join(CACHE_DIR, f"sector_news_{as_of}.json")
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"[fetch_sector_news] wrote {out_path} — "
          f"{len(sectors_out)} sectors, {total} articles", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
