# Sector Intelligence Report — 2026-07-31

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Early · **Generated**: 2026-07-31 22:46
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Financials | WARM | 77 | 1.03 | 全場唯一三窗口 RS 同為正：3M +6.0% / 20d +2.8% / 5d +0.7% · 30 天財報 beat_rate 1.00（n=12，樣本最大）、平均驚喜 +13.8% | ROBUST | XLF | signal_conflict_downgrade, fred_real_rate_conflict, thin_volume_confirmation |
| Consumer_Discretionary | WARM | 77 | 1.07 | AMZN AWS 帶動 Q2 超預期，5 日 RS +5.2% 為全場最強短窗 · PE z-score −1.78，估值處於一年低檔區 +5 | ROBUST | XLY | signal_conflict_downgrade, single_name_concentration, fred_real_rate_conflict |
| Materials | WARM | 69 | 1.03 | uptrend_ratio 0.269 但 10 日均線僅 0.179，slope +0.0152 為全場最陡改善 · LIN Q2 超預期並上調全年下緣，宣布投資 10 億美元亞利桑那半導體供應廠 | N/A | XLB | single_name_driven |
| Energy | WARM | 67 | 1.03 | uptrend_ratio 0.481 為全場最高，且 slope +0.0116 向上 · 20 日 RS +10.6% 全場最強 | N/A | XLE | binary_risk_within_48h, consensus_warning, thin_volume_confirmation |
| Consumer_Staples | WARM | 56 | 0.90 | 20 日 / 5 日 RS 均為正（+0.8% / +1.0%），slope 微幅向上 · PE z-score −1.31，估值 +5 | N/A | XLP | fred_avoid_list |
| Real_Estate | WARM | 50 | 0.96 | PE z-score −2.49 為全場最低，估值 +5 · 30 天平均財報驚喜 +32.0% 全場最高，EQIX AFFO 超預期 | N/A | XLRE | duration_risk_bear_steepening |
| Healthcare | COLD | 49 | 0.96 | R7 動能耗盡：3M RS +7.4% 但 20d −0.9%、5d −1.0% · 主題端最弱：Obesity & GLP-1（bearish heat 45.6）與 Healthcare & Pharma（bearish heat 34.9）雙壓 | N/A | XLV | momentum_exhaustion, guidance_cut_risk |
| Technology | COLD | 48 | 1.07 | uptrend_ratio 僅 0.117，全場倒數第二 — 指數強、個股極弱的典型背離 · R7 動能耗盡：3M RS +6.2% 但 20d −3.0%、5d −1.2% | N/A | XLK | momentum_exhaustion, low_uptrend_participation, late_stage_theme |
| Communication | **AVOID** | 47 | 1.03 | 3M RS −11.2% 為全場最差 · META Q2 後市場解讀為「積極 AI capex 坐實看空」，NFLX 已下跌 46% | N/A | XLC | exposure_floor_avoid_mandate, ai_capex_derating |
| Industrials | **AVOID** | 30 | 1.07 | 全場唯一 30 天平均財報驚喜為負（−3.7%），儘管 beat_rate 0.90 · RS 三窗口全負（3M −0.7% / 20d −2.3% / 5d −2.4%） | N/A | XLI | exposure_floor_avoid_mandate, negative_earnings_surprise, low_uptrend_participation |
| Utilities | **AVOID** | 26 | 0.90 | uptrend_ratio 0.062 為全場最低，僅約 6% 成分股處於上升趨勢 · 3M RS −7.8%、5 日 RS −3.8% 皆為全場最弱 | N/A | XLU | exposure_floor_avoid_mandate, fred_avoid_list, bearish_theme_pressure |

---

## Macro Context

```text
Market Regime: RISK_OFF | Breadth Ceiling: 75-90% | Synthesized: 0-25% | Cycle: Early
FTD: RALLY_ATTEMPT (quality 0) | Market Top: 46.7 Orange (Elevated Risk) | Breadth: 71.0 Healthy
Sentiment: F&G [53.4 — Neutral] | VIX: 18.15 | Put/Call: n/a | SPY RSI: 47.2
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Gold & Precious Metals（bullish, Trending, heat 34.0）— 美以對伊朗空襲升溫下的避險首選，代表股 NEM/AU/GFI · Nuclear Energy（bearish, heat 51.0 全場最高）— 空方動能最強主題，連帶壓制 Utilities 的 CEG/PEG · AI & Semiconductors（bullish 但 maturity 59.2）— 已屬生命週期後段，MSFT/AMZN 利多已反映，不宜追高

---

## Step 6 — FRED Regime Overlay

- **Regime**: Soft Landing (confidence 0.7)
- **Favor**: Technology, Industrials, Consumer Discretionary
- **Avoid**: Consumer Staples, Utilities
- **Velocity highlights**: T10Y2Y:accelerating, DGS10:accelerating, DFF:decelerating
- **Rationale**: Soft Landing regime, conf 0.7 → favor: Technology×1.072, Industrials×1.072, Consumer_Discretionary×1.072; avoid: Consumer_Staples×0.898, Utilities×0.898

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Financials | 19.09 | -1.25 | +6.0% | 0.204 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 42.36 | -1.78 | -5.5% | 0.335 | 🟢 OVERSOLD VALUE |
| Materials | 24.21 | -0.60 | -5.1% | 0.442 |  |
| Energy | 19.54 | -0.47 | -4.9% | 0.201 |  |
| Consumer_Staples | 29.37 | -1.31 | -2.0% | 0.275 | 🟢 OVERSOLD VALUE |
| Real_Estate | 28.56 | -2.49 | -1.7% | 0.331 | 🟢 OVERSOLD VALUE |
| Healthcare | 23.17 | -1.45 | +7.4% | 0.274 | 🟢 OVERSOLD VALUE |
| Technology | 41.98 | -0.80 | +6.2% | 0.275 |  |
| Communication | 22.17 | -1.42 | -11.2% | 0.152 | 🟢 OVERSOLD VALUE |
| Industrials | 29.86 | -0.83 | -0.7% | 0.161 |  |
| Utilities | 26.45 | -0.63 | -7.8% | 0.272 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.10T | $509.68 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $940.1B | $350.85 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $438.1B | $61.73 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $261.4B | $85.43 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $302.3B | $1024.86 | David Solomon | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.53T | $235.50 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.22T | $308.85 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $332.4B | $333.35 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $190.7B | $268.44 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $62.6B | $42.29 | Elliott J. Hill | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $235.3B | $508.64 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $83.7B | $344.84 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $91.2B | $63.44 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $66.8B | $300.20 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $78.6B | $279.34 | Christophe Beck | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $651.1B | $157.08 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $383.5B | $192.56 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $145.0B | $119.03 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $77.5B | $145.51 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $73.1B | $48.91 | Olivier Le Peuch | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $335.2B | $143.95 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $423.2B | $954.17 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $380.7B | $88.49 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $191.5B | $140.20 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $884.1B | $111.10 | John R. Furner | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $136.3B | $146.19 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $81.3B | $174.46 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $103.3B | $1047.53 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $169.8B | $235.63 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $33.4B | $76.51 | Christian H. Hillabra… | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.09T | $1155.27 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $382.8B | $421.47 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $616.5B | $255.82 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $455.1B | $257.61 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $320.6B | $129.79 | Robert Davis | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.90T | $333.43 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.35T | $451.10 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $4.72T | $195.04 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.85T | $387.84 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $367.4B | $127.56 | Michael D. Sicilia | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.04T | $333.66 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.37T | $539.03 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $304.7B | $73.17 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $166.9B | $96.14 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $185.9B | $173.34 | Srinivasan Gopalan | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $368.4B | $355.04 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $372.7B | $809.14 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $288.9B | $214.38 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $76.7B | $241.91 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $172.0B | $289.46 | Vincenzo James Vena | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $183.4B | $87.93 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $106.3B | $94.34 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $98.4B | $126.27 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $69.5B | $127.78 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $58.6B | $89.58 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.72)

> **防禦：反彈兩天但無 FTD 確認，先觀望**
> 
> 今天不新建倉、總曝險壓在兩成半以內；因為大盤只反彈兩天、還沒出現 FTD 確認，全市場也僅約兩成個股站上升趨勢。要等 FTD 成立或廣度回升，才值得轉積極。

### Key Takeaways
1. 壓低總曝險至 0-25%：FTD 僅在 RALLY_ATTEMPT 第 2 天、quality_score 0，反彈尚未取得技術確認
2. 不要被指數騙了：11 個板塊平均 uptrend_ratio 僅 0.225，個股廣度與指數強度嚴重背離
3. 今日無 HOT 板塊：Financials 與 Consumer_Discretionary 原判 HOT，因廣度與 FTD 的曝險建議相差 70 個百分點而降為 WARM
4. 全部 11 個板塊 ETF 量能都低於 20 日均量，07-30 的大漲是薄量反彈，不是資金回補
5. 把 08-07 非農（預估 9.1 萬 vs 前值 5.7 萬）當本週真正的方向決定點，之前的部位調整都算試單

### Sector Actions
- **Wait**: Financials (high) — 三窗口 RS 全正但量能僅 0.20 倍
- **Wait**: Consumer_Discretionary (med) — AMZN 單一股撐盤，廣度僅 0.211
- **Wait**: Energy (med) — OPEC 8/2 前不加碼，停損上移
- **Neutral**: Real_Estate (med) — 估值最低但長天期利率仍在上行
- **Avoid**: Utilities (high) — 廣度 0.062 全場最弱且 FRED 排除
- **Avoid**: Industrials (high) — 唯一 30 天負向財報驚喜 −3.7%
- **Avoid**: Communication (med) — 3M RS −11.2% 全場最差

### Watch Next
- 08-02 OPEC 會議：本週唯一 48 小時內的 binary 事件，直接決定 Energy 的 20 日 RS +10.6% 能否延續
- FTD 確認：需在 rally day 4-7 出現主要指數放量收漲逾 1.5%，成立才可把曝險由 0-25% 上調
- 廣度回升：11 板塊平均 uptrend_ratio 由 0.225 回到 0.35 以上，才視為反彈有基礎
- 08-07 非農與失業率（預估 4.3% vs 前值 4.2%）：在 FOMC 已移除前瞻指引、兩位官員主張升息的背景下，勞動市場數據是本週最大變數
- real rate 2.42% 若升破 2.75%，Financials 的淨利差多頭邏輯反轉為信用品質壓力

---

## Devil's Advocate Challenges (Accepted 0/4)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Energy — HOT | — | uptrend_ratio 0.481 與 20 日 RS +10.6% 屬實，但 5 日 RS 已翻負至 −2.0%、3M RS 為 −4.9%，所謂加速只是被前後兩個負值窗口夾住的極短區間。ETF 量能僅 20 日均量的 0.20 倍（與 XLF 並列全場最低），代表 20 日漲幅來自薄量而非信念買盤。多方催化劑（美以對伊朗空襲升溫、08-02 OPEC 會議）本質是雙向的地緣風險，不是單向的資金驅動。 |
| Consumer_Discretionary — HOT | — | 分數明確由 AMZN AWS 帶動的 Q2 超預期單一支撐，但板塊 uptrend_ratio 僅 0.211（11 個板塊倒數第三），代表多數非必需消費個股並未站上升趨勢，板塊分數卻讀到 77。3M RS −5.5%、20 日 RS −0.9%，只有 5 日 +5.2% 為正，而該反彈的 ETF 量能僅 20 日均量的 0.34 倍。FRED 自身的實質利率限制性邏輯（2.42% > 2.0%）本應壓抑利率敏感的非必需消費，FRED lane 卻未將其列入 COLD，是跨 lane 套用 macro overlay 的內部不一致。 |
| Financials — HOT | — | 77 的 HOT 分數倚賴 FRED 的淨利差擴張邏輯（實質利率 2.42% > 2.0% 限制性門檻、T10Y2Y +0.80 加速的 bear-steepening），但 ETF 量能僅 20 日均量的 0.20 倍，20 日 RS +2.8% 與 5 日 +0.7% 的改善未獲參與度背書。同一套 macro 背景在 07-29 造成道瓊重挫 1,100 點的「Fed 落後於曲線」恐慌，且 FOMC 剛移除前瞻指引、兩位官員異議主張更高利率 — 意味實質利率與殖利率曲線動態正進入更不可預測、更失序的階段，而非乾淨的 NIM 擴張軌道。整體市場 ... |
| Materials — HOT | — | News lane 的 Materials HOT 判定幾乎全建立在 LIN 的 beat-and-raise 與 10 億美元亞利桑那半導體廠，但板塊整體 RS 三窗口全負：3M −5.1%、20 日 −2.5%、5 日 −1.9%。單一個股催化劑把板塊分數推到 69、而該板塊自身相對強度全面為負、uptrend_ratio 僅 0.269，顯示這是 LIN 個股新聞被誤標為板塊輪動；1.00 的 beat_rate（n=9）是小而集中的樣本，可能掩蓋更廣泛的疲弱。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | — | — |  |
| Healthcare | — | — |  |
| Energy | — | — |  |
| Financials | — | — |  |
| Consumer_Discretionary | — | — |  |
| Materials | — | — |  |
| Industrials | — | — |  |

---

## Top Actionable Themes

1. Gold & Precious Metals（bullish, Trending, heat 34.0）— 美以對伊朗空襲升溫下的避險首選，代表股 NEM/AU/GFI
2. Nuclear Energy（bearish, heat 51.0 全場最高）— 空方動能最強主題，連帶壓制 Utilities 的 CEG/PEG
3. AI & Semiconductors（bullish 但 maturity 59.2）— 已屬生命週期後段，MSFT/AMZN 利多已反映，不宜追高
4. Utilities Defensive（bearish, Accelerating, heat 42.4）— 傳統防禦板塊反而是空方加速標的，防禦需求改以現金滿足
5. Memory / AI capex cost（Technology + Communication）— 記憶體成本上升侵蝕 AI 建置報酬，WDC 08-04、SNDK 08-05 財報為驗證點

---

## HANDOFF TO INVESTMENT PROTOCOL

> STALE cache 重跑：sector_intel.json mtime 看似新，但內部 generated_at=2026-07-31 07:18 距今約 15 小時，依 GLOBAL RULE 2 判定 STALE，完整重跑 Phase 0-1。phase_prefetch 首次執行時 valuation 與 smart_money 遭 FMP 429 rate limit（10 個平行任務同時打 FMP），已改序列重跑兩者，皆 rc=0。Phase 4a 四個 lane 全部回傳 subagent_isolated=true → PARALLEL_SUBAGENT，無 degraded agent。DA 預觸發計算：R4 命中（real_rate_preferred 2.42% > 2.0%，credit_stress 與 yield_curve_inverted 皆 false 故 real_rate_high 為最高優先項）；R5/R6/R7 對兩個 HOT 板塊未命中（Financials insider ratio 1.658、CD 1.200 皆遠高於 0.5 門檻；PT sample size 為 0；HOT 板塊未觸發動能耗盡）。R7 在 Technology 與 Healthcare 命中但兩者非 HOT，已記入其 risk_flags。PS 對 News lane 的兩處 sentiment 標籤做仲裁下修：Utilities 與 Real_Estate 由 bullish 改以 neutral 計分（標題內容為「無放緩跡象」「符合預期」與 AMT 利率敏感度警示，不足以支撐 bullish base），其餘照 lane 輸出。Energy 的 08-02 OPEC binary ×0.70 僅套用一次（rubric Step 5 與決策樹 STEP E 為同一規則），91.8 → 64.3。STEP G 因 signal_conflict=true 將 Financials(77) 與 Consumer_Discretionary(77) 由 HOT 降為 WARM，故今日 HOT 為零。STEP B 因 synthesized_exposure 中位 12.5% < 40% 強制三個 AVOID（Communication/Industrials/Utilities）。STEP F 未觸發（devils_advocate_accepted 非空）。STEP G.5 未觸發（FRED avoid 的 Consumer_Staples 與 Utilities 皆無 lane 提名 HOT）。Arbiter 走主模型單軌（Agent tool 存在高於 sonnet 的檔位，未進入 V4.67.0 的 2+1 降級模式）。Phase 3 WebSearch 用量 1/1（Case A 上限）。
