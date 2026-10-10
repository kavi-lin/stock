> 工程驗收重播：使用 Luna/max 原場次的保存輸入，經修正後程式重新組裝。未提交 production history，不能算成功試行。

# 2026-10-01 NVDA — 投資委員會分析

_執行引擎：manual（直接跑 renderer，未經 protocol 派工）_

## 決議摘要

<!--NARRATIVE:decision_summary_line:start-->
本次委員會對 NVDA 的判定為 HOLD（action: CANCEL），final_score 0.7151 / 3.0、decision_confidence N/A、position_size 0.00%；Red Team STRONG_COUNTER。
<!--NARRATIVE:decision_summary_line:end-->

<!--FACTS:decision_summary:start-->
| 欄位 | 值 |
|---|---|
| Final Decision | HOLD（action: CANCEL） |
| Final Score | 0.7151 / 3.0 |
| Decision Confidence | N/A |
| Position Size | 0.00% |
| 分析時價格 | $228.38 |
| 加權合理價 (weighted_fair_value) | $220.12（vs 現價 -3.61%，fairly_valued） |
| Scenario Odds | N/A |
| Entry（保守 / 積極） | [221.09, 227.52] / [227.52, 229.98] |
| TP / SL | $229.98 / $218.88 |
| R/R・staged_split | 4.02・N/A |
| Burry Score | 27.7 / 100 |
| Red Team | STRONG_COUNTER |
<!--FACTS:decision_summary:end-->

---

## Phase 0 宏觀背景

Phase 0 為波動市況；高長端與實質利率、信用壓力及偏弱市場參與使科技股估值承壓，較溫和的通膨與韌性活動構成抵銷。FTD 為 NO_SIGNAL，宏觀環境對估值擴張的支持有限。

| 指標 | 值 |
|---|---|
| market_regime | VOLATILE |
| macro_backdrop_score | -2.0 |
| macro_multiplier | 0.75 |
| macro_alignment | CONTRARIAN |
| regime_confidence | 0.62 |
| market_top_zone | Yellow |
| ftd_state | NO_SIGNAL |
| breadth_composite | 28.6 |
| vix | 16.34 |
| fred_verdict | Late Cycle Tightening |

**關鍵主題**
- High Treasury yields pressure equity valuations
- Softer inflation offset by resilient activity
- Elevated credit stress and weak participation
- Iran-linked oil volatility adds inflation risk

---

## Final Visualization Table

<!--FACTS:lane_scores:start-->
| Lane | Score（−3 … +3） |
|---|---|
| Fundamentals | 2 |
| Sentiment | -0.53 |
| News | 1.5 |
| Technical | 1.5 |
| Valuation | 0.0 |
| Burry（獨立否決軌） | 27.7 / 100 |
| Red Team | STRONG_COUNTER |
<!--FACTS:lane_scores:end-->

---

## 詳細評分

### Fundamentals（BUY, Score 2, Conf 0.79｜phase0_alignment: MISALIGNED）

**Key Factors**
- Revenue up 106% YoY
- Operating margin above 65%
- Net cash and low leverage

**Risk Flags**
- Negative accruals quality flag
- FCF yield only 2.28%

**Moat**：WIDE — scale_economies

> ~75% gross and 65% operating margins with 106% revenue growth; curated peer cohort unavailable.

**Bull Thesis**：Revenue grew 106% YoY with ~65% operating margins, 128% forward EPS growth, and net cash.

**Bear Thesis**：FCF yield is 2.28%, accruals carry a warning, and elevated real rates pressure technology valuations.

**Near-term Catalysts**

| 日期 | 類型 | 影響 | 說明 |
|---|---|---|---|
| 2026-11-18 | earnings | high | Next earnings estimate; ticker bundle lists Nov 17 while analyst bundle lists Nov 18. |
| 2026-11-18 | guidance | high | Management guidance at the next earnings release; separate timing not supplied. |
| 2026-Q4 | macro_event | low | INSUFFICIENT_DATA — no additional dated catalyst supplied in frozen inputs. |

---

### Sentiment（HOLD, Score -0.53, Conf 0.72｜phase0_alignment: ALIGNED）

**Key Factors**
- Recent insider selling; MSPR deeply negative
- Weak breadth; VIX remains normal
- Low short interest cushions sentiment

**Risk Flags**
- Insider and congressional selling signals
- Weakening market breadth

---

### News（BUY, Score 1.5, Conf 0.62｜phase0_alignment: MISALIGNED）

**Key Factors**
- Buyback expansion signals management confidence
- Vera Rubin reaches production workloads
- Upward PT revisions support momentum

**Risk Flags**
- No rating changes reported in 30 days
- Macro yields, capex scrutiny, China competition

**Reasoning**：Coverage leans bullish on buyback expansion, initial Vera Rubin production deployment, a Buy consensus, and upward one-month PT revisions; absent recent rating actions, AI capex and China risks, and Phase 0 macro headwinds limit conviction.

pt_revision_momentum：UP（1M 15.07%／3M N/A）；decision_point_days 21；immediate_catalyst_5d N/A

**Cross-asset Spillover**

| 資產 | 方向 | 機制 |
|---|---|---|
| sector_XLK | BULLISH | Vera Rubin production deployment supports semiconductor demand sentiment. |

---

### Technical（HOLD, Score 1.5, Conf 0.74｜phase0_alignment: MISALIGNED）

**Key Factors**
- Price above 20/50/200-day averages
- RSI bullish; MACD positive but flat
- Normal volume; resistance near $230

**Risk Flags**
- Resistance near $229.98
- Insider transactions show net distribution

**Pattern**：consolidation；market_strength STRONG

> 確認條件：A close above $229.98 with volume above the 20-day average confirms an upside breakout; a close below $221.09 invalidates the range.

**Key Levels**：support $221.09／resistance $229.98／pivot $227.67

ATR-14 N/A；hist_vol_20d_daily N/A；momentum_20d N/A

**Smart Money**：distributing

> Q3 acquired/disposed ratio of 0.0882 indicates insider distribution; normal volume and a 0.51% gain provide no strong accumulation confirmation.

**High-prob Scenario**：If price holds $221.09 support, it is likely to retest $229.98 over 5–15 days; a close above it on volume above the 20-day average opens $233.21.

---

### Valuation（HOLD, Score 0.0, Conf 0.6｜phase0_alignment: ALIGNED）

**Key Factors**
- Fair-value blend is near the current price
- Two correlated DCF anchors share one group
- No business-similar peer cohort is available

**Risk Flags**
- Outlier owner-earnings anchor weakens robustness
- Fundamental and analyst anchors diverge widely

Lane 自算 weighted_fair_value $220.12（vs 現價 -3.61%）

**⚠ Outlier anchors（engine 自標，未從加權中剔除）**

- `owner_earnings_mult` = 15.75（有效權重 0.166667） —— outside [73.00, 657.04] (median 219.01 × 1/3..3)

---

### Contrarian（Burry Score 27.7 / 100, N/A, veto_flag N/A）

**Narrative（僅註記，不調分）**：FCF yield 0.8% │ EV/EBITDA 27.2 │ D/E 0.17 │ 3% below 52wH │ insider=SELL

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
| fwd_earnings_discounted | $215.50 | N/A |

- 加權合理價 (weighted_fair_value): $220.12（vs 現價 -3.61%）
- Verdict band: fairly_valued｜confidence: medium｜current_price: $228.38
- 區間 (fair_value_range): P25 $131.46 / P50 $225.74 / P75 $288.68｜min–max anchor $15.75–$345.21｜fair_zone｜錨一致度 medium
- 隱含預期 (implied_expectations): 現價隱含 5Y FCF CAGR 60.0%（out_of_range: True，WACC 0.0976）
- 前瞻驗證 (forward_validation): **STRETCHED**；DCF gap -58.39%；支持 archetype_shadow, forward_earnings, revenue_path；失敗 無
- Valuation score: 0.0 → 0.0；T5 hard downgrade eligible: False
<!--FACTS:fair_value_anchors:end-->

### 5 日機率帶

- Band（Capped）：[下界 $221.09 / 點估計 $227.52 / 上界 $229.98]
- Drift (drift_sigma)：-0.1
- Sigma Daily：0.01684
- ATR-14：5.2971
- Confidence：high
- Catalyst Widened：false
- 關鍵水位反射註記：下界受 support $221.09 撐住（原始 $216.51）；上界受 resistance $229.98 壓制（原始 $238.53）

### 60 日 target

- Momentum Target：$235.12
- PT 60D：$247.58
- Earnings Revision：N/A
- 權重：momentum 0.5333 / pt_60d 0.4667 / earnings_revision N/A
- Mid Target：$240.94
- Reality Check：需突破 $229.98 才成立

### 三框收斂訊號

mhp_signal：wait_for_pullback — 5d 帶下界 $221.09 > 長期FV $220.12 → 短期超漲、長期偏貴，等回檔

### Archetype Shadow（advisory，不進決策）

Archetype：hypergrowth；weighted_fair_value_shadow $241.22（vs 現價 5.62%，verdict_band_shadow：fairly_valued）；flip_vs_live：false。

---

## Red Team Counter Thesis

### Consensus View（市場共識）

<!--NARRATIVE:consensus_view:start-->
Lane 訊號分佈：Fundamentals BUY (2)／Sentiment HOLD (-0.53)／News BUY (1.5)／Technical HOLD (1.5)／Valuation HOLD (0.0)。 最高分 lane 為 Fundamentals（2.0），最低分為 Sentiment（-0.53）。
<!--NARRATIVE:consensus_view:end-->

### Differentiated View（本委員會差異化判斷）

<!--NARRATIVE:differentiated_view:start-->
委員會結論 HOLD，final_score 0.7151 / 3.0。 polarization=ALIGNED（來源 calculation_steps）；macro_alignment=CONTRARIAN；red_team=STRONG_COUNTER。
<!--NARRATIVE:differentiated_view:end-->

### Counter Thesis

NVDA’s mixed HOLD is vulnerable because the $228.38 price implies a 60% five-year FCF CAGR, while the frozen inputs provide no actual or lane FCF growth estimate; the weighted fair value is $220.12, and the 10-year real yield is 2.88%. The analyst revenue path of 39.28% CAGR does not establish that FCF can meet the higher implied hurdle.

red_team_verdict STRONG_COUNTER｜counter_evidence_strength 4/5｜thesis_break_probability 0.42

### Kill Conditions

<!--FACTS:kill_conditions:start-->
1. IF FCF growth is below 30% annualized across the next two reported quarters WITHIN 180 days THEN the price-implied 60% five-year FCF growth case breaks.
2. IF year-over-year revenue growth falls below 36% in either of the next two quarterly reports WITHIN 180 days THEN the price-implied revenue path breaks.
3. IF the FRED 10-year real Treasury yield remains at or above 2.88% for the next 90 days THEN persistent discount-rate pressure and the $220.12 weighted fair value leave the $228.38 price without a rate-supported valuation cushion.
<!--FACTS:kill_conditions:end-->

---

## 進場計畫

### Base Case

| 欄位 | 值 |
|---|---|
| Entry（積極） | $227.52 – $229.98 |
| Entry（保守） | $221.09 – $227.52 |
| Take Profit | $229.98 |
| Stop Loss | $218.88 |
| Risk / Reward | 4.02 |
| Staged Split | N/A |
| Position Size | 0.00% |
| Position Size Method | RULE_BASED |
| Time Horizon | mid |

> position_size_pct = 0 —— 本次不建倉。上表 entry 區間僅為再評估參考，非進場掛單。

### Bull Case

<!--NARRATIVE:bull_case:start-->
上檔參考：60 日 mid_target $240.94（成立條件：需突破 $229.98 才成立）；關鍵阻力 $229.98。
<!--NARRATIVE:bull_case:end-->

### Bear Case

<!--NARRATIVE:bear_case:start-->
下檔紀律：跌破 5 日帶下界 $221.09 或 support $221.09 即退出；stop_loss $218.88，另有 3 條 kill conditions 見上節。
<!--NARRATIVE:bear_case:end-->

---

## 關鍵風險

<!--FACTS:key_risks:start-->
- 現價隱含五年 FCF CAGR 約 60%，但凍結資料沒有實際或 lane 預估的 FCF 成長率可確認此門檻。
- Fundamentals 與 Burry 輸入的 FCF yield 分別為 2.28% 與 0.76%；口徑與期間未在本次輸入中調和。
- 估值僅有 5/9 錨點、同業群不足，Forecaster 因預測信心低而排除；估值結論受資料覆蓋限制。
- 內部人交易偏向賣出、廣度轉弱，且高實質利率可能壓抑高估值科技股。
- forecaster transition source 與來源 bundle 的 mtime 相差約 9.2 小時，Phase 3 發出 transition_mtime_skew 高度警示。
<!--FACTS:key_risks:end-->

---

## Watch / 再評觸發條件

<!--FACTS:watch_conditions:start-->
- **fcf_growth**: 接下來兩次財報若年化 FCF 增速低於 30%，重新檢視現價隱含的長期現金流成長要求。
- **revenue_growth**: 接下來兩次財報任一次營收年增低於 36%，重新評估目前營收路徑是否仍能支持估值。
- **real_yield**: 若美國 10 年期實質殖利率連續 90 天維持在 2.88% 或以上，重新評估折現率壓力與估值折價。
- **range_support**: 若收盤跌破 221.09 美元，視為目前整理區間失效並重新評估風險。
- **breakout_confirmation**: 只有收盤站上 229.98 美元且成交量高於 20 日均量，才確認向上突破情境。
<!--FACTS:watch_conditions:end-->

---

*分析基準日：2026-10-01｜分析價格：$228.38｜price engine：compute_price_framework.py v2.4 (V4.131.13)｜renderer：render_investment_report.py v1.0.0 (V4.87.0)｜polish：none*

## 本場資料與執行紀錄

場次 `NVDA_20261001T094245_fac61d27a6` · 凍結時間 2026-10-01T01:43:19.967421+00:00
統一計價 $228.38 · 執行品質 complete
快照摘要 `sha256:1f71223d45b6688a0f8df9188a7c1be419b54e8747b634857604e87b6cb774ae`
Red Team synthetic: false

| 價格來源 | 原始價格 | 與凍結價差 | 抓取時間 | 行情時間 |
|---|---:|---:|---|---|
| FMP frozen quote | 228.38 | 0.0 | 2026-10-01T01:42:50.535329+00:00 | 1790798401 |
| Finnhub scoring | 228.38 | 0.0 | 2026-10-01T01:42:52.872383Z | None |
| FMP audit | 228.38 | 0.0 | 2026-10-01T01:42:52.872383Z | None |
