---
name: portfolio-risk-manager
description: Calculates vol-adjusted position size cap and correlation-aware multiplier for a new candidate ticker given current holdings. Use in investment protocol Phase 4 Step 2 to compute safe position size before entry. Reads positions.json and yfinance data; no API key.
market: market-agnostic
scope: portfolio-level
data_sources: [positions.json, yfinance]
---

# Portfolio Risk Manager

## Purpose
Computes a safe position size cap for a new candidate ticker by:
1. **Vol scaling**: target daily portfolio vol budget (default 0.6%) / ticker's daily vol = raw size %
2. **Correlation multiplier**: reduce if candidate highly correlated with existing large positions
3. **Sector concentration cap**: hard cap if candidate's sector already > 30% of portfolio

## Usage
```bash
python3 skills/portfolio-risk-manager/scripts/risk_manager.py NVDA
python3 skills/portfolio-risk-manager/scripts/risk_manager.py NVDA --vol-budget 0.8
python3 skills/portfolio-risk-manager/scripts/risk_manager.py CRWV --json-only
python3 skills/portfolio-risk-manager/scripts/risk_manager.py CRWV --positions /path/to/positions.json
```

`--positions` defaults to `<repo root>/positions.json` — resolved against the repo, not the
CWD, so a run from a subdirectory sees the same portfolio the protocol does. Missing file →
runs standalone (vol-scaling only, correlation multiplier 1.0). An explicit relative path is
still resolved against the CWD.

Failure → `{"error", "ticker"}` on stdout + exit 1. The consumer
(`trade_plan_builder.compute_step2`, `:355-370`) reads that and falls back to
`RULE_BASED` base 0.05 (protocol `:1310-1313`).

> **Known limitation — vol-scaling is currently inert.** `raw_cap = vol_budget / daily_vol × 100`
> is clipped by a hard 20% ceiling (`risk_manager.py:106-107`), and at the default 0.6% budget
> any ticker with daily vol ≤ 3% (≈48% annualized) pins to exactly 20.0. That covers nearly
> every normal equity — NVDA at 38.6% annualized vol still returns 20.0 — so in practice the
> correlation multiplier is the only live differentiator. Fixing this changes position sizing
> for real, so it is deferred to a user-approved decision (`docs/plan_risk_trio.md` B1).

## Output schema
```json
{
  "ticker": "NVDA",
  "generated_at": "ISO8601",
  "inputs": {
    "vol_budget_pct": 0.6,
    "positions_loaded": 5,
    "candidate_sector": "Technology"
  },
  "ticker_stats": {
    "daily_vol_pct": "float",
    "ann_vol_pct": "float",
    "avg_correlation_with_portfolio": "float -1 to 1"
  },
  "raw_vol_adjusted_cap_pct": "float — vol-only cap",
  "correlation_multiplier": "float 0.5-1.0",
  "sector_cap_triggered": "true | false",
  "final_position_cap_pct": "float — apply this to base Kelly / Phase 4 size",
  "reasoning": "string",
  "warnings": ["string — key present ONLY when something degraded"]
}
```

## Caps table
| Correlation avg | Multiplier |
|---|---|
| < 0.3 | 1.00 |
| 0.3 – 0.6 | 0.85 |
| 0.6 – 0.8 | 0.70 |
| > 0.8 | 0.55 |

Sector concentration > 30% → `sector_cap_triggered=true`, final cap × 0.5 extra penalty.

The sector check needs a price for **every** holding. If any holding fails to fetch, the
check is disarmed for that run (no cap, `warnings[]` names the tickers) rather than computed
on a partial denominator — dropping holdings shrinks `portfolio_value` and inflates the
exposure ratio, so a network blip could fire the ×0.5 penalty on a portfolio that never
breached 30%. Under-punish rather than mis-punish.
