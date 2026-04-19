# Breaking News Intelligence Protocol (V2.1)

> **V2.1 改動**（vs V2.0）
> 1. **Stage 2 / REVIEW 四 agent 辯論改為 per-agent batch subagent** — Bull/Bear/Sector/Macro 各自一個 Agent tool call，一次分析全部晉級項目，彼此 context 隔離。消除同 model 序列產生 4 視角的 anchoring 風險（與 investment V4.8 Phase 2 fan-out 同邏輯）
> 2. **Phase 4 digest.json schema 抽離**至 `digest_output_schema.md`，配 `validate_digest_output.py` 驗證腳本（rc=0 才可進 MD 報告）
> 3. **新欄位**：`fanout_mode` / `degraded_agents` / `subagent_isolated` — 標示 Stage 2 執行模式與 fallback 狀態
>
> **V2.0 核心改動**（vs V1；V2.1 保留）
> 1. **兩階段漏斗**：Stage 1 RSS 便宜寬掃描 → 篩選 TOP N → Stage 2 WebFetch 深度辯論
> 2. **Team 從 3 人擴至 5 人**：新增 Sector Analyst + Macro/Policy Expert
> 3. **Triage 表**給使用者，保留人類否決/加碼權
> 4. **Cache patch 只在 Stage 2 執行**，避免噪音污染

---

## SESSION STARTUP

```
NEWS TRIGGER
──────────────────────────────────────────
MODE : FLASH | DIGEST | REVIEW
      FLASH  = 單則即時新聞，直接深度辯論（< 5 分鐘）
      DIGEST = RSS 寬掃描 → 漏斗篩選 → 深度辯論（全面更新 cache）
      REVIEW = 對一則 pending FLASH 重新進行正式委員會審核
──────────────────────────────────────────
```

> 直接貼標題/連結觸發 FLASH；說「更新新聞 cache」「新聞分析 DIGEST」觸發 DIGEST。
> 「新聞分析 審核 [headline]」觸發 REVIEW。

---

## GLOBAL RULES

1. **Debate Required**: 每則進入 Stage 2 的新聞必須產出 Bull / Bear / Sector / Macro 四個視角，禁止單面結論。
2. **Token Discipline**:
   - DIGEST mode **禁止** WebSearch 作為主要來源（只能作為 Stage 1 的 fallback，且單次 query ≤ 2 條）
   - Stage 1 只讀 RSS cache，不做任何 web 請求
   - Stage 2 WebFetch 總數硬上限 **5 則**
3. **Theme Cache**（FRESH = mtime < 3 小時）: 若需要主題背景，執行 `theme-detector` 前先讀 `skills/theme-detector/cache/theme_detector_*.json`。FRESH → 載入（`theme_source: THEME_CACHE`），STALE → 執行 skill。
4. **Cache Patch 時機**: **只有 Stage 2 深度辯論後的結論**能 patch `sector_intel.json` / `phase0.json`。Stage 1 shallow 結果**完整寫入** `news_logs/*_digest.json`（標記 `depth: shallow`）且**呈現於最終 MD 的 Shallow Digest 區塊**（見 Phase 4），不浪費已產出的 4-agent snap 觀點：
   - `sector/sector_logs/YYYY-MM-DD_sector_intel.json` — 更新 `top_catalysts` / `political_overlay`
   - `investment/invest_logs/YYYY-MM-DD_phase0.json` — 更新 `binary_risks` / `macro_backdrop_score`
   - `news/news_logs/YYYY-MM-DD_digest.json` — append 所有（shallow + deep）
5. **FLASH mode**: 單則新聞直接進入 Stage 2（跳過 Stage 1 triage），因為使用者已經明確指定分析對象。FLASH 結果標記 `review_status: pending`（**不 patch cache**），直到經過 REVIEW mode 審核後才升級為 `reviewed` 並 patch。
6. **REVIEW mode**: 讀取 `news_logs` 中 `review_status: pending` 的 FLASH verdict → 每位 Agent 重新擴展辯論（從 snap 30 字 → 完整 200+ 字）→ Arbiter 正式裁決（可改變原 FLASH verdict / score）→ `review_status: pending → reviewed` → 此時才執行 cache patch。
7. **Output**: 邏輯輸出 JSON，結論輸出 Markdown Impact Card。
8. **review_status 欄位**:
   - `reviewed` — DIGEST Stage 2 結果 或 REVIEW mode 審核通過 → 允許 patch cache → Dashboard 顯示為「已審核」
   - `pending` — FLASH 結果，尚未經委員會審核 → **不 patch** `sector_intel.json` / `phase0.json` → Dashboard 顯示為「待審核」

---

## TEAM STRUCTURE

| Agent | 執行模式（V2.1）| 職責 | 核心關注點 |
|---|---|---|---|
| **News Collector** | inline | 蒐集 RSS / WebFetch 原文，確認來源可信度 | 來源 credibility、時效性、去重 |
| **Bull Analyst** | Stage 1 inline / **Stage 2 subagent batch** | 多頭角度解讀 | 受益族群、催化劑類型、短中期驅動 |
| **Bear Analyst** | Stage 1 inline / **Stage 2 subagent batch** | 空頭角度解讀 | 受損族群、風險傳導、尾部風險 |
| **Sector Analyst** | Stage 1 inline / **Stage 2 subagent batch** | 產業分析師視角 | 上下游傳導、供應鏈 2 階效應、受影響個股清單 |
| **Macro/Policy Expert** | Stage 1 inline / **Stage 2 subagent batch** | 財經/政策專家 | Fed 路徑、殖利率、匯率、地緣政治、歷史類比 |
| **News Arbiter** | inline | 仲裁辯論、加權評分、執行 cache patch | 綜合判斷、cache 一致性 |

> **V2.1 執行模式說明**：Stage 1 shallow triage（30-50 則 × 4 agent snap ≤30 字）保持 inline（subagent 啟動 overhead 對 120 個短 snap 不划算）；Stage 2 deep debate（≤5 則 × 4 agent 完整辯論）改用 **per-agent batch subagent** — 每位 agent 一個 Agent tool 呼叫，一次看全部 Stage 2 晉級項目並輸出 N 份自己視角的分析，彼此不看對方輸出。目的：消除同 model 序列產生 4 視角的 anchoring 風險，與 investment protocol V4.8 Phase 2 fan-out 同邏輯。REVIEW mode 同樣套用 subagent 模式（1 則 × 4 agent 擴展）。

### Arbiter 加權規則

**基礎權重**（平權）：Bull 25% / Bear 25% / Sector 25% / Macro 25%

**動態調整**（依 `news_type` 覆蓋基礎權重）：

| news_type | Bull | Bear | Sector | Macro |
|---|---|---|---|---|
| `monetary_policy`（FOMC / 利率決議） | 15% | 15% | 20% | **50%** |
| `macro_data`（CPI / NFP / GDP） | 15% | 15% | 20% | **50%** |
| `geopolitical`（戰爭 / 關稅 / 制裁） | 15% | 30% | 15% | **40%** |
| `earnings`（財報） | 25% | 25% | **40%** | 10% |
| `corporate`（併購 / 指引 / 管理層） | 25% | 25% | **40%** | 10% |
| `sector_news`（產業訂單 / 產能） | 20% | 20% | **50%** | 10% |
| `sentiment`（Fear&Greed / VIX spike） | 30% | 30% | 15% | 25% |
| `default` | 25% | 25% | 25% | 25% |

`net_impact_score = Σ(agent_score × weight)`，四捨五入到小數點後 1 位。

---

## DIGEST MODE — 兩階段漏斗

### STAGE 1 — RSS SHALLOW TRIAGE

**Agent**: News Collector + 4 位分析師（輕量模式，每則限 1–2 句）

**資料來源**：
1. 先檢查 `news/news_logs/YYYY-MM-DD_raw.json` 是否存在（由 `news/fetch_news_rss.py` 產出）
2. 若不存在或 `mtime > 1 小時`，執行：
   ```bash
   python3 news/fetch_news_rss.py --hours 24 --output news/news_logs/
   ```
3. 讀取 raw.json 取得 30–50 則標題 + 摘要

**Stage 1 輸出結構**：

```json
{
  "phase": "stage1_triage",
  "timestamp": "YYYY-MM-DD HH:MM",
  "source": "RSS_CACHE",
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
      "bull_case": "string ≤ 30 字 — Bull 一句話（寫入 news_logs 時直接沿用此欄位）",
      "bear_case": "string ≤ 30 字 — Bear 一句話",
      "sector_view": "string ≤ 30 字 — Sector Analyst 一句話",
      "macro_view": "string ≤ 30 字 — Macro Expert 一句話",
      "shallow_score": "-5 to +5（加權後）",
      "binary_flag": "true | false",
      "advance_to_stage2": "true | false",
      "advance_reason": "string or null"
    }
  ],
  "advanced_count": "integer ≤ 5"
}
```

### STAGE 1 → STAGE 2 晉級門檻

**符合任一條件即晉級**：
- `|shallow_score| ≥ 3`
- `binary_flag = true` 且事件在 48h 內
- `source_credibility = HIGH` 且 `|shallow_score| ≥ 2`
- 使用者在 Triage 表上手動勾選

**硬上限**：最多 5 則進入 Stage 2（若超過，依 `|shallow_score|` 排序取前 5）

### STAGE 1 輸出 — Triage 表（給使用者審核）

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
║  ❌ SKIP   n005  [+0.5]  MSFT partnership             corp    ║
║  ... (34 more skipped)                                        ║
╠══════════════════════════════════════════════════════════════╣
║  💡 要手動加選任何 SKIP 項目進入 DEEP 嗎？回覆 news_id 或「繼續」║
╚══════════════════════════════════════════════════════════════╝
```

**使用者互動**：
- 回覆 `繼續` / `ok` / `proceed` → 直接進 Stage 2
- 回覆 `加選 n001 n005` → 把指定項目加入 Stage 2（但仍受硬上限 7 則約束）
- 回覆 `剔除 n019` → 從 Stage 2 移除
- **無回覆超時預設**：繼續執行 Stage 2（避免阻塞）

---

### STAGE 2 — DEEP DEBATE（V2.1 per-agent batch subagent）

**Agents**：News Collector（inline WebFetch）+ Bull / Bear / Sector / Macro（**4 個平行 subagent，batch mode**）+ Arbiter（inline）

#### 執行流程
1. **News Collector inline**：對每則晉級新聞執行 `WebFetch url`；失敗則 1 次 WebSearch fallback。蒐集 full_text_bundle（≤ 5 則 × 全文）
2. **4 subagent 平行呼叫（同一則訊息內 4 tool_use）** — 每個 agent 看到：
   - 全部晉級新聞（full text）
   - Phase 0 macro 快照（read-only shared context）
   - 自己 lane 的 rubric（見下）
   - **看不到**：其他 agent 的 output、其他 session 的 bias
3. **Fan-in**：Arbiter 收到 4 個 subagent 的 JSON（每個內含 N 個 per-item 分析）→ 逐則合併 → 正式裁決
4. 每個 subagent 輸出 JSON 必含 `subagent_isolated: true` sentinel

#### Subagent Prompt 模板（每個 lane 差在 `<LANE>` + rubric）
```
Agent(
  description="<LANE> Stage 2 batch analyst",
  subagent_type="general-purpose",
  prompt="""
  You are the <LANE> analyst for Stage 2 deep debate.

  ISOLATION CONTRACT:
    - 你與其他 3 個 agent 以獨立 context 平行執行。
    - 禁止推測其他 lane 的結論。
    - 禁止為了「與共識一致」調整 impact_score。
    - 禁止跨題串接語氣（即使同一天 5 則都偏空，你仍各自獨立評估每則）。

  PHASE 0 MACRO CONTEXT:
  <paste phase0 macro_summary — read-only shared>

  STAGE 2 NEWS BUNDLE（N 則，N ≤ 5）：
  <paste each news item with full_text + news_id + source + news_type>

  YOUR LANE RUBRIC:
  <RUBRIC_LANE>（Bull / Bear / Sector / Macro 各一份，見下）

  OUTPUT: 單一 JSON object，包含每則新聞的本 lane 分析：
  {
    "agent": "<LANE>_Analyst",
    "subagent_isolated": true,
    "per_item": {
      "<news_id_1>": { ...本 lane 的完整分析 schema... },
      "<news_id_2>": { ... },
      ...
    }
  }
  """
)
```

#### Per-Lane Rubric

**Bull Analyst**：找多頭論據。每則輸出 `{interpretation, primary_beneficiary_sectors[], catalyst_type ∈ {demand_increase, cost_reduction, policy_tailwind, sentiment_boost, short_squeeze}, impact_score 1~5, time_horizon ∈ {immediate, short_term, mid_term}, confidence 0-1, key_assumption}`

**Bear Analyst**：找空頭論據。每則輸出 `{interpretation, primary_at_risk_sectors[], risk_type ∈ {demand_destruction, cost_increase, policy_headwind, sentiment_crash, contagion}, impact_score -5~-1, time_horizon, confidence, key_assumption}`

**Sector Analyst**：每則輸出 `{primary_sectors[{sector, direction, magnitude}], supply_chain_impact, tickers_mentioned[] (≥1 或顯式空陣列 + 理由), impact_score -5~+5, confidence}`

**Macro/Policy Expert**：每則輸出 `{fed_path_delta, yield_curve_impact, fx_commodity_impact, historical_analogue, impact_score -5~+5, confidence}`

#### 辯論強制規則（跨 agent，由 Arbiter 驗證）
- Bull / Bear 不得同為 |impact| ≤ 1（代表沒真正辯論）→ Arbiter 退回該則要求 re-analyze
- `source_credibility = LOW` → 四方 confidence 上限 0.5（subagent 自律 + Arbiter 複檢）
- 含 binary event → Bear + Macro 必須標記 `binary_risk: true`

#### Fan-Out 失敗處理（fanout_mode 對照）

| 情境 | `fanout_mode` | 處理 |
|---|---|---|
| 4 subagent 全部成功、`subagent_isolated=true` | `PER_AGENT_BATCH` | 正常流程 |
| 1-2 subagent timeout / malformed JSON → retry 1 次仍失敗 | `PARTIAL_FALLBACK` | 失敗者 inline fallback；`degraded_agents` 列出降級名單；該 agent confidence 上限 0.5 |
| 3-4 subagent 失敗 | `FULL_FALLBACK` | 整批 inline 產出；Arbiter 對該 DIGEST 的 BULLISH verdict 強制降級（例：BULLISH → NEUTRAL，BEARISH 保留不變）以反映 debate 品質下滑 |

**Single-item 特例（FLASH mode）**：1 則新聞時可直接 inline 四視角辯論（`fanout_mode: INLINE`），subagent overhead 不划算。

---

## PHASE 3 — ARBITER VERDICT

**Agent**: News Arbiter

```json
{
  "phase": "arbiter_verdict",
  "agent": "News_Arbiter",
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
- `|max_agent_score - min_agent_score| ≥ 4` → verdict = BINARY（四方嚴重分歧）
- `source_credibility = LOW` AND `|net_impact_score| > 3` → 截斷至 ±2，加 `credibility_warning`
- `binary_risk.within_48h = true` → 所有相關產業降一個 verdict 等級
- Sector vs Macro 嚴重衝突（差 ≥ 3）→ 必須在 `arbiter_reasoning` 解釋採納哪方

---

## PHASE 4 — CACHE PATCH（僅 Stage 2 / FLASH 執行）

### 更新 sector_intel.json
```json
// PATCH: sector/sector_logs/YYYY-MM-DD_sector_intel.json
// 在 top_catalysts 陣列 prepend：
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
// PATCH: investment/invest_logs/YYYY-MM-DD_phase0.json
{
  "last_news_update": "YYYY-MM-DD HH:MM",
  "news_patch_count": "integer",
  "macro_backdrop_score": "updated float"
}
// 若 binary_risk=true → append binary_risks[]
```

### 寫入 news_logs（shallow + deep 都要寫）

**Schema 定義位置**：`news/news_logs/YYYY-MM-DD_digest.json` 的完整 shape、必填欄位、三種 mode 差異（DIGEST / FLASH / REVIEW）、`fanout_mode` / `degraded_agents` / `subagent_isolated` 新欄位說明、DO NOT 禁止清單與 FULL EXAMPLE 全部集中於 **`./digest_output_schema.md`**。本 protocol 不再內嵌 JSON 範本。

**關鍵重點**（完整規範對照 schema 檔）：
- **DIGEST mode**：`verdicts[]` 必須包含全部 Stage 1 項目（shallow + deep 混合），不得丟棄 shallow — Dashboard 的 Shallow Digest 區塊需要這些資料
- **FLASH mode**：`stage1_count=0, stage2_count=1`；單筆 deep verdict `review_status=pending, cache_updated=false`
- **REVIEW mode**：`review_status: pending → reviewed`，此時才執行 cache patch
- **V2.1 新增**：`fanout_mode ∈ {PER_AGENT_BATCH, PARTIAL_FALLBACK, FULL_FALLBACK, INLINE}`、`degraded_agents[]`、每則 deep verdict 的 `subagent_isolated` sentinel

**Phase 4 結束前必須執行 validator**：
```bash
python3 news/scripts/validate_digest_output.py
```
rc ≠ 0 時必須修正 `news_logs/YYYY-MM-DD_digest.json` 後再跑一次，直到 rc=0 才可進 MD 報告階段。常見失敗：DIGEST 丟棄 shallow verdicts、deep verdict 缺 `arbiter_reasoning` / `subagent_isolated`、FLASH 誤設 `review_status=reviewed`。

### 儲存最終報告（Impact Card MD）
- **DIGEST** → `reports/YYYY-MM-DD_news_digest.md`
- **FLASH** → `reports/YYYY-MM-DD_HHMM_news_flash.md`

#### DIGEST MD 必須包含三段（按順序）

1. **Triage Summary** — 一行式篩選表（Stage 1 所有 items，含 DEEP/SKIP 標籤）
2. **Deep Analysis** — Stage 2 晉級項目的完整 Impact Card（含 4 agent 完整論述）
3. **Shallow Digest** — Stage 1 未晉級項目的緊湊小卡
   - 按 `|shallow_score|` 由大到小排序，**至少顯示前 20 則**（軟上限，完整項目仍在 `news_logs/*_digest.json`）
   - 每則格式固定為 4 個 agent 的 snap 句子，**不額外產生 token**（直接沿用 Stage 1 已打出的 `bull_case / bear_case / sector_view / macro_view`）

**Shallow Digest 小卡格式**：

```markdown
### [score] news_id  headline
- **Bull**: bull_case（Stage 1 snap 句）
- **Bear**: bear_case
- **Sector**: sector_view
- **Macro**: macro_view
- Source: source HIGH|MEDIUM|LOW │ type: news_type
---
```

**範例**：

```markdown
### [+2.2] n033 Wall St closes at record
- **Bull**: 動能突破歷史高，FOMO 進場
- **Bear**: 估值擴張 VIX 低檔，尾部風險累積
- **Sector**: 權值股領漲，breadth 有待確認
- **Macro**: 利率環境支撐，但 Fed 路徑是關鍵
- Source: Investing.com HIGH │ type: sentiment
---
```

**目的**：保留所有 Stage 1 已產出的分析觀點（否則 token 浪費），同時用緊湊格式避免 MD 過度膨脹。讀者可在 Triage 表快速掃描 → 在 Shallow Digest 看到 4 視角初步意見 → 在 Deep Analysis 看到晉級項目的完整辯論。

---

## FINAL IMPACT CARD（Markdown）

```
╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  YYYY-MM-DD HH:MM  │  MODE: DIGEST/FLASH  ║
╠══════════════════════════════════════════════════════════╣
║  [BULLISH +3.2]  NVDA Q3 guidance raised 12%             ║
║  type: earnings  │  weights: Sector 40%                 ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ AI capex 週期續航，雲端客戶追加訂單              ║
║  BEAR    ❌ 高基期 + 中國出口管制，FY27 成長率收斂            ║
║  SECTOR  ✅ Semi +strong, Semi-equip +moderate, Utilities +weak║
║           tickers: NVDA, TSM, ASML, AVGO, VRT              ║
║  MACRO   ➖ 對 Fed 路徑影響中性，非通膨驅動                  ║
║  ARBITER → BULLISH, 採 Sector 主論點，Bear 高基期警告保留    ║
╠══════════════════════════════════════════════════════════╣
║  受益產業 ↑  Semi (+strong)  Semi-equip (+moderate)      ║
║  受損產業 ↓  None                                         ║
║  Binary Risk  No                                          ║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel.json ✅  phase0.json ✅     ║
╚══════════════════════════════════════════════════════════╝
```

---

## FLASH MODE 簡化流程

```
使用者貼新聞 / 個股觸發 → News Collector WebFetch
  → Stage 2 Deep Debate（4 agent 完整辯論）
  → Arbiter → review_status: pending → Impact Card
  ⚠️ 不執行 cache patch（等 REVIEW 確認後才 patch）
```

FLASH mode **跳過 Stage 1**，因為：
1. 使用者已明確指定新聞 → 不需要篩選
2. 只有 1 則 → 無需漏斗
3. 通常有時效性 → 快速深讀

**FLASH 寫入規則**：
- `review_status: pending` → 不 patch `sector_intel.json` / `phase0.json`
- 寫入 `news_logs/YYYY-MM-DD_digest.json` → Dashboard 顯示在「待審核」tab
- 使用者可在 Dashboard 按「送審」觸發 REVIEW mode

---

## REVIEW MODE — 正式委員會審核

```
觸發：「新聞分析 審核 [headline]」
  → 讀取 news_logs 中匹配的 pending verdict
  → 4 agent 擴展辯論（snap 30 字 → 完整 200+ 字分析）
  → Arbiter 正式裁決（可覆寫原 verdict / score）
  → review_status: pending → reviewed
  → 執行 cache patch（sector_intel + phase0）
  → 覆寫原 verdict 到 news_logs + 更新 Impact Card
```

### REVIEW 流程細節

**Step 1 — 載入原 FLASH verdict**：
在 `news/news_logs/YYYY-MM-DD_digest.json` 搜尋 `review_status: pending` 且 `headline` 含 keyword match 的 verdict。若找到多筆，列出讓使用者選擇。

**Step 2 — 擴展辯論（V2.1 subagent 模式）**：
將原 FLASH 的 4 agent snap（各 ≤ 30 字）作為起點，**以 4 個平行 subagent 重新審視並擴展**：
- 同一則訊息內發 4 個 Agent tool call（Bull / Bear / Sector / Macro）
- 每個 subagent 看到：該則新聞 full text + 原 FLASH 的 4 agent snap（作為 `prior_flash` 參考，允許推翻但需在 `why_changed` 欄位說明）+ Phase 0 macro + 自己 lane 的 rubric
- **不得**看到其他 agent 的 expanded output
- 每人輸出 150–250 字完整論述（schema 同 Stage 2 Deep Debate 單則）+ `subagent_isolated: true` sentinel
- `fanout_mode: PER_AGENT_BATCH` 寫入 digest.json（REVIEW 的 N=1 也適用 batch schema）

**Step 3 — Arbiter 正式裁決**：
- 可改變 verdict（例：FLASH 判 BULLISH → REVIEW 改判 BINARY）
- 可改變 net_impact_score（重新加權計算）
- 必須在 `arbiter_reasoning` 中說明與原 FLASH 的差異（若有）

**Step 4 — 寫入**：
- `news_logs/YYYY-MM-DD_digest.json`：覆寫原 verdict，`review_status: reviewed`，`depth: deep`
- 此時執行 cache patch（Phase 4 規則）
- Impact Card 標記 `REVIEWED ✅`

### Token 預算
REVIEW ≈ 單則 Stage 2 deep：~4k tokens（比重跑 DIGEST ~28k 便宜 7 倍）

---

## 本地檔案結構

```
news/
├── README.md
├── news_protocol_v2.md              ← 本 instruction
├── fetch_news_rss.py                ← RSS 抓取腳本（新增）
└── news_logs/
    ├── YYYY-MM-DD_raw.json          ← RSS 原始資料（Stage 1 讀取）
    ├── YYYY-MM-DD_digest.json       ← 分析結果 cache（shallow + deep）
    └── YYYY-MM-DD_HH-MM_flash.json  ← FLASH cache

archive/old_protocols/news/
└── news_protocol_v1.md              ← 舊版歸檔

reports/
├── YYYY-MM-DD_news_digest.md        ← DIGEST 最終報告（含 Triage 表）
└── YYYY-MM-DD_HHMM_news_flash.md   ← FLASH 最終報告
```

---

## 觸發情境速查

| 情境 | MODE | 流程 |
|---|---|---|
| 看到重大新聞標題 | FLASH | 直接 WebFetch → Deep Debate → pending |
| 開盤前更新市場氣氛 | DIGEST | RSS → Triage → Deep Top 5 → reviewed |
| 針對個股查近期新聞 | FLASH | 「新聞分析 FLASH NVDA 近期動態」→ pending |
| Dashboard 決策卡片 📰 | FLASH | 複製 prompt → 貼回 CLI → pending |
| Dashboard 新聞頁「送審」 | REVIEW | 複製 prompt → 擴展辯論 → reviewed + cache patch |
| 盤中突發事件 | FLASH → REVIEW | 先 FLASH 快讀 → 需要時再送審正式入 cache |

---

## Token 預算參考

| 項目 | V1 | V2 |
|---|---|---|
| Web 請求 | ~30k（6 WebSearch） | ~8k（5 WebFetch）|
| RSS 解析 | 0 | ~3k（腳本預處理）|
| Agent 辯論 | ~15k（3 人） | ~12k（Stage 1 輕量 + Stage 2 4 人深度）|
| **合計** | **~45k** | **~23k** |

---

*End of Breaking News Intelligence Protocol V2.0*
