# Sector Intelligence Report — 2026-06-24

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Mid · **Generated**: 2026-06-24 21:14
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Technology | WARM | 77 | 1.00 | 3M 相對強度 +22.6% 全場最強、AI&半導體主題 57.1 加速 · 30d 財報 beat 100%、surprise +8.9% | MODERATE | XLK | signal_conflict_downgrade, smart_money_divergence, real_rate_headwind, consensus_warning, narrow_participation |
| Industrials | WARM | 61 | 1.00 | 廣度 uptrend 0.326 全場最高、20d/5d RS 轉正（+5.3%/+2.5%）新輪動跡象 · 機器人(73.6)/基建(65.2)/國防(59.2)三大加速主題堆疊 | N/A | XLI | momentum_3m_negative |
| Healthcare | WARM | 54 | 1.02 | uptrend 0.354 次高、PE 25.7 估值不貴（z1y -1.46 偏低） · Lilly 完成 Centessa 併購+$1.9B Abbisko 案、生技收購敘事回溫 | N/A | XLV | bearish_theme_drag, fred_favor_defensive |
| Financials | WARM | 51 | 1.00 | PE 19.1 全場最便宜、z1y -1.44 估值低、uptrend 0.320 偏高 · 殖利率曲線陡化（T10Y2Y 加速）對淨利差結構有利 | N/A | XLF | mixed_theme_signal |
| Real_Estate | COLD | 45 | 1.00 | z1y -4.24 嚴重超賣（+5 oversold value） · 但 real rate 2.24% 高+6/25 Core PCE 為利率敏感逆風 | N/A | XLRE | oversold_value, rate_sensitive_pce_risk |
| Consumer_Discretionary | COLD | 45 | 1.00 | RS3m -8.6% 資金流出、PE 50.3 偏貴 · 零售消費空頭主題（heat 26.1） | N/A | XLY | bearish_theme_drag, high_valuation |
| Consumer_Staples | COLD | 35 | 1.02 | RS3m -8.8%、uptrend 0.176 偏弱 · FRED Transitional 防禦微 favor（×1.024）但動能未跟上 | N/A | XLP | weak_momentum, fred_favor_defensive |
| Communication | **AVOID** | 35 | 1.00 | RS3m -16.8% 次差、uptrend 0.153 廣度崩壞 · 通訊集中度空頭主題（heat 34.5 加速） | N/A | XLC | weak_momentum, bearish_theme, breadth_collapse |
| Energy | **AVOID** | 34 | 1.00 | RS3m -20.6% 全場最差、uptrend 0.081 近乎停滯 · 油氣空頭主題（heat 30.9）、PE 35.4 偏貴(z1y +0.96) | N/A | XLE | worst_momentum, bearish_theme, fred_lane_conflict |
| Materials | COLD | 33 | 1.00 | uptrend 0.133 低、新聞催化少（僅 4 篇） · 基建主題或有外溢但 heat 未確認 | N/A | XLB | low_participation |
| Utilities | **AVOID** | 27 | 1.00 | uptrend 0.049 全場最低、RS3m -11.3% · Utilities Defensive 空頭主題（heat 40.8）— 連防禦都不 work | N/A | XLU | worst_uptrend, bearish_theme, rate_sensitive_pce_risk |

---

## Macro Context

```text
Market Regime: RISK_OFF | Breadth Ceiling: 60-75% | Synthesized: 0-25% | Cycle: Mid
FTD: CORRECTION (quality 0) | Market Top: 47.1 Orange (Elevated Risk) | Breadth: 53.0 Neutral
Sentiment: F&G [50.1 — Neutral] | VIX: 18.98 | Put/Call: n/a | SPY RSI: 46.9
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Robotics & Automation (73.6, Accelerating) · Infrastructure & Construction (65.2, Accelerating) · AI & Semiconductors (57.1, Accelerating)

---

## Step 6 — FRED Regime Overlay

- **Regime**: Transitional (confidence 0.47)
- **Favor**: —
- **Avoid**: —
- **Velocity highlights**: T10Y2Y:accelerating, DFF:decelerating, CPIAUCSL:accelerating
- **Rationale**: Transitional regime, conf 0.47 → favor: Healthcare×1.024, Consumer_Staples×1.024（其餘 sector ×1.0；favor/avoid 名單為空，僅 defensive 微調）

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 45.66 | +0.07 | +22.6% | 0.971 |  |
| Industrials | 42.35 | +1.11 | -2.7% | 1.081 |  |
| Healthcare | 25.68 | -1.46 | -6.8% | 0.849 |  |
| Financials | 19.09 | -1.44 | -2.6% | 0.864 |  |
| Real_Estate | 32.22 | -4.24 | -2.0% | 0.782 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 50.32 | -1.11 | -8.6% | 1.205 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 30.72 | -0.93 | -8.8% | 1.19 |  |
| Materials | 27.6 | -0.05 | -5.0% | 0.829 |  |
| Energy | 35.35 | +0.96 | -20.6% | 1.014 |  |
| Communication | 21.97 | -1.73 | -16.8% | 1.181 | 🟢 OVERSOLD VALUE |
| Utilities | 26.85 | -0.55 | -11.3% | 1.061 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.37T | $297.73 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $2.77T | $373.00 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $4.88T | $201.33 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.81T | $380.42 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $486.8B | $169.25 | Michael D. Sicilia | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $372.4B | $356.43 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $454.5B | $986.64 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $248.3B | $184.41 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $142.6B | $225.08 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $154.7B | $260.63 | Vincenzo James Vena | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.03T | $1096.85 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $371.1B | $408.59 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $567.1B | $235.60 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $413.9B | $234.26 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $290.9B | $117.79 | Robert Davis | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.06T | $493.77 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $894.8B | $333.94 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $410.0B | $57.78 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $256.5B | $83.82 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $322.7B | $1093.89 | David Solomon | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $135.5B | $145.36 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $82.9B | $177.99 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $109.7B | $1112.79 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $154.3B | $218.59 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $36.5B | $83.65 | Christian H. Hillabra… | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.52T | $233.90 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.44T | $382.88 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $325.5B | $326.45 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $193.1B | $271.74 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $62.9B | $42.55 | Elliott J. Hill | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $351.4B | $150.90 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $428.3B | $965.77 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $345.1B | $80.20 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $193.6B | $141.66 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $954.8B | $119.98 | John R. Furner | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $240.2B | $519.28 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $80.7B | $327.02 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $92.7B | $64.50 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $63.0B | $282.75 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $76.1B | $270.37 | Christophe Beck | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $580.0B | $139.93 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $350.4B | $175.96 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $134.5B | $110.40 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $71.4B | $133.96 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $71.1B | $47.56 | Olivier Le Peuch | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.19T | $346.50 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.43T | $564.06 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $307.8B | $73.10 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $179.5B | $103.35 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $198.5B | $183.42 | Srinivasan Gopalan | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $180.6B | $86.61 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $107.0B | $94.88 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $97.7B | $125.31 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $72.1B | $132.60 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $60.2B | $92.14 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.58)

> **內部背離防禦盤：科技領漲、廣度衰竭、FTD 仍校正**
> 
> 今天守住、別追高：指數靠科技 mega-cap 撐在高檔，但廣度（uptrend 多在 0.3 以下）與 FTD 校正、Distribution-Day 滿格三訊號嚴重背離；等 6/25 Core PCE 與 breadth 轉強再決定要不要加碼。

### Key Takeaways
1. 降曝險至 0-25%：三訊號背離 55pp、FTD 無確認，新倉一律縮手
2. 科技不追高只核心持有：3M RS +22.6% 最強，但內部人逢漲賣超(0.46)、real rate 2.24% 壓高乘數
3. 防禦優先選 Healthcare/Financials：估值低(PE 25.7/19.1)、廣度相對高
4. AVOID Energy/Communication/Utilities：動能最差(RS -20.6%/-16.8%/-11.3%)、空頭主題、無催化
5. 盯緊 6/25 Core PCE：熱數據將重壓利率敏感的 Real_Estate/Utilities/高乘數科技

### Sector Actions
- **Overweight**: Healthcare (med) — 估值低+廣度次高+Lilly M&A，防禦首選
- **Overweight**: Financials (low) — PE 19 最便宜+曲線陡化受益
- **Wait**: Industrials (low) — 主題堆疊強但 3M RS 仍負，等確認
- **Neutral**: Technology (med) — 核心持有不追高；內部人賣超+real rate 逆風
- **Avoid**: Energy (high) — RS -20.6% 最差+油氣空頭主題
- **Avoid**: Utilities (med) — uptrend 0.049 最低+連防禦主題都空頭

### Watch Next
- 6/25 Core PCE (May) — Fed 偏好通膨指標，熱數據壓利率敏感板塊與高乘數科技
- 6/25 FedEx(FDX) 財報 — 貨運景氣與 Industrials 輪動確認
- XLK 能否站回並守住 50MA — 科技動能真偽分水嶺
- S&P 500 廣度 uptrend ratio 能否脫離 0.3 以下窄區 — DEFENSIVE 升級前提
- 6/30 NKE 財報 + CB 消費者信心/JOLTs — 消費與就業動能

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | momentum_chips_divergence | 不追高、守 50MA | 3M RS +22.6% 但 5d RS -1.1% 轉負、內部人 acq/disp 0.46 逢漲賣超 — 動能與籌碼背離 |
| Energy | macro_vs_flow_divergence | 採信資金流、維持 AVOID | FRED lane 看多(real rate/曲線陡化/CPI) vs Rotation/Theme 看空(RS -20.6%) — macro 理論 vs 實際資金流背離 |
| Industrials | theme_vs_momentum_divergence | 等 3M RS 轉正再升級 | 機器人/基建/國防主題堆疊強 vs 3M RS -2.7% — 短線輪動 vs 中期動能背離 |

---

## Top Actionable Themes

1. Robotics & Automation (73.6, Accelerating)
2. Infrastructure & Construction (65.2, Accelerating)
3. AI & Semiconductors (57.1, Accelerating)
4. Defense & Aerospace (59.2, Trending)

---

## HANDOFF TO INVESTMENT PROTOCOL

> STALE cache（最新 intel 為 06-23）故完整重跑 Phase 0-1。Phase 0 四層皆 FRESH。prefetch 首輪 valuation/smart_money 撞 FMP 429，序列化重抓成功(smart_money 加 --skip-institutional)。四 lane 並行 PARALLEL_SUBAGENT 全回 isolated。signal_conflict=true(55pp) → STEP G 把 Technology HOT 降 WARM；exposure 0-25%<40% → ≥3 AVOID。無 HOT、stance DEFENSIVE。
