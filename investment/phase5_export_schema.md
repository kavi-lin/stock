# Phase 5 Session Export Schema

> **Schema Version**: `V4.8`
> **Consumer**: `bridge.py` / Dashboard decisions cards / decision history
> **Producer**: Investment Protocol Phase 5 (PM / Sonnet formatter)
> **Last updated**: 2026-04-18

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
| `session_export_version` | `"V4.8"` | 固定字串；若 protocol 升版，本檔 header + 此欄同步改 |
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
| `fragility_label` | `"ROBUST" \| "MODERATE" \| "FRAGILE"` | **必填** | HOLD 也要（tail-risk-analyzer 輸出）|
| `binary_classification` | `"positive" \| "unknown" \| "negative" \| "none"` | **必填** | |
| `time_horizon` | `"short" \| "mid" \| "long"` | **必填** | HOLD 也要（反映再評窗口長度）|
| `analysis_price` | float | **必填（V4.8+）** | 分析當下股價快照（從 Phase 2 Technical analyst 或 us-stock-analysis skill 抓取）。Dashboard 用來比較 vs 即時價的漂移 |
| `macro_context` | string (1-3 句) **繁體中文** | 填 | |
| `watch_conditions` | object（key: snake_case 英文識別名 → value: **繁體中文**描述）| **必填，最少 3 條** | HOLD：填再評 / 退場觸發；BUY：填進場後監控 |
| `key_risks` | array[string] **繁體中文短描述**（非 snake_case）| 填（3-8 條）| 例：「RSI 98 拋物線過熱衰竭風險」|
| `devils_advocate_filed` | bool | 填 | |
| `trade_metadata` | `{trade_type, event_tag}` | **必填** | trade_type ∈ {event, trend, mean_reversion} |

---

## FULL EXAMPLE（V4.8 — 以 BUY 決策為範本）

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
      }
    }
  ],
  "active_weights_end_of_session": {
    "Fundamentals": 0.30,
    "Sentiment": 0.20,
    "News": 0.20,
    "Technical": 0.30
  },
  "bias_notes": "V4.8 PARALLEL_SUBAGENT 4/4 isolated。…（1-3 句，反映決策理由 + 自省）",
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
