# Sector Intelligence Report — 2026-07-08

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Mid · **Generated**: 2026-07-08 07:38
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|
| Healthcare | WARM | 56 | 參與度全場最佳：uptrend 0.502（唯一 >0.5） · 估值偏低：PE z 分數 -1.53；3M RS -1.2% 為跌幅最小者 | N/A | XLV | — |
| Financials | WARM | 53 | 催化劑密集：今日 FOMC 紀要＋7/14 JPM/BAC/WFC 銀行財報季開局 · FRED favor＋實質利率 2.25% NIM 利多；估值低（PE z -1.38） | MODERATE | XLF | smart_money_divergence, fat_tail_warning |
| Technology | WARM | 50 | 主題最強：Robotics 62.9、AI/半導體 58.8、Quantum 48.3 全 Accelerating · 3M 相對強度 +17.5% 領先全場，唯一正 RS | MODERATE | XLK | fat_tail_warning, smart_money_divergence, momentum_exhaustion, macro_theme_divergence, real_rate_pressure |
| Real_Estate | COLD | 45 | 估值極低（PE z -3.53 全場最低）＋資料中心 REIT 題材 · 但列 FRED avoid：實質利率 2.25% 直接壓縮 cap rate 折現 | N/A | XLRE | macro_theme_divergence, real_rate_pressure |
| Industrials | COLD | 42 | Industrials 主題 Accelerating 47.1；RTX 趨勢買進題材 · 3M RS -2.9% 溫和；20d RS +3.4% 短線略回溫 | N/A | XLI | — |
| Consumer_Staples | COLD | 40 | 估值偏低觸發 oversold value +5（PE z -1.56、uptrend 0.225<0.3） · 防禦屬性但 3M RS -8.2% 資金外流 | N/A | XLP | oversold_value |
| Consumer_Discretionary | COLD | 37 | 列 FRED avoid（實質利率高＋Overheating） · 估值最貴（PE 51.1 全場最高）＝安全邊際低 | N/A | XLY | fred_avoid, expensive_valuation |
| Communication | COLD | 33 | 估值低觸發 oversold value +5（PE z -1.47、uptrend 0.243<0.3） · 3M RS -14.4% 資金外流嚴重 | N/A | XLC | oversold_value, weak_rotation |
| Utilities | **AVOID** | 29 | 曝險下限規則強制 AVOID（synthesized 0-25%） · 3M RS -14.0% 外流；Utilities Defensive 主題偏空 | N/A | XLU | exposure_floor_avoid, weak_rotation |
| Energy | **AVOID** | 29 | 曝險下限規則強制 AVOID＋3M RS -20.4%（全場最弱中期趨勢） · News/FRED 看多 vs Rotation/Theme 看空（2-2 分歧無多數） | MODERATE | XLE | fat_tail_warning, weak_rotation, exposure_floor_avoid, lane_split |
| Materials | **AVOID** | 26 | 曝險下限規則強制 AVOID；uptrend 0.122 全場次低 · 3M RS -12.6% 外流；FCX 跌幅大於大盤 | N/A | XLB | exposure_floor_avoid, weak_rotation |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 60-75% | Synthesized: 0-25% | Cycle: Mid
FTD: FTD_WINDOW (quality 0) | Market Top: 42.8 Orange (Elevated Risk) | Breadth: 55.0 Neutral
Sentiment: F&G [57.8 — Neutral] | VIX: 17.26 | Put/Call: n/a | SPY RSI: 51.8
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI/半導體與機器人自動化 Accelerating（Technology）但窄幅領漲，需底部確認再進 · 醫療保健防禦加參與度全場最佳（uptrend 0.502）加估值偏低 · 大型銀行財報季（7/14）加實質利率 2.25% NIM 利多，Financials 為守勢中相對亮點

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Healthcare | 23.97 | -1.53 | -1.2% | 0.242 |  |
| Financials | 19.04 | -1.38 | -1.9% | 0.194 |  |
| Technology | 44.08 | -0.43 | +17.5% | 0.138 |  |
| Real_Estate | 28.39 | -3.53 | -5.7% | 0.183 |  |
| Industrials | 30.84 | -0.76 | -2.9% | 0.215 |  |
| Consumer_Staples | 29.27 | -1.56 | -8.2% | 0.22 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 51.13 | -1.00 | -5.9% | 0.314 |  |
| Communication | 22.98 | -1.47 | -14.4% | 0.13 | 🟢 OVERSOLD VALUE |
| Utilities | 27.34 | -0.46 | -14.0% | 0.151 |  |
| Energy | 18.63 | -0.59 | -20.4% | 0.303 |  |
| Materials | 25.94 | -0.33 | -12.6% | 0.201 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.16T | $1235.56 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $388.9B | $428.19 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $643.3B | $267.24 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $449.9B | $254.65 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $318.3B | $128.86 | Robert Davis | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.09T | $504.00 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $908.9B | $339.22 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $424.8B | $59.86 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $266.9B | $87.21 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $307.7B | $1042.98 | David Solomon | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.56T | $310.66 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $2.89T | $388.84 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $4.77T | $196.93 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.76T | $370.78 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $408.0B | $141.64 | Michael D. Sicilia | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $133.9B | $143.61 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $77.0B | $165.25 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $100.9B | $1022.93 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $167.7B | $237.59 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $33.7B | $77.22 | Christian H. Hillabra… | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $383.4B | $366.98 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $433.1B | $940.12 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $270.5B | $200.85 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $71.3B | $225.05 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $168.1B | $283.12 | Vincenzo James Vena | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $355.7B | $152.75 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $420.2B | $947.50 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $361.6B | $84.05 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $198.2B | $144.98 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $887.6B | $111.54 | John R. Furner | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.65T | $245.98 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.51T | $402.90 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $344.2B | $345.21 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $200.5B | $282.21 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $63.9B | $43.21 | Elliott J. Hill | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.44T | $367.03 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.56T | $615.58 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $320.8B | $76.18 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $169.2B | $97.46 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $199.9B | $184.73 | Srinivasan Gopalan | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $184.5B | $88.47 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $109.7B | $97.29 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $100.0B | $128.22 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $74.8B | $137.53 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $61.8B | $94.59 | Jeffrey Walker Martin | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $587.1B | $141.65 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $346.4B | $173.94 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $132.1B | $108.44 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $71.7B | $134.54 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $69.4B | $46.42 | Olivier Le Peuch | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $249.0B | $538.23 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $84.4B | $342.26 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $85.2B | $59.27 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $67.9B | $305.05 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $79.7B | $283.08 | Christophe Beck | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.62)

> **防禦為主：底部未確認、無強勢領漲，僅醫療/金融相對抗跌**
> 
> 今天以守代攻、不追高：FTD 尚未確認（反彈第 7 天）加上頂部風險偏高，整體曝險守在低檔；科技看似最強卻出現內部人減碼與短線動能翻負，僅醫療保健與大型銀行（財報季在即）相對抗跌，等 FTD 與廣度回升再轉積極。

### Key Takeaways
1. 壓低整體曝險至 0-25%：FTD 未確認（反彈第 7 天）加頂部風險 Orange，守住現金優先。
2. 避開科技追高：3M RS +17.5% 但 20d -3.4%、5d -5.6% 已翻負，內部人減碼（比率 0.41），屬窄幅領漲。
3. 相對偏好醫療與金融：醫療參與度全場最佳（uptrend 0.502），金融受惠 NIM 加銀行財報季（7/14）。
4. 清倉能源、公用事業、原物料：資金持續外流且無催化劑，三者列 AVOID。
5. 靜待底部確認：FTD 觸發加廣度回升前，不擴大股票曝險。

### Sector Actions
- **Wait**: Technology (low) — 動能轉弱加內部人減碼，勿追高
- **Neutral**: Healthcare (med) — 參與度最佳、估值低，可選股
- **Neutral**: Financials (med) — NIM 加銀行財報季利多，選股佈局
- **Underweight**: Real_Estate (med) — 實質利率壓長天期估值
- **Avoid**: Energy (med) — 3M RS -20.4%，反彈勿追
- **Avoid**: Materials (low) — 資金外流且無催化

### Watch Next
- FTD 確認訊號（Follow-Through Day）與廣度 uptrend 是否回升
- 今日 FOMC 會議紀要對利率路徑的措辭
- 7/14 美國 6 月 CPI（CPIAUCSL 動能上升中，通膨是否再加速）
- 7/14 大型銀行財報 JPM/BAC/WFC 開局是否定調 Financials
- 科技 20d/5d 相對強度是否止跌（動能耗盡是否延續）

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | — | — |  |
| Real_Estate | — | — |  |
| Energy | — | — |  |

---

## Top Actionable Themes

1. AI/半導體與機器人自動化 Accelerating（Technology）但窄幅領漲，需底部確認再進
2. 醫療保健防禦加參與度全場最佳（uptrend 0.502）加估值偏低
3. 大型銀行財報季（7/14）加實質利率 2.25% NIM 利多，Financials 為守勢中相對亮點
4. 利率敏感長天期（REIT/Utilities/Tech）受實質利率 2.25% 壓制，回避
5. 能源內部分歧：Chevron 利多 vs 3M RS -20.4%，屬新聞面反彈勿追

---

## HANDOFF TO INVESTMENT PROTOCOL

> FMP /stable/ 於平行 prefetch 觸發 429 rate-limit，valuation 與 smart_money 冷卻 45s 後 sequential 重跑成功（今日 cache 完整）。核心訊號衝突：breadth/market-top 皆 60-75% 但 FTD 未確認（0-25%），55pp 落差觸發 signal_conflict → stance ≤ NEUTRAL，實際落 DEFENSIVE。無 HOT 板塊（最高 Healthcare 58）。
