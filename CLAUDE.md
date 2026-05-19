# AI 投資委員會 — Agent Execution Context

> **Version**: Sync `VERSION` file + `Dashboard/utils.js`. Full background in `README.md`.

## Protocol Triggers (中期 / 委員會層)

| Command | File | Notes |
|---|---|---|
| `產業掃描` | `sector/sector_protocol_main.md` | Multi-file (Phase 0-5) |
| `分析 [TICKER]` | `investment/investment_protocol_v5_0.md` | V5.0 — 5 lane subagent (含 Valuation Specialist) + Burry + Red Team + Phase 4.5 fair_value_summary（6 anchor weighted blend 給合理股價）+ **Phase 5.5 thesis registry auto-wire (V2.14.0)**。Bundle 規範見 `investment/protocol_appendix_fmp_bundles.md` |
| `財報 [TICKER]` | `skills/earnings-analyst/SKILL.md` | FMP 三表 8Q + 品質 flag + 0-100 composite。Cache key (TICKER, last_earnings_date)。**V2.14.0 起 MD 報告強制 EDGAR / IR / FMP markdown clickable link**（見 SKILL.md Citations section）|
| `新聞分析 DIGEST` | `news/news_protocol_v2.md` | RSS -> Triage -> Debate |
| `新聞分析 FLASH [text]` | `news/news_protocol_v2.md` | Deep Debate only |
| `動能 [TICKER]` | `skills/momentum-monitor/scripts/momentum.py` | Score + Signals |
| `動能選股` | `skills/momentum-monitor/scripts/screen.py` | Universe Scan |
| `更新 journal` | `skills/momentum-monitor/scripts/journal.py` | Performance tracking |
| `財報前瞻 [TICKER]` (UI 自動觸發) | `skills/earnings-valuation-forecaster/scripts/forecast.py --pre-earnings` | **V2.15.0** — Dashboard `earnings.html` 卡片 + `calendar.html` upcoming earnings event 在 `next_earnings_source==='fmp_confirmed'` 且 days_until ≤ 7 時自動 morph 出「📋 前瞻」button。Server SCRIPT_PROTOCOLS 路徑（不走 Claude turn，直接 subprocess）|

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

## Break News (V3.9.4 — Auto, no trigger needed)

dashboard_server 開機後常駐 2 條 daemon thread：

| 元件 | 內容 |
|---|---|
| `break_news_poll_loop` (每 600s) | 跑 `scripts/break_news/poller.py`：抓 **9 個 RSS feed + Futu 牛牛推播 (US 限定，自動濾掉港股/中股/廣告) + 免費社群/趨勢源 (Reddit / Hacker News / Google Trends；Bluesky adapter 預設關閉，可用 `BREAK_NEWS_BLUESKY_ENABLED=1` 測試)** → stage1_triage 分數閘 (Futu 走 advance_reason=futu_news 旁路；社群源用更高 `BREAK_NEWS_SOCIAL_GATE_MIN_SCORE`，多數只進 Raw 流) → 候選依 `abs(shallow_score)` / binary / credibility / freshness 排序後才消耗 LLM 預算；admission 讀 Break News A/B voice 的實際 LLM quota headroom，扣 `pending_debate` backlog × `BREAK_NEWS_EST_CALLS_PER_DEBATE`(預設 6)，`BREAK_NEWS_SESSION_RESERVE` 以 call 為單位保留美股新聞時段額度；`BREAK_NEWS_DAILY_MAX_DEBATES>0` 僅作 emergency item ceiling → 寫 `news/break_news_logs/bn_<date>_<hash>.json` (state=`pending_debate`) |
| `break_news_debate_loop` | 掃描 `pending_debate` 條目 → `scripts/break_news/debater.py` 起 `claude` + `gemini` CLI 交替留言（max 3 rounds，`<DONE>` 或 `done:true` 收斂）→ entities / relations 寫入 `summary.merged_*` |
| `/break-news.html` | 即時 stream 卡片 + Claude × Gemini 對話 side panel + entity chips + replay button + 情緒趨勢圖（Market Consensus 只吃系統性/大盤新聞；Raw Pulse 分線，不污染 consensus） |
| `/api/break-news/{feed,item/<id>,state}` GET / `/refresh, /item/<id>/replay` POST | 只讀檢視 + manual 觸發；debate 用獨立 `_break_news_dispatch_lock`，**不**搶 `_protocol_lock`（normal `分析/產業掃描/新聞分析` 不會被擋） |

可手動跑：
```bash
python3 scripts/break_news/poller.py --once             # 單次 poll
python3 scripts/break_news/social_sources.py            # 檢查免費社群/趨勢源
python3 scripts/break_news/debater.py --news-id <id>    # 單條 debate
python3 scripts/break_news/validate.py                  # schema lint
```

**重點紀律**：Break News 為**探索層**，**不**影響 investment_protocol 決策。Claude × Gemini 是要刻意造成意見分歧，divergence_note 是訊號不是 bug。

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
python3 scripts/nexus/build_graph.py --tier 1,2 --dry-run                       # V3.0 Nexus graph: dry-run stats (no Tier 3 LLM)
python3 scripts/nexus/build_graph.py --tier 1,2,3 --full                        # V3.0 Nexus graph: full Tier 1+2+3 rebuild (needs ANTHROPIC_API_KEY)
python3 sector/scripts/sector_digest.py                                         # V1.4.1 sector: 1-call macro + 11-sector decision table (read-only)
python3 sector/scripts/build_sector_intel.py --date YYYY-MM-DD                  # V1.4.1 sector: assemble sector_intel.json from caches + decision JSON
```

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
