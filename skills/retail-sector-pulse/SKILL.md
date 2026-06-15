---
name: retail-sector-pulse
description: Aggregate retail-perspective sentiment + multi-day direction by sector for the Tactical Opportunity Radar. Use when user asks for sector-level retail sentiment, "how are retail investors feeling about X sector", per-sector 3-7 day direction outlook, or wants to know which sector has news/Reddit/forecast divergence. Daily-only V3.20.0 (intraday refresh deferred V3.21+).
---

# Retail Sector Pulse

## Purpose

Produce per-sector (11 GICS sectors) daily snapshot of:

1. **News sentiment** — weighted avg of recent (72h) news-digest `net_impact_score`, joined by `affected_sectors[]`
2. **Retail discussion volume** — retired with narrative-pulse-detector (V3.34); component degrades gracefully to `score=None` / `sample_size=0`. Candidate future source: break_news social adapters (Reddit / HN)
3. **5-day direction forecast** — median `target_central_pct` + bullish-breadth % across `SECTOR_TOP_5`, via `short-term-target/predict.py`
4. **Composite direction label** — declarative weighted blend (see `config/weights.yaml`)
5. **Rule-based framing** — one-line 大白話 summary per sector (no LLM)

Output feeds `Dashboard/data.json['tactical']['retail_sector_pulse']` via `bridge.py`; rendered by `page-radar.js` as 11-card 4-column grid above Narrative Pulse.

## Triggers

- `python3 skills/retail-sector-pulse/scripts/aggregate.py` (CLI)
- Auto-invoked by `daily_update.sh` Step 9.5 (before bridge)

## Inputs (all retail-accessible)

| Source | Field used |
|---|---|
| `news/news_logs/<DATE>_digest.json` | `verdicts[].{verdict, net_impact_score, affected_sectors[], tickers_mentioned[], headline, source_label, published}` |
| `skills/short-term-target/scripts/predict.py` (called per ticker) | `horizons.5d.{target_central_pct, confidence, status}` |
| `skills/_shared/company_context.py` | `SECTOR_TOP_5` (11 × 5 ticker roster) |

**No new LLM calls.** Existing deep-digest verdicts are already LLM-processed, but inputs are 100% RSS-accessible.

## Output

`Dashboard/retail_sector_pulse.json` (~50 KB):

```jsonc
{
  "version": "1.0",
  "as_of": "<ISO>",
  "weights_version": "v1.0",
  "lookback_hours": 72,
  "horizon": "5d",
  "universe_size": 55,
  "sectors": [{ /* per-sector record, 11 total */ }]
}
```

See `tests/test_aggregate.py` fixtures for full per-sector schema.

## Configuration

All scoring formulas + labels in `config/weights.yaml`:

- `composite.{news_sentiment_norm,predicted_5d_pct_norm,retail_volume_signed}` — weighted blend to [-1, +1]
- `direction_labels` / `retail_volume_labels` / `news_sentiment_labels` / `predicted_5d_labels` — 5-tier bucket thresholds
- `sector_aliases` — normalize messy digest sector names (`"Real Estate"` / `"Tech"` / `"Semiconductors"` → canonical `SECTOR_UNIVERSE` key)

Bump `weights_version` after any edit; downstream consumers detect the change.

## CLI

```bash
# Default: read everything fresh, write Dashboard/retail_sector_pulse.json
python3 skills/retail-sector-pulse/scripts/aggregate.py

# Specific date
python3 skills/retail-sector-pulse/scripts/aggregate.py --date 2026-05-25

# Custom output path (for testing)
python3 skills/retail-sector-pulse/scripts/aggregate.py --output /tmp/rsp.json

# Skip predict.py (faster smoke; use cached predict results if any)
python3 skills/retail-sector-pulse/scripts/aggregate.py --skip-predict
```

## Discipline

Retail Sector Pulse is **exploratory display layer**. It does **NOT** influence:

- `investment_protocol_v5_0` (Phase 4.5 fair_value, buy_threshold, position_size)
- `momentum-monitor` or `thematic-screener` ranking
- Any auto-trading or alert logic

It only informs the user via the radar dashboard. Per-sector composite_score is a **suggestion direction**, not a buy/sell signal.

## V3.20.0 → V3.21+ Roadmap

- **V3.21+**: Intraday 4h refresh via `dashboard_server` daemon thread (after V3.20 stability confirmed)
- **V3.22+**: Optional LLM-enriched framing (Haiku 4.5 polishes the rule-based template line)
- **V3.23+**: Per-sector FTD pattern tracking
