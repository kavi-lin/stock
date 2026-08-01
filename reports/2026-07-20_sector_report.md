# Sector Intelligence Report — 2026-07-20

> **Protocol**: V1.4 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: —
> **Stance**: DEFENSIVE · **Cycle**: Late · **Generated**: 2026-07-20 09:06
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Energy | WARM | 69 | 1.04 | uptrend_ratio 0.424 為全 11 板塊最高，參與度是實質的而非指數權重帶動 · 多週期 RS 同向轉強：20d +8.49% / 5d +3.15%，短中期未背離 | ROBUST | XLE | fred_real_rate_high |
| Financials | WARM | 62 | 1.04 | 30d beat_rate 100%（n=8，樣本足）且 surprise_score_avg +0.18，是唯一達到 rubric 加分門檻的板塊 · 多週期 RS 全正：3M +2.35% / 20d +5.20% / 5d +0.85% | ROBUST | XLF | fred_real_rate_high, elevated_kurtosis |
| Real_Estate | WARM | 61 | 0.96 | uptrend_ratio 0.406 次高，PE_z -2.86 為全板塊最深度折價 · Real Estate Sector Concentration 主題 heat 58.33（Trending，Medium 信度）為當日最強多頭主題 | ROBUST | XLRE | fred_real_rate_high, smart_money_divergence, rate_sensitive |
| Healthcare | WARM | 54 | 0.96 | uptrend_ratio 0.382 第三高，20d RS +7.43% 為次強 · PE_z -1.53 相對自身一年區間便宜，30d beat_rate 100%（n=4） | N/A | XLV | fred_real_rate_high, theme_rotation_conflict |
| Industrials | COLD | 43 | 1.07 | FRED lane 因 real_rate_high 覆蓋而列入 favor（×1.075），但價格面未配合 · uptrend_ratio 僅 0.186，三窗口 RS 全負（3M -1.9% / 20d -0.98% / 5d -0.35%） | N/A | XLI | fred_real_rate_high, weak_breadth |
| Consumer_Staples | COLD | 40 | 0.89 | PE_z -1.47 且 uptrend 0.169 觸發超賣價值加分 +5 · FRED Soft Landing regime 明確列為 avoid（×0.894） | N/A | XLP | fred_sector_avoid |
| Communication | COLD | 39 | 1.04 | News lane 最高信度多頭：GOOGL 7/21 財報 + Meta $12B 資料中心融資 + smart money 正向（insider 2.18 / senate +1） · PE_z -1.43 且 uptrend 0.223 觸發超賣加分 +5 | N/A | XLC | binary_risk_within_48h, fred_real_rate_high |
| Consumer_Discretionary | COLD | 39 | 1.07 | PE 48.59 為全板塊最高，但 PE_z -1.19 + uptrend 0.222 觸發超賣加分 +5 · 3M RS -9.42% 為倒數第二，Retail & Consumer 主題看空（28.55） | N/A | XLY | fred_real_rate_high, weak_breadth |
| Materials | **AVOID** | 36 | 1.04 | uptrend_ratio 0.110 為全 11 板塊最低，3M RS -8.14% · 唯一支撐是 Gold & Precious Metals 主題（32.78，低成熟度 44.75），但新聞覆蓋極薄（僅 4 則） | N/A | XLB | low_exposure_forced_avoid, weak_breadth, fred_real_rate_high |
| Technology | **AVOID** | 31 | 1.07 | 4 個 lane 中有 3 個列為 COLD — 當日最強共識 · 動能耗盡：3M RS +9.56% 但 20d -7.49% / 5d -1.98%，短中期已反轉 | N/A | XLK | low_exposure_forced_avoid, momentum_exhaustion, smart_money_divergence, narrow_leadership |
| Utilities | **AVOID** | 28 | 0.89 | 全 11 板塊最低分；FRED avoid 名單（×0.894）+ Theme lane COLD 雙重確認 · uptrend_ratio 0.138 倒數第二，3M RS -7.27% | N/A | XLU | low_exposure_forced_avoid, fred_sector_avoid, weak_breadth |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 75-90% | Synthesized: 0-25% | Cycle: Late
FTD: RALLY_ATTEMPT (quality 0) | Market Top: 46.3 Orange (Elevated Risk) | Breadth: 67.0 Healthy
Sentiment: F&G [55.6 — Neutral] | VIX: 17.89 | Put/Call: n/a | SPY RSI: 50.4
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Real Estate Sector Concentration（heat 58.33，Trending）— 唯一 Medium 信度多頭主題，但與 REITs 空頭主題自相矛盾 · Oil & Gas Energy（heat 45.47，Mature）— 支撐能源板塊，惟生命週期已晚 · Gold & Precious Metals（heat 32.78，低成熟度 44.75）— 材料板塊唯一亮點，新聞覆蓋薄

---

## Step 6 — FRED Regime Overlay

- **Regime**: Soft Landing (confidence 0.73)
- **Favor**: Technology, Industrials, Consumer Discretionary
- **Avoid**: Consumer Staples, Utilities
- **Velocity highlights**: DGS10:accelerating, DFF:decelerating, CPIAUCSL:decelerating
- **Rationale**: Soft Landing regime, conf 0.73 → favor: Consumer_Discretionary×1.075, Industrials×1.075, Technology×1.075; avoid: Consumer_Staples×0.894, Utilities×0.894

---

## Sector Valuation Snapshot (V1.4)

| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |
|---|---|---|---|---|---|
| Energy | 19.04 | -0.52 | +0.9% | 0.323 |  |
| Financials | 18.72 | -1.43 | +2.4% | 0.364 |  |
| Real_Estate | 28.49 | -2.86 | -3.2% | 0.27 |  |
| Healthcare | 23.26 | -1.53 | +2.7% | 0.285 |  |
| Industrials | 29.86 | -0.94 | -1.9% | 0.316 |  |
| Consumer_Staples | 29.25 | -1.47 | -2.0% | 0.302 | 🟢 OVERSOLD VALUE |
| Communication | 22.68 | -1.43 | -11.4% | 0.235 | 🟢 OVERSOLD VALUE |
| Consumer_Discretionary | 48.59 | -1.19 | -9.4% | 0.333 | 🟢 OVERSOLD VALUE |
| Materials | 24.9 | -0.50 | -8.1% | 0.31 |  |
| Technology | 42.77 | -0.75 | +9.6% | 0.254 |  |
| Utilities | 24.93 | -0.84 | -7.3% | 0.333 |  |

> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。

---

## 競品地圖 (Competitive Landscape, V2.17.0)

_每 sector top-5 by market cap rank_。Profile 24h cache（reuse `skills/_shared/company_context.py`）。 Differentiator 欄位待 LLM 補強（Phase D 後續）。

### Energy

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **XOM** | Exxon Mobil Corporation | Oil & Gas Integrated | $610.9B | $147.39 | Darren W. Woods | _TBD_ |
| **CVX** | Chevron Corporation | Oil & Gas Integrated | $373.1B | $187.36 | Michael K. Wirth | _TBD_ |
| **COP** | ConocoPhillips | Oil & Gas Exploration… | $139.8B | $114.71 | Ryan Lance | _TBD_ |
| **EOG** | EOG Resources, Inc. | Oil & Gas Exploration… | $74.5B | $139.89 | Ezra Y. Yacob | _TBD_ |
| **SLB** | Slb N.V. | Oil & Gas Equipment &… | $70.3B | $46.99 | Olivier Le Peuch | _TBD_ |

### Financials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **BRK-B** | Berkshire Hathaway Inc. | Insurance - Diversifi… | $1.06T | $490.91 | Gregory Edward Abel | _TBD_ |
| **JPM** | JPMorgan Chase & Co. | Banks - Diversified | $914.0B | $341.10 | James Dimon | _TBD_ |
| **BAC** | Bank of America Corporation | Banks - Diversified | $434.8B | $61.27 | Brian Thomas Moynihan | _TBD_ |
| **WFC** | Wells Fargo & Company | Banks - Diversified | $267.8B | $87.53 | Charles W. Scharf | _TBD_ |
| **GS** | The Goldman Sachs Group, In… | Financial - Capital M… | $314.2B | $1065.22 | David Solomon | _TBD_ |

### Real_Estate

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PLD** | Prologis, Inc. | REIT - Industrial | $139.6B | $149.71 | Daniel Stephen Letter | _TBD_ |
| **AMT** | American Tower Corporation | REIT - Specialty | $79.2B | $170.06 | Steven O. Vondran | _TBD_ |
| **EQIX** | Equinix, Inc. | REIT - Specialty | $100.6B | $1020.00 | Adaire Rita Fox-Martin | _TBD_ |
| **WELL** | Welltower Inc. | REIT - Healthcare Fac… | $171.7B | $243.25 | Shankh S. Mitra | _TBD_ |
| **CCI** | Crown Castle Inc. | REIT - Specialty | $34.6B | $79.17 | Christian H. Hillabra… | _TBD_ |

### Healthcare

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly and Company | Drug Manufacturers - … | $1.11T | $1179.09 | David A. Ricks | _TBD_ |
| **UNH** | UnitedHealth Group Incorpor… | Medical - Healthcare … | $387.0B | $426.09 | Stephen J. Hemsley | _TBD_ |
| **JNJ** | Johnson & Johnson | Drug Manufacturers - … | $609.1B | $253.04 | Joaquin Duato | _TBD_ |
| **ABBV** | AbbVie Inc. | Drug Manufacturers - … | $449.6B | $254.49 | Robert A. Michael | _TBD_ |
| **MRK** | Merck & Co., Inc. | Drug Manufacturers - … | $314.9B | $127.50 | Robert Davis | _TBD_ |

### Industrials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GE** | GE Aerospace | Aerospace & Defense | $363.9B | $348.83 | H. Lawrence Culp Jr. | _TBD_ |
| **CAT** | Caterpillar Inc. | Agricultural - Machin… | $405.5B | $880.28 | Joseph E. Creed | _TBD_ |
| **RTX** | RTX Corporation | Aerospace & Defense | $260.6B | $193.51 | Christopher T. Calio | _TBD_ |
| **HON** | Honeywell International Inc. | Conglomerates | $71.3B | $225.02 | Vimal Kapur | _TBD_ |
| **UNP** | Union Pacific Corporation | Railroads | $179.2B | $301.75 | Vincenzo James Vena | _TBD_ |

### Consumer_Staples

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **PG** | The Procter & Gamble Company | Household & Personal … | $349.2B | $149.96 | Shailesh G. Jejurikar | _TBD_ |
| **COST** | Costco Wholesale Corporation | Discount Stores | $417.3B | $940.87 | Ron Vachris | _TBD_ |
| **KO** | The Coca-Cola Company | Beverages - Non-Alcoh… | $350.9B | $81.56 | Henrique Braun | _TBD_ |
| **PEP** | PepsiCo, Inc. | Beverages - Non-Alcoh… | $187.3B | $137.12 | Ramon Luis Laguarta | _TBD_ |
| **WMT** | Walmart Inc. | Discount Stores | $909.1B | $114.24 | John R. Furner | _TBD_ |

### Communication

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **GOOGL** | Alphabet Inc. | Internet Content & In… | $4.19T | $346.77 | Sundar Pichai | _TBD_ |
| **META** | Meta Platforms, Inc. | Internet Content & In… | $1.64T | $646.01 | Mark Elliot Zuckerberg | _TBD_ |
| **NFLX** | Netflix, Inc. | Entertainment | $290.3B | $68.95 | Theodore A. Sarandos | _TBD_ |
| **DIS** | The Walt Disney Company | Entertainment | $169.6B | $97.67 | Josh D'Amaro | _TBD_ |
| **TMUS** | T-Mobile US, Inc. | Telecommunications Se… | $208.2B | $192.43 | Srinivasan Gopalan | _TBD_ |

### Consumer_Discretionary

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AMZN** | Amazon.com, Inc. | Specialty Retail | $2.66T | $247.23 | Andrew R. Jassy | _TBD_ |
| **TSLA** | Tesla, Inc. | Auto - Manufacturers | $1.43T | $380.84 | Elon R. Musk | _TBD_ |
| **HD** | The Home Depot, Inc. | Home Improvement | $337.9B | $338.87 | Edward Decker | _TBD_ |
| **MCD** | McDonald's Corporation | Restaurants | $190.2B | $267.71 | Christopher J. Kempcz… | _TBD_ |
| **NKE** | NIKE, Inc. | Apparel - Footwear & … | $64.8B | $43.76 | Elliott J. Hill | _TBD_ |

### Materials

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **LIN** | Linde plc | Chemicals - Specialty | $237.4B | $513.22 | Sanjiv Lamba | _TBD_ |
| **SHW** | The Sherwin-Williams Company | Chemicals - Specialty | $81.7B | $331.32 | Heidi G. Petz | _TBD_ |
| **FCX** | Freeport-McMoRan Inc. | Copper | $84.0B | $58.40 | Kathleen Lynne Quirk | _TBD_ |
| **APD** | Air Products and Chemicals,… | Chemicals - Specialty | $65.8B | $295.62 | Eduardo F. Menezes | _TBD_ |
| **ECL** | Ecolab Inc. | Chemicals - Specialty | $76.8B | $272.83 | Christophe Beck | _TBD_ |

### Technology

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **AAPL** | Apple Inc. | Consumer Electronics | $4.90T | $333.74 | Timothy D. Cook | _TBD_ |
| **MSFT** | Microsoft Corporation | Software - Infrastruc… | $2.93T | $393.82 | Satya Nadella | _TBD_ |
| **NVDA** | NVIDIA Corporation | Semiconductors | $4.91T | $202.81 | Jen-Hsun Huang | _TBD_ |
| **AVGO** | Broadcom Inc. | Semiconductors | $1.76T | $370.82 | Hock E. Tan | _TBD_ |
| **ORCL** | Oracle Corporation | Software - Infrastruc… | $364.3B | $126.48 | Michael D. Sicilia | _TBD_ |

### Utilities

| Ticker | Company | Industry | Market Cap | Price | CEO | Differentiator |
|---|---|---|---|---|---|---|
| **NEE** | NextEra Energy, Inc. | Regulated Electric | $185.2B | $88.80 | John W. Ketchum | _TBD_ |
| **SO** | The Southern Company | Regulated Electric | $107.4B | $95.30 | Christopher C. Womack | _TBD_ |
| **DUK** | Duke Energy Corporation | Regulated Electric | $97.5B | $125.01 | Harry K. Sideris | _TBD_ |
| **AEP** | American Electric Power Com… | Regulated Electric | $71.9B | $132.14 | William J. Fehrman | _TBD_ |
| **SRE** | Sempra | Diversified Utilities | $60.3B | $92.24 | Jeffrey Walker Martin | _TBD_ |

---

## Today's Verdict — DEFENSIVE (confidence 0.72)

> **防禦：漲勢未獲確認，現金優先**
> 
> 今天不新增部位，手上留現金。市場已反彈 15 天卻遲遲沒等到確認訊號，同時機構派發訊號滿檔；要等 FTD 出現才值得把曝險拉回來。

### Key Takeaways
1. 把新倉暫停：反彈第 15 天仍無 FTD 確認，曝險上限壓在 0-25%
2. 別被廣度分數騙了：breadth 67 分看似健康，但派發天數已達最大警戒值 100
3. 科技股全面回避：4 個分析面向有 3 個看空，內部人賣超（0.48）且 20 日相對強度 -7.5%
4. 能源與金融是相對最強，但僅止於觀察名單，回檔到支撐才分批
5. GOOGL 7/21 財報前不碰通訊板塊，單一財報足以決定整個板塊方向

### Sector Actions
- **Wait**: Energy (med) — 參與度最高但 3M 相對強度僅持平
- **Wait**: Financials (med) — 財報週未過，左尾風險偏高
- **Wait**: Real_Estate (low) — 估值最便宜但利率敏感度高
- **Neutral**: Healthcare (low) — 輪動看多但主題面全空，訊號矛盾
- **Avoid**: Technology (high) — 動能反轉加內部人賣超，窄幅領漲
- **Avoid**: Utilities (med) — regime 逆風且參與度倒數

### Watch Next
- GOOGL 7/21 財報（二元事件，48 小時內）— 結果出爐前通訊板塊維持零曝險
- FTD 是否確認：反彈日計數已 15 天，確認後曝險可從 0-25% 上調
- 派發天數是否從 100 的最大警戒值回落 — 這是解除防禦的首要前提
- 10Y 殖利率（DGS10 加速中）與 real_rate 是否突破 2.5% — 影響不動產與金融
- 7/24 S&P Global PMI 三讀與 7/27 耐久財訂單（High impact，前值 -4.5%）

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Technology | momentum_exhaustion | avoid | 3M RS +9.56% 但 20d -7.49% / 5d -1.98% — 動能耗盡（R7 形態，惟已列 COLD 故未觸發 DA 規則） |
| Healthcare | lane_conflict | neutral | Rotation lane HOT（uptrend 0.382、20d RS +7.43%）vs Theme lane COLD（兩個非 Mature 空頭主題、零多頭對衝）— 當日最大 lane 間矛盾 |
| Real_Estate | theme_internal_conflict | wait | Theme lane HOT vs News lane COLD；主題內部亦矛盾（Concentration 58.33 Medium 信度 vs REITs 23.31 Low 信度） |
| Materials | theme_vs_breadth | avoid | Theme lane HOT（Gold & Precious Metals 32.78）vs Rotation lane COLD（uptrend 0.110 全市場最低、3M RS -8.14%） |
| ALL | breadth_vs_distribution | wait | breadth 67 Healthy（75-90%）vs distribution_days 100 最大警戒 + FTD 0-25% — 70pp 曝險落差的根源，本次防禦立場主因 |

---

## Top Actionable Themes

1. Real Estate Sector Concentration（heat 58.33，Trending）— 唯一 Medium 信度多頭主題，但與 REITs 空頭主題自相矛盾
2. Oil & Gas Energy（heat 45.47，Mature）— 支撐能源板塊，惟生命週期已晚
3. Gold & Precious Metals（heat 32.78，低成熟度 44.75）— 材料板塊唯一亮點，新聞覆蓋薄
4. AI & Semiconductors（heat 37.37，Trending）— 多頭主題但被 Cybersecurity/Cloud 兩個 Mature 空頭主題壓過
5. 空頭主題數 11 vs 多頭 6 — 主題面整體偏空是本次防禦立場的佐證之一

---

## HANDOFF TO INVESTMENT PROTOCOL

> Cache STALE（最新 intel 為 2026-07-16，距今 4 天）→ 完整執行 Phase 0-5。Phase 0 四層 cache 全 FRESH。Prefetch 首輪 hard_fail=true：valuation 與 smart_money 遭 FMP 429 rate limit，改序列重跑後兩者皆 rc=0，取得 2026-07-20 新鮮 cache。Phase 4a 四個 lane 全部回傳 subagent_isolated=true → PARALLEL_SUBAGENT。DA 預觸發：R4 fired（real_rate 2.33 > 2.0，全 HOT 提案）、R5 fired（Real_Estate senate -1，強度弱）；R6 未觸發（pt_sample_size=0 全板塊，analyst PT 本次不可用）、R7 未觸發於任何 HOT 提案（唯一符合的 Technology 已是 COLD）。Step 6 Overlay 由 step6_overlay.py 計算。Phase 4c STEP B（synthesized_exposure < 40%）強制 3 個 AVOID 名額 → Materials/Technology/Utilities。STEP E 僅對 GOOGL 7/21 判定 is_binary（板塊市值集中度高），Communication ×0.70 由 55.9 降至 39；此乘數在 Step 6 之後套用，故 calculator shadow check 會對 Communication 報 hard diff，屬預期行為非錯誤。零 HOT 板塊（最高 Energy 69.4 < 75），STEP G/G.5 均無實際作用。Step 5 WebSearch 跳過（general_news cache available，Case A 且已涵蓋當日 narrative）。
