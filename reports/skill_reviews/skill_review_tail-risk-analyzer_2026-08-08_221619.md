# Dual-Axis Skill Review

- Generated at: 2026-08-08 22:16:19
- Selected skill: `tail-risk-analyzer`
- Skill file: `skills/tail-risk-analyzer/SKILL.md`
- Skill type: `execution_or_hybrid`
- Selection mode: `manual`
- Seed: `None`
- Auto score: **72 / 100**
- LLM score: **78 / 100**
- Final score: **75 / 100**

## Auto Score Breakdown
- metadata_use_case: 20
- workflow_coverage: 5
- execution_safety_reproducibility: 21
- supporting_artifacts: 6
- test_health: 20

## Score Weights
- auto_weight: 0.50
- llm_weight: 0.50

## Findings (Combined)
1. [AUTO|MEDIUM] `skills/tail-risk-analyzer/SKILL.md` - Missing section: `## When to Use`.
2. [AUTO|MEDIUM] `skills/tail-risk-analyzer/SKILL.md` - Missing section: `## Prerequisites`.
3. [AUTO|MEDIUM] `skills/tail-risk-analyzer/SKILL.md` - Missing section: `## Workflow`.
4. [AUTO|MEDIUM] `skills/tail-risk-analyzer/SKILL.md` - Missing section: `## Resources`.
5. [AUTO|MEDIUM] `skills/tail-risk-analyzer/SKILL.md` - No markdown reference files found in `references/`.
6. [LLM|MEDIUM] `skills/tail-risk-analyzer/scripts/tail_risk.py:66` - The five normalizer constants are labelled 'Calibrated 2026-04' but nothing re-checks them. Four months on there is no drift alarm, and B7 concluded they still look healthy only because someone happened to sample 16 tickers by hand.
7. [LLM|MEDIUM] `skills/tail-risk-analyzer/scripts/tail_risk.py:37` - V4.113.3 measured |Δscore| up to 0.40 from the technical_core migration while the closest sample sat 0.60 from a band edge. The zero-flip gate passed, but any ticker within 0.4 of 30 or 60 will flip on a data-source change, and nothing surfaces that a result is band-marginal.
8. [LLM|LOW] `skills/tail-risk-analyzer/scripts/tail_risk.py:36` - No caching. Every invocation refetches a full year of history, and the investment protocol calls this per candidate on top of the other lanes.
9. [LLM|LOW] `skills/tail-risk-analyzer/SKILL.md` - Does not follow the reviewer's expected template (no When to Use / Prerequisites / Workflow / Resources, no references/). This is a deliberate house-style difference, but it means the auto axis scores document structure rather than skill quality.

## Test Verification (Auto Axis)
- Status: `passed`
- Command: `uv run --extra dev pytest /Users/kavi/Developer/Claude/Projects/ai-investment-committee/skills/tail-risk-analyzer/scripts/tests -q`

## Improvement Items (Final Score < 90)
1. Missing section: `## When to Use`. -> Add `## When to Use` to improve operator guidance.
2. Missing section: `## Prerequisites`. -> Add `## Prerequisites` to improve operator guidance.
3. Missing section: `## Workflow`. -> Add `## Workflow` to improve operator guidance.
4. Missing section: `## Resources`. -> Add `## Resources` to improve operator guidance.
5. No markdown reference files found in `references/`. -> Add methodology/reference docs to support consistent interpretation.
6. The five normalizer constants are labelled 'Calibrated 2026-04' but nothing re-checks them. Four months on there is no drift alarm, and B7 concluded they still look healthy only because someone happened to sample 16 tickers by hand. -> Add a cheap distribution check that can be run periodically (e.g. score a fixed cohort and assert the ROBUST/MODERATE/FRAGILE split stays within expected bounds), or record the reference distribution in references/ so drift is detectable without re-deriving it.
7. V4.113.3 measured |Δscore| up to 0.40 from the technical_core migration while the closest sample sat 0.60 from a band edge. The zero-flip gate passed, but any ticker within 0.4 of 30 or 60 will flip on a data-source change, and nothing surfaces that a result is band-marginal. -> Emit a `band_margin` field (distance to the nearest band edge) so consumers can tell a confident MODERATE from one that is 0.2 points from FRAGILE.
8. No caching. Every invocation refetches a full year of history, and the investment protocol calls this per candidate on top of the other lanes. -> Reuse the 24h cache pattern from skills/_shared/company_context.py; the input (ticker, lookback, trading day) is a natural cache key.
9. Does not follow the reviewer's expected template (no When to Use / Prerequisites / Workflow / Resources, no references/). This is a deliberate house-style difference, but it means the auto axis scores document structure rather than skill quality. -> Either adopt the four headings or record the deviation once in skills/MARKET_INDEX.md so future reviews do not re-report it as a defect.
