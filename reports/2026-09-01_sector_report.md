# Sector Intelligence Report — 2026-09-01

> **Protocol**: V1.4 · **Fan-out**: PARTIAL_FALLBACK · **Regime Confidence**: 0.6
> **Stance**: DEFENSIVE · **Cycle**: Early · **Generated**: 2026-09-01 22:46
> **Degraded Agents**: FRED_Macro_Analyst

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Energy | **HOT** | 93 | 1.00 | 產業廣度全場最高 · Hormuz 供給風險 | ROBUST | XLE | — |
| Healthcare | **HOT** | 86 | 1.02 | 三月相對強度領先 · 財報驚喜率強 | ROBUST | XLV | — |
| Financials | WARM | 56 | 1.00 | 三月相對強度突出 · 估值低於一年均值 | N/A | XLF | — |
| Materials | WARM | 53 | 1.00 | 潔淨能源主題外溢 · 相對強度小幅領先 | N/A | XLB | — |
| Consumer_Staples | WARM | 52 | 1.02 | FRED 防禦偏好 · 估值低於一年均值 | N/A | XLP | — |
| Industrials | COLD | 49 | 1.00 | 主題空頭強於多頭 · 相對強度近乎持平 | N/A | XLI | — |
| Technology | COLD | 47 | 1.00 | 四場財報二元風險 · 三月相對強度負八趴 | N/A | XLK | binary_risk_within_48h |
| Communication | COLD | 43 | 1.00 | 缺乏主導主題 · 三月相對強度落後 | N/A | XLC | — |
| Consumer_Discretionary | COLD | 39 | 1.00 | 零售主題偏空 · Amazon 訴訟壓力 | N/A | XLY | — |
| Utilities | COLD | 36 | 1.00 | 產業廣度全場最低 · 殖利率上升承壓 | N/A | XLU | — |
| Real_Estate | COLD | 29 | 1.00 | 房地產主題偏空 · 產業廣度接近底部 | N/A | XLRE | — |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 75-90% | Synthesized: 75-90% | Cycle: Early
FTD: FTD_CONFIRMED (quality 90) | Market Top: 35.5 Yellow (Early Warning) | Breadth: 63.0 Healthy
Sentiment: F&G [60.8 — Greed] | VIX: 15.56 | Put/Call: n/a | SPY RSI: 51.1
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: 能源供給風險與核能主題：偏多 Energy，分批布局 XLE。 · 醫療相對強勢：偏多 Healthcare，但監控內部人交易。 · 科技主題仍熱但價格轉弱：等待財報後再評估 XLK。

---

## Step 6 — FRED Regime Overlay

- **Regime**: Transitional (confidence 0.46)
- **Favor**: Consumer Staples, Health Care
- **Avoid**: —
- **Velocity highlights**: DGS10:accelerating, DFF:decelerating, CPIAUCSL:decelerating
- **Rationale**: Transitional regime, conf 0.46 → favor: Healthcare×1.023, Consumer Staples×1.023

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 40.94 | -0.90 | -8.0% | 0.233 |  |
| Healthcare | 23.38 | -1.23 | +16.9% | 0.257 |  |
| Energy | 18.12 | -0.57 | +10.3% | 0.346 |  |
| Financials | 19.11 | -1.06 | +11.9% | 0.183 | 🟢 OVERSOLD VALUE |
| Industrials | 27.6 | -1.15 | -0.8% | 0.36 | 🟢 OVERSOLD VALUE |
| Materials | 24.41 | -0.81 | +1.2% | 0.237 |  |
| Communication | 18.95 | -1.65 | -2.4% | 0.198 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 45.38 | -1.56 | -2.4% | 0.209 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 28.48 | -1.49 | +4.7% | 0.392 | 🟢 OVERSOLD VALUE |
| Utilities | 23.01 | -1.12 | -4.0% | 0.29 | 🟢 OVERSOLD VALUE |
| Real_Estate | 37.86 | -1.23 | +1.0% | 0.283 | 🟢 OVERSOLD VALUE |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.74T | $322.69 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.74T | $503.80 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.28T | $217.91 | Jensen Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.73T | $363.08 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $413.3B | $143.49 | Michael D. Sicilia | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.11T | $1173.88 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $362.7B | $399.38 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $646.6B | $268.30 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $459.9B | $260.31 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $370.6B | $150.04 | Robert Davis | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $673.5B | $162.50 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $415.4B | $208.60 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $163.3B | $134.06 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $77.8B | $146.04 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $87.5B | $58.95 | Olivier Le Peuch | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.09T | $505.40 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $961.6B | $358.85 | Jamie Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $444.8B | $62.69 | Brian T. Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $265.1B | $87.67 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $302.7B | $1026.07 | David Michael Solomon | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $346.3B | $333.72 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $358.6B | $778.50 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $281.0B | $208.50 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $66.9B | $210.97 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $176.8B | $297.68 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $223.8B | $483.74 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $80.8B | $332.94 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $108.4B | $75.39 | Kathleen L. Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $68.1B | $305.59 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $79.1B | $280.99 | Christophe Beck | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.07T | $336.37 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.45T | $567.68 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $340.4B | $81.75 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $188.6B | $108.61 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $195.7B | $182.48 | Srinivasan Gopalan | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.73T | $254.04 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.41T | $358.12 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $323.6B | $324.49 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $186.2B | $262.08 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $56.8B | $38.41 | Elliott J. Hill | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $351.7B | $147.96 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $421.2B | $949.85 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $383.0B | $89.02 | Henrique Gnani Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $192.2B | $140.72 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $845.1B | $106.20 | John Furner | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $172.2B | $82.55 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $101.3B | $88.04 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $93.8B | $120.27 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $66.7B | $122.58 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $54.5B | $83.41 | Jeffrey Walker Martin | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $129.8B | $139.13 | Daniel S. Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $81.9B | $175.72 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $102.1B | $1034.43 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $173.1B | $240.22 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $33.1B | $75.66 | Christian H. Hillabra… | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.6)

> **防禦：只做能源與醫療，廣度轉弱限制追價**
> 
> 今天聚焦能源與醫療、其餘降風險；廣度惡化與分配日壓過 FTD 利多，等待科技財報與 Hormuz 事件明朗再提高曝險。

### Key Takeaways
1. 採取防禦配置，因多數板塊廣度與輪動偏弱。
2. 提高能源與醫療權重，但採分批進場。
3. 降低科技新倉，等待四場財報落地。
4. 保留一至兩成現金，對應曝險上限。

### Sector Actions
- **Overweight**: Energy (high) — 廣度領先且供給風險支撐
- **Overweight**: Healthcare (high) — 相對強度與財報驚喜率領先
- **Wait**: Consumer Staples (med) — 巨觀偏好與主題偏空互相抵銷
- **Neutral**: Financials (med) — 相對強但廣度仍狹窄
- **Neutral**: Materials (med) — 主題外溢但尚未形成廣泛趨勢
- **Avoid**: Technology (high) — 四場財報前先避開二元風險

### Watch Next
- 追蹤 9 月 2 日 AVGO 財報對 AI 交易的指引。
- 追蹤 9 月 2 日 SNOW 財報對雲端需求的驗證。
- 追蹤 9 月 3 日 ZS 財報對資安支出的訊號。
- 追蹤 9 月 3 日 IOT 財報對工業軟體需求的訊號。
- 監控 Hormuz 供應中斷是否在 48 小時內擴大。

---

## Devil's Advocate Challenges (Accepted 3/3)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Energy — HOT | **Accepted** | Energy 三路共識偏多，但三月相對強度已達 +10.3%、breadth 僅 0.497，且實質利率 2.37% 高於 2.0% 門檻；Hormuz 事件溢價若快速消退，擁擠交易可能反轉。 |
| Healthcare — HOT | **Accepted** | Healthcare 三月相對強度 +16.9% 但 breadth 僅 0.322，強勢仍集中；insider ratio 0.479 低於 0.5，實質利率 2.37% 亦高於門檻。 |
| Technology — COLD | Rejected | Technology 仍有三個 bullish Trending 主題，heat 49.44、47.50、46.65；四場財報若優於預期可能觸發回補，但 insider ratio 0.492 與實質利率 2.37% 限制勝率。 |

---

## Top Actionable Themes

1. 能源供給風險與核能主題：偏多 Energy，分批布局 XLE。
2. 醫療相對強勢：偏多 Healthcare，但監控內部人交易。
3. 科技主題仍熱但價格轉弱：等待財報後再評估 XLK。

---

## HANDOFF TO INVESTMENT PROTOCOL

> 市場仍為 RISK_ON 且曝險上限 75–90%，但廣度惡化與分配日偏高使配置轉防禦；優先能源、醫療，科技等待財報落地。
