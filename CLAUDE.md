# AI 投資委員會 — Agent Execution Context

> **Version**: Sync `VERSION` file + `Dashboard/utils.js`. Full background in `README.md`.

## Protocol Triggers

| Command | File | Notes |
|---|---|---|
| `產業掃描` | `sector/sector_protocol_main.md` | Multi-file (Phase 0-5) |
| `分析 [TICKER]` | `investment/investment_protocol_v4_8.md` | Blind Analyst subagents |
| `新聞分析 DIGEST` | `news/news_protocol_v2.md` | RSS -> Triage -> Debate |
| `新聞分析 FLASH [text]` | `news/news_protocol_v2.md` | Deep Debate only |
| `動能 [TICKER]` | `skills/momentum-monitor/scripts/momentum.py` | Score + Signals |
| `動能選股` | `skills/momentum-monitor/scripts/screen.py` | Universe Scan |
| `更新 journal` | `skills/momentum-monitor/scripts/journal.py` | Performance tracking |

Detailed skills: `skills/MARKET_INDEX.md`.

## Validator Gates (Must be rc=0)

| Mode | Script | Schema |
|---|---|---|
| News | `news/scripts/validate_digest_output.py` | `news/digest_output_schema.md` |
| Sector | `sector/scripts/validate_sector_intel.py` | `sector/schema.md` |
| Invest | `investment/scripts/validate_session_export.py` | `investment/phase5_export_schema.md` |

## Output Paths

- **Reports**: `reports/` (`YYYYMMDD_TICKER.md`, `YYYY-MM-DD_sector_report.md`, etc.)
- **Caches**: `sector/logs/`, `investment/invest_logs/`, `news/news_logs/`, `skills/*/cache/`

## Ops Shortcut

```bash
./daily_update.sh   # Run Breadth -> FTD -> Top -> FRED cache -> Bridge
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
