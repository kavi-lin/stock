# Pre-Market Sector Intelligence Protocol (V1.3)

<!-- [scope] US equity sector rotation. GICS + US sector ETFs + TraderMonty breadth.
     Phase 4a/4b debate patterns are [framework]; data inputs are [domain:us-equity].
     See skills/MARKET_INDEX.md. -->

> **多檔案架構**：此主檔案約 200 行，詳細細節分拆於子檔案，按需載入以節省 context。

> **Changelog V1.2 → V1.3（Subagent Fan-Out + Validator）**
> - Phase 4a：三 agent 提案（Sector Rotation / Theme Intelligence / News Catalyst）改為 **3 個平行 Agent subagent**，isolation contract + `subagent_isolated` sentinel 消除同 model 序列 anchoring 風險（與 investment V4.8 / news V2.1 同邏輯）
> - Phase 4b：Devil's Advocate 改為獨立 subagent，收 Phase 0-4a 輸出後反駁，`risk_scenario` 要求 falsifiable 格式
> - Phase 5：新增 `validate_sector_intel.py` 為 MANDATORY gate，rc=0 才算完成；schema 加 `phase4_fanout_mode` / `degraded_agents` 頂層欄位
> - `protocol_version` 升至 `"V1.3"`

> **Changelog V1.1 → V1.2**
> - Phase 0: 新增層 C（FTD）、層 D（Market Top），三訊號合成規則輸出 `synthesized_exposure`
> - Phase 0: schema 補齊 `ftd`、`market_top`、`synthesized_exposure`、`signal_conflict`
> - Phase 3: `named_targets` → `named_targets_today`；移除無效 `SECTOR_CACHE`
> - Phase 4b: tail-risk 效率上限（HOT > 3 → 僅跑前 3）
> - Phase 4c: 仲裁改用 `synthesized_exposure`（原 `exposure_ceiling`）
> - Final Verdict Table footer 新增 `synthesized_exposure`

> **Changelog V1.2 → V1.2（Optimized，已整合）**
> - Phase 0: 三訊號合成計算範例（2 個 case）
> - 全局: Execution Timeline & Parallelization
> - Phase 3: Extreme Sentiment Playbook（Greed / Fear 分案處理）
> - Phase 4b: `consensus_warning` 精確三條件定義
> - Phase 4c: 決策樹改寫（代替 prose 規則）；新增 `decision_tree_path`、`regime_confidence` 欄位
> - Scoring: 動態權重自適應（cycle_phase × regime × breadth × sentiment）

---

## 子檔案索引（按需載入）

```
執行「產業掃描」時：
  1. 先讀此主檔案（sector_protocol_main.md）      ← 必讀
  2. Phase 0 執行時    → 讀 phase_0.md
  3. Phase 1-3 執行時  → 讀 phase_1-2-3.md
  4. Phase 4-5 執行時  → 讀 phase_4-5.md
  5. 寫入 JSON 輸出時  → 讀 schema.md 確認欄位
```

---

## SESSION STARTUP

```
SESSION CONFIG
──────────────────────────────────────────
RISK_TOLERANCE : LOW | MEDIUM | HIGH
FOCUS_DATE     : [留空 = 今日]
──────────────────────────────────────────
```

> 此 protocol 為**盤前產業熱度分析**，在個股分析（investment_protocol）之前執行。
> 輸出結果可直接作為 investment_protocol Phase 0 的補充 macro context。

---

## GLOBAL RULES

1. **Phase Execution Order**: 0 → 1 → 2 → 3 → 4 → 5。絕不跳過順序。
2. **Cache**（FRESH = mtime < 3 小時前 / 10800 秒）: 取 `./sector_logs/*_sector_intel.json` 最新檔。FRESH → 載入跳過 Phase 0–1，直接從 Phase 2 開始。STALE 或缺失 → 完整執行 Phase 0–1。**Phase 3 永遠重新執行，不可因快取跳過**。
   - **FTD/Market Top 新鮮度補丁**：即使走快取，仍需檢查 `./ftd_cache/` 與 `./market_top_cache/` 最新檔 FRESH 狀態。若有 FRESH 檔 → 覆寫 `_phase0.ftd`、`_phase0.market_top`、`_phase0.synthesized_exposure` 後再繼續。
3. **Debate Requirement**: Phase 4 必須有至少一個反方論點，禁止純多頭共識。
4. **Extreme Sentiment Trigger**: Phase 3 執行 `market-sentiment-analyzer` 後，`composite_score > 80` 或 `< 20` → `extreme_sentiment_triggered = true`。觸發後所有 HOT 產業 `risk_flags` 加入 `extreme_sentiment`；詳細級聯動作見 `phase_1-2-3.md`。
5. **Output Format**: 邏輯輸出為 JSON（schema 見 `schema.md`），最終 verdict 輸出 Markdown 表格。
6. **Skills Integration**: 各 phase 標明對應外部 skill，可直接調用其輸出。

---

## TEAM STRUCTURE

| Agent | 職責 | 對應 Skill |
|---|---|---|
| Macro Regime Analyst | 總體市場健康度、制度判斷 | `market-breadth-analyzer` |
| Sector Rotation Analyst | 產業輪動、週期定位 | `sector-analyst` |
| Theme Intelligence Analyst | 跨產業主題熱度與生命週期 | `theme-detector` |
| News Catalyst Analyst | 48h 新聞、財報催化劑、市場情緒儀表板 | `market-news-analyst`, `economic-calendar-fetcher`, `market-sentiment-analyzer` |
| Devil's Advocate | 挑戰多頭共識、量化尾部風險 | `tail-risk-analyzer` |
| Portfolio Strategist (PS) | 最終產業裁決、輸出報告 | — |

---

## EXECUTION TIMELINE & PARALLELIZATION

| Phase | Agent | 任務 | 預估時間 |
|---|---|---|---|
| 0 | Macro Regime | Breadth + FTD + Market Top | ~25 秒 |
| 1 | Sector Rotation | CSV 讀取 + uptrend 回填 | ~5 秒 |
| 2 | Theme Intelligence | theme-detector cache/skill | ~10–30 秒 |
| 3 | News Catalyst | sentiment + news + calendar | ~20 秒 |
| 4a–b | 各 Agent + DA | 提案 + tail-risk | ~35 秒 |
| 4c–5 | PS | 仲裁 + 輸出 | ~15 秒 |
| | | **順序總計** | **~110 秒** |

**並行機會（可縮至 ~75–85 秒）**：
- Phase 0：FTD + Market Top 腳本並行（節省 ~10 秒）
- Phase 2 + Phase 3：完全獨立，並行執行（節省 ~20 秒）
- Phase 4a：三 Agent 提案並行，PS 最後合成

---

## SCORING RUBRIC & WEIGHT ADAPTATION

### Base Score
```
Score_base = breadth_momentum(25) + theme_heat(25) + news_catalyst(25) + rotation_signal(25)
```

### 動態權重調整（乘法，Step 1–4 依序套用）

**Step 1 — Cycle Phase**

| cycle_phase | breadth | theme | news | rotation |
|---|---|---|---|---|
| Early | ×1.2 | ×1.0 | ×0.9 | ×1.0 |
| Mid | ×1.0 | ×1.1 | ×1.0 | ×1.1 |
| Late | ×0.8 | ×0.85 | ×1.2 | ×0.9 |
| Recession | ×0.5 | ×0.7 | ×1.4 | ×0.6 |

**Step 2 — Market Regime**

| market_regime | breadth | theme | news | rotation |
|---|---|---|---|---|
| VOLATILE (VIX>25) | ×1.3 | ×0.8 | ×1.2 | ×0.8 |
| RISK_OFF | ×1.2 | ×0.7 | ×1.3 | ×1.2 |
| RISK_ON | ×1.0 | ×1.2 | ×0.95 | ×1.0 |

**Step 3 — Breadth Score**
- breadth_score > 80 → breadth ×1.15
- breadth_score 30–50 → breadth ×0.85
- breadth_score < 30 → breadth ×0.5

**Step 4 — Extreme Sentiment**
- Extreme Greed（>80）→ 全部組件 ×0.85
- Extreme Fear（<20）→ 全部組件 ×1.05

**Step 5 — 特殊條件乘數（套用於 Score_adjusted）**
```
cycle_phase = Late/Recession + Cyclical sector → Score × 0.85
binary_risk_within_48h（affected sector）     → Score × 0.70
Score_adjusted: cap [0, 100]
```

### Verdict 對照

| Score | Verdict | 行動建議 |
|---|---|---|
| 75–100 | HOT | 積極尋找個股進場機會 |
| 50–74 | WARM | 選股謹慎，等待更好時機 |
| 25–49 | COLD | 減少暴露，避免新建倉 |
| 0–24 | AVOID | 清倉或嚴格停損 |

> `fragility_label = EXTREMELY FRAGILE` → 強制降一個 verdict 等級（不調整分數，直接 downgrade label）

---

## FINAL VERDICT TABLE

```
| Sector      | Verdict | Score | Key Reasons (top 2)       | Tail Risk   | Proxy ETF | Risk Flags          |
|-------------|---------|-------|---------------------------|-------------|-----------|---------------------|
| Technology  | HOT     |  82   | AI capex cycle intact...  | RESILIENT   | XLK       |                     |
| Energy      | COLD    |  38   | Demand slowdown, tariff.. | FRAGILE     | XLE       | binary_48h, fat_tail|

Market Regime: RISK_ON | Breadth Ceiling: 70% | Synthesized Ceiling: 55% ⚠️ | Cycle: Mid
Sentiment: Fear & Greed [XX/100 — Fear] | VIX: XX.X | Put/Call: X.XX | Signal Conflict: No

TOP THEMES TODAY: [theme1] [theme2]
HANDOFF TO INVESTMENT PROTOCOL: "一句話市場摘要"
```

> ⚠️ `signal_conflict = true` 時，Synthesized Ceiling 後方顯示警告符號，HANDOFF 明確說明衝突訊號。

---

## LOCAL FILE STRUCTURE

```
sector/
├── sector_protocol_main.md    ← 主檔（每次必讀，~200 行）
├── phase_0.md                 ← Phase 0 細節（~120 行）
├── phase_1-2-3.md             ← Phase 1–3 細節（~120 行）
├── phase_4-5.md               ← Phase 4–5 細節（~130 行）
├── schema.md                  ← 所有 JSON schema（~190 行）
├── sector_logs/
│   ├── YYYY-MM-DD_sector_intel.json
│   └── sector_history.json
├── breadth_cache/
├── ftd_cache/
└── market_top_cache/

reports/
└── YYYY-MM-DD_sector_report.md
```
