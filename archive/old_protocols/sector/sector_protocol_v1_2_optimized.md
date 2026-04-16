# Pre-Market Sector Intelligence Protocol (V1.2 Optimized)

> **Changelog from V1.2 → V1.2 Optimized**
> - **P0 修正**：
>   - Phase 0：補充 `synthesized_exposure` 計算具體範例（2 個 case）
>   - Phase 0：新增「Skills Compatibility Matrix」確保版本管理
>   - Phase 4c：決策樹改寫，邏輯決策代替敘述規則
> - **P1 修正**：
>   - 全局：新增「Execution Timeline & Parallelization」小節
>   - Phase 3：新增「Extreme Sentiment Playbook」，區分 Extreme Greed vs Extreme Fear
>   - Phase 4b：Devil's Advocate `consensus_warning` 精確化，補充義務定義
> - **P2.7 修正**：
>   - SCORING RUBRIC：權重自適應規則，乘法調整

> **Changelog from V1.0 → V1.1**
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
   - **FTD/Market Top 新鮮度補丁**：即使走快取跳過 Phase 0-1，仍需檢查 `./ftd_cache/` 與 `./market_top_cache/` 是否有比 sector_intel.json 更新的檔案。若有 → 用新資料覆寫 `_phase0.ftd`、`_phase0.market_top`、`_phase0.synthesized_exposure` 後再繼續。
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
| Macro Regime Analyst | 總體市場健康度、制度判斷 | `market-breadth-analyzer` |
| Sector Rotation Analyst | 產業輪動、週期定位 | `sector-analyst` |
| Theme Intelligence Analyst | 跨產業主題熱度與生命週期 | `theme-detector` |
| News Catalyst Analyst | 48h 新聞、財報催化劑、**市場情緒儀表板** | `market-news-analyst`, `economic-calendar-fetcher`, **`market-sentiment-analyzer`** |
| Devil's Advocate | 挑戰多頭共識、提出反方論點、**量化尾部風險** | **`tail-risk-analyzer`** |
| Portfolio Strategist (PS) | 最終產業裁決、輸出報告 | — |

---

## Execution Timeline & Parallelization

> **新增小節 — P1 修正項 4**：執行時間預期與並行化機會

### Single-Thread Sequential Timeline

| Phase | Agent | Task | Estimated Time | Remarks |
|---|---|---|---|---|
| 0 | Macro Regime | Breadth script + FTD/MT cache | ~25 秒 | 3 個 script 依序執行 |
| 1 | Sector Rotation | CSV 讀取 + uptrend 回填 | ~5 秒 | I/O bound |
| 2 | Theme Intelligence | theme-detector skill/cache | 10–30 秒 | 視 FINVIZ Elite 或公開模式 |
| 3 | News Catalyst | market-sentiment, news, economic | ~20 秒 | 3 個查詢並行可 |
| 4a | Sector/Theme/News | 提案合成 | ~5 秒 | 純邏輯 |
| 4b | Devil's Advocate | tail-risk-analyzer per HOT sector | ~10–30 秒 | 若 >3 HOT 取前 3 |
| 4c | Portfolio Strategist | 仲裁 + 最終 verdict | ~10 秒 | 決策樹求值 |
| 5 | PS | JSON + MD 輸出 | ~5 秒 | I/O bound |
| | | **TOTAL** | **~110 秒** | — |

### Optimized Parallel Execution

```
Phase 0: ▓▓▓▓▓▓▓▓▓▓ (25s)
  ├─ Parallel: FTD script + Market Top script (10s + 10s → 10s)
  
Phase 1: ▓▓ (5s) [depends on Phase 0]

Phase 2-3 Parallel: ▓▓▓▓▓▓▓▓▓▓▓▓▓ (30s max, 並行執行)
  ├─ Phase 2: theme-detector
  ├─ Phase 3: market-sentiment-analyzer + market-news-analyst + economic-calendar

Phase 4a-b: ▓▓▓▓▓▓▓▓▓▓▓ (30s, depends on Phase 2-3)

Phase 4c-5: ▓▓▓ (15s, depends on Phase 4a-b)

OPTIMIZED TOTAL: ~75–85 秒 (vs 110秒 sequential)
```

**Parallelization Opportunities**:
- Phase 0：FTD + Market Top script 可並行（save ~10s）
- Phase 2 + Phase 3：完全獨立，應並行執行（save ~20s）
- Phase 4a：三個 agent 提案可並行，最後合成（save ~3s）

---

## PHASE 0 — MARKET REGIME CHECK

**Agent**: Macro Regime Analyst

讀取 `./sector_logs/YYYY-MM-DD_sector_intel.json`：
- 存在且日期符合 → 載入，跳至 Phase 2（Phase 3 仍需重新執行；FTD/market_top 新鮮度補丁見 Global Rule 2）
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

> **注意**：`uptrend_ratio_overall` 不在此處取得，由 Phase 1 完成後取各產業 `uptrend_ratio` 平均值回填至 `_phase0`。

### 層 B — Web search（最後手段，已有層 A 則跳過）
2. Web search: "US market breadth today", "S&P 500 advance decline today"

### 層 C — FTD Detector cache（量化底部確認）
3. 檢查 `./ftd_cache/ftd_detector_YYYY-MM-DD_*.json`（取最新）
   - **存在** → 直接讀取
   - **不存在** → 執行腳本（約 10 秒）：
     ```bash
     python3 sector/ftd_yfinance.py --output-dir sector/ftd_cache/
     ```
   - 讀取欄位：`market_state.combined_state`、`quality_score.total_score`、`quality_score.exposure_range`

### 層 D — Market Top Detector cache（量化頂部偵測）
4. 檢查 `./market_top_cache/market_top_YYYY-MM-DD_*.json`（取最新）
   - **存在** → 直接讀取
   - **不存在** → 執行腳本（約 10 秒）：
     ```bash
     python3 sector/market_top_yfinance.py --output-dir sector/market_top_cache/
     ```
   - 讀取欄位：`composite.composite_score`、`composite.zone`、`composite.risk_budget`

---

### 三訊號合成規則 & 計算範例（Synthesized Exposure）

> **新增小節 — P0 修正項 1**：具體計算範例

取三個來源各自給出的曝險上限，採用「最保守值」作為 `synthesized_exposure`：

| 來源 | 欄位 | 說明 |
|---|---|---|
| Breadth | `composite.exposure_guidance` | 廣度分析器直接輸出（如 "60-80%"） |
| FTD | `quality_score.exposure_range` | FTD 品質對應的建議倉位（如 "40-65%"） |
| Market Top | `composite.risk_budget` | 頂部概率對應的風險預算（如 "50-70%"） |

#### 合成計算步驟

1. **解析字串 → 中位數**：
   - "60-80%" → 70
   - "40-65%" → 52.5
   - "50-70%" → 60

2. **找最小中位數**：
   - min(70, 52.5, 60) = 52.5

3. **衝突檢查**：
   - max - min = 70 - 52.5 = 17.5 pp （< 30pp）→ signal_conflict = false
   - 若 >30pp → signal_conflict = true

4. **最終 synthesized_exposure**：
   - 對應最小中位數的原始字串 = "40-65%"（FTD 的值）

#### 計算範例 1 — 一致看多

```
Input:
  • Breadth exposure_guidance: "70-85%" → midpoint 77.5
  • FTD exposure_range: "65-80%" → midpoint 72.5
  • Market Top risk_budget: "60-80%" → midpoint 70

Processing:
  → Midpoint list: [77.5, 72.5, 70]
  → min = 70, max = 77.5
  → diff = 7.5 pp < 30pp → signal_conflict = false
  → 對應 min 值（Market Top）的原始字串

Output:
  synthesized_exposure: "60-80%"
  signal_conflict: false
  assessment: "三訊號一致，可採納 FTD/Breadth 進取範圍"
```

#### 計算範例 2 — 衝突

```
Input:
  • Breadth exposure_guidance: "70-90%" → midpoint 80
  • FTD exposure_range: "20-35%" → midpoint 27.5
  • Market Top risk_budget: "55-75%" → midpoint 65

Processing:
  → Midpoint list: [80, 27.5, 65]
  → min = 27.5, max = 80
  → diff = 52.5 pp > 30pp → signal_conflict = true ⚠️
  → 對應最小值（FTD）的原始字串

Output:
  synthesized_exposure: "20-35%"
  signal_conflict: true
  assessment: "FTD 未確認底部（市場仍風險大），廣度樂觀被 Market Top 打折，採取最保守策略"
  action: "Phase 4c 最終 regime_stance 改為 NEUTRAL 或 DEFENSIVE"
```

#### Agent 評估要點：
- **FTD 訊號代表「底部確認 → 可加倉」**；若 Breadth 或 Market Top 同時轉弱 → FTD 的積極訊號打折 50%
- **Market Top 高分（>60）且 FTD 未確認** → 倉位上限取 Market Top 保守值
- **三訊號一致看多** → 可採納 FTD 進取範圍；**三訊號衝突** → 強制降一個等級，Phase 4c 改為 NEUTRAL

---

### 欄位映射（market-breadth-analyzer → phase0 JSON）

| Phase0 欄位 | 來源路徑 | 說明 |
|---|---|---|
| `breadth_score` | `composite.composite_score` | 0–100 複合分數 |
| `breadth_components.overall_breadth` | `composite.composite_score` | 同複合分數 |
| `breadth_components.sector_participation` | `composite.component_scores.breadth_level_trend.score` | 廣度水位 |
| `breadth_components.momentum` | `composite.component_scores.ma_crossover.score` | 8MA vs 200MA 動能 |
| `breadth_components.mean_reversion_risk` | `100 - composite.component_scores.cycle_position.score` | 週期位置反轉 → 風險 |
| `exposure_ceiling` | `composite.exposure_guidance` | 如 "40-60%"（廣度單一來源） |
| `uptrend_ratio_overall` | Phase 1 完成後各產業 `uptrend_ratio` 平均值 | 回填，非 Phase 0 計算 |
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
  "breadth_source": "market-breadth-analyzer | web_search",
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
  "uptrend_ratio_overall": "float 0.0–1.0 (由 Phase 1 回填)",
  "warning_flags": ["Bearish_Signal_Active", "Below_200MA", "Low_Historical_Percentile"],
  "exposure_ceiling": "40-60% (breadth only)",
  "regime_confidence": "0.0–1.0",
  "ftd": {
    "state": "FTD_CONFIRMED | FTD_WINDOW | RALLY_ATTEMPT | CORRECTION | FTD_INVALIDATED | NO_SIGNAL",
    "quality_score": "0–100",
    "exposure_range": "0-20% | 20-40% | 40-65% | 65-100%",
    "source": "ftd_cache | not_available"
  },
  "market_top": {
    "composite_score": "0–100",
    "zone": "Normal | Early_Warning | Elevated_Risk | High_Probability | Top_Formation",
    "risk_budget": "string 如 80-100%",
    "source": "market_top_cache | not_available"
  },
  "synthesized_exposure": "string — 最保守曝險上限（取三訊號中最低者）",
  "signal_conflict": "true | false — 若任兩訊號中位差 > 30pp"
}
```

---

## PHASE 1 — SECTOR ROTATION SCAN

**Agent**: Sector Rotation Analyst

**資料來源**: `sector-analyst` CSV（不需 API key）

> Phase 1 完成後，將各產業 `uptrend_ratio` 的平均值回填至 `_phase0.uptrend_ratio_overall`。

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

## PHASE 3 — NEWS CATALYST REVIEW

**Agent**: News Catalyst Analyst

**資料來源**:
- `market-news-analyst`（WebSearch，10 天內）
- `economic-calendar-fetcher`（未來 7 天）
- **`market-sentiment-analyzer` skill（取代 web search 的 F&G 查詢）**

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

---

### Extreme Sentiment Playbook（新增 P1 修正項 5）

> **當 `extreme_sentiment_triggered = true` 時的級聯效應和應對策略**

#### Case 1: Extreme Greed (composite_score > 80)

```
Trigger Condition:
  CNN Fear & Greed Index > 80
  OR VIX < 15 + Put/Call Ratio < 0.6 + SPY RSI > 70
  
Cascading Actions:
  1. 所有 HOT 產業 (composite_score > 75)：
     → risk_flags += "extreme_greed_warning"
  
  2. Phase 4c 決策樹強制檢查：
     IF (final_verdict=HOT AND extreme_greed=true):
       → sentiment_score_multiplier *= 0.85（降分）
       → downgrade HOT→WARM if composite_score < 80
  
  3. Devil's Advocate 義務：
     → 必須對至少 2 個 HOT 板塊提出「獲利了結/泡沫破裂」反方論點
     → tail_risk_analyzer 檢查優先級上升（前 5 個 HOT 都要跑）
  
  4. final_regime_stance：
     → 不得為 AGGRESSIVE，改為 NEUTRAL
  
  5. 報告警告：
     → HANDOFF 必須明確提及「極度樂觀環境，謹慎進場」
  
Example Output:
  {
    "extreme_sentiment_triggered": true,
    "greed_or_fear": "Extreme_Greed",
    "risk_flags": ["greed_peaked_warning"],
    "regime_stance": "NEUTRAL",
    "devils_advocate_strength": "REQUIRED_ACTIVATION"
  }
```

#### Case 2: Extreme Fear (composite_score < 20)

```
Trigger Condition:
  CNN Fear & Greed Index < 20
  OR VIX > 30 + Put/Call Ratio > 1.2 + SPY RSI < 30
  
Cascading Actions:
  1. 所有 COLD/AVOID 產業（composite_score < 50）：
     → 評估升級機會：
       IF (COLD AND uptrend_ratio > 0.5 AND tail_risk < 40):
         → 標記 "fear_capitulation_opportunity"
  
  2. Phase 4c 決策樹強制檢查：
     IF (verdict=COLD AND extreme_fear=true AND sector.cyclical=true):
       → sentiment_score_multiplier *= 1.10（升分）
       → upgrade COLD→WARM 若基本面面未變
  
  3. Devil's Advocate 軟化：
     → 不必對 COLD 產業強制挑戰
     → 改為尋找「恐慌被過度反應」的板塊機會
  
  4. final_regime_stance：
     → 可升級為 AGGRESSIVE（若 FTD 確認 + 三訊號合成 > 50%）
  
  5. 報告警告：
     → HANDOFF 提及「極度恐慌環境，高風險但機會浮現」
  
Example Output:
  {
    "extreme_sentiment_triggered": true,
    "greed_or_fear": "Extreme_Fear",
    "capitulation_candidates": ["Healthcare", "Real_Estate"],
    "regime_stance": "AGGRESSIVE_IF_FTD_CONFIRMED",
    "devils_advocate_strength": "REDUCED (opportunity_hunt_mode)"
  }
```

---

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
    "fear_greed_index": "0–100 (from market-sentiment-analyzer composite_score)",
    "fear_greed_label": "Extreme_Fear | Fear | Neutral | Greed | Extreme_Greed",
    "vix_current": "float (from market-sentiment-analyzer)",
    "put_call_ratio": "float (from market-sentiment-analyzer)",
    "spy_rsi": "float (from market-sentiment-analyzer)",
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

**Phase 3 執行清單**:
- `market-sentiment-analyzer` skill（取代 "Web search: CNN Fear Greed Index today"）
- `market-news-analyst` 標準查詢（10 天內市場新聞）
- `economic-calendar-fetcher` 或 web search: "upcoming FOMC CPI NFP dates"
- Web search: "Trump tariff statement today" / "Trump Truth Social market"
- Web search: "sector named threat Trump today"（若有政治事件）

---

## PHASE 4 — MULTI-AGENT DEBATE

**Agent**: Portfolio Strategist (PS) 主持，各 agent 輪流發言

### Step 1 — 各 Agent 提案

```json
{
  "phase": "4a",
  "agent": "Sector_Rotation_Analyst | Theme_Intelligence_Analyst | News_Catalyst_Analyst",
  "top_conviction_hot": ["sector1", "sector2"],
  "top_conviction_cold": ["sector1", "sector2"],
  "key_rationale": "string — 最多 2 句"
}
```

### Step 2 — Devil's Advocate（加入量化尾部風險 & 精確化 Consensus Warning）

> **新增細節 — P1 修正項 6**：精確定義 consensus_warning 觸發和要求

**consensus_warning 觸發條件精確定義**：

```
consensus_warning = true IF (sector 達成以下全部條件):
  ✓ Phase 1: rotation_signal = INFLOW
  ✓ Phase 2: lifecycle_stage ∈ [Accelerating, Trending]
  ✓ Phase 3: sector_news_sentiment = bullish
  
  表示：產業輪動、主題熱度、新聞催化都看多，無任何分歧
  
Devil's Advocate 的義務與責任：
  IF consensus_warning = true:
    MUST 提交 challenge_targets，且：
    • counter_evidence 長度 ≥ 2 句（必須實質論點，非敷衍）
    • 引用具體數據或邏輯（評估欄位、歷史對比等）
    • 若無實質反方論點 → 標記 "FORCED_CHALLENGE_WEAK"（低信度）
    
  IF consensus_warning = false:
    CAN 選擇性挑戰個別 HOT 產業
    （優先挑戰 tail_risk_score 最高的 2-3 個）
```

**Tail Risk 觸發規則**

在 Devil's Advocate 準備反方論點前，對 HOT 產業執行尾部風險檢查：

> **效率上限**：若 HOT 產業 > 3 個，僅對 `composite_score` 前 3 名執行 `tail-risk-analyzer`，其餘標記 `tail_risk_source: SKIPPED_CAPACITY_LIMIT`。

```
對每個納入檢查的 HOT 產業（composite_score > 75）的 proxy_etf：
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
      "tail_risk_source": "SKILL_EXECUTED | SKIPPED_LOW_SCORE | SKIPPED_CAPACITY_LIMIT"
    }
  ],
  "challenge_targets": [
    {
      "challenged_sector": "string",
      "challenged_call": "HOT | COLD",
      "counter_evidence": "string (≥ 2 句，含具體數據)",
      "tail_risk_evidence": "string — 來自 tail-risk-analyzer 的量化支撐（若有）",
      "risk_scenario": "string",
      "confidence_level": "HIGH | MEDIUM | LOW"
    }
  ],
  "consensus_warning": "true | false — 所有 agent 都看多同一板塊時必須為 true"
}
```

### Step 3 — PS 仲裁 & 決策樹（新增 P0 修正項 2）

> **改寫為決策樹格式 — 邏輯決策代替敘述規則**

```
PORTFOLIO STRATEGIST ARBITRATION DECISION TREE
═════════════════════════════════════════════════

IF signal_conflict = true:
  → final_regime_stance CANNOT be AGGRESSIVE
  → min(final_regime_stance) = NEUTRAL
  → explanation: "三訊號衝突，風險無法量化"

IF synthesized_exposure < 40%:
  → MUST flag ≥3 hot sectors as AVOID (no exception)
  → explanation: "倉位上限被三訊號合成壓低，必須防守"

IF cycle_phase ∈ [Late, Recession]:
  FOR EACH sector:
    IF sector.cyclical = true:
      → composite_score *= 0.85
    IF sector.defensive = true:
      → composite_score *= 1.10

FOR EACH hot_sector (composite_score > 75):
  IF tail_risk_label = EXTREMELY_FRAGILE:
    → verdict DOWNGRADE: HOT → WARM (no scoring change, direct downgrade)
    → risk_flags += "fragility_downgrade"
    → explanation: "尾部脆弱度過高，降級規避系統風險"
  
  ELSE IF (tail_risk_label = FRAGILE AND extreme_sentiment_triggered = true):
    → verdict DOWNGRADE: HOT → WARM
    → risk_flags += "extreme_sentiment_fragile_combo"
    → explanation: "脆弱而極端樂觀/恐慌，降級風險"

FOR EACH upcoming_binary_risk (timing = within_48h):
  FOR EACH affected_sector:
    → composite_score *= 0.70
    → risk_flags += "binary_risk_within_48h"
    → explanation: "48 小時內有重大風險事件"

IF consensus_warning = true AND devils_advocate_accepted = []:
  → warning: "所有訊號一致看多，Devil's Advocate 無實質反方論點"
  → regime_confidence *= 0.85
  → explanation: "監管風險：群體共識無自我檢驗"

FINAL VERDICT ASSIGNMENT:
  FOR EACH sector:
    score = adjusted composite_score (after all multipliers)
    
    IF score >= 75:
      verdict = HOT (unless EXTREMELY_FRAGILE downgrade)
    ELSE IF 50 <= score < 75:
      verdict = WARM (unless downgraded by conditions above)
    ELSE IF 25 <= score < 50:
      verdict = COLD
    ELSE (score < 25):
      verdict = AVOID
    
    VALIDATE:
      IF signal_conflict=true AND verdict=HOT:
        → downgrade to WARM (safe guard)

final_regime_stance = aggregate([verdict...]):
  HOT count >= 3 AND AVOID count = 0 AND synthesized_exposure >= 60%:
    → AGGRESSIVE
  HOT count >= 1 AND median(verdict) >= WARM:
    → NEUTRAL
  COLD count >= 3 OR synthesized_exposure < 40%:
    → DEFENSIVE
```

```json
{
  "phase": "4c",
  "agent": "Portfolio_Strategist",
  "debate_resolution": "string",
  "devils_advocate_accepted": ["sector1"],
  "devils_advocate_rejected": ["sector1"],
  "tail_risk_downgrades": ["sector — 因尾部風險被降一級的產業"],
  "decision_tree_path": "string — 簡要記錄走過哪些決策樹分支",
  "final_regime_stance": "AGGRESSIVE | NEUTRAL | DEFENSIVE",
  "regime_confidence": "float 0.0–1.0 (adjusted after debate)",
  "regime_confidence_rationale": "string — 為何這個信度分"
}
```

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
  "protocol_version": "V1.2_Optimized",
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
    "exposure_ceiling": "40-60% (breadth only)",
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
    "synthesized_exposure": "string — 最保守曝險上限",
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

## SCORING RUBRIC & WEIGHT ADAPTATION

> **修正 P2.7**：權重自適應規則

| Composite Score | Verdict | 行動建議 |
|---|---|---|
| 75–100 | HOT | 積極尋找個股進場機會 |
| 50–74 | WARM | 選股謹慎，等待更好時機 |
| 25–49 | COLD | 減少暴露，避免新建倉 |
| 0–24 | AVOID | 清倉或嚴格停損 |

### Base Sector Composite Score 計算

```
Score_base = breadth_momentum(25) + theme_heat(25) + news_catalyst(25) + rotation_signal(25)
```

### 自適應權重調整規則

> **新增 — P2 修正項 7**：權重乘法調整，根據市場環境動態優化

```
Step 1. 識別環境類型：
  market_regime ∈ {BULL, BEAR, SIDEWAYS, VOLATILE, RISK_OFF, RISK_ON}
  cycle_phase ∈ {Early, Mid, Late, Recession}
  breadth_score: 0–100

Step 2. 套用乘法權重調整（以下乘以 base components）：

┌─ IF cycle_phase = Early:
│  breadth_momentum *= 1.2    (上升趨勢初期，廣度可靠)
│  rotation_signal *= 1.0     (保持)
│  theme_heat *= 1.0
│  news_catalyst *= 0.9       (前期題材不穩)
│
├─ IF cycle_phase = Mid:
│  breadth_momentum *= 1.0    (中期均衡)
│  rotation_signal *= 1.1     (輪動加速)
│  theme_heat *= 1.1          (主題趨勢清晰)
│  news_catalyst *= 1.0
│
├─ IF cycle_phase = Late:
│  breadth_momentum *= 0.8    (廣度開始衰退的訊號)
│  rotation_signal *= 0.9     (輪動減速)
│  theme_heat *= 0.85         (主題走向疲乏)
│  news_catalyst *= 1.2       (震盪加大，新聞催化變重要)
│
└─ IF cycle_phase = Recession:
   breadth_momentum *= 0.5    (暴跌，廣度無參考)
   rotation_signal *= 0.6     (防守無輪動)
   theme_heat *= 0.7          (主題失效)
   news_catalyst *= 1.4       (政經風險主導)

┌─ IF market_regime = VOLATILE (VIX > 25):
│  breadth_momentum *= 1.3    (波動時廣度判讀最可靠)
│  rotation_signal *= 0.8     (輪動被壓制)
│  theme_heat *= 0.8
│  news_catalyst *= 1.2       (新聞驅動價格)
│
├─ IF market_regime = RISK_OFF:
│  breadth_momentum *= 1.2    (風險厭惡時看廣度對錯)
│  rotation_signal *= 1.2     (防守輪動明顯)
│  theme_heat *= 0.7          (成長主題減分)
│  news_catalyst *= 1.3       (脈衝新聞驅動)
│
└─ IF market_regime = RISK_ON:
   breadth_momentum *= 1.0
   rotation_signal *= 1.0
   theme_heat *= 1.2          (成長主題加分)
   news_catalyst *= 0.95      (相對背景雜訊)

┌─ IF breadth_score > 80 (Strong):
│  breadth_momentum *= 1.15
│
├─ IF breadth_score 30–50 (Weakening):
│  breadth_momentum *= 0.85
│
└─ IF breadth_score < 30 (Critical):
   breadth_momentum *= 0.5

┌─ IF extreme_sentiment_triggered = true AND greed_or_fear = Extreme_Greed:
│  (all score components) *= 0.85
│  explanation: "泡沫頂部機率上升，全面降分"
│
└─ IF extreme_sentiment_triggered = true AND greed_or_fear = Extreme_Fear:
   (all score components) *= 1.05
   explanation: "恐慌過度反應，逆向提價值板塊"

Step 3. 加總調整後的分數：
  Score_adjusted = breadth_momentum' + theme_heat' + news_catalyst' + rotation_signal'
  
  Cap: 若 Score_adjusted > 100 → 設為 100
      若 Score_adjusted < 0 → 設為 0

Step 4. 查詢 verdict：
  使用調整排名，對應上面的 Composite Score 區間
```

### 權重自適應範例

```
Example 1 — Early Cycle Bull Market (VIX < 15)

Base:
  breadth_momentum: 23
  theme_heat: 22
  news_catalyst: 20
  rotation_signal: 19
  Score_base = 84 (HOT)

Adjustments:
  cycle_phase = Early:
    breadth *= 1.2 → 27.6
    theme_heat *= 1.0 → 22
    news_catalyst *= 0.9 → 18
    rotation_signal *= 1.0 → 19
  
  market_regime = RISK_ON:
    theme_heat *= 1.2 → 26.4 (override)
    news_catalyst *= 0.95 → 17.1 (override)
  
  breadth_score = 85 (Strong):
    breadth *= 1.15 → 31.74 (override)

Score_adjusted = 31.74 + 26.4 + 17.1 + 19 = 94.24 (still HOT, but higher confidence)

→ PS 信度提升：這是最淨的上升趨勢，增加進攻性
```

```
Example 2 — Late Cycle Overheated Market (Breadth failing, VIX < 12)

Base:
  breadth_momentum: 25
  theme_heat: 24
  news_catalyst: 21
  rotation_signal: 22
  Score_base = 92 (HOT)

Adjustments:
  cycle_phase = Late:
    breadth *= 0.8 → 20
    theme_heat *= 0.85 → 20.4
    news_catalyst *= 1.2 → 25.2
    rotation_signal *= 0.9 → 19.8
  
  extreme_sentiment_triggered = true (composite_score = 85):
    (all) *= 0.85:
      breadth: 20 * 0.85 = 17
      theme_heat: 20.4 * 0.85 = 17.34
      news_catalyst: 25.2 * 0.85 = 21.42
      rotation_signal: 19.8 * 0.85 = 16.83

Score_adjusted = 17 + 17.34 + 21.42 + 16.83 = 72.59 (WARM, not HOT!)

→ PS 防守性：儘管數字高，but Late Cycle + Extreme Greed 自動降級
→ 須將進攻改為選股謹慎
```

---

## SKILLS COMPATIBILITY MATRIX

> **新增小節 — P0 修正項 3**：版本管理和依賴清單

| Skill | Min Ver | Key Output Fields | Fallback Strategy | Data Freshness Requirement |
|---|---|---|---|---|
| `market-breadth-analyzer` | v1.3+ | `composite.composite_score`, `exposure_guidance`, `component_scores.*` | Web search ("US market breadth today") | 當日或前一交易日 |
| `sector-analyst` | v1.0+ | `sectors[].uptrend_ratio`, `sectors[].rotation_signal` | CSV manual parse 或前一日 cache | 當日 |
| `ftd_yfinance.py` | v1.0+ | `market_state.combined_state`, `quality_score.total_score`, `exposure_range` | 前 7 日 cache（若全 script fail） | 當日或前一交易日 |
| `market_top_yfinance.py` | v1.0+ | `composite.composite_score`, `composite.zone`, `risk_budget` | 前 7 日 cache | 當日或前一交易日 |
| `theme-detector` | v2.0+ | `themes[].name`, `heat_score`, `lifecycle_stage`, `proxy_etfs` | 前 1 日 cache | 當日（新聞驅動更新） |
| `market-news-analyst` | v1.0+ | News event list, impact scoring | Web search 自主查詢 | 當日（<12h） |
| `economic-calendar-fetcher` | v1.0+ | Scheduled events, dates, impact | FMP API 或公開日程表 | 當日 |
| `market-sentiment-analyzer` | v1.2+ | `composite_score`, `vix.current`, `put_call_ratio`, `spy_momentum.rsi_14` | Web search: VIX + CNN F&G + options data | 當日（<1h） |
| `tail-risk-analyzer` | v1.1+ | `fragility_label`, `tail_risk_score`, `excess_kurtosis` | Skip tail risk check（標記 SKIPPED_UNAVAILABLE） | 當日 |

### Backward Compatibility 規則

```
若 Skill 版本低於 Min Ver：
  1. LOG warning: "Skill version mismatch: expected >= XVER, got YVer"
  2. 檢查欄位是否齊全：
     - 主要欄位缺失 → FALLBACK
     - 次要欄位缺失 → 補 "N/A" 或預設值
  3. resume execution 或 ABORT（取決於是否 critical path）

Critical Path Skills（必須可用）:
  - market-breadth-analyzer
  - market-sentiment-analyzer
  若失敗 → abort Phase，報告錯誤

Optional Skills（失敗可 fallback）:
  - theme-detector（前 1 日 cache）
  - tail-risk-analyzer（skip tail risk check）
```

---

## FINAL VERDICT TABLE

```
| Sector      | Verdict | Score | Key Reasons (top 2)       | Tail Risk   | Proxy ETF | Risk Flags          |
|-------------|---------|-------|---------------------------|-------------|-----------|---------------------|
| Technology  | HOT     |  82   | AI capex cycle intact...  | RESILIENT   | XLK       |                     |
| Energy      | COLD    |  38   | Demand slowdown, tariff.. | FRAGILE     | XLE       | binary_48h, fat_tail|

Market Regime: RISK_ON | Breadth Ceiling: 70% | Synthesized Ceiling: 55% ⚠️ | Cycle: Mid
Sentiment: Fear & Greed [XX/100 — Fear] | VIX: XX.X | Put/Call: X.XX | Signal Conflict: No

TOP THEMES TODAY: [theme1] [theme2]
HANDOFF TO INVESTMENT PROTOCOL: "市場 RISK_ON，科技與工業強，能源脆弱避開。"
```

> ⚠️ 當 `signal_conflict = true` 時，Synthesized Ceiling 後方顯示警告符號，並在 HANDOFF 中明確說明衝突訊號。

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

*End of Pre-Market Sector Intelligence Protocol V1.2 Optimized*
