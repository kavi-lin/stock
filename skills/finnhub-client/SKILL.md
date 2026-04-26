---
name: finnhub-client
description: Shared Finnhub API client used by other skills. Provides rate-limited (60/min), cached, retry-aware access to 17 Finnhub endpoints covering quotes, OHLCV, fundamentals, earnings calendar, earnings surprises, insider transactions, recommendation history, price targets, upgrades/downgrades, dividends, splits, IPOs, and SEC filings. Also exports adapters that normalize Finnhub raw responses into FMP-compatible shapes so that downstream code can swap providers without changing call sites. Use when another skill needs Finnhub data or when building a unified provider layer.
market: us-equity
scope: infrastructure
data_sources: [finnhub]
---

# Finnhub Client Skill

Shared infrastructure module — **not invoked directly by users**. Imported by other skills.

## Purpose

Provide a single, consistent client for Finnhub free-tier endpoints with:

- **Token-bucket throttle**: 60 calls/minute (Finnhub free-tier limit).
- **File cache**: mtime-based, per-endpoint TTL (mirrors `skills/fred-macro` and `skills/ftd-detector/scripts/fmp_client.py` patterns).
- **Retry**: exponential backoff on 429/5xx (max 3 retries).
- **Adapters**: normalize Finnhub raw payloads into FMP-shape so callers don't need to know which provider served the request.

## Endpoint Coverage (17 endpoints)

| Method | Finnhub Endpoint | Cache TTL | FMP equivalent |
|---|---|---|---|
| `quote(ticker)` | `/quote` | 5 min | `/api/v3/quote` |
| `candle(ticker, days)` | `/stock/candle` | 6 h | `/historical-price-full` |
| `profile(ticker)` | `/stock/profile2` | 7 d | `/profile` |
| `metric(ticker)` | `/stock/metric?metric=all` | 1 d | `/key-metrics` |
| `financials_reported(ticker)` | `/stock/financials-reported` | 1 d | `/income-statement` |
| `filings(ticker)` | `/stock/filings` | 6 h | `/sec-filings` |
| `company_news(ticker, days)` | `/company-news` | 1 h | — |
| `earnings_calendar(start, end)` | `/calendar/earnings` | 6 h | — (FMP-only via econ calendar, not earnings) |
| `earnings_surprise(ticker)` | `/stock/earnings` | 1 d | — |
| `insider_transactions(ticker)` | `/stock/insider-transactions` | 1 d | — |
| `insider_sentiment(ticker)` | `/stock/insider-sentiment` | 1 d | — |
| `recommendation(ticker)` | `/stock/recommendation` | 1 d | — |
| `price_target(ticker)` | `/stock/price-target` | 1 d | — |
| `upgrade_downgrade(ticker)` | `/stock/upgrade-downgrade` | 6 h | — |
| `dividends(ticker, start, end)` | `/stock/dividend2` | 1 d | — |
| `splits(ticker, start, end)` | `/stock/splits` | 7 d | — |
| `ipo_calendar(start, end)` | `/calendar/ipo` | 6 h | — |

## Authentication

Set `FINNHUB_API_KEY` in your environment. Free tier: 60 calls/minute, no documented daily cap.

```bash
export FINNHUB_API_KEY=...
```

## Programmatic Usage

```python
from skills.finnhub_client.scripts.finnhub_client import FinnhubClient

client = FinnhubClient()  # reads FINNHUB_API_KEY from env

q = client.quote("AAPL")
# → {"c": 178.32, "h": 179.01, "l": 177.50, "o": 178.00, "pc": 177.95, "t": 1714060800}

cal = client.earnings_calendar("2026-04-25", "2026-05-02")
# → {"earningsCalendar": [{"symbol": "MSFT", "date": "2026-04-29", "epsEstimate": 2.83, ...}]}
```

## Adapters (FMP-shape normalization)

When a downstream skill expects FMP-shaped data, use the adapters to translate:

```python
from skills.finnhub_client.scripts import adapters

raw = client.profile("AAPL")
fmp_like = adapters.profile_to_fmp(raw)
# → {"symbol": "AAPL", "companyName": "Apple Inc.", "sector": "Technology", ...}
```

Available adapters: `quote_to_fmp`, `candle_to_fmp_historical`, `profile_to_fmp`, `metric_to_fmp_key_metrics`.

## Side-by-side Diff Tool

To validate Finnhub data quality against FMP before flipping the primary provider, use:

```bash
bash skills/finnhub-client/scripts/run_diff.sh
# → outputs skills/finnhub-client/diff_reports/YYYYMMDD.md
```

The diff tool fetches the same fields from both providers across 10 default tickers, computes per-field percentage delta, and grades each (PASS <2%, WARN 2-5%, FAIL >5%). Use for one-off ad-hoc spot checks. For routine production ingest, use `dual_fetch.py` instead — see next section. Detailed usage in `README.md`.

## Dual-Fetch Discipline (production ingest)

`dual_fetch.py` is the production data-ingest entrypoint. It fetches canonical fields from **both** Finnhub and FMP and writes a single JSON per ticker with strict physical separation:

```json
{
  "scoring": { "_source": "finnhub", "price": ..., "peRatio": ..., ... },
  "_audit":  { "fmp": {...}, "diff": {...}, "fmp_status": "ok" }
}
```

**The hard rule — `_audit.*` MUST NOT reach the LLM prompt.**

Downstream code (LLM context construction, prompt assembly, scoring functions) MAY ONLY read `scoring.*`. The `_audit` underscore prefix is a python-style "private" flag enforced by code review and grep, not by runtime guards.

### Why this matters

The diff tool revealed that several canonical fields have **structural** provider divergence — same stock, same moment, different number, both correct under their own definition:

| Field | Divergence | Cause |
|---|---|---|
| `dividendYield` | 5-7% | Finnhub: indicated annual (forward); FMP: TTM trailing (backward) |
| `priceToBookRatio` | 12-38% | Different book-value snapshot (MRQ vs TTM avg) and goodwill treatment |

If the LLM sees both values, it invents its own weighting and **scoring becomes non-reproducible** — the same stock can score differently across runs depending on which value the model latched onto. By contrast, fixing Finnhub as the only scoring source guarantees that the same stock at the same moment always produces the same scoring inputs, while the parallel FMP fetch retains observability for drift detection.

### Drift monitoring

`audit_drift_check.py` scans `_audit.diff` from past N days and flags `(ticker, field)` pairs whose absolute divergence exceeded a threshold on >= MIN_HITS days. Run weekly. See `README.md` for cadence and interpretation.

```bash
python3 skills/finnhub-client/scripts/audit_drift_check.py --days 7 --threshold 5
```

### Failure modes

`fmp_status` in `_audit` is one of: `ok`, `quota_exceeded`, `unauthorized`, `http_<code>`, `network_error`. Scoring is **never** affected by audit-side failures — when FMP is unreachable, the day loses drift detection but analysis continues unchanged.

## Error Handling

- **429 (rate limit)**: client sleeps `Retry-After` seconds (or 60s default), retries up to 3 times. After 3 failures, raises `FinnhubRateLimit`.
- **403 (premium-required)**: client raises `FinnhubPremiumRequired` immediately — caller should fall back to FMP or skip the feature.
- **5xx / network**: exponential backoff (2s → 4s → 8s), then raises `FinnhubError`.
- **404 / empty payload**: returns `None` (matches FMP client convention).

## Cache Layout

```
skills/finnhub-client/cache/
├── quote_AAPL.json          # mtime-based TTL
├── candle_AAPL_365.json
├── profile_AAPL.json
├── earnings_calendar_2026-04-25_2026-05-02.json
└── ...
```

Cache dir is created on demand and gitignored (matches project-wide `skills/*/cache/` rule).

## Limitations

- Free tier: candles limited to **US stocks only**; deeper history (>1 yr) requires premium.
- `/calendar/economic` is **premium-only** — keep using FMP for economic events.
- `/stock/social-sentiment`, `/news-sentiment`, `/stock/institutional-ownership` are **premium-only** — not exposed by this client.
- `financials_reported` returns **raw SEC XBRL filings**. Concept tagging, units, and GAAP/non-GAAP classification are inconsistent across companies. **Do not use as a financial-statement primary** — FMP `/income-statement`, `/balance-sheet`, `/cash-flow-statement` remain the canonical source. The included `adapters.financials_to_fmp_income()` is intentionally lossy (top-line only) and is for raw-filing reference, not for quality models.

## Architecture Role

This client serves the **market & events layer**. Allocation:

| Layer | Provider | Why |
|---|---|---|
| Market data (quote / OHLCV / profile) | Finnhub primary | Low shape ambiguity, identical units |
| Events (earnings calendar / surprise / insider / upgrades) | Finnhub only | FMP doesn't cover these |
| Simple metrics (P/E, ROE, div yield, P/B) | **Finnhub canonical, FMP audit** (dual-fetch) | Resolved by `dual_fetch.py`: Finnhub feeds scoring; FMP fetched in parallel for drift monitoring only. See § Dual-Fetch Discipline. |
| **Financial statements (income / balance / cash flow)** | **FMP primary** | Normalized shape, consistent CFO/NI/share count — Finnhub raw XBRL would drift quality models |
| Economic calendar | FMP only | Finnhub free tier doesn't expose |
| Analyst estimates (forward EPS numerical) | FMP only | Finnhub gives buy/hold/sell counts, not numerical forecasts |

This is a 7-PR migration:
- **PR-1** (this skill): Finnhub client infrastructure ✓
- **PR-2** (`diff_tool.py`): Side-by-side validation harness ✓
- **PR-3**: Run diff tool 5-7 days, decide simple-metric primary
- **PR-4**: `data-client` abstraction with per-resource provider routing + source tagging + conflict detection
- **PR-5**: Migrate `ftd-detector` (lowest-risk pilot)
- **PR-6**: Migrate `market-top-detector`, `us-stock-analysis`
- **PR-7**: Wire new Finnhub-only features (earnings calendar, PEAD, insider monitor)
