# Sector Intelligence Report — 2026-06-07

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-06-07 14:20
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|
| Technology | WARM | 68 | 唯一正向 3M RS (+21.6%) 與最高 uptrend 0.232，撐起整個窄幅大盤 · 但 insider 0.47 (<0.5) + senate 淨賣 -2，價量與內部人方向背離 | N/A | XLK | smart_money_divergence, concentration_risk, rate_sensitive_long_duration |
| Real_Estate | WARM | 56 | 最便宜估值 z1y -1.63 + 第二高 uptrend 0.221，跌幅最小 RS -5.5% · 「降息題材、殖利率下行受惠」defensive 敘事 + insider 1.30 累積 | N/A | XLRE | rate_sensitive_long_duration, value_trap_risk |
| Healthcare | WARM | 54 | RISK_OFF defensive 領頭：「Health Care Flies High」+ low-vol 配置敘事 · insider 1.29 累積；FRED Transitional regime favor (×1.024) | N/A | XLV | — |
| Industrials | COLD | 49 | Space/Defense/Industrials 題材 heat 58.6 + beat 1.00 撐基本面 · 但 RS -7.2%、PE 42.5 (z +0.85) 偏貴，cyclical 在 Late/RISK_OFF 不利 | N/A | XLI | overbought_valuation |
| Financials | COLD | 47 | 最便宜 PE 19.0 (z -1.43) + 曲線陡化利 NIM (FRED lane HOT) · 但 theme bearish (Banks 42.0)、RS -6.3%，題材與動能逆風 | N/A | XLF | bearish_theme |
| Consumer_Staples | COLD | 44 | FRED favor (×1.024) + 便宜 z -1.06 (+5 penalty) · 但 RS -12.4% 重弱、bearish concentration 題材、uptrend 0.162 | N/A | XLP | bearish_theme |
| Energy | COLD | 42 | Iran 戰爭 100 天 + CPI 再加速 → 通膨對沖題材 (FRED lane HOT) · 但 z1y +1.36 最超買、RS -7.8% 已轉弱 = late-cycle 分布 | N/A | XLE | overbought_valuation |
| Consumer_Discretionary | COLD | 35 | PE 52.8 最貴 + insider 0.76 (次低) 賣壓 · Retail bearish 題材、RS -9.3% | N/A | XLY | bearish_theme, smart_money_soft |
| Communication | COLD | 34 | 便宜 z -1.87 (+5 penalty) 但 RS -14.6% 接近最弱 · 無熱題材帶動、uptrend 0.131 | N/A | XLC | weak_momentum |
| Utilities | COLD | 32 | insider 3.14 全表最強累積（DA 反向挑戰點） · 但 uptrend 0.089 最弱、RS -14.8% 最差、bearish 題材 3 lane COLD | N/A | XLU | bearish_theme, weak_momentum |
| Materials | COLD | 31 | FRED 通膨對沖題材 (real asset)，但 uptrend 0.097 次弱 · RS -8.2%、新聞 catalyst 量 0 | N/A | XLB | weak_momentum |

---

## Macro Context

```text
Market Regime: RISK_OFF | Breadth Ceiling: 40-60% | Synthesized: 40-60% | Cycle: Late
FTD: FTD_CONFIRMED (quality 100) | Market Top: 44.6 Orange (Elevated Risk) | Breadth: 34.5 Weakening
Sentiment: F&G [53.0 — Neutral] | VIX: 21.51 | Put/Call: n/a | SPY RSI: 48.6
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors (Trending heat 74.7) — 撐盤但 insider 分布，觀望非追高 · Defensive 輪動 (Healthcare/低波動/股息) — RISK_OFF 受惠首選 · 通膨對沖 (Energy/Materials, real asset) — 題材在但動能未跟上，避免追超買

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 49.61 | +0.81 | +21.6% | 2.075 |  |
| Real_Estate | 50.28 | -1.63 | -5.5% | 1.097 | 🟢 OVERSOLD VALUE |
| Healthcare | 30.2 | -0.53 | -9.5% | 2.019 |  |
| Industrials | 42.51 | +0.85 | -7.2% | 1.154 |  |
| Financials | 19.01 | -1.43 | -6.3% | 1.166 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 30.63 | -1.06 | -12.4% | 1.419 | 🟢 OVERSOLD VALUE |
| Energy | 36.13 | +1.36 | -7.8% | 0.732 |  |
| Consumer_Discretionary | 52.82 | -0.59 | -9.3% | 1.001 |  |
| Communication | 22.18 | -1.87 | -14.6% | 1.824 | 🟢 OVERSOLD VALUE |
| Utilities | 25.87 | -0.71 | -14.8% | 0.976 |  |
| Materials | 26.94 | -0.23 | -8.2% | 1.044 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.51T | $307.34 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.10T | $416.67 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $4.97T | $205.10 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.83T | $385.73 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $613.8B | $213.41 | Michael D. Sicilia | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $134.8B | $144.54 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $90.4B | $194.12 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $106.6B | $1080.95 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $146.1B | $206.93 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $41.2B | $94.49 | Christian H. Hillabra… | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.07T | $1131.42 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $362.8B | $399.47 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $560.3B | $232.77 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $401.5B | $227.23 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $298.3B | $120.79 | Robert Davis | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $342.7B | $328.00 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $416.5B | $904.28 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $243.7B | $180.99 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $135.6B | $213.97 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $161.7B | $272.32 | Vincenzo James Vena | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.05T | $488.13 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $837.0B | $312.37 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $382.0B | $53.83 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $250.8B | $81.94 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $306.4B | $1038.68 | David Solomon | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $341.2B | $146.54 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $431.0B | $971.87 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $342.0B | $79.48 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $194.0B | $141.92 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $946.1B | $118.88 | John R. Furner | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $621.4B | $149.92 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $373.0B | $187.31 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $142.7B | $117.14 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $73.4B | $137.78 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $82.0B | $54.87 | Olivier Le Peuch | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.65T | $246.03 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.47T | $391.00 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $309.9B | $310.78 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $198.8B | $279.84 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $63.5B | $42.98 | Elliott J. Hill | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.46T | $368.53 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.51T | $593.00 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $346.0B | $82.18 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $173.1B | $99.71 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $192.7B | $178.10 | Srinivasan Gopalan | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $179.0B | $85.84 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $104.4B | $92.60 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $96.8B | $124.22 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $70.3B | $129.14 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $59.8B | $91.42 | Jeffrey Walker Martin | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $235.0B | $507.90 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $75.3B | $305.30 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $91.1B | $63.37 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $62.9B | $282.35 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $72.6B | $257.97 | Christophe Beck | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.58)

> **防禦為先：窄幅弱勢盤，等 CPI 落地再加碼**
> 
> 今天先守不攻、把曝險壓在 40-60% 區間，原因是 breadth 跌到 34.5、八個板塊轉冷、唯一撐盤的科技股出現內部人賣超背離；要等 6/10 CPI 落地、breadth 回穩才考慮把資金從 defensive 轉回攻擊。

### Key Takeaways
1. 守勢定調：breadth 34.5 走弱 + 八板塊轉冷 + 大盤剛現 4 月以來最大單日跌幅，先降曝險不追高
2. 科技唯一撐盤但別當攻擊標的：RS +21.6% 背後 insider 0.47、senate 淨賣 -2，分布訊號明確，動作改為觀望
3. 避險首選醫療：defensive 領頭 + insider 1.29 累積 + FRED regime favor，相對最乾淨
4. Real_Estate 便宜勿急接：升實質利率 (2.1) + 曲線陡化下，cheap-and-falling 是價值陷阱
5. 6/10 CPI 為本週關鍵閘門：核心若再加速，長久期科技/REIT/公用先 de-rate

### Sector Actions
- **Overweight**: Healthcare (med) — defensive 領頭+內部人累積
- **Wait**: Technology (med) — 撐盤但內部人賣超背離
- **Wait**: Real_Estate (low) — 便宜但升息曲線陡化逆風
- **Neutral**: Energy (low) — 超買 z+1.36 但 RS 轉弱
- **Underweight**: Consumer_Discretionary (med) — PE 52.8 最貴+內部人賣
- **Avoid**: Materials (med) — uptrend 0.097 結構弱

### Watch Next
- 6/10 (週三) 08:30 ET May CPI：核心月增是否再加速 → 長久期資產 de-rate 風險
- 6/16-17 FOMC + 點陣圖：升實質利率 2.1 下的政策路徑訊號
- 科技 insider/senate 流向：若 insider 續 <0.5 兩週則 Tech 降 WARM→COLD
- Breadth 是否守住 34.5：跌破則 stance 轉更保守、WARM 板塊重評
- Utilities 動能：若 RISK_OFF 續行且 15 天內跑贏等權大盤，insider 3.14 撐起 → 升 WARM

---

## Top Actionable Themes

1. AI & Semiconductors (Trending heat 74.7) — 撐盤但 insider 分布，觀望非追高
2. Defensive 輪動 (Healthcare/低波動/股息) — RISK_OFF 受惠首選
3. 通膨對沖 (Energy/Materials, real asset) — 題材在但動能未跟上，避免追超買

---

## HANDOFF TO INVESTMENT PROTOCOL

> STALE cache (06-06 12:46, ~17h) → 完整跑 Phase 0-1。Phase 0 三訊號衝突 (Breadth 40-60% / FTD 75-100% / MarketTop 60-75%，spread 37.5pp >30) → signal_conflict=true，FTD 為 2026-04-08 舊確認、bottom-signal 折半。valuation 端點週末空 (06-07 Sunday)，採 last close 06-05 snapshot (複製為 06-07 cache)。econ/earnings calendar FMP legacy 403 soft-fail，CPI/FOMC 日期改 WebSearch。Phase 4a 4-lane PARALLEL_SUBAGENT 全回 isolated；科技呈 2(HOT)-vs-2(COLD) lane 分裂。0 HOT、3 WARM、8 COLD → stance DEFENSIVE (signal_conflict 已封頂 ≤NEUTRAL，DEFENSIVE 更保守 OK)。
