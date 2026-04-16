# Sector Protocol — 盤前產業分析說明

盤前產業熱度分析 instruction，在個股分析之前執行，判斷今日哪些產業值得進場、哪些應避開。

> **當前版本：V1.2（多檔案架構）** — `sector_protocol_main.md` 為主檔，執行時按需載入子檔案。
> 舊版本 v1 / v1_1 / v1_2 / v1_2_optimized 已歸檔至 `archive/old_protocols/sector/`。

---

## 檔案結構（V1.2 多檔案）

```
sector/
├── sector_protocol_main.md    ← 主檔：GLOBAL RULES / TEAM / 執行時程 / 評分 rubric / 子檔載入索引
├── phase_0.md                 ← Phase 0 細節：三層廣度/FTD/頂部訊號合成 + synthesized_exposure
├── phase_1-2-3.md             ← Phase 1-3 + Extreme Sentiment Playbook
├── phase_4-5.md               ← Phase 4 辯論 / 4c 決策樹 STEP A-G / Phase 5 輸出
└── schema.md                  ← 所有 Phase 0-5 的 JSON schema 定義
```

**載入規則**：
1. 觸發「產業掃描」→ Claude 先讀 `sector_protocol_main.md`
2. 執行 Phase 0 → 讀 `phase_0.md`
3. 執行 Phase 1-3 → 讀 `phase_1-2-3.md`
4. 執行 Phase 4-5 → 讀 `phase_4-5.md`
5. 寫 JSON 時 → 讀 `schema.md` 確認欄位

每 phase 的注意力只在 100–200 行內，避免一次載入 650+ 行的大檔。

---

## 快速開始

```
SESSION CONFIG
──────────────────────────────────────────
RISK_TOLERANCE : MEDIUM
FOCUS_DATE     : [留空 = 今日]
──────────────────────────────────────────
```

---

## 執行流程

```
Phase 0      →  Phase 1         →  Phase 2          →  Phase 3         →  Phase 4          →  Phase 5
市場健康度       產業輪動掃描        主題熱度偵測          新聞催化劑          三輪辯論 + 決策樹    產業裁決
(三層合成)       sector rotation    theme-detector       market-news        Devil's Advocate   HOT/WARM/COLD/AVOID
                                                                           + STEP A-G arbitration
```

---

## Agent 組成

| Agent | 職責 | 資料來源 |
|---|---|---|
| Macro Regime Analyst | 市場健康度、breadth、FTD、頂部合成 | `market-breadth-analyzer` + `ftd_yfinance` + `market_top_yfinance` |
| Sector Rotation Analyst | 產業輪動、週期定位 | `sector-analyst` CSV |
| Theme Intelligence Analyst | 跨產業主題熱度 | `theme-detector` FINVIZ |
| News Catalyst Analyst | 48h 新聞、即將催化劑 | `market-news-analyst` / sector_intel `top_catalysts` |
| Devil's Advocate | 挑戰 HOT 產業共識 | — |
| Tail Risk Assessor | 前 3 HOT 脆弱性評分 | `tail-risk-analyzer` |
| Portfolio Strategist (PS) | 最終產業裁決 | — |

> 所有核心功能不需 API key（使用免費 CSV / FINVIZ / yfinance）

---

## Phase 0 三層訊號合成（V1.2 新增）

| 層 | 訊號 | 來源 |
|---|---|---|
| A | Breadth | `market-breadth-analyzer` → breadth_cache/ |
| C | FTD | `ftd_yfinance.py` → ftd_cache/ |
| D | Market Top | `market_top_yfinance.py` → market_top_cache/ |

最終 `synthesized_exposure` 取三者中點 **最保守上限**；若三訊號分歧 > 30pp 則設 `signal_conflict = true` 觸發 Phase 4c STEP A。

---

## 必要 Skills

| Skill | Phase | API 需求 | 用途 |
|---|---|---|---|
| `market-breadth-analyzer` | Phase 0 層 A | ❌ 免費 | 6 組件 breadth 評分（CSV） |
| `sector-analyst` | Phase 1 | ❌ 免費 | 11 大產業輪動 |
| `theme-detector` | Phase 2 | ❌ 免費 | 跨產業主題熱度 |
| `market-news-analyst` | Phase 3 | ❌ 免費 | 近 10 天市場新聞 |
| `tail-risk-analyzer` | Phase 4b | ❌ 免費 | 產業級脆弱性（上限前 3）|
| `economic-calendar-fetcher` | Phase 3 | ⚠️ FMP API | 未來 7–90 天經濟事件 |

---

## Verdict 定義

| Verdict | Score | 行動建議 |
|---|---|---|
| HOT | 75–100 | 積極尋找個股進場機會 |
| WARM | 50–74 | 選股謹慎，等待更好時機 |
| COLD | 25–49 | 減少暴露，避免新建倉 |
| AVOID | 0–24 | 清倉或嚴格停損 |

### Composite Score 公式（V1.2 動態權重）

```
Score = breadth_momentum × w₁ + theme_heat × w₂ + news_catalyst × w₃ + rotation_signal × w₄

w₁–w₄ 依照 cycle_phase × market_regime × breadth_score × extreme_sentiment 動態調整
（詳見 sector_protocol_main.md 的 Scoring Rubric 章節）
```

### 分數調整機制
- `cycle_phase = Late/Recession` + cyclical 產業 → 分數 × 0.85
- `binary_risk_within_48h` → 分數 × 0.70
- `consensus_warning` + DA 未接受 → `regime_confidence × 0.85`
- `synthesized_exposure < 40%` → 至少 3 個 AVOID
- `EXTREMELY_FRAGILE` tail label → HOT 自動降級為 WARM

---

## Phase 4c Decision Tree（V1.2 新增）

原本散落的仲裁規則改為 STEP A–G 決策樹：

| Step | 條件 | 動作 |
|---|---|---|
| A | `signal_conflict = true` | regime_stance 上限 NEUTRAL |
| B | `synthesized_exposure < 40%` | 至少 3 個 AVOID |
| C | Late / Recession cycle | 週期性產業降級 |
| D | `EXTREMELY_FRAGILE` | HOT → WARM |
| E | `binary_risk_within_48h` | score × 0.70 |
| F | `consensus_warning` + 無 DA 接受 | `regime_confidence × 0.85` |
| G | `signal_conflict` + HOT 存在 | HOT → WARM 保險 |

---

## 本地檔案

```
sector_logs/YYYY-MM-DD_sector_intel.json  ← 當日最終 JSON（bridge.py 讀取）
breadth_cache/market_breadth_*.json       ← Phase 0 層 A 輸入
ftd_cache/ftd_detector_*.json             ← Phase 0 層 C 輸入
market_top_cache/market_top_*.json        ← Phase 0 層 D 輸入
```

`bridge.py` 會從 `sector_intel.json` 讀 `_phase0`（廣度/FTD/頂部合成）、`_phase1`（產業列表）、`_phase3`（binary_risks）三個區塊對應 Dashboard。

---

## 與 Investment Protocol 的銜接

Phase 5 輸出 `session_notes`（一句話 handoff）。`investment_protocol_v4_6` Phase 0 三層 cache 的 L1 會優先讀取 `sector_intel.json` 的 macro_regime / exposure_ceiling / hot_sectors / binary_risks，**跳過 web search**，節省 ~10k token。
