#!/usr/bin/env python3
"""quant-backtest golden-fixture 回歸測試 (V4.63.0) — 改 engine 後必跑 rc=0。

合成 OHLCV(無網路),斷言:
  1. momentum 重放組件分數 (stage / vol / ta 的關鍵轉折點)
  2. run_strategy 的持倉狀態機 / 成本 / 交易萃取
  3. 手算小案例的 metrics 數值
  4. ma_cross 訊號 + sweep 格形狀 / invalid cell
  5. STRATEGIES registry 完整性 + resolve_params 轉型
  6. 新模板 (donchian / supertrend / rsi_reversion / high_52w / triple_ma)
     合成序列決定性行為
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import (  # noqa: E402
    STRATEGIES, build_signals, resolve_params,
    replay_momentum_scores, momentum_signals, ma_cross_signals,
    run_strategy, run_sweep,
)

FAILURES = []


def check(name, cond):
    status = "ok" if cond else "FAIL"
    print(f"  [{status}] {name}")
    if not cond:
        FAILURES.append(name)


def synth_hist(n=600, seed_trend="up"):
    """確定性合成序列: 前段平盤 → 後段趨勢。量能固定 1e6,第 550 根 3 倍量。"""
    idx = pd.bdate_range("2022-01-03", periods=n)
    if seed_trend == "up":
        flat = np.full(300, 100.0)
        trend = 100 * (1.003 ** np.arange(1, n - 300 + 1))
        close = np.concatenate([flat, trend])
    else:
        close = np.full(n, 100.0)
    vol = np.full(n, 1_000_000.0)
    if n > 550:
        vol[550] = 3_000_000.0  # HEAVY spike → ratio 3.0 → vol_score 95
    return pd.DataFrame({
        "Open": close, "High": close * 1.01, "Low": close * 0.99,
        "Close": close, "Volume": vol}, index=idx)


print("— 1. momentum 重放組件 —")
hist = synth_hist()
df = replay_momentum_scores(hist)

# 平盤段尾 (i=299): 三 MA 全 100、close=100 → 非 Stage2/4;ma50>ma200 不成立
# → Stage 1 basing (65 分)
check("平盤段 stage = Stage 1 basing", df["stage"].iloc[299] == "Stage 1 basing")
check("平盤段 ma_score = 65", df["ma_score"].iloc[299] == 65)

# 趨勢確立後 (尾端): ma20>ma50>ma200 且 close>ma20 → Stage 2 (95 分)
check("趨勢段 stage = Stage 2 uptrend", df["stage"].iloc[-1] == "Stage 2 uptrend")
check("趨勢段 ma_score = 95", df["ma_score"].iloc[-1] == 95)

# 量能: 平量日 ratio=1.0 → 55;spike 日 ratio=3.0 → 95
check("平量日 vol_score = 55", df["vol_score"].iloc[299] == 55)
check("spike 日 vol_score = 95", df["vol_score"].iloc[550] == 95)

# sq 永遠中性 40
check("sq_score 恆為 40", (df["sq_score"] == 40).all())

# 上升趨勢起步後必有 golden cross 20/50 → 出現過 ta_score=80 或 95
check("趨勢啟動出現 fresh golden cross ta>=80", (df["ta_score"].iloc[300:400] >= 80).any())

# composite = 四組件均值
i = 299
expect = round((df["vol_score"].iloc[i] + df["ma_score"].iloc[i]
                + 40 + df["ta_score"].iloc[i]) / 4, 1)
check("composite = 組件均值", df["score"].iloc[i] == expect)

print("— 2. 持倉狀態機 / 交易萃取 —")
# 手工 5 根: entry 於第 1 根,exit 於第 3 根
tiny = pd.DataFrame({"close": [100.0, 100.0, 110.0, 110.0, 120.0]},
                    index=pd.bdate_range("2024-01-01", periods=5))
entry = pd.Series([False, True, False, False, False], index=tiny.index)
exit_ = pd.Series([False, False, False, True, False], index=tiny.index)
r = run_strategy(tiny, entry, exit_, cost_bps=0)
check("pos = [0,1,1,0,0]", list(r["pos"]) == [0, 1, 1, 0, 0])
check("1 筆交易", len(r["trades"]) == 1)
check("交易報酬 = +10%", r["trades"][0]["pct"] == 10.0)
check("持有 2 天", r["trades"][0]["days"] == 2)
# 策略只吃第 2→3 根的 +10%: eq 尾值 = 1.10
check("權益尾值 = 1.10", abs(r["eq_strat"].iloc[-1] - 1.10) < 1e-9)
# B&H 全程 100→120 = +20%
check("B&H 總報酬 = 20%", r["metrics"]["bh_total_return_pct"] == 20.0)
check("exposure = 40%", r["metrics"]["exposure_pct"] == 40.0)
check("win_rate = 100%", r["metrics"]["win_rate_pct"] == 100.0)

# 成本: 100bps/side → 進出共扣 2%;交易 pct = 10 - 2 = 8
r2 = run_strategy(tiny, entry, exit_, cost_bps=100)
check("成本入交易報酬 (10-2=8)", r2["trades"][0]["pct"] == 8.0)
check("成本入權益曲線", r2["eq_strat"].iloc[-1] < r["eq_strat"].iloc[-1])

# 未平倉交易
exit_none = pd.Series(False, index=tiny.index)
r3 = run_strategy(tiny, entry, exit_none, cost_bps=0)
check("未平倉 exit=(open)", r3["trades"][-1]["exit"] == "(open)")
check("未平倉報酬 = +20%", r3["trades"][-1]["pct"] == 20.0)

print("— 3. momentum 訊號閘 —")
entry_m, exit_m = momentum_signals(df, 65, 45)
check("Stage2 以外不進場", not (entry_m & (df["stage"] != "Stage 2 uptrend")).any())
check("score<45 必出場", bool((exit_m | (df["score"] >= 45)).all()))

print("— 4. ma_cross + sweep —")
entry_c, exit_c = ma_cross_signals(df, 20, 50)
check("ma_cross 趨勢段持有", bool(entry_c.iloc[-1]))
check("ma_cross entry/exit 互斥", not (entry_c & exit_c).any())

sweep = run_sweep("momentum", df, 252, {"entry_score": 65, "exit_score": 45}, 10)
check("momentum sweep 6x6 = 36 格", len(sweep["cells"]) == 36)
check("sweep 格含 sharpe", all("sharpe" in c or c.get("invalid") for c in sweep["cells"]))

sweep2 = run_sweep("ma_cross", df, 252, {"fast": 50, "slow": 200}, 10)
check("ma_cross sweep 3x3 = 9 格", len(sweep2["cells"]) == 9)
check("ma_cross 格全有效 (fast 恆 < slow)",
      all(not c.get("invalid") for c in sweep2["cells"]))

print("— 5. STRATEGIES registry —")
check("registry 共 11 模板", len(STRATEGIES) == 11)
for key, spec in STRATEGIES.items():
    sweep_keys = {spec["sweep"]["x"][0], spec["sweep"]["y"][0]}
    check(f"{key}: label/params/sweep 完整且 sweep 參數 ⊆ params",
          bool(spec.get("label")) and callable(spec["signals"])
          and sweep_keys <= set(spec["params"]))
check("resolve_params 轉型 str→int", resolve_params("donchian", {"n_entry": "40"})["n_entry"] == 40)
check("resolve_params 忽略未知 key", "bogus" not in resolve_params("donchian", {"bogus": 1}))
check("resolve_params 保留預設", resolve_params("supertrend", {})["mult"] == 3.0)
check("triple_ma validate 擋 fast>=mid",
      STRATEGIES["triple_ma"]["validate"]({"fast": 50, "mid": 50}) is not None)

print("— 6. 新模板決定性行為 —")
# 全模板煙霧測試: 訊號為 bool Series、與 df 等長、entry/exit 不同時為真
for key in STRATEGIES:
    p = resolve_params(key, {})
    e, x = build_signals(key, df, p)
    check(f"{key}: 訊號長度一致且 entry/exit 互斥",
          len(e) == len(df) and len(x) == len(df) and not (e & x).any())

# donchian: 平盤段 (等值序列) 創不了新高 → 不進場;趨勢段每天創新高 → 持續進場
e_d, x_d = build_signals("donchian", df, {"n_entry": 20, "n_exit": 10})
check("donchian 平盤段不進場", not e_d.iloc[100:299].any())
check("donchian 趨勢段進場", bool(e_d.iloc[-1]))

# supertrend: 趨勢確立尾端方向為多
e_s, x_s = build_signals("supertrend", df, {"n": 10, "mult": 3.0})
check("supertrend 趨勢尾端持多", bool(e_s.iloc[-1]) and not bool(x_s.iloc[-1]))

# rsi_reversion: 純上漲段 avg_loss=0 → RSI=NaN → 不進不出 (真實資料必有跌日);
# 加微幅鋸齒的上漲序列 → RSI 高檔 → 尾端在出場區
e_r, x_r = build_signals("rsi_reversion", df, {"buy_th": 30.0, "sell_th": 55.0})
check("rsi_reversion 上漲段不買超賣", not e_r.iloc[-50:].any())
saw = df.iloc[-120:].copy()
saw["close"] = saw["close"].to_numpy() * (1 + 0.002 * np.tile([1, -1], 60))
e_r2, x_r2 = build_signals("rsi_reversion", saw, {"buy_th": 30.0, "sell_th": 55.0})
check("rsi_reversion 鋸齒上漲段觸發出場", bool(x_r2.iloc[-1]))

# high_52w: 每日創高的趨勢段 = 距 52 週高 0% → 進場
e_h, x_h = build_signals("high_52w", df, {"near_pct": 5.0, "exit_pct": 15.0})
check("high_52w 創高段進場", bool(e_h.iloc[-1]) and not bool(x_h.iloc[-1]))

# triple_ma: 趨勢確立尾端 fast>mid>MA200 → 進場
e_t, x_t = build_signals("triple_ma", df, {"fast": 20, "mid": 50})
check("triple_ma 趨勢尾端多頭排列", bool(e_t.iloc[-1]))

# 訊號在完整歷史上算後切窗 = 直接對切窗算的長 lookback 不同 (warmup 保留)
e_full, _ = build_signals("ma_cross", df, {"fast": 20, "slow": 200})
e_win, _ = build_signals("ma_cross", df.iloc[-250:], {"fast": 20, "slow": 200})
check("完整歷史訊號保留 warmup (切窗版前 199 根無訊號)",
      bool(e_full.iloc[-250:].any()) and not bool(e_win.iloc[:199].any()))

print()
if FAILURES:
    print(f"FAILED: {len(FAILURES)} assert(s): {FAILURES}")
    sys.exit(1)
print(f"all asserts passed")
sys.exit(0)
