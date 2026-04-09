# Sector Protocol — 盤前產業分析說明

盤前產業熱度分析 instruction，在個股分析之前執行，判斷今日哪些產業值得進場、哪些應避開。

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
Phase 0      →  Phase 1         →  Phase 2          →  Phase 3         →  Phase 4       →  Phase 5
市場健康度       產業輪動掃描        主題熱度偵測          新聞催化劑分析       三輪辯論          產業裁決
(可快取)        sector-analyst     theme-detector       market-news       Debate → PS      HOT/WARM/COLD/AVOID
```

---

## Agent 組成

| Agent | 職責 | 資料來源 |
|---|---|---|
| Macro Regime Analyst | 市場健康度、breadth | `uptrend-analyzer` CSV（免費）|
| Sector Rotation Analyst | 產業輪動、週期定位 | `sector-analyst` CSV（免費）|
| Theme Intelligence Analyst | 跨產業主題熱度 | `theme-detector` FINVIZ（免費）|
| News Catalyst Analyst | 48h 新聞、即將催化劑 | `market-news-analyst` WebSearch |
| Devil's Advocate | 挑戰多頭共識 | — |
| Portfolio Strategist (PS) | 最終產業裁決 | — |

> 所有核心功能不需要 API key（使用免費 GitHub CSV 和 FINVIZ 公開資料）

---

## 必要 Skills 清單

| Skill | 用於 Phase | API 需求 | 資料來源 | 說明 |
|---|---|---|---|---|
| `uptrend-analyzer` | Phase 0 | ❌ 免費 | GitHub CSV（TraderMonty）| ~2,800 股上升趨勢比率，5 組件 breadth 評分 |
| `market-breadth-analyzer` | Phase 0 | ❌ 免費 | GitHub CSV（TraderMonty）| 6 組件 breadth 健康評分（0–100）|
| `sector-analyst` | Phase 1 | ❌ 免費 | GitHub CSV | 11 大產業輪動分析、週期定位、cyclical/defensive 比率 |
| `theme-detector` | Phase 2 | ❌ 免費 | FINVIZ 公開 + yfinance | 跨產業主題熱度、生命週期階段（Emerging → Exhausting）|
| `market-news-analyst` | Phase 3 | ❌ 免費 | WebSearch/WebFetch | 近 10 天市場新聞、Impact 評分排行 |
| `economic-calendar-fetcher` | Phase 3 | ⚠️ FMP API | Financial Modeling Prep | 未來 7–90 天重大經濟事件（FOMC、NFP、CPI 等）|

### API 說明

- **FMP API（`economic-calendar-fetcher`）**：免費帳號 250 calls/day，對每日一次盤前分析完全夠用
- 若不想申請 FMP API：可改用 web search 搜尋「upcoming FOMC date」，但每次多消耗約 3–5k token
- 其他 skills 完全不需要 API，直接調用

### 如何取得 Skills

這些 skills 來自獨立的 Market Analysis skill 專案。確保 cowork 設定中已載入對應的 skill 目錄，Claude 才能調用其 CSV 資料和腳本。

---

## Verdict 定義

| Verdict | Score | 行動建議 |
|---|---|---|
| HOT | 75–100 | 積極尋找個股進場機會 |
| WARM | 50–74 | 選股謹慎，等待更好時機 |
| COLD | 25–49 | 減少暴露，避免新建倉 |
| AVOID | 0–24 | 清倉或嚴格停損 |

### Composite Score 公式

```
Score = breadth_momentum(25) + theme_heat(25) + news_catalyst(25) + rotation_signal(25)
若 cycle_phase = Late/Recession + Cyclical 產業 → Score × 0.85
若 binary_risk_within_48h → Score × 0.70
```

---

## Phase 4 三輪辯論流程

1. **各 analyst 提案** — 每人提 top conviction HOT / COLD 產業
2. **Devil's Advocate** — 挑戰共識，所有 agent 看多同一板塊時必須提反論
3. **PS 仲裁** — 整合辯論結果，輸出最終 verdict

---

## 本地檔案

```
sector_logs/
├── YYYY-MM-DD_sector_intel.json   ← 當日產業分析 cache（Claude 自動讀寫）
└── sector_history.json            ← 歷史 verdict 紀錄
```

**Cache 行為**：
- 存在且日期符合 → 跳過 Phase 0–2，從 Phase 3 開始
- 不存在 → 完整執行並寫入 cache

---

## 與 Investment Protocol 的銜接

Phase 5 輸出 `session_notes`（一句話 handoff），例如：
> 「市場 RISK_ON，科技與工業強旺，能源受關稅壓力應避開。」

這句話可作為 investment_protocol Phase 0 的 macro context 補充。

---

## 版本紀錄

### V1.0（當前）
- 建立盤前產業分析框架（Phase 0–5）
- 六大 Agent 架構含 Devil's Advocate 辯論
- 4 組件 Composite Score（breadth / theme / news / rotation）
- Binary Risk 和 Cycle Phase 降分機制
- 全部核心功能不需 API key
- Cache 機制（`sector_logs/YYYY-MM-DD_sector_intel.json`）
- 輸出 HOT/WARM/COLD/AVOID verdict + handoff 給 investment_protocol
