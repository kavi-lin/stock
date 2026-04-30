#!/usr/bin/env python3
"""
fetch_all_news.py — Orchestrator for News Protocol Stage 1 data sources.

Runs the 4 fetchers in parallel, merges into a unified raw.json with
fingerprint dedupe (URL primary, headline-tokens secondary), and writes
to news_logs/<DATE>_raw.json — the file news_protocol_v2 Stage 1 reads.

Sources:
  1. fetch_news_rss.py     — 9 public RSS feeds (CNBC / MarketWatch / PR Newswire / ...)
  2. fetch_finnhub_news.py — Finnhub /news?category=general (1-5 min latency)
  3. fetch_fmp_news.py     — FMP /news-general-latest + /news-stock-latest (5-30 min)
  4. fetch_sec_edgar.py    — SEC EDGAR 8-K Atom feed (0-15 min, regulatory)

Each fetcher writes its own intermediate file (kept for audit) and this
orchestrator unions them. If any fetcher fails, the run continues with
the others — never hard-fails on a single source outage.

Usage:
    python3 news/fetch_all_news.py [--hours 24] [--output news/news_logs/]
"""

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
STOPWORDS = {"the","a","an","to","of","for","in","on","at","by","and","or","is","are","as","with","from","it","its","be","this","that","new"}


def _run_fetcher(script: str, args: list, timeout: int = 120):
    """Run one fetcher subprocess; return (script, rc, stdout, stderr)."""
    cmd = [sys.executable, str(HERE / script), *args]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (script, p.returncode, p.stdout, p.stderr)
    except subprocess.TimeoutExpired:
        return (script, -1, "", f"timeout after {timeout}s")
    except Exception as e:
        return (script, -2, "", str(e))


def _headline_fp(title: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", (title or "").lower())
    tokens = [t for t in tokens if t not in STOPWORDS][:8]
    return " ".join(tokens)


def _url_fp(url: str) -> str:
    """Strip query/fragment for dedupe; same article on different platforms
    sometimes shares path but adds tracking params."""
    if not url:
        return ""
    return re.sub(r"[?#].*$", "", url.lower().rstrip("/"))


def _load_intermediate(path: Path):
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("items") or []
    except Exception as e:
        print(f"  [WARN] {path.name}: load failed: {e}", file=sys.stderr)
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--output", default="news/news_logs/")
    ap.add_argument("--skip", default="", help="Comma-separated fetcher names to skip (rss/finnhub/fmp/edgar)")
    args = ap.parse_args()

    skip = {s.strip().lower() for s in args.skip.split(",") if s.strip()}
    common = ["--hours", str(args.hours), "--output", args.output]

    fetchers = [
        ("rss",     "fetch_news_rss.py",     common),
        ("finnhub", "fetch_finnhub_news.py", common),
        ("fmp",     "fetch_fmp_news.py",     common),
        ("edgar",   "fetch_sec_edgar.py",    common),
    ]
    fetchers = [f for f in fetchers if f[0] not in skip]
    print(f"Dispatching {len(fetchers)} fetchers in parallel: {[f[0] for f in fetchers]}")

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(fetchers)) as ex:
        futures = {ex.submit(_run_fetcher, script, fa): name for name, script, fa in fetchers}
        for fut in concurrent.futures.as_completed(futures):
            name = futures[fut]
            results[name] = fut.result()

    # Print per-fetcher summary
    print("\nFetcher results:")
    for name, (script, rc, out, err) in results.items():
        last_lines = "\n    ".join((out or err).strip().splitlines()[-3:])
        status = "OK" if rc == 0 else f"FAIL rc={rc}"
        print(f"  [{status:8}] {name:8} → {script}")
        if last_lines:
            print(f"    {last_lines}")

    # Load each fetcher's intermediate file and union
    out_dir = Path(args.output)
    local_today = datetime.now().strftime("%Y-%m-%d")
    intermediate_files = {
        "rss":     out_dir / f"{local_today}_raw.json",          # rss writes to canonical name; we'll overwrite at end
        "finnhub": out_dir / f"{local_today}_finnhub_raw.json",
        "fmp":     out_dir / f"{local_today}_fmp_raw.json",
        "edgar":   out_dir / f"{local_today}_edgar_raw.json",
    }

    # Snapshot RSS items first since we'll overwrite the canonical raw.json
    rss_items = _load_intermediate(intermediate_files["rss"])

    all_items = []
    for src in ("finnhub", "fmp", "edgar"):
        if src in skip:
            continue
        for it in _load_intermediate(intermediate_files[src]):
            it.setdefault("source_credibility", "HIGH")
            all_items.append(it)
    if "rss" not in skip:
        all_items.extend(rss_items)

    # Dedupe: URL fingerprint first (exact same article), then headline tokens.
    # HIGH credibility wins ties.
    by_url = {}
    by_hl  = {}
    for it in all_items:
        url_fp = _url_fp(it.get("url", ""))
        hl_fp  = _headline_fp(it.get("headline", ""))

        cred_high = it.get("source_credibility") == "HIGH"

        # URL match: keep first or replace if HIGH beats non-HIGH
        if url_fp:
            prev = by_url.get(url_fp)
            if prev is None:
                by_url[url_fp] = it
            elif cred_high and prev.get("source_credibility") != "HIGH":
                by_url[url_fp] = it

        # Headline fingerprint match (only after URL didn't disqualify it)
        if hl_fp:
            prev = by_hl.get(hl_fp)
            if prev is None:
                by_hl[hl_fp] = it
            elif cred_high and prev.get("source_credibility") != "HIGH":
                by_hl[hl_fp] = it

    # Final union: prefer headline-fp dedupe (catches reposts where URL differs)
    deduped = list(by_hl.values())

    # Sort newest first (None pubs sink last)
    def _ts_key(it):
        p = it.get("published") or ""
        return p
    deduped.sort(key=_ts_key, reverse=True)

    # Re-id sequentially so downstream Stage 1 sees stable n001..nNNN
    for i, it in enumerate(deduped, start=1):
        it["news_id"] = f"n{i:04d}"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": args.hours,
        "providers": [name for name, _, _ in fetchers if results.get(name, (None, -1, "", ""))[1] == 0],
        "providers_failed": [name for name, _, _ in fetchers if results.get(name, (None, -1, "", ""))[1] != 0],
        "raw_count": len(all_items),
        "after_dedupe": len(deduped),
        "items": deduped,
    }

    # Overwrite canonical raw.json (intermediates kept for audit)
    out_path = out_dir / f"{local_today}_raw.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nUnified summary:")
    print(f"  total raw items    : {len(all_items)}")
    print(f"  after dedupe       : {len(deduped)}")
    print(f"  providers ok       : {payload['providers']}")
    if payload["providers_failed"]:
        print(f"  providers failed   : {payload['providers_failed']}")
    print(f"  written → {out_path}")


if __name__ == "__main__":
    main()
