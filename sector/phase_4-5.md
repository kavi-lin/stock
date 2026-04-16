# Phase 4–5 執行細節

---

## PHASE 4 — MULTI-AGENT DEBATE

**Agent**: Portfolio Strategist (PS) 主持，各 Agent 輪流發言

---

### Step 1 (Phase 4a) — 各 Agent 提案

三個 Agent（Sector Rotation / Theme Intelligence / News Catalyst）同時提案，PS 合成。
可**並行執行**，最後由 PS 整合。

**JSON Schema** → 見 `schema.md` Phase 4a

---

### Step 2 (Phase 4b) — Devil's Advocate

#### consensus_warning 精確定義

```
consensus_warning = true  IF 某板塊同時滿足所有三個條件：
  ✓ Phase 1: rotation_signal = INFLOW
  ✓ Phase 2: lifecycle_stage ∈ [Accelerating, Trending]
  ✓ Phase 3: sector_news_sentiment = bullish

  表示：輪動、主題熱度、新聞催化三者全看多，無任何分歧。

DA 義務規則：
  IF consensus_warning = true:
    → MUST 提交 challenge_targets（不可省略）
    → counter_evidence ≥ 2 句（含具體數據或邏輯）
    → 若無實質論點 → 標記 "FORCED_CHALLENGE_WEAK"（低信度）

  IF consensus_warning = false:
    → 優先挑戰 tail_risk_score 最高的 2-3 個板塊
```

#### Tail Risk 觸發規則

> **效率上限**：HOT 產業 > 3 個 → 僅對 `composite_score` 前 3 名執行 `tail-risk-analyzer`，其餘標記 `SKIPPED_CAPACITY_LIMIT`。

```
對每個納入檢查的 HOT 產業（composite_score > 75）的 proxy_etf：
→ 執行 tail-risk-analyzer skill（per-stock mode，傳入 proxy_etf ticker）
→ fragility_label = FRAGILE 或 EXTREMELY FRAGILE
  → 必須將此產業加入 challenge_targets
→ tail_risk_score > 70 OR excess_kurtosis > 5
  → risk_flags += "fat_tail_warning"
→ 2020 COVID 情境回測下跌 > 40%
  → risk_flags += "crash_vulnerability"
```

**JSON Schema** → 見 `schema.md` Phase 4b

---

### Step 3 (Phase 4c) — PS 仲裁決策樹

```
PORTFOLIO STRATEGIST ARBITRATION DECISION TREE
═══════════════════════════════════════════════

STEP A — Signal Conflict Check
  IF signal_conflict = true:
    → final_regime_stance CANNOT be AGGRESSIVE
    → max allowed = NEUTRAL

STEP B — Exposure Floor Check
  IF synthesized_exposure < 40%:
    → MUST flag ≥ 3 sectors as AVOID（無例外）

STEP C — Cycle Adjustment
  IF cycle_phase ∈ [Late, Recession]:
    FOR EACH cyclical sector  → composite_score × 0.85
    FOR EACH defensive sector → composite_score × 1.10

STEP D — Tail Risk Downgrades
  IF fragility_label = EXTREMELY_FRAGILE:
    → DOWNGRADE: HOT → WARM（不調整分數，直接降 label）
    → risk_flags += "fragility_downgrade"
  ELIF (fragility_label = FRAGILE AND extreme_sentiment_triggered = true):
    → DOWNGRADE: HOT → WARM
    → risk_flags += "extreme_sentiment_fragile_combo"

STEP E — Binary Risk
  FOR EACH upcoming_binary_risk (timing = within_48h):
    FOR EACH affected_sector:
      → composite_score × 0.70
      → risk_flags += "binary_risk_within_48h"

STEP F — Consensus Safeguard
  IF (consensus_warning = true AND devils_advocate_accepted = []):
    → regime_confidence × 0.85

STEP G — Signal Conflict Safeguard
  IF (signal_conflict = true AND sector.verdict = HOT):
    → DOWNGRADE to WARM

FINAL VERDICT ASSIGNMENT:
  score = adjusted composite_score（套用所有乘數後）
  score >= 75 → HOT（除非 STEP D 降級）
  50-74      → WARM
  25-49      → COLD
  < 25       → AVOID
  Cap: score ∈ [0, 100]

FINAL REGIME STANCE:
  HOT >= 3 AND AVOID = 0 AND synthesized_exposure >= 60% → AGGRESSIVE
  HOT >= 1 AND median_verdict >= WARM                    → NEUTRAL
  COLD >= 3 OR synthesized_exposure < 40%                → DEFENSIVE
```

**JSON Schema** → 見 `schema.md` Phase 4c

---

## PHASE 5 — SECTOR VERDICT

**Agent**: Portfolio Strategist (PS)

完成後執行：
1. 寫入 `./sector_logs/YYYY-MM-DD_sector_intel.json`（供 bridge.py 和其他 protocol 讀取）
2. 將 FINAL VERDICT TABLE 存為 `../reports/YYYY-MM-DD_sector_report.md`

> ⚠️ **JSON Schema 必須嚴格遵守**（見 `schema.md` Phase 5）：
> - `bridge.py` 依賴 `_phase0`、`_phase1`、`_phase3` 三個子物件，key 名稱不可更換
> - `protocol_version` 固定為 `"V1.2"`
