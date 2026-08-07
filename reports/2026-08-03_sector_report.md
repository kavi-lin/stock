# Sector Intelligence Report — 2026-08-03

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.58
> **Stance**: DEFENSIVE · **Cycle**: Early · **Generated**: 2026-08-03 22:30
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|
| Consumer_Discretionary | WARM | 74 | RS_5d +5.0% strongest re-acceleration · AMZN $3T milestone drove tape | ROBUST | XLY | consensus_warning, single_megacap_driver, real_rate_above_2pct, no_ftd_confirmation |
| Financials | WARM | 72 | RS_3m +6.0% and RS_20d +2.0% positive · PE 19.08 cheapest ex-Energy | ROBUST | XLF | consensus_warning, theme_late_stage, real_rate_above_2pct, negative_skew |
| Technology | WARM | 68 | AI theme Accelerating, heat 54.6 · Analyst revisions +289 highest | MODERATE | XLK | smart_money_divergence, momentum_fade, overbought_valuation, narrow_breadth, real_rate_above_2pct |
| Energy | WARM | 67 | uptrend_ratio 0.562 highest by far · RS_20d +10.0% strongest inflow | N/A | XLE | catalyst_reversal, geopolitical_de_escalation, real_rate_above_2pct |
| Communication | WARM | 60 | Analyst revisions +255 second highest · RS_5d +1.65% and RS_20d +0.91% turning | N/A | XLC | no_theme_coverage, weak_3m_relative_strength |
| Materials | WARM | 55 | Gold theme bullish, uncontested · uptrend rising, above MA10 | N/A | XLB | all_window_relative_weakness, thin_news_coverage |
| Healthcare | COLD | 49 | beat_rate 1.00, LLY FDA breakthrough · RS_3m +7.14% highest but fading | N/A | XLV | momentum_exhaustion, all_themes_bearish, defensive_in_risk_on |
| Industrials | COLD | 46 | CAT record $63B backlog, defense spend · But surprise_avg -0.037, only negative | N/A | XLI | negative_earnings_surprise, outflow, infrastructure_theme_bearish |
| Consumer_Staples | **AVOID** | 37 | FRED avoid list, Soft Landing regime · surprise_avg +0.036 weakest of 11 | N/A | XLP | fred_avoid_list, exposure_floor_forced_avoid, bearish_news, weakest_earnings_surprise |
| Real_Estate | **AVOID** | 37 | slope -0.0232 worst deterioration · uptrend 0.174 vs MA10 0.314 collapse | N/A | XLRE | participation_collapse, exposure_floor_forced_avoid, rate_sensitive, thin_news_coverage |
| Utilities | **AVOID** | 20 | uptrend 0.025 lowest of all 11 · RS -9.3% / -2.4% / -4.9% all negative | N/A | XLU | fred_avoid_list, lowest_participation, all_window_relative_weakness, bearish_dominant_theme |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 75-90% | Synthesized: 0-25% | Cycle: Early
FTD: RALLY_ATTEMPT (quality 0) | Market Top: 45.6 Orange (Elevated Risk) | Breadth: 71.0 Healthy
Sentiment: F&G [61.1 — Greed] | VIX: 16.22 | Put/Call: n/a | SPY RSI: 57.1
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors — Accelerating, heat 54.6, breadth_signal 86.0（但 XLK 尾部風險全場最高，主題有效不等於可加碼） · Quantum Computing — Accelerating, heat 46.7, maturity 38.8 · Gold & Precious Metals — Emerging, heat 29.6，Materials 唯一未被反向主題抵銷者

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Consumer_Discretionary | 43.17 | -1.69 | -4.6% | 0.261 | 🟢 OVERSOLD VALUE |
| Financials | 19.08 | -1.24 | +6.0% | 0.144 | 🟢 OVERSOLD VALUE |
| Technology | 41.9 | -0.82 | +3.8% | 0.166 |  |
| Energy | 19.78 | -0.44 | -5.0% | 0.174 |  |
| Communication | 22.43 | -1.36 | -9.0% | 0.158 | 🟢 OVERSOLD VALUE |
| Materials | 24.32 | -0.58 | -6.0% | 0.188 |  |
| Healthcare | 23.34 | -1.42 | +7.1% | 0.177 | 🟢 OVERSOLD VALUE |
| Industrials | 30.09 | -0.77 | +0.5% | 0.189 |  |
| Consumer_Staples | 29.37 | -1.29 | -2.9% | 0.213 | 🟢 OVERSOLD VALUE |
| Real_Estate | 28.56 | -2.45 | -2.6% | 0.209 | 🟢 OVERSOLD VALUE |
| Utilities | 26.54 | -0.61 | -9.3% | 0.193 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.92T | $271.58 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.23T | $311.21 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $331.0B | $331.96 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $192.3B | $270.64 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $61.7B | $41.71 | Elliott J. Hill | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.10T | $511.54 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $942.6B | $351.79 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $439.6B | $61.95 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $261.4B | $86.45 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $300.4B | $1018.38 | David Solomon | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.54T | $308.91 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.45T | $464.72 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $4.86T | $200.75 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.85T | $389.28 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $374.1B | $129.88 | Michael D. Sicilia | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $644.4B | $155.46 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $392.1B | $196.87 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $146.8B | $120.48 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $79.2B | $148.69 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $73.6B | $49.59 | Olivier Le Peuch | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.31T | $356.13 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.42T | $556.71 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $298.6B | $71.71 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $167.1B | $96.22 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $185.3B | $172.71 | Srinivasan Gopalan | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $221.3B | $478.38 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $82.7B | $340.85 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $90.0B | $62.63 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $65.7B | $294.89 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $78.1B | $277.63 | Christophe Beck | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.08T | $1148.50 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $376.3B | $414.40 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $617.8B | $256.35 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $443.2B | $250.88 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $321.6B | $130.22 | Robert Davis | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $373.6B | $360.07 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $375.3B | $814.81 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $290.1B | $215.22 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $77.0B | $243.05 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $173.5B | $292.13 | Vincenzo James Vena | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $343.5B | $144.49 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $422.1B | $951.89 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $376.9B | $87.59 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $190.6B | $139.56 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $884.9B | $111.20 | John R. Furner | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $134.9B | $144.61 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $80.8B | $173.36 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $100.6B | $1019.28 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $168.9B | $234.44 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $33.3B | $76.30 | Christian H. Hillabra… | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $181.3B | $86.92 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $108.8B | $94.54 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $97.8B | $125.43 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $69.6B | $127.85 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $57.9B | $88.55 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.58)

> **防禦：廣度健康但 FTD 未確認、派發日爆表，零 HOT 板塊**
> 
> 今天不加碼、維持低曝險，等訊號歸位再說。廣度雖回到健康區，但 FTD 未確認且 NASDAQ 25 日內累積 9 個派發日，這波漲勢缺資金確認。看到 FTD 成立或派發日消退，才把倉位拉回廣度建議的水準。

### Key Takeaways
1. 維持現金為主：三個曝險訊號取最保守值後上限只到 0-25%，不要拿廣度的 75-90% 當依據
2. 暫停所有新建倉：本場零 HOT 板塊，最高分的 Consumer_Discretionary 74 分仍差 1 分未達門檻
3. 清掉 Utilities、Consumer_Staples、Real_Estate：三者同時落在 FRED 迴避名單或參與度崩壞
4. 科技股只減不加：XLK 尾部風險全場最高（倉位乘數 0.75），16 家大型股內部人賣多於買（0.461）
5. 盯 8/7 非農：本週唯一會重定價利率路徑的事件，市場正在辯論 Warsh 是否被迫升息

### Sector Actions
- **Wait**: Consumer_Discretionary (high) — 分數最高但訊號牴觸，等 FTD 確認
- **Wait**: Financials (med) — 陡化利差利多，但主題已到晚期
- **Neutral**: Technology (med) — AI 主題強，內部人與尾部風險反向
- **Neutral**: Energy (low) — 參與度最廣但油價催化劑轉空
- **Avoid**: Utilities (high) — 參與度 0.025 全場最低，FRED 迴避
- **Avoid**: Consumer_Staples (med) — P&G 下修、消費信心走弱

### Watch Next
- 8/7 非農就業：預估 83k vs 前值 57k、失業率 4.3%，本週唯一 binary 重定價事件
- FTD 是否成立：rally_day_count 目前 3，觀察 day 4-7 是否出現放量突破
- NASDAQ 派發日回落：25 日窗現有 9 個，降到 5 個以下才算資金重新進場
- 8/5 ISM 服務業 PMI（預估 54.2）與 Non-Mfg Prices（前值 67.7）通膨黏著度
- XLK 內部人買賣比 0.461 是否在下期申報回升至 0.5 以上

---

## Devil's Advocate Challenges (Accepted 4/4)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Consumer_Discretionary — HOT | **Accepted** | News lane 自己承認催化劑是單一巨型股事件（Amazon 站上 $3T、AWS $1T 願景），並非板塊性獲利改善，這種個股驅動的漲勢極易在敘事降溫後迅速消退。同時大盤層級紀律訊號直接牴觸這個 HOT 判斷：FTD 尚未確認（quality_score 0、rally_day_count 僅 3），曝險被壓在 0-25%；market_top 綜合分 45.6（Orange, Elevated Risk），其中 distribution_days 子分 100/100「CRITICAL」（25 日窗 NASDAQ 9 個派發日、S&P 6 ... |
| Financials — HOT | **Accepted** | Financials 的 HOT 判斷只來自 FRED_Macro_Analyst 單一 lane（陡化利差敘事），Sector_Rotation、Theme_Intelligence、News_Catalyst 三條 lane 全數未挑選 Financials 為 HOT，屬孤證式收斂而非真正跨 lane 共識。Theme_Intelligence 更明確標記 Financials 主題 maturity 54.8，是全部 19 個主題中最高（最晚期），代表這個上漲敘事可能已被市場充分定價。 |
| Technology — HOT | **Accepted** | Sector_Rotation_Analyst 本身已標記 Technology 為典型動能耗盡：RS_3m +3.82% 惡化至 RS_20d −4.73%、RS_5d −1.30%，PE 41.90 為市場最貴、breadth 0.121 為最窄，與 Theme_Intelligence 的 HOT 判斷直接矛盾。Smart money 進一步佐證看空：16 家 mega-cap 樣本 insider_acquired_disposed_ratio 僅 0.461（< 0.5 門檻），senate_net_buy_30d 為 0，且本場 13F... |
| Energy — HOT | **Accepted** | News_Catalyst_Analyst 明確將 Energy 列為當日最看空板塊：伊朗降溫導致油價當日重挫，且 Berkshire Hathaway 減持 Chevron 是機構層級的實際拋售行為，與 Sector_Rotation 僅憑 uptrend 0.562、PE 19.78 等靜態指標形成直接衝突 —— 便宜可以更便宜，尤其當催化劑已經轉向。能源股對地緣政治/油價的高敏感度意味著 RS_20d +10.0% 這類資金流入結論可在數日內因單一事件反轉。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | news_positive_price_negative | reduce_exposure | 分析師調升淨值 +289 為全場最高、AI 主題 Accelerating（heat 54.6），但 RS_20d −4.73% 是 11 個板塊最差，uptrend_ratio 0.121 倒數第二，且 16 家大型股 insider ratio 僅 0.461。敘事與資金流反向。 |
| Energy | news_negative_price_positive | monitor | uptrend_ratio 0.562 全場最高、RS_20d +10.0% 最強，但伊朗降溫當日油價重挫、波克夏減持 Chevron。價格動能屬回顧性，催化劑已轉向。 |
| Healthcare | news_positive_price_negative | monitor | beat_rate 1.00 且 LLY 獲 FDA 突破性療法認定，但 4 個相關主題（Robotics / Obesity / Biotech / Healthcare & Pharma）全數 bearish，RS_3m +7.14% 已在 20d（−0.18%）與 5d（−2.72%）同向轉弱。 |
| Real_Estate | news_negative_price_positive | reduce_exposure | RS_20d +1.75% 為正，但 uptrend_ratio 自 MA10 的 0.314 崩落至 0.174、slope −0.0232 為全場最差惡化速度，新聞覆蓋僅 2 篇最薄。反彈缺乏參與度支撐。 |

---

## Top Actionable Themes

1. AI & Semiconductors — Accelerating, heat 54.6, breadth_signal 86.0（但 XLK 尾部風險全場最高，主題有效不等於可加碼）
2. Quantum Computing — Accelerating, heat 46.7, maturity 38.8
3. Gold & Precious Metals — Emerging, heat 29.6，Materials 唯一未被反向主題抵銷者
4. Financial Sector Concentration — Trending, maturity 54.8 為全部 19 主題最高＝晚期，追高風險升溫
5. Defense & Aerospace — Trending, maturity 44.9，受國防預算（飛彈/無人機/太空）題材支撐

---

## HANDOFF TO INVESTMENT PROTOCOL

> 盤前給 investment_protocol 的 handoff：本場零 HOT 板塊、stance DEFENSIVE、曝險上限 0-25%（由 FTD 未確認決定，非廣度）。個股層級請一律套 no-new-entry 預設，僅允許既有部位持有；Technology 個股額外套 0.75 倉位乘數（XLK tail_risk 30.7 + insider ratio 0.461）。Utilities / Consumer_Staples / Real_Estate 三個 AVOID 板塊的個股一律不進場。8/7 非農為本週唯一 binary 事件，之前不要重建曝險。
