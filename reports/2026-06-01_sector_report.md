# Sector Intelligence Report — 2026-06-01

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: NEUTRAL · **Cycle**: Mid · **Generated**: 2026-06-01 21:48
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|
| Technology | **HOT** | 80 | 全市場唯一正相對強度 (3M RS +27.7%)，uptrend 0.366 居冠 · 主題熱度 83.8 居冠 (量子/AI 半導體/太空/機器人) | ROBUST | XLK | overbought_valuation, crowded_consensus, narrow_breadth, insider_distribution_watch, late_stage_index |
| Industrials | WARM | 58 | 國防/機器人/太空主題熱 (57-72) · Honeywell Quantinuum $14.3B IPO 題材 | N/A | — | theme_price_divergence |
| Communication | WARM | 58 | PE z -1.86 最便宜 + uptrend 0.236 → oversold value +5 · Meta 估值折價轉溢價敘事 | N/A | — | oversold_value |
| Healthcare | WARM | 53 | insider acq/disp 1.31 淨買最積極 · FRED Transitional favor 防禦 +2.4% | N/A | — | — |
| Consumer_Staples | WARM | 53 | PE z -1.15 + uptrend 0.103 → oversold value +5 · FRED 防禦 favor +2.4% | N/A | — | oversold_value |
| Materials | WARM | 52 | uptrend 0.329 次高 · Basic Materials 主題熱 57.8 | N/A | — | — |
| Real_Estate | WARM | 51 | PE z -1.75 + uptrend 0.189 → oversold value +5 · Welltower +15% 股息調升 | N/A | — | oversold_value, rate_duration_headwind |
| Consumer_Discretionary | COLD | 49 | RS -6.6% 為落後群中最佳 · PE_TTM 57.4 全場最貴 | N/A | — | expensive_valuation |
| Energy | COLD | 46 | uptrend 0.084 墊底 · PE z +1.44 估值偏高 (與弱動能背離) | N/A | — | weak_participation, stretched_pe_z |
| Financials | COLD | 46 | PE_TTM 21.5 最便宜 · FRED 軟著陸利多 (僅 1 lane 看多) | N/A | — | macro_thesis_unconfirmed_by_price |
| Utilities | COLD | 46 | RS -17.4% 全場最弱 · insider acq/disp 3.26 異常淨買 (與價格背離) | N/A | — | weak_participation, rate_duration_headwind |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 60-75% | Synthesized: 60-75% | Cycle: Mid
FTD: FTD_CONFIRMED (quality 100) | Market Top: 23.2 Yellow (Early Warning) | Breadth: 42.4 Neutral
Sentiment: F&G [70.1 — Greed] | VIX: 16.05 | Put/Call: n/a | SPY RSI: 67.3
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Quantum Computing · AI & Semiconductors · Space Economy

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 53.15 | +1.77 | +27.7% | 0.03 |  |
| Industrials | 40.64 | +0.45 | -14.3% | 0.009 |  |
| Communication | 22.64 | -1.86 | -11.9% | 0.009 | 🟢 OVERSOLD VALUE |
| Healthcare | 29.46 | -0.67 | -16.3% | 0.008 |  |
| Materials | 27.23 | -0.20 | -15.0% | 0.02 |  |
| Consumer_Staples | 30.51 | -1.15 | -17.1% | 0.009 | 🟢 OVERSOLD VALUE |
| Real_Estate | 49.35 | -1.75 | -10.6% | 0.085 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 57.38 | -0.10 | -6.6% | 0.009 |  |
| Energy | 35.69 | +1.44 | -10.1% | 0.017 |  |
| Financials | 21.48 | -0.60 | -10.1% | 0.014 |  |
| Utilities | 27.78 | -0.08 | -17.4% | 0.023 |  |

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

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.60T | $380.34 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.61T | $632.51 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $362.2B | $86.02 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $176.8B | $101.84 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $202.9B | $187.53 | Srinivasan Gopalan | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.04T | $1105.44 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $345.4B | $380.31 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $542.4B | $225.33 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $384.4B | $217.58 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $293.2B | $118.72 | Robert Davis | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $230.2B | $497.69 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $74.9B | $303.84 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $94.5B | $65.71 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $62.0B | $278.62 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $72.0B | $256.00 | Christophe Beck | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $334.3B | $143.57 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $424.3B | $956.32 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $339.9B | $79.01 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $197.1B | $144.19 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $922.6B | $115.75 | John R. Furner | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $133.8B | $143.52 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $87.1B | $186.96 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $105.3B | $1068.04 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $144.9B | $205.33 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $39.9B | $91.50 | Christian H. Hillabra… | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.91T | $270.64 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.64T | $435.79 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $316.2B | $317.14 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $198.4B | $279.20 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $68.3B | $46.23 | Elliott J. Hill | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $602.4B | $145.33 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $363.4B | $182.46 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $138.9B | $113.98 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $71.0B | $133.38 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $81.6B | $54.55 | Olivier Le Peuch | _TBD_ |

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

---

## Today's Verdict — NEUTRAL (confidence 0.6)

> **中性偏選股：科技獨強、廣度偏窄，AVGO 財報定調**
> 
> 今天維持中性、曝險靠 60-75% 下緣選股；因為僅科技 (3M RS +27.7%) 一柱擎天、breadth 中性 42.4 而 Greed 偏高，要等 AVGO 6/3 與 NFP 6/5 才決定是否加碼或退場。

### Key Takeaways
1. 維持中性：FTD 已確認 (品質 100) 撐住底氣，但 breadth 42.4 中性 + 僅科技正 RS，領導過窄不宜全面進攻
2. 科技僅龍頭加碼：uptrend 0.366、PE z+1.77、insider 0.561 偏賣，靠權值股拉抬，曝險走 60-75% 下緣
3. 工業/金融的多頭只在題材與 macro，價格未認 (RS -14% / -10%)，先觀望不追
4. 防禦股 (醫療/必需消費/REIT) 估值轉 oversold，可留底倉但非主動買點
5. 盯緊 AVGO 6/3 與 NFP 6/5 — 兩者定調科技動能與利率路徑

### Sector Actions
- **Overweight**: Technology (med) — 唯一正 RS，但僅限龍頭且控過熱
- **Wait**: Industrials (med) — 題材熱但價格落後 14pp，等 RS 翻正
- **Neutral**: Healthcare (med) — insider 淨買 + 防禦 favor，留底倉
- **Neutral**: Communication (low) — 估值最便宜，逢低分批 META
- **Avoid**: Financials (med) — 僅 macro 看多，價格未確認
- **Avoid**: Utilities (med) — RS 全場最弱 + 利率逆風

### Watch Next
- AVGO 6/3 盤後財報 — AI/半導體需求風向標，定調科技動能延續或耗盡
- NFP 6/5 非農就業 — 牽動聯準會降息路徑與 real rate (現 2.08)
- 科技 uptrend 是否升破 0.40 — 領導廣度擴散 or 持續權值股獨撐
- 工業/金融 3M RS 是否翻正 — 題材/macro 多頭能否被價格確認
- Greed 70 是否升破 80 觸發極端情緒 + VIX 16 是否轉升

---

## Top Actionable Themes

1. Quantum Computing
2. AI & Semiconductors
3. Space Economy
4. Robotics & Automation
5. Defense & Aerospace

---

## HANDOFF TO INVESTMENT PROTOCOL

> STALE cache (前次 generated_at 2026-05-31 19:24，距今約 26h) → 完整重跑 Phase 0-1。Phase 0 四層 cache 皆 FRESH (~0.24h，今日 daily_update.sh)。Legacy FMP econ/earnings calendar endpoint 已停用 (403)，改用 MCP fmp calendar 取得財報行事曆。Phase 4a 四 lane 平行 (fred_available=true)，全 isolated → PARALLEL_SUBAGENT。DA 對 Technology(MEDIUM)/Industrials(HIGH)/Financials(HIGH) 提出挑戰並被採納 (工業/金融 HOT→降 WARM/COLD)。XLK 尾部 ROBUST 26.7 → 無 fragility 降級。
