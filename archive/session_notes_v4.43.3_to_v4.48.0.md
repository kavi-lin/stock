# Session Notes 歸檔 v4.43.3 → v4.48.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v4.48.0) — 盤中評估引擎（Intraday weakness tape：破底/止跌/量價）
- **起因**：user 問「市場氛圍」是否參考過去幾天股價走勢+成交量、是不是 LLM 判斷。查證 `mood.py` = deterministic 0 LLM，只用 VIX/SKEW/PCR/F&G（波動率情緒），**價格趨勢僅間接、成交量完全沒用**。user 要求新增一條會看**盤中即時 + 近幾天走勢 + 量能**、能抓**破底/止跌/高開低走/量價背離**的完整盤中指標。
- **設計拍板（AskUserQuestion）**：資料源 = **FMP**（釐清：Finnhub `/stock/candle` 盤中 K 為付費，故盤中分鐘 K+量只能走 FMP）；呈現 = **獨立「盤中評估」面板**；更新 = **dashboard_server 常駐 poll loop**。
- **實作**：新引擎 `skills/market-sentiment-analyzer/scripts/intraday.py`（0 LLM，純函式 `assess()` core + FMP fetch via `fmp_pool`）讀 5-min bars + ~60 日 daily，對 SPY/QQQ/IWM 算 signed −100..+100（負=破底）。訊號：破底(5/20/50d 分級)、止跌(反彈/收復假跌破)、高開低走、量增價跌(RVOL)、VWAP、MA20、連跌、O'Neil 出貨日。`UNIVERSE`/`WEIGHTS`/門檻皆檔頭常數可調（探索期）。
- **接線**：`dashboard_server.py` `intraday_mood_poll_loop`（盤中每 300s + 開機 + 收盤後快照；獨立 lock）+ GET `/api/intraday-mood/{data,state}` + POST `/refresh`；`Dashboard/intraday-mood.html`（綜合分量表 + 旗標 + 每檔卡）；`utils.js` nav「盤中評估」；`index.html` mini-strip；`daily_update.sh` Step 9.35 基線；`test_intraday.py` 26 asserts。
- **驗收**：26-assert 測試 ALL PASS；live FMP smoke（盤中 frac 0.44，agg 中性，3 檔齊全 rvol/ma/破底偵測）；server 8099 boot → 4 endpoints 200/202 `available:true`；check_skills 0 warnings；VERSION 三處同步 4.48.0。**踩雷修正**：daily 端點 stable 用 `historical-price-eod/full`（非 `historical-price-full`，後者回 None）。
- **紀律**：探索層，**不**入 investment_protocol 決策（同 break_news/nexus）。待 user commit（在 working tree）。可調 universe / poll 間隔 / score 取向。

## 🟢 Session Note (v4.47.2) — weekly-tech-playbook：Codex Review 整合優化（解耦 fatal gate + 去自打臉 nag）
- **起因**：user 請 codex review 並改 code（結果已在 working tree），要我檢討優化。Codex 加了一整套「committee-blind then reconcile」獨立 review：build_pack 多寫 `blind_pack_<DATE>.json`（去委員會 verdict 防 anchoring）、selections 加 `codex_review` block、render 驗證 + 渲染、review.py 把 Codex 替代配置（含現金 sleeve）一起評分排名、page-playbook 加面板。
- **評估**：review **內容**強（抓到原三籃 ~100% 部署 vs macro 60–75% 的矛盾 → 現金當正式 sleeve、部署 75%；降權 MU/MRVL/CRDO 抛物線股；檢討加 QQQ/SOXX+回撤）——保留。但**工程整合**兩個 gating bug。
- **修法（不動 Codex 好設計）**：
  - **P1 解耦（關鍵）**：`render.py` 把 `codex_review` 從 fatal 必填改為**可選**——缺它仍 rc=0 生成（原本缺 review→rc=1 不出檔，依賴反轉、破壞可重跑）。提供時才驗結構。
  - **P2 去自打臉 nag**：原「非 blind→degraded」對每份非盲評都 rc=2（含 Codex 自己這份）。改為只在明確宣稱 `review_mode=committee_blind_then_reconcile` 時才要求 `blind_artifact`（fatal）。
  - **P4 比較公平性**：`review.py` Codex sleeve 加 `deployed_pct`/`cash_pct`，標「部署 75%」，避免含現金的 alpha 被當同 beta 比。
  - **SKILL.md** Step 2.5「必填」→「建議；對生成可選」與 code 對齊。
- **驗收**：render WITH review → rc=0（原 rc=2 nag 消失）；render WITHOUT review → rc=0 仍生成（原 rc=1）；review CLI 顯示「部署 75%」；py_compile + node -c OK。
- **未做（留 user 決定）**：P3 schema 欄位 `codex_review` 綁工具名，可泛化為 `independent_review` + `reviewer` meta；P5 render 同時生成+驗證自身 critique（職責混合）；P6 review.py 對「不在三籃內」的 codex 標的無進場價會當 flat（本週全在籃內故無影響）。
- **待 user**：仍未 commit（整個 feature + Codex 改動 + 本次優化都在 working tree）。

## 🟢 Session Note (v4.47.1) — weekly-tech-playbook：三籃子 $100k 科技投資方案 + Dashboard 頁 + 檢討機制
- **起因**：user 要把「從本週系統分析（指標線 + 新聞辯論 + 委員會 verdict）擬下週科技投資方案」變成常駐工具——保險 100% / 激進 100% / 混合 100% **各假設投入 $100k**，附理由+數據，供下週 LLM 一起檢討。先 commit 既有 snapshot（`1b16b11`，chore/snapshot 分支）再切 `feat/weekly-tech-playbook` 開工。
- **設計拍板（AskUserQuestion）**：(1) 籃內配重 = **信心分級**（核心 $15k×3 / 標準 $10k×4 / 輕倉 $5k×3 = $100k）；(2) 打包成 **skill + 新 Dashboard 頁**。
- **流程三段**：`build_pack.py`（0 LLM 組資料：regime + 熱題 + 近 14d 委員會 verdict 解析 + yfinance 報價/動能）→ LLM 寫 `selections_<DATE>.json` 選股 → `render.py`（0 LLM 算股數/成本、驗證每籃=$100k、rc 0/1/2）→ `Dashboard/playbook.json` + `reports/<DATE>_TECH_PLAYBOOK.md`。
- **本週首版**（2026-06-22，下週 06-23 起）：保險 NVDA/AVGO/MSFT/GOOGL/META/ORCL/TXN/AAPL/ANET/TSM；激進 AMD/CCJ/CEG/MU/MRVL/ALAB/CRDO/NBIS/PLTR/IONQ；混合 65% 保險 sleeve + 35% 激進 sleeve。背景 RISK_ON + 實質利率 2.17% 高檔 + Core PCE 6/25 binary → 激進籃過半近月漲 45–76%、委員會多標過熱故標「等回檔/小注/停損」。render rc=0，三籃各約 $99.4–100.2k（whole-share rounding，drift <2%）。
- **檢討機制（v4.47.1，user「請 LLM 檢討的機制也寫上」）**：`review.py`（0 LLM）讀 `render.py` 寫的 immutable dated snapshot `data/playbook_<ENTRY>.json`,抓檢討日收盤算每檔報酬 / 每籃 vs SPY alpha / 命中率 / kill 觸發（從 kill 文字擷取門檻價,跌破標 🔴）→ `reports/<REVIEW>_TECH_PLAYBOOK_REVIEW.md`（含空白「🧠 LLM 檢討」段）+ `Dashboard/playbook_review.json`。Claude turn 讀數據填質性判讀（哪籃贏+為何 / kill 認賠或續抱 / 貢獻+拖累 / 催化兌現 / 下週調整）→ 可改下週 selections。觸發詞「投資方案檢討」。page 頂部「上週方案檢討」橫幅（僅 entry≠review 日顯示,避同日 0% 退化）。永不自動覆寫 config（比照 short-term weekly_review）。
- **驗收**：`check_skills.py --skill weekly-tech-playbook` 0 warnings；`node -c page-playbook.js` OK；render.py rc=0、emit dated snapshot；review.py 同日 smoke rc=0（entry=asof → 0% 為預期）;playbook.json 三籃加總正確。
- **紀律**：前瞻探索層，**不**入 investment_protocol 決策。委員會單股 verdict 仍以各自報告為準。
- **待 user**：重啟 dashboard_server → 開 `/playbook.html` 看三籃；下週同日跑 `review.py --date 2026-06-22 --asof <下週日>` 產檢討,再讓 LLM 填質性段。可考慮 `/schedule` 每週一自動跑 build_pack + render、週末自動跑 review。

## 🟢 Session Note (v4.46.0) — 現值估值 confidence 接錨點一致性（破假精確）
- **起因**：user 貼 ARM 現值估值截圖（FV $52、現價 $375、$3–$164、LOW AGREE、`confidence: high`）質疑「不太合理吧」。
- **診斷**：方向是真的（$375 高於每一個錨點，連 analyst PT $164 也是），但 **$52 單點 + high confidence 是假精確**。root cause = `compute_fair_value_summary` 的 confidence 只看「有幾個錨點回傳數字」(n≥5→high)，不看一致性；同引擎 `fair_value_range` 早就算出 cv=1.20 / `agreement_grade=low`，沒回灌。DCF/owner-earnings 佔 55% 權重把前瞻成長股估到 $3–$12。
- **修法（通用，全標的）**：`reconcile_confidence()` 用**錨點離散 cv 兩段式**封頂 confidence（cv≥0.6→low、0.35–0.6→medium、<0.35 不動；記 `confidence_count_based` + `confidence_capped_by`）；range 加 `dispersion_ratio`；`page-decisions.js` Track A `cv≥0.6` 時 FV 點改灰 + `⚠ 錨點分散 N×` caption。
- **校準關鍵（user 拍板）**：backfill dry-run 發現有 grade 的 12 筆 snapshot **全部 grade=low**（含 AAPL）—— `owner_earnings_mult` 是全科技股結構性低離群值，cv 普遍 >0.35，直接綁 grade 會讓科技股一律 low、無鑑別度。改 cv 兩段式後：ARM/PLTR(50×+)→low、AAPL(11×)→medium。**不**自動剔錨點（median-ratio 會誤殺 analyst PT）；重新加權交給 `hypergrowth` archetype（shadow-only，待 ≥20 session 翻轉報告）。
- **backfill**：`Dashboard/data.json` 既有 snapshot 一次性重算 —— 13 筆補 dispersion_ratio，8 筆 confidence 變動（TSM/ARM/AMD/PLTR/GOOGL→low；AAPL/NOK/MU→medium）。
- **驗證**：engine golden 5 fixtures/38 asserts pass；ARM CLI 實測 confidence high→low、span 51.66×；`node --check` page-decisions.js pass。

## 🟢 Session Note (v4.45.0) — 供應鏈 Wave B：UI 訊號下鑽 + FMP budget tiering + node 人工校正
- **接續 Wave A**：user「繼續 wave b」。收口前次規劃三項 #5/#7/#8，跨 `supply_chain.py` + `dashboard_server.py` + `page-supply-chain.js` + `supply-chain.html` + 測試。
- **#7 UI 下鑽**：Wave A 算的 `direction`/`stale` 終於進 UI。edge row 加 `⚠ 方向衝突`(紅) / `✓ 方向確認`(綠) chip；node card + detail 加 stale(⏳ 半透明) + user_status(✓ 綠框 / ⚑ 黃虛線框)。
- **#5 budget tiering**：spine / 有 ticker / ≥2 downstream = priority；headroom<0.5 時週邊 node 只服務 peers cache（`_fetch_peers(allow_network=False)`）+ 跳 name-search，核心 node 不因 budget 燒乾失驗。profile TTL 7d→30d。data_quality 加 `override_count`/`fmp_peers_deferred`/`fmp_budget_headroom`。
- **#8 node override**：`overrides/<slug>.json` sidecar（**永不改寫 LLM YAML**），enrich 先 merge（修正欄位優先、流經 grounding+FMP）。`POST /api/supply-chain/<slug>/override`（pop cache 強制重 enrich）。detail panel ✓確認/⚑標記/清除 button。status confirmed/flagged/none + field 修正 + note；清空自動移除 entry。
- **驗收**：`pytest tests/test_supply_chain_enrichment.py` **23 pass**（18+5）；`py_compile` server+engine OK；be chain override roundtrip 驗 user_status/override_count 後清乾淨（無 git 殘留）。
- **供應鏈 8 gap 分析至此 Wave A+B 全收口**。剩餘未做：原 #2 已在 Wave A、所有 8 項皆已處理。後續若要：override 加 field-edit 表單 UI（目前 status+note via UI、field 修正僅 API）、relation 來源 clickable 連回新聞流。

## 🟢 Session Note (v4.44.0) — 供應鏈 Wave A：方向校驗 + 回寫閉環 + stale/relative-heat/ADR
- **起因**：user 要對現有供應鏈系統提優化。先做 8 項 gap 分析，user 選「Wave A 先」= 純後端高 ROI 六項（#1/#2/#3/#4/#6/#9），全集中 `scripts/nexus/supply_chain.py` + 測試。
- **#1 方向校驗**：digest co-mention 是對稱訊號（只證兩 ticker 相關、非誰供誰），LLM 畫的箭頭可能反。`_direction_check()` 改用 Nexus *directed* SUPPLIES_TO/CONTRACT_MFG_FOR edge 校驗 → `confirmed/conflict/unverified`；corroborated 但方向矛盾 → weight 1.0→0.5 + `relation_evidence.direction`。
- **#2 回寫閉環**：`export_corroborated_edges()` + CLI `--export-edges`。enrich serve 路徑維持唯讀紀律（不碰 KG）；改 opt-in batch，把 corroborated 方向乾淨 edge 寫 `bn_*.json`（schema 對齊 build_artifacts）餵 Nexus tier-1。source 標 `supply_chain`（非 `break_news:`）故不會被下次 enrich 當獨立 break-news 佐證 → 無增強迴圈。跨 chain dedup。實測 be chain 產出 `VRT SUPPLIES_TO ORCL support=3`。
- **#3 stale**：node `stale`/`stale_reason`（llm_only grounding + 無 heat + verification llm_only 且 age>45d）；computed 非 persist（enrich stateless）。FMP-off 刻意不算 stale（區分 budget vs 真 stale）。
- **#6 relative heat**：`_heat_relative()` 改 chain 內 33/67 百分位 + 絕對 floor 8（防低活躍 chain 造 hot）；<4 active node fallback 絕對 `_heat`。relation 門檻刻意維持絕對（相對會讓 edge 信心取決無關 node、破壞可重現 + golden test）。
- **#4 ADR**：foreign node name-match 命中 US 交易所 symbol → 升 `adr_ticker` → investability 從 opaque FOREIGN 變可交易 proxy。
- **#9 測試**：7 新 golden test，全檔 **18 pass**。既有 11 test 全綠（conflict penalty 只打 corroborated、新增 `direction` key 不動既有 assert）。
- **驗收**：`pytest tests/test_supply_chain_enrichment.py` 18 pass；be chain enrich serve 路徑新欄位齊全無 regression；export CLI 實跑 OK（artifact 已清，未留 git tree）。
- **Wave B 待辦**：#5 FMP budget tiering、#7 UI edge 下鑽 `relation_evidence.sources`、#8 node override 編輯。三項跨 server/JS，未動。

## 🟢 Session Note (v4.43.6) — Decision Review 優化：agent_score_stdev + accumulating_data stall 規則
- **起因**：依本週 LLM 檢討報告（REVIEW_2026-06-20）提優化。核心：保守決策 miss 率 ~3× 進取（59% vs 20%）、半導體佔 51% miss，根因疑在 0–1 分數帶 default HOLD 過保守；但缺 `agent_score_stdev` 無法分離「弱訊號」vs「agent 高分歧」，所有修正卡在此 instrumentation。
- **#1（已落地）**：`deep_dive_extractor.py` tuning_hooks 加 `agent_score_stdev`（四 lane score pstdev）+ `agent_score_count`。解鎖 TODO-013。驗證：TSLA lanes [-3,1,-1,-2] → stdev 1.479 ✓；extractor 單元測試 25 passed（1 failing 為 pre-existing `_find_macro_delta`，與本次無關）。
- **#4**：TODO-007 → `promoted-to-ledger`，Rec 7 加 `standing_monitor`（gap 已穩 ≥15pp，轉常設 tripwire，<15pp 連 3 週才 paused，移出 TODO 佇列）。
- **#5**：REVIEW_PROMPT.md Step -1 加 `stalled` 狀態（accumulating_data 樣本連 3 輪不增長 → 以現 N 直接評或 drop）；TODO-003 → `stalled`（momentum N=24 凍結 4 週）。
- **#3（已重建）**：`scripts/diff_verdict_flips.py` 原從未 commit（報告誤稱已備）。重建完成：跨 13 snapshot N=194 / flip_rate **13.4%** 落 observe band（與 06-07 12% 一致）→ 不加 provisional，Pattern 統計維持只計 window_complete=100。下輪 `python3 scripts/diff_verdict_flips.py` 即可重跑。
- **下輪待辦**：① 下次 REVIEW 用 `agent_score_stdev` 拆 0–1 band 決定改 HOLD 閾值 or 高分歧降倉（#2）。② Pattern C / TODO-014 僅記錄不動手（N=4）。③ flip_rate 跌破 10% → close TODO-010；破 20% → build_event_index 加 provisional。
- **未動 code**：deep_dive_extractor + 新增 diff_verdict_flips.py + 3 個 decision_review 文件；無 protocol 決策邏輯改動。

## 🟢 Session Note (v4.43.5) — 供應鏈 Rerun：資料新鮮度、生成模型、增量更新
- **起因**：user 要知道供應鏈是哪天抓取/生成、由哪個 LLM 生成，並希望 rerun 參考前一版加上最新 source，而不是整份從零重抓。
- **UI**：`sc-meta` 改成 chips：Fresh/Aging/Stale（依 `generated_at` 0-2 / 3-7 / >7 天）、`LLM <generated_by>`、`完整生成/增量更新`、節點/層/模組/關係數。
- **資料**：`supply_chain.generate()` 新增 `refresh_mode`、`source_scope`、`previous_generated_at`、`previous_generated_by`；`SCHEMA.md` 同步。
- **Rerun 行為**：`/api/supply-chain/generate` 接 `rerun:true`；protocol worker 載入同 slug 既有 YAML，傳給 LLM 作 previous-chain baseline。prompt 要求保留仍有效結構，根據最新 local context / model 可用 public sources 增量更新，避免每次從零漂移。
- **CLI**：`scripts/nexus/supply_chain.py --theme <T> --rerun` 支援同邏輯。
- **限制**：`generated_at` 是鏈條草稿時間，不保證每條底層 source 同時刷新；目前 source scope 仍取決於 local context 與所選 LLM runtime 是否具 web/search 能力。
- **驗證**：`node --check Dashboard/page-supply-chain.js` rc=0；`python3 -m py_compile dashboard_server.py scripts/nexus/supply_chain.py` rc=0；`python3 -m pytest tests/test_supply_chain_enrichment.py` 11 passed。

## 🟢 Session Note (v4.43.4) — 供應鏈頁：主題 Rerun 重新抓取
- **起因**：user 要供應鏈探索的主題可 rerun，方便針對同一主題重新抓最新資訊。
- **做法**：`supply-chain.html` 控制列新增 `Rerun`；`page-supply-chain.js` 新增 `rerunCurrent()`，讀目前 chain 的 `theme`，沿用 `/api/supply-chain/generate` 佇列與 `watchGeneratedTheme()` 輪詢載入。
- **後端確認**：`supply_chain_generate` 不是硬寫死 Claude；未指定 agent 時走 `run_role("generate")`，由 `config/llm_config.json` 的 model router 目前設定決定。dedup 僅擋同 slug active/pending，不擋完成後 rerun。
- **驗證**：`node --check Dashboard/page-supply-chain.js` rc=0；`python3 -m py_compile dashboard_server.py scripts/nexus/supply_chain.py` rc=0；`python3 -m pytest tests/test_supply_chain_enrichment.py` 11 passed。

## 🟢 Session Note (v4.43.3) — 供應鏈探索：材料型產業 prompt 稽核強化
- **起因**：MLCC 供應鏈討論中，原探索容易把焦點縮到單一報告或 finished maker，漏掉整條材料/製程/規格分層鏈。
- **做法**：`supply_chain_system.md` 新增 materials/process-heavy themes 規則，要求拆 upstream materials、additives/minerals、process equipment、product tiers、downstream demand cycles、substitutes/package-level alternatives。
- **MLCC 特化紀律**：要求區分高容值/高壓/低 ESL/車規/AI server MLCC vs commodity 0402/0603 消費料；cost driver 不再粗糙套白銀，需區分 BaTiO3、鎳/base-metal electrode、銅/錫端電極、稀土/摻雜與燒結能源成本。
- **證據衛生**：因 YAML schema 暫無 evidence-grade 欄位，要求在 `note` 標 `confirmed` / `industry_report` / `inferred` / `stale` / `contested`。
- **最後審核**：新增 LLM self-review 清單，防止漏上游材料/設備/替代技術、過度泛化單一熱門規格、亂填 ticker/listing/stage、混淆客戶/部署/製造/終端市場。
- **驗證**：`python3 -m pytest tests/test_supply_chain_enrichment.py` 11 passed。
