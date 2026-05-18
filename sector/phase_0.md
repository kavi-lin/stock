# Phase 0 — Market Regime Check

**Agent**: Macro Regime Analyst

讀取 `./sector_logs/*_sector_intel.json` 最新檔（FRESH = mtime < 3 小時前 / 10800s）：
- FRESH → 載入，跳至 Phase 2（Phase 3 仍需重新執行；FTD/market_top 新鮮度補丁見 Global Rule 2）
- STALE 或缺失 → 執行以下分析並寫入 `./sector_logs/YYYY-MM-DD_sector_intel.json`

---

## ⚡ V2.20.2 — Phase 0 Unified Reader（推薦，省 5-8 個 turn）

**一次跑取所有 5 層 cache** + 同時判斷新鮮度：

```bash
python3 sector/scripts/phase0_read_caches.py
```

stdout 輸出單一 JSON：
```
{
  "layers": {
    "breadth":    {available, age_hr, fresh, data: {composite, components, trend_summary, key_levels}},
    "ftd":        {available, age_hr, fresh, data: {market_state, ftd_timeline, quality_score}},
    "market_top": {available, age_hr, fresh, data: {composite, components}},
    "fred":       {available, age_hr, fresh, data: {regime_label, regime_confidence, macro_scores_composite, ...slim 11 fields}}
  },
  "stale_layers":   [...],
  "missing_layers": [...]
}
```

**用法**：一次 Bash → pipe 到 python -c 解析 → 一個 turn 拿到所有資料。**取代下方層 A-E 各自讀 cache 的舊流程**（每層 1 turn × LLM overhead ~3-5s → 5-8 個 turn 省掉）。

**Fallback**：`stale_layers` 或 `missing_layers` 非空 → 跑下方對應 layer script 重整 cache → 再跑一次 reader。

`fred_latest.json` 內部 1h cache（fresh_window 3600s）；其他層 fresh_window 10800s。

---

## 資料來源（優先順序）— 舊流程備援

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
   - 讀取欄位：`market_state.combined_state`、`quality_score.total_score`、`quality_score.exposure_range`、`ftd_timeline.*`
   - **⚠️ FTD 文字反幻覺規則（V1.5 — BUG-006）**：
     - 報告 FTD 狀態時，**必須引用 `ftd_timeline.ftd_status_text` 原文**（含 day-counter），不得自由命名「FTD Day N」。
     - `quality_score.breakdown.base` 的 `"Day 6 FTD: +60 (prime window)"` — 這個 `6` 是 **FTD 確認時的 rally-day**（永遠不變），**不是**「FTD 後過了幾天」。AI 若直接抄 `Day 6` 當作今天的 day-counter 即為幻覺。
     - 三個易混淆 day 的語意：`ftd_timeline.ftd_day_number`（fixed）vs `ftd_timeline.days_since_ftd`（每天 +1）vs `ftd_timeline.rally_day_count`（每天 +1）。

### 層 D — Market Top Detector cache（量化頂部偵測）

4. 取 `./market_top_cache/market_top_*.json` 最新檔（FRESH = mtime < 10800s）
   - **FRESH** → 直接讀取
   - **STALE 或缺失** → 執行腳本（約 10 秒）：
     ```bash
     python3 sector/market_top_yfinance.py --output-dir sector/market_top_cache/
     ```
   - 讀取欄位：`composite.composite_score`、`composite.zone`、`composite.risk_budget`

> 層 C + 層 D 腳本完全獨立 → 並行執行。

### 層 E — FRED Macro Snapshot（V1.4 新增，MUST-run）

5. 取 `skills/fred-macro/cache/fred_latest.json` 最新檔（FRESH = mtime < 3600s；fred-macro 自帶 1 hr cache）
   - **FRESH** → 直接讀取
   - **STALE 或缺失** → 執行：
     ```bash
     python3 skills/fred-macro/scripts/fetch.py --json-only
     ```
   - 失敗（無 API key / 網路錯誤）→ `fred_available = false`，`fred_snapshot = null`，protocol 繼續跑不中斷

6. **必讀**：`skills/fred-macro/SECTOR_ROTATION_GUIDE.md`（LLM instruction — 解釋 `favor` vs `adjustments` 兩層結構與衝突處理優先序）

7. 寫入 `_phase0.fred_snapshot` **slim shape**（僅這 11 個欄位，完整 snapshot 仍在 cache 檔）：
   ```
   generated_at / regime_label / regime_confidence / macro_scores_composite /
   yield_curve_value / yield_curve_inverted / credit_stress_elevated /
   financial_stress_above_avg / fed_rate_direction / real_rate_preferred /
   sector_rotation_favor[] / sector_rotation_avoid[] / velocity_highlights[]
   ```

> `velocity_highlights` 從 `change_velocity` 擷取 `velocity ∈ {accelerating, decelerating}` 的前 3 條 series，格式 `"SERIES_ID:velocity"`（e.g. `"NFCI:accelerating"`）。

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

### Agent 評估規則
- FTD = 底部確認；Breadth 或 Market Top 同時轉弱 → FTD 積極訊號打折 50%
- Market Top > 60 且 FTD 未確認 → 取 Market Top 保守值
- 三訊號衝突（diff > 30pp）→ 強制降一等級，Phase 4c final_regime_stance ≤ NEUTRAL

> 計算範例見 `README.md` §Phase 0 三訊號合成範例。

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
