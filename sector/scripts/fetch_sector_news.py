"""Sector news fetcher (V1.4 P4 hard-required).

Output: sector/cache/sector_news_<DATE>.json. Hard-fails on FMP error.
詳見 sector/scripts/README.md。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from sector.lib.date_utils import lookback_window  # noqa: E402
from sector.lib.fmp_client import SECTOR_TOP_5, cache_path, fmp_get  # noqa: E402


def fetch_sector_news(symbols: list, from_d: str, to_d: str, limit: int) -> list:
    rows = fmp_get(
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
    from_d, _ = lookback_window(as_of, args.lookback_days)

    print(f"[fetch_sector_news] window={from_d}..{as_of}", file=sys.stderr)

    sectors_out: dict = {}
    total = 0
    for sec, syms in SECTOR_TOP_5.items():
        rows = fetch_sector_news(syms, from_d, as_of, limit=args.max_per_sector * 3)
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

    out_path = cache_path("sector_news", as_of)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"[fetch_sector_news] wrote {out_path} — "
          f"{len(sectors_out)} sectors, {total} articles", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
