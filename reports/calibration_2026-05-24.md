# Composite Calibration Cohort — 2026-05-24

> Runner: `skills/_shared/composite_calibration_cohort/runner.py` · Cohort: v1.0

---

## Acceptance Summary

| Metric | Value | Threshold | Pass |
|---|---|---|---|
| Available samples | 0 / 18 | ≥ 6 | ⚠ |
| Directional / Flag rate | INSUFFICIENT_DATA | — | ⚠ |

**Overall**: `INSUFFICIENT_DATA` (missing=18, errors=0)

---

## Per-Ticker Results

| Ticker | Bucket | Target | Cache | Δd | Composite | Verdict | transition_sig | mix | cc_quality | Score | Expected |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NVDA | hyper_growth_transition | 2023-10-29 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_up |
| META | hyper_growth_transition | 2022-12-31 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_up |
| SHOP | hyper_growth_transition | 2020-09-30 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_up |
| MSFT | mature_mega_cap_stable | 2024-09-30 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_up |
| JNJ | mature_mega_cap_stable | 2023-06-30 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_flat |
| KO | mature_mega_cap_stable | 2024-03-31 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_flat |
| INTC | value_trap | 2023-09-30 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_down |
| VFC | value_trap | 2022-12-31 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_down |
| WBA | value_trap | 2023-08-31 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_down |
| PTON | hype_bust | 2022-06-30 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_down |
| RIVN | hype_bust | 2023-03-31 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_down |
| SPCE | hype_bust | 2022-09-30 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_down |
| SBUX | margin_recovery | 2022-09-30 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_up |
| DIS | margin_recovery | 2023-09-30 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_up |
| CRM | margin_recovery | 2022-10-31 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_up |
| AMD | cyclical_trough | 2019-09-30 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_up |
| MU | cyclical_trough | 2022-12-31 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_up |
| FCX | cyclical_trough | 2020-06-30 | — | — | — | `MISSING_CACHE` | — | — | — | — | directional_up |

---

## Notes

- Directional mapping: composite ≥ 65 → directional_up, 35-64 → directional_flat, < 35 → directional_down.
- Acceptance soft-fails (rc=0 + warning) when AVAILABLE < 6 — treat the cohort as a measurement layer, not an enforcement gate.
- Missing caches reported but excluded from scoring denominator. Populate caches manually via `python3 skills/earnings-analyst/scripts/fetch.py <T>` with the appropriate historical period.
- Stale-gate trigger rate is measured separately via `skills/earnings-analyst/tests/test_stale_gate_simulated.py` (fixture-based) rather than on historical cache mtime — local filesystem mtime ≠ financial event time.