#!/usr/bin/env python3
"""
market-sentiment-analyzer/intraday_spikes — individual-stock 急拉/急殺 fast lane.

A separate lane from intraday.py: while intraday.py reads FMP 5-min bars for the
market-level read (SPY/QQQ/IWM), this module reads **Alpaca 1-minute bars** for a
hand-edited watchlist of individual stocks and flags sharp spikes / sharp drops
(急拉 / 急殺) within the last few minutes.

Why Alpaca (not FMP): FMP's 1-min REST is paywalled (HTTP 402). Alpaca's Market
Data API serves real-time 1-min bars on its FREE tier (IEX feed) — the only $0
path to individual-stock 1-min data.

⚠️ Free IEX feed caveat: IEX is a single exchange (small share of consolidated
volume), so VOLUME is systematically understated. Detection is therefore
**price-led** (the IEX price tracks the tape well for liquid names); volume is a
secondary, optional confirmation — never a hard gate. Full-volume accuracy needs
Alpaca's paid SIP feed ($99/mo, feed=sip).

Deterministic, NO LLM. Graceful no-op when ALPACA_API_KEY / ALPACA_SECRET_KEY are
absent (writes a {"_health":"no_alpaca_key"} skeleton so the panel shows a hint).

Output: Dashboard/intraday_spikes.json. Refreshed by dashboard_server's
intraday_spikes_poll_loop every INTRADAY_SPIKES_INTERVAL_SEC (default 60s) during
US market hours. Read-only exploration layer — NEVER feeds investment_protocol.

Usage:
    python3 intraday_spikes.py --output Dashboard/intraday_spikes.json
    python3 intraday_spikes.py --json-only
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))
_WATCHLIST = os.path.join(os.path.dirname(SCRIPT_DIR), "config", "spike_watchlist.txt")

# Reuse the pure-python oscillators from the sibling market engine (same dir).
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import intraday as _ind  # noqa: E402  (compute_macd / compute_kdj)

# ── Tuning constants (exploration-phase; edit freely) ────────────────────────
SPIKE_1M_PCT = 1.0      # |1-min return| ≥ this (%) → 急
SPIKE_3M_PCT = 2.0      # |3-min cumulative| ≥ this (%) → 急
VOL_MULT = 3.0          # this-min vol ≥ N× trailing avg → 量增 confirmation (secondary)
WINDOW_MIN = 5          # scan the last N completed minutes for a qualifying move
AVG_LOOKBACK = 15       # trailing minutes for the volume baseline
REVERSAL_LOOKBACK = 3   # a momentum cross stays "正在反轉" for this many bars after it
                        # fires → sticky display (won't flicker away next minute)
KDJ_OS, KDJ_OB = 30.0, 70.0   # KDJ oversold/overbought zones — for 翻揚/翻落 annotation only
# ── 反轉降噪 (雙確認 + σ 位移 + 翻面冷卻) ─────────────────────────────────────
# Why: 1-min KDJ crosses every few minutes in chop, so "任一交叉 → 反轉" turned the
# panel into noise. 反轉 now needs KDJ **AND** MACD the same way, PLUS a price
# displacement big enough vs this stock's own pre-cross σ. 寧可漏弱訊號，不要雜訊。
REV_SIGMA_K = 1.5           # |交叉後位移| ≥ K×σ 才算反轉（σ = 交叉前 10 根 1 分報酬率）
REV_MIN_DISP_PCT = 0.3      # σ 算不出（bars 不足/完全無波動）時退回的固定位移門檻 (%)
REV_ALERT_SIGMA = 2.5       # 無 zone 註記時，位移 ≥ 這個 σ 倍數才升級 alert/strong
REV_FLIP_COOLDOWN_MIN = 10  # 上一輪反方向反轉在這幾分鐘內 → 本輪翻面需額外條件
REV_FLIP_SIGMA = 2.5        # 冷卻期內放行翻面所需的 σ 倍數（或有 zone 註記）
# ── 開盤加嚴窗 (09:30–09:45 ET) ──────────────────────────────────────────────
# 開盤前 15 分鐘每檔都在跳，門檻不抬就是雜訊機。判定用**最後一根 bar 的時間戳**
# 轉 ET（非 wall clock），純函式可單元測試。
OPEN_GRACE_MIN = 15         # 開盤後這幾分鐘視為加嚴窗（09:30 含 → 09:45 不含）
OPEN_GATE_MULT = 1.5        # 窗內 SPIKE_1M_PCT / SPIKE_3M_PCT 門檻乘數
# ── 順勢續攻/續跌 (trend-continuation STATE detector) tuning ──────────────────
TREND_MA = (5, 10, 20)        # strict bull/bear stack on 1-min closes (ma5>ma10>ma20)
TREND_K_MIN = 50.0            # KDJ K floor for a bull trend — momentum intact, NOT a fresh cross
TREND_HIGH_WINDOW = 20        # bars defining the 創高/破低 reference extreme
TREND_HIGH_TOL = 0.001        # last price within 0.1% of the window extreme counts as 貼價
# ── 10-min baseline context (B: adaptive σ + regime + 持續性 + 急拉擊殺) ───────
# Why: a fixed |1分|≥1% gate over-fires on high-β names (1%/min is their normal
# breath) and under-fires on quiet names. These layers read the ~10-min run BEFORE
# the spike to judge the incoming minute IN CONTEXT instead of in isolation.
REGIME_WINDOW = 10        # bars (≈10 min) for the trend/σ baseline BEFORE the spike
BASELINE_MIN = 15         # need ≥ this many bars to engage the adaptive layer; else legacy
NOISE_SIGMA_K = 2.0       # |move| < K×σ + unconfirmed + 順勢/區間 → 雜訊 → 降級過濾
SUSTAIN_RANGE_FRAC = 0.34 # spike bar must close in the top/bottom this frac of its range
REGIME_SLOPE_PCT = 0.12   # |linreg slope| ≥ this %/bar → trending (else 區間)
REGIME_R2 = 0.50          # linreg R² ≥ this → trend clean/monotonic (else 區間)
BREAKOUT_TOL = 0.001      # spike close beyond the 10-bar range extreme → 突破/破底
# 急拉擊殺 (pump→fade) composite — needs the multi-bar window detect_spikes can't see
PF_PUMP_PCT = 1.5         # 急拉 leg cumulative ≥ this %
PF_FADE_RETRACE = 0.5     # 急殺 retraces ≥ this fraction of the pump (拉高出貨/誘多被殺)
PF_PUMP_WIN = 5           # pump accumulates within ≤ this many bars
PF_FADE_WIN = 5           # fade completes within ≤ this many bars after the peak
ALPACA_FEED = os.getenv("ALPACA_FEED", "iex")   # 'iex' (free) | 'sip' (paid, full volume)
ALPACA_DATA_HOST = "https://data.alpaca.markets"


def _load_watchlist():
    """One ticker per line; '#' comments and blanks ignored. Upper-cased + deduped."""
    out, seen = [], set()
    try:
        with open(_WATCHLIST, "r", encoding="utf-8") as f:
            for line in f:
                t = line.split("#", 1)[0].strip().upper()
                if t and t not in seen:
                    seen.add(t)
                    out.append(t)
    except FileNotFoundError:
        pass
    return out


# Public aliases (imported by dashboard_server for the watchlist edit endpoint).
load_watchlist = _load_watchlist

_VALID_TICKER = __import__("re").compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
_WATCHLIST_HEADER = (
    "# 個股急拉/急殺監控名單（Alpaca 1分鐘線）\n"
    "# 一行一個 ticker，# 開頭為註解。探索期隨時加減。\n"
    "# REST 多檔一次抓，數量無硬上限（建議 ≤ 50）。\n"
    "# 流動性高的標的 IEX 報價較準；偵測以「價格 % 變動」為主，量能僅次要參考\n"
    "# （免費 IEX feed 量被低估，不可當硬門檻）。\n"
)


def save_watchlist(tickers):
    """Validate + dedupe + atomically rewrite spike_watchlist.txt (header preserved).

    Returns the cleaned list actually written. Raises ValueError on bad input so
    the caller can surface a 400. US-equity tickers only (Alpaca IEX universe).
    """
    cleaned, seen = [], set()
    for raw in (tickers or []):
        t = str(raw).strip().upper()
        if not t:
            continue
        if not _VALID_TICKER.match(t):
            raise ValueError(f"invalid ticker: {raw!r}")
        if t not in seen:
            seen.add(t)
            cleaned.append(t)
    if len(cleaned) > 50:
        raise ValueError(f"too many tickers ({len(cleaned)} > 50)")
    body = _WATCHLIST_HEADER + "".join(t + "\n" for t in cleaned)
    os.makedirs(os.path.dirname(os.path.abspath(_WATCHLIST)), exist_ok=True)
    tmp = f"{_WATCHLIST}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp, _WATCHLIST)
    return cleaned


# ── 10-min baseline context helpers (pure, unit-testable) ────────────────────
def _stdev(values):
    """Sample standard deviation (None if < 2 points)."""
    n = len(values)
    if n < 2:
        return None
    m = sum(values) / n
    return (sum((v - m) ** 2 for v in values) / (n - 1)) ** 0.5


def _ret_sigma(closes_seg):
    """一段 closes 的 1 分報酬率(%)樣本 σ。不足 2 筆報酬 → None；完全無波動 → 0.0。"""
    rets = [(closes_seg[k] / closes_seg[k - 1] - 1) * 100
            for k in range(1, len(closes_seg)) if closes_seg[k - 1]]
    return _stdev(rets)


_TS_FRAC_RE = __import__("re").compile(r"\.(\d{1,9})")


def _parse_ts(s):
    """ISO8601（'Z' 結尾、奈秒小數都吃）→ aware datetime；解析不了回 None（絕不 raise）。"""
    if not isinstance(s, str) or not s.strip():
        return None
    t = _TS_FRAC_RE.sub(lambda m: "." + m.group(1)[:6], s.strip().replace("Z", "+00:00"))
    try:
        d = datetime.fromisoformat(t)
    except (ValueError, TypeError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def in_open_grace(bar_ts):
    """該 bar 時間戳落在 ET 09:30（含）–09:45（不含）→ True（開盤加嚴窗）。
    刻意吃 bar 時間而非 wall clock：回放/測試才可重現。解析失敗一律 False。"""
    d = _parse_ts(bar_ts)
    if d is None:
        return False
    try:
        from zoneinfo import ZoneInfo
        et = d.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        et = d.astimezone(timezone(timedelta(hours=-4)))
    open_m = 9 * 60 + 30
    return open_m <= et.hour * 60 + et.minute < open_m + OPEN_GRACE_MIN


def _linreg(ys):
    """Least-squares line over x=0..n-1. Returns (slope, r2). Flat/degenerate → (0, 0)."""
    n = len(ys)
    if n < 2:
        return 0.0, 0.0
    xm = (n - 1) / 2.0
    ym = sum(ys) / n
    sxx = sum((i - xm) ** 2 for i in range(n))
    sxy = sum((i - xm) * (ys[i] - ym) for i in range(n))
    syy = sum((y - ym) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return 0.0, 0.0
    slope = sxy / sxx
    r2 = (sxy * sxy) / (sxx * syy)
    return slope, r2


def _classify_context(up, regime, breakout):
    """(ctx_class, 中文標籤) from spike direction × 10-min regime × breakout flag.
    breakout/counter are the high-signal cases; trend = continuation; range = chop."""
    if regime == "range":
        if breakout:
            return "breakout", ("突破急拉" if up else "破底急殺")
        return "range", ("區間急拉" if up else "區間急殺")
    aligned = (regime == "up") == up
    if aligned:
        return "trend", ("順勢急拉" if up else "順勢急殺")
    return "counter", ("逆勢急拉" if up else "逆勢急殺")


def _spike_score(sigma_mult, ctx_class, confs_n, sustained, rmax):
    """0–100 composite so the UI ranks/filters instead of flooding on every gate hit.
    σ-magnitude (or a legacy rmax proxy when no baseline) + context bonus + 確認 + 持續性."""
    s = (min(sigma_mult, 6.0) / 6.0 * 40.0) if sigma_mult is not None \
        else (min(rmax, 3.0) / 3.0 * 30.0)
    s += {"breakout": 25.0, "counter": 20.0, "trend": 5.0, "range": 0.0}.get(ctx_class, 0.0)
    s += min(confs_n, 3) * 8.0
    if sustained:
        s += 8.0
    return int(round(max(0.0, min(100.0, s))))


def compute_baseline(closes, highs, lows, idx, up):
    """Characterize the ~10-min run BEFORE the spike bar at index `idx`:
    1-min-return σ (→ a per-stock adaptive threshold), trend regime (linreg slope +
    R²), the 10-bar range extreme (→ breakout), and whether the spike bar closed
    strong (持續性 — top/bottom 1/3 of its own range). Returns a dict; has_baseline
    is False when history is too short, in which case detect_spikes stays legacy."""
    out = {"has_baseline": False, "sigma_mult": None, "regime": None, "ctx_class": None,
           "context_label": None, "sustained": None, "breakout": False}
    h, l, c = highs[idx], lows[idx], closes[idx]
    if h > l:
        pos = (c - l) / (h - l)
        out["sustained"] = (pos >= 1 - SUSTAIN_RANGE_FRAC) if up else (pos <= SUSTAIN_RANGE_FRAC)
    else:
        out["sustained"] = True            # flat-range synthetic/illiquid bar → don't penalize
    if idx < BASELINE_MIN - 1 or idx < REGIME_WINDOW + 1:
        return out
    base = closes[idx - REGIME_WINDOW:idx]            # the 10 bars before the spike
    sigma = _ret_sigma(base)
    move = abs((closes[idx] / closes[idx - 1] - 1) * 100) if closes[idx - 1] else 0.0
    if sigma and sigma > 1e-9:
        out["sigma_mult"] = round(move / sigma, 1)
    slope, r2 = _linreg(base)
    mean_p = sum(base) / len(base)
    slope_pct = (slope / mean_p * 100) if mean_p else 0.0
    trending = abs(slope_pct) >= REGIME_SLOPE_PCT and r2 >= REGIME_R2
    regime = ("up" if slope_pct > 0 else "down") if trending else "range"
    rng_hi = max(highs[idx - REGIME_WINDOW:idx])
    rng_lo = min(lows[idx - REGIME_WINDOW:idx])
    breakout = (c > rng_hi * (1 + BREAKOUT_TOL)) if up else (c < rng_lo * (1 - BREAKOUT_TOL))
    ctx_class, label = _classify_context(up, regime, breakout)
    out.update({"has_baseline": True, "regime": regime, "ctx_class": ctx_class,
                "context_label": label, "breakout": breakout})
    return out


# ── Pure detection core (no network — unit-testable) ─────────────────────────
def detect_spikes(symbol, bars):
    """Scan the last WINDOW_MIN one-minute bars for the strongest 急拉/急殺.

    bars: oldest-first list of {t,o,h,l,c,v} (Alpaca 1-min). Returns a spike dict
    or None. Price-led: qualifies on |1-min| ≥ SPIKE_1M_PCT OR |3-min| ≥ SPIKE_3M_PCT.
    """
    if len(bars) < 5:
        return None
    closes = [b["c"] for b in bars]
    vols = [b.get("v", 0) for b in bars]
    times = [b["t"] for b in bars]
    n = len(bars)

    base = vols[max(0, n - AVG_LOOKBACK - WINDOW_MIN):max(1, n - WINDOW_MIN)]
    avg_vol = sum(base) / len(base) if base else None

    # 開盤 15 分鐘：門檻 ×OPEN_GATE_MULT（開盤每檔都在跳，不抬門檻就是雜訊機）。
    open_win = in_open_grace(times[-1])
    gate1 = SPIKE_1M_PCT * (OPEN_GATE_MULT if open_win else 1.0)
    gate3 = SPIKE_3M_PCT * (OPEN_GATE_MULT if open_win else 1.0)

    best = None
    for i in range(max(1, n - WINDOW_MIN), n):
        m1 = (closes[i] / closes[i - 1] - 1) * 100 if closes[i - 1] else 0.0
        m3 = (closes[i] / closes[i - 3] - 1) * 100 if i >= 3 and closes[i - 3] else 0.0
        r1, r3 = abs(m1) / gate1, abs(m3) / gate3
        if r1 < 1 and r3 < 1:
            continue
        sign = m1 if r1 >= r3 else m3
        mag = abs(m1) if r1 >= r3 else abs(m3)
        rmax = max(r1, r3)
        vmult = (vols[i] / avg_vol) if avg_vol else None
        cand = {"at": times[i], "idx": i, "m1": round(m1, 2), "m3": round(m3, 2),
                "mag": round(mag, 2), "rmax": rmax, "sign": sign,
                "vol_mult": round(vmult, 1) if vmult else None}
        if best is None or cand["rmax"] > best["rmax"]:
            best = cand
    if best is None:
        return None

    direction = "spike_up" if best["sign"] > 0 else "spike_down"
    up = direction == "spike_up"
    dir_zh = "急拉" if up else "急殺"
    vol_conf = best["vol_mult"] is not None and best["vol_mult"] >= VOL_MULT

    # ── MACD / KDJ confirmation on the same 1-min bars (reuse intraday helpers) ──
    highs = [b.get("h", b["c"]) for b in bars]
    lows = [b.get("l", b["c"]) for b in bars]
    macd = _ind.compute_macd(closes)
    kdj = _ind.compute_kdj(highs, lows, closes)

    def _macd_ok():
        if not macd:
            return False
        h = macd["hist"] if macd["hist"] is not None else 0
        return (macd["dif"] > macd["dea"] or macd["cross"] == "golden" or h > 0) if up \
            else (macd["dif"] < macd["dea"] or macd["cross"] == "death" or h < 0)

    def _kdj_ok():
        if not kdj:
            return False
        return (kdj["k"] > kdj["d"]) if up else (kdj["k"] < kdj["d"])

    confs = []
    if _macd_ok():
        confs.append("MACD")
    if _kdj_ok():
        confs.append("KDJ")
    if vol_conf:
        confs.append(f"量{best['vol_mult']}×")
    confirmed = len(confs) >= 2           # price spike + ≥2 of {MACD, KDJ, 量}

    # ── 10-min baseline: adaptive σ + regime 脈絡 + 持續性 + 複合分數 ──
    ctx = compute_baseline(closes, highs, lows, best["idx"], up)
    sigma_mult = ctx["sigma_mult"]
    ctx_class = ctx["ctx_class"]
    context_label = ctx["context_label"]
    sustained = ctx["sustained"]
    breakout = ctx["breakout"]
    score = _spike_score(sigma_mult, ctx_class, len(confs), sustained, best["rmax"])
    # Noise: a move small vs THIS stock's own recent σ, that merely rides the trend or
    # chops inside a range, with no MACD/KDJ/量 confirmation → demote (filtered upstream).
    # Breakout / counter-trend / confirmed moves are never suppressed.
    suppressed = bool(ctx["has_baseline"] and not confirmed and sigma_mult is not None
                      and sigma_mult < NOISE_SIGMA_K and ctx_class in ("trend", "range"))
    if suppressed:
        severity = "low"
    elif best["rmax"] >= 2 or confirmed or score >= 72:
        severity = "high"
    else:
        severity = "med"
    if open_win and severity == "high" and not confirmed:
        severity = "med"                   # 開盤窗：未經 MACD/KDJ/量 確認的最多 med

    label_txt = f"　{context_label}" if context_label else ""
    sig_txt = f"　σ{sigma_mult:.1f}×" if sigma_mult is not None else ""
    conf_txt = ("　" + " ".join("✓" + c for c in confs)) if confs else ""
    return {
        "symbol": symbol, "direction": direction, "dir_zh": dir_zh,
        "severity": severity, "m1": best["m1"], "m3": best["m3"], "mag": best["mag"],
        "vol_mult": best["vol_mult"], "vol_confirmed": vol_conf, "at": best["at"],
        "macd": macd, "kdj": kdj, "confirmations": confs, "confirmed": confirmed,
        "regime": ctx["regime"], "context_label": context_label, "ctx_class": ctx_class,
        "sigma_mult": sigma_mult, "sustained": sustained, "breakout": breakout,
        "score": score, "suppressed": suppressed, "open_grace": open_win,
        "text_zh": f"{symbol} {dir_zh}{label_txt} 1分{best['m1']:+.1f}% · 3分{best['m3']:+.1f}%{sig_txt}{conf_txt}",
    }


def detect_pump_fade(symbol, bars):
    """急拉擊殺 — a pump (急拉) immediately killed by a fade (急殺) that retraces most
    of it (拉高出貨/誘多被殺), or the mirror flush-then-reclaim (急殺反軋/誘空被軋).
    This pattern spans multiple bars, so detect_spikes (single-bar) structurally
    cannot represent it — it needs the rolling window. Returns a dict or None."""
    n = len(bars)
    if n < PF_PUMP_WIN + 2:
        return None
    closes = [b["c"] for b in bars]
    times = [b["t"] for b in bars]
    seg = range(n - min(n, PF_PUMP_WIN + PF_FADE_WIN + 1), n)
    best = None                            # (direction, a_i, mid_i, c_i, mag, retrace)

    def _better(c):
        return best is None or (c[4] * c[5]) > (best[4] * best[5])

    for mid in seg:                        # mid = pump peak (up) / flush trough (down)
        lo = max(0, mid - PF_PUMP_WIN)
        hi = min(n, mid + 1 + PF_FADE_WIN)
        if lo >= mid or mid + 1 >= hi:
            continue
        # up: trough→peak pump, then fade to the post-peak low
        trough = min(range(lo, mid + 1), key=lambda j: closes[j])
        pump = (closes[mid] / closes[trough] - 1) * 100 if closes[trough] else 0.0
        fade_i = min(range(mid + 1, hi), key=lambda j: closes[j])
        denom = closes[mid] - closes[trough]
        retr = (closes[mid] - closes[fade_i]) / denom if denom > 0 else 0.0
        if pump >= PF_PUMP_PCT and retr >= PF_FADE_RETRACE and _better(("up", trough, mid, fade_i, pump, retr)):
            best = ("up", trough, mid, fade_i, pump, retr)
        # down: peak→trough flush, then reclaim to the post-trough high
        peak = max(range(lo, mid + 1), key=lambda j: closes[j])
        drop = (closes[peak] / closes[mid] - 1) * 100 if closes[mid] else 0.0   # magnitude ≥0
        pop_i = max(range(mid + 1, hi), key=lambda j: closes[j])
        denom2 = closes[peak] - closes[mid]
        retr2 = (closes[pop_i] - closes[mid]) / denom2 if denom2 > 0 else 0.0
        if drop >= PF_PUMP_PCT and retr2 >= PF_FADE_RETRACE and _better(("down", peak, mid, pop_i, drop, retr2)):
            best = ("down", peak, mid, pop_i, drop, retr2)

    if best is None:
        return None
    direction, a_i, mid_i, c_i, mag, retr = best
    up = direction == "up"
    dir_zh = "急拉擊殺" if up else "急殺反軋"
    strong = mag >= PF_PUMP_PCT * 1.6 and retr >= 0.75
    return {
        "symbol": symbol, "kind": "pump_fade",
        "direction": "up_then_down" if up else "down_then_up", "dir_zh": dir_zh,
        "pump_pct": round(mag, 2), "retrace": round(retr, 2),
        "trough_at": times[a_i] if up else times[mid_i],
        "peak_at": times[mid_i] if up else times[a_i],
        "fade_at": times[c_i], "at": times[c_i], "last": round(closes[-1], 2),
        "severity": "high" if strong else "med",
        "text_zh": (f"{symbol} {dir_zh} 急拉+{mag:.1f}% 後回吐 {retr * 100:.0f}%" if up
                    else f"{symbol} {dir_zh} 急殺-{mag:.1f}% 後收回 {retr * 100:.0f}%"),
    }


def regime_context(bars):
    """Always-on 10-min posture for a ticker (regime + 距高 + 現分 σ 倍數), anchored at
    NOW (the last bar) rather than a spike. Powers the per-card 脈絡 line that replaces
    the noisy timestamped 訊號流: it answers 「這檔現在處於什麼中期狀態」for EVERY card,
    including the 尚無訊號 ones. Returns None when history < BASELINE_MIN bars."""
    n = len(bars)
    if n < BASELINE_MIN:
        return None
    closes = [b["c"] for b in bars]
    highs = [b.get("h", b["c"]) for b in bars]
    lows = [b.get("l", b["c"]) for b in bars]
    win = closes[-REGIME_WINDOW:]
    sigma = _ret_sigma(win)
    move = (closes[-1] / closes[-2] - 1) * 100 if n >= 2 and closes[-2] else 0.0
    sigma_mult = round(min(abs(move) / sigma, 50.0), 1) if sigma and sigma > 1e-9 else None
    slope, r2 = _linreg(win)
    mean_p = sum(win) / len(win)
    slope_pct = (slope / mean_p * 100) if mean_p else 0.0
    trending = abs(slope_pct) >= REGIME_SLOPE_PCT and r2 >= REGIME_R2
    regime = ("up" if slope_pct > 0 else "down") if trending else "range"
    win_hi = max(highs[-REGIME_WINDOW:])
    win_lo = min(lows[-REGIME_WINDOW:])
    return {
        "regime": regime,
        "regime_zh": {"up": "多頭", "down": "空頭", "range": "區間"}[regime],
        "slope_pct": round(slope_pct, 3), "r2": round(r2, 2),
        "dist_high": round((closes[-1] / win_hi - 1) * 100, 2) if win_hi else 0.0,
        "dist_low": round((closes[-1] / win_lo - 1) * 100, 2) if win_lo else 0.0,
        "sigma_mult": sigma_mult,
        "spark": [round(c, 2) for c in win],   # last 10 closes → front-end draws an SVG sparkline
    }


def latest_reading(symbol, bars):
    """Per-ticker live signal — the most-recent completed bar's move, regardless of
    threshold. Powers the always-visible 獨立訊號 chip so you can see a ticker that
    moved but stayed below the 急拉/急殺 gate. Returns a dict (never None when bars
    exist) so the UI can render every watched ticker."""
    if not bars:
        return {"symbol": symbol, "last": None, "m1": None, "m3": None,
                "at": None, "spiking": False, "direction": None}
    closes = [b["c"] for b in bars]
    n = len(closes)
    last = closes[-1]
    m1 = (closes[-1] / closes[-2] - 1) * 100 if n >= 2 and closes[-2] else 0.0
    m3 = (closes[-1] / closes[-4] - 1) * 100 if n >= 4 and closes[-4] else 0.0
    spiking = abs(m1) >= SPIKE_1M_PCT or abs(m3) >= SPIKE_3M_PCT
    drv = m1 if abs(m1) / SPIKE_1M_PCT >= abs(m3) / SPIKE_3M_PCT else m3
    return {"symbol": symbol, "last": round(last, 2),
            "m1": round(m1, 2), "m3": round(m3, 2), "at": bars[-1]["t"],
            "spiking": spiking,
            "direction": ("up" if drv > 0 else "down" if drv < 0 else "flat")}


def _kdj_cross_recent(highs, lows, closes, lookback=REVERSAL_LOOKBACK):
    """Freshest KDJ K×D cross within lookback → (cross, bars_ago, snapshot)."""
    n = len(closes)
    for ago in range(0, lookback):
        end = n - ago
        if end < 35:
            break
        r = _ind.compute_kdj(highs[:end], lows[:end], closes[:end])
        if r and r.get("cross"):
            return r["cross"], ago, r
    return None, None, None


def _macd_turn_recent(closes, lookback=REVERSAL_LOOKBACK):
    """Freshest MACD *bullish/bearish turn* within lookback. A "turn" is broader than
    a DIF×DEA cross (the SNDK case: MACD 轉正 without a clean cross yet) — it counts
    a golden/death cross, a histogram sign-flip, or a DIF zero-cross.
    Returns (direction 'up'|'down'|None, bars_ago, reason_zh)."""
    n = len(closes)
    for ago in range(0, lookback):
        end = n - ago
        if end < 36:
            break
        cur = _ind.compute_macd(closes[:end])
        prev = _ind.compute_macd(closes[:end - 1])
        if not cur:
            continue
        if cur.get("cross") == "golden":
            return "up", ago, "金叉"
        if cur.get("cross") == "death":
            return "down", ago, "死叉"
        if prev and cur.get("hist") is not None and prev.get("hist") is not None:
            if prev["hist"] <= 0 < cur["hist"]:
                return "up", ago, "柱翻正"
            if prev["hist"] >= 0 > cur["hist"]:
                return "down", ago, "柱翻負"
        if prev and cur.get("dif") is not None and prev.get("dif") is not None:
            if prev["dif"] <= 0 < cur["dif"]:
                return "up", ago, "DIF轉正"
            if prev["dif"] >= 0 > cur["dif"]:
                return "down", ago, "DIF轉負"
    return None, None, None


def detect_reversal(symbol, bars):
    """Momentum-turn reversal (both directions) — **雙確認 + σ 位移** gated.

    "正在反轉" requires, within the last REVERSAL_LOOKBACK bars, a fresh KDJ K×D
    cross **AND** a fresh MACD turn the SAME direction (single-source no longer
    qualifies: a 1-min KDJ crosses every few minutes in chop, which is exactly the
    「小小波動就報反轉」noise), AND a price displacement since the cross that is
    large vs THIS stock's own pre-cross σ (≥ REV_SIGMA_K×σ; fixed REV_MIN_DISP_PCT
    fallback when σ is unavailable/zero). Demoted crosses are NOT lost — they still
    show up in build_signal_flow's 訊號流.

    alert (the "趕快提示" moment) = displacement gate passed AND (KDJ zone 註記 or
    ≥ REV_ALERT_SIGMA σ). Returns a dict, or None when not reversing (→ the card
    shows 尚無訊號 rather than being hidden, since every ticker has a slot)."""
    if len(bars) < 40:           # need a stable MACD signal line (slow+signal ≈ 35)
        return None
    closes = [b["c"] for b in bars]
    highs = [b.get("h", b["c"]) for b in bars]
    lows = [b.get("l", b["c"]) for b in bars]

    kdj_cross, kdj_ago, kdj_snap = _kdj_cross_recent(highs, lows, closes)
    macd_dir, macd_ago, macd_reason = _macd_turn_recent(closes)
    kdj_dir = ("up" if kdj_cross == "golden" else "down") if kdj_cross else None
    if not (kdj_dir and macd_dir and kdj_dir == macd_dir):
        return None                                       # 單一來源 → 不算反轉

    cands = []                                            # (basis, dir, bars_ago, reason)
    cands.append(("KDJ", kdj_dir, kdj_ago, "金叉" if kdj_dir == "up" else "死叉"))
    cands.append(("MACD", macd_dir, macd_ago, macd_reason))
    cands.sort(key=lambda c: c[2])                        # freshest first
    fresh_dir = cands[0][1]
    up = fresh_dir == "up"

    # KDJ zone annotation: golden from oversold / death from overbought = better turn.
    zone = None
    if kdj_snap and kdj_snap.get("k_prev") is not None:
        kp = kdj_snap["k_prev"]
        if up and kp <= KDJ_OS:
            zone = "超賣翻揚"
        elif not up and kp >= KDJ_OB:
            zone = "超買翻落"

    if in_open_grace(bars[-1]["t"]) and not zone:
        return None                    # 開盤窗：沒有超買/超賣區註記的翻轉一律不報

    # σ 位移門檻：交叉完成前一根 close → 最新 close 的位移，比對交叉前 10 根的 σ。
    ci = len(closes) - 1 - cands[0][2]                    # 較新那個訊號所在的 bar
    prev_c = closes[ci - 1] if ci >= 1 else None
    disp = (closes[-1] / prev_c - 1) * 100 if prev_c else 0.0
    sigma = _ret_sigma(closes[max(0, ci - REGIME_WINDOW):ci])
    if sigma and sigma > 1e-9:
        mult = min(abs(disp) / sigma, 50.0)               # 上限同 regime_context，避免爆數字
        if mult < REV_SIGMA_K:
            return None                                   # 位移 < K×σ → 只是呼吸
    else:
        mult = None                                       # σ 算不出 → 退固定門檻
        if abs(disp) < REV_MIN_DISP_PCT:
            return None

    alert = bool(zone) or (mult is not None and mult >= REV_ALERT_SIGMA)
    return {
        "symbol": symbol, "direction": "up" if up else "down",
        "dir_zh": "反轉向上" if up else "反轉向下",
        "basis": [f"{b}{r}" for b, d, a, r in cands if d == fresh_dir],
        "alert": alert, "both": True, "bars_ago": cands[0][2], "zone": zone,
        "strength": "strong" if alert else "med",
        "disp_pct": round(disp, 2),
        "disp_sigma_mult": round(mult, 1) if mult is not None else None,
        "last": round(closes[-1], 2), "at": bars[-1]["t"],
        "macd": _ind.compute_macd(closes), "kdj": _ind.compute_kdj(highs, lows, closes),
    }


def apply_trend_context(rv, tr):
    """Demote a reversal that fights a strict MA-stack trend.

    A 1-min oscillator cross AGAINST a stacked trend is a bounce/pullback, not a
    turn — the MU 急跌 case where an oversold KDJ+MACD bounce printed 『反轉向上』
    on a stock making new lows under a strict bear stack. When rv and tr disagree
    on direction, mark the reversal counter-trend, relabel it 逆勢反彈/回測, and
    drop its alert so it no longer screams a turn (and the card falls back to the
    dominant trend). Aligned reversals, or reversals with no opposing trend, are
    left untouched. Mutates & returns rv (or None)."""
    if rv and tr and rv.get("direction") != tr.get("direction"):
        rv["counter_trend"] = True
        rv["dir_zh"] = "逆勢反彈" if rv.get("direction") == "up" else "逆勢回測"
        rv["alert"] = False
    return rv


def prev_reversal_map(prev_payload):
    """上一輪 payload → {symbol: reversal}（翻面冷卻用）。只在 generated_at 是**同一
    UTC 日**時有效——隔夜/跨日不套冷卻。缺檔或格式壞一律回 {}（等於不冷卻）。"""
    if not isinstance(prev_payload, dict):
        return {}
    g = _parse_ts(prev_payload.get("generated_at"))
    if g is None or g.astimezone(timezone.utc).date() != datetime.now(timezone.utc).date():
        return {}
    out = {}
    for rv in (prev_payload.get("reversals") or []):
        if isinstance(rv, dict) and rv.get("symbol"):
            out[rv["symbol"]] = rv
    return out


def flip_cooldown_ok(rv, prev_rv):
    """翻面冷卻（純函式）：上一輪同 symbol 的反轉方向**相反**且距最新 bar 不到
    REV_FLIP_COOLDOWN_MIN 分鐘 → 這種來回翻面幾乎都是盤整雜訊，要有 zone 註記或
    ≥ REV_FLIP_SIGMA 的 σ 位移才放行；否則整筆壓掉。其餘情況一律 True。"""
    if not rv or not prev_rv:
        return True
    if prev_rv.get("direction") == rv.get("direction"):
        return True
    t_prev, t_now = _parse_ts(prev_rv.get("at")), _parse_ts(rv.get("at"))
    if t_prev is None or t_now is None:
        return True
    if abs((t_now - t_prev).total_seconds()) / 60.0 >= REV_FLIP_COOLDOWN_MIN:
        return True
    if rv.get("zone"):
        return True
    m = rv.get("disp_sigma_mult")
    return m is not None and m >= REV_FLIP_SIGMA


def _read_prev_payload(path=None):
    """讀上一輪輸出（預設 Dashboard/intraday_spikes.json）。讀不到/格式壞 → None，絕不 raise。"""
    p = path or os.path.join(_ROOT, "Dashboard", "intraday_spikes.json")
    try:
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def _sma(values, n):
    """Simple moving average of the trailing n values (None if insufficient)."""
    if len(values) < n:
        return None
    return sum(values[-n:]) / n


def detect_trend(symbol, bars):
    """Sustained momentum-continuation (順勢續攻 / 順勢續跌) — a STATE detector.

    Unlike detect_spikes (violent 1%/min burst) and detect_reversal (a *fresh* KDJ/
    MACD cross in the last few bars), this fires while a clean trend simply PERSISTS:
        strict MA stack (ma5>ma10>ma20) + price riding the fast MA + ma5 rising +
        KDJ momentum intact (K>D, K≥floor) + price pinned to the window high.
    That is the 「均線多頭排列順勢創高」case a smooth grind would otherwise miss —
    no spike (each minute only +0.1~0.3%) and no fresh cross (the golden cross fired
    minutes ago). Bear side is the strict mirror. Returns a dict, or None.
    """
    ma_s, ma_m, ma_l = TREND_MA
    if len(bars) < ma_l + 1:
        return None
    closes = [b["c"] for b in bars]
    highs = [b.get("h", b["c"]) for b in bars]
    lows = [b.get("l", b["c"]) for b in bars]
    ma5, ma10, ma20 = _sma(closes, ma_s), _sma(closes, ma_m), _sma(closes, ma_l)
    ma5_prev = _sma(closes[:-1], ma_s)
    if None in (ma5, ma10, ma20, ma5_prev):
        return None
    kdj = _ind.compute_kdj(highs, lows, closes)
    if not kdj or kdj.get("k") is None or kdj.get("d") is None:
        return None
    k, d = kdj["k"], kdj["d"]
    last = closes[-1]
    win_high = max(highs[-TREND_HIGH_WINDOW:])
    win_low = min(lows[-TREND_HIGH_WINDOW:])

    # Strict bull stack: ma5>ma10>ma20, price ≥ ma5, ma5 rising, KDJ K>D & K≥floor,
    # price pinned to the window high. Bear side is the strict mirror.
    bull = (ma5 > ma10 > ma20 and last >= ma5 and ma5 > ma5_prev
            and k > d and k >= TREND_K_MIN and last >= win_high * (1 - TREND_HIGH_TOL))
    bear = (ma5 < ma10 < ma20 and last <= ma5 and ma5 < ma5_prev
            and k < d and k <= (100.0 - TREND_K_MIN) and last <= win_low * (1 + TREND_HIGH_TOL))
    if not bull and not bear:
        return None

    up = bull
    basis = ["均線多頭排列" if up else "均線空頭排列",
             f"KDJ K{k:.0f}{'>' if up else '<'}D{d:.0f}",
             "創高貼價" if up else "破低貼價"]
    strong = (k >= KDJ_OB) if up else (k <= KDJ_OS)   # decisively extended in-zone
    return {
        "symbol": symbol, "direction": "up" if up else "down",
        "dir_zh": "順勢續攻" if up else "順勢續跌",
        "ma": {str(ma_s): round(ma5, 2), str(ma_m): round(ma10, 2), str(ma_l): round(ma20, 2)},
        "k": round(k, 1), "d": round(d, 1), "basis": basis,
        "strength": "strong" if strong else "med",
        "last": round(last, 2), "at": bars[-1]["t"],
    }


def _collapse_flow(events, max_events):
    """De-noise the raw flow: a run of consecutive same-direction events collapses
    into ONE entry (the newest of the run) so the card reminds once instead of
    repeating ⤴ ⤴ ⤴. A spike anywhere in the run keeps the ⚡ icon; the merged
    labels stay as the hover tooltip. Returns newest-first, capped at max_events."""
    events.sort(key=lambda e: e["at"])           # oldest first for run-merging
    runs = []
    for e in events:
        if runs and runs[-1]["dir"] == e["dir"]:
            r = runs[-1]
            r["at"] = e["at"]                    # advance to the newest in the run
            if e["kind"] == "spike":             # a burst dominates the run's icon
                r["icon"], r["kind"] = e["icon"], e["kind"]
            elif r["kind"] != "spike":
                r["icon"], r["kind"] = e["icon"], e["kind"]
            if e["label"] not in r["_labels"]:
                r["_labels"].append(e["label"])
            r["count"] += 1
        else:
            runs.append({**e, "_labels": [e["label"]], "count": 1})
    for r in runs:
        r["label"] = " · ".join(r.pop("_labels"))
    runs.sort(key=lambda e: e["at"], reverse=True)
    return runs[:max_events]


def build_signal_flow(symbol, bars, window=30, max_events=3):
    """Reconstruct the recent signal *flow* (訊號流) for a ticker from the bar window:
    KDJ/MACD crosses + price spikes in the last `window` bars. Consecutive
    same-direction events are collapsed (see _collapse_flow) so the card reminds
    once rather than repeating the same arrow — newest first, capped at max_events.
    Stateless (derived from the same bars each poll). Returns [] when nothing fired."""
    n = len(bars)
    if n < 36:
        return []
    closes = [b["c"] for b in bars]
    highs = [b.get("h", b["c"]) for b in bars]
    lows = [b.get("l", b["c"]) for b in bars]
    times = [b["t"] for b in bars]
    events = []
    for i in range(max(35, n - window), n):
        cm = _ind.compute_macd(closes[:i + 1])
        if cm and cm.get("cross") == "golden":
            events.append({"at": times[i], "icon": "⤴", "kind": "macd", "dir": "up", "label": "MACD金叉"})
        elif cm and cm.get("cross") == "death":
            events.append({"at": times[i], "icon": "⤵", "kind": "macd", "dir": "down", "label": "MACD死叉"})
        kj = _ind.compute_kdj(highs[:i + 1], lows[:i + 1], closes[:i + 1])
        if kj and kj.get("cross") == "golden":
            events.append({"at": times[i], "icon": "⤴", "kind": "kdj", "dir": "up", "label": "KDJ金叉"})
        elif kj and kj.get("cross") == "death":
            events.append({"at": times[i], "icon": "⤵", "kind": "kdj", "dir": "down", "label": "KDJ死叉"})
        m1 = (closes[i] / closes[i - 1] - 1) * 100 if closes[i - 1] else 0.0
        if abs(m1) >= SPIKE_1M_PCT:
            events.append({"at": times[i], "icon": "⚡", "kind": "spike",
                           "dir": "up" if m1 > 0 else "down",
                           "label": f"急{'拉' if m1 > 0 else '殺'}{m1:+.1f}%"})
    return _collapse_flow(events, max_events)


# ── Alpaca REST (1-min bars, multi-symbol, free IEX feed) ────────────────────
def _fetch_alpaca_bars(symbols):
    """One multi-symbol call for the last ~90 min of 1-min bars (enough history
    for a stable 1-min MACD). Returns {symbol: [bars oldest-first]}. Never raises."""
    import requests
    key, sec = os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY")
    start = (datetime.now(timezone.utc) - timedelta(minutes=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {"symbols": ",".join(symbols), "timeframe": "1Min", "start": start,
              "feed": ALPACA_FEED, "limit": 10000, "sort": "asc", "adjustment": "raw"}
    out = {}
    try:
        r = requests.get(f"{ALPACA_DATA_HOST}/v2/stocks/bars", params=params, timeout=15,
                         headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec})
        r.raise_for_status()
        for sym, arr in (r.json().get("bars") or {}).items():
            out[sym] = [{"t": b["t"], "o": b.get("o"), "h": b.get("h"), "l": b.get("l"),
                         "c": b["c"], "v": b.get("v", 0)} for b in arr if b.get("c") is not None]
    except Exception as e:
        print(f"[spikes] alpaca fetch failed: {e}", file=sys.stderr)
    return out


def _market_open():
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


def build(prev_payload=None):
    """prev_payload = 上一輪的 payload，供翻面冷卻比對；None → 自己讀預設輸出檔
    （讀不到就當沒有，不冷卻）。dashboard_server 的 build() 無參數呼叫照常生效。"""
    wl = _load_watchlist()
    base = {"version": "1.6", "generated_at": datetime.now(timezone.utc).isoformat(),
            "feed": ALPACA_FEED, "market_open": _market_open(),
            "watchlist": wl, "watchlist_count": len(wl),
            "alerts": [], "reversals": [], "spikes": [], "trends": [],
            "pump_fades": [], "readings": []}
    if not (os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY")):
        return {**base, "_health": "no_alpaca_key", "_partial": True,
                "note": "設定 ALPACA_API_KEY / ALPACA_SECRET_KEY 後啟用（免費 IEX feed）"}
    if not wl:
        return {**base, "_health": "empty_watchlist", "_partial": True,
                "note": "spike_watchlist.txt 為空"}

    bars_by = _fetch_alpaca_bars(wl)
    prev_rev = prev_reversal_map(prev_payload if prev_payload is not None else _read_prev_payload())
    spikes, readings, reversals, alerts, trends, pump_fades = [], [], [], [], [], []
    for sym in wl:
        bars = bars_by.get(sym) or []
        rd = latest_reading(sym, bars)
        tr = detect_trend(sym, bars)
        rv = apply_trend_context(detect_reversal(sym, bars), tr)
        if not flip_cooldown_ok(rv, prev_rev.get(sym)):
            rv = None                      # 冷卻期內的低品質翻面 → 本輪不報
        rd["reversal"] = rv
        rd["trend"] = tr
        rd["context"] = regime_context(bars)   # always-on 10-min posture (sparkline + regime)
        rd["alert"] = bool(rv and rv.get("alert"))
        s = detect_spikes(sym, bars)
        rd["spike"] = s                    # attach (may be None / suppressed) for the card
        pf = detect_pump_fade(sym, bars)
        rd["pump_fade"] = pf
        readings.append(rd)
        if rv:
            reversals.append(rv)
            if rv.get("alert"):
                alerts.append(sym)
        if tr:
            trends.append(tr)
        if s and not s.get("suppressed"):  # suppressed = sub-σ noise → kept on card, off the list
            spikes.append(s)
        if pf:
            pump_fades.append(pf)
    reversals.sort(key=lambda r: (0 if r["strength"] == "strong" else 1, r["bars_ago"]))
    spikes.sort(key=lambda s: (-(s.get("score") or 0), 0 if s["severity"] == "high" else 1))
    pump_fades.sort(key=lambda p: (0 if p["severity"] == "high" else 1, -p["pump_pct"]))
    trends.sort(key=lambda t: (0 if t["strength"] == "strong" else 1, -abs(t["k"] - t["d"])))
    health = "ok" if bars_by else "fetch_failed"
    return {**base, "alerts": alerts, "reversals": reversals, "spikes": spikes,
            "trends": trends, "pump_fades": pump_fades, "readings": readings,
            "_health": health, "_partial": health != "ok"}


def _write_atomic(path, payload):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, allow_nan=False)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description="Individual-stock 急拉/急殺 fast lane (Alpaca 1-min)")
    ap.add_argument("--output", default=os.path.join(_ROOT, "Dashboard", "intraday_spikes.json"))
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args()

    try:
        payload = build()
    except Exception as e:
        print(f"[spikes] build failed: {e}", file=sys.stderr)
        payload = {"version": "1.6", "generated_at": datetime.now(timezone.utc).isoformat(),
                   "feed": ALPACA_FEED, "spikes": [], "_health": "error",
                   "_partial": True, "note": str(e)[:200]}
    _write_atomic(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not args.json_only:
        sys.stderr.write(f"\n→ Spikes {len(payload.get('spikes', []))} │ feed={payload.get('feed')} "
                         f"│ health={payload.get('_health')} → {args.output}\n")
    return 0 if payload.get("_health") in ("ok", "no_alpaca_key") else 2


if __name__ == "__main__":
    sys.exit(main())
