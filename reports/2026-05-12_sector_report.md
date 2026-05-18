# Sector Intelligence Report — 2026-05-12

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.55
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-05-12 20:22
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Energy | WARM | 87.7 | 1.00 | 商品/中東/能源敘事領漲 · z=+2.59 估值極端、insider 0.701 分歧 | RESILIENT | XLE | signal_conflict_downgrade, extreme_valuation_zscore, smart_money_divergence, momentum_exhaustion_3m |
| Materials | WARM | 81.2 | 1.00 | Basic Materials theme 60 Trending · z=−0.086 估值中性、uptrend 40.6% | RESILIENT | XLB | signal_conflict_downgrade, rs_3m_negative_despite_consensus |
| Industrials | WARM | 66.3 | 0.97 | Golden Dome +$3.2B / GE Aero · insider 1.413 買盤確認 | RESILIENT | XLI | rs_3m_negative_despite_catalysts |
| Technology | WARM | 62.4 | 0.91 | AI/Quantum theme 領頭(63/62.5) · FRED avoid + real_rate 1.94% 久期壓力 | N/A | XLK | macro_theme_divergence |
| Communication | COLD | 50.0 | 0.97 | z=−1.251 oversold value · slope+0.0011 微反彈 | N/A | XLC | oversold_value |
| Healthcare | COLD | 42.3 | 1.00 | Obesity & GLP-1 bearish theme 54.7 · z=−0.955 偏便宜 | N/A | XLV | theme_bearish_glp1_drag |
| Consumer_Staples | COLD | 40.1 | 1.00 | 無催化、無 theme · uptrend 14.8% 微正 slope | N/A | XLP | — |
| Real_Estate | COLD | 39.2 | 0.94 | EQIX data-center capex 個案利多 · FRED avoid + real_rate 1.94% 壓 cap-rate | N/A | XLRE | macro_avoid_real_rate_pressure |
| Utilities | COLD | 35.2 | 1.00 | pulse rc=5 beat 1.0 / insider 2.567 · Utilities Defensive bearish theme 27.8 | N/A | XLU | oversold_extreme_no_bid |
| Financials | COLD | 26.5 | 1.00 | Private credit stress 個案利空 · uptrend 13% slope−0.0131 | N/A | XLF | private_credit_stress_overhang |
| Consumer_Discretionary | **AVOID** | 22.8 | 0.91 | WSJ 中低收入擠壓 + Tesla 延遲 · FRED avoid + Cyclical Concentration 28.6 | N/A | XLY | macro_avoid_consumer_squeeze |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 40-60% | Synthesized: 40-60% | Cycle: Late
FTD: FTD_CONFIRMED (quality 100) | Market Top: 26.1 Early_Warning | Breadth: 33.1 Weakening
Sentiment: F&G [70.8 — Greed] | VIX: 18.76 | Put/Call: n/a | SPY RSI: 80.5
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors · Quantum Computing · Space Economy

---

## Step 6 — FRED Regime Overlay

- **Regime**: Overheating (confidence 0.64)
- **Favor**: Energy, Materials, Financials
- **Avoid**: Technology, Real Estate, Consumer Discretionary
- **Velocity highlights**: CPIAUCSL:accelerating, BAMLH0A0HYM2:accelerating, NFCI:accelerating
- **Rationale**: Overheating regime, conf 0.64 → favor: Energy×0.998, Materials×0.998, Financials×0.998; avoid: Technology×0.907, Real_Estate×0.936, Consumer_Discretionary×0.907

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Energy | 37.02 | +2.59 | +0.0% | 0.759 |  |
| Materials | 27.89 | -0.09 | -6.4% | 0.812 |  |
| Technology | 48.67 | +0.89 | +17.5% | 0.993 |  |
| Industrials | 40.52 | +0.50 | -5.8% | 0.715 |  |
| Healthcare | 28.06 | -0.95 | -15.0% | 1.077 |  |
| Real_Estate | 50.51 | -1.61 | -1.1% | 0.824 | 🟢 OVERSOLD VALUE |
| Communication | 27.32 | -1.25 | -7.6% | 1.024 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 31.46 | -0.69 | -11.2% | 0.979 |  |
| Financials | 22.4 | -0.28 | -11.7% | 0.933 |  |
| Consumer_Discretionary | 58.1 | -0.16 | -5.0% | 0.751 |  |
| Utilities | 27.3 | -0.24 | -2.7% | 1.14 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $620.4B | $149.68 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $368.0B | $184.76 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $140.8B | $115.55 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $71.0B | $133.31 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $82.1B | $54.93 | Olivier Le Peuch | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $233.3B | $504.40 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $77.1B | $312.70 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $92.5B | $64.38 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $67.8B | $304.50 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $70.7B | $251.10 | Christophe Beck | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $314.3B | $300.77 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $426.9B | $926.79 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $240.5B | $178.61 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $138.8B | $219.11 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $156.4B | $263.35 | Vincenzo James Vena | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.30T | $292.68 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.07T | $412.66 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.33T | $219.44 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $2.03T | $428.43 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $557.5B | $193.83 | Michael D. Sicilia | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.70T | $388.64 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.52T | $598.86 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $359.8B | $85.45 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $181.8B | $104.71 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $206.5B | $190.85 | Srinivasan Gopalan | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $910.7B | $967.08 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $349.1B | $384.44 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $533.0B | $221.43 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $358.7B | $202.78 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $274.9B | $111.30 | Robert Davis | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $333.8B | $143.36 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $443.4B | $999.47 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $338.4B | $78.66 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $204.2B | $149.41 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $1.02T | $127.59 | John R. Furner | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $134.3B | $144.07 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $82.7B | $177.47 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $107.1B | $1086.22 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $151.7B | $214.84 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $39.6B | $90.67 | Christian H. Hillabra… | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $197.8B | $94.84 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $105.0B | $93.10 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $97.4B | $124.90 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $71.1B | $130.70 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $60.7B | $92.83 | Jeffrey Walker Martin | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.03T | $479.55 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $803.9B | $300.00 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $358.7B | $50.55 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $225.2B | $73.58 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $278.7B | $944.86 | David Solomon | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.89T | $268.99 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.67T | $445.00 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $310.2B | $311.40 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $195.1B | $274.60 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $62.7B | $42.39 | Elliott J. Hill | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.55)

> **防禦取向:訊號衝突+廣度疲弱主導,HOT 全數降溫**
> 
> FTD day 23 確認 vs 廣度 33.1 Weakening + Top 26.1 Yellow + FRED Overheating 三訊號分歧 37.5pp;能源/原物料雖領漲被 signal_conflict 降 WARM、Tech/RE 受 real_rate 1.94% 久期壓力。

### Key Takeaways
1. 三訊號衝突 37.5pp(廣度 40-60 vs FTD 75-100 vs Top 80-90),曝險取最保守 40-60%
2. FRED Overheating + real_rate 1.94% + CPI 加速 → 防禦 Tech / Real_Estate / Consumer_Discretionary (FRED avoid)
3. 全 11 產業無一 HOT,Energy/Materials 因訊號衝突強制 WARM、Industrials/Tech 持 WARM
4. Energy z=+2.59 已透支 + insider 0.701 分歧 + rs_3m +0.04% flat → 動能耗盡風險高
5. 5/13 PPI 與 5/14 零售銷售連兩天高影響 macro,5/20 FOMC Minutes 是本週 binary 主場

### Sector Actions
- **Wait**: Industrials (med) — RTX/GE 正向但 rs_3m -5.77%
- **Wait**: Technology (low) — FRED avoid + real_rate 1.94% 久期壓力
- **Neutral**: Energy (med) — WARM 但 z=+2.59 透支 + insider 分歧
- **Neutral**: Materials (med) — WARM;rs_3m -6.4% 動能未跟上
- **Avoid**: Real_Estate (high) — real_rate 1.94% × PE 50.51 duration kill
- **Avoid**: Consumer_Discretionary (high) — 消費者擠壓 + FRED avoid + slope worst

### Watch Next
- 5/13 PPI MoM(估 +0.5%)是否再次加速通膨敘事
- 5/14 零售銷售 MoM(估 +0.5% vs 前 +1.7%)看消費韌性
- 5/15 Trump-Xi 峰會 AI 晶片出口磋商結果(NVDA/AMD/TSM 直接受影響)
- 5/20 FOMC Minutes 對通膨加速 + real_rate 高位的反應
- NFCI / HY-OAS velocity 是否從 accelerating 轉為持平 — 信用渠道是否止裂

---

## Devil's Advocate Challenges (Accepted 6/6)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Energy — HOT | **Accepted** | Energy z=+2.59 是當前 11 產業最極端估值且 insider_ratio 0.701 (sell-leaning) 形成 smart-money 分歧;rs_3m 僅 +0.04% 已 flat-line 顯示動能枯竭,skew −0.34 表示左尾風險偏高。 |
| Technology — HOT | **Accepted** | Technology ∈ fred_rotation_avoid 因 real_rate_preferred 1.94% (DFII10) 進入久期壓力區;Theme lane 忽略此 discount rate 風險。News lane 同步降為 COLD (Barron's chip-fragile + AI-windfall-tax + insider 0.505 / senate -1) 表示頂部分配跡象明顯。 |
| Real_Estate — HOT | **Accepted** | Real_Estate ∈ fred_rotation_avoid;real_rate_preferred 1.94% 直接壓 REIT cap rate,sector PE_TTM 50.51 久期最重。NFCI/HY-OAS velocity 雙雙 accelerating (即使絕對值低) 是信用渠道最早裂痕的早期警告。 |
| Materials — HOT | **Accepted** | Materials 三路 (Rotation+Theme+FRED) 共識看多但 rs_3m 已是 −6.39%,意味多頭基於 'should work' 而非 'is working'。NFCI+HY-OAS velocity 雙 accelerating 是 cyclical-credit reversal 的早期 textbook,Materials 歷史上最先承壓。 |
| Industrials — HOT | **Accepted** | Industrials 設置最乾淨 (insider 1.413 + RTX Golden Dome + GE +35.7%) 但 rs_3m 仍 −5.77% 顯示新聞催化劑尚未轉化為相對強勢;excess_kurt 0.90 是 top-3 HOT 中最高雙向肥尾風險。CPI+NFCI velocity 同向 accelerating 是典型 CPI peak → Fed 鷹派轉向 → cyclical industrial demand crack 在 2-3 個月內的前序。 |
| Communication — HOT | **Accepted** | Communication 僅 Sector_Rotation lane 支持 (oversold value z=−1.251),Theme/News/FRED 三 lane 全略過。insider_ratio 0.894 偏中性偏空,sector 與 META/GOOGL 重疊高,後者在 fred_rotation_avoid 因 real_rate 1.94%。Late-cycle Overheating 歷史上懲罰 'cheap growth' bounce — discount rate 漲速超過估值修復。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Energy | news_positive_price_negative | monitor | 中東+supply tightness news 多,但 insider 0.701 + rs_3m flat 不接力 |
| Industrials | news_positive_price_negative | monitor | RTX Golden Dome + GE Aero 大利多但 rs_3m -5.77% RS 未跟上 |
| Real_Estate | news_positive_price_negative | reduce_exposure | EQIX/PLD 個案利多但 real_rate 1.94% 結構性壓 cap-rate |

---

## Top Actionable Themes

1. AI & Semiconductors
2. Quantum Computing
3. Space Economy
4. Basic Materials Concentration
5. Oil & Gas
6. Defense & Aerospace
7. Obesity & GLP-1 (bearish)

---

## HANDOFF TO INVESTMENT PROTOCOL

> DEFENSIVE 取向:三訊號衝突 37.5pp,曝險上限 40-60%;Energy/Materials WARM 仍是 11 產業最強但動能與估值警示;Tech WARM with macro_theme_divergence,個股選股聚焦避開 fred_avoid (Tech/RE/Disc) 且優先 insider buy-skew (Industrials 1.413, Utilities 2.567, Healthcare 1.27)。
