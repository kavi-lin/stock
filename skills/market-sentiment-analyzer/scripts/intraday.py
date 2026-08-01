#!/usr/bin/env python3
"""
market-sentiment-analyzer/intraday — deterministic intraday market-weakness engine.

Companion to mood.py. Where mood.py reads slow options-implied sentiment
(VIX / SKEW / PCR / CNN F&G, once daily), this engine reads FAST intraday
price + volume action for SPY / QQQ / IWM plus the last ~60 completed sessions,
to flag breakdowns the daily mood misses:

  破底       — today's low pierces the recent 5d / 20d / 50d low
  止跌       — intraday reversal back off the low after weakness (hammer / reclaim)
  高開低走   — gap-up that fades (open strong, close weak)
  量增價跌   — distribution (relative-volume surge on a down move)
  VWAP loss  — price below the intraday volume-weighted average price
  MA / streak— price vs MA20/MA50, consecutive down days, O'Neil distribution days

Output: Dashboard/intraday_mood.json. Refreshed by dashboard_server's
intraday_mood_poll_loop during US market hours + one post-close snapshot.

Deterministic, NO LLM. Every source degrades gracefully (never raises); on total
failure it still writes a {"_partial": true, "aggregate": {"score": null}}
skeleton so the panel shows "data unavailable" instead of erroring.

Intraday bars + volume REQUIRE FMP — Finnhub's /stock/candle is premium-only, so
the broad-market intraday read has no free Finnhub path; FMP is the sole source.

The signed score convention matches mood.py (bull positive), but here NEGATIVE is
the signal of interest: -100 = breaking down on volume, +100 = strong on volume.

Tuning knobs (UNIVERSE / WEIGHTS / thresholds) are module constants up top — this
is an exploration-phase panel, expected to be re-weighted by hand, not journaled.

Usage:
    python3 intraday.py --output Dashboard/intraday_mood.json
    python3 intraday.py --json-only            # suppress the human summary line
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import date, datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))

# ── Tuning constants ─────────────────────────────────────────────────────────
UNIVERSE = [
    {"symbol": "SPY", "label": "大盤",   "weight": 0.50},
    {"symbol": "QQQ", "label": "科技",   "weight": 0.30},
    {"symbol": "IWM", "label": "小型股", "weight": 0.20},
]

FULL_SESSION_BARS = 78          # 6.5h regular session / 5-min bars

# Signed-component weights (re-weight freely; missing components drop out and the
# remainder is renormalized, same as mood.py).
WEIGHTS = {
    "dir":        0.22,         # current vs prev close
    "range_pos":  0.16,         # where in today's range we sit (near low = weak)
    "vwap":       0.14,         # price vs intraday VWAP
    "vol_price":  0.16,         # volume-confirmed direction (distribution vs accumulation)
    "break_low":  0.20,         # 破底 severity
    "trend":      0.12,         # MA20 position + down-streak penalty
}

# 破底 severity → signed penalty fed into the break_low component
BREAK_LOW_PENALTY = {"5d": -40.0, "20d": -72.0, "50d": -100.0}

RVOL_SURGE = 1.3                # ≥ → 量增 (surge)
RVOL_QUIET = 0.7                # ≤ → 量縮 (quiet)
DIST_DAYS_LOOKBACK = 25         # O'Neil distribution-day window
DIST_DAYS_FLAG = 4              # flag when ≥ this many in the window


# ── NaN-safe helpers (output written with allow_nan=False) ───────────────────
def _f(v):
    try:
        x = float(v)
        return None if math.isnan(x) or math.isinf(x) else x
    except (TypeError, ValueError):
        return None


def _round(v, n=2):
    x = _f(v)
    return round(x, n) if x is not None else None


def _clamp(v, lo=-100.0, hi=100.0):
    return max(lo, min(hi, v))


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


# ── Labels ───────────────────────────────────────────────────────────────────
def risk_label(score):
    """Signed score → (en, zh). Negative = breakdown; positive = strength."""
    if score is None:
        return ("Unknown", "資料缺")
    if score <= -50:
        return ("Breakdown Alert", "破底警戒")
    if score <= -20:
        return ("Weak", "偏弱")
    if score < 20:
        return ("Neutral", "中性")
    if score < 50:
        return ("Firm", "偏強")
    return ("Strong", "強勢")


def _vwap(bars):
    num = den = 0.0
    for b in bars:
        tp = (b["h"] + b["l"] + b["c"]) / 3.0
        num += tp * b["v"]
        den += b["v"]
    return num / den if den > 0 else None


# ── Momentum oscillators (pure-python; confirmation layer, NOT score drivers) ──
# These are lagging and whipsaw on intraday data — used only to emit 下殺 / 反轉
# flags as confluence with the price-action signals, never to move the score.
# Tunable knobs:
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9
KDJ_N, KDJ_K, KDJ_D = 9, 3, 3
KDJ_OB, KDJ_OS = 70.0, 30.0     # K overbought / oversold zones for cross gating


def _ema(values, span):
    """Recursive EMA seeded at the first value (matches pandas ewm adjust=False)."""
    if not values:
        return []
    alpha = 2.0 / (span + 1)
    out, e = [], values[0]
    for i, v in enumerate(values):
        e = v if i == 0 else alpha * v + (1 - alpha) * e
        out.append(e)
    return out


def compute_macd(closes, fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL):
    """DIF/DEA/histogram + last-bar cross. None until enough bars for a stable
    signal line (slow+signal). cross ∈ {'golden','death',None}."""
    if len(closes) < slow + signal:
        return None
    ef, es = _ema(closes, fast), _ema(closes, slow)
    dif = [a - b for a, b in zip(ef, es)]
    dea = _ema(dif, signal)
    hist = [d - e for d, e in zip(dif, dea)]
    cross = None
    if len(hist) >= 2:
        if hist[-2] <= 0 < hist[-1]:
            cross = "golden"
        elif hist[-2] >= 0 > hist[-1]:
            cross = "death"
    return {"dif": round(dif[-1], 3), "dea": round(dea[-1], 3),
            "hist": round(hist[-1], 3),
            "hist_prev": round(hist[-2], 3) if len(hist) >= 2 else None,
            "cross": cross}


def compute_kdj(highs, lows, closes, n=KDJ_N, k_smooth=KDJ_K, d_smooth=KDJ_D):
    """Stochastic KDJ. RSV over n bars → K (1/k_smooth smoothing) → D → J=3K-2D.
    None until n+d_smooth bars. cross ∈ {'golden','death',None} on K vs D."""
    if len(closes) < n + d_smooth:
        return None
    k, d, ks, ds = 50.0, 50.0, [], []
    for i in range(len(closes)):
        if i < n - 1:
            ks.append(None); ds.append(None); continue
        hi = max(highs[i - n + 1:i + 1]); lo = min(lows[i - n + 1:i + 1])
        rng = hi - lo
        rsv = 50.0 if rng == 0 else (closes[i] - lo) / rng * 100.0
        k = (k_smooth - 1) / k_smooth * k + rsv / k_smooth
        d = (d_smooth - 1) / d_smooth * d + k / d_smooth
        ks.append(k); ds.append(d)
    valid = [(kk, dd) for kk, dd in zip(ks, ds) if kk is not None]
    if len(valid) < 2:
        return None
    k_cur, d_cur = valid[-1]; k_prev, d_prev = valid[-2]
    cross = ("golden" if k_prev <= d_prev and k_cur > d_cur
             else "death" if k_prev >= d_prev and k_cur < d_cur else None)
    return {"k": round(k_cur, 1), "d": round(d_cur, 1), "j": round(3 * k_cur - 2 * d_cur, 1),
            "k_prev": round(k_prev, 1), "cross": cross}


# ── Pure assessment core (no network — unit-testable) ────────────────────────
def assess(symbol, intraday_bars, daily_bars, *, label=None, live=None):
    """Score one ticker from today's 5-min bars + prior completed daily bars.

    intraday_bars : today's bars, oldest-first, [{time,o,h,l,c,v}, ...]
    daily_bars    : prior COMPLETED sessions, oldest-first (today excluded),
                    [{date,o,h,l,c,v}, ...]
    live          : optional real-time quote snapshot
                    {price, day_open, day_high, day_low, prev_close, volume, timestamp}.
                    The last closed 5-min bar lags up to ~5-6 min, so when present the
                    live quote overrides spot price / session high-low / day volume /
                    prev close — this is what makes 破底 / 止跌 detection second-level
                    instead of one-bar stale. VWAP and the intrabar pattern still come
                    from the 5-min bars (the quote carries no bar history).
    Returns a per-ticker dict (score may be None when intraday data is missing).
    """
    if not intraday_bars:
        return {
            "symbol": symbol, "label": label, "score": None,
            "risk_label": "資料缺", "risk_label_en": "Unknown",
            "flags": [], "interpretation_zh": "盤中資料缺", "_health": "missing",
        }

    day_open = intraday_bars[0]["o"]
    day_high = max(b["h"] for b in intraday_bars)
    day_low = min(b["l"] for b in intraday_bars)
    price = intraday_bars[-1]["c"]
    cum_vol = sum(b["v"] for b in intraday_bars)
    vwap = _vwap(intraday_bars)
    frac = max(0.05, min(1.0, len(intraday_bars) / FULL_SESSION_BARS))

    prev_close = daily_bars[-1]["c"] if daily_bars else day_open

    # Real-time quote override — authoritative session extremes / spot / day volume,
    # fresher than the last closed 5-min bar (which can be ~5-6 min stale).
    used_live = False
    quote_ts = None
    if live:
        quote_ts = live.get("timestamp")
        if live.get("price"):
            price = live["price"]; used_live = True
        if live.get("day_open"):
            day_open = live["day_open"]
        if live.get("day_high"):
            day_high = max(day_high, live["day_high"])
        if live.get("day_low"):
            day_low = min(day_low, live["day_low"])
        if live.get("prev_close"):
            prev_close = live["prev_close"]
        if live.get("volume") and live["volume"] > 0:
            cum_vol = live["volume"]

    # Prior-session aggregates
    closes = [b["c"] for b in daily_bars]
    vols = [b["v"] for b in daily_bars]
    lows = [b["l"] for b in daily_bars]
    highs = [b["h"] for b in daily_bars]

    def _recent_low(n):
        seg = lows[-n:]
        return min(seg) if seg else None

    low5, low20, low50 = _recent_low(5), _recent_low(20), _recent_low(50)
    ma20 = _mean(closes[-20:]) if len(closes) >= 20 else None
    ma50 = _mean(closes[-50:]) if len(closes) >= 50 else None
    avg20_vol = _mean(vols[-20:]) if len(vols) >= 20 else _mean(vols)

    cdd = 0
    for i in range(len(closes) - 1, 0, -1):
        if closes[i] < closes[i - 1]:
            cdd += 1
        else:
            break
    dist = 0
    for i in range(max(1, len(closes) - DIST_DAYS_LOOKBACK), len(closes)):
        if closes[i] < closes[i - 1] * 0.998 and vols[i] > vols[i - 1]:
            dist += 1

    # Intraday derived metrics
    ret_open = (price / day_open - 1) * 100 if day_open else None
    ret_pc = (price / prev_close - 1) * 100 if prev_close else None
    rng = day_high - day_low
    range_pos = (price - day_low) / rng if rng > 0 else 0.5
    vwap_gap = (price / vwap - 1) * 100 if vwap else None
    rvol = (cum_vol / frac) / avg20_vol if avg20_vol else None
    pct_ma20 = (price / ma20 - 1) * 100 if ma20 else None
    pct_ma50 = (price / ma50 - 1) * 100 if ma50 else None

    # 破底 — graded by deepest prior low pierced today
    break_level = None
    if low50 is not None and day_low < low50:
        break_level = "50d"
    elif low20 is not None and day_low < low20:
        break_level = "20d"
    elif low5 is not None and day_low < low5:
        break_level = "5d"

    # 止跌 — reversal off the low after weakness, or pierced-then-reclaimed
    weak_context = cdd >= 2 or (pct_ma20 is not None and pct_ma20 < -1.5)
    reclaimed = low5 is not None and day_low < low5 and price > low5
    reversal = range_pos >= 0.6 and price > day_open
    stabilizing = bool((weak_context and reversal) or reclaimed)

    # ── signed components (bull positive, -100..+100) ──
    comp = {}
    if ret_pc is not None:
        comp["dir"] = round(_clamp(ret_pc / 2.0 * 100), 1)       # -2% → -100
    comp["range_pos"] = round(_clamp((range_pos - 0.5) * 200), 1)
    if vwap_gap is not None:
        comp["vwap"] = round(_clamp(vwap_gap / 1.0 * 100), 1)    # ±1% → ±100
    if rvol is not None and ret_pc is not None:
        sgn = 1.0 if ret_pc > 0 else -1.0 if ret_pc < 0 else 0.0
        comp["vol_price"] = round(_clamp(sgn * min(rvol, 2.5) / 2.5 * 100), 1)
    bl = BREAK_LOW_PENALTY.get(break_level, 0.0)
    if stabilizing:
        bl *= 0.4                                                # reclaim dampens the破底 hit
    comp["break_low"] = round(bl, 1)
    if pct_ma20 is not None:
        t = pct_ma20 * 8.0                                        # +12.5% → +100
        if cdd >= 3:
            t -= 15.0
        comp["trend"] = round(_clamp(t), 1)

    used = {k: WEIGHTS[k] for k in comp if k in WEIGHTS}
    score = round(sum(comp[k] * used[k] for k in used) / sum(used.values())) if used else None
    # 止跌 softens (does not override) a deeply negative read — it's a signal.
    if score is not None and stabilizing and score < 0:
        score = round(score * 0.7)

    # Intraday shape pattern
    gap_up = prev_close and day_open > prev_close * 1.001
    gap_dn = prev_close and day_open < prev_close * 0.999
    if gap_up and range_pos < 0.35 and price < day_open:
        pattern, pattern_zh = "gap_up_fade", "高開低走"
    elif gap_dn and range_pos > 0.65 and price > day_open:
        pattern, pattern_zh = "gap_down_recover", "低開高走"
    elif ret_open is not None and ret_open > 0.3 and range_pos > 0.6:
        pattern, pattern_zh = "trend_up", "盤中走強"
    elif ret_open is not None and ret_open < -0.3 and range_pos < 0.4:
        pattern, pattern_zh = "trend_down", "盤中走弱"
    else:
        pattern, pattern_zh = "range", "區間震盪"

    # ── flags (ordered later by severity) ──
    flags = []
    if break_level:
        ref = {"5d": low5, "20d": low20, "50d": low50}[break_level]
        sev = {"5d": "low", "20d": "med", "50d": "high"}[break_level]
        zhn = {"5d": "5日", "20d": "20日", "50d": "50日"}[break_level]
        suffix = "（盤中已收復，疑假跌破）" if stabilizing else ""
        flags.append({"type": "break_low", "severity": sev,
                      "text_zh": f"跌破{zhn}低點 {ref:.2f}{suffix}"})
    if stabilizing and not break_level:
        flags.append({"type": "stabilizing", "severity": "info",
                      "text_zh": f"日內自低點反彈，收復至區間 {range_pos * 100:.0f}%，止跌訊號"})
    if pattern == "gap_up_fade":
        flags.append({"type": "gap_up_fade", "severity": "med",
                      "text_zh": "高開低走，開盤動能轉弱"})
    if pattern == "gap_down_recover":
        flags.append({"type": "gap_down_recover", "severity": "info",
                      "text_zh": "低開高走，盤中買盤回補"})
    if rvol is not None and ret_pc is not None:
        if rvol >= RVOL_SURGE and ret_pc < -0.2:
            flags.append({"type": "distribution", "severity": "med",
                          "text_zh": f"量增價跌（RVOL {rvol:.1f}，出貨疑慮）"})
        elif rvol >= RVOL_SURGE and ret_pc > 0.2:
            flags.append({"type": "accumulation", "severity": "info",
                          "text_zh": f"量價齊揚（RVOL {rvol:.1f}）"})
        elif rvol <= RVOL_QUIET:
            flags.append({"type": "low_volume", "severity": "info",
                          "text_zh": f"量縮（RVOL {rvol:.1f}），方向訊號弱"})
    if vwap_gap is not None and vwap_gap < -0.1:
        flags.append({"type": "below_vwap", "severity": "low",
                      "text_zh": f"跌破 VWAP（{vwap_gap:+.2f}%）"})
    if cdd >= 3:
        flags.append({"type": "down_streak", "severity": "med",
                      "text_zh": f"連續下跌 {cdd} 天"})
    if dist >= DIST_DAYS_FLAG:
        flags.append({"type": "distribution_days", "severity": "med",
                      "text_zh": f"近{DIST_DAYS_LOOKBACK}日出貨日 {dist} 天"})

    # ── momentum oscillators — confluence flags only (score untouched) ──
    i_close = [b["c"] for b in intraday_bars]
    i_high = [b["h"] for b in intraday_bars]
    i_low = [b["l"] for b in intraday_bars]
    momentum = {
        "macd_5m": compute_macd(i_close), "kdj_5m": compute_kdj(i_high, i_low, i_close),
        "macd_1d": compute_macd(closes), "kdj_1d": compute_kdj(highs, lows, closes),
    }
    m5, k5, m1 = momentum["macd_5m"], momentum["kdj_5m"], momentum["macd_1d"]
    # 下殺 — intraday momentum rolling over from a high
    if k5 and k5["cross"] == "death" and (k5["k_prev"] >= KDJ_OB or k5["j"] >= 90):
        flags.append({"type": "momentum_breakdown", "severity": "med",
                      "text_zh": f"盤中 KDJ 高檔死叉（K{k5['k']}/D{k5['d']}），動能轉弱"})
    elif m5 and m5["cross"] == "death" and vwap_gap is not None and vwap_gap < 0:
        flags.append({"type": "momentum_breakdown", "severity": "med",
                      "text_zh": "盤中 MACD 死叉 + 跌破 VWAP，下殺確認"})
    # 反轉 — intraday bottoming, or daily momentum improving after weakness
    if k5 and k5["cross"] == "golden" and (k5["k_prev"] <= KDJ_OS or k5["j"] <= 10):
        flags.append({"type": "momentum_reversal", "severity": "info",
                      "text_zh": f"盤中 KDJ 低檔金叉（K{k5['k']}/D{k5['d']}），反轉訊號"})
    elif (m1 and m1["hist"] is not None and m1["hist_prev"] is not None
          and m1["hist"] > m1["hist_prev"] and m1["hist"] < 0 and (cdd >= 2 or break_level)):
        flags.append({"type": "momentum_reversal", "severity": "info",
                      "text_zh": "日線 MACD 柱狀體轉升，動能改善"})
    # daily MACD cross — regime context (low noise; daily series is stable)
    if m1 and m1["cross"] == "death":
        flags.append({"type": "macd_daily", "severity": "low", "text_zh": "日線 MACD 死叉"})
    elif m1 and m1["cross"] == "golden":
        flags.append({"type": "macd_daily", "severity": "info", "text_zh": "日線 MACD 金叉"})

    en, zh = risk_label(score)
    interp = _interpret(zh, score, ret_pc, range_pos, break_level, stabilizing, rvol)

    return {
        "symbol": symbol, "label": label,
        "score": score, "risk_label": zh, "risk_label_en": en,
        "price": _round(price, 2), "prev_close": _round(prev_close, 2),
        "day_open": _round(day_open, 2), "day_high": _round(day_high, 2),
        "day_low": _round(day_low, 2),
        "intraday_return_open_pct": _round(ret_open, 2),
        "intraday_return_prevclose_pct": _round(ret_pc, 2),
        "range_position": _round(range_pos, 3),
        "vwap": _round(vwap, 2), "vwap_gap_pct": _round(vwap_gap, 2),
        "cum_volume": int(cum_vol), "avg20_volume": int(avg20_vol) if avg20_vol else None,
        "rvol": _round(rvol, 2),
        "ma20": _round(ma20, 2), "ma50": _round(ma50, 2),
        "pct_above_ma20": _round(pct_ma20, 2), "pct_above_ma50": _round(pct_ma50, 2),
        "consecutive_down_days": cdd, "distribution_days": dist,
        "recent_low_5d": _round(low5, 2), "recent_low_20d": _round(low20, 2),
        "recent_low_50d": _round(low50, 2),
        "break_low_level": break_level, "stabilizing": stabilizing,
        "open_pattern": pattern, "open_pattern_zh": pattern_zh,
        "components": comp, "flags": flags, "momentum": momentum,
        "session_fraction": round(frac, 3),
        "data_source": "live_quote+5min" if used_live else "5min",
        "quote_timestamp": quote_ts,
        "interpretation_zh": interp, "_health": "ok",
    }


def _interpret(zh, score, ret_pc, range_pos, break_level, stabilizing, rvol):
    parts = [f"{zh}（{score}）"]
    if ret_pc is not None:
        parts.append(f"現價較昨收 {ret_pc:+.2f}%")
    if break_level:
        parts.append(("假跌破" if stabilizing else "破底") + f"{break_level}")
    elif stabilizing:
        parts.append("止跌反彈")
    if rvol is not None:
        parts.append(f"RVOL {rvol:.1f}")
    parts.append(f"位於日內區間 {range_pos * 100:.0f}%")
    return "，".join(parts)


# ── Aggregate across the universe ────────────────────────────────────────────
_SEV_ORDER = {"high": 0, "med": 1, "low": 2, "info": 3}


def aggregate(rows):
    scored = [r for r in rows if r.get("score") is not None]
    if not scored:
        return {"score": None, "risk_label": "資料缺", "risk_label_en": "Unknown",
                "headline_zh": "盤中資料暫缺", "flags": []}
    wsum = sum(r.get("weight", 0) for r in scored) or len(scored)
    score = round(sum(r["score"] * r.get("weight", 1) for r in scored)
                  / (wsum if any(r.get("weight") for r in scored) else len(scored)))
    en, zh = risk_label(score)

    merged = {}
    for r in scored:
        for fl in r.get("flags", []):
            m = merged.setdefault(fl["type"], {
                "type": fl["type"], "severity": fl["severity"],
                "text_zh": fl["text_zh"], "tickers": []})
            m["tickers"].append(r["symbol"])
            if _SEV_ORDER.get(fl["severity"], 9) < _SEV_ORDER.get(m["severity"], 9):
                m["severity"] = fl["severity"]
                m["text_zh"] = fl["text_zh"]
    flags = sorted(merged.values(), key=lambda f: _SEV_ORDER.get(f["severity"], 9))

    if flags:
        top = "、".join(f["text_zh"].split("（")[0] for f in flags[:2])
        headline = f"盤面{zh}（{score}）：{top}"
    else:
        headline = f"盤面{zh}（{score}），無顯著破底/出貨訊號"
    return {"score": score, "risk_label": zh, "risk_label_en": en,
            "headline_zh": headline, "flags": flags}


# ── FMP fetchers (best-effort via the shared rate-governed pool) ─────────────
def _pool():
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from scripts._shared import fmp_pool
    return fmp_pool


def _fetch_intraday(symbol):
    """Today's 5-min bars oldest-first; returns (bars, latest_date)."""
    fp = _pool()
    today = date.today().isoformat()
    rows = fp.get("historical-chart/5min", {"symbol": symbol, "from": today, "to": today}, stable=True)
    if not isinstance(rows, list) or not rows:
        seven = (date.today() - timedelta(days=7)).isoformat()
        rows = fp.get("historical-chart/5min", {"symbol": symbol, "from": seven, "to": today}, stable=True) or []
    bars = []
    for r in (rows if isinstance(rows, list) else []):
        try:
            bars.append({"time": r.get("date"), "o": float(r["open"]), "h": float(r["high"]),
                         "l": float(r["low"]), "c": float(r["close"]), "v": int(r.get("volume") or 0)})
        except (TypeError, ValueError, KeyError):
            continue
    bars.sort(key=lambda b: b["time"] or "")
    if not bars:
        return [], None
    latest = (bars[-1]["time"] or "")[:10]
    bars = [b for b in bars if (b["time"] or "")[:10] == latest]
    return bars, latest


def _fetch_live_quote(symbol):
    """Real-time single-symbol quote (price + session high/low/open + day volume +
    prev close). ~2s fresh vs the 5-min bar's ~5-6 min lag. Returns dict | None."""
    fp = _pool()
    q = fp.get("quote", {"symbol": symbol}, stable=True)
    row = q[0] if isinstance(q, list) and q else (q if isinstance(q, dict) else None)
    if not row:
        return None
    return {
        "price": _f(row.get("price")), "day_open": _f(row.get("open")),
        "day_high": _f(row.get("dayHigh")), "day_low": _f(row.get("dayLow")),
        "prev_close": _f(row.get("previousClose")), "volume": _f(row.get("volume")),
        "timestamp": row.get("timestamp"),
    }


def _fetch_daily(symbol, before_date):
    """Prior COMPLETED daily bars (date < before_date), oldest-first, ~75 sessions."""
    fp = _pool()
    start = (date.today() - timedelta(days=130)).isoformat()
    # Stable EOD endpoint returns a flat list (newest-first) of full OHLCV bars.
    data = fp.get("historical-price-eod/full", {"symbol": symbol, "from": start,
                                                "to": date.today().isoformat()}, stable=True)
    hist = data if isinstance(data, list) else (data.get("historical") if isinstance(data, dict) else None)
    if not hist:
        # Legacy v3 fallback (nested under "historical").
        data = fp.get_url(f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}",
                          {"timeseries": 130})
        hist = data.get("historical") if isinstance(data, dict) else (data if isinstance(data, list) else None)
    bars = []
    for r in (hist or []):
        d = (r.get("date") or "")[:10]
        if before_date and d >= before_date:
            continue
        try:
            bars.append({"date": d, "o": float(r["open"]), "h": float(r["high"]),
                         "l": float(r["low"]), "c": float(r["close"]), "v": int(r.get("volume") or 0)})
        except (TypeError, ValueError, KeyError):
            continue
    bars.sort(key=lambda b: b["date"])
    return bars


def _market_open():
    """True if ET is Mon-Fri 09:30-16:00 (best-effort; standalone of the server)."""
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        now = datetime.now(timezone(timedelta(hours=-4)))
    if now.weekday() >= 5:
        return False
    o = now.replace(hour=9, minute=30, second=0, microsecond=0)
    c = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return o <= now <= c


def build():
    rows = []
    health = {}
    frac = None
    for u in UNIVERSE:
        sym = u["symbol"]
        try:
            intr, latest = _fetch_intraday(sym)
            live = _fetch_live_quote(sym)
            daily = _fetch_daily(sym, latest) if intr else []
            r = assess(sym, intr, daily, label=u["label"], live=live)
        except Exception as e:
            print(f"[intraday] {sym} assess failed: {e}", file=sys.stderr)
            r = {"symbol": sym, "label": u["label"], "score": None,
                 "risk_label": "資料缺", "risk_label_en": "Unknown", "flags": [],
                 "interpretation_zh": "抓取失敗", "_health": "error"}
        r["weight"] = u["weight"]
        health[sym] = r.get("_health", "ok")
        if frac is None and r.get("session_fraction") is not None:
            frac = r["session_fraction"]
        rows.append(r)

    agg = aggregate(rows)
    partial = agg["score"] is None or any(v in ("missing", "error") for v in health.values())
    return {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market_open": _market_open(),
        "session_fraction": frac,
        "aggregate": agg,
        "tickers": rows,
        "_source_health": health,
        "_partial": partial,
    }


def _write_atomic(path, payload):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, allow_nan=False)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description="Intraday market-weakness engine")
    ap.add_argument("--output", default=os.path.join(_ROOT, "Dashboard", "intraday_mood.json"))
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args()

    try:
        payload = build()
    except Exception as e:
        print(f"[intraday] build failed: {e}", file=sys.stderr)
        payload = {
            "version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "market_open": False, "session_fraction": None,
            "aggregate": {"score": None, "risk_label": "資料缺", "risk_label_en": "Unknown",
                          "headline_zh": "引擎錯誤", "flags": []},
            "tickers": [], "_source_health": {"error": str(e)}, "_partial": True,
        }

    _write_atomic(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not args.json_only:
        a = payload.get("aggregate", {})
        sys.stderr.write(f"\n→ Intraday {a.get('score')} ({a.get('risk_label')}) │ "
                         f"{a.get('headline_zh')} │ partial={payload.get('_partial')} "
                         f"→ {args.output}\n")
    return 2 if payload.get("_partial") else 0


if __name__ == "__main__":
    sys.exit(main())
