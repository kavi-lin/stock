# Sector Intelligence Report — 2026-06-25

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-06-25 21:55
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|
| Technology | WARM | 58 | 3M 相對強度 +24.8% 全場唯一為正、AI&半導體(62)+機器人(72)主題密集帶動 · 30d 財報 beat 100%、surprise +8.9%、NVDA 首度調升股息 | N/A | XLK | macro_theme_divergence, smart_money_divergence, real_rate_headwind, fred_avoid, narrow_participation, consensus_warning |
| Industrials | WARM | 54 | 20d RS +6.2% 領先、uptrend 0.332 次高、參與度相對健康 · 基礎建設(65)+國防航太(52)+太空(59)多主題加持、GE 航太調升股息 | N/A | XLI | consensus_warning, late_cycle_margin_risk, valuation_stretched |
| Healthcare | WARM | 50 | uptrend 0.403 全場最高、20d RS +5.2% 改善中、防禦輪動受惠 · PE z -1.94 偏便宜 + 內部人 acq/disp 1.64 淨買、估值有支撐 | N/A | XLV | defensive_value |
| Financials | COLD | 41 | FRED favor(陡峭化曲線 +0.62 利於利差)、20d RS +6.6% 全場最佳改善 · 但 3M RS -3.1% 仍落後、PE z -1.81 便宜但缺催化 | N/A | XLF | macro_momentum_divergence |
| Real_Estate | COLD | 40 | PE z -4.41 極度便宜(超賣價值 +5)、3M RS -1.5% 相對抗跌 · 但 real rate 2.26% 高檔直接壓抑利率敏感的長久期 REIT | N/A | XLRE | fred_avoid, high_real_rate_headwind |
| Consumer_Staples | COLD | 38 | 防禦輪動受惠(XLP 20d +1.67%)、PE z -1.51 偏便宜(+5) · uptrend 0.195 偏低、缺成長動能 | N/A | XLP | defensive_low_growth |
| Consumer_Discretionary | **AVOID** | 35 | FRED 列入 avoid、PE z -1.21 但 PE 49 仍高、20d RS -4.1% 走弱 · 黏性通膨(PCE 4.1%)+ 就業放緩壓抑可選消費購買力 | N/A | XLY | fred_avoid, consumer_squeeze, exposure_floor_downgrade, earnings_binary_nke |
| Materials | COLD | 34 | FRED favor(通膨傳導受惠)+黃金主題 emerging(34) · 但 uptrend 0.174 低、3M RS -8.4% 落後、動能未跟上 macro | N/A | XLB | macro_momentum_divergence |
| Utilities | COLD | 33 | 內部人 acq/disp 3.31 全場最強淨買、5d RS +3.3% 短線改善 · AI 電力需求結構性敘事(CEG 屬機器人主題) | N/A | XLU | high_real_rate_headwind |
| Communication | **AVOID** | 29 | 3M/20d/5d RS 全負且持續惡化(-17.5%/-7.5%/-2.8%) · Tepper/Icahn/Druckenmiller 大戶減碼訊號、派發特徵明顯 | N/A | XLC | momentum_breakdown, smart_money_distribution, exposure_floor_downgrade |
| Energy | **AVOID** | 29 | 3M RS -24.5% 全場最弱、uptrend 0.050 僅 5% 個股在升勢 · FRED favor(通膨傳導)但動能全面崩跌、macro 與價格嚴重分歧 | N/A | XLE | momentum_collapse, macro_momentum_divergence, exposure_floor_downgrade |

---

## Macro Context

```text
Market Regime: RISK_OFF | Breadth Ceiling: 60-75% | Synthesized: 0-25% | Cycle: Late
FTD: CORRECTION (quality 0) | Market Top: 48.0 Orange (Elevated Risk) | Breadth: 52.8 Neutral
Sentiment: F&G [52.0 — Neutral] | VIX: 17.88 | Put/Call: n/a | SPY RSI: 49.3
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Robotics & Automation (Accelerating, heat 72) — Technology/Industrials · AI & Semiconductors (Trending, heat 62) — Technology · Infrastructure & Construction / Defense & Aerospace / Space (Trending) — Industrials

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 43.75 | -0.48 | +24.8% | 0.015 |  |
| Industrials | 40.54 | +0.63 | -2.0% | 0.014 |  |
| Healthcare | 22.29 | -1.94 | -7.0% | 0.012 |  |
| Financials | 17.98 | -1.81 | -3.1% | 0.012 |  |
| Real_Estate | 30.41 | -4.41 | -1.5% | 0.017 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 29.61 | -1.51 | -9.3% | 0.007 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 49.29 | -1.21 | -8.9% | 0.01 | 🟢 OVERSOLD VALUE |
| Materials | 27.24 | -0.13 | -8.4% | 0.009 |  |
| Utilities | 27.93 | -0.16 | -11.2% | 0.024 |  |
| Communication | 22.29 | -1.66 | -17.5% | 0.012 | 🟢 OVERSOLD VALUE |
| Energy | 18.24 | -0.62 | -24.5% | 1.133 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.40T | $299.30 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $2.78T | $374.38 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $4.87T | $200.97 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.83T | $385.54 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $458.2B | $159.30 | Michael D. Sicilia | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $381.7B | $365.31 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $461.6B | $1002.11 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $250.0B | $185.67 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $144.0B | $227.19 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $155.1B | $261.30 | Vincenzo James Vena | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.04T | $1108.76 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $369.2B | $406.55 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $579.3B | $240.65 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $412.4B | $233.41 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $296.9B | $120.22 | Robert Davis | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.07T | $497.58 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $893.6B | $333.48 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $409.2B | $57.66 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $256.9B | $83.95 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $320.0B | $1084.70 | David Solomon | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $131.4B | $140.94 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $81.5B | $174.98 | Steven Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $108.9B | $1103.99 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $156.2B | $221.23 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $35.7B | $81.73 | Christian H. Hillabra… | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $355.7B | $152.75 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $426.2B | $960.94 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $349.7B | $81.28 | James Quincey | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $195.6B | $143.08 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $953.1B | $119.77 | John R. Furner | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.60T | $241.59 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.43T | $381.83 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $339.9B | $340.85 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $194.8B | $274.12 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $61.9B | $41.85 | Elliott J. Hill | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $240.6B | $520.21 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $82.6B | $334.80 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $88.9B | $61.87 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $61.6B | $276.67 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc | Chemicals - Specialty | $78.4B | $278.56 | Christophe Beck | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $181.6B | $87.09 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $106.8B | $94.76 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $97.6B | $125.16 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $72.7B | $133.66 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $60.1B | $91.90 | Jeffrey Walker Martin | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.24T | $350.27 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.43T | $563.28 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $303.7B | $72.11 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $179.4B | $103.28 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $197.7B | $182.66 | Srinivasan Gopalan | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $564.1B | $136.09 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $341.6B | $171.54 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $130.2B | $106.83 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $71.2B | $133.67 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $69.2B | $46.31 | Olivier Le Peuch | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.55)

> **偏防禦：窄幅科技領漲、無 FTD 確認，現金優先等跟進日**
> 
> 今天以防禦為主、暫不加碼且現金優先；因為市場仍在修正、尚無跟進日確認，廣度偏窄(僅科技 RS 為正)，加上實質利率 2.26% 與 PCE 回升至 4.1% 壓抑高評價板塊；要等到出現 FTD 跟進日或廣度明顯轉強，才轉趨積極。

### Key Takeaways
1. 維持低曝險(0-25%)、不建立新倉，等 FTD 跟進日確認——今日防禦主因是修正中無跟進日且三訊號衝突
2. 科技/工業/醫療僅列『選股謹慎』(WARM)，科技受 FRED 規避＋內部人淨賣(acq/disp 0.46)雙重壓制不宜追高
3. 能源、通訊、非必需消費降為 AVOID：能源動能崩跌(3M RS -24.5%)、通訊遭 Tepper/Druckenmiller 等大戶減碼
4. 防禦類(醫療/公用/必需消費)相對抗跌可作底倉，但高實質利率持續壓抑房地產與公用
5. 下週方向關鍵看 NFP(7/2，估 9 萬 vs 前 17.2 萬、失業率升至 4.5%)與 ISM 製造業(7/1)

### Sector Actions
- **Wait**: Technology (med) — 主題強但 FRED 規避＋內部人賣超
- **Wait**: Industrials (med) — 主題密集但晚週期 margin 風險
- **Neutral**: Healthcare (med) — 防禦＋估值便宜＋內部人買
- **Avoid**: Energy (high) — 動能全面崩跌、RS 最弱
- **Avoid**: Communication (med) — 大戶減碼、RS 全負
- **Avoid**: Consumer_Discretionary (med) — FRED 規避＋消費承壓

### Watch Next
- FTD 跟進日是否出現：NASDAQ/SP500 放量上漲收復 21EMA 才解除防禦
- NFP 7/2(估 9 萬、失業率 4.5%)——勞動市場急冷與 Fed 路徑風險
- ISM 製造業 PMI 7/1(估 53.6)是否守住擴張、牽動工業/原物料
- 實質利率是否續守 2.0% 上方＋CPI 是否二度加速(壓高乘數科技/利率敏感板塊)
- NASDAQ 派發日是否續增(已 6 天)、6/30 JOLTs 與 CB 消費者信心

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | macro_theme_divergence | cap WARM | Theme/News lane 提 HOT 但 FRED 規避＋內部人 acq/disp 0.46 淨賣，STEP G.5 上限 WARM |
| Energy | macro_momentum_divergence | AVOID | FRED 首位 favor 但 3M RS -24.5% 動能全面崩跌，macro 偏多 vs 價格偏空 |
| Materials | macro_momentum_divergence | COLD | FRED favor 通膨傳導但 uptrend 0.174、3M RS -8.4% 落後，待價格確認 |
| Financials | macro_momentum_divergence | COLD | FRED favor 曲線陡峭化但 3M RS -3.1% 落後，20d +6.6% 改善待跟進 |

---

## Top Actionable Themes

1. Robotics & Automation (Accelerating, heat 72) — Technology/Industrials
2. AI & Semiconductors (Trending, heat 62) — Technology
3. Infrastructure & Construction / Defense & Aerospace / Space (Trending) — Industrials
4. Defensive value rotation — Healthcare/Consumer_Staples 估值便宜＋內部人買

---

## HANDOFF TO INVESTMENT PROTOCOL

> FMP /stable 端口在 prefetch 期間遭遇暫時性 429(per-minute 節流，非當日額度耗盡)，valuation 與 smart_money 於 45s 後重跑成功，四個 HARD cache 均為 06-25 新鮮資料。FRED slim snapshot 的 favor/avoid 顯示為空陣列，但 step6_overlay 直接讀 full cache 取得 favor[Energy,Materials,Financials]/avoid[Technology,Real Estate,Consumer Discretionary]，分數已正確套用。核心張力:FRED 規避科技但科技是唯一動能領袖(macro vs momentum 分歧);能源為 FRED 首位 favor 卻動能最弱(鏡像分歧)。synthesized_exposure 0-25% 採 FTD 修正底線(Breadth/Market-Top 皆 60-75%)、三訊號 55pp 衝突 → signal_conflict=true、強制 ≥3 AVOID。0 HOT 因 signal_conflict 對任何 HOT 降級且最高分僅 58。STEP B 將 Energy/Communication/Consumer_Discretionary 降為 AVOID(依動能崩跌＋大戶派發＋FRED 規避＋消費承壓擇定，Utilities 因防禦買盤＋內部人 3.31 淨買保留 COLD)。STEP G.5:科技 ∈ FRED avoid 且 Theme/News lane 提 HOT → cap WARM＋regime_confidence ×0.90。
