# Pre-Market Sector Intelligence Report — 2026-04-19 (Sun)

> Protocol V1.3 · Fan-out: PARALLEL_SUBAGENT · Degraded agents: none (Theme data on inline fallback due to FMP API downtime)

## Final Verdict Table

| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|
| Industrials | **HOT** | 77.9 | Strongest slope +0.037 (42.1% OB); Iran-ceasefire airline tailwind | ROBUST | XLI | overbought, consensus_warning |
| Financials | **HOT** | 75.7 | JPM Q1 +19% record; Fed-cut repricing + INFLOW slope +0.031 | ROBUST | XLF | consensus_warning |
| Utilities | WARM | 68.7 | Highest breadth 43.9% OB; Fed-cut + defensive tilt Accelerating | ROBUST | XLU | overbought, fragility_downgrade |
| Consumer Discretionary | WARM | 67.2 | Oil -10% airline tailwind; core goods CPI +0.2% cooling | N/A | XLY | binary_earnings_within_week |
| Technology | WARM | 66.1 | AI capex cycle + Fed-cut; narrow-rally exhaustion risk (RSI 96.8) | N/A | XLK | overbought_rsi, binary_earnings_4_28 |
| Materials | WARM | 63.6 | Second-highest breadth 43.4% OB; INFLOW slope +0.028 | N/A | XLB | overbought, late_cycle |
| Healthcare | COLD | 46.1 | Neutral across 3 lanes; 29.7% breadth lagging | N/A | XLV | — |
| Real Estate | COLD | 46.0 | Weakest breadth 22.1%; rate-cut bid offset by RISK_ON rotation | N/A | XLRE | — |
| Communication | COLD | 43.1 | Netflix -9.3% guide shock; GOOGL 4/22 + META 4/28 binary | N/A | XLC | binary_earnings_cluster |
| Consumer Staples | COLD | 39.3 | 23.5% breadth weak; flat slope in RISK_ON regime | N/A | XLP | — |
| Energy | **COLD** | 30.6 | 3/3 lane consensus COLD; WTI -10% on Hormuz reopening | N/A | XLE | outflow_consensus, oil_crash |

**Market Regime:** RISK_ON | **Breadth Ceiling:** 60-75% | **Synthesized Ceiling:** 60-75% | **Cycle:** Mid
**Sentiment:** Fear & Greed [68.1 — Greed] composite 74.7 | **VIX:** 17.48 | **SPY RSI:** 96.8 ⚠️ | **Put/Call:** n/a | **Signal Conflict:** No
**Final Regime Stance:** NEUTRAL (regime_confidence 0.65) · **FTD:** CONFIRMED 2026-03-31 (quality 100) · **Market Top:** 31.7 Yellow Early Warning

**TOP THEMES TODAY:** Iran_ceasefire_oil_de-escalation (Trending 90) · Fed_cut_repricing (Accelerating 75) · AI_capex_mega_print (Mature 80) · Narrow_rally_exhaustion (Exhausting 70) · Defensive_late_cycle_tilt (Accelerating 65)

**HANDOFF TO INVESTMENT PROTOCOL:**
> FTD 確認但 breadth 40 / 23rd pct + SPY RSI 96.8 + Nasdaq 13-day streak = crowded late-cycle tactical peak。HOT 僅 Industrials / Financials (皆 DA-challenged)，曝險上限 60-75%；4/22–4/29 密集 mega-cap earnings + FOMC 為 10 日內 binary 窗口。避開 Energy / Communication。

---

## Phase 0 — Macro Regime

### 三訊號合成（Synthesized Exposure）

| 來源 | 原始值 | 中位數 |
|---|---|---|
| Breadth (40.3 Neutral, improving +3.5) | 60-75% | 67.5 ⬅ 最小 |
| FTD (CONFIRMED 2026-03-31, quality 100) | 75-100% | 87.5 |
| Market Top (31.7 Yellow) | 80-90% | 85.0 |

- **min=67.5, max=87.5, diff=20pp < 30pp** → `signal_conflict: false`
- `synthesized_exposure: "60-75%"` (Breadth 最保守值)
- FTD 訊號強但 breadth 仍在 Neutral → 未觸發 50% 積極訊號打折，但 PS 以 breadth 為上限不採 FTD 進取範圍

### 關鍵警示
- `Bearish_Signal_Active` (breadth pink zone)
- `Below_200MA` (gap -5.1%)
- `Low_Historical_Percentile` (23rd pct)
- SPY RSI **96.8** — extreme stretch；Nasdaq 12-13 連續上漲（1992/2009 以來最長）
- Commodity avg 38.6% > Cyclical 32.1% by 6.5pp — 典型 late-cycle commodity-over-cyclical divergence

---

## Phase 1 — Sector Rotation (TraderMonty 2026-04-19)

| Rank | Sector | Uptrend Ratio | Slope | Trend | Status | Rotation | Overbought |
|---|---|---|---|---|---|---|---|
| 1 | Utilities | 43.9% | +0.034 | Up | **Overbought** | INFLOW | HIGH |
| 2 | Materials | 43.4% | +0.028 | Up | **Overbought** | INFLOW | HIGH |
| 3 | Industrials | 42.1% | +0.037 | Up | **Overbought** | INFLOW | HIGH |
| 4 | Technology | 34.5% | +0.024 | Up | Normal | INFLOW | MEDIUM |
| 5 | Financials | 33.8% | +0.031 | Up | Normal | INFLOW | MEDIUM |
| 6 | Energy | 33.7% | **-0.031** | **Down** | Normal | **OUTFLOW** | MEDIUM |
| 7 | Healthcare | 29.7% | +0.019 | Up | Normal | NEUTRAL | LOW |
| 8 | Consumer Disc. | 26.5% | +0.023 | Up | Normal | NEUTRAL | LOW |
| 9 | Communication | 23.6% | +0.013 | Up | Normal | NEUTRAL | LOW |
| 10 | Consumer Staples | 23.5% | +0.010 | Up | Normal | NEUTRAL | LOW |
| 11 | Real Estate | 22.1% | +0.019 | Up | Normal | NEUTRAL | LOW |

**Overall uptrend_ratio: 32.4%** (narrow). Group avgs — Commodity 38.6% > Cyclical 32.1% > Defensive 29.8%. `divergence_flag: true`, `late_cycle_flag: true`.

---

## Phase 3 — News & Sentiment

### Top Catalysts (Past 7 Days)
1. **2026-04-13** Iran war oil shock peaks — IEA largest disruption in history (10.1 mb/d lost March) — binary
2. **2026-04-15** Trump US-Iran ceasefire proposal (SPX +2.5%, Nasdaq +2.8%) — bullish broad
3. **2026-04-16** Nasdaq 12-13 up days (longest since 1992/2009); Fed funds futures price ≥1 cut YE — bullish Tech/rate-sens
4. **2026-04-17** Hormuz "fully open"; WTI -10% to <$84 (5-week low) — bearish Energy, bullish Transports/ConsDisc
5. **2026-04-17** March CPI headline +0.9%/+3.3% hot (energy) but **core goods +0.2% slowest in 4 months** — mixed bullish equities
6. **2026-04-17** Netflix -9.3% on soft Q2 guide — bearish Communication
7. **2026-04-14** JPM Q1 markets revenue +19% record — bullish Financials

### Upcoming Binary Events
| Date | Event | Within 48h | Affected |
|---|---|---|---|
| rolling | Iran ceasefire collapse headline | ✅ | Energy, Industrials, Consumer Disc |
| 2026-04-22 AMC | TSLA + GOOGL Q1 earnings | — | Consumer Disc, Communication |
| 2026-04-28 AMC | MSFT + META Q1 (AI capex guide) | — | Technology, Communication |
| 2026-04-29 2pm ET | FOMC decision (~85% priced hold) | — | All, rate-sensitive |

### Political Overlay
- Trump last 72h: **de-escalatory** on Iran ("THANK YOU" Truth Social, peace "very close", uranium deal sighted)
- No new tariff escalation past 72h
- Named sector threats today: none

### Sentiment Snapshot
- Composite **74.7 (Greed)** — 5pp from extreme threshold
- VIX 17.48 NORMAL · SPY RSI **96.8 extreme stretch** · F&G 68.1 Greed · Above MA200 +7.1%
- `extreme_sentiment_triggered: false` but contextually near-extreme

---

## Phase 4a — Parallel Subagent Proposals

| Lane | HOT | COLD | Rationale |
|---|---|---|---|
| Sector Rotation | Industrials, Financials | Energy, Real Estate | Industrials +0.037 slope leads; Financials INFLOW Normal breadth; Energy -0.031 only down. |
| Theme Intelligence | Industrials, Utilities | Energy, Technology | Iran ceasefire heat 90 Trending; Fed-cut Accelerating + defensive tilt; Tech downgraded on Exhausting narrow rally (RSI 96.8 maturity 90). |
| News Catalyst | Consumer_Discretionary, Financials | Energy, Communication | ConsDisc triple tailwind (oil -10% + ceasefire + core CPI); JPM +19%; Hormuz crash Energy; Netflix -9.3% + GOOGL/META binary. |

**Consensus HOT set (3-condition trip: INFLOW + Accelerating/Trending + bullish news):** Industrials, Financials, Utilities → `consensus_warning: true`

---

## Phase 4b — Devil's Advocate (Isolated Subagent)

### Tail Risk Checks (top 3 HOT proxy ETFs)

| Sector | ETF | Fragility | Score | Excess Kurt | Skew | Max DD | Ann Vol |
|---|---|---|---|---|---|---|---|
| Industrials | XLI | **ROBUST** | 19.5 | 1.01 | +0.14 | 12.2% | 15.3% |
| Financials | XLF | **ROBUST** | 22.9 | 1.02 | -0.31 | 14.8% | 15.2% |
| Utilities | XLU | **ROBUST** | 19.0 | **1.77** | **-0.44** | 9.2% | 13.9% |

All ROBUST → no fragility downgrades. DA forced to find non-tail angles.

### Challenge Targets

**[HIGH] Industrials — binary ceasefire + crowded trade**
- Iran-ceasefire theme (heat 90 Trending) is a binary headline — ceasefires unravel fast; airline pop priced in at XLI 42.1% Overbought while SPY RSI 96.8 + Nasdaq 12-13-day streak (both 1992/2009 instances preceded 5-10% pullbacks within 4 weeks). Commodity avg > Cyclical by 6.5pp with 23rd-pct breadth = classic late-cycle divergence.
- *Risk scenario:* IF Iran-ceasefire headline reverses (Houthi/IRGC re-escalation OR Hormuz shipping incident) AND SPY closes below 20DMA WITHIN 10 trading days THEN Industrials HOT refuted.

**[HIGH] Utilities — defensive-in-RISK_ON incoherent + hawkish Fed tail**
- XLU HOT alongside cyclicals in RISK_ON is historically a distribution-phase signature. XLU kurtosis 1.77 + skew -0.44 are worst of HOT group; already Overbought at 43.9% breadth on 74.7 GREED composite leaves zero margin for hawkish surprise.
- *Risk scenario:* IF next FOMC/Powell presser OR April NFP hawkish (10Y +15bp OR 2026 cut pricing drops ≥25bp) WITHIN 3 weeks THEN Utilities HOT refuted.

**[MEDIUM] Financials — backward-looking JPM + NIM compression**
- JPM +19% is backward Q1 vol; forward steepener/rate-cut compresses NIM (KRE bigger XLF tail than money-center beat suggests). Banks historically lead DOWN 4-8 weeks before breadth-driven corrections (2007 Q2, 2015 Q3, 2018 Q3).
- *Risk scenario:* IF KRE underperforms XLF by ≥3% AND/OR top-5 credit-card issuer (AXP/COF/DFS) guides down on delinquencies WITHIN next 10 trading days THEN Financials HOT refuted.

---

## Phase 4c — Portfolio Strategist Arbitration

**Decision-tree path:** `A:pass(signal_conflict=false) B:pass(synth=60-75%≥40%) C:skip(Mid) D:skip(all ROBUST) E:skip(no within_48h earnings) F:DA_accepted→confidence_intact G:skip → HOT=2, median=WARM → NEUTRAL`

- DA accepted: **Industrials (HIGH)**, **Utilities (HIGH)**, **Financials (MEDIUM)**
- DA rejected: none
- Tail risk downgrades: none (all ROBUST)
- Industrials: base 86.6 × 0.90 = 77.9 → **HOT**（維持但 flagged）
- Financials: base 79.7 × 0.95 = 75.7 → **HOT**（維持）
- Utilities: base 76.3 × 0.90 = 68.7 → **WARM**（DA downgrade dropped HOT→WARM）

**Final regime stance: NEUTRAL (confidence 0.65)** — FTD confirmed anchor but crowded late-cycle tactical peak (breadth 40, hist pct 23, RSI 96.8, 13-day streak, commodity-over-cyclical divergence) warrants caution despite RISK_ON regime.

---

## Action Items

1. **Accept HOT entries** in Industrials (XLI / airlines UAL DAL LUV / transports) and Financials (XLF / JPM / regionals carefully given KRE risk) — but cap sizing; both are consensus-warning & DA-challenged.
2. **Watch Utilities (XLU)** — WARM not HOT despite #1 breadth; defensive rally in RISK_ON is structurally suspect, hawkish-Fed tail is biggest risk.
3. **Avoid Energy (XLE)** — 3/3 lane COLD consensus, OUTFLOW only negative slope, oil -10% still digesting.
4. **Trim Communication exposure** pre GOOGL (4/22) and META (4/28) earnings; Netflix shock already showing guide-miss vulnerability.
5. **Binary watchlist (within_48h):** Iran ceasefire reversal headlines (rolling). This is the single live 48h tail.
6. **Event cluster 4/22–4/29:** TSLA+GOOGL → MSFT+META → FOMC — 7 trading days of binary risk into stretched positioning.

---

*Generated by sector_protocol_main V1.3 · Validated by sector/scripts/validate_sector_intel.py (rc=0)*
