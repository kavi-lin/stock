# Multi-Agent Investment Protocol (V4.5)

## SESSION STARTUP

```
SESSION CONFIG
──────────────────────────────────────────
RISK_TOLERANCE : LOW | MEDIUM | HIGH
──────────────────────────────────────────
```

Ticker 由使用者在對話中直接指定。

---

## GLOBAL RULES

1. **Phase Execution Order**: 0 → 1 → 2 → 2.5 → 3 → 4 → 5。絕不跳過。
2. **Phase 0 Cache（三層優先順序）**:
   - 層 1：`../sector/sector_logs/YYYY-MM-DD_sector_intel.json` 存在且日期符合 → 提取 macro context，跳過 web search（`phase0_source: SECTOR_CACHE`）
   - 層 2：`./invest_logs/YYYY-MM-DD_phase0.json` 存在且日期符合 → 載入（`phase0_source: INVEST_CACHE`）
   - 層 3：皆無 → 執行 web search，寫入 `./invest_logs/YYYY-MM-DD_phase0.json`（`phase0_source: FRESHLY_EXECUTED`）
3. **Theme Cache**: 需要主題熱度時，先搜尋 `../skills/theme-detector/cache/theme_detector_YYYY-MM-DD_*.json`。找到 → 載入（`theme_source: THEME_CACHE`）；未找到 → 執行 skill，JSON cache 存入 `../skills/theme-detector/cache/`，MD 移至 `../reports/` 並重命名為 `YYYYMMDD_theme_detector_HHMMSS.md`。
4. **Prior Session**: 讀取 `./invest_logs/history.json`，取最近一筆作為 prior context。
5. **Output Format**: 邏輯輸出為 JSON；Markdown 僅用於最終 Visualization Table。
6. **key_factors**: 最多 3 條，每條最多 8 個英文單字。
7. **Phase 5**: session export 只存結果，不重複 Phase 3 計算。
8. **MD Report**（強制）: Phase 5 完成後，將完整分析存為 `../reports/YYYYMMDD_TICKER.md`（例：`20260410_CRWV.md`）。不得省略。

---

## TEAM STRUCTURE

| Agent | Responsibility | Skill |
|---|---|---|
| Global News Intelligence | Phase 0 macro backdrop | `market-news-analyst` |
| Fundamentals Analyst | Valuation, balance sheet, growth | `us-stock-analysis` |
| Sentiment Analyst | Market + stock-specific sentiment | `market-sentiment-analyzer` |
| News Analyst | Macro events, CPI/Fed, geopolitical | `market-news-analyst` |
| Technical Analyst | Price action, RSI, MACD, volume | `technical-analyst` |
| Contrarian Analyst (Burry) | 估值錨：FCF yield、EV/EBIT、內部人、逆向情緒 | `short-contrarian-analyst` |
| Trader Agent | Entry/exit planner | — |
| Risk Manager | Position sizer & safety auditor | `portfolio-risk-manager`, `tail-risk-analyzer` |
| Portfolio Manager (PM) | Decision, weight control, export | — |

---

## PHASE 0 — GLOBAL NEWS INTELLIGENCE

**三層 cache 檢查（依序執行）**：

1. `../sector/sector_logs/YYYY-MM-DD_sector_intel.json`
   - `verdict_date` = 今日 → 提取 `market_regime`, `exposure_ceiling`, `political_risk_summary`, `actionable_themes`, `session_notes` 作為 macro context，將 hot/cold sectors 填入 `macro_summary`，跳過 web search → Phase 1
2. `./invest_logs/YYYY-MM-DD_phase0.json`
   - `scan_date` = 今日 → 直接載入 → Phase 1
3. 皆無 → 執行 web search（優先用 `market-news-analyst` skill），寫入 `./invest_logs/YYYY-MM-DD_phase0.json`

**Web search queries（層 3）**:
- `market-news-analyst` skill，或逐條：
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
    { "rank": 1, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" }
  ],
  "bearish_signals": [
    { "rank": 1, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" }
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

> bullish_signals / bearish_signals 各輸出 rank 1–5，共 10 條。

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

Contrarian Analyst (Burry) 不參與加權，僅作為獨立 veto check。

---

## PHASE 2 — ANALYST MULTI-AGENT CORE

**Agents**: Fundamentals / Sentiment / News / Technical / Contrarian (Burry)

**統一輸出格式（Contrarian 另見下方）**:

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

**各 Analyst 聚焦範圍與 skill**:

- **Fundamentals**: P/E vs sector, revenue growth YoY, FCF, debt/equity, next earnings date → `us-stock-analysis`
- **Sentiment**: 市場 + 個股雙層融合
  - 優先從 `sector_intel.json` 讀 `fear_greed_status`
  - 不存在時：`market-sentiment-analyzer` skill，取 `composite_score`（0–100）作為市場基底
  - 個股層級：web search（Reddit/X mention volume, short interest %, insider sentiment）
  - `Sentiment Score = 0.4 × stock_specific_score + 0.6 × (market_composite/10 - 5)`
  - 額外輸出：`market_sentiment_composite: 0–100`、`vix_current: float`
- **News**: Company news 48h, analyst upgrades/downgrades, cross-ref Phase 0 key_themes → `market-news-analyst` 或從 `sector_intel.json.top_catalysts` 提取
- **Technical**: Price vs 20/50/200MA, RSI(14), MACD, volume vs 20-day avg, support/resistance → 有週線圖用 `technical-analyst`，無則 web search

**Contrarian Analyst (Burry)** — 執行 `short-contrarian-analyst` skill：

```json
{
  "phase": 2,
  "agent": "Contrarian_Analyst_Burry",
  "ticker": "STRING",
  "burry_score": "0–12",
  "burry_signal": "STRONGLY BULLISH | BULLISH | NEUTRAL | BEARISH | STRONGLY BEARISH",
  "value_analysis": {
    "fcf_yield_pct": "float",
    "ev_ebit_multiple": "float",
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
    "contrarian_pts": "0–1"
  },
  "burry_voice": "string — 用 Burry 語氣的一句評語",
  "veto_flag": "true if burry_score <= 2",
  "phase0_alignment": "ALIGNED | MISALIGNED | NEUTRAL",
  "data_source_timestamp": "YYYY-MM-DD HH:MM"
}
```

`veto_flag = true`（burry_score ≤ 2）→ 觸發 Phase 2.5 T4。

---

## PHASE 2.5 — CONFLICT & BIAS PROTOCOL

**Agent**: Portfolio Manager (PM)

**觸發條件**:
- **T1**: `Sentiment.score > +3` AND `Fundamentals.score < 0`
- **T2**: `News.score < -3` AND `Technical.signal = BUY`
- **T3**: `macro_backdrop_score < -3` AND any `signal = BUY` with `score > +3`
- **T4**: `Contrarian_Analyst.veto_flag = true` AND `tentative_decision = BUY`
- **Anti-Bias**: 所有 analyst 信號相同時，News Analyst 追加 `devils_advocate: ["reason1","reason2","reason3"]`

```json
{
  "phase": "2.5",
  "agent": "Portfolio_Manager",
  "triggers_fired": ["T1", "T4"],
  "conflict_summary": "one sentence per trigger",
  "t4_detail": {
    "burry_score": "float",
    "burry_concern": "string",
    "resolution": "OVERRIDE_BURRY | DOWNGRADE_DECISION | CANCEL"
  },
  "resolution": "string",
  "phase0_macro_flag": "OVERRIDE_ACTIVE | NONE",
  "proceed_to_phase3": "true | false"
}
```

**T4 仲裁規則**：
- `burry_score = 0–1` → 強烈建議 `CANCEL`
- `burry_score = 2` → `DOWNGRADE_DECISION`（BUY → HOLD）或 `OVERRIDE_BURRY`（需在 `t4_detail.resolution` 說明動能/基本面如何超越估值疑慮）

`proceed_to_phase3 = false` → 跳至 Phase 5，輸出 `CANCEL`。

---

## PHASE 3 — DECISION ENGINE

**Agent**: Portfolio Manager (PM)

**公式**: `FinalScore = Σ(Weight_i × Score_i × Confidence_i) × macro_multiplier`

Contrarian Analyst 不納入加權，僅透過 T4 影響決策。

**Regime Adjustment**: `market_regime = VOLATILE` → `FinalScore × 0.85`

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

### Step 1 — Trade Plan（Trader Agent）

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

### Step 2 — Vol-Adjusted Position Sizing（Risk Manager）

**觸發**：有多個持倉或需精確倉位計算時執行 `portfolio-risk-manager` skill（傳入 ticker + 現有持倉）

取回供 Step 4 使用：
- `vol_adjusted_limit_pct`
- `correlation_multiplier`（0.7x / 0.9x / 1.1x）
- `final_position_limit_pct = vol_adjusted_limit_pct × correlation_multiplier`

### Step 3 — Tail Risk Assessment（Risk Manager）

執行 `tail-risk-analyzer` skill（per-stock mode），取回 `fragility_label` → 倉位倍數：

| Fragility Label | 倉位倍數 |
|---|---|
| EXTREMELY FRAGILE | × 0.5 |
| FRAGILE | × 0.75 |
| RESILIENT | × 1.0 |
| ANTIFRAGILE | × 1.1（僅 PM 高確信度）|

### Step 4 — Risk Audit（整合輸出）

```
base = vol_adjusted_limit（若 Step 2 執行）或 0.05
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
      "key_tail_flags": ["fat_tail | high_leverage | negative_skew"]
    },
    "position_size_pct": "final float 0.00–0.10",
    "position_size_cap": "if macro_backdrop_score < -3 → cap at 0.03",
    "binary_risk_rule": "binary_risks present → reduce 30–50%; within 48h → force REJECTED",
    "approval": "APPROVED | REJECTED",
    "rejection_reason": "string if REJECTED"
  }
}
```

---

## PHASE 5 — SESSION EXPORT

**Agent**: Portfolio Manager (PM)

執行步驟：
1. Append session export JSON 到 `./invest_logs/history.json`
2. 確認 `./invest_logs/YYYY-MM-DD_phase0.json` 已存在
3. 將完整分析存為 `../reports/YYYYMMDD_TICKER.md`（Phase 0–4 + Visualization Table + 委員會決議）

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
  "burry_was_right": "true | false | N/A",
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

**Weight 限制**: 單一 agent 0.10–0.50，每次調整 ±0.05 以內，四個總和 = 1.0。

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
