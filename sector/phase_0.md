# Phase 0 — Market Regime Check

**Agent**: Macro Regime Analyst

讀取 `./sector_logs/*_sector_intel.json` 最新檔（FRESH = 內部 `generated_at` < 3 小時前 / 10800s，不看 `mtime`，詳見主文件全局規則 2）：
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

**用法**：一次 Bash → pipe 到 python -c 解析 → 一個 turn 拿到所有資料。**取代層 A-E 各自讀 cache 的舊流程**（每層 1 turn × LLM overhead ~3-5s → 5-8 個 turn 省掉；舊流程全文見 `protocol_appendix_fallback.md` §1）。

**Fallback**：`stale_layers` 或 `missing_layers` 非空 → 跑 `protocol_appendix_fallback.md` §1 對應 layer 的重整指令 → 再跑一次 reader。**注意 reader 只要有一層可用就 rc=0**，所以「有 stale/missing 層」是常見狀況而非 reader 失敗 —— 這種情況也要開 appendix §1 取重整指令。

`fred_latest.json` 內部 1h cache（fresh_window 3600s）；其他層 fresh_window 10800s。

---

## 每場都適用的紀律（不是備援）

### ⚠️ FTD 文字反幻覺規則（V1.5 — BUG-006）

- 報告 FTD 狀態時，**必須引用 `ftd_timeline.ftd_status_text` 原文**（含 day-counter），不得自由命名「FTD Day N」。
- `quality_score.breakdown.base` 的 `"Day 6 FTD: +60 (prime window)"` — 這個 `6` 是 **FTD 確認時的 rally-day**（永遠不變），**不是**「FTD 後過了幾天」。AI 若直接抄 `Day 6` 當作今天的 day-counter 即為幻覺。
- 三個易混淆 day 的語意：`ftd_timeline.ftd_day_number`（fixed）vs `ftd_timeline.days_since_ftd`（每天 +1）vs `ftd_timeline.rally_day_count`（每天 +1）。

### FRED（層 E）— MUST-run

- 失敗（無 API key / 網路錯誤）→ `fred_available = false`，`fred_snapshot = null`，protocol 繼續跑不中斷
- **必讀**：`skills/fred-macro/SECTOR_ROTATION_GUIDE.md`（LLM instruction — 解釋 `favor` vs `adjustments` 兩層結構與衝突處理優先序）
- 寫入 `_phase0.fred_snapshot` **slim shape**（僅這 11 個欄位，完整 snapshot 仍在 cache 檔）：
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

## cycle_phase 推斷規則（**LLM 仍在用** — 由 decision JSON authored）

由 `components.cycle_position.signal` 推斷：
- signal 含 "extreme_trough" 或 "TROUGH" → `"Early"`
- signal 含 "PEAK" 且含 "recovery" → `"Mid"`
- signal 含 "PEAK" 且不含 "recovery" → `"Late"`
- 其他 → `"Mid"`

## exposure_ceiling（**LLM 仍要寫** — 由 decision JSON authored）

- 值一律取自**廣度的單一來源** `composite.exposure_guidance`（e.g. `"40-60%"`），不要另行推估、不要與 `synthesized_exposure` 混用。
- `build_sector_intel.py` 用 `require(decision, "exposure_ceiling")` **硬取**這個 key：decision JSON 缺它 → build 直接中止（不是填預設值）。同時它也是 `validate_sector_intel.py` 檢查的頂層必填欄位。

> 其餘 phase0 欄位（`breadth_score` / `breadth_components` / `warning_flags` /
> `regime_confidence`）**由 `build_sector_intel.py` 的 `build_phase0()` 自動填**，
> 不需手填也不要手抄。舊版手動映射表的三處**過期列**（`breadth_components`、
> `regime_confidence`、`warning_flags`）連同它們與現行實作的差異記在
> `protocol_appendix_fallback.md` §2（僅供理解沿革，**判斷一律以 script 為準**）；
> 該表其餘各列已由上面的規則取代。

> **JSON Schema** → 見 `schema.md` Phase 0
> **備援流程**（reader 失敗，或 `stale_layers`/`missing_layers` 非空要重整）→ `protocol_appendix_fallback.md` §1
