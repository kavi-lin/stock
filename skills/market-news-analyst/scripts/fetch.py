#!/usr/bin/env python3
"""
market-news-analyst — per-ticker 48h news + structured analyst actions.

Produces the JSON consumed by investment_protocol_v4_8 Phase 2 News subagent.
Design principle: do deterministic scraping in Python so the subagent can't
hallucinate analyst actions or SEC filings; let the subagent judge headline
tone. When sources come back thin, surface a `sparse=true` flag so the
subagent can decide to augment with WebSearch.

Sources:
- finvizfinance (free, no API key): analyst actions + 100-row news list
- yfinance .news (free): additional recent headlines
- FMP (optional): SEC filings supplement; short-circuits on 429

Usage:
    python3 fetch.py STLD
    python3 fetch.py STLD --hours 48 --json-only
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import yfinance as yf

try:
    import requests
    HAS_REQUESTS = True
except Exception:
    HAS_REQUESTS = False

try:
    from finvizfinance.quote import finvizfinance
    HAS_FINVIZ = True
except Exception:
    HAS_FINVIZ = False


FMP_BASE = "https://financialmodelingprep.com"
_UTC = timezone.utc


# ── finvizfinance extractors ───────────────────────────────────────────
def _finviz_news(ticker: str, since: datetime):
    """Return list of {date, title, source, url} within `since`."""
    if not HAS_FINVIZ:
        return []
    try:
        s = finvizfinance(ticker)
        df = s.ticker_news()
    except Exception:
        return []
    if df is None or df.empty:
        return []
    rows = []
    for _, r in df.iterrows():
        d = r.get("Date")
        if d is None:
            continue
        # Normalize to aware UTC for comparison
        if hasattr(d, "tz_localize") and d.tz is None:
            d = d.tz_localize(_UTC)
        elif hasattr(d, "replace") and getattr(d, "tzinfo", None) is None:
            d = d.replace(tzinfo=_UTC)
        try:
            if d.to_pydatetime() < since if hasattr(d, "to_pydatetime") else d < since:
                continue
        except Exception:
            pass
        rows.append({
            "date":   d.isoformat() if hasattr(d, "isoformat") else str(d),
            "title":  str(r.get("Title", "")).strip(),
            "source": str(r.get("Source", "")).strip(),
            "url":    str(r.get("Link", "")).strip(),
        })
    return rows


def _finviz_analyst_actions(ticker: str, since: datetime):
    """Recent upgrade/downgrade/initiated/reiterated actions within `since`."""
    if not HAS_FINVIZ:
        return []
    try:
        s = finvizfinance(ticker)
        df = s.ticker_outer_ratings()
    except Exception:
        return []
    if df is None or df.empty:
        return []
    rows = []
    for _, r in df.iterrows():
        d = r.get("Date")
        if d is None:
            continue
        if hasattr(d, "tz_localize") and d.tz is None:
            d = d.tz_localize(_UTC)
        elif hasattr(d, "replace") and getattr(d, "tzinfo", None) is None:
            d = d.replace(tzinfo=_UTC)
        try:
            if d.to_pydatetime() < since if hasattr(d, "to_pydatetime") else d < since:
                continue
        except Exception:
            pass
        rows.append({
            "date":         d.isoformat() if hasattr(d, "isoformat") else str(d),
            "action":       str(r.get("Status", "")).strip(),    # Upgrade / Downgrade / Initiated / Resumed / Reiterated
            "firm":         str(r.get("Outer", "")).strip(),
            "rating":       str(r.get("Rating", "")).strip(),    # e.g. "Overweight → Equal-Weight"
            "price_target": str(r.get("Price", "")).strip(),
        })
    return rows


# ── yfinance supplemental ──────────────────────────────────────────────
def _yf_news(ticker: str, since: datetime):
    """Return additional headlines from yfinance .news not already in finviz."""
    try:
        items = yf.Ticker(ticker).news or []
    except Exception:
        return []
    rows = []
    for it in items:
        # yfinance 0.2.x nests actual content under "content"
        c = it.get("content") or it
        pub = c.get("pubDate") or c.get("providerPublishTime")
        if pub is None:
            continue
        try:
            if isinstance(pub, (int, float)):
                dt = datetime.fromtimestamp(pub, tz=_UTC)
            else:
                dt = datetime.fromisoformat(str(pub).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=_UTC)
        except Exception:
            continue
        if dt < since:
            continue
        title = c.get("title") or ""
        provider = c.get("provider") or {}
        source = provider.get("displayName") if isinstance(provider, dict) else str(provider)
        click_url = c.get("clickThroughUrl") or {}
        url = click_url.get("url") if isinstance(click_url, dict) else ""
        rows.append({
            "date":   dt.isoformat(),
            "title":  title.strip(),
            "source": (source or "Yahoo Finance").strip(),
            "url":    url or c.get("canonicalUrl", {}).get("url", "") if isinstance(c.get("canonicalUrl"), dict) else "",
        })
    return rows


def _dedupe_headlines(rows):
    """Dedupe by normalized title (case-insensitive, strip whitespace)."""
    seen = set()
    out = []
    for r in rows:
        key = (r.get("title") or "").lower().strip()[:80]
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(r)
    return sorted(out, key=lambda r: r.get("date", ""), reverse=True)


# ── FMP SEC filings (optional; short-circuits on 429) ──────────────────
def _fmp_sec_filings(ticker: str, api_key: str, since: datetime):
    """Recent SEC filings (8-K / 10-Q / etc.) within `since`.
    Short-circuits on 429. Returns (rows, failed_bool)."""
    if not HAS_REQUESTS or not api_key:
        return [], False
    try:
        url = f"{FMP_BASE}/api/v3/sec_filings/{ticker}"
        r = requests.get(url, params={"apikey": api_key, "limit": 10}, timeout=8)
        if r.status_code == 429:
            return [], True   # quota exhausted — treated as failure
        if r.status_code != 200:
            return [], True
        data = r.json() or []
        out = []
        for f in data:
            filed = f.get("fillingDate") or f.get("filingDate") or f.get("acceptedDate")
            if not filed:
                continue
            try:
                dt = datetime.fromisoformat(filed.replace("Z", "+00:00").replace(" ", "T"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=_UTC)
            except Exception:
                continue
            if dt < since:
                continue
            out.append({
                "form":        f.get("type") or f.get("form", ""),
                "filed_date":  dt.isoformat(),
                "url":         f.get("finalLink") or f.get("link", ""),
            })
        return out, False
    except Exception:
        return [], True


# ── Main ───────────────────────────────────────────────────────────────
def fetch(ticker: str, hours: int, use_fmp: bool = True):
    ticker = ticker.upper()
    now = datetime.now(_UTC)
    news_since    = now - timedelta(hours=hours)
    analyst_since = now - timedelta(days=30)   # analyst actions looked back 30d — rare to trigger per-48h

    finviz_news = _finviz_news(ticker, news_since)
    yf_items    = _yf_news(ticker, news_since)
    headlines   = _dedupe_headlines(finviz_news + yf_items)

    analyst_actions = _finviz_analyst_actions(ticker, analyst_since)

    api_key = os.getenv("FMP_API_KEY") if use_fmp else None
    fmp_calls, fmp_failures = 0, 0
    sec_filings = []
    if api_key:
        fmp_calls = 1
        sec_filings, failed = _fmp_sec_filings(ticker, api_key, now - timedelta(days=14))
        if failed:
            fmp_failures = 1

    # Sparse determination: subagent should augment with WebSearch if we're thin
    sparse = (len(headlines) < 5 and len(analyst_actions) == 0)
    recommendation = "websearch_recommended" if sparse else "ok"

    warnings = []
    if len(headlines) == 0:
        warnings.append("no_headlines_in_window")
    if len(analyst_actions) == 0:
        warnings.append("no_analyst_actions_in_30d")

    return {
        "ticker":        ticker,
        "generated_at":  now.isoformat(timespec="seconds"),
        "window_hours":  hours,
        "headlines":            headlines,
        "analyst_actions":      analyst_actions,
        "sec_filings_recent":   sec_filings,
        "warnings":             warnings,
        "data_quality": {
            "finviz_news_count":     len(finviz_news),
            "finviz_analyst_count":  len(analyst_actions),
            "yf_news_count":         len(yf_items),
            "headlines_total_dedup": len(headlines),
            "fmp_calls":             fmp_calls,
            "fmp_failures":          fmp_failures,
            "sparse":                sparse,
            "recommendation":        recommendation,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--hours", type=int, default=48,
                    help="Lookback window for company news (default 48)")
    ap.add_argument("--json-only", action="store_true",
                    help="Output JSON only; no human summary")
    ap.add_argument("--no-fmp", action="store_true",
                    help="Skip FMP sec-filings supplement (avoids 429 noise)")
    args = ap.parse_args()

    try:
        payload = fetch(args.ticker, args.hours, use_fmp=not args.no_fmp)
    except Exception as e:
        err = {"ticker": args.ticker.upper(), "error": f"{type(e).__name__}: {e}"}
        print(json.dumps(err, indent=2))
        sys.exit(1)

    print(json.dumps(payload, indent=2, default=str))

    if args.json_only:
        return

    # Human summary
    dq = payload["data_quality"]
    print(f"\n=== {payload['ticker']} news fetch (last {args.hours}h) ===", file=sys.stderr)
    print(f"  Headlines: {len(payload['headlines'])} deduped "
          f"(finviz={dq['finviz_news_count']}, yfinance={dq['yf_news_count']})",
          file=sys.stderr)
    print(f"  Analyst actions (30d): {len(payload['analyst_actions'])}", file=sys.stderr)
    print(f"  SEC filings (14d): {len(payload['sec_filings_recent'])}", file=sys.stderr)
    print(f"  Sparse: {dq['sparse']}   Recommendation: {dq['recommendation']}", file=sys.stderr)
    if payload["warnings"]:
        print(f"  ⚠ {', '.join(payload['warnings'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
