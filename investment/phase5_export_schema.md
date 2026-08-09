# Phase 5 Session Export Schema

> **Schema Version**: `V5.3`
> **Consumer**: `bridge.py` / Dashboard decisions cards / decision history
> **Producer**: Investment Protocol Phase 5 (PM / deterministic renderer)
> **Last updated**: 2026-08-03
>
> **V5.3 changes vs V5.2**（C1 — 統一 lane 資料契約）:
> - 新增必填 `lane_contract`：六個 lane（五個分析 lane + Red Team）各自的
>   `{provenance, llm_invoked, producer_version, input_hash, shadow_score}`
>   ＋ session 層 `{analysis_mode, llm_invoked_lanes[], llm_skipped_lanes[]}`（缺 → validator rc=1）
> - **lane 區塊形狀鎖**：`fundamentals_lane.moat_assessment` / `technical_lane.smart_money_analysis`
>   一律 object，`news_lane.immediate_catalyst_5d` 一律 object 或 null；smart money 的正文欄位
>   統一叫 `narrative`（`note` 落日）
> - `det_shadow.valuation_score_det` 降為**別名** —— 與 `lane_contract.lanes.valuation.shadow_score`
>   由同一次計算寫出，validator §15 硬性比對兩者相等
> - 既有 V5.0 / V5.1 / V5.2 entry **不需回填**：舊版號照原規則驗，永久相容
>
> **V5.2 changes vs V5.1**:
> - Phase 4 script 化（`trade_plan_builder.py`）。新增三個必填欄：`trade_plan_builder_version`、
>   `risk_audit`、`mandatory_risk_flags`（缺任一 → validator rc=1）
> - `mandatory_risk_flags` 首次持久化 —— 這是 Phase 3 Auto REJECT 與 Rec 11 probe 抑制的輸入，
>   過去從未寫進 history，`replay_decision_engine.py` 只能宣告 `[]` 當假設（declared assumption #2）
> - §14 新增：sizing 鏈 re-derivation（Tier A 算術 / Tier B 規則表，與 §13 同模式）
> - 既有 V5.0 / V5.1 entry **不需回填**：舊版號照原規則驗，永久相容
>
> **V5.1 changes vs V5.0**:
> - `calculation_steps` **+** `decision_engine_version` 從「建議」升為 **必填**（缺任一 → validator rc=1）
> - §13 算術硬閘由「`export_date ≥ 2026-08-03`」改綁 schema 版本 —— 版本切乾淨、回填不誤傷；
>   日期門檻續留當後衛，擋「cutover 後仍 stamp 舊版以繞道」的 mis-stamp
> - 既有 V5.0 entry **不需回填**：舊版號照原規則驗，永久相容
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
| `session_export_version` | `"V5.3"` | 固定字串；若 protocol 升版，本檔 header + 此欄同步改。Validator 接受 `V4.8` / `V5.0` / `V5.1` / `V5.2` / `V5.3`（舊版號只驗當年規則），新 export 一律戳 `V5.3` |
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
| `export_provenance` | object | **V4.117.0；由 `append_session_export.py` 自己蓋，PM 不得手填**。見下 |

### `export_provenance` (V4.117.0 — history.json 的唯一寫入者證明)

`history.json` 只由 `append_session_export.py` 追加。這個 block 是它蓋的，`export_date >= 2026-08-09` 的 entry 缺它 → validator rc=1。

| Field | Type | Note |
|---|---|---|
| `schema` | `"export_provenance.v1"` | 固定字串 |
| `writer` | string | `append_session_export.py (V<repo VERSION>)` |
| `appended_at` | ISO8601 UTC | 追加當下的時間 |
| `entry_digest` | `"sha256:<hex>"` | 本 entry **決策內容**的摘要 |

`entry_digest` 涵蓋整筆 entry，但排除 append 之後由既定工具寫入的欄位 —— 否則核可路徑會自己打自己的章：

| 排除欄位 | 由誰寫 |
|---|---|
| `export_provenance`（entry 層） | 本 script |
| `trades[].det_shadow` / `trades[].lane_contract` | `apply_det_shadow.py --inplace` |
| `trades[].thesis_id` / `trades[].thesis_registered_at` | `register_thesis.py` |
| `trades[]` 底下任何 `_` 開頭的鍵 | post-processor 暫存（如 `_as_of_date_inherited`）|

**其餘全部是決策內容，append 當下凍結。** 要改 `final_score`、`calculation_steps`、lane 分數這類欄位，唯一合法途徑是**重跑產生它的 engine，然後重新 append**；直接 `json.dump` 回 history.json 會讓 digest 對不上（rc=1），手寫的新 entry 則根本沒有 stamp（rc=1）。

> 為什麼是內容摘要而不是一個記號：記號誰打字誰就有。2026-08-09 的實際事故是一次 run 在乾淨 append 之後把 `final_score` 和整塊重打的 `calculation_steps` 就地寫進決策紀錄，另一次在閘變紅時用臨時 `json.dump` 把 entry `pop()` 掉 —— 兩者 validator 都綠，因為手寫的 entry 和 script 寫的 entry 是同一份 JSON。

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
| `entry_aggressive` | `[min, max]`（number；V5.2 前的 entry 為字串，兩者皆合法）or `null` | HOLD 通常 null；若 MD 報告有觀察區間可填 | V5.2 起由 `trade_plan_builder.py` 產出 number |
| `entry_conservative` | `[min, max]`（同上）or `null` | HOLD 若 MD 有再評觸發價位應填 | |
| `take_profit` | number or `null` | HOLD null | |
| `stop_loss` | number or `null` | HOLD null | |
| `risk_reward_ratio` | float or `null` | HOLD null；BUY/STAGED_ENTRY **必填且 ≥ 2.0** | |
| `position_size_pct` | float 0-1 | HOLD 填 0.0（**唯一例外**：`decision_cap_active=true` 把 BUY 壓成 HOLD 時保留 ≤ 0.003 的試水倉，見下） | Phase 4.6 cap 在 Phase 4 定倉之後才跑，只縮不放；validator §14 依 `approval` / `decision_cap_active` / `hot_zone_probe_capped` 三者判定倉位可否低於 `sizing_chain` 鏈尾 |
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
| `valuation_pack` | object（見下） | **新 engine output 必填**；舊 history 相容 | Phase 1.5 唯一估值計算權威；validator 強制所有 projection 相等 |
| `fair_value_summary` | object（見下） | **V5.0+ 必填** | `valuation_pack` 相容 projection（= MHP 長期層、受 decision_lock 保護）|
| `multi_horizon_price_framework` | object（見下） | **V5.0+ optional（過渡中）**；缺/不全 → validator 印 warning（非 fatal，rc 維持 0）| Phase 4.5 三時間框架（5d band / 60d target / long-term ref / convergence）。**不**進 11-field decision_lock（derived/advisory）|
| `fair_value_range` | object（見下） | **V3.45.1+ optional**；缺 → validator warning（非 fatal，rc 0）| Phase 4.5.0b anchor 分布區間（P25/P50/P75 + range_verdict + dispersion + oe shadow）。**不**進 decision_lock；`fair_value_summary` 不變 |
| `valuation_explained_range` | object（見下） | **V4.76.0+ optional** | structural-shift DCF 為 primary FV；DCF sensitivity + without/with-peer + 其他 eligible anchor 的解釋帶。range-only peer 不進 primary FV |
| `implied_expectations` | object（掛 `valuation_lane` 或 trade 頂層；見下） | **V3.45.1+ optional**；缺 → warning（rc 0）| reverse DCF 隱含預期。**V3.45.3 起由 `compute_price_framework.py` engine 計算**（V4.88.0 起在 Phase 1.5；非 LLM 手算）。**不**進加權 / lane score / decision_lock |
| `valuation_archetype_shadow` | object（見下） | **V3.46.0+ optional**；缺 → warning（rc 0）| Phase 1.5 engine archetype 分類 + 9-anchor shadow blend。**shadow-only** — live `fair_value_summary` 不動、不進 decision_lock。≥20 session 翻轉率報告後才議切換（#3b）|
| `valuation_reviewer_gate` | object（見下） | **V4.116.3 起：`export_date >= 2026-08-09` 的 session 缺此 block → rc=1**；之前的 entry 仍靜默（172 筆歷史 entry 都沒有它）。protocol §PHASE 2 一直要求把它寫進 export，但 validator 過去只在它出現時才驗，等於選配——2026-08-09 兩次實測顯示：codex 跑了、agy 沒跑，兩者都 rc=0 | L4b 條件式 Valuation Specialist 的 **shadow 紀錄**：`{schema, ticker, would_invoke, mandatory_fired, triggers_fired[], shadow_only}`。`shadow_only=false` → **rc=1**（翻預設需使用者拍板，session 不得自行讓 gate 生效）。`triggers_fired` 只認 5 個具名 trigger；`would_invoke` 必須等於 `bool(triggers_fired)` |
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
| `speculative_grade` | bool | optional **(V4.108.0+)** | Phase 4.6 speculative governor。true = 估值成立但只靠 pre-profit 錨／賣方預估，**verdict 放行、籌碼受限**（size ≤ 1%、conf ≤ 0.70）。由 `decision_engine.apply_decision_cap` 從 `fair_value_summary` 的 `pre_profit_anchor_live` / `sell_side_only` 兩個布林算出，非 PM 判斷。Validator §10b 強制，且 §14 為它開了「倉位可低於 sizing_chain 鏈尾」的合法出路 |
| `speculative_reasons` | array of `"pre_profit_fwd_earnings_anchor" \| "sell_side_only_evidence"` | required if `speculative_grade=true` | 觸發 governor 的具體條件；Validator §10b 強制非空且限於此 enum |
| `hot_zone_probe` | bool | optional **(V5.0.x+, Rec 11)** | 熱區保守性鬆綁觸發旗標。true 表示正分模糊區 `[0,+staged)` × `industry_top_30pct` × `RISK_ON/BULL` 把 default HOLD 降為小倉 probe。觸發時強制 `final_decision=STAGED_ENTRY`、`position_size_pct ≤ tier 上限`、且 `decision_cap_active != true`。Validator (`validate_session_export.py` § 11) 強制。預設 false |
| `hot_zone_probe_tier` | `"t1_15bps" \| "t2_30bps"` or `null` | required if `hot_zone_probe=true` **(V4.70.0+, P0-1)** | 分數分層 probe size：`final_score ≥ 0.4` → t2（≤30bps）/ `< 0.4` → t1（≤15bps）。依據 AUDIT_2026-07-16 replay（上半帶 mean +17.6% up 10/15 vs 下半帶 −1.2%）。Validator §11 按 tier 強制 size 上限 |
| `hot_zone_eval` | `"fired" \| "suppressed_by_risk_flag" \| "suppressed_by_cap" \| "not_qualifying"` | **required (V5.0.x+, TODO-015)** | Rec 11 評估結果，不論是否 probe 一律寫出，使驗收不再盲飛。判定樹見 `investment_protocol_v5_0.md` Rec 11 段。Validator §11 強制：`hot_zone_probe=true ⟺ hot_zone_eval="fired"`。extractor 對缺欄的歷史報告反推 `hot_zone_eval_derived`（含 `qualifying_unexplained` 告警值） |
| `trade_plan_builder_version` | `string` | **V5.2+ 必填** | Phase 4 engine 版號（如 `"1.0.0"`）。有此欄 = 走 script 化 Phase 4，validator §14 加驗規則表。缺欄且戳 V5.2 → rc=1 |
| `risk_audit` | object（見下） | **V5.2+ 必填** | `trade_plan_builder.py` 的 `risk_audit` 整塊 verbatim。內含 `sizing_chain`，validator §14 據此重算九段乘法鏈 |
| `mandatory_risk_flags` | array[string] | **V5.2+ 必填**（正常情況空陣列） | Phase 3 Auto REJECT（含 `systemic` 字樣者一票否決）與 Rec 11 probe 抑制的輸入。**V5.2 前從未持久化** —— 補上後 `replay_decision_engine.py` 才不必宣告 `[]` 當假設 |
| `final_stop_loss_pct` | float or `null` | **V5.2+ 必填**（HOLD 可 null） | Step 4 `base_stop_pct + ftd_timeline_stop_adjustment`，下限 −10%。取自 `risk_audit.final_stop_loss_pct` |

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
      "weight_effective": "float",
      "calibration": "object|null — anchor 自帶的校準原料；目前只有 fwd_earnings_discounted 有，其餘為 null"
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
  "confidence": "high|medium|low",
  "evidence_independence": {
    "eligible_anchors": ["string"],
    "sell_side_anchors": ["string — eligible 之中源自賣方預估者"],
    "sell_side_only": "bool — 每一根 eligible anchor 都是賣方預估",
    "note": "string"
  }
}
```

Reverse DCF 不在 anchors 中，只是 market-implied diagnostic。缺 `provenance/as_of` 的 anchor
不得 eligible；relative anchor 缺 `peer_count` 或少於 3 個 business-similar peers時不得 eligible；
analyst PT 超過 180 天不得 eligible；少於兩個獨立 family 時 `|score| < 2`。

**`evidence_independence`（V4.108.0）**：family topology 給獨立 family 各一票，但它看不出
「兩個不同 family 其實由同一批賣方分析師餵養」——`analyst_pt_consensus` 與
`fwd_earnings_discounted` 同時 eligible 就是這個情形。`sell_side_only=true` 不改估值數字、
不改 verdict，它的唯一後果是強制 Phase 4.6 的 speculative governor（見下）。
`forecaster_blend` 不算賣方錨：它的 cagr / trend 兩法用歷史實績。

**`fwd_earnings_discounted`（V4.108.0，第 9 根｜條件錨）**：專為**還在虧損、又沒有可比同業**
的題材成長股而設——這種標的八根 live anchor 全部無定義（DCF 為負、owner earnings / P/E
無定義、倍數族拿不到 ≥3 家 business-similar peers），`anchors_available=0` 會讓
`insufficient_anchors` 直接封死決策。公式（全決定論，peer-free）：

```
target  = horizon ≤ 3.5y 內**最遠**一個 epsAvg > 0 且 numAnalystsEps ≥ 3 的年度
pe      = clamp(成長率% × 1.0, 15, 35)      # EPS CAGR 優先，轉盈前退回營收 CAGR
beta    = profile beta（≤0 或缺 → FWD_BETA_FALLBACK 2.73，見下）
r       = clamp(10Y + beta × 0.045, 0.10, 0.30)
value   = target_eps × pe ÷ (1 + r)^horizon_years
```

> **無效 beta 不得解讀成「市場級風險」**：這根錨服務的母體定義上就比市場危險，讓
> `beta=0`／缺值落到折現率下限（10%）等於把資料缺陷換成最寬鬆的折現。實例：SPCX
> beta=0（IPO 2026-06-12，歷史不足兩個月）原本吃到 10% 下限、是整組樣本裡最寬鬆的一檔，
> 修正後改用母體中位數 2.73 → r=16.9%，anchor 由 $115.18 降到 $99.50。`beta_source`
> 記錄用的是 `profile` 還是 `population_median_fallback`，fallback 率在
> `shadow_report.py` 的校準區段可查——偏高就該重新量測 `FWD_BETA_FALLBACK`。

Live 資格（`evaluate_fwd_anchor_scope`）：**所有 cashflow_intrinsic 錨**
（dcf_unlevered / dcf_levered / dcf_self_built / owner_earnings_mult）皆非 live **且**
TTM EPS 非正時才開；否則值照算但只進 archetype shadow 池。raw weight 0.15 刻意留在
八根的 1.0 預算之外——它只在 cashflow 族（合計 0.50）結構性缺席時上場，永遠擠不掉既有錨。
`anchor_meta` 需帶 `analyst_count` 與 `horizon_years`，缺 → fail closed（與 `peer_count` 同紀律）。

> **已知限制**：目標年度的選擇對數值影響很大（AAOI 2026-08-07：FY27 覆蓋 3 家 → $153；
> 若 FY27 掉到 2 家則退回 FY26 → $33）。這是方法本身的性質，由「≥3 分析師 + 3.5 年
> horizon + 必須有第 2 根錨才解 cap + governor 壓倉位」四道限制共同約束，不由平滑掩蓋。

**`calibration` 與 `FWD_PE_CLAMP` 的校準（V4.108.0）**：pre-profit 標的的成長率幾乎必然
爆表，`justified_pe` 因此**恆取上限 35**——上限對不對，就是這根錨最關鍵的單一假設。
`calibration` 把重算所需的原料留在 pack（`target_eps` / `discount_rate` / `horizon_years`
/ `justified_pe_raw` / `pe_clamp_binding`），讓校準不必回頭重跑引擎：

```
市場隱含 justified PE = current_price × (1 + discount_rate)^horizon_years ÷ target_eps
```

即「同一個目標年度 EPS、同一個折現率下，市場實際付幾倍」。讀出端是
`shadow_report.py` 的 FWD_PE_CLAMP 區段（掃 `invest_logs/*_pf_quant.json`，同標的取最新
一次），判準 = **live cohort** 的 P33–P66 是否包住現行上限。

> 為什麼不能用 `#2 dispersion` 那套「切自己輸出分布的 percentile」：`agreement_grade`
> 的門檻是**描述性**的，切在它所描述的分布上；PE clamp 是**因果**參數，直接決定輸出——
> 拿它自己的輸出校準它會循環。市場隱含 PE 外生於這根錨，才是合法的校準標的。
> 同理**不可自動跟隨中位數**：泡沫期中位數上移、上限跟著上移，錨就永遠不會說貴。

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
    "forecaster_blend":     "float|null",
    "fwd_earnings_discounted": "float|null — V4.108.0+（條件錨，見 valuation_pack 說明）；舊 entry 無此 key，validator 不強制"
  },
  "anchors_effective":     "object — 僅 eligible anchors；排除者為 null，MHP 等 downstream 只讀此欄",
  "weights_used":         "object — valuation_pack effective weights projection",
  "weighted_fair_value":  "float",
  "current_price":        "float",
  "vs_current_pct":       "float",
  "verdict_band":         "extreme_undervalued | undervalued | fairly_valued | overvalued | extreme_overvalued",
  "confidence":           "high | medium | low（獨立 family coverage + dispersion cap）",
  "anchors_available":    "int 0-9（V4.108.0 前為 0-8；V4.69.0 前為 0-6；V4.70.0+ 為修剪後 count）",
  "families_present":     "array[string]",
  "excluded_anchors":     "object anchor→reason",
  "valuation_pack_schema": "valuation_pack.v1",
  "sell_side_only":       "bool|null — V4.108.0+；valuation_pack.evidence_independence 的投影，Phase 4.6 governor 直接讀",
  "pre_profit_anchor_live": "bool|null — V4.108.0+；fwd_earnings_discounted 是否 eligible",
  "methodology_note":     "string",
  "outlier_diagnostics":  "array[{anchor,value,reason}] optional；只警示，不剔除 live anchor"
}
```

### `multi_horizon_price_framework` (Phase 4.5)

三時間框架 deterministic 輸出（0 LLM 重評）。長期層 `long_term_ref` 直接引用 `fair_value_summary`，不複製不重算。
**不**進 11-field decision_lock。缺料降級：`sigma_daily` 缺 → short_term confidence=low（atr 反推）；`mid_target` 全錨缺 → null。
**V3.45.3 起整包由 `compute_price_framework.py` 計算**（V4.88.0 起 MHP 在 Phase 2.4、其餘在 Phase 1.5）（含 `fair_value_summary` blend / `fair_value_range` / 本 block / `implied_expectations`），
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
  "red_team_kill_seed":   "string — falsifiable kill condition 起點",
  "market_implied_revenue": {
    "applicable":               "bool",
    "reason":                   "string | null — 例：ev_to_sales_ttm_unavailable",
    "ev_to_sales_ttm":          "float | null",
    "terminal_ev_to_sales":     "4.0 — 保守（規範性）情境",
    "terminal_ev_to_sales_sector_typical": "8.0 — 科技中樞情境",
    "horizon_years":            5.0,
    "required_revenue_multiple": "float | null — ev_to_sales_ttm ÷ terminal",
    "implied_revenue_cagr":     "float | null",
    "required_revenue_multiple_sector": "float | null — 同上但用科技中樞；下限 1.0（不要求反向擴張）",
    "implied_revenue_cagr_sector": "float | null",
    "analyst_revenue_cagr":     "float | null — 覆蓋 ≥3 家的最遠年度回推",
    "analyst_horizon_years":    "float | null",
    "verdict": "market_above_sell_side | market_below_sell_side | aligned_with_sell_side | null",
    "note":                     "string",
    "red_team_kill_seed":       "string"
  }
}
```

**`market_implied_revenue`（V4.108.0）**：reverse DCF 對 FCF ≤ 0 的公司無定義（過去直接
棄權，`sanity_note` 只留一句「不適用」），但「市場在定價什麼」對虧損題材股恰恰是最該問的
問題。改問營收：**EV 原地不動**的前提下，營收要成長幾倍、年化幾 % 才能把今天的 EV/S 消化到
目標倍數。答案的意思是「光是撐住今天的價格，營收就得長這麼快」，**不是**任何形式的
目標價；與 `implied_5y_fcf_cagr` 同級——不進加權、不進 verdict，只餵 Red Team 與 governor。

**兩個 terminal 是刻意的**，因為這個假設的槓桿極大（AAOI：4x → 需 32% CAGR；8x → 15%），
藏在單一常數裡等於把結論藏起來：

| 常數 | 值 | 性質 |
|---|---|---|
| `TERMINAL_EV_SALES` | 4.0 | **規範性**假設：「倍數正常化到無題材光環的硬體業」。**不是**實測中樞——2026-08-07 量測成熟獲利公司 median EV/S 為半導體 13.9 / 通訊設備 8.3 / 軟體 8.0 / 工業包裝 2.8，4.0 大約在工業水準，對科技股刻意保守，當壓力測試用 |
| `TERMINAL_EV_SALES_SECTOR_TYPICAL` | 8.0 | 同次量測的科技中樞。標為「情境」而非基準是因為它有**循環性**：拿今天正在 re-rating 的可比公司當「成熟終值」（LITE 28.1x、PE 143）會讓門檻自動變低 |

sector 情境的 `required_revenue_multiple_sector` 下限為 1.0——EV/S 已在科技中樞之下時
不要求任何營收擴張，而不是輸出一個「倍數反向擴張」的負成長。

### `valuation_archetype_shadow` (V3.46.0 — Phase 1.5 engine，shadow-only)

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
  "anchors_used_n": "int 0-12（V4.108.0 起池含 fwd_earnings_discounted，僅 hypergrowth 權重 > 0；V4.69.0 起含 dcf_self_built / comps_implied；之前為 0-9）",
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
| `decision_engine_version` | `string` | engine 版號（如 `"1.0.0"`）。**有此欄 = 走 V4.70.0+ 規則**，validator 加驗規則表。**V5.1 起必填** |
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
- **`session_export_version = "V5.1"` 的 entry 缺 `calculation_steps` 或 `decision_engine_version`
  直接 rc=1**（V4.81.0）——否則「手算並整段省略該欄」就能繞過本節硬閘。門檻綁 schema 版本而非
  日期：回填一筆舊分析時只要照舊戳 `V5.0` 就依當年規則驗，不會被今天的門檻誤傷。
- **後衛**：`export_date ≥ 2026-08-03` 但戳 `V5.0`/`V4.8` 又缺 `calculation_steps` → 一樣 rc=1
  （V4.80.1 的日期閘留著，專擋「刻意戳舊版號繞過版本閘」的 mis-stamp）。另有反向 guard：
  戳 `V5.0` 卻帶 `decision_engine_version` → rc=1，提示改戳 `V5.1`。
- 上述皆不適用且無 `decision_engine_version` 的 entry → **整段跳過，rc=0**（向後相容，不溯及既往）。

**Validator §5l（V4.117.0）—— 抄寫必須抄到同一次的輸出**：

§13 驗的是這塊**自己內部**算得通，那證明不了它屬於**這一次**的 engine run。2026-08-09 有一份 export 的 `calculation_steps` 來自 valuation = −1.5 的那次執行，而 entry 自己的 valuation lane 寫著 −3.0；後續的修法迴圈還把數字往兩個相反方向各改了一次才終於重跑 engine。**重打的 block 和正確的 block 形狀完全一樣。**

`decision_engine.py` 因此把 Phase 3 輸出落地到 `investment/invest_logs/decision_engine/<TICKER>_decision_engine.json`（`--phase 4.6` 不寫，那是另一種 payload）。Validator 讀回來逐欄比對：

- artifact 存在、ticker 相符、24h 內 → `calculation_steps` 每一個 engine 有的鍵都必須相等（巢狀遞迴；浮點容差 1e-6）。任一不符 **rc=1**，訊息直接列出 `欄位 export值 vs engine值`。
- export 多出來的鍵不管（那是別節的 schema 業務）。
- artifact 缺席 / 過期 / ticker 不符 → **靜默**（同 technical rubric 閘：沒有證據就不下判斷，缺 artifact 是 `script_not_run` 家族的事）。

同 V4.116.3 的 technical payload：**關鍵那一步是把 stdout 落地**。engine 的數字原本只活在 stdout，最後躺在執行者的 transcript 裡，validator 構不到，於是「抄對了沒」永遠只能靠自陳。

**band 可達集合**（`final_decision` 允許偏離 band 的四條路徑，其餘一律 rc=1）：

| banded | 可另接受 | 依據 |
|---|---|---|
| `BUY` | `STAGED_ENTRY` | Step 1.7 BIPOLAR 強制降階 |
| `BUY` | `STAGED_ENTRY` | Phase 4.6 cap 觸發 **且** `cap_override_reason` 非空 |
| `BUY` / `STAGED_ENTRY` | `HOLD` | Auto REJECT 或 decision cap（無 override） |
| `HOLD` | `STAGED_ENTRY` | Rec 11 熱區 probe（`hot_zone_probe=true`） |

### `risk_audit` + `trade_plan_builder_version` (V5.2 — Phase 4 engine)

Phase 4 全部算術由 `investment/scripts/trade_plan_builder.py` 產出，PM **verbatim 抄寫**整塊。
欄位語意見 `investment_protocol_v5_0.md` §PHASE 4；此處只記 validator 契約：

| 欄 | 型別 | 說明 |
|---|---|---|
| `trade_plan_builder_version` | `string` | engine 版號（如 `"1.0.0"`）。**有此欄 = 走 V4.82.0+ 規則**，validator 加驗規則表。**V5.2 起必填** |
| `risk_audit.sizing_chain` | object | 九段乘法鏈的逐段值 + `steps[]` 文字軌跡。validator §14 逐段重算 |
| `risk_audit.sizing_chain.base` | `float` | Step 2 起點（`vol_adjusted_limit_pct / 100` 或 `0.05`） |
| `risk_audit.position_size_method` | `"VOL_ADJUSTED" \| "RULE_BASED"` | 與 `vol_adjusted_limit_pct` 是否為 null 必須一致 |
| `risk_audit.tail_risk.fragility_label` | `"ROBUST" \| "MODERATE" \| "FRAGILE"` | 與 `sizing_chain` 用的 fragility 乘數必須對得上（1.0 / 0.75 / 0.5） |
| `risk_audit.ftd_timeline_gate` | object | `applied=false` 時 multiplier 必須是 1.0；`applied=true` 時 stage × sector_class 必須映到表上的乘數 |
| `risk_audit.sector_concentration_f1` | object | `applied=true ⟺ multiplier=0.5`；`active_same_sector_confirmed=null` 時只能 `applied=false` |
| `risk_audit.approval` | `"APPROVED" \| "REJECTED"` | `REJECTED` → `position_size_pct` 必須為 0 且 `final_decision` 不得為 BUY/STAGED_ENTRY |
| `risk_audit.sized_for_decision` | `string` | **V5.2 必填**。Phase 4 **實際據以計算 sizing 鏈的**決策。Phase 4.6 cap 在 Phase 4 之後才跑，會把 BUY 改寫成 HOLD / STAGED_ENTRY，此時 `final_decision` 已無法解釋鏈（尤其 STAGED_ENTRY 的折半該不該套）。§14 一律用本欄重算，缺欄才退回 `final_decision` |

**Validator §14（V4.82.0）**：

- 有 `risk_audit.sizing_chain` → 硬驗九段鏈（`tail_adj = base × fragility`、macro cap 的
  `min()` 語意、binary / burry / ftd / f1 / shift / polar 各段乘法、STAGED 折半、
  `position_size_pct` 與鏈尾一致）。任一不符 **rc=1**。
- 再有 `trade_plan_builder_version` → 加驗規則表（fragility 乘數表、FTD stage × sector_class
  乘數表與停損 pp、F1 二值、`approval=REJECTED ⇒ size 0`、`hot_zone_probe` 的 tier 上限）。
- **`session_export_version = "V5.2"` 的 entry 缺 `risk_audit` / `trade_plan_builder_version` /
  `mandatory_risk_flags` 直接 rc=1** —— 否則「手算並整段省略該欄」就能繞過本節硬閘。
  門檻綁 schema 版本而非日期（同 §13）。
- 反向 guard：戳 `V5.1`/`V5.0` 卻帶 `trade_plan_builder_version` → rc=1，提示改戳 `V5.2`。
- 上述皆不適用的 entry → **整段跳過，rc=0**（向後相容，不溯及既往）。

**`sizing_chain` 為何連 `steps[]` 一起存**：macro cap 是 `min()` 不是乘法，鏈上只留數字的話
無法從尾部反推它有沒有觸發。`replay_trade_plan.py` 的 inverse solve 因此把「命中 macro cap」
的 trade 整批排除（`macro_cap_min_not_invertible`）而不是硬解——存 `steps[]` 讓未來的
entry 不必再走這條退路。

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

> **V5.3 起 `valuation_score_det` 是別名**：權威值在
> `lane_contract.lanes.valuation.shadow_score`。兩處由 `apply_to_trade()` 的**同一次**計算寫出，
> validator §15 硬性比對相等 —— 不等只可能是有人事後手改其中一處。既有消費端
> （`shadow_report.py` / `bridge.py` / Dashboard / `test_valuation_pack_consistency.py`）繼續讀舊欄，
> 不需要改；等契約全面上線後再落日。

### `lane_contract` (V5.3 — C1 統一 lane 資料契約，post-processor 寫入)

由 `apply_det_shadow.py` 與 `det_shadow` **同一步**寫出（Phase 5 Step 1.5），**LLM 不寫**。

```json
{
  "contract_version":  "C1/1.0",
  "analysis_mode":     "FULL_IC | LEAN | REFRESH",
  "llm_invoked_lanes": ["array[string] — 本次有 LLM 參與的 lane"],
  "llm_skipped_lanes": ["array[string] — 本次沒有 LLM 參與的 lane"],
  "lanes": {
    "fundamentals | sentiment | news | technical | valuation | red_team": {
      "provenance":       "llm | deterministic | hybrid | absent",
      "llm_invoked":      "bool — 由 provenance 推導：llm/hybrid ⇒ true",
      "producer_version": "string | null — det/hybrid 必填；LLM lane 填 'protocol:<repo VERSION>'",
      "input_hash":       "string | null — 目前恆 null，L9 factpack content_hash 落地後由 producer 填",
      "shadow_score":     "float | null — det producer 的分數（今天只有 valuation 有）"
    }
  }
}
```

**六個 lane 全列，缺席的填 `provenance: "absent"`**（不是省略）。省略與「跑了但沒記」在事後
無法區分，Phase 6 按 provenance 分層時會把兩者混為一談。Red Team 放進同一張表而不是另立
一組欄位 —— L8（RT decision-invariant skip）只要改 `lanes.red_team.provenance`，不必再發明
一套平行欄位，那正是 C1 要消滅的東西。

**保留外來聲明，重算自己的推導**（V4.90.4 定界）—— 逐欄位分兩域：

- **保留域（外來 producer 的聲明）**：`provenance` ∈ {`deterministic`, `hybrid`}（L5 / L6 /
  L8 在自己的 phase 寫入，post-processor 不得覆寫回 `llm` 預設）；`producer_version` /
  `input_hash` / 非 valuation 的 `shadow_score`（L5 shadow 期 det 值寫在這，provenance 仍是 `llm`）。
- **推導域（post-processor 自己的輸出，每次重算贏）**：`provenance` 的 `llm` / `absent`
  兩個值（預設行為與「從訊號推出缺席」是推導不是聲明——套保留規則的實錘後果：PM 漏填
  `lane_scores` → 推成 `absent` → 補分數重跑 → 上一輪的 `absent` 被自己保留住，§15 報錯
  而「重跑」永遠修不好）；`llm_invoked`（恆為 provenance 的投影）；
  `lanes.valuation.shadow_score`（與 `det_shadow.valuation_score_det` 同一次計算，**無條件**
  同步含變回 null 的情形，V4.90.1）。

這條界線劃錯一格就是一個「重跑修不好、只能手改契約」的死結，而手改正是 §15 要禁止的事
（V4.90.1 / V4.90.4 各實錘一次，`test_lane_contract.py` 兩組回歸鎖死）。

| provenance | 意思 | 今天誰會是這個值 |
|---|---|---|
| `llm` | LLM subagent 產出 | 六個 lane 的預設（現行協定行為） |
| `deterministic` | script 產出，本回合沒有 LLM | L5（Sentiment）/ L6（Technical）/ L8（RT skip）落地後 |
| `hybrid` | det producer + 條件式 LLM reviewer 都跑了 | L4b gate 翻預設後的 Valuation |
| `absent` | 本回合沒有產出 | lane 無分數，或 `red_team_execution_failed=true` |

**Validator §15（V4.90.0）**：

- `session_export_version = "V5.3"` 的 entry 缺 `lane_contract` 直接 **rc=1**；反向 guard：
  戳 `V5.2` 以下卻帶 `lane_contract` → rc=1（門檻綁 schema 版本，同 §13 / §14）。
- 值域：`provenance` / `analysis_mode` 必須落在上表；`llm_invoked` 必須與 `provenance` 一致
  （`llm`/`hybrid` ⇒ true）；`provenance` 為 `deterministic`/`hybrid` 時 `producer_version` 必填
  —— 不具名的 det lane 無法歸屬到任何一版公式，Phase 6 就分不了層。
- `llm_invoked_lanes` + `llm_skipped_lanes` 必須**剛好分割**六個 lane，且與 per-lane
  `llm_invoked` 完全一致（session 層清單是 per-lane 的投影，不是獨立事實）。
- `lanes.valuation.shadow_score` 必須等於 `det_shadow.valuation_score_det`（吸收閘）。
- **provenance 錨在外部事實上，雙向鎖**（V4.90.2）：五個分析 lane 用與 producer 同一條
  推導（`compute_polarization().missing_lanes`）——有分數 ⇒ 不得 `absent`、無分數 ⇒ 必須
  `absent`；RT 用 `red_team_execution_failed` ——沒失敗 ⇒ 不得 `absent`、失敗 ⇒ 必須
  `absent`。契約內部自洽（清單對齊、llm_invoked 一致）擋不住改得夠齊的手改，一致性
  必須錨在偽造者改不動的東西上（lane_scores 受 §13 算術鏈保護、RT 旗標 schema 必填）。
- lane block 一律 object：`"sentiment": null` 不是缺席（缺席 = `provenance: "absent"`），
  是 rc=1。
- **`lane_scores` 升為硬性要求，且四個 key 必須都在**（值可為 `null`；protocol 從 V2.10.0
  就寫必填，validator 過去沒擋）：契約用「這個 lane 有沒有分數」推導 `provenance: "absent"`，
  省略（整塊或部分）會把實際跑過的 lane 標成「本回合沒產出」—— 少寫一個欄位就偽造了
  provenance，且 producer 與 validator 會**一致同意**那個偽造，兩邊一致在這裡不是保護。
  與契約「六個 lane 全列、缺席明寫 `absent`」同一條紀律，往上游推一層。
- 版號不在 `LANE_CONTRACT_VERSIONS` 的 entry → **整段跳過，rc=0**（181 筆舊 entry 不回填）。

**為什麼舊 entry 不回填**：V4.6 的四 lane fanout 與今天的六 lane 契約不是同一回事。補一塊
「看起來很完整」的 provenance 上去，等於在稽核軌跡放假證據 —— 而 Phase 6 按 provenance 分層
校準時會直接吃到它。

**值域與形狀的單一事實來源是 `apply_det_shadow.py`**（`LANE_NAMES` / `PROVENANCE_VALUES` /
`ANALYSIS_MODES` / `LANE_FIELDS`）；validator **import** 不複製。

### `sentiment_det` (V4.91.0 — L5 Sentiment det producer，shadow-only)

由 `skills/market-sentiment-analyzer/scripts/sentiment_score.py` 產出，PM **整塊抄寫**。
Step 1.5 的 post-processor 把 `score` 映進 `lane_contract.lanes.sentiment.shadow_score`。

```json
{
  "producer_version": "string — 具名公式版號（shadow 樣本要可歸屬到哪一版）",
  "shadow_only":      "true — 恆真；false 由 validator 擋（翻預設需使用者拍板）",
  "score":            "float | null — 0.5×stock_specific + 0.5×(composite/10−5)，clamp [-3,+3]",
  "market_layer":     "float | null — composite/10 − 5",
  "market_composite": "float | null — sentiment.py composite_score (0-100)",
  "stock_specific":   "float — 規則表命中加總後 clamp [-3,+3]",
  "stock_detail":     "{raw_sum, clamped, rules_fired[{rule, points, detail}]}",
  "missing_inputs":   "array[string] — 拿不到的輸入（≠ 拿到了但中性）",
  "degraded_reason":  "string | null — score=null 時必填",
  "input_hash":       "string — 同輸入必得同分數，稽核用"
}
```

**這塊是 shadow，不是決策數字**：`lane_scores.sentiment` 仍由 LLM lane 產出並進 Phase 3。
Validator §5j 為 warning 級（缺 block 靜默、舊 entry 相容），但 **`shadow_only=false` 是 error** ——
那代表有 session 自行讓 det 取代了 LLM lane，而翻預設需使用者拍板 + weight 凍結窗。

> **契約側只映 `score`**。`producer_version` 在契約那格記的是**lane 的產出者**，shadow 期
> 是 LLM（`protocol:<VERSION>`）；把 det script 的版號填進去等於向 Phase 6 宣稱這筆已是
> script 產的，分層會歸錯池。det 公式的版號與 `input_hash` 完整留在本 block。

### lane 區塊形狀鎖 (V5.3)

真實 entry 之間，同一個欄位出現過兩種形狀，導致每個消費端各自寫相容碼（renderer 現在有三處）。
V5.3 起把形狀定死，**只對 V5.3+ 生效**：

| 欄位 | V5.3 起的形狀 | 過去出現過的另一種 |
|---|---|---|
| `fundamentals_lane.moat_assessment` | object `{level, type, evidence_one_line}` | 單行字串 |
| `technical_lane.smart_money_analysis` | object `{label, narrative}` | 單行字串／正文欄位叫 `note` |
| `news_lane.immediate_catalyst_5d` | object 或 `null` | 字串 |

> 舊 entry 照當年規則驗，所以 `render_investment_report.py` 的三處相容碼**必須留著** ——
> 它讀得到 181 筆舊 entry。等舊 entry 淡出 render 路徑才談刪除。

---

## FULL EXAMPLE（V5.3 — 以 BUY 決策為範本）

> Phase 3 數字（`final_score` / `avg_confidence` / `calculation_steps` / `hot_zone_eval`）為
> `decision_engine.py` 實跑輸出；Phase 4 數字（`trade_plan` 各價位 / `risk_audit` / `sizing_chain`）
> 為 `trade_plan_builder.py` 實跑輸出。整份範例可直接過 validator。抄 shape，**不要**抄數字。
>
> `det_shadow` 與 `lane_contract` **不在**範例裡：兩者都是 Step 1.5 post-processor 寫的，
> PM 手寫等於偽造 provenance。`test_session_export_schema.py` 驗證時會實跑 producer 補上這兩塊。
>
> `export_provenance` 同理不在範例裡（V4.117.0）：它由 `append_session_export.py` 蓋，內含
> 本 entry 的內容摘要。**照著抄一份 digest 進來只會讓 validator 紅**——摘要要對得上的是你自己
> 那筆 entry，不是這份範例。

```json
{
  "session_export_version": "V5.3",
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
      "final_score": 2.1888,
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
      "avg_confidence": 0.75,
      "lane_scores": {"fundamentals": 4, "sentiment": 3, "news": 3, "technical": 4},
      "decision_engine_version": "1.0.0",
      "calculation_steps": {
        "fund": "0.25 × 4 × 0.72 = 0.7200",
        "sent": "0.15 × 3 × 0.72 = 0.3240",
        "news": "0.20 × 3 × 0.72 = 0.4320",
        "tech": "0.25 × 4 × 0.72 = 0.7200",
        "val": "0.15 × 1 × 0.72 = 0.1080",
        "raw_total": 2.304,
        "structural_shift_modulation": {
          "tier": "NONE",
          "applied_adjustments": ["no modulation — standard rules apply"],
          "shift_macro_floor": 0.0,
          "position_size_cap_pct": 100,
          "red_team_mean_reversion_blocked": false
        },
        "polarization_modulation": {
          "label": "ALIGNED",
          "lane_range": 3.0,
          "pos_strong": 5,
          "neg_strong": 0,
          "outlier_lane_id": null,
          "applied_adjustments": ["no modulation"],
          "confidence_multiplier": 1.0,
          "position_cap_after": 100
        },
        "red_team_basis": "unclassified",
        "red_team_auto_downgrade": false,
        "cascade_rule_applied": "rule_5_default_strong_counter",
        "dynamic_threshold": {
          "buy_threshold": 1.2,
          "staged_threshold": 0.8,
          "rationale": "default 1.2 (tier=NONE, polarization=ALIGNED)"
        },
        "red_team_verdict": "STRONG_COUNTER",
        "red_team_effective_verdict": "STRONG_COUNTER",
        "red_team_counter_evidence_strength": null,
        "red_team_thesis_break_probability": null,
        "bonus_applied": false,
        "penalty_applied": true,
        "penalty_value": 0.95,
        "raw_after_bonus": 2.1888,
        "macro_multiplier": 0.9,
        "macro_alignment": "CONTRARIAN",
        "effective_macro_mult": 0.9,
        "final_score": 2.1888
      },
      "hot_zone_probe": false,
      "hot_zone_eval": "not_qualifying",
      "decision_cap_active": false,
      "burry_score": 37.1,
      "burry_override_active": false,
      "burry_override_recheck_date": null,
      "trade_plan_builder_version": "1.0.0",
      "mandatory_risk_flags": [],
      "entry_aggressive": [425.0, 462.0],
      "entry_conservative": [405.0, 425.0],
      "take_profit": 540.0,
      "stop_loss": 400.97,
      "risk_reward_ratio": 2.27,
      "position_size_pct": 0.0203,
      "final_stop_loss_pct": -9.59,
      "staged_split": null,
      "position_size_method": "VOL_ADJUSTED",
      "risk_audit": {
        "risk_level": "HIGH",
        "sized_for_decision": "BUY",
        "vol_adjusted_limit_pct": 4.06,
        "position_size_method": "VOL_ADJUSTED",
        "tail_risk": {
          "fragility_label": "FRAGILE",
          "tail_risk_score": 60.0,
          "fragility_adjustment": "× 0.5",
          "degraded": false
        },
        "binary_classification": "unknown",
        "binary_event_within_48h": false,
        "burry_override_active": false,
        "burry_override_multiplier": 1.0,
        "ftd_timeline_gate": {
          "applied": false, "days_since_ftd": null, "stage": "n/a",
          "sector_class": "cyclical", "multiplier": 1.0,
          "stop_loss_adjustment_pp": 0, "rejection_triggered": false
        },
        "sector_concentration_f1": {
          "applied": false, "multiplier": 1.0, "sector": "Technology",
          "active_same_sector_confirmed": 1, "source": "explicit_count",
          "note": "同 sector active CONFIRMED 1 < 3 → 不減倉"
        },
        "sizing_chain": {
          "base": 0.0406,
          "tail_adj": 0.0203,
          "macro_cap": 0.0203,
          "binary_adj": 0.0203,
          "binary_multiplier": 1.0,
          "burry_override_adj": 0.0203,
          "burry_override_multiplier": 1.0,
          "ftd_adj": 0.0203,
          "f1_adj": 0.0203,
          "f1_multiplier": 1.0,
          "shift_adj": 0.0203,
          "polar_adj": 0.0203,
          "final_position_size": 0.0203,
          "steps": [
            "base 0.040600 × fragility 0.5 = 0.020300",
            "macro_backdrop -1.0 ≥ -3.0 → macro cap 不觸發 = 0.020300",
            "binary unknown (event<48h=False) → × 1.0 = 0.020300",
            "burry_override False → × 1.0 = 0.020300",
            "ftd_timeline × 1.0 = 0.020300",
            "V20-F1 sector concentration × 1.0 = 0.020300",
            "structural_shift cap 100.0% → × 1.0 = 0.020300",
            "polarization cap 100.0% → × 1.0 = 0.020300",
            "decision BUY → 不折半 = 0.020300"
          ]
        },
        "position_size_pct": 0.0203,
        "final_stop_loss_pct": -9.59,
        "stop_loss_derivation": {
          "base_stop_pct": -9.59, "ftd_stop_adjustment_pp": 0,
          "floored_at_limit": false, "structural_stop_price": 400.95,
          "pct_based_stop_price": 400.97, "selected": "pct_based",
          "note": "base -9.59% + FTD 0pp = -9.59%"
        },
        "staged_entry_split": null,
        "hot_zone_probe_capped": false,
        "approval": "APPROVED",
        "rejection_reason": null
      },
      "ftd_timeline_gate": {
        "applied": false, "days_since_ftd": null, "stage": "n/a",
        "sector_class": "cyclical", "multiplier": 1.0,
        "stop_loss_adjustment_pp": 0, "rejection_triggered": false
      },
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

當 Protocol 升版（例如 V5.0 → V5.1）：
1. 本檔 header `Schema Version` + 正文 `session_export_version` + FULL EXAMPLE 的版本戳同步改
2. 如有新欄位 → 加到 REQUIRED table + FULL EXAMPLE
3. 如有欄位改語意 → 加進 DO NOT 區塊說明舊用法禁用
4. 更新 `validate_session_export.py`：`ACCEPTED_VERSIONS` 加新版號、`CURRENT_VERSION` 指到新版號，
   **舊版號一律留在 ACCEPTED_VERSIONS**（既有 entry 永不回填）。新的硬性必填欄用版本集合開閘
   （見 `CALC_STEPS_REQUIRED_VERSIONS`），不要用 `ver == "V5.x"` 單值比較——單值比較在下次升版時
   會靜默失效（V4.81.0 修掉的 `ver != "V5.0"` 就是這樣寫壞的）
5. 下游同步：`replay_decision_engine.py`（`FIVE_LANE_VERSIONS`）與 `validate_markdown_export.py`
   （`V5_VERSIONS`）都從 validator import 版本集合，新增版號時**只改 validator**即可
6. 若新版號同時是 Dashboard badge token → 檢查 `Dashboard/page-decisions.js`
   `detectProtocolVersion()` / `VERSION_COLOR` / `DECISION_TIPS` 是否撞名
7. Protocol 的 Phase 5 章節**不必動**（只引用本檔路徑）
8. 新的 engine 產出區塊（`calculation_steps` / `risk_audit` …）除了版本閘，一定要配一條
   **反向 mis-stamp guard**：戳舊版號卻帶新 engine 版號欄 → rc=1。少了它，「戳 V5.1 就好」
   就是繞過新硬閘的最短路徑（§13 的 V5.0 guard、§14 的 V5.0/V5.1 guard 都是這條）

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

> **Phase 4.5 補充**：`volatility` 為新增 sub-block，餵 Multi-Horizon Price Framework 5-Day Band。deterministic FMP read，LLM 不重判讀。缺欄不擋 validator（optional→required 過渡，同 `market_position`）。

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
    "analysts_last_month": "int | null",
    "unavailable_reason": "string — direction=UNKNOWN 時必填（V4.117.0）"
  }
}
```

> **V3.45.4**：`reasoning_one_line` / `key_factors` / `pt_revision_momentum` 為新增欄位。舊 entry 缺欄
> → validator warning（非 fatal）。PT 注入層剝離詳見 protocol News subagent 章節。
> **V4.71.0**：`medium_term_shift_20d` 落日移除（P1-6：無消費者 + default 模板輸出佔多數）。舊 entry 含此欄無害。

#### V4.117.0 — `pt_revision_momentum` 對 `export_date >= 2026-08-09` 的 entry 變必填

protocol §PHASE 2 用這欄計分（`direction=UP` 且 `delta_1m > +3%` → +0.5~+1；`DOWN` 且 `< -3%` → 反向同幅），但 validator 原本只在它**出現時**驗型別，於是 `null` 是免費的。2026-08-09 的實測：一份 export 在 News lane 的 risk flag 散文裡寫著 `-2.94% 1m`，結構化欄位卻是 `null` —— 分數剛好沒受影響（−2.94% 在 ±3% 帶內），所以沒人發現，**稽核鏈斷了而數字沒動**。

| 情形 | 要求 |
|---|---|
| 有資料 | `direction` ∈ `UP`/`DOWN`/`FLAT`；`UP`/`DOWN` 必須帶 **數值** `consensus_delta_pct_1m`（否則 ±3% 規則無從套用，方向宣稱不可稽核）|
| 無資料 | `{"direction": "UNKNOWN", "unavailable_reason": "<為什麼>"}` —— 沒有理由的 `UNKNOWN` 與漏填無法區分 |
| 整個 `news_lane` 是 null | 只有在 `lane_scores.news` 也是 null 時才放行。**lane 有評分就代表它跑過**；否則 = 分數留著、依據消失 |

**要求是「解析這個欄位」，不是「資料一定要存在」。**

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
