# REVIEW Carry-over Todo Queue

> 每週 LLM REVIEW 前讀此檔(preamble Step -1),把 active items 拋到報告頂部
> 「## 0. Carry-over Status」段。REVIEW 結束時(postamble Step 5)把本次新識別
> 的 carry-over 候選 append 到 Active Items 區段,ID 連號。
>
> **人類維護**:每週手動把已執行的 item mark `done`、被 promote 為 ledger Rec 的
> 改 `promoted-to-ledger`、不再相關的標 `dropped`,並從 Active 區段搬到 Closed
> 區段保留歷史。
>
> 跟 `ADJUSTMENT_LEDGER.md` 分工:ledger = **已套用** 的系統調整需週週評估;
> 此檔 = **待決定 / 等資料 / 等修** 的候選項,評估前不算 Rec。

---

## Schema

Each item = level-3 heading + bullet body:

```markdown
### TODO-<NNN> — <one-line title>
- **created_in**: REVIEW_<YYYY-MM-DD> (Section reference)
- **source_type**: `accumulating_data` | `out_of_scope` | `instrumentation_gap`
- **trigger_condition**: 何時可以動 (量化條件,e.g. "N ≥ 20 cancel decisions accumulated")
- **target_action**: 具體要做什麼 + file path
- **review_count**: 出現過幾次 REVIEW 還沒動 (每週 +1)
- **status**: `pending` | `in_progress` | `done` | `dropped` | `promoted-to-ledger`
- **last_check**: YYYY-MM-DD (最後一次 LLM 評估的日期)
- **evidence**: (optional) 每次 REVIEW 評估記一筆 — `- YYYY-MM-DD: N=X (still below threshold)`
```

### source_type 語義

- `accumulating_data` — REVIEW Section 4 「累積資料後再評估」類。trigger_condition 是
  量化樣本門檻 (e.g. `N ≥ 20`)、`evidence` 累積每週 N 值
- `out_of_scope` — REVIEW / implementation plan 明確「下輪再做」的延後項。trigger_condition
  通常是「下次有人開 ticket / blast radius 變小」這類軟條件
- `instrumentation_gap` — Pattern G/H 類「某 hook 100% null」的人黃。trigger_condition
  通常是「null rate 降到 X% 就 close」

### review_count 規則

- 出現第 1 次: review_count=0 (本週 emit)
- 後續每週 LLM preamble 跑 → +1
- review_count ≥ 4 (一個月沒動) → LLM 應在 Section 0 標 `[stale]` 並建議 drop / promote

---

## Active Items

### TODO-001 — Pattern B (CANCEL miss 78%) N=9 → 累積 N≥20 重新評估

- **created_in**: REVIEW_2026-05-24 Section 4 「累積更多資料後再評估」#2
- **source_type**: accumulating_data
- **trigger_condition**: deep-dive CANCEL decisions (含 final_action_modifier=CANCEL) 累積 N ≥ 20
- **target_action**: 重算 CANCEL miss_rate;若仍 ≥ 70% → 開新 Rec 放寬 CANCEL 規則
  (`investment/protocol/...` 規則檔位置待查)
- **review_count**: 0
- **status**: pending
- **last_check**: 2026-05-24
- **evidence**:
  - 2026-05-24: N=9 (原 REVIEW 統計);**v3.18.1 後** final_action_modifier=CANCEL 抓到
    12 個 pre-V5 漏標 case → 真實 N 應 ≥ 20 + 9 = 29,但需下次 LLM REVIEW 用新欄重算
    miss rate 才算數

### TODO-002 — Pattern A (HOLD-miss 集中 Semiconductors) 等 decisive_agent + macro_regime 累積 → 驗證 H1/H3

- **created_in**: REVIEW_2026-05-24 Section 4 「累積資料後再評估」#1, #3
- **source_type**: accumulating_data
- **trigger_condition**: V5 era deep-dive 累積 N ≥ 30 (目前 11),
  且 `decisive_agent_method=score_x_confidence` 比例 ≥ 80%
- **target_action**: 用 decisive_agent + macro_regime 交叉分析 Semiconductors HOLD-miss,
  區分 H1 (HOLD score threshold 過鬆) vs H3 (Semiconductors agent 主導偏保守);
  若 H1 確認 → 候選改 HOLD threshold 0 → 0.5 (`investment/protocol/decision_rules.yaml`
  位置待查)
- **review_count**: 0
- **status**: pending
- **last_check**: 2026-05-24
- **evidence**:
  - 2026-05-24: V5 era N=11 (3.18.1 已解鎖 decisive_agent 100% coverage)

### TODO-003 — momentum-screen verdict 規則重審 (Pattern F)

- **created_in**: REVIEW_2026-05-24 Section 4 「累積資料後再評估」#4
- **source_type**: accumulating_data
- **trigger_condition**: momentum-screen aggregate records 累積 8-12 週 (目前 24/週累積中)
- **target_action**: 評估是否 verdict window 對 momentum 短期屬性不適合,或 screen 本身在
  波動環境失靈;候選改 `skills/momentum-monitor/scripts/screen.py` verdict 邏輯或
  evaluation window
- **review_count**: 0
- **status**: pending
- **last_check**: 2026-05-24
- **evidence**:
  - 2026-05-24: hit_rate 13%, miss_rate 30% (n=23, preliminary)

### TODO-004 — 拆 `final_decision` + `final_action` 兩欄 (full version)

- **created_in**: 3.18.0 plan out-of-scope + Codex round-2 review #1 follow-up
- **source_type**: out_of_scope
- **trigger_condition**: 下輪 REVIEW 用 final_action_modifier 重算 Pattern A/B 後,
  若仍需更乾淨的 verb/label 分離 (e.g. CANCEL 跟 EXECUTE 應該是 verb 不是 modifier)
- **target_action**: extractor schema 完全拆兩欄,audit downstream consumer
  (`event_index` / `render_event_index.py` / `verdict_rules.py` / REVIEW_PROMPT 引用點),
  bump major / minor
- **review_count**: 0
- **status**: pending
- **last_check**: 2026-05-24
- **evidence**:
  - 2026-05-24: 3.18.1 已用輕量 modifier 欄 patch,先觀察 1-2 輪 REVIEW 看是否足夠

### TODO-005 — verdict 物件 surface max_drawdown / max_runup

- **created_in**: REVIEW_2026-05-24 Section 5 系統盲點 #1
- **source_type**: instrumentation_gap
- **trigger_condition**: 下次 CANCEL Pattern 評估 (TODO-001) 需要 cancel 後 drawdown 才能
  判斷 "miss 上漲" vs "miss 但避開大跌"
- **target_action**: `scripts/build_event_index.py:_build_eval_block()` 加 verdict 物件
  surface `reality_at_eval.ticker_reality.max_drawdown_since` /  `max_runup_since`
  到 verdict.max_drawdown / verdict.max_runup
- **review_count**: 0
- **status**: pending
- **last_check**: 2026-05-24
- **evidence**:
  - 2026-05-24: reality 物件已有此資料,只是 verdict 沒抽出

### TODO-006 — pre-V5 era macro_regime null 29% (33/112 老報告無 phase0 cache)

- **created_in**: 3.18.1 backfill 結果觀察
- **source_type**: instrumentation_gap
- **trigger_condition**: 若有需求回推 pre-V5 regime 分析 (e.g. TODO-002 跨年比較)
- **target_action**: 兩條路 — (a) 回填缺失的 `investment/invest_logs/<date>_phase0.json`
  (從當時 cache 重建),(b) 為 pre-V5 報告加新 MD regex fallback (若報告當時有
  inline regime label)
- **review_count**: 0
- **status**: pending
- **last_check**: 2026-05-24
- **evidence**:
  - 2026-05-24: pre-V5 null_regime 33/112 (29%);79/112 (71%) 接到 phase0_cache OK

### TODO-007 — Rec 7 (sub_industry_heat) heat asymmetry 連續 3 週 < 15pp 則 paused

- **created_in**: REVIEW_2026-05-24 Section 0 Rec 7 後續處置
- **source_type**: accumulating_data
- **trigger_condition**: 連續 3 週 top30 vs not30 miss_rate 差距 < 15pp
- **target_action**: 若觸發 → 在 `ADJUSTMENT_LEDGER.md` Rec 7 改 status: paused +
  記原因;否則繼續 continue 累積樣本 (目前 not30 N=36 偏少)
- **review_count**: 0
- **status**: pending
- **last_check**: 2026-05-24
- **evidence**:
  - 2026-05-24: 第 1 週,差距 9pp (top30=40% vs not30=31%, n=81/36)

### TODO-008 — news-digest 殘留 9 筆 macro_delta null 逐一檢視

- **created_in**: REVIEW_2026-05-24 Section 0 Rec 4 殘留
- **source_type**: instrumentation_gap
- **trigger_condition**: 下次 REVIEW 跑完看 news-digest null_rate 是否降到 < 20% (3.18.0
  Fix #1 修了 backtick+bold+equals 1 個 form,剩 9 筆需手動 audit 找新 form)
- **target_action**: 逐一檢視剩 9 筆 null 報告找出未涵蓋的 macro_delta form,加新
  pattern 到 `scripts/extractors/news_digest_extractor.py:_find_macro_delta`
- **review_count**: 0
- **status**: pending
- **last_check**: 2026-05-24
- **evidence**:
  - 2026-05-24: pre-fix null 28.6% (10/35);3.18.0 修了 backtick+bold+equals 1 form,
    下次 REVIEW 看殘量

---

## Closed Items (archive)

> 已 done / dropped / promoted-to-ledger 的 item 搬到這裡保留歷史。

### TODO-EXAMPLE — (placeholder, no closed items yet)

- **closed_at**: YYYY-MM-DD
- **closed_reason**: `done` / `dropped` / `promoted-to-ledger as Rec <N>`
- **outcome**: 一句話結果

---

## Maintenance

- 每週 LLM REVIEW preamble 自動 +1 `review_count` 並 mark `last_check`
- 人類在 weekly 之後手動:
  - tick `done` / `dropped` / `promoted-to-ledger`,搬到 Closed 區
  - new items 由 LLM postamble append,連號 (next free ID)
- 不在此檔記**已套用**的 config 改動 (那屬 ADJUSTMENT_LEDGER.md)
