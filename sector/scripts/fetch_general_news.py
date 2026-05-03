"""General market narrative news (V1.71+ Phase 3 Step 3e).

Output: sector/cache/general_news_<DATE>.json. Soft-fail（FMP 失敗 → {available: false}），
Phase 3 Step 5 WebSearch budget 視 available 動態調整。詳見 sector/scripts/README.md。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from sector.lib.fmp_client import cache_path, fmp_get  # noqa: E402


def slim(article: dict) -> dict:
    text = article.get("text") or ""
    return {
        "publishedDate": article.get("publishedDate"),
        "publisher":     article.get("publisher"),
        "title":         article.get("title"),
        "excerpt":       text[:280] if text else None,
        "url":           article.get("url"),
        "site":          article.get("site"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    as_of = args.date
    print(f"[fetch_general_news] as_of={as_of} limit={args.limit}", file=sys.stderr)

    rows = fmp_get(
        "/stable/news/general-latest",
        {"limit": args.limit},
        hard_fail=False,
        timeout=15,
    )

    out_path = cache_path("general_news", as_of)
    if not isinstance(rows, list):
        payload = {
            "as_of_date":     as_of,
            "schema_version": "V1.71",
            "available":      False,
            "reason":         "FMP /stable/news/general-latest unavailable; falling back to WebSearch ≤2",
            "articles":       [],
        }
    else:
        # Sort newest first, dedupe by URL.
        seen: set = set()
        deduped = []
        for r in sorted(rows, key=lambda x: x.get("publishedDate") or "", reverse=True):
            url = r.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            deduped.append(slim(r))
        payload = {
            "as_of_date":     as_of,
            "schema_version": "V1.71",
            "available":      True,
            "limit":          args.limit,
            "total_articles": len(deduped),
            "articles":       deduped,
        }

    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    n = payload.get("total_articles", 0)
    avail = payload["available"]
    print(f"[fetch_general_news] wrote {out_path} — available={avail}, {n} articles", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
