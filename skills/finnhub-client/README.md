# finnhub-client — Usage Guide

Companion to `SKILL.md` (architecture / endpoint reference) and `CHANGELOG.md` (version history). This file is the **how-to** for the three operational scripts.

---

## Three scripts, three purposes

| Script | When to use | Output |
|---|---|---|
| `dual_fetch.py` | Production data ingest for stock analysis. Run before `分析 [TICKER]` or batch screening. | `data/YYYY-MM-DD/{TICKER}.json` |
| `audit_drift_check.py` | Periodic health check (weekly cron, or before big decisions). Detects whether provider methodology has drifted. | Markdown report (stdout or file) |
| `diff_tool.py` | One-off side-by-side validation. Used during initial provider migration. | `diff_reports/YYYYMMDD.md` |

`dual_fetch.py` is what you run **routinely**. `audit_drift_check.py` reads what `dual_fetch.py` wrote. `diff_tool.py` is for ad-hoc spot-checks.

---

## 1. dual_fetch.py — production data ingest

Pulls canonical fields from **both** Finnhub and FMP, writes a structured JSON.
Finnhub side feeds scoring; FMP side is audit-only.

### Run

```bash
# default 10 reference tickers
bash skills/finnhub-client/scripts/run_dual_fetch.sh

# custom tickers
bash skills/finnhub-client/scripts/run_dual_fetch.sh --tickers AAPL,MSFT,NVDA

# bypass Finnhub cache (force live)
bash skills/finnhub-client/scripts/run_dual_fetch.sh --no-cache

# direct python
python3 skills/finnhub-client/scripts/dual_fetch.py --tickers AAPL --output-dir /tmp
```

### Output structure

```json
{
  "ticker": "AAPL",
  "fetched_at": "2026-04-25T03:55:18Z",
  "scoring": {
    "_source": "finnhub",
    "price": 271.06,
    "peRatio": 33.79,
    "epsTTM": 7.90,
    "dividendYield": 0.38,
    "priceToBookRatio": 50.98,
    ...
  },
  "_audit": {
    "fmp": { "price": 271.06, "peRatio": 33.94, ... },
    "diff": { "peRatio_pct": 0.46, "priceToBookRatio_pct": -11.08, ... },
    "fmp_status": "ok"
  }
}
```

### **The hard rule**

Downstream code (LLM context construction, prompt assembly, scoring functions)
**MAY ONLY READ `scoring.*`**. The `_audit` underscore prefix marks the section
as private — it exists for drift monitoring and post-mortem analysis, never
for inference inputs.

Why this matters: if both numbers reach the LLM, the model invents its own
weighting/judgment, which becomes a new noise source on top of provider
disagreement. See CHANGELOG v1.1.0 "Architecture decision" for the full
rationale.

### Library use (preferred)

```python
from skills.finnhub_client.scripts.dual_fetch import fetch_dual
from skills.finnhub_client.scripts.finnhub_client import FinnhubClient
import os, requests

client = FinnhubClient()
session = requests.Session()
bundle = fetch_dual("AAPL", client, os.environ["FMP_API_KEY"], session)

llm_input = bundle["scoring"]   # safe to render into prompt
audit_log = bundle["_audit"]    # log only, do NOT pass to LLM
```

### `fmp_status` values

| Value | Meaning | Effect on `diff` |
|---|---|---|
| `ok` | Both sides fetched successfully | Computed |
| `quota_exceeded` | FMP returned HTTP 402 | Empty `diff`, scoring still valid |
| `unauthorized` | FMP returned 401/403 (key invalid or endpoint blocked) | Empty `diff`, scoring still valid |
| `http_<code>` | Other HTTP error | Empty `diff` |
| `network_error` | Connection failure | Empty `diff` |

**Scoring is unaffected** by audit-side failures. The skill degrades gracefully:
when FMP is unreachable, you lose drift detection that day but analysis continues.

---

## 2. audit_drift_check.py — drift monitoring

Scans the last N days of dual-fetch outputs and flags fields whose
provider divergence has been persistent (not just one-off noise).

### Run

```bash
# default: last 7 days, threshold 5%, min 3 hit days
python3 skills/finnhub-client/scripts/audit_drift_check.py

# stricter: last 30 days, threshold 10%, min 5 hit days
python3 skills/finnhub-client/scripts/audit_drift_check.py --days 30 --threshold 10 --min-hits 5

# write to file
python3 skills/finnhub-client/scripts/audit_drift_check.py --output drift_report.md
```

### Sample output

```
# Audit Drift Report — last 7 days

**Threshold**: |diff| >= 5.0%
**Min hits**: 3 days out of 7
**Total samples scanned**: 70

## Persistent drift

| Ticker | Field | Hits | Samples | Max |diff%| | Avg diff% |
|---|---|---:|---:|---:|---:|
| AMD  | priceToBookRatio | 7 | 7 | 38.08% | -36.42% |
| TSLA | priceToBookRatio | 6 | 7 | 25.86% | +24.10% |
| MSFT | dividendYield    | 5 | 7 |  6.83% |  +6.41% |
```

### How to act on it

- **Persistent P/B drift** (most common): expected — see CHANGELOG. Only
  alarming if a previously-PASSing field starts drifting (suggests upstream
  data issue at one provider).
- **Sudden new drift on a previously-PASSing field**: investigate. Likely
  causes: stale Finnhub cache, FMP corporate-action backfill lag, share count
  change after a split/buyback.
- **All fields drifting on one ticker**: that ticker likely had a recent
  corporate action (split, spin-off, M&A) that one provider hasn't reflected yet.

### Suggested cadence

Weekly. Add to a cron or run manually before any large rebalancing decision.

---

## 3. diff_tool.py — one-off validation

The original validation tool. Use when:
- Adding a new ticker to the universe and want to spot-check both providers agree
- After an FMP plan change or endpoint migration
- Investigating a single drift report finding

```bash
bash skills/finnhub-client/scripts/run_diff.sh
# default 10 tickers, writes diff_reports/YYYYMMDD.md

bash skills/finnhub-client/scripts/run_diff.sh --tickers BRK.B
```

Output is a per-ticker, per-field PASS/WARN/FAIL grade table. Less structured
than dual_fetch — meant for human reading, not pipeline consumption.

---

## Setup

```bash
export FINNHUB_API_KEY=...
export FMP_API_KEY=...
```

Both keys required for `dual_fetch.py` and `diff_tool.py`. Only `FINNHUB_API_KEY`
required if you bypass FMP entirely (not recommended — you lose audit signal).

---

## File layout

```
skills/finnhub-client/
├── SKILL.md                 # endpoint reference, architecture, error handling
├── README.md                # this file
├── CHANGELOG.md             # version history
├── cache/                   # Finnhub response cache (gitignored, mtime-TTL)
├── data/                    # dual_fetch outputs (gitignored)
│   └── YYYY-MM-DD/
│       └── TICKER.json
├── diff_reports/            # diff_tool outputs (committed for history)
│   └── YYYYMMDD.md
└── scripts/
    ├── finnhub_client.py    # base API client
    ├── adapters.py          # Finnhub→FMP shape adapters
    ├── dual_fetch.py        # ★ production ingest
    ├── audit_drift_check.py # ★ drift monitor
    ├── diff_tool.py         # validation harness
    ├── run_dual_fetch.sh    # wrapper
    └── run_diff.sh          # wrapper
```
