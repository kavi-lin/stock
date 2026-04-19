---
description: Forward-return journal — snapshot/update/stats. Tracks 5/20/60d returns per screener entry.
argument-hint: <snapshot|update|stats> [csv_path]
---

Run the momentum journal subcommand from `$ARGUMENTS`.

## Subcommands

| Subcommand | Purpose | When to run |
|---|---|---|
| `snapshot <csv>` | Append a screener CSV's rows to journal.jsonl | Usually auto-invoked via `screen.py --journal`; manual only if you forgot the flag |
| `update` | Fill delayed forward returns (5/20/60d + MAE/MFE) | **Run daily** after market close — yfinance fills whatever horizons have matured |
| `stats` | Aggregate journal → stats.json + print MD summary | After `update`, or anytime you want to see current signal performance |

## Execution

```bash
python3 skills/momentum-monitor/scripts/journal.py $ARGUMENTS
```

## After running

- `snapshot`: report the number added/skipped, journal total
- `update`: report how many fills occurred; if 0 and journal has pending entries, note that markets are closed or data isn't available yet
- `stats`: print the MD summary output directly — it already has the winner table

## Interpretation hints (for stats output)

- Signals with `n < 10` → statistically noisy, don't over-interpret
- `win_rate ≥ 0.55` with `n ≥ 20` → worth flagging as potential edge
- `mean` close to 0 but `win_rate > 0.6` → lots of small wins, few big losses — common for momentum
- If all signals show `win_rate ≈ 0.5` → filter is not selecting edge, consider tightening `--min-score` in screen.py

## Guardrails

- Do NOT edit journal.jsonl manually — journal.py maintains integrity
- Do NOT interpret signals with `n < 5` as evidence either way
