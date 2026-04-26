# Phase 4–5 執行細節

---

## PHASE 4 — MULTI-AGENT DEBATE

**Agent**: Portfolio Strategist (PS) 主持，各 Agent 輪流發言

---

### Step 1 (Phase 4a) — 各 Agent 提案（V1.3 parallel subagent fan-out · V1.4 加 FRED lane）

#### 執行流程（MUST use Agent tool × N in single message）

PS 以**單一訊息**同時發出 N 個 Agent tool call（N=4 當 `fred_available=true`，N=3 否則），等全部 JSON 回來再進入 Phase 4b。每個 subagent 僅收自己 lane 的資料切片 + Phase 0 macro，**看不到**其他 agent 的提案。

```
Agent(description="Sector Rotation proposal",    subagent_type="general-purpose", prompt=<rotation-lane prompt>)
Agent(description="Theme Intelligence proposal", subagent_type="general-purpose", prompt=<theme-lane prompt>)
Agent(description="News Catalyst proposal",      subagent_type="general-purpose", prompt=<news-lane prompt>)
Agent(description="FRED Macro proposal",         subagent_type="general-purpose", prompt=<fred-lane prompt>)   # only if fred_available
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

#### Lane 具體差異

| Lane | 資料切片 | 判斷焦點 |
|---|---|---|
| **Sector Rotation** | `_phase1.sectors[]`（uptrend_ratio / rotation_signal / overbought_risk / ytd_perf_note）| INFLOW vs OUTFLOW 資金輪動、Late cycle overbought 風險 |
| **Theme Intelligence** | Phase 2 theme-detector 輸出（lifecycle_stage / theme_heat / affected_sectors） | Accelerating / Trending 主題帶動的板塊、生命週期末期主題 |
| **News Catalyst** | `_phase3.top_catalysts[]` + `sector_news_sentiment` + `upcoming_events[]` (filter `is_binary=true`) | 48h 內催化劑、財報窗口、政治事件受益/受損 |
| **FRED Macro** (V1.4) | `_phase0.fred_snapshot`（regime_label / regime_confidence / sector_rotation_favor·avoid / yield_curve / credit_stress / real_rate / velocity_highlights） | 結構性 macro regime（Goldilocks/Overheating/Late Cycle Tightening 等）對應的 favor/avoid sectors；對齊 SECTOR_ROTATION_GUIDE 規則 |

#### FRED Macro Lane Prompt（額外規則）

> Lane 收 `_phase0.fred_snapshot` 整段。**必讀** `skills/fred-macro/SECTOR_ROTATION_GUIDE.md`：
> - `favor[]` = base map；`adjustments[]` overrides favor (不可只重複 favor)
> - 優先序：credit_stress_elevated > yield_curve_inverted > real_rate_high > yield_curve_steep
> - `regime_confidence < 0.40` → `key_rationale` 開頭加 "LOW-CONFIDENCE"

#### Fan-In 驗證（PS 層）

1. N 個 subagent 全回傳 + `subagent_isolated=true` → `phase4_fanout_mode: PARALLEL_SUBAGENT`
2. 任一 retry 1 次仍失敗 → inline fallback (confidence cap 0.6)；加入 `degraded_agents` → `PARTIAL_FALLBACK`
3. ≥ N-1 失敗 → 整體 inline → `FULL_FALLBACK` + Phase 4c `final_regime_stance` 不得 AGGRESSIVE
4. `fred_available=false` → FRED lane skip，不算 degraded

**JSON Schema** → 見 `schema.md` Phase 4a

---

### Step 2 (Phase 4b) — Devil's Advocate（V1.3 獨立 subagent）

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

  PHASE 0 FRED MACRO SNAPSHOT (V1.4，slim — 若 fred_available=false 顯示 "FRED unavailable"):
  <paste _phase0.fred_snapshot 整段（11 個欄位）>

  PHASE 4a PROPOSALS（N agent 的 HOT/COLD 提案；含 FRED Macro lane 若可用）:
  <paste rotation / theme / news / [fred] agent 的 top_conviction_hot/cold + key_rationale>

  PHASE 4b TAIL-RISK RESULTS（已執行 tail-risk-analyzer on top 3 HOT proxy_etf）:
  <paste tail_risk_checks[]>

  CONSENSUS_WARNING: <true | false>（若 true 表示該板塊在 rotation/theme/news 三方向全看多，你必須強力挑戰）

  TASK:
  1. 若 consensus_warning=true → MUST 提交 challenge_targets（不可省略）；counter_evidence ≥ 2 句含具體數據
  2. 若 consensus_warning=false → 優先挑戰 tail_risk_score 最高的 2-3 個板塊
  3. 每個 challenge_target 必須 falsifiable（IF <條件> WITHIN <天數> THEN <推翻論點>）
  4. (V1.4) FRED 衝突挑戰規則 — 若 fred_snapshot 顯示與某 HOT 提案衝突的訊號：
       - yield_curve_inverted = true
       - real_rate_preferred > 2.0
       - credit_stress_elevated = true
       - financial_stress_above_avg = true
       - regime_label ∈ {Late Cycle Tightening, Stagflation, Recession Risk, Recession Easing}
       - sector ∈ fred_snapshot.sector_rotation_avoid
     → MUST 構造 kill_conditions 引用 **具體 FRED 數值**（"real_rate 1.92% > 2.0% threshold"），
       不可寫 vague 的「macro 轉差」或「總體環境不佳」

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

#### consensus_warning 定義

```
consensus_warning = true  IFF 某板塊同時滿足三條件：
  ✓ Phase 1: rotation_signal = INFLOW
  ✓ Phase 2: lifecycle_stage ∈ [Accelerating, Trending]
  ✓ Phase 3: sector_news_sentiment = bullish

DA 義務：
  consensus_warning = true  → MUST challenge_targets ≠ []，counter_evidence ≥ 2 句
                              無實質論點 → 標 "FORCED_CHALLENGE_WEAK"
  consensus_warning = false → 優先挑戰 tail_risk_score 前 2-3
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

STEP C — Cycle Adjustment（僅 fred_available=false 時跑；fred_available=true 改用 STEP C.6）
  IF cycle_phase ∈ [Late, Recession]:
    FOR EACH cyclical sector  → composite_score × 0.85
    FOR EACH defensive sector → composite_score × 1.10

STEP C.6 — Step 6 FRED Regime Overlay（取代 STEP C 當 fred_available=true）
  ⚠️ MUST 用 script，不可 LLM 心算。

  執行：
    1. 蒐集 11 sector base_score (Step 1-5 後)
    2. 跑：
       python3 sector/scripts/step6_overlay.py --input "Industrials:73,Technology:62,..."
    3. Paste 回傳 JSON 的 step6_overlay block + 每 sector 的 step6_fred_multiplier
       (script 已套 confidence gating)

  fred_available=false → 跳過，回 STEP C。

STEP D — Tail Risk Downgrades
  IF fragility_label = EXTREMELY_FRAGILE:
    → DOWNGRADE: HOT → WARM（不調整分數，直接降 label）
    → risk_flags += "fragility_downgrade"
  ELIF (fragility_label = FRAGILE AND extreme_sentiment_triggered = true):
    → DOWNGRADE: HOT → WARM
    → risk_flags += "extreme_sentiment_fragile_combo"

STEP E — Binary Risk
  FOR EACH ev IN upcoming_events WHERE ev.is_binary AND ev.within_48h:
    FOR EACH sector IN ev.sectors:
      → composite_score × 0.70
      → risk_flags += "binary_risk_within_48h"

STEP F — Consensus Safeguard
  IF (consensus_warning = true AND devils_advocate_accepted = []):
    → regime_confidence × 0.85

STEP G — Signal Conflict Safeguard
  IF (signal_conflict = true AND sector.verdict = HOT):
    → DOWNGRADE to WARM

STEP G.5 — FRED Macro vs Theme/Rotation Conflict
  Trigger（per sector）:
    - sector ∈ fred_snapshot.sector_rotation_avoid
    - AND {Theme | Rotation | News} 任一 lane proposed HOT for same sector
  Action:
    → cap verdict = WARM (不允許 HOT)
    → risk_flags += "macro_theme_divergence"
    → regime_confidence × 0.90

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

STEP H — Today Verdict（必填，繁中）

  所有文字欄位（headline / one_liner / key_takeaways / sector_actions.reason /
  watch_next）必須繁中。技術術語（FTD/RSI/MA/FOMC）可保留英文。

  "today_verdict": {
    "headline":    string ≤ 60 chars,         // stance + 核心診斷
    "stance":      AGGRESSIVE|NEUTRAL|DEFENSIVE,
    "confidence":  0.0-1.0,
    "one_liner":   string ≤ 160 chars,
    "key_takeaways": [3-5 條, 動詞開頭, 可操作化],
    "sector_actions": [
      { "sector": <name from sectors[]>,
        "action": overweight|wait|neutral|underweight|avoid,
        "confidence": high|medium|low,
        "reason": string ≤ 50 chars }
    ],                                        // 精選 4-6 個
    "watch_next": [3-5 條 trigger 監控點]
  }

  規則:
  - action=overweight  → verdict ∈ {HOT, WARM}
  - action=avoid       → verdict ∈ {COLD, AVOID}
  - action=wait        → verdict=WARM (高不確定性)
  - key_takeaways[0]   → 必須點出今日 stance 主因
  - watch_next         → 必須涵蓋全部 upcoming_events 中 is_binary=true AND within_48h=true 的事件
```

**JSON Schema** → 見 `schema.md` Phase 4c

---

## PHASE 5 — EMIT JSON + RENDER MARKDOWN

**Agent**: Portfolio Strategist (PS) · **無模型 — 機械步驟**

### Step 1 — 寫入 JSON

寫 `./sector_logs/YYYY-MM-DD_sector_intel.json`，shape 嚴格符合 `schema.md` Phase 5。
`_phase4c.today_verdict` 全欄位必填（renderer 的文字來源）。

### Step 2 — Validator Gate（MANDATORY）

```bash
python3 sector/scripts/validate_sector_intel.py
```

rc ≠ 0 必須修正 JSON 後重跑，直到 rc=0 才可進 Step 3。常見失敗：
- `protocol_version` 非 `V1.3`
- `_phase0` / `_phase1` / `_phase3` 缺必填 key
- `_phase3.top_catalysts` < 5 筆
- HOT sector 缺 `proxy_etf`
- 缺 `phase4_fanout_mode` / `degraded_agents`

### Step 3 — Render Markdown（MANDATORY，無模型）

```bash
python3 sector/scripts/render_sector_report.py
```

產出 `reports/YYYY-MM-DD_sector_report.md`。

**禁止**：PS 不得用 Write 手寫或改寫 markdown。輸出有問題就修 JSON 或 renderer，不是 markdown。

### Step 4 — 回覆使用者（≤ 10 行）

回報：
- Validator rc + sector 計數
- Renderer 輸出路徑 + 行數
- 三行濃縮：stance / synthesized_exposure / 本週關鍵事件
- （可選）Sources 連結清單

不重複 `today_verdict` 內容 — 使用者會直接看 markdown。

> Schema 紅線：`bridge.py` 依賴 `_phase0` / `_phase1` / `_phase3` 鍵名不可改；`protocol_version` 固定 `"V1.3"`。
