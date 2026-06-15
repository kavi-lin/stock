# Sector Intelligence Report — 2026-06-08

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-06-08 21:19
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Technology | WARM | 74 | 1.00 | 唯一正向 3M RS (+21.6%) 與最高 uptrend 0.232，獨力撐起整個窄幅大盤；AI/Quantum/Robotics 三大 Trending 主題 (heat ~74) 全壓 Technology 一個板塊 · 但 insider acq/disp 0.47 (<0.5，11 板塊最低) = 內部人對著強勢分批出貨；rs5d 已轉 -3.1% (rs20d 仍 +5.4%) 為首道裂縫 | MODERATE | XLK | smart_money_divergence, concentration_risk, binary_risk_within_48h, rate_sensitive_long_duration, momentum_5d_rollover, signal_conflict |
| Industrials | WARM | 52 | 1.00 | uptrend 0.201 為 Tech 以外最高；Space (58.6)/Defense (44.7)/Industrials concentration (45.4) 主題群支撐，beat_rate 1.00 · 但 RS3m -7.2% 為負，主題多屬 Mature 末段；Honeywell aerospace 拆分為個股催化 | N/A | XLI | late_cycle_mature_themes, negative_rs3m |
| Real_Estate | COLD | 49 | 1.00 | uptrend 0.221 (次高) + 「降息受益」敘事 + 估值便宜 (PE_z -1.61，+5 penalty) · 但長久期 REIT 對 6/10 CPI 最敏感，raw 49 已屬 COLD，binary 折價 ×0.70→34 進一步壓低；real_rate 2.1 restrictive 為逆風 | N/A | XLRE | binary_risk_within_48h, rate_sensitive_long_duration, negative_rs3m |
| Financials | COLD | 44 | 1.00 | 估值便宜 (PE_z -1.44，+5 penalty) + insider 1.22；FRED real_rate_high overlay 理論偏好 · 但主題偏空 (Financial Services & Banks 42.0 bearish)、RS3m -6.3%、CPI binary 折價 (利率重定價雙面刃) | N/A | XLF | binary_risk_within_48h, bearish_theme, negative_rs3m |
| Energy | COLD | 43 | 1.00 | Clean Energy (51.3)/Oil&Gas (38.1) 主題 + SLB 海底訂單催化；insider 1.14 · 但 PE_z +1.31 偏貴、RS3m -7.8%、uptrend 0.140，CPI 再加速雖利通膨對沖但動能不足 | N/A | XLE | negative_rs3m, pe_zscore_elevated |
| Healthcare | COLD | 42 | 1.02 | 最乾淨硬催化：J&J 收購 Firefly Bio $10 億 M&A + insider 1.29 累積確認 · FRED Transitional favor defensive (×1.024)，CPI binary 不吃折價，最佳 COLD 升級候選 | N/A | XLV | negative_rs3m, no_theme_leadership |
| Consumer_Staples | COLD | 40 | 1.02 | FRED favor defensive (×1.024) + 估值便宜 (PE_z -1.06，+5 penalty)；beat 1.00 · 但主題偏空 (Consumer Defensive concentration 33.3 bearish)、RS3m -12.4%，防禦輪動尚未啟動 | N/A | XLP | negative_rs3m, bearish_theme |
| Consumer_Discretionary | COLD | 39 | 1.00 | beat 1.00 但 insider 0.76 偏軟、PE 52.96 最貴之一、RS3m -9.3% · Retail 主題偏空 (30.2 bearish)，Late cycle 消費承壓 | N/A | XLY | negative_rs3m, high_pe, insider_soft |
| Communication | COLD | 39 | 1.00 | 估值便宜 (PE_z -1.85，+5 penalty) 但 RS3m -14.6% 為次深 outflow、uptrend 0.131 · 無獨立主題領導，資金持續流出 | N/A | XLC | negative_rs3m, deep_outflow |
| Utilities | **AVOID** | 30 | 1.00 | uptrend 0.089 倒數第一、RS3m -14.8% 最深 outflow；債券代理對 6/10 CPI 折價 ×0.70 · 正向背離訊號：insider 3.14 (11 板塊最高買進) + hyperscaler/核能 AI 電力敘事 — 若 CPI 降溫，為防禦再進場首選 (見 watch_next) | N/A | XLU | binary_risk_within_48h, rate_sensitive_bond_proxy, deep_outflow, bearish_theme |
| Materials | COLD | 28 | 1.00 | uptrend 0.097 全市場最弱參與、0 篇催化新聞 · Basic Materials concentration 主題雙線 (bull 22.8 / bear 31.8) 偏空，資金缺席 | N/A | XLB | weakest_participation, no_catalyst, negative_rs3m |

---

## Macro Context

```text
Market Regime: RISK_OFF | Breadth Ceiling: 40-60% | Synthesized: 40-60% | Cycle: Late
FTD: FTD_CONFIRMED (quality 100) | Market Top: 45.8 Orange (Elevated Risk) | Breadth: 34.5 Weakening
Sentiment: F&G [55.3 — Neutral] | VIX: 18.84 | Put/Call: n/a | SPY RSI: 48.6
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors (heat 74.7, Trending) — 集中於 Technology，擁擠多單需防 mean-reversion · Quantum Computing (73.7) / Robotics & Automation (73.6) — 同樣只壓 Technology，非廣度 · Space Economy (58.6, Mature) / Defense & Aerospace (44.7) — 帶動 Industrials 選股

---

## Step 6 — FRED Regime Overlay

- **Regime**: Transitional (confidence 0.48)
- **Favor**: —
- **Avoid**: —
- **Velocity highlights**: T10Y2Y:accelerating, DFF:decelerating, CPIAUCSL:accelerating
- **Rationale**: Transitional regime, conf 0.48 → favor: Healthcare×1.024, Consumer_Staples×1.024 (defensive favor); cyclical/defensive raw 1.0/1.0 否則中性

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 50.16 | +0.97 | +21.6% | 2.075 |  |
| Industrials | 42.52 | +0.85 | -7.2% | 1.154 |  |
| Healthcare | 30.18 | -0.53 | -9.5% | 2.019 |  |
| Energy | 35.96 | +1.31 | -7.8% | 0.732 |  |
| Consumer_Staples | 30.62 | -1.06 | -12.4% | 1.419 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 52.96 | -0.58 | -9.3% | 1.001 |  |
| Communication | 22.19 | -1.85 | -14.6% | 1.824 | 🟢 OVERSOLD VALUE |
| Real_Estate | 50.3 | -1.61 | -5.5% | 1.097 | 🟢 OVERSOLD VALUE |
| Financials | 19.02 | -1.44 | -6.3% | 1.166 | 🟢 OVERSOLD VALUE |
| Materials | 26.93 | -0.23 | -8.2% | 1.044 |  |
| Utilities | 25.86 | -0.73 | -14.8% | 0.976 |  |

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

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $342.7B | $328.00 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $416.5B | $904.28 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $243.7B | $180.99 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $135.6B | $213.97 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $161.7B | $272.32 | Vincenzo James Vena | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.07T | $1131.42 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $362.8B | $399.47 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $560.3B | $232.77 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $401.5B | $227.23 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $298.3B | $120.79 | Robert Davis | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $621.4B | $149.92 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $373.0B | $187.31 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $142.7B | $117.14 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $73.4B | $137.78 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $82.0B | $54.87 | Olivier Le Peuch | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $341.2B | $146.54 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $431.0B | $971.87 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $342.0B | $79.48 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $194.0B | $141.92 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $946.1B | $118.88 | John R. Furner | _TBD_ |

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

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $134.8B | $144.54 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $90.4B | $194.12 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $106.6B | $1080.95 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $146.1B | $206.93 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $41.2B | $94.49 | Christian H. Hillabra… | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.05T | $488.13 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $837.0B | $312.37 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $382.0B | $53.83 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $250.8B | $81.94 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $306.4B | $1038.68 | David Solomon | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $235.0B | $507.90 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $75.3B | $305.30 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $91.1B | $63.37 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $62.9B | $282.35 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $72.6B | $257.97 | Christophe Beck | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $179.0B | $85.84 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $104.4B | $92.60 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $96.8B | $124.22 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $70.3B | $129.14 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $59.8B | $91.42 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.6)

> **DEFENSIVE：窄幅科技獨撐，CPI 前降風險升高**
> 
> 今天維持防禦、現金 40-60%、暫不追高；因為廣度惡化到 34.5、僅科技一個板塊正 RS 在撐盤，且 6/10 CPI 前長久期資產風險升溫；要等 CPI 落地與廣度回升、或科技 5 日 RS 止穩，才考慮加碼。

### Key Takeaways
1. 守住防禦：曝險壓在 40-60%，把資金留到 CPI 落地後再決定方向
2. 科技只給 WARM 不追高：唯一正 RS 但 insider 0.47 分布、5 日 RS 已轉弱、CPI 前最敏感
3. 工業列 WARM 為相對抗跌選股標的 (非利率敏感、未吃 CPI 折價)
4. 防禦輪動尚未啟動：Healthcare 有 J&J M&A + 內部人買進，是 COLD 中最佳升級候選
5. Utilities 雖被 CPI 折價壓到 AVOID，但 insider 3.14 + AI 電力敘事，CPI 降溫即為再進場首選

### Sector Actions
- **Wait**: Technology (high) — 唯一領頭但 insider 分布+CPI 敏感
- **Neutral**: Industrials (med) — 相對抗跌、選股、主題偏 Mature
- **Neutral**: Healthcare (med) — M&A+內部人買進，升級候選
- **Avoid**: Real_Estate (med) — 長久期 REIT 對 CPI 最敏感
- **Avoid**: Financials (low) — 主題偏空+利率重定價雙面刃
- **Avoid**: Utilities (low) — 債券代理 CPI 折價，惟內部人強買背離

### Watch Next
- 6/10 08:30 ET May CPI：核心若再加速→長久期 (Tech/REIT/Utilities) 續壓；若降溫→防禦板塊與 Utilities (insider 3.14) 為再進場首選
- 6/16-17 FOMC + 點陣圖：fed flat-to-easing (DFF decelerating) 與 CPI 再加速的政策矛盾
- Technology rs5d：目前 -3.1%，若連續 10 日為負且 XLK 跌破 50MA→確認 insider 0.47 分布領先訊號
- Breadth score：現 34.5 Weakening，需回升 >40 且第二個板塊轉正 RS 才解除窄幅集中風險
- signal_conflict：FTD (day 41 stale, 75-100%) vs Breadth (40-60%) 37.5pp 分歧，待新 FTD 或廣度回升收斂

---

## Top Actionable Themes

1. AI & Semiconductors (heat 74.7, Trending) — 集中於 Technology，擁擠多單需防 mean-reversion
2. Quantum Computing (73.7) / Robotics & Automation (73.6) — 同樣只壓 Technology，非廣度
3. Space Economy (58.6, Mature) / Defense & Aerospace (44.7) — 帶動 Industrials 選股
4. AI 電力需求 → Utilities hyperscaler/核能合作 (insider 3.14 背離訊號)

---

## HANDOFF TO INVESTMENT PROTOCOL

> STALE cache 觸發完整 Phase 0-1 重跑 (前一檔 generated_at 2026-06-07 14:20，>3h)。Phase 0 四層 cache 全 FRESH (<0.5h)。Phase 4a 四 lane 並行 subagent 全回 (PARALLEL_SUBAGENT)，呈現真實分歧：Rotation+Theme 看多 Technology，News+FRED 看空 (insider 分布 + 長久期承壓)，無三方共識 (consensus_warning=false)。DA 出 5 條 falsifiable challenge (Tech smart-money 0.47 分布、real_rate/CPI 長久期、窄幅集中、stale FTD、Utilities COLD 誤判)。Phase 4c：signal_conflict 將 Tech 由 76.5 raw HOT 降 WARM；CPI binary within_48h 對 Tech/REIT/Utilities/Financials 套 ×0.70。stance=DEFENSIVE (COLD 8 ≥3)。econ/earnings calendar 403 soft-fail，institutional Q-on-Q 不可用 (n=0)，senate net buy 全 0。
