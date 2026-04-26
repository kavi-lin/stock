# JSON Schema Reference

> **Schema Version**: `V1.3`
> 所有 Phase 的 JSON 輸出 schema。執行各 Phase 寫入 JSON 時按需查閱。
> ⚠️ Phase 5 的 `_phase0`、`_phase1`、`_phase3` key 名稱不可更換（bridge.py 依賴）。
> ⚠️ Phase 5 末尾必須執行 `sector/scripts/validate_sector_intel.py`（rc=0 才算完成）。
>
> **V1.3 新增**（vs V1.2）：
> - 頂層：`phase4_fanout_mode` / `degraded_agents`（4a/4b subagent 執行狀態）
> - Phase 4a: `subagent_isolated` sentinel
> - Phase 4b: `subagent_isolated` sentinel；`risk_scenario` 要求 falsifiable 格式
>
> **V1.5 新增**（vs V1.3，BUG-006 修補）：
> - Phase 0 / Phase 5 `_phase0` 的 `ftd` block 加 `ftd_status_text` / `ftd_day_number` / `days_since_ftd` / `rally_day_count` 四欄。
> - **反幻覺**：報告 FTD 狀態必須引用 `ftd_status_text` 原文，禁止從 `quality_score.breakdown.base`（"Day 6 FTD..."）反推 day-counter。

---

## Phase 0 Schema

```json
{
  "phase": 0,
  "agent": "Macro_Regime_Analyst",
  "scan_date": "YYYY-MM-DD",
  "breadth_source": "market-breadth-analyzer | web_search",
  "breadth_score": "float 0–100",
  "breadth_zone": "Strong | Healthy | Neutral | Weakening | Critical",
  "breadth_components": {
    "overall_breadth": "0–100",
    "sector_participation": "0–100",
    "momentum": "0–100",
    "mean_reversion_risk": "0–100"
  },
  "market_regime": "BULL | BEAR | SIDEWAYS | VOLATILE | RISK_OFF | RISK_ON",
  "cycle_phase": "Early | Mid | Late | Recession",
  "uptrend_ratio_overall": "float 0.0–1.0 (由 Phase 1 回填)",
  "warning_flags": ["Bearish_Signal_Active", "Below_200MA", "Low_Historical_Percentile"],
  "exposure_ceiling": "string 如 40-60% (breadth only)",
  "regime_confidence": "float 0.0–1.0",
  "ftd": {
    "state": "FTD_CONFIRMED | FTD_WINDOW | RALLY_ATTEMPT | CORRECTION | FTD_INVALIDATED | NO_SIGNAL",
    "quality_score": "float 0–100",
    "exposure_range": "0-20% | 20-40% | 40-65% | 65-100%",
    "ftd_status_text":  "string — V1.5：必引用 cache 同名欄位原文。例：'FTD CONFIRMED, day 12 post-confirmation (rally-day 18; FTD originally confirmed on rally-day 6)'",
    "ftd_day_number":   "int — V1.5：FTD 確認時 rally 第幾天 (FIXED, 永不增加)；不得當作 days-since-FTD 寫進報告",
    "days_since_ftd":   "int — V1.5：距 FTD 確認日已過幾個 trading day（每天 +1）",
    "rally_day_count":  "int — V1.5：rally 已進行幾個 trading day（每天 +1）",
    "source": "ftd_cache | not_available"
  },
  "market_top": {
    "composite_score": "float 0–100",
    "zone": "Normal | Early_Warning | Elevated_Risk | High_Probability | Top_Formation",
    "risk_budget": "string 如 80-100%",
    "source": "market_top_cache | not_available"
  },
  "synthesized_exposure": "string — 最保守曝險上限（三訊號最低者）",
  "signal_conflict": "true | false",

  "fred_available": "true | false — V1.4 新增（MUST-run Layer E）",
  "fred_snapshot": {
    "generated_at":            "ISO timestamp from FRED fetch",
    "regime_label":            "Goldilocks | Soft Landing | Reflation | Benign Easing | Overheating | Late Cycle Tightening | Stagflation | Recession Easing | Recession Risk | Transitional",
    "regime_confidence":       "float 0.20-0.95",
    "macro_scores_composite":  "int 0-100 (latency-weighted)",
    "yield_curve_value":       "float (T10Y2Y)",
    "yield_curve_inverted":    "bool — T10Y2Y < 0",
    "credit_stress_elevated":  "bool — HY pctile > 75",
    "financial_stress_above_avg": "bool — NFCI > 0",
    "fed_rate_direction":      "rising | falling | flat | unknown",
    "real_rate_preferred":     "float — DFII10 if available else DGS10 - CPI YoY",
    "sector_rotation_favor":   ["sector1", "sector2"],
    "sector_rotation_avoid":   ["sector1", "sector2"],
    "velocity_highlights":     ["series:velocity", "e.g. NFCI:accelerating"]
  }
}
```

> `fred_snapshot` 為 **slim 版本**（~15 行），僅保留 Phase 4/Step 6 所需欄位。完整 snapshot 仍在 `skills/fred-macro/cache/fred_latest.json`。失敗時 `fred_available=false` + `fred_snapshot=null`。

---

## Phase 1 Schema

```json
{
  "phase": 1,
  "agent": "Sector_Rotation_Analyst",
  "cycle_position": "Early | Mid | Late | Recession",
  "sectors": [
    {
      "name": "Technology | Healthcare | Energy | Financials | Consumer_Discretionary | Consumer_Staples | Industrials | Materials | Utilities | Real_Estate | Communication",
      "uptrend_ratio": "float 0.0–1.0",
      "uptrend_ratio_vs_ma10": "above | below",
      "slope": "rising | flat | falling",
      "cyclical_or_defensive": "cyclical | defensive",
      "rotation_signal": "INFLOW | NEUTRAL | OUTFLOW",
      "overbought_risk": "HIGH | MEDIUM | LOW",
      "oversold_opportunity": "HIGH | MEDIUM | LOW"
    }
  ],
  "hot_sectors": ["sector1", "sector2"],
  "cold_sectors": ["sector1", "sector2"],
  "rotation_theme": "string — 一句話描述當前輪動方向"
}
```

---

## Phase 2 Schema

```json
{
  "phase": 2,
  "agent": "Theme_Intelligence_Analyst",
  "themes": [
    {
      "name": "string",
      "direction": "bullish | bearish",
      "heat_score": "0–100",
      "lifecycle_stage": "Emerging | Accelerating | Trending | Mature | Exhausting",
      "lifecycle_maturity": "0–100",
      "confidence": "Low | Medium | High",
      "proxy_etfs": ["ETF1", "ETF2"],
      "representative_stocks": ["TICKER1", "TICKER2"],
      "cross_sector_reach": ["sector1", "sector2"]
    }
  ],
  "dominant_bullish_theme": "string",
  "dominant_bearish_theme": "string"
}
```

---

## Phase 3 Schema

```json
{
  "phase": 3,
  "agent": "News_Catalyst_Analyst",
  "scan_window": "past 10 days + next 7 days",
  "top_catalysts": [
    {
      "rank": 1,
      "event": "string",
      "type": "FOMC | earnings | geopolitical | macro_data | sector_specific | political",
      "impact_score": "1–5",
      "affected_sectors": ["sector1"],
      "direction": "bullish | bearish | binary",
      "timing": "past | within_48h | this_week | beyond"
    }
  ],
  "political_overlay": {
    "trump_trade_signals": [
      {
        "keyword": "tariff | energy_deregulation | immigration | china_threat | pharma_threat",
        "headline": "string",
        "source": "X | Truth_Social_secondary | news_report",
        "affected_sectors": ["sector1"],
        "direction": "bullish | bearish"
      }
    ],
    "named_targets_today": ["TICKER or COUNTRY被點名受威脅"],
    "fear_greed_index": "float 0–100",
    "fear_greed_label": "Extreme_Fear | Fear | Neutral | Greed | Extreme_Greed",
    "vix_current": "float",
    "put_call_ratio": "float",
    "spy_rsi": "float",
    "sentiment_source": "SKILL_EXECUTED | WEB_SEARCH_FALLBACK",
    "extreme_sentiment_triggered": "true | false"
  },
  "upcoming_events": [
    {
      "id": "string — 唯一鍵, 格式: <slug-or-ticker>_<date>，例如 'aapl-q2-earnings_2026-04-30'",
      "date": "YYYY-MM-DD",
      "time": "string | null — 'BMO' | 'AMC' | 'HH:MM ET' | 'ALL' | null",
      "category": "string — earnings | macro | econ | binary | geopolitical | system | watchlist",
      "title": "string — **短標** ≤ 36 字 (e.g. 'AAPL Q2 財報', 'FOMC 利率決議')",
      "description": "string | null — 補述; 看多/看空 sector 列在 sectors 欄位, 不要塞 title",
      "tickers": ["TICKER — 受影響個股, 全市場事件留空"],
      "sectors": ["GICS sector name (Technology / Real_Estate / ...) — 用底線連字"],
      "impact": "string — high | med | low",
      "is_binary": "bool — true 會在 calendar 加紅框警示樣式",
      "within_48h": "bool — 派生; date - today ≤ 2"
    }
  ],
  "upcoming_binary_risks": [
    {
      "_legacy_format": "保留供向後相容; 內容應由 upcoming_events (is_binary=true) 派生。新報告請優先填 upcoming_events。",
      "event": "string — 同 upcoming_events.title (沿用舊格式時也可保留括號補述)",
      "date": "YYYY-MM-DD",
      "affected_sectors": [],
      "within_48h": "bool"
    }
  ],
  "sector_news_sentiment": {
    "Technology": "bullish | bearish | neutral",
    "Healthcare": "bullish | bearish | neutral"
  }
}
```

---

## Phase 4a Schema

```json
{
  "phase": "4a",
  "agent": "Sector_Rotation_Analyst | Theme_Intelligence_Analyst | News_Catalyst_Analyst | FRED_Macro_Analyst",
  "top_conviction_hot": ["sector1", "sector2"],
  "top_conviction_cold": ["sector1", "sector2"],
  "key_rationale": "string — 最多 2 句",
  "subagent_isolated": "true | false (V1.3: true when produced by parallel subagent; false for inline fallback)"
}
```

> V1.4：Phase 4a 新增第 4 lane `FRED_Macro_Analyst`（當 `fred_available=true` 時必跑；`fred_available=false` 時跳過該 lane，`phase4_fanout_mode` 仍可為 PARALLEL_SUBAGENT 但 lane 數變 3）

---

## Phase 4b Schema

```json
{
  "phase": "4b",
  "agent": "Devils_Advocate",
  "tail_risk_checks": [
    {
      "sector": "string",
      "proxy_etf": "string",
      "fragility_label": "ANTIFRAGILE | RESILIENT | FRAGILE | EXTREMELY FRAGILE",
      "tail_risk_score": "float 0–100",
      "key_tail_flags": ["fat_tail_warning", "crash_vulnerability"],
      "tail_risk_source": "SKILL_EXECUTED | SKIPPED_LOW_SCORE | SKIPPED_CAPACITY_LIMIT"
    }
  ],
  "challenge_targets": [
    {
      "challenged_sector": "string",
      "challenged_call": "HOT | COLD",
      "counter_evidence": "string (≥ 2 句，含具體數據或邏輯)",
      "tail_risk_evidence": "string — 來自 tail-risk-analyzer 的量化支撐（若有）",
      "risk_scenario": "string — V1.3 要求 falsifiable (IF <條件> WITHIN <窗口> THEN <推翻>)",
      "confidence_level": "HIGH | MEDIUM | LOW"
    }
  ],
  "consensus_warning": "true | false",
  "subagent_isolated": "true | false (V1.3: true when DA ran as isolated subagent)"
}
```

---

## Phase 4c Schema

```json
{
  "phase": "4c",
  "agent": "Portfolio_Strategist",
  "debate_resolution": "string",
  "devils_advocate_accepted": ["sector1"],
  "devils_advocate_rejected": ["sector1"],
  "tail_risk_downgrades": ["sector — 因尾部風險被降一級的產業"],
  "decision_tree_path": "string — 走過的決策樹分支摘要（如 A:pass B:triggered C:late+cyclical）",
  "final_regime_stance": "AGGRESSIVE | NEUTRAL | DEFENSIVE",
  "regime_confidence": "float 0.0–1.0",
  "regime_confidence_rationale": "string — 為何這個信度分",
  "today_verdict": {
    "headline":    "string ≤ 60 chars — stance + 1 行核心診斷",
    "stance":      "AGGRESSIVE | NEUTRAL | DEFENSIVE — 對齊 final_regime_stance",
    "confidence":  "float 0.0–1.0 — 對齊 regime_confidence",
    "one_liner":   "string ≤ 160 chars — 一句話擴展",
    "key_takeaways": [
      "string — 今日必看，動詞開頭可操作化（3-5 條）"
    ],
    "sector_actions": [
      {
        "sector":     "Industrials | Financials | ...",
        "action":     "overweight | underweight | avoid | wait | neutral",
        "confidence": "high | medium | low",
        "reason":     "string ≤ 50 chars"
      }
    ],
    "watch_next": [
      "string — 要 monitor 的觸發點（3-5 條，含所有 within_48h binary risks）"
    ]
  }
}
```

---

## Phase 5 Schema（sector_intel.json 完整結構）

```json
{
  "verdict_date": "YYYY-MM-DD",
  "protocol_version": "V1.3",
  "phase4_fanout_mode": "PARALLEL_SUBAGENT | PARTIAL_FALLBACK | FULL_FALLBACK | INLINE",
  "degraded_agents": ["Sector_Rotation_Analyst | Theme_Intelligence_Analyst | News_Catalyst_Analyst | Devils_Advocate (empty array in normal runs)"],
  "generated_at": "YYYY-MM-DD HH:MM",
  "market_regime": "from Phase 0",
  "exposure_ceiling": "from Phase 0 (breadth only)",
  "synthesized_exposure": "from Phase 0 (three-signal)",
  "cycle_phase": "from Phase 0",
  "_phase0": {
    "phase": 0,
    "agent": "Macro_Regime_Analyst",
    "scan_date": "YYYY-MM-DD",
    "breadth_source": "market-breadth-analyzer | web_search",
    "breadth_score": "float 0–100",
    "breadth_zone": "Strong | Healthy | Neutral | Weakening | Critical",
    "breadth_components": {
      "overall_breadth": "0–100",
      "sector_participation": "0–100",
      "momentum": "0–100",
      "mean_reversion_risk": "0–100"
    },
    "market_regime": "BULL | BEAR | SIDEWAYS | VOLATILE | RISK_OFF | RISK_ON",
    "cycle_phase": "Early | Mid | Late | Recession",
    "uptrend_ratio_overall": "float 0.0–1.0",
    "warning_flags": ["Bearish_Signal_Active"],
    "exposure_ceiling": "string (breadth only)",
    "regime_confidence": "float 0.0–1.0",
    "ftd": {
      "state": "FTD_CONFIRMED | FTD_WINDOW | RALLY_ATTEMPT | CORRECTION | FTD_INVALIDATED | NO_SIGNAL",
      "quality_score": "float 0–100",
      "exposure_range": "string",
      "ftd_status_text":  "string — V1.5: bridge from _phase0.ftd.ftd_status_text",
      "ftd_day_number":   "int — V1.5: rally-day FTD was confirmed (FIXED)",
      "days_since_ftd":   "int — V1.5: trading days since FTD date (increments daily)",
      "rally_day_count":  "int — V1.5: trading days since rally low (increments daily)",
      "source": "ftd_cache | not_available"
    },
    "market_top": {
      "composite_score": "float 0–100",
      "zone": "Normal | Early_Warning | Elevated_Risk | High_Probability | Top_Formation",
      "risk_budget": "string",
      "source": "market_top_cache | not_available"
    },
    "synthesized_exposure": "string",
    "signal_conflict": "true | false"
  },
  "_phase1": {
    "phase": 1,
    "agent": "Sector_Rotation_Analyst",
    "sectors": [
      {
        "name": "string",
        "uptrend_ratio": "float",
        "rotation_signal": "INFLOW | NEUTRAL | OUTFLOW",
        "overbought_risk": "HIGH | MEDIUM | LOW",
        "ytd_perf_note": "string"
      }
    ]
  },
  "_phase3": {
    "phase": 3,
    "agent": "News_Catalyst_Analyst",
    "scan_window": "past 10 days + next 7 days",
    "top_catalysts": [
      {
        "rank": 1,
        "event": "string — 繁體中文",
        "type": "FOMC | earnings | geopolitical | macro_data | sector_specific | political",
        "impact_score": "1–5",
        "affected_sectors": ["sector1"],
        "direction": "bullish | bearish | binary",
        "timing": "past | within_48h | this_week | beyond"
      }
    ],
    "political_overlay": {
      "trump_trade_signals": [
        {
          "keyword": "string",
          "headline": "string",
          "affected_sectors": ["sector1"],
          "direction": "bullish | bearish"
        }
      ],
      "named_targets_today": ["TICKER or COUNTRY"],
      "fear_greed_index": "float 0–100",
      "fear_greed_label": "Extreme_Fear | Fear | Neutral | Greed | Extreme_Greed",
      "vix_current": "float",
      "put_call_ratio": "float",
      "spy_rsi": "float",
      "sentiment_source": "SKILL_EXECUTED | WEB_SEARCH_FALLBACK",
      "extreme_sentiment_triggered": "true | false"
    },
    "upcoming_binary_risks": [
      {
        "event": "string — 繁體中文，格式：事件名稱（影響方向；看多/看空哪些子產業）",
        "date": "YYYY-MM-DD",
        "affected_sectors": [],
        "within_48h": "true | false"
      }
    ],
    "sector_news_sentiment": {
      "Technology": "bullish | bearish | neutral"
    }
  },
  "sentiment_snapshot": {
    "composite_score": "float 0–100",
    "fear_greed_label": "string",
    "vix": "float",
    "put_call_ratio": "float",
    "extreme_sentiment_triggered": "true | false"
  },
  "sectors": [
    {
      "name": "string",
      "verdict": "HOT | WARM | COLD | AVOID",
      "composite_score": "0–100",
      "score_components": {
        "breadth_momentum": "0–25",
        "theme_heat": "0–25",
        "news_catalyst": "0–25",
        "rotation_signal": "0–25"
      },
      "key_reasons": ["max 3 items, max 10 words each"],
      "devils_advocate_note": "string if challenged",
      "tail_risk_label": "ANTIFRAGILE | RESILIENT | FRAGILE | EXTREMELY FRAGILE | N/A",
      "proxy_etf": "string",
      "risk_flags": ["binary_risk_within_48h", "late_cycle", "overbought", "fat_tail_warning", "extreme_sentiment", "fragility_downgrade", "extreme_sentiment_fragile_combo", "macro_theme_divergence"],
      "step6_fred_multiplier": "float (V1.4) — FRED regime overlay applied to score; 1.0 = no-op"
    }
  ],
  "step6_overlay": {
    "applied":          "bool — true iff fred_available && Step 6 ran",
    "replaces_step1":   "bool — true (always; documents that Step 1 was skipped)",
    "regime_label":     "from fred_snapshot",
    "regime_confidence":"float — used as gating factor",
    "rationale":        "string — one line, e.g. 'Overheating regime, conf 0.71 → Energy ×1.10 (favor), Tech ×0.85 (avoid)'"
  },
  "summary": {
    "hot_sectors": ["sector with verdict=HOT"],
    "warm_sectors": ["sector with verdict=WARM"],
    "cold_sectors": ["sector with verdict=COLD"],
    "avoid_sectors": ["sector with verdict=AVOID"]
  },
  "sector_divergence_watch": [
    {
      "sector": "string",
      "signal": "news_positive_price_negative | news_negative_price_positive",
      "description": "string",
      "action": "monitor | reduce_exposure"
    }
  ],
  "political_risk_summary": {
    "active_trump_trades": ["Energy_deregulation_bullish", "China_tariff_bearish"],
    "named_targets_today": ["TICKER or sector被點名"],
    "fear_greed_status": "Extreme_Fear | Fear | Neutral | Greed | Extreme_Greed"
  },
  "actionable_themes": ["theme1", "theme2"],
  "session_notes": "string — PM 給 investment_protocol 的一句話 handoff"
}
```
