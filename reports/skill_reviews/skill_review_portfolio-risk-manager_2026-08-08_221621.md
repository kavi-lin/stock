# Dual-Axis Skill Review

- Generated at: 2026-08-08 22:16:21
- Selected skill: `portfolio-risk-manager`
- Skill file: `skills/portfolio-risk-manager/SKILL.md`
- Skill type: `execution_or_hybrid`
- Selection mode: `manual`
- Seed: `None`
- Auto score: **72 / 100**
- LLM score: **70 / 100**
- Final score: **71 / 100**

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
1. [LLM|HIGH] `skills/portfolio-risk-manager/scripts/risk_manager.py:110` - vol-scaling is effectively inert. At the default 0.6%/day budget the 20% ceiling binds for any daily vol <= 3.0%, and back-solving 47 historical trades showed the implied base clustering on the ceiling lattice (0.140 appears 8 times) with only ~6-8 trades ever escaping it. A caller reading 'vol_adjusted_limit_pct' reasonably believes volatility sized the position; it did not.
2. [AUTO|MEDIUM] `skills/portfolio-risk-manager/SKILL.md` - Missing section: `## When to Use`.
3. [AUTO|MEDIUM] `skills/portfolio-risk-manager/SKILL.md` - Missing section: `## Prerequisites`.
4. [AUTO|MEDIUM] `skills/portfolio-risk-manager/SKILL.md` - Missing section: `## Workflow`.
5. [AUTO|MEDIUM] `skills/portfolio-risk-manager/SKILL.md` - Missing section: `## Resources`.
6. [AUTO|MEDIUM] `skills/portfolio-risk-manager/SKILL.md` - No markdown reference files found in `references/`.
7. [LLM|MEDIUM] `skills/portfolio-risk-manager/scripts/risk_manager.py:126` - One unpriceable holding disarms the sector check for the entire portfolio. That is the right direction (better to under-punish than mis-punish), but it is coarse: a 20-position portfolio loses concentration protection because a single ticker failed to fetch.
8. [LLM|MEDIUM] `skills/portfolio-risk-manager/scripts/risk_manager.py:22` - load_positions() accepts anything shaped roughly like a position and coerces silently: a missing shares field becomes 0.0, so a malformed entry contributes zero exposure and quietly weakens the sector denominator instead of being reported.
9. [LLM|LOW] `skills/portfolio-risk-manager/scripts/risk_manager.py:132` - The sector loop is serial with no cache: one yf.Ticker per holding, .info plus .history each. For a 20-name portfolio that is 20 sequential round trips on every candidate evaluation.

## Test Verification (Auto Axis)
- Status: `passed`
- Command: `uv run --extra dev pytest /Users/kavi/Developer/Claude/Projects/ai-investment-committee/skills/portfolio-risk-manager/scripts/tests -q`

## Improvement Items (Final Score < 90)
1. vol-scaling is effectively inert. At the default 0.6%/day budget the 20% ceiling binds for any daily vol <= 3.0%, and back-solving 47 historical trades showed the implied base clustering on the ceiling lattice (0.140 appears 8 times) with only ~6-8 trades ever escaping it. A caller reading 'vol_adjusted_limit_pct' reasonably believes volatility sized the position; it did not. -> Either lower the default budget so the formula has range, or rename the output to reflect what it is (a correlation-adjusted cap). Leaving an accurate-sounding name on an inert computation is the more expensive of the two failure modes.
2. Missing section: `## When to Use`. -> Add `## When to Use` to improve operator guidance.
3. Missing section: `## Prerequisites`. -> Add `## Prerequisites` to improve operator guidance.
4. Missing section: `## Workflow`. -> Add `## Workflow` to improve operator guidance.
5. Missing section: `## Resources`. -> Add `## Resources` to improve operator guidance.
6. No markdown reference files found in `references/`. -> Add methodology/reference docs to support consistent interpretation.
7. One unpriceable holding disarms the sector check for the entire portfolio. That is the right direction (better to under-punish than mis-punish), but it is coarse: a 20-position portfolio loses concentration protection because a single ticker failed to fetch. -> Compute the ratio over the priced subset and only disarm when the unpriced weight could change the verdict — i.e. when best case and worst case for the missing holdings straddle the 30% threshold.
8. load_positions() accepts anything shaped roughly like a position and coerces silently: a missing shares field becomes 0.0, so a malformed entry contributes zero exposure and quietly weakens the sector denominator instead of being reported. -> Count and report skipped/degenerate entries in warnings[] — the same failure-path-only convention the sector check already uses.
9. The sector loop is serial with no cache: one yf.Ticker per holding, .info plus .history each. For a 20-name portfolio that is 20 sequential round trips on every candidate evaluation. -> Route sector metadata through skills/_shared/company_context.py, which already provides the same data with a 24h cache.
