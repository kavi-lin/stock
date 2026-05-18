# Sector Intelligence Report — 2026-05-08

> **Protocol**: V1.4 · **Fan-out**: INLINE · **Regime Confidence**: 0.55
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-05-08 17:44
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Technology | WARM | 64.57 | 0.91 | RS_3M +17% 領跑全市場 · AI/Semi/Quantum/Robotics 主題群正向 | FRAGILE | XLK | macro_theme_divergence, fat_tail_warning, extreme_greed_warning |
| Energy | WARM | 50.4 | 1.00 | Q1 surprise +37% 全市場最高 · FRED Overheating favor 實物資產 | RESILIENT | XLE | overbought, binary_risk_within_48h |
| Industrials | COLD | 49.28 | 0.97 | 排名 #2 但 RS 全期負 · Trump 關稅 binary 風險直擊 | RESILIENT | XLI | binary_risk_within_48h |
| Materials | COLD | 47.8 | 1.00 | FRED favor + Concentration heat 52 · RS_3M −6% slope -0.011 失動能 | N/A | XLB | binary_risk_within_48h |
| Communication | COLD | 40.84 | 0.97 | GOOGL/DIS 新聞偏正面 · 估值 z-score -1.11 觸底位 +5 penalty | N/A | XLC | — |
| Healthcare | COLD | 37.3 | 1.00 | beat_rate 100% N=7 surprise +9.6% · 估值 z-score -0.87 偏低 | N/A | XLV | — |
| Financials | COLD | 32.73 | 1.00 | FRED Overheating favor (利差擴) · RS_3M -11.2% slope -0.007 偏弱 | N/A | XLF | — |
| Real_Estate | COLD | 32.49 | 0.94 | 估值 z-score -1.59 全市場最低 +5 penalty · FRED Overheating avoid + Stagflation 壓利率敏感 | N/A | XLRE | macro_theme_divergence |
| Utilities | COLD | 28.5 | 1.00 | ratio 0.10 全市場最弱 + slope -0.016 最陡 · NextEra/Sempra 個股偏多但板塊壓抑 | N/A | XLU | — |
| Consumer_Staples | COLD | 27.7 | 1.00 | ratio 0.111 倒數第 2 · Concentration theme 29 bearish Accelerating | N/A | XLP | — |
| Consumer_Discretionary | **AVOID** | 19.47 | 0.91 | FRED avoid + Trump 關稅 binary 直擊 · MCD K-shaped 經濟負面 | N/A | XLY | macro_theme_divergence, binary_risk_within_48h |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 40-60% | Synthesized: 40-60% | Cycle: Late
FTD: FTD_CONFIRMED (quality 100) | Market Top: 26.4 Early_Warning | Breadth: 33.1 Weakening
Sentiment: F&G [69.6 — Greed] | VIX: 17.05 | Put/Call: n/a | SPY RSI: 69.1
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Basic Materials Sector Concentration (heat 52, bullish) · AI & Semiconductors (heat 50, Mature) · Oil & Gas Energy (heat 48, Trending)

---

## Step 6 — FRED Regime Overlay

- **Regime**: Overheating (confidence 0.61)
- **Favor**: Energy, Materials, Financials
- **Avoid**: Technology, Real Estate, Consumer Discretionary
- **Velocity highlights**: NFCI:accelerating, BAMLH0A0HYM2:accelerating, ICSA:accelerating
- **Rationale**: Overheating regime, conf 0.61 → favor: Energy/Materials/Financials ×0.998; avoid: Technology/Cons_Disc ×0.912, Real_Estate ×0.939

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 46.26 | +0.35 | +17.2% | 1.071 |  |
| Industrials | 40.53 | +0.50 | -4.6% | 1.233 |  |
| Energy | 35.68 | +2.68 | -0.8% | 1.236 |  |
| Materials | 27.51 | -0.15 | -6.2% | 1.272 |  |
| Healthcare | 28.85 | -0.87 | -14.5% | 0.912 |  |
| Communication | 28.13 | -1.11 | -7.0% | 0.955 | 🟢 OVERSOLD VALUE |
| Real_Estate | 51.12 | -1.59 | -0.3% | 1.374 | 🟢 OVERSOLD VALUE |
| Financials | 21.87 | -0.42 | -11.2% | 1.123 |  |
| Consumer_Discretionary | 54.27 | -0.40 | -5.9% | 1.033 |  |
| Consumer_Staples | 32.0 | -0.42 | -11.3% | 0.882 |  |
| Utilities | 28.78 | +0.20 | -3.3% | 1.192 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.22T | $287.44 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.13T | $420.77 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.14T | $211.50 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.95T | $412.56 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $559.5B | $194.53 | Michael D. Sicilia | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $609.3B | $146.58 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $364.2B | $182.51 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $140.0B | $114.88 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $69.7B | $130.89 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $79.2B | $53.00 | Olivier Le Peuch | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $316.2B | $302.63 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $416.8B | $895.69 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $238.1B | $176.78 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $136.9B | $216.07 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $157.3B | $264.89 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $228.8B | $493.85 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $79.0B | $320.21 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $87.1B | $60.61 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $65.7B | $294.99 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $72.5B | $256.55 | Christophe Beck | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.81T | $397.99 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.57T | $616.81 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $371.6B | $88.25 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $192.6B | $108.72 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $210.2B | $194.20 | Srinivasan Gopalan | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $918.2B | $974.96 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $335.6B | $369.74 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $535.6B | $222.51 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $358.5B | $202.71 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $277.4B | $112.30 | Robert Davis | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $132.7B | $142.29 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $83.8B | $179.77 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $105.2B | $1066.76 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $150.3B | $212.95 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $39.7B | $91.07 | Christian H. Hillabra… | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.02T | $475.08 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $826.0B | $306.27 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $374.3B | $52.75 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $242.2B | $79.16 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $274.8B | $925.87 | David Solomon | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.92T | $271.17 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.55T | $411.79 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $321.4B | $322.64 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $201.7B | $283.70 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $65.7B | $44.41 | Elliott J. Hill | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $194.6B | $93.32 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $104.2B | $92.43 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $97.3B | $124.85 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $71.7B | $131.76 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $59.8B | $91.59 | Jeffrey Walker Martin | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $340.1B | $146.06 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $449.0B | $1012.06 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $337.6B | $78.43 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $213.6B | $156.29 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $1.04T | $130.20 | John R. Furner | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.55)

> **DEFENSIVE：FTD 確認但廣度走弱、三訊號衝突**
> 
> FTD 已確認 day 21，但 8MA 0.573 仍低於 200MA、廣度合成 33；FRED Overheating 偏實物/金融、避高估值成長與 REIT；曝險上限壓 40-60%。

### Key Takeaways
1. 三訊號衝突（FTD 75-100 / Breadth 40-60 / MTop 80-90）→ 採最保守 40-60%、stance 不允許 AGGRESSIVE
2. Technology RS 領跑但 FRED avoid + NVDA 走私 + breadth divergence → 降為 WARM 不追高
3. Energy/Materials FRED favor 但估值頂（XLE pe_z 2.68）+ 多週期 RS 反轉 → 戰術不重壓
4. Consumer_Discretionary 受 Trump EU 關稅 binary 直擊 → 觸發 ×0.70 score 懲罰，最該減碼
5. 盯下週 jobs report / CPI、Trump 關稅最後通牒、Iran 局勢 → 任何放鬆都有變盤動能

### Sector Actions
- **Wait**: Technology (high) — FRED avoid 與 RS 強勢矛盾，等廣度回升
- **Wait**: Healthcare (med) — 估值低 + 財報 100% beat，等 RS 止跌
- **Wait**: Communication (low) — 估值 z-score -1.1 但廣度未轉
- **Neutral**: Energy (med) — FRED favor 但估值頂、多週期 RS 反轉
- **Underweight**: Consumer_Discretionary (high) — Trump 關稅 binary + FRED avoid + RS 全負
- **Underweight**: Utilities (med) — ratio 0.10 最弱 + slope -0.016 最陡

### Watch Next
- Trump 5/8 對歐關稅最後通牒結果（binary within_48h，看空 Industrials/Materials/Cons_Disc）
- Iran 戰事油價尾部（binary within_48h，影響 Energy/Materials）
- Breadth 8MA 重回 0.60 之上 → 解除 Weakening_Zone 警戒
- 下週 jobs report / CPI 與 NFP（Fed 路徑、Stagflation 疑慮）
- Distribution Days 是否突破 5 個 O'Neil 警戒線（目前 4.5 effective）

---

## Devil's Advocate Challenges (Accepted 3/3)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Technology — HOT | **Accepted** | FRED Overheating regime 把 Technology 列 avoid（real_rate 1.95% 仍高、PCE YoY 3.2% 黏、Fed flat）。NVDA 晶片走私案升溫出口管制風險；S&P/Nasdaq 觸新高後動能股出現 5y 最大反轉。Distribution Days 4.5 effective 已觸 O'Neil 警戒。 |
| Energy — HOT | **Accepted** | XLE pe_zscore 2.68（1y 極端高）— overbought distribution 風險。RS_3M −0.8% / 20d −10% / 5d −8% 典型動能耗盡。WTI 109.76 已 1y 98 pctile。 |
| Industrials — HOT | **Accepted** | Trump 對歐關稅最後通牒（48h 內）直接打 Industrials；slope falling −0.013（11 sectors 中第 3 陡）；RS_3M −4.6% / 5d −2.1%。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | news_positive_price_negative | monitor | Tech 財報季最強 + RS_3M +17% 但 NVDA 走私 + 動能股 5y 最大反轉 + FRED Overheating avoid |
| Energy | news_positive_price_negative | reduce_exposure | Q1 surprise +37% + Trump 邀 XOM CEO + WTI 109，但 RS_5d/20d 同向 negative + 估值 z-score 2.68 過熱 |
| Healthcare | news_positive_price_negative | monitor | beat_rate 100% N=7 + Insider ratio 1.27 強買，但 RS_3M -14.5% 最弱、GLP-1 主題 bearish |

---

## Top Actionable Themes

1. Basic Materials Sector Concentration (heat 52, bullish)
2. AI & Semiconductors (heat 50, Mature)
3. Oil & Gas Energy (heat 48, Trending)
4. Quantum Computing (heat 48, Mature)
5. Infrastructure & Construction (heat 41, Mature)

---

## HANDOFF TO INVESTMENT PROTOCOL

> Stance=DEFENSIVE/conf 0.55. WARM 僅 Tech (RS 領先但 FRED avoid + NVDA 走私) 與 Energy (FRED favor 但估值頂)。投資選股建議：(1) Tech 只挑 ratio<-1y_z 的低估個股，避 NVDA/AVGO 等 +2σ 名單；(2) Healthcare 估值 z -0.87 + beat 100% 是 contrarian 觀察池但等 RS 止跌；(3) 嚴避 Cons_Disc/REIT (FRED avoid + binary)；曝險上限 40-60%。
