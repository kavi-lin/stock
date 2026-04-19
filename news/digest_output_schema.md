# News Digest Output Schema

> **Schema Version**: `V2.1`
> **Consumer**: `bridge.py` / Dashboard news page / decisions binary_risks sidebar
> **Producer**: News Protocol V2 Phase 4（DIGEST / FLASH / REVIEW 三模式共用）
> **File location**: `news/news_logs/YYYY-MM-DD_digest.json`
> **Last updated**: 2026-04-18

---

## 目的

本檔案是 `news/news_logs/YYYY-MM-DD_digest.json` 每次 Phase 4 新寫入的 shape **唯一事實來源**。News Protocol V2 不再內嵌 JSON 範本 — 任何 schema 變動改這裡就好。

**V2.1 新增**（vs V2.0）：
- `fanout_mode` — Stage 2 per-agent batch subagent 執行狀態
- `degraded_agents` — fallback 時標記哪些 agent 降級 inline
- `subagent_isolated` per-verdict sentinel — 驗證 deep verdicts 來自獨立 subagent

Claude 在 Phase 4 末尾**必須**：
1. 以本檔的 `FULL EXAMPLE` 為 shape 範本填入本次 DIGEST / FLASH / REVIEW 結果
2. 執行 `python3 news/scripts/validate_digest_output.py` — rc ≠ 0 時修正再重跑
3. 禁止輸出本檔 `## DO NOT` 區塊列出的任何 legacy shape

---

## REQUIRED fields

### Top-level
| Field | Type | Note |
|---|---|---|
| `timestamp` | `"YYYY-MM-DD HH:MM"` | Phase 4 寫入時間 |
| `mode` | `"DIGEST" \| "FLASH" \| "REVIEW"` | 觸發模式 |
| `stage1_count` | integer | DIGEST 限用；FLASH / REVIEW = 0 |
| `stage2_count` | integer | DIGEST 限用；FLASH = 1；REVIEW = 1 |
| `fanout_mode` | `"PER_AGENT_BATCH" \| "PARTIAL_FALLBACK" \| "FULL_FALLBACK" \| "INLINE"` | V2.1 — Stage 2 subagent 執行模式；FLASH 小量時可 `INLINE` |
| `degraded_agents` | array[string] | V2.1 — fallback 時列出降級的 agent（正常空陣列）|
| `verdicts` | array | 本次所有分析結果（shallow + deep 混合；至少 1 則）|
| `session_macro_delta` | float | -1.0 ~ +1.0；所有 deep verdicts 加總後對 phase0 macro 的淨衝擊 |

### verdicts[i] — 每則新聞（shallow 與 deep 共用，但部分欄位只在 deep 填）

| Field | Type | Shallow | Deep | Note |
|---|---|---|---|---|
| `news_id` | string | 必填 | 必填 | `n001`, `n002`, … |
| `depth` | `"shallow" \| "deep"` | 必填 | 必填 | 決定本則是否經過 Stage 2 |
| `review_status` | `"reviewed" \| "pending"` | 必填 | 必填 | DIGEST Stage 2 / REVIEW = reviewed；FLASH = pending；Stage 1 shallow = reviewed（不會再 promote） |
| `headline` | string | 必填 | 必填 | 原文（通常英文）|
| `headline_zh` | string | 必填 | 必填 | 繁中翻譯 |
| `source_label` | `"Reuters \| Bloomberg \| Yahoo Finance \| MarketWatch \| CNBC \| Investing.com \| …"` | 必填 | 必填 | |
| `news_type` | `"earnings \| monetary_policy \| macro_data \| geopolitical \| corporate \| sector_news \| sentiment"` | 必填 | 必填 | |
| `bull_case` | string | ≤30 字 snap | 完整段落 150–250 字 | |
| `bear_case` | string | ≤30 字 snap | 完整段落 150–250 字 | |
| `sector_view` | string | ≤30 字 snap | 完整段落 | Shallow 時是一句話；Deep 時含 supply chain 2 階效應 |
| `macro_view` | string | ≤30 字 snap | 完整段落 | Shallow 時是一句話；Deep 時含 Fed path / yield / FX / historical analogue |
| `verdict` | `"BULLISH \| BEARISH \| BINARY \| NEUTRAL"` | 可 null | 必填 | Shallow 時 Arbiter 不介入故 null；Deep 必填 |
| `net_impact_score` | float | 必填（shallow_score）| 必填 | Shallow 為四家 snap 加權；Deep 為 Arbiter 正式裁決 |
| `arbiter_reasoning` | string | 空字串 或 null | 必填 150 字+ | Shallow 無 Arbiter；Deep 必填 |
| `debate_note` | string | null | 必填 | 四方最大分歧點（Deep only）|
| `binary_risk` | bool | 必填 | 必填 | |
| `binary_event_date` | `"YYYY-MM-DD"` or `null` | null OK | 若 `binary_risk=true` 必填 | |
| `within_48h` | bool | 必填 | 必填 | |
| `cache_updated` | bool | `false`（shallow 不 patch）| DIGEST deep / REVIEW = true；FLASH = false | |
| `affected_sectors` | array of `{sector, direction}` | 可空 | 必填 ≥ 1 筆 | `direction ∈ {bullish, bearish, binary, neutral}` |
| `tickers_mentioned` | array[string] | 可空 | 必填（若完全無個股 → 顯式 `[]`）| Ticker symbols |
| `subagent_isolated` | bool | null OK | V2.1：Deep 來自 subagent → true；fallback inline → false | |

---

## FULL EXAMPLE（DIGEST，含 shallow + deep 混合）

```json
{
  "timestamp": "2026-04-18 09:15",
  "mode": "DIGEST",
  "stage1_count": 42,
  "stage2_count": 4,
  "fanout_mode": "PER_AGENT_BATCH",
  "degraded_agents": [],
  "verdicts": [
    {
      "news_id": "n003",
      "depth": "deep",
      "review_status": "reviewed",
      "headline": "NVDA raises Q3 guidance by 12%",
      "headline_zh": "輝達上修第三季指引 12%",
      "source_label": "Bloomberg",
      "news_type": "earnings",
      "bull_case": "AI capex 週期續航明確…（150-250 字完整論述）",
      "bear_case": "高基期 + 中國出口管制…（150-250 字）",
      "sector_view": "半導體 +strong、半導體設備 +moderate、公用事業 +weak（AI 電力需求連動）；供應鏈 2 階效應：CoWoS 產能緊俏拉動 TSM / ASML 稼動率…",
      "macro_view": "對 Fed 路徑中性，非通膨驅動；利差 / 匯率無顯著衝擊；歷史類比 2024 Q2 NVDA 指引上調後 SOX 三週 +11%…",
      "verdict": "BULLISH",
      "net_impact_score": 3.2,
      "arbiter_reasoning": "news_type=earnings 權重 Sector 40%；四方分數 Bull +4 / Bear -2 / Sector +4 / Macro 0，加權 = 3.2 BULLISH。採 Sector 主論點，Bear 高基期警告保留作再評條件。",
      "debate_note": "Sector Bull（基期論）vs Bear 最大分歧：FY27 能否維持 +30% 成長",
      "binary_risk": false,
      "binary_event_date": null,
      "within_48h": false,
      "cache_updated": true,
      "affected_sectors": [
        { "sector": "Semi", "direction": "bullish" },
        { "sector": "Semi-equip", "direction": "bullish" },
        { "sector": "Utilities", "direction": "bullish" }
      ],
      "tickers_mentioned": ["NVDA", "TSM", "ASML", "AVGO", "VRT"],
      "subagent_isolated": true
    },
    {
      "news_id": "n001",
      "depth": "shallow",
      "review_status": "reviewed",
      "headline": "AAPL minor analyst upgrade",
      "headline_zh": "蘋果獲分析師小幅調升",
      "source_label": "Yahoo Finance",
      "news_type": "corporate",
      "bull_case": "小幅 PT 上調，對 AAPL 中性偏多",
      "bear_case": "評級調整幅度有限，消息強度低",
      "sector_view": "Tech 大型股觸動不大",
      "macro_view": "對 Fed 路徑無影響",
      "verdict": null,
      "net_impact_score": 1.2,
      "arbiter_reasoning": null,
      "debate_note": null,
      "binary_risk": false,
      "binary_event_date": null,
      "within_48h": false,
      "cache_updated": false,
      "affected_sectors": [],
      "tickers_mentioned": ["AAPL"],
      "subagent_isolated": null
    }
  ],
  "session_macro_delta": 0.3
}
```

---

## MODE-SPECIFIC rules

### DIGEST
- `stage1_count ≥ stage2_count`（triage 必然 ≥ 晉級）
- verdicts 必須包含全部 stage1 項目（shallow + deep 混合），不得只留 deep
- 所有 deep verdict `review_status = reviewed` + `cache_updated = true`
- fanout_mode 應為 `PER_AGENT_BATCH`（正常）或 `PARTIAL_FALLBACK`（某 agent 降級）/ `FULL_FALLBACK`（極端情況）

### FLASH
- `stage1_count = 0, stage2_count = 1`
- verdicts 只有 1 筆、`depth = deep`、`review_status = pending`、`cache_updated = false`
- fanout_mode 可為 `INLINE`（單則 + 速度考量，subagent overhead 不划算）

### REVIEW
- `stage1_count = 0, stage2_count = 1`
- verdicts 只有 1 筆、`depth = deep`、`review_status = reviewed`（升級自 pending）、`cache_updated = true`
- fanout_mode 應為 `PER_AGENT_BATCH`（1 則 × 4 agent subagent 擴展，isolation 很划算）

---

## DO NOT（禁止 shape 清單）

### ❌ 只留 deep，丟棄 shallow verdicts（DIGEST mode）
```json
{ "mode": "DIGEST", "verdicts": [ ...只有 5 則 deep 的項目... ] }
```
**原因**：Shallow 是「你已經花 token 跑過 Stage 1 triage 的成果」，不寫入 = 浪費。Dashboard 的 Shallow Digest 區塊需要這些資料。

### ❌ Deep verdict 缺 `arbiter_reasoning` / `debate_note`
Deep 必填 Arbiter 正式裁決理由與四方分歧點。缺 → validator 失敗。

### ❌ Deep verdict `tickers_mentioned` 完全省略（非空陣列）
必填欄位。無相關個股應寫 `[]` 並在 `arbiter_reasoning` 說明原因（例：純宏觀事件）。

### ❌ FLASH verdict 帶 `review_status: "reviewed"` + `cache_updated: true`
FLASH 必須 `pending` + `cache_updated=false`（要等 REVIEW mode 升級）。

### ❌ `fanout_mode: "PER_AGENT_BATCH"` 但所有 deep verdict `subagent_isolated: false`
自相矛盾；正確：全 true（真的用 subagent）或 fanout_mode 改為 `INLINE`。

### ❌ Legacy V1 shape（pre-V2）
```json
{ "timestamp": "...", "items": [{...}], "summary": "..." }
```
`items` 改為 `verdicts`；`summary` 改為 top-level `session_macro_delta` + Markdown 報告。

---

## 版本更新規則

當 Protocol 升版（例如 V2.1 → V2.2）：
1. 本檔 header `Schema Version` + 正文 `fanout_mode` enum 同步改
2. 新欄位 → 加到 REQUIRED table + FULL EXAMPLE
3. 更新 `validate_digest_output.py` 的版本檢查與必填清單
4. Protocol 的 Phase 4 章節**不必動**（只引用本檔路徑）
