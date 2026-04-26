# thematic-screener — Usage Guide

Companion to `SKILL.md` (spec). The how-to for daily / weekly use.

---

## Quick start

```bash
# Default (top 5 themes × top 4 movers per theme = ~20 predict.py calls)
python3 skills/thematic-screener/scripts/screen.py

# Smoke test (4 calls, ~30s)
python3 skills/thematic-screener/scripts/screen.py --top-themes 2 --top-movers 2 --no-write

# Pipe-friendly
python3 skills/thematic-screener/scripts/screen.py --json-only | jq '.themes[] | {name, heat, top_movers: [.top_movers[].ticker]}'
```

**Output paths**:
- stdout: full JSON
- file: `skills/thematic-screener/data/recommendations/<YYYY-MM-DD>.json` (overwritten if same day re-run)

---

## Pre-requisites

| Source | Needed | If missing |
|---|---|---|
| `skills/theme-detector/cache/theme_detector_*.json` | Required | Script exits with `error: no_theme_detector_cache` |
| `skills/short-term-target/scripts/predict.py` | Required | Per-ticker predict will error |
| `skills/fred-macro/cache/*.json` | Optional | regime_snapshot will be partial (no FRED fields) |
| yfinance internet access | Optional | regime_snapshot will be partial (no SPY/VIX) |

To refresh upstream caches:
```bash
# theme-detector (slow, 2-3 min)
python3 skills/theme-detector/scripts/theme_detector.py

# fred-macro (fast, < 30s, cached 15 min)
python3 skills/fred-macro/scripts/fetch.py --json-only > /dev/null
```

---

## How to read the output

### regime_snapshot — your situational awareness

```
"regime_snapshot": {
  "spy_close": 713.94,
  "spy_rsi_14": 87.4,           ← extreme overbought!
  "spy_ma50_status": "above",
  "vix": 18.71,                 ← low vol
  "yield_curve_t10y2y": 0.62,
  "credit_spread_pctile_1y": 29,
  "fred_regime_label": "expansion"
}
```

**Read this FIRST**. If SPY RSI > 80, expect mean-reversion risk on all bullish recs. If `fred_regime_label = "caution"`, treat all directional predictions as lower-conviction.

### Per-theme block

```
{
  "name": "Nuclear Energy",
  "heat": 78.3,                  ← higher = more attention/momentum
  "heat_label": "Hot",           ← Cool/Warm/Hot/Extreme
  "lifecycle_stage": "Mature",   ← Emerging/Growing/Mature/Cooling
  "confidence": "Medium",
  "proxy_etfs": ["URA", "URNM", "NLR"],
  "fred_alignment": "neutral",   ← v0.1 always neutral; v0.2 evaluate
  "top_movers": [...]
}
```

### Per-mover block

```
{
  "ticker": "CEG",
  "short_term": { ...full short-term-target output (see that skill's README)... },
  "concentration_flag": {
    "theme": "Nuclear Energy",
    "co_recommendations": ["VST", "OKLO"],
    "warning": "..."
  }
}
```

**Concentration_flag is informational, not a "skip"**. If you see 3 nuclear names recommended, that could be:
- (Bad) "I'm about to over-concentrate in one drawdown vector" — same as NTRS+STT case
- (Good) "The whole nuclear theme is rallying; missing this group means missing the move"

The screener can't tell which. **You decide based on your portfolio**.

---

## Daily workflow (recommended)

```
Morning (before market open):
  1. Refresh theme-detector if cache > 24h old:
     python3 skills/theme-detector/scripts/theme_detector.py
  2. Refresh fred-macro:
     python3 skills/fred-macro/scripts/fetch.py --json-only > /dev/null
  3. Run thematic-screener (writes to data/recommendations/):
     python3 skills/thematic-screener/scripts/screen.py
  4. Review JSON or look at Dashboard panel (Step 4 future)

Weekend:
  python3 skills/short-term-target/scripts/weekly_review.py  ← Step 7 (future)
  → Read reports/SHORT_TERM_WEEKLY_<DATE>.md
  → Decide if weights.yaml needs hand-tuning
```

---

## Common interpretation mistakes

| Mistake | Reality |
|---|---|
| Treating `heat` as a buy signal | Heat is **attention/momentum**, not direction. A theme can be Hot while individual constituents are bearish |
| Ignoring `concentration_flag` | Same-theme exposure ≥ 2 = correlated risk. Even if bullish on theme, consider rotating across themes |
| Using `top_movers[0]` as "the best pick" | Order is from `representative_stocks` (theme-detector ranking by liquidity / market cap), not by short-term-target confidence |
| Ignoring `regime_snapshot.spy_rsi_14` when > 80 | Extreme overbought market amplifies mean-reversion risk on individual bullish predictions |
| Treating predict failure as "ticker has no signal" | Could just be data fetch error. Check `short_term.error` field |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `error: no_theme_detector_cache` | theme-detector never run | Run `python3 skills/theme-detector/scripts/theme_detector.py` first |
| All movers `error: predict_timeout` | yfinance / network slow | Re-run; predict.py default timeout is 60s |
| `theme-detector cache > 24h old` warning | Stale theme data | Refresh theme-detector |
| Empty `themes[]` in output | theme-detector cache valid but `themes.all` is empty | Inspect cache file directly |
| `model_clamped: true` on many tickers | Drivers are extreme (large news + heat) | Expected during major catalyst days; check confidence |
| FRED snapshot missing | No fred-macro cache OR parse fails | Run `fred-macro/scripts/fetch.py` |

---

## How recommendations log is used downstream

```
data/recommendations/2026-04-25.json   ← thematic-screener writes
data/recommendations/2026-04-26.json
...
data/recommendations/2026-05-15.json

           ↓

Future Step 7: skills/short-term-target/scripts/weekly_review.py
           ↓
   Reads last 7 days of logs
           ↓
   Compares predictions to yfinance actuals
           ↓
   Per-horizon hit rate / per-theme alpha / failed-case analysis
           ↓
   Suggests config/weights.yaml adjustments
           ↓
   reports/SHORT_TERM_WEEKLY_<DATE>.md
```

**Important**: Logs accumulate from day 1. Don't delete `data/recommendations/*.json` — they are the validation evidence base.

---

## Performance notes

For default 5×4 = 20 tickers:
- short-term-target subprocess overhead: ~5s per call (yfinance + sector_intel I/O)
- Total wall time: 100-200s typical
- Memory: < 50MB
- Output file: ~50-80KB JSON per run

For larger universes (e.g., 10×5 = 50), consider:
- Adding a multiprocessing pool for parallel predict.py
- v0.2 enhancement; current sequential approach is fine for daily cadence
