# Sector Intelligence Report — 2026-08-17

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.68
> **Stance**: DEFENSIVE · **Cycle**: Early · **Generated**: 2026-08-17 19:38
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Healthcare | **HOT** | 76 | 0.96 | 三月相對強度領先 · 財報脈動維持正向 | ROBUST | XLV | — |
| Technology | WARM | 65 | 1.07 | AI 主題維持高熱度 · FOMC 與 ADI 事件壓分 | N/A | XLK | binary_risk_within_48h |
| Industrials | WARM | 57 | 1.07 | 軟著陸環境受惠 · 工業主題維持趨勢 | N/A | XLI | binary_risk_within_48h |
| Energy | WARM | 56 | 1.04 | 產業廣度居首 · 荷莫茲風險支撐油價 | N/A | XLE | binary_risk_within_48h |
| Communication | WARM | 51 | 1.04 | 廣度回升確認流入 · AI 資本支出侵蝕現金流 | N/A | XLC | — |
| Financials | COLD | 47 | 1.04 | 三月相對強度偏強 · 輪動廣度僅小幅改善 | N/A | XLF | binary_risk_within_48h |
| Consumer_Discretionary | COLD | 43 | 1.07 | 廣度仍低於十日均值 · HD 財報與房市數據密集 | N/A | XLY | binary_risk_within_48h |
| Materials | COLD | 42 | 1.04 | 銅價反彈提供支撐 · 中國需求訊號轉弱 | N/A | XLB | binary_risk_within_48h |
| Consumer_Staples | COLD | 34 | 0.90 | 防禦主題仍偏空 · WMT 前景面臨成本壓力 | N/A | XLP | — |
| Real_Estate | COLD | 26 | 0.96 | 廣度低於十日均值 · 房市數據與 FOMC 雙重風險 | N/A | XLRE | binary_risk_within_48h |
| Utilities | **AVOID** | 21 | 0.90 | 廣度接近零 · 主題與輪動同步偏空 | N/A | XLU | binary_risk_within_48h |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 75-90% | Synthesized: 75-90% | Cycle: Early
FTD: FTD_CONFIRMED (quality 100) | Market Top: 33.1 Yellow (Early Warning) | Breadth: 79.2 Healthy
Sentiment: F&G [71.9 — Greed] | VIX: 14.9 | Put/Call: n/a | SPY RSI: 65.8
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & Semiconductors · Robotics & Automation · Industrials Sector Concentration

---

## Step 6 — FRED Regime Overlay

- **Regime**: Soft Landing (confidence 0.72)
- **Favor**: Technology, Industrials, Consumer Discretionary
- **Avoid**: Consumer Staples, Utilities
- **Velocity highlights**: DGS10:accelerating, DFF:decelerating, CPIAUCSL:decelerating
- **Rationale**: Soft Landing regime, conf 0.72 → favor: Technology×1.074, Industrials×1.074, Consumer_Discretionary×1.074; avoid: Consumer_Staples×0.896, Utilities×0.896

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 44.55 | -0.12 | +2.1% | 0.425 |  |
| Healthcare | 23.19 | -1.33 | +10.4% | 0.549 |  |
| Energy | 19.26 | -0.36 | +2.8% | 0.808 |  |
| Financials | 19.42 | -1.06 | +9.6% | 0.936 |  |
| Industrials | 31.5 | -0.24 | +3.1% | 0.564 |  |
| Materials | 24.8 | -0.76 | -2.1% | 0.646 |  |
| Communication | 21.26 | -1.41 | -7.3% | 0.508 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 46.51 | -1.31 | -4.2% | 0.518 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 29.07 | -1.36 | -2.5% | 0.651 | 🟢 OVERSOLD VALUE |
| Utilities | 24.81 | -1.27 | -5.1% | 0.843 | 🟢 OVERSOLD VALUE |
| Real_Estate | 28.13 | -2.21 | -0.7% | 0.884 | 🟢 OVERSOLD VALUE |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.49T | $305.93 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.68T | $495.40 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.45T | $225.16 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.87T | $392.99 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $433.0B | $150.32 | Michael D. Sicilia | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.11T | $1180.16 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $364.8B | $401.73 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $627.4B | $260.35 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $440.7B | $249.45 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $335.5B | $135.84 | Robert Davis | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $663.5B | $160.09 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $398.3B | $200.01 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $154.5B | $126.78 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $76.0B | $142.61 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $79.8B | $53.77 | Olivier Le Peuch | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.09T | $504.03 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $972.2B | $362.84 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $457.7B | $64.49 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $268.5B | $88.79 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $306.6B | $1039.42 | David Solomon | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $382.2B | $368.38 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $394.6B | $856.57 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $300.5B | $222.97 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $74.2B | $233.96 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $174.5B | $293.68 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $223.3B | $482.74 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $87.2B | $359.10 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $95.6B | $66.50 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $68.8B | $308.97 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $77.7B | $276.11 | Christophe Beck | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.19T | $345.90 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.50T | $589.85 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $325.5B | $78.16 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $185.6B | $106.86 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $195.9B | $182.61 | Srinivasan Gopalan | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.83T | $262.65 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.35T | $342.27 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $337.9B | $338.86 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $193.8B | $272.83 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $60.3B | $40.73 | Elliott J. Hill | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $343.6B | $144.55 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $426.2B | $961.10 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $377.4B | $87.71 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $192.3B | $140.79 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $917.3B | $115.27 | John R. Furner | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $179.8B | $86.19 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $106.8B | $92.80 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $96.6B | $123.92 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $68.4B | $125.60 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $56.5B | $86.41 | Jeffrey Walker Martin | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $131.6B | $141.03 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $81.8B | $175.58 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $108.7B | $1102.10 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $169.7B | $235.46 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $33.2B | $75.98 | Christian H. Hillabra… | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.68)

> **防禦觀望｜高曝險上限下先避開事件密集板塊**
> 
> 今天先保留現金、僅偏多醫療；市場廣度仍健康，但未來 48 小時地緣、房市、財報與 FOMC 事件密集，待風險落地再擴大進攻部位。

### Key Takeaways
1. 降低事件密集板塊曝險，維持防禦觀望
2. 偏多醫療，但監控實質利率與相對強度
3. 等待 FOMC 紀要後再評估科技與金融
4. 觀察荷莫茲航運是否恢復以調整能源

### Sector Actions
- **Overweight**: Healthcare (med) — 相對強度領先且尾部風險低
- **Wait**: Technology (med) — 主題強但利率與資金訊號分歧
- **Wait**: Energy (med) — 地緣溢價高但可快速反轉
- **Wait**: Industrials (med) — 軟著陸受惠但事件風險未落地
- **Avoid**: Utilities (high) — 廣度、主題與巨觀同步偏弱

### Watch Next
- 追蹤 8/17 美伊停火期限與荷莫茲航運
- 檢查 8/18 美國房市數據是否止跌
- 檢查 8/18 HD 財報與消費指引
- 檢查 8/19 FOMC 紀要的利率訊號
- 檢查 8/19 ADI 財報對半導體需求的驗證

---

## Devil's Advocate Challenges (Accepted 4/5)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Healthcare — HOT | Rejected | Healthcare 的 uptrend 0.420 高於 MA10 0.315、RS3m +10.4%，可能只是已延伸的相對動能。實質利率 2.41% 已觸發巨觀衝突，且 Healthcare 不在 Soft Landing 優先輪動名單。 |
| Technology — HOT | **Accepted** | Technology 主題分數雖高，事件乘數後僅得 65 分。實質利率 2.41% 形成估值壓力，參議院 30 日淨買入為 -3，且 institutional sample size 為 0。 |
| Energy — HOT | **Accepted** | Energy 廣度 0.552，但事件乘數後僅得 56 分。利多依賴荷莫茲航運與停火二元事件，航運正常化將快速消除溢價，且實質利率 2.41% 壓抑需求。 |
| Industrials — HOT | **Accepted** | Industrials 主題分數僅 56.78，事件乘數後總分也只有 57。實質利率 2.41% 若維持高檔，融資成本可能同時壓抑訂單與估值。 |
| Materials — HOT | **Accepted** | Materials 雖有三重方向共識，事件乘數後僅得 42 分 COLD。它未進入任何 lane 的明確 HOT 前二名，將弱訊號交集升格為 HOT 是重複計票。 |

---

## Top Actionable Themes

1. AI & Semiconductors
2. Robotics & Automation
3. Industrials Sector Concentration

---

## HANDOFF TO INVESTMENT PROTOCOL

> 廣度與 FTD 仍支持 75-90% 上限，但事件乘數後僅 Healthcare 維持 HOT；科技、能源與工業等待 48 小時風險落地。
