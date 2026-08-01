# AI Investment Committee — 產業掃描協定 (Sector Protocol) 深度審查、優化建議與實作計劃報告

本報告針對目前的 **Pre-Market Sector Intelligence Protocol (V1.4)** 進行了深度架構審查、代碼流追蹤與實例驗證，並整合了具體的實作計劃（Implementation Plan）。

本報告包含：
1. 協定核心規則與關鍵 Bug 修正（已落實）
2. 全 11 GICS 板塊對齊 Audit 驗證結果
3. 系統性優化方案（細節修正與路徑防坑版）
4. 具體實作計劃與程式碼變更指引（五大實作防線與階段合約）
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

## 💡 系統性優化方案 (細節修正與路徑防坑版)

依據系統算術正確性優先、防止靜默失效及漸進遷移原則，我們重新整理了五大優化建議與實作細節：

### 建議一：建立共享的顯式 Alias 模組與未知報錯 (徹底防止板塊名稱漂移)
> [!IMPORTANT]
> **設計漏洞防範**：
> 移除空格、底線、轉小寫及去 "services" 等「模糊匹配 (fuzzy matching)」方式在實務上會產生重大 bug（例如：會將 "Consumer Services" 誤合為 "Consumer"，或通配 "Communications" 與 "Communication Services" 兩個合法板塊）。模糊比對會吞掉新型態的 alias 命名，導致靜默失敗。

* **正解方案**：
  板塊名稱別名漂移的影響絕不僅限於 `sector_digest.py` 的顯示。如果 LLM 在 `decision.json` 中寫入帶空格的板塊名，或者上游/FRED 返回了不同的格式，Builder、Validator、Step6 與 Digest 等所有組件都會踩坑，導致快取載入失敗或 downstream keys 漂移。
  因此，我們必須建立一個**共享的別名工具模組 `sector/lib/sector_utils.py`**。
  - 維護一個顯式的 **`SECTOR_ALIASES` 字典**，映射目標**必須嚴格使用專案 Canonical Keys**（例如：`Consumer_Discretionary`，帶底線且去 services 的 repo canonical 格式），不能對齊到 GICS display/prose 名稱。
  - 提供 `canonicalize_sector_name(name)` 函數，為 `sector_digest.py`、`build_sector_intel.py`、`validate_sector_intel.py` 與 `step6_overlay.py` **統一導入使用**。
  - 對於未知的板塊名稱，**必須主動向 stderr 輸出警報**，確保新板塊或 API 命名異動能第一時間被發現。

---

### 建議二：Deterministic `sector_score_calculator` 計算器與精確分數階段合約
> [!TIP]
> **實作核心**：
> 目前協定的 `Scoring Rubric` 包含多步複雜的乘數與 Penalty 疊加（Step 1 至 Step 5b），LLM 心算極易產生隨機算術漂移。將其代碼化是保證決策模型一致性的最優解。

為防止過渡期架構與比對基線衝突，計算器實作與驗證必須遵循以下分數合約：
1. **分數階段合約 (Score Stages Contract)**：
   由於 Step 6 FRED Macro Regime Overlay 是在 Step 1-5 之後單獨套用的（如 `sector/phase_4-5.md:241` 所定義），直接將計算器輸出與最終的 `composite_score` 做單一對比會產生嚴重的噪聲。我們定義精確的三個分數階段：
   - **`base_score`**：Step 1 之前的基底分數：`breadth_momentum` + `theme_heat` + `news_catalyst` + `rotation_signal` (範圍 [0, 100])。
   - **`pre_step6_score`**：Step 1 至 Step 5b 運算後的得分（包含動態權重調整、Step 5 特殊條件乘數、Valuation Penalty Overlay，並完成 `[0, 100]` 限制）。此分數與 LLM 在 `decision.json` 中的 `score_components` 加總基準進行對比（此時尚未套用 FRED 乘數）。
   - **`post_step6_score`**：`pre_step6_score` 乘以 Step 6 FRED Overlay 乘數後的最終分數（同樣經過 `[0, 100]` 限制）。此階段分數與頂層最終的 `composite_score` 進行對照比對。
2. **FRED 互斥邏輯**：當 `fred_available = true` 時，計算 `pre_step6_score` 必須**自動 SKIP Step 1 (Cycle Phase) 的乘數調整**，直接在後續由 Step 6 FRED Regime Overlay 取代，絕對不能重複計算以防雙重計分。
3. **Explicit 快取路徑管理**：計算器與 Step 6 必須使用絕對/顯式路徑指定快取來源，嚴防因路徑漂移而默默讀取到舊快取。
4. **Dual-Run 漸進式遷移驗證**：在 `build_sector_intel.py` 內以 Shadow Mode 方式呼叫計算器，將其計算結果（`pre_step6_score` 與 `post_step6_score`）與 `decision.json` 中的數據進行對比，設定浮點數四捨五入容差為 `diff <= 1.0`。若超出容差則輸出日誌，確保在 N 次 Sessions 驗證無誤後再行正式割接。

---

### 建議三：FTD 反幻覺 — 提示注入與 Verbatim 緩存比對
> [!WARNING]
> **設計漏洞防範**：
> 在 `validate_sector_intel.py` 中使用 `\bDay X FTD\b` 這類寬泛的 regex 檢索容易誤判（例如歷史描述中合法的 "Previous Day 6 FTD in March" 會中招）。

* **優化方案**：
  1. **Prompt 注入 (Step 3a)**：在 `phase0_read_caches.py` 中輸出 `ftd_status_text` 提示，約束 LLM 發言，此方法成本極低且效益顯著。
  2. **Verbatim 雙向比對 (Step 3b)**：僅檢查欄位存在與非空並不能杜絕 LLM 幻覺重寫。最健壯的校驗是：
     在 `validate_sector_intel.py` 內，直接讀取**當前/最新的 FTD 快取 JSON** 內的 `ftd_timeline.ftd_status_text`，將其與組裝好的 `_phase0.ftd.ftd_status_text` 進行**字串精確比對 (Verbatim Assert)**。只要字串不精確匹配即視為重寫/幻覺，簡潔且 100% 精準。

---

### 建議四：改善 Parallel Subagent 超時降級的預警與健康度自檢
* **4a. Pre-flight 1-Sec 快取自檢 (高優先)**：在 protocol 執行最前端，用 1秒時間預檢 FMP 剩餘額度、FRED 密鑰狀態與 Breadth CSV 解析完備性。這能大幅降低運行 5 分鐘後才在 Phase 4a 觸發 degraded partial fallback 的挫折感。
* **4b. Progress Bar 進度可視化 (延後/低優先)**：此屬於純 UX 飾品，對決策品質無實質提升，僅建議在 Dev 本地環境中按需開啟，Prod 端的 Cron 自動執行時應完全跳過。

---

### 建議五：Step 6 FRED 預設快取路徑防護
* **正解方案**：
  `step6_overlay.py` 的預設快取路徑若使用相對路徑，在不同的工作目錄（Cwd）下執行時可能會解析失敗。
  我們必須在腳本中實現強健的基準路徑解析：使用專案根目錄定位器（以 `CLAUDE.md` 作為 repo 根標記），並在找不到快取時主動印出清晰的引導訊息，防止在不帶 CLI 參數的 Cron 自動執行時默默讀不到快取。

---

## 📋 具體實作計劃與程式碼變更指引 (Implementation Plan)

為確保上述 guardrails 落地不踩坑，我們制定了以下具體實作計劃，並進行 v3.14.5 的 Session 版本同步。

### 1. 建立共享別名工具模組與對齊 (Shared Alias Utility)
* **變更範圍**：[NEW] `sector/lib/sector_utils.py`、`sector_digest.py`、`build_sector_intel.py`、`validate_sector_intel.py`、`step6_overlay.py`、`fetch_sector_valuation.py`、`tests/test_gics_sector_audit.py`
* **細節說明**：
  - 新增 `sector/lib/sector_utils.py`，定義 `CANONICAL_SECTORS`、`SECTOR_ALIASES` 與 `canonicalize_sector_name(name: str) -> str` 函數。
  - 將別名映射目標嚴格設為 repo canonical keys，對於未知別名向 stderr 警告並安全 fallback。
  - **跨組件整合**：
    - `sector_digest.py`、`step6_overlay.py` 與 `fetch_sector_valuation.py` 在比對、快取下載與對齊時導入此函數與 `PROJECT_TO_FMP`，徹底統一 FMP 映射與 GICS 解析。
    - `build_sector_intel.py` 在合併 `decision.json` 時，統一用 `canonicalize_sector_name(s["name"])` 對齊板塊名，徹底消滅空格/大小寫引起的 valuation 快取載入失敗與 key 漂移。

### 2. FTD Verbatim 雙向比對與橋接 (FTD Assembly & Cache Verification)
* **變更範圍**：`sector/scripts/build_sector_intel.py`、`sector/scripts/validate_sector_intel.py`
* **細節說明**：
  - **Builder 橋接**：在 `build_phase0` 中提取 `ftd_timeline`，將 `ftd_status_text`、`ftd_day_number`、`days_since_ftd`、`rally_day_count` 橋接複製寫入最終 JSON 的 `_phase0["ftd"]`。
  - **Validator Verbatim 雙向斷言**：在 `validate_sector_intel.py` 中，載入最新 FTD 快取，提取快取內 `ftd_timeline.ftd_status_text` 原值，與組裝後的 `_phase0.ftd.ftd_status_text` 進行精確字串比對，若不匹配則 raise schema compliance error，強效阻斷 LLM 的二次加工。

### 3. 心算計算器 (Score Calculator) 精確合約設計
* **變更範圍**：[NEW] `sector/scripts/sector_score_calculator.py`
* **邊界合約合規計畫**：
  - **加總範圍驗證 (Verified)**：經分析 `decision.json` 之 `score_components`，四個維度評分皆在 `[0, 25]` 區間內，相加剛好為 `[0, 100]`，已在代碼中落實 `base_score = max(0, min(100, base_score))` 限制。
  - 設計 `sector_score_calculator.py`，完整復刻 `sector_protocol_main.md` 的所有 Rubric 計算步驟（Step 1 - 5b & Step 6）。
  - 當 `fred_available=true` 時，自動將 Step 1 (Cycle Phase) 設為 1.0 (跳過)，由後續的 Step 6 FRED regime overlay 處理。
  - **雙軌驗證路徑**：在 `build_sector_intel.py` 中，載入計算器進行 shadow 運算。將計算出來的 `pre_step6_score` 與 `decision.json` 中的 `score_components`（各項加總）進行比對，將 `post_step6_score` 與頂層 `composite_score` 比對。容差設為 `diff <= 1.0`。
  - **Dual-Run 割接達標基準 (Concrete Criteria)**：
    - 累計執行 **N=5 次** 雙軌運行會話 (dual-run sessions)。
    - **0 個** hard diff > 1.0 (重大計算偏差)。
    - **≤ 2 個** soft diff (0.5–1.0) (浮點四捨五入或乘積累積誤差容差)。
    - **0 個** penalty_drift 估值懲罰判定偏差。
    - 全部達標方可正式割接；否則修正計算器後重新進行 N=5 輪驗證。

### 4. 解決新鮮度衝突 (Macro Freshness Consolidation)
* **變更範圍**：`sector/phase_0.md`
* **細節說明**：修改 `sector/phase_0.md` 第 5 行，將 `mtime < 3 小時` 改為「統一以內部 `generated_at` < 3 小時為基準，不看 `mtime`（詳見主文件全局規則 2）」，徹底消除協定指令衝突。

### 5. Step 6 FRED 預設快取路徑防坑修正
* **變更範圍**：`sector/scripts/step6_overlay.py`
* **細節說明**：檢驗並測試 `step6_overlay.py:194` 的相對路徑解析，引入根目錄定位器定位 `CLAUDE.md` 以計算絕對路徑，確保絕對路徑精確指向 `repo_root/skills/fred-macro/cache/fred_latest.json`，防止在不帶 CLI 參數的 Cron 自動執行時默默讀不到快取。

### 6. 全板塊別名 pytest 自動化測試 (GICS Audit Test)
* **變更範圍**：`tests/test_gics_sector_audit.py`
* **細節說明**：建立 pytest 自動化測試，定期載入最新 `theme_detector_*.json` 快取，利用共享模組 `sector_utils` 別名解析全部 `sector_uptrend` 板塊，斷言其屬於 11 大 Canonical Sector 鍵名之一。內置 `@pytest.mark.skipif` 機制，若無快取自動 skip 以避免 CI 假陽性報錯。

---

## 🔑 Session 版本號同步 (v3.14.5) 指引

依照專案 canonical 的 **`CLAUDE.md` 與 `AGENTS.md`** 的 Session 完工規範，當本報告通過使用者 OK 授權並執行完畢後，將同步執行以下檔案與版本標記的升級：
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

