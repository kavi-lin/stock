# AI 投資委員會 — Agent Execution Context

> **Version**: Sync `VERSION` file + `Dashboard/utils.js`. Full background in `README.md`.

## Protocol Triggers (中期 / 委員會層)

| Command | File | Notes |
|---|---|---|
| `產業掃描` | `sector/sector_protocol_main.md` | Multi-file (Phase 0-5) |
| `分析 [TICKER]` | `investment/investment_protocol_v5_0.md` | V5.0 — 5 lane subagent (含 Valuation Specialist) + Burry + Red Team + Phase 4.5 fair_value_summary（6 anchor weighted blend 給合理股價）。Bundle 規範見 `investment/protocol_appendix_fmp_bundles.md` |
| `財報 [TICKER]` | `skills/earnings-analyst/SKILL.md` | FMP 三表 8Q + 品質 flag + 0-100 composite。Cache key (TICKER, last_earnings_date) |
| `新聞分析 DIGEST` | `news/news_protocol_v2.md` | RSS -> Triage -> Debate |
| `新聞分析 FLASH [text]` | `news/news_protocol_v2.md` | Deep Debate only |
| `動能 [TICKER]` | `skills/momentum-monitor/scripts/momentum.py` | Score + Signals |
| `動能選股` | `skills/momentum-monitor/scripts/screen.py` | Universe Scan |
| `更新 journal` | `skills/momentum-monitor/scripts/journal.py` | Performance tracking |

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
# Steps: 1) Breadth → 2) FTD → 3) Top → 4) FRED → 5) Bridge → 6) Thematic Screener

# Tier 3 — Weekend manual (1-2 min)
python3 skills/short-term-target/scripts/weekly_review.py
# Output: reports/SHORT_TERM_WEEKLY_<DATE>.md

# Ad-hoc
python3 skills/short-term-target/scripts/predict.py <TICKER>          # 1d/5d/15d projection
python3 skills/finnhub-client/scripts/run_dual_fetch.sh --tickers X   # canonical scoring snapshot
python3 skills/finnhub-client/scripts/audit_drift_check.py            # Finnhub vs FMP drift
python3 investment/scripts/backtest_postmortem.py                     # protocol decisions backtest
python3 skills/_shared/company_context.py <TICKER> --peers            # shared profile/peers cache (24h TTL)
```

## Shared Modules

- `skills/_shared/company_context.py` — single source for FMP company-level metadata. Exports `SECTOR_UNIVERSE` / `TICKER_TO_SECTOR` / `SECTOR_TOP_5`（被 `sector/scripts/fetch_*.py` import）+ `get_profile/get_peers/get_market_cap_history/get_employee_history`（24h cache @ `skills/_shared/cache/`）。修改 mega-cap 名單請只改這一處。

## Workflow Rules

### 1. Pre-implementation Confirmation
**Trigger**: Changes involving **≥ 2 files** OR single file **≥ 50 lines**.
**Format**: Output a summary table (File, Action, Est. Lines, Description) + total tokens. Wait for user "OK" to proceed.

### 2. Session Completion Checklist
**Definition**: Human-requested dev/refactor/fix is complete.
1. **Bump VERSION**: Sync **three** locations together — `VERSION` file (純數字 `1.5.0`) + `Dashboard/utils.js` (`'V1.5.0'`) + **`CHANGELOG.md`** (新增 `## [x.y.z] — YYYY-MM-DD` 區塊，含 `### Changed/Added/Fixed` 條列 + `### Why` 動機；格式參考既有 v1.42.x 條目)。大改動 bump minor、小改動 bump patch。三處任一 desync 都不算完成。
2. **Update SESSION_NOTES.md / TODO.md**: Tick done, update state, write `Last Session Note`.

**🚫 EXCLUSION**: Protocol runs (`產業掃描`, `分析 [TICKER]`, etc.) are **NOT** sessions. Do NOT bump version or modify todolist after protocol execution.
