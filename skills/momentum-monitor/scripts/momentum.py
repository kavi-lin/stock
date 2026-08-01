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
    parabolic_severity_tag,
)

# V3.22 — fundamentals layer (P/S TTM, GM%, Rev YoY TTM). Pulled from the
# shared FMP cache so a screen.py run shares quarterly-income hits with any
# other consumer (earnings-analyst, etc.). Import is guarded because the
# shared module hard-exits when FMP_API_KEY is missing; without it we still
# want momentum.py to run with fundamentals fields = None.
try:
    _REPO_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
    )
    if _REPO_ROOT not in sys.path:
        sys.path.insert(0, _REPO_ROOT)
    if os.environ.get("FMP_API_KEY"):
        from skills._shared.company_context import (  # noqa: E402
            get_quarterly_income,
            get_profile,
        )
        _FUNDAMENTALS_AVAILABLE = True
    else:
        get_quarterly_income = None  # type: ignore[assignment]
        get_profile = None  # type: ignore[assignment]
        _FUNDAMENTALS_AVAILABLE = False
except Exception as _exc:  # pragma: no cover - defensive import guard
    print(f"[momentum] fundamentals layer disabled: {_exc}", file=sys.stderr)
    get_quarterly_income = None  # type: ignore[assignment]
    get_profile = None  # type: ignore[assignment]
    _FUNDAMENTALS_AVAILABLE = False

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
        # V3.25.8 — invalidate caches predating the 3D volume window block.
        # Old v2.2 payloads are missing avg_3d_vs_20d / vol_3d_state, which
        # would render as "—" forever on the Dashboard; force a refresh.
        if payload.get("schema_version") != "v2.3":
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
# 24h sidecar for the .info fields we use — short interest updates biweekly
# and marketCap drifts slowly, so the daily 529-ticker screen doesn't need
# 529 Yahoo quoteSummary calls (the slowest network op of the run).
_INFO_SIDECAR_DIR = os.path.join(CACHE_DIR, "yf_info")
_INFO_TTL_SEC = 24 * 3600
_INFO_FIELDS = ("sharesShort", "shortRatio", "shortPercentOfFloat",
                "dateShortInterest", "marketCap")


def _get_info_cached(ticker, t):
    import time as _time
    path = os.path.join(_INFO_SIDECAR_DIR, f"{str(ticker).upper()}.json")
    try:
        if os.path.exists(path) and _time.time() - os.path.getmtime(path) < _INFO_TTL_SEC:
            with open(path, encoding="utf-8") as fp:
                return json.load(fp)
    except Exception:
        pass
    try:
        info = t.info or {}
    except Exception:
        info = {}
    slim = {k: info.get(k) for k in _INFO_FIELDS}
    try:
        os.makedirs(_INFO_SIDECAR_DIR, exist_ok=True)
        tmp = f"{path}.tmp{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as fp:
            json.dump(slim, fp)
        os.replace(tmp, path)
    except Exception:
        pass
    return slim


def _short_interest_block(info):
    """Short interest from the cached yfinance `info` slim dict."""
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


def _market_cap(info):
    """V3.17 (Wave 1) — marketCap from the cached yfinance info slim dict.
    Returns None on any failure (rate-limit, missing field). Consumed by
    _signals_and_warnings to assign extension severity tag."""
    mc = info.get("marketCap")
    try:
        return float(mc) if mc else None
    except (TypeError, ValueError):
        return None


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

    V3.25.8 — also emits a 3D window for the Dashboard's at-a-glance
    contraction / expansion read:
      avg_3d_vs_20d : (last 3 bars excl. today) / (last 20 bars excl. today)
      vol_3d_state  : "expanding" (≥1.3) | "drying_up" (≤0.75) | "neutral"
    Thresholds mirror existing dry-up cutoff + `volume_expansion` signal.
    """
    # Single empty-state template — keeps every early-return aligned and
    # ensures new keys never go missing in degenerate paths.
    empty = {
        "avg_5d_vs_20d": None, "today_vs_20d": None,
        "dry_up": None, "spike": None, "pattern_active": None,
        "avg_3d_vs_20d": None, "vol_3d_state": None,
    }
    try:
        if hist is None or len(hist) < 25:
            return dict(empty)
        # Exclude today from 3D/5D-prev / 20D-prev to avoid look-ahead
        vol = hist["Volume"]
        avg_20d_prev = float(vol.iloc[-21:-1].mean())  # 20 days excluding today
        avg_5d_prev  = float(vol.iloc[-6:-1].mean())   # 5 days excluding today
        avg_3d_prev  = float(vol.iloc[-4:-1].mean())   # 3 days excluding today
        today_vol    = float(vol.iloc[-1])

        if avg_20d_prev <= 0:
            return dict(empty)

        ratio_5_20  = round(avg_5d_prev  / avg_20d_prev, 2)
        ratio_3_20  = round(avg_3d_prev  / avg_20d_prev, 2)
        today_ratio = round(today_vol    / avg_20d_prev, 2)
        dry_up = bool(ratio_5_20 < 0.75)
        spike  = bool(today_ratio > 1.5)

        if   ratio_3_20 >= 1.3:  state_3d = "expanding"
        elif ratio_3_20 <= 0.75: state_3d = "drying_up"
        else:                    state_3d = "neutral"

        return {
            "avg_5d_vs_20d":  ratio_5_20,
            "today_vs_20d":   today_ratio,
            "dry_up":         dry_up,
            "spike":          spike,
            "pattern_active": dry_up and spike,
            "avg_3d_vs_20d":  ratio_3_20,
            "vol_3d_state":   state_3d,
        }
    except Exception as e:
        out = dict(empty)
        out["error"] = str(e)
        return out


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


def _compute_short_term_returns(hist):
    """V3.22 — pure-price short-horizon momentum (1D / 5D % return).

    Complements the existing RS-vs-SPY block which is 3M/6M. Useful for the
    Catalyst / breakout playbooks where a 5-day price thrust matters more
    than a 6-month relative-strength reading. Returns None when history is
    too short rather than zero (zero is a real reading — "flat").
    """
    out = {"return_1d_pct": None, "return_5d_pct": None}
    try:
        if hist is None or len(hist) < 6:
            return out
        close = hist["Close"]
        last = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        prev5 = float(close.iloc[-6])
        if prev > 0:
            out["return_1d_pct"] = round((last - prev) / prev * 100, 2)
        if prev5 > 0:
            out["return_5d_pct"] = round((last - prev5) / prev5 * 100, 2)
    except Exception as e:
        out["error"] = str(e)
    return out


def _compute_fundamentals(ticker, market_cap):
    """V3.22 — P/S TTM, GM% TTM, Revenue YoY TTM.

    All three derived from `get_quarterly_income(ticker, n=8)` (8 quarters →
    TTM = sum of latest 4, prior TTM = sum of quarters 5-8). P/S needs
    market cap from yfinance — falls back to FMP profile if yfinance returned
    None. Any missing input collapses that field to None; the function never
    raises. Behaviour when FMP_API_KEY is unset: all fields None (graceful).
    """
    out = {
        "ps_ttm":            None,
        "gm_ttm_pct":        None,
        "rev_yoy_ttm_pct":   None,
        "ttm_revenue_usd":   None,
        "data_lag_days":     None,
    }
    if not _FUNDAMENTALS_AVAILABLE or get_quarterly_income is None:
        return out
    try:
        rows = get_quarterly_income(ticker, n=8) or []
    except Exception as e:
        out["error"] = str(e)
        return out
    if len(rows) < 4:
        # Need at least the latest 4 quarters for TTM revenue; YoY needs 8.
        return out

    def _sum(field, slc):
        total = 0.0
        for r in rows[slc]:
            v = r.get(field)
            try:
                total += float(v) if v is not None else 0.0
            except (TypeError, ValueError):
                return None
        return total

    # Newest first — slice [0:4] = latest TTM, [4:8] = prior TTM.
    ttm_rev = _sum("revenue", slice(0, 4))
    ttm_gp  = _sum("grossProfit", slice(0, 4))

    if ttm_rev and ttm_rev > 0:
        out["ttm_revenue_usd"] = round(ttm_rev, 0)
        # Resolve market cap: prefer yfinance value already pulled by analyze();
        # fall back to FMP profile to avoid losing P/S when yfinance returns None.
        mc = market_cap
        if mc is None and get_profile is not None:
            try:
                prof = get_profile(ticker) or {}
                mc_raw = prof.get("marketCap") or prof.get("mktCap")
                mc = float(mc_raw) if mc_raw else None
            except Exception:
                mc = None
        if mc and mc > 0:
            out["ps_ttm"] = round(mc / ttm_rev, 2)
        if ttm_gp is not None:
            out["gm_ttm_pct"] = round(ttm_gp / ttm_rev * 100, 2)

    # Revenue YoY TTM only when we have 8 full quarters.
    if len(rows) >= 8:
        prior_ttm_rev = _sum("revenue", slice(4, 8))
        if prior_ttm_rev and prior_ttm_rev > 0 and ttm_rev:
            out["rev_yoy_ttm_pct"] = round(
                (ttm_rev - prior_ttm_rev) / prior_ttm_rev * 100, 2
            )

    # Lag indicator — days since the most-recent quarter's `date` field.
    latest_date = rows[0].get("date") or rows[0].get("fillingDate") or rows[0].get("acceptedDate")
    if latest_date:
        try:
            dt = datetime.strptime(latest_date[:10], "%Y-%m-%d")
            out["data_lag_days"] = max(0, (datetime.utcnow() - dt).days)
        except Exception:
            pass

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


def _signals_and_warnings(volume, ma, short_int, comp, rsi=None, macd=None,
                          market_cap=None):
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
    # V3.17 (Wave 1, Codex v5) — market-cap aware severity tag.
    # `market_cap` is injected into the local namespace by analyze() prior to
    # this call (see momentum.py:analyze). Tag is additive — parabolic_blowoff_risk
    # remains the base flag, severity is the secondary classifier.
    # V4.72.0 (P2-9): 判定移至 _shared/technical_core.parabolic_severity_tag 單一源
    # （technical-analyst 同步使用，修 protocol Technical lane 引用斷鏈）。
    severity = parabolic_severity_tag(am200, market_cap)
    if severity:
        warnings.append(severity)
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
    info_slim = _get_info_cached(ticker, t)
    short_int = _short_interest_block(info_slim)
    market_cap = _market_cap(info_slim)
    rsi       = rsi_state(hist)
    macd      = compute_macd(hist["Close"])
    comp      = _composite(volume, ma, short_int)
    signals, warnings = _signals_and_warnings(volume, ma, short_int, comp, rsi, macd,
                                              market_cap=market_cap)

    # V2.1 leader-finder indicators
    nhp           = _compute_nhp(hist)
    rs            = _compute_rs_vs_spy(hist)
    vcp           = _compute_vcp_compression(hist)
    vol_pattern   = _compute_dry_up_spike(hist)
    eps_accel     = _compute_eps_acceleration(ticker)
    dtc           = _compute_days_to_cover(short_int)

    # V3.22 — short-term price thrust + fundamentals layer (P/S / GM% / Rev YoY)
    short_returns = _compute_short_term_returns(hist)
    fundamentals  = _compute_fundamentals(ticker, market_cap)

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
        "schema_version":   "v2.3",   # V3.25.8 — adds 3D volume window (avg_3d_vs_20d, vol_3d_state)
        "price":            price,
        "market_cap":       market_cap,
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
        # V3.22 — short-term price thrust + fundamentals (P/S, GM, Rev YoY)
        "short_term_returns":  short_returns,
        "fundamentals":        fundamentals,
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
