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
python3 skills/portfolio-risk-manager/scripts/risk_manager.py NVDA --max-cap 10   # 見下方 Known limitation
```

`--positions` defaults to `<repo root>/positions.json` — resolved against the repo, not the
CWD, so a run from a subdirectory sees the same portfolio the protocol does. Missing file →
runs standalone (vol-scaling only, correlation multiplier 1.0). An explicit relative path is
still resolved against the CWD.

Failure → `{"error", "ticker"}` on stdout + exit 1. The consumer
(`trade_plan_builder.compute_step2`, `:355-370`) reads that and falls back to
`RULE_BASED` base 0.05 (protocol `:1310-1313`).

> **Known limitation — vol-scaling only acts inside a narrow slit.**
> `raw_cap = vol_budget / daily_vol × 100`, clipped by `--max-cap` (default 20.0). At the
> default 0.6%/day budget the ceiling binds for any ticker with daily vol ≤ 3.0%
> (≈48% annualized) — nearly every normal equity, NVDA at 38.6% annualized vol included.
> Above that breakpoint the formula does take over, but the observed range is thin.
>
> Back-solving the implied Step 2 base from 47 historical trades
> (`replay_trade_plan.replay_sizing`) makes the shape concrete. If the ceiling always binds,
> the base can only land on `20 × {1.00, .85, .70, .55} × {1, 0.5} / 100` — eight points:
>
> | on the ceiling lattice | ±0.0005 | ±0.005 |
> |---|---|---|
> | hits | 13/47 (28%) | 33/47 (70%) |
>
> The loose figure overstates it (those eight ±0.005 bins cover 42% of the observed range).
> The decisive evidence is the exact cluster: `0.140` appears **8 times** at three decimals
> (= 20 × 0.70). One value repeating eight times cannot come from a continuous vol
> calculation — only from a pinned constant times a discrete correlation tier.
>
> The top of the distribution is where vol did participate: `0.1955–0.1957` (×4),
> `0.1778` (×2), `0.1680` (×2) sit *below* the 0.20 lattice point and only resolve with
> `corr_mult = 1.00` and `raw_cap < 20` — implying daily vol 3.07–3.57%, just past the
> breakpoint, moving the cap by ≤ 3.2pp.
>
> So: **~6–8 trades saw marginal vol participation at the edge; every other trade pinned at
> 20.** `--max-cap` exists (V4.112.0) to make that observable — the same 47 trades can be
> re-solved under a different ceiling to see how the distribution moves. **Changing the
> default changes position sizing and remains a user decision** (`docs/plan_risk_trio_B.md` B1).

## Output schema
```json
{
  "ticker": "NVDA",
  "generated_at": "ISO8601",
  "inputs": {
    "vol_budget_pct": 0.6,
    "max_cap_pct": 20.0,
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
