---
name: dual-axis-skill-reviewer
description: "Review skills in any project using a dual-axis method: (1) deterministic code-based checks (structure, scripts, tests, execution safety) and (2) LLM deep review findings. Use when you need reproducible quality scoring for `skills/*/SKILL.md`, want to gate merges with a score threshold (for example 90+), or need concrete improvement items for low-scoring skills. Works across projects via --project-root."
---

# Dual Axis Skill Reviewer

> **Upstream alignment**: fork 自 [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills)
> （MIT）。引入 **2026-08-08**（V4.113.4），上游版本 `b814274`。程式碼未改；SKILL.md 只移除了
> global-install 段（本 repo 為 vendored 副本）。
> 2026-08-08 稽核評為「立即可用」後只寫進 SESSION_NOTES 而未落地，兩個版本後才補——
> **評估結論若不落到 repo 或 TODO，就會靜默蒸發**。
>
> **本專案的計分注意事項**：auto 軸有三個子項檢查的是**上游的 SKILL.md 章節模板**
> （When to Use / Prerequisites / Workflow / Resources 四個標題 + `references/` 目錄）。
> 本 repo 的 SKILL.md 是另一套風格，所以這三項對本專案的 skill 一律扣分，
> **那是格式差異，不是品質問題**。對本專案真正有訊號的是 `execution_safety_reproducibility`
> 與 `test_health`。**讀 breakdown，不要只看總分。**

Run the dual-axis reviewer script and save reports to `reports/`.

The script supports:
- Random or fixed skill selection
- Auto-axis scoring with optional test execution
- LLM prompt generation
- LLM JSON review merge with weighted final score
- Cross-project review via `--project-root`

## When to Use

- Need reproducible scoring for one skill in `skills/*/SKILL.md`.
- Need improvement items when final score is below 90.
- Need both deterministic checks and qualitative LLM code/content review.
- Need to review skills in a **different project** from the command line.

## Prerequisites

- Python 3.9+
- `uv` (recommended — auto-resolves `pyyaml` dependency via inline metadata)
- For tests: `uv sync --extra dev` or equivalent in the target project
- For LLM-axis merge: JSON file that follows the LLM review schema (see Resources)

## Workflow

This repo vendors the skill, so the script is always at the in-repo path:

```bash
REVIEWER=skills/dual-axis-skill-reviewer/scripts/run_dual_axis_review.py
```

`uv run` is optional here — the repo already ships `pyyaml`, so plain `python3 "$REVIEWER"`
works and skips a dependency resolve on every invocation.

### Step 1: Run Auto Axis + Generate LLM Prompt

```bash
uv run "$REVIEWER" \
  --project-root . \
  --emit-llm-prompt \
  --output-dir reports/
```

When reviewing a different project, point `--project-root` to it:

```bash
uv run "$REVIEWER" \
  --project-root /path/to/other/project \
  --emit-llm-prompt \
  --output-dir reports/
```

### Step 2: Run LLM Review
- Use the generated prompt file in `reports/skill_review_prompt_<skill>_<timestamp>.md`.
- Ask the LLM to return strict JSON output.
- When running inside Claude Code, let Claude act as orchestrator: read the generated prompt, produce the LLM review JSON, and save it for the merge step.

### Step 3: Merge Auto + LLM Axes

```bash
uv run "$REVIEWER" \
  --project-root . \
  --skill <skill-name> \
  --llm-review-json <path-to-llm-review.json> \
  --auto-weight 0.5 \
  --llm-weight 0.5 \
  --output-dir reports/
```

### Step 4: Optional Controls

- Fix selection for reproducibility: `--skill <name>` or `--seed <int>`
- Review all skills at once: `--all`
- Skip tests for quick triage: `--skip-tests`
- Change report location: `--output-dir <dir>`
- Increase `--auto-weight` for stricter deterministic gating.
- Increase `--llm-weight` when qualitative/code-review depth is prioritized.

## Output

- `reports/skill_review_<skill>_<timestamp>.json`
- `reports/skill_review_<skill>_<timestamp>.md`
- `reports/skill_review_prompt_<skill>_<timestamp>.md` (when `--emit-llm-prompt` is enabled)

## Resources

- Auto axis scores metadata, workflow coverage, execution safety, artifact presence, and test health.
- Auto axis detects `knowledge_only` skills and adjusts script/test expectations to avoid unfair penalties.
- LLM axis scores deep content quality (correctness, risk, missing logic, maintainability).
- Final score is weighted average.
- If final score is below 90, improvement items are required and listed in the markdown report.
- Script: `skills/dual-axis-skill-reviewer/scripts/run_dual_axis_review.py`
- LLM schema: `references/llm_review_schema.md`
- Rubric detail: `references/scoring_rubric.md`
