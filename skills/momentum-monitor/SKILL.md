---
name: momentum-monitor
description: Per-stock momentum & flow monitor — volume dynamics, MA structure & crosses, short interest, spike detection. Use when user asks about 爆大量, 動能, volume spike, moving average cross, short interest / squeeze potential, or a quick bullish/bearish flow read on a single ticker.
market: market-agnostic
scope: universe-scan
data_sources: [yfinance]
---

# Momentum Monitor

## Purpose
Single-ticker technical flow read:
- **Volume**: today vs 20/50D avg, spike detection, recent heavy-volume days
- **MA structure**: 20/50/200 stack, Stage classification (Weinstein 1-4), cross events
- **Short interest**: % of float, days-to-cover, squeeze-candidate flag
- **Composite momentum score** (0-100) with component breakdown

Designed as a focused companion to `technical-analyst` skill — technical-analyst handles
RSI/MACD/chart patterns; this skill handles the **tape/flow** side (volume + shorts + MA crosses).

## Usage

```bash
# Standalone (any terminal)
python3 skills/momentum-monitor/scripts/momentum.py TSLA
python3 skills/momentum-monitor/scripts/momentum.py TSLA --json-only
python3 skills/momentum-monitor/scripts/momentum.py TSLA --no-cache
python3 skills/momentum-monitor/scripts/momentum.py TSLA --max-age 300
```

Within Claude Code, trigger via:
- Slash: `/momentum-monitor TSLA`
- Natural language: 「動能 TSLA」or「momentum TSLA」

## Screener (batch mode)

`scripts/screen.py` runs `momentum.py`'s `analyze()` in parallel across a
universe, then filters, ranks, and emits CSV + Markdown. Same cache as
single-ticker mode, so repeat runs within 15 min are near-instant.

```bash
# Built-in S&P 500 universe, bullish filter
python3 skills/momentum-monitor/scripts/screen.py --universe sp500 --min-score 70

# Custom ticker list
python3 skills/momentum-monitor/scripts/screen.py --tickers AAPL,MSFT,NVDA,AMD

# Watchlist file (one ticker per line; # comments allowed)
python3 skills/momentum-monitor/scripts/screen.py --tickers-file my_watchlist.txt

# Multi-filter: Stage 2 uptrend + fresh golden cross, exclude blow-off risk
python3 skills/momentum-monitor/scripts/screen.py \
  --universe sp500 \
  --stage "Stage 2 uptrend" \
  --signal fresh_golden_cross_20_50 \
  --exclude-warning parabolic_blowoff_risk \
  --top 25
```

### Filter flags
| Flag | Effect |
|---|---|
| `--min-score N` / `--max-score N` | Composite score bounds |
| `--stage "Stage 2 uptrend"` | Exact stage match |
| `--label BULLISH` | Composite label match |
| `--signal X` (repeatable, AND) | Required signal in `.signals[]` |
| `--exclude-signal X` / `--exclude-warning X` | Negative filters |

### Execution flags
| Flag | Default | Effect |
|---|---|---|
| `--workers N` | 15 | Parallel yfinance fetches |
| `--no-cache` | off | Force fresh fetch for every ticker |
| `--max-age SEC` | 900 | Cache TTL |
| `--top N` | 30 | MD table row limit (CSV always has all) |
| `--output-dir PATH` | `cache/` | Where to write `screen_YYYYMMDD_HHMM.csv` |
| `--json` | off | Also print full JSON summary to stdout |

### Universes
Ship with `scripts/universes/sp500.txt` (503 tickers). Add your own file
there and pass its name: `--universe my_list`.

### Trigger
- Slash: `/momentum-screen` (see `.claude/commands/momentum-screen.md`)
- Natural language: 「動能選股」/「momentum screen」

## Forward-return journal

`scripts/journal.py` accumulates screener results over time and fills in
5/20/60-day forward returns so you can measure signal quality empirically.

```bash
# Record today's screen (or pass --journal to screen.py so it auto-appends)
python3 skills/momentum-monitor/scripts/journal.py snapshot cache/screen_YYYYMMDD_HHMM.csv

# Run DAILY after market close to fill matured returns
python3 skills/momentum-monitor/scripts/journal.py update

# Aggregate + print summary
python3 skills/momentum-monitor/scripts/journal.py stats

# Wipe journal + stats (asks for YES confirmation; use --yes to skip)
python3 skills/momentum-monitor/scripts/journal.py clear
```

### Data layout

- `skills/momentum-monitor/journal/journal.jsonl` — append/update-only, one JSON per snap × ticker
- `skills/momentum-monitor/journal/stats.json` — rolling aggregates (by_signal, by_score_bin, by_stage)

### Journal entry schema

```json
{
  "snap_id": "screen_20260418_1430",
  "snap_date": "2026-04-18",
  "ticker": "NVDA",
  "entry_price": 201.68,
  "score": 72.5,
  "label": "BULLISH",
  "stage": "Stage 2 uptrend",
  "ratio_20d": 1.35,
  "above_ma200_pct": 11.0,
  "signals": ["fresh_golden_cross_20_50", "volume_expansion"],
  "warnings": [],
  "returns": {
    "5d":  {"value": null, "filled_date": null},
    "20d": {"value": 4.2,  "filled_date": "2026-05-15"},
    "60d": {"value": null, "filled_date": null}
  },
  "mae_20d": -1.8,
  "mfe_20d":  6.4,
  "updated_at": "2026-05-15T16:05:10"
}
```

### Stats output (by_signal)

Per signal: `n`, `win_rate`, `mean`, `median`, `p25`, `p75`, `min`, `max`
(default horizon = 20d). Also `mae_mfe_by_signal` with mean/median MAE and MFE.

### Recommended cadence

- Daily: `screen.py --journal` once pre-open (records tickers seen)
- Daily post-close: `journal.py update` then `journal.py stats`
- After 4-6 weeks: examine `by_signal` — signals with `n ≥ 30 AND win_rate ≥ 0.55`
  are candidates to promote into edge-candidate-agent tickets

### Trigger
- Slash: `/momentum-journal <snapshot|update|stats>`
- Natural language: 「更新 journal」/「journal stats」

## Caching
Per-ticker file cache at `skills/momentum-monitor/cache/momentum_<TICKER>.json`,
default TTL **900 s (15 min)**. yfinance data doesn't need sub-minute granularity
for this read; 15 min is enough. `--no-cache` forces a fresh fetch.

## Output schema

```json
{
  "ticker": "TSLA",
  "generated_at": "ISO-8601",
  "price": 400.62,
  "cache_hit": false,
  "cache_age_sec": 0,

  "volume": {
    "today":        65000000,
    "avg_20d":      48000000,
    "avg_50d":      52000000,
    "ratio_20d":    1.35,
    "spike_label":  "NORMAL | MILD_SPIKE (>=2x) | HEAVY_SPIKE (>=3x)",
    "spike_days_last_10": 2,
    "volume_trend": "expanding | stable | contracting"
  },

  "ma_structure": {
    "ma_20":  395.50,
    "ma_50":  380.12,
    "ma_200": 310.40,
    "stage":  "Stage 1 basing | Stage 2 uptrend | Stage 3 top | Stage 4 downtrend",
    "above_ma20_pct":  1.3,
    "above_ma200_pct": 29.1,
    "recent_crosses": [
      {"type": "golden_cross_20_50", "date": "YYYY-MM-DD", "days_ago": 14}
    ]
  },

  "short_interest": {
    "shares_short":             18500000,
    "short_pct_float":          1.2,
    "short_ratio_days_to_cover": 2.3,
    "last_updated":             "YYYY-MM-DD",
    "interpretation":           "low | moderate | high | squeeze_candidate"
  },

  "rsi": {
    "rsi_14": 68.4,
    "zone":   "oversold | neutral | bullish | overbought"
  },

  "momentum_composite": {
    "score": 72,
    "label": "BEARISH | WEAK | NEUTRAL | BULLISH | STRONGLY_BULLISH",
    "components": {
      "volume_flow":             60,
      "ma_stage":                95,
      "short_squeeze_potential": 20,
      "trend_acceleration":      80
    }
  },

  "signals":  ["stage2_uptrend_intact", "volume_expansion", "low_short_interest"],
  "warnings": []
}
```

## Composite Score formula

Equal-weight (25% each) of 4 components, each normalized 0-100:

1. **volume_flow (25%)** — expansion vs contraction
   - `ratio_20d ≥ 1.5 AND today > prev day` → 80-100
   - `ratio_20d ≥ 1.0` → 50-80
   - `ratio_20d < 0.7` → 20-40

2. **ma_stage (25%)** — Weinstein stage
   - Stage 2 uptrend (20>50>200) → 90-100
   - Stage 1 basing (flat above rising 200) → 60-70
   - Stage 3 top → 30-50
   - Stage 4 downtrend (20<50<200) → 0-20

3. **short_squeeze_potential (25%)** — high short + positive momentum
   - `short_pct_float > 20% AND above_ma20_pct > 5%` → 80+
   - `short_pct_float 10-20%` → 50-70
   - `short_pct_float < 3%` → 10-30 (no fuel)

4. **trend_acceleration (25%)** — how far above long-term MA + recent cross
   - Recent golden_cross_50_200 in last 10 days → 90+
   - `above_ma200_pct 20-50%` healthy uptrend → 70-80
   - `above_ma200_pct > 100%` parabolic exhaustion → 20-40

## Spike detection rules
- `volume_today / avg_20d ≥ 3.0` → **HEAVY_SPIKE** (`spike_label`)
- `volume_today / avg_20d ≥ 2.0` → **MILD_SPIKE**
- Else → **NORMAL**

`spike_days_last_10`: count of days in last 10 sessions where `volume ≥ 2× avg_20d`.

## MA cross detection
Scans last 30 sessions for these events:
- `golden_cross_20_50` — 20MA crosses above 50MA
- `death_cross_20_50`  — 20MA crosses below 50MA
- `golden_cross_50_200` — 50MA crosses above 200MA (major bull)
- `death_cross_50_200`  — 50MA crosses below 200MA (major bear)

## Signals glossary (output `.signals[]`)
- `stage2_uptrend_intact` — MA stack 20>50>200 valid
- `volume_expansion` — ratio_20d ≥ 1.3 + today up
- `volume_dry_up` — ratio_20d < 0.7
- `low_short_interest` / `high_short_interest` / `squeeze_candidate`
- `parabolic_blowoff_risk` — above_ma200_pct > 50%
- `fresh_golden_cross` — golden_cross_20_50 within 10 days
- `fresh_death_cross` — death_cross_20_50 within 10 days
- `overbought_rsi` — RSI-14 > 70 (**warning**, near-term exhaustion)
- `oversold_rsi` — RSI-14 < 30 **AND** Stage 2 uptrend (**signal**, momentum pullback buy; oversold in a downtrend is weakness, not opportunity — not flagged)

## RSI (Wilder's 14-period)

Classic Wilder smoothing (first value is 14-period SMA, subsequent use exponential
with α = 1/14). Pure tape indicator, **not included in composite score** because
it overlaps with `trend_acceleration` — kept as independent signal/warning + CSV
column so you can filter or analyze separately.

CLI:
```bash
python3 screen.py --universe sp500 --max-rsi 70   # exclude overbought
python3 screen.py --universe sp500 --min-rsi 30 --max-rsi 60  # non-extreme zone
```

## Limitations
- Short interest updates biweekly (FINRA/Yahoo schedule) — `last_updated` may be 1-2 weeks old
- `short_pct_float` from yfinance `info`; occasionally null for micro-caps → interpretation = "unknown"
- Volume "trend" uses 5-day rolling comparison — noisy for low-liquidity tickers
- 融資 (Taiwan-style margin debt per stock) not available in US — absent from this skill
