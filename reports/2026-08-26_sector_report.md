# Sector Intelligence Report — 2026-08-26

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.62
> **Stance**: DEFENSIVE · **Cycle**: Early · **Generated**: 2026-08-26 23:18
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Healthcare | **HOT** | 76 | 1.02 | 輪動與財報脈動最強 · 生技主題熱度居首 | ROBUST | XLV | momentum_exhaustion, real_rate_headwind |
| Energy | WARM | 69 | 1.00 | 供應風險形成催化 · 輪動廣度相對健康 | N/A | XLE | real_rate_headwind, low_theme_confidence |
| Industrials | WARM | 53 | 1.00 | 耐久財訂單優於預期 · 主題仍維持Trending | N/A | XLI | narrow_breadth, theme_concentration |
| Materials | COLD | 49 | 1.00 | 財報脈動提供支撐 · 耐久財數據偏多 | N/A | XLB | narrow_breadth |
| Utilities | COLD | 37 | 1.00 | 清潔能源主題支撐 · 上升趨勢比僅2.5% | N/A | XLU | binary_risk_within_48h, narrow_breadth, low_theme_confidence |
| Consumer_Staples | COLD | 33 | 1.02 | 估值觸發超賣加分 · FRED偏好防禦板塊 | N/A | XLP | binary_risk_within_48h, bearish_theme |
| Real_Estate | COLD | 31 | 1.00 | 估值觸發超賣加分 · 資料中心需求偏多 | N/A | XLRE | binary_risk_within_48h, bearish_theme, narrow_breadth |
| Communication | COLD | 30 | 1.00 | Meta和解形成重大利空 · 缺乏正向主題支撐 | N/A | XLC | bearish_theme, negative_catalyst |
| Consumer_Discretionary | COLD | 29 | 1.00 | 估值觸發超賣加分 · 零售財報事件密集 | N/A | XLY | binary_risk_within_48h, multiple_binary_events, narrow_breadth |
| Financials | COLD | 25 | 1.00 | 兩項總經事件疊加 · 領先集中於少數成分股 | N/A | XLF | binary_risk_within_48h, multiple_binary_events, narrow_breadth |
| Technology | **AVOID** | 21 | 1.00 | 三項二元事件疊加 · 上升趨勢比僅22.5% | N/A | XLK | binary_risk_within_48h, multiple_binary_events, narrow_breadth |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 75-90% | Synthesized: 75-90% | Cycle: Early
FTD: FTD_CONFIRMED (quality 90) | Market Top: 38.7 Yellow (Early Warning) | Breadth: 76.2 Healthy
Sentiment: F&G [64.7 — Greed] | VIX: 15.48 | Put/Call: n/a | SPY RSI: 54.6
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Biotech & Genomics · Clean Energy & EV

---

## Step 6 — FRED Regime Overlay

- **Regime**: Transitional (confidence 0.49)
- **Favor**: Consumer Staples, Health Care
- **Avoid**: —
- **Velocity highlights**: T10Y2Y:accelerating, DGS10:decelerating, DFF:decelerating
- **Rationale**: Transitional regime, conf 0.49 → favor: Healthcare×1.024, Consumer_Staples×1.024

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 40.74 | -0.95 | -3.3% | 0.146 |  |
| Healthcare | 23.83 | -1.20 | +15.0% | 0.146 |  |
| Energy | 17.88 | -0.62 | +7.6% | 0.304 |  |
| Financials | 19.95 | -0.86 | +11.1% | 0.169 |  |
| Industrials | 29.32 | -0.77 | +1.3% | 0.316 |  |
| Materials | 25.07 | -0.67 | +3.0% | 0.257 |  |
| Communication | 19.43 | -1.64 | -4.8% | 0.283 |  |
| Consumer_Discretionary | 44.4 | -1.58 | -5.6% | 0.15 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 28.76 | -1.40 | +0.1% | 0.204 | 🟢 OVERSOLD VALUE |
| Utilities | 23.8 | -0.87 | -5.8% | 0.199 |  |
| Real_Estate | 39.2 | -1.15 | -0.6% | 0.185 | 🟢 OVERSOLD VALUE |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.55T | $309.66 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.67T | $494.85 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.15T | $212.46 | Jensen Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.71T | $358.39 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $431.7B | $149.88 | Michael D. Sicilia | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.13T | $1200.05 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $367.4B | $404.54 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $650.9B | $270.11 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $460.7B | $260.78 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $379.5B | $153.65 | Robert Davis | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $662.0B | $159.74 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $397.6B | $199.62 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $160.3B | $131.58 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $77.5B | $145.58 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $78.9B | $53.13 | Olivier Le Peuch | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.09T | $505.06 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $955.7B | $356.66 | Jamie Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $441.3B | $62.19 | Brian T. Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $257.1B | $85.03 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $309.7B | $1049.77 | David Michael Solomon | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $368.6B | $355.23 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $377.9B | $820.43 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $285.7B | $212.01 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $69.3B | $218.62 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $185.3B | $311.91 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $227.9B | $492.57 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $85.4B | $351.60 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $115.0B | $80.01 | Kathleen L. Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $68.4B | $307.27 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $82.5B | $293.31 | Christophe Beck | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.18T | $345.49 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.46T | $574.77 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $340.4B | $81.75 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $192.1B | $110.61 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $195.1B | $181.90 | Srinivasan Gopalan | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.80T | $260.67 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.38T | $348.98 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $335.1B | $336.10 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $189.7B | $267.02 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $57.7B | $39.02 | Elliott J. Hill | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $344.8B | $145.05 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $425.1B | $958.47 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $390.7B | $90.80 | Henrique Gnani Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $193.7B | $141.78 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $833.6B | $104.75 | John Furner | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $175.9B | $84.33 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $103.6B | $90.10 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $95.0B | $121.88 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $67.0B | $123.10 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $55.4B | $84.75 | Karen Sedgwick | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $133.4B | $142.93 | Daniel S. Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $83.1B | $178.44 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $106.8B | $1082.62 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $174.1B | $241.64 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $33.3B | $76.30 | Christian H. Hillabra… | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.62)

> **防禦配置：僅醫療保健維持 HOT**
> 
> 今天降低追價、僅偏多醫療保健；多數產業廣度偏弱且科技與利率事件密集，待大型科技財報與 Jackson Hole 落地再提高風險。

### Key Takeaways
1. 降低整體風險，因七個產業仍為 COLD
2. 集中醫療保健，XLV 尾部風險維持 ROBUST
3. 控制科技曝險，三項二元事件在48小時內疊加
4. 保留能源觀察倉，實質利率2.38%壓抑週期交易

### Sector Actions
- **Overweight**: Healthcare (high) — 輪動、財報與FRED偏好共振
- **Wait**: Energy (med) — 催化偏多但實質利率與主題信心受限
- **Neutral**: Industrials (med) — 數據改善但價格廣度尚未擴散
- **Underweight**: Financials (med) — 事件密集且領先集中於少數成分股
- **Avoid**: Technology (high) — 三項二元事件疊加且廣度偏窄

### Watch Next
- 8月26日 NVDA 與大型科技股財報
- 8月27日 Jackson Hole 政策年會
- 8月27日大型股財報群
- 8月28日密大一年通膨預期

---

## Devil's Advocate Challenges (Accepted 2/2)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Energy — HOT | **Accepted** | Energy共識來自高度相關的輪動、主題與新聞訊號。主題信心偏低，且實質利率2.38%高於2.0%門檻，可能反轉週期交易。 |
| Healthcare — HOT | **Accepted** | Healthcare三個月RS為+15.0%，但20日與5日已轉為-0.2%與-0.4%。主題進入Mature，且2.38%實質利率可能形成估值壓力。 |

---

## Top Actionable Themes

1. Biotech & Genomics
2. Clean Energy & EV

---

## HANDOFF TO INVESTMENT PROTOCOL

> 維持防禦配置與75-90%曝險上限；僅Healthcare為HOT，科技與利率二元事件落地前不擴張風險。
