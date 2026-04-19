---
description: Run momentum-monitor skill on a ticker (volume, MA crosses, short interest, composite score)
argument-hint: <TICKER>
---

Run the momentum-monitor skill on ticker `$ARGUMENTS` and present the result.

1. Execute the Python script:
   ```bash
   python3 skills/momentum-monitor/scripts/momentum.py $ARGUMENTS --json-only
   ```
2. Parse the JSON output.
3. Present a compact summary in this exact shape:

```
## $ARGUMENTS — Momentum Monitor  {price}  [{composite_label} {composite_score}/100]

| Block | Key Numbers |
|---|---|
| **Volume** | today {today} vs 20D avg {avg_20d} → **{ratio_20d}×** {spike_label} │ trend {volume_trend} │ spike days (last 10): {spike_days_last_10} |
| **MA Structure** | 20MA ${ma_20} / 50MA ${ma_50} / 200MA ${ma_200} → **{stage}** │ +{above_ma200_pct}% above 200MA |
| **Recent Crosses** | (list each cross type + days_ago; or "none in last 30 sessions") |
| **Short Interest** | {short_pct_float}% of float │ {short_ratio_days_to_cover}d cover │ last update {last_updated} → **{interpretation}** |
| **Composite Components** | volume_flow {v} / ma_stage {m} / squeeze {s} / trend_accel {t} |

**Signals**: (bullet list from `.signals[]`)
**Warnings**: (bullet list from `.warnings[]`)

> Data freshness: {cache_hit ? "cached " + cache_age_sec + "s ago" : "fresh fetch"}
```

If the script exits with `"skill_execution_failed": true`, report the error clearly
instead of fabricating numbers.
