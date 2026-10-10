# Sector Intelligence Report — 2026-08-27

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: NEUTRAL · **Cycle**: Early · **Generated**: 2026-08-27 22:12
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Healthcare | **HOT** | 88 | 1.02 | 趨勢寬度領先 · 生醫主題熱度高 | ROBUST | XLV | — |
| Technology | **HOT** | 76 | 1.00 | AI財報超預期 · 主題動能強勁 | MODERATE | XLK | — |
| Energy | WARM | 73 | 1.00 | 3M相對強弱領先 · 趨勢寬度健康 | ROBUST | XLE | — |
| Financials | WARM | 71 | 1.00 | 3M相對強弱表現強 · 財報超預期比率100% | N/A | XLF | — |
| Materials | WARM | 67 | 1.00 | 原物料主題持穩 · 銅礦與基本金屬需求 | N/A | XLB | — |
| Industrials | WARM | 66 | 1.00 | 機器人自動化主題 · 內部人買賣比例健康 | N/A | XLI | — |
| Consumer_Staples | WARM | 66 | 1.02 | FRED青睞防禦板塊 · 低估值超跌修復機會 | N/A | XLP | — |
| Communication | WARM | 61 | 1.00 | 3M相對強弱落後 · 估值處於低位區間 | N/A | XLC | — |
| Consumer_Discretionary | WARM | 58 | 1.00 | 3M相對強弱疲弱 · 消費支出謹慎 | N/A | XLY | — |
| Real_Estate | WARM | 54 | 1.00 | 趨勢寬度低迷 · 實質利率高壓制房產 | N/A | XLRE | — |
| Utilities | COLD | 47 | 1.00 | 趨勢寬度極低(0.013) · 資金持續流出 | N/A | XLU | — |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 75-90% | Synthesized: 75-90% | Cycle: Early
FTD: FTD_CONFIRMED (quality 90) | Market Top: 35.1 Yellow (Early Warning) | Breadth: 63.8 Healthy
Sentiment: F&G [58.1 — Greed] | VIX: 14.83 | Put/Call: n/a | SPY RSI: 56.4
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Biotech & Genomics · AI & Semiconductors · Robotics & Automation

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
| Healthcare | 23.67 | -1.21 | +12.0% | 0.142 |  |
| Technology | 40.97 | -0.90 | -2.0% | 0.232 |  |
| Energy | 17.86 | -0.62 | +7.0% | 0.149 |  |
| Financials | 19.87 | -0.88 | +11.5% | 0.098 |  |
| Materials | 24.92 | -0.70 | +1.7% | 0.163 |  |
| Industrials | 29.18 | -0.79 | +1.0% | 0.198 |  |
| Consumer_Staples | 28.61 | -1.46 | -0.7% | 0.148 | 🟢 OVERSOLD VALUE |
| Communication | 19.34 | -1.64 | -5.6% | 0.099 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 44.07 | -1.63 | -6.5% | 0.168 | 🟢 OVERSOLD VALUE |
| Real_Estate | 38.94 | -1.17 | -0.7% | 0.222 | 🟢 OVERSOLD VALUE |
| Utilities | 23.81 | -0.86 | -5.4% | 0.133 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.11T | $1178.01 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $360.5B | $396.97 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $636.9B | $264.27 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $455.2B | $257.63 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $370.9B | $150.19 | Robert Davis | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.57T | $311.17 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.71T | $499.76 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.46T | $225.37 | Jensen Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.73T | $364.31 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $435.0B | $151.00 | Michael D. Sicilia | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $648.2B | $156.40 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $395.0B | $198.33 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $157.0B | $128.88 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $76.6B | $143.87 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $79.2B | $53.37 | Olivier Le Peuch | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.08T | $501.85 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $949.7B | $354.42 | Jamie Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $436.2B | $61.46 | Brian T. Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $255.6B | $84.52 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $308.1B | $1044.36 | David Michael Solomon | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $223.4B | $483.01 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $83.8B | $345.15 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $113.2B | $78.77 | Kathleen L. Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $67.7B | $303.90 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $80.4B | $285.59 | Christophe Beck | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $357.8B | $344.80 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $372.1B | $807.84 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $284.2B | $210.90 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $69.3B | $218.57 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $182.9B | $307.90 | Vincenzo James Vena | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $340.7B | $143.30 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $418.2B | $942.93 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $385.6B | $89.62 | Henrique Gnani Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $191.8B | $140.39 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $817.0B | $102.66 | John Furner | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.12T | $340.68 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.49T | $585.29 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $332.1B | $79.75 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $187.8B | $108.12 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $190.5B | $177.59 | Srinivasan Gopalan | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.76T | $256.87 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.38T | $349.45 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $329.0B | $329.97 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $187.5B | $263.90 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $57.2B | $38.63 | Elliott J. Hill | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $132.9B | $142.42 | Daniel S. Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $81.4B | $174.72 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $107.1B | $1084.99 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $172.5B | $239.45 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $32.9B | $75.25 | Christian H. Hillabra… | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $173.0B | $82.94 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $101.9B | $88.56 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $94.0B | $120.56 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $66.7B | $122.47 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $55.0B | $84.13 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — NEUTRAL (confidence 0.75)

> **中性偏多偏好防禦與強勢成長，維持 75-90% 曝險**
> 
> 大盤維持健康廣度與多頭格局，優先配置生醫與科技龍頭，暫避動能破位之公用事業。

### Key Takeaways
1. 確認廣度健康（分數 63.8）且 FTD 有效，維持 75-90% 穩健曝險上限
2. 醫療保健（Healthcare）動能與防禦雙強，獲 FRED 與輪動分析一致評為 HOT
3. 科技（Technology）受惠 AI 財報動能評為 HOT，但須留意內部人處分與實質利率高檔
4. 公用事業（Utilities）趨勢寬度跌破 0.02 且相對強弱落後，維持 COLD 觀望

### Sector Actions
- **Overweight**: Healthcare (high) — 趨勢與3M相對強弱領先，生醫主題熱度高
- **Overweight**: Technology (med) — AI財報超預期支撐，留意高實質利率逆風
- **Neutral**: Energy (med) — 趨勢改善且估值合理，維持標配
- **Neutral**: Financials (med) — 3M相對強弱強勁，財報全數超預期
- **Underweight**: Utilities (high) — 趨勢寬度極低且資金流出明確，避開新建倉

### Watch Next
- 監控美國即將公佈之 Q2 GDP 修正值與 PCE 通膨數據
- 觀察科技巨頭內部人賣壓與 10 年期美債實質利率走勢
- 追蹤生醫與 AI 概念股成交量與回檔支撐力道

---

## Top Actionable Themes

1. Biotech & Genomics
2. AI & Semiconductors
3. Robotics & Automation

---

## HANDOFF TO INVESTMENT PROTOCOL

> 今日市場廣度健康，FTD 第 17 天確認，首選 Healthcare (XLV) 與 Technology (XLK)，Utilities 動能疲弱建議減碼。
