# Sector Intelligence Report — 2026-05-16

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.68
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-05-16 12:15
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Energy | WARM | 65.57 | 1.00 | 唯一 RS 全週期領先 SPY · Oil & Gas 主題 heat 58.2 | N/A | XLE | overbought, late_cycle |
| Technology | WARM | 54.7 | 0.89 | AI/太空/量子主題群 heat 領先 · 3M RS +17.9% 但 5d 趨平 | N/A | XLK | late_cycle, consensus_crowding |
| Industrials | COLD | 35.26 | 0.96 | RS 3M -10%、資金流出 · uptrend 0.255 下行 | N/A | XLI | late_cycle |
| Communication | COLD | 32.37 | 0.96 | PE z-score -2.14 估值極低 · 無資金回補、RS 落後 | N/A | XLC | — |
| Utilities | COLD | 27.9 | 1.00 | uptrend 0.062 全場最低 · NextEra-Dominion 併購題材 | N/A | XLU | — |
| Real_Estate | COLD | 26.58 | 0.92 | PE z-score -1.68 偏低 · 實質利率 2% 壓制估值 | N/A | XLRE | — |
| Financials | COLD | 25.9 | 1.00 | FRED 偏好但廣度極弱 · uptrend 0.104、RS 流出 | N/A | XLF | late_cycle |
| Materials | COLD | 25.4 | 1.00 | RS 3M -14%、斜率最陡 · Freeport Grasberg 干擾 | N/A | XLB | late_cycle |
| Healthcare | **AVOID** | 24.65 | 1.00 | RS 3M -16.4% 全場最弱 · GLP-1/生技/製藥主題全空 | N/A | XLV | — |
| Consumer_Staples | **AVOID** | 23.65 | 1.00 | 防禦股未獲避險買盤 · uptrend 0.149、RS -13.9% | N/A | XLP | — |
| Consumer_Discretionary | **AVOID** | 19.67 | 0.89 | uptrend 0.105、全面流出 · Amazon 關稅訴訟壓力 | N/A | XLY | late_cycle |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 40-60% | Synthesized: 40-60% | Cycle: Late
FTD: FTD_CONFIRMED (quality 100) | Market Top: 31.9 Early_Warning | Breadth: 32.4 Weakening
Sentiment: F&G [67.4 — Greed] | VIX: 18.43 | Put/Call: n/a | SPY RSI: 69.6
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Space Economy · AI & Semiconductors · Oil & Gas (Energy)

---

## Step 6 — FRED Regime Overlay

- **Regime**: Overheating (confidence 0.77)
- **Favor**: —
- **Avoid**: —
- **Velocity highlights**: DGS10:accelerating, DFF:decelerating, CPIAUCSL:accelerating
- **Rationale**: Overheating regime, conf 0.77 → favor: Energy×0.998, Materials×0.998, Financials×0.998; avoid: Technology×0.888, Real_Estate×0.923, Consumer_Discretionary×0.888

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Energy | 37.36 | +2.27 | +0.9% | 0.856 |  |
| Technology | 48.39 | +0.84 | +17.9% | 1.348 |  |
| Industrials | 39.54 | +0.24 | -10.0% | 0.93 |  |
| Communication | 22.7 | -2.14 | -7.1% | 0.946 | 🟢 OVERSOLD VALUE |
| Healthcare | 28.32 | -0.89 | -16.4% | 0.966 |  |
| Materials | 27.96 | -0.08 | -14.1% | 1.118 |  |
| Consumer_Staples | 32.52 | -0.12 | -13.9% | 1.087 |  |
| Real_Estate | 50.02 | -1.68 | -9.0% | 0.938 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 56.98 | -0.25 | -8.1% | 1.382 |  |
| Financials | 22.02 | -0.40 | -9.5% | 0.877 |  |
| Utilities | 26.79 | -0.39 | -14.1% | 1.094 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $654.6B | $157.93 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $380.5B | $191.06 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $149.1B | $122.41 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $74.7B | $140.26 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $82.8B | $55.38 | Olivier Le Peuch | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.41T | $300.23 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.13T | $421.92 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.48T | $225.32 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $2.01T | $425.19 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $555.0B | $192.98 | Michael D. Sicilia | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $304.6B | $291.54 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $423.9B | $920.22 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $236.6B | $175.68 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $138.0B | $217.72 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $159.9B | $269.34 | Vincenzo James Vena | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.85T | $401.07 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.57T | $618.43 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $366.1B | $86.94 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $183.1B | $105.45 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $203.7B | $188.19 | Srinivasan Gopalan | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $199.5B | $95.68 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $105.6B | $93.68 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $96.9B | $124.31 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $70.0B | $128.60 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $60.7B | $92.86 | Jeffrey Walker Martin | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $133.0B | $142.66 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $79.4B | $170.50 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $106.5B | $1079.68 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $153.7B | $217.75 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $38.1B | $87.31 | Christian H. Hillabra… | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.04T | $482.70 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $798.0B | $297.81 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $353.2B | $49.77 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $224.7B | $73.42 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $279.8B | $948.47 | David Solomon | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $236.7B | $511.65 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $76.3B | $309.18 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $95.1B | $66.14 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $66.8B | $299.87 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $70.0B | $248.88 | Christophe Beck | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $946.4B | $1004.92 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $357.7B | $393.85 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $545.7B | $226.71 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $371.7B | $210.39 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $275.1B | $111.38 | Robert Davis | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $329.7B | $141.57 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $465.4B | $1048.95 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $347.7B | $80.82 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $203.2B | $148.67 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $1.06T | $132.46 | John R. Furner | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.84T | $264.14 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.59T | $422.24 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $296.3B | $297.51 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $196.4B | $276.39 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $61.9B | $41.88 | Elliott J. Hill | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.68)

> **防禦為先：指數新高掩蓋廣度崩壞，無板塊夠格 HOT**
> 
> 僅 21% 個股處上升趨勢、breadth 32.4 Weakening，資金擠在 Energy 與 Technology 兩處；曝險上限 40-60%，本週宜守不宜攻。

### Key Takeaways
1. 降低曝險至 40-60%：6 個板塊 COLD、廣度危險背離，stance 定為 DEFENSIVE
2. 勿追 Energy 與 Technology：唯二 WARM 但 Energy pe_zscore 2.27 過熱、Tech 5d 動能趨平
3. 停看 Healthcare/Consumer_Staples/Consumer_Discretionary：三個 AVOID，不新建倉
4. 監控 10 年期殖利率：DGS10 加速 + CPI 加速，對高估值板塊持續逆風
5. 等待廣度轉強訊號再加碼：breadth 跌破 30 則進一步減碼

### Sector Actions
- **Wait**: Energy (med) — 唯一 RS 領先，但 pe_zscore 2.27 過熱追高
- **Wait**: Technology (med) — 主題強但動能趨平、FRED 逆風
- **Neutral**: Financials (low) — FRED 偏好但廣度極弱、資金流出
- **Avoid**: Healthcare (high) — RS 全場最弱、主題全面看空
- **Avoid**: Consumer_Discretionary (high) — 全面流出 + 關稅訴訟壓力
- **Avoid**: Consumer_Staples (med) — 防禦股未獲避險買盤

### Watch Next
- 10 年期公債殖利率：加速上行則高估值板塊續壓
- 市場廣度 breadth_score：跌破 30 為進一步減碼訊號
- 5/21 初領失業金 + 費城聯儲製造業
- 5/22 密大消費者信心終值與通膨預期
- 零售股財報週：檢驗關稅成本轉嫁與消費韌性

---

## Devil's Advocate Challenges (Accepted 2/3)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Technology — HOT | **Accepted** | Technology 為典型擁擠共識陷阱：Rotation/Theme/News 三方同標 HOT，FRED 卻明確標 COLD — Overheating regime（conf 0.77）配 1.99% 實質利率、CPI 與 10Y 同步加速，對 48.4 倍 PE 結構性不利。動能已轉折：rs_5d 崩至 +0.2% vs rs_20d +10.1%，insider ratio 0.507 僅高於 0.5 門檻、議員淨賣 -1，疊加 60 日危險背離（SPY +9.6% vs 廣度 8MA -0.119、僅 21% 個股上升趨勢）。 |
| Energy — HOT | **Accepted** | Energy 被標 HOT 主要靠動能與 Overheating 實物資產敘事，但統計上已過度延展：pe_zscore_1y 2.27、超買逾 2 個標準差，遠比 Tech 的 0.84 極端。rs 型態（5d +6.5% > 20d +3.9%）為末段加速衝刺，正是均值回歸最劇的型態，Late cycle、RISK_ON 狹窄領導下追高風險高。 |
| ALL — HOT | — | 更深層挑戰是本週期是否有任何板塊配得上 HOT：Phase 4b 發現無板塊 composite>75、三訊號曝險上限僅 40-60% 且 signal_conflict 啟動（FTD 75-100% vs 廣度 40-60%、37.5pp 落差），宏觀為 Late cycle RISK_ON 加危險狹窄領導 — 僅 21% 個股上升趨勢、breadth_score 32.4 Weakening。指數新高由少數權值股製造，平均個股仍在下行。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | news_positive_price_negative | monitor | 新聞情緒看多（Trump-Xi 晶片談判），但 5d RS 趨平至 +0.2%、廣度狹窄、FRED 標 COLD。 |
| Utilities | news_positive_price_negative | monitor | NextEra-Dominion 4000 億併購題材偏多，但 uptrend 0.062 全場最低、RS 3M -14%。 |

---

## Top Actionable Themes

1. Space Economy
2. AI & Semiconductors
3. Oil & Gas (Energy)

---

## HANDOFF TO INVESTMENT PROTOCOL

> DEFENSIVE：指數新高但廣度崩壞（21% 個股上升趨勢、breadth 32.4），無板塊達 HOT；曝險上限 40-60%。選股僅在 Energy/Technology 兩個 WARM 板塊謹慎進行，且兩者皆有過熱/動能耗盡警訊，宜等回檔。Healthcare/Consumer_Staples/Consumer_Discretionary 不新建倉。
