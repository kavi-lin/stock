# Session Notes 歸檔 v1.53.3 → v1.55.5（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v1.55.5) — 修短期雷達 themes 鎖在 10 個的衝突

User 反映「全部主題又變回只有十個」，疑似 skill 衝突。診斷：

**症狀**：theme-detector cache 4/25 還有 20 themes，4/26 12:17 後降到 10。下游 thematic-screener / radar 全部跟著掉。

**根因**：兩條 call path 對 `theme_detector.py` 給的 `--max-themes` 不一致：
- `daily_update.sh`: `--max-themes 25 --max-stocks-per-theme 25` (顯式)
- `sector/phase_1-2-3.md` Phase 2 (產業掃描)：沒帶 `--max-themes`，吃 default **10**

當 user 在 daily_update 跑完之後又跑「產業掃描」→ Phase 2 重觸發 theme-detector 用 default 10 → cache 從 20 降到 10 → `--skip-if-fresh 10800` 鎖住降級狀態，後面 daily_update 想恢復 25 也跳過。

**修法**：把 `theme_detector.py` 的 `--max-themes` default 從 10 → **25**（與 daily_update 對齊），`--max-stocks-per-theme` 同樣 10 → 25。再跑一次 theme-detector 重生 cache 確認 → **20 themes**（25 是上限，theme universe 實際只有 20）。

**同步改 phase_1-2-3.md**：在 Phase 2 段落加註明 default 已對齊 25，避免將來有人「以為要降回 10」。

**驗證**：theme cache 從 10 → 20。下游 thematic-screener + bridge 重跑後 data.json `tactical.themes` 應該也回到 20（pipeline 跑 ~90s 完整跑完）。

VERSION 1.55.4 → **1.55.5**（patch — config 衝突修補）。

## 🟢 Session Note (v1.55.4) — 綜合曝險 (Synthesized Ceiling) 也加 tooltip

延續同 dispatcher 模式補齊四顆 pill 的 tooltip：

**SIGNAL_TIPS.synth**：
- desc 講三訊號合成邏輯（min 規則）+ 為什麼這樣設計（衝突時偏向最保守）+ 個股實際倉位還會再乘其他乘數
- 4 stage（Aggressive 75+ / Standard 50-75 / Defensive 25-50 / Crisis < 25）
- live banner 多一行 source breakdown：`廣度 60-75% · FTD 75-100% · 頂部 80-90%`（讓 user 一眼看出是哪個訊號在拖底）
- hint：直接寫公式 `min( breadth_ceiling_mid, ftd_range_mid, market_top_budget_mid )`

**新增 CSS**：`.stt-live-sources` — JetBrains Mono 小字、灰色、縮在 live banner 底下顯示來源拆解

**新 STAGE_DOTS**：sy_aggressive / sy_standard / sy_defensive / sy_crisis（4 個）

VERSION 1.55.3 → **1.55.4**（patch — 補齊四顆 pill 的 tooltip 完整性）。

## 🟢 Session Note (v1.55.3) — Breadth + Market Top 也加 hover tooltip

延續 v1.55.2 的 FTD tooltip 風格，把另兩個 macro signal pill（市場廣度 / 頂部風險）也接同套 UX：

**重構**：把原本只支援 FTD 的 `buildFtdTipHTML` → 改成 dispatcher `buildSignalTipHTML(el, lang)`：
- `LIVE_BUILDERS` map：`{ ftd, breadth, market_top }` 各自定義 live banner 邏輯
- `renderStageRows` 抽出共用 stage list 渲染
- `STAGE_DOTS` 集中管理三組 stage key → emoji dot

**SIGNAL_TIPS 新增 2 entry**：
- `breadth` — 5 stage（Strong / Healthy / Neutral / Weakening / Critical）by score thresholds 0-100，每個 stage 都有「行動取向」action label（全力進攻 / 標準參與 / 選股降倉 / 防禦為主 / 退守 cash）
- `market_top` — 5 stage（Normal / Early Warning / Elevated / High / Top Formed）by composite_score thresholds，action label（可進攻 / 留意 / 降倉收緊 / 撤退中 / Cash 優先）

**desc 寫法刻意不對稱**：
- breadth desc 強調「現在健康嗎」+ 列出組成（200 MA / 8 MA / 突破家數 / A-D 差）
- market_top desc 強調「快崩了嗎」+ 列出組成（distribution day / leadership / defensive rotation / 新高萎縮 / R2K vs SPY）
- 並在 market_top desc 末尾加一句「與 breadth 互補」幫 user 理解兩者差異

**pill HTML**：breadth + market_top wrapper 各加 3 個 data attrs（score / zone / ceiling-or-budget），同套 hover behavior（無 cursor 變化、淡 bg highlight）

VERSION 1.55.2 → **1.55.3**（patch — UX 擴充，沿用同模式）。

## 🟢 Session Note (v1.55.2) — FTD tooltip 文案重寫（去 jargon、行動取向）

User 反饋三點：
1. 「late but valid 是啥」→ 階段名太 jargon，看不懂
2. 「不要這麼技術，加說明指標怎麼產生 + 各階段意義（可以買 / 要等 / 太晚）」
3. 「Phase 4 那個不用寫進去」+「滑鼠移上去不要變問號」

### 改動

**內部 enum rename**：`late_valid` → `standard`（涉及 script.js + investment_protocol_v4_8.md Phase 4 Step 3.5 + risk_audit schema）

**Tooltip 文案重寫**（zh / en 雙語）：
- title: `FTD · Follow-Through Day` → `FTD · 市場底部確認訊號`
- desc: 用大白話解釋 rally day 計數 + 4-7 天條件 + 為什麼越早越好（不講 O'Neil 名詞）
- 每個 stage 4 個欄位：`range_label`（day 1-5）/ `tag`（黃金期）/ `action`（可以買）/ `detail`（一句話講原因）
- 行動取向標籤：黃金期·可以買 / 主升期·仍可參與 / 補漲期·晚但仍有機會 / 過熱期·等下一輪
- 移除原本的 hint「Phase 4 Step 3.5 ...」與底部 status text（過於技術）
- 新 hint 改成 reset 條件提醒（user 上一條問過的東西）

**視覺**：
- Stage row 改成 grid 三欄（dot · range · tag · action）+ 第二行 detail 撐底
- 當前 stage 整 row 加綠色 tinted 底（`rgba(16, 185, 129, 0.08)`）+ tag 變綠
- Live banner 顯示「📅 ftd_date · 已過 N 天 · stage tag — action」
- 拿掉 `cursor: help`（user 抱怨變問號），改純 hover bg 變化作 affordance

VERSION 1.55.1 → **1.55.2**（patch — UX 文案修補）。

## 🟢 Session Note (v1.55.1) — Index 卡 FTD pill 加 hover tooltip + 解 user 「為什麼 baseline 是 4/8」

### Q&A 記錄
- **「FTD 是個股不同嗎？」** → 否，FTD 是市場級訊號（S&P 500 + NASDAQ 條件），所有股票共享同一個 ftd_date
- **「為什麼 baseline 是 4/8？」** → O'Neil 4 條件第一個全中的日子。3/31~4/2 太早；4/6 +0.44%、4/7 +0.08% 漲幅不夠；4/8 +2.51% 量增 29.6% 雙指數確認 → 鎖定
- **「4/27 後若再符合會重算嗎？」** → 否，FTD 一旦確認就鎖，只有 invalidation（跌破 swing low / 累積 6+ distribution day）或新 swing low 才會 reset

### 改動：FTD pill tooltip
原本 v1.55.0 只用 `title=""` 屬性顯示 ftd_status_text，UX 太陽春。改成跟 radar 頁同款的 hover tooltip：

- **index.html**: 加 `<div id="signal-tip-tooltip">` 容器
- **style.css**: 加 `#signal-tip-tooltip` + `.stt-title` / `.stt-desc` / `.stt-live` / `.stt-stages` / `[data-signal-tip]` (clone 自 #radar-term-tooltip 風格)
- **script.js**:
  - FTD pill wrapper 加 `data-signal-tip="ftd"` + 4 個 data attributes (state/date/day/status)
  - 新增 `initSignalTipTooltip` IIFE：包含 SIGNAL_TIPS 字典 (zh/en) + classifyStage (用 Phase 4 Step 3.5 同樣 4 階段分類) + buildFtdTipHTML + showSignalTip/hideSignalTip
  - mouseover delegate 在 document level，hover 100ms 後 show，leave 80ms 後 hide

**Tooltip 內容** (3 段)：
1. Title + 概念解釋（O'Neil + invalidation 規則）
2. Live 區：`📅 2026-04-08 · 已過 12d · Late but valid`（current stage 高亮）
3. Stage 對照：4 種階段全列出，當前 stage 加粗白色，其他灰色
4. Hint: 「Phase 4 Step 3.5 FTD timeline gate 依此 stage 套用倉位乘數」

VERSION 1.55.0 → **1.55.1**（patch — UX polish）。

## 🟢 Session Note (v1.55.0) — Investment Protocol V4.9：FTD Timeline Gate

User 看完 BUG-006 修補 + FTD 解釋後決定把 FTD timeline 接進個股決策流程。同時補上 Dashboard 顯示。

**為什麼**：FTD 是市場級訊號（不分個股），但「FTD 後第幾天進場」對 cyclical leaders 勝率影響大 — O'Neil 統計：第 1-5 天 prime window vs 第 13+ 天「補漲」失敗率約 2x。

### 三個改動

**1. bridge.py — 把 `ftd_timeline.*` 帶進 data.json**
- `extract_ftd_data` 新讀 `raw["ftd_timeline"]` → 輸出 `data.ftd.days_since_ftd` / `ftd_status_text`
- 跑了一次 `ftd_yfinance.py` 重生 cache（舊 cache 沒新欄位，自然 None）
- 驗證 data.json：`days_since_ftd=12, ftd_status_text="FTD CONFIRMED, day 12 post-confirmation (rally-day 18; FTD originally confirmed on rally-day 6)"`

**2. Dashboard `index.html` FTD pill — 露出 date + day**
- `script.js` Phase 0 macro composite pill 加一行：`2026-04-08 · day 12`（hover tooltip 顯示完整 ftd_status_text）
- 字小、放在 quality_score 下方，視覺不搶 focus

**3. invest_protocol_v4_8.md — 加 Phase 4 Step 3.5 FTD Timeline Gate（V4.9）**

Lookup 表：

| `days_since_ftd` | O'Neil 階段 | Cyclical | Defensive | 停損調整 |
|---|---|---|---|---|
| 1-5  | Prime entry | ×1.0 | ×1.0 | 標準 |
| 6-12 | Late but valid | ×0.90 | ×1.0 | 標準 |
| 13-20 | Late cycle / distribution risk | **×0.75** | ×0.95 | **-1pp（cyclical only）** |
| 21+  | FTD exhausted | **×0.50 OR REJECT** | ×0.85 | **-2pp（cyclical only）** |

Day 21+ reject 條件（cyclical only）：`RS_rating < 90 OR distance_50ma > 15%` → final_decision = REJECT。

Schema 改動：
- `risk_audit.ftd_timeline_gate` 新增 7 個 sub-field（applied / days_since_ftd / stage / sector_class / multiplier / stop_loss_adjustment_pp / rejection_triggered）
- `phase5_export_schema.md` 對應 row 加上去
- Phase 0 mtime cache 讀取必抓 `_phase0.ftd.days_since_ftd` 供 Phase 4 用
- validator 暫不加入 required（保持 backward compat，等 V4.9 session 累積夠多再啟用 hard check）

### FTD 是個股不同嗎？— ❌ 不是

回應 user 提問：FTD 是市場級訊號（S&P 500 + NASDAQ 反彈日量價條件），所有股票共享同一個 ftd_date。個股差別在「對 FTD 的反應強度」（領導股 vs 補漲股 vs 落後股），但 FTD signal 本身只有一個。

### 後續可能的延伸（暫不做）
- #2 FRED regime ticker-level multiplier
- #3 Theme exhaustion warning
- 等 V4.9 session 累積後啟用 validator hard check

VERSION 1.54.1 → **1.55.0**（minor — 新功能 + protocol 大版本 V4.8 → V4.9）。

## 🟢 Session Note (v1.54.1) — events_archive.json 持久化過去事件

User 反映「4/27 的財報，4/28 也要在 calendar 上看得到」。問題：bridge.py 每次都從 FMP/Fed/sector-protocol 重撈 forward-only feeds，過去事件就被沖掉。

**修法**：
- 新增 `events_archive.json` 持久化檔（BASE_DIR），schema：`{schema_version, updated_at, events: [...]}`
- `aggregate_upcoming_events()` 流程：
  1. Load archive（過去 + 已知未來）
  2. 撈 fresh feeds（sector-protocol + Fed + FMP econ + FMP earnings）
  3. Concat archive + fresh，按 `_event_dedupe_key` dedupe（fresh 覆蓋 archive，新資料更準）
  4. 既有 cross-category merge & 排序維持原樣
  5. **每筆 event 都重算 `within_48h`** 從當下日期判斷（archive 裡的 stale flag 自動更正）
  6. 寫回 archive（atomic `.tmp` → `os.replace`）
- `.gitignore` 加 `events_archive.json`（accumulates daily，regenerable，不該污染 commit）

**驗證**：
- 第一次跑：archive 從 0 → 61 筆（今日 + 未來）
- 手動注入過去事件 (TEST_PAST_EVENT @ 2026-04-25, within_48h=True stale) → 跑 bridge → data.json 含該筆，within_48h 自動修正為 False ✓
- 清理測試事件 → 61 筆 ✓

**檔案**：`bridge.py` (+~50 行：`EVENTS_ARCHIVE_FILE` const + `_load_events_archive` / `_save_events_archive` + 改 `aggregate_upcoming_events`) / `.gitignore` (+1 行)

**前端不用改** — calendar 已經會在過去日期 cell 渲染 chip（v1.53.4 改的 `cal-cell-events` 對 past dates 也有效），只是過去 archive 沒餵資料。

VERSION 1.54.0 → **1.54.1**（patch — bug fix 性質：原本就應該 persist 但漏了）。

## 🟢 Session Note (v1.54.0) — 決策日曆 filter bar（preset + 三維 toggle）

把 v1.53.4 的「Sources / Verdicts」靜態 legend 改成 **互動 filter bar**，新增 Events 維度：

**4 row layout**：
1. **Mode**：3 個 preset 按鈕
   - `All` — 全部開（預設）
   - `Analysis` — 只看過去決策（all sources + verdicts on，events off）
   - `Up-Event` — 只看未來事件（sources + verdicts off，all events on）
2. **Sources**：9 個來源各自 toggle（deep-dive / sector-scan / news / theme / momentum / radar / earnings / weekly / postmortem）
3. **Verdicts**：5 個判讀各自 toggle（hit / miss / neutral / pending / n/a）
4. **Events**：7 個 category（earnings / Fed/macro / econ / binary / geo / watchlist / system）

**過濾邏輯**：
- Decisions：`source ∈ activeSources AND verdict ∈ activeVerdicts`（兩維 intersect，內部 OR）
- Events：`category ∈ activeEventCats`（獨立維度）
- 任一 set 為空 → 該類別全部不顯示（這正是 preset 切換 events-only / analysis-only 的機制）

**互動**：
- 任何 pill 或 preset click → 立即 `rerenderAll()`：grid + aggregate 同步更新
- 當 filterState 與某 preset 完全一致 → 該 preset 顯示綠色 active 邊框
- 用戶手動 toggle 某個 pill 後 → preset active 自動消失

**檔案**：`calendar.html`（替換 legend block）/ `page-calendar.js`（+~150 行：filterState、applyPreset、toggleFilter、rebuildFilterBar、wireFilterBar）/ `style.css`（+~120 行：`.cal-filterbar` / `.cal-filter-pill[.is-on]` / `.cal-filter-preset[.is-active]`）

驗證：dashboard server (port 8080) 已在跑，refresh `http://localhost:8080/calendar.html`，預設應看到所有 pill 綠色 on，All preset active；點任一 pill 立即看到 calendar grid 對應日期的 chip 消失/出現。

## 🟢 Session Note (v1.53.4) — 決策日曆 events 內聯到儲存格

User 反映 FMP 整合後 `upcoming_events` 暴增到 61 筆 / 12 dates（最高一天 19 筆），右側「即將發生」rail 太長。

**處理**：
- 把 events 用 **category-grouped chip** 形式塞回每格儲存格底部，與決策指標 (`cal-badge-row`) **分行**：
  - 每格按 category 群組，顯示 icon + count（例：💼3 📊5 ⚠1）
  - binary / high impact 用紅 / 黃 tinted 樣式凸顯
  - 最多顯示 4 種 category，超過 +N 收尾
  - hover 顯示完整 title list（含 ticker prefix）
- 右側 rail panel `cal-upcoming-rail` 加 `hidden` class（保留 DOM 與 `renderUpcoming()` 不刪，未來要恢復改一個 class toggle 就好）
- `cal-main` grid 從 `lg:grid-cols-[1fr_280px]` 改成單欄全寬
- Drawer 點擊任一格時，事件 section 渲染在 decisions section **之前**（重用 `renderUpcomingCard()` 不重寫）
- CSS 新增 `.cal-cell-events` (`margin-top: auto` 推到底部) + `.cal-cell-event-chip` 三色變體 (`-high` / `-binary` / 預設)

**檔案**：`page-calendar.js` (+~80 行) / `calendar.html` (2 處小改) / `style.css` (+~60 行新樣式)

驗證方式：dashboard_server (port 8080) 已在跑，refresh `http://localhost:8080/calendar.html` 即可看到新 layout。

## 🟢 Session Note (v1.53.3) — ARCHITECTURE_DIAGRAM.md 重寫為 4 視角

原本一張平鋪 5 層 DAG，user 反映「mermaid 不太好懂、call stack 看不出時序」。重寫成 4 個視角各解一個問題：

- **A. 系統地圖**：保留 flowchart 但加 subgraph 分層 + 觸發點顏色標記（藍=自動 / 綠=用戶 protocol / 橘=手動工具）+ 粗線 / 虛線 / 細線區分觸發鏈、Skill 呼叫、cache 寫入。
- **B. Tier 1 daily pipeline 時序**：sequenceDiagram 顯示 Step 1-6 的順序、寫哪個 cache、bridge 怎麼吃進去。
- **C. Tier 2 三大 protocol call stack**（Sector V1.4 / Investment V4.8 / News V2.1）：sequenceDiagram 顯示 Phase 順序 + subagent 平行 fan-out（`par`/`and` block）+ 各 phase 讀寫的檔案 + 關鍵紀律。
- **D. Bridge 聚合表 + Cache 目錄樹 + Skill 依賴表**：解「data.json 某欄位是哪來的」、「某個 cache 在哪」、「哪些 skill 在哪個 phase 平行/序列」。

加碼：失敗診斷小抄（症狀 → 先看哪），把 BUG-002 atomic write、BUG-006 ftd_status_text 等紀律寫進來，下次出問題能快速定位。

454 行（從 103 行擴 4×）。
