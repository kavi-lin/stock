# Sector Intelligence Report — 2026-07-29

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.81
> **Stance**: DEFENSIVE · **Cycle**: Early · **Generated**: 2026-07-29 22:40
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Financials | WARM | 81 | 1.03 | RS vs SPY 三窗口全正：3M +6.67% / 20d +7.90% / 5d +3.36%，資金持續流入 · PE 19.1x、pe_zscore_1y -1.261 — 全場第二便宜且低於自身一年均值 | ROBUST | XLF | signal_conflict_downgrade, consensus_crowding |
| Energy | WARM | 75 | 1.03 | 上升股比 0.401 全場最高（均值 0.234） · RS 20d +12.57% 為全場最強，動能由負轉正 | ROBUST | XLE | signal_conflict_downgrade, earnings_binary_xom, theme_maturity_late |
| Healthcare | WARM | 70 | 0.97 | RS vs SPY 三窗口全正且幅度最大：3M +12.97% / 20d +6.95% / 5d +6.53% · 財報 n=6 全數 beat，平均驚喜 +10.6%，分析師調升淨額 +141 | SKIPPED_CAPACITY_LIMIT | XLV | — |
| Consumer_Staples | WARM | 65 | 0.90 | RS 20d +6.68% / 5d +5.14%，短窗資金流入明確（防禦輪動 CRITICAL 的直接受益者） · 上升股比 0.221 高於 ma10 0.156 且斜率為正，內部廣度在改善 | SKIPPED_CAPACITY_LIMIT | XLP | fred_rotation_avoid |
| Materials | WARM | 63 | 1.03 | 上升股比 0.207 大幅高於 ma10 0.155，斜率 +0.0098 為全場最陡之一 · RS 20d +3.21% / 5d +3.32% 同向轉正，3M -2.77% 的落後正在收斂 | SKIPPED_CAPACITY_LIMIT | XLB | — |
| Consumer_Discretionary | WARM | 52 | 1.07 | 上升股比 0.248 顯著高於 ma10 0.199、斜率 +0.0105，內部廣度是全場改善最快之一 · pe_zscore_1y -1.748 為全場第二低，估值壓縮已深 | SKIPPED_CAPACITY_LIMIT | XLY | weak_earnings_beat_rate |
| Industrials | COLD | 47 | 1.07 | 唯一平均財報驚喜為負的板塊（-4.2%，n=9），beat_rate 0.889 但獲利品質下滑 · CAT 遭降評且理由直指 AI 資本支出排擠傳統工業訂單 | SKIPPED_CAPACITY_LIMIT | XLI | negative_earnings_surprise, macro_theme_divergence |
| Communication | COLD | 45 | 1.03 | META 今晚 AMC 財報為 48 小時內二元事件（已套用 ×0.70 二元風險折減） · RS 3M -9.05% 為全場最差，僅短窗（20d +3.39%）微幅回穩 | SKIPPED_CAPACITY_LIMIT | XLC | binary_risk_within_48h, ai_capex_scrutiny |
| Real_Estate | **AVOID** | 44 | 0.97 | FRED real_rate_high 調整明確將 Real Estate 列入 lower 名單（實質利率 2.43% > 2.0% 門檻，DGS10 加速） · FOMC 點陣圖為今日 48 小時內二元事件，長存續期資產首當其衝（已套用 ×0.70） | SKIPPED_CAPACITY_LIMIT | XLRE | binary_risk_within_48h, fred_real_rate_headwind, exposure_floor_avoid |
| Technology | **AVOID** | 29 | 1.07 | NASDAQ/QQQ 已回檔 -9.4% 進入修正，S&P 500 反彈失敗(-2.4%)，無跟進日確認 · 動能耗盡最明確：RS 3M +3.83% 但 20d -9.71% / 5d -4.57% | SKIPPED_CAPACITY_LIMIT | XLK | binary_risk_within_48h, momentum_exhaustion, fred_real_rate_headwind, exposure_floor_avoid, insider_distribution |
| Utilities | **AVOID** | 23 | 0.90 | 上升股比 0.086 全場墊底，低於 ma10 0.132 且斜率 -0.0074（唯一內部廣度崩壞的板塊） · 主題面最惡：Nuclear Energy(bearish 52.60/Trending) + Utilities Defensive(bearish 49.66/Accelerating) | SKIPPED_CAPACITY_LIMIT | XLU | binary_risk_within_48h, fred_rotation_avoid, macro_theme_divergence, weakest_breadth |

---

## Macro Context

```text
Market Regime: RISK_OFF | Breadth Ceiling: 60-75% | Synthesized: 0-25% | Cycle: Early
FTD: CORRECTION (quality 0) | Market Top: 51.7 Orange (Elevated Risk) | Breadth: 59.5 Neutral
Sentiment: F&G [50.4 — Neutral] | VIX: 19.31 | Put/Call: n/a | SPY RSI: 44.1
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: 價值/防禦輪動：Healthcare、Financials、Consumer_Staples 的 RS 三窗口全正，且 PE zscore 皆低於自身一年均值 · 長存續期折價：實質利率 2.43% > 2% 門檻，直接壓抑 Technology(PE 40.6x) 與 Real_Estate(zscore -2.505) · 能源短線動能：20 日 RS +12.57% 全場最強，OPEC+ 暫停增產 + XOM 07-31 財報為催化劑

---

## Step 6 — FRED Regime Overlay

- **Regime**: Soft Landing (confidence 0.66)
- **Favor**: Technology, Industrials, Consumer Discretionary
- **Avoid**: Consumer Staples, Utilities
- **Velocity highlights**: DGS10:accelerating, DFF:decelerating, CPIAUCSL:decelerating
- **Rationale**: Soft Landing regime, conf 0.66 → favor: Technology×1.068, Consumer_Discretionary×1.068, Industrials×1.068; avoid: Consumer_Staples×0.904, Utilities×0.904

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Financials | 19.1 | -1.26 | +6.7% | 0.226 | 🟢 OVERSOLD VALUE |
| Energy | 19.54 | -0.47 | -1.1% | 0.348 |  |
| Healthcare | 24.08 | -1.34 | +13.0% | 0.253 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 29.81 | -1.11 | +1.8% | 0.255 | 🟢 OVERSOLD VALUE |
| Materials | 24.96 | -0.46 | -2.8% | 0.234 |  |
| Consumer_Discretionary | 42.68 | -1.75 | -7.4% | 0.147 | 🟢 OVERSOLD VALUE |
| Industrials | 29.48 | -0.97 | +1.5% | 0.235 |  |
| Communication | 22.21 | -1.43 | -9.0% | 0.158 | 🟢 OVERSOLD VALUE |
| Real_Estate | 28.97 | -2.50 | +1.1% | 0.187 |  |
| Technology | 40.58 | -1.16 | +3.8% | 0.224 | 🟢 OVERSOLD VALUE |
| Utilities | 26.34 | -0.64 | -5.0% | 0.212 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.11T | $512.37 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $957.4B | $357.31 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $444.4B | $62.62 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $265.8B | $86.87 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $304.8B | $1033.34 | David Solomon | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $635.0B | $153.20 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $373.8B | $187.71 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $139.0B | $114.10 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $74.4B | $139.64 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $74.7B | $49.98 | Olivier Le Peuch | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.15T | $1222.61 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $389.4B | $428.79 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $642.8B | $266.73 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $465.5B | $263.48 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $325.6B | $131.84 | Robert Davis | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $346.4B | $148.75 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $428.7B | $966.58 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $379.8B | $88.27 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $195.1B | $142.86 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $900.1B | $113.10 | John R. Furner | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $236.5B | $511.18 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $87.4B | $354.27 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $88.6B | $61.64 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $65.2B | $292.85 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $79.6B | $282.90 | Christophe Beck | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.48T | $230.86 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.21T | $307.44 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $343.5B | $344.47 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $194.0B | $273.02 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $63.7B | $43.05 | Elliott J. Hill | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $377.2B | $363.59 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $387.3B | $840.85 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $294.6B | $218.58 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $78.3B | $247.05 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $174.9B | $294.45 | Vincenzo James Vena | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.04T | $333.71 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.51T | $593.41 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $301.4B | $72.39 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $171.7B | $98.89 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $195.6B | $182.39 | Srinivasan Gopalan | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $137.2B | $147.12 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $79.9B | $171.50 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $102.1B | $1034.86 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $171.9B | $243.57 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $33.1B | $75.75 | Christian H. Hillabra… | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.99T | $340.08 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $2.92T | $393.35 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $4.77T | $197.01 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.81T | $380.91 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $345.6B | $119.99 | Michael D. Sicilia | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $186.2B | $89.28 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $109.1B | $96.78 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $100.8B | $129.24 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $72.4B | $133.02 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $59.2B | $90.56 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.81)

> **防禦：科技領跌修正未止，資金轉向價值與防禦**
> 
> 今天不加碼、先守住現金：NASDAQ 已回檔 9.4%、機構分佈賣壓沉重，但醫療與金融的資金流仍在。等 FOMC 記者會定調、科技股止穩後再談進場。

### Key Takeaways
1. 壓低總曝險至 25% 以下：FTD 仍判定 CORRECTION、無跟進日確認，S&P 500 反彈失敗(-2.4%)、NASDAQ 回檔 9.4%
2. 避開科技與 REIT：實質利率 2.43% 突破 2% 門檻，長存續期折現壓力最大；科技上升股比僅 0.114、內部人買賣比 0.462 全場唯一低於 0.5
3. 保留金融與能源觀察倉但不追價：分數最高(81/75)，惟三訊號分歧使其降為 WARM，等 FOMC 後再確認
4. 今晚同時盯 Powell 記者會與 META 財報：兩者皆為 48 小時內二元事件
5. 留意等權與權值背離：平均個股仍創高但 NASDAQ 修正，若廣度 8MA 跌破 200MA 0.613 則轉為全面防禦

### Sector Actions
- **Overweight**: Healthcare (med) — RS 三窗全正，財報 6 戰全勝
- **Wait**: Financials (med) — 分數最高但訊號分歧，不追價
- **Wait**: Energy (med) — 20 日 RS +12.6%，等 XOM 財報
- **Avoid**: Technology (high) — 回檔 9.4%，上升股比全場最低
- **Avoid**: Real_Estate (med) — 實質利率 2.43% 壓抑長存續期
- **Avoid**: Utilities (high) — 上升股比 0.086 墊底且主題最空

### Watch Next
- FOMC 決議與 Powell 記者會（今日 14:00 ET）：點陣圖若上調終點利率，科技與 REIT 續殺
- META 財報（今晚 AMC）：資本支出指引是 AI 敘事的下一個壓力測試
- Core PCE MoM（明日 08:30 ET，估 0.2% vs 前值 0.3%）：低於預期才可能鬆綁實質利率壓力
- NASDAQ 能否守住回檔低點並做出跟進日（FTD）—— 這是轉多的唯一機械條件
- 廣度 8MA 0.677 是否跌破 200MA 0.613：跌破代表等權市場也開始鬆動

---

## Devil's Advocate Challenges (Accepted 3/4)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Financials — HOT | Rejected | Financials 是唯一三相位全多（Phase1 INFLOW + Phase2 bullish/Trending + Phase3 bullish）的板塊，而同日 distribution_days 與 defensive_rotation 皆為 CRITICAL(100)、signal_conflict=TRUE（55pp 分歧）、market_top 51.7 Orange。跨相位一致共識與臨界分佈訊號同時出現，是典型擁擠交易特徵而非持久性確認。 |
| Utilities — HOT | **Accepted** | Utilities 僅 News lane 憑單一資本支出新聞提為 HOT，Rotation lane 列 COLD、Theme lane 判定為最偏空板塊、FRED 明列 sector_rotation_avoid。上升股比 0.086 為全 11 板塊最低（其餘介於 0.114–0.401），RS_3M -5.01% 為倒數第二。單一新聞稿無法抵銷全場最差的內部廣度加上三 lane 的宏觀迴避共識。 |
| Real_Estate — HOT | **Accepted** | Rotation lane 的多方論據為 RS 三窗全正(+1.05/+5.62/+3.44%)搭配 PE zscore -2.505，但 FRED lane 明列 COLD，因為當前生效的 real_rate_high 覆蓋規則（real_rate_preferred 2.43% > 2.0% 門檻、DGS10 加速）逐字將 Real Estate 列入 adjustments.lower。這是具名的結構性衝突而非推論；在實質利率上行環境中，長存續期資產的低 PE zscore 較可能是合理的結構性壓縮而非被忽略的便宜貨。 |
| Energy — HOT | **Accepted** | Energy 多方論據完全依賴短窗 RS 翻轉：RS_3M 仍為負(-1.14%)，僅在 20d/5d 轉正，且財報 beat 樣本僅 n=2，是所有被提名 HOT 板塊中最薄的。Theme lane 自身將 Oil & Gas 標記為 stage=Mature、maturity 63.50、confidence=Low，而全部 18 個主題皆為 Low confidence（5 多 / 13 空）。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Utilities | — | — |  |
| Real_Estate | — | — |  |
| Industrials | — | — |  |
| Consumer_Discretionary | — | — |  |

---

## Top Actionable Themes

1. 價值/防禦輪動：Healthcare、Financials、Consumer_Staples 的 RS 三窗口全正，且 PE zscore 皆低於自身一年均值
2. 長存續期折價：實質利率 2.43% > 2% 門檻，直接壓抑 Technology(PE 40.6x) 與 Real_Estate(zscore -2.505)
3. 能源短線動能：20 日 RS +12.57% 全場最強，OPEC+ 暫停增產 + XOM 07-31 財報為催化劑
4. AI capex 紀律：hyperscaler 舉債推升殖利率、投資人要求資本支出自律，半導體正測試支撐
5. 等權 vs 權值背離：平均個股創新高但 NASDAQ 修正 9.4% — 這是本次掃描三訊號分歧的根源

---

## HANDOFF TO INVESTMENT PROTOCOL

> V1.4 完整 Phase 0-5 執行。快取判定 STALE（前次 sector_intel 為 2026-07-21，內部 generated_at 距今 >3h），故完整重跑 Phase 0-1。Phase 0 四層 cache 全 FRESH（breadth/ftd/market_top age 2.6h、fred 0.5h）。phase_prefetch 首輪 valuation 與 smart_money 遭 FMP HTTP 429（9 路並行造成 rate limit），改為循序重跑後兩者皆 rc=0，資料完整無降級。Phase 2 theme-detector cache 過期，重跑產出 18 主題（5 多 / 13 空，confidence 全數 Low）。Phase 3 general_news cache available=true 且已涵蓋當日 narrative，依 Case A 規則跳過 Step 5 WebSearch。Phase 4a 四 lane 全數 PARALLEL_SUBAGENT 回傳且 subagent_isolated=true，degraded_agents 為空。核心矛盾：三訊號曝險分歧達 55pp（breadth 60-75% vs FTD 0-25% vs market_top 60-75%），根源是等權個股創新高而 NASDAQ 權值指數回檔 9.4%，屬真實市場背離而非資料錯誤，故 signal_conflict=true 且取最保守值 0-25%。
