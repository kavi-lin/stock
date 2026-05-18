# Plan: Support Codex Runner

## Current Findings

- Skills structure check passes: `python3 scripts/check_skills.py --strict`.
- Dashboard protocol execution is still Claude-only: `dashboard_server.py` spawns `claude -p`.
- Break News exposes `codex` in config plumbing, but `scripts/break_news/llm_drivers.py::run_codex()` is a graceful failure stub.
- Core protocol docs assume Claude Code tool names and behavior: `Agent`, `Write`, `Edit`, `Read`, `WebFetch`, `WebSearch`.
- Several live scripts/docs still reference `~/.claude/skills/...`, which can drift from repo-local `skills/...`.
- `AGENTS.md` exists for Codex, but it is not yet fully synchronized with `GEMINI.md` safety notes or all current triggers.

## TODO

### P0 — Codex Entry Rules

- [x] Sync missing safety rules from `GEMINI.md` into `AGENTS.md`.
- [x] Add `財報前瞻 [TICKER]` trigger to `AGENTS.md`.
- [x] Add `更新 journal` trigger to `AGENTS.md`.
- [x] Add explicit Codex rule: protocol runs preserve validator gates and report/cache output paths.
- [x] Add explicit Codex rule: never write API keys, env values, or secrets to logs/files.
- [x] Document that `CLAUDE.md` remains canonical until protocol docs are made model-neutral.

### P1 — Break News Codex Runner

- [x] Verify Codex CLI non-interactive flags.
- [x] Verify Codex CLI JSON or machine-readable output shape.
- [x] Implement `run_codex()` in `scripts/break_news/llm_drivers.py`.
- [x] Parse Codex output into the existing `LLMResult` contract.
- [x] Preserve timeout, missing-binary, and parse-failure handling.
- [x] Make `python3 scripts/break_news/llm_drivers.py --probe --agent codex` return rc=0.
- [ ] Keep Claude and Gemini probe behavior unchanged. Current env check: Claude CLI is not logged in; Gemini probe timed out at 120s.

### P2 — Dashboard Protocol Runner Registry

- [ ] Replace Claude-only subprocess construction in `dashboard_server.py::run_protocol()` with a model-dispatch runner.
- [ ] Reuse `config/llm_config.json` `primary` model for protocol execution.
- [ ] Preserve Claude as the default when config is missing or invalid.
- [ ] Add Codex-specific command construction, timeout handling, and output parsing.
- [ ] Keep `SCRIPT_PROTOCOLS` path unchanged for pure Python protocols.
- [ ] Enable Dashboard Codex option only after Codex smoke tests pass.
- [ ] Ensure protocol queue status, logs, cancel behavior, and validators still work.

### P3 — Protocol Compatibility

- [ ] Add Codex execution notes to `investment/investment_protocol_v5_0.md`.
- [ ] Add Codex execution notes to `sector/sector_protocol_main.md`.
- [ ] Add Codex execution notes to `news/news_protocol_v2.md`.
- [ ] Define mapping from Claude `Read` / `Write` / `Edit` terminology to Codex file-read and patch workflow.
- [ ] Define mapping from Claude `WebSearch` / `WebFetch` terminology to Codex browsing workflow.
- [ ] Define fallback for Claude `Agent(...)` requirements under Codex.
- [ ] Decide how Codex may satisfy `subagent_isolated: true` when subagent spawning is unavailable or not user-authorized.
- [ ] Preserve existing validator gates and schema contracts without loosening them.
- [ ] Document degraded-mode reporting when Codex cannot perform required subagent isolation.

### P4 — Path Cleanup

- [ ] Replace live `~/.claude/skills/...` script references with repo-local `skills/...` where possible.
- [ ] Update `daily_update.sh` to prefer repo-local skill scripts.
- [ ] Update sector protocol docs that still recommend `.claude` skill paths.
- [ ] Add a helper resolver only if both repo-local and user-global skill paths must remain supported.
- [ ] Avoid editing archived protocol docs unless historical cleanup is explicitly requested.
- [ ] Verify path cleanup does not change generated cache locations unexpectedly.

### P5 — Verification

- [ ] Run `python3 scripts/check_skills.py --strict`.
- [ ] Run `python3 scripts/break_news/llm_drivers.py --probe --agent codex`.
- [ ] Run `python3 scripts/break_news/llm_drivers.py --probe --agent claude`.
- [ ] Run `python3 scripts/break_news/llm_drivers.py --probe --agent gemini`.
- [ ] Confirm Dashboard protocol queue still works with default Claude config.
- [ ] Confirm Codex config fails clearly instead of hanging when unsupported.
- [ ] Run relevant protocol validators after any protocol-output behavior change.

## Acceptance Criteria

- Codex can be selected as a configured LLM without immediate stub failure.
- Break News Codex probe returns rc=0 and parseable JSON.
- Dashboard protocol runner no longer hardcodes Claude as the only protocol execution engine.
- Existing Claude and Gemini paths remain backward compatible.
- Three primary protocols document Codex-compatible execution semantics.
- Live skill script paths prefer repo-local `skills/...`.
- Skills lint remains clean in strict mode.

## Notes

- This plan is intentionally split so P0/P1 can land before changing the higher-risk Dashboard protocol runner.
- Protocol runs remain analysis/report generation and should not trigger version bump or TODO/session updates by themselves.
- Runtime implementation changes should still follow the project completion checklist in `CLAUDE.md`.
