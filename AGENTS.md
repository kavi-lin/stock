# AI Investment Committee（AI 投資委員會） — Codex Agent Context
Codex should treat `CLAUDE.md` as the canonical project context. This file is the Codex-facing entry point and mirrors the current operating rules without replacing the deeper protocol docs.

## Protocol Triggers
The trigger table lives in `CLAUDE.md` (single source of truth — do NOT duplicate it here). Read `CLAUDE.md` § Protocol Triggers for the trigger → file mapping, then load the referenced protocol file.

## Decision Boundaries
- Tactical radar, Break News, and Nexus graph are exploration layers only. They must not change `investment_protocol` decisions, buy thresholds, or position sizing unless the protocol explicitly says so.
- `skills/short-term-target/config/weights.yaml` is manually calibrated by the user. Do not auto-overwrite it.
- Nexus Tier 3 LLM entities stay provisional until ≥3 independent reports corroborate them (rule in `CLAUDE.md` § 全域紀律).
- Claude x Gemini Break News divergence is an intended signal.

## Validation Gates
Run the relevant validator and require `rc=0` before calling protocol output complete:
| Mode | Script | Schema |
|---|---|---|
| News | `news/scripts/validate_digest_output.py` | `news/digest_output_schema.md` |
| Sector | `sector/scripts/validate_sector_intel.py` | `sector/schema.md` |
| Invest | `investment/scripts/validate_session_export.py` | `investment/phase5_export_schema.md` |

## Useful Commands
Full command reference: `docs/agent-ops/OPS_COMMANDS.md` (grouped by scenario, includes the engine-changed → test mapping).
```bash
./daily_update.sh   # daily routine
```

## Codex Workflow Rules
- Before edits, inspect local context and preserve unrelated dirty work. This repo often has many generated reports and caches.
- For changes involving 2+ files or a single file of 50+ lines, first present a concise table: file, action, estimated lines, description, plus total token estimate; wait for user OK. Exception: skip the confirmation when the user has explicitly authorized autonomous work in the current request (same rule as `CLAUDE.md` § Workflow Rules).
- Use `rg` / `rg --files` for searches. Prefer existing project scripts and shared modules over new ad hoc logic.
- Treat `CLAUDE.md` as canonical until the protocol docs are made model-neutral.
- Protocol runs must preserve validator gates and the existing report/cache output paths.
- Never write API keys, environment values, or secrets into source, reports, logs, prompts, or generated artifacts.
- Be careful around `.env` and local config files; do not print or persist secret values.
- On human-requested dev/refactor/fix completion, follow `CLAUDE.md`: sync `VERSION`, `Dashboard/utils.js`, `CHANGELOG.md`, then update `SESSION_NOTES.md` / `TODO.md`.
- Protocol runs such as `產業掃描`, `分析 [TICKER]`, and `新聞分析` are not sessions. Do not bump version or update todo/session notes merely because a protocol ran.
- Keep reports in `reports/`; caches belong under the protocol or skill cache directories already used by the project.

## Codex LLM Budget and Cross-Model Review Rules
Treat every LLM invocation as consuming a limited rolling five-hour quota and adding response latency. Correctness matters, but repeated model discussion is not a substitute for deterministic inspection, tests, or a clear owner decision.

### Default call policy
- Use local search, scripts, diffs, tests, validators, and static reasoning before asking another LLM. Do not call a second model for routine lookup, formatting, status checks, or findings that the code/tests can settle.
- Cross-model review is opt-in: use it only when the user explicitly requests it, a protocol requires it, or a high-risk unresolved judgment materially benefits from an independent model family.
- Use at most one reviewer model at a time. Do not launch parallel Claude/Gemini/Codex reviews of the same artifact unless the user explicitly requests independent samples after seeing the cost trade-off.
- Per task, the default cross-model budget is two inference turns total: one initial review and one consolidated follow-up containing all fixes, disagreements, and remaining questions. A third turn requires fresh user approval with a concise reason and estimated benefit.
- “Discuss until consensus” still uses the two-turn budget: resolve objective findings with code/tests locally, batch all disputed judgment calls into one follow-up, and report any remaining non-critical disagreement instead of continuing an open-ended debate.

### Five-hour window and waiting discipline
- Preserve quota for user-facing work across the rolling five-hour reset window; do not spend remaining quota on speculative review, duplicated summaries, or repeated reassurance.
- Never poll an LLM by sending prompts such as “status?”, “done?”, or the same request again. A resumed session is still an inference call and may resend/charge context.
- For a running CLI process, launch it once and wait through the existing process/session handle or inspect the OS process without invoking the model. Send no more than one user update per 60 seconds while waiting.
- On quota, authentication, or login errors, stop immediately. Do not retry in the same turn unless there is evidence the state changed. Report the blocker and continue with local deterministic work where possible.
- On timeout, first verify whether the original process is still alive. Retry at most once and only if it is confirmed dead; never start duplicate reviewers concurrently.

### Prompt and response budget
- Send the smallest review packet that can support the decision: objective, acceptance criteria, focused diff, relevant tests, and unresolved questions. Do not paste full chat history, entire repositories, generated reports, or raw logs when a focused excerpt or file path is enough.
- Target cross-model input at no more than roughly 8k tokens and output at no more than roughly 1.5k tokens. If more context is genuinely necessary, create a compact evidence file and ask the reviewer to read only named sections; exceeding about 15k input tokens requires user approval.
- Ask for findings in a bounded format: severity, file/line, evidence, fix. Prohibit restating the task, narrating the whole codebase, or rewriting unchanged material.
- Reuse a reviewer session only when prior context is essential. Otherwise use a fresh focused review to avoid repeatedly carrying a large conversation history.
- Images, screenshots, PDFs, and other multimodal inputs are allowed only when visual evidence is necessary; do not attach them to code or valuation review that can be resolved from text/data.

### Review convergence and stop conditions
- The implementation owner fixes objective defects once, then runs deterministic tests/validators before the follow-up review. Do not ask the reviewer to rediscover failures already covered by tests.
- A review is complete when critical/high findings are fixed or explicitly rejected with evidence and required validators pass. Cosmetic differences and model preference do not justify another inference turn.
- If the same disagreement survives two model turns, Codex must make and document an evidence-based decision or ask the user; it must not keep debating automatically.
- Keep a short call ledger in the active response when cross-model work is used: model/session, purpose, inference-turn count, and outcome. Waiting/polling must never increment the count because it must never invoke the model.
