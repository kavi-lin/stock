# Multi-Agent Investment Protocol (V4.8)

<!-- [scope] US equity single-ticker analysis — phases tagged [framework] are
     market-agnostic debate scaffolding; [domain:us-equity] phases use US-specific
     data sources, analyst definitions, or tick/R-R conventions. See
     skills/MARKET_INDEX.md for the skill-level breakdown. -->

> V4.8 changelog / rationale moved to `investment/README.md`. This protocol file is execution-only.

## SESSION STARTUP
<!-- [framework] session config + startup — market-agnostic -->

```
SESSION CONFIG
──────────────────────────────────────────
RISK_TOLERANCE : LOW | MEDIUM | HIGH   (若未提供 → 預設 MEDIUM)
──────────────────────────────────────────
```

Ticker 由使用者在對話中指定。

> **非互動模式預設值（V4.8 Dashboard reverse-call）**：當 protocol 透過 `claude -p`（non-interactive）被呼叫時：
> - 若 prompt 中未帶 `RISK_TOLERANCE` → 自動採用 `MEDIUM`
> - 若 Phase 0 cache 剛過 TTL 但仍在同一交易日的 pre-market 窗口內 → 直接使用不重跑，不得因「是否越線使用」而停下來問使用者
> - 任何需要使用者輸入的點都應採「protocol 規則預設」而非 ask-and-wait，因為 reverse-call 無法接收後續訊息

---

## GLOBAL RULES
<!-- [framework] debate hygiene / evidence rules / language — market-agnostic -->

1. **Phase Order**: 0 → 1 → 2 → 2.5 → 2.8 → 3 → 4 → 5。不跳過。
2. **Phase 0 Cache（三層優先；FRESH = mtime < 3 小時前 / 10800s）**:
   - L1: `../sector/sector_logs/*_sector_intel.json` 最新檔 FRESH → 提取 macro，跳過 search（`phase0_source: SECTOR_CACHE`）
   - L2: `./invest_logs/*_phase0.json` 最新檔 FRESH → 載入（`INVEST_CACHE`）
   - L3: 皆 STALE 或缺失 → web search，寫入 `./invest_logs/YYYY-MM-DD_phase0.json`（`FRESHLY_EXECUTED`）
3. **Theme Cache**（FRESH = mtime < 3h）: 執行 `python3 ../skills/theme-detector/scripts/theme_detector.py --skip-if-fresh 10800`；script 自管 freshness — 快速 exit（< 1s）代表 cache fresh，慢速 exit（140-180s）代表重新抓取；兩種情況完成後都讀 `../skills/theme-detector/cache/theme_detector_*.json` 最新檔。
4. **Prior Session**: 讀 `./invest_logs/history.json` 最近一筆（僅供 PM 參考，**不得** pass 進 Phase 2 subagent）。
5. **Output**: 邏輯輸出 JSON；Markdown 僅用於 Final Viz Table。
6. **key_factors**: 最多 3 條，每條 ≤ 8 英文字。
6a. **語言規定（強制）**: 下列欄位**必須用繁體中文**輸出，不得使用英文：`watch_conditions`（鍵值的 description 部分）、`key_risks`（每條描述）、`macro_context`、`red_team_counter_thesis`、`red_team_kill_conditions`（每條）。`watch_conditions` 的 key 名稱保持 snake_case 英文（供程式識別用），value 描述必須是中文。
7. **MD Report**（強制）: Phase 5 後存 `../reports/YYYYMMDD_TICKER.md`。不得省略。
8. **Skill 執行強制規則（NO SIMULATION）**: 凡 protocol 內標示「**MUST run**」的 skill 指令，**必須實際執行 Bash 呼叫 python3 script 並解析 JSON 輸出**，嚴禁以語言模型自行估算／模擬數值代替。受此規則約束的 skill：
   - `market-sentiment-analyzer`（Phase 2 Sentiment subagent 內）
   - `us-stock-analysis`（Phase 2 Fundamentals subagent 內）
   - `market-news-analyst`（Phase 2 News subagent 內）
   - `technical-analyst`（Phase 2 Technical subagent 內）
   - `short-contrarian-analyst`（Phase 2 inline Burry）
   - `portfolio-risk-manager`（Phase 4 Step 2）
   - `tail-risk-analyzer`（Phase 4 Step 3）
   - `fred-macro`（Phase 0 L4，V4.9 新增）— 失敗不阻斷流程，`fred_available: false` 繼續跑
   - 若某次執行 skill script 發生錯誤，必須在 Final Report 對應欄位標記 `skill_execution_failed: true` 並記錄 stderr，禁止靜默用估算值補上。
9. **Red Team 獨立執行強制規則（V4.7）**: Phase 2.8 Red Team Adversary **必須以 Agent tool 呼叫 subagent 執行**（`subagent_type: "general-purpose"`），禁止 inline 推理代替。
10. **Non-Interactive 執行強制規則（V4.8 新增）**: 當 protocol 被 Dashboard reverse-call（`claude -p` non-interactive）觸發時，Claude 不得向使用者發問或輸出「請確認…」的摘要表並等候。Protocol 本身的明確規則優先（e.g. RISK_TOLERANCE 預設 MEDIUM、Phase 0 三層 cache 依 TTL 決定）。**CLAUDE.md 的「實作前確認規則」僅適用於使用者要求的 code change，不適用於 protocol 自動產生的 reports/history/cache 等分析輸出檔案** — 這些是 protocol 正常執行產物，不得因檔案數量觸發確認流程。
11. **Parallel Analyst 強制規則（V4.8 新增 — 核心機制）**:
    - Phase 2 四個 analyst（Fundamentals / Sentiment / News / Technical）**必須**以 **4 個 Agent tool 平行呼叫**（subagent_type: "general-purpose"）執行，**並放在同一則訊息內**（確保真正平行；parent 在 4 個結果都回來前不進入 Phase 2.5）。
    - 每個 subagent 的 prompt **只能包含**：(a) ticker、(b) Phase 0 macro JSON、(c) 該 lane 的 rubric + MUST run skill 指令、(d) output schema。
    - **禁止** pass 進 subagent 的資訊：其他 analyst 的 tentative signal、prior_session 的 historical_bias、current active_weights、任何來自既有持倉 / 偏好的引導。
    - 每個 subagent 回傳的 JSON **必須包含** `subagent_isolated: true` sentinel，parent 需驗證；若缺少 → 該 analyst 視為 degraded，confidence cap 0.6。
    - Burry 不套用 D 規則（inline skill call）。
    - Red Team 仍然是 subagent，但在 Phase 2 之後、Phase 3 之前。

---

## TEAM STRUCTURE
<!-- [domain:us-equity] defines 5 analysts (Fundamental/Sentiment/News/Technical/Burry)
     tuned for US-listed equities; Burry in particular is US-valuation-specific. -->

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
<!-- [domain:us-equity] pulls SPX breadth, FTD, market-top, VIX, F&G (all US indices / sentiment). -->

**三層 cache（依序；FRESH = mtime < 3 小時前）**:
1. `../sector/sector_logs/*_sector_intel.json` 取最新檔，`now - mtime < 10800s` → FRESH → 提取 `market_regime`, `exposure_ceiling`, `political_risk_summary`, `actionable_themes`, `session_notes` → Phase 1
2. `./invest_logs/*_phase0.json` 取最新檔，FRESH → 載入 → Phase 1
3. 皆 STALE 或缺失 → 執行 `market-news-analyst` skill（或 web search），寫入 `./invest_logs/YYYY-MM-DD_phase0.json`

> 檢查 mtime 可用 Bash `find path -name pattern -mmin -180` 或 `stat -f %m file`；Python `os.path.getmtime()`。

**L4 — FRED macro snapshot（V4.9 新增；MUST run）**:

不管 L1/L2/L3 哪層觸發，Phase 0 **一定額外跑** `fred-macro` skill 拿官方利率 / 通膨 / 就業 / 信用 / 壓力五類官方數據。FRED 免費無配額，用來**校正**下面的 `phase3_macro_multiplier`（見 blending 規則）。skill 自帶 15 min cache，連續分析多個 ticker 只打一次網路。

```bash
python3 skills/fred-macro/scripts/fetch.py --json-only
```

> ⚠️ **讀取輸出前必讀**：`skills/fred-macro/SECTOR_ROTATION_GUIDE.md`（LLM instruction set，非人類文件）

取回 `fred_snapshot` 整個 object + `regime_signals` 區塊，寫入 phase0 JSON。若 skill 失敗（網路 / key 失效）→ `fred_snapshot: null` + `fred_available: false`，protocol 繼續跑不中斷，multiplier 回退純 LLM 查表值。

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

  "fred_available": "true | false",
  "fred_snapshot": {
    "generated_at": "ISO timestamp from FRED fetch",
    "yield_curve_value":          "float (T10Y2Y) — null if unavailable",
    "yield_curve_inverted":       "bool — T10Y2Y < 0",
    "yield_curve_steep":          "bool — T10Y2Y > 1.0",
    "fed_funds_current":          "float — DFF latest %",
    "fed_rate_direction":         "rising | falling | flat | unknown",
    "real_rate_10y_estimate":     "float — DGS10 - CPIAUCSL YoY",
    "credit_spread_pctile_1y":    "int 0-100 — HY spread percentile in last year",
    "credit_stress_elevated":     "bool — HY pctile > 75",
    "financial_stress_above_avg": "bool — NFCI > 0",
    "cpi_yoy_pct":                "float — CPIAUCSL YoY",
    "core_cpi_yoy_pct":           "float — CPILFESL YoY",
    "unemployment_pct":           "float — UNRATE latest",
    "series_fetched_count":       "int — how many of the 12 series succeeded"
  },

  "phase3_macro_multiplier": "float",
  "macro_multiplier_rationale": "string — one line explaining LLM baseline + FRED caps applied",
  "mandatory_risk_flags": [],
  "binary_risks": []
}
```

**macro_multiplier 查表（LLM baseline）**:

| macro_backdrop_score | baseline multiplier |
|---|---|
| ≥ +3 | 1.2 |
| +1 to +3 | 1.0 |
| -1 to +1 | 0.9 |
| -3 to -1 | 0.75 |
| < -3 | 0.6 |

**V4.9 FRED blending rules**（套用到 baseline 上，取**最小值**為 final multiplier）:

當 `fred_available == true`，逐條檢查，凡觸發的都算出上限值，最後 `final = min(baseline, 觸發的所有上限)`：

| 觸發條件（FRED） | 意義 | 上限 cap |
|---|---|---|
| `yield_curve_inverted` (T10Y2Y < 0) | 12-18m 衰退前兆 | **0.75** |
| `credit_stress_elevated` (HY pctile > 75) | 信用市場 risk-off | **0.85** |
| `financial_stress_above_avg` (NFCI > 0) | 整體金融緊縮 | **0.9** |
| `real_rate_10y_estimate > 2.0` | 實質利率 > 2% 屬壓抑區 | **0.9** |
| `fred_available == false` | FRED 無資料 | baseline（無 FRED 校正） |

**雙向 bonus**（選擇性，只觸發一條）:
- 若 baseline ≥ 1.0 **且** 所有 FRED 條件均正常（無倒掛、credit pctile < 50、NFCI < 0、real_rate < 1）→ multiplier `× 1.05`（總 cap 仍為 1.25）

**rationale 欄位**：必寫一行記錄決策過程，e.g.
- `"LLM baseline 1.0 (score +1.5); no FRED caps triggered; × 1.05 bonus for all-clear → 1.05"`
- `"LLM baseline 1.2 (score +3.5); capped to 0.75 (yield_curve_inverted, T10Y2Y=-0.12)"`
- `"LLM baseline 0.9 (score -0.5); FRED unavailable, kept baseline → 0.9"`

**Phase 0 Validator Gate（V4.9，MANDATORY）**:

寫完 phase0 JSON 後 MUST 跑：
```bash
python3 investment/scripts/validate_phase0.py --ticker <TICKER>
```

rc ≠ 0 必須修正後重跑。常見失敗：
- `fred_available` 欄位缺失（最常見 — LLM 直接跳過 L4）
- `fred_snapshot` null 但 `fred_available=true`
- `macro_multiplier_rationale` 缺失或無 FRED 引用
- `regime_label` 不在 10 個合法值內

---

## PHASE 1 — CONTEXT & MEMORY REVIEW
<!-- [framework] ticker intake + prior-session lookup — market-agnostic flow -->

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
<!-- [framework] 4-analyst parallel subagent pattern is market-agnostic.
     [domain:us-equity] analyst identities (Fundamental/Sentiment/News/Technical)
     and data sources (yfinance, FMP, VIX, F&G) are US-specific. -->

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
<!-- [domain:us-equity] Burry Score uses US valuation metrics (FCF yield, EV/EBIT, 52w high). -->

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
<!-- [framework] conflict-resolution arithmetic; market-agnostic -->

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
<!-- [framework] red-team subagent adversary; market-agnostic -->

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

  PHASE 0 FRED MACRO SNAPSHOT (V4.9，slim — 若 fred_available=false 顯示 "FRED unavailable"):
  <paste fred_snapshot 11 個欄位：regime_label / regime_confidence / macro_scores_composite /
   yield_curve_value / yield_curve_inverted / credit_stress_elevated / financial_stress_above_avg /
   fed_rate_direction / real_rate_preferred / sector_rotation_favor[] / sector_rotation_avoid[] /
   velocity_highlights[]>

  PHASE 2 ANALYST OUTPUTS (5 agents including Burry):
  <paste all 5 analyst JSONs>

  TASK:
  1. 不要客氣、不要持平 — 你的任務是破壞共識。
  2. 找出共識最脆弱的 1 個主論點，寫成 `counter_thesis`（1-2 句）。
  3. 產出 2-3 條 falsifiable kill_conditions：「IF <事件> WITHIN <天數> THEN <推翻論點>」。
     無效範例（不可驗證）：「IF 市場反轉」「IF 利空」
  4. (V4.9) FRED 衝突挑戰規則 — 若 fred_snapshot 顯示與 thesis 衝突的訊號：
       - yield_curve_inverted = true
       - real_rate_preferred > 2.0
       - credit_stress_elevated = true OR financial_stress_above_avg = true
       - regime_label ∈ {Late Cycle Tightening, Stagflation, Recession Risk, Recession Easing}
       - ticker 屬於 sector ∈ fred_snapshot.sector_rotation_avoid
       - velocity_highlights 含「accelerating」於 NFCI / BAMLH0A0HYM2（金融緊縮加速）
     → MUST 至少 1 條 kill_condition 引用 **具體 FRED 數值**
       (e.g.「real_rate 2.15% > 2.0% threshold AND DGS10 trend rising 90d」)
       不可寫 vague 的「macro 轉差」、「總體環境不佳」
  5. 評 counter_evidence_strength（1-5 整數）：
     - 1-2 = 找不到有力反論
     - 3 = 有值得警惕的風險但無確切反證
     - 4-5 = 有具體數據/事件強烈反駁（**FRED 衝突訊號 ≥ 2 個自動 ≥ 4**）
  6. verdict 對照：
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
<!-- [framework] scoring + consensus bonus + macro multiplier; market-agnostic -->

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
<!-- [framework] vol-adjusted sizing / R-R math. [domain:us-equity] tick-size and option-chain assumptions. -->

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
<!-- [framework] schema validation + append to history.json; market-agnostic -->

**Agent**: PM（inline）

執行步驟：
1. **Append session export JSON 至 `./invest_logs/history.json`** — shape **必須**嚴格符合 `./phase5_export_schema.md`（FULL EXAMPLE 區塊）。該檔案是 session export schema 的唯一事實來源；protocol 本身不再內嵌 JSON 範本。
2. **執行驗證腳本**：
   ```bash
   python3 investment/scripts/validate_session_export.py
   ```
   rc ≠ 0 時必須**修正 history.json 最後一筆 entry** 後再跑一次，直到 rc=0 才可進入步驟 3。常見失敗：missing top-level `ticker`/`final_action` mirrors、legacy `{ticker, metadata:{}}` flat shape、HOLD 省略 `watch_conditions`。
3. 確認 `./invest_logs/YYYY-MM-DD_phase0.json` 已存在
4. **MD 報告撰寫委派 Sonnet subagent（V4.8 成本優化）**：將完整 Phase 0–4 決策資料傳入 Sonnet subagent，由其**純粹排版**產出 `../reports/YYYYMMDD_TICKER.md`。Subagent 不得重新評分、不得改變任何 score / signal / decision / position_size。這是純格式化任務，節省 ~$0.5/次的 Opus 輸出成本。

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

> **Schema 定義位置**：Session export 的完整 shape、必填欄位、HOLD/CANCEL 填法、legacy shape 禁止清單、FULL EXAMPLE 全部集中於 **`./phase5_export_schema.md`**。本 protocol 不再內嵌 JSON 範本，避免 protocol 升版時兩邊 drift。
>
> 以下為該檔案的關鍵重點（完整規範必須對照該檔）：
> - **單一事實來源** = `trades_this_session[0]`；頂層 `ticker` / `final_action` / `date` 需與 `trades_this_session[0]` 同步（bridge.py 讀頂層）
> - **禁止 pre-V4.6 legacy shape** `{"ticker":..., "metadata":{...}}` — validator 會直接拒絕
> - **HOLD / CANCEL 決策也必填觀察類欄位**：`macro_alignment`、`fragility_label`、`binary_classification`、`time_horizon`、`trade_metadata`、`analysis_price` 一律必填；`watch_conditions` ≥ 3 條再評 / 退場觸發
> - **`analysis_price`**（V4.8 新增必填）：分析當下的股價快照，從 Phase 2 Technical analyst 或 us-stock-analysis skill 的輸出抓取（通常是最新收盤或即時價）。Dashboard 用此對比 yfinance 即時價呈現漂移百分比
> - **BUY / STAGED_ENTRY 決策**：`risk_reward_ratio` 必填且 ≥ 2.0，否則 validator 失敗
>
> **Step 2 validator 是強制 gate**：它 import 當前 schema 的 REQUIRED 清單，自動偵測任何 drift。若未跑 validator 或 rc ≠ 0 就繼續 Step 3，視為 protocol 違規。

---

## PHASE 6 — CONTINUOUS LEARNING
<!-- [framework] post-mortem review; market-agnostic -->

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
<!-- [framework] output format; market-agnostic -->

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
