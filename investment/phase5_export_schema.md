# Phase 5 Session Export Schema

> **Schema Version**: `V5.0`
> **Consumer**: `bridge.py` / Dashboard decisions cards / decision history
> **Producer**: Investment Protocol Phase 5 (PM / Sonnet formatter)
> **Last updated**: 2026-05-02
>
> **V5.0 changes vs V4.8**:
> - Added `valuation_lane` to track 5th parallel analyst (Valuation Specialist)
> - Added `fair_value_summary` from Phase 4.5 (deterministic anchor blend)
> - `active_weights_end_of_session` now includes `Valuation` weight (0.15 default)

---

## 目的

本檔案是 `investment/invest_logs/history.json` 每次 Phase 5 新 append 的 entry 之**唯一 shape 事實來源**。Protocol 不再內嵌 JSON 範本 — 任何 schema 變動改這裡就好。

Claude（或 Sonnet 格式化 subagent）在 Phase 5 末尾**必須**：
1. 以本檔的 `FULL EXAMPLE` 為 shape 範本填入本次 session 的真實值
2. 執行 `python3 investment/scripts/validate_session_export.py` — rc ≠ 0 時修正再重跑
3. 禁止輸出本檔 `## DO NOT` 區塊列出的任何 legacy shape

---

## REQUIRED fields（不得省略，HOLD / CANCEL 決策也必填）

### Top-level
| Field | Type | Note |
|---|---|---|
| `session_export_version` | `"V5.0"` | 固定字串；若 protocol 升版，本檔 header + 此欄同步改 |
| `export_date` | `"YYYY-MM-DD"` | 交易會議日期 |
| `date` | `"YYYY-MM-DD"` | 鏡射 `export_date`（舊版相容；bridge.py 兩者都讀）|
| `ticker` | `"STRING"` | 鏡射 `trades_this_session[0].ticker` |
| `final_action` | `"EXECUTE" \| "STAGED" \| "CANCEL"` | 鏡射 `trades_this_session[0].final_action` |
| `phase0_file` | `"./invest_logs/YYYY-MM-DD_phase0.json"` | 對應 Phase 0 cache 檔 |
| `phase0_macro_snapshot` | object | 見下 |
| `trades_this_session` | array (len=1) | **單一事實來源**，所有決策欄位都在這裡 |
| `active_weights_end_of_session` | object | Fundamentals/Sentiment/News/Technical 四權重 |
| `bias_notes` | string | 1-3 句 session 自述：決策邏輯 + 自省偏誤 |
| `last_outcome` | `"WIN" \| "LOSS" \| "UNKNOWN"` | 之前 session 結果（prior context）|

### `phase0_macro_snapshot`
```json
{
  "market_regime": "BULL | BEAR | SIDEWAYS | VOLATILE | RISK_OFF | RISK_ON",
  "macro_backdrop_score": -5.0,
  "macro_multiplier": 0.6,
  "key_themes": ["..."]
}
```

### `trades_this_session[0]` — **核心欄位，全部必填**

| Field | Type | HOLD/CANCEL 時 | Note |
|---|---|---|---|
| `ticker` | string | 填 | |
| `final_action` | `"EXECUTE" \| "STAGED" \| "CANCEL"` | 填 | |
| `final_decision` | `"BUY" \| "STAGED_ENTRY" \| "HOLD" \| "STAGED_EXIT" \| "SELL"` | 填 | |
| `final_score` | float | 填 | |
| `consensus_bonus_applied` | bool | 填 | |
| `red_team_verdict` | `"NO_VIABLE_COUNTER" \| "MODERATE_COUNTER" \| "STRONG_COUNTER"` | 填 | V4.7+ |
| `red_team_counter_thesis` | string | 填 | V4.7+ |
| `red_team_kill_conditions` | array[string] (2-3 條) | 填 | V4.7+ falsifiable |
| `red_team_execution_failed` | bool | 填 | |
| `phase2_fanout_mode` | `"PARALLEL_SUBAGENT" \| "PARTIAL_FALLBACK" \| "FULL_FALLBACK"` | 填 | V4.8 |
| `degraded_analysts` | array[string] | 填（正常情況空陣列）| V4.8 |
| `macro_alignment` | `"ALIGNED" \| "CONTRARIAN"` | **必填** | HOLD 也要 |
| `avg_confidence` | float 0-1 | 填 | |
| `burry_score` | float 0-100 | 填 | |
| `burry_override_active` | bool | 填 | V4.7+ |
| `burry_override_recheck_date` | `"YYYY-MM-DD"` or `null` | 填 | V4.7+ |
| `entry_aggressive` | `[min_str, max_str]` or `null` | HOLD 通常 null；若 MD 報告有觀察區間可填 | |
| `entry_conservative` | `[min_str, max_str]` or `null` | HOLD 若 MD 有再評觸發價位應填 | |
| `take_profit` | number or `null` | HOLD null | |
| `stop_loss` | number or `null` | HOLD null | |
| `risk_reward_ratio` | float or `null` | HOLD null；BUY/STAGED_ENTRY **必填且 ≥ 2.0** | |
| `position_size_pct` | float 0-1 | HOLD 填 0.0 | |
| `staged_split` | `{aggressive_pct, conservative_pct}` or `null` | 僅 STAGED_ENTRY 填 | |
| `position_size_method` | `"VOL_ADJUSTED" \| "RULE_BASED"` | 填 | |
| `ftd_timeline_gate` | `{applied, days_since_ftd, stage, sector_class, multiplier, stop_loss_adjustment_pp, rejection_triggered}` or `null` | **V4.9+ 必填**；`applied=false` 時其他欄位 null | Phase 4 Step 3.5 輸出，記錄 FTD timeline gate 決策軌跡 |
| `fragility_label` | `"ROBUST" \| "MODERATE" \| "FRAGILE"` | **必填** | HOLD 也要（tail-risk-analyzer 輸出）|
| `binary_classification` | `"positive" \| "unknown" \| "negative" \| "none"` | **必填** | |
| `time_horizon` | `"short" \| "mid" \| "long"` | **必填** | HOLD 也要（反映再評窗口長度）|
| `analysis_price` | float | **必填（V4.8+）** | 分析當下股價快照（從 Phase 2 Technical analyst 或 us-stock-analysis skill 抓取）。Dashboard 用來比較 vs 即時價的漂移 |
| `macro_context` | string (1-3 句) **繁體中文** | 填 | |
| `watch_conditions` | object（key: snake_case 英文識別名 → value: **繁體中文**描述）| **必填，最少 3 條** | HOLD：填再評 / 退場觸發；BUY：填進場後監控 |
| `key_risks` | array[string] **繁體中文短描述**（非 snake_case）| 填（3-8 條）| 例：「RSI 98 拋物線過熱衰竭風險」|
| `devils_advocate_filed` | bool | 填 | |
| `trade_metadata` | `{trade_type, event_tag}` | **必填** | trade_type ∈ {event, trend, mean_reversion} |
| `valuation_lane` | `{signal, score, confidence, weighted_fair_value, vs_current_pct}` | **V5.0+ 必填** | Phase 2 第 5 lane Valuation Specialist 輸出 |
| `fair_value_summary` | object（見下） | **V5.0+ 必填** | Phase 4.5 deterministic anchor blend |
| `lane_scores` | `{fundamentals: int, sentiment: int, news: int, technical: int}` | **V2.10.0+ 必填** | Phase 2 五 lane 中除 valuation 外的 4 個 raw score（−3..+3）；用於 polarization detection |
| `det_inputs` | `{altman_z, debt_to_equity, fcf_yield, insider_ratio_q, short_interest_pct, fred_in_sector_avoid}` | **V2.10.0+ 必填** | Red Team kill triggers 的 6 個量化輸入；LLM 從 FMP_SUPP_BUNDLE / earnings-analyst 拿到的原始數值，**直接寫入**，不再 LLM 重新解讀 |
| `det_shadow` | object（見下） | **V2.10.0+ 由 post-processor 寫入**，LLM 不寫 | `apply_det_shadow.py` 後處理填入；包含 polarization label + det shadow scores + agreement flags |
| `technical_lane` | object（見 V2.13 章節） | **V2.13.0+ 必填** | smart_money / pattern / market_strength / key_levels / high_prob_scenario |
| `fundamentals_lane` | object（見 V2.13 章節） | **V2.13.0+ 必填** | moat_assessment / near_term_catalysts / bull_thesis / bear_thesis |
| `news_lane` | object（見 V2.13 章節） | **V2.13.0+ 必填** | immediate_catalyst_5d / medium_term_shift_20d / decision_point_days / cross_asset_spillover |
| `institutional_lens` | string | **V2.13.0+ 必填** | Phase 3 PM 1-2 句機構流向整合 narrative |
| `decision_confidence_pct` | int 0-100 | **V2.13.0+ 必填** | Phase 3 PM 決策信心度百分比 |
| `scenario_odds` | `{bull, base, bear}` int 加總 100 | **V2.13.0+ 必填** | Phase 3 PM 三劇本機率 |
| `action_label` | `ATTACK \| WAIT \| DEFENSIVE` | **V2.13.0+ 必填** | Phase 3 PM 動作建議（與 final_action 並存，不取代） |

### `valuation_lane` (V5.0)
```json
{
  "signal": "BUY | HOLD | SELL",
  "score": "float -5 to +5",
  "confidence": "float 0-1",
  "weighted_fair_value": "float — Specialist 計算的合理價",
  "vs_current_pct": "float — (fair - current) / current * 100"
}
```

### `fair_value_summary` (V5.0 — Phase 4.5)
```json
{
  "anchors": {
    "dcf_unlevered":        "float|null",
    "dcf_levered":          "float|null",
    "analyst_pt_consensus": "float|null",
    "peer_pe_implied":      "float|null",
    "owner_earnings_mult":  "float|null",
    "forecaster_blend":     "float|null"
  },
  "weights_used":         "object — 重分配後的權重（缺 anchor 時 sum=1.0）",
  "weighted_fair_value":  "float",
  "current_price":        "float",
  "vs_current_pct":       "float",
  "verdict_band":         "extreme_undervalued | undervalued | fairly_valued | overvalued | extreme_overvalued",
  "confidence":           "high | medium | low",
  "anchors_available":    "int 0-6",
  "methodology_note":     "string — e.g. '5/6 anchors used; owner_earnings_mult unavailable, weight redistributed'"
}
```

### `lane_scores` (V2.10.0)

LLM 在 Phase 2 末尾彙總 4 個 lane 各自最終 raw score，寫入 trades_this_session[]：

```json
{
  "fundamentals": "int -3 to +3 — Fundamentals lane 最終分數",
  "sentiment":    "int -3 to +3 — Sentiment lane 最終分數",
  "news":         "int -3 to +3 — News lane 最終分數",
  "technical":    "int -3 to +3 — Technical lane 最終分數"
}
```

> Valuation lane score 已存於 `valuation_lane.score`，不重複。

### `det_inputs` (V2.10.0)

LLM 從 Phase 2 / Phase 4.5 bundle 取得的 6 個量化原始值（**直接抄寫，不重新判讀**）：

```json
{
  "altman_z":             "float | null — FMP_SUPP_BUNDLE.quality_scores.altmanZScore",
  "debt_to_equity":       "float | null — earnings-analyst slim_ttm_keymetrics.debtToEquityRatio",
  "fcf_yield":            "float | null — slim_ttm_keymetrics.freeCashFlowYield × 100（轉成 %）",
  "insider_ratio_q":      "float | null — FMP_SUPP_BUNDLE.insider_summary.quarters[0].acquired_disposed_ratio",
  "short_interest_pct":   "float | null — Phase 2 Sentiment bundle short interest（%）",
  "fred_in_sector_avoid": "bool — phase0.fred_snapshot.sector_rotation_avoid 是否含此 ticker 的 sector"
}
```

> 任一欄位若 bundle 該回合未取得 → 填 null。`apply_det_shadow.py` 對 missing 欄位 graceful skip（≥3 個有效才出 verdict）。

### `det_shadow` (V2.10.0 — post-processor 寫入)

由 `python3 investment/scripts/apply_det_shadow.py` 在 Phase 5 末尾跑出來，附加到每筆 trade：

```json
{
  "version":              "V2.10.0",
  "signal_polarization":  "ALIGNED | MIXED | BIPOLAR — 從 5 lane 分布判斷",
  "polarization_detail":  {
    "label":         "...",
    "range":         "float — max−min",
    "max":           "float — highest lane score",
    "min":           "float — lowest lane score",
    "missing_lanes": "array[string] — 缺哪幾個 lane（lane_scores 沒填齊時）"
  },
  "valuation_score_det":  "float | null — 純從 weighted_fair_value vs price 算的 [-1, +1] 分數",
  "val_agreement":        "AGREE | DRIFT | DISAGREE — LLM val score vs det 差距 (≤0.25/≤0.75/>0.75)",
  "red_team_verdict_det": "NO_VIABLE_COUNTER | MODERATE_COUNTER | STRONG_COUNTER — 純從 6 kill triggers 數量",
  "red_team_detail":      {
    "verdict":     "...",
    "kill_count":  "int 0-6",
    "triggered":   "array[string] — 哪幾條 trigger 觸發",
    "missing":     "array[string] — det_inputs 缺哪幾個欄位"
  },
  "red_team_agreement":   "AGREE | DISAGREE — LLM red_team_verdict vs det"
}
```

**Polarization 規則**：
- `BIPOLAR`：range ≥ 4 AND 任一 lane ≥ +2 AND 任一 lane ≤ −2（極端兩極）
- `MIXED`：range ≥ 3 AND 至少一正一負（有分歧但不極端）
- `ALIGNED`：以上都不滿足（訊號方向一致）

**Det Valuation 閾值表**（`vs_current_pct` % → score）：
| upside % | det score |
|---|---|
| ≥ +30% | +1.0 |
| ≥ +10% | +0.5 |
| ≥ −5% | 0 |
| ≥ −20% | −0.5 |
| < −20% | −1.0 |

**Red Team kill triggers**：6 條全部量化條件（Altman<1.8 / D/E>5 / FCF<0 / insider<0.3 / short>20% / FRED sector_avoid）；count ≥ 5 = STRONG，≥ 3 = MODERATE，否則 NO_VIABLE_COUNTER。

**用途**：rubric / score 公式不變；新欄位提供「LLM 是否與量化規則一致」+「訊號是否兩極化」的 sanity check 維度。Dashboard 會把 BIPOLAR / DISAGREE 顯示為 badge。

---

## FULL EXAMPLE（V5.0 — 以 BUY 決策為範本）

```json
{
  "session_export_version": "V4.8",
  "export_date": "2026-04-18",
  "date": "2026-04-18",
  "ticker": "MU",
  "final_action": "EXECUTE",
  "phase0_file": "./invest_logs/2026-04-18_phase0.json",
  "phase0_macro_snapshot": {
    "market_regime": "RISK_ON",
    "macro_backdrop_score": -1.0,
    "macro_multiplier": 0.9,
    "key_themes": ["AI_Semi_AVOID", "Iran_Hormuz_48_72h", "SPY_extreme_overbought"]
  },
  "trades_this_session": [
    {
      "ticker": "MU",
      "final_action": "EXECUTE",
      "final_score": 1.746,
      "final_decision": "BUY",
      "consensus_bonus_applied": false,
      "red_team_verdict": "STRONG_COUNTER",
      "red_team_counter_thesis": "196%YoY + Fwd P/E 4.5x 是記憶體週期頂部誤判…",
      "red_team_kill_conditions": [
        "IF MU 收盤 < MA50 (~$420) WITHIN 10 交易日 + 量 > 1.5×avg THEN Stage 2 失效",
        "IF 任一記憶體同業 30 天內下修 HBM ASP guidance THEN super-cycle 敘事崩塌",
        "IF 48-72h 內 Iran/Hormuz 觸發 VIX > 25 THEN RISK_ON 前提瓦解"
      ],
      "red_team_execution_failed": false,
      "phase2_fanout_mode": "PARALLEL_SUBAGENT",
      "degraded_analysts": [],
      "macro_alignment": "CONTRARIAN",
      "avg_confidence": 0.703,
      "burry_score": 37.1,
      "burry_override_active": false,
      "burry_override_recheck_date": null,
      "entry_aggressive": ["448", "462"],
      "entry_conservative": ["405", "425"],
      "take_profit": 540,
      "stop_loss": 415,
      "risk_reward_ratio": 2.13,
      "position_size_pct": 0.0203,
      "staged_split": null,
      "position_size_method": "VOL_ADJUSTED",
      "fragility_label": "FRAGILE",
      "binary_classification": "unknown",
      "time_horizon": "mid",
      "analysis_price": 455.07,
      "macro_context": "RISK_ON 但 macro_backdrop -1.0…（1-3 句）",
      "watch_conditions": {
        "ma50_break": "Close < $415 + 量 > 1.5× 20D avg → Stage 2 失效",
        "peer_capex_cut": "SK Hynix / Samsung HBM / WDC 30 天內下修 ASP guidance",
        "insider_resume_selling": "Q2 財報前 45 天內新增 > $20M 淨賣出",
        "macro_binary_trigger": "VIX 單日 > 25 或 SPY < -2%（Iran/Hormuz 事件）",
        "exit_stop": "跌破 $415 (MA50) + 放量 → 觸發退場"
      },
      "key_risks": [
        "記憶體週期頂部誤判風險",
        "內部人淨賣出群聚訊號",
        "AI 主題動能衰退疊加宏觀壓制",
        "52 週高點附近低量拉升",
        "伊朗/霍爾木茲 48-72h 二元風險",
        "尾部風險極高（脆弱分數 60）"
      ],
      "devils_advocate_filed": false,
      "trade_metadata": {
        "trade_type": "trend",
        "event_tag": "earnings"
      },
      "valuation_lane": {
        "signal": "BUY",
        "score": 2.5,
        "confidence": 0.7,
        "weighted_fair_value": 525.50,
        "vs_current_pct": 15.5
      },
      "fair_value_summary": {
        "anchors": {
          "dcf_unlevered":        510.20,
          "dcf_levered":          495.80,
          "analyst_pt_consensus": 540.00,
          "peer_pe_implied":      520.30,
          "owner_earnings_mult":  528.00,
          "forecaster_blend":     null
        },
        "weights_used": {"dcf_unlevered": 0.32, "dcf_levered": 0.16, "analyst_pt_consensus": 0.21, "peer_pe_implied": 0.21, "owner_earnings_mult": 0.10},
        "weighted_fair_value":  525.50,
        "current_price":        455.07,
        "vs_current_pct":       15.5,
        "verdict_band":         "undervalued",
        "confidence":           "high",
        "anchors_available":    5,
        "methodology_note":     "5/6 anchors used; forecaster_blend unavailable, weight redistributed"
      }
    }
  ],
  "active_weights_end_of_session": {
    "Fundamentals": 0.25,
    "Sentiment": 0.15,
    "News": 0.20,
    "Technical": 0.25,
    "Valuation": 0.15
  },
  "bias_notes": "V5.0 PARALLEL_SUBAGENT 5/5 isolated。…（1-3 句，反映決策理由 + 自省）",
  "last_outcome": "UNKNOWN"
}
```

---

## HOLD / CANCEL 範例片段

HOLD 時不可以把 shape 簡化成 `{ticker, metadata:{…少數欄位}}`。必填欄位的填法：

```json
{
  "final_action": "CANCEL",
  "final_decision": "HOLD",
  "entry_aggressive": null,
  "entry_conservative": ["220", "230"],   // 若 MD 有再評觸發區間也要填
  "take_profit": null,
  "stop_loss": null,
  "risk_reward_ratio": null,
  "position_size_pct": 0.0,
  "staged_split": null,
  "macro_alignment": "CONTRARIAN",         // 必填
  "fragility_label": "FRAGILE",             // 必填
  "binary_classification": "positive",      // 必填
  "time_horizon": "mid",                    // 必填（反映再評窗口）
  "watch_conditions": {                     // 最少 3 條再評 / 退場觸發
    "conservative_entry": "回落 MA20/50 叢集 + RSI < 70 → 重啟 entry 評估",
    "parabolic_breakdown": "收盤 < MA20 5 個交易日 → 拋物線崩跌確認",
    "earnings_catalyst": "2026-05-05 Q2 財報 — guide 低於共識 → 動能失效"
  },
  "trade_metadata": {                       // 必填
    "trade_type": "trend",
    "event_tag": "earnings"
  }
}
```

---

## DO NOT（禁止 shape 清單）

以下 shape 在 V4.8 session 裡**任何情況**都不得出現，違反 → validator 直接 rc=1。

### ❌ Legacy V4.3 flat shape（pre-V4.6）
```json
{
  "date": "…",
  "ticker": "…",
  "final_action": "…",
  "metadata": { "final_score": …, "key_risks": [], … }
}
```
**原因**：缺 `session_export_version` / `trades_this_session` — bridge.py 雖然能勉強解析，但會遺失 V4.8 新增的 red_team / fanout / override 欄位。

### ❌ 只省略 `trades_this_session`
```json
{
  "session_export_version": "V4.8",
  "ticker": "…",
  "final_score": …
}
```
頂層平鋪欄位也不接受 — 一定要走 `trades_this_session[0]`。

### ❌ 用空陣列代替 HOLD 的 `watch_conditions`
HOLD 要填再評觸發，不是 `{}`。

### ❌ `risk_reward_ratio: null` 但 `final_decision: "BUY"`
BUY / STAGED_ENTRY 必填 R/R ≥ 2.0；沒有就應該降級到 HOLD。

---

## 版本更新規則

當 Protocol 升版（例如 V4.8 → V5.0）：
1. 本檔 header `Schema Version` + 正文 `session_export_version` 同步改
2. 如有新欄位 → 加到 REQUIRED table + FULL EXAMPLE
3. 如有欄位改語意 → 加進 DO NOT 區塊說明舊用法禁用
4. 更新 `validate_session_export.py` 的版本檢查與必填清單
5. Protocol 的 Phase 5 章節**不必動**（只引用本檔路徑）

---

## V2.13.0 新欄位明細

V2.13.0 為 invest protocol Phase 2 三個 lane（Technical / Fundamentals / News）+ Phase 3 PM 整合層補強，對齊「外部專業分析師 prompt 模板」。**不影響 final_score 公式**；新欄位皆為 narrative / metadata，validator 不擋（cf V2.10 同 pattern）。

### `technical_lane` (V2.13.0)

```json
{
  "smart_money_analysis": {
    "label": "accumulating | distributing | neutral | mixed",
    "narrative": "string — 1-2 句綜合 insider Q ratio + 量價背離 + analyst flow"
  },
  "pattern_taxonomy": {
    "pattern": "uptrend_breakout | uptrend_continuation | consolidation | pullback_in_uptrend | false_breakout | topping_pattern | downtrend | oversold_bounce_attempt",
    "confirmation_criteria": "string — 1 句說明何條件代表 pattern 成立 / 失效"
  },
  "market_strength": "STRONG | NEUTRAL | WEAK",
  "key_levels": {
    "support": "float | null",
    "resistance": "float | null",
    "pivot": "float | null"
  },
  "high_prob_scenario": "string — 1 句話描繪未來 5-15 天最有機率走法（含具體價位 + 觸發條件）"
}
```

### `fundamentals_lane` (V2.13.0)

```json
{
  "moat_assessment": {
    "level": "WIDE | NARROW | ERODING | NONE",
    "type": "brand | IP_patent | switching_cost | scale_economies | network_effect | regulation | none",
    "evidence_one_line": "string — 1 句量化依據"
  },
  "near_term_catalysts": [
    {
      "date": "ISO YYYY-MM-DD or quarter notation '2026-Q3'",
      "type": "earnings | guidance | product_launch | analyst_day | M&A | macro_event",
      "description": "string",
      "impact": "high | medium | low"
    }
  ],
  "bull_thesis_one_line": "string ≤ 40 字 — 真正強在哪（量化證據）",
  "bear_thesis_one_line": "string ≤ 40 字 — 市場擔心什麼（量化反駁）"
}
```

### `news_lane` (V2.13.0)

```json
{
  "immediate_catalyst_5d": {
    "event": "string",
    "date": "ISO YYYY-MM-DD",
    "direction_lean": "BULLISH | BEARISH | NEUTRAL",
    "expected_move_pct": "float | null"
  } | null,
  "medium_term_shift_20d": {
    "narrative": "string — 1 句話描繪 5-20 天可能 narrative 移轉",
    "label": "BULLISH | BEARISH | NEUTRAL"
  },
  "decision_point_days": "int — 下次該重新評估的天數（預設 21，binary 事件當天）",
  "cross_asset_spillover": [
    {
      "asset": "treasury_10y | DXY | oil_WTI | gold | copper | sector_<XLX> | VIX | none",
      "direction": "BULLISH | BEARISH | NEUTRAL",
      "mechanism": "string — 1 句說明傳導路徑"
    }
  ]
}
```

### Phase 3 PM 整合層新欄位

直接掛在 `trades_this_session[]` 上（不包在 sub-object）：

| 欄位 | 型別 | 說明 |
|---|---|---|
| `institutional_lens` | string | 1-2 句機構流向 narrative，整合 Sentiment.institutional + congressional_trades + FTD + (V2.9.0) `institutional_holders_qoq_delta`；矛盾訊號要點出 |
| `decision_confidence_pct` | int 0-100 | 決策信心度百分比；與 `avg_confidence` (0-1) 共存 |
| `scenario_odds` | `{bull: int, base: int, bear: int}` | 三劇本機率，**加總必須 = 100** |
| `action_label` | `ATTACK \| WAIT \| DEFENSIVE` | 動作建議，與 `final_action` 並存補強 sizing 提示 |

**`action_label` 對映規則**：
- `ATTACK`：BUY 且 confidence ≥ 70%；或 STAGED_ENTRY 第一階段條件已成
- `WAIT`：STAGED_ENTRY 第二階段；或 HOLD 但有 watch 條件接近觸發
- `DEFENSIVE`：HOLD 但訊號矛盾；SELL；STAGED_EXIT；或 BUY 但 confidence < 50%

### Validator 對 V2.13 欄位的處理

V2.13 新欄位 **皆為 informational**：
- `validate_session_export.py` **不**將其列為 hard-required
- 缺值不擋 rc=0；統計 `--coverage-report` 旗標可顯示新欄位非空率
- LLM 應遵守 protocol 內 "必填" 規定（缺資料寫 `INSUFFICIENT_DATA` 而非 null），但 schema 層級不強制 — 累積 30+ run 後再評估是否提升至 hard-required

