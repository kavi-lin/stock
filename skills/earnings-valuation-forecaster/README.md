# earnings-valuation-forecaster

Scenario-based 12-month valuation engine for US equities.

Combines three forward-EPS methods with the company's own PE percentile history,
peer-group median blending, and interest-rate regime adjustment to produce
**bull / base / bear target prices**, a probability-weighted **expected value**,
and an advisory **signal** (STRONG BUY → SELL).

---

## Requirements

```bash
export FMP_API_KEY=your_key_here     # required
# FRED_API_KEY not needed — reads from fred-macro cache if available
```

Python packages: `requests` (already in project env)

---

## Usage

```bash
# Basic — prints Markdown to stdout
python3 skills/earnings-valuation-forecaster/scripts/forecast.py MSFT

# JSON output only
python3 skills/earnings-valuation-forecaster/scripts/forecast.py NVDA --json-only

# Save report to reports/
python3 skills/earnings-valuation-forecaster/scripts/forecast.py AAPL --output-dir reports/

# Force fresh data (bypass 4h cache)
python3 skills/earnings-valuation-forecaster/scripts/forecast.py TSLA --no-cache

# Custom cache TTL
python3 skills/earnings-valuation-forecaster/scripts/forecast.py AMD --max-age 7200
```

**Within Claude Code**, trigger via natural language:
- 「估值 MSFT」「目標價 NVDA」「MSFT 12個月目標」「fair value AAPL」

---

## How it works (4 steps)

### Step 1 — Forward EPS (3 methods)

Fetches annual income statements and analyst estimates from FMP.

| Method | Logic |
|--------|-------|
| **CAGR** | 4-year EPS CAGR × 0.7 dampening factor applied to latest TTM |
| **Consensus** | FMP analyst-estimates median (next fiscal year, ≥6 months out) |
| **Trend** | Linear regression on last 5 annual EPS → project +1 year |

`forward_eps = median(all available methods)`

Confidence rating based on spread:
- **HIGH**: all 3 methods within ±10%
- **MEDIUM**: within ±25%
- **LOW**: > 25% (fragile — treat scenarios with caution)

### Step 2 — PE multiple range

FMP annual ratios endpoint → last 5 years of trailing PE.
Computes **p25 / p50 / p75** percentiles.

**v1.1 — Peer blending (70/30):**
Fetches peer group via FMP `/stock-peers` (or static `PEER_MAP` fallback).
Blends own-history PE with peer median: `effective_PE = own × 0.70 + peer_median × 0.30`.

**v1.1 — Rate adjustment:**
Reads `real_rate_preferred` (DFII10) from `skills/fred-macro/cache/fred_latest.json`.
Scales the blended PE range by regime:

| Real Rate | Regime | Multiplier |
|-----------|--------|------------|
| < 1% | Accommodative | ×1.08 |
| 1–2% | Neutral | ×1.00 |
| 2–3% | Elevated | ×0.90 |
| > 3% | Restrictive | ×0.82 |

### Step 3 — Scenarios & sensitivity grid

| | EPS −15% | EPS base | EPS +15% |
|---|---|---|---|
| **PE p25** | deep bear | moderate bear | — |
| **PE p50** | mild bear | **BASE** | mild bull |
| **PE p75** | — | moderate bull | **BULL** |

`Bear = EPS × 0.85 × PE_p25_effective`
`Base = EPS × PE_p50_effective`
`Bull = EPS × 1.15 × PE_p75_effective`

### Step 4 — Expected value & signal (v1.1)

Probability-weighted target, scaled by EPS confidence:

| Confidence | Bear prob | Base prob | Bull prob |
|------------|-----------|-----------|-----------|
| HIGH | 20% | 60% | 20% |
| MEDIUM | 25% | 50% | 25% |
| LOW | 30% | 40% | 30% |

Advisory signal:

| Signal | Condition |
|--------|-----------|
| 🟢 STRONG BUY | price < EV × 0.90 |
| 🟩 BUY | price < EV |
| 🟡 HOLD | price within base ±10% |
| 🟠 TRIM | price > base × 1.10 and ≤ base × 1.25 |
| 🔴 SELL | price > base × 1.25 |

---

## Output

**Markdown** (default): printed to stdout; saved to `reports/YYYYMMDD_<TICKER>_valuation.md` with `--output-dir`.

**JSON** (`--json-only`): full payload including all fields below.

Key fields:
```json
{
  "signal": "BUY",
  "expected_value": 422.5,
  "expected_value_upside_pct": 10.0,
  "scenarios": { "bear": {...}, "base": {...}, "bull": {...} },
  "multiple_range": { "pe_p25": 24.5, "pe_p50": 32.0, "pe_p75": 38.8 },
  "multiple_range_effective": { "pe_p25": 23.1, "pe_p50": 30.2, "pe_p75": 36.7 },
  "peer_pe_info": { "median_pe": 28.0, "peers_used": ["AAPL","GOOGL"], "source": "fmp_stock_peers" },
  "rate_context": { "real_rate": 1.92, "rate_multiplier": 1.0, "rate_regime": "neutral" }
}
```

---

## Cache

Per-ticker JSON at `cache/<TICKER>.json`, TTL **4 hours** (default).

---

## Limitations

- Positive-EPS companies only (TTM EPS ≤ 0 → returns `status: unsupported`)
- PE percentiles use own 5-year history — stale in regime shifts (e.g., ZIRP → high-rate)
- Peer blend limited to 5 peers; thin/mismatched peers reduce accuracy
- Rate adjustment uses DFII10 from fred-macro cache — stale if cache not refreshed today
- Signal is **advisory only**, not a trading instruction
- Earnings quality not adjusted (SBC, one-offs, GAAP vs non-GAAP)
