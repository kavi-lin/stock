# Sector Intelligence Report — 2026-05-07

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.55
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-05-07 21:50
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Industrials | WARM | 59.84 | 1.00 | Defense/Infrastructure 主題支撐 · trend Down 廣度疲弱 | N/A | XLI | late_cycle, overbought |
| Technology | WARM | 55.34 | 1.00 | RS 全週期領先 · AI semis 財報 + PT 21% | N/A | XLK | late_cycle, overbought |
| Materials | WARM | 55.03 | 1.00 | Basic Materials Trending 主題 · trend Down 廣度疲弱 | N/A | XLB | late_cycle, overbought |
| Real_Estate | COLD | 49.59 | 1.00 | pe_z -1.315 oversold value · Up trend 但 ratio 24.8% | N/A | XLRE | — |
| Communication | COLD | 46.92 | 1.00 | Up trend 但 RS 負 -7.4% · Quantum/Space 邊緣加分 | N/A | XLC | — |
| Healthcare | COLD | 46.26 | 1.00 | RS 全週期最弱 · earnings 5/5 beat + GLP-1 | N/A | XLV | — |
| Energy | COLD | 43.58 | 1.00 | 48h Hormuz binary · pe_z 3.365 估值極端 | N/A | XLE | binary_risk_within_48h, late_cycle |
| Utilities | COLD | 39.19 | 1.00 | uptrend 12.2% 最低 · earnings 7/7 beat 但動能弱 | N/A | XLU | — |
| Financials | COLD | 38.73 | 1.00 | theme bearish 18.2 · Down trend RS 負 | N/A | XLF | — |
| Consumer_Discretionary | COLD | 35.99 | 1.00 | theme bearish concentration · 0 reports sample 不足 | N/A | XLY | — |
| Consumer_Staples | COLD | 35.97 | 1.03 | FRED favor (1.026 overlay) · RS 全週期負 -12%/3M | N/A | XLP | — |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 40-60% | Synthesized: 40-60% | Cycle: Late
FTD: FTD_CONFIRMED (quality 100) | Market Top: 26.4 Early_Warning | Breadth: 33.1 Weakening
Sentiment: F&G [70.8 — Greed] | VIX: 17.31 | Put/Call: n/a | SPY RSI: 72.3
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Space Economy · Infrastructure & Construction · Defense & Aerospace

---

## Step 6 — FRED Regime Overlay

- **Regime**: Transitional (confidence 0.53)
- **Favor**: Consumer Staples, Health Care
- **Avoid**: —
- **Velocity highlights**: DFF:decelerating, CPIAUCSL:accelerating, UNRATE:decelerating
- **Rationale**: Transitional regime, conf 0.53 → favor: Consumer_Staples×1.026

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Industrials | 42.44 | +0.94 | -2.9% | 0.009 |  |
| Materials | 28.06 | -0.07 | -4.1% | 0.004 |  |
| Technology | 48.11 | +0.90 | +17.2% | 0.012 |  |
| Energy | 38.84 | +3.37 | -1.5% | 0.032 |  |
| Healthcare | 29.6 | -0.74 | -14.4% | 0.015 |  |
| Communication | 28.53 | -1.06 | -7.3% | 0.007 | 🟢 OVERSOLD VALUE |
| Financials | 21.46 | -0.54 | -11.1% | 0.019 |  |
| Real_Estate | 52.03 | -1.31 | -0.1% | 0.045 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 52.87 | -0.49 | -5.5% | 0.028 |  |
| Consumer_Staples | 32.12 | -0.36 | -12.0% | 0.009 |  |
| Utilities | 29.5 | +0.43 | -2.7% | 0.009 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $319.5B | $305.83 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $431.3B | $926.93 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $238.0B | $176.74 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $137.4B | $216.86 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $159.3B | $268.23 | Vincenzo James Vena | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.22T | $287.51 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.08T | $413.96 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.05T | $207.83 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $2.01T | $425.44 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $557.9B | $193.99 | Michael D. Sicilia | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $232.6B | $501.87 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $79.8B | $323.63 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $87.5B | $60.89 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $66.8B | $300.21 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $74.4B | $263.42 | Christophe Beck | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $133.2B | $142.90 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $83.9B | $180.16 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $107.3B | $1087.96 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $152.8B | $216.47 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $39.4B | $90.24 | Christian H. Hillabra… | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.81T | $398.04 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.56T | $612.88 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $371.7B | $88.27 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $191.3B | $107.99 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $209.0B | $193.16 | Srinivasan Gopalan | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $932.6B | $987.11 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $333.4B | $367.28 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $540.7B | $224.62 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $362.6B | $204.98 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $280.5B | $113.56 | Robert Davis | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $617.5B | $148.56 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $369.4B | $185.13 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $144.9B | $118.90 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $72.2B | $134.69 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $82.5B | $55.16 | Olivier Le Peuch | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $198.9B | $95.39 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $105.4B | $93.51 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $97.7B | $125.54 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $72.1B | $132.56 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $61.2B | $93.66 | Jeffrey Walker Martin | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.01T | $469.83 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $849.3B | $314.90 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $380.4B | $53.60 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $246.0B | $80.40 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $278.2B | $937.35 | David Solomon | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.96T | $274.99 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.50T | $398.73 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $321.8B | $323.05 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $201.9B | $284.10 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $64.9B | $43.88 | Elliott J. Hill | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $344.5B | $147.93 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $441.8B | $995.75 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $341.0B | $79.23 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $213.2B | $155.96 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $1.04T | $130.08 | John R. Furner | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.55)

> **DEFENSIVE：FTD 雖確認但廣度衰退 + 信號分歧主導**
> 
> 三訊號衝突 (FTD 100 vs Breadth 33.1)、Late-cycle 派發訊號、SPY RSI 72.3 + F&G 70.8 Greed 過熱；曝險上限 40-60%，無 HOT、八個 COLD，等廣度回升或 binary 出清前避免追高。

### Key Takeaways
1. 鎖定 stance DEFENSIVE — signal_conflict 強制不得 AGGRESSIVE
2. 曝險上限 40-60%，現有部位先收最弱 25%、不開新動能單
3. Energy 在 Hormuz/伊朗 binary 收尾前壓低部位，避免追高 pe_z 3.365 估值極端
4. Tech RS 雖領先但 SPY RSI 72.3 + Mature stage 屬 blow-off 風險，等 RSI 回 60 以下再考慮
5. 防禦輪動觀察：FRED Transitional favor Staples/HC，但 RS 全週期仍負，等 capitulation

### Sector Actions
- **Wait**: Industrials (med) — Mature 主題 + RS 3M 已負，廣度未恢復前等
- **Wait**: Technology (high) — RSI 72.3 + Mature + insider 0.519 邊緣
- **Wait**: Materials (med) — Trending 主題但 trend Down + 廣度疲弱
- **Neutral**: Real_Estate (low) — z-1.31 oversold value 觀察點
- **Neutral**: Consumer_Staples (low) — FRED favor 但價格動能弱
- **Underweight**: Energy (high) — 48h binary + pe_z 3.365 + 3M RS 負

### Watch Next
- Hormuz/伊朗 binary 出清 (5/7-5/8) — 影響 Energy/Industrials Defense
- 美伊核協議 24h 結果 (5/8) — 油價 ±$10-15
- Breadth 8MA 是否收復 0.60 + 200MA gap 翻正
- SPY RSI 是否冷卻至 60 以下
- FRED real_rate 是否突破 2.0 防禦觸發點

---

## Devil's Advocate Challenges (Accepted 3/3)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Energy — HOT | **Accepted** | Energy 3M RS -1.5% 已負，pe_z 3.365 為 >3 sigma 估值極端歷史多為派發區。Insider ratio 0.658 <1.0 (內部人偏賣)，senate_net 0、institutional inflow +701 (n=11) 為 HOT 提案中最低，整個 HOT call 立基於 48h 二元地緣事件 — 若 de-escalate，6.5% PT upside (already <10%) 在無動能支撐下崩潰。 |
| Technology — HOT | **Accepted** | Macro 環境敵視追高：SPY RSI 72.3 超買、F&G 70.8 Greed、Market Top Yellow Early Warning + distribution_days 75、明確 'Dangerous bearish divergence: S&P +6.3%、Breadth 8MA -0.115 60d'、breadth peak 44d ago — Tech 在窄幅市場領導為典型 Late-cycle blow-off。Insider ratio 0.519 剛好踩 0.5 bearish 門檻、theme stage ... |
| Industrials — HOT | **Accepted** | Industrials 3M RS -2.9% 為負 — 'stacked bullish theme' 為敘事而非價格確認。Breadth 33.1 Weakening + 200MA gap -0.027 + FRED Transitional 明確 favor 防禦 (Staples/HC) 而非 cyclicals — 直接跨 lane 衝突。最高 composite 僅 59.84 (無 sector 過 75 tail-risk 門檻)，整個 HOT slate 由弱絕對強度為基底。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Energy | news_positive_price_negative | monitor | 9 reports 100% beat / +0.44 surprise + Hormuz tail，但 3M RS -1.5% / 5d -8.6% 已先反轉 |
| Technology | news_positive_price_negative | monitor | AI semis 利多 + PT 21%，但 Mature stage + breadth divergence + insider 0.519 borderline |
| Real_Estate | news_negative_price_positive | monitor | earnings 0/2 beat -0.10，但 Up trend + pe_z -1.315 oversold value 浮現 |

---

## Top Actionable Themes

1. Space Economy
2. Infrastructure & Construction
3. Defense & Aerospace
4. AI & Semiconductors
5. Oil & Gas (Energy)

---

## HANDOFF TO INVESTMENT PROTOCOL

> Stance DEFENSIVE：signal_conflict 強制 ≤NEUTRAL，曝險 40-60%；無 HOT、3 WARM (Indust/Tech/Mat)、8 COLD；Late-cycle + dangerous divergence + RSI 72.3 過熱主導；Energy/Hormuz binary 5/7-5/8 出清前避免追高；防禦輪動 (Staples/HC) FRED favor 但 RS 仍負，等 capitulation。
