# Sector Intelligence Report — 2026-06-05

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-06-05 21:44
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|
| Technology | WARM | 75 | 唯一正 RS 板塊（3M +26.7%），uptrend 0.395 最高，AI/Robotics/Quantum 主題熱度全市場最高 · 但 PE 54.49 / z+1.93 過熱，內部人賣超（insider 0.49 < 0.5）+ 議員淨賣 -3，signal_conflict 強制 HOT→WARM | ROBUST | XLK | signal_conflict_downgrade, smart_money_divergence, overbought_valuation, late_cycle_narrow_leadership, macro_duration_risk |
| Industrials | COLD | 49 | Caterpillar 成長題材 + insider 1.14 乾淨，但 RS 3M -8.7% 仍跑輸大盤 · Late-cycle 無資金輪入，敘事買不等於價格領導（DA: 無 RS 的 cyclical = value trap） | N/A | — | negative_relative_strength, late_cycle_no_rotation |
| Materials | COLD | 47 | Basic Materials 集中度主題 heat 59 + 通膨再加速利多，但 RS 3M -9.6% · FCX 銅成本壓力，uptrend 0.218 偏弱 | N/A | — | negative_relative_strength |
| Energy | COLD | 43 | Iran deal 利空油價（Chevron 降評），RS 3M -7.1% · 通膨利多被地緣供給敘事抵消 | N/A | — | negative_relative_strength, bearish_catalyst |
| Consumer_Discretionary | COLD | 43 | PE 56.08 偏貴，RS 3M -10.5% · Retail 主題 trending-bearish | N/A | — | negative_relative_strength, high_valuation |
| Real_Estate | COLD | 42 | z-score -1.71 估值便宜（+5 oversold），但 real_rate 2.08% 壓抑長久期 REIT · REITs 主題 trending-bearish，RS 3M -8.7% | N/A | — | negative_relative_strength, rate_duration_risk |
| Financials | COLD | 42 | PE 19.44 / z-1.28 最便宜（+5），SpaceX IPO 話題 + FRED real-rate 利多 · 但 RS 3M -9.2%，主題熱度低、無資金輪入 | N/A | — | negative_relative_strength |
| Healthcare | COLD | 40 | Transitional regime 防禦微利多（×1.023）+ insider 1.30 · 但 Healthcare & Pharma 主題 accelerating-bearish，RS 3M -12.3% | N/A | — | negative_relative_strength, bearish_theme |
| Consumer_Staples | COLD | 36 | z-1.21 便宜（+5）+ Transitional 防禦微利多 + Dividend Aristocrats 折價 · 但 uptrend 0.103 全市場最弱，RS 3M -15.1% | N/A | — | weakest_breadth, negative_relative_strength |
| Communication | COLD | 35 | z-1.80 最便宜（+5），GOOG/META 廣告基本面穩 · 但 RS 3M -15.6% 接近最弱，無主題催化 | N/A | — | weakest_relative_strength |
| Utilities | COLD | 27 | insider 3.14 重買是唯一亮點（防禦性吸籌），但 Nuclear + Utilities Defensive 主題雙 bearish · RS 3M -17.4% 全市場最弱，real_rate 壓抑 | N/A | — | weakest_relative_strength, bearish_theme, rate_duration_risk |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 40-60% | Synthesized: 40-60% | Cycle: Late
FTD: FTD_CONFIRMED (quality 100) | Market Top: 28.7 Yellow (Early Warning) | Breadth: 33.0 Weakening
Sentiment: F&G [67.8 — Greed] | VIX: 15.94 | Put/Call: n/a | SPY RSI: 64.7
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI & 半導體 / Robotics（heat 80-85，但已 Trending 末段且資金分配中——觀望不追） · Defense & Aerospace（Mature，Industrials 次要支撐） · 通膨再加速利多 Materials/Energy（被各自利空抵消，尚未轉成 RS）

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 54.49 | +1.93 | +26.7% | 1.024 |  |
| Industrials | 42.02 | +0.77 | -8.7% | 0.845 |  |
| Materials | 27.52 | -0.14 | -9.6% | 0.814 |  |
| Energy | 37.91 | +1.55 | -7.1% | 0.594 |  |
| Consumer_Discretionary | 56.08 | -0.25 | -10.5% | 0.624 |  |
| Real_Estate | 49.96 | -1.71 | -8.7% | 1.066 | 🟢 OVERSOLD VALUE |
| Financials | 19.44 | -1.28 | -9.2% | 1.631 | 🟢 OVERSOLD VALUE |
| Healthcare | 29.97 | -0.57 | -12.3% | 1.392 |  |
| Consumer_Staples | 30.34 | -1.21 | -15.1% | 1.018 | 🟢 OVERSOLD VALUE |
| Communication | 22.59 | -1.80 | -15.6% | 1.225 | 🟢 OVERSOLD VALUE |
| Utilities | 26.28 | -0.59 | -17.4% | 0.818 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.57T | $310.93 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.19T | $429.98 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.22T | $215.36 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.93T | $407.73 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $676.0B | $235.03 | Michael D. Sicilia | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $335.9B | $321.49 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $428.8B | $930.94 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $240.2B | $178.34 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $140.1B | $221.16 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $155.6B | $262.05 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $236.4B | $511.07 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $73.6B | $298.54 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $99.8B | $69.44 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $63.3B | $284.11 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $72.4B | $257.26 | Christophe Beck | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $634.2B | $153.01 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $377.6B | $189.61 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $145.0B | $118.98 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $75.0B | $140.84 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $85.8B | $57.38 | Olivier Le Peuch | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.73T | $253.72 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.57T | $418.65 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $309.5B | $310.42 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $195.4B | $275.04 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $64.5B | $43.65 | Elliott J. Hill | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $133.6B | $143.29 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $86.8B | $186.23 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $106.1B | $1075.99 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $141.8B | $200.81 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $39.5B | $90.41 | Christian H. Hillabra… | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.03T | $476.40 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $826.7B | $308.54 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $381.6B | $53.77 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $249.3B | $81.47 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $317.5B | $1076.20 | David Solomon | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.07T | $1135.00 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $362.3B | $399.00 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $546.7B | $227.10 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $390.8B | $221.22 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $292.3B | $118.36 | Robert Davis | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $327.9B | $140.83 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $436.2B | $983.25 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $339.2B | $78.83 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $195.4B | $142.97 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $943.4B | $118.55 | John R. Furner | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.47T | $369.21 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.62T | $639.18 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $347.2B | $82.45 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $174.7B | $100.59 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $194.7B | $179.89 | Srinivasan Gopalan | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $176.3B | $84.56 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $101.9B | $90.42 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $94.0B | $120.63 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $68.7B | $126.29 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $58.4B | $89.39 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.62)

> **防禦為主：窄幅科技獨撐，廣度走弱不宜加碼**
> 
> 今天守住 40-60% 曝險下緣、不追高：全場只有科技有正向相對強度，但它同時是內部人賣超最重、估值最貴的板塊，廣度在 Late-cycle 高點後持續走弱；等廣度回升或第二個板塊轉強再考慮加碼。

### Key Takeaways
1. 守住曝險於 40-60% 下緣——FTD 與廣度/頂部訊號衝突達 37.5pp，強制降一級不得積極
2. 科技降為 WARM 不加碼：唯一正 RS 但 insider 0.49 賣超 + senate -3 + PE 54x 過熱
3. 避免在 Late-cycle 窄幅領導下追新倉，全場 11 板塊有 10 個跑輸大盤
4. real_rate 2.08% + 核心 CPI 再加速，壓抑 REIT/Utilities/高倍數科技等長久期資產
5. 防禦板塊（Healthcare/Staples）僅獲 Transitional 微幅加權，基本面未轉強，不構成避風港

### Sector Actions
- **Wait**: Industrials (med) — 敘事佳但無 RS，等資金輪入確認
- **Neutral**: Technology (med) — 唯一領導但 smart-money 賣超+過熱，持有不加碼
- **Underweight**: Energy (med) — Iran deal 壓油價，RS 轉弱
- **Avoid**: Utilities (high) — RS 最弱+主題雙 bearish+利率壓抑
- **Avoid**: Consumer_Staples (med) — uptrend 0.103 廣度最弱
- **Avoid**: Real_Estate (med) — long-duration 受 real_rate 2.08% 壓抑

### Watch Next
- 廣度 composite 能否站回 40 以上、是否出現第二個正 RS 板塊（窄幅領導擴散訊號）
- 科技 insider ratio 是否回到 0.5 以上、XLK 能否創新高（分配 vs 吸籌分水嶺）
- 下週核心 CPI 是否再加速——決定 real_rate 對長久期估值的壓力
- market-top distribution_days 分數（目前 75 偏高）是否惡化進入紅區
- FTD 確認與廣度走弱的衝突是否收斂（任一方靠攏才解除降級）

---

## Top Actionable Themes

1. AI & 半導體 / Robotics（heat 80-85，但已 Trending 末段且資金分配中——觀望不追）
2. Defense & Aerospace（Mature，Industrials 次要支撐）
3. 通膨再加速利多 Materials/Energy（被各自利空抵消，尚未轉成 RS）

---

## HANDOFF TO INVESTMENT PROTOCOL

> Cache STALE（intel generated_at 07:52，距今 13.5h）→ 完整重跑 Phase 0-1。Phase 0 四層 cache 全 FRESH（age<0.3h）。signal_conflict=true（FTD 75-100% vs breadth 40-60% vs market-top 80-90%，37.5pp spread）強制降級、stance≤NEUTRAL；疊加 COLD≥3 → DEFENSIVE。Phase 4a PARALLEL_SUBAGENT（4 lane 全 isolated）；Tech 在 rotation/theme 為 HOT、news/FRED 為 COLD，分歧明顯。DA 提 4 challenge（Tech smart-money + real-rate de-rate / Industrials no-RS trap / 全場 macro veto）。XLK tail-risk ROBUST（26.9）無 fragility 降級。econ/earnings calendar 403 soft-fail，無 binary event 入帳。
