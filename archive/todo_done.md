# TODO — 已完成任務歸檔

> 從 `TODO.md` 搬出的已完成區塊（完成逾 30 天）。依 `docs/agent-ops/MAINTENANCE.md` §3 輪替門檻。
> **權威的版本沿革請查 `CHANGELOG.md`**；本檔只是 TODO 當時的紀錄原文，不維護、不更新。
> 首批搬移：2026-08-10（v4.124.0 期間的 TODO triage），涵蓋 v4.64.0 及更早 + 舊「已完成任務詳情」。

---

## ✅ Done (v4.64.0) — Agent 治理層（CLAUDE.md 瘦身 + docs/agent-ops/）

- CLAUDE.md 178→74 行純路由；父層指標化；`docs/agent-ops/` 8 檔（診斷/指令總表/模型調度/判斷 rubric/派工模板/維護協議/教訓/交接信）；v4_8 歸檔+引用清零；MARKET_INDEX 補齊 24 skills；AGENTS/GEMINI 去重。對抗審查 13 findings 全修。
- ✅ SESSION_NOTES 歸檔完成（v4.64.1）：保留最近 10 個 Session Note，236 個搬 `archive/session_notes_archive.md`（4754→~100 行）。
- ✅ CLAUDE拷貝.md 已由使用者刪除（2026-07-03）。
- ✅ daily health 摘要完成（v4.65.0）：`scripts/daily_health.py` + daily_update.sh 收尾自動印表。
- ✅ 報告決策數字 script 注入完成（v4.66.0）：`inject_report_facts.py` + protocol Step 4.5，6 區塊佔位符制，33-assert golden fixture。**⏳ 待實戰**：下次跑 `分析 [TICKER]` 驗證一輪佔位符流程。
- ✅ 2+1 評審制接線完成（v4.67.0）：Red Team + Arbiter 降級補償寫入兩 protocol 本文，schema 零改動。**⏳ 待實測**：首次在無高階檔環境跑 protocol 時盯 referee 是否守三問制。
- **⏳ Backlog（詳見 docs/agent-ops/LETTER.md 交接表）**：llm_review 300KB 索引預切段（script 先切段統計、模型只看摘要層）。

---

## ✅ Done (v4.62.0) — 量化策略回測頁（quant-backtest）

- **`skills/quant-backtest/`** — 0-LLM 回測引擎（momentum 計分規則 5-10y 重放 + ma_cross）+ 29-assert golden fixture + SKILL.md；`backtest.html` 新頁（tiles/權益/進出場/回撤/分數/Sharpe 熱力圖/逐年/交易）；server `quant_backtest` SCRIPT_PROTOCOLS + `GET /api/backtest/{list,result}`。探索層，不入委員會決策。
- **⏳ 待 user**：重啟 dashboard_server 生效後實機開 `/backtest.html` 看渲染。
- **⏳ V2 候選**：多 ticker 組合、walk-forward 分段、自家訊號源（journal/thematic recommendations）接入回測、股息調整報酬。

---

## ✅ Done (v4.54.1) — 修逆勢假反轉(MU) + 訊號流收合

- **`apply_trend_context(rv, tr)`** — 反轉撞嚴格反向均線排列 → `counter_trend`/`alert=False`/「逆勢反彈·回測」;`build()` 套用,前端不當頭條。修 MU 空頭排列急跌卻爆「反轉向上」。
- **`_collapse_flow()`** — 訊號流連續同向收一筆(spike 保留 ⚡),`max_events` 4→3,不再連三次。
- **+4 case**(逆勢降級/同向保留/無趨勢保留/flow 收合)。
- **⏳ 已知取捨**：counter_trend 僅嚴格對向排列觸發;tr=None 時逆勢反轉仍報。

---

## ✅ Done (v4.54.0) — 個股急拉/急殺：加「順勢續攻/續跌」趨勢延續 STATE 偵測器

- **`detect_trend()`**（intraday_spikes.py，0 LLM）— 狀態型偵測,補 spike(暴衝)/reversal(剛交叉) 抓不到的「均線多頭排列順勢創高」。多頭 = 嚴格 ma5>ma10>ma20 + 收≥ma5 + ma5 上揚 + KDJ K>D & K≥50 + 貼近 20 根窗高;空頭鏡像。payload 1.3→1.4,reading 掛 `trend` + top-level `trends[]`。前端狀態行優先序 反轉>趨勢>尚無訊號,趨勢卡左緣色條。+5 case/+19 asserts。Live：12 檔全無訊號 → 6 檔跳順勢訊號。
- **⏳ 可調**：render 把非 alert 小反轉排在 strong 趨勢前,若要 strong 趨勢優先可調;`TREND_K_MIN`/`TREND_HIGH_WINDOW`/`TREND_HIGH_TOL` tuning。

---

## ✅ Done (v4.51.0) — 急拉/急殺加 MACD/KDJ/量 確認層

- **`detect_spikes()`** 重用 `intraday.compute_macd`/`compute_kdj` → confirmations + confirmed(價 + ≥2)；fetch 40→90 分；chip 加 ✓badge + ★。24 asserts。
- **⏳ 資金流向/特大單（待 user 選）**：(a) Futu OpenAPI/OpenD（確切特大單，免費 user Futu 帳號，需裝 futu-api + 跑 OpenD）/ (b) Alpaca SIP $99 tick 自分類 / (c) 免費 bar 近似（OBV/上下量比，只有方向）。

---

## ✅ Done (v4.50.0) — 個股急拉/急殺快線（Alpaca 1 分鐘，獨立 lane）

- **`intraday_spikes.py`**（0 LLM）— Alpaca 1min REST 多檔一次抓 + `detect_spikes()`：近 5 分鐘 `|1分|≥1%` / `|3分|≥2%` → 急拉/急殺，severity + 量增 3× 次要確認。`config/spike_watchlist.txt` 可手編。
- **接線**：`intraday_spikes_poll_loop`（60s，盤中）+ GET `/api/intraday-spikes/data` + intraday 頁頂部區塊。無 Alpaca key graceful no-op。`test_intraday_spikes.py` 18 asserts。
- **⏳ 待 user**：alpaca.markets 免費註冊 → 設 `ALPACA_API_KEY`/`ALPACA_SECRET_KEY`。`ALPACA_FEED=sip`（$99/mo）才有準確量；免費 IEX 量低估，偵測以價格為主。

---

## ✅ Done (v4.49.x) — 盤中評估：MACD/KDJ 動能層 + 即時 quote + 修側欄

- v4.49.1 修 `intraday-mood.html` 漏 `UI.boot('intraday')` → 左側欄不 render（已修）。
## ✅ Done (v4.49.0) — 盤中評估：MACD/KDJ 動能確認層

- **`intraday.py`** pure-python `compute_macd`/`compute_kdj`（末根交叉 + bar 數守門）→ 日線(regime)+5min(時機) 雙框。
- **旗標（只確認層、不動分數）**：下殺=盤中 KDJ 高檔死叉 / MACD 死叉+跌破VWAP；反轉=盤中 KDJ 低檔金叉 / 日線 MACD 柱轉升；macd_daily=日線金叉死叉。confluence-gated 擋 5min whipsaw。
- 每檔 `momentum` 數值透出；卡片加 MACD/KDJ 讀數+交叉箭頭。`MACD_*`/`KDJ_*`/`KDJ_OB`/`KDJ_OS` 檔頭可調。`test_intraday.py` 47 asserts。

---

## ✅ Done (v4.48.1) — 盤中評估：即時 quote 混合

- **`intraday.py`** `assess(live=)` + `_fetch_live_quote`：FMP `quote` 覆蓋 spot/當日高低/量/昨收（~2s 新），破底/止跌秒級化；5-min K 仍管 VWAP+型態。每檔 `data_source`+`quote_timestamp`，頁面 pill「· 即時報價」。`test_intraday.py` 34 asserts。
- **1min 不可用**（stable 回 None）→ 型態最細 5-min。

### ⏳ 盤中評估候選增強（user 待決，Tier-1）
- 盤中 VIX context 分量（`quote ^VIX`）、類股輪動快照（`sector-performance-snapshot`）、HYG 信用佐證（同 assess 跑 HYG）、時段化 RVOL 曲線（修早盤線性外推噪音）。皆走既有 quote/5min 端點。

---

## ✅ Done (v4.48.0) — 盤中評估引擎（Intraday weakness tape）

- **`intraday.py`**（0 LLM）— FMP 5-min bars + ~60 日 daily → SPY/QQQ/IWM signed −100..+100 盤中評估。破底(5/20/50d)/止跌/高開低走/量增價跌(RVOL)/VWAP/MA20/連跌/出貨日。`UNIVERSE`/`WEIGHTS`/門檻 = 檔頭常數可調。
- **接線**：dashboard_server `intraday_mood_poll_loop`（盤中 300s + 開機 + 收盤快照）+ GET `/api/intraday-mood/{data,state}` + POST `/refresh`；`intraday-mood.html` 獨立面板；utils.js nav；index.html mini-strip；daily_update Step 9.35；`test_intraday.py` 26 asserts。
- **踩雷**：stable daily 端點 = `historical-price-eod/full`（`historical-price-full` 回 None）。
- **可調項（user 探索期）**：universe 增減（如加 ^VIX 盤中）、poll 間隔、score 取向（目前 負=破底）、各 WEIGHTS/門檻。
- **紀律**：探索層，**不**入 investment_protocol。

---

## ✅ Done (v4.47.2) — weekly-tech-playbook：Codex Review 整合優化

- **P1 解耦（關鍵）**：`render.py` `codex_review` 改可選——缺它 rc=0 仍生成（原 fatal、依賴反轉破壞可重跑）。
- **P2 去自打臉**：非 blind review 不再 by-default degraded；只在宣稱 blind 時要求 `blind_artifact`。
- **P4 公平性**：`review.py` Codex sleeve 標 `deployed_pct`/`cash_pct`（部署 75%），alpha 非同 beta 比較已標示。
- **SKILL.md** Step 2.5「必填」→「可選」對齊 code。
- **保留 Codex 好設計**：committee-blind pack（反 anchoring）、現金當 sleeve、降權抛物線股、檢討加 QQQ/SOXX+回撤。
- **待 user 決定**：P3 `codex_review` 欄位泛化為 `independent_review`+`reviewer` meta；P5 render 職責拆分；P6 codex 標的若不在三籃內無進場價。

---

## ✅ Done (v4.47.1) — weekly-tech-playbook：下週 LLM 檢討機制

- **`scripts/review.py`**（0 LLM）— 過去某週方案 vs 檢討日收盤:每檔報酬、每籃 vs SPY alpha、命中率、kill 觸發偵測、三籃排名 → `reports/<REVIEW>_TECH_PLAYBOOK_REVIEW.md`（含空白「🧠 LLM 檢討」段）+ `Dashboard/playbook_review.json`。觸發詞「投資方案檢討」。
- **`render.py`** 加寫 immutable dated snapshot `data/playbook_<DATE>.json`（進場錨點,可回放）。
- **`page-playbook.js`** 頂「上週方案檢討」橫幅（讀 playbook_review.json,僅 entry≠review 日顯示）。
- **兩段式**:review.py 算硬數據(0 LLM,永不自動覆寫) → Claude turn 讀填質性判讀 → 改下週 selections。
- **用法**:下週同日 `python3 skills/weekly-tech-playbook/scripts/review.py --date 2026-06-22 --asof <下週日>`。

---

## ✅ Done (v4.47.0) — weekly-tech-playbook：三籃子 $100k 科技投資方案 + Dashboard 頁

- **新 skill `skills/weekly-tech-playbook/`** — build_pack（0 LLM 組 regime+熱題+委員會 verdict+報價）→ LLM 選股 selections JSON → render（0 LLM 算股數/驗證每籃=$100k，rc 0/1/2）→ `Dashboard/playbook.json` + `reports/<DATE>_TECH_PLAYBOOK.md`。
- **三籃子設計** — 保險/激進/混合各 $100k，信心分級（核心 $15k×3 / 標準 $10k×4 / 輕倉 $5k×3）；混合 = 65% 保險 sleeve + 35% 激進 sleeve。
- **Dashboard** — 新增 `/playbook.html` + `page-playbook.js`，sidebar「投資方案」（portfolio group），三籃可切換 + 檢討 scaffold。
- **本週首版** selections_2026-06-22.json 已產，render rc=0。
- **待 user**：重啟 dashboard_server 開 `/playbook.html`；下週同日跑檢討；考慮 `/schedule` 每週一自動 build_pack+render。
- **後續可選**：build_pack 委員會 scraper 會抓「最近 14d 內」報告，可能含較舊/不同價基的 FV（如 AMD 6/14 FV $142）→ 之後可加 freshness 標記或只取 ≤7d；render 可加 `--refresh-prices` 重抓 yfinance。

---

## ✅ Done (v4.45.0) — 供應鏈 Wave B：UI 下鑽 + budget tiering + node 校正

- **#7 UI 下鑽** — edge `direction` chip（衝突/確認）+ node `stale`/`user_status` 視覺標記進 card+detail（Wave A 訊號終於可見）。
- **#5 FMP budget tiering** — priority(spine/ticker/≥2 downstream) 先驗；headroom<0.5 週邊只服務 cache + 跳 name-search；profile TTL 7d→30d。
- **#8 node override** — `overrides/<slug>.json` sidecar（不改 LLM YAML）+ `POST /api/supply-chain/<slug>/override` + detail panel ✓確認/⚑標記/清除 button。enrich merge 修正欄位優先。
- **#9 測試** — 5 新 test，全檔 23 pass。
- **供應鏈 8 gap 全收口（Wave A+B）**。後續可選：override field-edit 表單 UI（現 field 修正僅 API）；relation source clickable 連回新聞流。
- **待 user**：重啟 dashboard_server → 開 `/supply-chain.html`，點 node 試「✓確認/⚑標記」確認框線變化與 detail；觀察 edge `方向衝突/確認` chip 是否在有 Nexus 有向邊的 pair 出現。

---

## ✅ Done (v4.44.0) — 供應鏈 Wave A：方向校驗 + 回寫閉環 + stale/relative-heat/ADR

- **#1 edge 方向校驗** — `_direction_check()`：co-mention 對稱只證相關非方向，改用 Nexus directed edge 校驗 LLM 箭頭；corroborated 但方向矛盾 → weight 0.5 + `relation_evidence.direction`。
- **#2 corroborated 回寫閉環** — `export_corroborated_edges()` + CLI `--export-edges`：digest-corroborated 方向乾淨 edge → `bn_*.json` 餵 Nexus tier-1。opt-in，不在 enrich serve 路徑；source 標 `supply_chain` 防增強迴圈。
- **#3 stale flag** — node `stale`/`stale_reason`（age>45d 且無 live 訊號）；`data_quality.stale_node_count`/`chain_age_days`。FMP-off 不算 stale。
- **#6 relative heat** — heat 改 chain 內 33/67 百分位 + 絕對 floor 8；<4 active node fallback 絕對。
- **#4 foreign ADR 補全** — foreign node name-match 命中 US 交易所 → 升 `adr_ticker` → 可交易 proxy。
- **#9 測試** — 7 新 golden test，`tests/test_supply_chain_enrichment.py` 全檔 18 pass。
- **Wave B 待辦**（下次）：#5 FMP budget tiering（spine/investable 先驗、週邊 lazy）、#7 UI edge 下鑽到 `relation_evidence.sources`、#8 node override（標錯/確認 → override file → enrich merge）。
- **待 user**：可選跑 `python3 scripts/nexus/supply_chain.py --export-edges --export-graph-refresh` 把現有 chain 的 corroborated edge 灌回 KG；開 `/supply-chain.html` 確認 heat 分級與既有頁面無 regression。

---

## ✅ Done (v4.43.5) — 供應鏈 freshness + incremental rerun metadata

- 供應鏈頁右側 meta 顯示 Fresh/Aging/Stale、生成 LLM、完整/增量模式與生成時間 tooltip。
- Rerun 會把前一版 YAML 傳給 LLM 作 baseline，要求保留有效結構並以最新 local context / 可用 public sources 增量更新。
- YAML metadata 新增 `refresh_mode/source_scope/previous_generated_at/previous_generated_by`；CLI 支援 `--rerun`。
- **待 user**：重啟/刷新 `/supply-chain.html` 後，選既有主題確認右上 freshness badge；按 `Rerun` 後新版應顯示 `增量更新` 與當日生成時間。

---

## ✅ Done (v4.43.4) — 供應鏈頁主題 Rerun

- 供應鏈頁選定既有主題後可按 `Rerun`，用同一 theme 重新排入 `supply_chain_generate`，完成後覆寫同 slug YAML 並自動輪詢載入新版。
- Generate / Rerun 共用 queue helper；未選 chain 時 Rerun disabled。
- **待 user**：重啟 dashboard_server 後開 `/supply-chain.html`，選 MLCC 或既有主題按 `Rerun`，右下角 protocol pill 應顯示進度，完成後圖譜刷新。

---

## ✅ Done (v4.43.3) — 供應鏈探索：材料型產業 prompt 稽核強化

- 供應鏈生成 prompt 對 MLCC/電池/基板/光學/化學品等材料/製程型主題新增完整拆鏈要求：上游材料、受限添加物/礦物、製程設備、產品等級、下游需求週期、替代技術。
- MLCC 類主題新增規格分層與成本驅動紀律，避免把 AI server 高階料缺貨外推到全 MLCC，或把現代 MLCC 成本粗糙連到白銀。
- evidence 暫以 `note` 標 `confirmed` / `industry_report` / `inferred` / `stale` / `contested`；未改 YAML schema。
- **待 user**：重新用 supply-chain generator 產一條 `MLCC` 鏈，檢查是否展開材料/設備/替代技術與規格分層；若效果仍不夠，再升級成獨立 reviewer/validator pass。

---

## ✅ Done (v4.43.1) — 供應鏈外股常見公司 backfill

- 舊 YAML 只有 `foreign_listed` 時，常見外股供應鏈公司自動補 `TW/KR/JP/EU + local_ticker + ADR` 顯示；人工欄位不覆蓋。
- **待 user**：重啟 dashboard_server 後重新開 `/supply-chain.html`，常見 TSMC/Samsung/Tokyo Electron 等應不再顯示 `FOREIGN`。

---

## ✅ Done (v4.43.0) — 供應鏈頁外股標示 + 上下游投資摘要

- 台股/韓股/日股等非美上市節點新增 `market/local_ticker/adr_ticker/investability`，Dashboard 卡片不再把外股誤顯為未上市。
- 供應鏈頁新增 deterministic「上下游投資摘要」：可投資標的、瓶頸/槓桿節點、私有公司 proxy、高信心關係。
- **待 user**：重啟 dashboard_server 後打開 `/supply-chain.html` 實看既有鏈條；舊 YAML 若要完整顯示台/韓/日代號，可逐步補 `market/local_ticker/adr_ticker`。

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
- **待 user**：跑幾天後覆核 `_state.json` 的 `items_echo_merged`/`items_sentiment_clustered` 與每日 call 數，視情況調 `BREAK_NEWS_CLUSTER_SIM`（0.55）/ `BREAK_NEWS_SENTIMENT_MIN_SCORE`（3）。（原 ②「codex CLI 壞掉」已失效：codex 現為 `protocol_providers` 白名單成員，v4.117.0 實跑 rc=0。）

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
  - `/stable/rating-historical` + `/stable/grades-summary` 仍 404 — earnings bundle 的 rating_history/grades_summary 長期全零。（econ-calendar 本身已於 v4.111.5 修復並實測 477 筆。）
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
- Follow-ups:(b) link_digest 不 patch
  sector_intel/phase0（探索層）;(c) 早於 morning news DIGEST 寫 bn 時，news run 會覆寫 digest.json（KG 不受影響）;
  (d) judgment.json `<id>` 由 LLM 命名，build_artifacts 不強制檢查 id 一致性（容錯）;(e) 可考慮 link_digest
  也吐到 trader-memory thesis registry / decisions（目前只到新聞層）。

## ✅ Done (v3.34.0) — Narrative Pulse 完整退役

- 提前退役(週末無新 sample):刪 daily `step9_narrative()`、server `/api/narrative-pulse/*`
  + SCRIPT_PROTOCOLS、`Dashboard/narrative_pulse.json`、整個 `skills/narrative-pulse-detector/`。
- 副作用:mood.html 每產業「散戶量能」label 恆 `calm`(retail aggregate.py 的 legacy NPD
  fallback 缺 cache → graceful;主 composite 不受影響)。
- Follow-up 已升級為 **[RSP-0]**（見「路線 RSP」）：`load_npd_cache_for` 恆回 None 不只是死碼，
  它讓 mood.html「散戶量能」恆顯示 calm。

## ✅ Done (v3.33.0) — 退役 Narrative Pulse UI + 移除散戶視角 + index 產業趨勢 mini

- index Zone B「Narrative 焦點」→ 真實「產業趨勢」mini(`renderIndustryMini`,讀
  `data.industry_trend`);移除 index 內 narrative fetch IIFE。
- radar 刪 `#npd-section` + page-radar.js NPD IIFE 死碼;刪散戶視角 `#radar-retail-sector-pulse`
  + page-radar.js retail 全套 + render 呼叫 + tooltip。mood.html 接手散戶,不受影響。
- 保留 narrative generator + server route + json(觀察期到 2026-05-31)→ **v3.34.0 已整套退役**。
- Follow-ups:(b) index 產業趨勢 mini 目前固定 perf_1w,可考慮跟 radar 一樣加區間 toggle。

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
  freshness badge — 若要每日新鮮可在 daily Step6 強制 refresh;(c) laggards
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
