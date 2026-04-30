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
1. `../sector/sector_logs/*_sector_intel.json` 取最新檔，`now - mtime < 10800s` → FRESH → 提取 `market_regime`, `exposure_ceiling`, `political_risk_summary`, `actionable_themes`, `session_notes`, **`_phase0.ftd.days_since_ftd` / `_phase0.ftd.ftd_status_text`（V4.9 — Phase 4 Step 3.5 FTD timeline gate 必需）** → Phase 1
2. `./invest_logs/*_phase0.json` 取最新檔，FRESH → 載入 → Phase 1
3. 皆 STALE 或缺失 → **跑 4 個 skill 組成 chain**（V4.9 / I-PD：取代「web search」這條 fallback，可重現、節省 LLM token）：

   ```bash
   # 4 個 skill 平行可、序列也行；任何一個失敗不阻斷 protocol（marker null）
   python3 skills/market-sentiment-analyzer/scripts/sentiment.py --json-only
   python3 skills/market-breadth-analyzer/scripts/market_breadth_analyzer.py --output-dir sector/breadth_cache/
   python3 sector/ftd_yfinance.py --output-dir sector/ftd_cache/
   python3 sector/market_top_yfinance.py --output-dir sector/market_top_cache/
   ```

   合成這 4 個 skill 輸出 + L4 `fred-macro` 結果 → `phase0.json`；不需要 LLM 自行 web search 抓 VIX / F&G / breadth / FTD / market-top。**僅 `key_themes` / `bullish_signals` / `bearish_signals` 文字面**保留 LLM 摘要（市場敘事是 LLM 強項，數字是 API 強項）。

   寫入 `./invest_logs/YYYY-MM-DD_phase0.json` (`phase0_source: SKILL_CHAIN`)

> 檢查 mtime 可用 Bash `find path -name pattern -mmin -180` 或 `stat -f %m file`；Python `os.path.getmtime()`。
> Skill chain 失敗時 fallback：若 ≥ 2 個 skill 失敗，protocol 才 fallback 到 LLM web search，並在 `phase0_source` 標 `WEB_SEARCH_FALLBACK`。

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

  "_market_signals": {
    "// V4.9 / I-PE — explicit fields so Phase 2 lanes don't re-fetch": "",
    "fear_greed_index":     "float 0-100 (from market-sentiment-analyzer / CNN endpoint, null if missing)",
    "vix_current":          "float (from yfinance ^VIX or sentiment skill)",
    "vix_regime":           "LOW | NORMAL | ELEVATED | CRISIS",
    "spy_rsi_14":           "float 0-100 (from sentiment skill)",
    "spy_pct_above_ma200":  "float % (positive = above MA200)",
    "breadth_composite":    "int 0-100 (from market-breadth-analyzer)",
    "ftd_status":           "FTD_CONFIRMED | RALLY_ATTEMPT | NO_SIGNAL | DISTRIBUTION (from ftd-detector)",
    "ftd_days_since":       "int — days since last FTD (sector_intel _phase0.ftd 欄位)",
    "market_top_score":     "int 0-100 — top risk score (from market-top-detector)",
    "top_catalysts":        "list of {date, ticker?, headline, source} from sector_intel.top_catalysts; Phase 2 News lane 應該先檢查再決定要不要重抓"
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

### Phase 1 資料層（V4.8.1 新增）— Dual-Fetch Snapshot

Phase 1 結束前 PM **MUST** 執行下列步驟，產生供 Phase 2 全 4 個 lane 共享的 ticker 資料快照：

1. **執行 dual_fetch**（一次性 per ticker per session）:
   ```bash
   bash skills/finnhub-client/scripts/run_dual_fetch.sh --tickers <TICKER>
   ```
   - 輸出：`skills/finnhub-client/data/<YYYY-MM-DD>/<TICKER>.json`
   - 失敗判定（key 未設、network error、Finnhub 全部 500）→ Phase 1 設 `data_bundle_available: false`，分析照跑，Phase 2 共通 prompt 省略 `TICKER_DATA_BUNDLE` 段落
   - FMP audit-side 失敗（quota_exceeded / unauthorized）**不算失敗** — `scoring.*` 仍完整，照常使用

2. **讀取 scoring 段**（取得 9 個 canonical scalar 欄位）:
   ```
   bundle = json.load(open("skills/finnhub-client/data/<DATE>/<TICKER>.json"))
   TICKER_DATA_BUNDLE = bundle["scoring"]   # 只取這個 key
   ```

3. **物理隔離契約**（與 V4.8 historical_bias 規則同等強度）:
   - **禁止**讀取 `bundle["_audit"]` 任何欄位
   - **禁止**將 audit 內容寫入任何 subagent prompt、log、reasoning
   - PM context 若意外出現 `_audit.fmp.*` 或 `_audit.diff.*` → 視為 protocol 違規，當前 ticker 分析作廢，重啟 Phase 1
   - 用途說明：`_audit` 是給 `audit_drift_check.py` 與人類稽核用，跨 provider 數字若灌進 LLM 會讓 score 混入「provider 加權」隨機性，破壞跨 session 可重現性

### Phase 1 資料層（V1.71 新增）— Earnings-Analyst Cache 機會式讀取

Phase 1 末段 PM **可選**檢查 earnings-analyst skill 的歷史 cache，補充 Fundamentals lane 的深度財報視野(成本:1 次 file read,**0 FMP call**)。

1. **檢查 cache 是否存在**:
   ```bash
   ls skills/earnings-analyst/cache/<TICKER>_*.json 2>/dev/null
   ```
   找到最新的 `<TICKER>_<YYYY-MM-DD>.json` 檔。

2. **新鮮度判斷**(必須兩條件都符合):
   - cache 檔含 `composite_score` 欄位(代表 analyze.py 已跑完)
   - 距 cache 檔 mtime ≤ 90 天(對齊 earnings-analyst CACHE_TTL_DAYS)

3. **若 cache 新鮮 → PM 抽 thin 摘要進 EARNINGS_ANALYST_BUNDLE**:
   ```python
   ea = json.load(open("skills/earnings-analyst/cache/<TICKER>_<DATE>.json"))
   EARNINGS_ANALYST_BUNDLE = {
     "last_earnings_date":  ea["last_earnings_date"],
     "next_earnings_est":   ea.get("next_earnings_est"),
     "composite_score":     ea["composite_score"],
     "verdict":             ea["verdict"],
     "score_components":    ea["score_components"],
     "quality_flags":       ea.get("quality_flags") or [],
     "margins_8q":          (ea.get("derived") or {}).get("margins_8q"),       # 8Q gross/op/net margin trend
     "yoy_growth":          (ea.get("derived") or {}).get("yoy_growth"),       # rev/earnings YoY + acceleration label
     "balance_health":      (ea.get("derived") or {}).get("balance_health"),
     "cash_flow_quality":   (ea.get("derived") or {}).get("cash_flow_quality"),
     "valuation": {
       "dcf_intrinsic":          (ea.get("valuation") or {}).get("dcf_intrinsic"),
       "dcf_vs_price_pct":       (ea.get("valuation") or {}).get("dcf_vs_price_pct"),
       "price_target_consensus": (ea.get("valuation") or {}).get("price_target_consensus"),
       "pt_upside_pct":          (ea.get("valuation") or {}).get("pt_upside_pct")
     },
     "report_path":         "reports/<DATE>_<TICKER>_earnings.md"
   }
   ```

4. **若 cache 不存在或過期** → 整段省略,Phase 2 Fundamentals lane 標註 "EARNINGS_ANALYST_BUNDLE: not available — pure dual-fetch + skill output";**禁止**僅為了補 cache 而 enqueue 一次 `財報` protocol(那是 user 主動觸發層,不該由 PM 自動排隊)。

5. **物理隔離契約同 dual-fetch**:
   - 不得修改 cache 內容
   - 不得讓 Fundamentals 以外的 lane 使用 `EARNINGS_ANALYST_BUNDLE.composite_score / verdict`(避免 lane 間互相 anchor)
   - Sentiment / News / Technical lane 的 prompt **不得**包含此 bundle

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
<paste Phase 0 macro_summary JSON + Phase 0._market_signals (含 fear_greed_index/vix_current/vix_regime/spy_rsi_14/spy_pct_above_ma200/breadth_composite/ftd_status/market_top_score/top_catalysts)>

TICKER DATA BUNDLE (read-only, shared across all 4 analysts; canonical for 15 scalar fields — V4.9 I-PA):
<paste TICKER_DATA_BUNDLE JSON — Phase 1 PM 提供；若 data_bundle_available: false 則整段省略並在 prompt 標註 "TICKER_DATA_BUNDLE: unavailable, fall back to skill-internal fetch">

EARNINGS-ANALYST BUNDLE (read-only, **Fundamentals lane only** — V1.71):
<僅在 Fundamentals subagent prompt 出現;其他 3 個 lane 不得包含此段。
若 EARNINGS_ANALYST_BUNDLE 為 None(cache 不存在或過期 > 90d)→ 整段省略並標註 "EARNINGS_ANALYST_BUNDLE: not available — pure dual-fetch + skill output";否則 paste Phase 1 收集到的 EARNINGS_ANALYST_BUNDLE JSON。
**用途**:Fundamentals 可以引用 8Q margin trend / cash flow quality / DCF upside 強化估值與品質判斷;**禁止**將 composite_score 直接 mirror 為 lane score(各 lane 須維持獨立評分)>

DATA SOURCE DISCIPLINE (V4.9 / I-PF — STRICT):

  ❌ FORBIDDEN web search — 以下資料**已在 Phase 0 _market_signals / TICKER DATA BUNDLE / 你的 lane skill 輸出裡**，禁止 web search 重抓 / 用 web 結果覆寫：
    Quote / Valuation: price, peRatio, forwardPE, pegRatio, epsTTM, mktCap, dividendYield, priceToBookRatio
    Quality / Forward: roeTTM, debtToEquity, fcfPerShareTTM, nextEarningsDate
    Market signals: VIX, fear_greed_index, SPY RSI, breadth, FTD status, market_top_score
    Insider / short: insider_transactions, MSPR, short_pct_float, acquired_disposed_ratio
    Analyst: rating consensus (strongBuy/buy/hold/sell counts), price target high/low/median, upgrade/downgrade history
    Filings: 10-K / 10-Q / 8-K dates and links
    Company news headlines（已由 fetch.py 提供 finviz + yfinance + Finnhub 三來源 deduped）
    OHLC / RSI / MACD / MA（已由 technical-analyst skill 提供）
    
  ✅ ALLOWED web search — 僅以下情境可用 ≤ 1 次 web search call，且只取 narrative tone，不可從中抽結構化數字：
    - Reddit / X / StockTwits 個股討論氛圍（hype / bearish / split）
    - Conference call transcript 段落引用 / management commentary
    - 即時 supply chain rumors / 地緣政治新聞（API 無）
    - 競爭格局 / market share narrative（API 無）
    - Product reviews / user-level sentiment

  違規處理：subagent 輸出若引用 web search 來的數字而非結構化 source，PM 在 Phase 2.5 conflict resolution 時 **自動扣 confidence 0.2**；連續 3 次違規該 lane 視為 degraded。

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
- **TICKER_DATA_BUNDLE 使用規則**（V4.9 — I-PA 擴充至 15 scalar）— 若 prompt 含 bundle:
  - **15 個 scalar 以 bundle 為權威來源**（已通過 dual-fetch audit）：
    - **Quote (4)**: `price`, `previousClose`, `dayHigh`, `dayLow`
    - **Profile / valuation (5)**: `mktCap`, `peRatio`, `epsTTM`, `dividendYield`, `priceToBookRatio`
    - **Forward / quality / earnings (6, NEW)**: `forwardPE`, `pegRatio`, `roeTTM`, `debtToEquity`, `fcfPerShareTTM`, `nextEarningsDate`
  - **Skill 應該優先讀 bundle，不要重打 yfinance / FMP 抓相同欄位**。us-stock-analysis 改成「給定 bundle，計算衍生指標（P/E vs sector median、FCF yield、預期成長率分位）」，不重抓 raw scalar
  - 若 us-stock-analysis 輸出與 bundle 同一欄位**不一致**（差異 > 1%）→ 採用 bundle 值，並在 reasoning 註記「以 dual-fetch canonical 為準」
  - **估值評分權重建議**:
    - `peRatio`：主要估值依據，搭配 epsTTM 做合理性檢查（peRatio × epsTTM ≈ price）
    - `forwardPE`：前瞻估值（用 sell-side EPS estimate），對成長股**比 trailing peRatio 更具預測力**；若兩者差距 > 20% 表示 sell-side 預期 EPS 大幅變化（成長預期 / 衰退預期）
    - `pegRatio`：trailing PEG（peTTM ÷ EPS 5Y 成長率），<1 一般視為合理；⚠️ pegRatio 對非穩態成長公司易失真，不要當主要 signal
    - `roeTTM`：資本效率，>15% 視為優質、>25% 是 wide moat 候選；金融股例外（杠桿放大）
    - `debtToEquity`：< 0.5 健康 / 0.5-1.5 中性 / > 1.5 槓桿偏高；資本密集行業（utilities/REIT/銀行）放寬
    - `fcfPerShareTTM`：FCF 直接除股本；**FCF yield = fcfPerShareTTM ÷ price**，> 5% 通常是價值訊號；負值需在 reasoning 解釋（投資期 / 一次性 capex）
    - `nextEarningsDate`：若距今 ≤ 7 天 → 進 binary risk window，rubric 的「conviction」打分自動 ×0.7（避免 earnings whipsaw 後悔）；若 ≤ 2 天 ×0.5
    - `dividendYield`：**單位是百分比**（e.g. 0.38 = 0.38%，不是 38%），定義為 indicated annual（前瞻）
    - `priceToBookRatio`：⚠️ **視為近似值**。已知跨 provider 方法論差異 10-30%（書值 snapshot、goodwill 處理不同）。在估值打分中**權重應低於 P/E**。資產型公司（金融、REIT、保險）若 P/B 為主要估值依據，需在 reasoning 明示「依 Finnhub canonical book value，方法論為 ...」並接受 ±20% 模糊區間
    - `mktCap` 用於 size cohort 判斷：mega > $200B / large $10B-$200B / mid $2B-$10B / small < $2B；不同 cohort 的 P/E 與成長預期 baseline 不同
  - 若 bundle 某欄位為 `null`（e.g. ETF 沒 mktCap、新上市無 epsTTM、無發放股利時 dividendYield=null）→ 用 us-stock-analysis 輸出補值；若皆無則該欄位排除於評分計算，不得猜測
  - 若 prompt 標註 `TICKER_DATA_BUNDLE: unavailable` → 完全 fallback 到 us-stock-analysis 輸出，本段規則不適用
- **EARNINGS_ANALYST_BUNDLE 使用規則**(V1.71)— 若 prompt 含此 bundle:
  - **8Q margins / yoy_growth / cash_flow_quality** 是 Fundamentals 計分的「深層證據」— 引用具體數字(e.g. "gross margin 8Q 從 60% 擴張到 75% — operating leverage 持續發酵")
  - `quality_flags` 觸發強訊號:`accruals_warning` / `negative_fcf` / `capex_outpaces_ocf` 任何一條 → score 至少 -1;乾淨(空 list)且 composite ≥ 80 → 至少 +1
  - `valuation.dcf_intrinsic` + `valuation.pt_upside_pct` 是品質校驗:dual-fetch peRatio 與 DCF intrinsic vs price 兩相對照(e.g. peRatio 35 偏高,但 DCF +20% upside → 估值不極端)
  - **絕對禁止**:把 `composite_score / verdict` 直接 copy 為 lane score。Fundamentals 維持獨立評分,只用 bundle 當輔助證據
  - 若 prompt 標註 `EARNINGS_ANALYST_BUNDLE: not available` → 完全 fallback 到 us-stock-analysis 輸出 + dual-fetch bundle,本段不適用

#### Sentiment Subagent
- **RUBRIC**:
  - **市場層**（V4.9 / I-PE 優化）：**優先讀 Phase 0 `_market_signals`**（已含 `fear_greed_index` / `vix_current` / `spy_rsi_14` / `breadth_composite`）— 不要重跑 sentiment.py 抓市場數字。
  - **個股層 + 補充市場層**（若 Phase 0 缺欄位才打）：
    ```bash
    python3 skills/market-sentiment-analyzer/scripts/sentiment.py --ticker <TICKER> --json-only
    ```
    回傳：
    - 市場層 fallback（Phase 0 沒有時用）：`composite_score`, `vix.current`, `spy_momentum.rsi_14`, `fear_greed_index`, `extreme_sentiment_triggered`
    - 個股層 `ticker_signals`：
      - `insider_stats[]`（FMP `/stable/insider-trading/statistics`，最近 4 季）— 每季含 `acquired_disposed_ratio`, `total_acquired_shares`, `total_disposed_shares`, `acquired_transactions`, `disposed_transactions`
        - **`acquired_disposed_ratio` 是 acquired_count / disposed_count**（按 transaction 個數，非股數）：< 0.3 = insider 顯著在賣，0.3-0.7 = mixed，> 1.0 = insider 在買
      - `insider_sentiment.latest_mspr`（Finnhub `/stock/insider-sentiment` MSPR 最近一個月）—  -100 ~ +100 score。Null 不一定壞訊號（小型股 / 該月無 transaction）
      - `short_pct_float`（yfinance `info.shortPercentOfFloat`）— **百分比**（e.g. 1.22 = 1.22%）。FINRA bi-monthly 更新較慢（2 週週期）
      > **V4.9 重要規則**：個股層**禁止 web search Reddit/X/insider/short**。Reddit/X **narrative tone** 仍可保留 ≤ 1 次 web search，但**數字必須來自上述 API**。LLM 不得從 web search 結果猜短利率 / 內部人活動。
      > 市場層 ticker-agnostic 部分**仍有 15 min cache**（連續分析多 ticker 自動 hit）；個股層每 ticker 都重抓（per-ticker session-scope）。
  - 融合公式：`Sentiment Score = 0.5 × stock_specific + 0.5 × (market_composite/10 − 5)`
    - **stock_specific** 計分（-5 到 +5）：
      - insider ratio < 0.3 → -1（賣壓）；> 1.0 → +1（買進）；MSPR > +30 → +1；< -30 → -1
      - short_pct_float > 20% → -2（重壓且 squeeze 風險）；10-20% → -1；< 5% → +1
      - Reddit/X tone（單次 search 取整體傾向）→ ±1
- **額外輸出欄位**：`market_sentiment_composite`, `vix_current`, `insider_signal`, `short_pct_float`, `mspr_latest`

#### News Subagent
- **RUBRIC**: 過去 48h company news + analyst rating changes + price target trend + cross-ref Phase 0 macro themes。重大 upgrade / downgrade / 8-K / 併購傳聞明顯偏向。
- **SKILL** (V4.9 / I-PC 擴充：FMP grades-historical + price-target-consensus + grades-consensus + grades-news + Finnhub /company-news):
  ```bash
  python3 skills/market-news-analyst/scripts/fetch.py <TICKER> --hours 48 --json-only
  ```
- **回傳結構化欄位**（subagent 應優先用，**禁止** 用 web search 重抓 analyst rating / target 數字）：
  - `analyst_actions[]`：FMP `/stable/grades-historical` 過去 30 天 upgrade/downgrade/initiate，每筆含 `action`, `firm`, `new_grade`, `previous_grade`。`analyst_actions_source` 標 `fmp_grades_historical`（主）/ `finviz_fallback`（FMP 空時）
  - `analyst_consensus`：FMP `/stable/grades-consensus` 當前評等分布 `{strong_buy, buy, hold, sell, strong_sell, consensus}`。**評分權重**：consensus="Strong Buy"+1.5、"Buy"+1、"Hold"0、"Sell"-1、"Strong Sell"-2
  - `price_target`：FMP 高/低/median/consensus + 月/季/年期間平均 target trend。比較 `target_consensus` vs `current_price`：>20% 折價 → +1，>20% 溢價 → -1
  - `analyst_news[]`：FMP `/stable/grades-news` 評等變動相關新聞含 publisher/URL（補 narrative）
  - `headlines[]`：finviz + yfinance + **Finnhub `/company-news`**（含 sentiment + category）三來源 deduped
  - `sec_filings_recent[]`：FMP `/stable/sec-filings-financials` 取代 legacy v3 endpoint
  - `data_quality.fmp_calls` / `fmp_failures` 顯示資料 freshness 跟可靠性
- **優先檢查 Phase 0 `_market_signals.top_catalysts[]`**（V4.9 / I-PE）：若該票已在裡面，subagent 應引用既有 catalyst（避免重抓）；只有「Phase 0 缺該票 catalyst」OR「需 24h 內最新」才跑 fetch.py
- 若 `data_quality.sparse: true` AND `analyst_actions: []` → subagent 可 ≤ 1 次 web search 補 narrative，但 **數字仍以 fetch.py 回傳為準**

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

### Step 3.5 — FTD Timeline Gate（V4.9 新增 — BUG-006 follow-up）

**動機**：Phase 0 的 `ftd.exposure_range` 給出總體曝險上限（如 `75-100%`），但**忽略了一個 ticker 是在 FTD 後第幾天進場**。O'Neil 統計：FTD 後第 1-5 天進場的 cyclical leaders 勝率最高，第 13 天才出現的 setup 屬「補漲」性質，失敗率約 2x。本 gate 把這個時間軸資訊變成具體乘數。

**適用前提**：`phase0.ftd.state == "FTD_CONFIRMED"` 且 `phase0.ftd.days_since_ftd != null`。其他狀態（RALLY_ATTEMPT / NO_SIGNAL / FTD_INVALIDATED）此 gate 跳過（multiplier=1.0）。

**Sector 分類**（cyclical / defensive — 沿用 sector protocol Phase 1 cyclical_or_defensive 欄位）：
- **Cyclical**: Technology, Industrials, Materials, Financials, Consumer_Discretionary, Energy, Communication
- **Defensive**: Utilities, Consumer_Staples, Healthcare, Real_Estate

**Lookup 表**：

| `days_since_ftd` | Stage（內部 enum）| Cyclical multiplier | Defensive multiplier | 停損調整 |
|---|---|---|---|---|
| 1-5 | `prime` — Prime entry window | × 1.0 | × 1.0 | 標準 |
| 6-12 | `standard` — Standard window | × 0.90 | × 1.0 | 標準 |
| 13-20 | `late_cycle` — Late cycle / distribution risk | **× 0.75** | × 0.95 | **-1%（cyclical only）** |
| 21+  | `exhausted` — FTD exhausted / Stage 2 mature | **× 0.50** OR reject | × 0.85 | **-2%（cyclical only）** |

**Day 21+ reject 條件**（cyclical only）：
- IF `RS_rating < 90` OR `phase2.technical.distance_from_50ma > 15%` → 標 `decision = REJECT`，理由 `ftd_exhausted_late_entry`
- ELSE `multiplier = 0.50`（仍允許但極少量）

**輸出**：`ftd_timeline_gate` 區塊（見 Step 4 schema）

---

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

# FTD Timeline Gate（V4.9 — Step 3.5 lookup 結果套入）
ftd_adj = burry_override_adj × ftd_timeline_multiplier  # 1.0 / 0.95 / 0.90 / 0.75 / 0.50

IF final_decision = STAGED_ENTRY:
  final_position_size = ftd_adj × 0.5
ELSE:
  final_position_size = ftd_adj

# 停損套用 ftd_timeline 加扣 pp（cyclical only），上限不超過 -10%
final_stop_loss_pct = base_stop_pct + ftd_timeline_stop_adjustment
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
    "ftd_timeline_gate": {
      "applied": "bool — true iff phase0.ftd.state == 'FTD_CONFIRMED' AND days_since_ftd != null",
      "days_since_ftd": "int | null — 從 phase0.ftd.days_since_ftd 帶入",
      "stage": "prime | standard | late_cycle | exhausted | n/a",
      "sector_class": "cyclical | defensive",
      "multiplier": "1.0 | 0.95 | 0.9 | 0.75 | 0.5",
      "stop_loss_adjustment_pp": "0 | -1 | -2 — 額外加扣 pp（cyclical only）",
      "rejection_triggered": "bool — true iff stage=exhausted AND cyclical AND (RS<90 OR distance_50ma>15%)"
    },
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
