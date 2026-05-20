# Sector Intelligence Report — 2026-05-19

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-05-19 19:53
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|
| Energy | WARM | 70 | 唯一 uptrend_ratio 0.695 領先且 Up 趨勢、RS 3M +4.5% · 四 lane 一致看多但 1y z-score +2.24 已超買 — 持有不追高 | ROBUST | XLE | overbought, late_cycle |
| Communication | WARM | 52 | PE 1y z-score -2.05 估值深度壓縮 → valuation_penalty +5 (oversold value) · Up 趨勢 + Google/Blackstone AI 雲端合資正向催化 | ROBUST | XLC | weak_relative_strength |
| Industrials | COLD | 41 | Down 趨勢、RS 3M -10.6%、uptrend_ratio 0.215 資金外流 · Robotics & Automation 主題 bearish-Accelerating,惡化中 | N/A | — | capital_outflow |
| Utilities | COLD | 35 | uptrend_ratio 0.075 全市場最低、RS 3M -13.4% · NextEra/Dominion 併購為個案催化,難扭轉板塊資金外流 | N/A | — | capital_outflow, oversold |
| Technology | COLD | 35 | NVDA 5/20 財報 binary 事件 → composite ×0.70 懲罰 · RS 3M +16.8% 強但 uptrend_ratio 僅 0.278 且 Down 趨勢 — 縮窄領導 | N/A | — | binary_risk_within_48h, macro_theme_divergence, late_cycle |
| Consumer_Staples | COLD | 34 | Up 趨勢但 RS 3M -10.8% 落後大盤 · Consumer Defensive 主題 bearish heat 25.9 偏冷 | N/A | — | — |
| Real_Estate | COLD | 34 | PE 1y z-score -1.70 估值壓縮 → valuation_penalty +5 · REITs 主題 bearish-Accelerating heat 26.0 惡化 | N/A | — | capital_outflow |
| Materials | COLD | 33 | Down 趨勢、RS 3M -12.9%、新聞 0 篇無催化 · Basic Materials Concentration 主題 bullish heat 51.9 為唯一支撐 | N/A | — | capital_outflow |
| Financials | COLD | 32 | uptrend_ratio 0.109 偏低、Down 趨勢、RS 3M -9.0% · 穩定幣熱潮 + Buffett 買入為敘事型催化,廣度未擴張 | N/A | — | capital_outflow |
| Healthcare | COLD | 31 | RS 3M -15.6% 全市場最差、Down 趨勢 · Healthcare & Pharma 主題 bearish-Accelerating heat 36.6 惡化 | N/A | — | capital_outflow |
| Consumer_Discretionary | **AVOID** | 23 | uptrend_ratio 0.087 接近最低、Oversold、RS 3M -7.9% · PE_TTM 54.4 偏貴、FRED avoid (實質利率逆風) | N/A | — | capital_outflow, oversold |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 40-60% | Synthesized: 40-60% | Cycle: Late
FTD: FTD_CONFIRMED (quality 100) | Market Top: 33.4 Yellow (Early Warning) | Breadth: 32.4 Weakening
Sentiment: F&G [68.5 — Greed] | VIX: 18.05 | Put/Call: n/a | SPY RSI: 73.1
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Oil & Gas (Energy) — heat 65.8 Mature;地緣油價催化撐住 Energy,但屬均值回歸型題材 · AI & Semiconductors — heat 67.4 Trending;NVDA 5/20 binary 落地前不宜追價 · Quantum Computing — heat 71.3 Trending 但 confidence Low,敘事性過熱、缺基本面確認

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Energy | 38.45 | +2.24 | +4.5% | 1.143 |  |
| Communication | 22.84 | -2.05 | -5.9% | 1.116 | 🟢 OVERSOLD VALUE |
| Industrials | 39.12 | +0.13 | -10.6% | 1.044 |  |
| Utilities | 25.66 | -0.71 | -13.4% | 1.563 |  |
| Consumer_Staples | 33.63 | +0.46 | -10.8% | 1.036 |  |
| Technology | 48.2 | +0.71 | +16.8% | 1.748 |  |
| Real_Estate | 50.11 | -1.70 | -8.6% | 1.152 | 🟢 OVERSOLD VALUE |
| Materials | 26.69 | -0.28 | -12.9% | 1.057 |  |
| Financials | 22.03 | -0.40 | -9.0% | 0.999 |  |
| Healthcare | 28.52 | -0.86 | -15.6% | 0.847 |  |
| Consumer_Discretionary | 54.44 | -0.43 | -7.9% | 1.322 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $665.2B | $160.49 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $390.6B | $196.13 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $151.7B | $124.54 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $76.2B | $142.99 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $85.4B | $57.15 | Olivier Le Peuch | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.80T | $396.94 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.55T | $611.21 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $377.5B | $89.65 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $180.5B | $103.95 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $206.3B | $190.65 | Srinivasan Gopalan | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $298.8B | $285.99 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $398.0B | $863.95 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $236.9B | $175.95 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $137.6B | $217.23 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $163.3B | $275.13 | Vincenzo James Vena | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $185.7B | $89.04 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $105.6B | $93.71 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $95.8B | $122.84 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $69.5B | $127.68 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $59.0B | $90.23 | Jeffrey Walker Martin | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $331.5B | $142.35 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $477.6B | $1076.47 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $349.4B | $81.20 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $203.8B | $149.06 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $1.06T | $133.34 | John R. Furner | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.37T | $297.84 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.15T | $423.54 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.40T | $222.32 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.99T | $420.71 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $536.6B | $186.57 | Michael D. Sicilia | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $132.7B | $142.31 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $82.6B | $177.28 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $104.8B | $1062.62 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $150.1B | $212.61 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $39.2B | $89.92 | Christian H. Hillabra… | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $236.3B | $510.86 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $74.7B | $302.78 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $86.9B | $60.48 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $65.3B | $293.31 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $70.1B | $249.21 | Christophe Beck | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.05T | $488.30 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $805.8B | $300.73 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $359.7B | $50.69 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $227.6B | $74.39 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $279.2B | $946.36 | David Solomon | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $930.6B | $988.20 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $355.2B | $391.13 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $551.1B | $228.92 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $370.0B | $209.41 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $278.0B | $112.56 | Robert Davis | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.85T | $264.86 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.54T | $409.99 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $298.6B | $299.81 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $200.7B | $282.47 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $62.9B | $42.57 | Elliott J. Hill | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.6)

> **內部結構轉弱、訊號分歧 — 防禦為先,不新建倉**
> 
> 廣度 32.4 Weakening、8/11 產業下降趨勢、分布天數 90;FTD 雖確認但已 day-28 老化,三訊號 35pp 分歧鎖死進攻;僅 Energy/Communication 達 WARM,無 HOT。

### Key Takeaways
1. 曝險上限壓回 40-60%:廣度 32.4 Weakening 疊加分布天數分數 90,內部結構持續惡化
2. 暫停新建倉:11 產業中 8 個處下降趨勢,僅 Energy/Communication 達 WARM,無 HOT
3. 迴避 NVDA 5/20 財報前加碼 Technology:binary 事件 + 縮窄領導 + 實質利率 2.03% 逆風三重壓制
4. Energy 雖四 lane 一致看多,1y z-score +2.24 已超買 — 持有可、不追高
5. 等 5/20 FOMC Minutes 與 5/21 PMI/Housing 數據確認景氣再評估方向

### Sector Actions
- **Wait**: Communication (low) — 估值壓縮但 RS -5.9%,等趨勢確認
- **Neutral**: Energy (med) — 四 lane 一致但 z+2.24 超買,持有不追
- **Neutral**: Financials (low) — 敘事性催化,板塊廣度未擴張
- **Underweight**: Technology (med) — NVDA 5/20 binary + 實質利率逆風
- **Underweight**: Utilities (med) — 資金外流 + 實質利率逆風
- **Avoid**: Consumer_Discretionary (high) — 資金外流 + 超賣無反轉訊號

### Watch Next
- NVDA 2026-05-20 財報 (AMC) — AI 生態系 binary,盤後反應定 Technology 短線方向
- FOMC Minutes 2026-05-20 — 利率路徑與 Fed 獨立性 (新主席 Warsh) 語調
- S&P Global PMI 2026-05-21 — 製造/服務景氣確認 Overheating 是否降溫
- 廣度 composite 能否回升站上 40 — 跌破則加速防禦、再降曝險
- Energy 1y z-score 是否守住 +2.0 上方 — 回落即動能耗盡確認

---

## Top Actionable Themes

1. Oil & Gas (Energy) — heat 65.8 Mature;地緣油價催化撐住 Energy,但屬均值回歸型題材
2. AI & Semiconductors — heat 67.4 Trending;NVDA 5/20 binary 落地前不宜追價
3. Quantum Computing — heat 71.3 Trending 但 confidence Low,敘事性過熱、缺基本面確認

---

## HANDOFF TO INVESTMENT PROTOCOL

> Cache STALE (generated_at 2026-05-18 22:04,約 21h) → 完整重跑 Phase 0-1。Phase 0 五層 cache 全 FRESH (breadth/ftd/market_top/fred 皆 ~0.27h)。三訊號分歧:Breadth 40-60% vs FTD 75-100% vs Market-Top 80-90% → 35pp spread → signal_conflict=true,stance 鎖 ≤NEUTRAL,實際落 DEFENSIVE (COLD≥3)。econ-calendar / earnings-calendar 舊端點 403,改用 FMP MCP 補。Phase 4a 四 lane PARALLEL_SUBAGENT 全回。
