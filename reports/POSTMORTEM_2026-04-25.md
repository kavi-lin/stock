# Postmortem Backtest — 2026-04-25

**Reports parsed**: 33 (NEW format only)
**With price outcome**: 27
**Window coverage**: 0/27 have ≥5d, 0/27 have ≥10d, 0/27 have ≥20d

> ⚠️ **Most reports have <5 trading days elapsed.** Treat `ret_so_far` (current return) as the primary metric. `ret_5d`/`ret_10d`/`ret_20d` cells show '—' when window not yet elapsed.

**Method**: For each report, fetch yfinance prices from decision_date forward up to 20 trading days. Compute aggressive/conservative fill, SL/TP touches, 5/10/20-day close returns from decision-day close.

**Limits**: Reports newer than ~20 trading days have partial windows. Outcomes use unadjusted close prices; intraday slippage and transaction costs not modeled.

---

## 1. Overall scoring vs realized outcomes

### Cross-tab by Final Decision

| Bucket | N | ret_so_far | ret_5d | ret_10d | min_close_pct | max_close_pct |
|---|---:|:---:|:---:|:---:|:---:|:---:|
| `BUY` | 13 | +3.25% | — | — | +0.30% | +3.86% |
| `HOLD` | 10 | +5.77% | — | — | -0.95% | +7.36% |
| `STAGED_ENTRY` | 4 | +10.62% | — | — | +9.58% | +11.38% |

---

## 2. Red Team strength validation

**Question**: Does Red Team strength 4-5 actually predict bad outcomes?

### Cross-tab by Red Team strength (0-5)

| Bucket | N | ret_so_far | ret_5d | ret_10d | min_close_pct |
|---|---:|:---:|:---:|:---:|:---:|
| `4` | 20 | +4.66% | — | — | +1.07% |
| `5` | 1 | +26.50% | — | — | +3.47% |

---

## 3. Technical RSI extreme validation

**Question**: Does RSI > 90/95 + breakout actually predict mean reversion?

### Cross-tab by Technical RSI bucket

| Bucket | N | ret_so_far | ret_5d | ret_10d | min_close_pct |
|---|---:|:---:|:---:|:---:|:---:|
| `50-70_neutral_up` | 2 | -0.32% | — | — | -0.38% |
| `70-90_strong` | 6 | +8.60% | — | — | +2.03% |
| `90-95_overbought` | 2 | +2.21% | — | — | -0.98% |
| `>=95_extreme` | 3 | +4.59% | — | — | +0.42% |

---

## 4. Phase 0 Early_Warning validation

**Question**: Does Early_Warning regime actually need a stronger macro multiplier cap?

### Cross-tab by Phase 0 warning flag

| Bucket | N | ret_5d | ret_10d | ret_20d | min_close_pct |
|---|---:|:---:|:---:|:---:|:---:|
| `Early_Warning` | 14 | — | — | — | -0.11% |
| `Other` | 13 | — | — | — | +2.63% |

---

## 5. News BUY +4 + RSI > 90 co-occurrence

**Question**: Does the 'sell-the-news' pattern empirically show up?

### Cross-tab by News+RSI pattern

| Bucket | N | ret_so_far | ret_5d | ret_10d | min_close_pct |
|---|---:|:---:|:---:|:---:|:---:|
| `News>=3 AND RSI>=90` | 3 | +4.59% | — | — | +0.42% |
| `News>=3 only` | 4 | +10.63% | — | — | +3.23% |
| `RSI>=90 only` | 2 | +2.21% | — | — | -0.98% |
| `neither` | 4 | +2.10% | — | — | -0.38% |

---

## 6. Aggressive entry fill statistics

**Question**: Did aggressive LIMIT entries actually fill, and how did they perform?


**Filled aggressive entries**: 1 / 27

### Cross-tab by Final Decision (aggr-filled only)

| Bucket | N | aggr_pnl_close_now | aggr_pnl_max_dd | aggr_pnl_max_up |
|---|---:|:---:|:---:|:---:|
| `BUY` | 1 | -0.60% | -1.12% | +4.60% |

---

## 7. SL / TP hit rates


| Metric | Count | % of with-outcome |
|---|---:|---:|
| SL hit | 0 | 0.0% |
| TP hit | 1 | 3.7% |

---

## 8. Score-to-outcome correlation (additive analysis)

**Question**: Do model scores actually predict ret_so_far? Pearson r close to 0 = noise.

| Source | Pearson r vs ret_so_far | N |
|---|---:|---:|
| final_score | +0.035 | 21 |
| raw_score | -0.076 | 6 |
| Fundamentals | -0.116 | 26 |
| Sentiment | +0.042 | 27 |
| News | +0.373 | 27 |
| Technical | -0.133 | 25 |
| Burry score | -0.110 | 24 |
| RT strength (inverted: -x) | -0.447 | 21 |

> Interpret: |r| > 0.3 = some signal; |r| < 0.15 = noise. Negative = predictor inversely correlated.


### Outlier-robust BUY vs HOLD comparison

| Decision | N | Mean | Mean (drop top1+bot1) | Median |
|---|---:|---:|---:|---:|
| BUY | 13 | +3.25% | +3.92% | +4.44% |
| HOLD | 10 | +5.77% | +4.44% | +0.53% |
| STAGED_ENTRY | 4 | +10.62% | +6.19% | +6.19% |

---

## 9. Per-report detail


| Date | Ticker | Decision | Score | RT | Tech RSI | EarlyWarn | 10d Ret | Aggr filled | Aggr P/L now |
|---|---|---|---:|---:|---:|:---:|---:|:---:|---:|
| 2026-04-18 | AMD | HOLD | +0.41 | 5/5 | — | Y | — | n | — |
| 2026-04-18 | INTC | HOLD | — | 4/5 | 90 | Y | — | n | — |
| 2026-04-18 | MSFT | HOLD | -0.09 | — | 93 | Y | — | n | — |
| 2026-04-18 | MU | BUY | +1.75 | 4/5 | — | Y | — | n | — |
| 2026-04-19 | CHRW | HOLD | +0.71 | — | — | n | — | n | — |
| 2026-04-19 | EME | BUY | — | 4/5 | — | n | — | n | — |
| 2026-04-19 | HPE | STAGED_ENTRY | +1.01 | 4/5 | — | n | — | n | — |
| 2026-04-19 | IR | HOLD | +0.43 | 4/5 | 53 | n | — | n | — |
| 2026-04-21 | AAPL | STAGED_ENTRY | +0.97 | — | — | Y | — | n | — |
| 2026-04-21 | ALAB | BUY | — | 4/5 | — | Y | — | n | — |
| 2026-04-21 | APLD | HOLD | +0.45 | — | 76 | Y | — | n | — |
| 2026-04-21 | GOOGL | BUY | +1.61 | 4/5 | 88 | Y | — | n | — |
| 2026-04-21 | MRVL | BUY | — | 4/5 | 98 | n | — | n | — |
| 2026-04-21 | MU | STAGED_ENTRY | +1.12 | 4/5 | 88 | n | — | n | — |
| 2026-04-21 | NTRS | BUY | +1.46 | 4/5 | 98 | Y | — | Y | -0.6% |
| 2026-04-21 | ORCL | HOLD | +0.10 | 4/5 | 78 | n | — | n | — |
| 2026-04-21 | STT | BUY | — | 4/5 | — | Y | — | n | — |
| 2026-04-21 | TEL | BUY | — | 4/5 | — | Y | — | n | — |
| 2026-04-22 | ALAB | BUY | +1.09 | 4/5 | 99 | Y | — | n | — |
| 2026-04-22 | GEV | BUY | +1.45 | 4/5 | 66 | n | — | n | — |
| 2026-04-22 | HPE | HOLD | +0.52 | 4/5 | — | n | — | n | — |
| 2026-04-22 | MRVL | BUY | +1.41 | 4/5 | 87 | n | — | n | — |
| 2026-04-22 | MSFT | HOLD | +0.51 | 4/5 | — | n | — | n | — |
| 2026-04-22 | NVDA | HOLD | +0.39 | — | 92 | Y | — | n | — |
| 2026-04-23 | POET | STAGED_ENTRY | +0.89 | 4/5 | — | n | — | n | — |
| 2026-04-23 | TSM | BUY | +2.20 | — | — | Y | — | n | — |
| 2026-04-23 | VRT | BUY | +1.43 | 4/5 | — | n | — | n | — |
