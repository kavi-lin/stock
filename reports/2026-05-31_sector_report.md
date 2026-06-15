# Sector Intelligence Report — 2026-05-31

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Mid · **Generated**: 2026-05-31 19:24
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|
| Technology | **HOT** | 85 | 全市場唯一正相對強度 (3M RS +27.4%) · 主題熱度 83.8 居冠 (AI/半導體/量子/機器人) | ROBUST | XLK | smart_money_divergence, fred_real_rate_divergence, overbought_valuation, crowded_consensus, late_stage_index |
| Industrials | WARM | 58 | 國防航太/太空主題熱度 64.2 · beat_rate 1.00 | ROBUST | — | — |
| Materials | WARM | 53 | uptrend_ratio 0.329 為非科技最高 · 主題集中度熱度 57.8 | N/A | — | — |
| Healthcare | WARM | 52 | FRED Transitional 防禦偏好 (×1.025) · 內部人買盤 1.31 | N/A | — | fred_favor_defensive |
| Consumer_Discretionary | COLD | 47 | 零售財報群催化但僅 News 單 lane 看多 · 內部人 0.71 淨賣 | N/A | — | single_lane_hot, insider_net_sell |
| Real_Estate | COLD | 46 | PE z -1.78 超賣 (+5 valuation) · 主題與動能皆墊底 | N/A | — | oversold_value |
| Communication | COLD | 44 | PE z -1.89 最便宜 (+5 valuation) · 無近期催化 | N/A | — | oversold_value, no_catalyst |
| Financials | COLD | 42 | FRED 因 real_rate 偏好但 Theme 評最冷 · 內部人買盤 1.34 為亮點 | N/A | — | lane_conflict |
| Utilities | COLD | 42 | 內部人買盤 3.26 全板塊最高 · uptrend 0.138 動能弱 | N/A | — | — |
| Consumer_Staples | COLD | 42 | uptrend 0.103 資金外流嚴重 · PE z -1.16 超賣 (+5) | N/A | — | oversold_value, fred_favor_defensive, capitulation_outflow |
| Energy | COLD | 41 | uptrend 0.084 全市場最弱 · PE z +1.49 貴卻弱 | N/A | — | expensive_weak, lane_conflict |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 60-75% | Synthesized: 60-75% | Cycle: Mid
FTD: FTD_CONFIRMED (quality 100) | Market Top: 23.2 Yellow (Early Warning) | Breadth: 42.4 Neutral
Sentiment: F&G [71.7 — Greed] | VIX: 15.32 | Put/Call: n/a | SPY RSI: 68.8
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & 半導體 · 量子運算 · 機器人自動化

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 53.13 | +1.78 | +27.4% | 1.249 |  |
| Industrials | 40.63 | +0.45 | -12.5% | 0.884 |  |
| Materials | 27.29 | -0.20 | -14.5% | 1.091 |  |
| Healthcare | 29.45 | -0.68 | -17.0% | 1.363 |  |
| Consumer_Discretionary | 57.38 | -0.10 | -6.9% | 0.869 |  |
| Real_Estate | 49.28 | -1.78 | -9.9% | 1.369 | 🟢 OVERSOLD VALUE |
| Communication | 22.6 | -1.89 | -12.3% | 1.108 | 🟢 OVERSOLD VALUE |
| Financials | 21.54 | -0.57 | -10.0% | 0.976 |  |
| Utilities | 27.76 | -0.08 | -17.2% | 1.11 |  |
| Energy | 35.87 | +1.49 | -9.6% | 0.828 |  |
| Consumer_Staples | 30.49 | -1.16 | -18.2% | 1.143 | 🟢 OVERSOLD VALUE |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.58T | $312.06 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.34T | $450.24 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.11T | $211.14 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $2.12T | $446.77 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $649.4B | $225.81 | Michael D. Sicilia | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $338.3B | $323.76 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $403.5B | $875.87 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $241.9B | $179.66 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $150.7B | $237.86 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $155.9B | $262.64 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $230.2B | $497.69 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $74.9B | $303.84 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $94.5B | $65.71 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $62.0B | $278.62 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $72.0B | $256.00 | Christophe Beck | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.04T | $1105.44 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $345.4B | $380.31 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $542.4B | $225.33 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $384.4B | $217.58 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $293.2B | $118.72 | Robert Davis | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.91T | $270.64 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.64T | $435.79 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $315.9B | $317.14 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $198.4B | $279.20 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $68.3B | $46.23 | Elliott J. Hill | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $133.8B | $143.52 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $87.1B | $186.96 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $105.3B | $1068.04 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $144.9B | $205.33 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $39.9B | $91.50 | Christian H. Hillabra… | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.60T | $380.34 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.61T | $632.51 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $362.2B | $86.02 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $176.8B | $101.84 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $202.9B | $187.53 | Srinivasan Gopalan | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.02T | $474.47 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $802.0B | $299.31 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $366.2B | $51.60 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $237.3B | $77.54 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $302.5B | $1025.56 | David Solomon | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $181.4B | $87.01 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $103.8B | $92.05 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $95.7B | $122.73 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $68.9B | $126.67 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $58.3B | $89.11 | Jeffrey Walker Martin | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $602.4B | $145.33 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $363.4B | $182.46 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $138.9B | $113.98 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $71.0B | $133.38 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $81.6B | $54.55 | Olivier Le Peuch | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $334.3B | $143.57 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $424.3B | $956.32 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $339.9B | $79.01 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $197.1B | $144.19 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $922.6B | $115.75 | John R. Furner | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.62)

> **窄幅領漲：僅科技值得加碼，其餘謹慎選股**
> 
> 今天把新增曝險集中在科技龍頭，不要為了分散而追落後板塊；breadth 僅 42、全市場只有科技相對大盤轉強，內部人卻在賣。等 AVGO 財報與週五非農確認方向，再決定要不要擴大佈局。

### Key Takeaways
1. 認清今日 DEFENSIVE 主因：breadth 42、僅科技正相對強度，市場極度集中
2. 加碼僅限科技龍頭，並用移動停損控管 PE z+1.78 與 RSI 68.8 過熱風險
3. 避開能源（貴又弱，uptrend 0.084）與必需消費（資金外流，uptrend 0.103）
4. 緊盯科技內部人淨賣（insider 0.49）與 real rate 2.08 對長久期估值的壓力
5. 工業／原物料／醫療僅選股觀察，不做整體加碼

### Sector Actions
- **Overweight**: Technology (high) — 唯一正相對強度，AI 催化密集
- **Wait**: Healthcare (low) — FRED 防禦偏好但動能弱
- **Neutral**: Industrials (med) — 主題熱但相對大盤仍落後
- **Underweight**: Energy (med) — 貴又弱，價格未確認
- **Avoid**: Consumer_Staples (med) — 資金外流，動能最弱
- **Avoid**: Real_Estate (low) — 估值便宜但缺催化

### Watch Next
- AVGO 6/3 財報 — AI／半導體需求風向標
- NFP 非農 6/5 — 勞動市場降溫是否失速
- ISM 製造業 6/1 ／ 服務業 6/3 PMI 擴張收縮分界
- 科技 breadth 能否擴散（uptrend 0.366 是否帶動其他板塊）
- real rate 是否守住 2.0 上方、Market-Top 由黃轉紅與否

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | — | — |  |
| Technology | — | — |  |
| Energy | — | — |  |
| Financials | — | — |  |

---

## Top Actionable Themes

1. AI & 半導體
2. 量子運算
3. 機器人自動化
4. 國防航太
5. 太空經濟

---

## HANDOFF TO INVESTMENT PROTOCOL

> Sunday pre-market scan (2026-05-31) using last-trading-day (Fri 2026-05-29) FMP data; legacy econ/earnings-calendar endpoints 403, earnings sourced via FMP MCP. FTD CONFIRMED (quality 100) but breadth 42.4 Neutral + Market-Top Yellow + only Technology with positive RS → DEFENSIVE despite Greed. Step6 Transitional regime near-neutral (Healthcare/Staples ×1.025 only).
