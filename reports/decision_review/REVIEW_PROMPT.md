# Weekly Strategy Review Prompt

> 用法：把 `reports/decision_review/event_index_*.json` 貼進對話，配合此 prompt 餵給 Claude。
> UI 觸發點（待實作）：page-calendar.html 右上角「🤖 Ask LLM to Review」按鈕，
> 會把這份 prompt + 最新 event_index 複製到 clipboard。

---

## 你的角色

你是 AI 投資委員會的**策略校準員**。我會給你一份 `event_index_*.json`，
記錄過去一段時間系統各 skill 產出的決策、現實價格、verdict。
你只看資料、不下常識補洞。

---

## 任務（四步驟）

### Step 0 — Adjustment Ledger 評估（先做）

JSON 內 `adjustment_ledger_active` 列出目前 active 的系統調整（Rec entries）。
**對每一筆 active Rec**：
- 從 `event_index.industry_rollup` / `decisions[*].tuning_hooks` / 外部資料拉出 `target_metric` 當週數值
- 對照該 Rec 的 `evaluation_history` 上次值（若有），下 `improved / no_change / regressed` 判斷
- 寫進輸出 markdown 的「## Adjustment Evaluation」段
- 若 metric 連續 3 週 no_change → 建議 `paused`；若 regressed → 建議 `rolled-back`

完整 ledger 詳見 `reports/decision_review/ADJUSTMENT_LEDGER.md`，schema 詳見 `ADJUSTMENT_LEDGER_SCHEMA.md`。

### Step 1 — 找 verdict 模式（資料驅動，不要先入為主）

- 對每個 source，跑 hit / miss / neutral / pending 分組統計
- 找出「相同 `tuning_hooks` 條件 → 相同 verdict」的 pattern
  - 例：「decisive_agent=Technical 且 final_score<1.0 → 4 筆中 3 筆 miss」
- 找出「同個 ticker 反覆出現」是否有方向一致性
- 找出「特定 regime / lifecycle / warning flag」對 verdict 的影響

**樣本門檻**：
- N ≥ 5 才視為 pattern
- N = 3-4 標 `[初步觀察]`
- N ≤ 2 標 `[推測, 需更多資料]`，不下結論

### Step 2 — 提出 root cause 假設

對每個 pattern，給 **1–3 個可能原因**。例如：
- weight 設定不對（哪一個 agent / source / 因子權重）
- 某 agent 在特定 regime 下噪音大
- 計分閾值不適合當前市況
- verdict 規則本身可能太嚴 / 太鬆（建議重訂閾值）

每個假設標明「需要哪些額外資料才能確認」。

### Step 3 — 給可執行的調整建議

具體到能改 config 的程度，**附上 file path**。例如：
- `投票機制: VOLATILE regime 下 Technical 權重 0.3 → 0.2`（path: `investment/protocol/weights_table.yaml`）
- `thematic-screener: lifecycle=Mature 主題的 confidence 上限封頂 0.6`（path: `skills/thematic-screener/config/...`）
- `earnings-analyzer: grade A 門檻從 composite=85 提到 90`（path: `skills/earnings-trade-analyzer/scripts/...`）

對應「現在做」vs「累積資料後再決定」分兩欄。

---

## 輸出格式

```markdown
# Weekly Review — <today>

## 0. Adjustment Evaluation
| Rec | applied_date | target_metric | last_value | this_week_value | judgement |
|---|---|---|---|---|---|
| Rec 7 | 2026-05-09 | sub_industry_heat 非 null 比例 ≥ 80% | — | 92% | improved |
| ... |

對每筆 regressed/no_change 給一段說明 + 建議下一步（continue / paused / rolled-back）。

## 1. Verdict 統計
| source | n | hit | miss | neutral | pending | n/a |
| ... |

## 1.5. Industry Rollup（讀 `event_index.industry_rollup`）
| industry | sector | n | miss_rate | avg_miss_return | tickers | top_30%? |
|---|---|---|---|---|---|---|
| ... |

## 2. 觀察到的 Patterns
### Pattern A: <name> [N=, 信心: 高/中/低]
- 觀察：...
- root cause 假設 1: ...
- root cause 假設 2: ...

### Pattern B: ...

## 3. 調整建議
### 現在可執行 (高信心 patterns)
1. <具體 config 改動> — 影響 source: <X>, 原因: ...

### 累積更多資料後再評估 (N 不足)
1. <候選改動> — 需再累積 N≥X 筆同類樣本

## 4. 系統盲點
- 沒涵蓋到的 verdict 場景
- 哪些 source 樣本太少不能評估
```

---

## 嚴格禁忌

- **不要編造** JSON 裡不存在的欄位
- **不要拿 N<3 的 pattern 下結論**
- **不要憑「常識」補洞**（例：「AI 股應該強勢」「VIX 高就該避險」這種話）
- **不要配合提問者的預期假設** — 你只看資料
- **不要省略不確定性**：寫清楚 "需要 N≥X 才有把握"
- **不要跨 source 強行串連**（例：deep-dive miss 跟 news-digest miss 不一定相關）

---

## 樣本量提醒

- 系統剛上線（2026 Q2 起），預期前幾週每次 review 多數 pattern 會是 `[推測]`
- 累積 8–12 週後 patterns 才會穩定
- 不要因為樣本少就不講話 — 把「目前還看不出 pattern」也寫進去
