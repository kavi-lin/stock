# Rec 11 shadow-replay — Semiconductor HOLD-miss
_index generated_at: 2026-06-13T22:47:01.579517_  ·  _replay: read-only, no protocol state touched_

- candidate default-HOLD miss records: **19**
- **strict gate** (RISK_ON/BULL only — the live rule): would fire **12**
- **ex-regime** (gate widened to all regimes — the deferred what-if): would fire **18**

| pass | n_fired | avg_missed_return% | avg_dd% | synthetic NAV capture% (@15bps) |
|---|---|---|---|---|
| strict (live gate) | 12 | 34.2 | -3.14 | 0.6156 |
| ex-regime (what-if) | 18 | 35.85 | -3.46 | 0.9681 |

⚠️ `decision_cap_active` / `mandatory_risk_flags` are not in event_index → assumed-pass; fired counts are upper bounds on those two terms only.

### fired records (strict)
| id | regime | score | missed_ret% | dd% | decisive |
|---|---|---|---|---|---|
| deep-dive_AMD_2026-04-18 | RISK_ON | 0.413 | 53.115 | 0.0 | News |
| deep-dive_INTC_2026-04-18 | RISK_ON | 0.092 | 64.642 | -0.654 | News |
| deep-dive_NVDA_2026-04-22 | RISK_ON | 0.386 | 6.336 | -2.963 | Fundamentals |
| deep-dive_ARM_2026-04-27 | BULL | 0.239 | 40.221 | -7.981 | Fundamentals |
| deep-dive_MRVL_2026-05-01 | RISK_ON | 0.544 | 24.28 | -2.995 | News |
| deep-dive_AMD_2026-05-07 | RISK_ON | 0.462 | 14.18 | 0.0 | Valuation |
| deep-dive_MU_2026-05-08 | BULL | 0.692 | 15.693 | -8.74 | Fundamentals |
| deep-dive_MU_2026-05-10 | RISK_ON | 1.194 | 17.673 | -14.307 | Fundamentals |
| deep-dive_MU_2026-05-16 | BULL | 0.692 | 44.028 | 0.0 | Fundamentals |
| deep-dive_MU_2026-05-18 | RISK_ON | 0.869 | 44.028 | 0.0 | Fundamentals |
| deep-dive_MRVL_2026-05-20 | BULL | 0.36 | 49.732 | 0.0 | News |
| deep-dive_MRVL_2026-05-29 | RISK_ON | 0.431 | 36.439 | 0.0 | Unknown |
