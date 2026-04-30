#!/usr/bin/env python3
"""
fetch_finnhub_news.py — Finnhub general news source for News Protocol Stage 1.

Finnhub /news?category=general typically lags real-time by 1-5 min, much
faster than the 1-6h RSS index ceiling. Output is normalized to the same
shape as fetch_news_rss.py so downstream merger can union them.

Usage:
    python3 news/fetch_finnhub_news.py [--hours 24] [--output news/news_logs/]

Requires FINNHUB_API_KEY env var.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Reuse the project's Finnhub client (handles throttle / retry / cache headers).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "finnhub-client", "scripts"))
from finnhub_client import FinnhubClient  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--output", default="news/news_logs/")
    ap.add_argument("--category", default="general", choices=["general", "forex", "crypto", "merger"])
    args = ap.parse_args()

    if not os.getenv("FINNHUB_API_KEY"):
        print("ERROR: FINNHUB_API_KEY not set", file=sys.stderr)
        sys.exit(2)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    print(f"Fetching Finnhub /news?category={args.category}, window={args.hours}h")

    cli = FinnhubClient()
    # /news?category=general — bypass the wrapper (none defined for general news).
    raw = cli._request("/news", params={"category": args.category}) or []

    items_out = []
    for i, n in enumerate(raw, start=1):
        ts = n.get("datetime")  # unix epoch seconds
        if not ts:
            continue
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        if dt < cutoff:
            continue
        items_out.append({
            "news_id": f"fh{i:04d}",
            "headline": (n.get("headline") or "").strip(),
            "url": n.get("url") or "",
            "raw_summary": (n.get("summary") or "")[:500],
            "source": n.get("source") or "Finnhub",
            "source_credibility": "HIGH",  # Finnhub aggregates wire / Reuters / etc.
            "published": dt.isoformat(),
            "category": n.get("category") or args.category,
            "related": n.get("related") or "",  # comma-sep tickers when populated
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": args.hours,
        "provider": "finnhub",
        "category": args.category,
        "raw_count": len(raw),
        "after_time_filter": len(items_out),
        "items": items_out,
    }

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    local_today = datetime.now().strftime("%Y-%m-%d")
    out_path = out_dir / f"{local_today}_finnhub_raw.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  raw fetched      : {len(raw)}")
    print(f"  after time filter: {len(items_out)}")
    print(f"  written → {out_path}")


if __name__ == "__main__":
    main()
