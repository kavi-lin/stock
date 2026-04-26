---
name: short-term-target
description: Short-term (1d / 5d / 15d) directional projection for a US stock — "Tactical Opportunity Radar". Outputs target range + confidence breakdown + benchmark-relative alpha + trading meta (stop / position size hint / exit trigger). Each horizon uses independent weights from config/weights.yaml. Refuses to project when source data is stale (returns insufficient_data with reasons). Hard-clamped to prevent cold-start absurd predictions. Use when caller wants short-term directional bias on a specific ticker, NOT for long-term valuation (use earnings-valuation-forecaster for 12-month). Standalone — not auto-wired into investment_protocol.
market: us-equity
scope: per-ticker
data_sources: [yfinance, sector/sector_logs, finnhub-client/data (dual_fetch), config/weights.yaml]
horizons: [1d, 5d, 15d]
status: experimental
---

# short-term-target — Tactical Opportunity Radar

Short-term directional projection skill. Sister to `earnings-valuation-forecaster` (12-month fundamental target). Together they cover both ends of the time spectrum; `investment_protocol_v4_8.md` covers the 3-6 month middle.

## Purpose

Take one US ticker and output **1d / 5d / 15d directional projections** with target range, confidence breakdown, benchmark-relative alpha, and trading meta. Designed for daily refresh on Dashboard / batch screening across watchlist.

**What it is**:
- Short-term momentum + news + sector-heat fusion
- Per-horizon independent weights (1d driven by news / 5d by momentum / 15d by sector persistence)
- Hard-clamped output (1d ±5%, 5d ±15%, 15d ±30%) to prevent cold-start absurdity
- Refuses to project when source data is stale (insufficient_data)
- Confidence breakdown is fully transparent (every contributor exposed)

**What it is NOT**:
- Not a deterministic price prediction
- Not for long-term investment thesis (use investment_protocol)
- Not for fundamental valuation (use earnings-valuation-forecaster)
- Not auto-wired into investment_protocol — standalone tool

## Usage

```bash
# Pretty-printed JSON
python3 skills/short-term-target/scripts/predict.py NVDA

# Compact JSON (for piping into other tools)
python3 skills/short-term-target/scripts/predict.py NVDA --json-only
```

Required: nothing — yfinance is open. dual_fetch / sector_intel are read if present (graceful degrade).

Optional environment: `FINNHUB_API_KEY`, `FMP_API_KEY` if extending to v0.2 with real news API.

## Output Schema

```json
{
  "ticker": "NVDA",
  "as_of": "ISO timestamp",
  "current_price": 195.32,
  "weights_version": "v0.1.0",
  "horizons": {
    "1d": {
      "status": "ok | insufficient_data",
      "target_central": 198.5,
      "target_low": 192.0,
      "target_high": 204.0,
      "target_central_pct": 1.63,
      "confidence": 0.62,
      "confidence_breakdown": {
        "base": 0.50,
        "news_freshness": 0.08,
        "sector_heat_persistence": 0.10,
        "atr_penalty": -0.04,
        "horizon_penalty": -0.01,
        "data_completeness_bonus": 0.02,
        "model_clamped_penalty": 0.0
      },
      "drivers": {"news_score": 0.4, "sector_heat": 0.64, "momentum_score": 0.6, "atr_pct": 3.95},
      "model_clamped": false,
      "data_sufficiency": {"ohlcv_days": 60, "news_age_hr": 0.5, "sector_age_hr": 14.9, "atr_pct": 3.95},
      "weights_applied": {...},
      "driver_labels": {"momentum": "RSI=97, current>MA20>MA50", "news": "vol 2.2× avg, gap +13.9%", "sector_status": "ok_proxy_median"},
      "benchmark_etf": "SPY",
      "benchmark_realized_pct": 0.77,
      "implied_alpha_pct": 0.86
    },
    "5d": {...},
    "15d": {...}
  },
  "trading_meta": {
    "stop_suggestion": 188.0,
    "stop_distance_pct": 5.93,
    "position_size_hint_pct": 5.0,
    "tx_cost_estimate_pct": 0.05,
    "min_holding_days": 1,
    "exit_trigger": "Close < 188.0 OR 5d target X reached OR confidence drops < 0.4"
  },
  "invalidation": "Close < $X OR sector heat downgrades by 0.2 OR ATR jumps > 50% from Y%",
  "metadata": {
    "dual_fetch_status": "ok | no_ticker_file | ...",
    "sector_heat_status": "ok_proxy_median | no_cache | ...",
    "news_driver_kind": "proxy_volume_gap (v0.1)",
    "experimental": true,
    "framework": "Tactical Opportunity Radar v0.1",
    "benchmark_etf": "SPY"
  },
  "global_warnings": ["..."]
}
```

### insufficient_data shape

When a horizon's required sources are too stale or missing:
```json
"5d": {
  "status": "insufficient_data",
  "missing": ["sector>72h_old", "ohlcv<5d"],
  "would_need": "Refresh stale sources OR wait for sufficient OHLCV history",
  "data_sufficiency": {...}
}
```

**No target / confidence is fabricated** when status is `insufficient_data`. Caller must handle absence.

## Architecture

```
yfinance OHLCV (60d)
     ↓
ATR (14) + Momentum (RSI + MA structure) + News proxy (volume/gap)
     ↓
sector_intel cache → sector_heat (0-1)
     ↓
config/weights.yaml HORIZON_WEIGHTS[h] applied per horizon
     ↓
shift_pct = α × news + β × sector_heat + γ × momentum
     ↓
hard clamp by horizon (1d ±5%, 5d ±15%, 15d ±30%)
     ↓
target_range = target_central ± k × ATR
confidence = base + news_fresh + heat_persist - atr_penalty - horizon_penalty + ...
     ↓
benchmark ETF realized (forward window) → implied_alpha
     ↓
trading_meta (stop / pos% / exit)
```

## Data sufficiency rules (per horizon)

| Horizon | Must have | Triggers `insufficient_data` if |
|---|---|---|
| 1d | quote (live), 1d ATR, 24h news | quote > 60min OR news > 8h OR ATR sample < 5d |
| 5d | 5d momentum baseline, 24-48h news, sector heat | sector_intel > 72h OR news > 24h OR ohlcv < 5d |
| 15d | 15d realized vol, sector heat persistence, multi-week news | sector_intel > 168h OR ohlcv < 15d OR news < 5 in 3w |

All thresholds in `config/weights.yaml` `freshness_thresholds`. Edit there.

## Confidence formula (transparent)

```
base = 0.50
+ news_freshness        : (news_conf - 0.5) * 0.4         # max +0.2
+ sector_heat_persistence: heat * 0.15                    # max +0.15
+ atr_penalty           : -(atr_pct - 3.0) / 10           # heavy penalty for high ATR
+ horizon_penalty       : -(days_horizon / 100)           # 1d -0.01, 5d -0.05, 15d -0.15
+ data_completeness     : +0.02 if all sources fresh
+ model_clamped_penalty : -0.15 if shift_pct was clamped
= clamp(0.0, 0.95)                                        # never 1.0
```

Output `confidence_breakdown` exposes every term — sum equals final confidence (audit-able).

## Benchmark-relative output

Each horizon's prediction shows:
- `benchmark_etf`: chosen by sub-industry (defaults to SPY in v0.1; GICS lookup deferred to v0.2)
- `benchmark_realized_pct`: ETF's recent N-day realized return
- `implied_alpha_pct`: prediction - benchmark_realized

⚠️ **Caveat**: `implied_alpha_pct` compares **forward prediction** vs **backward realized**. It's a proxy assuming benchmark continues at recent pace. Document caveat: if SPY had a big recent move, alpha will look misleadingly small/negative. Use as directional context, not absolute claim.

## Trading meta

Designed for **trade decisions, not watchlist** (per user requirement):

- `stop_suggestion`: 1.5 × ATR below current
- `stop_distance_pct`: stop distance as % (1.5 × atr_pct)
- `position_size_hint_pct`: 0.33 / atr_pct, capped 0.5%-5%. Risks ~0.5% portfolio per trade.
- `tx_cost_estimate_pct`: flat 0.05% (round-trip estimate for liquid US stocks)
- `min_holding_days`: 1 (avoid being whipsawed by own short signals)
- `exit_trigger`: composite condition string

## Recalibration workflow (Weekend Recalibration Tool — Step 7)

`config/weights.yaml` is **hand-editable**. To recalibrate:

1. Run `python3 skills/short-term-target/scripts/weekly_review.py` (Step 7, separate tool)
2. Review markdown report in `reports/SHORT_TERM_WEEKLY_<DATE>.md`
3. If suggestions look reasonable, edit `config/weights.yaml` accordingly
4. Bump `weights_version` field
5. All future predictions tag with new version → backtest can compare

**Tool does NOT auto-overwrite config**. User has full control.

## Limitations (v0.1)

| Area | Limitation | Plan |
|---|---|---|
| News driver | Volume/gap proxy, not real news API | v0.2 add Finnhub /company-news with sentiment |
| GICS sub-industry | Not looked up; benchmark defaults to SPY | v0.2 add ticker→GICS resolver |
| Cache | None — every call hits yfinance | Add 4h TTL cache |
| dual_fetch consumption | Best-effort read; not enforced | Optional |
| Real Finnhub catalysts (insider, upgrades) | Not used | v0.2 |
| Validation | None — first run, no outcome data | Step 5 outcome log accumulates from day 1 |

## Files

```
skills/short-term-target/
├── SKILL.md                       # this file
├── README.md                      # usage walkthrough + interpretation guide
├── CHANGELOG.md                   # version history
├── config/weights.yaml            # hand-editable parameters
├── scripts/predict.py             # main entry
├── cache/                         # gitignored
└── data/                          # gitignored — recommendation log dest (Step 5)
```
