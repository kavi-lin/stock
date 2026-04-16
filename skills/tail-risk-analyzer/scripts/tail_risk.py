#!/usr/bin/env python3
"""
tail-risk-analyzer — single-ticker fragility from daily returns.

Usage:
    python3 tail_risk.py NVDA
    python3 tail_risk.py XLK --lookback 2y --json-only
"""
import argparse
import json
import sys
from datetime import datetime, timezone

import numpy as np
import yfinance as yf


def compute(ticker: str, lookback: str):
    hist = yf.Ticker(ticker).history(period=lookback, auto_adjust=True)
    if hist.empty or len(hist) < 30:
        raise ValueError(f"insufficient data for {ticker}")

    close = hist["Close"].dropna()
    rets = close.pct_change().dropna()

    mean = float(rets.mean())
    std = float(rets.std())
    # Excess kurtosis (Fisher) — normal distribution = 0
    kurt = float(((rets - mean) ** 4).mean() / (std ** 4) - 3) if std > 0 else 0.0
    skew = float(((rets - mean) ** 3).mean() / (std ** 3)) if std > 0 else 0.0

    var95 = float(-np.percentile(rets, 5) * 100)  # positive = loss %
    ann_vol = float(std * np.sqrt(252) * 100)

    # Max drawdown
    cum = (1 + rets).cumprod()
    peak = cum.cummax()
    dd = (cum / peak - 1).min()
    max_dd = float(-dd * 100)  # positive pct

    # Downside deviation (semi-std of negative returns)
    neg = rets[rets < 0]
    downside = float(neg.std() * np.sqrt(252) * 100) if len(neg) > 0 else 0.0

    # Normalize each component to 0-100 (higher = more fragile)
    def clamp(v, lo=0, hi=100):
        return max(lo, min(hi, v))

    # Normalize each component 0-100 (higher = more fragile)
    # Calibrated 2026-04 against SPY/TLT/NVDA/TSLA/COIN/RIVN/BTC-USD
    n_kurt = clamp(kurt * 8)            # fat-tail penalty (weight low b/c noisy on 1y)
    n_skew = clamp(-skew * 40 if skew < 0 else 0)
    n_var = clamp(var95 * 15)           # var95 6% → 90
    n_dd = clamp(max_dd * 2)            # 40% DD → 80
    n_vol = clamp(ann_vol * 1.5)        # 40% ann vol → 60 (primary fragility signal)

    # Weights: vol + dd dominate (65%); kurt/skew are noisy on 1y history
    score = round(
        n_kurt * 0.10
        + n_skew * 0.10
        + n_var * 0.15
        + n_dd * 0.30
        + n_vol * 0.35,
        1,
    )

    if score < 30:
        label, mult = "ROBUST", 1.0
    elif score < 60:
        label, mult = "MODERATE", 0.75
    else:
        label, mult = "FRAGILE", 0.5

    return {
        "ticker": ticker.upper(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lookback": lookback,
        "sample_days": int(len(rets)),
        "excess_kurtosis": round(kurt, 2),
        "skewness": round(skew, 2),
        "var_95": round(var95, 2),
        "max_drawdown": round(max_dd, 2),
        "ann_vol": round(ann_vol, 2),
        "downside_deviation": round(downside, 2),
        "tail_risk_score": score,
        "fragility_label": label,
        "position_multiplier": mult,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--lookback", default="1y")
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args()

    try:
        out = compute(args.ticker, args.lookback)
    except Exception as e:
        print(json.dumps({"error": str(e), "ticker": args.ticker}), file=sys.stdout)
        sys.exit(1)

    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not args.json_only:
        print(
            f"\n→ {out['ticker']} {out['fragility_label']} "
            f"score={out['tail_risk_score']} kurt={out['excess_kurtosis']} "
            f"VaR95={out['var_95']}% maxDD={out['max_drawdown']}% mult={out['position_multiplier']}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
