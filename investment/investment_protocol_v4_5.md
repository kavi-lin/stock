# Multi-Agent Investment Protocol (V4.5)

> **Changelog from V4.4**
> - Phase 2: 新增第五 Agent「Contrarian Analyst (Burry)」，使用 `short-contrarian-analyst` skill
> - Phase 2: Sentiment Agent 新增 `market-sentiment-analyzer` skill 作為 fallback
> - Phase 2.5: 新增 T4 觸發條件（Burry Score ≤ 2 AND BUY）
> - Phase 4: Risk Audit 新增 vol-adjusted position sizing（`portfolio-risk-manager`）
> - Phase 4: Risk Audit 新增尾部風險評估（`tail-risk-analyzer`）
> - Final Viz Table: 新增 Contrarian 列

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

| Agent | Responsibility | Skill |
|---|---|---|
| Global News Intelligence | Phase 0 macro backdrop | `market-news-analyst` |
| Fundamentals Analyst | Valuation, balance sheet, growth | `us-stock-analysis` |
| Sentiment Analyst | Market-wide + stock-specific sentiment | `market-sentiment-analyzer` |
| News Analyst | Macro events, CPI/Fed, geopolitical | `market-news-analyst` |
| Technical Analyst | Price action, RSI, MACD, volume | — |
| **Contrarian Analyst (Burry)** | **估值錨：FCF yield、EV/EBIT、內部人、逆向情緒** | **`short-contrarian-analyst`** |
| Trader Agent | Entry/exit planner | — |
| Risk Manager | Position sizer & safety auditor | `portfolio-risk-manager`, `tail-risk-analyzer` |
| Portfolio Manager (PM) | Decision, weight control, export | — |

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
    { "rank": 5, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" }
  ],
  "bearish_signals": [
    { "rank": 1, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 2, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 3, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 4, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" },
    { "rank": 5, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" }
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

> **Note**: Contrarian Analyst (Burry) 不參與加權計算，作為獨立 veto check 使用。

---

## PHASE 2 — ANALYST MULTI-AGENT CORE

**Agents**: Fundamentals / Sentiment / News / Technical / **Contrarian (Burry)**

**五個 Analyst 全部執行，輸出統一格式（Contrarian 另見下方額外 schema）**:

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

**各 Analyst 聚焦範圍與建議 skill**:

- **Fundamentals**: P/E vs sector, revenue growth YoY, FCF, debt/equity, next earnings date
  → 優先使用 `us-stock-analysis` skill

- **Sentiment**: 市場整體情緒 + 個股特定情緒（雙層融合）
  → **優先**從 `sector_intel.json` 讀取 `fear_greed_status`（若存在）
  → `sector_intel.json` 不存在時：執行 `market-sentiment-analyzer` skill，取 `composite_score`（0–100）作為市場基底
  → 個股層級：web search（Reddit/X mention volume, short interest %, insider sentiment）
  → 最終 Sentiment Score = `0.4 × stock_specific_score + 0.6 × (market_composite/10 - 5)`
    （市場 composite 0–100 映射為 -5 至 +5）
  → 額外輸出：`market_sentiment_composite: 0–100`、`vix_current: float`

- **News**: Company news 48h, analyst upgrades/downgrades, cross-ref Phase 0 key_themes
  → 優先使用 `market-news-analyst` skill，或從 `sector_intel.json` `top_catalysts` 提取相關條目

- **Technical**: Price vs 20/50/200MA, RSI(14), MACD crossover, volume vs 20-day avg, nearest support/resistance
  → 若有週線圖 → 使用 `technical-analyst` skill；無圖則 web search

**Contrarian Analyst（Burry）— 額外 schema**:

執行 `short-contrarian-analyst` skill，輸出以下結構：

```json
{
  "phase": 2,
  "agent": "Contrarian_Analyst_Burry",
  "ticker": "STRING",
  "burry_score": "0–12",
  "burry_signal": "STRONGLY BULLISH | BULLISH | NEUTRAL | BEARISH | STRONGLY BEARISH",
  "value_analysis": {
    "fcf_yield_pct": "float — 正值好，>10% 強烈看多",
    "ev_ebit_multiple": "float — 低值好，<6x 強烈看多",
    "value_pts": "0–6"
  },
  "balance_sheet": {
    "debt_to_equity": "float",
    "net_cash_positive": "true | false",
    "balance_pts": "0–3"
  },
  "insider_activity": {
    "net_activity": "BUYING | NEUTRAL | SELLING",
    "insider_pts": "0–2"
  },
  "contrarian_sentiment": {
    "news_tone": "NEGATIVE | MIXED | POSITIVE",
    "contrarian_pts": "0–1",
    "note": "負面新聞 = 潛在逆向機會；正面新聞 = 人群擁擠警告"
  },
  "burry_voice": "string — 用 Burry 簡潔語氣的一句評語",
  "veto_flag": "true if burry_score ≤ 2 — 觸發 Phase 2.5 T4",
  "phase0_alignment": "ALIGNED | MISALIGNED | NEUTRAL",
  "data_source_timestamp": "YYYY-MM-DD HH:MM"
}
```

**Burry Score 解讀**：

| Score | Signal | 含義 |
|---|---|---|
| ≥ 7 | STRONGLY BULLISH | 深度價值，逆向買入高確信度 |
| 5–6 | BULLISH | 估值合理偏低，值得關注 |
| 3–4 | NEUTRAL | 無明顯優勢或劣勢 |
| ≤ 2 | BEARISH | **觸發 veto_flag → Phase 2.5 T4** |

---

## PHASE 2.5 — CONFLICT & BIAS PROTOCOL

**Agent**: Portfolio Manager (PM)

**觸發條件**:
- **T1**: `Sentiment.score > +3` AND `Fundamentals.score < 0`
- **T2**: `News.score < -3` AND `Technical.signal = BUY`
- **T3**: `macro_backdrop_score < -3` AND any `signal = BUY` with `score > +3`
- **T4（新增）**: `Contrarian_Analyst.veto_flag = true` AND `tentative_decision = BUY`
  → 含義：Burry 認為估值嚴重高估（score ≤ 2），與 BUY 決策衝突，強制進行衝突審查
- **Anti-Bias**: 所有 analyst 信號相同時，News Analyst 追加 `devils_advocate: ["reason1","reason2","reason3"]`

```json
{
  "phase": "2.5",
  "agent": "Portfolio_Manager",
  "triggers_fired": ["T1", "T4"],
  "conflict_summary": "one sentence per trigger",
  "t4_detail": {
    "burry_score": "float",
    "burry_concern": "string — 具體說明高估原因（FCF 負、EV/EBIT 過高等）",
    "resolution": "OVERRIDE_BURRY | DOWNGRADE_DECISION | CANCEL"
  },
  "resolution": "string",
  "phase0_macro_flag": "OVERRIDE_ACTIVE | NONE",
  "proceed_to_phase3": "true | false"
}
```

**T4 仲裁規則**：
- `burry_score = 0–1`（極端高估）→ 強烈建議 `resolution: CANCEL`
- `burry_score = 2`（高估）→ PM 可選擇 `DOWNGRADE_DECISION`（BUY → HOLD）或 `OVERRIDE_BURRY`（需提供明確理由）
- `OVERRIDE_BURRY` 需在 `t4_detail.resolution` 說明為何動能/基本面超越估值疑慮

`proceed_to_phase3 = false` → 直接跳至 Phase 5，輸出 `CANCEL`。

---

## PHASE 3 — DECISION ENGINE

**Agent**: Portfolio Manager (PM)

**公式**: `FinalScore = Σ(Weight_i × Score_i × Confidence_i) × macro_multiplier`

> Contrarian Analyst 不納入加權，僅透過 T4 影響決策。

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
  "decision_margin": "e.g. BUY by 0.4 margin",
  "contrarian_note": "Burry Score [X/12] — [brief implication]"
}
```

---

## PHASE 4 — EXECUTION & RISK MANAGEMENT

**Agents**: Trader Agent + Risk Manager

### Step 1 — Trade Plan（Trader Agent，不變）

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
  }
}
```

### Step 2 — Vol-Adjusted Position Sizing（新增，Risk Manager）

**觸發條件**：使用者有多個持倉，或本次分析需要精確倉位計算時執行。
**執行**：`portfolio-risk-manager` skill（傳入 ticker + 現有持倉 tickers）

取回以下數值用於 Step 3：
- `vol_adjusted_limit_pct`：基於波動率的基礎上限
- `correlation_multiplier`：相關性調整係數（0.7x / 0.9x / 1.1x）
- `final_position_limit_pct` = `vol_adjusted_limit_pct × correlation_multiplier`

**波動率閾值**（與 portfolio-risk-manager 一致）：

| 年化波動率 | 基礎倉位上限 |
|---|---|
| > 50% | 5% |
| > 30% | 10% |
| > 中位數 | 15% |
| ≤ 中位數 | 25% |

**相關性調整**：
- > 0.7（高相關）→ × 0.7
- 0.4–0.7（中等）→ × 0.9
- < 0.4（低相關）→ × 1.1

### Step 3 — Tail Risk Assessment（新增，Risk Manager）

**執行**：`tail-risk-analyzer` skill（per-stock mode，傳入 ticker）

取回 `fragility_label` 並調整 `position_size_pct`：

| Fragility Label | 倉位調整 |
|---|---|
| EXTREMELY FRAGILE | × 0.5 |
| FRAGILE | × 0.75 |
| RESILIENT | × 1.0（不調整）|
| ANTIFRAGILE | × 1.1（若 PM 高確信度）|

### Step 4 — Risk Audit（整合輸出）

最終 position_size_pct 計算邏輯：
```
base = vol_adjusted_limit（若有執行 Step 2）或 0.05（DEFAULT）
tail_adjusted = base × fragility_multiplier
macro_capped = min(tail_adjusted, 0.03 if macro_backdrop_score < -3)
binary_adjusted = macro_capped × 0.5–0.7 if binary_risk present
final_position_size = binary_adjusted
```

```json
{
  "phase": 4,
  "risk_audit": {
    "risk_level": "LOW | MEDIUM | HIGH",
    "volatility_flag": "true if regime = VOLATILE or RISK_OFF",
    "max_drawdown_allowed_pct": 0.02,
    "vol_adjusted_limit_pct": "from portfolio-risk-manager (null if not executed)",
    "correlation_multiplier": "float | null",
    "position_size_method": "VOL_ADJUSTED | RULE_BASED",
    "tail_risk": {
      "fragility_label": "ANTIFRAGILE | RESILIENT | FRAGILE | EXTREMELY FRAGILE",
      "tail_risk_score": "float 0–100",
      "fragility_adjustment": "× 1.1 | × 1.0 | × 0.75 | × 0.5",
      "key_tail_flags": ["string — e.g. fat_tail, high_leverage, negative_skew"]
    },
    "position_size_pct": "final float 0.00–0.10",
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
  "session_export_version": "V4.5",
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
      "burry_score": "float",
      "entry_range": ["min", "max"],
      "take_profit": "float",
      "stop_loss": "float",
      "risk_reward_ratio": "float",
      "position_size_pct": "float",
      "position_size_method": "VOL_ADJUSTED | RULE_BASED",
      "fragility_label": "string",
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
  "primary_failure_agent": "Fundamentals | Sentiment | News | Technical | Contrarian | Risk_Manager | timing | macro_model",
  "what_was_missed": "string",
  "contributing_factors": ["factor1", "factor2"],
  "burry_was_right": "true | false | N/A — 回顧 Burry Score 的預測準確性",
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
| Agent              | Signal | Score | Confidence | Key Factors (top 2)  | Phase 0 Alignment |
|--------------------|--------|-------|------------|----------------------|-------------------|
| Fundamentals       |        |       |            |                      |                   |
| Sentiment          |        |       |            |                      |                   |
| News               |        |       |            |                      |                   |
| Technical          |        |       |            |                      |                   |
| Contrarian (Burry) | —      | X/12  |     —      | FCF X%, EV/EBIT Xx   | ALIGNED/MISALIGNED|

| RESULT | Decision | Raw Score | Multiplier | Final Score | Burry Score | Position Size | Fragility   | Action          |
|--------|----------|-----------|------------|-------------|-------------|---------------|-------------|-----------------|
|        | BUY/HOLD |   float   |   float    |    float    |    X/12     |      %        | RESILIENT   | EXECUTE / CANCEL|
```

---

*End of Protocol V4.5*
