#!/usr/bin/env python3
"""quant-backtest — deterministic strategy backtest engine (V4.63.0).

Replays rule-based strategies over historical daily OHLCV and produces
equity curve / drawdown / per-year returns / trade list / parameter-sweep
grid as a single JSON artifact for Dashboard/backtest.html.

Templates (STRATEGIES registry, 11 個):
  momentum       — momentum-monitor 計分規則歷史重放 (short_squeeze 中性化 40)。
                   進場 score>=entry 且 Stage 2;出場 close<MA50 或 score<exit。
  ma_cross       — MA fast/slow 交叉。進場 fast 上穿 slow;出場 fast 下穿 slow。
  roc_trend      — 時間序列動能 (TSMOM):lookback 日報酬 > th% 持有,< 0 出場。
  donchian       — 唐奇安通道 (海龜):創 n_entry 日新高買,跌破 n_exit 日新低賣。
  obv_trend      — OBV > 其均線且 close > 價格均線;OBV 跌破均線出場。
  boll_reversion — 布林回歸:MA200 之上跌破下軌買,回到中軌賣。
  supertrend     — SuperTrend (ATR 通道翻轉) 方向多頭持有。
  triple_ma      — 三均線多頭排列 (fast>mid>MA200 且 close>fast);fast<mid 出場。
  rsi_reversion  — RSI14 < buy 超賣買進,> sell 出場。
  high_52w       — 收盤距 252 日高點 near% 內買進,跌落 exit% 出場。
  keltner        — 肯特納通道:close > EMA+k×ATR 突破買,跌破 EMA 出場。

訊號在完整抓取歷史上計算後才切回測窗 (V4.63.0 起) — 長 lookback
(MA200 / 252d) 不再吃掉窗口前段。

Discipline: 探索層。0 LLM。結果不進入 investment_protocol 決策。
FMP EOD 為拆股調整、非股息調整;宇宙以現在名單回看有存活者偏差 —
data_caveats 隨 artifact 輸出,UI 必須顯示。

Usage:
    python3 skills/quant-backtest/scripts/backtest.py NVDA
    python3 skills/quant-backtest/scripts/backtest.py NVDA --template momentum \
        --period 5y --entry-score 65 --exit-score 45 --cost-bps 10 --sweep
    python3 skills/quant-backtest/scripts/backtest.py AAPL --template ma_cross \
        --fast 50 --slow 200 --period 10y
    python3 skills/quant-backtest/scripts/backtest.py MSFT --template donchian \
        --params-json '{"n_entry": 20, "n_exit": 10}'

Exit codes: 0 ok / 1 fatal (no data, bad params) / 2 degraded (short window).
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "_shared"))
from technical_core import fetch_history  # noqa: E402

SCHEMA_VERSION = "v1.0"
DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "data"))
MOMENTUM_CACHE_DIR = os.path.join(REPO_ROOT, "skills", "momentum-monitor", "cache")

# 回測窗 → 抓取窗 (多抓 ≥200 交易日供 MA200 warmup)
PERIOD_FETCH = {"3y": "5y", "5y": "10y", "10y": "max"}
PERIOD_BARS = {"3y": 3 * 252, "5y": 5 * 252, "10y": 10 * 252}
MIN_WINDOW_BARS = 252  # 不足 1 年 → rc=2 degraded

DATA_CAVEATS = [
    "FMP EOD 為拆股調整、非股息調整;高股息標的長期報酬被低估",
    "momentum 模板的 short_squeeze 組件以中性 40 分重放(歷史 short interest 不可得)",
    "以現在的 ticker 回看歷史 → 存活者偏差;下市/被併股票不在樣本內",
    "探索層工具:結果不進入 investment_protocol 決策",
]

# ── momentum-monitor 計分規則逐日重放 (口徑同 momentum.py:_composite) ──
def replay_momentum_scores(hist: pd.DataFrame) -> pd.DataFrame:
    close, vol = hist["Close"], hist["Volume"]
    df = pd.DataFrame(index=hist.index)
    df["close"] = close
    df["high"], df["low"], df["volume"] = hist["High"], hist["Low"], vol

    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()
    df["ma50"] = ma50

    # 1. volume_flow — ratio = 今日量 / 前 20 日均量 (排除今日,同 _avg_prev)
    ratio = vol / vol.shift(1).rolling(20).mean()
    vol_score = pd.Series(25.0, index=df.index)
    vol_score[ratio >= 0.7] = 40
    vol_score[ratio >= 1.0] = 55
    vol_score[ratio >= 1.2] = 65
    vol_score[ratio >= 1.5] = 80
    vol_score[ratio >= 2.0] = 95
    vol_score[ratio.isna()] = 55  # 同 ratio_20d=None → neutral

    # 2. ma_stage — classify_stage 逐日 (Weinstein)
    stage = pd.Series("unknown", index=df.index)
    valid = ma20.notna() & ma50.notna() & ma200.notna()
    s2 = valid & (ma20 > ma50) & (ma50 > ma200) & (close > ma20)
    s4 = valid & (ma20 < ma50) & (ma50 < ma200) & (close < ma20)
    s3 = valid & ~s2 & ~s4 & (ma50 > ma200) & (close < ma20) & (ma20 < ma50)
    s1 = valid & ~s2 & ~s4 & ~s3
    stage[s1], stage[s3], stage[s4], stage[s2] = (
        "Stage 1 basing", "Stage 3 top", "Stage 4 downtrend", "Stage 2 uptrend")
    df["stage"] = stage
    ma_score = stage.map({
        "Stage 2 uptrend": 95, "Stage 1 basing": 65,
        "Stage 3 top": 40, "Stage 4 downtrend": 10, "unknown": 50}).astype(float)

    # 3. short_squeeze — 歷史不可得 → 中性 40 (同 live 版 pct=None fallback)
    sq_score = 40.0

    # 4. trend_acceleration — fresh cross (≤10d) 優先,否則 above_ma200 分級
    def days_since(event: pd.Series) -> np.ndarray:
        idx = np.arange(len(event), dtype=float)
        marked = np.where(event.to_numpy(), idx, np.nan)
        return idx - pd.Series(marked).ffill().to_numpy()  # NaN → 從未發生

    def cross_up(fast, slow):
        d_prev, d_curr = (fast - slow).shift(1), fast - slow
        return d_prev.notna() & d_curr.notna() & (d_prev <= 0) & (d_curr > 0)

    def cross_dn(fast, slow):
        d_prev, d_curr = (fast - slow).shift(1), fast - slow
        return d_prev.notna() & d_curr.notna() & (d_prev >= 0) & (d_curr < 0)

    fresh_g5020 = days_since(cross_up(ma20, ma50)) <= 10
    fresh_g50200 = days_since(cross_up(ma50, ma200)) <= 10
    fresh_death = (days_since(cross_dn(ma20, ma50)) <= 10) | \
                  (days_since(cross_dn(ma50, ma200)) <= 10)
    am200 = ((close / ma200 - 1) * 100).fillna(0).to_numpy()

    ta_score = np.full(len(df), 35.0)
    ta_score[am200 > 50] = 50
    ta_score[am200 > 100] = 30
    ta_score[(am200 > 0) & (am200 < 20)] = 60
    ta_score[(am200 >= 20) & (am200 <= 50)] = 75
    ta_score[fresh_death] = 15
    ta_score[fresh_g5020] = 80
    ta_score[fresh_g50200] = 95

    df["vol_score"], df["ma_score"], df["sq_score"], df["ta_score"] = (
        vol_score, ma_score, sq_score, ta_score)
    df["score"] = ((vol_score + ma_score + sq_score + ta_score) / 4).round(1)
    return df


# ── 共用指標 (訊號模板用;皆吃 replay 後的 df: close/high/low/volume) ──
def _atr(df: pd.DataFrame, n: int) -> pd.Series:
    """Wilder ATR。"""
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def _rsi(close: pd.Series, n: int) -> pd.Series:
    """Wilder RSI (口徑同 technical_core.rsi_14)。"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _supertrend_dir(df: pd.DataFrame, n: int, mult: float) -> pd.Series:
    """標準 SuperTrend 方向 (+1 多 / -1 空)。逐 bar 遞迴,無法向量化。"""
    c = df["close"].to_numpy()
    mid = ((df["high"] + df["low"]) / 2).to_numpy()
    band = (_atr(df, n) * mult).to_numpy()
    ub, lb = mid + band, mid - band
    fub, flb = ub.copy(), lb.copy()
    d = np.ones(len(c), dtype=int)
    for i in range(1, len(c)):
        if np.isnan(band[i]):
            continue
        if np.isnan(fub[i - 1]) or np.isnan(flb[i - 1]):
            fub[i], flb[i] = ub[i], lb[i]  # 第一根有效 bar 先鋪 band
            continue
        fub[i] = ub[i] if (ub[i] < fub[i - 1] or c[i - 1] > fub[i - 1]) else fub[i - 1]
        flb[i] = lb[i] if (lb[i] > flb[i - 1] or c[i - 1] < flb[i - 1]) else flb[i - 1]
        if d[i - 1] == 1:
            d[i] = -1 if c[i] < flb[i] else 1
        else:
            d[i] = 1 if c[i] > fub[i] else -1
    return pd.Series(d, index=df.index)


# ── 訊號模板 ─────────────────────────────────────────────────────────
def momentum_signals(df: pd.DataFrame, entry_score: float, exit_score: float):
    entry = (df["score"] >= entry_score) & (df["stage"] == "Stage 2 uptrend")
    exit_ = (df["close"] < df["ma50"]) | (df["score"] < exit_score)
    return entry, exit_


def ma_cross_signals(df: pd.DataFrame, fast: int, slow: int):
    f = df["close"].rolling(fast).mean()
    s = df["close"].rolling(slow).mean()
    ok = f.notna() & s.notna()
    entry = ok & (f > s)
    exit_ = ok & (f < s)
    return entry, exit_


def roc_trend_signals(df: pd.DataFrame, lookback: int, entry_th_pct: float):
    roc = df["close"].pct_change(lookback) * 100
    return roc > entry_th_pct, roc < 0


def donchian_signals(df: pd.DataFrame, n_entry: int, n_exit: int):
    c = df["close"]
    hh = c.rolling(n_entry).max().shift(1)
    ll = c.rolling(n_exit).min().shift(1)
    return c > hh, c < ll


def obv_trend_signals(df: pd.DataFrame, obv_ma: int, price_ma: int):
    c = df["close"]
    obv = (np.sign(c.diff().fillna(0)) * df["volume"]).cumsum()
    om = obv.rolling(obv_ma).mean()
    pm = c.rolling(price_ma).mean()
    entry = pm.notna() & om.notna() & (obv > om) & (c > pm)
    exit_ = om.notna() & (obv < om)
    return entry, exit_


def boll_reversion_signals(df: pd.DataFrame, n: int, k: float):
    c = df["close"]
    m, sd = c.rolling(n).mean(), c.rolling(n).std()
    m200 = c.rolling(200).mean()
    entry = m200.notna() & (c > m200) & (c < m - k * sd)
    exit_ = m.notna() & (c >= m)
    return entry, exit_


def supertrend_signals(df: pd.DataFrame, n: int, mult: float):
    d = _supertrend_dir(df, n, mult)
    return d == 1, d == -1


def triple_ma_signals(df: pd.DataFrame, fast: int, mid: int):
    c = df["close"]
    f, m = c.rolling(fast).mean(), c.rolling(mid).mean()
    m200 = c.rolling(200).mean()
    ok = m200.notna()
    entry = ok & (f > m) & (m > m200) & (c > f)
    exit_ = f.notna() & m.notna() & (f < m)
    return entry, exit_


def rsi_reversion_signals(df: pd.DataFrame, buy_th: float, sell_th: float):
    r = _rsi(df["close"], 14)
    return r < buy_th, r > sell_th


def high_52w_signals(df: pd.DataFrame, near_pct: float, exit_pct: float):
    c = df["close"]
    hh = c.rolling(252).max()
    ok = hh.notna()
    entry = ok & (c >= (1 - near_pct / 100) * hh)
    exit_ = ok & (c <= (1 - exit_pct / 100) * hh)
    return entry, exit_


def keltner_signals(df: pd.DataFrame, n: int, mult: float):
    c = df["close"]
    ema = c.ewm(span=n, adjust=False).mean()
    upper = ema + mult * _atr(df, 10)
    entry = upper.notna() & (c > upper)
    exit_ = c < ema
    return entry, exit_


def _validate_fast_slow(p: dict, fast_key: str, slow_key: str):
    if p[fast_key] >= p[slow_key]:
        return f"{fast_key}({p[fast_key]}) must be < {slow_key}({p[slow_key]})"
    return None


# 模板 registry — label 供 artifact/log,params 為預設值 (型別即轉型規則),
# sweep 為參數掃描格,invalid 為 sweep 格內無效組合判定。
STRATEGIES = {
    "momentum": {
        "label": "動能重放",
        "signals": lambda df, p: momentum_signals(df, p["entry_score"], p["exit_score"]),
        "params": {"entry_score": 65.0, "exit_score": 45.0},
        "sweep": {"x": ("entry_score", [55, 60, 65, 70, 75, 80]),
                  "y": ("exit_score", [30, 35, 40, 45, 50, 55])},
    },
    "ma_cross": {
        "label": "均線交叉",
        "signals": lambda df, p: ma_cross_signals(df, p["fast"], p["slow"]),
        "params": {"fast": 50, "slow": 200},
        "sweep": {"x": ("fast", [10, 20, 50]), "y": ("slow", [100, 150, 200])},
        "validate": lambda p: _validate_fast_slow(p, "fast", "slow"),
    },
    "roc_trend": {
        "label": "時序動能 TSMOM",
        "signals": lambda df, p: roc_trend_signals(df, p["lookback"], p["entry_th_pct"]),
        "params": {"lookback": 126, "entry_th_pct": 0.0},
        "sweep": {"x": ("lookback", [63, 126, 189, 252]),
                  "y": ("entry_th_pct", [0, 2, 5])},
    },
    "donchian": {
        "label": "唐奇安通道",
        "signals": lambda df, p: donchian_signals(df, p["n_entry"], p["n_exit"]),
        "params": {"n_entry": 20, "n_exit": 10},
        "sweep": {"x": ("n_entry", [10, 20, 40, 55]), "y": ("n_exit", [5, 10, 20])},
    },
    "obv_trend": {
        "label": "OBV 量能趨勢",
        "signals": lambda df, p: obv_trend_signals(df, p["obv_ma"], p["price_ma"]),
        "params": {"obv_ma": 20, "price_ma": 50},
        "sweep": {"x": ("obv_ma", [10, 20, 50]), "y": ("price_ma", [20, 50, 100])},
    },
    "boll_reversion": {
        "label": "布林回歸",
        "signals": lambda df, p: boll_reversion_signals(df, p["n"], p["k"]),
        "params": {"n": 20, "k": 2.0},
        "sweep": {"x": ("n", [10, 20, 30]), "y": ("k", [1.5, 2.0, 2.5])},
    },
    "supertrend": {
        "label": "SuperTrend",
        "signals": lambda df, p: supertrend_signals(df, p["n"], p["mult"]),
        "params": {"n": 10, "mult": 3.0},
        "sweep": {"x": ("n", [7, 10, 14]), "y": ("mult", [2.0, 3.0, 4.0])},
    },
    "triple_ma": {
        "label": "三均線多頭排列",
        "signals": lambda df, p: triple_ma_signals(df, p["fast"], p["mid"]),
        "params": {"fast": 20, "mid": 50},
        "sweep": {"x": ("fast", [10, 20, 30]), "y": ("mid", [50, 100, 150])},
        "validate": lambda p: _validate_fast_slow(p, "fast", "mid"),
    },
    "rsi_reversion": {
        "label": "RSI 超賣反轉",
        "signals": lambda df, p: rsi_reversion_signals(df, p["buy_th"], p["sell_th"]),
        "params": {"buy_th": 30.0, "sell_th": 55.0},
        "sweep": {"x": ("buy_th", [20, 25, 30, 35]), "y": ("sell_th", [50, 55, 60, 65])},
    },
    "high_52w": {
        "label": "52週新高動能",
        "signals": lambda df, p: high_52w_signals(df, p["near_pct"], p["exit_pct"]),
        "params": {"near_pct": 5.0, "exit_pct": 15.0},
        "sweep": {"x": ("near_pct", [2, 5, 10]), "y": ("exit_pct", [10, 15, 20])},
    },
    "keltner": {
        "label": "肯特納通道突破",
        "signals": lambda df, p: keltner_signals(df, p["n"], p["mult"]),
        "params": {"n": 20, "mult": 2.0},
        "sweep": {"x": ("n", [10, 20, 30]), "y": ("mult", [1.5, 2.0, 2.5])},
    },
}


# ── 回測核心 ─────────────────────────────────────────────────────────
def run_strategy(df: pd.DataFrame, entry: pd.Series, exit_: pd.Series,
                 cost_bps: float) -> dict:
    """State machine → position;訊號日收盤成交,次日起吃報酬,單邊 cost_bps。"""
    pos = np.zeros(len(df), dtype=int)
    holding = False
    ent, ext = entry.to_numpy(), exit_.to_numpy()
    for i in range(len(df)):
        if holding and ext[i]:
            holding = False
        elif not holding and ent[i]:
            holding = True
        pos[i] = int(holding)
    pos = pd.Series(pos, index=df.index)

    ret = df["close"].pct_change().fillna(0)
    turns = pos.diff().abs().fillna(pos.iloc[0] if len(pos) else 0)
    strat_ret = pos.shift(1).fillna(0) * ret - turns * cost_bps / 10000
    eq_strat = (1 + strat_ret).cumprod()
    eq_bh = (1 + ret).cumprod()
    dd = eq_strat / eq_strat.cummax() - 1
    dd_bh = eq_bh / eq_bh.cummax() - 1
    years = max(len(df) / 252, 1e-9)

    std = strat_ret.std()
    sharpe = float(strat_ret.mean() / std * np.sqrt(252)) if std > 0 else 0.0
    std_bh = ret.std()
    sharpe_bh = float(ret.mean() / std_bh * np.sqrt(252)) if std_bh > 0 else 0.0

    # 交易清單 (成本已含: 進出各一次)
    trades, entry_i = [], None
    pv = pos.to_numpy()
    for i in range(len(df)):
        if pv[i] == 1 and (i == 0 or pv[i - 1] == 0):
            entry_i = i
        elif pv[i] == 0 and i > 0 and pv[i - 1] == 1 and entry_i is not None:
            p_in, p_out = float(df["close"].iloc[entry_i]), float(df["close"].iloc[i])
            trades.append({
                "entry": str(df.index[entry_i].date()), "exit": str(df.index[i].date()),
                "days": i - entry_i,
                "pct": round((p_out / p_in - 1) * 100 - 2 * cost_bps / 100, 2)})
            entry_i = None
    if entry_i is not None:  # 未平倉
        p_in = float(df["close"].iloc[entry_i])
        trades.append({
            "entry": str(df.index[entry_i].date()), "exit": "(open)",
            "days": len(df) - 1 - entry_i,
            "pct": round((float(df["close"].iloc[-1]) / p_in - 1) * 100
                         - cost_bps / 100, 2)})

    wins = [t for t in trades if t["pct"] > 0]
    yearly_df = pd.DataFrame({"strat": strat_ret, "bh": ret}, index=df.index) \
        .groupby(df.index.year).apply(lambda g: ((1 + g).prod() - 1) * 100).round(1)

    return {
        "metrics": {
            "total_return_pct": round(float(eq_strat.iloc[-1] - 1) * 100, 1),
            "bh_total_return_pct": round(float(eq_bh.iloc[-1] - 1) * 100, 1),
            "cagr_pct": round((float(eq_strat.iloc[-1]) ** (1 / years) - 1) * 100, 1),
            "bh_cagr_pct": round((float(eq_bh.iloc[-1]) ** (1 / years) - 1) * 100, 1),
            "sharpe": round(sharpe, 2),
            "bh_sharpe": round(sharpe_bh, 2),
            "max_dd_pct": round(float(dd.min()) * 100, 1),
            "bh_max_dd_pct": round(float(dd_bh.min()) * 100, 1),
            "exposure_pct": round(float(pos.mean()) * 100, 1),
            "n_trades": len(trades),
            "win_rate_pct": round(len(wins) / len(trades) * 100, 1) if trades else None,
        },
        "yearly": {str(y): {"strat": float(r["strat"]), "bh": float(r["bh"])}
                   for y, r in yearly_df.iterrows()},
        "trades": trades,
        "pos": pos,
        "eq_strat": eq_strat,
        "eq_bh": eq_bh,
        "drawdown": dd,
        "drawdown_bh": dd_bh,
    }


def build_signals(template: str, df: pd.DataFrame, params: dict):
    if template not in STRATEGIES:
        raise ValueError(f"unknown template: {template}")
    return STRATEGIES[template]["signals"](df, params)


def resolve_params(template: str, overrides: dict) -> dict:
    """registry 預設值 + overrides;型別以預設值為準轉型,未知 key 忽略。"""
    params = dict(STRATEGIES[template]["params"])
    for k, v in (overrides or {}).items():
        if k in params:
            params[k] = type(params[k])(v)
    return params


def run_sweep(template: str, full: pd.DataFrame, window_bars: int,
              params: dict, cost_bps: float) -> dict:
    """x×y 參數格 → 每格 4 指標。訊號在完整歷史上算,再切窗回測。
    看「高原」不是「尖峰」— 只在單一參數點賺錢 = 曲線擬合。"""
    spec = STRATEGIES[template]["sweep"]
    invalid_fn = STRATEGIES[template].get("validate")
    (x_name, xs), (y_name, ys) = spec["x"], spec["y"]
    df = full.iloc[-window_bars:]
    cells = []
    for yv in ys:
        for xv in xs:
            p = {**params, x_name: xv, y_name: yv}
            if invalid_fn and invalid_fn(p):
                cells.append({"x": xv, "y": yv, "invalid": True})
                continue
            entry, exit_ = build_signals(template, full, p)
            r = run_strategy(df, entry.iloc[-window_bars:],
                             exit_.iloc[-window_bars:], cost_bps)
            m = r["metrics"]
            cells.append({"x": xv, "y": yv, "cagr_pct": m["cagr_pct"],
                          "sharpe": m["sharpe"], "max_dd_pct": m["max_dd_pct"],
                          "n_trades": m["n_trades"]})
    return {"x_name": x_name, "y_name": y_name, "xs": xs, "ys": ys, "cells": cells}


# ── momentum 重放 vs live cache 口徑驗證 ──────────────────────────────
def validate_vs_live_cache(ticker: str, full: pd.DataFrame):
    path = os.path.join(MOMENTUM_CACHE_DIR, f"momentum_{ticker}.json")
    if not os.path.exists(path):
        return None
    try:
        cache = json.load(open(path, encoding="utf-8"))
        comp = cache["momentum_composite"]["components"]
        cache_date = cache["generated_at"][:10]
        row = full[full.index.strftime("%Y-%m-%d") == cache_date]
        if not len(row):
            return None
        r = row.iloc[0]
        return {
            "cache_date": cache_date,
            "ma_stage_match": bool(float(r["ma_score"]) == comp["ma_stage"]),
            "trend_accel_match": bool(float(r["ta_score"]) == comp["trend_acceleration"]),
            "stage_match": bool(str(r["stage"]) == cache["ma_structure"]["stage"]),
            "note": "volume 分數不比對(live 為盤中投影量);short_squeeze 重放固定 40",
        }
    except Exception as e:
        return {"error": str(e)}


# ── Main ────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="quant-backtest deterministic engine")
    ap.add_argument("ticker")
    ap.add_argument("--template", default="momentum", choices=list(STRATEGIES))
    ap.add_argument("--period", default="5y", choices=list(PERIOD_BARS))
    ap.add_argument("--entry-score", type=float, default=None,
                    help="momentum 舊參數 (相容)")
    ap.add_argument("--exit-score", type=float, default=None)
    ap.add_argument("--fast", type=int, default=None, help="ma_cross 舊參數 (相容)")
    ap.add_argument("--slow", type=int, default=None)
    ap.add_argument("--params-json", default=None,
                    help='通用參數 JSON,如 \'{"n_entry": 20, "n_exit": 10}\'')
    ap.add_argument("--cost-bps", type=float, default=10)
    ap.add_argument("--sweep", action="store_true", default=True,
                    help="參數掃描格 (預設開)")
    ap.add_argument("--no-sweep", dest="sweep", action="store_false")
    ap.add_argument("--output-dir", default=DATA_DIR)
    args = ap.parse_args()

    ticker = args.ticker.strip().upper()
    legacy = {"entry_score": args.entry_score, "exit_score": args.exit_score,
              "fast": args.fast, "slow": args.slow}
    overrides = {k: v for k, v in legacy.items() if v is not None}
    if args.params_json:
        try:
            overrides.update(json.loads(args.params_json))
        except (json.JSONDecodeError, TypeError) as e:
            print(f"[fatal] bad --params-json: {e}")
            sys.exit(1)
    try:
        params = resolve_params(args.template, overrides)
    except (ValueError, TypeError) as e:
        print(f"[fatal] bad params for {args.template}: {e}")
        sys.exit(1)
    err = STRATEGIES[args.template].get("validate", lambda p: None)(params)
    if err:
        print(f"[fatal] {err}")
        sys.exit(1)

    t0 = time.time()
    try:
        hist, _ = fetch_history(ticker, period=PERIOD_FETCH[args.period])
    except Exception as e:
        print(f"[fatal] fetch failed for {ticker}: {e}")
        sys.exit(1)
    if hist is None or len(hist) < 60:
        print(f"[fatal] insufficient history for {ticker}: "
              f"{0 if hist is None else len(hist)} bars")
        sys.exit(1)
    fetch_sec = round(time.time() - t0, 2)
    print(f"[fetch] {ticker} {len(hist)} bars "
          f"({hist.index[0].date()} → {hist.index[-1].date()}) in {fetch_sec}s")

    t1 = time.time()
    full = replay_momentum_scores(hist)  # ma_cross 也要 close/ma50 欄位,重用
    validation = validate_vs_live_cache(ticker, full) \
        if args.template == "momentum" else None

    bars = min(PERIOD_BARS[args.period], len(full))
    df = full.iloc[-bars:].copy()
    degraded = len(df) < MIN_WINDOW_BARS
    if degraded:
        print(f"[warn] window only {len(df)} bars (<{MIN_WINDOW_BARS}) — degraded")

    # 訊號在完整歷史上計算 (warmup 不吃窗口),再切窗回測
    entry, exit_ = build_signals(args.template, full, params)
    result = run_strategy(df, entry.iloc[-bars:], exit_.iloc[-bars:], args.cost_bps)
    sweep = run_sweep(args.template, full, bars, params, args.cost_bps) \
        if args.sweep else None
    compute_sec = round(time.time() - t1, 3)
    print(f"[compute] {len(full)} days replay + backtest"
          f"{' + sweep' if sweep else ''} in {compute_sec}s")

    out = {
        "schema_version": SCHEMA_VERSION,
        "ticker": ticker,
        "template": args.template,
        "template_label": STRATEGIES[args.template]["label"],
        "params": params,
        "cost_bps_per_side": args.cost_bps,
        "period": args.period,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window": {"from": str(df.index[0].date()), "to": str(df.index[-1].date()),
                   "bars": len(df)},
        "degraded": degraded,
        "timing": {"fetch_sec": fetch_sec, "compute_sec": compute_sec},
        "data_caveats": DATA_CAVEATS,
        "validation_vs_live_cache": validation,
        "metrics": result["metrics"],
        "yearly": result["yearly"],
        "trades": result["trades"],
        "sweep": sweep,
        "series": {
            "dates": [str(d.date()) for d in df.index],
            "close": [round(float(v), 2) for v in df["close"]],
            "eq_strat": [round(float(v), 4) for v in result["eq_strat"]],
            "eq_bh": [round(float(v), 4) for v in result["eq_bh"]],
            "score": [float(v) for v in df["score"]],
            "pos": [int(v) for v in result["pos"]],
            "drawdown": [round(float(v) * 100, 2) for v in result["drawdown"]],
            "drawdown_bh": [round(float(v) * 100, 2) for v in result["drawdown_bh"]],
        },
    }

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, f"{ticker}_{args.template}.json")
    tmp = f"{out_path}.tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False)
    os.replace(tmp, out_path)
    print(f"[write] {out_path}")

    m = result["metrics"]
    print(f"[done] {ticker} {args.template} {args.period}: "
          f"strat {m['total_return_pct']:+.1f}% (B&H {m['bh_total_return_pct']:+.1f}%) "
          f"| Sharpe {m['sharpe']} | MaxDD {m['max_dd_pct']}% "
          f"| {m['n_trades']} trades")
    sys.exit(2 if degraded else 0)


if __name__ == "__main__":
    main()
