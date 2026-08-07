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
- **review_count**: 9
- **status**: stalled — **建議 drop（2026-07-19）**：N=24 凍 7 輪，decided 僅 9 筆，統計上無法支持任何 verdict 規則改動
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-05-24: hit_rate 13%, miss_rate 30% (n=23, preliminary)
  - 2026-05-31: still_waiting — n=24, hit 17% / miss 33% / neutral 50%;未到 8-12 週
  - 2026-06-13: still_waiting — n=24, hit 17% / miss 33% / neutral 50%(持平);未到 8-12 週
  - 2026-06-14: still_waiting — n=24, hit 16% / miss 33% / neutral 50%(無新 screen run);未到 8-12 週
  - 2026-06-20: still_waiting **[stale rc=4]** — n=24 持平 (4H/8M/12neu)，screen 未產新 run。accumulating_data 模型失效(樣本不增長) → 建議改「以 N=24 直接評」或 drop
  - 2026-06-21: stalled **[stale rc=5]** — n=24 持平 (4H/8M/12neu)，無新 screen run。建議人工裁決 drop 或以 N=24 直接評，不再逐週追蹤
  - 2026-06-28: stalled **[stale rc=6]** — n=24 持平 (4H/8M/12neu)，第 6 輪無新 screen run。建議人工本輪後直接以 N=24 評或 drop
  - 2026-07-19: stalled **[rc=7 → drop]** — n=24 第 7 輪持平 (4H/5M/14neu/1pend)，decided 僅 9 筆 (miss 55.6%)。
    N 太小無法支持規則改動且上游停產 → 建議人工 **drop**（見 REVIEW_2026-07-19 §3「累積後再評估」#4）
  - 2026-07-31: stalled **[rc=8 → drop]** — n=24 第 8 輪持平 (4H/5M/14neu/1pend)；W28–W31 零新 screen run。
    根因併入 Pattern D（決策層產出率崩落，見 TODO-021），非本 skill 獨立問題 → 建議人工 **drop**
  - 2026-08-02: stalled **[rc=9 → drop]** — n=24 第 9 輪持平 (4H/5M/14neu/1pend)；最後一筆 run 為 2026-05-24，W28–W31 = 0/0/0/0。維持建議人工 **drop**

### TODO-004 — 拆 `final_decision` + `final_action` 兩欄 (full version)

- **created_in**: 3.18.0 plan out-of-scope + Codex round-2 review #1 follow-up
- **source_type**: out_of_scope
- **trigger_condition**: 下輪 REVIEW 用 final_action_modifier 重算 Pattern A/B 後,
  若仍需更乾淨的 verb/label 分離 (e.g. CANCEL 跟 EXECUTE 應該是 verb 不是 modifier)
- **target_action**: extractor schema 完全拆兩欄,audit downstream consumer
  (`event_index` / `render_event_index.py` / `verdict_rules.py` / REVIEW_PROMPT 引用點),
  bump major / minor
- **review_count**: 9
- **status**: **dropped (2026-06-28)** — modifier 欄 6 輪乾淨分離、final_action null 1.9%，輕量欄已足，無完整拆兩欄需求
  **（2026-07-31：drop 判準被 Pattern A 否證 — modifier 對真實 CANCEL 母體 recall 僅 24.7%，建議重新檢視，見 TODO-019）**
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-05-24: 3.18.1 已用輕量 modifier 欄 patch,先觀察 1-2 輪 REVIEW 看是否足夠
  - 2026-05-31: still_waiting — modifier 欄足夠:CANCEL/HOLD/EXECUTE/STAGED 乾淨分離,
    final_action null 1.6% (2/126)。暫不需完整拆兩欄,再觀察 1 輪
  - 2026-06-13: still_waiting — final_action null 1.5% (2/133),modifier 仍乾淨分離。
    輕量 modifier 欄持續足夠,不需完整拆兩欄
  - 2026-06-14: still_waiting — final_action null 2.1% (3/140),modifier 仍乾淨分離,輕量欄足夠
  - 2026-06-20: still_waiting **[stale rc=4]** — final_action null 2.1% (3/143)，modifier 4 週乾淨分離 → 建議 drop(輕量欄已足)
  - 2026-06-21: still_waiting **[stale rc=5]** — final_action null 2.0% (3/147)，modifier 乾淨分離維持 → 建議人工 drop(輕量欄已足，5 輪無需求)
  - 2026-06-28: stale **[rc=6 → drop]** — final_action null 1.9% (3/160)，modifier 6 輪持續乾淨分離 → 建議人工 drop(輕量欄已足)
  - 2026-07-19: dropped 維持 **[rc=7]** — final_action null 1.8% (3/163)，modifier 持續乾淨分離。可搬 Closed
  - 2026-07-31: **drop 判準被否證 [rc=8]** — final_action null 1.8% (3/164) 維持，但 REVIEW_2026-07-31 Pattern A 實測
    modifier 欄對**真實 CANCEL 母體 recall 僅 24.7%**(24/97)。原 drop 判準（null rate + 分離乾淨度）漏掉 recall 維度 →
    建議重新檢視；處置併入 **TODO-019**（改以 export decision verb 為母體，不必然需完整拆兩欄）
  - 2026-08-02: **superseded by TODO-019 [rc=9]** — final_action null 1.8% (3/167)。本輪 stance×verb cross-tab：HOLD→CANCEL **50/51**、BUY→EXECUTE 23/24、STAGED_ENTRY→STAGED 25/30 → 映射近乎確定性，**join 補 `execution_verb` 即可，不需完整拆兩欄**。建議併入 TODO-019 後 close

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
- **review_count**: 9
- **status**: **dormant/休眠 (2026-06-28)** — 殘量凍結老報告，7 輪無回推需求；待 TODO-002 類跨年比較有需求時才回填，期間不逐週追蹤
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-05-24: pre-V5 null_regime 33/112 (29%);79/112 (71%) 接到 phase0_cache OK
  - 2026-05-31: still_waiting — deep-dive macro_regime null 33/126 (26%);本週無回推需求
  - 2026-06-13: still_waiting — deep-dive macro_regime null 33/133 (24.8%);本週無回推需求
  - 2026-06-14: still_waiting — deep-dive macro_regime null 33/140 (23.6%);本週無回推需求
  - 2026-06-20: still_waiting **[stale rc=4]** — deep-dive macro_regime null 23.1% (33/143)，4 週無回推需求 → 建議 drop/休眠(待跨年比較才回填)
  - 2026-06-21: still_waiting **[stale rc=5]** — deep-dive macro_regime null 22.4% (33/147，殘量凍結在老報告)，無回推需求 → 建議休眠至跨年比較
  - 2026-06-28: stale **[rc=6 → 休眠]** — 殘量凍結老報告，6 輪無回推需求 → 建議人工休眠至跨年比較才回填
  - 2026-07-19: dormant 維持 **[rc=7]** — null 20.2% (33/163，分母增而殘量不變)。**新觀察**：Pattern E regime 分析因此少
    14 筆保守決策（該 null bucket cons-miss 71.4%），若回填可能改變 regime 排序（見 REVIEW_2026-07-19 §4 盲點 #6）
  - 2026-07-31: dormant 維持 **[rc=8]** — null 20.1% (33/164)。cons-miss 的 null bucket **73.3%**(11/15) 仍為 regime 排序
    第 2 高（Pattern F），回填仍可能改變排序結論；本輪無回推需求，維持休眠
  - 2026-08-02: dormant 維持 **[rc=9]** — null **19.8%** (33/167，殘量凍結、分母增)。cons-miss 的 null bucket **73.3%**(11/15) 仍為 regime 排序第 2 高；本輪無回推需求

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
- **review_count**: 8
- **status**: pending（**建議降級**：方向已 4 輪一致，改為「N≥40 時一次性確認後 close」，不再逐週追蹤）
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-05-31: News-decisive miss 48% (15/31),vs Fundamentals 35% (19/56) / Sentiment
    33% (3/9);News 主導的 HOLD miss 62%
  - 2026-06-13: still_waiting — News-decisive miss 56% (15/27 evaluable),N=31 仍 < 40 門檻
    (與上週持平);vs Fundamentals 36% / Technical 43% / Sentiment 33%
  - 2026-06-14: still_waiting — News-decisive miss 56% (15/27 eval),N=31 (<40,持平)。拆 active/
    conservative:News-active miss 27% vs News-conservative 69% → 高 miss 主要來自保守決策(與 Pattern A 同根)
  - 2026-06-20: still_waiting — News-decisive N=31 (<40)，miss 56% (15/27 eval)；News-conserv 11/16=69% vs News-active 4/11=36% → 與 Pattern A 同根，可能不需獨立 News 權重
  - 2026-06-21: still_waiting — News-decisive N=32 (<40)，miss 55.6% (15/27 eval)；News-conserv 11/16=68.8% vs News-active 4/11=36.4% → 持續支持「與 Pattern A 同根」假設,補到 N≥40 後若維持即可 close(毋須獨立 News 權重)
  - 2026-06-28: still_waiting — News-decisive N=33 (<40，+1)，miss 51.7% (15/29 eval)；News-conserv 58.8% vs News-active 36.4% → 持續同 Pattern A 根。差 7 筆到門檻
  - 2026-07-19: still_waiting — News-decisive N=**33**（3 週 **+0**，<40），miss 55.6% (15/27 eval)；
    News-conserv **66.7%** (10/15) vs News-active **41.7%** (5/12)。News-active 41.7% ≈ Technical 42.9% →
    **第 4 輪確認「與 Pattern B 保守性同根、非 News edge 衰減」**，毋須獨立 News 權重。建議降級為 N≥40 一次性確認後 close
  - 2026-07-31: **stalled [rc=7]** — N=**33** 第 4 輪 +0（<40 門檻）；miss 51.7% (15/29)；
    News-conserv **61.1%**(11/18) vs News-active **36.4%**(4/11)。方向第 5 輪一致（與保守性同根、非 News edge 衰減）→
    建議以現有 **N=33 直接 close**，毋須獨立 News 權重。樣本凍結根因見 TODO-021
  - 2026-08-02: stalled 維持 **[rc=8 → 建議以 N=33 直接 close]** — N=**33** 第 5 輪 +0；miss 51.7% (15/29)；News-conserv **61.1%**(11/18) vs News-active **36.4%**(4/11)。方向第 6 輪一致（與保守性同根、非 News edge 衰減），毋須獨立 News 權重

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
- **review_count**: 9
- **status**: in_progress（flip 13.5% 落 observe band,**四輪無漂移**；建議降頻為每 4 輪重跑一次）
- **last_check**: 2026-08-02
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
  - 2026-06-28: **ran [rc=6]** — 跨 15 snapshot 重跑：N=**206** transition、flip=27、flip_rate **13.1%** 仍落 10–20% observe band（與 06-20 的 13.4%、06-07 的 12% 一致，無漂移）→ 維持不加 provisional flag。續觀察：跌破 10% → close，破 20% → build_event_index 加 provisional
  - 2026-07-19: **ran [rc=7]** — 跨 18 snapshot：N=**237** transition、flip=**32**、flip_rate **13.5%**。序列 12.0%(06-07) → 13.4%(06-20) → 13.1%(06-28) → 13.5%(本輪)，**四輪穩定無漂移趨勢** → 維持不加 provisional flag。建議降頻為每 4 輪重跑一次（逐週重跑資訊增益已趨零）
  - 2026-07-31: **ran [rc=8]** — 跨 **20** snapshot：N=**259** transition、flip=**33**、flip_rate **12.7%**。
    序列 12.0%(06-07) → 13.4%(06-20) → 13.1%(06-28) → 13.5%(07-19) → **12.7%**(本輪)，**五讀全落 10–20% observe band
    且無漂移趨勢** → 建議 **close**（維持不加 provisional flag；Pattern 統計續只計 window_complete=100）
  - 2026-08-02: **ran [rc=9] → 建議 close** — 跨 **21** snapshot：N=**259**、flip=**33**、flip_rate **12.7%**，與上輪逐位相同（距上輪僅 2 天，無新完成窗口）。六讀 12.0→13.4→13.1→13.5→12.7→12.7 全落 10–20% observe band 且無漂移 → close，維持不加 provisional flag

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
- **review_count**: 6
- **status**: **stalled (2026-07-19)** — 強訊號 N=9 凍 4 輪，「等 N≥15 再 grid 精校」路徑失效。Rec 10 的 ±1.0% 止血值維持 active；改為「以現有 N=9 直接評或無限期擱置」，不再逐週追蹤
- **last_check**: 2026-08-02
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
  - 2026-07-19: **stalled [rc=4]** — 強訊號 N=**9** 第 4 輪持平 (1H/3M/5neu)，macro_delta null 已降至 5.6% (4/71，
    殘為 v1 protocol legit n/a) → 非 parser 問題，是**上游不產強訊號**（71 筆 digest 中 62 筆 neutral，多為弱訊號 by-design）。
    accumulating_data 模型失效 → 宣告 stalled（見 REVIEW_2026-07-19 §0.5 Rec 10 說明 + §3 #3）
  - 2026-07-31: stalled 維持 **[rc=5]** — 強訊號 \|delta\|>0.5 **N=9** 第 5 輪持平 (1H/3M/5neu)。
    macro_delta null 已降至 **5.3%**(4/75) → 再確認非 parser 問題；75 筆 digest 中 65 筆 neutral（弱訊號 by-design）。
    Rec 10 本輪建議 status → paused（metric 凍結），但 `NEWS_HIT_THRESHOLD_PCT = 1.0` **不 rollback**
  - 2026-08-02: stalled 維持 **[rc=6]** — 強訊號 \|delta\|>0.5 **N=9** 第 6 輪持平 (1H/3M/5neu)；macro_delta null **5.3%**(4/76)。Rec 10 本輪建議 status → paused（metric 凍結第 3 輪），`NEWS_HIT_THRESHOLD_PCT = 1.0` **不 rollback**

### TODO-012 — Rec 11 hot_zone_probe 活化驗收（決策層 Rec 尚未實測）

- **created_in**: REVIEW_2026-06-13 Section 4 系統盲點 #1 + Section 0.5 Rec 11 no_change
- **source_type**: accumulating_data
- **trigger_condition**: 2026-06-07 後累積 **N ≥ 5 筆** `macro_regime ∈ {RISK_ON, BULL}` 且
  `industry_top_30pct=true` 且 `final_score ∈ [0,+staged)` 的 deep-dive（即 Rec 11 規則應觸發的場景）
- **target_action**: 確認規則正確 fire — 該類標的 `hot_zone_probe=true`、`final_action=STAGED_ENTRY`、
  `position_size_pct ≤ 0.0015`(15bps)、與 decision_cap 互斥;並比對 Semis HOLD-miss / CANCEL-miss
  是否朝 <60% target 移動。資料源 `event_index.decisions[*].decision_content.hot_zone_probe`
- **review_count**: 6
- **status**: **ready — 根因查明，驗收路徑併入 TODO-016**（0 fire 非 regime dormant，而是 risk_flag 硬閘抑制 15/18 qualifying）
- **last_check**: 2026-08-02
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
  - 2026-07-19: **根因查明 [rc=4]** — TODO-015 instrumentation 落地，`hot_zone_qualifying`=**18**（跨 04-18~07-08，
    regime 全 RISK_ON/BULL）、`fired`=**0**、`suppressed_by_risk_flag`=**15**。**前 3 輪「regime 不對故正確 dormant」
    結論否證** — qualifying 場景常態發生，binding constraint 是 `mandatory_risk_flags` 硬閘。suppressed 子集
    decided miss **78.6%**(11/14)、avg runup +49.81% vs avg dd −2.31%。Rec 11 target metric（Semis HOLD-miss 64.3%、
    CANCEL 68.2%）4 輪皆為**未介入基線**，未達 >70% paused 門檻 → **不 paused**（不可 rollback 從未執行的規則）。
    本 TODO 收斂為 TODO-016 的驗收路徑
  - 2026-07-31: **ready 維持 [rc=5]** — qualifying=**18**、fired=**0**、suppressed_by_risk_flag=**15**（decided 14→15）。
    本輪改以**已實現 30d 報酬**重算：suppressed 子集(win100, N=14) avg **+26.77%** vs 全書基準 **+9.76%**；
    miss 子集(n=11) avg **+36.94%**、**100% 上漲** → 證據較上輪轉強。驗收路徑續併入 TODO-016
  - 2026-08-02: **⚠️ 前提被推翻 [rc=6]** — 查權威 export `investment/invest_logs/history.json` → `trades_this_session[].hot_zone_probe/eval`：**Rec 11 已 fire 2 次**（MU 2026-06-21 probe=true / STAGED / 15bps；NVDA 2026-07-08 eval=**fired** / STAGED / 15bps），非 index 顯示的 fired=0。兩次皆合規（`decision_cap_active=false`、position_size_pct=0.0015）。實績：MU ret **−19.86%** / dd −29.92%（miss，win100）、NVDA ret −1.65% / dd −6.91%（neutral，win83）→ 平均 **−10.76%**，與 suppressed 子集反事實 +26.77% **方向相反**。驗收路徑改為：先做 TODO-020 的 join（讀權威欄），再以 fired 子集實績評估（衍生 **TODO-023**）

### TODO-013 — 0–1 score band 內部結構不可見 (Pattern B 假設 2)

- **created_in**: REVIEW_2026-06-14 Section 4 系統盲點 + Pattern B 假設 2
- **source_type**: instrumentation_gap
- **trigger_condition**: instrumentation 落地後即可評估(非未來累積) — 加欄後下輪 REVIEW 用
  agent_score_stdev 拆 0–1 band 的 hit/miss
- **target_action**: `scripts/build_event_index.py` tuning_hooks 加 `agent_score_stdev`
  (4 lane agent score 標準差),分離「弱訊號 0–1」(低 stdev) vs「agent 高分歧 0–1」(高 stdev);
  若高分歧子集 miss 顯著高 → 候選在高 dispersion 時降倉或標 low-conviction
- **review_count**: 6
- **status**: **done (hypothesis refuted, 2026-06-28)** — agent_score_stdev 全樣本**三輪**一致否證；不實作「高 dispersion 降倉」。可搬 Closed
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-06-14: score 0–1 band n=68 (最大樣本),decided hit 48% (29H/31M) 近擲硬幣,
    vs 1–2 band 74% (32H/11M)。無法分離弱訊號 vs 高分歧兩種成因 — 缺 agent_score_stdev
  - 2026-06-20: **ready** — score|0-1| decided n=76 miss 50% (38/76) vs |1-2| 31% (14/45)。instrumentation 可即落地(非未來累積) → 優先處理
  - 2026-06-21: **EVALUATED → 假設否證** — `agent_score_stdev` 已落地(null 17/147)。0–1 band(N=82) 以中位 stdev 1.363 拆兩半:低 stdev(共識弱訊號) miss **56.8%**(25/44) vs 高 stdev(agent 高分歧) miss **40.6%**(13/32)。**與假設相反**:0–1 miss 來自共識弱訊號被 default HOLD(低 stdev 反而 miss 更高),非 agent 高分歧。「高 dispersion 降倉/標 low-conviction」候選**無證據支持,不實作**。併入 Pattern A,建議 status → done(refuted)
  - 2026-06-28: **CLOSED (refuted)** — 全樣本複驗方向穩定(低 stdev miss 59.5% > 高 stdev 40.5%)，假設持續否證。done，搬 Closed
  - 2026-07-19: **第 3 輪複驗方向穩定** — 0–1 band 以中位 stdev 1.225 拆半：低 stdev miss **63.3%**(19/30) >
    高 stdev **44.8%**(13/29)。假設穩定否證，維持 done。真因併入 Pattern B（共識弱正分被 default 觀望）
  - 2026-07-31: **第 4 輪複驗方向穩定 [rc=5]** — 0–1 band(N=63) 以中位 stdev 1.200 拆半：
    低 stdev miss **56.2%**(18/32) > 高 stdev **48.4%**(15/31)。假設持續否證，維持 done，可搬 Closed
  - 2026-08-02: **第 5 輪複驗方向穩定 [rc=6]** — 0–1 band N=77（stdev 已知 63），median stdev 1.200：低 stdev miss **56.2%**(18/32) > 高 stdev **48.4%**(15/31)，與上輪同值。維持 done(refuted)，可搬 Closed

### TODO-014 — Rec 11 regime guard 範圍重檢 (Pattern C：保守 miss 集中 SIDEWAYS 非 RISK_ON/BULL)

- **created_in**: REVIEW_2026-06-20 Section 2 Pattern C + Section 0.5 Rec 11 新觀察
- **source_type**: accumulating_data
- **trigger_condition**: SIDEWAYS regime 下 top30 × score∈[0,+staged) 的保守 miss 累積 **N ≥ 10**，
  且 RISK_ON/BULL 出現 ≥1 筆 qualifying scenario 作對照 (目前 SIDEWAYS 保守 miss N=3，RISK_ON N=0)
- **target_action**: 評估是否把 Rec 11 熱區鬆綁的 regime guard 從 {RISK_ON,BULL} 擴到含 SIDEWAYS;
  若 SIDEWAYS 保守 miss 持續 ≥60% 且 drawdown 仍小 → 候選改
  `investment/investment_protocol_v5_0.md` Rec 11 regime guard 條件。**嚴禁在 N<10 時動 Rec 11**
- **review_count**: 4
- **status**: **建議 close（2026-07-19）** — 全樣本再證 regime guard 方向正確，不擴 SIDEWAYS；驗收路徑已併入 TODO-012 → TODO-016
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-06-20: 06-07 後保守 miss (MRVL RISK_OFF / MU·ALAB·ARM SIDEWAYS) **0 筆在 RISK_ON/BULL**，
    但 Rec 11 只在 RISK_ON/BULL 觸發 → regime guard 可能把規則限制在「問題不發生的 regime」。N=4 太小，列推測
  - 2026-06-21: **全樣本否證** — conservative(HOLD/CANCEL) miss by regime：BULL **77.8%**(7/9) > RISK_ON **55.6%**(15/27) > VOLATILE 55.6%(5/9) > **SIDEWAYS 38.5%**(5/13)。保守 miss 在 BULL/RISK_ON 最嚴重、SIDEWAYS 最低 → 06-07 後 SIDEWAYS 那 3 筆是 6 月回檔小樣本 artifact。Rec 11 regime guard={RISK_ON,BULL} **方向正確**,**不應**擴到 SIDEWAYS(SIDEWAYS 保守反而較準,鬆綁增風險)。本 TODO 收斂為 TODO-012 驗收路徑
  - 2026-07-19: **再證 → 建議 close** — conservative miss by regime：BULL **83.3%**(5/6) > null 71.4%(10/14) >
    VOLATILE 55.6%(5/9) > RISK_ON **47.4%**(9/19) > SIDEWAYS **27.3%**(3/11)。排序與 06-21 一致，SIDEWAYS 續為最低 →
    regime guard={RISK_ON,BULL} 方向確認正確。真正 binding constraint 是 risk_flag（TODO-016），非 regime 範圍
  - 2026-07-31: **三輪再證 → 建議 close [rc=3]** — cons-miss by regime(win100)：BULL **77.8%**(7/9) > null 73.3%(11/15) >
    VOLATILE 55.6%(5/9) > RISK_ON 53.3%(16/30) > RISK_OFF 33.3%(2/6) > **SIDEWAYS 20.0%**(4/20)。
    排序與 06-21 / 07-19 一致，regime guard={RISK_ON,BULL} 方向確認正確，不擴 SIDEWAYS
  - 2026-08-02: **四輪再證 → 建議 close [rc=4]** — cons-miss by regime(win100)：BULL **77.8%**(7/9) > null 73.3%(11/15) > VOLATILE 55.6%(5/9) > RISK_ON 53.3%(16/30) > RISK_OFF 33.3%(2/6) > **SIDEWAYS 20.0%**(4/20)，排序與 06-21 / 07-19 / 07-31 一致。惟須併記反向證據：Rec 11 實際 fire 的 2 筆皆在 RISK_ON（正確 regime 內）**且皆虧損** → regime guard 方向正確不等於熱區鬆綁有效（見 TODO-023）

### TODO-015 — surface `hot_zone_probe` + `hot_zone_eval`（Rec 11 評估結果 instrumentation）

- **created_in**: REVIEW_2026-06-28 Section 3 #2 + Section 4 盲點 #1（TXN 06-22 場景暴露）
- **source_type**: instrumentation_gap
- **trigger_condition**: 下次 deep-dive run 後 event_index 帶非 null 的 `hot_zone_eval` / `hot_zone_eval_derived`
- **target_action**: ✅ 已實作（V4.54.2）— Phase 5 export 強制寫 `hot_zone_eval` enum
  (`investment_protocol_v5_0.md` Rec 11 段 + export JSON)；`deep_dive_extractor.py` 讀權威值並對缺欄歷史報告
  反推 `hot_zone_eval_derived`（fired/suppressed_by_risk_flag/suppressed_by_cap/not_qualifying/qualifying_unexplained）；
  `validate_session_export.py` §11b 強制 `probe=true ⟺ eval=fired`；`replay_rec11.py` 改讀 eval 不再 assume-pass
- **review_count**: 3
- **status**: **done — 首輪即產出決定性成果**（揭穿 Rec 11 0-fire 真因）。衍生 TODO-016（flag 明細）+ TODO-017（`qualifying_unexplained`=1）
  **（2026-07-31 建議重開為 `in_progress`：權威欄 `hot_zone_eval` 覆蓋率為 0，交付物實際未生效 — 見 TODO-020）**
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-06-28: 實作驗證 — 反推 TXN 06-22 = `suppressed_by_risk_flag`（score 0.047∈[0,0.8) × RISK_ON × Semis top30
    但 Valuation SELL −3.0 + Burry WARNING）= 規則有評估且正確抑制，非「未評估」。MU/MSFT/PLTR = `not_qualifying`。
    extractor 25 test 通過（news_digest 1 筆 pre-existing fail 與本案無關）
  - 2026-07-19: **成果驗收** — 全 163 筆 deep-dive 帶 `hot_zone_eval_derived`：not_qualifying 145 /
    **suppressed_by_risk_flag 15** / not_evaluated_pre_rec11 2 / **qualifying_unexplained 1** / **fired 0**。
    首輪即推翻前 3 輪「Rec 11 正確 dormant」誤判 → 衍生 **TODO-016**（surface flag 明細 + 軟/硬分級）。
    `qualifying_unexplained`=1（MU 07-08）依本 TODO 預設判準 = 真 bug → 衍生 **TODO-017**
  - 2026-07-31: **⚠️ 需重開 [rc=2]** — 權威欄 `hot_zone_eval` **0/164 非 null**（`hot_zone_probe` 亦 0/164），
    含 V4.54.2 之後的最新 run（`2026-07-31 MU`, ver=V5.0）。根因：`validate_session_export.py:387` 的警告條件
    `ver != "V5.0"` 對現行 export **恆為 False**（history 版本戳 V5.0×75）→ gate 從未生效。
    上輪驗收只看 `hot_zone_eval_derived` 覆蓋率(164/164)，但 derived 是對歷史報告的反推、必然 100%，
    對「export 有沒有寫」**零資訊量** → status 建議 done → **in_progress**，處置見 **TODO-020**
  - 2026-08-02: **⚠️ 診斷更正 — 交付物實際成功 [rc=3]** — 上輪「Phase 5 export 未寫出 `hot_zone_eval`」的判定**錯誤**。查 `history.json`：`trades_this_session[].hot_zone_probe` 自 **2026-06-13** 起 **37 筆非 null**、`hot_zone_eval` 自 **2026-07-08** 起 **7 筆非 null**（not_qualifying×4 / suppressed_by_cap×2 / **fired×1**）。validator 亦已生效（`validate_session_export.py:346` 硬性要求 eval 必填、`:1006` 強制 `fired ⟺ probe`）。event_index 的 0/167 純為**讀取路徑錯層**（extractor 刮 MD、export 寫 JSON）→ 本 TODO 交付物成立，處置全數移交 **TODO-020**

### TODO-016 — surface `suppressing_risk_flags` + Rec 11 risk_flag 軟/硬分級（Rec 11 0-fire 死結）

- **created_in**: REVIEW_2026-07-19 Section 2 Pattern A + Section 3 #1/#2
- **source_type**: instrumentation_gap（第一段）→ 決策層 Rec（第二段）
- **trigger_condition**: 第一段（instrumentation）**立即可做**，非未來累積；第二段（protocol 改動）需第一段落地後、
  `tuning_hooks.suppressing_risk_flags` 非 null 覆蓋 ≥ 15 筆 `suppressed_by_risk_flag` 樣本
- **target_action**:
  - (a) `scripts/extractors/deep_dive_extractor.py` 推導 `hot_zone_eval_derived='suppressed_by_risk_flag'` 時
    同時寫觸發 flag 名稱清單到 `tuning_hooks.suppressing_risk_flags`；`scripts/build_event_index.py` 透傳
  - (b) 據 (a) 結果切軟/硬分界後，改 `investment/investment_protocol_v5_0.md` Rec 11 熱區例外段：
    硬閘（systemic / proceed_to_phase3=false / Auto REJECT / burry≤1）維持 100% 否決；
    軟閘（valuation warning / 單一 agent SELL / burry WARNING）不再否決 probe，但 probe 上限 15bps → **8bps**
  - **嚴禁**跳過 (a) 直接改 (b)
- **review_count**: 2
- **status**: pending
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-07-19: TODO-015 instrumentation 落地後首次可見 — `hot_zone_qualifying` N=**18**、`fired`=**0**、
    `suppressed_by_risk_flag`=**15**。前 3 輪「regime 不對所以正確 dormant」結論**否證**（qualifying 場景常態發生、
    regime 全為 RISK_ON/BULL）。suppressed 子集 decided miss **78.6%**(11/14)、avg max_runup **+49.81%** vs
    avg max_drawdown **−2.31%**、worst dd −8.74%；3 筆正確抑制（NEE −7.80% / NOK −12.33% / TXN −14.52%）。
    以 8bps 計，3 筆全錯的組合層損失約 −1.2bps，遠小於錯過 11 筆 +50% 之機會成本
  - 2026-07-31: **ready，(a) 段仍未動 [rc=1]** — `tuning_hooks.suppressing_risk_flags` **0/164 存在**。
    本輪以已實現報酬重算，證據轉強且定位更精確：suppressed 子集(N=14) avg **+26.77%**（基準 +9.76% 的 2.7 倍）、
    miss 子集(n=11) avg **+36.94%** 且 100% 上漲、正確抑制的 3 筆 avg **−10.53%**。
    **但 Pattern B 同時顯示 CANCEL 母體整體有鑑別力**（avg 已實現 +6.86% < 全書基準 +9.76% < EXECUTE +11.64%）→
    (b) 段鬆綁**必須限縮在 qualifying 熱區窄口徑**，不可外推為全域放寬 CANCEL
  - 2026-08-02: **(a) 仍未動；(b) 前提須先複驗 [rc=2]** — `tuning_hooks.suppressing_risk_flags` 仍 **0/167**。**(b) 段立論基礎動搖**：`suppressed_by_risk_flag=15` 為影子值，其中**唯一有權威值可查的 1 筆（NVDA 2026-07-08）權威值為 `fired`、不是 suppressed**，其餘 14 筆全落在 2026-04~06 的 MD-only 期、**永久不可查核**。→ 須先完成 TODO-020 的 join，用權威欄重算 suppressed 母體（N≥10）後才可進入 (b)。**嚴禁**在權威重算前改 protocol

### TODO-017 — `qualifying_unexplained`=1（MU 2026-07-08）+ validator §11b 漏洞

- **created_in**: REVIEW_2026-07-19 Section 3 #3 + Section 4 盲點 #1
- **source_type**: instrumentation_gap
- **trigger_condition**: **立即可做** — 依 TODO-015 定義，`qualifying_unexplained > 0` 即為真 bug
- **target_action**: 查 `reports/20260708_MU.md`（score 0.381 ∈ [0,0.8) × RISK_ON × Semis top30 × final_action=HOLD）
  為何 Phase 5 export 未寫 `hot_zone_eval`；補 `investment/scripts/validate_session_export.py` §11b —
  現行只強制 `probe=true ⟺ eval=fired`，**未強制「qualifying 場景必須寫 eval」** → 應加此 gate
- **review_count**: 2
- **status**: pending
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-07-19: deep-dive 163 筆中 `qualifying_unexplained`=1（MU 07-08，verdict=hit）。其餘分布
    not_qualifying 145 / suppressed_by_risk_flag 15 / not_evaluated_pre_rec11 2 / fired 0
  - 2026-07-31: still_waiting，未動 **[rc=1]** — `qualifying_unexplained` 仍為 1 筆（MU 07-08）。
    與 TODO-015 同根（權威欄 0% 覆蓋使影子值無從裁決究竟是 export 漏寫還是影子邏輯誤判）→
    建議併入 **TODO-020** 一次處理（validator §11b 同時補 version gate + qualifying gate）
  - 2026-08-02: **已可裁決 — 非 export bug [rc=2]** — 權威 export 對 MU 2026-07-08 寫的是 **`suppressed_by_cap`**（probe=false、position_size_pct=0.0）。`qualifying_unexplained` 是**影子邏輯誤判**，不是「protocol 未評估」。另 validator 已在 `validate_session_export.py:346` 對 engine-scored deep-dive 硬性要求 `hot_zone_eval` 必填 → 原「補 qualifying gate」需求大致已滿足。處置併入 TODO-020（join）+ **TODO-022**（修影子邏輯）

### TODO-018 — REVIEW_TODO schema 加 `expected_rate_per_week`（accumulating_data 樣本枯竭自動偵測）

- **created_in**: REVIEW_2026-07-19 Section 2 Pattern G + Section 4 盲點 #4
- **source_type**: out_of_scope
- **trigger_condition**: 下次有人動 REVIEW_TODO schema 時一併做（軟條件）
- **target_action**: 本檔 Schema 區段加選填欄 `expected_rate_per_week`；REVIEW_PROMPT.md Step -1 加規則：
  accumulating_data item 連續 3 輪 N 零成長 → 自動標 `stalled`，不再靠人工在 evidence 註記
- **review_count**: 2
- **status**: pending
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-07-19: 三個 accumulating_data TODO 同時樣本凍結 — TODO-003 momentum N=24 凍 **7 輪**、
    TODO-011 news 強訊號 N=9 凍 **4 輪**、TODO-009 News-decisive N=33 三週 +0。絕對 N 門檻缺上游產出率健康檢查
  - 2026-07-31: **ready，證據轉強 [rc=1]** — 本輪 **4 個** accumulating_data item 同時凍結
    （TODO-003 凍 8 輪 / TODO-009 凍 4 輪 / TODO-011 凍 5 輪 / TODO-012 樣本不增）。
    Pattern D 查明共同根因為**決策層產出率崩落**（deep-dive W29–W30 = **0** run，W16–W18 曾 31–34/週），
    非四個獨立上游問題 → 與 **TODO-021** 同源，建議一併設計
  - 2026-08-02: ready 維持 **[rc=2]** — 4 個 accumulating item 續凍（TODO-003 凍 9 輪 / TODO-009 凍 5 輪 / TODO-011 凍 6 輪 / TODO-012 樣本不增）。本輪另發現同源機制缺陷：tripwire 的「連續 N 週」以 REVIEW 輪次計數，本輪距上輪僅 2 天卻會累加計數 → 衍生 **TODO-024**，建議與本 item、TODO-021 一併設計

### TODO-019 — CANCEL 母體定義錯誤（Rec 11 target metric 測在 24.7% 偏樣本）

- **created_in**: REVIEW_2026-07-31 Section 2 Pattern A + Section 3 #1
- **source_type**: instrumentation_gap
- **trigger_condition**: **立即可做**，非未來累積 — 兩份資料皆已存在（`investment/invest_logs/history.json` ↔ `event_index`）
- **target_action**:
  - `scripts/build_event_index.py` join 階段引入 history.json 的 `final_action`（execution **verb**），
    寫入新欄 `decision_content.execution_verb`；**不覆蓋**現有 `final_action`（MD 解析出的 **stance**）
  - REVIEW 的 CANCEL / EXECUTE / STAGED metric 一律改讀 verb 欄；`ADJUSTMENT_LEDGER.md` Rec 11
    的 target_metric 量測口徑同步改寫
  - 重算後複驗 TODO-001 當年「CANCEL miss ≥70% 故應放寬」的歷史結論是否成立
- **review_count**: 1
- **status**: pending
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-07-31: index CANCEL bucket（MD `final_action_modifier` 口徑）n=**24**，真實 CANCEL 母體
    （export verb 口徑）n=**97**，涵蓋率 **24.7%**，且偏誤單向 — 被抓到的 24 筆 miss **70.8%**、
    未被抓到的 73 筆 miss **42.5%**。正確母體 CANCEL-miss = **49.5%**(48/97) < 60% target，
    而表面讀數 70.8% 恰跨過 Rec 11 的 `>70% → paused` 跳閘線。
    根因：MD 標頭為兩軸語意 `| Final Decision | HOLD（action: CANCEL） |`（`reports/20260731_MU.md:12`），
    extractor 抽 stance、export 存 verb，**兩邊欄位同名 `final_action`**。
    TODO-004 於 2026-06-28 以「輕量 modifier 欄已足」drop，判準只看 null rate(1.8%) 與分離乾淨度，
    **未驗證 modifier 對真實 CANCEL 母體的 recall** → 該 drop 判準本輪被否證
  - 2026-08-02: ready，證據更精確 **[rc=1]** — 重測：verb-CANCEL n=**102**、MD-CANCEL n=**24**、recall **23.5%**；captured miss **70.8%**(17/24) vs uncaptured **43.1%**(31/72)；真實 CANCEL-miss **50.0%**(48/96)。新增 stance×verb cross-tab 證明映射近乎確定性（HOLD→CANCEL 50/51）→ **join 補 `execution_verb` 即可**，TODO-004 的完整拆欄不需要。另：按 verb 拆分的已實現報酬顯示 CANCEL 母體**整體仍有鑑別力**（CANCEL +6.95% < 全書 +9.76% < EXECUTE +11.29% < STAGED +17.63%）→ 熱區鬆綁必須限縮窄口徑，不可外推全域放寬。**與 TODO-020 為同一次 join 修改，建議一起做**

### TODO-020 — `hot_zone_eval` 權威欄 0/164 覆蓋 + validator §11b version gate 恆不觸發

- **created_in**: REVIEW_2026-07-31 Section 2 Pattern E + Section 3 #4 + Section 4 盲點 #1
- **source_type**: instrumentation_gap
- **trigger_condition**: **立即可做** — 缺漏可由 history.json 版本戳分布直接證明
- **target_action**:
  - `investment/scripts/validate_session_export.py:387` 的 `ver != "V5.0"` 條件改為對現行 export 生效
    （以 `export_date >= '2026-06-28'`（TODO-015 上線日）或 `ver` 前綴比對 `V5`），並確認 Phase 5 export
    路徑**實際寫出** `hot_zone_eval`
  - 併入 TODO-017 的 gate：**qualifying 場景必須寫 `hot_zone_eval`**（現行 §11b 只強制 `probe=true ⟺ eval=fired`）
  - TODO-015 status 由 `done` 改回 `in_progress`（其唯一交付物覆蓋率為 0）
- **review_count**: 1
- **status**: pending
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-07-31: `decision_content.hot_zone_eval` **0/164 非 null**、`hot_zone_probe` **0/164 非 null**，
    含 V4.54.2 之後的最新 run（`2026-07-31 MU`, ver=V5.0）。history.json 版本戳分布：
    V4.5×1 / V4.6×21 / V4.8×73 / **V5.0×75** / null×8 → 現行 export 恆為 `"V5.0"`，
    故 `ver != "V5.0"` 恆為 False，警告**永不觸發**。
    MU 07-31 的 `bias_notes` 以中文散文記錄了熱區評估（「熱區 probe 因 regime=RISK_OFF 自動 dormant」）
    → 評估**有發生**，只是沒寫進結構化欄位。
    驗收 TODO-015 時只檢查 `hot_zone_eval_derived` 覆蓋率(164/164)，但 derived 是對歷史報告的反推、
    必然 100%，對「export 有沒有寫」零資訊量 → 所有熱區結論（含 Pattern C / TODO-016）目前
    只建立在影子重算上，`qualifying_unexplained`(MU 07-08) 無從裁決
  - 2026-08-02: **⚠️ target_action 須改寫 [rc=1]** — 0/167 覆蓋成立，但**根因不是 export 未寫、也不是 validator gate 失效**：export 自 2026-06-13（probe）/ 2026-07-08（eval）起已寫進 `history.json` → `trades_this_session[]`，validator `:346` / `:1006` 亦已生效。真因是 **event_index 讀錯來源** — `scripts/extractors/deep_dive_extractor.py:506-552` 以 regex 刮 **MD 報告全文**（MD 並未複述該欄），而 `scripts/build_event_index.py` **全檔從不開啟 history.json**（全 repo 僅 `scripts/kill_trigger_monitor.py` 讀它）。→ 改寫後的 target_action：在 build_event_index 的 join 階段讀 history.json，把 `hot_zone_eval` / `hot_zone_probe` / `hot_zone_probe_tier` / `position_size_pct` 寫入 `decision_content`（權威優先、缺值才 fallback 影子），MD regex 保留為 legacy fallback；同 join 順帶補 `execution_verb`（TODO-019）

### TODO-021 — 決策層產出率崩落監控（deep-dive W29–W30 = 0 run）

- **created_in**: REVIEW_2026-07-31 Section 2 Pattern D + Section 4 盲點 #3
- **source_type**: out_of_scope（流程層）
- **trigger_condition**: 與 TODO-018 的 `expected_rate_per_week` 同源，建議一併設計（軟條件）
- **target_action**:
  - 在 REVIEW Step -1 加上游產出率健康檢查：對每個 source 計近 4 ISO 週 run 數，
    連續 2 週為 0 → 該 source 的 accumulating_data item 自動標 `stalled`，不再逐週 still_waiting
  - 與 TODO-018 合併實作於 `REVIEW_PROMPT.md` Step -1 + `REVIEW_TODO.md` Schema 區段
- **review_count**: 1
- **status**: pending
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-07-31: deep-dive 每 ISO 週 run 數 W16–W18 為 32/34/31，W28–W31 降為 **3/0/0/1**（降幅 >90%）。
    分層對照：自動層（thematic-screener 3/3/5/3、news-digest 3/1/2/2、sector-scan 3/1/2/2）產出穩定；
    需人工觸發 Claude turn 的層（deep-dive / momentum-screen / theme-detector / earnings-analyzer）近 3 週幾近歸零。
    → TODO-003(N=24 凍 8 輪) / TODO-009(N=33 凍 4 輪) / TODO-011(N=9 凍 5 輪) / TODO-012(qualifying 不增)
    **同時**停滯並非四個獨立上游問題，而是同一個 production-rate 問題
  - 2026-08-02: still_waiting — **部分回復 [rc=1]** — deep-dive W28–W31 = 3/**0**/**0**/**4**（MU 07-31 + MSFT/MU/PLTR 08-02），「連 2 週為 0」狀態解除。但 momentum-screen（最後 run 2026-05-24）/ theme-detector / earnings-analyzer 仍 W28–W31 全 0；自動層（thematic-screener 3/3/5/4、news-digest 3/1/2/3、sector-scan 3/1/2/2）續穩 → 分層對照結論維持

### TODO-022 — `hot_zone_eval_derived` 影子欄與權威 export 欄 3/3 不符 → 降級為 fallback-only

- **created_in**: REVIEW_2026-08-02 Section 2 Pattern A + Section 3 #2
- **source_type**: instrumentation_gap
- **trigger_condition**: **立即可做**，非未來累積 — 兩份資料皆已存在（`investment/invest_logs/history.json` ↔ `event_index`）；
  依賴 TODO-020 的 join 先落地（權威值須先讀得到）
- **target_action**:
  - event_index 中權威 `hot_zone_eval` 存在時，REVIEW 統計**一律不使用** `hot_zone_eval_derived`；
    加 `hot_zone_eval_source: authoritative|shadow` 標記，derived 僅對 2026-07-08 之前的列生效
  - 修 `scripts/extractors/deep_dive_extractor.py:538-584` 影子邏輯的兩個已知誤判：
    (1) cap 抑制被歸為 `qualifying_unexplained`（MU 2026-07-08，權威值 `suppressed_by_cap`）；
    (2) 已 fire 被歸為 `suppressed_by_risk_flag`（NVDA 2026-07-08，權威值 `fired`）
  - 加一致性 assert：權威與影子不一致時 event_index 輸出 warning 計數，REVIEW Step 0 必讀
  - 2026-04~06 的 14 筆不可查核 `suppressed_by_risk_flag` 標為 `unverifiable`，
    不可再作為決策層改動的唯一依據
- **review_count**: 0
- **status**: pending
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-08-02: 權威 vs 影子逐筆比對 7 筆（權威欄 2026-07-08 上線後全部）：
    PLTR 07-08 `suppressed_by_cap` vs 影子 `not_qualifying` ✗；MU 07-08 `suppressed_by_cap` vs
    `qualifying_unexplained` ✗；NVDA 07-08 **`fired`** vs `suppressed_by_risk_flag` ✗；
    07-31 MU / 08-02 MU·MSFT·PLTR 四筆 `not_qualifying` 一致 ✓。
    **3 筆「熱區真有評估動作」的列上影子 3/3 全錯，4 筆一致的全是 trivially-correct 的 `not_qualifying`**。
    後果：5 輪 REVIEW 的「Rec 11 fired=0」與 TODO-016 (b) 的立論全建立在錯誤影子值上

### TODO-023 — Rec 11 `fired` 子集實績追蹤（反事實 vs 實測分歧）

- **created_in**: REVIEW_2026-08-02 Section 2 Pattern D + Section 3「累積後再評估」#2
- **source_type**: accumulating_data
- **trigger_condition**: `hot_zone_eval='fired'` 樣本累積 **N ≥ 5**，且跨 **≥2 個 regime 段**（目前 N=2，皆 RISK_ON）
- **target_action**: 對照兩組數字判斷 TODO-016 (b) 該不該做 —
  (a) `suppressed` 子集的**反事實**已實現報酬（現 N=14，avg **+26.77%**，全書基準 +9.76%）；
  (b) `fired` 子集的**實測**報酬（現 N=2，avg **−10.76%**）。
  若 N≥5 後 (b) 續顯著低於 (a)，則 (a) 的超額報酬應判為選擇效應（不含滑價／實際進場時點／
  持有期間回撤觸發停損），**不足以支持鬆綁 risk_flag**；反之才 promote TODO-016 (b)
- **review_count**: 0
- **status**: pending
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-08-02: Rec 11 實際 fire 2 筆（皆合規：STAGED + 恰好 15bps + `decision_cap_active=false`）—
    MU 2026-06-21 ret **−19.86%** / max_dd **−29.92%**（verdict=miss, win100）；
    NVDA 2026-07-08 ret **−1.65%** / max_dd −6.91%（verdict=neutral, win83）。
    組合層影響約 −3.0bps 與 −0.2bps（15bps 上限如設計般 bound 住下檔）。
    N=2 屬 `[推測]` 層級不下結論，但與 suppressed 子集反事實 +26.77% **方向相反**，
    須在 TODO-016 (b) 動 protocol 前解決

### TODO-024 — tripwire 計數器與 REVIEW 觸發頻率解耦

- **created_in**: REVIEW_2026-08-02 Section 0.5 Rec 7 說明 + Section 3 #4 + Section 4 盲點 #5
- **source_type**: out_of_scope（REVIEW 機制層）
- **trigger_condition**: 與 TODO-018 / TODO-021 同屬 REVIEW_PROMPT Step -1 機制層，建議一併設計（軟條件）
- **target_action**:
  - `REVIEW_PROMPT.md` Step 0 加規則：所有「連續 N 週」tripwire（Rec 7 asymmetry、Rec 10 no_change、
    TODO stalled 判定）的計數，只在**距上次計數 ≥7 天且期間有新完成窗口**時 +1；
    同批樣本重測不累加
  - `ADJUSTMENT_LEDGER.md` Rec 7 `standing_monitor` 加註上述定義 ＋ 把量測口徑書面固定為
    **win100 全 deep-dive**（避免全窗口 13.4pp / CANCEL 母體 23.0pp 的口徑漂移造成假跳閘）
- **review_count**: 0
- **status**: pending
- **last_check**: 2026-08-02
- **evidence**:
  - 2026-08-02: 本輪距上輪 REVIEW 僅 **2 天**，13 筆新記錄中 deep-dive 4 筆全 pending，
    無新完成窗口 → Rec 7 gap **13.2pp** 與上輪**逐位相同**（top30 43/97、not30 14/45）。
    若機械累加，Rec 7 會在 5 天內走完「連續 3 週 <15pp」的 paused 計數器；
    Rec 10 no_change 計數亦同樣受影響


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
