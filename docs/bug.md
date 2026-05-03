# AI 投資委員會 — Bug & 缺陷追蹤系統

本文件記錄系統在運行過程中發現的 Bug、UX 缺陷或架構性隱患。

---

## [BUG-001] 跨頁面導航導致掃描進度橫幅遺失
- **嚴重程度 (Severity)**: Medium
- **優先級 (Priority)**: High
- **狀態**: Resolved (2026-04-22)
- **發現日期**: 2026-04-21
- **修法**: `page-sector.js` 與 `page-news.js` 的 resume 區塊改為同時處理 `running` / `done` / `error` 三態；終態 (done/error) 僅在 `ended_at` 距今 5 分鐘內才恢復，避免舊結果永遠卡在畫面上。`done` 狀態保留直到使用者手動按 ✕ dismiss。

### 描述
當使用者啟動「產業掃描」或「新聞分析」後，若切換到其他頁面（如動能選股）再返回原頁面，原本顯示即時進度的資訊流卡片（Scan Card/Banner）會消失，使用者無法看到掃描是否完成或剩餘進度。

### 根因分析
1. **恢復邏輯過窄**：`page-sector.js` 與 `page-news.js` 在頁面載入時僅檢查 `status === 'running'`。若返回時任務已進入 `bridging` 或剛變為 `done`，則不觸發顯示邏輯。
2. **缺乏持久化 UI 狀態**：前端沒有記錄「我剛才啟動過一個任務」的意圖，完全依賴後端瞬時狀態回傳。

### 建議解法
- 修改前端 `Resume banner` 邏輯，支援 `running`, `bridging`, `done` 三種狀態的恢復。
- `done` 狀態應保留顯示至少 60 秒，或直到使用者手動關閉。

---

## [BUG-002] Protocol 鎖與動能掃描鎖的併發衝突隱患
- **嚴重程度 (Severity)**: High
- **優先級 (Priority)**: Medium
- **狀態**: Mitigated (2026-04-22)
- **發現日期**: 2026-04-21
- **修法**: `bridge.py` 寫 `Dashboard/data.json` 改為 atomic（寫 `.tmp` → `os.replace` 原子換檔）。兩個任務同時結束呼叫 bridge 時，JSON 不會被看到半截。未實作全域 heavy-task lock — 雙任務並跑仍會搶 CPU/IO，但不會再產出壞 JSON。如未來需要防止資源競爭，可另開 ticket 加 `_heavy_task_lock`。

### 描述
`run_protocol` (Sector/News/Invest) 使用 `_protocol_lock`，但 `run_momentum_screen` 使用獨立的 `_momentum_lock`。若使用者同時啟動兩者，會導致兩個重量級子進程競爭 CPU/IO 資源，且最終都會觸發 `bridge.py` 寫入同一個 `data.json`，極易造成資料損壞或掃描崩潰。

### 根因分析
後端鎖機制設計過於分散，缺乏全域的 **Heavy Task Arbiter**。

### 建議解法
- 在 `dashboard_server.py` 引入全域互斥鎖，或讓 `run_momentum_screen` 也檢查 `_protocol_lock`。
- 建立一個全域任務佇列，確保系統同時只有一個 Heavy Process (Claude Protocol 或 Volume Scan) 在執行。

---

## [BUG-003] Preflight 自動修補機制導致 UX 混淆
- **嚴重程度 (Severity)**: Low
- **優先級 (Priority)**: Low
- **狀態**: Resolved (2026-04-22)
- **發現日期**: 2026-04-21
- **修法**: 描述有誤 — preflight 不是 page load 自動跑，是使用者按「產業掃描」+ confirm 之後才觸發。真實 UX 痛點是 confirm 完看到「⏳ 更新基礎數據」長達 1-3 分鐘不知所云。改 `i18n.js` 的 `scan_confirm` 對話框文案，事先告知「若基礎數據過期會先自動更新（~1-3 分鐘）再進 Claude 掃描」。zh/en 同步。

### 描述（原始）
當數據過期（> 3h）時，打開產業掃描頁面會「靜默自動啟動」基礎數據更新（廣度/FTD）。使用者會看到「⏳ 更新基礎數據」但不知道為什麼它會自己動。

### 根因分析
`page-sector.js` 為了保證數據新鮮，實作了主動 POST `/api/preflight/run-free` 的邏輯。

### 建議解法
- 改為「被動提示」：彈出一個小黃條提示「數據已過期，[點此更新]」，由使用者決定。
- 或者在系統設置中加入「自動修補」開關。

---

## [BUG-004] 決策中心重複分析導致 Protocol 鎖死
- **嚴重程度 (Severity)**: Medium
- **優先級 (Priority)**: Medium
- **狀態**: Resolved (2026-04-22)
- **發現日期**: 2026-04-21

### 描述
點擊重新分析時，若多次連點或在分析中點擊其他股票，會因為 Protocol Lock 導致請求失敗，且 UI 保持禁用狀態，無法得知何時可以再次操作。

### 建議解法
- 已透過整合 `AnalyzeQueue` (2026-04-21) 解決大部分阻塞問題。
- 仍需優化：點擊後立即顯示琥珀色「佇列中」狀態（已實作）。

---

## [BUG-005] 掃描橫幅（Scan Banner）內容變化導致佈局抖動
- **嚴重程度 (Severity)**: Low
- **優先級 (Priority)**: Medium
- **狀態**: Resolved
- **發現日期**: 2026-04-21
- **修復日期**: 2026-04-21

### 描述
當產業掃描或動能掃描進行中時，中間的即時 Log 預覽文字長度變化（例如：條列 Skill 名稱）會導致右側的計時器與操作按鈕（展開/取消）位置發生水平漂移，甚至在某些情況下導致整個卡片高度抖動。

### 根因分析
1. **缺乏彈性空間限制**：中間的 Log 區域沒有強制 `truncate` 或固定 `flex-grow` 規則，導致其寬度隨內容「呼吸」。
2. **操作區未固定**：右側操作區（Timer + Buttons）沒有固定寬度，導致其成為佈局計算的被動方。

### 解決方案
- **三段式鎖定佈局**：
    - 左側標題區固定寬度。
    - 中間 Log 預覽區設為 `flex-1 min-w-0 overflow-hidden` 並強制 `truncate`。
    - 右側操作區固定寬度 `150px` 並向右對齊。
- 移除標頭的 `flex-wrap`，確保內容始終保持在單行水平線上。

---

## [BUG-006] 產業掃描 FTD day-counter 幻覺（欄位語意混淆）
- **嚴重程度 (Severity)**: High
- **優先級 (Priority)**: High
- **狀態**: Resolved (2026-04-26)
- **發現日期**: 2026-04-26（gemini code review 觸發）
- **修法**: `sector/ftd_yfinance.py` 新增 `ftd_timeline` 區塊輸出（含 `ftd_status_text` / `days_since_ftd` / `rally_day_count` / `ftd_day_number` 四欄）；`sector/phase_0.md` 層 C 加反幻覺規則，要求報告 FTD 狀態必須引用 `ftd_status_text` 原文；`sector/schema.md` Phase 0 / Phase 5 ftd block 補新欄位（V1.5 schema bump）。

### 描述
4/22 產業掃描報告寫 "FTD day 6"，但 4/21 報告寫 "FTD Day 14"。兩者皆指同一個 rally 週期內、僅相差 1 個交易日的時間點，物理上「day」應該每天 +1（4/21 是 N → 4/22 是 N+1），結果 AI 卻寫出反直覺的 14 → 6，引發 gemini 質疑「AI 抄歷史 JSON 當範本」。

### 根因分析（gemini 的指控錯了，真因如下）
底層 `ftd_detector` cache 同時提供三個語意完全不同的「Day」數字：

| 欄位 | 語意 | 4/21 值 | 4/22 值 |
|---|---|---|---|
| `sp500.ftd.ftd_day_number` | FTD 在 rally 第幾天確認（fixed，永不增加） | 6 | 6 |
| `sp500.rally_attempt.current_day_count` | rally 已進行幾個交易日（每天 +1） | 14 | 15 |
| `quality_score.breakdown.base` 字串 | `"Day 6 FTD: +60 (prime window)"` — `6` 是 prime-window 評分依據，**不是** days-since-FTD | "Day 6 FTD" | "Day 6 FTD" |

**phase_0.md / schema.md 完全沒規範 AI 該寫哪個**，於是兩天 AI 各自選不同欄位：
- 4/21：抓 `current_day_count = 14` → 寫成 "FTD Day 14"
- 4/22：抓 `quality_score.breakdown.base "Day 6 FTD"` → 直接抄成 "day 6"

這不是「抄範本偷懶」，而是**欄位 semantic ambiguity 導致 AI 行為不一致**。Gemini 提的「禁止讀歷史 JSON 當範本」會誤傷正常的 cache 讀取流程，治不了這個 bug。

附帶觀察：4/22 早上 breadth composite 仍是 42.4（與 4/21 同），原因是 TraderMonty CSV 上游每天約 22:00 後才更新前一日收盤資料，早上 7:30 跑只能拿到 4/20 數值。**這是上游資料 lag，不是 AI 抄襲**。

### 解決方案
1. **`sector/ftd_yfinance.py`** — 在輸出 JSON 加 `ftd_timeline` 區塊，提供 canonical 「FTD CONFIRMED, day {N} post-confirmation (rally-day {M}; FTD originally confirmed on rally-day {K})」字串供 AI 直接引用，並附 `_help` 欄位說明三個 day 的語意差異。
2. **`sector/phase_0.md`** 層 C — 增「FTD 文字反幻覺規則」：必引用 `ftd_status_text` 原文，禁止從 `quality_score.breakdown.base` 反推 day-counter。
3. **`sector/schema.md`** — Phase 0 / Phase 5 `_phase0` ftd block 加 `ftd_status_text` / `ftd_day_number` / `days_since_ftd` / `rally_day_count` 四欄（V1.5）。

### 後續觀察點
- 下次 sector_protocol 跑（4/27 早）應自動使用新 `ftd_status_text`；如果 AI 仍寫成「FTD Day N」格式，代表 prompt 沒讀進新規則，要再強化 phase_4-5.md 內的引用語法。
- Validator 只驗 `state` + `quality_score`，新欄位 additive，不會破壞既有 sector_intel.json 通過率。
