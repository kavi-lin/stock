# Sector Intelligence Report — 2026-07-16

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.6
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-07-16 11:51
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Real_Estate | WARM | 69 | 0.96 | 全場最高分：唯一純 1.0 權重 Trending 多頭主題（heat 57.0）+ 趨勢向上（slope +0.0034） · PE z-score -2.98 為全場最低（相對自身 1 年歷史極便宜），RS 短線轉強（20d +0.3%/5d +2.5%） | ROBUST | XLRE | consensus_warning, rate_headwind, theme_maturity_late |
| Energy | WARM | 69 | 1.04 | 20d slope 全場最陡正值 +0.0067，RS 由 20d +3.0% 加速至 5d +4.2% · 催化明確：Chevron 伊拉克油田 MOU、柴油庫存驟降恐重燃通膨、AI 電力需求 | ROBUST | XLE | momentum_reversal_risk, highest_tail_risk_of_checked |
| Healthcare | WARM | 61 | 0.96 | 廣度全場第一（0.403）且 RS20d +5.7% 最強，UNH 財報後上漲 · 催化密集：Merck 首款口服降膽固醇藥 FDA 核准、Lilly 28 億美元收購 Atai Beckley | ROBUST | XLV | overbought, theme_divergence |
| Financials | WARM | 57 | 1.04 | 4 lane 中 3 個列 HOT：唯一統計穩健財報樣本（n=8、beat 100%、surprise +18.2%） · JPM 股票交易營收 +86% 並上調全年指引；PE 19.10、z-score -1.32 不貴 | N/A | XLF | narrow_breadth, theme_lane_dissent |
| Utilities | COLD | 47 | 0.89 | 趨勢向上（slope +0.0049）且防禦需求回流，但 RS3m -9.0% 為全場倒數第二 · FRED Soft Landing regime 明確列為 avoid → ×0.888 壓抑分數 | N/A | XLU | fred_avoid, theme_divergence |
| Industrials | COLD | 45 | 1.08 | Theme 與 FRED 兩 lane 列 HOT，但價格行為完全背離：20d slope -0.0161 為全場最陡下降 · RS 三週期全負（3m -2.7% / 20d -0.6% / 5d -1.1%），廣度僅 0.157（r8） | N/A | XLI | steepest_downtrend, macro_vs_tape_divergence |
| Consumer_Staples | COLD | 41 | 0.89 | 零售支出轉向必需品為順風，RS5d +3.0% 短線最強之一 · 估值加分 +5（PE z-score -1.37 且廣度 0.119 < 0.3 = 超賣價值） | N/A | XLP | fred_avoid, weak_breadth |
| Communication | COLD | 39 | 1.04 | Netflix 今日盤後財報為 48 小時內二元風險 → 分數 ×0.70 · RS3m -10.8% 為全場最差；但估值加分 +5（z-score -1.39 且廣度 0.239 < 0.3） | N/A | XLC | binary_risk_within_48h, worst_3m_relative_strength |
| Materials | **AVOID** | 39 | 1.04 | 廣度 0.110 為全場最低（r11），RS3m -8.8% / RS20d -4.1% 中長期同步走弱 · 新聞覆蓋僅 3 篇（全場最少），催化真空 | N/A | XLB | worst_breadth, exposure_floor_avoid |
| Technology | **AVOID** | 38 | 1.08 | 動能耗盡確認：RS3m +10.7%（全場唯一顯著正值）但 RS20d -5.0% / RS5d -4.2% 同步轉負 · 內部人淨賣（ratio 0.45 < 0.5）+ 參議員近 30 日淨賣 -3；實質利率 2.34% 壓抑長久期估值 | N/A | XLK | momentum_exhaustion, smart_money_divergence, real_rate_pressure, theme_net_bearish, exposure_floor_avoid |
| Consumer_Discretionary | **AVOID** | 31 | 1.08 | 全場最低分：PE 50.46 最貴，RS3m -8.1%，主題 Retail & Consumer 空頭（32.6）無多頭抵銷 · 三重需求逆風：零售支出轉向必需品、房貸利率 2026 新高、成屋銷售 -5.4% | N/A | XLY | expensive_valuation, demand_weakening, macro_vs_tape_divergence, exposure_floor_avoid |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 60-75% | Synthesized: 0-25% | Cycle: Late
FTD: CORRECTION (quality 0) | Market Top: 45.2 Orange (Elevated Risk) | Breadth: 58.0 Neutral
Sentiment: F&G [59.9 — Neutral] | VIX: 16.46 | Put/Call: n/a | SPY RSI: 55.1
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Real Estate Sector Concentration（Trending, heat 57.0 — 唯一純權重多頭主題，惟 maturity 55.7 偏擁擠） · Nuclear Energy（Emerging, heat 35.9 — Energy／Utilities 交集，早期） · Gold & Precious Metals（Emerging, heat 35.0 — Materials 板塊唯一支撐）

---

## Step 6 — FRED Regime Overlay

- **Regime**: Soft Landing (confidence 0.77)
- **Favor**: Technology, Industrials, Consumer Discretionary
- **Avoid**: Consumer Staples, Utilities
- **Velocity highlights**: DGS10:accelerating, DFF:decelerating, CPIAUCSL:decelerating
- **Rationale**: Soft Landing regime, conf 0.77 → favor: Industrials×1.079, Technology×1.079, Consumer_Discretionary×1.079; avoid: Utilities×0.888, Consumer_Staples×0.888

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Real_Estate | 28.3 | -2.98 | -3.0% | 0.508 |  |
| Energy | 18.82 | -0.55 | -5.0% | 0.506 |  |
| Healthcare | 23.61 | -1.51 | +2.2% | 0.76 |  |
| Financials | 19.1 | -1.32 | +1.0% | 0.527 |  |
| Utilities | 24.97 | -0.82 | -9.0% | 0.449 |  |
| Industrials | 29.71 | -0.98 | -2.7% | 0.534 |  |
| Consumer_Staples | 29.49 | -1.37 | -1.7% | 0.629 | 🟢 OVERSOLD VALUE |
| Communication | 23.09 | -1.39 | -10.8% | 0.492 | 🟢 OVERSOLD VALUE |
| Materials | 25.15 | -0.47 | -8.8% | 0.414 |  |
| Technology | 42.59 | -0.78 | +10.7% | 0.494 |  |
| Consumer_Discretionary | 50.46 | -0.97 | -8.1% | 0.424 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $133.8B | $143.53 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $78.5B | $168.60 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $100.9B | $1022.60 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $164.6B | $233.24 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $34.7B | $79.43 | Christian H. Hillabra… | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $598.9B | $144.49 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $361.7B | $181.62 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $135.8B | $111.46 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $73.2B | $137.43 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $71.1B | $47.57 | Olivier Le Peuch | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.09T | $1156.46 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $380.1B | $418.59 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $594.6B | $247.00 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $431.5B | $244.22 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $305.3B | $123.60 | Robert Davis | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.05T | $488.97 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $929.8B | $347.02 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $437.3B | $61.62 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $267.8B | $87.52 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $339.9B | $1152.25 | David Solomon | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $185.9B | $89.12 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $106.6B | $94.59 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $96.9B | $124.32 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $72.1B | $132.50 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $60.7B | $92.79 | Jeffrey Walker Martin | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $376.4B | $360.26 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $421.1B | $914.09 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $263.8B | $195.88 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $70.6B | $222.84 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $171.2B | $288.35 | Vincenzo James Vena | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $344.7B | $148.01 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $406.5B | $916.54 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $354.7B | $82.44 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $185.0B | $135.40 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $895.4B | $112.52 | John R. Furner | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.49T | $370.92 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.73T | $681.31 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $310.2B | $73.67 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $168.7B | $97.17 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $203.0B | $187.62 | Srinivasan Gopalan | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $237.8B | $514.15 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $82.0B | $332.41 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $87.7B | $60.99 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $65.4B | $293.87 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $76.1B | $270.26 | Christophe Beck | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.81T | $327.50 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $2.94T | $395.63 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.15T | $212.50 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.88T | $394.28 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $381.8B | $132.53 | Michael D. Sicilia | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.74T | $254.96 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.48T | $394.35 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $340.6B | $341.56 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $188.2B | $264.94 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $63.3B | $42.78 | Elliott J. Hill | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.6)

> **防禦站位：底部訊號未確認、廣度極窄，零板塊達積極進場門檻**
> 
> 今天守多於攻：市場仍在修正、底部訊號尚未確認，11 個板塊沒有一個夠格積極進場；真要動手只在地產、能源、醫療、金融四個板塊選股，等 FTD 確認或實質利率回落再談加碼。

### Key Takeaways
1. 採防禦站位：底部訊號(FTD)顯示仍在修正、建議曝險 0-25%，與廣度給的 60-75% 嚴重打架，取最保守值
2. 認清廣度極窄：11 板塊僅 3 個處於上升趨勢，平均上升比僅 0.216，指數靠少數龍頭撐
3. 科技降至迴避：3 個月相對強弱 +10.7% 但 20 日 -5.0%、5 日 -4.2%，動能耗盡且內部人淨賣、實質利率 2.34% 壓估值
4. 只在地產、能源、醫療、金融四個板塊選股，且都不追高——醫療已過熱、能源 3 個月動能仍落後
5. 留意 Fed 官員轉鷹：Dallas Fed Logan 公開呼籲「小幅」升息，房貸利率已創 2026 新高

### Sector Actions
- **Wait**: Real_Estate (med) — 主題最強且估值極低，但利率逆風未解
- **Wait**: Energy (med) — 短線動能最強，惟 3 個月仍落後
- **Neutral**: Healthcare (med) — FDA/併購催化實在，但已過熱等回檔
- **Neutral**: Financials (med) — 財報最扎實，惟廣度未跟上靠龍頭撐
- **Avoid**: Technology (high) — 動能耗盡+內部人淨賣+實質利率壓估值
- **Avoid**: Consumer_Discretionary (med) — PE 50 最貴，需求轉向必需品

### Watch Next
- Netflix 今日盤後財報 — Communication 板塊 48 小時內二元風險，財報落地前不進場
- FTD 是否於 rally day 13 之後確認 — 決定曝險能否從 0-25% 上調
- 7/17 Housing Starts 與 Building Permits — 地產板塊多頭論點的證偽點
- 7/17 Michigan 消費者信心(est 51 vs prev 49.5) — 驗證非必需消費需求是否止穩
- 實質利率是否回落至 2.0% 以下 — 科技與地產估值壓力的解除條件

---

## Devil's Advocate Challenges (Accepted 3/4)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Real_Estate — HOT | **Accepted** | 三方向共識建立在落後指標上：pe_zscore_1y -2.98 為統計異常低點，但 RS3m 仍 -3.0% 尚未轉正，RS20d +0.3%/RS5d +2.5% 更可能只是短線反彈，且 ETF vol ratio 20d 僅 0.51（量能萎縮）缺乏成交量確認。同時房貸利率創 2026 新高、成屋銷售 -5.4%、Fed Logan 呼籲升息三則逆風齊發，直擊 REIT 資金成本與需求面；real_rate 2.34% > 2.0% threshold 且 DGS10 加速，對長存續期地產資產是結構性逆風；theme maturity 55.... |
| Financials — HOT | Rejected | 三 lane 看多理由是 RS 三週期轉強與財報 beat 100% (n=8, surprise +18.2%)，但掩蓋了 uptrend_ratio 僅 0.320、板塊 slope -0.0042（下降），代表財報光環尚未轉化為廣度改善，仍靠 JPM 等少數龍頭撐盤。smart money 分歧：senate_net_buy_30d -1、institutional 13F 全數 null 機構部位不可見；儘管 insider ratio 1.60 方向偏多，三方向看多敘事完全建立在財報與 FRED real_rate override 兩個... |
| Energy — HOT | **Accepted** | Energy 是受檢三者中 tail_risk_score 26.0 最高、maxDD 14.98% 最深者，卻被列為首選 HOT，理由僅是短線 RS20d→RS5d 加速 (+3.0%→+4.2%)；但 RS3m -5.0% 代表 3 個月動能仍明顯落後，短線加速很可能只是下降趨勢中的技術性反彈。uptrend_ratio 僅 0.228 與「唯一 Up trend」敘事存在內部矛盾 — 多數個股尚未確立上升趨勢。real_rate 2.34% > 2.0% 亦推高資本支出型產業的實質資金成本。 |
| Industrials — HOT | **Accepted** | Theme 與 FRED 同列 HOT，但技術面呈現全場最陡下降惡化：uptrend_ratio 僅 0.157 (r8)、20d-slope -0.0161 為全場最陡、RS 三週期全負 (-2.7%/-0.6%/-1.1%)。指標股 GE 財報 beat 仍因供應鏈與估值疑慮遭賣壓，PE_ttm 29.71 偏貴。FRED 用 real_rate override 護航，但 real_rate 2.34% > 2.0% 同時推高資本財重資產產業的資金成本，override 論述自我矛盾。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | news_negative_price_positive | reduce_exposure | RS3m +10.7% 仍為全場最強，但 RS20d -5.0% / RS5d -4.2% 已轉負，且晶片股回檔、Oracle -33%、內部人淨賣（ratio 0.45）同步出現 — 3 個月的強勢是滯後訊號。 |
| Industrials | news_positive_price_negative | monitor | Theme（Sector Concentration Trending）與 FRED（base favor）雙雙看多，但 20d slope -0.0161 為全場最陡下降、RS 三週期全負，GE 財報 beat 仍遭賣壓 — 模型看多與價格行為背離。 |
| Real_Estate | news_positive_price_negative | monitor | PLD 財報 beat 且主題 heat 57.0 最高，但房貸利率創 2026 新高、成屋銷售 -5.4%、Fed 官員轉鷹 — 個股利多與板塊總體逆風並存。 |

---

## Top Actionable Themes

1. Real Estate Sector Concentration（Trending, heat 57.0 — 唯一純權重多頭主題，惟 maturity 55.7 偏擁擠）
2. Nuclear Energy（Emerging, heat 35.9 — Energy／Utilities 交集，早期）
3. Gold & Precious Metals（Emerging, heat 35.0 — Materials 板塊唯一支撐）

---

## HANDOFF TO INVESTMENT PROTOCOL

> DEFENSIVE：無 HOT 板塊、synthesized_exposure 0-25%（FTD CORRECTION 主導，與廣度 60-75% 衝突 55pp）。investment_protocol 若要選股，僅限 Real_Estate／Energy／Healthcare／Financials 四個 WARM，且需個股層級 FTD 或催化確認；Technology／Consumer_Discretionary／Materials 列 AVOID 不建新倉。
