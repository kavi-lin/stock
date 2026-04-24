# Changelog — earnings-valuation-forecaster

All notable changes to this skill.

---

## v1.1.0 — 2026-04-25

### Added
- **Peer PE blending** (`blend_pe`): fetches up to 5 peers via FMP `/stock-peers`
  (dynamic); falls back to static `PEER_MAP` for 10 common tickers. Own-history
  PE and peer median blended 70/30. Peer info surfaced in JSON payload and Markdown.
- **Interest-rate regime adjustment** (`rate_adjust_pe`): reads `real_rate_preferred`
  (DFII10) from `skills/fred-macro/cache/fred_latest.json`. Applies a multiplier to
  the blended PE range based on regime (accommodative ×1.08 → restrictive ×0.82).
  Falls back to 4.5% real rate if cache unavailable.
- **Expected value** (`calc_expected_value`): probability-weighted target price.
  Bear/base/bull probabilities scaled by forward EPS confidence (HIGH=20/60/20,
  MEDIUM=25/50/25, LOW=30/40/30). Added `expected_value` and
  `expected_value_upside_pct` to payload.
- **Advisory signal** (`valuation_signal`): STRONG BUY / BUY / HOLD / TRIM / SELL
  based on current price vs expected value and base target. Added `signal` to payload.
- **`multiple_range_effective`** in payload: the adjusted PE range actually used for
  scenario calculations (post peer-blend + rate-adjust), distinct from `multiple_range`
  (raw own-history).
- **Markdown improvements**: signal badge in header, EV row in scenarios table,
  PE section now shows raw → peer blend → rate adjust → effective values.
- **PEER_MAP expanded**: added META, JPM, XOM, AMD entries.
- `FMP.stock_peers()` method for dynamic peer lookup.
- Updated caveats to cover peer blending and rate adjustment limitations.

### Changed
- `run()`: PE range pipeline now `pe_percentiles → blend_pe → rate_adjust_pe`
  before passing to `build_scenarios()`.
- `sensitivity_axes` rows now reflect effective (adjusted) PE values.
- Caveats list updated (removed generic DCF disclaimer; added peer/rate notes).

---

## v1.0.0 — 2026-04-20

### Added
- Initial implementation.
- Three-method forward EPS: trailing CAGR (×0.7 dampened), analyst consensus
  (FMP `/analyst-estimates`), linear trend regression.
- EPS confidence scoring (HIGH / MEDIUM / LOW) based on inter-method spread.
- PE percentile range from 5 years of FMP annual ratios (p25 / p50 / p75).
- 3×3 scenario sensitivity grid (EPS ±15% × PE p25/p50/p75).
- Bull / base / bear targets with falsifiable trigger conditions.
- TTM EPS guard: rejects negative-EPS tickers with `status: unsupported`.
- 4-hour per-ticker JSON cache with `--no-cache` / `--max-age` CLI flags.
- FMP 429 exhausted-flag guard (prevents infinite retry on daily quota hit).
- Markdown output with `--output-dir` flag → `reports/YYYYMMDD_<TICKER>_valuation.md`.
- `--json-only` CLI flag for machine-readable output.
