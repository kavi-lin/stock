# Short-Term Recommendation Weekly Review — 2026-06-11

**Window**: past 7 days  |  **Total predictions evaluated**: 476  |  **Unique tickers**: 138

**Method**: For each prediction in `data/recommendations/<date>.json`, fetch actual yfinance close at `prediction_date + horizon_days`, compute hit/miss + range coverage + bias.

---

## 1. Per-horizon hit rate & bias

| Horizon | N | Hit Rate (direction) | In-Range | Mean Pred | Mean Actual | Bias (pred-actual) |
|---|---:|---:|---:|---:|---:|---:|
| 1d | 396 | 44.4% | 61.1% | +0.29% | +nan% | +nan% |
| 5d | 80 | 0.0% | 0.0% | +0.30% | +nan% | +nan% |
| 15d | — | — | — | — | — | — |

**Read this**:
- `Hit Rate` < 50% = worse than random walk; > 70% = strong signal
- `In-Range` = % of cases where actual price fell within [target_low, target_high]
- `Bias` > 0 = model OVER-predicts (more bullish than reality); < 0 = UNDER-predicts

_All evaluated predictions used weights_version `v0.1.0` — no before/after comparison this window._

---

## 2. Per-theme 5d alpha breakdown

| Theme | N | Hit Rate | Mean Pred | Mean Actual | Model Bias |
|---|---:|---:|---:|---:|---:|
| Oil & Gas (Energy) | 5 | 0.0% | +1.39% | +nan% | +nan% |
| Financial Services & Banks | 5 | 0.0% | -0.68% | +nan% | +nan% |
| AI & Semiconductors | 5 | 0.0% | +1.83% | +nan% | +nan% |
| Clean Energy & EV | 5 | 0.0% | -1.04% | +nan% | +nan% |
| Quantum Computing | 5 | 0.0% | +1.75% | +nan% | +nan% |
| Healthcare & Pharma | 5 | 0.0% | +1.64% | +nan% | +nan% |
| Obesity & GLP-1 | 5 | 0.0% | -1.08% | +nan% | +nan% |
| Robotics & Automation | 5 | 0.0% | +1.66% | +nan% | +nan% |
| Space Economy | 5 | 0.0% | +1.70% | +nan% | +nan% |
| Nuclear Energy | 5 | 0.0% | -1.01% | +nan% | +nan% |
| Defense & Aerospace | 5 | 0.0% | +1.74% | +nan% | +nan% |
| Infrastructure & Construction | 5 | 0.0% | -1.21% | +nan% | +nan% |
| Retail & Consumer | 5 | 0.0% | -1.49% | +nan% | +nan% |
| Consumer Defensive Sector Concentration | 5 | 0.0% | -1.26% | +nan% | +nan% |
| Industrials Sector Concentration | 4 | 0.0% | +0.92% | +nan% | +nan% |
| Real Estate & REITs | 4 | 0.0% | +0.26% | +nan% | +nan% |
| Basic Materials Sector Concentration | 1 | 0.0% | -0.16% | +nan% | +nan% |
| Uranium | 1 | 0.0% | -0.16% | +nan% | +nan% |

---

## 3. Worst 5 predictions (by absolute error)

| Date | Ticker | Theme | Horizon | Pred | Actual | Error | Confidence |
|---|---|---|---|---:|---:|---:|---:|
| 2026-06-09 | WM | Utilities Defensive | 1d | -0.91% | +nan% | +nan% | 0.82 |
| 2026-06-09 | SO | Utilities Defensive | 1d | -0.79% | +nan% | +nan% | 0.82 |
| 2026-06-09 | NEE | Utilities Defensive | 1d | -1.03% | +nan% | +nan% | 0.77 |
| 2026-06-09 | SRE | Utilities Defensive | 1d | -0.53% | +nan% | +nan% | 0.8 |
| 2026-06-09 | ETR | Utilities Defensive | 1d | -0.52% | +nan% | +nan% | 0.79 |

---

## 4. Suggested adjustments

**These are SUGGESTIONS only**. The tool does NOT auto-apply changes. 
Edit `skills/short-term-target/config/weights.yaml` manually if you accept any.

- 🔴 1d: hit_rate 44.4% < 50% (random walk). Consider reducing all weights for this horizon by 20-30% to dampen overconfidence
- 🔴 5d: hit_rate 0.0% < 50% (random walk). Consider reducing all weights for this horizon by 20-30% to dampen overconfidence
- 🔴 Theme 'Oil & Gas (Energy)' (5d): hit_rate 0.0% on 5 samples. Consider removing from screener watchlist OR investigate driver mis-calibration
- 🔴 Theme 'Financial Services & Banks' (5d): hit_rate 0.0% on 5 samples. Consider removing from screener watchlist OR investigate driver mis-calibration
- 🔴 Theme 'AI & Semiconductors' (5d): hit_rate 0.0% on 5 samples. Consider removing from screener watchlist OR investigate driver mis-calibration
- 🔴 Theme 'Clean Energy & EV' (5d): hit_rate 0.0% on 5 samples. Consider removing from screener watchlist OR investigate driver mis-calibration
- 🔴 Theme 'Quantum Computing' (5d): hit_rate 0.0% on 5 samples. Consider removing from screener watchlist OR investigate driver mis-calibration
- 🔴 Theme 'Healthcare & Pharma' (5d): hit_rate 0.0% on 5 samples. Consider removing from screener watchlist OR investigate driver mis-calibration
- 🔴 Theme 'Obesity & GLP-1' (5d): hit_rate 0.0% on 5 samples. Consider removing from screener watchlist OR investigate driver mis-calibration
- 🔴 Theme 'Robotics & Automation' (5d): hit_rate 0.0% on 5 samples. Consider removing from screener watchlist OR investigate driver mis-calibration
- 🔴 Theme 'Space Economy' (5d): hit_rate 0.0% on 5 samples. Consider removing from screener watchlist OR investigate driver mis-calibration
- 🔴 Theme 'Nuclear Energy' (5d): hit_rate 0.0% on 5 samples. Consider removing from screener watchlist OR investigate driver mis-calibration
- 🔴 Theme 'Defense & Aerospace' (5d): hit_rate 0.0% on 5 samples. Consider removing from screener watchlist OR investigate driver mis-calibration
- 🔴 Theme 'Infrastructure & Construction' (5d): hit_rate 0.0% on 5 samples. Consider removing from screener watchlist OR investigate driver mis-calibration
- 🔴 Theme 'Retail & Consumer' (5d): hit_rate 0.0% on 5 samples. Consider removing from screener watchlist OR investigate driver mis-calibration
- 🔴 Theme 'Consumer Defensive Sector Concentration' (5d): hit_rate 0.0% on 5 samples. Consider removing from screener watchlist OR investigate driver mis-calibration

**To apply changes**:
1. Edit `skills/short-term-target/config/weights.yaml`
2. Bump `weights_version` field (e.g., `v0.1.0` → `v0.1.1`)
3. Future predictions tagged with new version → enables before/after comparison

---

## 5. KPI gate (per plan_short.md §6 + §12.H)

**5d hit rate**: 0.0% (must be ≥ 50%)  →  🔴 FAIL
**5d realized**: +nan% (must be ≥ 0%)  →  🔴

⚠️ **KPI failed at N ≥ 30**. Per plan_short.md §6: consider retiring the system.

---

*Generated by `weekly_review.py`. Tool location: `skills/short-term-target/scripts/`*