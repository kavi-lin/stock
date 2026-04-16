---
name: short-contrarian-analyst
description: Burry-style valuation anchor and contrarian veto check for a single ticker. Computes Burry Score (0-100) from FCF yield, EV/EBIT, debt/equity, and price vs 52-week high. Use in investment protocol Phase 2 as the 5th agent — triggers T4 veto when Burry Score < 20 (extremely overvalued) on an otherwise bullish thesis.
---

# Short Contrarian Analyst (Burry)

## Purpose
Independent valuation anchor for investment protocol Phase 2. Unlike Bull/Bear/Sentiment/
Technical agents (which are weighted), this agent has **veto power** on T4 (overvaluation
veto) when Burry Score < 20 — forces the protocol into HOLD regardless of other bullish signals.

## Usage
```bash
python3 skills/short-contrarian-analyst/scripts/burry_score.py NVDA
python3 skills/short-contrarian-analyst/scripts/burry_score.py KO --json-only
```

## Burry Score components (0-100, higher = cheaper / safer)

| Metric | Weight | Scoring |
|---|---|---|
| FCF yield (FCF / EV) | 35% | < 2% → 10, 5% → 50, 10% → 90 |
| EV / EBIT | 25% | > 30 → 10, 15 → 50, < 8 → 90 |
| Debt / Equity | 15% | > 2 → 10, 1 → 50, < 0.3 → 90 |
| Price vs 52w high | 15% | at high → 20, -20% → 60, -40% → 90 |
| Insider activity | 10% | net buy → 80, neutral → 50, net sell → 20 |

Components missing → drop from weighted average (weights renormalize).

## Veto rules
- Burry Score `< 20` → **T4 veto active** → HOLD regardless of other agents
- Burry Score `< 35` → **warning flag** → Phase 4 position multiplier × 0.7
- Burry Score `>= 60` → deep value bonus → Phase 4 multiplier × 1.15

## Output schema
```json
{
  "ticker": "NVDA",
  "generated_at": "ISO8601",
  "burry_score": "float 0-100",
  "verdict": "T4_VETO | WARNING | NEUTRAL | VALUE_BONUS",
  "components": {
    "fcf_yield_pct": "float or null",
    "ev_ebit": "float or null",
    "debt_to_equity": "float or null",
    "pct_below_52w_high": "float",
    "insider_net": "BUY | SELL | NEUTRAL | UNKNOWN"
  },
  "component_scores": {"fcf_yield": 50, "ev_ebit": 30, ...},
  "reasoning": "string"
}
```
