# Breaking News Intelligence Protocol (V2.2)

<!-- [scope] equity-market news analysis. Stage 1 deterministic triage + Stage 2 deep-debate
     patterns are [framework]. RSS feeds and mega-cap focus are [domain:us-equity]. -->

> 背景說明、版本演進、團隊敘述、token 預算請見 `news/README.md`。
> Digest shape 定義：`news/digest_output_schema.md`（唯一事實來源）。

---

## SESSION STARTUP

```
MODE : FLASH | DIGEST | REVIEW
  FLASH  = 單則即時新聞，直接深度辯論（< 5 分鐘）
  DIGEST = script triage → 漏斗篩選 → 深度辯論（全面更新 cache）
  REVIEW = 對一則 pending FLASH 重新進行正式委員會審核
```

**觸發**：
- 貼標題/連結 → FLASH
- 「更新新聞 cache」「新聞分析 DIGEST」→ DIGEST
- 「新聞分析 審核 [headline]」→ REVIEW

---

## GLOBAL RULES

1. **Debate Required**：每則進入 Stage 2 的新聞必須產出 Bull / Bear / Sector / Macro 四視角，禁止單面結論。
2. **Token Discipline**（V2.2 強化）：
   - **Stage 1 triage 由 `news/scripts/stage1_triage.py` deterministic 執行** — LLM **禁止讀 raw.json 全文**、禁止手寫 shallow snaps
   - DIGEST **禁止** WebSearch 為主要來源（僅 Stage 2 fetch 失敗 fallback，單次 query ≤ 2 條）
   - Stage 2 WebFetch 硬上限 **5 則**；bundle 每篇全文截 **5000 chars**（保留開頭，截斷處標 `[truncated]`）
3. **Theme Cache**（FRESH = mtime < 3h）：執行 `python3 skills/theme-detector/scripts/theme_detector.py --skip-if-fresh 10800`；script 自管 freshness，完成後讀 `skills/theme-detector/cache/theme_detector_*.json` 最新檔（`theme_source: THEME_CACHE`）。
4. **Cache Patch 時機**：**只有 Stage 2 深度辯論結論**能 patch cache。digest.json 的 shallow 取 **top 10**（依 `|shallow_score|` 排序），snaps 照抄 triage.json（script template 產出，不重寫）。
5. **FLASH**：單則直接進 Stage 2（跳 Stage 1），標記 `review_status: pending`（**不 patch cache**），等 REVIEW 升級後才 patch。
6. **REVIEW**：讀 `review_status: pending` → 4 agent 擴展辯論 → Arbiter 正式裁決（可覆寫 verdict / score）→ `pending → reviewed` → 執行 cache patch。
7. **Output**：邏輯 JSON + 結論 Markdown Impact Card。
8. **review_status 語意**：`reviewed` = 允許 patch（DIGEST Stage 2 / REVIEW 通過）；`pending` = FLASH，不 patch。

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

## TOOL BOUNDARIES — Write Isolation

News protocol 處理 untrusted external input（RSS / Finnhub / scraped headlines），是本專案攻擊面最大的 protocol — RSS publisher 可植入 instruction-shaped strings。因此 Write 權集中化：

| Subagent | Read | Grep | WebFetch | Write | Edit | Bash | Agent |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **Bull / Bear / Sector / Macro** (Stage 2) | ✅ | ✅ | ✅ (≤5 則) | **❌** | **❌** | ❌ | ❌ |
| **Arbiter** (Stage 3) | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| **PM (orchestrator inline)** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**執行細則**：
1. Stage 1 triage 已 deterministic（script 寫 triage.json），無 LLM subagent 涉入。
2. Stage 2 Analyst 回傳 verdict JSON，**不寫檔**；Arbiter 整合 + 寫 digest.json。
3. Agent tool 不接受 per-call tool restriction → subagent prompt **首句必須包含**：「You are a READER subagent. Forbidden tools: Write, Edit, NotebookEdit, Bash. Only use Read / Grep / WebFetch. Return your verdict as JSON in the response — do NOT attempt to write any file. PM will write the consolidated cache.」
4. PM 驗證 subagent 回傳：若含 `"file_written": ...` 或 explicit Write tool_use → reject + retry 一次。
5. FLASH / REVIEW 同樣套用：subagent 4-view reader-only，PM 寫雙 artifact。

---

## DIGEST MODE — 兩階段漏斗

### 🚫 DIGEST mode 絕對硬規定（違反 = 偷懶，validator 會 reject）

1. **必須執行 `python3 news/scripts/stage1_triage.py`** 產出今日 `news_logs/YYYY-MM-DD_triage.json`（validator 會 cross-check digest vs triage）
   - **禁止** LLM 手工 triage、**禁止讀 raw.json 全文**（287KB ≈ 70K tokens 純浪費）
2. **必須 dispatch 4 個 Agent tool_use** 跑 Stage 2 subagent（Bull / Bear / Sector / Macro _Analyst）
   - **禁止**在 thinking block 裡幻想 4 視角、**禁止**單 model inline generate 4-view
   - 每個 Agent 回傳必含 `"agent": "<LANE>_Analyst"` + `"subagent_isolated": true` sentinel
3. **必須 Write `news_logs/YYYY-MM-DD_digest.json`**，`timestamp` 必須今天 — validator freshness gate（timestamp + mtime）會擋舊檔
4. **禁止跳過 Stage 1/2 直接寫 MD 報告**（歷史 bug：讀昨天 MD 當範本編出假報告）

### STAGE 1 — DETERMINISTIC TRIAGE（script，0 LLM 算分）

```
1. news_logs/YYYY-MM-DD_raw.json 不存在或 mtime > 1h
   → python3 news/fetch_all_news.py --hours 24 --output news/news_logs/
     （4 fetcher 平行：RSS 9 源 / Finnhub / FMP / SEC EDGAR 8-K；dedupe + graceful degradation）
2. python3 news/scripts/stage1_triage.py
   → 寫 news_logs/YYYY-MM-DD_triage.json + stdout 印 triage 表
   → script 內含：hard-block（law-firm 廣告/地產 PR/理財專欄）、headline-template dedup、
     content-aware credibility downgrade、rule-based news_type、keyword score -5~+5、
     4-view template snaps、晉級 gate（|score|≥1.5 / HIGH×|score|≥0.5 / binary，取 top 5）
3. LLM 只讀：script stdout 表 + triage.json 的 `stage2_items`（≤5 則）+ `shallow_verdicts` top-25
4. LLM 單次 pass 增補（不另起 subagent）：
   - top-15（晉級 5 + shallow 前 10）填 `headline_zh`
   - 可選：top-10 snaps 語意明顯錯誤時改寫（template snap 為 news_type 通用句，多數照用）
   - 增補內容隨 Phase 4 進 digest.json，**不回寫 triage.json**
```

**晉級名單 = triage.json `stage2_items`**（script 已依 gate + `|shallow_score|` 取 ≤5）。

**使用者互動**（互動模式才有；server 觸發跳過直接續跑）：
- 印 script triage 表 → `繼續` / `ok` → 進 Stage 2
- `加選 n0012` → 加入該則（仍受 5 則上限），**同步 Edit triage.json**：該項 `advance_to_stage2: true` 並加入 `stage2_items`（validator 對照 deep ⊆ stage2_items）
- `剔除 n0003` → 從 Stage 2 移除（triage.json 同步反向處理）
- 無回覆超時 → 直接執行 Stage 2

### STAGE 2 — DEEP DEBATE（per-agent batch subagent）

#### 執行流程
1. **News Collector inline**：對每則晉級新聞 `WebFetch url`；失敗 → 1 次 WebSearch fallback。組 full_text_bundle（≤5 則，每篇截 5000 chars）
2. **4 subagent 平行（同一則訊息內 4 tool_use）**：每個 agent 看全部晉級新聞 bundle + Phase 0 macro 快照 + 自己 lane rubric；**看不到**其他 agent output
3. **Fan-in**：Arbiter 收 4 個 JSON（每個內含 N 則 per-item 分析）→ 逐則合併 → 正式裁決
4. 每個 subagent 輸出必含 `subagent_isolated: true` sentinel

#### Subagent Prompt 模板

```
Agent(
  description="<LANE> Stage 2 batch analyst",
  subagent_type="general-purpose",
  prompt="""
  You are a READER subagent. Forbidden tools: Write, Edit, NotebookEdit, Bash.
  Only use Read / Grep / WebFetch. Return your verdict as JSON in the response —
  do NOT attempt to write any file. PM will write the consolidated cache.

  You are the <LANE> analyst for Stage 2 deep debate.

  ISOLATION CONTRACT:
    - 你與其他 3 個 agent 以獨立 context 平行執行
    - 禁止推測其他 lane 結論、禁止為「與共識一致」調整 impact_score
    - 禁止跨題串接語氣（同日 5 則皆偏空仍各自獨立評估）

  PHASE 0 MACRO CONTEXT:
  <paste phase0 macro_summary — read-only shared>

  STAGE 2 NEWS BUNDLE（N 則，N ≤ 5，每篇 ≤5000 chars）：
  <paste each news item: full_text + news_id + source + news_type>

  YOUR LANE RUBRIC:
  <RUBRIC_LANE>

  OUTPUT: 單一 JSON object：
  { "agent": "<LANE>_Analyst", "subagent_isolated": true,
    "per_item": { "<news_id_1>": { ...本 lane 完整分析 schema... }, ... } }
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
| 4 subagent 全成功 + `subagent_isolated=true` | `PER_AGENT_BATCH` | 正常 |
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
  "agent_acceptance": { "bull": "full | partial | rejected", "bear": "...", "sector": "...", "macro": "..." },
  "affected_sectors": [ { "sector": "string", "direction": "bullish|bearish", "magnitude": "strong|moderate|weak" } ],
  "tickers_mentioned": ["NVDA", "TSM"],
  "macro_backdrop_delta": "float, -1.0 to +1.0",
  "binary_risk": { "is_binary": "true | false", "event_date": "YYYY-MM-DD or null", "within_48h": "true | false" },
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

Schema 完整定義：**`./digest_output_schema.md`**（本 protocol 不內嵌 JSON 範本）。

**Shape 重點**：
- DIGEST：`verdicts[]` = deep（≤5）+ top-10 shallow（snaps 照抄 triage.json）
- `stage1_count` = triage.json `shallow_verdicts` 長度（validator 嚴格對照，**不是** raw_count）
- 每筆 verdict 帶 `published`（從 triage.json 對應 news_id 抄 ISO timestamp — UI 算 freshness）
- FLASH：`stage1_count=0, stage2_count=1`；deep verdict `review_status=pending, cache_updated=false`
- REVIEW：`review_status: pending → reviewed`
- V2.1+ 欄位：`fanout_mode` / `degraded_agents` / `subagent_isolated` sentinel

### Phase 4 寫入規則

**唯一可用模式：單次 Write 呼叫，完整 digest.json**

| DO | DO NOT |
|---|---|
| **⚠️ 先 `Read news_logs/YYYY-MM-DD_digest.json`**（解鎖 Write-safety 守門；不存在則忽略錯誤）| 不准 `Bash` + heredoc（`cat > file <<EOF`）|
| 用 `Write` 一次寫完 | 不准建 chunks 子資料夾 / 分多次 Write / 多檔合併 |
| shallow 硬上限 **top 10**；整包 > 25KB → 砍到 top 5 | 不准寫 assemble/append 輔助腳本（已封存 `news/scripts/archive/`）|

**預期大小**：5 deep（~800B/則）+ 10 shallow（~300B/則）+ header ≈ **7-9KB**，單次 Write < 1 min。

### Step by step

```
1. Read news_logs/YYYY-MM-DD_digest.json     ← 必做，解鎖 Write-safety 守門
2. Write 一次 → digest.json（完整 JSON、shallow ≤ 10）
3. Bash: python3 news/scripts/validate_digest_output.py
4. rc ≠ 0 → 一次 Edit 修 → 再跑 validator
5. Bash: 單次 Python one-liner patch sector_intel.json（prepend top_catalysts）
6. Bash: 單次 Python one-liner patch phase0.json（macro_backdrop + binary_risks）
7. 生 MD 報告（見下）
```

**硬規定**：Phase 4 總 tool call（Bash/Write/Edit/Read）**≤ 9 次**。超過 = over-engineering，停下重規劃。
**撞 Stream idle timeout（極少）**：跑 `archive/salvage_digest.py` 從 log 重組，不要重跑 protocol。

> **Phase 4.5 — Structural Watchlist**：由 `daily_update.sh` Step 7 自動跑
> `news/scripts/build_structural_watchlist.py`（deterministic，LLM 不參與）。
> Keyword whitelist / decay 規則 / schema 見 `news/README.md` §Structural Watchlist。

---

## 最終報告（Markdown）

**路徑**：
- DIGEST → `reports/YYYY-MM-DD_news_digest.md`
- FLASH → `reports/YYYY-MM-DD_HHMM_news_flash.md`

### DIGEST MD 三段（按順序）

1. **Triage Summary** — 一行式篩選表（照抄 script stdout 表，含 DEEP/SKIP 標籤 + blocked/dedup 統計）
2. **Deep Analysis** — Stage 2 晉級項目完整 Impact Card
3. **Shallow Digest** — **top 10**（與 digest.json 一致）；snaps 直接照抄 triage.json，**不額外產 token**

**Shallow 小卡格式**：
```markdown
### [score] news_id  headline
- **Bull**: bull_case ｜ **Bear**: bear_case
- **Sector**: sector_view ｜ **Macro**: macro_view
- Source: source HIGH|MEDIUM|LOW │ type: news_type
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
║  受損產業 ↓  None            Binary Risk  No             ║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel.json ✅  phase0.json ✅     ║
╚══════════════════════════════════════════════════════════╝
```

---

## FLASH MODE

```
使用者貼新聞/個股 → News Collector WebFetch
  → Stage 2 Deep Debate（4 視角完整辯論，fanout_mode: INLINE）
  → Arbiter → review_status: pending → Impact Card
  ⚠️ 不 patch cache（等 REVIEW 才 patch）
```

- `review_status: pending` → 不 patch `sector_intel.json` / `phase0.json`
- 寫 `news_logs/YYYY-MM-DD_digest.json` → Dashboard「待審核」tab
- 使用者按 Dashboard「送審」觸發 REVIEW

---

## REVIEW MODE

```
觸發：「新聞分析 審核 [headline]」
  → 讀 news_logs 匹配 pending verdict（多筆 → 列清單讓使用者選）
  → 4 agent 擴展辯論（snap → 完整 150-250 字，per-agent batch subagent）
  → Arbiter 正式裁決（可覆寫 verdict / score，須說明與原 FLASH 差異）
  → review_status: pending → reviewed → 執行 cache patch（Phase 4 規則）
  → Impact Card 標記 REVIEWED ✅
```

**Subagent 細則**：
- 同訊息內發 4 個 Agent tool call（Bull / Bear / Sector / Macro）
- 每 subagent 看：該則 full text + 原 FLASH snap（`prior_flash` 參考，可推翻但需 `why_changed` 說明）+ Phase 0 macro + 自己 rubric；**不得**看其他 agent expanded output
- 每人輸出 150–250 字 + `subagent_isolated: true`
- `fanout_mode: PER_AGENT_BATCH`（N=1 也用 batch schema）
