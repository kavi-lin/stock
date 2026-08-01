# Session Notes 歸檔 v1.59.0 → v1.61.3（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v1.61.3) — Triage 燈號改成 RSS 源層級（單顆）+ 按鈕改名「更新 RSS 源」

### 修正：v1.61.2 我做錯
v1.61.2 我把 freshness dot 加到「每張 card」(per-headline) 並加 tier 計數摘要。User 真實要求是：
- **一顆**燈號（不是每張都一顆），代表 **RSS 源最後抓取時間**（不是每則新聞發布時間）
- 燈號**位置**：放在 Triage tab header 的「更新 RSS 源」按鈕**旁邊**
- Button 改名：原「跑新 Triage」/「Run new Triage」→「更新 RSS 源」/「Refresh RSS」
- Tooltip：hover 燈號或按鈕都顯示詳細

### 修
- `Dashboard/page-news.js`：
  - 撤掉 `_freshness()` per-card helper、撤掉 tier 計數摘要、撤掉每張 card 的圓點與相對時間欄
  - `renderTriageFeed()` 開頭 `await fetch('/api/preflight')` 拿 `rss` 項的 `age_sec`，4-tier 算單顆燈號 class
  - 燈號 + 按鈕都掛同一份 tooltip（文字含上次抓取時間 + 規則 + 按下按鈕的副作用說明）
- `Dashboard/i18n.js`：`triage_run_btn` 中文「更新 RSS 源」/ 英文「Refresh RSS」；`triage_no_data` 對應改字
- `Dashboard/page-news.js` 確認對話框文字也對齊：「更新 RSS 源？會重抓 RSS（~30s）+ 對 60+ 則跑 Stage 1 shallow snap」

### 行為
- Section header：`🗂 Stage 1 RSS Triage  | 30 則  ●  [更新 RSS 源]`
- 燈號顏色（4-tier）依 raw.json mtime（preflight rss item）：
  - <1h 🟢 / <3h 🟡 / <5h 🟠 / ≥5h 🔴 / missing ⚪
- Tooltip（hover 燈號 / 按鈕）：
  ```
  RSS 源上次抓取：3h 前
  狀態：偏舊 (FRESH)
  規則：<1h 🟢 / <3h 🟡 / <5h 🟠 / ≥5h 🔴
  按「更新 RSS 源」會重抓 + 跑 Stage 1 shallow snap
  ```

### 殘留
- `bridge.py` v1.61.2 加的 `published` 欄位仍保留（從 raw.json join），目前未用，留作未來可能用途；若後續確認不會用可一併移除（~10 行）

## 🟢 Session Note (v1.61.2) — Triage tab freshness 4-tier 燈號 + tooltip + tier 計數摘要

### 改動
- `bridge.py`：`extract_shallow_news()` 新增 raw.json `news_id → published` map（per-date cache），每筆 shallow 注入 `published` ISO timestamp。30/30 命中（raw.json 完整 cover）
- `dashboard_server.py`：`triage` prompt 加要求 verdict 含 `published`（從 raw.json 抄），未來 user 跑 triage protocol 也會帶
- `Dashboard/page-news.js`：
  - 新增 `_freshness(publishedIso)` 4-tier helper：<1h 🟢 / <3h 🟡 / <5h 🟠 / ≥5h 🔴；missing → ⚪ 灰
  - 每張 triage card 左上加圓點（dot）+ 相對時間 (Xm/Xh/Xd)，hover 顯示 tooltip 含真實時間 + 來源 + 規則
  - Section header 加 tier 計數摘要（🟢 N · 🟡 N · 🟠 N · 🔴 N）
  - 切回 Triage tab 強制 re-render（避免相對時間過期，移除 dataset.rendered guard）

### Tooltip 格式
```
5m 前發布
📡 CNBC Top
🕒 04/29 03:29
規則：<1h 🟢 / <3h 🟡 / <5h 🟠 / ≥5h 🔴
```

### 設計取捨
- 4-tier 不 5-tier：avoiding 5-10h 中間色彩管理；≥5h 一律 🔴 反映「動能多半 priced in」
- 用 RSS 真實 `published` 不用 file timestamp：UI 反映新聞實際發布年齡，不被 DIGEST 跑時間污染
- 強制重 render：避免長時間打開 tab 時相對時間鎖死

## 🟢 Session Note (v1.61.1) — Protocol confirm 對話框加 daily_update.sh 上次更新時間

### 動機
User 點 invest / sector / DIGEST / FLASH / REVIEW 前忘記跑 `daily_update.sh` → 分析吃舊 macro/breadth/sector_intel cache。要在 confirm() 文字最前面加上「上次跑 daily_update 是多久前」做提醒。

### 修
- `Dashboard/utils.js` 新增 `UI.dailyUpdatePrefix()` async helper：fetch `/api/preflight`、抓 `breadth` cache age（daily_update.sh 第一步）作為 proxy；回傳：
  - 正常：`📌 daily_update：{age_str} 前\n\n`（中）/ `📌 daily_update: {age_str} ago\n\n`（英）
  - cache MISSING：`⚠️ daily_update 未跑過`
  - fetch 失敗：空字串（不污染 confirm）
- 5 個 confirm dialog 接上 prefix（皆加 `await UI.dailyUpdatePrefix()` + 字串前綴）：
  - `Dashboard/script.js:674` — Quick Launch invest
  - `Dashboard/page-decisions.js:567` — `goFlash` (FLASH from card)
  - `Dashboard/page-decisions.js:1109` — `refreshTicker` (re-analyze invest)
  - `Dashboard/page-news.js:445` — REVIEW (`copyReviewPrompt`)
  - `Dashboard/page-news.js:456` — flash_text (`goFlashText`)
  - `Dashboard/page-news.js:709` — DIGEST (`refresh-news` 按鈕)
  - `Dashboard/page-sector.js:851` — `triggerSectorScan`

### 不加範圍
- **Triage** (`page-news.js:407`)：自己 fetch RSS、跑 shallow snap，不依賴 daily_update.sh 任何輸出
- **動能** / **delete position** 等：無 daily_update 依賴
- 7 個 confirm dialog 共動 5 個檔

## 🟢 Session Note (v1.61.0) — Unified protocol queue：news/flash/triage 不再被 invest 擋

### Bug：news.html 按 Triage 跳「another protocol is running: invest」
- 原因：`dashboard_server.py:run_protocol()` 全域單一 `_protocol_state` lock。invest（10-15min）跑時 news/flash/triage/review 全被擋 (409)。
- 既有 `_analyze_queue` 是 invest 專用。news 系列沒有 queue，撞到 lock 就 reject。

### 修：擴展為 unified `_protocol_queue`
- `dashboard_server.py`：rename `_analyze_queue` → `_protocol_queue`；新增通用 `enqueue_protocol(name, params, source)` 接所有 protocol；entry 含 `id`/`label`/`name`/`params`；保留 `enqueue_analysis()` 為 invest-only backward-compat wrapper
- 3-min cooldown 只在連續兩個 invest 之間生效（`last_finished_name == "invest" and name == "invest"`），news 系列背靠背跑無 cooldown
- 新 endpoint：`POST /api/protocol-queue` 接所有 protocol；`DELETE /api/protocol-queue/{id}` 取消 queued entry
- 舊 `/api/analyze-queue` (GET/POST/DELETE-by-ticker) 全保留，沿用 wrapper

### Frontend：toast 取代立即 banner
- `Dashboard/page-news.js` `triggerProtocol()` 改 POST `/api/protocol-queue`：
  - `total_ahead === 0` → 立即 showRunBanner（會在 ~2s 內開跑）
  - `total_ahead > 0` → 只 toast：「⚡ FLASH «headline» 已排隊（第 3 個，前面 2 個進行/排隊中）」
  - 新增 `pollForMyJob(myId, title)` poller：以 `_activeQueueId` 為 gate，當 status.queue_id 等於 my id 才 showRunBanner（之前 banner 隱藏中）
- `Dashboard/analyze-queue.js` widget filter：`/api/analyze-queue` 回傳的 queue 現在含所有 protocol，widget 只 keep invest entries（widget 是 index.html invest queue 的視覺，不該污染 triage/flash）

### 設計取捨
- **單一 queue**：user 明確要求；簡化 lock 邏輯；不會兩 protocol 同時燒 token
- **延遲 banner**：避免 user 一按就看到「Claude 處理中」但實際在排隊（誤導）
- **toast 顯示完整位置**：第 N 個 / 前面 X 個進行/排隊中 — user 知道要等多久
- **invest 仍保 cooldown**：5-hour token 限制現實，連續兩個 invest 還是要 3min 緩衝

### Smoke test
- `enqueue_analysis('NVDA')`（legacy）+ `enqueue_protocol('triage')` + `enqueue_protocol('flash_text', {headline})` → 3 entries 全進同 queue，position 正確 1/2/3
- `enqueue_protocol('invest', {ticker:'NVDA'})` 對既有 NVDA 重複 → 拒絕 (duplicate_pending)
- `remove_from_queue(id)` 正確移除 by id

### User 動作
- 重啟 dashboard_server.py 載入新 queue 邏輯
- 之後 invest 跑時可同時點 Triage / FLASH，會 toast「已排隊（第 N 個）」，invest 跑完才開始

## 🟢 Session Note (v1.60.2) — Firstrade 自動記錄 Phase 1：macOS NotificationCenter discovery script

### 確認的事實
- 富途 push DB（v1.58.0 已接）只有市場新聞 bot 兩個 sender (10025/10027)，掃 400 筆 zero Firstrade 內容 → 「既然能收推播」這個前提僅對市場新聞成立
- User 確認 Firstrade trade confirmation 是走 macOS 系統推播（iPhone Continuity 鏡像到 Mac），落點 `~/Library/Group Containers/group.com.apple.usernoted/db2/db`（438KB SQLite）
- 該 DB 被 TCC 鎖住，Bash sandbox `unable to open database file` — Apple 規定 Terminal/Python 要加「Full Disk Access」
- DB schema：`record.data` 是 binary plist（NSKeyedArchiver wrap），需 plistlib + 處理 `$objects` list

### 兩階段策略
卡點：「不知道 Firstrade push 在 DB 裡長什麼樣」+「TCC 必須先授權」。所以拆兩階段：
- **Phase 1 (本 session)**：Discovery 腳本，user 跑一次告訴我真實格式
- **Phase 2 (待 Phase 1 feedback)**：寫 watch / parser / dashboard_server thread / 自動 sync positions.json

### Phase 1 script — `scripts/parse_firstrade_notifications.py` v0.1
- 讀 NotificationCenter DB：先 `shutil.copy` 到 tmp 避免 -wal/-shm journal 卡
- `sqlite3` URI 用 `mode=ro` 唯讀打開
- Output：(1) 最近 N 小時各 app push 計數（標 `← FIRSTRADE 命中` / `可疑（含 fst/trade/broker）`）；(2) 最近 limit 筆 sample 含 title/body/subtitle/uuid
- `_extract_title_body()` 兩條解碼路徑：`req` 直接 dict（早期 macOS）OR `$objects` NSKeyedArchiver 字串列（新版）
- TCC 阻擋時印中文錯誤 + 修法步驟（避免 user 不知所措）
- 用法：`python3 scripts/parse_firstrade_notifications.py -k firstrade --hours 720 -n 50`

### User 待辦
1. macOS System Settings → Privacy & Security → Full Disk Access → 加 Terminal.app → 重啟 Terminal
2. 跑 `python3 scripts/parse_firstrade_notifications.py --hours 168 -n 30` 看 app 清單
3. 鎖定 firstrade：`python3 scripts/parse_firstrade_notifications.py -k firstrade --hours 720`
4. 把命中的 bundle id + 1-2 筆 title/body 樣本貼給我 → 我寫 Phase 2 parser

### Fallback
- 若 NotificationCenter 真找不到 Firstrade（iPhone push 沒開 / Continuity 沒鏡像）→ 改走 Gmail MCP 讀 Trade Confirmation email
- 若 plist 解碼太複雜 → 用 `bpylist2` pip package

## 🟢 Session Note (v1.60.1) — 即時動態 banner：重新整理按鈕只在 done/error 才出現

### Bug：跑 protocol 時計時器持續累加，user 不該能按重新整理（會中斷觀察進度）
- 修：`news.html` 重新整理按鈕預設加 `hidden` class
- `showRunBanner()` running 狀態主動 `add('hidden')`
- `setRunBannerDone` / `setRunBannerError` 會 `remove('hidden')` 讓按鈕浮現
- 行為：跑著時 banner 只有 [展開][CANCEL][✕]；done 後變成 [展開][🔄 重新整理][✕]

## 🟢 Session Note (v1.60.0) — Triage tab：Stage 1 RSS triage 獨立檢視 + per-card Phase 2 按鈕

### 新增 `triage` protocol mode（`dashboard_server.py`）
- PROTOCOL_PROMPTS 加 `triage`：(1) 必須先跑 `python3 news/fetch_news_rss.py --hours 24` 重撈 RSS；(2) 對 raw.json 60+ 條跑 30 字 shallow snap；(3) 寫 `news_logs/YYYY-MM-DD_triage.json` (格式同 digest.json verdicts schema)；(4) 禁止跑 Stage 2 / 寫 digest.json / patch caches
- LOG_DIRS / TIMEOUT_OVERRIDES 對應補上（10 min timeout）

### 新 data feed：`shallow_news[]`（`bridge.py`）
- 加 `extract_shallow_news()` 函式：合併最近 3 份 `*_digest.json` 的 `depth: shallow` 項目 + 最近 3 份 `*_triage.json` 全部項目，dedupe by headline，按 `|score|` desc 排序取前 60
- `data.shallow_news` 注入 data.json，原 `data.news` 行為不動（只有 deep verdicts）

### Triage tab UI（`Dashboard/news.html` + `Dashboard/page-news.js`）
- filter tabs 加第 4 顆 `data-filter="triage"`，與 All/Reviewed/Pending 用分隔線隔開（**不在 All 內**）
- `<div id="news-triage-feed">` 獨立容器，跟既有 `#news-feed-detailed` 並列在 flex-1 包裝下
- `applyNewsFilter()` 切到 triage 時 hide deep feed / show triage feed（含 lazy render）
- `renderTriageFeed()` 渲 compact card：score badge + binary flag + source tag (digest/triage) + 截 3 sectors + 截 5 tickers + ⚡ Phase 2 按鈕
- 區塊 header 有「⚡ 跑新 Triage」按鈕：confirm（~30s RSS + 5-8min snap / ~$0.5 tokens）→ `triggerProtocol('triage', {}, ...)`
- per-card「⚡ Phase 2」按鈕 → 直接呼叫既有 `goFlashText(headline)`（複用 flash_text mode，append pending verdict 到 digest.json）

### i18n
- 加 `triage_tab` / `triage_section_title` / `triage_run_btn` / `triage_phase2_btn` / `triage_no_data`（中英）

### 設計取捨
- **Triage 不入 All**：避免 60+ 條 shallow 沖淡主 feed 的 deep verdict 視覺
- **dedupe by headline**：同一篇若 digest 跟 triage 都有，digest 優先（已過 4-subagent debate 的更可信）
- **不開 triage.json schema 文件**：完全沿用 digest.json verdicts schema，prompt 內 inline 描述
- **「跑新 Triage」每次強制重撈 RSS**：避免吃舊 raw.json，user 確認 Q2 是要新鮮資料

### Smoke test
- `python3 -c "import dashboard_server"` confirm `triage` 載入到 PROTOCOL_PROMPTS
- `python3 bridge.py` confirm `[OK] Shallow triage: 30 items`（從現有 digest.json 撈出）
- `node --check page-news.js` ok
- ⚠️ User 需重啟 dashboard_server.py 才會載到 `triage` mode

## 🟢 Session Note (v1.59.2) — flash_text 修「沒寫 digest.json」漏洞 + reload 後 banner 不再彈回

### Bug A：flash_text FLASH 跑完後 news.html 看不到 card
- 原因：v1.59.0 寫的 `flash_text` prompt 只叫 Claude 「產 reports/*_news_flash.md」，沒提示「也要 append verdict 到 news_logs/YYYY-MM-DD_digest.json」
- bridge.py 的 news cards 是從 `digest.json.verdicts[]` 抽，所以只有 MD 就等於 Dashboard 看不見
- 修：`PROTOCOL_PROMPTS["flash_text"]` step 4 改為「**必須產兩個檔（缺一不可）**」，明列 digest.json 的 schema 欄位（news_id, depth, review_status: pending, headline, headline_zh, source_label, news_type, bull/bear/sector/macro_case, verdict, net_impact_score, arbiter_reasoning, binary_risk, within_48h, affected_sectors, tickers_mentioned）
- 已對 22:17 OpenAI 那次 FLASH 手動補 patch（從 MD 萃 verdict 寫進 digest.json `n077`，重跑 bridge.py）— user 不用花 $1 重跑
- ⚠️ 概念澄清：FLASH 結果在「**待審核**」tab（review_status: pending），不在「已審核」。要進 已審核 需手動按卡片上「送審」按鈕觸發 `review` protocol 升級

### Bug B：點「重新整理」後 banner 又自動彈回
- 原因：page-news.js 第 458-479 行 resume IIFE 在 reload 後檢測到 protocol status=done within 5min，強制重新顯示 banner
- 修：reload 按鈕 click handler 額外寫 `sessionStorage.setItem('news_banner_dismissed', Date.now())`；resume IIFE 讀到 30s 內標記就跳過 done/error 重顯（running 仍會 resume，避免 user 在 active job 中誤點 reload 後沒進度可看）
- one-shot：標記讀完即 `removeItem`，不影響後續切頁

### Files
- `dashboard_server.py` — flash_text prompt
- `Dashboard/page-news.js` — reload click handler + resume IIFE skip 邏輯
- `news/news_logs/2026-04-28_digest.json` — 手動 append n077 verdict（含 .bak）

### 後續驗證（user）
- 開 `localhost:8080/news.html` → 看到「OpenAI 業務「運轉良好」」⏳ PENDING 卡片（在 待審核 tab）
- 重啟 dashboard_server.py 後再跑一次 flash_text → 確認 digest.json 自動更新（不再要手動 patch）
- 點 banner ✕ / 重新整理 → 頁面重整後 banner 不再彈回

## 🟢 Session Note (v1.59.1) — News banner 加重新整理按鈕 + 修 done 後 detail 殘留 bug

### Bug：banner 在 done 狀態下同時顯示矛盾文案
- title 被 `setRunBannerDone` 改成「分析完成，資料已更新」
- 但 `news-run-detail` 還是 `showRunBanner` 留下的「Claude 正在處理中...」沒清
- 修：`setRunBannerDone` / `setRunBannerError` 都加上 `detailEl.textContent = ''`

### 加 `news-run-reload` 按鈕
- `news.html` banner 右側 expand/cancel 之間加 `<button id="news-run-reload">🔄 重新整理</button>`，總是可見（不管 running/done/error）
- `page-news.js` 綁 click → `location.reload()`
- 用途：`pollNewsRunStatus` done 後雖然會自動 `loadNews()` 2s 後重撈，但 `bridge.py` 可能還沒跑完 / cache 沒同步，這個按鈕讓 user 在他想看到的時機強制硬重整

## 🟢 Session Note (v1.59.0) — 富途推播搬到 news.html + 每筆加 FLASH 按鈕

### 1) Backend 加 `flash_text` mode（`dashboard_server.py`）
- `PROTOCOL_PROMPTS` 新增 entry：prompt 接 `{headline}`（非 `{ticker}`），指示 LLM 抽事件主體 → WebFetch 補上下文 → 4 視角 inline 辯論 → 產 `reports/YYYY-MM-DD_HHMM_news_flash.md` (review_status: pending)
- `PROTOCOL_LOG_DIRS` / `PROTOCOL_TIMEOUT_OVERRIDES` 對應補上（10 min timeout，env override `FLASH_TEXT_TIMEOUT_SEC`）
- `run_protocol()` 第 263-266 行 `{headline}` validation 已存在（review 用），自動沿用

### 2) 卡片從 index.html 搬到 news.html
- `Dashboard/index.html` 移除 Layer 5 富途 card 與相關 IIFE
- `Dashboard/script.js` 移除 `initFutuPush()` IIFE + i18n 白名單條目（共 ~80 行）
- `Dashboard/news.html` 在 `<div class="p-8">` 起手、stats grid 之前插入 `id="futu-card"` glass-card（與舊版同結構，但新增 filter-stats span）

### 3) page-news.js 加 IIFE + handler
- 加 `window.goFlashText(headline)`：confirm 對話 → `triggerProtocol('flash_text', { headline }, '...')`，token 警告寫 `~$0.5-1` / 5-10 分鐘
- 加 `initFutuPush` IIFE：每筆 row 移除 ticker pill click（純顯示徽章），新增右側 `⚡ FLASH` 按鈕，點擊 → `goFlashText(rawText)`
- 新增 `filter-stats` 顯示「已過濾 N 則 HK/A 股」（從 `/api/futu-notifications` 回傳的 `filtered_count` 取）
- `applyTranslations()` 加 overview.futu_* 三鍵 lookup（避免切語言時富途標題不譯）
- 第 462 行 `isNews` 判斷加上 `'flash_text'`，使切回 news.html 時能 resume banner

### 設計取捨
- **不另開 protocol 檔**：news_protocol_v2.md L21/L394 已寫 FLASH 接「貼標題/連結」 — 原生支援 free text，只動 dashboard_server.py prompt template 即可
- **不從推播抽 ticker 走 `flash` (ticker) 路徑**：那會讓 FLASH 變成 generic ticker 新聞掃描，弱化「對這則推播事件本身分析」的核心
- **ticker pill 改純顯示**：news.html 沒 Quick Launch input，原 prefill 行為失效；主互動讓給 ⚡ FLASH 按鈕
- **FLASH 按鈕 inline confirm**：跟 page-decisions.js `goFlash` 對齊樣式，先 confirm 再送，避免誤觸 ~$1 token 燒

### Smoke test
- `python3 -c "import dashboard_server"` confirm `flash_text` 載入到 PROTOCOL_PROMPTS / LOG_DIRS / TIMEOUT_OVERRIDES
- `node --check Dashboard/page-news.js` / `script.js` 皆 ok
- `curl /news.html | grep futu-card` → 1（已加入）；`curl / | grep futu-card` → 0（已移除）
- ⚠️ User 9:27am 啟動的 dashboard_server.py 需手動重啟才會載到 `flash_text` mode（舊 process 不認）

### 後續驗證（user 自行）
- 重啟 dashboard_server.py
- 開 `localhost:8080/news.html`，確認最上方有富途 card + ⚡ FLASH 按鈕
- 點某筆 ⚡ FLASH → 對話 → OK → 看 `news/scan_logs/flash_text_*.log` + 5-10 分鐘後 `reports/*_news_flash.md`
