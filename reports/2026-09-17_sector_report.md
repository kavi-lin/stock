# Sector Intelligence Report — 2026-09-17

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Early · **Generated**: 2026-09-18 00:06
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Energy | WARM | 79 | 0.98 | 11 個板塊中上升家數比最高（uptrend_ratio 0.294） · 3M RS 對 SPY +14.22% 為全市場最強動能 | ROBUST | XLE | signal_conflict_downgrade, theme_divergence_bearish_oil_gas |
| Healthcare | WARM | 75 | 1.02 | 上升家數比 0.206 次高，3M RS +9.00% 展現防禦韌性 · Biotech 主題熱度 51.8 為多頭之冠，AbbVie Phase 3 數據帶來臨床催化 | ROBUST | XLV | signal_conflict_downgrade, smart_money_divergence_warning |
| Technology | WARM | 64 | 0.95 | AI、量子與資安多主題交織，Apple 與 Nvidia 生態催化劑強勁 · 20d RS +3.31%、5d RS +0.96% 短期走勢回溫 | MODERATE | XLK | macro_theme_divergence, smart_money_divergence_warning |
| Financials | WARM | 54 | 0.97 | JPM 資本市場手續費動能良好，淨利息收入具韌性 · PE z-score -1.127 具備估值安全邊際 (+5) | N/A | XLF | macro_credit_watch |
| Communication | WARM | 54 | 0.97 | PE z-score -1.458 估值處於歷史極度低檔 (+5) · 20d RS +2.03% 與 5d RS +0.40% 短期呈現修復 | N/A | XLC | low_theme_support |
| Consumer_Staples | COLD | 46 | 1.02 | 上升家數比僅 0.081，防禦板塊未能吸引實質避險資金 · 內部人買賣比僅 0.34 顯示內部資金偏向調節 | N/A | XLP | weak_breadth, insider_disposal_elevated |
| Industrials | COLD | 44 | 0.97 | 3M RS -8.71% 且 20d RS -6.16%，多週期相對弱勢明顯 · 國防航太與太空經濟主題熱度雖高但走弱（bearish 50.7） | N/A | XLI | momentum_exhaustion, supply_chain_drag |
| Materials | COLD | 35 | 0.97 | 上升家數比僅 0.053，廣度極度疲弱 · 3M RS -5.26% 且各週期皆處於負值區間 | N/A | XLB | low_breadth, global_demand_softness |
| Consumer_Discretionary | **AVOID** | 23 | 0.95 | FRED 明確列入 sector_rotation_avoid 名單 · PE TTM 高達 45.93，在實質高利率環境面臨劇烈估值壓縮 | N/A | XLY | macro_avoid_list, high_pe_compression, exposure_floor_forced_avoid |
| Real_Estate | **AVOID** | 21 | 0.99 | FRED 避開名單首位，實質利率 2.61% 嚴重推升融資成本 · 上升家數比 0.022，幾乎全板塊破位 | N/A | XLRE | macro_avoid_list, real_rate_headwind, exposure_floor_forced_avoid |
| Utilities | **AVOID** | 18 | 1.02 | 上升家數比 0.013 全市場墊底，結構性廣度崩潰 · 3M RS -9.20% 為全市場最差表現，20d RS -4.50%、5d RS -2.63% | N/A | XLU | lowest_breadth, severe_momentum_breakdown, exposure_floor_forced_avoid |

---

## Macro Context

```text
Market Regime: RISK_OFF | Breadth Ceiling: 60-75% | Synthesized: 0-25% | Cycle: Early
FTD: RALLY_ATTEMPT (quality 0) | Market Top: 43.0 Orange (Elevated Risk) | Breadth: 52.5 Neutral
Sentiment: F&G [55.3 — Neutral] | VIX: 15.68 | Put/Call: 0.85 | SPY RSI: 49.6
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Biotech & Genomics: 熱度 51.8 居首，Healthcare 防禦與研發雙輪驅動 · AI & Semiconductors: 熱度 35.2 活躍，但需提防高折現率估值折價 · Defense & Aerospace: 熱度 50.7 但方向走熊，地緣溢價被緊縮宏觀沖淡

---

## Step 6 — FRED Regime Overlay

- **Regime**: Late Cycle Tightening (confidence 0.2)
- **Favor**: Energy, Consumer Staples, Health Care, Utilities
- **Avoid**: Technology, Consumer Discretionary, Real Estate
- **Velocity highlights**: T10Y2Y:accelerating, DGS10:accelerating, DFF:decelerating
- **Rationale**: Late Cycle Tightening regime, conf 0.2 → favor: Healthcare×1.02, Energy×0.979, Consumer_Staples×1.02, Utilities×1.02; avoid: Technology×0.953, Consumer_Discretionary×0.953, Real_Estate×0.989

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Energy | 16.17 | -0.97 | +14.2% | 0.586 |  |
| Healthcare | 23.2 | -1.19 | +9.0% | 0.33 | 🟢 OVERSOLD VALUE |
| Technology | 42.54 | -0.44 | -1.7% | 0.489 |  |
| Financials | 18.53 | -1.13 | +0.7% | 0.414 | 🟢 OVERSOLD VALUE |
| Communication | 19.22 | -1.46 | +0.2% | 0.433 | 🟢 OVERSOLD VALUE |
| Consumer_Staples | 27.99 | -1.60 | -3.4% | 0.363 | 🟢 OVERSOLD VALUE |
| Industrials | 27.24 | -1.05 | -8.7% | 0.387 | 🟢 OVERSOLD VALUE |
| Materials | 23.04 | -1.17 | -5.3% | 0.382 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 45.93 | -1.53 | -6.0% | 0.301 | 🟢 OVERSOLD VALUE |
| Real_Estate | 36.98 | -1.22 | -5.0% | 0.381 | 🟢 OVERSOLD VALUE |
| Utilities | 22.74 | -1.12 | -9.2% | 0.362 | 🟢 OVERSOLD VALUE |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $677.0B | $163.34 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $421.3B | $211.52 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $161.5B | $132.54 | Andrew O'Brien | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $77.2B | $144.93 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $77.6B | $52.30 | Olivier Le Peuch | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.07T | $1138.21 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $340.8B | $375.26 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $644.1B | $267.28 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $463.9B | $262.58 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $358.0B | $144.95 | Robert Davis | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.88T | $332.41 | John Ternus | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.64T | $490.30 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.18T | $213.90 | Jensen Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.62T | $339.51 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $412.6B | $143.24 | Michael D. Sicilia | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.12T | $520.67 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $934.9B | $348.92 | Jamie Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $411.6B | $57.99 | Brian T. Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $262.6B | $86.84 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $277.9B | $942.00 | David Michael Solomon | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.15T | $342.87 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.72T | $673.31 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $318.2B | $76.41 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $185.8B | $106.97 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $189.1B | $176.26 | Srinivasan Gopalan | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $349.5B | $147.04 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $396.4B | $893.74 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $378.1B | $87.87 | Henrique Gnani Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $183.5B | $134.34 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $855.5B | $107.50 | John Furner | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $324.7B | $312.90 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $360.5B | $782.72 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $265.3B | $196.83 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $65.8B | $207.66 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $166.9B | $280.92 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $213.8B | $462.09 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $78.0B | $321.46 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $99.6B | $69.25 | Kathleen L. Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $63.9B | $287.08 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $77.1B | $274.08 | Christophe Beck | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.65T | $245.96 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.41T | $358.08 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $301.6B | $302.47 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $176.6B | $248.56 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $52.9B | $35.78 | Elliott J. Hill | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $124.8B | $133.76 | Daniel S. Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $82.2B | $176.39 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $100.3B | $1016.16 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $169.0B | $234.59 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $32.0B | $73.22 | Christian H. Hillabra… | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $167.7B | $80.37 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $99.2B | $86.23 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $91.8B | $117.76 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $65.7B | $120.69 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $53.4B | $81.72 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.65)

> **防禦：訊號衝突疊加實質高利率，嚴控曝險靜待確認**
> 
> 今天嚴格將總部位控制在 0-25% 並迴避利率敏感資產；因為反彈嘗試尚未確認為 FTD 且廣度低迷，疊加實質利率高達 2.61%；等待確認日或均線站穩再考慮加碼。

### Key Takeaways
1. 整體曝險壓制於 0-25%：反彈嘗試尚未確認為 FTD，大盤 8MA 跌破 200MA，為本場定調主因
2. 全面迴避公用事業、房地產與可選消費：實質利率 2.61% 對高負債與高存續期板塊構成直接估值壓縮
3. 續抱能源與醫療但不可追高：兩者相對強度領先但內部人持續減持，嚴格設置停損防線
4. 科技板塊以觀察為主：雖然 AI 催化劑活躍，但在 FRED 避開名單與高折現率下缺乏加碼依據
5. 現金部位維持高檔：耐心等待實質利率與殖利率曲線陡峭化趨緩，保留火藥應對變局

### Sector Actions
- **Wait**: Technology (med) — AI催化充沛但折現率壓制估值
- **Neutral**: Energy (med) — 相對動能最強但原油走熊主題壓抑
- **Neutral**: Healthcare (med) — 防禦估值偏低但內部人大幅減持
- **Avoid**: Consumer_Discretionary (high) — PE過高且FRED明確列為避開
- **Avoid**: Real_Estate (high) — 實質利率2.61%重創REITs融資
- **Avoid**: Utilities (high) — 上升家數比0.013全表最差

### Watch Next
- FTD 確認進展：關注大盤能否在接下來數日內出現帶量突破的確認日（FTD），打破當前嘗試期猶豫
- HUBG 財報 09-17：檢驗物流與貨運需求，作為工業與週期性板塊景氣的重要即時讀數
- 10 年期實質利率走勢：若持續攀升突破 2.70%，將引發科技與房地產進一步去槓桿拋售
- 原油期貨支撐與 XLE 動能：若 XLE 5 日相對強度連續 10 個交易日為負，觸發能源板塊強制停損
- AutoZone (AZO) 財報 09-22：觀察汽車後市場與可選消費在緊縮後期的韌性

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Healthcare | — | — |  |
| Technology | — | — |  |
| Energy | — | — |  |

---

## Top Actionable Themes

1. Biotech & Genomics: 熱度 51.8 居首，Healthcare 防禦與研發雙輪驅動
2. AI & Semiconductors: 熱度 35.2 活躍，但需提防高折現率估值折價
3. Defense & Aerospace: 熱度 50.7 但方向走熊，地緣溢價被緊縮宏觀沖淡
4. Real Estate & REITs: 熱度 49.9 走熊，融資成本劇增引發持續去槓桿

---

## HANDOFF TO INVESTMENT PROTOCOL

> 2026-09-17 盤前掃描：FTD 處於 RALLY_ATTEMPT Day 1，與廣度 Neutral (52.5) 形成 55pp 訊號衝突，強制曝險上限 0-25% 並定調 DEFENSIVE。FRED 宏觀實質利率高達 2.61%，避開名單鎖定 Tech/Discretionary/REITs。所有板塊無 HOT 評級，防守為上。
