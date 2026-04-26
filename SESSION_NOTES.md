# INTEL COMMAND — Session Notes & System State

> **Last Updated**: 2026-04-26
> **Role**: This file serves as the "Short-term Memory" and "Handoff Cache" for AI Agents. It contains market regime states, token optimization logs, and data integrity notes. **Task backlog has been moved to TODO.md; full version history to CHANGELOG.md.**



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



## 🟢 Session Note (v1.53.2) — BUG-006 修補 + FRED fetch.py None 比較 fix

**兩個 bug，當天解：**

### 1. `skills/fred-macro/scripts/fetch.py:1054` TypeError
`hy_pct = rs.get("credit_spread_pctile_1y", 50)` 在 key 存在但值為 `None` 時 `dict.get` 不會回 default，導致 `hy_pct > 45` 比較炸掉。改成 `rs.get(...) or 50`。`daily_update.sh` Step 4 解鎖。

### 2. BUG-006 — sector_protocol FTD day-counter 幻覺
Gemini 報「4/22 報告抄 4/21 範本，忽略 breadth 36.8 → 42.4」。實際根因不一樣：
- Breadth 4/21=42.4 / 4/22=42.4 是因 TraderMonty CSV 上游早上沒更新（晚上才有 4/21 收盤），不是 AI 抄。
- 真正幻覺：4/21 報告寫 "FTD Day 14"，4/22 寫 "FTD day 6" — 兩天 AI 抓 ftd_cache 不同欄位（`current_day_count` vs `quality_score.breakdown.base "Day 6 FTD"`）。

**修法 V1.5 schema bump**：
- `sector/ftd_yfinance.py` 加 `ftd_timeline` block（含 `ftd_status_text` canonical 字串 + `days_since_ftd` / `rally_day_count` / `ftd_day_number` 三個明確 day-counter + `_help` 註解）
- `sector/phase_0.md` 層 C 加反幻覺規則（必引用 `ftd_status_text` 原文）
- `sector/schema.md` Phase 0 / Phase 5 ftd block 補新欄位

**驗證輸出（4/26 跑）**：
```
FTD Timeline: FTD CONFIRMED, day 12 post-confirmation (rally-day 18; FTD originally confirmed on rally-day 6)
```
ftd_date 4/8 + 12 trading days = 4/24 ✓；rally_low 3/31 + 18 trading days = 4/24 ✓

**後續觀察**：4/27 跑 sector_protocol 時看 AI 是否引用新 `ftd_status_text` 原文；如果還寫成「FTD Day N」要再強化 phase_4-5.md 內的 prompt 引用語法。



## 🟢 Session Note (v1.53.0) — News Driver v0.2.1（兌現 Finnhub /company-news + sentiment）

從 v1.46-v1.52 的 News driver 一直是 v0.1 volume/gap proxy（雖然 SKILL.md / global_warnings 一直寫「v0.2 will integrate Finnhub」）。User 提醒後實作。

**Method 4 個方案評估**：
1. Pure keyword（粗糙）
2. Keyword + magnitude + negation（finance-tuned，0 cost）— 採用
3. Finnhub `/news-sentiment` endpoint — 測試 **403 premium-only 不能用**
4. LLM scoring — $1-2/day cost，先不上

**v0.2 第一版實作後 5-ticker test 找到 5 critical bug**：
- NVDA 248 articles 多數 tangentially-related 噪音（"Walmart's investment in Mexico" 被當 NVDA news）
- 問句被當 sentiment claim（"Is X a Buy?" → +0.5）
- "Lockheed Martin Shares Are Falling" 沒抓到（"falling" 不在詞庫）
- "Insiders Sold Suggesting Hesitancy" 沒抓到
- 248 articles 全平均 → 訊號被噪音稀釋

**v0.2.1 修正**：
1. **Headline relevance filter**：Finnhub profile 抓 company short name → 標題沒有 ticker 也沒 short name → 過濾
2. **問句 ×0.5**：標題含 `?` 或 `Is/Why/Should/Will/Can` 開頭 → score halved
3. **Cap top 20 by recency**
4. **+25 個新詞彙**：falling/hesitancy/flopped/buyback/dividend cut/sluggish 等
5. **Source blacklist**：simplywall.st / fool.com / zacks.com

**測試結果（v0.2 → v0.2.1）**：
| Ticker | v0.2 | v0.2.1 | 變化 |
|---|---|---|---|
| NVDA | 248→+0.152 | 20 of 249→+0.250 | 噪音砍 92% |
| LMT | 47→-0.011 | 20 of 92→-0.045 | 抓到 Q1 miss |
| LLY | 36→+0.033 | 10 of 49→**-0.055** | **翻轉成負**（GLP-1 壓力） |
| JPM | 42→+0.031 | 1 of 52→-0.040 | 41 篇 commentary noise 砍 |

**Fallback 設計**：Finnhub 失敗或無相關文章 → 降回 v0.1 proxy + warning 標明

**整合**：predict.py 主流程自動用 v0.2.1（清 cache 後第一輪 fresh prediction 都用新算法）。daily_update.sh thematic-screener 跑時自動生效。

**已知殘留小 bug**（v0.2.2 修）：
- "Why X Flopped" 顯示 +0.25 應 -0.25（summary 某詞蓋過 — 待 trace）
- 動詞變化漏：slips / lag / lags 詞庫沒有

## 🟢 Session Note (v1.52.0) — Radar v0.4: ETF holdings universe + auto-refresh

修正 user 點出來的兩個 fundamental issue：(1) static_stocks 只有手選 10 個 → universe 太窄、(2) 「top 5」semantic 錯（top 5 of 10 不是 top 5 of universe）。

### 核心改動：ETF holdings 取代手選 universe

**之前**：每主題 themes.yaml 寫死 10 個我手挑的 static_stocks
**現在**：每主題的 proxy_etfs (e.g. SOXX/QTUM/BOTZ) 抓 yfinance top 10 holdings → 跨 ETF dedup → 過濾非美股 → cap 25 → 寫進 themes.yaml

結果：
- 270+ 個 unique US-tradeable tickers（vs 之前 171）
- 17 主題從 10 → 16-25 stocks
- 4 主題真實 universe 小（保留 5-12）：Gold, Uranium, Real Estate, Utilities Defensive
- Quantum 17 stocks，**重疊 0** vs 我手選名單 → 證明 ETF 比手選代表性高

### 新增基礎設施

- **`skills/thematic-screener/scripts/refresh_etf_holdings.py`**（150 行）：完全自動化 — 用 yfinance 抓 ETF top holdings、dedup、過濾非美股、寫回 themes.yaml + bump etf_meta.yaml `last_refreshed` timestamp
- **`skills/thematic-screener/etf_meta.yaml`**：紀錄 last_refreshed + summary stats
- **`daily_update.sh` Step 5.5**：每天檢查 etf_meta，60 天內 fresh 顯示 ✅，60-90 天黃色提示，**90 天自動觸發 refresh + 同步重跑 theme-detector**

### Refresh 自動化頻率（per user 確認）

90 天自動 refresh 對應 ETF rebalance 季度週期。ARK 系列雖可日動但 top 25 一季內幅度<5 個是常態 → 90d 是合理 cadence。
**完全本地、0 token 成本**（yfinance 免費 + Python 腳本，不調 LLM）。

### 真實 breadth 結果驗證

```
AI & Semiconductors             N=22  95% bullish (21/22) — 真強勢
Financial Services & Banks      N=25  80→84→88% — 漸強
Defense & Aerospace             N=18  33→38→44% — 短空長中性
Oil & Gas (Energy)              N=25  32→36→36% — 失寵
Utilities Defensive             N=12  41→50→50% — 中性偏空
```

對比 v0.3：之前 top-5 預先 selection → 多數主題假性 100% bullish。現在跨 universe 平均，breadth 真實反映「主題內多少股看多」。

### 工作流程
- **每天**：daily_update.sh 自動跑 → etf_meta < 60d 顯示綠燈、< 90d 黃燈、≥ 90d 自動 refresh
- **使用者 0 維護**：完全 set-and-forget；季度自動 refresh
- **Manual override**：`python3 skills/thematic-screener/scripts/refresh_etf_holdings.py --top-n 25` 隨時可跑

### 延後的事
- **primary_theme tagging（解重複）**：原 plan 的 step 5 還沒做。NVDA 仍同時在 AI/Quantum/Robotics 都算。等使用 1-2 週看是否 visually 困擾再決定要不要做
- **動態 ETF API**：v0.5 才考慮（手動 quarterly refresh 已夠用）

## 🟢 Session Note (v1.51.0) — Radar v0.3 horizon switcher + breadth 算法修正

兩個 user feedback 觸發的 critical 修正：

### 1. Breadth 算法 bug 修正（嚴重）
**之前**：bullish_breadth_pct 是基於「top 5 movers」算的 → 都被 ranked by score×conv 預先 selected → 必然 100% bullish 大概率 → metric 失去意義
**修正**：改成對主題的**全部 representative_stocks (10 名)** 算 breadth → 得到真實「主題內多少股看多」

修正後例：
- Defense & Aerospace: 1d 10% (1/10) → 5d 20% (2/10) → 15d 30% (3/10) — **真實短空長多 pattern**
- Robotics: 100% (9/9) all horizons — 真強勢
- Cybersecurity: 66% → 77% → 88% — 漸強
- Cloud: 40% → 50% → 50% — 混雜
- Obesity & GLP-1: 22% → 33% → 44% — 短期偏空

### 2. 1d/5d/15d Horizon Switcher
- screen.py `compute_theme_short_term` 重寫：回傳 `{n_total_constituents, primary_horizon, by_horizon: {1d/5d/15d: {bullish_breadth_pct, avg_conviction, n_valid_predictions, n_bullish, mean_target_pct}}, components}`
- page-radar.js 加 `_currentHorizon` state + 3 個 button (1d / 5d ★ / 15d)
- Theme card 顯示「SHORT bull [5d] 80% (8/10)」格式 — 含當前 horizon 標示 + bullish/valid 計數
- 切換 horizon 自動重排 + 重 render

### 3. 額外 polish（同輪）
- Tooltip CSS 改用 theme variables (`var(--bg-card)`、`var(--text-main)`、`var(--secondary)` 等) → light/dark 自適應
- Cursor 從 `cursor: help` 改 `inherit`（不再變問號游標）
- Theme card 多顯示「constituents: N」讓 user 知道分母是多少

**Output schema 變化**（v0.3 vs v0.2）：
- `short_term.bullish_breadth_pct` → `short_term.by_horizon.<h>.bullish_breadth_pct`
- 加入 `n_total_constituents`、`n_valid_predictions`、`n_bullish` 透明化分母

**plan_short.md 全進度**（**整套 v0.3 production**）：
- Step 1-7 ✅ + 文件 ✅ + Step 4 v0.1 dual-section ✅ + v0.2 all-themes-grid ✅ + **v0.3 horizon switcher + breadth 修正 ✅ v1.51.0**

## 🟢 Session Note (v1.50.0) — Tactical Radar v0.2 重設計（all themes grid + regime layer + predict cache）

User feedback「不直覺」+「想看全部主題 + 點開 movers」+「regime 是市場主導力」的 3 個訴求一次落地。

**結構性重設計**：
1. **Theme runtime sync**（修我之前 Step 2 的 bug）：themes.yaml + default_theme_config.py 同步加 5 個新主題（Nuclear Energy / Uranium / Space Economy / Quantum Computing / Robotics & Automation / Utilities Defensive / Obesity & GLP-1），15 → 21 themes
2. **Theme-detector 重跑**：max-themes 25 → 偵測到 20 主題（含 5 個新加 + 4 auto-discovered sector concentration）
3. **predict.py 加 4h cache**：cache hit 1.7s → 0.4s。171 unique tickers 全跑也只需單次（之後 4h 內全 hit）
4. **screen.py v0.2 重寫**：
   - 移除 top_themes 限制 → **顯示全部 20 主題**
   - 每主題加 short_term { bullish_breadth_pct, avg_conviction, components }
   - 加 regime layer：2 獨立 badges (RSI + VIX) + factor (取 max 偏離度)
   - regime factor 自動 dampen bullish_breadth (今天 0.9× 因為 SPY RSI 87)
   - 排序預設 by short bullish_breadth_pct desc
   - 同時收集 components 欄位給 v0.2 後續用
5. **radar.html v0.2**：grid 6 cols + sort toggle (Short/Mid) + regime badges 區 + expanded movers panel
6. **page-radar.js v0.2**：~360 行重寫，theme grid 點擊展開單一主題 movers，sort 即時切換，badges 中英雙語

**Regime layer 設計**（per user 確認 2 badges + 1 factor）：
- RSI > 85 → 「極端超買 — mean reversion 風險」(factor 0.90)
- RSI < 25 → 「極端超賣 — 反彈燃料」(factor 1.10)
- VIX > 25 → 「緊張 — caution」(factor 0.92)
- VIX > 35 → 「恐慌 — 防禦」(factor 0.85)
- VIX > 40 → 「投降底 — contrarian buy」(factor 1.15)
- 取「max 偏離度」當 factor，不 double-count

**今天實際狀態**（驗證 4 象限）：SPY RSI 87.4 + VIX 18.7 → 「**複雜頂**」象限
- ✅ RSI badge fired: "SPY RSI 87.4 極端超買"
- 🟢 VIX badge silent (VIX 18.7 沒進極端區)
- 數字 factor: 0.90 (rsi_87_overbought)

**Bridge 注入結構**：data.tactical.{themes[20], regime_snapshot, regime_badges, regime_factor, screener_params}

**設計分區決定的修正**：
- 之前 Step 4 的「2 分區強迫看」改成「1 grid + click 展開」(per user 不直覺反饋)
- Movers 不再預設展開，使用者主動點才看詳細
- Cool 主題 (mid_heat < 30) 透明度 0.7 區分但不隱藏（per user「全部顯示」訴求）

**plan_short.md 全進度**：
- Step 1-7 ✅ + 文件刷新 ✅ + Step 4 v1（雙分區）✅ → **v0.2 全 grid 重設計 ✅ v1.50.0**

整套 Tactical Opportunity Radar v0.2 production-ready。

## 🟢 Session Note (v1.49.0) — plan_short Step 4 完成（Dashboard「短期雷達」頁）

落地 Tactical Opportunity Radar 的視覺化層。**plan_short.md 全部 7 個 Step 完成**。

**架構決策**：
- 走方案 B：**新頁面 `radar.html`**（不擴充 momentum）— sidebar 加「短期雷達」icon=radar
- 走方案 A 資料流：**`bridge.py` 注入 `data.tactical` sub-key**（單一 fetch，不破壞既有 data.json 模型）
- 桌面 only，預設展開第 1 個主題卡

**完成檔案**：
- `bridge.py` +35 行：`load_tactical_recommendations()` + 注入 `data["tactical"]` + import time
- `Dashboard/utils.js`：NAV_ITEMS 加 radar entry
- `Dashboard/i18n.js`：zh/en nav.radar + 完整 radar 頁面字串（~40 entries × 2 langs）
- `Dashboard/style.css` +120 行：experimental-badge / regime-banner / heat-bar / horizon-bar / driver-row / invalidation-box / concentration-warning / confidence-breakdown 等 radar 專屬類別
- `Dashboard/radar.html`（85 行 NEW）：頁面骨架 — header + EXPERIMENTAL badge + regime banner + section A (主題卡) + section B (movers)
- `Dashboard/page-radar.js`（260 行 NEW）：render 邏輯 — 嚴格遵守 plan_short §11.D 顯示規則（range / confidence / drivers / invalidation / concentration / trading_meta 全顯示）

**§11.D 顯示規則檢核**（強制）：
- ✅ EXPERIMENTAL badge（橘色，header 內）
- ✅ Range（每個 horizon 都顯示 $low – $high，不只 mid 點）
- ✅ Confidence + breakdown（collapsible，7 contributors 展開）
- ✅ Drivers（4 sources：news / sector / momentum / atr）
- ✅ Invalidation box（紅色左 border）
- ✅ Concentration warning（橘色左 border，列出 co-recs）
- ✅ Trading meta（stop / pos% / tx / exit trigger）
- ✅ FRED regime banner（頂部，含 SPY/RSI/VIX/yield curve/credit spread）
- ✅ 累積天數提示（header）+ KPI gate hint

**Smoke test**：
- node syntax 通過
- HTML id 全 18 個 ✓ 對應 JS reference
- bridge.py 注入成功：`tactical.status: success / 3 themes / 9 movers`
- Dashboard server 已在跑（pgrep 確認）

**plan_short.md 全進度**：
- Step 1 short-term-target ✅ v1.46.0
- Step 2 4 themes ✅ v1.46.1
- Step 3 thematic-screener ✅ v1.47.0
- Step 5 outcome log（Step 3 內含）✅ v1.47.0
- Step 6 daily_update.sh 整合 ✅ v1.48.0
- Step 7 weekly_review.py ✅ v1.48.0
- 文件刷新 ✅ v1.48.1
- **Step 4 Dashboard「短期雷達」 ✅ v1.49.0 ← 全 plan 收尾**

整個 Tactical Opportunity Radar v0.1 系統 production-ready。

## 🟢 Session Note (v1.48.1) — 文件刷新（README.md + CLAUDE.md）

把短期戰術層的整套變更**反映到使用者日常文件**。

### README.md 改動
- **頂部**：新增「三層時間維度設計」說明（長期/中期/短期）
- **常用指令表**：加 description 欄位、補 `動能 [TICKER]`
- **每日工作流程**：從原本 4 step 重寫成 **Tier 1/2/3/4 結構**：
  - Tier 1 自動：daily_update.sh 6 step（含新 Step 6 thematic-screener）
  - Tier 2 每日手動：開 Dashboard / 看 recommendations / 視需求做深度分析
  - Tier 3 每週末手動：weekly_review.py
  - Tier 4 不定期：分析、產業掃描、dual_fetch、postmortem 等
- **腳本用途速查（新增）**：4 個分類 × 共 ~20 個 .py 一覽，每個含「用途」「觸發」
- **Tactical Opportunity Radar 章節（新增）**：架構圖 + 與既有系統關係表 + KPI gate

### CLAUDE.md 改動
- **Protocol Triggers 表**：標註 V4.8.1 dual_fetch + 各 protocol 內容
- **新增「Tactical Opportunity Radar」section**：說明戰術層自動產出位置 + 紀律「不影響 protocol 決策、永不自動覆寫 config」
- **Ops Shortcuts**：從單行擴成 4 個常用指令（含 weekly_review、predict、dual_fetch、audit_drift_check、backtest_postmortem）

### 今日完整 plan_short 進度
- Step 1 short-term-target ✅ v1.46.0
- Step 2 4 themes ✅ v1.46.1
- Step 3 thematic-screener ✅ v1.47.0
- Step 5 outcome log（Step 3 內含）✅ v1.47.0
- Step 6 daily_update 整合 ✅ v1.48.0
- Step 7 weekly_review.py ✅ v1.48.0
- **文件刷新 ✅ v1.48.1**
- Step 4 Dashboard ⏳ 唯一剩下

## 🟢 Session Note (v1.48.0) — plan_short Step 6 + Step 7（自動化 + 週末校準工具）

把每日推薦生成自動化 (Step 6) 並建立每週手動校準工具 (Step 7)。**day-1 logging 機制現在每天會自動運轉**。

### Step 6 — `daily_update.sh` 加入 thematic-screener
新增第 6 步驟：
- 檢查 `theme-detector` cache 存在性 + 新鮮度（> 7 天 → 跳過警示，不報錯）
- 用 `set +e` 包覆 thematic-screener 執行，**失敗不中止整體 daily flow**
- 顯示輸出檔大小確認成功
- 加提示「每週末跑 weekly_review.py」

### Step 7 — `skills/short-term-target/scripts/weekly_review.py`（330 行）

每週末手動跑，**不自動覆寫任何 config**。輸出 `reports/SHORT_TERM_WEEKLY_<DATE>.md` 含：
1. **Per-horizon 統計**：1d / 5d / 15d 各別 hit rate / in-range / mean error / directional bias
2. **Per-theme 5d alpha 分解**：哪個主題的推薦最準 / 最不準
3. **Worst 5 cases**：最大絕對誤差案例 + driver 細節
4. **Suggested adjustments**：基於 hit rate 與 bias 的具體建議（reduce α/γ 等）
5. **KPI gate**：對照 plan_short §6 + §12.H 的失敗判定（hit rate < 50% AND mean alpha < 0% on N≥30 → 整套退役）

**重要紀律**：Tool 只給建議，**完全由使用者決定**要不要 edit `config/weights.yaml`。每次調整需手動 bump `weights_version`，未來預測自動 tag 版本，可做 before/after 比較。

### Smoke test
- `daily_update.sh` syntax check 通過
- `weekly_review.py` 跑通：找到 1 個 recommendations file（今天的），0 預測達到 evaluation window（horizons 都還沒到期）→ 正確顯示 "No outcomes available" graceful message

### plan_short.md 進度
- Step 1（short-term-target）✅ v1.46.0
- Step 2（4 themes）✅ v1.46.1
- Step 3（thematic-screener）✅ v1.47.0
- Step 5（outcome log）✅ v1.47.0（內含於 Step 3）
- **Step 6（daily_update 整合）✅ v1.48.0**
- **Step 7（weekly_review tool）✅ v1.48.0**
- Step 4（Dashboard）⏳ 唯一剩下

### 系統現狀（每天運轉中）

```
每天 daily_update.sh:
  Step 1-5 (廣度/FTD/Top/FRED/bridge) — 既有
  Step 6 thematic-screener → data/recommendations/<DATE>.json — 新增

每週末手動:
  python3 skills/short-term-target/scripts/weekly_review.py
  → reports/SHORT_TERM_WEEKLY_<DATE>.md
  → user 決定是否 edit weights.yaml + bump weights_version
```

從今天起，每跑一次 daily_update.sh 就累積一筆推薦樣本。**約 7-10 天後 1d/5d 就有可評估資料；3-4 週後達到 N≥30 KPI gate 門檻**。

## 🟢 Session Note (v1.47.0) — thematic-screener skill v0.1（plan_short Step 3 + Step 5 內含）

新增 `skills/thematic-screener/` — Tactical Opportunity Radar 的聚合層，把 theme-detector（中期主題熱度）與 short-term-target（1d/5d/15d 個股預測）串成每日推薦輸出。

**架構決策**：
- **Subprocess 呼叫 short-term-target**（不 import） — 保持 skill 獨立性。N×M tickers × ~5-15s/call 是可接受的日 cadence
- **Theme-detector 已提供 `representative_stocks` per theme** — 不需 parse cross_sector_themes.md
- **Concentration 是 WARNING 不是 REMOVE**（per §11.B 修正）— 同主題 ≥2 picks → 加 flag 但都保留，使用者決定
- **無 FRED → theme scoring**（per §12.E 硬版拒絕）— 只記錄 FRED 狀態到 regime_snapshot
- **Day-1 outcome log 寫入機制**（per Step 5）— 每次 run 寫 `data/recommendations/<DATE>.json`，含完整 regime context (SPY/RSI/MA50/VIX/FRED)，未來 Step 7 weekly_review 可直接 cross-tab

**完成檔案**：
- `scripts/screen.py`（230 行）— 主聚合腳本
- `SKILL.md` / `README.md` / `CHANGELOG.md`
- `data/recommendations/.gitignore` + `cache/.gitignore`

**Smoke test**（2x2 = 4 calls，~30s）：
- ✅ theme-detector cache 載入正確
- ✅ Top 5 themes 排序正確（Clean Energy 67.4 / Defense 66.0 / Materials 64.3）
- ✅ short-term-target subprocess 對每個 ticker 回傳完整 JSON
- ✅ concentration_flag 觸發正確（同主題 2 picks → 都標警示）
- ✅ regime_snapshot 完整（SPY=713.94 RSI=87.4 VIX=18.71 FRED=expansion）

**真實 run**（3x3 = 9 calls，~90s）：成功寫入 60KB recommendations log

**plan_short.md 進度**：
- Step 1（short-term-target）✅ v1.46.0
- Step 2（4 themes）✅ v1.46.1
- **Step 3（thematic-screener，含 Step 5 log writer）✅ v1.47.0**
- Step 4（Dashboard 兩分區）⏳
- Step 6（daily_update.sh 整合）⏳
- Step 7（weekly_review.py）⏳

**值得注意**：今天 SPY RSI 87.4 是極端區。所有今日推薦的 regime context 都記錄了這個事實，未來 backtest 可以分析「在 SPY RSI > 80 時，模型表現如何」這類問題。

**設計亮點 — Day-1 logging 已運轉**：
從這一刻起，每次 thematic-screener 執行（手動或未來 daily_update.sh 自動）都會留下完整的「當下推薦 + 當下市場狀態」紀錄。3-4 週後就有 N≥30 樣本可供 Step 7 weekly_review 評估。**這比「先做 7 個 step 再驗證」省 3-4 週**。

## 🟢 Session Note (v1.46.1) — plan_short Step 2 完成（4 個新主題）

`cross_sector_themes.md` 17 → **21 主題**。實作前盤點發現原計畫的 6 個新主題實際只該加 4 個：
- **Nuclear Energy 已存在**（既有第 15 主題，含 CCJ/CEG/VST/OKLO 等）→ skip
- **Healthcare Defensive 與既有 Healthcare & Pharma 重複**（UNH/JNJ/LLY/PFE 已涵蓋）→ skip

**新增主題**：
- **Space Economy**（從 Defense 拆 RKLB；ROKT/ARKX/UFO ETFs；14 名）
- **Quantum Computing**（IONQ/RGTI/QBTS/QUBT pure-plays + IBM/GOOGL/MSFT/NVDA mega-cap dilution；11 名；標明 pure-plays ATR ~8%）
- **Robotics & Automation**（ISRG/TER/ONTO/ABBN/FANUY/ROK；BOTZ/ROBO/IRBO/ARKQ ETFs；15 名）
- **Utilities Defensive**（NEE/DUK/SO/AEP/XEL；XLU/IDU/VPU/FUTY；15 名；明示與 Nuclear Energy 區別 — Nuclear 是 offense，這個是 defense）

**附帶調整**：
- Defense & Aerospace 移除 RKLB（補 TXT），ETFs 從 4 → 2（ROKT/ARKX 移到 Space）
- Overlap Matrix 加 8 行（含 BWXT 三重歸屬：Defense + Nuclear + Space 都正確）
- Summary Table N=21

**plan_short.md 進度**：
- Step 1（short-term-target）✅ v1.46.0
- Step 2（4 themes）✅ v1.46.1
- Step 3-7 ⏳

## 🟢 Session Note (v1.46.0) — short-term-target skill v0.1（plan_short Step 1）

承接從 backtest 反思 + Gemini/ChatGPT 雙 review 整合的 plan_short.md，落地 Step 1：建立 `skills/short-term-target/` skill 提供 1d/5d/15d 短期目標價預測（"Tactical Opportunity Radar" framework）。

**架構決策（從 plan_short 帶入）**：
- 每 horizon 獨立權重（1d news-heavy、5d momentum-heavy、15d sector-persistence-heavy），不共用 α/β/γ
- Hard clamp（1d ±5%、5d ±15%、15d ±30%）防冷啟動爆走，clamped 預測 confidence 自動 -0.15
- Confidence breakdown 7 項貢獻全透明，sum 等於 final
- Benchmark-relative output（ETF realized + implied_alpha），預設 SPY
- Refuses to fabricate：source 過舊 → `status: insufficient_data` 含 missing/would_need
- Trading meta（stop = 1.5×ATR、pos% = 0.33/ATR%、tx_cost、exit_trigger）
- weights.yaml 手動編輯，每次調整 bump weights_version（搭配未來 Step 7 weekly_review）

**完成**：
- `skills/short-term-target/scripts/predict.py`（385 行）— 主腳本含全部上述規則
- `skills/short-term-target/config/weights.yaml`— 可手動編輯參數
- `skills/short-term-target/SKILL.md`— 形式 spec
- `skills/short-term-target/README.md`— 使用 + 詮釋指引
- `skills/short-term-target/CHANGELOG.md`— v0.1.0 紀錄含 smoke test 結果
- `cache/`、`data/` 目錄含 .gitignore

**Smoke test（3 ticker，全通過）**：
- AMD（Stage 2 + 量增）：1d conf 0.59、5d target +3.28%、News 抓到 +13.9% gap
- CEG（低波動 utility）：1d conf 0.61、5d +1.52%、預測平緩
- IONQ（高波動 quantum，ATR 8.18%）：1d conf 0.17、15d conf 0.03（"沒意見"）— 高 ATR 自動降信心驗證 OK

**plan_short.md 進度**：
- Step 1（short-term-target）✅ 完成（v1.46.0）
- Step 2（4-6 個新主題到 cross_sector_themes.md）⏳
- Step 3（thematic-screener skill）⏳
- Step 4（Dashboard 兩分區）⏳
- Step 5（outcome tracking log）⏳
- Step 6（daily_update.sh 整合）⏳
- Step 7（weekly_review.py 手動 recalibration tool）⏳

**v0.1 已知限制**（README 已詳載）：
- News driver 是 volume/gap proxy，非真實 Finnhub /company-news（v0.2 升級）
- GICS sub-industry lookup 未做，benchmark 全部 default SPY
- 沒做 cache layer，每次 hit yfinance
- dual_fetch consumption 是 best-effort（read 不到不報錯）
- 未做 outcome 驗證（從 day 1 累積 + Step 7 評估）

**設計帶入的 backtest lessons**：
- News lane r=+0.373 的發現 → 1d horizon 給 news 0.6 最高權重
- 高 ATR 在 backtest 中是 outcome 變異最大來源 → 直接做進 confidence penalty
- 「不要在 1 個 regime 上過擬合」 → 整套設計接受失靈 + Step 7 手動 recalibration（user 拍板）

## 🟢 Session Note (v1.45.0) — Investment Protocol V4.8.1 Dual-Fetch 整合

把 v1.44 的 dual_fetch 接進 `investment_protocol_v4_8.md`。設計討論時排除了兩個明顯路線（Phase 1 加 subagent 做判斷 / 4 個 Phase 2 subagent 各自 call dual_fetch），採第三路：**PM inline 一次抓、4 個 subagent 共享 snapshot**。理由：(1) 同 session 同 snapshot，cross-lane 資料一致；(2) 不增 subagent，Phase 1 維持輕量；(3) `_audit.*` 隔離紀律集中守在 PM 一處 paste 動作。

**完成**：
- **`investment_protocol_v4_8.md` Phase 1**：新增「Phase 1 資料層 (V4.8.1)」段落，PM MUST 執行 `run_dual_fetch.sh`、讀取 `bundle["scoring"]`、絕對禁止讀寫 `_audit.*`（違反→當前 ticker 作廢、重啟 Phase 1）
- **Phase 2 共通 prompt 模板**：在 PHASE 0 MACRO CONTEXT 之後插入 `TICKER DATA BUNDLE` 段落（與 macro 同樣 read-only / shared-across-analysts 的 pattern）
- **Fundamentals subagent rubric**：新增 9 scalar 使用規則。重點：
  - bundle 為 9 欄位權威來源；與 us-stock-analysis 衝突 > 1% 採 bundle 並註記原因
  - `priceToBookRatio` 視為近似值，估值權重低於 P/E（已知跨 provider 10-30% 差）
  - `dividendYield` 單位 = percent / indicated annual（前瞻）
  - bundle 缺欄位 → 用 us-stock-analysis 補；皆無 → 排除於評分，不得猜
- **`investment/README.md`**：開頭新增 V4.8.1 增量變更段落
- **失敗模式**：FMP audit 失敗（quota / 401 / 403）不算失敗，scoring 仍完整；只有 Finnhub 全失敗才標 `data_bundle_available: false`，subagent 走 fallback

**未做（暫不動）**：
- 不修改 `us-stock-analysis` skill 內部 fetch 邏輯（仍會自己抓 FMP）。當前 bundle + skill 雙抓共存，由 subagent 在 prompt 規則裡仲裁衝突。未來可優化為 skill 接受 `--data-bundle` 參數跳過自抓
- 其他 3 個 lane（Sentiment / News / Technical）資料需求與 bundle 9 個 scalar 不重疊，本次不變更
- 未跑端到端 protocol 測試（需要使用者實際 `分析 [TICKER]` 才能驗證 PM inline 是否正確執行 dual_fetch）

## 🟢 Session Note (v1.44.0) — Finnhub Dual-Fetch + Audit Drift Monitor

承接 v1.43 的 diff 結果，把「驗證工具」升級成「常態雙抓 + 物理隔離」。先用 diff_tool 跑出 FMP stable 端點問題（v3 全 403、QQQ 402、`key-metrics-ttm` 欄位搬到 `ratios-ttm`、`peNormalizedAnnual` 與 `peTTM` 定義不同），逐一修完後得到完整 diff 報告，發現 `dividendYield` 5-7% 與 `priceToBookRatio` 12-38% 是**結構性方法論差異**，不是哪家錯。

**架構決策**：採用「Finnhub canonical, FMP audit」雙抓設計而非 fallback。理由：fallback 會讓同一支股票今天用 Finnhub、明天 quota 切 FMP 時 scoring 漂移、且漂移無法歸因；雙抓則保證 scoring 永遠來自 Finnhub（可重現），同時 FMP 平行抓取保留觀測能力（drift monitoring）。物理隔離靠 `_audit` 底線前綴慣例，禁止進入 LLM prompt。

**完成**：
- **`scripts/dual_fetch.py`（200 行）**：library + CLI 雙模式。輸出 `data/YYYY-MM-DD/{TICKER}.json`，頂層 `scoring`（Finnhub）+ `_audit`（FMP + diff + status）
- **`scripts/audit_drift_check.py`（110 行）**：掃過去 N 天 audit 紀錄，找出 `(ticker, field)` 在 >= MIN_HITS 天內 diff 超過 threshold 的持續性漂移，輸出 markdown 報告
- **`scripts/run_dual_fetch.sh`**：wrapper（檢查兩個 API key）
- **`README.md`**：三 script 用法（dual_fetch 日常 / audit_drift_check 週檢 / diff_tool 一次性 spot check），含 fmp_status 對照與 library 用法
- **`CHANGELOG.md`**：v1.1.0 紀錄含架構決策表
- **`SKILL.md`**：新增 § Dual-Fetch Discipline，明訂 `_audit.*` 不得進 prompt 的硬規則；Architecture Role 表把 simple metrics 從 TBD 改成 Finnhub canonical + FMP audit
- **修正 `diff_tool.py` + `adapters.py`**：v3 → stable 端點遷移、`peTTM` 提到 `peNormalizedAnnual` 之前

**未做（後續 PR）**：
- 不動 `investment_protocol_v4_8.md`，scoring/audit 整合進 protocol 是下一個獨立決策（PR-5/6 範圍）
- 不動既有下游 skill（ftd-detector / market-top-detector / us-stock-analysis）

## 🟡 Session Note (v1.43.0) — Finnhub Client + Diff Tool（PR-1 + PR-2）

新增 `skills/finnhub-client/` 作為共用基礎設施。背景：審計後發現 FMP free 250/day 配額會卡死 batch screening + Phase 3 自動化，且專案缺三個重大資料源（earnings calendar / earnings surprise / insider transactions）。Finnhub free 60/min ≈ 300× FMP 吞吐量，剛好補洞。

**完成**：
- **finnhub_client.py（359 行）**：60/min token-bucket throttle + file cache (per-method TTL) + exp backoff retry + 17 endpoints (quote / candle / profile / metric / financials-reported / filings / company-news / earnings-calendar / earnings-surprise / insider-tx / insider-sent / recommendation / price-target / upgrade-downgrade / dividends / splits / ipo-calendar)
- **adapters.py（171 行）**：5 個 Finnhub→FMP shape 轉換器；financials_to_fmp_income 標 `_lossy: True`（concept 對應不完整，僅供 raw filing reference）
- **diff_tool.py + run_diff.sh（374 行）**：side-by-side 比對 9 欄位 × 10 ticker，PASS<2% / WARN 2-5% / FAIL>5% 三級評分，輸出 `diff_reports/YYYYMMDD.md`

**架構修訂（吸收 ChatGPT review feedback）**：原方案「Finnhub Tier 1 包含 financials」改為**按資料種類分層**：
- 市場/事件層 → Finnhub primary（quote / OHLCV / profile / 4 種事件流）
- 財報真實層 → **FMP primary**（income/balance/cashflow，避免 Finnhub raw XBRL 漂移 quality model 的 CFO/NI/share count）
- 經濟/forward EPS → FMP only
- 簡易 metrics（P/E、ROE、div yield、P/B）→ PR-3 跑 5-7 天 diff 後再決定

**接下來**：使用者跑 `bash skills/finnhub-client/scripts/run_diff.sh`（需先 `export FINNHUB_API_KEY=...` 和 `export FMP_API_KEY=...`），連跑 5-7 天累積 diff 報告 → 決定 PR-4 data-client 抽象層的 routing 規則。

## 🟢 Previous Session Note (v1.42.2) — Sector Protocol 文字瘦身 R2

第二輪 trim — v1.42.0/v1.42.1 加進去的 FRED 解說文字現在搬到 README。原則：
- protocol 檔只留 LLM 執行所需（規則 / schema / 命令）
- 「為什麼這樣設計」「歷史教訓」「比舊版快多少」全部 → README 設計理由區

砍掉：Step 1 vs Step 6 解釋、confidence gating 教學、Renderer 給 user 的提示、
1999 dotcom/2021 SPAC 歷史教訓、Phase 3 「vs 舊流程 200 秒」對比、STEP C.6 timing 對比、
today_verdict bilingual 解說 + 中文範例、4-25 run 觀察記錄。

Phase 2 同時併入 user 的優化：theme_detector 改用 `--skip-if-fresh 10800` flag，script 自管 cache，LLM 不需要再 stat mtime。

統計：protocol 檔 1464 → 1423 行（-3%）；README 補上 5 個新 rationale 區塊。每次 sector 掃描 LLM 載入量都減一點。

## 🟢 Session Note (v1.42.1) — Sector Protocol 提速

4-25 跑 sector scan 仍 20 分鐘（v1.42.0 砍了 5 分但還可降）。Phase-by-phase 拆解後三個瓶頸都改掉：

- **Phase 3** 19 個 WebSearch 砍到 ≤ 5。強制走 `market-sentiment-analyzer` + `economic-calendar-fetcher` + `~/.claude/skills/earnings-calendar` + reuse `_phase0.fred_snapshot`。WebSearch 限 5 個 narrative，給了具體 query 範本與 ban list（Russia/Ukraine、FDA PDUFA、bank earnings dates、copper price、AI capex、DOJ Powell — 不是 sector-level 該管的）。
- **Phase 2** theme_detector 跑兩次浪費 145s（第一次 `timeout 150` 殺掉 retry）。Phase_1-2-3.md 加 runtime 提示：正常 140-180s，禁止 `timeout < 240` 包裝。
- **Phase 4c** Step 6 LLM 心算 11 sectors 改用 `step6_overlay.py --input` CLI，純 Python <1s 出 JSON 直接 paste。

**Phase 4a 4-lane 平行確認 OK**：4 個 Agent 都在 `msg_01U6D4...` 同一訊息，wall-clock = max lane = 109s（vs 序列 372s）。

預計 4-26 跑 sector scan：20 分 → ~14-15 分。

## 🟢 Session Note (v1.42.0) — FRED 整合

8 個改動全做完（P0-P3）。背景：審計發現 v4.9 spec 寫 fred-macro MUST-run 但 7/7 近期 invest 跑都跳過。Sector 完全沒接 FRED。

**完成**：
- **fred-macro**: composite score 改 latency-weighted（real-time tier 1.0 / employment 0.7 / inflation 0.5），解決 Lag Trap。composite 60→62。
- **Sector Phase 0**: 新增 Layer E (FRED MUST-run)。schema `_phase0.fred_snapshot` slim 11 欄位。validator 強制檢查。
- **Sector Phase 4a**: 新增第 4 lane `FRED_Macro_Analyst`，讀 `SECTOR_ROTATION_GUIDE`。
- **Sector Phase 4b DA + Investment Phase 2.8 Red Team**: 兩個 prompt 都加 FRED slim paste + 衝突規則（必須引用具體數值，不可寫 vague「macro 轉差」）。
- **Sector Phase 4c STEP G.5**: Macro/Theme 衝突 → cap WARM + `macro_theme_divergence` flag。Anti-1999/2021 泡沫頂規則。
- **Sector Step 6**: FRED regime overlay 取代 Step 1（不疊加）+ regime_confidence gating。`step6_fred_multiplier` 寫入每 sector，`step6_overlay` block 寫頂層。renderer 新增 FRED× 欄位。
- **`step6_overlay.py`**: deterministic Python 計算器（10 regimes × cyclical/defensive matrix + favor/avoid override + confidence gating）。
- **`backtest_step6_overlay.py`**: 用 `fred-macro --asof` + yfinance 回測 top-3 vs bottom-3 spread。目前 n=5 樣本太小（每個 sector 才 12 天 history），smoke test 跑通；data 累積到 50+ 才有統計意義。
- **`investment/scripts/validate_phase0.py`**: V4.9 mini-gate 抓 LLM 漏填 fred_available / fred_snapshot / rationale。

**今日 sector_intel.json** 已 backfill FRED slim snapshot + Step 6 multipliers。`reports/2026-04-24_sector_report.md` 已重 render 含 FRED× 欄位 + Step 6 區塊。`validate_sector_intel.py` rc=0。

**下次跑投資 protocol 預期變化**：
1. LLM 必須跑 fred-macro fetch（會被 validate_phase0.py 抓）
2. Red Team subagent 收 FRED slim paste，產出 kill_conditions 會引用具體 FRED 數值
3. macro_multiplier_rationale 必須提到 FRED / yield / real_rate / nfci / credit / regime 之一

**下次跑產業掃描預期變化**：
1. Phase 0 多 Layer E（fred-macro fetch + slim snapshot 寫入 _phase0）
2. Phase 4a 多第 4 lane（FRED_Macro_Analyst subagent）
3. Phase 4b DA 收 FRED snapshot，可量化反論
4. Phase 4c 仲裁可能觸發 STEP G.5（FRED-avoid sector 被 theme 推 HOT → cap WARM）
5. Phase 5 evaluator 跑前算 step6_multiplier 寫入每 sector
6. 報告含 FRED× 欄位 + Step 6 overlay 區塊

## 🟢 Session Note (v1.41.1)
- **Protocol 檔案瘦身**：`sector_protocol_main.md` / `phase_0.md` / `phase_1-2-3.md` / `phase_4-5.md` 全部清掉人類向敘述、計算範例、歷史沿革，只留 LLM 執行所需。702 → 641 行。
- **README 吸收**：被移走的內容（Phase 0 計算範例 ×2、Phase 5 機械化動機、V1.4 changelog）全部進 `sector/README.md`。
- **新原則寫入 README**：protocol 檔只給 LLM 看（緊湊、機械、可驗證），README 只給人看（背景、設計理由、debug）。Protocol 是 source of truth，README 註明 pointer 即可，避免雙邊漂移。

## 🟢 Session Note (v1.41.0)
- **(1) 產業掃描 Phase 5 機械化**：新增 `sector/scripts/render_sector_report.py`，從 `_sector_intel.json` 直接渲染 markdown 報告（7 段：Verdict / Macro / Today's Verdict / DA Challenges / Divergence / Themes / Handoff）。
- **(2) Protocol V1.4**：`sector/phase_4-5.md` Phase 5 重寫為 4 步機械流程（寫 JSON → validator → renderer → ≤10 行 summary）。PS **禁止**用 Write 手寫 markdown；`_phase4c.today_verdict` 所有欄位為必填（renderer 的文字來源）。
- **(3) 動機**：今日 `產業掃描` 跑 26 分鐘（`sector_20260424_210620.log`）。時間軸拆解顯示 Phase 5 markdown 生成 663s + 最終 summary 225s 共 15 分鐘純模型輸出，內容與 `today_verdict` 完全重疊 → 全部改機械渲染。
- **(4) 今日 markdown 已用新 renderer 回寫**：`reports/2026-04-24_sector_report.md` 現為 102 行 / 5.2KB，比原 71 行版本多出 Macro Context / Sector Divergence Watch / 完整 Actionable Themes 區塊。

## 🟢 Session Note (v1.40.0)
- **(6) 宏觀資料官方化**：新增 `fred-macro` skill 抓 12 條 FRED 官方 series（利率 / 通膨 / 就業 / 信用 / 壓力）；投資 protocol Phase 0 新 L4 layer 永遠跑（MUST-run）；`fred_snapshot` 輸入 multiplier 雙向 blending（LLM baseline × FRED caps 取 min，全 clear 時 × 1.05 bonus）。
- **(5) Dashboard 自動刷新**：`dashboard_server.py` 新 `fred_refresh_loop` daemon 每 15 min 重抓 cache；`bridge.py` 注入 `data.fred_macro` 到前端 data.json。
- **(4) MACD UI 完整**：點擊 MACD 欄跳 RSI 同風格 click popup — zero-axis bar + 4-regime quadrant map (strongest_bull / weakening_bull / reversal_bull / strongest_bear) + personalised advice。Preset buttons 加 hover tooltip（criteria / strategy / action 三段式，紫色 accent）。Signal/warning pills 也改自訂 hover tooltip，取代原生 title=。
- **(3) 前次累積**：跨頁導航 scan banner `Ended_at` 時間戳（5 分鐘效期）；AnalyzeQueue 解決重複分析；`i18n.js` `scan_confirm` preflight 時間預告。

---

## 🔵 Momentum Context (Multi-Universe)
**動能選股 Universe 整合機制**。
- **(1) 市場狀態**：目前預設掃描 `all` (SP500 + Nasdaq 100 + Watchlist)，總數 527 檔。
- **(5) 數據結構**：CSV/JSON 新增 `in_nasdaq100` 布林欄位。
- **(4) UI 連動**：Dashboard 預設顯示 Top 200，但透過 `isWatchlist` 邏輯，自選股不受 Universe 篩選器影響，始終顯示。

---

> **📜 完整版本歷史已移至 [`CHANGELOG.md`](./CHANGELOG.md)** — 自 v1.0.0（2026-04-09 初始）至目前全部 entries，含 git commit 引用與 evolution highlights。

---

## 📋 Bridge 資料流對照（System Manifest）

| Protocol | 輸出 Log | Bridge 讀取欄位 | Dashboard 顯示 |
|---|---|---|---|
| `investment_v4_8` | `invest_logs/history.json` | `final_decision`, `score`, `macro_alignment`, `key_risks` | decisions 頁全部 |
| `sector_v1.3` | `sector_logs/*_intel.json` | `market_regime`, `_phase0` (breadth/FTD/MT), `today_verdict` | index + sector |
| `news_v2.1` | `news_logs/*_digest.json` | `verdicts[]`, `trump_signals`, `catalysts` | news 頁 + sidebar |
| `breadth_analyzer`| `breadth_cache/*.json` | 6 組件 breadth + trend | index 廣度 gauge |
| `positions.json`  | — | lots → avg_cost / live_position | decisions 持倉 |
