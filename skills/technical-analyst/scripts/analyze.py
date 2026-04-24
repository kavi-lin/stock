#!/usr/bin/env python3
"""
technical-analyst — chart-pure technical snapshot for a single ticker.

Produces the JSON consumed by investment_protocol_v4_8 Phase 2 Technical
subagent. Per the V4.8 rubric: 20/50/200MA structure, RSI(14), MACD
histogram, volume vs 20D avg, recent support/resistance.

Shares computation primitives with momentum-monitor via the
`technical_core` module (MA / RSI / volume / stage / crosses are defined
once, consumed by both skills). This script adds MACD and S-R which are
chart-technical-specific and not needed by momentum scoring.

Usage:
    python3 analyze.py NVDA
    python3 analyze.py NVDA --json-only
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Reuse the core primitives from momentum-monitor rather than duplicating.
# Both skills live under skills/<name>/scripts/ — add momentum-monitor's
# scripts dir to sys.path so `technical_core` is importable.
_SHARED_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "momentum-monitor", "scripts"
))
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)

from technical_core import (   # noqa: E402
    fetch_history,
    volume_profile,
    ma_structure,
    rsi_state,
    compute_macd,
)

import pandas as pd   # noqa: E402


# ── Support / Resistance via swing pivots ──────────────────────────────
def compute_support_resistance(hist, lookback=60, pivot_window=5):
    """Detect swing highs/lows via `pivot_window`-bar confirmation on both sides.
    A swing high at bar i requires high[i] = max(high[i-k..i+k]) where k = pivot_window//2.
    Returns nearest resistance above current price + nearest support below it.
    """
    high = hist["High"].tail(lookback)
    low  = hist["Low"].tail(lookback)
    close = hist["Close"]
    current = float(close.iloc[-1])

    k = max(1, pivot_window // 2)
    swing_highs, swing_lows = [], []

    # Pivot detection — skip edges where we lack k-bar window on both sides
    for i in range(k, len(high) - k):
        h = float(high.iloc[i])
        # swing high if h is the maximum in [i-k, i+k]
        if h == high.iloc[i-k:i+k+1].max():
            swing_highs.append({"date": str(high.index[i].date()), "price": round(h, 2)})
        l = float(low.iloc[i])
        if l == low.iloc[i-k:i+k+1].min():
            swing_lows.append({"date": str(low.index[i].date()), "price": round(l, 2)})

    # Dedupe near-duplicate levels (within 1%)
    def _dedupe(levels):
        if not levels: return []
        sorted_levels = sorted(levels, key=lambda x: x["price"])
        out = [sorted_levels[0]]
        for lv in sorted_levels[1:]:
            if abs(lv["price"] - out[-1]["price"]) / out[-1]["price"] > 0.01:
                out.append(lv)
        return out

    swing_highs = _dedupe(swing_highs)
    swing_lows  = _dedupe(swing_lows)

    # Nearest level ABOVE current = resistance; BELOW = support
    resistances_above = sorted([h["price"] for h in swing_highs if h["price"] > current])
    supports_below    = sorted([l["price"] for l in swing_lows  if l["price"] < current], reverse=True)

    nearest_resistance = round(resistances_above[0], 2) if resistances_above else None
    nearest_support    = round(supports_below[0],    2) if supports_below    else None

    return {
        "recent_swing_highs":  [h["price"] for h in sorted(swing_highs, key=lambda x: x["date"], reverse=True)[:5]],
        "recent_swing_lows":   [l["price"] for l in sorted(swing_lows,  key=lambda x: x["date"], reverse=True)[:5]],
        "nearest_resistance":  nearest_resistance,
        "nearest_support":     nearest_support,
        "pct_to_resistance":   round((nearest_resistance / current - 1) * 100, 2) if nearest_resistance else None,
        "pct_to_support":      round((1 - nearest_support    / current) * 100, 2) if nearest_support    else None,
    }


# ── Rubric-based signal hints ──────────────────────────────────────────
def _signal_hints(ma, rsi, volume, macd):
    """V4.8 Phase 2 Technical rubric shortcuts. Subagent still makes final call
    but these booleans make the decision cheap (no extra LLM reasoning needed
    for the obvious cases)."""
    stage = ma.get("stage")
    rsi_val = rsi.get("rsi_14")
    vol_ratio = volume.get("ratio_20d")
    vol_trend = volume.get("volume_trend")
    am200 = ma.get("above_ma200_pct") or 0

    # Full Stage-2 structural bull: MA stack intact, RSI in healthy range, volume expanding
    stage2_complete = (
        stage == "Stage 2 uptrend"
        and rsi_val is not None and 40 <= rsi_val <= 70
        and vol_trend == "expanding"
    )

    # Bearish breakdown: below MA200 + volume confirming the break
    bearish_breakdown = (
        stage == "Stage 4 downtrend"
        and am200 < -5
        and vol_ratio is not None and vol_ratio > 1.3
    )

    # Parabolic exhaustion risk
    parabolic_risk = am200 > 80 and rsi_val is not None and rsi_val > 75

    # Rubric hint — suggested score range; subagent decides exact signal/score.
    if bearish_breakdown:     hint = "-3 to -4"
    elif stage2_complete:     hint = "+3 to +4"
    elif parabolic_risk:      hint = "+1 to +2 (parabolic risk — consider fade)"
    elif stage == "Stage 2 uptrend":  hint = "+1 to +2"
    elif stage == "Stage 3 top":      hint = "-1 to -2"
    elif stage == "Stage 4 downtrend": hint = "-2 to -3"
    else:                     hint = "0 to +1 (basing — wait for confirmation)"

    return {
        "stage_2_complete":  stage2_complete,
        "bearish_breakdown": bearish_breakdown,
        "parabolic_risk":    parabolic_risk,
        "macd_bullish_cross": macd.get("bullish_cross", False),
        "macd_bearish_cross": macd.get("bearish_cross", False),
        "rubric_hint":       hint,
    }


# ── Main ───────────────────────────────────────────────────────────────
def analyze(ticker: str):
    ticker = ticker.upper()
    hist, _ = fetch_history(ticker, period="1y")
    close = hist["Close"]
    current_price = round(float(close.iloc[-1]), 2)

    ma      = ma_structure(hist)
    rsi     = rsi_state(hist)
    volume  = volume_profile(hist)
    macd    = compute_macd(close)
    sr      = compute_support_resistance(hist)
    hints   = _signal_hints(ma, rsi, volume, macd)

    # Price block
    prev_close = float(close.iloc[-2]) if len(close) > 1 else current_price
    change_pct = round((current_price / prev_close - 1) * 100, 2) if prev_close > 0 else 0.0
    price_block = {
        "current":      current_price,
        "change_pct":   change_pct,
        "52w_high":     round(float(hist["High"].max()), 2),
        "52w_low":      round(float(hist["Low"].min()), 2),
    }

    warnings = []
    if ma.get("stage") == "unknown":
        warnings.append("insufficient_history_for_stage")
    if volume.get("intraday_state") == "too_early":
        warnings.append("intraday_volume_unreliable")
    if hints["parabolic_risk"]:
        warnings.append("parabolic_exhaustion_risk")

    return {
        "ticker":              ticker,
        "generated_at":        datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "price":               price_block,
        "ma_structure":        ma,
        "rsi_14":              rsi,
        "macd":                macd,
        "volume":              volume,
        "support_resistance":  sr,
        "signal_hints":        hints,
        "warnings":            warnings,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args()

    try:
        payload = analyze(args.ticker)
    except Exception as e:
        err = {"ticker": args.ticker.upper(), "error": f"{type(e).__name__}: {e}", "skill_execution_failed": True}
        print(json.dumps(err, indent=2))
        sys.exit(1)

    print(json.dumps(payload, indent=2, default=str))

    if args.json_only:
        return

    # Human summary (to stderr so it doesn't pollute JSON capture)
    ma  = payload["ma_structure"]
    rsi = payload["rsi_14"]
    mcd = payload["macd"]
    sr  = payload["support_resistance"]
    h   = payload["signal_hints"]
    print(f"\n=== {payload['ticker']} technical snapshot ===", file=sys.stderr)
    print(f"  Price: ${payload['price']['current']}  ({payload['price']['change_pct']:+}%)", file=sys.stderr)
    print(f"  Stage: {ma['stage']}  |  MA 20/50/200: {ma['ma_20']}/{ma['ma_50']}/{ma['ma_200']}", file=sys.stderr)
    print(f"  RSI 14: {rsi['rsi_14']} ({rsi['zone']})  |  MACD hist: {mcd['histogram']} ({mcd['histogram_trend']})", file=sys.stderr)
    print(f"  Volume: {payload['volume']['ratio_20d']}x ({payload['volume']['spike_label']})  "
          f"trend={payload['volume']['volume_trend']}  state={payload['volume']['intraday_state']}", file=sys.stderr)
    print(f"  S: ${sr['nearest_support']} (-{sr['pct_to_support']}%)   "
          f"R: ${sr['nearest_resistance']} (+{sr['pct_to_resistance']}%)", file=sys.stderr)
    print(f"  Rubric hint: {h['rubric_hint']}   "
          f"[stage2_complete={h['stage_2_complete']} breakdown={h['bearish_breakdown']}]", file=sys.stderr)
    if payload["warnings"]:
        print(f"  ⚠ {', '.join(payload['warnings'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
