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
    "source": "ftd_cache | not_available"
  },
  "market_top": {
    "composite_score": "float 0–100",
    "zone": "Normal | Early_Warning | Elevated_Risk | High_Probability | Top_Formation",
    "risk_budget": "string 如 80-100%",
    "source": "market_top_cache | not_available"
  },
  "synthesized_exposure": "string — 最保守曝險上限（三訊號最低者）",
  "signal_conflict": "true | false"
}
```

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
  "upcoming_binary_risks": [
    {
      "event": "string",
      "date": "YYYY-MM-DD",
      "affected_sectors": [],
      "within_48h": "true | false"
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
  "agent": "Sector_Rotation_Analyst | Theme_Intelligence_Analyst | News_Catalyst_Analyst",
  "top_conviction_hot": ["sector1", "sector2"],
  "top_conviction_cold": ["sector1", "sector2"],
  "key_rationale": "string — 最多 2 句",
  "subagent_isolated": "true | false (V1.3: true when produced by parallel subagent; false for inline fallback)"
}
```

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
  "regime_confidence_rationale": "string — 為何這個信度分"
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
        "event": "string",
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
      "risk_flags": ["binary_risk_within_48h", "late_cycle", "overbought", "fat_tail_warning", "extreme_sentiment", "fragility_downgrade", "extreme_sentiment_fragile_combo"]
    }
  ],
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
