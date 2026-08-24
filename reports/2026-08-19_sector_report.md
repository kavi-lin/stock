# Sector Intelligence Report — 2026-08-19

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.66
> **Stance**: DEFENSIVE · **Cycle**: Early · **Generated**: 2026-08-19 22:18
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Technology | WARM | 55 | 1.07 | AI半導體熱度71.19 · Google晶片交易利多 | MODERATE | XLK | binary_risk_within_48h, real_rate_headwind, consensus_challenged |
| Healthcare | WARM | 54 | 0.96 | 醫療廣度明顯改善 · mRNA癌症疫苗試驗成功 | ROBUST | XLV | binary_risk_within_48h, catalyst_concentration |
| Energy | WARM | 51 | 1.04 | 產業廣度居首 · Chevron新增安哥拉發現 | MODERATE | XLE | binary_risk_within_48h, theme_divergence, tail_risk_capacity_limit |
| Financials | COLD | 39 | 1.04 | 估值提供超跌加分 · 廣度低於10日均值 | ROBUST | XLF | binary_risk_within_48h, smart_money_divergence, real_rate_headwind |
| Consumer_Discretionary | COLD | 37 | 1.07 | 零售財報密集 · 廣度與斜率同步走弱 | N/A | XLY | binary_risk_within_48h, retail_earnings_cluster |
| Communication | COLD | 36 | 1.04 | Google交易提供催化 · 產業集中主題偏空 | N/A | XLC | binary_risk_within_48h, bearish_theme |
| Industrials | COLD | 36 | 1.07 | 工業主題仍Trending · 廣度低於10日均值 | MODERATE | XLI | binary_risk_within_48h, tail_risk_capacity_limit |
| Materials | COLD | 30 | 1.04 | 材料主題仍Trending · 廣度斜率轉弱 | N/A | XLB | binary_risk_within_48h, financing_cost_risk |
| Consumer_Staples | **AVOID** | 22 | 0.90 | FRED列為避開板塊 · 缺乏多頭主題 | N/A | XLP | binary_risk_within_48h, fred_avoid |
| Real_Estate | **AVOID** | 21 | 0.96 | 廣度僅0.071 · REIT主題偏空 | N/A | XLRE | binary_risk_within_48h, bearish_theme, real_rate_headwind |
| Utilities | **AVOID** | 11 | 0.90 | 廣度近乎歸零 · 防禦主題偏空 | N/A | XLU | binary_risk_within_48h, fred_avoid, bearish_theme |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 75-90% | Synthesized: 75-90% | Cycle: Early
FTD: FTD_CONFIRMED (quality 100) | Market Top: 39.2 Yellow (Early Warning) | Breadth: 76.2 Healthy
Sentiment: F&G [66.7 — Greed] | VIX: 15.39 | Put/Call: n/a | SPY RSI: 58.2
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI與半導體 · mRNA癌症疫苗 · 機器人與自動化

---

## Step 6 — FRED Regime Overlay

- **Regime**: Soft Landing (confidence 0.72)
- **Favor**: Technology, Industrials, Consumer Discretionary
- **Avoid**: Consumer Staples, Utilities
- **Velocity highlights**: T10Y2Y:accelerating, DFF:decelerating, CPIAUCSL:decelerating
- **Rationale**: Soft Landing regime, conf 0.72 → favor: Technology×1.074, Industrials×1.074, Consumer_Discretionary×1.074; avoid: Consumer_Staples×0.896, Utilities×0.896

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 43.15 | -0.43 | +1.1% | 0.186 |  |
| Healthcare | 23.66 | -1.25 | +14.3% | 0.385 |  |
| Energy | 19.15 | -0.39 | -0.4% | 0.178 |  |
| Financials | 19.37 | -1.06 | +8.8% | 0.157 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 45.77 | -1.41 | -2.4% | 0.168 | 🟢 OVERSOLD VALUE |
| Communication | 21.16 | -1.41 | -8.8% | 0.121 | 🟢 OVERSOLD VALUE |
| Industrials | 30.51 | -0.47 | +3.7% | 0.189 |  |
| Materials | 24.52 | -0.82 | +2.9% | 0.202 |  |
| Consumer_Staples | 28.97 | -1.39 | -4.0% | 0.197 | 🟢 OVERSOLD VALUE |
| Real_Estate | 29.81 | -1.96 | -2.5% | 0.187 | 🟢 OVERSOLD VALUE |
| Utilities | 26.83 | -0.27 | -5.3% | 0.155 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.55T | $310.03 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.58T | $481.63 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.32T | $219.74 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.81T | $380.00 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $411.0B | $142.67 | Michael D. Sicilia | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.16T | $1226.67 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $357.7B | $393.93 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $653.3B | $271.11 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $457.5B | $258.92 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $333.9B | $135.18 | Robert Davis | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $686.4B | $165.62 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $409.7B | $205.74 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $158.0B | $129.72 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $79.2B | $148.70 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $79.0B | $53.21 | Olivier Le Peuch | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.08T | $502.96 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $973.3B | $363.25 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $455.8B | $64.23 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $264.3B | $87.42 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $306.9B | $1040.47 | David Solomon | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.79T | $259.45 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.33T | $336.87 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $336.5B | $337.49 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $189.7B | $266.99 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $59.3B | $40.06 | Elliott J. Hill | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.17T | $344.20 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.38T | $543.67 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $323.8B | $77.77 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $180.6B | $103.99 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $196.0B | $182.75 | Srinivasan Gopalan | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $389.2B | $375.09 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $387.3B | $840.87 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $303.9B | $225.49 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $72.2B | $227.71 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $177.5B | $298.74 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $221.4B | $478.70 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $83.8B | $345.27 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $95.3B | $66.31 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $67.5B | $303.23 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $78.8B | $280.00 | Christophe Beck | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $341.0B | $143.46 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $426.3B | $961.35 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $382.2B | $88.82 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $191.4B | $140.13 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $916.8B | $115.20 | John R. Furner | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $130.6B | $140.02 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $80.3B | $172.33 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $107.1B | $1085.09 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $169.7B | $235.52 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $32.4B | $74.03 | Christian H. Hillabra… | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $179.9B | $86.22 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $105.9B | $92.07 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $96.7B | $123.99 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $68.8B | $126.35 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $57.0B | $87.18 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.66)

> **DEFENSIVE｜廣度健康但48小時事件密集**
> 
> 今天先防守並縮小新倉，廣度與FTD仍健康，但FOMC紀要和大型財報可能重定價；等利率、零售與製造訊號落地再提高曝險。

### Key Takeaways
1. 維持防守，主因是FOMC與財報事件集中
2. 等待科技廣度確認後再追AI題材
3. 保留醫療與能源觀察倉但不追價
4. 避開公用事業、REIT與必需消費新倉

### Sector Actions
- **Overweight**: Healthcare (med) — 廣度改善且疫苗催化明確，事件前控制倉位
- **Wait**: Technology (med) — AI催化強，但實質利率與廣度緩衝不足
- **Wait**: Energy (med) — 廣度領先但相對強度與主題分歧
- **Underweight**: Financials (high) — 廣度轉弱且smart money訊號分歧
- **Avoid**: Real_Estate (high) — 廣度極弱且高實質利率壓抑估值
- **Avoid**: Utilities (high) — 廣度近零且FRED與主題同向偏空

### Watch Next
- 追蹤8月19日FOMC會議紀要的利率路徑語氣
- 檢視EIA庫存與ADI、TJX、LOW、TGT財報
- 核對初領失業金、費城製造與WMT、DE、ROST財報
- 觀察8月21日美國PMI及UI、BJ財報
- 等待8月26日核心PCE與NVDA、CRWD、CRM財報

---

## Devil's Advocate Challenges (Accepted 4/5)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Healthcare — HOT | Rejected | 醫療三月相對強度+14.3%，已有擁擠反轉風險；實質利率2.41%高於2.0%門檻，仍壓抑長久期生技估值。 |
| Financials — HOT | **Accepted** | 金融三月相對強度+8.8%可能已反映Soft Landing；實質利率2.41%且senate 30日淨買入-1，形成smart money分歧。 |
| Technology — HOT | **Accepted** | 科技廣度0.326僅略高於MA10的0.321；實質利率2.41%且XLK尾風險30.5為MODERATE，直接挑戰三向多頭共識。 |
| Industrials — HOT | **Accepted** | 工業主題熱度49.34弱於AI半導體71.19；實質利率2.41%提高資本密集訂單融資成本，且尾風險因容量上限未驗證。 |
| Energy — HOT | **Accepted** | 能源廣度0.564高於MA10的0.434，但三月相對強度仍-0.4%；清潔能源多頭熱度38.45亦受油氣空頭熱度29.91抵銷。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | news_positive_price_negative | monitor | 晶片交易利多，但三向共識受高實質利率挑戰 |
| Energy | news_positive_price_negative | monitor | 勘探利多與廣度強，但三月相對強度仍為負 |

---

## Top Actionable Themes

1. AI與半導體
2. mRNA癌症疫苗
3. 機器人與自動化
4. 能源廣度修復

---

## HANDOFF TO INVESTMENT PROTOCOL

> 廣度與FTD仍健康，但FOMC紀要及大型財報使全板塊折價；事件落地前僅保留科技、醫療、能源WARM觀察。
