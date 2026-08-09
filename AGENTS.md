# AI Investment Committee（AI 投資委員會） — Codex / Grok Agent Context

**This file is self-sufficient.** Codex and Grok both auto-load it (probed
2026-08-09), and the generated section at the bottom carries the trigger table,
the exploration-layer boundaries, the validator gates, and the workflow rules
verbatim from `CLAUDE.md`. You do not need to open `CLAUDE.md` or `GEMINI.md`
to route or run a protocol — go straight from the trigger to the protocol doc
it names.

`CLAUDE.md` remains the single *written* source for those sections; they are
mirrored here by `scripts/sync_agent_context.py`, so edit them there.

## Useful Commands
Full command reference: `docs/agent-ops/OPS_COMMANDS.md` (grouped by scenario, includes the engine-changed → test mapping).
```bash
./daily_update.sh   # daily routine
```

## Codex / Grok Specific Rules
The shared workflow rules (confirmation table, session-close checklist, "a
protocol run is not a dev session") are in the generated section below — these
are the additions that only apply to these two CLIs.

- Before edits, inspect local context and preserve unrelated dirty work. This repo often has many generated reports and caches.
- Use `rg` / `rg --files` for searches. Prefer existing project scripts and shared modules over new ad hoc logic.
- Protocol runs must preserve validator gates and the existing report/cache output paths.
- Never write API keys, environment values, or secrets into source, reports, logs, prompts, or generated artifacts.
- Be careful around `.env` and local config files; do not print or persist secret values.
- Keep reports in `reports/`; caches belong under the protocol or skill cache directories already used by the project.
- Work only inside the current working directory. Paths outside it (the home directory, `~/Documents`, `~/Stock`, another CLI's state directory) are not this project.

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

<!-- BEGIN generated from CLAUDE.md — do not edit by hand -->

> **本區塊由 `scripts/sync_agent_context.py` 從 `CLAUDE.md` 生成，不要手改。**
> 本檔是 Codex 與 Grok 共用的 context 檔（兩者實測都會自動載入，2026-08-09）。
> 你只需要這一個 context 檔 —— 不必去讀 `CLAUDE.md` 或 `GEMINI.md`。

## Protocol Triggers（中期 / 委員會層）

| 指令 | 先讀這個檔 | 一句話紀律 |
|---|---|---|
| `產業掃描` | `sector/sector_protocol_main.md` | 主檔載入 phase_0 / phase_1-2-3 / phase_4-5 子檔 |
| `分析 [TICKER]` | `investment/investment_protocol_v5_0.md` | 5 lane subagent + Red Team；數字全走 script 禁手算；FMP bundle 規範見 `investment/protocol_appendix_fmp_bundles.md` |
| `財報 [TICKER]` | `skills/earnings-analyst/SKILL.md` | Cache key = (TICKER, last_earnings_date)；MD 報告必附 EDGAR/IR/FMP clickable link（規則在 SKILL.md Citations） |
| `新聞分析 DIGEST` | `news/news_protocol_v2.md` | RSS → deterministic triage → debate |
| `新聞分析 FLASH [text]` | `news/news_protocol_v2.md` | Deep Debate only |
| `動能 [TICKER]` / `動能選股` / `更新 journal` | `skills/momentum-monitor/scripts/` 的 momentum.py / screen.py / journal.py | 直接跑 script |
| `ic-memo [TICKER]`（或 `分析 --memo`） | `skills/ic-memo-writer/SKILL.md` | Deterministic renderer（0 LLM）；不重評分、不改 history.json |
| `首次覆蓋 [TICKER]`（或 `分析 --initiation`） | `skills/ic-memo-writer/SKILL.md`（`template_initiation.md`） | Deterministic renderer；前置 = history entry + valuation-modeler cache；validator `--initiation` rc=0/2 |
| `估值模型 [TICKER]` / `同業比較 [TICKER]` | `skills/valuation-modeler/SKILL.md` | 直接跑 dcf.py / comps.py；數字全 script；餵 protocol 的 dcf_self_built / comps_implied anchor |
| `財報前瞻 [TICKER]` | （UI 自動觸發，server subprocess，不走 Claude turn） | 手動版指令見 `docs/agent-ops/OPS_COMMANDS.md` §2 |
| `回測 [TICKER]` | （UI 自動觸發，server subprocess，不走 Claude turn） | 探索層；手動版見 `docs/agent-ops/OPS_COMMANDS.md` §2；細節 `skills/quant-backtest/SKILL.md` |

## 自動層（無需觸發，直接讀輸出檔）

| 層 | 輸出在哪 | 細節文件 |
|---|---|---|
| 戰術雷達（1-15 天） | `skills/thematic-screener/data/recommendations/<DATE>.json` | `skills/MARKET_INDEX.md`、`docs/plan_short.md` |
| Break News（daemon） | `news/break_news_logs/bn_*.json`、`/break-news.html` | 手動指令 `docs/agent-ops/OPS_COMMANDS.md` §6 |
| Nexus 知識圖譜／主動供應鏈 Radar | `Dashboard/nexus_graph.json`、`nexus_topics.json`、`nexus_quality.json`、`nexus/claim_ledger.jsonl`、`/graph.html` | `docs/agent-ops/OPS_COMMANDS.md` §5 |
| Link Digest（News 頁貼 URL） | `reports/*_link_digest.md` + judgment.json | `news/link_digest_protocol.md` |

**全域紀律（不可違反）**：以上自動層 + 回測全部是**探索層**——產出**永不**進入 investment_protocol 的決策（buy_threshold / position_size / verdict）。Break News 的 Claude × Gemini 分歧是刻意設計，divergence_note 是訊號不是 bug。Nexus Tier 3 LLM 找到的新實體先標 `provisional`，需 ≥3 份獨立報告才晉升一級節點。`skills/short-term-target/config/weights.yaml` 只由使用者手動校準，任何 agent 不得自動覆寫。

## Validator Gates（protocol 收尾必 rc=0）

| Mode | Script | Schema |
|---|---|---|
| News | `news/scripts/validate_digest_output.py` | `news/digest_output_schema.md` |
| Sector | `sector/scripts/validate_sector_intel.py` | `sector/schema.md` |
| Invest | `investment/scripts/validate_session_export.py` | `investment/phase5_export_schema.md` |

## Workflow Rules（dev/refactor/fix session）

1. **動工前確認**：改動 ≥2 檔或單檔 ≥50 行 → 先輸出摘要表（File / Action / Est. Lines / Description），等使用者「OK」。使用者已在本輪明確授權自主作業時免確認。
2. **收尾 checklist**：(a) 三處版本同步並跑 MAINTENANCE.md 的驗證命令；(b) 按 MAINTENANCE.md 的讀寫規則更新 `SESSION_NOTES.md` / `TODO.md`（禁止整檔 Read）；(c) 改了引擎 → 跑 `OPS_COMMANDS.md` §7 對應測試 rc=0；(d) 收尾殘留掃描 + 靜默綠防線 —— `MAINTENANCE.md` §2b / §2c。
3. **🚫 排除**：protocol 執行（`產業掃描`、`分析` 等）不是 dev session——不 bump 版本、不動 todolist。

<!-- END generated from CLAUDE.md -->
