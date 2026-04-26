---
name: thematic-screener
description: Daily Top N hot themes × Top M short-term movers per theme. Combines theme-detector heat scoring (medium-term) with short-term-target predictions (1d/5d/15d) into a "Tactical Opportunity Radar" recommendation log. Tags concentration WARNING when ≥2 picks share theme. Records FRED + market regime snapshot at recommendation time for future backtest cross-tabs. Standalone — not auto-wired into investment_protocol. Use for daily watchlist refresh / Dashboard推薦面板feed / batch screening across hot themes.
market: us-equity
scope: cross-ticker
data_sources: [theme-detector cache, short-term-target, fred-macro cache, yfinance (SPY/VIX)]
status: experimental
---

# thematic-screener — Tactical Opportunity Radar (Aggregator)

Daily aggregator that connects two upstream skills:

```
theme-detector (heat / lifecycle, medium-term)
       ↓
   Top N themes by heat
       ↓
   representative_stocks (per theme)
       ↓
short-term-target (1d / 5d / 15d projection per ticker)
       ↓
+ regime_snapshot (SPY / VIX / FRED)
+ concentration_flag (per §11.B WARNING-not-REMOVE)
       ↓
data/recommendations/<DATE>.json
```

## Usage

```bash
# Default: top 5 themes × top 4 movers (~ 20 predict.py calls, 100-300s)
python3 skills/thematic-screener/scripts/screen.py

# Smoke test
python3 skills/thematic-screener/scripts/screen.py --top-themes 2 --top-movers 2 --no-write

# JSON-only for piping
python3 skills/thematic-screener/scripts/screen.py --json-only
```

## Output Schema

```json
{
  "as_of": "ISO timestamp",
  "experimental": true,
  "framework": "Tactical Opportunity Radar v0.1 (thematic-screener)",
  "regime_snapshot": {
    "spy_close": 713.94,
    "spy_ma50": 676.99,
    "spy_ma50_status": "above",
    "spy_rsi_14": 87.4,
    "vix": 18.71,
    "yield_curve_t10y2y": 0.62,
    "yield_curve_inverted": false,
    "fed_funds_current": 3.64,
    "credit_spread_pctile_1y": 29,
    "credit_stress_elevated": false,
    "fred_regime_label": "expansion | caution"
  },
  "theme_detector_meta": {"age_hr": 20.0, "file": "..."},
  "screener_params": {"top_themes": 5, "top_movers": 4},
  "themes": [
    {
      "name": "Nuclear Energy",
      "direction": "bullish",
      "heat": 78.3,
      "heat_label": "Hot",
      "lifecycle_stage": "Mature",
      "confidence": "Medium",
      "proxy_etfs": ["URA", "URNM", "NLR"],
      "fred_alignment": "neutral",
      "top_movers": [
        {
          "ticker": "CEG",
          "short_term": { ...full short-term-target output... },
          "concentration_flag": {
            "theme": "Nuclear Energy",
            "co_recommendations": ["VST", "OKLO"],
            "warning": "Theme 'Nuclear Energy' has 3 co-recs; correlated drawdown risk in same-theme exposure"
          }
        }
      ]
    }
  ],
  "global_warnings": []
}
```

## Concentration WARNING (per plan_short.md §11.B)

Same theme ≥ 2 picks → `concentration_flag` with co-recommendations and warning text.

**Important**: Per §11.B修正 — concentration is **WARNING not REMOVE**. The screener returns ALL top movers; downstream consumers (Dashboard) decide whether to dim / hide / cap. This is because:
- Same-theme co-recs can be **correlated drawdown risk** (NTRS+STT case)
- BUT same-theme co-recs can also be **sector momentum** (CCJ+CEG+VST during nuclear rally)
- The system can't tell which is which from data alone — let user decide

v0.1: concentration is THEME-based (proxy). v0.2: switch to GICS sub-industry once lookup table built.

## Regime snapshot (per plan_short.md §12.D)

Each daily log includes the full market state at recommendation time:
- SPY close + RSI(14) + MA50 status
- VIX
- FRED regime signals (yield curve / credit / fed funds / real rate)
- FRED regime label (expansion | caution)

**Why this matters for backtest**: Future `weekly_review.py` (Step 7) can cross-tab predictions vs outcomes by regime — answer "does the model work better when SPY RSI < 70 vs > 70?" / "when fred_regime_label = caution vs expansion?" etc.

## Architecture

```
scripts/screen.py
├── load_latest_themes()         → reads skills/theme-detector/cache/theme_detector_*.json
├── load_fred_snapshot()         → reads skills/fred-macro/cache/*.json
├── get_market_snapshot()        → yfinance SPY/^VIX
├── select_top_movers()          → theme.representative_stocks[:max_movers]
├── run_short_term_target()      → subprocess to skills/short-term-target/scripts/predict.py
├── tag_concentration()          → §11.B WARNING (not REMOVE)
└── build_output() / write       → data/recommendations/<DATE>.json
```

**Key design choices**:
- **Subprocess (not import) to call short-term-target**: skill independence. ~5-15s × N tickers = 100-300s per full run. Acceptable for daily cadence.
- **No own data fetching**: relies entirely on upstream skill caches + yfinance for regime snapshot.
- **No scoring of FRED → theme**: per plan_short §12.E (硬版拒絕). Just records FRED state; humans / LLM judge.
- **Theme = concentration proxy in v0.1**: GICS sub-industry lookup deferred to v0.2.

## Limitations (v0.1)

| Area | Limitation | Plan |
|---|---|---|
| Concentration grain | Theme-level (not GICS sub-industry) | v0.2: add GICS lookup table for finer dedup |
| FRED → theme alignment | Always "neutral" — placeholder | v0.2 evaluate after Step 7 outcome data |
| Cache | Reads only; no own cache | Sufficient (theme-detector/short-term-target each cache themselves) |
| Cost | ~ N×M predict.py calls (≈ 100-300s for 5×4) | Acceptable for daily cadence |
| Validation | No outcome backtest yet (Step 7) | Day-1 log accumulation enables Step 7 |

## Files

```
skills/thematic-screener/
├── SKILL.md                          # this file
├── README.md                         # usage walkthrough
├── CHANGELOG.md                      # version history
├── scripts/screen.py                 # main entry
├── cache/                            # gitignored (currently unused — reads upstream caches)
└── data/recommendations/             # gitignored — daily JSON logs
    └── YYYY-MM-DD.json               # one per run-day
```

## Relationship to other skills

| Skill | Relationship |
|---|---|
| `theme-detector` | Direct upstream — reads its cache |
| `short-term-target` | Direct upstream — subprocess invokes its predict.py |
| `fred-macro` | Optional upstream — reads cache for regime context |
| `momentum-monitor` | Independent (different scoring paradigm) |
| `investment_protocol_v4_8.md` | **No relationship** — does not affect protocol decisions |
| `weekly_review.py` (Step 7, future) | Direct downstream — reads `data/recommendations/` to evaluate hit rate |
