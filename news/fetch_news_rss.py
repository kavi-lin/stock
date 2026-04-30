#!/usr/bin/env python3
"""
fetch_news_rss.py — News Protocol V2 Stage 1 data source.

Fetches financial news from public RSS feeds, dedupes by headline similarity,
filters by time window, and writes a single raw.json consumed by the
news_protocol_v2 Stage 1 triage.

Usage:
    python3 news/fetch_news_rss.py [--hours 24] [--output news/news_logs/]

No API key required. Uses requests + lxml (already in project env).
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
from lxml import etree

# ---- Feeds (public, no key) --------------------------------------------------
FEEDS = [
    ("Yahoo Finance",  "https://finance.yahoo.com/news/rssindex",          "HIGH"),
    ("MarketWatch",    "https://feeds.content.dowjones.io/public/rss/mw_topstories", "HIGH"),
    ("MarketWatch Mkt","https://feeds.content.dowjones.io/public/rss/mw_marketpulse", "HIGH"),
    ("CNBC Top",       "https://www.cnbc.com/id/100003114/device/rss/rss.html",   "HIGH"),
    ("CNBC Markets",   "https://www.cnbc.com/id/15839135/device/rss/rss.html",    "HIGH"),
    ("CNBC Economy",   "https://www.cnbc.com/id/20910258/device/rss/rss.html",    "HIGH"),
    ("Seeking Alpha",  "https://seekingalpha.com/market_currents.xml",             "MEDIUM"),
    ("Investing.com",  "https://www.investing.com/rss/news_25.rss",                "MEDIUM"),
    # PR Newswire financial press releases — typical latency 5-15 min from
    # company release, much fresher than wire RSS index polls.
    ("PR Newswire",    "https://www.prnewswire.com/rss/financial-services-latest-news/financial-services-latest-news-list.rss", "MEDIUM"),
]

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
TIMEOUT = 15
STOPWORDS = {"the","a","an","to","of","for","in","on","at","by","and","or","is","are","as","with","from","it","its","be","this","that","new"}

# Titles matching any of these regexes are dropped as low-signal stubs.
# (Yahoo Finance RSS commonly emits template titles like "Analyst Report: X"
#  and "Market Update: A, B, C" with no usable summary.)
LOW_SIGNAL_PATTERNS = [
    re.compile(r"^analyst report:\s*", re.I),
    re.compile(r"^market update:\s*", re.I),
    re.compile(r"^(stock|sector) movers?:\s*", re.I),
    re.compile(r"^earnings preview:\s*", re.I),
]


def is_low_signal(title: str) -> bool:
    return any(p.search(title) for p in LOW_SIGNAL_PATTERNS)


def clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", "", s)  # strip html
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_date(s: str):
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def headline_fingerprint(title: str) -> str:
    """Normalized fingerprint for dedupe: lowercase, alnum only, drop stopwords, take first 8 tokens."""
    tokens = re.findall(r"[a-z0-9]+", title.lower())
    tokens = [t for t in tokens if t not in STOPWORDS][:8]
    return " ".join(tokens)


def fetch_feed(name: str, url: str, credibility: str):
    """Fetch one feed, return list of normalized items (dicts)."""
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        print(f"  [WARN] {name}: {e}", file=sys.stderr)
        return []

    try:
        # recover=True tolerates minor malformations common in real-world RSS
        root = etree.fromstring(r.content, parser=etree.XMLParser(recover=True))
    except Exception as e:
        print(f"  [WARN] {name}: parse failed: {e}", file=sys.stderr)
        return []

    if root is None:
        return []

    # Support RSS 2.0 (<item>) and Atom (<entry>)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = root.findall(".//item") or root.findall(".//atom:entry", ns)

    out = []
    for it in items:
        def g(tag):
            el = it.find(tag)
            if el is None:
                el = it.find(f"atom:{tag}", ns)
            return clean_text(el.text) if el is not None and el.text else ""

        title = g("title")
        if not title or is_low_signal(title):
            continue
        link_el = it.find("link")
        if link_el is not None and link_el.text:
            link = link_el.text.strip()
        else:
            link_el = it.find("atom:link", ns)
            link = link_el.get("href") if link_el is not None else ""

        desc = g("description") or g("summary")
        pub = g("pubDate") or g("published") or g("updated")
        pub_dt = parse_date(pub)

        out.append({
            "headline": title,
            "url": link,
            "raw_summary": desc[:500],
            "source": name,
            "source_credibility": credibility,
            "published": pub_dt.isoformat() if pub_dt else None,
            "_fp": headline_fingerprint(title),
            "_dt": pub_dt,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24, help="Time window in hours (default 24)")
    ap.add_argument("--output", default="news/news_logs/", help="Output directory")
    ap.add_argument("--max-per-feed", type=int, default=25)
    args = ap.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    print(f"Fetching {len(FEEDS)} feeds, window={args.hours}h, cutoff={cutoff.isoformat()}")

    all_items = []
    feed_stats = []
    for name, url, cred in FEEDS:
        print(f"  → {name}")
        items = fetch_feed(name, url, cred)
        kept = items[: args.max_per_feed]
        feed_stats.append({"feed": name, "fetched": len(items), "kept": len(kept)})
        all_items.extend(kept)

    # Time filter (keep items without timestamps — better than dropping)
    filtered = [x for x in all_items if (x["_dt"] is None or x["_dt"] >= cutoff)]

    # Dedupe by headline fingerprint (keep first seen, prefer HIGH credibility)
    seen = {}
    for x in filtered:
        fp = x["_fp"]
        if not fp:
            continue
        prev = seen.get(fp)
        if prev is None:
            seen[fp] = x
        elif x["source_credibility"] == "HIGH" and prev["source_credibility"] != "HIGH":
            seen[fp] = x
    deduped = list(seen.values())

    # Sort newest-first (None goes last)
    deduped.sort(key=lambda x: x["_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    # Assign ids and strip private fields
    now = datetime.now(timezone.utc)
    items_out = []
    for i, x in enumerate(deduped, start=1):
        items_out.append({
            "news_id": f"n{i:03d}",
            "headline": x["headline"],
            "url": x["url"],
            "raw_summary": x["raw_summary"],
            "source": x["source"],
            "source_credibility": x["source_credibility"],
            "published": x["published"],
        })

    payload = {
        "generated_at": now.isoformat(),
        "window_hours": args.hours,
        "feeds_queried": len(FEEDS),
        "feed_stats": feed_stats,
        "raw_count": len(all_items),
        "after_time_filter": len(filtered),
        "after_dedupe": len(deduped),
        "items": items_out,
    }

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Use local date for filename (project convention), not UTC
    local_today = datetime.now().strftime("%Y-%m-%d")
    out_path = out_dir / f"{local_today}_raw.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nSummary:")
    print(f"  raw fetched      : {len(all_items)}")
    print(f"  after time filter: {len(filtered)}")
    print(f"  after dedupe     : {len(deduped)}")
    print(f"  written → {out_path}")


if __name__ == "__main__":
    main()
