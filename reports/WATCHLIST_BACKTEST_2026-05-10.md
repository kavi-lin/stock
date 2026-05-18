# Structural Watchlist Backtest — 2026-05-10

> V2.19.1 directional sanity check.
> Sample = 7 unique tickers from `watchlist_lifecycle.jsonl`.
> **n < 50 = directional only — do NOT use as production decision rule.**

## Tier graduation (Ground Truth A)

`first_seen` (watchlist enter) → `graduated_candidate / graduated_confirmed`
(earnings-analyst structural_shift tier upgrade).

| Outcome | Count | % |
|---|---|---|
| Graduated CONFIRMED | 1 | 14.3% |
| Graduated CANDIDATE | 1 | 14.3% |
| Still active (no graduation yet) | 5 | 71.4% |
| Evicted without graduation | 0 | 0.0% |
| **Total tickers** | **7** | 100% |

### Graduated → CONFIRMED
- **MU** (`Memory Semiconductors`) — lead time 17d

### Graduated → CANDIDATE
- **NVDA** (`Memory Semiconductors`) — lead time 17d

### Still active
- **TSM** (`Memory Semiconductors`) — lead time 0d
- **ASML** (`Memory Semiconductors`) — lead time 0d
- **DELL** (`Memory Semiconductors`) — lead time 0d
- **WDC** (`Memory Semiconductors`) — lead time 0d
- **STX** (`Memory Semiconductors`) — lead time 0d

### Evicted without graduation (false positive candidates)
_(無)_

## Lead time stats (CONFIRMED only)

- Sample n = 1
- Mean lead = 17.0d
- Median lead = 17d
- Min / Max = 17d / 17d

## Forward returns (Ground Truth B)

| Ticker | Sector ETF | Base | r_5d | r_15d | r_45d | r_90d | α_SPY_15d | α_sector_15d | Status |
|---|---|---|---|---|---|---|---|---|---|
| **ASML** | SOXX | $1417.8 | -2.3% | +12.3% | — | — | +8.2% | -5.7% | `partial` |
| **DELL** | SOXX | $212.14 | -2.9% | +22.8% | — | — | +18.7% | +4.8% | `partial` |
| **MU** | SOXX | $481.72 | +4.7% | +55.0% | — | — | +50.9% | +37.0% | `partial` |
| **NVDA** | SOXX | $199.64 | +6.8% | +7.8% | — | — | +3.7% | -10.2% | `partial` |
| **STX** | SOXX | $587.62 | -1.5% | +33.2% | — | — | +29.1% | +15.2% | `partial` |
| **TSM** | SOXX | $382.66 | +2.5% | +7.6% | — | — | +3.5% | -10.4% | `partial` |
| **WDC** | SOXX | $403.12 | -3.0% | +19.1% | — | — | +14.9% | +1.1% | `partial` |

### 15d alpha aggregates
- SPY-relative: n=7 | mean=+18.4% | hit_rate (α>0)=7/7 = 100%
- Sector-relative: n=7 | mean=+4.6% | hit_rate (α>0)=4/7 = 57%

## Random sector baseline (B1) — null hypothesis test

If watchlist mean alpha ≈ random sector baseline → **no edge, only sector momentum**.

| Sector ETF | Watchlist mean α (15d) | Random baseline mean α (15d) | n_random | Hit rate Δ |
|---|---|---|---|---|
| SOXX | +18.4% | +14.0% | 35 | +4.4pp |

## Per-keyword breakdown (B2) — which keywords carry signal

| Keyword | n | Tickers | Mean α (SPY 15d) | Hit rate | Mean α (sector 15d) |
|---|---|---|---|---|---|
| `super-cycle` | 5 | DELL, MU, STX, TSM, WDC | +23.4% | 100% | +9.6% |
| `供不應求` | 7 | ASML, DELL, MU, NVDA, STX, TSM, WDC | +18.4% | 100% | +4.5% |
| `supply tight` | 3 | ASML, NVDA, TSM | +5.1% | 100% | -8.8% |

## Per-credibility (B3) — HIGH vs MEDIUM source

If HIGH ≈ MEDIUM, credibility is false signal.

| Credibility | n | Mean α SPY 15d | Hit rate |
|---|---|---|---|
| HIGH | 1 | +3.5% | 100% |
| MEDIUM | 6 | +20.9% | 100% |

## Horizon sweep (B4) — optimal hold window

| Horizon | n | Mean α SPY | Hit rate SPY | Mean α sector | Hit rate sec |
|---|---|---|---|---|---|
| 5d | 7 | +0.1% | 43% | +1.1% | 43% |
| 15d | 7 | +18.4% | 100% | +4.5% | 57% |

## Caveats

- Lifecycle log only began 2026-05-10 (V2.19.1 deploy date)
- Earnings tier graduation requires next earnings cycle (~30-90d) — small n until Q2/Q3 reports
- Watchlist eviction at 21d may flag false positives that would have graduated later
- IR boilerplate ("supply tight" / "demand strong") inflates baseline noise floor
