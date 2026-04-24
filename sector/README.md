# Sector Protocol — 盤前產業分析說明

盤前產業熱度分析 instruction，在個股分析之前執行，判斷今日哪些產業值得進場、哪些應避開。

> **當前版本：V1.4（Phase 5 機械化）** · 內部 wire `protocol_version="V1.3"`（schema/validator）
> `sector_protocol_main.md` 為主檔，執行時按需載入子檔案。
> 舊版本 v1 / v1_1 / v1_2 / v1_2_optimized 已歸檔至 `archive/old_protocols/sector/`。

> **檔案分工**：`*_protocol_*.md` / `phase_*.md` / `schema.md` 只放 LLM 執行
> 規則（緊湊、可機械讀）。設計理由、計算範例、changelog、背景敘述都在
> 此 README — LLM 不會載入。

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

### 計算範例 1 — 三訊號一致看多

```
Breadth:     "70-85%" → midpoint 77.5
FTD:         "65-80%" → midpoint 72.5
Market Top:  "60-80%" → midpoint 70

min = 70, max = 77.5, diff = 7.5pp < 30pp
→ signal_conflict = false
→ synthesized_exposure = "60-80%"（Market Top 原始值）
→ 三訊號一致，可採納 FTD/Breadth 進取範圍
```

### 計算範例 2 — 訊號衝突

```
Breadth:     "70-90%" → midpoint 80
FTD:         "20-35%" → midpoint 27.5
Market Top:  "55-75%" → midpoint 65

min = 27.5, max = 80, diff = 52.5pp > 30pp
→ signal_conflict = true ⚠️
→ synthesized_exposure = "20-35%"（FTD 原始值）
→ Phase 4c 最終 regime_stance 改為 NEUTRAL 或 DEFENSIVE
```

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

Phase 5 輸出 `session_notes`（一句話 handoff）。`investment_protocol_v4_8` Phase 0 三層 cache 的 L1 會優先讀取 `sector_intel.json` 的 macro_regime / exposure_ceiling / hot_sectors / binary_risks，**跳過 web search**，節省 ~10k token。

---

## 市場範圍 & 框架標注

- **[domain:us-equity]**：Phase 0 廣度（SPX）、FTD（S&P+NDX）、市場頂部（US distribution days）、F&G（CNN）、VIX — 全為美股資料源
- **[domain:us-equity]**：Phase 1 迭代 11 個 GICS 產業 + US sector ETFs（finvizfinance + yfinance）
- **[framework]**：Phase 4a 三 agent 平行辯論 + Phase 4b Devil's Advocate adversary + Phase 5 validator gate — 邏輯可通用
- 詳見 `skills/MARKET_INDEX.md` 完整分類

---

## 設計理由

### Phase 4a — 平行 Subagent Fan-Out
三個提案 agent 看三種不同資料來源（Sector Rotation 看 Phase 1 CSV、Theme Intelligence 看 Phase 2 主題、News Catalyst 看 Phase 3 新聞），本質上彼此獨立。V1.3 改為 3 個平行 Agent subagent，消除同 model 序列產生 3 份提案的 anchoring 風險——若在同一 context 序列執行，第二、三個 agent 會隱性受第一個影響。

### Phase 4b — Devil's Advocate 獨立 Subagent
DA 的工作是挑戰 Phase 4a 共識。若 DA 在同一 model context 中看過三 agent 提案再登場，會有「我已經論證 HOT 三個板塊，現在硬擠反論」的 anchoring effect。V1.3 改為獨立 Agent subagent，只收 Phase 0-4a 輸出 + tail-risk 腳本結果，看不到自己的前文，才能真反駁。

### Phase 5 — 機械化（V1.4）
原本 Phase 5 由 PS（Opus）寫 27KB JSON + 4.5KB markdown + 最終 summary，
拆解 2026-04-24 一次跑（`sector/scan_logs/sector_20260424_210620.log`）顯示
Phase 5 純模型輸出佔 663s + 225s = ~15 分鐘 / 26 分總時長。內容與
`_phase4c.today_verdict` 完全重疊。

V1.4 改為 PS 把所有文字（headline / one_liner / key_takeaways /
sector_actions / watch_next）一次寫進 JSON，Markdown 改由
`scripts/render_sector_report.py` 純 Python 渲染，沒有第二輪模型生成。
預估每次跑省下 12-15 分鐘。

### 文檔分工
- **Protocol files (`*_protocol_*.md`, `phase_*.md`, `schema.md`)**：只給 LLM
  讀的執行規則。緊湊、機械、可驗證。沒有歷史沿革、沒有設計理由、沒有
  「為什麼這樣寫」的敘述。
- **README.md（這份）**：人類視角。背景、設計理由、計算範例、changelog、
  與其他 protocol 的銜接、debug 提示。LLM 在 `產業掃描` 流程中**不會**載入。

兩邊維護同一個事實時，protocol 是 source of truth，README 註明「詳見
phase_X.md」即可，避免重複漂移。

### Step 1 vs Step 6（為什麼取代而不疊加）
- Step 1 cycle_phase 乘數是 LLM 從 breadth signal 字串推斷的 heuristic
- Step 6 FRED `regime_label` 是 5-6 個官方 series 共識，更可信
- 兩者都在編碼「週期位置」 → 疊加會雙重扣分
- 規則：`fred_available=true` SKIP Step 1；`false` 則 Step 1 自動恢復

### Step 6 confidence gating
公式 `effective = 1.0 + (raw - 1.0) × regime_confidence`：
- `regime_confidence ≈ 1.0` → effective = raw（規則完全套用）
- `regime_confidence ≈ 0.5` → effective 趨向 1.0 一半（規則弱化）
- `regime_confidence < 0.40` → effective ≈ 1.0（FRED 訊號太弱不干預）

### STEP G.5 macro/theme 衝突的歷史證據
1999 dotcom + 2021 SPAC 兩次大頂的核心 thesis 都是「主題火熱抵銷宏觀逆風」。
Theme heat + macro warning 在歷史上是泡沫頂特徵，不是利多 — 主題不可
蓋過 FRED 結構性訊號。所以衝突時 cap WARM，不允許主題把 sector 推到 HOT。

### Phase 3 web fetch 預算的由來
舊流程（4-25 run 前）由 LLM 自由 WebSearch，實測一次跑了 19 個查詢、
~200 秒，半數重複（FOMC date 2 次、earnings calendar 2 次）+ 半數 sector
無關（Russia/Ukraine、FDA PDUFA、bank earnings dates、copper price）。
新規則強制 4 個 structured tools 先（calendar / sentiment / FRED reuse）
然後 WebSearch HARD CAP ≤ 5 narrative。預算從 200s 砍到 80s。

### Phase 4c Step 6 為何用 script
LLM 心算 11 個 sector × multi-step multiplier ≈ 60-90 秒推理時間 +
容易算錯（過去多次發現 LLM 忘了 confidence gating）。`step6_overlay.py`
< 1 秒出 deterministic JSON，paste 即用，省 ~1 分鐘 + 消除算錯風險。

### Theme detector 為何不能加 timeout
FINVIZ scrape 自然耗時 140-180s。LLM 第一次跑容易包 `timeout 150` 求
保險 → 145s 時被殺 → retry 再跑 145s → 浪費整整 145 秒（4-25 run 觀察到）。
Script 自管 1hr cache，不需要 LLM 額外保護機制。

---

## Changelog

### V1.3 → V1.4（Phase 5 機械化 + Protocol 瘦身）
- Phase 5：新增 `scripts/render_sector_report.py`，從 `_sector_intel.json` 直接渲染 markdown 報告（7 段，零 LLM）
- Phase 5：PS 不再撰寫 markdown；`_phase4c.today_verdict` 全欄位變成 renderer 的唯一文字來源
- Protocol 檔案瘦身：刪除人類向敘述、計算範例、歷史沿革，集中到此 README（protocol 檔總行數 702 → 641）
- `protocol_version` wire 仍為 `"V1.3"`（schema/validator 不變）

### V1.2 → V1.3（Subagent Fan-Out + Validator）
- Phase 4a：三 agent 提案改為 3 個平行 Agent subagent，isolation contract + `subagent_isolated` sentinel 消除 anchoring 風險
- Phase 4b：Devil's Advocate 改為獨立 subagent，`risk_scenario` 要求 falsifiable 格式
- Phase 5：新增 `validate_sector_intel.py` 為 MANDATORY gate，rc=0 才算完成；schema 加 `phase4_fanout_mode` / `degraded_agents`
- `protocol_version` 升至 `"V1.3"`

### V1.1 → V1.2
- Phase 0: 新增層 C（FTD）、層 D（Market Top），三訊號合成規則輸出 `synthesized_exposure`
- Phase 0: schema 補齊 `ftd`、`market_top`、`synthesized_exposure`、`signal_conflict`
- Phase 3: `named_targets` → `named_targets_today`；移除無效 `SECTOR_CACHE`
- Phase 4b: tail-risk 效率上限（HOT > 3 → 僅跑前 3）
- Phase 4c: 仲裁改用 `synthesized_exposure`（原 `exposure_ceiling`）
- Final Verdict Table footer 新增 `synthesized_exposure`

### V1.2 → V1.2 Optimized（已整合）
- Phase 0: 三訊號合成計算範例（2 個 case）
- Phase 3: Extreme Sentiment Playbook（Greed / Fear 分案處理）
- Phase 4b: `consensus_warning` 精確三條件定義
- Phase 4c: 決策樹改寫；新增 `decision_tree_path`、`regime_confidence` 欄位
- Scoring: 動態權重自適應（cycle_phase × regime × breadth × sentiment）
