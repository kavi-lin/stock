# SECTOR_ROTATION_GUIDE — LLM instruction set

## SCHEMA
sector_rotation has TWO layers. Always read both before concluding.

```
favor       → base sectors for this regime (static)
adjustments → list of override rules triggered by current macro values (may be empty)
```

## RULE 1 — adjustments overrides favor
If adjustments is non-empty:
- sectors in any adjustment.lower → deprioritise even if in favor
- sectors in any adjustment.raise → consider even if not in favor
- do NOT simply repeat favor list as final recommendation

## RULE 2 — conflict resolution
Multiple adjustments may conflict (e.g. real_rate_high raises Financials, credit_stress lowers Financials).
Priority order (highest first):
  1. credit_stress_elevated
  2. yield_curve_inverted
  3. real_rate_high
  4. yield_curve_steep

Higher-priority adjustment wins on the conflicting sector.

## RULE 3 — output format
Always state: base regime → active adjustments → net conclusion.
Example:
  "Soft Landing (base: favor Tech/Industrials) + real_rate_high overlay →
   net: favor Industrials/Financials/Energy; Tech deprioritised despite base"

## RULE 4 — empty adjustments
adjustments: [] means base map is valid as-is. Use favor directly.
