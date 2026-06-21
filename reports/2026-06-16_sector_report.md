# Sector Intelligence Report — 2026-06-16

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Mid · **Generated**: 2026-06-16 21:16
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|
| Technology | WARM | 75 | AI/半導體主題 84 領跑、RS3m +25% (分數 75) · PE z+1.81 偏貴、內部人淨賣 (ratio 0.47) | RESILIENT | XLK | smart_money_divergence, binary_risk_within_48h, high_valuation_z, overbought, crowding_risk, verdict_downgrade_binary |
| Industrials | WARM | 58 | Robotics 82 / Defense / Infra 三主題並進 · GE Aerospace、HON +3.2% 個股強 | N/A | XLI | late_cycle_cyclical, narrative_driven |
| Financials | COLD | 48 | PE z-1.95 最便宜、JPM 歐洲擴張 · FOMC 明日二元 → ×0.70 降 COLD | N/A | — | binary_risk_within_48h, value_trap_watch, rate_sensitive |
| Materials | COLD | 47 | FCX 銅多頭點評帶動 · 基礎材料集中度主題 61 | N/A | XLB | thin_news_coverage |
| Consumer_Discretionary | COLD | 41 | PE 56 偏貴、RS -7.1% · TSLA PT 更新、FedEx 關稅觀望 | N/A | — | outflow |
| Real_Estate | COLD | 38 | real_rate 2.18% 直接壓久期 · FOMC 明日二元 → ×0.70 | N/A | — | binary_risk_within_48h, rate_sensitive, outflow |
| Communication | COLD | 37 | RS -15.5% 動能流出 · PE z-1.71 估值偏低 (+5 value) | N/A | — | momentum_outflow |
| Healthcare | COLD | 35 | Pharma/Biotech/GLP-1 三主題皆空 · Allergan FDA 核准、Merck 合作為個案 | N/A | — | bearish_theme_cluster |
| Consumer_Staples | COLD | 26 | 防禦紅利敘事 (怕崩盤) · RS -12.2% 流出、uptrend 0.19 低 | N/A | — | outflow |
| Energy | **AVOID** | 24 | 油價週跌 5.7%、RS -16.9% · Oil&Gas + Clean Energy 雙空主題 | N/A | — | oil_weakness, outflow |
| Utilities | **AVOID** | 21 | uptrend 0.086 全場最弱、RS -18.1% · real_rate 2.18% + FOMC 雙壓 | N/A | — | binary_risk_within_48h, rate_sensitive, outflow |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 60-75% | Synthesized: 60-75% | Cycle: Mid
FTD: FTD_CONFIRMED (quality 100) | Market Top: 37.1 Yellow (Early Warning) | Breadth: 51.8 Neutral
Sentiment: F&G [59.7 — Neutral] | VIX: 16.13 | Put/Call: n/a | SPY RSI: 53.0
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors · Robotics & Automation · Defense & Aerospace

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 54.66 | +1.81 | +25.4% | 0.836 |  |
| Industrials | 28.84 | -1.95 | -5.2% | 0.906 |  |
| Materials | 28.06 | -0.02 | -6.5% | 1.192 |  |
| Consumer_Discretionary | 56.18 | -0.19 | -7.1% | 0.809 |  |
| Communication | 22.47 | -1.71 | -15.5% | 1.135 | 🟢 OVERSOLD VALUE |
| Healthcare | 30.32 | -0.52 | -11.6% | 0.872 |  |
| Financials | 20.15 | -1.08 | -4.2% | 0.992 | 🟢 OVERSOLD VALUE |
| Real_Estate | 49.57 | -1.58 | -7.2% | 1.082 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 31.15 | -0.75 | -12.2% | 0.862 |  |
| Energy | 35.49 | +1.11 | -16.9% | 1.114 |  |
| Utilities | 26.43 | -0.56 | -18.1% | 0.885 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.35T | $296.46 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $2.96T | $398.73 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.12T | $211.37 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.87T | $392.86 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $559.6B | $194.59 | Michael D. Sicilia | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $362.5B | $346.98 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $429.8B | $933.15 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $248.9B | $184.84 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $145.1B | $229.07 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $158.9B | $267.69 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $240.3B | $519.46 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $79.6B | $322.73 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $99.9B | $69.52 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $62.6B | $280.95 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $75.9B | $269.82 | Christophe Beck | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.64T | $245.78 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.54T | $410.26 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $332.9B | $333.88 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $203.0B | $285.70 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $67.3B | $45.52 | Elliott J. Hill | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.49T | $371.36 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.52T | $598.39 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $342.0B | $81.22 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $176.6B | $101.71 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $203.5B | $188.02 | Srinivasan Gopalan | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.07T | $1131.50 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $372.8B | $410.47 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $569.9B | $236.74 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $391.8B | $221.77 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $286.2B | $115.86 | Robert Davis | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.06T | $493.55 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $860.7B | $321.21 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $398.6B | $56.16 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $257.0B | $83.97 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $320.0B | $1084.55 | David Solomon | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $139.0B | $149.07 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $86.2B | $184.95 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $105.0B | $1064.25 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $151.1B | $214.11 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $38.7B | $88.69 | Christian H. Hillabra… | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $348.1B | $149.49 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $432.6B | $975.52 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $345.9B | $80.41 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $198.5B | $145.20 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $954.2B | $119.91 | John R. Furner | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $586.4B | $141.47 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $360.0B | $180.76 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $137.2B | $112.63 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $70.8B | $132.89 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $80.8B | $54.05 | Olivier Le Peuch | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $178.8B | $85.75 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $105.7B | $93.72 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $97.6B | $125.17 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $70.3B | $129.25 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $60.2B | $92.07 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.62)

> **DEFENSIVE：窄頭部＋FOMC 明日，進場前先觀望**
> 
> 今天先按兵不動、現有部位守住不加碼；因為漲勢只剩科技少數大型股撐盤、廣度偏弱，加上明早 FOMC 利率決議與經濟預測是二元變數；等 FOMC 表態與零售銷售出爐、廣度回升再決定是否進攻。

### Key Takeaways
1. 守住曝險上限 60-75%，FOMC 前不開新倉
2. 科技雖唯一動能領先 (分數 75)，但內部人邊漲邊賣＋估值偏貴，標籤降 WARM、續抱不追高
3. 利率敏感的 Utilities/Real_Estate/Financials FOMC 前一律避開
4. 工業 (Robotics/Defense/Infra) 為唯一次優選股池，等 RS 翻正；材料銅題材僅單標的觀察
5. 市場廣度 uptrend<0.36 偏窄，留意頭部早期預警 (Market-Top 37 黃燈)

### Sector Actions
- **Wait**: Technology (med) — 動能領先但派發訊號＋FOMC 風險
- **Wait**: Industrials (med) — 主題強但 RS 仍落後、等翻正
- **Underweight**: Materials (low) — RS 落後、新聞覆蓋薄
- **Avoid**: Financials (med) — FOMC 二元、價值陷阱待驗證
- **Avoid**: Utilities (high) — 全場最弱＋利率雙壓
- **Avoid**: Energy (med) — 油價週跌、雙空主題

### Watch Next
- FOMC 利率決議＋SEP＋記者會 (6/17)：dots 與 core PCE 預測是關鍵二元變數
- 零售銷售 MoM (6/17, May)：消費動能驗證
- ACN 財報 (6/18)：科技/顧問 capex 指引風向
- 科技廣度 uptrend 能否升破 0.45：窄頭部是否擴散
- real_rate 2.18% 與 CPI 再加速：久期/估值壓力是否升溫

---

## Top Actionable Themes

1. AI & Semiconductors
2. Robotics & Automation
3. Defense & Aerospace
4. Quantum Computing
5. Infrastructure & Construction

---

## HANDOFF TO INVESTMENT PROTOCOL

> DEFENSIVE：窄頭部 (僅科技 RS+25% 撐、廣度 uptrend<0.36) + FOMC 明日二元，0 HOT。selection 限 Tech/Industrials WARM 且 FOMC 後再進攻；利率敏感 (Utilities/RE/Financials) 與能源全避。
