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

# V2.1 — module-level SPY history cache (avoids N×SPY fetch in screen.py).
# Cleared per-process; refreshed when first ticker analyzed.
_SPY_HIST_CACHE: dict = {"hist": None, "fetched_at": 0.0}
_SPY_TTL_SEC = 3600  # 1h — SPY only changes intraday; screen runs are bursty


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
        # V2.1 — invalidate caches missing leader-finder fields (NHP / RS / VCP / etc.)
        if payload.get("schema_version") != "v2.1":
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


# ── V2.1 new derives — leader-finder indicators ──────────────────────────
def _get_spy_hist():
    """Return SPY hist (1y), shared across all tickers in same process. Cached 1h."""
    import time
    now = time.time()
    if _SPY_HIST_CACHE["hist"] is not None and (now - _SPY_HIST_CACHE["fetched_at"]) < _SPY_TTL_SEC:
        return _SPY_HIST_CACHE["hist"]
    try:
        spy_hist, _ = fetch_history("SPY", period="1y")
        _SPY_HIST_CACHE["hist"] = spy_hist
        _SPY_HIST_CACHE["fetched_at"] = now
        return spy_hist
    except Exception as e:
        print(f"[momentum] SPY hist fetch failed: {e}", file=sys.stderr)
        return None


def _compute_nhp(hist):
    """52-week New-High Proximity. Returns dict {pct_from_52w_high, is_new_high}.

    pct_from_52w_high: (price - 52w_high) / 52w_high × 100; 0 = at high, -5 = 5% below.
    """
    try:
        if hist is None or len(hist) < 50:
            return {"pct_from_52w_high": None, "is_new_high": None, "weeks_since_high": None}
        # Use last 252 trading days (1y) of High; if shorter history use what exists
        window = min(252, len(hist))
        high_252 = float(hist["High"].iloc[-window:].max())
        price = float(hist["Close"].iloc[-1])
        pct = round((price - high_252) / high_252 * 100, 2) if high_252 else None
        is_new_high = bool(pct is not None and pct >= -0.5)  # within 0.5% counts
        # Weeks since the high
        try:
            high_idx = hist["High"].iloc[-window:].idxmax()
            days_ago = (hist.index[-1] - high_idx).days
            weeks_since_high = round(days_ago / 7, 1)
        except Exception:
            weeks_since_high = None
        return {
            "pct_from_52w_high": pct,
            "is_new_high":       is_new_high,
            "weeks_since_high":  weeks_since_high,
        }
    except Exception as e:
        return {"pct_from_52w_high": None, "is_new_high": None, "weeks_since_high": None,
                "error": str(e)}


def _compute_rs_vs_spy(ticker_hist):
    """Relative Strength vs SPY (3M + 6M return diff). Higher = ticker outperforming.

    Returns rs_3m_pct, rs_6m_pct (ticker_return - spy_return in %), rs_rating (0-99 rough).
    """
    try:
        spy_hist = _get_spy_hist()
        if spy_hist is None or ticker_hist is None or len(spy_hist) < 60 or len(ticker_hist) < 60:
            return {"rs_3m_pct": None, "rs_6m_pct": None, "rs_rating": None}

        def _ret(hist, days):
            if len(hist) < days + 1:
                return None
            try:
                p_now = float(hist["Close"].iloc[-1])
                p_then = float(hist["Close"].iloc[-days - 1])
                return (p_now - p_then) / p_then * 100 if p_then else None
            except Exception:
                return None

        t_3m = _ret(ticker_hist, 63)   # ~3 months trading days
        t_6m = _ret(ticker_hist, 126)
        s_3m = _ret(spy_hist, 63)
        s_6m = _ret(spy_hist, 126)

        rs_3m = round(t_3m - s_3m, 2) if (t_3m is not None and s_3m is not None) else None
        rs_6m = round(t_6m - s_6m, 2) if (t_6m is not None and s_6m is not None) else None

        # Rough RS rating: clamp rs_3m to 0-99 via piecewise scale
        # rs_3m -30 → 5 / -15 → 25 / 0 → 50 / +15 → 75 / +30 → 90 / +50+ → 99
        rs_rating = None
        if rs_3m is not None:
            if rs_3m >= 50:    rs_rating = 99
            elif rs_3m >= 30:  rs_rating = 90
            elif rs_3m >= 15:  rs_rating = 75
            elif rs_3m >= 5:   rs_rating = 60
            elif rs_3m >= -5:  rs_rating = 50
            elif rs_3m >= -15: rs_rating = 35
            elif rs_3m >= -30: rs_rating = 20
            else:              rs_rating = 5

        return {
            "rs_3m_pct": rs_3m,
            "rs_6m_pct": rs_6m,
            "rs_rating": rs_rating,
        }
    except Exception as e:
        return {"rs_3m_pct": None, "rs_6m_pct": None, "rs_rating": None, "error": str(e)}


def _compute_vcp_compression(hist):
    """Volatility Contraction Pattern (Minervini): 4w price range vs 12w range.

    compression_ratio = (4w_high - 4w_low) / (12w_high - 12w_low)
    < 0.55 = healthy contraction (setup); > 0.85 = no contraction
    """
    try:
        if hist is None or len(hist) < 60:
            return {"compression_ratio": None, "is_compressed": None,
                    "range_4w_pct": None, "range_12w_pct": None}
        # Use last 20 (4w) and 60 (12w) trading days
        last_20 = hist.iloc[-20:]
        last_60 = hist.iloc[-60:]
        h4, l4 = float(last_20["High"].max()), float(last_20["Low"].min())
        h12, l12 = float(last_60["High"].max()), float(last_60["Low"].min())
        range_4w = h4 - l4
        range_12w = h12 - l12
        ratio = round(range_4w / range_12w, 3) if range_12w > 0 else None
        # Express ranges as % of period midpoint for context
        mid_4w = (h4 + l4) / 2
        mid_12w = (h12 + l12) / 2
        return {
            "compression_ratio": ratio,
            "is_compressed":     bool(ratio is not None and ratio < 0.55),
            "range_4w_pct":      round(range_4w / mid_4w * 100, 2) if mid_4w else None,
            "range_12w_pct":     round(range_12w / mid_12w * 100, 2) if mid_12w else None,
        }
    except Exception as e:
        return {"compression_ratio": None, "is_compressed": None, "error": str(e)}


def _compute_dry_up_spike(hist):
    """Volume dry-up → spike pattern (accumulation followed by breakout).

    dry_up: 5D avg / 20D avg < 0.75 (recent volume below baseline)
    spike: today_volume / 20D avg > 1.5 (today expanded)
    pattern_active = dry_up AND spike (both required)
    """
    try:
        if hist is None or len(hist) < 25:
            return {"avg_5d_vs_20d": None, "today_vs_20d": None,
                    "dry_up": None, "spike": None, "pattern_active": None}
        # Exclude today from 5D-prev / 20D-prev to avoid look-ahead
        vol = hist["Volume"]
        avg_20d_prev = float(vol.iloc[-21:-1].mean())  # 20 days excluding today
        avg_5d_prev  = float(vol.iloc[-6:-1].mean())   # 5 days excluding today
        today_vol    = float(vol.iloc[-1])

        if avg_20d_prev <= 0:
            return {"avg_5d_vs_20d": None, "today_vs_20d": None,
                    "dry_up": None, "spike": None, "pattern_active": None}

        ratio_5_20 = round(avg_5d_prev / avg_20d_prev, 2)
        today_ratio = round(today_vol / avg_20d_prev, 2)
        dry_up = bool(ratio_5_20 < 0.75)
        spike  = bool(today_ratio > 1.5)
        return {
            "avg_5d_vs_20d":  ratio_5_20,
            "today_vs_20d":   today_ratio,
            "dry_up":         dry_up,
            "spike":          spike,
            "pattern_active": dry_up and spike,
        }
    except Exception as e:
        return {"avg_5d_vs_20d": None, "today_vs_20d": None, "dry_up": None,
                "spike": None, "pattern_active": None, "error": str(e)}


def _compute_eps_acceleration(ticker):
    """Read earnings-analyst cache (opt-in, 0 cost on cache miss).

    Returns latest_yoy_pct, growth_acceleration ∈ {accelerating|steady|decelerating|None}.
    """
    import glob
    out = {"latest_q_yoy_pct": None, "growth_acceleration": None,
           "cache_used": False, "cache_age_days": None}
    try:
        cache_dir = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..",
                                                  "earnings-analyst", "cache"))
        pattern = os.path.join(cache_dir, f"{ticker.upper()}_*.json")
        files = sorted(glob.glob(pattern))
        if not files:
            return out
        latest = files[-1]
        age_days = (datetime.now().timestamp() - os.path.getmtime(latest)) / 86400
        if age_days > 90:
            return out
        with open(latest, "r") as fp:
            ea = json.load(fp)
        derived = ea.get("derived") or {}
        yoy = derived.get("yoy_growth") or {}
        out["latest_q_yoy_pct"] = (
            round(yoy["earnings_yoy"] * 100, 1) if yoy.get("earnings_yoy") is not None else None
        )
        out["growth_acceleration"] = yoy.get("growth_acceleration")
        out["cache_used"] = True
        out["cache_age_days"] = round(age_days, 1)
    except Exception as e:
        out["error"] = str(e)
    return out


def _compute_days_to_cover(short_int):
    """Days-to-cover (already in short_int as short_ratio_days_to_cover).

    Returns dtc + tier classification:
      - none: <1
      - low:  1-3
      - moderate: 3-5
      - elevated: 5-10 (squeeze candidate when MA confirms)
      - high: 10+ (rare, risky)
    """
    dtc = short_int.get("short_ratio_days_to_cover")
    if dtc is None:
        return {"days_to_cover": None, "tier": "unknown"}
    if dtc < 1:    tier = "none"
    elif dtc < 3:  tier = "low"
    elif dtc < 5:  tier = "moderate"
    elif dtc < 10: tier = "elevated"
    else:          tier = "high"
    return {"days_to_cover": dtc, "tier": tier}


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

    # V2.1 leader-finder indicators
    nhp           = _compute_nhp(hist)
    rs            = _compute_rs_vs_spy(hist)
    vcp           = _compute_vcp_compression(hist)
    vol_pattern   = _compute_dry_up_spike(hist)
    eps_accel     = _compute_eps_acceleration(ticker)
    dtc           = _compute_days_to_cover(short_int)

    # Promote new patterns to signals (so they appear in --signal filter)
    if nhp.get("is_new_high"):
        signals.append("at_52w_new_high")
    elif nhp.get("pct_from_52w_high") is not None and nhp["pct_from_52w_high"] >= -5:
        signals.append("near_52w_high")
    if rs.get("rs_3m_pct") is not None and rs["rs_3m_pct"] >= 15:
        signals.append("rs_leader_3m")
    if vcp.get("is_compressed"):
        signals.append("vcp_compressed")
    if vol_pattern.get("pattern_active"):
        signals.append("vol_dryup_spike")
    if eps_accel.get("growth_acceleration") == "accelerating":
        signals.append("eps_accelerating")
    if dtc.get("tier") in ("elevated", "high") and (ma.get("above_ma50_pct") or 0) > 0:
        signals.append("dtc_squeeze_candidate")

    return {
        "ticker":           ticker.upper(),
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "schema_version":   "v2.1",   # bumped: includes new derive fields
        "price":            price,
        "cache_hit":        False,
        "cache_age_sec":    0,
        "volume":           volume,
        "ma_structure":     ma,
        "short_interest":   short_int,
        "rsi":              rsi,
        "macd":             macd,
        # V2.1 — leader-finder fields
        "nhp":                 nhp,
        "rs_vs_spy":           rs,
        "vcp":                 vcp,
        "volume_pattern":      vol_pattern,
        "eps_acceleration":    eps_accel,
        "days_to_cover":       dtc,
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
