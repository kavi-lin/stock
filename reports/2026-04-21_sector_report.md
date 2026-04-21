# Pre-Market Sector Intelligence — 2026-04-21

## Final Verdict Table

| Sector                 | Verdict | Score | Key Reasons (top 2)                                              | Tail Risk | Proxy ETF | Risk Flags                       |
|------------------------|---------|-------|------------------------------------------------------------------|-----------|-----------|----------------------------------|
| Industrials            | HOT     | 75    | Slope +0.047 highest cyclical leader; FTD Day 14 Power Trend     | ROBUST    | XLI       |                                  |
| Materials              | WARM    | 72    | Ratio 0.605 +27pp above 10MA; DA HIGH blow-off challenge accepted| ROBUST    | XLB       | overbought                       |
| Financials             | WARM    | 62    | Russell 2000 record broadening rally; regional-bank beta         | ROBUST    | XLF       |                                  |
| Healthcare             | WARM    | 52    | Ratio 0.416 Overbought + slope +0.031; defensive catch-up bid    | N/A       | XLV       | overbought                       |
| Real Estate            | WARM    | 52    | Ratio +13pp above 10MA; rate-stability tailwind                  | N/A       | XLRE      |                                  |
| Communication          | COLD    | 47    | Nasdaq 13-day streak snapped 4/20; AI theme Exhausting           | N/A       | XLC       |                                  |
| Technology             | COLD    | 42    | TSLA/IBM/INTC binary 4/22-23; SPY RSI 97.7 + AI Exhausting       | ROBUST    | XLK       | binary_risk_within_48h, overbought |
| Consumer Discretionary | COLD    | 42    | TSLA binary 4/22; gas $4/gal headwind                            | N/A       | XLY       | binary_risk_within_48h           |
| Energy                 | COLD    | 36    | Only downtrending sector -21pp below 10MA; Iran truce binary     | ROBUST    | XLE       | binary_risk_within_48h           |
| Consumer Staples       | COLD    | 33    | Ratio 0.233 near flat vs 10MA; bearish concentration theme       | N/A       | XLP       |                                  |
| Utilities              | COLD    | 28    | Ratio -11pp BELOW 10MA; OUTFLOW rotation                         | N/A       | XLU       |                                  |

---

## Market Context

**Market Regime**: RISK_ON  |  **Breadth Ceiling**: 60-75%  |  **Synthesized Ceiling**: 60-75%  |  **Cycle**: Mid
**Sentiment**: Fear & Greed [69.9 / 73.4 Greed]  |  **VIX**: 18.87  |  **Put/Call**: N/A  |  **Signal Conflict**: No

**Phase 0 Signal Stack**:
- Breadth composite 42.4 Neutral zone (delta +5.6 improving over 5 observations; 8MA=0.566 in downtrend)
- FTD CONFIRMED Day 14 post 2026-03-30 rally low, Quality 100/100, Power Trend YES, 0 distribution days
- Market Top composite 29.2 Yellow Early_Warning (but internal Distribution Day sub-score 90 CRITICAL)
- 3 signals aligned (diff 20pp < 30pp threshold) → no signal_conflict
- Phase 4 fan-out: PARALLEL_SUBAGENT (4a × 3 lanes + 4b DA all returned `subagent_isolated: true`)

---

## Phase 4a Cross-Lane Conviction Map

| Sector                 | Rotation (CSV)     | Theme (heat)          | News Catalyst        | Cross-Lane Signal  |
|------------------------|--------------------|-----------------------|----------------------|--------------------|
| Industrials            | HOT (slope top)    | HOT (Defense 57)      | —                    | **2/3 HOT**        |
| Energy                 | COLD (downtrend)   | HOT (Oil 57 Accel)    | HOT (WTI $100)       | **Contradiction**  |
| Materials              | HOT (ratio 0.605)  | —                     | —                    | 1/3 HOT            |
| Financials             | —                  | —                     | HOT (Russell record) | 1/3 HOT            |
| Technology             | —                  | COLD (AI Exhausting)  | COLD (binary × 3)    | **2/3 COLD**       |
| Consumer Discretionary | —                  | —                     | COLD (gas, TSLA)     | 1/3 COLD           |
| Healthcare             | —                  | COLD (bearish H&P)    | —                    | 1/3 COLD           |
| Utilities              | COLD (below 10MA)  | —                     | —                    | 1/3 COLD           |

Consensus_warning: **false** (no sector has all three lanes bullish with matching lifecycle + news sentiment).

---

## Devil's Advocate Challenges (Phase 4b)

All 5 HOT proxy ETFs scored ROBUST on tail-risk-analyzer → no fragility-label downgrades.

| Challenged Sector | Call | Confidence | Risk Scenario (falsifiable) |
|-------------------|------|------------|------------------------------|
| Materials | HOT | HIGH | IF XLB closes >2% below 10MA on a day SPY RSI falls <70 WITHIN 7 trading days THEN blow-off top confirmed → **accepted, downgraded WARM** |
| Energy | HOT | HIGH | IF WTI drops >5% single-day on Hormuz de-escalation WITHIN 10 days AND XLE fails 50DMA reclaim THEN Energy HOT invalidated → **accepted, COLD retained** |
| Industrials | HOT | MEDIUM | IF breadth fails to break 50 AND SPY prints 1 distribution day WITHIN 5 days THEN FTD quality suspect → **rejected, HOT held** |
| Technology | COLD | MEDIUM | IF 2-of-3 (TSLA/IBM/INTC) beat + guide in-line WITHIN 4/22-23 THEN XLK +2.5% squeeze → **accepted for risk flag; COLD retained** |
| Consumer Discretionary | COLD | MEDIUM | IF Russell 2000 makes 2nd new high AND XLY reclaims 20DMA on volume WITHIN 10 days THEN small-cap broadening → **accepted for watch; COLD retained** |

---

## Portfolio Strategist Arbitration (Phase 4c)

**Decision Tree Path**: A:pass(signal_conflict=false) → B:pass(synth_exp 60-75%) → C:no-op(Mid cycle) → D:no-downgrade(all ROBUST) → **E:3 binaries_48h applied × 0.70 to Technology/Energy/Consumer_Discretionary** → F:no-op(consensus_warning=false) → G:no-op → H:today_verdict emitted.

Mechanical rule: **COLD=6 ≥ 3 → DEFENSIVE** triggered. synthesized_exposure 60-75% allows selective WARM cyclical expression under defensive stance.

**Final Regime Stance**: **DEFENSIVE**  |  **Regime Confidence**: 0.55

**Confidence rationale**: Reduced by three divergences:
1. Breadth Neutral 42.4 <50 vs FTD CONFIRMED quality 100 → strength unconfirmed by participation
2. Market Top composite 29.2 Yellow but internal Distribution Day sub-score 90 CRITICAL
3. SPY RSI_14 97.7 historic extreme-overbought + F&G 73.4 Greed → tactical pullback probability elevated

---

## Today Verdict — Hero Card

> **DEFENSIVE — narrow cyclical lead, breadth 42 未確認**

**One-liner**: FTD Day 14 Power Trend 成立但 breadth 未破 50、SPY RSI 97.7 極端超買 + 4 項 48h binary 事件群 — 選擇性持 Industrials/Materials/Financials，避開 Tech/Energy/CD。

### Key Takeaways
1. DEFENSIVE stance 由 COLD=6 觸發；synthesized_exposure 60-75% 仍可持 Industrials/Materials/Financials 選股
2. SPY RSI 97.7 極端超買 + Greed 73.4 → 技術面 3-5% 回檔機率升高，新倉先緩一緩
3. 4/22–4/24 四項 binary 事件（TSLA/IBM/INTC 財報 + Iran 停火 deadline）before 重倉 Tech/Energy/CD
4. breadth 改善中（+5.6 delta 過去 5 次）但需突破 50 才能確認 FTD leadership broadening
5. Materials +27pp 偏離 10MA = blow-off 風險，追高進場用小倉位 + 緊停損

### Sector Actions

| Sector | Action | Confidence | Reason |
|--------|--------|------------|--------|
| Industrials | overweight | high | FTD Day 14 + 最強 slope +0.047 cyclical 主升 |
| Materials | wait | medium | +27pp 偏離 10MA blow-off 風險 |
| Financials | overweight | medium | Russell 2000 新高 broadening rally |
| Technology | wait | medium | TSLA/IBM/INTC 4/22-23 binary earnings |
| Energy | avoid | medium | commodity-equity 背離 + 停火 binary |
| Utilities | avoid | high | ratio below 10MA -11pp 防禦 laggard |

### Watch Next
- TSLA + IBM 財報 2026-04-22 AMC → XLK 隔日波動 ±2.5% 關鍵
- Intel 財報 2026-04-23 AMC → SOXX/SMH 再評價 + AI foundry 需求讀值
- Iran/Hormuz 停火 deadline 2026-04-24 → WTI 雙向 ±5% 觸發 XLE bimodal
- S&P 500 breadth composite 能否突破 50（目前 42.4，delta +5.6 過去 5 觀察改善中）
- SPY RSI_14 若回落至 70 以下 + 1 day distribution day → FTD 品質風險升級

---

## Divergence Watch

| Sector | Signal | Description | Action |
|--------|--------|-------------|--------|
| Energy | news+ / price− | WTI +40-50% from Hormuz yet XLE only downtrending sector — commodity-equity decoupling | reduce exposure |
| Materials | news− / price+ | Tariff+Hormuz raw-material cost shocks but ratio 0.605 +27pp above 10MA = late-stage blow-off possible | monitor |

---

## Top Themes Today
**Defense & Aerospace**, **Infrastructure & Construction**, **Oil & Gas (caution — binary truce)**, **AI & Semiconductors (caution — Exhausting)**

## Political Risk Summary
- **Active Trump trades**: Iran/Hormuz blockade bullish Energy/Defense · Tariff stack bearish Consumer_Discretionary
- **Named targets today**: Iran
- **Fear & Greed status**: Greed (73.4 composite, not extreme)

---

## Handoff to Investment Protocol
> 盤前：FTD Day 14 confirmed 但 breadth 42.4 未破 50 + SPY RSI 97.7 + 4 項 48h binary 事件群。DEFENSIVE stance 選擇性持 Industrials (HOT) / Materials / Financials / Healthcare / Real_Estate (WARM)；Tech/Energy/CD 因 binary 風險標記 COLD 暫避。synthesized_exposure 60-75% 上限，不追 overbought。
