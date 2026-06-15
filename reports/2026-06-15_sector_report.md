# Sector Intelligence Report — 2026-06-15

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Mid · **Generated**: 2026-06-15 20:45
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Technology | WARM | 70 | 1.00 | 唯一正 RS +23.1% · Robotics/AI 主題熱度最高 | N/A | XLK | overbought |
| Industrials | WARM | 54 | 1.00 | uptrend 0.326 最高 · 估值便宜 z-2.02 | N/A | XLI | — |
| Materials | COLD | 48 | 1.00 | 油價跌利好投入成本 · RS -5.9% 仍偏弱 | N/A | — | — |
| Financials | COLD | 46 | 1.00 | 估值便宜 PE 19.8 z-1.19 · RS -2.9% 相對抗跌 | N/A | — | — |
| Consumer_Discretionary | COLD | 42 | 1.00 | 零售銷售 06-17 binary 風險 · Retail 主題最空 | N/A | — | binary_risk_within_48h |
| Communication | COLD | 41 | 1.00 | RS -14.4% 資金外流 · z-1.82 超賣價值 (+5) | N/A | — | — |
| Healthcare | COLD | 40 | 1.03 | 內部人買超 1.69 · J&J $1B 投資利多 | N/A | — | — |
| Real_Estate | COLD | 40 | 1.00 | 利率敏感 FOMC binary · Housing Starts 06-16 訊號 | N/A | — | binary_risk_within_48h |
| Consumer_Staples | COLD | 35 | 1.03 | FRED 防禦 favor · PEP 估值偏貴 ($144 vs $99) | N/A | — | — |
| Energy | COLD | 31 | 1.00 | 油價週跌 5.7% · RS -12.3% 資金外流 | N/A | — | — |
| Utilities | **AVOID** | 23 | 1.00 | uptrend 0.086 全場最弱 · RS -17.2% 重挫 | N/A | — | binary_risk_within_48h |

---

## Macro Context

```text
Market Regime: SIDEWAYS | Breadth Ceiling: 60-75% | Synthesized: 60-75% | Cycle: Mid
FTD: FTD_CONFIRMED (quality 100) | Market Top: 49.5 Orange (Elevated Risk) | Breadth: 46.8 Neutral
Sentiment: F&G [57.3 — Neutral] | VIX: 16.63 | Put/Call: n/a | SPY RSI: 53.0
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Robotics & Automation · AI & Semiconductors · Infrastructure & Construction

---

## Step 6 — FRED Regime Overlay

- **Regime**: Transitional (confidence 0.51)
- **Favor**: —
- **Avoid**: —
- **Velocity highlights**: DFF:decelerating, CPIAUCSL:accelerating, ICSA:decelerating
- **Rationale**: Transitional regime, conf 0.51 → favor: Healthcare×1.026, Consumer_Staples×1.026

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 52.38 | +1.36 | +23.1% | 0.97 |  |
| Industrials | 29.42 | -2.02 | -5.0% | 0.837 |  |
| Materials | 27.87 | -0.05 | -5.9% | 1.23 |  |
| Financials | 19.81 | -1.19 | -2.9% | 1.375 |  |
| Communication | 21.89 | -1.82 | -14.4% | 1.331 | 🟢 OVERSOLD VALUE |
| Healthcare | 30.5 | -0.48 | -9.3% | 0.839 |  |
| Consumer_Staples | 31.29 | -0.68 | -10.7% | 0.743 |  |
| Energy | 35.94 | +1.19 | -12.3% | 0.827 |  |
| Consumer_Discretionary | 55.74 | -0.26 | -6.8% | 0.95 |  |
| Real_Estate | 50.03 | -1.51 | -4.6% | 0.813 |  |
| Utilities | 26.13 | -0.64 | -17.2% | 0.86 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.28T | $291.13 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $2.90T | $390.74 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $4.97T | $205.19 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.82T | $382.07 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $529.6B | $184.13 | Michael D. Sicilia | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $350.3B | $335.30 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $419.4B | $910.57 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $247.2B | $183.53 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $139.6B | $220.31 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $161.9B | $272.70 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $242.2B | $523.57 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $78.3B | $317.30 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $98.3B | $68.41 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $62.7B | $281.62 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $74.7B | $265.41 | Christophe Beck | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.06T | $489.25 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $859.4B | $320.72 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $397.6B | $56.02 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $256.3B | $83.74 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $313.5B | $1062.75 | David Solomon | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.35T | $359.68 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.44T | $566.98 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $338.3B | $80.34 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $173.7B | $100.04 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $204.6B | $189.10 | Srinivasan Gopalan | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.07T | $1133.00 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $371.0B | $408.52 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $579.8B | $240.87 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $402.4B | $227.73 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $294.0B | $119.05 | Robert Davis | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $348.4B | $149.61 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $435.7B | $982.35 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $355.5B | $82.62 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $197.2B | $144.27 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $963.2B | $121.04 | John R. Furner | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $609.3B | $147.00 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $372.9B | $187.22 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $142.5B | $116.98 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $72.8B | $136.65 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $84.0B | $56.18 | Olivier Le Peuch | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.57T | $238.55 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.53T | $406.43 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $327.4B | $328.39 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $202.4B | $284.81 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $66.4B | $44.93 | Elliott J. Hill | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $138.7B | $148.74 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $87.2B | $187.18 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $104.1B | $1055.85 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $151.2B | $214.23 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $40.2B | $92.16 | Christian H. Hillabra… | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $179.3B | $85.99 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $106.0B | $94.00 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $97.4B | $124.97 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $70.3B | $129.23 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $60.3B | $92.29 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.62)

> **防禦為主：指數靠科技獨撐，廣度疲弱、FOMC 在即**
> 
> 盤前以防禦為主、不追高：僅科技獨強但內部人賣超且估值偏貴，整體廣度中性、市場頂部風險升高，FOMC 點陣圖兩天後揭曉；工業可選擇性布局，等利率方向明朗再加碼。

### Key Takeaways
1. 守住防禦部位：整體參與度僅 0.26、廣度 46.8 中性，不宜全面進攻
2. 科技不追高：+23% RS 但內部人賣超 (0.47)、本益比 z+1.36，等回檔
3. 工業選擇性布局：估值便宜 (z-2.02)、Honeywell 分拆催化、內部人買超
4. FOMC 前降風險：利率決議+點陣圖 06-17，利率敏感族群 (REITs/公用) 減碼
5. 公用事業列 AVOID：RS -17.2%、參與度 0.086 全場最弱

### Sector Actions
- **Overweight**: Industrials (med) — 便宜+分拆催化+內部人買超，選擇性布局
- **Wait**: Technology (med) — RS強但內部人賣超+估值貴，等FOMC回檔
- **Neutral**: Healthcare (low) — 內部人買超但RS弱，防禦持有
- **Underweight**: Real_Estate (med) — 利率敏感，FOMC前減碼
- **Underweight**: Energy (med) — 油價週跌5.7%，無反轉催化
- **Avoid**: Utilities (high) — 動能最弱RS-17%，清倉

### Watch Next
- FOMC 利率決議+點陣圖 06-17：轉鷹→科技/REITs/公用承壓
- 美國 5月零售銷售 06-17：驗證 Consumer_Discretionary 消費動能
- Housing Starts/Building Permits 06-16：REITs/營建訊號
- 10年期實質利率 (TIPS)：若站上 2.35% → 長久期科技 DCF 壓力
- 科技內部人賣超 (insider ratio 0.47) 是否延續

---

## Devil's Advocate Challenges (Accepted 0/3)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Technology — HOT | — | 內部人賣超 (acq/disp 0.47 < 0.5) 在 +23.1% RS 漲勢 + PE 52.4 (z+1.36) 高檔同時發生；FRED lane 因實質利率 2.19% (>2.0 DCF 痛點) 將科技列 COLD。廣度 46.8 + uptrend 0.26 證明這是窄基、擁擠的 mega-cap AI 交易，非全面健康。 |
| Industrials — HOT | — | 三方共識 HOT = 擁擠條件，歷史上前瞻報酬最差；FRED regime confidence 僅 0.51、favor 為空無明確背書。便宜 (z-2.02) 可能是價值陷阱：CPI 再加速 + 投入成本黏著恐侵蝕周期性盈餘。 |
| Consumer_Discretionary — COLD | — | COLD 方向正確但可能過度自信：ICSA 減速 (勞動市場仍緊) → 消費者資產負債表仍具韌性，COLD 隱含的消費疲軟假設未必成立；單看估值是差的擇時訊號。 |

---

## Top Actionable Themes

1. Robotics & Automation
2. AI & Semiconductors
3. Infrastructure & Construction
4. Defense & Aerospace

---

## HANDOFF TO INVESTMENT PROTOCOL

> 防禦基調：指數由 mega-cap 科技獨撐、廣度疲弱 (uptrend 0.26)，FOMC 點陣圖 06-17 為近期最大變數。選股偏好便宜+有催化的工業；科技等回檔、勿追高 (內部人賣超 0.47)；利率敏感 REITs/公用減碼。
