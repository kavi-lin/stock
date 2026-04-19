# Breaking News Intelligence Protocol (V2.1)

<!-- [scope] equity-market news analysis. Stage 1 triage + Stage 2 deep-debate
     patterns are [framework]. RSS feeds and mega-cap focus are [domain:us-equity]. -->

> 背景說明、版本演進、團隊敘述、token 預算請見 `news/README.md`。
> Digest shape 定義：`news/digest_output_schema.md`（唯一事實來源）。

---

## SESSION STARTUP

```
MODE : FLASH | DIGEST | REVIEW
  FLASH  = 單則即時新聞，直接深度辯論（< 5 分鐘）
  DIGEST = RSS 寬掃描 → 漏斗篩選 → 深度辯論（全面更新 cache）
  REVIEW = 對一則 pending FLASH 重新進行正式委員會審核
```

**觸發**：
- 貼標題/連結 → FLASH
- 「更新新聞 cache」「新聞分析 DIGEST」→ DIGEST
- 「新聞分析 審核 [headline]」→ REVIEW

---

## GLOBAL RULES

1. **Debate Required**：每則進入 Stage 2 的新聞必須產出 Bull / Bear / Sector / Macro 四視角，禁止單面結論。
2. **Token Discipline**：
   - DIGEST **禁止** WebSearch 為主要來源（僅 Stage 1 fallback，單次 query ≤ 2 條）
   - Stage 1 只讀 RSS cache，不做任何 web 請求
   - Stage 2 WebFetch 硬上限 **5 則**
3. **Theme Cache**（FRESH = mtime < 3h）：先讀 `skills/theme-detector/cache/theme_detector_*.json`；FRESH 直接載入（`theme_source: THEME_CACHE`），STALE 才跑 skill。
4. **Cache Patch 時機**：**只有 Stage 2 深度辯論結論**能 patch cache。Stage 1 shallow 仍完整寫入 `news_logs/*_digest.json`（`depth: shallow`），不浪費已產出的觀點。
5. **FLASH**：單則直接進 Stage 2（跳 Stage 1），標記 `review_status: pending`（**不 patch cache**），等 REVIEW 升級後才 patch。
6. **REVIEW**：讀 `review_status: pending` → 4 agent 擴展辯論（snap 30 字 → 完整 200+ 字）→ Arbiter 正式裁決（可覆寫 verdict / score）→ `pending → reviewed` → 執行 cache patch。
7. **Output**：邏輯 JSON + 結論 Markdown Impact Card。
8. **review_status 語意**：
   - `reviewed` → DIGEST Stage 2 或 REVIEW 通過 → 允許 patch → Dashboard「已審核」
   - `pending` → FLASH → **不 patch** → Dashboard「待審核」

---

## ARBITER 加權規則

**基礎**：Bull 25 / Bear 25 / Sector 25 / Macro 25（%）

**依 `news_type` 覆蓋**：

| news_type | Bull | Bear | Sector | Macro |
|---|---|---|---|---|
| `monetary_policy` | 15 | 15 | 20 | **50** |
| `macro_data` | 15 | 15 | 20 | **50** |
| `geopolitical` | 15 | 30 | 15 | **40** |
| `earnings` | 25 | 25 | **40** | 10 |
| `corporate` | 25 | 25 | **40** | 10 |
| `sector_news` | 20 | 20 | **50** | 10 |
| `sentiment` | 30 | 30 | 15 | 25 |
| `default` | 25 | 25 | 25 | 25 |

`net_impact_score = Σ(agent_score × weight)`，四捨五入到小數點後 1 位。

---

## DIGEST MODE — 兩階段漏斗

### STAGE 1 — RSS SHALLOW TRIAGE

**資料來源**：
1. 檢查 `news/news_logs/YYYY-MM-DD_raw.json` 是否存在
2. 不存在或 `mtime > 1h` → 執行 `python3 news/fetch_news_rss.py --hours 24 --output news/news_logs/`
3. 讀取 raw.json 取得 30–50 則標題 + 摘要

**Stage 1 輸出**：

```json
{
  "phase": "stage1_triage",
  "timestamp": "YYYY-MM-DD HH:MM",
  "raw_count": 42,
  "shallow_verdicts": [
    {
      "news_id": "n001",
      "headline": "string",
      "headline_zh": "string",
      "source": "Reuters | Bloomberg | Yahoo Finance | MarketWatch | CNBC",
      "source_credibility": "HIGH | MEDIUM | LOW",
      "raw_summary": "string — RSS 摘要（不改寫）",
      "news_type": "earnings | monetary_policy | macro_data | geopolitical | corporate | sector_news | sentiment",
      "bull_case": "string ≤ 30 字",
      "bear_case": "string ≤ 30 字",
      "sector_view": "string ≤ 30 字",
      "macro_view": "string ≤ 30 字",
      "shallow_score": "-5 to +5（加權後）",
      "binary_flag": "true | false",
      "advance_to_stage2": "true | false",
      "advance_reason": "string or null"
    }
  ],
  "advanced_count": "integer ≤ 5"
}
```

### 晉級門檻（任一成立即晉級，硬上限 5 則）

- `|shallow_score| ≥ 3`
- `binary_flag = true` 且事件在 48h 內
- `source_credibility = HIGH` 且 `|shallow_score| ≥ 2`
- 使用者在 Triage 表手動勾選

超過 5 則 → 依 `|shallow_score|` 取前 5。

### Triage 表（給使用者）

```
╔══════════════════════════════════════════════════════════════╗
║  NEWS TRIAGE  │  YYYY-MM-DD HH:MM  │  42 則 → 4 則晉級        ║
╠══════════════════════════════════════════════════════════════╣
║  ✅ DEEP   n003  [+3.8]  NVDA guidance raise          earnings║
║  ✅ DEEP   n007  [-3.2]  Fed hawkish minutes    monetary_pol. ║
║  ✅ DEEP   n012  [BINARY] Taiwan election 48h   geopolitical  ║
║  ✅ DEEP   n019  [+3.1]  Oil supply shock       geopolitical  ║
║  ──────────────────────────────────────────────────────────  ║
║  ❌ SKIP   n001  [+1.2]  AAPL minor upgrade           corp    ║
║  ❌ SKIP   n002  [-0.8]  generic bear note            senti.  ║
║  ... (34 more skipped)                                        ║
╠══════════════════════════════════════════════════════════════╣
║  💡 加選 SKIP 項目？回覆 news_id 或「繼續」                    ║
╚══════════════════════════════════════════════════════════════╝
```

**使用者互動**：
- `繼續` / `ok` / `proceed` → 直接進 Stage 2
- `加選 n001 n005` → 指定項目加入（仍受硬上限）
- `剔除 n019` → 從 Stage 2 移除
- 無回覆超時 → 直接執行 Stage 2

---

### STAGE 2 — DEEP DEBATE（per-agent batch subagent）

#### 執行流程
1. **News Collector inline**：對每則晉級新聞執行 `WebFetch url`；失敗則 1 次 WebSearch fallback。蒐集 full_text_bundle（≤ 5 則 × 全文）
2. **4 subagent 平行呼叫（同一則訊息內 4 tool_use）**：每個 agent 看到全部晉級新聞 full text + Phase 0 macro 快照 + 自己 lane 的 rubric；**看不到**其他 agent output 或其他 session bias
3. **Fan-in**：Arbiter 收 4 個 JSON（每個內含 N 個 per-item 分析）→ 逐則合併 → 正式裁決
4. 每個 subagent 輸出必含 `subagent_isolated: true` sentinel

#### Subagent Prompt 模板

```
Agent(
  description="<LANE> Stage 2 batch analyst",
  subagent_type="general-purpose",
  prompt="""
  You are the <LANE> analyst for Stage 2 deep debate.

  ISOLATION CONTRACT:
    - 你與其他 3 個 agent 以獨立 context 平行執行
    - 禁止推測其他 lane 結論
    - 禁止為了「與共識一致」調整 impact_score
    - 禁止跨題串接語氣（即使同一天 5 則都偏空，仍各自獨立評估）

  PHASE 0 MACRO CONTEXT:
  <paste phase0 macro_summary — read-only shared>

  STAGE 2 NEWS BUNDLE（N 則，N ≤ 5）：
  <paste each news item with full_text + news_id + source + news_type>

  YOUR LANE RUBRIC:
  <RUBRIC_LANE>

  OUTPUT: 單一 JSON object：
  {
    "agent": "<LANE>_Analyst",
    "subagent_isolated": true,
    "per_item": {
      "<news_id_1>": { ...本 lane 完整分析 schema... },
      ...
    }
  }
  """
)
```

#### Per-Lane Rubric

- **Bull**：`{interpretation, primary_beneficiary_sectors[], catalyst_type ∈ {demand_increase, cost_reduction, policy_tailwind, sentiment_boost, short_squeeze}, impact_score 1~5, time_horizon ∈ {immediate, short_term, mid_term}, confidence 0-1, key_assumption}`
- **Bear**：`{interpretation, primary_at_risk_sectors[], risk_type ∈ {demand_destruction, cost_increase, policy_headwind, sentiment_crash, contagion}, impact_score -5~-1, time_horizon, confidence, key_assumption}`
- **Sector**：`{primary_sectors[{sector, direction, magnitude}], supply_chain_impact, tickers_mentioned[] (≥1 或顯式空陣列 + 理由), impact_score -5~+5, confidence}`
- **Macro**：`{fed_path_delta, yield_curve_impact, fx_commodity_impact, historical_analogue, impact_score -5~+5, confidence}`

#### 辯論強制規則（Arbiter 驗證）
- Bull / Bear 不得同為 `|impact| ≤ 1`（代表沒真正辯論）→ 退回該則要求 re-analyze
- `source_credibility = LOW` → 四方 confidence 上限 0.5
- 含 binary event → Bear + Macro 必須標記 `binary_risk: true`

#### Fan-Out 失敗處理

| 情境 | `fanout_mode` | 處理 |
|---|---|---|
| 4 subagent 全部成功 + `subagent_isolated=true` | `PER_AGENT_BATCH` | 正常 |
| 1-2 agent timeout / malformed → retry 1 次仍失敗 | `PARTIAL_FALLBACK` | 失敗者 inline fallback；`degraded_agents[]` 列出；confidence 上限 0.5 |
| 3-4 agent 失敗 | `FULL_FALLBACK` | 整批 inline；BULLISH verdict 強制降級（BULLISH → NEUTRAL，BEARISH 保留） |
| 1 則（FLASH） | `INLINE` | 直接 inline 四視角辯論，subagent overhead 不划算 |

---

## PHASE 3 — ARBITER VERDICT

```json
{
  "phase": "arbiter_verdict",
  "news_id": "n003",
  "headline": "string",
  "news_type": "earnings | monetary_policy | ...",
  "weights_used": { "bull": 0.25, "bear": 0.25, "sector": 0.40, "macro": 0.10 },
  "verdict": "BULLISH | BEARISH | BINARY | NEUTRAL",
  "net_impact_score": "float, -5 to +5",
  "arbiter_reasoning": "string — 加權計算過程與採納理由",
  "agent_acceptance": {
    "bull": "full | partial | rejected",
    "bear": "full | partial | rejected",
    "sector": "full | partial | rejected",
    "macro": "full | partial | rejected"
  },
  "affected_sectors": [
    { "sector": "string", "direction": "bullish|bearish", "magnitude": "strong|moderate|weak" }
  ],
  "tickers_mentioned": ["NVDA", "TSM"],
  "macro_backdrop_delta": "float, -1.0 to +1.0",
  "binary_risk": {
    "is_binary": "true | false",
    "event_date": "YYYY-MM-DD or null",
    "within_48h": "true | false"
  },
  "cache_action": "UPDATE_SECTOR | UPDATE_PHASE0 | UPDATE_BOTH | NO_UPDATE"
}
```

**仲裁規則**：
- `|max_agent_score - min_agent_score| ≥ 4` → verdict = `BINARY`（四方嚴重分歧）
- `source_credibility = LOW` AND `|net_impact_score| > 3` → 截斷至 ±2 + `credibility_warning`
- `binary_risk.within_48h = true` → 所有相關產業降一個 verdict 等級
- Sector vs Macro 差 ≥ 3 → 必須在 `arbiter_reasoning` 解釋採納哪方

---

## PHASE 4 — CACHE PATCH（Stage 2 / REVIEW 才執行）

### 更新 sector_intel.json（在 `top_catalysts` prepend）
```json
{
  "rank": "recalculate",
  "event": "headline",
  "type": "news_type",
  "impact_score": "mapped 1–5",
  "affected_sectors": [],
  "direction": "bullish | bearish | binary",
  "timing": "within_48h | this_week | beyond",
  "source": "news_protocol_v2",
  "updated_at": "YYYY-MM-DD HH:MM"
}
```

### 更新 phase0.json
```json
{
  "last_news_update": "YYYY-MM-DD HH:MM",
  "news_patch_count": "integer",
  "macro_backdrop_score": "updated float"
}
// binary_risk=true → append binary_risks[]
```

### 寫入 news_logs/YYYY-MM-DD_digest.json

Schema 完整定義：**`./digest_output_schema.md`**（本 protocol 不再內嵌 JSON 範本）。

**重點**：
- DIGEST：`verdicts[]` 必須包含全部 Stage 1 項目（shallow + deep 混合），不得丟棄 shallow
- FLASH：`stage1_count=0, stage2_count=1`；deep verdict `review_status=pending, cache_updated=false`
- REVIEW：`review_status: pending → reviewed`
- V2.1 新增：`fanout_mode` / `degraded_agents` / `subagent_isolated` sentinel

**寫入完必須執行 validator**：
```bash
python3 news/scripts/validate_digest_output.py
```
rc=0 才可進 MD 階段。

---

### 🚨 寫入 digest.json 的強制規則（避免 API stream idle timeout）

兩次歷史案例：Phase 4 用單一超大 tool call 噴整包 digest.json → Anthropic API 的 stream idle watchdog 中斷 → rc=1 + token 全浪費。

**DO NOT**：
- ❌ `Bash` + heredoc（`cat > file.json <<EOF ... EOF`、`python3 -c "json.dump(...)"`）一次灌入
- ❌ 單一 `Write` 把整個 digest.json 當一個字串 argument 傳入
- ❌ Phase 4 寫檔前又跑大量 `thinking` block（thinking 後接大 tool_use 最容易觸發 stream idle）

**MUST**：
1. 用 `Write` 工具（不是 `Bash`）
2. **分塊寫**：>10 則或 >8KB 必須拆：
   - 第 1 call：skeleton（top-level 欄位 + `"verdicts": [`）
   - 第 2..N call：每次 append 5-10 筆 verdicts
   - 最後 call：封檔（補 `]` + `session_macro_delta`）
3. **推薦**：用 `Write` 寫 shallow-only 版本 → 再用 `Bash` 跑 merge script（`news/scripts/digest_append_deep.py`）分批加入 deep verdicts（每 call input_json 都很小）
4. 寫完立刻跑 validator（rc=0 才算成功）

**撞到 Stream idle timeout**：
不要重跑 protocol，改跑 **`news/scripts/salvage_digest.py`** 從 `scan_logs/news_*.log` 重組 digest.json（零 API 成本，只能救 deep verdicts）。

---

## 最終報告（Markdown）

**路徑**：
- DIGEST → `reports/YYYY-MM-DD_news_digest.md`
- FLASH → `reports/YYYY-MM-DD_HHMM_news_flash.md`

### DIGEST MD 三段（按順序）

1. **Triage Summary** — 一行式篩選表（Stage 1 所有 items，含 DEEP/SKIP 標籤）
2. **Deep Analysis** — Stage 2 晉級項目的完整 Impact Card
3. **Shallow Digest** — Stage 1 未晉級項目緊湊小卡
   - 按 `|shallow_score|` 排序，**至少前 20 則**
   - 直接沿用 Stage 1 產出的 `bull_case / bear_case / sector_view / macro_view`（不額外產 token）

**Shallow Digest 小卡格式**：
```markdown
### [score] news_id  headline
- **Bull**: bull_case
- **Bear**: bear_case
- **Sector**: sector_view
- **Macro**: macro_view
- Source: source HIGH|MEDIUM|LOW │ type: news_type
---
```

### Final Impact Card（Deep）
```
╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  YYYY-MM-DD HH:MM  │  MODE: DIGEST/FLASH  ║
╠══════════════════════════════════════════════════════════╣
║  [BULLISH +3.2]  NVDA Q3 guidance raised 12%             ║
║  type: earnings  │  weights: Sector 40%                 ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ AI capex 週期續航，雲端客戶追加訂單              ║
║  BEAR    ❌ 高基期 + 中國出口管制，FY27 成長率收斂            ║
║  SECTOR  ✅ Semi +strong, Semi-equip +moderate             ║
║           tickers: NVDA, TSM, ASML, AVGO                   ║
║  MACRO   ➖ 對 Fed 路徑中性，非通膨驅動                      ║
║  ARBITER → BULLISH, 採 Sector 主論點                       ║
╠══════════════════════════════════════════════════════════╣
║  受益產業 ↑  Semi (+strong)  Semi-equip (+moderate)      ║
║  受損產業 ↓  None                                         ║
║  Binary Risk  No                                          ║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel.json ✅  phase0.json ✅     ║
╚══════════════════════════════════════════════════════════╝
```

---

## FLASH MODE

```
使用者貼新聞/個股 → News Collector WebFetch
  → Stage 2 Deep Debate（4 agent 完整辯論，fanout_mode: INLINE）
  → Arbiter → review_status: pending → Impact Card
  ⚠️ 不 patch cache（等 REVIEW 才 patch）
```

**FLASH 寫入規則**：
- `review_status: pending` → 不 patch `sector_intel.json` / `phase0.json`
- 寫 `news_logs/YYYY-MM-DD_digest.json` → Dashboard「待審核」tab
- 使用者按 Dashboard「送審」觸發 REVIEW

---

## REVIEW MODE

```
觸發：「新聞分析 審核 [headline]」
  → 讀 news_logs 匹配的 pending verdict
  → 4 agent 擴展辯論（snap 30 字 → 完整 200+ 字，per-agent batch subagent）
  → Arbiter 正式裁決（可覆寫原 verdict / score）
  → review_status: pending → reviewed
  → 執行 cache patch
  → 覆寫原 verdict + 更新 Impact Card
```

**流程細節**：

1. **載入原 FLASH verdict**：`news/news_logs/YYYY-MM-DD_digest.json` 搜 `review_status: pending` + `headline` keyword match；多筆 → 列清單讓使用者選。

2. **擴展辯論（subagent 模式）**：
   - 同訊息內發 4 個 Agent tool call（Bull / Bear / Sector / Macro）
   - 每 subagent 看：該則 full text + 原 FLASH 4 agent snap（`prior_flash` 參考，可推翻但需在 `why_changed` 說明）+ Phase 0 macro + 自己 rubric
   - **不得**看其他 agent expanded output
   - 每人輸出 150–250 字 + `subagent_isolated: true`
   - `fanout_mode: PER_AGENT_BATCH`（N=1 也用 batch schema）

3. **Arbiter 正式裁決**：可改 verdict / net_impact_score，必須在 `arbiter_reasoning` 說明與原 FLASH 的差異。

4. **寫入**：
   - `news_logs/YYYY-MM-DD_digest.json`：覆寫原 verdict，`review_status: reviewed`，`depth: deep`
   - 執行 cache patch（Phase 4 規則）
   - Impact Card 標記 `REVIEWED ✅`
