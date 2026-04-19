---
description: Batch momentum screener across a ticker universe (S&P 500 or custom). Outputs ranked MD table + CSV.
argument-hint: [universe_or_flags]
---

Run the momentum screener with `$ARGUMENTS` (default: `--universe sp500 --min-score 60 --top 30`).

## Argument forms

Accept whatever the user passes. Common shapes:
- `sp500` → `--universe sp500 --min-score 60`
- `sp500 --min-score 70 --signal fresh_golden_cross_20_50`
- `AAPL,MSFT,NVDA,AMD` → `--tickers AAPL,MSFT,NVDA,AMD`
- Raw flags → pass through as-is

If `$ARGUMENTS` is empty, default to: `--universe sp500 --min-score 60 --top 30`.

## Execution

```bash
python3 skills/momentum-monitor/scripts/screen.py $ARGUMENTS --md-only
```

Then:
1. Print the Markdown table exactly as emitted (it is already formatted).
2. After the table, add one short line summarizing what stood out — e.g.
   "Top scorers concentrated in semis (NVDA, AMD, AVGO)" or
   "Only 3 matches — universe may be in corrective phase."
3. If >0 errors reported by the script, list up to 5 failed tickers and note
   "remaining errors in stderr / rerun with `--no-cache`".

## Guardrails

- Do NOT fabricate rows. If the script returns 0 matches, say so and suggest
  loosening filters (`--min-score`, drop `--signal`).
- Do NOT re-rank or reorder. The script has already ranked by
  composite score → volume ratio.
- Pricing comes from yfinance at 15-min cache freshness. For intraday
  certainty, suggest the user append `--no-cache` themselves.

## Filter cheatsheet (reference in one-line tips if the user asks)

| Want | Flags |
|---|---|
| Strong bullish only | `--min-score 75` |
| Breakout candidates | `--signal fresh_golden_cross_20_50 --stage "Stage 2 uptrend"` |
| Squeeze setups | `--signal squeeze_candidate` |
| Healthy trend (no blow-off) | `--min-score 65 --exclude-warning parabolic_blowoff_risk` |
| Custom watchlist | `--tickers-file path/to/list.txt` |
