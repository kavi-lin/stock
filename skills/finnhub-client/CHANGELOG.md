# CHANGELOG — finnhub-client

## v1.1.0 — 2026-04-25

### Added
- **`scripts/dual_fetch.py`** — dual-provider fetch with physical separation. Pulls canonical fields from both Finnhub (scoring) and FMP (audit), writes a single JSON per ticker under `data/YYYY-MM-DD/`. Top-level `scoring.*` is the only surface downstream code may pass to LLM; `_audit.*` is reserved for human / drift-checker consumption.
- **`scripts/audit_drift_check.py`** — scans the last N days of audit logs, flags `(ticker, field)` pairs whose absolute provider diff exceeds a threshold on >= MIN_HITS days. Default: 7 days, 5%, 3 hits.
- **`scripts/run_dual_fetch.sh`** — wrapper that asserts both API keys are set before invoking `dual_fetch.py`.
- **`data/`** directory for output, gitignored via `data/.gitignore`.

### Changed
- **FMP endpoints migrated v3 → stable** in `diff_tool.py`. Old `/api/v3/quote/{ticker}` and `/api/v3/key-metrics-ttm/{ticker}` returned HTTP 403 on current FMP plans. New paths use `/stable/quote?symbol=X` and `/stable/ratios-ttm?symbol=X`.
- **PE adapter mapping** in `adapters.py:121`: `peTTM` now preferred over `peNormalizedAnnual` so Finnhub's PE matches FMP's `priceToEarningsRatioTTM` definition. Reduces normal-stock PE diff from 5-15% to <1%.

### Architecture decision: dual-fetch over fallback
After running the diff tool, several canonical fields showed real provider methodology divergence that cannot be resolved by either choosing one provider or by averaging:

| Field | Provider divergence | Root cause |
|---|---|---|
| `dividendYield` | 5-7% | Finnhub uses indicated annual (forward), FMP uses TTM trailing (backward) |
| `priceToBookRatio` | 12-38% | Different book value snapshot (MRQ vs TTM avg) and different goodwill/intangibles treatment |

**Decision**: Finnhub becomes the **only** source feeding scoring inputs. FMP is fetched in parallel for cross-provider observability but never reaches the LLM prompt. This preserves scoring reproducibility (same stock at same time produces same numbers across runs) while retaining drift-monitoring capability.

The discipline is enforced by naming convention (`_audit` underscore prefix) and documented in `SKILL.md` § Dual-Fetch Discipline.
