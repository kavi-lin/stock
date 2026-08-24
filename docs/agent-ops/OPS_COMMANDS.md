# Ops 指令總表

> 從 CLAUDE.md 抽出的完整指令清單（2026-07-03）。CLAUDE.md 只留最常用兩條；其餘都在這裡。
> 按「什麼情境跑什麼」分組。指令本身是唯一真相；註解只說用途，不記版本史。

## 1. 例行

```bash
# 每日（3-5 min）：Breadth → FTD → Top → FRED → Bridge → Thematic → Watchlist → Nexus
./daily_update.sh

# 週末（1-2 min）：短期戰術層覆盤 → reports/SHORT_TERM_WEEKLY_<DATE>.md
python3 skills/short-term-target/scripts/weekly_review.py

# 資料源健康檢查（daily_update.sh 收尾自動跑；可隨時手動）：artifact 新鮮度抓 silent SOFT fail
python3 scripts/daily_health.py            # --strict 有 FAIL 時 rc=1；daily gate 加 --run-date YYYY-MM-DD

# SESSION_NOTES 批次輪替（dev session 收尾跑；≤20 個 note 時 no-op）
python3 scripts/rotate_session_notes.py    # >20 個 → 最舊 10 個切成 archive/session_notes_v<A>_to_v<B>.md
```

## 2. 單股 ad-hoc 查詢

```bash
python3 skills/short-term-target/scripts/predict.py <TICKER>          # 1d/5d/15d projection
python3 skills/finnhub-client/scripts/run_dual_fetch.sh --tickers X   # canonical scoring snapshot
python3 skills/_shared/company_context.py <TICKER> --peers            # 共用 profile/peers cache (24h TTL)
python3 skills/earnings-valuation-forecaster/scripts/forecast.py <T> --pre-earnings --output-dir reports/  # 財報前瞻 cheat sheet
python3 skills/quant-backtest/scripts/backtest.py <T> --template momentum --period 5y  # 量化回測（探索層）
python3 investment/scripts/forward_price_range.py <TICKER>            # future price range（shadow）
python3 skills/valuation-modeler/scripts/dcf.py <T> [--xlsx] [--set wacc=0.09]  # 自建 driver-based DCF（V4.69.0；--json-only = anchor 模式）
python3 skills/valuation-modeler/scripts/comps.py <T> [--xlsx]                  # 多指標同業比較（V4.69.0）
```

## 3. Investment protocol 周邊

```bash
python3 investment/scripts/compute_price_framework.py --from-file <inputs.json>  # Phase 2.4 價格框架引擎（0 LLM 算術；--self-assemble 自組輸入；--no-fetch 跳過 FMP vol）
python3 investment/scripts/decision_engine.py --from-file /tmp/<T>_p3.json       # Phase 3 決策引擎（0 LLM 算術；calculation_steps 整塊 verbatim 抄寫，V4.117.0 起 validator §5l 拿 invest_logs/decision_engine/<T>_decision_engine.json 對答案）
python3 investment/scripts/decision_engine.py --phase 4.6 --from-file /tmp/<T>_p46.json  # Phase 4.6 decision cap 套用（收 Phase 4 sizing 後）
python3 investment/scripts/replay_decision_engine.py                             # engine × history 全量 replay + 排除清單 → reports/decision_review/DECISION_ENGINE_REPLAY_<date>.md
python3 investment/scripts/inject_report_facts.py                                # Phase 5 Step 4.5：報告佔位符 → history.json verbatim 注入（0 LLM、idempotent）
python3 investment/scripts/append_session_export.py --from-file <SESSION.json> --stamp-only --stamped-out <SESSION.json>  # Phase 5 prepare：蓋 provenance，尚不寫 history
python3 investment/scripts/append_session_export.py --from-file <SESSION.json> --preserve-stamp  # Phase 5 commit：驗 digest + stable lock 後追加 history
python3 investment/scripts/register_thesis.py --session <SESSION.json>           # Phase 5.5 thesis register（idempotent、non-fatal）
python3 investment/scripts/audit_gate_compliance.py <scan_logs/....log>          # 判讀一次 invest run 對 V4.116.x/V4.117.0 五道閘的實際行為（唯讀）。只掃引擎執行的指令、不掃它讀到的檔案內容；Gate 3 需在該 run 剛跑完時看（artifact 是單槽快取）
python3 investment/scripts/websearch_shadow.py --log <scan_logs/....log>         # 記一次 run 的 lane web-search 用量（shadow，不扣分、不進決策）
python3 investment/scripts/websearch_shadow.py --backfill                        # 回填全部 invest log 重建 ledger（會先備份成 .bak）
python3 investment/scripts/websearch_shadow.py --report                          # 統計 ledger（web-search 額度拍板用；不可觀測的 run 不進分母）
python3 investment/scripts/backtest_postmortem.py                                # protocol 決策回測
python3 investment/scripts/shadow_report.py                                      # shadow 讀出端 → reports/SHADOW_REPORT_<date>.md（唯讀）
python3 investment/scripts/forward_expectations.py --ticker <T> --self-assemble  # 前瞻預期引擎（shadow；0 LLM）
python3 investment/scripts/forward_expectations.py --ticker <T> --self-assemble --acquire-documents  # + SEC filing 抽取（opt-in）
```

## 4. IC Memo

```bash
python3 skills/ic-memo-writer/scripts/build_fact_pack.py <T>                             # fact_pack 聚合 + decision_lock hash
python3 skills/ic-memo-writer/scripts/compose.py <T>                                     # MD render（deterministic，0 LLM）
python3 skills/ic-memo-writer/scripts/validate_ic_memo.py reports/<DATE>_<T>_ic_memo.md  # validator（rc=0 pass / 1 fatal / 2 degraded）

# 首次覆蓋 Initiating Coverage（V4.69.0；前置 = history entry + valuation-modeler payload cache）
python3 skills/ic-memo-writer/scripts/build_fact_pack.py <T> --initiation                # 缺 vm cache → rc=4 + 印補跑指令
python3 skills/ic-memo-writer/scripts/compose_initiation.py <T>                          # → reports/<DATE>_<T>_initiation.md
python3 skills/ic-memo-writer/scripts/validate_ic_memo.py reports/<DATE>_<T>_initiation.md --initiation
```

## 5. Sector / News / Nexus / Link Digest

```bash
python3 sector/scripts/sector_digest.py                          # 1-call macro + 11-sector 決策表（唯讀）
python3 sector/scripts/build_sector_intel.py --date YYYY-MM-DD   # 從 caches 組 sector_intel.json（順帶落盤 shadow）
python3 sector/scripts/da_pretrigger.py --date YYYY-MM-DD --hot "A,B" --prompt-only
                                                                 # Phase 4b R4-R7 預判 → 逐字 paste 進 DA prompt
python3 sector/scripts/fred_lane_gate.py --date YYYY-MM-DD --hot "A,B" --write
                                                                 # FRED lane 觸發 gate（shadow-only，累積樣本）
python3 sector/scripts/sector_score_calculator.py --status        # Phase 4c 割接進度（SE2 前置判準）
python3 sector/scripts/sector_score_calculator.py --audit-decisions
                                                                 # 重放歷史 decision 檔（唯讀，不產 shadow 樣本）
python3 scripts/nexus/build_graph.py --tier 1,2 --dry-run        # Nexus 圖譜 dry-run（無 LLM）
python3 scripts/nexus/build_graph.py --tier 1,2,3 --full         # 全量重建（Tier 3 需 ANTHROPIC_API_KEY）
python3 -m scripts.nexus.claim_ledger --check                    # relation source 去重／晉升閘 validator
python3 -m scripts.nexus.topic_discovery --check                 # 主動 topic queue／chain candidate validator
python3 -m scripts.nexus.source_packets --check                  # source/excerpt ID、hash、逐關係證據 validator
python3 -m scripts.nexus.source_packets --fetch-topic topic:...  # 只抓指定 topic；零 LLM
python3 scripts/link_digest/build_artifacts.py <judgment.json>   # Link Digest fan-out（rc 0/1/2）
python3 news/scripts/news_event_store.py pending                 # 列出待審 event_id
python3 news/scripts/news_event_store.py project --date YYYY-MM-DD
python3 news/scripts/news_event_store.py migrate --all           # legacy digest → JSONL；自動留 backup
python3 news/scripts/news_event_store.py rollback --date YYYY-MM-DD
python3 news/scripts/news_event_store.py telemetry --limit 10    # 滿 10 場後才調 materiality
python3 scripts/wind/terms.py --dry-run                          # 風向 關鍵字熱度表（唯讀，不寫檔）
python3 scripts/wind/dispatch.py --dry-run                       # 會掃哪個 term + 預估花費，不呼叫引擎
python3 scripts/wind/dispatch.py --once                          # 跑一次派工（消耗額度）
python3 scripts/wind/dispatch.py --interval 3600                 # 常駐每小時一輪（Ctrl-C 停）
python3 scripts/wind/budget.py --status                          # 掃描花費 / 今日剩餘次數
```

**常駐由 `open_dashboard.sh` 帶起**（V4.131.7 起）：它在開瀏覽器之後 `python3 -u --interval 3600` 起一隻背景 daemon，log 落 `/tmp/wind_dispatch.log`，Ctrl+C 跟 server 一起收。`-u` 不可省 —— stdout 導到檔案是 block buffering，沒有它 log 會空好幾個小時。

**怎麼知道它在跑 / 下一輪何時**（V4.131.8 起）：風向頁標題列直接顯示「掃描中 / 下一輪 HH:MM (mm:ss) / 上一輪結果」，30s 自動重取。底層是心跳檔 `news/wind_logs/wind_daemon.json`（`state` / `next_tick_at` / `tick_count` / `last_detail`…），只有常駐迴圈會寫，`--once` 與頁面按鈕不寫。`/api/wind/terms` 的 `daemon` 欄位會驗 PID 是否還是 dispatcher（PID 會回收），並在沒有心跳檔時 `pgrep` 補一刀 —— 沒心跳不等於沒 daemon。**沒有通知**，這是使用者選的。上面那條手打指令只在「dashboard 沒開但想掃」時用 —— 兩邊同時跑會各自吃每日次數，所以 script 內建 `pgrep` 防重複。單次不想跑：`WIND_DISPATCH=0 ./open_dashboard.sh`。注意 daemon **啟動即跑第一輪**，開 dashboard 等於花一次額度。

**風向紀律**：探索層。產出只落 `news/wind_logs/`，不進任何評分、不寫 Nexus、不碰 `Dashboard/market_mood.json` 的 atmosphere indicators。領先性**尚未驗證**，判準已預先寫死於 `docs/wind_evaluation_criteria.md`（`TODO.md:440` 要求「看資料前先寫死」），不及格就砍掉派工器。`分析 [TICKER]` 的人工晉升閘不受影響 —— 派工器自動跑的只有唯讀社群掃描。

**前置**：reasoning **不再需要** `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`。`scripts/wind/reasoning_adapter.py` 先向 quota broker 取得一個 lease，由 broker 在 Claude / Agy / Codex 的既有登入訂閱中選當下可用者；planner、rerank、fun judge 三段整輪固定走該 CLI。broker 不可達／拒絕、CLI 未登入或回傳非 JSON 時整輪 fail-closed，term 回 pending，不會退化成 `local-score`。資料擷取來源自己的憑證（例如 ScrapeCreators、X）仍照舊需要。查實跑產物的 `engine.reasoning`：應有 `route: broker:*`、`calls`、`usage`、`reasoning_api_keys: disabled`。`grounding` 目前恆為 `unreachable`（web 層刻意不補，見 `TODO.md` 風向節），無害。

**環境相依（全 repo 通用）**：`python3` 必須 import 得到 `requests` / `pandas` / `numpy` / `yfinance` / `yaml` / `lxml` / `bs4` / `openpyxl` / `anthropic`。這些裝在**該直譯器的 user-site**，不是系統層——2026-08-16 Homebrew 把預設 `python3` 換成 3.14（user-site 全空），整條 pipeline 在 import 層靜默斷了兩天。健檢：`python3 -c "import requests, pandas, yfinance"`。**每次 `brew upgrade python` 後都要重跑一次這個檢查**。

## 6. Break News 手動

```bash
python3 scripts/break_news/poller.py --once             # 單次 poll
python3 scripts/break_news/cluster.py --feed            # 24h 事件 cluster 熱度表
python3 scripts/break_news/market_brief.py --force      # 強制重產市場導讀（1 LLM call）
python3 scripts/break_news/debater.py --news-id <id>    # 單條 debate
python3 scripts/break_news/validate.py                  # schema lint（含 clusters/brief）
python3 scripts/_shared/model_router.py --status        # 多模型預算/cooldown 現況
```

## 7. 回歸測試 — 改了哪個引擎就跑哪組（rc=0 才算完成）

| 你改了什麼 | 必跑 |
|---|---|
| Nexus claim ledger / topic discovery / evidence drafts / graph projection / Radar UI | `python3 -m pytest -q tests/test_nexus_claim_ledger.py tests/test_nexus_topic_discovery.py tests/test_nexus_evidence_drafts.py tests/test_nexus_frontend_contract.py tests/test_break_news_v4.py tests/test_supply_chain_enrichment.py` + `node --check Dashboard/page-graph.js` + `python3 scripts/nexus/build_graph.py --tier 1,2 --dry-run` + claim/topic/draft 三支 `python3 -m scripts.nexus.<module> --check` validator（全部 rc=0）。source_count 必須按 canonical URL；draft node 只能來自 source topic，且永遠 decision-ineligible。|
| Nexus source packet / bounded gap-fill runner / proposal ledger | `python3 -m pytest -q tests/test_nexus_source_packets.py tests/test_nexus_gap_fill.py` + `python3 tests/test_broker_gate.py` + source packet / gap-fill 兩支 `python3 -m scripts.nexus.<module> --check` + `node --check Dashboard/page-graph.js`。測試必證明：source/excerpt hash 與 ownership 錯會紅、每項需 fetched-page text、外加 URL 會紅、一 topic 最多一個 spent turn、blocked turns=0 可再選、base + packet digest drift 會紅、proposal 不得改 immutable edge；Claude profile 必為 Sonnet / max-turns 1 / no-tools / strict-MCP，且仍走 governed chain、不 fallback。|
| `compute_price_framework.py` / valuation projection validator | `python3 investment/scripts/test_compute_price_framework.py` + `python3 investment/scripts/test_valuation_pack_consistency.py`（兩者 rc=0；後者含故意 drift 的 rc=1 fixture）。前者含 V4.88.0 staged regression：`--stage quant` + `--stage mhp` 合併輸出必須與單發模式逐位元一致（只豁免 `valuation_pack.built_at`），改到分段/合併路徑必紅。另含 V4.116.0 `script_not_run` 判別（`mark_unrun_anchor_scripts`）：artifact 缺／過期 → `script_not_run`，artifact 新鮮 → 維持原 reason，anchor 有值 → 完全不碰 |
| `validate_session_export.py` 的 `valuation_reviewer_gate` / technical rubric 兩道閘、`technical-analyst/analyze.py` 的 payload cache | `python3 investment/scripts/test_validate_session_export_gates.py`（rc=0）。走**真 validator subprocess** + schema doc 的 FULL EXAMPLE fixture。**cutoff 日期在測試裡寫死、不讀被測常數**——第一版讀了，於是把 cutoff 推到 2099 時測試照樣全綠（同源對照，MAINTENANCE §2c）|
| `apply_det_shadow.py` 的 `compute_polarization` / `classify_red_team_basis`（4-tier polarization + RT basis） | `python3 investment/scripts/validate_v219.py`（rc=0，10 polarization + 6 basis fixtures）。**改到這兩支的分類邏輯必跑**——它們餵 §13 的 polarization 重算與 cascade rule 1/3。它 import 真 producer 不複製邏輯，所以是有效對照。（V4.128.0 補列：這支自 2026-05-10 起就沒進過本表，改 polarization 的人不會知道要跑它。）|
| `us-stock-analysis/analyze.py` 的 Fundamentals payload 落地 | `python3 skills/us-stock-analysis/scripts/test_bundle_merge.py`（rc=0）。含**接線斷言**（落地段從 `main()` 拿掉要會紅）與**形狀斷言**（最新 payload 六個 rubric 區塊齊全）。V4.128.0 起 Fundamentals lane 的計分 scalar 才變成 validator 構得到的物證，同 Technical V4.116.3 |
| `backtest_postmortem.py` 的報告解析 | `python3 investment/scripts/backtest_postmortem.py --reports-dir <小目錄>`（rc=0）。**看 stderr 有沒有「份報告有欄位解析不出來」那行**——V4.87.0 換 renderer 後舊 regex 靜默漏了 33/145 份 decision、126/145 份 action，工具照樣 rc=0。改 `render_investment_report.py` 的決議摘要表就要回頭看這支 |
| `websearch_shadow.py`（Phase 2 lane 的 web search shadow ledger） | `python3 investment/scripts/test_websearch_shadow.py`（rc=0）。**最重要的案例走真實 log**（`invest_20260418_141121.log`，Agent×6 + WebSearch×6 + WebFetch×2）——合成 fixture 只證明「照我寫的邏輯跑得通」，證明不了對得上真實世界。合約鎖三件事：偵測器在已知有 web search 的 log 上必須報非零、歸屬必須走 `parent_tool_use_id`（拆掉要塌成 unattributed 而不是靜靜換一個 lane）、codex 這種不上報 web 工具的 log 一律 `observable: false` 而非 `web_calls: 0` |
| `validate_phase0.py` 的 resolver / 新鮮度閘 | `python3 investment/scripts/test_validate_phase0.py`（rc=0）。鎖住「Phase 0 是全市場共用、GEV 可讀 AAOI-era legacy snapshot、canonical 同 mtime 優先」、「`scan_date` 過舊／未來 → rc=1」與「內容與**較舊**快照除 `scan_date` 外相同 → rc=1」。**週末案例是刻意留的**：週六與週日都讀週五收盤，快照可以合法相同，所以雙胞胎必須比新鮮度窗口更舊才算證據 |
| `fwd_earnings_discounted` 的四個 clamp 常數（`FWD_PE_CLAMP` / `FWD_DISCOUNT_CLAMP` / `FWD_MIN_ANALYSTS` / `FWD_MAX_HORIZON_YEARS`）| `python3 investment/scripts/test_compute_price_framework.py` + `python3 investment/scripts/test_shadow_report.py`（兩者 rc=0）。**改 clamp 值之前先跑 `python3 investment/scripts/shadow_report.py` 看校準區塊**：判準是 live cohort 的市場隱含 PE P33–P66 有沒有包住現行上限。live cohort 不足 `FWD_PE_CALIB_MIN_N` 時判準會回 `accumulating`——那是「還不知道」，不是「沒問題」。**不可自動跟隨中位數**（泡沫期會讓上限一路上移），改值一律 user 核准 |
| `valuation_reviewer_gate.py` / `peer_cohorts.py` 的 discovery cache | `python3 investment/scripts/test_valuation_reviewer_gate.py`（rc=0）+ `python3 skills/valuation-modeler/tests/test_comps.py`。鎖住「5 條 trigger 各自獨立命中、`transition_case_active` 是唯一 mandatory、TTL 30d 邊界、discovered 永不覆寫人工核准的 `config/peer_cohorts.json`、artifact 不可用 rc=1」 |
| earnings valuation forecaster | `python3 skills/earnings-valuation-forecaster/tests/test_forecaster_v3_17.py` |
| `forward_expectations.py` 核心 | `python3 investment/scripts/test_forward_expectations.py`（rc=0 為準） |
| `inject_report_facts.py` | `python3 investment/scripts/test_inject_report_facts.py` |
| `decision_engine.py` / Phase 3 決策數學 / `validate_session_export.py` §13 | `python3 investment/scripts/test_decision_engine.py` + `python3 investment/scripts/validate_session_export.py`（兩者 rc=0）；改到 cascade/threshold 再跑 `replay_decision_engine.py` 看 replay 是否仍 rc=0 |
| export 八道紀律閘：`valuation_reviewer_gate` / technical rubric / `export_provenance` / `pt_revision_momentum` / `calculation_steps` parity / `forward_validation` / `conflict_bias`（§16 Phase 2.5）/ fan-in 紀律（§17 degraded lane 的 confidence cap） | `python3 investment/scripts/test_append_session_export.py` + `python3 investment/scripts/test_validate_session_export_gates.py`（兩者 rc=0）。前者鎖住 isolated prepare、tamper refusal 與 18 路並行 commit 不丟 entry。**動到 `append_session_export.py` 的蓋章、lock 或 digest 排除清單、`decision_engine.py` 的 artifact 落地、`forward_validation`、或任一 cutoff 常數時必跑**——這些閘都是「規則寫了但沒接線」修回來的，而沒接線的閘沒有症狀。§17 還示範了第二種後果：閘沒接線久了，**它要讀的欄位會自己爛掉**——`degraded_analysts` 用過 10 種寫法指涉 5 個 lane，於是 cap 想接也接不上。合約含**接線斷言**（把 check 從 `main()` 拆掉要會紅），因為只驗行為的版本擋不住 V4.116.2 那種「閘存在、從不被呼叫」。T5 同時鎖住兩代行為：1.0.x legacy 僅 warning；1.1.0+ 只有 `forward_validation=FAIL` 可硬降級，未執行則 rc=1 |
| `trade_plan_builder.py` / Phase 4 sizing 鏈 / `validate_session_export.py` §14 | `python3 investment/scripts/test_trade_plan_builder.py` + `python3 investment/scripts/validate_session_export.py`（兩者 rc=0）；改到 sizing 鏈段序或 FTD/fragility 表再跑 `replay_trade_plan.py` 看三個 cohort 是否仍 rc=0（`current_rule_mismatched` 必須為 0） |
| `render_investment_report.py` / Phase 5 MD 渲染 / `inject_report_facts.py` 的 6 個 FACTS renderer | `python3 investment/scripts/test_render_investment_report.py`（rc=0）。鎖住「golden 逐位元穩定 + FACTS 區塊與 inject_report_facts 同源、decision-lock 數字全部到頁、bundle↔history 12 個重疊欄位逐一漂移偵測、Step 1.5 覆寫不誤判、`--polish` 三道守衛 fail-open、輸出過 `validate_markdown_export.py`」。改了 `inject_report_facts.py` 的 renderer 也要跑這支——報告與注入共用同一組函式 |
| `session_export_version` / export schema 版本閘 / `phase5_export_schema.md` 的 FULL EXAMPLE | `python3 investment/scripts/test_session_export_schema.py`（rc=0；fixture 直接從 schema doc 的 FULL EXAMPLE 解析，doc 壞掉會紅）。升版號時同時檢查 `replay_decision_engine.py` / `replay_trade_plan.py` 覆蓋數沒歸零 |
| `sentiment_score.py`（L5 Sentiment det producer）/ validator §5j | `python3 skills/market-sentiment-analyzer/scripts/test_sentiment_score.py` + `python3 investment/scripts/test_lane_contract.py`（兩者 rc=0）。**動到規則表門檻或兩個 clamp 常數時必跑**——那兩個常數是 protocol 規格空白的填補，改了等於 shadow 累積中的樣本與翻預設時要跑的公式不是同一個。另跑 `shadow_report.py`（L5 區段不得 crash） |
| `apply_det_shadow.py` 的 C1 契約 / `validate_session_export.py` §15 / lane 區塊形狀鎖 | `python3 investment/scripts/test_lane_contract.py` + `python3 investment/scripts/validate_session_export.py`（兩者 rc=0）。**動到 provenance 值域或 lane 名單時必跑**——契約的保留規則一旦破掉，L5/L6/L8 的 det producer 會被靜默覆寫回 `llm` 預設（驗證仍全綠）。另跑 `test_valuation_pack_consistency.py`（它直接呼叫 `apply_to_trade`）|
| forward_expectations 子模組 | 對應測試檔用 `ls investment/scripts/test_forward_expectations_*.py` 找（多數與子模組同名；另有 numeric_safety 等綜合測試——改到相鄰邏輯就一併跑） |
| Royalty/IP adapter | `python3 investment/scripts/test_royalty_ip_adapter.py` |
| Semiconductor adapter | `python3 investment/scripts/test_semiconductor_adapter.py` |
| quant-backtest 引擎 | `python3 skills/quant-backtest/scripts/test_backtest.py`；策略排名變動再跑 `rank_strategies.py` |
| ticker price range CLI | `python3 investment/scripts/test_forward_price_range.py` |
| valuation-modeler 引擎（dcf/comps/xlsx） | `python3 skills/valuation-modeler/tests/test_dcf.py` + `test_comps.py` + `test_export_xlsx.py` |
| ic-memo initiation renderer / validator | `python3 skills/ic-memo-writer/tests/test_compose_initiation.py` |
| `phase1_factpack.py` 的 shared Phase 0 resolver、earnings-analyst / forecaster prewarm、`EARNINGS_ANALYST_BUNDLE` 取得路徑 | `python3 investment/scripts/test_phase1_factpack.py`（rc=0）。鎖住「canonical Phase 0 優先於較新的 incomplete sector context、跨 ticker 共用、sector-only → `INCOMPLETE_NEEDS_L3`、frozen `phase0_path` 對外輸出」，以及 fetch→analyze→forecast、換季 refetch、timeout/缺 script fail-soft、`--no-prewarm`。**動到 Phase 0 cache 或 prewarm/bundle 取得順序時必跑** |
| `deep_dive_extractor.py` 的 Phase 0 歷史查找 | `pytest -q scripts/extractors/tests/test_extractors_review_fixes.py -k macro_regime`（rc=0）。鎖住同日 canonical 優先、ticker-scoped legacy fallback 與 MD fallback；動到 deep-dive Phase 0 lookup 時必跑 |
| 盤前檢查 modal / chain UI（`index.html` / `style.css` / `script.js`） | `pytest -q tests/test_premarket_chain_ui.py tests/test_premarket_daily_outcome.py && node --check Dashboard/script.js`（rc=0）。鎖住三階段 stepper、viewport 限高、mobile fallback、phase state wiring 與 backend 非阻塞規則 |
| `us-stock-analysis/analyze.py` 的 bundle→區塊 merge（Fundamentals lane 數字來源） | `python3 skills/us-stock-analysis/scripts/test_bundle_merge.py`（rc=0）。鎖住「`_derive_from_bundle()` emit 的每個 key 都有 merge 目標、不得回退成 `locals()` 解析、`revenue_yoy_pct` 走 bundle 不走 yfinance」。**改到 `_derive_from_bundle` 的 key 或 `analyze()` 的區塊變數名時必跑**——兩邊漂移是靜默的，覆寫會被算完丟掉 |
| `dashboard_server` heatmap PE 快取 / `_fetch_pe_ttm` / `_heatmap_refresh_pe_universe` | `python3 tests/test_heatmap_pe_retry.py`（rc=0）。鎖住「失敗不進快取、部分成功保留、backoff escalate、429 熔斷不算失敗批次、`PE_ABSENT` 空資料 symbol 隔離而非永久重試、outage 不得隔離任何 symbol」 |
| `dashboard_server` protocol queue / broker execution slot / process attach-heartbeat | `python3 tests/test_protocol_cooldown.py`（檔名為歷史名稱）+ `python3 tests/test_protocol_model_routing.py` + `python3 tests/test_broker_gate.py`；`Dashboard/utils.js`、`analyze-queue.js`、`page-news.js`、`page-earnings.js`、`page-sector.js` 各自跑一次 `node --check <file>`。鎖住最多三個 active、artifact single-writer、`provider_busy` 重排、`broker:unavailable` bounded-backoff 重試與 waiting reason、最近失敗不得隨 active 歸零消失、啟動窗口不可提早 cancel 釋放 slot、status/cancel job identity、broker client 0.3 heartbeat/PID attach；broker 端另跑 `tests/test_provider_slots.py`、full pytest、Ruff、mypy。 |
| `model_router.py` / task registry / broker-only routing / `llm_config.json` | `python3 scripts/_shared/test_model_router_window.py` + `python3 tests/test_broker_gate.py` + `python3 scripts/audit_llm_governance.py`（皆 rc=0）。Local budget 只留 telemetry；任何 task 未註冊、未認證、broker off/unreachable/refused 都不得啟動 LLM。|
| `broker_gate.quota_snapshot()` / `Dashboard/utils.js` 的 LLM 額度面板（長條、hover card、旗標） | `python3 tests/test_broker_gate.py`（rc=0）+ `node --check Dashboard/utils.js`。鎖住 headline 讀 5h 窗口、`headline_bucket` 標明來源、沒有 5h 的那家不得把週數字當 5h 用，以及 V4.130.2 的**過期 cooldown**：`cooldown_until` 在 gate 層是**原封轉送**（broker 是唯一權威），所以「過期不算冷卻」的判斷在 JS，測試因此直接斷言 utils.js 原始碼。broker 那側的對應修正在 `llm-quota-broker` 的 `service.py` / `db/ledger.py`，改任一邊都要跑另一邊 |
| Signal Queue 聚合／delivery lifecycle／protocol queue writeback／跨頁 deep-link | `python3 -m pytest -q tests/test_signal_queue.py` + `python3 tests/test_protocol_model_routing.py` + `node --check Dashboard/signal-queue.js` + `node --check Dashboard/page-break-news.js`。必須看到 78+ passed 與 routing contract holds；鎖住 failed 同 revision 可重試、consumed 遇新 revision 重開、pending remove / pre-dispatch reject 的 terminal writeback、earnings 兩種執行 family 的 fresh artifact gate、與 feed 之外 `news_id` 直達 item endpoint。|
| `dashboard_server` agentic protocol 模型路由 / Codex JSONL 解析 / `PROTOCOL_DOC` / `PROVIDER_CONTEXT_FILE` / `protocol_providers` 白名單 | `python3 tests/test_protocol_model_routing.py`（rc=0）。鎖住 primary 選擇、Codex CLI 寫入權限、tool/subagent 語意映射、進度/錯誤/token usage 解析，以及 V4.114.0 三件事：(a) 每個非 claude provider 的 prompt 前導只提**自己**那個 context 檔、且必帶本次 protocol 的規範路徑；(b) `PROTOCOL_PROMPTS` 每個 key 都要有存在的 `PROTOCOL_DOC` 檔；(c) 白名單必須落到 `forbidden_providers`——只放 `preferred_providers` 是**不會生效的**（broker 只把它當評分），且白名單空/壞掉一律 fail closed。**V4.131.14 起同時鎖 `PROTOCOL_REQUIRED_ARTIFACTS`**：每個有 validator gate 的 protocol（news/sector/invest）都必須有 required artifact，且閘的路徑與 `PREFLIGHT_ITEMS` 的 glob 必須解析到**同一個檔**。前者是因為 sector/news 兩個 key 從來沒被登記，HARD gate 正確中止的跑會 rc=0 顯示成功；後者是因為兩處在同一模組相隔約 1300 行、各手寫一次，漂移後閘會永遠檢查一個沒人寫的路徑而靜默通過。**注意這支是腳本不是 pytest 模組**，`python3 -m pytest` 跑它會 `no tests ran` |
| `investment/scripts/run_protocol_manual.py`（手動跨 provider 執行） | `python3 investment/scripts/run_protocol_manual.py <provider> <protocol> [TICKER]`。**用途只有一個**：驗證某個正式 provider 到底跑不跑得動某支 protocol。prompt / argv / timeout 全部複用 `dashboard_server`；啟動前向 quota broker 取得該 provider 的 pinned lease，process attach 後以實際 tokens settle，broker 不授權就不執行。會寫正式 `history.json`，因此保留原子鎖、獨立 log/backup/job_id、validator 失敗報告隔離，以及 `protocol code untouched` / `contexts` 兩項證據。|
| `CLAUDE.md` 的 Protocol Triggers / 自動層 / Validator Gates / Workflow Rules 四節 | `python3 scripts/sync_agent_context.py --check`（rc=0）。這四節是 `GEMINI.md` / `AGENTS.md` generated 區塊的來源，改完沒重生成 = 非 Claude 的 CLI 讀到舊路由 |
| News event store / finalizer / projection / migration | `python3 -m pytest tests/news -q`（rc=0）後跑 `python3 news/scripts/validate_digest_output.py`。鎖住 append-only replay、event-id REVIEW、cache idempotency、rollback 與 JSONL→digest exact projection |
| `sector_score_calculator.py` / `build_sector_intel.py` 的 shadow 段 | `python3 sector/scripts/test_sector_score_calculator.py`（rc=0）。鎖住「Step 5 乘數**偵測不重算**（重算 = 雙重計分，含 2026-07-31 Energy 真實回歸樣本）、half-up 捨入（**不可換回內建 `round()`**，也**不可在乘法後補 `round(x,2)`** —— 那是銀行家捨入會造成雙重捨入；`_ROUND_EPS` 不可移除，浮點雜訊會讓真值 `.5` 少 1 分）、**逐欄位**守衛（單一分項 null 被當 0 = 假 hard diff，累計上限 0 會永久擋死 SE2）、算不出 ≠ 算錯、割接統計只數 `sample_valid` 場次、歷史 audit 與**回填舊日期**都不得混進 live 分母、shadow 落盤失敗不得中斷 build」。改完順手跑 `--audit-decisions` 對照 43 場基線（38 clean / 4 hard / 33 soft / 1 drift）沒退 |
| `da_pretrigger.py` / `phase_4-5.md` 的 R4–R7 門檻 | `python3 sector/scripts/test_da_pretrigger.py`（rc=0）。鎖住「四條規則各自的 sample-size / 方向性 gate、R4 邊界是 `>` 不是 `>=`、**資料缺席 ≠ 沒觸發**（FRED 缺席標 unavailable、HARD cache 缺席 rc=1、**逐板塊缺席標 `uncovered`**）、null 欄位不得被當 0 誤觸發、R5 豁免三條件皆須有值、錯誤走 stderr（stdout 是逐字 paste 契約）」 |
| `fetch_sector_valuation.py` 的 PE snapshot 取得／回退、`build_sector_intel.py` 的 provenance passthrough | `python3 sector/scripts/test_fetch_sector_valuation.py`（rc=0，零網路）。鎖住「非交易日回退到最近**有資料**的交易日並回報**實際來源日**、交易日不誤觸回退（多探 = 白花額度）、**單一 exchange 有值不算數**（半套資料湊出的 snapshot 是靜默半真相）、回看窗口第 5 天過第 6 天中止、窗口內全空仍 rc≠0、provenance 欄位有進 payload 與 `_phase1`」。**這支存在的理由是觸發面**：FMP `sector-pe-snapshot` 只有交易日有值，舊版一拿到空就 `sys.exit`，於是產業掃描逢週末必掛——而今年 sector 幾乎只在平日跑，唯一的週末（2026-07-11）就掛了同一個錯，沒人發現。日曆形狀的盲區不會被任何既有測試碰到。整檔還原到修復前的版本驗過會紅（吐的正是線上那句 `returned empty for .../NASDAQ`），兩道接線守衛也各自種回突變驗過紅 |
| `fetch_earnings_calendar.py` / `sector/lib/earnings_calendar.py` / `phase_prefetch.build_tasks` | `python3 -m pytest -q sector/scripts/test_fetch_earnings_calendar.py`（rc=0，7 passed）。**必須用 pytest 跑**——它是 `sector/scripts/` 底下唯一的 pytest 模組（其餘四支是可直接執行的腳本）。拿它當腳本跑有兩種結果，**兩種都會騙人**：從 repo root 直接 `python3 <path>` 會 `ModuleNotFoundError: No module named 'sector'`（看起來像測試壞了，其實是跑法錯）；加了 `PYTHONPATH=.` 則 **rc=0 但跑了 0 個測試**（只 import 了模組，`def test_*` 沒人叫），這是 §2c「沉默不是通過」的教科書案例——2026-08-16 我自己就這樣回報過一次假綠。判準：**看到 `N passed` 才算跑過**，只看 rc=0 不算 |
| `fetch_smart_money.py` 的兩趟 per-ticker 掃描 / `fmp_client.fmp_get_many` | **沒有 fixture 測試**（要打 FMP）。改到 fan-out 就跑 `python3 sector/scripts/fetch_smart_money.py --date <D>` 前後各一次，**逐欄位 diff 兩份 cache 必須完全相同**（`json.dumps(sort_keys=True)` 後 diff）。用 diff 報零之前先種一個差異確認它會報紅（§2c 規則 1）。另跑 `python3 sector/scripts/phase_prefetch.py --date <D>` 確認 `hard_fail=false`——這兩趟掃描是 360s per-task cap 的長桿，序列版 242s 在九路搶 RPM 時會超時 |
| `fred_lane_gate.py` | `python3 sector/scripts/test_fred_lane_gate.py`（rc=0）。鎖住「`adjustments_active` 是唯一 mandatory、低信心**不是** trigger、壞形狀不誤判（含**舊形狀 cache 的 `market_implications.sector_rotation` fallback** —— 漏了會讓 mandatory trigger 靜默不觸發）、`shadow_only` 恆 true」 |
| `scripts/wind/`（風向容器 / 派工器 / broker reasoning adapter / 預算閘）或 `config/wind.json` 的權重 | `python3 scripts/wind/test_wind.py`（rc=0，19 cases）+ `python3 -m pytest tests/test_x_kol_api.py -q`（26 passed，含 daemon 狀態）+ `python3 tests/test_broker_gate.py` + `node --check Dashboard/utils.js`；改到端點再驗 `curl -s localhost:8080/api/wind/terms`。除原有排序／佐證／冷卻／merge／心跳契約外，reasoning 必須由 adapter 走 broker-selected logged-in CLI、child env 不含 reasoning API keys、broker/JSON 失敗 fail-closed。 |
| `scripts/x_kol/heat.py` 的 `fetch_price_context` / `mark_unanalyzable` / `price_backend_status` | `python3 -m pytest -q tests/test_x_kol_heat.py tests/test_x_kol_api.py`（rc=0）。**先確認跑測試的那支 `python3` 真的 import 得到 `requests`** —— 2026-08-16 的整起事故就是 Homebrew 把預設 `python3` 換成 3.14（site-packages 空），`fetch_price_context` 的 `except Exception: return {}` 吞掉 ImportError，頁面於是對 NVDA/AMZN/GOOGL 全印「no price series in FMP」。測試用 monkeypatch 注入假 prices，**繞過真實 import，所以測試在環境斷掉時照樣全綠**。環境健檢：`python3 -c "import requests, pandas, yfinance"` |
| 任何 `argparse` CLI 的 `help=` 字串，或升級 Python 版本後 | `python3 tests/test_argparse_help_strings.py`（rc=0）。**Python 3.14 起裸 `%` 在 `add_argument()` 當下就 raise**（不再是跑 `--help` 才炸），所以 CLI 會一啟動即死。2026-08-16 就是這樣讓 `market_top_yfinance.py` 掛掉、Phase 1 fatal、整支 `daily_update.sh` rc=1，而盤前 chain 只顯示 `exited rc=1`——成因要去 `$TMPDIR/daily_update_<date>_<pid>_<step>.log` 撈。用 `%%`（argparse 仍印單一 `%`）。|
| `skills/_shared/finviz_screener.py`（FINVIZ public screener 的 ticker 修復）或任一 `Overview().screener_view()` 呼叫點 | `python3 -m pytest -q skills/_shared/tests/test_finviz_screener.py skills/theme-detector/scripts/tests/`（rc=0）+ `python3 tests/test_heatmap_pe_retry.py`。finviz 的 ticker `<td>` 內含一個 logo 載入失敗用的替代字母 `<span>`，finvizfinance 1.3.0 用 `col.text` 把它跟 ticker 連在一起讀，**每個 ticker 首字都被複製**（NVDA→NNVDA、AAPL→AAAPL）。偵測必須是**整批簽名**而非逐檔 `t[0]==t[1]`——AAPL/DDOG/LLY/FFIV/WWD 本來就是雙字母開頭，逐檔判斷會把它們砍成 APL。**不受影響、不要順手改**：Elite CSV export（`export.ashx`，真 CSV 無 HTML）與 `finviz_performance_client.py` 的 group view（Sector/Industry 聚合，無 Ticker 欄）|
| 任何 skill 的 SKILL.md / 結構 | `python3 scripts/check_skills.py`（warnings only；`--strict` 才 rc=1） |
| Finnhub/FMP 資料層 | `python3 skills/finnhub-client/scripts/audit_drift_check.py` |

## 8. Validator gates（protocol 收尾必過，rc=0）

```bash
python3 news/scripts/validate_digest_output.py        # News（schema: news/digest_output_schema.md）
python3 sector/scripts/validate_sector_intel.py       # Sector（schema: sector/schema.md）
python3 investment/scripts/validate_session_export.py # Invest（schema: investment/phase5_export_schema.md）
```
