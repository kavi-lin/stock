# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + [SemVer](https://semver.org).
Single source of truth for version history. Current version authority is `VERSION` file + `Dashboard/utils.js`.

> **Purpose**: Let future Claude sessions (and humans) understand the evolution
> of the system — what changed, where to look, why. Entries link back to git
> commits where applicable; for un-committed work, dates reflect local VERSION
> bump time.

---

## [3.9.4] — 2026-05-20 — Break News model-aware admission

### Fixed — 硬 cap 餓死 debater

Break News poller 原本用 `BREAK_NEWS_DAILY_MAX_DEBATES` 當全域每日 item cap，
會出現 dashboard 顯示「今日剩餘預算 0」，但 settings 裡 Claude/Gemini/Codex
仍有 quota 的矛盾。本版把 automatic debate admission 改成讀 multi-model
governor 的真實可用 call：

- capacity 綁 Break News A/B voice，而不是三模型總 quota；Codex 保留 fallback
  buffer，不拉低正常 Claude × Gemini 容量。
- 一則 debate 依 `BREAK_NEWS_EST_CALLS_PER_DEBATE`（預設 6 calls）估算，不再把
  1 則新聞錯算成 1 call。
- admission 會扣掉現有 `pending_debate` backlog，避免 poller 連續 cycle 超發。
- disabled / cooldown / over-budget 的 voice 會讓 automatic admission 歸 0；手動
  raw debate 仍可由使用者觸發。
- `BREAK_NEWS_SESSION_RESERVE` 改為 call reserve；預設 25 calls 約保留 4 則
  debate，若要保留約 25 則 debate 應設約 150 calls。
- `BREAK_NEWS_DAILY_MAX_DEBATES` 預設 0，僅在設成 >0 時作 emergency item
  ceiling。
- Break News UI 顯示 `admission/model_capacity`，tooltip 顯示 pair 與 calls/debate。

---

## [3.9.3] — 2026-05-19 — Market-wide 公司名誤中修正

### Fixed — Dollar / Dow / S&P 裸 token 誤判

V3.9.2 收窄多數 broad-market regex 後，仍保留少數裸 token 可能誤中公司名：
`Dollar General` / `Dollar Tree`、`Dow Inc`、`S&P Global`。本版改為只匹配明確
指數或宏觀語境：

- `dollar` → `US dollar` / `dollar index` / `DXY`
- `dow` → `Dow Jones` / `Dow futures` / `DJIA`
- `s&p` → `S&P 500` / `S&P futures` / `SPX` / `SPY`

---

## [3.9.2] — 2026-05-19 — Market-wide 判定收斂

### Changed — 收窄 Market Consensus 的 broad-market regex

V3.9.1 的方向修正有效，但 market-wide regex 仍有裸 `rates/oil/gold/war/yield`
等寬匹配，可能把 `price war`、油金個股財報、公司貸款利率等個股新聞拉回
Market Consensus。本版收窄為明確宏觀語境：

- `interest rates` / `fed rate` / `rate outlook` / `rate cut|hike`
- `Treasury yields/market/auction/selloff/retreat`
- `oil prices` / `crude oil`、`gold prices`
- `trade war`、`Iran war`、`Ukraine war`

### Fixed — digest market-wide 判定帶入 affected sectors

committee digest 本身有 `affected_sectors` / `tickers_mentioned`，但 V3.9.1 沒把
它傳給 `_is_market_wide()`，導致 digest 的 multi-sector `sector_news` 比
break-news debate 更難進 Market Consensus。本版把 digest sectors/tickers 包成
entities 傳入，讓 high-quality digest 與 debate 使用同一套判定。

驗證：最近 12h market events 維持精簡（10 筆），合計貢獻約 `-3.7`；未見裸
keyword 導致的個股噪音回流。

---

## [3.9.1] — 2026-05-19 — Break News Market Consensus 校準

### Fixed — 市場共識線被個股 bullish 新聞推得過高

V3.9.0 後圖上 `Market` 仍顯示高情緒，但當日大盤已連跌。診斷發現 trend rollup
有三個偏多來源：

- `_event_weight()` 用 signed score 算權重，`BEARISH -2` 被 clamp 成最低權重
  `-0.25`，低估負面事件。
- digest 有 signed `net_impact_score` 但 `verdict` 缺失時，原本 sign=0，導致
  「futures fall / oil-yield shocks」這類負面 headline 不入帳。
- `__ALL__` 把所有個股/小題材 closed debate 等權加到 market line，POET / INOD /
  target increase 類個股 bullish 新聞把大盤線推高。

修正：

- `_event_weight()` 改用 `abs(score)`；方向只由 verdict 或 signed impact 決定。
- digest verdict 缺失時 fallback `sign(net_impact_score)`。
- `__ALL__` 改為 Market Consensus，只吃 macro / monetary / geopolitical / broad
  market headline；個股新聞仍進 sector/theme，不再等權推高大盤線。
- closed debate 時間優先用 source `published`，缺失才 fallback `fetched_at`。
- `trend-chart.js` label 改成 Market Consensus / Raw Pulse，meta 顯示
  `market_event_count/log_count`。

驗證：最近 12h market events 由泛新聞 67 筆縮到 11 筆，合計貢獻 `-4.2`；
`__ALL__` 尾端從約 `+0.87` 轉為約 `-0.81`，方向與盤面壓力一致。

---

## [3.9.0] — 2026-05-19 — Break News quota pacing + Raw Pulse

### Added — Raw Pulse 即時脈搏線

Break News source 擴充後，raw stream 已能更快抓到市場訊號，但趨勢圖原本只吃
committee digest + closed debate，LLM quota 用完後半天情緒線就不動。本版新增
獨立 `__RAW_PULSE__` 線：

- `trend_rollup.py` 讀 `_raw_stream.json`，用 raw item 既有 signed `shallow_score`
  產生低權重即時脈搏。
- Raw Pulse 是獨立 `kind: pulse`，不混入 `__ALL__` market consensus，也不產
  sector/theme，避免雜訊污染權威辯論線與 EMA scale。
- raw headline fingerprint 若已被 committee digest 或 closed debate 覆蓋則跳過，
  避免 raw→debate 雙算。
- `trend-chart.js` 認 `kind: pulse`，full mode selector 永遠保留「即時脈搏 /
  Raw Pulse」選項；compact 首頁仍鎖定乾淨的 whole-market consensus。

### Changed — LLM debate admission 改成分數排序 + 美股時段保留

- `poller.py` 改兩段式 admission：第一段只收 raw entries + debate candidates；
  第二段依 priority 排序後才消耗 LLM 預算。priority = `abs(shallow_score)`、
  binary、source credibility、非社群優先、Futu tie-break、freshness。
- 新增 `BREAK_NEWS_SESSION_RESERVE=25`。非美股新聞時段最多使用
  `DAILY_MAX - reserve`，07:00-18:00 America/New_York 才釋放全日額度。
- poller state 新增 `debate_candidates`、`auto_budget_limit`、
  `session_reserve`、`us_news_window_open`，方便 debug 為何候選被擋。

### Changed — raw stream retention

- `_raw_stream.json` 保留期由 24h/150 筆改為可設定，預設
  `BREAK_NEWS_RAW_STREAM_MAX_AGE_H=72`、`BREAK_NEWS_RAW_STREAM_CAP=500`，
  讓 Raw Pulse 能覆蓋完整 3 日趨勢圖。

---

## [3.8.1] — 2026-05-19 — Break News 辯論氣泡左右/配色修正

### Fixed — codex ↔ gemini 辯論兩邊都靠右藍色

`renderThreadBubble` 用 `agent === 'claude'` 硬判左右與配色：只有 claude 走左側橘色，
其餘 model 全部右側藍色。當辯論配對非 claude（例如 codex ↔ gemini）時，兩邊都判為
非 claude → 都靠右、都藍色，看不出對話分側。

- **`scripts/break_news/debater.py`** comment record 新增 `side`（`"A"`/`"B"`）欄位，
  由 turn 位置決定（後端真相），與既有 `agent_role_label` 一致。
- **`Dashboard/news_components.js`** `renderThreadBubble` 改讀 `comment.side` 決定
  左右 + 配色（A=左/橘、B=右/藍）；舊資料無 `side` 時 fallback 解析 role label，
  再退回舊 claude heuristic。avatar 改用 model 查表（claude🤖 / gemini💎 / codex🧠）。

### Why

多模型治理層（V3.7.0）後辯論配對可為任意兩 model，前端仍假設 claude 必為一方，
側別判斷失效。side 應為後端位置真相，前端不該用 model 名重算。

---

## [3.8.0] — 2026-05-19 — Break News 免費社群/趨勢源

### Added — Reddit / Bluesky / Hacker News / Google Trends 探勘層

Break News 原本只有正式新聞 RSS + Futu 推播，缺少市場題材早期發酵訊號。本版新增
免費低摩擦 source adapter，保持探索層定位，不影響 investment protocol 決策。

- **`scripts/break_news/social_sources.py`** 新增 normalized adapters：
  Reddit subreddit RSS、HN Algolia、Google Trends RSS；Bluesky public search adapter 保留，
  但因目前 public endpoint 回 403，預設關閉，可用 `BREAK_NEWS_BLUESKY_ENABLED=1` 測試。
- **`poller.py`** 接入 `BREAK_NEWS_SOCIAL_ENABLED`，社群/趨勢來源會進未閘 Raw 流；
  自動辯論需通過較高的 `BREAK_NEWS_SOCIAL_GATE_MIN_SCORE`，避免社群雜訊吃掉每日預算。
- **source metadata** 寫入 raw entry：`is_social` / `source_meta`，Dashboard 現有 raw 卡可直接顯示來源標籤。
- **可觀測性**：poller state 新增 `items_added_social`、`social_enabled`、`feed_stats`。

### Deferred

X、Stocktwits、Product Hunt 暫不接入：X 為 pay-per-use；Stocktwits 新 app 註冊暫停；
Product Hunt 需 token 且有商用限制。保留為 optional adapters。

---

## [3.7.1] — 2026-05-18 — Break News 辯論獨立配對（codex review fix）

### Fixed — Break News 辯論改用自己的兩模型配對

V3.7.0 的治理層讓 Break News debater 與通用路由共用同一組 primary/secondary —
改 dashboard 設定會同時動到兩邊。codex code review 指出此漏洞,本版修正:

- **`config/llm_config.json`** 新增 `break_news: {primary, secondary}` 區段 —
  Break News 辯論的 A/B 兩位辯手,獨立於通用 primary/secondary/tertiary 鏈。
- **`llm_drivers.py`** — `load_llm_config()` 解析 `break_news`;新 helper
  `break_news_pair()`。`debater.py` `_turn_order()` 改讀此區段。
- **`POST /api/llm-config`** 接受 `break_news` 區段(merge,不影響通用設定)。
- **sidebar 設定面板** 加「突發辯論配對」子區:辯手 A / 辯手 B 兩個下拉,與
  通用 主要/次要/備援 分開。
- **辯論身分標籤修正** — debater turn 若 fallback 換了模型,改用實際模型
  (`res.model_used`)重貼 role label,避免「Analyst-A (Claude)」卻存成 gemini。
  side A/B 仍為位置固定。

### Why

Break News 的 Claude×Gemini 刻意分歧是核心設計,需要跟供應鏈 / 協定路由解耦 —
獨立配對讓使用者單獨調辯論雙方,不波及通用 fallback 鏈。

---

## [3.7.0] — 2026-05-18 — 多模型治理層（claude / gemini / codex）

### Added — model_router governor:角色路由 + 預算 + quota 自動降級

3 個模型 CLI(claude / gemini / codex)過去各自為政:無 fallback(debater 連 2
次 CLI 失敗直接 abort)、無預算/quota 感知、協定寫死 claude。claude 額度一用完,
趨勢圖 / 辯論 / 協定全停。

- **`scripts/_shared/model_router.py`(新)** — 治理層。`run_role()` /
  `run_with_fallback()` 走 fallback 鏈(primary → secondary → tertiary),跳過
  停用 / 超預算 / quota cooldown 的模型,失敗或撞 quota 自動降級。
  `config/llm_usage.json` 記每模型每日呼叫數 + cooldown(UTC 日界自動重置)。
  quota 偵測 = best-effort 比對 CLI 錯誤/stdout 的 rate-limit/429/quota 字樣 →
  該模型進 `cooldown_hours` 冷卻。`model_status()` 給 dashboard。
- **`config/llm_config.json` 擴充** — 加 `tertiary` / `enabled` / `budgets`
  (每模型 `daily_max_calls`)/ `cooldown_hours`。舊 `{primary,secondary}` 仍相容。
  `llm_drivers.load_llm_config()` 改回傳完整治理 config + `model_chain()`。
- **消費者接governor** — break-news `debater.py`(每回合 `run_with_fallback`,
  模型掛了自動換,不再整場 abort)、`supply_chain.py generate()`(`run_role`)。
- **協定路由** — `dashboard_server.run_protocol()` 改用 `model_router.pick_model()`
  選模型(claude 優先,gemini/codex 只在 claude 超額/冷卻時頂上),per-model
  指令建構器(`_protocol_command`),跑完 `note_run()` 記帳 + quota cooldown。
- **dashboard** — `GET /api/llm-config` 回傳 config + 即時 `model_status`;
  `POST` 接受擴充 schema(merge 不覆蓋 budgets);sidebar 設定面板加備援 LLM
  下拉 + 每模型 `calls/daily_max` + 冷卻/額度滿標示。Codex 選項解鎖。

### Why

claude quota 一掛全系統停擺。治理層讓三模型有統一的角色路由、每日預算、quota
自動降級 — 一個模型用完,工作自動流到下一個,不中斷。

---

## [3.6.3] — 2026-05-18 — 情緒趨勢圖：線寬 / 字級不隨寬度爆掉

### Fixed — 寬螢幕上線太粗、x 軸字太大且重疊

`trend-chart.js` 的 SVG viewBox 固定 760 寬,圖以 `width:100%` 撐滿 → 在寬容器
(~2000px)上整體放大 ~2.6×:`stroke-width:1.6` 變 ~4px、SVG `<text>` font 9
變 ~23px,且相鄰日期標籤互相重疊。

- **線**:所有 stroke 加 `vector-effect="non-scaling-stroke"` → 線寬恆為固定
  px(設 1.3),不隨縮放變粗。
- **x 軸 / 「現在」標籤**:從 SVG `<text>` 改為 HTML overlay span(`.trend-xaxis`
  / `.trend-xlabel` / `.trend-nowlabel`)→ 字級固定 9px / 8px,不隨 viewBox 縮放。
- **重疊**:日期標籤碰撞檢查 — 與前一個標籤距離 < 8% 就略過(分隔線仍畫)。
- now 圓點 r 2.8→2.2。

### Why

SVG viewBox 縮放會等比放大 stroke 與 `<text>`;在寬版面上線與字都失控。線用
non-scaling-stroke、文字改 HTML overlay 後,兩者皆為固定 px,任何寬度都一致。

---

## [3.6.2] — 2026-05-18 — 情緒趨勢圖 x 軸可讀性優化

### Changed — `Dashboard/trend-chart.js` x 軸改為按日分界

舊 x 軸把 4 個 tick 放在任意 1/3 位置 → 標籤落在隨機小時(`5/15 18h`、`5/16 18h`、
`5/17 17h`),小時是雜訊、最右標籤被裁掉、看不出日界。

- **按日分界**:走訪 `series_labels` 偵測本地午夜,每個日界畫一條極淡垂直分隔線
  + 標「日期 + 星期」(`5/16 六` / `5/16 Sat`)。新 helper `_dayTicks()` / `fmtDay()`。
- **參考格線**:±0.5 格線由 `rgba(255,255,255,0.05)`(淺色主題下白底白線看不見)改為
  theme-safe `rgba(128,128,128,0.12)`。
- 修正最右標籤裁切(估寬後 clamp 進繪圖區)。
- 最新點旁加極淡「現在 / now」標記。`padB` 16→20 給日期標籤留白。
- hover tooltip 時間格式 `13h` → `13:00`。

### Why

使用者反映 `5/15 18h` 很難看懂。按日分界 + 星期讓 3 日結構一眼可讀,且能看出
週末(低新聞量)。維持低調風格 — 線條 / 顏色 / 資料不變,只動軸與格線。

---

## [3.6.1] — 2026-05-18 — sector 協定 turn-bloat 重構

### Fixed — `產業掃描` 33 分 / 52 turn → 預期 ~20-25 turn

2026-05-18 一次 sector run 跑 33 分(52 turns)被 30 分 timeout 砍 — 但其實**已成功**
(rc=0、artifact 有效)。診斷:不是 429、不是子代理 — 是 parent agent turn 太碎:
手寫整個 15+ key 巢狀 `sector_intel.json`(實際還寫 `/tmp/build_intel.py` Edit ×2)、
逐檔 `python3 -c` peek cache、validator retry loop。

把機械組裝從 LLM 移進 committed 腳本:

- **`sector/scripts/build_sector_intel.py`(新)** — 從 phase cache + 一個精簡
  LLM-authored decision JSON 確定性組出完整 `sector_intel.json`。模型只寫判斷欄位
  (`sector/cache/sector_decision_<DATE>.json`),腳本自動填 `_phase0` / `_phase1`
  / `_phase3` / metadata / `_phase4c`。輸出設計上即過 `validate_sector_intel.py`
  → 消滅 validator retry loop。decision JSON schema 見腳本檔頭 docstring。
- **`sector/scripts/sector_digest.py`(新)** — 一次印出 macro header + 11-sector
  決策表(uptrend / PE / z-score / RS / theme heat / news / smart-money / beat
  rate),取代逐檔 ad-hoc peek。
- **協定 MD 改寫** — `phase_1-2-3.md`(不再手抄 valuation / earnings_pulse /
  smart_money 進 JSON)、`phase_4-5.md`(Phase 5 改「寫 decision JSON → 跑 build
  script」;Phase 4a 並行 launch 升級為硬規則 + 違規警告)、`sector_protocol_main.md`
  GLOBAL RULE 7、`phase_0.md` / `schema.md` 指向新腳本。
- **`SECTOR_TIMEOUT_SEC`** 1800 → 2700(45 分)— 慢但成功的 run 不再被砍。

### Why

慢的根因是 parent agent 步驟太碎;把 JSON 組裝與 cache 讀取交給確定性腳本後,模型
只做真正的分析判斷,turn 數大幅下降,也不再因手寫 JSON 不合 schema 而重試。

---

## [3.6.0] — 2026-05-18 — 可設定主要/次要 LLM(server config + sidebar 設定面板)

### Added — server-side LLM config

LLM CLI 選擇過去全 hard-code(`run_claude`/`run_gemini`、debater `TURN_ORDER`、
`supply_chain.generate`)。新增可設定的主要 / 次要 LLM。

- **`config/llm_config.json`(新)** — `{"primary":"claude","secondary":"gemini"}`。
  Server-side 檔(Python script 讀得到;localStorage 只在瀏覽器,scripts 讀不到)。
- **`scripts/break_news/llm_drivers.py`** — 新 `run_codex` graceful stub(codex CLI
  尚未接線,回傳 rc=1 LLMResult,不會 crash 呼叫端);`_RUNNERS` registry +
  `run_llm(model, …)` dispatcher;`load_llm_config()` / `primary_model()` /
  `secondary_model()`。

### Added — sidebar LLM 設定面板

- `dashboard_server.py` — `GET/POST /api/llm-config`(POST 驗證 ∈ {claude,gemini,codex},
  寫回 config 檔)。
- `Dashboard/utils.js` `renderSidebar()` footer — 可展開「⚙ 設定」面板:主要 / 次要
  LLM 下拉(Codex 為 disabled「即將支援」),change 即 POST + toast。`style.css` 加
  `.sidebar-settings` 等樣式。

### Changed — generation / debate 走 config

- `scripts/nexus/supply_chain.py` — `generate(theme, agent=None)`:未指定 agent 時
  用設定的 primary;新 `--agent claude|gemini|codex` CLI 旗標(納入 Gemini 的建議,
  泛化為讀共用 config)。`generated_by` 反映實際模型。
- `scripts/break_news/debater.py` — `TURN_ORDER` 改由 `load_llm_config()` 在每場
  辯論開始時解析為 `[primary, secondary]`,config 缺失時 fallback claude↔gemini。

### Why

使用者要能切換 LLM CLI,且次要 LLM 供辯論 / 未來 review 用。預設 config 與舊行為
完全一致(零回歸)。Codex 預留:stub + disabled 選項,日後填 CLI flags 即可啟用。
另註:Gemini 建議中的「bridge.py 即時新聞」項已過時略過 — `extract_shallow_news`
於 v3.4.0 移除,即時 raw 新聞已是 break-news「未閘 Raw 流」(v3.3.2)。

---

## [3.5.3] — 2026-05-18 — heatmap 429 熔斷器

### Fixed — heatmap 背景刷新狂噴 HTTP 429

`heatmap_refresh_loop`(常駐背景 daemon,與是否開啟 heatmap 頁無關 — 負責把
`heatmap.json` 保溫)在美股盤中每 `HEATMAP_REFRESH_SEC`(10 分)就 fan-out
~517 個 FMP `stable/quote` 單檔呼叫(20 workers)。FMP 方案撐不住 → 全部回
429,每輪在 log 噴 ~500 行 `[heatmap] HTTP error: 429`。

加 **429 熔斷器**(`dashboard_server.py`):

- `_fmp_get_json` 收到 429 → 設 `_heatmap_ratelimit_until = now + 1800`(30 分
  冷卻),且**只在首次跳閘時 log 一行**(原本每通呼叫各噴一行)。
- `_heatmap_refresh_quotes` / `_heatmap_refresh_pe_universe` 開頭檢查熔斷器,
  冷卻中直接跳過整批 fan-out(各只留一行 `skip … cooldown`)。
- fan-out 內 `_fetch_one` / `_fetch_pe_ttm` 逐一檢查熔斷器 — 跳閘後排隊中的
  symbol 直接略過,不再實際打 API。

效果:429 風暴從「每 10 分 ~500 行」降為「每 30 分冷卻窗 ~1-2 行」。冷卻期間
heatmap 用既有 `heatmap.json` 快取,過後自動重試。

### Why

背景保溫迴圈無 rate-limit 處理 → 一被限流就無腦重打 + 洗版 log,既吵又浪費
配額。熔斷器讓它限流時安靜退避。

---

## [3.5.2] — 2026-05-18 — 供應鏈節點卡 UI 修正

### Fixed — 卡片重疊 / 溢出類別框 / badge 語言不一致

供應鏈圖節點卡有三個問題:

- **卡片重疊 + 溢出 module 框** — 卡片用 `min-height: NODE_H`(68px),但 2 行
  role 文字 + badge 列實際把卡撐到 ~90px+;佈局卻以固定 68px 間距排版 →
  卡片互相重疊、並超出所屬 module 子面板。改:卡片改**固定** `height`,
  `NODE_H` 拉到 100;`.sc-role` 設 `flex:1`(吸收空隙)、`.sc-badges`
  `flex-shrink:0`(錨在底部)。卡片等高 → 間距一致、面板尺寸精準。
- **badge 中英不一致** — `grounding` / `heat` badge 顯示原始 enum
  (`LLM_ONLY` / `VERIFIED` / `WARM`),中文頁面也顯示英文,與圖例
  (追蹤中 / 有資料 / 僅 LLM)對不上。新增 `groundingLabel` / `heatLabel` /
  `listingLabel` 隨頁面語言切換;節點卡 + detail panel 全部本地化。
- **節點卡加寬** — `NODE_W` 174 → 198,減少公司名稱過度截斷
  (「NTT Innovativ…」等)。

### Why

固定卡高是讓兩層佈局(stage → module → node)間距精準、不重疊的前提;
badge 跟著頁面語言走才不會中英混雜。

---

## [3.5.1] — 2026-05-18 — 供應鏈圖例 hover 說明

### Added — 圖例 pill hover tooltip

供應鏈頁底部 9 個圖例 pill(US 上市 / 外股 / 擬上市 / 私有 / 追蹤中 / 有資料 /
僅 LLM / 熱度 / 商用階段)過去無說明。沿用 `sector.html` 的 pill tooltip 模式
(`#pill-tooltip` + `data-tip-key` + `tip-title/desc/scale`),hover 跳出標題 +
解釋 +(熱度 / 商用階段)等級說明。

- `supply-chain.html` — `#pill-tooltip` CSS + 元素;每個 `.sc-legend-item` 加
  `data-tip-key` + `cursor:help` + hover 邊框。
- `page-supply-chain.js` — `SC_PILL_TIPS`(zh/en × 9 項)+ `initPillTooltip()`
  (mouseover/out 委派、量高後翻轉定位,與 sector 一致)。

### Why

圖例符號無說明時使用者得猜;一致的 hover 說明讓 grounding / 熱度 / 商用階段的
語意一看就懂。

---

## [3.5.0] — 2026-05-18 — 供應鏈：商用化階段 stage 標記層 + 生成完整度

### Added — node 級 commercialization-stage 標記

供應鏈鏈圖過去無法表達「誰會先變 revenue customer」。新增 node 級 `stage` 欄,
值域 `design_partner → sampling → qualification → production → revenue`(+ `unknown`)。

- **`scripts/nexus/supply_chain.py`** — 新 `_STAGES` enum;`_normalise()` 保留並
  驗證 node `stage`,非法值 → `unknown`。
- **`prompts/supply_chain_system.md`** — node schema 加 `stage`;指示 LLM 僅在有
  公開證據時標,否則 `unknown`(高精度時效資訊,使用者再編 YAML 校正)。
- **`Dashboard/page-supply-chain.js`** — `STAGE` 色階(design 灰→sampling 藍→
  qual 黃→production 橘→revenue 綠);node 卡 badge + 詳情面板「商用階段」列。
- **`Dashboard/supply-chain.html`** — `.sc-stage` badge CSS + 圖例階段色階。

### Changed — 提高 LLM 生成完整度

供應鏈公司清單 100% 來自 LLM 草稿(專案 DB 不參與選公司)。原 prompt 硬上限
8–20 node + 「omit rather than guess」壓制廣度 → 量產 OEM / 客戶層常漏。

- `prompts/supply_chain_system.md` — node 上限 8–20 → 12–32;模塊 2–3 → 2–4;
  「omit rather than guess」限縮到上游 materials/IP 層;OEM 層 + 客戶/系統層
  改為要求合理完整(列出主要量產 OEM/ODM 與主要 hyperscaler 客戶)。

### Changed — POET 供應鏈鏈圖擴充

`nexus/supply_chains/poet.yaml` 由 20 node 擴為 27:補 NTT Innovative Devices、
Credo、Luxshare、Foxconn Interconnect、ASE、Google、AWS,並對每個 node 標 `stage`
(保守:5 design_partner / 2 production / 其餘 unknown,待手動校正)。新增
`advanced_packaging` 模塊。

### Why

外部檢討指出 POET 鏈缺量產 OEM/客戶且無「商用化階段」標記層 — 後者比塞更多
公司更有投資價值。診斷確認缺公司是**生成/分析缺口**(LLM 草稿被 prompt 上限與
保守規則壓制),非資料量不足:DB 從不參與選公司,只做事後 grounding。stage 層
讓鏈圖能標出 POET 股價催化路徑。

---

## [3.4.1] — 2026-05-17 — 供應鏈：stage 內模塊分組 + 邊線修正

### Added — 每個 stage 分 2-3 個產業模塊

供應鏈的 stage 過去是扁平一欄,使用者要求把同一 stage 分成 2-3 個產業模塊
(如 `silicon` → CPU / GPU加速器 / 記憶體 / 網通)。

- **資料模型** — YAML 新增 `modules: {layerId: [{id,label}]}`,每個 node 加
  `module` 欄。`supply_chain.py` `_normalise()` 解析 modules、驗證 node.module
  ∈ 該層模塊;舊 YAML 無 modules → 隱式單一 `_default`(向後相容)。
  生成 prompt 要求 LLM 每層產出 2-3 模塊並指派每個 node。
- **佈局** — `page-supply-chain.js` `layout()` 改兩層:stage 欄內以 module
  子面板垂直堆疊,欄頂對齊。`renderDiagram()` 畫帶框 `.sc-module` 子面板 +
  標籤;stage band 弱化為虛線外框,模塊面板成為視覺主體。
- 已重生 `cpo/hbm/openai/spacex` 四條鏈帶入模塊結構。

### Fixed — 供應鏈邊線兩個 bug

- **隱形 spine 線** — spine 邊共用一個 `objectBoundingBox` 漸層;邊完全水平時
  (兩端同 y)bounding box 高度 0 → 漸層退化 → stroke 不顯示,只剩會動的粒子
  (openai 鏈 `nvidia→microsoft`)。改 per-edge `userSpaceOnUse` 漸層,絕對
  座標不退化。
- **同 stage 邊鼓圈** — 同層兩 node 的邊原本從右緣拉出又繞回同欄,在區塊內鼓
  醜圈。新增 `sidePath()`:同欄邊改走欄位右側的 C 形連接器(細、虛線、低調),
  不穿過區塊。

### Why

把產業分好讓供應鏈一眼看出結構;邊線修正讓主流向乾淨可讀。

---

## [3.4.0] — 2026-05-17 — 新聞層整併 + 情緒趨勢上首頁 + 供應鏈佐證

### Changed — 移除 news.html Triage tab(消除冗餘的「未辯論新聞」第三面)

`news.html` 過去有 3 個未辯論新聞清單之一的 Triage tab(讀 `bridge.py
extract_shallow_news()`),與 break-news 的「未閘 Raw 流」重複,使用者少用。

- 移除 `news.html` 🗂 Triage tab + `#news-triage-feed`。
- `page-news.js` 刪 `renderTriageFeed()` / `wireTriageButtons()` / triage filter 分支(~270 行)。
- `bridge.py` 刪 `extract_shallow_news()` + `data["shallow_news"]`(`_raw_pub_map` 保留,`extract_news` 仍用)。
- `news.html` = 純委員會深度 digest;break-news「未閘 Raw 流」= 唯一未辯論新聞面。
- `triage` 協定本身保留(`新聞分析 TRIAGE` 文字指令仍可用),只移除 dashboard 按鈕。

### Added — 情緒趨勢圖抽成可重用 module + index.html 首頁精簡 widget

- **`Dashboard/trend-chart.js`(新)** — `window.TrendChart` module:`mount({root, compact,
  withSelector})`。自帶 CSS(注入 `<style id="trend-chart-css">`)+ i18n + 30s 共用 fetch
  cache。`compact` 模式只畫市場整體線、92px 矮圖、無 entity 選擇器。
- `page-break-news.js` / `break-news.html` 改用 module(完整模式:選擇器 + legend + hover)。
- `index.html` `#risk-overview` 下方新增精簡趨勢卡(連往 break-news.html),`script.js` boot 掛載。

### Added — 委員會 digest verdict 餵入情緒趨勢指數

`trend_rollup.py` `compute_trends()` 過去只讀 `bn_*.json`。現在也讀
`news_logs/*_digest.json`:deep verdict 權重 ×1.8、shallow ×1.0;以 headline
fingerprint 對 break-news 去重(digest 品質高者勝)。趨勢指數現反映委員會層。

### Added — 供應鏈邊「知識圖譜佐證」

`supply_chain.py` `enrich()` 新增讀 `nexus_graph.json` 的 ticker↔ticker **edges**
(已含 break-news 辯論抽出的 SUPPLIES_TO / BENEFITS_FROM 等關係)。每條 LLM 草擬
的供應鏈邊標 `corroboration`(佐證來源數 + nexus 關係型別 + sources)。
`page-supply-chain.js` 邊列加 `✓N` 綠色 badge。

### Why

新聞層有兩條平行 pipeline(委員會 digest / break-news 探索),Triage tab 是第三個
冗餘未辯論清單。整併後職責清楚:digest = 深度委員會、break-news raw 流 = 即時全量。
趨勢圖上首頁讓使用者快速一覽市場情緒;餵入 digest 讓指數涵蓋最深一層分析。
Nexus 早已吃 break-news 實體/關係 — 供應鏈佐證讓 LLM 草擬的價值鏈能被真實辯論交叉驗證。

---

## [3.3.2] — 2026-05-17 — Break News 未閘 Raw 流 + 手動辯論觸發

### Added — un-gated raw breaking-news stream on `break-news.html`

突發辯論室過去只顯示過了 score gate(`|shallow_score| ≥ 2`)的自動辯論項。
冷門時段(週末/盤後)沒新聞過閘 → 頁面空窗看似停擺。此版加一條**未閘 raw 流**:
poller 抓到的**全部** RSS 項(過閘 + 未閘)都進 `_raw_stream.json`,UI 即時呈現,
每則可手動「🔥 辯論」繞過 gate 升級成辯論項。

- **`scripts/break_news/store.py`** — 新 `RAW_STREAM_FILE` + `load_raw_stream()` /
  `save_raw_stream(cap=150, max_age_h=24)`(atomic、key dedupe、汰 24h、保留既有
  `news_id` promotion)/ `mark_raw_promoted(key, news_id)`。
- **`scripts/break_news/poller.py`** — `run_once` loop 對每則非重複 item 收集 raw
  entry(headline / source / score / gate 結果 / 完整 triage / `key` / `news_id`),
  poll 末 merge 寫 `_raw_stream.json`。bn-creation 上限由 `break` 改 `continue` —
  raw 捕捉不受 `MAX_ITEMS_PER_CYCLE` 截斷。state 加 `raw_stream_size`。
- **`dashboard_server.py`** — `GET /api/break-news/raw-stream?limit=N`;
  `POST /api/break-news/raw/debate`(body `{key}` → 查 entry → `init_item` 繞閘 →
  `pending_debate` + 背景 `_bn_kick_debate_scan` 立即起辯論)。
- **`Dashboard/break-news.html` + `page-break-news.js`** — trend strip 與雙欄之間
  插可收合「未閘 Raw 流」面板:每卡片 score badge / 過閘狀態 / age / 來源 +
  「🔥 辯論」鈕。`loadRawStream()` 納入 poll cycle。

### Why

冷門時段 break news 頁空窗,使用者以為壞了。Raw 流提供「全量可視 + 手動升級」
旁路 — score gate **保留**(自動辯論門檻不變),raw 流純探索層展示,不進
investment_protocol 決策。

---

## [3.3.1] — 2026-05-17 — Supply-Chain page visual polish

### Changed — frontend-design pass on `/supply-chain.html`

V3.3.0 shipped the page functional but visually weak. This pass aligns it to the
dashboard design system and turns the layered diagram into a polished centerpiece.

- **Dual-theme fix** — node cards hardcoded `rgba(24,24,27,…)` (dark only); now
  use `var(--bg-card)` / `color-mix()` tokens → light theme works.
- **Controls** — plain box → `.ea-cmdbar`-style command bar with `>` prompt
  glyph, mono theme input, `focus-within` emerald glow, mono Generate button.
- **Canvas** — dotted-grid backdrop; each layer = a tinted band column with a
  numbered header chip so upstream→downstream structure reads instantly.
- **Edges** — flat grey → spine edges get an emerald→amber gradient stroke +
  animated flow particles (`<animateMotion>`) travelling upstream→downstream.
- **Node cards** — gradient listing-color accent stripe, heat → outer glow
  (hot red / warm amber / cold blue), hover lift, staggered reveal animation,
  badges restyled to the 9–9.5px uppercase-pill convention.
- **Detail panel** — polished floating card with listing-color header stripe +
  styled upstream/downstream edge rows. Legend → clean pill row.

### Why

User found the page's colours off and the diagram flat. Visual quality matters
for a tool meant to be explored; the bold treatment (flow animation, layer
depth, heat glow) makes the supply chain legible at a glance.

---

## [3.3.0] — 2026-05-17 — Supply-Chain Explorer

### Added — theme-keyed US supply-chain maps on a new `/supply-chain.html` page

User found the Nexus knowledge graph (`/graph.html`) too messy (800 nodes /
3895 edges, `MENTIONED_IN` = 50% = hairball) and wanted instead to *explore
US-stock supply chains by theme* — e.g. the CPO (co-packaged optics)
upstream→downstream value chain. Nexus can't serve this: directional
supply-chain edges are absent (count 0) and private/foreign players never
enter the graph at all.

New separate **Supply-Chain Explorer** — LLM drafts the chain, existing data
grounds it, a clean layered diagram renders it. Nexus auto-graph untouched.

- **`scripts/nexus/supply_chain.py`(新)** — `generate(theme)` calls Claude (via
  reused `scripts/break_news/llm_drivers.py` `run_claude`) with
  `prompts/supply_chain_system.md` → drafts ordered layers, companies (honest
  `listing`, real tickers only), directional edges, a `spine` → saved as
  editable YAML in `nexus/supply_chains/<slug>.yaml`. `enrich()` adds live
  per-node `grounding` (verified = in `heatmap_universe.json` / seen = in
  `nexus_graph.json` / llm_only) + `heat` (from Nexus mention counts).
  `nexus_themes()` exposes Nexus theme/narrative labels as quick-picks.
- **`dashboard_server.py`** — `GET /api/supply-chain/{list,themes,<slug>}` (60s
  TTL cache) + `POST /api/supply-chain/generate {theme}` (synchronous LLM draft).
- **`Dashboard/supply-chain.html` + `page-supply-chain.js`(新)** — layered
  upstream→downstream diagram: each layer = a column, nodes = HTML cards over an
  SVG edge layer, directional bezier arrows, spine highlighted. Per-node badges:
  可投資性 (listing 色條) · 資料支持度 (grounding ✓◦⚠) · 供應鏈層級 (column) ·
  近期熱度 (heat dot). Chain selector + theme free-text/quick-pick + 生成 button.
  Node click → detail panel (role / upstream / downstream).
- **`utils.js` + `i18n.js`** — `供應鏈` sidebar nav entry (portfolio group).
- Seeded `nexus/supply_chains/cpo.yaml` (18 companies, 5 layers, 21 edges).

### Why

User wants to *know* supply chains, not untangle a log-derived hairball. LLM
drafts breadth fast; grounding against existing universe/Nexus data flags which
nodes are tradeable vs unverified LLM claims. Editable YAML accumulates a
reviewed library. Nexus stays the exploration layer — this is the curated view.

---

## [3.2.0] — 2026-05-15 — Break News 3-day sentiment-trend chart

### Added — rolling sentiment-index trajectory on break-news.html

突發新聞辯論室的辯論 log 過去是孤立快照,看不出敘事「方向」隨時間怎麼演化。
此版把每則 debate 當成帶正負號的事件,經時間衰減 EMA 串成一條情緒指數軌跡,
呈現在 `break-news.html` 頂部全寬面板:單一大圖 + 實體選擇器。一次畫一條線
(市場整體 / 某產業 / 某主題),避免多線疊圖糾纏。

- **`scripts/break_news/trend_rollup.py`(新)** — `compute_trends()` 唯讀掃
  `news/break_news_logs/bn_*.json`,只取 closed/partial_closed。
  - 每則 log = 事件:`sign` = BULLISH +1 / BEARISH −1 / NEUTRAL·SPLIT 0;
    `weight` = impact(`triage.shallow_score`/4,clamp 0.25–2.0)× 來源可信度
    (HIGH 1.0 / MED 0.7 / LOW 0.4);`貢獻 = sign × weight`。
  - 72 個每小時 bucket(3 日窗,直接走 UTC),時間衰減 EMA
    `S = S_prev × decay + Σ貢獻`,`decay` 由 12h half-life 推導。
  - 顯示值 = `tanh(S / scale)`,scale 為**每實體自適應**(該實體 peak 對應
    ~0.9,floor `_MIN_SCALE`)→ 每條線都用滿 [−1,+1],無新聞時自然衰回 0。
  - 實體層級:市場整體(全 log)/ 各 sector / 各 theme(theme 走輕量
    `ALIAS_MAP` 正規化)。sector/theme 需 ≥3 事件才可選,各 cap top 12。
- **`dashboard_server.py`** — 新 GET `/api/break-news/trends`,60s TTL cache
  (`_bn_trend_cache`),共用 `BREAK_NEWS_AVAILABLE` guard。
- **`Dashboard/break-news.html` + `page-break-news.js`** — 頂部 `.bn-trend-strip`
  面板:`<select>` 實體選擇器(optgroup 分 市場/產業/主題)+ 手刻 SVG area
  chart(零基線、綠上紅下填色 clipPath、4 個時間軸刻度)+ 即時數值讀數 +
  hover 游標(任一時點的時間與分數)。切換實體不重 fetch(所有 series 同
  payload)。隨既有 30s poll loop 更新。

### Why

使用者要的是「根據每次收到的新聞修正當下趨勢往上或往下」— 一條會穿越 0、隨
利多利空演化的軌跡,而非靜態的提及量排行。EMA 時間衰減讓指數有記憶但會遺忘,
符合「漂亮時高、利空連發跌破 0、無新聞慢慢衰回 0」的直覺。維持探索層紀律:
trend 面板不進 investment_protocol 決策。

---

## [3.1.2] — 2026-05-14 — Break News side-panel synthesis + categorized entities

### Added — bull/bear bullet synthesis + grouped entity sections + graph linkage

User feedback on V3.1.1 side panel (screenshot): `合議摘要` only showed
verdict enum + flat entity chip dump, no written bull/bear/conclusion and no
visible link to the knowledge graph. This release fixes all 3 with zero extra
LLM calls (schema extended on the existing per-turn JSON response).

- **`scripts/break_news/prompts.py` — schema additions**
  - `SYSTEM_PROMPT` now requires `bull_points: [str ≤3]`, `bear_points: [str ≤3]`,
    `final_take: str` (≤30字繁中) per agent response. Each side must give at
    least 1 point (forces balanced view even when agent leans strongly).
  - `build_summary_block` extended: returns `bull_summary[]`, `bear_summary[]`,
    `final_take`, `final_take_by`. Bull/Bear bullets merged across both agents
    with `_rough_dedup` using Jaccard ≥ 0.6 over zh-aware char-level tokens.
    `final_take` taken from latest comment with a non-empty value.
- **`Dashboard/news_components.js`**
  - New `renderEntityChipsGrouped(entities)` — 4 labeled sections with header
    + count badge (🏢 個股 / 🏭 產業 / 🔥 主題 / 🔬 技術節點) instead of
    flat chip dump. Lang-aware labels via `currentLang()`.
  - New `entityTotal(entities)` — `{tickers, sectors, themes, tech_keywords, total}`
    counts used by graph footer.
  - Existing `renderEntityChips` (flat) kept for per-comment thread bubbles.
- **`Dashboard/page-break-news.js:renderDetail`** — rewrite of summary panel:
  - Verdict header w/ rounds + close reason
  - 🎯 最終結論 line (with agent attribution)
  - 分歧 (divergence) line if predicates diverge
  - ✅ 正方意見 bullet list (green left-border accent)
  - ❌ 反方意見 bullet list (red left-border accent)
  - 🧩 萃取實體 categorized chip sections
  - 🌐 知識圖譜入口 footer: catalyst node id, edge counts, graph_status,
    link to `/graph.html`
  - Placeholder block for items still in `debating` / `pending_debate` state

### Backward compatibility

Old `bn_*.json` files without `bull_points` / `bear_points` / `final_take`
render gracefully: bull/bear sections suppressed, only verdict + entities
appear (same as V3.1.1). Replay (`⟳ 重跑`) regenerates with new fields.

### Verification

```bash
ITEM=$(ls news/break_news_logs/bn_*.json | head -1 | xargs basename | sed 's/.json//')
python3 -c "from scripts.break_news import store; store.set_state('$ITEM', 'pending_debate')"
python3 scripts/break_news/debater.py --news-id "$ITEM" --max-rounds 1 --verbose
jq '.summary | {consensus_verdict, bull_summary, bear_summary, final_take, final_take_by}' \
   news/break_news_logs/$ITEM.json
open http://localhost:8080/break-news.html   # side panel: bull/bear bullets + grouped chips + graph footer
```

---

## [3.1.1] — 2026-05-14 — Break News + Futu push channel

### Added

- **Futu 牛牛 push** as a second break-news source alongside the 9 RSS feeds.
  Pre-filter is strict: US ticker required, no HK/A-share, no ads/clickbait.
  Pushes feed `scripts/break_news/poller.py` via new
  `scripts.parse_futu_notifications.load_for_break_news(window_hours, max_items)`.
- `scripts/parse_futu_notifications.py`:
  - `_AD_HARD_KEYWORDS` — 富途早晚報 system notices, 開戶 / 贈金 promos,
    直播 / 課程 / 牛友圈 educational ads, 立即下載 / 掃碼 CTAs
  - `_HOWTO_PATTERNS` — `如何...？` / `教你...` / `一文讀懂...` clickbait regex
  - `_is_ad(text)` — predicate used by poller via `filter_ads=True`
  - `load_notifications(filter_ads=, require_us_ticker=, ...)` — backward
    compat; both flags default False so existing `/api/futu-notifications`
    endpoint behavior unchanged
  - `load_for_break_news()` — emits items in `fetch_news_rss.fetch_feed`
    shape (`headline, url, raw_summary, source="Futu Push", credibility="MEDIUM",
    published, _fp, _dt, tickers`)
  - `_futu_fingerprint(headline, tickers)` — sha1-based fp that survives zh-CN
    text (the RSS `headline_fingerprint` only keeps `[a-z0-9]` tokens, which
    collapsed every Futu zh push to "" or "20" → false dedupe)
- `scripts/break_news/poller.py`:
  - Lazy `import scripts.parse_futu_notifications as _futu`
  - `fetch_fresh_items()` merges Futu items with RSS items, time-window cutoff
    applied uniformly, dedupe ranks by credibility tier (HIGH > MEDIUM > LOW)
    and prefers non-Futu on tie (real URL beats synthetic `futu://`)
  - `run_once()` — Futu items skip the English-keyword score gate (would
    mis-score zh text) with `advance_reason="futu_news"`. Daily cap + per-cycle
    cap unchanged.
  - New counters: `items_added_futu`, `futu_enabled` in `_state.poller`
- Env vars: `BREAK_NEWS_FUTU_ENABLED` (default `1`),
  `BREAK_NEWS_FUTU_MAX_PER_CYCLE` (default `30`)

### Why

User explicitly asked: 「futu 牛牛的推播也要放入辯論, 美股限定, 中股港股不用,
廣告也不用, 新聞限定」. Futu push 是 zh-CN 速報，常比 RSS 早 5-30 分鐘出
（券商直連 Reuters/Bloomberg wire），加進辯論池可增加新聞覆蓋的及時性。

### Verification

```bash
python3 -c "from scripts.parse_futu_notifications import load_for_break_news; \
  items, stats = load_for_break_news(window_hours=6); print(stats); \
  [print(f'  [{\",\".join(i[\"tickers\"])}] {i[\"headline\"][:80]}') for i in items[:5]]"
python3 scripts/break_news/poller.py --once
jq '.poller | {items_added, items_added_futu, futu_enabled}' news/break_news_logs/_state.json
```

---

## [3.1.0] — 2026-05-14 — Break News (RSS + Dual-CLI Debate Layer)

### Added — Continuous short-cycle news with Claude × Gemini debate

- **`scripts/break_news/`** — new module: RSS poller + Claude/Gemini CLI debate orchestrator
  - `store.py` — atomic JSON store at `news/break_news_logs/<news_id>.json`, per-id
    in-process locks, `_seen_index.json` dedupe (sha1 of url+headline fingerprint),
    `_state.json` poller/debater health, startup sweep that resets `debating` items
    older than 15 min back to `pending_debate`
  - `poller.py` — pulls all 9 RSS feeds via `news/fetch_news_rss.py` parsers,
    in-process triage via `stage1_triage.classify_news_type` + `calc_shallow_score`,
    gate `|shallow_score| ≥ BREAK_NEWS_GATE_MIN_SCORE` OR HIGH credibility + |s|≥1
    OR binary event; daily cap `BREAK_NEWS_DAILY_MAX_DEBATES`; flags `--once --dry-run`
  - `llm_drivers.py` — subprocess wrappers for `claude` (envelope `.result`) and
    `gemini` (envelope `.response`); 3-stage JSON extraction (fenced → whole →
    brace-balanced); raw stdout dump on parse failure; default Gemini model is
    `gemini-2.5-flash-lite` (pro/2.5-pro/flash hit RESOURCE_EXHAUSTED on free tier)
  - `prompts.py` — strict SYSTEM_PROMPT requiring single fenced JSON output with
    schema `{commentary, entities, relations, done, confidence}`; opener + follow-up
    user prompts; `build_summary_block` merges entities/relations across the thread
  - `debater.py` — state machine `pending_debate → debating → closed/partial_closed/failed`;
    alternates Claude (Analyst-A) and Gemini (Analyst-B); both must signal
    `done:true` or `<DONE>` in commentary to close; max 3 rounds (env-overridable);
    480s wall-clock budget; partial close on timeout. Flags `--news-id`, `--scan`,
    `--workers`
  - `validate.py` — schema lint for break_news_logs/*.json (rc=0/1)
- **`Dashboard/break-news.html` + `page-break-news.js`** — new `/break-news.html`
  page; vertical card stream + side panel with Claude/Gemini bubble thread, entity
  chips (tickers, sectors, themes, tech-keywords), consensus summary block, replay
  button per item. 30s polling for feed + state, 5s polling for selected item
  while still debating
- **`Dashboard/news_components.js`** — shared primitives: `renderNewsCard`,
  `renderScoreBadge`, `renderSourcePill`, `renderAgePill`, `renderStatePill`,
  `renderEntityChips`, `renderThreadBubble`, `escapeHtml`, `relTime`
- **`dashboard_server.py`** — 2 daemon threads (`break_news_poll_loop`,
  `break_news_debate_loop`) modeled on `refresh_loop`; 5 routes
  (`GET /api/break-news/feed`, `/item/<id>`, `/state`; `POST /refresh`,
  `/item/<id>/replay`); new `GEMINI_BIN` constant; startup sweep call;
  separate `_break_news_dispatch_lock` so debates don't block `_protocol_lock`
  (normal `分析/產業掃描/新聞分析` keep running)
- **`Dashboard/utils.js`** — new `break-news` NAV_ITEM in MARKET group;
  VERSION bumped to V3.1.0
- **`Dashboard/i18n.js`** — `nav.break_news` zh + en keys

### Changed

- `dashboard_server.py` — `PORT` now reads `DASHBOARD_PORT` env var (still defaults
  to 8080); enables running an isolated test instance on a different port

### Why

The daily DIGEST pipeline (`news/news_protocol_v2.md`) runs on user trigger
once per day and produces a single batched verdict file. Market-moving news
during the trading day was being missed. The new Break News layer pulls RSS
every 10 minutes and runs an automated Claude × Gemini debate per item;
divergence between the two models surfaces uncertainty that single-model
arbitration hides. Entities + relations extracted from each comment feed into
the Knowledge Graph (V3.0) as a new data source so 2nd / 3rd-order
relationships build up faster.

### Env vars

```
BREAK_NEWS_INTERVAL_SEC=600         # poll cadence (10 min)
BREAK_NEWS_LLM_TIMEOUT_SEC=180      # per CLI turn
BREAK_NEWS_THREAD_TIMEOUT_SEC=480   # whole debate wall-clock
BREAK_NEWS_PARALLEL=2               # concurrent debates
BREAK_NEWS_DAILY_MAX_DEBATES=30     # cost cap
BREAK_NEWS_MAX_ROUNDS=3
BREAK_NEWS_GATE_MIN_SCORE=2
BREAK_NEWS_GEMINI_MODEL=gemini-2.5-flash-lite
CLAUDE_BIN, GEMINI_BIN              # binary path overrides
DASHBOARD_PORT=8080
```

### Verification

```bash
python3 scripts/break_news/poller.py --once --dry-run
python3 scripts/break_news/poller.py --once
python3 scripts/break_news/llm_drivers.py --probe --agent claude
python3 scripts/break_news/llm_drivers.py --probe --agent gemini
python3 scripts/break_news/debater.py --news-id <id> --max-rounds 1 --verbose
python3 scripts/break_news/validate.py
curl http://localhost:8080/api/break-news/state | jq .
curl http://localhost:8080/api/break-news/feed?limit=5 | jq .
open http://localhost:8080/break-news.html
```

---

## [3.0.0] — 2026-05-13 — Project Nexus (Knowledge Graph)

### Added — Major architectural layer: 1st/2nd/3rd-order relationship graph

- **`scripts/nexus/`** — new module tree implementing news + financial-analysis-driven
  knowledge graph extraction. Built atop existing V2.X analytical pipeline, does NOT
  alter decision layer (Arbiter wiring deferred to V3.1).
  - `schema.py` — Node/Edge dataclasses, NodeType + EdgeType enums, canonical id helpers
  - `config.yaml` — multi-dimensional decay strategies (catalyst 7d / narrative 21d /
    structural_shift 90d / supply_chain_hop 45d / outcome_for 30d), tier confidence
    multipliers (Tier 1: 1.0 / Tier 2: 0.7 / Tier 3: 0.85), alias map (TSM/NVDA/MSFT…),
    pruning thresholds, Tier 3 backfill limit
  - `tier1_loaders.py` — pre-structured JSON loaders (theme-detector cache,
    event_index, news_logs digests, thesis registry, Dashboard/data.json earnings)
  - `tier2_regex.py` — extends existing extractors with tech-node regex
    (HBM3e / N3P / CoWoS-L / Blackwell / Rubin / silicon photonics / GaN / SiC …)
    — these are leading-leading indicators surfacing in commentary weeks before
    financial confirmation. Emits SUPPLY_CHAIN_HOP edges via canonical narrative nodes
  - `tier3_llm_ner.py` — Haiku 4.5 batched LLM NER with prompt caching, SHA256
    per-document cache, two-stage alias canonicalization (hard alias map +
    ≥3-doc promotion guard for provisional narratives)
  - `pagerank_lite.py` — Power Iteration PageRank fallback when `networkx`
    unavailable; degree-centrality cheap fallback below that
  - `build_graph.py` — orchestrator: tier merge → multi-dim decay + confidence-weighted
    → networkx/lite centrality → leaf+cap prune → emit `Dashboard/nexus_graph.json`
    (<5MB hard cap, asserted)
  - `prompts/ner_system.md` — Haiku ontology + few-shot for triple extraction
- **`Dashboard/graph.html` + `Dashboard/page-graph.js`** — new `/graph.html` page
  rendering Obsidian-style force-directed graph via `force-graph@1.43` CDN.
  Monochrome by default, size = √(degree centrality), hover glows `--secondary`.
  **Narrative Flow path tracing**: click any node → BFS up to 3 hops → 1st/2nd/3rd
  order beneficiaries highlighted in blue gradient, animated link particles along
  active frontier. Side-panel lists ranked neighbors per hop with PageRank, plus
  source-document audit trail
- **`Dashboard/utils.js` NAV_ITEMS** — new `knowledge graph` nav item in PORTFOLIO group
- **`Dashboard/i18n.js`** — `nav.graph` zh/en keys
- **`daily_update.sh` Step 8** — Nexus build appended after Step 7 (Structural
  Watchlist); soft-installs `networkx` if missing; non-fatal failure mode
- **`dashboard_server.py`** — new `/api/graph/data` (serves cached JSON) and
  `/api/graph/centrality/<TICKER>` (per-ticker connected themes/catalysts/narratives/peers)
  read-only inspection endpoints. **No** Arbiter integration

### Why

Existing V2.X analyzes individual stocks well but lacks 全域空間感知. Daily news +
theme detector + sector intel + deep dives already produce structured artifacts —
what was missing is the edge layer surfacing 2nd-order beneficiaries (e.g. NVDA
capex story → VRT/COHR/GLW supply chain) and narrative共振 before financial outcomes
confirm them. Nexus introduces a graph-shaped entity store as a structural new
layer (hence major version jump) atop the analytical pipeline. Tier 3 LLM is the
heart, not a supplement — it reads the prose where 2nd/3rd-order relationships
actually live. MVP is visualization + centrality inspection only; Arbiter wiring
into investment_protocol Phase 3 (二階衍生推薦 + 紅隊打折) deferred to V3.1.

### Costs / Operations

- Daily Tier 1+2 build wall time: ~10–20s
- Tier 3 steady-state daily cost: ~$0.05 (40 MDs × ~3k tokens × Haiku 4.5,
  cache-hit ≥90%). First-day backfill capped at 10 MDs/run (~$0.03)
- Output: `Dashboard/nexus_graph.json` (~1.5MB Tier 1+2, ~3MB w/ Tier 3 full)
- Audit log: `scripts/nexus/cache/build_log_<DATE>.json` per build

---

## [2.20.2] — 2026-05-12
### Added — Sector protocol 加速 (A1 + B2) + 時間 timeout 拉到 30 min (V2.20.1)

### Added
- `sector/scripts/phase0_read_caches.py` (A1, 新檔):
  - Phase 0 unified cache reader — 一次跑取 5 層 cache (breadth / FTD / market_top / FRED) + 新鮮度判斷
  - stdout 輸出單一 JSON，取代過去 5+ 個 inline `python -c` bash call（每個 = 1 turn × LLM overhead）
  - slim_* 函式只保留 Phase 0 需要的欄位（FRED 11 fields, breadth/FTD/market_top 4 key blocks）
  - 預估省 **2-3 min** sector wall time（5-8 個 turn → 1 個 turn）
- `sector/phase_0.md` — 上面標示推薦使用 unified reader，舊流程改備援
- `sector/phase_1-2-3.md` — Step 3b/3c/3d/3e parallel mode（bash `&` + `wait`）：
  - 4 個 fetch_*.py (earnings_pulse / smart_money / sector_news / general_news) 平行跑
  - 過去 sequential ~6 min → parallel ~30s wall
  - 預估省 **3-4 min** sector wall time
- `dashboard_server.py` (V2.20.1):
  - Preflight chain sector wait timeout 1200s (20 min) → **1800s (30 min)**
  - `PROTOCOL_TIMEOUT_OVERRIDES` 加 sector override 1800s + `SECTOR_TIMEOUT_SEC` env var

### Why
- 用戶觀察 sector V1.4 PARALLEL_SUBAGENT 跑 ~17-21 min（p95 21 min），偶爾 hit 1200s preflight cap timeout
- 解兩個方向：
  1. **拉 timeout cap**：preflight 1200 → 1800，避免 false timeout
  2. **減 sector 實際耗時**：A1 + B2 應省 5-7 min (17.8 min → 11-13 min)
- 沒做 A3 (Devil's Advocate inline)、A2 (Phase 5 builder)：兩者需動 protocol 邏輯，風險 vs 收益不對等

### Smoke
- `python3 sector/scripts/phase0_read_caches.py` rc=0，輸出 4 layer (breadth/ftd/market_top stale, fred fresh)
- `python3 -m py_compile sector/scripts/phase0_read_caches.py` OK
- `python3 -m py_compile dashboard_server.py` OK

### Out of Scope (V2.20.3+)
- A2 — Phase 5 build_sector_intel.py 拆出獨立 script（需 Phase 4 lane outputs 先序列化到 disk）
- A3 — Devil's Advocate 從 Phase 4 獨立 subagent → Phase 2.5 inline（需動 protocol divergence 邏輯）
- B1 — 4 lane subagent 合併（Theme + News Catalyst）
- B3 — theme_detector `--skip-if-fresh` 邏輯確認（目前 cache hit < 3h 應該秒退，需 verify）

---

## [2.20.0] — 2026-05-10
### Added — V2.20.0：UI Decision Layer 完整化 + Backtest 深化 + Decision Logic 動態化

### Added (A — UI Decision Layer)
- `bridge.py` `extract_audit_history`：`recent_analysis[].det_shadow` 已含 polarization + red_team_basis（從 V2.19 history.json 經 apply_det_shadow 重跑後注入）
- `bridge.py` `extract_earnings_analyses`：每筆 entry 加 `structural_shift` 欄位（從 cache directly），給 earnings card badge 用
- `bridge.py` `load_theme_overrides()` (新)：讀 theme-detector cache 過濾出 `structural_shift_override=True` 的 themes，注入 `data.theme_overrides`
- `Dashboard/page-decisions.js`:
  - Polarization badge 升 4-tier (BIPOLAR / **OUTLIER** 新增 / MIXED / ALIGNED 不顯)
  - Red Team basis 4-tier badge：**RT MR-ONLY** 紅 / **RT CONTAM** 橘 / **RT FWD** 綠（pure_forward 健康才綠）/ unclassified 不顯
- `Dashboard/page-earnings.js`：earnings card 加 **SHIFT⚡⚡** (CONFIRMED 紅) / **SHIFT⚡** (CANDIDATE 黃) badge
- `Dashboard/page-sector.js` `renderThemes`：themes 列表加 ⚡ icon + tooltip（來自 `data.theme_overrides`，含 hits + bonus）

### Added (B — Backtest 深化)
- `investment/scripts/backtest_watchlist.py`:
  - `RANDOM_SECTOR_TICKERS`：14 sector ETF 各 5 個代表性 ticker（共 70 個 universe）
  - `compute_random_baseline()` (B1)：null hypothesis test — 比較 watchlist alpha vs random 同 sector 5 ticker 的 alpha
  - `compute_per_keyword()` (B2)：14 個 keyword 拆解 — 哪幾個 keyword 帶 signal、哪幾個是 noise
  - `compute_per_credibility()` (B3)：HIGH vs MEDIUM source 切片
  - `compute_horizon_sweep()` (B4)：5d/15d/45d/90d 全 horizon mean alpha + hit rate
  - render_markdown 4 個新區塊
  - `--dry-run` flag (D2)：純 stdout 不寫檔
- 今天跑出來：**watchlist +4.4pp 過 random sector baseline (35 samples)** → 證明非純 sector momentum；`super-cycle` keyword 最強 (+23.4% mean α)；`supply tight` 最弱 (+5.1% — 疑似 boilerplate)

### Added (C — Decision Logic)
- `investment/investment_protocol_v5_0.md` Phase 3 Step 4 — **Dynamic Decision Threshold**：
  - CONFIRMED + ALIGNED → buy_threshold 1.0（更敢進）
  - CANDIDATE + ALIGNED → 1.1
  - BIPOLAR → 1.5（更嚴）
  - OUTLIER → 1.3
  - default 1.2 （staged_threshold 永遠 = buy − 0.4）
- `investment/scripts/apply_det_shadow.py` `compute_lane_freshness_penalty()` (C2)：
  - 5 lane 各自 fresh window：news 2d / sentiment 1d / technical 1d / fundamentals 90d / valuation 90d
  - 4 級 multiplier：fresh ×1.0 / 1-2x ×0.9 / 2-3x ×0.8 / >3x ×0.7
  - 寫入 `det_shadow.lane_freshness` block
  - 114/123 historical entries 套上 freshness penalty (大多 sentiment/technical lane 略過 fresh window)
- `investment/scripts/apply_det_shadow.py` `classify_red_team_basis_detail()` (Gemini review #1)：
  - V2.20.0 metadata：mr_hits / fw_hits / mr_keywords / fw_keywords / mr_density / fw_density per 1000 chars
  - 不改 basis label binary 4-tier 契約，純為 V2.21+ density-weighted calibration 留資料

### Added (D — UX)
- `bridge.py` `load_structural_watchlist()` 加 trajectory：每個 candidate 帶 `n_events / first_seen_event / graduated_candidate / graduated_confirmed / continued_count`
- `Dashboard/script.js` `renderStructuralWatchlist`：加 lifecycle badge — **NEW** (≤2 events 綠) / **AGING** (≥5 continued 灰) / **CANDIDATE** (黃) / **CONFIRMED** (紅)

### Backfill (cumulative cross-version delta in this commit)
本 commit 也含 V2.19.1 + V2.19.2 在這些 file 累積的部分（無法乾淨切到前面 commit）：
- `bridge.py` V2.19.1 `load_structural_watchlist()` + V2.20.0 theme_overrides / trajectory / earnings shift
- `Dashboard/script.js` V2.19.1 `renderStructuralWatchlist` + V2.20.0 trajectory badges
- `Dashboard/page-decisions.js` V2.19.2 ⚡ + V2.20.0 OUTLIER + RT basis
- `Dashboard/page-earnings.js` V2.19.2 ⚡ + V2.20.0 SHIFT
- `investment/scripts/backtest_watchlist.py` V2.19.1 skeleton + V2.19.2 forward returns + V2.20.0 B1-B4 + dry-run

### Why
- V2.18+V2.19 加了 protocol 改動，但 UI 沒 surface → user 看不到 polarization / red_team_basis / structural_shift tier 起作用
- V2.20.0 把所有改動 surface 到 dashboard 三頁（decisions / earnings / sector），user 一目了然
- Backtest 從 V2.19.2 的「跑得起來」深化到「拆解 signal 來源」：random baseline 證明 watchlist 真有 edge，per-keyword 找出 noise vs signal
- Dynamic threshold 解決固定 1.2 對 paradigm-shift 太嚴、對 chaotic 太鬆的問題

### Smoke
- `python3 bridge.py` → `[OK] Theme overrides: 3 paradigm-shift themes` + watchlist 注入
- `python3 investment/scripts/apply_det_shadow.py --inplace history.json` → 114/123 entries 套 freshness penalty
- `python3 investment/scripts/backtest_watchlist.py` →
  - SOXX watchlist mean α 15d = +18.4% vs random baseline +14.0% = **+4.4pp edge**
  - Per-keyword: super-cycle +23.4%（5 hits）/ 供不應求 +18.4%（7 hits）/ supply tight +5.1%（3 hits）
  - Horizon: 5d +0.1% 沒動；15d peak +18.4%；45/90d 還沒到
- `python3 investment/scripts/backtest_watchlist.py --dry-run` → stdout 全 markdown，不寫檔

### Out of Scope (V2.20.X — 等 watchlist accrue)
- E1-E3 backtest 真實驗證（lifecycle ≥30 events / 3+ sector / 5+ evicted samples）
- F1 thesis_registry concentration check（Phase 4 sizing）
- F2 sector protocol 反向加權
- Lane-specific freshness mtime（Gemini review #2 — 取代 session-level penalty）

### Out of Scope (V2.21+ — 大改)
- News provisional → tier modulation（需 V2.20.X backtest 結果）
- Modulation 參數 auto-calibration（需 n>50 sample）
- macro_multiplier sector × duration sensitivity matrix

---

## [2.19.2] — 2026-05-10
### Added — V2.19.X 補強：⚡ badge 跨頁、backtest forward returns、theme heat bonus

### Added
- `Dashboard/page-decisions.js` + `page-earnings.js`:
  - 個股名旁 ⚡ amber lightning badge if ticker ∈ `data.structural_watchlist.candidates`
  - 兩頁各自在 data load 處 populate `window.UI.watchlistSet`
- `investment/scripts/backtest_watchlist.py`:
  - `_fetch_price_series()` — FMP `/stable/historical-price-eod/light` endpoint，cache by ticker
  - `_close_at_or_after()` — 跳過週末 / 假期，找下一個交易日
  - `fetch_forward_returns()` — 完整實作（取代 V2.19.1 stub）：
    - T+5d / T+15d / T+45d / T+90d 報酬
    - α_SPY (絕對 alpha vs SPY) + α_sector (相對 alpha vs sector ETF)
    - SECTOR_ETF_MAP：Memory Semis→SOXX、Energy→XLE、Healthcare→XLV…
    - 未到的 horizon 寫 None；status: ok / partial / no_data / api_unavailable
  - 改 `collapse_by_ticker` 用 `first_observed`（news 首次提及日）為 backtest anchor，不用 event date
  - render_markdown 加 forward returns table + 15d alpha aggregate (mean / hit_rate)
  - JSON 輸出 加 forward_returns block
- `skills/theme-detector/scripts/calculators/heat_calculator.py`:
  - `structural_shift_bonus()` — 加性 bonus +0/+5/+10/+15 cap
    - `+10` if 任一 rep stock CONFIRMED；`+5` if 多個 CONFIRMED stack；`+5` if CANDIDATE 但無 CONFIRMED
  - `calculate_theme_heat()` 加新參數 `structural_tier_hits` 並加進 final raw
- `skills/theme-detector/scripts/theme_detector.py`:
  - `_theme_has_structural_shift()` 改回傳 3-tuple 含 `tier_counts: {CONFIRMED, CANDIDATE}`
  - main scoring loop 把 tier_counts 餵 calculate_theme_heat → heat 真的會升
  - heat_breakdown 新欄位 `structural_shift_bonus` + `structural_tier_counts`
  - 移除舊 fundamental_override 重複 call（V2.18 寫了兩次）

### Why
- V2.18 只 hack lifecycle stage label，heat score 本身沒動 → ranking 沒反映 paradigm shift
- V2.19.2 直接動 heat → ranking 跟著改（AI&Semis 從第 3 升第 1，heat 52.8→62.8 +10 bonus）
- 個股 ⚡ badge 在 V2.19.1 只在 index.html audit cards 上，decisions/earnings 主頁面看不到 — 補完
- backtest forward returns 從 stub 變實做：今天就跑得出 directional sanity（n=7 17 天 mean SPY-alpha +18.4%）

### Smoke
- `python3 investment/scripts/backtest_watchlist.py` → 7 candidates 全 partial data，15d SPY-relative mean +18.4% hit_rate 7/7，sector-relative mean +4.6% hit_rate 4/7（caveat: n 小 + 單一 sector + lookback bias）
- `python3 skills/theme-detector/scripts/theme_detector.py` → AI&Semis heat 52.8→62.8 (+10 MU+NVDA bonus)、Quantum Computing 52.7→62.7 (+10 MU bonus)
- `python3 -m py_compile` 全 OK

---

## [2.19.1] — 2026-05-10
### Added — Structural Watchlist UI + archival 接線（為未來 backtest 準備）

### Added
- `news/scripts/build_structural_watchlist.py`:
  - `_write_history_snapshot()` — 每日寫 `news/news_logs/watchlist_history/<DATE>.json` snapshot（atomic）
  - `_emit_lifecycle_events()` — append-only `news/news_logs/watchlist_lifecycle.jsonl` 事件記錄
  - 事件 enum: `first_seen / continued / evicted / graduated_candidate / graduated_confirmed`
  - graduation 對 earnings-analyst cache `structural_shift.tier` 即時偵測（CANDIDATE/CONFIRMED）
- `bridge.py`:
  - `load_structural_watchlist()` — 讀 `news/news_logs/structural_watchlist.json`，注入 `data.json.structural_watchlist` (top 10 candidates + hot_sectors + decay_rules + freshness)
  - main flow Step 6 接線（Tactical Step 5 之後）
- `Dashboard/index.html`:
  - Layer 5 — `<section id="structural-watchlist">` 新增 watchlist tile（藏起來預設，data 有才秀）
  - i18n key: `watchlist_title / watchlist_badge / watchlist_subtitle / watchlist_disclaimer`（中英文）
- `Dashboard/script.js`:
  - `renderStructuralWatchlist(sw)` — 渲染 candidates 卡片（ticker / sector / hits / credibility / days_since_last / keywords / first_observed），點擊跳到 decisions.html
  - `decorate()` 擴充：crossSet ⭐ 之外加 `watchlistSet` ⚡ 黃色 lightning badge
- `Dashboard/i18n.js` — 中英 4 個 watchlist label
- `investment/scripts/backtest_watchlist.py` (新檔):
  - 讀 lifecycle.jsonl + earnings cache
  - `compute_tier_lead_time()` — first_seen → graduation lead time stats
  - 4 outcome 分類: confirmed / candidate / still_active / evicted_no_graduation
  - Forward return stub (V2.20 寫 FMP 整合)
  - 輸出 `reports/WATCHLIST_BACKTEST_<DATE>.md` + JSON

### Why
- V2.19.0 watchlist 每天 atomic rename 蓋掉舊檔 → 沒歷史資料 → 2 週後想 backtest 沒 raw data 可用
- V2.19.1 補 archival 緊急修補：每日 snapshot + append-only lifecycle log，**不做的話未來無法驗證 watchlist signal 質量**
- UI 接線：watchlist 從 metadata-only file 變成 dashboard 看板上的早警示，user 可以提早注意 paradigm shift 候選股
- backtest skeleton 兩週後就能跑：tier graduation rate（hit rate） + lead time（多早預警）+ 後續 V2.20 加 forward returns（alpha 對比 SPY/sector ETF）

### Smoke
- `python3 news/scripts/build_structural_watchlist.py` → 7 candidates / 1 hot sectors / 9 lifecycle events（含 NVDA→graduated_candidate / MU→graduated_confirmed）
- `python3 bridge.py` → `[OK] Watchlist: 7 candidates / 1 hot sectors (0.1h)` 注入 data.json
- `python3 investment/scripts/backtest_watchlist.py` → `7 tickers / 1 CONFIRMED / 1 CANDIDATE` rc=0
- compile-check：build_structural_watchlist.py + backtest_watchlist.py 全 OK

### Out of Scope (V2.20)
- backtest_watchlist.py forward returns 部分（FMP price fetch + SPY/sector ETF alpha）
- watchlist → earnings-analyst tier 觸發 tie-breaker（需先 backtest 證明 signal 質量）
- decisions.html / earnings.html 個股級 ⚡ badge（目前只在 index.html audit cards 上）

---

## [2.19.0] — 2026-05-10
### Added — Lane Cross-Talk Wiring (Phase 3 polarization + Red Team anti-spoof + News watchlist)

### Added
- `investment/scripts/apply_det_shadow.py`:
  - `compute_polarization()` 升 4-tier (BIPOLAR/OUTLIER/MIXED/ALIGNED)。BIPOLAR 規則加 `pos_strong ≥ 2 AND neg_strong ≥ 2` direction count，避免 4-vs-1 outlier 誤判（例 `[+4,+3,+3,+2,-2]` 修前 BIPOLAR、修後 OUTLIER）
  - `classify_red_team_basis()` — V2.19 anti-spoofing classifier。4-tier basis：`pure_forward / pure_mean_reversion / contaminated / unclassified`。LLM 偷渡 mr (塞 1 個 fw keyword 偽裝) → 標 `contaminated`，CONFIRMED tier 下視同純 mr 觸發降級
  - `apply_to_trade()` 寫 `red_team_basis` 入 det_shadow block
- `investment/scripts/validate_v219.py` — 16 fixture (10 polarization + 6 basis)，含 Gemini outlier case 與 contamination spoof test
- `investment/investment_protocol_v5_0.md`:
  - Phase 3 **Step 1.7** Lane Polarization Modulation (4-tier，BIPOLAR ×0.5 confidence + cap 25% + BUY→STAGED_ENTRY；OUTLIER ×0.85；MIXED ×0.75；ALIGNED 不動)
  - Phase 3 **Step 2** anti-spoofing 邏輯：CONFIRMED + (pure_mr OR contaminated) → STRONG_COUNTER auto-downgrade MODERATE + penalty 折半
  - Phase 2.8 Red Team prompt 加 `STRUCTURAL_SHIFT_TIER` input + 條件指令 (CONFIRMED 必引 forward mechanism)
  - Phase 4 Step 4 Sizing 加 `polar_adj` 串聯 (BIPOLAR 強制 ×0.25 跟 V2.18 shift_adj 串接)
  - Phase 3 JSON shape 加 `polarization_modulation` + `red_team_basis` + `red_team_auto_downgrade` 欄位
- `investment/phase5_export_schema.md`:
  - det_shadow 升 V2.19 schema：`signal_polarization` 4 值、`pos_strong/neg_strong`、`red_team_basis` 4-tier
  - 新增 Phase 3 Step 1.7 modulation 對照表 + Red Team basis 判定規則
- `investment/scripts/validate_session_export.py`:
  - 新增 `det_shadow.signal_polarization` enum 檢查（V2.19 4-tier）
  - 新增 `det_shadow.red_team_basis` enum 檢查
  - det_shadow 缺欄 → schema fail
- `news/news_protocol_v2.md` Phase 4.5 — Structural Watchlist 段落（schema、decay rules、daily cron 規範、V2.19 約束 metadata-only）
- `news/scripts/build_structural_watchlist.py` (新檔):
  - 14 keyword whitelist (sold out / capacity constrained / supercycle / 供不應求 ...)
  - 14d hit window + 21d eviction + ≥2 sources first-hit gate + url stem / 8-gram dedup
  - sector aggregation + atomic temp+rename + failure non-fatal
  - 已 smoke 跑通：7 candidates / 1 hot sector (TSM/MU/NVDA/ASML 在 Memory Semis)
- `daily_update.sh` — Step 7 接線 (1/6 → 1/7 全部更新)，failure non-fatal

### Why
- V2.18.0 解 MU/QCOM 超級週期錯失只是繃帶；user 反思指出「lanes 各自為政」病根沒治
- Gemini 三提案 critical eval：
  - **#1 News provisional 強版 REJECT** — IR boilerplate / reflexive loop / mosaic violation；輕量版 (watchlist metadata-only) DO
  - **#2 Cross-lane divergence DO 但簡化** — `compute_polarization` 已存在，Gemini stdev 提案是重造輪子
  - **#3 Red Team dynamic prompt DO 雙層** — prompt + post-filter classifier 防 LLM jailbreak
- V2.19 = wiring + hardening release，不是 feature release。把 V2.18 留下的 dangling hook (`red_team_basis="mean_reversion_only"` 行 604) + 現存沒接線的 `compute_polarization` 串起來
- 三條 anti-adversarial 鐵律：
  1. **mr 一票否決**：mean-reversion keyword 一旦出現都觸發 dampening（contaminated 不是 mixed）
  2. **OUTLIER 不誤殺**：4-vs-1 outlier 不是真衝突 (×0.85 不像 BIPOLAR 砍倉)
  3. **Watchlist 強制衰減**：14d/21d 防幽靈數據，single-source 不入榜

### Smoke
- `python3 investment/scripts/validate_v219.py` → PASSED 10 polarization + 6 basis fixtures (含 Gemini outlier + contamination spoof)
- `python3 news/scripts/build_structural_watchlist.py` → 7 candidates / 1 hot sector (Memory Semis: TSM/MU/NVDA/ASML)
- compile-check：apply_det_shadow.py / validate_v219.py / validate_session_export.py / build_structural_watchlist.py 全 OK

### Out of Scope (V2.20)
- News provisional → 直接驅動 tier modulation（須先 backtest watchlist 是否能可靠當 leading indicator）
- backtest 餵回 V2.18/V2.19 modulation 參數 auto-tune
- macro_multiplier 改 sector × duration sensitivity matrix
- Theme-detector heat 公式納入 sector aggregate EPS momentum (V2.18 只 hack lifecycle stage)

---

## [2.18.0] — 2026-05-10
### Added — Structural Shift Modulation: 解 MU/QCOM 超級週期錯失 systemic bug

### Added
- `skills/earnings-analyst/scripts/analyze.py` — `compute_structural_shift()`：偵測 EPS QoQ ≥30% / GM ≥ historical+2σ / revenue YoY ≥25% AND accelerating 三 signal，≥2 → CANDIDATE，連 2 季 → CONFIRMED。獨立 signal，不影響 composite_score
- `skills/earnings-analyst/schema.md` + `SKILL.md` — `structural_shift` 區塊文件化（tier / signals / metrics / 設計理由）
- `investment/scripts/register_thesis.py` — `_read_structural_shift()`：thesis registry 自動接收 latest earnings cache 的 structural_shift block，存入 thesis_data
- `investment/investment_protocol_v5_0.md` Phase 3 **Step 1.5 Structural Shift Modulation**：
  - CONFIRMED → analyst-PT weight ×0、Red Team mean-reversion attack BLOCKED、shift_macro_floor=1.00、position_cap=100%
  - CANDIDATE → analyst-PT ×0.3、STRONG_COUNTER penalty 折半、shift_macro_floor=0.95、position_cap=50%
  - NONE/INSUFFICIENT_DATA → 標準規則
- Phase 3 JSON shape 加 `calculation_steps.structural_shift_modulation`（tier/applied_adjustments/shift_macro_floor/position_size_cap_pct/red_team_mean_reversion_blocked）
- Phase 4 Step 4 Sizing 加入 `shift_adj = ftd_adj × (position_size_cap_pct/100)`，將 shift cap 套在所有其他乘數之後
- `skills/theme-detector/scripts/calculators/lifecycle_calculator.py` `classify_stage()` — 新增 `fundamental_override` param：true 時門檻整體往後拉（80→95 才算 Exhausting），避免 paradigm-shift sector 被技術面過熱誤判
- `skills/theme-detector/scripts/theme_detector.py` `_theme_has_structural_shift()` — 掃 representative stocks 的 earnings cache，命中 CANDIDATE/CONFIRMED 即觸發 fundamental_override；scored_theme 額外輸出 `structural_shift_override` + `structural_shift_hits`

### Why
- MU/QCOM 案例復盤：超級週期股票被三個 backward-looking 模型同時壓制 → DEFENSIVE HOLD，錯失主升段
  - Valuation lane：被滯後 analyst PT 拖累（MU 4/24 Q2 blowout 後 PT 還停在 $455 / 算出合理價 $549 vs 市價 $714）
  - Red Team：用「記憶體歷史 GM 30-35%、現在 74% 是 Peak Cycle」mean-reversion 攻擊
  - Macro：Theme Detector 把 Semis 標 Exhausting → Phase 0 sector_avoid → multiplier ×0.9
- 機制設計（不是 override，是 dampening）：
  - 1Q earnings blowout 即可觸發 CANDIDATE（避免 2Q 確認太慢，主升段已過）
  - 但 CANDIDATE position cap 50% 防止單季 noise 變 bubble-top BUY
  - CONFIRMED 才完全解除錨點，且 Red Team 必須 forward mechanism breakage 攻擊（不接受純歷史均值論證）
- 對稱性：missing top = bounded loss、buying top = unbounded loss → tier 階梯保護後者
- 校準：MU=CONFIRMED (eps_qoq +163%/gm z=4.18/rev_yoy +196%)、NVDA=CANDIDATE、AAPL/AMD/ARM=NONE

### Smoke
- `python3 skills/earnings-analyst/scripts/analyze.py MU` → composite=80/100 verdict=STRONG **shift=CONFIRMED**
- `python3 skills/earnings-analyst/scripts/analyze.py NVDA` → composite=86/100 verdict=STRONG **shift=CANDIDATE**
- `python3 skills/earnings-analyst/scripts/analyze.py AAPL` → composite=70/100 verdict=SOLID shift=NONE
- `_read_structural_shift()` & `_theme_has_structural_shift()` 直接 import 測通

---

## [2.17.26] — 2026-05-10
### Fixed — verdict_deep_dive 方向推論支援 V5.0 動詞 action（STAGED_ENTRY / EXECUTE）

### Fixed
- `scripts/verdict_rules.py` `verdict_deep_dive` — substring matching 換成 V5-aware 顯式 mapping：
  - **BUY 類**：`{BUY, LONG, EXECUTE, STAGED_ENTRY, STAGED}` → direction = "buy"
  - **SELL 類**：`{SELL, SHORT, STAGED_EXIT}` → direction = "sell"
  - **HOLD 類**：HOLD / CANCEL / unknown → direction = "hold"
  - 保留 substring 兜底（cover 多字串如 `BUY (T2)`）

### Smoke result
| metric | baseline | 修後 |
|---|---|---|
| MU 6 staged/execute records | all miss | all **hit** ✓ |
| STAGED_ENTRY miss_rate | 72% (21/29) | **17%** (5/29) ✓ |
| EXECUTE miss_rate | 75% (6/8) | **25%** (2/8) ✓ |
| 整體 deep-dive hit_rate | 40% (44/109) | **55%** (60/109) ✓ |
| 整體 deep-dive miss_rate | 54% (59/109) | **37%** (40/109) ✓ |

### Why
- User 觀察 MU 幾乎全 miss，例：2026-05-01 STAGED_ENTRY score 1.22 / 9 天 +37.73% 卻判 miss
- Root cause：V2.17.18 parser 修完後 final_action 正確帶到 V5 verbs，但 verdict 邏輯沒同步 — V5 verbs 不含 `BUY` substring，全 fallthrough 到 hold → 觀望 + 正報酬 = "錯過上漲" 假 miss
- 影響：REVIEW_2026-05-09 Pattern 1（mega-cap repeat-miss：AMD / MU / NBIS / GOOGL）有大半是這個 verdict bug 製造的 artifact，不是真策略失敗
- 修法：純 verdict label 邏輯，不動策略本身。下週 REVIEW Pattern 1 會大幅縮水，Hypothesis A（Bull regime under-call）需用乾淨資料重評

### Ledger
- `ADJUSTMENT_LEDGER.md` 新增 entry 追蹤本修法 metrics

---

## [2.17.25] — 2026-05-10
### Fixed — theme-detector extractor 升級到 header-name lookup（解決 0 themes detected）

### Fixed
- `scripts/extractors/theme_detector_extractor.py` `_find_themes` — 重寫成 header-driven column resolution：
  - 偵測 Theme Dashboard table 第一行 header
  - 用名稱映射（"theme"/"direction"/"heat"/"stage"/"confidence" + alias 如 "dir"）找到每個欄位的 cell 索引
  - 後續資料 row 用索引取值，不再依賴固定欄位順序
  - skip markdown separator row（`|---|---|...`）
- 新格式（V2 2026-04-23+）`Theme | Origin | Direction | Heat | Maturity | Stage | Confidence` 7 欄、無 # 索引
- 舊格式 V1 / 中英雙語 header `# | Theme 主題 | Dir 方向 | Heat 熱度 | Stage 階段 | Confidence 信心` 也通

### Smoke
| report | before | after |
|---|---|---|
| theme_detector_2026-04-11 | 0 themes | **10 themes** ✓ |
| theme_detector_2026-04-23_220833 | 0 themes | **10 themes** ✓ |
| theme_detector_2026-04-25_004154 | 0 themes | **10 themes** ✓ |

verdict 全 5 筆現在算出真實 hit/miss/neutral：4/11 miss (3/9 跑贏)、4/23 neutral 4/7、4/23 hit 6/9 ×2、4/25 hit 6/9。

### Why
- User 截圖：theme-detector drill 5 筆「0 themes detected」+ verdict 全 PENDING/MISS — root cause: extractor 寫死「第一格必須是數字 #」，新報告把 # 列拿掉 → 全 skip
- 修法：header-name 映射不依賴欄位順序 / 個數，未來 schema 再加欄位也不會破

### 規則重申（user 問）
- Window 10 個交易日
- 對每個 LEAD 主題：proxy_etf 5d/10d 跑贏 SPY → hit；輸 SPY → miss
- 聚合：hit_rate ≥ 60% HIT / ≤ 40% MISS / 中間 NEUTRAL
- LAG 主題（看空）目前 verdict 沒評，待後續加 symmetric check

---

## [2.17.24] — 2026-05-10
### Fixed — Drill row 現實行覆蓋更多 source（thematic / theme / momentum / earnings）

### Fixed
- `Dashboard/page-calendar.js` `_drillRealityLine` — 原本只處理 `ticker_reality` + `spy_return_pct`，多數 market-wide source 顯示「—」。新增分支：
  - `mover_returns`（thematic-screener）→ 顯示「X/Y 方向對」+ 前 5 檔 mover ±%（hit 綠 / miss 紅）
  - `etf_returns`（theme-detector / sector-scan）→ SPY 報酬 + 前 4 檔 ETF rel-to-SPY
  - `ticker_returns`（earnings-analyzer）→ 前 4 檔 ticker ±%
  - `per_ticker`（momentum-screen）→ N/總 命中比率（綠/黃/紅 by hit rate）
- 仍保留 `ticker_reality`（deep-dive）+ `spy_return_pct`（news-digest）+ pending fallback

### Why
- User 截圖：thematic-screener 5 筆 row「現實」全是「—」但 verdict 已是 NEUTRAL/MISS，讓人疑惑判定基礎
- root cause：mover_returns 已寫進 reality_at_eval（每筆 19-20 個 ticker），但 row renderer 沒讀
- 修後 row 直接顯示 movers 命中比 + 前 5 檔對齊狀況

### 雷達評斷規則（user 問）
- Window 5 個交易日
- 每檔 mover：target_5d_pct 方向 × actual_5d 方向 對 → hit
- 聚合：hit_rate ≥ 60% HIT / ≤ 40% MISS / 中間 NEUTRAL
- 只看方向不看幅度；mover_returns 缺 → PENDING

---

## [2.17.23] — 2026-05-10
### Fixed — Drill modal 改用 CSS vars 跟頁面 theme 連動（不再硬寫深色）

### Changed
- `Dashboard/style.css` drill modal CSS：
  - `cal-drill-shell` / `cal-drill-header` / `cal-drill-body` / `cal-drill-row` 全部從 hardcoded 顏色改成 `var(--bg-card)` / `var(--bg-main)` / `var(--bg-header)` / `var(--text-main)` / `var(--text-card-title)` / `var(--text-muted)` / `var(--border)` / `var(--border-hover)` / `var(--sidebar-active-bg)` / `var(--primary)` / `var(--danger)`
  - 移除所有 `!important` 硬蓋（不再需要對抗 page theme）
  - 移除 `.cal-drill-modal .text-zinc-* / text-green-400 / text-red-400` 強制改寫（既然跟 theme 連動就不需）
  - badge 顏色 layered：default 適合淺色背景的深綠/深紅/深琥珀（light theme readable），`[data-theme="dark"]` override 為亮綠/亮紅/亮黃（dark theme readable）
  - reason highlight box 顏色同樣 dual-theme：light 用 `#92400e` (amber-800)，dark 用 `#fde68a` (amber-200)，背景半透明 amber 對兩 theme 都通
  - heat chip 同 dual-theme handling

### Why
- User 反問：page 是 light theme 為什麼 modal 硬選深色？
- Root cause：先前修法為了解決「page color leak」直接 hardcode 深色 + `!important` 蓋掉，違反 theme 一致性 — light 頁面開深色 modal 視覺斷裂
- 正解：用 CSS vars，site theme 切換自動 propagate；保留先前的 layout 結構，只換顏色 token
- 副作用：dark mode 下會用 `[data-theme="dark"]` override 提供亮色 badge，light 不需 override 直接用 default

---

## [2.17.22] — 2026-05-10
### Fixed — Stale price → pending（不再誤判 HIT）+ drill modal 配色變淺更舒適

### Fixed
- `scripts/build_event_index.py` `compute_reality_for_ticker` — 偵測 yfinance fallback 把 eval bar 對齊到 decision-day 的情況（`e_key == d_key`）→ 回傳 None 強制下游 verdict 變 `pending`
  - 影響：本日後 deep-dive（window 未完成且無新 bar）不再被算成 +0% HIT；MU / CRWV / NEE 2026-05-08 三筆從 hit → pending（價格 746.81 → 746.81 0% 那種）
  - **報告本身也跟著更新**（event_index 重跑後所有 source 同步）；下週 REVIEW 跑 Step 0 protocol 會自動讀新 JSON

### Changed
- `Dashboard/style.css` drill modal 配色重設：
  - shell `#18181b` → `#2a2d36`（slate-tinted, 不再純黑）
  - row `#27272a` → `#383b46`（拉淺一階對比 shell）
  - row hover `#3f3f46` → `#43475a`
  - border `#3f3f46` → `#474b58`
  - reason 行字色 `#fbbf24` → `#fde68a`（柔和琥珀 amber-200）
  - tailwind utility hard-overrides 全部 +1 階亮度（zinc-400 → #b8bdc9 等）
  - backdrop 從 zinc → slate tint，blur 4 → 6px 更柔
  - header 用 slate gradient

### Why
- User 截圖 V2.17.21：MU/CRWV/NEE 2026-05-08 顯 ✅ HIT，實際 746.81 → 746.81 +0.00% 是 yfinance 沒新 bar → reuse decision-day price 假裝有 return
- Root cause：`closest_price(prices, eval_date, "before")` fallback 到最後一個有 bar 的日期；當 eval 在 today 且 today 沒收盤 → e_key == d_key
- 修法：data 層直接判 e_key==d_key → return None → 走 verdict_deep_dive 既有 None branch → pending
- 配色：原 #18181b/#27272a 太重，user feedback「底色太深」，改 slate-tinted 中間調

### Side effect
- aggregate 計數變動：deep-dive hit 50→44 / miss 60→59 / neutral 7→6 / pending 11→3（pending 集中到「真窗口未到」+「stale price 三筆」），餘 6 筆原 pending 為 parser 修好後可評估的，自動轉 hit/miss

---

## [2.17.21] — 2026-05-10
### Fixed — Drill-down row 顏色 cascade leak（rows 全部黑底看不見內容）

### Fixed
- `Dashboard/style.css`：
  - 所有 row selectors scope 加 `.cal-drill-modal` 前綴，阻擋 page light-mode 層級規則洩漏
  - `.cal-drill-shell` 加 `color: #e4e4e7` 強制 base text
  - row bg 從 `rgba(39,39,42,0.55)` 改 solid `#27272a`（zinc-800），跟 modal shell `#18181b` 對比夠
  - 所有 row 內 text-color rules 加 `!important` 抗 Tailwind utility（`text-zinc-*` / `text-green-400` / `text-red-400`）
  - row 加 `min-height: 86px` 避免 flex 收縮成幾乎不可見
  - reason 行新增 `background: rgba(251,191,36,0.08)` + 左 border 2px 變 highlight box
  - tailwind utility colors（`text-zinc-400/500/600` / `text-green-400` / `text-red-400`）在 modal 內 hard-override 為深色背景下看得到的色階

### Why
- User V2.17.20 截圖：modal 一片黑、128 row 縮成一條條細線、無 text 可見
- Root cause：page 在 light mode → body 套 `color: #18181b` 繼承到 modal；modal 用 dark bg 但 text 顏色被 page rule 蓋成黑色 → 黑底黑字
- row bg `rgba(39,39,42,0.55)` alpha 過低，跟 `#18181b` modal shell 視覺幾乎一致 → row 邊界看不清
- 解法：每條 rule 加 `.cal-drill-modal` scope + 文字 `!important`，CSS specificity 提升一級超過 page 規則

---

## [2.17.20] — 2026-05-10
### Fixed — Drill-down modal UI 重做（compact row, no raw button, prominent reason）

### Changed
- `Dashboard/page-calendar.js`：
  - 廢棄 `renderDecisionCard` reuse（cal-card light-mode 顏色在 dark modal 顯不出 + 帶 raw button）
  - 新增 `renderDrillRow(d)` + `_drillDecisionLine(d)` + `_drillRealityLine(d)` per-source 一行抽 decision / reality 摘要（9 source 全覆蓋）
  - 每筆 row：左色帶 + verdict pill badge + source icon + ticker logo + date + window 進度 + decision 行 + reality 行 + **reason 行（橘色 prominent）** + heat chip
  - 移除 raw 報告 link
- `Dashboard/style.css` — 新 `.cal-drill-row*` styles（自帶深色背景 + verdict badge 4 色 + reason 黃橘色強調行 + chip）

### Why
- User 截圖：reuse `renderDecisionCard` 後在 modal 顯示成「白色空 pill」— root cause: `cal-card` 用 `var(--bg-card)` 是頁面 theme 變數（light mode = white），dark modal 上看起來像空白；body text 顏色 inherit 也錯亂
- User 不需 raw button（占空間 + 干擾），但要看「簡單原因」 — verdict.rationale 提到 row 中央用橘色行顯示
- 每筆 row 高度約 90-110px，128 筆 dollar-friendly scroll；4 行布局 (head / decision / reality / reason / chip) 一眼看完

### Layout 規格（每筆）
```
║ [✅ HIT] 📈 [logo] AMD 2026-04-15           w 115% (23/20d)
   DECISION  BUY · score 1.21 · pos 5%
   REALITY   192.50 → 295.00  +53.20%   max +63 / dd -2
   REASON    return ≥ 30% within 20d → HIT
   🔥 Semiconductors · sector #1 · top 30%
```

---

## [2.17.19] — 2026-05-10
### Added — Decision-review category drill-down modal

### Added
- `Dashboard/calendar.html` — `<div id="cal-drill-modal">` 容器（modal shell + header + filter + sort + close + body）
- `Dashboard/style.css` — modal / backdrop / header / filter pill / sort dropdown / close button / heat chip styles（~135 行）
- `Dashboard/page-calendar.js`：
  - `cal-stat-tile` 加 `data-drill-source` + click/keyboard handler → `openDrillDown(source)`
  - `openDrillDown` / `closeDrillDown` / `renderDrillDown` / `wireDrillDown` — fullscreen modal with verdict filter pills、sort dropdown（date/return/score）、ESC + outside click close
  - `renderHeatChip` — V2.17.16 `sub_industry_heat` 取出 industry / sector_rank / top_30%? 視覺 chip（hot/cold 兩態），append 到每張 card 末
  - 直接 reuse 既有 `renderDecisionCard` → 9 source body 自動覆蓋（deep-dive / sector-scan / news-digest / theme-detector / momentum-screen / thematic-screener / earnings-analyzer / short-term-weekly / postmortem）

### Why
- User 看到「深度分析 128 筆」summary tile 想點進去看每筆當初決策 + 現實 + verdict
- 既有 `renderDecisionCard` 已含 verdict 色帶 + emoji badge + per-source body + raw_path link，drill-down 直接 reuse 不重寫；只補：modal shell / 篩選 pill / sort / 視覺化 industry heat chip
- chip 利用 V2.17.16 sub_industry_heat instrumentation：top 30% sub-industry 顯橘紅 🔥；其他 cool 灰，一眼看出是不是熱門族群的決策（可解釋 miss 為何集中）
- 9 類全自動覆蓋（不分流）— 任何新 source 接到 calendar 都自動有 drill-down

### 互動細節
- tile hover：浮起 + 陰影
- modal: backdrop blur, animate-in scale + slide
- filter pills 顯示 verdict count；count=0 自動隱藏（除 "all"）
- sort: date↓/↑、return↓/↑、score↓
- ESC / 點 backdrop / 點 ✕ 都關閉

---

## [2.17.18] — 2026-05-10
### Fixed — Decision-review parsers 跟上 V5.0 schema（Rec 1 + Rec 4）

### Fixed
- `scripts/extractors/deep_dive_extractor.py` `_find_decision` — 新增 V5.0 patterns：
  - `**Final Decision**` / `**最終決議**` 表頭（值可加粗或不加粗）
  - `**Action Label**`（DEFENSIVE / OFFENSIVE / NEUTRAL …）
  - 內文裸 `EXECUTE` / `STAGED_ENTRY` / `STAGED_EXIT` 動詞
  - parenthetical secondary action 自動剝（`HOLD (CANCEL)` → `HOLD`）
- `scripts/extractors/deep_dive_extractor.py` `_find_final_score` — 新增 V5 table row + case-insensitive body form + 全形冒號 + table cell `| final score | 2.055 |`
- `scripts/extractors/news_digest_extractor.py` `_find_macro_delta` — 新增 `(session_macro_delta +0.20)` parenthetical + JSON-ish 形式 + Greek `Δ` headers（May 2026+ digests 改用 Δ 不再是 "Delta"）

### Smoke result
| metric | baseline | 修後 |
|---|---|---|
| deep-dive `final_action is null` | 52% (58/112) | **2.7%** (3/112) ✓ |
| deep-dive `final_score is null` | ~16% (~18/112) | **6.2%** (7/112) ✓ |
| news `macro_delta is null` | 59% (13/22) | **27.3%** (6/22) ✓ |

殘留：3 筆 deep-dive + 6 筆 news 全屬 v1/legacy protocol 格式（legit n/a，非 parser bug）。

### Why
- REVIEW_2026-05-09 Hypothesis B + Rec 1 / Rec 4 標 high conf prerequisite — 不修這兩個解析器，所有 strategy-level pattern 數字都被污染（unknown 跟 n/a 拉爆 hit/miss 比率），無法評估 Rec 2 / 3.5 等策略 Rec 是否該 apply
- 純 instrumentation 修法：parser 跟上現實格式，**完全不動決策邏輯** → 下週 deep-dive / news-digest 報告**內容跟本週一樣**，但 REVIEW 看到的數字會是真的
- Ledger 新增 Rec 1 + Rec 4 entries，下週 REVIEW Step 0 會自動跑 evaluation_history 比對

---

## [2.17.17] — 2026-05-09
### Changed — `llm_review` protocol prompt 同步 4-step REVIEW flow

### Changed
- `dashboard_server.py` `SCRIPT_PROTOCOLS["llm_review"]` — protocol prompt 從「三步驟」改「四步驟」，明加 Step 0 Adjustment Evaluation；Step 1 加引用 `industry_rollup` + `sub_industry_heat`；Markdown 輸出 schema 加「## 0. Adjustment Evaluation」+「## Industry Rollup」表頭範本；Step 0 indexer rebuild 描述加 `industry_rollup` + `adjustment_ledger_active` 兩個新 top-level 欄位

### Why
- V2.17.16 改了 `REVIEW_PROMPT.md` 變 4-step 但 `dashboard_server.py` 內嵌的 protocol prompt 還寫「依 REVIEW_PROMPT 三步驟執行」 → 用戶按「請 LLM 檢討」按鈕觸發的 LLM 會跳過 Step 0 Adjustment Evaluation
- 兩處 prompt 必須同步，否則 ledger evaluation 形同虛設
- V2.17.17 後按按鈕 → server `subprocess` 跑 `build_event_index.py`（Step 0 已寫入 protocol）→ LLM 收 prompt 自動跑 4-step → write `REVIEW_<DATE>.md`，不需手動串接

---

## [2.17.16] — 2026-05-09
### Added — Decision review: sub_industry_heat + industry rollup + adjustment ledger

### Added
- `scripts/_sector_heat.py` (NEW) — `enrich_ticker_heat(ticker)` 共用 join helper：合 latest `sector_intel` (sector composite_score / rank) + `theme_detector` (theme heat / direction) + `fmp_industry/snapshot` (industry averageChange / rank) + `company_context.get_profile` (sector / industry resolve)
- `scripts/build_event_index.py` `_build_industry_rollup` — 把 deep-dive verdict 按 `tuning_hooks.sub_industry_heat.ticker_industry` 聚類，輸出 `event_index.industry_rollup`（n / hit / miss / miss_rate / avg_miss_return / industry_top_30pct）
- `scripts/build_event_index.py` `_load_adjustment_ledger` — parse `ADJUSTMENT_LEDGER.md` 中 `status: active` 的 Rec entries，注入 `event_index.adjustment_ledger_active`
- `reports/decision_review/ADJUSTMENT_LEDGER.md` (NEW) — 系統調整 ledger，含 Rec 7 / Rec 8 / Pill alignment 三筆 entry
- `reports/decision_review/ADJUSTMENT_LEDGER_SCHEMA.md` (NEW) — schema + 維護規範
- `event_index.json` schema bump v1.0 → v1.1（新增 industry_rollup + adjustment_ledger_active 兩個 top-level 欄位）

### Changed
- `scripts/extractors/deep_dive_extractor.py` — `tuning_hooks` 加 `sub_industry_heat` 欄位（fail-soft：若 join helper 失敗只寫 `{"error": "..."}`，不影響其他欄位）
- `reports/decision_review/REVIEW_PROMPT.md`：
  - 新增 Step 0「Adjustment Evaluation」— LLM 開頭先讀 ledger，對每筆 active Rec 比對 metric 變化下 improved / no_change / regressed 判斷
  - 輸出格式新增「## 0. Adjustment Evaluation」表 + 「## 1.5 Industry Rollup」表

### Why
- User 觀察：本週 CPU+memory 市場共識強 / 光通訊+SaaS 弱，但 REVIEW_2026-05-09 的 Pattern 1 只看 ticker（AMD/MU/INTC repeat-miss），沒做 sub-industry rollup → sector heat asymmetry 完全沒進系統考量
- Root cause：`tuning_hooks` 沒 industry context 欄位 → REVIEW 只能用 ticker 名單表達 pattern，無法量化 sector tail-wind 跟 deep-dive miss 的關聯
- Rec 7 補 instrumentation（純資料注入，不改決策邏輯），下週 REVIEW 即可跑 industry rollup
- Rec 8 把 rollup 做進 build_event_index post-process，讓 REVIEW 開段就能引用
- Adjustment Ledger 解決「系統調整不被回測」的 meta-bug — 之前 Rec 應用後沒檔案紀錄，每次 REVIEW 等於從零開始無法評估前次調整是否有效。Ledger 把每筆 Rec 變成可追溯的實驗（hypothesis + target_metric + evaluation_history）

### 樣本驗證（smoke）
- `python3 scripts/_sector_heat.py AMD MU` → 兩檔正確 resolve 為 Technology / Semiconductors / sector_top_3=true / industry_top_30pct=true
- `_build_industry_rollup` 用 fake records 測試：Semiconductors bucket n=2 miss_rate=1.0 avg_miss_return=50.45 ✓
- `_load_adjustment_ledger` 從 ADJUSTMENT_LEDGER.md parse 出 3 個 active entry ✓

---

## [2.17.15] — 2026-05-09
### Fixed — Sector pill ring 全面對齊 tooltip 5-tier 語義

### Fixed
- `Dashboard/script.js` `pill-marketop` — 改 inline 5-tier 對齊 tooltip：≥80 紅 / ≥65 橙 / ≥50 琥珀 / ≥30 黃 / <30 綠（原本 `'amber'` polarity 全 amber，0-29 normal 應綠卻黃、80+ top 應紅卻 amber）
- `Dashboard/script.js` `pill-fg` — 改 inline 5-tier contrarian：≥75 紅 / ≥55 橙 / ≥25 黃 / <25 綠（原本 `'amber-bell'` 全 amber，extreme_fear 應綠 contrarian buy / extreme_greed 應紅卻都 amber）
- `Dashboard/script.js` `pill-cycle` — Mid 顏色 `#84cc16` lime → `#eab308` yellow 對齊 cy_mid 🟡；新增 `map` 欄位，`Distribution` 為 canonical key（保留 `recession` legacy alias）；segment label `REC`→`DIST`
- `Dashboard/script.js` `pill-vix` — 3-tier (18/25) → 5-tier (20/30/40) 對齊 vx_calm/normal/elevated/high/panic：≥40 紅 / ≥30 橙 / ≥20 黃 / <20 綠（原本 VIX 19 應綠卻 amber、VIX 32 應 amber 卻紅）

### Why
- User 看到 33 廣度分（5/8 修）後追問「所有 pill 一起檢查」
- 全 audit 發現 4 個 pill colors 跟 tooltip dot 顏色（🟢🟡🟠🔴）不對齊
- `_gaugeColor(s, 'amber')` 對 marketop 來說語義錯：tooltip 兩端有 🟢 跟 🔴，但 'amber' polarity 永遠回 amber 系列
- `_gaugeColor(s, 'amber-bell')` 同問題：F&G 是 contrarian（fear=綠/buy, greed=紅/sell），bell-shape amber 把方向都丟了
- VIX tooltip 是 5-tier 但 code 只 3-tier，邊界值（VIX 17-19、30-39）顏色錯
- Cycle 的 `Recession` key 跟 tooltip `cy_distribution` 不對齊，data 帶 `Distribution` 進來時 segment 不會 highlight

### 已 OK（無改動）
- `pill-breadth`（V2.17.14 已修 `'positive'`）
- `pill-ftd`（FTD_STAGES 4-tier 對 prime/standard/late_cycle/exhausted ✓）
- `pill-regime`（4 segment 對 RISK_ON/NEUTRAL/VOLATILE/RISK_OFF ✓）
- `pill-exposure`（V2.17.14 hardcode 紫修為 4-tier ✓）

---

## [2.17.14] — 2026-05-09
### Fixed — 廣度分數 ring 顏色跟 tooltip 5-tier 不一致

### Fixed
- `Dashboard/script.js` `_gaugeColor` — 新增 `polarity === 'positive'` 分支，對齊 breadth tooltip 5-tier 語義：≥75 深綠 / ≥60 綠 / ≥40 黃 / ≥25 琥珀 / <25 紅
- 原本 `'positive'` 字串不匹配任何分支，fall through 到 default 3-tier（40 / 70）→ score 33.1 < 40 → 紅，但 tooltip 同樣 33.1 是 `br_weakening` 🟠 琥珀，視覺矛盾
- `Dashboard/script.js` `pill-exposure` — hardcoded `#a78bfa` 紫 → 改 4-tier 對齊 exposure tooltip：≥85 綠 / ≥60 黃 / ≥30 琥珀 / <30 紅（midPct=50 從紫變正確的琥珀）

### Why
- User 截圖：score 33.1 落在 25-40 「走弱中」（tooltip 🟠 琥珀），但卡片 ring 顯示紅色
- Root cause：`_gaugeColor(s, 'positive')` 在原 function 沒有對應 branch → 走 fallback `s>=70 綠 / s>=40 黃 / else 紅`，跟 5-tier tooltip thresholds 不對齊
- Exposure ring 一律紫色（hardcode）跟 tooltip 4-tier 完全不對齊，狀態看不出
- 影響範圍：只有 breadth + exposure 兩處 call

---

## [2.17.13] — 2026-05-08
### Fixed — Heatmap 全頁掛掉（FMP 402 Restricted Endpoint）

### Changed
- `dashboard_server.py` `_heatmap_build_universe` — 改 load `Dashboard/heatmap_universe.json`（static），不再呼叫 FMP `sp500-constituent` / `nasdaq-constituent`
- `dashboard_server.py` `_heatmap_refresh_quotes` — 改 ThreadPool fan-out single `stable/quote`（20 workers default），不再呼叫 `batch-quote`
- `HEATMAP_REFRESH_SEC` default 180 → 600（3 min → 10 min），降低 daily call 量
- 新增 env `HEATMAP_QUOTE_WORKERS`（default 20）

### Added
- `Dashboard/heatmap_universe.json` — 517 ticker static universe（symbol/name/sector/industry），bootstrapped from `Dashboard/heatmap.json` 既有 cache。季度手動 sync。

### Why
- FMP 把 `sp500-constituent` / `nasdaq-constituent` / `batch-quote` 移到高 tier plan → 當前 plan 直接 402 「Restricted Endpoint」，不是 quota 問題（FMP dashboard 看不到用量）
- v3 endpoints 也已 retired (2025-08-31, 403 Legacy)
- heatmap 完全跑不起來（universe 0 rows → quotes 0/517）
- Probe 結果：`stable/quote`（單檔）/ `ratios-ttm` / `key-metrics-ttm` / `analyst-estimates` / `news/stock` / `historical-chart/5min` 仍 200 → 改用 fan-out 可繼續用，PE warmup / news hover / radar K-line 不受影響
- 每 10 min × 6.5h × 517 ≈ 20k calls/day，落在合法 daily 範圍

---

## [2.17.12] — 2026-05-08
### Fixed — 短期雷達 bearish theme top movers 全是 + 預測（方向矛盾）

### Fixed
- `skills/thematic-screener/scripts/screen.py` `select_top_movers_ranked()` — 加 direction-aware 排序：
  - bullish theme → DESC（top-N **最正** target_pct，long candidates）← 既有行為
  - **bearish theme → ASC**（top-N **最負** target_pct，short candidates / 跌勢預期最強名單）← 新增
  - 其他（neutral / unknown）→ DESC

### Why
- User 觀察：「短期雷達的 1d 5d 15d 預測區間怎麼都是+的」— 270 筆預測 232 筆正、37 筆負（86% 正向）
- Root cause：`select_top_movers_ranked` 不論 theme direction 都 sort DESC → bearish 主題（Cybersecurity、Clean Energy & EV、Cloud / SaaS 等）的 top 5 movers **全是該主題裡 5d_pct 最高的**，跟 theme bearish call 自相矛盾
- 例：Clean Energy & EV `direction=bearish` 但 movers 全 + (ORA +1.75 / HASI +1.65 / FSLR +1.84 / ON +2.12 / RIO +1.06)
- 修後 bearish theme 會 surface 跌最兇的 representative_stocks，雷達會出現預期下行的 movers，方向跟主題對齊
- predict.py 模型本身偏多（gamma_momentum × 6 主導，stage 2 stocks 都會給正分）— 這是另一個議題；本 patch 先讓**選股階段**對齊主題方向，方向矛盾的視覺先解掉

---

## [2.17.11] — 2026-05-08
### Fixed — Chain pill terminal 後不消失

### Fixed
- `Dashboard/utils.js` `pollChainPill` — terminal grace 改成從 `s.ended_at` 直接算 age（每 3s tick 算一次），取代原 setTimeout-based 邏輯。原本 timer fire 後 hide pill，但下一次 poll 看到 `status='done'`（server 保留 terminal state 到下次 chain）就 unconditionally 把 `hidden` class 移除 → pill 又跳回來。改 server-side timestamp 算 age：`Date.now() - ended_at > 60000` → 永久 hide 直到下次 chain 跑

### Why
- User 反饋 chain 跑完 ✅ 都顯示完成後 pill 還在右下角不消失
- setTimeout 模型的 race：timer 一次性 fire，但 polling 每 3s 又 unconditionally re-show pill
- Server-side `ended_at` 是真理：以它為基準算 age，每次 poll 都計算同一答案，不需要客戶端 state 追蹤

---

## [2.17.10] — 2026-05-08
### Changed — FTD gauge 顯示 ACTIVE STAGE 取代靜態 100 + 綠圈

### Changed
- `Dashboard/script.js` `renderSectorStatusStrip` FTD gauge — 之前固定顯示 `quality_score=100` + 綠色滿環，user 看好幾天都一樣不知道 FTD 走到哪一段。改為依 `days_since_ftd` 分 4 stage：
  - **Day 1-5（黃金期 PRIME）** — 綠 #22c55e、ring 100%
  - **Day 6-12（主升期 STANDARD）** — 黃 #eab308、ring 78%
  - **Day 13-20（補漲期 LATE）** — 橘 #f97316、ring 52%
  - **Day 21+（過熱期 EXHAUSTED）** — 紅 #ef4444、ring 22%
- 主體顯示 `Day N` 取代 `100`（讓 user 直接看到 FTD 已過幾天）
- Suffix 顯示 stage tag（黃金期 / 主升期 / 補漲期 / 過熱期）
- `displaySize` 改 `md` 讓 `Day N` + suffix 兩行排得下
- 非 confirmed state 也分別處理：FTD_INVALIDATED → 紅色「失效」、RALLY_ATTEMPT → 灰色「Day N · 反彈中」、其他 → 灰「無 FTD」

### Why
- User 反饋：FTD gauge 永遠顯示 100 + 綠圈，看好幾天都不變，**沒辦法知道現在是黃金 / 主升 / 補漲 / 過熱期**。tooltip 內容對但 gauge 本體沒呼應 → 視覺被誤導
- `quality_score=100` 是 FTD detector 的 binary confidence (FTD 確認 = 100)，不適合直接餵 gauge — 真正動態資訊在 `days_since_ftd` 對應的 stage
- Ring 填滿百分比改 reflect「剩下多少 momentum window」（prime 100% → exhausted 22%），視覺上一眼看出能量衰減

---

## [2.17.9] — 2026-05-08
### Changed — Decisions page tooltip 統一 sector 視覺 + 重寫關鍵 chip 解釋

### Changed
- `Dashboard/decisions.html` — 移除 `<div id="decision-tip">`，改加 `<div id="signal-tip-tooltip" aria-hidden="true">` 跟 sector / index page 共用同一個 tooltip element
- `Dashboard/page-decisions.js` `initDecisionTip` — 改 render 進 `#signal-tip-tooltip`，使用 `.stt-title` / `.stt-desc` / `.stt-hint` classes 取代舊 `.tip-title` / `.tip-desc` / `.tip-scale`，並加 visible class 觸發顯示。新增 `_md()` helper 支援 `**bold**` + 換行 markdown
- `Dashboard/style.css` — 移除 `#decision-tip` + `.tip-*` legacy rules（已由 `#signal-tip-tooltip` + `.stt-*` 取代）
- `Dashboard/page-decisions.js` `DECISION_TIPS` — 重寫以下 chip 的 desc / scale 文字，用 user-facing 語言（操作建議、為什麼重要、警示）取代過去純定義式描述：
  - `contrarian` — 解釋方向 ≠ macro 的兩種 thesis 假設 + sizing 建議
  - `fragility_robust / moderate / fragile` — 三層級各自的「下一步怎麼操作」（standard cap / 降一檔 / 大砍 + OFFRAMP）
  - `signal_polarization_bipolar / mixed` — lane 共識度 + 為什麼 verdict 會晃 + sizing 對應
  - `red_team_disagree` — 解釋 LLM vs DET 雙路徑 + 6 條 kill trigger 細節
  - `val_disagree` — LLM > DET vs LLM < DET 各自的警示
  - `action_attack / wait / defensive` — 操作層判定（非 final_decision）+ 為什麼會 BUY + DEFENSIVE
  - `moat_narrow` — 為什麼 entry timing 比 WIDE 重要 + swing vs long-hold 操作差異
  - `pattern_false_breakout` — bull trap 機制 + 不追價規則 + 反指標
  - `market_weak` — institutional distribution 訊號 + 該怎麼處理已持有
  - `decision_confidence` — 70% 不是「會漲」是「重跑 100 次有 70 次同方向」+ 跟其他 chip 怎麼一起讀

### Why
- User 反饋 ALAB 卡片 chip 的 tooltip 風格沒跟 sector page 統一，且**解釋寫得太籠統 / 過於技術定義式**，看不出「我接下來該怎麼做」
- Visual：`#decision-tip` 跟 `#signal-tip-tooltip` 雖然 base 都是 `var(--bg-card)`，但 stt-* 系列 padding / radius / shadow / visible-class 都是 sector page 已調好的版本；統一可避免 cross-page 風格漂移
- 內容：原 desc 多是「Tail-risk 三維評估：論點建立在多支柱之上」這種定義句 — user 看完還是不知道倉位該不該降。重寫後每個 chip 都包 (1) 機制 / 為什麼觸發 (2) 對 sizing / 操作的具體含義 (3) 跟其他 chip 怎麼搭配看
- markdown helper 讓 desc 能用 `**bold**` 強調操作要點 + `\n\n` 段落分隔，可讀性大幅提升

---

## [2.17.8] — 2026-05-07
### Added — 決策日曆卡片 17 個 label 加 rich tooltip + 修 V4.8 mis-stamp guard

**動機**：User 觀察 TSM 卡片顯示「V4.8」標籤但專案已到 V5.0；卡片上「中等脆弱 / 訊號兩極 / Red Team 不一致」等 pill 用原生 `title=` 沒有富格式說明。

### Added
- `Dashboard/page-decisions.js` `DECISION_TIPS`：17 個新 entries（zh+en）涵蓋所有 pill：
  - **det_shadow**: signal_polarization_bipolar / mixed, red_team_disagree, val_disagree（4）
  - **action_label**: action_attack / action_wait / action_defensive（3）
  - **moat_assessment**: moat_wide / moat_narrow / moat_eroding / moat_none（4）
  - **technical pattern**: pattern_breakout / continuation / consolidation / pullback / false_breakout / topping / downtrend / oversold_bounce（8）
  - **market_strength**: market_strong / market_neutral / market_weak（3）
  - **decision_confidence_pct**: decision_confidence（1）
  - **protocol version bookmark**: version_v50 / v48 / v47 / v46 / legacy（5）
  - 每筆都含 `title` + `desc` + 可選 `scale` 三段（reuse 既有 `#decision-tip` rich tooltip render path，跟 fragility tip 同視覺）

### Changed
- `Dashboard/page-decisions.js` `buildV48StatusPills`：所有 native `title="..."` 換成 `data-tip-key="..."` reference 對應上述 entries
- `Dashboard/page-decisions.js` `buildVersionBookmark`：加 `tipKeyMap` 讓 V5.0 / V4.8 / V4.7 / V4.6 / LEGACY 各對應 rich tooltip + cursor:help
- `investment/scripts/validate_session_export.py`：新增 V4.8 mis-stamp guard — entry 若有 V5.0-only fields (`valuation_lane` / `fair_value_summary`) 但 stamp 為 `V4.8` → fail，附 patch 指示

### Fixed
- `investment/invest_logs/history.json` — 今天 TSM (2026-05-07) entry `session_export_version` `V4.8` → `V5.0`（entry 完整 V5.0 fields 都齊全，是 Phase 5 寫 history 時誤標）

### Why
- 每張 pill 都有清楚 scale + 量化邊界，user hover 一眼看完含義 + 何時該擔心；不再依賴記憶 / 翻 SKILL.md
- mis-stamp guard 是長期 hygiene：未來若 Claude 在 Phase 5 又寫錯版本，validator 會立刻擋下來（之前 V4.8 / V5.0 兩者都收 → 沒抓出來）
- 老 V4.8 真實 entries（71 筆 4/18-5/02）全部沒 V5.0 fields → 新 guard 不會誤殺

---

## [2.17.7] — 2026-05-07
### Fixed — Tooltip 內 `**bold**` markdown 真正渲染為粗體 + 段落分行

**動機**：User screenshot — earnings 頁 QUALITY tooltip 顯示 `**1. Margin 趨勢**` 字面 markdown，沒被解析為粗體；4 個 sub-component 也沒換行擠成連續一段。30+ 個 SIGNAL_TIPS 都受影響（FTD / Breadth / Market Top / 4 個 ed_score_* / EPS / Revenue / Geographic / Segment 等）。

### Fixed
- `Dashboard/utils.js` `buildSignalTipHTML`：
  - 新 `_renderTipMarkdown(s)` helper：先 escape HTML（defense-in-depth）→ 轉 `**bold**` 為 `<strong>`（non-greedy `[^*]+?` 避免跨段吃字）→ 拆 `\n\n` 為 `<p>...</p>` 段落 → 殘餘 `\n` 為 `<br>`
  - `t.desc` / `t.hint` 都套用此 helper（單行字串自動跳過 `<p>` wrap，不影響短描述）
- `Dashboard/style.css` `#signal-tip-tooltip`：新 `.stt-desc p` / `.stt-hint p` margin reset (0 0 6px 0, last-child 0)；`.stt-desc strong` / `.stt-hint strong` font-weight 700 + 同 var(--text-main) 顏色

### Verified
- helper 單元 case：`衡量公司**財報體質乾淨度**。\\n\\n**1. Margin 趨勢**：毛利率\\n**2. Accruals**：應計項` → `<p>衡量公司<strong>財報體質乾淨度</strong>。</p><p><strong>1. Margin 趨勢</strong>：毛利率<br><strong>2. Accruals</strong>：應計項</p>`
- JS syntax check rc=0
- 影響範圍：30+ 個 tooltip（涵蓋 index.html status pills、earnings.html 4 score bars、earnings-detail.html 8 chart tips）— **0 source string 重寫**

### Why
Source string 維持 markdown 風格易讀易維護；render layer 一處修補對所有 tooltip 生效，未來新加 tooltip 直接用同 markdown 風格 → 無需另寫 HTML escape boilerplate。

---

## [2.17.6] — 2026-05-07
### Fixed — 盤前檢查 Phase 1 真正並行 + modal 完成後自動關閉

**動機**：User 觀察 51m 53s 總時間 = 16:27 + 17:35 + 17:46，三段順序排隊（標籤雖寫「平行執行」實際 sequential）；且 chain 完成後 modal 不自動關閉，需手動 ESC。

### Fixed
- `dashboard_server.py` `run_premarket_chain._run()` Phase 1：改為 daily + news 兩 thread `start() + join()` 真正並行。`phase1_errors` list 收集兩條任一失敗 → raise 中止整 chain。Phase 2 sector 等兩條都結束才開始
- `Dashboard/script.js` `_pollPremarketChain` done 分支：updateDashboard + showToast 完成後再延遲 4s 自動 `closePreflight()`（user 來得及看 ✅ 結果再回正常 UI）

### Why
- daily_update.sh 抓 breadth/FTD/macro → 寫 data.json；news protocol 抓 RSS / Finnhub / FMP / SEC → 寫 digest.json。**兩者獨立**，sequential 等於浪費 wall-clock 時間
- daily 跟 news 用**不同 state machine**（`_daily_update_state` vs `_protocol_state`），並行無 lock conflict
- sector 真的 depend 兩者，必須等 Phase 1 全部完成才能跑

### Expected impact
- 之前：Phase 1 wall = daily 16m + news 17m = ~33min；總 chain ~51min
- 之後：Phase 1 wall ≈ max(daily, news) ≈ 17min；總 chain ≈ 17 + sector 18 = **~35min**（省 16 分鐘）

---

## [2.17.5] — 2026-05-07
### Added — 盤前檢查跨頁狀態 pill（atomic 三段式）

### Added
- `Dashboard/utils.js` — 新 `ensureChainPill()` + `pollChainPill()`：每 3s 拉 `/api/run-premarket-chain/status`，當 chain 非 idle 且 preflight modal **不在 open 狀態**時，於右下角浮出單一 pill；包含 daily / news / sector 三個 sub-row（icon + label + meta）。Terminal `done`/`error` 後 60s 自動消失
- `Dashboard/style.css` — `.chain-status-pill` + 配套 `.chain-pill-*` rules：amber 色框（呼應 📋 前瞻 button），固定底右 18px / 18px。當 `proto-status-pill` 同時可見，自動加 `.has-proto-pill` 抬到 92px 上方（疊接，不重疊）

### Why
- User reflow：盤前檢查 chain 跑 ~25-30 分鐘，user 不可能整段保持 modal 開。關掉 modal 後就「看不到 chain 在跑哪一段」。Pill 解決可視性
- **單一 pill 內含 3 行**而非 3 顆獨立 pill：chain 是 atomic operation（daily → news → sector 順序強制），不應允許 user 個別 dismiss / 誤判單段已結束 → 全 chain 結束才 auto-hide
- Modal 開時隱藏 pill 避免 UI 重複（modal 內已有完整 chain 列；pill 是 modal 關閉後的 fallback view）

---

## [2.17.4] — 2026-05-07
### Fixed — pre_earnings 報告在 recent_analysis 隱形

### Fixed
- `bridge.py` `extract_audit_history()` fallback scan — `*_pre_earnings.md` 檔現在用 compound dedupe key `(ticker, "pre_earnings", date)`，不再被同 ticker 既有 investment-protocol 條目蓋掉。新增 `decision: "PREVIEW"` + `report_type: "pre_earnings"` 標記
- `Dashboard/i18n.js` — 新增 `status.PREVIEW` 翻譯（zh: 「財報前瞻」/ en: 「PREVIEW」）
- `Dashboard/components.js` `renderAuditCard()` — 識別 `decision === 'PREVIEW'` 或 `report_type === 'pre_earnings'`，狀態色用 amber `#f59e0b`（與 📋 前瞻 button 視覺一致），不再跌回灰色 `var(--text-muted)`

### Why
- User 跑 CRWV / ARM 前瞻後產出 `reports/<DATE>_<T>_pre_earnings.md`，但 dashboard recent_analysis 都不顯示。Root cause：bridge fallback 用 `if t_part not in audit_map` 純 ticker key dedupe，CRWV 既有 history.json 條目 → pre_earnings 全被靜默丟棄
- Compound dedupe key 讓同 ticker 可同時保留 investment-protocol 決策 + pre_earnings 報告（多份 pre_earnings 也按日期分開保留）
- Amber 視覺色與既有 📋 前瞻 button 一致，user 一眼能分辨 PREVIEW 不是正式分析

---

## [2.17.3] — 2026-05-07
### Changed — Top 5 競品 row 改用 signal-tip 風格 rich tooltip

**動機**：v2.17.2 競品 row 用原生 `title=` 屬性，跟 sector page 其他元素（status pills / FTD / Breadth 等）的 frosted dark tooltip 視覺不一致。改為 reuse `#signal-tip-tooltip` element + `.stt-*` CSS classes。

### Changed
- `Dashboard/page-sector.js`:
  - 競品 row 移除 `title=`，改帶 `data-comp-tip="<json>"`（packed: ticker / company / industry / ceo / price / market_cap / sector / verdict）
  - 新 `initCompetitorTooltip()` IIFE 在檔尾：mouseover/mouseout listener `[data-comp-tip]` → 解析 JSON → 用 `.stt-title / .stt-desc / .stt-stages / .stt-hint` 結構 render → reuse `#signal-tip-tooltip` element + 同 CSS（dark frame + backdrop blur）
  - Position：偏好 row 右側 →（fallback above → fallback below），與其他 tooltip 行為一致
  - 與既有 SIGNAL_TIPS engine 不衝突：trigger 屬性不同（`data-comp-tip` vs `data-signal-tip`）

### Why
視覺一致性 — sector page 上 7 個 status pill + 競品 row 都用同一套 tooltip 樣式；無新增 DOM 元素 / 無新增 CSS（純 reuse）。

---

## [2.17.2] — 2026-05-07
### Added — Dashboard sector card 內嵌 Top 5 競品 collapsible

**動機**：v2.17.0 競品地圖只在 `reports/<DATE>_sector_report.md` MD 檔，user 要 surface 到 Dashboard sector page 卡片內方便瀏覽。

### Added
- `bridge.py` — 新 `_extract_sector_competitors()` (~50 行)：iterate `SECTOR_TOP_5` + reuse `get_profile()` (24h cache)，回傳 dict[sector → 5 × {ticker, company, market_cap, industry, ceo, price}]。`extract_sectors()` 把 `competitors[]` field 附到每個 sector entry → data.json
- `Dashboard/page-sector.js` `buildSectorCard` — 新 `competitorsBlock`：`<details>` 預設摺疊 + mini table（Ticker / Company / Market Cap），industry/CEO/price 進 row title tooltip。Click ticker `<a>` 跳 `momentum.html?sector=<gics>&ticker=<T>`，event.stopPropagation 避免觸發外層卡片 jump
- `Dashboard/sector.html` 內嵌 CSS — `.sec-comp*` mini-table style：dashed top border / amber summary chevron / row hover / ticker link 用 sector verdict color

### Why
- bridge 端 reuse 現成 24h profile cache，0 新 FMP call cost
- UI 端預設摺疊不佔卡片空間，點開才看；row tooltip 補完整 metadata（industry/CEO/price）避免 table 過寬
- 跳 momentum 沿用既有 `data-sector-jump` 模式 + 加 ticker query param

### Verified
- bridge.py 跑完 data.json Technology sector competitors 5 個 (AAPL $4.2T / MSFT $3.1T / NVDA $5.1T / AVGO $2.0T / ORCL $0.6T)
- JS syntax check rc=0

---

## [2.17.1] — 2026-05-07
### Fixed — preflight UI 計時、CRWV 財報日曆過濾、pre-earnings 資訊密度

### Fixed
- `dashboard_server.py` — `run_premarket_chain._run()` daily polling 改從 `_daily_update_state["started_at"]` 直接算 elapsed，不再依賴從未被寫入的 `elapsed_sec` 欄位（UI Phase 1 daily 卡 `0s` 不動）
- `dashboard_server.py` — `_wait_protocol_completion()` 同 pattern 修：news / sector phase 的 `_protocol_state["elapsed_sec"]` 只在收尾才寫，poller 改算 `started_at` diff
- `bridge.py` — `_load_calendar_universe()` 新增 `watchlist.txt` 為第 4 個 universe source；CRWV 等 IPO / out-of-index 名稱可手動 append 即被收進 earnings calendar，不再被 SP500∪Nasdaq100∪SOX gate 砍掉
- `skills/momentum-monitor/scripts/universes/watchlist.txt` — 建檔，預載 CRWV
- `skills/earnings-valuation-forecaster/scripts/forecast.py`：
  - `FMP.income_quarter` limit 5→8（pre-earnings watch_metrics 算 YoY 需 ≥5Q）
  - `_next_earnings_info()` 過濾條件 `date > today` → `date >= today AND epsActual is None`，**今日報財報的 ticker** consensus card 不再是空的
  - 新 `_watch_metrics_computed(income_q)` — 從 income_q 計算 **實值** Watch List：Revenue YoY + accel/decel、GM% 4Q trend + QoQ bps、OpM% trend、EPS trend；取代純文字 hint 模板
  - 新 `build_ps_scenarios()` — TTM EPS ≤ 0 時改用 P/S × forward revenue 法產 12M target（之前直接顯示「不適用 — 請改用 P/S 或 EV/Sales」全空）
  - 新 `_merged_watch_metrics()` — earnings-analyst cache（segments / quality flags） + computed real values 合併 dedupe，capped 6 chips
- `Dashboard/page-earnings.js`：
  - 12M target 區塊 method-aware label（PE 法 / P/S 法（負 EPS））+ TTM rev / 當前 P/S / 近期 YoY meta line
  - seasonality SVG GM% 標籤 collision 防撞：當 GM% circle 落在 bar top label 14px 內，label 自動 flip 到 circle 下方（之前 $1.21B 與 74% 重疊）

### Why
- Preflight UI 卡 `0s`：daily_update.sh 跑得好好的（log streaming 有 `[N/6]` step），但 `elapsed_sec` 從未被寫入 → user 以為 chain 卡死。Fix at consumer side（poller 自算）比加 ticker thread 簡單
- CRWV 2025-03 IPO，今天（2026-05-07）報財報但被 SP500∪Nasdaq100∪SOX universe gate 砍掉，calendar 看不到、財報分析輸入欄 filter 也濾掉。Watchlist mechanism 給 user 後續加 IPO / out-of-index 名稱的乾淨 override
- pre-earnings 卡片之前對 CRWV 顯示：consensus EPS/Rev = `—`、Watch List 全是 generic 模板字（「QoQ ±100bps 看 mix / pricing」沒實值）、12M target 全空。User 反饋「看不出資訊」。三個洞各自 fix：consensus filter、watch_metrics computed、P/S scenarios

---

## [2.17.0] — 2026-05-07
### Added — Phase D + B-2 batch（institutional format / TAM block / 競品地圖 / Write 隔離）

**動機**：Gemini cross-check 顯示 reference/financial-services 還有 4 個小強化點未做 — 機構級報告長度規範、個股 fundamentals lane TAM block、sector report 競品比較表、news subagent Write 隔離 doc。詳見 plan file Phase D。

### Added
- `skills/earnings-analyst/SKILL.md` — 「Institutional Format Standards」section：8-12 頁 / 3,000-5,000 字 / 1-3 summary tables / 8-12 charts / 24-48h turnaround / NEW info focus / format checklist（仿 reference equity-research/earnings-analysis SKILL.md）
- `investment/investment_protocol_v5_0.md` Phase 2 Fundamentals subagent — 新 V2.17.0 sub-block「TAM / Market Position」必填：tam_usd / industry_5y_cagr_pct / company_revenue_share_pct / position_label / competitive_moat_evidence。**禁止 LLM 自編 TAM 數字**，缺資料 → null + 註記
- `investment/phase5_export_schema.md` `fundamentals_lane.market_position` schema 新增（V2.17 optional，validator 不擋向下相容）
- `news/news_protocol_v2.md` — 新「TOOL BOUNDARIES — Write Isolation」section：tool 權限矩陣（triage / 4-view subagent reader-only，arbiter 持 Write）+ Agent tool prompt 強制首句約束 + PM 驗證機制
- `sector/scripts/render_sector_report.py` — 新 `render_competitive_landscape()`：reuse `SECTOR_TOP_5` + `get_profile()` (24h cache)，per-sector 渲染 top-5 比較表（Ticker / Company / Industry / Market Cap / Price / CEO / Differentiator placeholder）。Sector 顯示順序依 Phase 5 verdict score 由高到低。`_HAS_COMPETITIVE` graceful skip 若 company_context import 失敗

### Why
- D-1：reference earnings-analysis 是機構標準格式範本，加長度規範可讓 render.py 後續加 lint 檢查（未做）
- D-2：sector report 缺最後一塊「sector 內哪個 stock 大」直觀比較；reuse `SECTOR_TOP_5` 0 維護成本，0 額外 FMP call（cache 24h）
- D-3：fundamentals lane 之前只看 P/E + FCF + moat，**缺市場層級 sizing**（TAM / share），這正是 reference sector-overview pattern 的核心。加進去後 fundamentals lane 視野完整覆蓋公司 ↔ 產業
- B-2 #7：news 是攻擊面最大 protocol（untrusted RSS / scraped headlines），formalize Write 隔離 pattern 是長期 security 投資；當前實作無破壞性，純文件規範 + spawn-time prompt 約束

### Verified
- render_sector_report.py --stdout：11 sectors × 5 tickers 全 render（GOOGL Alphabet $4.81T / etc.），sector 排序依 verdict score
- 既有 sector validator 不需動（純 render 層改動）

### Phase D 完成度
- ✅ D-1 / D-2 / D-3 + B-2 #7 doc-level
- 待做：B-2 #7 真正 spawn Agent tool 時加 prompt 約束（在 news protocol 實際執行時生效，不需 code 改動）

---

## [2.16.0] — 2026-05-06
### Added — 財報前瞻 popup card modal（圖形化視覺優化）

**動機**：v2.15.3 「看前瞻報告」開新分頁顯示 raw MD，user 要 popup card view 易讀 + 圖形化。

### Added
- `dashboard_server.py` — 新 endpoint `GET /api/preview-cache/<TICKER>` 讀 forecaster cache JSON 回傳（404 若 cache 無 pre_earnings block；500 若 IO 錯誤）
- `Dashboard/earnings.html`:
  - 新 modal scaffold `#ea-preview-modal`（amber accent bar + close button + raw MD fallback link）
  - 內嵌 ~220 行 CSS：section card frame / header card / stats row / SVG chart frame / watch chips / 12M scenario columns / caveats `<details>` / responsive media query
- `Dashboard/page-earnings.js`:
  - `wirePreviewModal()` + `openPreviewModal(ticker)` + `closePreviewModal()`：fetch endpoint → render 5 sections
  - `renderPreviewModal()`：Header card（ticker + countdown badge today/明天/Xd + price）+ Consensus（EPS / Revenue 大數字並排）+ Seasonality（SVG bar chart + GM% line overlay）+ Watch chips（icon + title + hover hint）+ 12M Scenarios（bull/base/bear 3-col + target 大字 + upside %）+ Caveats `<details>` 預設摺疊
  - `renderSeasonalitySection()`：純 SVG 760×130，amber bars + emerald GM% polyline + dashed legend
  - `eaSetRunBannerDone` preview 分支：button onClick 改呼叫 `openPreviewModal()` 而非開新 tab；保留 raw MD fallback link 在 modal header

### Visual design
- amber `#fbbf24` accent（跟 morph button 一致辨識）
- bull `#10b981` / base `#a1a1aa` / bear `#f87171` 三色 scenario
- countdown badge：今天 = 紅 `#f87171`，> 0 天 = amber
- watch chip hover 變 amber outline + bg
- responsive：< 640px stats / scenarios 變 1-col stack

### Negative-EPS handle
12M section 顯示「⚠ TTM EPS ≤ 0，PE 估值不適用」灰色 placeholder，其他 section 照樣 render。

### Verified
- CRWV cache shape OK (`pre_earnings` block 含 next_earnings / seasonality_4q / watch_metrics / scenarios=null)
- JS syntax check rc=0

---

## [2.15.4] — 2026-05-06
### Fixed — 財報日曆 ARM missing + 過濾 SP500/Nasdaq100/SOX universe

**動機**：User 發現 FMP `/stable/earnings-calendar` 直接打有 ARM 5/6 row，但 Dashboard 財報日曆沒出現；且整體 2840 個 earnings events 太雜。Root cause 兩個 bug：

1. **Cache stale**：`.cache_bridge/fmp_earnings_<date>.json` 凌晨 00:03 抓的，FMP 後續才 add ARM 5/6 → cache 整天不更新 → ARM 永遠不在
2. **FMP 4000-row cap**：bridge 用 `from=today, to=today+14d` 14-day window 撞 FMP 響應 4000 行上限，**API 從最早日期開始截**（drop today/tomorrow），ARM 5/6 整段被 skip

### Changed
- `bridge.py` `_from_fmp_earnings`:
  - **Cache TTL 4h**（之前永久 day-key cache）— FMP 整天會陸續 add 新 ticker，4h 重 fetch 抓到 ARM 這類 last-minute add
  - **Chunked fetch 3 段**：`(today-1, today+4)` → `(today+5, today+9)` → `(today+10, today+horizon)`，dedup by `(symbol, date)`。每段遠低於 4000 cap → 完整覆蓋
  - **Universe filter**：新 `_load_calendar_universe()` 讀 `skills/momentum-monitor/scripts/universes/{sp500,nasdaq100,sox}.txt` (~530 unique tickers)，`symbol not in universe → skip`
- `bridge.py` `aggregate_upcoming_events`:
  - **Final universe gate**：archive 累積的歷史 events 也用同一 universe 過濾，避免舊 entry 漏網

### Verified
- 4000 raw rows → 93 fresh events → final 139 (含 archive)，下降 ~95%
- ARM 5/6 出現 in data.json upcoming_events ✓
- VZ / GM / KO / V / HOOD 等 blue chip 仍在 calendar

### Why
Universe sets 是現成 `momentum-monitor` 維護的官方 index 成員 list，零維護成本。chunking 一次 daily_update +3 calls 對 250/day FMP free tier 無壓力。

---

## [2.15.3] — 2026-05-06
### Changed — 財報前瞻 done banner 加「📄 看前瞻報告」link button

**動機**：v2.15.0 跑完前瞻 banner 雖 ✓ Done，但 user 看不到產出 MD（earnings 頁卡片只列 post-earnings cache，pre-earnings 寫到 `reports/<DATE>_<T>_pre_earnings.md` 後沒 surface）。

### Added
- `Dashboard/earnings.html` — 新 banner button `#ea-run-view-report`（amber `<a target=_blank>` link，預設 hidden）
- `Dashboard/page-earnings.js`:
  - 新 module-level state `_eaActiveMode`：`'earnings' | 'earnings_preview' | null`
  - `runEarningsPreview` / `runEarnings` 起跑時各自 set mode
  - `eaShowRunBanner` title 依 mode 切 `財報前瞻中` vs `財報分析中`
  - `eaSetRunBannerDone` 依 mode 分流 affordance：
    - preview → 顯示「📄 看前瞻報告」連到 `/reports/<TODAY YYYYMMDD>_<TICKER>_pre_earnings.md`
    - earnings → 維持「重新整理」button
  - poller done 分支：preview mode 不跑 `loadAndRender()`（earnings_analyses 不會更新）；earnings mode 仍 reload data.json 拿新卡片
  - banner 隱藏 / dismiss 時清掉 `_eaActiveMode`
  - 補：banner 從 server status 回填 `_eaActiveMode = s.name`（page refresh 中途 resume 也能正確 render button）

### Why
B 方案（手動 click 看報告 vs 自動開新 tab）：尊重 user 是否想立刻看，避免分心。amber 色與既有 morph button 一致辨識「前瞻 = 黃色」。

---

## [2.15.2] — 2026-05-06
### Fixed — `--pre-earnings` 對 negative-EPS ticker (CRWV / RIVN / SOFI) 不再 abort

**動機**：user 跑 CRWV 財報前瞻 → forecaster 因 TTM EPS = -2.49 直接 return `unsupported` rc=1 → server SCRIPT_PROTOCOLS 標 error。但 pre-earnings cheat sheet（consensus / seasonality / watch list）**根本不需要 positive EPS**——只有 12M target price section 才要 PE math。

### Changed
- `skills/earnings-valuation-forecaster/scripts/forecast.py`:
  - Negative TTM EPS + `--pre-earnings` flag → 改回傳 `status: "ok_partial"` 含 `pre_earnings` block + `scenarios: null` + `negative_eps: true`，而非整個 abort
  - `to_markdown_pre_earnings()` 偵測 `negative_eps` → header 加 ⚠ 警告 + skip Forward EPS line + 12M section 替換為 explanation 註解（指向 P/S / EV/Sales 替代）
  - `main()` 接受 `ok_partial` 為 success rc=0（僅 pre-earnings mode；plain mode 仍嚴格 require positive EPS）

### Why
unprofitable growth tech（CRWV / RIVN / SOFI / RDDT）仍有 quarterly earnings reports，pre-earnings cheat sheet 對這類名單照樣有用：consensus EPS（即使 -$0.89）+ revenue trajectory + GM% trend + 待觀察 metric 都是有用 input。**前瞻 ≠ 估值**，沒理由因 negative EPS 全 reject。

### Verified
- CRWV `--pre-earnings` → rc=0，產出完整 cheat sheet（next earnings 1d / consensus / 4Q seasonality + revenue 0.98→1.57B 成長軌跡 / 12M section graceful skip）
- NVDA `--pre-earnings` → rc=0，仍正常產出 12M scenarios（regression OK）

---

## [2.15.1] — 2026-05-06
### Changed — Earnings command bar 即時 morph + 模式 hint

**動機**：V2.15.0 morph 邏輯只在卡片上生效；user 從 input bar 手動輸入 ticker 也應該即時 reflect 模式（前瞻 vs 分析上季），不要等按下執行才知道跑哪一個。

### Added
- `Dashboard/page-earnings.js`:
  - 新 `upcomingEarningsMap` (ticker → `{date, days_until}`) — 從 data.json `upcoming_events`（已是 FMP confirmed）抽 future earnings，nearest-date wins
  - `rebuildUpcomingEarningsMap()` 在 `loadAndRender()` + DataStore subscribe 都呼叫
  - `wireCommandBar()` 新 `syncMode()` — input listener 每次 keystroke 比對 map：
    - `0 ≤ days ≤ 7` → button 變 amber「📋 財報前瞻」+ hint「⚡ 下次財報 X（Yd）→ 跑前瞻 cheat sheet」
    - `8 ≤ days ≤ 30` → button 維持 default「執行」+ hint「📅 下次財報 X（Yd）→ 跑分析上季（前瞻在 7d 內才開放）」
    - 其他 → button「執行」+ hint「📊 無近期確認財報日 → 跑分析上季」
  - `trigger()` 改依 `btn.dataset.mode` 分派 `runEarningsPreview` vs `runEarnings`
- `Dashboard/earnings.html` + 內嵌 CSS：
  - cmdbar 下方加 `#ea-cmd-hint` span
  - `.ea-cmdbar-btn-preview` amber 變體
  - `.ea-cmd-hint[data-mode="preview"]` amber / `soon` slate / `post` zinc 三色

### Why
User 觀察：「假如我輸入的是七天內的 ticker, 應該要註明是財報前瞻」。直接 reuse `data.json.upcoming_events`（calendar cache 同源），無需新 endpoint，0 額外 FMP 呼叫。Map 在 page load 一次建好，每次 keystroke 是 in-memory lookup（O(1)），延遲 0ms。

---

## [2.15.0] — 2026-05-06
### Added — Pre-earnings 前瞻 mode + Dashboard 7-day morph button (Phase B-1)

**動機**：reference/financial-services equity-research vertical 有 `earnings-preview` skill；本專案決定以**擴充既有 forecaster** 達成（避免新 skill 維護成本）+ Dashboard UI 在財報 ≤ 7 天時自動 morph 出「📋 前瞻」button，跑 forecaster --pre-earnings cheat sheet。**option Z 邏輯**：≤7d 用 forecaster（最準）、>7d 維持 earnings-analyst（看上季品質），兩 skill 互補不重疊。詳見 `~/.claude/plans/refernce-finanical-services-mcp-server-snazzy-canyon.md`。

### Added
- `skills/earnings-valuation-forecaster/scripts/forecast.py` — `--pre-earnings` flag (~150 行)：
  - 新 FMP method `earnings_upcoming()` → `/earnings?symbol=` future-dated row 抓 `epsEstimated` / `revenueEstimated`
  - `_seasonality_4q()` — last 4Q revenue / EPS dil. / GM% chronological 表
  - `_watch_metrics_from_cache()` + `_watch_metrics_default()` — 從 earnings-analyst cache 抽 segment names + quality_flags 強化 watch list；無 cache fallback 5 條 generic
  - 新 MD layout `to_markdown_pre_earnings()` — cheat sheet at top, seasonality middle, 12M scenarios demoted to bottom supplementary
  - 輸出 `reports/<DATE>_<TICKER>_pre_earnings.md`（與 plain `_valuation.md` 區分；cache key 也分離）
- `dashboard_server.py` — `SCRIPT_PROTOCOLS` 新基礎設施（~120 行）：
  - 新 dict 註冊純 subprocess 協議（不走 Claude turn，省 ~$0.02/click + ~30s）
  - `_run_script_protocol()` 鏡像 `run_protocol` 的 state machine（status / log / cancel / banner 全相容）
  - `enqueue_protocol` + `_label_for` + `run_protocol` 都加 SCRIPT_PROTOCOLS 分支
  - 註冊 `earnings_preview` 路由 forecast.py --pre-earnings，timeout 180s

### Changed
- `Dashboard/page-earnings.js` — 卡片 render 計算 `daysTo(next_earnings_est)`，`fmp_confirmed` 且 `0 ≤ days ≤ 7` → swap 重跑 button 為「📋 財報前瞻」（amber 色）。新 `runEarningsPreview()` handler、click 分派 action='preview'、poller 接受 `name='earnings_preview'`
- `Dashboard/page-calendar.js` — Option Z 4-quadrant 邏輯：
  - ≤7d + nocache → 「📋 前瞻」單 button（forecaster 最準時機，post-earnings 跑會吃舊 cache）
  - ≤7d + cached → 看報告 + 📋 前瞻 + 🔄（上季 / 下季 / 重跑上季 三事權各對應一鈕）
  - \>7d + nocache → 📊 跑財報分析（維持，user 可主動分析上季）
  - \>7d + cached → 看報告 + 🔄（維持）
  - 新 `window.runEarningsPreview()` global handler
- `Dashboard/earnings.html` + `Dashboard/style.css` — `ea-act-btn-preview` + `cal-earnings-btn-preview` amber 色 (`#fbbf24`) variant
- `skills/earnings-valuation-forecaster/SKILL.md` — 「Pre-Earnings Mode (V2.15.0+)」section：output schema / 適用條件 / UI 觸發規則 / 不適用場景
- `CLAUDE.md` — trigger 表加「財報前瞻」+ Ops Shortcuts 加 `--pre-earnings` CLI

### Why
forecaster 距離 earnings 越近越準（fresh consensus + whisper 出爐 + management commentary cues）；earnings-analyst cache key = `last_earnings_date` 不會因下次財報未發布而更新，跑了浪費資源。Option Z 把兩 skill 在時間軸上互補：7 天內 forecaster 主導，7 天外 earnings-analyst 主導。Dashboard morph 讓 user 不用記 trigger，UI 自動出最適 button。

### Architecture note
`SCRIPT_PROTOCOLS` 是新類別的 protocol —— 不走 Claude conversation。長期可把其他純腳本工作（e.g. `daily_update.sh` step、`build_event_index.py`）也搬進來，省 LLM cost。目前先收 earnings_preview 一個。

---

## [2.14.0] — 2026-05-06
### Added — reference/financial-services Phase A 移植（IC-memo + thesis registry + skills linter + hyperlink discipline）

**動機**：對照 Anthropic 官方 `reference/financial-services/` 找出 4 個高 ROI 低成本的強化點：機構級 IC-memo 結構、thesis 生命週期串接、skills cross-ref linter、earnings 報告強制 EDGAR/IR clickable hyperlinks。詳細決策見 `~/.claude/plans/refernce-finanical-services-mcp-server-snazzy-canyon.md`。

### Added
- `investment/scripts/register_thesis.py` (104L) — Phase 5.5 wire-up，把 history.json 最後一筆 register 進 trader-memory-core，回填 `thesis_id` + `thesis_registered_at`。Idempotent + non-fatal（trader-memory-core 不在 / dep 缺失時 graceful skip）。State 寫到 `investment/invest_logs/theses/`。
- `scripts/check_skills.py` (160L) — skills/*/SKILL.md frontmatter + cross-ref linter。Lenient mode 預設（rc=0 always），`--strict` 旗標 CI 用。檢查 frontmatter name/description、referenced script files exist、cross-skill references 有效、cache/ dir 一致性。22 skills 全 pass 0 warnings。

### Changed
- `skills/earnings-analyst/SKILL.md` — 新增「Citations & Hyperlinks ⭐⭐⭐ MANDATORY」section（仿 reference equity-research/earnings-analysis）。MD 報告所有財務數字必須掛 markdown clickable link 指向 SEC EDGAR / IR / FMP source page。提供 7 類內容對應 URL 模板。
- `investment/investment_protocol_v5_0.md`：
  - Phase 5 Step 4 OUTPUT 結構強化 §7-§8（V2.14.0 IC-memo pattern）：
    - §7 Red Team 拆 Consensus View / Differentiated View / Counter Thesis / Numbered Kill Conditions（強制 numbered list，禁 free-form）
    - §8 進場計畫拆 Base / Bull / Bear case 三檔
  - 新增 Phase 5 Step 6 = Phase 5.5 thesis registry wire-up（呼叫 `register_thesis.py`，non-fatal）
- `investment/phase5_export_schema.md` — `trades_this_session[]` 加 optional `thesis_id` + `thesis_registered_at` 欄位 + FULL EXAMPLE 範例值
- `investment/scripts/validate_session_export.py` — 接受 V2.14.0 optional thesis 欄位（type-check string-or-null，不強制存在）
- `CLAUDE.md` — 更新 trigger 表（Phase 5.5 + hyperlink 強制）+ Ops Shortcuts 加兩條（register_thesis.py + check_skills.py）

### Why
Reference repo 的 IC-memo / hyperlink discipline / lifecycle tracker 是機構研究室標配；本專案投資 protocol 已成熟但缺這幾片。Phase A 全 doc-level + 一個小 script，無破壞性改動：所有改動 backward-compatible（V5.0 entries 仍 valid，optional 欄位缺失不擋 validator）。

---

## [2.13.13] — 2026-05-06
### Fixed — daily_update.sh Step 6 進度可見化

**動機**：`daily_update.sh` 跑到 `[ 6/6 ] Thematic Screener` 完全靜默 3-8 分鐘，使用者誤以為當機。Root cause：`screen.py --json-only > /dev/null 2>&1` 把 stderr 進度（每 10 tickers 一行 `[HH:MM:SS] ... i/N (elapsed Ns)`）也吞了。

### Changed
- `daily_update.sh` Step 6:
  - 跑前先讀 theme-detector cache 算 unique ticker 數，印 `▶ predicting ~N unique tickers（4h cache 命中數秒；冷跑 3-8 分鐘）` 預期 hint
  - stderr 改用 process substitution stream：`2> >(sed 's/^/         │ /' >&2)`，預測進度即時縮排輸出
  - 完成 / 失敗訊息附 wall-clock elapsed 秒數
  - stdout 仍 `> /dev/null`（不汙染 terminal — 大量 JSON 已寫到 `data/recommendations/`）

### Why
無 progress feedback 的長時操作 = bad UX。screen.py 早已 flush stderr `_log()`，只是被 shell redirect 吃掉。修 shell 層即可，不動 screen.py。

---

## [2.13.12] — 2026-05-05
### Added — Forward P/E + EV/EBITDA TTM（補 PE TTM 不足）

**動機**：HPE PE TTM = -253 因 Q2 2025 一次性 -$1.05B 拖累，但公司實際 ongoing 賺錢。User 詢問「PE / P/B 哪個更有參考價值」— 結論 Forward P/E + EV/EBITDA 比 TTM PE 與 P/B 都更實用。

**Server (dashboard_server.py)**
- `_fetch_pe_ttm` 改回 valuation bundle，每 ticker 3 次 FMP 呼叫：
  - `/stable/ratios-ttm` → `priceToEarningsRatioTTM`
  - `/stable/key-metrics-ttm` → `evToEBITDATTM`
  - `/stable/analyst-estimates?period=annual` → 最近未來年度 `epsAvg`（forward EPS）
- `_heatmap_pe_cache` 改存 dict `{pe_ttm, ev_ebitda, fwd_eps}`
- `_heatmap_refresh_quotes` + `_heatmap_refresh_pe_universe` + `_fetch_theme_extra_quotes` 都attach `pe`、`ev_ebitda`、`forward_pe`（forward_pe 即時用 row.price / fwd_eps 算，價格漂移仍即時）
- Theme heatmap payload 多帶兩欄

**Bridge (bridge.py)**
- `extract_earnings_analyses` + `ingest_momentum_screen` 從 `Dashboard/heatmap.json` 讀 forward_pe + ev_ebitda lookup
- earnings row 新增 `forward_pe` + `ev_ebitda`（earnings cache 已有 ev_ebitda from key-metrics-ttm；forward_pe 借 heatmap）
- momentum row 新增 `forward_pe` + `ev_ebitda`（資料齊但目前 UI 不顯示，留 future 用）

**Frontend**
- `page-sector.js` heatmap tooltip：新增 Fwd P/E + EV/EBITDA 兩 row（同 4 段染色 + tooltip 解釋）。增量 update path 同步加欄
- `page-radar.js` tooltip 同樣新增兩 row
- `page-earnings.js` card meta-pills：PE pill 之後加 Fwd Pill + EV/EBITDA pill，皆染色 + hover 解釋

**色階**
- P/E（TTM 與 Forward 同）：< 0 紅 / < 15 綠 / 15-30 白 / > 30 黃
- EV/EBITDA：< 0 紅 / < 10 綠 / 10-20 白 / > 20 黃

### Why
P/E TTM 易被一次性項目扭曲，P/B 對輕資產（科技、軟體、品牌）幾乎無參考價值。Forward P/E 排除一次性 hit、看分析師共識，與 EV/EBITDA（跨資本結構可比）為實務最常用兩個補充指標。HPE 案例驗證：TTM PE = -253，但 Forward PE 預期應在 17-20 範圍。

FMP `/stable/key-metrics-ttm.evToEBITDATTM` 與 `/stable/analyst-estimates.epsAvg` 都按 ticker 單獨呼叫，所以 PE daemon 從原本 600 calls/24h 變成 1800 calls/24h；ThreadPool(10) 估 ~3 min 完成，仍可接受。

### How to apply
- Restart `dashboard_server.py`，等 stderr `[heatmap-pe] done: N/N`（~3min）
- 重跑 `bridge.py` 讓 earnings / momentum 拿到新欄位
- Hard refresh sector / radar / earnings 各 page

---

## [2.13.11] — 2026-05-05
### Changed — 盤前檢查 chain 從前端搬到 server-side orchestrator（修「sector 從未啟動」race）

**Server (dashboard_server.py)**
- 新 `_premarket_chain_state` + `_premarket_chain_lock`，shape：`{status, started_at, ended_at, phase, elapsed_sec, items: {daily/news/sector: {status, elapsed_sec, reason, error}}, error}`
- 新 `run_premarket_chain()` daemon thread sequencer：
  - Phase 1a daily：`preflight_check` 全 free FRESH → skip；否則 `run_daily_update()` + 輪詢 `_daily_update_state.status` 至 done/error
  - Phase 1b news：`news` key FRESH → skip；否則 `enqueue_protocol("news")` + `_wait_protocol_completion()` 透過 **`_protocol_history`** 偵測完成（durable record，不會錯過瞬間 transition）
  - Phase 2 sector：`sector` key FRESH → skip；否則 enqueue + wait
- 新 `_wait_protocol_completion(name, history_baseline, timeout, on_progress)` helper
- 新 endpoints：
  - `POST /api/run-premarket-chain` → 啟動（409 duplicate_active 含當前 phase）
  - `GET /api/run-premarket-chain/status` → 完整 state

**Frontend (Dashboard/script.js)**
- `runPremarketChain` 簡化為 thin POST + 起 2s poll loop
- 新 `_pollPremarketChain` — 單一 endpoint 取 server aggregated state、render 三 row（daily / news / sector）+ verdict
- 移除 `_pollDailyUpdate` / `_pollProtoForChain` / `_maybeStartPhase2` / `_finalizeChain` / `_chainState`（現由 server 持有 canonical state）
- 新 page-load resume IIFE：若 server 端 chain `running` 或 5min 內 `done/error`，自動 attach poll，user 重整不丟進度

### Why
原 chain 邏輯純前端 polling `/api/run-protocol/status` 2.5s 一次。發現的問題：
1. **Race**：news done 後 server 端 `_protocol_state` 立即被 sector 覆蓋（worker 切下個 job），如果 frontend 沒在那瞬間 catch 到 `name=news status=done` 就永遠不會設 `newsDone=true`、Phase 2 永遠不 fire（今天觀察到「2 次 chain 都失敗，sector 從未啟動」即此症狀）。
2. **Tab close kill**：browser 關 tab → chain 整個失效。Server 端有 daily 跑完、news 跑完，但 sector 永遠 enqueue 不到。

Server-side daemon thread 用 `_protocol_history`（持久 完成記錄）偵測 transition，不依賴瞬時狀態；user 關 tab 也能繼續完成。Frontend 只負責 render，重整即 resume。

### How to apply
- Restart `dashboard_server.py`
- Hard refresh dashboard
- 試：點「開始盤前檢查」→ 應依序看到 daily（skip 或 running→done）→ news（skip 或 running→done）→ sector（skip 或 running→done）→ verdict ✅。中途關 tab 重開應自動恢復進度。

---

## [2.13.10] — 2026-05-05
### Added — 個股 PE TTM 全 Dashboard 顯示（heatmap tooltip / radar / earnings card / momentum row）

**新基建（dashboard_server.py）**
- `_heatmap_pe_cache: {sym: (ts, pe)}` + `_heatmap_pe_lock` + `HEATMAP_PE_TTL_SEC=86400`（24h）
- `_fetch_pe_ttm(ticker, api_key)`：FMP `/stable/ratios-ttm` 單支抓 `priceToEarningsRatioTTM`
- `_heatmap_refresh_pe_universe(max_workers=10)`：ThreadPool 10 平行刷整個 universe，啟動時跑一次 daemon thread
- `_heatmap_refresh_quotes` 每次 batch-quote 後從 PE cache 補 `row["pe"]`
- `_fetch_theme_extra_quotes` 對 radar small/mid cap 也帶 `pe`，缺 PE 的 ticker 在背景 thread pool lazy fetch

**Bridge.py**
- `extract_earnings_analyses` 加 `pe_ttm`（從 earnings cache `ttm_metrics.from_ratios_ttm.priceToEarningsRatioTTM`）
- `ingest_momentum_screen` 載入 `Dashboard/heatmap.json` 建 `pe_lookup` → 每 row 加 `pe`

**Frontend**
- `page-sector.js` heatmap tooltip：加「P/E (TTM)」row（color 分級：<0 紅、<15 綠、>30 黃、其他白）。ticker 增量 update 也帶 pe
- `page-radar.js` `_radarShowTooltip` 同樣加 PE row
- `page-earnings.js` card meta-pills 加 `P/E xx.x` 染色 pill
- `page-momentum.js` table 加 P/E 欄（價格右側）+ sort 支援；header 翻譯 `col_pe` zh「本益比」/ en「P/E」；emptyRow colspan 12 → 13
- `momentum.html` 加 `<th id="th-pe" data-sort="pe">P/E</th>`

### Why
個股 PE 之前完全沒在 Dashboard 任何 list / hover 出現，只在 invest deep-dive 報告 markdown 內。User 平時看 heatmap / earnings / momentum 都看不到 valuation 資訊。

FMP `/stable/batch-quote` 與 `/stable/quote` 已 drop `pe` 欄位（測試確認），改走 `/stable/ratios-ttm`（每 ticker 單獨 fetch、24h TTL cache）。Universe ~600 ticker × 24h refresh × ThreadPool(10) ≈ 60s，FMP usage 可承受。

色階沿用財務分析常識：< 15 便宜 / 15-30 fair / > 30 高估 / < 0 虧損。User 一眼看 hover / card / row 就能判斷估值區間。

### How to apply
- Restart `dashboard_server.py`（PE daemon 啟動 + 補欄 quote refresh）
- 等 1-2 分鐘 PE universe fetch 完（看 stderr `[heatmap-pe] done: N/N`）
- Hard refresh 各 page

---

## [2.13.9] — 2026-05-05
### Added — 盤前檢查 chain 加 freshness skip（外部跑過 daily_update.sh 不重跑）

- `dashboard_server.py::POST /api/run-daily-update`：先跑 `preflight_check()`，若所有 `free=true` 項目皆 `FRESH` → 200 `{skipped: true, reason: "all_free_caches_fresh", items, ages}`。否則維持 202 啟 daily_update.sh。Defensive：preflight_check 自身錯時 fall-through 到實跑（不誤跳）。
- `Dashboard/script.js::runPremarketChain`：
  - 開跑前一次 `/api/preflight` 撈 freshness，記錄 `newsFresh` / `sectorFresh`。
  - Phase 1 daily 收 `{skipped: true}` → row 顯「已新鮮 · 跳過」綠勾，不啟 poll。
  - Phase 1 news：`newsFresh === true` → 不打 `/api/protocol-queue`，row 直接綠勾。
  - Phase 1 兩個都 skip → 立即進 Phase 2，不啟 daily/proto poll loop。
  - Phase 2 sector：`sectorFresh === true` → 不打 protocol-queue，row 直接綠勾、`_finalizeChain()`。
  - 啟動的 timer 只針對 actually-launched job（之前無條件啟兩個 timer）。

### Why
User 已在 shell 跑過 `./daily_update.sh`，回 dashboard 點「開始盤前檢查」應 detect cache 全 fresh 直接跳過。原本無條件 fire daily_update.sh + news Claude + sector Claude，浪費 ~5min + tokens。同邏輯延伸至 news / sector Claude protocol — 今日 digest / sector_intel 若 < 3h 視為 fresh，使用者一個 session 內按多次也只跑第一次。

也順便處理「我沒按開始盤前檢查就自己開始跑了」的副作用：即使誤觸按鈕，全 fresh → chain 秒結束、不消耗資源。

### How to apply
- Restart `dashboard_server.py` + hard refresh index 頁。
- 跑前可先 `./daily_update.sh` 在 shell，回 UI 按「開始盤前檢查」應全部顯「跳過」3 秒內完成。

---

## [2.13.8] — 2026-05-05
### Fixed — thematic-screener 加 socket timeout + 進度 log（修 65min hang）

- `skills/thematic-screener/scripts/screen.py`：
  - `socket.setdefaulttimeout(15)` 模組頂層 — 任何 yfinance / FMP socket op 15s 沒回就 raise，避免 SYN_SENT 無限 hang。
  - 新 `_log(msg)` helper（HH:MM:SS prefix + `flush=True`）讓 daily_update.sh 的 stderr tail 即時看到進度。
  - Predict loop 加每 10 ticker batch 進度 + 個別 > 5s 的單筆 log + TIMEOUT 標籤。
  - Predict + Enrich 階段印總 elapsed。

### Why
今日 daily_update.sh PID 31623（screen.py）卡 65 分鐘。診斷：`lsof` 看到 1 個 socket 在 `SYN_SENT` 對 ec2 host（FMP / yfinance proxy 之一），對方無回應 → Python socket 預設無 timeout → 阻塞 IO 等到 OS 自己 RST。Predict loop 順序跑 249 tickers，1 個 ticker hang 整個 pipeline 死。

加 `socket.setdefaulttimeout(15)` 強制每個 op 上限；progress log 讓 user 下次能立即定位是哪個 ticker / 階段慢。

### How to apply
- 立刻生效（Python module-level 改）。下次 `./daily_update.sh` Step 6 stderr 會出時間戳記日誌。

---

## [2.13.7] — 2026-05-05
### Added — earnings page 專屬 run banner（分離自 news scan-card）

- `Dashboard/earnings.html`：在 hero strip 與 command bar 之間插入 `#ea-run-banner`（紫色 accent，`scan-card-frame` reuse）。含 expand / cancel / dismiss / reload 按鈕 + 即時日誌 pre。
- `Dashboard/style.css`：`scan-card-frame` + `scan-card-log` styles 從 news.html inline 搬到全域，所有 page 共用。
- `Dashboard/page-earnings.js`：
  - `runEarnings` 排隊成功後記 `_eaActiveJobId` + `_eaActiveTicker`、起 2s poll。
  - `pollEarningsRunStatus`：fetch `/api/run-protocol/status`，gate by `name === 'earnings'` AND (`queue_id === _eaActiveJobId` OR `analyze_ticker === _eaActiveTicker`)；只有自家 job 才 render banner。
  - `done` 翻 emerald + 自動 `loadAndRender()` 補資料；`error` 翻 red 顯示錯誤訊息。
  - `resumeEarningsRunBanner`：page load 時若 server 端正跑 earnings 直接接續顯示 banner（重整不會丟進度）。

### Why
User 點「財報分析」時觀察到右下角 protocol pill 顯 `news · 📰 DIGEST`，因為當時 server 端真的在跑 news（earnings 排在 queue 後面）。News page 有 scan-card 顯活 log → 看起來像 news 取代了 earnings。問題不是 pill 標錯，而是 **earnings page 沒有自己的 banner**，user 不知道自己的 job 排在哪、哪時候會跑。新增 earnings-scoped banner 解決：
1. queue 排隊期間 toast 提示位置；
2. 輪到自己跑 → banner 顯示 ticker / elapsed / 即時 log；
3. 完成自動 reload 資料 + 顯示綠色完成框；error 紅色 + 錯誤訊息。

### How to apply
- Hard refresh earnings 頁。
- 排一個 earnings job 觀察 banner 從 hidden → 紫色 running → 綠色 done。

---

## [2.13.6] — 2026-05-04
### Fixed — radar K 線 tail label 格式 + header 文字重複

- `Dashboard/page-radar.js`：tail label / header `updated` 改 `toLocaleTimeString('en-GB', { hour12: false })` → 24h `HH:MM:SS`，避免 zh-TW 加「下午/上午」與 bar label 的 `HH:MM` 風格混搭。
- Header `updated` field 在 tick 模式下從 `tick HH:MM:SS` 改成純 `HH:MM:SS`，避免和 status `15s tick` 的 `tick` 字重複。

### Why
盤中截圖顯示 bar label `10:45` 與 tail label `下午10:58:37` 風格不一致 + status 區出現 `15s tick · tick 下午10:58:52` 重複字。和 5-min bar 沒到 10:50/10:55 無關（那是 FMP 個別 bar commit 慢於 wall-clock，下次 base poll 就會補上）。

---

## [2.13.5] — 2026-05-04
### Added — radar K 線 live tail（FMP `/quote` 每 15s tick 疊在 5-min bars 後）

- `dashboard_server.py`：新 `/api/heatmap/quote/<TICKER>` endpoint + `_fetch_heatmap_quote()`（FMP `/stable/quote`，5s TTL `_heatmap_quote_cache`）。回 `{symbol, price, change_pct, volume, as_of, market_open}`。
- `Dashboard/page-radar.js`：
  - 拆兩個 polling：base bars 60s（`/api/heatmap/intraday/`，原本 15s）+ live tick 15s（新 `/api/heatmap/quote/`）。
  - `_radarTickTail` 維護 ≤25 個 tick（25 × 15s = 6.25min 上限），每 tick `{t: HH:MM:SS, price}`。新 5-min bar 出現（base re-fetch 偵測 `lastBarTime` 變化）→ 清空 tail。
  - `renderRadarKline` 加第二個 dataset：dashed amber line + 1.8px points，從最後一根 bar close 接續延伸。Volume chart 不疊 tail（quote 不帶該 bar 累計 volume）。
  - Header price + change_pct 改用 quote tick 即時更新（比 5-min bar close 即時）。
  - `visibilitychange` 切回 tab 同時觸發 base + tick 各一次。

### Why
v2.13.4 拿掉 visibility gate 但 chart 視覺仍每 5min 才動 — 因 FMP 5-min bars 在 boundary 之間沒新資料。User 質疑「15s API 沒意義」。改用雙 endpoint：粗 bars 走 `/historical-chart/5min`、細 ticks 走 `/quote`，base 不漂移、tail 即時延長，5-min boundary 自動 reset。20 ticks/min × 1 ticker FMP 用量輕。

### How to apply
- Restart `dashboard_server.py`（新 endpoint）+ hard refresh radar 頁。
- 盤中點 ticker tile，5-min bar 後應每 15s 看到黃色虛線往右延一段。每 5min 黃線歸零、新 indigo bar 出現。

---

## [2.13.4] — 2026-05-04
### Fixed — radar K 線 polling 拿掉 visibility gate（不切 tab 也會自更新）

- `Dashboard/page-radar.js:1322`：移除 `setInterval` 內 `document.visibilityState === 'visible'` 條件，只保留 `_radarKlineTicker` 存在性檢查。

### Why
原 gate 是省 FMP/server 用量設計，但 1 ticker × 15s 對 server 無負擔（且 server 端 `HEATMAP_INTRADAY_TTL_SEC_OPEN=15` 已 TTL coalesce）。Browser visibility 在 macOS Stage Manager / 其他 app 全屏覆蓋 / Chrome Memory Saver 下會誤判 `hidden`，user 看著頁面但 polling 卻被 skip → 體感「切 tab 才更新」。

注意：chart bars 是 FMP 5-min OHLCV，視覺形狀仍每 5 分鐘才換新；header `updated HH:MM:SS` 每 15s 跳秒可確認 polling 在跑。

### How to apply
- Hard refresh radar 頁（cache busting 已由 mtime 注入處理）。

---

## [2.13.3] — 2026-05-04
### Fixed — radar 熱力圖補抓非 S&P 500 ticker（修「主題股數 5 卻只看到 1 檔」）

- `dashboard_server.py::_build_theme_heatmap_payload`：第一輪掃 TD theme `representative_stocks` 收集所有不在 `_heatmap_state["tickers"]` 的 ticker，呼叫新 helper `_fetch_theme_extra_quotes(symbols)` 用 FMP `batch-quote` 一次撈齊（單 request、TTL 180s in-process cache）。第二輪 join lookup 用 `_resolve(sym)` 包含 heatmap state + extra fetch 結果。FMP miss / 無 API key → 該 ticker skip（舊行為）。
- 新增 `_theme_extra_quote_cache` + `THEME_EXTRA_QUOTE_TTL_SEC=180`。

### Why
TD theme universe 涵蓋 small/mid cap，heatmap state universe 只 S&P 500（517 tickers）。例：Gold & Precious Metals 5 檔 representative_stocks（NEM/CDE/AU/GFI/HL）只有 NEM 在 S&P 500 → 4 檔被 skip → tile 只剩 NEM 一個。Card body top movers 不受影響因 thematic-screener 用 FMP 直接抓自己的 prediction。

擴 universe 太重；最少改動方案：render 時補抓缺的 ticker quote、cache 3min。實測 17 themes 平均缺 ~25 ticker，1 個 batch-quote call 即解決，不影響整體 latency。

### How to apply
- Restart `dashboard_server.py`。
- Smoke test：`/api/theme-heatmap` 回傳 Gold theme `tickers` length 應 = 5。

---

## [2.13.2] — 2026-05-04
### Fixed — radar 熱力圖 pin 到 recommendations.json 同源 TD cache（修「無覆蓋資料」假空白）

- `dashboard_server.py::_build_theme_heatmap_payload`：先讀 `skills/thematic-screener/data/recommendations/<latest>.json` 的 `theme_detector_meta.file`，找到對應 TD cache 才 join `_heatmap_state`。recommendations 缺檔或 meta 缺欄位 → fallback 最新 TD cache（舊行為）。
- 回傳 payload 增加 `theme_detector_file` + `pin_source`（debug 用，前端不需動）。

### Why
今日 radar 觀察到 17 個 theme 卡片中 4 個顯「無覆蓋資料」，但點開卡片底部 top movers 有資料。根因：thematic-screener 21:06 跑時讀 TD-03 cache 寫 recommendations.json，22:00 跑 `產業掃描` 時 sector Phase 2 又重寫一份 TD-04（`--skip-if-fresh 10800` 觸發），thematic-screener 沒跟著重跑。`/api/theme-heatmap` 一直 glob 抓最新 TD（TD-04）；前端 card body 的 theme.name 來自 recommendations.json（指 TD-03）。兩份 TD 的 sector concentration 系列 theme 名字不同（TD-03 `Financial Sector Concentration` ↔ TD-04 `Financial Services & Banks`），strict name match 失敗 → 4 個 theme heatmap slot 顯空白。

Pin 到同源 TD 後 card body 與熱力圖看的 theme 結構一致；tile 顏色（漲跌幅）仍取自 live `_heatmap_state`，不受影響。

### How to apply
- Restart `dashboard_server.py`。
- 之後若想長期解 TD/screener cache 不同步，要在 sector protocol Phase 2 重寫 TD 後接 thematic-screener re-run（單獨另案）。

---

## [2.13.1] — 2026-05-04
### Fixed — protocol 完成判定加 validator gate（修「綠燈 + 空 dashboard」假成功）

- `dashboard_server.py`：新增 `PROTOCOL_VALIDATORS` map（`sector` → `validate_sector_intel.py`、`news` → `validate_digest_output.py`）。`run_protocol` 跑完且 subprocess `rc=0` 時，再跑對應 validator；validator rc≠0 → 狀態翻 `error` + error 訊息塞前 5 行（含完整輸出 append 到 scan log）。

### Why
今天跑 `產業掃描` 觀察到 banner 顯示綠燈 DONE，但 Dashboard index 市場機制 / 熱門產業 top3 / sector hot/warm/cold / 政治訊號 / 背離觀察全空白。實際 `2026-05-04_sector_intel.json` 缺 top-level `market_regime` / `summary` / `actionable_themes` / `_phase3.political_overlay` / `_phase3.top_catalysts` — Phase 5 emit + validator gate 從未執行。

根因：`_run` 只看 Claude subprocess 的 `rc`，turn 正常結束就標 done，**完全沒驗證產出物**。Schema 規定 Phase 5 末尾 mandatory `validate_sector_intel.py rc=0`，但 server 沒接這條繩。新 gate 直接補上，未來這類 stop-mid-protocol 會以 error 紅色 banner 呈現 + bridge.py 不會被誤觸發。

### How to apply
- Python 3 syntax-only 改動，restart `dashboard_server.py` 即生效。
- 若要新增其他 protocol 的 gate（invest 用 `validate_session_export.py` 等），加進 `PROTOCOL_VALIDATORS` 即可。

---

## [2.13.0] — 2026-05-03
### Added — invest protocol V5.0 subagent 對齊「外部專業分析師 prompt 模板」+ 新 PM 整合層欄位

**動機**：user 看了一份外部分享的 4 套「專業分析師」prompt 模板（技術 / 基本面 / AI 交易決策整合 / 市場消息），對照 V5.0 protocol 找出可優化或缺失的部分。實測 V5.0 結構上已覆蓋 70-75%，剩 25% 是 output JSON 欄位缺漏，不需要新 lane / 不動 score 公式。

**設計原則**（沿用 V2.10 哲學）：純加 narrative / metadata 欄位；final_score 公式不變；schema validator 不擋；舊報告分數可重現。

**Phase A — Technical lane 補三件**（對應外部模板 A）：
- `smart_money_analysis`（label + narrative）— 從 insider Q ratio + 量價背離 + analyst sell-side flow 綜合判
- `pattern_taxonomy`（8 種強制分類）— breakout / consolidation / pullback / false_breakout / topping / downtrend / oversold_bounce 等 + 確認條件 1 句
- 三件套 output：`market_strength` (STRONG/NEUTRAL/WEAK) / `key_levels` ({support, resistance, pivot}) / `high_prob_scenario` (1 句帶價位 + 觸發條件)

**Phase B — Fundamentals lane 補兩件**（對應外部模板 B）：
- `moat_assessment`：WIDE/NARROW/ERODING/NONE + type (brand/IP/switching cost...) + 1 行依據
- `near_term_catalysts[]`：3-5 筆 {date, type, description, impact}
- `bull_thesis_one_line` / `bear_thesis_one_line`：≤ 40 字二元對偶 narrative

**Phase C — News lane 補時間軸**（對應外部模板 D）：
- `immediate_catalyst_5d`：5 天內 binary 事件物件或 null
- `medium_term_shift_20d`：5-20 天 narrative 移轉預期
- `decision_point_days`：下次重新評估的天數
- `cross_asset_spillover[]`：受影響的非個股市場（treasury_10y / DXY / oil / sector_ETF...）+ 傳導機制

**Phase D — Phase 3 PM 整合層補 4 欄位**（對應外部模板 C）：
- `institutional_lens`：1-2 句機構流向整合 narrative（綜合 Sentiment.institutional + Congress trades + FTD + V2.9.0 institutional_holders_qoq_delta）
- `decision_confidence_pct`：int 0-100，與既有 avg_confidence (0-1) 共存
- `scenario_odds`：{bull, base, bear} int 加總 100，三劇本機率
- `action_label`：ATTACK / WAIT / DEFENSIVE，與既有 final_action (BUY/STAGED/HOLD/SELL) **並存補強**，不取代

**Phase F — 同步 surfacing**：
- `bridge.py` 把 7 個新欄位帶進 `recent_analysis[]`
- `Dashboard/page-decisions.js` 加 5 種新 pill：action_label 三色（ATTACK 橙 / WAIT 黃 / DEFENSIVE 灰）/ moat (WIDE 金 / NARROW 銀 / ERODING 紅) / pattern_taxonomy / market_strength / decision_confidence_pct

**Files**:
- 修改：`investment/investment_protocol_v5_0.md`（Phase 2 三 lane prompt 補強約 80 行；Phase 3 PM 整合段補 4 欄位）
- 修改：`investment/phase5_export_schema.md`（V2.13 章節 + REQUIRED table 加 7 個必填欄位）
- 修改：`bridge.py`（meta.get + audits.append 各加 7 行）
- 修改：`Dashboard/page-decisions.js`（buildV48StatusPills 加 5 種 pill）

**Phase E（historical_analog）**：規劃中未做。需要建 historical FRED 月度 vector 表 + cosine similarity；工程量大，等其他 phase 跑一陣子有數據再評估。

### Why
- V5.0 五個 lane 的內部分析其實 ≥90% 已經對齊外部模板，差別只是輸出 schema 沒結構化欄位 — 補欄位 ROI 高
- 跨 V2.10（det_shadow）+ V2.13（lane outputs + PM lens）後，每筆 invest 報告會有 ~20 個結構化 narrative 欄位，給 Dashboard / 回測 / debug 都好用
- `action_label` 與 `final_action` 並存讓「BUY 但 WAIT」這種「等條件」的細微決策可以表達；既有 5 級 final_action 不破壞回測

### Caveats
- LLM 對新 prompt 是否真的填欄位需累積 5-10 個 ticker run 才能評估；Protocol prompt 已加「**必填**，缺資料寫 `INSUFFICIENT_DATA` 而非 null」
- `near_term_catalysts[]` 與 `_phase3.upcoming_events[]` 視角不同：前者限該 ticker 自己的事件，後者跨 sector — 不衝突
- Validator V2.13 新欄位**不**列為 hard-required（informational 階段，累積 30+ run 後再評估提升）
- Dashboard pill 數可能變多（最多 +5）—visual density 升高；如果太擠可後續整併到 expander
- Phase E historical_analog 留待後續

---

## [2.12.0] — 2026-05-03
### Added — radar 頁加 per-theme mini heatmap (intraday) + click→K-line drill + top 5 movers 意義說明

**動機**：user 看 radar 頁覺得「全 theme grid 沒視覺衝擊」，想要每個 theme 自己的 finviz 風 mini heatmap（半導體 theme 內的 TSM/NVDA/AMD 用顏色顯示當日漲跌+成交量）；同時不知道 expanded panel 的 top 5 movers 是怎麼挑出來的。極短期（intraday，今天）vs 短期（thematic-screener 5d horizon）兩個視角分工清楚。

> **設計 pivot**：第一版誤做成全市場 sector heatmap（與 sector.html 重複，517 ticker 巨大 SVG 拖累 radar 頁載入）。User 反饋後改正為 per-theme mini heatmap：每個 theme card 內嵌一個小 D3 treemap，僅該 theme 的 representative_stocks（typically 5-25 ticker / theme）。

**1. Per-theme mini heatmap**（極短期 intraday 視角）
- 每個 theme card 內嵌 110px 高的 D3 mini treemap（不是整頁一個大 heatmap）
- 新後端 `GET /api/theme-heatmap`：讀 `skills/theme-detector/cache/theme_detector_*.json` 拿每 theme 的 `representative_stocks` (~25 ticker)，join `_heatmap_state.tickers`（既有 517-ticker 3min thread）拼出 quote — **零新增 FMP 呼叫**
- 17 themes，16 有 ≥ 3 個 ticker 覆蓋（少數小型 theme 涵蓋率較低）
- Tile 大小依 √(market_cap)（避免 mega-cap 完全壓死小型股）；顏色依當日 % change（紅 ↔ 灰 ↔ 綠 ±3% saturation）
- Hover tooltip：sector / industry / 現價 / 漲跌 / 市值 / 日內區間 / 成交量
- Theme grid 從 6-col 改 4-col 配合 mini heatmap 寬度
- Server-side cache 3min；前端 polling 3min visibility-aware（hidden tab 暫停）

**2. Click → K-line drill**（極短期 5min OHLCV）
- 新 backend endpoint `GET /api/heatmap/intraday/<TICKER>`：FMP `/stable/historical-chart/5min`，cache TTL 15s 開盤 / 5min 收盤
- 點 heatmap tile → K-line panel 在 heatmap 上方滑入（`#radar-kline-panel`）
- Chart.js: 上方 line chart 顯示 close price，下方 bar chart 顯示 volume（顏色：bar 跟前一根 close 比，綠/紅）
- Polling 15s（盤中）/ 5min（盤後），visibility-aware；切 tab 暫停
- 「同時只追蹤 1 個 ticker」設計：新點擊取代舊計時器，避免 quota 累加

**3. Top 5 movers 意義說明**（low-effort fix）
- `renderExpanded()` 加 inline 解釋 banner：「模型對該主題內個股的『未來 5 日預期報酬 × 信心度』由高到低排序，取前 5」
- 雙語（中文 / English）依 `UI.currentLang` 切換
- 對應原始 logic：`skills/thematic-screener/scripts/screen.py:select_top_movers_ranked()` 的 `score = target_central_pct × confidence` desc

**Files**：
- 修改：`dashboard_server.py`（+ `_build_theme_heatmap_payload()` + `_fetch_heatmap_intraday()` + 2 個新 endpoint + import `date`）
- 修改：`Dashboard/radar.html`（+ D3 + Chart.js CDN + theme grid 4-col + K-line panel + tooltip）
- 修改：`Dashboard/page-radar.js`（+ mini heatmap renderer + K-line + explanation banner；theme card markup 加 mini-heatmap-slot）

**FMP 用量**：
- Heatmap quotes：背景 thread 3min/次，多 user 共用（既有，無新增）
- K-line drill：1 watcher × 4 calls/min；server cache 15s 收容多分頁；總 ≤ 5 calls/min ≪ 250 free tier

### Why
- Sector heatmap 補位 finviz-like 「市場全景」視角；theme grid 保留為跨 sector 的「主題切片」視角，兩者互補
- D3 + Chart.js 既有頁面用過（`sector.html` 與 `momentum.html`），CDN 引入零成本
- 後端用既有 `/api/heatmap/data` 基礎建設（517 ticker × 11 sector × 3min thread + heatmap.json 持久化）— 不重造輪子
- Top 5 movers 意義不明只是 UI 缺解釋，1 行 banner 解掉

### Caveats
- Heatmap K-line 用 line chart（非完整 candlestick）— Chart.js 原生不支援 OHLC，要 candlestick 需 `chartjs-chart-financial` 套件；先用 close-line + volume bar，視覺夠用
- 收盤後 K-line panel 仍可開但 bar 不再變動；header 標 `收盤 · 5min 更新`
- mega-cap 視覺壟斷（NVDA / AAPL / MSFT 占大塊）— 與 finviz 同行為，未限制 max-width；user 反饋再加
- 既有 `Dashboard/sector.html` 的 heatmap 邏輯**沒被影響**（純複製到 radar，namespace 隔離）

### Added — thematic-screener v0.3 enrichment（market_cap_tier + earnings/quality/smart-money/analyst guardrails）

**動機**：user 反饋「thematic-screener 推薦本來就很不準」+ 想看到小型股出現在 top 5 時被特別標出。盤點發現原 screener 只用「`5d target_pct × confidence`」排序，無 event 過濾、無 quality gate、無籌碼確認 — 容易推薦進財報前夜或財務岌岌可危的股票。

**新檔**：`skills/thematic-screener/scripts/enrich.py`
- 讀 3 個既有 cache（**零新 API call**）：`_shared/cache/<TICKER>_profile.json` (marketCap) + `earnings-analyst/cache/<TICKER>_*.json` (next_earnings_est) + `_shared/fmp_supp_cache/<TICKER>_*_supp.json` (Altman Z, Piotroski F, insider, institutional)
- 2 個新 FMP HTTP 端點：`/stable/price-target-consensus` (PT upside) + `/stable/grades-historical` (recent upgrades / downgrades 30d)
- 6h TTL per-ticker cache 在 `skills/thematic-screener/cache/enrich/`
- 算每 ticker 的 `enrichment_multiplier`（事件砍半 / 品質紅旗砍 40% / insider 買加 30% / 機構加碼加 20% / PT upside ±30% 範圍 / 評等升加 15%）

**Wire**：`skills/thematic-screener/scripts/screen.py`
- import enrich + 在 prediction 收集後對所有 ok ticker 一次 batch enrich
- `select_top_movers_ranked` 改用 `target_pct × confidence × enrichment_multiplier` 排序
- 每個 mover 輸出加 `enrichment` / `raw_score` / `final_score` 三 field
- framework version v0.2 → v0.3

**Market cap tier 分類**：large_cap (≥$10B) / mid_cap ($2-10B) / small_cap ($300M-$2B) / micro_cap (<$300M) / unknown

**Dashboard radar UI**：`Dashboard/page-radar.js` `renderEnrichmentPills()` 新函式
- 每 mover card 上端加 pill row：market_cap_tier (小型/微型用警告色 ⚡)、earnings within 5d/10d (📅紅/橘)、quality red_flag/premium (⚠/✓)、insider buying/selling (💰/↓)、institutional accumulation (🏦)、analyst PT upside ±%、recent upgrades (↑)、score multiplier (×N.NN)
- `Dashboard/style.css` 加 `.enr-pill` style

### Why (v0.3 enrichment)
- 原 screener 純技術 prediction → 加上 fundamental + event guardrails 後，理論上 false positive 大降（待 backtest 驗證）
- 小型股 user 想多注意 → 用 ⚡ 與警告配色 + market_cap_usd tooltip 直接顯示
- 90% 資料來自既有 cache → 加成本只有 PT + grades (≤2 calls/ticker)，全 17 themes ~80 ticker 也只 ~160 額外 call

### Tests (v0.3 enrichment)
- `python3 skills/thematic-screener/scripts/enrich.py AAPL` → tier=large_cap, MC=$4.1T, earnings 88d 安全, quality_premium (Z=11.6 F=9), PT upside +13.04%, multiplier=1.28
- screen.py smoke run 進行中：1 個 batch enrich 對所有 themes ok-ticker

### Out of scope (留 BACKLOG)
- backtest 比較 v0.2 vs v0.3 推薦在歷史 hit-rate / 5d realized return 上的差異
- 加 Finnhub `/stock/recommendation-trends` 補充 grades-historical（更詳細的買賣評等 distribution）
- 加 short interest / days-to-cover 標籤（目前只用 quality 不看 short crowding）

---

## [2.11.1] — 2026-05-03
### Fixed — proto-pill 殘留前次 invest ticker（"news · CRWV" 假象）

**問題**：user 按「盤前檢查」啟動 news + sector chain，proto-pill 顯示「news · CRWV」（CRWV 是上一次 `分析 CRWV` 的 ticker）。news DIGEST 本身沒有 ticker 概念。

**根因**（`dashboard_server.py:692-693`）：
```python
with _protocol_lock:
    if name == "invest":
        _protocol_state["analyze_ticker"] = params.get("ticker")
```
`analyze_ticker` 只在 invest 啟動時被設值，其他 protocol（news / sector / triage / flash_text / review）啟動時不動到。invest CRWV 跑完後 `analyze_ticker="CRWV"` 殘留；下一個 news 啟動 → `_protocol_state.name = "news"` 但 `analyze_ticker` 還是 "CRWV"。`get_queue_state()` 不論 name 都回傳 `analyze_ticker` → proto-pill 拼成「news · CRWV」。

**Fix**：dispatch 時無條件覆寫，ticker-less protocol 寫 None：
```python
_protocol_state["analyze_ticker"] = params.get("ticker")  # None for DIGEST/sector
```
- earnings/flash 等也有 ticker 的 protocol 反而修對了（之前是看起來對是因為 invest 殘留剛好相同 ticker）
- invest dedup 不影響（`_currently_analyzing_ticker` 已用 `name == "invest"` gate）

### Action required
restart `dashboard_server.py` 才會生效（執行中 process 還持有舊代碼）。

---

## [2.11.0] — 2026-05-03
### Added — earnings real next-date + EV ratios + theme-detector mapping + sector-analyst FMP overlay

**動機**：本 session 涵蓋 4 個獨立小強化：(1) earnings dashboard 「下次財報」一直是 +91d 猜測（用 🔮 icon 暗示）— 改用 FMP 實際日期；(2) FMP_強化分析.md 留下的 `evToEBITTTM` 坑實測 FMP 沒此欄位 — 改補 `evToFreeCashFlowTTM` + `evToSalesTTM`；(3) 全 skill × FMP catalog 盤點顯示 theme-detector 仍 finviz 為主 + sector-analyst 完全沒 FMP overlay；(4) 為 theme-detector FMP-primary 遷移建好 industry name mapping table。

### Added
- **`skills/earnings-analyst/scripts/fetch.py`** — 取代 +91d 猜測：scan 現有 `earn_surprises`（FMP /stable/earnings limit=8）找未來日期，補 `next_earnings_source`（`fmp_confirmed` / `estimated_91d`）+ `next_earnings_eps_estimate` + `next_earnings_revenue_estimate`。fallback 保留向後相容。
- **`skills/earnings-analyst/scripts/fetch.py`** `slim_ttm_keymetrics` 加 `evToFreeCashFlowTTM` + `evToSalesTTM`（FMP 沒 evToEBITTTM，走實際存在的 EV ratio 補 Burry/value 視角）。`render.py` Valuation block 同步顯示。
- **`bridge.py`** L1592 區塊 pass-through 新增 4 個 next_earnings_* 欄位到 `Dashboard/data.json`。
- **`Dashboard/page-earnings.js`** L435-453 — 依 `next_earnings_source` 切 icon：`fmp_confirmed` → 📅「下次財報」+ EPS/Rev tooltip；fallback → 🔮「下次預估」（無 source 欄位的舊 cache 自動 fallback）。
- **`skills/theme-detector/scripts/dry_run_compare.py`** — Finviz vs FMP industry 對比 dry-run（read-only，no writes to themes.yaml/cache）。輸出 `reports/theme_dry_run_<DATE>.md`。
- **`skills/theme-detector/scripts/industry_name_mapping.yaml`** — 47 rename + 8 collapse + 16 finviz_only + 6 fmp_only，把原 51% string-overlap 提升到 100% finviz coverage（migration 預備工，未啟用）。
- **`skills/sector-analyst/scripts/analyze_sector_rotation.py`** — `fetch_fmp_sector_overlay()` 新函式：FMP `sector-pe-snapshot` + `sector-performance-snapshot` 兩端點，11 sector PE + 1d / rolling 5d perf，跨 exchange 平均 + `Financial Services` → `Financial` rename 對齊 TraderMonty taxonomy。`format_json` 加 `fmp_overlay` field；human format 末尾加 Valuation+Perf 表格。No FMP key 時 graceful no-op，舊 schema 不變。

### Why
1. **next_earnings real date**：TEAM 原顯示 2026-07-30 (猜)，實際 2026-08-06。NVDA 原顯示 2026-04-26 (已過期 +91d) ，實際 2026-05-20。6 個 cached tickers 全部 `fmp_confirmed`。
2. **EV ratios**：原 `slim_ttm_keymetrics` 只有 `evToEBITDATTM` — Burry rubric 需要更多估值維度。FMP probe 證實 `evToEBITTTM` 為 ghost field（不存在），改走 `evToFreeCashFlowTTM` + `evToSalesTTM`（real fields，AAPL 驗證 OK）。
3. **theme-detector dry-run**：finviz 資料品質 ~50% 損壞（HARD_CAPS 註解已認證），FMP 完全乾淨。但 finviz 144 vs FMP 128 industries name overlap 只 51%。Mapping YAML 為日後切 primary 準備但**未啟用**（`theme_detector.py:479` 仍 import finviz_performance_client）。
4. **sector-analyst overlay**：原 skill 只用 TraderMonty CSV 的 uptrend ratio（breadth metric）— 缺估值與價格動能視角。FMP overlay 補上 PE + 5d perf，TraderMonty 仍 canonical。Investment / sector protocol 可參考新欄位但尚未強制使用。

### Tests
- `python3 skills/earnings-analyst/scripts/fetch.py TEAM --force` → cache JSON 含 `next_earnings_source: fmp_confirmed`, `next_earnings_est: 2026-08-06`, EPS est 1.14
- 6 cached tickers (TEAM/NVDA/MU/MSFT/GOOGL/AAPL) `--force` 重抓 + `python3 bridge.py` → data.json 全 `fmp_confirmed`
- AAPL re-fetch → `evToFreeCashFlowTTM=31.50, evToSalesTTM=9.01`
- `python3 skills/theme-detector/scripts/dry_run_compare.py --out reports/theme_dry_run_2026-05-03.md` → 73 matched / 71 finviz-only / 55 fmp-only
- `python3 skills/sector-analyst/scripts/analyze_sector_rotation.py --json` → `fmp_overlay` 含 11 sector PE + 11 sector perf；human format 末尾 Valuation+Perf 表格出現

### Out of scope (留 BACKLOG)
- theme-detector 切 FMP-primary（mapping YAML 已備但 `theme_detector.py:479` 未動）
- sector-analyst overlay 整合進 sector_protocol Phase 4 估值面決策（目前只是輸出，未進 rubric）
- 71 finviz-only 中部分（如 Internet Retail）值得二次審視 — 可能 FMP 用其他名稱包進去

---

## [2.10.0] — 2026-05-03
### Added — invest protocol det-shadow + polarization 標籤（保留 LLM，加 quant sanity check）

**動機**：CRWV 2026-05-03 同日重跑兩次，final_score 從 −0.055（CANCEL）跳到 −0.481（HOLD），verdict 跨 band 翻面。診斷發現主因是 5 lane 的獨立 LLM subagent 在 −2/−3 邊界各自抽到不同邊（Fund/Sent 兩 lane 同向 ±1 notch ≈ ±0.40 final_score）。架構上正常 noise 但 user 體感很怪。

**設計**：保留 LLM 判斷主分數（不犧牲 nuance），加 deterministic shadow 與 polarization label 做平行 sanity check：

**1. Polarization detection**（純 LLM lane scores 算，無新依賴）
- `signal_polarization`: `BIPOLAR` (range ≥ 4 + 任一 lane ≥ +2 + 任一 ≤ −2) / `MIXED` (range ≥ 3 一正一負) / `ALIGNED`
- 跨 run 一致：CRWV 兩 run 都判 BIPOLAR，user 一眼就知道「這股本來就會晃」

**2. Deterministic Valuation shadow**（從 weighted_fair_value vs price 算）
- `valuation_score_det`：閾值表 ≥+30%→+1 / ≥+10%→+0.5 / ≥−5%→0 / ≥−20%→−0.5 / <−20%→−1
- `val_agreement`：AGREE (|Δ|≤0.25) / DRIFT (≤0.75) / DISAGREE (>0.75)

**3. Deterministic Red Team shadow**（6 條 quant kill triggers）
- 觸發條件：`Altman Z<1.8 / D/E>5 / FCF<0 / insider<0.3 / short>20% / FRED sector_avoid`
- count ≥ 5 → STRONG_COUNTER；≥ 3 → MODERATE_COUNTER；否則 NO_VIABLE_COUNTER
- `red_team_agreement`：LLM verdict vs det 對照

**CRWV 案例驗證**（apply 在歷史兩 run 上）：

| | Run 1 (CANCEL, −0.055) | Run 2 (HOLD, −0.481) |
|---|---|---|
| signal_polarization | **BIPOLAR** | **BIPOLAR**（兩 run 一致 ✓） |
| valuation_score_det | 0 | 0 |
| val_agreement | DRIFT | **DISAGREE** |
| red_team_verdict_det | STRONG_COUNTER | STRONG_COUNTER |
| red_team_agreement | AGREE | **DISAGREE** ⚠ |

→ Run 2 雙 DISAGREE flag 揭露「LLM 比 quant 寬容了」，這是 final_score 之外的關鍵資訊維度。

**Files**:
- 新增 `investment/scripts/apply_det_shadow.py`（pure-python post-processor，無新 API call）
- 新增 schema 欄位（trades_this_session[]）：`lane_scores` / `det_inputs` / `det_shadow`
- 修改 `investment/phase5_export_schema.md`（V2.10 章節）/ `investment/investment_protocol_v5_0.md`（Phase 5 加 Step 1.5）
- `bridge.py` 把 `det_shadow` 帶進 `recent_analysis[]`
- `Dashboard/page-decisions.js` 加 BIPOLAR / MIXED / RT DISAGREE / VAL DISAGREE 四個 pill（hover tip 解釋）
- 歷史 CRWV 2026-05-03 兩 run 已 backfill `lane_scores` + `det_inputs` + `det_shadow`（從 bias_notes 與 fmp_supp_cache 重建）

### Why
final_score noise（±0.3-0.5）在 BIPOLAR 兩極股本來就是架構天然上限（5 個獨立 LLM subagent），改全 deterministic 會犧牲 LLM 看軟訊號的能力（如 "Microsoft $10B 合約" 這種 quant rule 看不到的事）。V2.10 走中間路線：LLM 主分數不變，加 sidecar 顯示「LLM 跟 quant 是否一致」+「股票本身是否兩極化」。痛點被打到（CRWV 重跑 verdict 翻面看起來矛盾 → 加 BIPOLAR badge 後 user 預期管理對了），同時保留 LLM 彈性。

### Caveats
- `lane_scores` / `det_inputs` 必須由 LLM 在 Phase 5 Step 1 寫入（protocol 已加註）；否則 polarization/red_team_det 各自 graceful skip，不影響其他欄位
- val_det 只看 FV vs price ratio（純算數），不考慮 distress / FCF quality 等軟訊號 — 這是設計（要的就是 quant baseline）；若 LLM 加分 distress 因素到 −1，shadow 顯示 DISAGREE 是預期行為，user 知道 LLM 多扣分了
- Threshold（kill trigger 數 ≥5 / ≥3、val 分數閾值）目前是 Day-1 拍腦袋值；累積 30+ ticker 數據後可校準

---

## [2.9.1] — 2026-05-03
### Added — earnings card 4 score bar tooltip + fiscal-aware 日期 + next earnings

**問題**：User NVDA card 截圖回報三點 (V2.8.x 殘留)：
1. Quality / Growth / Value / Analyst 四 bar 看不出含義 + 視覺上「都滿的」
2. `2026-01-25` 看不出意思（應為 Q4 FY26）
3. 沒有下次財報日 + 哪季

**Fix**：
1. **Bar tooltip**：每 bar 加 `data-signal-tip="ed_score_<key>"`，hover 出 sector-style rich card 解釋該分項組成（Quality 4 子項、Growth 4 子項、Value 4 子項、Analyst 4 子項）+ how-to-read tip。`Dashboard/utils.js` 加 4 個 SIGNAL_TIPS entries (zh+en)
2. **Bar pct 顯示**：`25/30 → 25/30 · 83%`，VALUE 16/25 立刻看出 64% 比 GROWTH 100% 短
3. **Last earnings pill 加 fiscal**：`📅 2026-01-25` → `📅 Q4 FY26 · 2026-01-25`（無 fiscal_label fallback to date only）
4. **Next earnings pill 新增**：`🔮 Q1 FY27 · 2026-04-26`，fiscal 自動 +1 quarter
5. `bridge.py:extract_earnings_analyses` 讀 sibling `<TICKER>_<DATE>.infographic.json` 取 `fiscal_label` 注入 listing payload；無 infographic 則 None

### Files changed
- `bridge.py` — `extract_earnings_analyses` 加 lazy load `fiscal_label` from infographic
- `Dashboard/utils.js` — 加 4 SIGNAL_TIPS (`ed_score_quality / growth / value / analyst`)
- `Dashboard/page-earnings.js` — `renderComponentBars` 加 `data-signal-tip` + pct%；`renderCard` 用 fiscal_label 包 last earnings pill + 新增 next earnings pill
- `Dashboard/earnings.html` — body 加 `<div id="signal-tip-tooltip">`、新 `.ea-pill-date-next` (purple dashed) + `.ea-comp` hover tint

### 驗證
- 5/6 tickers 有 infographic → fiscal_label 正確顯示（AAPL FY26 Q2 / MSFT FY26 Q3 / GOOGL FY26 Q1 / TEAM FY26 Q3 / MU FY26 Q2）
- NVDA 無 infographic → 退化為 `📅 2026-01-25` + `🔮 2026-04-26`（無 fiscal prefix）
- Hover 任 bar → tooltip 出現解釋

---

## [2.9.0] — 2026-05-03
### Added — sector protocol 三個新 FMP 訊號（不改 rubric，純 Phase 4b divergence 提示）

**動機**：對照 V2.8.2 整理的 FMP MCP 完整清單，sector protocol 還有三個高價值訊號沒納入：(1) `form13f_top10_delta` 一直是 null；(2) sector 層級沒有 forward valuation 訊號；(3) 動能訊號只有 3M 一個視窗。

**1. Institutional Q-on-Q（取代 form13F）**：`sector/scripts/fetch_smart_money.py` 加 `/stable/institutional-ownership/symbol-positions-summary` 對 SECTOR_UNIVERSE 全 ticker aggregate
- 新欄位：`institutional_holders_qoq_delta`（13F filer 數 QoQ 增減 sum）+ `institutional_ownership_pct_delta`（機構持股 % QoQ 變化 median）+ `institutional_sample_size`
- 頂層 metadata `institutional_quarter`（如 `"2025Q4"`）
- helper `latest_complete_13f_quarter()` 加進 `sector/lib/date_utils.py`（13F 申報截止 45 天 lag rule）
- soft-fail per ticker；`--skip-institutional` 旗標可省 ~131 calls
- `form13f_top10_delta` 欄位保留向後相容，永遠 null（已被取代）

**2. Forward valuation via PT consensus**：`sector/scripts/fetch_earnings_pulse.py` 加 `/stable/price-target-consensus` 對 SECTOR_TOP_5 + 單一 batch 拉 55 ticker 當前價（`/stable/batch-quote-short`）
- 新欄位：`analyst_pt_upside_median_pct`（中位 PT 上行空間，0.05 = 5% upside）+ `pt_sample_size`
- soft-fail；CLI flag `--skip-grades` → `--skip-analyst`（同時跳過 grades + PT），舊 flag alias 向後相容

**3. 多週期 RS（零新增 API call）**：`sector/scripts/fetch_sector_valuation.py` 重用既有 3M ETF chart 計算 5d / 20d
- 新欄位：`rs_vs_spy_5d` / `rs_vs_spy_20d`（既有 `rs_vs_spy_3m` 對 V2.8.x cache **byte-identical**）
- 用法：3M 強但 5d/20d 同向轉弱 = 動能耗盡訊號

**Phase 4b 新規則**（不寫進 score 公式，只給 LLM divergence challenge 用）：
- 規則 5 擴充：HOT + 13F holders QoQ < 0 AND ownership % QoQ < 0 AND sample_size >= 3 → smart_money_divergence
- 規則 6 新增：HOT + PT upside median < 3% AND pt_sample_size >= 3 → pt_target_exhausted
- 規則 7 新增：HOT + 3M RS > +5% AND 5d/20d 皆 < 0 → momentum_exhaustion

**Files changed**：
- 新增 fields 不動 schema 結構：`sector/scripts/fetch_smart_money.py` / `fetch_earnings_pulse.py` / `fetch_sector_valuation.py` / `sector/lib/date_utils.py`
- Doc 同步：`sector/schema.md`（V2.9.0 changelog block + Validator Coverage 註記）/ `sector/scripts/README.md`（endpoint 表 + skip flag）/ `sector/BACKLOG.md`（form13F 段更新 + acquisition-ownership 已評估不採用 rationale）/ `sector/phase_1-2-3.md`（Step 2/3b/3c 加新訊號用法）/ `sector/phase_4-5.md`（Phase 4b 規則 5 擴充 + 規則 6/7 新增）

### Why
sector protocol 的 verdict 公式不動（向後相容；舊報告分數可重現），新訊號只進入 Phase 4b 強制 divergence challenge — 三個都有量化 threshold，避免 LLM 自由發揮。多週期 RS 零新增 API call 是 hidden bonus；institutional Q-on-Q 是真正補上 V1.4 規劃時欠下的 form13F 坑（用 free tier 可用的端點實現）。

### Bonus — `acquisition-of-beneficial-ownership` 已評估、不採用
原本 plan 要用此 endpoint 補 13D/13G 訊號，curl 實測 mega-cap 數據過時（AAPL/NVDA/META 等最近 180 天皆 0 filing），signal 對 sector aggregate 太稀疏。改走 institutional-ownership/symbol-positions-summary（涵蓋全部 13F holder 的 Q-on-Q 變動）。rationale 留在 `sector/BACKLOG.md`。

---

## [2.8.2] — 2026-05-03
### Added — FMP MCP 中文參考文件
- 新增 `reference/fmpstab/FMP_MCP_TOOLS_中文參考.md`：透過 Claude Code 載入的 27 個 `mcp__fmp__*` tool schema 整理成中文索引（~230 endpoints），每個 endpoint 帶簡短中文說明 + 必要參數 + 用途
- 含 HTTP path ↔ MCP tool 對照表，提醒「腳本走 HTTP / LLM 對話走 MCP」的分工
- 來源：`claude mcp list` ✓ Connected `https://financialmodelingprep.com/mcp?apikey=...`

### Why
之前的 `FMP_API_中文參考.md` 是 HTTP REST 視角；MCP 連線後 LLM 在對話中可以直接呼叫工具，需要一份「MCP tool/endpoint 名稱」對照才好查。這份文件補位，未來 endpoint 增減重跑 ToolSearch 即可重生。

---

## [2.8.1] — 2026-05-03
### Changed — earnings-detail chart 整合：取消 ? icon、disable Chart.js 原生 tooltip、加 always-visible inline 數據

**問題**：V2.7.18 用 `?` icon 分離兩種 tooltip，user 拒絕（不想 ? 干擾視覺）。雙 tooltip（card-level signal-tip + bar-level Chart.js dark popover）仍會疊。

**新方案**：單一 tooltip + 永遠可見的 inline 數據。
- HTML：移除 `?` icon button，還原 `data-signal-tip` 到整個 chart card；canvas 下方加 `<div class="ed-chart-summary">`
- JS：6 個 chart `plugins.tooltip.enabled = false`（Chart.js 原生 dark popover 全關），渲染後 populate inline summary：
  - Revenue/NI: `Revenue $111B · Net Income $30B · YoY Rev +X%`
  - EPS: `Latest $2.02 · 5Q $1.57–$2.85 · YoY +22%`
  - OCF/FCF: `OCF $28.7B · FCF $26.7B · FCF margin 24.0%`
  - GM/OM: `GM 49.3% · OM 32.3% · GM Δ -0.5pp`
  - Segment: `iPhone +21.7% · Services +16.3% · Mac +5.7% · ...`
  - Geo: `USA +85% · TW +25% · CN -8% · APAC +45% · ...`
  - 顏色：positive 綠 / negative 紅 / neutral 主色
- CSS：刪 `.ed-chart-help` / `.ed-chart-title-row`（unused），新 `.ed-chart-summary` + `.ed-chart-summary-item` + `.ed-chart-summary-label`，dashed top-border 與 chart 視覺分離

### 行為
- Hover chart card → ONE signal-tip card 解說（bar hover 不再跳第二 tooltip）
- 精確數值看 canvas 下方 inline 一行（永遠可見、wrap 自適應）

### Files changed
- `Dashboard/earnings-detail.html` — 6 card 移除 `?` button + 加 `<div class="ed-chart-summary">`
- `Dashboard/page-earnings-detail.js` — 全 chart `tooltip: { enabled: false }`；新 `_setChartSummary / _summaryItem` helper；6 chart 各加 summary 計算 ~80 行
- `Dashboard/style.css` — 刪 ~30 行 unused styles + 新 `.ed-chart-summary` block

### Why
解決連兩版（V2.7.16 雙 tooltip 撞 + V2.7.18 ? icon 不滿意）的反饋：要單一 tooltip + 數字一目了然。

---

## [2.8.0] — 2026-05-03
### Changed — sector protocol fetch 層 DRY refactor + 註解外移

**動機**：sector/scripts 4 份 fetch 腳本 `_fmp_get` 邏輯重複 4 次（4 × ~20 行），docstring 把「為何 hard-fail / form13F 緩議 / analyst_revision 緩議」這類背景資訊寫在 code 裡，每次改腳本都要繞過長 header；同時 `reference/fmpstab/FMP_API_中文參考.md` 還有 free-tier 可用、但沒納入的 endpoint。

**Refactor**：
- 新增 `sector/lib/{__init__.py, fmp_client.py, date_utils.py}`，集中：`fmp_get()`（含 429 退避 + 4xx 不重試）、`cache_path()`、`SECTOR_UNIVERSE/TICKER_TO_SECTOR/SECTOR_TOP_5` re-export、`lookback_window()/cutoff_date()`
- 4 份 fetch 腳本（`fetch_sector_valuation.py` / `fetch_earnings_pulse.py` / `fetch_smart_money.py` / `fetch_sector_news.py`）移除自家 `_fmp_get`、改 import lib；docstring 縮為 2–3 行；行為對前 cache 檔 byte-identical（`sector_valuation_2026-05-01.json` 與 `sector_earnings_pulse_2026-05-02.json --skip-grades` diff = 空）
- `validate_sector_intel.py` header 從 22 行縮為 5 行；驗證項目搬到 `sector/schema.md` 新增的「Validator Coverage」section

**註解外移**：
- 新增 `sector/BACKLOG.md`（form13f / analyst_revision deferred / MCP-vs-HTTP 路徑）
- 新增 `sector/scripts/README.md`（hardness 表、retry 策略、執行範例）

### Added — Phase 3 補位 endpoints（並行、不取代 WebSearch）
- 新增 `sector/scripts/fetch_general_news.py`（FMP `/stable/news/general-latest`，limit=20）— **soft-fail**（失敗寫 `{available: false}`，protocol 不中斷）
- `phase_1-2-3.md` 新增 Step 3e（fetch_general_news）；Step 5 WebSearch budget 依 `general_news.available` 動態調整：true → ≤1 query（純突發）；false → ≤2 query（回退原 V1.4 規則）— **WebSearch fallback 永遠保留**
- `fetch_earnings_pulse.py` 加 `fetch_grades_consensus_for_sectors()`：對 `SECTOR_TOP_5` 各 ticker 呼叫 `/stable/grades-consensus` 加總 `(strongBuy+buy)−(sell+strongSell)` 填 `analyst_revision_net`（之前永遠為 null）— soft-fail per ticker，整體失敗欄位回 null；新加 `--skip-grades` 旗標可省 55 calls

### Fixed — `fmp_client.fmp_get` 4xx 不重試
4xx（除 429）為永久 client error，原 retry logic 浪費 3 × 0.5s。新增 `400 ≤ status_code < 500` early-break，避免 endpoint 不存在或 ticker 無資料時的無謂等待。

### Files changed
- 新增：`sector/lib/__init__.py`、`sector/lib/fmp_client.py`、`sector/lib/date_utils.py`、`sector/BACKLOG.md`、`sector/scripts/README.md`、`sector/scripts/fetch_general_news.py`
- 修改：`sector/scripts/fetch_sector_valuation.py`、`sector/scripts/fetch_earnings_pulse.py`、`sector/scripts/fetch_smart_money.py`、`sector/scripts/fetch_sector_news.py`、`sector/scripts/validate_sector_intel.py`、`sector/phase_1-2-3.md`、`sector/schema.md`
- 不動：`sector/sector_protocol_main.md`（rubric 維持原樣）、`render_sector_report.py`、`step6_overlay.py`、Dashboard、bridge.py、daily_update.sh

### Why
WebSearch 在 Phase 3 narrative 是刻意保留的 fallback，不該被取代只該被「補位」。Refactor 行為對舊 cache byte-identical 確保 V1.4 報告輸出不變；新增 grades-consensus / general-news 都是 soft-fail，FMP 故障時自動回退到既有 WebSearch 預算。

---

## [2.7.18] — 2026-05-03
### Fixed — 快速啟動引擎 widget 沒區分 protocol type 導致 user 誤把財報當成投資分析

**問題**：index.html 「快速啟動引擎」widget 的「最近」行顯示 `✓MU`，user 以為 MU 是投資深度分析（決策中心應顯示），但其實是 earnings 跑的（5/3 10:36 完成）→ 「決策中心」沒有 5/3 MU = 對的。

**Fix** (`Dashboard/analyze-queue.js`)：
- 新 `_protoMeta(name)` mapping：invest=🔬分析 / earnings=📊財報 / news=📰新聞 / sector=🌐產業 / llm_review=🤖檢討 / flash=⚡ / triage=🔍
- Active 行：`🔬 QCOM` (含 icon)
- Recent 行：`✓📊MU · ✓🔬AAPL` 每筆前綴 protocol icon + status icon
- Pending queue pill：同樣加 icon
- title 屬性帶 `分析 QCOM` / `財報 MU` 等中文 label，hover 確認

### Why
User 截圖顯示 widget 的「分析中 QCOM」+「最近 ✓MU」，沒辦法區分 QCOM 是 invest deep-dive、MU 是 earnings analysis。視覺上看起來像「同類任務」造成決策中心查無 MU 的混淆。

---

## [2.7.17] — 2026-05-03
### Added — 盤前檢查 chain：daily_update + news 平行 → sector → AI 裁決自動刷新

**問題**：原盤前檢查只跑 4 個 free shell + news/sector 序列，**沒呼叫 daily_update.sh**，user 須手動跑兩次。daily_update 內含 FRED / bridge / thematic-screener 等 preflight 完全不管的步驟。

**設計**（user 確認）：
- **Phase 1 平行**：`bash daily_update.sh` (~10 min) + `news` Claude protocol (~12 min) — 兩者無 file 相依，平行省 ~10 min
- **Phase 2 序列**：`sector` Claude protocol（讀 news digest + breadth/ftd/market_top cache）
- **Phase 3 自動**：bridge.py 在 protocol worker 內建跑 → data.json 更新 → index.html 4 pills 自動 reload（無新 Claude call）

### Files changed
- `daily_update.sh` — 標準化所有 step 標籤為 `[N/6]`（原本 mix `[N/5]` + `[5/6]`），給 backend stdout parser 抓進度
- `dashboard_server.py` — 新 `_daily_update_state` dict + `run_daily_update()` runner（Popen + line-by-line stdout 解析 `[N/6]` 更新 `current_step`）+ `POST /api/run-daily-update` + `GET /api/run-daily-update/status` 兩 endpoint
- `Dashboard/index.html` — `#preflight-modal` 內加 `#preflight-chain` 三 phase 區塊（daily_update / news / sector / AI 裁決 4 row 含 progress bar）+ 新主按鈕「開始盤前檢查」；既有 free/all-stale 按鈕降為次要（向下相容）
- `Dashboard/script.js` — 新 `runPremarketChain()` orchestrator + `_pollDailyUpdate()` + `_pollProtoForChain()` + `_maybeStartPhase2()` + `_finalizeChain()` + DOM helpers `_setRow / _fmtSec`
- `Dashboard/style.css` — 新 `.preflight-phase` / `.preflight-row` / `.preflight-row-bar` 全套樣式
- `Dashboard/i18n.js` — 加 `preflight.{run_chain, phase1_title, phase1_hint, phase2_title, phase2_hint, phase3_title, phase3_hint, waiting_phase1, waiting_phase2, ai_verdict}` 10 keys × zh/en

### 驗證
- `curl -X POST /api/run-daily-update` → 202 + job_id
- `curl /api/run-daily-update/status` → status=running, current_step=3/6, elapsed_sec=13s（parser 正確抓 `[ 3/6 ]` echo）
- 不含 cancel button — user 確認任意中斷 = 關 modal 即可（背景 subprocess + Claude queue 繼續）
- Progress UI = bar + N/6（user 確認）；無 step 名稱

### 不做
- 不改 daily_update.sh 內部執行邏輯
- 不引入並行 Claude（既有 _analyze_worker 仍 single-threaded FIFO；news + sector 仍序列，但 daily_update.sh 是 shell 平行於 Claude queue）
- 不為 earnings/momentum/radar 加 phase
- 不刪 /api/preflight/run-free（向下相容）

---

## [2.7.16] — 2026-05-03
### Added — chart i18n + sector-style tooltip + 全域 protocol status pill

**改動 1：chart 翻譯 + sector-style tooltip**
- 中文模式 chart legend：Revenue→營收、Net Income→淨利、OCF/FCF/GM/OM 縮寫保留 + 中文長標題
- 每個 chart card 加 `data-signal-tip="ed_chart_<x>"`，hover 出 sector page 同款 rich tooltip：title + 多段 desc（解釋 OCF / FCF / GM / OM / Net Income / EPS 是什麼、看點、watch threshold）+ hint
- 6 個 tip 條目：`ed_chart_revenue_ni` / `_eps` / `_cashflow` / `_margins` / `_segment_growth` / `_geo_growth`，全部 zh + en
- earnings-detail.html 加 `<div id="signal-tip-tooltip">` 啟用 utils.js 既有 tooltip engine

**改動 2：全域 protocol 狀態 pill**

**問題**：user 在 earnings page 觸發財報分析任務（POST /api/protocol-queue），看到 toast 確認入排，但切到其他頁面（index / calendar）後**任何狀態都消失**，不知道任務還在不在跑。其他頁面也沒地方顯示 active job。

**Fix**：utils.js 加 `pollProtoPill` 每 5 秒 GET `/api/protocol-queue`，根據 `active` + `queue.length` 動態 render 一個 fixed bottom-right pill，跨頁持續顯示：
- Idle → 隱藏
- Running → indigo pulse 邊框 + 自旋 🔄 + `<protocol> · <ticker> · 2m 12s` + queue count
- Click chevron → expand 詳情：active job + queue list (max 5 rows)
- 利用 `utils.js` 已存在每頁載入 → 自動跨頁可見，無需每頁手動加

### Files changed
- `Dashboard/utils.js` — 加 6 個 SIGNAL_TIPS chart entries + `ensureProtoPill / pollProtoPill / fmtElapsed` 三個 helper + 5s 輪詢
- `Dashboard/earnings-detail.html` — 6 chart card 加 `data-signal-tip` attribute + body 加 `#signal-tip-tooltip` div
- `Dashboard/page-earnings-detail.js` — chart legend labels 改用 `i18n.legend_*` 變數
- `Dashboard/i18n.js` — 加 8 個 `legend_*` key（zh/en）+ 改 `chart_eps/cashflow` 中文標題用全名
- `Dashboard/style.css` — 加 `.proto-status-pill` 全套樣式（fixed bottom-right、indigo pulse、spin icon、expandable detail panel）

### Why
chart 上線後 user 反映：(a) 中文模式 OCF/FCF/GM/OM 應翻譯、(b) 不知道每個 chart 在看什麼、(c) earnings 觸發任務後切頁失蹤。三點一次解。

---

## [2.7.15] — 2026-05-03
### Added — earnings-detail page 加 6 chart 趨勢圖區塊（Chart.js）

**動機**：既有 detail page 只看當季數字 + segment 卡片，沒歷史趨勢視覺。User 提供 reference image 要 5Q bar/line chart 風格。

**整合決定**：純新增不取代 — 既有 metric card / segment grid / geographic cell 全保留（資訊密度高），上方加 chart row 提供 5Q 趨勢視角。

**新增 6 charts**：
1. Revenue + Net Income bars × 5Q
2. EPS line × 5Q
3. OCF + FCF bars × 5Q
4. Gross + Operating Margin lines × 5Q
5. Segment YoY Growth horizontal bars
6. Geography YoY Growth horizontal bars（AAPL 為 FY-only fallback → 該卡片自動隱藏）

**FMP API 限制**：geographic Q-level YoY FMP 不提供（只 FY annual），唯一管道 = earnings transcript LLM 抽（infographic.geographic_q.yoy_pct）。AAPL 目前 yoy_pct=null → frontend 隱藏該 chart card。Phase 2 可改 protocol prompt narrate phase 強制從 transcript CFO 段抽 region YoY。

### Files changed
- `dashboard_server.py:1703-1736` — `/api/earnings-infographic/<TICKER>` payload `cache` subset 加三個 trend slice：`quarterly_pnl[:8]` / `cash_flow[:8]` / `margins_8q[:8]`（slim shape，只取 chart 需要欄位）
- `Dashboard/earnings-detail.html` — 加 Chart.js CDN script tag + 新 `<section class="ed-charts-section">` 含 6 個 `<canvas>`，插在 metric cards 後 segments 前
- `Dashboard/page-earnings-detail.js` — 新 `renderTrendCharts(payload)` 共 ~250 行（含 `chartTheme` / `makeChart` helper / 6 個 chart configs）；`renderAll` 加 call
- `Dashboard/style.css` — 新 `.ed-charts-grid` (2-col responsive) + `.ed-chart-card` + `.ed-chart-canvas-wrap` (200px height)
- `Dashboard/i18n.js` — 加 7 個翻譯 key（zh/en）：`section_trends` / `section_trends_hint` / `chart_*` ×6

### Why
User 提供 iOS-widget 風格 infographic 圖；既有 page 缺歷史趨勢。Chart.js 70KB 引入比手刻 SVG 動畫漂亮 + 維護成本低。

---

## [2.7.14] — 2026-05-03
### Fixed — earnings-analyst `fetch.py --force` 洗掉 analyzed fields；AAPL 補回

**問題現場**：dashboard `earnings_analyses` 只見 MSFT/GOOGL/NVDA 三筆，AAPL 不見。

**追因鏈**：
1. 5/2 01:41 有人跑 `python3 skills/earnings-analyst/scripts/fetch.py AAPL --force`（SESSION_NOTES line 189 紀錄為 transcript 測試）
2. `fetch.py` 第 451-453 行直接 `json.dump(bundle, f)` 整檔覆寫 cache JSON
3. analyze.py 之前寫進去的 5 個 fields（`composite_score` / `verdict` / `score_components` / `derived` / `quality_flags`）全洗掉
4. analyze.py 沒被接著跑 → cache 留半殘狀態
5. `bridge.py:extract_earnings_analyses:1551` `if "composite_score" not in d: continue` → 跳過 AAPL
6. data.json 缺 AAPL，dashboard 顯示也缺

**為何 UI 路徑沒問題**：dashboard「跑財報分析」按鈕走 `/api/protocol-queue {name:'earnings'}`，protocol prompt 強制 6 步驟（fetch→analyze→validate→narrate→render→validate_infographic），analyze 一定接 fetch。問題只發生在 user/dev terminal 直接 `fetch.py --force` 略過 chain。

**Fix**：
1. **`skills/earnings-analyst/scripts/fetch.py:448-470`** — overwrite 前先 `read` 既存 cache，preserve `composite_score / verdict / score_components / derived / quality_flags` 5 keys 並 stderr log 「merged N analyzed field(s)」。`--force` 不再洗 analyzed 結果。
2. **AAPL recovery** — 跑 `python3 skills/earnings-analyst/scripts/analyze.py AAPL` → composite=70/100 verdict=SOLID
3. **bridge refresh** — `python3 bridge.py` → earnings_analyses 從 3 筆變 4 筆，AAPL SOLID 70 上線

### Files changed
- `skills/earnings-analyst/scripts/fetch.py` — 加 PRESERVE_KEYS merge 邏輯（~15 行）
- (recovery actions) `skills/earnings-analyst/cache/AAPL_2026-03-28.json` 由 analyze.py 重補
- (recovery actions) `Dashboard/data.json` 由 bridge.py 重產

### Why
未來若 dev 直接終端跑 `fetch.py --force` 測試，不會再連帶把分析結果洗掉。安全網。

---

## [2.7.13] — 2026-05-02
### Added — 每週日早 6:00 自動跑 LLM Review (launchd plist)

**動機**：V2.7.11/12 落 backend queue + indexer freshness gate 後，缺定期觸發。User 要每週固定一次，避免人工健忘。

**作法**：macOS launchd `~/Library/LaunchAgents/com.kavi.aicommittee.llm-review.plist`
- `StartCalendarInterval`：Weekday=0、Hour=6、Minute=0（週日早 6:00）
- 動作：先 health-check `http://localhost:8080/api/refresh_status` (HTTP 200 才繼續) → POST `/api/protocol-queue {name:'llm_review'}`
- Log：`~/Library/Logs/llm-review-weekly.log`

**已驗證**：
- `plutil -lint` OK
- `launchctl load` 無錯
- 手動 `launchctl start` → log 寫 HTTP 200 + queue position 1（順便補 4/27→5/2 缺漏 review）

**限制**：
- Mac 6am 週日 sleep 中 → launchd 不補跑
- dashboard_server 沒在跑 → log 顯 "SKIP: not reachable"，跳過該週
- plist 在 user space (`~/Library/LaunchAgents/`)，不污染 git status

### Files added
- `~/Library/LaunchAgents/com.kavi.aicommittee.llm-review.plist`（OS-level，repo 外）

### Files changed
- `VERSION`、`Dashboard/utils.js`、`CHANGELOG.md` — 版本同步（僅 metadata，無 code）

---

## [2.7.12] — 2026-05-02
### Fixed — LLM Review event_index staleness + 收合 + 標 technical

**Issue 1**：上次 review 跑出來漏掉 4/29 NVDA / TSM 兩筆 deep-dive。根因：`event_index_latest.json` 是 4/26 11:25 indexer 跑出來的，6 天沒 rebuild。LLM Review 直接讀那份 stale 索引 → 看不到 4/27+ 的決策。

**Fix 1**：`llm_review` protocol prompt 加 Step 0 — `python3 scripts/build_event_index.py`，rc=0 才繼續。每次 review 自帶 freshness。Step 2 也加上 `generated_at == today` 檢查，否則 abort。

**Issue 2**：`REVIEW_<DATE>.md` 內容是 protocol-tuning meta-feedback（pattern stats / agent 權重建議 / score 閾值微調），給 maintainer + LLM 下次 protocol 升級時讀，不是 daily user reading。但上版直接在 calendar 攤開 13KB markdown → 用戶被迫滑過去。

**Fix 2**：`#cal-llm-review-section` 改 `<details>` 預設收合，summary 行加 `technical · protocol-tuning` tag 暗示這不是 daily report。Summary 行同時抽 `_decisions_analyzed` + pattern count + recommendation count 顯示在 meta 字串：`2026-05-02 · 56 decisions · 4 patterns · 7 recs`，user 不展開也能掌握 review 規模。

### Files changed
- `dashboard_server.py`：`PROTOCOL_PROMPTS["llm_review"]` 加 Step 0 indexer rebuild + Step 2 freshness check
- `Dashboard/calendar.html`：`#cal-llm-review-section` 從 `<section>` 改 `<details>`，summary 加 chevron + tech tag + refresh button stop-propagation
- `Dashboard/page-calendar.js`：`loadLatestReview()` 用 regex 抽 `_decisions_analyzed` / `### .+(n=N` / Adjustment Recommendations 區內 `###` 數量，組成 meta 字串
- `Dashboard/style.css`：`.cal-llm-review-details` collapsed/expanded 樣式 + `.cal-llm-review-tech-tag` chip + `.cal-llm-review-chevron` rotate

### Why
User 質問為何 4/29 兩筆深度分析被漏掉，並指出 REVIEW_*.md 內容「不是 user 該看的」。第一個是 indexer 沒自動跑的根因；第二個是把 protocol-tuning artifact 跟 daily UI 混在一起的設計錯誤。

---

## [2.7.11] — 2026-05-02
### Changed — 「請 LLM 檢討」改為 backend queue（取代 clipboard copy）

**問題**：原本 button 是把 prompt + event_index 複製到 clipboard，要 user 自己貼到外部 Claude 跑。流程斷裂、Safari 還會擋 clipboard 寫入。User 要的是：點按鈕 → 自動排隊 → 跑完結果直接顯示在頁面上。

**設計**：

1. **Backend 新 protocol `llm_review`**（`dashboard_server.py`）：
   - `PROTOCOL_PROMPTS["llm_review"]` — 指示 Claude 讀 `REVIEW_PROMPT.md` + `event_index_latest.json` → 三步驟（pattern detection / root cause / adjustments）→ 寫 `reports/decision_review/REVIEW_<TODAY>.md`
   - `PROTOCOL_LOG_DIRS["llm_review"] = "reports/decision_review"`
   - `PROTOCOL_TIMEOUT_OVERRIDES["llm_review"] = 900`（15 min）
   - 既有 `/api/protocol-queue` POST handler 自動接受新 name，無需新 endpoint

2. **Frontend click handler 重寫**（`Dashboard/page-calendar.js`）：
   - 刪舊 `prebuildLlmBundle / legacyCopyFallback / copyLlmReviewBundle`（V2.7.9 clipboard 邏輯）
   - 新 `requestLlmReview()`：`window.confirm()` 二次確認（含 「~10-15 min + Claude tokens」警示）→ POST `/api/protocol-queue { name: 'llm_review' }` → toast 顯示 queue position；409 duplicate 也照常啟動 polling
   - 新 `pollLlmReviewStatus()`：每 3s `/api/run-protocol/status`，當 `name=llm_review` 時更新 button label `檢討中… Ns`，status=done → 觸發 `loadLatestReview()`，error → toast log_tail
   - 新 `loadLatestReview()`：fetch `/decision_review/REVIEW_<TODAY>.md`，404 fallback 往前找 14 天最新存在的
   - 新 `renderReviewMarkdown()`：手刻 regex（headers `#/##/###` + bullets `-/*` + bold `**` + italic `_` + inline code `` ` `` + hr `---`），HTML escape 安全
   - 新 `checkLlmReviewRunning()`：page load 時若已在跑，自動接續 polling

3. **UI 新 section**（`Dashboard/calendar.html`）：在 `#cal-aggregate` 上方加 `#cal-llm-review-section`，含標題 + 產出日期 meta + refresh icon button + render 區塊

4. **Button 狀態**（`Dashboard/style.css`）：
   - Idle → 既有 emerald style
   - Running → indigo `cal-llm-review-running` class，pulse animation `cal-llm-pulse 1.6s`，label 動態 `檢討中… Ns`
   - Refresh icon button 同樣 disabled
   - Markdown render 樣式：h1/h2/h3 emerald + indigo 階層；code chip indigo；hr dashed

### Files changed
- `dashboard_server.py`：3 dict 各加 1 entry
- `Dashboard/page-calendar.js`：clipboard 邏輯換成 queue/poll/render（~150 lines 替換）
- `Dashboard/calendar.html`：新 section 區塊
- `Dashboard/style.css`：~120 lines `cal-llm-review-*` 樣式 + pulse keyframe

### Why
User 直接要求：「請 LLM 檢討應該透過 bridge 發到 Claude 處理 + 加到 queue + 結束後自動更新到日曆頁面」。clipboard 流程不符合 dashboard 一鍵化操作的設計目標，且 Safari clipboard 限制（V2.7.9 已 patch 過一次）說明這條路本來就不該走。

---

## [2.7.10] — 2026-05-02
### Changed — Heatmap palette: light-gray center + fluorescent extremes

User 不喜歡原本 zinc-900 深底，改成淺灰中心。新 7-stop divergent scale：

| pct | 色 | 對應 |
|-----|----|----|
| -3% | 螢光紅 `#ef4444` (red-500) | 兩端 saturate |
| -2% | 紅 `#fca5a5` (red-300) | 中段 |
| -1% | 紅淺灰 過渡到 zinc-300 | 接近中心 |
|  0% | 淺灰 `#d4d4d8` (zinc-300) | 中心 |
| +1% | 綠淺灰 過渡到 emerald | 接近中心 |
| +2% | 綠 `#86efac` (green-300) | 中段 |
| +3% | 螢光綠 `#10b981` (emerald-500) | 兩端 saturate |

**算法**：兩段 piecewise linear（center → mid 在 0..0.5、mid → peak 在 0.5..1）讓接近 0% 的 cell 真的看起來像「沒動」（淺灰），±1% 才開始顯色，±2% 強烈。

**Text color**：因為大部分 cell 現在是淺底，threshold 從 0.5% 拉到 1.8% 才換成白字；其餘用 zinc-900 深字確保對比。

**Legend gradient** 也同步換成新 5-stop（red-500 / red-300 / zinc-300 / green-300 / emerald-500）。

---

## [2.7.9] — 2026-05-02
### Fixed — 決策日曆「請 LLM 檢討」按鈕在 Safari 出現 `Copy failed: The request is not allowed by the user agent` 錯誤

**根因**：Safari 嚴格要求 `navigator.clipboard.writeText` 必須在 user-gesture 同步流程內呼叫。原本 click handler `await fetch(REVIEW_PROMPT.md) + await fetch(event_index)` 才寫 clipboard → 兩個 await 之後 gesture context 已失效 → Safari 拒絕複製。

**Fix**（兩段式）：
1. **Pre-build bundle on page load**：`loadAndRender()` 結尾 fire-and-forget `prebuildLlmBundle()` 預先 fetch + 拼接，存到 module-level `llmBundleText`
2. **Click handler 改為純 sync**：用 `document.execCommand('copy')` 配 hidden textarea（legacy 但仍 work，gesture-safe）為主要路徑；`navigator.clipboard.writeText` 為 fallback
3. Bundle 尚未載入完成時點按鈕 → toast 提示 + 觸發再 fetch，下次點即可
4. 全失敗 → toast 引導用戶手動下載 event_index_latest.json

### Why
User 在決策日曆按「請 LLM 檢討」收到 Safari 標準錯誤訊息。標準 web API 限制，必須 sync write。

---

## [2.7.8] — 2026-05-02
### Changed — 決策日曆改為「點擊浮動 modal」交互；移除 hover tooltip

**問題**：上版 hover tooltip 即使重做成 sector-style rich card，hover 區大易誤觸；inline detail panel 又在月曆下方 → 點 cell 後要捲到 panel、視覺和被點 cell 失聯。

**新交互**：
1. 點任一 cell → backdrop（rgba(0,0,0,0.55) + blur(4px)）覆蓋 viewport + 浮動 card 視窗置中（720×80vh, scale-in 18ms cubic-bezier）
2. 關閉路徑：backdrop click / Esc / card 右上 × — 三條都保留；不保留「再點同 cell toggle」
3. 點不同 cell → 直接替換 card 內容，不需先關
4. body scroll lock（`body.cal-detail-locked`）防止月曆背景同步捲動
5. Card 內容 `overflow-y: auto`，max 80vh — 處理 5/29 那種 30+ ticker case
6. **完全移除 hover tooltip**：刪除 `#cal-tooltip` element / CSS（~80 行）/ `wireCellTooltip()` JS（~75 行）/ event row 的 `data-cal-tip` attribute
7. event row hover affordance：保留 `cursor: pointer`，cell 整體已有 hover lift 樣式

### Files changed
- `Dashboard/calendar.html`：`#cal-detail` 加上 `.cal-detail-card` 子層 + 新 `#cal-detail-backdrop`；刪 `#cal-tooltip`
- `Dashboard/page-calendar.js`：openDetailPanel/closeDetailPanel 多 backdrop show/hide + body scroll lock；wireControls 加 backdrop click → close；刪 wireCellTooltip + bootstrap call + renderEventLogoGroup 內 data-cal-tip
- `Dashboard/style.css`：`.cal-detail-panel` 改為 fixed inset 0 flex center + `.cal-detail-card` 720×80vh scale-in；新 `.cal-detail-backdrop`；新 `body.cal-detail-locked`；刪整段 `#cal-tooltip` 規則；event row `cursor: pointer`

### Why
User 直接要求：「點單日會展開一個新的 cardview float 在 calendar 上顯示當天所有的內容；取消 tooltip」。這把資訊密度交給點擊互動而非 hover，讓月曆瀏覽更乾淨。

---

## [2.7.7] — 2026-05-02
### Changed — Decision card tooltips upgraded to rich pill-popover style

**Problem**: User 嫌 native `title` tooltip 樣醜（系統預設黑底）+ `cursor-help` 變成 `?` 游標破壞流暢感。

**Fix**: 把 `Dashboard/page-decisions.js` 內所有 pill 的 hover 解釋改成 sector page 同款 rich tooltip：

1. **新 `DECISION_TIPS` map**（zh + en）— 12 個 entry：tp_sl / dual_track / da_filed / contrarian / pos_binary / neg_binary / consensus / fragility_robust / fragility_moderate / fragility_fragile / phase2_fanout / degraded_lanes / burry_override
2. **每個 tip 含 title / desc / scale 三層** — title bold (CJK 800 weight)、desc 段落說明、scale 用 emoji + 縮排列出狀態階梯（如 fragility 的 🟢/🟡/🔴 三檔）
3. **`#decision-tip` 元素** 加到 `decisions.html` `</main>` 後面，CSS 抽到 `style.css`（`#decision-tip` + `.tip-title/.tip-desc/.tip-scale` 全域共用）
4. **`initDecisionTip()`** mouseover/mouseout 偵測 `[data-tip-key]`，定位邏輯（top-flip below if cramped, horizontal clamp）跟 sector page 完全一致
5. **替換**：所有 `title="..."` + `cursor-help` → `data-tip-key="..."`。`cursor-help` 全部移除（不再有 `?` 游標）
6. **TP/SL 區塊** 整塊綁 `data-tip-key="tp_sl"`，hover 兩個值都會顯示同一個 rich tooltip
7. **Dual-Track 標題列** 綁 `data-tip-key="dual_track"`，hover 解釋 AGG/CONS 概念

### Why
User 截圖比較 native title vs rich pill tooltip — native 看起來像 1995 年瀏覽器警告框，rich 版有 title/desc/scale 三層結構、跟 sector page 已存在的 regime/breadth/exposure pill tooltip 風格統一。`cursor-help` 的 `?` 也跟整體 UX 不搭。

---

## [2.7.6] — 2026-05-02
### Fixed — 日曆 cell ticker 字對比 + tooltip 改為 sector page 同款卡片視覺

**問題**：
1. cell 內 ticker 文字（NVDA / NTRS · NVTS · APLD 等）`color: var(--text)` 太淡，淺色模式幾乎看不到
2. 上版 cal-tooltip 雖然用 var(--bg-card) 但只是單調深底 + 平鋪每行，跟 sector / news page 用的 signal-tip-tooltip rich card style 不像

**Fix**：
1. `.cal-cell-decision-tickers` / `.cal-cell-event-tickers` / `.cal-cell-event-text`：font-weight 800、size 10.5px、letter-spacing 0.03em，加 light/dark 主題對比色（light=zinc-900、dark=zinc-200）；high impact 黃、binary 紅
2. `#cal-tooltip` rebuild：
   - title row 含 category icon + 大標 + 右側 count（`💼 財報  · 13 件`）
   - rows 用 grid-cols `auto auto 1fr`（icon / ticker / event title），奇數 row 淡灰底
   - footer line 列 ⚠️ binary risk / 🟡 high impact flag
   - light theme 白底（rgba(255,255,255,0.98)）+ subtle shadow；dark theme 維持 var(--bg-card)
   - Ticker 用 teal 強調色（light=teal-700, dark=teal-300），跟 sector page tooltip ticker 風格一致
   - max-height 360px + scroll 處理 30+ ticker 場景
3. JS `buildTipHtml` 帶 `catMeta` icon dictionary，emit grid layout

### Why
User 截圖比較自家 sector page tooltip（`market_breadth · 33.1 · score 75+ 健康強勢` 那種 rich card 配色）vs 我寫的單調 dark pill — 要求視覺一致 + ticker 文字加深。

---

## [2.7.5] — 2026-05-02
### Changed — 決策日曆 cell tooltip 改為 custom rich tooltip

**問題**：cell 內 future-event row hover 出來的是 native browser `title=` tooltip — 醜（深灰扁長條）、被瀏覽器決定何時顯示、event 全部擠成一行 ` · ` 串接、不能格式化 ticker。

**Fix**：
1. 新增 `#cal-tooltip` 浮動元素（HTML），CSS 用 signal-tip-tooltip 同款（`var(--bg-card)` + `var(--border-hover)` + `backdrop-filter: blur(8px)`）
2. 每 row 用 `data-cal-tip` 帶 JSON payload（icon / ticker / title / impact / is_binary）
3. JS delegated `mousemove` 在 `#cal-grid` 偵測 hover，跟隨鼠標位置（自動避免超出 viewport）
4. Tooltip 內容：標題 `[category] · N`，每事件一行：`icon ticker title`，impact=high 黃字、binary 紅字
5. 移除 row 上的 native `title=` 屬性避免雙重 tooltip

### Why
User 截圖 5/29 cell hover 跑出 native tooltip 把 30+ 個 ticker 擠成一團，要求「跟其他頁面 tooltip 風格一樣，一行一行列出來，icon/name/event」。

---

## [2.7.4] — 2026-05-02
### Fixed — Decision card light-mode contrast + missing tooltips + translations

**Light-mode 對比 (Red Team block)**：
- thesis 內文 / kill conditions / summary text：原本 `text-zinc-300/400` 在白底幾乎不可見 → 改用 `style="color:var(--text-main)"`（自動跟主題切換）+ `text-zinc-700 dark:text-zinc-300`
- Failed warning：`text-amber-400` → `text-amber-600 dark:text-amber-400`
- Counter thesis summary 文字加粗 + 字級 10px → 11px

**新增 hover tooltips**（用 native `title`，與 V5.0 anchor chip 一致）：
- `DA Filed` / 反向論點已提交：解釋 PM Devils Advocate 流程（書面記錄反 thesis 的論述，quality flag）
- `CONTRARIAN` / 逆勢訊號：解釋此分析違反當下 macro regime 體制
- `POS BINARY` / 正向二元事件：48h 內確定 catalyst（財報/法規/併購）
- `NEG BINARY` / 負向二元事件：48h 內確定下行 catalyst
- `×1.15 CONSENSUS`：四個分析師同向 → 模型分數加權
- `FRAGILE / MODERATE / ROBUST`：Tail-risk 三維評估（穩健 / 中等脆弱 / 脆弱）
- `Phase2 fanout` 降級警示：subagent 部分失敗
- `Degraded` lane 計數：列出哪些 lane 沒成
- `BURRY OVERRIDE`：Burry 模型推翻共識 BUY → 倉位減半 + recheck
- `TP / SL` 區塊：止盈止損定義 + R/R 計算公式
- `Dual-Track Entry`：AGG/CONS 雙軌進場意義（搶趨勢 + 等回測，降低 timing 風險）

**翻譯**：
- `FRAGILE` → 「脆弱」、`MODERATE` → 「中等脆弱」、`ROBUST/RESILIENT` → 「穩健」（zh 模式）
- `FLASH` 按鈕（zh）→ 改名為「即時新聞」（更直覺）

### Why
User 看到白天模式 NVDA Red Team 反向論點區塊「文字幾乎隱形」、status pills 縮寫看不懂意思（FRAGILE / 逆勢訊號 / DA Filed 沒解釋）、TP/SL/AGG/CONS 在卡上頻繁出現但對非交易員 user 抽象。一次性補完所有 hover 解釋，並修白天模式對比。

---

## [2.7.3] — 2026-05-02
### Fixed — Cell dashed-line baseline 對齊

**問題**：Layer B（未來事件區）高度依事件數量伸縮，1 row vs 2 row → dashed line 在不同 cell 出現在不同 y 位置（看起來歪歪的）。

**Fix**：
1. `.cal-cell-event-rows { min-height: 50px }` — 固定 2 行 slot 高度
2. 無事件 cell 也 render `<div class="cal-cell-event-rows is-empty">` placeholder（dashed line 顏色降淡）→ 整月所有 cell 的 dashed line 都在同一 y

### Why
User 截圖顯示 5/27 (1 row VZ) vs 5/28 (2 row GM·KO·V + CB) 的 dashed line 高度差很大、整體不齊。

---

## [2.7.2] — 2026-05-02
### Fixed — 決策日曆 cell 排版微調

1. **Layer A 固定高度（22px）**：過去決策列即使空白也保留 slot → 未來 earnings 永遠錨在 cell 底部、不再因為當日無分析而上浮
2. **Cell min-height 96px → 144px**：拉高 ~2 行，雙層 logo + 2 行 event rows 不再互相擠
3. **Cell padding 收窄**：`8px 10px` → `6px 9px 8px`，視覺更緊湊
4. **日曆 main container padding**：`p-6` → `px-6 pt-2 pb-6`、`space-y-5` → `space-y-4`，星期 header 上方空白少 ~20px
5. **Day-of-week header padding**：`8px 0` → `4px 0 6px`

### Why
User 跑了一輪實際看到 5 月 cell 後回報：「過去分析高度不固定 → 未來財報往上擠」+「上面星期 padding 太多」+「cell 可以拉高兩行 (Mac Safari 不會蓋到)」。

---

## [2.7.1] — 2026-05-02
### Changed — Decision card header de-clutter

**Problem**: V5.0 卡 header 大標題行同時擠了 ticker / sector chip / current price，再加 metadata 行的 date / @analysis_price / +5 history，加上右上角 V5.0 bookmark + refresh + 「執行建倉」status pill — 整個視覺爭注意力。

**Changes**:
- **Sector chip 從大標題行移到 metadata 行**：跟 date / @ 分析價 / +N history pill 並排，整體歸為「次要資訊」一條
- **Bookmark V5.0 縮小** + 透明度降到 0.85：`9px → 8px font`、`padding 3/9/4 → 2/7/3`、`right 18px → 8px`、`box-shadow` 也縮小，不再跟綠色 status pill 搶眼
- **Current price 字級** `text-sm → text-base`：頭排只留 ticker + 價格，反而 prominence 拉起來
- **price 跟 drift % 之間** 加 `ml-1` 微距，避免黏太緊

### Why
User 回報「視覺好擁擠」附 NVDA 卡截圖。三軌：(1) 把 sector chip 等 metadata 統一到第二行；(2) bookmark 視覺重要性降一級；(3) 大標題行只剩兩件事（ticker + price），讀起來輕鬆很多。

---

## [2.7.0] — 2026-05-02
### Changed — 決策日曆 (calendar.html) 重新設計：logo 疊合 + 雙層 cell + 底部摘要

**問題**：日曆讀 `event_index_latest.json`（last indexed 2026-04-26 stale 6 天），新分析（5/1、5/2 NVDA/TEAM/VRT/LLY 等）看不到；cell 只顯示 source icon badge 看不到 ticker；下方「依來源彙總」9 stat tile 視覺嘈雜且和「過去決策 + 未來事件」narrative 無關。

**設計**（採用 iOS 通話 widget 風格 logo 疊合 pattern）：

1. **資料源切換（核心修復）**：calendar 改讀 `data.json:recent_analysis[]` 為主，`event_index.decisions[]` 降為 verdict overlay（by `(date, ticker)` key）→ 即時看到當日分析，無 indexer 等待
2. **雙層 cell**（min-height 96px）：
   - Layer A 過去決策：logo stack（圓形 ticker logo 重疊 + verdict ring）+ ticker 文字
   - Layer B 未來事件：每 category 一行（`💼 logo-stack AMD·ET`、`🏛️ FOMC`），同 icon 不重複
3. **Logo + monogram fallback**：FMP CDN deterministic URL `images.financialmodelingprep.com/symbol/<TICKER>.png`，404 onerror → 首兩字母 monogram 圓點（hash 出穩定背景色）
4. **底部 panel** 取代「依來源彙總」：
   - **Past 30 Days** ticker pill cloud（按 decision 顏色：EXECUTE 綠 / STAGED 琥珀 / CANCEL 紅），點 pill 開 report
   - **Coming Up Next 7 Days** 時序 strip（按日期 + category 分組）
   - **Verdict Review by Source**（原 aggregate）降級為 collapsible `<details>`，預設收合
5. **密度切換**：filter bar 加 `[High + Watchlist] / [All earnings]` 切換鈕（壓掉 2351/14d earnings 雜訊），預設 high impact ∪ watchlist；偏好存 localStorage

### Files changed
- `bridge.py`：`extract_audit_history()` + `aggregate_upcoming_events()` 加 `profile_image` 欄位（synthesize FMP CDN URL，零成本）
- `Dashboard/page-calendar.js`：新 loader merge `recent_analysis[]` ∪ `indexDecisions[]`；新 `renderTickerLogo` / `renderLogoStack` / `renderDecisionLogoGroup` / `renderEventLogoGroup` / `renderMonthlySummary` / `renderUpcomingStrip`；`renderDecisionCard` + `renderUpcomingCard` header 加 logo
- `Dashboard/calendar.html`：`#cal-aggregate` 改為 `<details>` 收合；新增 `#cal-monthly-summary` + `#cal-upcoming-strip` + `#cal-density-toggle`
- `Dashboard/style.css`：新 `.cal-ticker-logo` / `.cal-logo-stack` / `.cal-monogram-fallback` / `.cal-cell-decision-row` / `.cal-cell-event-rows` / `.cal-bottom-section` / `.cal-monthly-pill` / `.cal-up-strip-*` / `.cal-aggregate-details`

### Why
User 直接回報：「最近做過的分析都沒在 calendar」+「沒辦法一目瞭然知道哪些公司有分析」+「下方來源匯總 ui 很奇怪」。重設目標：一頁看到「過去做過的公司 + 未來重要 earnings」，保持月曆排版緊湊感。

---

## [2.6.1] — 2026-05-02
### Fixed — V5.0 decision card UX polish

1. **`<details>` 點擊被 history drilldown 攔截**：`page-decisions.js` 的 grid click delegation 把 `summary, details` 加入 ignore selector，反向論點現在點一下就展開（原本要點兩下）
2. **Valuation 區塊文字太淡**：label `text-[8px] text-zinc-500` → `text-[10px] text-zinc-300`；anchor chip text `text-zinc-400` → `text-zinc-100`、bg `bg-zinc-800/60` → `bg-zinc-800`、border `border-zinc-700/50` → `border-zinc-600`；methodology note `zinc-500` → `zinc-400`
3. **Anchor chip 加 hover tooltip**：新增 `ANCHOR_INFO` 常數，6 種估值錨點（DCF-U / DCF-L / Analyst PT / Peer P/E / Owner E. / Forecaster）都有中英解釋，hover chip 即顯示 native tooltip。`cursor-help` 視覺暗示

### Why
昨天上線 V5.0 卡後 user 試用回報三點：細節點不開、label 看不清、chip 縮寫看不懂意思。

---

## [2.6.0] — 2026-05-02
### Added — Version-aware decision card UI (V5.0 / V4.8 / V4.7 / V4.6 / Legacy)

**新功能：決策中心個股卡片改成「按 protocol 版本顯示對應欄位」**

**右上角 bookmark 標籤**：每張卡都有一個從卡頂垂下的小 tab 標 `V5.0` / `V4.8` / `V4.7` / `V4.6` / `ARCHIVE`，配色：
- V5.0 = 綠（emerald，最新）
- V4.8 = 藍 (主流)
- V4.7 = 琥珀 
- V4.6 / V4.5 = 灰
- legacy / 無版本 = 暗灰 ARCHIVE

**版本特定區塊**：
- **V5.0**：`Valuation · Fair Value` 區塊 — 顯示 `weighted_fair_value` / `vs_current_pct` / `confidence` / `verdict_band` (極度低估/低估/合理/高估/極度高估，色條配對) + 6 個 anchor chips (DCF-U/DCF-L/Analyst PT/Peer P/E/Owner E./Forecaster) + methodology note
- **V5.0/V4.8/V4.7**：`Red Team 反向挑戰` 區塊 — verdict pill (NO_VIABLE / MODERATE / STRONG)、counter thesis (collapsed `<details>` 展開)、kill conditions 編號清單 (前 3)
- **V4.8 status pills**（加在 badges 列）：fragility (ROBUST/MODERATE/FRAGILE)、phase2_fanout_mode 非 PARALLEL 時警示、degraded_analysts 數量、burry override + recheck date
- **V4.6 / V4.5 / Legacy**：保留現有最簡卡片 + bookmark 標版本

**bridge.py**：plumb 9 個版本欄位進 `recent_analysis[]`：`protocol_version`, `fragility_label`, `red_team_*` (4), `phase2_fanout_mode`, `degraded_analysts`, `burry_override*`, `ftd_timeline_gate`, `valuation_lane`, `fair_value_summary`

**i18n**：新增 ~25 組 zh + en 字串 (`fv_*`, `rt_*`, `degraded_lanes`, `burry_override`)

### Why
原本 buildCard 對所有版本一視同仁渲染，新版 protocol 加的欄位 (V5.0 fair value、V4.8 red team / degraded lanes) 沒被顯示，等於 protocol 升級了 dashboard 看不出來。改成版本感知後：(1) 升級新欄位自動冒出來；(2) 老資料 graceful degrade，仍可讀；(3) bookmark 一眼看出每筆是哪版分析的，方便對照解讀深度。

---

## [2.5.1] — 2026-05-02
### Added — Momentum filter chips: rich tooltips for V2.1 signals + new presets

**User feedback**: 新加的 chips 沒 tooltip — 點 dual_engine / nh_leaders 等 V2.2 preset 跟 hover V2.1 signal chips (vcp_compressed / rs_leader_3m / dtc_squeeze_candidate ...) 都沒大型解釋 tooltip。

**Root causes**:
1. `Dashboard/page-momentum.js` `SIG_DESC_ZH` / `SIG_DESC_EN` 只有 V2.0 11 個 signal，缺 V2.1 7 個 leader-finder signal description
2. `PRESET_DETAIL_ZH` / `PRESET_DETAIL_EN` 還是 V2.0 9 個舊 preset 內容，沒 V2.2 11 個新 preset entry → 點 dual_engine 等找不到 tooltip data
3. `renderSignalChips()` / `renderWarningChips()` / `renderRequiredWarningChips()` 只有 native `title` attribute（淺顯），沒 `data-sig-tip` / `data-warn-tip` → 不會觸發 mom-pill-tooltip 大 tooltip 機制

**Fixes**:
- 新加 7 個 V2.1 signals 的 SIG_DESC_ZH/EN（含 desc、tiers 分級、hint）：`at_52w_new_high`, `near_52w_high`, `rs_leader_3m`, `vcp_compressed`, `vol_dryup_spike`, `eps_accelerating`, `dtc_squeeze_candidate`
- PRESET_DETAIL_ZH/EN 整個 rewrite：11 個 V2.2 preset 各含 criteria（filter 規則）+ strategy（市場意圖）+ action（如何用）三段式內容
- filter chips 加 `data-sig-tip` / `data-warn-tip` attribute，hover 觸發 mom-pill-tooltip 大型 tooltip（含 tiers 分級表 + hint）

### Why
- chip 上方 hover 才看得到完整解釋（V2.1 新 signals 對 user 是陌生概念，必須有解釋才會用）；舊 chip 也順帶升級到大 tooltip

---

## [2.5.0] — 2026-05-02
### Changed — Heatmap UX polish (top placement, brighter colors, more tickers)

- **Position**：`heatmap-section` 從 verdict matrix 下方移到 `sector.html` 最上面（剛進頁面就是視覺焦點）
- **配色**：從 zinc-500 中性灰改為 zinc-900 深底，配上 emerald-500 / red-500 鮮色 — 解決原本「整體偏灰偏髒」的觀感
- **Ticker 顯示密度大幅提升**：移除原本 `width > 30 && height > 22` 的高 threshold，改為「能塞水平就水平、塞不下但夠高就轉 90°」邏輯。窄高 cell 用垂直 ticker
- **標籤截斷**：sector / industry 標籤照 box 寬度估算可容納字數截斷加 `…`，box 太小直接隱藏 — 修正原本標籤從 box 溢出到背景的鬼字（"ology Set..."、"kers"）
- **i18n 修正**：`heatmap_*` keys 原本誤加在 `i18n.zh.sector_page` 第一個 block，但被同檔後面第二個 sector_page block override，導致 zh 模式 tooltip label 顯示英文 fallback。已搬到正確的 winning block，zh 模式 tooltip 現在正確顯示「現價 / 漲跌 / 市值 / 日內區間 / 成交量」
- **Color legend gradient** 同步更新成新配色（dc2626 → 27272a → 16a34a）

### Why
盤後測試時 user 回報觀感問題：（1）顏色看起來髒、（2）很多 cell 沒 ticker 但其實裝得下、（3）背景出現詭異殘字、（4）tooltip 標籤沒翻成中文、（5）想看熱力圖要先滑過 verdict matrix。一次性修完。

---

## [2.4.1] — 2026-05-02
### Fixed — Momentum preset chip active-state mis-highlight

**Bug**: 點 `dual_engine`（💎 加速雙引擎）後 active highlight 跳回 `nh_leaders`（🚀 新高領航者）。其他 V2.1 preset 也有此 bug。

**Root cause**: `_activePresetKey()` 只比對 V2.0 fields (minScore / stage / label / onlyHotSectors / requiredSignals / excludedWarnings)。新 V2.1 preset 的 V2.0 簽名常相同（都 stage='Stage 2 uptrend' + 0 signals），導致迴圈第一個 hit 永遠是 FEATURED_PRESETS[0] = nh_leaders。實際 filter state 套對，只是 chip 高亮錯位。

**Fix**: `Dashboard/page-momentum.js:_activePresetKey()` 加 V2.1 fields 比對 (`minNhp`, `minRs`, `minRs3mPct`, `minDtc`, `minEpsYoy`, `minRsi`, `maxRsi`, `topSectors`, `requireVcp`, `requireVolDryupSpike`, `requireEpsAccel`)。`_numEq` helper 處理 null/number 對等。

---

## [2.4.0] — 2026-05-02
### Added — Dashboard Momentum UI: V2.1 leader-finder 完整整合 + preset 重設計

**Problem**: V2.1 加了 7 個 leader-finder 指標到 momentum.py / screen.py，CSV 已有 10+ 新欄位，但 Dashboard 整條 stack 沒接 — 進階篩選 0 個新 input、PRESETS chips 仍 V2.0 過嚴 criteria、signals chips 0 個新項、i18n 0 翻譯。

**4-layer integration**:
- **`bridge.py`**：`_build_row()` 加 15 個 V2.1 欄位 + `_load_sector_rs_rank()` 新函式（GICS canonical 名 alias map：`Information Technology` ↔ sector_intel `Technology`）→ 注入每行 `sector_rs_rank`
- **`Dashboard/page-momentum.js`**：`defaultFilter()` 加 9 個 V2.1 fields + `matchesFilter()` 加 9 條 filter chain + `PRESETS` 整個 rewrite（11 個新 preset：5 featured + 6 secondary）+ `FILTER_SIGNALS` 加 7 個 V2.1 signals + `renderFilterPanel()` 8 個新 control binding
- **`Dashboard/momentum.html`**：新 「🚀 Leader Finder (V2.1)」section（5 input + 3 checkbox）
- **`Dashboard/i18n.js`**：signals_map 加 7 個 V2.1 翻譯 + 11 個 preset label/tip + 9 個 filter 控制 key（zh + en 雙語）

**Featured presets (top rail)**:
1. 🚀 新高領航者 (`nh_leaders`) — RS≥75 + NHP≥-5 + Stage 2 + Top 4 sectors
2. 🎯 VCP 突破前夕 (`vcp_setup`) — VCP compressed + dry-up spike
3. 💎 加速雙引擎 (`dual_engine`) — EPS accelerating + RS≥60 + Stage 2
4. 🔥 強勢突破 (`breakout`) — fresh GC + 量能擴張 (保留)
5. ⚡ 軋空潛伏 (`dtc_squeeze`) — DTC≥5 + 站上 50MA

**Secondary (expand)**: 🎢 強勢回檔買點 / 📈 52w 高點池 / 🎯 無過熱精選 / 📊 MACD 突破確認 / ⚡ MACD 動能加速 / 📊 全部

**砍舊 preset**：`leaders` (過嚴 onlyHotSectors), `uptrend` (與 safe_quality 重疊), `pullback` (純 oversold 太鬆), `squeeze` (高短利率太罕見), `macd_reversal` (用太少)

### Verified
- bridge.py + sector_intel mapping：NVDA/WOLF/MU (Tech) → sector_rs_rank=1；GNRC (Industrials) → 4；XOM (Energy) → 3
- 完整 stack 通到 `data.json.momentum_screen.rows[]` (528 rows，全 V2.1 欄位 populated)

### Why
- V2.1 算了一堆指標但 user 在 Dashboard 看不到等於白做
- 取代過嚴 / lagging 的舊 preset（原 leaders 用 score≥75 + onlyHotSectors 過嚴；原 breakout 用 fresh_golden_cross_50_200 lagging 30-60 天；新 preset 用 RS / NHP / VCP 早期信號）

---

## [2.3.0] — 2026-05-02
### Fixed — Heatmap startup behavior on after-hours / weekend

- 加入 `_heatmap_load_from_cache()`：server 重啟時先讀 `Dashboard/heatmap.json` 把 in-memory state warm up，避免 endpoint 回傳空 ticker 名單
- 加入 `_heatmap_has_quote_data()`：判斷是否需要強制 startup quote refresh
- 修正 startup 邏輯：若無快取資料則無視 market hours gate 強制做 1 次 quote refresh（FMP 盤後仍回傳上次收盤價 + 當日 % change，正是 heatmap 該顯示的）
- 之後在 loop 內維持原本邏輯（盤中才 3 分鐘 refresh，盤後保留最後 snapshot）

**Why**：原本盤後 startup 只 build universe（拿到 ticker 但 `market_cap=0`、`price=null`），前端 `market_cap > 0` filter 把全部 box 濾掉導致空白。新邏輯確保任何時候啟動 server 後都立即有可顯示的資料。

---

## [2.2.0] — 2026-05-02
### Added — Live Market Heatmap (S&P 500 + NDX 100)

**新功能：sector.html 加入即時熱力圖**
- Treemap：Sector → subSector → Ticker，大小 = market cap，顏色 = 當日 % change（-3% red ↔ +3% green）
- Universe = S&P 500 ∪ NDX 100（去重 ~517 ticker），用 FMP `/stable/sp500-constituent` + `/stable/nasdaq-constituent`，每 18h 重建一次
- Quote refresh：FMP `/stable/batch-quote?symbols=...`，200 ticker/call、3 calls/refresh、~4 sec 完成
- 後端 polling thread 住在 `dashboard_server.py` 同 process（盤中每 3 分鐘，`./open_dashboard.sh` 啟動 / 結束自動同步）
- 前端 D3 v7 treemap，layout cache 機制：universe 不變只 update 顏色（~10ms），visibility-aware polling 切 tab 自動暫停
- Hover tooltip 立即顯示快取資料（價、漲跌、市值、日內 range、成交量）；停留 **3 秒**後才打 `/api/heatmap/news/<TICKER>` 抓 1-2 則新聞 headline（user-confirmed debounce）
- 兩個新 endpoint：`/api/heatmap/data`（前端 polling）、`/api/heatmap/news/<TICKER>`（lazy news with 30 min server cache）
- API budget：~840 calls/day，FMP Starter 配額 10%

### Changed
- `Dashboard/sector.html`：加 D3 v7 CDN + heatmap section + tooltip element
- `Dashboard/page-sector.js`：+220 行 heatmap render / tooltip / polling 邏輯
- `Dashboard/i18n.js`：加 11 個 heatmap_* 字串（zh + en）
- `dashboard_server.py`：+200 行（state、4 個 helper、polling thread、2 個 endpoint）

### Why
原本 sector.html 只有 Phase 1-5 中期視角（rotation / breadth / sentiment）。加入即時熱力圖補完「當日 intra-day」這層，雙層視角（中期 ↔ 當日）在同一頁。Heatmap 自成 sub-system（獨立 polling、獨立 JSON、獨立 endpoint），不和 bridge.py / data.json pipeline 耦合。

---

## [2.1.0] — 2026-05-02
### Added — Momentum Screener V2.1: 7 leader-finder indicators

**Problem**: 既有 `動能選股` filter criteria 過嚴 (composite ≥70 + Stage 2 精確 match + parabolic_blowoff 排除 above-200 > 50%) 把真正 leader 全砍掉；signals 用 lagging 信號（fresh_golden_cross_50_200 慢 30-60d）+ 過鬆 vol 門檻 (ratio_20d ≥ 1.3)。

**Added 7 new indicators in `skills/momentum-monitor/scripts/momentum.py`**:
1. **NHP** (52w New-High Proximity)：`pct_from_52w_high` + `is_new_high` + `weeks_since_high`。signal `at_52w_new_high` (≤0.5%) / `near_52w_high` (≤5%)
2. **RS vs SPY** (3M / 6M)：`rs_3m_pct` / `rs_6m_pct` / `rs_rating` (0-99)。signal `rs_leader_3m` (rs_3m ≥ +15pp)。Module-level SPY hist cache 1h，避免 N×SPY fetch
3. **VCP Compression** (Minervini)：4w/12w range ratio。signal `vcp_compressed` (< 0.55)
4. **Volume Dry-up Spike**：5D/20D < 0.75 (dry up) AND today/20D > 1.5 (spike)。signal `vol_dryup_spike`
5. **EPS Acceleration** (CAN SLIM C)：opt-in 讀 `earnings-analyst/cache/<T>_*.json`（cache miss 0 cost）→ `latest_q_yoy_pct` + `growth_acceleration`。signal `eps_accelerating`
6. **Days-to-Cover** tier：`none/low/moderate/elevated/high`。signal `dtc_squeeze_candidate` (DTC ≥ 5 + above MA50)
7. **Sector RS pre-filter** (`screen.py`)：從 `sector/sector_logs/*_sector_intel.json` 讀 top-N sectors by composite_score → `--top-sectors N`

**`skills/momentum-monitor/scripts/screen.py` new CLI flags**:
- `--min-nhp N` / `--min-rs N` / `--min-rs-3m-pct N`
- `--require-vcp` / `--require-volume-dryup-spike`
- `--min-eps-yoy N` / `--require-eps-accelerating`
- `--min-dtc N` / `--top-sectors N`

CSV columns + MD table 加 NHP / RS3M / VCP / EPS YoY / DTC 欄位。

**Cache invalidation**: `schema_version: "v2.1"` field bumped；舊 cache 自動 stale 重抓。

**SKILL.md 更新**: filter flags table 加 V2.1 leader-finder section + 3 個範例 (leader-hunter / VCP-setup / squeeze-candidate)

### Why
- 真正 momentum leader (NVDA / VRT / MU) 通常 above_ma200 50-100%，被 `parabolic_blowoff_risk` 過嚴排除
- 「Stage 2 uptrend」字串 match miss 掉 Stage 1→2 過渡期突破前的 setup
- O'Neil RS rating + Minervini VCP + CAN SLIM EPS acceleration 都是經典 leader-finder 指標，repo 既有資料源（yfinance hist + earnings-analyst cache + sector_intel.json）就能 derive，0 額外 cost
- Sector RS pre-filter 避免在弱勢 sector 找動能（強勢 sector 內找強勢股勝率高）

### Test
- SOX 30 → 18 matched with `--min-nhp -10 --min-rs 60`
- SP500 503 → 26 matched with `--top-sectors 4 --min-rs 75`
- WOLF 觸發 `dtc_squeeze_candidate` (DTC 6.5d + MA50)，APA 觸發 `vcp_compressed` (ratio 0.541)

---

## [2.0.1] — 2026-05-02

### Changed
- 將三個第三方 git repo (`finance-skills/`, `fmpstab/`, `Fincept_enhance/`) 統一移入 `reference/`
- 將鬆散文件 (`ARCHITECTURE_DIAGRAM.md`, `bug.md`, `plan_short.md`) 移入 `docs/`
- `CLAUDE.md`：更新 `plan_short.md` 路徑參考 → `docs/plan_short.md`
- `.gitignore`：`Fincept_enhance/` → `reference/`（整體 ignore 第三方 repos）

### Why
根目錄過度雜亂，三個純參考用的 nested git repo 與核心 protocol 檔案混在一起。整理後 core ops 與外部參考資料有清楚分層，不影響任何 protocol/skill 運作。

---

## [2.0.0] — 2026-05-02
### Major — Investment Protocol V5.0 (5-lane + Fair Value Estimation)

**Protocol restructure**:
- **`investment/investment_protocol_v5_0.md`** (NEW)：精簡版主文（867 行 vs V4.8 1278 行 = -32%），砍 V4.7-V4.11 沿革說明、整合 PM MUST/MUST NOT cheatsheet
- **`investment/protocol_appendix_fmp_bundles.md`** (NEW, 155 行)：把 EARNINGS_ANALYST_BUNDLE / PEER_BUNDLE / FMP_SUPP_BUNDLE 三層 bundle 詳細 schema + injection rules 從主文挪出

**新監管者：Valuation Specialist (第 5 lane)**:
- Phase 2 從 4 lane parallel → **5 lane parallel subagent**
- 獨立估值維度：收 6 個 anchor (DCF unlevered/levered, analyst PT, peer PE implied, owner earnings × 15, forecaster blend)
- 加權合理價 vs current price → score -5/+5（折溢價分級）
- 預設 weights：Fund 0.25 / Sent 0.15 / News 0.20 / Tech 0.25 / **Valuation 0.15**
- Phase 2.5 新增 **T5 trigger**：Valuation -3 (extreme overvalued) AND tentative=BUY → 自動 downgrade

**Phase 4.5 — Fair Value Summary (V5.0 NEW)**:
- PM **inline deterministic 計算**（禁 LLM 重評），把 Valuation Specialist 的 6 anchor 用權重 blend
- 缺 anchor 時 weight 重分配（< 3 anchor → confidence=low）
- 輸出 `verdict_band` (extreme_undervalued / undervalued / fairly_valued / overvalued / extreme_overvalued) + `confidence` (high/medium/low)
- Phase 5 MD 報告新增「合理股價估算」section

**FMP API 整合**:
- `executive_compensation` (`/governance-executive-compensation`) → `fmp_supplementary.executive_compensation`：CEO comp YoY > 30% → 治理紅旗
- `comp_benchmark` (`/executive-compensation-benchmark`) → CEO 薪酬 vs 行業中位數
- `employee_history` (`/historical-employee-count`)：5Y CAGR > 15% → 擴張訊號；1Y < -5% → 裁員訊號
- 整合到 Fundamentals + Sentiment + Burry lane rubric

**Schema + Validator 升級**:
- `investment/phase5_export_schema.md`: 加 `valuation_lane` + `fair_value_summary` 必填欄位；version V4.8 → V5.0
- `validate_session_export.py`: 接受 V4.8 (legacy) + V5.0；V5.0 entry 必須含 `fair_value_summary` + `valuation_lane` + `Valuation` weight；驗 verdict_band + confidence enum
- `validate_markdown_export.py`: V5.0 entry 必須在 MD 含「合理股價」section + `weighted_fair_value` 標示

**MD report**:
- Final Visualization Table 加第 5 lane (Valuation) row
- 新「合理股價估算」table（6 anchor + weighted + verdict + confidence）

### Breaking Changes
- `分析 [TICKER]` 觸發從 V4.8 protocol 切到 V5.0 — Phase 2 多 1 個 subagent (~+25% token cost per analysis)
- 新 protocol run 必須產 V5.0 schema entry；舊 V4.8 entries 仍 valid（backward compatible）

### Why
- VRT vs TEAM 分數對比顯示「估值維度」在現有 4 lane 被分散到 Fundamentals 而導致估值警告被稀釋。獨立 Valuation Specialist 給專門 weight + 合理股價 anchor blend 讓 user 一眼看到「這檔現價 vs 合理價」的數字判斷
- V4.8 protocol 1278 行混雜大量歷史變更說明，新 PM session load 時讀不必要 context；V5.0 砍歷史保留 execution 必須資訊

---

## [1.88.1] — 2026-05-02
### Added — Phase 5 markdown score-scale 強制驗證
- **`investment/scripts/validate_markdown_export.py`**: 新檔，post-format gate（rc=0/1）。檢查 Final Score `/3.0`、Burry `/100`，禁 `/5.0` `/10` `/12` drift。可獨立用 `--report <path>` audit。
- **`investment/investment_protocol_v4_8.md`**：
  - Sonnet MD subagent prompt HARD CONSTRAINTS 加 score scale 規範（Final Score `X / 3.0`、4 lane 0-3 裸數字、Burry `/100`、Red Team `N/5`），含正反範例
  - Phase 5 新增 Step 5 markdown validation gate：rc=1 → retry Sonnet 一次，再失敗 PM inline 覆寫 + 重跑 validator
- **驗證結果**：73 份 V4.8 standard 報告 pass；21 份 4/14-4/19 早期 V4.6/V4.7 報告 fail（合理偵測 `/12` Burry bug 等早期 drift）；outlier 全擋（VRT `/10`、MRVL `/5.0`）

### Why
- VRT 報告 freestyle `/10` scale 跟 MRVL `/5.0` scale 是 LLM 在 Sonnet formatter 失敗時手動 fallback 跑掉的結果。Schema 沒強制 → 報告無法跨檔比較分數高低（同 raw consensus 看起來一個 6.72、一個 1.609 完全不同數量級，視覺幻覺）。validator + prompt 雙層強制統一 scale，未來新報告 100% `/3.0`

---

## [1.88.0] — 2026-05-02
### Added — FMP Valuation & Analyst API 深度整合 (Tier 1+2)
- **`skills/earnings-analyst/scripts/fetch.py`**: 新增 6 個 FMP 呼叫 + 5 個 slim helpers
  - `levered_discounted_cash_flow` → `valuation.dcf_levered_intrinsic`（FCFE 模型，補充現有 FCFF DCF）
  - `price_target_news?limit=8` → `valuation.pt_news[]`（機構 PT 調整事件：誰、何時、從X調到Y）
  - `rating_historical?limit=12` → `analyst.rating_history[]` + 計算 `analyst.rating_trend`（improving/stable/declining）
  - `grades_summary` → `analyst.grades_summary`（strongBuy%, total_analysts，比 snapshot 更豐富）
  - `grades_news?limit=10` → `analyst.grades_news[]`（事件級升降評：機構名稱+評級+日期）
  - `_compute_pt_dispersion` 衍生欄位 `valuation.pt_dispersion_pct`（分析師分歧度，>40% 觸發警示）
- **`skills/earnings-analyst/schema.md`**: 新增 V1.74 欄位文件 + Protocol 引用規則說明
- **`investment/investment_protocol_v4_8.md`**：
  - Phase 1 EARNINGS_ANALYST_BUNDLE 加入 `dcf_levered_intrinsic`、`pt_dispersion_pct`、`pt_news`、`analyst` 子區塊
  - Fundamentals lane V1.74 規則：`rating_trend` 取代舊「升評 +0.5」邏輯、`grades_news` 升降評計數信號、`pt_news` 方向信號
  - Burry lane 第 5 規則：levered vs unlevered DCF 差距 > 20% → 資本結構警告 narrative

### Why
- FMP MCP API 審查後，6 個新 endpoint 填補現有「分析師動態」盲點（grades_news 是事件級，grades-historical 只有月分佈）；levered DCF 對高槓桿公司（銀行/REITs/重資本科技）更準確。Tier 3 APIs (custom DCF/market_risk_premium) 需手動參數或用途有限，暫跳過。

---

## [1.87.0] — 2026-05-02
### Added — annual analyst estimates + ESG into bundles
- **`skills/earnings-analyst/scripts/fetch.py`**: `/stable/analyst-estimates?period=annual&limit=3` 加入 EARNINGS_ANALYST_BUNDLE 為 `annual_estimates[]`，含 revenue_avg/low/high + EPS_avg/low/high + ebitda_avg + net_income_avg + num_analysts_revenue/eps。AAPL 確認 3 fiscal year 2028-2030 estimates，eps_avg 從 10.36 → 13.07
- **`skills/_shared/fmp_supplementary.py`**: 新 `_fetch_esg`，從 `/stable/esg-disclosures` 取最新 SEC filing 的 E/S/G/總分，從 `/stable/esg-ratings` 取最新年度 letter rating（B/A/C 等）。AAPL 結果：環保 66.29 / 社會 45.21 / 治理 58.87 / 總 56.79，2025 letter B
- 跳過 COT integration（per-stock protocol 內無相關 instrument，COT 為期貨層級資料；後續若 sector_protocol 需要可獨立加入）
- bundle 體積最終 ~4.4KB（v1.78 起累計）

### Why
- FMP_強化分析.md Section 4.6 + 4.7 + 4.8 P3/P4 工作項。Probe v1.77 已確認三項都免費；annual estimates 補 EARNINGS_ANALYST_BUNDLE 的 forward consensus 缺口（quarterly 為 paid blocker），ESG 補 sentiment / risk lane 的 governance flag

### Out of Scope
- COT report（Section 4.8）— 期貨層級宏觀，不在 invest_protocol 個股分析範圍；若做 sector_protocol macro 章節再加
- Burry rubric 接入 ESG governance score（後續可加，governance score < 50 → SBC 風險加成警示）

---

## [1.86.0] — 2026-05-02
### Added — FMP_SUPP_BUNDLE.congressional_trades + ma_events
- **`skills/_shared/fmp_supplementary.py`**: 新 `_fetch_congressional` (senate-trades + house-trades by symbol，180d window，client-filter) + `_fetch_ma_events` (mergers-acquisitions-latest 200 row 全市場 → client-filter ticker 為 acquirer or target)
- 派生欄位：`congressional_trades.net_signal` ∈ {bullish > 2× sells, bearish > 2× buys, neutral}；`ma_events.events[].role` ∈ {acquirer, target}
- **AAPL 180d**：senate=12, house=18, buys=15 vs sells=15 → neutral；most_recent 2026-04-08。M&A events=0（AAPL 期間無）
- bundle 體積從 ~2.3KB 增至 ~3.8KB

### Why
- v1.85 已 protocol Sentiment+News lane 寫好接收規則；本 bump 把實際資料填進 bundle。Probe v1.77 確認 endpoint 免費。M&A endpoint 無 per-symbol API，只能全市場 + client filter（200 records 約 13 月窗）— mid/small cap 命中率高，mega cap 通常 0 events 為正常

### Out of Scope
- congressional 金額加權（FMP 給的是 range string `"$1,001-$15,000"`，後續可加 `_classify_amount` 已有 helper 待用）
- M&A 全市場 200-record 上限（FMP 沒 from/to 參數）— 罕見的 13 月以外 events 不會抓到，OK

---

## [1.85.0] — 2026-05-02
### Changed — `investment/investment_protocol_v4_8.md` V4.11 — 4 個 lane 接入 FMP_SUPP_BUNDLE 規則
- **Burry lane**（`Phase 2 末段 Burry inline`）：新增 4 條確定性規則
  - Altman Z danger → score -2，grey → -1
  - Piotroski F ≥ 7 → +1（不強制 verdict，保 LLM 收尾權）
  - Owner earnings vs GAAP FCF > 30% 差異 → narrative 標註
  - insider trend accumulating → 允許 insider_pts 升至 1
  - 任何單一規則 ±2 上限；FMP_SUPP_BUNDLE 缺則整條 skip
- **Fundamentals lane**：FMP_SUPP_BUNDLE.quality_scores → score ±1；owner_earnings.qoq_growth < -30% → -0.5
- **Sentiment lane**：FMP_SUPP_BUNDLE.institutional.accumulation_signal ±1；put_call_ratio_change > 0.2 → -0.5；congressional_trades.net_signal ±0.5（v1.86 啟用）
- **News lane**：sec_8k_filings 必看 + 30d window 觸發 ±0.5；FMP_SUPP_BUNDLE.ma_events 強訊號（v1.86 啟用）
- 決策 B 採「只調 score、不強制 verdict」立場 — Piotroski weak 不強制 PASS，避免 LLM 收尾權被剝奪

### Why
- FMP_強化分析.md Section 6.5「Phase 2 Burry Lane 新增規則」+ 4 個 lane 接入 supplementary bundle。前述 v1.78-v1.84 都是資料層；本 bump 把資料 wired 進 protocol prompt，讓 4 個 subagent 真的看得到並按確定性規則計分。決策 B 規定不強制 verdict（避免機械化過頭）

### Out of Scope
- congressional_trades / ma_events 的 fmp_supplementary 實作（v1.86.0 處理；目前 protocol 規則已寫好等資料）

---

## [1.84.0] — 2026-05-02
### Changed — `skills/us-stock-analysis/scripts/analyze.py` bundle-first
- 新增 `_load_bundle(ticker)` 從 `skills/earnings-analyst/cache/<TICKER>_<DATE>.json` 讀最新 bundle；新增 `_derive_from_bundle(bundle)` 把 EARNINGS_ANALYST_BUNDLE TTM ratios + key-metrics 對映到 valuation/balance_sheet/margins_cash/earnings_calendar 的同樣 schema
- `analyze()` 改 bundle-first：bundle 命中時 FMP-sourced TTM canonical 值 override yfinance 同名欄位（pe_ratio / pb_ratio / ev_ebitda / debt_to_equity / margins / fcf_yield / next_earnings_date）；缺值仍 fallback yfinance
- output `data_source` 標 "bundle+yfinance"，`data_quality.bundle_used` + `bundle_meta` 追蹤源頭
- 加 `--no-bundle` flag 維持 skill 獨立 yfinance-only mode 可用
- **AAPL 對比**：bundle path P/E 33.91（FMP TTM canonical）vs yfinance 35.71；EV/EBITDA 25.60 vs 24.98；next_earnings 2026-07-31 vs unknown

### Why
- FMP_強化分析.md Section 1.3 + 5 P2 工作項。Bundle 已存在則重打 yfinance 是浪費 + 數值不一致（yfinance trailing fields lag、FMP TTM 為 canonical）。決策 F：bundle-first 但保 fallback / 獨立可用，無 protocol 流程破壞

### Out of Scope
- yfinance 完全淘汰（growth_yoy / EPS forward / analyst recommendation 仍 yfinance only，bundle 沒這些）

---

## [1.83.0] — 2026-05-02
### Added — News lane 8-K material event filings
- **`skills/market-news-analyst/scripts/fetch.py`**: 新 `_fmp_sec_8k_filings` 用 `/stable/sec-filings-search/symbol?from=...&to=...` 客端 filter formType=8-K（注：`/stable/sec-filings-8k` 端點不支 symbol filter；`sec-filings-search/symbol` 才正確）。返回 30 日內 AAPL 2 件 8-K
- output 新增 `sec_8k_filings` array + `data_quality.fmp_sec_8k_count`。fmp_calls 9 → 9（+1）

### Why
- FMP_強化分析.md Section 3.3 + 5 P2 工作項。`sec-filings-financials` 只回 10-K/Q 財報，重大事件（M&A、CEO 更替、訴訟、重組）走 8-K，原 News lane 漏這層

### Out of Scope
- 8-K item code 解析（事件分類後續可補；現階段 News lane subagent 由 LLM 從 finalLink URL 推測即可）

---

## [1.82.0] — 2026-05-02
### Added — market-news-analyst FMP news/stock + press-releases (PRIMARY headlines source)
- **`skills/market-news-analyst/scripts/fetch.py`**: 新增 `_fmp_news_stock` (`/stable/news/stock?limit=30`) + `_fmp_press_releases` (`/stable/news/press-releases?limit=10`)。fetch() 把這兩個放在 4-way dedup 鏈條最前（FMP 為 PRIMARY, finviz/yfinance/Finnhub fallback）。output `data_quality.headlines_primary_source` 表明來源
- **AAPL 168h test**：FMP=30 + press=2 + finviz=100 + yf=10 + finnhub=25 → dedup 149 headlines；fmp_calls 從 6 → 8
- **`_finviz_analyst_actions:97-104` pre-existing TypeError fix**：`replace(tzinfo=_UTC)` 對 numpy datetime64 失敗，改 `isinstance(d, datetime)` gate；前段 `tz_localize` 嘗試包進 try/except 避免破壞流程

### Why
- FMP_強化分析.md Section 1.2 + 5 P2 工作項。決策 D 採 4 源 dedup（FMP primary + finviz/yf/finnhub fallback）。FMP REST 比 finviz HTML 穩定，新增 press-releases 為高訊號補充（公司官方發布）

### Out of Scope
- FMP `sentiment` 欄位（實測 response 無此欄位，報告 1.2 描述有誤；後續若 FMP 加上再接）
- News lane prompt 規則調整（headline source 的權重等待 v1.84 後 protocol 整合）

---

## [1.81.0] — 2026-05-02
### Added — `skills/theme-detector/scripts/fmp_industry_perf_client.py` (FMP industry perf cross-check)
- 新檔 `fmp_industry_perf_client.py` (~150 行) 從 `/stable/industry-performance-snapshot` 抓最近 5 個營業日的 industry-level `averageChange`，建立 per-industry `perf_1d_pct` + `perf_rolling_pct`（arithmetic sum）+ `_per_day_avg` 序列。每天 cache 6h 至 `skills/theme-detector/cache/fmp_industry/snapshot_<DATE>.json`
- **不**替換 `finviz_performance_client.py`（決策 C：cross-check 不替換）。FMP 為新欄位，scorer 後續可選擇性使用做 sanity check（finviz HTML breakage 偵測 / 雙來源 cross-validate）
- 128 industries × 5 days probe 確認 OK，CLI 可 `python3 fmp_industry_perf_client.py --days-back 5 --head 10` 查 top/bottom

### Why
- FMP_強化分析.md Section 1.1 + 5 P1 工作項。finviz HTML 爬取偶發 breakage，FMP REST 為更穩定的 cross-check 來源。決策 C 採 option-3：FMP 為新欄位、不破壞既有 finviz 流程，theme-detector scorer 與下游報告可選擇性消費

### Out of Scope
- theme-detector `scorer.py` 整合（保持 finviz 為主，FMP 純 cross-check）— 後續 minor bump 或選用時再接入
- `historical-industry-performance` endpoint：實測 200 但 count=0，跳過

---

## [1.80.0] — 2026-05-02
### Added — FMP_SUPP_BUNDLE.institutional (法人 QoQ 籌碼變化)
- **`skills/_shared/fmp_supplementary.py`** `_fetch_institutional`：從 `/stable/institutional-ownership/symbol-positions-summary` 抓最近一季完整 13F filing。從 `q-1` 開始往前 walk back（避免 mid-filing-window partial data，sanity gate: 跳過 investorsHolding 或 ownershipPercent 不到上季 50% 的 partial quarter）
- 派生 `accumulation_signal` ∈ {accumulating > +1%, distributing < -1%, neutral} from `ownershipPercentChange`
- 14 raw fields 攜帶（investors_holding, num_13f_shares, total_invested_usd, new_positions, increased_positions, reduced_positions, put_call_ratio + 對應 last/change 欄位）
- **AAPL probe**：2025 Q4 snapshot — investorsHolding=6288, ownership_percent=64.60%, QoQ change +3.03% → accumulation_signal=accumulating

### Why
- FMP_強化分析.md Section 4.3 P2 工作項。Sentiment lane 缺機構籌碼面 QoQ 訊號（13F summary 已含 last/change 欄位省 2 次抓取）；mid-filing-window 防呆是必要的，否則 Q1 2026 看到 3.32% 會誤判 distributing

### Out of Scope
- Sentiment lane prompt 接入規則（v1.81.0 protocol 改動處理）

---

## [1.79.0] — 2026-05-02
### Added — FMP_SUPP_BUNDLE.insider_summary + sentiment skill bundle-first
- **`skills/_shared/fmp_supplementary.py`**: 新增 `_fetch_insider_summary(ticker)`，從 `/stable/insider-trading/statistics?limit=4` 抓最近 4 季資料；派生 `latest_trend` ∈ {accumulating ≥ 1.0, distributing < 0.5, neutral 0.5-1.0}
- **`skills/market-sentiment-analyzer/scripts/sentiment.py`**: `_fetch_ticker_signals` 改為 bundle-first。先嘗試從 `FMP_SUPP_BUNDLE.insider_summary.quarters` 讀，命中標 `insider_stats_source: "FMP_SUPP_BUNDLE"`；miss 才走原來 FMP direct 抓（標 `"FMP direct"`），維持 skill 獨立可用性
- **AAPL probe 確認**：4 quarters, latest_trend=distributing（acq/dis ratio = 0.18），bundle-first source 正確標示

### Why
- FMP_強化分析.md Section 3.5 + 5「P1 — insider_stats[] 移入 Phase 1 FMP_SUPP_BUNDLE」。原架構 insider 只在 Sentiment lane skill 內部抓，Burry inline lane（Phase 2 末段）讀不到。改放共用 bundle 後 Burry 也可消費；同時 Sentiment skill 不再每次重打 FMP（同 ticker 同日 0 額外 call）
- bundle-first + skill self-fetch fallback 雙路：(a) protocol 整合場景走 bundle 省 call；(b) skill 獨立執行（user 直接跑）仍可用

### Out of Scope
- Burry lane prompt 接入 insider_summary（v1.81.0 burry 規則化處理）

---

## [1.78.0] — 2026-05-02
### Added — `skills/_shared/fmp_supplementary.py` (FMP_SUPP_BUNDLE V1.0) + protocol Phase 1 整合
- **新檔 `skills/_shared/fmp_supplementary.py`** (~180 行): `get_supplementary_bundle(ticker)` 24h cache @ `skills/_shared/fmp_supp_cache/<TICKER>_<DATE>_supp.json`，FMP-only，與 dual_fetch / FinnhubClient 物理隔離
- **首批 sections 填入**: `quality_scores`（Altman Z + Piotroski F + 派生 zone/strength + 7 個 raw 欄位）、`owner_earnings`（latest quarter + qoq_growth + maintenance/growth capex split）。其他 sections（insider_summary / institutional / congressional / ma_events）保留 `{}` 待後續 bump 填
- **`investment/investment_protocol_v4_8.md`**: Phase 1 末段新增「Phase 1 資料層（V4.11 新增）— FMP Supplementary Bundle」節（~30 行）。注入規則：Fundamentals + Burry 收 quality_scores + owner_earnings；Sentiment + News 收對應 sections；Technical 不收
- **AAPL probe 確認**：altmanZScore=11.64 (safe zone), piotroskiScore=9 (strong), ownersEarnings=$28.86B, qoq_growth=-46.7%

### Why
- FMP_強化分析.md Section 6 提案。Burry rubric 缺確定性數值（Altman Z / Piotroski F），目前依賴 LLM 對 debt/asset 比值的定性判斷。將高價值 FMP 欄位集中放 FMP-only bundle，4 lane 共用，避免每個 lane skill 各自重打 FMP（同 ticker 同日 0 額外 call）。物理隔離契約防止 cross-lane anchoring 與 Finnhub/FMP 混淆

### Out of Scope
- Burry rubric 規則化（v1.81.0 處理）
- Sentiment skill bundle-first（v1.79.0 處理）
- 其他 FMP_SUPP sections 填值（後續 bumps）

---

## [1.77.0] — 2026-05-02
### Added — `investment/scripts/fmp_endpoint_probe.py` + `investment/fmp_probe_2026-05-02.json`
- 18 endpoint probe vs AAPL，17/18 PASS（含 ESG / COT / annual analyst estimates 等先前疑慮 paid blocker）。Result file `investment/fmp_probe_<DATE>.json` 後續 v1.78+ bumps 讀取以 gate P3/P4 features
- **PASS endpoints**: financial-scores, owner-earnings, insider-trading/statistics, institutional-ownership/symbol-positions-summary, senate-trades, house-trades, mergers-acquisitions-latest, sec-filings-8k, news/stock, news/press-releases, industry-performance-snapshot, sector-performance-snapshot, historical-chart/1hour, esg-ratings, esg-disclosures, analyst-estimates(annual), commitment-of-traders-analysis
- **FAIL**: historical-industry-performance（200 但 count=0；需特定 industry 名稱 + 日期範圍）→ 後續用 snapshot 取代

### Why
- FMP_強化分析.md Section 4 + 5 列出多項「需驗證是否免費」的 endpoint。實作前先做一輪可重現 probe，免得 v1.78+ bumps 寫進 code 才發現 402 要 rollback。Probe 採只記欄位名稱 / count（不寫 secret）。

### Out of Scope
- historical-industry-performance 的正確 industry 名稱字典（snapshot 已足夠 cross-check 用）
- 任何 endpoint 的下游接入（v1.78+ 處理）

---

## [1.76.0] — 2026-05-02
### Added — earnings-analyst slim_ttm_keymetrics +3 capital efficiency fields
- **`skills/earnings-analyst/scripts/fetch.py:105` slim_ttm_keymetrics**: keep list +3 → `returnOnInvestedCapitalTTM` (ROIC), `returnOnCapitalEmployedTTM` (ROCE), `returnOnTangibleAssetsTTM` (ROTA)。從 `/stable/key-metrics-ttm` 直接拿。AAPL probe 確認三欄位回傳值（ROIC=0.513 / ROCE=0.623 / ROTA=0.350）

### Why
- FMP_強化分析.md Section 3.1 + 4.1 P0 工作項：Burry rubric 缺資本效率指標。`evToEBITTTM` 在 FMP stable 不存在(實測 None)，改採 ROIC + ROCE + ROTA 三個資本回報率欄位。Slim 列加 3 字段，bundle 體積增 ~60 bytes，下游 Fundamentals + Burry lane 立即可用，無 schema 破壞。

### Out of Scope
- evToEBIT 直接欄位（FMP stable 未提供，後續可用 EV / income 推算）
- bundle 消費端 protocol prompt 改動（v1.81.0 Burry 規則化時一併處理）

---

## [1.75.0] — 2026-05-02
### Added — 決策中心 (decisions.html) Invest Cmdbar + 視覺布局重組
- **`Dashboard/decisions.html`**: header 下方新增 `.ea-cmdbar` (terminal-style quick-launch) — 含 prompt `›` + ticker input + 全局 RISK hint + 分析 button + recent chips 條;summary 4 stats 加 `.dc-summary-tile` hover lift + `.dc-summary-num` (32px JetBrains Mono),avg conf/RR 兩格加 blue/violet 4px left-border (彩色一致);整體 grid 從 `space-y-8` 改為 `space-y-6` 為 cmdbar 騰出視覺空間
- **`Dashboard/page-decisions.js`**: 新 `dcRunInvest(ticker)` (POST `/api/protocol-queue` `{name:'invest', ticker, risk_tolerance: UI.riskTolerance}`) + `dcGetRecent/dcSetRecent/dcPushRecent/dcRenderRecent` localStorage 5-slot recent chips (`dc_recent_invest_tickers`) + `dcRefreshRiskHint` 跟 sidebar `#risk-chip` 同步;wire input/Enter/btn/recent-click + window.focus 自動 refresh risk hint;`applyTranslations` 擴充 `decisions.cmdbar_*` keys;`buildCard` 加 `.dc-card-hover` class
- **`Dashboard/style.css`**: `.ea-cmdbar*` 從 earnings.html L64-119 inline 提升為共用 css block (`Dashboard/style.css` 末尾 +90 行,earnings.html inline 保留無風險),decisions/earnings 兩頁共用;新增 `.dc-summary-tile` / `.dc-summary-num` / `.dc-card-hover` 視覺 polish class
- **`Dashboard/i18n.js`**: 新增 `decisions: {cmdbar_run / cmdbar_placeholder / cmdbar_recent_label / cmdbar_risk_hint / cmdbar_queued / cmdbar_duplicate / cmdbar_empty}` zh+en 雙語 7 keys (parity 驗證 OK)
- **`Dashboard/utils.js`**: `VERSION = 'V1.75.0'`

### Why
- 用戶比對 earnings.html 的 cmdbar 體驗(輸入 ticker → 快速跑分析),要求 decisions 同款。決策中心是 invest protocol 的天然 surface(深度委員會分析 → 對應決策追蹤),但既有頁面只能透過個股卡片右上 refresh icon 觸發,沒有 quick-launch entry,要憑空跑新 ticker 必須去 index.html 或 radar.html
- Risk tolerance 已是全局狀態(`UI.riskTolerance` getter 讀 `localStorage.dash_risk_tolerance`,sidebar `#risk-chip` 可切換),cmdbar 只顯示當前值不重複暴露切換 UI,避免 multi-source-of-truth
- `.ea-cmdbar*` 提升為共用 css 是因為 visually identical,複製整段到 decisions inline 會造成兩處 drift;earnings 的 inline 保留作 graceful fallback (即使 style.css load 失敗 earnings 仍能顯示)
- 視覺 polish 控制在 hover/colour 微調,不動 modal / positions table / 卡片內部欄位 layout / bridge.py — 純前端視覺改動,沒有 schema / API 風險

### Out of Scope
- 持倉 modal / 平倉 modal / 持倉 table 結構
- `bridge.py extract_audit_history` 邏輯
- 卡片內部 layout (target/stop/risk-reward 等保持原樣)
- `?ticker=X` deep-link 自動鑽取 (known UX debt)
- Sidebar `#risk-chip` 結構

---

## [1.74.0] — 2026-05-01
### Added — `skills/_shared/company_context.py` 共用 FMP 公司層 metadata cache
- **新檔 `skills/_shared/__init__.py`** + **`skills/_shared/company_context.py`**(~250 行):提供 `SECTOR_UNIVERSE` / `TICKER_TO_SECTOR` / `SECTOR_TOP_5` 三個常數作為 sector 名單單一真相源,以及 `get_profile/get_peers/get_market_cap_history/get_employee_history/get_profiles_bulk` 五個 24h-TTL cache 函式。Cache 路徑 `skills/_shared/cache/<TICKER>_<KIND>.json`。402 paid blocker 回 None 不 abort。

### Changed — sector 三個 fetch script 改 import 共用模組（去重複 ~75 行）
- **`sector/scripts/fetch_earnings_pulse.py`**: 刪本檔 `SECTOR_UNIVERSE` (~24 行) + `TICKER_TO_SECTOR` reverse build (~4 行),改 `from skills._shared.company_context import SECTOR_UNIVERSE, TICKER_TO_SECTOR`
- **`sector/scripts/fetch_smart_money.py`**: 同上 pattern
- **`sector/scripts/fetch_sector_news.py`**: 刪本檔 `SECTOR_TOP_5` (~14 行),改 import shared `SECTOR_TOP_5`(保留 hand-tuned Communication 差異:GOOGL/META/NFLX/DIS/TMUS,**不**用 SECTOR_UNIVERSE[:5])

### Changed — `skills/earnings-analyst/scripts/fetch.py` profile 走共用 cache
- 刪 `_fmp_get("/stable/profile", ...)` 直接呼叫,改 `from skills._shared.company_context import get_profile as _shared_get_profile`,在 `fetch_bundle()` 起頭單行 `profile = _shared_get_profile(ticker) or {}`
- 與 sector scripts 共用 24h cache → 同 ticker 一天內第二次跑(產業掃描 + 分析 [TICKER])0 重複 FMP call

### Changed — `investment/investment_protocol_v4_8.md` Phase 1 新增 PEER_BUNDLE,Fundamentals + Burry lane 加 relative valuation rubric
- **Phase 1 末段**新增 sub-section「Phase 1 資料層（V4.10 新增）— Peer Comparison Bundle」(~50 行):PM MUST 呼叫 `skills/_shared/company_context.get_peers(TICKER)[:5]` + `get_profile(p)`,計算 `peer_pe_median / peer_market_cap_median / peer_beta_median`,注入 PEER_BUNDLE 到 Fundamentals + Burry lane prompt(Sentiment/News/Technical 不得包含,避免 cross-lane anchoring)
- **Fundamentals lane rubric** 新增 PEER_BUNDLE 使用規則:`peRatio` vs `peer_pe_median` 差 > 30% → score ±1,> 50% → ±2;論述格式從「貴」改寫為「P/E 35× vs peer median 22× = +59% premium」
- **Burry inline** 新增 PEER_BUNDLE 額外校驗:EV/EBIT > peer median × 1.5 → 在 `burry_voice` 加 narrative 註記,**禁止**因此調整 burry_score(保 deterministic)
- 失敗策略:`len(peers) < 3` → `PEER_BUNDLE.status = insufficient_peers`,fallback 既有 sector median rubric;**不**中止 protocol

### Changed — `CLAUDE.md` 同步 protocol triggers + 新增 Shared Modules section
- `分析 [TICKER]` row 從 V4.8.1 → V4.10(含 PEER_BUNDLE 註記)
- Ad-hoc 區加 `python3 skills/_shared/company_context.py <TICKER> --peers` smoke test 指令
- 新增 `## Shared Modules` section 說明 `_shared/company_context` 是 mega-cap 名單修改唯一入口

### Why
- Bucket A1 + A2 + A3 來自 `/Users/kavi/.claude/plans/3-fluffy-moonbeam.md` 分析:9 個 FMP company API 方法中只 2 個高 ROI(`stock_peers` + `profile` 共用 cache)。本次一次落地全部 Bucket A,削掉 sector 3 份重複名單,給 protocol lane 加量化 peer comparison
- LLM 判斷增益:Burry / Bear lane 從「貴」變成「P/E 35× vs peer median 22× = +59% premium」,可 reproducible
- API 成本:同 ticker 24h 內第二次呼叫 0 FMP call(原本 earnings-analyst + Phase 1 PEER_BUNDLE 會打兩次 /profile)

---

## [1.73.7] — 2026-05-01
### Fixed — sector Phase 3 Step 1/2/3 缺 explicit bash block,agent guess flag 浪費 retry
- **`sector/phase_1-2-3.md`**: Phase 3 執行順序 block 後新增 Step 1 (`market-sentiment-analyzer/scripts/sentiment.py --json`) / Step 2 (`economic-calendar-fetcher/scripts/get_economic_calendar.py --from --to --format json`) / Step 3 (`earnings-calendar/scripts/fetch_earnings_fmp.py {SCAN_DATE} {SCAN_DATE+7d}` 位置參數) 三個 bash 範例,明示 argparse vs 位置參數差異

### Why
- scan log `sector_20260501_213508.log` 顯示 agent 對 Step 2/3 連續 retry `--json --days 7` → `--from --to --format json` → 讀 `--help` → 才用對的 positional/argparse 介面,每次浪費 ~5-15s + tokens
- Step 3b/3c/3d 早就有 explicit `python3 ...` 範例所以 agent 不 guess,Step 1/2/3 漏掉
- 加範例後 future protocol run 直接 copy-paste 不 hallucinate flag

---

## [1.73.6] — 2026-05-01
### Changed — sector 頁面去重: 移除 Today's Verdict card
- **`Dashboard/sector.html`**: 移除 `#today-verdict-card` 完整 card HTML; 改為單行 hidden stub + tv-* 子元素 hidden stubs (供 `Components.renderTodayVerdict` / page-sector.js `set()` 呼叫不報錯); `Components.renderTodayVerdict` 已有 `if (!card || !market) return` 保護

---

## [1.73.5] — 2026-05-01
### Changed — sector 頁面去重: 移除廣度/三訊號面板
- **`Dashboard/sector.html`**: 移除 Three-Signal Synthesis col (COL 1); 底部格線改 `lg:grid-cols-3` → `lg:grid-cols-2`; binary-alert/warning-flags stubs 縮短為單行
- **`Dashboard/page-sector.js`**: 移除 `three-signal-title` i18n set 呼叫 (`renderThreeSignal` 本身已有 `if (!container) return` 保護)

---

## [1.73.4] — 2026-05-01
### Changed — 反向去重:把 sector 的 8 gauges + binary-adaptive + warning flags 整批搬到 dashboard,sector 留乾淨 sector-only 內容
- **`Dashboard/style.css`**(+170 行):從 sector.html `<style>` block 升級 `.sector-status-row` / `.sector-gauge*` / `.sector-gauge-seg*` / `.sector-gauge-unit` / `.binary-adaptive*` / `.risk-flag-card.risk-flag-sector` 為共用樣式,index 與 sector 共用
- **`Dashboard/index.html`**:
  - 移除 Today's Verdict 卡內 `<div id="three-signal-mini">` 4-bar render 點(stub 隱藏保留以免 script.js 報錯)
  - 加新 `<div id="binary-alert-section">` 用 `.binary-adaptive` 結構(取代舊的 `.binary-alert px-4 py-3` 簡單 list)
  - `<section id="risk-overview">` 改成 `.sector-status-row` 容器,內含 8 個 pill div(`pill-breadth/ftd/marketop/fg/regime/cycle/exposure/vix`)+ warning-flags-row
- **`Dashboard/script.js`**:
  - 加 `_gaugeColor()` / `_gaugeHTML()` / `_gaugeSegmentedHTML()` helper(從 page-sector.js port)
  - 加 `renderSectorStatusStrip(data)`:渲染 4 numeric gauges(Breadth/FTD/Market Top amber/F&G amber-bell)+ 4 categorical/scaled gauges(Regime 4-seg pie / Cycle 4-seg pie / Exposure range gauge / VIX max=40)+ setAttrs for signal-tip engine
  - 重寫 `renderBinaryAlertIndex()` 為 adaptive density(≤2 inline / 3-5 grid / ≥6 collapsible 含 `<details>` toggle)
  - `renderWarningFlagsIndex()` 加 `REDUNDANT_FLAGS_DASH` 過濾(Below_200MA / Critical_Zone / Weakening_Zone — Breadth gauge 已表達)+ `FLAG_TIP_KEY_DASH` 路由到 `#signal-tip-tooltip` 共用引擎(same as sector page V1.72.8)
  - `renderThreeSignalMini` 不再從 main render path 呼叫(stub 函式留著向下相容)
  - `updateRiskOverviewVisibility()` 簡化:gauges 永遠可見,不再 gate
- **`Dashboard/sector.html`**:
  - 移除 `<div class="sector-status-row">` 容器(8 pill divs + warning-flags-row)
  - 移除 `<div id="binary-alert-section">` 完整 markup(只留 stub `<div id="binary-alert-section" class="hidden">`)
  - 移除 inline `<style>` block 中所有 `.sector-status-row` / `.sector-gauge*` / `.sector-chip*` / `.binary-adaptive*` 樣式(~200 行,改用 shared style.css)
- **`Dashboard/page-sector.js`**:
  - 刪除 `_gaugeColor` / `_gaugeHTML` / `_gaugeSegmentedHTML` helpers(~80 行)
  - 刪除 `renderStatusStrip()` 完整 body(~220 行)、`renderBinaryAlert()` 完整 body(~70 行)
  - 兩個 function 改為 no-op stub,既有 `loadSectorData()` 呼叫不報錯
- **`Dashboard/utils.js`**:`V1.73.4`
### Why
- 用戶比對 image 2(sector hero)vs image 3(dashboard DEFENSIVE 卡 4-bar):核心市場指標(Breadth/FTD/Market Top + 廣度等 warning flags)在兩頁看到 2 次 = 認知冗餘
- 反向決策:dashboard 是「市場層級 hero」自然位置,sector 是「sector-specific 深潛」,把所有市場指標集中在 dashboard,sector 頁聚焦 verdict + matrix + 三 col
- Dashboard 4-bar 是舊版視覺(progress bars no ceiling),取代為 8-gauge circular pies — 跟 sector V1.72.x 系列建立的 visual language 統一(verdict-color discipline + amber palette for warning indicators)

---

## [1.73.3] — 2026-05-01
### Changed — Sector status row 去除跟 index.html 重複的 3 個指標
- **`Dashboard/sector.html`**:status row 移除 `<div id="pill-breadth">` / `<div id="pill-ftd">` / `<div id="pill-marketop">` 3 個 wrapper(留下 5 個 sector-specific:F&G / Regime / Cycle / Exposure / VIX + warning-flags-row)
- **`Dashboard/page-sector.js`** `renderStatusStrip()`:
  - 刪除 Breadth / FTD / Market Top 的 `_gaugeHTML` render block(~30 行)
  - `setAttrs` 對應 3 個 pill 的呼叫一併移除
- **`Dashboard/utils.js`**:`V1.73.3`
### Why
- 用戶比對 index.html dashboard DEFENSIVE 卡的 4-bar 區塊(市場廣度 33.1 / FTD 訊號 100 / 頂部風險 31.2 / 綜合曝險 50%)跟 sector.html 前 3 個 circular gauge 完全重複
- 跨頁面看到同一份指標 2 次 = 認知冗餘;dashboard 已是市場層級總覽的合理位置,sector 頁聚焦在 sector-specific context(情緒、體制、週期、本身曝險、波動)
- Sector matrix / Today's Verdict / Three-Signal Synthesis 等下方區塊不動

---

## [1.73.2] — 2026-05-01
### Fixed — Protocol 完成後外面財報卡片不自動刷新
- **`Dashboard/utils.js`** (`pollProtocolStateMonitor`, line ~603): 偵測到 `status === 'done'` 時加 `setTimeout(() => window.DataStore?.refresh(), 3000)`
- **Root cause**: `run_bridge()` 在 protocol 完成後於 background thread 更新 `data.json`，但 DataStore TTL=60s — 前端最多需等 60 秒才能看到新資料。加入 3s 延遲後強制 refresh，讓外面卡片立即反映最新 score/verdict。3s 延遲目的是讓 bridge.py 有時間寫完 data.json。

---

## [1.73.1] — 2026-05-01
### Fixed — earnings-detail empty-state 重跑按鈕「Failed: missing ticker」
- **`Dashboard/page-earnings-detail.js`** (`renderEmptyState` 重跑 button onclick): POST `/api/protocol-queue` 的 payload 從巢狀 `{name:'earnings', params:{ticker}}` 改為扁平 `{name:'earnings', ticker}`
### Why
- `dashboard_server.py:1576` 處理 `/api/protocol-queue` POST 時用 `params = {k:v for k,v in body.items() if k != "name"}`,把所有 top-level key 當作 params。送巢狀 `{params:{ticker:X}}` 會導致 server 收到 `params={"params":{"ticker":X}}`,`params.get("ticker")=None` → `enqueue_protocol` 回 "missing ticker"
- `page-earnings.js` 既有的「重跑」按鈕用扁平 `{name:'earnings', ticker}` 是對的;新頁複製時誤包進巢狀 `params{}`

---

## [1.73.0] — 2026-05-01
### Added — 個股財報 Infographic 風格頁面（取代「看報告」markdown modal）
- **`Dashboard/earnings-detail.html`** (NEW): standalone page `?ticker=X`，公司 hero + 4 主指標 actual vs estimated ✓✗ + 6-segment grid + 地理分部（≥3 regions 才渲）+ 資本回報 card + CEO blockquote + Key Highlights 雙欄 + 重點總結 list + 詳細 markdown `<details>` collapse + empty state
- **`Dashboard/page-earnings-detail.js`** (NEW, ~340 行): page boot + 8 render 函式 (`renderHero/MetricCards/Segments/Geographic/CapitalReturn/Quote/Highlights/Summary`) + lazy markdown collapse + empty-state re-run button (POST `/api/protocol-queue`) + 全程 `UI.escapeHTML`
- **`skills/earnings-analyst/scripts/validate_infographic.py`** (NEW, ~80 行): schema gate（`schema_kind=='infographic'`、`SUMMARY_MIN=2`、`HIGHLIGHT_MIN=3`、`ceo_quote` gated on `transcript_used==true`）

### Changed — earnings-analyst skill 擴充至 6-step protocol
- **`skills/earnings-analyst/scripts/fetch.py`**: 加 5 個 `/stable/` 免費 endpoint（`earnings` / `revenue-product-segmentation` / `revenue-geographic-segmentation` / `dividends` / `earning-call-transcript`）+ 4 個 slim helpers + `_resolve_transcript_q()` 4-tier fiscal-Q resolver（先用 cache 內 fiscalYear+period，再退化 calendar Q，再 Q-1 walk back）→ bundle 新增 `earnings_surprises` / `segments.product_fy` / `segments.geographic_fy` / `dividends_history` / `transcript`
- **`skills/earnings-analyst/SKILL.md`**: 4 steps → **6 steps**，第 4 步 NEW LLM narrate phase（Claude Code in-conversation 讀 cache + ~50K 字 transcript content，Write `<TICKER>_<DATE>.infographic.json`）
- **`skills/earnings-analyst/schema.md`**: 追加「Cache 檔 V1.73 新增欄位」+「Infographic Cache (V1.0)」section（含完整 JSON 範例 + fallback 行為文件化）
- **`dashboard_server.py`**: 新 `/api/earnings-infographic/<TICKER>` route 回傳 merged `{infographic, cache subset, report_path}`；`PROTOCOL_PROMPTS["earnings"]` 4 steps → 6 steps（加 narrate phase prompt 細節）；既有 `/api/earnings-cache/` glob 過濾 `.infographic.json` sibling
- **`bridge.py`**: `extract_earnings_analyses()` glob 排除 `.infographic.json`；每筆加 `has_infographic: bool` 欄位（Dashboard 卡片可選擇性顯示「Infographic ready」標記）
- **`Dashboard/earnings.html` 卡片按鈕**: 「看報告」(markdown modal) 改為「📊 Infographic」(navigate 到 detail page)；markdown 退為 detail page 內 `<details>` lazy load
- **`Dashboard/page-earnings.js`**: action handler `view` → `infographic`，handler 改 `window.location.href = 'earnings-detail.html?ticker=X'`
- **`Dashboard/style.css`**: 新增 `.ed-*` namespace ~180 行（hero / metric grid / segment grid / capital card / quote card / highlights & summary lists / detail collapse / empty state）全用 CSS 變數 light/dark adaptive
- **`Dashboard/i18n.js`**: 追加 `earnings_detail.*` zh/en 雙語 29 個 keys (section labels / metric labels / beat-miss / FY fallback / no dividend / capital labels / loading / error)

### Why
- User 看到 AAPL Q2 風格 infographic（公司 hero + 4 主指標 + segment + 資本回報 + CEO + highlights + summary），希望 `財報 [TICKER]` 改這個樣式
- 實測 5 個 `/stable/` 免費 endpoint 全可用（含 transcript ~48-53K 字）；唯一缺口「季度分部數字」無法從 paid endpoint 取得（402），改由 LLM 從 transcript 抽 CFO 段落獲得（infographic 上的 569.9/309.8 億等數字本來就是這樣來的）
- 新 schema 採 **兩個 cache 檔並存**（`<TICKER>_<DATE>.json` V1.0 不動 + `<TICKER>_<DATE>.infographic.json` V1.0 narrative 層），完全 backward compatible，舊 cache 仍能用，新頁面 404 時走 empty state
- 端到端驗證通過（AAPL Q2 FY26）：`fetch → analyze → validate → narrate(LLM) → render → validate_infographic` 6 phase 全 rc=0；`Dashboard/data.json` `earnings_analyses[ticker=AAPL].has_infographic=true`；其他 3 ticker (GOOGL/MSFT/NVDA) 須手動重跑 `財報 X` 才會生成

### Out of Scope
- Quarterly product/geographic segmentation 付費 endpoint（FMP `period=quarter` 全 402）
- 其他 dashboard 頁面視覺
- 其他 protocol triggers
- LLM provider 替換（沿用 Claude Code in-conversation）
- 多季 history 比較頁（只渲最新一季）

---

## [1.72.9] — 2026-05-01
### Added — Browser tab favicon:AUGUR diamond logo
- **`Dashboard/favicon.svg`**(新檔):24x24 SVG inline gradient(emerald → lime → amber)+ 旋轉鑽石 + 羅盤十字 + 占卜師之眼(同心圓 emerald 瞳 + 琥珀眼神反光)— 跟 sidebar logo mark 視覺一致
- **8 個 HTML 頁面**(`calendar.html` / `decisions.html` / `earnings.html` / `index.html` / `momentum.html` / `news.html` / `radar.html` / `sector.html`):`<title>` 後注入 `<link rel="icon" type="image/svg+xml" href="favicon.svg">`
- **`Dashboard/utils.js`** VERSION:`V1.72.9`
### Why
- 用戶反映 browser tab 顯示預設 "L"(本機 host favicon fallback),要換成 AUGUR diamond logo
- SVG favicon 跨主流瀏覽器(Chrome/Firefox/Safari/Edge)都支援,且向量縮放清晰;沒有 png/ico 多尺寸需求

---

## [1.72.8] — 2026-05-01
### Fixed — Sector warning flags:tooltip 風格統一 + 取消 `?` 游標
- **`Dashboard/utils.js`** SIGNAL_TIPS engine:
  - 新增 3 個 warning flag 條目:`bearish_signal` / `low_historical_percentile` / `divergence`(zh+en 雙語 title + desc + hint,`stages: []`)
  - 新增 `_flagMetricLive(emoji)` factory 產生 LIVE_BUILDERS for 3 個 key,讀 `data-flag-metric` 渲染 single-line 警示 banner(🚨 / 📊 / ↘)
- **`Dashboard/page-sector.js`** `renderStatusStrip()` warning-flags 渲染:
  - 加 `FLAG_TIP_KEY` 映射:`Bearish_Signal_Active → bearish_signal`、`Low_Historical_Percentile → low_historical_percentile`、`Early_Warning_Divergence → divergence`
  - 從 `data-tip-key="warning_flag"`(舊 #pill-tooltip,只在 index.html script.js 有引擎)→ `data-signal-tip="<key>"`(共用 #signal-tip-tooltip engine,所有頁面通用)
  - 加 `risk-flag-sector` class 區隔 sector 頁專屬樣式
- **`Dashboard/sector.html`** `<style>`:加 `.risk-flag-card.risk-flag-sector { cursor: default; }` override 共用 `style.css:1877` 的 `cursor: help` — sector 頁不要 `?` 游標
- **`Dashboard/utils.js`** VERSION:`V1.72.8`
### Why
- 用戶反映 2 個 warning flag 顯示 `?` 游標、且 tooltip 風格跟同頁面其他 8 個 gauge 不一致(實際上 sector 頁根本沒有 #pill-tooltip 引擎,所以舊 tooltip 完全沒出來)
- 直接接到 #signal-tip-tooltip 共用引擎,跨 8 gauge + 3 warning flag 全部 hover tooltip 視覺一致(title + desc + live banner + hint)
- 提供完整指標說明而非只是 metric 數值,讓使用者一眼懂「為何這個 flag 重要」+「該怎麼應對」

---

## [1.72.7] — 2026-05-01
### Changed — Sector warning flags:升級 severity-tier card + 過濾跟 Breadth gauge 重複的 flag
- **`Dashboard/page-sector.js`** `renderStatusStrip()` warning-flags-row 區段重寫:
  - 從舊 `text-yellow-500 px-2 py-1 border` 簡單黃色 pill → **共用 `.risk-flag-card`** 樣式(已在 `style.css:1869` 定義)+ severity 分層 (`sev-critical` 紅 / `sev-warning` 橙 / `sev-caution` 黃)
  - **過濾重複 flag**:`REDUNDANT_FLAGS = {Below_200MA, Critical_Zone, Weakening_Zone}` — 這 3 個 flag 的訊息已被 Breadth circular gauge 完整表達(Below_200MA 是 ma_crossover gap = breadth 4 大 component 之一;Critical_Zone / Weakening_Zone 等於 Breadth score 的 zone label,gauge 顏色已染)
  - 保留獨立 flag:`Bearish_Signal_Active`(critical)、`Low_Historical_Percentile`(warning,顯 percentile %)、`Early_Warning_Divergence`(warning,顯 signal 名)
  - 偏好 `warning_flags_v2`(含 `severity` + `metric_value`)+ 舊 `string[]` schema fallback;按 severity rank 排序
  - 加 `_formatFlagMetric()` helper 對齊 index.html 同名函式行為
  - 加 `data-tip-key="warning_flag"` + `data-flag-*` 屬性,讓既有 `#pill-tooltip` 引擎可顯 severity-tinted tooltip(definition + metric chip + remediation hint)
- **`Dashboard/utils.js`**:`V1.72.7`
### Why
- 用戶反映 sector page 4 個 warning flag 跟 Breadth gauge 視覺/語意可能重複
- 分析後確認 3 個 flag(Below_200MA / Critical_Zone / Weakening_Zone)100% 重複(都是 breadth score 的衍生分量),保留只會稀釋訊號
- 改 risk-flag-card 樣式跟 index.html 對齊,跨頁面 design language 一致;severity 分層讓使用者一眼分辨「critical 必看 / warning 注意 / caution 知道就好」

---

## [1.72.6] — 2026-05-01
### Fixed — Sector status row:曝險上限換行 + 取消 `?` 游標
- **`Dashboard/sector.html`** `<style>`:
  - 加 `.sector-gauge-unit`(`display:block` + 9px JetBrains Mono + 0.55 opacity)讓單位 `%` 換行到第二行 + 字體變小
  - `.sector-gauge` / `.sector-chip` 的 `cursor: help` → `cursor: default`(取消滑鼠變成 `?` 樣)
- **`Dashboard/page-sector.js`** Exposure gauge:`displayStr` 從 `"40-60%"` 改 `"40-60<span class='sector-gauge-unit'>%</span>"`(`<span display:block>` 強制換行)
- **`Dashboard/utils.js`**:`V1.72.6`
### Why
- 「40-60%」5 字符在 64px 圓內擠到邊緣,蓋到 gauge 弧線;拆 2 行(數字大、單位小)更清楚
- `cursor: help` 在 macOS / Windows 都顯示成 `?` 樣式滑鼠 — 用戶覺得干擾視覺,改 default(普通箭頭),tooltip 仍然 hover 觸發

---

## [1.72.5] — 2026-05-01
### Fixed — Sector status row:Market Top tooltip + 移除冗餘 suffix
- **`Dashboard/sector.html`**:`#pill-marketop` 的 `data-signal-tip` 從 `"marketop"` → `"market_top"`(對齊 `utils.js:631` SIGNAL_TIPS engine 註冊的 key — 之前命名不一致 → 完全沒 tooltip 出現)
- **`Dashboard/page-sector.js`** `renderStatusStrip()`:移除 FTD / Market Top / F&G 的 `suffix` 參數(`Yellow (Ea...` zone 字串會 overflow + 重複下方 label;FTD state abbrev 雙引信也冗餘),所有 gauge 中央只顯數值,文字描述交給 hover tooltip
- **`Dashboard/utils.js`**:`V1.72.5`
### Why
- 用戶反映 Market Top hover 沒 tooltip(其他 7 個都有)— root cause 是 data-signal-tip key 字串不對,引擎 silent 跳過
- Suffix 文字被截斷顯「Yellow (Ea」誤解為「?」字符 + 視覺 noise(label 已在最下面),移除後 gauge 視覺更乾淨
- gauge 圓圈本身就是「上限 vs 目前」直覺指示,不需文字補強

---

## [1.72.4] — 2026-05-01
### Fixed — Sector status row:8 個指標**全部圓形化** + 修問號 + 琥珀色 palette
- **問題**:V1.72.2 後 4 個 categorical chip 仍是矩形,看不到圓形;Market Top / F&G 用綠紅切換不符警示性質;部分 pill 顯示「?」(em dash `—` 在 system font fallback 下渲染失敗)
- **`Dashboard/sector.html`** (`<style>` block):
  - 加 `.sector-gauge-seg` / `.sector-gauge-seg.active`(分段 pie,butt linecap + drop-shadow halo on active 段)
  - 加 `.sector-gauge-value-sm` / `-md` 字體大小 modifier(短文字用 sm 11px,中文字用 md 14px)
- **`Dashboard/page-sector.js`**:
  - `_gaugeColor` 加 2 種 polarity:`'amber'`(Market Top:純琥珀 light→mid→dark 三段,#fbbf24/#f59e0b/#d97706)+ `'amber-bell'`(F&G:兩端 #d97706 / 偏 #f59e0b / 中性 #fbbf24)
  - `_gaugeHTML` 加 `max` 參數(支援 VIX 0-40 scale)+ `displaySize` 參數(sm/md/lg);**修 fallback 字符** `—`(U+2014 em dash 字體缺字會渲染成 ?)→ `--`(雙連字符,universal)
  - 新增 `_gaugeSegmentedHTML({segments, activeIndex, label, valueDisplay, color, displaySize})`:N 段 SVG circle 用 `stroke-dasharray` + `stroke-dashoffset` 切割成等分扇形,active 段染 verdict 色 + drop-shadow halo,inactive 灰色
  - **Regime** 改 4-segment pie(BULL / SIDEWAYS / VOLATILE / BEAR;RISK_ON→BULL、RISK_OFF→BEAR 映射),active 段顯該 regime 色
  - **Cycle** 改 4-segment pie(Early / Mid / Late / Recession,色階 emerald → lime → amber → red 表現週期推進)
  - **Exposure** 改 circular gauge — 解析 `"60-75%"` 取 mid → 0-100 環形,中央顯原始 range 字串,固定 violet `#a78bfa`
  - **VIX** 改 circular gauge `max=40`,< 18 emerald / 18-25 amber / >= 25 red,中央 mono 字
  - **Market Top** 改 amber 三段(原 negative polarity)— 不再綠紅切換,純警示色階
  - **F&G** 改 amber-bell 三段 — 中性琥珀,偏向兩端漸深
  - 多欄位 fallback:`mt.composite_score ?? mt.score ?? m.market_top_score`、`m.fear_greed ?? m.fear_greed_index`(防止 schema drift 顯 ?)
- **`Dashboard/utils.js`**:`V1.72.4`
### Why
- 用戶反映 sector 狀態列「Market Top 顯問號 + 旁邊 4 格沒圓形」+「Market Top 應該是琥珀色 / F&G 也是」
- Market Top 是「警示指標」(高 = 高風險)而非「成長指標」,綠紅切換誤導使用者判讀;琥珀色階符合警示語義
- F&G 同屬警示性質(極端兩端都危險),amber bell 配色反映「中性 = 安全」直覺
- 8 個指標全部 circular 達成視覺一致性,離散分類用 segment pie 同樣呈現「上限 vs 目前」結構

---

## [1.72.3] — 2026-05-01
### Added — 動能選股列表可收折
- **`Dashboard/momentum.html`**: 新增 `#table-section` wrapper，包含 `#table-collapse-btn`（含 chevron icon + 「選股結果（N 筆）」標題）和原 `#table-wrap`；toggle bar 採用 glass-card 樣式，頂部 border-radius 連接底部 table
- **`Dashboard/page-momentum.js`**:
  - `toggleMomTable()`: 切換 `#table-wrap` hidden，旋轉 chevron，狀態存入 `localStorage('mom_table_collapsed')`
  - `_syncTableCollapseLabel()`: 從 localStorage 還原 collapsed 狀態（預設展開）
  - `renderTable()` 末尾自動更新標題為「選股結果（N 筆）」
  - `loadMomentumData()` / `showEmptyState()` 改用 `#table-section` 控制顯隱（原 `#table-wrap`）

---

## [1.72.2] — 2026-05-01
### Changed — Sector 頁 UX:圓形 gauge / Binary 自適應 / Today's Verdict 去重
- **`Dashboard/sector.html`** (`<style>` block + body L235-289):
  - 加 `.sector-status-row` / `.sector-gauge` / `.sector-chip` / `.binary-adaptive` 系列 CSS(~150 行 SVG circular-gauge spec + 自適應 binary container)
  - Status pill row 從 7 個 vertical text pill → **4 個 circular gauges(Breadth / FTD / Market Top / F&G,SVG stroke-dasharray + verdict-color drop-shadow)+ 4 個 categorical chips(Regime / Cycle / Exposure / VIX)**
  - Binary alert 區改 `binary-adaptive`,容器內 list 用 `data-density` 控制三段:`compact`(≤2)/ `grid`(3-5)/ `compact + <details> collapsible`(≥6)
  - Today's Verdict 從 3-col 改 **2-col**(takeaways / watch_next),刪除 `tv-actions` 欄位視覺(legacy stub 隱藏保留以免 Components 報錯)— 因為下方 Sector Matrix 已完整列出 HOT/WARM/COLD/AVOID 分組
- **`Dashboard/page-sector.js`**:
  - 新加 `_gaugeColor(score, polarity)`:三 polarity 規則(positive 高=好 / negative 高=差 / bell 兩端=差),配 emerald/amber/red 三色染
  - 新加 `_gaugeHTML({value, label, suffix, color, valueDisplay})` SVG inline gauge renderer(circumference 264,stroke-dasharray 動態繪弧)
  - 新加 `_chipHTML({value, label, color, mono})` categorical chip renderer
  - 重寫 `renderStatusStrip()` 為 4 gauge + 4 chip 結構,**保留 `setAttrs` 邏輯**讓 utils.js 的 signal-tip tooltip 引擎不破
  - 重寫 `renderBinaryAlert()` 含 adaptive 三段邏輯 + `<details>` toggle 動態切換「展開/收合」label
- **`Dashboard/utils.js`**: `const VERSION = 'V1.72.2'`
### Why
- 用戶反映 sector 頁「資訊很多但很雜」+ 部分資料重複(Today's Verdict 的 sector_actions 跟下方 matrix 100% 重疊)+ 7 個指標 pill 看不出「上限 vs 目前」距離
- 圓形 gauge 一眼看到佔比(空圈 vs 滿圈),配 verdict 色三段染色降低視覺認知負擔
- Binary risks 48h 在 0/1/6+ 事件量級下視覺一致性差(空時還佔 ~80px / 多時爆長),adaptive 自動調密度
- 確保不動 sector matrix 內部結構(verdict-group / score-ring / risk_flags / handoff)— 純上方 hero 區重塑

---

## [1.72.2] — 2026-05-01
### Fixed — Journal 統計顯示空白（hasData 邏輯錯誤）+ 新增「更新收益」按鈕
- **Root cause**: `hasData` 硬判 `20d?.n > 0`，但 20d 需等 ~20 個交易日，目前只有 5d 填入（12,342 fills）→ 統計區塊永遠空白
- **`Dashboard/page-momentum.js`**:
  - `renderJournalStats()`: 改為自動偵測最佳 horizon（fills['20d'] > 0 → '20d'，否則 '5d'），`hasData` 判斷基於 bestHorizon
  - by-signal 表格 & 標題（"By signal (5d win rate)"）動態帶入 bestHorizon
  - fills label 顯示三個 horizon 的填充數
  - 空白狀態提示文字說明原因（「fills=0 → 需跑 journal update」）
  - 新增 `updateJournalReturns()` + `_pollJournalUpdate()`：呼叫 `/api/journal-update`，每 4s 輪詢進度，完成後自動重新載入資料
- **`Dashboard/momentum.html`**: journal section 標題列加「更新收益」按鈕（`#journal-update-btn`），點擊後顯示 phase 進度
- **`dashboard_server.py`**: 新增 `run_journal_update()` + `_journal_update_state`；POST `/api/journal-update` 在背景 thread 依序執行 `journal.py update` → `journal.py stats` → `bridge.py`；GET `/api/journal-update/status` 回傳即時 phase
### Note
- 「今日快照」按鈕（stale banner）= 今天還沒拍 screen snapshot → 正確，今天已拍所以隱藏
- 「更新收益」按鈕 = 填入 forward returns 並重算統計，隨時可按

---

## [1.72.1] — 2026-05-01
### Fixed — Journal 統計頁面空白 + 今日未跑提示 Banner
- **Root cause**: `journal.py stats` 從未被自動呼叫 → `stats.json` 不存在 → `bridge.py` 回傳 `journal.stats=null` → momentum 頁 journal 區塊空白（16,043 entries 存在但前端看不到）
- **`dashboard_server.py`** (`_worker()`, ~line 986-998): `--journal` flag 為 true 且 screen.py 成功後，自動呼叫 `journal.py stats`（timeout=120s）；phase label 期間改為「computing journal stats…」
- **`bridge.py`** (`ingest_momentum_screen()`, ~line 1904-1935): binary seek 讀 `journal.jsonl` 末尾 4KB，提取最後一筆 `snap_date`，以 `journal.last_snap_date` 暴露給前端
- **`Dashboard/momentum.html`** (line ~1059): 新增 `#journal-stale-banner`（amber 色 flex row），內含 `#journal-stale-text` + `#journal-run-btn`，預設 hidden
- **`Dashboard/page-momentum.js`** (~line 1939 + 2019-2059): `renderJournalStats()` 開頭呼叫 `renderJournalStaleBanner(journal)`；新增 `renderJournalStaleBanner()` 比對 `last_snap_date` vs 今日 ISO date，stale 時顯示 banner；新增 `runJournalNow()` POST 至 `/api/run-momentum-screen` with `{journal:true}`
- **`Dashboard/style.css`** (`.sidebar-brand` / `.sidebar-brand-text`): 移除 `min-width:0` / `overflow:hidden` / `text-overflow:ellipsis`，改為 `flex-shrink:0`，修正左上角 INTELCOMMAND 末尾「D」被截斷問題
### Why
- 用戶手動跑 `screen.py --journal` 後 CSV 產出但頁面 journal section 仍空白；根因是 stats.json 從未生成
- 需要一個明確 UI 提示告知今日尚未記錄快照，避免靜默遺漏

---

## [1.72.0] — 2026-05-01
### Changed — index.html Risk Overview 重設計（severity-tier warnings + Focus Ticker 提權 + XSS pass）
- **`bridge.py`** (`extract_breadth_from_analyzer`, ~line 249-263 + assignment ~line 1992): 並列輸出新 schema `warning_flags_v2: object[]`（含 `key/severity/metric_value`），舊 `warning_flags: string[]` 保留以維持 `Dashboard/page-sector.js` 相容。每個 flag 帶確切數值（gap_pct / percentile / breadth_score / bearish_score / divergence signal）。
- **`Dashboard/index.html`**:
  - Layer 2a (Binary Alert) + Layer 2b (Warning Flags) 包進共同 `<section id="risk-overview">` 父層，加標題「風險總覽 / Risk Overview」+ count badge；兩個 child 都空才隱藏。
  - `#focus-ticker-card` 從 Momentum 卡子層抽出，提權為 Layer 2 之後的全寬 attention strip（套 `.focus-ticker-promoted`）。
  - Quick Launch input 改用 `.ticker-input-wrap` 加 `lucide:search` prefix icon；button 套 `.cta-launch`（hover glow）。
  - Modal `#preflight-body` + `#report-content` 加 `.modal-scroll-shadow` class（純 CSS sticky pseudo-element fade）。
- **`Dashboard/style.css`** (~80 lines added): 新增 `.risk-overview` / `.risk-overview-title` / `.risk-flag-card`（3 種 severity variants：critical 🔴 / warning 🟠 / caution 🟡，dot + 3px 左邊框 + name + metric chip）+ `#pill-tooltip` 子元素 (`.rft-title-*` / `.rft-metric-row` / `.rft-hint`) + `.modal-scroll-shadow` + `.cta-launch` + `.ticker-input-wrap` + `#focus-ticker-card.focus-ticker-promoted` ::after 漸層。
- **`Dashboard/script.js`**:
  - 重寫 `renderWarningFlagsIndex` (~80 lines)：用 `warning_flags_v2` 渲染，severity tier 自動排序 critical→warning→caution，每張卡掛 `data-tip-key="warning_flag"` + `data-flag-*` 屬性；schema fallback 兼容舊 string[]。
  - 加 `updateRiskOverviewVisibility()` 統籌 `#risk-overview` 父層顯隱 + 翻譯 + count badge。
  - 擴充 `#pill-tooltip` engine (line 1028-1095)：`data-tip-key="warning_flag"` 走專屬路徑，從 `i18n.warnings.tooltips.<flag_key>` 組 severity-tinted title + definition + metric chip + remediation hint。
  - Hero `renderThreeSignalMini` 4 欄各加 10-cell `.score-battery`（複用 Momentum teaser 同款元件 line ~520）。
  - 五個 teaser render 區塊（binary alert / hot sectors / news verdicts / momentum / focus ticker）全面套 `UI.escapeHTML()`，封死 innerHTML XSS [ARCH-14]；focus-ticker enqueue 改用白名單 `[A-Za-z0-9.\-]` 過濾 ticker 防止 inline `onclick` 注入。
- **`Dashboard/i18n.js`** (zh + en 雙語追加): `warnings.severity` (critical/warning/caution) + `warnings.risk_overview_title` + `warnings.tooltips.<flag_key>` (definition + hint，6 個 flag key) + 補 `warnings.flags.Critical_Zone` / `Early_Warning_Divergence` 翻譯。
- **`Dashboard/page-sector.js`** (~line 264): `warning_flags` consumer 加 schema fallback —`(typeof f === 'string') ? f : f?.key`，兼容兩種輸入避免新 schema 上線後 sector page 渲染壞掉。
### Why
- User 觀察 index.html 的 48 小時二元風險條幅下方四個 ⚠ label —「空頭信號啟動 / 廣度跌破 200MA / 歷史低百分位 / 弱化區間」。其中後三項都是同一個廣度指標的不同切面（`ma_crossover.gap` / `historical_percentile` / `composite.zone`），會綁在一起亮（今天 4 個全觸發、breadth_score=33.1）。原本扁平 flex pill 用 regex 區分紅/黃，視覺權重均等，看不出哪個是真正獨立信號（Bearish_Signal 是複合 RSI/價格/MA 維度，與廣度不重疊）。
- 順手解決長期 UX debt：Focus Ticker 藏在 Momentum 卡內易被忽視、modal 長內容無滾動指示、innerHTML XSS 系統性未修。
- Schema 採並列 v1/v2 而非取代，因為 `page-sector.js` 也消費 `market.warning_flags`；不破壞既有頁面的前提下逐步遷移。

---

## [1.42.2] — 2026-04-25
### Changed — Sector protocol token diet (round 2)
- **`sector_protocol_main.md`**: Step 1 / Step 6 sections trimmed of explanatory parentheticals (confidence-gating tutorial, replaces-Step-1 rationale, renderer note for users). Step 6 now points to `step6_overlay.py` script as authoritative; spec table compressed (10 regimes → 8 rows by grouping equal weights).
- **`sector/phase_0.md`**: (already lean — script `--skip-if-fresh 10800` flag adopted in protocol so LLM no longer needs to compare mtime manually).
- **`sector/phase_1-2-3.md`**:
  - Phase 2: replaced manual mtime check with `theme_detector.py --skip-if-fresh 10800` (script self-manages cache); trimmed historical 4-25 observation comment.
  - Phase 3: collapsed step descriptions, dropped budget comparison footnote.
- **`sector/phase_4-5.md`**:
  - Phase 4a Fan-In rules + FRED Macro Lane Prompt: removed parenthetical explanations.
  - Phase 4b consensus_warning: tighter table form.
  - Phase 4c STEP C.6: dropped "比 LLM 心算快 1 分鐘" timing footnote.
  - Phase 4c STEP G.5: removed dotcom/SPAC historical lesson narrative.
  - Phase 4c STEP H today_verdict: dropped Dashboard localization explanation paragraph + concrete chinese examples; kept rules + schema only.
- **`sector/README.md`**: absorbed all moved rationale into 5 new sections (Step 1 vs Step 6 / confidence gating / G.5 historical evidence / Phase 3 budget origin / Phase 4c Step 6 script / theme_detector timeout warning).
### Why
- Each `產業掃描` run loads sector_protocol_main + phase_0 + phase_1-2-3 + phase_4-5 + schema (~1300 lines). Every removed line × every run = real LLM token savings.
- This is the second pass after v1.41.1 (which moved older v1.2/v1.3 narrative). v1.42.0/v1.42.1 added FRED-related explanations that needed similar treatment.
- Net change: protocol files 1464→1423 lines (-3%, -41 lines) but ~70 lines of explanation moved out of LLM hot path → README.

---

## [1.42.1] — 2026-04-25
### Changed — Sector protocol speed pass (3 bottlenecks)
- **Phase 3 web fetch budget**: 4-25 run did 19 WebSearch in a subagent. New rule forces structured tools first (`market-sentiment-analyzer` → `economic-calendar-fetcher` → `earnings-calendar` → reuse `_phase0.fred_snapshot`), then HARD CAP ≤ 5 narrative WebSearch. Provided exact 5-query template + ban list (Russia/Ukraine, FDA PDUFA, bank earnings dates, copper price, AI capex, DOJ Powell — out of sector-level scope). Expected: 3.5min → 1.5min.
- **Phase 2 theme_detector runtime documented**: Added explicit warning that script needs 140-180s; ban `timeout < 240` wrappers (4-25 run wasted 145s on a `timeout 150` kill+retry); ban `--output-dir reports/` + cp dance. Expected: 3.3min → 0.8min.
- **Phase 4c Step 6 multiplier via script** (not LLM hand-computation): `step6_overlay.py` got a real CLI (`--input "Sector:Score,..."`). Phase 4c protocol now MANDATES script execution — paste JSON output directly into `sectors[].step6_fred_multiplier`. Expected: 6.9min → 5.9min.
### Why
- 4-25 sector scan ran 20 min. Phase-by-phase decomposition: Phase 0=63s / Phase 1=52s / Phase 2=3m17s / Phase 3=3m34s (subagent + 19 WebSearch) / Phase 4a=109s (verified parallel via single-message agent calls) / Phase 4b=2m7s / Phase 4c=6m52s (LLM thinking + 27KB JSON write) / Phase 5=18s.
- Phase 4a parallelism confirmed working (4 lanes in `msg_01U6D4...` single message, wall-clock = max lane = 109s vs sequential 372s).
- Estimated combined impact: 20min → ~14-15min after these 3 changes land.

---

## [1.42.0] — 2026-04-25
### Added — FRED 整合（兩 protocol + 強化 Red Team）
- **`sector/scripts/step6_overlay.py`**: deterministic Step 6 multiplier calculator. Base regime × cyclical/defensive matrix (10 regimes) + sector-specific favor/avoid override + regime_confidence gating (`effective = 1.0 + (raw − 1.0) × confidence`). Used by patcher, renderer, backtest harness.
- **`sector/scripts/backtest_step6_overlay.py`**: backtest harness using `fred-macro --asof DATE` + yfinance forward returns. Top-3 vs bottom-3 spread comparison with/without Step 6 multiplier. Currently smoke-test (n≈5 sessions) — becomes statistically valid as logs accumulate (target n ≥ 50).
- **`investment/scripts/validate_phase0.py`**: V4.9 mini-gate. Catches LLM skipping FRED L4 (most common drift mode). Checks `fred_available` / `fred_snapshot.regime_label` / `macro_multiplier_rationale` references FRED.
- **Sector Phase 4a 4th lane (`FRED_Macro_Analyst`)**: parallel subagent reads `_phase0.fred_snapshot` + `SECTOR_ROTATION_GUIDE.md`, proposes favor/avoid per regime.
- **Sector Phase 4c STEP G.5 — Macro/Theme conflict**: when FRED-Avoid sector is HOT-promoted by Theme/Rotation lane → cap WARM, +`macro_theme_divergence` flag, ×0.90 confidence. Anti-1999-dotcom/2021-SPAC rule (theme heat + macro warning = bubble top).
- **Sector Phase 4b DA prompt**: now receives slim FRED snapshot. Conflict rule: yield_curve_inverted / real_rate>2 / credit_stress / Recession-Risk regime / sector ∈ avoid → MUST construct kill_conditions citing **specific FRED values**, not vague "macro 轉差".
- **Investment Phase 2.8 Red Team prompt**: same slim FRED paste + same conflict rule. `counter_evidence_strength` ≥ 4 auto-applied when ≥ 2 FRED conflict signals trip.
- **Sector schema**: `_phase0.fred_snapshot` slim (11 fields) + `sectors[].step6_fred_multiplier` + top-level `step6_overlay` block.
- **Sector renderer**: new `FRED×` column in FINAL VERDICT TABLE (when overlay applied) + new "Step 6 — FRED Regime Overlay" section.
- **Sector validator**: enforces `_phase0.fred_available` + `fred_snapshot` slim shape compliance.
### Changed
- **`skills/fred-macro/scripts/fetch.py`**: composite score now uses **latency-weighted** average. Real-time series (rates / credit / NFCI) weight 1.0; ICSA-mixed employment 0.7; CPI/PCE inflation 0.5. Solves the "Lag Trap" (54-day-stale CPI driving today's regime overlay). composite changed 60→62 in current snapshot (negative inflation_score down-weighted).
- **Sector Step 1 cycle_phase multiplier**: now SKIPPED when `fred_available=true` (Step 6 takes over). Avoids double-counting regime via two LLM heuristics.
- **Sector Phase 0**: new Layer E (FRED MUST-run) parallel to A-D.
### Why
- Audit revealed: across 7 recent investment runs (4-23 to 4-24), **0/7** populated `fred_available` / `fred_snapshot` / `macro_multiplier_rationale` despite V4.9 spec marking these MUST-run. `validate_session_export.py` only checks Phase 5 export, never gates phase0.
- Sector protocol had **zero** FRED integration. Today's run produced HOT for Industrials and WARM for Tech while FRED simultaneously flagged "Overheating regime, avoid Tech/Real Estate/Cons Disc" — major macro-vs-sector divergence with no mechanism to surface it.
- Gemini review caught Lag Trap + double-count + token bloat issues; partially adopted (lagging-tier weighting fix; Step 6 replaces Step 1; slim FRED paste). Disagreed on lane-conflict resolution (Gemini wanted theme to override macro; reversed direction per dotcom/SPAC history).

---

## [1.41.1] — 2026-04-24
### Changed
- **Sector protocol 檔案瘦身**：`sector_protocol_main.md` / `phase_0.md` / `phase_1-2-3.md` / `phase_4-5.md` 全面移除人類向敘述、計算範例、歷史沿革，僅保留 LLM 執行所需的規則與步驟。Protocol 總行數 702 → 641（-9%）。
- **`sector/README.md` 擴充**：吸收移走的內容（Phase 0 三訊號合成計算範例 ×2、Phase 5 機械化背景與動機、文檔分工說明、V1.4 changelog 條目）。檔案分工原則寫入 README 開頭：protocol 檔只給 LLM 看，README 只給人看，避免雙邊漂移。

---

## [1.41.0] — 2026-04-24
### Added
- **`sector/scripts/render_sector_report.py`** — deterministic JSON→Markdown renderer for Phase 5. Reads latest `sector_logs/*_sector_intel.json`, emits `reports/YYYY-MM-DD_sector_report.md` with 7 sections (Verdict table, Macro, Today's Verdict, DA challenges, Divergence, Themes, Handoff). Zero LLM calls.
### Changed
- **Sector protocol V1.4**: Phase 5 is now a mechanical step (JSON write → validator → renderer → user summary). Portfolio Strategist MUST NOT rewrite markdown; if output is wrong, fix the JSON or the renderer.
- `sector/phase_4-5.md` Phase 5 section rewritten with 4 discrete steps and an explicit "≤ 10 行 summary, do not repeat today_verdict" instruction to the model.
- `sector/sector_protocol_main.md` Rule 5 updated to reflect renderer ownership of markdown output.
### Why
- Today's sector scan took 26 min (`sector/scan_logs/sector_20260424_210620.log`). Timeline reconstruction showed 663s of pure LLM generation for Phase 5 markdown + 225s for the final summary — both redundant because `_phase4c.today_verdict` already carries the zh-TW narrative. Rendering from JSON reclaims ~15 min per run.

---

## [1.40.0] — 2026-04-24
### Added
- **Phase 0 L4 FRED integration** in `investment_protocol_v4_8.md` — MUST-run `fred-macro` skill alongside existing 3-layer cache cascade, outputs `fred_snapshot` block with 12 official series (rates / inflation / employment / credit / stress).
- **Macro multiplier blending rules** — LLM baseline from headline-score table + up to 4 FRED-derived caps (yield_curve_inverted 0.75 / credit_stress 0.85 / NFCI>0 0.9 / real_rate>2 0.9) taking min. All-clear bonus × 1.05.
- **`macro_multiplier_rationale` field** (mandatory) documenting the blend decision per run.
- **Dashboard FRED refresh thread** — `dashboard_server.py` adds `fred_refresh_loop` daemon at 15-min cadence (`FRED_REFRESH_SEC=900`), independent of the 5-min bridge loop.
- **`bridge.py` injects `fred_macro` into `data.json`** so Dashboard pages have access without each page re-fetching.
### Changed
- GLOBAL RULES §8 MUST-run list adds `fred-macro` (failure non-blocking; `fred_available=false` continues flow).

---

## [1.39.0] — 2026-04-24
### Added
- **`fred-macro` skill** (`skills/fred-macro/`) — fetches 12 key FRED series via free API (120 req/min, no daily cap). Output: per-series `{value, date, yoy/mom change, percentile_1y, trend_30d}` + aggregate `regime_signals` (yield curve, fed direction, real rate estimate, credit stress).
- Parallel fetch via `ThreadPoolExecutor(6)` → 2-second run for 12 series.
- 15-minute atomic-write cache at `skills/fred-macro/cache/fred_latest.json`.

---

## [1.38.4] — 2026-04-24
### Changed
- Preset tooltip criteria now show translated label (`強多` not `STRONGLY_BULLISH`) and clarify that "Hot Sector" (dynamic from sector scan) differs from the manual "Sector" dropdown (page-momentum.js).

## [1.38.3] — 2026-04-24
### Added
- **Preset-button hover tooltip** — reuses existing pill-tooltip system; new `PRESET_DETAIL_ZH/EN` dicts with 3-section layout (criteria / strategy / action) for all 10 presets.
- `data-preset-tip` attribute + purple accent CSS class.

## [1.38.2] — 2026-04-24
### Added
- **MACD column click popup** mirrors RSI popup structure — header values + zero-axis position bar + 4-quadrant regime map (strongest_bull / weakening_bull / reversal_bull / strongest_bear) + personalised advice.
### Changed
- MACD cell: removed native `title=` tooltip, cell is now clickable.

## [1.38.1] — 2026-04-24
### Added
- MACD column sortable (`data-sort="macd_hist"`).
- **Custom pill hover tooltip** for 11 signals + 7 warnings — replaces ugly native `title=` with a themed card (green for signals, red for warnings), each with description + actionable hint.

## [1.38.0] — 2026-04-23 (commit 4ff7849)
### Added
- Leader button + i18n fixes; MACD column first appearance.
- Earlier (commit f07847c): MACD field wiring in momentum-monitor — `compute_macd()` added to `technical_core.py`; `screen.py` CSV columns + bridge.py + Dashboard row render pipeline.

---

## [1.37.0] — 2026-04-23
### Changed
- **SKILL.md slim** (3 files): `market-news-analyst` 727 → 253 lines, `us-stock-analysis` 297 → 137, `technical-analyst` 241 → 137. Pedagogy / tone / example queries moved to new per-skill `README.md` (3 new files).
- **`technical_core.py` extracted** as shared module between `momentum-monitor` and `technical-analyst` (Option C refactor — no duplication of MA / RSI / volume / stage / crosses primitives).
- **New `us-stock-analysis/scripts/analyze.py`** (fundamentals), **`market-news-analyst/scripts/fetch.py`** (news + analyst actions via finvizfinance), **`technical-analyst/scripts/analyze.py`** (adds MACD + swing-pivot S/R on top of shared core) — addressed "missing script" bug that caused V4.8 Phase 2 subagents to fall back to 30-min WebSearch loops.
### Fixed
- **FMP 429 short-circuit** (3 skills): `theme-detector/etf_scanner.py` + `market-top-detector/fmp_client.py` + `earnings-valuation-forecaster/forecast.py` — first 429 sets flag, subsequent calls skip HTTP. Removes 60-second retry sleep and infinite recursion.
- `theme-detector` daemon-thread timeout for `batch_stock_metrics` (replaces ThreadPoolExecutor which waited on exit).

## [1.36.1] — 2026-04-22 (commit f9caed0)
### Fixed
- **`bug.md` four tickets cleared**: scan banner lost on cross-page nav (sector + news resume covers running/done/error states within 5-min window); `bridge.py` `data.json` writes now atomic (`os.replace`); `scan_confirm` dialog notes preflight phase timing; `AnalyzeQueue` closes BUG-004.
### Added
- `supply-chain-event-analyst` skill.

## [1.36.0] — 2026-04-22
### Added
- **Momentum watchlist feature** — `universes/watchlist.txt` for non-SP500 tickers (APLD / ALAB / RKLB seed), merged automatically when `--universe sp500`; CSV `in_sp500` flag.
- Three REST endpoints on `dashboard_server.py`: `GET/POST/DELETE /api/momentum-watchlist`; atomic file write + `_TICKER_RE` regex validation.
- `momentum.html` ⭐ button + modal with chip list (add/remove with ×) + filter panel "Watchlist 範圍" three-way chip; purple accent row tint for non-SP500.

## [1.35.0] — 2026-04-22
### Fixed
- **Intraday volume pollution** — `momentum.py:_volume_block` used yfinance's partial-day bar directly, triggering `volume_dry_up` on ~500 tickers when scanning during session hours. New `_intraday_state(hist)` three-way classifier (`complete` / `partial` / `too_early`); partial scales `today_v × 390/elapsed_min` to project full-day equivalent; too_early suppresses volume signals entirely.
- `volume_trend` v5/v10 comparison now uses prior-days-only to avoid intraday drift.

## [1.34.x] — 2026-04-21
### Added
- **Protocol-run session exclusion** rule in CLAUDE.md — sector scan / news / invest protocols do NOT trigger VERSION bump or todolist update (root-caused a stuck subagent rc=1 loop).
- CLAUDE.md slim (165 → 81 lines); README expanded (148 → 244 lines) absorbing market classification / protocol evolution / rule rationale.
- Sector banner UI: title/status/latest-log wrapped in `flex-1 min-w-0 overflow-hidden` container; long 401 JSON no longer deforms card.

## [1.32.0] — 2026-04-21
### Changed
- **Dashboard M1+M2+M3 overhaul**: Layer 1 hero = Today's Verdict (stance + headline + 3-col takeaways/sector_actions/watch_next); Layer 2 binary-risk banner + warning_flags strip; Layer 3 three-column teaser (HOT sectors / reviewed news / momentum top 3); cross-module ⭐ intersection signals (`recent_analysis.decision ∈ {BUY,EXECUTE} ∩ momentum top 30`).

## [1.30.0] — 2026-04-19 (commit 02162a9)
### Added
- **Global analyze queue** (`AnalyzeQueue` module) — per-ticker 🔍 button enqueues ticker; background worker thread runs `run_protocol("invest")` serially; dedupe active/pending; decisions page widget shows NOW ANALYZING / QUEUE / RECENT history.
- Market-hours-aware cache freshness (`_market_minutes_between` helper; weekend / post-close cache stays FRESH).
- Deep-links from sector card → momentum page with sector filter pre-applied.

## [1.28.0] — 2026-04-20
### Added
- Today's Verdict structured object on sector page (stance + confidence + key_takeaways + sector_actions + watch_next) — consumed later by index dashboard.

## [1.27.0] — 2026-04-19
### Changed
- Three-page scan log UI unified — inline glass-card with expandable live-log, replaces fixed banner / compact pill. Live stderr tail via new `log_tail` field in status endpoint.

## [1.23.0] — 2026-04-19 (commit 38ce105)
### Added
- Momentum screener Dashboard first ship — covers v1.13 → v1.23 (new `momentum-monitor` skill, full momentum page, filter panel with 6 presets, score battery UI, stage/rsi/volume popups, GICS sector dimension, intraday volume projection).

## [1.22.x] — 2026-04-18
### Added
- RSI column clickable popup (blood bar + zone legend + personalised advice).
- Stage classification popup (MA stack visualization + rule checklist + transition conditions).

## [1.21.0] — 2026-04-18
### Fixed
- **Volume ratio intraday projection** — clickable popup shows "projected full-day volume" when ET 9:30-16:00; `_avg_prev(n)` excludes today to avoid self-dilution.

## [1.20.0] — 2026-04-18
### Added
- **GICS sector dimension** in momentum selector — `sp500_sectors.json` from Wikipedia S&P 500 list (503 tickers × 11 sectors); sector subscript on ticker cell + filter dropdown.

## [1.18.x] — 2026-04-18
### Fixed
- JSON.parse NaN bug — `momentum.py` / `bridge.py` sanitize NaN → None; `json.dump(allow_nan=False)`.
- Scan real-time progress via `Popen` + background reader thread parsing `screen.py` stderr.

## [1.17.0] — 2026-04-18
### Changed
- Momentum to **client-side real-time filtering** (previously server-side `min_score=60`) — backend returns all 503 rows, client filters live. Enables instant slider changes without rescan.

## [1.15.0–1.16.0] — 2026-04-17
### Added
- RSI-14 (Wilder smoothing) in `momentum.py`.
- 10-cell battery UI for score display.
- `ThreadingHTTPServer` to prevent scan blocking other requests.

## [1.13.0] — 2026-04-17 (commit 38ce105 begins)
### Added
- `momentum-monitor` skill (per-ticker volume / MA / short interest / composite score 0-100) + CLI + cache.

---

## [1.12.0] — 2026-04-16
### Added
- `feat: V4.8 protocol` (commit b955a5c) — **Parallel Blind Analyst Subagents** (4 Phase 2 analysts now run in single-message parallel Agent tool calls with `subagent_isolated:true` sentinel).
- Per-card refresh on decisions page.
- `market-sentiment-analyzer` skill file-based cache (15-min TTL).

## [1.11.0] — 2026-04-16
### Added
- Pre-market preflight cache health modal (`/api/preflight`, `/api/preflight/run-free`) — one-click refresh for stale breadth/FTD/market-top caches.
- Reverse-call from Dashboard to Claude CLI (`/api/run-protocol` covering invest/flash/digest/review).

## [1.10.0] — 2026-04-16 (commit 0f3bcd2)
### Added
- **News review workflow** — REVIEW mode + Dashboard `reviewed` / `pending` filter pills + submit-for-review button.
- FLASH/DIGEST buttons on Dashboard news page trigger reverse-call.

## [1.9.0] — 2026-04-16 (commit 62fdabe)
### Added
- News V2 protocol — RSS two-stage funnel + 4-agent roundtable (Bull/Bear/Sector/Macro).
- 4 missing skills added; protocol MUST-run rules; calibration doc.

## [1.5.0–1.8.0] — 2026-04-13 (commits d34f2b1, b03f806, 90e6034, 54bc9a0)
### Added
- `market-breadth-analyzer` skill (C-BREADTH) with TraderMonty CSV data source — 6-component 0-100 composite.
- `ftd-detector` skill (C-FTD) via yfinance adapter — dual-index tracking (S&P 500 + NASDAQ), rally-attempt state machine.
- `market-top-detector` skill (C-TOP) — O'Neil Distribution Days + Minervini leadership deterioration + Monty defensive rotation.
- Hover tooltip explanations on `breadth.html` indicator cells.

## [1.3.0–1.4.0] — 2026-04-12 (commits 304da30, 062bdee, dd61383)
### Added
- 4 risk/sentiment skills integrated into protocols (V4.5 / V1.1):
  `short-contrarian-analyst` (Burry) / `market-sentiment-analyzer` / `portfolio-risk-manager` (vol-adjusted caps) / `tail-risk-analyzer`.
- Historical, news, sector pages added to Dashboard.
### Fixed
- Safari compatibility; UI icon issues; dash logic bugs.

## [1.2.0] — 2026-04-11 (commit 35d23f6)
### Changed
- Project structure reorganization; protocol upgrades (Sector V1.2 multi-file + Investment V4.4).

## [1.1.0] — 2026-04-11
### Added
- `investment/` / `sector/` / `news/` protocol directories with per-module README.

## [1.0.0] — 2026-04-09 (commit 98cce74)
### Added
- **Initial commit**: AI投資委員會 multi-protocol investment system.
  - `investment_protocol_v4_3`: individual stock analysis with 8-agent debate.
  - `sector_protocol_v1`: pre-market sector intelligence with bull/bear debate.
  - `news_protocol_v1`: real-time news analysis with cache patching.
  - Three-layer Phase 0 cache: sector_intel → phase0 → web search.
  - Skills: `us-stock-analysis`, `market-news-analyst`, `technical-analyst`.

---

## Evolution highlights

For quick orientation of future Claude sessions:

- **Weeks 1-2** (v1.0 → v1.12): foundational skills + protocols; sector/news/invest three-way split; Dashboard first pages.
- **Week 3** (v1.13 → v1.30): momentum-monitor ecosystem (screener + journal + live Dashboard page with every interaction clickable); analyze queue; watchlist.
- **Week 4** (v1.31 → v1.38): UX polish phase — banner layout, MACD/RSI/Stage popups, preset strategy tooltips, custom tooltip system; bug.md triage.
- **Week 5** (v1.39 → v1.40): macro data enrichment — FRED API integration for authoritative rates/inflation/employment/credit feed into Phase 0 multiplier calibration.

Protocol evolution: investment V4.3 → V4.8 (parallel blind analysts); sector V1 → V1.3 (multi-file with Phase 0-5 split + validator gate); news V1 → V2.1 (RSS two-stage + 4-agent roundtable + per-agent batch subagent).
