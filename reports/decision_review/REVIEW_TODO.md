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
- **review_count**: 2
- **status**: promoted-to-ledger as Rec 11 (2026-06-07, v3.41.0)
- **last_check**: 2026-06-07
- **evidence**:
  - 2026-05-24: N=9 (原 REVIEW 統計);**v3.18.1 後** final_action_modifier=CANCEL 抓到
    12 個 pre-V5 漏標 case → 真實 N 應 ≥ 20 + 9 = 29,但需下次 LLM REVIEW 用新欄重算
    miss rate 才算數
  - 2026-05-31: **READY** — CANCEL N=21 (≥20 達標),miss_rate 71% (15/21) ≥70% →
    開新 Rec 放寬 CANCEL。**blocked on TODO-005** (需 drawdown 才能定 threshold)
  - 2026-05-31 (post-fix): **blocker CLEARED** — Rec 9 (TODO-005) 已 surface drawdown。
    semis miss avg_dd 僅 -3.26% vs avg_ret +33.86% → CANCEL/HOLD miss 是真錯過非避損。
    decision band 位置已查明:`investment/investment_protocol_v5_0.md:851-857`
    (HOLD = score ∈ [-staged, +staged], default staged=0.8)。照紀律本週不改 protocol;
    下週 REVIEW 用新 drawdown 欄定 threshold 後 promote-to-ledger
  - 2026-06-07: **PROMOTED** — 與 TODO-002 合併為 **Rec 11 熱區保守性鬆綁**(v3.41.0)。
    CANCEL 多為 HOLD 經 cap 降下,故鬆綁 decision band 同時涵蓋。硬閘 CANCEL(burry/
    proceed_to_phase3=false/systemic) 保留不動。target_metric: CANCEL-miss<60%。搬 Closed

### TODO-002 — Pattern A (HOLD-miss 集中 Semiconductors) 等 decisive_agent + macro_regime 累積 → 驗證 H1/H3

- **created_in**: REVIEW_2026-05-24 Section 4 「累積資料後再評估」#1, #3
- **source_type**: accumulating_data
- **trigger_condition**: V5 era deep-dive 累積 N ≥ 30 (目前 11),
  且 `decisive_agent_method=score_x_confidence` 比例 ≥ 80%
- **target_action**: 用 decisive_agent + macro_regime 交叉分析 Semiconductors HOLD-miss,
  區分 H1 (HOLD score threshold 過鬆) vs H3 (Semiconductors agent 主導偏保守);
  若 H1 確認 → 候選改 HOLD threshold 0 → 0.5 (`investment/protocol/decision_rules.yaml`
  位置待查)
- **review_count**: 2
- **status**: promoted-to-ledger as Rec 11 (2026-06-07, v3.41.0)
- **last_check**: 2026-06-07
- **evidence**:
  - 2026-05-24: V5 era N=11 (3.18.1 已解鎖 decisive_agent 100% coverage)
  - 2026-05-31: **READY** — Semis HOLD 9/9=100% miss;HOLD-miss 跨 Fundamentals(56%)/
    News(62%)/Technical(50%) 均勻 → **否證 H3** (非單一 agent 偏保守),**支持 H1**
    (score 0–1 模糊區 default HOLD)。候選改 score 0–1 + top30 entry bias
  - 2026-05-31 (post-fix): **blocker CLEARED + 量化驗證 H1** — drawdown 欄證實 semis
    HOLD miss 是真錯過 (+33.86% 上漲,僅 -3.26% drawdown)。候選改:score ∈ [0,0.8)
    且 industry_top_30pct 且 regime ∈ {RISK_ON,BULL} 時不 default HOLD,降為
    STAGED_ENTRY probe。target file = `investment/investment_protocol_v5_0.md:851-857`
    decision band 表。下週 REVIEW promote-to-ledger (本週照紀律不動 protocol)
  - 2026-06-07: **PROMOTED** — 06-07 REVIEW Semis HOLD-miss 19/22=86% 確認。合併
    TODO-001 為 **Rec 11**(v3.41.0)。decision band 加熱區例外 + 15bps probe + 3 道硬保險
    (regime guard / decision_cap / risk_flag)。target: Semis HOLD-miss<60%,>70% paused。搬 Closed

### TODO-003 — momentum-screen verdict 規則重審 (Pattern F)

- **created_in**: REVIEW_2026-05-24 Section 4 「累積資料後再評估」#4
- **source_type**: accumulating_data
- **trigger_condition**: momentum-screen aggregate records 累積 8-12 週 (目前 24/週累積中)
- **target_action**: 評估是否 verdict window 對 momentum 短期屬性不適合,或 screen 本身在
  波動環境失靈;候選改 `skills/momentum-monitor/scripts/screen.py` verdict 邏輯或
  evaluation window
- **review_count**: 5
- **status**: stalled (2026-06-20 — accumulating_data 樣本凍結 N=24 連 4 輪不增長，screen 未產新 run。模型假設失效；下輪以**現有 N=24 直接評估**或 drop，不再 still_waiting。見 REVIEW_PROMPT.md Step -1 `stalled` 規則)
- **last_check**: 2026-06-21
- **evidence**:
  - 2026-05-24: hit_rate 13%, miss_rate 30% (n=23, preliminary)
  - 2026-05-31: still_waiting — n=24, hit 17% / miss 33% / neutral 50%;未到 8-12 週
  - 2026-06-13: still_waiting — n=24, hit 17% / miss 33% / neutral 50%(持平);未到 8-12 週
  - 2026-06-14: still_waiting — n=24, hit 16% / miss 33% / neutral 50%(無新 screen run);未到 8-12 週
  - 2026-06-20: still_waiting **[stale rc=4]** — n=24 持平 (4H/8M/12neu)，screen 未產新 run。accumulating_data 模型失效(樣本不增長) → 建議改「以 N=24 直接評」或 drop
  - 2026-06-21: stalled **[stale rc=5]** — n=24 持平 (4H/8M/12neu)，無新 screen run。建議人工裁決 drop 或以 N=24 直接評，不再逐週追蹤

### TODO-004 — 拆 `final_decision` + `final_action` 兩欄 (full version)

- **created_in**: 3.18.0 plan out-of-scope + Codex round-2 review #1 follow-up
- **source_type**: out_of_scope
- **trigger_condition**: 下輪 REVIEW 用 final_action_modifier 重算 Pattern A/B 後,
  若仍需更乾淨的 verb/label 分離 (e.g. CANCEL 跟 EXECUTE 應該是 verb 不是 modifier)
- **target_action**: extractor schema 完全拆兩欄,audit downstream consumer
  (`event_index` / `render_event_index.py` / `verdict_rules.py` / REVIEW_PROMPT 引用點),
  bump major / minor
- **review_count**: 5
- **status**: pending
- **last_check**: 2026-06-21
- **evidence**:
  - 2026-05-24: 3.18.1 已用輕量 modifier 欄 patch,先觀察 1-2 輪 REVIEW 看是否足夠
  - 2026-05-31: still_waiting — modifier 欄足夠:CANCEL/HOLD/EXECUTE/STAGED 乾淨分離,
    final_action null 1.6% (2/126)。暫不需完整拆兩欄,再觀察 1 輪
  - 2026-06-13: still_waiting — final_action null 1.5% (2/133),modifier 仍乾淨分離。
    輕量 modifier 欄持續足夠,不需完整拆兩欄
  - 2026-06-14: still_waiting — final_action null 2.1% (3/140),modifier 仍乾淨分離,輕量欄足夠
  - 2026-06-20: still_waiting **[stale rc=4]** — final_action null 2.1% (3/143)，modifier 4 週乾淨分離 → 建議 drop(輕量欄已足)
  - 2026-06-21: still_waiting **[stale rc=5]** — final_action null 2.0% (3/147)，modifier 乾淨分離維持 → 建議人工 drop(輕量欄已足，5 輪無需求)

### TODO-005 — verdict 物件 surface max_drawdown / max_runup

- **created_in**: REVIEW_2026-05-24 Section 5 系統盲點 #1
- **source_type**: instrumentation_gap
- **trigger_condition**: 下次 CANCEL Pattern 評估 (TODO-001) 需要 cancel 後 drawdown 才能
  判斷 "miss 上漲" vs "miss 但避開大跌"
- **target_action**: `scripts/build_event_index.py:_build_eval_block()` 加 verdict 物件
  surface `reality_at_eval.ticker_reality.max_drawdown_since` /  `max_runup_since`
  到 verdict.max_drawdown / verdict.max_runup
- **review_count**: 1
- **status**: done (promoted-to-ledger as Rec 9, 2026-05-31, v3.40.1)
- **last_check**: 2026-05-31
- **evidence**:
  - 2026-05-24: reality 物件已有此資料,只是 verdict 沒抽出
  - 2026-05-31: **READY (升優先)** — Pattern A (non-committal miss 63%) 上線驗收 blocker;
    本週見負 avg_miss_return 異常 (Renewable -5.99 / Banks -5.19 / VST -14.28) 無法判方向。
    TODO-001/002 Rec 須等此 surface 才能定 threshold
  - 2026-05-31 (DONE): 加 `max_runup_pct`/`max_drawdown_pct` 到 reality + deep-dive
    verdict + rollup (`avg_miss_drawdown_pct`/`worst_miss_drawdown_pct`)。注意原 spec 寫
    surface `max_*_since`,但那是**絕對價格**不可讀,改 surface **從 decision price 換算的
    pct**。50 筆 deep-dive miss 全帶欄位。→ Rec 9

### TODO-006 — pre-V5 era macro_regime null 29% (33/112 老報告無 phase0 cache)

- **created_in**: 3.18.1 backfill 結果觀察
- **source_type**: instrumentation_gap
- **trigger_condition**: 若有需求回推 pre-V5 regime 分析 (e.g. TODO-002 跨年比較)
- **target_action**: 兩條路 — (a) 回填缺失的 `investment/invest_logs/<date>_phase0.json`
  (從當時 cache 重建),(b) 為 pre-V5 報告加新 MD regex fallback (若報告當時有
  inline regime label)
- **review_count**: 5
- **status**: pending
- **last_check**: 2026-06-21
- **evidence**:
  - 2026-05-24: pre-V5 null_regime 33/112 (29%);79/112 (71%) 接到 phase0_cache OK
  - 2026-05-31: still_waiting — deep-dive macro_regime null 33/126 (26%);本週無回推需求
  - 2026-06-13: still_waiting — deep-dive macro_regime null 33/133 (24.8%);本週無回推需求
  - 2026-06-14: still_waiting — deep-dive macro_regime null 33/140 (23.6%);本週無回推需求
  - 2026-06-20: still_waiting **[stale rc=4]** — deep-dive macro_regime null 23.1% (33/143)，4 週無回推需求 → 建議 drop/休眠(待跨年比較才回填)
  - 2026-06-21: still_waiting **[stale rc=5]** — deep-dive macro_regime null 22.4% (33/147，殘量凍結在老報告)，無回推需求 → 建議休眠至跨年比較

### TODO-007 — Rec 7 (sub_industry_heat) heat asymmetry 連續 3 週 < 15pp 則 paused

- **created_in**: REVIEW_2026-05-24 Section 0 Rec 7 後續處置
- **source_type**: accumulating_data
- **trigger_condition**: 連續 3 週 top30 vs not30 miss_rate 差距 < 15pp
- **target_action**: 若觸發 → 在 `ADJUSTMENT_LEDGER.md` Rec 7 改 status: paused +
  記原因;否則繼續 continue 累積樣本 (目前 not30 N=36 偏少)
- **review_count**: 4
- **status**: promoted-to-ledger (2026-06-20 — 轉常設 tripwire；見 `ADJUSTMENT_LEDGER.md` Rec 7 `standing_monitor`。移出 Active 佇列，gap <15pp 連 3 週才 paused，不再逐週 TODO 追蹤)
- **last_check**: 2026-06-20
- **evidence**:
  - 2026-05-24: 第 1 週,差距 9pp (top30=40% vs not30=31%, n=81/36)
  - 2026-05-31: 第 2 週,差距 **14pp** (top30=44% 36/83 vs not30=30% 11/37);<15pp 第 2
    連週。再 1 週 <15pp → 觸發 paused
  - 2026-06-13: 差距 **18pp** (top30=47% 37/79 vs not30=29% 10/35) ≥15pp → **連續 <15pp
    計數歸零**,asymmetry 本週成立,Rec 7 continue 不 paused
  - 2026-06-14: 差距 **18pp** (top30=47% 37/79 vs not30=29% 10/35) 持平 ≥15pp;asymmetry 維持,Rec 7 continue
  - 2026-06-20: continue **[stale rc=4]** — gap **24pp** (top30 50% 44/88 vs not30 26% 10/38) ≥15pp，asymmetry 維持。建議轉常設 tripwire 移出 TODO 佇列(見 REVIEW_2026-06-20 §3)

### TODO-008 — news-digest 殘留 9 筆 macro_delta null 逐一檢視

- **created_in**: REVIEW_2026-05-24 Section 0 Rec 4 殘留
- **source_type**: instrumentation_gap
- **trigger_condition**: 下次 REVIEW 跑完看 news-digest null_rate 是否降到 < 20% (3.18.0
  Fix #1 修了 backtick+bold+equals 1 個 form,剩 9 筆需手動 audit 找新 form)
- **target_action**: 逐一檢視剩 9 筆 null 報告找出未涵蓋的 macro_delta form,加新
  pattern 到 `scripts/extractors/news_digest_extractor.py:_find_macro_delta`
- **review_count**: 1
- **status**: done (resolved into Rec 4, 2026-05-31, v3.40.1)
- **last_check**: 2026-05-31
- **evidence**:
  - 2026-05-24: pre-fix null 28.6% (10/35);3.18.0 修了 backtick+bold+equals 1 form,
    下次 REVIEW 看殘量
  - 2026-05-31: **READY** — null **回升** 35% (14/40),未降反升 → 新增 v2 digest 帶進
    未涵蓋寫法。Rec 4 judged regressed;須 audit 14 筆 null 找新 form
  - 2026-05-31 (DONE): audit 14 筆找到 4 種未涵蓋 form + 短 form `Macro Δ`。10-pattern
    ladder 換成單一 tolerant regex (label 變體 + backtick/bold wrapper + 選擇性 :/= +
    IGNORECASE)。null **35%→2.5%** (14→1),殘留 2026-04-15 是 v1 無 delta legit n/a,
    previously-good 零 regression。→ Rec 4 evaluation_history

### TODO-009 — News-decisive deep-dive miss 偏高 (Pattern D)

- **created_in**: REVIEW_2026-05-31 Section 3 「累積更多資料後再評估」#1 + Pattern D
- **source_type**: accumulating_data
- **trigger_condition**: decisive_agent=News 的 deep-dive 累積 N ≥ 40 (目前 31)
- **target_action**: 拆 News-decisive 決策的 action 分布 (是否偏 HOLD/CANCEL),確認 miss 是
  保守性 (與 Pattern A 同根) 還是 News edge 時效衰減;若後者 → 候選在短時效 / VOLATILE
  regime 降 News agent 權重 (`investment/protocol/` agent weights 位置待查)
- **review_count**: 4
- **status**: pending
- **last_check**: 2026-06-21
- **evidence**:
  - 2026-05-31: News-decisive miss 48% (15/31),vs Fundamentals 35% (19/56) / Sentiment
    33% (3/9);News 主導的 HOLD miss 62%
  - 2026-06-13: still_waiting — News-decisive miss 56% (15/27 evaluable),N=31 仍 < 40 門檻
    (與上週持平);vs Fundamentals 36% / Technical 43% / Sentiment 33%
  - 2026-06-14: still_waiting — News-decisive miss 56% (15/27 eval),N=31 (<40,持平)。拆 active/
    conservative:News-active miss 27% vs News-conservative 69% → 高 miss 主要來自保守決策(與 Pattern A 同根)
  - 2026-06-20: still_waiting — News-decisive N=31 (<40)，miss 56% (15/27 eval)；News-conserv 11/16=69% vs News-active 4/11=36% → 與 Pattern A 同根，可能不需獨立 News 權重
  - 2026-06-21: still_waiting — News-decisive N=32 (<40)，miss 55.6% (15/27 eval)；News-conserv 11/16=68.8% vs News-active 4/11=36.4% → 持續支持「與 Pattern A 同根」假設,補到 N≥40 後若維持即可 close(毋須獨立 News 權重)

### TODO-010 — window_complete_pct <100% 的 verdict 可能過早 → 追蹤 verdict 翻轉率

- **created_in**: REVIEW_2026-05-24 Section 5 系統盲點 #2(孤兒,2026-05-31 補建)
- **source_type**: instrumentation_gap
- **trigger_condition**: **資料已存在** — 9 個 weekly event_index snapshot
  (`event_index_2026-04-26 ~ 2026-05-31.json`)。先建 snapshot-diff helper 跨 snapshot
  比對同 decision_id 的 verdict.label,收集 **N≥20 筆** 從 window_complete_pct <100%
  → 100% 的 transition,量 flip_rate。N 不靠未來累積,下輪 REVIEW 即可跑
- **target_action**:
  - 建 `scripts/diff_verdict_flips.py`(讀 ≥2 snapshot,輸出 transition + flip_rate)
  - **修改門檻**:flip_rate **≥20%** → verdict 在未完成窗口不可靠 → 在
    `build_event_index.py` 為 window_complete_pct<100% 的 verdict 加 `provisional: true`,
    REVIEW Pattern 統計只計 100% 完成窗口 (或標 provisional 分開算);
    flip_rate **<10%** → close 為非問題 (早期 verdict 夠穩);10–20% → 再觀察 1 輪
- **review_count**: 5
- **status**: in_progress（flip 13.4% 落 observe band,續觀察；`scripts/diff_verdict_flips.py` 已重建並 commit，下輪可直接 `python3 scripts/diff_verdict_flips.py` 重跑）
- **last_check**: 2026-06-21
- **evidence**:
  - 2026-05-31 (補建): 0524 盲點 #2 連兩週無人接。drawdown (Rec 9) 本週剛 surface,
    與此可一起做。**N 門檻 = ≥20 筆 <100%→100% transition** (跨現有 9 snapshot,資料已備,
    非未來累積);決策看 flip_rate(≥20% 修 / <10% close)
  - 2026-06-07: **ran** — 跨 10 snapshot 算出 N=170 transition,flip_rate **12%** 落
    10-20% observe band → **不加 `provisional` flag**,Pattern 統計維持只計
    window_complete_pct=100 (現 112/128 已如此)。下輪再看:跌破 10% → close (早期 verdict
    夠穩);破 20% → 在 build_event_index.py 加 provisional。無需改 code,純記錄
  - 2026-06-13: still_waiting — 本週未重跑 diff_verdict_flips.py;Pattern 統計續維持只計
    window_complete=100 (106/119 evaluable 已如此)。下輪重跑確認 flip_rate 是否漂移出
    observe band
  - 2026-06-14: still_waiting — 本週仍未重跑 diff (距上次重跑僅 +1 日,snapshot 未顯著增長);
    Pattern 統計續只計 window_complete=100 (109/119 evaluable)。建議週末批次重跑
  - 2026-06-20: still_waiting **[stale rc=4]** — 仍未重跑 diff；資料已備可即跑。READY：週末批次重跑確認 flip_rate 是否漂出 12% observe band
  - 2026-06-20 (rebuild): **ran** — `scripts/diff_verdict_flips.py` 原從未 commit（報告誤稱已備），本輪重建並 commit。跨 13 snapshot 算出 N=**194** transition、flip=26、flip_rate **13.4%** 仍落 10–20% observe band（與 06-07 的 12% 一致）→ **不加 provisional flag**，Pattern 統計維持只計 window_complete=100。flip 多來自 sector-scan / momentum-screen 的中段窗口（多 neutral↔hit/miss），deep-dive flip 少（僅 NVDA 1 筆 miss→hit）。下輪用 `python3 scripts/diff_verdict_flips.py` 即可重跑；跌破 10% → close，破 20% → build_event_index 加 provisional
  - 2026-06-21: still_waiting **[rc=5]** — 距 06-20 重跑僅 +1 日，無新 weekly snapshot，未重跑 diff（flip 13.4% 維持 observe band）。READY：週末批次重跑確認未漂出 10–20%

### TODO-011 — news-digest verdict 規則結構性 0% hit(HIT_THRESHOLD_PCT 單股門檻誤套指數)

- **created_in**: REVIEW_2026-05-24 Section 5 盲點 #3 + REVIEW_2026-05-31 Section 4 盲點
  (連兩週列盲點未開 TODO,2026-05-31 補建)
- **source_type**: accumulating_data
- **trigger_condition**: 累積 **N≥15 筆 `|macro_delta|>0.5` 的 evaluable digest**
  (目前 7;弱訊號日 |delta|≤0.5 by-design neutral 不算)。強訊號日約 1/週,~8 週到標。
  TODO-008 修完 parser 後 macro_delta 已 39/40 non-null,評估管道已通
- **target_action**:
  - **root cause 已確認**(N=7 即可見):`HIT_THRESHOLD_PCT = 2.0`
    (`scripts/verdict_rules.py:25`,為單股設計)誤套 SPY。SPY 窗口內幾乎不動 ±2% →
    強訊號全被壓成 neutral。smoking gun:2026-05-14 delta -0.6 / SPY -1.93% 正確看空
    卻判 neutral(|1.93|<2.0);2026-05-16/05-17/05-23 同類
  - **修改門檻**:N≥15 強訊號後,用 grid 找最大化「方向正確 hit_rate」的 index-level
    threshold(候選 ±0.75 ~ ±1.0% 取代 ±2.0%),或改用 sign(delta)==sign(spy) 方向法。
    改 `verdict_news_digest` 傳入 source-specific threshold(不動 deep-dive 的 2.0%)
  - **注**:root cause 已明,若 user 要可不等 N=15,直接套保守 ±1.0% 預設先止血,
    下輪再用累積樣本微調(exploration-phase 偏好:即時調參優於等大樣本)
- **review_count**: 3
- **status**: in_progress（止血已套 Rec 10 / v3.40.3;待 N≥15 精校）
- **last_check**: 2026-06-20
- **evidence**:
  - 2026-05-31 (補建): post TODO-008,news-digest evaluable 39/40,但 hit 仍 0
    (miss 2 / neutral 36)。|delta|>0.5 僅 7 筆,其中 4 筆方向正確但 SPY 動 <2% 被 neutral。
    **N 門檻 = ≥15 筆強訊號 digest** 校準 threshold 值
  - 2026-05-31 (止血): root cause 既明 + 零 protocol 風險 + exploration-phase 偏好 →
    直接套 `NEWS_HIT_THRESHOLD_PCT = 1.0`(Rec 10 / v3.40.3)。hit **0→1**(05-14)。
    **剩餘工作**:累積 ≥15 筆強訊號後用 grid 精校 ±1.0% 值(或改 sign 方向法),屆時
    close 此 TODO / promote 為定版 Rec
  - 2026-06-13: still_waiting — 強訊號 |delta|>0.5 累積 **N=9** (上週 7) 仍 < 15。Rec 10
    後強訊號 hit 1 / miss 3 / neutral 5;5 筆強訊號仍被壓 neutral → 待 N≥15 用 grid 精校
    或改 sign(delta)==sign(spy) 方向法
  - 2026-06-14: still_waiting — 強訊號 N=9 (持平,本週無新強訊號 digest);hit 1/miss 3/neu 5。
    待 N≥15 精校
  - 2026-06-20: still_waiting — 強訊號 |delta|>0.5 N=9 (<15，持平)；Rec 10 後 1H/3M/5neu。待 N≥15 grid 精校

### TODO-012 — Rec 11 hot_zone_probe 活化驗收（決策層 Rec 尚未實測）

- **created_in**: REVIEW_2026-06-13 Section 4 系統盲點 #1 + Section 0.5 Rec 11 no_change
- **source_type**: accumulating_data
- **trigger_condition**: 2026-06-07 後累積 **N ≥ 5 筆** `macro_regime ∈ {RISK_ON, BULL}` 且
  `industry_top_30pct=true` 且 `final_score ∈ [0,+staged)` 的 deep-dive（即 Rec 11 規則應觸發的場景）
- **target_action**: 確認規則正確 fire — 該類標的 `hot_zone_probe=true`、`final_action=STAGED_ENTRY`、
  `position_size_pct ≤ 0.0015`(15bps)、與 decision_cap 互斥;並比對 Semis HOLD-miss / CANCEL-miss
  是否朝 <60% target 移動。資料源 `event_index.decisions[*].decision_content.hot_zone_probe`
- **review_count**: 3
- **status**: pending
- **last_check**: 2026-06-21
- **evidence**:
  - 2026-06-13: Rec 11 套用 6 天 0 次觸發(`hot_zone_probe` tagged = 0)。新 5 筆 deep-dive
    regime 全為 RISK_OFF/SIDEWAYS → 規則正確 dormant(符合 6 月回檔預期),但決策層 Rec
    target_metric 全為未介入基線(Semis HOLD-miss 83% / CANCEL 68%),**尚未驗收**。等 regime
    回 RISK_ON/BULL 才有評估樣本
  - 2026-06-14: still_waiting — Rec 11 套用 7 天,hot_zone_probe fires=0;06-07 後 12 筆 deep-dive
    regime 全 RISK_OFF(1)/SIDEWAYS(11),qualifying scenario N=0 → 規則持續正確 dormant。
    連續 2 週 no_change(=dormant by design,非失效);等 regime 回 RISK_ON/BULL 才有驗收樣本
  - 2026-06-20: still_waiting — 套用 13 天 hot_zone_probe fires=0；06-07 後 15 筆 deep-dive regime=SIDEWAYS 13/RISK_OFF 1/RISK_ON 1，qualifying N=0 → 持續正確 dormant。新觀察：保守 miss 全落 SIDEWAYS/RISK_OFF(見 TODO-014)
  - 2026-06-21: still_waiting — 套用 14 天 fires=0。**regime 翻回 RISK_ON**：06-21 新 4 筆 deep-dive(MU 0.814/NVDA 1.04/NBIS -0.009/PLTR -0.485) 全 RISK_ON 但 score 不落 [0,0.8) 觸發窗 → qualifying 仍 N=0。距首次驗收最近的一次機會窗；下批 top30 半導體若 score∈[0,0.8) 即觸發。Rec 11 cumulative no_change 第 3 輪(dormant 非失效；89% Semis HOLD-miss 為未介入基線，不觸發 paused)

### TODO-013 — 0–1 score band 內部結構不可見 (Pattern B 假設 2)

- **created_in**: REVIEW_2026-06-14 Section 4 系統盲點 + Pattern B 假設 2
- **source_type**: instrumentation_gap
- **trigger_condition**: instrumentation 落地後即可評估(非未來累積) — 加欄後下輪 REVIEW 用
  agent_score_stdev 拆 0–1 band 的 hit/miss
- **target_action**: `scripts/build_event_index.py` tuning_hooks 加 `agent_score_stdev`
  (4 lane agent score 標準差),分離「弱訊號 0–1」(低 stdev) vs「agent 高分歧 0–1」(高 stdev);
  若高分歧子集 miss 顯著高 → 候選在高 dispersion 時降倉或標 low-conviction
- **review_count**: 2
- **status**: ready → **可 close (hypothesis refuted)**（agent_score_stdev 已落地，全樣本檢定假設不成立）
- **last_check**: 2026-06-21
- **evidence**:
  - 2026-06-14: score 0–1 band n=68 (最大樣本),decided hit 48% (29H/31M) 近擲硬幣,
    vs 1–2 band 74% (32H/11M)。無法分離弱訊號 vs 高分歧兩種成因 — 缺 agent_score_stdev
  - 2026-06-20: **ready** — score|0-1| decided n=76 miss 50% (38/76) vs |1-2| 31% (14/45)。instrumentation 可即落地(非未來累積) → 優先處理
  - 2026-06-21: **EVALUATED → 假設否證** — `agent_score_stdev` 已落地(null 17/147)。0–1 band(N=82) 以中位 stdev 1.363 拆兩半:低 stdev(共識弱訊號) miss **56.8%**(25/44) vs 高 stdev(agent 高分歧) miss **40.6%**(13/32)。**與假設相反**:0–1 miss 來自共識弱訊號被 default HOLD(低 stdev 反而 miss 更高),非 agent 高分歧。「高 dispersion 降倉/標 low-conviction」候選**無證據支持,不實作**。併入 Pattern A,建議 status → done(refuted)

### TODO-014 — Rec 11 regime guard 範圍重檢 (Pattern C：保守 miss 集中 SIDEWAYS 非 RISK_ON/BULL)

- **created_in**: REVIEW_2026-06-20 Section 2 Pattern C + Section 0.5 Rec 11 新觀察
- **source_type**: accumulating_data
- **trigger_condition**: SIDEWAYS regime 下 top30 × score∈[0,+staged) 的保守 miss 累積 **N ≥ 10**，
  且 RISK_ON/BULL 出現 ≥1 筆 qualifying scenario 作對照 (目前 SIDEWAYS 保守 miss N=3，RISK_ON N=0)
- **target_action**: 評估是否把 Rec 11 熱區鬆綁的 regime guard 從 {RISK_ON,BULL} 擴到含 SIDEWAYS;
  若 SIDEWAYS 保守 miss 持續 ≥60% 且 drawdown 仍小 → 候選改
  `investment/investment_protocol_v5_0.md` Rec 11 regime guard 條件。**嚴禁在 N<10 時動 Rec 11**
- **review_count**: 1
- **status**: pending（trigger 改：全樣本已否證「集中 SIDEWAYS」；僅保留 RISK_ON/BULL qualifying 驗收路徑＝TODO-012）
- **last_check**: 2026-06-21
- **evidence**:
  - 2026-06-20: 06-07 後保守 miss (MRVL RISK_OFF / MU·ALAB·ARM SIDEWAYS) **0 筆在 RISK_ON/BULL**，
    但 Rec 11 只在 RISK_ON/BULL 觸發 → regime guard 可能把規則限制在「問題不發生的 regime」。N=4 太小，列推測
  - 2026-06-21: **全樣本否證** — conservative(HOLD/CANCEL) miss by regime：BULL **77.8%**(7/9) > RISK_ON **55.6%**(15/27) > VOLATILE 55.6%(5/9) > **SIDEWAYS 38.5%**(5/13)。保守 miss 在 BULL/RISK_ON 最嚴重、SIDEWAYS 最低 → 06-07 後 SIDEWAYS 那 3 筆是 6 月回檔小樣本 artifact。Rec 11 regime guard={RISK_ON,BULL} **方向正確**,**不應**擴到 SIDEWAYS(SIDEWAYS 保守反而較準,鬆綁增風險)。本 TODO 收斂為 TODO-012 驗收路徑

---

## Closed Items (archive)

> 已 done / dropped / promoted-to-ledger 的 item 搬到這裡保留歷史。

> 註:TODO-001 / TODO-002 / TODO-005 / TODO-008 已 promoted/done,完整 evidence 仍留 Active
> 區段供歷史對照(尚未實體搬移),下次人工維護時可搬來此區。

### TODO-002 — Pattern A (Semis HOLD-miss) 驗 H1

- **closed_at**: 2026-06-07
- **closed_reason**: promoted-to-ledger as Rec 11
- **outcome**: HOLD-miss 86% (N=22) + drawdown 證實真錯過 → H1 確認、H3 否證。熱區 decision band
  鬆綁(15bps probe + 3 道硬保險),Semis HOLD-miss>70% 即 paused。

### TODO-001 — Pattern B (CANCEL miss) N≥20 重評

- **closed_at**: 2026-06-07
- **closed_reason**: promoted-to-ledger as Rec 11 (與 TODO-002 合併)
- **outcome**: CANCEL-miss 71% (N=21),與 Pattern A 同根(多為 HOLD 經 cap 降下)。band 鬆綁同時涵蓋;
  硬閘 CANCEL 保留。target CANCEL-miss<60%。

---

## Maintenance

- 每週 LLM REVIEW preamble 自動 +1 `review_count` 並 mark `last_check`
- 人類在 weekly 之後手動:
  - tick `done` / `dropped` / `promoted-to-ledger`,搬到 Closed 區
  - new items 由 LLM postamble append,連號 (next free ID)
- 不在此檔記**已套用**的 config 改動 (那屬 ADJUSTMENT_LEDGER.md)
