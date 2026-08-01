# Session Notes 歸檔 v4.4.0 → v4.10.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v4.10.0) — 決策中心 RWD + 三層卡片 + V3.45+ 估值欄位接通
- **動機**：user 反映決策中心 ①無 RWD（4K 要往右捲、卡片固定寬不跟視窗）②卡片 10+ pills 平鋪看不出結論 ③invest protocol V3.45-V3.49 新欄位沒上頁面。
- **RWD**：主 grid 加 `2xl:grid-cols-3 min-[2200px]:grid-cols-4`；**歷史 drill overlay 從固定 420px 橫向 rail 改 wrap grid**（4K 橫捲主因）；main 加 `min-w-0`；style.css 全站 `@media(max-width:860px)` sidebar 隱藏（15 頁共用一條規則）。
- **三層卡片（同 4.2.0 產業頁哲學）**：L1 結論 = 新 `buildDecisionStrip()`（action_label 主視覺 + conf% + CAP/PROBE/binary pills + institutional_lens 一句話 2 行 clamp）+ score/TP/SL/雙軌/持倉；L2 理由 = 單一 collapse（其餘 pills + Red Team + 觸發條件 + risks，summary 帶 RT verdict chip + 計數）；L3 證據 = 單一 collapse（估值 6-anchor + FvExtras，summary 帶 band chip）。`buildV48StatusPills` 改回傳 array；`buildV5ValuationBlock`/`buildRedTeamBlock` 改回傳 `{html, chip}`。
- **斷鏈補齊**：bridge.py 接 8 欄位（MHP/fair_value_range/implied_expectations/archetype_shadow/decision_cap_active/reason/cap_override_reason/hot_zone_probe）。前端 `buildFvExtras()` V3.49 早寫好但 data.json 從沒資料；本版接上後 **MHP 等 4 個 advisory block 要等下次跑 `分析` 才有資料**（history.json 現為 0 筆），cap 欄位立即可見（MRVL/PANW/CRWD 3 檔 4 筆）。
- **驗證**：node/py syntax 全過；`python3 bridge.py` 後 data.json MRVL `decision_cap_active=true/insufficient_anchors` ✓；headless Chrome 3840/1440/1280/760 截圖 — 4K 滿版 4 欄無橫捲、760 sidebar 收合 + CAP pill/防守/29%/lens 一句話全到位；index.html 760 無副作用；卡片 click delegation（details/summary 排除）原樣保留。
- **檔案**：bridge.py / Dashboard/{decisions.html, page-decisions.js, style.css, i18n.js} / VERSION×3。

## 🟢 Session Note (v4.9.0) — 市場氛圍頁重設計：決策漏斗 + 川普政策雷達
- **動機**：user 反映 mood 頁無法回答「目前市場走向、當下要不要投資」，產業情緒 grid 難讀；要求散戶視角 + 近 3 天趨勢為主、開盤含即時盤勢、多社群參考、即時新聞/突發辯論推播納入、**不增 token 成本**。
- **重設計（決策漏斗）**：①判定帶 偏多/偏空/觀望（確定性公式：開盤 盤面.35/新聞.25/辯論.20/情緒.20，收盤 .35/.30/.35，±0.15 中性帶，分項 chip 透明 + 分歧警示）+ Market Brief 導讀四欄；②trend-chart.js 72h 情緒線 + brief history regime 時間軸 + 每日錨點；③盤中即時（heatmap client 聚合，開盤 3min 輪詢、收盤收合一行）；④社群雷達 Reddit/HN/Bluesky 貼文 feed（直讀 trending_tickers.json 全量）；④b **川普政策雷達**：raw-stream 過濾 Truth Social，政策詞高亮 + TACO 轉彎 lexicon flag + 已辯論帖掛 verdict/final_take；⑤突發辯論 10 列 + 熱事件 clusters；⑥產業情緒 11 卡 → 單列排行；⑦舊三 tile 降頁尾。半圓儀表 + Chart.js 移除。
- **0 新 LLM call**：全頁只 GET 已存在 artifact（brief/debates/trends/heatmap/trending）。探索層，不回饋 investment_protocol。
- **Server**：brief API 加 `?history=1`（預設回應不變）；store feed projection 加截斷 final_take（≤400）。
- **驗證**：server 重啟後 curl 三項全過（default brief 迴歸無 history key / history=1 回 list / feed 帶 final_take）；node 煙霧測試（真 heatmap+data.json）：tape 聚合正確、收盤模式正確排除盤面、verdict=觀望 +0.141、renderAll 無 throw；JS/HTML id 交叉檢查 55/55；validate.py 僅 pre-existing 壞檔 bn_20260530_d1e30a96 fail（與本次無關）。
- **user 決策記錄**：移除儀表 / 接受預設權重 / 收盤收合摘要 / Truth Social 獨立政策雷達（只評川普政策轉彎，不混一般 feed）。
- **檔案**：mood.html / page-mood.js（重寫）/ i18n.js / dashboard_server.py / scripts/break_news/store.py / VERSION×3。dashboard_server 已重啟。

## 🟢 Session Note (v4.8.0) — Break News V6：event clustering + 嚴格 gate + Market Brief
- **動機**：user 要 refactor 即時新聞辯論省 token + triage 先用 Python 統計同類新聞防重複辯論 + 系統產可用的市場現況導讀。診斷（6/1-11 實測）：650 件 2,873 call（4.4/件、~261/天），**69% 跑滿 3 輪**（V5 conf-gap 0.4 觸發太鬆，實際 round-1 收斂率僅 17%）；56% 是 sentiment 情緒標題且多同事件跨源重複。
- **V6 三刀 + 一個新輸出**：
  1. `cluster.py`（新，0 LLM）— zh-aware token（en stemming + 中文 bigram）Jaccard/containment ≥0.55 同 news_type 聚類；echo 不重辯；milestone 4/8/16/32 + 距上辯 ≥3h → 增量追辯（opener 附前次結論）。`_clusters.json` 滾動 48h。
  2. debater V6 — max_rounds 3→2 全員；gate 只認真衝突（verdict 對立/極性衝突）；conf-gap 限 high-priority ≥0.65；`single_voice`：單邊 CLI 掛直接收 partial_closed（實測抓到 codex 掛時省 2 call/件）。
  3. poller — sentiment 非 binary/非 HIGH/|score|<3 只聚類不辯；EST_CALLS 3→2；state 新增 echo/sentiment/escalation 計數；dry-run 零寫檔合約保持。
  4. `market_brief.py`（新）— 每 2h 聚合 24h clusters+verdicts → 1 call 產繁中導讀（regime/drivers/bull/bear/watch）→ `_market_brief.json`；UI 頂部面板 + `/api/break-news/brief` + `/brief/refresh` + `/clusters`；卡片 ×N echo badge。
- **估算**：~261 → ~60-75 call/天（▼70%+），含 brief +12/天。
- **驗證**：cluster 單元測試全過（echo/escalation/milestone 防重發/type 隔離/zh tokenize）；poller dry-run OK；live debate ×2（V6 gate + single_voice 路徑）；live brief 1 call 產出品質好；validator 含新 lint 通過（僅 bn_20260530_d1e30a96 一個 pre-existing 壞檔 fail，與本次無關）。
- **⚠️ user 動作**：**dashboard_server 需重啟**（新 module import + brief loop + 新 API）。**codex CLI 目前壞掉**（`Reading additional input from stdin...` rc=1，probe 也掛）— break_news pair 是 gemini×codex，codex 修好前辯論都走 single_voice 單聲道（gemini 仍有結論，但無對抗）。可考慮暫時把 `config/llm_config.json` break_news.secondary 改 claude。
- **檔案**：cluster.py + market_brief.py（新）/ poller.py / debater.py / prompts.py / store.py / validate.py / dashboard_server.py / break-news.html / page-break-news.js / news_components.js / CLAUDE.md / VERSION×3。

## 🟢 Session Note (v4.7.0) — News Protocol V2.2：script-first triage 省 token
- **動機**：user 要求 refactor news protocol 減 token、品質持平。診斷：DIGEST 單跑 ~110K+，最大洞是 LLM 讀整包 raw.json（287KB ≈ 70K tokens）手工 triage — 但 `stage1_triage.py` v3.14.3（block/dedup/credibility/score/snap/gate）+ validator triage cross-check 早已存在，protocol 文件沒接上。
- **V2.2 改動**：Stage 1 全 script 化（LLM 禁讀 raw.json，只讀 stage2_items + shallow top-25，補 top-15 headline_zh）；Stage 2 bundle 每篇截 5000 chars；MD shallow 20→10 照抄 script snaps；Phase 4.5 watchlist 節移 README；protocol 563→361 行（每 run 省 ~4K context）。**Stage 2 四方辯論 / Arbiter / 加權表 / cache patch / FLASH / REVIEW 全不動**。
- **server prompts**：`news` + `triage` 改 script-first；順帶修 `triage` prompt 舊 `verdicts` shape 與 validator `shallow_verdicts` 期望的衝突（UI 無人消費 triage.json，i18n triage_* keys 是 orphan，安全）。
- **預期**：DIGEST ~110K → ~35-40K；TRIAGE ~75K → ~5K。品質 trade-off：shallow snaps 從 LLM 個別寫改 script template（本就「品質不穩、不 patch cache」的展示層；明顯錯誤時 protocol 允許 LLM 改寫 top-10）。
- **驗證**：dashboard_server.py ast.parse OK；validator 規則（stage1_count 對照、deep ⊆ stage2_items、shallow 10-15 cap）逐條核對相容，validator 0 改動。
- **⚠️ user 動作**：dashboard_server 需重啟（PROTOCOL_PROMPTS 改動）。下次 DIGEST 跑完建議覆核 token 實耗 + shallow snaps 可讀性。
- **檔案**：news/news_protocol_v2.md（重寫 V2.2）/ news/README.md / news/digest_output_schema.md（註記）/ dashboard_server.py（2 prompts + 1 註解）/ VERSION×3。

## 🟢 Session Note (v4.6.2) — 取消 LLM Fallback 機制
- user 要求取消 LLM Fallback。修改後，若主要模型不可用或呼叫失敗，系統將直接顯式報錯，不再默默 fallback 到其他備援模型。
- **`model_router.py`**：重構 `_run_chain` 以取消 fallback 機制，`order` 列表中僅包含單一模型（優先使用指定的 `preferred`，若無指定則僅用 `chain[0]`）。
- **`poller.py`**：修改 `_voice_order` 只回傳單一優先模型，以避免准入控制（Admission Gate）誤判 fallback 備援容量。
- **`llm_drivers.py`**：更新 `_DEFAULT_CONFIG` 預設模型順序，將 `run_llm` 與 `model_chain` 的預設 fallback 模型由 `claude` 改為 `gemini`。
- **`llm_config.json`**：更新 `primary` 為 `gemini`，`secondary` 為 `codex`，`tertiary` 為 `claude`。

## 🟢 Session Note (v4.6.1) — ops glob 大小寫 + postmortem 資料修復
- user 跑完回測仍標 never_run：Python glob macOS 大小寫敏感（`*postmortem*` ≠ `POSTMORTEM_`）→ registry glob 修 + `_glob_ci()` fallback（需重啟 server 生效；registry 修即時生效）。
- postmortem 報告半盲三因：yfinance 尾端 NaN Close 毒 mean/pearson、V4.x 加粗格式 regex 漂移（5 月起 score/RT/burry 全空）、RSI 只認表格式。全修 + 重跑，N 大增（score 49→94）。
- **修後關鍵發現**（詳 POSTMORTEM_2026-06-11.md + 本次對話分析）：final_score r=-0.003 純噪音、News lane 唯一接近訊號 (+0.186)、RSI>90 derate 只在 5d 視窗成立（10d 後 90-95 桶反而最強 +23%）、aggressive 進場 3/99 成交、SELL 1/1 錯。樣本偏差：半導體大多頭 tape + MU/TSM 重複計入。
- **候選 protocol 調整（未動，待 user 決定）**：RSI derate 改 horizon-aware、aggressive 進場帶提高、score 權重等 weekly REVIEW 樣本累積後再判。

## 🟢 Session Note (v4.6.0) — 工作流導向 Dashboard（Today 工作台 / 產出閉環 / 節奏自動化）
- **起因**：user 要求從前端觀點重新檢視工作流。盤點（2 Explore agents）：16 頁 ~16.8K 行 JS、42 API 運作正常，但 weekly/shadow/postmortem/REVIEW/ledger/premarket 6 類產出無前端入口、手動 cadence 靠人記、index 缺梳理後全貌。user 確認三痛點 + 選工作流導向、分階段。**頁面瘦身合併明確不做**。
- **架構**：聚合放 `/api/today`（server 即時算，真相源 ops_scripts_status/preflight_check/_list_reports_cached 全現成），不擴 bridge/data.json。報告關鍵行萃取 deterministic regex 0-LLM。
- **Phase 1**：`/api/today` + `today-panel.js` 三卡（該做的事：triggered kill > protocol stale > due scripts > watch 股財報 ≤7d > kill 倒數 ≤2d > break-news stale；最新產出 feed 用 reports 頁 chip + deep-link；晨報 digest + 過期黃條觸發盤前檢查）。index 加盤前/盤中/盤後分段標籤，零 DOM id 變動。
- **Phase 2**：分類器 +5 type、掃 decision_review/ 子目錄、view API 白名單分支（traversal 測試 400）、reports 頁摘要行、`/api/adjustment-ledger` + decisions 頁唯讀 active-recs panel。
- **Phase 3**：SCRIPT_PROTOCOLS +3 script、registry 加 protocol_id/endpoint/auto、`ops_auto_loop`（30min tick、6h 防抖、`OPS_AUTO_LLM` 雙重開關）、ops/Today ▶ 一鍵。**發現 llm_review 已有 launchd 週日 06:00 自動**（com.kavi.aicommittee.llm-review）— registry 只收監控不重複排。
- **驗證**：curl smoke 全過；headless 截圖 4 頁逐區；auto loop 實測（touch 舊→enqueue→fresh、weights.yaml 未動）；dedup 擋連點。注意 touch 模擬時年份格式 `202606020000`（CCYY）。
- **⚠️ user 動作**：**dashboard_server 需重啟**（新端點 /api/today、/api/adjustment-ledger、ops_auto_loop daemon）。
- **檔案**：dashboard_server.py（+~280 行）/ today-panel.js（新）/ index.html / page-reports.js / page-ops.js / page-decisions.js / decisions.html / style.css / config/ops_scripts.json / VERSION×3。

## 🟢 Session Note (v4.5.1) — 刪 earnings-trade-analyzer
- user 拍板刪除（0 接線、4/27 後無活動）。`git rm -f`（含未提交 fmp_client.py 修改一併捨棄）+ README / earnings-analyst SKILL.md / MARKET_INDEX 引用清除。
- event index extractor + 歷史 artifact（`reports/earnings_trade_analyzer_2026-04-26_*`）保留。check_skills 22 skills 0 warn。要復原：`git log -- skills/earnings-trade-analyzer`。

## 🟢 Session Note (v4.5.0) — Kill-Trigger Monitor + 稽核餘留批
- **Kill-trigger monitor（★★★）**：`scripts/kill_trigger_monitor.py` 0-LLM 每日重檢 Red Team 推翻條件（history.json 近 90d kill_conditions + sector _phase4b risk_scenario）。regex 謂詞：價格/MA（`200MA`+`MA200`）/量比/VIX/SPY RSI/breadth/DFII10（讀 fred cache）；WITHIN 窗口支援絕對日期/交易日(×1.45)/日曆日；**`未能…WITHIN` 否定期限語義到期才判**（MSFT 200MA 案例驅動，防假紅 banner）；AND/且 拆子句、OR/或 → manual；不可解析 → `manual`+倒數照樣上畫面。daily Step 9.9 + index.html banner（headless 截圖驗收：PANW d3 amber + DFII10 met-chip）。實測 189 條件 3 armed/60 manual/126 expired。
- **稽核餘留批**：predict 抽 `predict_ticker()` → thematic in-process（cache hit 0.00s）；earnings fetch 20 call 並行×8 + income dedupe（main 抓 limit 8 傳入）；weekly_review weights_version 讀 `top_movers[].short_term`（修死層級）+ per-ticker 史料 memoize（476→138 fetch）+ per-version 比較段；**technical_core 整檔升 `skills/_shared/`**（舊路徑 shim，momentum/analyze 零改）；RSI 5 實作→1（etf_scanner/sentiment/screen/predict 全 import shared Wilder；predict momentum_score 數值分布會移，weights 校準時注意）；MARKET_INDEX.md 23 skills 全列重寫。
- **順手修**：yfinance 尾端 NaN Close row（6/10 SPY 實測）→ screen/predict dropna；retail-pulse SKILL.md 退役引用清掉（check_skills 0 WARN）。
- **發現（待處置）**：FMP `/stable/rating-historical` + `/stable/grades-summary` 404（pre-existing；earnings bundle 該兩欄長期全零）— legacy 退役系列同 econ-calendar。
- **驗證**：6 消費端 RSI 同值 53.48、momentum NVDA / predict NVDA fresh / screen snapshot live ✓、check_skills 0 warn、bash -n、node --check、headless banner 截圖、weekly_review 真跑 476 預測。
- **檔案**：新 kill_trigger_monitor.py；technical_core 搬家+shim；predict/screen/weekly_review/fetch.py/etf_scanner/sentiment.py；index.html/script.js/style.css/daily_update.sh；MARKET_INDEX/SKILL.md×1/VERSION×3。

## 🟢 Session Note (v4.4.0) — Skills 稽核修復批（依 SKILLS_AUDIT_2026-06-11）
- **🔴 bug 批**：ic-memo quality_flags list crash（MSFT 全鏈驗證修復）+ trades[0] 錯 ticker 進 decision_lock + 9 欄位 shape 防護；v5_0 Burry 契約鍵名/T4 刻度修正（CANCEL 分支原不可達）；predict news_age 傳through（新鮮度閘復活）；retail-pulse 比對 headline+內文（原誤用 feed 名）；earnings render 新 flag 描述；us-stock-analysis（教 lane 違規 web search）/ technical-analyst 兩份 SKILL.md 補 lane 契約段。
- **靜默失敗**：fred degraded→rc2 + 不重寫 cache mtime；mood _partial→rc2；daily Step1 breadth 改 non-fatal；Step5.5 theme-detector 重跑補 rc 檢查；forecaster real_rate fallback 加 WARN + 修 0.0-falsy。
- **殭屍/效能**：刪 supply-chain-event-analyst（被 nexus 取代）；momentum .info 24h sidecar（省 529 Yahoo call/日）；predict SPY 1h file cache；retail-pulse predict ThreadPool×8 + 首例失敗 log；finnhub calendar memoize + status 不被 poison；enrich >7d prune（8386→1012）+ breadth keep-30（history 排除）。
- **驗證**：golden 26 asserts ✓、check_skills 23 skills ✓、MSFT ic-memo rc=2 degraded-usable ✓、momentum/predict smoke ✓、bash -n ✓。
- **餘留 backlog（audit 報告 §四之二）**：thematic in-process predict、earnings fetch 並行/重複抓、weekly_review weights_version 讀錯層、RSI 三實作統一、_shared price-history helper、MARKET_INDEX 重寫、kill-trigger monitor（新功能）。
- **檔案**：12 個 script + protocol v5_0 + daily_update.sh + 2 SKILL.md + VERSION×3。
