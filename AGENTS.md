# AI 投資委員會 — Codex Agent Context
Codex should treat `CLAUDE.md` as the canonical project context. This file is the Codex-facing entry point and mirrors the current operating rules without replacing the deeper protocol docs.

## Protocol Triggers
| User trigger | Read first | Notes |
|---|---|---|
| `產業掃描` | `sector/sector_protocol_main.md` | Multi-phase sector protocol. |
| `分析 [TICKER]` | `investment/investment_protocol_v5_0.md` | V5.0 committee workflow, valuation blend, thesis registry. |
| `財報 [TICKER]` | `skills/earnings-analyst/SKILL.md` | FMP 8Q analysis, quality flags, clickable source links. |
| `新聞分析 DIGEST` / `FLASH` | `news/news_protocol_v2.md` | Digest uses RSS triage; flash runs deep debate only. |
| `動能 [TICKER]` | `skills/momentum-monitor/scripts/momentum.py` | Score and signals. |
| `動能選股` | `skills/momentum-monitor/scripts/screen.py` | Universe scan. |
| `更新 journal` | `skills/momentum-monitor/scripts/journal.py` | Momentum performance tracking. |
| `財報前瞻 [TICKER]` | `skills/earnings-valuation-forecaster/scripts/forecast.py --pre-earnings` | Script protocol for near-term earnings previews. |

## Decision Boundaries
- Tactical radar, Break News, and Nexus graph are exploration layers only. They must not change `investment_protocol` decisions, buy thresholds, or position sizing unless the protocol explicitly says so.
- `skills/short-term-target/config/weights.yaml` is manually calibrated by the user. Do not auto-overwrite it.
- Nexus Tier 3 LLM entities stay provisional until promoted by `CLAUDE.md` rules.
- Claude x Gemini Break News divergence is an intended signal.

## Validation Gates
Run the relevant validator and require `rc=0` before calling protocol output complete:
| Mode | Script | Schema |
|---|---|---|
| News | `news/scripts/validate_digest_output.py` | `news/digest_output_schema.md` |
| Sector | `sector/scripts/validate_sector_intel.py` | `sector/schema.md` |
| Invest | `investment/scripts/validate_session_export.py` | `investment/phase5_export_schema.md` |

## Useful Commands
```bash
./daily_update.sh
python3 skills/short-term-target/scripts/predict.py <TICKER>
python3 investment/scripts/backtest_postmortem.py
python3 skills/_shared/company_context.py <TICKER> --peers
python3 investment/scripts/register_thesis.py
python3 scripts/check_skills.py
python3 scripts/nexus/build_graph.py --tier 1,2 --dry-run
python3 sector/scripts/sector_digest.py
python3 sector/scripts/build_sector_intel.py --date YYYY-MM-DD
```

## Codex Workflow Rules
- Before edits, inspect local context and preserve unrelated dirty work. This repo often has many generated reports and caches.
- For changes involving 2+ files or a single file of 50+ lines, first present a concise table: file, action, estimated lines, description, plus total token estimate; wait for user OK.
- Use `rg` / `rg --files` for searches. Prefer existing project scripts and shared modules over new ad hoc logic.
- Treat `CLAUDE.md` as canonical until the protocol docs are made model-neutral.
- Protocol runs must preserve validator gates and the existing report/cache output paths.
- Never write API keys, environment values, or secrets into source, reports, logs, prompts, or generated artifacts.
- Be careful around `.env` and local config files; do not print or persist secret values.
- On human-requested dev/refactor/fix completion, follow `CLAUDE.md`: sync `VERSION`, `Dashboard/utils.js`, `CHANGELOG.md`, then update `SESSION_NOTES.md` / `TODO.md`.
- Protocol runs such as `產業掃描`, `分析 [TICKER]`, and `新聞分析` are not sessions. Do not bump version or update todo/session notes merely because a protocol ran.
- Keep reports in `reports/`; caches belong under the protocol or skill cache directories already used by the project.
