---
name: tail-risk-analyzer
description: Quantifies tail risk / fragility for a single ticker using 1-year daily returns. Computes excess kurtosis, skewness, VaR95, max drawdown, and maps to a fragility label (ROBUST/MODERATE/FRAGILE). Use in sector protocol Phase 4b Devil's Advocate (top-3 HOT sectors) and investment protocol Phase 4 Step 3 (per-stock fragility → position sizing).
market: market-agnostic
scope: single-ticker
data_sources: [yfinance]
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
  "sample_days": "int — daily returns actually used (< 30 bars → error JSON + exit 1)",
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

> `scripts/tail_risk.py` is canonical for both the weights and the bands. This table was
> out of sync until V4.111.7 (it claimed 30/20/20/20/10 weights and 35/65 bands, which no
> code or consumer has ever used) — if the two ever disagree again, believe the script.

Each component is normalized to 0-100 (higher = more fragile), then weighted
(`tail_risk.py:72-79`). vol + max_DD carry 65% because kurtosis and skew are noisy on a
single year of history:

| Component | Weight | Normalizer (`:65-69`, calibrated 2026-04) |
|---|---|---|
| ann vol | 35% | `vol × 1.5` → 40% ann vol ≈ 60 |
| max drawdown | 30% | `dd × 2` → 40% DD = 80 |
| VaR95 | 15% | `var × 15` → 6% = 90 |
| excess kurtosis | 10% | `kurt × 8` |
| negative skew | 10% | `-skew × 40` (positive skew scores 0) |

- `tail_risk_score < 30` → **ROBUST** → multiplier 1.0
- `30 ≤ score < 60` → **MODERATE** → multiplier 0.75
- `score ≥ 60` → **FRAGILE** → multiplier 0.5

The label is mirrored in three places that must stay in lockstep — changing a band means
changing all of them plus the replay cohort: `investment/scripts/trade_plan_builder.py:102`
(`FRAGILITY_MULTIPLIER`), `investment/scripts/validate_session_export.py:386` (`_FRAGILITY_MULT`,
plus the §14b enum gate at `:1545-1549`), and `investment/scripts/replay_trade_plan.py`.

**Degradation contract**: fewer than 30 bars → `{"error", "ticker"}` on stdout + exit 1.
The consumer must then take **MODERATE ×0.75, never ROBUST** (`trade_plan_builder.py:373-389`,
protocol `:1310-1313`) — an unknown ticker does not get the largest multiplier.
