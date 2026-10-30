# Sector Intelligence Report — 2026-10-20

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Mid · **Generated**: 2026-10-20 21:23
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Healthcare | COLD | 44 | 1.04 | 近三個月相對強勢(+7.2%)但整體廣度偏弱 · 內部人買賣比僅0.411低於門檻 | ROBUST | XLV | market_correction, weak_breadth, binary_risk_within_48h, smart_money_divergence |
| Energy | COLD | 40 | 0.96 | 上升占比33.3%為各板塊最高 · 油氣主題進入力竭階段(Exhausting) | ROBUST | XLE | market_correction, weak_breadth, binary_risk_within_48h, theme_exhaustion |
| Consumer_Staples | COLD | 34 | 1.04 | 上升比率27.6%相對穩定 · 防禦屬性獲FRED制度偏好加持 | N/A | XLP | market_correction, weak_breadth |
| Consumer_Discretionary | COLD | 32 | 0.91 | FRED避免配置名單 · 實質利率高達2.79%壓抑消費信貸 | N/A | XLY | market_correction, weak_breadth, binary_risk_within_48h, macro_theme_divergence |
| Industrials | COLD | 28 | 0.94 | 多頭比率僅12.7%，廣度嚴重萎縮 · 3個月相對強度-9.1%大幅落後大盤 | N/A | XLI | market_correction, weak_breadth, binary_risk_within_48h |
| Financials | COLD | 27 | 0.94 | 銀行板塊核心主題加速看空 · 多頭比率僅10.0%嚴重惡化 | N/A | XLF | market_correction, weak_breadth, credit_stress, binary_risk_within_48h |
| Materials | **AVOID** | 23 | 0.94 | 多頭比率僅8.8%為全市場次低 · 黃金與貴金屬主題加速看空 | N/A | XLB | market_correction, weak_breadth |
| Communication | **AVOID** | 23 | 0.94 | 多頭比率僅17.5% · Netflix財報二元風險逼近 | N/A | XLC | market_correction, weak_breadth, binary_risk_within_48h |
| Utilities | **AVOID** | 19 | 1.04 | 多頭比率僅1.3%全市場最低 · 3個月相對強度-10.4%墊底 | N/A | XLU | market_correction, weak_breadth |
| Real_Estate | **AVOID** | 18 | 0.98 | 房屋開工數據持續疲軟 · FRED總經體制列入avoid避免配置名單 | N/A | XLRE | market_correction, weak_breadth, macro_theme_divergence |
| Technology | **AVOID** | 17 | 0.91 | FRED總經體制明確列入avoid避免配置名單 · 內部人比率僅0.432顯示資金撤出 | MODERATE | XLK | market_correction, weak_breadth, macro_theme_divergence, smart_money_divergence |

---

## Macro Context

```text
Market Regime: RISK_OFF | Breadth Ceiling: 40-60% | Synthesized: 0-25% | Cycle: Mid
FTD: RALLY_ATTEMPT (quality 0) | Market Top: 56.4 Orange (Elevated Risk) | Breadth: 35.8 Weakening
Sentiment: F&G [48.5 — Neutral] | VIX: 18.72 | Put/Call: n/a | SPY RSI: 47.5
Signal Conflict: Yes | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Healthcare Sector Concentration (Trending, Heat 61.5) · Oil & Gas (Energy) (Exhausting, Heat 54.0) · Cybersecurity (Accelerating, Heat 52.8)

---

## Step 6 — FRED Regime Overlay

- **Regime**: Late Cycle Tightening (confidence 0.4)
- **Favor**: Energy, Consumer Staples, Health Care, Utilities
- **Avoid**: Technology, Consumer Discretionary, Real Estate
- **Velocity highlights**: T10Y2Y:accelerating, DFF:accelerating, CPIAUCSL:accelerating
- **Rationale**: Late Cycle Tightening regime, conf 0.4 → favor: Healthcare×1.041, Energy×0.957, Consumer_Staples×1.041; avoid: Consumer_Discretionary×0.906, Technology×0.906, Real_Estate×0.978

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Healthcare | 22.9 | -1.07 | +7.2% | 0.711 | 🟢 OVERSOLD VALUE |
| Energy | 15.98 | -0.98 | +13.5% | 0.889 |  |
| Consumer_Staples | 29.94 | -0.59 | +1.3% | 1.149 |  |
| Consumer_Discretionary | 46.12 | -1.36 | -2.8% | 0.917 | 🟢 OVERSOLD VALUE |
| Financials | 18.81 | -0.83 | -4.3% | 0.741 |  |
| Industrials | 26.61 | -1.39 | -9.1% | 0.803 | 🟢 OVERSOLD VALUE |
| Materials | 24.18 | -0.62 | -0.7% | 0.752 |  |
| Communication | 19.33 | -1.23 | -2.4% | 0.651 | 🟢 OVERSOLD VALUE |
| Technology | 40.51 | -0.99 | +0.4% | 1.103 |  |
| Utilities | 22.73 | -0.99 | -10.4% | 0.683 |  |
| Real_Estate | 39.32 | -0.77 | -10.2% | 0.997 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.17T | $1247.87 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $363.3B | $404.73 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $612.5B | $254.15 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $504.9B | $285.73 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $360.2B | $146.00 | Robert Davis | _TBD_ |

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxonmobil Holdings Corpora… | Oil & Gas Integrated | $736.0B | $179.00 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $444.2B | $224.81 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $175.9B | $146.46 | Andrew O'Brien | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $83.1B | $158.35 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $72.6B | $48.94 | Olivier Le Peuch | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $367.4B | $158.16 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $439.2B | $991.05 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $403.0B | $93.67 | Henrique Gnani Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $180.1B | $132.15 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $944.5B | $118.69 | John Furner | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.77T | $256.44 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.42T | $359.84 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $306.2B | $306.88 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $170.9B | $241.49 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $54.7B | $36.84 | Elliott J. Hill | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.14T | $531.36 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $896.1B | $337.11 | Jamie Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $358.7B | $51.29 | Brian T. Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $250.6B | $82.86 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $256.5B | $880.79 | David Michael Solomon | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $324.3B | $312.57 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $331.4B | $721.04 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $257.7B | $191.23 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $66.8B | $210.80 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $170.5B | $286.96 | Vincenzo James Vena | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $230.6B | $500.22 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $80.2B | $330.50 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $99.2B | $69.03 | Kathleen L. Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $66.6B | $298.91 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $79.8B | $284.53 | Christophe Beck | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.18T | $343.08 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.78T | $697.22 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $289.0B | $69.41 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $189.2B | $109.58 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $169.6B | $158.12 | Srinivasan Gopalan | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $5.02T | $343.75 | John Ternus | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $3.95T | $531.44 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $5.20T | $215.72 | Jensen Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.61T | $336.59 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $393.4B | $130.10 | Michael D. Sicilia | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $164.3B | $78.78 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $103.9B | $90.28 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $93.8B | $120.29 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $68.8B | $126.31 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $54.0B | $82.66 | Jeffrey Walker Martin | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $117.6B | $123.78 | Daniel S. Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $86.0B | $184.66 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $96.5B | $977.95 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $168.9B | $234.41 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $35.7B | $81.69 | Christian H. Hillabra… | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.4)

> **防禦至上：總曝險壓縮至極限，全面暫停多頭建倉**
> 
> 今日全面拉高現金並暫停新建倉，因市場廣度惡化且缺乏確認買點，等待廣度重返健康或確認底部訊號出現再行介入。

### Key Takeaways
1. 鎖定現金水位：合成曝險降至0-25%極限水準，市場廣度疲弱(35.8)且未見FTD確認買點。
2. 嚴格執行停損：對評估為AVOID之科技、工業、公用事業等板塊清倉或嚴格停損。
3. 暫緩追高能源與醫療：雖具相對強勢但受內部人賣超及高實質利率壓制，僅列觀察名單。
4. 緊盯財報窗口衝擊：Netflix、Tesla等巨頭財報接連公布，防範盤面進一步波動擴大。

### Sector Actions
- **Neutral**: Consumer_Staples (med) — 走勢平穩且獲FRED制度偏好加持，防禦持有
- **Underweight**: Healthcare (med) — 相對強勢但內部人賣超且高利率壓制防禦溢價
- **Underweight**: Energy (med) — 多頭比率最高但油氣主題力竭且總體風險壓抑
- **Avoid**: Technology (high) — 名列FRED避免清單，內部人撤出且估值面臨折現壓力
- **Avoid**: Utilities (high) — 多頭比率僅1.3%墊底，相對強度嚴重破位
- **Avoid**: Real_Estate (high) — 開工數據持續疲軟且高房貸利率壓制資產收益

### Watch Next
- 監控 Netflix (NFLX) 與 Intuitive Surgical (ISRG) 財報公布後的市場反應與通訊/醫療板塊承接力道。
- 關注 Tesla (TSLA) 財報與 AI 資本支出指引對科技與可選消費的二元外溢效應。
- 追蹤 GE Aerospace、RTX 等工業龍頭業績表現對供應鏈壓力的最新評估。
- 觀察市場廣度 8MA 能否止跌回升或出現低檔極值翻揚的底部確認訊號。

---

## Devil's Advocate Challenges (Accepted 0/3)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Healthcare — HOT | — | 內部人買賣比僅 0.411 遠低於 0.5 門檻（R5 觸發），且在 Late Cycle Tightening 實質利率高達 2.79% 下，擁擠防禦交易面臨流動性重新定價風險。 |
| Technology — HOT | — | FRED 宏觀體制明確將 Technology 列入 avoid 名單（R4 觸發），內部人比率僅 0.432（R5 觸發），在實質利率 2.79% 與通膨加速下，高估值成長股現金流折現承壓。 |
| Energy — HOT | — | 整體環境為 RISK_OFF 且合成曝險僅 0-25%，在 Late Cycle 實質利率高企與信貸壓力下，隨時可能引發終端需求破壞。 |

---

## Top Actionable Themes

1. Healthcare Sector Concentration (Trending, Heat 61.5)
2. Oil & Gas (Energy) (Exhausting, Heat 54.0)
3. Cybersecurity (Accelerating, Heat 52.8)

---

## HANDOFF TO INVESTMENT PROTOCOL

> Phase 4 multi-agent debate 完成。四位分析師獨立提案，Devil's Advocate 成功挑戰過熱共識。受限於三訊號衝突與極低合成曝險(0-25%)，依規則下修所有 HOT 板塊至 COLD/AVOID，維持 DEFENSIVE 紀律。
