# Sector Intelligence Report — 2026-08-20

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.72
> **Stance**: DEFENSIVE · **Cycle**: Early · **Generated**: 2026-08-20 23:34
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Healthcare | **HOT** | 80 | 1.02 | 多週期RS同步強 · 癌症疫苗催化 | ROBUST | XLV | real_rate_headwind, crowding_watch |
| Energy | **HOT** | 77 | 1.00 | 產業廣度居首 · 短週期RS加速 | ROBUST | XLE | geopolitical_watch, theme_divergence |
| Materials | WARM | 59 | 1.00 | 關鍵礦物政策催化 · 多週期RS同向 | N/A | XLB | smart_money_divergence, real_rate_headwind, consensus_challenged |
| Technology | WARM | 52 | 1.00 | AI題材仍偏多 · 短週期RS轉負 | N/A | XLK | real_rate_headwind, momentum_exhaustion, low_theme_confidence, consensus_challenged |
| Industrials | COLD | 49 | 1.00 | 政策催化偏多 · 工業主題偏空 | N/A | XLI | bearish_theme, earnings_surprise_weak, momentum_exhaustion_watch |
| Financials | COLD | 48 | 1.00 | 估值提供超跌加分 · 產業廣度極弱 | N/A | XLF | oversold_value_opportunity, breadth_weak, short_term_rs_stall |
| Consumer_Discretionary | COLD | 42 | 1.00 | 估值呈超跌 · 主題多空抵銷 | N/A | XLY | oversold_value_opportunity, walmart_demand_warning |
| Communication | COLD | 41 | 1.00 | 產業廣度居中 · 集中主題偏空 | N/A | XLC | bearish_theme, news_neutral, medium_term_rs_weak |
| Consumer_Staples | COLD | 35 | 1.02 | FRED防禦偏好 · 銷售成長轉弱 | N/A | XLP | oversold_value_opportunity, bearish_news, real_rate_headwind, consensus_challenged |
| Real_Estate | COLD | 33 | 1.00 | 估值提供超跌加分 · REIT主題偏空 | N/A | XLRE | oversold_value_opportunity, bearish_theme, real_rate_headwind |
| Utilities | COLD | 29 | 1.00 | 清潔能源主題加速 · 產業廣度近零 | N/A | XLU | breadth_weak, single_theme_concentration, real_rate_headwind |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 75-90% | Synthesized: 75-90% | Cycle: Early
FTD: FTD_CONFIRMED (quality 100) | Market Top: 39.2 Yellow (Early Warning) | Breadth: 79.2 Healthy
Sentiment: F&G [64.9 — Greed] | VIX: 15.59 | Put/Call: n/a | SPY RSI: 55.7
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI與半導體 · 醫療與生技 · 黃金與關鍵礦物

---

## Step 6 — FRED Regime Overlay

- **Regime**: Transitional (confidence 0.5)
- **Favor**: Consumer Staples, Health Care
- **Avoid**: —
- **Velocity highlights**: DGS10:accelerating, DFF:decelerating, CPIAUCSL:decelerating
- **Rationale**: Transitional regime, conf 0.5 → favor: Healthcare×1.025, Consumer_Staples×1.025

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 42.05 | -0.65 | +0.4% | 0.261 |  |
| Healthcare | 24.15 | -1.18 | +15.2% | 0.398 |  |
| Energy | 19.28 | -0.36 | +4.2% | 0.35 |  |
| Financials | 19.35 | -1.06 | +7.9% | 0.356 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 46.24 | -1.36 | -4.3% | 0.291 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 27.89 | -1.83 | -3.3% | 0.424 | 🟢 OVERSOLD VALUE |
| Industrials | 30.38 | -0.58 | +3.0% | 0.372 |  |
| Materials | 25.03 | -0.69 | +3.3% | 0.354 |  |
| Utilities | 26.24 | -0.43 | -4.1% | 0.342 |  |
| Real_Estate | 30.06 | -1.91 | -1.5% | 0.287 | 🟢 OVERSOLD VALUE |
| Communication | 21.28 | -1.38 | -8.1% | 0.201 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.65T | $316.83 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.60T | $484.31 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.27T | $217.56 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.72T | $362.48 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $414.3B | $143.82 | Michael D. Sicilia | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.21T | $1280.74 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $352.9B | $388.61 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $658.9B | $273.41 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $469.9B | $265.97 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $376.0B | $152.22 | Robert Davis | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $683.0B | $164.79 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $409.8B | $205.77 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $159.1B | $130.58 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $79.6B | $149.48 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $79.5B | $53.55 | Olivier Le Peuch | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.08T | $499.80 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $957.3B | $357.26 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $448.3B | $63.17 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $259.9B | $85.95 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $301.4B | $1021.65 | David Solomon | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.86T | $265.84 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.39T | $351.12 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $343.3B | $344.30 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $190.0B | $267.45 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $60.7B | $41.05 | Elliott J. Hill | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $343.3B | $144.40 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $424.4B | $956.99 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $388.7B | $90.35 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $194.8B | $142.58 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $909.6B | $114.30 | John R. Furner | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $369.6B | $356.23 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $375.9B | $816.15 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $297.0B | $220.35 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $70.3B | $221.73 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $179.3B | $301.80 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $222.6B | $481.13 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $85.8B | $353.59 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $99.3B | $69.09 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $67.5B | $303.22 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $80.4B | $285.62 | Christophe Beck | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $179.2B | $85.91 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $106.1B | $92.19 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $96.4B | $123.60 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $68.7B | $126.27 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $56.0B | $85.59 | Jeffrey Walker Martin | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $131.8B | $141.30 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $81.3B | $174.49 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $106.3B | $1077.08 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $169.9B | $235.77 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $32.6B | $74.65 | Christian H. Hillabra… | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.17T | $344.72 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.39T | $546.03 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $334.0B | $80.22 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $185.7B | $106.92 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $195.6B | $182.36 | Srinivasan Gopalan | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.72)

> **DEFENSIVE｜醫療與能源領先，廣度分化仍深**
> 
> 今天先防守，僅偏多醫療與能源；FTD與整體廣度健康，但多數產業參與不足且實質利率偏高，等板塊廣度擴散再提高曝險。

### Key Takeaways
1. 維持防守，主因是七個產業仍為COLD
2. 偏多醫療，三個RS窗口與疫苗催化同向
3. 保留能源，但監控伊朗風險與油價反轉
4. 等待科技短週期RS轉正後再加碼

### Sector Actions
- **Overweight**: Healthcare (high) — 廣度、RS與癌症疫苗催化同向
- **Overweight**: Energy (med) — 廣度居首，但地緣事件波動偏高
- **Wait**: Technology (med) — 題材偏多，短週期RS仍為負
- **Wait**: Materials (med) — 政策利多但smart money分歧
- **Avoid**: Real_Estate (high) — 廣度極弱且高實質利率壓估值
- **Avoid**: Utilities (high) — 單一主題強但產業廣度近零

### Watch Next
- 追蹤實質利率是否降回2.0%以下
- 觀察科技20日與5日RS能否同步轉正
- 監控能源油價與地緣催化是否反轉
- 檢視8月25至27日大型科技財報與Jackson Hole

---

## Devil's Advocate Challenges (Accepted 3/5)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Healthcare — HOT | Rejected | 實質利率2.42%高於2.0%門檻，仍對估值形成壓力。醫療三個RS窗口均強，也提高擁擠反轉風險。 |
| Energy — HOT | Rejected | 實質利率2.42%高於2.0%門檻，要求挑戰能源HOT。能源三個RS窗口均為正，可能已反映大量短期樂觀。 |
| Technology — HOT | **Accepted** | 實質利率2.42%高於門檻0.42個百分點，直接壓抑長久期估值。科技廣度僅0.234，20日RS為-0.75%、5日RS為-2.11%。 |
| Materials — HOT | **Accepted** | 實質利率2.42%高於2.0%門檻，挑戰高融資成本板塊。Senate 30日淨買入-1且insider ratio僅0.893，與新聞分85形成分歧。 |
| Consumer_Staples — HOT | **Accepted** | 實質利率2.42%高於2.0%門檻，仍需挑戰FRED偏好。必需消費廣度僅0.169，三月RS-3.26%、20日RS-0.91%，新聞分僅32。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | news_positive_price_negative | monitor | AI與晶片新聞偏多，但20日與5日RS轉負 |
| Materials | news_positive_price_negative | monitor | 政策與新聞偏多，但Senate 30日淨買入為-1 |

---

## Top Actionable Themes

1. AI與半導體
2. 醫療與生技
3. 黃金與關鍵礦物
4. 清潔能源

---

## HANDOFF TO INVESTMENT PROTOCOL

> 整體廣度與FTD健康，但七個產業仍為COLD；僅醫療與能源為HOT，待板塊廣度擴散再提高風險。
