#!/usr/bin/env python3
"""
fetch_sec_edgar.py — SEC EDGAR 8-K Atom feed for News Protocol Stage 1.

8-K = "current report" — public companies must file within 4 business days
of any material event (M&A, CEO change, earnings guidance, restatement,
bankruptcy, etc.). Latency from event to filing is typically 0-15 min,
making this the fastest single source of US company news.

EDGAR's "browse" endpoint provides an Atom feed:
    https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&output=atom

Usage:
    python3 news/fetch_sec_edgar.py [--hours 24] [--output news/news_logs/]

No API key. SEC requires a User-Agent header identifying contact email
(per https://www.sec.gov/os/accessing-edgar-data) — set EDGAR_UA env var
or fall back to the project default.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from lxml import etree

EDGAR_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
DEFAULT_UA = "AI Investment Committee research@example.com"
TIMEOUT = 20
ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}


def _parse_dt(s: str):
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def _extract_ticker_from_title(title: str):
    """8-K titles look like '8-K - APPLE INC (0000320193) (Filer)'.
    EDGAR doesn't include ticker; return company name (caller may resolve later)."""
    m = re.match(r"^[\d\-A-Z/]+\s+-\s+(.+?)\s+\(\d+\)", title)
    return m.group(1).strip() if m else title.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--output", default="news/news_logs/")
    ap.add_argument("--form", default="8-K")
    ap.add_argument("--count", type=int, default=100, help="Max filings to pull (EDGAR cap ~100/page)")
    args = ap.parse_args()

    ua = os.getenv("EDGAR_UA") or DEFAULT_UA
    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    print(f"Fetching EDGAR {args.form} feed, window={args.hours}h")

    params = {
        "action":  "getcurrent",
        "type":    args.form,
        "company": "",
        "dateb":   "",
        "owner":   "include",
        "count":   args.count,
        "output":  "atom",
    }
    headers = {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}

    try:
        r = requests.get(EDGAR_URL, params=params, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        print(f"ERROR: EDGAR fetch failed: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        root = etree.fromstring(r.content, parser=etree.XMLParser(recover=True))
    except Exception as e:
        print(f"ERROR: parse failed: {e}", file=sys.stderr)
        sys.exit(1)
    if root is None:
        print("ERROR: empty Atom feed", file=sys.stderr)
        sys.exit(1)

    entries = root.findall(".//a:entry", ATOM_NS)
    items_out = []
    for i, e in enumerate(entries, start=1):
        title_el   = e.find("a:title",   ATOM_NS)
        updated_el = e.find("a:updated", ATOM_NS)
        link_el    = e.find("a:link",    ATOM_NS)
        summary_el = e.find("a:summary", ATOM_NS)
        if title_el is None or title_el.text is None:
            continue

        title    = title_el.text.strip()
        company  = _extract_ticker_from_title(title)
        updated  = (updated_el.text or "") if updated_el is not None else ""
        dt       = _parse_dt(updated)
        if dt is None or dt < cutoff:
            continue
        link     = link_el.get("href", "") if link_el is not None else ""
        summary  = (summary_el.text or "").strip() if summary_el is not None else ""

        items_out.append({
            "news_id": f"sec{i:04d}",
            # Headline format makes downstream LLM triage trivially understand
            # this is a regulatory filing, not a press article.
            "headline": f"[8-K] {company}: {title}",
            "url": link,
            "raw_summary": summary[:500],
            "source": "SEC EDGAR",
            "source_credibility": "HIGH",
            "published": dt.isoformat(),
            "form": args.form,
            "company": company,
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": args.hours,
        "provider": "sec_edgar",
        "form": args.form,
        "raw_count": len(entries),
        "after_time_filter": len(items_out),
        "items": items_out,
    }

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    local_today = datetime.now().strftime("%Y-%m-%d")
    out_path = out_dir / f"{local_today}_edgar_raw.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  raw entries      : {len(entries)}")
    print(f"  after time filter: {len(items_out)}")
    print(f"  written → {out_path}")


if __name__ == "__main__":
    main()
