# Session Notes 歸檔 v3.31.0 → v3.40.2（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v3.40.2) — 動能選股 Journal 統計區：中文化 + 點訊號→篩選 + unknown 說明

接 user 反映「動能選股下面那張圖（Journal 統計區）是英文、有 unknown 看不懂、想點訊號直接篩選」。
調查後確認：by-signal 表**本來就**按勝率降序 + 訊號名已翻；真正缺的是殘留英文 + unknown 說明 + 點擊互動。

範圍（皆取輕量、純前端）：
- **翻譯**（`i18n.js` zh+en 補 8 key / `page-momentum.js` renderStats）：by-signal 標題後綴（原 zh 還重複疊英文 `(20d win rate)`）、
  `Filled:`、等待 20d、`Signal` 表頭、量能 regime 的 expanding/stable/contracting（新 `vol_trend_map`）+ stage（走 stages_map）+ 空狀態。
- **unknown**：`stages_map.unknown`「未知」→「資料不足」；主表 stage cell hover 出原因（歷史<200日）。sector 已「未分類」。
  根因記錄：stage unknown = MA20/50/200 任一 NaN（`technical_core.py:259`）；sector Unknown = 不在三大名單（`screen.py:409`）。
- **點訊號→篩選**：by-signal 列可點 → toggle `_state.filter.requiredSignals`（複用 filter-chip 路徑）→ 重繪主表 + 捲動；
  已選 ✓、再點取消。table-section 與 journal-section 同頁並列（非互斥 view），故只捲動不切 view。

決策（問過 user，全取建議/輕量）：勝率用既有全史 stats.json（不加近窗）、點列 toggle（不做 Top-K preset）、
unknown 純前端 relabel+tooltip（不動後端 sector 補值）。

驗證：node --check 全過；/momentum.html 200；data.json by_signal=17 / by_volume_regime=99 / 20d fills=16565；
4 筆 unknown stage + 1 筆 Unknown sector 可驗。版本 3.40.2 三處同步。

⚠️ 待 user 在瀏覽器實點驗收（headless 無法點）。三張圖未附，以「下面那張=Journal 統計區」為準（user 已確認）；
若主表/filter 面板另有英文殘留，補圖再一併翻。

## 🟢 Session Note (v3.40.1) — Weekly REVIEW 回測檢討：drawdown surface + news parser 修復

針對 0531 LLM REVIEW（`REVIEW_2026-05-31.md`）的 READY items 執行回測檢討。共 4 個 READY：
TODO-005（drawdown surface）/ TODO-001 / TODO-002（protocol threshold）/ TODO-008（news parser）。

**做了什麼（問過 user，選 005 + 008）**：
- **TODO-005 → Rec 9**（`scripts/build_event_index.py`）：reality 加 `max_runup_pct` /
  `max_drawdown_pct`（從 decision price 換算 pct；原 `max_*_since` 是絕對價格不可讀）；
  deep-dive verdict 注入兩欄；rollup miss 區加 `avg_miss_drawdown_pct` / `worst_miss_drawdown_pct`。
- **TODO-008 → Rec 4 resolved**（`scripts/extractors/news_digest_extractor.py`）：10-pattern
  ladder 換單一 tolerant regex。news-digest macro_delta null **35% → 2.5%** (14→1)，零 regression。

**關鍵發現（drawdown 解開謎團）**：負 avg_miss_return 之謎 = rollup 對 HOLD-miss（正值）+
BUY-miss（負值）不分方向混算的 artifact。surface drawdown 後：**Semiconductors HOLD/CANCEL
miss avg_ret +33.86% vs avg_dd 僅 -3.26%** → 真錯過上漲、caution 不成立、**H1 確認**。

**刻意不做（紀律）**：TODO-001/002 protocol decision threshold（`investment_protocol_v5_0.md:851-857`
HOLD = score ∈ [±0.8]）**本週不改**。改 threshold 前須走完 drawdown 資料 → 下週 REVIEW 重評 →
promote-to-ledger 迴圈，避免盲改誤殺避損 HOLD。blocker 已清，候選方向（score [0,0.8) +
top30 + RISK_ON/BULL → STAGED_ENTRY probe）已寫進 TODO-001/002 evidence。

event_index 已 rebuild（271 records）反映兩項修復。

## 🟢 Session Note (v3.40.0) — AI 辦公室翻案：自主多角色協作（砍掉 3.38 PTY terminal）

**user 回饋翻案**：3.38 的 PTY terminal「效果奇差、畫面破碎」，而且**本來就不是要 terminal** —
要的是**多角色自動協同工作**，需要 persist 的互動式 UI 來驅動/觀察。terminal 是我把手段當目標。

決策（問過 user）：多 CLI 真分歧 / 通用辦公任務 / 全自動到產出。

**關鍵發現**：專案**早就有** programmatic 多 agent 引擎 — `scripts/break_news/llm_drivers.py`
（`run_claude`=`claude -p --output-format json`、`run_gemini`=`agy --print`、`run_codex`=`codex exec --json`）
+ `scripts/_shared/model_router.py`（角色鏈 + 每模型日預算 + cooldown + fallback），Break News 每天在跑。
→ 直接長大這個，**不用 PTY、不用 WS、破碎問題從根消失**，且因 reuse 既有 `-p` driver **零新增計費面**
（3.38 RFC §1 的計費焦慮對本專案根本不成立 — 早就在用 `-p`）。

砍掉：`scripts/office/pty_session.py` / `ws.py` / `preflight_smoke.py` / `config/office_claude/`。
新增：
- `scripts/office/roles.py`（Lead=claude 主筆 / Critic=gemini 挑戰 / Verifier=codex 佐證，通用領域中立，JSON envelope 契約）
- `scripts/office/store.py`（run 生命週期 `reports/office/<run_id>/`：meta.json + events.jsonl append-only + deliverable.md）
- `scripts/office/orchestrator.py`（round-robin 迴圈 → run_with_fallback → 收斂(全員 done/輪數/wall/預算) → Lead compose 交付物；合作式 stop）
- `dashboard_server.py` office routes（token/runs/run/<id>/SSE stream/run start 202/stop；single-active 409 guard；token+Origin gate）
- `Dashboard/office.html` + `page-office.js`（任務輸入 + 啟動/停止 + SSE live 角色卡 + 交付物面板 + 歷史 run replay）

驗證：roles/store/orchestrator 邏輯（stub 引擎：收斂/事件/交付物/spend/stop 全綠）+ 全 HTTP/SSE live test
（token gate 403 / run 202 / dup 409 / SSE 全程 replay+end / 交付物 / runs list 全綠）。版本 3.40.0 三處同步。

⚠️ **待辦**：(a) **尚未對真 claude/agy/codex 跑端到端**（只用 stub 測編排）— 要實跑一次驗 agy/codex 真會吐
可解析 envelope（不然該角色會 fallback 到別引擎）;(b) 全自動跑一輪量出真實 per-run 呼叫數/耗時/預算衝擊;
(c) phase-2：mid-run interject（user 選全自動，暫不做）、可設定角色 YAML、多 run 並行。

## 🟢 Session Note (v3.38.0) — AI 辦公室 · Claude member v1（Route A persistent PTY terminal，已於 3.39 移除）

實作 `docs/office_claude_route_a.md`。定位：drawer 內是真 **xterm.js terminal viewport**，後端純 PTY raw
byte relay（`claude` 無 inline，永遠 alt-screen TUI，scraper 是死路）。v1 **只做 Claude member**。

決策（問過 user）：(1) transport = **手寫 WebSocket** 直接 bolt 在既有純 stdlib `ThreadingHTTPServer`
上（無新依賴、無 async refactor；SSE+POST 對終端機太 laggy）;(2) scope = **minimal Claude-only page**
（新 `office.html`，不先做 multi-member shell）。

交付：
- `scripts/office/pty_session.py`（PtySession：pty.openpty+Popen 起互動式 claude **無 -p**，sanitize nested env，
  注入 `CLAUDE_CONFIG_DIR=config/office_claude` 無 MCP，bounded scrollback + reconnect replay，resize TIOCSWINSZ，
  clear/restart/stop，Asia/Taipei 日界 rollover）
- `scripts/office/ws.py`（純 stdlib RFC6455 server：handshake+frame codec+續傳+thread-safe send）
- `config/office_claude/settings.json`（無 MCP、default permission mode）
- `scripts/office/preflight_smoke.py`（Gate1 啟動健檢 auto / Gate2 billing **手動 checklist 不 auto-pass**）
- `dashboard_server.py` office routes（token mint / status / WS relay / message·resize·lifecycle）+ token+Origin gate
- `Dashboard/office.html` + `page-office.js`（xterm CDN + WS client + 控制鈕）+ 側欄 `工具/OPS` group nav

安全：127.0.0.1 + per-process session token（hmac.compare_digest）+ Origin allowlist；**不** bypassPermissions。

驗證：ws frame round-trip + PtySession（cat 替身）lifecycle + 全 HTTP/WS live test 全綠
（token mint / token gate 403 / origin gate 403 / WS 101 / 雙向 PTY echo / resize / lifecycle）。

⚠️ **未做/待辦**：(a) **billing gate 未實測** — RFC §1 計費前提仍未驗，正式上線前須跑 preflight Gate2 對真帳號確認
訂閱有扣、Agent-SDK credit 沒動;(b) 多行貼上 bracketed paste = phase 2;(c) 乾淨 transcript parser = phase 2;
(d) Codex/Gemini member 各自 smoke 後再加;(e) 尚未對真 `claude` 跑過 preflight（只用 cat 替身測 relay）。

## 🟢 Session Note (v3.37.0) — 新聞 digest 全面 zh-TW（補 bridge 缺口 + 自動翻譯 hook）

接 3.36。user 要「都上中文翻譯」。**查證翻案**：每日 news digest（05-27/28/29）的 bull_case/arbiter
**本來就是中文**（news protocol 中文輸出，native-zh=5/5），只有今日 1 筆偶發英文 + link_digest/flash 英文。
所以重點不是「全翻」，是「補英文 straggler + 確保 zh 欄位流到前端」。

**抓到 3.36 的隱性 bug**：`bridge.extract_news()` 只挑特定欄位建 news item，**沒帶 `*_zh`** →
3.36 的 link_digest 翻譯欄位**根本到不了前端**（page-news 讀的是 data.json，永遠 fallback 英文）。已補。

做的：
- `bridge.py`：news item 補 6 個 `*_zh` 欄位 → data.json 帶 zh。
- `news/scripts/translate_digest.py`：翻一份 digest 的 deep verdicts → `*_zh`（重用 translate_to_zh，
  單批次 agy，idempotent + **CJK-skip**：已中文欄位跳過，避免每日對中文 digest 燒 agy）。
- `dashboard_server.py`：news/flash_text/flash/review rc=0 後、bridge 前自動跑 translate_digest。
- backfill 今日 digest（6/6 欄）+ re-run bridge → NVIDIA 卡 data.json 已帶 `bull_case_zh`。

驗證：data.json news item 帶 `bull_case_zh`（`Vera Rubin 平台強迫資料中心電力進行結構性重寫…`）;
05-29 native-zh → CJK-skip 翻 0（不燒 agy）;05-30 idempotent skip;`--date` parse bug 修掉;全 py/js syntax 過。
版本 3.37.0 三處同步。

follow-up：(a) link_digest 報告 **MD 仍英文**（只翻卡片欄位）;(b) 翻譯無 cache，同一 digest 重跑會
重翻英文欄（但 idempotent skip 已翻者）;(c) en 語系下 native-zh verdict 仍顯中文（base 是中文，pre-existing）;
(d) sector_view/macro_view 已備 `_zh` 但 news 卡未渲染這兩欄。

## 🟢 Session Note (v3.36.0) — Link Digest zh-TW 在地化（gemini/agy 翻譯）

接 3.35.0。user 反映 link_digest 產物全英文；查證後發現即時新聞（break-news 辯論）本來就中文
（debater prompt 要求中文），但每日 news digest 的 bull_case/arbiter **也是英文**（只 headline_zh 翻）。
user 選「保留英文分析 + agy 翻譯」(非 claude 直接寫中文)。

做的：
- `scripts/link_digest/translate.py`：重用 break-news `run_gemini`，單次批次 JSON in/out EN→zh-TW；
  env `LINK_DIGEST_TRANSLATE`（預設開）；agy 缺/失敗回 `{}` 非致命。
- `build_artifacts.py`：`build_translations()` 翻 7 欄 → verdict + bn 接 `*_zh`（headline_zh 優先序：
  LLM 提供 > gemini > 原文）。agy 缺 → warn + rc=2 degraded，不擋。
- `page-news.js`：news 卡 bull/bear/arbiter/debate 改 `_zh || base`（`UI.currentLang`）。既有 digest 無 `_zh` → 不變。
- `link_digest_protocol.md`：Localisation 段。

驗證：**translate.py 實打 agy** → 回乾淨 zh-TW JSON（`NVIDIA 資料中心營收優於預期` …）；
build_artifacts mock translator + 真 validator e2e（verdict/bn `*_zh` 都在）；env gate 關/空輸入回 `{}`；
4 支 JS / py syntax 過。版本 3.36.0 三處同步。

follow-up：(a) 每日 **news digest 本身仍英文**（本次只動 link_digest；要全站中文化需改 `news` protocol 或加共用翻譯 pass）；
(b) link_digest 報告 **MD 仍英文**（只翻結構化卡片欄位；要 MD 中文需 claude 直接寫 zh 或 agy 翻整篇）;
(c) sector_view/macro_view 有翻 `_zh` 但 news 卡目前不渲染這兩欄（已備好，未來要顯示即可用）。

## 🟢 Session Note (v3.35.0) — Link Digest（URL → 讀全文 + 上網找相關 → 判斷 digest → 報告/新聞/KG）

新功能。使用者丟一條文章 URL，LLM 讀全文 + 上網找相關新聞交叉佐證 → 判斷 digest，
結果同時進投資報告(raw md)、新聞 digest，且 entities/relations 讓 KG/供應鏈撿到。

**架構決策**：重用既有 `flash_text` claude-turn pattern（bypassPermissions → WebFetch+WebSearch 可用）
+ Nexus Tier-1 ingestion 契約。**LLM 負責 prose MD + judgment.json；deterministic script 負責 KG schema**。
- `news/link_digest_protocol.md`：5 步 spec + judgment.json schema + relation rubric。
- `scripts/link_digest/build_artifacts.py`：judgment.json → append digest.json verdict（安全 append：
  既有 DIGEST bump stage2_count；無檔開 REVIEW/INLINE）+ 寫 bn_*.json（`support_count=len(corroborating_sources)`，
  ≥2 源 → Nexus Phase-2 directed 供應鏈 edge）+ validate + tier-1 graph refresh。rc 0/1/2。
- `dashboard_server.py`：註冊 link_digest（PROMPTS `{url}` + guard + LOG_DIRS + 900s + label + classify）。
- `news.html`+`page-news.js`+`i18n.js`：URL 輸入框 + 分析連結 button + 驗證 + banner resume。

**巧妙耦合**：web-search 廣度 = 供應鏈 edge 強度。一條 ticker↔ticker 關係被 ≥2 篇來源佐證 →
`support_count≥2` 過 Nexus Phase-2 門檻 → 晉升 directed edge（否則只 provisional/co-mention）。

**驗證**：build_artifacts 兩條 digest path（fresh REVIEW + 既有 DIGEST safe-append）都過**真 validator** rc=0；
full main() e2e（temp ROOT）rc=0 + bn relation support_count=2 edge-eligible；
4 支 JS node --check 過；news.html tag balance OK；dashboard_server syntax OK；`--enable-direct-edge` flag 確認存在。
版本 3.35.0 三處同步。

**未做/follow-up**：(a) 沒實跑一條真 URL（需 claude turn + tokens；e2e 寫手已驗）；(b) link_digest verdict
不 patch sector_intel/phase0（cache_updated=false，探索層定位，標 reviewed）；(c) bn 若早於當天 morning news
DIGEST 寫，之後 news run 會覆寫 digest.json（bn_*.json KG 仍在）— 罕見邊界。

## 🟢 Session Note (v3.34.0) — Narrative Pulse 完整退役

接 3.33.0(UI 移除)。觀察期原 2026-05-31,但 5/30(週六)、5/31(週日)無新市場資料 →
不會再有 sample(最後 2026-05-29 週五)→ 提前整套退役:
- `daily_update.sh` 刪 `step9_narrative()` + Phase 3 呼叫;`dashboard_server.py` 刪
  SCRIPT_PROTOCOLS `narrative_pulse` + `/api/narrative-pulse/{data,ticker}` 2 route。
- 刪 `Dashboard/narrative_pulse.json` + 整個 `skills/narrative-pulse-detector/` skill dir。
- **唯一依賴**:`retail-sector-pulse/aggregate.py` 的 `load_npd_cache_for`/`aggregate_retail_volume`
  是 legacy graceful fallback(註解標 "kept as fallback")→ 缺 cache 自動回 `calm`/None。
  mood.html 每產業「散戶量能」恆 calm;**主 composite(trending polarity)不受影響**。fallback
  程式碼留著無害,日後可清。

驗證:bash -n daily_update.sh 過、dashboard_server.py + retail aggregate.py ast 過、repo 代碼層
narrative 殘留只剩 retail legacy fallback、narrative_pulse.json + skill dir 已刪。版本 3.34.0 三處同步。
memory `project-narrative-pulse-v12-review` 已改記退役結論。

## 🟢 Session Note (v3.33.0) — 退役 Narrative Pulse UI + 移除散戶視角 + index 產業趨勢 mini

使用者:narrative 完全沒參考用處。清掉死/冗餘 UI:
- **index Zone B「Narrative 焦點」→ 真實「產業趨勢」mini**(`#industry-mini-strip` +
  script.js `renderIndustryMini`):讀 `data.industry_trend`(領漲前3+領跌前2 perf_1w),連
  radar。移除原 index 內 fetch `/api/narrative-pulse/data` 的 inline IIFE(舊連結連到已隱藏
  radar#npd-section,是死的)。
- **radar 清死碼**:刪 `#npd-section` + page-radar.js NPD IIFE(NPD_RADAR_ENABLED 死碼)。
- **散戶視角移除**:radar 刪 `#radar-retail-sector-pulse` + page-radar.js retail 全套
  (`renderRetailSectorPulse`/`renderMarketWideBuzz`/`buildRspCard`/`_rsp*`)+ render 呼叫 +
  tooltip。mood.html 自帶副本不受影響。
- **保留**:batch_scan generator + `/api/narrative-pulse/*` + narrative_pulse.json(觀察期
  2026-05-31);bridge 仍餵 retail_sector_pulse(mood 用)。

陷阱:page-radar.js 多塊刪除必須**行號高→低**(2228→1142-939→508→347-372),否則上面先刪
會位移下面行號(第一次刪 508 在刪 tooltip 之後 → 誤刪 collateral,已 restore backup 重做)。
驗證:node --check 兩檔過、residue grep 0(只剩自家註解)、industry_trend success/15、
narrative_pulse.json 仍在。版本 3.33.0 三處同步。

remote-control 任務:重新規劃 index.html、優化 AI 裁決頁面、判斷今日焦點是否有意義。**純前端、零 backend、零 schema 變更**。

做的:
- **index.html 4-zone**:9 條垂直 stack 收斂成 Zone A 指令(verdict+binary+8-gauge)/ Zone B 訊號帶(sentiment+narrative+today-focus 三薄 strip 合成 `#signals-band` 3-up grid)/ Zone C teasers / Zone D action。Structural Watchlist body → `<details class="experimental-collapse">` 摺疊。**所有依賴 ID 逐一 verify 保留**(35 個 grep 全中)。
- **decisions.html AI 裁決卡片**(`page-decisions.js` buildCard + 3 helper):V5 估值/Red Team/進場條件 → `<details class="dc-collapse">` 摺疊(summary 露 verdict chip);Model Score text-4xl→2xl;key_risks 4 顆 inline + "+N more";估值 grid 加 sm: breakpoint。click handler L1478 已排除 summary,details → drill 不誤觸。
- **hero 密度**:`components.js` tv-signal-grid min-h 76→60。
- **今日焦點**(`script.js renderFocusTicker`):**判斷=真訊號但 framing 誤導**(三軍同向 deterministic 可重現,但單 pick + 紫色買進 CTA 把 NTAP RSI92 末段噴出當進場)。改造保留→ Top 3 + 過熱守衛(rsi≥80/overbought/Stage3 → 「過熱」amber pill)+ 中性 `查看分析` CTA + 0 候選 graceful fallback。

驗證:3 支 JS node --check 過;index.html tag balance OK;35 ID grep 全中;真實 data.json 跑 selection → Top3 = NTAP(過熱)/IT(乾淨)/CRWD(過熱),守衛正確;server :8080 serve 200 + signals-band 命中。版本 3.32.0 三處同步。

## 🟢 Session Note (v3.31.0) — 個股動向 row 可點 → inline 動能明細 + K線

接 V3.30.0(個股動向 panel)。讓 row 可點就地展開明細。**純前端、零 backend、零新 fetch** —
資料(`momentum_screen` row + `history_by_ticker` 30 日)與 K線 API、analyze queue 都現成。

做的(`page-radar.js` + `radar.html`):
- `_smRow` + 弱中強 chip 加 `data-sm-ticker` + cursor;新 `#sm-detail` 共用明細容器。
- `renderStockDetail(ticker)`:30日 score sparkline(`_miniSparkline` inline SVG,免 Chart.js)
  + 均線排列(above_ma20/50/200_pct) + RSI/MACD/RS3m6m/距52週高 + signals/warnings chips
  + [看即時 K線](`selectRadarKline`+scrollIntoView) + [完整分析](重用 `.analyze-ticker-btn`)。
- document click delegation:`[data-sm-ticker]`(非 button)→ renderStockDetail;`[data-sm-kline]`
  → selectRadarKline;`#sm-detail-close` → 收;再點同檔收合。

驗證:node --check 過;data.json momentum_screen success + history 529;wiring grep 11 命中。
版本 3.31.0 三處同步。
