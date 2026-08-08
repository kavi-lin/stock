# Dual-Axis Skill Review

- Generated at: 2026-08-08 22:16:20
- Selected skill: `short-contrarian-analyst`
- Skill file: `skills/short-contrarian-analyst/SKILL.md`
- Skill type: `execution_or_hybrid`
- Selection mode: `manual`
- Seed: `None`
- Auto score: **72 / 100**
- LLM score: **74 / 100**
- Final score: **73 / 100**

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
1. [LLM|HIGH] `skills/short-contrarian-analyst/scripts/burry_score.py:62` - get_insider_net() flattens each yfinance row to a string and substring-matches 'buy'/'purchase'/'sale'/'sell'. It carries 10% of the score and will silently degrade to UNKNOWN on any upstream column change — fail-safe, but it can also mislabel: a row containing the word 'Sale' in an unrelated field votes SELL.
2. [AUTO|MEDIUM] `skills/short-contrarian-analyst/SKILL.md` - Missing section: `## When to Use`.
3. [AUTO|MEDIUM] `skills/short-contrarian-analyst/SKILL.md` - Missing section: `## Prerequisites`.
4. [AUTO|MEDIUM] `skills/short-contrarian-analyst/SKILL.md` - Missing section: `## Workflow`.
5. [AUTO|MEDIUM] `skills/short-contrarian-analyst/SKILL.md` - Missing section: `## Resources`.
6. [AUTO|MEDIUM] `skills/short-contrarian-analyst/SKILL.md` - No markdown reference files found in `references/`.
7. [LLM|MEDIUM] `skills/short-contrarian-analyst/SKILL.md` - burry_voice and veto_flag are required by the Phase 2 JSON contract but are produced by the PM, not this script. The split is documented in prose only; nothing fails if the PM omits them.
8. [LLM|MEDIUM] `skills/short-contrarian-analyst/scripts/burry_score.py:93` - The `ev_ebit` key holds EV/EBITDA. This is documented and the key is frozen for history compatibility, but every downstream reader that trusts the name compares against EV/EBIT thresholds, which are systematically stricter.
9. [LLM|LOW] `skills/short-contrarian-analyst/scripts/burry_score.py:87` - The FCF fallback substitutes OpCF x 0.85 when freeCashflow is missing or negative. The 15% capex assumption is hard-coded and unlabelled in the output, so a fabricated FCF is indistinguishable from a reported one.

## Test Verification (Auto Axis)
- Status: `passed`
- Command: `uv run --extra dev pytest /Users/kavi/Developer/Claude/Projects/ai-investment-committee/skills/short-contrarian-analyst/scripts/tests -q`

## Improvement Items (Final Score < 90)
1. get_insider_net() flattens each yfinance row to a string and substring-matches 'buy'/'purchase'/'sale'/'sell'. It carries 10% of the score and will silently degrade to UNKNOWN on any upstream column change — fail-safe, but it can also mislabel: a row containing the word 'Sale' in an unrelated field votes SELL. -> Parse the transaction-type column explicitly and treat an unrecognized schema as UNKNOWN. B5 measured only 67% agreement with FMP's insider statistics, so the current reading is not obviously trustworthy either way.
2. Missing section: `## When to Use`. -> Add `## When to Use` to improve operator guidance.
3. Missing section: `## Prerequisites`. -> Add `## Prerequisites` to improve operator guidance.
4. Missing section: `## Workflow`. -> Add `## Workflow` to improve operator guidance.
5. Missing section: `## Resources`. -> Add `## Resources` to improve operator guidance.
6. No markdown reference files found in `references/`. -> Add methodology/reference docs to support consistent interpretation.
7. burry_voice and veto_flag are required by the Phase 2 JSON contract but are produced by the PM, not this script. The split is documented in prose only; nothing fails if the PM omits them. -> Have validate_session_export assert both fields whenever burry_score is present, so the contract is machine-enforced rather than convention.
8. The `ev_ebit` key holds EV/EBITDA. This is documented and the key is frozen for history compatibility, but every downstream reader that trusts the name compares against EV/EBIT thresholds, which are systematically stricter. -> Add an `ev_metric: "EV/EBITDA"` sibling field so consumers can branch on the actual metric instead of inferring it from a name that lies.
9. The FCF fallback substitutes OpCF x 0.85 when freeCashflow is missing or negative. The 15% capex assumption is hard-coded and unlabelled in the output, so a fabricated FCF is indistinguishable from a reported one. -> Flag the substitution in components (e.g. fcf_source: reported|estimated) — it drives the heaviest-weighted component at 35%.
