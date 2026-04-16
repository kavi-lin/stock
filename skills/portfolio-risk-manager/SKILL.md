---
name: portfolio-risk-manager
description: Calculates vol-adjusted position size cap and correlation-aware multiplier for a new candidate ticker given current holdings. Use in investment protocol Phase 4 Step 2 to compute safe position size before entry. Reads positions.json and yfinance data; no API key.
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
python3 skills/portfolio-risk-manager/scripts/risk_manager.py CRWV --positions positions.json
```

Defaults: reads `positions.json` from repo root; if missing, runs standalone
(vol-scaling only, correlation multiplier = 1.0).

## Output schema
```json
{
  "ticker": "NVDA",
  "generated_at": "ISO8601",
  "inputs": {
    "vol_budget_pct": 0.6,
    "positions_loaded": 5,
    "candidate_sector": "Technology",
    "portfolio_size_usd": 100000
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
  "reasoning": "string"
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
