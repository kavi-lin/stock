# INTEL COMMAND — Backlog & Tasks

> **Last Updated**: 2026-06-13 (v4.10.0)

---

## ✅ Done (v4.10.0) — 決策中心 RWD + 三層卡片 + V3.45+ 估值欄位接通

- RWD（4K 4 欄滿版、drill overlay 改 wrap grid、<860px sidebar 收合全站生效）+ 卡片三層化（結論 strip / 理由 collapse / 證據 collapse）+ bridge.py 接 8 個 V3.45+/V5.0.x 欄位（CAP/PROBE pills 立即可見）。
- **待 user**：①實機 4K 開 decisions.html 確認無橫捲 + 欄數；②MRVL/PANW/CRWD 卡確認 ⛔ CAP pill + tooltip；③下次跑 `分析 [TICKER]`（V3.45+ engine）後確認 Layer 3 內 Range/5D Band/Implied CAGR/Archetype 4 行 advisory 出現。

---

## ✅ Done (v4.9.0) — 市場氛圍頁重設計：決策漏斗 + 川普政策雷達

- mood.html/page-mood.js 重寫：判定帶（確定性公式 0 LLM）+ Market Brief 導讀 + 3 天趨勢/regime 時間軸/每日錨點 + 盤中即時（heatmap 聚合）+ 社群貼文 feed + 川普政策雷達（TACO lexicon + 辯論 verdict 掛載）+ 辯論訊號 + 產業排行。儀表移除。brief API `?history=1`、feed projection 加 final_take。server 已重啟。
- **待 user**：①開盤時段（美東 09:30-16:00）開 mood.html 確認 LIVE 模式：判定帶出現「盤面」分項、盤中區自動展開、3 分鐘輪詢。②判定權重/±0.15 門檻若要調，改 `page-mood.js` 頂部 `VERDICT_WEIGHTS_*` 常數即可。③川普雷達目前 48h 內僅非政策類帖文 — 等有 tariff/Fed 類帖文時確認高亮 + ⚠️ flag 正確觸發。

---

## ✅ Done (v4.8.0) — Break News V6：event clustering + 嚴格 gate + Market Brief

- `cluster.py` 事件聚類（0 LLM）：echo 不重辯、sentiment 類只計數、milestone 增量追辯；debater max_rounds 3→2 + gate 只認真衝突 + `single_voice`；`market_brief.py` 每 2h 1 call 產市場現況導讀（UI 頂部面板）。估 ~261 → ~60-75 call/天（▼70%+）。
- **待 user**：①重啟 dashboard_server（新 module + brief loop + 新 API）。②**codex CLI 壞掉**（probe rc=1 `Reading additional input from stdin...`）— 修好前 break news 辯論都走 single_voice；可暫改 `llm_config.json` break_news.secondary=claude。③跑幾天後覆核 `_state.json` 的 `items_echo_merged`/`items_sentiment_clustered` 與每日 call 數，視情況調 `BREAK_NEWS_CLUSTER_SIM`（0.55）/ `BREAK_NEWS_SENTIMENT_MIN_SCORE`（3）。

---

## ✅ Done (v4.7.0) — News Protocol V2.2：script-first triage 省 token

- Stage 1 接上 `stage1_triage.py` deterministic triage（LLM 禁讀 raw.json 全文）；Stage 2 bundle 每篇 cap 5000 chars；MD shallow 20→10；protocol 563→361 行。DIGEST ~110K → ~35-40K tokens、TRIAGE ~75K → ~5K。
- server `news` / `triage` prompts 同步改 script-first（修 triage `verdicts` shape 與 validator 衝突）。
- **待 user**：重啟 dashboard_server（PROTOCOL_PROMPTS 改動）；下次 DIGEST 覆核實耗 token + shallow snaps（script template）可讀性，不滿意可開 top-10 LLM refine。

---

## ✅ Done (v4.6.2) — 取消 LLM Fallback 機制

- 取消了 `scripts/_shared/model_router.py` 中的 LLM fallback，避免在指定的 LLM 或預設 primary LLM 出現 quota 不足或錯誤時，默默回退到不符預期的模型（如 claude）。
- 同步在 `scripts/break_news/poller.py` 中更新了 `_voice_order`，以及在 `scripts/break_news/llm_drivers.py` 中更新了預設與回退配置。
- 將 `config/llm_config.json` 的 `primary` 預設配置設為 `gemini`。

---

## ✅ Done (v4.6.0) — 工作流導向 Dashboard 三 phase

- Today 工作台（/api/today + today-panel.js）/ 產出閉環（5 報告 type + Ledger panel）/ 節奏自動化（ops_auto_loop + ▶ 一鍵）全上。
- **待 user**：重啟 dashboard_server（新端點 + auto daemon）；實看 index 三卡 / ops ▶ / decisions Ledger panel。
- **未來選項（明確此輪不做）**：earnings×2 / graph vs supply-chain / news×3 頁面合併瘦身。
- **kill-trigger v2 候選**（沿 v4.5）：sector RS 謂詞、ic-memo §11 條件同步。

---

## ✅ Done (v4.5.0) — Kill-Trigger Monitor + 稽核餘留批

- **Kill-trigger monitor 上線**：`scripts/kill_trigger_monitor.py`（0 LLM）每日重檢 Red Team 推翻條件 → `Dashboard/kill_triggers.json` + index.html 紅/琥珀 banner + daily Step 9.9。**待 user 實看 banner**（今日資料：0 triggered / 3 armed / 60 manual）。
- 稽核餘留全清：thematic in-process predict ✓、earnings fetch 並行 ✓、weekly_review weights_version ✓（+ per-version 報告段）、RSI 5→1 統一 ✓、technical_core 升 _shared ✓、MARKET_INDEX 重寫 ✓。
- ~~earnings-trade-analyzer 處置~~ → **已刪（v4.5.1，user 拍板）**；event index extractor 留（讀歷史 artifact）。
- **仍待**：
  - econ-calendar 修復（FMP legacy 403；連帶發現 `/stable/rating-historical` + `/stable/grades-summary` 也 404 — earnings bundle 的 rating_history/grades_summary 長期全零）。
  - ftd/market-top 三頭 lineage 整併（sector/*_yfinance.py ↔ skills 目錄 ↔ ~/.claude 路徑）。
  - kill-trigger v2 候選：sector RS 謂詞（需 sector_intel 數值欄）、predict 端 invalidation 接入、ic-memo §11 條件同步。

## ✅ Done (v4.4.0) — Skills 稽核修復批

- 7 真 bug（ic-memo crash / decision_lock 錯 ticker / T4 不可達 / news 新鮮度閘 / retail 比對 / flag 描述 / 2 份 SKILL.md lane 契約）+ 靜默失敗 5 處 + 殭屍刪除 + 效能 5 處 + cache prune。

## ✅ Done (v4.3.0) — 知識圖譜重構：theme hub-and-spoke + 聚焦模式

- CO_THEME clique（262/280 邊）→ ~30 個 theme hub + spoke，邊 −70%；點擊改 ego 聚焦（1/2 hop）；zoom 修復（user 動手後永不 auto-fit、移除每幀漸層特效）。
- **待**：user 實測點擊聚焦 / hover tooltip / 搜尋自動完成；若主題 hub 數量仍嫌多可把 per-ticker themes 取 top-1。

---

## ✅ Done (v4.2.0) — 產業掃描頁重設計：結論→辯論→證據

- sector_intel 先前被 bridge 丟掉的 2/3 產出全部上畫面：委員會 4 lane 投票矩陣、Red Team IF/THEN 推翻條件、量化證據熱力表（PE z1y / RS 多週期 / beat rate / insider / 情緒 / FRED×）、宏觀 overlay chips + 地緣風險。
- Today's Verdict hero 補上 sector.html（原 hidden stub）；heatmap 移頁尾。
- **待**：user 瀏覽器實看驗收；下次跑「產業掃描」後確認新區塊隨新 intel 正常刷新。

---

## ✅ Done (v3.40.8) — Market Mood scoring 修正

- mood page 並非沒更新；根因是 CNN put/call fallback 被當成 raw put/call 強訊號，讓頁面長期偏樂觀。
- 已將 CNN `put_call_options` proxy cap 到 ±50 並降權，新增 F&G internals quality（breadth/strength/junk bond demand）扣分。
- 今日重產後 `Dashboard/data.json.market_mood.mood.score = 2 Neutral`。

## ✅ Done (v3.40.4) — 短期雷達：產業趨勢榜可點 → 列出**完整**成分股（finvizfinance）

- radar 產業趨勢榜每列可點 → 彈 `#ind-stock-panel` 列該 finviz 產業**完整**成分股（含小中型）。
- server 新 `GET /api/industry/<name>` → `finvizfinance` Screener by-industry（免 key）+ 12h TTL 快取 + lazy import + 驗證。
- `page-radar.js` showIndustryStocks 主打此 endpoint，heatmap 當 fallback；chip 沿用 analyze-ticker-btn；`radar.html` 加面板。
- 效果：Comm Equip 7→44 / Solar 1→22 / 半導體設備 0→29。**user server 需重啟**才有新 route；需實點驗收。

## ✅ Done (v3.40.2) — 動能選股 Journal 統計區：中文化 + 點訊號→篩選 + unknown 說明

- Journal 統計區全繁中（i18n zh+en 補 8 key + renderStats）：標題後綴 / Filled / 等待20d / Signal 表頭 /
  量能 regime trend(vol_trend_map)+stage+空狀態。
- unknown：stages_map.unknown→「資料不足」+ 主表 stage cell hover 原因（歷史<200日）。sector 已「未分類」。
  根因：stage=MA NaN（technical_core.py:259）/ sector=不在三大名單（screen.py:409）。
- 點 by-signal 績效列（已按勝率降序）→ toggle 進主表 filter（複用 filter-chip 路徑）+ 捲動 + ✓/取消。
- 純前端、零後端。驗證 node --check / 200 / data.json stats 齊全。
- **待**：user 瀏覽器實點驗收；若主表/filter 另有英文殘留補圖再翻。

## ✅ Done (v3.40.0) — AI 辦公室翻案：自主多角色協作（砍掉 3.38 PTY terminal）

- **砍 3.38 PTY 路線**（破碎 + 方向錯）。改用既有 `llm_drivers`(`-p`) + `model_router`（日預算/cooldown/fallback）→
  零新增計費面、破碎問題根除。
- `scripts/office/`：`roles.py`（Lead/Critic/Verifier = claude/gemini/codex）、`store.py`（run 生命週期 + JSONL 事件）、
  `orchestrator.py`（round-robin 自動收斂 + Lead compose 交付物 + 合作式 stop）。
- server：`/api/office/{token,runs,run/<id>,run/<id>/stream(SSE),run(POST 202),run/<id>/stop}`，single-active 409、token+Origin gate。
- `office.html` + `page-office.js`：任務輸入 → 啟動 → SSE live 角色卡 → 交付物面板 + 歷史 replay。
- 全 stub/HTTP/SSE live test 綠。
- **待辦**：(a) ⚠️ **尚未對真 CLI 跑端到端** — 要實跑驗 agy/codex 吐得出可解析 JSON envelope（否則該角色 fallback 換引擎）;
  (b) 量真實 per-run 呼叫數/耗時/預算;(c) phase-2：mid-run interject、角色 YAML、多 run 並行。

## ✅ Done (v3.38.0) — AI 辦公室 · Claude member v1（Route A persistent PTY terminal，已於 3.39 移除）

- 新 `/office.html` xterm.js terminal viewport + 後端 PTY raw byte relay（spec `docs/office_claude_route_a.md`）。
- `scripts/office/`：`pty_session.py`（互動式 claude 無 -p / sanitize env / 無 MCP config / scrollback /
  resize / lifecycle / 日界 rollover）、`ws.py`（純 stdlib 手寫 RFC6455）、`preflight_smoke.py`（Gate1 auto + Gate2 billing 手動）。
- `dashboard_server.py` office routes（token mint / status / WS relay / message·resize·lifecycle）+ token+Origin gate。
- 側欄 `工具/OPS` group + `AI 辦公室` nav。全 HTTP/WS live test 綠（cat 替身）。
- **待辦/phase-2**：(a) ⚠️ **billing gate 未實測**（RFC §1，上線前須對真帳號跑 preflight Gate2）;
  (b) 尚未對真 `claude` 跑 preflight（只測過 relay）;(c) 多行 bracketed paste;(d) 乾淨 transcript parser;
  (e) Codex/Gemini member。

## ✅ Done (v3.37.0) — 新聞 digest 全面 zh-TW（補 bridge 缺口 + 自動翻譯 hook）

- 修 3.36 隱性 bug：`bridge.extract_news` 沒帶 `*_zh` → 翻譯到不了前端。已補 6 欄。
- `news/scripts/translate_digest.py`（agy 翻 deep verdicts，idempotent + CJK-skip）+ server hook
  （news/flash_text/flash/review rc=0 後自動翻、再 bridge）。
- 查證：每日 digest 本來就中文，只翻英文 straggler；CJK-skip 讓中文 digest ~0 agy 成本。
- Follow-ups:(a) link_digest 報告 MD 仍英文;(b) 翻譯無 cache;(c) sector_view/macro_view 已備 `_zh`
  但 news 卡未渲染;(d) en 語系下 native-zh verdict 仍中文（pre-existing）。

## ✅ Done (v3.36.0) — Link Digest zh-TW 在地化（gemini/agy 翻譯）

- `scripts/link_digest/translate.py`（agy EN→zh-TW，env-gated，非致命）+ build_artifacts 接 `*_zh`
  + page-news.js news 卡依語系渲染 `_zh || base`。實打 agy 驗過。
- Follow-ups:(a) 每日 **news digest 本身仍英文**（bull_case/arbiter）— 要全站中文化需改 `news` protocol
  或加共用翻譯 pass;(b) link_digest **報告 MD 仍英文**（只翻卡片結構化欄位）;(c) sector_view/macro_view
  已翻 `_zh` 但 news 卡沒渲染這兩欄;(d) 翻譯每次跑一次 agy call（~1 call/link_digest）— 量大可考慮 cache。

## ✅ Done (v3.35.0) — Link Digest（URL → 讀全文 + 上網找相關 → 判斷 digest → 報告/新聞/KG）

- News 頁 URL 輸入框 → `link_digest` protocol（claude turn，WebFetch+WebSearch）→ 4 視角辯論
  → 同時產 reports md + digest.json verdict + bn_*.json（KG entities+relations）。
- 新檔：`news/link_digest_protocol.md`（spec）、`scripts/link_digest/build_artifacts.py`（deterministic 寫手）。
- 改：dashboard_server 註冊、news.html/page-news.js/i18n.js UI。
- web-search 廣度耦合供應鏈 edge：relation 被 ≥2 源佐證 → support_count≥2 → Nexus directed edge。
- Follow-ups:(a) 還沒實跑一條真 URL（需 tokens；寫手 e2e 已驗 rc=0）;(b) link_digest 不 patch
  sector_intel/phase0（探索層）;(c) 早於 morning news DIGEST 寫 bn 時，news run 會覆寫 digest.json（KG 不受影響）;
  (d) judgment.json `<id>` 由 LLM 命名，build_artifacts 不強制檢查 id 一致性（容錯）;(e) 可考慮 link_digest
  也吐到 trader-memory thesis registry / decisions（目前只到新聞層）。

## ✅ Done (v3.34.0) — Narrative Pulse 完整退役

- 提前退役(週末無新 sample):刪 daily `step9_narrative()`、server `/api/narrative-pulse/*`
  + SCRIPT_PROTOCOLS、`Dashboard/narrative_pulse.json`、整個 `skills/narrative-pulse-detector/`。
- 副作用:mood.html 每產業「散戶量能」label 恆 `calm`(retail aggregate.py 的 legacy NPD
  fallback 缺 cache → graceful;主 composite 不受影響)。
- Follow-ups:(a) 可順手清 `retail-sector-pulse/aggregate.py` 的 `load_npd_cache_for`/
  `aggregate_retail_volume` + SKILL.md 對 narrative 的 doc 引用(無害留著);(b) style.css
  殘留 `npd-*` class 可清。

## ✅ Done (v3.33.0) — 退役 Narrative Pulse UI + 移除散戶視角 + index 產業趨勢 mini

- index Zone B「Narrative 焦點」→ 真實「產業趨勢」mini(`renderIndustryMini`,讀
  `data.industry_trend`);移除 index 內 narrative fetch IIFE。
- radar 刪 `#npd-section` + page-radar.js NPD IIFE 死碼;刪散戶視角 `#radar-retail-sector-pulse`
  + page-radar.js retail 全套 + render 呼叫 + tooltip。mood.html 接手散戶,不受影響。
- 保留 narrative generator + server route + json(觀察期到 2026-05-31)。
- Follow-ups:(a) 觀察期 5/31 過後可決定整 feature(generator+route+json)退役;(b) index
  產業趨勢 mini 目前固定 perf_1w,可考慮跟 radar 一樣加區間 toggle;(c) style.css 殘留
  `npd-*`/`rsp-*` class 無害,日後可順手清。

## ✅ Done (v3.32.0) — Dashboard 4-zone 重構 + AI 裁決漸進揭露 + 今日焦點改造

- **index.html 4-zone**:9 stack → Zone A 指令 / Zone B `#signals-band` 3-up(合併 3 薄 strip)/ Zone C teasers / Zone D action;Structural Watchlist body 摺疊。所有依賴 ID 保留。
- **decisions.html AI 裁決卡片**:V5/Red Team/進場條件 `<details>` 漸進揭露 + Model Score 降階 + risk cap 4 + mobile grid。卡片 >800px → 大幅縮短。
- **今日焦點**:判斷=真訊號但 framing 誤導 → Top 3 + 過熱守衛 + 中性 CTA + graceful empty。
- Follow-ups:(a) decisions badge row 多 badge 仍可能 wrap,本次未 cap(保留 tooltip 綁定),需要再做 `<details>` 收納;(b) index 可考慮把 teasers + recent 進一步左欄 stack 成真 2-col(本次保留 full-width 3-up 避免左欄過擠);(c) 今日焦點守衛閾值(RSI80 / Stage3)hardcoded,日後可移 config。

## ✅ Done (v3.31.0) — 個股動向 row 可點 → inline 動能明細 + K線

- `renderStockDetail()` + `_miniSparkline()`:點 row/弱中強 chip → 區塊下方展開明細
  (30日 score sparkline + 均線排列 + RSI/MACD/RS/距高 + signals/warnings) + 看 K線
  + 完整分析 button。純讀既有 `momentum_screen` row + `history_by_ticker`,零 backend。
- Follow-ups:(a) 明細卡的「完整分析」走 protocol queue —— 留意 cost;(b) sparkline 目前
  只畫 score,可考慮加 price overlay;(c) 仍受 momentum_screen ~529 宇宙限制(小型題材股
  漏,見 v3.30 follow-up)。

## ✅ Done (v3.30.0) — 短期雷達「個股動向」panel

- radar 新 `#radar-stock-movers` 區塊 + `renderStockMovers()`:對稱領漲個股↔走弱
  個股 + 🔥強勢產業中走弱 strip。純讀既有 `data.json.momentum_screen.rows[]`
  (Weinstein stage + RS + warnings),零 backend 改動。
- 走弱判定用「Stage3/4 OR WEAK/BEARISH」(非 RS<0,避免強 SPY 盤誤標 80% 宇宙);
  弱中強用 `sector_rs_rank≤3`。
- Follow-ups:(a) momentum_screen 宇宙 ~529 (sp500/n100/sox/watchlist),小型題材股
  (含部分光通名)可能漏 — 要更廣需擴 universe 或補 thematic theme laggard_movers;
  (b) 可考慮點走弱股 drill 出 K 線 / 動能細節 (radar 已有 kline panel 可重用);
  (c) sector 縮寫對映 momentum_screen 用 GICS 名,`_SECTOR_ABBR` 是 finviz 名,部分
  GICS sector (Information Technology/Health Care/Financials) 落 fallback slice(0,4),
  顯示堪用但未完全在地化。

## ✅ Done (v3.29.0) — 短期雷達改用真實近期趨勢

- radar headline 改「產業趨勢榜 領漲↔領跌」(`#radar-industry-board` +
  `renderIndustryBoard`):真實 finviz 產業 trailing perf (theme-detector cache
  `industry_rankings`,既有但棄置) + 1週/1月/3月 toggle + 11-sector uptrend strip。
- theme card 顯示指標 forward `bullish_breadth_pct` → 真實「真實上漲率」
  (`trailing_breadth_5d_pct`) +「中位漲幅」(median 5d) + 看多/看空 badge。可看空。
- `predict.py` 加 `trailing_return_5d_pct/_20d_pct`;`screen.py` 加 `trailing` 區塊;
  `bridge.py` 加 `load_industry_trend()` → `data['industry_trend']`。
- Narrative Pulse 從 radar UI 隱藏 (`NPD_RADAR_ENABLED=false`),generator 保留。
- Follow-ups:(a) theme-detector cache 非每日強制重跑 (≤7天舊),趨勢榜目前帶
  freshness badge — 若要每日新鮮可在 daily Step6 強制 refresh;(b) Narrative Pulse
  觀察期 2026-05-31 到期後決定 generator 去留 (見 memory project note);(c) laggards
  排序目前 client 端按 active horizon,bottom list 來源是 momentum_score blend。

## ✅ Done (v3.28.0) — Market Mood 市場氛圍 page

- New page `mood.html`/`page-mood.js`: hero composite gauge + options/VIX-SKEW/F&G
  tiles + retail hot-stock strip + sentiment-first sector grid.
- `mood.py` → `market_mood.json` (VIX term structure + SKEW + put/call + F&G 7 subs).
- StockTwits social source + wider subreddits → retail coverage 41→110 posts/day.
- bridge merges `market_mood` + slim `tactical.trending`; daily step 9.3.
- Follow-ups: CBOE put/call CDN is 403-blocked (using CNN put_call sub-index
  proxy) — revisit if a clean market-wide put/call feed becomes available; wire
  StockTwits native Bull/Bear tag into trending_tickers polarity (currently in
  meta only); FMP per-stock putCallRatio corroboration tile (deferred).

## ✅ Done (v3.27.0) — Pre-Market Pipeline Redesign (FMP 250/min)

- Central cross-process FMP rate pool `scripts/_shared/fmp_pool.py`
  (flock sliding-window @ 220/min; `get`/`get_url`/`fetch_many`/`acquire_slot`).
- All 6+ FMP clients delegate pacing to the pool (300ms throttles removed,
  signatures/caches unchanged); supply_chain + dashboard count via `acquire_slot()`.
- `daily_update.sh` FMP lane parallelized (thematic ∥ momentum), workers 6→20/16.
- Morning brief `scripts/premarket/morning_brief.py` → `reports/PREMARKET_<DATE>.md`
  (step 9.8). §3 movers ranks the curated mega-cap universe (SECTOR_UNIVERSE,
  131 names, price≥$5) — drops the noisy market-wide biggest-gainers feed.
  Follow-up: optional `--llm` narrative summary.

## 📋 Open

- [ ] **[V325.X-ICMEMO-PHASE-A5] IC Memo peer_descriptor LLM swap** — replace
  the V1.0 stub at `skills/ic-memo-writer/scripts/fetch_peer_descriptor.py`
  with a real Haiku 4.5 one-shot batch call (~5-10 peers per prompt). Output
  per-peer `{focus_area, market_share_note}` written to
  `skills/ic-memo-writer/cache/peer_descriptor/<T>.json` with `status: ok`,
  TTL 14d. Trigger only when shipping/testing on 3-5 real tickers shows the
  §4 ticker-only peer table is genuinely unhelpful. Keep the shared
  `_shared/cache/` deterministic — LLM output stays in the skill's own
  cache directory.

- [ ] 🟡 **[V325.X-ICMEMO-PHASE-B] IC Memo Dashboard view（部分完成）** — `Dashboard/stock-detail.html`
  that renders the latest ic_memo MD + live FMP quote + 6-anchor bar chart
  + peer comp click-through (Nexus graph integration optional). Wait for at
  least 3 successful IC Memo runs on real tickers before designing the
  layout — current Dashboard pages tend to over-fit early use cases.
  **Partially superseded by V3.26.0 Reports Center** (`/reports.html` now
  renders IC memo MD with verdict badge + decision_lock chip + degraded
  banner + TOC). Remaining scope: live FMP quote refresh + 6-anchor bar
  chart + peer click-through.

- [ ] **[V322.X-MOM-PR2] Momentum Fundamentals PR2** — follow-up slice of
  the V3.22 fundamentals layer. Adds: ATR-normalized Gap Up detector
  (`gap_pct >= max(2%, 0.5 * ATR14 / close)` + `open > prev_high` confirm),
  `Catalyst Gap-Up` preset, sector-relative P/S percentile column,
  optional Pocket Pivot detector. Plan to ship after 1-2 weeks of PR1
  screen output so the GM% / P/S thresholds in Value Momentum can be
  calibrated against actual hit rates.

- [ ] **[V321.X-ROUTER] Model router 5hr-window counter** — `model_router.py`
  only tracks UTC-day budgets. Add rolling 5hr counter so protocol runs
  (`分析`, `產業掃描`, `新聞分析`) also self-throttle when the Anthropic
  session window is near exhaustion. Deferred from V3.21.0 — only needed if
  the hourly-cap fix doesn't fully prevent the next quota incident.

- [ ] **[V325.X-PE-WARMUP-RETRY] heatmap PE warm-up should retry on failure** —
  `dashboard_server._heatmap_refresh_pe_universe()` runs once on startup with
  a 24h TTL. If it errors mid-batch, the in-memory cache stays empty until
  the next server restart, and heatmap.json (+ everything joined from it,
  including momentum-screen P/E) renders blank. V3.25.2 added the manual
  rescue `scripts/backfill_heatmap_pe.py`; the real fix is making the
  daemon retry-on-failure or re-attempt every N hours when the cache is
  still partially empty. Schedule separately from the V3.25.2 hot-fix.

## ✅ Recently Completed

> 完成項詳見 `CHANGELOG.md`（version history 權威來源）+ 頂部「✅ Done (vX)」區塊；更舊細項見本檔末「📦 已完成任務詳情」。此區先前逐條 [x] 清單與上述兩處重複，已整併移除。

---

## 🎯 活動 Backlog (Pending)

### 路線 RSP — Retail Sector Pulse 後續

- [x] ~~**[RSP-1] 擴 NPD universe 含 SECTOR_TOP_5**~~ — 廢棄：依賴 narrative-pulse `batch_scan.py`，該 skill 已於 v3.34.0 整套退役/刪除，項目無效。
- [ ] **[RSP-2] V3.21 — Intraday 4h refresh daemon** — dashboard_server.py 加
  daemon thread 每 4h 重跑 `aggregate.py`。沿用 break_news daemon pattern。
  V3.20 跑 1-2 週後評估必要性再做。
- [ ] **[RSP-3] V3.22 — LLM-enriched framing** — Haiku 4.5 對 rule-based
  framing 做一句潤色(11 call/day,~$0.01)。權衡:LLM dependency vs 自然語感。
- [ ] **[RSP-4] V3.23 — Per-sector FTD pattern** — sector ETF (XLK/XLF/...)
  FTD state machine,類似 SPY ftd_yfinance.py。 sector 級 "follow-through
  day" 信號。
- [ ] **[RSP-5] Weekly review hit rate** — `scripts/retail_sector_pulse_review.py`
  比 composite_score 預測方向 vs 後續 5d sector ETF 實際 return,計算 IC。

### 路線 NP — Narrative Pulse V1.1 後續 ⚪ 整路線廢棄

> narrative-pulse-detector 已於 **v3.34.0 整套退役/刪除**（skill 目錄、generator、route、snapshots 全清；memory 註記「勿重啟」）。以下三項全讀已不存在的檔，永久無效。

- [x] ~~**[NP-1]** Dashboard hover tooltip（prob/target breakdown）~~ — radar NPD UI 已清。
- [x] ~~**[NP-2]** 5/31 review script（讀 narrative-pulse snapshots）~~ — 目錄已刪、不再產 sample。
- [x] ~~**[NP-3]** Stage 2/4/5 adjustment 校準~~ — feature 不存在。

### 路線 BN — Break News source expansion

- [ ] **[BN-1]** Optional paid/token adapters：X recent search / Product Hunt / official Google Trends API alpha。只在 user 提供 token 或明確接受成本後接入。
- [x] **[BN-2]** ~~Stocktwits adapter~~：V3.40.7 移除（噪訊比過低，~5% 才成 primary source）。改補 Fed Press / Nasdaq Markets / Benzinga RSS。
- [ ] **[BN-3]** Social source quality backtest：比較社群 raw item 被手動辯論後的 verdict hit-rate，調 `BREAK_NEWS_SOCIAL_GATE_MIN_SCORE`。

### 路線 V20 — V2.20 規劃 ⭐ 焦點

**前提**：V2.18 (Structural Shift Modulation) + V2.19 (Lane Cross-Talk Wiring) + V2.19.1 (Watchlist Archival) + V2.19.2 (UI ⚡ + Backtest forward returns + Theme heat bonus) 已完工。下一階段 **聚焦 UI 補齊 + Backtest 深化**，**不搶做需 backtest 結果的功能**。

#### V2.20.0 — 1-2 週可做（低風險）

##### A. UI Decision Layer 完整化

- [ ] **[V20-A1]** Polarization 4-tier badge in `decisions.html` — `det_shadow.signal_polarization` (BIPOLAR/OUTLIER/MIXED/ALIGNED) 已存 data.json，UI 沒秀
- [ ] **[V20-A2]** Red Team basis badge in `decisions.html` — `red_team_basis` (pure_forward/pure_mean_reversion/contaminated/unclassified) 已存，user 看不到 anti-spoofing 偵測結果
- [ ] **[V20-A3]** structural_shift tier badge in earnings card (`page-earnings.js`) — CANDIDATE/CONFIRMED 視覺化
- [ ] **[V20-A4]** Theme-detector structural_shift override icon in `sector.html` — `tier_counts` 已寫進 theme JSON
- [ ] **[V20-A5]** `bridge.py` 加 polarization / red_team_basis 注入 `recent_analysis[]` — 給 A1/A2 用

##### B. Backtest 深化（先補分析維度，accrual 等不及）

- [ ] **[V20-B1]** Random sector baseline 對照 — 現在 alpha vs SPY 看起來好 (+18.4% mean) 但可能只是 Memory Semi sector momentum，需 random 同 sector 5 ticker baseline 驗證 watchlist 真的 outperform
- [ ] **[V20-B2]** Per-keyword breakdown — 14 個 keyword 哪幾個是 noise (e.g. "supply tight" 通用)？哪幾個是 signal (e.g. "supercycle" 罕見)？砍 noise 提訊噪比
- [ ] **[V20-B3]** Per-credibility 切片 — HIGH 命中 alpha vs MEDIUM 有差嗎？沒差 → credibility 是 false signal
- [ ] **[V20-B4]** Time-window sweep — 5d/15d/45d/90d 哪窗 alpha 最高 → 決定 optimal hold horizon

##### C. Decision Logic 小修

- [ ] **[V20-C1]** Dynamic decision threshold — BUY≥1.2 / STAGED≥0.8 是死的。CONFIRMED + ALIGNED → BUY 降到 1.0；BIPOLAR + chaotic → BUY 拉到 1.5
- [ ] **[V20-C2]** (可延後) Lane freshness weighting — News 48h vs Earnings 80d 同權重不對；lane cache mtime > N 天 → confidence ×0.8

##### D. UX 補齊

- [ ] **[V20-D1]** Watchlist tile 顯示 lifecycle 軌跡（first_seen / 已 graduated / evicted）— 給 user 一目了然每個 watchlist ticker 軌跡
- [ ] **[V20-D2]** `backtest_watchlist.py` 加 `--dry-run` flag

#### V2.20.X — 3-4 週後可做（需 watchlist accrual）

##### E. Backtest 真實驗證（必須等 lifecycle log 累積）

- [ ] **[V20-E1]** lifecycle ≥ 30 events，覆蓋 ≥ 3 sector → 跑完整 backtest 驗 signal 非 lookback bias
- [ ] **[V20-E2]** ≥ 5 個 evicted_no_graduation 樣本 → 算 false positive rate；rate > 50% → 砍 keyword whitelist 或廢 watchlist 概念
- [ ] **[V20-E3]** ≥ 3 個 自然 graduated_confirmed → 算真 lead time（不是 lookback 假 17 天）

##### F. Phase 5.5 Cross-Protocol Wiring

- [ ] **[V20-F1]** `thesis_registry` concentration check — Phase 4 sizing：同 sector ≥3 active CONFIRMED → 第 4 個減半。防 sector concentration risk
- [ ] **[V20-F2]** Sector protocol 讀 thesis_registry 反向加權 — `sector_intel.json` 加 `active_thesis_count[sector]`，下次 sector 跑時 sector heat 拉

#### V2.21+ — 大改，**不要塞 V2.20**

- [ ] **[V21-G1]** News provisional → 直接驅動 tier modulation — 必須先 V2.20.X backtest 證明 watchlist signal 質量
- [ ] **[V21-G2]** Modulation 參數 auto-calibration（V2.18 ×0.3 PT / 0.5 RT 折半 / 0.95 floor / 50% cap 全是猜）— 需 backtest sample n>50
- [ ] **[V21-G3]** macro_multiplier sector × duration sensitivity matrix — 5+ 年 macro/sector data + multicollinearity 處理，**不是兩週工作量**
- [ ] **[V21-G4]** Position size 連續 sizing（取代 binary tier cap）— 需 G2 結果
- [ ] **[V21-G5]** Phase 3 Step 1.5 + 1.7 modulation cap 改 backtest 校準值 — 需 G2

#### 紀律提醒

1. **V2.20 不能塞 News provisional → tier modulation**（G1）— V2.18+V2.19 anti-spoofing 鐵律寫過：未經 backtest 驗證的 leading signal 不能進決策層
2. **V2.20 不能搶 parameter calibration**（G2）— sample 不足會把噪音當 signal 寫進公式
3. **V2.20 焦點 = UI surface + backtest signal 拆解**

### 路線 H — thematic-screener v0.3 enrichment 後續
- [ ] **[H-1]** Backtest v0.2 vs v0.3：過去 30d/60d 推薦在 5d realized return / hit-rate 上差異
- [ ] **[H-2]** 加 Finnhub `/stock/recommendation-trends` 補充 grades-historical（更詳細買賣評等 distribution）
- [ ] **[H-3]** 加 short interest / days-to-cover label（目前只用 quality 不看 short crowding）
- [ ] **[H-4]** Tune `enrichment_multiplier` 加成係數 — 目前憑直覺設（earnings ×0.5 / quality ×0.6 / insider ×1.3 等），backtest 後校準

### 路線 G — FMP catalog 二階強化（v2.11.0 後續）
- [ ] **[G-1]** theme-detector 切 FMP-primary：`theme_detector.py:479` import 改 `fmp_industry_perf_client` 為主、`finviz_performance_client` 為 Tier C fallback。先 user review `skills/theme-detector/scripts/industry_name_mapping.yaml` accuracy。
- [ ] **[G-2]** FMP industry rolling perf 多週期 (1m/3m/6m/1y/ytd) — 改用 `historical-industry-performance` per industry 取代每日 snapshot 累積（API call 從 ~252 降到 ~128，且支援 compound 而非 sum）
- [ ] **[G-3]** sector-analyst overlay 進 sector_protocol Phase 4 估值面 rubric — 目前 `fmp_overlay` 只是輸出，未進決策邏輯
- [ ] **[G-4]** 71 finviz-only industries 二次審視 — Internet Retail / Department Stores / Confectioners / Beverages-Brewers / Textile / Pharmaceutical Retailers 等可能 FMP 用其他名稱包進去（如 "Software - Services" 包 Amazon？）
- [ ] **[G-5]** technicalIndicators FMP 整合 — momentum-monitor + technical-analyst 改吃 FMP RSI/SMA/EMA/ADX 直接結果，省 OHLC fetch + 跨 skill 一致性
- [ ] **[G-6]** commitmentOfTraders macro overlay → sector Phase 0（期貨籌碼信號目前完全空白）
- [ ] **[G-7]** marketHours 預檢 → `daily_update.sh` 跳過 NYSE 假日（目前盲跑）

### 路線 F — Finnhub 整合
- [ ] **[F-PR4]** `skills/data-client/`：按資料種類路由 provider（market→Finnhub / financials→FMP / events→Finnhub-only / econ→FMP-only），加 `_source` tagging + conflict detection
- [ ] **[F-PR5]** 遷移 `ftd-detector` 到 data-client（最低風險 pilot）
- [ ] **[F-PR6]** 遷移 `market-top-detector` + `us-stock-analysis`
- [ ] **[F-PR7]** 啟用新功能：`earnings-calendar` skill 修好（Finnhub `/calendar/earnings`）、`pead-screener` 啟動（`/stock/earnings` surprise）、新增 `insider-monitor` skill

### 路線 B — Calendar 頁面（事件日曆補充與自動化）
- [ ] **[B-DAILY]** `daily_update.sh` 加 Step 7：跑 indexer + render markdown

**Upcoming events feeds — 補充事件源（Tier 2 & 3）**
- [ ] **[B-FEED-OPEX]** Options expiry calendar（每月第三個週五 + quarterly）→ 純算式生成，category=`system`，impact=`med`，給 risk_flags 用
- [ ] **[B-FEED-INDEX]** Index rebalance dates（S&P 季末 / Russell 6 月）→ 硬編，category=`system`
- [ ] **[B-FEED-TREASURY]** Treasury auctions（FMP 或財政部 RSS）— 做 fixed income / 殖利率部位才補
- [ ] **[B-FEED-DIVIDENDS]** Finnhub `/calendar/dividends` — kanchi-dividend-sop 已用，整合進 upcoming_events
- [ ] **[B-FEED-IPO]** Finnhub `/calendar/ipo` — IPO 投機部位才補
- [ ] **[B-FEED-FED-WEB]** WebFetch Fed 官網 `/newsevents/calendar.htm` — 比 YAML 更即時（YAML 補不到的臨時 speeches）
- [ ] **[B-FEED-POLICY]** WebFetch 白宮/USTR 公告 — tariff / executive order

### 路線 C — Positions Tracker 強化
- [ ] **[C-IMPORT]** `import_firstrade_csv.py` — 解析 Firstrade 月結單 CSV → `positions.json`
- [ ] **[C-ADD]** 同一 ticker 加碼時提示「併入現有 avg cost」vs「另開 lot」兩個選項

### 路線 FE — Fincept Strategy Extraction（短期訊號強化）
- [ ] **[FE-A1]** 提取 `momentum.py` 三層訊號：Optimal Lookback、Trend Strength、Acceleration → `skills/short-term-target/scripts/momentum_signals.py`
- [ ] **[FE-A2]** 提取 `mean_reversion.py` 三層指標：Z-score、Hurst exponent、OU half-life → `skills/short-term-target/scripts/mean_reversion_signals.py`
- [ ] **[FE-A3]** 整合 A1+A2 到 `predict.py`：新增 `fincept_momentum` + `fincept_mean_reversion` 特徵與權重
- [ ] **[FE-A4]** `statistical_arbitrage.py` regime detector → 接進 `predict.py` regime filter
- [ ] **[FE-B1]** 實作 `skills/earnings-quality-analyzer/scripts/quality.py`：Beneish M-Score、Accrual Ratio 等 6 指標
- [ ] **[FE-B2]** 實作 `skills/earnings-quality-analyzer/scripts/ratios.py`：多年度 key metrics 趨勢
- [ ] **[FE-B3]** Protocol 整合：Phase 2 Burry inline 新增 `quality_label` 欄位與罰則
- [ ] **[FE-C1]** 評估 `indicators.py` 的 Hurst + RSI + ADX 是否接進 `technical-analyst`

### 路線 D — 效能優化（低優先）
- [ ] **[ARCH-11]** `lucide.createIcons()` debounce（`requestAnimationFrame` 批次）
- [ ] **[ARCH-12]** Chart.js 惰性載入
- [ ] **[ARCH-13]** marked.js 惰性載入
- [ ] **[ARCH-14]** `innerHTML` XSS 防護全面套用

---

## 📦 已完成任務詳情 (Archived Tasks)

### 路線 SS — Structural Shift Modulation (V2.18 → V2.19.2)
- [x] ~~**[SS-V2.18-EARNINGS]** `earnings-analyst/scripts/analyze.py` `compute_structural_shift()` — EPS QoQ ≥30% + GM ≥hist+2σ + rev YoY accel → tier NONE/CANDIDATE/CONFIRMED~~
- [x] ~~**[SS-V2.18-PHASE3]** Phase 3 Step 1.5 modulation：CONFIRMED 解除 analyst-PT/sector_avoid/RT mean-reversion；CANDIDATE 折半 + cap 50%~~
- [x] ~~**[SS-V2.18-THEME]** theme-detector `lifecycle_calculator.classify_stage` 加 `fundamental_override`：paradigm-shift sector 不誤判 Exhausting~~
- [x] ~~**[SS-V2.18-REGISTRY]** `register_thesis.py` 接收 structural_shift 進 thesis_data~~
- [x] ~~**[SS-V2.19-POLAR]** `compute_polarization` 升 4-tier (BIPOLAR/OUTLIER/MIXED/ALIGNED)，BIPOLAR 加 direction count 條件防 4-vs-1 outlier 誤判（Gemini case `[+4,+3,+3,+2,-2]`）~~
- [x] ~~**[SS-V2.19-RTBASIS]** Red Team anti-spoofing classifier：pure_forward / pure_mean_reversion / contaminated / unclassified；CONFIRMED 下 contaminated 視同 mr 觸發降級~~
- [x] ~~**[SS-V2.19-PHASE3-1.7]** Phase 3 Step 1.7 polarization modulation：BIPOLAR ×0.5 conf+cap25 / OUTLIER ×0.85 / MIXED ×0.75~~
- [x] ~~**[SS-V2.19-RTPROMPT]** Phase 2.8 Red Team prompt 加 STRUCTURAL_SHIFT_TIER input + 條件指令~~
- [x] ~~**[SS-V2.19-WATCHLIST]** News Phase 4.5 structural_watchlist：14d hit window + 21d eviction + ≥2 sources gate + dedup~~
- [x] ~~**[SS-V2.19-DAILY]** `daily_update.sh` Step 7 接線~~
- [x] ~~**[SS-V2.19-VALIDATOR]** `validate_v219.py` 16 fixture (含 Gemini outlier + contamination spoof)；`validate_session_export.py` 加 polarization + red_team_basis enum 檢查~~
- [x] ~~**[SS-V2.19.1-ARCHIVAL]** `build_structural_watchlist.py` 加 daily snapshot (`watchlist_history/`) + append-only `watchlist_lifecycle.jsonl` + 5-event enum (first_seen/continued/evicted/graduated_candidate/graduated_confirmed)~~
- [x] ~~**[SS-V2.19.1-BRIDGE]** `bridge.py` `load_structural_watchlist()` 注入 `data.json.structural_watchlist`~~
- [x] ~~**[SS-V2.19.1-UI]** Dashboard `index.html` Layer 5 watchlist tile + `script.js` `renderStructuralWatchlist()` + audit card ⚡ badge + i18n 4 label~~
- [x] ~~**[SS-V2.19.1-BACKTEST-SKEL]** `backtest_watchlist.py` skeleton：tier graduation rate + lead time stats + outcome 4-classify~~
- [x] ~~**[SS-V2.19.2-UIBADGE]** decisions.html / earnings.html 個股名旁 ⚡ amber badge if ticker ∈ watchlist~~
- [x] ~~**[SS-V2.19.2-FORWARD-RETURNS]** `backtest_watchlist.py` 補完 forward returns：FMP `/stable/historical-price-eod/light` + SECTOR_ETF_MAP (13 sector) + α_SPY + α_sector + 4 horizon (5/15/45/90d) + 15d alpha aggregate~~
- [x] ~~**[SS-V2.19.2-HEAT]** theme-detector `calculate_theme_heat` 加 `structural_shift_bonus` (+0/+5/+10/+15)，AI&Semis heat 52.8→62.8 + ranking 動 (V2.18 只動 stage label)~~

### 路線 F — Finnhub 雙抓架構
- [x] ~~**[F-PR1]** `skills/finnhub-client/`：60/min throttle + cache + retry + 17 endpoints + 5 個 FMP-shape adapter~~
- [x] ~~**[F-PR2]** `skills/finnhub-client/scripts/diff_tool.py` + `run_diff.sh`：Finnhub vs FMP 對照~~
- [x] ~~**[F-PR3]** 修正 FMP v3→stable 端點 + adapter + dual_fetch.py 設計~~
- [x] ~~**[F-PR4.5]** 把 dual_fetch 接進 investment_protocol Phase 1 (V4.8.1)~~
- [x] ~~**[F-PR4.6]** 端到端驗證：AMD 分析驗證，7/7 條件全 PASS~~

### 路線 ST — Short-Term Target System
- [x] ~~**[ST-Step1]** `short-term-target` skill：1d/5d/15d 預測模型與權重配置~~
- [x] ~~**[ST-Step2]** 加新主題到 `cross_sector_themes.md` (17→21)~~
- [x] ~~**[ST-Step3]** `thematic-screener` skill 實作~~
- [x] ~~**[ST-Step4]** Dashboard `radar.html` 短期雷達頁完成~~
- [x] ~~**[ST-Step5]** Outcome tracking log 自動化儲存~~
- [x] ~~**[ST-Step6]** `daily_update.sh` 整合自動跑~~
- [x] ~~**[ST-Step7]** `weekly_review.py` 每週末校準工具~~

### 路線 S — Skill 建立與 Review
- [x] ~~**[S-BUILD-01~04]** 建立 Sentiment, Tail-Risk, Portfolio, Burry 4 個核心 Skill~~
- [x] ~~**[S-COPY]** 遷移既有 Skill 至 `skills/` 目錄~~
- [x] ~~**[S-REVIEW-01~05]** 全量 Skill 驗證與閾值校準，完成 NVDA 整合測試~~

### 路線 N — News Protocol V2
- [x] ~~**[N-PROTO]** 草擬 `news_protocol_v2.md` (RSS 兩階段漏斗 + 5 Agent)~~
- [x] ~~**[N-RSS]** 撰寫 `fetch_news_rss.py` (去重 + 多源)~~
- [x] ~~**[N-ARCHIVE]** 歸檔 V1 協議~~
- [x] ~~**[N-CLAUDEMD]** 更新 `CLAUDE.md` 版本至 1.7.0~~
- [x] ~~**[N-DASH-BTN/NEWS]** Dashboard 整合 FLASH 按鈕與 DIGEST 複製功能~~
- [x] ~~**[N-TOAST/I18N/BRIDGE]** 支援 Toast 通知、多語系與 bridge.py v2 欄位~~

### 路線 B — Calendar 頁面與 Feed
- [x] ~~**[B-BRIDGE]** `bridge.py` 整合 `aggregate_upcoming_events`~~
- [x] ~~**[B-PAGE]** 建立 `calendar.html` 月曆、詳情面板與 LLM Review~~
- [x] ~~**[B-SKILL]** 整合 `earnings-calendar` (FMP API) 至 bridge~~
- [x] ~~**[B-MILESTONE1]** Event index milestone 1 樣本提取與規則~~
- [x] ~~**[B-INDEXER]** 全量 indexer `build_event_index.py` 實作~~
- [x] ~~**[B-SCHEMA]** UpcomingEvent 統一 schema 與跨頁面整合~~
- [x] ~~**[B-PROMPT]** Sector-protocol prompt 改寫與 `upcoming_events` 輸出~~
- [x] ~~**[B-FEED-FED-YAML]** 整合 FED FOMC 日曆~~
- [x] ~~**[B-FEED-EARNINGS]** 整合 FMP 財報日曆 (Top 50 tickers + $500M filter)~~
- [x] ~~**[B-FEED-ECON]** 整合 FMP 經濟指標日曆 (High Impact Only)~~

### 路線 P — 富途牛牛推播整合
- [x] ~~**[P-TICKER]** `parse_futu_notifications.py` 實作~~
- [x] ~~**[P-BACKEND]** Server lazy-fetch + 5s cache 實作~~
- [x] ~~**[P-CARD]** Dashboard 即時通知卡片實作~~

### 路線 C — Positions Tracker 強化
- [x] ~~**[C-CLOSE]** Dashboard 平倉動作實作 (exit_price + realized_pl 紀錄)~~

### 路線 I — Invest Protocol V4.8 (API 化)
- [x] ~~**[I-PA]** dual_fetch.py 擴充至 15 scalar 欄位~~
- [x] ~~**[I-PB]** Sentiment lane：Insider 統計與 Short Interest 介接~~
- [x] ~~**[I-PC]** News lane：Analyst Ratings & Price Targets 結構化 API~~
- [x] ~~**[I-PD]** Phase 0 L3 Fallback 改用 Skill Chain~~
- [x] ~~**[I-PE]** Phase 0 Schema 明列關鍵指標，減少 Phase 2 重抓~~
- [x] ~~**[I-PF]** Phase 2 共通 prompt 導入 Web Search 白名單~~
- [x] ~~**[I-PG]** Technical lane：yfinance OHLC 換成 FMP stable API~~

---

## ✅ 已完成歷史紀錄 (Summary)

- **Dashboard 強化**：`calendar.html` 全功能實作、`page-decisions.js` 平倉邏輯。
- **Data Feeds**：FMP API 全面替代 WebFetch、Upcoming events 統一 Schema 化。
- **Tactical Radar**：1d/5d/15d 短期預測系統上線。
- **V4.6 投資協議**：雙軌 entry、STAGED 狀態、Consensus bonus。
- **Sector Protocol V1.2**：主子檔拆分、三層訊號合成、決策樹。
- **Server 與 Infrastructure**：dashboard_server.py CRUD、自動 mtime cache-busting。
- **V2.18 Structural Shift Modulation**：MU/QCOM 超級週期錯失 systemic fix；earnings tier (NONE/CANDIDATE/CONFIRMED) → Phase 3 Step 1.5 modulation 解除 backward-looking lane 三重壓制。
- **V2.19 Lane Cross-Talk Wiring**：polarization 4-tier (含 OUTLIER 防 4-vs-1 誤判) → Step 1.7 modulation；Red Team anti-spoofing classifier (contaminated 不是 mixed) → mr 一票否決；structural_watchlist 14d/21d decay。
- **V2.19.1 Watchlist Archival**：daily snapshot + append-only lifecycle log（5 event enum），建立 backtest 基礎建設。
- **V2.19.2 UI + Backtest Forward Returns**：⚡ badge 跨 3 頁；FMP price + SPY/sector ETF α；theme heat bonus 動 ranking（不只 stage label）。
