# Sector Intelligence Report — 2026-06-22

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Mid · **Generated**: 2026-06-22 21:34
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Technology | WARM | 75 | 1.00 | Robotics/AI 題材熱度 72.8 最高 · RS 3M +25.1% 動能仍在 | MODERATE | XLK | signal_conflict_downgrade, smart_money_divergence, real_rate_headwind, consensus_crowding |
| Industrials | WARM | 71 | 1.00 | uptrend 0.365 全場最高、估值便宜 PE z-1.34 · Robotics+Infrastructure+Defense 題材帶動 | ROBUST | XLI | real_rate_headwind |
| Healthcare | WARM | 62 | 1.02 | AbbVie 併購 Apogee $10.9B + Merck 三期成功 · 內部人買超 1.64 最強 | ROBUST | XLV | — |
| Financials | WARM | 57 | 1.00 | PE 20.3、z-1.05 估值便宜（+5 oversold value） · 殖利率曲線陡峭 T10Y2Y+0.64 利差環境改善 | N/A | XLF | oversold_value |
| Communication | COLD | 48 | 1.00 | GOOGL/META AI 利多但 uptrend 僅 0.147 · RS 3M -16.4% 落後 | N/A | XLC | oversold_value, weak_breadth |
| Consumer_Discretionary | COLD | 45 | 1.00 | 題材熱度低 24.1、PE 54.7 偏貴 · Prime Day 測試消費韌性 | N/A | XLY | — |
| Materials | COLD | 44 | 1.00 | 題材集中度 60.8 但催化薄、零新聞流 · uptrend 0.227 中段 | N/A | XLB | — |
| Consumer_Staples | COLD | 42 | 1.02 | FRED favor 防禦 ×1.024 + z-1.19 便宜（+5） · 低 beta 防禦買盤 | N/A | XLP | oversold_value |
| Real_Estate | **AVOID** | 35 | 1.00 | 實質利率 2.17% 直接壓抑利率敏感股 · trend 下彎、OUTFLOW | N/A | XLRE | real_rate_headwind, exposure_floor_avoid, downtrend |
| Energy | **AVOID** | 32 | 1.00 | Chevron-Microsoft 電力交易單一利多 · 但 RS 3M -22.6% 最弱、uptrend 0.073 破線 | N/A | XLE | exposure_floor_avoid, broken_trend |
| Utilities | **AVOID** | 25 | 1.00 | uptrend 0.050 全場最低、OUTFLOW · 實質利率 2.17% 壓抑 | N/A | XLU | real_rate_headwind, exposure_floor_avoid, weakest_breadth |

---

## Macro Context

```text
Market Regime: SIDEWAYS | Breadth Ceiling: 60-75% | Synthesized: 0-25% | Cycle: Mid
FTD: FTD_WINDOW (quality 0) | Market Top: 34.2 Yellow (Early Warning) | Breadth: 53.0 Neutral
Sentiment: F&G [58.6 — Neutral] | VIX: 17.06 | Put/Call: n/a | SPY RSI: 55.1
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Robotics & Automation (Trending, heat 72.8) · Infrastructure & Construction (Trending) · AI & Semiconductors (Mature — 晚期需減碼)

---

## Step 6 — FRED Regime Overlay

- **Regime**: Transitional (confidence 0.47)
- **Favor**: —
- **Avoid**: —
- **Velocity highlights**: T10Y2Y:accelerating, DGS10:accelerating, DFF:decelerating
- **Rationale**: Transitional regime, conf 0.47 → favor: Healthcare×1.024, Consumer_Staples×1.024（其餘 ×1.0；低信度下 overlay 近乎中性）

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 55.14 | +1.83 | +25.1% | 0.803 |  |
| Industrials | 29.84 | -1.34 | -2.9% | 0.951 |  |
| Healthcare | 29.49 | -0.67 | -11.3% | 0.996 |  |
| Financials | 20.26 | -1.05 | -3.8% | 0.967 | 🟢 OVERSOLD VALUE |
| Communication | 22.28 | -1.69 | -16.4% | 1.856 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 54.73 | -0.34 | -6.4% | 1.122 |  |
| Materials | 27.65 | -0.08 | -4.7% | 0.926 |  |
| Consumer_Staples | 30.24 | -1.19 | -11.6% | 0.813 | 🟢 OVERSOLD VALUE |
| Real_Estate | 48.51 | -1.72 | -8.6% | 1.112 | 🟢 OVERSOLD VALUE |
| Energy | 34.53 | +0.93 | -22.6% | 0.991 |  |
| Utilities | 25.91 | -0.85 | -17.0% | 1.851 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.38T | $298.01 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $2.82T | $379.40 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.10T | $210.69 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.96T | $411.35 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $530.1B | $184.31 | Michael D. Sicilia | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $373.7B | $357.64 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $454.1B | $985.82 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $249.9B | $185.60 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $145.1B | $229.01 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $152.5B | $256.88 | Vincenzo James Vena | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.03T | $1098.13 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $364.1B | $400.96 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $549.8B | $228.39 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $382.7B | $216.63 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $281.2B | $113.87 | Robert Davis | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.06T | $489.46 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $871.4B | $325.22 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $398.8B | $56.20 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $251.6B | $82.21 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $323.5B | $1096.56 | David Solomon | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.45T | $368.03 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.47T | $577.22 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $325.8B | $77.38 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $180.4B | $103.89 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $196.6B | $181.67 | Srinivasan Gopalan | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.63T | $244.39 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.50T | $400.49 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $333.3B | $334.28 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $198.0B | $278.61 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $66.8B | $45.20 | Elliott J. Hill | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $236.9B | $512.15 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $79.1B | $320.79 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $98.7B | $68.67 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $62.4B | $280.21 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $75.7B | $269.12 | Christophe Beck | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $350.2B | $150.38 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $421.9B | $951.45 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $341.6B | $79.39 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $194.1B | $142.02 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $932.5B | $117.18 | John R. Furner | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $131.0B | $140.54 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $82.0B | $176.05 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $107.7B | $1092.19 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $145.9B | $206.65 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $35.8B | $82.05 | Christian H. Hillabra… | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $571.2B | $137.81 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $345.8B | $173.63 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $131.3B | $107.74 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $69.2B | $129.98 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $71.9B | $48.09 | Olivier Le Peuch | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $180.9B | $86.75 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $104.9B | $93.09 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $96.6B | $123.86 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $69.5B | $127.69 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $59.3B | $90.69 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.6)

> **防禦為先：反彈未確認、賣壓未清，等 FTD 再加碼**
> 
> 今天先守不追：大盤仍在反彈嘗試但未出現 FTD 確認、廣度偏弱，科技工業雖有題材卻遇內部人賣超與偏高實質利率；保留現金、汰弱留強，等 FTD 確認或核心 PCE 落地再決定是否加碼。

### Key Takeaways
1. 守住現金、曝險壓在 0-25%，反彈未經 FTD 確認前不追高新倉。
2. 科技維持 WARM 不升 HOT：內部人賣超（insider 0.45）＋實質利率 2.17% 壓抑高評價成長股。
3. 偏好低估值＋有催化的防禦：醫療（AbbVie 併購＋insider 1.64）與金融（PE 20、曲線陡峭）相對抗跌。
4. 迴避利率敏感與破線族群：公用、能源、房地產一律 AVOID。
5. 緊盯 6/24 美光財報與 6/25 核心 PCE，作為轉守為攻的觸發點。

### Sector Actions
- **Overweight**: Healthcare (med) — 併購催化＋insider 買超＋防禦favor
- **Wait**: Technology (high) — 題材熱但內部人賣超、估值偏貴，等確認
- **Wait**: Industrials (med) — 題材+估值佳但實質利率壓 capex
- **Neutral**: Financials (med) — 估值便宜、曲線陡峭但廣度弱
- **Avoid**: Energy (high) — RS-22.6% 破線，單一利多不追
- **Avoid**: Utilities (high) — 利率敏感、uptrend 墊底

### Watch Next
- FTD 確認：NASDAQ/S&P 在 rally day 6+ 是否放量突破（解除 0-25% 曝險上限的關鍵）
- 6/24 美光（MU）財報盤後：記憶體/HBM 定價對 AI 半導體鏈 read-through
- 6/25 核心 PCE＋個人所得＋耐久財訂單（Fed 偏好通膨指標，左右降息路徑）
- 6/23 S&P Global PMI 快報（製造/服務景氣動能）
- 實質利率是否守在 2.0% 以上（高評價成長股壓抑的關鍵變數）

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Energy | news_positive_price_negative | monitor | Chevron-Microsoft 電力交易利多 vs RS 3M -22.6%、uptrend 0.073 破線 |
| Technology | news_positive_price_negative | monitor | NVDA 系列利多 + 動能仍在，但內部人賣超 0.45 與 AAPL 下修，留意分歧 |

---

## Top Actionable Themes

1. Robotics & Automation (Trending, heat 72.8)
2. Infrastructure & Construction (Trending)
3. AI & Semiconductors (Mature — 晚期需減碼)

---

## HANDOFF TO INVESTMENT PROTOCOL

> 盤前 DEFENSIVE：反彈未經 FTD 確認＋廣度薄（最佳板塊 uptrend 僅 0.365）＋實質利率 2.17% 偏高。給 investment_protocol：個股可選 WARM 板塊中估值合理、有催化者（醫療/金融/工業/科技龍頭），但整體曝險上限壓在 0-25%，等 FTD 確認或 PCE 落地再升評。能源/公用/房地產迴避。
