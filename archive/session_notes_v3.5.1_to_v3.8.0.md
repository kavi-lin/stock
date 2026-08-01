# Session Notes 歸檔 v3.5.1 → v3.8.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v3.8.0 → v3.8.1) — Break News 辯論氣泡左右/配色修正

使用者問:為何 break news 中 codex ↔ gemini 辯論兩邊都靠右、都藍方角色。查 `renderThreadBubble` (`Dashboard/news_components.js`):左右 + 配色用 `agent === 'claude'` 硬判,只有 claude 走左/橘,其餘 model 全部右/藍。多模型治理層 (V3.7.0) 後辯論配對可為任意兩 model,配對非 claude(codex ↔ gemini)時兩邊都判非 claude → 都右、都藍。對比 `debater.py._role_for` side 本就用位置判 (idx==0→A 否則 B)。修法:`debater.py` comment record 新增 `side` (`"A"`/`"B"`) 欄(後端位置真相,schema validate 用 subset 不擋);前端改讀 `comment.side` 決定左右+配色(A=左/橘、B=右/藍),舊資料無 side 時 fallback 解析 role label 再退回舊 heuristic;avatar 改 model 查表 (claude🤖/gemini💎/codex🧠)。bump 3.8.0→3.8.1。

## 🟢 Session Note (v3.7.1 → v3.8.0) — Break News 免費社群/趨勢源

使用者要求在 break-news 頁面多加 source,包含社群,探勘市場趨勢。先查現況:poller 只有 9 RSS + Futu,Dashboard raw stream 已能承接未閘來源。實作低摩擦免費版:新增 `scripts/break_news/social_sources.py`,輸出與 RSS 相同 normalized shape,接 Reddit subreddit RSS、HN Algolia、Google Trends RSS；Bluesky public search adapter 保留但預設關閉(真實 dry-run 回 403,需 `BREAK_NEWS_BLUESKY_ENABLED=1` 才測)。`poller.py` 新增 `BREAK_NEWS_SOCIAL_ENABLED` + `BREAK_NEWS_SOCIAL_GATE_MIN_SCORE`；社群/趨勢 item 預設進未閘 Raw 流,但 auto-debate 門檻提高,避免雜訊吃每日 debate budget。raw entry 加 `is_social` / `source_meta`;state 加 `items_added_social` / `social_enabled` / `feed_stats`。真實網路 dry-run:Reddit 20,HN 10,Google Trends 0(市場關鍵詞過濾後),Bluesky disabled。X/Stocktwits/Product Hunt 不做 P0: X pay-per-use、Stocktwits 新 app 註冊暫停、Product Hunt token+商用限制,留 TODO optional。bump 3.7.1→3.8.0。

## 🟢 Session Note (v3.7.0 → v3.7.1) — Break News 辯論獨立配對

codex code review 指出 v3.7.0 漏了:Break News debater 跟通用路由共用 primary/secondary,改 dashboard 設定會同時動兩邊。修 4 個 finding:(1) `config/llm_config.json` 加 `break_news: {primary,secondary}` 區段;(2) `llm_drivers.load_llm_config()` 解析它 + 新 `break_news_pair()`,`debater._turn_order()` 改讀此區;(3) `POST /api/llm-config` 接受 `break_news`(merge);(4) sidebar 加「突發辯論配對」子區 A/B 下拉。另修辯論身分標籤:debater turn fallback 換模型後用 `res.model_used` 重貼 role label(side A/B 仍位置固定)。取捨:保留 tertiary(通用 fallback 鏈,v3.7.0 已核准),Break News 配對與它並存非取代。bump 3.7.0→3.7.1。

## 🟢 Session Note (v3.6.3 → v3.7.0) — Multi-model Governance(Governor 層)

3 個模型 CLI(claude/gemini/codex)過去無 fallback、無預算/quota 感知、協定寫死 claude → claude 額度掛了全停。建治理層:`scripts/_shared/model_router.py`(新)— `run_role()`/`run_with_fallback()` 走 fallback 鏈(primary→secondary→tertiary),跳過停用/超預算/quota cooldown,失敗或撞 quota 自動降級;`config/llm_usage.json` 記每模型每日 calls + cooldown(UTC 日界重置);quota 偵測 = best-effort 比對 rate-limit/429/quota 字樣。`config/llm_config.json` 擴充 tertiary/enabled/budgets/cooldown_hours(舊 schema 相容),`llm_drivers.load_llm_config()` 回傳完整 config + 新 `model_chain()`。消費者接 governor:debater(每回合 `run_with_fallback`,模型掛了換不 abort)、supply_chain。協定:`run_protocol` 用 `pick_model()` 選模型(claude 優先,gemini/codex 頂替)+ `_protocol_command()` per-model 指令 + `note_run()` 記帳。dashboard:`/api/llm-config` GET 回 config+status、POST merge;sidebar 加備援下拉 + 每模型用量/冷卻顯示,codex 解鎖。注意:`run_codex` 之前已由 codex 自己寫好(非 stub)。協定跑非-claude 模型品質未驗證,故 claude 永遠排第一。bump 3.6.3→3.7.0。

## 🟢 Session Note (v3.6.2 → v3.6.3) — SVG trend-chart 寬螢幕適配

使用者回報情緒趨勢圖在寬螢幕上「線太粗、字太大」(還重疊)。根因:`trend-chart.js` SVG viewBox 固定 760,圖 `width:100%` 撐滿 → 寬容器上整體放大 ~2.6×,`stroke-width` 與 SVG `<text>` 等比爆大。修:(1) 所有 stroke 加 `vector-effect="non-scaling-stroke"` → 線寬恆 1.3px;(2) x 軸日期 + 「現在」標籤從 SVG `<text>` 改 HTML overlay span(`.trend-xaxis`/`.trend-xlabel`/`.trend-nowlabel`,固定 9px/8px);(3) 日期標籤碰撞檢查(<8% 距離略過);(4) now 圓點 r 2.8→2.2。單檔 `trend-chart.js`。bump 3.6.2→3.6.3。

## 🟢 Session Note (v3.6.1 → v3.6.2) — 日界趨勢 tick 與現在標記

使用者反映情緒趨勢圖 x 軸 `5/15 18h` 難看懂。單檔改 `Dashboard/trend-chart.js`:x 軸由「4 個任意 1/3 位置 tick」改成「按本地日界」— `_dayTicks()` 偵測午夜,每個日界畫極淡垂直分隔線 + 標「日期+星期」(`fmtDay()` → `5/16 六`/`Sat`)。±0.5 參考格線 `rgba(255,255,255,0.05)`(淺色主題看不見)改 theme-safe `rgba(128,128,128,0.12)`。修最右標籤裁切(估寬 clamp)。最新點加極淡「現在/now」標記。padB 16→20。hover tooltip `13h`→`13:00`。線條/顏色/資料/endpoint 不動。break-news.html 與 index.html 兩處 mount 同步受惠。靜態 JS,硬重載即可。

## 🟢 Session Note (v3.6.0 → v3.6.1) — sector 協定 turn-bloat 重構

2026-05-18 sector run 跑 33 分(52 turns)超過 30 分 timeout 被砍 — 但其實已成功。診斷(讀 `sector/scan_logs/sector_20260518_102854.log`):非 429(log 裡的 429 字串是 phase_1-2-3.md 內文被 Read 的誤命中)、非子代理 — 是 parent agent turn 太碎:手寫整個 15+ key 巢狀 `sector_intel.json`(實際還寫 `/tmp/build_intel.py` Edit ×2)、逐檔 `python3 -c` peek、validator retry。修法:把機械組裝移進 committed 腳本。新 `sector/scripts/build_sector_intel.py`(從 phase cache + 精簡 decision JSON 組出完整 intel,decision schema 見腳本 docstring)+ `sector/scripts/sector_digest.py`(一次印 macro + 11-sector 決策表)。協定 MD 改寫:phase_1-2-3(不再手抄 cache 欄位)、phase_4-5(Phase 5 改寫 decision JSON→跑 build script;Phase 4a 並行 launch 升級硬規則)、sector_protocol_main GLOBAL RULE 7、schema.md 指向。`SECTOR_TIMEOUT_SEC` 1800→2700。子代理建構交 general-purpose agent(已測:build→validate rc=0→render rc=0)。bump 3.6.0→3.6.1。

## 🟢 Session Note (v3.5.3 → v3.6.0) — 可設定主要/次要 LLM

使用者要能在設定面板切換 LLM(主要用於生成、次要用於辯論/未來 review),預設 3 個 CLI:claude/gemini/codex。先收到一份 Gemini 寫的 plan,但其「bridge.py 即時新聞」項已過時(`extract_shallow_news` v3.4.0 已移除、即時 raw 新聞已是 break-news「未閘 Raw 流」v3.3.2)— 略過;其「supply_chain `--agent`」項泛化納入。最終做中等版:**server-side config + sidebar 設定面板**(不做 web review 層)。`config/llm_config.json`(新,server-side — Python script 讀得到,localStorage 不行)。`llm_drivers.py`:`run_codex` graceful stub(codex 未接線,rc=1 不 crash)、`_RUNNERS` registry + `run_llm()` dispatcher、`load_llm_config/primary_model/secondary_model`。`dashboard_server.py`:`GET/POST /api/llm-config`(POST 驗證 + 寫檔)。`utils.js` renderSidebar footer 加可展開「⚙ 設定」面板(主要/次要下拉,Codex disabled「即將支援」),change → POST + toast;`style.css` 加 `.sidebar-settings`。`supply_chain.generate(theme, agent=None)` 走 primary + 新 `--agent` CLI 旗標;`debater.py` `TURN_ORDER` 改由 config 解析 `[primary, secondary]`(缺失 fallback claude↔gemini)。預設 config = 舊行為零回歸。驗證:endpoints GET/POST/400 正常、`--agent codex` graceful 失敗不寫檔、debate turn order 預設 claude-gemini。Codex 預留:填 CLI flags + 解除 disabled 即可。6 檔。

## 🟢 Session Note (v3.5.2 → v3.5.3) — heatmap 429 熔斷器

使用者回報 server log 狂噴 `[heatmap] HTTP error: 429`(沒開 heatmap 頁也噴)。診斷:`heatmap_refresh_loop` 是常駐背景 daemon(保溫 `heatmap.json`,與頁面無關),盤中每 10 分 fan-out ~517 個 FMP `stable/quote` 呼叫(20 workers),FMP 方案被限流 → 全 429,每輪噴 ~500 行。修:`dashboard_server.py` 加 429 熔斷器 — `_fmp_get_json` 收 429 設 `_heatmap_ratelimit_until = now+1800` 且只首次 log;`_heatmap_refresh_quotes`/`_heatmap_refresh_pe_universe` 開頭檢查熔斷器冷卻中就跳過整批;`_fetch_one`/`_fetch_pe_ttm` 逐一檢查 → 跳閘後排隊 symbol 不再打 API。429 風暴從每 10 分 ~500 行 → 每 30 分窗 ~1-2 行。單檔改動。bump 3.5.2→3.5.3。

## 🟢 Session Note (v3.5.1 → v3.5.2) — 供應鏈圖節點卡對齊

使用者回報供應鏈圖節點卡:卡片重疊、溢出 module 框、badge 中英不一致。根因:卡片用 `min-height` 但 2 行 role + badge 列實際撐高到 ~90px+,佈局卻以固定 68px 排版 → 重疊 + 溢出。修:卡片改固定 `height`,`NODE_H` 68→100,`.sc-role` `flex:1`、`.sc-badges` `flex-shrink:0` 錨底 → 等高卡、間距一致、面板精準。badge:新增 `groundingLabel`/`heatLabel`/`listingLabel` 隨 `isZh()` 切換,節點卡 + detail panel 全本地化(原本顯示原始 enum LLM_ONLY/VERIFIED)。`NODE_W` 174→198 減少名稱截斷。bump 3.5.1→3.5.2。
