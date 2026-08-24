# Sector Intelligence Report — 2026-08-18

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.68
> **Stance**: DEFENSIVE · **Cycle**: Early · **Generated**: 2026-08-18 21:30
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Healthcare | WARM | 50 | 0.96 | 三月相對強度領先 · 財報九成全數超預期 | ROBUST | XLV | binary_risk_within_48h |
| Communication | COLD | 42 | 1.04 | 估值呈超賣 · 監管新聞偏空 | N/A | XLC | binary_risk_within_48h |
| Technology | COLD | 40 | 1.07 | AI主題熱度最高 · 債息與AI修正壓力 | MODERATE | XLK | binary_risk_within_48h |
| Materials | COLD | 39 | 1.04 | 銅價反彈 · 廣度仍低於三成 | N/A | XLB | binary_risk_within_48h |
| Energy | COLD | 37 | 1.04 | 能源廣度居首 · 油價與LNG催化 | ROBUST | XLE | binary_risk_within_48h |
| Financials | COLD | 28 | 1.04 | 三月相對強度突出 · 短週期動能耗盡 | N/A | XLF | binary_risk_within_48h |
| Industrials | **AVOID** | 24 | 1.07 | 主題多空並存 · 三項事件風險疊加 | N/A | XLI | binary_risk_within_48h |
| Consumer_Discretionary | **AVOID** | 24 | 1.07 | 估值呈超賣 · 消費與財報事件密集 | N/A | XLY | binary_risk_within_48h |
| Consumer_Staples | **AVOID** | 23 | 0.90 | WMT財報待驗證 · FRED結構性迴避 | N/A | XLP | binary_risk_within_48h |
| Real_Estate | **AVOID** | 23 | 0.96 | 廣度僅九趴 · 長端殖利率逆風 | N/A | XLRE | binary_risk_within_48h |
| Utilities | **AVOID** | 20 | 0.90 | 廣度全場最低 · FRED結構性迴避 | N/A | XLU | binary_risk_within_48h |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 75-90% | Synthesized: 75-90% | Cycle: Early
FTD: FTD_CONFIRMED (quality 100) | Market Top: 29.8 Yellow (Early Warning) | Breadth: 76.2 Healthy
Sentiment: F&G [69.5 — Greed] | VIX: 15.75 | Put/Call: n/a | SPY RSI: 65.8
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI與半導體 · 機器人 · GLP-1與生技

---

## Step 6 — FRED Regime Overlay

- **Regime**: Soft Landing (confidence 0.72)
- **Favor**: Technology, Industrials, Consumer Discretionary
- **Avoid**: Consumer Staples, Utilities
- **Velocity highlights**: T10Y2Y:accelerating, DGS10:accelerating, DFF:decelerating
- **Rationale**: Soft Landing regime, conf 0.72 → favor: Technology×1.074, Industrials×1.074, Consumer_Discretionary×1.074; avoid: Consumer_Staples×0.896, Utilities×0.896

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Energy | 19.28 | -0.36 | +0.8% | 0.849 |  |
| Technology | 44.6 | -0.10 | +3.5% | 0.75 |  |
| Healthcare | 23.47 | -1.29 | +10.6% | 0.808 |  |
| Industrials | 31.2 | -0.28 | +4.2% | 0.873 |  |
| Financials | 19.3 | -1.09 | +8.2% | 1.557 |  |
| Communication | 20.86 | -1.47 | -9.1% | 0.655 | 🟢 OVERSOLD VALUE |
| Materials | 24.76 | -0.78 | -0.7% | 0.665 |  |
| Consumer_Discretionary | 46.08 | -1.37 | -4.3% | 0.971 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 28.72 | -1.52 | -4.5% | 1.023 | 🟢 OVERSOLD VALUE |
| Real_Estate | 28.36 | -2.17 | -0.8% | 1.65 | 🟢 OVERSOLD VALUE |
| Utilities | 24.76 | -1.31 | -3.8% | 0.812 | 🟢 OVERSOLD VALUE |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $669.4B | $161.52 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $403.7B | $202.71 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $155.4B | $127.56 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $77.8B | $146.15 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $79.9B | $53.86 | Olivier Le Peuch | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.49T | $305.59 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.57T | $480.35 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.45T | $225.01 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.87T | $392.43 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $422.6B | $146.71 | Michael D. Sicilia | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.12T | $1185.16 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $359.3B | $395.62 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $632.3B | $262.37 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $442.3B | $250.35 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $335.8B | $135.97 | Robert Davis | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $383.3B | $369.43 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $406.1B | $881.65 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $298.7B | $221.64 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $72.7B | $229.45 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $178.2B | $299.90 | Vincenzo James Vena | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.07T | $498.23 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $967.2B | $360.96 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $453.4B | $63.89 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $264.8B | $87.55 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $310.1B | $1051.31 | David Solomon | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.16T | $344.00 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.45T | $568.97 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $316.5B | $76.02 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $179.7B | $103.51 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $193.2B | $180.12 | Srinivasan Gopalan | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $219.4B | $474.33 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $85.0B | $349.97 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $98.4B | $68.43 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $67.0B | $300.86 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $77.6B | $275.84 | Christophe Beck | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.81T | $261.31 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.34T | $339.30 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $336.9B | $337.88 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $188.7B | $265.53 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $57.8B | $39.09 | Elliott J. Hill | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $340.2B | $143.13 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $422.9B | $953.50 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $374.2B | $86.98 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $188.8B | $138.24 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $909.8B | $114.33 | John R. Furner | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $131.2B | $140.62 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $80.3B | $172.23 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $108.3B | $1097.61 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $169.7B | $235.45 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $32.5B | $74.44 | Christian H. Hillabra… | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $179.9B | $86.22 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $106.2B | $92.29 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $96.3B | $123.58 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $68.9B | $126.53 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $56.2B | $85.94 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.68)

> **防禦：高廣度遭密集二元事件壓縮**
> 
> 今天先降風險、只保留醫療等待單；FOMC 與密集財報可能重定價利率和需求，待事件落地、廣度維持後再加碼。

### Key Takeaways
1. 降低總曝險，密集二元事件主導今日防禦立場
2. 保留醫療觀察，等待財報優勢轉成更廣價格參與
3. 暫緩能源追價，監控戰爭溢價與EIA驗證
4. 避開工業、非必需消費與利率敏感防禦板塊

### Sector Actions
- **Wait**: Healthcare (med) — 財報強但FOMC前不追價
- **Underweight**: Technology (high) — AI熱度遭實質利率與ADI事件壓制
- **Underweight**: Energy (med) — 催化強但EIA與戰爭溢價具二元性
- **Avoid**: Industrials (high) — 三項事件風險複合
- **Avoid**: Consumer_Discretionary (high) — 零售財報與勞動數據同時驗證
- **Avoid**: Utilities (high) — 廣度最低且長債殖利率不利

### Watch Next
- 監控8月19日FOMC會議紀要對殖利率路徑的重定價
- 核對8月19日EIA原油庫存與ADI財報
- 追蹤8月19至20日TJX、LOW、WMT與DE財報
- 檢查8月20日初領失業金與費城製造數據

---

## Devil's Advocate Challenges (Accepted 3/4)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Technology — HOT | **Accepted** | XLK尾風險分數30.6且最大回撤15.92%。real rate為2.41%並高於2.0%門檻，且新聞面受AI修正與債息上升壓制。 |
| Energy — HOT | **Accepted** | 能源廣度雖居首但僅0.552，催化高度依賴戰爭溢價。real rate為2.41%並高於2.0%門檻，可能壓抑融資與需求。 |
| Healthcare — HOT | Rejected | 醫療主題信心為Low且缺乏能源般的廣度確認。real rate為2.41%並高於2.0%門檻，仍不利長久期醫療估值。 |
| Financials — HOT | **Accepted** | senate 30日淨買入為-1。3M RS為+8.2%，但20日與5日RS分別轉為-1.4%與-0.4%，且real rate為2.41%。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | news_negative_price_positive | monitor | 3M相對強度為正，但當日AI與債息新聞轉弱 |

---

## Top Actionable Themes

1. AI與半導體
2. 機器人
3. GLP-1與生技
4. 工業集中度

---

## HANDOFF TO INVESTMENT PROTOCOL

> FTD已確認且廣度健康，但FOMC、EIA與密集大型股財報使11產業全面承受48小時二元風險，僅醫療維持WARM。
