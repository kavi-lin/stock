# Multi-Agent Investment Protocol (V4.4)

---

## SESSION STARTUP

```
SESSION CONFIG
──────────────────────────────────────────
RISK_TOLERANCE : LOW | MEDIUM | HIGH
──────────────────────────────────────────
```

> Ticker 由使用者在對話中直接指定，無需填入 config。

---

## GLOBAL RULES

1. **Phase Execution Order**: 0 → 1 → 2 → 2.5 → 3 → 4 → 5。絕不跳過順序。
2. **Phase 0 Cache（三層優先順序）**:
   - **層 1** 讀取 `../sector/sector_logs/YYYY-MM-DD_sector_intel.json`。存在且日期符合 → 直接從中提取 macro context，完全跳過所有 web search（`phase0_source: SECTOR_CACHE`）。
   - **層 2** 讀取 `./invest_logs/YYYY-MM-DD_phase0.json`。存在且日期符合 → 載入（`phase0_source: INVEST_CACHE`）。
   - **層 3** 兩者皆不存在 → 執行 web search，完成後寫入 `./invest_logs/YYYY-MM-DD_phase0.json`（`phase0_source: FRESHLY_EXECUTED`）。
3. **Theme Cache**: 若任何 Phase 需要主題熱度資料，執行 `theme-detector` skill **前**必須先以今日日期搜尋 `../skills/theme-detector/cache/theme_detector_YYYY-MM-DD_*.json`。找到 → 直接載入（`theme_source: THEME_CACHE`），跳過 skill 執行；未找到 → 執行 skill，JSON cache 存入 `../skills/theme-detector/cache/`，MD 報告移至 `../reports/` 並重新命名為 `YYYYMMDD_theme_detector_HHMMSS.md`。
4. **Prior Session**: 讀取 `./invest_logs/history.json`，取最近一筆作為 prior context。
5. **Output Format**: 邏輯輸出為 JSON；Markdown 僅用於最終 Visualization Table。
6. **key_factors**: 最多 3 條，每條最多 8 個英文單字。
7. **Phase 5**: session export 只存結果，不重複 Phase 3 的計算步驟。
8. **MD Report**（強制）: Phase 5 完成後，將完整分析（Phase 0–4 + Visualization Table + 委員會決議）存為 `../reports/YYYYMMDD_TICKER.md`。命名格式範例：`20260410_CRWV.md`。不得省略。

---

## TEAM STRUCTURE

| Agent | Responsibility |
|---|---|
| Global News Intelligence | Phase 0 macro backdrop |
| Fundamentals Analyst | Valuation, balance sheet, growth |
| Sentiment Analyst | Reddit/X, retail flow, fear/greed |
| News Analyst | Macro events, CPI/Fed, geopolitical |
| Technical Analyst | Price action, RSI, MACD, volume |
| Trader Agent | Entry/exit planner |
| Risk Manager | Position sizer & safety auditor |
| Portfolio Manager (PM) | Decision, weight control, export |

---

## PHASE 0 — GLOBAL NEWS INTELLIGENCE

**三層 cache 檢查（依序執行）**：

1. 讀取 `../sector/sector_logs/YYYY-MM-DD_sector_intel.json`
   - 存在且 `verdict_date` = 今日 → 從中提取以下欄位作為 macro context，**跳過所有 web search**，前往 Phase 1：
     `market_regime`, `exposure_ceiling`, `political_risk_summary`, `actionable_themes`, `session_notes`
   - 同時將 `sector_intel.summary` 的 hot/cold sectors 直接填入 `macro_summary.hot_sectors / cold_sectors`

2. 讀取 `./invest_logs/YYYY-MM-DD_phase0.json`
   - 存在且 `scan_date` = 今日 → 直接載入，前往 Phase 1

3. 兩者皆不存在 → 執行以下 web search，完成後寫入 `./invest_logs/YYYY-MM-DD_phase0.json`

**Web search queries（層 3 才執行，優先用 `market-news-analyst` skill）**:
- `market-news-analyst` skill（涵蓋以下全部）或逐條 web search：
  - "global stock market news today"
  - "Fed interest rate outlook today"
  - "geopolitical risk markets today"
  - "S&P 500 outlook today"
  - "sector rotation news today"

```json
{
  "phase": 0,
  "agent": "Global_News_Intelligence",
  "scan_date": "YYYY-MM-DD",
  "data_source_timestamp": "YYYY-MM-DD HH:MM",
  "bullish_signals": [
    { "rank": 1, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 2, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 3, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 4, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 5, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 6, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 7, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 8, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 9, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 10, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" }
  ],
  "bearish_signals": [
    { "rank": 1, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 2, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 3, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 4, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 5, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 6, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 7, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 8, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 9, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 10, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" }
  ],
  "macro_summary": {
    "bullish_total_impact": "sum of bullish impact_scores",
    "bearish_total_impact": "sum of bearish impact_scores",
    "net_score": "bullish_total - bearish_total",
    "macro_backdrop_score": "net_score normalized to -5.0 to +5.0",
    "market_regime": "BULL | BEAR | SIDEWAYS | VOLATILE | RISK_OFF | RISK_ON",
    "regime_confidence": "0.0 to 1.0",
    "key_themes": ["theme1", "theme2"],
    "hot_sectors": ["sector1"],
    "cold_sectors": ["sector1"]
  },
  "phase3_macro_multiplier": "float",
  "mandatory_risk_flags": ["string"],
  "binary_risks": ["earnings_YYYYQX", "FOMC_YYYY-MM-DD", "geopolitical_escalation"]
}
```

**macro_multiplier 規則**:

| macro_backdrop_score | multiplier |
|---|---|
| >= +3 | 1.2 |
| +1 to +3 | 1.0 |
| -1 to +1 | 0.9 |
| -3 to -1 | 0.75 |
| < -3 | 0.6 |

---

## PHASE 1 — CONTEXT & MEMORY REVIEW

**Agent**: Portfolio Manager (PM)

```json
{
  "phase": 1,
  "agent": "Portfolio_Manager",
  "phase0_source": "CACHE_LOADED | FRESHLY_EXECUTED",
  "prior_session_loaded": "true | false",
  "last_outcome": "WIN | LOSS | UNKNOWN",
  "historical_bias": "string",
  "adjustment_strategy": "string",
  "current_market_regime": "from Phase 0",
  "active_weights": {
    "Fundamentals": 0.30,
    "Sentiment": 0.20,
    "News": 0.20,
    "Technical": 0.30
  }
}
```

---

## PHASE 2 — ANALYST MULTI-AGENT CORE

**Agent**: Fundamentals / Sentiment / News / Technical Analyst

```json
{
  "phase": 2,
  "agent": "Fundamentals_Analyst | Sentiment_Analyst | News_Analyst | Technical_Analyst",
  "ticker": "STRING",
  "signal": "BUY | SELL | HOLD",
  "score": "-5 to +5",
  "confidence": "0.0 to 1.0",
  "key_factors": ["max 8 words each", "max 3 items"],
  "risk_flags": ["max 2 items"],
  "phase0_alignment": "ALIGNED | MISALIGNED | NEUTRAL",
  "data_source_timestamp": "YYYY-MM-DD HH:MM"
}
```

**各 analyst 聚焦範圍與建議 skill**:
- **Fundamentals**: P/E vs sector, revenue growth YoY, FCF, debt/equity, next earnings date
  → 優先使用 `us-stock-analysis` skill（結構化基本面輸出，省 ~3–5k token vs web search）
- **Sentiment**: Reddit/X mention volume, Put/Call ratio, short interest %, fear/greed index
  → 無直接 skill，使用 web search（fear/greed 可從 sector_intel.json 直接讀取）
- **News**: Company news 48h, analyst upgrades/downgrades, cross-ref Phase 0 key_themes
  → 優先使用 `market-news-analyst` skill，或從 sector_intel.json `top_catalysts` 提取相關條目
- **Technical**: Price vs 20/50/200MA, RSI(14), MACD crossover, volume vs 20-day avg, nearest support/resistance
  → 若有週線圖 → 使用 `technical-analyst` skill；無圖則 web search

---

## PHASE 2.5 — CONFLICT & BIAS PROTOCOL

**Agent**: Portfolio Manager (PM)

**觸發條件**:
- **T1**: `Sentiment.score > +3` AND `Fundamentals.score < 0`
- **T2**: `News.score < -3` AND `Technical.signal = BUY`
- **T3**: `macro_backdrop_score < -3` AND any `signal = BUY` with `score > +3`
- **Anti-Bias**: 所有 analyst 信號相同時，News Analyst 追加 `devils_advocate: ["reason1","reason2","reason3"]`

```json
{
  "phase": "2.5",
  "agent": "Portfolio_Manager",
  "triggers_fired": ["T1", "T3"],
  "conflict_summary": "one sentence per trigger",
  "resolution": "string",
  "phase0_macro_flag": "OVERRIDE_ACTIVE | NONE",
  "proceed_to_phase3": "true | false"
}
```

`proceed_to_phase3 = false` → 直接跳至 Phase 5，輸出 `CANCEL`。

---

## PHASE 3 — DECISION ENGINE

**Agent**: Portfolio Manager (PM)

**公式**: `FinalScore = Σ(Weight_i × Score_i × Confidence_i) × macro_multiplier`

**Regime Adjustment**: 若 `market_regime = VOLATILE` → `FinalScore × 0.85`

**決策閾值**: BUY `>= 2.0` / HOLD `-2.0 to 2.0` / SELL `<= -2.0`

**自動 REJECT**: `risk_reward_ratio < 2.0` / `final_decision = HOLD` / `mandatory_risk_flags` 含系統性事件 / `proceed_to_phase3 = false`

```json
{
  "phase": 3,
  "agent": "Portfolio_Manager",
  "ticker": "STRING",
  "calculation_steps": {
    "fund": "0.30 × [score] × [conf] = [result]",
    "sent": "0.20 × [score] × [conf] = [result]",
    "news": "0.20 × [score] × [conf] = [result]",
    "tech": "0.30 × [score] × [conf] = [result]",
    "raw_total": "float",
    "macro_multiplier": "float from Phase 0",
    "final_score": "raw_total × multiplier = float",
    "high_risk_penalty": "× 0.8 if high_risk = true",
    "risk_adjusted_score": "float"
  },
  "avg_confidence": "float",
  "final_decision": "BUY | HOLD | SELL",
  "decision_margin": "e.g. BUY by 0.4 margin"
}
```

---

## PHASE 4 — EXECUTION & RISK MANAGEMENT

**Agents**: Trader Agent + Risk Manager

```json
{
  "phase": 4,
  "ticker": "STRING",
  "trade_plan": {
    "entry_conditions": {
      "trigger_type": "LIMIT | MARKET | BREAKOUT",
      "price_must_be_above": "20MA | 50MA | none",
      "volume_confirmation_required": "true | false",
      "max_spread_pct": 0.003,
      "entry_range": ["min_price", "max_price"],
      "entry_notes": "string"
    },
    "take_profit": "price",
    "stop_loss": "price",
    "risk_reward_ratio": "float — must be >= 2.0",
    "time_horizon": "short | mid | long",
    "exit_conditions": "string"
  },
  "risk_audit": {
    "risk_level": "LOW | MEDIUM | HIGH",
    "volatility_flag": "true if regime = VOLATILE or RISK_OFF",
    "max_drawdown_allowed_pct": 0.02,
    "position_size_pct": "0.00–0.10",
    "position_size_cap": "if macro_backdrop_score < -3 → cap at 0.03",
    "binary_risk_rule": "if binary_risks present → reduce position_size_pct 30–50%; if event within 48h → force REJECTED",
    "approval": "APPROVED | REJECTED",
    "rejection_reason": "string if REJECTED"
  }
}
```

---

## PHASE 5 — SESSION EXPORT

**Agent**: Portfolio Manager (PM)

完成後執行：
1. Append 本次 session export JSON 到 `./invest_logs/history.json`（JSON array）
2. 確認 `./invest_logs/YYYY-MM-DD_phase0.json` 已存在
3. 將完整分析報告存為 `../reports/YYYYMMDD_TICKER.md`（含 Phase 0–4、Visualization Table、委員會決議）

```json
{
  "session_export_version": "V4.4",
  "export_date": "YYYY-MM-DD",
  "phase0_file": "./invest_logs/YYYY-MM-DD_phase0.json",
  "phase0_macro_snapshot": {
    "market_regime": "string",
    "macro_backdrop_score": "float",
    "key_themes": [],
    "macro_multiplier": "float"
  },
  "trades_this_session": [
    {
      "ticker": "STRING",
      "final_action": "EXECUTE | CANCEL",
      "final_score": "float",
      "final_decision": "BUY | HOLD | SELL",
      "avg_confidence": "float",
      "entry_range": ["min", "max"],
      "take_profit": "float",
      "stop_loss": "float",
      "risk_reward_ratio": "float",
      "position_size_pct": "float",
      "time_horizon": "short | mid | long",
      "macro_context": "string",
      "trade_metadata": {
        "trade_type": "event | trend | mean_reversion",
        "event_tag": "FOMC | earnings | tariff | ceasefire | optional"
      }
    }
  ],
  "active_weights_end_of_session": {
    "Fundamentals": 0.30,
    "Sentiment": 0.20,
    "News": 0.20,
    "Technical": 0.30
  },
  "bias_notes": "string",
  "last_outcome": "WIN | LOSS | UNKNOWN"
}
```

---

## PHASE 6 — CONTINUOUS LEARNING

**Trigger**: `TRADE_RESULT: ticker=XXX result=WIN|LOSS`

**Agent**: Portfolio Manager (PM)

```json
{
  "phase": 6,
  "ticker": "STRING",
  "outcome": "WIN | LOSS",
  "primary_failure_agent": "Fundamentals | Sentiment | News | Technical | Risk_Manager | timing | macro_model",
  "what_was_missed": "string",
  "contributing_factors": ["factor1", "factor2"],
  "weight_adjustment_delta": {
    "Fundamentals": "-0.05 to +0.05",
    "Sentiment": "-0.05 to +0.05",
    "News": "-0.05 to +0.05",
    "Technical": "-0.05 to +0.05"
  },
  "updated_weights_for_next_session": {
    "Fundamentals": "current + delta",
    "Sentiment": "current + delta",
    "News": "current + delta",
    "Technical": "current + delta"
  },
  "lesson_learned": "string",
  "instruction": "將 updated_weights_for_next_session 寫入 history.json 最新一筆的 active_weights_end_of_session 欄位。"
}
```

**Weight 限制**: 單一 agent 0.10–0.50，每次調整 ±0.05 以內，四個總和必須 = 1.0。

---

## FINAL VISUALIZATION TABLE

```
| Agent        | Signal | Score | Confidence | Key Factors (top 2)  | Phase 0 Alignment |
|--------------|--------|-------|------------|----------------------|-------------------|
| Fundamentals |        |       |            |                      |                   |
| Sentiment    |        |       |            |                      |                   |
| News         |        |       |            |                      |                   |
| Technical    |        |       |            |                      |                   |

| RESULT | Decision | Raw Score | Multiplier | Final Score | Position Size | Action          |
|--------|----------|-----------|------------|-------------|---------------|-----------------|
|        | BUY/HOLD |   float   |   float    |    float    |      %        | EXECUTE / CANCEL|
```

---

*End of Protocol V4.3*