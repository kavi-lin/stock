# Multi-Agent Investment Protocol (V5.0)

> US equity single-ticker analysis. **Execution-only file** — historical changelog/rationale see `CHANGELOG.md`. Bundle schemas see `protocol_appendix_fmp_bundles.md`. Session export schema see `phase5_export_schema.md`.

---

## SESSION STARTUP

```
SESSION CONFIG
RISK_TOLERANCE : LOW | MEDIUM | HIGH   (預設 MEDIUM)
```

Ticker 由 user 指定。**非互動模式**（Dashboard reverse-call via `claude -p`）：所有需要 user input 的點皆採 protocol 預設，不停下等候。

---

## GLOBAL RULES (PM cheatsheet)

### MUST
1. **Phase order**: 0 → 1 → 2 → 2.4 → 2.5 → 2.8 → 3 → 4 → 4.5 → 5。不跳過。（2.4 = price framework engine，V3.45.3）
2. **Skill execution (NO SIMULATION)**: 凡標 **MUST run** 的 skill 指令必須實際執行 Bash 呼叫並解析 JSON 輸出，**禁止** LLM 估算 / 模擬數值。受規則約束的 skill：
   - `market-sentiment-analyzer`, `us-stock-analysis`, `market-news-analyst`, `technical-analyst`, `short-contrarian-analyst`, `portfolio-risk-manager`, `tail-risk-analyzer`, `fred-macro`
   - 失敗時必須在 final report 標 `skill_execution_failed: true` + stderr，禁止靜默用估算值補上。
3. **Parallel subagent (Phase 2)**: 5 lane 必須在**單一訊息內**以 5 個 Agent tool_use blocks 平行呼叫（subagent_type: "general-purpose"）。每個 subagent JSON 必須含 `subagent_isolated: true`；缺則 confidence cap 0.6 + `subagent_validation_failed: true`。
4. **Red Team (Phase 2.8)**: 必須以 Agent tool 呼叫 subagent 執行，**禁止 inline 推理代替**。
5. **MD Report (Phase 5)**: 存 `reports/YYYYMMDD_TICKER.md`。**不得省略**。
6. **Phase 0 cache**: 三層優先（FRESH = mtime < 3h）— L1 sector_intel → L2 invest_logs phase0 → L3 skill chain。
7. **Validate gates rc=0**:
   - Phase 0: `validate_phase0.py --ticker <T>`
   - Phase 5: `validate_session_export.py` + `validate_markdown_export.py`

### MUST NOT
- ❌ Phase 2 subagent prompt 含其他 lane 的 score / signal / reasoning
- ❌ Phase 2 subagent prompt 含 PM 的 historical_bias / active_weights / prior session
- ❌ 跨 lane 引用 PEER_BUNDLE / EARNINGS_ANALYST_BUNDLE / FMP_SUPP_BUNDLE 的數字推測對方結論
- ❌ Sonnet MD formatter 重新評分 / 改 score / 改 decision / 改 position size
- ❌ Final Score 用 `/5.0` 或 `/10` scale（V1.88 統一 `/3.0`）
- ❌ 為了補 cache 自動 enqueue `財報` protocol（user 主動觸發層）

### Output rules
- 邏輯輸出 JSON；Markdown 僅用於 Final Viz Table + Phase 5 MD report
- `key_factors`：最多 3 條，每條 ≤ 8 英文字
- 強制中文欄位：`watch_conditions` (description)、`key_risks`、`macro_context`、`red_team_counter_thesis`、`red_team_kill_conditions`

---

## TEAM STRUCTURE (V5.0 — 5 parallel lanes + 2 inline + 1 RT subagent)

| Agent | 模式 | Skill |
|---|---|---|
| Global News Intelligence | inline (Phase 0) | `market-news-analyst` |
| **Fundamentals Analyst** | **parallel subagent** | `us-stock-analysis` |
| **Sentiment Analyst** | **parallel subagent** | `market-sentiment-analyzer` |
| **News Analyst** | **parallel subagent** | `market-news-analyst` |
| **Technical Analyst** | **parallel subagent** | `technical-analyst` |
| **Valuation Specialist** (V5.0 新增) | **parallel subagent** | inline computation + EARNINGS_ANALYST_BUNDLE + PEER_BUNDLE |
| Contrarian (Burry) | inline (Phase 2 末) | `short-contrarian-analyst` |
| Red Team Adversary | subagent (Phase 2.8) | general-purpose |
| Trader Agent | inline (Phase 4) | — |
| Risk Manager | inline (Phase 4) | `portfolio-risk-manager`, `tail-risk-analyzer` |
| Portfolio Manager (PM) | inline (orchestrator) | — |

Burry 不參與 Phase 3 加權，僅作 T4 veto check。Valuation Specialist 參與加權但 weight 較輕（0.15）— 詳見 Phase 3。

---

## PHASE 0 — GLOBAL NEWS INTELLIGENCE

### 三層 cache (FRESH = mtime < 3h / 10800s)
1. **L1**: `../sector/sector_logs/*_sector_intel.json` 取最新檔 → 提取 `market_regime`, `exposure_ceiling`, `political_risk_summary`, `actionable_themes`, `_phase0.ftd.days_since_ftd` / `ftd_status_text` → Phase 1
2. **L2**: `./invest_logs/*_phase0.json` → 載入
3. **L3** (皆 STALE): 跑 4 個 skill chain：
   ```bash
   python3 skills/market-sentiment-analyzer/scripts/sentiment.py --json-only
   python3 skills/market-breadth-analyzer/scripts/market_breadth_analyzer.py --output-dir sector/breadth_cache/
   python3 sector/ftd_yfinance.py --output-dir sector/ftd_cache/
   python3 sector/market_top_yfinance.py --output-dir sector/market_top_cache/
   ```
   合成 + L4 FRED → 寫 `./invest_logs/YYYY-MM-DD_phase0.json`（`phase0_source: SKILL_CHAIN`）。≥ 2 skill 失敗 → fallback web search（`WEB_SEARCH_FALLBACK`）。

### L4 — FRED macro snapshot (MUST run, 任何層級皆執行)
```bash
python3 skills/fred-macro/scripts/fetch.py --json-only
```
> 讀取輸出前必讀 `skills/fred-macro/SECTOR_ROTATION_GUIDE.md`

寫入 phase0 JSON 的 `fred_snapshot`。失敗 → `fred_available: false`，protocol 繼續。

### Phase 0 JSON shape (核心欄位)

```json
{
  "phase": 0,
  "scan_date": "YYYY-MM-DD",
  "macro_summary": {
    "macro_backdrop_score": "float -5.0 to +5.0",
    "market_regime": "BULL | BEAR | SIDEWAYS | VOLATILE | RISK_OFF | RISK_ON",
    "regime_confidence": "0-1",
    "key_themes": [], "hot_sectors": [], "cold_sectors": []
  },
  "_market_signals": {
    "fear_greed_index": "float 0-100",
    "vix_current": "float", "vix_regime": "LOW|NORMAL|ELEVATED|CRISIS",
    "spy_rsi_14": "float", "spy_pct_above_ma200": "float",
    "breadth_composite": "int 0-100",
    "ftd_status": "FTD_CONFIRMED|RALLY_ATTEMPT|NO_SIGNAL|DISTRIBUTION",
    "ftd_days_since": "int",
    "market_top_score": "int 0-100",
    "top_catalysts": "[{date, ticker?, headline, source}]"
  },
  "fred_available": "bool",
  "fred_snapshot": { /* 12 series, see fred-macro skill */ },
  "phase3_macro_multiplier": "float",
  "macro_multiplier_rationale": "string — LLM baseline + FRED caps applied",
  "systemic_backdrop": {
    "ai_bubble_proximity": null,
    "vix_regime": null,
    "fed_funds_regime": null,
    "version": "v0.1_stub"
  }
}
```

> **V3.17 NOTE — `systemic_backdrop`** (Codex v5 + Gemini review): added as schema
> stub only. Values stay `null` in this wave; future V3.18+ will populate
> `ai_bubble_proximity` (via `market-top-detector` + sector concentration metrics),
> `vix_regime` (from FRED VIXCLS percentile), and `fed_funds_regime` (FRED DFF /
> rate-cycle classifier). Stub exists now so downstream consumers can branch on
> presence of the field without breaking when values fill in.

### macro_multiplier (LLM baseline)

| macro_backdrop_score | baseline |
|---|---|
| ≥ +3 | 1.2 |
| +1 to +3 | 1.0 |
| -1 to +1 | 0.9 |
| -3 to -1 | 0.75 |
| < -3 | 0.6 |

### FRED blending caps (final = min(baseline, 觸發的所有 cap))

| 觸發條件 | cap |
|---|---|
| `yield_curve_inverted` (T10Y2Y < 0) | 0.75 |
| `credit_stress_elevated` (HY pctile > 75) | 0.85 |
| `financial_stress_above_avg` (NFCI > 0) | 0.9 |
| `real_rate_10y_estimate > 2.0` | 0.9 |

**Bonus**: baseline ≥ 1.0 且全 FRED clear（無倒掛、credit < 50、NFCI < 0、real_rate < 1）→ × 1.05（總 cap 1.25）。

### Validator gate (MANDATORY)
```bash
python3 investment/scripts/validate_phase0.py --ticker <TICKER>
```
rc ≠ 0 必須修正後重跑。

---

## PHASE 1 — CONTEXT + DATA BUNDLES

PM (inline)。Phase 1 結束前 PM **MUST** 取得 4 個 bundles 供 Phase 2 共享。

### FAST PATH（預設走這條 — 1 call 取代 ~13 個取數 turn）

```bash
python3 investment/scripts/phase1_factpack.py <TICKER> --out /tmp/<TICKER>_factpack.json
```

讀回 `/tmp/<TICKER>_factpack.json`（~2-3k token，deterministic 0-LLM）一次拿齊：
- `phase0`（L1 sector_intel / L2 invest cache 抽核心欄位）+ `phase0_source` + `phase0_validator_rc`
- `bundles.ticker_data_bundle.scoring`（15 scalar，已剝 `_audit`）
- `bundles.earnings_analyst_bundle` / `peer_bundle` / `fmp_supp_bundle`（appendix shape，fail-soft）

**判讀規則**：
- `phase0_source == "STALE_NEEDS_L3"` → 依 Phase 0 L3 重跑 skill chain（factpack 不跑重活），完成後再進 Phase 2。其餘值（`SECTOR_CACHE`/`INVEST_CACHE`）= phase0 FRESH，直接用。
- `phase0_validator_rc != 0` → 修正後重跑（同 Validator gate）。
- 任一 `bundles_loaded[*]` 非 ok → 該 lane 走原 fallback 規則（見下表 + appendix），**不**中止 protocol。
- factpack 為**唯讀聚合**，不寫 history、不評分。若它失敗，回落手動逐 bundle（下方摘要 + appendix）。

> ⚠️ 仍須遵守 Physical isolation：注入 lane 時只貼該 lane 對應欄位，禁貼整包 factpack 給單一 lane（會 cross-anchor）。

### Bundle 摘要（詳細 schema 與 injection rules → `protocol_appendix_fmp_bundles.md`；factpack 失敗時的手動 fallback）

| Bundle | Source | Cost | Lane 注入 |
|---|---|---|---|
| `TICKER_DATA_BUNDLE` | `bash skills/finnhub-client/scripts/run_dual_fetch.sh --tickers <T>` → 讀 `scoring.*` (15 scalar) | 1 dual_fetch / session | All 5 lanes |
| `EARNINGS_ANALYST_BUNDLE` | 讀 `skills/earnings-analyst/cache/<T>_*.json` (≤ 90d) — V3.17 加 `transition_signature` / `business_mix_shift_overlay` / `cash_conversion_quality` / `working_capital_diagnostics` | 0 FMP call | Fundamentals + **Valuation Specialist** + Phase 3 penalty cascade |
| `PEER_BUNDLE` | `from skills._shared.company_context import get_peers, get_profile` | 2-7 FMP, 24h cache | Fundamentals + Burry + **Valuation Specialist** |
| `FMP_SUPP_BUNDLE` | `from skills._shared.fmp_supplementary import get_supplementary_bundle` | 2-9 FMP, 24h cache | 視 lane 而定（見 appendix） |

### Physical isolation (核心契約)
- ❌ 禁讀 `bundle["_audit"]` 欄位（dual_fetch isolation）— 違規 → 當前 ticker 分析作廢，重啟 Phase 1
- ❌ Bundle 純讀，禁改寫
- ❌ Cross-lane anchoring：lane prompt 不得含「其他 lane 看到什麼」
- ❌ PM 在 Phase 2.5 conflict resolution 不得引用 bundle 數字作裁量

### Phase 1 output

```json
{
  "phase": 1,
  "phase0_source": "SECTOR_CACHE | INVEST_CACHE | FRESHLY_EXECUTED | WEB_SEARCH_FALLBACK",
  "bundles_loaded": {
    "ticker_data_bundle":     "ok | unavailable",
    "earnings_analyst_bundle":"ok | not_available",
    "peer_bundle":            "ok | insufficient_peers | unavailable",
    "fmp_supp_bundle":        "ok | unavailable"
  },
  "active_weights": {
    "Fundamentals": 0.25, "Sentiment": 0.15, "News": 0.20,
    "Technical": 0.25, "Valuation": 0.15
  }
}
```

> `historical_bias`、`adjustment_strategy`、`active_weights` 為 PM 層 state，**禁止傳入** Phase 2 subagent prompt。

---

## PHASE 2 — 5-LANE PARALLEL SUBAGENT FAN-OUT

PM 以**單一訊息**平行呼叫 5 個 Agent subagent（Fundamentals / Sentiment / News / Technical / Valuation Specialist），等 5 個結果回傳後進入 Phase 2 末段（Burry inline）與 Phase 2.5。

### Model 分層（V4.0.0 — 成本治理）

| Subagent | Agent tool `model` 參數 | 理由 |
|---|---|---|
| **Sentiment / News / Technical** | `"sonnet"` | rubric 明確的結構化抽取+評分；品質哨兵 = det_shadow agreement + lane score 分布（`shadow_report.py` 監測） |
| Fundamentals / Valuation Specialist | 不指定（inherit session model） | 判斷較重，第二批降級候選 — 第一批 10 session 哨兵無異常後再議 |
| Red Team (Phase 2.8) | 不指定（inherit） | 對抗性推理 = 核心價值，**永不降級** |
| Sonnet MD Formatter (Phase 5) | `"sonnet"`（既有） | validator gate 兜底 |

> 第一批降級後**前 10 個 session** 盯 `shadow_report.py` lane 哨兵段：任一降級 lane 的 score
> 分布 vs 歷史明顯偏移、或 agreement 異常率升 → 該 lane 改回 inherit 並記 SESSION_NOTES。

### 共通 Subagent Prompt 模板

```
You are the <LANE> analyst for ticker <TICKER>.

ISOLATION CONTRACT:
  - 你與其他 4 個 analyst 以獨立 context 平行執行。
  - 你看不到其他 analyst 的 score / signal / reasoning。
  - 禁止推測其他 lane 的結論。
  - 禁止為了「與共識一致」調整自己的 score。
  - 禁止考慮 PM 的 historical_bias / active_weights / prior session。
  - score -5..+5 僅依據你本 lane 收集的證據。

TICKER: <TICKER>

PHASE 0 MACRO CONTEXT (read-only):
<paste Phase 0 macro_summary + _market_signals>

TICKER DATA BUNDLE (read-only, all 5 lanes):
<paste TICKER_DATA_BUNDLE.scoring; if unavailable 標 "TICKER_DATA_BUNDLE: unavailable">

[CONDITIONAL BUNDLES — 依 lane 注入規則; 見 protocol_appendix_fmp_bundles.md]

DATA SOURCE DISCIPLINE (STRICT):
  ❌ FORBIDDEN web search for: Quote/Valuation scalar (price/peRatio/forwardPE/peg/eps/mktCap/divYield/PB/D-E/FCF/ROE), Market signals (VIX/F&G/RSI/breadth/FTD/top score), Insider/short, Analyst rating/PT, Filings, OHLCV, news headlines (skill 已抓三來源)
  ✅ ALLOWED web search (≤ 1 call, narrative tone only): Reddit/X tone, transcript quotes, supply chain rumors, competitive narrative
  違規處理：subagent 引用 web search 的數字 → PM 自動扣 confidence 0.2；連 3 次 → 該 lane 視為 degraded

YOUR LANE RUBRIC:
<RUBRIC_LANE>

MANDATORY DATA COLLECTION:
<SKILL_CMD — MUST run, do NOT simulate>

OUTPUT (strict JSON):
{
  "phase": 2,
  "agent": "<LANE>_Analyst",
  "ticker": "<TICKER>",
  "signal": "BUY | SELL | HOLD",
  "score": "-5 to +5",
  "confidence": "0.0 to 1.0",
  "key_factors": ["max 3 items, ≤ 8 words each"],
  "risk_flags": ["max 2 items"],
  "phase0_alignment": "ALIGNED | MISALIGNED | NEUTRAL",
  "data_source_timestamp": "YYYY-MM-DD HH:MM",
  "subagent_isolated": true,
  "skill_execution_failed": "true | false"
}
```

### Lane Rubrics

#### Fundamentals Subagent
- **Rubric**: P/E vs sector/peer median, revenue YoY, FCF margin, D/E, next earnings date, analyst EPS growth。強訊號（FCF yield > 5% AND rev_growth > 20%）給 +3/+4。
- **Skill**: `python3 skills/us-stock-analysis/scripts/analyze.py <TICKER> --json-only`
- **Bundle 使用**：
  - `TICKER_DATA_BUNDLE.scoring.*` 為 15 scalar 權威來源；skill 輸出衝突 → 採 bundle，註記「以 dual-fetch canonical 為準」
  - `EARNINGS_ANALYST_BUNDLE.derived` (8Q margins / yoy_growth / cash_flow_quality) 為深層證據引用；`quality_flags` 觸發 → score ±1
  - `PEER_BUNDLE.peer_pe_median`：差異 > 30% → ±1；> 50% → ±2
  - `FMP_SUPP_BUNDLE.quality_scores`: `altman_zone == danger` → -1；`piotroski_strength == strong` → +1，weak → -1
  - `FMP_SUPP_BUNDLE.owner_earnings.qoq_growth`: > 0.15 → reasoning 註記；< -0.30 → -0.5
  - `FMP_SUPP_BUNDLE.employee_history` (V5.0): 5Y CAGR > 15% → +0.5（持續擴張）；最近 1Y -5% → -0.5（裁員）
- **絕對禁止**: 把 `composite_score / verdict` 直接 mirror 為 lane score

##### V2.13.0 Fundamentals lane 額外輸出（必填，不影響 score 公式）

對應外部模板「真正強在哪 / 市場擔心什麼」+ moat + catalysts：

1. **`moat_assessment`**（必填）：`WIDE | NARROW | ERODING | NONE` + 1 行依據
   - 類型：brand / IP-patent / switching_cost / scale_economies / network_effect / regulation / 無
   - 例：「WIDE — 平台網路效應（active devs ≥ 25M, App Store 30% take rate 連續 5Y 穩定）」
   - 依據：peer 比較（PEER_BUNDLE）+ FCF margin trend + ROIC vs WACC（如可得）

2. **`near_term_catalysts[]`**（必填，3-5 筆）：每筆 `{date, type, description, impact}`
   - `type ∈ {earnings | guidance | product_launch | analyst_day | M&A | macro_event}`
   - `impact ∈ {high | medium | low}`
   - `date` 用 ISO `YYYY-MM-DD`；不確定用 `2026-Q3` 季度標記
   - 來源：EARNINGS_ANALYST_BUNDLE next_earnings + News bundle headlines + macro calendar
   - 例：`[{"date":"2026-08-15","type":"earnings","description":"Q3 FY26 財報","impact":"high"},...]`

3. **二元對偶 narrative**（必填）：
   - `bull_thesis_one_line`: 一句話「真正強在哪」（≤ 40 字，量化證據）
   - `bear_thesis_one_line`: 一句話「市場擔心什麼」（≤ 40 字，量化反駁）

> 以上**必填**；缺資料寫 `INSUFFICIENT_DATA` 而非 null。`bull/bear thesis` 是 narrative summary，不替代 lane score。

##### V2.17.0 Fundamentals lane TAM / Market Position 必填 sub-block

對應 reference equity-research/sector-overview pattern（market sizing layer）。Phase 2 Fundamentals subagent **必填**：

4. **`market_position`**（必填）：
   - `tam_usd`：Total Addressable Market 估算（USD billions），來源：公司 IR 投資人簡報 / sell-side primer / WebSearch（標 source link）
   - `industry_5y_cagr_pct`：產業未來 5y 預期 CAGR（%），來源同上
   - `company_revenue_share_pct`：公司營收佔 TAM 比例（公司營收 ÷ TAM × 100），算術可推
   - `position_label`：`leader | challenger | niche | follower`（依 market share + growth vs industry）
   - `competitive_moat_evidence`：1-2 句 — 為什麼 share 守得住 / 拿不下（pricing power / switching cost / scale），引 PEER_BUNDLE 數字
   - 例：
     ```json
     {
       "tam_usd": 350,
       "industry_5y_cagr_pct": 12.4,
       "company_revenue_share_pct": 18.5,
       "position_label": "leader",
       "competitive_moat_evidence": "scale economies — capex/rev 17% vs peer median 9%（PEER_BUNDLE），3 年內無 challenger 能複製"
     }
     ```

> **資料缺失處理**：TAM / CAGR 找不到第三方來源 → `tam_usd: null` + reasoning 註記「TAM 數據缺失，share 估算降級為 revenue rank in peer set」。**禁止**用 LLM 自己編 TAM 數字。
> **不重複 sector_protocol**：sector_protocol 給 sector 層 valuation / breadth；本 block 給**個股**在 sector 內的位置。兩者互補不矛盾。

#### Sentiment Subagent
- **Rubric**: 市場層 + 個股層融合 → `Sentiment Score = 0.5 × stock_specific + 0.5 × (market_composite/10 − 5)`
- **Market layer**: 優先讀 Phase 0 `_market_signals`（fear_greed / vix / spy_rsi / breadth）— 不重跑
- **Stock layer skill**: `python3 skills/market-sentiment-analyzer/scripts/sentiment.py --ticker <TICKER> --json-only`
  - `insider_stats[]` 4 季：`acquired_disposed_ratio` < 0.3 → -1；> 1.0 → +1
  - `insider_sentiment.latest_mspr`: > +30 → +1；< -30 → -1
  - `short_pct_float`: > 20% → -2；10-20% → -1；< 5% → +1
- **FMP_SUPP_BUNDLE 規則**：
  - `institutional.accumulation_signal == accumulating` → +1，`distributing` → -1
  - `congressional_trades.net_signal == bullish` → +0.5，`bearish` → -0.5
  - `executive_compensation` (V5.0): CEO comp YoY > 30% → reasoning 註記治理紅旗；SBC > 15% revenue → -0.5
- 額外輸出: `market_sentiment_composite`, `vix_current`, `insider_signal`, `short_pct_float`, `mspr_latest`

#### News Subagent
- **Rubric**: 過去 48h company news + analyst rating changes + PT trend + cross-ref Phase 0 themes
- **Skill**: `python3 skills/market-news-analyst/scripts/fetch.py <TICKER> --hours 48 --json-only`
- 結構化欄位（**禁止** web search 重抓 analyst rating / target 數字）：
  - `analyst_actions[]` (FMP `/grades-historical` 過去 30d)
  - `analyst_consensus`: Strong Buy +1.5 / Buy +1 / Hold 0 / Sell -1 / Strong Sell -2
  - `pt_revision_momentum` (V3.45.4 — 取代舊「PT vs price 折溢價 ±1」項): 30d consensus PT
    **變動方向**。`direction=UP` 且 `delta_1m > +3%` → bullish sell-side flow（同 rating change 性質，+0.5~+1）；
    `DOWN` 且 `delta_1m < -3%` → bearish（-0.5~-1）；`FLAT/UNKNOWN` → 0
  - `analyst_news[]` (FMP `/grades-news`)
  - `headlines[]` (finviz + yfinance + Finnhub deduped)
  - `sec_filings_recent[]` + `sec_8k_filings[]` (30d)
- **優先檢查 Phase 0 `_market_signals.top_catalysts[]`** 避免重抓
- `FMP_SUPP_BUNDLE.ma_events.events[]` 非空 → 強訊號（target 通常 +1）

> **V3.45.4 — PT 注入層剝離（去三重計分）**：PT consensus **level** 已在 Valuation anchor
> (0.20) + MHP 60d `pt_60d` (0.35) 計分兩次；News lane 再比 level vs price 是第三次（cross-lane
> anchoring，共識牛市系統性放大多頭）。`fetch.py` V3.45.4 起 payload **不含任何絕對 PT level**
> （`price_target` block 已移除，只給 `pt_revision_momentum` 方向+幅度%）。**禁止**：在 News lane
> prompt 額外注入 PT level、或 reasoning 中以「PT 折價/溢價 X%」「目標價 vs 現價」計分 —
> 後驗由 `apply_det_shadow.py` `news_pt_leakage` keyword classifier 抓（warning 級，累積統計）。

##### V2.13.0 News lane 額外輸出（必填，不影響 score 公式）

對應外部模板「利多 / 利空 / 下一步」三段時間軸 + 跨資產溢出：

1. **`immediate_catalyst_5d`**（必填）：物件或 null
   - 5 天內 binary 事件（earnings / FOMC / FDA / 重大公告）
   - shape: `{event: str, date: ISO, direction_lean: BULLISH|BEARISH|NEUTRAL, expected_move_pct: float|null}`
   - 例：`{"event":"Q2 earnings", "date":"2026-08-13", "direction_lean":"BULLISH", "expected_move_pct": 5.5}`
   - 無 5d 內 binary 事件 → null

2. **`medium_term_shift_20d`**（必填）：1 句話 + label
   - 5-20 天可能 narrative 移轉（規則調整、產品 cycle 拐點、macro pivot 預期）
   - shape: `{narrative: str, label: BULLISH|BEARISH|NEUTRAL}`
   - 無顯著拐點 → `{"narrative": "no significant shift expected", "label": "NEUTRAL"}`

3. **`decision_point_days`**（必填）：int
   - 下次該重新評估的天數（用於 watch_conditions 的 review trigger）
   - 通常 = 最近 binary 事件距今天數；若無 binary，預設 21
   - 例：14（下次財報）、5（下次 FOMC）、21（無 binary，例行 review）

4. **`cross_asset_spillover[]`**（必填）：受影響的非個股市場
   - shape: `[{asset: str, direction: BULLISH|BEARISH|NEUTRAL, mechanism: str}]`
   - asset 例：`treasury_10y / DXY / oil_WTI / gold / copper / sector_XLK / VIX`
   - mechanism 1 句話解釋傳導路徑
   - 至少 1 筆；若該股新聞純個股無溢出，明示 `[{"asset":"none","direction":"NEUTRAL","mechanism":"news 純個股財務，無跨資產傳導"}]`
   - 例：`[{"asset":"treasury_10y", "direction":"BEARISH", "mechanism":"AI capex 預期 → cyclical 通膨壓力 → 殖利率上行"}]`

5. **`reasoning_one_line`** + **`key_factors[]`**（V3.45.4 必填，持久化進 export）：
   - `reasoning_one_line`: 1 句 — News score 的核心依據
   - `key_factors[]`: 2-4 條短語 — 計分主因（與 Final Visualization Table 的 Key Factors 同源）
   - **用途**：history.json 持久化後供 `apply_det_shadow.py` `news_pt_leakage` classifier 掃描
     （V2.19 red_team_basis 同模式 — 沒有落地文字，後驗防線就沒有 haystack）

> 以上 5 個欄位**必填**；缺資料寫 `INSUFFICIENT_DATA`（陣列用 `[]` + 註記）。

#### Technical Subagent
- **Rubric**: 20/50/200MA 結構、RSI(14)、MACD histogram、volume vs 20D avg、support/resistance。Stage 2 上升結構 → +3+；跌破 200MA + 量放大 → -3-
- **Skill**: `python3 skills/technical-analyst/scripts/analyze.py <TICKER> --json-only`
- OHLCV-only lane，但 V2.13 起額外讀 FMP_SUPP_BUNDLE.insider_summary 做主力分析（見下）

##### V3.17 (Wave 1) — Large-cap parabolic ceiling

當 `momentum-monitor` 輸出 `warnings` 含 `large_cap_parabolic` (marketCap > $10B AND
above_ma200_pct > 100) 時 Technical lane:
- `raw score ceiling = +1`(就算 trend / pattern / smart money 都偏多,score 也不得 > +1)
- 必填 narrative `extension_penalty_note`: 1 句說明為何 large-cap parabolic 蓋頂(crowded trade、回測 SMA50 平均 -30%、historical R/R 不對稱)
- 設計理由(Codex v5):大型股 +100% above SMA200 的 R/R 跟小型股 不同 — 全市場可見 → 散戶 FOMO 已到、回檔深度通常更大。Technical 不能因 Stage 2 / golden cross 給滿分

##### V2.13.0 Technical lane 額外輸出（必填，不影響 score 公式）

對應外部模板「主力吸籌/出貨」+「型態分類」+「強弱/關鍵價/劇本」三件套：

1. **`smart_money_analysis`**（必填）：1-2 句敘述 + 一個 label
   - label: `accumulating | distributing | neutral | mixed`
   - 依據綜合：
     - `FMP_SUPP_BUNDLE.insider_summary.quarters[0].acquired_disposed_ratio`（< 0.3 distributing；> 1.0 accumulating）
     - `quote.volume vs avgVolume` 量價背離（量放大 + 跌 = distributing；量放大 + 漲 = accumulating）
     - `analyst_actions[]` 30d 升降評淨值（≥ +3 = accumulating sell-side flow；≤ -3 = distributing）
     - 若 institutional 訊號（V2.9.0 sector intel `institutional_holders_qoq_delta` 該股可用）正負一致 → 強化判斷
   - 例：「insider Q ratio 0.06 重度賣超 + 機構 13F holders QoQ −12 + sell-side 30d 淨降評 −2 → distributing」

2. **`pattern_taxonomy`**（必填，從 8 種選一）：
   - `uptrend_breakout` / `uptrend_continuation` / `consolidation` /
     `pullback_in_uptrend` / `false_breakout` / `topping_pattern` /
     `downtrend` / `oversold_bounce_attempt`
   - 必附 `confirmation_criteria`（1 句）：什麼條件代表 pattern 成立或失效
   - 例：「pattern: pullback_in_uptrend；confirmation: 站穩 50MA $118 且收回 5MA 上方 → 持續上升；跌破 $115 + 量 > 1.5×avg → 降為 false_breakout」

3. **三件套 output**（必填）：
   - `market_strength`: `STRONG | NEUTRAL | WEAK` （盤面強弱單字判決）
   - `key_levels`: `{support: float, resistance: float, pivot: float}` （三個關鍵價位；缺項用 null）
   - `high_prob_scenario`: 1 句話描繪未來 5-15 天最有機率的走法（明確帶價位 + 觸發條件）
     例：「站穩 $122 pivot + 量 ≥ 1.5×20D avg → 突破上攻 $135；跌破 $115 → 回測 $108 200MA」

4. **`volatility`**（V5.1 必填，deterministic — 餵 Phase 4.5 Multi-Horizon Price Framework 5-Day Band）：
   - `atr_14`: FMP `technicalIndicators` ATR period 14（float；缺 → null）
   - `hist_vol_20d_daily`: 20D 日報酬標準差（小數，e.g. 0.028；FMP `technicalIndicators` standardDeviation period 20，或 20D close 序列算）。缺 → 用 `atr_14 / current_price` 反推
   - `momentum_20d_pct`: 20 交易日報酬 %（(price / close_20d_ago − 1) × 100；float）
   - 三值皆**直接寫入原始數字**，LLM **不**重新判讀；缺料寫 null（Phase 4.5 自動降級，不擋）

> 以上 4 區塊**必填**；1-3 區塊資料缺寫 `INSUFFICIENT_DATA`，volatility 缺寫 null。LLM 不得跳過。

#### Valuation Specialist Subagent (V5.0 NEW)
- **角色**: 純估值錨點專家。獨立於 Fundamentals lane（後者偏品質 + 成長），這層專注「現價 vs 多錨點合理價」
- **Rubric**: 收集 6 個估值 anchor，計算 ticker `current_price` 與加權平均合理價的折/溢價：
  - 折價 > 30% → score +3 (extreme undervalued)
  - 折價 10-30% → +1 to +2 (undervalued)
  - ±10% → 0 (fairly valued)
  - 溢價 10-30% → -1 to -2 (overvalued)
  - 溢價 > 30% → -3 (extreme overvalued)
- **Anchors（從現有 bundle 抽，0 額外 FMP call）**：
  | Anchor | 來源 | Weight |
  |---|---|---|
  | `dcf_unlevered` | `EARNINGS_ANALYST_BUNDLE.valuation.dcf_intrinsic` | 0.30 |
  | `dcf_levered` | `EARNINGS_ANALYST_BUNDLE.valuation.dcf_levered_intrinsic` | 0.15 |
  | `analyst_pt_consensus` | `EARNINGS_ANALYST_BUNDLE.valuation.price_target_consensus` | 0.20 |
  | `peer_pe_implied` | `PEER_BUNDLE.peer_pe_median × TICKER_DATA_BUNDLE.scoring.epsTTM` | 0.20 |
  | `owner_earnings_mult` | `FMP_SUPP_BUNDLE.owner_earnings.ownersEarnings × 15` (default Buffett multiple) | 0.10 |
  | `forecaster_blend` | `python3 skills/earnings-valuation-forecaster/scripts/forecast.py <T> --json-only` (3-method blend) | 0.05 |
- **缺 anchor 處理**: 對應 weight 重分配給其他 anchor；< 3 anchor 可用 → confidence cap 0.5
- **論述格式**: 必須引用具體 anchor 數字，e.g.「DCF $155 / FCFE $148 / PT consensus $325 / Peer-implied $200 → 加權合理價 $215，現價 $285 = 32.5% premium → score -3」
- **絕對禁止**: 直接 mirror Fundamentals 的 P/E judgment；本 lane 是獨立估值維度
- 額外輸出: `valuation_anchors{}` (6 anchor 數字), `weighted_fair_value`, `vs_current_pct`

##### Reverse DCF `implied_expectations`（engine 產出，Specialist 不算）

現價隱含 5Y FCF CAGR vs 實際 vs lane 估 — falsifiable sanity check + Red Team 彈藥。
由 **Phase 2.4 engine 計算**（Specialist 只負責 anchors；演算法 / clamp / WACC fallback 見
`protocol_appendix_price_framework.md`）。**不進**加權 / lane score / decision_lock。
Red Team subagent 收 `red_team_kill_seed` 當 kill condition 起點。shape 見 schema。

##### V3.17 (Wave 1) 新增必填欄位 — Transition case dissent_basis

當 `EARNINGS_ANALYST_BUNDLE.transition_signature ∈ {paradigm_only, mix_only, both}`
**或** `forecaster.transition_case is True` 時,Valuation Specialist 必須額外輸出:

```json
{
  "cited_transition_overlay": true | false,
  "transition_dissent_basis": "macro_systemic" | "thesis_fundamental" | "valuation_anchor" | null
}
```

- `cited_transition_overlay`: 是否在 narrative 內引用 `transition_signature` 或
  `forecaster.revenue_margin_matrix`(EMERGING / ESTABLISHED 任一)
- `transition_dissent_basis`: 當 `lane_score < 0` 時 **必填** (null 視同 `thesis_fundamental` 保守處理):
  - `macro_systemic`: 負分主因 = 大盤 multiples 壓縮 (高利率 / regime stagflation),非 transition 本身
  - `thesis_fundamental`: 負分主因 = transition thesis 本身存疑 (segment growth 不可持續、margin 路徑不通)
  - `valuation_anchor`: 負分主因 = 歷史 PE / DCF 等 anchor 給出明顯失真結論
- `lane_score >= 0` 時 dissent_basis 可填 null

此欄位被 Phase 3 Step 2 `valuation_confirmed_transition` gate 消費 (V3.17 — Gemini G4 乾淨方案,`lane_score` 不再是 gate)。

### Fan-Out 執行（PM 層）

```
[single assistant turn, 5 tool_use blocks in parallel]
  Agent(description="Fundamentals analyst",  subagent_type="general-purpose", prompt="<fund prompt>")
  Agent(description="Sentiment analyst",     subagent_type="general-purpose", prompt="<sent prompt>")
  Agent(description="News analyst",          subagent_type="general-purpose", prompt="<news prompt>")
  Agent(description="Technical analyst",     subagent_type="general-purpose", prompt="<tech prompt>")
  Agent(description="Valuation specialist",  subagent_type="general-purpose", prompt="<val prompt>")
```

### Fan-In 驗證 + Inline Fallback

| 情境 | 處理 |
|---|---|
| 單一 subagent 失敗 / malformed JSON | retry 1 次；仍失敗 → PM inline 該 lane；`subagent_execution_failed: true`，confidence cap 0.6 |
| 2-4 subagent 失敗 | 失敗者 inline；`mode = PARTIAL_FALLBACK` |
| 5 個全失敗 | `mode = FULL_FALLBACK` + `degraded_mode: true`；Red Team 強制 `STRONG_COUNTER` |

寫入 `phase2_fanout_summary`:
```json
{
  "mode": "PARALLEL_SUBAGENT | PARTIAL_FALLBACK | FULL_FALLBACK",
  "subagent_successes": 5, "subagent_failures": 0,
  "degraded_analysts": [],
  "fanout_started_at": "ISO", "fanout_completed_at": "ISO"
}
```

---

## PHASE 2 末段 — CONTRARIAN (BURRY, inline)

執行在 Fan-In 完成後。Burry 是 deterministic skill output，不受 anchoring 影響。

```bash
python3 skills/short-contrarian-analyst/scripts/burry_score.py <TICKER> --json-only
```

取回 `burry_score (0-100)`、`verdict`、`components`。

### Verdict → Phase 4 影響

| Verdict | Score | Phase 4 影響 |
|---|---|---|
| `T4_VETO` | < 20 | 強制 HOLD，Phase 4 不執行倉位計算 |
| `WARNING` | 20-35 | Phase 4 final × 0.7 |
| `NEUTRAL` | 35-60 | 無調整 |
| `VALUE_BONUS` | ≥ 60 | Phase 4 final × 1.15 |

### Burry 加分／減分規則（從 PEER_BUNDLE / FMP_SUPP_BUNDLE / EARNINGS_ANALYST_BUNDLE 讀）

任何單一規則 ±2 上限。所有調整必須在 `burry_voice` 留可追溯字串。

1. **Altman Z-Score** (`quality_scores.altman_zone`): danger → -2，grey → -1，safe → 0
2. **Piotroski F-Score** (`piotroski_strength`): strong → +1；weak → reasoning 註記不調 score
3. **Owner Earnings vs GAAP FCF** (`owner_earnings.ownersEarnings` vs `cash_flow[0].freeCashFlow`): 差距 > 30% → narrative 註記，不調 score
4. **Insider trend** (`insider_summary.latest_trend`): accumulating + `component_scores.insider == 0` → narrative 註記正向背離；distributing → narrative 註記
5. **DCF FCFF vs FCFE 差距** (`dcf_intrinsic` vs `dcf_levered_intrinsic`): 差 > 20% → narrative 加註資本結構警告，不調 score
6. **Comp benchmark** (V5.0, `comp_benchmark.ceo_vs_peer_pct`): CEO comp > peer median 200%+ → narrative 治理紅旗
7. **PEER_BUNDLE mispricing** (V4.10): `EV/EBIT > peer_median × 1.5` 或 `fcf_yield < peer 中位數一半` → narrative 加註，不調 score

```json
{
  "phase": 2, "agent": "Contrarian_Analyst_Burry",
  "ticker": "STRING",
  "burry_score": "0-100",
  "verdict": "T4_VETO | WARNING | NEUTRAL | VALUE_BONUS | UNKNOWN",
  "components": { "fcf_yield_pct", "ev_ebit", "debt_to_equity", "pct_below_52w_high", "insider_net" },
  "component_scores": { "fcf_yield", "ev_ebit", "debt_to_equity", "pct_below_52w_high", "insider" },
  "burry_voice": "string — 含所有規則調整理由",
  "veto_flag": "true if score < 20"
}
```

`veto_flag = true` → 觸發 Phase 2.5 T4。

---

## PHASE 2.4 — PRICE FRAMEWORK ENGINE (V3.45.3 NEW)

PM (inline，一個 Bash call)。Phase 2 Fan-In 後所有估值輸入已備齊
（anchors / volatility / key_levels / pattern / catalyst / FRED / owner earnings）。
PM 組 input JSON 後呼叫 deterministic engine，**禁止手算任何 framework 數字**：

```bash
# input：Phase 2 Valuation Specialist anchors + technical_lane key_levels/pattern/smart_money
#        + news_lane immediate_catalyst_5d + Phase 0 FRED + owner earnings per share
#        + V3.46.0 archetype shadow 用：archetype_inputs{sector,revenue_yoy,fcf_margin,eps_ttm,
#          margin_sigma_pp} + peer_ratios（PEER_BUNDLE 新 median 欄）+ self_ratios（PEER_BUNDLE
#          self_ratios_ttm）+ ev_block{enterprise_value,net_debt,shares}（earnings bundle）+ beta
#
# V3.48.0 — 標準跑法：--self-assemble。quant 欄位（anchors / ev_block / archetype_inputs /
# peer_ratios / self_ratios / beta / fred real rate / fcf base）由 engine 直接讀
# earnings cache + peer bundle + supp bundle + forecaster cache + phase0 自組，
# **0 LLM 抄寫**。PM 的 input file 只需給 qualitative 欄（pattern_taxonomy / smart_money_label /
# key_levels / immediate_catalyst_5d）+ ticker；file 給的欄位永遠優先。
# 輸出 self_assembled_fields[] 供 audit。
python3 investment/scripts/compute_price_framework.py --from-file /tmp/<ticker>_pf.json --self-assemble
```

一次回傳 4 個 block：`fair_value_summary`（V5.0 blend，演算法 byte-identical）+ `fair_value_range` +
`multi_horizon_price_framework` + `implied_expectations`。PM **verbatim 抄寫**進後續 phase 輸出。
input 含 `ticker` 且未給 volatility 時，engine 自抓 FMP OHLCV 算 sigma/atr/momentum
（消除 LLM 抄寫風險）；`technical_lane.volatility` 仍必填（lane 呈現用），framework 計算以 engine 自算值為準。

**時點 2.4 的原因**：下游全是消費者 — T5 (2.5) 用 `mhp_signal`、Red Team (2.8) 收 `red_team_kill_seed`、Phase 3/4/4.5 引用既存輸出；且 engine 是唯一計算來源（迭代解/percentile 超出 LLM inline 可靠範圍）。

---

## PHASE 2.5 — CONFLICT & BIAS PROTOCOL

PM (inline)。**Triggers**:

- **T1**: `Sentiment.score > +3` AND `Fundamentals.score < 0`
- **T2**: `News.score < -3` AND `Technical.signal = BUY`
- **T3**: `macro_backdrop_score < -3` AND any `signal = BUY` with `score > +3`
- **T4**: `Burry.veto_flag = true` AND `tentative_decision = BUY`
- **T5 (V5.0)**: `Valuation.score ≤ -2` AND `tentative_decision ∈ {BUY, STAGED_ENTRY}` → 估值警告
- **Anti-Bias**: 5 lane 同向 → News 追加 `devils_advocate[]` (≤ 3 條)

### T4 仲裁
（burry_score 為 0-100 刻度；T4 觸發 = `veto_flag`，即 score < 20）
- `burry_score < 10` → 強烈建議 `CANCEL`
- `burry_score 10-19` → `DOWNGRADE_DECISION` (BUY → HOLD) 或 `OVERRIDE_BURRY`
- `verdict = UNKNOWN`（資料不足，score=null）→ 不觸發 T4，narrative 註記資料缺口
- 選 `OVERRIDE_BURRY` 自動三項成本：
  1. Phase 4 倉位 × 0.5 (`burry_override_multiplier`)
  2. 必填 `override_justification` (≥ 20 字，具體引用 Phase 2 某 analyst 證據)
  3. 自動計算 `override_recheck_date` = 交易日 + 5 個交易日

### T5 仲裁 (V5.0)
- `Valuation.score = -2`: reasoning 加注「估值警告 (溢價 {pct}%)」，不強制 downgrade
- `Valuation.score = -3` (extreme overvalued): **自動 downgrade BUY → STAGED_ENTRY**；STAGED_ENTRY → HOLD
- **V5.1 MHP 強化（reasoning-only，不改決策數學；V3.45.3 起 `mhp_signal` 由 Phase 2.4 engine 產出，T5 當下直接可用）**：
  - `wait_for_pullback`（短期帶下界 > 長期合理價）→ T5 reasoning 追加「短期超漲 vs 長期偏貴 (band_lower ${bl} > FV ${fv})，建議等回檔」
  - `momentum_not_value`（mid_target > 現價 > 長期合理價）→ 對齊既有 `hot_zone_probe` 語意（動能交易非價值持有）

```json
{
  "phase": "2.5",
  "triggers_fired": ["T1", "T4", "T5"],
  "conflict_summary": "one sentence per trigger",
  "t4_detail": { /* burry_score, resolution, justification, recheck_date */ },
  "t5_detail": {
    "valuation_score": "float",
    "weighted_fair_value": "float",
    "vs_current_pct": "float",
    "downgrade_applied": "bool"
  },
  "proceed_to_phase3": "bool"
}
```

`proceed_to_phase3 = false` → 跳 Phase 5 輸出 `CANCEL`。

---

## PHASE 2.8 — RED TEAM ADVERSARIAL CHECK

Red_Team_Adversary 以 Agent tool 呼叫 subagent 執行（**禁止 inline**）。始終執行（除非 Phase 2.5 `proceed_to_phase3 = false`）。

**特例**: `phase2_fanout_summary.mode = FULL_FALLBACK` → 自動 `red_team_verdict = STRONG_COUNTER`，跳過 subagent。

### Subagent prompt 摘要

```
You are the RED TEAM. 任務：破壞 tentative consensus。

TICKER: <T>
TENTATIVE CONSENSUS DIRECTION: <BULLISH | BEARISH | MIXED>
PHASE 0 MACRO + FRED slim
PHASE 2 ANALYST OUTPUTS (6: 5 lanes + Burry)
STRUCTURAL_SHIFT_TIER: <NONE | CANDIDATE | CONFIRMED | INSUFFICIENT_DATA>     ← V2.19 NEW
IMPLIED_EXPECTATIONS: <Phase 2.4 engine implied_expectations，含 red_team_kill_seed>   ← V3.45.1 NEW (V3.45.3 改 engine 產出)

TASK:
1. 找共識最脆弱 1 個主論點 → counter_thesis (1-2 句)
2. 產 2-3 條 falsifiable kill_conditions: "IF <事件> WITHIN <天數> THEN <推翻論點>"
   - V3.45.1: 若 `implied_5y_fcf_cagr` 顯著高於 actual/lane 估 → 至少 1 條 kill_condition 用 `red_team_kill_seed` 為起點（隱含預期破滅型）
3. FRED 衝突挑戰：若 fred_snapshot 顯示衝突訊號（yield_curve_inverted / real_rate > 2.0 / credit_stress / regime ∈ {Late Cycle, Stagflation, Recession Risk} / sector ∈ rotation_avoid / NFCI accelerating）→ MUST 至少 1 條 kill_condition 引用具體 FRED 數值
4. counter_evidence_strength (1-5):
   1-2 = 找不到有力反論
   3 = 有風險但無確切反證
   4-5 = 有具體數據強烈反駁（FRED 衝突訊號 ≥ 2 個自動 ≥ 4）
5. verdict: ≤2 NO_VIABLE_COUNTER / =3 MODERATE_COUNTER / ≥4 STRONG_COUNTER

V2.19 — STRUCTURAL_SHIFT_TIER 條件指令 (anti-spoofing):
  IF STRUCTURAL_SHIFT_TIER = CONFIRMED:
    - MUST cite forward mechanism breakage in counter_thesis + kill_conditions:
      competitor capacity addition / customer inventory rebuild / demand saturation /
      technology substitution / share loss to next-gen
    - 禁止使用 mean-reversion 純歷史論證作為攻擊主線：
      "歷史均值 / 週期見頂 / Peak Cycle / 歷史毛利 / 回歸歷史中位"
    - 後驗 classifier (`classify_red_team_basis`) 偵測 mr 關鍵字 → STRONG_COUNTER 自動降級為 MODERATE_COUNTER
    - 即使搭配 1-2 個 forward 關鍵字 (contaminated)，仍視同 mr 觸發降級
  IF STRUCTURAL_SHIFT_TIER = CANDIDATE:
    - mr 論證仍可用但效力減半（penalty 0.85 → 0.925）
  IF STRUCTURAL_SHIFT_TIER = NONE / INSUFFICIENT_DATA:
    - 標準攻擊模式，無限制

V3.17 (Wave 1) — Cash conversion 攻擊限制:
  - 若 EARNINGS_ANALYST_BUNDLE.cash_conversion_quality == "clean_positive_gap":
    禁止用「OpCF >> NI 推論造假」作為攻擊路徑。clean positive gap 已通過
    DSO/DIO/DPO 4Q 二階校對 — 用 cash quality 攻擊 = 直接違反 deterministic
    flag,後驗 classifier 將自動把該 counter_thesis 視為 invalid。
  - 要攻擊 cash quality,必須引用 working_capital_diagnostics 內 ≥1 個 indicator
    (DSO/DIO/DPO)惡化 (rising trend + 最新 Q > 4Q_avg × 1.15)
  - 若 cash_conversion_quality == "wc_driven",可攻擊 cash quality,但需明確
    引用是哪一個 WC indicator 異常 (e.g. "DSO Q4 trend rising 117→138 + 最新
    Q 比 4Q avg 高 22% → revenue 認列鬆綁")

V3.17 (Wave 1) — transition_signature 攻擊指引:
  - 若 transition_signature ∈ {mix_only, both}:
    pure mean-reversion 攻擊仍可送,但 Phase 3 Step 2 cascade #2 會自動軟化到
    × 0.95 (前提 Valuation Specialist 也確認 transition,即 cited_transition_overlay
    == True AND transition_dissent_basis != "thesis_fundamental")
  - 鼓勵 pure_forward 攻擊主線(新對手 / 新技術 / 訂單下修 / margin thesis 證偽)
    — 這類攻擊維持 × 0.85 penalty,殺傷力最大
```

### Phase 3 影響對照

| red_team_verdict | red_team_basis (V2.19) | structural_shift.tier | Phase 3 Step 2 |
|---|---|---|---|
| `NO_VIABLE_COUNTER` | any | any | consensus bonus × 1.15 可觸發 |
| `MODERATE_COUNTER` | any | any | 無 bonus 無 penalty |
| `STRONG_COUNTER` | `pure_forward` / `unclassified` | any | raw_total × 0.85 penalty |
| `STRONG_COUNTER` | any | CANDIDATE | penalty 折半 → × 0.925 |
| `STRONG_COUNTER` | `pure_mean_reversion` / `contaminated` | CONFIRMED | **auto-downgrade 為 MODERATE_COUNTER + penalty × 0.925** |

失敗（timeout / parse error）→ `red_team_execution_failed: true`，verdict 固定 `MODERATE_COUNTER`，basis 固定 `unclassified`。

---

## PHASE 3 — DECISION ENGINE

PM (inline)。Price framework 數字已由 **Phase 2.4 engine** 產出，直接引用。

```
Step 1 (Raw):
  raw_total = Σ(Weight_i × Score_i × Confidence_i)
  weights default: Fund 0.25, Sent 0.15, News 0.20, Tech 0.25, Valuation 0.15

Step 1.5 (Structural Shift Modulation — V2.18.0):
  Read latest earnings-analyst cache `structural_shift.tier` for ticker.
  IF tier = CONFIRMED:
    - Valuation lane analyst-PT contribution × 0  (full unanchor; stale PT)
    - Red Team mean-reversion attack BLOCKED — cannot trigger STRONG_COUNTER
      via "歷史均值回歸 / 週期見頂" arguments alone; must cite forward
      mechanism breakage (具體論證為何結構性改善會逆轉)
    - shift_macro_floor = 1.00 (sector_avoid 對個股失效)
    - position_size_cap_pct = 100
  ELIF tier = CANDIDATE:
    - Valuation lane analyst-PT contribution × 0.3 (stale flag)
    - Red Team STRONG_COUNTER penalty 折半 (0.85 → 0.925)
    - shift_macro_floor = 0.95
    - position_size_cap_pct = 50
  ELSE (NONE / null / INSUFFICIENT_DATA):
    - shift_macro_floor = 0; no modulation; standard rules apply

Step 1.7 (Lane Polarization Modulation — V2.19.0):
  Compute polarization via `apply_det_shadow.compute_polarization(lane_scores, val_score)`.
  Read `det_shadow.signal_polarization` 4-tier label: BIPOLAR / OUTLIER / MIXED / ALIGNED.

  IF polarization = BIPOLAR (range ≥ 4 AND ≥2 lanes ≥ +1 AND ≥2 lanes ≤ -1 AND has +2/-2):
    - avg_confidence × 0.5
    - position_size_cap_pct = min(cap, 25)
    - decision band: BUY → STAGED_ENTRY 強制降階
    - 例外：IF structural_shift.tier = CONFIRMED AND macro = bull
            → confidence × 0.7 (paradigm shift 期間衝突是預期，但仍降一點)
  ELIF polarization = OUTLIER (range ≥ 4 但只有 1 lane 站對立面):
    - avg_confidence × 0.85
    - position cap 不動
    - 標記 outlier_lane_id（哪個 lane 站對立面）便於 user 檢視
  ELIF polarization = MIXED (range ≥ 3 雙邊都有但無極端):
    - avg_confidence × 0.75
    - position cap 不動
  ELSE (ALIGNED):
    - no modulation

Step 2 (Red-Team-Gated Bonus/Penalty — V3.17 5-level priority cascade):
  Read red_team_basis from det_shadow (V2.19 classifier output).
  basis ∈ {pure_forward, pure_mean_reversion, contaminated, unclassified}

  Read transition_signature from EARNINGS_ANALYST_BUNDLE (V3.17 — added field).
  Read forecaster.transition_case + valuation_specialist.cited_transition_overlay
  + valuation_specialist.transition_dissent_basis (V3.17 — Codex v5 + Gemini G4).

  Compute valuation_confirmed_transition (V3.17 — Gemini G4 dissent_basis gate):
    valuation_confirmed_transition = (
        forecaster.transition_case is True
        AND valuation_specialist.cited_transition_overlay is True
        AND valuation_specialist.transition_dissent_basis != "thesis_fundamental"
    )
    # Note: lane_score is NOT the gate (V3.17 — was Round 3 design,
    # rejected to avoid macro-systemic false negatives).
    # Note: dissent_basis is REQUIRED when valuation_specialist.lane_score < 0;
    # null → treated as "thesis_fundamental" (conservative default).

  Cross-check stale signal (V3.17.1 — Codex review fix; Staleness Alert + Gemini G2):
    IF abs(bundle.transition_signature_mtime - forecaster.transition_case_mtime) > 6h
       OR bundle.transition_signature inconsistent with forecaster.transition_case:
      emit_terminal_alert(level=HIGH, includes=[bundle_mtime, forecaster_mtime, delta])
      session_export["transition_data_stale_or_inconsistent"] = true
      transition_softening_disabled = true       # disables rule #2 only,
                                                  # cascade #1/#3/#4/#5 still apply
      # 不寫 SESSION_NOTES.md (per CLAUDE.md §2 EXCLUSION — protocol run 不是 session)
    # Field source:
    # - `bundle.transition_signature_mtime` emitted by earnings-analyst analyze.py
    #   and backfilled from cache file mtime by forecaster if missing.
    # - `forecaster.transition_case_mtime` emitted by forecast.py.

  IF all 5 signals same direction AND Burry.veto_flag = false AND red_team_verdict = NO_VIABLE_COUNTER:
    raw_after_bonus = raw_total × 1.15

  ELIF red_team_verdict = STRONG_COUNTER:
    # V3.17 — 5-level priority cascade, first match wins.
    # Cascade rules:
    #   1. structural paradigm shift CONFIRMED + mr/contaminated → 0.925 + downgrade
    #   2. transition_signature (mix-based) + Valuation confirmed + mr → 0.95 (NEW)
    #   3. structural paradigm shift CANDIDATE → 0.925
    #   4. pure_forward attack → 0.85
    #   5. otherwise → no penalty (default catch-all)
    IF shift_tier = CONFIRMED AND red_team_basis IN {pure_mean_reversion, contaminated}:
      # Rule #1 — mr 一票否決：CONFIRMED paradigm shift 期間不接受 mr 攻擊
      effective_verdict = MODERATE_COUNTER
      penalty = 0.925
      raw_after_bonus = raw_total × penalty
      auto_downgrade_logged = true
      cascade_rule_applied = "rule_1_paradigm_confirmed_mr_downgrade"

    ELIF (not transition_softening_disabled
          AND transition_signature IN {"mix_only", "both"}
          AND valuation_confirmed_transition is True
          AND red_team_basis == "pure_mean_reversion"):
      # Rule #2 (V3.17 NEW) — business mix transition + Valuation lane confirms
      # + Red Team is purely mean-reversion → soft-penalize (0.95).
      # NOTE: reuses pure_mean_reversion / contaminated keyword set in
      # apply_det_shadow.py — does NOT introduce a "valuation_anchor" attack
      # class (per Round 3 Q3 — anchor 已含在 MR_KEYWORDS 內).
      penalty = 0.95
      raw_after_bonus = raw_total × penalty
      cascade_rule_applied = "rule_2_transition_signature_mr_soften"

    ELIF shift_tier = CANDIDATE:
      penalty = 0.925
      raw_after_bonus = raw_total × penalty
      cascade_rule_applied = "rule_3_paradigm_candidate"

    ELIF red_team_basis == "pure_forward":
      penalty = 0.85
      raw_after_bonus = raw_total × penalty
      cascade_rule_applied = "rule_4_pure_forward"

    ELSE:
      # Rule #5 — STRONG_COUNTER but no specific rule triggers
      # (e.g. unclassified basis without paradigm/mix evidence)
      penalty = 0.85
      raw_after_bonus = raw_total × penalty
      cascade_rule_applied = "rule_5_default_strong_counter"

  ELSE:
    raw_after_bonus = raw_total
    cascade_rule_applied = "no_penalty"

Step 3 (Directional Macro Multiplier):
  effective_macro_mult = max(macro_multiplier, shift_macro_floor)
  IF sign(raw_after_bonus) == sign(macro_backdrop_score):
    final_score = raw_after_bonus × effective_macro_mult
    macro_alignment = ALIGNED
  ELSE:
    final_score = raw_after_bonus
    macro_alignment = CONTRARIAN
```

Burry 不納入 Step 1 加權。VOLATILE regime 不重複扣分（已計入 macro_backdrop_score）。

> **設計理由（V2.18.0 Structural Shift / V2.19.0 Lane Polarization + Red Team Anti-Spoofing）** 已移至 `investment_protocol_v5_0_DESIGN_NOTES.md`（純人讀，runtime 不載入）。對應操作規則仍在本節 Phase 3 step 定義（polarization tier / STRONG_COUNTER downgrade / position cap 等）。

### 決策閾值（V2.20.0 — Dynamic Threshold）

**Step 4 — Dynamic Threshold (V2.20.0)**：

```
buy_threshold = 1.2  (default)

# Lower threshold (更敢進) for high-conviction paradigm-shift consensus
IF structural_shift.tier = CONFIRMED AND polarization = ALIGNED:
    buy_threshold = 1.0
ELIF structural_shift.tier = CANDIDATE AND polarization = ALIGNED:
    buy_threshold = 1.1

# Raise threshold (更嚴) for chaotic / lane-conflict scenarios
ELIF polarization = BIPOLAR:
    buy_threshold = 1.5
ELIF polarization = OUTLIER:
    buy_threshold = 1.3

# All other combinations use default 1.2

staged_threshold = max(0.6, buy_threshold - 0.4)   # always 0.4 below buy
```

| final_score | decision (default buy=1.2 staged=0.8) |
|---|---|
| ≥ buy_threshold | BUY |
| staged_threshold ~ buy_threshold | STAGED_ENTRY |
| -staged_threshold ~ +staged_threshold | HOLD |
| -buy_threshold ~ -staged_threshold | STAGED_EXIT |
| ≤ -buy_threshold | SELL |

#### 熱區保守性鬆綁（V5.0.x — Rec 11，rec_source TODO-001+002）

正分 HOLD band（`[0, +staged_threshold)`）在熱門 sub-industry × 多頭 regime 下系統性錯過平順上漲（Semis HOLD-miss 86% N=22 / CANCEL-miss 71% N=21；miss avg runup +30.5% vs drawdown −3.2% → 真錯過非避損）。故加單一例外，把正分模糊區的 default 觀望降為小倉試探：

```
WHEN final_score ∈ [0, +staged_threshold)        # 正分模糊區（不含負分）
  AND industry_top_30pct = true                   # 熱門 sub-industry
  AND macro_regime ∈ {RISK_ON, BULL}              # regime guard — 只在驗證過的多頭觸發
  AND decision_cap_active != true                  # 硬保險：valuation 證據不足 cap 仍走原路
  AND (mandatory_risk_flags 為空)                  # 硬保險：任何系統性 risk flag → 不鬆綁
THEN:
    final_decision = STAGED_ENTRY (hot_zone_probe)  # 原 default HOLD 降為小倉試探
    hot_zone_probe = true
    position_size_pct ≤ 0.0015                       # 15 bps 上限（正常 cap 30bps 之半）
    # 連動 cap 規則第 6 點：熱區 probe 不 force CANCEL（見下）
```

- **負分區（`(-staged, 0)`）不適用** — 仍 default HOLD（無證據鬆綁空方）。
- **硬閘優先**：Auto REJECT（下節）、burry≤1 CANCEL、`proceed_to_phase3=false`、systemic risk flag、decision_cap 全部**優先於**本例外；任一觸發即不 probe。

**設計理由**：
- 固定 +1.2 BUY 對 5-lane ALIGNED + CONFIRMED 太嚴（白白錯失 super-cycle 進場），對 BIPOLAR 衝突太鬆（容易誤判 BUY）
- Tier × polarization 矩陣 4 種組合對應不同信心 → threshold 動態化
- staged_threshold 永遠 = buy − 0.4 維持比例
- 其他組合（CONFIRMED + MIXED、CANDIDATE + OUTLIER、NONE + ALIGNED 等）走 default — 漸進式 conviction，不所有 tier 都改
- **熱區 probe regime guard 是刻意自限**：規則僅在 `RISK_ON/BULL` 觸發，即只在 N=22/21 樣本驗證過的多頭市況生效。空頭/避險 regime 樣本不足（見 REVIEW §4 盲點），不外推。回檔來臨時 regime 轉 `VOLATILE/SIDEWAYS` → 規則**自動 dormant**；外加 `decision_cap` + `mandatory_risk_flags` 兩道硬保險，防 regime 偵測落後仍誤標 RISK_ON 而在回檔段誤 probe。
- **probe 15 bps**：即使 pattern 在某 regime 失效，單筆曝險上限極小（正常 cap 30bps 之半）— 鬆綁的下檔風險受嚴格 bound。
- ⚠️ **2026-06 中旬預期大幅回檔**（user 2026-06-07 提示）：若回檔期 regime 仍被誤標 RISK_ON，依賴上述兩道硬保險 dormant；Rec 11 首兩週加嚴觀察 Semis HOLD-miss，>70% 即 paused。

### Auto REJECT
- `risk_reward_ratio < 2.0`
- `proceed_to_phase3 = false`
- Unknown/negative binary risk < 48h
- `mandatory_risk_flags` 含系統性事件
- `phase2_fanout_summary.mode = FULL_FALLBACK` AND `final_decision ∈ {BUY, STAGED_ENTRY}` → 強制降為 HOLD

```json
{
  "phase": 3,
  "calculation_steps": {
    "fund": "0.25 × score × conf = result",
    "sent": "0.15 × score × conf = result",
    "news": "0.20 × score × conf = result",
    "tech": "0.25 × score × conf = result",
    "val":  "0.15 × score × conf = result",
    "raw_total": "float",
    "structural_shift_modulation": {
      "tier": "NONE | CANDIDATE | CONFIRMED | INSUFFICIENT_DATA | null",
      "applied_adjustments": [ "string", ... ],
      "shift_macro_floor": "float — 0/0.95/1.00",
      "position_size_cap_pct": "int — 100/50/100",
      "red_team_mean_reversion_blocked": "bool"
    },
    "polarization_modulation": {
      "label": "BIPOLAR | OUTLIER | MIXED | ALIGNED — V2.19",
      "lane_range": "float",
      "pos_strong": "int — count of lanes >= +1",
      "neg_strong": "int — count of lanes <= -1",
      "outlier_lane_id": "string | null — which lane is on minority side",
      "applied_adjustments": [ "string", ... ],
      "confidence_multiplier": "float — 0.5/0.85/0.75/1.0",
      "position_cap_after": "int"
    },
    "red_team_basis": "pure_forward | pure_mean_reversion | contaminated | unclassified — V2.19 classifier",
    "red_team_auto_downgrade": "bool — V2.19; true if mr-spoofing 觸發 STRONG→MODERATE 降級",
    "dynamic_threshold": {
      "buy_threshold":    "float — V2.20 dynamic (1.0/1.1/1.2/1.3/1.5)",
      "staged_threshold": "float — buy_threshold − 0.4",
      "rationale":        "string — e.g. 'CONFIRMED+ALIGNED → 1.0' / 'BIPOLAR → 1.5' / 'default 1.2'"
    },
    "red_team_verdict": "...",
    "bonus_applied": "bool", "penalty_applied": "bool",
    "raw_after_bonus": "float",
    "macro_multiplier": "float", "macro_alignment": "ALIGNED | CONTRARIAN",
    "effective_macro_mult": "float — max(macro_multiplier, shift_macro_floor)",
    "final_score": "float"
  },
  "avg_confidence": "float",
  "final_decision": "BUY | STAGED_ENTRY | HOLD | STAGED_EXIT | SELL",
  "decision_margin": "string",
  "contrarian_note": "Burry [X/100] — implication",
  "red_team_note": "counter_thesis + 主要 kill condition",
  "fanout_mode": "PARALLEL_SUBAGENT | PARTIAL_FALLBACK | FULL_FALLBACK",

  // V2.13.0 — PM 整合層補強欄位（必填，不影響 final_score 公式）
  "institutional_lens": "string — 1-2 句機構流向 narrative，整合 Sentiment.institutional + congressional_trades + FTD + (V2.9.0) institutional_holders_qoq_delta；矛盾訊號要點出來",
  "decision_confidence_pct": "int 0-100 — 決策信心度百分比（與 avg_confidence 0-1 共存，給 user 直觀）",
  "scenario_odds": {
    "bull": "int 0-100 — 看多劇本機率",
    "base": "int 0-100 — 主場景機率",
    "bear": "int 0-100 — 看空劇本機率"
  },
  "action_label": "ATTACK | WAIT | DEFENSIVE — 動作建議（與 final_decision 並存，補強 sizing 提示）"
}
```

> **`scenario_odds` 必須加總 100**。LLM 算錯就 reject 重算。
>
> **`action_label` 對映**（並存於 final_decision，不取代）：
> - `ATTACK`：立即進（BUY 且 confidence ≥ 70%、或 STAGED_ENTRY 第一階段條件已成）
> - `WAIT`：等 pullback / 條件觸發（STAGED_ENTRY 第二階段、或 HOLD 但有 watch 觸發）
> - `DEFENSIVE`：觀望或縮倉（HOLD 但訊號矛盾、SELL、STAGED_EXIT）
>
> **`institutional_lens` 撰寫指引**：必引用具體數值，例：「機構 Q-on-Q +434 holders 流入，但 insider Q ratio 0.06 重度賣超 + Senate net buy −3 — 散戶搶機構之外的籌碼，矛盾訊號 → 慎防散戶 trap」

---

## PHASE 4 — EXECUTION & RISK MANAGEMENT

Trader Agent + Risk Manager (inline)。

### Step 1 — Dual-Track Trade Plan

```json
{
  "trade_plan": {
    "entry_aggressive":   {"range": [min, max], "trigger": "LIMIT|MARKET|BREAKOUT", "trigger_conditions": "string"},
    "entry_conservative": {"range": [min, max], "trigger_conditions": "string"},
    "take_profit": "price",
    "stop_loss": "price",
    "risk_reward_ratio": "float — must >= 2.0",
    "time_horizon": "short | mid | long",
    "exit_conditions": "string"
  }
}
```

- BUY → 兩軌二選一（預設 aggressive）
- STAGED_ENTRY → 兩軌各佔 50%

> **V5.1 — entry/TP/SL 取值 provenance（補原本 protocol 未明定缺口；V3.45.3 起直接取 Phase 2.4 engine 輸出，不再前向引用）**：
> - `entry_aggressive.range` ← short_term_5d `[band_point 附近, band_upper_capped]`（突破續勢）或現價附近（pattern=breakout 時）
> - `entry_conservative.range` ← short_term_5d `[band_lower_capped, band_point]`（回檔承接；下界貼 support）
> - `take_profit` ← mid_term_60d `mid_target`；若 > `key_levels.resistance` → cap 在 resistance 並於 `exit_conditions` 註記「需突破 $R 才上看 $mid_target」
> - `stop_loss` ← `min(short_term band_lower_capped, key_levels.support)` − buffer；與 Step 4 `final_stop_loss_pct` 算出的價取**較保守（較高）**者
> - `risk_reward_ratio` 用上述 TP/SL 重算，仍須 ≥ 2.0（不足 → 收緊 entry 或降級 HOLD）

### Step 2 — Vol-Adjusted Position Sizing
```bash
python3 skills/portfolio-risk-manager/scripts/risk_manager.py <TICKER> --json-only
```
取 `final_position_cap_pct` → `vol_adjusted_limit_pct`

### Step 3 — Tail Risk Assessment
```bash
python3 skills/tail-risk-analyzer/scripts/tail_risk.py <TICKER> --json-only
```

| fragility_label | tail_risk_score | position_multiplier |
|---|---|---|
| ROBUST | < 30 | × 1.0 |
| MODERATE | 30-60 | × 0.75 |
| FRAGILE | ≥ 60 | × 0.5 |

### Step 3.5 — FTD Timeline Gate (V4.9)

適用前提: `phase0.ftd.state == FTD_CONFIRMED` AND `days_since_ftd != null`。

Sector 分類：
- **Cyclical**: Tech, Industrials, Materials, Financials, Cons. Disc., Energy, Communication
- **Defensive**: Utilities, Cons. Staples, Healthcare, Real Estate

| `days_since_ftd` | Stage | Cyclical mul. | Defensive mul. | 停損調整 |
|---|---|---|---|---|
| 1-5 | prime | × 1.0 | × 1.0 | 標準 |
| 6-12 | standard | × 0.90 | × 1.0 | 標準 |
| 13-20 | late_cycle | × 0.75 | × 0.95 | -1% (cyclical) |
| 21+ | exhausted | × 0.50 OR reject | × 0.85 | -2% (cyclical) |

Day 21+ reject (cyclical only): IF `RS_rating < 90` OR `distance_from_50ma > 15%` → `decision = REJECT`。

### Step 4 — Final Sizing

```
base       = vol_adjusted_limit OR 0.05
tail_adj   = base × fragility_multiplier
macro_cap  = min(tail_adj, 0.03) if macro_backdrop_score < -3 else tail_adj
binary_adj = macro_cap × 0.5-0.7  if binary_classification ∈ [unknown, negative] AND event < 48h
           = macro_cap            otherwise
burry_override_adj = binary_adj × 0.5 if t4.resolution == OVERRIDE_BURRY else binary_adj
ftd_adj    = burry_override_adj × ftd_timeline_multiplier
shift_adj  = ftd_adj × (position_size_cap_pct / 100)   # V2.18.0 — CANDIDATE 強制 ×0.5
polar_adj  = shift_adj × (polar_position_cap_pct / 100)  # V2.19.0 — BIPOLAR 強制 ×0.25
final_position_size = polar_adj × 0.5 if final_decision == STAGED_ENTRY else polar_adj
final_stop_loss_pct = base_stop_pct + ftd_timeline_stop_adjustment   # 上限 -10%
```

> V2.18.0: `position_size_cap_pct` 來自 Phase 3 Step 1.5 structural_shift_modulation。
> CONFIRMED → 100（不縮）；CANDIDATE → 50（強制半倉）；NONE → 100（一般規則接管）。
>
> V2.19.0: `polar_position_cap_pct` 來自 Phase 3 Step 1.7 polarization_modulation。
> BIPOLAR → 25（砍 1/4）；OUTLIER → 100；MIXED → 100；ALIGNED → 100。
>
> 兩個 cap 串聯（multiply）— BIPOLAR + CANDIDATE = 0.25 × 0.50 = 0.125 倍 → 極小試水單。

**Binary risk**: positive (歷史 beat ≥ 70%) → 不減倉；unknown (FOMC / 地緣) → 48h 內減倉；negative (已知壞消息) → 減 50%

```json
{
  "phase": 4,
  "trade_plan": { /* see above */ },
  "risk_audit": {
    "risk_level": "LOW|MEDIUM|HIGH",
    "vol_adjusted_limit_pct": "float|null",
    "position_size_method": "VOL_ADJUSTED | RULE_BASED",
    "tail_risk": {
      "fragility_label": "ROBUST|MODERATE|FRAGILE",
      "tail_risk_score": "float",
      "fragility_adjustment": "× 1.0|× 0.75|× 0.5"
    },
    "binary_classification": "positive|unknown|negative|none",
    "burry_override_active": "bool",
    "burry_override_multiplier": "0.5 | 1.0",
    "ftd_timeline_gate": {
      "applied": "bool", "days_since_ftd": "int|null",
      "stage": "prime|standard|late_cycle|exhausted|n/a",
      "sector_class": "cyclical|defensive",
      "multiplier": "1.0|0.95|0.9|0.75|0.5",
      "stop_loss_adjustment_pp": "0|-1|-2",
      "rejection_triggered": "bool"
    },
    "position_size_pct": "float 0.00-0.10",
    "staged_entry_split": {"aggressive_pct": "float|null", "conservative_pct": "float|null"},
    "approval": "APPROVED | REJECTED",
    "rejection_reason": "string if REJECTED"
  }
}
```

---

## PHASE 4.5 — MULTI-HORIZON PRICE FRAMEWORK（封裝呈現層）

**全部數字已由 Phase 2.4 engine 算出**（`fair_value_summary` + `fair_value_range` +
`multi_horizon_price_framework` + `implied_expectations` + `valuation_archetype_shadow`）。
本 Phase PM 只做兩件事：

1. **verbatim 抄寫** engine 5 個 block 進 session export（shape 見 `phase5_export_schema.md`）。
   **禁止手算 / 重算 / 改寫任何數字**。
2. MD 報告 §6 呈現（三時間框架表，見 Phase 5 Step 4 模板）。

紀律速記：
- `fair_value_summary` 是決策數字唯一來源（decision_lock 保護）；range / MHP / implied /
  archetype shadow 全部 **advisory sibling**，不進 11-field decision_lock、不改決策數學。
- `mhp_signal` 只餵 T5 reasoning 與 Phase 4 trade_plan 取值（entry ← 5d band、TP ← 60d
  mid_target cap at resistance、SL ← min(band_lower, support) 取較保守）。
- 缺料降級 = data 非 failure（engine 自動處理；validator warning-only）。
- shadow 退出條件 / 演算法細節 / 權重表：見 `investment/protocol_appendix_price_framework.md`
  （audit 用，跑 protocol 不需讀）。checkpoint 報告：`python3 investment/scripts/shadow_report.py`。

---

## PHASE 4.6 — DECISION CAP (V5.0.x NEW)

PM (inline, deterministic — 沒有 LLM 呼叫)。在 Phase 5 export 之前強制執行。

### 目的
Phase 4.5 anchors 不足 / fair value confidence=low 時，仍可能因其他 lane 推力推出
高信心 BUY → 過去常見「弱 valuation 證據卻給高信心 BUY」誤判。Cap 把這類決策硬壓回
低 size、低 confidence、不得 BUY，但保留 STAGED_ENTRY / HOLD 路徑。

### 觸發條件 (任一即觸發 cap)

| 條件 | `decision_cap_reason` |
|---|---|
| `fair_value_summary.anchors_available < 2` | `insufficient_anchors` |
| `fair_value_summary.confidence == "low"` | `low_valuation_confidence` |
| 任一 lane data_quality 標記為 low（degraded_analysts 或 bundle 缺失） | `low_data_quality` |

### Cap 規則（強制套用）

觸發後 PM **必須**：

1. **`decision_cap_active = true`** — schema field
2. **`decision_cap_reason`** = 上表的 reason 值
3. **`final_decision`** 不得是 `BUY` — 只能 `STAGED_ENTRY` / `HOLD`
4. **`avg_confidence`** = `min(原值, 0.65)`
5. **`position_size_pct`** = `min(原值, 0.003)` — 即 30 bps 上限
6. **`final_action`** 對應改：原 `EXECUTE` → `STAGED`；若降為 HOLD 則 `CANCEL`
   - **熱區例外（Rec 11）**：當 `hot_zone_probe=true`（見 decision band 熱區鬆綁）且本 cap 非 systemic / 非 decision_cap 觸發時，**保留 `STAGED` probe，不 force `CANCEL`**。15 bps 倉位上限本就 ≤ 30bps cap，無衝突。systemic risk flag / decision_cap_active 觸發的 cap **不適用**此例外（硬閘優先）。

### Override 例外

若 PM 認為有重大 catalyst 推力（earnings beat / 結構性 thesis / 監管利多），
可保留 `STAGED_ENTRY` + 30 bps，但 **必須**填：

- **`cap_override_reason: string`** — 一句說明為何 override（非空字串）

Override **不解除** size 與 confidence 的 cap，只是允許不退到 HOLD。

### Schema export 欄位（trades_this_session[0]）

```json
{
  "decision_cap_active":  true,
  "decision_cap_reason":  "insufficient_anchors | low_valuation_confidence | low_data_quality",
  "cap_override_reason":  "string | null"
}
```

未觸發 cap 時 `decision_cap_active=false`、其餘兩欄 null。
Validator (`validate_session_export.py` § 10) 會檢查 cap 規則一致性，違反 rc=1。

---

## PHASE 5 — SESSION EXPORT + MD REPORT + VALIDATE

PM (inline)。

### Step 1 — Append session export JSON 至 `./invest_logs/history.json`
Shape **必須**符合 `phase5_export_schema.md` (FULL EXAMPLE)。

**V5.0.x — 用 script 寫入，不再在 prompt 內手寫巨大 JSON 段**：

```bash
# 把本次 session 完整 entry JSON 存到暫存檔（PM 在 Phase 5 末段用 Write 工具寫入）
# 然後呼叫：
python3 investment/scripts/append_session_export.py --from-file /tmp/<ticker>_session.json
```

或直接 pipe：

```bash
cat <<'JSON' | python3 investment/scripts/append_session_export.py
{ "session_export_version": "V5.0", ... }
JSON
```

腳本會：原子寫入（tmp + rename）、`fcntl.flock` 序列化、自動鏡射 top-level
`ticker` / `final_action` / `date`、檢查最小 shape。失敗 → 修 entry 再重跑。

> **V2.10.0 補必填欄位**（trades_this_session[] 內）：
> - `lane_scores: {fundamentals, sentiment, news, technical}` — Phase 2 四個非 valuation lane 的 raw score（−3..+3）
> - `det_inputs: {altman_z, debt_to_equity, fcf_yield, insider_ratio_q, short_interest_pct, fred_in_sector_avoid}` — 6 個 quant 原始值，**直接從 Phase 2 bundle 抄寫**，禁重新解讀
> - `det_shadow` — Step 1.5 跑 post-processor 後自動產生，**不要手寫**

> **V5.0.x 補必填欄位**（trades_this_session[] 內，Phase 4.6 產出）：
> - `decision_cap_active: bool`
> - `decision_cap_reason: "insufficient_anchors" | "low_valuation_confidence" | "low_data_quality" | null`
> - `cap_override_reason: string | null`

### Step 1.5 — Apply deterministic shadow + polarization label (V2.10.0+ MUST-run)
```bash
python3 investment/scripts/apply_det_shadow.py --inplace investment/invest_logs/history.json
```
此步把 `det_shadow` block 寫入最新一筆 trades_this_session[]。Polarization 從 lane_scores 算；val_det 從 weighted_fair_value 算；red_team_det 從 det_inputs 6 條 kill triggers 算。
- 若 `lane_scores` 不齊 → polarization=null（不影響其他欄位）
- 若 `det_inputs` < 3 個有效值 → red_team_verdict_det=null（不影響其他欄位）
- LLM 主分數（final_score / valuation_lane.score / red_team_verdict）**不被覆蓋**

### Step 2 — Schema validate (MANDATORY gate)
```bash
python3 investment/scripts/validate_session_export.py
```
rc ≠ 0 → 修正最後一筆後重跑直到 rc=0。

### Step 3 — 確認 `./invest_logs/YYYY-MM-DD_phase0.json` 已存在

### Step 4 — Sonnet MD Report Formatter (MUST use Agent tool)

```
Agent(
  description="Session MD report formatter",
  subagent_type="general-purpose", model="sonnet",
  prompt="""
  You are a MARKDOWN FORMATTER — not an analyst.

  HARD CONSTRAINTS:
    - 不得重新評分、改變 signal、改變 final_decision、改變 position_size、改變 entry/TP/SL 數字。
    - 不得新增你自己的判斷或觀點。
    - 若資料有缺漏，填「N/A」而非自行補全。
    - **Score Scale 強制 (V1.88)**：
      * Final Score: `X.XXX / 3.0` 或裸數字 ≤ 3.0；禁 /5.0、/10
      * 5 lane scores (Fund/Sent/News/Tech/Val): 0-3 範圍裸數字；禁 lane: X/10
      * Burry score: `X.X / 100`；禁 /12 或 /10
      * Red Team strength: `N/5` 或 N 整數
      * 範例對：`Final Score 1.609 / 3.0`、`Burry 50.3 / 100`
      * 範例錯：`HOLD (6.72/10)`、`Fundamentals: 8.1/10`、`Burry 4.5/12`

  TICKER: <T>
  DATE: <YYYY-MM-DD>

  PHASE 0-4.5 COMPLETE JSON:
  <paste phase0_macro_snapshot, phase2 all 6 outputs (5 lanes + Burry), phase2.5, phase2.8 red team, phase3, phase4, phase4.5 fair_value_summary, phase5 trades_this_session[0]>

  OUTPUT 結構 (純 Markdown，不含 code fence):
    1. 標題: `# YYYY-MM-DD TICKER — 投資委員會分析`
    2. 決議摘要: Final decision、final_score、position_size、合理股價（fair_value_summary.weighted_fair_value + vs_current_pct）
    3. Phase 0 Macro Context (1 段)
    4. Final Visualization Table (5 lanes + Burry + Red Team)
    5. 詳細評分 (key_factors / risk_flags per lane)
    6. **Multi-Horizon Price Framework (V5.1 — 升級自 V5.0 合理股價估算)**: 三時間框架表 —
       - **長期合理價**: anchors 6 行 + weighted_fair_value + verdict_band + confidence（`fair_value_summary`，不變）
       - **長期區間 (V3.45.1)**: `fair_value_range` — `[P25 / P50 / P75]` + min/max anchor + `range_verdict` + `agreement_grade`（錨一致度）。重點呈現「合理股價是 $170–$280 區間不是單點 $215」
       - **隱含預期 (V3.45.1)**: `implied_expectations` — 現價隱含 5Y FCF CAGR vs 實際 vs lane 估（sanity_note）
       - **5 日機率帶**: `[下界 / 點估計 / 上界]`（capped 版）+ drift + confidence + catalyst flag + key_level 反射註記
       - **60 日 target**: momentum_target / pt_60d / earnings_revision → mid_target + reality_check 成立條件
       - **三框收斂訊號**: `mhp_signal`（wait_for_pullback / high_conviction_long_zone / momentum_not_value / neutral_aligned）+ 1 句解讀
    7. **Red Team Counter Thesis (V2.14.0 IC-memo 結構強化)**:
       - **Consensus View (市場共識)**: 1-2 句 — 主流分析師 / 媒體普遍認同的看法（從 Phase 2 News + Sentiment lane 抽）
       - **Differentiated View (本委員會差異化判斷)**: 1-2 句 — 本次分析跟 consensus 哪裡不同、為什麼（from final_decision + final_score 的關鍵 driver）
       - **Counter Thesis**: red_team_counter_thesis 全文
       - **Numbered Kill Conditions**: 必須 numbered list（1. / 2. / 3.），每條 falsifiable + 可量化（red_team_kill_conditions 直接照搬 + 編號）。禁 free-form 段落
    8. **進場計畫 (V2.14.0 Returns Profile 三檔)**:
       - **Base Case**: 進場區間（← 5 日 band）+ TP1 / TP2（TP ← 60 日 mid_target）+ SL（← band 下界 / support 取較保守）+ R/R（雙軌 staged_split）+ position_size_pct
       - **Bull Case (1-2 句)**: 若 base case 觸發後 follow-through，下一個 TP3 / 加碼條件 / 持有窗口（從 long-term verdict_band + watch_conditions 推）
       - **Bear Case (1-2 句)**: 若 SL 觸發 / kill condition 命中 → exit 行為 + 不再進場條件
    9. 關鍵風險（key_risks 條列）
    10. Watch / re-eval 觸發條件（watch_conditions dict 全列，加觀察 metric）

  寫入 `../reports/<YYYYMMDD>_<TICKER>.md`，回傳檔案路徑。
  """
)
```

> **V2.14.0 IC-memo 強化動機** 已移至 `investment_protocol_v5_0_DESIGN_NOTES.md`（純人讀）。執行重點：consensus vs differentiated view 並陳、Kill Conditions numbered、Returns Profile 三檔；欄位來源**仍是** Phase 2-4 已產出 JSON，formatter 不重新評分。

> **成本**: Sonnet 4.6 vs Opus → 每次節省 ~$0.4-0.7。違反 hard constraints → PM reject 並 retry 1 次；再失敗 → PM inline 寫 MD (照 V5.0 template，禁 freestyle)。

### Step 5 — Markdown Score-Scale Validation Gate
```bash
python3 investment/scripts/validate_markdown_export.py
```
- rc=0 → 完成
- rc=1 → retry Sonnet 一次（paste stderr 違規清單進 prompt）
- 再失敗 → PM inline 覆寫 + 重跑 validator，rc=0 才結束 protocol

**禁止**：跳過 validator、接受 rc=1 報告、把 freestyle MD 寫進 reports/ 標 done。

### Step 6 — Phase 5.5: Thesis Registry Wire-up (V2.14.0+, non-fatal)

把本次 session 自動 register 進 trader-memory-core thesis 生命週期，產出 `thesis_id` 寫回 `history.json` 最後一筆。

```bash
python3 investment/scripts/register_thesis.py
```

- **rc=0 + 「✓ registered」**：成功 register，`history.json[-1].trades_this_session[0].thesis_id` 已填。後續 review queue / postmortem 都靠此 ID 串接。
- **rc=0 + 「unavailable」**：trader-memory-core 模組缺 dep / 不在路徑。**non-fatal** — `thesis_id` 留 null，不擋 protocol 結束。
- **rc=1**：`thesis_store.register()` 真的炸了（state dir 寫不進去 / 資料 corrupt）。報錯後 PM 可選擇手動 register 或 skip。

**Idempotent**：若 last entry 已有 thesis_id（同一 protocol run 重跑），script 直接 rc=0 退出，不重複 register。

**State 位置**：`investment/invest_logs/theses/`（project-local，不汙染 global trader-memory-core state）。

### Step 7 — IC Memo Hook (V3.25.0+, non-fatal, `--memo` flag only)

當 `分析 [TICKER]` 加 `--memo` flag 時，於 Phase 5.5 結束後執行；不加 flag 預設**跳過**。

```bash
python3 skills/ic-memo-writer/scripts/build_fact_pack.py <TICKER>
python3 skills/ic-memo-writer/scripts/compose.py <TICKER>
python3 skills/ic-memo-writer/scripts/validate_ic_memo.py reports/<DATE>_<TICKER>_ic_memo.md
```

- 產出第二份 MD：`reports/<YYYYMMDD>_<TICKER>_ic_memo.md`（高可讀敘事 12 章節）
- **不重評分、不重抓 FMP、不修改 history.json**。資料源 = profile + earnings-analyst cache + history.json `trades_this_session[-1]`。
- §11 委員會結論 **verbatim** 來自 protocol.history，受 11 欄位 SHA256 decision_lock 保護（`final_decision / final_action / position_size_pct / analysis_price / fair_value_summary / scenario_odds / watch_conditions / key_risks / red_team_counter_thesis / red_team_kill_conditions / lane_scores`）。
- Validator rc 分級：
  - rc=0 pass
  - rc=1 **fatal** — decision_lock hash mismatch / §11 verbatim 失敗 / FV mismatch / 重評分禁字。**不可稱完成**；memo file 仍寫但加 `<!-- INVALID -->` 標頭，hook 報錯。
  - rc=2 **degraded-usable** — earnings cache 缺 / 章節 stub / peer_descriptor 為 stub。 Memo published；footer 標 `degraded_sections`。
- **失敗 non-fatal**：IC Memo composer 任一步炸了，**不影響** Phase 5 委員會決策報告（`reports/<DATE>_<TICKER>.md`）的 done 狀態。

第一版（V1.0）為 deterministic-only：0 LLM call，純資料 → MD 拼接。`--llm-polish` flag 預留但 raise `NotImplementedError`。

詳見 `skills/ic-memo-writer/SKILL.md`。

---

## PHASE 6 — CONTINUOUS LEARNING

**Trigger**: `TRADE_RESULT: ticker=XXX result=WIN|LOSS`
PM (inline)。

```json
{
  "phase": 6,
  "ticker": "STRING",
  "outcome": "WIN | LOSS",
  "primary_failure_agent": "Fundamentals|Sentiment|News|Technical|Valuation|Contrarian|Red_Team|Risk_Manager|timing|macro_model",
  "what_was_missed": "string",
  "burry_was_right": "true|false|N/A",
  "red_team_was_right": "true|false|N/A",
  "valuation_was_right": "true|false|N/A",
  "fanout_mode_at_entry": "PARALLEL_SUBAGENT|PARTIAL_FALLBACK|FULL_FALLBACK",
  "weight_adjustment_delta": {
    "Fundamentals": "-0.05~+0.05", "Sentiment": "-0.05~+0.05",
    "News": "-0.05~+0.05", "Technical": "-0.05~+0.05",
    "Valuation": "-0.05~+0.05"
  },
  "updated_weights_for_next_session": {/* current + delta, sum = 1.0 */},
  "lesson_learned": "string"
}
```

**Weight 限制**: 單 agent 0.10-0.40；每次調整 ±0.05；總和 = 1.0。

> **V3.45.4 — News lane weight 凍結窗**：PT 注入層剝離後 News score 分布會系統性下移
> （歷史 baseline `{-1:1, 0:2, +1:6, +2:18, +3:4}`，n=31 — 牛市常態 +1 來源消失）。
> 歷史 lane weights 是在舊行為上校準的 → V3.45.4 後**前 10 個含 News lane 的 session**，
> `weight_adjustment_delta.News` 強制 = 0 並在 `lesson_learned` 標注 `news_weight_frozen_v3454`，
> 避免學習層把分布偏移誤判成 lane 失準。第 11 個 session 起恢復正常調整。

---

## FINAL VISUALIZATION TABLE

```
| Agent              | Signal | Score | Confidence | Key Factors (top 2) | Phase 0 Alignment | Isolated |
|--------------------|--------|-------|------------|---------------------|-------------------|----------|
| Fundamentals       |        |       |            |                     |                   |   Y/N    |
| Sentiment          |        |       |            |                     |                   |   Y/N    |
| News               |        |       |            |                     |                   |   Y/N    |
| Technical          |        |       |            |                     |                   |   Y/N    |
| Valuation (V5.0)   |        |       |            |                     |                   |   Y/N    |
| Contrarian (Burry) |   —    | X/100 |     —      |                     |                   |    —     |
| Red Team           | verdict|N/5    |     —      | kill_condition #1   |        —          |    Y     |

| RESULT | Decision        | Raw | RT Gate       | ×Macro | Final | Burry | Override | Pos% | Fragility | Fanout    | Action                |
|--------|-----------------|-----|---------------|--------|-------|-------|----------|------|-----------|-----------|-----------------------|
|        | BUY/STAGED/HOLD |  f  | ×1.15/—/×0.85 | ×f/—   |   f   | X/100 |  Y/N×0.5 |  %   | ROBUST    | PARALLEL  | EXECUTE/STAGED/CANCEL |

| Fair Value (V5.0)            | Value          |
|------------------------------|----------------|
| DCF Unlevered                | $X             |
| DCF Levered                  | $X             |
| Analyst PT Consensus         | $X             |
| Peer P/E Implied             | $X             |
| Owner Earnings × Multiple    | $X             |
| Earnings Forecaster Blend    | $X             |
| **Weighted Fair Value**      | **$X**         |
| Current Price                | $Y             |
| Premium/Discount             | ±X.X%          |
| Verdict Band                 | undervalued/fairly_valued/overvalued/extreme_overvalued |
| Confidence                   | high/medium/low|

| Entry Track       | Range        | Trigger Conditions                      |
|-------------------|--------------|-----------------------------------------|
| Aggressive (50%)  | $min – $max  | 立即 / 當前震盪區 / 破前高               |
| Conservative (50%)| $min – $max  | 技術反轉確認 / 財報後 / RSI>50 / 站上MA  |

| Red Team Kill Conditions                                 |
|----------------------------------------------------------|
| 1. IF <事件> WITHIN <天數> THEN <推翻論點>                 |
```
