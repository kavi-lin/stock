# Sector Intelligence Report — 2026-07-01

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-07-01 23:07
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|
| Industrials | WARM | 61 | 主題最強：太空/國防/基建 Trending · 資金 20d 淨流入（+7.3%）、參與度最高 | RESILIENT | XLI | late_cycle |
| Financials | WARM | 54 | Fed 壓測全過、雙位數股利調升 · FRED favor：實質利率 2.18% 擴大 NIM | RESILIENT | XLF | earnings_season_ahead |
| Technology | WARM | 53 | 主題最熱：AI/量子/機器人 83/79/76 · 但動能三窗翻負、內部人淨賣 | RESILIENT | XLK | macro_theme_divergence, momentum_exhaustion, insider_distribution, narrow_breadth |
| Healthcare | WARM | 53 | 參與度最高 0.475、資金 20d +10.7% · 估值便宜 z-1.69、防禦性資金接棒 | N/A | XLV | — |
| Real_Estate | WARM | 50 | 估值極度超賣 z-4.13（+5 價值 overlay） · 資料中心 REIT 主題熱 57.5 | N/A | XLRE | rate_sensitive, late_cycle |
| Materials | COLD | 45 | FRED favor 但參與度低 0.174 · 銅供給短缺+APD +8% 為亮點 | N/A | XLB | weak_participation |
| Consumer_Staples | COLD | 44 | 估值超賣 z-2.04（+5 價值 overlay） · 防禦股利敘事、但動能疲弱 | N/A | XLP | — |
| Communication | COLD | 42 | META +9% AI 算力變現撐盤 · 但漲勢單一名稱集中、RS 3M -15.1% | N/A | XLC | single_name_concentration |
| Consumer_Discretionary | **AVOID** | 35 | 估值最貴 PE 55、FRED 迴避 · Burry 放空 TSLA、零售主題最冷 | N/A | XLY | macro_theme_divergence, overvaluation, forced_avoid_low_exposure |
| Utilities | **AVOID** | 34 | 參與度全場最低 0.136、RS 3M -16.9% · AI 電力敘事（NextEra/SO）僅局部 | N/A | XLU | weak_participation, forced_avoid_low_exposure |
| Energy | **AVOID** | 28 | RS 3M -28.8% 全場最弱、確認下跌 · FRED favor 但淪價值陷阱 | N/A | XLE | value_trap, momentum_downtrend, forced_avoid_low_exposure |

---

## Macro Context

```text
Market Regime: SIDEWAYS | Breadth Ceiling: 60-75% | Synthesized: 0-25% | Cycle: Late
FTD: RALLY_ATTEMPT (quality 0) | Market Top: 42.2 Orange (Elevated Risk) | Breadth: 52.8 Neutral
Sentiment: F&G [58.1 — Neutral] | VIX: 16.32 | Put/Call: n/a | SPY RSI: 55.6
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors · Space Economy · Defense & Aerospace

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Industrials | 34.24 | -0.29 | -1.1% | 0.277 |  |
| Financials | 18.46 | -1.60 | -4.3% | 0.228 |  |
| Technology | 47.7 | +0.28 | +25.4% | 0.207 |  |
| Healthcare | 23.48 | -1.69 | -6.0% | 0.225 |  |
| Real_Estate | 28.24 | -4.13 | -6.5% | 0.354 | 🟢 OVERSOLD VALUE |
| Materials | 26.96 | -0.16 | -12.5% | 0.23 |  |
| Consumer_Staples | 28.44 | -2.04 | -13.5% | 0.259 | 🟢 OVERSOLD VALUE |
| Communication | 23.01 | -1.50 | -15.1% | 0.457 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 55.27 | -0.59 | -5.9% | 0.236 |  |
| Utilities | 27.9 | -0.30 | -16.9% | 0.278 |  |
| Energy | 18.04 | -0.65 | -28.8% | 0.229 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $387.4B | $370.75 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $491.2B | $1066.43 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $254.0B | $188.59 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $70.6B | $222.86 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $161.7B | $272.41 | Vincenzo James Vena | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.07T | $497.14 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $879.6B | $328.26 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $405.5B | $57.15 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $254.3B | $83.11 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $299.4B | $1014.84 | David Solomon | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.24T | $288.96 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $2.76T | $371.31 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $4.80T | $198.22 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.79T | $376.34 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $419.3B | $145.55 | Michael D. Sicilia | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.14T | $1208.35 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $378.2B | $416.46 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $615.3B | $255.62 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $447.2B | $253.13 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $316.6B | $128.18 | Robert Davis | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $126.3B | $135.47 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $76.2B | $163.57 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $102.8B | $1042.39 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $160.2B | $226.97 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $33.1B | $75.73 | Christian H. Hillabra… | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $241.6B | $522.26 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $84.5B | $342.73 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $90.2B | $62.72 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $65.8B | $295.62 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $78.5B | $279.02 | Christophe Beck | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $341.5B | $146.66 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $416.3B | $938.66 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $352.5B | $81.92 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $187.1B | $136.85 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $905.5B | $113.79 | John R. Furner | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.32T | $357.37 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.43T | $563.29 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $300.7B | $71.40 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $167.1B | $96.23 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $181.5B | $167.73 | Srinivasan Gopalan | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.58T | $239.72 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.56T | $416.54 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $351.1B | $352.08 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $192.1B | $270.35 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $61.3B | $41.45 | Elliott J. Hill | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $183.1B | $87.77 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $107.9B | $95.71 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $98.7B | $126.58 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $74.4B | $136.81 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $60.6B | $92.70 | Jeffrey Walker Martin | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $565.7B | $136.49 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $334.8B | $168.10 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $127.3B | $104.47 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $70.2B | $131.80 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $69.5B | $46.48 | Olivier Le Peuch | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.57)

> **防禦為主：反彈未確認、資金撤離科技**
> 
> 今天守成、暫緩新倉：大盤只是反彈嘗試、廣度中性且漲幅極度集中於少數科技股，明日 NFP 前不宜追高；等反彈站穩、NFP 落地後再考慮加碼工業與金融。

### Key Takeaways
1. 守住現金：三訊號取最保守曝險 0-25%，FTD 僅反彈嘗試、未確認
2. 減碼科技：3M 領先但 20d/5d 動能翻負、內部人淨賣（比 0.44）、實質利率 2.18% 壓長天期估值
3. 留意輪動接棒：資金 20d 淨流入工業、金融、醫療（價值與防禦）
4. 明日 NFP 為關鍵二元事件（估 11 萬 vs 前 17.2 萬），落地前控制曝險
5. 迴避能源/公用/非核心消費：動能最弱、低曝險環境強制降評

### Sector Actions
- **Wait**: Industrials (med) — 主題+資金雙撐，等反彈確認再進
- **Wait**: Financials (med) — 壓測過關+利差擴，NFP 後評估
- **Wait**: Healthcare (med) — 防禦資金流入、估值便宜
- **Wait**: Technology (low) — 動能耗盡+內部人賣，暫不追高
- **Avoid**: Energy (med) — 動能崩跌，宏觀偏好成價值陷阱
- **Avoid**: Consumer_Discretionary (med) — 估值最貴+FRED 迴避

### Watch Next
- 7/2 NFP（估 11 萬 vs 前 17.2 萬）+ 失業率 4.3%——二元、48h 內
- FTD 確認訊號：需 follow-through day 才升級曝險
- 科技 20d/5d RS 是否翻正（動能是否止跌）
- 7/6 ISM 服務業 PMI（估 51.5 vs 前 54.5）——景氣放緩確認
- 7/8 FOMC 會議紀要 + Warsh 升息辯論措辭

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | news_positive_price_negative | reduce_exposure | 主題熱度 83（AI 獨強）但 20d/5d RS 翻負、內部人淨賣（0.44）、實質利率壓估值——主題與價格/宏觀背離 |
| Energy | news_negative_price_positive | monitor | FRED 宏觀 favor（實質利率利多商品）但 RS 3M -28.8%、三方判 COLD——宏觀先驗滯後於價格，恐為價值陷阱 |

---

## Top Actionable Themes

1. AI & Semiconductors
2. Space Economy
3. Defense & Aerospace
4. Infrastructure & Construction

---

## HANDOFF TO INVESTMENT PROTOCOL

> 防禦環境：大盤僅反彈嘗試（FTD 未確認）、市寬中性且極度集中，三訊號取最保守 0-25% 曝險。無 HOT 板塊。輪動主軸為撤離科技（動能三窗翻負+內部人賣+實質利率壓估值）、資金接棒工業/金融/醫療。明日 NFP 為關鍵二元事件。個股層若做多優先落在工業(XLI)/金融(XLF)反彈確認後，科技追高需等 20d RS 翻正。
