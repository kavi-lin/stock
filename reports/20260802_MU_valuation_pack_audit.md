# MU canonical valuation-pack audit — 2026-08-02

Command:

```bash
python3 investment/scripts/compute_price_framework.py --self-assemble --no-fetch
```

Input contained only ticker, current price `$823.03`, and a confirmed structural-shift record
(`evidence_date=2026-06-25`, provenance `earnings_analyst.transition_signature`). No live anchor
value or anchor metadata was supplied by the input file.

## Canonical result

| Field | Result |
|---|---:|
| Fair value | $623.79 |
| Versus current | -24.21% |
| Verdict | overvalued |
| Score | -1.0 |
| Confidence | low |
| Families present | fundamental only |

The score is capped at `-1` because fewer than two independent valuation families are available.
The fundamental representative combines two correlation groups: the correlated earnings-analyst
DCF pair (group median `$415.09`) and owner earnings (`$832.50`). Their family median is `$623.79`.

## Eligibility audit

| Anchor | Status | Value | Reason / lineage |
|---|---|---:|---|
| earnings DCF unlevered | eligible | $446.09 | earnings cache, as of 2026-05-28 |
| earnings DCF levered | eligible | $384.09 | same correlation group as unlevered DCF |
| owner earnings ×15 | eligible | $832.50 | FMP supplementary, as of 2026-08-02 |
| self-built DCF | excluded | null | `negative_terminal_fcff` |
| analyst PT consensus | excluded | $1,468.26 | `predates_structural_shift` |
| peer P/E | excluded | null | no eligible business-similar peer bundle |
| comps | excluded | null | `fewer_than_3_exact_industry_peers` |
| forecaster blend | excluded | $183.63 | `low_forecast_confidence` (transition case retained only for shadow audit) |

Reverse DCF remains diagnostic only: current price implies approximately `1.71%` five-year FCF
CAGR at `9.18%` WACC (`fred_10y` source). It does not vote in fair value.
