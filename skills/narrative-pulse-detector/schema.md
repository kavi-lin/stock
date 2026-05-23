# narrative-pulse-detector — Output Schema

## Cache file 路徑

```
skills/narrative-pulse-detector/cache/<TICKER>_<YYYY-MM-DD>.json
```

TTL: 4 小時 (盤中變動快,4h 內 cache hit;超過 4h 重跑)。

## Top-level schema

```jsonc
{
  // identity
  "ticker": "NOK",
  "run_at": "2026-05-23T22:30:00+00:00",     // ISO UTC
  "cache_key": "NOK_2026-05-23",
  "data_window": {
    "ohlcv_from": "2026-02-22",
    "ohlcv_to":   "2026-05-22",
    "ohlcv_bars": 63
  },

  // quote snapshot (來自 FMPClient.quote)
  "quote": {
    "price": 15.47,
    "change_pct": 9.10,
    "volume": 126294237,
    "year_high": 15.78,
    "year_low":  4.00,
    "market_cap": 83551799240
  },

  // 8 components (raw measurements,給 classifier 算 stage 用)
  "components": {
    "rsi_14_latest": 71.5,
    "rsi_overbought_days": 17,            // consecutive days with RSI >= 70 (reset on <50)
    "rsi_peak_recent": 83.0,              // RSI peak in last 30d
    "price_to_sma50_ratio": 1.43,
    "price_to_sma200_ratio": 2.14,        // 拉伸倍數
    "sma200_breakout_days_ago": 95,       // 距上次站上 SMA200 多少日
    "volume_baseline_30d_avg": 18000000,  // 早期 30d 平均成交量
    "volume_recent_20d_avg": 109000000,
    "volume_multiplier": 6.06,            // recent / baseline
    "gap_up_density_4w": 6,               // 4 週內 gap-up >= 5% 個數
    "distribution_days_25d": 2,           // O'Neil per-stock,25d window
    "stalling_days_25d": 1,
    "failed_rally_signal": false,         // 新高失敗 + 收破前低
    "pt_raise_30d": 7,                    // sell-side raise event 30d
    "pt_raise_60d": 12,
    "retail_mention_24h": 142,            // Reddit + HN $TICKER cashtag
    "retail_mention_baseline_7d_avg": 18,
    "retail_mention_multiplier": 7.89,
    "media_mention_30d": 38,              // news_logs 統計
    "media_source_diversity": 12,         // unique source 數
    "vix_now": 18.5,
    "breadth_200dma_pct": 62.0
  },

  // stage classification 結果
  "stage": 4,                              // 1-5
  "stage_label_zh": "狂熱後段",
  "stage_label_en": "Late Euphoria",
  "stage_confidence": 0.82,                // 0-1
  "stage_components_triggered": [          // 哪些條件命中 Stage 4
    "rsi_overbought_days >= 10",
    "price_to_sma200_ratio >= 1.8",
    "gap_up_density_4w >= 3",
    "volume_multiplier >= 5",
    "pt_raise_30d >= 5",
    "retail_mention_multiplier >= 3"
  ],

  // 4-scenario R/R 量化
  "scenarios": [
    {
      "label": "末段衝高",
      "label_en": "climactic_top",
      "prob": 0.35,
      "target_pct": 13.0,                  // % from current price
      "target_price": 17.48
    },
    {
      "label": "橫盤消化",
      "label_en": "consolidation",
      "prob": 0.25,
      "target_pct": -10.0,
      "target_price": 13.92
    },
    {
      "label": "回測 SMA50",
      "label_en": "test_sma50",
      "prob": 0.25,
      "target_pct": -30.0,
      "target_price": 10.83
    },
    {
      "label": "回測 SMA200",
      "label_en": "test_sma200",
      "prob": 0.15,
      "target_pct": -53.4,
      "target_price": 7.22
    }
  ],
  "expected_return_pct": -13.4,            // sum(prob * target_pct)
  "next_warning_condition": "distribution day count >= 4 / 25d",
  "recommended_action": "no_new_entry",    // see enum below

  // metadata
  "weights_version": "v1.0",               // config/stage_weights.yaml 版本
  "input_health": {
    "ohlcv_ok": true,
    "quote_ok": true,
    "finnhub_pt_ok": true,
    "social_ok": true,                     // false 時 retail_mention_24h=null
    "news_ok": true,
    "macro_ok": true
  }
}
```

## `recommended_action` enum

| Value | Stage 對應 | 中文 |
|---|---|---|
| `early_entry_window` | 1 | 早期建倉窗口 |
| `active_accumulation` | 2 | 積極布局 |
| `hold_or_follow` | 3 | 持有 / 跟進 |
| `reduce_or_no_new_entry` | 4 | 減倉 / 不新進 |
| `exit_or_short_candidate` | 5 | 出場 / 做空候選 |
| `insufficient_data` | — | 資料不足無法判斷 (input_health 任一 false 且 critical) |

## Batch output (`Dashboard/narrative_pulse.json`)

```jsonc
{
  "version": "1.0",
  "last_updated": "2026-05-23T22:30:00+00:00",
  "weights_version": "v1.0",
  "universe": {
    "source": "thematic_screener_top_movers + structural_watchlist",
    "ticker_count": 28
  },
  "tickers": {
    "NOK":  { /* per-ticker schema 摘要 — 不重複 components,只放 stage + scenarios + recommended_action */ },
    "AVGO": { /* ... */ }
  },
  "ranking": {
    "top_risk":        ["NOK", "AVGO", "PLTR"],     // stage 4-5 by stage_confidence DESC
    "top_opportunity": ["XYZ", "ABC"],              // stage 1-2 by stage_confidence DESC
    "watch_distribution_imminent": ["NOK"]          // stage 4 + distribution_days >= 2
  }
}
```
