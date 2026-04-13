# INTEL COMMAND — Todo List
> Last Updated: 2026-04-13
> Last Session Note: Phase 1 ARCH 重構完成（utils.js + components.js + 6頁 sidebar 組件化）；執行產業掃描 → RISK_OFF，廣度 36.8，XLP HOT，銀行財報 & 伊朗停火為本週 Binary；bridge.py 更新 data.json

---

## ✅ 已完成

- [x] Dashboard 基本頁面架構（index / sector / news / history）
- [x] CSS 變數主題系統（dark/light mode）
- [x] i18n 雙語支援（zh/en）
- [x] `bridge.py` 雛形（讀取 invest_logs + news_logs → data.json）
- [x] `viewReport()` 彈窗支援 .md 和 .html 報告
- [x] System Logs debug console
- [x] `ARCHITECTURE_REVIEW.md` 架構分析文件
- [x] **[BRIDGE-1]** 修復 `fear_greed` 擷取路徑 bug（`_phase3.political_overlay.fear_greed_index`，值 15）
- [x] **[BRIDGE-2]** 新增 `sectors[]` 陣列擷取，`sector.html` 改從 `data.json.sectors` 讀取
- [x] **[BRIDGE-3]** 新增 warm / cold / avoid sectors 至 market summary
- [x] **[BRIDGE-4]** 新增 `macro_multiplier` 和 `exposure_ceiling`（sector.html 顯示真實值）
- [x] **[SECTOR-1/2/3]** Sector heatmap 改用真實資料，verdict badge + proxy_etf + risk_flags
- [x] **[LAUNCH-1]** 快速啟動引擎：輸入 ticker → `分析 TICKER` 指令 + copy-to-clipboard
- [x] **[LAUNCH-2]** 修正 `index.html` 導航 `href="#"` → `href="history.html"`

---

## 🚀 路線 A — 現有資料補完（零新 skill，純利用 logs）

### A1 · `watchlist.html` 進場雷達（新頁面）

- [x] ~~**[A1-BRIDGE]** `bridge.py` 補出 watchlist 專用欄位~~
  - ~~`watch_conditions` (entry_A/B/C) → `recent_analysis[].watch_conditions`~~
  - ~~`key_risks[]`, `risk_reward_ratio`, `position_size_pct`, `avg_confidence`, `time_horizon`~~
  - ~~新增 `binary_risks[]`, `divergence_watch[]`, `breadth{}` 欄位~~

- [x] ~~**[A1-PAGE]** 建立 `watchlist.html`~~
  - ~~分兩區：ACTIVE（EXECUTE）/ WAITING（watch_conditions）~~
  - ~~每張卡：entry_A/B/C 觸發條件 + key_risks 標籤 + R/R + 信心指數 + DA badge~~
  - ~~Filter tabs (ALL / ACTIVE / WAITING)、Summary stats row~~

- [x] ~~**[A1-NAV]** 所有頁面 sidebar 加入「進場雷達」導航（radar 圖示）~~

### A2 · 強化 `index.html` 主儀表板

- [x] ~~**[A2-WARN]** `_phase0.warning_flags` 頂部警告 banner~~
  - ~~Death_Cross / Extreme_Fear 旗幟顯示，附 Uptrend Ratio 百分比~~
- [x] ~~**[A2-BREADTH]** `uptrend_ratio_overall` mini gauge（Market Regime 卡底部橫條）~~

### A3 · 強化 `sector.html` 產業掃描

- [x] ~~**[A3-ROTATION]** Sector tile 加入 `rotation_signal`（▲INFLOW / ▼OUTFLOW）+ uptrend bar~~
- [x] ~~**[A3-DIVERGE]** 底部新增 `sector_divergence_watch` 區塊（signal + action + description）~~
- [x] ~~**[A3-NOTES]** Strategy Notes 改從真實資料生成（HOT/COLD sector key_reason + DA note）~~

### A4 · 強化 `news.html` 即時新聞

- [x] ~~**[A4-CALENDAR]** 右側欄 `upcoming_binary_risks` 倒數（T-Xd + 受影響產業 tags）~~
- [x] ~~**[A4-TRUMP]** `trump_trade_signals[]` 政策交易信號卡片（右側欄新增 Policy Trade Signals 區塊）~~

### A5 · 強化 `history.html` 決策歷史

- [x] ~~**[A5-RISKS]** 每張卡展開顯示 `key_risks[]` 標籤~~
- [x] ~~**[A5-COND]** 顯示 `watch_conditions.entry_A/B/C` 觸發條件（CANCEL 卡才顯示）~~

---

## 📅 路線 B — `calendar.html` 財報 & 事件日曆

- [ ] **[B-BRIDGE]** `bridge.py` 導出 `upcoming_binary_risks[]` + `sector_news_sentiment{}`
- [ ] **[B-PAGE]** 建立 `calendar.html`
  - 週曆視圖，顯示財報日期、FOMC、地緣政治 binary events
  - 每個事件顯示受影響產業 + direction（bullish/bearish/binary）
  - 資料來源：`_phase3.upcoming_binary_risks`（已有）+ `earnings-calendar` skill（補完）
- [ ] **[B-SKILL]** 整合 `earnings-calendar` skill（FMP API），產出 JSON cache 讓 bridge 讀取

---

## 📊 路線 C — `breadth.html` 市場廣度雷達

- [x] ~~**[C-BRIDGE]** `bridge.py` 導出 `_phase0` 完整廣度資料~~
  - ~~`breadth_components{}`, `warning_flags[]`, `uptrend_ratio_overall`, `cycle_phase`, `regime_confidence`~~
  - ~~新增 `data.breadth{}` 子物件供 breadth.html 專用~~
- [x] ~~**[C-PAGE]** 建立 `breadth.html`（386 行）~~
  - ~~廣度綜合儀表（0–100 semicircle gauge）~~
  - ~~4 個分量 bar：`overall_breadth`, `sector_participation`, `momentum`, `mean_reversion_risk`~~
  - ~~Warning flags 視覺化（badge grid）~~
  - ~~`uptrend_ratio` per sector（來自 `data.sectors[]`，依比例排序）~~
  - ~~Regime confidence bar、Cycle phase、Exposure ceiling stat cards~~
  - ~~Analyst Notes 區塊（選填）~~
- [x] ~~**[C-FTD]** 整合 `ftd-detector` skill 產出，顯示 FTD 狀態 + Distribution Days~~
  - ~~FMP endpoint 已停用，改寫 `sector/ftd_yfinance.py` yfinance 轉接器，重用 skill 原有分析邏輯~~
  - ~~bridge.py 新增 `load_ftd_cache()` + `extract_ftd_data()`，輸出 `data.ftd{}`~~
  - ~~breadth.html 新增 FTD Detector 區塊：State/Quality/Exposure + FTD Event + Post-FTD Health 三欄~~
  - ~~cache 路徑：`sector/ftd_cache/ftd_detector_YYYY-MM-DD_*.json`~~
- [x] ~~**[C-TOP]** 整合 `market-top-detector` skill，顯示市場頂部概率~~
  - ~~`sector/market_top_yfinance.py` yfinance 轉接器，`YFinanceClient` drop-in 替代 FMPClient~~
  - ~~bridge.py 新增 `load_market_top_cache()` + `extract_market_top_data()`，輸出 `data.market_top{}`~~
  - ~~breadth.html 新增 Market Top Detector 區塊（Row 6）：Top Probability score + zone badge + 6 components bar + actions + FTD monitor~~
  - ~~cache 路徑：`sector/market_top_cache/market_top_YYYY-MM-DD_*.json`~~
- [x] ~~**[C-BREADTH]** 整合 `market-breadth-analyzer` skill（Monty's CSV），取代 phase0 的估算值~~
  - ~~sector_protocol_v1_1.md Phase 0 加入 script 執行 + cache 邏輯 + 欄位映射表~~
  - ~~bridge.py 新增 `load_breadth_cache()` + `extract_breadth_from_analyzer()`~~
  - ~~data.breadth 新增 `components_full`（6組件）、`zone`、`trend_direction`、`actions`、`key_levels`、`current_8ma/200ma`~~
  - ~~breadth.html 升級：6組件 bar（含 weight + signal）、zone badge、trend badge、actions、Key Levels 區塊~~
  - ~~cache 路徑：`sector/breadth_cache/market_breadth_YYYY-MM-DD_*.json`~~

---

## 🏗️ 架構重構路線（ARCH — MVP Pattern）

> **設計目標**：用 MVP（Model-Presenter-View）把目前散落在各 HTML inline script 的邏輯分層，
> 同時消除重複代碼、提升效能，但保持 **pure HTML/JS 無框架**，方便維護。
>
> **分層定義**：
> - **Model** → `data-store.js`：單一資料來源、TTL cache、change event
> - **Presenter** → `page-*.js`：每頁業務邏輯，訂閱 Model、操作 View
> - **View** → HTML + `components.js`：純 render 函數，只接受資料輸出 DOM string/node
> - **Shared Utils** → `utils.js`：theme/lang/log/lucide 等通用工具

---

### Phase 1 — 消除重複（低風險，Quick Win）

> 目標：把 5 個頁面都有的重複函數抽到共用檔，不改任何 UI 行為。

- [x] ~~**[ARCH-1]** 建立 `Dashboard/utils.js`~~
  - 移入：`initTheme()`, `toggleTheme()`（目前 script.js + 4 HTML 各一份）
  - 移入：`currentLang` state + `toggleLang()`（各頁 ~20 行重複）
  - 移入：`logToUI(msg, type)`（完全相同，5 個檔案）
  - 移入：`viewReport(path)`（目前只在 script.js，但 watchlist/news 呼叫不到）
  - 移入：`updateMarketStatus()`（目前只在 script.js，history.html 用不到）
  - 加上：`lucide.safe()` wrapper（try-catch 包住 `lucide.createIcons()`）
  - 所有頁面改 `<script src="utils.js">` 取代重複 inline 代碼
  - **估計削減**：~400 行重複代碼

- [x] ~~**[ARCH-2]** 建立 `Dashboard/components.js`（純 render 函數）~~
  - 移入：`renderProgressBar(val, max, color)` → 通用進度條 HTML string
  - 移入：`renderBadge(label, color, style)` → 通用 badge HTML string
  - 移入：`renderFlagBadge(flag, translations)` → 目前 breadth.html + script.js 各有一份
  - 移入：`renderSignalCard(icon, label, val, sub, color, bar, link)` → index.html signal angles
  - 移入：`renderAuditCard(item, compact)` → 合併 `renderAuditCard` + `renderAuditCardCompact`（compact flag 控制）
  - 統一 `glass-card` wrapper 邏輯
  - **估計削減**：~250 行重複代碼

- [x] ~~**[ARCH-3]** Sidebar HTML 組件化~~
  - 建立 `_sidebar.html` snippet（或 JS function `renderSidebar(activePage)`）
  - 六個頁面目前各自複製完整 sidebar HTML（~50 行 × 6 = 300 行重複）
  - 方案 A（簡單）：JS function 動態插入，頁面只留 `<aside id="sidebar"></aside>`
  - 方案 B（SSI）：若未來有輕量後端，用 server-side include
  - 推薦方案 A，純 JS，零依賴

---

### Phase 2 — Data Layer（Model 層）

> 目標：建立單一資料來源，消除各頁各自 fetch、無 cache 的問題。

- [ ] **[ARCH-4]** 建立 `Dashboard/data-store.js`（DataStore singleton）
  ```
  window.DataStore = {
    _cache: null,
    _ttl: 60_000,          // 60秒 TTL，與現有 setInterval 對齊
    _lastFetch: 0,
    _listeners: [],
    async get(force = false),  // 有 cache 直接返回，過期才重 fetch
    subscribe(fn),             // 頁面 Presenter 訂閱 change event
    refresh(),                 // 手動強制刷新
  }
  ```
  - 解決問題：目前 6 個頁面每次刷新都獨立 fetch，切換頁面不共用 cache
  - 加入 `AbortController`，防止快速連點刷新產生 race condition
  - 加入 retry（最多 2 次，指數退避）

- [ ] **[ARCH-5]** 各頁改用 `DataStore.get()` 取代直接 fetch
  - `index.html` / `script.js` 的 `updateDashboard()`
  - `news.html` 的 `loadNews()`
  - `watchlist.html` 的 `loadWatchlist()`
  - `breadth.html` 的 `loadBreadth()`
  - `sector.html` 的 `loadSectorData()`
  - **估計效益**：頁面切換無需重 fetch；同頁多次刷新不疊加請求

---

### Phase 3 — Presenter 層（各頁邏輯分離）

> 目標：把各頁 inline `<script>` 移到獨立 JS 檔，HTML 只留純結構。

- [ ] **[ARCH-6]** 抽出 `Dashboard/page-breadth.js`
  - 移出 breadth.html 內 ~620 行 inline script
  - 保留：`buildGauge()`, `componentBar()`, `flagBadge()`, `sectorUptrendRow()`, `loadBreadth()`
  - tooltip engine 可留在 breadth.html（breadth 專用）或移入 utils.js（若其他頁也需要）
  - breadth.html 只留 HTML skeleton + `<script src="page-breadth.js">`

- [ ] **[ARCH-7]** 抽出 `Dashboard/page-watchlist.js`（watchlist.html inline ~300 行）
- [ ] **[ARCH-8]** 抽出 `Dashboard/page-news.js`（news.html inline ~250 行）
- [ ] **[ARCH-9]** 抽出 `Dashboard/page-sector.js`（sector.html inline ~250 行）
  - 保留 Chart.js instance 管理邏輯（sectorchart 有 update/destroy 邏輯）

- [ ] **[ARCH-10]** `script.js` 瘦身 → 成為 `page-index.js`
  - 目前 script.js 混了：全域工具函數 + index.html 專用邏輯
  - 全域工具 → 移入 utils.js / components.js
  - index 邏輯 → 重命名為 page-index.js 或保留 script.js 但清除重複

---

### Phase 4 — 效能優化

> 目標：減少不必要的 CPU/網路消耗，不影響現有功能。

- [ ] **[ARCH-11]** `lucide.createIcons()` 防抖（debounce）
  - 目前全站呼叫 ~12 次以上（初始化 + 每次 DOM 更新）
  - 在 utils.js 加入 `scheduleIconUpdate()` — 用 `requestAnimationFrame` 批次執行
  - 替換所有直接 `lucide.createIcons()` 呼叫
  - **估計效益**：減少 ~50% 重複 DOM scan

- [ ] **[ARCH-12]** Chart.js 惰性載入（僅 sector.html 需要）
  - 目前 index.html 也載入了 Chart.js（`script src cdn.jsdelivr.net/npm/chart.js`）
  - 改為在 sector.html + calendar.html 才載入
  - 或改為動態 import：`import('https://cdn.jsdelivr.net/.../chart.js')`
  - **估計效益**：index.html 減少 ~200KB JS 解析

- [ ] **[ARCH-13]** marked.js 惰性載入（僅 viewReport() 觸發時才載入）
  - 目前所有有 report modal 的頁面都載入 marked（index + watchlist + history）
  - 改為 viewReport() 第一次呼叫時動態載入
  - **估計效益**：每頁減少 ~45KB

- [ ] **[ARCH-14]** innerHTML XSS 防護
  - 建立 `escapeHTML(str)` helper（utils.js）
  - 套用到所有用 `innerHTML` 渲染 data.json 文字欄位的地方
  - 高風險欄位：`news.headline`, `sector.key_reason`, `sector.risk_flags[]`, `item.key_risks[]`
  - **注意**：data.json 是本地產生（trusted source），優先度 Medium，但養成習慣

---

### 舊版架構債（保留）

- [ ] **[BRIDGE-5]** 自動觸發機制：`run_bridge.sh` 或 `.claude` post-analysis hook
- [ ] **[JS-1]** ← 已被 ARCH-1 取代，可視為同一件事
- [ ] **[SIDEBAR-1]** ← 已被 ARCH-3 取代

---

## 🔁 Bridge 雙向架構（最終目標）

```
Dashboard [watchlist.html]
    輸入 Ticker → copy 指令 → Claude Code 終端機
                                    ↓
              investment_protocol_v4_5 執行
                                    ↓
                    invest_logs/history.json  +  reports/
                                    ↓  (bridge.py 自動觸發)
                              data.json 更新
                                    ↓  (60s polling)
        Dashboard 所有頁面自動刷新顯示最新結果
```

### Protocol → Log → Dashboard 對應表

| Protocol | 產出 Log | Bridge 讀取 | Dashboard 顯示 |
|----------|---------|------------|----------------|
| `investment_protocol_v4_5` | `invest_logs/history.json` | final_action, score, entry/tp/sl, **watch_conditions**, **key_risks** | history + **watchlist** |
| `sector_protocol_v1_1` | `sector_logs/*_sector_intel.json` | market_regime, sectors[], themes, fear_greed, **_phase0 breadth**, **_phase3 binary_risks** | sector + index + **breadth** + **calendar** |
| `news_protocol_v1` | `news_logs/*_digest.json` | verdicts[], **trump_signals**, **upcoming_events** | news + **calendar** |
| `theme-detector` skill | `skills/theme-detector/cache/*.json` | themes[], heat_scores, stocks | index themes（待加強） |
