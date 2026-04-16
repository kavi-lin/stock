---
name: tail-risk-analyzer
description: Quantifies tail risk / fragility for a single ticker using 1-year daily returns. Computes excess kurtosis, skewness, VaR95, max drawdown, and maps to a fragility label (ROBUST/MODERATE/FRAGILE). Use in sector protocol Phase 4b Devil's Advocate (top-3 HOT sectors) and investment protocol Phase 4 Step 3 (per-stock fragility → position sizing).
---

# Tail Risk Analyzer

## Purpose
Provides quantitative fragility evidence for any ticker (stock or ETF). Used by:
- **Sector Phase 4b** — proxy ETF tail risk challenges hot sector (top 3 by composite)
- **Investment Phase 4 Step 3** — per-stock fragility multiplies position sizing

## Usage
```bash
python3 skills/tail-risk-analyzer/scripts/tail_risk.py NVDA
python3 skills/tail-risk-analyzer/scripts/tail_risk.py XLK --json-only
python3 skills/tail-risk-analyzer/scripts/tail_risk.py SPY --lookback 2y
```

## Output schema
```json
{
  "ticker": "NVDA",
  "generated_at": "ISO8601",
  "lookback": "1y",
  "excess_kurtosis": "float (> 3 is fat-tailed vs normal)",
  "skewness": "float (negative = left-tailed / crash risk)",
  "var_95": "float — daily loss exceeded 5% of days (pct)",
  "max_drawdown": "float pct",
  "ann_vol": "float pct",
  "downside_deviation": "float pct",
  "tail_risk_score": "0-100 (higher = more fragile)",
  "fragility_label": "ROBUST | MODERATE | FRAGILE",
  "position_multiplier": "1.0 | 0.75 | 0.5 — applied to base position size"
}
```

## Fragility mapping
Score is weighted: excess_kurt (30%) + |neg skew| (20%) + VaR95 (20%) + max_DD (20%) + vol (10%).
- `tail_risk_score < 35` → **ROBUST** → multiplier 1.0
- `35 ≤ score < 65` → **MODERATE** → multiplier 0.75
- `score ≥ 65` → **FRAGILE** → multiplier 0.5
