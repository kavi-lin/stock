# Multi-Agent Investment Protocol (V4.8)

> **V4.8 核心變更（Parallel Blind Analyst Subagents）**
> - **D**：Phase 2 四個 analyst（Fundamentals / Sentiment / News / Technical）改為 **4 個平行 subagent（Agent tool, general-purpose）**，各自封閉 context、禁止互看輸出。這是針對 V4.7 仍殘留的「一人演四角」問題的結構性修正。
> - Burry 保留 inline（純 skill 呼叫，已是 deterministic，包 subagent 無加值）。
> - Red Team (Phase 2.8) 與 V4.7 相同，仍是獨立 subagent。
> - 繼承 V4.7 全部機制：Red-Team-gated Consensus Bonus / Penalty、Phase 2.8 Red Team、Burry OVERRIDE 成本化。

## SESSION STARTUP

```
SESSION CONFIG
──────────────────────────────────────────
RISK_TOLERANCE : LOW | MEDIUM | HIGH
──────────────────────────────────────────
```

Ticker 由使用者在對話中指定。

---

## GLOBAL RULES

1. **Phase Order**: 0 → 1 → 2 → 2.5 → 2.8 → 3 → 4 → 5。不跳過。
2. **Phase 0 Cache（三層優先；FRESH = mtime < 3 小時前 / 10800s）**:
   - L1: `../sector/sector_logs/*_sector_intel.json` 最新檔 FRESH → 提取 macro，跳過 search（`phase0_source: SECTOR_CACHE`）
   - L2: `./invest_logs/*_phase0.json` 最新檔 FRESH → 載入（`INVEST_CACHE`）
   - L3: 皆 STALE 或缺失 → web search，寫入 `./invest_logs/YYYY-MM-DD_phase0.json`（`FRESHLY_EXECUTED`）
3. **Theme Cache**（FRESH = mtime < 3h）: 需主題熱度時先搜 `../skills/theme-detector/cache/theme_detector_*.json` 最新檔；FRESH → 載入；STALE 或缺失 → 執行 skill，cache 存回原路徑，MD 移至 `../reports/YYYYMMDD_theme_detector_HHMMSS.md`。
4. **Prior Session**: 讀 `./invest_logs/history.json` 最近一筆（僅供 PM 參考，**不得** pass 進 Phase 2 subagent）。
5. **Output**: 邏輯輸出 JSON；Markdown 僅用於 Final Viz Table。
6. **key_factors**: 最多 3 條，每條 ≤ 8 英文字。
7. **MD Report**（強制）: Phase 5 後存 `../reports/YYYYMMDD_TICKER.md`。不得省略。
8. **Skill 執行強制規則（NO SIMULATION）**: 凡 protocol 內標示「**MUST run**」的 skill 指令，**必須實際執行 Bash 呼叫 python3 script 並解析 JSON 輸出**，嚴禁以語言模型自行估算／模擬數值代替。受此規則約束的 skill：
   - `market-sentiment-analyzer`（Phase 2 Sentiment subagent 內）
   - `us-stock-analysis`（Phase 2 Fundamentals subagent 內）
   - `market-news-analyst`（Phase 2 News subagent 內）
   - `technical-analyst`（Phase 2 Technical subagent 內）
   - `short-contrarian-analyst`（Phase 2 inline Burry）
   - `portfolio-risk-manager`（Phase 4 Step 2）
   - `tail-risk-analyzer`（Phase 4 Step 3）
   - 若某次執行 skill script 發生錯誤，必須在 Final Report 對應欄位標記 `skill_execution_failed: true` 並記錄 stderr，禁止靜默用估算值補上。
9. **Red Team 獨立執行強制規則（V4.7）**: Phase 2.8 Red Team Adversary **必須以 Agent tool 呼叫 subagent 執行**（`subagent_type: "general-purpose"`），禁止 inline 推理代替。
10. **Parallel Analyst 強制規則（V4.8 新增 — 核心機制）**:
    - Phase 2 四個 analyst（Fundamentals / Sentiment / News / Technical）**必須**以 **4 個 Agent tool 平行呼叫**（subagent_type: "general-purpose"）執行，**並放在同一則訊息內**（確保真正平行；parent 在 4 個結果都回來前不進入 Phase 2.5）。
    - 每個 subagent 的 prompt **只能包含**：(a) ticker、(b) Phase 0 macro JSON、(c) 該 lane 的 rubric + MUST run skill 指令、(d) output schema。
    - **禁止** pass 進 subagent 的資訊：其他 analyst 的 tentative signal、prior_session 的 historical_bias、current active_weights、任何來自既有持倉 / 偏好的引導。
    - 每個 subagent 回傳的 JSON **必須包含** `subagent_isolated: true` sentinel，parent 需驗證；若缺少 → 該 analyst 視為 degraded，confidence cap 0.6。
    - Burry 不套用 D 規則（inline skill call）。
    - Red Team 仍然是 subagent，但在 Phase 2 之後、Phase 3 之前。

---

## TEAM STRUCTURE

| Agent | 執行模式（V4.8）| Skill |
|---|---|---|
| Global News Intelligence | inline（Phase 0）| `market-news-analyst` |
| **Fundamentals Analyst** | **parallel subagent** | `us-stock-analysis` |
| **Sentiment Analyst** | **parallel subagent** | `market-sentiment-analyzer` |
| **News Analyst** | **parallel subagent** | `market-news-analyst` |
| **Technical Analyst** | **parallel subagent** | `technical-analyst` |
| Contrarian Analyst (Burry) | inline（Phase 2 末）| `short-contrarian-analyst` |
| Red Team Adversary | subagent（Phase 2.8）| general-purpose |
| Trader Agent | inline（Phase 4）| — |
| Risk Manager | inline（Phase 4）| `portfolio-risk-manager`, `tail-risk-analyzer` |
| Portfolio Manager (PM) | inline（orchestrator）| — |

---

## PHASE 0 — GLOBAL NEWS INTELLIGENCE

**三層 cache（依序；FRESH = mtime < 3 小時前）**:
1. `../sector/sector_logs/*_sector_intel.json` 取最新檔，`now - mtime < 10800s` → FRESH → 提取 `market_regime`, `exposure_ceiling`, `political_risk_summary`, `actionable_themes`, `session_notes` → Phase 1
2. `./invest_logs/*_phase0.json` 取最新檔，FRESH → 載入 → Phase 1
3. 皆 STALE 或缺失 → 執行 `market-news-analyst` skill（或 web search），寫入 `./invest_logs/YYYY-MM-DD_phase0.json`

> 檢查 mtime 可用 Bash `find path -name pattern -mmin -180` 或 `stat -f %m file`；Python `os.path.getmtime()`。

```json
{
  "phase": 0,
  "agent": "Global_News_Intelligence",
  "scan_date": "YYYY-MM-DD",
  "data_source_timestamp": "YYYY-MM-DD HH:MM",
  "bullish_signals": [
    { "rank": 1, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" }
  ],
  "bearish_signals": [
    { "rank": 1, "headline": "string", "source": "string", "impact_score": "1–5", "affected_sectors": [], "reasoning": "string" }
  ],
  "macro_summary": {
    "bullish_total_impact": "sum",
    "bearish_total_impact": "sum",
    "net_score": "bull - bear",
    "macro_backdrop_score": "net_score normalized -5.0 to +5.0",
    "market_regime": "BULL | BEAR | SIDEWAYS | VOLATILE | RISK_OFF | RISK_ON",
    "regime_confidence": "0.0 to 1.0",
    "key_themes": [],
    "hot_sectors": [],
    "cold_sectors": []
  },
  "phase3_macro_multiplier": "float",
  "mandatory_risk_flags": [],
  "binary_risks": []
}
```

**macro_multiplier 查表**:

| macro_backdrop_score | multiplier |
|---|---|
| ≥ +3 | 1.2 |
| +1 to +3 | 1.0 |
| -1 to +1 | 0.9 |
| -3 to -1 | 0.75 |
| < -3 | 0.6 |

---

## PHASE 1 — CONTEXT & MEMORY REVIEW

**Agent**: PM（inline）

```json
{
  "phase": 1,
  "agent": "Portfolio_Manager",
  "phase0_source": "SECTOR_CACHE | INVEST_CACHE | FRESHLY_EXECUTED",
  "prior_session_loaded": "true | false",
  "last_outcome": "WIN | LOSS | UNKNOWN",
  "historical_bias": "string (PM 自用，不得傳入 Phase 2 subagent)",
  "adjustment_strategy": "string",
  "current_market_regime": "from Phase 0",
  "active_weights": {
    "Fundamentals": 0.30,
    "Sentiment": 0.20,
    "News": 0.20,
    "Technical": 0.30
  }
}
```

> **V4.8 契約**：`historical_bias`、`adjustment_strategy`、`active_weights` 屬於 PM 層 state，**不得傳入** Phase 2 subagent prompt。Phase 2 subagent 的 score 必須完全獨立於這些歷史偏好。

Contrarian (Burry) 不參與加權，僅作 T4 veto check。

---

## PHASE 2 — PARALLEL BLIND ANALYST FAN-OUT (V4.8 核心)

**執行模式**：PM 以**單一訊息**平行呼叫 4 個 Agent subagent（Fundamentals / Sentiment / News / Technical），等待全部 4 個結果回傳後再進入 Phase 2 末段（Burry inline）與 Phase 2.5。

### 共通 Subagent Prompt 模板

每個 subagent 收到以下結構化 prompt（只替換 `<LANE>` / `<RUBRIC_LANE>` / `<SKILL_CMD>`）：

```
You are the <LANE> analyst for ticker <TICKER>.

ISOLATION CONTRACT:
  - 你與其他 3 個 analyst 以獨立 context 平行執行。
  - 你看不到其他 analyst 的 score / signal / reasoning。
  - 禁止推測其他 lane 的結論。
  - 禁止為了「與共識一致」調整自己的 score。
  - 禁止考慮 PM 的 historical_bias / active_weights / prior session。
  - score -5..+5 僅依據你本 lane 收集的證據。

TICKER: <TICKER>

PHASE 0 MACRO CONTEXT (read-only, shared across all analysts):
<paste Phase 0 macro_summary JSON>

YOUR LANE RUBRIC:
<RUBRIC_LANE>

MANDATORY DATA COLLECTION:
<SKILL_CMD — MUST run, do NOT simulate>

OUTPUT (strict JSON, no prose):
{
  "phase": 2,
  "agent": "<LANE>_Analyst",
  "ticker": "<TICKER>",
  "signal": "BUY | SELL | HOLD",
  "score": "-5 to +5",
  "confidence": "0.0 to 1.0",
  "key_factors": ["max 8 words each", "max 3 items"],
  "risk_flags": ["max 2 items"],
  "phase0_alignment": "ALIGNED | MISALIGNED | NEUTRAL",
  "data_source_timestamp": "YYYY-MM-DD HH:MM",
  "subagent_isolated": true,
  "skill_execution_failed": "true | false"
}
```

### 四個 Lane 的 Rubric + Skill 指令

#### Fundamentals Subagent
- **RUBRIC**: P/E vs sector median, revenue YoY, FCF margin, debt-to-equity, next earnings date, analyst consensus EPS growth。強訊號（e.g. FCF yield > 5% AND rev_growth > 20%）給 +3 或 +4；避免自我審查向中間靠攏。
- **SKILL**:
  ```bash
  python3 skills/us-stock-analysis/scripts/analyze.py <TICKER> --json-only
  ```

#### Sentiment Subagent
- **RUBRIC**:
  - 市場層：優先從 Phase 0 macro 的 `fear_greed_status`；若無，MUST run：
    ```bash
    python3 skills/market-sentiment-analyzer/scripts/sentiment.py --json-only
    ```
    取回 `composite_score`（0–100）、`vix.current`、`spy_momentum.rsi_14`、`extreme_sentiment_triggered`
    > **V4.8 自動 cache（TTL 900s / 15 min）**：市場層是 ticker-agnostic，連續分析多個 ticker 時第 2+ 個 Sentiment subagent 會拿到 cache hit（JSON 輸出含 `cache_hit: true` + `cache_age_sec`），跳過 yfinance 下載，節省約 $0.1/ticker。若需即時值可改呼叫 `sentiment.py --json-only --no-cache`。
  - 個股層：web search Reddit/X、short interest、insider activity
  - 融合公式：`Sentiment Score = 0.4 × stock_specific + 0.6 × (market_composite/10 − 5)`
- **額外輸出欄位**：`market_sentiment_composite`, `vix_current`

#### News Subagent
- **RUBRIC**: 過去 48h company news + analyst rating changes + cross-ref Phase 0 macro themes。重大 upgrade / downgrade / 8-K / 併購傳聞明顯偏向。
- **SKILL**:
  ```bash
  python3 skills/market-news-analyst/scripts/fetch.py <TICKER> --hours 48 --json-only
  ```
  或若 `sector_intel.json.top_catalysts` 涵蓋該票則直接引用。

#### Technical Subagent
- **RUBRIC**: 20/50/200MA 結構、RSI(14)、MACD histogram、volume vs 20D avg、最近 support/resistance。完整 stage 2 上升結構（20>50>200，RSI 40-70，量放大）給 +3 以上；下降結構（跌破 200MA + 量放大）給 -3 以下。
- **SKILL**（若有週線圖）:
  ```bash
  python3 skills/technical-analyst/scripts/analyze.py <TICKER> --json-only
  ```
  若無圖表輸入，subagent 可從 yfinance 自行拉週線後計算。

### Fan-Out 執行（PM 層）

PM 必須在**同一則訊息**中發出 4 個 Agent tool call（以確保 runtime 真正平行）。示意：

```
[single assistant turn, 4 tool_use blocks in parallel]
  Agent(description="Fundamentals analyst", subagent_type="general-purpose", prompt="<fund prompt>")
  Agent(description="Sentiment analyst",    subagent_type="general-purpose", prompt="<sent prompt>")
  Agent(description="News analyst",         subagent_type="general-purpose", prompt="<news prompt>")
  Agent(description="Technical analyst",    subagent_type="general-purpose", prompt="<tech prompt>")
```

### Fan-In 驗證（PM 層）

收到 4 個 JSON 後，PM 逐一驗證：
1. `subagent_isolated == true` → 若 false / 缺失 → confidence cap 0.6 + `subagent_validation_failed: true`
2. JSON schema 符合 → 若 malformed → retry 一次；再失敗 → 降為 inline fallback（見下節）
3. 寫入 `phase2_fanout_summary`：

```json
{
  "phase2_fanout_summary": {
    "mode": "PARALLEL_SUBAGENT | PARTIAL_FALLBACK | FULL_FALLBACK",
    "subagent_successes": 4,
    "subagent_failures": 0,
    "degraded_analysts": [],
    "fanout_started_at": "ISO-8601",
    "fanout_completed_at": "ISO-8601"
  }
}
```

### Inline Fallback 策略

| 情境 | 處理 |
|---|---|
| 單一 subagent timeout / tool error | retry 1 次；仍失敗 → PM inline 執行該 lane；標記 `subagent_execution_failed: true`，confidence cap 0.6 |
| 單一 subagent 回傳 malformed JSON | 同上 |
| 2-3 個 subagent 失敗 | 全部失敗者 inline fallback；session 標記 `phase2_fanout_summary.mode = "PARTIAL_FALLBACK"` |
| 4 個全部失敗 | session `mode = "FULL_FALLBACK"` + `degraded_mode: true`；**Red Team 強制視為 STRONG_COUNTER**（不信任 Phase 2 輸出）;  Final Report 首段必須顯示警告 |

---

## PHASE 2 末段 — CONTRARIAN (BURRY, inline)

**Agent**: Contrarian Analyst (Burry) — inline，不使用 subagent

執行在 Fan-In 完成後；Burry 是 deterministic skill output，不受 anchoring 影響，因此維持 inline。

**MUST run**（不得以估算代替）：

```bash
python3 skills/short-contrarian-analyst/scripts/burry_score.py <TICKER> --json-only
```

取回 `burry_score`（0–100）、`verdict`（T4_VETO / WARNING / NEUTRAL / VALUE_BONUS）、`components`。

**Verdict → Phase 4 影響**：
- `T4_VETO` (score < 20) → 強制 HOLD，Phase 4 不執行倉位計算
- `WARNING` (20 ≤ score < 35) → Phase 4 final × 0.7
- `NEUTRAL` (35 ≤ score < 60) → 無調整
- `VALUE_BONUS` (score ≥ 60) → Phase 4 final × 1.15

```json
{
  "phase": 2,
  "agent": "Contrarian_Analyst_Burry",
  "ticker": "STRING",
  "burry_score": "0–12",
  "burry_signal": "STRONGLY BULLISH | BULLISH | NEUTRAL | BEARISH | STRONGLY BEARISH",
  "value_analysis": {
    "fcf_yield_pct": "float",
    "ev_ebit_multiple": "float",
    "value_pts": "0–6"
  },
  "balance_sheet": {
    "debt_to_equity": "float",
    "net_cash_positive": "true | false",
    "balance_pts": "0–3"
  },
  "insider_activity": {
    "net_activity": "BUYING | NEUTRAL | SELLING",
    "insider_pts": "0–2"
  },
  "contrarian_sentiment": {
    "news_tone": "NEGATIVE | MIXED | POSITIVE",
    "contrarian_pts": "0–1"
  },
  "burry_voice": "string",
  "veto_flag": "true if burry_score <= 2",
  "phase0_alignment": "ALIGNED | MISALIGNED | NEUTRAL",
  "data_source_timestamp": "YYYY-MM-DD HH:MM"
}
```

`veto_flag = true` → 觸發 Phase 2.5 T4。

---

## PHASE 2.5 — CONFLICT & BIAS PROTOCOL

**Agent**: PM（inline）

**觸發條件**:
- **T1**: `Sentiment.score > +3` AND `Fundamentals.score < 0`
- **T2**: `News.score < -3` AND `Technical.signal = BUY`
- **T3**: `macro_backdrop_score < -3` AND any `signal = BUY` with `score > +3`
- **T4**: `Contrarian.veto_flag = true` AND `tentative_decision = BUY`
- **Anti-Bias**: 所有 analyst 信號同向 → News 追加 `devils_advocate: [...]`（最多 3 條）
  > V4.7 起真正的異議 gate 由 Phase 2.8 Red Team 執行；V4.8 起 Phase 2 獨立性大幅提高，若 fan-out 成功執行、4 analyst 仍同向，則該共識的信度顯著高於 V4.7 — 但仍需經 Red Team 驗證。

```json
{
  "phase": "2.5",
  "agent": "Portfolio_Manager",
  "triggers_fired": ["T1", "T4"],
  "conflict_summary": "one sentence per trigger",
  "t4_detail": {
    "burry_score": "float",
    "burry_concern": "string",
    "resolution": "OVERRIDE_BURRY | DOWNGRADE_DECISION | CANCEL",
    "override_justification": "required if OVERRIDE_BURRY; ≥ 20 字具體凌駕理由；須具體引用 Phase 2 某 analyst 的某項證據；泛泛之言視為無效",
    "override_recheck_date": "YYYY-MM-DD (trade_date + 5 trading days) if OVERRIDE_BURRY else null"
  },
  "resolution": "string",
  "phase0_macro_flag": "OVERRIDE_ACTIVE | NONE",
  "proceed_to_phase3": "true | false"
}
```

**T4 仲裁（V4.7 強化，V4.8 沿用）**:
- `burry_score 0–1` → 強烈建議 `CANCEL`
- `burry_score = 2` → `DOWNGRADE_DECISION`（BUY → HOLD）或 `OVERRIDE_BURRY`
- **若選 `OVERRIDE_BURRY`，自動啟動以下三項成本**：
  1. Phase 4 倉位 × 0.5（`burry_override_multiplier`）
  2. 必填 `override_justification`（≥ 20 字，具體引用 Phase 2 某 analyst 的某項證據）
  3. 自動計算 `override_recheck_date` = 交易日 + 5 個交易日

`proceed_to_phase3 = false` → 跳 Phase 5 輸出 `CANCEL`。

---

## PHASE 2.8 — RED TEAM ADVERSARIAL CHECK

**Agent**: Red_Team_Adversary（以 Agent tool 呼叫 subagent 執行，**禁止 inline 推理代替**）

**觸發條件**: 始終執行（除非 Phase 2.5 `proceed_to_phase3 = false`）。

**V4.8 特別規則**：若 `phase2_fanout_summary.mode = "FULL_FALLBACK"`（4 analyst 全 fallback inline），Red Team 自動標記 `red_team_verdict = STRONG_COUNTER`，跳過 subagent 呼叫（Phase 2 輸出本身已不可信任）。

### 執行方式

```
Agent(
  description="Red Team counter-thesis",
  subagent_type="general-purpose",
  prompt="""
  You are the RED TEAM. Your sole job: argue against the tentative consensus and try to prove it wrong.

  TICKER: <TICKER>
  TENTATIVE CONSENSUS DIRECTION: <BULLISH | BEARISH | MIXED>

  PHASE 0 MACRO:
  <paste macro_summary from Phase 0>

  PHASE 2 ANALYST OUTPUTS (5 agents including Burry):
  <paste all 5 analyst JSONs>

  TASK:
  1. 不要客氣、不要持平 — 你的任務是破壞共識。
  2. 找出共識最脆弱的 1 個主論點，寫成 `counter_thesis`（1-2 句）。
  3. 產出 2-3 條 falsifiable kill_conditions：「IF <事件> WITHIN <天數> THEN <推翻論點>」。
     無效範例（不可驗證）：「IF 市場反轉」「IF 利空」
  4. 評 counter_evidence_strength（1-5 整數）：
     - 1-2 = 找不到有力反論
     - 3 = 有值得警惕的風險但無確切反證
     - 4-5 = 有具體數據/事件強烈反駁
  5. verdict 對照：
     - strength ≤ 2 → NO_VIABLE_COUNTER
     - strength = 3 → MODERATE_COUNTER
     - strength ≥ 4 → STRONG_COUNTER

  OUTPUT: 單一 JSON object，schema 見 protocol Phase 2.8。
  """
)
```

### 輸出 JSON

```json
{
  "phase": "2.8",
  "agent": "Red_Team_Adversary",
  "ticker": "STRING",
  "tentative_consensus_direction": "BULLISH | BEARISH | MIXED",
  "counter_thesis": "string — 共識最脆弱的 1 個主論點，1-2 句",
  "kill_conditions": [
    "IF <具體事件> WITHIN <具體時間窗> THEN <被推翻的具體論點>",
    "..."
  ],
  "counter_evidence_strength": "1–5 integer",
  "red_team_verdict": "NO_VIABLE_COUNTER | MODERATE_COUNTER | STRONG_COUNTER",
  "subagent_isolated": "true (verifies call was via Agent tool, not inline)",
  "data_source_timestamp": "YYYY-MM-DD HH:MM"
}
```

### Phase 3 影響對照

| red_team_verdict | Phase 3 Step 2 |
|---|---|
| `NO_VIABLE_COUNTER` | consensus bonus × 1.15 可觸發（若 4 analyst 同向且 Burry 未 veto） |
| `MODERATE_COUNTER` | 無 bonus 無 penalty |
| `STRONG_COUNTER` | raw_total × 0.85 penalty，bonus 被禁用 |

### 失敗處理

Red Team subagent 失敗（timeout / tool error / JSON parse error）→ `red_team_execution_failed: true`，`red_team_verdict` 固定為 `MODERATE_COUNTER`。

---

## PHASE 3 — DECISION ENGINE

**Agent**: PM（inline）

**計算步驟**:

```
Step 1 (Raw):
  raw_total = Σ(Weight_i × Score_i × Confidence_i)

Step 2 (Red-Team-Gated Bonus/Penalty):
  IF all 4 signals same direction
     AND Burry.veto_flag = false
     AND red_team_verdict = "NO_VIABLE_COUNTER":
    raw_after_bonus = raw_total × 1.15
  ELIF red_team_verdict = "STRONG_COUNTER":
    raw_after_bonus = raw_total × 0.85
  ELSE:
    raw_after_bonus = raw_total

Step 3 (Directional Macro Multiplier):
  IF sign(raw_after_bonus) == sign(macro_backdrop_score):
    final_score = raw_after_bonus × macro_multiplier
    macro_alignment = "ALIGNED"
  ELSE:
    final_score = raw_after_bonus
    macro_alignment = "CONTRARIAN"
```

Contrarian Analyst 不納入 Step 1 加權。VOLATILE regime 不在 Phase 3 重複扣分（已計入 `macro_backdrop_score`）。

**決策閾值**:

| final_score | decision |
|---|---|
| ≥ +1.2 | BUY |
| +0.8 ~ +1.2 | STAGED_ENTRY |
| −0.8 ~ +0.8 | HOLD |
| −1.2 ~ −0.8 | STAGED_EXIT |
| ≤ −1.2 | SELL |

**Auto REJECT**（僅下列情況）:
- `risk_reward_ratio < 2.0`
- `proceed_to_phase3 = false`
- Unknown/negative binary risk 事件 < 48h
- `mandatory_risk_flags` 含系統性事件
- **V4.8 新增**：`phase2_fanout_summary.mode = "FULL_FALLBACK"` AND `final_decision ∈ {BUY, STAGED_ENTRY}` → 強制降為 HOLD（不信任 degraded 模式下的看多共識）

```json
{
  "phase": 3,
  "agent": "Portfolio_Manager",
  "ticker": "STRING",
  "calculation_steps": {
    "fund": "0.30 × [score] × [conf] = [result]",
    "sent": "0.20 × [score] × [conf] = [result]",
    "news": "0.20 × [score] × [conf] = [result]",
    "tech": "0.30 × [score] × [conf] = [result]",
    "raw_total": "float",
    "red_team_verdict": "NO_VIABLE_COUNTER | MODERATE_COUNTER | STRONG_COUNTER",
    "bonus_applied": "true | false",
    "penalty_applied": "true | false",
    "raw_after_bonus": "float",
    "macro_multiplier": "float from Phase 0",
    "macro_alignment": "ALIGNED | CONTRARIAN",
    "final_score": "float"
  },
  "avg_confidence": "float",
  "final_decision": "BUY | STAGED_ENTRY | HOLD | STAGED_EXIT | SELL",
  "decision_margin": "e.g. STAGED_ENTRY by 0.3 margin above HOLD",
  "contrarian_note": "Burry Score [X/12] — [brief implication]",
  "red_team_note": "counter_thesis + 主要 kill condition（1 句）",
  "fanout_mode": "PARALLEL_SUBAGENT | PARTIAL_FALLBACK | FULL_FALLBACK"
}
```

---

## PHASE 4 — EXECUTION & RISK MANAGEMENT

**Agents**: Trader Agent + Risk Manager（皆 inline）

### Step 1 — Dual-Track Trade Plan（Trader Agent）

**雙軌進場規則**:
- `entry_aggressive`: 當前震盪區，立即 / 市價
- `entry_conservative`: 技術反轉確認 / 財報後 / 關鍵均線突破
- **BUY** 決策 → 兩軌二選一（預設 aggressive）
- **STAGED_ENTRY** 決策 → 兩軌各佔 50% 倉位

```json
{
  "phase": 4,
  "ticker": "STRING",
  "trade_plan": {
    "entry_aggressive": {
      "range": ["min_price", "max_price"],
      "trigger": "LIMIT | MARKET | BREAKOUT",
      "trigger_conditions": "string"
    },
    "entry_conservative": {
      "range": ["min_price", "max_price"],
      "trigger_conditions": "string"
    },
    "take_profit": "price",
    "stop_loss": "price",
    "risk_reward_ratio": "float — must be >= 2.0",
    "time_horizon": "short | mid | long",
    "exit_conditions": "string"
  }
}
```

### Step 2 — Vol-Adjusted Position Sizing（Risk Manager）

**MUST run**:

```bash
python3 skills/portfolio-risk-manager/scripts/risk_manager.py <TICKER> --json-only
```

取回 `raw_vol_adjusted_cap_pct` / `correlation_multiplier` / `sector_cap_triggered` / `final_position_cap_pct`（直接作為 `vol_adjusted_limit_pct`）。

### Step 3 — Tail Risk Assessment（Risk Manager）

**MUST run**:

```bash
python3 skills/tail-risk-analyzer/scripts/tail_risk.py <TICKER> --json-only
```

取回 `fragility_label` + `position_multiplier`：

| fragility_label | tail_risk_score | position_multiplier |
|---|---|---|
| ROBUST | < 30 | × 1.0 |
| MODERATE | 30–60 | × 0.75 |
| FRAGILE | ≥ 60 | × 0.5 |

### Step 4 — Risk Audit & Final Sizing

```
base         = vol_adjusted_limit（若 Step 2 執行）或 0.05
tail_adj     = base × fragility_multiplier
macro_cap    = min(tail_adj, 0.03) if macro_backdrop_score < -3 else tail_adj
binary_adj   = macro_cap × 0.5–0.7  (if binary_classification in [unknown, negative] AND event < 48h)
             = macro_cap            (otherwise)

# Burry Override 倉位成本（V4.7）
burry_override_adj = binary_adj × 0.5  if phase2_5.t4_detail.resolution == "OVERRIDE_BURRY"
                   = binary_adj        otherwise

IF final_decision = STAGED_ENTRY:
  final_position_size = burry_override_adj × 0.5
ELSE:
  final_position_size = burry_override_adj
```

**Binary risk 分類**:
- `positive` — 歷史 beat 率 ≥ 70% 的 earnings → 不減倉
- `unknown` — FOMC / 地緣事件 → 僅 48h 內減倉
- `negative` — 已知壞消息 → 減倉 50%

```json
{
  "phase": 4,
  "risk_audit": {
    "risk_level": "LOW | MEDIUM | HIGH",
    "volatility_flag": "true if regime = VOLATILE or RISK_OFF",
    "max_drawdown_allowed_pct": 0.02,
    "vol_adjusted_limit_pct": "float | null",
    "correlation_multiplier": "float | null",
    "position_size_method": "VOL_ADJUSTED | RULE_BASED",
    "tail_risk": {
      "fragility_label": "ROBUST | MODERATE | FRAGILE",
      "tail_risk_score": "float 0–100",
      "fragility_adjustment": "× 1.0 | × 0.75 | × 0.5",
      "key_tail_flags": []
    },
    "binary_classification": "positive | unknown | negative | none",
    "burry_override_active": "true | false",
    "burry_override_multiplier": "0.5 | 1.0",
    "position_size_pct": "final float 0.00–0.10",
    "staged_entry_split": {
      "aggressive_pct": "float | null",
      "conservative_pct": "float | null"
    },
    "approval": "APPROVED | REJECTED",
    "rejection_reason": "string if REJECTED"
  }
}
```

---

## PHASE 5 — SESSION EXPORT

**Agent**: PM（inline）

執行步驟：
1. Append session export JSON 至 `./invest_logs/history.json`
2. 確認 `./invest_logs/YYYY-MM-DD_phase0.json` 已存在
3. **MD 報告撰寫委派 Sonnet subagent（V4.8 成本優化）**：將完整 Phase 0–4 決策資料傳入 Sonnet subagent，由其**純粹排版**產出 `../reports/YYYYMMDD_TICKER.md`。Subagent 不得重新評分、不得改變任何 score / signal / decision / position_size。這是純格式化任務，節省 ~$0.5/次的 Opus 輸出成本。

### Phase 5 Step 3 — Sonnet MD Report Formatter（MUST use Agent tool）

```
Agent(
  description="Session MD report formatter",
  subagent_type="general-purpose",
  model="sonnet",
  prompt="""
  You are a MARKDOWN FORMATTER — not an analyst.

  HARD CONSTRAINTS:
    - 不得重新評分、改變 signal、改變 final_decision、改變 position_size、改變 entry/TP/SL 數字。
    - 不得新增你自己的判斷或觀點。
    - 只能將已有資料重新排版成易讀的 Markdown。
    - 若資料有缺漏，填「N/A」而非自行補全。

  TICKER: <TICKER>
  DATE: <YYYY-MM-DD>

  PHASE 0-4 COMPLETE JSON:
  <paste phase0_macro_snapshot, phase2 all 5 analyst outputs, phase2.5, phase2.8 red team, phase3 calculation_steps, phase4 trade_plan + risk_audit, phase5 trades_this_session[0]>

  FINAL VIZ TABLE TEMPLATE（從 protocol 複製）:
  <paste the Final Viz Table markdown from v4_8 protocol section>

  OUTPUT: 純 Markdown 內容（不含 code fence），結構：
    1. 標題：`# YYYY-MM-DD TICKER — 投資委員會分析`
    2. 決議摘要：Final decision、final_score、position_size
    3. Phase 0 Macro Context（1 段）
    4. Final Visualization Table（填入實際值）
    5. 五大 Agent + Burry + Red Team 詳細評分（key_factors / risk_flags）
    6. Red Team Counter Thesis + Kill Conditions
    7. 雙軌進場計畫 + R/R + position_size
    8. 關鍵風險
    9. Watch / re-eval 觸發條件

  直接寫入 `../reports/<YYYYMMDD>_<TICKER>.md`（絕對路徑或相對於 protocol 執行目錄）。完成後回傳檔案路徑。
  """
)
```

> **成本取捨**：格式化任務從 Opus（$75/M output）移至 Sonnet 4.6（$15/M output）— 假設 MD 約 5-10k tokens，**每次節省約 $0.4-0.7**。排版品質夠用（Sonnet 4.6 格式化能力等同 Opus），但決策內容零改變。若 subagent 偏離 hard constraints（例如擅自改 score），PM 必須 reject 並 retry 一次；再失敗則 PM 自行 inline 寫 MD（fallback）。

> **Schema 契約**：單一事實來源 = `trades_this_session[0]`。所有 Dashboard / bridge.py 需要的欄位（含 `watch_conditions`、`key_risks`、`devils_advocate_filed`、`red_team_verdict`、`burry_override_active`、**`phase2_fanout_mode`**）必須寫入該物件。頂層 `ticker` / `final_action` 需與 `trades_this_session[0]` 同步。

```json
{
  "session_export_version": "V4.8",
  "export_date": "YYYY-MM-DD",
  "phase0_file": "./invest_logs/YYYY-MM-DD_phase0.json",
  "phase0_macro_snapshot": {
    "market_regime": "string",
    "macro_backdrop_score": "float",
    "key_themes": [],
    "macro_multiplier": "float"
  },
  "phase2_fanout_summary": {
    "mode": "PARALLEL_SUBAGENT | PARTIAL_FALLBACK | FULL_FALLBACK",
    "subagent_successes": 4,
    "subagent_failures": 0,
    "degraded_analysts": [],
    "fanout_started_at": "ISO-8601",
    "fanout_completed_at": "ISO-8601"
  },
  "trades_this_session": [
    {
      "ticker": "STRING",
      "final_action": "EXECUTE | STAGED | CANCEL",
      "final_score": "float",
      "final_decision": "BUY | STAGED_ENTRY | HOLD | STAGED_EXIT | SELL",
      "consensus_bonus_applied": "true | false",
      "red_team_verdict": "NO_VIABLE_COUNTER | MODERATE_COUNTER | STRONG_COUNTER",
      "red_team_counter_thesis": "string",
      "red_team_kill_conditions": ["string", "..."],
      "red_team_execution_failed": "true | false",
      "phase2_fanout_mode": "PARALLEL_SUBAGENT | PARTIAL_FALLBACK | FULL_FALLBACK",
      "degraded_analysts": ["Fundamentals | Sentiment | News | Technical | ..."],
      "macro_alignment": "ALIGNED | CONTRARIAN",
      "avg_confidence": "float",
      "burry_score": "float",
      "burry_override_active": "true | false",
      "burry_override_recheck_date": "YYYY-MM-DD | null",
      "entry_aggressive": ["min", "max"],
      "entry_conservative": ["min", "max"],
      "take_profit": "float",
      "stop_loss": "float",
      "risk_reward_ratio": "float",
      "position_size_pct": "float",
      "staged_split": { "aggressive_pct": "float|null", "conservative_pct": "float|null" },
      "position_size_method": "VOL_ADJUSTED | RULE_BASED",
      "fragility_label": "string",
      "binary_classification": "positive | unknown | negative | none",
      "time_horizon": "short | mid | long",
      "macro_context": "string",
      "watch_conditions": { "trigger_name": "description", "...": "..." },
      "key_risks": ["tag_snake_case", "..."],
      "devils_advocate_filed": "true | false",
      "trade_metadata": {
        "trade_type": "event | trend | mean_reversion",
        "event_tag": "FOMC | earnings | tariff | ceasefire | optional"
      }
    }
  ],
  "active_weights_end_of_session": {
    "Fundamentals": 0.30,
    "Sentiment": 0.20,
    "News": 0.20,
    "Technical": 0.30
  },
  "bias_notes": "string",
  "last_outcome": "WIN | LOSS | UNKNOWN"
}
```

---

## PHASE 6 — CONTINUOUS LEARNING

**Trigger**: `TRADE_RESULT: ticker=XXX result=WIN|LOSS`
**Agent**: PM（inline）

```json
{
  "phase": 6,
  "ticker": "STRING",
  "outcome": "WIN | LOSS",
  "primary_failure_agent": "Fundamentals | Sentiment | News | Technical | Contrarian | Red_Team | Risk_Manager | timing | macro_model",
  "what_was_missed": "string",
  "contributing_factors": [],
  "burry_was_right": "true | false | N/A",
  "red_team_was_right": "true | false | N/A",
  "fanout_mode_at_entry": "PARALLEL_SUBAGENT | PARTIAL_FALLBACK | FULL_FALLBACK",
  "weight_adjustment_delta": {
    "Fundamentals": "-0.05 to +0.05",
    "Sentiment": "-0.05 to +0.05",
    "News": "-0.05 to +0.05",
    "Technical": "-0.05 to +0.05"
  },
  "updated_weights_for_next_session": {
    "Fundamentals": "current + delta",
    "Sentiment": "current + delta",
    "News": "current + delta",
    "Technical": "current + delta"
  },
  "lesson_learned": "string",
  "instruction": "寫入 history.json 最新一筆的 active_weights_end_of_session"
}
```

**Weight 限制**: 單一 agent 0.10–0.50；每次調整 ±0.05；總和 = 1.0。

---

## FINAL VISUALIZATION TABLE

```
| Agent              | Signal | Score | Confidence | Key Factors (top 2) | Phase 0 Alignment | Isolated |
|--------------------|--------|-------|------------|---------------------|-------------------|----------|
| Fundamentals       |        |       |            |                     |                   |   Y/N    |
| Sentiment          |        |       |            |                     |                   |   Y/N    |
| News               |        |       |            |                     |                   |   Y/N    |
| Technical          |        |       |            |                     |                   |   Y/N    |
| Contrarian (Burry) |   —    | X/12  |     —      |                     |                   |    —     |
| Red Team (V4.7)    | verdict|strength|    —      | kill_condition #1   |        —          |    Y     |

| RESULT | Decision        | Raw | RT Gate       | ×Macro | Final | Burry | Override | Pos% | Fragility | Fanout           | Action                |
|--------|-----------------|-----|---------------|--------|-------|-------|----------|------|-----------|------------------|-----------------------|
|        | BUY/STAGED/HOLD |  f  | ×1.15/—/×0.85 | ×f/—   |   f   | X/12  |  Y/N ×0.5|   %  | ROBUST    | PARALLEL/FALLBACK| EXECUTE/STAGED/CANCEL |

| Entry Track       | Range        | Trigger Conditions                      |
|-------------------|--------------|-----------------------------------------|
| Aggressive (50%)  | $min – $max  | 立即 / 當前震盪區 / 破前高               |
| Conservative (50%)| $min – $max  | 技術反轉確認 / 財報後 / RSI>50 / 站上MA  |

| Red Team Kill Conditions                                 |
|----------------------------------------------------------|
| 1. IF <事件> WITHIN <天數> THEN <推翻論點>                 |
| 2. ...                                                   |
```
