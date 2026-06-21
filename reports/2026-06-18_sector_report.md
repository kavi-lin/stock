# Sector Intelligence Report — 2026-06-18

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: NEUTRAL · **Cycle**: Mid · **Generated**: 2026-06-18 21:31
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|
| Technology | **HOT** | 76 | 全場唯一正 RS3m (+22.7%)，且多週期同向正 (20d +6.3% / 5d +3.1%) — 動能未耗盡 · AI & Semiconductors 71.6 (唯一仍 Trending 的多頭主題)，MRVL/NVDA 兆元敘事領軍 | MODERATE | XLK | smart_money_divergence, real_rate_valuation_headwind, narrow_breadth_concentration, stretched_valuation |
| Industrials | WARM | 66 | uptrend_ratio 0.330 全場最高，估值溫和 z1y -1.62、內部人淨買 1.26 · Robotics 65.9 / Infrastructure 60.7 / Defense 57.0 多題撐盤 (皆 Mature stage) | N/A | — | momentum_only_no_macro_tailwind, breadth_below_0.34 |
| Financials | WARM | 55 | 全場最便宜 PE 20.2 / z1y -1.07 (oversold value +5)，殖利率曲線 +0.66 陡化利 NIM · FRED lane 唯一主動點名 HOT — T10Y2Y + DGS10 加速陡化的直接受益者 | N/A | — | news_sentiment_cautious |
| Materials | WARM | 54 | Basic Materials 主題集中度 62.7 Trending — 第二個仍活躍多頭主題 · uptrend 0.271 中段、估值中性 z1y -0.05 | N/A | — | single_pillar_theme_only, thin_news_coverage |
| Healthcare | COLD | 44 | Healthcare & Pharma 主題 32.6 bearish 且 Accelerating — 下行動能升溫 · RS3m -9.6% 弱，內部人淨買 1.64 為唯一亮點 | N/A | — | bearish_theme_accelerating |
| Consumer_Discretionary | COLD | 42 | Retail & Consumer 主題 26.1 bearish；PE 54.1 偏貴 · RS3m -7.6% 落後，beat_rate 1.00 但動能不足 | N/A | — | bearish_theme, stretched_valuation |
| Communication | COLD | 38 | RS3m -15.9% 接近全場最弱，uptrend 0.167 低 · 估值便宜 z1y -1.77 (oversold value +5) 為唯一支撐 | N/A | — | weakest_rs_cluster |
| Real_Estate | COLD | 35 | real_rate 2.15% > 2.0 對長久期 REIT 為直接逆風 (FRED lane 點名 COLD) · Real Estate & REITs 主題 29.4 bearish；估值 z1y -1.73 oversold (+5) | N/A | — | real_rate_headwind, bearish_theme |
| Consumer_Staples | COLD | 35 | Consumer Defensive 集中度主題 28.4 bearish 且 Accelerating · uptrend 0.153 低、RS3m -10.8% 弱，估值 z1y -1.05 oversold (+5) | N/A | — | bearish_theme_accelerating |
| Energy | COLD | 27 | RS3m -18.5% 全場最差，uptrend 0.061 近乎全滅 · Oil & Gas 主題 47.3 但 direction bearish；估值 z1y +0.97 偏貴 | N/A | — | worst_rs, lowest_breadth_cluster |
| Utilities | **AVOID** | 24 | uptrend 0.037 全場最低，RS3m -16.9% 倒數 · real_rate 2.15% > 2.0 壓長久期 (FRED lane 點名 COLD) | N/A | — | lowest_breadth, real_rate_headwind |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 60-75% | Synthesized: 60-75% | Cycle: Mid
FTD: FTD_CONFIRMED (quality 100) | Market Top: 37.6 Yellow (Early Warning) | Breadth: 53.0 Neutral
Sentiment: F&G [55.5 — Neutral] | VIX: 17.0 | Put/Call: n/a | SPY RSI: 50.8
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors · Robotics & Automation · Infrastructure & Construction

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 53.39 | +1.45 | +22.7% | 0.951 |  |
| Industrials | 29.22 | -1.62 | -3.3% | 1.332 |  |
| Financials | 20.2 | -1.07 | -1.7% | 1.29 | 🟢 OVERSOLD VALUE |
| Materials | 27.85 | -0.05 | -4.7% | 1.281 |  |
| Healthcare | 29.83 | -0.59 | -9.6% | 1.0 |  |
| Consumer_Discretionary | 54.14 | -0.45 | -7.6% | 1.169 |  |
| Communication | 21.97 | -1.77 | -15.9% | 1.592 | 🟢 OVERSOLD VALUE |
| Real_Estate | 48.7 | -1.73 | -7.4% | 2.384 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 30.54 | -1.05 | -10.8% | 1.434 | 🟢 OVERSOLD VALUE |
| Energy | 34.49 | +0.97 | -18.5% | 0.973 |  |
| Utilities | 25.14 | -1.07 | -16.9% | 1.116 | 🟢 OVERSOLD VALUE |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.36T | $297.12 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $2.87T | $385.76 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.01T | $206.66 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.89T | $398.21 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $541.6B | $188.30 | Michael D. Sicilia | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $374.8B | $358.72 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $446.3B | $968.91 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $258.2B | $191.74 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $148.3B | $233.98 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $155.2B | $261.36 | Vincenzo James Vena | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.06T | $490.05 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $902.4B | $336.79 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $409.2B | $57.66 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $262.8B | $85.89 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $329.9B | $1118.38 | David Solomon | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $239.6B | $517.92 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $79.4B | $321.85 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $103.4B | $71.94 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $62.9B | $282.36 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $77.1B | $273.94 | Christophe Beck | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.05T | $1118.47 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $370.9B | $408.38 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $562.9B | $233.84 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $392.9B | $222.38 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $285.5B | $115.60 | Robert Davis | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.59T | $240.62 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.50T | $400.47 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $337.6B | $338.55 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $203.0B | $285.77 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $67.4B | $45.59 | Elliott J. Hill | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.41T | $364.96 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.47T | $581.01 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $327.9B | $77.86 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $177.3B | $102.10 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $198.0B | $182.96 | Srinivasan Gopalan | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $134.8B | $144.53 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $85.6B | $183.69 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $107.1B | $1086.28 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $148.4B | $210.19 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $38.3B | $87.84 | Christian H. Hillabra… | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $354.4B | $152.18 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $434.1B | $978.74 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $345.0B | $80.18 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $197.2B | $144.30 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $950.0B | $119.37 | John R. Furner | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $587.1B | $141.64 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $357.3B | $179.43 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $135.4B | $111.17 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $71.2B | $133.62 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $77.7B | $51.94 | Olivier Le Peuch | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $179.2B | $85.93 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $105.5B | $93.57 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $97.2B | $124.65 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $70.2B | $129.09 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $59.6B | $91.14 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — NEUTRAL (confidence 0.52)

> **中性偏防禦：唯科技領軍，tape 極窄選股優先**
> 
> 今天維持 60-75% 暴險但集中在 mega-cap 科技與便宜週期股 (工業/金融)，因為全場 11 板塊 uptrend 全數低於 0.34、僅科技 RS 為正——市場由少數權值股撐住；等下週 MU 財報與 Core PCE 確認方向，breadth 若再縮或 real rate 升破 2.3% 就降暴險。

### Key Takeaways
1. 科技仍是唯一 HOT — 但已現內部人淨賣 (0.474) 與 real rate 2.15% 估值逆風，加碼不追高、設停損
2. 工業 (0.330)、金融 (PE 20.2 + 曲線陡化)、原物料 (主題 62.7) 列 WARM，逢回分批、不齊追
3. Breadth 較昨日進一步收窄，市場頂部偵測進入黃色早期警示 (37.6)、FTD 已 day 49 老化 — 不擴張新題
4. 防禦/落後股 (能源、公用、必需消費、REIT) 維持低配或迴避，real rate 高壓長久期
5. 下週催化密集 (FDX 6/23、MU 6/24、Core PCE 6/25) — 留現金待方向確認

### Sector Actions
- **Overweight**: Technology (med) — 唯一正 RS 領軍，但內部人賣壓設停損
- **Wait**: Industrials (med) — breadth 最高但仍 <0.34，逢回布局
- **Wait**: Financials (med) — 估值便宜 + 曲線陡化，等催化
- **Neutral**: Materials (low) — 單一主題撐盤、佐證不足
- **Underweight**: Energy (high) — RS 最差 -18.5%、breadth 近全滅
- **Avoid**: Utilities (high) — breadth 0.037 墊底 + real rate 逆風

### Watch Next
- MU 美光記憶體財報 6/24 — 半導體與科技 HOT 論點關鍵 read-through
- Core PCE 6/25 (est 0.2% MoM) — 通膨/利率路徑，影響 real rate 與長久期估值
- real_rate_preferred 升破 2.30% → 科技/REIT/公用估值降評觸發點
- Breadth composite 若跌破 50 或 uptrend 全面再縮 → 降暴險至 60% 下緣
- Fed 銀行壓力測試 6/24 + FDX/PAYX 財報 6/23 — 金融與工業 WARM 驗證

---

## Top Actionable Themes

1. AI & Semiconductors
2. Robotics & Automation
3. Infrastructure & Construction
4. Defense & Aerospace

---

## HANDOFF TO INVESTMENT PROTOCOL

> Phase 0-1 完整重跑 (無 sector_intel；FTD/breadth/market_top/FRED cache 皆 fresh @20:57)。Prefetch 首跑 valuation+smart_money 撞 FMP 429，各 retry 1 次後成功。Tape 較 6/17 進一步收窄：全 11 板塊 uptrend_ratio 全數 <0.34 (最高工業 0.330)，僅科技 RS3m 為正 (+22.7%)，其餘全負 → 極端窄幅/權值股集中盤。決策樹 STEP G DEFENSIVE tripwire (COLD>=3, 共 6 COLD+1 AVOID) 觸發，但因 synthesized_exposure 60-75% (>=60)、FTD 確認、VIX 17/情緒中性、tail-risk 無 FRAGILE，PS 仲裁覆寫為 NEUTRAL-偏防禦 (confidence 0.52)：COLD 群為 RS 相對落後非派發/崩跌風險。科技 consensus_warning=TRUE 已由 DA 強力挑戰 (R4 real_rate 2.15>2.0 + R5 內部人 0.474<0.5)，挑戰被接受為 risk_flags，未推翻 HOT (動能多週期同向正、tail MODERATE)。R6/R7 未觸發。
