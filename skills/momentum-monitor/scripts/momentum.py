#!/usr/bin/env python3
"""
momentum-monitor — per-stock volume & MA flow read.

Reports volume dynamics (today vs 20/50D avg, spike detection), MA structure
(Weinstein stage + cross events), short interest (% float, days-to-cover,
squeeze potential), and a composite momentum score 0-100.

Pure-computation primitives (MA structure, RSI, volume profile, stage
classification, cross detection) live in `technical_core.py` — this file
owns momentum-monitor-specific layers: short interest, composite scoring,
signals/warnings, caching, CLI.

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

# Pure computation primitives — shared with technical-analyst skill.
from technical_core import (
    fetch_history,
    volume_profile,
    ma_structure,
    classify_stage,
    detect_crosses,
    rsi_14,
    rsi_state,
    intraday_state,
    compute_macd,
)

# Backward-compat aliases — some existing callers may import the old
# underscore-prefixed names. Keep them working by re-exporting the public
# names here.
_fetch_history   = fetch_history
_volume_block    = volume_profile
_ma_block        = ma_structure
_classify_stage  = classify_stage
_detect_crosses  = detect_crosses
_rsi_14          = rsi_14
_rsi_block       = rsi_state
_intraday_state  = intraday_state

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
        # Invalidate old cache entries that pre-date MACD field (treat as stale)
        if "macd" not in payload:
            return None
        # Re-derive MACD signals from cached macd data if signals were generated
        # before MACD signal detection was added (cheap: no network call needed).
        macd = payload.get("macd") or {}
        sigs = set(payload.get("signals", []))
        warns = set(payload.get("warnings", []))
        changed = False
        if macd.get("bullish_cross") and "macd_bullish_cross" not in sigs:
            sigs.add("macd_bullish_cross"); changed = True
        if macd.get("bearish_cross") and "macd_bearish_cross" not in warns:
            warns.add("macd_bearish_cross"); changed = True
        if macd.get("histogram_trend") == "rising" and "macd_histogram_rising" not in sigs:
            sigs.add("macd_histogram_rising"); changed = True
        if changed:
            payload["signals"]  = list(sigs)
            payload["warnings"] = list(warns)
            _write_cache(ticker, {**payload, "cache_hit": False, "cache_age_sec": 0})
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


# ── Momentum-specific layers ────────────────────────────────────────────
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
    # 1. volume_flow — neutral (55) when too early to read intraday
    r = volume["ratio_20d"]
    if r is None:  vol_score = 55
    elif r >= 2.0: vol_score = 95
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
    if pct is None:                          sq_score = 40
    elif pct >= 20 and am20 > 5:             sq_score = 90
    elif pct >= 20:                          sq_score = 60
    elif pct >= 10:                          sq_score = 55
    elif pct >= 3:                           sq_score = 40
    else:                                    sq_score = 20

    # 4. trend_acceleration — fresh golden cross bonus + above-ma200 health
    am200 = ma["above_ma200_pct"] or 0
    has_fresh_golden_50_200 = any(c["type"] == "golden_cross_50_200" and c["days_ago"] <= 10 for c in ma["recent_crosses"])
    has_fresh_golden_20_50  = any(c["type"] == "golden_cross_20_50"  and c["days_ago"] <= 10 for c in ma["recent_crosses"])
    has_fresh_death         = any(c["type"].startswith("death_cross") and c["days_ago"] <= 10 for c in ma["recent_crosses"])

    if has_fresh_golden_50_200:  ta_score = 95
    elif has_fresh_golden_20_50: ta_score = 80
    elif has_fresh_death:        ta_score = 15
    elif 20 <= am200 <= 50:      ta_score = 75
    elif 0 < am200 < 20:         ta_score = 60
    elif am200 > 100:            ta_score = 30   # parabolic exhaustion
    elif am200 > 50:             ta_score = 50
    else:                        ta_score = 35

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


def _signals_and_warnings(volume, ma, short_int, comp, rsi=None, macd=None):
    signals, warnings = [], []
    if rsi and rsi.get("rsi_14") is not None:
        v = rsi["rsi_14"]
        if v > 70:
            warnings.append("overbought_rsi")
        elif v < 30 and ma.get("stage") == "Stage 2 uptrend":
            # Oversold is a buy signal only while the trend is still up.
            signals.append("oversold_rsi")
    if ma["stage"] == "Stage 2 uptrend":
        signals.append("stage2_uptrend_intact")
    if ma["stage"] == "Stage 4 downtrend":
        warnings.append("stage4_downtrend")
    # Volume-based signals suppressed when intraday reading is too_early (<30 min).
    if volume["intraday_state"] != "too_early":
        r20 = volume["ratio_20d"]
        if r20 is not None and r20 >= 1.3 and volume["volume_trend"] == "expanding":
            signals.append("volume_expansion")
        if r20 is not None and r20 < 0.7:
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
    # MACD-based signals
    if macd:
        if macd.get("bullish_cross"):
            signals.append("macd_bullish_cross")
        if macd.get("bearish_cross"):
            warnings.append("macd_bearish_cross")
        if macd.get("histogram_trend") == "rising":
            signals.append("macd_histogram_rising")
    return signals, warnings


# ── Main ────────────────────────────────────────────────────────────────
def analyze(ticker):
    hist, t = fetch_history(ticker)
    price = round(float(hist["Close"].iloc[-1]), 2)
    volume    = volume_profile(hist)
    ma        = ma_structure(hist)
    short_int = _short_interest_block(t)
    rsi       = rsi_state(hist)
    macd      = compute_macd(hist["Close"])
    comp      = _composite(volume, ma, short_int)
    signals, warnings = _signals_and_warnings(volume, ma, short_int, comp, rsi, macd)

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
        "macd":             macd,
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
