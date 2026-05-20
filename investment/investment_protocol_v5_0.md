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
1. **Phase order**: 0 → 1 → 2 → 2.5 → 2.8 → 3 → 4 → 4.5 → 5。不跳過。
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
  "macro_multiplier_rationale": "string — LLM baseline + FRED caps applied"
}
```

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

### Bundle 摘要（詳細 schema 與 injection rules → `protocol_appendix_fmp_bundles.md`）

| Bundle | Source | Cost | Lane 注入 |
|---|---|---|---|
| `TICKER_DATA_BUNDLE` | `bash skills/finnhub-client/scripts/run_dual_fetch.sh --tickers <T>` → 讀 `scoring.*` (15 scalar) | 1 dual_fetch / session | All 5 lanes |
| `EARNINGS_ANALYST_BUNDLE` | 讀 `skills/earnings-analyst/cache/<T>_*.json` (≤ 90d) | 0 FMP call | Fundamentals + **Valuation Specialist** |
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
  - `price_target` consensus vs current_price: > 20% 折價 → +1；> 20% 溢價 → -1
  - `analyst_news[]` (FMP `/grades-news`)
  - `headlines[]` (finviz + yfinance + Finnhub deduped)
  - `sec_filings_recent[]` + `sec_8k_filings[]` (30d)
- **優先檢查 Phase 0 `_market_signals.top_catalysts[]`** 避免重抓
- `FMP_SUPP_BUNDLE.ma_events.events[]` 非空 → 強訊號（target 通常 +1）

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

> 以上 4 個欄位**必填**；缺資料寫 `INSUFFICIENT_DATA`（陣列用 `[]` + 註記）。

#### Technical Subagent
- **Rubric**: 20/50/200MA 結構、RSI(14)、MACD histogram、volume vs 20D avg、support/resistance。Stage 2 上升結構 → +3+；跌破 200MA + 量放大 → -3-
- **Skill**: `python3 skills/technical-analyst/scripts/analyze.py <TICKER> --json-only`
- OHLCV-only lane，但 V2.13 起額外讀 FMP_SUPP_BUNDLE.insider_summary 做主力分析（見下）

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

> 以上 3 區塊**必填**；資料缺則寫 `INSUFFICIENT_DATA` 而非 null。LLM 不得跳過。

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
4. **Insider trend** (`insider_summary.latest_trend`): accumulating + insider_pts==0 → 升至 1；distributing → narrative 註記
5. **DCF FCFF vs FCFE 差距** (`dcf_intrinsic` vs `dcf_levered_intrinsic`): 差 > 20% → narrative 加註資本結構警告，不調 score
6. **Comp benchmark** (V5.0, `comp_benchmark.ceo_vs_peer_pct`): CEO comp > peer median 200%+ → narrative 治理紅旗
7. **PEER_BUNDLE mispricing** (V4.10): `EV/EBIT > peer_median × 1.5` 或 `fcf_yield < peer 中位數一半` → narrative 加註，不調 score

```json
{
  "phase": 2, "agent": "Contrarian_Analyst_Burry",
  "ticker": "STRING",
  "burry_score": "0-100",
  "verdict": "T4_VETO | WARNING | NEUTRAL | VALUE_BONUS",
  "components": { "value_pts", "balance_pts", "insider_pts", "contrarian_pts" },
  "burry_voice": "string — 含所有規則調整理由",
  "veto_flag": "true if score < 20"
}
```

`veto_flag = true` → 觸發 Phase 2.5 T4。

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
- `burry_score 0-1` → 強烈建議 `CANCEL`
- `burry_score = 2` → `DOWNGRADE_DECISION` (BUY → HOLD) 或 `OVERRIDE_BURRY`
- 選 `OVERRIDE_BURRY` 自動三項成本：
  1. Phase 4 倉位 × 0.5 (`burry_override_multiplier`)
  2. 必填 `override_justification` (≥ 20 字，具體引用 Phase 2 某 analyst 證據)
  3. 自動計算 `override_recheck_date` = 交易日 + 5 個交易日

### T5 仲裁 (V5.0)
- `Valuation.score = -2`: reasoning 加注「估值警告 (溢價 {pct}%)」，不強制 downgrade
- `Valuation.score = -3` (extreme overvalued): **自動 downgrade BUY → STAGED_ENTRY**；STAGED_ENTRY → HOLD

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

TASK:
1. 找共識最脆弱 1 個主論點 → counter_thesis (1-2 句)
2. 產 2-3 條 falsifiable kill_conditions: "IF <事件> WITHIN <天數> THEN <推翻論點>"
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

PM (inline)。

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

Step 2 (Red-Team-Gated Bonus/Penalty — V2.19 anti-spoofing):
  Read red_team_basis from det_shadow (V2.19 classifier output).
  basis ∈ {pure_forward, pure_mean_reversion, contaminated, unclassified}

  IF all 5 signals same direction AND Burry.veto_flag = false AND red_team_verdict = NO_VIABLE_COUNTER:
    raw_after_bonus = raw_total × 1.15

  ELIF red_team_verdict = STRONG_COUNTER:
    # V2.19: anti-spoofing — mr 偷渡偵測
    IF shift_tier = CONFIRMED AND red_team_basis IN {pure_mean_reversion, contaminated}:
      # mr 一票否決：即使 LLM 塞 fw keyword 試圖救回，仍降級
      effective_verdict = MODERATE_COUNTER
      penalty = 0.925
      raw_after_bonus = raw_total × penalty
      auto_downgrade_logged = true
    ELIF shift_tier = CANDIDATE:
      penalty = 0.925
      raw_after_bonus = raw_total × penalty
    ELSE:
      penalty = 0.85
      raw_after_bonus = raw_total × penalty
  ELSE:
    raw_after_bonus = raw_total

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

### V2.18.0 — Structural Shift Modulation 設計理由

**痛點**：MU/QCOM 案例顯示 Valuation Lane（被過時 analyst PT 拖累）+ Red Team（用歷史週期 mean-reversion 攻擊）+ Macro（sector_avoid 一視同仁壓 multiplier）三個 backward-looking 模型同時壓制 forward signal，導致超級週期股票被迫 `DEFENSIVE HOLD`，錯失主升段。

**機制**：earnings-analyst (`compute_structural_shift`) 偵測 EPS QoQ ≥30% + GM 歷史 +2σ + revenue 加速三個 signal，≥2 過 → CANDIDATE，連 2 季 → CONFIRMED。Phase 3 讀此 tier 對症給予豁免。

**安全閥**：
- CANDIDATE 只放寬不解除，position cap 50% — 避免單季 noise 導致 bubble-top BUY
- CONFIRMED 才完全解除估值錨點，但仍要求 Red Team 必須以 forward mechanism breakage 攻擊（不接受純歷史均值論證）
- Tier 不影響 Step 1 raw_total — 個別 lane 仍然獨立評分；modulation 只動 Step 2/3 的 backward-looking 折扣

**對稱性原則**：missing top 是 bounded loss（少賺）；buying top 是 unbounded loss（套牢）。Tier 階梯 + position cap 把後者風險壓住。

### V2.19.0 — Lane Polarization + Red Team Anti-Spoofing 設計理由

**痛點 1 — Lane 各自為政**：5 lane 獨立評分後 PM 加權平均，但加權平均把「集體看多」(ALIGNED +2) 和「兩極衝突」(+3 +3 -3 -3 +1) 都壓平成中性數字，喪失「lane 衝突 = 系統不確定性」的訊號。Phase 3 沒做 divergence detection。

**痛點 2 — Red Team 偷渡 mean-reversion**：V2.18 在 PM 端 post-filter，但 Red Team prompt 仍用標準歷史攻擊；LLM 常塞 1 個 forward 關鍵字（"客戶庫存"）但本質是 mean-reversion 論證（"歷史均值"），表面 mixed 實則污染。

**機制 1 — Polarization 4-tier**：reuse 既存 `apply_det_shadow.compute_polarization`，加 OUTLIER 級避免 4-vs-1 outlier 誤判 BIPOLAR。Phase 3 Step 1.7 對應 confidence multiplier 0.5/0.85/0.75/1.0。

**機制 2 — Red Team basis classifier**：deterministic keyword scan（mr_keywords + fw_keywords）→ 4 級 basis（pure_forward / pure_mean_reversion / contaminated / unclassified）。CONFIRMED 狀態下 contaminated 跟 pure_mean_reversion 同等對待 → STRONG_COUNTER 自動降 MODERATE。

**Anti-Adversarial 鐵律**：
1. **mr 一票否決**：mr keyword 出現即觸發 dampening，無論搭配多少 fw keyword
2. **OUTLIER 不誤殺**：4-vs-1 不是真衝突，confidence × 0.85（不像 BIPOLAR 砍倉位）
3. **雙層防偽**：prompt 限制 + post-filter classifier，不單靠 LLM 自律

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

**設計理由**：
- 固定 +1.2 BUY 對 5-lane ALIGNED + CONFIRMED 太嚴（白白錯失 super-cycle 進場），對 BIPOLAR 衝突太鬆（容易誤判 BUY）
- Tier × polarization 矩陣 4 種組合對應不同信心 → threshold 動態化
- staged_threshold 永遠 = buy − 0.4 維持比例
- 其他組合（CONFIRMED + MIXED、CANDIDATE + OUTLIER、NONE + ALIGNED 等）走 default — 漸進式 conviction，不所有 tier 都改

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

## PHASE 4.5 — FAIR VALUE SUMMARY (V5.0 NEW)

PM **inline deterministic 計算**。**禁止 LLM 重新評估數字** — 純 anchor weighted blend。

### 算法

```python
# 從 Valuation Specialist (Phase 2) 拿 valuation_anchors
anchors = phase2.valuation_specialist.valuation_anchors
weights_default = {
  "dcf_unlevered":      0.30,
  "dcf_levered":        0.15,
  "analyst_pt_consensus": 0.20,
  "peer_pe_implied":    0.20,
  "owner_earnings_mult": 0.10,
  "forecaster_blend":   0.05,
}

# 缺 anchor → weight 重分配
available = {k: v for k, v in anchors.items() if v is not None and v > 0}
total_w = sum(weights_default[k] for k in available)
weights_norm = {k: weights_default[k] / total_w for k in available}

weighted_fair_value = sum(weights_norm[k] * available[k] for k in available)
current_price = ticker_data_bundle["scoring"]["price"]
vs_current_pct = (weighted_fair_value - current_price) / current_price * 100

# Verdict band
if vs_current_pct >= 30:   verdict_band = "extreme_undervalued"
elif vs_current_pct >= 10: verdict_band = "undervalued"
elif vs_current_pct >= -10: verdict_band = "fairly_valued"
elif vs_current_pct >= -30: verdict_band = "overvalued"
else:                       verdict_band = "extreme_overvalued"

# Confidence by anchor count
if len(available) >= 5:    confidence = "high"
elif len(available) >= 3:  confidence = "medium"
else:                       confidence = "low"
```

### 輸出

```json
{
  "phase": "4.5",
  "agent": "Portfolio_Manager",
  "fair_value_summary": {
    "anchors": {
      "dcf_unlevered":        "float|null",
      "dcf_levered":          "float|null",
      "analyst_pt_consensus": "float|null",
      "peer_pe_implied":      "float|null",
      "owner_earnings_mult":  "float|null",
      "forecaster_blend":     "float|null"
    },
    "weights_used": {"dcf_unlevered": 0.32, "dcf_levered": 0.16, ...},  // 重分配後
    "weighted_fair_value":  "float",
    "current_price":        "float",
    "vs_current_pct":       "float",
    "verdict_band":         "extreme_undervalued | undervalued | fairly_valued | overvalued | extreme_overvalued",
    "confidence":           "high | medium | low",
    "anchors_available":    "int 0-6",
    "methodology_note":     "string — e.g. '5/6 anchors used; owner_earnings_mult unavailable, weight redistributed'"
  }
}
```

### 與 Valuation lane 的關係
- Valuation Specialist (Phase 2) 給 lane score（-5 ~ +5）參與加權
- `fair_value_summary` (Phase 4.5) 給 deterministic 數字呈現給 user（"合理股價 $215，現價 $285，溢價 32.5%"）
- 兩者都用同一組 anchor，但 Specialist 是 LLM 詮釋（含 narrative），Phase 4.5 是純算數

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
    6. **合理股價估算 (V5.0 新 section)**: anchors 6 行 + weighted_fair_value + verdict_band + confidence
    7. **Red Team Counter Thesis (V2.14.0 IC-memo 結構強化)**:
       - **Consensus View (市場共識)**: 1-2 句 — 主流分析師 / 媒體普遍認同的看法（從 Phase 2 News + Sentiment lane 抽）
       - **Differentiated View (本委員會差異化判斷)**: 1-2 句 — 本次分析跟 consensus 哪裡不同、為什麼（from final_decision + final_score 的關鍵 driver）
       - **Counter Thesis**: red_team_counter_thesis 全文
       - **Numbered Kill Conditions**: 必須 numbered list（1. / 2. / 3.），每條 falsifiable + 可量化（red_team_kill_conditions 直接照搬 + 編號）。禁 free-form 段落
    8. **進場計畫 (V2.14.0 Returns Profile 三檔)**:
       - **Base Case**: 進場區間 + TP1 / TP2 + SL + R/R（雙軌 staged_split）+ position_size_pct
       - **Bull Case (1-2 句)**: 若 base case 觸發後 follow-through，下一個 TP3 / 加碼條件 / 持有窗口（從 fair_value_summary verdict_band + watch_conditions 推）
       - **Bear Case (1-2 句)**: 若 SL 觸發 / kill condition 命中 → exit 行為 + 不再進場條件
    9. 關鍵風險（key_risks 條列）
    10. Watch / re-eval 觸發條件（watch_conditions dict 全列，加觀察 metric）

  寫入 `../reports/<YYYYMMDD>_<TICKER>.md`，回傳檔案路徑。
  """
)
```

> **V2.14.0 IC-memo 強化動機**：對齊機構級投資決策備忘錄 (PE 業界標準 ic-memo skill pattern) — 強迫呈現「consensus vs differentiated view」避免 echo chamber，Kill Conditions numbered 加強執行紀律，Returns Profile 三檔給未來 thesis review 一致對照基準。所有欄位來源**仍是** Phase 2-4 已產出 JSON，formatter 不重新評分。

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
