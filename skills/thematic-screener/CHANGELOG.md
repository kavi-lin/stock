# CHANGELOG — thematic-screener

## v0.1.0 — 2026-04-25

### Added (initial release — Step 3 of plan_short.md)

- **`scripts/screen.py`** — main aggregator. Reads theme-detector cache, calls short-term-target per representative_stock, attaches FRED + market regime snapshot, writes `data/recommendations/<DATE>.json`.
- **`SKILL.md`** — formal spec.
- **`README.md`** — usage walkthrough + troubleshooting + daily workflow.
- `data/recommendations/.gitignore` — log files not committed (per plan_short Step 5 design).
- `cache/.gitignore` — placeholder for v0.2 cache layer.

### Architecture choices (per plan_short.md)

- **No own data fetching** — relies entirely on theme-detector cache + short-term-target subprocess + fred-macro cache + yfinance for SPY/VIX.
- **Subprocess to call short-term-target**: skill independence preserved; ~5-15s × N tickers is acceptable for daily cadence.
- **Concentration is WARNING not REMOVE** (per §11.B修正): same-theme ≥ 2 → adds `concentration_flag` but keeps both picks. User decides.
- **Theme = concentration proxy in v0.1**: GICS sub-industry lookup deferred to v0.2.
- **No FRED → theme scoring** (per §12.E硬版拒絕): only records FRED state in regime_snapshot; humans/LLM judge.
- **Day-1 outcome log writing**: every run writes `data/recommendations/<DATE>.json` with full regime context for future Step 7 evaluation.

### Smoke test results (2026-04-25)

| Run | Themes | Movers | Calls | Wall time | Status |
|---|---|---|---|---|---|
| 2×2 (smoke) | Clean Energy, Defense | 2 each | 4 | ~30s | ✅ |
| 3×3 (real) | Clean Energy, Defense, Basic Materials | 3 each | 9 | ~90s | ✅ wrote 60KB log |

Verified:
- ✅ theme-detector cache loaded correctly (top 5 themes by heat)
- ✅ representative_stocks per theme extracted properly
- ✅ short-term-target subprocess returns valid JSON for each ticker
- ✅ concentration_flag triggers correctly when ≥2 picks share theme
- ✅ regime_snapshot populated (SPY 713.94, RSI 87.4, VIX 18.71, FRED expansion)
- ✅ Output file written to data/recommendations/<DATE>.json
- ✅ EXPERIMENTAL flag in metadata

### Known limitations (v0.1)

- Concentration grain is THEME, not GICS sub-industry (proxy). Same theme = warning. v0.2 will add GICS lookup.
- `fred_alignment` field per theme always "neutral" — placeholder for v0.2.
- No own caching; if theme-detector cache > 24h old, just adds warning (doesn't refresh).
- Sequential predict.py calls; no parallelization (acceptable for ≤30 tickers/run).
- Reads upstream caches only; does not trigger upstream refresh.

### Validation roadmap

This skill launches **without backtest validation** — by design, per plan_short.md §6 + §12.H.

Day-1 logs accumulate to `data/recommendations/`; first formal evaluation at N≥30 days of logs (~3-4 weeks daily) via Step 7 `weekly_review.py` (TBD).

Failure threshold (per plan §6 + §12.H): if 8-week hit rate < 50% **OR** median alpha vs benchmark < 0% → entire system retired.

### Next steps (per plan_short.md)

- **Step 4** (Dashboard): Build "Tactical Opportunity Radar" panel reading data/recommendations/<latest>.json
- **Step 7** (weekly_review.py): Build weekend recalibration tool reading recommendations log + comparing to actuals
- **Step 6** (daily_update.sh): Wire thematic-screener into daily auto-refresh
