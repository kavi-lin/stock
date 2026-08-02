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
| `red_team_counter_evidence_strength` | int 1-5 or `null` | optional **(V4.70.0+, P0-2)** | Phase 2.8 subagent 的 strength 輸出。Phase 3 rule 4 用它分級懲罰（5→×0.85 / 4→×0.925）；export 供 ≥20 session 後 outcome 校準 |
| `red_team_thesis_break_probability` | float 0-1 or `null` | optional **(V4.70.0+, P0-2)** | Red Team 估 counter_thesis 在最長 kill window 內成立的機率。**僅記錄不進決策數學**——校準檢驗（AUDIT_2026-07-16 檢驗 A 的後續）用 |
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
| `valuation_lane` | `{signal, score, confidence, weighted_fair_value, vs_current_pct}` | **V5.0+ 必填** | reviewer narrative + `valuation_pack` projection；LLM 不得產數字 |
| `valuation_pack` | object（見下） | **新 engine output 必填**；舊 history 相容 | Phase 2.4 唯一估值計算權威；validator 強制所有 projection 相等 |
| `fair_value_summary` | object（見下） | **V5.0+ 必填** | `valuation_pack` 相容 projection（= MHP 長期層、受 decision_lock 保護）|
| `multi_horizon_price_framework` | object（見下） | **V5.1+ optional→required**；缺/不全 → validator 印 warning（非 fatal，rc 維持 0）| Phase 4.5 三時間框架（5d band / 60d target / long-term ref / convergence）。**不**進 11-field decision_lock（derived/advisory）|
| `fair_value_range` | object（見下） | **V3.45.1+ optional**；缺 → validator warning（非 fatal，rc 0）| Phase 4.5.0b anchor 分布區間（P25/P50/P75 + range_verdict + dispersion + oe shadow）。**不**進 decision_lock；`fair_value_summary` 不變 |
| `valuation_explained_range` | object（見下） | **V4.76.0+ optional** | structural-shift DCF 為 primary FV；DCF sensitivity + without/with-peer + 其他 eligible anchor 的解釋帶。range-only peer 不進 primary FV |
| `implied_expectations` | object（掛 `valuation_lane` 或 trade 頂層；見下） | **V3.45.1+ optional**；缺 → warning（rc 0）| reverse DCF 隱含預期。**V3.45.3 起由 Phase 2.4 `compute_price_framework.py` engine 計算**（非 LLM 手算）。**不**進加權 / lane score / decision_lock |
| `valuation_archetype_shadow` | object（見下） | **V3.46.0+ optional**；缺 → warning（rc 0）| Phase 2.4 engine archetype 分類 + 9-anchor shadow blend。**shadow-only** — live `fair_value_summary` 不動、不進 decision_lock。≥20 session 翻轉率報告後才議切換（#3b）|
| `lane_scores` | `{fundamentals: int, sentiment: int, news: int, technical: int}` | **V2.10.0+ 必填** | Phase 2 五 lane 中除 valuation 外的 4 個 raw score（−5..+5，V4.72.0 修正——原文件誤寫 −3..+3 與協議 Phase 2 量表矛盾，歷史 9 筆合法 ±4 分即超出舊註記）；用於 polarization detection。validator §12 強制值域 |
| `det_inputs` | `{altman_z, debt_to_equity, fcf_yield, insider_ratio_q, short_interest_pct, fred_in_sector_avoid}` | **V2.10.0+ 必填** | Red Team kill triggers 的 6 個量化輸入；LLM 從 FMP_SUPP_BUNDLE / earnings-analyst 拿到的原始數值，**直接寫入**，不再 LLM 重新解讀 |
| `det_shadow` | object（見下） | **V2.10.0+ 由 post-processor 寫入**，LLM 不寫 | `apply_det_shadow.py` 後處理填入；包含 polarization label + det shadow scores + agreement flags |
| `technical_lane` | object（見 V2.13 章節） | **V2.13.0+ 必填** | smart_money / pattern / market_strength / key_levels / high_prob_scenario |
| `fundamentals_lane` | object（見 V2.13 章節） | **V2.13.0+ 必填** | moat_assessment / near_term_catalysts / bull_thesis / bear_thesis |
| `news_lane` | object（見 V2.13 章節） | **V2.13.0+ 必填** | immediate_catalyst_5d / decision_point_days / cross_asset_spillover（`medium_term_shift_20d` V4.71.0 落日移除） |
| `institutional_lens` | string | **V2.13.0+ 必填** | Phase 3 PM 1-2 句機構流向整合 narrative |
| `decision_confidence_pct` | int 0-100 | **V2.13.0+ 必填** | Phase 3 PM 決策信心度百分比 |
| `scenario_odds` | `{bull, base, bear}` int 加總 100 | **V2.13.0+ 必填** | Phase 3 PM 三劇本機率 |
| `action_label` | `ATTACK \| WAIT \| DEFENSIVE` | **V2.13.0+ 必填** | Phase 3 PM 動作建議（與 final_action 並存，不取代） |
| `thesis_id` | string or `null` | optional | **V2.14.0+** Phase 5.5 trader-memory-core register 後回填的 thesis lifecycle ID（e.g. `nvda-2026-05-06-001`）；register 失敗 / skip 時 null。Dashboard 用此 ID 拉 review queue |
| `thesis_registered_at` | `"YYYY-MM-DDTHH:MM:SSZ"` or `null` | optional | **V2.14.0+** Phase 5.5 register 完成的 ISO timestamp；null = 未 register |
| `decision_cap_active` | bool | optional **(V5.0.x+)** | Phase 4.6 — true 表示 valuation 證據不足，cap 已套用（不得 BUY、conf ≤ 0.65、size ≤ 30bps）。預設 false 視為未觸發 |
| `decision_cap_reason` | `"insufficient_anchors" \| "low_valuation_confidence" \| "low_data_quality"` or `null` | required if `decision_cap_active=true` | 觸發 cap 的具體原因。Validator (`validate_session_export.py` § 10) 強制此 enum |
| `cap_override_reason` | string or `null` | optional | PM 在 cap active 時若有重大 catalyst,可填 1 句說明保留 STAGED_ENTRY 路徑;不解除 size/conf cap |
| `hot_zone_probe` | bool | optional **(V5.0.x+, Rec 11)** | 熱區保守性鬆綁觸發旗標。true 表示正分模糊區 `[0,+staged)` × `industry_top_30pct` × `RISK_ON/BULL` 把 default HOLD 降為小倉 probe。觸發時強制 `final_decision=STAGED_ENTRY`、`position_size_pct ≤ tier 上限`、且 `decision_cap_active != true`。Validator (`validate_session_export.py` § 11) 強制。預設 false |
| `hot_zone_probe_tier` | `"t1_15bps" \| "t2_30bps"` or `null` | required if `hot_zone_probe=true` **(V4.70.0+, P0-1)** | 分數分層 probe size：`final_score ≥ 0.4` → t2（≤30bps）/ `< 0.4` → t1（≤15bps）。依據 AUDIT_2026-07-16 replay（上半帶 mean +17.6% up 10/15 vs 下半帶 −1.2%）。Validator §11 按 tier 強制 size 上限 |
| `hot_zone_eval` | `"fired" \| "suppressed_by_risk_flag" \| "suppressed_by_cap" \| "not_qualifying"` | **required (V5.0.x+, TODO-015)** | Rec 11 評估結果，不論是否 probe 一律寫出，使驗收不再盲飛。判定樹見 `investment_protocol_v5_0.md` Rec 11 段。Validator §11 強制：`hot_zone_probe=true ⟺ hot_zone_eval="fired"`。extractor 對缺欄的歷史報告反推 `hot_zone_eval_derived`（含 `qualifying_unexplained` 告警值） |

### `valuation_lane` (V5.0)
```json
{
  "signal": "BUY | HOLD | SELL",
  "score": "float -3 to +3 — verbatim valuation_pack.score",
  "confidence": "float 0-1",
  "weighted_fair_value": "float — verbatim valuation_pack.weighted_fair_value",
  "vs_current_pct": "float — verbatim valuation_pack.vs_current_pct"
}
```

### `valuation_pack`（canonical；唯一 builder=`compute_price_framework.py`）

```json
{
  "schema": "valuation_pack.v1",
  "engine": "string",
  "current_price": "float",
  "anchors": {
    "<anchor>": {
      "value": "float|null",
      "family": "fundamental|relative|external_expectations",
      "correlation_group": "string",
      "assumption_set_id": "deterministic hash",
      "provenance": "string|null",
      "as_of": "YYYY-MM-DD|null",
      "status": "eligible|ineligible",
      "reason": "string|null",
      "weight_raw": "float",
      "weight_effective": "float"
    }
  },
  "families": "object — group median → family representative",
  "families_present": ["fundamental", "relative"],
  "family_coverage_weight": "float",
  "aggregation_mode": "dcf_primary_anchor_range|complete_fixed_family_weights|degraded_equal_family_votes|unavailable",
  "primary_method": "dcf_self_built|family_aggregation",
  "family_blended_fair_value": "float|null — DCF-primary 時僅供 scenario/audit",
  "weighted_fair_value": "float|null",
  "vs_current_pct": "float|null",
  "verdict_band": "string|null",
  "score": "float|null",
  "confidence": "high|medium|low"
}
```

Reverse DCF 不在 anchors 中，只是 market-implied diagnostic。缺 `provenance/as_of` 的 anchor
不得 eligible；relative anchor 缺 `peer_count` 或少於 3 個 business-similar peers時不得 eligible；
analyst PT 超過 180 天不得 eligible；少於兩個獨立 family 時 `|score| < 2`。

### `fair_value_summary` (V5.0 — Phase 4.5)
```json
{
  "anchors": {
    "dcf_unlevered":        "float|null",
    "dcf_levered":          "float|null",
    "dcf_self_built":       "float|null — V4.69.0+（valuation-modeler dcf.py）；舊 entry 無此 key，validator 不強制",
    "analyst_pt_consensus": "float|null",
    "peer_pe_implied":      "float|null",
    "comps_implied":        "float|null — V4.69.0+（valuation-modeler comps.py）；舊 entry 無此 key，validator 不強制",
    "owner_earnings_mult":  "float|null",
    "forecaster_blend":     "float|null"
  },
  "anchors_effective":     "object — 僅 eligible anchors；排除者為 null，MHP 等 downstream 只讀此欄",
  "weights_used":         "object — valuation_pack effective weights projection",
  "weighted_fair_value":  "float",
  "current_price":        "float",
  "vs_current_pct":       "float",
  "verdict_band":         "extreme_undervalued | undervalued | fairly_valued | overvalued | extreme_overvalued",
  "confidence":           "high | medium | low（獨立 family coverage + dispersion cap）",
  "anchors_available":    "int 0-8（V4.69.0 前的 entry 為 0-6；V4.70.0+ 為修剪後 count）",
  "families_present":     "array[string]",
  "excluded_anchors":     "object anchor→reason",
  "valuation_pack_schema": "valuation_pack.v1",
  "methodology_note":     "string",
  "outlier_diagnostics":  "array[{anchor,value,reason}] optional；只警示，不剔除 live anchor"
}
```

### `multi_horizon_price_framework` (V5.1 — Phase 4.5)

三時間框架 deterministic 輸出（0 LLM 重評）。長期層 `long_term_ref` 直接引用 `fair_value_summary`，不複製不重算。
**不**進 11-field decision_lock。缺料降級：`sigma_daily` 缺 → short_term confidence=low（atr 反推）；`mid_target` 全錨缺 → null。
**V3.45.3 起整包由 Phase 2.4 `compute_price_framework.py` 計算**（含 `fair_value_summary` blend / `fair_value_range` / 本 block / `implied_expectations`），
PM verbatim 抄寫；block 內含 `engine` stamp（audit 用，optional 欄位）。

```json
{
  "short_term_5d": {
    "band":             ["float band_lower", "float band_point", "float band_upper"],
    "band_capped":      ["float lower_capped", "float band_point", "float upper_capped"],
    "drift_sigma":      "float — clamp [-0.6, +0.5]",
    "sigma_daily":      "float | null — 20D 日報酬標準差（小數）",
    "atr_14":           "float | null",
    "confidence":       "high | medium | low",
    "catalyst_widened": "bool — 5d 內 binary 事件放大帶寬 + 降信心",
    "key_level_note":   "string — 哪邊被 support/resistance 反射"
  },
  "mid_term_60d": {
    "momentum_target":    "float | null — current × (1 + 20d_mom% × decay 0.5)",
    "pt_60d":             "float | null — analyst PT 折算到 60d",
    "earnings_revision":  "float | null — forecaster_blend 近端值",
    "weights_used":       "object — 重分配後（sum=1.0）",
    "mid_target":         "float | null — 0.40 mom + 0.35 pt_60d + 0.25 earn",
    "reality_check_note": "string — vs key_levels 成立條件"
  },
  "long_term_ref": {
    "weighted_fair_value": "float — 引用自 fair_value_summary，不重算",
    "verdict_band":        "string — 引用自 fair_value_summary",
    "confidence":          "string — 引用自 fair_value_summary"
  },
  "convergence": {
    "mhp_signal":  "wait_for_pullback | high_conviction_long_zone | momentum_not_value | neutral_aligned",
    "signal_note": "string — 1 句解釋三框相對位置"
  }
}
```

### `fair_value_range` (V3.45.1 — Phase 4.5.0b，advisory sibling)

Legacy anchor 分布區間。**不**進 11-field decision_lock；決策數字仍只讀
`fair_value_summary`。V4.76.0 structural-shift DCF-primary 模式另以
`valuation_explained_range` 呈現方法差異，不回寫 primary FV。
`agreement_grade` / `anchor_dispersion_cv` 為**純展示**（3.45.1 不接 Phase 4.6 cap，接線留 P2）。
`owner_earnings_multiple_shadow` 為 shadow-log（live anchor 仍 static ×15，不回寫 weighted_fair_value）。

```json
{
  "range_method":  "weighted_percentile | minmax_fallback | null",
  "p25":           "float | null",
  "p50":           "float | null — median；不取代 weighted_fair_value 的決策角色",
  "p75":           "float | null",
  "min_anchor":    "float | null",
  "max_anchor":    "float | null",
  "range_verdict": "undervalued_zone | fair_zone | overvalued_zone | extreme_undervalued | extreme_overvalued | null",
  "anchor_dispersion_cv": "float | null — weighted std/mean",
  "agreement_grade":      "high | medium | low | null — cv<0.15 high / <0.35 medium / else low",
  "anchors_used_n":       "int 0-8（V4.69.0 前的 entry 為 0-6）",
  "owner_earnings_multiple_shadow": {
    "oe_mult_static":      "float — 15（live anchor 用值，不變）",
    "oe_mult_rate_linked": "float | null — clamp(1/(treasury_10y_real+0.04), 10, 22)",
    "required_yield":      "float | null"
  }
}
```

> 退化（V3.45.1 spec）：`anchors_used_n >= 4` → percentile；`2..3` → `minmax_fallback`（[min, median, max]）；`<2` → range 整組 null。

### `valuation_explained_range`（V4.76.0 — DCF-primary presentation）

```json
{
  "available": "bool",
  "primary_fv": "float — eligible structural-shift DCF",
  "primary_sensitivity": {"low": "float", "high": "float"},
  "scenario_without_peer": "float|null — fundamental family representative",
  "scenario_with_peer": "float|null — without-peer 與 range-only relative family 等權點",
  "peer_pe_range_anchor": "float|null — ≥3 audited adjacent peers；非 primary",
  "other_eligible_anchors": "object",
  "range_low": "float",
  "range_high": "float",
  "range_low_driver": "string",
  "range_high_driver": "string",
  "peer_symbols": "array[string]",
  "limitations": "array[string]"
}
```

### `implied_expectations` (V3.45.1 — Phase 2 Valuation Specialist，reverse DCF)

現價隱含的未來 5 年 FCF CAGR。**不**進加權 / lane score / decision_lock — 純 Red Team 素材 + sanity check。

```json
{
  "implied_5y_fcf_cagr":  "float | null — FCF ≤ 0 → null",
  "wacc_used":            "float — FRED treasury_10y + ERP 0.045",
  "fcf_base":             "float | null",
  "fcf_base_source":      "owner_earnings",
  "terminal_growth":      0.025,
  "actual_3y_fcf_cagr":   "float | null",
  "lane_fcf_estimate":    "float | null",
  "sanity_note":          "string",
  "red_team_kill_seed":   "string — falsifiable kill condition 起點"
}
```

### `valuation_archetype_shadow` (V3.46.0 — Phase 2.4 engine，shadow-only)

固定 anchor 權重對未獲利成長股 / 金融股半殘 → archetype 動態權重。**live `fair_value_summary` 不動**；
本 block 純 shadow 累積翻轉率數據（#6 oe shadow 同模式），**不**進 decision_lock。

```json
{
  "archetype": "financial | hypergrowth | cyclical | mature_cashflow | balanced",
  "rule_hit": "string — 命中規則 + 觸發值（audit）",
  "missing_inputs": ["string — 缺哪些判定輸入"],
  "new_anchors": {
    "peer_ev_ebitda_implied": "float | null — (peer_med × EV/self_mult − netDebt)/shares",
    "peer_ev_sales_implied":  "float | null",
    "pb_roe_justified":       "float | null — (ROE−g)/(r−g) × BVPS，clamp [0.2,15]"
  },
  "anchors_used_n": "int 0-11（V4.69.0 起池含 dcf_self_built / comps_implied；之前為 0-9）",
  "weights_used": "object — archetype 權重重分配後（sum=1.0）",
  "weighted_fair_value_shadow": "float | null",
  "vs_current_pct_shadow":      "float | null",
  "verdict_band_shadow":        "extreme_undervalued | undervalued | fairly_valued | overvalued | extreme_overvalued | null",
  "flip_vs_live": "bool | null — verdict_band_shadow != fair_value_summary.verdict_band",
  "note": "string"
}
```

> 權重表單一事實來源：`compute_price_framework.py` `ARCHETYPE_WEIGHTS`。`balanced` = live 權重 +
> 新 anchor 0 → shadow==live、flip=false（自驗路徑）。PEER_BUNDLE V3.46.0 新欄：`peer_ev_ebitda_median` /
> `peer_ev_sales_median` / `peer_pb_median` / `peer_ratios_n` / `self_ratios_ttm`。

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

### `calculation_steps` + `decision_engine_version` (V4.80.0 — Phase 3 engine)

Phase 3 全部算術由 `investment/scripts/decision_engine.py` 產出，PM **verbatim 抄寫**整塊。
欄位明細見 `investment_protocol_v5_0.md` §PHASE 3 的 export shape；此處只記 validator 契約：

| 欄 | 型別 | 說明 |
|---|---|---|
| `decision_engine_version` | `string` | engine 版號（如 `"1.0.0"`）。**有此欄 = 走 V4.70.0+ 規則**，validator 加驗規則表 |
| `calculation_steps.penalty_value` | `float｜null` | 實際套用的 cascade 乘數（0.85 / 0.925 / 0.95）；`penalty_applied=true` 時必填 |
| `calculation_steps.cascade_rule_applied` | `string` | `no_penalty` / `consensus_bonus` / `rule_1..5_*`；與 `penalty_value` 必須對得上 |
| `calculation_steps.red_team_effective_verdict` | `string` | rule 1 降級後的 verdict（未降級時等同 `red_team_verdict`） |

**Validator §13（V4.80.0）**：

- 有 `calculation_steps` → 硬驗算術鏈（每條 Step 1 乘積、Σ=raw_total、bonus/penalty 乘法、
  `effective_macro_mult = max(macro_multiplier, shift_macro_floor)`、macro_alignment 與正負號
  一致、`final_score` 與頂層鏡射一致、`staged = max(0.6, buy−0.4)`、polarization label 由
  lane scores 重算須相符、`final_decision` 必須落在 band 可達集合內）。任一不符 **rc=1**。
- 再有 `decision_engine_version` → 加驗規則表（C_eff ∈ {0.35, 0.60, 0.72}、cascade→penalty
  對映、`buy_threshold` 符合 tier × polarization 矩陣、`hot_zone_eval` 必填）。
- **2026-08-03 起的 entry 缺 `calculation_steps` 直接 rc=1**（V4.80.1）——否則「手算並整段
  省略該欄」就能繞過本節硬閘。此門檻目前綁 `export_date`；改綁 schema 版本需 bump
  `session_export_version` 到 V5.1（獨立一版做，見 TODO）。
- 該日期之前且無 `decision_engine_version` 的 entry → **整段跳過，rc=0**（向後相容，不溯及既往）。

**band 可達集合**（`final_decision` 允許偏離 band 的四條路徑，其餘一律 rc=1）：

| banded | 可另接受 | 依據 |
|---|---|---|
| `BUY` | `STAGED_ENTRY` | Step 1.7 BIPOLAR 強制降階 |
| `BUY` | `STAGED_ENTRY` | Phase 4.6 cap 觸發 **且** `cap_override_reason` 非空 |
| `BUY` / `STAGED_ENTRY` | `HOLD` | Auto REJECT 或 decision cap（無 override） |
| `HOLD` | `STAGED_ENTRY` | Rec 11 熱區 probe（`hot_zone_probe=true`） |

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
  "version":              "V2.19.0",
  "signal_polarization":  "ALIGNED | MIXED | OUTLIER | BIPOLAR — V2.19 4-tier",
  "polarization_detail":  {
    "label":         "...",
    "range":         "float — max−min",
    "max":           "float — highest lane score",
    "min":           "float — lowest lane score",
    "pos_strong":    "int — V2.19; count of lanes ≥ +1",
    "neg_strong":    "int — V2.19; count of lanes ≤ -1",
    "missing_lanes": "array[string] — 缺哪幾個 lane"
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
  "red_team_agreement":   "AGREE | DISAGREE — LLM red_team_verdict vs det",
  "red_team_basis":       "pure_forward | pure_mean_reversion | contaminated | unclassified — V2.19 anti-spoofing",
  "news_pt_leakage":        "bool | null — V3.45.4；News reasoning 出現 PT level vs price 措辭（null=舊 entry 無 haystack）",
  "news_pt_leakage_detail": "{flag, hits[], scanned} — V3.45.4 keyword 命中明細（warning 級累積統計，不改 score）"
}
```

**Polarization 規則 (V2.19 4-tier)**：
- `BIPOLAR`：range ≥ 4 AND 任一 ≥ +2 AND 任一 ≤ −2 AND **≥2 lanes ≥ +1 AND ≥2 lanes ≤ −1**（真衝突）
- `OUTLIER`：range ≥ 4 AND 任一極端但少數方只 1 lane（4-vs-1 outlier，例 [+4,+3,+3,+2,-2]）
- `MIXED`：range ≥ 3 AND 至少一正一負（有分歧但無極端）
- `ALIGNED`：以上都不滿足（訊號方向一致）

**Phase 3 Step 1.7 對應 modulation**：
| label | confidence × | position cap | decision band |
|---|---|---|---|
| BIPOLAR | 0.5 (CONFIRMED+bull 例外 0.7) | 25% | BUY → STAGED_ENTRY |
| OUTLIER | 0.85 | 100% | unchanged |
| MIXED | 0.75 | 100% | unchanged |
| ALIGNED | 1.0 | 100% | unchanged |

**Red Team basis 規則 (V2.19 anti-spoofing)**：
- `pure_forward`: 只有 fw 關鍵字 (competitor / capacity / inventory / substitution) — 唯一可保 STRONG_COUNTER 殺傷力
- `pure_mean_reversion`: 只有 mr 關鍵字 (歷史均值 / 週期見頂 / Peak Cycle) — CONFIRMED tier 下自動降級
- `contaminated`: fw + mr 都有 — LLM 偷渡 mr，視同 mr (一票否決)
- `unclassified`: 都沒有 — 退回原 verdict 邏輯

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
      "red_team_counter_evidence_strength": 4,
      "red_team_thesis_break_probability": 0.35,
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
        "score": 1.0,
        "confidence": 0.7,
        "weighted_fair_value": 525.50,
        "vs_current_pct": 15.5
      },
      "valuation_pack": {
        "schema": "valuation_pack.v1",
        "engine": "compute_price_framework.py",
        "current_price": 455.07,
        "anchors": {},
        "families": {},
        "families_present": ["fundamental", "relative", "external_expectations"],
        "family_coverage_weight": 1.0,
        "aggregation_mode": "complete_fixed_family_weights",
        "weighted_fair_value": 525.50,
        "vs_current_pct": 15.5,
        "verdict_band": "undervalued",
        "score": 1.0,
        "confidence": "high"
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
        "families_present":     ["fundamental", "relative", "external_expectations"],
        "valuation_pack_schema": "valuation_pack.v1",
        "methodology_note":     "canonical family aggregation; 5/8 anchors"
      },
      "thesis_id": "nvda-2026-05-06-001",
      "thesis_registered_at": "2026-05-06T15:42:00Z"
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
  "high_prob_scenario": "string — 1 句話描繪未來 5-15 天最有機率走法（含具體價位 + 觸發條件）",
  "volatility": {
    "atr_14":             "float | null — FMP technicalIndicators ATR period 14",
    "hist_vol_20d_daily": "float | null — 20D 日報酬標準差（小數 e.g. 0.028）；缺則 Phase 4.5 用 atr_14/price 反推",
    "momentum_20d_pct":   "float | null — 20 交易日報酬 %"
  }
}
```

> **V5.1**：`volatility` 為新增 sub-block，餵 Phase 4.5 Multi-Horizon Price Framework 5-Day Band。deterministic FMP read，LLM 不重判讀。缺欄不擋 validator（optional→required 過渡，同 `market_position`）。

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

> **V2.17.0 → V4.71.0**：`market_position`（TAM/CAGR/市占 sub-block）已於 V4.71.0 落日移除
> （P1-6：無渲染/決策消費者 + 無來源數字幻覺面，見 AUDIT_2026-07-16 F5）。
> 舊 entry 含此欄無害；validator 從未強制。

### `news_lane` (V2.13.0)

```json
{
  "immediate_catalyst_5d": {
    "event": "string",
    "date": "ISO YYYY-MM-DD",
    "direction_lean": "BULLISH | BEARISH | NEUTRAL",
    "expected_move_pct": "float | null"
  } | null,
  "decision_point_days": "int — 下次該重新評估的天數（預設 21，binary 事件當天）",
  "cross_asset_spillover": [
    {
      "asset": "treasury_10y | DXY | oil_WTI | gold | copper | sector_<XLX> | VIX | none",
      "direction": "BULLISH | BEARISH | NEUTRAL",
      "mechanism": "string — 1 句說明傳導路徑"
    }
  ],
  "reasoning_one_line": "string — V3.45.4 必填；News score 核心依據 1 句（pt_leakage classifier haystack）",
  "key_factors": ["string — V3.45.4 必填；2-4 條計分主因短語"],
  "pt_revision_momentum": {
    "direction": "UP | DOWN | FLAT | UNKNOWN — V3.45.4；30d consensus PT 變動方向（fetch.py 算，無絕對 level）",
    "consensus_delta_pct_1m": "float | null",
    "consensus_delta_pct_3m": "float | null",
    "analysts_last_month": "int | null"
  }
}
```

> **V3.45.4**：`reasoning_one_line` / `key_factors` / `pt_revision_momentum` 為新增欄位。舊 entry 缺欄
> → validator warning（非 fatal）。PT 注入層剝離詳見 protocol News subagent 章節。
> **V4.71.0**：`medium_term_shift_20d` 落日移除（P1-6：無消費者 + default 模板輸出佔多數）。舊 entry 含此欄無害。

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
