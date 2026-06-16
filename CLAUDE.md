# AI 投資委員會 — Agent Execution Context

> **Version**: Sync `VERSION` file + `Dashboard/utils.js`. Full background in `README.md`.

## Protocol Triggers (中期 / 委員會層)

| Command | File | Notes |
|---|---|---|
| `產業掃描` | `sector/sector_protocol_main.md` | Multi-file (Phase 0-5) |
| `分析 [TICKER]` | `investment/investment_protocol_v5_0.md` | V5.0/V3.48 — 5 lane subagent (含 Valuation Specialist) + Burry + Red Team + **Phase 2.4 price framework engine**（`compute_price_framework.py` 一次算 fair_value_summary 6-anchor blend + fair_value_range 區間 + MHP 三時間框架 + reverse DCF + archetype shadow，0 LLM 算術，`--self-assemble` 自組 quant 輸入）+ Phase 4.5 封裝呈現 + **Phase 5.5 thesis registry auto-wire (V2.14.0)**。Bundle 規範見 `investment/protocol_appendix_fmp_bundles.md` |
| `財報 [TICKER]` | `skills/earnings-analyst/SKILL.md` | FMP 三表 8Q + 品質 flag + 0-100 composite。Cache key (TICKER, last_earnings_date)。**V2.14.0 起 MD 報告強制 EDGAR / IR / FMP markdown clickable link**（見 SKILL.md Citations section）|
| `新聞分析 DIGEST` | `news/news_protocol_v2.md` | RSS -> Triage -> Debate |
| `新聞分析 FLASH [text]` | `news/news_protocol_v2.md` | Deep Debate only |
| `動能 [TICKER]` | `skills/momentum-monitor/scripts/momentum.py` | Score + Signals |
| `動能選股` | `skills/momentum-monitor/scripts/screen.py` | Universe Scan |
| `更新 journal` | `skills/momentum-monitor/scripts/journal.py` | Performance tracking |
| `財報前瞻 [TICKER]` (UI 自動觸發) | `skills/earnings-valuation-forecaster/scripts/forecast.py --pre-earnings` | **V2.15.0** — Dashboard `earnings.html` 卡片 + `calendar.html` upcoming earnings event 在 `next_earnings_source==='fmp_confirmed'` 且 days_until ≤ 7 時自動 morph 出「📋 前瞻」button。Server SCRIPT_PROTOCOLS 路徑（不走 Claude turn，直接 subprocess）|
| `ic-memo [TICKER]` 或 `分析 [TICKER] --memo` | `skills/ic-memo-writer/scripts/{build_fact_pack,compose,validate_ic_memo}.py` | **V3.25.0** — 12 章節高可讀 IC Memo MD (`reports/<DATE>_<TICKER>_ic_memo.md`)。Deterministic-only renderer (0 LLM call)，重用 protocol.history + earnings-analyst cache + company_context；**不重評分、不修改 history.json**。§11 verbatim 由 11 欄位 SHA256 decision_lock 保護。rc 分級：0 pass / 1 fatal / 2 degraded-usable。 hook 失敗 non-fatal，不影響 Phase 5 done。詳見 `skills/ic-memo-writer/SKILL.md` |

## Tactical Opportunity Radar (短期 1-15 天層 — Auto, no trigger needed)

每日跑 `daily_update.sh` Step 6 自動產出。直接讀檔即可：

| 檔案路徑 | 內容 |
|---|---|
| `skills/thematic-screener/data/recommendations/<DATE>.json` | 當日 Top 5 themes × Top 4 movers + regime snapshot + concentration WARNING |
| `reports/SHORT_TERM_WEEKLY_<DATE>.md` | 週末手動跑 `weekly_review.py` 產出，含 hit rate / alpha / 建議 weights 調整 |
| `skills/short-term-target/config/weights.yaml` | 手動編輯校準（bump `weights_version` 後生效） |

可手動單股查詢：`python3 skills/short-term-target/scripts/predict.py <TICKER>`

**重點紀律**：戰術層**完全不影響** investment_protocol 決策。`weights.yaml` 由 user 手動 edit；`weekly_review.py` 永不自動覆寫 config。

Detailed skills: `skills/MARKET_INDEX.md`. Architecture rationale: `docs/plan_short.md`.

## Break News (V6 / 4.8.0 — Auto, no trigger needed)

dashboard_server 開機後常駐 2 條 daemon thread：

| 元件 | 內容 |
|---|---|
| `break_news_poll_loop` (每 600s) | 跑 `scripts/break_news/poller.py`：抓 **9 個 RSS feed + Futu 牛牛推播 (US 限定) + 免費社群/趨勢源 (Reddit / HN / Google Trends)** → stage1_triage 分數閘（Futu 旁路、社群源更高門檻）→ **V6 event clustering (`cluster.py`，0 LLM)**：同事件多源重複合併為 echo 不重辯（`cluster_echo`）、sentiment 類非 binary/非 HIGH cred/\|score\|<3 只聚類計數不辯論（`sentiment_cluster_only`）、echo milestone (4/8/16/32 且距上次辯論 ≥3h) 觸發增量追辯（`cluster_escalation`）→ 候選依 score/binary/credibility/freshness 排序消耗 LLM 預算；admission 讀 A/B voice quota headroom，扣 backlog × `BREAK_NEWS_EST_CALLS_PER_DEBATE`(預設 2)，`BREAK_NEWS_SESSION_RESERVE` 保留美股時段額度 → 寫 `news/break_news_logs/bn_<date>_<hash>.json` |
| `break_news_debate_loop` | 掃 `pending_debate` → `debater.py` V6：round 1 blind 雙開（2 call），**嚴格 divergence gate** — 只有 verdict 真對立 / 關係極性衝突才開 1 輪 rebuttal（max 2 rounds；conf-gap 觸發限 high-priority 且 ≥0.65）；單邊 CLI 掛 → `single_voice` 收 partial_closed 不燒空轉 rebuttal。escalation item 的 opener 附前次 cluster 結論只辯增量。每 cycle 順跑 `market_brief.maybe_generate()`（TTL 2h，1 LLM call 產市場導讀）|
| `/break-news.html` | **Market Brief 導讀面板**（regime + 200-300 字繁中導讀 + drivers/bull/bear/watch — 評估市場現況的入口）+ stream 卡片（×N echo badge / ⤴ 升級追辯 badge）+ 辯論 side panel + 情緒趨勢圖 |
| API | GET `/api/break-news/{feed,item/<id>,state,brief,clusters,trends}` / POST `/refresh`, `/brief/refresh`, `/item/<id>/replay`；debate 用獨立 `_break_news_dispatch_lock`，**不**搶 `_protocol_lock`（normal `分析/產業掃描/新聞分析` 不會被擋） |

可手動跑：
```bash
python3 scripts/break_news/poller.py --once             # 單次 poll
python3 scripts/break_news/cluster.py --feed            # 24h 事件 cluster 熱度表
python3 scripts/break_news/market_brief.py --force      # 強制重產市場導讀 (1 LLM call)
python3 scripts/break_news/debater.py --news-id <id>    # 單條 debate
python3 scripts/break_news/validate.py                  # schema lint (含 clusters/brief)
```

**重點紀律**：Break News 為**探索層**，**不**影響 investment_protocol 決策。Claude × Gemini 是要刻意造成意見分歧，divergence_note 是訊號不是 bug。echo_count 高 = 多源報導 = 重要性訊號；cluster 去重省的是「重複辯論」不是「資訊」。

## Knowledge Graph (Project Nexus V3.0)

Force-directed graph layer over news + sector + theme + earnings + decision artifacts.
Surfaces 1st/2nd/3rd-order ticker ↔ narrative ↔ catalyst relationships.

| 觸發點 | 內容 |
|---|---|
| `daily_update.sh` Step 8 | Tier 1 (structured JSON) + Tier 2 (regex tech-nodes: HBM3e / N3P / CoWoS-L / Blackwell …) + Tier 3 (Haiku 4.5 NER, 條件: `ANTHROPIC_API_KEY` 已設定) |
| `Dashboard/nexus_graph.json` | 圖譜輸出（~1.5 MB Tier 1+2，~3 MB 含 Tier 3 full backfill；硬上限 5 MB） |
| `/graph.html` Dashboard page | Obsidian-style monochrome force-graph，點 node → BFS 3 跳路徑追蹤 |
| `/api/graph/data` + `/api/graph/centrality/<TICKER>` | 只讀檢視 API；**不**進入 investment_protocol Arbiter (V3.1 預留) |
| Ad-hoc | `python3 scripts/nexus/build_graph.py --tier 1,2,3 --full` |

**重點紀律**：Nexus 為**探索層**。Tier 3 LLM 找到的新實體先標 `provisional`，需 ≥3 份獨立報告才晉升為一級節點。決策邏輯（buy_threshold / position_size）**完全不受** Nexus 影響 — Arbiter 整合留給 V3.1。

## Validator Gates (Must be rc=0)

| Mode | Script | Schema |
|---|---|---|
| News | `news/scripts/validate_digest_output.py` | `news/digest_output_schema.md` |
| Sector | `sector/scripts/validate_sector_intel.py` | `sector/schema.md` |
| Invest | `investment/scripts/validate_session_export.py` | `investment/phase5_export_schema.md` |

## Output Paths

- **Reports**: `reports/` (`YYYYMMDD_TICKER.md`, `YYYY-MM-DD_sector_report.md`, etc.)
- **Caches**: `sector/logs/`, `investment/invest_logs/`, `news/news_logs/`, `skills/*/cache/`

## Ops Shortcuts

```bash
# Tier 1 — Daily auto (3-5 min)
./daily_update.sh
# Steps: 1) Breadth → 2) FTD → 3) Top → 4) FRED → 5) Bridge → 6) Thematic Screener → 7) Structural Watchlist → 8) Nexus Graph (V3.0)

# Tier 3 — Weekend manual (1-2 min)
python3 skills/short-term-target/scripts/weekly_review.py
# Output: reports/SHORT_TERM_WEEKLY_<DATE>.md

# Ad-hoc
python3 skills/short-term-target/scripts/predict.py <TICKER>          # 1d/5d/15d projection
python3 skills/finnhub-client/scripts/run_dual_fetch.sh --tickers X   # canonical scoring snapshot
python3 skills/finnhub-client/scripts/audit_drift_check.py            # Finnhub vs FMP drift
python3 investment/scripts/backtest_postmortem.py                     # protocol decisions backtest
python3 skills/_shared/company_context.py <TICKER> --peers            # shared profile/peers cache (24h TTL)
python3 investment/scripts/register_thesis.py                         # Phase 5.5 thesis register (V2.14.0; idempotent + non-fatal)
python3 scripts/check_skills.py                                       # skills/*/SKILL.md frontmatter + cross-ref linter (V2.14.0; warnings only, rc=0)
python3 skills/earnings-valuation-forecaster/scripts/forecast.py <T> --pre-earnings --output-dir reports/   # V2.15.0 pre-earnings cheat sheet
python3 skills/ic-memo-writer/scripts/build_fact_pack.py <T>                                  # V3.25.0 IC Memo fact_pack (12 章節資料聚合 + decision_lock 11 欄位 hash)
python3 skills/ic-memo-writer/scripts/compose.py <T>                                          # V3.25.0 IC Memo MD render (deterministic, 0 LLM)
python3 skills/ic-memo-writer/scripts/validate_ic_memo.py reports/<DATE>_<T>_ic_memo.md       # V3.25.0 IC Memo validator (rc=0/1/2)
python3 scripts/nexus/build_graph.py --tier 1,2 --dry-run                       # V3.0 Nexus graph: dry-run stats (no Tier 3 LLM)
python3 scripts/nexus/build_graph.py --tier 1,2,3 --full                        # V3.0 Nexus graph: full Tier 1+2+3 rebuild (needs ANTHROPIC_API_KEY)
python3 sector/scripts/sector_digest.py                                         # V1.4.1 sector: 1-call macro + 11-sector decision table (read-only)
python3 sector/scripts/build_sector_intel.py --date YYYY-MM-DD                  # V1.4.1 sector: assemble sector_intel.json from caches + decision JSON
python3 scripts/link_digest/build_artifacts.py <judgment.json>                  # V3.35 Link Digest: judgment.json → digest verdict + bn_*.json KG payload + validate + tier-1 graph refresh (rc 0/1/2)
python3 investment/scripts/compute_price_framework.py --from-file <inputs.json> # V3.45.3 Phase 2.4 price framework engine: fair_value_summary blend + fair_value_range + MHP 三框架 + reverse DCF + archetype shadow（0 LLM 算術；--no-fetch 跳過 FMP vol 自抓）
python3 investment/scripts/shadow_report.py                                     # V3.46.1 shadow 讀出端: #2 dispersion backfill + #6 oe / #3 archetype 翻轉率 + #4 news 分布偏移 + checkpoint 進度（唯讀，輸出 reports/SHADOW_REPORT_<date>.md）
python3 investment/scripts/test_compute_price_framework.py                      # V3.48.0 engine golden-fixture 回歸測試（26 asserts，改 engine 後必跑 rc=0）
python3 investment/scripts/forward_expectations.py --ticker <T> --self-assemble # V4.30.0 前瞻預期引擎（shadow）：同口徑 matrix + expectations gap + scenario policy + operating-driver scenario builder（Royalty/IP driver-level cases）+ future_price_range + ledger/inventory + ticker-neutral source discovery + bounded SEC document acquisition + management guidance extraction + estimate revision snapshot + financial bridge + primary-source gate + adapters（0 LLM；不碰 live blend）
python3 investment/scripts/forward_price_range.py <TICKER> # V4.30.0 ticker → future price range 驗收入口（current / horizon / bear-base-bull / method / warnings）
python3 investment/scripts/forward_expectations.py --ticker <T> --self-assemble --acquire-documents # V4.26.0 opt-in allowlisted SEC filing text normalization + guidance extraction
python3 investment/scripts/forward_expectations_source_discovery.py <T> --no-fetch # V4.21.0 跨 ticker source manifest（metadata only；不 promotion）
python3 investment/scripts/forward_expectations_guidance.py --primary-source-file primary.json # V4.21.0 明確 management guidance/range extractor
python3 investment/scripts/forward_expectations_revisions.py --ticker <T> --earnings-cache-file <cache.json> # V4.21.0 analyst estimate/rating point-in-time snapshot
python3 investment/scripts/forward_expectations_calibration.py                  # V4.22.0 read-only forecast-vs-actual scaffold（insufficient_sample 不調參）
python3 investment/scripts/forward_expectations_financial_bridge.py --earnings-cache-file <cache.json> # V4.23.0 forward P&L/FCF bridge（shadow；不產生 fair value）
python3 investment/scripts/forward_expectations_gap.py --snapshot-file <snapshot.json> # V4.24.0 expectations gap builder（shadow；同口徑比較）
python3 investment/scripts/forward_expectations_report.py --snapshot-file <snapshot.json> # V4.25.0 render Forward Expectations shadow markdown section
python3 investment/scripts/forward_expectations_scenario_policy.py --snapshot-file <snapshot.json> # V4.26.0 scenario evidence gate policy（不產生 scenario 數字）
python3 investment/scripts/forward_expectations_scenario_builder.py --snapshot-file <snapshot.json> # V4.28.0 operating-driver scenario builder（shadow；Royalty/IP driver-level cases；不產生 fair value）
python3 investment/scripts/forward_expectations_price_range.py --snapshot-file <snapshot.json> # V4.29.0 future price range mapper（shadow；bear/base/bull target range）
python3 investment/scripts/forward_expectations_multiple_anchor.py <T>          # V4.31.0 自身歷史 multiple regime anchor（EXP-R1；price-independent；破套套邏輯）
python3 investment/scripts/forward_expectations_success_criteria.py             # V4.34.0 成功標準 gate（EXP-0.4；8 criteria；shadow→live 唯讀門檻；現況 insufficient_evidence）
python3 investment/scripts/test_forward_expectations.py                         # V4.34.0 forward_expectations core golden-fixture（48 asserts，改 engine 後必跑 rc=0）
python3 investment/scripts/test_forward_price_range.py                          # V4.30.0 ticker-facing future price range CLI golden-fixture
python3 investment/scripts/test_forward_expectations_source_discovery.py        # V4.21.0 ticker-neutral source discovery golden-fixture
python3 investment/scripts/test_forward_expectations_document_acquisition.py    # V4.21.0 bounded SEC document acquisition golden-fixture
python3 investment/scripts/test_forward_expectations_guidance.py                # V4.21.0 management guidance extraction golden-fixture
python3 investment/scripts/test_forward_expectations_revisions.py               # V4.21.0 estimate revision snapshot golden-fixture
python3 investment/scripts/test_forward_expectations_calibration.py             # V4.22.0 forecast calibration scaffold golden-fixture
python3 investment/scripts/test_forward_expectations_financial_bridge.py        # V4.23.0 financial bridge golden-fixture
python3 investment/scripts/test_forward_expectations_gap.py                     # V4.24.0 expectations gap golden-fixture
python3 investment/scripts/test_forward_expectations_report.py                  # V4.25.0 Forward Expectations markdown renderer golden-fixture
python3 investment/scripts/test_forward_expectations_scenario_policy.py         # V4.26.0 scenario policy golden-fixture
python3 investment/scripts/test_forward_expectations_scenario_builder.py        # V4.28.0 operating-driver scenario builder golden-fixture
python3 investment/scripts/test_forward_expectations_price_range.py             # V4.29.0 future price range mapper golden-fixture
python3 investment/scripts/test_forward_expectations_primary_sources.py         # V4.21.0 cache-first primary-source acquisition golden-fixture
python3 investment/scripts/test_forward_expectations_evidence.py                # V4.21.0 Evidence Inventory golden-fixture
python3 investment/scripts/test_royalty_ip_adapter.py                           # V4.28.0 Royalty/IP adapter golden-fixture（32 asserts，改 adapter 後必跑 rc=0）
python3 investment/scripts/test_semiconductor_adapter.py                        # V4.36.0 Semiconductor adapter golden-fixture（30 asserts；NVDA/AMD/MU end-market driver tree，royalty 讓給 royalty_ip）
python3 investment/scripts/test_forward_expectations_cohort.py                  # V4.35.0 base-rate cohort engine golden（23 asserts，防 cherry-pick）
python3 investment/scripts/test_forward_expectations_success_criteria.py        # V4.34.0 success-criteria gate golden（19 asserts，shadow→live 門檻）
python3 investment/scripts/test_forward_expectations_multiple_anchor.py         # V4.31.0 歷史 multiple regime anchor golden（21 asserts，EXP-R1 破套套邏輯）
```

## Link Digest (V3.35 — News 頁 URL 輸入框觸發)

News 頁貼上一條文章 URL → `link_digest` protocol（claude turn，`bypassPermissions` 故 WebFetch+WebSearch 可用）：讀全文 → WebSearch + 抓 3-5 篇相關 → 4 視角 inline 辯論 + Arbiter → LLM 寫 `reports/<DATE>_<HHMM>_link_digest.md`（人讀）+ `news/news_logs/link_digest/<id>.judgment.json`（機器），再跑 `scripts/link_digest/build_artifacts.py`（deterministic 0-LLM）fan-out 成 digest.json verdict（進新聞流）+ `news/break_news_logs/bn_*.json`（餵 Nexus 知識圖譜 / 供應鏈頁）。Spec：`news/link_digest_protocol.md`。**重點**：relation 被 ≥2 源佐證 → `support_count≥2` → Nexus Phase-2 晉升 directed 供應鏈 edge；KG schema 由 build_artifacts 保證（LLM 不手寫 digest/bn）。探索層，**不** patch sector_intel/phase0、不入 investment_protocol 決策。

## Shared Modules

- `skills/_shared/company_context.py` — single source for FMP company-level metadata. Exports `SECTOR_UNIVERSE` / `TICKER_TO_SECTOR` / `SECTOR_TOP_5`（被 `sector/scripts/fetch_*.py` import）+ `get_profile/get_peers/get_market_cap_history/get_employee_history`（24h cache @ `skills/_shared/cache/`）。修改 mega-cap 名單請只改這一處。
- `scripts/_shared/model_router.py` (V3.7.0) — 多模型治理層。`run_role()` / `run_with_fallback()` 走 fallback 鏈（primary → secondary → tertiary），跳過停用/超預算/quota cooldown 的模型,失敗自動降級。config 在 `config/llm_config.json`（primary/secondary/tertiary + enabled + budgets + cooldown_hours,sidebar 設定面板可改）;每日用量/cooldown 在 `config/llm_usage.json`（UTC 日界重置）。debater / supply_chain / `run_protocol` 都走它。`python3 scripts/_shared/model_router.py --status` 看現況。

## Workflow Rules

### 1. Pre-implementation Confirmation
**Trigger**: Changes involving **≥ 2 files** OR single file **≥ 50 lines**.
**Format**: Output a summary table (File, Action, Est. Lines, Description) + total tokens. Wait for user "OK" to proceed.

### 2. Session Completion Checklist
**Definition**: Human-requested dev/refactor/fix is complete.
1. **Bump VERSION**: Sync **three** locations together — `VERSION` file (純數字 `1.5.0`) + `Dashboard/utils.js` (`'V1.5.0'`) + **`CHANGELOG.md`** (新增 `## [x.y.z] — YYYY-MM-DD` 區塊，含 `### Changed/Added/Fixed` 條列 + `### Why` 動機；格式參考既有 v1.42.x 條目)。大改動 bump minor、小改動 bump patch。三處任一 desync 都不算完成。
2. **Update SESSION_NOTES.md / TODO.md**: Tick done, update state, write `Last Session Note`.

**🚫 EXCLUSION**: Protocol runs (`產業掃描`, `分析 [TICKER]`, etc.) are **NOT** sessions. Do NOT bump version or modify todolist after protocol execution.
