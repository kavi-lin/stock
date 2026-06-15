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
  - 2026-05-31: improved/maintained — STAGED_ENTRY miss 15% (4/26)、EXECUTE miss 20% (2/10)、整體 deep-dive hit 50.8% (64/126)，三 metric 全達標。continue。

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
  - 2026-05-31: maintained — deep-dive final_action null 1.6% (2/126)，遠低於 30% 門檻。continue。

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
  - 2026-05-31: **regressed** — macro_delta null 回升 35% (14/40)，超過 30% 門檻且高於上週 27.3%。非 patch 失效，是新增 v2 digest 帶進未涵蓋寫法。**不 rollback**（會更糟），建議 continue + audit 14 筆 null 找新 form（TODO-008 ready）；若下週仍 ≥30% 再 paused 重設計 parser。
  - 2026-05-31 (TODO-008 audit, applied_version 3.40.1): audit 14 筆 null → 找到 4 種未涵蓋 form（label 後直接 bold 無 separator / `**` 包 label / 空格分詞 + 大小寫 / `:` 後 bold number）+ 短 form `Macro Δ`。**把 10-pattern ladder 換成單一 tolerant regex**（label 變體 + backtick/bold wrapper + 選擇性 `:`/`=` + IGNORECASE）。實測 null **35% → 2.5%** (14→1)，唯一殘留 2026-04-15 是 news_protocol_v1 無 delta 概念之 legit n/a。previously-good 值零 regression。status 回 **active (resolved)**，下週 REVIEW 確認維持。

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
  - 2026-05-31: improved — sub_industry_heat 非 null deep-dive 100% (126/126)，達標 ≥80%。但 heat asymmetry **未證實**：top30 miss 44% vs not30 30%，gap 14pp <15pp 目標（連 2 週 <15pp，見 TODO-007；再 1 週觸發 paused）。continue 累積 not30 樣本。

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
  - 2026-05-31: maintained — industry_rollup 30 buckets (≥5)，adjustment_ledger_active 反映 6 active entries，本週 REVIEW Section 1.5 + Pattern B 已引用 rollup。continue。

---

## Rec 10 — news-digest verdict index-level hit threshold（TODO-011 止血）

- **applied_date**: 2026-05-31
- **applied_version**: 3.40.3
- **rec_source**: REVIEW_2026-05-24 盲點 #3 + REVIEW_2026-05-31 Section 4 盲點（連兩週列盲點）
- **hypothesis**: `verdict_news_digest` 用單股設計的 `HIT_THRESHOLD_PCT=2.0` 評 SPY 市場級 call。SPY 窗口內幾乎不動 ±2% → 強訊號全壓 neutral → news-digest hit_rate 結構性 0%（n=40 中 hit 0）。
- **target_metric**:
  - news-digest `verdict.label=='hit'` 樣本 > 0（baseline 0/40）
  - 不製造假 miss（sub-1% SPY 雜訊不應翻成反向 miss）
- **files_changed**:
  - `scripts/verdict_rules.py` — 新增 `NEWS_HIT_THRESHOLD_PCT = 1.0`；`verdict_news_digest` 改用之（deep-dive 2.0% 不動）
- **smoke_result（3.40.3 實測）**:
  - news-digest verdict: hit **0 → 1**（2026-05-14 看空 SPY −1.93%）/ miss 2 / neutral 35 ✓
  - 7 筆強訊號驗算 ±1.0% 最優：救回 05-14，不像 ±0.5% 把 05-16/17/23 sub-1% 雜訊誤判成 miss
- **rollback_plan**: `verdict_news_digest` 改回 `HIT_THRESHOLD_PCT`，移除常數
- **status**: active（止血值；N≥15 強訊號後精校 — 見 TODO-011）
- **scope_note**: **純回測 verdict 標籤規則，不影響 investment_protocol 任何決策**。零下單風險。
- **evaluation_history**:
  - 2026-05-31: smoke 達標（hit 0→1）。下週 REVIEW 看強訊號累積數,N≥15 用 grid 精校 threshold 值。

---

## Rec 9 — verdict surface max_drawdown_pct / max_runup_pct（TODO-005）

- **applied_date**: 2026-05-31
- **applied_version**: 3.40.1
- **rec_source**: REVIEW_2026-05-31 Section 4 系統盲點 #1 + TODO-005（Pattern A/B 上線驗收 blocker）
- **hypothesis**: verdict 只標 hit/miss 看結算日 return_pct，不看 path。HOLD/CANCEL「miss」無法分辨「平順上漲真錯過」vs「中途深 drawdown，caution 合理」。rollup `avg_miss_return_pct` 對所有 miss 不分方向混算（HOLD-miss 正值 + BUY-miss 負值）→ 出現無法解讀的負均值。surface drawdown 後 Pattern A/B threshold Rec 才能定量驗收。
- **target_metric**:
  - `event_index.decisions[?source=='deep-dive'].verdict.max_drawdown_pct / max_runup_pct` 非 null（committed window）
  - `industry_rollup[*].avg_miss_drawdown_pct / worst_miss_drawdown_pct` 出現 → 下週 REVIEW 可分辨避損
- **files_changed**:
  - `scripts/build_event_index.py` — `compute_reality_for_ticker` 加 `max_runup_pct`/`max_drawdown_pct`（從 price_at_decision 換算）；deep-dive verdict 注入兩欄；`_build_industry_rollup` miss 區聚合 `avg_miss_drawdown_pct`/`worst_miss_drawdown_pct`
- **smoke_result（3.40.1 實測）**:
  - deep-dive miss 50 筆全帶 max_runup_pct/max_drawdown_pct ✓
  - **解開負 avg_miss_return 之謎**：Semiconductors miss avg_ret **+33.86%** vs avg_dd 僅 **-3.26%**（worst -14.31%）→ 真錯過上漲，caution 不成立，**H1 確認**。負 return bucket（Renewable/Banks/IPP）avg_ret≈avg_dd 同量級負 → 是 BUY/STAGED miss（買了跌）非 HOLD 避損，方向混算 artifact 已分離 ✓
- **rollback_plan**: 移除新增欄位即可，label 邏輯未動（純 instrumentation）
- **status**: active
- **evaluation_history**:
  - 2026-05-31: smoke 達標。**解鎖 TODO-001/002** — drawdown 資料證實 semis HOLD/CANCEL miss 是真錯過非避損；下週 REVIEW 可 promote score 0–1 + top30 entry-bias 為正式決策 Rec（本週照紀律不改 protocol threshold）。

---

## Rec 11 — 熱區保守性鬆綁：正分模糊區 × top30 × 多頭 → HOLD 降小倉 probe（TODO-001+002）

- **applied_date**: 2026-06-07
- **applied_version**: 3.41.0
- **rec_source**: REVIEW_2026-06-07 Section 3 #1+#2（合併 Pattern A HOLD-miss + Pattern B CANCEL-miss）；TODO-001 + TODO-002 promoted
- **⚠️ scope**: **本 ledger 首個 investment_protocol 決策層 Rec**（Rec 1-10 皆 parser/verdict/instrumentation，零下單影響）。本 Rec **改 deck decision band → 影響實際 final_decision / position_size**。風險等級高於既有所有 Rec，故 target_metric 退步門檻嚴、首兩週加嚴觀察。
- **hypothesis**: 正分模糊區 HOLD band `[0,+staged)` 在熱門 sub-industry × 多頭 regime 系統性錯過平順上漲。Semis HOLD-miss 86%（19/22）、CANCEL-miss 71%（15/21），miss avg runup +30.5% vs drawdown −3.2%（Rec 9 drawdown 證實真錯過非避損，H1 確認、H3 否證）。default 觀望太保守。
- **change**: decision band 加例外 — `final_score∈[0,+staged) ∧ industry_top_30pct ∧ macro_regime∈{RISK_ON,BULL} ∧ decision_cap_active!=true ∧ mandatory_risk_flags 空` → default HOLD 降為 `STAGED_ENTRY (hot_zone_probe)`，`position_size_pct ≤ 0.0015`（15bps）。連動 cap 規則第 6 點：熱區 probe 不 force CANCEL。負分區不適用；硬閘（Auto REJECT / burry≤1 / proceed_to_phase3=false / systemic flag / decision_cap）全部優先。
- **target_metric**（任一退步 → 評估 paused/rollback）:
  - Semis HOLD-miss_rate **< 60%**（baseline 86%）；**回升 > 70% → 立即 paused**（user 指定門檻）
  - deep-dive CANCEL-miss_rate **< 60%**（baseline 71%）
  - 整體 deep-dive hit_rate **不退**（baseline 53%，68/128）
  - hot_zone_probe 標的後續 max_drawdown 不顯著惡化（probe 15bps 本就 bound 曝險）
- **files_changed**:
  - `investment/investment_protocol_v5_0.md` — decision band 加熱區例外段 + 設計理由 + cap 規則第 6 點熱區例外
  - `investment/phase5_export_schema.md` — 加 `hot_zone_probe` bool 欄
  - `investment/scripts/validate_session_export.py` — § 11 hot_zone_probe enforcement（STAGED_ENTRY / ≤15bps / 與 decision_cap 互斥）
- **rollback_plan**: 移除 decision band 熱區例外段（HOLD band 回復原狀）+ cap 規則第 6 點回復「降為 HOLD 則 CANCEL」；schema/validator 欄位可留（向後相容，預設 false）。
- **status**: active（決策層 — 首兩週加嚴觀察）
- **scope_note**: **影響 investment_protocol 實際決策（final_decision / position_size）**。regime guard（只在 RISK_ON/BULL）+ decision_cap/risk_flag 兩道硬保險 + 15bps 倉位上限三重 bound 下檔風險。⚠️ **2026-06 中旬預期大幅回檔**（user 2026-06-07 提示）：回檔期 regime 應轉 VOLATILE/SIDEWAYS → 規則自動 dormant；若 regime 誤標滯後，依賴硬保險。
- **evaluation_history**:
  - 2026-06-07: 套用。validator smoke 待下次真實 deep-dive run 帶 hot_zone_probe 欄驗證。下週 REVIEW 看 Semis/CANCEL miss_rate 首週走勢；回檔期間額外確認規則確實 dormant（hot_zone_probe 觸發數應 ≈0）。

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
