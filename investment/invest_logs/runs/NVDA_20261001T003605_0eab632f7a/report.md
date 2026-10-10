# 2026-09-30 NVDA — 投資委員會分析

_執行引擎：**codex** (gpt-6-luna) · job `invest_manual_codex_NVDA_20261001_003028`_

## 決議摘要

<!--NARRATIVE:decision_summary_line:start-->
本次委員會對 NVDA 的判定為 HOLD（action: CANCEL），final_score 0.757 / 3.0、decision_confidence N/A、position_size N/A；Red Team STRONG_COUNTER。
<!--NARRATIVE:decision_summary_line:end-->

<!--FACTS:decision_summary:start-->
| 欄位 | 值 |
|---|---|
| Final Decision | HOLD（action: CANCEL） |
| Final Score | 0.757 / 3.0 |
| Decision Confidence | N/A |
| Position Size | N/A |
| 分析時價格 | $230.24 |
| 加權合理價 (weighted_fair_value) | $220.12（vs 現價 -4.39%，fairly_valued） |
| Scenario Odds | N/A |
| Entry（保守 / 積極） | [221.09, 231.11] / [231.11, 233.21] |
| TP / SL | $233.21 / $218.88 |
| R/R・staged_split | 5.48・N/A |
| Burry Score | N/A / 100 |
| Red Team | STRONG_COUNTER |
<!--FACTS:decision_summary:end-->

---

## Phase 0 宏觀背景

Phase 0 判定 VOLATILE，macro_backdrop_score=-2.0、macro_multiplier=0.75；長端殖利率偏高、信用利差位於第85百分位且市場 breadth 轉弱；凍結的 FRED 10 年實質殖利率讀值為 2.86%。

| 指標 | 值 |
|---|---|
| market_regime | VOLATILE |
| macro_backdrop_score | -2.0 |
| macro_multiplier | 0.75 |
| macro_alignment | CONTRARIAN |
| regime_confidence | 0.7 |
| market_top_zone | Orange |
| ftd_state | NO_SIGNAL |
| breadth_composite | 28.6 |
| vix | 15.91 |
| fred_verdict | Late Cycle Tightening |

**關鍵主題**
- Long yields near multi-decade highs; rate sensitivity elevated
- Credit spreads at 85th percentile; breadth weakening
- Oil supply uncertainty from the continuing US-Iran conflict
- Softer August inflation eased yields and supported equities

**hot sectors**：Technology、Energy

**cold sectors**：Real Estate、Consumer Discretionary

---

## Final Visualization Table

<!--FACTS:lane_scores:start-->
| Lane | Score（−3 … +3） |
|---|---|
| Fundamentals | 2.5 |
| Sentiment | -0.4 |
| News | 1.0 |
| Technical | 1.5 |
| Valuation | 0.0 |
| Burry（獨立否決軌） | N/A / 100 |
| Red Team | STRONG_COUNTER |
<!--FACTS:lane_scores:end-->

---

## 詳細評分

### Fundamentals（BUY, Score 2.5, Conf 0.68）

**Key Factors**
- Revenue +105.9% YoY; FCF margin 22.2%
- Forward EPS growth estimate +127.8%
- Net cash; debt/equity 0.05

**Risk Flags**
- FCF yield 2.3%, below the 5% threshold
- DCF 3.4% below spot; credit spreads at 85th percentile

**Moat**：NARROW — scale_economies

> 66.2% operating margin and 22.2% FCF margin indicate scale; curated peer cohort is unavailable.

**Bull Thesis**：營收年增105.9%，營業利益率66.2%，淨現金支撐再投資。

**Bear Thesis**：28.7倍本益比高於DCF估值3.4%；信用利差升至一年85百分位。

**Near-term Catalysts**

| 日期 | 類型 | 影響 | 說明 |
|---|---|---|---|
| 2026-11-18 | earnings | high | Next earnings estimate; guidance will test continued revenue growth above 100% YoY. |
| 2026-Q4 | macro_event | medium | 10-year yield at 5.24% and real yield near 2.9% may pressure growth multiples. |
| 2026-Q4 | macro_event | medium | High-yield spreads at the 85th percentile; further widening could weigh on risk appetite. |
| 2026-Q4 | macro_event | medium | US-Iran oil-supply uncertainty could sustain inflation and rates volatility. |

---

### Sentiment（HOLD, Score -0.4, Conf 0.72）

**Key Factors**
- Recent insider sales exceed acquisitions
- Low short interest provides modest support
- Fear and weakening breadth temper market tone

**Risk Flags**
- Persistent insider distribution
- Elevated rates and credit stress

---

### News（BUY, Score 1.0, Conf 0.58）

**Key Factors**
- Production Vera Rubin rollout
- Upward PT revisions, low sample
- DeepSeek-Huawei software challenge

**Risk Flags**
- PT revision reflects one analyst
- AI capex and software competition

**Reasoning**：Production deployment and upward revisions support a modest bullish news read, tempered by software competition, a thin revision sample, and risk-off Phase 0 conditions.

pt_revision_momentum：UP（1M 15.07%／3M 1.11%）；decision_point_days 21；immediate_catalyst_5d N/A

**Cross-asset Spillover**

| 資產 | 方向 | 機制 |
|---|---|---|
| sector_XLK | BULLISH | CoreWeave's production Vera Rubin rollout supports AI infrastructure demand expectations across technology suppliers. |

---

### Technical（BUY, Score 1.5, Conf 0.72）

**Key Factors**
- Stage 2 price above all major averages
- Bullish RSI and rising MACD histogram
- Resistance at $233.21 limits near-term upside

**Risk Flags**
- Elevated yields and credit stress pressure technology
- Insider transactions indicate distribution

**Pattern**：uptrend_continuation；market_strength STRONG

> 確認條件：A close above $233.21 with volume at or above the 20-day average confirms continuation; a close below $221.09 weakens the setup.

**Key Levels**：support $221.09／resistance $233.21／pivot $229.98

ATR-14 N/A；hist_vol_20d_daily N/A；momentum_20d N/A

**Smart Money**：distributing

> Q3 acquired/disposed ratio is 0.0882, with 3 acquired versus 34 disposed transactions. Effective volume is 94.3M versus the 112.3M 20-day average, so current price-volume data does not confirm accumulation.

**High-prob Scenario**：A hold above $229.98 and close above $233.21 with volume at or above 112.3M would favor a test of $236.00; a break below $221.09 risks a pullback toward $217.27.

---

### Valuation（HOLD, Score 0.0, Conf 0.6）

**Key Factors**
- Fair value is close to current price
- Only fundamental and external-expectations families qualify
- Peer and forecaster anchors are ineligible

**Risk Flags**
- Forward validation marked STRETCHED
- Owner earnings anchor is a low outlier

Lane 自算 weighted_fair_value $220.12（vs 現價 -4.39%）

**⚠ Outlier anchors（engine 自標，未從加權中剔除）**

- `owner_earnings_mult` = 15.75（有效權重 0.166667） —— outside [73.02, 657.22] (median 219.07 × 1/3..3)

---

### Contrarian（Burry Score N/A / 100, N/A, veto_flag N/A）

**Narrative（僅註記，不調分）**：FCF yield 0.8% │ EV/EBITDA 27.1 │ D/E 0.17 │ 2% below 52wH │ insider=SELL

---

## Multi-Horizon Price Framework

### 長期：合理股價

<!--FACTS:fair_value_anchors:start-->
**合理股價（fair_value_summary — decision_lock 保護，engine 原值）**

| Anchor | 值 | 權重 |
|---|---|---|
| dcf_unlevered | $222.52 | 0.083333 |
| dcf_levered | $232.16 | 0.083333 |
| dcf_self_built | $95.04 | 0.166667 |
| analyst_pt_consensus | $345.21 | 0.5 |
| peer_pe_implied | N/A | N/A |
| comps_implied | N/A | N/A |
| owner_earnings_mult | $15.75 | 0.166667 |
| forecaster_blend | N/A | N/A |
| fwd_earnings_discounted | $215.62 | N/A |

- 加權合理價 (weighted_fair_value): $220.12（vs 現價 -4.39%）
- Verdict band: fairly_valued｜confidence: medium｜current_price: $230.24
- 區間 (fair_value_range): P25 $131.46 / P50 $225.74 / P75 $288.68｜min–max anchor $15.75–$345.21｜fair_zone｜錨一致度 medium
- 隱含預期 (implied_expectations): 現價隱含 5Y FCF CAGR 60.0%（out_of_range: True，WACC 0.0974）
- 前瞻驗證 (forward_validation): **STRETCHED**；DCF gap -58.72%；支持 archetype_shadow, forward_earnings, revenue_path；失敗 無
- Valuation score: 0.0 → 0.0；T5 hard downgrade eligible: False
<!--FACTS:fair_value_anchors:end-->

### 5 日機率帶

- Band（Capped）：[下界 $221.09 / 點估計 $231.11 / 上界 $233.21]
- Drift (drift_sigma)：0.1
- Sigma Daily：0.01684
- ATR-14：5.2971
- Confidence：high
- Catalyst Widened：false
- 關鍵水位反射註記：下界受 support $221.09 撐住（原始 $220.01）；上界受 resistance $233.21 壓制（原始 $242.20）

### 60 日 target

- Momentum Target：$237.03
- PT 60D：$249.14
- Earnings Revision：N/A
- 權重：momentum 0.5333 / pt_60d 0.4667 / earnings_revision N/A
- Mid Target：$242.68
- Reality Check：需突破 $233.21 才成立

### 三框收斂訊號

mhp_signal：wait_for_pullback — 5d 帶下界 $221.09 > 長期FV $220.12 → 短期超漲、長期偏貴，等回檔

### Archetype Shadow（advisory，不進決策）

Archetype：hypergrowth；weighted_fair_value_shadow $241.25（vs 現價 4.78%，verdict_band_shadow：fairly_valued）；flip_vs_live：false。

---

## Red Team Counter Thesis

### Consensus View（市場共識）

<!--NARRATIVE:consensus_view:start-->
Lane 訊號分佈：Fundamentals BUY (2.5)／Sentiment HOLD (-0.4)／News BUY (1.0)／Technical BUY (1.5)／Valuation HOLD (0.0)。 analyst_consensus：{'strong_buy': 2, 'buy': 58, 'hold': 16, 'sell': 3, 'strong_sell': 0, 'consensus': 'Buy'}。 最高分 lane 為 Fundamentals（2.5），最低分為 Sentiment（-0.4）。
<!--NARRATIVE:consensus_view:end-->

### Differentiated View（本委員會差異化判斷）

<!--NARRATIVE:differentiated_view:start-->
委員會結論 HOLD，final_score 0.757 / 3.0。 polarization=ALIGNED（來源 calculation_steps）；macro_alignment=CONTRARIAN；red_team=STRONG_COUNTER。
<!--NARRATIVE:differentiated_view:end-->

### Counter Thesis

At $230.24, the underwriting margin is thin: the frozen valuation pack puts fair value at $220.12 (-4.39%) while implied expectations require 60% five-year FCF CAGR, with actual and lane FCF-growth estimates unavailable to corroborate that hurdle. The frozen FRED input shows a 2.86% 10-year real yield, adding a material discount-rate headwind to a growth-dependent valuation.

red_team_verdict STRONG_COUNTER｜counter_evidence_strength 4/5｜thesis_break_probability 0.36

### Kill Conditions

<!--FACTS:kill_conditions:start-->
1. IF annualized FCF growth is below 30% across the next two reported quarters (within 180 days) THEN the 60% five-year FCF CAGR embedded in the price is not credible and the cash-flow thesis breaks.
2. IF annualized revenue growth falls below 35% across the next two reported quarters (within 180 days) THEN the frozen market-implied revenue path is missed and the growth justification breaks.
3. IF the 10-year real yield remains at or above its frozen FRED reading of 2.86% for 30 trading days within the next 90 days THEN persistent high discount rates undermine the staged-entry risk/reward thesis.
<!--FACTS:kill_conditions:end-->

---

## 進場計畫

### Base Case

| 欄位 | 值 |
|---|---|
| Entry（積極） | $231.11 – $233.21 |
| Entry（保守） | $221.09 – $231.11 |
| Take Profit | $233.21 |
| Stop Loss | $218.88 |
| Risk / Reward | 5.48 |
| Staged Split | N/A |
| Position Size | N/A |
| Position Size Method | VOL_ADJUSTED |
| Time Horizon | mid |

### Bull Case

<!--NARRATIVE:bull_case:start-->
上檔參考：60 日 mid_target $242.68（成立條件：需突破 $233.21 才成立）；關鍵阻力 $233.21。
<!--NARRATIVE:bull_case:end-->

### Bear Case

<!--NARRATIVE:bear_case:start-->
下檔紀律：跌破 5 日帶下界 $221.09 或 support $221.09 即退出；stop_loss $218.88，另有 3 條 kill conditions 見上節。
<!--NARRATIVE:bear_case:end-->

---

## 關鍵風險

<!--FACTS:key_risks:start-->
- 加權公允價值 $220.12 低於現價 $230.24 約 4.39%，估值安全邊際有限。
- 現價隱含五年 FCF CAGR 約 60%，但可用實際與 lane FCF 成長估計不足以驗證該門檻。
- 10 年實質殖利率凍結讀值 2.86%；信用利差位於第85百分位，成長股折現與風險偏好承壓。
- 內部人交易呈分配：Q3 acquired/disposed ratio 為 0.0882，3 筆取得對 34 筆處分。
- 可比同業與 forecaster anchor 不合格，估值聚合僅由 fundamental 與 external-expectations 家族支撐。
- AI capex 需求與 DeepSeek-Huawei 軟體競爭可能改變供應商需求預期。
- $233.21 阻力限制短期上檔；MHP 指向 wait_for_pullback。
<!--FACTS:key_risks:end-->

---

## Watch / 再評觸發條件

<!--FACTS:watch_conditions:start-->
- **support_break**: 收盤跌破 $221.09 將削弱 uptrend_continuation 型態，重新評估趨勢支撐。
- **resistance_confirmation**: 收盤站上 $233.21 且成交量達或高於 20 日均量 112.3M，才確認延續並解除目前阻力限制。
- **fcf_growth_kill**: 未來 180 天內連續兩季的年化 FCF 成長低於 30%，依 Red Team 條件推翻現價隱含的成長假設。
- **real_yield_persistence**: 未來 90 天內 10 年實質殖利率連續 30 個交易日維持在 2.86% 或以上，依 Red Team 條件重新評估折現率壓力。
<!--FACTS:watch_conditions:end-->

---

*分析基準日：2026-09-30｜分析價格：$230.24｜price engine：compute_price_framework.py v2.4 (V4.131.13)｜renderer：render_investment_report.py v1.0.0 (V4.87.0)｜polish：none*

## 本場資料與執行紀錄

場次 `NVDA_20261001T003605_0eab632f7a` · 凍結時間 2026-09-30T16:36:11.248079+00:00
統一計價 $230.24 · 執行品質 complete
快照摘要 `sha256:1f1ba017c5f4b3c7abbddb37a4f67de365624c60c2e57e9bc893c07ffa67dea0`
Red Team synthetic: false

| 價格來源 | 原始價格 | 與凍結價差 | 抓取時間 | 行情時間 |
|---|---:|---:|---|---|
| FMP frozen quote | 230.24 | 0.0 | 2026-09-30T16:36:09.458978+00:00 | 1790786168 |
| Finnhub scoring | 230.28 | 0.03999999999999204 | 2026-09-30T16:32:33.890003Z | None |
| FMP audit | 230.298 | 0.057999999999992724 | 2026-09-30T16:32:33.890003Z | None |
