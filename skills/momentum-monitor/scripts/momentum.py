#!/usr/bin/env python3
"""
momentum-monitor — per-stock volume & MA flow read.

Reports volume dynamics (today vs 20/50D avg, spike detection), MA structure
(Weinstein stage + cross events), short interest (% float, days-to-cover,
squeeze potential), and a composite momentum score 0-100.

Usage:
    python3 momentum.py TSLA
    python3 momentum.py TSLA --json-only
    python3 momentum.py TSLA --no-cache
    python3 momentum.py TSLA --max-age 300
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

SCRIPT_DIR      = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR       = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "cache"))
DEFAULT_TTL_SEC = 900


# ── Cache helpers ────────────────────────────────────────────────────────
def _cache_path(ticker):
    return os.path.join(CACHE_DIR, f"momentum_{ticker.upper()}.json")


def _load_cache(ticker, max_age_sec):
    path = _cache_path(ticker)
    if not os.path.exists(path):
        return None
    try:
        age_sec = int(datetime.now().timestamp() - os.path.getmtime(path))
        if age_sec >= max_age_sec:
            return None
        with open(path, "r", encoding="utf-8") as fp:
            payload = json.load(fp)
        for k in ("cache_hit", "cache_age_sec"):
            payload.pop(k, None)
        payload["cache_hit"]     = True
        payload["cache_age_sec"] = age_sec
        return payload
    except Exception:
        return None


def _write_cache(ticker, payload):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(_cache_path(ticker), "w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[momentum] cache write failed: {e}", file=sys.stderr)


# ── Core analysis ────────────────────────────────────────────────────────
def _fetch_history(ticker, period="1y"):
    t = yf.Ticker(ticker)
    hist = t.history(period=period, auto_adjust=True)
    if hist is None or hist.empty:
        raise RuntimeError(f"no history data for {ticker}")
    return hist, t


def _volume_block(hist):
    close  = hist["Close"]
    volume = hist["Volume"]
    today_v = float(volume.iloc[-1])
    # Average over the 20/50 sessions BEFORE today (exclude today itself) —
    # otherwise a spike inflates its own denominator and understates the ratio.
    def _avg_prev(n):
        if len(volume) < 2:
            return 0.0
        prior = volume.iloc[-min(n + 1, len(volume)):-1]
        if len(prior) == 0:
            return 0.0
        m = float(prior.mean())
        return 0.0 if m != m else m   # NaN → 0
    avg_20 = _avg_prev(20)
    avg_50 = _avg_prev(50)
    ratio   = today_v / avg_20 if avg_20 > 0 else 0.0

    if ratio >= 3.0:
        spike = "HEAVY_SPIKE"
    elif ratio >= 2.0:
        spike = "MILD_SPIKE"
    else:
        spike = "NORMAL"

    # Count days in last 10 sessions where volume >= 2x avg_20
    last10_vol = volume.tail(10)
    last10_avg = avg_20 if avg_20 > 0 else 1
    spike_days = int((last10_vol / last10_avg >= 2.0).sum())

    # Simple volume trend: 5-day avg vs 10-day avg
    v5   = float(volume.tail(5).mean())
    v10  = float(volume.tail(10).mean())
    if v10 == 0:
        trend = "stable"
    elif v5 / v10 >= 1.15:
        trend = "expanding"
    elif v5 / v10 <= 0.85:
        trend = "contracting"
    else:
        trend = "stable"

    return {
        "today":        int(today_v),
        "avg_20d":      int(avg_20),
        "avg_50d":      int(avg_50),
        "ratio_20d":    round(ratio, 2),
        "spike_label":  spike,
        "spike_days_last_10": spike_days,
        "volume_trend": trend,
    }


def _detect_crosses(hist, window=30):
    """Scan last `window` sessions for MA cross events."""
    close = hist["Close"]
    ma20  = close.rolling(20).mean()
    ma50  = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()

    crosses = []
    today_idx = len(close) - 1
    start_idx = max(200, today_idx - window)

    for i in range(start_idx + 1, today_idx + 1):
        # 20 vs 50
        if pd.notna(ma20.iloc[i-1]) and pd.notna(ma50.iloc[i-1]):
            prev_diff = ma20.iloc[i-1] - ma50.iloc[i-1]
            curr_diff = ma20.iloc[i]   - ma50.iloc[i]
            if prev_diff <= 0 and curr_diff > 0:
                crosses.append({
                    "type": "golden_cross_20_50",
                    "date": str(close.index[i].date()),
                    "days_ago": today_idx - i,
                })
            elif prev_diff >= 0 and curr_diff < 0:
                crosses.append({
                    "type": "death_cross_20_50",
                    "date": str(close.index[i].date()),
                    "days_ago": today_idx - i,
                })
        # 50 vs 200
        if pd.notna(ma50.iloc[i-1]) and pd.notna(ma200.iloc[i-1]):
            prev_diff = ma50.iloc[i-1] - ma200.iloc[i-1]
            curr_diff = ma50.iloc[i]   - ma200.iloc[i]
            if prev_diff <= 0 and curr_diff > 0:
                crosses.append({
                    "type": "golden_cross_50_200",
                    "date": str(close.index[i].date()),
                    "days_ago": today_idx - i,
                })
            elif prev_diff >= 0 and curr_diff < 0:
                crosses.append({
                    "type": "death_cross_50_200",
                    "date": str(close.index[i].date()),
                    "days_ago": today_idx - i,
                })
    return crosses


def _classify_stage(price, ma20, ma50, ma200):
    if any(pd.isna(x) for x in (ma20, ma50, ma200)):
        return "unknown"
    if ma20 > ma50 > ma200 and price > ma20:
        return "Stage 2 uptrend"
    if ma20 < ma50 < ma200 and price < ma20:
        return "Stage 4 downtrend"
    # Stage 3 top: price below 20MA but 50 still above 200
    if ma50 > ma200 and price < ma20 and ma20 < ma50:
        return "Stage 3 top"
    # Stage 1 basing: flat around rising 200
    return "Stage 1 basing"


def _ma_block(hist):
    close = hist["Close"]
    price = float(close.iloc[-1])
    # NaN when history shorter than the rolling window (e.g. new listings).
    # bool(NaN) is truthy in Python, so we must filter NaN explicitly before any math.
    def _clean(v):
        fv = float(v)
        return None if fv != fv else fv   # NaN != NaN is the classic NaN test
    ma20  = _clean(close.rolling(20).mean().iloc[-1])
    ma50  = _clean(close.rolling(50).mean().iloc[-1])
    ma200 = _clean(close.rolling(200).mean().iloc[-1])

    stage = _classify_stage(price, ma20, ma50, ma200)
    above_20  = (price / ma20  - 1) * 100 if ma20  else None
    above_50  = (price / ma50  - 1) * 100 if ma50  else None
    above_200 = (price / ma200 - 1) * 100 if ma200 else None

    return {
        "ma_20":           round(ma20, 2)  if ma20  is not None else None,
        "ma_50":           round(ma50, 2)  if ma50  is not None else None,
        "ma_200":          round(ma200, 2) if ma200 is not None else None,
        "stage":           stage,
        "above_ma20_pct":  round(above_20, 2)  if above_20  is not None else None,
        "above_ma50_pct":  round(above_50, 2)  if above_50  is not None else None,
        "above_ma200_pct": round(above_200, 2) if above_200 is not None else None,
        "recent_crosses":  _detect_crosses(hist),
    }


def _rsi_14(close, period=14):
    """Classic Wilder RSI: first avg is SMA, subsequent use Wilder EMA."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _rsi_block(hist):
    rsi = _rsi_14(hist["Close"])
    latest = rsi.iloc[-1]
    if pd.isna(latest):
        return {"rsi_14": None, "zone": "unknown"}
    v = float(latest)
    if v >= 70:   zone = "overbought"
    elif v >= 50: zone = "bullish"
    elif v >= 30: zone = "neutral"
    else:         zone = "oversold"
    return {"rsi_14": round(v, 1), "zone": zone}


def _short_interest_block(t):
    """Pull short interest from yfinance `info` dict. Fields can be None."""
    try:
        info = t.info or {}
    except Exception:
        info = {}
    shares_short       = info.get("sharesShort")
    short_ratio        = info.get("shortRatio")           # days to cover
    short_pct_float    = info.get("shortPercentOfFloat")  # 0.0-1.0 fraction
    short_last_date    = info.get("dateShortInterest")     # epoch

    pct = short_pct_float * 100 if short_pct_float else None
    last = None
    if short_last_date:
        try:
            last = datetime.fromtimestamp(short_last_date).strftime("%Y-%m-%d")
        except Exception:
            pass

    # Interpretation
    if pct is None:
        interp = "unknown"
    elif pct < 3:
        interp = "low"
    elif pct < 10:
        interp = "moderate"
    elif pct < 20:
        interp = "high"
    else:
        interp = "very_high"

    return {
        "shares_short":             int(shares_short) if shares_short else None,
        "short_pct_float":          round(pct, 2) if pct is not None else None,
        "short_ratio_days_to_cover": round(float(short_ratio), 2) if short_ratio else None,
        "last_updated":             last,
        "interpretation":           interp,
    }


def _composite(volume, ma, short_int):
    """Compute 0-100 composite score + label."""
    # 1. volume_flow
    r = volume["ratio_20d"]
    if r >= 2.0:   vol_score = 95
    elif r >= 1.5: vol_score = 80
    elif r >= 1.2: vol_score = 65
    elif r >= 1.0: vol_score = 55
    elif r >= 0.7: vol_score = 40
    else:          vol_score = 25

    # 2. ma_stage
    stage = ma["stage"]
    if   stage == "Stage 2 uptrend":   ma_score = 95
    elif stage == "Stage 1 basing":    ma_score = 65
    elif stage == "Stage 3 top":       ma_score = 40
    elif stage == "Stage 4 downtrend": ma_score = 10
    else:                              ma_score = 50

    # 3. short_squeeze_potential — high short + above-ma20 momentum = fuel
    pct = short_int["short_pct_float"]
    am20 = ma["above_ma20_pct"] or 0
    if pct is None:
        sq_score = 40
    elif pct >= 20 and am20 > 5:
        sq_score = 90
    elif pct >= 20:
        sq_score = 60
    elif pct >= 10:
        sq_score = 55
    elif pct >= 3:
        sq_score = 40
    else:
        sq_score = 20

    # 4. trend_acceleration — fresh golden cross bonus + above-ma200 health
    am200 = ma["above_ma200_pct"] or 0
    has_fresh_golden_50_200 = any(
        c["type"] == "golden_cross_50_200" and c["days_ago"] <= 10
        for c in ma["recent_crosses"]
    )
    has_fresh_golden_20_50 = any(
        c["type"] == "golden_cross_20_50" and c["days_ago"] <= 10
        for c in ma["recent_crosses"]
    )
    has_fresh_death = any(
        c["type"].startswith("death_cross") and c["days_ago"] <= 10
        for c in ma["recent_crosses"]
    )
    if has_fresh_golden_50_200:
        ta_score = 95
    elif has_fresh_golden_20_50:
        ta_score = 80
    elif has_fresh_death:
        ta_score = 15
    elif 20 <= am200 <= 50:
        ta_score = 75
    elif 0 < am200 < 20:
        ta_score = 60
    elif am200 > 100:
        ta_score = 30   # parabolic exhaustion
    elif am200 > 50:
        ta_score = 50
    else:
        ta_score = 35

    composite = round((vol_score + ma_score + sq_score + ta_score) / 4, 1)
    if   composite >= 80: label = "STRONGLY_BULLISH"
    elif composite >= 65: label = "BULLISH"
    elif composite >= 45: label = "NEUTRAL"
    elif composite >= 30: label = "WEAK"
    else:                 label = "BEARISH"

    return {
        "score": composite,
        "label": label,
        "components": {
            "volume_flow":             vol_score,
            "ma_stage":                ma_score,
            "short_squeeze_potential": sq_score,
            "trend_acceleration":      ta_score,
        },
    }


def _signals_and_warnings(volume, ma, short_int, comp, rsi=None):
    signals, warnings = [], []
    if rsi and rsi.get("rsi_14") is not None:
        v = rsi["rsi_14"]
        if v > 70:
            warnings.append("overbought_rsi")
        elif v < 30 and ma.get("stage") == "Stage 2 uptrend":
            # Only flag oversold as a buy signal if the trend is still up
            # (oversold in a downtrend is weakness, not opportunity)
            signals.append("oversold_rsi")
    if ma["stage"] == "Stage 2 uptrend":
        signals.append("stage2_uptrend_intact")
    if ma["stage"] == "Stage 4 downtrend":
        warnings.append("stage4_downtrend")
    if volume["ratio_20d"] >= 1.3 and volume["volume_trend"] == "expanding":
        signals.append("volume_expansion")
    if volume["ratio_20d"] < 0.7:
        warnings.append("volume_dry_up")
    if volume["spike_label"] == "HEAVY_SPIKE":
        signals.append("heavy_volume_spike_today")
    pct = short_int["short_pct_float"]
    if pct is not None:
        if pct < 3:    signals.append("low_short_interest")
        elif pct > 10: signals.append("high_short_interest")
        if pct > 20 and (ma["above_ma20_pct"] or 0) > 5:
            signals.append("squeeze_candidate")
    am200 = ma["above_ma200_pct"] or 0
    if am200 > 50:
        warnings.append("parabolic_blowoff_risk")
    for c in ma["recent_crosses"]:
        if c["days_ago"] <= 10:
            if c["type"] == "golden_cross_20_50":  signals.append("fresh_golden_cross_20_50")
            if c["type"] == "golden_cross_50_200": signals.append("fresh_golden_cross_50_200")
            if c["type"] == "death_cross_20_50":   warnings.append("fresh_death_cross_20_50")
            if c["type"] == "death_cross_50_200":  warnings.append("fresh_death_cross_50_200")
    return signals, warnings


# ── Main ────────────────────────────────────────────────────────────────
def analyze(ticker):
    hist, t = _fetch_history(ticker)
    price = round(float(hist["Close"].iloc[-1]), 2)
    volume    = _volume_block(hist)
    ma        = _ma_block(hist)
    short_int = _short_interest_block(t)
    rsi       = _rsi_block(hist)
    comp      = _composite(volume, ma, short_int)
    signals, warnings = _signals_and_warnings(volume, ma, short_int, comp, rsi)

    return {
        "ticker":           ticker.upper(),
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "price":            price,
        "cache_hit":        False,
        "cache_age_sec":    0,
        "volume":           volume,
        "ma_structure":     ma,
        "short_interest":   short_int,
        "rsi":              rsi,
        "momentum_composite": comp,
        "signals":          signals,
        "warnings":         warnings,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker", help="Stock ticker (e.g. TSLA, AMD)")
    ap.add_argument("--json-only", action="store_true")
    ap.add_argument("--no-cache",  action="store_true", help="bypass cache, always fetch fresh")
    ap.add_argument("--max-age",   type=int, default=DEFAULT_TTL_SEC,
                    help=f"cache TTL in seconds (default {DEFAULT_TTL_SEC})")
    args = ap.parse_args()

    ticker = args.ticker.strip().upper()

    # Cache check
    if not args.no_cache:
        cached = _load_cache(ticker, args.max_age)
        if cached is not None:
            print(json.dumps(cached, ensure_ascii=False, indent=2))
            if not args.json_only:
                c = cached["momentum_composite"]
                v = cached["volume"]
                print(f"\n→ cache hit ({cached['cache_age_sec']}s) │ {ticker} ${cached['price']} │ "
                      f"{c['label']} {c['score']}/100 │ vol {v['ratio_20d']}x {v['spike_label']}",
                      file=sys.stderr)
            return

    try:
        out = analyze(ticker)
    except Exception as e:
        err = {"ticker": ticker, "error": str(e), "skill_execution_failed": True}
        print(json.dumps(err, ensure_ascii=False, indent=2))
        sys.exit(1)

    _write_cache(ticker, out)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not args.json_only:
        c = out["momentum_composite"]
        v = out["volume"]
        ma = out["ma_structure"]
        print(
            f"\n→ fresh │ {ticker} ${out['price']} │ {c['label']} {c['score']}/100 │ "
            f"vol {v['ratio_20d']}x {v['spike_label']} │ {ma['stage']} │ "
            f"signals: {','.join(out['signals']) or '-'}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
