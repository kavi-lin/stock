# Sector Intelligence Report — 2026-05-10

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.53
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-05-10 21:30
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Technology | WARM | 69 | 0.90 | AI+Quantum 雙引擎 theme heat 52.8/52.7 · 3M RS +17.6% 仍領漲但 slope 轉負 | ROBUST | XLK | macro_theme_divergence, late_cycle |
| Materials | WARM | 59 | 1.00 | Theme heat 53.9 居首但 narrow_rally · FRED favor (Overheating + 商品) | N/A | XLB | late_cycle, narrow_rally_concentration |
| Energy | WARM | 56 | 1.00 | 9 報全 beat surprise +44% · FRED Overheating favor 實物資產 | N/A | XLE | late_cycle, overbought, bearish_theme_overlay |
| Industrials | COLD | 48 | 0.97 | uptrend rank 2 (32.6%) · Infra+Defense+Space 三 mature theme | N/A | XLI | late_cycle, bearish_theme_overlay |
| Consumer_Discretionary | COLD | 40 | 0.90 | earnings surprise +43.7% (NFLX/AMZN 帶動) · FRED avoid 利率敏感 | N/A | XLY | late_cycle, bearish_theme_overlay |
| Healthcare | COLD | 39 | 1.00 | Lilly 上修 guide $2B · Obesity/GLP-1 bearish theme heat 53.9 | N/A | XLV | bearish_theme_overlay |
| Utilities | COLD | 36 | 1.00 | insider 2.57 強買但市場最弱 ratio 10% · Nuclear bearish heat 35.3 | N/A | XLU | bearish_theme_overlay |
| Communication | COLD | 34 | 0.97 | PE z=-1.12 oversold value (+5) · 唯一 trend Up 但 RS_3M -5.8% | N/A | XLC | late_cycle |
| Real_Estate | COLD | 31 | 0.93 | PE z=-1.66 最深超賣 (+5) · 財報 beat 0.0 surprise -10% | N/A | XLRE | macro_theme_divergence |
| Consumer_Staples | COLD | 31 | 1.00 | beat 1.0 但 surprise +4.2% 平淡 · bearish concentration heat 26 | N/A | XLP | — |
| Financials | **AVOID** | 24 | 1.00 | FRED Overheating favor (NFCI -13%) · Senate +1 唯一正 | N/A | XLF | late_cycle |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 40-60% | Synthesized: 40-60% | Cycle: Late
FTD: FTD_CONFIRMED (quality 100) | Market Top: 26.9 Early_Warning | Breadth: 33.1 Weakening
Sentiment: F&G [71.2 — Greed] | VIX: 17.19 | Put/Call: n/a | SPY RSI: 73.8
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors (heat 52.8 Trending) — 主導 Tech 領導，但 narrow_rally 結構脆弱 · Basic Materials Concentration (heat 53.9 Trending) — narrow_rally divergence gap=30.8 警示 · Oil & Gas Energy (heat 48.2 Mature) — beat 100% surprise +44% 但 z=+2.64 overbought

---

## Step 6 — FRED Regime Overlay

- **Regime**: Overheating (confidence 0.66)
- **Favor**: Energy, Materials, Financials
- **Avoid**: Technology, Real Estate, Consumer Discretionary
- **Velocity highlights**: NFCI:accelerating, BAMLH0A0HYM2:accelerating, ICSA:accelerating
- **Rationale**: Overheating regime, conf 0.66 → favor: Materials×0.998, Energy×0.998, Financials×0.998; avoid: Technology×0.904, Consumer_Discretionary×0.904, Real_Estate×0.934

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 47.28 | +0.54 | +17.6% | 1.075 |  |
| Industrials | 40.42 | +0.47 | -6.8% | 0.673 |  |
| Materials | 27.84 | -0.10 | -6.7% | 0.723 |  |
| Energy | 35.42 | +2.63 | -2.2% | 0.716 |  |
| Healthcare | 28.52 | -0.91 | -15.8% | 1.21 |  |
| Communication | 28.01 | -1.12 | -5.8% | 0.914 | 🟢 OVERSOLD VALUE |
| Real_Estate | 50.22 | -1.66 | -1.1% | 0.634 | 🟢 OVERSOLD VALUE |
| Financials | 21.93 | -0.41 | -12.4% | 0.891 |  |
| Consumer_Discretionary | 55.69 | -0.40 | -4.9% | 0.782 |  |
| Consumer_Staples | 31.9 | -0.47 | -11.1% | 0.906 |  |
| Utilities | 28.08 | +0.08 | -3.6% | 0.92 |  |

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

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $310.5B | $297.15 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $417.6B | $897.45 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $237.1B | $176.09 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $135.0B | $213.12 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $157.1B | $264.65 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $228.1B | $493.16 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $78.1B | $316.82 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $88.6B | $61.65 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $65.8B | $295.41 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $71.8B | $254.22 | Christophe Beck | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $598.5B | $144.39 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $362.1B | $181.45 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $138.7B | $113.87 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $69.3B | $130.03 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $79.6B | $53.27 | Olivier Le Peuch | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $893.2B | $948.45 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $344.9B | $379.98 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $532.8B | $221.32 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $356.5B | $201.55 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $275.1B | $111.38 | Robert Davis | _TBD_ |

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
| **MCD** | McDonald's Corporation | Restaurants | $195.9B | $275.75 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $65.3B | $44.14 | Elliott J. Hill | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $341.0B | $146.42 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $447.6B | $1008.79 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $337.4B | $78.42 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $211.4B | $154.62 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $1.04T | $130.43 | John R. Furner | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $194.1B | $93.10 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $103.5B | $91.80 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $96.8B | $124.17 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $70.8B | $130.16 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $59.8B | $91.53 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.53)

> **DEFENSIVE：窄幅領導 + breadth 33 + 三訊號分歧（synth 40-60%）**
> 
> FTD day 22 已過 prime window，breadth 33.1 Weakening + market_top Yellow + cycle Late，僅 Tech/Materials/Energy 進 WARM 但全帶警示；保持低暴露，等待 breadth 修復或 leadership 換手。

### Key Takeaways
1. stance DEFENSIVE：signal_conflict (max-min 37.5pp) 強制 cap NEUTRAL，但 7 COLD + breadth 33 推到 DEFENSIVE。
2. Tech 表面強(RS_3M +17.6%)但 4 lane 矛盾：Theme/Rotation HOT vs News/FRED COLD；insider 0.505 borderline + chip/software 分化。
3. FRED Overheating + CPI MoM +0.87% 加速 → Energy/Materials/Financials 結構性 favor，但個別 valuation 已透支(Energy z=+2.64)。
4. Real_Estate z=-1.66 oversold 為 1-vs-3 孤立論點，DA HIGH 反對；不建議 mean-reversion 進場。
5. watch SPY RSI 73.8 + breadth 8MA -0.118 60d divergence；任一 mega-cap > 4% 單日跌幅可能引發 leadership rotation。

### Sector Actions
- **Overweight**: Materials (low) — FRED favor + theme heat 53.9 但 narrow_rally
- **Overweight**: Energy (low) — FRED favor + 9 報全 beat 但 z=+2.64 overbought
- **Wait**: Technology (med) — FRED avoid + smart money borderline，等 RSI 回落
- **Wait**: Financials (low) — FRED favor 但 uptrend 17.8% 全市場第三弱
- **Avoid**: Real_Estate (high) — 財報 0% beat + FRED avoid，oversold 不等於 turnaround
- **Avoid**: Utilities (high) — uptrend 10% + 20d RS -13.3% 全市場最差

### Watch Next
- SPY RSI 從 73.8 回落到 < 60 → leadership rotation 啟動訊號
- DFII10 real_rate 突破 2.0% → growth/Real_Estate 估值連鎖打擊
- breadth 8MA crossover 200MA (gap -0.028) 是否擴大或收斂
- Tech mega-cap (NVDA/AVGO/MSFT) 任一單日 > 4% 跌幅 → 確認 narrow leadership 結束
- CPI 下次 MoM 是否延續 +0.87% 加速 → Fed hawkish re-pricing

---

## Devil's Advocate Challenges (Accepted 3/3)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Technology — HOT | **Accepted** | FRED Overheating regime 明確將 Technology 列為 sector_rotation_avoid，real_rate=1.95% 接近 2% 警戒、DFII10 高位對長存續 growth 估值是直接逆風；rotation 5d RS slope 已轉負（窄幅領導侵蝕），News_Catalyst lane 反向把 Tech 列 COLD（insider_ratio 0.505 borderline、Senate 30d -1、'chip 漲 software 慢' narrative）。Tail risk 26.4 ... |
| Real_Estate — HOT | **Accepted** | Sector_Rotation 以 z=-1.66 mean-reversion 為由列 HOT，但 Theme(heat 21.2 最低)、News(beat 0.0 surprise -10.0% 純利空)、FRED(real_rate 1.95% + Overheating avoid Real_Estate) 三條 lane 全部反向列 COLD，1-vs-3 孤立論點。insider_ratio 1.62 看似 bullish 但在 fundamentals 惡化 + 利率長期高位環境下，僅是 insider 認為股價已反映，並非基本面轉折。 |
| Energy — HOT | **Accepted** | News + FRED 表面雙確認，但 Sector_Rotation 端 Energy 為 Down (rotation OUTFLOW) 且 z=+2.64 屬 overbought valuation extreme，beat surprise +44.4% 已 priced-in。cycle Late (PEAK 45d ago) + sentiment Greed 71.2 環境，商品 sector 容易在 Greed 高峰反向確認 top；CPI 加速短期利多但放大 Fed hawkish re-pricing risk，real_ra... |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | news_negative_price_positive | reduce_exposure | 價格 RS +17.6% 仍領漲但 insider 0.505 + Senate -1 + chip/software 分化 narrative — smart money 邊緣退場 |
| Real_Estate | news_negative_price_positive | monitor | PE z=-1.66 最深超賣但財報 0% beat + FRED avoid — oversold 為 trend-following 而非 mean-reversion |

---

## Top Actionable Themes

1. AI & Semiconductors (heat 52.8 Trending) — 主導 Tech 領導，但 narrow_rally 結構脆弱
2. Basic Materials Concentration (heat 53.9 Trending) — narrow_rally divergence gap=30.8 警示
3. Oil & Gas Energy (heat 48.2 Mature) — beat 100% surprise +44% 但 z=+2.64 overbought
4. Obesity/GLP-1 (bearish heat 53.9) — 壓抑 Healthcare 整體 sentiment

---

## HANDOFF TO INVESTMENT PROTOCOL

> DEFENSIVE stance — signal_conflict + breadth Weakening + cycle Late + 7 COLD。Investment protocol: 個股應限定在 WARM sectors (Tech/Materials/Energy)，但每筆都需 valuation/smart money/macro divergence 三重檢驗；避開 Real_Estate / Utilities。
