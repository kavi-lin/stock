# Pre-Market Sector Intelligence Protocol (V1.1)

> **Changelog from V1.0**
> - Phase 3: `fear_greed_index` 改由 `market-sentiment-analyzer` skill 提供（取代 web search），並新增 VIX、Put/Call Ratio 欄位
> - Phase 4b: Devil's Advocate 新增 `tail-risk-analyzer` 量化支撐——對 HOT 產業（分數 > 75）的 proxy ETF 跑尾部風險，強制挑戰高分板塊
> - `extreme_sentiment_triggered` 判斷改用 `market-sentiment-analyzer` composite score

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
2. **Cache**: 讀取 `./sector_logs/YYYY-MM-DD_sector_intel.json`。存在且日期符合 → 載入跳過 Phase 0–1（廣度與輪動可快取），直接從 Phase 2 開始。**Phase 3（新聞催化劑）永遠重新執行，不可因快取跳過** — 新聞是即時的。
3. **Debate Requirement**: Phase 4 必須有至少一個反方論點，禁止純多頭共識。
4. **Extreme Sentiment Trigger（更新）**: 在 Phase 3 執行 `market-sentiment-analyzer` 後，使用 **composite_score** 判斷：
   - `composite_score > 80` 或 `composite_score < 20` → `extreme_sentiment_triggered = true`
   - 觸發後：Phase 4b Devil's Advocate **強制**提交極端反向論點，所有 HOT 產業 `risk_flags` 加入 `extreme_sentiment`
5. **Output Format**: 邏輯輸出為 JSON，最終 verdict 輸出 Markdown 表格。
6. **Skills Integration**: 各 phase 標明對應的外部 skill，可直接調用其 CSV/data 輸出作為輸入。

---

## TEAM STRUCTURE

| Agent | 職責 | 對應 Skill |
|---|---|---|
| Macro Regime Analyst | 總體市場健康度、制度判斷 | `uptrend-analyzer`, `market-breadth-analyzer` |
| Sector Rotation Analyst | 產業輪動、週期定位 | `sector-analyst` |
| Theme Intelligence Analyst | 跨產業主題熱度與生命週期 | `theme-detector` |
| News Catalyst Analyst | 48h 新聞、財報催化劑、**市場情緒儀表板** | `market-news-analyst`, `economic-calendar-fetcher`, **`market-sentiment-analyzer`** |
| Devil's Advocate | 挑戰多頭共識、提出反方論點、**量化尾部風險** | **`tail-risk-analyzer`** |
| Portfolio Strategist (PS) | 最終產業裁決、輸出報告 | — |

---

## PHASE 0 — MARKET REGIME CHECK

**Agent**: Macro Regime Analyst

讀取 `./sector_logs/YYYY-MM-DD_sector_intel.json`：
- 存在且日期符合 → 載入，跳至 Phase 2（Phase 3 仍需重新執行）
- 否則 → 執行以下分析並寫入檔案

**資料來源**（優先順序）：

### 層 A — market-breadth-analyzer script（優先，量化）
1. 檢查 `./breadth_cache/market_breadth_YYYY-MM-DD_*.json` 是否存在且日期符合今日
   - **存在** → 直接讀取，跳至「欄位映射」步驟
   - **不存在** → 執行腳本（約 5 秒）：
     ```bash
     python3 ~/.claude/skills/market-breadth-analyzer/scripts/market_breadth_analyzer.py \
       --output-dir ./breadth_cache/
     ```
     完成後讀取產出的 `market_breadth_YYYY-MM-DD_*.json`

### 層 B — uptrend-analyzer（補充 uptrend_ratio_overall）
2. 執行 `uptrend-analyzer` skill 取得 `uptrend_ratio_overall`（各產業上升趨勢比率）
   - 若無法執行 → 用 `breadth_analyzer.components.breadth_level_trend.current_8ma` 作為代理值

### 層 C — Web search（最後手段，已有 A+B 則跳過）
3. Web search: "US market breadth today", "S&P 500 advance decline today"

---

### 欄位映射（market-breadth-analyzer → phase0 JSON）

| Phase0 欄位 | 來源路徑 | 說明 |
|---|---|---|
| `breadth_score` | `composite.composite_score` | 0–100 複合分數 |
| `breadth_components.overall_breadth` | `composite.composite_score` | 同複合分數 |
| `breadth_components.sector_participation` | `composite.component_scores.breadth_level_trend.score` | 廣度水位 |
| `breadth_components.momentum` | `composite.component_scores.ma_crossover.score` | 8MA vs 200MA 動能 |
| `breadth_components.mean_reversion_risk` | `100 - composite.component_scores.cycle_position.score` | 週期位置反轉 → 風險 |
| `exposure_ceiling` | `composite.exposure_guidance` | 如 "40-60%" |
| `uptrend_ratio_overall` | `components.breadth_level_trend.current_8ma` | 8MA 作為代理（若無 uptrend-analyzer） |
| `cycle_phase` | 由 `components.cycle_position.signal` 推斷（見下） | Early/Mid/Late/Recession |
| `warning_flags` | 由各組件信號推斷（見下） | 量化觸發 |
| `regime_confidence` | data_quality: Complete=0.9, Partial=0.7, Limited=0.4 | 資料完整度 |

**cycle_phase 推斷規則**：
- signal 含 "extreme_trough" 或 "TROUGH" → `"Early"`
- signal 含 "PEAK" 且含 "recovery" → `"Mid"`
- signal 含 "PEAK" 且不含 "recovery" → `"Late"`
- 其他 → `"Mid"`

**warning_flags 量化觸發規則**：
- `components.bearish_signal.signal_active = true` → `"Bearish_Signal_Active"`
- `components.ma_crossover.gap < 0`（8MA 低於 200MA）→ `"Below_200MA"`
- `components.historical_percentile.percentile_rank < 30` → `"Low_Historical_Percentile"`
- `components.divergence.early_warning = true` → `"Early_Warning_Divergence"`
- `composite.zone = "Critical"` → `"Critical_Zone"`
- `composite.zone = "Weakening"` → `"Weakening_Zone"`

```json
{
  "phase": 0,
  "agent": "Macro_Regime_Analyst",
  "scan_date": "YYYY-MM-DD",
  "breadth_source": "market-breadth-analyzer | uptrend-analyzer | web_search",
  "breadth_score": "0–100 (composite.composite_score)",
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
  "warning_flags": ["Bearish_Signal_Active", "Below_200MA", "Low_Historical_Percentile"],
  "exposure_ceiling": "40-60% (from composite.exposure_guidance)",
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
1. 以今日日期搜尋 `skills/theme-detector/cache/theme_detector_YYYY-MM-DD_*.json`
   - **找到** → 直接載入 JSON，`theme_source: THEME_CACHE`，**跳過 skill 執行**，前往填寫下方 JSON
   - **未找到** → 執行 `theme-detector` skill（FINVIZ Elite 優先，公開模式備用）
     - JSON cache → 存入 `skills/theme-detector/cache/`
     - MD 最終報告 → 移至 `reports/`，並重新命名為 `YYYYMMDD_theme_detector_HHMMSS.md`

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

## PHASE 3 — NEWS CATALYST REVIEW（已更新）

**Agent**: News Catalyst Analyst

**資料來源**:
- `market-news-analyst`（WebSearch，10 天內）
- `economic-calendar-fetcher`（未來 7 天）
- **`market-sentiment-analyzer` skill（新增，取代 web search 的 F&G 查詢）**

### 市場情緒儀表板（Phase 3 開始時執行）

> ⚠️ **Phase 3 強制執行規則（每次都跑，不可用快取跳過）**：
> 1. `market-sentiment-analyzer` skill — 取得即時情緒數值
> 2. `market-news-analyst` skill — 取得近 10 天新聞（**必須呼叫 skill，禁止用訓練資料中的舊新聞**）
> 3. `top_catalysts` 最少 5 筆，全部來自 skill 的 WebSearch 結果

**執行 `market-sentiment-analyzer` skill**，取回以下數值，填入 `political_overlay` 欄位：

從 skill 輸出中提取：
- `composite_score` → `fear_greed_index`（0–100）
- `composite_score label` → `fear_greed_label`
- `vix.current` → `vix_current`（新欄位）
- `put_call_ratio.equity_pc_ratio` → `put_call_ratio`（新欄位）
- `spy_momentum.rsi_14` → `spy_rsi`（新欄位）

**extreme_sentiment 判斷**：`composite_score > 80 OR composite_score < 20` → `extreme_sentiment_triggered = true`

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
    "fear_greed_index": "0–100 (from market-sentiment-analyzer composite_score)",
    "fear_greed_label": "Extreme_Fear | Fear | Neutral | Greed | Extreme_Greed",
    "vix_current": "float (from market-sentiment-analyzer)",
    "put_call_ratio": "float (from market-sentiment-analyzer)",
    "spy_rsi": "float (from market-sentiment-analyzer)",
    "sentiment_source": "SECTOR_CACHE | SKILL_EXECUTED | WEB_SEARCH_FALLBACK",
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

**Phase 3 執行清單**:
- `market-sentiment-analyzer` skill（取代 "Web search: CNN Fear Greed Index today"）
- `market-news-analyst` 標準查詢（10 天內市場新聞）
- `economic-calendar-fetcher` 或 web search: "upcoming FOMC CPI NFP dates"
- Web search: "Trump tariff statement today" / "Trump Truth Social market"
- Web search: "sector named threat Trump today"（若有政治事件）

---

## PHASE 4 — MULTI-AGENT DEBATE（已更新）

**Agent**: Portfolio Strategist (PS) 主持，各 agent 輪流發言

### Step 1 — 各 Agent 提案（不變）

```json
{
  "phase": "4a",
  "agent": "Sector_Rotation_Analyst | Theme_Intelligence_Analyst | News_Catalyst_Analyst",
  "top_conviction_hot": ["sector1", "sector2"],
  "top_conviction_cold": ["sector1", "sector2"],
  "key_rationale": "string — 最多 2 句"
}
```

### Step 2 — Devil's Advocate（已更新，加入量化尾部風險）

**新增：Tail Risk 觸發規則**

在 Devil's Advocate 準備反方論點前，對所有 `composite_score > 75` 的 HOT 產業執行尾部風險檢查：

```
對每個 HOT 產業（composite_score > 75）的 proxy_etf：
→ 執行 tail-risk-analyzer skill（per-stock mode，傳入 proxy_etf ticker）
→ 若 fragility_label = FRAGILE 或 EXTREMELY FRAGILE → 必須將此產業加入 challenge_targets
→ 若 tail_risk_score > 70 OR excess_kurtosis > 5 → 加入 risk_flags: "fat_tail_warning"
→ 若 2020 COVID 情境回測下跌 > 40% → 加入 risk_flags: "crash_vulnerability"
```

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
      "tail_risk_source": "SKILL_EXECUTED | SKIPPED_LOW_SCORE"
    }
  ],
  "challenge_targets": [
    {
      "challenged_sector": "string",
      "challenged_call": "HOT | COLD",
      "counter_evidence": "string",
      "tail_risk_evidence": "string — 來自 tail-risk-analyzer 的量化支撐（若有）",
      "risk_scenario": "string"
    }
  ],
  "consensus_warning": "true | false — 所有 agent 都看多同一板塊時必須為 true"
}
```

### Step 3 — PS 仲裁 & 權重整合（不變）

```json
{
  "phase": "4c",
  "agent": "Portfolio_Strategist",
  "debate_resolution": "string",
  "devils_advocate_accepted": ["sector1"],
  "devils_advocate_rejected": ["sector1"],
  "tail_risk_downgrades": ["sector — 因尾部風險被降一級的產業"],
  "final_regime_stance": "AGGRESSIVE | NEUTRAL | DEFENSIVE"
}
```

**仲裁規則（新增）**：
- `exposure_ceiling < 40%` → 至少 3 個產業標記 AVOID
- `cycle_phase = Late | Recession` → Defensive 產業加分，Cyclical 降分
- `upcoming_binary_risks` 含 within_48h → 相關產業降一級
- **新增**：`fragility_label = EXTREMELY FRAGILE` → 該產業強制降一個 verdict 等級（HOT → WARM）
- **新增**：`extreme_sentiment_triggered = true AND fragility_label = FRAGILE` → 加入 `risk_flags: extreme_sentiment_fragile_combo`

---

## PHASE 5 — SECTOR VERDICT

**Agent**: Portfolio Strategist (PS)

完成後執行：
1. 寫入 `./sector_logs/YYYY-MM-DD_sector_intel.json`（cache，供其他 protocol 讀取）
2. 將 FINAL VERDICT TABLE 存為 `../reports/YYYY-MM-DD_sector_report.md`

> ⚠️ **JSON Schema 必須嚴格遵守**：以下所有 key 名稱不可自行更換。bridge.py 依賴 `_phase0`、`_phase1`、`_phase3` 這三個子物件讀取資料。

```json
{
  "verdict_date": "YYYY-MM-DD",
  "protocol_version": "V1.1",
  "generated_at": "YYYY-MM-DD HH:MM",
  "market_regime": "from Phase 0",
  "exposure_ceiling": "from Phase 0",
  "cycle_phase": "from Phase 0",
  "_phase0": {
    "phase": 0,
    "agent": "Macro_Regime_Analyst",
    "scan_date": "YYYY-MM-DD",
    "breadth_source": "market-breadth-analyzer | uptrend-analyzer | web_search",
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
    "exposure_ceiling": "40-60%",
    "regime_confidence": "float 0.0–1.0"
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
    "composite_score": "float 0–100 (from market-sentiment-analyzer)",
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
      "risk_flags": ["binary_risk_within_48h", "late_cycle", "overbought", "fat_tail_warning", "extreme_sentiment"]
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
若 fragility_label = EXTREMELY FRAGILE → 強制降一個 verdict 等級（不調整分數，直接 downgrade label）
```

---

## FINAL VERDICT TABLE

```
| Sector      | Verdict | Score | Key Reasons (top 2)       | Tail Risk   | Proxy ETF | Risk Flags          |
|-------------|---------|-------|---------------------------|-------------|-----------|---------------------|
| Technology  | HOT     |  82   | AI capex cycle intact...  | RESILIENT   | XLK       |                     |
| Energy      | COLD    |  38   | Demand slowdown, tariff.. | FRAGILE     | XLE       | binary_48h, fat_tail|

Market Regime: RISK_ON | Exposure Ceiling: 70% | Cycle: Mid
Sentiment: Fear & Greed [XX/100 — Fear] | VIX: XX.X | Put/Call: X.XX

TOP THEMES TODAY: [theme1] [theme2]
HANDOFF TO INVESTMENT PROTOCOL: "市場 RISK_ON，科技與工業強，能源脆弱避開。"
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

*End of Pre-Market Sector Intelligence Protocol V1.1*
