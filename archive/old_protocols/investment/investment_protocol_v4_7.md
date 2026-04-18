# Multi-Agent Investment Protocol (V4.7)

> **V4.7 核心變更（Anti-Self-Deception Patch）**
> - **A**：Consensus Bonus 改為 Red-Team-gated；同時新增 STRONG_COUNTER 情境下的 ×0.85 penalty。
> - **B**：新增 **Phase 2.8 Red Team Adversary**，以 subagent 獨立呼叫（禁止 inline 推理代替），輸出 falsifiable kill conditions。
> - **C**：Phase 2.5 T4 `OVERRIDE_BURRY` 強制成本化 — 倉位 × 0.5、+5 交易日 `override_recheck_date`、必須提供 ≥ 20 字具體凌駕理由。

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

1. **Phase Order**: 0 → 1 → 2 → 2.5 → **2.8** → 3 → 4 → 5。不跳過。
2. **Phase 0 Cache（三層優先；FRESH = mtime < 3 小時前 / 10800s）**:
   - L1: `../sector/sector_logs/*_sector_intel.json` 最新檔 FRESH → 提取 macro，跳過 search（`phase0_source: SECTOR_CACHE`）
   - L2: `./invest_logs/*_phase0.json` 最新檔 FRESH → 載入（`INVEST_CACHE`）
   - L3: 皆 STALE 或缺失 → web search，寫入 `./invest_logs/YYYY-MM-DD_phase0.json`（`FRESHLY_EXECUTED`）
3. **Theme Cache**（FRESH = mtime < 3h）: 需主題熱度時先搜 `../skills/theme-detector/cache/theme_detector_*.json` 最新檔；FRESH → 載入；STALE 或缺失 → 執行 skill，cache 存回原路徑，MD 移至 `../reports/YYYYMMDD_theme_detector_HHMMSS.md`。
4. **Prior Session**: 讀 `./invest_logs/history.json` 最近一筆。
5. **Output**: 邏輯輸出 JSON；Markdown 僅用於 Final Viz Table。
6. **key_factors**: 最多 3 條，每條 ≤ 8 英文字。
7. **MD Report**（強制）: Phase 5 後存 `../reports/YYYYMMDD_TICKER.md`。不得省略。
8. **Skill 執行強制規則（NO SIMULATION）**: 凡 protocol 內標示「**MUST run**」的 skill 指令，**必須實際執行 Bash 呼叫 python3 script 並解析 JSON 輸出**，嚴禁以語言模型自行估算／模擬數值代替。受此規則約束的 skill：
   - `market-sentiment-analyzer`（Phase 2 Sentiment Agent）
   - `short-contrarian-analyst`（Phase 2 Contrarian Agent — Burry）
   - `portfolio-risk-manager`（Phase 4 Step 2）
   - `tail-risk-analyzer`（Phase 4 Step 3）
   - 若某次執行 skill script 發生錯誤（例如 yfinance 暫時無法存取），必須在 Final Report 對應欄位標記 `skill_execution_failed: true` 並記錄 stderr，禁止靜默用估算值補上。
9. **Red Team 獨立執行強制規則（V4.7 新增）**: Phase 2.8 Red Team Adversary **必須以 Agent tool 呼叫 subagent 執行**（`subagent_type: "general-purpose"`），禁止 inline 推理代替。目的：切斷與 Phase 2 analyst 的 context 共享，避免同一 model 自己反駁自己的偽獨立性。若 subagent 執行失敗，Final Report 標記 `red_team_execution_failed: true` 並將 `red_team_verdict` 固定為 `MODERATE_COUNTER`（保守處理 — 不給 bonus 也不給 penalty）。

---

## TEAM STRUCTURE

| Agent | Skill |
|---|---|
| Global News Intelligence | `market-news-analyst` |
| Fundamentals Analyst | `us-stock-analysis` |
| Sentiment Analyst | `market-sentiment-analyzer` |
| News Analyst | `market-news-analyst` |
| Technical Analyst | `technical-analyst` |
| Contrarian Analyst (Burry) | `short-contrarian-analyst` |
| **Red Team Adversary (V4.7)** | **subagent (general-purpose)** |
| Trader Agent | — |
| Risk Manager | `portfolio-risk-manager`, `tail-risk-analyzer` |
| Portfolio Manager (PM) | — |

---

## PHASE 0 — GLOBAL NEWS INTELLIGENCE

**三層 cache（依序；FRESH = mtime < 3 小時前）**:
1. `../sector/sector_logs/*_sector_intel.json` 取最新檔，`now - mtime < 10800s` → FRESH → 提取 `market_regime`, `exposure_ceiling`, `political_risk_summary`, `actionable_themes`, `session_notes` → Phase 1
2. `./invest_logs/*_phase0.json` 取最新檔，FRESH → 載入 → Phase 1
3. 皆 STALE 或缺失 → 執行 `market-news-analyst` skill（或 web search: "global stock market news today" / "Fed interest rate outlook today" / "geopolitical risk markets today" / "S&P 500 outlook today" / "sector rotation news today"），寫入 `./invest_logs/YYYY-MM-DD_phase0.json`

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

> bullish_signals / bearish_signals 各輸出 rank 1–5（共 10 條）。

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

**Agent**: PM

```json
{
  "phase": 1,
  "agent": "Portfolio_Manager",
  "phase0_source": "SECTOR_CACHE | INVEST_CACHE | FRESHLY_EXECUTED",
  "prior_session_loaded": "true | false",
  "last_outcome": "WIN | LOSS | UNKNOWN",
  "historical_bias": "string",
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

Contrarian (Burry) 不參與加權，僅作 T4 veto check。

---

## PHASE 2 — ANALYST MULTI-AGENT CORE

**Agents**: Fundamentals / Sentiment / News / Technical / Contrarian (Burry)

**Scoring Rules**:
- 評分獨立，**不為 Burry 預留讓分空間**（Burry 有獨立 T4 veto 機制）
- 強訊號就給強分，避免自我審查

**統一格式**（Contrarian 另見下方）:

```json
{
  "phase": 2,
  "agent": "Fundamentals_Analyst | Sentiment_Analyst | News_Analyst | Technical_Analyst",
  "ticker": "STRING",
  "signal": "BUY | SELL | HOLD",
  "score": "-5 to +5",
  "confidence": "0.0 to 1.0",
  "key_factors": ["max 8 words each", "max 3 items"],
  "risk_flags": ["max 2 items"],
  "phase0_alignment": "ALIGNED | MISALIGNED | NEUTRAL",
  "data_source_timestamp": "YYYY-MM-DD HH:MM"
}
```

**聚焦範圍**:
- **Fundamentals**: P/E vs sector, revenue YoY, FCF, D/E, next earnings → `us-stock-analysis`
- **Sentiment**: 市場 + 個股雙層融合
  - 優先從 `sector_intel.json.fear_greed_status`；無則 **MUST run**（不得模擬）：
    ```bash
    python3 skills/market-sentiment-analyzer/scripts/sentiment.py --json-only
    ```
    取回 `composite_score`（0–100）、`vix.current`、`spy_momentum.rsi_14`、`extreme_sentiment_triggered`
  - 個股層：web search (Reddit/X, short interest, insider)
  - `Sentiment Score = 0.4 × stock_specific + 0.6 × (market_composite/10 − 5)`
  - 額外輸出：`market_sentiment_composite`, `vix_current`
- **News**: Company news 48h + analyst ratings + cross-ref Phase 0 themes → `market-news-analyst` 或 `sector_intel.json.top_catalysts`
- **Technical**: 20/50/200MA, RSI(14), MACD, volume vs 20D avg, support/resistance → `technical-analyst`（有週線圖時）

**Contrarian (Burry)** — **MUST run**（不得以估算代替）：

```bash
python3 skills/short-contrarian-analyst/scripts/burry_score.py <TICKER> --json-only
```

取回 `burry_score`（0–100）、`verdict`（T4_VETO / WARNING / NEUTRAL / VALUE_BONUS）、`components`（fcf_yield_pct / ev_ebit / debt_to_equity / pct_below_52w_high / insider_net）。

**Verdict → Phase 4 影響**：
- `T4_VETO` (score < 20) → 強制 HOLD，Phase 4 不執行倉位計算
- `WARNING` (20 ≤ score < 35) → Phase 4 final × 0.7
- `NEUTRAL` (35 ≤ score < 60) → 無調整
- `VALUE_BONUS` (score ≥ 60) → Phase 4 final × 1.15

skill 輸出映射到以下 JSON：

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

**Agent**: PM

**觸發條件**:
- **T1**: `Sentiment.score > +3` AND `Fundamentals.score < 0`
- **T2**: `News.score < -3` AND `Technical.signal = BUY`
- **T3**: `macro_backdrop_score < -3` AND any `signal = BUY` with `score > +3`
- **T4**: `Contrarian.veto_flag = true` AND `tentative_decision = BUY`
- **Anti-Bias**: 所有 analyst 信號同向 → News 追加 `devils_advocate: [...]`（最多 3 條）
  > 注意：V4.7 起 devil's advocate 欄位僅為輔助記錄；真正的異議 gate 由 **Phase 2.8 Red Team** 執行。

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
    "override_justification": "required if OVERRIDE_BURRY; ≥ 20 字具體凌駕理由；說明哪個 analyst 的哪項證據強度足以壓過估值疑慮；泛泛之言（如『基本面強』『動能好』）視為無效",
    "override_recheck_date": "YYYY-MM-DD (trade_date + 5 trading days) if OVERRIDE_BURRY else null"
  },
  "resolution": "string",
  "phase0_macro_flag": "OVERRIDE_ACTIVE | NONE",
  "proceed_to_phase3": "true | false"
}
```

**T4 仲裁（V4.7 強化）**:
- `burry_score 0–1` → 強烈建議 `CANCEL`
- `burry_score = 2` → `DOWNGRADE_DECISION`（BUY → HOLD）或 `OVERRIDE_BURRY`
- **若選 `OVERRIDE_BURRY`，自動啟動以下三項成本（V4.7 新增）**：
  1. Phase 4 倉位 × 0.5（`burry_override_multiplier`）
  2. 必填 `override_justification`（≥ 20 字，具體引用 Phase 2 某 analyst 的某項證據）
  3. 自動計算 `override_recheck_date` = 交易日 + 5 個交易日 → 寫入 Phase 5 export；到期必須重跑 protocol 驗證是否仍站得住

`proceed_to_phase3 = false` → 跳 Phase 5 輸出 `CANCEL`。

---

## PHASE 2.8 — RED TEAM ADVERSARIAL CHECK (V4.7 新增)

**Agent**: Red_Team_Adversary（以 Agent tool 呼叫 subagent 執行，**禁止 inline 推理代替**）

**觸發條件**: 始終執行（除非 Phase 2.5 `proceed_to_phase3 = false`）。

**設計動機**: V4.6 所有 analyst 由同一 model 連續產生，context 共享 → 產生「偽獨立」共識。Red Team 以獨立 subagent 強制切斷 context 錨定效應，並產出 **falsifiable kill conditions**，作為 Phase 3 bonus/penalty 的 gate。

### 執行方式（MUST use Agent tool）

```
Agent(
  description="Red Team counter-thesis",
  subagent_type="general-purpose",
  prompt="""
  You are the RED TEAM. Your sole job: argue against the tentative consensus and try to prove it wrong.

  TICKER: <TICKER>
  TENTATIVE CONSENSUS DIRECTION: <BULLISH | BEARISH | MIXED>（由 Phase 2 四個 analyst 的 signal 推得）

  PHASE 0 MACRO:
  <paste macro_summary from Phase 0>

  PHASE 2 ANALYST OUTPUTS:
  <paste all 5 analyst JSONs including Burry>

  TASK:
  1. 不要客氣、不要持平 — 你的任務是破壞共識。
  2. 找出共識最脆弱的 1 個主論點，寫成 `counter_thesis`（1-2 句）。
  3. 產出 2-3 條 **falsifiable kill_conditions** — 每條必須是具體、可驗證的未來事件，格式：「IF <X 事件> 發生於 <Y 天內> THEN 共識錯誤」。
     - 範例：「IF Q2 FCF YoY < -10% in earnings report within 30 days THEN bullish thesis broken」
     - 反例（無效）：「IF 市場反轉」「IF 利空」（不可驗證）
  4. 評 counter_evidence_strength（1-5 整數）：
     - 1-2 = 我找不到有力反論（共識夠穩）
     - 3 = 有值得警惕的風險但無確切反證
     - 4-5 = 有具體數據/事件強烈反駁共識
  5. 依 strength 決定 red_team_verdict：
     - strength ≤ 2 → `NO_VIABLE_COUNTER`
     - strength = 3 → `MODERATE_COUNTER`
     - strength ≥ 4 → `STRONG_COUNTER`

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
| `MODERATE_COUNTER` | 無 bonus 無 penalty（raw_total 不變） |
| `STRONG_COUNTER` | raw_total × 0.85 penalty，**bonus 被禁用** |

### 失敗處理

若 Agent subagent 執行失敗（timeout、tool error、JSON parse error）：
- Final Report 標記 `red_team_execution_failed: true`
- `red_team_verdict` 固定為 `MODERATE_COUNTER`（保守處理）
- Phase 3 不套用 bonus 也不套用 penalty

---

## PHASE 3 — DECISION ENGINE

**Agent**: PM

**計算步驟**（V4.7 修訂 Step 2）:

```
Step 1 (Raw):
  raw_total = Σ(Weight_i × Score_i × Confidence_i)

Step 2 (Red-Team-Gated Bonus/Penalty):  ← V4.7 核心變更
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
    final_score = raw_after_bonus           # 逆向訊號不縮小
    macro_alignment = "CONTRARIAN"
```

Contrarian Analyst 不納入 Step 1 加權。VOLATILE regime 不在 Phase 3 重複扣分（已計入 `macro_backdrop_score`）。

**Step 2 設計理由（V4.7）**：
- **V4.6 問題**：consensus bonus ×1.15 在四個 analyst 同向時無條件觸發 — 但同一 model 產生的四個「獨立」分析本身高度相關，bonus 變成偏誤放大器。
- **V4.7 解法**：bonus 必須通過 Red Team 的獨立反駁 — 只有當 Red Team（獨立 subagent）也找不到有力反論時，才配得上 ×1.15 的額外 confidence。同時為 STRONG_COUNTER 新增 ×0.85 penalty，使 Red Team 的異議有實際重量。

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

（`HOLD` 不再強制 REJECT；由 Phase 4 依 Fundamentals score 決定是否啟動 STAGED_ENTRY）

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
  "red_team_note": "counter_thesis + 主要 kill condition（1 句）"
}
```

---

## PHASE 4 — EXECUTION & RISK MANAGEMENT

**Agents**: Trader Agent + Risk Manager

### Step 1 — Dual-Track Trade Plan（Trader Agent）

**雙軌進場規則**:
- `entry_aggressive`: 當前震盪區，立即 / 市價；對應「若漲勢持續」情境
- `entry_conservative`: 技術反轉確認 / 財報後 / 關鍵均線突破；對應「若等回檔」情境
- **BUY** 決策 → 兩軌二選一由使用者決定（預設 aggressive）
- **STAGED_ENTRY** 決策 → 兩軌各佔 50% 倉位（aggressive 先進，conservative 等條件）

```json
{
  "phase": 4,
  "ticker": "STRING",
  "trade_plan": {
    "entry_aggressive": {
      "range": ["min_price", "max_price"],
      "trigger": "LIMIT | MARKET | BREAKOUT",
      "trigger_conditions": "string — e.g. 當前震盪區 / 日收盤破前高"
    },
    "entry_conservative": {
      "range": ["min_price", "max_price"],
      "trigger_conditions": "string — e.g. 陽包陰+量>1.2x avg / 財報後 / RSI>50 / 站上 200MA"
    },
    "take_profit": "price",
    "stop_loss": "price",
    "risk_reward_ratio": "float — must be >= 2.0（以 aggressive range 中點計算）",
    "time_horizon": "short | mid | long",
    "exit_conditions": "string"
  }
}
```

### Step 2 — Vol-Adjusted Position Sizing（Risk Manager）

**MUST run**（skill 會自動讀取 `positions.json` 當作既有持倉）：

```bash
python3 skills/portfolio-risk-manager/scripts/risk_manager.py <TICKER> --json-only
```

取回：
- `raw_vol_adjusted_cap_pct` — 基於 0.6% 日波動預算的原始上限
- `correlation_multiplier`（0.55 / 0.70 / 0.85 / 1.00，依 |avg_corr|）
- `sector_cap_triggered` — 若候選產業在投組 > 30% 則 true，final × 0.5
- `final_position_cap_pct` — 已整合以上所有調整 → **直接作為 `vol_adjusted_limit_pct`**

### Step 3 — Tail Risk Assessment（Risk Manager）

**MUST run**（per-stock mode）：

```bash
python3 skills/tail-risk-analyzer/scripts/tail_risk.py <TICKER> --json-only
```

取回 `fragility_label` + `position_multiplier`：

| fragility_label | tail_risk_score | position_multiplier |
|---|---|---|
| ROBUST | < 30 | × 1.0 |
| MODERATE | 30–60 | × 0.75 |
| FRAGILE | ≥ 60 | × 0.5 |

> **注意**：v4.6 以前使用 EXTREMELY FRAGILE / RESILIENT / ANTIFRAGILE 四級命名；當前 skill 實作採 ROBUST / MODERATE / FRAGILE 三級（1y daily returns → kurt/skew/var/DD/vol 加權）。倉位倍數邏輯不變。

### Step 4 — Risk Audit & Final Sizing（V4.7 新增 Burry Override 成本）

```
base         = vol_adjusted_limit（若 Step 2 執行）或 0.05
tail_adj     = base × fragility_multiplier
macro_cap    = min(tail_adj, 0.03) if macro_backdrop_score < -3 else tail_adj
binary_adj   = macro_cap × 0.5–0.7  (if binary_classification in [unknown, negative] AND event < 48h)
             = macro_cap            (otherwise)

# V4.7 新增 — Burry Override 倉位成本
burry_override_adj = binary_adj × 0.5  if phase2_5.t4_detail.resolution == "OVERRIDE_BURRY"
                   = binary_adj        otherwise

IF final_decision = STAGED_ENTRY:
  final_position_size = burry_override_adj × 0.5   # 分批只投一半
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

**Agent**: PM

執行步驟：
1. Append session export JSON 至 `./invest_logs/history.json`
2. 確認 `./invest_logs/YYYY-MM-DD_phase0.json` 已存在
3. 將完整分析存為 `../reports/YYYYMMDD_TICKER.md`（Phase 0–4 + Final Viz Table + 雙軌 entry range + 委員會決議 + **Red Team counter_thesis 與 kill_conditions**）

> **Schema 契約**：單一事實來源 = `trades_this_session[0]`。所有 Dashboard / bridge.py 需要的欄位（含 `watch_conditions`、`key_risks`、`devils_advocate_filed`、**`red_team_verdict`**、**`burry_override_active`**）必須寫入該物件；**不要**再另開 `metadata` 區塊（pre-V4.6 做法已廢棄，bridge.py 僅為向後相容保留讀取）。頂層 `ticker` / `final_action` 需與 `trades_this_session[0]` 同步。

```json
{
  "session_export_version": "V4.7",
  "export_date": "YYYY-MM-DD",
  "phase0_file": "./invest_logs/YYYY-MM-DD_phase0.json",
  "phase0_macro_snapshot": {
    "market_regime": "string",
    "macro_backdrop_score": "float",
    "key_themes": [],
    "macro_multiplier": "float"
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
**Agent**: PM

```json
{
  "phase": 6,
  "ticker": "STRING",
  "outcome": "WIN | LOSS",
  "primary_failure_agent": "Fundamentals | Sentiment | News | Technical | Contrarian | Red_Team | Risk_Manager | timing | macro_model",
  "what_was_missed": "string",
  "contributing_factors": [],
  "burry_was_right": "true | false | N/A",
  "red_team_was_right": "true | false | N/A (若 kill_conditions 有觸發且方向正確 → true)",
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
| Agent              | Signal | Score | Confidence | Key Factors (top 2) | Phase 0 Alignment |
|--------------------|--------|-------|------------|---------------------|-------------------|
| Fundamentals       |        |       |            |                     |                   |
| Sentiment          |        |       |            |                     |                   |
| News               |        |       |            |                     |                   |
| Technical          |        |       |            |                     |                   |
| Contrarian (Burry) |   —    | X/12  |     —      |                     |                   |
| Red Team (V4.7)    | verdict|strength|    —      | kill_condition #1   |        —          |

| RESULT | Decision        | Raw | RT Gate       | ×Macro | Final | Burry | Override | Pos% | Fragility | Action                |
|--------|-----------------|-----|---------------|--------|-------|-------|----------|------|-----------|-----------------------|
|        | BUY/STAGED/HOLD |  f  | ×1.15/—/×0.85 | ×f/—   |   f   | X/12  |  Y/N ×0.5|   %  | ROBUST    | EXECUTE/STAGED/CANCEL |

| Entry Track       | Range        | Trigger Conditions                      |
|-------------------|--------------|-----------------------------------------|
| Aggressive (50%)  | $min – $max  | 立即 / 當前震盪區 / 破前高               |
| Conservative (50%)| $min – $max  | 技術反轉確認 / 財報後 / RSI>50 / 站上MA  |

| Red Team Kill Conditions                                 |
|----------------------------------------------------------|
| 1. IF <事件> WITHIN <天數> THEN <推翻論點>                 |
| 2. ...                                                   |
```
