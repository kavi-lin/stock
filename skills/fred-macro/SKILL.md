---
name: fred-macro
version: 1.13.0
description: Fetches structured macro-economic data from FRED (Federal Reserve Economic Data) for 13 key series covering rates, inflation, employment, credit spreads, and financial stress. Produces a regime snapshot (label, confidence, macro_scores, sector_rotation, change_velocity) consumed by investment_protocol Phase 0, macro-regime-detector, and news-protocol macro context. Use when needing timely, authoritative macro inputs without relying on WebSearch or FMP (which has daily quota). Requires free FRED_API_KEY env var.
market: global-macro
scope: macro-snapshot
data_sources: [FRED API]
---

# FRED Macro Snapshot

Pulls 12 key US economic series from FRED (Federal Reserve Economic Data) and derives a regime snapshot. FRED is free (120 req/min, effectively unlimited daily) and authoritative — no LLM hallucination risk vs WebSearch.

## Prerequisites

- `FRED_API_KEY` env var — register free at https://fred.stlouisfed.org/docs/api/api_key.html
- Python `requests` (already installed)

## Usage

```bash
python3 skills/fred-macro/scripts/fetch.py                       # 12 default series, 15-min cache
python3 skills/fred-macro/scripts/fetch.py --json-only           # machine-readable only
python3 skills/fred-macro/scripts/fetch.py --no-cache            # force refetch
python3 skills/fred-macro/scripts/fetch.py --series DGS10,T10Y2Y # custom subset
```

## Tracked series (12)

| Category | Series ID | Description |
|---|---|---|
| Rates | `DGS10` / `DGS2` / `T10Y2Y` / `DFF` | 10Y / 2Y Treasury, yield curve, Fed Funds |
| Inflation | `CPIAUCSL` / `CPILFESL` / `PCEPILFE` | CPI, Core CPI, Core PCE (Fed's preferred) |
| Employment | `UNRATE` / `PAYEMS` / `ICSA` | Unemployment, Nonfarm payrolls, Initial claims |
| Credit | `BAMLH0A0HYM2` | High-yield bond spread (credit stress proxy) |
| Stress | `NFCI` | Chicago Fed Financial Conditions Index |
| Commodity | `DCOILWTICO` | WTI crude oil |

## Output schema

Per-series:
- **Rate / spread series** (`DGS10`, `DGS2`, `T10Y2Y`, `DFF`, `BAMLH0A0HYM2`): `{value, date, delta_bps_1m, delta_bps_3m, delta_bps_1y, percentile_1y, trend_30d, trend_90d}`
- **Other series**: `{value, date, yoy_change_pct, mom_change_pct, percentile_1y, trend_30d, trend_90d}`

Derived `regime_signals`:
- `yield_curve_inverted` — `T10Y2Y < 0` (recession leading indicator)
- `yield_curve_steep` — `T10Y2Y > 1.0` (early recovery)
- `credit_stress_elevated` — `BAMLH0A0HYM2` above 1-year 75th percentile
- `financial_stress_above_avg` — `NFCI > 0` (tightening conditions)
- `fed_rate_direction` — `DFF` 3-month delta: `rising` / `falling` / `flat`
- `real_rate_estimate` — `DGS10 − CPI YoY` (rough real rate)

Enhanced fields (v1.1.0):
- `macro_scores` — `{rates, inflation, employment, credit, financial_conditions, composite}` (0–100)
- `regime_label` — one of 9 regime strings (Goldilocks / Soft Landing / Reflation / Easing Cycle / Overheating / Late Cycle Tightening / Stagflation / Recession Risk / Transitional)
- `regime_confidence` — float 0.20–0.95, signal agreement score
- `market_implications` — list of human-readable implication strings
- `change_velocity` — per-series `{trend_30d, mom_change_pct, monthly_baseline, velocity}`
- `sector_rotation` — `{regime, favor: [...], avoid: [...], rationale}`

## Caching

15-minute TTL at `skills/fred-macro/cache/fred_latest.json`. Most FRED series update daily or slower, so cache hits are safe.

## Consumers

- `investment_protocol_v4_8.md` Phase 0 — macro context
- `macro-regime-detector` — replace ETF-ratio proxies with official data
- `news_protocol_v2.md` Phase 3 — news catalyst cross-reference
