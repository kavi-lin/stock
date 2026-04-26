# AI 投資委員會 — Agent Execution Context

> **Version**: Sync `VERSION` file + `Dashboard/utils.js`. Full background in `README.md`.

## Protocol Triggers (中期 / 委員會層)

| Command | File | Notes |
|---|---|---|
| `產業掃描` | `sector/sector_protocol_main.md` | Multi-file (Phase 0-5) |
| `分析 [TICKER]` | `investment/investment_protocol_v4_8.md` | V4.8.1 Phase 1 含 dual_fetch；4 lane subagent + Burry + Red Team |
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

Detailed skills: `skills/MARKET_INDEX.md`. Architecture rationale: `plan_short.md`.

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
```

## Workflow Rules

### 1. Pre-implementation Confirmation
**Trigger**: Changes involving **≥ 2 files** OR single file **≥ 50 lines**.
**Format**: Output a summary table (File, Action, Est. Lines, Description) + total tokens. Wait for user "OK" to proceed.

### 2. Session Completion Checklist
**Definition**: Human-requested dev/refactor/fix is complete.
1. **Bump VERSION**: Sync `VERSION` + `Dashboard/utils.js`.
2. **Update SESSION_NOTES.md / TODO.md**: Tick done, update state, write `Last Session Note`.

**🚫 EXCLUSION**: Protocol runs (`產業掃描`, `分析 [TICKER]`, etc.) are **NOT** sessions. Do NOT bump version or modify todolist after protocol execution.
