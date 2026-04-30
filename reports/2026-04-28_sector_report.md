# Sector Intelligence Report — 2026-04-28

> **Protocol**: V1.3 · **Fan-out**: PARALLEL_SUBAGENT · **Regime Confidence**: 0.58
> **Stance**: DEFENSIVE · **Cycle**: Mid · **Generated**: 2026-04-28 19:55
> **Degraded Agents**: none

---

## FINAL VERDICT TABLE

| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |
|---|---|---|---|---|---|---|---|
| Industrials | **HOT** | 81.82 | 0.97 | Top-1 uptrend 0.439 + INFLOW slope+0.030 · Robotics 65.8 + Infra 61.1 + Defense 57.6 三主題 | ROBUST | XLI | overbought, late_cycle |
| Energy | WARM | 60.58 | 1.00 | FRED Overheating real-asset favor · Brent $111 + COP 4/30 / CVX/XOM 5/01 | ROBUST | XLE | rotation_outflow_warning |
| Materials | WARM | 58.83 | 1.00 | FRED Overheating favor + 鋼/銅 cyclical · Top-3 uptrend 0.386 INFLOW | N/A | XLB | overbought, single_lane_warning |
| Technology | WARM | 51.17 | 0.90 | Space 68.8 Trending + 18 日半導體連漲 · Mag-7 4/29 binary 內 ×0.70 折讓 | ROBUST | XLK | binary_risk_within_48h, macro_theme_divergence, overbought |
| Real_Estate | COLD | 44.13 | 0.93 | FRED Overheating avoid（duration-sensitive） · FOMC 4/29 binary 利率風險 | N/A | XLRE | macro_theme_divergence, binary_risk_within_48h |
| Financials | COLD | 41.67 | 1.00 | FRED Overheating favor (NIM/spread) · 主題熱度全市場最低 19.8 | N/A | XLF | — |
| Healthcare | COLD | 34.3 | 1.00 | 100% 製藥關稅 + LLY/MRK/BMY 4/30 · Biotech 25.5 + GLP-1 20.7 雙 bearish | N/A | XLV | pharma_tariff_overhang |
| Consumer_Discretionary | COLD | 32.08 | 0.90 | AMZN 4/29 AMC binary catalyst · FRED Overheating avoid override | N/A | XLY | binary_risk_within_48h, macro_theme_divergence |
| Communication | COLD | 28.03 | 0.97 | GOOGL/META 4/29 AMC 雙財報 binary · Comm Concentration bearish Accelerating | N/A | XLC | binary_risk_within_48h |
| Utilities | COLD | 25.4 | 1.00 | Trend Down + OUTFLOW · Nuclear 29.7 bearish + Util Defensive 失血 | N/A | XLU | defensive_bleed |
| Consumer_Staples | **AVOID** | 21.9 | 1.00 | uptrend 0.162 全市場最弱 + Trend Down · Cons Defensive 24.3 bearish Emerging | N/A | XLP | defensive_bleed |

---

## Macro Context

```text
Market Regime: RISK_ON | Breadth Ceiling: 60-75% | Synthesized: 60-75% | Cycle: Mid
FTD: FTD_CONFIRMED (quality 100) | Market Top: 25.9 Yellow (Early Warning) | Breadth: 42.4 Neutral
Sentiment: F&G [70.7 — Greed] | VIX: 18.94 | Put/Call: n/a | SPY RSI: 87.6
Signal Conflict: No | Extreme Sentiment: No
```

**TOP THEMES TODAY**: Space Economy (heat 68.8 Trending, Technology) · Robotics & Automation (heat 65.8 Mature, Industrials/Tech) · Infrastructure & Construction (heat 61.1 Mature, Industrials/Materials)

---

## Step 6 — FRED Regime Overlay

- **Regime**: Overheating (confidence 0.67)
- **Favor**: Energy, Materials, Financials
- **Avoid**: Technology, Real Estate, Consumer Discretionary
- **Velocity highlights**: BAMLH0A0HYM2:accelerating, DFF:decelerating, NFCI:accelerating
- **Rationale**: Overheating regime, conf 0.67 → favor: Energy/Materials/Financials ×0.998；avoid: Technology/Consumer_Discretionary ×0.903、Real_Estate ×0.933。

---

## Today's Verdict — DEFENSIVE (confidence 0.58)

> **防禦立場：FOMC + Mag-7 + Brent $111 三地雷 48h 內，僅 Industrials 維持 HOT**
> 
> FTD 確認 day 13 + Power Trend ON 但 SPY RSI 87.6、breadth pctile 26、6 COLD sector 揭示 narrow leadership；4/29 FOMC + Mag-7 五家財報 + Hormuz 油價 binary 落地前不擴張部位。

### Key Takeaways
1. 防禦立場：48h 內 FOMC（4/29）+ MSFT/GOOGL/META/AMZN/QCOM（4/29 AMC）+ Brent $111 Hormuz 三重 binary，新進倉位等過數據再評估
2. Industrials 唯一 HOT — Robotics/Infra Mature + Defense Accelerating 三主題 + ROBUST tail-risk，但 HIGH overbought 須收緊停損 5-8%
3. Technology 從共識 HOT 降為 WARM — STEP G.5 FRED Overheating avoid + Mag-7 binary ×0.70 雙重壓力，僅守不加
4. Energy/Materials 維持 WARM 受 FRED Overheating favor + Brent $111 支撐；Energy rotation OUTFLOW 與油價矛盾須 monitor XLE 收上 10MA
5. Healthcare/Real_Estate/Financials/Utilities/Comm/Disc 全 COLD、Consumer_Staples AVOID — 避免新建倉，定期審視既有部位

### Sector Actions
- **Overweight**: Industrials (high) — 唯一 HOT；三主題支撐 + ROBUST tail-risk
- **Overweight**: Energy (med) — FRED favor + 油價 $111 對沖 OUTFLOW
- **Overweight**: Materials (med) — FRED favor + Top-3 uptrend
- **Wait**: Technology (high) — FRED 規避 vs Mag-7 4/29 binary
- **Underweight**: Real_Estate (med) — FRED 規避 + FOMC 利率風險
- **Avoid**: Healthcare (high) — 100% 製藥關稅 + 雙 bearish 主題
- **Avoid**: Consumer_Staples (high) — 全市場最弱 uptrend；defensive 失血

### Watch Next
- 4/29 14:00 ET FOMC 利率決議與 Powell 措辭 — 偏鷹則 Tech/Real_Estate/Utilities 加速賣壓
- 4/29 AMC MSFT/GOOGL/META/AMZN/QCOM 五家 Mag-7 財報 — AI capex 2026 guidance + Azure/GCP/AWS 增速為核心訊號
- 4/30 AAPL 財報（已超 48h 但指數權重最大）+ LLY/MRK/BMY BMO 財報（製藥關稅疊加）
- 10Y 實質利率 DFII10 1.89% → 突破 2.00 觸發 STEP G.5 強化、Real_Estate/Tech duration-sensitive 賣壓
- Brent / WTI + Hormuz 進展 — Brent 跌破 $103 削弱 Energy WARM；XLE 收上 10MA 才確認 rotation OUTFLOW 解除

---

## Devil's Advocate Challenges (Accepted 3/4)

| Challenge | Status | Counter-Evidence |
|---|---|---|
| Technology — HOT | **Accepted** | FRED Overheating（conf 0.67）明確將 Technology 列入 sector_rotation_avoid，real_rate 1.91% 距 2.0% threshold 僅 9 bps — FOMC 4/29 任何 hawkish dot 可在 intraday 收斂。Theme_Intelligence 標 AI&Semis 46.2 Exhausting（XLK 主要權重），SPY RSI 87.6 已超買 7.6pp，Sector_Rotation 引用的 18 日半導體連漲本身就是 mean-reversion... |
| Industrials — HOT | Rejected | 三 lane 共識在 Mid-cycle breadth-PEAK-36-days-ago juncture 是教科書級 crowded-consensus 訊號 — Sector_Rotation 自身標 HIGH overbought，Robotics 65.8 / Infra 61.1 兩主題皆 Mature（非 Accelerating），即 second-derivative 已減速。Brent $111 + WTI YoY +43% 直接成為 Industrials 投入成本稅（運輸、機械、建材），CPI MoM +0.87% 加速壓縮... |
| Energy — HOT | **Accepted** | Energy HOT 建立在 Brent $111.50 已 priced 的 Hormuz 中斷 binary — 這是買 headline 而非 trend；單一外交解套或 SPR 協調 headline 即可在 hours 內崩解 $8-12 地緣溢價。CVX/XOM 5/01 + COP 4/30 將 report 不含此 spike 的 Q1 價格，形成「舊價 beat、需求 guide cautious」設定。FRED Overheating favor Energy 是 coincident 指標（WTI YoY +43% 已在 ta... |
| Materials — HOT | **Accepted** | Materials 僅在 FRED lane（Overheating 模板）出現，未獲 Sector_Rotation/Theme/News 確認 — Mid-cycle、breadth 已 peak 環境下單 lane HOT 為最弱共識，且 FRED 顯式為 lagging/coincident 框架。CPI MoM +0.87% 加速 + real_rate 1.91% 意味 Fed 4/29 偏向 hawkish；hawkish surprise 推高 DXY，是工業金屬與礦業最可靠 kill-switch（不論 WTI 水準）。 |

---

## Sector Divergence Watch

| Sector | Signal | Action | Description |
|---|---|---|---|
| Energy | news_positive_price_negative | monitor | Brent $111 + FRED Overheating favor + Oil&Gas 59.5 Trending vs Phase 1 rotation OUTFLOW 與 slope -0.009 — 價格訊號落後敘事；XLE 收上 10MA 為解除門檻。 |
| Technology | news_positive_price_negative | monitor | 18 日半導體連漲 + INTC/AMD/QCOM 強勢 + Section 232 carve-out 利好 vs FRED Overheating avoid + RSI 87.6 + Mag-7 4/29-30 binary；HOT 共識被 STEP G.5 cap 為 WARM。 |

---

## Top Actionable Themes

1. Space Economy (heat 68.8 Trending, Technology)
2. Robotics & Automation (heat 65.8 Mature, Industrials/Tech)
3. Infrastructure & Construction (heat 61.1 Mature, Industrials/Materials)
4. Oil & Gas (heat 59.5 Trending, Energy)
5. Defense & Aerospace (heat 57.6 Accelerating, Industrials/Tech)
6. Basic Materials Concentration (heat 54.3 Accelerating, Materials)

---

## HANDOFF TO INVESTMENT PROTOCOL

> DEFENSIVE 立場：48h 內 FOMC + Mag-7 五家財報 + Brent $111 Hormuz 三重 binary；唯一 HOT = Industrials（三主題 + ROBUST tail-risk）；Technology 受 STEP G.5 FRED 衝突 + Mag-7 ×0.70 由 HOT 降為 WARM；Energy/Materials WARM 受 FRED Overheating favor 支撐；Consumer_Staples AVOID。新進倉位等過 4/29 數據再評估，停損收緊 5-8%。
