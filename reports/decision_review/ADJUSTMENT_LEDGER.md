# Adjustment Ledger

> 系統層調整 ledger。每筆 Rec 一個 entry，記錄假設、目標 metric、檔案、狀態。
> 下週 weekly REVIEW 會讀此檔，emit「Adjustment Evaluation」段比對 metric 變化。
>
> 寫入規則：
> - `applied_date`：absolute date (YYYY-MM-DD)
> - `applied_version`：VERSION 檔當時的值（e.g. `2.17.16`）
> - `rec_source`：原始 Rec 來源 ID（e.g. `REVIEW_2026-05-09 Rec 7`）
> - `target_metric`：要追蹤的量化指標（用具體欄位名 + 比較對象）
> - `files_changed`：絕對 / 相對 path 清單
> - `status`：`active` / `rolled-back` / `superseded` / `paused`
> - `evaluation_history`：weekly review 結束後 append 該週 metric 值與評語
>
> Schema 變更請同步更新 `ADJUSTMENT_LEDGER_SCHEMA.md`。

---

## Rec — verdict_deep_dive 方向推論支援 V5.0 動詞型 action

- **applied_date**: 2026-05-10
- **applied_version**: 2.17.26
- **rec_source**: User 觀察「MU 幾乎全 miss」追蹤
- **hypothesis**: V2.17.18 parser 修完後抓到 V5.0 verbs (`STAGED_ENTRY` / `EXECUTE` / `STAGED_EXIT`)，但 verdict 邏輯用 substring matching 只認 `BUY` / `SELL` / `CANCEL`，所有 V5 動詞默默 fallthrough 到 `direction="hold"` → bullish staged entry + 正報酬 → 被判 miss（"觀望/CANCEL → 錯過上漲"）
- **target_metric**:
  - `STAGED_ENTRY` action 的 `miss_rate < 30%`（baseline 21/29 = 72%）
  - `EXECUTE` action 的 `miss_rate < 30%`（baseline 6/8 = 75%）
  - 整體 deep-dive `hit_rate ≥ 50%`（baseline 44/109 = 40%）
- **files_changed**:
  - `scripts/verdict_rules.py` — `verdict_deep_dive` 方向推論 substring → 顯式 set + substring 雙重 mapping
- **smoke_result（V2.17.26 實測）**:
  - MU 6 STAGED_ENTRY/EXECUTE 全 flip miss→hit ✓
  - STAGED_ENTRY: hit 8→21 / miss 21→**5** / neutral 0→3 → miss_rate 72% → **17%** ✓
  - EXECUTE: hit 2→6 / miss 6→**2** → miss_rate 75% → **25%** ✓
  - 整體 deep-dive: hit 44→60 (+16) / miss 59→40 (-19) → hit_rate 40% → **55%** ✓
- **rollback_plan**: 還原 substring matching 區塊
- **status**: active
- **evaluation_history**:
  - 2026-05-10: smoke 達標。**REVIEW_2026-05-09 Pattern 1（mega-cap repeat-miss）大半是這個 verdict bug 製造的 artifact**，下週 REVIEW Pattern 1 會大幅縮水或消失，可重新評估 Hypothesis A 是否仍成立

---

## Rec 1 — deep-dive parser 跟上 V5.0 schema

- **applied_date**: 2026-05-10
- **applied_version**: 2.17.18
- **rec_source**: REVIEW_2026-05-09 Rec 1（高 conf prerequisite）
- **hypothesis**: V5.0 reports 用 `**Final Decision**` / `**最終決議**` 表頭 + 非加粗 / 加粗 value cell；既有 regex 只抓 `| **HOLD** |` (V4 form) → 52% deep-dive 變 unknown，污染所有 strategy pattern
- **target_metric**:
  - `event_index.decisions[?source=='deep-dive'].decision_content.final_action is null` 比例 < 30%（baseline 52%）
  - `final_score is null` 比例 < 20%（baseline ~16%）
  - 下週 REVIEW Pattern 1 / 2 數字大幅變化（人類驗證：BUY committed miss_rate / score 中段 miss_rate）
- **files_changed**:
  - `scripts/extractors/deep_dive_extractor.py` — `_find_decision` 新增 V5 patterns（Final Decision / 最終決議 / Action Label / EXECUTE / STAGED_ENTRY）+ 剝 parenthetical secondary action；`_find_final_score` 新增 V5 table row + case-insensitive body form + 全形冒號
- **smoke_result（V2.17.18 實測）**:
  - deep-dive action=None: 52% → **2.7%** (3/112) ✓
  - deep-dive score=None: 16% → **6.2%** (7/112) ✓
  - 殘留：20260422_MSFT / 20260503_TSM / 20260508_CRWV（特殊格式，留人工檢視）
- **rollback_plan**: 移除新增 patterns block，原 patterns 留著
- **status**: active
- **evaluation_history**:
  - 2026-05-10: smoke 達標（action 2.7%, score 6.2%），下週 REVIEW 比 pattern shift

---

## Rec 4 — news-digest macro_delta 解析跟上新 header 格式

- **applied_date**: 2026-05-10
- **applied_version**: 2.17.18
- **rec_source**: REVIEW_2026-05-09 Rec 4（高 conf instrumentation）
- **hypothesis**: 新版 digest 把 delta 寫進 `(session_macro_delta +0.20)` parenthetical / 用 Greek `Δ`，extractor 只認 `Delta` (英文) 或 signed prefix → 59% n/a
- **target_metric**:
  - `event_index.decisions[?source=='news-digest'].decision_content.macro_delta is null` 比例 < 30%（baseline 59%）
  - 下週 REVIEW news-digest evaluable 樣本翻倍（hit/miss 才能算）
- **files_changed**:
  - `scripts/extractors/news_digest_extractor.py` — `_find_macro_delta` 新增 `session_macro_delta` 兩種寫法 + Greek `Δ` headers
- **smoke_result（V2.17.18 實測）**:
  - news delta=None: 59% → **27.3%** (6/22) ✓
  - 殘留 6 筆全是 2026-04-15 ~ 04-28 的 news_protocol_v1 舊格式（無 macro_delta 概念，legit n/a，非 parser bug）
- **rollback_plan**: 移除 6 個新 patterns
- **status**: active
- **evaluation_history**:
  - 2026-05-10: smoke 達標（27.3% 含 6 筆 v1 protocol legit n/a），下週新增 v2 digest delta 應 100% 解析

---

## Rec 7 — sub_industry_heat 注入 deep-dive tuning_hooks

- **applied_date**: 2026-05-09
- **applied_version**: 2.17.16
- **rec_source**: REVIEW_2026-05-09（原始 Rec 7，Pattern 1 + 用戶 sector heat 觀察）
- **hypothesis**: deep-dive repeat-miss 集中在熱門 sub-industry（CPU / memory / AI infra）。沒有 industry-level context 進入 tuning_hooks → REVIEW 只能看 ticker，無法做 sector rollup
- **target_metric**:
  - `event_index.decisions[*].tuning_hooks.sub_industry_heat` 非 null 比例 ≥ 80%
  - 下週 REVIEW 應出現「Industry Rollup」段（人類驗證）
  - sub_industry_heat 的 `industry_top_30pct=true` 的 deep-dive miss_rate 跟 false 的差距（目標：差距 ≥ 15 個百分點 → 證實 heat asymmetry hypothesis）
- **files_changed**:
  - `scripts/_sector_heat.py` (NEW) — join helper
  - `scripts/extractors/deep_dive_extractor.py` — 注入 `tuning_hooks.sub_industry_heat`
- **rollback_plan**: 改 `enrich_ticker_heat = None` 即可關閉，不影響其他欄位
- **status**: active
- **evaluation_history**:
  - _尚未評估 — 下週 REVIEW 跑完後 append_

---

## Rec 8 — Industry rollup + adjustment_ledger_active 加入 event_index

- **applied_date**: 2026-05-09
- **applied_version**: 2.17.16
- **rec_source**: REVIEW_2026-05-09（原始 Rec 8）
- **hypothesis**: 只有 ticker-level pattern 不足以判斷 root cause。沒有 industry rollup 的 review，CPU/memory cluster 永遠看不見
- **target_metric**:
  - `event_index.industry_rollup` 至少包含 5 個 industry buckets
  - 下週 REVIEW 引用 `industry_rollup` 至少 1 次（人類驗證）
  - `event_index.adjustment_ledger_active` 反映本檔所有 `status: active` entries
- **files_changed**:
  - `scripts/build_event_index.py` — `_build_industry_rollup` + `_load_adjustment_ledger`
- **rollback_plan**: 移除 `out["industry_rollup"]` + `out["adjustment_ledger_active"]` 兩行；helper fn 留著無害
- **status**: active
- **evaluation_history**:
  - _尚未評估_

---

## Rec — Pill ring color alignment（追溯記錄，前面 sessions 已完成）

- **applied_date**: 2026-05-08 ~ 2026-05-09
- **applied_version**: 2.17.13 → 2.17.15
- **rec_source**: 用戶 dashboard ring 顏色報錯
- **hypothesis**: 8 個 sector pill ring 中有 4 個顏色 threshold 跟 tooltip dot 不對齊
- **target_metric**:
  - 8 個 pill 全部 ring color ≡ tooltip dot 顏色（人類目視）
- **files_changed**:
  - `Dashboard/script.js` — `_gaugeColor` 加 `'positive'` polarity；marketop / fg / vix inline 5-tier；cycle Mid 改 yellow + Distribution 為 canonical key；exposure 改 4-tier
- **rollback_plan**: git revert
- **status**: active
- **evaluation_history**:
  - 2026-05-09: 8/8 pill 對齊 ✓
