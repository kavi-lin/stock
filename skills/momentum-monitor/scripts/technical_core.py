#!/usr/bin/env python3
"""
technical_core — shared pure-computation functions for chart-based technicals.

This module hosts the computation primitives (MA structure, RSI, volume
profile, stage classification, MA crosses, MACD) originally grown inside
`momentum-monitor/momentum.py`. Both `momentum.py` (the full momentum-monitor
pipeline with composite score + short interest) and `technical-analyst/
analyze.py` (chart-pure technical analysis for investment protocol V4.8
Phase 2) consume these primitives, so they live here rather than being
duplicated between skills.

Public API (no underscore prefix):
- fetch_history(ticker, period="1y") → (pandas DataFrame, yf.Ticker)
- intraday_state(hist) → (state, elapsed_min, projection_factor)
- volume_profile(hist) → dict
- classify_stage(price, ma20, ma50, ma200) → str
- detect_crosses(hist, window=30) → list[dict]
- ma_structure(hist) → dict
- rsi_14(close, period=14) → pandas Series
- rsi_state(hist) → dict
- compute_macd(close, fast=12, slow=26, signal=9) → dict

Nothing momentum-specific (composite score, short interest, signals,
caching) lives here — those remain in momentum.py.
"""
import os
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

try:
    from zoneinfo import ZoneInfo      # Python 3.9+
    _ET = ZoneInfo("America/New_York")
except Exception:
    _ET = timezone(timedelta(hours=-4))  # EDT fallback (approximate)

SESSION_TOTAL_MIN = 390   # 9:30 → 16:00 ET regular session
INTRADAY_EARLY_CUTOFF_MIN = 30  # < 30 min elapsed → too_early (vol signals suppressed)

# v1.62 (I-PG): primary OHLC source switched to FMP /stable/historical-price-eod/full
# (Starter plan unlocks this endpoint). yfinance kept as automatic fallback when
# FMP_API_KEY is unset, returns 401, or response is malformed. The yf.Ticker handle
# is still returned so downstream callers (momentum.py:_short_interest_block) can
# read .info attributes.
_PERIOD_DAYS = {
    "1mo": 35, "3mo": 95, "6mo": 185, "1y": 370, "2y": 740, "5y": 1830,
    "10y": 3650, "max": 10000,
}


def _fetch_fmp_ohlc(ticker, period):
    """Fetch FMP /stable/historical-price-eod/full → DataFrame matching yfinance schema.
    Returns None on any failure (caller falls back to yfinance)."""
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return None
    days = _PERIOD_DAYS.get(period, 370)
    end = datetime.now()
    start = end - timedelta(days=days)
    try:
        import requests
        r = requests.get(
            "https://financialmodelingprep.com/stable/historical-price-eod/full",
            params={
                "symbol": ticker,
                "from": start.date().isoformat(),
                "to":   end.date().isoformat(),
                "apikey": api_key,
            },
            timeout=30,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if not isinstance(data, list) or not data:
            return None
        df = pd.DataFrame(data)
        if df.empty or "date" not in df.columns:
            return None
        df["Date"] = pd.to_datetime(df["date"])
        df = df.set_index("Date").sort_index()  # ascending date
        df = df.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        })
        # FMP /stable/historical-price-eod returns split-adjusted (NOT dividend-adjusted)
        # close. yfinance auto_adjust=True is dividend-adjusted. For RSI/MA/MACD pattern
        # recognition the difference is ~1-2% accumulated dividends — does not affect
        # technical signals. Dividend payers (KO/JNJ/PG) may show slightly higher MA
        # readings vs yfinance, acceptable.
        return df[["Open", "High", "Low", "Close", "Volume"]]
    except Exception:
        return None


# ── Data fetch ─────────────────────────────────────────────────────────
def fetch_history(ticker, period="1y"):
    """Fetch OHLCV. Tries FMP /stable/historical-price-eod/full first (Starter plan),
    falls back to yfinance on any failure. Always returns (hist_df, yf.Ticker_handle)
    so downstream code can still access yfinance metadata via the handle.
    Raises RuntimeError if both providers fail."""
    t = yf.Ticker(ticker)  # lazy — no API call until .info / .history accessed

    # Primary: FMP
    hist = _fetch_fmp_ohlc(ticker, period)
    if hist is not None and not hist.empty:
        return hist, t

    # Fallback: yfinance
    hist = t.history(period=period, auto_adjust=True)
    if hist is None or hist.empty:
        raise RuntimeError(f"no history data for {ticker}")
    return hist, t


# ── Intraday partial-bar detection ─────────────────────────────────────
def intraday_state(hist):
    """Classify the last bar's reliability vs today's ET session.

    Returns (state, elapsed_min, projection_factor):
      - 'complete'   : last bar is a full session (weekend/holiday/pre-market
                       or today ≥ 16:00 ET) → projection_factor = 1.0
      - 'too_early'  : today's session, 0 ≤ elapsed < 30 min
                       → projection_factor = None (suppress volume signals)
      - 'partial'    : today's session, 30 ≤ elapsed < 390 min
                       → projection_factor = 390 / elapsed_min
    """
    now_et = datetime.now(_ET)
    last_bar_ts = hist.index[-1]
    last_bar_date = last_bar_ts.date() if hasattr(last_bar_ts, "date") else None
    today_et = now_et.date()

    if last_bar_date is None or last_bar_date < today_et:
        return ("complete", SESSION_TOTAL_MIN, 1.0)

    market_open  = now_et.replace(hour=9,  minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0,  second=0, microsecond=0)

    if now_et >= market_close:
        return ("complete", SESSION_TOTAL_MIN, 1.0)
    if now_et < market_open:
        return ("too_early", 0, None)

    elapsed_min = int((now_et - market_open).total_seconds() // 60)
    if elapsed_min < INTRADAY_EARLY_CUTOFF_MIN:
        return ("too_early", elapsed_min, None)
    return ("partial", elapsed_min, SESSION_TOTAL_MIN / float(elapsed_min))


# ── Volume profile ─────────────────────────────────────────────────────
def volume_profile(hist):
    """Volume dynamics: today vs avg, spike label, 5d/10d trend. Intraday-safe.

    Keys: today / today_effective / avg_20d / avg_50d / ratio_20d / spike_label
          / spike_days_last_10 / volume_trend / intraday_state / elapsed_min
    """
    volume = hist["Volume"]
    today_v_raw = float(volume.iloc[-1])
    state, elapsed_min, proj = intraday_state(hist)

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

    # too_early → ratio is unreliable (<30 min of session); caller should treat
    # ratio_20d=None as neutral (no signal, no warning, neutral vol_score).
    if state == "too_early":
        today_v_effective = today_v_raw
        ratio = None
    elif state == "partial":
        today_v_effective = today_v_raw * proj    # project → full-day equivalent
        ratio = today_v_effective / avg_20 if avg_20 > 0 else 0.0
    else:
        today_v_effective = today_v_raw
        ratio = today_v_effective / avg_20 if avg_20 > 0 else 0.0

    if ratio is None:
        spike = "UNKNOWN"
    elif ratio >= 3.0:
        spike = "HEAVY_SPIKE"
    elif ratio >= 2.0:
        spike = "MILD_SPIKE"
    else:
        spike = "NORMAL"

    # 10-day spike count (today excluded)
    hist_vol = volume.iloc[:-1].tail(10) if len(volume) > 1 else volume.tail(10)
    last10_avg = avg_20 if avg_20 > 0 else 1
    spike_days = int((hist_vol / last10_avg >= 2.0).sum())

    # Trend = prior-5d avg vs prior-10d avg (both exclude today).
    prior = volume.iloc[:-1] if len(volume) > 1 else volume
    v5  = float(prior.tail(5).mean())  if len(prior) >= 5  else 0.0
    v10 = float(prior.tail(10).mean()) if len(prior) >= 10 else 0.0
    if v10 == 0:
        trend = "stable"
    elif v5 / v10 >= 1.15:
        trend = "expanding"
    elif v5 / v10 <= 0.85:
        trend = "contracting"
    else:
        trend = "stable"

    return {
        "today":              int(today_v_raw),
        "today_effective":    int(today_v_effective) if today_v_effective else 0,
        "avg_20d":            int(avg_20),
        "avg_50d":            int(avg_50),
        "ratio_20d":          round(ratio, 2) if ratio is not None else None,
        "spike_label":        spike,
        "spike_days_last_10": spike_days,
        "volume_trend":       trend,
        "intraday_state":     state,
        "elapsed_min":        elapsed_min,
    }


# ── MA cross detection ────────────────────────────────────────────────
def detect_crosses(hist, window=30):
    """Scan last `window` sessions for 20/50 and 50/200 MA cross events."""
    close = hist["Close"]
    ma20  = close.rolling(20).mean()
    ma50  = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()

    crosses = []
    today_idx = len(close) - 1
    start_idx = max(200, today_idx - window)

    for i in range(start_idx + 1, today_idx + 1):
        if pd.notna(ma20.iloc[i-1]) and pd.notna(ma50.iloc[i-1]):
            prev_diff = ma20.iloc[i-1] - ma50.iloc[i-1]
            curr_diff = ma20.iloc[i]   - ma50.iloc[i]
            if prev_diff <= 0 and curr_diff > 0:
                crosses.append({"type": "golden_cross_20_50", "date": str(close.index[i].date()), "days_ago": today_idx - i})
            elif prev_diff >= 0 and curr_diff < 0:
                crosses.append({"type": "death_cross_20_50",  "date": str(close.index[i].date()), "days_ago": today_idx - i})
        if pd.notna(ma50.iloc[i-1]) and pd.notna(ma200.iloc[i-1]):
            prev_diff = ma50.iloc[i-1] - ma200.iloc[i-1]
            curr_diff = ma50.iloc[i]   - ma200.iloc[i]
            if prev_diff <= 0 and curr_diff > 0:
                crosses.append({"type": "golden_cross_50_200", "date": str(close.index[i].date()), "days_ago": today_idx - i})
            elif prev_diff >= 0 and curr_diff < 0:
                crosses.append({"type": "death_cross_50_200",  "date": str(close.index[i].date()), "days_ago": today_idx - i})
    return crosses


# ── Stage classification + MA structure ───────────────────────────────
def classify_stage(price, ma20, ma50, ma200):
    """Weinstein-esque 4-stage classifier. Returns 'unknown' if any MA is NaN."""
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


def ma_structure(hist):
    """MA (20/50/200) values + distance % + stage + recent crosses."""
    close = hist["Close"]
    price = float(close.iloc[-1])

    def _clean(v):
        """bool(NaN) is truthy in Python — explicit NaN check before math."""
        fv = float(v)
        return None if fv != fv else fv

    ma20  = _clean(close.rolling(20).mean().iloc[-1])
    ma50  = _clean(close.rolling(50).mean().iloc[-1])
    ma200 = _clean(close.rolling(200).mean().iloc[-1])

    stage = classify_stage(price, ma20, ma50, ma200)
    above_20  = (price / ma20  - 1) * 100 if ma20  else None
    above_50  = (price / ma50  - 1) * 100 if ma50  else None
    above_200 = (price / ma200 - 1) * 100 if ma200 else None

    return {
        "ma_20":           round(ma20,  2) if ma20  is not None else None,
        "ma_50":           round(ma50,  2) if ma50  is not None else None,
        "ma_200":          round(ma200, 2) if ma200 is not None else None,
        "stage":           stage,
        "above_ma20_pct":  round(above_20, 2)  if above_20  is not None else None,
        "above_ma50_pct":  round(above_50, 2)  if above_50  is not None else None,
        "above_ma200_pct": round(above_200, 2) if above_200 is not None else None,
        "recent_crosses":  detect_crosses(hist),
    }


# ── RSI ─────────────────────────────────────────────────────────────────
def rsi_14(close, period=14):
    """Classic Wilder RSI: first avg is SMA, subsequent use Wilder EMA.
    Returns pandas Series aligned with `close`."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def rsi_state(hist):
    """Latest RSI-14 reading with zone label (oversold/neutral/bullish/overbought)."""
    rsi = rsi_14(hist["Close"])
    latest = rsi.iloc[-1]
    if pd.isna(latest):
        return {"rsi_14": None, "zone": "unknown"}
    v = float(latest)
    if v >= 70:   zone = "overbought"
    elif v >= 50: zone = "bullish"
    elif v >= 30: zone = "neutral"
    else:         zone = "oversold"
    return {"rsi_14": round(v, 1), "zone": zone}


# ── MACD (Moving Average Convergence Divergence) ───────────────────────
def compute_macd(close, fast=12, slow=26, signal=9):
    """Standard MACD:
      - macd_line   = EMA(fast) - EMA(slow)
      - signal_line = EMA(signal) of macd_line
      - histogram   = macd_line - signal_line

    Returns dict with latest values + short-term histogram trend
    (rising / falling / flat via last-3-bar slope sign).
    """
    ema_fast = close.ewm(span=fast,  adjust=False).mean()
    ema_slow = close.ewm(span=slow,  adjust=False).mean()
    macd_line   = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram   = macd_line - signal_line

    def _f(v):
        if v is None or pd.isna(v):
            return None
        return round(float(v), 3)

    trend = "flat"
    if len(histogram) >= 3:
        recent = histogram.tail(3).dropna()
        if len(recent) == 3:
            deltas = recent.diff().dropna()
            if len(deltas) >= 2:
                if all(d > 0 for d in deltas):
                    trend = "rising"
                elif all(d < 0 for d in deltas):
                    trend = "falling"
                elif deltas.iloc[-1] > 0 and abs(deltas.iloc[-1]) > abs(deltas.iloc[0]) * 0.5:
                    trend = "rising"
                elif deltas.iloc[-1] < 0 and abs(deltas.iloc[-1]) > abs(deltas.iloc[0]) * 0.5:
                    trend = "falling"

    return {
        "macd_line":        _f(macd_line.iloc[-1]),
        "signal_line":      _f(signal_line.iloc[-1]),
        "histogram":        _f(histogram.iloc[-1]),
        "histogram_trend":  trend,
        "bullish_cross":    bool(len(macd_line) > 1
                                  and pd.notna(macd_line.iloc[-2])
                                  and pd.notna(signal_line.iloc[-2])
                                  and macd_line.iloc[-2] <= signal_line.iloc[-2]
                                  and macd_line.iloc[-1]  > signal_line.iloc[-1]),
        "bearish_cross":    bool(len(macd_line) > 1
                                  and pd.notna(macd_line.iloc[-2])
                                  and pd.notna(signal_line.iloc[-2])
                                  and macd_line.iloc[-2] >= signal_line.iloc[-2]
                                  and macd_line.iloc[-1]  < signal_line.iloc[-1]),
    }
