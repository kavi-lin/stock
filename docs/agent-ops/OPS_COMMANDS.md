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
python3 investment/scripts/decision_engine.py --from-file /tmp/<T>_p3.json       # Phase 3 決策引擎（0 LLM 算術；輸出 calculation_steps 整塊 verbatim 抄寫）
python3 investment/scripts/decision_engine.py --phase 4.6 --from-file /tmp/<T>_p46.json  # Phase 4.6 decision cap 套用（收 Phase 4 sizing 後）
python3 investment/scripts/replay_decision_engine.py                             # engine × history 全量 replay + 排除清單 → reports/decision_review/DECISION_ENGINE_REPLAY_<date>.md
python3 investment/scripts/inject_report_facts.py                                # Phase 5 Step 4.5：報告佔位符 → history.json verbatim 注入（0 LLM、idempotent）
python3 investment/scripts/register_thesis.py                                    # Phase 5.5 thesis register（idempotent、non-fatal）
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
python3 scripts/link_digest/build_artifacts.py <judgment.json>   # Link Digest fan-out（rc 0/1/2）
python3 news/scripts/news_event_store.py pending                 # 列出待審 event_id
python3 news/scripts/news_event_store.py project --date YYYY-MM-DD
python3 news/scripts/news_event_store.py migrate --all           # legacy digest → JSONL；自動留 backup
python3 news/scripts/news_event_store.py rollback --date YYYY-MM-DD
python3 news/scripts/news_event_store.py telemetry --limit 10    # 滿 10 場後才調 materiality
```

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
| `compute_price_framework.py` / valuation projection validator | `python3 investment/scripts/test_compute_price_framework.py` + `python3 investment/scripts/test_valuation_pack_consistency.py`（兩者 rc=0；後者含故意 drift 的 rc=1 fixture）。前者含 V4.88.0 staged regression：`--stage quant` + `--stage mhp` 合併輸出必須與單發模式逐位元一致（只豁免 `valuation_pack.built_at`），改到分段/合併路徑必紅 |
| `fwd_earnings_discounted` 的四個 clamp 常數（`FWD_PE_CLAMP` / `FWD_DISCOUNT_CLAMP` / `FWD_MIN_ANALYSTS` / `FWD_MAX_HORIZON_YEARS`）| `python3 investment/scripts/test_compute_price_framework.py` + `python3 investment/scripts/test_shadow_report.py`（兩者 rc=0）。**改 clamp 值之前先跑 `python3 investment/scripts/shadow_report.py` 看校準區塊**：判準是 live cohort 的市場隱含 PE P33–P66 有沒有包住現行上限。live cohort 不足 `FWD_PE_CALIB_MIN_N` 時判準會回 `accumulating`——那是「還不知道」，不是「沒問題」。**不可自動跟隨中位數**（泡沫期會讓上限一路上移），改值一律 user 核准 |
| `valuation_reviewer_gate.py` / `peer_cohorts.py` 的 discovery cache | `python3 investment/scripts/test_valuation_reviewer_gate.py`（rc=0）+ `python3 skills/valuation-modeler/tests/test_comps.py`。鎖住「5 條 trigger 各自獨立命中、`transition_case_active` 是唯一 mandatory、TTL 30d 邊界、discovered 永不覆寫人工核准的 `config/peer_cohorts.json`、artifact 不可用 rc=1」 |
| earnings valuation forecaster | `python3 skills/earnings-valuation-forecaster/tests/test_forecaster_v3_17.py` |
| `forward_expectations.py` 核心 | `python3 investment/scripts/test_forward_expectations.py`（rc=0 為準） |
| `inject_report_facts.py` | `python3 investment/scripts/test_inject_report_facts.py` |
| `decision_engine.py` / Phase 3 決策數學 / `validate_session_export.py` §13 | `python3 investment/scripts/test_decision_engine.py` + `python3 investment/scripts/validate_session_export.py`（兩者 rc=0）；改到 cascade/threshold 再跑 `replay_decision_engine.py` 看 replay 是否仍 rc=0 |
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
| `phase1_factpack.py` 的 earnings-analyst / forecaster prewarm、`EARNINGS_ANALYST_BUNDLE` 取得路徑 | `python3 investment/scripts/test_phase1_factpack.py`（rc=0，27 案例）。鎖住「fetch→analyze→forecast 順序、fetch 失敗必須不跑 analyze（否則 analyze 會刷新舊季 cache 的 mtime 讓它看起來新鮮）、`refreshed` 旗標來自 fetch.py 的 stderr 宣告而非 mtime 比較、只有換季才對 forecaster 加 `--no-cache`、timeout/缺 script/任意例外一律降級成狀態字串不得 raise、`--no-prewarm` 兩者都 disabled」。**動到 prewarm 或 bundle 取得順序時必跑**——這條壞掉會讓 Phase 1.5 對著缺席 bundle 凍結 valuation_pack（8 個 anchor 全滅且無警告），或讓每次 protocol 都多付一次完整 forecaster refetch |
| `us-stock-analysis/analyze.py` 的 bundle→區塊 merge（Fundamentals lane 數字來源） | `python3 skills/us-stock-analysis/scripts/test_bundle_merge.py`（rc=0）。鎖住「`_derive_from_bundle()` emit 的每個 key 都有 merge 目標、不得回退成 `locals()` 解析、`revenue_yoy_pct` 走 bundle 不走 yfinance」。**改到 `_derive_from_bundle` 的 key 或 `analyze()` 的區塊變數名時必跑**——兩邊漂移是靜默的，覆寫會被算完丟掉 |
| `dashboard_server` heatmap PE 快取 / `_fetch_pe_ttm` / `_heatmap_refresh_pe_universe` | `python3 tests/test_heatmap_pe_retry.py`（rc=0）。鎖住「失敗不進快取、部分成功保留、backoff escalate、429 熔斷不算失敗批次、`PE_ABSENT` 空資料 symbol 隔離而非永久重試、outage 不得隔離任何 symbol」 |
| `model_router.py` 預算 / `llm_config.json` budgets / `llm_drivers.load_llm_config()` | `python3 scripts/_shared/test_model_router_window.py`（rc=0）。含 end-to-end 案例走真的 loader + 真的 config —— `load_llm_config()` 是**白名單**不是 merge，新增 budget key 沒加進 loader 會被靜默丟掉、cap 永遠不生效 |
| `dashboard_server` agentic protocol 模型路由 / Codex JSONL 解析 | `python3 tests/test_protocol_model_routing.py`（rc=0）。鎖住 primary 選擇、Codex CLI 寫入權限、tool/subagent 語意映射、進度/錯誤/token usage 解析 |
| News event store / finalizer / projection / migration | `python3 -m pytest tests/news -q`（rc=0）後跑 `python3 news/scripts/validate_digest_output.py`。鎖住 append-only replay、event-id REVIEW、cache idempotency、rollback 與 JSONL→digest exact projection |
| `sector_score_calculator.py` / `build_sector_intel.py` 的 shadow 段 | `python3 sector/scripts/test_sector_score_calculator.py`（rc=0）。鎖住「Step 5 乘數**偵測不重算**（重算 = 雙重計分，含 2026-07-31 Energy 真實回歸樣本）、half-up 捨入（**不可換回內建 `round()`**，也**不可在乘法後補 `round(x,2)`** —— 那是銀行家捨入會造成雙重捨入；`_ROUND_EPS` 不可移除，浮點雜訊會讓真值 `.5` 少 1 分）、**逐欄位**守衛（單一分項 null 被當 0 = 假 hard diff，累計上限 0 會永久擋死 SE2）、算不出 ≠ 算錯、割接統計只數 `sample_valid` 場次、歷史 audit 與**回填舊日期**都不得混進 live 分母、shadow 落盤失敗不得中斷 build」。改完順手跑 `--audit-decisions` 對照 43 場基線（38 clean / 4 hard / 33 soft / 1 drift）沒退 |
| `da_pretrigger.py` / `phase_4-5.md` 的 R4–R7 門檻 | `python3 sector/scripts/test_da_pretrigger.py`（rc=0）。鎖住「四條規則各自的 sample-size / 方向性 gate、R4 邊界是 `>` 不是 `>=`、**資料缺席 ≠ 沒觸發**（FRED 缺席標 unavailable、HARD cache 缺席 rc=1、**逐板塊缺席標 `uncovered`**）、null 欄位不得被當 0 誤觸發、R5 豁免三條件皆須有值、錯誤走 stderr（stdout 是逐字 paste 契約）」 |
| `fred_lane_gate.py` | `python3 sector/scripts/test_fred_lane_gate.py`（rc=0）。鎖住「`adjustments_active` 是唯一 mandatory、低信心**不是** trigger、壞形狀不誤判（含**舊形狀 cache 的 `market_implications.sector_rotation` fallback** —— 漏了會讓 mandatory trigger 靜默不觸發）、`shadow_only` 恆 true」 |
| 任何 skill 的 SKILL.md / 結構 | `python3 scripts/check_skills.py`（warnings only；`--strict` 才 rc=1） |
| Finnhub/FMP 資料層 | `python3 skills/finnhub-client/scripts/audit_drift_check.py` |

## 8. Validator gates（protocol 收尾必過，rc=0）

```bash
python3 news/scripts/validate_digest_output.py        # News（schema: news/digest_output_schema.md）
python3 sector/scripts/validate_sector_intel.py       # Sector（schema: sector/schema.md）
python3 investment/scripts/validate_session_export.py # Invest（schema: investment/phase5_export_schema.md）
```
