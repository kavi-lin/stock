# Sector Intelligence Report — 2026-07-06

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-07-06 07:09
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|
| Technology | WARM | 58 | 主題最強：AI/半導體 62.9、機器人 63.1 Trending · 3M 相對強度 +21.6% 領先全場 | MODERATE | XLK | fat_tail_warning, smart_money_divergence, momentum_exhaustion, macro_theme_divergence, real_rate_pressure |
| Healthcare | WARM | 56 | 廣度最佳：uptrend 0.520（全場唯一參與度） · 估值偏低 PE z -1.56、20d RS 回升 +6.9% | ROBUST | XLV | theme_bearish_lifecycle |
| Communication | WARM | 53 | 晶片/AI 輪動新聞催化（新聞面最熱） · 估值偏低 PE z -1.48（oversold value +5） | MODERATE | XLC | fat_tail_warning, macro_theme_divergence |
| Industrials | COLD | 49 | 主題強：機器人/太空/國防/基建 Trending · 20d RS 回升 +6.7% 但 3M 仍 -0.6% | N/A | — | late_cycle |
| Financials | COLD | 48 | FRED Overheating 偏好（NIM 受惠實質利率） · 20d RS 回升 +7.9%、估值 PE z -1.38 偏低 | N/A | — | theme_bearish_lifecycle |
| Consumer_Staples | COLD | 44 | 估值深度偏低 PE z -1.64（oversold value +5） · 防禦屬性、20d RS 回升 +3.8% | N/A | — | — |
| Real_Estate | COLD | 44 | 估值全場最便宜 PE z -3.74 · 主題 Concentration 62.6 但 REIT 空頭主題並存 | N/A | — | macro_theme_divergence, real_rate_pressure |
| Consumer_Discretionary | COLD | 38 | FRED avoid（Overheating 消費裁量承壓） · 估值偏高 PE 51.1、3M RS -6.2% | N/A | — | macro_avoid_override |
| Materials | **AVOID** | 32 | 資金外流 3M RS -11.5%、新聞稀薄（2 篇） · 新聞明確警示『buy window has closed』 | N/A | — | exposure_floor_avoid, capital_outflow |
| Utilities | **AVOID** | 31 | 四方向（Rotation/Theme/News/FRED）全數看空 · 3M RS -15.7%、無承接買盤 | N/A | — | exposure_floor_avoid, capital_outflow, real_rate_pressure |
| Energy | **AVOID** | 20 | 全場最弱：3M RS -24.2%、uptrend 0.121 · 資金外流最重、清潔能源/EV 空頭主題壓制 | N/A | — | capital_outflow |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 60-75% | Synthesized: 0-25% | Cycle: Late
FTD: FTD_WINDOW (quality 0) | Market Top: 40.6 Orange (Elevated Risk) | Breadth: 54.8 Neutral
Sentiment: F&G [61.3 — Greed] | VIX: 16.42 | Put/Call: n/a | SPY RSI: 57.0
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI/半導體與機器人自動化 Trending（Technology/Industrials）但需底部確認再進 · 醫療保健防禦＋估值偏低（uptrend 0.520 全場最佳參與度） · 利率敏感長天期（REIT/Utilities）受實質利率 2.2% 壓制，回避

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 44.54 | -0.37 | +21.6% | 0.081 |  |
| Healthcare | 24.01 | -1.56 | -4.6% | 0.165 |  |
| Communication | 23.01 | -1.48 | -16.3% | 0.104 | 🟢 OVERSOLD VALUE |
| Industrials | 31.09 | -0.74 | -0.6% | 0.142 |  |
| Financials | 19.08 | -1.38 | -1.6% | 0.105 |  |
| Consumer_Staples | 29.16 | -1.64 | -11.3% | 0.172 | 🟢 OVERSOLD VALUE |
| Real_Estate | 28.23 | -3.74 | -7.4% | 0.143 |  |
| Consumer_Discretionary | 51.06 | -1.00 | -6.2% | 0.146 |  |
| Materials | 27.37 | -0.08 | -11.5% | 0.093 |  |
| Utilities | 27.53 | -0.41 | -15.7% | 0.071 |  |
| Energy | 18.12 | -0.66 | -24.2% | 0.073 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.53T | $308.63 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $2.90T | $390.49 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $4.72T | $194.83 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.71T | $360.45 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $404.0B | $140.27 | Michael D. Sicilia | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.14T | $1210.50 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $386.3B | $425.36 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $633.2B | $263.04 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $461.3B | $261.07 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $319.9B | $129.52 | Robert Davis | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.35T | $359.91 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.48T | $582.90 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $327.0B | $77.65 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $172.7B | $99.46 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $192.1B | $177.52 | Srinivasan Gopalan | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $394.4B | $377.52 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $443.8B | $963.53 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $268.3B | $199.25 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $72.8B | $229.86 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $167.6B | $282.25 | Vincenzo James Vena | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.10T | $507.78 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $896.2B | $334.47 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $416.8B | $58.73 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $261.7B | $85.51 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $301.2B | $1021.00 | David Solomon | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $352.5B | $151.40 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $422.0B | $951.67 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $362.0B | $84.14 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $197.1B | $144.22 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $890.0B | $111.84 | John R. Furner | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $130.0B | $139.45 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $77.4B | $166.03 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $98.8B | $1002.02 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $166.5B | $235.84 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $33.4B | $76.60 | Christian H. Hillabra… | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.61T | $242.67 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.48T | $393.45 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $356.9B | $357.90 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $199.4B | $280.63 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $65.2B | $44.09 | Elliott J. Hill | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $252.9B | $546.64 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $86.9B | $352.48 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $87.6B | $60.96 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $70.0B | $314.19 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $79.7B | $283.36 | Christophe Beck | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $184.2B | $88.34 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $110.5B | $97.98 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $101.0B | $129.60 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $75.4B | $138.51 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $60.8B | $93.06 | Jeffrey Walker Martin | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $567.9B | $137.02 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $337.0B | $169.21 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $127.6B | $104.73 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $69.7B | $130.78 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $67.5B | $45.13 | Olivier Le Peuch | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.58)

> **防禦為主：情緒偏貪婪、底部未確認、無強勢領漲板塊**
> 
> 今天以守代攻、不追高：市場情緒偏樂觀但 FTD 尚未確認、廣度偏弱且無單一板塊夠強領漲；科技看似最強卻出現內部人減碼與短線動能轉弱，等底部確認訊號再加碼。

### Key Takeaways
1. 壓低整體曝險至 0-25%：FTD 未確認（反彈第 5 天）＋頂部風險偏高，守住現金優先。
2. 避開科技追高：3M RS +21.6% 但 20d/5d 已翻負、內部人減碼（比率 0.41），屬窄幅領漲。
3. 減碼利率敏感板塊：實質利率 2.2% 壓抑長天期，Real_Estate/Utilities/Technology 估值承壓。
4. 清倉能源、公用事業、原物料：資金持續外流且無催化劑（三者列 AVOID）。
5. 靜待底部確認：關注 FTD 與廣度回升，出現後再轉積極。

### Sector Actions
- **Wait**: Technology (low) — 動能轉弱＋內部人減碼，勿追高
- **Wait**: Communication (low) — AI 催化但主題轉冷、肥尾偏高
- **Wait**: Financials (low) — FRED 偏好但分數偏弱，等銀行財報
- **Neutral**: Healthcare (med) — 廣度最佳、估值偏低，選股防禦
- **Avoid**: Energy (med) — 資金外流最重、3M RS -24%
- **Avoid**: Utilities (med) — 四方向皆看空、無承接買盤

### Watch Next
- FTD 確認訊號（指數放量突破反彈高點）— 出現才提高曝險
- 實質利率是否回落至 2.0% 以下，緩解長天期估值壓力
- 科技 20d/5d 相對強度能否翻正，判斷動能是否真的耗盡
- PEP（7/9）、DAL（7/9）財報與 7/14 起銀行財報季開局
- 市場廣度 uptrend ratio 能否自 0.25 均值回升

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | — | — |  |
| Real_Estate | — | — |  |
| Communication | — | — |  |

---

## Top Actionable Themes

1. AI/半導體與機器人自動化 Trending（Technology/Industrials）但需底部確認再進
2. 醫療保健防禦＋估值偏低（uptrend 0.520 全場最佳參與度）
3. 利率敏感長天期（REIT/Utilities）受實質利率 2.2% 壓制，回避
4. 能源/清潔能源空頭主題主導，資金外流最重

---

## HANDOFF TO INVESTMENT PROTOCOL

> V1.4 protocol；快取 STALE（前次 07-01，5 日）故全量重跑 Phase 0-1。Phase 1 valuation 與 Phase 3 smart_money 首輪撞 FMP 429 rate limit，個別重試後成功取得當日 cache。4 lane 平行 subagent（PARALLEL_SUBAGENT）意見分歧顯著、無單一板塊全數看多，與 signal_conflict=true 一致。DA 對 Technology 三重結構性 divergence（R4 real_rate/R5 insider/R7 momentum）全觸發並提出 HIGH 信度挑戰。fred_available=true 故走 Step 6 overlay 取代 Step 1。無 HOT 板塊（最高 Technology 58 WARM）。曝險底線 <40% 觸發 STEP B 強制 ≥3 AVOID。
