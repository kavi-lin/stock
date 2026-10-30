# Sector Intelligence Report — 2026-10-22

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Mid · **Generated**: 2026-10-22 22:30
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|
| Healthcare | WARM | 68 | 3M RS +7.6% 且 20d/5d 動能齊揚 · 醫療集中度多頭主題 heat 59.38 居全市場之冠 | N/A | — | smart_money_divergence |
| Energy | WARM | 62 | 上升趨勢比例 0.453 為全市場最高 · 3M RS +8.61% 領先大盤 | N/A | — | credit_stress_headwind |
| Consumer_Staples | WARM | 54 | 寶僑 (PG) 等龍頭財報超預期支撐板塊 · 內部人買賣比 1.40 籌碼偏向積極流入 | N/A | — | — |
| Industrials | COLD | 30 | 3M RS -12.84% 資金持續流出 · 上升趨勢佔比僅 0.164 廣度疲弱 | N/A | — | weak_breadth, momentum_lag |
| Consumer_Discretionary | COLD | 30 | 名列 FRED sector_rotation_avoid 名單 · 實質利率高達 2.77% 壓抑非必需消費支出 | N/A | — | macro_avoid |
| Financials | COLD | 28 | 銀行主題處於加速走空階段 (heat 43.36) · credit_stress_elevated 抑制信貸利差擴張 | N/A | — | credit_stress_elevated |
| Communication | **AVOID** | 23 | 短中期 RS 嚴重惡化 (20d -5.10%, 5d -3.19%) · 大型通訊與科技面臨訴訟與反壟斷監管雜音 | N/A | — | accelerating_outflow |
| Materials | **AVOID** | 22 | 上升趨勢比例 0.106 瀕臨冰點 · 貴金屬主題處於 Trending bearish 趨勢走弱 | N/A | — | weak_breadth, low_uptrend |
| Real_Estate | **AVOID** | 21 | 財報擊敗率僅 0.50 為全市場最低 · FRED 體制明訂 sector_rotation_avoid | N/A | — | rate_sensitive, macro_avoid |
| Technology | **AVOID** | 20 | 實質利率 2.77% 壓制估值擴張空間 · 內部人買賣比 0.438 顯著背離 | N/A | — | macro_avoid, smart_money_divergence, macro_theme_divergence |
| Utilities | **AVOID** | 20 | 上升趨勢比例 0.013 為全市場最低 · 3M RS -12.26% 表現極度疲弱 | N/A | — | lowest_uptrend, exposure_floor_avoid |

---

## Macro Context

```text
Market Regime: RISK_OFF | Breadth Ceiling: 40-60% | Synthesized: 0-25% | Cycle: Mid
FTD: CORRECTION (quality 0) | Market Top: 54.2 Orange (Elevated Risk) | Breadth: 39.4 Weakening
Sentiment: F&G [49.7 — Neutral] | VIX: 18.02 | Put/Call: n/a | SPY RSI: 47.2
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Healthcare Sector Concentration · Cybersecurity · Cloud Computing & SaaS

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Healthcare | 23.58 | -0.98 | +7.6% | 0.222 |  |
| Energy | 15.79 | -1.02 | +8.6% | 0.29 |  |
| Consumer_Staples | 30.08 | -0.50 | +1.4% | 0.338 |  |
| Industrials | 26.35 | -1.49 | -12.8% | 0.294 | 🟢 OVERSOLD VALUE |
| Financials | 19.2 | -0.69 | -3.4% | 0.154 |  |
| Consumer_Discretionary | 48.85 | -1.00 | +1.8% | 0.2 | 🟢 OVERSOLD VALUE |
| Materials | 19.76 | -2.00 | -4.1% | 0.174 | 🟢 OVERSOLD VALUE |
| Communication | 18.59 | -1.32 | -2.1% | 0.173 |  |
| Real_Estate | 39.21 | -0.75 | -11.8% | 0.362 |  |
| Technology | 40.67 | -0.92 | +1.2% | 0.184 |  |
| Utilities | 23.04 | -0.89 | -12.3% | 0.19 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.21T | $1287.34 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $376.3B | $419.20 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $630.7B | $261.73 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $498.5B | $282.08 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $374.6B | $151.83 | Robert Davis | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxonmobil Holdings Corpora… | Oil & Gas Integrated | $732.6B | $178.17 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $448.4B | $226.96 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $175.3B | $145.96 | Andrew O'Brien | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $83.3B | $158.89 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $74.7B | $50.35 | Olivier Le Peuch | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $384.0B | $165.31 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $445.6B | $1005.65 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $403.8B | $93.86 | Henrique Gnani Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $185.6B | $136.20 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $941.3B | $118.28 | John Furner | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $298.7B | $287.85 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $328.9B | $715.51 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $259.0B | $192.18 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $66.4B | $209.55 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $174.4B | $293.62 | Vincenzo James Vena | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.17T | $545.67 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $891.7B | $335.46 | Jamie Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $356.5B | $50.98 | Brian T. Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $248.6B | $82.83 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $262.6B | $901.96 | David Michael Solomon | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.73T | $252.91 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.51T | $382.93 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $318.2B | $318.89 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $175.7B | $248.27 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $55.7B | $37.52 | Elliott J. Hill | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $231.8B | $502.81 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $82.4B | $339.26 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $95.4B | $66.35 | Kathleen L. Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $67.6B | $303.73 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $81.1B | $289.26 | Christophe Beck | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $3.99T | $327.62 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.67T | $654.64 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $276.2B | $66.33 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $194.0B | $112.37 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $169.5B | $158.03 | Srinivasan Gopalan | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $121.1B | $127.47 | Daniel S. Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $84.6B | $181.50 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $95.4B | $967.26 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $169.4B | $235.03 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $34.8B | $79.72 | Christian H. Hillabra… | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $5.04T | $345.25 | John Ternus | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.90T | $525.46 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.21T | $216.34 | Jensen Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.57T | $328.26 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $382.3B | $126.42 | Michael D. Sicilia | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $166.7B | $79.92 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $105.5B | $91.68 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $95.1B | $122.00 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $70.0B | $128.64 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $55.0B | $84.18 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.75)

> **防禦體制確立：總體訊號衝突降級，聚焦醫療與能源防禦配置**
> 
> 今日採取防禦姿態控制總曝險在0-25%，主因市場廣度惡化且FTD處於修正狀態引發訊號衝突，建議僅限於醫療與必需消費等防禦板塊低吸，靜待廣度築底與利率企穩。

### Key Takeaways
1. 維持整體防禦姿態並落實 0-25% 極低總曝險上限，嚴格防範市場下行波動
2. 三訊號合成觸發衝突條款（FTD 修正 vs 頂部預算 60-75%），全市場禁止激進加倉
3. 逢低關注相對強度強韌且具防禦特質之板塊（Healthcare、Energy、Consumer Staples）
4. 全面規避實質利率高企與信用收緊受損板塊（Technology、Real Estate、Utilities）

### Sector Actions
- **Wait**: Healthcare (med) — 多週期相對強度強韌，但內部人買賣比較低，待拉回支撐再行布局
- **Wait**: Energy (med) — 抗通膨相對強度突出，受總體信用收緊壓制，等待油價支撐確認
- **Neutral**: Consumer_Staples (high) — 防禦資金持續流入且財報穩健，作為市場震盪之資金避風港
- **Avoid**: Technology (high) — 高實質利率與信用壓力雙重逆風，AI債務憂慮拖累動能
- **Avoid**: Real_Estate (high) — 財報擊敗率僅 50% 且長端殖利率反彈加劇融資壓力
- **Avoid**: Utilities (med) — 上升趨勢佔比極低且觸發曝險下限強制規避，宜維持觀望

### Watch Next
- 美國初領失業救濟金人數與持續請領趨勢
- 標普全球製造業與服務業 Flash PMI 初值表現
- 10年期公債殖利率與實質利率是否突破前高
- 市場廣度指標 8MA 能否向上穿越 200MA 確認止跌

---

## Top Actionable Themes

1. Healthcare Sector Concentration
2. Cybersecurity
3. Cloud Computing & SaaS
4. Oil & Gas (Energy)

---

## HANDOFF TO INVESTMENT PROTOCOL

> Phase 0 廣度指標 score 39.40 (Weakening)，FTD state CORRECTION (quality 0)，Market-Top score 54.20 (Elevated Risk)。三訊號合成曝險中位數落差達 55pp，觸發 signal_conflict=true，強制降級最終 stance 為 DEFENSIVE，並依規則封頂總曝險於 0-25%。FRED Late Cycle Tightening（信心 0.37）偏好抗通膨與防禦板塊，迴避高估值成長與高槓桿地產。Phase 4 四 lane 並行 fan-out 運作正常，DA 提出實質利率與內部人籌碼背離挑戰，裁決樹全面落實評分與曝險門檻。
