# Session Notes 歸檔 v3.8.1 → v3.12.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v3.12.0 → v3.13.0) — Migrate gemini CLI to agy CLI

使用者要求將專案中所有呼叫 `gemini` CLI 的地方改為 `agy` CLI。實作內容：
1. `llm_drivers.py`: `GEMINI_BIN` -> `AGY_BIN` (agy)，`run_gemini` 更新為 `agy --print` 並移除 `--output-format json`，改由 3-stage extractor 處理。
2. `dashboard_server.py`: `_protocol_command` 更新，將 `--approval-mode yolo` 替換為 `agy` 的 `--dangerously-skip-permissions`。
3. `CLAUDE.md` / `GEMINI.md`: 文件同步更新。
4. 版本號 bump 3.12.0 -> 3.13.0。

## 🟢 Session Note (v3.11.0 → v3.12.0) — Cerebras supply-chain grounding

使用者要求檢查昨天產出的 Cerebras/CBRS 供應鏈是否漏項，web 查核後發現最大問題是
`cerebras.yaml` 已修正 ticker/listing 但內容仍偏舊：缺 OpenAI 750MW inference capacity、
AWS Bedrock / Trainium × CS-3 disaggregated inference、AlphaSense/Cognition/Meta Llama API/
OpenRouter/Hugging Face 等 2026 年核心商業與分發節點。已補進 YAML，spine 改為
`tsmc -> cerebras -> aws -> openai`，G42/Aleph Alpha 保留為 sovereign AI 分支。

同輪修 supply-chain generator：`_local_context_for_theme()` 從本地 Nexus / news / break-news /
reports 抽 theme 相關片段注入 prompt；`_audit_chain()` 生成後提示重要實體漏項、上市狀態錯、
下游客戶稀稀疏、未公開關係卻非 unknown stage。Prompt 加 company/ticker 主題規則與 evidence
hygiene；`SCHEMA.md` 補 `stage` 與 note 標示規範。驗證：`cerebras.yaml` 28 nodes / 29 edges
schema sanity errors=0；`supply_chain.py` py_compile 通過。

## 🟢 Session Note (v3.10.0 → v3.11.0) — Invest V5.0.x decision quality patch

使用者把 codex 的 V5.1 大改方案請我評估。原方案要砍 5 lane→3 lane(含 Sentiment 併入 News、Risk 併入 Valuation)、移除 MD formatter agent、Red Team 條件式。Review 後指出 5 處要修:Sentiment 不能合(insider/short/institutional 是獨立 edge)、Risk 留 Phase 4、Red Team gate 反向(consensus BUY 強制跑)、Technical 退 script 是對的但要設極端門檻、fast gate 要 shadow 校準。使用者改成「V5.0.x patch 先做、V5.1 後做」分段方案。Plan mode 寫入 `~/.claude/plans/llm-llm-queue-pythone-script-whimsical-beacon.md` 含完整數字門檻(conf cap 0.65 / size cap 30bps / shadow KPI agreement≥70%、fast_too_strict<10%)。

本輪只實作 V5.0.x 3 patches(同 1 commit):
- **A1 — UI/decision 跨欄一致**:`validate_session_export.py` §9 拒絕 `final_action=CANCEL + final_decision in {BUY, STAGED_ENTRY}` 並存;`Dashboard/page-decisions.js` 對遺留壞資料 defensive render 成 muted dual label。
- **A2 — Phase 4.6 Valuation Decision Cap**:新 phase deterministic 條款,anchors<2 / fair value confidence=low / data_quality low 任一觸發 → no BUY、conf ≤ 0.65、size ≤ 30bps。schema 加 `decision_cap_active` / `decision_cap_reason` / `cap_override_reason`,validator §10 強制。`investment_protocol_v5_0.md` Phase 4.5 後加新段。
- **A3 — `append_session_export.py`**:新 script 用 `fcntl.flock(LOCK_EX)` + tmp atomic rename 寫入 history.json;Phase 5 Step 1 改成 PM Write 暫存 + 呼叫 script,不再 prompt 內手寫巨大 JSON。Roundtrip 測試通過(132→133→restored 132,validator rc=0)。

注意:codex 已先 bump 3.10.0(supply-chain queue),所以本輪 bump 3.10.0→3.11.0。V5.1 mode 切換 + 4-lane + shadow 校準等 V5.0.x ship + 觀察 2 週 / ≥5 個 ticker 後再啟動,KPI 達標(agreement ≥70%、fast_too_strict <10%)才開 production skip。

## 🟢 Session Note (v3.9.5 → v3.10.0) — Supply-chain queue + Truth Social source

使用者在供應鏈頁輸入 TPU 生成時切頁，server log 出現 `BrokenPipeError`。診斷:原 `POST /api/supply-chain/generate` 是同步 request，生成成功但瀏覽器 abort 時 server 寫回 JSON 會噴 pipe，且任務不進右下角 pill。修:新增 custom queued protocol `supply_chain_generate`，沿用既有 `_protocol_queue` / `/api/protocol-queue` / global pill；worker 背景跑 `_sc.generate(theme)` + `_sc.enrich()` 並寫 `_sc_cache`。供應鏈頁改成 enqueue 後顯示「已排入佇列」，留在本頁時每 5s 刷 chain list，完成自動載入新主題；切頁則 pill 顯示 `🔗 Supply <theme>`。`_json()` 靜默處理 BrokenPipeError。bump 3.9.5→3.10.0。

同輪使用者要求 Raw 流考慮追蹤 Trump Truth Social。新增 `social_sources.fetch_truth_social()`，預設 `BREAK_NEWS_TRUTH_SOCIAL_ENABLED=1`、handle=`realDonaldTrump`，用 Truth Social Mastodon-like lookup/statuses endpoint 抓公開貼文，source=`Truth Social:@realDonaldTrump`、credibility=MEDIUM、`_social_source=True`。Raw 全收，auto-debate 仍走 social gate；若 endpoint 被擋只在 feed_stats 記 error，不影響其他來源。

同輪追問 Codex quota 滿是否會 fallback Claude。debater 實際留言已會用 `res.model_used` 重貼 Analyst label，但 poller admission v3.9.4 只看指定 voice headroom，Codex 滿會餓死 automatic admission。修 `_model_call_headroom()` 模擬 `run_with_fallback(preferred)` route:每個 voice 用第一個 available 且 headroom 至少 `BREAK_NEWS_EST_CALLS_PER_DEBATE` 的模型計容量；若 selected model != preferred，state 標 `fallback_backed_capacity=true`，前端 tooltip 顯示 fallback-backed。這樣 Codex 剩餘 call 不足一場 debate、但 Claude 可用時，仍會 admit 新辯論，留言顯示實際 Claude。

## 🟢 Session Note (v3.9.4 → v3.9.5) — 未閘 Raw 流排序

使用者問 Raw 流來源、為何看起來很少，並要求時間近到遠排序。查 `_raw_stream.json`:實際 248 筆，來源含 Yahoo Finance/MarketWatch/CNBC/Seeking Alpha/Investing.com/PR Newswire/Futu/Reddit/HN；畫面只取 `/raw-stream?limit=120`，且原排序用 `fetched_at`，同輪 poll 全同時間戳所以順序不像新聞發布時間。修 `store.load_raw_stream()/save_raw_stream()` 改用 `published` desc，缺值才 fallback `fetched_at`。bump 3.9.4→3.9.5。

## 🟢 Session Note (v3.9.3 → v3.9.4) — Break News model-aware admission

使用者回報 Break News 頁顯示「今日剩餘預算 0」、最後辯論已 3h 前，但 settings 的 Claude/Gemini/Codex quota 都還有。診斷:poller 仍用 `BREAK_NEWS_DAILY_MAX_DEBATES` 全域 item hard cap，與 multi-model governor 脫鉤，導致 debater 被 admission gate 餓死而非模型 quota 真用完。修:poller admission 改讀 Break News A/B voice 的有效 headroom；capacity = `min(A,B headroom) - session_call_reserve - pending_debate_backlog * BREAK_NEWS_EST_CALLS_PER_DEBATE` 再除 calls/debate。Codex 只算 fallback buffer，不拉低正常 capacity；任一 voice disabled/cooldown/over-budget 則 automatic admission=0。`BREAK_NEWS_EST_CALLS_PER_DEBATE` 預設 6；`BREAK_NEWS_SESSION_RESERVE` 改 call 單位，預設 25 calls 約 4 則 debate，若要保留約 25 則 debate 應設約 150；`BREAK_NEWS_DAILY_MAX_DEBATES` 預設 0，只作 >0 emergency item ceiling。UI 顯示 `admission/model_capacity`。bump 3.9.3→3.9.4。

## 🟢 Session Note (v3.9.2 → v3.9.3) — Market-wide 公司名誤中修正

使用者指出 `_MARKET_WIDE_PATTERNS` 仍有低頻裸 token 誤中: `dollar` 會吃 Dollar General / Dollar Tree, `dow` 會吃 Dow Inc, `s&p` 會吃 S&P Global。修成明確宏觀/指數語境: `US dollar/dollar index/DXY`; `Dow Jones/Dow futures/DJIA`; `S&P 500/S&P futures/SPX/SPY`。避免個股公司名回流 Market Consensus。bump 3.9.2→3.9.3。

## 🟢 Session Note (v3.9.1 → v3.9.2) — Market-wide 判定收斂

Claude review 指出 V3.9.1 合理但有兩個 polish: (1) `_MARKET_WIDE_PATTERNS` 裸 `rates/oil/gold/war/yield` 太寬,會把 price war、油金個股財報、公司貸款利率等個股新聞拉回 Market Consensus,造成「過於敏感」；(2) digest pass 沒把 `affected_sectors/tickers_mentioned` 傳給 `_is_market_wide()`,導致 high-quality digest 的 multi-sector `sector_news` 比 break-news debate 更難進 market。修:收窄 regex 為 `interest rates/fed rate/rate outlook/rate cut|hike`、`Treasury yields/market/auction/selloff/retreat`、`oil prices/crude oil`、`gold prices`、`trade war/Iran war/Ukraine war`;digest sectors/tickers 包成 entities 傳入。驗證:最近 12h market events 10,合計 -3.7,未見裸 keyword 噪音回流。bump 3.9.1→3.9.2。

## 🟢 Session Note (v3.9.0 → v3.9.1) — Break News Market Consensus 校準

使用者貼圖指出 Break News 市場情緒 +0.87 明顯不合理,因當時市場已連跌三天。只讀診斷:最近 12h 有 67 個事件合計 +5.99,但多數是個股/小題材 bullish debate；同時 bearish digest 如 `Wall St futures fall...` / `oil and yield shocks` 因 `verdict=None` 被算 0；`_event_weight()` 用 signed score,負分被 clamp 到最低 0.25,低估 BEARISH。修:(1) `_event_weight()` 改 `abs(score)`,方向只由 verdict / sign 決定。(2) digest sign fallback `sign(net_impact_score)`。(3) `__ALL__` 改 Market Consensus,只吃 systemic/macro/monetary/geopolitical/broad-market headline；個股新聞仍進 sector/theme,不再等權推高 market。(4) closed debate time 優先 `source.published`,缺失才 `fetched_at`。(5) `trend-chart.js` label 改 Market Consensus / Raw Pulse,meta 顯示 `market_event_count/log_count`。驗證:最近 12h market events 67→11,貢獻 -4.2,`__ALL__` 尾端約 -0.81；Raw Pulse 獨立仍在。bump 3.9.0→3.9.1。

## 🟢 Session Note (v3.8.1 → v3.9.0) — Break News quota pacing + Raw Pulse

使用者指出 source 變多後,今日 LLM debate quota 很快燒完,後半天新聞停在 raw stream,情緒圖仍看 5-6h 前的 closed debate。Claude review 同意診斷並修正方案:raw 不應 blend 進 Market consensus,應獨立成 Raw Pulse；UTC 線性 pacing 不適合美股,改 score-ranked admission + 美股時段 reserve。實作:(1) `poller.py` 兩段式 admission:先收 raw + candidates,再依 priority(`abs(shallow_score)`, binary, credibility, 非 social, Futu tie-break, freshness)排序後消耗 budget。(2) 新 `BREAK_NEWS_SESSION_RESERVE=25`:非 07:00-18:00 America/New_York 時段最多用 `DAILY_MAX-reserve`,美股新聞時段釋放全額；state 加 `debate_candidates/auto_budget_limit/session_reserve/us_news_window_open`。(3) `store.save_raw_stream()` 預設 72h/500 筆,env 可調,支援 3 日 Raw Pulse。(4) `trend_rollup.py` 新增 `__RAW_PULSE__` kind=pulse,用 raw signed `shallow_score`,低權重、只 market-level、fingerprint 跳過 digest/closed debate,不污染 `__ALL__` consensus。(5) `trend-chart.js` 認 pulse,full selector 永遠保留「即時脈搏 / Raw Pulse」,首頁 compact 仍看乾淨 Market。驗證:py_compile ok; network dry-run ok(`auto_budget_limit=60`, `us_news_window_open=True`, `debate_candidates=22`); trend_rollup 產生 `raw_pulse_count=36`。bump 3.8.1→3.9.0。
