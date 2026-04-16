#!/usr/bin/env python3
"""
market-sentiment-analyzer — composite market sentiment (0-100).

Replaces CNN F&G web-search queries with a local computation combining:
  VIX level + percentile, SPY RSI(14), SPY vs MA50/MA200, Put/Call (proxy),
  and CNN F&G (fetched via public JSON endpoint with graceful fallback).

Usage:
    python3 sentiment.py
    python3 sentiment.py --json-only
"""
import argparse
import json
import sys
from datetime import datetime, timezone

import requests
import yfinance as yf
import pandas as pd
import numpy as np

TIMEOUT = 10
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args()

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
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not args.json_only:
        print(f"\n→ composite {composite} ({out['label']}) │ VIX {vix_now:.1f} {vix_regime} │ SPY RSI {spy_rsi:.1f}", file=sys.stderr)


if __name__ == "__main__":
    main()
