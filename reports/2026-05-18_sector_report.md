# Sector Intelligence Report — 2026-05-18

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-05-18 22:04
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Energy | WARM | 66 | 1.00 | 唯一全週期 INFLOW：RS 5d +3.2%／20d +2.8%／3M +1.5% 皆正 · uptrend-ratio 0.602 rank-1、FRED favor 名單 | N/A | XLE | overbought, late_cycle |
| Technology | WARM | 52 | 0.89 | AI & 半導體 heat 58.6、量子 57.4 雙 Trending 主題 · 3M RS vs SPY +18.1% 為全場最強資金流入 | N/A | XLK | late_cycle, momentum_divergence_5d |
| Industrials | COLD | 42 | 0.96 | Industrials Concentration 57.1、Defense 56.4 主題熱度居前 · 資金 OUTFLOW、3M RS vs SPY −10.9% | N/A | XLI | late_cycle |
| Communication | COLD | 41 | 0.96 | 估值便宜 pe z-score −2.10（觸發 +5 oversold overlay） · Meta「賣壓被誤讀」、Netflix 目標價偏多 | N/A | XLC | late_cycle |
| Materials | COLD | 35 | 1.00 | Basic Materials Concentration 主題 + FRED favor · RS 全週期為負（5d −3.9%／20d −8.2%／3M −13.0%） | N/A | XLB | late_cycle |
| Real_Estate | COLD | 33 | 0.93 | 估值便宜 pe z-score −1.76（觸發 +5 oversold overlay） · 資料中心 REIT 高信度題材、REIT 重定價週期接近轉折 | N/A | XLRE | — |
| Utilities | COLD | 31 | 1.00 | NextEra 擬約 670 億美元收購 Dominion 大型 M&A 催化 · rank-11 uptrend 0.062 oversold、RS 3M −13.3% 全週期最弱 | N/A | XLU | — |
| Financials | COLD | 31 | 1.00 | FRED favor（過熱 regime 利好銀行 NIM）但價格未驗證 · Financial Services & Banks 為空頭主題 heat 40.3 | N/A | XLF | late_cycle |
| Consumer_Staples | COLD | 29 | 1.00 | 防禦未獲青睞 — Consumer Defensive Concentration 為空頭主題 · uptrend 0.149 偏弱、3M RS −11.7% | N/A | XLP | — |
| Healthcare | COLD | 28 | 1.00 | 多頭主題近乎熄火（Healthcare & Pharma heat 僅 11.7） · 巴菲特 Berkshire 出清 UNH 持股、UNH 走弱 | N/A | XLV | — |
| Consumer_Discretionary | **AVOID** | 19 | 0.89 | 零售龍頭財報週（HD 5/19、TGT/LOW 5/20）binary 風險 ×0.70 · FRED 過熱 regime 列為避開、uptrend 0.105 倒數第三 | N/A | XLY | binary_risk_within_48h, late_cycle |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 40-60% | Synthesized: 40-60% | Cycle: Late
FTD: FTD_CONFIRMED (quality 100) | Market Top: 31.9 Yellow (Early Warning) | Breadth: 32.4 Weakening
Sentiment: F&G [68.0 — Greed] | VIX: 18.52 | Put/Call: n/a | SPY RSI: 72.8
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Space Economy · AI & Semiconductors · Oil & Gas (Energy)

---

## Step 6 — FRED Regime Overlay

- **Regime**: Overheating (confidence 0.74)
- **Favor**: —
- **Avoid**: —
- **Velocity highlights**: DGS10:accelerating, DFF:decelerating, CPIAUCSL:accelerating
- **Rationale**: Overheating regime, conf 0.74 → favor: Energy×0.998, Materials×0.998, Financials×0.998; avoid: Technology×0.893, Consumer_Discretionary×0.893, Real_Estate×0.926

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 49.1 | +0.98 | +18.1% | 0.097 |  |
| Energy | 38.29 | +2.31 | +1.5% | 0.124 |  |
| Industrials | 39.33 | +0.19 | -10.9% | 0.053 |  |
| Communication | 22.73 | -2.10 | -6.2% | 0.065 | 🟢 OVERSOLD VALUE |
| Materials | 26.71 | -0.29 | -13.0% | 0.091 |  |
| Real_Estate | 49.82 | -1.76 | -9.3% | 0.131 | 🟢 OVERSOLD VALUE |
| Utilities | 25.93 | -0.63 | -13.3% | 0.194 |  |
| Financials | 22.0 | -0.41 | -10.0% | 0.066 |  |
| Consumer_Staples | 33.12 | +0.20 | -11.7% | 0.066 |  |
| Healthcare | 28.31 | -0.89 | -16.3% | 0.074 |  |
| Consumer_Discretionary | 55.88 | -0.32 | -7.7% | 0.057 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.41T | $300.23 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.13T | $421.92 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.48T | $225.32 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $2.01T | $425.19 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $555.0B | $192.98 | Michael D. Sicilia | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $654.6B | $157.93 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $380.5B | $191.06 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $149.1B | $122.41 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $74.7B | $140.26 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $82.8B | $55.38 | Olivier Le Peuch | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $294.2B | $281.53 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $409.2B | $888.31 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $230.5B | $171.18 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $135.1B | $213.24 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $160.6B | $270.56 | Vincenzo James Vena | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.80T | $396.78 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.56T | $614.23 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $366.4B | $87.02 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $178.4B | $102.72 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $200.4B | $185.22 | Srinivasan Gopalan | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $234.1B | $506.11 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $74.0B | $300.10 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $90.6B | $63.01 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $65.8B | $295.38 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $69.7B | $247.62 | Christophe Beck | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $131.0B | $140.53 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $79.5B | $170.63 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $104.5B | $1059.44 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $150.9B | $213.74 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $37.8B | $86.66 | Christian H. Hillabra… | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $194.7B | $93.36 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $104.3B | $92.55 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $94.3B | $120.95 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $68.1B | $125.15 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $59.1B | $90.43 | Jeffrey Walker Martin | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.04T | $482.70 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $798.0B | $297.81 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $353.2B | $49.77 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $224.7B | $73.42 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $279.8B | $948.47 | David Solomon | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $329.7B | $141.57 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $465.4B | $1048.95 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $347.7B | $80.82 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $203.8B | $149.12 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $1.05T | $131.45 | John R. Furner | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $946.4B | $1004.92 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $357.7B | $393.85 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $545.7B | $226.71 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $371.7B | $210.39 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $275.1B | $111.38 | Robert Davis | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.84T | $264.14 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.59T | $422.24 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $296.3B | $297.51 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $196.4B | $276.39 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $61.9B | $41.88 | Elliott J. Hill | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.8)

> **防禦為先：廣度惡化、配銷沉重，無產業達 HOT**
> 
> 11 產業全數下降趨勢、0 上升，廣度複合分 32.4、配銷日 90/100；僅 Energy、Technology 勉強 WARM，曝險守 40-60% 下緣、停止新增動能進場。

### Key Takeaways
1. 守住整體曝險於 40-60% 下緣 — 廣度複合分僅 32.4、危險空頭背離（S&P +9.6% vs 廣度 8MA −0.119/60d）
2. 停止新增任何動能進場 — 11 產業全數下降趨勢、0 上升，FTD 75-100% 訊號因廣度背離打 5 折
3. 觀望輝達 NVDA 5/20 盤後財報 — 本週 AI 半導體方向關鍵 binary
4. 規避非必需消費 — 零售龍頭財報週疊加需求警訊，Consumer_Discretionary 降為 AVOID
5. 提防 FRED 過熱 regime 對科技逆風 — CPI 與 10Y 殖利率同步加速、實質利率 1.99%

### Sector Actions
- **Wait**: Energy (med) — 唯一全週期 INFLOW 但估值 z+2.31 過熱
- **Wait**: Technology (low) — FRED 過熱列避開、5d RS 轉負
- **Neutral**: Utilities (low) — M&A 催化但全週期 RS 最弱
- **Underweight**: Industrials (med) — 主題熱但資金 OUTFLOW、RS −10.9%
- **Avoid**: Consumer_Discretionary (high) — 零售財報 binary＋需求警訊
- **Avoid**: Healthcare (med) — 多頭主題熄火＋巴菲特清倉 UNH

### Watch Next
- 零售龍頭財報 HD 5/19、TGT/LOW 5/20：消費需求即時讀數（within_48h binary）
- 輝達 NVDA 5/20 盤後財報：AI 資本支出與半導體景氣 binary
- FOMC 4月會議紀要 5/20：利率路徑與通膨語氣
- S&P／NASDAQ 配銷日計數：再添 2 日即確認機構賣壓叢集
- 廣度 8MA 能否站回 0.60，或續跌向 0.40 極弱區

---

## Devil's Advocate Challenges (Accepted 0/2)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Energy — HOT | — | Energy 標 Overbought（uptr 0.602）卻 3M RS 僅 +1.5% — 高參與、相對表現近零，是擁擠但停滯交易的特徵，而非領頭羊。Oil&Gas 主題為 Mature（晚期），內部人比率 0.915 低於 1.0（輕微淨賣）、議員淨買 0，commodity 群 uptrend 39.9% 正是廣度（複合 32.4、Weakening、0/11 上升）一旦轉弱即劇烈回歸的晚周期讀數。3-of-4 lane 提 HOT 是把 reflation 敘事追進 Overbought、Mature、內部人賣超的盤面。 |
| Technology — HOT | — | Technology 內部分歧（2 lane HOT、2 lane COLD），空方催化更硬：NVDA 5/20 盤後 binary 在「年初以來最弱科技訊號」中先行交易 — 任何 HOT 在最大市場推動數據解析前就建倉。RS5d 已 −0.9% 卻 RS3m +18.1%：5d 對 3M 背離是動能率先轉折的早期裂痕。內部人比率 0.507 僅略高於 0.5 賣超閾值、議員淨買 0，FRED 過熱 + 10Y 上行直接壓縮長存續期 Tech DCF，SPY RSI 72.8 / Greed 68 對失誤無緩衝。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Energy | news_positive_price_negative | monitor | 新聞偏多（Alaska LNG 供應協議）且 uptrend rank-1，但 3M RS vs SPY 僅 +1.5%，價格未充分驗證題材熱度。 |
| Technology | momentum_short_term_crack | monitor | 3M RS vs SPY +18.1% 強勢，但 5d RS −0.9%、20d +9.7% 已減速，短週期動能率先轉折，疊加 NVDA binary。 |
| Industrials | news_positive_price_negative | monitor | 主題熱度居前（Concentration 57.1、Defense 56.4）但資金 OUTFLOW、3M RS −10.9%，題材與價格背離。 |

---

## Top Actionable Themes

1. Space Economy
2. AI & Semiconductors
3. Oil & Gas (Energy)
4. Defense & Aerospace

---

## HANDOFF TO INVESTMENT PROTOCOL

> 防禦環境：廣度 32.4（Weakening）、配銷日 90/100、11 產業全數下降趨勢、0 上升。stance DEFENSIVE、曝險守 40-60% 下緣。三訊號衝突（FTD 75-100% vs Breadth 40-60%，37.5pp）→ FTD 積極訊號因廣度背離打 5 折，stance 上限封頂 NEUTRAL，實際落於 DEFENSIVE。investment_protocol 對新進場應從嚴。唯一全週期 INFLOW 為 Energy 但估值過熱（pe z+2.31）；Technology 受 FRED 過熱 regime 逆風、5d RS 已轉負。NVDA 5/20 盤後財報為本週 AI 方向關鍵 binary。經濟與財報日曆 FMP legacy endpoint 403，upcoming_events 以 WebSearch 驗證之 NVDA 日期與當週既知事件補位。
