# Phase 4–5 執行細節

---

## PHASE 4 — MULTI-AGENT DEBATE

**Agent**: Portfolio Strategist (PS) 主持，各 Agent 輪流發言

---

### Step 1 (Phase 4a) — 各 Agent 提案（V1.3 parallel subagent fan-out · V1.4 加 FRED lane）

#### 執行流程（MUST use Agent tool × N in single message）

PS 以**單一訊息**同時發出 N 個 Agent tool call（N=4 當 `fred_available=true`，N=3 否則），等全部 JSON 回來再進入 Phase 4b。每個 subagent 僅收自己 lane 的資料切片 + Phase 0 macro，**看不到**其他 agent 的提案。

> ❌ **硬規則 — 違規會慢數倍**：N 個 `Agent` tool_use **必須放在同一個 assistant
> message 內**（一則訊息含 N 個 tool_use block）。分多則訊息一次發一個 = subagent
> 被**強制序列化**，整個 Phase 4a 從 ~5 分變 ~20 分。發完這一則訊息後**停**，等 N
> 個 JSON 全回來再繼續 — 不要在等待期間插入其他 tool call。

```
# ✅ 正確：同一則訊息，N 個 Agent block 一起送
Agent(description="Sector Rotation proposal",    subagent_type="general-purpose", model="sonnet", prompt=<rotation-lane prompt>)
Agent(description="Theme Intelligence proposal", subagent_type="general-purpose", model="sonnet", prompt=<theme-lane prompt>)
Agent(description="News Catalyst proposal",      subagent_type="general-purpose", model="sonnet", prompt=<news-lane prompt>)
Agent(description="FRED Macro proposal",         subagent_type="general-purpose", model="sonnet", prompt=<fred-lane prompt>)   # only if fred_available
```

> 💰 **V3.44 — lane subagent 跑 Sonnet**：每個 lane 是**有界 JSON 任務**（收固定資料切片 → 出固定 schema 提案），不需 Opus 推理深度。`model="sonnet"` 砍 fan-out 段成本（~40%），**Arbiter（Phase 4c）留主模型 Opus** 做最終整合與決策樹。若 harness 不支援 `model=` 參數則忽略此欄、退回繼承主模型，不影響正確性。

> **V4.67.0 — Arbiter 降級模式（2+1 補償）**：session 開場檢查 Agent tool 的 `model` 可用值——
> **不存在高於 `sonnet` 的檔位**時，Phase 4c 改走 2+1（有高階檔照舊，本段零成本）：
> 1. PS 以單一訊息盲開 **2 個獨立 Arbiter subagent**（各收全部 lane 提案 + Phase 4b DA 結果 +
>    Phase 0 macro，prompt 完全相同、互相看不見），各自產出完整 Phase 4c 決策 JSON。
> 2. 第 3 個 **referee subagent**（fresh context）只回答三問：兩份決策哪裡矛盾（exposure /
>    sector 排序 / stance）；各自引用的證據哪份更硬；選哪份為主、需補什麼。**禁止 referee
>    重做決策樹**、禁止產生兩份都沒有的新結論。
> 3. Referee 輸出 = 既有單份 Phase 4c JSON（**不動 sector schema / validator**）；分歧摘要
>    1-2 句寫進既有 rationale 文字欄位，格式 `[2+1: <一句話分歧>]`。
> 4. 單份 Arbiter 失敗 → 直接採用另一份（等同原單軌）。
> 原理見 `docs/agent-ops/MODEL_DISPATCH.md` §6。

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

##### 條件式觸發 gate（V4.94.0 — **shadow-only，本版 lane 照跑**）

跑完 Phase 4a 後補一行（不影響本場任何決策，只累積樣本）：

```bash
python3 sector/scripts/fred_lane_gate.py --date {SCAN_DATE} \
        --hot "{Phase 4a HOT sectors}" --write
```

| Trigger | 意義 |
|---|---|
| `adjustments_active` | **mandatory** — `sector_rotation.adjustments` 非空。GUIDE RULE 1 要求 override favor，而**本專案只有這個 lane 會做**（`step6_overlay.py` 只讀 favor/avoid） |
| `adjustment_conflict` | 同一 sector 被不同 adjustment 一升一降 → 需 RULE 2 優先序仲裁 |
| `macro_theme_conflict` | Phase 4a HOT 撞上 FRED avoid 或 `adjustment.lower` |
| `regime_transition` | `regime_label` 與上一場不同 |

- 四條全靜默（adjustments 為空 = GUIDE RULE 4「base map valid as-is」）→ lane 只會覆述
  step6 已 deterministic 套完的 `favor[]`，增量趨近於零。
- `regime_confidence < 0.40` **不是** trigger：低信心時 step6 的 confidence gating 已把
  乘數壓回 1.0 附近，lane 增量更低。只記 note。
- **翻預設（skip 生效）需使用者拍板**，依賴 shadow 樣本；翻時唯一要小心的是
  **skip 不得寫進 `degraded_agents`**（會誤觸發 PARTIAL_FALLBACK 的 confidence cap 與
  stance 限制）。既有先例：`fred_available=false → FRED lane skip，不算 degraded`。
- 跳過**不改決策數字**（與 invest L4b 的 valuation lane 相反）：STEP G.5 直接讀
  `fred_snapshot.sector_rotation_avoid`、Step 6 走 `step6_overlay.py`、`consensus_warning`
  只定義在 rotation/theme/news 三 lane —— 都不經此 lane。

> ⚠️ **已知缺口（V4.94.0 記錄，未修）**：`_phase0.fred_snapshot` 的 slim 11 欄**不含
> `adjustments`**，但上面的規則要求 lane 套用它 —— lane 目前收不到這份資料。修法（把
> adjustments 併進 lane 切片）會改變 lane 產出，屬行為變更，不與 shadow-only 的 gate 同版動。
> gate 會在 `notes` 標出這件事。

#### Fan-In 驗證（PS 層）

1. N 個 subagent 全回傳 + `subagent_isolated=true` → `phase4_fanout_mode: PARALLEL_SUBAGENT`
2. 任一 retry 1 次仍失敗 → inline fallback (confidence cap 0.6)；加入 `degraded_agents` → `PARTIAL_FALLBACK`
3. ≥ N-1 失敗 → 整體 inline → `FULL_FALLBACK` + Phase 4c `final_regime_stance` 不得 AGGRESSIVE
4. `fred_available=false` → FRED lane skip，不算 degraded

**JSON Schema** → 見 `schema.md` Phase 4a

---

### Step 2 (Phase 4b) — Devil's Advocate（V1.3 獨立 subagent）

#### DA Pre-Trigger 計算（V4.12.2 prompt 瘦身 · V4.93.0 script 化）

> 結構性 divergence 規則 R4–R7 是**條件觸發**型：多數日子根本沒命中，但舊版每次把
> 4 條全文塞進 DA prompt（DA 是單一最肥 subagent input）。V4.12.2 改為只 paste fired
> 的規則塊；V4.93.0 進一步把**判定本身**從 PS 心算搬進 script。

⚠️ **MUST 用 script，不可 LLM 逐條比對**（同 `step6_overlay.py` 紀律）：

```bash
python3 sector/scripts/da_pretrigger.py --date {SCAN_DATE} \
        --hot "{Phase 4a HOT sectors，逗號分隔}" --prompt-only
```

- **零新計算**：只讀 Phase 1/3 已落地的 cache（valuation / smart_money / earnings_pulse
  + `fred_latest.json`），不打 API、不重算上游指標。
- stdout 就是 `<TRIGGERED_DIVERGENCE_RULES>` 的內容，**逐字 paste**，PS 不需再組字。
  去掉 `--prompt-only` 可拿完整 JSON（誰觸發、引哪個數值）供稽核。
- **rc=1 = HARD cache 缺席**（valuation / smart_money / earnings_pulse）→ 先修 Phase 1/3
  的 cache 再繼續。**不得**把 rc=1 當成「沒有觸發」跳過 —— 那會靜默關掉 DA 該發的 challenge。
- FRED 缺席不是錯誤（`fred_available=false` 是合法狀態）：R4 會標
  `available=false`，prompt block 明寫「未能判定 ≠ 未觸發」。

規則門檻（**僅供參考；script 是唯一執行者**，改門檻改 `da_pretrigger.py` 的常數區）：

| 規則 | 觸發條件（per HOT sector） | 來源 |
|---|---|---|
| **R4 FRED 衝突** | `yield_curve_inverted=true` OR `real_rate_preferred>2.0` OR `credit_stress_elevated=true` OR `financial_stress_above_avg=true` OR `regime_label ∈ {Late Cycle Tightening, Stagflation, Recession Risk, Recession Easing}` OR sector ∈ `sector_rotation_avoid` | `_phase0.fred_snapshot` |
| **R5 Smart Money divergence** | `insider_acquired_disposed_ratio_q<0.5` OR `senate_net_buy_30d<0` OR (`institutional_holders_qoq_delta<0` AND `institutional_ownership_pct_delta<0` AND `institutional_sample_size>=3`) | `_phase3.smart_money_signals` |
| **R6 PT target exhausted** | `analyst_pt_upside_median_pct<0.03` AND `pt_sample_size>=3` | `_phase3.sector_earnings_pulse` |
| **R7 動能耗盡** | `rs_vs_spy_3m>0.05` AND `rs_vs_spy_5d<0` AND `rs_vs_spy_20d<0` | `_phase1.sectors[].sector_valuation` |

> 完全沒觸發時 script 會輸出 `"(無結構性 divergence 觸發 — 專注 R1-R3 + tail-risk)"`。
> R4–R7 原文留在下方 library（spec 參考）與 script 內，**不再無條件塞進每次 prompt**。

##### R4–R7 Rule Library（觸發才 paste；each MUST 引具體數值）

- **R4 FRED 衝突**：→ MUST 構造 kill_conditions 引用**具體 FRED 數值**（"real_rate 1.92% > 2.0% threshold"），不可寫 vague「macro 轉差」。優先序：credit_stress > yield_curve_inverted > real_rate_high > yield_curve_steep。
- **R5 smart_money_divergence**：→ MUST 在 `challenge_targets` 加 **smart_money_divergence** challenge，counter_evidence 引具體數值（"insider ratio 0.41 < 0.5; senate net −3 in 30d; 13F holders QoQ −12, ownership % −0.45"）。smart money 與 consensus 一致（ratio>0.8 且 senate≥0 且 holders_qoq≥0）→ 不挑。
- **R6 pt_target_exhausted**：→ MUST 加 **pt_target_exhausted** challenge，counter_evidence 引數值（"PT median upside 1.8% < 3% across 5 mega-caps"）。
- **R7 momentum_exhaustion**：→ MUST 加 **momentum_exhaustion** challenge，counter_evidence 引數值（"3M RS +8.1% but 20d −2.3% / 5d −0.7% — short-term reversal"）。三窗口同向 → 不挑。

#### 執行方式（MUST use Agent tool）

```
Agent(
  description="Devil's Advocate sector challenge",
  subagent_type="general-purpose",
  model="sonnet",   # V3.44 — 有界挑戰任務，跑 Sonnet 省成本；Arbiter 留 Opus
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

  PHASE 3 SMART MONEY SIGNALS (V1.4，from `sector/cache/sector_smart_money_<DATE>.json`):
  <僅當 R5 觸發時 paste _phase3.smart_money_signals[hot_sector]（命中 sector）；R5 未觸發則填 "n/a">

  CONSENSUS_WARNING: <true | false>（若 true 表示該板塊在 rotation/theme/news 三方向全看多，你必須強力挑戰）

  TASK:
  1. 若 consensus_warning=true → MUST 提交 challenge_targets（不可省略）；counter_evidence ≥ 2 句含具體數據
  2. 若 consensus_warning=false → 優先挑戰 tail_risk_score 最高的 2-3 個板塊
  3. 每個 challenge_target 必須 falsifiable（IF <條件> WITHIN <天數> THEN <推翻論點>）
  4. 結構性 divergence 規則（R4–R7）— 僅處理 PS 已預先判定觸發、paste 在下方的規則：

  TRIGGERED STRUCTURAL DIVERGENCE RULES (V4.12.2 — PS 預算後只填 fired 的):
  <TRIGGERED_DIVERGENCE_RULES>

     對上方每條 fired 規則，依其指示加對應 challenge_target，counter_evidence MUST
     引具體數值。**未列在上方 = 當日未觸發，不需處理、不需自行重算 cache。**

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
→ fragility_label = FRAGILE
  → 必須將此產業加入 challenge_targets
→ tail_risk_score ≥ 60 OR excess_kurtosis > 5      # ≥ 60 = FRAGILE 帶
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
  IF (fragility_label = FRAGILE AND extreme_sentiment_triggered = true):
    → DOWNGRADE: HOT → WARM
    → risk_flags += "extreme_sentiment_fragile_combo"

  # V4.112.0：原本這裡還有一條「IF fragility_label = EXTREMELY_FRAGILE → 降級 +
  # risk_flags += fragility_downgrade」。tail-risk-analyzer 只輸出
  # ROBUST / MODERATE / FRAGILE，從來沒有 EXTREMELY_FRAGILE，該條永不觸發，已刪除。
  # 歷史上 fragility_downgrade 出現過三列（2026-04-18 XLK/XLB、04-19 XLU），
  # 而那三列的 fragility_label 分別是 FRAGILE/FRAGILE/ROBUST——沒有一個是
  # EXTREMELY_FRAGILE，證明那個 flag 一直是 DA 自行判斷貼上的，不是這條規則的產物。
  # 改以 FRAGILE 單獨觸發會「放寬」降級門檻，屬語意變更，不在本次對齊範圍。

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
    "one_liner":   string ≤ 160 chars,        // 結論 → 原因 → 行動，給人讀的盤前摘要
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
  - one_liner          → 必須像投資人盤前摘要，不得像內部規則/validator 訊息
    - 格式：先講「今天怎麼做」，再講「為什麼」，最後講「等什麼才改變」
    - 禁止輸出內部 enum / 規則語：signal_conflict、不得 AGGRESSIVE、強制 stance、STEP、Phase、validator、score 69、pp
    - 可保留必要市場術語：FTD、breadth、RSI、MA、FOMC、real rate
    - 避免把 5 個以上指標硬塞同一句；細節放 key_takeaways / watch_next
    - 中文標點需自然；避免半形分號串接多個子句
```

**JSON Schema** → 見 `schema.md` Phase 4c

---

## PHASE 5 — EMIT JSON + RENDER MARKDOWN

**Agent**: Portfolio Strategist (PS) · **無模型 — 機械步驟**

> ⚡ **V1.4.1 — 不再手寫完整 `sector_intel.json`**。PS 只寫一個**精簡 decision
> JSON**（純判斷欄位），由 `build_sector_intel.py` 從 phase cache 自動組裝出完整
> 的 intel 檔。禁止用 Write 手刻 15+ key 的巢狀 intel — 那是 turn-bloat 主因。

### Step 1 — 寫入 decision JSON

PS 把 Phase 4a/4b/4c 的**判斷結果**寫成 `sector/cache/sector_decision_<DATE>.json`
（Write 一次，~11 sector × 少數欄位 + 少數 top-level）。**只放判斷欄位** — cache
裡已有的機械資料（valuation / earnings_pulse / smart_money / breadth / ftd /
market_top / fred）**不要手抄**，build script 會自己讀。

Decision JSON 完整 schema 見 **`sector/scripts/build_sector_intel.py` 檔頭 docstring**
（authoritative）。重點欄位：

- top-level：`verdict_date` / `market_regime` / `exposure_ceiling` /
  `synthesized_exposure` / `cycle_phase` / `phase4_fanout_mode` /
  `degraded_agents` / `regime_stance` / `summary` / `today_verdict` /
  `actionable_themes` / `political_risk_summary` / `session_notes` /
  `top_catalysts`(≥5) / `political_overlay`
- `sectors[]` 每筆：`name` / `verdict` / `composite_score` / `score_components`
  (含 `valuation_penalty`) / `risk_flags` / `proxy_etf`(HOT 必填) /
  `rotation_signal` / `uptrend_ratio` / `sector_actions`

### Step 2 — Build + Validator Gate（MANDATORY）

```bash
python3 sector/scripts/build_sector_intel.py --date YYYY-MM-DD
python3 sector/scripts/validate_sector_intel.py
```

`build_sector_intel.py` 讀 decision JSON + phase cache → 組出
`sector_logs/<DATE>_sector_intel.json`（`protocol_version="V1.4"`、
`_phase4c.today_verdict` 等全自動填好）。輸出**設計上即過 validator**。

rc ≠ 0 時：build script rc≠0 → 修 decision JSON（缺欄位 / cache 沒抓到）後重跑；
validator rc≠0 → 多半是 decision JSON 的 sector 欄位缺漏，照錯誤訊息補。**不要**
手改組出來的 intel 檔。

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

> Schema 紅線：`bridge.py` 依賴 `_phase0` / `_phase1` / `_phase3` 鍵名不可改；
> `protocol_version` 由 `build_sector_intel.py` 固定填 `"V1.4"`（勿手改）。
