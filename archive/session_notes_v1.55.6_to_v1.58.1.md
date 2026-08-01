# Session Notes 歸檔 v1.55.6 → v1.58.1（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v1.58.1) — 富途 HK/A 股過濾 + 決策日曆 today 動態化

### A) Futu push HK/A 股過濾（`scripts/parse_futu_notifications.py` + `dashboard_server.py`）
- 加 `_HK_CN_HARD_KEYWORDS` (~25 個：港股/恒生/A股/滬深/上證/科創板/港元/南向資金/.HK/.SH/.SZ 等)
- 加 `_HK_CN_ONLY_NAMES` (~50 個：騰訊/美團/小米/中國移動/工商銀行/中國平安/寧德時代/茅台/萬科/京東方/海康威視/藥明康德 等)
- 加 HK 5 位代碼 + CN 6 位代碼 regex
- `load_notifications()` 加 `filter_hk_cn=True` 與 `return_stats=True` 參數；endpoint 預設過濾並回傳 `filtered_count`
- CLI 加 `--no-filter` opt-out
- 200 筆樣本驗證：精準抓出 41 筆 HK/CN（涵蓋恒指/南向資金/中國平安/寧德時代/中信證券 等樣式），美股相關全部保留

### B) 決策日曆 today hardcode 修正（`Dashboard/page-calendar.js`）
- Bug：`todayIso` 之前吃 event_index.json 的 `j.today`，indexer 沒重跑時鎖在 2026-04-26；月份預設亦 hardcode `new Date(2026, 3, 1)`；7-day 視窗 fallback `'2026-04-26'`
- 修：加 `browserTodayIso()` helper，`todayIso` 始終取瀏覽器當天；`currentMonth` 預設改成當天月份；indexer 的 `j.today` 改名 `indexedAt`，僅在 stats 行顯示供 staleness 提示（`today=YYYY-MM-DD · indexed=YYYY-MM-DD`）
- 移除所有 `2026-04-26` / `new Date(2026, 3, 1)` hardcode

## 🟢 Session Note (v1.58.0) — 路線 P 富途即時推播整合（lazy fetch + ticker 辨識）

把 macOS 富途牛牛客戶端 IM SQLite (`msg_0.db`) 推播接進 Dashboard，5 筆顯示在 index.html Layer 5。

### 1) `scripts/parse_futu_notifications.py` 重寫
- 新增 `load_notifications(limit, keyword, with_tickers)` 純資料函式 + `is_available()` + `extract_tickers(text)`
- 中文公司名 → US ticker dict（~70 筆，Mag-7 / 半導體 / SaaS / 中概 ADR / 金融 / 能源 / 民生 / 醫藥 / crypto）
- 英文 ticker regex `[A-Z]{2,5}` + stopword 過濾（避免 AI/CEO/RAS/NEW 等誤判）
- 加 `--json` flag；保留原 CLI 列表行為

### 2) `dashboard_server.py` 新增 endpoint
- `GET /api/futu-notifications?limit=5`：lazy fetch（無背景 thread），5s 記憶體 cache 防抖
- DB 找不到 → `{available:false}`，client 顯示「客戶端未安裝」
- script lazy import `parse_futu_notifications`，模組載入失敗也不影響 server 啟動

### 3) `Dashboard/index.html` 加 Layer 5 卡片
- glass-card「富途即時推播」全寬，含 reload 按鈕 + 5 筆 list 容器

### 4) `Dashboard/script.js` 新增 IIFE renderer
- 每筆顯示相對時間（`Xs/Xm/Xh`）+ ticker pills + 推播全文
- 點 ticker pill → 預填 Quick Launch input + scroll + toast（不直接入隊，避免誤觸燒 token）
- 60s 自動重整；reload 按鈕手動觸發

### 5) `Dashboard/i18n.js` 新增 5 個鍵
- `futu_push_title / futu_reload / futu_loading / futu_no_data / futu_unavailable`（中英）

### 設計取捨
- **不放背景 thread**：用戶不在 Dashboard 時不需要查 DB，lazy fetch + 5s cache 已足
- **ticker pill 不直接入隊**：只 prefill ticker-input，最終由 user 手動點「分析」決定是否花 ~$4 tokens
- **不動 daily_update.sh**：富途推播是純查詢層，不影響 protocol 流水線

### Smoke test
- `python3 scripts/parse_futu_notifications.py --json -n 5` 正確輸出 ticker（NVDA/BTC/GOOGL/POET 等）
- `curl /api/futu-notifications?limit=3` 200 OK，2nd hit 0.6ms（cache 命中）
- index.html 含 `futu-card` + `futu_push_title` 元素

### TODO 進度
- [P-TICKER] / [P-BACKEND] / [P-CARD] 全部完成

## 🟢 Session Note (v1.57.0) — Tooltip 升級 Wave 2：radar / momentum 全頁套上 stages-with-action 風格

延續 v1.56.0 (sector pill rich tooltip)，這版把同樣的 stage-row + action-verb 解說方法擴到 radar 與 momentum 頁面。

### Radar (`page-radar.js` + `style.css`)

**內容升級** — 給 9 個關鍵 metric 加 `stages` 陣列（每階段含 dot + range + tag + action verb + detail）：
- mid_heat（3 階段：熱/溫/冷）
- short_bull（4 階段：unanimous/majority/split/bearish）
- avg_conv（3 階段：高/中/低）
- confidence（3 階段：強/中/弱）
- driver_atr（3 階段：高/中/低 → 倉位反向）
- factor（3 階段：amplify/normal/dampen）
- spy_rsi（5 階段：含逆向 contrarian 訊號）
- vix（5 階段：calm/normal/elevated/high/panic）
- yield_curve（3 階段：含倒掛衰退預警）
- credit_spread（3 階段：寬鬆/正常/緊縮）

**引擎升級** — `showRadarTip` 加上：
- `RADAR_STAGE_DOTS` map（41 個 stage key 對應 dot）
- `classifyRadarStage(stages, value)` helper（依 `data-tip-value` 屬性 highlight 對應 row）
- `renderRadarStageRows()` mirror style.css 的 `.stt-stage-row` 視覺
- `entry.stages` 自動 render 為 `.rtt-stages` 區塊

**CSS** — `style.css#radar-term-tooltip`：max-width 320→360px，加 `.rtt-stages / .rtt-stage-row / .rtt-stage-active / .rtt-stage-dot / .rtt-stage-range / .rtt-stage-tag / .rtt-stage-action / .rtt-stage-detail` 全套樣式，hint 改用 dashed top border 對齊 signal-tip。

### Momentum (`page-momentum.js` + `momentum.html` 內聯 CSS)

**內容升級** — 給 8 個歧義度高的 signal/warning 加 `tiers` 陣列（3 行 scenario matrix：strong / standard / weak 對應的解讀）：

Signals: `high_short_interest`、`squeeze_candidate`、`oversold_rsi`、`macd_bullish_cross`
Warnings: `overbought_rsi`、`parabolic_blowoff_risk`、`stage4_downtrend`、（macd_bearish_cross 既存）

每個 tier 含 `{ dot, label, text }` — 例：`oversold_rsi` 在 Stage 2 + 量縮是 🟢 (健康回檔買點)，但在 Stage 3-4 是 🟠 (弱勢延續訊號，**不是機會**)。明確告訴 user「同一訊號在不同 context 下意義完全不同」。

**引擎升級** — `_renderSignalTip()` 加 `_renderTierRows()` helper，當 `entry.tiers` 存在時 render `.mpt-tiers` 區塊。

**CSS** — `momentum.html` 內聯：max-width 320→360px、加 `.mpt-tiers / .mpt-tier-row / .mpt-tier-dot / .mpt-tier-text` 樣式對齊 `#signal-tip-tooltip` 視覺，hint 改用 dashed top border。

### 風格一致性

三套 tooltip 引擎（signal-tip-tooltip / radar-term-tooltip / mom-pill-tooltip）現在視覺上幾乎不可區分：
- max-width 360px
- 12.5px bold title + 11.5px desc + 10.5px stage rows
- dashed top border for hint
- 🟢🟡🟠🔴 dot system 統一

**驗證**：`node -e new Function()` 4 檔（radar / momentum / decisions / utils）syntax 全 pass。

VERSION 1.56.2 → **1.57.0**（minor — UX consistency wave 完成）。

> 後續可選：(a) 給 radar render 補 `data-tip-value` 屬性以便 live highlight 對應 stage row；(b) 為剩下不歧義的 momentum signals 簡單加 tier 也可（fresh_golden_cross_20_50 / 50_200、stage2_uptrend_intact、volume_expansion 等）。

## 🟢 Session Note (v1.56.2) — 決策中心 risk pill 溢出卡片修補

User 反映 BE 個股分析有條 risk「FRED Overheating + Sector Rotation Avoid Technology — BE 雖歸 Industrials 但 AI Data Center 本質為高久期」溢出卡片。

**根因**：`page-decisions.js:315` `riskTag()` pill 用 `whitespace-nowrap`，搭配 `flex flex-wrap` 父容器只允許 pill 之間換行，pill **內部**長文字會直接溢出。

**附帶 bug**：原本 `replace(/\b\w/g, c => c.toUpperCase())` 在 CJK / 拉丁混合字串上會在 unicode word boundary 處強制 title case，混成奇怪的大小寫。改成 `/\b[a-zA-Z]/g` 只針對 ASCII。

**修法**：
- 移除 `whitespace-nowrap`，加 `leading-relaxed max-w-full break-words` 讓長 risk 在 pill 內自然換行。
- title case regex 限定 ASCII 字元，避免影響中文。

VERSION 1.56.1 → **1.56.2**（patch — UX bug fix）。

> ⚠ Wave 2 進行中（CSS for radar-term-tooltip 已升級，RADAR_TERMS stages content 編寫中被中斷）— 本 session 完成此 BE bug 後等下一輪指示再續做。

## 🟢 Session Note (v1.56.1) — sector pill hover 視覺修補：背景消失 → 3D 浮起

User 反映 Wave 1 後 sector 7 顆 pill hover 時「背景消失、變純文字」。

**根因**：`style.css:588` 有條全域規則 `[data-signal-tip]:hover { background-color: rgba(255,255,255,0.025); border-radius: 6px; }`，原本設計給 index 頁無背景的 verdict pill 加 hover 提示。但 sector pill 本來有 `background: var(--bg-card)` 實心卡片底色，被這條 0.025 半透明白覆蓋後反而變得「沒底」。

**修法**（sector.html 內聯 style，~12 行）：
- `.status-pill` 加 `transition`（transform/shadow/border 0.15s）。
- `.status-pill[data-signal-tip]:hover` (specificity 0,3,0 > 全域 0,2,0) 蓋過去：
  - `background: var(--bg-card)`（強制保留實心底）
  - `border-color: rgba(255,255,255,0.20)`（微亮邊框做 affordance）
  - `transform: translateY(-1px)` + `box-shadow: 0 6px 14px rgba(0,0,0,0.32)` → 3D 浮起
- light theme 同步：邊框與 shadow 改成深色變體。

VERSION 1.56.0 → **1.56.1**（patch — UX 修正）。

## 🟢 Session Note (v1.56.0) — Tooltip 升級 Wave 1：Sector page 7 顆 pill 套上「AI 裁決區風格」rich tooltip

User 反映「sector 頁面的 pill hover 看不懂」。診斷後發現：
1. **UX bug**：sector.html 7 顆 pill 用簡易 `pill-tooltip` 引擎（單行解釋），但 i18n 字典根本沒有 `breadth/ftd/regime/exposure/fg/cycle/vix` 對應條目 → fallback 顯示字面 key（"breadth"），近乎壞掉。
2. **架構限制**：index 頁的「AI 裁決區」rich tooltip engine（`signal-tip-tooltip` + `SIGNAL_TIPS`）寫在 `script.js`，只有 index 頁載入 → 其他頁面拿不到。

**Wave 1 改法**（4 檔，~440 行 diff）：
- **`utils.js`**（+475 行）：新增 IIFE `initSharedSignalTipEngine()`，整段 engine + 9 個 SIGNAL_TIPS bundles（沿用 `breadth/ftd/market_top/synth` + 新增 `regime/exposure/fg/cycle/vix`）。Live builders 涵蓋類別型訊號（regime/cycle 用 keyMap 對應 stage）與字串範圍（exposure 用 regex parse "60-75%" 取中位數）。Engine init 用 `DOMContentLoaded` guard 因為 utils.js 在 <head> 載入時 `#signal-tip-tooltip` 還不存在。
- **`script.js`**（−275 行）：刪除 lines 1083-1356 重複的 engine block（功能已搬到 utils.js）。簡易 `pill-tooltip` engine 保留（給 sector 頁的其他 risk-flag tag 用）。
- **`sector.html`**（+1 行 + 7 處改）：加 `<div id="signal-tip-tooltip">`；7 顆 pill 從 `data-tip-key="X"` 改 `data-signal-tip="X"`。
- **`page-sector.js`**（+25 行）：`renderStatusStrip` 在每顆 pill 上 setAttribute 寫入 live data 屬性（`data-regime`, `data-br-score`, `data-ftd-date` …），讓共用 engine 的 live banner 能讀到當前值並 highlight 對應 stage。

**新 5 個 SIGNAL_TIPS 內容設計**（每個含 zh+en × ~30 行）：
- `regime`：4 種 posture（RISK_ON/NEUTRAL/VOLATILE/RISK_OFF）對應的進攻/防禦操作。
- `exposure`：85+/60-85/30-60/0-30 四級 cash 比例與選股紀律。
- `fg`：Fear&Greed 5 級含逆向訊號詮釋（極度恐慌 = 🟢 buy, 極度貪婪 = 🔴 trim）。
- `cycle`：Early/Mid/Late/Distribution 4 階段對應動作。
- `vix`：< 15 / 15-20 / 20-30 / 30-40 / 40+ 五級波動環境策略。

每個 stage row 含：dot（🟢🟡🟠🔴）+ range_label + tag + action verb + detail（為何要這樣做）。

**驗證**：`node -e new Function(code)` 三檔 syntax check 全 pass：utils.js 1078 行、script.js 1082 行、page-sector.js 943 行。

VERSION 1.55.9 → **1.56.0**（minor — UX 升級 + 引擎共用化）。

> Wave 2 待批：momentum / radar 各自有自家 tip system（`data-sig-tip`, `data-warn-tip`, `data-radar-tip`），文案要重寫，user 看完 Wave 1 再決定。

## 🟢 Session Note (v1.55.9) — Dashboard 動能選股 整合 SOX：UI filter button + scan coverage 補齊

延續 v1.55.8 的 SOX universe（CLI 層），這版把它打通到 dashboard。User 反映「動能選股看不到費半」，診斷後發現兩個問題：

**A. UX bug**：Dashboard 的「Universe 範圍」filter 是 client-side post-scan filter，UI 寫死只有 All/SP500/NDX100 三鈕，沒有 SOX。
**B. Coverage bug**：Dashboard scan 跑 `screen.py --universe all` 等於 sp500 ∪ nasdaq100，30 檔 SOX 中有 9 檔（TSM, AZTA, ENTG, IPGP, ONTO, QRVO, RMBS, SLAB, WOLF）根本不在 union 內、永遠不會出現在 scan 結果。

**改法**（4 檔 ~25 行）：
- `screen.py`：CSV 多 `in_sox` 欄；`_row_from_payload` 加 `sox_set` 參數；`--universe all` 改成 `sp500 ∪ nasdaq100 ∪ sox` union（universe_desc 同步更新）；watchlist merge 條件加 `sox`。
- `bridge.py`：`_build_row` 把 `in_sox` 從 CSV 帶進 `data.json.momentum_screen.rows[]`（fallback 到 `"0"` 兼容舊 CSV）。
- `Dashboard/momentum.html`：segmented-control 加第 4 顆 `<button data-value="sox">費半 SOX</button>`。
- `Dashboard/page-momentum.js`：filter 加 `if (f.universe === 'sox' && !r.in_sox) return false;`；`isWatchlistOnly` / `isWatchlist` 都從「不在 sp500 也不在 ndx」改成「三個 reference 都不在」（避免 SOX-only ticker 如 TSM/WOLF 被誤判為 watchlist）；i18n label 加 `費半 SOX` / `PHLX SOX`。

**端到端驗證**：
- 跑 `screen.py` → CSV 第一行欄位含 `in_sox`，scan 536 tickers（含 9 SOX-only 新增）。
- `bridge.py` → `data.json.momentum_screen.rows[]` 30 列 `in_sox=true`。
- 9 個 SOX-only ticker 全部 in_sp500=False, in_nasdaq100=False, in_sox=True ✓。
- ARM(NDX+SOX)、ON(SP+SOX)、MU(SP+NDX+SOX)、RMBS(SOX-only) 4 種覆蓋情境分布正確 ✓。

VERSION 1.55.8 → **1.55.9**（patch — UI button + 1 個新欄位 + universe union 擴充，無 schema 破壞性變更）。

## 🟢 Session Note (v1.55.8) — momentum screener 加 SOX (費半) universe

User 想用短期動能掃描費半 30 檔成份股。`skills/momentum-monitor/scripts/screen.py` 已支援 universe 模式（檔名約定 `universes/{name}.txt` + 可選 `{name}_sectors.json`），純加檔即可：

- **新增** `universes/sox.txt`：30 檔 PHLX Semiconductor Index 成份（含 2 檔 ADR：TSM、ASML — user 確認要含）。
- **新增** `universes/sox_sectors.json`：30 檔 GICS sector 對應（全 Information Technology；既有 `_load_sector_map()` 會自動 merge 所有 `*_sectors.json`，無須改 loader）。
- **改** `screen.py` usage 範例 + `--universe` help 列舉 `sox`。

Smoke test：`screen._load_universe('sox')` 載入 30 檔、TSM/ASML 在內、sector map 合併後 530 entries（sp500=503 + sox 新增 27 檔不重複）。

用法：`python3 skills/momentum-monitor/scripts/screen.py --universe sox --min-score 60`。

VERSION 1.55.7 → **1.55.8**（patch — 純新增 universe，無 schema/API 變更）。

## 🟢 Session Note (v1.55.7) — 盤前檢查「更新全部過期」改 sequential queue + 修依賴順序

**症狀**：User 按 Dashboard 首頁「盤前檢查 → 更新全部過期」，confirm dialog 列出 sector + news 兩項說會跑，但切到 news.html / sector.html 兩個分頁都看不到 running banner。

**根因 1（單啟動 bug）**：`Dashboard/script.js` preflight-run-all handler 對 staleToken loop 只 POST 第一個就 `break`（comment 寫 "single-job lock — only start one"）。第二個 protocol 永遠沒被啟動，user 看到的 confirm dialog 是空頭支票。

**根因 2（依賴順序錯）**：`/api/preflight` 回傳順序剛好是 sector 先、news 後。即使修好「啟動兩個」，也會讓 sector 先跑、引用上一輪舊的 news_protocol_v2 catalysts（驗證：`sector/sector_logs/*_sector_intel.json` `top_catalysts[]` 帶 `"source": "news_protocol_v2"`）。

**改法**（單檔 ~80 行）：
- 新增 `waitForProtocolDone()` helper，輪詢 `/api/run-protocol/status` 直到非 running。
- 新增 `runPreflightQueue(items, isZh)`：sequential async loop，每輪 POST 完等 backend single-job lock 釋放再進下一輪；toast 顯示 `執行 1/2: 新聞 DIGEST（排隊中: 產業情報）`。
- 新增 `PREFLIGHT_ORDER = ['news', 'sector']` 常數，queue 強制依此排序，與 `/api/preflight` 順序解耦。
- 重用既有 `_launchPollTimer` + `pollLaunchStatus()` 維持 index 頁 launch-status banner；page-sector.js / page-news.js 自身的 resume IIFE 自動處理對應分頁的 running banner 顯示（無須改）。

**重要**：後端 `_protocol_lock`（single-job 互斥）保持不變 — lock 是正確設計，client queue 是合適的解法層級。

VERSION 1.55.6 → **1.55.7**（patch — bug fix + 依賴順序修正）。

## 🟢 Session Note (v1.55.6) — 決策日曆改 inline detail panel（取代 bottom drawer）

User 反映「點日曆任何東西都不該用 drawer 彈出，他會蓋掉下面的東西」。原本 `#cal-drawer` 是 `fixed inset-x-0 bottom-0 max-h-[70vh]`，從畫面底部滑上來，直接遮住日曆下半 + filter bar + aggregate panel，無法對照其他日期。

**改法**（option B：inline detail panel）：
- `calendar.html`：把 drawer 容器從 `<body>` 底搬進 `#cal-main` 裡，放在 `#cal-grid` 之後 / `#cal-filterbar` 之前；移掉 `fixed/inset/bottom/z-30/max-h/shadow-2xl`，改為 inline `<div id="cal-detail" class="cal-detail-panel">`。
- `page-calendar.js`：`openDrawer/closeDrawer` → `openDetailPanel/closeDetailPanel`；新增 `selectedDate` state；點被選格子再次 → toggle 收起；切月/ESC 也收起；切換 selected 時舊格 ring 移除、新格加 `cal-cell-selected`；開啟後 `scrollIntoView({block:'nearest'})` 讓 panel 自然進視野。
- `style.css`：替換 `#cal-drawer` 樣式為 `.cal-detail-panel`（max-height + opacity + translateY 摺疊動畫，dark/light 兩套底色）；新增 `.cal-cell-selected` emerald ring（與 today-cell 區分但同色系）；`#cal-drawer table` selector 改 `#cal-detail table`；`.cal-drawer-section*` class 保留（被 inline panel 重用）。

**效果**：日曆 grid 永遠 100% 在視野上，點任一格詳情長在下方、可連點不同日期比對，filter bar / aggregate panel 都不再被遮。

VERSION 1.55.5 → **1.55.6**（patch — UI 互動改善）。
