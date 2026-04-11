# Pre-Market Sector Intelligence Protocol (V1.0)

---

## SESSION STARTUP

```
SESSION CONFIG
──────────────────────────────────────────
RISK_TOLERANCE : LOW | MEDIUM | HIGH
FOCUS_DATE     : [留空 = 今日]
──────────────────────────────────────────
```

> 此 protocol 為**盤前產業熱度分析**，在個股分析（investment_protocol）之前執行。
> 輸出結果可直接作為 investment_protocol Phase 0 的補充 macro context。

---

## GLOBAL RULES

1. **Phase Execution Order**: 0 → 1 → 2 → 3 → 4 → 5。絕不跳過順序。
2. **Cache**: 讀取 `./sector_logs/YYYY-MM-DD_sector_intel.json`。存在且日期符合 → 載入跳過 Phase 0–2，直接從 Phase 3 開始。
3. **Debate Requirement**: Phase 4 必須有至少一個反方論點，禁止純多頭共識。
4. **Fear & Greed Trigger**: 在 Phase 3 結束後，檢查 CNN Fear & Greed Index。若 > 80 或 < 20 → Phase 4 的 Devil's Advocate **強制**提交極端反向論點（不可略過），並在所有 HOT 產業的 `risk_flags` 加入 `extreme_sentiment`。
5. **Output Format**: 邏輯輸出為 JSON，最終 verdict 輸出 Markdown 表格。
6. **Skills Integration**: 各 phase 標明對應的外部 skill，可直接調用其 CSV/data 輸出作為輸入。

---

## TEAM STRUCTURE

| Agent | 職責 | 對應 Skill |
|---|---|---|
| Macro Regime Analyst | 總體市場健康度、制度判斷 | `uptrend-analyzer`, `market-breadth-analyzer` |
| Sector Rotation Analyst | 產業輪動、週期定位 | `sector-analyst` |
| Theme Intelligence Analyst | 跨產業主題熱度與生命週期 | `theme-detector` |
| News Catalyst Analyst | 48h 新聞、財報催化劑 | `market-news-analyst`, `economic-calendar-fetcher` |
| Devil's Advocate | 挑戰多頭共識、提出反方論點 | — |
| Portfolio Strategist (PS) | 最終產業裁決、輸出報告 | `exposure-coach` |

---

## PHASE 0 — MARKET REGIME CHECK

**Agent**: Macro Regime Analyst

讀取 `./sector_logs/YYYY-MM-DD_sector_intel.json`：
- 存在且日期符合 → 載入，跳至 Phase 3
- 否則 → 執行以下分析並寫入檔案

**資料來源**（優先順序）：
1. `uptrend-analyzer` CSV 輸出（~2,800 股上升趨勢比率）
2. `market-breadth-analyzer` 6 組件評分
3. Web search: "US market breadth today", "S&P 500 advance decline today"

```json
{
  "phase": 0,
  "agent": "Macro_Regime_Analyst",
  "scan_date": "YYYY-MM-DD",
  "breadth_score": "0–100",
  "breadth_components": {
    "overall_breadth": "0–100",
    "sector_participation": "0–100",
    "momentum": "0–100",
    "mean_reversion_risk": "0–100"
  },
  "market_regime": "BULL | BEAR | SIDEWAYS | VOLATILE | RISK_OFF | RISK_ON",
  "cycle_phase": "Early | Mid | Late | Recession",
  "uptrend_ratio_overall": "float 0.0–1.0",
  "warning_flags": ["Late_Cycle", "High_Selectivity", "Narrowing_Breadth"],
  "exposure_ceiling": "0–100%",
  "regime_confidence": "0.0–1.0"
}
```

---

## PHASE 1 — SECTOR ROTATION SCAN

**Agent**: Sector Rotation Analyst

**資料來源**: `sector-analyst` CSV（不需 API key）

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

## PHASE 2 — THEME INTELLIGENCE

**Agent**: Theme Intelligence Analyst

**Theme-Detector Cache Check（執行 skill 前必須先做）**：
1. 以今日日期搜尋 `../skills/theme-detector/cache/theme_detector_YYYY-MM-DD_*.json`
   - **找到** → 直接載入 JSON，`theme_source: THEME_CACHE`，**跳過 skill 執行**，前往填寫下方 JSON
   - **未找到** → 執行 `theme-detector` skill（FINVIZ Elite 優先，公開模式備用）
     - JSON cache → 存入 `../skills/theme-detector/cache/`
     - MD 最終報告 → 移至 `../reports/`，並重新命名為 `YYYYMMDD_theme_detector_HHMMSS.md`

**資料來源**: `theme-detector` skill（FINVIZ Elite 優先，公開模式備用）

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

## PHASE 3 — NEWS CATALYST REVIEW

**Agent**: News Catalyst Analyst

**資料來源**: `market-news-analyst`（WebSearch，10 天內）、`economic-calendar-fetcher`（未來 7 天）

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
    "named_targets": ["TICKER or COUNTRY被點名受威脅"],
    "fear_greed_index": "0–100",
    "fear_greed_label": "Extreme_Fear | Fear | Neutral | Greed | Extreme_Greed",
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

**Phase 3 必須執行的 web search queries**:
- `market-news-analyst` 標準查詢（10 天內市場新聞）
- `economic-calendar-fetcher` 或 web search: "upcoming FOMC CPI NFP dates"
- Web search: "Trump tariff statement today" / "Trump Truth Social market"
- Web search: "CNN Fear Greed Index today"
- Web search: "sector named threat Trump today" （若有政治事件）

---

## PHASE 4 — MULTI-AGENT DEBATE

**Agent**: Portfolio Strategist (PS) 主持，各 agent 輪流發言

**必須完成的辯論流程**：

### Step 1 — 各 Agent 提案

每位 analyst 提交對產業的「強烈看法」（不得全部 neutral）：

```json
{
  "phase": "4a",
  "agent": "Sector_Rotation_Analyst | Theme_Intelligence_Analyst | News_Catalyst_Analyst",
  "top_conviction_hot": ["sector1", "sector2"],
  "top_conviction_cold": ["sector1", "sector2"],
  "key_rationale": "string — 最多 2 句"
}
```

### Step 2 — Devil's Advocate

```json
{
  "phase": "4b",
  "agent": "Devils_Advocate",
  "challenge_targets": [
    {
      "challenged_sector": "string",
      "challenged_call": "HOT | COLD",
      "counter_evidence": "string",
      "risk_scenario": "string"
    }
  ],
  "consensus_warning": "true | false — 所有 agent 都看多同一板塊時必須為 true"
}
```

### Step 3 — PS 仲裁 & 權重整合

```json
{
  "phase": "4c",
  "agent": "Portfolio_Strategist",
  "debate_resolution": "string",
  "devils_advocate_accepted": ["sector1"],
  "devils_advocate_rejected": ["sector1"],
  "final_regime_stance": "AGGRESSIVE | NEUTRAL | DEFENSIVE"
}
```

**仲裁規則**：
- `exposure_ceiling < 40%` → 至少 3 個產業標記 AVOID
- `cycle_phase = Late | Recession` → Defensive 產業加分，Cyclical 降分
- `upcoming_binary_risks` 含 within_48h → 相關產業降一級

---

## PHASE 5 — SECTOR VERDICT

**Agent**: Portfolio Strategist (PS)

完成後執行：
1. 寫入 `./sector_logs/YYYY-MM-DD_sector_intel.json`（cache，供其他 protocol 讀取）
2. 將 FINAL VERDICT TABLE 存為 `../reports/YYYY-MM-DD_sector_report.md`

```json
{
  "verdict_date": "YYYY-MM-DD",
  "market_regime": "from Phase 0",
  "exposure_ceiling": "from Phase 0",
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
      "proxy_etf": "string",
      "risk_flags": ["binary_risk_within_48h", "late_cycle", "overbought"]
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
      "description": "string — 消息面與價格行為背離的一句說明",
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

---

## SCORING RUBRIC

| Composite Score | Verdict | 行動建議 |
|---|---|---|
| 75–100 | HOT | 積極尋找個股進場機會 |
| 50–74 | WARM | 選股謹慎，等待更好時機 |
| 25–49 | COLD | 減少暴露，避免新建倉 |
| 0–24 | AVOID | 清倉或嚴格停損 |

**Sector Composite Score 計算**：
```
Score = breadth_momentum(25) + theme_heat(25) + news_catalyst(25) + rotation_signal(25)
若 cycle_phase = Late/Recession + 屬於 Cyclical → Score × 0.85
若 binary_risk_within_48h → Score × 0.70
```

---

## FINAL VERDICT TABLE

```
| Sector      | Verdict | Score | Key Reasons (top 2)       | Proxy ETF | Risk Flags |
|-------------|---------|-------|---------------------------|-----------|------------|
| Technology  | HOT     |  82   | AI capex cycle intact...  | XLK       |            |
| Energy      | COLD    |  38   | Demand slowdown, tariff.. | XLE       | binary_48h |

Market Regime: RISK_ON | Exposure Ceiling: 70% | Cycle: Mid

TOP THEMES TODAY: [theme1] [theme2]
HANDOFF TO INVESTMENT PROTOCOL: "市場 RISK_ON，科技與工業強，能源避開。"
```

---

## 本地檔案結構

```
sector/
└── sector_logs/
    ├── YYYY-MM-DD_sector_intel.json   ← 當日產業分析 cache（中繼，Claude 自動讀寫）
    └── sector_history.json            ← 歷史 verdict 紀錄（選擇性 append）

reports/                               ← 最終報告集中存放
└── YYYY-MM-DD_sector_report.md        ← FINAL VERDICT TABLE（人類可讀）
```

---

*End of Pre-Market Sector Intelligence Protocol V1.0*
