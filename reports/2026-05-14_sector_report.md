# Sector Intelligence Report — 2026-05-14

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.69
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-05-14 21:58
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Energy | WARM | 92.79 | 1.00 | uptrend 50.9% rank #1 · FRED Overheating favor + 通膨對沖 | ROBUST | XLE | late_cycle, signal_conflict_downgrade |
| Materials | WARM | 87.84 | 1.00 | uptrend 42.8% Up rising · BM Concen 59.8 + Silver +14.9% 1w | ROBUST | XLB | late_cycle, signal_conflict_downgrade, momentum_caution |
| Technology | WARM | 76.12 | 0.90 | AI/Quantum Trending 雙引擎 · FRED avoid + insider 0.484 bearish | ROBUST | XLK | late_cycle, signal_conflict_downgrade, macro_theme_divergence |
| Industrials | WARM | 64.86 | 0.97 | Space/Defense/Robotics 3 主題 · trend Down RS 三窗負 | N/A | XLI | — |
| Communication | WARM | 59.14 | 0.97 | AI infra tail benefit · pe_z -1.44 oversold +5 | N/A | XLC | — |
| Healthcare | WARM | 54.6 | 1.00 | beat rate 100% (n=1) · insider 1.27 偏正 | N/A | XLV | — |
| Consumer_Staples | COLD | 42.37 | 1.00 | grocery 價飆對 SSS 警訊 · WMT Q1 binary 21 日 | N/A | XLP | — |
| Utilities | COLD | 37.41 | 1.00 | uptrend 12.5% defensive 弱 · insider 中性 | N/A | XLU | — |
| Real_Estate | COLD | 36.15 | 0.93 | pe_z -1.59 oversold +5 · FRED avoid + rate sensitivity | N/A | XLRE | macro_theme_divergence |
| Financials | COLD | 34.4 | 1.00 | insider 1.30 sector 最高 · FRED favor 利差受惠 | N/A | XLF | — |
| Consumer_Discretionary | **AVOID** | 21.28 | 0.90 | uptrend 11.7% rank #10 · Clean EV + Cycl Concen 雙 bearish | N/A | XLY | macro_theme_divergence |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 40-60% | Synthesized: 40-60% | Cycle: Late
FTD: FTD_CONFIRMED (quality 100) | Market Top: 28.4 Yellow (Early Warning) | Breadth: 33.1 Weakening
Sentiment: F&G [71.8 — Greed] | VIX: 17.88 | Put/Call: n/a | SPY RSI: 80.7
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors (Trending 62.8) · Space Economy (Mature 61.5) · Oil & Gas / Energy (Mature 59.7)

---

## Step 6 — FRED Regime Overlay

- **Regime**: Overheating (confidence 0.68)
- **Favor**: Energy, Materials, Financials
- **Avoid**: Technology, Real_Estate, Consumer_Discretionary
- **Velocity highlights**: DFF:decelerating, CPIAUCSL:accelerating, CPILFESL:accelerating
- **Rationale**: Overheating regime, conf 0.68 → favor: Energy×0.998, Materials×0.998, Financials×0.998; avoid: Technology×0.901, Real_Estate×0.932, Consumer_Discretionary×0.901

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Energy | 37.79 | +2.45 | -2.4% | 0.016 |  |
| Materials | 28.31 | -0.02 | -10.4% | 0.024 |  |
| Technology | 48.68 | +0.89 | +18.2% | 0.033 |  |
| Industrials | 39.35 | +0.20 | -8.3% | 0.011 |  |
| Healthcare | 28.81 | -0.82 | -14.9% | 0.011 |  |
| Communication | 26.23 | -1.44 | -6.9% | 0.011 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 32.28 | -0.24 | -13.9% | 0.014 |  |
| Real_Estate | 50.38 | -1.59 | -5.8% | 0.015 | 🟢 OVERSOLD VALUE |
| Utilities | 26.8 | -0.38 | -10.4% | 0.012 |  |
| Consumer_Discretionary | 58.35 | -0.15 | -6.5% | 0.004 |  |
| Financials | 22.01 | -0.40 | -9.8% | 0.021 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $628.2B | $151.56 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $370.4B | $185.99 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $143.0B | $117.40 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $71.9B | $134.93 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $82.8B | $55.38 | Olivier Le Peuch | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $237.4B | $513.26 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $75.6B | $306.34 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $96.5B | $67.16 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $68.2B | $306.20 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $70.3B | $249.62 | Christophe Beck | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.39T | $298.87 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.01T | $405.21 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.49T | $225.83 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.97T | $416.79 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $545.8B | $189.76 | Michael D. Sicilia | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $307.9B | $294.71 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $415.6B | $902.30 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $239.9B | $178.11 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $138.1B | $217.96 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $157.1B | $264.65 | Vincenzo James Vena | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.87T | $402.62 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.57T | $616.63 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $368.7B | $87.56 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $182.2B | $104.92 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $205.9B | $190.28 | Srinivasan Gopalan | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $956.7B | $1015.93 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $364.3B | $401.16 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $554.7B | $230.42 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $368.4B | $208.50 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $280.2B | $113.45 | Robert Davis | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $331.2B | $142.24 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $458.3B | $1033.08 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $345.3B | $80.26 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $204.0B | $149.27 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $1.05T | $131.47 | John R. Furner | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $197.8B | $94.85 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $105.0B | $93.14 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $96.6B | $123.90 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $69.6B | $127.95 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $59.9B | $91.68 | Jeffrey Walker Martin | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $132.4B | $142.00 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $81.0B | $173.87 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $106.2B | $1077.28 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $155.4B | $220.14 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $39.1B | $89.62 | Christian H. Hillabra… | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.05T | $485.52 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $804.5B | $300.25 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $353.7B | $49.84 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $225.0B | $73.53 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $281.9B | $955.42 | David Solomon | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.91T | $270.13 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.67T | $445.27 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $301.3B | $302.55 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $195.9B | $275.70 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $62.6B | $42.34 | Elliott J. Hill | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.69)

> **防禦立場：訊號分歧 + 廣度惡化 + 商品/Tech 過熱**
> 
> FTD 強但 breadth Weakening 與 signal_conflict 共存 — 三 HOT (Energy/Materials/Tech) 全 signal_conflict 降 WARM，late-cycle 須收縮新部位、優先觀察 RS 五日轉折。

### Key Takeaways
1. Signal conflict 觸發 → 全 HOT 降 WARM、stance 鎖 DEFENSIVE，新建倉須等 breadth ≥40 或 RS 5d 三窗同向回穩
2. Technology 雖 RS 領先但 FRED avoid + insider 0.484 + SPY RSI 80.7 過熱 — Trump-Xi 峰會 5/19 為 binary 觸發點
3. Energy/Materials 受 FRED Overheating favor 但 Materials RS 三窗仍負（-10.4/-5.2/-0.2）— 通膨對沖 narrative 尚未被驗證
4. Cons_Disc 零售降溫 + grocery 飆價雙殺 → 維持 AVOID；WMT 5/21 Q1 將驗證消費降級韌性
5. Financials FRED favor + insider 1.30 與 rotation COLD 衝突 — 等 20d RS 由負轉正再考慮升級

### Sector Actions
- **Wait**: Energy (med) — score 92.8 但 signal_conflict 降 WARM
- **Wait**: Materials (low) — FRED favor 但 RS 三窗仍負
- **Wait**: Industrials (med) — 3 主題撐但 trend Down + RS 負
- **Wait**: Communication (low) — pe_z 反轉 +5 但 RS 5d -1.8%
- **Underweight**: Technology (high) — FRED avoid + insider 0.484 過熱
- **Avoid**: Consumer_Discretionary (high) — 零售降溫 + grocery 飆 + FRED avoid

### Watch Next
- Trump-Xi 科技議題峰會 5/19 — Tech/Cons_Disc binary 觸發點
- WMT Q1 2026-05-21 BMO — 消費降級韌性驗證
- 下一份 CPI YoY MoM 與 10Y UST 4.6% 門檻 — Tech HOT 推翻條件
- Materials 3M RS 是否能在 30 trading days 內由 -10.4% 回升至 ≥ -3%
- breadth 8MA 是否能回升突破 200MA（當前 gap -0.038）

---

## Devil's Advocate Challenges (Accepted 2/4)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Technology — HOT | **Accepted** | FRED Overheating 將 Technology 列 sector_rotation_avoid（CPI/CoreCPI 雙加速 + Fed 3.63% flat）；Smart Money 雙重背離 — insider ratio 0.484 < 0.5 BEARISH + Senate -1 在 RS +18.2% 領先期間反向減持。疊加 SPY RSI 80.7 overbought + market_top 28.4 Yellow + breadth 33.1 Weakening + S&P/Breadth 60d 發散，Tech ... |
| Materials — HOT | **Accepted** | Phase 1 RS 三窗皆負（rs_3m -10.4%、rs_20d -5.2%、rs_5d -0.2%）— 不是『開始輪入』，是『一直在掉，只是掉得慢一點』。把 RS 弱勢板塊用 FRED Overheating 通膨對沖 narrative 包裝成 HOT 為 narrative-driven over evidence。Insider ratio ~1.0 中性、Senate 0 中性 — 無 smart money 支持。 |
| Energy — HOT | Rejected | RS 三窗 rs_3m=-2.4%/rs_20d=-4.2%/rs_5d=+1.3% — 3 個月仍負，5d 微反彈不足成趨勢；Theme Oil&Gas 為 Mature（非 Trending/Accel）顯示熱度 plateau；insider ratio 0.697 mild bearish 內部人未加碼；Chevron 為個案 M&A 不可外推。 |
| Financials — COLD | Rejected | Insider ratio 1.303 為 sector 最高 BULLISH + Goldman Conviction List + FRED 列 favor（殖利率正 0.47 + Overheating 利差環境）。Rotation 因近期 RS 弱判 COLD 為以後驗價格動能否定領先基本面訊號，典型 momentum trap 反例。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | news_positive_price_negative | reduce_exposure | AI/Nvidia/CSCO 新聞 bullish 但 insider 0.484 + Senate -1 反向減持；SPY RSI 80.7 顯示價格 overshoot |
| Materials | news_positive_price_negative | monitor | BM Concen 59.8 Trending + 通膨對沖 narrative 但 RS 三窗負 — 主題熱度未轉換為相對表現 |
| Financials | news_positive_price_negative | monitor | insider 1.30 BULLISH + Goldman Conviction List + FRED favor 但 rotation 全期負 — smart money vs price action 分歧 |

---

## Top Actionable Themes

1. AI & Semiconductors (Trending 62.8)
2. Space Economy (Mature 61.5)
3. Oil & Gas / Energy (Mature 59.7)
4. Basic Materials Concentration (Trending 59.8)
5. Defense & Aerospace (Mature 53.0)

---

## HANDOFF TO INVESTMENT PROTOCOL

> DEFENSIVE stance（signal_conflict + breadth 33.1 Weakening + RSI 80.7 過熱）。無 HOT verdict — Energy/Materials/Tech 三高分被 signal_conflict 降 WARM；Cons_Disc AVOID。新部位優先觀察 RS 5d 三窗同向回穩 + breadth ≥40 才考慮升級；Tech 須額外通過 insider ratio ≥0.5 + Trump-Xi 5/19 利空消化才能解除 underweight。
