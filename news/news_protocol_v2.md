# Breaking News Intelligence Protocol (V2.0)

> **V2 核心改動**（vs V1）
> 1. **兩階段漏斗**：Stage 1 用 RSS 便宜寬掃描 → 篩選 TOP N → Stage 2 WebFetch 深度辯論
> 2. **Team 從 3 人擴至 5 人**：新增 Sector Analyst + Macro/Policy Expert
> 3. **Triage 表**給使用者，保留人類否決/加碼權
> 4. **Cache patch 只在 Stage 2 執行**，避免噪音污染

---

## SESSION STARTUP

```
NEWS TRIGGER
──────────────────────────────────────────
MODE : FLASH | DIGEST
      FLASH  = 單則即時新聞，直接深度辯論（< 5 分鐘）
      DIGEST = RSS 寬掃描 → 漏斗篩選 → 深度辯論（全面更新 cache）
──────────────────────────────────────────
```

> 直接貼標題/連結觸發 FLASH；說「更新新聞 cache」「新聞分析 DIGEST」觸發 DIGEST。

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
5. **FLASH mode**: 單則新聞直接進入 Stage 2（跳過 Stage 1 triage），因為使用者已經明確指定分析對象。
6. **Output**: 邏輯輸出 JSON，結論輸出 Markdown Impact Card。

---

## TEAM STRUCTURE

| Agent | 職責 | 核心關注點 |
|---|---|---|
| **News Collector** | 蒐集 RSS / WebFetch 原文，確認來源可信度 | 來源 credibility、時效性、去重 |
| **Bull Analyst** | 多頭角度解讀 | 受益族群、催化劑類型、短中期驅動 |
| **Bear Analyst** | 空頭角度解讀 | 受損族群、風險傳導、尾部風險 |
| **Sector Analyst** 🆕 | 產業分析師視角 | 上下游傳導、供應鏈 2 階效應、受影響個股清單 |
| **Macro/Policy Expert** 🆕 | 財經/政策專家 | Fed 路徑、殖利率、匯率、地緣政治、歷史類比 |
| **News Arbiter** | 仲裁辯論、加權評分、執行 cache patch | 綜合判斷、cache 一致性 |

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

### STAGE 2 — DEEP DEBATE

**Agent**: News Collector（WebFetch 全文）+ Bull / Bear / Sector / Macro（完整辯論）+ Arbiter

**資料來源**：
1. 對每則晉級新聞執行 `WebFetch url` 取得全文
2. 若 RSS url 為空或 WebFetch 失敗 → 允許 1 次 WebSearch fallback（`"headline" site:reuters.com OR site:bloomberg.com`）

**Stage 2 每則新聞輸出**：

```json
{
  "phase": "stage2_deep",
  "news_id": "n003",
  "headline": "string",
  "full_text_fetched": "true | false",
  "bull_case": {
    "agent": "Bull_Analyst",
    "interpretation": "string",
    "primary_beneficiary_sectors": ["sector1"],
    "catalyst_type": "demand_increase | cost_reduction | policy_tailwind | sentiment_boost | short_squeeze",
    "impact_score": "1–5",
    "time_horizon": "immediate | short_term | mid_term",
    "confidence": "0.0–1.0",
    "key_assumption": "string"
  },
  "bear_case": {
    "agent": "Bear_Analyst",
    "interpretation": "string",
    "primary_at_risk_sectors": ["sector1"],
    "risk_type": "demand_destruction | cost_increase | policy_headwind | sentiment_crash | contagion",
    "impact_score": "-5 to -1",
    "time_horizon": "immediate | short_term | mid_term",
    "confidence": "0.0–1.0",
    "key_assumption": "string"
  },
  "sector_view": {
    "agent": "Sector_Analyst",
    "primary_sectors": [
      { "sector": "string", "direction": "bullish|bearish|neutral", "magnitude": "strong|moderate|weak" }
    ],
    "supply_chain_impact": "string — 上下游 2 階效應",
    "tickers_mentioned": ["NVDA", "TSM", "..."],
    "impact_score": "-5 to +5",
    "confidence": "0.0–1.0"
  },
  "macro_view": {
    "agent": "Macro_Policy_Expert",
    "fed_path_delta": "string — 對 Fed 路徑的影響（若有）",
    "yield_curve_impact": "string",
    "fx_commodity_impact": "string",
    "historical_analogue": "string — 歷史類比案例（如 2018 關稅戰、2020 COVID）",
    "impact_score": "-5 to +5",
    "confidence": "0.0–1.0"
  },
  "debate_note": "string — 四方最大分歧點"
}
```

**辯論強制規則**：
- Bull / Bear 不得同為 impact ≤ 1（代表沒真正辯論）
- `source_credibility = LOW` → 四方 confidence 上限 0.5
- 含 binary event → Bear + Macro 必須標記 `binary_risk: true`
- Sector Analyst **必須**輸出 `tickers_mentioned`（至少 1 檔，或明確寫 `[]` 加理由）

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

```json
// APPEND: news/news_logs/YYYY-MM-DD_digest.json
// ⚠️ 缺任何欄位會導致 Dashboard 顯示空白
{
  "timestamp": "YYYY-MM-DD HH:MM",
  "mode": "FLASH | DIGEST",
  "stage1_count": "integer（DIGEST only）",
  "stage2_count": "integer（DIGEST only）",
  "verdicts": [
    {
      "news_id": "n003",
      "depth": "shallow | deep",
      "headline": "string",
      "headline_zh": "string",
      "verdict": "BULLISH | BEARISH | BINARY | NEUTRAL",
      "net_impact_score": "float",
      "source_label": "string",
      "news_type": "string",
      "bull_case": "string",
      "bear_case": "string",
      "sector_view": "string — 產業分析師核心論點",
      "macro_view": "string — 財經專家核心論點",
      "arbiter_reasoning": "string",
      "debate_note": "string",
      "binary_risk": "true | false",
      "binary_event_date": "YYYY-MM-DD | null",
      "within_48h": "true | false",
      "cache_updated": "true | false",
      "affected_sectors": [
        { "sector": "string", "direction": "bullish|bearish|binary|neutral" }
      ],
      "tickers_mentioned": ["NVDA", "TSM"]
    }
  ],
  "session_macro_delta": "float"
}
```

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
使用者貼新聞 → News Collector WebFetch
  → Stage 2 Deep Debate（4 agent 完整辯論）
  → Arbiter → Cache Patch → Impact Card
```

FLASH mode **跳過 Stage 1**，因為：
1. 使用者已明確指定新聞 → 不需要篩選
2. 只有 1 則 → 無需漏斗
3. 通常有時效性 → 快速深讀

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
| 看到重大新聞標題 | FLASH | 直接 WebFetch → Deep Debate |
| 開盤前更新市場氣氛 | DIGEST | RSS → Triage → Deep Top 5 |
| 針對個股查近期新聞 | FLASH | 「分析 NVDA 近期動態」→ RSS filter + Deep |
| Dashboard 卡片按鈕觸發 | FLASH | 複製 prompt → 貼回 CLI |
| 盤中突發事件 | FLASH → DIGEST | 先 FLASH 該則 → 後續 DIGEST 補齊上下文 |

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
