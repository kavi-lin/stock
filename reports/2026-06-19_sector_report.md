# Sector Intelligence Report — 2026-06-19

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Mid · **Generated**: 2026-06-20 14:08
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|
| Technology | WARM | 71 | RS vs SPY 3M +25.1% 為唯一明確 INFLOW，AI & Semiconductors 題材 Trending（heat 64.6） · 但 PE z-score +1.85 最貴、insider 買賣比 0.45 賣超、廣度 uptrend 僅 0.284 → 窄幅領漲、不追高 | N/A | — | smart_money_divergence, overbought_valuation, narrow_leadership, real_rate_headwind |
| Industrials | WARM | 63 | 廣度最佳（uptrend 0.330）、估值便宜（PE z -1.42）、beat_rate 1.00；國防/太空/基建多題材撐盤 · 三大題材皆 Mature 生命週期、晚期耗盡風險；RS -2.9% 短線落後 | N/A | — | mature_theme_exhaustion, real_rate_headwind |
| Materials | WARM | 55 | Basic Materials Concentration 題材 Trending（heat 60.8）；銅為 AI 關鍵且短缺（FCX） · 估值中性（PE z -0.09）、RS -4.7% 偏弱、廣度 0.271 | N/A | — | — |
| Financials | WARM | 53 | 估值最便宜（PE z -1.05、PE TTM 20.3）；殖利率曲線 0.64 未倒掛、信用無壓力 · 僅 FRED lane 看多、Transitional 信心 0.49 接近五五波；6/24 Fed 壓力測試為變數 | N/A | — | single_lane_conviction, real_rate_headwind |
| Healthcare | COLD | 43 | 廣度尚可（0.310）+ AbbVie $11B 併購 Apogee；但 Healthcare & Pharma 題材轉空（Accelerating 33.8）、RS -11.3% | N/A | — | — |
| Consumer_Discretionary | COLD | 40 | beat_rate 1.00 但題材冷（Retail Accelerating 偏空 24.1）、RS -6.4% | N/A | — | — |
| Consumer_Staples | COLD | 37 | 估值便宜（PE z -1.18）獲超賣 +5；但廣度極弱 0.153、RS -11.6%、防禦題材轉空 | N/A | — | — |
| Real_Estate | COLD | 36 | 估值最便宜（PE z -1.73）獲超賣 +5；但 real_rate 2.17% 直接打壓長存續、RS -8.6%、題材轉空 | N/A | — | rate_sensitive |
| Communication | **AVOID** | 32 | 曝險上限 0-25%<40% 強制至少 3 個 AVOID，本板塊最弱列入；RS -16.4%、廣度 0.167、無題材撐 | N/A | — | exposure_floor_avoid |
| Utilities | **AVOID** | 21 | 廣度全場最差 0.037、RS -17.0%；real_rate 2.17% 對殖利率替代品最不利（雖 insider 3.31 防禦性買進） | N/A | — | rate_sensitive_outflow |
| Energy | **AVOID** | 19 | RS 全場最差 -22.6%、Exxon 因美伊協議重挫、Oil & Gas 題材轉空；廣度 0.061 接近清倉 | N/A | — | oil_bearish_iran_deal, outflow |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 60-75% | Synthesized: 0-25% | Cycle: Mid
FTD: FTD_WINDOW (quality 0) | Market Top: 34.2 Yellow (Early Warning) | Breadth: 53.0 Neutral
Sentiment: F&G [59.4 — Neutral] | VIX: 16.4 | Put/Call: n/a | SPY RSI: 55.1
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors（Trending, heat 64.6）— 科技唯一明確 INFLOW 動能但內部背離 · Defense & Aerospace / Space Economy（Mature, heat 63-72）— 工業撐盤但晚期 · Infrastructure & Construction + Basic Materials（銅 AI 短缺）— 工業/原物料交集

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 55.15 | +1.85 | +25.1% | 0.803 |  |
| Industrials | 29.8 | -1.42 | -2.9% | 0.951 |  |
| Materials | 27.62 | -0.09 | -4.7% | 0.926 |  |
| Financials | 20.27 | -1.05 | -3.8% | 0.967 | 🟢 OVERSOLD VALUE |
| Healthcare | 29.67 | -0.63 | -11.3% | 0.996 |  |
| Consumer_Discretionary | 54.73 | -0.34 | -6.4% | 1.122 |  |
| Consumer_Staples | 30.27 | -1.18 | -11.6% | 0.813 | 🟢 OVERSOLD VALUE |
| Real_Estate | 48.54 | -1.73 | -8.6% | 1.112 | 🟢 OVERSOLD VALUE |
| Communication | 22.28 | -1.70 | -16.4% | 1.856 | 🟢 OVERSOLD VALUE |
| Utilities | 25.88 | -0.84 | -17.0% | 1.851 |  |
| Energy | 34.34 | +0.93 | -22.6% | 0.991 |  |

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

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $236.9B | $512.15 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $79.1B | $320.79 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $98.7B | $68.67 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $62.4B | $280.21 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $75.7B | $269.12 | Christophe Beck | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.06T | $489.46 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $871.4B | $325.22 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $398.8B | $56.20 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $251.6B | $82.21 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $323.5B | $1096.56 | David Solomon | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.03T | $1098.13 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $364.1B | $400.96 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $549.8B | $228.39 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $382.7B | $216.63 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $281.2B | $113.87 | Robert Davis | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.63T | $244.39 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.50T | $400.49 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $333.3B | $334.28 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $198.0B | $278.61 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $66.8B | $45.20 | Elliott J. Hill | _TBD_ |

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

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.45T | $368.03 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.47T | $577.22 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $325.8B | $77.38 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $180.4B | $103.89 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $196.6B | $181.67 | Srinivasan Gopalan | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $180.9B | $86.75 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $104.9B | $93.09 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $96.6B | $123.86 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $69.5B | $127.69 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $59.3B | $90.69 | Jeffrey Walker Martin | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $571.2B | $137.81 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $345.8B | $173.63 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $131.3B | $107.74 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $69.2B | $129.98 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $71.9B | $48.09 | Olivier Le Peuch | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.62)

> **內部結構疲弱、三訊號衝突，防禦為主不追高**
> 
> 盤前先守不攻：VIX 16 看似平靜，但市場廣度全面疲弱、無 FTD 確認、分佈日數攀高，曝險上限壓到 0-25%；等 6/24 Micron 財報與 6/25 核心 PCE 通膨數據再決定是否加碼。

### Key Takeaways
1. 維持防禦：無任何產業達 HOT，曝險上限 0-25%，廣度（全產業 uptrend<0.34）與 FTD/分佈日訊號嚴重衝突
2. 科技動能最強卻內部背離：RS +25% 但 insider 賣超（比率 0.45）、估值最貴（PE z +1.85），逢強不追
3. 工業相對抗跌：廣度最佳 0.330、估值便宜（PE z -1.42）、beat_rate 1.00，但題材皆成熟、僅可選股不可重壓
4. 清倉級弱勢：能源（RS -22.6%、美伊協議壓油）、公用、通訊列 AVOID
5. 等 6/25 核心 PCE（YoY 估 4.0 升溫）確認通膨路徑、6/24 Micron 確認半導體風向前不擴張曝險

### Sector Actions
- **Wait**: Technology (med) — 動能強但背離、估值貴，逢回再選股
- **Wait**: Financials (low) — 估值便宜但僅單 lane、等壓力測試
- **Neutral**: Industrials (med) — 廣度與估值最佳、可選股、勿重壓
- **Neutral**: Materials (low) — 銅題材 Trending、RS 偏弱
- **Avoid**: Energy (high) — RS 全場最差、油價受美伊協議打壓
- **Avoid**: Utilities (high) — 廣度最差、real rate 壓殖利率替代

### Watch Next
- 6/24 Micron (MU) 財報 — 半導體/AI 記憶體需求風向
- 6/23 FedEx (FDX) 財報 — 運輸景氣、工業 read-through
- 6/25 核心 PCE MoM 0.3 / YoY 估 4.0（升溫）— Fed 偏好通膨指標
- 6/24 Fed 銀行壓力測試結果 — 金融板塊
- 是否出現 Follow-Through Day、分佈日數是否續增 — 決定能否升級曝險

---

## Top Actionable Themes

1. AI & Semiconductors（Trending, heat 64.6）— 科技唯一明確 INFLOW 動能但內部背離
2. Defense & Aerospace / Space Economy（Mature, heat 63-72）— 工業撐盤但晚期
3. Infrastructure & Construction + Basic Materials（銅 AI 短缺）— 工業/原物料交集
4. Oil & Gas 轉空（美伊協議）— 能源迴避

---

## HANDOFF TO INVESTMENT PROTOCOL

> 掃描於 2026-06-20（週六）執行，市場休市；valuation/smart_money/earnings 採 2026-06-19（週五收盤）最後交易日資料，Phase 0 廣度/FTD/Market-Top/FRED 為 06-20 當日 cache。週六 FMP sector-pe-snapshot 無資料屬正常（非 API 故障），已退回週五。三訊號衝突（Breadth 60-75% / FTD 0-25% / MktTop 80-90%，spread 72.5pp）+ 無 FTD + 曝險上限 0-25% → DEFENSIVE。無 HOT 板塊。
