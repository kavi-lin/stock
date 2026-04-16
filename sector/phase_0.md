# Phase 0 — Market Regime Check

**Agent**: Macro Regime Analyst

讀取 `./sector_logs/*_sector_intel.json` 最新檔（FRESH = mtime < 3 小時前 / 10800s）：
- FRESH → 載入，跳至 Phase 2（Phase 3 仍需重新執行；FTD/market_top 新鮮度補丁見 Global Rule 2）
- STALE 或缺失 → 執行以下分析並寫入 `./sector_logs/YYYY-MM-DD_sector_intel.json`

---

## 資料來源（優先順序）

### 層 A — market-breadth-analyzer（優先，量化）

1. 取 `./breadth_cache/market_breadth_*.json` 最新檔（FRESH = mtime < 10800s）
   - **FRESH** → 直接讀取，跳至「欄位映射」
   - **STALE 或缺失** → 執行腳本（約 5 秒）：
     ```bash
     python3 ~/.claude/skills/market-breadth-analyzer/scripts/market_breadth_analyzer.py \
       --output-dir ./breadth_cache/
     ```
     完成後讀取產出的新檔

> `uptrend_ratio_overall` 不在此處取得，由 Phase 1 完成後取各產業 `uptrend_ratio` 平均值回填。

### 層 B — Web Search（最後手段，有層 A 則跳過）

2. Web search: "US market breadth today", "S&P 500 advance decline today"

### 層 C — FTD Detector cache（量化底部確認）

3. 取 `./ftd_cache/ftd_detector_*.json` 最新檔（FRESH = mtime < 10800s）
   - **FRESH** → 直接讀取
   - **STALE 或缺失** → 執行腳本（約 10 秒）：
     ```bash
     python3 sector/ftd_yfinance.py --output-dir sector/ftd_cache/
     ```
   - 讀取欄位：`market_state.combined_state`、`quality_score.total_score`、`quality_score.exposure_range`

### 層 D — Market Top Detector cache（量化頂部偵測）

4. 取 `./market_top_cache/market_top_*.json` 最新檔（FRESH = mtime < 10800s）
   - **FRESH** → 直接讀取
   - **STALE 或缺失** → 執行腳本（約 10 秒）：
     ```bash
     python3 sector/market_top_yfinance.py --output-dir sector/market_top_cache/
     ```
   - 讀取欄位：`composite.composite_score`、`composite.zone`、`composite.risk_budget`

> **並行機會**：層 C + 層 D 兩個腳本完全獨立，可並行執行（節省 ~10 秒）

---

## 三訊號合成規則（Synthesized Exposure）

取三個來源的曝險上限，採用「最保守值」作為 `synthesized_exposure`：

| 來源 | 欄位 | 說明 |
|---|---|---|
| Breadth | `composite.exposure_guidance` | 廣度分析器輸出（如 "60-80%"） |
| FTD | `quality_score.exposure_range` | FTD 品質建議倉位（如 "40-65%"） |
| Market Top | `composite.risk_budget` | 頂部概率風險預算（如 "50-70%"） |

### 合成計算步驟

1. 解析字串 → 中位數（如 "40-65%" → 52.5）
2. 找三個中位數的最小值
3. 衝突檢查：max - min > 30pp → `signal_conflict = true`
4. `synthesized_exposure` = 對應最小中位數的**原始字串**

### 計算範例 1 — 三訊號一致看多

```
Breadth:     "70-85%" → midpoint 77.5
FTD:         "65-80%" → midpoint 72.5
Market Top:  "60-80%" → midpoint 70

min = 70, max = 77.5, diff = 7.5pp < 30pp
→ signal_conflict = false
→ synthesized_exposure = "60-80%"（Market Top 原始值）
→ 三訊號一致，可採納 FTD/Breadth 進取範圍
```

### 計算範例 2 — 訊號衝突

```
Breadth:     "70-90%" → midpoint 80
FTD:         "20-35%" → midpoint 27.5
Market Top:  "55-75%" → midpoint 65

min = 27.5, max = 80, diff = 52.5pp > 30pp
→ signal_conflict = true ⚠️
→ synthesized_exposure = "20-35%"（FTD 原始值）
→ Phase 4c 最終 regime_stance 改為 NEUTRAL 或 DEFENSIVE
```

### Agent 評估要點
- FTD 訊號 = 「底部確認」；若 Breadth 或 Market Top 同時轉弱 → FTD 積極訊號打折 50%
- Market Top > 60 且 FTD 未確認 → 取 Market Top 保守值
- 三訊號一致看多 → 採 FTD 進取範圍；三訊號衝突 → 強制降一等級，Phase 4c → NEUTRAL

---

## 欄位映射（market-breadth-analyzer → phase0 JSON）

| Phase0 欄位 | 來源路徑 | 說明 |
|---|---|---|
| `breadth_score` | `composite.composite_score` | 0–100 複合分數 |
| `breadth_components.overall_breadth` | `composite.composite_score` | |
| `breadth_components.sector_participation` | `composite.component_scores.breadth_level_trend.score` | |
| `breadth_components.momentum` | `composite.component_scores.ma_crossover.score` | |
| `breadth_components.mean_reversion_risk` | `100 - composite.component_scores.cycle_position.score` | |
| `exposure_ceiling` | `composite.exposure_guidance` | 廣度單一來源 |
| `cycle_phase` | 由 `components.cycle_position.signal` 推斷 | |
| `warning_flags` | 由各組件信號推斷 | |
| `regime_confidence` | data_quality: Complete=0.9, Partial=0.7, Limited=0.4 | |

### cycle_phase 推斷規則
- signal 含 "extreme_trough" 或 "TROUGH" → `"Early"`
- signal 含 "PEAK" 且含 "recovery" → `"Mid"`
- signal 含 "PEAK" 且不含 "recovery" → `"Late"`
- 其他 → `"Mid"`

### warning_flags 量化觸發規則
- `components.bearish_signal.signal_active = true` → `"Bearish_Signal_Active"`
- `components.ma_crossover.gap < 0` → `"Below_200MA"`
- `components.historical_percentile.percentile_rank < 30` → `"Low_Historical_Percentile"`
- `components.divergence.early_warning = true` → `"Early_Warning_Divergence"`
- `composite.zone = "Critical"` → `"Critical_Zone"`
- `composite.zone = "Weakening"` → `"Weakening_Zone"`

> **JSON Schema** → 見 `schema.md` Phase 0
