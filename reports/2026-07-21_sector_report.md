# Sector Intelligence Report — 2026-07-21

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-07-21 07:43
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Energy | WARM | 86 | 1.04 | 全市場唯一 uptrend_ratio 明顯站上自身 MA10（0.452 vs 0.300）且 slope +0.031 為正 · RS20d +7.2% / RS5d +2.7% 同步轉強，PE 19.03 為 11 個產業最低 | ROBUST | XLE | signal_conflict_downgrade, consensus_warning, event_driven_catalyst, fred_real_rate_high |
| Financials | WARM | 67 | 1.04 | 唯一樣本數足夠的財報脈動：30 天 8 篇 beat_rate 100%、surprise +18.2% · PE 18.83、PEz1y −1.39 且 uptrend 0.293 < 0.3 → 估值 penalty +5（oversold value） | ROBUST | XLF | fred_real_rate_high, bond_market_warning |
| Real_Estate | WARM | 65 | 0.96 | uptrend_ratio 0.373 站上 MA10 0.307、slope +0.005，RS20d +2.7% / RS5d +2.6% · PEz1y −2.80 為 11 個產業最低（1 年估值底部） | ROBUST | XLRE | smart_money_divergence, fred_real_rate_high, rate_sensitive |
| Healthcare | WARM | 52 | 0.96 | PE 23.41、PEz1y −1.50 且 uptrend < 0.3 → 估值 penalty +5 · 30 天 4 篇財報全數 beat、surprise +13.4%，analyst_revision_net +141 | N/A | XLV | breadth_deterioration, mega_cap_concentration |
| Communication | COLD | 48 | 1.04 | RS3m −12.4% 為 11 個產業最弱，雖 RS20d +3.0% 有短線反彈 · PEz1y −1.45 且 uptrend 0.209 < 0.3 → 估值 penalty +5 | N/A | XLC | earnings_overhang, weakest_3m_rs |
| Industrials | COLD | 45 | 1.07 | 被 Theme / News / FRED 三個 lane 同列 HOT，但 RS3m −2.4% / RS20d −1.8% / RS5d −0.1% 三窗口全負 · uptrend_ratio 0.171 低於自身 MA10 0.179、slope −0.0121 | N/A | XLI | consensus_vs_price_divergence, fred_real_rate_high, all_window_negative_rs |
| Technology | COLD | 41 | 1.07 | R7 動能耗盡：RS3m +10.51% 但 RS20d −7.09%、RS5d −1.78%（17.6pp 反轉，全表最大） · R5 聰明錢背離：insider ratio 0.476 < 0.5（買 188 / 賣 395, n=16）、senate net −3 | N/A | XLK | momentum_exhaustion, smart_money_divergence, fred_real_rate_high, expensive_valuation, china_sanction_risk |
| Consumer_Staples | COLD | 37 | 0.90 | FRED Soft Landing regime 明列 avoid → step6 multiplier 0.896 · PEz1y −1.64 且 uptrend 0.153 → 估值 penalty +5，但 PE 28.88 對防禦股偏貴 | N/A | XLP | fred_sector_avoid, no_catalyst |
| Materials | **AVOID** | 35 | 1.04 | uptrend_ratio 0.096 為 11 個產業最低，RS3m −9.0% · Greer 稱對數十國全面新關稅「很快就會有動作」→ 原物料直接曝險 | N/A | XLB | exposure_floor_avoid, worst_breadth, tariff_exposure |
| Utilities | **AVOID** | 34 | 0.90 | Theme / News / FRED 三個 lane 同列 COLD（唯一被三方看空者） · FRED avoid 名單 → step6 multiplier 0.896；殖利率曲線陡化（T10Y2Y accelerating）不利 | N/A | XLU | exposure_floor_avoid, fred_sector_avoid, no_catalyst |
| Consumer_Discretionary | **AVOID** | 33 | 1.07 | TSLA（$1.4T）7/22 盤後財報 = 48h 內 binary → 各分項已套用 ×0.70 · PE_TTM 49.19 全市場最貴，RS3m −9.5% | N/A | XLY | exposure_floor_avoid, binary_risk_within_48h, most_expensive_pe, tariff_exposure |

---

## Macro Context

```text
Market Regime: RISK_OFF | Breadth Ceiling: 75-90% | Synthesized: 0-25% | Cycle: Late
FTD: RALLY_ATTEMPT (quality 0) | Market Top: 48.1 Orange (Elevated Risk) | Breadth: 67.0 Healthy
Sentiment: F&G [56.2 — Neutral] | VIX: 17.7 | Put/Call: n/a | SPY RSI: 51.0
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Robotics & Automation（heat 43.2, Accelerating, confidence Low）——主題最熱但對應的 Technology/Industrials 價格動能皆為負，暫不追 · AI & Semiconductors（heat 42.1, Accelerating）——受 Amazon Trainium 侵蝕 NVDA 敘事與中國 AI 制裁威脅雙重壓抑 · Oil & Gas Refining & Marketing——產業動能分數 99.25 全市場第一（1M +24.6%、YTD +75.7%），是本輪唯一價格與催化劑同向的細分族群

---

## Step 6 — FRED Regime Overlay

- **Regime**: Soft Landing (confidence 0.72)
- **Favor**: Technology, Industrials, Consumer Discretionary
- **Avoid**: Consumer Staples, Utilities
- **Velocity highlights**: T10Y2Y:accelerating, DFF:decelerating, CPIAUCSL:decelerating
- **Rationale**: Soft Landing regime, conf 0.72 → favor: Industrials×1.074, Technology×1.074, Consumer_Discretionary×1.074; avoid: Consumer_Staples×0.896, Utilities×0.896

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Energy | 19.03 | -0.52 | +0.2% | 0.181 |  |
| Financials | 18.83 | -1.39 | +1.4% | 0.164 | 🟢 OVERSOLD VALUE |
| Real_Estate | 28.63 | -2.80 | -3.8% | 0.211 |  |
| Healthcare | 23.41 | -1.50 | +3.3% | 0.162 | 🟢 OVERSOLD VALUE |
| Communication | 22.53 | -1.45 | -12.4% | 0.116 | 🟢 OVERSOLD VALUE |
| Industrials | 30.06 | -0.84 | -2.4% | 0.131 |  |
| Technology | 43.39 | -0.61 | +10.5% | 0.145 |  |
| Consumer_Staples | 28.88 | -1.64 | -3.0% | 0.129 | 🟢 OVERSOLD VALUE |
| Materials | 24.8 | -0.52 | -9.0% | 0.169 |  |
| Utilities | 24.68 | -0.91 | -7.4% | 0.186 |  |
| Consumer_Discretionary | 49.19 | -1.14 | -9.5% | 0.17 | 🟢 OVERSOLD VALUE |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $615.1B | $148.40 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $377.7B | $189.67 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $140.9B | $115.67 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $75.1B | $141.09 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $69.4B | $46.39 | Olivier Le Peuch | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.06T | $491.41 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $908.1B | $338.89 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $428.9B | $60.44 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $264.2B | $86.34 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $311.4B | $1055.45 | David Solomon | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $137.5B | $147.47 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $77.9B | $167.10 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $100.3B | $1017.31 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $172.9B | $244.86 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $34.1B | $78.17 | Christian H. Hillabra… | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.08T | $1146.80 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $383.1B | $421.85 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $599.0B | $248.85 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $447.7B | $253.42 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $307.3B | $124.41 | Robert Davis | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.26T | $351.99 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.64T | $645.85 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $284.7B | $67.60 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $167.5B | $96.44 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $211.7B | $195.64 | Srinivasan Gopalan | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $356.1B | $341.29 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $398.3B | $864.75 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $261.9B | $194.47 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $71.7B | $226.18 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $175.8B | $296.16 | Vincenzo James Vena | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.80T | $326.59 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $2.99T | $402.29 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $4.92T | $203.28 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.80T | $378.16 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $349.6B | $121.37 | Michael D. Sicilia | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $347.3B | $149.14 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $415.0B | $935.80 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $353.3B | $82.11 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $185.0B | $135.46 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $892.9B | $112.20 | John R. Furner | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $236.9B | $512.05 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $79.8B | $323.55 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $84.5B | $58.80 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $66.1B | $296.71 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $75.6B | $268.71 | Christophe Beck | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $183.7B | $88.06 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $106.5B | $94.50 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $98.2B | $125.90 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $71.3B | $131.05 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $59.3B | $90.75 | Jeffrey Walker Martin | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.69T | $249.99 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.39T | $369.57 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $332.1B | $333.08 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $190.1B | $267.58 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $64.3B | $43.47 | Elliott J. Hill | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.62)

> **防禦：無 FTD 確認前，能源反彈只當交易不當趨勢**
> 
> 今天不加碼、先守住現金部位，因為大盤仍在無 FTD 確認的反彈中、NASDAQ 出貨日已達 8 天，且全市場僅約兩成個股維持上升趨勢；要等出現真正的 Follow-Through Day、廣度回升，才值得把曝險拉回正常水位。

### Key Takeaways
1. 維持防禦：三大訊號分歧達 70pp，取最保守的 0-25% 曝險，今天不做新的方向性加碼
2. 能源分數最高（86）但仍降為 WARM——利多是油輪遇襲與颶風停產兩起 48h 突發，RS3m 僅 +0.20% 顯示中期動能沒跟上
3. 科技減碼至核心：3 個月領先 +10.5% 已翻成 20 日 −7.1%，內部人買賣比 0.476、參議員近 30 天淨賣 3 筆
4. 工業被三個 lane 同時看多但三個時間窗 RS 全負，不因共識進場，等 RS20d 轉正再說
5. 原物料、公用事業、非核心消費列為 AVOID：廣度最差、無催化劑、TSLA 財報在 48 小時內

### Sector Actions
- **Overweight**: Financials (med) — 唯一財報樣本足夠且 100% beat
- **Wait**: Energy (med) — 供給中斷屬事件驅動，等 RS20d 站穩
- **Wait**: Real_Estate (low) — 估值最低但實質利率 2.33% 逆風
- **Underweight**: Technology (high) — 動能耗盡疊加內部人淨賣
- **Avoid**: Consumer_Discretionary (high) — TSLA 財報 48h 內且本益比最貴
- **Avoid**: Utilities (high) — 三方看空且無任何催化劑

### Watch Next
- TSLA 7/22 盤後財報（binary，48h 內）——結果將決定 Consumer_Discretionary 是否脫離 AVOID
- 是否出現 Follow-Through Day：目前 rally_day_count 16、尚無 FTD，確認後曝險上限才可上調
- NASDAQ 有效出貨日是否升破 9 天：升破則進一步降低曝險
- 美國貿易代表 Greer 的全面關稅公告時點——直接衝擊 Materials 與 Consumer_Discretionary
- 7/27 耐久財訂單（前值 −4.5%、預估 +0.3%）與 7/28 CB 消費者信心（前值 91.2）

---

## Devil's Advocate Challenges (Accepted 0/4)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Energy — HOT | — | 利多建立在極窄的催化劑上：兩則皆為 48h 內天氣/地緣突發（CPC 因油輪遇襲停收哈薩克原油、Chevron 因熱帶風暴關閉美灣平台），歷史上多在 1-3 週內反轉，非結構性需求訊號。中期動能其實很弱：RS3m 僅 +0.20%，與 RS20d +7.20% / RS5d +2.70% 的急拉形成典型窄視窗反轉；此時大盤 RISK_OFF、Late cycle、Distribution Days 100/100 CRITICAL，全市場 uptrend_ratio 平均僅 0.226。 |
| Industrials — HOT | — | 被三條獨立 lane 同時提為 HOT，但自身價格數據全面否定：RS3m −2.40%、RS20d −1.80%、RS5d −0.10% 三窗口全負，uptrend_ratio 0.171 低於自身 MA10 0.179，slope −0.0121 持續惡化。News lane 引用的只是單一個股事件（RTX 逾 20 億美元合約），Theme lane 自承 17 個主題 confidence 全為 Low，FRED 的支持完全來自被統一套用在 Industrials/Financials/Energy 三者的 real_rate_high ov... |
| Technology — HOT | — | R7 動能衰竭：RS3m +10.51% 已完全反轉為 RS20d −7.09%、RS5d −1.78%，三個月上升趨勢在最近 20 天與 5 天雙雙破壞。R5 聰明錢背離：insider_acquired_disposed_ratio_q 0.476 低於 0.5 門檻（16 筆申報中買 188 / 賣 395），同時 senate_net_buy_30d −3（0 買 / 3 賣）——內部人與參議員同步淨賣出，恰好發生在 Theme lane 喊 HOT 的同一時點。疊加 PE_TTM 43.39 與 uptrend_ratio 0.143 低... |
| Real_Estate — HOT | — | R5 聰明錢背離：senate_net_buy_30d −1（0 買 / 1 賣），即使 insider ratio 1.957 表面偏多，兩個聰明錢訊號方向不一致；此訊號恰與 PEz1y −2.80「一年最便宜」敘事相牴觸，須警惕 value trap。R4：real_rate_preferred 2.33% > 2.0% 對 REIT 資本化率與融資成本是直接基本面壓力，而 Rotation lane 支持 HOT 的理由（uptrend 0.373 > MA10 0.307）純屬技術訊號，未處理此利率逆風；Real_Estate 過去 30 ... |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Industrials | — | — |  |
| Technology | — | — |  |
| Technology | — | — |  |
| Real_Estate | — | — |  |
| Healthcare | — | — |  |
| Energy | — | — |  |

---

## Top Actionable Themes

1. Robotics & Automation（heat 43.2, Accelerating, confidence Low）——主題最熱但對應的 Technology/Industrials 價格動能皆為負，暫不追
2. AI & Semiconductors（heat 42.1, Accelerating）——受 Amazon Trainium 侵蝕 NVDA 敘事與中國 AI 制裁威脅雙重壓抑
3. Oil & Gas Refining & Marketing——產業動能分數 99.25 全市場第一（1M +24.6%、YTD +75.7%），是本輪唯一價格與催化劑同向的細分族群
4. Gold & Precious Metals（heat 30.1, bullish, Emerging）——關稅與地緣風險升溫下的對沖選項，但 Materials 整體廣度僅 0.096

---

## HANDOFF TO INVESTMENT PROTOCOL

> Cache 判定 STALE（最新 sector_intel 為 2026-07-20），完整重跑 Phase 0–5。Phase 3 prefetch 首次執行時 valuation 與 smart_money 因 FMP 429 rate limit 失敗（並行 5 個 fetch 打同一端點），改為序列重試後兩者皆 rc=0，四個 HARD cache 齊備。Phase 0 三訊號合成：breadth 82.5 / FTD 12.5 / market_top 67.5 → 取最保守 0-25%，spread 70pp 觸發 signal_conflict=true。Phase 4a 四 lane 並行（Sonnet）全數回傳；Industrials 被 Theme/News/FRED 三方提為 HOT，但 RS 三窗口全負，採納 DA 挑戰維持 COLD。Energy 分數 86 達 HOT 門檻，因 STEP G（signal_conflict + HOT）強制降為 WARM，全日無 HOT 產業。STEP B（synthesized_exposure < 40%）強制標記 Materials / Utilities / Consumer_Discretionary 為 AVOID。tail-risk 對 XLE / XLF / XLRE 執行，三檔皆 ROBUST，STEP D 無降級。Step 5 WebSearch 跳過（general_news cache available=true 已涵蓋當日 narrative，無未涵蓋突發）。DA 觸發規則：R4（real_rate 2.33% > 2.0%）、R5（Technology / Real_Estate）、R7（Technology）；R6 未觸發（全產業 pt_sample_size=0）。institutional Q-on-Q 全產業 sample_size=0，本輪無 13F 訊號。
