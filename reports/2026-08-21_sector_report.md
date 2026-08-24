# Sector Intelligence Report — 2026-08-21

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.68
> **Stance**: DEFENSIVE · **Cycle**: Early · **Generated**: 2026-08-21 21:33
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Healthcare | **HOT** | 76 | 1.02 | RS3m 領先 SPY 14.3% · 癌症療法管線催化 | ROBUST | XLV | high_real_rate |
| Energy | WARM | 71 | 1.00 | 產業廣度升至 0.539 · Brent 接近 94 至 95 美元 | N/A | XLE | high_real_rate, oil_price_reversal |
| Communication | WARM | 50 | 1.00 | 估值 z-score 為 -1.38 · RS3m 落後 SPY 7.6% | N/A | XLC | weak_theme_heat, regulatory_headwind |
| Utilities | COLD | 49 | 1.00 | 產業廣度僅 0.025 · 2.4% 實質利率壓抑 | N/A | XLU | high_real_rate, weak_market_breadth |
| Real_Estate | COLD | 44 | 1.00 | 產業廣度僅 0.070 · 殖利率反彈壓抑估值 | N/A | XLRE | high_real_rate, yield_rebound |
| Technology | COLD | 38 | 1.00 | AI 主題仍為 Trending · 產業廣度僅 0.215 | N/A | XLK | smart_money_divergence, high_real_rate |
| Consumer_Staples | COLD | 38 | 1.02 | Walmart 財報後重挫 · 產業廣度僅 0.121 | N/A | XLP | high_real_rate, macro_news_divergence |
| Materials | COLD | 36 | 1.00 | 黃金主題 heat 45.8 · 產業廣度僅 0.220 | N/A | XLB | binary_risk_within_48h, thin_news_breadth |
| Financials | COLD | 34 | 1.00 | 廣度僅 0.110 · 3M 強但 20d 與 5d 轉弱 | N/A | XLF | binary_risk_within_48h, momentum_exhaustion |
| Industrials | COLD | 33 | 1.00 | 廣度僅 0.181 · 機器人主題偏空 | N/A | XLI | binary_risk_within_48h |
| Consumer_Discretionary | COLD | 25 | 1.00 | RS3m 落後 SPY 4.0% · Tesla 召回壓抑新聞面 | N/A | XLY | binary_risk_within_48h, weak_relative_strength |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 75-90% | Synthesized: 60-75% | Cycle: Early
FTD: FTD_CONFIRMED (quality 100) | Market Top: 40.4 Orange (Elevated Risk) | Breadth: 79.2 Healthy
Sentiment: F&G [62.9 — Greed] | VIX: 15.43 | Put/Call: n/a | SPY RSI: 51.8
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Biotech & Genomics · AI & Semiconductors · Gold & Precious Metals

---

## Step 6 — FRED Regime Overlay

- **Regime**: Transitional (confidence 0.49)
- **Favor**: Consumer Staples, Health Care
- **Avoid**: —
- **Velocity highlights**: T10Y2Y:accelerating, DGS10:accelerating, DFF:decelerating
- **Rationale**: Transitional regime, conf 0.49 → favor: Healthcare×1.024, Consumer_Staples×1.024

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 40.86 | -0.97 | +0.5% | 0.611 |  |
| Healthcare | 23.77 | -1.22 | +14.3% | 1.011 |  |
| Energy | 18.64 | -0.48 | +3.7% | 0.877 |  |
| Financials | 19.12 | -1.11 | +7.4% | 1.018 | 🟢 OVERSOLD VALUE |
| Industrials | 29.77 | -0.71 | +2.4% | 1.032 |  |
| Materials | 24.39 | -0.86 | +2.5% | 0.826 |  |
| Communication | 21.2 | -1.38 | -7.5% | 0.644 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 44.14 | -1.59 | -4.0% | 0.737 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 27.76 | -1.88 | -3.1% | 1.067 | 🟢 OVERSOLD VALUE |
| Utilities | 26.33 | -0.42 | -4.5% | 0.848 |  |
| Real_Estate | 31.61 | -1.75 | -1.4% | 0.785 | 🟢 OVERSOLD VALUE |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.57T | $311.30 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.57T | $481.15 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.25T | $216.85 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.73T | $364.03 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $409.2B | $142.05 | Michael D. Sicilia | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.17T | $1245.69 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $349.5B | $384.85 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $644.3B | $267.37 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $462.6B | $261.83 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $368.6B | $149.25 | Robert Davis | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $689.3B | $166.32 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $409.9B | $205.82 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $164.3B | $134.89 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $81.1B | $152.19 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $79.5B | $53.55 | Olivier Le Peuch | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.07T | $496.96 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $942.0B | $351.55 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $439.0B | $61.86 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $253.1B | $83.70 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $295.6B | $1001.95 | David Solomon | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $357.6B | $344.64 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $375.6B | $815.39 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $286.1B | $212.29 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $69.2B | $218.32 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $180.6B | $303.97 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $222.6B | $481.29 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $84.2B | $346.91 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $102.4B | $71.24 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $66.9B | $300.33 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $79.2B | $281.48 | Christophe Beck | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.12T | $340.67 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.39T | $545.83 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $333.7B | $80.14 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $186.4B | $107.36 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $194.4B | $181.22 | Srinivasan Gopalan | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.80T | $260.11 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.36T | $345.13 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $333.5B | $334.49 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $191.2B | $269.13 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $59.5B | $40.21 | Elliott J. Hill | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $340.0B | $143.01 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $414.0B | $933.51 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $389.4B | $90.50 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $194.1B | $142.08 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $826.4B | $103.84 | John R. Furner | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $177.4B | $85.03 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $105.2B | $91.43 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $95.6B | $122.69 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $68.4B | $125.70 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $57.1B | $87.38 | Jeffrey Walker Martin | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $131.3B | $140.68 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $81.9B | $175.72 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $106.8B | $1082.61 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $171.1B | $237.42 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $32.9B | $75.39 | Christian H. Hillabra… | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.68)

> **防禦：醫療維持主線，PMI 與高實質利率壓抑循環股**
> 
> 保留醫療、能源等待拉回，其餘板塊降低曝險；FTD 與 breadth 仍健康，但分配日、2.4% 實質利率及 PMI 壓力未解，待殖利率回落與事件落地再加碼。

### Key Takeaways
1. 採取防禦配置，因分配日與高實質利率壓抑多數板塊
2. 聚焦 Healthcare，RS3m 領先且 XLV 尾部風險低
3. 等待 Energy 拉回，避免追逐擁擠的油價多頭
4. 降低循環股曝險，先觀察 PMI 對殖利率的影響

### Sector Actions
- **Overweight**: Healthcare (high) — RS3m +14.3%，XLV 尾部風險低
- **Wait**: Energy (med) — 油價催化強，但三個 lane 共識偏擁擠
- **Wait**: Communication (low) — 估值折價，但 RS 與新聞仍弱
- **Avoid**: Technology (high) — 廣度偏低且內部人比率低於 0.5
- **Avoid**: Consumer_Staples (high) — Walmart 訊號偏弱，FRED 偏好未獲確認
- **Avoid**: Real_Estate (high) — 殖利率反彈，產業廣度僅 0.070

### Watch Next
- 追蹤 8/21 美國 PMI 對殖利率與循環股的衝擊
- 監控 10 年期殖利率是否持續回落
- 查看 8/26 NVDA 財報對 AI 資本支出的驗證
- 追蹤 Brent 是否跌破 85 美元

---

## Devil's Advocate Challenges (Accepted 3/4)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Energy — HOT | **Accepted** | Energy 的 INFLOW、Accelerating theme 與 bullish news 形成擁擠的三 lane 共識。實質利率 2.4% 高於 2.0% 門檻，在 RISK_ON／Early regime 下仍是融資逆風。 |
| Technology — HOT | **Accepted** | R5 smart-money divergence 已觸發，內部人買賣比 0.467 低於 0.5。R4 同時觸發，實質利率 2.4% 高於 2.0% 門檻，壓抑長久期估值。 |
| Healthcare — HOT | Rejected | R4 觸發，2.4% 實質利率高於 2.0% 門檻，形成融資與估值逆風。XLV 的 tail-risk 18.3 與最大回撤 10.47% 屬 ROBUST，無法排除相對績效反轉。 |
| Consumer_Staples — HOT | **Accepted** | R4 觸發，2.4% 實質利率高於 2.0% 門檻。FRED 雖偏好 Consumer Staples，但 news lane 偏空且 regime confidence 僅 0.49。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | news_positive_price_negative | monitor | AI 新聞偏正向，但產業廣度僅 0.215 且內部人比率 0.467。 |
| Consumer_Staples | news_negative_price_positive | monitor | FRED 偏好防禦板塊，但 Walmart 訊號與價格廣度仍弱。 |

---

## Top Actionable Themes

1. Biotech & Genomics
2. AI & Semiconductors
3. Gold & Precious Metals

---

## HANDOFF TO INVESTMENT PROTOCOL

> Breadth 與 FTD 仍健康，但 2.4% 實質利率、分配日及 PMI 事件使多數板塊維持 COLD；Healthcare 為唯一 HOT，Energy 保留 WARM。
