# AI 投資委員會 — 產業掃描協定 (Sector Protocol) 深度審查、優化建議與實作計劃報告

本報告針對目前的 **Pre-Market Sector Intelligence Protocol (V1.4)** 進行了深度架構審查、代碼流追蹤與實例驗證，並整合了具體的實作計劃（Implementation Plan）。

本報告包含：
1. 協定核心規則與關鍵 Bug 修正（已落實）
2. 全 11 GICS 板塊對齊 Audit 驗證結果
3. 系統性優化方案（細節修正版）與優先序決策矩陣
4. 具體實作計劃與程式碼變更指引（五大 Implementation Guardrails）
5. 驗證與測試方案

---

## 🟢 關鍵 Bug 修正與全 11 GICS 板塊 Audit 驗證

### 1. 發現與修復 Financials 板塊 n/a Bug
在運行 `python3 sector/scripts/sector_digest.py` 輸出摘要表時，原先 **`Financials`** 板塊的 **`Uptr` (Uptrend Ratio)** 與 **`Heat` (主題熱度)** 欄位因名稱對齊失同步，顯示為 `n/a`。
* **原因**：`sector_digest.py` 的 `UPTREND_NAME_MAP` 將 `"Financials"` 映射到了 `"Financial Services"`，而 `theme-detector` 最新快取實體中，對應的鍵名為 `"Financial"`。
* **修復**：已將 [sector_digest.py](file:///Users/kavi/Documents/Claude/Projects/AI%E6%8A%95%E8%B3%87%E5%A7%94%E5%93%A1%E6%9C%83/sector/scripts/sector_digest.py#L51) 的映射修正為 `"Financials": "Financial"`。經重新執行已完美恢復正常數值。

### 2. 全 11 GICS 板塊完整性 Audit
為避免同類型 Bug 隱性存在於其他板塊，我們對全部 11 個 GICS 板塊在 `theme-detector` 快取與本系統中的對齊狀態進行了完整 Audit 檢索。
**驗證結果如下**：
* 11 個板塊全部綠燈對齊，`theme_detector` 無孤兒 key，**Financials 是唯一的斷裂點且已被成功修復**。

| Canonical Key | → Theme-Detector Key | Audit 狀態 |
|---|---|---|
| Technology | Technology | ✅ OK |
| Healthcare | Healthcare | ✅ OK |
| Energy | Energy | ✅ OK |
| **Financials** | **Financial** | ✅ **OK (已修復)** |
| Industrials | Industrials | ✅ OK |
| Materials | Basic Materials | ✅ OK |
| Communication | Communication Services | ✅ OK |
| Consumer_Discretionary | Consumer Cyclical | ✅ OK |
| Consumer_Staples | Consumer Defensive | ✅ OK |
| Utilities | Utilities | ✅ OK |
| Real_Estate | Real Estate | ✅ OK |

---

## 💡 系統性優化方案 (細節修正版)

依據系統算術正確性優先、防止靜默失效及漸進遷移原則，我們重新整理了四大優化建議與實作細節：

### 建議一：建立 explicit 顯式 Alias 字典與未知報錯 (而非靜默模糊匹配)
> [!IMPORTANT]
> **設計漏洞防範**：
> 移除空格、底線、轉小寫及去 "services" 等「模糊匹配 (fuzzy matching)」方式在實務上會產生重大 bug（例如：會將 "Consumer Services" 誤合為 "Consumer"，或通配 "Communications" 與 "Communication Services" 兩個合法板塊）。模糊比對會吞掉新型態的 alias 命名，導致靜默失敗。

* **正解方案**：
  維護一個顯式的 **`SECTOR_ALIASES` 字典**，對於未知的板塊名稱，**必須主動 log/raise 報錯**，確保新板塊或 API 命名異動能第一時間被工程人員發現。
  並且，`SECTOR_ALIASES` 的映射目標**必須嚴格使用專案的 Canonical Keys**，如 `Consumer_Discretionary`（帶底線且去 services 的 repo canonical 格式），決不能映射回 "Consumer Discretionary" 等 GICS 顯示 prose 名稱，以防 builder 快取查無此項或 validator 發生 drift。

---

### 建議二：Deterministic `sector_score_calculator` 計算器 (最大槓桿，極力推薦)
> [!TIP]
> **實作核心**：
> 目前協定的 `Scoring Rubric` 包含多步複雜的乘數與 Penalty 疊加（Step 1 至 Step 5b），LLM 心算極易產生隨機算術漂移。將其代碼化是保證決策模型一致性的最優解。

為防止過渡期架構衝突，實作必須遵循以下 4 點規範：
1. **FRED 互斥邏輯**：當 `fred_available = true` 時，必須**自動 SKIP Step 1 (Cycle Phase)**，直接由 Step 6 FRED Regime Overlay 取代，絕對不能重疊運行以防重複扣分。
2. **Explicit 快取路徑管理**：計算器必須使用絕對/顯式路徑指定快取來源，嚴防因路徑漂移而默默讀取到舊快取：
   - **FRED**: `skills/fred-macro/cache/fred_latest.json`
   - **Breadth**: `sector/breadth_cache/market_breadth_history.json`
   - **Theme**: 最新 `skills/theme-detector/cache/theme_detector_*.json`
   - **FTD**: `sector/ftd_cache/` 最新 JSON
   - **Market Top**: `sector/market_top_cache/` 最新 JSON
3. **Dual-Run 漸進式遷移驗證**：不可直接 cutover。新計算器完成後，需進行 **N 次 Sessions 的雙軌運行 (LLM 心算 vs 程式計算)**，將產出的 decision JSON 進行 diff 比對，確保沒有非預期的行為偏差，以防破壞 `backtest_postmortem` 的歷史連續性。
4. **定位澄清**：此優化的真正最大收益是 **算術正確性與邏輯一致性**，Token 省費與 Wall Time 縮短均屬附屬收益。

---

### 建議三：FTD 反幻覺 — 提示注入與 Verbatim 精確比對
> [!WARNING]
> **設計漏洞防範**：
> 在 `validate_sector_intel.py` 中使用 `\bDay X FTD\b` 這類寬泛的 regex 檢索容易誤判（例如歷史描述中合法的 "Previous Day 6 FTD in March" 會中招）。

* **優化方案**：
  1. **Prompt 注入 (Step 3a)**：在 `phase0_read_caches.py` 中輸出 `ftd_status_text` 提示，約束 LLM 發言，此方法成本極低且效益顯著。
  2. **Verbatim 精確比對 (Step 3b)**：在 `validate_sector_intel.py` 中，直接將 LLM 回填的 `ftd_status_text` 與腳本輸出的期望值進行**字串精確比對 (Verbatim Assert)**，而非 regex 搜索。只要字串不匹配即視為重寫/幻覺，簡潔且 100% 精準。

---

### 建議四：改善 Parallel Subagent 超時降級的預警與健康度自檢
* **4a. Pre-flight 1-Sec 快取自檢 (高優先)**：在 protocol 執行最前端，用 1秒時間預檢 FMP 剩餘額度、FRED 密鑰狀態與 Breadth CSV 解析完備性。這能大幅降低運行 5 分鐘後才在 Phase 4a 觸發 degraded partial fallback 的挫折感。
* **4b. Progress Bar 進度可視化 (延後/低優先)**：此屬於純 UX 飾品，對決策品質無實質提升，僅建議在 Dev 本地環境中按需開啟，Prod 端的 Cron 自動執行時應完全跳過。

---

## 📌 優化實作優先序與決策矩陣

| 建議項目 | 採納狀態 | 實作槓桿 / 核心考量 |
|---|---|---|
| **Gemini 漏 — Audit 全 11 GICS** | **✅ 必做 (已於本輪完成驗證)** | 確保無隱性 silent fail，建立綠燈基準 |
| **建議 2: Deterministic Calculator** | **✅ 必做 (規劃雙軌測試)** | 算術正確性、防止歷史 decision 數據斷裂 |
| **建議 1: Explicit SECTOR_ALIASES** | **✅ 必做 (不使用 fuzzy 模糊)** | 預警上游改名，防錯優於通配 |
| **建議 3a: FTD Prompt 注入** | **✅ 做** | 成本極低，約束力強 |
| **建議 3b: Verbatim 精確 Assert** | **✅ 做 (不使用 regex)** | 邏輯簡潔，杜絕 LLM 二次加工 |
| **建議 4a: Pre-flight 1秒自檢** | **✅ 做** | 快速失敗 (Fast-Fail) 設計，省去無謂耗時 |
| **建議 4b: UX 進度條** | **⏳ 延後** | 純 UX 點綴，自動化 cron 跑時不需開啟 |

---

## 📋 具體實作計劃與程式碼變更指引 (Implementation Plan)

為確保上述 guardrails 落地不踩坑，我們制定了以下具體實作計劃，並進行 v3.14.5 的 Session 版本同步。

### 1. 別名目標精確對齊 (Alias Target Canonicalization)
* **變更範圍**：`sector_digest.py`、`tests/test_gics_sector_audit.py`
* **細節說明**：`SECTOR_ALIASES` 字典必須統一將各種外部 GICS 別名（如 "Consumer Cyclical", "Financial Services", "Real Estate" 等）精確映射至本 repo 的 **Canonical Sector Keys**：
  ```python
  SECTOR_ALIASES = {
      "Financial":              "Financials",
      "Financial Services":     "Financials",
      "Consumer Cyclical":      "Consumer_Discretionary",
      "Consumer Discretionary": "Consumer_Discretionary",
      "Consumer Defensive":     "Consumer_Staples",
      "Consumer Staples":       "Consumer_Staples",
      "Basic Materials":        "Materials",
      "Materials":              "Materials",
      "Communications":         "Communication",
      "Communication Services": "Communication",
      "Real Estate":            "Real_Estate",
      "REIT":                   "Real_Estate",
  }
  ```

### 2. FTD Verbatim 欄位組裝橋接與驗證 (FTD Assembly & Validation)
* **變更範圍**：`sector/scripts/build_sector_intel.py`、`sector/scripts/validate_sector_intel.py`
* **細節說明**：
  - **Builder 橋接**：在 `build_phase0` 函數（約 172 行）中，解析來自 `phase0_read_caches.py` 的 `ftd` layer 數據，從 `ftd_timeline` 中完整提取 `ftd_status_text`、`ftd_day_number`、`days_since_ftd`、`rally_day_count` 四個欄位，並將它們橋接寫入 final JSON 的 `_phase0["ftd"]` 內。
  - **Validator 收緊**：在 `validate_sector_intel.py` 內檢索 `_phase0.ftd` 結構時，新增斷言確保這四個 Verbatim 欄位存在，且 `ftd_status_text` 內容不為空，防止後續 LLM 幻覺重寫此欄位。

### 3. 心算計算器 (Score Calculator) 合約細節
* **變更範圍**：規劃新增 `sector/scripts/sector_score_calculator.py`
* **邊界合約合規計畫**：
  - **輸入合約**：接受 FRED 最新快取、Breadth、Theme-detector 等的 raw 欄位數據。
  - **執行模式分期**：
    - **Phase A (雙軌 Shadow Mode)**：在 `build_sector_intel.py` 組裝決策時，後台執行計算器，計算出各板塊的分數，並將其與 LLM 在 `decision.json` 中產出的 `composite_score` 與 `score_components` 進行比對。
    - **容差值合約**：允許浮點運算產生的 `abs(LLM_score - Calc_score) <= 1.0` 容差。若超出容差則發出 `stderr` 警報並輸出 `shadow_run_diff.json`，但不中止建置，以此進行 N 次 Session 的雙軌漂移驗證。
    - **Phase B (Authoritative Promotion)**：當雙軌運行連續 N 次均完全無誤後，正式切換為 Authoritative 模式，完全以計算器結果覆蓋並寫入最終的 `*_sector_intel.json`。

### 4. 解決新鮮度衝突 (Macro Freshness Consolidation)
* **變更範圍**：`sector/phase_0.md`
* **細節說明**：修改 `sector/phase_0.md` 第 5 行，將 `mtime < 3 小時` 的舊文字刪除，改為「統一以內部 `generated_at` < 3 小時為基準，不看 `mtime`（詳見主文件全局規則 2）」，徹底消除多檔案協定的指令矛盾。

### 5. 全板塊別名 pytest 自動化測試 (GICS Audit Test)
* **變更範圍**：`tests/test_gics_sector_audit.py`
* **細節說明**：建立 pytest 自動化測試檔，加載最新的主題偵測器快取（`skills/theme-detector/cache/theme_detector_*.json`），抓取 `sector_uptrend` 內的所有 Key，斷言經 `SECTOR_ALIASES` 處理後皆能完美對齊專案 11 大 Canonical Sector 鍵名，若出現未知的板塊 Key 則主動 raise。

---

## 🔑 Session 版本號同步 (v3.14.5) 指引

依照 `GEMINI.md` 的 Session 完工規範，當本報告通過使用者 OK 授權並執行完畢後，將同步執行以下三個檔案的版本升級：
1. **`VERSION`** 檔案改為 `3.14.5`
2. **`Dashboard/utils.js`** 第 11 行 `const VERSION = 'V3.14.5';`
3. **`CHANGELOG.md`** 新增 `## [3.14.5] — 2026-05-21` 區塊，記錄 Changes/Why。
4. **`SESSION_NOTES.md`** 新增 `v3.14.4 → v3.14.5` 說明。
5. **`TODO.md`** 更新完成狀態。

---

## 🧪 驗證與測試方案

在變更完成後，將執行以下 4 項檢驗以保證綠燈交付：
1. **Pytest 自動化 Audit 測試**：
   ```bash
   pytest tests/test_gics_sector_audit.py -v
   ```
2. **Validator 綠燈驗證**：
   ```bash
   python3 sector/scripts/validate_sector_intel.py
   ```
3. **Digest 執行測試**：
   ```bash
   python3 sector/scripts/sector_digest.py
   ```
4. **PyCompile 編譯安全檢查**：
   ```bash
   python3 -m py_compile sector/scripts/build_sector_intel.py sector/scripts/validate_sector_intel.py
   ```
