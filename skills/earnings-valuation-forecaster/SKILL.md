---
name: earnings-valuation-forecaster
description: Project 12-month target prices for a US stock using earnings trend analysis, peer multiple comparison, and sensitivity grids. Produces bull / base / bear scenarios with upside/downside, key assumptions, trigger conditions, and a 3×3 sensitivity matrix (EPS growth × forward multiple). Use when user asks for 目標價, fair value, 合理價格, valuation target, price projection, scenario analysis, or "what's this stock worth in 12 months" for a specific ticker. Standalone skill — not auto-wired into investment protocol.
market: us-equity
scope: per-ticker
data_sources: [FMP]
---

# Earnings Valuation Forecaster

## Purpose

Take one US ticker and produce a **12-month scenario-based target price range**
from earnings fundamentals + multiple comparison. This fills the gap in the
system where we consume analyst consensus PTs but never produce our own.

**What it is**:
- **Scenario framework**: 9-cell sensitivity grid of (EPS growth × forward PE)
  → extract bull / base / bear target prices
- **Forward EPS**: three estimation methods cross-checked (trailing CAGR,
  analyst consensus from FMP, seasonally-adjusted trend)
- **Multiple**: company's own 5Y percentile range (25th / 50th / 75th) — not
  peer-relative to avoid sector anchoring bias
- **Trigger conditions**: each scenario comes with "achieves if" and
  "invalidated if" falsifiable thresholds

**What it is NOT**:
- Not DCF or intrinsic value
- Not a day-trading signal
- Not a definitive "buy/sell" — it's input to a decision, not a decision
- Not integrated into `investment_protocol_v4_8.md` (user chose standalone)

## Usage

```bash
# Required
export FMP_API_KEY=your_key_here

# Standalone CLI
python3 skills/earnings-valuation-forecaster/scripts/forecast.py MSFT
python3 skills/earnings-valuation-forecaster/scripts/forecast.py NVDA --json-only
python3 skills/earnings-valuation-forecaster/scripts/forecast.py AAPL --output-dir reports/
```

Within Claude Code, trigger via:
- Natural language: 「估值 MSFT」「目標價 NVDA」「MSFT 12個月目標」「fair value AAPL」
- Slash: `/earnings-valuation-forecaster MSFT`

## Method

### Step 1 — Forward EPS projection (3 methods, averaged)

Fetches last 8 quarters of diluted EPS from FMP `/income-statement?period=quarter`.

1. **Trailing CAGR method**: `EPS_fwd = EPS_ttm × (1 + cagr_4yr_adjusted)`
   where `cagr_4yr_adjusted` is last-4Q EPS growth dampened ×0.7 (decay factor
   so recent parabolic growth doesn't extrapolate linearly)
2. **Analyst consensus method**: FMP `/analyst-estimates` next-year EPS median
3. **Trend method**: linear regression on last 8 quarters → project next 4

Final `forward_eps = median(method_1, method_2, method_3)` if all available,
else mean of available. Flag `confidence: HIGH | MEDIUM | LOW` based on:
- HIGH: all 3 methods within ±10% spread
- MEDIUM: within ±25% spread
- LOW: > 25% spread (divergence signals fragility)

### Step 2 — Multiple range

FMP `/key-metrics?period=quarter&limit=20` gives 5 years of trailing PE.
Compute:
- `pe_p25` (bear multiple — 25th percentile of last 5Y, trimmed)
- `pe_p50` (base multiple — median)
- `pe_p75` (bull multiple — 75th percentile)

Fallback if < 20 quarters: use `min / median / max` of available with warning.

### Step 3 — 3×3 sensitivity matrix

| | EPS bear (−15%) | EPS base | EPS bull (+15%) |
|---|---|---|---|
| **PE bear (p25)** | deep_bear | moderate_bear | — |
| **PE base (p50)** | mild_bear | **BASE** | mild_bull |
| **PE bull (p75)** | — | moderate_bull | **BULL** |

Bull target = `EPS_fwd × 1.15 × PE_p75`
Base target = `EPS_fwd × PE_p50`
Bear target = `EPS_fwd × 0.85 × PE_p25`

### Step 4 — Trigger conditions

Each scenario reports:
- `upside_pct`: vs current price
- `achieves_if`: forward-looking conditions (e.g., "next 2 earnings beat by > 5%
  AND multiple re-rates to p75")
- `invalidated_if`: falsifiable kill condition (e.g., "any FY miss > 10%
  OR PE compresses below p25")

## Output Schema (JSON)

```json
{
  "ticker": "MSFT",
  "generated_at": "2026-04-20T10:15:00",
  "current_price": 384.23,
  "ttm_eps": 11.80,
  "forward_eps": {
    "value": 13.20,
    "method_1_cagr": 13.50,
    "method_2_consensus": 13.10,
    "method_3_trend": 13.00,
    "confidence": "HIGH",
    "spread_pct": 3.8
  },
  "multiple_range": {
    "pe_p25": 24.5,
    "pe_p50": 32.0,
    "pe_p75": 38.8,
    "window_quarters": 20
  },
  "scenarios": {
    "bear":  {"target": 266.0, "upside_pct": -30.8, "eps_delta": -15, "pe": 24.5,
              "achieves_if": "forward EPS miss > 10% or margin compression",
              "invalidated_if": "beats guidance 2 quarters in a row"},
    "base":  {"target": 422.4, "upside_pct":  10.0, "eps_delta":   0, "pe": 32.0,
              "achieves_if": "in-line earnings + range-bound multiple",
              "invalidated_if": "either earnings surprise > 10% or multiple break"},
    "bull":  {"target": 589.6, "upside_pct":  53.5, "eps_delta": +15, "pe": 38.8,
              "achieves_if": "capex cycle extension + 2x consensus beat",
              "invalidated_if": "any guidance cut or macro multiple compression"}
  },
  "sensitivity_grid": [
    [266.0, 313.0, 360.0],
    [307.0, 361.0, 415.0],
    [427.0, 502.0, 577.0]
  ],
  "sensitivity_axes": {
    "rows": ["PE p25 (24.5)", "PE p50 (32.0)", "PE p75 (38.8)"],
    "cols": ["EPS bear (-15%)", "EPS base", "EPS bull (+15%)"]
  },
  "caveats": [
    "Multiple range uses company 5Y history — blind to sector regime shifts",
    "Forward EPS trend method assumes business model continuity",
    "Not a replacement for DCF / intrinsic value analysis"
  ]
}
```

## Output Schema (Markdown)

Written to `reports/YYYYMMDD_<TICKER>_valuation.md`:

```markdown
# MSFT · 12-Month Valuation Scenarios

**Current**: $384.23  ·  **TTM EPS**: $11.80  ·  **Forward EPS**: $13.20 (HIGH conf)

| Scenario | Target | Upside | PE  | EPS Δ  | Key Trigger |
|----------|--------|--------|-----|--------|-------------|
| 🐂 Bull  | $589.6 | +53.5% | 38.8× | +15%  | capex extension + 2x beat |
| 📊 Base  | $422.4 | +10.0% | 32.0× | 0%    | in-line, range-bound |
| 🐻 Bear  | $266.0 | −30.8% | 24.5× | −15%  | miss > 10% or compression |

## Sensitivity Matrix (target price)
| | EPS −15% | EPS base | EPS +15% |
|---|---|---|---|
| **PE p25** | $266 | $313 | $360 |
| **PE p50** | $307 | $361 | $415 |
| **PE p75** | $427 | $502 | $578 |

## Forward EPS reconciliation
- Trailing CAGR (dampened): $13.50
- Analyst consensus: $13.10
- Trend regression: $13.00
- **Adopted**: $13.20 (median, ±3.8% spread → HIGH confidence)

## Caveats
...
```

## Cache

Per-ticker cache at `cache/<ticker>.json`, TTL 4 hours (default).
CLI flags: `--no-cache`, `--max-age <sec>`.

## Caveats

- **Assumes continuity of business model**: secular disruption breaks forward
  EPS methods (e.g., a tobacco company's 5Y PE range doesn't apply in a
  post-FDA-ban world).
- **Multiple percentiles are regime-blind**: if the stock traded at 40× during
  ZIRP 2020-2021 and we're now in a higher-rate regime, p75=38.8 is stale.
- **Not for non-earners**: if TTM EPS ≤ 0, skill refuses and returns
  `{"status": "unsupported", "reason": "negative_ttm_eps"}` — user should
  switch to P/S or EV/EBITDA based valuation (not in scope).
- **Earnings quality ignored**: no adjustment for stock-based comp, one-offs,
  or GAAP vs non-GAAP divergence. Use with judgement.
