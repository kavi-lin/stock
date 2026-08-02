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
python3 scripts/daily_health.py            # --strict 有 FAIL 時 rc=1；--json 機器可讀

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
python3 sector/scripts/build_sector_intel.py --date YYYY-MM-DD   # 從 caches 組 sector_intel.json
python3 scripts/nexus/build_graph.py --tier 1,2 --dry-run        # Nexus 圖譜 dry-run（無 LLM）
python3 scripts/nexus/build_graph.py --tier 1,2,3 --full         # 全量重建（Tier 3 需 ANTHROPIC_API_KEY）
python3 scripts/link_digest/build_artifacts.py <judgment.json>   # Link Digest fan-out（rc 0/1/2）
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
| `compute_price_framework.py` / valuation projection validator | `python3 investment/scripts/test_compute_price_framework.py` + `python3 investment/scripts/test_valuation_pack_consistency.py`（兩者 rc=0；後者含故意 drift 的 rc=1 fixture） |
| earnings valuation forecaster | `python3 skills/earnings-valuation-forecaster/tests/test_forecaster_v3_17.py` |
| `forward_expectations.py` 核心 | `python3 investment/scripts/test_forward_expectations.py`（rc=0 為準） |
| `inject_report_facts.py` | `python3 investment/scripts/test_inject_report_facts.py` |
| `decision_engine.py` / Phase 3 決策數學 / `validate_session_export.py` §13 | `python3 investment/scripts/test_decision_engine.py` + `python3 investment/scripts/validate_session_export.py`（兩者 rc=0）；改到 cascade/threshold 再跑 `replay_decision_engine.py` 看 replay 是否仍 rc=0 |
| `trade_plan_builder.py` / Phase 4 sizing 鏈 / `validate_session_export.py` §14 | `python3 investment/scripts/test_trade_plan_builder.py` + `python3 investment/scripts/validate_session_export.py`（兩者 rc=0）；改到 sizing 鏈段序或 FTD/fragility 表再跑 `replay_trade_plan.py` 看三個 cohort 是否仍 rc=0（`current_rule_mismatched` 必須為 0） |
| `session_export_version` / export schema 版本閘 / `phase5_export_schema.md` 的 FULL EXAMPLE | `python3 investment/scripts/test_session_export_schema.py`（rc=0；fixture 直接從 schema doc 的 FULL EXAMPLE 解析，doc 壞掉會紅）。升版號時同時檢查 `replay_decision_engine.py` / `replay_trade_plan.py` 覆蓋數沒歸零 |
| forward_expectations 子模組 | 對應測試檔用 `ls investment/scripts/test_forward_expectations_*.py` 找（多數與子模組同名；另有 numeric_safety 等綜合測試——改到相鄰邏輯就一併跑） |
| Royalty/IP adapter | `python3 investment/scripts/test_royalty_ip_adapter.py` |
| Semiconductor adapter | `python3 investment/scripts/test_semiconductor_adapter.py` |
| quant-backtest 引擎 | `python3 skills/quant-backtest/scripts/test_backtest.py`；策略排名變動再跑 `rank_strategies.py` |
| ticker price range CLI | `python3 investment/scripts/test_forward_price_range.py` |
| valuation-modeler 引擎（dcf/comps/xlsx） | `python3 skills/valuation-modeler/tests/test_dcf.py` + `test_comps.py` + `test_export_xlsx.py` |
| ic-memo initiation renderer / validator | `python3 skills/ic-memo-writer/tests/test_compose_initiation.py` |
| 任何 skill 的 SKILL.md / 結構 | `python3 scripts/check_skills.py`（warnings only；`--strict` 才 rc=1） |
| Finnhub/FMP 資料層 | `python3 skills/finnhub-client/scripts/audit_drift_check.py` |

## 8. Validator gates（protocol 收尾必過，rc=0）

```bash
python3 news/scripts/validate_digest_output.py        # News（schema: news/digest_output_schema.md）
python3 sector/scripts/validate_sector_intel.py       # Sector（schema: sector/schema.md）
python3 investment/scripts/validate_session_export.py # Invest（schema: investment/phase5_export_schema.md）
```
