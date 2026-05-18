# Sector Intelligence Report — 2026-05-05

> **Protocol**: V1.4 · **Fan-out**: INLINE · **Regime Confidence**: 0.65
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-05-05 22:16
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Energy | WARM | 81.89 | 1.00 | uptrend ratio 60% INFLOW · Iran tensions geopolitical premium | ROBUST | XLE | overbought, binary_risk_within_48h, signal_conflict_downgrade |
| Technology | WARM | 50.49 | 0.91 | AI exuberance narrow leadership · FRED avoid + RSI 71.5 | N/A | XLK | macro_theme_divergence, extreme_sentiment, late_cycle |
| Industrials | COLD | 48.89 | 0.97 | Defense premium 中東 tailwind · ratio 28% slope 轉負 | N/A | XLI | binary_risk_within_48h |
| Communication | COLD | 46.65 | 0.97 | earnings surprise +33% 居首 · valuation z=-1.05 oversold +5 | N/A | XLC | — |
| Materials | COLD | 43.5 | 1.00 | FRED favor 但 RS 持續落後 · 1d -1.87% / rolling -2.32% | N/A | XLB | — |
| Utilities | COLD | 40.81 | 1.00 | AEP/DUK Q1 beats +2.14% 1d · ratio 15% 弱 | N/A | XLU | — |
| Healthcare | COLD | 37.91 | 1.00 | beat rate 100% 但無 theme · GLP-1 bearish, biotech 落後 | N/A | XLV | — |
| Real_Estate | COLD | 35.3 | 0.94 | valuation z=-1.25 oversold +5 · FRED avoid 利率 risk | N/A | XLRE | macro_theme_divergence |
| Financials | COLD | 31.47 | 1.00 | credit risk record low (positive) · FRED favor 但 RS -8.4% | N/A | XLF | — |
| Consumer_Staples | COLD | 31.14 | 1.00 | beat rate 100% 但 surprise 弱 +5% · concentration bearish heat 24 | N/A | XLP | — |
| Consumer_Discretionary | COLD | 27.51 | 0.91 | ratio 9% oversold + OUTFLOW · FRED avoid + bearish concentration | N/A | XLY | macro_theme_divergence |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 40-60% | Synthesized: 40-60% | Cycle: Late
FTD: FTD_CONFIRMED (quality 100) | Market Top: 28.3 Early_Warning | Breadth: 33.1 Weakening
Sentiment: F&G [69.6 — Greed] | VIX: 17.38 | Put/Call: n/a | SPY RSI: 71.5
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Oil & Gas (Energy) · Defense & Aerospace · AI & Semiconductors

---

## Step 6 — FRED Regime Overlay

- **Regime**: Overheating (confidence 0.61)
- **Favor**: Energy, Materials, Financials
- **Avoid**: Technology, Real_Estate, Consumer_Discretionary
- **Velocity highlights**: DFF:decelerating, CPIAUCSL:accelerating, UNRATE:decelerating
- **Rationale**: Overheating regime, conf 0.61 → favor: Energy×0.998, Materials×0.998, Financials×0.998; avoid: Technology×0.912, Real_Estate×0.939, Consumer_Discretionary×0.912

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Energy | 24.52 | +0.88 | +10.1% | 0.122 |  |
| Technology | 46.97 | +0.56 | +10.8% | 0.115 |  |
| Industrials | 41.55 | +0.74 | -2.8% | 0.139 |  |
| Healthcare | 28.52 | -0.89 | -10.7% | 0.117 |  |
| Materials | 27.77 | -0.12 | -3.7% | 0.163 |  |
| Communication | 28.53 | -1.05 | -6.6% | 0.163 | 🟢 OVERSOLD VALUE |
| Real_Estate | 52.72 | -1.25 | +3.2% | 0.233 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 53.08 | -0.32 | -6.5% | 0.112 |  |
| Consumer_Staples | 32.42 | -0.21 | -7.2% | 0.186 |  |
| Financials | 21.36 | -0.57 | -8.4% | 0.144 |  |
| Utilities | 27.27 | -0.22 | +2.9% | 0.13 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## Today's Verdict — DEFENSIVE (confidence 0.65)

> **防守為主：FTD 強但 breadth 33 弱，Energy 是唯一順風**
> 
> FTD CONFIRMED day 19 與 Greed 69.6 給多頭外觀，但 breadth 僅 33 + 11 板塊 10 個下行 + Iran tensions binary 在 48h 內，倉位上限 40-60%。

### Key Takeaways
1. 倉位 ceiling 40-60%（三訊號最低 breadth 主導），不追新高
2. Energy 是唯一強勢但 PT 已消化，回測買進位等 5d/20d RS 同向
3. Tech 不升 HOT：FRED avoid + RSI 71.5 + insider ratio 0.524 三重警示
4. Iran 衝突 48h 內 binary，先檢查 Energy/Industrials 部位風險
5. Cons_Disc 9% uptrend ratio + FRED avoid，避免逢低承接

### Sector Actions
- **Wait**: Energy (high) — PT 已消化、20d RS 轉弱
- **Wait**: Industrials (med) — defense premium 待確認
- **Neutral**: Technology (med) — FRED avoid + narrow leadership
- **Neutral**: Utilities (med) — AEP/DUK beat 但 ratio 15% 弱
- **Neutral**: Communication (low) — earnings surprise 強但 RS 落後
- **Underweight**: Real_Estate (med) — FRED avoid + 利率 risk
- **Avoid**: Consumer_Discretionary (high) — ratio 9% + FRED avoid

### Watch Next
- Iran tensions 是否在 48h 內升級或降溫（決定 Energy/Defense premium）
- 10y real rate 是否站穩 > 2.0%（觸發 FRED Late Cycle 切換）
- S&P 500 breadth 是否回升至 50（解除 Weakening Zone 壓抑）
- FTD day 19 後是否出現 distribution day cluster
- PLTR 等延伸 Q1 財報的個股反應作為 Tech 動能參考

---

## Devil's Advocate Challenges (Accepted 2/3)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Energy — HOT | **Accepted** | PT consensus 已被消化：5 mega-cap PT 中位上行空間僅 0.38%（< 3% 門檻），代表分析師目標價已反映地緣溢價。20-day RS vs SPY -10.9%（過去一個月明顯轉弱），與 3M RS +10.1% 成衝突。 |
| Technology — HOT | **Accepted** | FRED Overheating regime 將 Tech 列為 avoid（real_rate 1.94 接近 2.0 警戒、CPI accelerating）；breadth 僅 35% + slope 已轉負；SPY RSI 71.5 + Greed 69.6 顯示 narrow leadership。Insider ratio 0.524 接近 < 0.5 偏空門檻。 |
| Industrials — HOT | Rejected | 雖有 defense narrative，但 Industrials Concentration（bearish）heat 36.65 Accelerating，UBS 偏好大型股暗示中型 industrials 走弱；rotation slope -0.023、ratio 28% 仍在 MA10 之下。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Energy | news_positive_price_negative | monitor | 3M RS +10.1% 但 20d RS -10.9% — 中東 narrative 強，近月已消化；PT 中位 upside 0.38% 顯示分析師目標已飽和 |
| Technology | news_positive_price_negative | monitor | AI exuberance narrative 持續但 slope 轉負、insider 賣多買少 ratio 0.524 |

---

## Top Actionable Themes

1. Oil & Gas (Energy)
2. Defense & Aerospace
3. AI & Semiconductors

---

## HANDOFF TO INVESTMENT PROTOCOL

> DEFENSIVE stance：FTD CONFIRMED day 19 但 breadth 33 / 11 板塊 10 個下行；Energy 唯一 HOT 因 signal_conflict 降為 WARM；Iran tensions 48h binary，倉位 ceiling 40-60%。投資 protocol 接手時請優先檢視 Energy/Industrials 既有部位風險、避免新增 Cons_Disc/Real_Estate。
