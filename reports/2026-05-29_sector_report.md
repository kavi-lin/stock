# Sector Intelligence Report — 2026-05-29

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Mid · **Generated**: 2026-05-29 22:09
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Technology | **HOT** | 78 | — | 唯一正向相對強度 +27.2% · AI/半導體題材熱度 87.7 | ROBUST | XLK | overbought, smart_money_divergence |
| Healthcare | WARM | 50 | — | 內部人買超 1.31 · FRED Transitional 偏好防禦 | N/A | XLV | — |
| Industrials | COLD | 49 | — | uptrend 0.295 次高 · RS -12.5% 資金流出 | N/A | — | — |
| Materials | COLD | 43 | — | RS -14.3% 弱 · 題材熱度中性 53.3 | N/A | — | — |
| Consumer_Discretionary | COLD | 43 | — | RS -6.2% 相對最不弱 · PE 58 偏高 | N/A | — | — |
| Energy | COLD | 41 | — | 油價走弱、伊朗未解禁 · PEz +1.53 偏貴 | N/A | — | — |
| Utilities | COLD | 41 | — | 內部人買超 3.26 最強 · AI 電力題材 | N/A | — | — |
| Financials | COLD | 39 | — | 內部人買超 1.34 · GS 看 2026 M&A 創高 | N/A | — | — |
| Real_Estate | COLD | 38 | — | 估值最低 PEz -1.74(+5 oversold) · REIT 反彈敘事 | N/A | — | — |
| Communication | COLD | 36 | — | 估值最低 PEz -1.84(+5 oversold) · 無在線多頭題材 | N/A | — | — |
| Consumer_Staples | COLD | 35 | — | RS -18.0% 最弱 · beat_rate 0.50 偏低 | N/A | — | — |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 60-75% | Synthesized: 60-75% | Cycle: Mid
FTD: FTD_CONFIRMED (quality 100) | Market Top: 23.2 Yellow (Early Warning) | Breadth: 42.4 Neutral
Sentiment: F&G [71.5 — Greed] | VIX: 15.69 | Put/Call: n/a | SPY RSI: 69.5
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors · Quantum Computing · Defense & Aerospace

---

## Step 6 — FRED Regime Overlay

- **Regime**: Transitional (confidence 0.49)
- **Favor**: —
- **Avoid**: —
- **Velocity highlights**: DGS10:accelerating, DFF:decelerating, CPIAUCSL:accelerating
- **Rationale**: Transitional regime, conf 0.49 → favor Healthcare/Consumer_Staples ×1.024 (defensive tilt); cyclical/avoid 無調整(favor/avoid 清單空)

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 52.01 | +1.54 | +27.2% | 0.105 |  |
| Healthcare | 29.63 | -0.64 | -16.8% | 0.109 |  |
| Industrials | 40.71 | +0.47 | -12.5% | 0.072 |  |
| Materials | 27.35 | -0.18 | -14.3% | 0.119 |  |
| Consumer_Discretionary | 58.2 | -0.00 | -6.2% | 0.068 |  |
| Energy | 36.2 | +1.53 | -9.7% | 0.086 |  |
| Utilities | 27.47 | -0.20 | -17.5% | 0.086 |  |
| Financials | 21.17 | -0.69 | -10.6% | 0.072 |  |
| Real_Estate | 49.46 | -1.74 | -10.1% | 0.123 | 🟢 OVERSOLD VALUE |
| Communication | 22.88 | -1.84 | -12.8% | 0.078 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 31.22 | -0.79 | -18.0% | 0.093 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.57T | $311.45 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.14T | $422.97 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.14T | $212.11 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.98T | $418.57 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $564.5B | $196.29 | Michael D. Sicilia | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.08T | $1144.43 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $351.8B | $387.35 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $557.0B | $231.39 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $387.1B | $219.09 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $297.9B | $120.62 | Robert Davis | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $333.1B | $318.85 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $410.6B | $891.27 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $243.4B | $180.73 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $147.1B | $232.21 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $158.5B | $267.00 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $231.4B | $500.20 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $75.5B | $306.10 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $91.4B | $63.60 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $63.1B | $283.21 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $73.7B | $261.93 | Christophe Beck | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.90T | $269.19 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.65T | $440.22 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $318.7B | $319.98 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $198.7B | $279.70 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $69.3B | $46.87 | Elliott J. Hill | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $617.4B | $148.96 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $365.1B | $183.31 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $140.4B | $115.25 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $71.7B | $134.66 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $82.7B | $55.33 | Olivier Le Peuch | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $184.0B | $88.23 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $105.5B | $93.58 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $97.6B | $125.19 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $69.6B | $127.97 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $59.2B | $90.62 | Jeffrey Walker Martin | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.04T | $479.93 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $797.5B | $297.63 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $361.4B | $50.92 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $234.8B | $76.72 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $291.3B | $987.48 | David Solomon | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $136.7B | $146.62 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $87.5B | $187.77 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $105.9B | $1073.29 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $151.9B | $215.24 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $40.2B | $92.07 | Christian H. Hillabra… | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.71T | $389.10 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.62T | $637.00 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $365.2B | $86.72 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $181.0B | $104.21 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $206.9B | $191.19 | Srinivasan Gopalan | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $340.2B | $146.09 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $446.3B | $1005.87 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $348.1B | $80.91 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $201.7B | $147.53 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $944.4B | $118.48 | John R. Furner | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.62)

> **防禦操作：科技獨強，但市場廣度疲弱、情緒偏貪婪**
> 
> 今天偏防禦、別追高：只有科技維持正向相對強度(+27%)，其餘十個板塊資金流出、廣度僅 42、情緒已到貪婪；科技可續抱但收緊停損，盯 6/3 AVGO 與 6/5 非農是否打破窄基行情。

### Key Takeaways
1. 維持防禦、縮小新進場部位 — 廣度僅 42 屬窄基行情
2. 續抱科技但收緊停損 — RS +27% 領先，惟內部人偏賣(0.49)、估值偏高(PEz +1.54)
3. 觀察醫療作防禦性輪動 — 內部人買超(1.31)＋FRED 偏好＋Lilly 利多
4. 避免追逐能源、公用、金融等資金流出板塊，等相對強度轉正
5. 盯緊 6/3 AVGO 與 6/5 非農，檢驗窄基行情是否擴散

### Sector Actions
- **Overweight**: Technology (high) — RS +27% 領先，但收緊停損
- **Wait**: Healthcare (med) — 內部人買超＋FRED 偏好，等轉強
- **Neutral**: Utilities (low) — 內部人買超但題材偏空
- **Underweight**: Energy (med) — 油價走弱、資金流出
- **Avoid**: Communication (low) — 無多頭題材，僅估值便宜
- **Avoid**: Consumer_Staples (med) — RS -18% 最弱、beat 0.50

### Watch Next
- 6/3 AVGO 財報(盤後) — 半導體龍頭，科技 thesis 試金石
- 6/5 非農就業(est 96k vs 前值 115k) — 放緩確認與否牽動全市場
- 6/1 ISM 製造業 PMI(est 52.6) — 景氣擴張續否
- 廣度能否站回 50 ＋ SPY RSI 是否跌破 60 — 窄基行情擴散或瓦解訊號
- 科技內部人賣超比 0.49 是否持續惡化

---

## Devil's Advocate Challenges (Accepted 0/3)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Technology — HOT | — | 唯一正 RS3m(+27.2%)而廣度僅 42.4 = 典型窄基領漲，非全面上升；情緒貪婪 71.5、VIX 15.69、SPY RSI 69.5 三項反身性指標同時偏緊，4 路共識聚合代表交易擁擠而非確認。 |
| Technology — HOT | — | Smart-money divergence：內部人 acquired/disposed ratio 0.49 < 0.5，內部人在 +27.2% 漲勢中淨賣；對比防禦板塊內部人淨買(公用 3.26、金融 1.34、醫療 1.31)，且 senate 淨買 0、機構 QoQ 樣本 0 無增持背書。 |
| Technology — HOT | — | FRED kill：實質利率 2.12% > 2.0% 限制線，FRED lane 因長天期估值承壓將科技列 COLD；DGS10 加速上行，對 PEz +1.54 的溢價估值構成壓縮通道。 |

---

## Top Actionable Themes

1. AI & Semiconductors
2. Quantum Computing
3. Defense & Aerospace

---

## HANDOFF TO INVESTMENT PROTOCOL

> 防禦基調：僅科技維持正向動能且 tail-risk ROBUST，但內部人賣超(0.49)＋估值偏高(PEz +1.54)需收緊停損；醫療為較佳防禦性輪動標的(內部人買超＋FRED 偏好)。整體窄基行情，廣度站回 50 前不擴大暴露；留意 6/3 AVGO 與 6/5 非農。
