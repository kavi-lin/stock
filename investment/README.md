# Investment Protocol — 個股分析說明

個股完整分析 instruction，使用多 Agent 模擬委員會辯論，輸出 BUY/HOLD/SELL 決策與進出場計畫。

> 當前檔案：`investment_protocol_v4_3.md`

---

## 快速開始

```
SESSION CONFIG
──────────────────────────────────────────
RISK_TOLERANCE : MEDIUM
──────────────────────────────────────────
```

然後在對話中說：「幫我分析 NVDA」

---

## 執行流程

```
Phase 0  →  Phase 1  →  Phase 2  →  Phase 2.5  →  Phase 3        →  Phase 4  →  Phase 5
總體掃描     記憶載入    四大分析師    衝突仲裁       決策引擎           執行規劃     Session 存檔
(可快取)                                       FinalScore 公式
```

### 決策公式

```
FinalScore = Σ(Weight_i × Score_i × Confidence_i) × macro_multiplier
若 market_regime = VOLATILE → FinalScore × 0.85

BUY  ≥ +2.0 / HOLD -2.0~+2.0 / SELL ≤ -2.0
```

---

## Agent 組成

| Agent | 職責 | 預設權重 |
|---|---|---|
| Fundamentals Analyst | P/E, FCF, 營收成長 | 0.30 |
| Sentiment Analyst | Reddit/X, Put/Call, 恐慌指數 | 0.20 |
| News Analyst | 48h 新聞、分析師評級 | 0.20 |
| Technical Analyst | MA, RSI, MACD, 量能 | 0.30 |
| Portfolio Manager (PM) | 決策整合、輸出主控 | — |

---

## 本地檔案

```
invest_logs/
├── history.json                  ← 所有 session exports（Claude 自動 append）
├── YYYY-MM-DD_phase0.json        ← 當日 Phase 0 macro cache（Claude 自動讀寫）
└── YYYY-MM-DD_TICKER.md          ← 個股 session log（選擇性保留）
```

**自動化行為**：
- **Phase 0 三層 cache**（優先順序）：
  1. `../sector/sector_logs/YYYY-MM-DD_sector_intel.json` → 最優先，sector_protocol 跑過後直接用
  2. `./invest_logs/YYYY-MM-DD_phase0.json` → 備用 cache
  3. 都沒有 → 執行 web search（優先用 `market-news-analyst` skill）
- Prior context：自動讀 `history.json` 最新一筆
- Phase 5：自動 append session export 到 `history.json`

---

## 版本紀錄

### V4.1
- 建立完整 8 Agent 架構（Phase 0–6）
- JSON-first 輸出原則
- Phase 2.5 衝突仲裁（T1/T2/T3）
- Phase 6 連續學習 + 權重自動調整

### V4.3（當前）
- **Phase 0 三層 cache 優先順序**：sector_intel.json → phase0.json → web search，sector_protocol 跑過後完全省掉 Phase 0 web search（~10k token）
- **Phase 2 Skills 整合**：Fundamentals 用 `us-stock-analysis`、News 用 `market-news-analyst` 或 sector cache、Technical 支援 `technical-analyst` skill
- **Sentiment fear/greed 從 sector cache 讀取**，不再需要額外 web search

### V4.2
- 移除 COMPACT mode — 永遠輸出完整 JSON
- SESSION CONFIG 精簡為 1 欄位（`RISK_TOLERANCE`），ticker 在對話中指定
- Phase 0 cache / history.json 改為 Claude 直接讀寫本地檔案
- 新增 `binary_risks` 到 Phase 0 + Binary Risk Rule 到 Phase 4
- 新增 VOLATILE regime adjustment（FinalScore × 0.85）
- Phase 5 `trade_metadata` 新增 `trade_type` 和 `event_tag`

---

## 風控規則速查

| 規則 | 條件 | 結果 |
|---|---|---|
| Binary Risk | 事件 < 48h | 強制 REJECTED |
| Binary Risk | 事件存在 | 減倉 30–50% |
| VOLATILE penalty | market_regime = VOLATILE | FinalScore × 0.85 |
| Macro cap | macro_backdrop_score < -3 | position_size ≤ 3% |
| Auto REJECT | risk_reward_ratio < 2.0 | REJECTED |
| Auto REJECT | final_decision = HOLD | REJECTED |

---

## Weight 限制

單一 agent 0.10–0.50，每次調整 ±0.05 以內，四個總和必須 = 1.0
