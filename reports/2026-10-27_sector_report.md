# Sector Intelligence Report — 2026-10-27

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Mid · **Generated**: 2026-10-27 00:50
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Energy | WARM | 77 | 0.96 | 3M相對強度最強 · 獲利達成率100% | ROBUST | XLE | macro_conflict_downgraded_from_hot, theme_exhausting_stage |
| Healthcare | WARM | 73 | 1.03 | 醫療主題熱度高達62.4 · 估值修復優勢(+5) | ROBUST | XLV | smart_money_insider_divergence, credit_stress_headwind |
| Consumer_Staples | WARM | 60 | 1.03 | FRED總體模型偏好 · 內部人比例1.31偏多 | ROBUST | XLP | low_theme_heat |
| Technology | WARM | 60 | 0.92 | AI主題加速 · 內部人買賣比0.418倒貨 | MODERATE | XLK | macro_theme_divergence, smart_money_divergence, binary_risk_within_48h, consensus_challenged |
| Financials | COLD | 46 | 0.95 | 3M相對強度-6.0% · 信用壓力升溫 | ROBUST | XLF | credit_stress_elevated, rs_negative |
| Communication | COLD | 44 | 0.95 | 3M相對強度-8.3% · 資金呈現淨流出 | ROBUST | XLC | rs_negative, valuation_rebound_trap |
| Consumer_Discretionary | COLD | 40 | 0.92 | FRED明確迴避 · 本益比偏高(47.0) | ROBUST | XLY | fred_sector_rotation_avoid, macro_tightening_drag |
| Materials | COLD | 35 | 0.95 | 多頭排列僅12.9% · 3M相對強度-5.0% | ROBUST | XLB | low_uptrend_ratio, weak_relative_strength |
| Industrials | **AVOID** | 24 | 0.95 | 相對強度居全板塊之末 · 資金持續外流 | ROBUST | XLI | rs_worst_performer, outflow_persistent, low_exposure_forced_avoid |
| Real_Estate | **AVOID** | 21 | 0.98 | FRED明確迴避 · 財報達成率僅50% | ROBUST | XLRE | fred_sector_rotation_avoid, earnings_beat_rate_50pct, refinance_stress |
| Utilities | **AVOID** | 18 | 1.03 | 多頭排列2.7%全市場最低 · 3M相對強度-9.7% | ROBUST | XLU | uptrend_ratio_collapsed, severe_outflow, rate_sensitive_trap |

---

## Macro Context

```text
Market Regime: RISK_OFF | Breadth Ceiling: 60-75% | Synthesized: 0-25% | Cycle: Mid
FTD: RALLY_ATTEMPT (quality 0) | Market Top: 56.0 Orange (Elevated Risk) | Breadth: 42.5 Neutral
Sentiment: F&G [49.9 — Neutral] | VIX: 18.36 | Put/Call: n/a | SPY RSI: 47.5
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Oil & Gas (Energy) - 熱度 64.3，動能高檔力竭警戒，聚焦現金流龍頭 · AI & Technology - 熱度 60.1，超級財報週資本支出與變現能力驗證 · Healthcare Innovation - 熱度 62.4，抗景氣循環防禦屬性與選股聚焦

---

## Step 6 — FRED Regime Overlay

- **Regime**: Late Cycle Tightening (confidence 0.34)
- **Favor**: Energy, Consumer Staples, Health Care, Utilities
- **Avoid**: Technology, Consumer Discretionary, Real Estate
- **Velocity highlights**: DGS10:decelerating, CPIAUCSL:accelerating, CPILFESL:accelerating
- **Rationale**: Late Cycle Tightening regime, conf 0.34 → favor: Energy×0.963, Healthcare×1.035, Consumer_Staples×1.035; avoid: Technology×0.92, Consumer_Discretionary×0.92, Real_Estate×0.981

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Energy | 16.26 | -0.93 | +17.4% | 0.51 |  |
| Healthcare | 23.28 | -1.01 | +3.7% | 0.468 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 30.62 | -0.27 | -2.2% | 0.504 |  |
| Technology | 40.04 | -1.04 | +5.5% | 0.375 |  |
| Financials | 19.05 | -0.73 | -6.0% | 0.219 |  |
| Communication | 18.11 | -1.36 | -8.3% | 0.718 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 47.01 | -1.26 | -1.5% | 0.364 | 🟢 OVERSOLD VALUE |
| Materials | 24.0 | -0.65 | -5.0% | 0.369 |  |
| Industrials | 25.97 | -1.67 | -11.8% | 0.482 | 🟢 OVERSOLD VALUE |
| Real_Estate | 39.47 | -0.71 | -10.5% | 0.745 |  |
| Utilities | 23.03 | -0.92 | -9.7% | 0.188 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxonmobil Holdings Corpora… | Oil & Gas Integrated | $753.3B | $183.21 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $460.8B | $233.21 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $181.2B | $150.80 | Andrew O'Brien | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $85.5B | $163.03 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $78.7B | $53.06 | Olivier Le Peuch | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.20T | $1273.46 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $375.3B | $418.09 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $635.1B | $263.81 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $504.8B | $285.64 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $358.4B | $145.27 | Robert Davis | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $373.2B | $161.02 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $444.6B | $1003.32 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $398.9B | $92.71 | Henrique Gnani Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $185.0B | $135.77 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $954.1B | $119.89 | John Furner | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $5.07T | $347.73 | John Ternus | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.89T | $524.51 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.08T | $210.96 | Jensen Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.54T | $321.68 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $381.5B | $126.16 | Michael D. Sicilia | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.16T | $542.19 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $881.4B | $331.58 | Jamie Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $353.6B | $50.56 | Brian T. Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $247.3B | $82.39 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $255.0B | $875.68 | David Michael Solomon | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $3.90T | $320.21 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.64T | $642.62 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $274.2B | $65.85 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $194.3B | $112.52 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $157.2B | $146.54 | Srinivasan Gopalan | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.68T | $248.00 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.47T | $372.22 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $319.1B | $319.83 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $175.8B | $248.46 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $55.4B | $37.30 | Elliott J. Hill | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $234.6B | $508.83 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $81.8B | $337.06 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $93.7B | $65.18 | Kathleen L. Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $68.4B | $307.15 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $80.9B | $288.53 | Christophe Beck | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $296.4B | $285.64 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $315.8B | $687.00 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $257.8B | $191.01 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $70.1B | $221.15 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $174.0B | $292.87 | Vincenzo James Vena | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $120.2B | $126.45 | Daniel S. Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $88.1B | $188.97 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $94.2B | $955.03 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $171.0B | $237.32 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $37.6B | $85.97 | Christian H. Hillabra… | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $172.2B | $82.10 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $106.9B | $92.89 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $97.4B | $124.98 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $70.6B | $129.69 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $55.0B | $84.06 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.72)

> **總體三訊號衝突疊加超級週，防禦降噪、暫避高估值與破位板塊**
> 
> 盤前嚴控曝險上限在25%以內並聚焦能源與防禦板塊，主因FTD尚未確立且廣度與頂部指標背離，靜待FOMC利率決議與科技巨頭財報落地後再行定奪。

### Key Takeaways
1. 控管整體曝險上限於 0-25% 區間：FTD 尚未獲確認且廣度與頭部風險指標存在背離，嚴格限制新建部位規模。
2. 優先聚焦防禦與抗通膨韌性板塊：在晚週期緊縮與實質利率 2.72% 格局下，保留能源與必需消費等具現金流支撐配置。
3. 全面避開結構瓦解與高融資風險板塊：公用事業多頭排列僅 2.7% 且工業與房地產相對弱勢，嚴格落實防禦迴避。
4. 緊盯 48 小時內重大二元風險：微軟與谷歌財報及 FOMC 利率決議在即，嚴防高波動引發估值回調。

### Sector Actions
- **Overweight**: Energy (med) — 3M相對強度居冠且具備獲利韌性，惟動能高檔防追高
- **Wait**: Technology (med) — 超級財報週即將揭曉，內部人偏空減持需靜待指引
- **Wait**: Healthcare (med) — 主題熱度維持高檔，惟受信用壓力與內部人減持壓抑
- **Avoid**: Utilities (high) — 多頭排列比率僅2.7%且結構崩解，資金持續流出
- **Avoid**: Industrials (high) — 相對強度表現墊底且多頭架構脆弱，維持迴避
- **Avoid**: Real_Estate (high) — 高實質利率環境壓抑商業地產再融資，獲利勝率偏低

### Watch Next
- 10/28 FOMC 利率決議與經濟預測：關注基準利率走勢與點陣圖對實質利率與通膨路徑之定調
- 10/28 微軟與谷歌 Q3 財報：檢視 AI 資本支出指引是否持續擴張或面臨獲利變現考驗
- 10/29 美國 Q3 GDP 初值與核心 PCE 物價指數：觀察經濟增長韌性與通膨黏性是否推升美債殖利率
- 10/29 亞馬遜與禮來 Q3 財報：追蹤消費終端需求韌性與重磅藥品銷售增長動力
- 美股大盤 FTD 確認訊號：監控指數是否出現放量長紅以達成底部結構之雙重確認

---

## Top Actionable Themes

1. Oil & Gas (Energy) - 熱度 64.3，動能高檔力竭警戒，聚焦現金流龍頭
2. AI & Technology - 熱度 60.1，超級財報週資本支出與變現能力驗證
3. Healthcare Innovation - 熱度 62.4，抗景氣循環防禦屬性與選股聚焦

---

## HANDOFF TO INVESTMENT PROTOCOL

> Phase 0 廣度 (42.5) 與市場頂部指標 (56.0) 偏弱，FTD 處於 RALLY_ATTEMPT (Day 28) 尚未確認，合成曝險壓制於 0-25% 且三訊號衝突 (diff 55pp > 30pp)，強制判定 DEFENSIVE 並將原 HOT 板塊降級為 WARM。Phase 4a 4 位獨立分析師完成平行推演，Phase 4b DA 觸發 R4 FRED 衝突與 R5 內部人背離挑戰成功。落實 STEP B 迴避 3 個板塊 (Industrials, Real_Estate, Utilities)。
