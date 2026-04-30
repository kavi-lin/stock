#!/usr/bin/env python3
"""
fetch_fmp_news.py — FMP general/stock news for News Protocol Stage 1.

Complementary to fetch_finnhub_news.py:
- Finnhub /news = wire / Reuters / Yahoo aggregator angle
- FMP /general_news + /stock_news = SeekingAlpha / Benzinga / Press release angle
Roughly 50% overlap, 50% incremental coverage. Dedupe happens in fetch_all_news.

Usage:
    python3 news/fetch_fmp_news.py [--hours 24] [--output news/news_logs/]

Requires FMP_API_KEY env var.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

FMP_BASE = "https://financialmodelingprep.com/stable"
TIMEOUT = 15


def _parse_dt(s: str):
    """FMP returns 'YYYY-MM-DD HH:MM:SS' (UTC implicit)."""
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _fetch(endpoint: str, key: str, **params):
    params["apikey"] = key
    url = f"{FMP_BASE}/{endpoint}"
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"  [WARN] {endpoint}: {e}", file=sys.stderr)
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--output", default="news/news_logs/")
    ap.add_argument("--limit-per-endpoint", type=int, default=100)
    args = ap.parse_args()

    key = os.getenv("FMP_API_KEY")
    if not key:
        print("ERROR: FMP_API_KEY not set", file=sys.stderr)
        sys.exit(2)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    print(f"Fetching FMP general_news + stock_news, window={args.hours}h")

    # Two endpoints in parallel mindshare — general wire + ticker-tagged stories.
    raw = []
    raw += _fetch("news/general-latest", key, page=0, limit=args.limit_per_endpoint)
    raw += _fetch("news/stock-latest",   key, page=0, limit=args.limit_per_endpoint)
    print(f"  raw rows from FMP: {len(raw)}")

    items_out = []
    for i, n in enumerate(raw, start=1):
        # FMP fields vary across endpoints — coalesce to common shape.
        title    = (n.get("title") or n.get("headline") or "").strip()
        if not title:
            continue
        date_str = n.get("publishedDate") or n.get("date") or ""
        dt = _parse_dt(date_str)
        if dt is None or dt < cutoff:
            continue
        items_out.append({
            "news_id": f"fmp{i:04d}",
            "headline": title,
            "url": n.get("url") or n.get("link") or "",
            "raw_summary": ((n.get("text") or n.get("content") or n.get("snippet") or "")[:500]),
            "source": n.get("publisher") or n.get("site") or n.get("source") or "FMP",
            "source_credibility": "HIGH",
            "published": dt.isoformat(),
            "symbol": n.get("symbol") or "",  # ticker tag if endpoint provides it
            "image": n.get("image") or "",
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": args.hours,
        "provider": "fmp",
        "raw_count": len(raw),
        "after_time_filter": len(items_out),
        "items": items_out,
    }

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    local_today = datetime.now().strftime("%Y-%m-%d")
    out_path = out_dir / f"{local_today}_fmp_raw.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  after time filter: {len(items_out)}")
    print(f"  written → {out_path}")


if __name__ == "__main__":
    main()
