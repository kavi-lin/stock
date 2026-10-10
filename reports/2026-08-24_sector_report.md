# Sector Intelligence Report — 2026-08-24

> **Protocol**: V1.4 · **Fan-out**: PARTIAL_FALLBACK · **Regime Confidence**: 0.58
> **Stance**: DEFENSIVE · **Cycle**: Early · **Generated**: 2026-08-24 22:42
> **Degraded Agents**: FRED_Macro_Analyst

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Healthcare | **HOT** | 84 | 1.02 | 資金流入與財報脈動強 · FDA 催化支持醫療需求 | ROBUST | XLV | — |
| Consumer_Staples | WARM | 55 | 1.02 | FRED 制度偏好防禦板塊 · 財報脈動與估值支撐 | N/A | XLP | — |
| Energy | WARM | 52 | 1.00 | 輪動與趨勢居產業首位 · 伊朗制裁可能推升溢價 | N/A | XLE | binary_risk_within_48h |
| Communication | COLD | 49 | 1.00 | 估值均值回歸提供緩衝 · 輪動僅維持中性 | N/A | XLC | — |
| Utilities | COLD | 40 | 1.00 | 價格廣度為全市場最低 · 殖利率上行形成壓力 | N/A | XLU | binary_risk_within_48h |
| Materials | COLD | 38 | 1.00 | 財報脈動提供支撐 · 輪動與廣度仍然偏弱 | N/A | XLB | binary_risk_within_48h |
| Industrials | COLD | 33 | 1.00 | 主題行情集中度偏高 · 輪動仍為資金流出 | N/A | XLI | binary_risk_within_48h |
| Consumer_Discretionary | COLD | 30 | 1.00 | 消費主題方向偏空 · 消費信心即將公布 | N/A | XLY | binary_risk_within_48h |
| Technology | COLD | 25 | 1.00 | AI 主題仍熱但廣度狹窄 · 三項事件風險同時落地 | N/A | XLK | binary_risk_within_48h |
| Financials | **AVOID** | 23 | 1.00 | 輪動流出且廣度薄弱 · 兩項總經事件疊加 | N/A | XLF | binary_risk_within_48h |
| Real_Estate | **AVOID** | 20 | 1.00 | REIT 主題仍為偏空 · 兩項總經事件疊加 | N/A | XLRE | binary_risk_within_48h |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 75-90% | Synthesized: 75-90% | Cycle: Early
FTD: FTD_CONFIRMED (quality 90) | Market Top: 35.6 Yellow (Early Warning) | Breadth: 76.2 Healthy
Sentiment: F&G [63.1 — Greed] | VIX: 15.92 | Put/Call: n/a | SPY RSI: 51.8
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Biotech & Genomics · AI & Semiconductors · Clean Energy & EV

---

## Step 6 — FRED Regime Overlay

- **Regime**: Transitional (confidence 0.47)
- **Favor**: Consumer Staples, Health Care
- **Avoid**: —
- **Velocity highlights**: T10Y2Y:accelerating, DGS10:accelerating, DFF:decelerating
- **Rationale**: Transitional regime, conf 0.47 → favor: Healthcare×1.024, Consumer_Staples×1.024

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 40.23 | -1.07 | -3.0% | 0.24 | 🟢 OVERSOLD VALUE |
| Healthcare | 23.87 | -1.20 | +14.1% | 0.193 |  |
| Energy | 17.82 | -0.64 | +4.1% | 0.161 |  |
| Financials | 19.79 | -0.92 | +10.0% | 0.219 |  |
| Industrials | 29.13 | -0.89 | +1.9% | 0.151 |  |
| Materials | 24.86 | -0.74 | +4.9% | 0.337 |  |
| Communication | 19.26 | -1.70 | -5.0% | 0.114 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 45.02 | -1.52 | -2.9% | 0.175 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 28.74 | -1.43 | +0.7% | 0.239 | 🟢 OVERSOLD VALUE |
| Utilities | 23.47 | -1.01 | -7.8% | 0.167 | 🟢 OVERSOLD VALUE |
| Real_Estate | 38.27 | -1.22 | -0.7% | 0.183 | 🟢 OVERSOLD VALUE |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.54T | $309.35 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.61T | $486.20 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.08T | $209.63 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.75T | $368.45 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $409.6B | $142.19 | Michael D. Sicilia | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.17T | $1247.59 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $360.6B | $397.06 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $654.8B | $271.73 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $468.7B | $265.29 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $372.2B | $150.69 | Robert Davis | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $683.7B | $164.96 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $407.7B | $204.72 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $164.6B | $135.07 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $81.4B | $152.78 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $78.8B | $53.09 | Olivier Le Peuch | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.09T | $503.07 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $957.5B | $357.35 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $442.8B | $62.40 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $257.7B | $85.22 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $306.1B | $1037.75 | David Solomon | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $360.6B | $347.51 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $372.8B | $809.42 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $283.8B | $210.55 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $68.2B | $215.24 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $184.3B | $310.17 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $226.2B | $488.91 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $84.7B | $348.87 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $111.8B | $77.80 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $67.9B | $304.83 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $80.4B | $285.52 | Christophe Beck | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.17T | $344.82 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.41T | $551.78 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $333.2B | $80.02 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $192.3B | $110.72 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $196.5B | $183.21 | Srinivasan Gopalan | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.81T | $261.64 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.40T | $353.25 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $339.0B | $340.02 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $193.4B | $272.15 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $60.7B | $41.03 | Elliott J. Hill | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $347.6B | $146.23 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $425.5B | $959.55 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $396.7B | $92.20 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $198.8B | $145.56 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $833.3B | $104.71 | John R. Furner | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $174.2B | $83.53 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $103.1B | $89.67 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $94.4B | $121.06 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $65.9B | $121.03 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $54.6B | $83.48 | Jeffrey Walker Martin | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $133.6B | $143.20 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $82.7B | $177.53 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $103.2B | $1045.53 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $173.8B | $241.25 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $33.1B | $75.83 | Christian H. Hillabra… | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.58)

> **防禦配置：事件密集期優先守醫療與必需消費**
> 
> 今天先守醫療與必需消費，能源等待伊朗風險落地；通膨、消費信心與大型科技財報明朗後，再考慮提高循環與成長曝險。

### Key Takeaways
1. 降低事件密集板塊的新倉比重
2. 保留醫療相對強勢部位並設標準停損
3. 等待能源地緣溢價與通膨數據落地
4. 監控科技廣度能否從窄幅行情擴散

### Sector Actions
- **Overweight**: Healthcare (high) — 資金流入、財報脈動與 FDA 催化共振
- **Wait**: Energy (med) — 趨勢領先但伊朗制裁屬二元風險
- **Neutral**: Consumer_Staples (med) — FRED 偏好與低估值提供緩衝
- **Underweight**: Technology (high) — 三項事件疊加且行情廣度偏窄
- **Avoid**: Financials (high) — 輪動流出且兩項總經事件疊加
- **Avoid**: Real_Estate (high) — 長端殖利率壓力與事件風險共振

### Watch Next
- 追蹤 8 月 25 日美國消費者信心
- 追蹤 8 月 26 日核心 PCE 與耐久財
- 追蹤 8 月 26 日 NVDA 財報
- 追蹤 8 月 26 日大型軟體股財報群
- 追蹤 8 月 26 日伊朗制裁預告

---

## Devil's Advocate Challenges (Accepted 3/4)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Energy — HOT | **Accepted** | 實質利率 2.37% 高於 2.0%，且趨勢仰賴伊朗二元催化。 |
| Healthcare — HOT | Rejected | 實質利率 2.37% 壓抑長久期 biotech，且主題已進入 Mature。 |
| Technology — HOT | **Accepted** | 實質利率 2.37%、上升趨勢比 0.231，且內部人買賣比 0.461 低於 0.5。 |
| Financials — HOT | **Accepted** | 實質利率 2.37% 可能壓抑貸款需求，且只有 FRED lane 提出 HOT。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | news_positive_price_negative | reduce_exposure | AI 新聞偏多但上升趨勢比僅 0.231 且輪動流出。 |
| Industrials | news_positive_price_negative | monitor | 主題仍 Trending，但價格廣度 0.189 且輪動流出。 |

---

## Top Actionable Themes

1. Biotech & Genomics
2. AI & Semiconductors
3. Clean Energy & EV

---

## HANDOFF TO INVESTMENT PROTOCOL

> 宏觀仍為 RISK_ON，但未來 48 小時二元事件密集；優先醫療與必需消費，能源等待制裁風險落地。
