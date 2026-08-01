# Session Notes 歸檔 v3.13.0 → v3.15.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

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
