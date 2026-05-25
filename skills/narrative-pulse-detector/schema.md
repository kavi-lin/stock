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

  // 4-scenario R/R 量化 (V1.1 — per-ticker adjusted)
  "scenarios": [
    {
      "label": "末段衝高",
      "label_en": "climactic_top",
      "prob_base": 0.35,                   // V1.0 prior hardcoded in stage_weights.yaml
      "prob": 0.28,                        // V1.1 final after delta + clamp + bounded_normalize
      "prob_breakdown": [                  // every applied rule (V1.1)
        {"rule": "rsi_extreme_85_plus",      "delta": -0.06, "note": "RSI peak ≥85"},
        {"rule": "distribution_days_3_plus", "delta": -0.08, "note": ""},
        {"rule": "_clamp",                   "delta":  0.0,  "note": "within [0.05, 0.80]"},
        {"rule": "_normalize",               "delta":  0.07, "note": "bounded water-fill to Σ=1 within [0.05, 0.80]"}
      ],
      "target_pct_base": 13.0,             // V1.0 prior
      "target_pct": 10.0,                  // V1.1 final
      "target_breakdown": [                // (V1.1)
        {"rule": "strain_p_sma200_2.0_plus", "delta": -3.0, "note": ""}
      ],
      "target_price": 17.02                // price × (1 + target_pct/100)
    }
    // ... 其餘 scenarios 同結構
  ],

  // Three-layer E[R] (V1.1 schema)
  "expected_return_pct_base":      11.15,  // V1.0 prior, NO ticker delta, NO macro (control for 5/31 review)
  "expected_return_pct_pre_macro":  8.92,  // V1.1 ticker-adjusted scenario sum, NO macro
                                           //   (注意:V1.0 此欄位語義 = raw prior;V1.1 改為 adjusted)
  "expected_return_pct":           11.92,  // 最終值 = pre_macro + Σ macro_delta (Dashboard 顯這個)
  "macro_adjustments_applied": [
    {"name": "breadth_washout_stage_1", "delta_pct": 3.0, "note": "..."}
  ],
  "scenario_model_version": "v1.1_declarative",  // schema version tag for downstream consumers

  "next_warning_condition": "distribution day count >= 4 / 25d",
  "recommended_action": "no_new_entry",    // see enum below

  // metadata
  "weights_version": "v1.1",               // config/stage_weights.yaml 版本
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
  "version": "1.1",                            // V3.19.0 schema bump (three-layer E[R] + prob_breakdown)
  "last_updated": "2026-05-25T22:30:00+00:00",
  "weights_version": "v1.1",
  "universe": {
    "source": "thematic_screener_top_movers + structural_watchlist",
    "ticker_count": 28
  },
  "tickers": {
    "NOK":  {
      "stage": 4,
      "stage_label_zh": "...",
      "stage_confidence": 0.82,
      "expected_return_pct":          -13.4,   // final (Dashboard reads this)
      "expected_return_pct_pre_macro": -8.4,   // V1.1 ticker-adjusted (no macro)
      "expected_return_pct_base":     -10.6,   // V1.0 prior (control)
      "scenario_model_version": "v1.1_declarative",
      "scenarios": [ /* per-scenario with prob_base / prob / prob_breakdown / target_breakdown */ ],
      "...": "..."
    }
  },
  "ranking": {
    "top_risk":        ["NOK", "AVGO", "PLTR"],     // stage 4-5 by stage_confidence DESC
    "top_opportunity": ["XYZ", "ABC"],              // stage 1-2 by expected_return_pct DESC
    "watch_distribution_imminent": ["NOK"]          // stage 4 + distribution_days >= 2
  }
}
```

### Snapshot Archive (V1.1)

每次 `batch_scan.py` 跑完額外寫一份到:

```
skills/narrative-pulse-detector/snapshots/<YYYY-MM-DD>.json
```

內容 = `Dashboard/narrative_pulse.json` 完整 copy。5/31 observation review join
momentum-journal forward returns 計算 `_base` vs `_pre_macro` vs `final` 三層
E[R] 的 IC / hit rate。

## V1.1 Breaking Schema Changes

| 欄位 | V1.0 語義 | V1.1 語義 |
|---|---|---|
| `expected_return_pct_pre_macro` | raw stage prior (no ticker delta, no macro) | V1.1 ticker-adjusted scenario sum (no macro) |
| `scenarios[].prob` | 等於 hardcoded prior | 含 per-ticker delta + clamp + bounded_normalize |
| `scenarios[].target_pct` | 等於 hardcoded prior | 含 per-ticker strain delta |

新增欄位 (V1.0 consumer 會忽略):
- `expected_return_pct_base` — V1.0 prior 搬到這裡 (5/31 review 控制組)
- `scenarios[].prob_base` / `prob_breakdown` / `target_pct_base` / `target_breakdown`
- `scenario_model_version` — 標 `"v1.1_declarative"`
- `macro_adjustments_applied[]` — list of applied macro overrides (V1.0 已有)
