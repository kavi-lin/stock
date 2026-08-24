# Sector Intelligence Report — 2026-08-14

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.7
> **Stance**: DEFENSIVE · **Cycle**: Early · **Generated**: 2026-08-14 21:03
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Technology | **HOT** | 85 | 1.08 | AI與半導體主題熱度最高 · breadth與斜率同步改善 | MODERATE | XLK | macro_theme_divergence |
| Industrials | **HOT** | 77 | 1.08 | 國防訂單與工業主題支持 · 財報 beat rate 90.9% | ROBUST | XLI | — |
| Financials | WARM | 69 | 1.04 | 3M RS +9.47% · 財報與smart money偏正面 | N/A | XLF | momentum_exhaustion |
| Energy | WARM | 64 | 1.04 | uptrend ratio全市場最高 · 估值中性且財報 beat 強 | N/A | XLE | overbought |
| Healthcare | WARM | 61 | 0.96 | 3M RS領先 · 財報脈動強但主題已成熟 | N/A | XLV | overbought |
| Communication | COLD | 46 | 1.04 | 3M RS -8.40% · 新聞中性且輪動外流 | N/A | XLC | — |
| Consumer_Discretionary | COLD | 43 | 1.08 | Michigan信心為48小時二元風險 · 估值提供小幅反彈空間 | N/A | XLY | binary_risk_within_48h |
| Materials | COLD | 42 | 1.04 | 3M RS落後 · 新聞與主題催化不足 | N/A | XLB | — |
| Consumer_Staples | COLD | 36 | 0.89 | FRED列入avoid · uptrend ratio偏低 | N/A | XLP | — |
| Real_Estate | COLD | 34 | 0.96 | uptrend ratio與斜率弱 · 估值超跌但缺乏催化 | N/A | XLRE | — |
| Utilities | COLD | 29 | 0.89 | uptrend ratio僅3.7% · FRED列入avoid | N/A | XLU | — |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 75-90% | Synthesized: 75-90% | Cycle: Early
FTD: FTD_CONFIRMED (quality 100) | Market Top: 34.4 Yellow (Early Warning) | Breadth: 79.2 Healthy
Sentiment: F&G [73.5 — Greed] | VIX: 14.52 | Put/Call: n/a | SPY RSI: 67.4
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors · Robotics & Automation · Cloud Computing & SaaS

---

## Step 6 — FRED Regime Overlay

- **Regime**: Soft Landing (confidence 0.76)
- **Favor**: Technology, Industrials, Consumer Discretionary
- **Avoid**: Consumer Staples, Utilities
- **Velocity highlights**: DGS10:accelerating, DFF:decelerating, CPIAUCSL:decelerating
- **Rationale**: Soft Landing regime, conf 0.76 → favor: Technology×1.078, Industrials×1.078, Consumer_Discretionary×1.078; avoid: Consumer_Staples×0.89, Utilities×0.89

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 45.18 | +0.03 | +3.1% | 0.558 |  |
| Healthcare | 23.33 | -1.32 | +10.0% | 0.716 |  |
| Energy | 18.99 | -0.42 | +1.2% | 0.726 |  |
| Financials | 19.54 | -1.03 | +9.5% | 0.766 |  |
| Industrials | 31.34 | -0.29 | +2.2% | 0.769 |  |
| Materials | 24.79 | -0.76 | -4.3% | 0.912 |  |
| Communication | 21.0 | -1.46 | -8.4% | 0.943 |  |
| Consumer_Discretionary | 46.22 | -1.33 | -5.0% | 0.604 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 29.11 | -1.35 | -3.3% | 0.959 | 🟢 OVERSOLD VALUE |
| Utilities | 24.65 | -1.31 | -6.2% | 0.882 | 🟢 OVERSOLD VALUE |
| Real_Estate | 27.84 | -2.26 | -2.7% | 1.137 | 🟢 OVERSOLD VALUE |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.48T | $305.26 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.69T | $496.88 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.46T | $225.30 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.99T | $417.82 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $450.2B | $156.31 | Michael D. Sicilia | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.14T | $1209.85 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $362.4B | $399.06 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $631.6B | $262.08 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $443.3B | $250.88 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $334.8B | $135.55 | Robert Davis | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $657.4B | $158.61 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $393.8B | $197.71 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $151.7B | $124.52 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $75.3B | $141.41 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $77.3B | $52.06 | Olivier Le Peuch | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.09T | $506.93 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $973.0B | $363.11 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $454.8B | $64.09 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $266.5B | $88.13 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $307.6B | $1042.63 | David Solomon | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $374.2B | $360.64 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $393.7B | $854.60 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $297.2B | $220.48 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $74.2B | $233.99 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $176.9B | $297.79 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $221.2B | $478.20 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $87.8B | $361.55 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $96.1B | $66.83 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $68.0B | $305.52 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $77.8B | $276.26 | Christophe Beck | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.19T | $346.36 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.52T | $594.97 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $325.8B | $78.24 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $182.0B | $104.80 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $196.7B | $183.38 | Srinivasan Gopalan | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.85T | $265.13 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.34T | $339.96 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $340.7B | $341.70 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $193.4B | $272.25 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $61.0B | $41.23 | Elliott J. Hill | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $342.9B | $144.26 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $426.6B | $961.85 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $376.1B | $87.42 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $192.1B | $140.62 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $920.9B | $115.72 | John R. Furner | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $179.4B | $86.01 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $106.7B | $92.79 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $97.1B | $124.49 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $68.3B | $125.38 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $56.5B | $86.48 | Jeffrey Walker Martin | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $131.8B | $141.21 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $81.2B | $174.19 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $106.0B | $1073.78 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $169.0B | $234.56 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $33.1B | $75.73 | Christian H. Hillabra… | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.7)

> **防禦：FTD確認但領導集中，收緊新倉**
> 
> 維持防禦、只挑選 Technology 與 Industrials 的相對強勢；FTD 與 breadth 健康但領導集中、real rate 2.43% 且 Market Top 警訊升高；等 breadth 擴散再提高曝險。

### Key Takeaways
1. 保留 Technology 與 Industrials 的核心觀察，採分批進場並控制單筆風險。
2. 收緊停損並降低新倉，因指數仍有分配壓力且領導股集中。
3. 避開 Utilities 與 Consumer Staples，FRED Soft Landing overlay 對兩者維持避開訊號。
4. 監控 real rate 2.43% 與 Technology senate 30 日淨賣出 -3，防止成長股估值壓縮。
5. 等待 breadth 持續擴散，並觀察 8 月 18–20 日財報與宏觀數據是否確認輪動。

### Sector Actions
- **Overweight**: Technology (high) — AI主題與breadth領先，但需控估值風險
- **Overweight**: Industrials (med) — 國防訂單與工業主題支持，留意real rate
- **Wait**: Financials (med) — 3M RS強但短線動能轉弱
- **Wait**: Energy (low) — 廣度偏強但過熱訊號限制追價
- **Underweight**: Consumer_Discretionary (med) — 48小時內消費信心事件帶來二元風險
- **Avoid**: Utilities (high) — FRED避開且uptrend ratio僅3.7%

### Watch Next
- 8 月 14 日 Michigan Consumer Sentiment：結果將影響 Consumer_Discretionary 的風險偏好。
- 8 月 18 日 KEYS、HD、MRCY 財報：檢驗科技與工業催化能否延續。
- 8 月 19 日 FOMC Minutes：留意 real rate 與成長股估值反應。
- 8 月 20 日初領失業救濟金與 Philadelphia Fed：確認工業循環是否降溫。

---

## Devil's Advocate Challenges (Accepted 2/2)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Technology — HOT | **Accepted** | R4 FRED 衝突：real rate 2.43% 高於 2.0% 門檻，對 duration-sensitive 的科技領導交易形成逆風。R5 smart-money divergence 亦觸發：Technology senate 30 日淨買入為 -3，且 XLK 尾部風險僅 MODERATE。 |
| Industrials — HOT | **Accepted** | R4 FRED 衝突：real rate 2.43% 高於 2.0% 門檻，因此即使殖利率曲線正斜且信用壓力低，macro 也不是無條件利多。76.54 的 HOT 分數集中於 rotation inflow、Trending 主題與 bullish news，senate net buy 只有 0，institutional 欄位也不可用。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Financials | news_positive_price_negative | monitor | 3M RS +9.47%，但 20d RS -0.96%、5d RS -0.43%，短線動能有耗盡跡象。 |
| Industrials | news_positive_price_negative | monitor | 新聞與主題偏正面，但 20d RS -0.49%、5d RS -0.65%，需確認相對強度能否回升。 |

---

## Top Actionable Themes

1. AI & Semiconductors
2. Robotics & Automation
3. Cloud Computing & SaaS
4. Industrials Sector Concentration

---

## HANDOFF TO INVESTMENT PROTOCOL

> FTD CONFIRMED, day 7 post-confirmation (rally-day 11; FTD originally confirmed on rally-day 4)；breadth 與 Soft Landing 支持週期板塊，但 Technology/Industrials 領導集中，real rate 與 FOMC 為後續風險監控。
