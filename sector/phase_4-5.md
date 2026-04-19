# Phase 4–5 執行細節

---

## PHASE 4 — MULTI-AGENT DEBATE

**Agent**: Portfolio Strategist (PS) 主持，各 Agent 輪流發言

---

### Step 1 (Phase 4a) — 各 Agent 提案（V1.3 parallel subagent fan-out）

三個提案 agent 看三種不同的資料來源（Sector Rotation 看 Phase 1 CSV、Theme Intelligence 看 Phase 2 主題、News Catalyst 看 Phase 3 新聞），本質上彼此獨立。V1.3 改為 **3 個平行 Agent subagent** 消除同 model 序列產生 3 份提案的 anchoring 風險。

#### 執行流程（MUST use Agent tool × 3 in single message）

PS 以**單一訊息**同時發出 3 個 Agent tool call，等全部 3 個 JSON 回來再進入 Phase 4b。每個 subagent 僅收自己 lane 的資料切片 + Phase 0 macro，**看不到**其他 agent 的提案。

```
Agent(description="Sector Rotation proposal",    subagent_type="general-purpose", prompt=<rotation-lane prompt>)
Agent(description="Theme Intelligence proposal", subagent_type="general-purpose", prompt=<theme-lane prompt>)
Agent(description="News Catalyst proposal",      subagent_type="general-purpose", prompt=<news-lane prompt>)
```

#### 共通 Subagent Prompt 骨架

```
You are the <LANE> analyst for sector selection.

ISOLATION CONTRACT:
  - 你與其他 2 個 agent 以獨立 context 平行執行。
  - 看不到 Sector Rotation / Theme Intelligence / News Catalyst 其他兩 lane 的提案。
  - 禁止推測其他 lane 的結論、或為「與共識一致」調整 conviction。
  - 僅依你自己收到的資料切片做提案。

PHASE 0 MACRO CONTEXT（read-only shared）:
<paste phase0 macro_regime / cycle_phase / synthesized_exposure / signal_conflict>

YOUR LANE DATA:
<RUBRIC_LANE_DATA>

OUTPUT（單一 JSON object）:
{
  "phase": "4a",
  "agent": "<LANE>_Analyst",
  "top_conviction_hot": ["sector1", "sector2"],   // 排序由信度高到低
  "top_conviction_cold": ["sector1", "sector2"],
  "key_rationale": "string — 最多 2 句，基於你 lane 的具體證據",
  "subagent_isolated": true
}
```

#### 三 Lane 具體差異

| Lane | 資料切片 | 判斷焦點 |
|---|---|---|
| **Sector Rotation** | `_phase1.sectors[]`（uptrend_ratio / rotation_signal / overbought_risk / ytd_perf_note）| INFLOW vs OUTFLOW 資金輪動、Late cycle overbought 風險 |
| **Theme Intelligence** | Phase 2 theme-detector 輸出（lifecycle_stage / theme_heat / affected_sectors） | Accelerating / Trending 主題帶動的板塊、生命週期末期主題 |
| **News Catalyst** | `_phase3.top_catalysts[]` + `sector_news_sentiment` + `upcoming_binary_risks[]` | 48h 內催化劑、財報窗口、政治事件受益/受損 |

#### Fan-In 驗證（PS 層）

1. 3 個 subagent 都回傳 + 每個 `subagent_isolated=true` → `phase4_fanout_mode: PARALLEL_SUBAGENT`
2. 任一 retry 1 次仍失敗 → 該 agent 改 inline fallback（confidence cap 0.6）；`degraded_agents` 陣列加入該 agent → `phase4_fanout_mode: PARTIAL_FALLBACK`
3. 2-3 個失敗 → 整體 inline fallback → `phase4_fanout_mode: FULL_FALLBACK` + Phase 4c 仲裁 `final_regime_stance` 不得為 AGGRESSIVE（degraded 模式下不信任多頭共識）

**JSON Schema** → 見 `schema.md` Phase 4a

---

### Step 2 (Phase 4b) — Devil's Advocate（V1.3 獨立 subagent）

DA 的工作是**挑戰 Phase 4a 共識**。若 DA 在同一 model context 中看過三 agent 提案再登場，會有「我已經論證 HOT 三個板塊，現在硬擠反論」的 anchoring effect。V1.3 改為**獨立 Agent subagent**，只收 Phase 0-4a 輸出 + tail-risk 腳本結果，看不到自己的前文，才能真反駁。

#### 執行方式（MUST use Agent tool）

```
Agent(
  description="Devil's Advocate sector challenge",
  subagent_type="general-purpose",
  prompt="""
  You are DEVIL'S ADVOCATE. 你的任務是破壞 Phase 4a 的共識。

  ISOLATION CONTRACT:
    - 你以獨立 context 執行，看不到自己在其他 Phase 的推理。
    - 不要客氣、不要持平 — 任務是找反駁。

  PHASE 0 MACRO:
  <paste phase0 macro_regime / cycle_phase / synthesized_exposure / signal_conflict / extreme_sentiment>

  PHASE 4a PROPOSALS（3 agent 的 HOT/COLD 提案）:
  <paste rotation / theme / news 三 agent 的 top_conviction_hot/cold + key_rationale>

  PHASE 4b TAIL-RISK RESULTS（已執行 tail-risk-analyzer on top 3 HOT proxy_etf）:
  <paste tail_risk_checks[]>

  CONSENSUS_WARNING: <true | false>（若 true 表示該板塊在 rotation/theme/news 三方向全看多，你必須強力挑戰）

  TASK:
  1. 若 consensus_warning=true → MUST 提交 challenge_targets（不可省略）；counter_evidence ≥ 2 句含具體數據
  2. 若 consensus_warning=false → 優先挑戰 tail_risk_score 最高的 2-3 個板塊
  3. 每個 challenge_target 必須 falsifiable（IF <條件> WITHIN <天數> THEN <推翻論點>）

  OUTPUT JSON:
  {
    "phase": "4b",
    "agent": "Devils_Advocate",
    "tail_risk_checks": [<paste from tail-risk script>],
    "challenge_targets": [
      {
        "challenged_sector": "string",
        "challenged_call": "HOT | COLD",
        "counter_evidence": "string (≥ 2 句，含具體數據或邏輯)",
        "tail_risk_evidence": "string — 量化支撐（若有）",
        "risk_scenario": "IF <falsifiable> WITHIN <window> THEN <推翻>",
        "confidence_level": "HIGH | MEDIUM | LOW"
      }
    ],
    "consensus_warning": "true | false",
    "subagent_isolated": true
  }
  """
)
```

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

#### Fan-In 驗證（PS 層）

DA subagent 必須回傳 `subagent_isolated: true`。若：
- Subagent timeout / JSON 解析失敗 → retry 1 次；仍失敗 → inline fallback（記 `degraded_agents += ["Devils_Advocate"]`）
- `challenge_targets = []` AND `consensus_warning = true` → 視為違規 → retry 要求 DA 產出 2+ 個 challenge（不得放水）

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
1. 寫入 `./sector_logs/YYYY-MM-DD_sector_intel.json`（供 bridge.py 和其他 protocol 讀取）— shape **必須**嚴格符合 `schema.md` Phase 5
2. **執行驗證腳本**（V1.3 新增，MANDATORY gate）：
   ```bash
   python3 sector/scripts/validate_sector_intel.py
   ```
   rc ≠ 0 時必須修正 `sector_intel.json` 後再跑一次，直到 rc=0 才可進 Step 3。常見失敗：
   - `protocol_version` 非 `V1.3`
   - `_phase0` / `_phase1` / `_phase3` 缺必填 key
   - `_phase3.top_catalysts` < 5 筆（protocol 要求至少 5 筆）
   - HOT sector 缺 `proxy_etf`
   - 缺 V1.3 新增欄位 `phase4_fanout_mode` / `degraded_agents`
3. 將 FINAL VERDICT TABLE 存為 `../reports/YYYY-MM-DD_sector_report.md`

> ⚠️ **JSON Schema 必須嚴格遵守**（見 `schema.md` Phase 5）：
> - `bridge.py` 依賴 `_phase0`、`_phase1`、`_phase3` 三個子物件，key 名稱不可更換
> - `protocol_version` 固定為 `"V1.3"`
> - V1.3 新增頂層欄位：`phase4_fanout_mode`、`degraded_agents`
