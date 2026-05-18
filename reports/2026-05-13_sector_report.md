# Sector Intelligence Report — 2026-05-13

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.62
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-05-13 20:45
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Energy | WARM | 79.1 | 1.00 | 唯一 breadth>MA10 + 上揚斜率 · Trending bullish 主題 Oil&Gas 熱度 59.5 | RESILIENT | XLE | overbought, late_cycle |
| Materials | WARM | 72.7 | 1.00 | 第二佳 breadth(0.414)+ 上揚斜率 · 通膨對沖 + 中美關稅故事 | RESILIENT | XLB | late_cycle |
| Technology | COLD | 44.3 | 0.90 | RS3M +16% 但 breadth 0.36 < MA10 · FRED Overheating avoid + Shiller 泡沫警示 | RESILIENT | XLK | macro_theme_divergence, overbought |
| Industrials | COLD | 40.3 | 0.96 | 4 個 bullish themes 收斂(Space/Infra/Defense/Robot) · breadth 0.279 < MA10、斜率 -0.011 | N/A | XLI | late_cycle |
| Healthcare | COLD | 38.0 | 1.00 | 唯一 ratio>MA10 的 defensive(0.258) · GLP-1 看空主題 51.4 主導敘事 | N/A | XLV | — |
| Financials | COLD | 29.7 | 1.00 | FRED Overheating favor + 利差 +0.72 · 但 breadth 0.124(最差)+ 斜率 -0.0143 | N/A | XLF | — |
| Real_Estate | COLD | 26.0 | 0.93 | PE z-1.58 + uptrend 0.224 → oversold value +5 · FRED Overheating avoid(實質利率 1.95%) | N/A | XLRE | — |
| Consumer_Discretionary | **AVOID** | 23.1 | 0.90 | breadth 0.110 最低 + 斜率 -0.0118 · FRED Overheating avoid + Trump 關稅減免有利但已 priced | N/A | XLY | late_cycle |
| Consumer_Staples | **AVOID** | 22.7 | 1.00 | RISK_ON 環境下防禦類無 bid · Defensive Concentration 看空 28.1 | N/A | XLP | — |
| Communication | **AVOID** | 20.9 | 0.96 | PE z-1.29 + uptrend 0.157 → oversold value +5 · breadth 0.157 遠低於 MA10 0.214 | N/A | XLC | — |
| Utilities | **AVOID** | 17.6 | 1.00 | RS20d -9.05% 最差 + breadth 0.113 · RISK_ON 防禦類無 bid | N/A | XLU | — |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 40-60% | Synthesized: 40-60% | Cycle: Late
FTD: FTD_CONFIRMED (quality 100) | Market Top: 28.4 Early_Warning | Breadth: 33.1 Weakening
Sentiment: F&G [70.4 — Greed] | VIX: 17.93 | Put/Call: n/a | SPY RSI: 76.1
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors · Oil & Gas (Energy) · Basic Materials Concentration

---

## Step 6 — FRED Regime Overlay

- **Regime**: Overheating (confidence 0.7)
- **Favor**: Energy, Materials, Financials
- **Avoid**: Technology, Real_Estate, Consumer_Discretionary
- **Velocity highlights**: DGS10:accelerating, DFF:decelerating, CPIAUCSL:accelerating
- **Rationale**: Overheating regime, conf 0.70 → favor: Energy×0.998, Materials×0.998, Financials×0.998; avoid: Technology×0.898, Consumer_Discretionary×0.898, Real_Estate×0.93

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 47.87 | +0.67 | +16.2% | 1.513 |  |
| Healthcare | 28.59 | -0.86 | -12.8% | 1.36 |  |
| Energy | 37.35 | +2.51 | +0.8% | 0.887 |  |
| Financials | 22.16 | -0.35 | -10.3% | 1.346 |  |
| Consumer_Discretionary | 57.07 | -0.24 | -6.7% | 0.854 |  |
| Consumer_Staples | 32.04 | -0.38 | -9.8% | 1.418 |  |
| Industrials | 39.84 | +0.31 | -6.4% | 0.854 |  |
| Materials | 28.11 | -0.05 | -8.1% | 1.103 |  |
| Utilities | 27.06 | -0.31 | -4.4% | 1.403 |  |
| Real_Estate | 50.64 | -1.58 | -2.6% | 0.991 | 🟢 OVERSOLD VALUE |
| Communication | 27.11 | -1.29 | -8.1% | 1.16 | 🟢 OVERSOLD VALUE |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $624.4B | $150.63 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $370.4B | $185.97 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $143.6B | $117.87 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $71.4B | $134.13 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $83.2B | $55.64 | Olivier Le Peuch | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $233.1B | $503.87 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $76.8B | $311.58 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $94.9B | $66.03 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $67.6B | $303.60 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $70.8B | $251.70 | Christophe Beck | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.33T | $294.80 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.03T | $407.77 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.37T | $220.78 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.99T | $419.30 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $537.2B | $186.79 | Michael D. Sicilia | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $310.8B | $297.45 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $420.2B | $912.14 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $240.9B | $178.89 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $138.5B | $218.54 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $157.7B | $265.60 | Vincenzo James Vena | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $932.2B | $989.87 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $360.0B | $396.39 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $539.8B | $224.26 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $367.4B | $207.94 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $277.5B | $112.37 | Robert Davis | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.05T | $485.16 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $816.9B | $304.88 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $360.4B | $50.78 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $230.1B | $75.18 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $279.0B | $945.90 | David Solomon | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $134.0B | $143.76 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $83.3B | $178.82 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $106.6B | $1080.63 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $153.5B | $217.50 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $39.9B | $91.50 | Christian H. Hillabra… | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.86T | $265.82 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.63T | $433.45 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $309.2B | $310.46 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $195.3B | $274.84 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $62.6B | $42.35 | Elliott J. Hill | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $335.1B | $143.91 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $453.4B | $1021.88 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $344.3B | $80.03 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $207.6B | $151.85 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $1.04T | $130.35 | John R. Furner | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.68T | $387.35 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.53T | $603.00 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $369.1B | $87.66 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $184.3B | $106.16 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $209.2B | $193.30 | Srinivasan Gopalan | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $197.3B | $94.59 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $105.4B | $93.47 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $97.5B | $125.07 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $71.8B | $131.94 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $61.1B | $93.41 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.62)

> **防禦定調:Breadth 33 + Distribution Days 4 抵消 FTD 多頭訊號**
> 
> Overheating + Breadth Weakening + Distribution Days 4 + signal_conflict → 強迫 Energy 由 HOT 降 WARM,僅 Energy/Materials 為 WARM,曝險上限 40-60%,以防禦為主、不追高。

### Key Takeaways
1. 因 signal_conflict(Breadth 50% vs FTD 87.5%)強迫降風險,曝險封頂 40-60%。
2. 僅 Energy / Materials 為 WARM,但兩者皆有 DA HIGH 挑戰(Energy 估值過熱、Materials 敘事 vs 價格背離),不可重押。
3. Technology 雖 RS3M +16% 領漲,但 FRED Overheating avoid + Shiller 泡沫警示 + 內部人賣超,屬 narrow leadership 反轉風險。
4. 防禦類 Utilities / Consumer_Staples / Real_Estate / Communication 在 RISK_ON 但 breadth 已弱的環境下並無 bid,屬 AVOID 區。
5. 未來 2 週監看 Energy 5d RS、Tech distribution day 是否升到 6+、Trump-Xi 關稅實際協議內容。

### Sector Actions
- **Wait**: Energy (high) — 估值 +2.51σ + 短期 RS 崩塌,等回落 +2σ 以下
- **Wait**: Materials (high) — 敘事熱但 RS 三窗全負,等 RS20d 轉正
- **Neutral**: Industrials (med) — 4 bullish 主題收斂但 breadth 仍弱
- **Underweight**: Technology (med) — FRED avoid + 內部人賣超 + 窄頭領導
- **Avoid**: Real_Estate (high) — FRED avoid + 實質利率 1.95% 壓力
- **Avoid**: Utilities (high) — RS20d -9% 最差,defensive bid 失靈

### Watch Next
- Energy XLE 5d/20d RS 是否回穩(目前 -5.15% / -3.40%)— 跌破 20d SMA 即確認 distribution top
- S&P 500 + NASDAQ distribution day 是否升至 6+(目前各 4)
- Trump-Xi 關稅協議實際範圍 — 影響 Consumer_Discretionary/Technology 短期
- Tech insider_ratio 是否跌破 0.5 bearish threshold(目前 0.524)
- Breadth composite score 是否跌破 30 進入 Critical zone

---

## Devil's Advocate Challenges (Accepted 2/3)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Energy — HOT | **Accepted** | 4-way consensus 看似最強(rotation 0.72 + theme 0.78 + news 0.78 + FRED 收藏),但價量背離:PE TTM 37.35 + pe_zscore_1y +2.51σ 處於 1-year overbought distribution zone;RS 從 3M +0.80% 衰退到 20d -3.40%、5d -5.15%,過去一週領漲動能急速崩塌 — 典型『新聞最熱、價格最弱』的 distribution top 訊號。insider_ratio 0.70(< 1.0)顯示內部人輕度賣超,s... |
| Materials — HOT | **Accepted** | 表面 4-way consensus 強(rotation 0.58 + theme 0.66 + news 0.68 + FRED 收藏),但 RS_vs_SPY 三窗全負 — 3M -8.11%、20d -6.05%、5d -0.81%,過去一季 Materials 都在 underperform SPY;Trump-Xi tariff + inflation-hedge 故事完全沒反映在相對價格上。pe_zscore +0.05 不貴但 insider_ratio 0.94 顯示內部人也無加碼,資金與內部人都用腳投票 — 比 Energy 更... |
| Technology — HOT | Rejected | Rotation/Theme 把 Tech 列為 HOT 直接違反 FRED Overheating(CPI accelerating, real rate 1.95%)對 Tech 的明確 avoid。Tech PE TTM 47.87 最貴,News 把 Tech 列為最強 COLD(Shiller bubble + worst smart-money + 3 stacked bearish vectors);insider_ratio 0.524 距 0.5 bearish threshold 只剩 0.024,senate -1。Theme... |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Energy | news_positive_price_negative | monitor | 新聞熱(Chevron 警告短缺、SLB/XOM +4%)但 5d RS -5.15%、20d RS -3.40% 雙負,屬 distribution top 風險 |
| Materials | news_positive_price_negative | monitor | 通膨對沖敘事 + Trump-Xi 關稅熱但 RS 三窗全負(3M -8%、20d -6%、5d -0.8%),典型敘事陷阱 |
| Technology | news_negative_price_positive | reduce_exposure | Shiller 泡沫 + Microsoft 走熊 + 內部人賣超但 RS3M +16% — 窄頭領導反轉風險 |

---

## Top Actionable Themes

1. AI & Semiconductors
2. Oil & Gas (Energy)
3. Basic Materials Concentration
4. Defense & Aerospace
5. Infrastructure & Construction

---

## HANDOFF TO INVESTMENT PROTOCOL

> DEFENSIVE 定調:signal_conflict 強迫 Energy 由 HOT 降 WARM,僅 Energy/Materials WARM 且皆帶 DA HIGH 挑戰。投資協議建議:wait Energy/Materials 至 RS 修復,Tech 因 FRED avoid + Shiller 警示走 underweight,Real_Estate/Utilities/Consumer_Staples AVOID。
