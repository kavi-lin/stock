# Sector Intelligence Report — 2026-05-11

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.5
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-05-11 21:05
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Technology | WARM | 61 | 0.89 | AI&Semi 雙 Trending heat 62.75 · Rank #1 + RS_3M +17.6% | ROBUST | XLK | macro_theme_divergence, overbought, late_cycle |
| Industrials | WARM | 53 | 0.96 | Infrastructure/Defense Mature 主題 · Rank #2 但 slope −0.0113 | N/A | XLI | late_cycle |
| Materials | WARM | 50 | 1.00 | FRED Overheating favor sector · Materials Concentration 主題 53.89 | N/A | XLB | late_cycle |
| Communication | WARM | 50 | 0.96 | 唯一 Up trend +0.0043 · PE_z −1.18 oversold value +5 | ROBUST | XLC | — |
| Energy | COLD | 49 | 1.00 | +42.7% earnings surprise (backward-looking) · PE_z +2.52 最貴 + RS 三窗皆負 | ROBUST | XLE | overbought, late_cycle |
| Healthcare | COLD | 38 | 1.00 | RS_3M −15.8% 全宇宙最深落後 · Obesity/GLP-1 + Biotech 雙 bearish 主題 | N/A | XLV | — |
| Consumer_Discretionary | COLD | 28 | 0.89 | FRED avoid sector + Rank #9 · 5d +1.6% 反彈但 3M −4.9% | N/A | XLY | late_cycle |
| Real_Estate | COLD | 28 | 0.92 | PE_z −1.70 深 oversold +5 · 0% beat rate (−18% surprise) | N/A | XLRE | macro_theme_divergence |
| Consumer_Staples | COLD | 27 | 1.00 | Greed 70 不利防禦 · Rank #10 + slope −0.0016 | N/A | XLP | — |
| Financials | COLD | 26 | 1.00 | FRED favor 但 Rank #8 OUTFLOW · Insider ratio 1.30 + senate +1 | N/A | XLF | — |
| Utilities | **AVOID** | 20 | 1.00 | Rank #11 + 5d −4.1% 最差 · slope −0.0129 最陡 | N/A | XLU | — |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 40-60% | Synthesized: 40-60% | Cycle: Late
FTD: FTD_CONFIRMED (quality 100) | Market Top: 25.6 Early_Warning | Breadth: 33.1 Weakening
Sentiment: F&G [70.0 — Greed] | VIX: 18.14 | Put/Call: n/a | SPY RSI: 73.8
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors · Quantum Computing · Basic Materials Concentration

---

## Step 6 — FRED Regime Overlay

- **Regime**: Overheating (confidence 0.76)
- **Favor**: Energy, Materials, Financials
- **Avoid**: Technology, Real Estate, Consumer Discretionary
- **Velocity highlights**: CPIAUCSL:accelerating, UNRATE:decelerating
- **Rationale**: Overheating conf 0.76 → favor: Energy/Materials/Financials ×0.998; avoid: Technology ×0.89, Real_Estate ×0.924, Consumer_Discretionary ×0.89; cyclical baseline ×0.962, defensive ×1.0

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 47.76 | +0.61 | +17.6% | 1.075 |  |
| Industrials | 40.36 | +0.45 | -6.8% | 0.673 |  |
| Materials | 27.41 | -0.17 | -6.7% | 0.723 |  |
| Energy | 35.62 | +2.52 | -2.2% | 0.716 |  |
| Healthcare | 27.98 | -0.97 | -15.8% | 1.21 |  |
| Communication | 27.72 | -1.18 | -5.8% | 0.914 | 🟢 OVERSOLD VALUE |
| Real_Estate | 50.07 | -1.70 | -1.1% | 0.634 | 🟢 OVERSOLD VALUE |
| Financials | 21.93 | -0.42 | -12.4% | 0.891 |  |
| Consumer_Discretionary | 56.08 | -0.29 | -4.9% | 0.782 |  |
| Consumer_Staples | 31.78 | -0.53 | -11.1% | 0.906 |  |
| Utilities | 28.84 | +0.23 | -3.6% | 0.92 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.31T | $293.26 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.08T | $415.06 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.23T | $215.22 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $2.04T | $430.00 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $563.5B | $195.94 | Michael D. Sicilia | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $310.5B | $297.15 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $413.4B | $897.45 | Joseph E. Creed | _TBD_ |
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

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.85T | $400.71 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.55T | $609.63 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $368.3B | $87.48 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $187.5B | $107.98 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $209.5B | $193.63 | Srinivasan Gopalan | _TBD_ |

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
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $345.1B | $379.98 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $532.8B | $221.32 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $356.5B | $201.55 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $275.1B | $111.38 | Robert Davis | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.93T | $272.68 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.61T | $428.35 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $316.2B | $317.45 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $195.9B | $275.75 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $65.3B | $44.14 | Elliott J. Hill | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $134.3B | $144.09 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $82.2B | $176.53 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $105.7B | $1072.08 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $151.5B | $214.63 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $39.5B | $90.57 | Christian H. Hillabra… | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $341.0B | $146.42 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $447.6B | $1008.79 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $337.4B | $78.42 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $211.4B | $154.62 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $1.04T | $130.43 | John R. Furner | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.03T | $475.66 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $809.5B | $302.10 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $364.1B | $51.31 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $231.5B | $75.64 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $276.3B | $936.48 | David Solomon | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $194.1B | $93.10 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $103.5B | $91.80 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $96.8B | $124.17 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $70.8B | $130.16 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $59.8B | $91.53 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.5)

> **Late-cycle 訊號交織，DEFENSIVE 守勢、輕度進場**
> 
> FTD 確認 vs 廣度走弱 vs Greed 70 vs CPI 加速—四訊號矛盾，先以 40-60% 上限保護資本，等待 CPI 5/14 數據再判方向。

### Key Takeaways
1. 保守持倉：synthesized_exposure 守住 40-60%（最保守來源為廣度），不追高 Tech / Communication WARM
2. 等 5/14 CPI 核心 MoM：>0.3% 將推升 DGS10、放大 Tech / Real_Estate 折扣率風險
3. Energy 雖 News + FRED 雙票 HOT，但 PE_z +2.52 + RS 三窗皆負 — 維持 COLD、不追財報後 momentum
4. Communication / Real_Estate 估值 oversold（PE_z −1.18 / −1.70）但缺催化，等廣度反轉再分批
5. Utilities AVOID：rank #11 + 5d −4.1%；insider ratio 2.57 contrarian 信號需更多時間發酵

### Sector Actions
- **Wait**: Technology (med) — WARM 但 RSI 73.8 + FRED avoid + CPI binary
- **Wait**: Industrials (med) — Mature 主題 + slope 轉弱，須廣度回穩
- **Wait**: Materials (med) — FRED favor 但 5d −1.9% 未確認
- **Wait**: Communication (low) — Up trend vs 50% beat 內部衝突
- **Underweight**: Healthcare (med) — Theme bearish 雙重 + RS_3M −15.8%
- **Avoid**: Energy (high) — PE_z +2.52 + RS 三窗全負
- **Avoid**: Utilities (high) — rank 11 + 5d −4.1% 守不住

### Watch Next
- 5/14 CPI 4 月（核心 MoM；若 ≥ 0.3% 觸發 Tech / Real_Estate 折扣率風險）
- 5/13 WMT/HD/CSCO 財報（消費韌性 + 企業 IT 雙驗證）
- Trump 訪中峰會 5/13 視窗 — 晶片出口管制 / 關稅
- Breadth 8MA 是否回升 0.60（目前 0.572，距 healthy 線僅 −0.028）
- Distribution day 計數：S&P 4 + NASDAQ 3，若任一達 6+ 觸發 market_top 升 Elevated

---

## Devil's Advocate Challenges (Accepted 4/5)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Technology — HOT | **Accepted** | SPY RSI_14 = 73.8 已伸展且廣度背離（S&P +6.0% vs Breadth 8MA −0.118 60d、Weakening 33.1、cycle PEAK 45d）；FRED slim 將 Tech 列 avoid（Overheating conf 0.76、DGS10 4.41% 升 90d、DGS2 3.92% 升 30d、CPI MoM 0.87% 為 baseline 3.2 倍、Core PCE 3.2%、real_rate 1.11%）— 每項利率敏感變量都與 Rotation/Theme HOT 對撞。 |
| Technology — HOT | **Accepted** | Smart-money 邊際轉空：mega-cap insider ratio 0.505 恰落在 0.5 警戒線（acquired 186 vs disposed 368）、senate net −1。雖未全面反轉，但與 RSI 73.8 froth 同步發生。 |
| Energy — HOT | **Accepted** | PE_z +2.52 全市場最貴 + RS 三窗皆負（3M −2.21%、20d −10.74%、5d −7.70% 持續走弱、非分歧）；News HOT 仰賴 6 報 +42.7% surprise 是 backward-looking，但 etf_volume_ratio 0.716 無新買盤、insider ratio 0.701 內部小幅賣出皆否定 thesis。FRED 與 News HOT 都未被當前盤面確認。 |
| Communication — HOT | **Accepted** | Rotation HOT 立論於唯一 Up trend (+0.0043、PE_z −1.18 oversold)，但 News 同時將 Communication 列 COLD（beat_rate 50%、surprise_avg −47.3%、2 報樣本）。一個建立於少量財報且 surprise 大幅負的「sole Up trend」更像技術殘留，無 thesis；無 AI&Semis 主題加持（紅利歸 XLK）。 |
| Healthcare — HOT | **Accepted** | News HOT 與 Theme COLD 衝突：Obesity/GLP-1 53.94 bearish + Biotech 42.12 bearish 是 Healthcare 兩大子題 — 均反向。RS_3M −15.8% 為全宇宙最深 3M 落後；財報 beat 未轉化為相對強度。Late-cycle + Overheating 之下傳統 defensive 該領漲卻沒做到，本身就是結構性警訊。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Energy | news_positive_price_negative | monitor | Earnings beat 100% + surprise +42.7% (6 reports) 但 RS 三窗皆負、PE_z +2.52、etf_volume 0.716 |
| Healthcare | news_positive_price_negative | monitor | AbbVie/JNJ 財報強但 RS_3M −15.8% 全宇宙最深落後，Theme bearish 雙壓 |
| Communication | news_negative_price_positive | monitor | 唯一 Up trend (+0.0043) 但 beat rate 50% surprise −47.3%（樣本 2，留意 reversion） |

---

## Top Actionable Themes

1. AI & Semiconductors
2. Quantum Computing
3. Basic Materials Concentration
4. Infrastructure & Construction
5. Defense & Aerospace

---

## HANDOFF TO INVESTMENT PROTOCOL

> DEFENSIVE 守勢，0 HOT / 4 WARM / 6 COLD / 1 AVOID。Tech/Industrials/Materials/Communication WARM 但皆需 wait — 等 5/14 CPI 與 5/13 WMT/HD/CSCO 財報後再決定加碼方向。Energy 雖財報亮眼但盤面拒絕，列 COLD。Utilities AVOID。signal_conflict=true 強制 stance ≤ NEUTRAL，最終 DEFENSIVE（COLD ≥ 3）。
