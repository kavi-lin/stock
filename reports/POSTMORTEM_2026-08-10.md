# Postmortem Backtest — 2026-08-10

**Reports parsed**: 144 (NEW format only)
**With price outcome**: 136
**Window coverage**: 133/136 have ≥5d, 132/136 have ≥10d, 132/136 have ≥20d

> ⚠️ **Most reports have <5 trading days elapsed.** Treat `ret_so_far` (current return) as the primary metric. `ret_5d`/`ret_10d`/`ret_20d` cells show '—' when window not yet elapsed.

**Method**: For each report, fetch yfinance prices from decision_date forward up to 20 trading days. Compute aggressive/conservative fill, SL/TP touches, 5/10/20-day close returns from decision-day close.

**Limits**: Reports newer than ~20 trading days have partial windows. Outcomes use unadjusted close prices; intraday slippage and transaction costs not modeled.

---

## 1. Overall scoring vs realized outcomes

### Cross-tab by Final Decision

| Bucket | N | ret_so_far | ret_5d | ret_10d | min_close_pct | max_close_pct |
|---|---:|:---:|:---:|:---:|:---:|:---:|
| `BUY` | 43 | +12.73% | +3.03% | +7.92% | -4.74% | +19.44% |
| `HOLD` | 56 | +9.05% | +2.64% | +5.23% | -9.36% | +21.64% |
| `SELL` | 2 | +20.40% | +13.62% | +18.22% | +2.01% | +24.43% |
| `STAGED_ENTRY` | 11 | +19.22% | -0.14% | +10.15% | -4.90% | +29.87% |

---

## 2. Red Team strength validation

**Question**: Does Red Team strength 4-5 actually predict bad outcomes?

### Cross-tab by Red Team strength (0-5)

| Bucket | N | ret_so_far | ret_5d | ret_10d | min_close_pct |
|---|---:|:---:|:---:|:---:|:---:|
| `3` | 5 | -7.61% | -3.36% | -6.42% | -15.50% |
| `4` | 64 | +11.84% | +1.48% | +7.12% | -7.73% |
| `5` | 21 | +4.25% | +3.16% | +3.05% | -10.00% |

---

## 3. Technical RSI extreme validation

**Question**: Does RSI > 90/95 + breakout actually predict mean reversion?

### Cross-tab by Technical RSI bucket

| Bucket | N | ret_so_far | ret_5d | ret_10d | min_close_pct |
|---|---:|:---:|:---:|:---:|:---:|
| `30-50_neutral_dn` | 5 | -2.54% | +1.27% | -3.43% | -12.92% |
| `50-70_neutral_up` | 40 | +8.91% | +2.91% | +6.71% | -6.26% |
| `70-90_strong` | 34 | +19.57% | +3.71% | +10.65% | -4.13% |
| `90-95_overbought` | 4 | +23.00% | +5.54% | +9.54% | -1.77% |
| `>=95_extreme` | 5 | +14.25% | +0.18% | +3.89% | -2.82% |

---

## 4. Phase 0 Early_Warning validation

**Question**: Does Early_Warning regime actually need a stronger macro multiplier cap?

### Cross-tab by Phase 0 warning flag

| Bucket | N | ret_5d | ret_10d | ret_20d | min_close_pct |
|---|---:|:---:|:---:|:---:|:---:|
| `Early_Warning` | 33 | +3.08% | +7.94% | +15.79% | -4.49% |
| `Other` | 103 | +0.96% | +4.13% | +5.74% | -9.27% |

---

## 5. News BUY +4 + RSI > 90 co-occurrence

**Question**: Does the 'sell-the-news' pattern empirically show up?

### Cross-tab by News+RSI pattern

| Bucket | N | ret_so_far | ret_5d | ret_10d | min_close_pct |
|---|---:|:---:|:---:|:---:|:---:|
| `News>=3 AND RSI>=90` | 5 | +17.23% | -1.07% | +5.00% | -3.84% |
| `News>=3 only` | 17 | +16.25% | +1.64% | +9.54% | -6.12% |
| `RSI>=90 only` | 4 | +19.28% | +7.09% | +8.14% | -0.51% |
| `neither` | 48 | +13.18% | +4.22% | +8.85% | -5.14% |

---

## 6. Aggressive entry fill statistics

**Question**: Did aggressive LIMIT entries actually fill, and how did they perform?


**Filled aggressive entries**: 5 / 136

### Cross-tab by Final Decision (aggr-filled only)

| Bucket | N | aggr_pnl_close_now | aggr_pnl_max_dd | aggr_pnl_max_up |
|---|---:|:---:|:---:|:---:|
| `BUY` | 3 | +1.88% | -3.92% | +5.48% |
| `SELL` | 1 | +17.40% | -5.87% | +22.92% |

---

## 7. SL / TP hit rates


| Metric | Count | % of with-outcome |
|---|---:|---:|
| SL hit | 7 | 5.1% |
| TP hit | 9 | 6.6% |

---

## 8. Score-to-outcome correlation (additive analysis)

**Question**: Do model scores actually predict ret_so_far? Pearson r close to 0 = noise.

| Source | Pearson r vs ret_so_far | N |
|---|---:|---:|
| final_score | +0.176 | 130 |
| raw_score | -0.385 | 11 |
| Fundamentals | +0.100 | 98 |
| Sentiment | +0.119 | 97 |
| News | +0.147 | 98 |
| Technical | +0.022 | 98 |
| Burry score | +0.002 | 86 |
| RT strength (inverted: -x) | +0.014 | 90 |

> Interpret: |r| > 0.3 = some signal; |r| < 0.15 = noise. Negative = predictor inversely correlated.


### Outlier-robust BUY vs HOLD comparison

| Decision | N | Mean | Mean (drop top1+bot1) | Median |
|---|---:|---:|---:|---:|
| BUY | 43 | +12.73% | +11.62% | +6.40% |
| HOLD | 56 | +9.05% | +8.89% | +2.46% |
| SELL | 2 | +20.40% | — | +20.40% |
| STAGED_ENTRY | 11 | +19.22% | +17.95% | +12.32% |

---

## 9. Per-report detail


| Date | Ticker | Decision | Score | RT | Tech RSI | EarlyWarn | 10d Ret | Aggr filled | Aggr P/L now |
|---|---|---|---:|---:|---:|:---:|---:|:---:|---:|
| 2026-04-18 | AMD | HOLD | +0.41 | 5/5 | 93 | Y | +24.2% | n | — |
| 2026-04-18 | INTC | HOLD | +0.09 | 4/5 | 90 | Y | +45.8% | n | — |
| 2026-04-18 | MSFT | HOLD | -0.09 | — | 93 | Y | -1.1% | n | — |
| 2026-04-18 | MU | BUY | +1.75 | 4/5 | — | Y | +28.6% | n | — |
| 2026-04-19 | CHRW | HOLD | +0.71 | — | — | n | -12.3% | n | — |
| 2026-04-19 | EME | BUY | +1.33 | 4/5 | 61 | n | +9.5% | n | — |
| 2026-04-19 | HPE | STAGED_ENTRY | +1.01 | 4/5 | 70 | n | +3.2% | n | — |
| 2026-04-19 | IR | HOLD | +0.43 | 4/5 | 53 | n | -12.1% | n | — |
| 2026-04-21 | AAPL | STAGED_ENTRY | +0.97 | — | 98 | Y | +6.8% | n | — |
| 2026-04-21 | ALAB | BUY | +1.27 | 4/5 | 95 | Y | +12.4% | n | — |
| 2026-04-21 | APLD | HOLD | +0.45 | — | 76 | Y | +27.3% | n | — |
| 2026-04-21 | GOOGL | BUY | +1.61 | 4/5 | 88 | Y | +16.9% | n | — |
| 2026-04-21 | MRVL | BUY | +1.48 | 4/5 | 98 | n | +11.5% | n | — |
| 2026-04-21 | MU | STAGED_ENTRY | +1.12 | 4/5 | 88 | n | +42.5% | n | — |
| 2026-04-21 | NTRS | BUY | +1.46 | 4/5 | 98 | Y | -5.9% | Y | -0.1% |
| 2026-04-21 | ORCL | HOLD | +0.10 | 4/5 | 78 | n | +2.3% | n | — |
| 2026-04-21 | STT | BUY | +1.31 | 4/5 | 97 | Y | -3.2% | n | — |
| 2026-04-21 | TEL | BUY | — | 4/5 | — | Y | -14.9% | n | — |
| 2026-04-22 | ALAB | BUY | +1.09 | 4/5 | 99 | Y | +10.2% | n | — |
| 2026-04-22 | GEV | BUY | +1.45 | 4/5 | 66 | n | -0.8% | n | — |
| 2026-04-22 | HPE | HOLD | +0.52 | 4/5 | — | n | +6.5% | n | — |
| 2026-04-22 | MRVL | BUY | +1.41 | 4/5 | 87 | n | +9.4% | n | — |
| 2026-04-22 | MSFT | HOLD | +0.51 | 4/5 | — | n | -4.4% | n | — |
| 2026-04-22 | NVDA | HOLD | +0.39 | — | 92 | Y | +2.6% | n | — |
| 2026-04-23 | POET | STAGED_ENTRY | +0.89 | 4/5 | — | n | -18.3% | n | — |
| 2026-04-23 | TSM | BUY | +2.20 | — | — | Y | +8.2% | n | — |
| 2026-04-23 | VRT | BUY | +1.43 | 4/5 | 87 | n | +5.7% | n | — |
| 2026-04-24 | FCX | HOLD | -0.08 | 4/5 | — | Y | +1.0% | n | — |
| 2026-04-24 | MRVL | HOLD | +0.77 | 4/5 | 87 | n | +3.5% | n | — |
| 2026-04-24 | MU | STAGED_ENTRY | +1.19 | 4/5 | 68 | n | +50.3% | n | — |
| 2026-04-24 | NEE | BUY | +1.21 | — | 65 | n | -2.3% | n | — |
| 2026-04-24 | ON | HOLD | +0.53 | 4/5 | 89 | Y | +4.9% | n | — |
| 2026-04-25 | SNA | HOLD | +0.65 | 4/5 | 54 | n | -3.6% | n | — |
| 2026-04-26 | AIZ | BUY | — | — | 63 | n | +4.9% | n | — |
| 2026-04-26 | AVGO | STAGED_ENTRY | +0.84 | 4/5 | 78 | n | +2.4% | n | — |
| 2026-04-26 | CSCO | STAGED_ENTRY | +0.84 | 4/5 | 70 | n | +11.9% | n | — |
| 2026-04-26 | CSX | HOLD | +0.19 | 4/5 | 70 | n | -1.6% | n | — |
| 2026-04-26 | DLR | STAGED_ENTRY | +1.13 | 4/5 | 72 | n | -0.1% | n | — |
| 2026-04-26 | GSAT | BUY | +1.40 | — | 69 | n | +0.4% | Y | +2.3% |
| 2026-04-26 | QCOM | HOLD | +0.73 | 4/5 | 73 | n | +58.1% | n | — |
| 2026-04-26 | TSM | BUY | +2.13 | 4/5 | 68 | n | -0.1% | n | — |
| 2026-04-26 | VRT | BUY | +1.99 | 4/5 | 68 | n | +14.1% | n | — |
| 2026-04-27 | AAOI | HOLD | +0.56 | 4/5 | 64 | n | +26.8% | n | — |
| 2026-04-27 | ALAB | HOLD | +0.72 | — | 84 | n | +5.4% | n | — |
| 2026-04-27 | ARM | HOLD | +0.24 | 5/5 | 87 | n | -1.5% | n | — |
| 2026-04-27 | CRM | HOLD | +0.65 | — | 49 | n | -1.5% | n | — |
| 2026-04-27 | FTV | HOLD | +0.36 | — | 66 | n | -2.7% | n | — |
| 2026-04-27 | GLW | HOLD | +0.90 | 4/5 | 68 | n | +23.4% | n | — |
| 2026-04-27 | LITE | HOLD | +1.10 | 5/5 | 58 | n | +22.5% | n | — |
| 2026-04-27 | MU | BUY | +1.20 | 4/5 | 87 | n | +51.6% | n | — |
| 2026-04-27 | NOW | HOLD | -0.32 | 3/5 | — | n | +1.1% | n | — |
| 2026-04-27 | NVDA | BUY | +1.37 | 4/5 | 72 | n | +1.3% | n | — |
| 2026-04-27 | PKG | HOLD | +0.07 | 4/5 | — | n | +4.2% | n | — |
| 2026-04-27 | SLB | BUY | +1.22 | — | 70 | n | -0.5% | n | — |
| 2026-04-27 | TSM | BUY | +1.64 | — | 68 | n | -0.1% | n | — |
| 2026-04-28 | BE | SELL | — | 5/5 | 72 | n | +24.0% | n | — |
| 2026-04-28 | HUBB | HOLD | +0.55 | 4/5 | 65 | Y | -10.8% | n | — |
| 2026-04-29 | NVDA | HOLD | +0.92 | — | 71 | n | +7.9% | n | — |
| 2026-04-29 | TSM | BUY | +1.23 | 4/5 | 60 | n | +1.5% | n | — |
| 2026-05-01 | AAPL | STAGED_ENTRY | +1.01 | 5/5 | 70 | n | +7.2% | n | — |
| 2026-05-01 | GOOG | BUY | +1.32 | 4/5 | 81 | n | +2.6% | n | — |
| 2026-05-01 | LLY | BUY | +1.51 | — | 81 | n | +4.3% | n | — |
| 2026-05-01 | MRVL | HOLD | +0.54 | 4/5 | 77 | n | +7.2% | n | — |
| 2026-05-01 | MU | BUY | +1.22 | 4/5 | 68 | n | +33.6% | n | — |
| 2026-05-02 | EME | HOLD | +0.66 | 5/5 | — | n | -3.6% | n | — |
| 2026-05-02 | GOOGL | STAGED_ENTRY | +0.95 | 4/5 | 82 | n | +3.6% | n | — |
| 2026-05-02 | NVDA | BUY | +1.30 | — | 53 | n | +12.0% | n | — |
| 2026-05-02 | TEAM | BUY | — | 4/5 | — | Y | -4.0% | n | — |
| 2026-05-02 | VRT | HOLD | +0.62 | 5/5 | 65 | Y | +2.6% | n | — |
| 2026-05-03 | CRWV | HOLD | -0.06 | — | 62 | n | -17.3% | n | — |
| 2026-05-03 | LLY | STAGED_ENTRY | +1.10 | 4/5 | 58 | Y | +2.1% | n | — |
| 2026-05-03 | QCOM | HOLD | +0.72 | 4/5 | 83 | n | +20.9% | n | — |
| 2026-05-03 | TSM | BUY | — | 4/5 | 63 | Y | -1.4% | n | — |
| 2026-05-05 | TSM | BUY | +1.49 | 4/5 | 61 | Y | -0.5% | n | — |
| 2026-05-07 | ALAB | HOLD | -0.38 | — | — | Y | +52.2% | n | — |
| 2026-05-07 | AMD | HOLD | +0.46 | 5/5 | — | Y | +10.1% | n | — |
| 2026-05-07 | CRWV | HOLD | +0.05 | — | 72 | n | -16.5% | n | — |
| 2026-05-07 | TSM | BUY | +1.58 | 5/5 | 69 | Y | -1.7% | n | — |
| 2026-05-08 | CRWV | HOLD | -0.28 | 5/5 | 63 | n | -7.6% | n | — |
| 2026-05-08 | MU | BUY | +0.69 | — | 82 | n | +0.6% | n | — |
| 2026-05-08 | NEE | HOLD | +0.13 | 4/5 | — | n | -4.9% | n | — |
| 2026-05-10 | HPE | HOLD | +0.59 | — | 74 | Y | +23.3% | n | — |
| 2026-05-10 | MU | HOLD | +1.19 | — | 84 | Y | +12.6% | n | — |
| 2026-05-10 | TSM | BUY | +1.41 | — | — | n | +1.9% | Y | +3.4% |
| 2026-05-11 | NVDA | — | +1.84 | 5/5 | 68 | Y | -2.1% | n | — |
| 2026-05-16 | MU | BUY | +0.69 | — | — | n | +56.1% | n | — |
| 2026-05-18 | MU | BUY | +0.87 | 4/5 | — | n | +56.1% | n | — |
| 2026-05-20 | D | HOLD | +0.48 | 3/5 | 71 | Y | -1.8% | n | — |
| 2026-05-20 | GOOGL | BUY | +0.81 | 5/5 | — | Y | -4.3% | n | — |
| 2026-05-20 | MRVL | HOLD | +0.36 | 5/5 | 69 | n | +69.4% | n | — |
| 2026-05-20 | MU | BUY | +0.99 | 4/5 | 64 | n | +36.1% | n | — |
| 2026-05-20 | TSM | BUY | +1.41 | 4/5 | 52 | n | +10.8% | n | — |
| 2026-05-23 | NOK | HOLD | +0.33 | 5/5 | 72 | Y | -15.9% | n | — |
| 2026-05-26 | CRWD | HOLD | +0.18 | — | 87 | n | -4.0% | n | — |
| 2026-05-29 | MRVL | HOLD | +0.43 | — | 68 | Y | +36.4% | n | — |
| 2026-05-29 | MU | HOLD | +0.92 | 4/5 | 77 | Y | +1.1% | n | — |
| 2026-05-31 | MSFT | BUY | +0.60 | 4/5 | — | n | -13.2% | n | — |
| 2026-05-31 | TSM | BUY | +1.56 | 3/5 | 60 | n | +1.3% | n | — |
| 2026-06-08 | MRVL | HOLD | +0.03 | — | — | n | -3.4% | n | — |
| 2026-06-13 | GOOGL | — | +0.38 | — | 42 | n | -3.2% | n | — |
| 2026-06-13 | MU | BUY | +0.64 | 4/5 | 61 | n | +6.1% | n | — |
| 2026-06-13 | NOK | — | +0.24 | 4/5 | — | n | -10.4% | n | — |
| 2026-06-13 | SPCX | — | — | 4/5 | — | n | -11.2% | n | — |
| 2026-06-14 | AAPL | HOLD | -0.64 | 4/5 | — | n | -2.4% | n | — |
| 2026-06-14 | ALAB | — | +0.10 | — | — | n | +24.1% | n | — |
| 2026-06-14 | AMD | — | +0.75 | 5/5 | — | n | +6.1% | n | — |
| 2026-06-14 | MRVL | — | +0.51 | 4/5 | — | n | -3.6% | Y | -15.5% |
| 2026-06-14 | PLTR | — | -0.28 | — | — | n | -13.4% | n | — |
| 2026-06-14 | RGTI | HOLD | -0.33 | 3/5 | — | n | -14.9% | n | — |
| 2026-06-14 | TSM | BUY | +1.06 | — | 54 | n | +8.2% | n | — |
| 2026-06-15 | ARM | — | -0.06 | — | — | n | -14.1% | n | — |
| 2026-06-18 | TSM | — | +1.06 | — | — | n | -2.2% | n | — |
| 2026-06-21 | MU | BUY | +0.81 | 5/5 | — | n | -22.5% | n | — |
| 2026-06-21 | NBIS | HOLD | -0.01 | — | 70 | n | -31.2% | n | — |
| 2026-06-21 | NVDA | — | +1.04 | 4/5 | 50 | n | -5.6% | n | — |
| 2026-06-21 | PLTR | SELL | -0.48 | — | — | n | +12.4% | Y | +17.4% |
| 2026-06-22 | AAPL | HOLD | -0.15 | 5/5 | — | n | +4.6% | n | — |
| 2026-06-22 | CCJ | — | -0.40 | 4/5 | — | n | -11.6% | n | — |
| 2026-06-22 | CEG | — | +0.59 | 4/5 | — | n | -13.0% | n | — |
| 2026-06-22 | CRDO | — | +0.55 | — | 66 | n | -18.6% | n | — |
| 2026-06-22 | IONQ | HOLD | +0.18 | 5/5 | 49 | n | -22.2% | n | — |
| 2026-06-22 | MRVL | — | +0.64 | 4/5 | — | n | -25.1% | n | — |
| 2026-06-22 | NOK | HOLD | -0.59 | 3/5 | — | n | -17.9% | n | — |
| 2026-06-22 | TXN | HOLD | +0.05 | 5/5 | — | n | -11.7% | n | — |
| 2026-06-24 | JBL | — | +0.54 | 5/5 | — | n | -10.6% | n | — |
| 2026-06-24 | SNDK | HOLD | +0.07 | 5/5 | — | n | -2.9% | n | — |
| 2026-06-24 | SPCX | HOLD | +0.15 | 4/5 | — | n | -1.5% | n | — |
| 2026-06-27 | MSFT | — | +0.13 | — | — | n | +4.4% | n | — |
| 2026-06-27 | PLTR | HOLD | -0.57 | — | 35 | n | +15.6% | n | — |
| 2026-07-08 | MU | — | +0.38 | — | — | n | +1.1% | n | — |
| 2026-07-08 | NVDA | — | +0.40 | — | — | n | +3.9% | n | — |
| 2026-07-08 | PLTR | — | +0.01 | — | 50 | n | -5.8% | n | — |
| 2026-07-31 | MU | — | +0.78 | — | — | n | — | n | — |
| 2026-08-02 | MSFT | — | +0.73 | — | 74 | n | — | n | — |
| 2026-08-02 | MU | — | -0.30 | — | — | n | — | n | — |
| 2026-08-02 | PLTR | — | -0.26 | — | — | n | — | n | — |
