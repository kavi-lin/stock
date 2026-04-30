#!/usr/bin/env python3
"""
market-sentiment-analyzer — composite market sentiment (0-100).

Replaces CNN F&G web-search queries with a local computation combining:
  VIX level + percentile, SPY RSI(14), SPY vs MA50/MA200, Put/Call (proxy),
  and CNN F&G (fetched via public JSON endpoint with graceful fallback).

Usage:
    python3 sentiment.py                 # default: use 15-min cache if fresh
    python3 sentiment.py --json-only
    python3 sentiment.py --no-cache      # force fresh compute
    python3 sentiment.py --max-age 300   # custom TTL in seconds (default 900)
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import requests
import yfinance as yf
import pandas as pd
import numpy as np

TIMEOUT = 10
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# Market-level sentiment is ticker-agnostic; within 15 minutes the composite
# barely moves (VIX intraday range ~0.3 pts, F&G updates ~hourly). Batch runs
# that query N tickers in one session share the same value, so we cache a
# single file rather than recompute per ticker.
SCRIPT_DIR      = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR       = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "cache"))
CACHE_FILE      = os.path.join(CACHE_DIR, "sentiment_latest.json")
DEFAULT_TTL_SEC = 900


def _load_cache(max_age_sec):
    """Return cached payload (dict) if fresh, else None."""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        age_sec = int(datetime.now().timestamp() - os.path.getmtime(CACHE_FILE))
        if age_sec >= max_age_sec:
            return None
        with open(CACHE_FILE, "r", encoding="utf-8") as fp:
            payload = json.load(fp)
        # Strip previous cache sentinels — we'll re-stamp.
        for k in ("cache_hit", "cache_age_sec", "cache_source"):
            payload.pop(k, None)
        payload["cache_hit"]     = True
        payload["cache_age_sec"] = age_sec
        payload["cache_source"]  = CACHE_FILE
        return payload
    except Exception:
        return None


def _write_cache(payload):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)
    except Exception as e:
        # Cache write failure must not break the skill — fall through silently.
        print(f"[sentiment] cache write failed: {e}", file=sys.stderr)


def rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_val = 100 - (100 / (1 + rs))
    return float(rsi_val.iloc[-1]) if not rsi_val.empty else float("nan")


def pct_rank(series: pd.Series, value: float) -> float:
    arr = series.dropna().values
    if len(arr) == 0:
        return float("nan")
    return float((arr < value).sum() / len(arr) * 100)


def fetch_yf():
    """Fetch VIX + SPY history in one batch."""
    tickers = yf.download(
        ["^VIX", "SPY"], period="1y", interval="1d",
        auto_adjust=True, progress=False, group_by="ticker"
    )
    return tickers


def fetch_cnn_fg():
    """CNN Fear & Greed index — try backend JSON, else None."""
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        return float(data["fear_and_greed"]["score"])
    except Exception:
        return None


def fetch_pcr():
    """CBOE total put/call ratio — best-effort; return None if unavailable."""
    try:
        url = "https://cdn.cboe.com/api/global/us_indices/daily_prices/_totalpc_daily_price_history.json"
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "data" in data and data["data"]:
            return float(data["data"][-1].get("close") or data["data"][-1].get("value"))
    except Exception:
        pass
    return None


def normalize_vix(vix: float) -> float:
    # piecewise linear: 12→90, 20→50, 35→15, cap 5-95
    if vix <= 12: return 90.0
    if vix <= 20: return 90 - (vix - 12) * (40 / 8)       # 90→50
    if vix <= 35: return 50 - (vix - 20) * (35 / 15)      # 50→15
    return max(5.0, 15 - (vix - 35) * 0.5)


def normalize_pcr(pcr: float) -> float:
    if pcr <= 0.6: return 85.0
    if pcr <= 0.9: return 85 - (pcr - 0.6) * (35 / 0.3)   # 85→50
    if pcr <= 1.2: return 50 - (pcr - 0.9) * (30 / 0.3)   # 50→20
    return max(5.0, 20 - (pcr - 1.2) * 30)


def normalize_ma(pct: float) -> float:
    # SPY pct above/below MA200 → 0% → 50, +10% → 80, -10% → 20
    return float(max(0, min(100, 50 + pct * 3)))


def label_for(score: float) -> str:
    if score >= 80: return "Extreme Greed"
    if score >= 60: return "Greed"
    if score >= 40: return "Neutral"
    if score >= 20: return "Fear"
    return "Extreme Fear"


# ── Ticker-specific signals (v1.64 / I-PB) ─────────────────────────────────
# Replaces Phase 2 Sentiment lane "個股層 web search Reddit/X/short interest/insider activity"
# with structured API. Reddit/X narrative is left to subagent (still allowed; no API).
def _fetch_ticker_signals(ticker: str) -> dict:
    """Pull insider statistics (FMP), insider sentiment MSPR (Finnhub), short
    interest (yfinance fallback) for a single ticker. Each sub-call has its own
    try/except — partial result is acceptable; subagent should handle nulls."""
    out = {
        "ticker": ticker.upper(),
        "insider_stats": None,        # FMP /stable/insider-trading/statistics
        "insider_sentiment": None,    # Finnhub /stock/insider-sentiment (MSPR trend)
        "short_pct_float": None,      # yfinance shortPercentOfFloat
        "short_pct_float_source": None,
    }

    fmp_key = os.getenv("FMP_API_KEY")
    fh_key  = os.getenv("FINNHUB_API_KEY")

    # 1) FMP insider statistics (quarterly aggregated)
    if fmp_key:
        try:
            r = requests.get(
                "https://financialmodelingprep.com/stable/insider-trading/statistics",
                params={"symbol": ticker, "apikey": fmp_key},
                timeout=TIMEOUT,
            )
            if r.status_code == 200:
                arr = r.json()
                if isinstance(arr, list) and arr:
                    # Most recent quarter first; pick top 4 quarters for trend
                    arr.sort(key=lambda x: (x.get("year", 0), x.get("quarter", 0)), reverse=True)
                    out["insider_stats"] = [{
                        "year": x.get("year"), "quarter": x.get("quarter"),
                        "acquired_disposed_ratio": x.get("acquiredDisposedRatio"),
                        "total_acquired_shares": x.get("totalAcquired"),
                        "total_disposed_shares": x.get("totalDisposed"),
                        "acquired_transactions": x.get("acquiredTransactions"),
                        "disposed_transactions": x.get("disposedTransactions"),
                    } for x in arr[:4]]
        except Exception as e:
            print(f"[sentiment] FMP insider stats error: {e}", file=sys.stderr)

    # 2) Finnhub insider sentiment (MSPR per month, last 6 months)
    if fh_key:
        try:
            from datetime import timedelta as _td
            today = datetime.now().date()
            r = requests.get(
                "https://finnhub.io/api/v1/stock/insider-sentiment",
                params={"symbol": ticker,
                        "from": (today - _td(days=180)).isoformat(),
                        "to":   today.isoformat(),
                        "token": fh_key},
                timeout=TIMEOUT,
            )
            if r.status_code == 200:
                data = r.json()
                items = (data or {}).get("data", []) if isinstance(data, dict) else []
                if items:
                    # MSPR (Monthly Share Purchase Ratio) -100 to +100
                    items.sort(key=lambda x: (x.get("year", 0), x.get("month", 0)))
                    out["insider_sentiment"] = {
                        "monthly_mspr": [{
                            "year": x.get("year"), "month": x.get("month"),
                            "mspr": x.get("mspr"),
                            "change_shares": x.get("change"),
                        } for x in items[-6:]],
                        "latest_mspr": items[-1].get("mspr") if items else None,
                    }
        except Exception as e:
            print(f"[sentiment] Finnhub insider sentiment error: {e}", file=sys.stderr)

    # 3) Short interest fallback — yfinance .info (bi-monthly FINRA snapshot)
    try:
        info = yf.Ticker(ticker).info or {}
        sp = info.get("shortPercentOfFloat")
        if sp is not None:
            out["short_pct_float"] = round(float(sp) * 100, 2)  # 0.012 → 1.2%
            out["short_pct_float_source"] = "yfinance.info (FINRA bi-monthly)"
    except Exception as e:
        print(f"[sentiment] yfinance short interest error: {e}", file=sys.stderr)

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-only", action="store_true")
    ap.add_argument("--no-cache", action="store_true", help="force fresh compute (bypass cache)")
    ap.add_argument("--max-age", type=int, default=DEFAULT_TTL_SEC,
                    help=f"cache TTL in seconds (default {DEFAULT_TTL_SEC})")
    ap.add_argument("--ticker", default=None,
                    help="If set, also include per-ticker insider statistics (FMP), "
                         "insider sentiment MSPR (Finnhub), short interest (yfinance). "
                         "Replaces Phase 2 Sentiment lane individual-stock web search.")
    args = ap.parse_args()

    # Cache check (skipped with --no-cache, OR when --ticker is set since
    # ticker-specific signals are not in the market-level cache).
    if not args.no_cache and not args.ticker:
        cached = _load_cache(args.max_age)
        if cached is not None:
            print(json.dumps(cached, ensure_ascii=False, indent=2))
            if not args.json_only:
                print(f"\n→ cache hit (age {cached['cache_age_sec']}s) │ composite {cached.get('composite_score')} ({cached.get('label')})", file=sys.stderr)
            return

    data = fetch_yf()
    # yf multi-ticker returns MultiIndex or dict-like; normalize
    try:
        vix_close = data["^VIX"]["Close"].dropna()
        spy_close = data["SPY"]["Close"].dropna()
    except Exception:
        vix_close = yf.Ticker("^VIX").history(period="1y")["Close"].dropna()
        spy_close = yf.Ticker("SPY").history(period="1y")["Close"].dropna()

    vix_now = float(vix_close.iloc[-1])
    vix_pct = pct_rank(vix_close, vix_now)
    if vix_now < 15: vix_regime = "LOW"
    elif vix_now < 22: vix_regime = "NORMAL"
    elif vix_now < 32: vix_regime = "ELEVATED"
    else: vix_regime = "CRISIS"

    spy_now = float(spy_close.iloc[-1])
    ma50 = float(spy_close.rolling(50).mean().iloc[-1])
    ma200 = float(spy_close.rolling(200).mean().iloc[-1])
    spy_rsi = rsi(spy_close, 14)
    pct_above_ma50 = (spy_now / ma50 - 1) * 100
    pct_above_ma200 = (spy_now / ma200 - 1) * 100

    pcr = fetch_pcr()
    fg = fetch_cnn_fg()

    components = {
        "vix": normalize_vix(vix_now),
        "spy_rsi": float(spy_rsi) if not np.isnan(spy_rsi) else None,
        "pct_above_ma": normalize_ma(pct_above_ma200),
    }
    if pcr is not None:
        components["pcr"] = normalize_pcr(pcr)
    if fg is not None:
        components["fg"] = fg

    valid = [v for v in components.values() if v is not None and not (isinstance(v, float) and np.isnan(v))]
    composite = round(sum(valid) / len(valid), 1) if valid else None

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "composite_score": composite,
        "label": label_for(composite) if composite is not None else None,
        "vix": {
            "current": round(vix_now, 2),
            "percentile_1y": round(vix_pct, 1),
            "regime": vix_regime,
        },
        "spy_momentum": {
            "rsi_14": round(spy_rsi, 1) if not np.isnan(spy_rsi) else None,
            "pct_above_ma50": round(pct_above_ma50, 2),
            "pct_above_ma200": round(pct_above_ma200, 2),
        },
        "put_call_ratio": round(pcr, 2) if pcr is not None else None,
        "fear_greed_index": round(fg, 1) if fg is not None else None,
        "components_used": list(components.keys()),
        "extreme_sentiment_triggered": (composite is not None and (composite > 80 or composite < 20)),
        "cache_hit": False,
        "cache_age_sec": 0,
    }

    # Don't cache when ticker-specific block is present — that's per-ticker, not market-wide
    if not args.ticker:
        _write_cache(out)

    # Per-ticker structured signals (insider stats / MSPR / short interest)
    if args.ticker:
        out["ticker_signals"] = _fetch_ticker_signals(args.ticker)

    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not args.json_only:
        msg = f"\n→ fresh compute │ composite {composite} ({out['label']}) │ VIX {vix_now:.1f} {vix_regime} │ SPY RSI {spy_rsi:.1f}"
        if args.ticker and out.get("ticker_signals"):
            ts = out["ticker_signals"]
            stats = (ts.get("insider_stats") or [None])[0]
            ratio = stats.get("acquired_disposed_ratio") if stats else None
            short_pct = ts.get("short_pct_float")
            msg += f" │ {args.ticker} insider_ratio={ratio} short={short_pct}%"
        print(msg, file=sys.stderr)


if __name__ == "__main__":
    main()
