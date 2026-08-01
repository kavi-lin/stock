---
name: quant-backtest
description: Deterministic strategy backtest engine — replays 11 rule-based strategy templates (momentum-monitor score replay, MA cross, TSMOM, Donchian, OBV trend, Bollinger reversion, SuperTrend, triple MA, RSI reversion, 52-week high, Keltner) over 3-10y daily OHLCV with costs, parameter-sweep grid, equity curve / drawdown / per-year returns / trade list, plus a cross-ticker template benchmark ranking. Use when user asks about 回測, backtest, strategy validation, 策略回測, parameter robustness, or the Dashboard backtest page.
market: US
scope: single-ticker
data_sources: [fmp, yfinance]
---

# Quant Backtest

## Purpose

把「規則可完全代碼化」的策略在歷史日線上重放,產出可檢驗的績效與**強健性**證據。
設計哲學承襲 backtest-expert 方法論:找「最不容易壞」的策略,不是紙上報酬最高的
— 成本永遠內建、參數掃描格看高原不看尖峰、逐年表拆穿單一 regime 依賴。

## Templates(STRATEGIES registry,V4.63.0 起 11 個)

| Template | Entry | Exit | Params(預設) |
|---|---|---|---|
| `momentum` | composite ≥ entry_score 且 Stage 2 uptrend | close < MA50 或 composite < exit_score | entry_score 65, exit_score 45 |
| `ma_cross` | MA(fast) 上穿 MA(slow) | 下穿 | fast 50, slow 200 |
| `roc_trend` | lookback 日報酬 > entry_th_pct | 報酬轉負 | lookback 126, entry_th_pct 0 |
| `donchian` | 創 n_entry 日新高 | 跌破 n_exit 日新低 | n_entry 20, n_exit 10 |
| `obv_trend` | OBV > OBV 均線且 close > 價格均線 | OBV 跌破均線 | obv_ma 20, price_ma 50 |
| `boll_reversion` | MA200 之上跌破布林下軌 | 回到中軌 | n 20, k 2.0 |
| `supertrend` | SuperTrend(n, mult) 翻多 | 翻空 | n 10, mult 3.0 |
| `triple_ma` | MA(fast)>MA(mid)>MA200 且 close>MA(fast) | fast 跌破 mid | fast 20, mid 50 |
| `rsi_reversion` | RSI14 < buy_th | RSI14 > sell_th | buy_th 30, sell_th 55 |
| `high_52w` | 收盤距 252 日高 near_pct% 內 | 回落 exit_pct% | near_pct 5, exit_pct 15 |
| `keltner` | close > EMA(n) + mult×ATR10 | 跌破 EMA(n) | n 20, mult 2.0 |

模板選型:V4.63.0 曾以 20 個候選對 12 檔 (SPY/QQQ + 跨產業 mega-cap) 跑
5y/10bps 同一基準,取**中位數 Sharpe 前 10 名** + 自家 momentum 引擎入
registry;落選 9 個 (chandelier / rsi2 / stoch / zscore / boll_breakout /
adx_trend / macd_cross / dip_buy / breakout_vol) 不提供。基準排名 artifact 由
`rank_strategies.py` 產出 → `data/strategy_rank.json` → Dashboard 卡片 badge。

`momentum` 是 momentum-monitor 計分規則的**歷史重放**(口徑鎖定
`skills/momentum-monitor/scripts/momentum.py:_composite`):volume_flow /
ma_stage / trend_acceleration 逐日重算;short_squeeze 以中性 40 分固定
(歷史 short interest 不可得)。每次跑會自動比對 live cache 的
ma_stage / trend_acceleration / stage 口徑並寫入 `validation_vs_live_cache`。

**訊號在完整抓取歷史上計算後才切回測窗**(V4.63.0 起)— MA200 / 252 日
lookback 不再吃掉窗口前段。

## Usage

```bash
python3 skills/quant-backtest/scripts/backtest.py NVDA                    # momentum 5y 預設
python3 skills/quant-backtest/scripts/backtest.py NVDA --period 10y \
    --entry-score 70 --exit-score 40 --cost-bps 15                        # 舊 flags 仍相容
python3 skills/quant-backtest/scripts/backtest.py AAPL --template ma_cross --fast 20 --slow 100
python3 skills/quant-backtest/scripts/backtest.py MSFT --template donchian \
    --params-json '{"n_entry": 40, "n_exit": 20}'                         # 通用參數通道
python3 skills/quant-backtest/scripts/rank_strategies.py                  # 12 檔基準排名 → data/strategy_rank.json
python3 skills/quant-backtest/scripts/test_backtest.py                    # golden fixture, 改 engine 必跑 rc=0
```

Dashboard 觸發:`backtest.html` 策略卡片 dialog → POST `/api/protocol-queue`
`{name:"quant_backtest", ticker, template, period, cost_bps, params_json}`
(SCRIPT_PROTOCOLS 路徑,0 LLM)。卡片 badge 讀 `GET /api/backtest/strategies`。

## Output

`skills/quant-backtest/data/<TICKER>_<template>.json`(gitignored,同
ticker+template 覆寫):metrics / yearly / trades / sweep 格 / series
(dates, close, eq_strat, eq_bh, score, pos, drawdown×2)。
`data/strategy_rank.json`:模板基準排名(rank_strategies.py)。
Exit codes: 0 ok / 1 fatal / 2 degraded(窗口 < 252 bars)。

## Known Limitations(UI 必須顯示 data_caveats)

1. **FMP EOD 拆股調整、非股息調整** — 高股息標的長期報酬被低估。
2. **short_squeeze 組件中性化** — momentum 重放分數與 live 分數在高 short
   interest 股票上會有偏差。
3. **存活者偏差** — 以現在的 ticker 回看;下市/被併股票不在樣本。
4. **訊號日收盤成交假設** — 實務上訊號收盤才確立,以次日開盤成交會更保守;
   cost_bps 請至少 10 起跳補償。

## Discipline

**探索層**。結果**不**進入 investment_protocol 決策,不回寫任何
protocol.history / weights 設定。回測績效好 ≠ 未來有效 — 參數掃描格出現
「只有單點賺錢」= 曲線擬合,棄用該參數區。
