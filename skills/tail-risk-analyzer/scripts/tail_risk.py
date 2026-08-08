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

import os

import numpy as np
import yfinance as yf

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from skills._shared.technical_core import fetch_history  # noqa: E402


def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


# Fragility bands, lower bound inclusive: 30 → MODERATE, 60 → FRAGILE. This table is
# mirrored in investment/scripts/{trade_plan_builder.py:102, validate_session_export.py:386
# (+ the §14b enum gate), replay_trade_plan.py} — moving a bound means moving all of them
# and re-baselining the replay cohort.
FRAGILITY_BANDS = ((30.0, "ROBUST", 1.0), (60.0, "MODERATE", 0.75), (None, "FRAGILE", 0.5))


def fragility_for(score):
    """score → (fragility_label, position_multiplier)."""
    for upper, label, mult in FRAGILITY_BANDS:
        if upper is None or score < upper:
            return label, mult


def compute(ticker: str, lookback: str):
    # V4.113.3: canonical price source (FMP dividend-adjusted primary, yfinance fallback).
    # Both legs are dividend-adjusted as of V4.113.0 — required here because this module
    # computes a return *distribution*, where an unadjusted ex-dividend drop reads as a
    # real down day and inflates drawdown, downside deviation and negative skew.
    hist, _ = fetch_history(ticker, period=lookback)
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

    # Downside deviation (semi-std of negative returns). Needs >= 2 samples: pandas' std
    # is ddof=1, so a single negative day divides by zero and yields NaN — which
    # json.dumps then writes as the bare literal `NaN`, invalid strict JSON. No consumer
    # reads this field today, so the failure was silent; report 0.0 instead.
    neg = rets[rets < 0]
    downside = float(neg.std() * np.sqrt(252) * 100) if len(neg) > 1 else 0.0

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

    label, mult = fragility_for(score)

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
