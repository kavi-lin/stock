# INTEL COMMAND — Session Notes & System State

> **Last Updated**: 2026-06-15 (v4.12.1)
> **Role**: This file serves as the "Short-term Memory" and "Handoff Cache" for AI Agents. It contains market regime states, token optimization logs, and data integrity notes. **Task backlog has been moved to TODO.md; full version history to CHANGELOG.md.**

## 🟢 Session Note (v4.12.1) — Premarket chain 完成偵測 bug 修復
- **症狀**：news 20:11 已寫 digest，但 chain 仍卡 `news: queued, elapsed=1500`；sector 等到 news timeout（1500s）才於 20:26 啟動。
- **Root cause**：`_wait_protocol_completion()` 用 count-based baseline（`len(_protocol_history)`），但 `_protocol_history` 受 `_PROTOCOL_HISTORY_MAX=10` 封頂、長度滿後恆定 → `history[: len-baseline]` 永遠空集合 → 完成永遠偵測不到 → 跑滿 timeout。**非 enqueue duplicate**。
- **第二 bug**：`_run_news` 跑獨立 thread，timeout 的 `RuntimeError` 無聲逃逸 → `phase1_errors` 空 → chain 假性過關推進 sector。
- **修復**：(1) baseline 改 timestamp，比 `ended_at >= baseline_ts`；(2) news/sector wait 包 try/except，timeout 記 item error + 中止 chain。`dashboard_server.py` 單檔。parse OK。
- **驗證待辦**：server 重啟後跑一次 premarket chain 確認 news 完成即推進 sector（不再卡 1500s）。
- **追加 bug（同 session）**：產業掃描 2026-06-15 跑完 + validator rc=0，但 `data.json.sectors` 空 → 沒進網頁。Root cause = `bridge.py _extract_committee` 對 `_phase4a` 無條件 `.get`，但該 run LLM 把 `_phase4a` 寫成 bare list（非 dict）→ `'list' object has no attribute 'get'` → sector ingest try-block 整段中止。改成兩種 shape 都吃。重跑 bridge → 11 sectors + 4 committee proposals 已進 data.json。

## 🟢 Session Note (v4.12.0) — Weekly REVIEW 改善計劃落地（shadow 量測 + 合成 replay）
- **動機**：user「針對這禮拜的 llm 回顧提改善計劃」。讀 REVIEW_2026-06-13 — 11 個 TODO 7 個卡資料門檻 still_waiting，週評估空轉。提三層計劃，user 選 Tier 1 全做 + Rec 11 shadow-replay，gate 保留 RISK_ON/BULL。
- **改動**（3 檔，~150 行，皆 shadow/唯讀，零決策層風險）：
  1. `verdict_rules.py`：`verdict_news_digest_directional()` 方向法（H-D）— shadow only，不進 DISPATCH。
  2. `build_event_index.py`：news verdict 掛 `shadow_directional`；新增 `decisive_agent_split` rollup（Pattern C 自動化）。index version 1.1→1.2。
  3. `investment/scripts/replay_rec11.py`（new 唯讀）：Rec 11 strict + ex-regime 雙 pass 合成驗收。
- **跑出來的發現**（量測揭露，未改決策）：
  - **H-C 收斂**：miss 是 action_class（保守性）驅動非 agent 驅動 — 各 agent conservative 都 ~57-69% miss，active 都 ~18-27%。News 不特殊 = Pattern A 同根。
  - **H-D 反轉**：強訊號 shadow directional = hit 1 / miss 8 → magnitude gate 過去藏的是**真 miss** 非 hit；macro_delta 方向校準本身弱，汰換前要先修 delta 來源。
  - **Rec 11 驗收**：strict 歷史 fire 12/19 Semis（+0.62% NAV，dd −3.1%）→ 規則健全，live dormant 純 regime timing。ex-regime 放寬只多 +0.35% 邊際 → 維持 strict gate 正確。
- **驗證**：py_compile 三檔過；build_event_index rc=0（314 records，version 1.2，shadow/split 欄就位）；replay 產 `reports/decision_review/REC11_SHADOW_REPLAY_2026-06-13.md`。
- **未動**：REVIEW_TODO.md（人/LLM-review 維護，TODO-012 監控點不自動改）；decision band / Rec 11 gate 規則本體不碰。
- **下一步建議**：下週 REVIEW 讀 `decisive_agent_split` + `shadow_directional` 自動帶入；H-D 汰換 magnitude 前先查 macro_delta extractor 方向校準。
- **檔案**：scripts/{verdict_rules.py, build_event_index.py} / investment/scripts/replay_rec11.py / VERSION×3。

## 🟢 Session Note (v4.11.0) — Dashboard 協定 per-protocol model tiering
- **動機**：user 問 dashboard 個股分析走 bridge → `claude -p` 預設用哪個 model；發現 `_protocol_command` 無 `--model` flag，全部協定吃 CLI 全域預設（手動 `/model` 切、易忘、貴）。要求按性質分層：需推理用 opus、簡單用 sonnet 省 token。
- **改動**（`dashboard_server.py` 單檔）：新增 `PROTOCOL_MODEL` map + `_protocol_model_for()`；`_protocol_command()` 加 `claude_model` 參數注入 `claude --model`（接受 alias `opus`/`sonnet`）。dispatch site 接上 + log 行印出 tier。
- **分層**：opus = `invest`/`llm_review`/`sector`（深推理/綜合）；sonnet = `news`/`flash`/`flash_text`/`review`/`link_digest`/`triage`/`earnings`（script-first/結構化抽取）。default=sonnet。env `PROTOCOL_MODEL_<NAME>` 可單協定覆寫（空字串回退 CLI 預設）。
- **範圍外**：break_news debater / supply_chain / office 走 model_router（primary=gemini），獨立不受影響；nexus Tier 3 = Haiku 不動。
- **驗證**：`ast.parse` 過；`claude --help` 確認 `--model` 接 alias。
- **檔案**：dashboard_server.py / VERSION×3（VERSION, utils.js, CHANGELOG）。

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

## 🟢 Session Note (v4.3.0) — 知識圖譜重構：theme hub-and-spoke + 聚焦模式
- **user 三抱怨**：看不懂 / zoom 不順 / 資訊量太大。診斷：280 邊中 262 是 CO_THEME 合成 clique（hairball 數學根源）；3 個錯開 auto-zoomToFit timer 跟 user 搶縮放 + 每幀 radial-gradient glow / `lighter` 合成拖累 zoom；點擊 thermographic 全圖特效資訊過載。
- **重構**（page-graph.js 全重寫 1046→~620 行，純呈現層，nexus_graph.json / build_graph.py 不動）：CO_THEME 不渲染，client-side 由 ticker.metadata.themes 合成 ~30 theme hub + MEMBER_OF spoke（邊 280→85）；點擊改 ego 聚焦模式（1/2 hop 切換、麵包屑、ESC 返回）；user 動手後永不 auto-fit；painter 只剩 circle+fillText；theme label 恆定螢幕大小（地標）。
- **控制台**：datalist 搜尋自動完成、關係類型 chip 開關、邊權重門檻 slider（取代時間衰減倍率）、聚焦深度按鈕；砍 provisional toggle。
- **驗證**：node --check 過；headless 截圖 ×2（hub 星系成形、主題 label 可讀、孤立節點自動隱藏）。聚焦模式點擊互動待 user 實測。
- **檔案**：page-graph.js / graph.html / VERSION×3。

## 🟢 Session Note (v4.2.0) — 產業掃描頁重設計：結論→辯論→證據
- **動機**：user 抱怨「掃描跑很多 token、頁面呈現很簡單」。盤點發現 sector_intel.json ~1300 行只有約 1/3 被 bridge 搬上 Dashboard — `_phase4a` 委員會 4 lane 投票、`_phase4b` Red Team IF/THEN 推翻條件、phase-1 估值（PE z1y/RS 多週期）、phase-3 盈餘脈搏/內部人/情緒全被丟掉；Today's Verdict hero 在 sector.html 還是 hidden stub（只活在 index.html）。
- **新區塊**：委員會決議矩陣（11×4 ▲▼ 投票 + 分歧高亮 + lane rationale）/ Red Team panel（反證 + IF/THEN amber 觸發塊 + DA conf 徽章）/ 量化證據矩陣（14 欄可排序熱力表）/ 宏觀 Overlay chips（FRED snapshot + step6 乘數理由 + 地緣風險）。verdict hero 上掃描頁（briefing signal grid 一併）。heatmap 移頁尾。
- **bridge.py**：market 增 `committee/da_challenges/fred_overlay/political_risk`；sectors[] 增 `valuation/earnings_pulse/smart_money/news_sentiment/fred_multiplier`。
- **驗證**：bridge 跑過、data.json 新欄位齊；node --check + ast.parse 過；headless Chrome 截圖逐區塊目視（矩陣/Red Team/quant 表/macro chips 全部 real data render）。
- **註**：新區塊文案用 isZh inline 雙語 fallback，i18n.js 未動。卡片 DA note 改 ⚔ marker（hover 全文），完整內容歸 Red Team panel。
- **檔案**：bridge.py / sector.html / page-sector.js / style.css / VERSION×3。

## 🟢 Session Note (v4.1.0) — Break News 辯論 V5：盲開局 + 分歧閘門
- **目標**：突發辯論省 token 但保有效產出。舊制 normal 固定 4 call（~10k tok）/ high 6 call，Round 2/3 大量重複 Round 1 資訊。
- **Round 1 雙盲並行**：A/B 各吃 opener、互不見 → divergence 變真訊號（舊制 B 看完 A 再寫，分歧被稀釋）。
- **Divergence gate（0 LLM）**：verdict 對立 / 同 pair predicate 極性衝突 / conf gap ≥0.4（`BREAK_NEWS_DIVERGENCE_CONF_GAP`）；`concede` 即收斂。無分歧 → 2 call 收場 `converged_round1`。舊 low-density early-stop 併入。
- **Round 2+ slim rebuttal**：新 `REBUTTAL_SYSTEM_PROMPT`+`rebuttal_user_prompt` — headline 1 行 + known state 1 行 + 確切分歧點 + 雙方 stance；output 只剩 commentary ≤60字/stance/新 relations/done，不重抽 entities。Round 3 只給 high-priority 仍分歧。
- **預算端**：`EST_CALLS_PER_DEBATE` 6→3，同 quota 可辯 ~2 倍條數。估收斂 case −70% tok、分歧 case −45%。
- **驗證**：mock 全流程 5 scenario（converge 2 call / concede relabel `divergence_resolved` / high persist 6 call / normal cap 4 call / 雙開局失敗→failed）+ gate 單測 6 case 全過。UI / build_summary_block / Nexus merge schema 相容免改。
- **注意**：validate.py 掃到 1 個 2026-05-30 舊檔缺 key — pre-existing，與本次無關。
- **檔案**：debater.py / prompts.py / poller.py / VERSION×3。

## 🟢 Session Note (v4.0.0) — Protocol 瘦身 + Model 分層（major）
- **B1 外移**：Phase 4.5 演算法 366 行 → `protocol_appendix_price_framework.md`（audit 用；engine+golden 為事實來源）。Protocol 4.5 縮成封裝呈現層 ~25 行。
- **B2**：Phase 2 reverse DCF pseudocode → 指路；2.4 時點 bullet → 1 行。**合計 1853 → 1471 行（−21%）**。
- **Model 分層第一批**：Sent/News/Tech lane → `model="sonnet"`；Fund/Val inherit（第二批候選）；**Red Team 永不降**；MD formatter Sonnet 既有。估單次 `分析` 成本 −35-50%。
- **哨兵**：shadow_report 加 lane 段（近 10 mean drift vs baseline n=31 + DISAGREE/polar 計數）。**降級後前 10 session 必看**；異常 lane 回 inherit。
- **第二批條件**：10 session 哨兵乾淨 → Fund/Val → Sonnet + MD formatter 試 Haiku。**第三批（另議，動決策）**：Valuation Specialist 裁撤（val_det 已有 deterministic 分數）。
- **驗證**：17 個 PHASE header 完整、golden 26/26、validator rc=0。
- **檔案**：protocol / 新 appendix / shadow_report / VERSION×3。

## 🟢 Session Note (v3.49.0) — 估值新 block 呈現層 + moat 容錯
- **呈現層補齊**：ic-memo §8（range/reverse DCF/MHP 三框/archetype shadow 四段，graceful skip 舊 entry，decision_lock 不動）+ decisions 頁 Valuation 卡 `buildFvExtras()` 4 行（Range/5D Band+60D+signal badge/Implied CAGR/Archetype flip ⚠）。
- **⚠️ 又抓到 pre-existing bug**：近期 entries（MRVL/PLTR/PANW）`moat_assessment` 被 LLM 寫成 string → **ic-memo 對最新 entries 一直 crash**。容錯修復，MRVL memo 重新可產（rc=2 degraded-usable）。註：根因是 LLM 沒照 schema 寫 dict — 之後 protocol 跑時 PM 應注意 fundamentals_lane shape；可考慮 validator 加 warning（未做）。
- **驗證**：render_sec_8 單測（synthetic blocks 全 render）、MRVL 全鏈 build→compose→validate rc=2、page-decisions.js syntax OK、golden 26 asserts 過。
- **Backlog 剩**：protocol token 瘦身、#10 cron 化、moat string drift 的 validator warning、shadow checkpoints（等 session）。
- **檔案**：build_fact_pack / compose / page-decisions.js / VERSION×3。

## 🟢 Session Note (v3.48.0) — Engine self-assemble + golden 測試 + peer_pe bug 修
- **P2 完成**：`--self-assemble` — quant 欄全由 engine 讀 deterministic 源（earnings cache / peer bundle / supp / forecaster cache / phase0），file 欄位優先，`self_assembled_fields[]` audit。AAPL 實測 24 欄自組、5/6 anchor。**估值鏈 0 LLM 算術 + 0 LLM 抄寫達成**（qualitative 欄 pattern/key_levels/catalyst 仍 LLM lane）。
- **⚠️ 順藤摸瓜抓到既有 bug**：FMP stable migration 後 `/stable/profile` 無 `peRatio`、`/stable/quote` 無 `eps` → **peer_pe_implied anchor 默默失效已久**。修：peer pe 用 ratios-ttm `pe_ttm` median；self eps = price/pe_ttm 反推（虧損股 → None，hypergrowth 規則退化只看 rev_yoy）。
- **#8a 修**：60d earnings_revision 折算 60/250（原直接用長期錨 = horizon mismatch）。
- **golden 測試**：`test_compute_price_framework.py` 4 fixtures × 26 asserts 全過；入 ops registry。改 engine 必跑。
- **限制註記**：self-assemble 的 fred 只補 real rate（nominal 10Y 無乾淨快取源 → engine fallback_fixed）；earnings cache 缺的 ticker（如 MRVL）→ DCF/PT/archetype 缺料降級（decision cap 接住）。
- **剩餘 backlog**：呈現層（ic-memo/Dashboard render range/implied/archetype）、protocol token 瘦身、#10 cron 化、shadow checkpoints（等 session）。
- **檔案**：engine / phase1_factpack / company_context / 新 test / protocol / CLAUDE.md / ops registry / VERSION×3。

## 🟢 Session Note (v3.47.0) — Dashboard Script 工具箱
- **起因**：user 要面板看「有哪些 script / 上次多久前用 / 需不需要跑」。
- **實作**：`config/ops_scripts.json` registry（11 支，可編輯）→ `/api/ops/scripts`（artifact-mtime 推斷 last run，零侵入；cadence 寬限 daily 26h/weekly 8d/monthly 32d）→ `/ops.html` + `page-ops.js`（badge: due/never_run/fresh/on_demand，due 排前；📋 複製指令；唯讀不執行）。
- **實測**：weekly_review 46 天未跑 → due 紅標（立刻有用的訊號）。
- **注意**：dashboard_server 需重啟才吃到新 endpoint（user 自管 daemon）。
- **檔案**：ops_scripts.json / dashboard_server.py / ops.html / page-ops.js / utils.js / i18n.js / VERSION×3。

## 🟢 Session Note (v3.46.1) — shadow_report.py 讀出端 + dispersion backfill
- **起因**：3 個 shadow 實驗（#3/#6/#4）只有寫入端沒有讀出端，checkpoint 到了要手挖 history。
- **`shadow_report.py`**：唯讀，一次算 4 section + checkpoint 進度，數學 import engine（單一事實來源），輸出 `reports/SHADOW_REPORT_<date>.md` + `--json`。#10 cron 前半身。
- **⚠️ backfill 重大發現**：歷史 37 筆 anchor CV 分布 median=0.46、P33=0.367、max=1.27 — agreement_grade 拍腦袋門檻 0.15/0.35 會把幾乎全部 session 判 low。**校準建議：high<0.367 / low>0.484**（33/66 pct），已寫進 protocol 4.5.0b 註記，#2 cap 接線前需 user 核可改 engine 常數。
- **跑法**：任何時候 `python3 investment/scripts/shadow_report.py`；#6/#3 到 20 session、#4 到 10 session 時跑它出報告。
- **檔案**：新 script + protocol 註記 + CLAUDE.md + VERSION×3。

## 🟢 Session Note (v3.46.0) — Valuation Archetype Shadow（#3，shadow-only）
- **起因**：固定 anchor 權重對未獲利成長股（DCF 0.45 雜訊、peer_pe EPS≤0 失效）與金融股（無 P/B）半殘。user 拍板：shadow 先行 + 權重表/門檻照設計初值。
- **archetype 分類**（按序首中）：financial → hypergrowth → cyclical → mature_cashflow → balanced。門檻初值：rev 25% / FCF 8% / rev 15% / margin σ 5pp。
- **3 新 anchor**：peer_ev_ebitda/ev_sales implied（精確 EV 數學，非比例近似）+ pb_roe_justified。資料：`get_ratios_ttm()`（company_context 新函數，雙 endpoint merge，24h cache）→ PEER_BUNDLE 新 5 欄。
- **紀律**：live `fair_value_summary` 完全不動；shadow 輸出 `flip_vs_live` 累積。**退出條件 ≥20 session 翻轉率報告 → #3b 切 live（cap/T5 接線同步）**。balanced fallback = shadow==live 自驗。
- **實測**：hypergrowth case live $225.7 overvalued vs shadow $270.5 fairly_valued（flip=true，EV/Sales 主錨）；financial pb_roe $76.95 手算一致；back-compat 舊 input → balanced flip=false；AAPL live peer median EV/EBITDA 20.4。validator rc=0。
- **Deferred**：forward EPS peer_pe、normalized-earnings anchor（cyclical）、cap/T5 接線 → #3b。
- **shadow 等待中清單**：#3 archetype（20 session）、#6 oe_mult（20 session）、#4 news_score 分布監測（10 session 凍結窗）。
- **檔案**：company_context / phase1_factpack / compute_price_framework / protocol / schema / validator / VERSION×3。

## 🟢 Session Note (v3.45.4) — News lane PT 去重（external review #4）
- **起因**：PT consensus 計分三次（valuation anchor 0.20 + 60d pt_60d 0.35 + News「PT vs price ±1」）。user 拍板：移除（非減半，LLM 聚合下減半不可控）+ 注入層剝離（非 rubric 層）+ revision momentum 回填 + 後驗防線。
- **fetch.py 剝離**：payload 砍 `price_target` block 全部絕對 level → `pt_revision_momentum`（30d/90d 方向+delta%+家數）。實測 AAPL：leak check 0、1m 下修 8% 有料。
- **持久化先行**：`news_lane.reasoning_one_line`+`key_factors[]` 必填第 5 欄（之前 0/134 落地，classifier 無 haystack — 這是 #4 計畫 review 抓到的致命缺陷）。
- **classifier**：`apply_det_shadow.py` `news_pt_leakage`（PT 折溢價措辭 → flag；「PT 上修/下修」合法）。warning 級。det_shadow → V3.45.4。
- **Phase 6 凍結窗**：前 10 個 News session delta.News=0（`news_weight_frozen_v3454`），防分布下移被誤判 lane 失準。
- **驗證法**：前向監測 news_score 分布 vs baseline `{-1:1,0:2,1:6,2:18,3:4}` (n=31) + leakage 累積率。history 反事實不可行（PT 子分數/reasoning/threshold 皆未落地）。
- **測試**：classifier 3 case PASS、舊 history entry back-compat（flag=None）、validator §5g warning-only rc=0。
- **待辦移交**：P2 餘項（#2 cap 接線 / #3 archetype anchor / #9 vol-normalize）、#8b DECAY backtest、#10 anchor 校準 cron、#6 oe shadow 20-session 檢查、PT 三點化 anchor（#1 後續）。
- **檔案**：fetch.py / protocol / schema / apply_det_shadow.py / validator / VERSION×3。

## 🟢 Session Note (v3.45.3) — Price Framework Engine script 化 + Phase 2.4
- **起因**：protocol review 抓到 B1（P0）：3.45.x spec 累積 weighted percentile / CV / reverse DCF 迭代解，LLM inline 算不可靠，卻寫「PM inline deterministic 計算」。user 拍板：order 對調（先 script 後 #4）、script 整包。
- **`compute_price_framework.py`**：一個 call 算 4 block（fvs blend byte-identical / range / MHP / reverse DCF bisection）。ticker 給了且缺 vol → 自抓 FMP OHLCV（消 LLM 抄寫）。降級=data 非 failure → rc=0。
- **新 Phase 2.4**：phase order `0→1→2→2.4→2.5→2.8→3→4→4.5→5`。一次解 B2 時序 fudge：T5(2.5) 直接用 mhp_signal、Red Team(2.8) 直接收 kill_seed、Phase 3/4/4.5 引用既存輸出。**注意**：本來打算放 Phase 3 Step 0，發現 implied_expectations 餵 2.8 Red Team → 必須 2.4。
- **Phase 4.5 降格為封裝呈現層**；implied_expectations 歸屬 Specialist→engine；B3 常數註記（ERP 0.04 real vs 0.045 nominal，用途不同非筆誤）；convergence low-conf guard。
- **驗證**：full / degraded（1 anchor、無 vol、FCF<0、FRED 缺）/ live FMP fetch（AAPL σ=0.0143）三路徑 rc=0。
- **版號**：3.45.2 跳過（原配 #4 PT 去重，對調後移後）。**下一步**：#4（注入層剝 PT + pt_revision_momentum 改 engine/deterministic 算 + news_lane 文字持久化 + leakage classifier）。
- **檔案**：新 script + protocol（Phase 2.4 新章 + 4.5/T5/RedTeam/Phase3/4 措辭）+ schema + CLAUDE.md + VERSION×3。

## 🟢 Session Note (v3.45.1) — 估值層 external review P0+P1 批次
- **起因**：外部 AI model review V5.1 protocol 給 10 點建議。本批做 P0（bug）+ P1（advisory/sibling，零決策衝擊）。user 釐清 4 點全收。
- **#7 bug 修**：`high_conviction_long_zone` 是 dead code（band_lower 必 < current）→ 改 `band_point<LT AND mid_target>current AND current<LT×0.9`。
- **#1 `fair_value_range`**：anchor 分布 P25/P50/P75 + `range_verdict` 位置判定。解決「加權平均沒人信、分歧被銷毀」。退化 n<4→minmax、n<2→null。
- **#2 拆半**：CV + `agreement_grade` **純展示**進 P1（**不**接 Phase 4.6 cap，接線+winsorize 留 P2，待歷史分布校準門檻）。
- **#5 `implied_expectations`**：reverse DCF 現價隱含 5Y FCF CAGR。WACC=FRED10Y+0.045、FCF base=owner earnings、FCF≤0→null。餵 Red Team `red_team_kill_seed`。不進加權。
- **#6 shadow (option a)**：live anchor 仍 static ×15（weighted_fair_value 不變），shadow-log rate-linked 倍數。確認翻轉率後才切換。
- **契約鐵律**：`fair_value_summary` byte-for-byte 不動 → decision_lock / val_det / validator / 舊 entry 全相容。新 block 全 sibling、warning-only rc=0。實測 MRVL entry rc=0。
- **未做（待議）**：P2 改決策數學各項（#2 cap 接線 / #3 archetype+EV/Sales/EBITDA/PB anchor / #4 PT 去重 / #9 verdict vol-normalize）逐項 review；#8b DECAY backtest；#10 anchor 校準 cron（獨立 infra）。
- **檔案**：protocol / schema / validator / VERSION×3 + SESSION_NOTES。

## 🟢 Session Note (v3.45.0) — investment Phase 4.5 → Multi-Horizon Price Framework
- **起因**：user 提案把單點 `fair_value_summary` 擴成三時間框架（5d 機率帶 / 60d target / 長期 6-anchor），各用該尺度合適方法 + 三框收斂成交易語意，並補 protocol 原本沒定義的 trade_plan TP/SL 來源。
- **做法**：Phase 4.5 升級成 Multi-Horizon Price Framework（仍 inline deterministic、0 LLM 重評）。
  - 5d band = 波動率錨定（σ_daily·√5 ± 1.28 + drift 查表 + catalyst override + key_level 反射）。
  - 60d = 0.40 momentum + 0.35 pt_60d + 0.25 earnings_revision。
  - convergence → `mhp_signal` 4 態，餵 Phase 3 T5 reasoning + Phase 4 entry/TP/SL provenance。
- **契約零破壞關鍵**：`fair_value_summary` key/shape **不動**（被 ic-memo 11-field decision_lock + apply_det_shadow val_det + validator 鎖死）→ 新框架另存 sibling `multi_horizon_price_framework`，長期層引用不重算。MHP **不**進 decision_lock（derived/advisory）。
- **新缺料輸入**：technical_lane 加 `volatility` sub-block（atr_14 / hist_vol_20d_daily / momentum_20d_pct，deterministic FMP read，缺 → 降級不擋）。
- **validator**：MHP warning-only（rc 維持 0），驗 long_term_ref 一致性 + mhp_signal enum + sub-block 完整度。實測既有 V5.0 MRVL entry rc=0 + 印 degraded warning。
- **檔案**：protocol / schema / validator / VERSION×3。

## 🟢 Session Note (v3.43.0 + v3.44.0) — token 計量上線 + sector 三招砍 cache_read
- **起因**：user 要盤前檢查的 per-stage token 報表。診斷發現系統只記 per-model **call 數**、
  從不記 token；真 token 全在 agentic protocol(sector/news/invest)+ break-news debate 的
  stream-json log 裡沒被聚合。
- **盤前實測 (2026-06-09→10)**：daily_update.sh 全 deterministic = 0 token；TOKEN 消費 =
  news DIGEST $2.75 + sector $4.25 = **claude 今日 $7.00**（in 27.8K / out 77.6K /
  cache_read 3.09M → cache_read 佔 89%）。
- **v3.43.0 token 計量**：`llm_drivers`(LLMResult +5 token 欄 + `parse_stream_log_usage`) +
  `model_router`(per-model `tokens` dict、`_record`/`note_run(tokens=)` 累加、migrate 舊檔) +
  `dashboard_server`(run_protocol 結束解析 log→note_run) + sidebar 顯示 in/out/cache/$。
  **已重啟 dashboard server (PID 變)**，今日 $7 已 backfill。break-news daemon 重啟回常駐。
- **v3.44.0 sector**：解剖 sector log = 24 Bash turn、cache_read 16K→131K 雪球。三招(同 3.42.0
  invest 模式)：① `phase_prefetch.py`(NEW 0-LLM 並行聚合 9 取數→1 JSON，Phase 3 FAST PATH) ②
  4 lane + Devil's Advocate 加 `model="sonnet"`(Arbiter 留 Opus) ③ GLOBAL RULES 禁 fmp MCP
  ToolSearch。**決策邏輯零變動**。
- ⚠️ **未跑真實驗證**：phase_prefetch 結構測過(valuation/sector_news/sentiment/digest rc0)，
  但 econ/earnings calendar 撞 FMP **legacy endpoint 退役**(403→SOFT null，非本次 bug)；
  smart_money ~131 ticker 慢(timeout 調 360s)。**下次真實「產業掃描」需確認 FAST PATH 真省 turn +
  Sonnet lane 品質不掉**。

## 🟢 Session Note (v3.41.0) — Rec 11 熱區保守性鬆綁（首個決策層 weekly-review 調整）
- 依 REVIEW_2026-06-07 + 上週(05-31) READY 項，promote **TODO-001 + TODO-002 → Rec 11**：
  Pattern A（Semis HOLD-miss 86% N=22）+ Pattern B（CANCEL-miss 71% N=21）同根，miss avg runup
  +30.5% vs drawdown −3.2%（Rec 9 證實真錯過）→ 鬆綁 V5.0 decision band。
- 改 `investment_protocol_v5_0.md`：正分模糊區 `[0,+staged)` × `industry_top_30pct` ×
  `RISK_ON/BULL` → default HOLD 降為 `STAGED_ENTRY (hot_zone_probe)`，15bps 上限；cap 規則不 force CANCEL。
  **3 道硬保險**：regime guard / `decision_cap_active!=true` / `mandatory_risk_flags 空`；硬閘（Auto REJECT /
  burry≤1 / proceed_to_phase3=false）全部優先。
- schema 加 `hot_zone_probe`；validator §11 enforcement（4-case smoke 綠：valid rc0 / HOLD・20bps・cap 衝突 rc1）。
- ledger Rec 11 target_metric：Semis HOLD-miss<60% / CANCEL-miss<60% / deep-dive hit 不退；
  **Semis HOLD-miss 回升>70% → paused**（user 指定）。
- 順手修 `build_event_index.py` ledger loader（`startswith("active")`，補抓 Rec 10）→ active 7→8。
- ⚠️ **user 提示 2026-06 中旬將大幅回檔**：回檔期 regime 應轉 VOLATILE/SIDEWAYS → 規則自動 dormant；
  首兩週需確認 `hot_zone_probe` 觸發數 ≈0、Semis HOLD-miss 走勢。
- **待**：下次真實 `分析 [TICKER]` deep-dive run 帶 hot_zone_probe 欄做真實 smoke；下輪 REVIEW 評 Rec 11。
- 留待累積：TODO-003（momentum-screen 8-12週）/ TODO-009（News-decisive N≥40）/ TODO-011（強訊號 N≥15 精校）；
  TODO-010 flip 12% observe band，續觀察 1 輪。

## 🟢 Session Note (v3.40.8) — Market Mood scoring 修正
- 使用者指出 mood page 每天都是「偏樂觀」。查證：`Dashboard/market_mood.json` 有更新，但 CBOE raw put/call 抓不到時退回 CNN `put_call_options=96.6`，被當成 `pc_signed=+93.2` 強訊號，壓過 SKEW high、breadth/strength 弱、junk bond demand 低。
- 修：CNN put/call fallback 改弱 proxy（cap ±50、權重 0.10）；新增 `fg_quality_signed` 聚合 stock_price_strength / stock_price_breadth / junk_bond_demand，權重 0.15。
- 重跑 mood producer（需網路權限）與 bridge：`data.json.market_mood.mood.score` 從 `+36 Greed` 變 `+2 Neutral`。

## 🟢 Session Note (v3.40.7) — Break News 源整理：移除 StockTwits + 補 3 RSS

User 觀察 StockTwits 很少被選到、沒用 → 要求移除並找新 RSS。先驗證：StockTwits 每
cycle 抓 ~35 則但只 63/1304（~5%）bn files 以它為 primary source，幾乎純雜訊進 Raw 流，
claim 成立。`social_sources.py` 移除 `fetch_stocktwits` 函式 + `STOCKTWITS_*` 3 個 env
var + adapter-list entry（社群源剩 truth_social / reddit / bluesky / hacker_news /
google_trends）。新 RSS 先 live curl + 過專案 `fetch_feed` 驗證才接：Fed Press(HIGH)、
Nasdaq Markets(MEDIUM)、Benzinga(MEDIUM) 全部 200 + 有效 item + 日期新鮮 → 加進共用
`FEEDS`（9→12，news protocol 與 break news 同步受惠）。淘汰 WSJ（item 全凍結 2025-01-27
dead endpoint）、GlobeNewswire（外語 micro-cap 噪訊）、Fool/FT(301)、SEC(403)。
TODO BN-2 closed。

## 🟢 Session Note (v3.40.5) — 新聞戰情室卡片可點開原文
- 修：新聞頁卡片無法點開原文。`url` 在 `*_raw.json` 抓取階段有，但 triage/digest 只保留 `news_id`、丟掉 `url`。
- `bridge.py` `_raw_pub_map` 改回傳 `{published, url}`，`extract_news()` 用 `news_id` 重新 join url；`page-news.js` source_label → clickable `↗`（新分頁），舊 digest 無 url 時 fallback 純文字。
- 驗：當前 11 筆全帶 url，`data.json` 已重生。

## 🟢 Session Note (v3.40.4) — 短期雷達：產業趨勢榜可點 → 列出**完整**成分股（finvizfinance）

user 要 radar 產業趨勢榜「點產業列出該類**所有**股票」。`industry_trend` 只有產業漲幅、無成分股。
先做輕量版（heatmap 大型股，Solar 1/半導體設備 0），user 追問「免費 api 也拿不到嗎」→ 查到 **`finvizfinance`**
（theme-detector 既有依賴、免 key、公開爬）Screener 可 by-industry 撈**完整**清單 → user 同意升級完整版。

最終實作（完整版）：
- **server**：`GET /api/industry/<name>` → `finvizfinance` Screener(`filters_dict={'Industry':name}`) → `{ticker,company,sector,market_cap}` list
  + **12h TTL 快取**（`_industry_cache`，`INDUSTRY_CACHE_TTL_SEC`）+ lazy import 防呆 + `_INDUSTRY_NAME_RE` 驗證 + `unquote`（名稱含空白/&）。
- **`page-radar.js`** `showIndustryStocks()`：主打 `/api/industry/`（完整），失敗才 fallback `_ensureHeatmapIndustries()`（本地大型股）；
  chip 沿用 `analyze-ticker-btn`→深度分析；`_industryRow` 加 `data-industry`+clickable；click 委派 + 關閉。`radar.html` 加 `#ind-stock-panel`。
- 保留 `_finvizIndustryUrl()`「在 finviz 看全部」連結（雙保險）。

驗證（fresh server live test）：Communication Equipment 44 / Semiconductor Equipment & Materials 29（& 名稱 OK）/ Solar 22；
2nd call cached 即時；bad name 400。node/py syntax 全過。

⚠️ user 的**跑著的 server 需重啟**才有 `/api/industry` route（route 是 boot 時註冊）。需瀏覽器實點驗收。
finviz 偶爾擋爬 → 自動 fallback 本地大型股 + finviz 連結。

## 🟢 Session Note (v3.40.3) — TODO-011 止血：news-digest verdict 門檻（接 3.40.1 回測檢討）

接 3.40.1 回測檢討。user 問 TODO-011 現在改不改 → 建議「現在改」並執行。

**root cause（確定 bug 非假設）**：`verdict_news_digest` 用單股設計的 `HIT_THRESHOLD_PCT=2.0`
評 SPY 市場級 call。SPY 窗口內幾乎不動 ±2% → 強訊號全壓 neutral → news-digest hit 結構性 0%
（連兩週 0524/0531 列盲點卻沒人開 TODO）。

**為何敢直接改**：純回測 verdict 標籤規則,**不碰任何 live 決策 / protocol** → 零下單風險、可逆。
跟 TODO-001/002 protocol threshold（必須等 drawdown 驗收）本質不同。

**改動**：`scripts/verdict_rules.py` 加 `NEWS_HIT_THRESHOLD_PCT = 1.0`,`verdict_news_digest` 改用之
（deep-dive 2.0% 不動）。±1.0% 經現有 7 筆強訊號驗算最優（救回 05-14 看空 SPY−1.93%,不像 ±0.5%
製造 sub-1% 雜訊假 miss）。rebuild 後 hit **0→1**。→ Rec 10。

**剩餘（TODO-011 in_progress）**：N≥15 強訊號 digest 累積後 grid 精校 ±1.0% 值。
**同時補建 TODO-010**（verdict <100% 窗口翻轉追蹤,資料已存在 9 snapshot,缺 diff 工具,下輪可跑）。

⚠️ **並行 session 注意**：本分支有另一條 session 同時在動（momentum journal v3.40.2）。VERSION
被推進數次,我的 review 改動最終落 **3.40.3**（3.40.1 = drawdown+parser / 3.40.3 = news 門檻止血;
3.40.2 是 momentum journal 那條 session 的）。

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

## 🟢 Session Note (v3.30.0) — 短期雷達加「個股動向」panel

接 V3.29.0(產業級趨勢榜)。痛點:產業榜看不出**產業內個股強弱分化**(光通 case —
強勢產業裡某股連跌多天)。

**關鍵**:個股 Weinstein stage / RS / Stage4 warning 系統每日算好且**已在
`data.json.momentum_screen.rows[]`**(daily Step 9.7 momentum-monitor ~529 檔),radar
沒用。→ **純前端、零 backend**。

做的:radar 新 `#radar-stock-movers` 區塊 + `renderStockMovers()`:
- 對稱 📈領漲個股(Stage2+RS≥70/新高) ↔ 📉走弱個股(Stage4/Stage3/WEAK·BEARISH),
  各 top 12,走弱按 composite score 由低到高。
- **🔥強勢產業中走弱 strip**:走弱 ∩ `sector_rs_rank≤3`(用 row 內建欄位,免 sector
  名對映)。實測抓到 BSX(RS-46/-14.9% 5d, Health Care #2)、ISRG、MDT 等。
- stage chip(S1-S4) + warning dots(🔻✗💀🪫) + freshness badge + 2 tooltip。

陷阱修正:走弱判定**不**用 `rs_3m_pct<0`(強 SPY 盤 412/529 會被誤標),改「Stage3/4
OR WEAK/BEARISH」→ 193 檔,UI top12 worst-first。校準:今日光通(COHR/CIEN/MRVL/LITE)
其實是 Stage2 強勢 parabolic,非走弱 — 引擎對,只是今天讀數異於印象。

驗證:node --check 過;data.json momentum_screen success/529/snap 2026-05-29;
consistency 印 leaders95/laggards193/weak-in-strong67 對得上。版本 3.30.0 三處同步。

## 🟢 Session Note (v3.29.0) — 短期雷達改用真實近期趨勢

痛點:radar 只反映 forward 預測 → ① narrative pulse 數據死板無參考價值
② 短期看多率結構性永遠 >50、看不到看空 ③ 看不出真實近期趨勢
(SaaS/CPU/AI server 巔峰、光通走弱)。

**關鍵**:使用者要的真實 trailing 資料系統**早已算好、卻被 radar 棄置** —
`theme-detector` cache 的 `industry_rankings.top/bottom` (140 finviz 產業真實
`perf_1w/1m/3m`) + `sector_uptrend`。修法 = surface 既有真實資料 + 顯示指標換真實。

四件事:
1. **`predict.py`** 輸出加 top-level `trailing_return_5d_pct` / `_20d_pct`
   (純價格 trailing,可負)。
2. **`screen.py`** `compute_theme_short_term` 加 `trailing` 區塊
   (`trailing_breadth_5d_pct` = 成分股近 5d **實際**上漲比例 + median 5d/20d +
   median momentum)。保留 bullish_breadth 不當主顯示。預設排序改 trailing。
3. **`bridge.py`** `load_industry_trend()` → `data['industry_trend']`
   (leaders/laggards/sector_uptrend/summary + freshness)。
4. **radar UI**:headline 新 `#radar-industry-board` (領漲↔領跌 + 1週/1月/3月
   toggle + 11-sector strip);theme card 改「真實上漲率」+「中位漲幅」+ 看多/看空
   badge;**Narrative Pulse 隱藏** (`NPD_RADAR_ENABLED=false`,generator 保留到
   5/31 觀察期)。

驗證:predict NVDA real 5d -1.77% / IONQ +16%;screen 重跑後 Oil&Gas REAL_up
10% med -5.37% (forward 是 40%)、多主題 <50、負中位 — 對稱看空生效;
smoking gun = 舊版 direction=bearish 主題仍顯示 bullish_breadth 83/66%。
JS node --check 過;bridge 餵 industry_trend OK (leaders top1=Computer Hardware
+17.98% 1w = AI server 巔峰);data.json 確認帶 industry_trend + theme trailing。
**注意** theme-detector cache 非每日強制重跑 (≤7天舊),趨勢榜帶 freshness badge。

## 🟢 Session Note (v3.28.0) — Market Mood 市場氛圍 page + retail social expansion

新增 Dashboard 專頁「市場氛圍」(`mood.html`/`page-mood.js`, nav group market)。
動機:radar Sector Pulse 看似情緒、實為純技術 — 散戶社群太稀 (整天 ~41 post)，
composite 塌縮成 5d 價格預測。

三件事:
1. **`mood.py`** → `Dashboard/market_mood.json`:VIX + ^VIX3M term structure +
   ^SKEW + CBOE/CNN put-call + Fear&Greed 7 子指標 → signed -100..+100 氛圍分。
   CBOE put/call CDN 目前 **403 封鎖**,fallback 到 CNN `put_call_options` 子指標
   proxy (有效)。缺源時權重 re-normalize。import sentiment.py 不改它。
2. **社群擴充** `social_sources.py`:新增 StockTwits source (trending → 各檔
   streams,native Bull/Bear tag 進 meta;env-gate + 429 graceful) + 加寬
   subreddit + 提高上限。實測 post 41→110、tickers[] 0→6+。契約不變,
   trending_tickers.py/aggregate.py 零改。
3. **新頁 UI**:hero gauge (Chart.js 半圓 + deterministic needle) + 3 訊號 tile
   (期權/VIX-SKEW/F&G+7子指標 bar) + 散戶熱股 strip + sector grid (情緒在前、
   技術 lane 灰底降權標「技術面參考」)。bridge 烤進 data.json (market_mood top-level
   + tactical.trending slim 投影,+7.7KB),無新 server route。

期權誠實講:無 live IV chain (FMP 付費也沒),用市場級 put/call + VIX + SKEW proxy。
驗證:mood.py CBOE 403 仍 score=41 不報錯;server serve mood.html/page-mood.js 200;
data.json 含 market_mood + trending;JS node --check 全過。

## 🟢 Session Note (v3.27.0) — Pre-Market Pipeline Redesign + Morning Brief

Redesigned the pre-market flow (`daily_update.sh`) to exploit the FMP **paid**
250/min plan, which the old free-tier-shaped pipeline (serialized FMP lane,
300ms per-client throttles, 150-call budgets, 6 workers) left unused.

Core: new `scripts/_shared/fmp_pool.py` — a single **cross-process** rate
limiter. It models FMP's "calls per rolling minute" via a JSON timestamp window
in `~/.cache_bridge/fmp_pool_window.json` guarded by an `fcntl.flock` lockfile,
targeting 220/min. The lock is held only for the read-trim-write (microseconds),
released before any backoff sleep, so the parallel subprocesses + threaded
workers `daily_update.sh` spawns share one budget without serializing. Verified
hermetically: 8 procs × 3 threads × 6 calls under cap 30/min held to exactly 30
per 60s window over ~240s.

All 6+ previously-uncoordinated FMP clients now delegate pacing to the pool
(signatures + caches unchanged). FMP lane de-serialized into two parallel chains
(thematic ∥ momentum); workers 6→20/16; supply_chain call-count cap 150→2000.
`dashboard_server.py` heatmap fan-out calls `acquire_slot()` so the always-on
server + a daily run never collectively exceed 250/min (optional
`FMP_DASHBOARD_RPM` soft sub-cap).

New `scripts/premarket/morning_brief.py` (step 9.8, non-fatal) → deterministic
`reports/PREMARKET_<DATE>.md`, 10 sections, cache-reuse + ~5-25 pooled fresh
calls, graceful when `FMP_API_KEY` unset, 36h staleness guard. Verified render
with and without the key.

## 🟢 Session Note (v3.26.1) — Break News Debate Scroll Reset

User reported that clicking a different Break News debate left the right-side
chat room at the previous item's scroll position instead of starting from the
top.

Fix: `Dashboard/page-break-news.js` now passes `resetScroll` only when
`selectedId` actually changes, and `renderDetail()` sets
`#bn-thread-panel.scrollTop = 0` after replacing the panel HTML. The 5s
same-item polling path does not pass `resetScroll`, so an active debate can
refresh without yanking the reader back to the top.

## 🟢 Session Note (v3.26.0) — Reports Center

Built a Dashboard reading layer over the existing 251 MD files in `reports/`.
Triggered by user wanting to visually browse the new IC memo outputs
(V3.25.0) plus 10 other report families in one place instead of using finder.

Implementation:
- `dashboard_server.py` adds two read-only routes — `/api/reports` (classified
  list, 60s cache, mtime-invalidated) and `/api/reports/view/<filename>` (raw
  markdown, ASCII whitelist + traversal guard). Cloned the existing
  `/decision_review/` static-serve pattern for consistency.
- New page `Dashboard/reports.html` + `Dashboard/page-reports.js` — master
  list (search + 12 type tabs with counts) on left, marked.js-rendered
  viewer with TOC on right.
- IC-memo-specific post-processing: verdict badge (BUY/HOLD/SELL/CANCEL
  colour), 🔒 `decision_lock` chip with 11-field SHA256 tooltip, degraded
  banner from footer flag, summary card extracting Date/Live Spot/Analysis
  Price/Market Cap/Sector from the YAML-ish header.
- Filename classifier handles 12 type families. `deep_dive` rule
  (`^YYYYMMDD_TICKER.md$` or `^YYYY-MM-DD_TICKER.md$`) catches 126 of the
  legacy V5.0 single-stock reports; only 9 misc files fall to `other`.

Strict discipline: pure viewer — no edit/delete/regeneration. Decision-lock
hash *verification* stays with `validate_ic_memo.py`; the page only displays
the lock. No protocol or skill behaviour touched.

**Server restart required** to load the new `/api/reports` routes (the
running `dashboard_server.py` process pre-dates this commit).

## 🟢 Session Note (v3.25.10) — Daily Update Hybrid Parallelism

User asked to implement the earlier dependency analysis for `daily_update.sh`
while respecting FMP's 250 calls/minute limit.

Implemented hybrid scheduling:
- Phase 1 runs breadth / FTD / market-top / FRED in parallel, then joins
  before `bridge.py`.
- Post-bridge FMP lane remains serialized: ETF holdings check → thematic
  screener → momentum fundamentals prefetch → full momentum screen.
- Non-FMP lane runs structural watchlist / Nexus / trending discovery in
  parallel, then retail sector pulse.
- Narrative Pulse runs after both lanes complete so thematic recommendations
  and structural watchlist are available.
- A final lightweight `bridge.py` refresh runs after Narrative Pulse so
  `Dashboard/data.json` includes same-run narrative / retail / momentum screen
  outputs instead of waiting for the next daily run.

Live timing correction: the first run showed Step 6 thematic can take ~948s
on a cold path, while `9.7` momentum screen took ~106s. User clarified both
are intended daily signals, so they remain enabled by default.

Optimization added:
- `skills/thematic-screener/scripts/screen.py` now supports
  `--predict-workers` for bounded parallel `predict.py` subprocess fanout.
  `daily_update.sh` uses `THEMATIC_PREDICT_WORKERS=6` by default.
- FMP-heavy enrichment remains serialized to avoid bursting the 250/min FMP
  limit.
- Temporary escape hatches exist for incident response:
  `DAILY_RUN_THEMATIC=0`, `DAILY_RUN_MOMENTUM_SCREEN=0`,
  `DAILY_FORCE_THEMATIC=1`.

Added temp-log background helpers so parallel jobs do not interleave stdout,
with elapsed seconds printed for every background job after join.
When enabled, `9.7` uses full universe with `MOMENTUM_SCREEN_WORKERS=6` by
default; caller can override the env var after observing 429/rate-limit logs.

Validation: `bash -n daily_update.sh` passes. Full live run intentionally not
executed during implementation because it would hit external APIs.

## 🟢 Session Note (v3.25.9) — Momentum 3D Volume Window

User asked for a quick-scan read of "**最近 3 天是量縮或放量**" without
clicking into the per-ticker volume modal. The existing 量比 column
only shows today vs 20D, which flips around on intraday noise. The 5D
average inside `_compute_dry_up_spike` was already there but too
smoothed for "recent" reading. 3D sits in the middle.

Compute (`momentum.py:_compute_dry_up_spike`): added `avg_3d_vs_20d`
(last-3-day avg / 20D avg, both excluding today, `iloc[-4:-1]`) +
`vol_3d_state` ∈ `{expanding, neutral, drying_up}` with thresholds
≥1.3 / [0.75,1.3] / ≤0.75 mirroring the existing dry-up cutoff.
Schema bumped `v2.2 → v2.3`; `_load_cache` gate updated to invalidate
old caches.

UI placement (per user pick): subscript under the existing 量比 cell.
Three stacked lines — today × ratio (existing, colored by today's
tier), then `3D X.XX×` dim subscript, then small colored state pill
(放量 / 中性 / 量縮). The cell stays clickable; the modal also gained a
new "3D 均量 / 20D" row. Single `_vol3dSubHTML(r)` helper renders the
two new lines so the rowHTML stays compact.

Smoke (NVDA, AMD, WMT, ULTA on real OHLCV):
- NVDA  today=1.12 3d=1.14 state=neutral
- WMT   today=1.50 3d=1.94 state=expanding (放量)
- AMD   today=0.88 3d=0.77 state=neutral   (just above 0.75 cutoff)
- ULTA  today=0.96 3d=0.85 state=neutral

Tooltip wording (`col_volume_tip`) updated zh + en so users discover
the subscript on header hover. No new tooltip component; reused the
existing styled card.

Out of scope: filter / preset wiring on `vol_3d_state`. If user wants
it later as a screening axis, the field is already in the CSV and
JSON path — only need `--min-vol-3d` flag + a defaultFilter() entry.

## 🟢 Session Note (v3.25.8) — IC Memo F-8 §1 Dedup

Cosmetic followup to V3.25.7 review. F-8 §1 entry-range check sat inside
the per-key for-loop, so when both `entry_aggressive` and
`entry_conservative` were non-null and §1 row was broken, validator emitted
two identical findings. Moved the §1 check out of the loop with an
`any_entry_set` guard preserving the original "skip when both keys null"
semantics. Added `test_md_entry_range_sec1_finding_not_duplicated` to lock
the behavior; 60 tests pass. No LOCK_FIELDS / decision_lock contract
touched — committee `decision_lock_hash` invariance preserved across
V3.25.4 → V3.25.7 → V3.25.8.

## 🟢 Session Note (v3.25.7) — IC Memo Validator Narrowing

Claude review of the V3.25.4 IC Memo patch found two real low-risk issues:
D-6 scanned the whole memo for `{"tier": ...}` and D-7 scanned the whole memo
for `Consensus View` / `Differentiated View`. Both were useful regression
checks but too broad — an appendix example or quoted phrase could trip them.

Fix: `validate_ic_memo.py` now extracts section blocks and limits D-6 to §7
and D-7 to §10 markdown headers. D-6 also catches Python-dict style
`{'tier': ...}` inside §7. Added a small stderr log when `build_fact_pack.py`
falls back to shared FMP peers because no IC Memo local roster exists.

Verification: `python3 -m pytest skills/ic-memo-writer/tests -q` → 59 passed.
MU memo validator remains rc=2 with only `sec_4_peer_descriptor_stub`.

## 🟢 Session Note (v3.25.6) — Column tooltips switched to styled card UI

User screenshot showed the V3.25.5 column tooltips rendering as the OS
native black box (Image #2), wanted them as the white-card style that
the sector heatmap uses for GOOGL row hover (Image #3).

Fix: instead of native `title="..."` attribute, wire `data-col-tip="<key>"`
on each annotated `<th>` and dispatch through the existing
`#mom-pill-tooltip` element + `showTip()` handler that already powers
the signal / warning / preset cards on this page. New CSS class
`.mpt-col` (emerald-accent title, 440px max-width) + `.mpt-body`
(`white-space: pre-line` so the `\n` in i18n strings renders cleanly).
Removed the now-redundant `setTitle` block — native title + styled card
were both firing on slow hovers and competed visually.

No new tooltip system, no popup framework, no hydration. The momentum
page now has exactly one tooltip component handling four content types
(signal / warning / preset / column). Consistent UX across hover
surfaces.

## 🟢 Session Note (v3.25.5) — Tooltips + Fund-tab i18n + 100% PE coverage

User flagged three follow-ups on the V3.25.x momentum work:

1. `MU` still showed empty 本益比 even after V3.25.2's backfill.
2. Fund-tab column headers (P/S / GM% / Rev YoY / 5D%) had no zh
   translation; left as raw English in the HTML.
3. Score vs Rank columns needed an in-UI tooltip explaining the
   difference, same UX pattern as the sector page's tooltips.

### MU root cause + 100% backfill

The `scripts/backfill_heatmap_pe.py` parallel run (15 workers) was
consistently dropping ~250/517 tickers in the SAME alphabetic cluster
(EQR, EQT, ERIE, ES, ESS, ETN, ETR…) — looked like an FMP rate-limit /
worker-batch failure that the script swallowed silently because every
network exception in `fetch_valuation` just falls through to the
all-None default.

Workaround: keep the parallel run for speed, then sequential second-pass
through the still-missing list with `time.sleep(0.08)` between calls
and `timeout=20`. Sequential pass filled all 236 remaining; MU now
reports `pe=41.79` end-to-end (heatmap.json → bridge → data.json).

Final coverage: heatmap.json `517/517`, data.json momentum rows
`515/528` (the residual ~13 are tickers genuinely missing TTM PE on
FMP, mostly negative-earnings names — not a bug).

There was also a `__pycache__` ghost that made an isolated `python3 -c`
import of `fetch_valuation` return all-None until the cache was wiped.
Likely the cached `.pyc` came from a half-saved earlier version of the
script. Cleared with `find scripts -name __pycache__ -exec rm -rf {} +`
before re-running. Not a long-term concern because the CLI script
recompiles cleanly each invocation; just a footgun when debugging via
`-c` snippets.

### Tooltips + Fund-tab labels

Pattern intentionally minimal: inline `title="..."` attribute set in
`applyLanguage()` via a small `setTitle` helper, mirroring the sector
page's heatmap-cell tooltips (`page-sector.js:1295-1297`). No new popup
component, no hover JS — browsers render multi-line tooltips natively.
Same UX as the macd column's existing tooltip already had.

Added 9 tooltip keys + 4 label keys (zh+en) to `i18n.js`. Score vs Rank
tooltip explicitly enumerates the bonus/penalty table from
`screen.py:_rank_score()` so users no longer have to ask "why is rank
80 when score is 65?".

### Operational note

If PE goes empty again later, run:

```bash
find scripts -name __pycache__ -exec rm -rf {} + 2>/dev/null
python3 scripts/backfill_heatmap_pe.py
# then sequential pass on still-missing if parallel left holes:
python3 -c "
import os, sys, json, time
sys.path.insert(0, 'scripts')
from backfill_heatmap_pe import fetch_valuation, HEATMAP, _safe_round
api = os.environ['FMP_API_KEY']
with open(HEATMAP) as f: d = json.load(f)
for row in d['tickers']:
    if row.get('pe') is not None: continue
    v = fetch_valuation(row['ticker'], api, timeout=20)
    if v.get('pe_ttm') is not None: row['pe'] = v['pe_ttm']
    if v.get('ev_ebitda') is not None: row['ev_ebitda'] = v['ev_ebitda']
    if v.get('fwd_eps') and row.get('price'):
        try: row['forward_pe'] = _safe_round(float(row['price'])/v['fwd_eps'], 2)
        except: pass
    time.sleep(0.08)
with open(HEATMAP+'.tmp','w') as f: json.dump(d, f, ensure_ascii=False)
os.replace(HEATMAP+'.tmp', HEATMAP)"
python3 bridge.py
```

V325.X-PE-WARMUP-RETRY (already in TODO) should fold this two-pass
shape into the dashboard_server daemon so the manual rescue isn't
needed; out of scope for this hot-fix.

## 🟢 Session Note (v3.25.4) — IC Memo MU Data-Gap Patch

MU smoke on the new IC Memo Writer exposed readable-output bugs that the
V1.0 hash validator did not catch: live spot and protocol analysis price were
mixed in the header, entry ranges stored as lists rendered as `—`, populated
earnings-cache fields were missed due to key-name mismatches, and §7 printed
a truncated raw structural-shift JSON fragment.

Patch shape:

- Dual price basis in fact_pack + memo: `Live Spot` and `Analysis Price` are
  both shown, and FV downside is split vs analysis and vs live.
- `fmt_price_range()` renders list/dict/scalar entry zones in §1 and §11.
- §5-§7 flatten TTM aliases, derive surprise %, alias balance-sheet fields,
  and support snake_case analyst estimates.
- §3 splits MU's FY2025 DRAM/NAND presentation from legacy CNBU/MBU/EBU/SBU.
- §4 uses a skill-local `peer_rosters.py` override for MU/NVDA/AMD/INTC/TSM
  instead of changing `_shared.company_context.get_peers()`.
- Validator gained MD-level checks for price-basis labels, lost entry ranges,
  raw structural JSON, and dead §10 consensus/differentiated headers.

Verification: `python3 -m pytest skills/ic-memo-writer/tests -q` → 59 passed.
Rebuilt MU/NVDA/CRWD fact packs and memos. MU and NVDA validate rc=2 only
because `sec_4_peer_descriptor_stub` remains Phase A.5 work; CRWD keeps the
expected missing-earnings-cache + low-anchor degraded findings. MU report was
regenerated at `reports/20260527_MU_ic_memo.md`.

## 🟢 Session Note (v3.25.3) — Fund tab color parity with Tech tab

User screenshot showed the Fund tab with an emerald tint on every
`.col-fund` cell (P/E header + body). After V3.25.2 pushed score/signals
into `col-tech`, the Fund tab's visible columns alternated between
untinted (`col-anchor`: #/ticker/price) and tinted (`col-fund`: P/E,
short, P/S, GM%, Rev YoY, 5D%) which read as broken stripes rather
than a unified group.

Fix: removed the `.col-fund` tint rules entirely. Both tabs now share
the same neutral cell background; emerald identity lives only in the
active tab pill in the rail above. Single-line CSS deletion. No JS,
no markup, no data changes.

## 🟢 Session Note (v3.25.2) — 2-Tab Refinements + P/E Backfill

User opened the new 2-tab view and reported two things: (a) `本益比` (P/E)
column was empty for every row, (b) score battery and signal pills should
only render on the Tech tab — Fund tab should read as raw fundamentals.

Root cause of P/E empty: `dashboard_server._heatmap_refresh_pe_universe()`
runs exactly once on server startup with a 24h TTL. The current
`Dashboard/heatmap.json` had 0/517 P/E entries — the warm-up either errored
mid-run or the server hadn't restarted in the meantime. Since
`bridge.py:ingest_momentum_screen` joins P/E from heatmap.json, every
momentum row got `pe=null`.

Fix: new `scripts/backfill_heatmap_pe.py` mirrors the daemon's three-call
fetch (ratios-ttm + key-metrics-ttm + analyst-estimates) out of process,
parallel via ThreadPoolExecutor, writes back atomically. Backfilled
269/517 entries (the remaining ~half are negative-earnings tickers where
FMP correctly returns no TTM PE). Re-ran `bridge.py` → data.json now
shows real P/E values on the Fund tab.

UI refinement: moved `score` + `signals` from `col-anchor` to `col-tech`.
New anchor set: `# · ticker · price` only. The 2-tab counts shifted to
Tech 12 / Fund 9. Fund badge updated. Class-based hide model meant zero
CSS work — just swap class on 2 `<th>` and 2 `<td>` cells.

Operational note: if P/E goes empty again later, run
`python3 scripts/backfill_heatmap_pe.py && python3 bridge.py`. Long-term
the dashboard_server PE warm-up should retry on failure instead of
silently leaving the cache empty — that's a deeper fix worth scheduling
separately, not for this patch.

## 🟢 Session Note (v3.25.1) — Momentum Table 2-Tab Column View

User pointed out the "More columns" toggle no longer fits after V3.22 added
the Fundamentals group. Default view hid the new P/S · GM% · Rev YoY · 5D%
work; expanded view ballooned to 18 cols. The boolean lens was the wrong
mental model — Tech and Fundamentals are two different ways of reading the
same row, not "less / more" of the same thing.

Replacement design (planned in `/Users/kavi/.claude/plans/more-column-colume-zany-cascade.md`):

- Two named tabs styled like the existing preset rail: 📊 技術面 (12 cols)
  and 💰 基本面 (11 cols). Each tab carries an inline count badge.
- 5 anchor columns (`# · ticker · price · score · signals`) render in both;
  the other 13 split by domain (7 tech, 6 fund). Hide control is purely
  class-based — `[data-view="tech"] .col-fund { display: none }` and inverse.
  No `nth-child` indexing, no fragility on column-reorder.
- Lag disclaimer (`#mom-fnd-note`) only shows when `#table-wrap[data-view=
  "fund"]` — it's a fundamentals-only message, so the Tech tab stays clean.
- localStorage key changed `momentum_cols_extra` → `momentum_table_view ∈
  {tech, fund}`. Legacy key intentionally ignored; default is `tech` to
  preserve the existing mental model for users who haven't touched anything.
- `.col-fund` doubles as visibility class and visual tint. The previous
  `.col-fnd` tint only covered the 4 V3.22 cells; reusing `.col-fund` now
  also tints P/E + short, which unifies the Fund lens visually.

No CSV / `bridge.py` / data shape changes — every field still ships in the
row payload; this is purely client-side rendering. Filters and presets work
identically across tabs (they operate on the underlying row data, not the
visible columns).

## 🟢 Session Note (v3.25.0) — IC Memo Writer (deterministic readable memo)

User shared a long Chinese Planet Labs (PL) analyst memo and asked whether
the project could surface that kind of "readable research report" view —
not Dashboard panels, but a narrative MD covering business model, revenue
segments, peers, scenarios, and DCF triangulation. Codex round-tripped on
the design and pushed back on five things that became the final spec:

1. `fact_pack.json` middle layer between cache and Memo MD (so template
   changes can re-render without re-fetching).
2. Per-section provenance tags (`<!-- src: ... -->` + Provenance Roster
   table) so every fact is traceable to its source.
3. **Decision-lock SHA256 over 11 fields** (not just `lane_scores`) —
   `final_decision`, `final_action`, `position_size_pct`, `analysis_price`,
   `fair_value_summary`, `scenario_odds`, `watch_conditions`, `key_risks`,
   `red_team_counter_thesis`, `red_team_kill_conditions`, `lane_scores`.
   Floats `round(x, 4)` before canonicalization to avoid IEEE drift.
4. LLM peer descriptor is isolated to the skill's own cache, not
   `_shared/cache` — that keeps the deterministic FMP-derived shared cache
   pristine. V1.0 ships the descriptor as a `status: stub_no_llm` empty
   shell; Phase A.5 will swap in a single Haiku 4.5 batch call.
5. `compose.py` is **deterministic-only** in V1.0 (zero LLM calls);
   `--llm-polish` flag is reserved but raises `NotImplementedError` so
   nobody accidentally re-introduces narrative drift.

Validator rc ladder: `0` pass / `1` fatal / `2` degraded-usable. Fatal
codes (F-1.1/1.2/1.3/2/3/4/5/6) cover hash self-inconsistency, history
mismatch, §11 verbatim mismatch, FV mismatch, missing §11 block, and
forbidden re-scoring phrases. Degraded codes (D-1..D-5) cover missing
earnings cache, low FV anchor count, missing provenance comments, and
missing Provenance Roster.

Smoke-tested on CRWD (no earnings cache → 6 degraded sections, rc=2 as
expected) and NVDA (full data path → only peer_descriptor stub degraded,
rc=2). 44 pytest cases pass, including all 11 single-field decision_lock
breach parametrized cases.

### Files touched

| File | Lines | Purpose |
|---|---|---|
| `skills/ic-memo-writer/SKILL.md` | new ~180 | skill spec + decision_lock + rc ladder |
| `skills/ic-memo-writer/template.md` | new ~150 | 12-section reference skeleton |
| `skills/ic-memo-writer/scripts/build_fact_pack.py` | new ~360 | aggregator + hash |
| `skills/ic-memo-writer/scripts/compose.py` | new ~430 | deterministic renderer |
| `skills/ic-memo-writer/scripts/validate_ic_memo.py` | new ~270 | rc=0/1/2 validator |
| `skills/ic-memo-writer/scripts/fetch_peer_descriptor.py` | new ~70 | V1.0 stub |
| `skills/ic-memo-writer/tests/test_validator.py` | new ~240 | 24 tests incl 11 breach sub-cases |
| `skills/ic-memo-writer/tests/test_fact_pack.py` | new ~115 | 11 tests |
| `skills/ic-memo-writer/tests/test_compose.py` | new ~135 | 9 tests |
| `skills/ic-memo-writer/tests/fixtures/*.json` | new ~660 | minimal NVDA history + earnings |
| `investment/investment_protocol_v5_0.md` | +20 | Phase 5 Step 7 IC Memo hook |
| `CLAUDE.md` | +5 | Protocol Triggers row + Ops Shortcuts |
| `CHANGELOG.md` | +60 | V3.25.0 entry |
| `VERSION`, `Dashboard/utils.js` | sync | 3.22.0 → 3.25.0 |

### Last Session Note

Phase A (IC Memo Writer V1.0.0) shipped. Composer is deterministic, no
network calls beyond profile/peers (24h-cached). Decision-lock SHA256 over
11 history fields means the memo cannot silently change committee output —
mutation of any single field flips validator to rc=1 fatal. Phase A.5
follow-up will swap `fetch_peer_descriptor.py` from stub to Haiku 4.5
one-shot batch call; Phase B will be a Dashboard `stock-detail.html` that
renders the memo + live FMP quote / 6-anchor bar chart. Neither is on the
critical path — Phase A alone delivers the requested "readable memo".

---

## 📦 Previous Session Note (v3.22.0) — Momentum Fundamentals Layer (P/S · GM% · Rev YoY TTM)

User asked to add P/S + "營收股價比值" to the momentum page. Round-tripped
through Gemini Codex review which flagged the two obvious failure modes of
naive valuation overlays on a momentum table:

1. A hard P/S cap on the breakout preset strips the strongest leaders
   (NVDA / LLY) precisely at their thrust moment.
2. A naked low-P/S filter is a value trap without a gross-margin floor +
   non-shrinking revenue guard (retail / commodity names look "cheap"
   because they earn nothing).

Final shape:

- New fundamentals derive block on `momentum.py` (schema `v2.2`) computes
  `ps_ttm`, `gm_ttm_pct`, `rev_yoy_ttm_pct`, `ttm_revenue_usd`, plus 1D/5D
  price return. All TTM (8 quarters of FMP `income-statement?period=quarter`)
  to dampen single-quarter noise.
- Shared cache at `skills/_shared/cache/quarterly_income/{TICKER}.json`
  with 7-day TTL — fundamentals only refresh once per earnings cycle.
- `daily_update.sh` Step 9.6 prefetches the screener universe (~532 tickers
  across SP500 + Nasdaq100 + SOX) so ad-hoc `screen.py` runs cost zero
  FMP calls on the fundamentals side.
- 7 new CSV columns appended (not inserted) so legacy `bridge.py` column
  parsers stay compatible; bridge already used `DictReader` so by-name
  lookup was free.
- Dashboard adds a tinted Fundamentals column group (P/S · GM% · Rev YoY ·
  5D%) hidden behind the "More columns" toggle. Two new Featured presets:
  `🚀 Sales Breakout` (no P/S cap; Stage 2 + RS≥80 + RevYoY≥15%) and
  `💎 Value Momentum` (P/S≤5 stacked with GM%≥15 + RevYoY>0 + exclude
  parabolic).

Smoke test on NVDA: P/S=20.36, GM=74.15%, Rev YoY=+70.7%, TTM rev=$253B,
lag=30d. Sales Breakout includes NVDA; Value Momentum correctly excludes.

Discipline kept: fundamentals are **information-only**, never feed into
`momentum_composite.score` or `rank_score`. Cross-industry P/S comparisons
aren't trustworthy enough to weight a momentum signal — they're guardrails
the user reads, not gradients the system optimizes.

Deferred to a follow-up PR (per user agreement to ship in two slices):
ATR-normalized Gap Up detector, `Catalyst Gap-Up` preset, sector-relative
P/S, Pocket Pivot. Ship V3.22 first, watch a couple of weeks of screen
output to calibrate Value Momentum's GM/P-S thresholds before piling on.

## 🟢 Session Note (v3.21.0) — Break News Hourly Cap + Stale-Backlog Guard

Diagnosis: previous 5-6hr session burned the Anthropic 5hr quota window.
Forensic counts: 106 break-news debates in ~6hr × MAX_ROUNDS=3 Claude voice =
~300+ `claude` CLI subprocess spawns, plus 3 large protocols (`分析 CRWD` +
`產業掃描` + `新聞分析`) running concurrently. `config/llm_usage.json` showed
claude in cooldown (34 calls, tripped early), gemini fell back to 404 calls
(over its 200 budget — only daily counters, no 5hr window awareness).

Fix shape: throttle the explore layer at the admission stage, not after-the-fact.

- `BREAK_NEWS_HOURLY_CAP=25` rolling 1hr admission cap, slot = 2.4 min/item;
  quiet periods accumulate slot tokens, bursts still bounded by hourly_left.
- `BREAK_NEWS_BACKFILL_MINUTES=30` freshness gate — auto-admission only for
  news published within the last 30 min. Older stuff still visible in raw
  stream, just not in the auto-debate queue.
- `BREAK_NEWS_PENDING_MAX_AGE_HOURS=2` stops `scan_and_debate` from
  re-processing stale `pending_debate` after a long idle. Stale queue surfaces
  in a new UI panel with per-item manual 🔥 Debate button.
- Feed sort key changed `last_activity_ts` → `fetched_at` so news ordering
  reflects arrival time (debating items no longer float to top).

Endpoints: `GET /api/break-news/stale-pending`, `POST /api/break-news/item/<id>/debate-now`.

Dry-run verified: hourly_used=8, hourly_left=17, slot_tokens=0 (slot未滿),
allowed_this_cycle=0 — correctly throttled. Model headroom side still has
room (model_debate_capacity=11), but hourly cap is now the binding constraint.

Followup-ish: still need a real 5hr-rolling-window counter in `model_router.py`
for protocol runs (this PR only governs break_news). Defer until next quota
incident.

## 🟢 Session Note (v3.20.7) — Momentum Volume Regime Alpha UI

- `journal.py` extended momentum journal evidence with `volume_trend`,
  `ratio_20d_bucket`, and `by_volume_regime` (`trend × stage × ratio bucket`).
  Existing historical journal rows are not rewritten; stats backfills old
  fields from matching cached `screen_*.csv` snapshots when available.
- Existing sample check: 23,986 entries, 12,342 filled 20d returns, 100% volume
  regime field coverage via cache. `expanding + Stage 2 + ratio_20d>=1.3`
  showed n=113, 20d win=73.5%, median=+9.56%. `volume_expansion` alone was
  weak, confirming regime-dependent volume interpretation.
- Momentum Dashboard Journal section now shows `Volume Regime Alpha` cells that
  pass exploratory gate `n>=5`, `20d win_rate>=55%`, `20d median>=+2%`.
  Composite score and row ranking intentionally unchanged.

## 🟢 Session Note (v3.20.2 → v3.20.3) — Truth Social Filter + Wire-News Polarity

User ran daily_update + refreshed UI after V3.20.2 ship; reported "目測還是
沒什麼變". Diagnosis showed retail polarity all 0 across sectors despite 3
qualified tickers because:

1. Lexicon偏 WSB slang (moon/puts/diamond hands/tendies),但 RSS feed 抓到
   的多是 wire-news 風格 (surge/plunge/dip/downside/buying opportunity)。
   49 live posts → 0 lexicon hits。
2. DJT 4 mentions 全來自 Trump Truth Social 簽名 "— President DJT",政治
   貼文不該被當 DJT 股票訊號。

User 提示 「川普的貼文有公信力,只是要濾掉政治貼文,只看股票或經濟」,
所以方向是 **relevance filter,不是 blanket reject**。

V3.20.3 修法:

**A. Wire-news polarity vocabulary** — lexicon v1.2 → v1.3:
- Bull ~37 新詞:buying opportunity / upside potential / extends gains /
  outperforms / surge(s|d|ing) / soar(s|ed) / jumps / climbs / advances /
  rebounds / recovers / gain(s|ed) / rises / rose
- Bear ~43 新詞:downside (risk) / extends losses / underperforms /
  headwind(s) / plunge(s|d|ing) / tumble(s|d) / slump(s|ed) / slides /
  slid / slip(ped|ping) / drops / drop / declines / declined / falls /
  fell / sinks / sank / retreats / weakens
- 標題詞 RDDT "great buying opportunity, ... downside" 現在能匹配兩端

**B. Truth Social filter** — 新 `truth_social_filter` block in yaml:
- Signature regex strip: `"— President DJT"` / `"-DJT"` / `"RT @ realDonaldTrump"`
- Relevance check:post 必須含一個 economic/market keyword (economy /
  tariff / fed / stock / earnings / jobs / oil / dollar / 經濟 / 關稅 等
  38 keyword + macro topic lexicon 全部 macro term)
- 不含 → drop 整篇 (政治 endorsement 砍掉)
- 含 → 保留 + signature stripped 後跑正常 pipeline
- 套用範圍:只 Truth Social,其他 platform 不影響
- `trending_tickers.py` 新 `apply_truth_social_filter()` 在 `run()` 內
  fetch 後 process 前呼叫

Live verification:
- 49 posts → 41 (7 政治貼被 drop)
- DJT 從 V3.20.2 qualified 列表完全消失 (簽名 strip 後沒 hit)
- RDDT 從 matched_terms=[] → matched_terms=[great buying opportunity, downside]
  (wire-news 詞庫第一次 hit live data)
- RDDT polarity 還是 0.0 — 但原因從「lexicon 0 hit」變「真實 mixed
  (bull + bear 各 1)」,這是 honest signal

Validation:
- `tests/test_trending_tickers.py` → 39 OK (+5 V3.20.3 tests:政治 drop /
  經濟 keep / 簽名 strip / $DJT body 保留 / wire-news polarity hit)
- `tests/test_aggregate.py` → 22 OK
- Live trending output 寫入 Dashboard/trending_tickers.json + 跑 aggregate +
  bridge → data.json[tactical][retail_sector_pulse] FRESH

下一輪改進可能方向 (defer):
- Reddit JSON API (取代 RSS) — 拿真實 upvote 數
- Question-form polarity heuristic ("Is X a buy?" 偏多)
- Topic matcher 改 word-boundary (現在還是 substring,Codex V3.20.1 留的)

---

## 🟢 Session Note (v3.20.1 → v3.20.2) — Dual-Gate + Retail Override + Broad ETF Routing

V3.20.1 ship 後 user 反映 XLK 卡片 retail polarity = None,只剩 price + 2-篇
news,參考價值偏弱。診斷後三個 root cause:

1. **Lexicon 污染** — live trending output 14 個 low_confidence 全是
   `LONG`/`CALLS`/`EARLY`/`GPU`/`NYSE`/`TRUMP`/`NIFTY`/`RINOS`/`FOSS` 這類
   非 ticker (WSB 動詞、英文常用字、組織名、政治 meme)。Lexicon v1.1
   blocklist 漏抓。
2. **Threshold 單閘太嚴** — 真實 ticker (NVDA) 只有 1 Reddit mention
   (engagement=1.0 fallback,RSS feed 不給 upvote 數)。
   `min_mention_count: 2 + min_total_engagement: 5.0` 把它跟 garbage 一起
   demote。
3. **Sector 對映漏** — `DJT` / `SMCI` / `RDDT` / `GME` 等 retail-heavy
   ticker 不在 `SECTOR_UNIVERSE` (mega-cap roster) → `sector=None` →
   silently dropped。`SPY` / `QQQ` 即使被抽到也不該進單一 sector
   (broad index)。

Codex 提出三向修法,我採納並補三點:

- **Dual-gate** instead of naive threshold drop:
  - known_sector: 1 mention, 1.0 engagement (NVDA single Reddit 過閘)
  - unknown_sector: 3 mentions, 8.0 engagement (long-tail garbage 不過閘)
- **retail_only_sector_overrides** in lexicon yaml — DJT/GME/AMC/HOOD/
  COIN/SOFI/SMCI/RDDT/ARM/MU/MARA/RIOT/OXY/MRNA 對映到 GICS sector,
  **不動 SECTOR_UNIVERSE** (避免污染 narrative-pulse-detector / sector
  protocol 等其他 skill)。
- **broad_market_etfs** in lexicon yaml — SPY/QQQ/IWM/DIA/VOO/VTI/
  TLT/VXX/UVXY/SQQQ/TQQQ/SPXS/SPXL 抽到後不進 sector,改 contribute
  到 `market_wide_buzz` 的 `broad_etf` + `market_direction` topic。
- 補:blocklist 擴 9 個 (LONG/CALLS/EARLY/GPU/NYSE/TRUMP/NIFTY/RINOS/FOSS)
- 補:UI card retail polarity 行加 `· n=X` mention 警告,thin sample
  時 dim 字體
- 補:legacy single-gate config backward compat shim

實作層面:
- `aggregate_tickers` 改 return 3-tuple (qualified / low_conf /
  broad_etf_posts);ETF posts 直接 pipe 到 `aggregate_market_wide`
- 加 `build_extended_sector_map(lex)` + `get_broad_etf_set(lex)` 兩個
  helper
- `qualified` 每 ticker 帶 `_gate: "known" | "unknown"` field 供 audit
- 7 條新 V3.20.2 test:blocklist verification, known-sector 1 mention 過閘,
  unknown 不過閘,retail override (DJT→Cons Disc),ETF route to market_wide
  (兩條:aggregate_tickers 層 + 端到端 `run()` 層),legacy config 兼容

Live verification:
- 49 posts → 3 qualified (DJT/RDDT/NVDA),2 unknown demoted,1 market_wide
  topic (ai_capex)。V3.20.1 是 0 qualified / 14 garbage in low_conf。
- Lexicon v1.2:50 blocklist + 15 retail overrides + 13 broad ETFs。

Validation:
- `python3 skills/retail-sector-pulse/tests/test_trending_tickers.py` → 34 OK
- `python3 skills/retail-sector-pulse/tests/test_aggregate.py` → 22 OK
- Live `trending_tickers.py --window-hours 24` → 3 qualified, 2 sectors
  with retail data, blocklist working (LONG/CALLS/NYSE/TRUMP 全擋掉)

---

## 🟢 Session Note (v3.20.0 → v3.20.1) — Polarity-First 3-Lane Sector Pulse

User flagged V3.20.0 retail layer was volume only — `retail_mention_multiplier`
told you Reddit was hot on NVDA but not whether retail was buying or selling.
Wanted to infer "what would a retail investor conclude" from public info.
Through plan → multiple Codex reviews → lexicon-curated implementation:

**Architecture refactor**:

- New `scripts/trending_tickers.py` pulls Reddit / HN / Bluesky / Google Trends
  via existing `social_sources.py`. Per post: extract tickers (with strict
  disambiguation), compute engagement = `log(upvotes+1) + log(comments+1)`,
  and compute bull/bear polarity via **span-masked lexicon match** (longest
  term first; matched span consumed so `short squeeze` does not also fire
  `short`).
- Per-ticker rollup → per-sector engagement-weighted polarity. Thresholds
  (`>= 2 mentions`, `engagement >= 5.0`) demote long-tail garbage to
  `low_confidence[]`. Posts with no ticker or `> 5` tickers go to
  `market_wide_buzz` bucket classified by 9-topic macro lexicon.
- `aggregate.py` refactored: composite formula now **3-lane polarity-first**
  (price 0.30 / retail polarity 0.50 / retail attention 0.20). News digest
  is secondary context only — displayed on card but does NOT enter composite.

**Lexicon (v1.1)** — `config/retail_lexicon.yaml`:

- 120 bull + 138 bear terms covering English / Chinese / WSB / PTT slang.
- Curated by Gemini suggestions filtered by Codex. Skipped high-noise
  emoji (🔥💪🤡💩), ambiguous META/COIN naked whitelist, substring-risk
  qt/qe; corrected 軋多 from bull → bear (it's a long squeeze).
- 137 cashtag-only tickers (AI / ON / X / IT / FOMO / etc. require `$`).
- 41 blocklist acronyms rejected even with `$` (USA / IPO / FED / CPI /
  ATH / YOLO / FUD / DCA / GAAP / FCF / ROIC / ROE / NAV / ESG / etc.).
- 12 high-liquidity naked whitelist (NVDA / TSLA / AAPL / AMD / SMCI /
  PLTR / MSFT / AMZN / GOOG / GOOGL / NFLX / BABA).
- 141 macro topic terms across 9 buckets.

**Codex review must-fix verified by 49 unit tests**:

1. `$NVDA` cashtag always wins; naked rejected for ambiguous English-word
   tickers; blocklist blocks even cashtag form.
2. Span-masked polarity — `short squeeze` → bull (1 hit), not `short` →
   bear; `pump and dump` → bear (1 hit), not pump + dump.
3. Market-wide bucket fires for sectorless macro posts.
4. Inclusion thresholds demote single-mention tickers to `low_confidence`.

**Composite formula trace** (Tech sector smoke):

- trending_tickers: NVDA polarity +0.761, engagement 11.32
- polarity lane: 0.50 × 0.761 = +0.3805
- attention lane: min(11.32, 50)/50 × sign(+) = 0.226 → 0.20 × 0.226 = +0.045
- price lane skipped (smoke used --skip-predict)
- total_w = 0.70; composite = 0.426 / 0.70 = **+0.608** → strong_bull ✓
- framing: "散戶 polarity +0.76 (NVDA); 新聞 2 篇中性。資料部分缺。"

**UI changes** (page-radar.js + radar.html):

- Card 3-line metrics reordered: **Price 5d → Retail polarity → News
  context** (polarity now primary).
- Visual polarity bar (−1 to +1) anchored at center; green right, red
  left, stone-grey within ±0.20.
- Card hover tooltip shows `signal_lanes` breakdown + top 3 sample posts
  for audit.
- New market-wide buzz strip above sector grid renders topic pills with
  polarity (`Fed +0.45`, `recession -0.55`).
- Tooltip `RADAR_TERMS.retail_sector_pulse` rewritten to document 3-lane
  composite formula and polarity-first philosophy.

**daily_update.sh changes**:

- Added Step 9.4 (`trending_tickers.py`) before Step 9.5 (`aggregate.py`).
  Both non-fatal.

Validation:
- `tests/test_aggregate.py` → 22 OK
- `tests/test_trending_tickers.py` → 27 OK
- `node --check Dashboard/page-radar.js` → no syntax errors
- E2E smoke (fixture 8 posts → trending → aggregate): Tech sector composite
  +0.608 strong_bull verified, formula traceable.

---

## 🟢 Session Note (v3.19.1 → v3.20.0) — Retail Sector Pulse · 散戶視角分產業

User asked for a new Tactical Opportunity Radar layer that surfaces, per
sector, the retail-perspective sentiment + multi-day direction. Existing
infrastructure had per-ticker stage (narrative-pulse), per-theme heat
(thematic-screener), and market-wide regime, but nothing per-sector that
combined "news polarity + Reddit chatter + 5d direction" into a single
view for the 11 GICS sectors.

Built `skills/retail-sector-pulse/`:

- `scripts/aggregate.py` reads `news_logs/*_digest.json` (verdicts with
  `affected_sectors[]` + `net_impact_score`), `narrative-pulse-detector/
  cache/<TICKER>_<DATE>.json` (retail_mention_multiplier), and
  subprocesses `short-term-target/predict.py` for each `SECTOR_TOP_5`
  ticker (55 total). Per-sector record carries news / retail / 5d
  signals plus composite_score and rule-based framing.
- `config/weights.yaml` keeps the composite formula declarative: 0.4
  news + 0.4 predicted + 0.2 retail_signed. Sector_aliases map handles
  messy digest values (`"Real Estate"`, `"Tech"`, `"Semiconductors"`,
  `"Defense"`, etc.) — verified against actual digest fixtures during
  exploration.
- 21 unit tests cover bucket boundaries, alias normalization, weighted
  decay, composite traceability, partial-signal re-normalization, and
  framing template output.
- `bridge.py` loads the JSON into `data['tactical']['retail_sector_pulse']`.
- `daily_update.sh` Step 9.5 runs the aggregator after narrative_pulse,
  before bridge.
- `Dashboard/radar.html` has a new section above Narrative Pulse;
  `Dashboard/page-radar.js` adds `renderRetailSectorPulse()` + a new
  `RADAR_TERMS.retail_sector_pulse` tooltip entry. 11-card 4-column
  responsive grid with composite pill, 3-line metric rows, framing
  one-liner, and top-tickers footer.

Codex review during planning caught two contradictions in the draft
plan:

1. "Daily + intraday 4h refresh" in Assumptions vs "intraday deferred"
   in Non-Goals. Picked daily-only for V1 — defers the
   dashboard_server daemon + cache invalidation surface to V3.21+.
2. UI E2E originally said "刻意把 cache 拿掉". Replaced with
   `--sector-override Sector=insufficient_data` CLI flag so testers
   never need to touch real cache.

Known coverage limitation: `SECTOR_TOP_5` tickers (AAPL, LLY, XOM,
BRK-B, AMZN, …) are mostly NOT in the narrative-pulse `batch_scan`
universe today, so `retail_mention_multiplier` is None for most
sectors on initial ship. Aggregator falls back gracefully
(re-normalizes composite weights to available signals). V3.20.1
backlog: expand narrative-pulse universe to include SECTOR_TOP_5 so
retail volume signal is always populated.

Validation:
- `python3 skills/retail-sector-pulse/tests/test_aggregate.py` → 21 OK
- `node --check Dashboard/page-radar.js` → no syntax errors
- `python3 skills/retail-sector-pulse/scripts/aggregate.py --skip-predict
  --output /tmp/rsp.json` → 11 sectors, framing zh+en correct, news
  sentiment correctly joined via alias map
- Full integration with predict.py (55 tickers) running at session
  close — verifies E[R] dispersion across sectors

---

## 🟢 Session Note (v3.19.0 → v3.19.1) — Codex review fixes for V1.1

Codex did a post-implementation review of V3.19.0 and surfaced three real
bugs:

1. **Stage 1 SMA200 "hard gate" was not hard.** Weights `0.4 / 0.3 / 0.3`
   meant `media_quiet + no_sell_side_raise = 0.6 = min_conf`, so a
   below-SMA200 ticker could still classify as Stage 1 brewing as long as
   it was media-quiet with no sell-side raise. Reproduced with
   `sma200_breakout_days_ago=None, price_to_sma200_ratio=0.95`,
   `media_mention_30d=5, pt_raise_60d=0` → stage=1, conf=0.6.
2. **Post-normalize probs could exceed clamp `[0.05, 0.80]`.** Clamp
   happened first, then simple proportional `prob *= scale` could re-inflate
   a clamped 0.80 above the cap. Reproduced with raw `[0.90, 0.05, 0.05]`
   → final `[0.889, 0.056, 0.056]`. The existing test only asserted
   `0 ≤ prob ≤ 1`, so it missed the bug.
3. **batch_scan emitted `"version": "1.0"`** despite the V1.1 breaking
   payload; `schema.md` still documented the V1.0 shape and never
   mentioned `prob_base`, `prob_breakdown`, `expected_return_pct_base`,
   or the shifted `expected_return_pct_pre_macro` semantics.

Fixes:

- **#1**: weights re-balanced `0.5 / 0.25 / 0.25`. `media + no_sell_side = 0.50 < 0.60`,
  so the breakout signal is now effectively mandatory for Stage 1.
- **#2**: replaced naive normalize with `_bounded_normalize()` — water-filling
  iteration that distributes deficit/excess proportional to each scenario's
  headroom toward the relevant bound. Post-normalize values respect
  `[clamp_lo, clamp_hi]` AND `Σ = 1`. Breakdown's `_normalize` entry now
  annotates the bounded behavior.
- **#3**: `batch_scan.py` → `"version": "1.1"`; `schema.md` rewritten
  with V1.1 scenario shape, three-layer E[R], snapshot archive path,
  and an explicit "V1.1 Breaking Schema Changes" table.

Added 2 regression tests reproducing Codex's exact fixtures
(`test_below_sma200_quiet_does_not_classify_stage_1` +
`test_bounded_normalize_respects_clamp`). 30/30 tests pass.

Validation:
- `python3 skills/narrative-pulse-detector/tests/test_stage_classifier.py` → 30 OK
- `python3 skills/narrative-pulse-detector/tests/test_fetch_inputs.py` → 3 OK

### Codex round 3 follow-up — cache + dashboard staleness

After the V1.1.1 commit Codex flagged two more release-hygiene issues:

1. **`weights_version` was not bumped after the post-review fixes.** YAML still
   read `v1.1`; `pulse._cache_fresh()` invalidates on version-string mismatch,
   so existing morning V1.1 cache files (under
   `skills/narrative-pulse-detector/cache/`) would survive into evaluations
   that should have triggered the fixed code paths. Bumped to `v1.1.1` with a
   history comment block in the YAML.
2. **`Dashboard/narrative_pulse.json` was still V1.0.** The daily flow had not
   re-run since the V1.1 series shipped, so the live dashboard payload was
   `version: 1.0`, `weights_version: v1.0`, and lacked
   `expected_return_pct_base` / `scenario_model_version`. Re-ran
   `batch_scan.py --no-cache` to regenerate the full universe under V1.1.1.

Both fixes folded into the V3.19.1 release. No code change beyond the
weights_version string + the batch_scan rerun.

---

## 🟢 Session Note (v3.18.4 → v3.19.0) — Narrative Pulse V1.1 per-ticker scenario math

User flagged that the short-term radar showed every Stage 1 ticker with
identical `+11.2%` E[R] and identical 55/25/20 scenario probabilities — no
information density. Codex's review surfaced a second issue: `fetch_inputs.py`
returned `sma200_breakout_days_ago = 0` when the latest close was *below*
SMA200, which satisfied the Stage 1 brewing rule and let below-SMA200 tickers
masquerade as fresh breakouts.

User priority: not a black-box capped delta. Wants every probability movement
to map to a named YAML rule with a condition and a delta, so weekly
calibration is "edit YAML, not Python."

- Fixed SMA200 breakout semantics at fetch layer (close<SMA200 → None).
- Tightened Stage 1 `sma200_breakout_recent` rule with explicit `is not None`
  + `price_to_sma200_ratio >= 1.0` hard gate.
- Bumped `weights_version: v1.0 → v1.1` so cache invalidates automatically.
- Added `scenario_adjustments:` block to `stage_weights.yaml` for Stage 1, 2,
  4, 5 — Stage 3 (acceleration) intentionally not adjusted. Global
  `prob_clamp: [0.05, 0.80]` + `normalize: true`.
- Implemented `_apply_scenario_adjustments()` in `classify_stage.py` —
  reads YAML, applies deltas, clamps, normalizes, records full breakdown
  per rule.
- Output now carries three E[R] layers: `_base` (V1.0 prior, control for
  5/31 review), `_pre_macro` (V1.1 ticker-adjusted, no macro), and the
  final value. Dashboard renders only the final; the others sit in the
  JSON for analytics.
- `expected_return_pct_pre_macro` semantics shifted (raw prior → adjusted
  sum). Original V1.0 meaning moved to new `expected_return_pct_base`.
  CHANGELOG records this as a breaking schema change.
- `batch_scan.py` now writes a daily snapshot to
  `skills/narrative-pulse-detector/snapshots/<YYYY-MM-DD>.json` for the
  5/31 review (will join momentum-journal forward returns to compute IC /
  hit rate for `base` vs `pre_macro` vs `final`).
- 31 unit tests pass (3 new fetch tests + 7 new V1.1 adjustment tests +
  21 pre-existing). Smoke run on 8 Stage 1 tickers shows V1.0 baseline =
  11.15 (identical) → V1.1 = 5 unique E[R] values across 8 tickers.

Validation:
- `python3 skills/narrative-pulse-detector/tests/test_stage_classifier.py` → 28 OK
- `python3 skills/narrative-pulse-detector/tests/test_fetch_inputs.py` → 3 OK
- `python3 skills/narrative-pulse-detector/scripts/batch_scan.py --tickers AAPL,CSCO,TXN,ASML,WFC,MA,AXP,STM --no-cache` → 8/8 successful, dispersion confirmed.

Tooltip showing `prob_breakdown` on the radar Dashboard is deferred to
V3.19.1 — `Dashboard/page-radar.js` is monolithic and a hover patch is a
separate diff.

5/31 review path: if `pre_macro` IC does not beat `base`, set every
`scenario_adjustments.*.prob_deltas[].delta = 0` in YAML — equivalent to
V1.0 fallback with no code rollback.

---

## 🟢 Session Note (v3.18.3 → v3.18.4) — Momentum rank-score UI wiring

User asked whether the momentum dashboard page had corresponding UI changes for
the new calibrated momentum ranking. It did not: V3.18.2 generated `rank_score`
in the screen/journal/event-index path, but the dashboard table still displayed
and sorted only by raw `score`.

- Added `rank_score` ingestion in `bridge.py`.
- Added a dedicated rank-score table column in `Dashboard/momentum.html`.
- Updated `Dashboard/page-momentum.js` to default-sort by calibrated
  `rank_score`, with fallback to raw `score` for legacy rows.
- Kept the raw `score` slider as the quality threshold so the page now separates
  "base score passes" from "calibrated rank prefers this ticker".

Validation:
- `python3 -m py_compile bridge.py`
- `node --check Dashboard/page-momentum.js`
- `node --check Dashboard/i18n.js`

---

## 🟢 Session Note (v3.18.1 → v3.18.2) — Momentum-screen calibration

User asked why momentum review showed very low screen-run hit rate, then asked
to implement the improvement plan. Implemented momentum-specific calibration
without changing investment protocol buy thresholds:

- Added `rank_score` to momentum screen output and journal flow. Raw `score`
  remains unchanged; Top-N ranking now uses calibrated `rank_score`.
- Ranking rewards Stage 2 / RS leader / fresh 20-50 cross / near-high strength
  and penalizes squeeze/high-short/VCP-only/death-cross/bearish-MACD/extension
  patterns that were dragging recent per-ticker results.
- Added soft cooldown for names repeatedly appearing in recent journal Top-20.
- Dashboard momentum runs now default to conservative leader filters:
  min score 65, RS >= 60, NHP >= -10%, and exclusion of squeeze/death-cross names.
- Added event-index momentum aggregate metrics so future reviews can separate
  screen-run hit rate from per-ticker hit rate and neutral-heavy outcomes.
- Fixed `screen.py --tickers ...` being ignored because `--universe` had a
  default inside a mutually-exclusive group.

Validation:
- `python3 -m py_compile scripts/verdict_rules.py scripts/build_event_index.py scripts/extractors/momentum_extractor.py skills/momentum-monitor/scripts/screen.py skills/momentum-monitor/scripts/journal.py dashboard_server.py`
- `python3 skills/momentum-monitor/scripts/screen.py --tickers AAPL,MSFT,NVDA --max-age 9999999 --output-dir /private/tmp --md-only --cooldown-snapshots 0 --top 3`
- Conservative custom-ticker filter smoke with cached data.

---

## 🟢 Session Note (v3.17.0 → v3.17.1) — Transition overlay review fixes

User asked Codex to first commit the previous feature work, then fix Codex review
findings so Claude can review the fix separately.

- Created feature baseline commit `684b5e7 feat(protocol): add transition overlays`.
- Fixed `earnings-analyst` segment parsing: `business_mix_shift_overlay` now
  flattens `products` / `regions` nested rows from `fetch.py`, excludes metadata
  such as `fiscal_year`, and includes the 25% EMERGING boundary.
- Fixed `earnings-valuation-forecaster`: markdown now renders the
  Revenue-Margin Matrix, `transition_case` emits `transition_case_mtime`, and
  loaded EA bundles backfill `transition_signature_mtime` from cache mtime when
  older caches lack it.
- Renamed V3.17 test files to unique module names, eliminating pytest import
  mismatch when both skill test directories are collected together.
- Aligned protocol/schema/changelog wording for annual PE + FY segment YoY
  numeric anomaly.

Validation:
- `python3 -m pytest skills/earnings-analyst/tests/test_earnings_analyst_v3_17.py skills/earnings-valuation-forecaster/tests/test_forecaster_v3_17.py` → 31 passed
- `python3 -m pytest skills/earnings-analyst/tests/test_earnings_analyst_v3_17.py skills/earnings-valuation-forecaster/tests/test_forecaster_v3_17.py skills/narrative-pulse-detector/tests/test_stage_classifier.py` → 52 passed
- NVDA cache smoke: business mix candidate is `Data Center`, not `fiscal_year`.

---

## 🟢 Session Note (v3.15.1 → v3.15.2) — Break News V4 final-gate polish

Opus final-gate review of Gemini's V4 implementation + codex's V4 review fixes.
Four downstream gaps caught; each would have silently degraded the V4 KG-first
design without breaking tests.

- **Depth-policy shallow_score threshold mis-scaled** (`debater.py:143`):
  `abs(score) >= 7.0` never fires — Stage 1 triage emits values on a ~0–3 scale
  (`abs(s) >= 1.5` important, `>= 3` strong). Dropped to `3.0` to match the
  existing strong gate. Sample real bn item: `shallow_score=2.0`.
- **Futu Push round-cap regression** (`debater.py:189`):
  `item.get("source") == "Futu Push"` compared a dict to a string, so
  `MAX_ROUNDS_FUTU=2` never applied. Fixed to read `.get("name")`.
- **Mega-cap regex case-sensitive** (`debater.py:156`): added `re.IGNORECASE`
  so headlines that render tickers as `Nvda` still trigger high-priority.
- **Dashboard supply-chain UI missing provisional badge**
  (`page-supply-chain.js:53-64`): `RELATION_EVIDENCE` only had `corroborated`
  and `llm` entries; new `break_news_provisional` level was rendering as
  raw key string with no styling. Added amber `◐` badge with BN source-count
  suffix.

Validation:
- `pytest tests/` → 75 passed
- `python3 scripts/break_news/validate.py` → rc=0, 458 files
- `python3 scripts/nexus/build_graph.py --tier 1,2 --dry-run --enable-direct-edge` → 166 nodes / 594 edges / 638kB (under 5MB cap)

Not fixed (out of scope / contested):
- BN-provisional weight (0.2) < llm_relation (0.4) — semantically odd (some
  evidence rates lower than no evidence) but locked in V4 plan + tests.
- `merge_edges` keeps only first edge's metadata — no real impact today since
  `cross_item_count` is identical across duplicates, but worth revisiting.
- Symmetric predicates (`COMPETES_WITH`, `CO_DEVELOPS_WITH`) not order-
  normalized; (A↔B) and (B↔A) would dedupe as 2 edges. Minor.
- `validate.py` uses date-based strict gate instead of `summary.schema_version`
  field — works but a replayed old debate would be marked strict.

---

## 🟢 Session Note (v3.15.0 → v3.15.1) — Break News V4 Codex review fixes

Codex review of Gemini's Break News V4 implementation found 5 issues; this patch fixes them without expanding scope:

- **Universe loader fix**: `_load_universe_tickers()` now supports `heatmap_universe.json` dict-list entries, so neutral early-stop correctly detects tracked tickers.
- **Nexus metadata persistence**: `Edge` now carries `metadata`, and `merge_edges()` preserves it, so provisional Break News direct edges keep `is_break_news/provisional/support_count/cross_item_count/confidence_avg`.
- **Supply-chain evidence precision**: Break News provisional evidence now checks relation type and direction. `COMPETES_WITH` or reversed `SUPPLIES_TO` no longer corroborates a supply-chain hop.
- **Legacy schema fallback**: missing `support_count` is treated as `1` during the transition window.
- **Regression tests added**: `tests/test_break_news_v4.py` plus supply-chain evidence compatibility tests cover the reviewed failure modes.

Validation:
- `pytest tests/test_break_news_v4.py tests/test_supply_chain_enrichment.py` → 11 passed
- `python3 scripts/break_news/validate.py` → rc=0, 458 files
- `python3 scripts/nexus/build_graph.py --tier 1,2 --dry-run` → 166 nodes / 554 edges / 620471 bytes
- `python3 scripts/nexus/build_graph.py --tier 1,2 --dry-run --enable-direct-edge` → 166 nodes / 596 edges / 638483 bytes

---

## 🟢 Session Note (v3.14.8 → v3.15.0) — Break News Debate V4 Implementation

成功實作 Break News Debate V4 改進計畫（KG-first 與供應鏈證據對齊）：

- **Debate Prompt 與 Thread 壓縮**: 重構 `prompts.py` 使用 `compact_thread_formatter` 滑動窗（包含壓縮後的 `kg_state` 與各 Agent 最後一條 comment 原文），引導 A/B 對立補強 second-order / supply-chain 與 contradiction，並保留 early-stop done 出口。
- **Summary 聚合指標優化**: 擴充 `build_summary_block()`，聚合 `support_count`、排除 confidence=null 的 `confidence_avg`、擷取 evidence snippets (最多 3 條，每條 ≤200 字，按置信度排序)，以及 round-by-round 的 `final_takes_by_round`，保留相容的 `final_take`。
- **Dynamic Depth Policy 與 Early-Stop**: 在 `debater.py` 實作優先度感知 depth policy (正常 2 輪/4 calls，高優先度 3 輪/6 calls)。依據來源可信度、binary_flag、abs(shallow_score) >= 7.0、`SECTOR_TOP_5` 權重、與技術 Regex `ALL_DOMAIN_PATTERNS` 判定優先度。在 Round 1 結尾，依據低關係密度、共識 neutral 且無 universe tickers、或雙方 complete 自動觸發 early-stop。
- **Transitional Strictness 校驗**: 更新 `validate.py`。歷史 log 寬鬆向下相容（忽略 round 遞減錯誤），2026-06-20 起的突發辯論 log 則強制執行嚴格 V2 欄位檢查，確保 rc=0。
- **Phase 2 Direct Edge 載入**: 在 `tier1_loaders.py` 修改 `load_break_news` 支援 `--enable-direct-edge` / `BREAK_NEWS_NEXUS_DIRECT_EDGE_ENABLED=1`。解析 structured relations，進行雙方 `support_count >= 2` 或跨日誌共現 pre-pass 判定，歸一化方向 (`CUSTOMER_OF` 反轉成 `SUPPLIES_TO`)，限制 weight <= 0.15 且標記為 provisional。
- **供應鏈三級證據權重優先序**: 在 `supply_chain.py` 的 `enrich` 重構關係證據判定，優先度為：`corroborated_relation` (1.0, 30天共現 >= 閾值) > `llm_relation` (0.4, yaml draft) > `break_news_provisional` (0.2, Nexus 圖譜中 provisional 邊)。

驗證結果：
- `validate.py` 校驗既有 458 份突發辯論 log 完美通過 (`rc=0`)。
- `test_summary_aggregation.py` 單元測試順利通過，涵蓋 null 置信度排除、最優 final_take 挑選與 snippets cap。
- `build_graph.py --enable-direct-edge --dry-run` 順利載入 +40 條 (如 `SUPPLIES_TO`, `COMPETES_WITH`) provisional direct edges。

---

## 🟢 Session Note (v3.14.6 → v3.14.7) — Codex 3 nits closure

Codex review of v3.14.6 抓到 3 個小瑕(2 P2 + 1 P3),全收:

- **P2-1 builder strict 過度宣稱**:v3.14.6 log 寫「builder/validator/pytest pass strict=True」,實際 `build_sector_intel.py:289` `canonicalize_sector_name(raw_name)` 沒 strict。但這是 by design — builder 故意吸收 LLM 別名(`"Financial Services"` → `"Financials"`)讓 valuation cache lookup 能命中;若 LLM 寫完全亂 cache miss 會在下一行 hard-fail。**Validator 才是真正擋 schema 漂移的閘**。CHANGELOG / SESSION_NOTES 改寫成「validator + pytest 用 strict;builder/digest/fetch 維持寬鬆 canonicalize」。
- **P2-2 FTD source_file path 沒測試覆蓋**:v3.14.6 最關鍵的 correctness fix(從 latest cache 改 source_file)inline 在 `main()` 沒 unit test,未來 agent 可能默默 revert。本輪抽出 `verify_ftd_verbatim(phase0_ftd, root)` 純函數,加 6 個 test case 包括**反 regression「必須讀 source_file 不是 latest cache」**(寫 old + newer 兩個 cache,phase0_ftd 指 old,assert validator 用 old 過、不會被 newer 干擾)。
- **P3 SESSION_NOTES 數字錯**:v3.14.6 寫 4/4 pass,實際 12/12。本輪報告 18/18(加 FTD source_file 6 個 case)。

實測:`pytest tests/test_gics_sector_audit.py` 18/18 pass。`python3 sector/scripts/validate_sector_intel.py` 跑既有 intel rc=0(legacy FTD 軟跳過)。

版本 bump 3.14.6→3.14.7。Functional code 不變,只:(a) refactor 出 testable helper,(b) docs honesty。

## 🟢 Session Note (v3.14.5 → v3.14.6) — Sector validator hardening + 4 codex follow-ups

Codex review of v3.14.5 ship 抓到 4 點(2 correctness + 2 overclaim),全收:

- **P1-1 FTD verifier race condition**:v3.14.5 validator 拿「磁碟最新 FTD cache」跟 sector intel 比對,FTD daemon 若在 build 之後寫新 snapshot 就會把合法舊報告誤判 hallucination。修法:`build_sector_intel.py` 把實際讀的 FTD cache repo-relative path 寫入 `_phase0.ftd.source_file`(從 `layers.ftd.file`);validator 改成讀 **那個檔**比對,缺 source_file 的 legacy 報告 → 警告 + 跳過(不 fallback latest 以免誤殺)。
- **P1-2 N=5 dual-run criteria overclaim**:v3.14.5 CHANGELOG/SESSION_NOTES 寫「N=5 sessions, 0 hard diff > 1.0…」當成已 enforced 規格,但 calculator 只看當次 run,沒 history 持久化。本輪改寫為「per-run shadow check;N=5 promotion thresholds 已 document 但 history 持久化留下次 patch」。`SECTOR_CALC_STRICT=1` 仍只在當次 run 內 fail-fast,不跨 run 累計。
- **P2-1 validator 沒接 canonicalize**:v3.14.5 CHANGELOG 列了 `validate_sector_intel.py` 在統一 canonicalization 清單裡,但 diff 沒 import `sector_utils`。本輪真的接上:validator import `canonicalize_sector_name(strict=True)` 對 `sectors[].name` assert,LLM emit `"Financial Services"` 或 `" Technology "` 即 schema fail。
- **P2-2 `sector_utils` 缺 strict mode**:`canonicalize_sector_name` 對未知名永遠 warning + fallback。本輪加 `strict=False` kwarg(default 不破壞既有 caller),`strict=True` 時 raise `UnknownSectorError`。**validator + pytest** 用 `strict=True`;**builder / digest / fetch 維持寬鬆 canonicalize**(builder 故意吸收 LLM 別名 → canonical 形式;若 LLM emit 亂寫名而後續 valuation cache 找不到 key 仍會 hard-fail。validator 才是真正擋 schema 漂移的閘)。

實測:`pytest tests/test_gics_sector_audit.py` 12/12 pass(含新 strict mode + validator canonicalize 案例)。validator 跑既有 2026-05-20_sector_intel.json → legacy report warning + 跳過 FTD verbatim,其他 schema check rc=0。

未做(留下次):
- N=5 history file persistence(`sector/sector_logs/_calc_dual_run_history.json`)— 補上後 `SECTOR_CALC_STRICT=1` 可跨 5 run 算 promotion gate
- calculator Phase 2 — replicate Step 1-4 動態乘數心算

版本 bump 3.14.5→3.14.6。

## 🟢 Session Note (v3.14.4 → v3.14.5) — Sector protocol precision alias & score calculator shadow-run

使用者與 Codex review 要求優化與修復產業掃描協定 (Sector Protocol V1.4)，確保系統算術正確性、防止靜默失效及漸進遷移原則。本輪實作採納 P0/P1/P2 重點：

- **共享別名模組統一 (A, D)**：
  - 新增 `sector/lib/sector_utils.py`，定義 11 大 Canonical Sector 名稱，維護顯式 `SECTOR_ALIASES` 與 `PROJECT_TO_FMP` 對齊字典。
  - 將名稱對齊完全引入口入端 `fetch_sector_valuation.py`（對齊 FMP API）、`sector_digest.py`、`step6_overlay.py` 及 `build_sector_intel.py`，完全消除因空格/大小寫引起的 valuation 快取載入失敗與 key 漂移，修復 Financials `n/a` 問題。
  - 為 `tests/test_gics_sector_audit.py` 加上 `@pytest.mark.skipif(not theme_caches)` 裝飾器，防止 CI 在無快取環境中報錯，且測試已完全通過。
- **心算分數計算器雙軌運行 (B, C)**：
  - 建立 `sector/scripts/sector_score_calculator.py`，當前為 Phase 1 (Summation and Post-scaling sanity check) 弱驗證版本，驗證 4 大 lane 分數加總、估值 penalty 漂移與 FRED 乘積後 cap 上限（**注意：此版本暫未 replicate Step 1-4 動態乘數心算，Phase 2 留下次擴展 Step 1-4 multiplier replication**）。
  - 驗證 `score_components` 欄位確為 4 大 lane (每維度 `[0, 25]`，相加上限為 `100`，加總公式正確)。
  - **Per-run** shadow 檢查;promotion thresholds (N=5 sessions, 0 hard diff > 1.0, ≤2 soft diff 0.5-1.0, 0 valuation penalty drift) **僅文件記載,未實作 history 持久化**(v3.14.6 honesty fix)。`build_sector_intel.py` shadow 運行中當次抓到 Industrials 板塊 composite score LLM 與心算的 2 分差距 (50 vs 48)。
- **FTD Verbatim 反幻覺比對**：
  - 在 `build_sector_intel.py` 內將 `ftd_timeline` 資訊組裝橋接寫入 `_phase0.ftd`。
  - 在 `validate_sector_intel.py` 內直接載入磁碟最新 FTD 快取之 `ftd_status_text` 字串原值，進行精確字串比對，拒絕 LLM 的二次加工重寫。
- **FRED 快取與新鮮度路徑防護**：
  - `step6_overlay.py` 引入口專案根目錄定位器 (尋找 `CLAUDE.md`) 計算絕對路徑，確保 Cron 執行時相對路徑漂移不影響 `fred_latest.json` 載入。
  - 修改 `sector/phase_0.md`，統一以產出的 `generated_at` < 3 小時為新鮮度基準，不看 `mtime`。

版本 bump 3.14.4→3.14.5。

## 🟢 Session Note (v3.14.3 → v3.14.4) — Supply-chain FMP verification + relation evidence

使用者要求依 Claude review 釘死供應鏈頁與資料來源優化，尤其避免 FMP 被誤用成「供應鏈關係已驗證」。本輪實作採納 P0/P1/P2 重點:

- **刪除新 `verified` verification level**:保留既有 `grounding=verified` 代表 tracked universe；新 `verification_level` 只含 `corroborated / fmp_profile / name_match / llm_only / fmp_unavailable`。
- **FMP 只驗公司，不驗關係**:`fmp_profile` 文字明寫 relation NOT verified。profile batch + shared cache + file-backed daily budget，缺 key / quota / 403/429 / network 都降級 `fmp_unavailable` 不爆頁面。
- **Cache / budget 釘死**:`skills/_shared/fmp_supp_cache/supply_chain/{profile,peers,search_name}`，profile TTL 7d、peers/search 24h、`_budget_<YYYY-MM-DD>.json` UTC reset，預設 budget 150。
- **Ticker disambiguation**:US exchange allowlist + aliases(TSMC→TSM、GOOG/GOOGL、BRK class shares、Facebook/Meta)。lookup 順序:exact profile → hand alias profile → search-name US exchange top-1 → fallback。
- **Relation evidence**:不用 FMP，不掃 prose；只算近 30 天 digest verdict `tickers_mentioned[]` 兩端同時出現。`>=3` → `corroborated_relation`，否則 `llm_relation` 並提示 low-volume edge 不等於虛構。
- **Frontend composite rule**:節點卡只顯示一個 primary company-verification badge；grounding 只放 detail panel。detail panel 增 FMP profile / peers / alias / reasons，edge row 顯示 relation evidence badge。
- **測試**:`tests/test_supply_chain_enrichment.py` 覆蓋 no-key fallback、alias profile、budget exhausted、name-match、strict co-mention。驗證 `py_compile`、pytest 5/5、`node --check`。

版本 bump 3.14.3→3.14.4。

## 🟢 Session Note (v3.14.2 → v3.14.3) — News pipeline Stage 1 quality + validator cross-check

Codex review 對 news 頁面提 7 點,review 後確認真正最大弱點是 **Stage 1 選題品質**(不是 protocol 流程防呆)。律所徵案 / Astoria condo PR / 個人理財 fluff 經常 advance 到 Stage 2,4-agent debate 把垃圾新聞寫得像高價值分析。具體案例(2026-05-20 production digest):n0197 Johnson Fistel about FLGT → BEARISH deep verdict、n0038 PARISIAN Condominium Debuts → stage2、n0107「I inherited a house」→ shallow top 10。

**User 明確要求一次上 P0+P1,但測試必須真跑,不准只 py_compile**。實作 P0a-f + P1a-b(8 件) + 38 個 pytest tests + 真實 2026-05-20 raw regression:

- **P0a hard-block negative-content**:`_BLOCK_PATTERNS` 三類 regex(law_firm_solicitation / real_estate_pr / personal_finance_advice),命中即 continue。
- **P0b headline-template dedup**:`_headline_template_key` normalize ticker/$/date/DOW 後 dedup,跨 N ticker 模板只留首條。
- **P0c content-aware credibility**:`effective_credibility(item, head, summary)` 把 provider HIGH × press-release marker 降為 MEDIUM、opinion/personal-finance → LOW。advancement gate 走 effective_credibility,堵 raw HIGH 短路。
- **P0d 397→313 cap → env `STAGE1_MAX_ITEMS=800`**:預設 800,2026-05-20 raw 397 全 scored(過去丟掉 84 條尾端)。
- **P0e validator cross-check**:`_cross_check_files()` 讀同日 triage.json,assert stage1_count match + deep verdict subset of stage2_items。loose / strict mode 兩路。
- **P0f headline_zh = None**:stage 1 不假譯,留 downstream digest LLM 補 top-N。
- **P1a `assemble_digest.py` git mv to `news/scripts/archive/`** + README + protocol footnote。
- **P1b rule-based classifier**:priority-ordered regex,修掉 FLGT shareholder loss 誤判 monetary_policy。簽名不變,break_news poller 沿用。

**真實 regression 結果**(2026-05-20 raw 397 條): items_scored=394、items_blocked=3、blocked_counts={law_firm:1, real_estate:1, personal_finance:1}。Stage 2 deep 5 slot 中 2 個 noise(FLGT、condo)換成 genuine signal(Dow -320pt、Schwab Q2 sentiment)。`pytest tests/news/ -v` 38/38 passed。

Wave 2(lane completeness validator + LLM 翻譯 top-10 digest)留下次,牽涉 protocol 改寫 + token budget。bump 3.14.2→3.14.3(patch)。

## 🟢 Session Note (v3.14.1 → v3.14.2) — Skills × Codex compat Wave 1

Codex 提出 5-skill 相容性 proposal(earnings-analyst / market-news-analyst / theme-detector / market-top-detector / supply-chain-event-analyst)。Review 後採 3-wave 風險順序:Wave 1 低風險文檔 + sidecar、Wave 2 fetch 主線化、Wave 3 earnings narrate via router。**核心架構決定**:narrate / narrative 步驟走 `scripts/_shared/model_router.run_role()`,不走 deterministic-only — 讓 codex/claude/gemini 任一都能驅動,deterministic 只作 router 全失敗的 fallback。Plan 全文:`~/.claude/plans/llm-llm-queue-pythone-script-whimsical-beacon.md`

本輪實作 **Wave 1 三件**:

1. **market-top-detector doc + path**:`sector/market_top_yfinance.py` sys.path 從 `~/.claude/skills/...` 改 repo-local(同 v3.14.1 daily_update fix 的對應修)+ `SKILL_SCRIPTS_PATH` env override。SKILL.md 重寫 Execution Workflow,canonical entry 改為 yfinance adapter,WebSearch 從必需降為 optional CLI flags(`--breadth-50dma` / `--put-call` / `--margin-debt-yoy` / `--vix-term`),缺失欄位寫 `data_quality.missing_optional`。
2. **theme-detector narrative_confirm.py sidecar(evidence-grounded)**:新 script 走 `run_role("narrative_confirm", ...)`,top-5 themes 跑 LLM 確認後寫 sidecar `theme_detector_<ts>.narrative.json`。Codex review 抓到原版兩個 P0:(a) prompt 沒餵 evidence → 模型靠記憶 / 幻覺 URL bump;(b) `medium->high` 沒強制 `primary_source` non-null。**已修**:從 `news/news_logs/*_digest.json` 14 天 verdicts 撈出每個 theme 的封閉候選 evidence(按 representative_stocks ∩ tickers_mentioned 或 industries ∩ affected_sectors),top-6 / theme 餵 prompt;模型必須引用 `news_id ∈ allowed_ids`,否則 validator 自動降為 `none` 並計入 `dropped_bumps_no_evidence`。Router 失敗 → `narrate_mode=skipped` 空 bump 不報錯。
3. **bridge.py 接 sidecar consumer**(codex review #3):新 `load_theme_narrative_bumps()` 讀 sidecar,輸出 `data["theme_narrative_bumps"]` + `load_theme_overrides()` 自動對 paradigm-shift 主題套用 confidence bump(`narrative_bumped=true`、`confidence="High"`)。Sidecar 不存在 = `status: "no_sidecar"`,絕不報錯。
4. **supply-chain-event-analyst DEPRECATED**:SKILL.md 頂部加 banner,指向 `scripts/nexus/supply_chain.py`。`chain_mapper.py` 留作 FMP quick probe。
5. **Untrack 29 個 stale .pyc**(codex review #4):`__pycache__/*.pyc` 早就 commit 進 repo(gitignore 加上去前的事)。本輪 `git rm --cached` 一次清掉。Daemon-state(data.json / nexus_graph.json / llm_usage.json)維持 tracked 但不進本 commit。

Wave 1 全部走 model_router governance 一致(V3.7.0 既有層)。Codex review 4 點全在 ship 前修完。Dry-run 驗證:evidence_window=14d / pool_size=232 / 6 候選/theme。bump 3.14.1→3.14.2(patch)。

Wave 2(market-news-analyst fetch.py 主線化 + source_mode schema)等本 patch ship + 觀察 3-5 day,確認 daily_update 仍綠 + Dashboard 無 regression 再進。

## 🟢 Session Note (v3.14.0 → v3.14.1) — daily_update.sh 可靠性修正

Codex review 指出 daily_update.sh 4 個 priority 問題,全證實成立:

1. **Step 1 `~/.claude/skills/...` 路徑漂移** — repo 內已有 `skills/market-breadth-analyzer/`,跨機器/agent 跑不同版本。改 repo-local。
2. **Step 4 FRED 「非致命」是錯的** — `python3 ... > /dev/null` 不在 if/&&/|| 條件內,`set -e` 上一旦非零 shell 立刻 exit,line 64 的 `if [ $? -eq 0 ]` **永遠不會跑**。包 `set +e` ... `set -e` 才真的非致命。
3. **Step 5.5 `| tail -3` 吃 rc** — `REFRESH_RC=$?` 拿 tail 的 rc(永遠 0),python 失敗訊號被吞。加 `set -o pipefail` 修正。
4. **Step 8 cron 內 `pip install networkx`** — 卡網路/污染環境/失敗無聲。`build_graph.py` 本有 `pagerank_lite` fallback(驗證:`networkx not installed; using pagerank_lite + degree fallback`),直接移除 install。

Bonus:結尾 banner 原固定講「FRED 已更新」即使 skip / fail 也照講,加 `FRED_STATUS=ok|failed|skipped` 三態,訊息對應實際狀態。

Helper 化(`run_hard_step`/`run_soft_step`)、Step 8 默認降級 tier 1+2、daily_update_<DATE>.log run summary 等 second-phase 優化留下次。bump 3.14.0→3.14.1。

## 🟢 Session Note (v3.13.0 → v3.14.0) — Nexus graph ticker-centric

使用者 `/goal` 設定:知識圖譜只要 ticker↔ticker 關係,news 改顯示在 ticker tooltip,不要 news 節點。原 V3.0 multi-type 800 節點(catalyst 328 / theme 123 / narrative 82 / sector 43 / ticker 224)把 ticker 之間的訊號淹沒,且 news 太搶眼。重構成 ticker-only graph:

- **build_graph.py 加 `_to_ticker_centric()`**:prune 後遍歷每個 ticker 的非 ticker 鄰居,把 catalyst → recent_news[]、theme → themes[]、narrative → narratives[]、sector → sector、thesis → theses[] 聚到 ticker.metadata,然後 filter survivors 只留 ticker,edges 只留兩端都是 ticker 的。內部 Tier 1/2/3 pipeline 完全不動。
- **合成 CO_THEME 邊**:沒了 theme hub,大部分 ticker 變孤立。每個 theme 取 top-12 tickers,每個 ticker 取 top-3 themes,pairwise 建 CO_THEME 邊。tier="synth"、confidence=0.6,weight 取 min(theme_edge_a, theme_edge_b)。爆炸控制:204 ticker × ~3 = ~593 CO_THEME 邊。
- **重算 centrality**:collapse 後用 ticker-only 拓樸算 degree/pagerank,避免被 theme/catalyst hub 中介人為膨脹。
- **page-graph.js 改 tooltip + detail panel**:hover ticker 卡片用 dark glassmorphism 顯示 6 則 recent news(headline + verdict color-coded + net_impact + date)+ themes chips(amber)+ narratives chips(emerald)+ sector(violet)。點擊後 detail panel 同步顯示 News / Themes / Narratives 區塊。edge 顏色依 type 區分(PEER_OF 藍 / SUPPLIES_TO 綠 / COMPETES_WITH 紅 / CO_THEME 琥珀淡),idle 有薄底讓拓樸可見,hover 強化。
- **UI 過濾列**:ticker-only 模式下隱藏無意義的 type checkbox,改成 edge type legend(同業 / 供應 / 客戶 / 競爭 / 合作 / 同主題)。

新 config flag `ticker_centric: true`(default)+ `ticker_centric_recent_news_per_ticker: 8`。Legacy 多型 graph 用 `ticker_centric: false` 跑(主要給 Tier 3 LLM NER 除錯)。

驗證:T1+T2 dry-run 204 ticker / 704 edge(PEER_OF 111 + CO_THEME 593)/ JSON 649 KB(原 2.5 MB)。NVDA / AVGO / AMD 等龍頭都帶 8 news + 12 narratives + 多 themes。bump 3.13.0→3.14.0。

**注意**:V5.0.x patch (A1/A2/A3) 仍未 commit,working tree 同時帶這兩組變更(validate_session_export / page-decisions / append_session_export / investment_protocol_v5_0)。下次 commit 要分 2 個 logical commit(invest V5.0.x + nexus ticker-centric)。

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

## 🟢 Session Note (v3.5.0 → v3.5.1) — 供應鏈圖例 tooltip

供應鏈頁底部 9 個圖例 pill 無說明。沿用 `sector.html` pill tooltip 模式:`page-supply-chain.js` 加 `SC_PILL_TIPS`(zh/en × 9:us/fl/pi/pv/verified/seen/llm/heat/stage)+ `initPillTooltip()`(mouseover/out 事件委派、量高翻轉定位);`supply-chain.html` 加 `#pill-tooltip` CSS + 元素,每個 `.sc-legend-item` 加 `data-tip-key` + `cursor:help`。熱度/商用階段 tooltip 含等級說明。bump 3.5.0→3.5.1。

## 🟢 Session Note (v3.4.1 → v3.5.0) — 供應鏈商用化階段 stage 標記層

User 在供應鏈探索頁建了 POET 鏈,外部檢討(ChatGPT)指缺量產 OEM/客戶(Luxshare/Foxconn Interconnect/Credo/Google/AWS/ASE/NTT)且缺「商用化階段」標記層。問題:資料量不足 vs 漏分析?3 Explore agent 勘查確認:`generate(theme)` 公司清單 **100% 來自 LLM 草稿**,專案 DB(nexus_graph/universe)從不參與選公司,只做事後 grounding → 缺公司是**生成/分析缺口**(prompt 硬上限 8–20 node + 「omit rather than guess」壓廣度),非資料量不足。stage 層則純缺功能。實作:(1) node 級 `stage` 欄(design_partner→revenue+unknown)— `supply_chain.py _STAGES`+`_normalise` 驗證、prompt schema、`page-supply-chain.js` STAGE 色階+node badge+詳情列、`supply-chain.html` CSS+圖例。(2) prompt 提完整度:node 8–20→12–32、模塊 2–3→2–4、omit 規則限上游、OEM+客戶層要求完整。(3) POET 鏈:**直接手動擴充**(非跑 LLM 重生成 — 會蓋掉現有中文校對)20→27 node,補 7 家 + 每 node 標 stage,新增 advanced_packaging 模塊。驗證:_normalise 27 node 全帶 stage、33 edge 無 drop、server 送出 enriched 鏈。grounding-assist(讓 generate 看 nexus 候選)刻意不做 — nexus 對光通訊 niche 太薄。5 檔。

## 🟢 Session Note (v3.4.0 → v3.4.1) — 供應鏈 stage 內模塊分組 + 邊線修正

供應鏈頁 stage 過去扁平一欄。使用者要求每 stage 分 2-3 個產業模塊(silicon → CPU/GPU加速器/記憶體/網通)。資料模型加 `modules: {layerId:[{id,label}]}` + node `module` 欄,`_normalise` 驗證、舊 YAML 隱式 `_default` 向後相容,prompt 要 LLM 每層產 2-3 模塊。`page-supply-chain.js` `layout()` 改兩層:stage 欄內 module 子面板垂直堆疊、欄頂對齊;`renderDiagram()` 畫帶框 `.sc-module` 面板,stage band 弱化為虛線。重生 cpo/hbm/openai/spacex 帶模塊。同時修兩個邊線 bug:(1) 隱形 spine 線 — 共用 objectBoundingBox 漸層在水平邊退化 → 改 per-edge userSpaceOnUse 漸層;(2) 同 stage 邊鼓圈 — 新增 `sidePath()` 同欄邊走右側 C 形虛線連接器。保留既有 edge corroboration(✓N)。Files:supply_chain.py + prompts/supply_chain_system.md + SCHEMA.md + page-supply-chain.js + supply-chain.html + 4 條 yaml 重生。bump 3.4.0→3.4.1。

## 🟢 Session Note (v3.3.2 → v3.4.0) — 新聞層整併 + 情緒趨勢上首頁 + 供應鏈佐證

User 質疑兩條新聞 pipeline(委員會 digest `news.html` / break-news 探索層)重複,且 break-news 趨勢圖該不該上首頁、digest 該不該餵趨勢圖、知識庫/供應鏈怎麼用 break-news 輸出。3 個 Explore agent 勘查後決策(user 全選推薦案):**不合併 pipeline,改移除冗餘的 Triage tab**。Phase 1:刪 `news.html` 🗂 Triage tab + `page-news.js` `renderTriageFeed/wireTriageButtons`(~270 行)+ `bridge.py extract_shallow_news`(`_raw_pub_map` 保留)。`news.html` 純委員會 digest;break-news「未閘 Raw 流」= 唯一未辯論新聞面。Phase 2:趨勢圖抽成 `Dashboard/trend-chart.js`(`window.TrendChart` module,自帶 CSS/i18n/30s fetch cache,compact 模式),break-news 用完整版、index.html `#risk-overview` 下方加精簡 widget(連往 break-news)。Phase 3:`trend_rollup.py compute_trends()` 加讀 `*_digest.json`,deep verdict ×1.8,headline fingerprint 對 bn 去重。Phase 4:`supply_chain.py enrich()` 加讀 `nexus_graph.json` ticker↔ticker edges(已含 break-news 關係),供應鏈邊標 `corroboration`,`page-supply-chain.js` 加 ✓N badge。關鍵發現:Nexus Tier1 `load_break_news()` 早已吃 break-news 實體+關係,Phase 4 是強化非新接線。驗證:bridge.py 後 data.json 無 `shallow_news`;trends API log_count 118 / 25 entities;supply-chain openai 鏈 6/24 邊佐證;trend-chart.js 200。RSS 抓取重工依 user 決定不動。10 檔。

## 🟢 Session Note (v3.3.1 → v3.3.2) — Break News 未閘 Raw 流 + 手動辯論觸發

突發辯論室 (`break-news.html`) 冷門時段空窗:poller 只把過 score gate(`|score|≥2`)的項變辯論項,週末/盤後沒新聞過閘 → 頁面停在舊資料看似壞掉(實為 server 隔夜停機 + 冷門時段)。先誤把 plan 套到「新聞戰情室」Triage tab 改 `bridge.py` — user 澄清後全 rollback,目標是突發辯論頁。最終做法:加一條**未閘 raw 流**。poller `run_once` 對每則非重複 item 收集 raw entry(含完整 triage + gate 結果 + `key`),寫 rolling `_raw_stream.json`(cap 150 / 汰 24h / dedupe);bn-creation 上限由 `break` 改 `continue` 讓 raw 捕捉不被截。新 `store.load_raw_stream/save_raw_stream/mark_raw_promoted`。新 API `GET /api/break-news/raw-stream`、`POST /api/break-news/raw/debate`(繞 gate `init_item` → `pending_debate` + 背景 `_bn_kick_debate_scan` 立即起辯論)。`break-news.html` trend strip 與雙欄間插可收合「未閘 Raw 流」面板,每卡 score/過閘狀態/age/來源 + 🔥 辯論鈕,`page-break-news.js` `loadRawStream()` 納 poll cycle。score gate **保留**,raw 流純探索層展示。測試:poller 跑出 11 entries(10 gated/1 passed),兩 API 端點 202/400 正常,手動觸發後 bn item 進 `debating` advance_reason=`manual_raw`。5 檔(store.py / poller.py / dashboard_server.py / break-news.html / page-break-news.js)。i18n.js 未動 — break-news 頁用自帶 `t()` helper。

## 🟢 Session Note (v3.3.0 → v3.3.1) — Supply-Chain 頁視覺強化

V3.3.0 的供應鏈頁功能完整但視覺弱(配色 ad-hoc、light 主題壞掉、節點扁平)。套 frontend-design 做大膽強化,純改 2 檔(`supply-chain.html` inline style + `page-supply-chain.js` render markup),layout 數學/資料流不動。改:(1) 配色全改 `var(--*)` token + `color-mix`,修好雙主題;(2) 控制列 → `.ea-cmdbar` 指令列風(`>` prompt、mono input、focus 翠綠光暈);(3) canvas 加點陣格背景,每層 = 帶色塊欄 + 編號 header chip;(4) 邊:spine 邊翠綠→琥珀漸層 stroke + `<animateMotion>` 流動粒子(上游→下游);(5) 節點卡:漸層 listing 色條、heat → 外發光(hot 紅/warm 琥珀/cold 藍)、hover 抬升、staggered reveal、badge 改 9px uppercase pill;(6) detail panel 改浮動卡 + listing 色條 header + 上下游邊列。bump 3.3.0→3.3.1。

## 🟢 Session Note (v3.2.0 → v3.3.0) — Supply-Chain Explorer

User 看 Nexus 知識圖譜(`graph.html`)覺得太雜(800 節點/3895 邊,MENTIONED_IN 佔 50% = hairball)。釐清後發現要的不是清理 hairball — 是「依主題探索美股供應鏈」(例:CPO 上下游價值鏈)。Nexus 無法服務:有向供應鏈邊 count=0,私有/外股玩家根本不在圖裡。決策:做獨立的 **Supply-Chain Explorer**,Nexus 自動圖不動。`scripts/nexus/supply_chain.py`(新)`generate(theme)` 用 Claude(reuse break_news `llm_drivers.run_claude`)草擬分層價值鏈 → 存可編輯 YAML `nexus/supply_chains/<slug>.yaml`;`enrich()` 即時加 grounding(verified=在 universe / seen=在 Nexus / llm_only)+ heat(Nexus 提及數)。新 API `/api/supply-chain/{list,themes,<slug>}` + `POST /generate`。新頁 `supply-chain.html` + `page-supply-chain.js`:分層 upstream→downstream 圖(每層一欄,HTML 節點卡疊在 SVG 邊層上,有向 bezier 箭頭,spine 高亮),節點 4 badge(可投資性色條/grounding/層級/熱度),選擇器 + 主題自由輸入 + 生成鈕。sidebar 加「供應鏈」入口。Seed `cpo.yaml`(18 公司 5 層 21 邊)。生成方式 = LLM 草稿 + Nexus 驗證 hybrid。維持紀律:Nexus 探索層,此頁為 curated view。Files:supply_chain.py + prompts/supply_chain_system.md + dashboard_server.py + supply-chain.html + page-supply-chain.js + utils.js + i18n.js + cpo.yaml(新)。

## 🟢 Session Note (v3.1.2 → v3.2.0) — Break News 3 日情緒趨勢圖

突發新聞辯論室的辯論 log 過去是孤立快照,看不出敘事「方向」隨時間怎麼演化。User 要的是「每收到一則新聞就修正當下趨勢往上/往下」的軌跡。先做了提及量排行榜,user 釐清後 pivot 成**情緒指數軌跡**:每則 debate = 帶正負號事件(BULLISH +1 / BEARISH −1 / NEUTRAL·SPLIT 0)× 影響力權重(shallow_score × 來源可信度),72 個每小時 bucket 經時間衰減 EMA(12h half-life)串成軌跡,`tanh(S/scale)` 限縮 [−1,+1] 且 scale 每實體自適應(各線用滿範圍)。無新聞時線自然衰回 0。`scripts/break_news/trend_rollup.py`(新)`compute_trends()` 算市場整體 / 各 sector / 各 theme 的 series。新 GET `/api/break-news/trends`(60s TTL)。`break-news.html` 頂部 `.bn-trend-strip`:`<select>` 實體選擇器 + 手刻 SVG area chart(零基線綠上紅下、clipPath 填色、時間軸刻度、hover 游標)+ 即時數值讀數。一次畫一條 = 不糾纏。維持探索層紀律:trend 面板不進 investment_protocol 決策。Files:trend_rollup.py(新) + dashboard_server.py + break-news.html + page-break-news.js。

## 🟢 Session Note (v2.12.0 → v2.13.0) — invest protocol subagent 對齊外部「專業分析師」模板

User 看了 4 套外部分析師 prompt 模板（技術 / 基本面 / 決策整合 / 消息），對照 V5.0 找出 ~25% 缺口（其實是 output 欄位沒結構化，不是邏輯黑洞）。改造分 4 個 phase 對應 4 模板：(A) Technical lane 補 smart_money_analysis + pattern_taxonomy(8 種強制分類) + 三件套 (market_strength / key_levels / high_prob_scenario)；(B) Fundamentals lane 補 moat_assessment + near_term_catalysts[] + bull/bear thesis 對偶；(C) News lane 補時間軸三段 (immediate_5d / medium_20d / decision_point_days) + cross_asset_spillover[]；(D) Phase 3 PM 整合層補 institutional_lens + decision_confidence_pct + scenario_odds (bull/base/bear 加總 100) + action_label (ATTACK/WAIT/DEFENSIVE)。action_label 與既有 final_action (BUY/STAGED/HOLD/SELL) **並存**不取代。bridge.py 把 7 個新欄位帶進 recent_analysis[]；Dashboard page-decisions.js 加 5 種新 pill（action / moat / pattern / strength / confidence%）。final_score 公式不動、舊報告可重現；validator 不擋（informational 階段）。Phase E (historical_analog) 工程量大，未做。

## 🟢 Session Note (v2.11.1 → v2.12.0) — radar 頁 per-theme mini heatmap + K-line drill + thematic-screener v0.3 enrichment

**[Part A — radar UI]** User 看 radar 頁想要每個 theme 自己的 finviz 風 mini heatmap（半導體 theme 內 TSM/NVDA/AMD 顏色顯示當日漲跌）+ 點個股看 K 線。同時不解 expanded panel 的 top 5 movers 怎麼挑出來。設計上 radar 區分兩個時間軸：mini heatmap = 今天（intraday，3min refresh），thematic-screener theme grid metrics = 5 天 horizon（每日 refresh）。第一版誤做成全市場 sector heatmap（與 sector.html 重複、517 ticker 拖累載入），反饋後 pivot 為 per-theme mini heatmap。實作：(1) 新後端 `/api/theme-heatmap` 讀 theme-detector cache 拿 representative_stocks，join 既有 `_heatmap_state.tickers` cache 拼 quote — **零新增 FMP 呼叫**；(2) theme card 內嵌 110px D3 mini treemap，tile size = √market_cap，color = % change；(3) 新 endpoint `/api/heatmap/intraday/<T>`（FMP `/stable/historical-chart/5min`，cache 15s 開/5min 關），click tile → Chart.js line + volume bar 上方滑入；(4) renderExpanded() 加 1 行 banner 解釋 movers 排序 = 5d 預期報酬 × 信心度。17 themes，16 有 ≥ 3 ticker 覆蓋。

**[Part B — thematic-screener v0.3 enrichment]** User 反饋「thematic-screener 推薦本來就很不準」+ 想看到小型股出現在 top 5 時被特別標出。盤點發現原 screener 只用 `5d target_pct × confidence` 排序，無 event 過濾、無 quality gate、無籌碼確認。新增 `skills/thematic-screener/scripts/enrich.py` — 讀 3 個既有 cache（profile / earnings-analyst / fmp_supp_cache）**零新 API call** + 2 個輕 FMP fetch（PT consensus + grades 30d）→ 算每 ticker 的 `enrichment_multiplier`（事件砍半 / 品質紅旗砍 40% / insider 買 ×1.3 / 機構加碼 ×1.2 / PT upside ±30% bound / 評等升 ×1.15）。`screen.py select_top_movers_ranked` 改用 `target_pct × confidence × multiplier` 排序，輸出加 `enrichment` / `raw_score` / `final_score` 三 field。Market cap 4 tier：large(≥$10B) / mid($2-10B) / small($300M-$2B) / micro(<$300M)。Dashboard `page-radar.js` `renderEnrichmentPills()` 渲染 mover card 上端 pill row：⚡小型股警告色 + 📅 earnings landmine + ⚠ quality red flag + 💰 insider buy + 🏦 institutional accum + PT upside % + ↑ upgrades + ×N.NN multiplier。AAPL 驗證：tier=large_cap MC=$4.1T, earnings 88d 安全, quality_premium (Z=11.6 F=9), PT +13%, multiplier=1.28。

## 🟢 Session Note (v2.10.0 → v2.11.0) — earnings real next-date + EV ratios + theme-detector mapping + sector-analyst FMP overlay

User 起點：「earnings dashboard 上的 🔮 下次財報日是猜的」。修完發現 earnings-analyst 早就 fetch FMP /stable/earnings limit=8 用做 surprise，response 含 1 個未來 row — **資料早在記憶體只是沒用**。改 scan future row + 加 `next_earnings_source` 後，6 個 cached tickers 全 `fmp_confirmed`（NVDA 從過期 +91d 的 2026-04-26 → 正確 2026-05-20）。Frontend 依 source 切 📅↔🔮，向後相容（舊 cache 自動 fallback 🔮）。

順手做完 user 要求的全 skill × FMP catalog 盤點：FMP_強化分析.md 2025-01-30 提的 P0/P1/P2 大部分都 ship 了（financial-scores / owner-earnings / institutional / senate+house / M&A / ESG / news-stock / sec-8k 在 `_shared/fmp_supplementary.py`）。剩 (1) `evToEBITTTM` 漏 — 實測 FMP 沒此欄位（ghost field），改補 `evToFreeCashFlowTTM` + `evToSalesTTM`；(2) theme-detector 仍 finviz primary；(3) sector-analyst 完全沒 FMP overlay。

Theme-detector dry-run 揭露兩個關鍵：finviz 資料 ~50% 損壞（HARD_CAPS 註解已認證 — 看到 ±98% 不可能值）但 finviz vs FMP 只 73/144 (51%) name overlap。手工建 `industry_name_mapping.yaml`（47 rename + 8 collapse + 16 finviz_only + 6 fmp_only = 100% finviz coverage），但**未啟用**（`theme_detector.py:479` 還 import finviz）— 等 user 確認 mapping accuracy 再切 primary。

Sector-analyst 因 TraderMonty CSV uptrend ratio 是 breadth metric（FMP 沒此概念）→ 不能 1:1 替換 → 改加 FMP `sector-pe-snapshot` + `sector-performance-snapshot` 為 overlay（11 sector PE + 1d/5d perf，跨 exchange 平均 + Financial Services→Financial rename 對齊 TraderMonty）。`format_json` 加 `fmp_overlay` field，human format 末尾追加表格。No FMP key 時 graceful no-op。

Files：earnings-analyst/fetch.py + render.py + bridge.py + Dashboard/page-earnings.js + theme-detector/dry_run_compare.py + theme-detector/industry_name_mapping.yaml + sector-analyst/analyze_sector_rotation.py。

下一個自然 follow-up（**留 BACKLOG**）：(1) theme-detector 切 FMP-primary（mapping 已備；先 user review YAML 再切）；(2) sector-analyst overlay 整合進 sector_protocol Phase 4 估值面 rubric；(3) 71 finviz-only 中疑似 FMP 有等價名（Internet Retail 等）二次審視。

## 🟢 Session Note (v2.9.1 → v2.10.0) — invest protocol det-shadow + polarization

CRWV 2026-05-03 同日重跑兩次，final_score 從 −0.055 跳到 −0.481（verdict CANCEL ↔ HOLD 翻面）。診斷出主因：5 個 lane 的獨立 LLM subagent 在 −2/−3 邊界各自抽到不同邊（Fund/Sent 兩 lane 同向 ±1 notch ≈ ±0.40 final_score），架構正常 noise 但 user 體感很怪。V2.10 不改 LLM 主分數（保留 nuance），加三層 sidecar：(1) `signal_polarization`（純看 5 lane 分布，CRWV 兩 run 都判 BIPOLAR — 跨 run 一致 label）；(2) deterministic Valuation shadow（純算 FV/price 閾值表）；(3) deterministic Red Team shadow（6 條 quant kill triggers 數量決定 verdict）。新增 `apply_det_shadow.py` post-processor + Phase 5 Step 1.5 強制跑；schema 新增 `lane_scores` / `det_inputs` / `det_shadow`；bridge + Dashboard pills 帶到 UI（BIPOLAR / RT DISAGREE / VAL DISAGREE 三個 badge）。歷史 CRWV 兩 run 已 backfill 驗證對應預期：Run 1 BIPOLAR + AGREE + DRIFT；Run 2 BIPOLAR + DISAGREE + DISAGREE（完美揭露 LLM 比 quant 寬容了）。

## 🟢 Session Note (v2.8.2 → v2.9.0) — sector protocol 三個新 FMP 訊號

對照 V2.8.2 整理的 FMP MCP 完整清單，發現 sector protocol 還有三個高價值訊號沒納入。**(1) institutional Q-on-Q**：`fetch_smart_money.py` 加 `/stable/institutional-ownership/symbol-positions-summary` 對全 SECTOR_UNIVERSE aggregate，新欄位 `institutional_holders_qoq_delta` / `institutional_ownership_pct_delta` — 真正補上 V1.4 欠下的 form13F 坑（free tier 可用）。**(2) Forward valuation**：`fetch_earnings_pulse.py` 加 `/stable/price-target-consensus` + `batch-quote-short`，新欄位 `analyst_pt_upside_median_pct`。**(3) 多週期 RS**：`fetch_sector_valuation.py` 重用既有 3M chart 算 5d/20d，零新增 API call；既有 `rs_vs_spy_3m` 對 V2.8.x cache **byte-identical**。三個都 soft-fail；rubric 不動，新訊號只進 Phase 4b divergence challenge（規則 5 擴充 + 規則 6/7 新增，皆有量化 threshold 避免 LLM 自由發揮）。原本提案的 `acquisition-of-beneficial-ownership` 實測 mega-cap 太稀疏（最近 180d 全 0），rationale 留在 BACKLOG。

## 🟢 Session Note (v2.7.18 → v2.8.0) — sector protocol DRY refactor + FMP 補位

四份 sector fetch 腳本（valuation/earnings_pulse/smart_money/sector_news）的 `_fmp_get` 抽到 `sector/lib/fmp_client.py`（含 4xx 不重試早退）；docstring 砍到 2-3 行，背景搬 `sector/BACKLOG.md` + `sector/scripts/README.md`。新增 `fetch_general_news.py`（FMP `/stable/news/general-latest`，soft-fail）作 Phase 3 narrative 補位 — `general_news.available=true` 時 Step 5 WebSearch budget 從 ≤2 降到 ≤1，**WebSearch fallback 永遠保留**。`fetch_earnings_pulse.py` 加 `/stable/grades-consensus` 填滿 `analyst_revision_net`（之前永遠 null，現在 11 sectors 都有值）。Refactor 行為對舊 cache byte-identical；驗證器 rc=0。Schema/rubric/render/daily_update.sh/Dashboard 都不動。

## 🟢 Session Note (v1.76.0 → v1.87.0) — FMP 強化分析 12-bump 串接

### 動機
User 提交 `investment/FMP_強化分析.md` 報告，列出 invest_protocol V4.10 全鏈 FMP API 強化機會 (Web-Fetch 替換 / Burry 確定性規則 / Sentiment+News 新訊號 / FMP_SUPPLEMENTARY_BUNDLE 新增)。要求按主要功能切版本 bump 不要擠一筆，autonomous 跑完 + 跑測試 + AAPL benchmark 對比。

### 12 個 bump 結構
| Version | Feature | Files | 風險 |
|---|---|---|---|
| v1.76.0 | earnings-analyst slim_ttm_keymetrics +3 capital efficiency 欄位 (ROIC/ROCE/ROTA) | 1 | 低 |
| v1.77.0 | FMP endpoint probe script (17/18 PASS, 1 skip) | 2 | 無 |
| v1.78.0 | `skills/_shared/fmp_supplementary.py` skeleton + quality_scores + owner_earnings + protocol Phase 1 整合 V4.11 | 3 | 中 |
| v1.79.0 | FMP_SUPP.insider_summary + sentiment skill bundle-first | 2 | 中 |
| v1.80.0 | FMP_SUPP.institutional QoQ (mid-filing-window sanity gate) | 1 | 低 |
| v1.81.0 | theme-detector FMP industry perf cross-check (不替換 finviz) | 1 | 低 |
| v1.82.0 | market-news-analyst FMP news/stock + press-releases (PRIMARY 4-source dedup) + finviz_analyst_actions tzinfo bug fix | 1 | 中 |
| v1.83.0 | News lane sec-filings-search/symbol → 8-K filter | 1 | 低 |
| v1.84.0 | us-stock-analysis bundle-first (EARNINGS_ANALYST_BUNDLE override yfinance) | 1 | 中 |
| v1.85.0 | protocol V4.11 — 4 lane (Burry+Fundamentals+Sentiment+News) FMP_SUPP rules | 1 (protocol) | 中 |
| v1.86.0 | FMP_SUPP.congressional_trades + ma_events | 1 | 低 |
| v1.87.0 | annual analyst-estimates 加入 EARNINGS_ANALYST_BUNDLE + FMP_SUPP.esg | 2 | 低 |

### AAPL benchmark — final integration test 結果
**FMP_SUPP_BUNDLE V1.0** (AAPL_2026-05-02_supp.json, 4082 bytes, 9 FMP calls):
- `quality_scores`: altmanZ=11.64 (safe) / piotroski=9 (strong) → Burry rubric V4.11 規則：safe + strong → +1 score
- `owner_earnings`: $28.86B latest, qoq=-46.7% → Fundamentals -0.5 narrative trigger
- `insider_summary`: 4Q latest_trend=distributing (acq/dis ratio=0.18) → Burry voice 加註，Sentiment lane 已從 bundle 讀
- `institutional`: 64.60% ownership, +3.03% QoQ → accumulation_signal=accumulating → Sentiment +1
- `congressional_trades`: 30 trades 180d (15 buy / 15 sell) → neutral
- `ma_events`: 0（mega cap 通常 0，schema 正確）
- `esg`: total 56.79, rating B (2025)

**us-stock-analysis bundle-first**:
- bundle path P/E 33.89 (FMP TTM canonical) vs no-bundle P/E 35.74 (yfinance) — 5.2% drift
- EV/EBITDA 25.59 (bundle) vs 24.98 (yfinance) — 2.4% drift
- next_earnings 2026-07-31 from bundle vs unknown from yfinance

**News 4-source dedup**:
- FMP news/stock=30, press_releases=2, finviz=100, yfinance=10, finnhub=25
- 5-source dedup → 149 unique headlines, primary_source=fmp_news_stock
- 8-K filings: 2 件 (30d window)

**theme-detector FMP cross-check**:
- 128 industries × 5 trading days, top 5d perf: Manufacturing-Metal Fabrication +13.82%, Software-Services +11.58%, Personal Products +10.10%
- 不替換 finviz，scorer 後續可選用 cross-validate

### 物理隔離契約 (V4.11)
FMP_SUPP_BUNDLE 為 FMP-only。fmp_supplementary.py 模組**不得**import dual_fetch / FinnhubClient。Bundle 經 Phase 1 PM 路由到 4 個 lane（Fundamentals / Sentiment / News / Burry），Technical lane 不收（OHLCV-only）。Sentiment skill bundle-first + skill self-fetch fallback：bundle 命中時 0 額外 FMP call，bundle 缺時 skill 獨立可用。

### 注意事項與決策記錄
- 決策 B：Burry 規則只調 score (±1/±2)、不強制 verdict (LLM 收尾權保留)
- 決策 C：theme-detector option-3，FMP 為新欄位、不替換 finviz
- 決策 D：news 5-source dedup（FMP primary + finviz/yf/finnhub/press fallback）
- 決策 E：sentiment bundle-first + skill fallback
- 決策 F：us-stock-analysis bundle-first + yfinance fallback (--no-bundle 旗標保留)
- 決策 G：沿用檔名 `investment_protocol_v4_8.md`，內文 V4.11 章節
- 決策 H：獨立 cache `skills/_shared/fmp_supp_cache/`

### Endpoint 修正記錄
- ❌ `/stable/news-stock` → ✅ `/stable/news/stock`
- ❌ `/stable/news-press-release` → ✅ `/stable/news/press-releases`
- ❌ `/stable/sec-filings-8k` (ignores symbol filter) → ✅ `/stable/sec-filings-search/symbol` + 客端 filter formType=8-K
- ❌ `/stable/intraday-1hour` → ✅ `/stable/historical-chart/1hour`
- `historical-industry-performance` 200 但 count=0；改用 industry-performance-snapshot rolling sum

### 既有 bug fix
- `_finviz_analyst_actions:97-104` `replace(tzinfo=)` 對 numpy datetime64 失敗 → 加 `isinstance(d, datetime)` gate (v1.82.0)
- `_derive_from_bundle` next_earnings_est schema：bundle 給 string `"YYYY-MM-DD"` 而不是 dict → 加 isinstance check (v1.84.0)

### 改動清單（v1.76.0 → v1.87.0 累計）
**新檔**：
- `skills/_shared/fmp_supplementary.py` (~340 行 V1.0 schema + 7 fetch helpers)
- `investment/scripts/fmp_endpoint_probe.py` (~110 行)
- `investment/fmp_probe_2026-05-02.json` (probe 結果)
- `skills/theme-detector/scripts/fmp_industry_perf_client.py` (~150 行)

**改動檔**：
- `skills/earnings-analyst/scripts/fetch.py` (slim +3 fields, +annual_estimates)
- `skills/market-sentiment-analyzer/scripts/sentiment.py` (bundle-first insider)
- `skills/market-news-analyst/scripts/fetch.py` (FMP news/stock + press + 8-K + tzinfo fix)
- `skills/us-stock-analysis/scripts/analyze.py` (bundle-first override)
- `investment/investment_protocol_v4_8.md` (V4.11 — Phase 1 + 4 lane FMP_SUPP 規則)

### 驗證
- 6 個 integration test 全綠：FMP_SUPP_BUNDLE / us-stock-analysis / news / sentiment / earnings / theme-detector
- `validate_session_export.py` 對既有 AAPL session export ✓ V4.8 schema compliant
- 無 protocol contract 破壞（dual-fetch isolation 保留）

---

## 🟢 Session Note (v1.75.0) — 決策中心 (decisions.html) Invest Cmdbar + 視覺布局重組

### 動機
User 比對 earnings.html 的 cmdbar 體驗(terminal-style ticker input + 快速跑 protocol),希望 decisions.html (決策中心) 也加同款,但 trigger **invest protocol** (`分析 [TICKER]` V4.10 委員會深度分析) — 與決策中心語意一致。順便做視覺布局重組:summary stats / 卡片 hover state 微調。

### 實作重點
- **Cmdbar HTML** (decisions.html `<header>` 下方): prompt `›` + input + RISK hint + 分析 btn + recent chips,套既有 `.ea-cmdbar*` class
- **Risk tolerance**: 用全局 `UI.riskTolerance` (utils.js:474 getter,localStorage `dash_risk_tolerance`,sidebar `#risk-chip` 可切換),cmdbar 只顯示「RISK: MEDIUM」hint,不重複暴露切換 UI(避免 multi-source-of-truth)
- **runInvest 邏輯**: POST `/api/protocol-queue` flat payload `{name:'invest', ticker, risk_tolerance}` (與 script.js:1094 / page-radar.js:843 一致),202 → recent chip + toast + clear input;409 → duplicate toast
- **Recent chips**: localStorage `dc_recent_invest_tickers` max 5,點擊重跑同一 ticker
- **css 提升**: `.ea-cmdbar*` 從 earnings.html L64-119 inline 拷貝到 `Dashboard/style.css` 共用區(+90 行),earnings inline 保留作 graceful fallback;decisions 直接用 shared
- **視覺 polish**: `.dc-summary-tile` hover lift + `.dc-summary-num` (32px JetBrains Mono),conf/RR 兩格加 blue/violet 4px left-border;`.dc-card-hover` 卡片 emerald border + lift

### 既有 utility 重用
- `UI.riskTolerance` (utils.js:474), `UI.escapeHTML`, `UI.boot('decisions', ...)`, `UI.showToast`
- `.ea-cmdbar*` / `.ea-recent-chip` (earnings.html → style.css 提升共用)
- POST `/api/protocol-queue` invest payload pattern (analyze-queue.js:60 / script.js:1094 / page-radar.js:843 既有)

### 注意:`refreshTicker` 已在跑 invest
卡片右上「refresh-cw」按鈕 (page-decisions.js:1108 `refreshTicker`) 既有就走 `AnalyzeQueue.enqueue` invest,不是 FLASH。Plan 探索期 explorer 誤判;**本次未動該函式**。卡片底部的 FLASH 按鈕走 `goFlash` (新聞快訊),那是刻意的二次選項,保留不動。

### 改動清單
- `Dashboard/decisions.html` (~30 行 add/edit) — cmdbar HTML + summary tile classes
- `Dashboard/page-decisions.js` (~110 行 add) — dcRunInvest + recent chips + wireCmdbar + applyTranslations 擴充 + buildCard 加 dc-card-hover class
- `Dashboard/style.css` (~90 行 add) — `.ea-cmdbar*` 共用 + `.dc-summary-tile` / `.dc-summary-num` / `.dc-card-hover`
- `Dashboard/i18n.js` (~30 行 add) — `decisions.cmdbar_*` zh/en 雙語 7 keys
- `Dashboard/utils.js`, `VERSION`, `CHANGELOG.md`, `SESSION_NOTES.md`, `TODO.md` — version bump 1.74.0 → 1.75.0

### 不在範圍
- 持倉 modal / 平倉 modal / 持倉 table 結構
- bridge.py extract_audit_history 邏輯
- 卡片內部 layout (target/stop/risk-reward)
- `?ticker=X` deep-link 自動鑽取 (known UX debt)
- 完全移除 FLASH news 入口 (仍可從卡片底部 goFlash 觸發 / news.html)

---

## 🟢 Session Note (v1.74.0) — FMP company API Bucket A (shared profile cache + peer bundle)

### 動機
分析計畫 `/Users/kavi/.claude/plans/3-fluffy-moonbeam.md`:9 個 FMP `mcp__fmp__company` 方法中只 2 個高 ROI(stock_peers + profile)。Bucket A1+A2+A3 一次落地。

### 落地三件事
1. **共用模組** `skills/_shared/company_context.py`(NEW ~250 行)+ `__init__.py` + `cache/` dir
   - 常數:`SECTOR_UNIVERSE` / `TICKER_TO_SECTOR` / `SECTOR_TOP_5`(sector scripts 共用唯一真相源)
   - 函式:`get_profile / get_peers / get_market_cap_history / get_employee_history / get_profiles_bulk`(24h TTL,402 graceful)
2. **sector 3 script 去重** ~75 行:`fetch_earnings_pulse.py` / `fetch_smart_money.py` / `fetch_sector_news.py` 改 `from skills._shared.company_context import ...`
3. **earnings-analyst fetch.py** profile 走共用 cache(同 ticker 24h 內 0 重複 FMP call)
4. **investment_protocol_v4_8.md** Phase 1 末段新增 PEER_BUNDLE step;Fundamentals + Burry lane rubric 加 relative valuation 規則(P/E 差 > 30% → ±1,> 50% → ±2)

### 端對端驗證
- `python3 sector/scripts/fetch_earnings_pulse.py --date 2026-05-01` rc=0,輸出 `92 mega-cap reports in 30d`(數字與 v1.73.6 一致,行為 zero-regression)
- `python3 skills/_shared/company_context.py AAPL --peers` → AAPL profile.sector=Technology,marketCap=$4.2T,peers=['GOOGL','META','MSFT','NVDA','NXT','RIME','SONY','TBCH','TSM']
- `python3 skills/earnings-analyst/scripts/fetch.py AAPL`(no --force)→ cache hit,新 import path 通
- 三個 sector script importlib smoke test 全 OK

### 風險與後續
- **下次跑 `分析 [TICKER]` 才會真正觸發 PEER_BUNDLE 路徑**:目前只完成 spec + 模組,實際 Phase 2 lane subagent 是否正確消費 PEER_BUNDLE 需 user 跑一次 `分析 NVDA` 等高 P/E 票觀察 lane 輸出
- Bucket B(theme-detector dict 拋棄 + Burry historical_employee_count 訊號)未做,等 Bucket A 用一陣子再評
- shared cache `skills/_shared/cache/` 已 .gitkeep 佔位,內容由 runtime 生成不入版控(後續 .gitignore 視需要加)

---

## 🟢 Session Note (v1.73.7) — sector Phase 3 Step 1/2/3 補 explicit bash block

### 問題
scan log `sector_20260501_213508.log` 顯示 sector Phase 3 agent 對 Step 2 (`get_economic_calendar.py`) / Step 3 (`fetch_earnings_fmp.py`) 連續 retry 錯誤 flag：
- `--json --days 7` ❌ unrecognized / `Invalid start date format`
- `--from --to --format json` ✅ (Step 2 econ calendar argparse)
- positional `2026-05-01 2026-05-08` ✅ (Step 3 earnings)

每次 retry 浪費 5-15s + tokens。

### 根因
`sector/phase_1-2-3.md` Phase 3 執行順序 block 只列 step 名沒 bash 指令。Step 3b/3c/3d 有 explicit `python3 ... --date {SCAN_DATE}` 範例所以 agent 不 guess; Step 1/2/3 漏掉。

### Fix
`sector/phase_1-2-3.md` 第 71 行後新增三個 sub-section：
- Step 1 — Market Sentiment (`sentiment.py --json` 已 work, 補完整性)
- Step 2 — Economic Calendar (argparse: `--from --to --format json`，明示**不**支援 `--json`/`--days`)
- Step 3 — Earnings Calendar (positional: `START_DATE END_DATE [API_KEY]`，明示**不**支援 flag 形式)

每段含失敗策略 (soft fail / 不 abort protocol)。

---

## 🟢 Session Note (v1.73.0) — 個股財報 Infographic 風格頁面（取代「看報告」markdown modal）

### 動機
User 看到 AAPL FY26 Q2 財報視覺化 infographic（公司 hero + 4 主指標 actual vs estimate ✓✗ + 6 segment grid + 資本回報 + CEO 引述 + Key Highlights + 重點總結），希望 `財報 [TICKER]` 個股報告改這個樣式。原 markdown 報告退為新頁面內 `<details>` collapse 區塊作 reference。

### 端對端驗證（AAPL Q2 FY26）
- 跑 `fetch.py --force` → 17 endpoints 全成功（含 transcript Y2026Q2 offset=0, 48,024 chars）
- `analyze.py` → composite=72 verdict=SOLID flags=clean
- `validate.py` rc=0
- **Step 4 LLM narrate phase**：Claude in-conversation 讀 cache + transcript content，Write `AAPL_2026-03-28.infographic.json`（含 6 segments + 6 highlights + 4 summary + Tim Cook quote 講 Greater China +28%）
- `render.py` → `reports/2026-05-01_AAPL_earnings.md`（既有 markdown 不變）
- `validate_infographic.py` rc=0：「✓ V1.0 compliant — AAPL FY26 Q2 ✓ transcript segs=6 highlights=6 summary=4」
- `bridge.py --no-fetch` → `data.earnings_analyses[ticker=AAPL].has_infographic=true`，其他 3 ticker (GOOGL/MSFT/NVDA) 為 false 直到重跑

### 技術重點
- **資料層雙 cache 並存**：原 `<TICKER>_<DATE>.json`（V1.0 quantitative）不動；新增 `<TICKER>_<DATE>.infographic.json`（V1.0 narrative，schema_kind="infographic"）；bridge.py 與 `/api/earnings-cache/*` 已加 glob 過濾排除 `.infographic.json` sibling
- **Transcript fiscal-Q resolver 4-tier**：用 cache 內 fiscalYear+period (FMP fiscal labels) → calendar Q → walk back Q-1 with year rollover；最差 4 calls，AAPL 0 offset 命中
- **季度分部來源**：FMP `period=quarter` 全 402 付費，改由 LLM 從 transcript CFO 段抽（infographic 上的 569.9/309.8 億等本來就是這樣來的）
- **Page 切換**：earnings card 「看報告」按鈕改為「📊 Infographic」連到 `earnings-detail.html?ticker=X`；markdown 退為頁內 `<details>` lazy load

### 改動清單
- `skills/earnings-analyst/scripts/fetch.py` — +5 endpoints + 4 slim helpers + transcript resolver (~110 lines)
- `skills/earnings-analyst/scripts/validate_infographic.py` — NEW (~80 lines)
- `skills/earnings-analyst/SKILL.md` — 4 → 6 steps doc
- `skills/earnings-analyst/schema.md` — 追加 V1.73 cache 新欄位 + Infographic schema 完整文件
- `dashboard_server.py` — `/api/earnings-infographic/<T>` + 6-step PROTOCOL_PROMPTS + glob filter fix
- `bridge.py` — `has_infographic` 欄位 + glob filter
- `Dashboard/earnings-detail.html` — NEW (~150 行)
- `Dashboard/page-earnings-detail.js` — NEW (~340 行)
- `Dashboard/page-earnings.js` — view → infographic action
- `Dashboard/style.css` — `.ed-*` namespace ~180 行
- `Dashboard/i18n.js` — `earnings_detail.*` 29 keys × zh/en

### 不在範圍
- 季度 segmentation 付費 endpoint
- Backfill 既有 GOOGL/MSFT/NVDA 必須手動 `財報 X` 觸發 LLM narrate phase
- 多季比較頁（只渲最新一季）

---

## 🟢 Session Note (v1.72.1) — Journal Stats 修復 + 今日未跑提示 Banner

### 問題
- `screen.py --journal` 只寫入 `journal.jsonl`，但從未自動呼叫 `journal.py stats`
- 結果 `stats.json` 不存在 → `bridge.py` 回傳 `journal.stats=null` → 頁面 journal 區塊空白
- 16,043 entries 已存在但頁面看不到任何資料

### 修改

**`dashboard_server.py`** — `_worker()` 在 screen.py 成功且 `--journal` flag 為 true 時，自動呼叫 `journal.py stats`（timeout=120s），phase label 更新為「computing journal stats…」

**`bridge.py`** — binary seek 讀 `journal.jsonl` 最後 4KB，提取 `last_snap_date`，加入 `journal` dict 供前端判斷今日是否已跑

**`Dashboard/momentum.html`** — 新增 `#journal-stale-banner`（amber 色）在 journal-section 頂部

**`Dashboard/page-momentum.js`** — 新增 `renderJournalStaleBanner()` + `runJournalNow()`；比對 `last_snap_date` vs 今天，若過期顯示 banner 及「立即執行」按鈕

**`Dashboard/style.css`** — sidebar brand text 移除 `overflow:hidden` / `min-width:0`，加 `flex-shrink:0`，修正 INTELCOMMAND D 被截斷問題

### 動機
User 看 index.html 的 48 小時二元風險條幅下方四個 ⚠ label —「空頭信號啟動 / 廣度跌破 200MA / 歷史低百分位 / 弱化區間」。其中後三項都是同一個廣度指標的不同切面（`ma_crossover.gap` / `historical_percentile` / `composite.zone`），會綁在一起亮（今天 4 個全觸發、breadth_score=33.1）。原本扁平 flex pill 用 regex 區分紅/黃，視覺權重均等，看不出哪個是真正獨立信號。

### 改動

**bridge.py** — `extract_breadth_from_analyzer` 並列輸出新 schema `warning_flags_v2`（object[]，含 `key/severity/metric_value`），舊 `warning_flags: string[]` 保留以維持 `page-sector.js` 相容。

**Dashboard/style.css** — 新增 `.risk-overview` / `.risk-flag-card`（3 種 severity variants：critical 🔴 / warning 🟠 / caution 🟡）/ `.modal-scroll-shadow`（純 CSS sticky pseudo-element fade）/ `.cta-launch`（Quick Launch button glow）/ `.ticker-input-wrap`（input search-icon prefix）/ `.focus-ticker-promoted` ::after 漸層。

**Dashboard/index.html** — Layer 2a (Binary Alert) + Layer 2b (Warning Flags) 包進共同父層 `<section id="risk-overview">` 加標題 "風險總覽" + count badge。`#focus-ticker-card` 從 Momentum 卡內抽出，提權為 Layer 2 之後的全寬 attention strip。Quick Launch input 加 search icon prefix；button 套 `.cta-launch`。Modal `#preflight-body` + `#report-content` 加 `.modal-scroll-shadow`。

**Dashboard/script.js**:
- 重寫 `renderWarningFlagsIndex` — 用 severity tier 渲染 `.risk-flag-card`，dot + 左邊框 + name + metric chip；自動排序 critical→warning→caution；schema fallback 兼容舊 string[]
- 加 `updateRiskOverviewVisibility()` 協調 #risk-overview 父層顯隱（兩個 child 都空才隱藏）
- 擴充 `#pill-tooltip` engine — `data-tip-key="warning_flag"` 走專屬路徑，從 `i18n.warnings.tooltips.<flag_key>` 組 severity-tinted title + definition + metric chip + remediation hint
- Hero `renderThreeSignalMini` 4 欄各加 10-cell `.score-battery`（複用 Momentum teaser 同款）
- 五區 (`renderBinaryAlertIndex` / `renderHotSectorsTeaser` / `renderNewsVerdictsTeaser` / `renderMomentumTeaser` / `renderFocusTicker`) 全面套 `UI.escapeHTML()`，封死 innerHTML XSS [ARCH-14]
- focus-ticker enqueue 用白名單 `[A-Za-z0-9.\-]` 過濾 ticker，防止 inline `onclick` 注入

**Dashboard/i18n.js** — 追加 `warnings.severity` (critical/warning/caution) + `warnings.risk_overview_title` + `warnings.tooltips.<flag_key>` (definition + hint) zh/en 雙語；新增 `Critical_Zone`、`Early_Warning_Divergence` flag 名稱翻譯。

**Dashboard/page-sector.js** — `warning_flags` consumer 加 schema fallback：兼容 `string[]` 與 `{ key, severity, metric_value }[]` 兩種輸入。

### 驗證
- `python3 bridge.py --no-fetch` → data.json 正確產出 `warning_flags_v2`（4 項：critical 1 / warning 2 / caution 1）
- `node` 語法檢查 script.js / page-sector.js / utils.js / i18n.js 全部通過
- 視覺驗證（user 端）：開 index.html 應看到 1 紅 + 2 橘 + 1 黃 順序排列；hover 各 card 顯示 severity-tinted tooltip 含 `gap −2.83%` / `pct 25%` / `score 33.1` / `risk 25` 等具體數值與 remediation hint。

### 不在範圍
- Sidebar nav 結構不變
- market-breadth-analyzer skill 內部不動（只動 bridge.py glue layer）
- decisions.html `?ticker=XXX` deep-link 仍是 known UX debt
- 其他 page 視覺改動（除 page-sector.js 防禦性 fallback）

---

## 🟢 Session Note (v1.71.4) — Earnings sparkline 黑底破圖修

User 截圖顯示 NVDA earnings card「毛利率 8Q -3.4 PTS」sparkline 呈現整片黑色三角形（應該是淡紅 fill + 紅線）。

### 根因
`Dashboard/earnings.html:332` CSS：
```css
.ea-sparkline path { fill: none; stroke-width: 1.6; }
```
Selector 只 catch `<path>`，但 `page-earnings.js:484` 渲染的是 `<polyline>` — CSS 沒套到 → polyline 用 SVG 預設 `fill: black` → 黑色三角形蓋掉下面 `.ea-sparkline-fill` polygon (opacity 0.18 淡紅) 的視覺。

### 改動
CSS selector 加 `polyline`：
```css
.ea-sparkline path,
.ea-sparkline polyline { fill: none; stroke-width: 1.6; }
```
一行加完，整個 sparkline 立即恢復「淡色背景區塊 + 趨勢線」應有樣貌。

### 驗證
Hard reload `earnings.html`，sparkline 應顯示淡紅 fill (trend down) / 淡綠 (up) / 灰 (flat) + 對應顏色的折線。

---

## 🟢 Session Note (v1.71.3) — Preflight popup 對齊 sidebar：sector/news 也讀內部 timestamp

### 動機
v1.71.2 修了 sector protocol 自己的 cache rule（看 generated_at）+ runPreflightQueue 切頁不斷。但 user 觀察到新矛盾：「盤前狀態檢查 popup 顯示『產業情報 ✓ 3h 前』，但 sidebar 橘燈說『產業掃描 29h 前』— 同一個檔到底新還舊？」

### 根因
Popup 跟 sidebar 讀同一個 `sector_intel.json` 但**不同欄位**：
- **Popup** (`dashboard_server.py:735` `preflight_check()`)：用 `os.path.getmtime()` → 20:34（news Phase 4 patch top_catalysts 時 touch 的）
- **Sidebar** (`Dashboard/script.js:583`)：用內部 `generated_at` → `2026-04-29 18:21`

這是 v1.71.2 漏掉的對稱修：sector protocol 自己看 generated_at 了，但 dashboard 的監控層還在看 mtime。

### 改動
**`dashboard_server.py` 加 `_content_timestamp_for(key, path)` helper**
- 對 `key in ('sector', 'news')`：讀檔內部 `generated_at` (sector) 或 `timestamp` (news digest)，parse 失敗 fallback 到 mtime
- 其他 key (breadth/ftd/market_top/rss)：仍用 mtime（這些是 yfinance/RSS script 寫的 fresh 檔，mtime 跟內容時間一致，無 false-FRESH 風險）
- 支援多種 timestamp 格式：ISO with/without tz、`YYYY-MM-DD HH:MM:SS`、`YYYY-MM-DD HH:MM`、`YYYY-MM-DD`

`preflight_check()` 把原本 `age_sec = now - mtime` 改成 `age_sec = now - _content_timestamp_for(key, path)`。

### 驗證
跑 `python3 -c "import dashboard_server; ds.preflight_check()"`：
```
sector  產業情報   STALE  age=29.2h   ← 之前是 FRESH 3h
news    新聞 DIGEST STALE age=11.1h   ← 之前是 FRESH 32min（patch 了 top_catalysts 那刻）
```
跟 sidebar 橘燈所見完全一致。

### 不在範圍
- 不改前端 `script.js:583` 的 source timestamps array（既已正確讀 generated_at）
- 不改其他 4 項 free 的 mtime 邏輯（沒有 cross-protocol patch 風險）
- 不解決「news Phase 4 為什麼要 patch sector_intel.json」這個更深的架構問題（屬下一輪 refactor）


## 🟢 Session Note (v1.71.2) — 「更新全部過期」三 bug 串連修

### 動機
User 觀察「點盤前檢查 → 更新全部過期 → news 跑了但 sector 沒跑，sidebar sync 燈一直橘」。Forensic 三個 bug 疊加：

1. **Frontend for-loop 切頁就斷**（`script.js:runPreflightQueue`）：原本 `POST /api/run-protocol` + `await waitForProtocolDone()`，news 跑 17min 期間 user 切頁/關 tab → JS Promise 死 → sector POST 從未發出。
2. **Sector prompt 缺「非互動模式」**（`dashboard_server.py:88` 原本只是裸字串「產業掃描」）：手動跑 sector 時 Claude 會主動停下「準備好進入 Phase X 嗎？」等 user reply，浪費 ~$1 / 9k tokens 只讀檔思考然後卡住。
3. **Sector cache freshness 用 mtime 誤判**（`sector_protocol_main.md` GLOBAL RULES #2）：news protocol Phase 4 patch `top_catalysts` 進 `sector_intel.json` 會 touch mtime 但不動 `generated_at` → sector cache rule 看 mtime < 3h 誤判 FRESH → 跳過 Phase 0-1 → 但內部 `generated_at` 還是昨天。

證據：sector_20260430_210533.log 開頭 Claude 自己點出矛盾「mtime 32min 前 FRESH，但 generated_at 2026-04-29 18:21」然後就停下問了。

### 改動

**1. `Dashboard/script.js:972-1017` `runPreflightQueue` 改 server-side queue**
- 從「for loop POST `/api/run-protocol` + await waitForProtocolDone」改成「全部一口氣 POST `/api/protocol-queue`，server FIFO 自己序列跑」
- Frontend 只負責提交，不需要等。切頁/關 tab/重整都不影響 — server 持續跑
- 一次 toast 報「已排入 N 個 protocol：news → sector，server 序列執行」
- 沿用既有 `pollLaunchStatus` banner 顯示進度

**2. `dashboard_server.py:88` sector prompt 加非互動模式 + cache 衝突自動處理**
```
非互動模式：依 sector_protocol_main.md GLOBAL RULES 直接執行 Phase 0→5 完整流程，
不要輸出「準備好進入 Phase X 嗎？」「請確認」這類停頓等候，一個 turn 完整收尾。
Cache 衝突自動處理：若 sector_intel.json 的 mtime 看起來新但內部 `generated_at` 距今 ≥ 3 小時
（通常是 news protocol Phase 4 patch top_catalysts 造成的 mtime touch），
視為 STALE 必須重跑 Phase 0–1，不要當成 FRESH 跳過。
```

**3. `sector/sector_protocol_main.md` GLOBAL RULES #2 重寫 cache freshness rule**
- 從「FRESH = mtime < 3h」改成「FRESH = `generated_at` 距今 < 3h」
- 明確說「以內部 `generated_at` 為準，不看 mtime」
- 加註 false-FRESH 來源（news Phase 4 patch top_catalysts）
- `generated_at` parse 失敗 → 視為 STALE

### 驗證
- `node -c script.js` + `python3 -c "import dashboard_server"` 都過
- `dashboard_server.PROTOCOL_PROMPTS["sector"]` 含「非互動模式」+「generated_at」字串
- `sector_protocol_main.md` 含 3 處 `generated_at` references（GLOBAL RULES + 兩處說明）

### 注意事項
- **要重啟 `dashboard_server.py`** prompt 改動才生效
- 既有 `runPreflightQueue` 同事流程不再需要 `waitForProtocolDone` — 但函數本身留著（其他 caller 可能還用，未動）
- News Phase 4 patch sector_intel.json 的設計沒動（屬另一個架構議題：news/sector cache 責任邊界）— 但 sector cache rule 改用 generated_at 已能避開誤判


## 🟢 Session Note (v1.71.1) — earnings 頁 UX redesign + markdown viewer 修復

### 動機
v1.71.0 落地的 earnings 頁是基本 grid card,user 反映:
1. **看報告按鈕變成下載** — `window.open('/${path}','_blank')` 開 `.md` 被 SimpleHTTPRequestHandler 預設 MIME 當下載
2. **頁面太 generic** — 缺視覺層次 / 節奏 / 特色

User 要求用 frontend-design skill 重做 UX。本 session 在 **不改資料邏輯** 前提下,重構 layout + 美學語彙 + 修 markdown render。

### 改動

**1. Markdown viewer 接線(原本卡的就是這個)**
- `Dashboard/earnings.html` 加 `<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js">` + 完整 `report-modal` markup(複用 `decisions.html:179-189` 結構)
- `Dashboard/page-earnings.js` 加 `wireReportModal()`(close button + click backdrop + ESC 關閉);看報告按鈕從 `window.open()` 改 `window.UI.viewReport(path)`
- **零 server / MIME 改動** — 純複用 `utils.js:322-344` 既有 `UI.viewReport()`(fetch md → marked.parse → 套 prose theme dark/light 自動切)

**2. UX redesign — Editorial × Financial Terminal 美學**
- `Dashboard/earnings.html` 重寫(186 → 326 行,內含 ~290 行 inline `<style>` block .ea-* 命名)
- `Dashboard/page-earnings.js` 重寫(248 → 415 行,模組化成 7 個 render 函式 + filter/animation 邏輯)
- 美學決策:
  - **Typography**: JetBrains Mono 加重(score 用 64px 900 weight, ticker 24px 800),Inter 維持 body 字
  - **配色**:不引新色,強化 5 verdict 漸層 stripe + glow(STRONG 帶 inner-glow shadow)
  - **背景**:subtle dotted grid pattern(18px / 6% opacity),邊緣 fade
  - **動效**:cards stagger reveal(60ms 間隔),hero stats 計數 0→真值動畫(480ms),score 數字用 IntersectionObserver 進入視窗才 count up(避免初始 jank)

**3. 新元素**
- **Hero Stat Strip**(4 tile):Total / Avg score / STRONG count / Risk Watch count,各帶 verdict-color accent strip,進場有計數動畫
- **Command Bar**:`›` prompt 字符 + JetBrains Mono 大字 input + recent ticker chips(localStorage 記 5 個);placeholder 每 3.5s 輪播 NVDA/AAPL/MSFT/AVGO/META
- **Filter Chip Bar** 取代 3 個 select:
  - Sort:segmented control(Score↓/↑/Recent/A→Z)
  - Verdict:5 個 toggle chip 各帶 verdict 色,active 反白
  - Flags:`✅ Clean` / `⚠️ Has Flags` 互斥 chip
  - Reset 按鈕 + 即時 match count(`12 / 24` 風格)
- **Asymmetric Card** layout(左 145px score column + 右 data column):
  - 左:64px JetBrains Mono 900 score 數字、verdict pill、4px 漸層 stripe(STRONG/WEAK 加 glow)
  - 右上:ticker(24px)+ company truncate + sector/industry/date pills
  - 右中:**8Q gross margin sparkline**(SVG inline polyline + fill + delta label),trend up/down 自動染色
  - 右下:4 個 component horizontal mini bar(Quality/Growth/Valuation/Analyst,各 max bar 寬一致),verdict-tinted gradient fill
  - 底部:freshness dot(綠<14d / 黃<45d / 紅≥45d)+ 看報告 / 重跑 buttons
- **Empty State**:大 icon + title + 3 個 sample ticker quick-start chip
- **Filter persistence**:sort / verdicts / flags 寫 localStorage,reload 還原

**4. bridge.py 擴 schema(支援 sparkline)**
- `extract_earnings_analyses()` 加 `margins_8q` 欄位(每 ticker 8 個 {date, gross} 點)— 16 floats × N tickers 額外體積可忽略
- 既有結構 100% 向下相容(只是多一個欄位)

**5. utils.js**
-  const VERSION = 'V3.13.0';

### 不影響範圍
- `dashboard_server.py` 完全不動(no MIME 設定,no 新 endpoint)
- `utils.js`:`UI.viewReport()` 不改,直接重用
- 其他頁面零變動
- earnings-analyst skill 本身(scripts/, schema)不動

### 驗證
- `bridge.py` rc=0,`data.earnings_analyses[]` 含 margins_8q(NVDA/MSFT/AAPL 各 8 點)
- `node -c page-earnings.js` syntax OK
- 手動瀏覽 earnings.html:
  - hero stats 計數動畫 ✓
  - command bar `>` prefix + placeholder 輪播 ✓
  - filter chips 點擊切 verdict / flags 即時更新 + match count 同步 ✓
  - reset 還原 + localStorage 持久化 ✓
  - card stagger reveal + sparkline + component bars + verdict glow ✓
  - 點 📄 看報告 → modal 開 markdown(prose theme dark/light 跟主題切換)+ ESC/close 關閉 ✓
  - empty state(濾掉所有結果)→ 友善 quick-start ✓
  - dark / light 切換無破口 ✓

### 重啟需求
- **必須重啟 dashboard_server** 因為 PROTOCOL_PROMPTS earnings 條目在 v1.71.0 加,還沒 reload(若還沒重啟過)
- 已自動跑 `bridge.py`,data.json 含新 schema,重新整理頁面即看到 sparkline


## 🟢 Session Note (v1.71.0) — earnings-analyst 全面整合(calendar UI + 獨立頁 + 投資協議 Tier 2)

### 動機
v1.70.0 已落地 `skills/earnings-analyst` 但屬孤立 skill(只能 CLI 跑)。User 要求:(1) calendar 點財報事件 → 一鍵觸發;(2) 想清楚怎麼跟其他 protocol 整合。本 session 補完整合三層 — UI 觸發 + 獨立 Dashboard 頁 + investment_protocol Phase 2 機會式讀取。

### 改動

**1. Backend(`dashboard_server.py`)**
- `PROTOCOL_PROMPTS["earnings"]` 新增,prompt 強制 fetch+analyze+validate+render 4 步驟非互動執行
- `PROTOCOL_LOG_DIRS["earnings"]` = `skills/earnings-analyst/cache`
- `enqueue_protocol()` 加 earnings ticker dedup(running/queued 同 ticker 拒絕)
- `_label_for()` 加 `📊 Earnings <ticker>` queue label
- 新 GET 端點 `/api/earnings-cache/:ticker` — 回 cache 狀態(cached / composite_score / verdict / quality_flags / report_path / cache_age_days)

**2. Calendar UI(`Dashboard/page-calendar.js` + `style.css`)**
- 載 `data.earnings_analyses[]` 進 `earningsCacheMap` 供 inline 查詢
- `renderUpcomingCard()`:earnings event 自動加 action row
  - **已 cache**:`<verdict 顏色 chip> <📄 看報告 button> <🔄 重新分析 button>`
  - **無 cache**:`<📊 跑財報分析 button>`
- 點按 → `window.runEarningsAnalysis(ticker)` POST `/api/protocol-queue {name:"earnings",ticker}`
- 加 6 個 CSS class:`cal-earnings-action-row` / `cal-earnings-btn` / `cal-earnings-btn-run` / `cal-earnings-btn-refresh` / `cal-earnings-cached-badge`

**3. Bridge 索引(`bridge.py`)**
- 新 `extract_earnings_analyses()`:scan `skills/earnings-analyst/cache/*.json`,過濾 90d TTL + composite_score 已寫入,emit thin summary list(ticker / verdict / score / flags / score_components / report_path / company_name / sector / industry / price)
- `data["earnings_analyses"]` 寫入 data.json(daily bridge.py 跑時自動 refresh)

**4. Dashboard 獨立頁(`Dashboard/earnings.html` + `page-earnings.js`)**
- nav 加新 entry `📊 財報分析`(`utils.js` NAV_ITEMS;`i18n.js` zh/en 兩處 nav 字典)
- 主頁 layout:trigger 輸入框(任意 ticker)+ 排序/filter 列(score/date/ticker × verdict × flags clean)+ 卡片格(每個 cached ticker 一張卡)
- 卡片內容:ticker / company / sector / industry / score / verdict / quality_flags / 4 個 score components / last+next earnings date / 看報告/重新分析/cache age 工具列

**5. Investment Protocol Phase 2 整合(`investment/investment_protocol_v4_8.md`)**
- Phase 1 加新 sub-section「Phase 1 資料層(V1.71)— Earnings-Analyst Cache 機會式讀取」:PM 檢查 cache 是否存在 + 90d 新鮮度 → 抽 thin EARNINGS_ANALYST_BUNDLE(margins_8q / yoy_growth / balance_health / cash_flow_quality / valuation / quality_flags)
- Phase 2 共通 prompt 模板加 `EARNINGS-ANALYST BUNDLE` 段(僅 Fundamentals lane,其他 3 lane 不含)
- Fundamentals subagent rubric 加「EARNINGS_ANALYST_BUNDLE 使用規則」:
  - 引用 8Q margin trend 等深層證據
  - quality_flags 觸發 ±1 分強訊號(accruals/negative_fcf/capex_outpaces 至少 -1;乾淨 + composite ≥ 80 至少 +1)
  - DCF intrinsic 與 dual-fetch peRatio 互相校驗
  - **絕對禁止**直接 mirror composite_score 為 lane score

**整合資料流**:
```
calendar 點按 / earnings 頁點按 → POST /api/protocol-queue
   ↓
queue worker 跑 PROTOCOL_PROMPTS["earnings"] = "財報 {ticker}"
   ↓
Claude Code → fetch+analyze+validate+render 4 步驟
   ↓
skills/earnings-analyst/cache/<T>_<DATE>.json + reports/<DATE>_<T>_earnings.md
   ↓ (next bridge.py run)
data.earnings_analyses[] → Dashboard 全面可見
   ↓ (next 分析 [TICKER])
investment Phase 1 PM 抽 thin bundle → Phase 2 Fundamentals 深層證據
```

### 驗證
- `bridge.extract_earnings_analyses()` rc=0 → 3 entries(NVDA STRONG / MSFT SOLID + accruals_warning / AAPL SOLID)
- `/api/earnings-cache/<ticker>` 4 ticker 測試:NVDA/MSFT/AAPL 全 cached + report_path 正確,ZZZZ 回 cached:false
- 6 個 JS 檔 syntax check 全 OK
- dashboard_server / bridge import OK

### 重啟需求
- **必須 restart `dashboard_server.py`** 新 PROTOCOL_PROMPTS["earnings"] / GET endpoint / dedup 邏輯才生效
- bridge.py 需重跑一次 → data.json 出 `earnings_analyses[]` 後 Dashboard 才看得到 inline cached chip / earnings.html 才有資料

### 已知限制
- bridge index 僅在 daily `bridge.py` 跑時 refresh;若中途跑了新財報分析,需手動 `python3 bridge.py` 才會反映到 Dashboard(或寫個 watch + auto-refresh,留作後續)
- earnings.html 的「重新分析」按鈕會繞過 cache 但仍走 queue;若 cache hit 時 fetch.py 自己會 skip 11 個 endpoint,所以重複按其實只跑 1 個 income-statement check + analyze + render(快)
- Phase 2 Fundamentals lane 引用 EARNINGS_ANALYST_BUNDLE 的成本是 +500-800 tokens 給 subagent prompt,但僅當 cache 命中(< 90d)時觸發

### 不影響範圍
- 其他 3 個 Phase 2 lane(Sentiment / News / Technical)prompt 不變
- daily protocol 不會自動 enqueue earnings 分析(必須 user 主動觸發 via UI 或 CLI)
- sector / news / triage protocol 不變


## 🟢 Session Note (v1.70.0) — 新 skill: earnings-analyst(`財報 [TICKER]`)+ Skills FMP 遷移盤點

### 動機
User 想要兩件事:(1) 盤點 21 個 skill 哪些值得從 yfinance 遷到 FMP;(2) 補上「個股財報深度分析」(目前 `分析 [TICKER]` 是「監控層級」非「財報層級」,缺逐季三表趨勢、品質 flag、cash flow quality)。

User 點出關鍵 cache 觀察:**財報是季度事件,daily 跑 `分析 [TICKER]` 不應重抓三表**。

### 改動

**1. 新 skill `skills/earnings-analyst/`**(`財報 [TICKER]` 觸發):
- `scripts/fetch.py`(~210 行)— 12 個 FMP HTTP REST 端點 orchestrator,cache key `(TICKER, last_earnings_date)`,TTL 90d 上限。Step 0 先用便宜 income-statement?limit=1 查 last_earnings_date,若 cache 已有同 date 檔且 < 90d → skip 11 個 endpoint
- `scripts/analyze.py`(~270 行)— derive margins_8q / yoy_growth(含加速度) / balance_health / cf_quality;6 個 deterministic quality_flag(accruals/capex outpace/margin compress/DSO slow/negative FCF/debt buildup);composite 0-100(Quality 30 / Growth 30 / Valuation 25 / Analyst 15)
- `scripts/render.py`(~280 行)— 10-section Markdown report → `reports/<DATE>_<TICKER>_earnings.md`
- `scripts/validate.py`(~115 行)— V1.0 schema gate
- `SKILL.md` + `schema.md` 文件化

**2. 觸發整合**:
- `CLAUDE.md` Protocol Triggers 加 `財報 [TICKER]` 列
- `skills/MARKET_INDEX.md` 加新 skill 進 single-ticker 區

**3. FMP 端點探測結果**(關鍵 ✅/❌):
- ✅ /stable/profile / income-statement / balance-sheet-statement / cash-flow-statement(period=quarter limit=8)
- ✅ /stable/key-metrics-ttm / ratios-ttm / financial-growth(period=annual)/ enterprise-values
- ✅ /stable/discounted-cash-flow / price-target-consensus / ratings-snapshot / grades-historical
- ❌ /stable/key-metrics?period=quarter(402 paid;TTM 替代)
- ❌ /stable/analyst-estimates?period=quarter(402 paid;earnings-valuation-forecaster 自算 forward EPS 替代)
- ❌ earningsTranscript / ESG(402 paid;graceful skip)
- ❌ /api/v3/key-metrics, /api/v3/ratios(legacy 端點,2025-08 後不可用)

**4. Skills FMP 遷移盤點**(本 session 只交付盤點,不改 code)

| 排序 | Skill | 預期效益 | 難度 |
|---|---|---|---|
| 1 | momentum-monitor | yfinance OHLC → FMP chart;加 earnings surprise + insider 信號 | 中 |
| 2 | us-stock-analysis | yfinance TTM 概要 → FMP 三表 quarterly 細節 | 中 |
| 3 | ftd-detector | yfinance OHLC → FMP chart EOD,精度與 sector cache 一致 | 低 |

不建議遷移:fred-macro(FRED 是官方源)/ market-breadth-analyzer / sector-analyst(TraderMonty CSV 優於 API)/ tail-risk-analyzer / portfolio-risk-manager(純計算)/ market-news-analyst(web native)/ technical-analyst(chart-native)。

### 驗證
3 個 ticker end-to-end 跑通:
- **NVDA** Q4 FY26: 86/100 STRONG, clean flags(rev +73% YoY accelerating, 75% GM, $51B net cash, FCF margin 51%)
- **AAPL** Q1 FY26 (2025-12-27): 77/100 SOLID, clean flags(Q30/G27/V7/A13)
- **MSFT** Q1 FY26 (2026-03-31): 71/100 SOLID, **accruals_warning flag fired**(說明 deterministic 邏輯有效)

cache hit/miss 測試 OK:首次 12 calls 寫 cache,重跑 1 call(income-statement?limit=1)→ skip。`--force` 繞過 cache。

### 已知限制
- forward EPS 估計需另外呼叫 `earnings-valuation-forecaster`(此 skill 不自動接)
- per-Q 細部 metrics(GAAP-NonGAAP reconciliation、segment revenue)需 paid plan
- mega-cap universe 不限定,任何有 FMP 三表的 ticker 都可跑
- DSO 計算用簡化(receivables/revenue × 91d)

### 不影響範圍
- 不改 `分析 [TICKER]` Phase 2 流程 — earnings-analyst 是獨立深度層,不自動掛 daily protocol(避免 token 浪費)
- 不寫 `data.json` / 不影響 Dashboard
- 3 個 yfinance→FMP 遷移候選(momentum-monitor / us-stock-analysis / ftd-detector)留作後續獨立 PR


## 🟢 Session Note (v1.70.0 補2) — Triage UI: dot 對齊 feed freshness + tooltip 改 fixed/z9999

### 動機
v1.70.0 補1 加了多源整合後，user 看到「dot 顯示 12m 前更新，但下面 feed 都是 16h 前」— 矛盾感非常強。原因：dot 讀的是 **raw.json mtime**（剛 fetch_all_news 抓完所以 12m），但 feed 是 **shallow_news[]**（昨晚 triage.json 結果，published 都是 16h 前）。raw 抓完後 user 還沒重跑 triage，UI 給的訊號就騙人。

另外 tooltip 用 `position:absolute` + Tailwind `hidden group-hover:block` 被 glass-card 的 stacking context 截斷，蓋不住下方 cards。

### 改動（`Dashboard/page-news.js`）

**1. Dot freshness 改讀 feed 自身**
- 原本：`/api/preflight` → raw.json mtime
- 現在：`max(items.published)` from shallow_news — 永遠跟 feed top 第一則一致
- 4-tier 顏色保持但門檻調整：<1h 🟢 / <3h 🟡 / <6h 🟠 / ≥6h 🔴

**2. 新增 stale-cache warning**
- Raw.json 比 feed 新 ≥30min → dot 旁加黃色 ⚠ 圖示
- Tooltip 內加完整警語：「新聞源已更新（X 前），但下面 feed 是上次 triage 結果（Y 前）— 點「更新新聞源」重跑 Stage 1 才會反映新內容」
- 解決「raw 抓了但 triage 還沒重跑」的隱形矛盾

**3. Tooltip 改用 utils.js canonical pattern**
- 從 `position:absolute` + `hidden group-hover:block`（被 glass-card stacking 截斷）
- 改成 `position:fixed; z-index:9999` + JS 動態 `getBoundingClientRect()` 定位（仿 `applySyncLight()`）
- 共用 `#_news_tooltip` element，hover dot 觸發 inject HTML
- 邏輯：preferred top below dot；若會超出 viewport bottom 則翻到 dot 上方
- 與 sidebar sync dot tooltip 視覺一致（同樣 #18181b 底 + #3f3f46 邊框 + 10px font）

### 驗證
- `node -c page-news.js` syntax OK
- 當前 shallow_news：feed top = 0.5h ago（Caterpillar），oldest = 19.3h ago → dot 會顯示「30m ago」+ stale-cache ⚠（因為 raw.json 剛被 fetch_all_news 更新，但 triage 沒重跑）
- 重整 page → tooltip 浮在 dot 下方、不被 cards 蓋

### 設計取捨
- **不用 `applySyncLight()` 直接呼叫**：那個 helper 設計給「資料同步狀態」(綠/橘/黃/紅 + 4 級門檻)，與 triage 的「feed freshness + 可選 stale-cache 警告」邏輯不同。我複用它的 fixed/z9999 tooltip 模式，但內容自製
- **不顯示「最新一則 Xh 前」雙指標**：user 之前明確說過下面排序看得到了不需要。所以 dot 上的數字就是 feed 最新一則的 age


## 🟢 Session Note (v1.70.0 補1) — News Stage 1 多源整合：RSS + Finnhub + FMP + SEC EDGAR

### 動機
User 觀察：「新聞 triage 跑完，最新一則 7h 前」。8 個 RSS feed 本身的「freshness 上限」就被卡在 1-6h（CNBC / MarketWatch RSS index 推送頻率本身慢），勤抓也榨不出新東西。要破這道牆只有加新源。

### 改動
**新增 4 個 fetcher + 1 orchestrator（`news/`）**：
- `fetch_finnhub_news.py` — Finnhub `/news?category=general`（複用 `skills/finnhub-client/scripts/finnhub_client.py` 的 `_request`）。1-5 min latency
- `fetch_fmp_news.py` — FMP `/stable/news/general-latest` + `/stable/news/stock-latest`（注意 endpoint 是斜線分隔不是 hyphen，曾踩坑抓 0 筆）。5-30 min latency
- `fetch_sec_edgar.py` — SEC EDGAR 8-K Atom feed（`?action=getcurrent&type=8-K&output=atom`），需 User-Agent 帶 email（讀 `EDGAR_UA` env，否則 fallback default）。0-15 min material event
- `fetch_news_rss.py` — `FEEDS` list 加 PR Newswire（financial-services-latest）
- `fetch_all_news.py`（orchestrator）— `concurrent.futures` 平行跑 4 個 subprocess，timeout 120s，任一失敗不影響其他源；產 intermediate `*_<provider>_raw.json` 保留 audit，最後合併寫 canonical `*_raw.json`，URL fingerprint + headline tokens 雙層 dedupe，HIGH credibility 優先

**Triage prompt 改源**（`dashboard_server.py:88-94`）：
- `triage` / `news` 兩個 prompt 從 call `fetch_news_rss.py` 改成 call `fetch_all_news.py`

**UI button 改名**（`Dashboard/i18n.js` + `page-news.js`）：
- 「更新 RSS 源」→「更新新聞源」（en: Refresh RSS → Refresh News）
- Section title 加 `(RSS + Finnhub + FMP + SEC EDGAR)`
- Tooltip 提全 4 源 + dedupe 規則
- Confirm dialog 從「重抓 RSS（~30s）+ 60+ 則」改成「平行重抓 4 個源 + 100+ 則」、預估時間 5-8 → 6-10 min

**Protocol 文件更新**（`news/news_protocol_v2.md` Stage 1 段落）— 列出 4 個 fetcher 名稱 + latency + key 需求 + graceful degradation 規則

### 驗證
跑一次 `fetch_all_news.py --hours 24`：
- 4 個源全 OK，412 raw → 393 dedupe（overlap 只 5%，覆蓋互補）
- 最新 12 則 timestamps：0.9m / 4.5m / 6.2m / 6.5m × 2 / 6.8m / 6.9m / 7.4m / 8.9m / 9.4m / 9.7m / 10.9m
- 25 則 < 1h、37 則 < 3h、145 則 < 6h（之前是「最新 7h 前」）
- 393 筆全有 `news_id` + `published`，bridge.py raw_pub_map join 不需改

### 不在範圍
- UI 不加「最新一則 Xh 前」雙指標（user 說下面排序看得到了不需要）
- 沒做：Twitter/X、Cboe options flow、Bloomberg/Reuters terminal feed（成本/接入難度高）

### 注意事項
- **要重啟 `dashboard_server.py`** triage prompt 改動才生效
- 重抓時間從 ~30s（單 RSS）→ ~30-45s（4 平行）；triage shallow snap 工作量隨 raw 量翻倍（88 → 393）會拖長至 ~8-12 min；token 估從 $0.5 → $0.8
- FMP endpoint 路徑陷阱：`news/general-latest`（斜線）不是 `news-general-latest`（hyphen）— 後者靜默回 []


## 🟢 Session Note (v1.69.2) — Triage feed sort: published desc (freshest first)

User follow-up：「triage 的新聞頁面必須按照時間近到遠排序」。

### 改動
`bridge.py:1622-1628` `extract_shallow_news()` 排序由 `(|score|, date) desc` 改成 `(published, |score|) desc`：
- Primary: `published` ISO timestamp 字串字典序倒排 = 時序倒排
- Secondary: `|score|` 同 timestamp 時用衝擊度當 tie-breaker
- 沒 `published` 的（極少數舊資料）`""` 沉到最底

### 為什麼改
v1.69.1 加了 freshness pill 後 user 一眼就能看每則新舊，但 feed 順序仍按 |score| desc — 結果「分數高的舊聞」浮在「剛發生的小事」上面，違反 triage 直覺：分流第一原則就是新的先看。

### 驗證
- Top 5 published：18:07 → 18:05 → 18:03 → 18:03 → 18:02 ✓
- Bottom 3：16:00 同 timestamp，secondary 用 score 排序 ✓

---

## 🟢 Session Note (v1.69.1) — News triage freshness pill + protocol-queue KeyError fix

### 動機
跑 6 分鐘 news triage 後 UI 看不出哪些新聞是新的、哪些已在富途看過 — triage（分流）的核心就是 freshness 判斷，缺了相對時間標籤等於沒做 triage。順便修了今天觸發 triage 時 protocol-queue thread 直接炸 `KeyError: '\n  "timestamp"'` 的 bug。

### 改動
**1. `dashboard_server.py:316-323` — 修 KeyError**
- `PROTOCOL_PROMPTS["triage"]` 內含 JSON schema 範例（字面 `{...}`），原本 `.format(**params)` 把它當 placeholder 解析炸掉
- 改成 manual token replace：`prompt.replace("{" + k + "}", str(v))`，只替換 known params (`ticker` / `headline` / `risk_tolerance`)，字面大括號保留

**2. `bridge.py:54-75` — 提升 `_raw_pub_map()` 到 module 層**
- 原本只在 `extract_shallow_news()` 內部 closure；deep 路徑想用就 copy-paste
- 提到模組層共用，single source of truth

**3. `bridge.py:1438-1492` `extract_news()` — Deep verdict 也 join `published`**
- 對 digest.json verdict 走 `pub_map.get(news_id)` fallback 補 `published` 欄位
- 驗證：17 筆 deep news 16 筆有 published（1 筆 fallback 沒對應 raw.json，UI graceful fallback 到 date）

**4. `Dashboard/page-news.js` — Freshness pill 三處生效**
- L8-21：把 `relTime()` 提到 DOMContentLoaded scope（共享 helper），加 `if (!isFinite)` / `if (diff < 0) return 'now'` 邊界保護
- L778-786：刪掉 `initFutuPush()` IIFE 內重複定義（走 closure 到 outer）
- Triage card (L430+)：在 score badge 旁加「12m ago」pill，4 級顏色（<1h emerald / <6h zinc-400 / <12h zinc-500 / ≥12h zinc-600），中英隨 `UI.currentLang` 切「前/ago」
- Deep verdict card (L178+)：右上 date block 升級為「Xh ago / YYYY-MM-DD」雙行，hover 顯示完整 ISO

**5. `dashboard_server.py:87-95` — Protocol prompts 加 `published` 寫入要求**
- `news` (DIGEST)：第 8 條硬規定，「verdict 必須帶 published 欄位」
- `flash_text` (FLASH from Futu push)：verdict 欄位列表加 `published (ISO timestamp — 用 WebFetch 取得的原始發布時間)`
- `review`：覆寫 verdict 時保留 `published`，缺則從 raw.json 補
- 未來新跑的 verdict 自帶 published，bridge 不必依賴 raw.json join；舊資料 fallback 到 join

### 驗證
- `python3 bridge.py` rc=0 → `data.json` 中 `news[].published` 16/17、`shallow_news[].published` 60/60
- `node -c page-news.js` syntax OK；`python3 -c "import dashboard_server"` OK
- 前端：點 News tab → Triage 子 tab，每張 card 標題列有彩色「Xm/Xh ago」pill；點全部/已審核/待審核 deep verdict 同樣顯示

### 不在範圍（user 明確選不做）
- 按 published desc 自動排序 freshest first
- 「< 6h only」過濾 toggle / localStorage dismiss 已讀
- RSS 源檢討、加 Twitter/X / SEC EDGAR real-time / cron pre-warm RSS（速度不是這次主軸）

### 使用須知
- **要重啟 `dashboard_server.py`** prompt + KeyError 修補才生效
- 既有 digest.json（v1.69.1 之前產生的）verdict 沒寫 published，靠 bridge join raw.json 補；未來新跑的會自帶
- `relTime()` 是純前端即時計算，reload 一次相對時間就會更新

---

## 🟢 Session Note (v1.69.0) — Sector V1.4: FMP estructured layer (P1-P4)

### 改動
依 `~/.claude/plans/sector-protocol-fmp-precious-cake.md` 落地 P1-P4(Plan 在 FMP MCP 401 卡關後恢復;此 session 完成全部實作):

**新增 fetch scripts(全走 FMP HTTP REST + `$FMP_API_KEY`,hard-fail)**:
- `sector/scripts/fetch_sector_valuation.py`(~210 行)— P1:11 sector × NASDAQ+NYSE PE TTM,1y daily PE z-score(雙 exchange 平均),sector ETF 3M return - SPY 3M(用 chart light EOD,因 batch-quote 402),20d ETF volume ratio
- `sector/scripts/fetch_earnings_pulse.py`(~160 行)— P2:131 mega-cap 30d earnings beat/miss/in-line + clipped surprise%(±100% cap 防 INTC 0.019 estimate 拉爆 avg);analyst_revision_net 延後到 P2.5
- `sector/scripts/fetch_smart_money.py`(~190 行)— P3:per-symbol insider acquired/disposed quarterly ratio + senate-latest 30d window aggregated by sector;form13f_top10_delta 延後到 P3.5(industry-summary 402)
- `sector/scripts/fetch_sector_news.py`(~120 行)— P4:per-sector top-5 mega-cap × `news/stock` 結構化 headline,取代 WebSearch ≤5 → ≤2

**Validator + schema V1.4 hard-fail gates**:
- `_phase1.sectors[].sector_valuation`(pe_ttm / pe_zscore_1y / rs_vs_spy_3m / etf_volume_ratio_20d)
- `_phase3.sector_earnings_pulse`(report_count / beat_rate_30d / surprise_score_avg)
- `_phase3.smart_money_signals`(insider_acquired_disposed_ratio_q / senate_net_buy_30d)
- `sectors[].score_components.valuation_penalty`(deterministic ±10/+5 overlay)

**Protocol 文件**:
- `sector_protocol_main.md` V1.3 → V1.4,加 Step 5b Valuation Penalty Overlay
- `phase_1-2-3.md` Phase 1 加 Step 2 sector valuation;Phase 3 加 Step 3b/3c/3d (earnings pulse / smart money / news cache);WebSearch ≤5 → ≤2
- `phase_4-5.md` Phase 4b Devil's Advocate 加規則 5 — smart money divergence 強制檢查
- `render_sector_report.py` 加 Sector Valuation Snapshot 節(自動標 🔴 OVERBOUGHT / 🟢 OVERSOLD VALUE)

**FMP MCP 探測結果**(blocker 已修;此 session 開頭):
- ✅ `marketPerformance/sector-PE-snapshot`、`historical-sector-pe`、`sector-performance-snapshot`、`chart/historical-price-eod-light`、`quote/quote`(single)、`calendar/earnings-calendar`、`insiderTrades/insider-trade-statistics`、`senate-latest`、`news/search-stock-news`
- ❌ 402 paid plan(已迴避):`quote/batch-quote`、`form13F/industry-summary`

**驗證**:V1.4 round-trip(載 2026-04-29 真實 cache 補強舊 log 模擬 V1.4)→ validator rc=0 + render rc=0(8.2KB md,Healthcare 自動 🟢 OVERSOLD VALUE)

### 已知限制
- `analyst_revision_net`(P2)、`form13f_top10_delta`(P3)目前都 null,需 paid plan/額外 cache layer
- mega-cap universe (~131 ticker)是手動硬編碼的;sector 變動或新 IPO 需手動加
- Phase 1 sector valuation 一次跑要 ~36 calls;FMP free tier 250/day 仍可承受 daily 但需注意 rate limit

### 接續工作(若想做)
1. 把 4 支 fetch script 加入 `daily_update.sh` 使早晨自動 prefetch cache
2. 寫 `backtest_valuation_overlay.py` 驗證 valuation_penalty 是否提升歷史 alpha
3. P2.5 / P3.5 paid-plan 補回 analyst_revision_net + form13f_top10_delta


## 🟢 Session Note (v1.68.0) — I-PF: Phase 2 共通 prompt 加 FORBID web search 白名單

### 改動
`investment/investment_protocol_v4_8.md` Phase 2 共通 subagent prompt 模板（行 308 後）加新區塊 `DATA SOURCE DISCIPLINE`：

**❌ FORBIDDEN（禁 web search 重抓）**：
- Quote / Valuation: price/peRatio/forwardPE/pegRatio/epsTTM/mktCap/dividendYield/priceToBookRatio
- Quality / Forward: roeTTM/debtToEquity/fcfPerShareTTM/nextEarningsDate
- Market signals: VIX/F&G/SPY RSI/breadth/FTD/market_top_score
- Insider / short: 所有 insider 數字、MSPR、short_pct_float
- Analyst: rating consensus / price target / upgrade-downgrade history
- Filings: 10-K/Q/8-K
- Company news headlines（fetch.py 已涵蓋 3 來源 deduped）
- OHLC / RSI / MACD / MA

**✅ ALLOWED ≤ 1 web search call（僅 narrative tone）**：
- Reddit/X/StockTwits sentiment narrative
- Conference call transcript / management commentary
- Supply chain rumors / 地緣政治
- 競爭格局 / market share narrative
- Product reviews

**違規處理**：subagent 引用 web search 數字而非結構化 source → PM 在 Phase 2.5 自動扣 confidence 0.2；連續 3 次該 lane degraded。


## 🟢 Session Note (v1.67.0) — I-PE: Phase 0 schema 加 `_market_signals` + Phase 2 共通 prompt 直接 inline pass

### 改動
- `investment/investment_protocol_v4_8.md` Phase 0 JSON schema 新增 `_market_signals` block：
  - `fear_greed_index` / `vix_current` / `vix_regime` / `spy_rsi_14` / `spy_pct_above_ma200`
  - `breadth_composite` / `ftd_status` / `ftd_days_since` / `market_top_score`
  - `top_catalysts[]`（從 sector_intel 注入）
- Phase 2 共通 prompt 段落更新：`PHASE 0 MACRO CONTEXT` 區塊 inline paste 包含 `_market_signals`
- Sentiment lane rubric 改寫：**「優先讀 Phase 0 `_market_signals`」**；只有缺欄位時才跑 sentiment.py 抓市場層
- News lane rubric 改寫：**「優先檢查 Phase 0 `_market_signals.top_catalysts[]`」**；只有沒涵蓋或需 24h 內最新才跑 fetch.py

### 效益
- Sentiment lane 多 ticker 連續跑：第 2 個 ticker 開始市場層直接 inline 不用 yfinance call（~省 1.5 min/ticker）
- News lane 多 ticker 連續跑：top_catalysts 已 cover 的 ticker 可直接引用（fetch.py call 變可選）
- Phase 2 共通 prompt 多了 ~200 tokens 的 _market_signals JSON 但省下 4 lane 各自 fetch 的 LLM token 跟時間


## 🟢 Session Note (v1.66.0) — I-PD: Phase 0 L3 fallback 從 web search 改 skill chain

### 改動
`investment/investment_protocol_v4_8.md` Phase 0 三層 cache L3 重寫：
- **舊** (v4.8)：「皆 STALE 或缺失 → 執行 market-news-analyst skill（或 web search），寫入 phase0.json」 — 模糊，容易 fallback web search
- **新** (v4.9 / I-PD)：「皆 STALE 或缺失 → 跑 4 個 skill chain」：
  ```bash
  python3 skills/market-sentiment-analyzer/scripts/sentiment.py
  python3 skills/market-breadth-analyzer/scripts/market_breadth_analyzer.py
  python3 sector/ftd_yfinance.py
  python3 sector/market_top_yfinance.py
  ```
  合成 4 個 skill 輸出 + L4 fred-macro → `phase0.json` (`phase0_source: SKILL_CHAIN`)。
- LLM web search 只留給 `key_themes` / `bullish_signals` / `bearish_signals` 敘事面（VIX/F&G/breadth/FTD/market-top 數字一律 API）。
- ≥ 2 個 skill 失敗才退回 web search，標 `phase0_source: WEB_SEARCH_FALLBACK`

### 效益
- 同 ticker 兩次跑得到 deterministic 數字（VIX 18.72 不變）
- 省 LLM token（web search 一次 ~5K tokens）
- 跨 session 可重現（regression test 友善）


## 🟢 Session Note (v1.65.0) — I-PC: News lane 加 FMP analyst grades / price-target / Finnhub company-news

### 改動
- `skills/market-news-analyst/scripts/fetch.py` 加 5 個 FMP `/stable/*` endpoints + 1 個 Finnhub:
  - **FMP `/stable/grades-historical`** → `analyst_actions[]` 過去 30d upgrade/downgrade（含 action/firm/newGrade/previousGrade/url）
  - **FMP `/stable/grades-consensus`** → `analyst_consensus` 當前 strong_buy/buy/hold/sell/strong_sell 分布
  - **FMP `/stable/price-target-consensus` + `/price-target-summary`** → `price_target` 高/低/median/consensus + 月/季/年 trend
  - **FMP `/stable/grades-news`** → `analyst_news[]` 評等變動相關新聞
  - **FMP `/stable/sec-filings-financials`** → `sec_filings_recent[]`（取代壞掉的 `/api/v3/sec_filings` Legacy 403）
  - **Finnhub `/company-news`** → 補進 headlines pool（含 category + sentiment 欄位）
- `analyst_actions` 來源策略：FMP grades-historical（主）→ finvizfinance（fallback 當 FMP 空）
- `data_quality` block 加 `fmp_calls` / `fmp_failures` / `finnhub_news_count` / `fmp_grades_count` 等診斷欄位
- `investment/investment_protocol_v4_8.md` Phase 2 News rubric 改寫：列出新增的 4 個結構化 fields，subagent 必須優先用、禁止 web search 重抓 analyst rating 數字

### Smoke test (NVDA, 168h)
```
headlines: 129 (finviz 100 + yfinance 10 + Finnhub 25, deduped)
analyst_actions: 1 (source=fmp_grades_historical)
consensus: {strong_buy:2, buy:58, hold:16, sell:3, strong_sell:0, consensus:"Buy"}
price_target: {high:400, low:140, consensus:279.96, median:275, last_quarter_count:11 avg=290.27}
fmp_calls: 6, fmp_failures: 0
```

### 替代了什麼
- finvizfinance scraping（脆弱、layout 改 break）→ FMP `/grades-historical` 結構化
- LLM 從新聞文字「猜」price target → FMP `/price-target-consensus` 數字
- analyst rating 從 web search 推論 → FMP `/grades-consensus` 結構化分布
- Legacy FMP `/api/v3/sec_filings` 403 → `/stable/sec-filings-financials`


## 🟢 Session Note (v1.64.0) — I-PB: Sentiment lane 個股層 web search → 結構化 API

### 改動
- `skills/market-sentiment-analyzer/scripts/sentiment.py` 加 `--ticker X` 參數：
  - FMP `/stable/insider-trading/statistics` → 最近 4 季 acquired/disposed 統計（`acquired_disposed_ratio` 是按 transaction 個數的比，非股數）
  - Finnhub `/stock/insider-sentiment` → 最近 6 個月每月 MSPR（小型股可能 sparse → null acceptable）
  - yfinance `info.shortPercentOfFloat` → short interest fallback（FINRA bi-monthly snapshot）
- 輸出 JSON 加 `ticker_signals` block：`insider_stats[]` / `insider_sentiment.latest_mspr` / `short_pct_float`
- 市場層仍維持 15 min cache；個股層 per-ticker fresh
- `investment/investment_protocol_v4_8.md` Phase 2 Sentiment rubric 改寫：
  - 一個指令 `sentiment.py --ticker X` 同時拿市場層 + 個股層
  - **禁止 web search Reddit/X/insider/short 數字**；只能保留 ≤ 1 次 Reddit/X narrative tone search
  - 融合公式從 `0.4×stock + 0.6×market` 改成 `0.5×stock + 0.5×market`（個股層權重提高，因為訊號變結構化更可信）
  - 個股 stock_specific 打分規則明列（insider ratio / MSPR / short %）

### Smoke test (NVDA)
```
ticker_signals.insider_stats Q1/2026: ratio=0.163, acq=60M, dis=31M shares, 15 acq tx vs 92 dis tx → 顯著賣壓
ticker_signals.insider_sentiment.latest_mspr: None (NVDA 該月無 insider transaction)
ticker_signals.short_pct_float: 1.22% (yfinance / FINRA bi-monthly)
```

### 替代了什麼 web search
- 「web search Reddit/X」→ 仍允許 narrative tone（無 API 等價）
- 「web search short interest」→ FMP/Finnhub 都沒 free tier endpoint，yfinance 是合理 fallback
- 「web search insider activity」→ FMP `/insider-trading/statistics` 結構化、可比較


## 🟢 Session Note (v1.63.0) — I-PG: Technical lane OHLC FMP-primary

### 改動
- `skills/momentum-monitor/scripts/technical_core.py` `fetch_history()` 改成 FMP-primary：
  - 加 `_fetch_fmp_ohlc(ticker, period)` 用 FMP `/stable/historical-price-eod/full`，回 yfinance schema 的 DataFrame（OHLCV 大寫欄位、DatetimeIndex 升序）
  - `fetch_history()` 邏輯：先嘗試 FMP（FMP_API_KEY 設定 + 200 OK + 非空），失敗才 fallback yfinance
  - 仍回 `(hist, yf.Ticker)` tuple — yf.Ticker handle lazy 不打 API，給 momentum.py `_short_interest_block(t.info)` 用
- 同時影響 `technical-analyst` 跟 `momentum-monitor` 兩個 skill（都共用 technical_core）

### 跨 provider 差異
- FMP `/historical-price-eod/full` 是 split-adjusted（不含 dividend adjust），yfinance auto_adjust=True 是 dividend-adjusted
- 對 RSI/MA/MACD pattern recognition 影響 < 1-2%（累積股息），不影響技術訊號
- 配息股（KO/JNJ/PG）MA 數值會比 yfinance 略高，acceptable

### Smoke test
```
NVDA 1y → 254 rows OHLCV
technical-analyst: price=208.94, MA stage=Stage 2 uptrend, RSI=65 bullish, MACD hist=1.784
momentum-monitor: composite=58.8, signals=[stage2_uptrend_intact, low_short_interest, fresh_golden_cross_20_50]
```

### 效益
- yfinance scraping fragility 解決（Yahoo 偶爾擋 IP / schema 變動）
- FMP `/historical-price-eod/full` 多含 `vwap` / `change` / `changePercent`（目前未用，可未來擴展）
- Starter rate limit 充裕（300/min vs yfinance IP-based）


## 🟢 Session Note (v1.62.0) — I-PA: dual_fetch 9 → 15 scalar (Invest Protocol Refactor 第 1 步)

### 改動
- `skills/finnhub-client/scripts/dual_fetch.py`：CANONICAL_FIELDS 從 9 → 15，新增 6 個欄位 (`forwardPE`, `pegRatio`, `roeTTM`, `debtToEquity`, `fcfPerShareTTM`, `nextEarningsDate`)
- Finnhub side：從現有 `/stock/metric` 抽 `forwardPE` / `pegTTM` / `roeTTM` / `totalDebt/totalEquityAnnual`；fcfPerShare 從 `pfcfShareTTM` 推導 (price / pfcfShareTTM)；nextEarningsDate 走 `/calendar/earnings`（多 1 個 API call）
- FMP side：擴充 `/stable/ratios-ttm` 取 `debtToEquityRatioTTM` / `freeCashFlowPerShareTTM` / `forwardPriceToEarningsGrowthRatioTTM`（forward PEG）；nextEarningsDate 走 `/stable/earnings-calendar` filter
- `compute_diff` 加 DATE_FIELDS 集合，date 欄位用 match/mismatch boolean 不算 %
- `investment/investment_protocol_v4_8.md` Phase 2 Fundamentals lane TICKER_DATA_BUNDLE 規則：列 15 個 scalar、加 6 個新欄位的估值打分規則（forwardPE / pegRatio / roeTTM / debtToEquity / fcfPerShareTTM / nextEarningsDate 用法）

### 跨 provider 預期 diff
NVDA smoke test：
- price/previousClose/dayHigh/dayLow：< 0.25%（intraday tick noise）
- 大多估值欄位：< 4%
- **pegRatio**：85% diff（Finnhub trailing PEG 0.66 vs FMP forward PEG 1.22 — 不同方法論）
- **debtToEquity**：35% diff（Finnhub annual 0.054 vs FMP TTM 0.073 — 不同 time frame）
- pegRatio + debtToEquity 的 audit diff **預期會大**，是 expected behavior，不是 bug

### Smoke test
```
python3 skills/finnhub-client/scripts/dual_fetch.py --tickers NVDA --output-dir /tmp/dual_test
→ scoring 含全部 15 scalar；_audit.fmp 含對應 audit 值；_audit.diff 12 個 %（3 個 fields FMP 沒提供）
```

### Phase 2 Fundamentals lane 預期效益
- us-stock-analysis 改成「讀 bundle 不重抓」 → 省 ~2-3 次 API call
- 新增 forwardPE / fcfPerShareTTM 直接給 subagent 估值打分用，省一次 yfinance / FMP fetch
- nextEarningsDate ≤ 7 天觸發 conviction 自動降權，避免 earnings whipsaw

### Note：FMP API key rotation
User 升 Starter plan 後 FMP rotate 了 API key。`.zshrc` 已更新新 key (SyJJzDfG...)。所有後續 Bash 開頭 `source ~/.zshrc` 才會抓到新值。


## 🟢 Session Note (v1.61.5) — 修嚴重 bug：cancel 後整條 queue 卡死

### 災情
User triage 跑卡了，按 Cancel 後 status=cancelled。但後面 enqueue 的 invest (MRVL, CRWV) 永遠不開始跑。

### 根因
`cancel_protocol()` 只設 `status="cancelled"`，**沒設 `ended_at`**。依賴 `_run` thread 的 post-wait block 設 ended_at，但這次該 thread 沒走到（可能 reader thread / lf.close 卡住、或 SIGTERM 被 claude CLI 吞掉）。

Worker dispatch 後等待回收的 loop：
```python
if s != "running" and ended:   # ← ended is None → 條件 False → 死循環
    break
```

### 修
1. **`cancel_protocol()`**：cancel 時立即設 `ended_at` + `elapsed_sec`，不再依賴 _run thread post-wait
2. **Recovery path**：如果第二次 cancel 看到「status=cancelled 但 ended_at=None」（previously cancelled but stuck），主動補設 ended_at + 清 `_protocol_proc["p"]` 給 caller
3. **Worker wait loop**：放寬條件為 `s in ("done","error","cancelled","idle")`，不再檢 ended_at（防禦縱深）

### 用戶需要
- **重啟** dashboard_server.py 才會載入新邏輯
- 重啟後 queue 會空（in-memory），MRVL + CRWV 要從 Quick Launch / decisions 重新點分析


## 🟢 Session Note (v1.61.4) — Triage 燈號 tooltip 修：native title 太小看不到 → 改 CSS group-hover

### 問題
v1.61.3 用 native HTML `title` attribute 寫 tooltip，但 dot 只有 10px (w-2.5 h-2.5) 在 macOS Safari 上 hover 不太可靠/根本不顯示。

### 修
- 把 dot 跟「3h」age string 包進同一個 `relative group inline-flex` 容器擴大 hover 命中範圍
- tooltip 改 CSS-only：absolute hidden `group-hover:block`，用 `whitespace-pre-line` 處理多行
- 加 `cursor-help` 視覺暗示
- 移除舊 `title` attribute（雙重設置反而干擾）

### 結果視覺
```
🗂 Stage 1 RSS Triage    30 則    ● 3h    [↻ 更新 RSS 源]
                                  ↑ hover 此區塊跳 320px 寬 tooltip
```


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
