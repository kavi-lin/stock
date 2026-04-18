# Investment Protocol — 個股分析說明

個股完整分析 instruction，使用多 Agent 模擬委員會辯論，輸出 BUY/STAGED_ENTRY/HOLD/SELL 決策與雙軌進場計畫。

> 當前檔案：`investment_protocol_v4_8.md`

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
Phase 0 → Phase 1 → Phase 2 FAN-OUT → Phase 2.5 → Phase 2.8 → Phase 3 → Phase 4 → Phase 5
總體掃描   記憶載入   4 平行 subagent    衝突仲裁    Red Team     決策引擎   雙軌執行   Session 存檔
(可快取)            + Burry inline    (含 T4)    (subagent)  raw→RT→macro (Agg+Cons)
```

### V4.8 Phase 2 執行模式（Parallel Blind Analyst Fan-Out）

- Fundamentals / Sentiment / News / Technical 四個 analyst **必須以 4 個 Agent subagent 平行執行**（同一訊息發出 4 個 tool call）。
- 每個 subagent 僅收到：ticker、Phase 0 macro、該 lane 的 rubric + 必跑 skill 指令。
- 禁止傳入：其他 analyst 輸出、historical_bias、active_weights。
- 每個輸出必須含 `subagent_isolated: true` sentinel，PM 驗證後才進入 Phase 2.5。
- Burry 仍是 inline skill call（deterministic output 不受 anchoring 影響）。
- Fallback：單一 subagent 失敗 → retry 1 次 → inline fallback（confidence cap 0.6）；4 全失敗 → `FULL_FALLBACK` + 強制 STRONG_COUNTER + 禁止 BUY/STAGED_ENTRY。

### 決策公式（V4.8 沿用 V4.7）

```
Step 1: raw_total = Σ(Weight_i × Score_i × Confidence_i)
Step 2 (Red-Team-gated):
  4 agent 同向 + Burry 未 veto + red_team_verdict = NO_VIABLE_COUNTER → × 1.15 (bonus)
  red_team_verdict = STRONG_COUNTER                                    → × 0.85 (penalty)
  其他                                                                  → 不變
Step 3: 若 sign(raw) == sign(macro_backdrop) → × macro_multiplier (ALIGNED)
        否則 → 保留原值 (CONTRARIAN flag)

VOLATILE regime 不在 Phase 3 重複懲罰（已在 macro_backdrop_score 內）
```

### 決策閾值

| final_score | decision | 倉位 |
|---|---|---|
| ≥ +1.2 | BUY | 100% standard |
| +0.8 ~ +1.2 | **STAGED_ENTRY** | 50%（雙軌分批）|
| −0.8 ~ +0.8 | HOLD | 0 |
| −1.2 ~ −0.8 | **STAGED_EXIT** | 漸出 |
| ≤ −1.2 | SELL | 100% |

HOLD 不再強制 Auto-REJECT，交由 Phase 4 依 Fundamentals score 決定是否啟動 STAGED_ENTRY。

---

## 雙軌進場（Dual-Track Entry）

每個 BUY / STAGED_ENTRY 決策都輸出兩組 entry range：

| Track | 對應情境 | Trigger |
|---|---|---|
| **Aggressive** | 「若漲勢持續」 | 立即 / 當前震盪區 / 日收破前高 |
| **Conservative** | 「若等回檔/確認」 | 陽包陰 + 量 > 1.2x / 財報後 / RSI > 50 / 站上關鍵均線 |

- **BUY**: 使用者二選一（預設 aggressive）
- **STAGED_ENTRY**: aggressive 50% 先進，conservative 50% 等條件

目的：解決「0414 分析 CANCEL 但股價繼續漲」那類誤殺情境 — 即使委員會對時點無共識，也提供保守進場的價格區間。

---

## Agent 組成

| Agent | 職責 | 預設權重 | 執行模式 | Skill |
|---|---|---|---|---|
| Fundamentals Analyst | P/E, FCF, 營收成長 | 0.30 | **parallel subagent** | `us-stock-analysis` |
| Sentiment Analyst | Reddit/X, Put/Call, VIX | 0.20 | **parallel subagent** | `market-sentiment-analyzer` |
| News Analyst | 48h 新聞、分析師評級 | 0.20 | **parallel subagent** | `market-news-analyst` |
| Technical Analyst | MA, RSI, MACD, 量能 | 0.30 | **parallel subagent** | `technical-analyst` |
| **Contrarian (Burry)** | **估值錨 + veto check** | **獨立，不加權** | inline skill | **`short-contrarian-analyst`** |
| **Red Team (V4.7)** | **Phase 2.8 獨立反駁 + kill conditions** | **獨立，不加權** | subagent | general-purpose |
| Risk Manager | 倉位 + 尾部風險 | — | inline | `portfolio-risk-manager`, `tail-risk-analyzer` |
| Portfolio Manager (PM) | orchestrator — 決策整合、輸出主控 | — | inline | — |

Contrarian Analyst 不納入 FinalScore 加權，只透過 Phase 2.5 T4 觸發 veto。

---

## Skills 對照（V4.8）

| Skill | 執行點 | 作用 |
|---|---|---|
| `short-contrarian-analyst` | Phase 2（第五 Agent）| Burry Score 估值錨，觸發 T4 veto |
| `market-sentiment-analyzer` | Phase 2 Sentiment fallback | 取代 web search，提供 VIX + composite score |
| `portfolio-risk-manager` | Phase 4 Step 2 | Vol-adjusted 倉位上限 + correlation multiplier |
| `tail-risk-analyzer` | Phase 4 Step 3 | 個股脆弱性評分，自動調整倉位 |
| `us-stock-analysis` | Phase 2 Fundamentals | 財報 / 估值 |
| `market-news-analyst` | Phase 0 / Phase 2 News | 總體 + 個股新聞 |
| `technical-analyst` | Phase 2 Technical（若有週線圖）| 技術面分析 |

---

## Burry Score 解讀（Phase 2 Contrarian）

| Score | Signal | 含義 |
|---|---|---|
| ≥ 7 | STRONGLY BULLISH | 深度價值，逆向買入高確信度 |
| 5–6 | BULLISH | 估值合理偏低，值得關注 |
| 3–4 | NEUTRAL | 無明顯優勢或劣勢 |
| ≤ 2 | BEARISH | **觸發 veto_flag → Phase 2.5 T4** |

**Score 組成**（總分 12）：
- `value_pts` 0–6（FCF yield、EV/EBIT）
- `balance_pts` 0–3（debt/equity、net cash）
- `insider_pts` 0–2（內部人活動）
- `contrarian_pts` 0–1（逆向情緒：負面新聞 = 機會，正面新聞 = 擁擠警告）

### T4 仲裁規則（V4.7 強化）
- `burry_score = 0–1`（極端高估）→ 強烈建議 `CANCEL`
- `burry_score = 2`（高估）→ `DOWNGRADE_DECISION`（BUY → HOLD）或 `OVERRIDE_BURRY`
- **`OVERRIDE_BURRY` 自動啟動三項成本（V4.7）**：
  1. Phase 4 倉位 × 0.5
  2. 必填 `override_justification`（≥ 20 字具體凌駕理由，不可泛泛而談）
  3. `override_recheck_date` = 交易日 + 5 個交易日，到期強制複審

---

## Phase 4 倉位計算參考

> 實際閾值由 `portfolio-risk-manager` / `tail-risk-analyzer` skill 維護，此處僅供查閱。

### 波動率倉位上限（portfolio-risk-manager）

| 年化波動率 | 基礎倉位上限 |
|---|---|
| > 50% | 5% |
| > 30% | 10% |
| > 中位數 | 15% |
| ≤ 中位數 | 25% |

### 相關性調整

| 與現有持倉相關性 | 倍數 |
|---|---|
| > 0.7（高相關）| × 0.7 |
| 0.4–0.7（中等）| × 0.9 |
| < 0.4（低相關）| × 1.1 |

### 尾部風險調整（tail-risk-analyzer）

| Fragility Label | 倉位倍數 |
|---|---|
| EXTREMELY FRAGILE | × 0.5 |
| FRAGILE | × 0.75 |
| RESILIENT | × 1.0 |
| ANTIFRAGILE | × 1.1（僅 PM 高確信度）|

### 最終倉位計算順序
```
base = vol_adjusted_limit（若 Step 2 執行）或 0.05
→ × fragility_multiplier
→ macro_backdrop_score < -3 時 cap 至 0.03
→ binary_risk present 時 × 0.5–0.7
→ final_position_size
```

---

## 風控規則速查（V4.8）

| 規則 | 條件 | 結果 |
|---|---|---|
| Binary — unknown/negative < 48h | FOMC/地緣/壞消息 | 強制 REJECTED |
| Binary — unknown/negative 存在 | 事件距今 > 48h | 減倉 30–50% |
| Binary — positive | earnings 歷史 beat ≥ 70% | 不減倉 |
| Macro cap | macro_backdrop_score < −3 | position ≤ 3% |
| Auto REJECT | risk_reward_ratio < 2.0 | REJECTED |
| T4 Veto | burry_score ≤ 2 AND BUY | CANCEL / DOWNGRADE / OVERRIDE |
| **Burry OVERRIDE 成本（V4.7）** | T4 resolution = OVERRIDE_BURRY | 倉位 × 0.5 + 必填 justification + 5d 複審 |
| **Consensus Bonus（V4.7 Red-Team-gated）** | 4 agent 同向 + Burry 不 veto + Red Team NO_VIABLE_COUNTER | raw × 1.15 |
| **Red Team Penalty（V4.7）** | red_team_verdict = STRONG_COUNTER | raw × 0.85，bonus 禁用 |
| **FULL_FALLBACK 保護（V4.8）** | phase2_fanout_mode = FULL_FALLBACK AND BUY/STAGED_ENTRY | 強制降為 HOLD（degraded 下不信任看多共識）|
| Directional Macro | sign(raw) 與 sign(macro) 不同 | 不乘 multiplier（contrarian 保留）|

> V4.5 的 `HOLD → 強制 REJECTED` 與 `VOLATILE × 0.85` 雙重懲罰已移除。

---

## Weight 限制（Phase 6 Continuous Learning）

- 單一 agent 權重範圍：0.10–0.50
- 每次調整幅度：±0.05 以內
- 四個 agent 總和必須 = 1.0
- Contrarian 不在加權範圍內

---

## 本地檔案

```
invest_logs/
├── history.json                  ← 所有 session exports（自動 append）
├── YYYY-MM-DD_phase0.json        ← 當日 Phase 0 macro cache
└── YYYY-MM-DD_TICKER.md          ← 個股 session log（選擇性保留）

reports/
└── YYYYMMDD_TICKER.md            ← 最終 MD 報告（Phase 5 強制產出）
```

**自動化行為**：
- **Phase 0 三層 cache**（優先順序）：
  1. `../sector/sector_logs/YYYY-MM-DD_sector_intel.json` ← 最優先，sector_protocol 跑過後直接用
  2. `./invest_logs/YYYY-MM-DD_phase0.json` ← 備用 cache
  3. 都沒有 → 執行 web search（優先用 `market-news-analyst` skill）
- Prior context：自動讀 `history.json` 最新一筆
- Phase 5：自動 append session export 到 `history.json`，並強制產出 `../reports/YYYYMMDD_TICKER.md`

---

## 版本紀錄

### V4.8（當前 — parallel blind analyst subagents）

**動機**：V4.7 解決了 consensus bonus 被同一 model 放大的問題，但 Phase 2 四個 analyst 仍由同一 model 序列產生，context 共享 → 偽獨立的結構性根因仍在。V4.8 把 4 個 analyst 改為平行 subagent，真正以獨立 context 產生訊號。

**一項修訂（D patch）**：
- **V4.8-D** Phase 2 四個 analyst（Fundamentals / Sentiment / News / Technical）改為 **4 個 Agent subagent 平行呼叫**（同一訊息內的 4 個 tool_use block）；Burry 保留 inline（skill 已 deterministic）
- **+ Isolation contract**：每個 subagent 禁看其他 analyst 輸出、PM historical_bias、active_weights
- **+ Sentinel 驗證**：`subagent_isolated: true` 必填，PM 驗證後才進 Phase 2.5
- **+ Fallback 階梯**：單一失敗 retry → inline（cap 0.6）；2-3 失敗 → PARTIAL_FALLBACK；全失敗 → FULL_FALLBACK + 強制 STRONG_COUNTER + 禁 BUY/STAGED_ENTRY
- **+ Phase 5 Schema**：`session_export_version` 升至 `V4.8`，新增 `phase2_fanout_summary` + `phase2_fanout_mode` + `degraded_analysts`
- **+ Phase 5 Step 3 成本優化（2026-04-18）**：MD 報告撰寫委派 Sonnet 4.6 subagent（純格式化，禁改任何決策數值），每次分析節省約 $0.4-0.7。fallback：subagent 偏離 constraints 或失敗 → PM inline 寫

### V4.7（anti-self-deception patch）

**動機**：V4.6 架構下四個 analyst 由同一 model 連續產生，context 共享造成「偽獨立共識」；`consensus_bonus × 1.15` 因此變成偏誤放大器而非確信度加權。Burry 作為唯一真正異議訊號可被 PM 一段話無成本 override。Devil's Advocate 由 News agent 自己寫、不 gate 任何決策。

**三項修訂（ABC patch）**：
- **V4.7-A** Consensus Bonus 改為 **Red-Team-gated**：只有 Red Team `NO_VIABLE_COUNTER` 才觸發 ×1.15；新增 `STRONG_COUNTER` 時 ×0.85 penalty
- **V4.7-B** 新增 **Phase 2.8 Red Team Adversary**：必須以 Agent tool 呼叫 subagent（切斷 context 錨定），強制產出 falsifiable `kill_conditions`
- **V4.7-C** T4 **OVERRIDE_BURRY 強制成本化**：倉位 × 0.5、必填 ≥ 20 字 `override_justification`、自動排定 `override_recheck_date`（+5 交易日強制複審）
- **+ Phase 5 Schema**：`session_export_version` 升至 `V4.7`，新增 `red_team_verdict` / `red_team_kill_conditions` / `burry_override_active` / `burry_override_recheck_date`

### V4.6（anti-conservatism 修訂）

**動機**：V4.5 在 2026-04-14 MSFT 回測中誤殺 — 四個 agent 全部正分（raw +1.06）卻因雙重乘數（macro 0.75 × VOLATILE 0.85 = 0.64）被砍到 0.676 → HOLD → Auto-REJECT → CANCEL，隔日股價仍上漲 2.6%。

**四項修訂**：
- **V4.6-1** 移除 Phase 3 `VOLATILE × 0.85` — VOLATILE 已計入 `macro_backdrop_score`，重複扣分
- **V4.6-2** BUY 門檻 2.0 → **1.2**；新增 `STAGED_ENTRY`（0.8–1.2）與 `STAGED_EXIT`（−1.2 ~ −0.8）狀態；HOLD 不再強制 Auto-REJECT
- **V4.6-3** `macro_multiplier` 改為**同向才縮放**（`sign(raw) == sign(macro)`）；逆向 signal 保留原值並加 `CONTRARIAN` flag
- **V4.6-4** 新增 **consensus bonus × 1.15**（4 agent 同向且 Burry 不 veto 時觸發）
- **+ Dual-Track Entry**：Phase 4 trade_plan 改為輸出 `entry_aggressive` + `entry_conservative` 兩組 range
- **+ Binary 分類**：`positive` / `unknown` / `negative`，只對 unknown/negative 且 48h 內減倉
- **+ Protocol 明寫** Phase 2 評分不為 Burry 預留讓分空間，避免自我審查

### V4.5
- Phase 2 新增第五 Agent **Contrarian Analyst (Burry)**，使用 `short-contrarian-analyst` skill
- Phase 2 Sentiment Agent 新增 `market-sentiment-analyzer` skill 作為 fallback
- Phase 2.5 新增 **T4** 觸發條件（`burry_score ≤ 2` AND `BUY`）
- Phase 4 Risk Audit 新增 vol-adjusted position sizing（`portfolio-risk-manager`）
- Phase 4 Risk Audit 新增尾部風險評估（`tail-risk-analyzer`）
- Final Visualization Table 新增 Contrarian 列

### V4.3
- Phase 0 三層 cache 優先順序：sector_intel.json → phase0.json → web search
- Phase 2 Skills 整合：`us-stock-analysis` / `market-news-analyst` / `technical-analyst`
- Sentiment fear/greed 從 sector cache 讀取

### V4.2
- 移除 COMPACT mode，永遠輸出完整 JSON
- SESSION CONFIG 精簡為 1 欄位（`RISK_TOLERANCE`）
- Phase 0 cache / history.json 改為直接讀寫本地檔案
- 新增 `binary_risks` + Binary Risk Rule
- 新增 VOLATILE regime adjustment

### V4.1
- 建立完整 8 Agent 架構（Phase 0–6）
- JSON-first 輸出原則
- Phase 2.5 衝突仲裁（T1/T2/T3）
- Phase 6 連續學習 + 權重自動調整
