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


# ── FMP /stable/* analyst & filings family (v1.65 / I-PC) ──────────────
# Replaces:
#   - finvizfinance analyst_actions scraping (unreliable, fragile to layout changes)
#   - FMP /api/v3/sec_filings (Legacy 403 since 2024-08)
# All endpoints below are on /stable/ which Starter plan unlocks.

def _fmp_get(path: str, api_key: str, params: dict | None = None):
    """Single FMP /stable/* GET helper. Returns parsed JSON or None on failure."""
    if not HAS_REQUESTS or not api_key:
        return None
    try:
        p = dict(params or {})
        p["apikey"] = api_key
        r = requests.get(f"{FMP_BASE}/stable/{path}", params=p, timeout=8)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def _fmp_grades_historical(ticker: str, api_key: str, since: datetime):
    """Historical analyst grades — upgrades/downgrades/initiations/maintains.
    Returns list of {date, action, firm, new_grade, previous_grade, url}."""
    data = _fmp_get("grades-historical", api_key, {"symbol": ticker, "limit": 50})
    if not isinstance(data, list):
        return []
    rows = []
    for it in data:
        d = it.get("date")
        if not d:
            continue
        try:
            dt = datetime.fromisoformat(d.replace("Z", "+00:00").replace(" ", "T"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_UTC)
        except Exception:
            continue
        if dt < since:
            continue
        rows.append({
            "date":           dt.isoformat(),
            "action":         it.get("action", ""),                # upgrade / downgrade / hold ...
            "firm":           it.get("gradingCompany", ""),
            "new_grade":      it.get("newGrade", ""),
            "previous_grade": it.get("previousGrade", ""),
            "url":            it.get("url", ""),
        })
    return rows


def _fmp_grades_consensus(ticker: str, api_key: str):
    """Current analyst rating distribution: strongBuy/buy/hold/sell/strongSell."""
    data = _fmp_get("grades-consensus", api_key, {"symbol": ticker})
    if isinstance(data, list) and data:
        d = data[0]
        return {
            "strong_buy":  d.get("strongBuy"),
            "buy":         d.get("buy"),
            "hold":        d.get("hold"),
            "sell":        d.get("sell"),
            "strong_sell": d.get("strongSell"),
            "consensus":   d.get("consensus"),
        }
    return None


def _fmp_price_target(ticker: str, api_key: str):
    """Analyst price target — consensus high/low/median + monthly/quarterly trend."""
    cons = _fmp_get("price-target-consensus", api_key, {"symbol": ticker})
    summ = _fmp_get("price-target-summary",   api_key, {"symbol": ticker})
    out = {}
    if isinstance(cons, list) and cons:
        c = cons[0]
        out["target_high"]     = c.get("targetHigh")
        out["target_low"]      = c.get("targetLow")
        out["target_consensus"] = c.get("targetConsensus")
        out["target_median"]   = c.get("targetMedian")
    if isinstance(summ, list) and summ:
        s = summ[0]
        out["last_month_count"]      = s.get("lastMonthCount")
        out["last_month_avg_target"] = s.get("lastMonthAvgPriceTarget")
        out["last_quarter_count"]    = s.get("lastQuarterCount")
        out["last_quarter_avg_target"] = s.get("lastQuarterAvgPriceTarget")
        out["last_year_count"]       = s.get("lastYearCount")
        out["last_year_avg_target"]  = s.get("lastYearAvgPriceTarget")
    return out or None


def _fmp_grades_news(ticker: str, api_key: str, since: datetime):
    """Analyst rating change news (with publisher / URL / image)."""
    data = _fmp_get("grades-news", api_key, {"symbol": ticker, "limit": 20})
    if not isinstance(data, list):
        return []
    rows = []
    for it in data:
        d = it.get("publishedDate")
        if not d:
            continue
        try:
            dt = datetime.fromisoformat(d.replace("Z", "+00:00").replace(" ", "T"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_UTC)
        except Exception:
            continue
        if dt < since:
            continue
        rows.append({
            "date":      dt.isoformat(),
            "title":     it.get("newsTitle", ""),
            "publisher": it.get("publisher", ""),
            "url":       it.get("newsURL", ""),
        })
    return rows


def _fmp_sec_filings(ticker: str, api_key: str, since: datetime):
    """Recent SEC filings via /stable/sec-filings-financials (replaces broken
    /api/v3/sec_filings Legacy 403). Returns (rows, failed_bool).
    Note: sec-filings-financials returns financial-related filings (10-Q/K, 8-K).
    """
    if not HAS_REQUESTS or not api_key:
        return [], False
    data = _fmp_get("sec-filings-financials", api_key, {"symbol": ticker, "limit": 10})
    if data is None:
        return [], True
    if not isinstance(data, list):
        return [], False
    out = []
    for f in data:
        filed = f.get("filedDate") or f.get("filingDate") or f.get("acceptedDate") or f.get("date")
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
            "form":       f.get("formType") or f.get("type") or f.get("form", ""),
            "filed_date": dt.isoformat(),
            "url":        f.get("finalLink") or f.get("link") or f.get("reportUrl", ""),
        })
    return out, False


# ── Finnhub /company-news supplement (free; structured sentiment field) ──
def _finnhub_company_news(ticker: str, since: datetime, max_items: int = 25):
    """Returns headlines with category/sentiment from Finnhub. Supplements finviz/yf."""
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key or not HAS_REQUESTS:
        return []
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/company-news",
            params={"symbol": ticker,
                    "from":   since.date().isoformat(),
                    "to":     datetime.now(_UTC).date().isoformat(),
                    "token":  api_key},
            timeout=8,
        )
        if r.status_code != 200:
            return []
        data = r.json() or []
        rows = []
        for it in data[:max_items]:
            ts = it.get("datetime")
            if not ts:
                continue
            try:
                dt = datetime.fromtimestamp(ts, tz=_UTC)
            except Exception:
                continue
            if dt < since:
                continue
            rows.append({
                "date":     dt.isoformat(),
                "title":    it.get("headline", ""),
                "source":   it.get("source", "Finnhub"),
                "url":      it.get("url", ""),
                "category": it.get("category", ""),
            })
        return rows
    except Exception:
        return []


# ── Main ───────────────────────────────────────────────────────────────
def fetch(ticker: str, hours: int, use_fmp: bool = True):
    ticker = ticker.upper()
    now = datetime.now(_UTC)
    news_since    = now - timedelta(hours=hours)
    analyst_since = now - timedelta(days=30)   # analyst actions looked back 30d

    # Headlines: finviz + yfinance + Finnhub /company-news
    finviz_news = _finviz_news(ticker, news_since)
    yf_items    = _yf_news(ticker, news_since)
    fh_news     = _finnhub_company_news(ticker, news_since)
    headlines   = _dedupe_headlines(finviz_news + yf_items + fh_news)

    # finviz analyst actions kept as fallback when FMP grades-historical empty
    finviz_analyst_actions = _finviz_analyst_actions(ticker, analyst_since)

    api_key = os.getenv("FMP_API_KEY") if use_fmp else None
    fmp_calls, fmp_failures = 0, 0
    fmp_analyst_grades = []
    fmp_consensus = None
    fmp_price_target = None
    fmp_grades_news = []
    sec_filings = []
    if api_key:
        # 5 FMP calls: grades-historical, grades-consensus, price-target-consensus,
        # price-target-summary (folded into _fmp_price_target), grades-news, sec-filings
        fmp_analyst_grades = _fmp_grades_historical(ticker, api_key, analyst_since)
        fmp_consensus      = _fmp_grades_consensus(ticker, api_key)
        fmp_price_target   = _fmp_price_target(ticker, api_key)        # 2 calls
        fmp_grades_news    = _fmp_grades_news(ticker, api_key, news_since)
        sec_filings, failed = _fmp_sec_filings(ticker, api_key, now - timedelta(days=14))
        fmp_calls = 6
        if failed:
            fmp_failures = 1

    # analyst_actions: prefer FMP grades-historical (structured); fallback finviz
    if fmp_analyst_grades:
        analyst_actions_primary = fmp_analyst_grades
        analyst_actions_source = "fmp_grades_historical"
    else:
        analyst_actions_primary = finviz_analyst_actions
        analyst_actions_source = "finviz_fallback"

    # Sparse determination: subagent should augment with WebSearch if we're thin
    sparse = (len(headlines) < 5 and len(analyst_actions_primary) == 0)
    recommendation = "websearch_recommended" if sparse else "ok"

    warnings = []
    if len(headlines) == 0:
        warnings.append("no_headlines_in_window")
    if len(analyst_actions_primary) == 0:
        warnings.append("no_analyst_actions_in_30d")

    return {
        "ticker":        ticker,
        "generated_at":  now.isoformat(timespec="seconds"),
        "window_hours":  hours,
        "headlines":            headlines,
        "analyst_actions":      analyst_actions_primary,
        "analyst_actions_source": analyst_actions_source,
        "analyst_consensus":    fmp_consensus,
        "price_target":         fmp_price_target,
        "analyst_news":         fmp_grades_news,
        "sec_filings_recent":   sec_filings,
        "warnings":             warnings,
        "data_quality": {
            "finviz_news_count":     len(finviz_news),
            "finviz_analyst_count":  len(finviz_analyst_actions),
            "yf_news_count":         len(yf_items),
            "finnhub_news_count":    len(fh_news),
            "fmp_grades_count":      len(fmp_analyst_grades),
            "fmp_grades_news_count": len(fmp_grades_news),
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
