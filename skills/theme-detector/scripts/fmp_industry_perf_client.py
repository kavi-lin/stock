#!/usr/bin/env python3
"""
Theme Detector - FMP Industry Performance Cross-Check Client.

Supplements the finviz scraper with structured FMP /stable/industry-performance-snapshot
data. Used for sanity-checking finviz HTML scrape against FMP REST output.

Strategy:
- Fetches today's snapshot (and last N business days for rolling sum approximations).
- Returns dict keyed by industry_name -> {perf_1d, perf_5d_sum, exchange}.

NOT a replacement for finviz_performance_client.py. The scorer may surface
both side-by-side or use this only when finviz HTML breakage is detected.
"""
from __future__ import annotations
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache" / "fmp_industry"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL = 3600 * 6  # 6h


def _fmp_get(path: str, params: dict, *, timeout: int = 12):
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return None
    try:
        r = requests.get(
            f"https://financialmodelingprep.com/stable/{path}",
            params={**params, "apikey": api_key},
            timeout=timeout,
        )
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def _last_n_business_days(n: int) -> list[str]:
    """Return last n business day ISO dates ending today (newest first)."""
    out: list[str] = []
    d = date.today()
    while len(out) < n:
        if d.weekday() < 5:  # Mon-Fri
            out.append(d.isoformat())
        d -= timedelta(days=1)
    return out


def get_industry_snapshot(target_date: Optional[str] = None) -> list[dict]:
    """One-day snapshot of FMP industry-performance-snapshot.

    Returns list of {industry, exchange, averageChange, date} dicts.
    Caches per date.
    """
    if target_date is None:
        target_date = date.today().isoformat()
    cache_path = CACHE_DIR / f"snapshot_{target_date}.json"
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < CACHE_TTL:
            with open(cache_path) as f:
                return json.load(f)
    data = _fmp_get("industry-performance-snapshot", {"date": target_date})
    if not isinstance(data, list):
        return []
    with open(cache_path, "w") as f:
        json.dump(data, f, indent=2)
    return data


def get_industry_perf_crosscheck(days_back: int = 5) -> dict:
    """
    Aggregate last `days_back` business-day snapshots into per-industry rolling
    perf approximation. Returns:
      {
        "as_of_date": <today>,
        "lookback_days": <days_back>,
        "industries": {
          "<industry name>": {
            "perf_1d_pct": <float>,         # most recent day
            "perf_rolling_pct": <float>,    # arithmetic sum of N days
            "exchange": "<NASDAQ|NYSE|...>",
            "samples": <int>,
          },
          ...
        },
        "source": "FMP /stable/industry-performance-snapshot"
      }
    """
    days = _last_n_business_days(days_back)
    if not days:
        return {}
    snapshots: list[list[dict]] = []
    for d in days:
        snap = get_industry_snapshot(d)
        if snap:
            snapshots.append(snap)
    if not snapshots:
        return {}
    # Build aggregate. Note FMP returns one row per (industry, exchange) pair —
    # collapse to industry-level by averaging across exchanges.
    out: dict = {}
    for idx, snap in enumerate(snapshots):
        for row in snap:
            industry = row.get("industry")
            if not industry:
                continue
            chg = row.get("averageChange")
            if chg is None:
                continue
            slot = out.setdefault(industry, {
                "perf_1d_pct": None,
                "perf_rolling_pct": 0.0,
                "exchange": row.get("exchange"),
                "samples": 0,
                "_per_day_avg": [],
            })
            # Track per-day per-industry mean across exchanges
            per_day_buckets = slot.setdefault("_buckets", {})
            bucket = per_day_buckets.setdefault(idx, [])
            bucket.append(chg)
    # Reduce buckets -> per-day mean -> rolling sum
    for industry, slot in out.items():
        per_day_buckets = slot.pop("_buckets", {})
        per_day_means = [
            sum(vals) / len(vals) for _, vals in sorted(per_day_buckets.items())
        ]
        slot["_per_day_avg"] = [round(v, 4) for v in per_day_means]
        slot["samples"] = len(per_day_means)
        slot["perf_rolling_pct"] = round(sum(per_day_means), 4)
        slot["perf_1d_pct"] = round(per_day_means[0], 4) if per_day_means else None
    return {
        "as_of_date": date.today().isoformat(),
        "lookback_days": days_back,
        "industries": out,
        "source": "FMP /stable/industry-performance-snapshot",
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--days-back", type=int, default=5)
    ap.add_argument("--head", type=int, default=10)
    args = ap.parse_args()
    out = get_industry_perf_crosscheck(args.days_back)
    industries = out.get("industries", {})
    # Sort by rolling perf desc
    rows = sorted(
        ((name, data) for name, data in industries.items()),
        key=lambda kv: kv[1].get("perf_rolling_pct") or 0,
        reverse=True,
    )
    print(json.dumps({
        "as_of_date": out.get("as_of_date"),
        "lookback_days": out.get("lookback_days"),
        "top_n": args.head,
        "top": [{"industry": n, **d} for n, d in rows[:args.head]],
        "bottom": [{"industry": n, **d} for n, d in rows[-args.head:]],
        "industries_count": len(industries),
    }, indent=2, ensure_ascii=False))
