---
name: ic-memo-writer
description: 從 investment_protocol 既有 cache (history.json + earnings-analyst cache + company_context) 組「高可讀 IC Memo」12 章節 MD 報告；V4.69.0 起另支援「首次覆蓋 Initiating Coverage」長格式（同一 fact pack 基礎 + valuation-modeler 自建 DCF/comps 全文渲染）。Deterministic-only renderer，不重評分，decision_lock hash 11 欄位防偷改結論。
triggers:
  - "ic-memo [TICKER]"
  - "分析 [TICKER] --memo"  # protocol hook
  - "首次覆蓋 [TICKER]"      # V4.69.0 → build_fact_pack --initiation + compose_initiation
  - "分析 [TICKER] --initiation"
version: V1.1.0
---

# ic-memo-writer — Readable IC Memo from Protocol Cache

## 目的

`分析 [TICKER]` 已產出**委員會決策報告** (`reports/<YYYYMMDD>_<TICKER>.md`)，形態偏交易決策紀錄。本 skill 額外產出**高可讀 IC Memo** (`reports/<YYYYMMDD>_<TICKER>_ic_memo.md`)：12 章節敘事，重用 protocol 既有 cache + earnings-analyst segments，**不重評分、不重抓資料**。

## 與既有 skill 的邊界

| Skill | 重點 | 觸發 | 是否評分 |
|---|---|---|---|
| `investment_protocol_v5_0` | 委員會 5 lane + Burry + Red Team + Phase 4.5 fair_value | `分析 [TICKER]` | ✅ 評分 + 決策 |
| `earnings-analyst` | 8Q 三表 + segments + composite | `財報 [TICKER]` | ✅ 評分 |
| **`ic-memo-writer` (本)** | **12 章節敘事 MD，純 deterministic 渲染** | `ic-memo [TICKER]` | ❌ 不評分 |
| **`ic-memo-writer --initiation` (V4.69.0)** | **首次覆蓋長格式：12 章節 + §8a 8-anchor 表 + §8b 自建 DCF（假設 provenance/FCFF/sensitivity）+ §8c comps 全表** | `首次覆蓋 [TICKER]` | ❌ 不評分 |

**首次覆蓋流程與前置**（規格見 `template_initiation.md`）：需 history.json 有 protocol entry
＋ `skills/valuation-modeler/cache/<T>_{dcf,comps}_payload.json`（缺 → build_fact_pack rc=4
並印出確切補跑指令）。流程：`build_fact_pack.py <T> --initiation` → `compose_initiation.py <T>`
→ `validate_ic_memo.py reports/<DATE>_<T>_initiation.md --initiation`。輸出
`reports/YYYYMMDD_<T>_initiation.md`。

## 12 章節結構

1. 一頁摘要
2. 公司與商業模式
3. 收入結構與成長驅動 (segments product/geographic 5FY)
4. 客戶 / 供應商 / 競爭格局 (peers + Focus Area descriptor，第一版為 stub)
5. 最新財務與申報重點 (8Q P&L + ttm_metrics + 業績驚喜)
6. 資產負債表與現金流品質
7. 盈利能力與 2-3 年模型 (annual_growth + structural_shift)
8. 估值：DCF + multiples + analyst PT + peer (來自 Phase 4.5 fair_value_summary)
9. 催化劑與風險，3/6/12 個月排序
10. Bull / Bear / Base case (scenario_odds + Red Team)
11. 委員會結論：動作 / 理想買點 / 重新評估條件 (verbatim from protocol)
12. 附錄：lane / source provenance roster / degraded sections / validator result

## 觸發語

```bash
# 1. 純組 memo (要求 ticker 已有 protocol history entry)
ic-memo PL

# 2. Protocol hook (在 Phase 5 後執行，non-fatal)
分析 PL --memo
```

CLI:
```bash
python3 skills/ic-memo-writer/scripts/build_fact_pack.py <TICKER>
python3 skills/ic-memo-writer/scripts/compose.py <TICKER>
python3 skills/ic-memo-writer/scripts/validate_ic_memo.py reports/<DATE>_<TICKER>_ic_memo.md
```

## 資料源 (read-only)

| 章節 | 來源 |
|---|---|
| §1 §2 | `_shared/company_context.get_profile()` (FMP profile，24h cache) |
| §3 §5 §6 §7 | `skills/earnings-analyst/cache/<T>_<earnings_date>.json` |
| §4 peers | `_shared/company_context.get_peers()` (FMP，24h cache) |
| §4 Focus Area | **stub**: `skills/ic-memo-writer/cache/peer_descriptor/<T>.json` (第一版 empty，TTL 14d) |
| §8 §9 §10 §11 | `investment/invest_logs/history.json` latest `trades_this_session[]` for ticker |

**禁止** 重算 DCF / 重評分 / 新抓 FMP statements (除非 cache 不存在)。

## fact_pack 中間層

```
skills/ic-memo-writer/cache/<T>_<DATE>_fact_pack.json
```

`build_fact_pack.py` 將上述資料源聚合成單一 JSON。`compose.py` 唯一資料源即 fact_pack；template 改版可重 render 而不重抓。

Schema:
```json
{
  "schema_version": "1.0",
  "ticker": "PL",
  "as_of": "2026-05-27",
  "composed_at": "2026-05-27T10:30:00Z",
  "sources": {
    "profile": {"path": "live:fmp/profile/PL", "fetched_at": "..."},
    "earnings_cache": {"path": "skills/earnings-analyst/cache/PL_<date>.json", "stale_days": 23},
    "protocol_history": {"path": "investment/invest_logs/history.json#trades[42]", "session_date": "2026-05-26"},
    "peers": {"path": "_shared/cache/peers/PL.json", "stale_hours": 2},
    "peer_descriptor": {"path": "skills/ic-memo-writer/cache/peer_descriptor/PL.json", "llm_call": null, "status": "stub_no_llm"}
  },
  "facts": { "sec_1": {...}, "sec_2": {...}, ... },
  "degraded_sections": ["sec_3", "sec_7"],
  "_protocol_decision_lock": {
    "fields": ["final_decision", "final_action", "position_size_pct", "analysis_price",
               "fair_value_summary", "scenario_odds", "watch_conditions", "key_risks",
               "red_team_counter_thesis", "red_team_kill_conditions", "lane_scores"],
    "payload": {...},
    "hash": "sha256:..."
  }
}
```

## decision_lock 11 欄位

```python
LOCK_FIELDS = [
    "final_decision", "final_action", "position_size_pct", "analysis_price",
    "fair_value_summary", "scenario_odds", "watch_conditions", "key_risks",
    "red_team_counter_thesis", "red_team_kill_conditions", "lane_scores",
]
```

任一欄位篡改 → validator rc=1 fatal。 浮點 (fair_value, position_size_pct) `round(x, 4)` 後序列化避免 IEEE 飄移。

## Validator rc 分級

| rc | 含意 | 範例 | hook 處置 |
|---|---|---|---|
| 0 | pass | 全綠 | memo published |
| 1 | fatal | decision_lock hash mismatch / §11 verbatim 失敗 / FV mismatch / 缺 §11 / 重評分禁字命中 / 11 欄位篡改 | **不可稱完成**，memo file 寫入但加 `<!-- INVALID -->` header |
| 2 | degraded-usable | earnings cache 缺 / 章節 stub / peer_descriptor stub / anchors_available<3 | memo published + footer 標 `degraded_sections: [...]` |

## Provenance 規範

每章節最末必加 HTML 註釋：
```html
<!-- src: protocol.history.phase4_5 -->
<!-- src: earnings_analyst.cache (stale 23d) -->
<!-- src: llm_synth.peer_descriptor (stub) -->
```

MD footer 必有「Provenance Roster」表，列出 12 章節各自來源 + as_of + 註記。

## Deterministic-only 宣告

第一版 (V1.0.0)：
- compose.py 全程 **0 LLM call**
- 任何敘事段落均由 fact_pack 欄位拼接 (含表格化 `peer comp`、章節間 transition 句固定模板)
- `--llm-polish` flag 預留 (raises `NotImplementedError`)

未來 V1.1+ 加 `--llm-polish` 後，**polished MD 仍必須通過 fact boundary validator** (禁止引入 fact_pack 外的數字)。

## 缺資料嚴重度

| 缺失 | 章節影響 | Memo 仍可出？ |
|---|---|---|
| profile fail | §1 §2 全毀 | ❌ fatal abort |
| protocol.history 無此 ticker | §8 §9 §10 §11 全毀 | ❌ abort，提示先跑 `分析 [TICKER]` |
| earnings cache 缺 | §3 §5 §6 §7 stub | ✅ degraded |
| peers 缺 | §4 列空表 | ✅ |
| peer_descriptor 缺 | §4 Focus Area 空白 (第一版預設) | ✅ |

## 與 investment_protocol 邊界

- 失敗 **non-fatal**：protocol Phase 5 完成後執行，失敗不影響決策報告
- 不修改 `history.json`
- 不更新 thesis registry (V2.14.0 已負責)
- 不重跑任何 phase

## 後續路徑

- Phase A.5: `fetch_peer_descriptor.py` swap stub → 真 Haiku 4.5 一次性 batch call (~110 行)
- Phase B: Dashboard `stock-detail.html` render ic_memo + live quote bar chart
- Phase C: Nexus graph 串接 §4 peer click-through
