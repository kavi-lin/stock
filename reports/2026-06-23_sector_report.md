# Sector Intelligence Report — 2026-06-23

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-06-23 20:31
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Technology | WARM | 77 | 1.00 | AI/半導體題材熱度 79.1 全場最高，RS 3M +27.3% 動能最強 · 但內部人 acq/disp 0.45<0.5 邊漲邊賣、PE z+1.97 偏貴、PE_TTM 55.7 | MODERATE | XLK | signal_conflict_downgrade, smart_money_divergence, real_rate_headwind, binary_earnings_within_48h, overbought_valuation |
| Industrials | WARM | 65 | 1.00 | 廣度 0.377 全場最高 + 估值便宜(z-1.01、PE 31.3) · 題材熱度 77.2 次高；Rotation/Theme/FRED 三 lane 一致看多 | LOW | XLI | weak_absolute_breadth, ftd_unconfirmed |
| Financials | WARM | 51 | 1.00 | 殖利率曲線陡化(T10Y2Y accelerating)利多淨利差 · PE 20.1 全場最便宜、z-1.09 | LOW | XLF | low_regime_confidence |
| Materials | COLD | 45 | 1.00 | 題材熱度 61.7 中等但廣度 0.227 偏弱 · RS 3M -4.9%、無明確催化 | MODERATE | — | weak_breadth |
| Consumer_Staples | COLD | 39 | 1.02 | z-1.25 估值偏低(+5 oversold penalty) · RS 3M -13.7% 動能弱、廣度 0.171 | LOW | — | weak_rotation, oversold_value |
| Real_Estate | COLD | 39 | 1.00 | Theme/News/FRED 三 lane 一致看空 · real_rate 2.19% 直擊長久期 REITs | MODERATE | — | real_rate_headwind, three_lane_cold_consensus, oversold_value |
| Consumer_Discretionary | COLD | 38 | 1.00 | 題材熱度僅 33.9、RS -8.1% · PE 55.5 偏貴但無動能支撐 | MODERATE | — | weak_theme, expensive_valuation |
| Healthcare | COLD | 38 | 1.02 | 內部人買超 1.64 為全場第二強訊號 · 但 RS 3M -11.5%、無活躍題材帶動 | LOW | — | weak_rotation, no_active_theme |
| Utilities | **AVOID** | 34 | 1.02 | 廣度 0.062 全場最低、RS -14.6% · 內部人買超 3.31 最強但價格未跟上 | MODERATE | — | exposure_floor_avoid, real_rate_headwind, lowest_breadth |
| Energy | **AVOID** | 34 | 1.00 | RS 3M -23.6% 全場最差、廣度 0.074 倒數第二 · 題材熱度 61.1 但資金持續流出 | HIGH | — | exposure_floor_avoid, worst_rotation |
| Communication | **AVOID** | 31 | 1.00 | RS 3M -19.6%、廣度 0.156、無活躍題材 · z-1.79 超賣(+5)但缺催化 | MODERATE | — | exposure_floor_avoid, weak_momentum, no_active_theme |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 60-75% | Synthesized: 0-25% | Cycle: Late
FTD: FTD_WINDOW (quality 0) | Market Top: 32.2 Yellow (Early Warning) | Breadth: 53.0 Neutral
Sentiment: F&G [54.1 — Neutral] | VIX: 19.52 | Put/Call: n/a | SPY RSI: 53.6
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: AI/半導體題材熱度全場最高但內部人賣超+MU 財報在即，核心持有不追高 · 工業股廣度全場最佳(0.377)+估值便宜(z-1.01)，DEFENSIVE 中相對首選 · 殖利率曲線陡化利多金融淨利差，但 real rate 2.19% 壓抑長久期(公用/REITs)

---

## Step 6 — FRED Regime Overlay

- **Regime**: Transitional (confidence 0.47)
- **Favor**: —
- **Avoid**: —
- **Velocity highlights**: T10Y2Y:accelerating, DGS10:accelerating, DFF:decelerating
- **Rationale**: Transitional regime, conf 0.47 → 防禦小幅加權 ConsumerStaples×1.024, Healthcare×1.024；cyclical 中性 ×1.0。favor/avoid 名單皆空，overlay 近中性。

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Technology | 55.66 | +1.97 | +27.3% | 0.752 |  |
| Industrials | 31.26 | -1.01 | -2.3% | 0.798 |  |
| Financials | 20.13 | -1.09 | -5.4% | 0.719 |  |
| Materials | 27.84 | -0.04 | -4.9% | 0.73 |  |
| Consumer_Staples | 30.12 | -1.25 | -13.7% | 0.887 | 🟢 OVERSOLD VALUE |
| Real_Estate | 48.97 | -1.59 | -6.3% | 0.847 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 55.45 | -0.31 | -8.1% | 0.993 |  |
| Healthcare | 29.92 | -0.57 | -11.5% | 1.07 |  |
| Utilities | 26.02 | -0.83 | -14.6% | 1.049 |  |
| Energy | 35.07 | +0.98 | -23.6% | 0.791 |  |
| Communication | 21.57 | -1.79 | -19.6% | 1.118 | 🟢 OVERSOLD VALUE |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.42T | $301.00 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $2.76T | $371.74 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.09T | $210.25 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.89T | $396.77 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $512.2B | $178.08 | Michael D. Sicilia | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $375.0B | $358.95 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $467.2B | $1014.14 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $245.8B | $182.55 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $146.1B | $230.64 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $155.1B | $261.27 | Vincenzo James Vena | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.05T | $488.96 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $886.5B | $330.83 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $408.3B | $57.53 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $255.9B | $83.62 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $324.3B | $1099.23 | David Solomon | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $237.4B | $513.23 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $79.1B | $320.82 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $99.2B | $69.02 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $63.1B | $283.53 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $76.3B | $271.12 | Christophe Beck | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $348.6B | $149.70 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $421.4B | $950.31 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $342.0B | $79.50 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $194.1B | $141.97 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $935.5B | $117.55 | John R. Furner | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $133.0B | $142.67 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $82.7B | $177.43 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $109.8B | $1112.92 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $147.4B | $208.78 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $36.4B | $83.45 | Christian H. Hillabra… | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.52T | $234.53 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.54T | $409.60 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $329.7B | $330.62 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $194.6B | $273.83 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $64.5B | $43.60 | Elliott J. Hill | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.04T | $1104.06 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $368.0B | $405.25 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $555.9B | $230.91 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $408.4B | $231.14 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $283.8B | $114.91 | Robert Davis | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $181.3B | $86.94 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $105.5B | $93.61 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $96.8B | $124.22 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $70.3B | $129.22 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $60.0B | $91.78 | Jeffrey Walker Martin | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $571.6B | $137.90 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $346.9B | $174.19 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $132.8B | $109.03 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $70.0B | $131.35 | Ezra Y. Yacob | _TBD_ |
| **SLB** | SLB N.V. | Oil & Gas Equipment &… | $71.2B | $47.65 | Olivier Le Peuch | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.18T | $345.96 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.43T | $562.39 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $309.7B | $73.54 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $178.3B | $102.68 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $195.8B | $180.97 | Srinivasan Gopalan | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.62)

> **指數近高點但內部轉弱，轉守等 FTD 確認**
> 
> 今天先收手、別追高——指數雖離高點僅 1.9%，但只有約兩成個股在上升趨勢、FTD 還沒確認、breadth 與頂部訊號嚴重背離；先守住現有核心(科技/工業)、暫不開新倉，等 follow-through day 出現或 6/25 PCE 落地再決定是否升曝險。

### Key Takeaways
1. 轉守主因：FTD 未確認(曝險建議 0-25%)+ 全市場廣度僅 0.23 + 三訊號背離 72pp，指數強是少數權值撐盤
2. 守住科技但不追高：題材熱度全場最高，惟內部人賣超(0.45)+ real rate 2.19% + MU 6/24 財報在即
3. 工業為防禦中相對首選：廣度 0.377 全場最高、估值便宜、三 lane 一致看多，可小量試探
4. 避開公用/能源/通訊：廣度與動能全場最弱，real rate 壓抑公用殖利率溢價
5. 等 6/25 Core PCE(YoY 估 4.0% 黏著)與 FTD 確認為升曝險的兩大前提

### Sector Actions
- **Overweight**: Industrials (med) — 廣度全場最高+估值便宜+三lane看多
- **Wait**: Financials (low) — 陡化曲線利多但等壓力測試結果
- **Neutral**: Technology (med) — 核心持有不追高，MU財報+內部人賣超
- **Avoid**: Real_Estate (med) — real rate壓長久期+三lane看空
- **Avoid**: Utilities (high) — 廣度最低+殖利率溢價被real rate吞沒
- **Avoid**: Energy (high) — RS全場最差-23.6%、資金持續流出

### Watch Next
- 6/24 MU(Micron)財報(~36h，binary)— AI-memory/HBM read-through，牽動整個半導體複合體
- 6/25 Core PCE(May) MoM 估+0.3%、YoY 估 4.0% 黏著 — Fed 偏好通膨指標，定調降息路徑
- FTD(Follow-Through Day)是否確認 — 目前 rally day 7 仍在 window，確認才可升曝險
- NASDAQ distribution day 是否累積第 7 根 — 機構出貨壓力訊號
- 6/24 Fed 銀行壓力測試結果 — Financials 催化

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | — | — |  |
| Utilities | — | — |  |
| Healthcare | — | — |  |

---

## Top Actionable Themes

1. AI/半導體題材熱度全場最高但內部人賣超+MU 財報在即，核心持有不追高
2. 工業股廣度全場最佳(0.377)+估值便宜(z-1.01)，DEFENSIVE 中相對首選
3. 殖利率曲線陡化利多金融淨利差，但 real rate 2.19% 壓抑長久期(公用/REITs)
4. FTD 未確認 + 全市場廣度僅 0.23，等 follow-through 與 PCE 落地再升曝險

---

## HANDOFF TO INVESTMENT PROTOCOL

> Phase 0 三訊號嚴重衝突(breadth 67.5 / FTD 12.5 / market-top 85，差 72.5pp)→ signal_conflict=true → stance 封頂並落 DEFENSIVE。synth_exposure 0-25%<40% 觸發強制≥3 AVOID(Utilities/Energy/Communication)。prefetch 首跑 valuation+smart_money 遇 FMP 429，已個別重抓 rc=0。4 lane 並行隔離(PARALLEL_SUBAGENT)+DA R4/R5 雙觸發於 Technology。無 HOT(指數強但內部弱)；Industrials 為相對首選。
