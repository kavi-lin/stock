# Pre-Market Sector Intelligence Protocol (V1.3)

## 子檔案載入順序

```
1. sector_protocol_main.md   ← 此檔（必讀）
2. Phase 0 執行   → phase_0.md
3. Phase 1-3 執行 → phase_1-2-3.md
4. Phase 4-5 執行 → phase_4-5.md
5. 寫 JSON       → schema.md
```

## SESSION CONFIG

```
RISK_TOLERANCE : LOW | MEDIUM | HIGH
FOCUS_DATE     : [留空 = 今日]
```

---

## GLOBAL RULES

1. **Phase Execution Order**: 0 → 1 → 2 → 3 → 4 → 5。絕不跳過順序。
2. **Cache**（FRESH = mtime < 3 小時前 / 10800 秒）: 取 `./sector_logs/*_sector_intel.json` 最新檔。FRESH → 載入跳過 Phase 0–1，直接從 Phase 2 開始。STALE 或缺失 → 完整執行 Phase 0–1。**Phase 3 永遠重新執行，不可因快取跳過**。
   - **FTD/Market Top 新鮮度補丁**：即使走快取，仍需檢查 `./ftd_cache/` 與 `./market_top_cache/` 最新檔 FRESH 狀態。若有 FRESH 檔 → 覆寫 `_phase0.ftd`、`_phase0.market_top`、`_phase0.synthesized_exposure` 後再繼續。
3. **Debate Requirement**: Phase 4 必須有至少一個反方論點，禁止純多頭共識。
4. **Extreme Sentiment Trigger**: Phase 3 執行 `market-sentiment-analyzer` 後，`composite_score > 80` 或 `< 20` → `extreme_sentiment_triggered = true`。觸發後所有 HOT 產業 `risk_flags` 加入 `extreme_sentiment`；詳細級聯動作見 `phase_1-2-3.md`。
5. **Output Format**: 邏輯輸出為 JSON（schema 見 `schema.md`）。**Markdown 報告由 `sector/scripts/render_sector_report.py` 從 JSON 直接渲染，Phase 5 不再由模型重寫文字**（V1.4）。
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

## SCORING RUBRIC & WEIGHT ADAPTATION

### Base Score
```
Score_base = breadth_momentum(25) + theme_heat(25) + news_catalyst(25) + rotation_signal(25)
```

### 動態權重調整（乘法，Step 1–4 依序套用）

**Step 1 — Cycle Phase**（`fred_available=true` 時 SKIP，由 Step 6 取代）

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
cycle_phase = Late/Recession + Cyclical sector → Score × 0.85   # only if Step 1 active (fred_available=false)
binary_risk_within_48h（affected sector）     → Score × 0.70
Score_adjusted: cap [0, 100]
```

**Step 6 — FRED Regime Overlay**（`fred_available=true` 時取代 Step 1）

⚠️ MUST 用 `python3 sector/scripts/step6_overlay.py --input "Sector:Score,..."` 計算，**不可 LLM 心算**。Script 已套規則 + confidence gating，輸出 JSON 直接 paste。

規則（僅參考；script 是唯一執行者）：
- `step6_multiplier = 1.0 + (raw - 1.0) × regime_confidence`
- raw = base matrix (regime × cyclical/defensive) × sector-specific override
- `fred_available=false` → multiplier=1.0（自動降回 Step 1）

| regime_label | cyclical raw | defensive raw |
|---|---|---|
| Goldilocks / Soft Landing / Benign Easing | 1.05 | 0.95 |
| Reflation | 1.10 | 0.90 |
| Overheating | 0.95 | 1.00 |
| Late Cycle Tightening | 0.85 | 1.05 |
| Stagflation | 0.75 | 1.10 |
| Recession Easing | 0.95 | 1.05 |
| Recession Risk | 0.70 | 1.15 |
| Transitional | 1.00 | 1.00 |

Override：`sector ∈ favor` → raw × 1.05 (cap 1.15)；`sector ∈ avoid` → raw × 0.90 (floor 0.70)

**輸出**：sectors[] 每筆寫 `step6_fred_multiplier`；頂層寫 `step6_overlay` block。詳見 schema.md。

### Verdict 對照

| Score | Verdict | 行動建議 |
|---|---|---|
| 75–100 | HOT | 積極尋找個股進場機會 |
| 50–74 | WARM | 選股謹慎，等待更好時機 |
| 25–49 | COLD | 減少暴露，避免新建倉 |
| 0–24 | AVOID | 清倉或嚴格停損 |

> `fragility_label = EXTREMELY FRAGILE` → 強制降一個 verdict 等級（不調整分數，直接 downgrade label）

---

## FINAL OUTPUT

Phase 5 由 `sector/scripts/render_sector_report.py` 從 `sector_intel.json`
渲染 markdown — 模型不再撰寫 markdown。詳見 `phase_4-5.md` Phase 5。
