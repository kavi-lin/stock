# Sector Intelligence Report — 2026-05-09

> **Protocol**: V1.4 · **Fan-out**: INLINE · **Regime Confidence**: 0.58
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-05-09 10:40
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Technology | WARM | 61.13 | 0.90 | RS_3M +17.6% 三窗同向領跑全市場 · AI/Semis + Quantum Mature bullish 主題群 | N/A | XLK | macro_theme_divergence, late_cycle |
| Energy | WARM | 60.58 | 1.00 | 9 reports beat 100% surprise +44% 全市場最高 · PBF 煉油廠爆炸短期供給收緊 + FRED favor | N/A | XLE | late_cycle |
| Materials | WARM | 57.78 | 1.00 | FRED Overheating favor cyclical 抗通膨 · Basic Materials Concentration 53.9 Trending bullish | N/A | XLB | late_cycle |
| Industrials | WARM | 55.35 | 0.97 | Honeywell Quantinuum IPO 雙催化 · Infra/Defense 主題 Mature bullish + ratio 0.326 #2 | N/A | XLI | overbought, late_cycle |
| Communication | COLD | 48.37 | 0.97 | PE z-1.12 深度 oversold 給 +5 估值修復獎勵 · Disney/ABC vs Trump 言論衝突 + RS_3M -5.8% | N/A | XLC | late_cycle |
| Real_Estate | COLD | 44.37 | 0.93 | PE z-1.58 極度 oversold → valuation_penalty +5 · FRED avoid + Existing Home Sales 5/11 within_48h | N/A | XLRE | macro_theme_divergence, late_cycle |
| Financials | COLD | 38.32 | 1.00 | FRED favor 但 RS_3M -12.4% 嚴重轉弱 · insider 1.30 + senate +1 唯一雙正 | N/A | XLF | late_cycle |
| Utilities | COLD | 34.31 | 1.00 | ratio 0.10 全市場最低 + RS_20d -13.3% · 8 reports beat 100% + insider 2.57 全市場最高 | N/A | XLU | late_cycle |
| Consumer_Discretionary | COLD | 32.78 | 0.90 | FRED Overheating avoid（消費承擔關稅 + 利率） · NKE 關稅集體訴訟 + 零售銷售 4 月估大減速 | N/A | XLY | macro_theme_divergence, late_cycle |
| Healthcare | COLD | 32.5 | 1.00 | RS_3M -15.8% 全市場最差 · Obesity/GLP-1 + Biotech 主題雙重 bearish | N/A | XLV | late_cycle |
| Consumer_Staples | COLD | 31.8 | 1.00 | RS_3M -11.1% / ratio 0.147 持續轉弱 · Cons Defensive Concentration 主題 bearish 26.0 | N/A | XLP | late_cycle |

---

## Macro Context

```text
Market Regime: SIDEWAYS | Breadth Ceiling: 40-60% | Synthesized: 40-60% | Cycle: Late
FTD: FTD_CONFIRMED (quality 100) | Market Top: 26.9 Early_Warning | Breadth: 33.1 Weakening
Sentiment: F&G [71.2 — Greed] | VIX: 17.19 | Put/Call: n/a | SPY RSI: 73.8
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors · Quantum Computing · Basic Materials Sector Concentration

---

## Step 6 — FRED Regime Overlay

- **Regime**: Overheating (confidence 0.67)
- **Favor**: Energy, Materials, Financials
- **Avoid**: Technology, Real_Estate, Consumer_Discretionary
- **Velocity highlights**: NFCI:accelerating, BAMLH0A0HYM2:accelerating, ICSA:accelerating
- **Rationale**: Overheating regime, conf 0.67 → favor: Materials×0.998, Energy×0.998, Financials×0.998; avoid: Technology×0.903, Real_Estate×0.933, Consumer_Discretionary×0.903

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 47.28 | +0.54 | +17.6% | 1.073 |  |
| Industrials | 42.46 | +0.94 | -6.8% | 0.673 |  |
| Materials | 28.05 | -0.06 | -6.7% | 0.723 |  |
| Energy | 24.4 | +0.63 | -2.2% | 0.703 |  |
| Healthcare | 28.52 | -0.90 | -15.8% | 1.185 |  |
| Communication | 28.01 | -1.12 | -5.8% | 0.914 | 🟢 OVERSOLD VALUE |
| Real_Estate | 51.16 | -1.58 | -1.1% | 0.634 | 🟢 OVERSOLD VALUE |
| Financials | 21.93 | -0.41 | -12.4% | 0.885 |  |
| Consumer_Discretionary | 52.66 | -0.36 | -4.9% | 0.782 |  |
| Consumer_Staples | 32.04 | -0.40 | -11.1% | 0.903 |  |
| Utilities | 29.51 | +0.43 | -3.6% | 0.918 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.31T | $293.32 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.08T | $415.12 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.23T | $215.20 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $2.04T | $430.00 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $563.5B | $195.94 | Michael D. Sicilia | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $598.5B | $144.39 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $362.1B | $181.45 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $138.7B | $113.87 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $69.3B | $130.03 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $79.6B | $53.27 | Olivier Le Peuch | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $228.1B | $493.16 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $78.1B | $316.82 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $88.6B | $61.65 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $65.8B | $295.41 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $71.8B | $254.22 | Christophe Beck | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $310.5B | $297.15 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $417.6B | $897.45 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $237.1B | $176.09 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $135.0B | $213.12 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $157.1B | $264.65 | Vincenzo James Vena | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.85T | $400.80 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.55T | $609.63 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $368.4B | $87.49 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $187.5B | $107.98 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $209.5B | $193.63 | Srinivasan Gopalan | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $134.3B | $144.09 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $82.2B | $176.53 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $105.7B | $1072.08 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $151.5B | $214.63 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $39.5B | $90.57 | Christian H. Hillabra… | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $893.2B | $948.45 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $344.9B | $379.98 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $532.8B | $221.32 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $356.5B | $201.55 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $275.1B | $111.38 | Robert Davis | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.03T | $475.66 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $809.5B | $302.10 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $364.1B | $51.31 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $231.5B | $75.64 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $276.3B | $936.48 | David Solomon | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.93T | $272.68 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.61T | $428.35 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $316.2B | $317.45 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $196.0B | $275.75 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $65.3B | $44.14 | Elliott J. Hill | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $194.1B | $93.10 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $103.5B | $91.80 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $96.8B | $124.17 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $70.8B | $130.16 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $59.8B | $91.53 | Jeffrey Walker Martin | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $341.0B | $146.42 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $447.6B | $1008.79 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $337.5B | $78.42 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $211.4B | $154.62 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $1.04T | $130.43 | John R. Furner | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.58)

> **FTD 強 vs 廣度弱訊號衝突，CPI 前先降風險防 Late 反轉**
> 
> FTD 確認 day22 75-100% 與 breadth 33.1 Weakening 40-60% 上限衝突 37.5pp → 強制取最保守 40-60%；Greed 71.2 + RSI 73.8 + Overheating 制度 + CPI 5/12 加速風險，全板塊無 HOT，先降風險。

### Key Takeaways
1. 三訊號衝突（FTD 87.5 / 廣度 50 / 頂部 85，差距 37.5pp）強制 stance 上限 NEUTRAL，最終裁決 DEFENSIVE 至下週 CPI 過後再評估
2. Tech 為 4 lane 中 3 lane 提名 HOT 的唯一板塊，但 FRED Overheating sector_rotation_avoid 直接觸發 macro_theme_divergence，cap 為 WARM 不允許進場加碼
3. Energy 財報 surprise +44% 領跑但 XLE 三窗口 RS 全負 + volume 0.70（資金未跟進）→ 基本面 vs 流動性背離，等 50DMA 守住再考慮
4. 下週 CPI 5/12 核心 MoM 估 0.4%（前值 0.2%）為 Overheating 制度的關鍵試金石，rate-sensitive 板塊（RE / Tech / Cons Disc）建議事前減碼
5. 全 11 板塊 score < 75 無 HOT verdict、亦無 AVOID < 25；4 個 WARM (Tech/Energy/Materials/Industrials) 暫停加倉，7 個 COLD 觀望

### Sector Actions
- **Wait**: Technology (med) — AI 領跑但 FRED avoid + Overheating 逆風
- **Wait**: Energy (med) — 財報 +44% 但 XLE 三窗口 RS 全負
- **Wait**: Materials (low) — FRED favor + 主題 Trending 但 RS 弱
- **Wait**: Industrials (low) — Quantinuum 催化但 PE z+0.94 偏高
- **Wait**: Real_Estate (low) — PE z-1.58 oversold +5 但 FRED avoid + CPI 風險
- **Underweight**: Healthcare (med) — RS_3M -15.8% 最差 + Trump FDA
- **Underweight**: Consumer_Discretionary (med) — FRED avoid + NKE 關稅訴訟 + 零售減速

### Watch Next
- 美國 4 月成屋銷售 5/11 10:00 ET（est 4.05M vs prev 3.98M）— Real_Estate 短期方向
- 美國 4 月 CPI 5/12 08:30 ET（核心 MoM est 0.4% vs prev 0.2%）— Overheating 制度關鍵驗證
- 美國 4 月 PPI 5/13 08:30 ET（est 0.4% MoM）— 通膨黏性二次確認
- AMAT 5/14 AMC 財報（est EPS $2.68）— 半導體 capex 風向標，AI 主題延續測試
- 美國 4 月零售銷售 5/14 08:30 ET（est 0.4% vs prev 1.7% 大減速）— 消費衰退訊號

---

## Devil's Advocate Challenges (Accepted 3/3)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Technology — HOT | **Accepted** | FRED Overheating + sector_rotation_avoid 同時點名 Technology（real_rate 1.95% 高、CPI 核心將加速到 0.4% MoM、Fed flat）；SPY RSI 73.8 + composite 71.2 Greed 屬獲利了結區；insider ratio 0.505 邊緣 + 議員 net -1 → 內部人和議員雙向減持。 |
| Energy — HOT | **Accepted** | Energy ETF XLE RS_3M -2.2% / RS_20d -10.7% / RS_5d -7.7%（三窗口 RS 皆負且加速轉弱）即便財報 surprise +44% 全市場最高；ETF volume ratio 0.703 < 1（成交量萎縮，缺資金跟進）；insider ratio 0.701 < 1 mild bearish。 |
| Industrials — HOT | **Accepted** | Industrials PE z+0.94 偏高（11 sector 第二高 PE z）+ RS_3M -6.8% 動能弱；ETF volume ratio 0.673 最低（無資金支撐）；4 月零售銷售估值大降速 (1.7%→0.4%) 暗示終端需求衰退將拖累 capex 預期。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Energy | news_positive_price_negative | monitor | 9 reports beat 100% surprise +44% 全市場最高 vs XLE 三窗口 RS 全負（3M -2.2 / 20d -10.7 / 5d -7.7）+ ETF volume ratio 0.70；基本面強但 flow 不買單 |
| Real_Estate | news_negative_price_positive | monitor | PE z-1.58 極度 oversold + insider 1.62 內部人加碼 + 1 報 miss surprise -18%（樣本小）；估值已 price-in 利空但 FRED + CPI 風險未過 |

---

## Top Actionable Themes

1. AI & Semiconductors
2. Quantum Computing
3. Basic Materials Sector Concentration
4. Infrastructure & Construction
5. Oil & Gas (Energy)

---

## HANDOFF TO INVESTMENT PROTOCOL

> DEFENSIVE 至下週 CPI 過後再評估。無 HOT verdict，最強 Tech 受 FRED Overheating avoid 強制 cap WARM。三訊號衝突 37.5pp → synth 40-60% 取最保守。Late + Greed 71 + RSI 73.8 → 不加倉新部位，先觀察 CPI/PPI/AMAT 三大事件 5/12-14。
