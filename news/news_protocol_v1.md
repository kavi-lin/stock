# Breaking News Intelligence Protocol (V1.0)

---

## SESSION STARTUP

```
NEWS TRIGGER
──────────────────────────────────────────
MODE : FLASH | DIGEST
      FLASH  = 單則即時新聞快速分析（< 5 分鐘）
      DIGEST = 掃描近期新聞全面更新 cache
──────────────────────────────────────────
```

> 直接在對話中貼入新聞標題/連結，或說「更新新聞 cache」即可觸發。
> 完成後自動更新相關 cache 檔案，後續 protocol 讀取時即取得最新資訊。

---

## GLOBAL RULES

1. **Debate Required**: 每則新聞必須同時產出 bull 與 bear 兩個解讀，禁止單面結論。
2. **Cache Update**: 分析完成後，自動 patch 以下檔案：
   - `../sector/sector_logs/YYYY-MM-DD_sector_intel.json` — 更新 `top_catalysts` 與 `political_overlay`
   - `../investment/invest_logs/YYYY-MM-DD_phase0.json` — 更新 `binary_risks` 與 `mandatory_risk_flags`
   - `./news_logs/YYYY-MM-DD_digest.json` — append 本次分析
3. **FLASH mode**: 單則新聞，快速辯論，直接輸出影響結論。
4. **DIGEST mode**: 掃描近 48h 新聞，產出完整新聞日誌，全面更新所有 cache。
5. **Output Format**: 邏輯輸出為 JSON，結論輸出 Markdown Impact Card。

---

## TEAM STRUCTURE

| Agent | 職責 |
|---|---|
| News Collector | 搜集新聞原文、確認來源可信度 |
| Bull Analyst | 從多頭角度解讀新聞影響 |
| Bear Analyst | 從空頭角度解讀新聞影響 |
| News Arbiter | 仲裁辯論、輸出最終影響評分與 cache patch |

---

## PHASE 1 — NEWS COLLECTION

**Agent**: News Collector

### FLASH mode
使用者直接提供新聞內容，News Collector 確認來源並補充背景：

```
Web search: "[新聞關鍵詞] site:reuters.com OR site:bloomberg.com OR site:wsj.com"
```

### DIGEST mode
執行完整掃描：

**必須執行的 web search queries**：
- `market-news-analyst` skill（優先）或以下逐條：
  - "breaking market news today"
  - "Trump tariff announcement today"
  - "Fed statement today"
  - "earnings surprise today"
  - "geopolitical event market impact today"
  - "CNN Fear Greed Index today"

```json
{
  "phase": 1,
  "agent": "News_Collector",
  "mode": "FLASH | DIGEST",
  "timestamp": "YYYY-MM-DD HH:MM",
  "news_items": [
    {
      "id": "n001",
      "headline": "string",
      "source": "Reuters | Bloomberg | WSJ | AP | Truth_Social_secondary | other",
      "source_credibility": "HIGH | MEDIUM | LOW",
      "timestamp": "YYYY-MM-DD HH:MM",
      "url": "string or null",
      "raw_summary": "string — 原文重點，不加入任何評價"
    }
  ]
}
```

---

## PHASE 2 — BULL vs BEAR DEBATE

**Agent**: Bull Analyst + Bear Analyst（同時發言，禁止互相妥協）

每則新聞雙方各自獨立分析：

```json
{
  "phase": 2,
  "news_id": "n001",
  "bull_case": {
    "agent": "Bull_Analyst",
    "interpretation": "string — 為何這是利多",
    "primary_beneficiary_sectors": ["sector1", "sector2"],
    "catalyst_type": "demand_increase | cost_reduction | policy_tailwind | sentiment_boost | short_squeeze",
    "impact_score": "1–5",
    "time_horizon": "immediate | short_term | mid_term",
    "confidence": "0.0–1.0",
    "key_assumption": "string — 這個解讀成立的前提"
  },
  "bear_case": {
    "agent": "Bear_Analyst",
    "interpretation": "string — 為何這是利空",
    "primary_at_risk_sectors": ["sector1", "sector2"],
    "risk_type": "demand_destruction | cost_increase | policy_headwind | sentiment_crash | contagion",
    "impact_score": "1–5",
    "time_horizon": "immediate | short_term | mid_term",
    "confidence": "0.0–1.0",
    "key_assumption": "string — 這個解讀成立的前提"
  },
  "debate_note": "string — 雙方最大分歧點"
}
```

**辯論強制規則**：
- `impact_score` 兩方不得同為 1（代表沒有真正辯論）
- 若 `source_credibility = LOW` → 兩方 `confidence` 上限 0.5
- 若新聞含 binary event（財報/FOMC/地緣）→ Bear Analyst 必須標記 `binary_risk: true`

---

## PHASE 3 — ARBITER VERDICT

**Agent**: News Arbiter

仲裁辯論，輸出最終影響評分：

```json
{
  "phase": 3,
  "agent": "News_Arbiter",
  "news_id": "n001",
  "headline": "string",
  "verdict": "BULLISH | BEARISH | BINARY | NEUTRAL",
  "net_impact_score": "-5 to +5",
  "arbiter_reasoning": "string — 為何採納哪方論點",
  "bull_accepted": "full | partial | rejected",
  "bear_accepted": "full | partial | rejected",
  "affected_sectors": [
    {
      "sector": "string",
      "direction": "bullish | bearish",
      "magnitude": "strong | moderate | weak"
    }
  ],
  "macro_backdrop_delta": "float — 建議對現有 macro_backdrop_score 的調整量（-1.0 to +1.0）",
  "binary_risk": {
    "is_binary": "true | false",
    "event_date": "YYYY-MM-DD or null",
    "within_48h": "true | false"
  },
  "cache_action": "UPDATE_SECTOR | UPDATE_PHASE0 | UPDATE_BOTH | NO_UPDATE"
}
```

**仲裁規則**：
- `|bull_impact - bear_impact| < 1` → verdict = BINARY（市場解讀分歧）
- `source_credibility = LOW` AND `net_impact_score > 3` → 降為 2，加 `credibility_warning`
- `binary_risk.within_48h = true` → 強制降低所有相關產業一個 verdict 等級

---

## PHASE 4 — CACHE PATCH

**Agent**: News Arbiter

根據 `cache_action` 執行以下寫入：

### 更新 sector_intel.json
```json
// PATCH: ../sector/sector_logs/YYYY-MM-DD_sector_intel.json
// 在 top_catalysts 陣列 prepend（插入最前）：
{
  "rank": "recalculate",
  "event": "headline",
  "type": "政治 | FOMC | earnings | geopolitical | macro_data",
  "impact_score": "net_impact_score mapped to 1–5",
  "affected_sectors": [],
  "direction": "bullish | bearish | binary",
  "timing": "within_48h | this_week | beyond",
  "source": "news_protocol_flash",
  "updated_at": "YYYY-MM-DD HH:MM"
}
```

### 更新 phase0.json
```json
// PATCH: ../investment/invest_logs/YYYY-MM-DD_phase0.json
// 若 binary_risk = true → append 到 binary_risks 陣列
// 若 net_impact_score 變化 > 1 → 重新計算 macro_backdrop_score
{
  "last_news_update": "YYYY-MM-DD HH:MM",
  "news_patch_count": "integer",
  "macro_backdrop_score": "updated float"
}
```

### 寫入 news_logs
```json
// APPEND: ./news_logs/YYYY-MM-DD_digest.json
{
  "timestamp": "YYYY-MM-DD HH:MM",
  "mode": "FLASH | DIGEST",
  "items_analyzed": "integer",
  "verdicts": [
    {
      "news_id": "n001",
      "headline": "string",
      "verdict": "BULLISH | BEARISH | BINARY | NEUTRAL",
      "net_impact_score": "float",
      "cache_updated": "true | false"
    }
  ],
  "session_macro_delta": "float — 本次所有新聞的合計 macro_backdrop 變動"
}
```

---

## FINAL IMPACT CARD（Markdown 輸出）

```
╔══════════════════════════════════════════════════════════╗
║  NEWS FLASH  │  YYYY-MM-DD HH:MM  │  MODE: FLASH/DIGEST ║
╠══════════════════════════════════════════════════════════╣
║  [BULLISH +3.2]  川普暫停對科技股加徵關稅 90 天             ║
╠══════════════════════════════════════════════════════════╣
║  BULL ✅  科技供應鏈壓力驟降，AI 採購週期重啟               ║
║  BEAR ❌  90 天後不確定性仍在，資本支出可能推遲              ║
║  ARBITER → BULLISH, 採納 BULL 主論點                      ║
╠══════════════════════════════════════════════════════════╣
║  受益產業 ↑  Technology (+strong)  Industrials (+moderate)║
║  受損產業 ↓  None                                         ║
║  Binary Risk  No                                          ║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel.json ✅  phase0.json ✅     ║
╚══════════════════════════════════════════════════════════╝
```

---

## 本地檔案結構

```
news/
├── README.md
├── news_protocol_v1.md              ← 本 instruction
└── news_logs/
    ├── YYYY-MM-DD_digest.json       ← 當日所有新聞分析（累積）
    └── YYYY-MM-DD_HH-MM_flash.json  ← 單則即時快閃（選擇性）
```

---

## 觸發情境速查

| 情境 | 說明 | 建議 MODE |
|---|---|---|
| 看到重大新聞標題 | 直接貼標題給 Claude | FLASH |
| 開盤前想更新市場氣氛 | 說「更新新聞 cache」 | DIGEST |
| 個股分析前想確認最新新聞 | 說「掃描 NVDA 最新新聞」 | FLASH |
| 感覺盤中走勢異常 | 說「掃描近 2 小時重大事件」 | DIGEST |
| 關稅/政策突發消息 | 貼原文或連結 | FLASH → cache_action: UPDATE_BOTH |

---

*End of Breaking News Intelligence Protocol V1.0*
