# Invest Protocol 冷區盤點 — 最近沒被 review 的 stage 與待辦

> 產生：2026-08-10（repo V4.121.3，HEAD `c7d0969`）。
> 方法：對 `investment/investment_protocol_v5_0.md`（1950 行）逐段 git blame 行級統計
> 「最後被改日期」＋「2026-07-25 之後改動行數比例」；對照 scripts 最後 commit 日、
> TODO.md 已立項項目；決定性宣稱皆獨立驗證（history.json 189 session 全量掃描、
> validator / scripts grep）。檔案創建於 2026-05-04（V5.0 上線），故 median=05-04
> ＝「上線後沒動過」。
> **本檔是 review 結論＋待辦，不含任何已實施的變更。**

## TL;DR

1. 最近三週的優化火力幾乎全集中在 quant/validator 軸（Phase 1.5、2.4、3、4、4.6、5 的閘門，以及 Sentiment/Technical/Valuation 三條 lane 的 deterministic 錨）。
2. **最久沒被 review 的是 Phase 2 的「協作層」：共通 Subagent Prompt 模板、Fan-Out/Fan-In fallback、Phase 2.5 Conflict & Bias——三段自 V5.0 上線（2026-05-04）至今近乎原封不動。**
3. 實測發現 Phase 2.5 在 189 個 session 的 history.json 裡**一筆輸出都沒有**（schema/validator 根本沒有它的欄位）——T1–T5 有沒有 fire 過、fire 了怎麼裁，想 audit 也沒資料。

## 摘要表（各 stage 新鮮度，依 2026-07-25 後改動比例排序）

| Stage（protocol 行號） | 最後被改 | 7/25 後改動 | 狀態 |
|---|---|---|---|
| Phase 1.5 Valuation Quant (245-277) | 2026-08-08 | 100% | 🟢 剛全面翻新（V4.88+anchor 系列） |
| Phase 2.4 MHP (778-813) | 2026-08-02 | 75% | 🟢 V4.88.0 改組 |
| P2 Sentiment lane + L5 (408-452) | 2026-08-08 | 71% | 🟢 V4.91.0 det producer |
| P2 Valuation Specialist (575-692) | 2026-08-09 | 70% | 🟢 V4.89 gate + pack 硬閘 |
| Phase 4 Execution & Risk (1339-1509) | 2026-08-02 | 59% | 🟢 風控三支 Batch A/B |
| Phase 4.6 Decision Cap (1542-1645) | 2026-08-08 | 52% | 🟢 V4.106 speculative governor |
| Phase 4.5 Price Framework (1510-1541) | 2026-08-02 | 43% | 🟢 |
| Phase 5 Export/Validate (1646-1950) | 2026-08-09 | 41% | 🟢 V4.116/117 三道閘 |
| Phase 0 Macro (68-180) | 2026-08-02 | 30% | 🟡 V4.116 新鮮度閘（validator 新、macro 邏輯 V4.71 舊） |
| Phase 3 Decision Engine (955-1338) | 2026-08-09 | 30% | 🟢 V4.80 script 化 + V4.117 parity |
| Phase 2.8 Red Team (862-954) | 2026-08-02 | 26% | 🟡 V4.70 分級懲罰已上，校準資料才 1 筆（見 T6） |
| P2 Fundamentals rubric (365-407) | 2026-08-03 | 20% | 🔴 錨盤點唯一缺席的 lane（見 T4） |
| P2 Contrarian Burry (724-777) | 2026-08-08 | 16% | 🟡 script 端剛被風控三支掃過；殘餘項已在 TODO.md |
| P2 News rubric (453-512) | 2026-08-09 | 11% | 🟡 已立項（TODO.md「News lane 接錨」，不重複開） |
| Phase 1 Bundles/Factpack (181-244) | 2026-08-08 | 6% | 🟡 script 新（factpack 08-08）、文件主體 05-04 |
| **Phase 2.5 Conflict & Bias (814-861)** | 2026-08-02 | **2%（1 行）** | 🔴 **零 export、零可稽核性（見 T1）** |
| **P2 共通 Subagent Prompt 模板 (312-362)** | **2026-05-04** | **0%** | 🔴 含「有文件、無產生器」規則（見 T2） |
| **P2 Fan-Out/Fan-In (693-723)** | **2026-05-04** | **0%** | 🔴 Claude-only 語法 + cap 未驗（見 T2/T3） |

相關 scripts 冷區：`register_thesis.py`（05-10）、`backtest_watchlist.py`（05-10）、`backtest_postmortem.py`（06-15）、`validate_v219.py`（05-10，疑 legacy）——見 T5。

## 多模型前提（所有待辦的共同約束）

invest 現由 `config/llm_config.json` 的 `protocol_providers` 限 **claude + codex** 執行；gemini 路由已通但執行能力未驗（TODO.md 既有項，5-lane subagent 撐不撐得住沒測過），**驗過之前不進白名單**。因此本檔所有修改必須：

1. **閘門一律落在 script/validator（rc=1），不落在 prompt 散文**——V4.116/117 已證明：agy 手寫 history 7+6 次 → 加閘後 0 次；codex 一次過。散文紀律對不同模型的漂移模式沒有約束力。
2. **export 欄位一律由工具產出、模型只轉錄**（V4.117 三道閘原則）——不同模型「打字」出來的欄位不可信，validator 要能對回 producer 的 artifact。
3. **凡涉及跨 session 狀態（計數器、ledger），必須以 (provider, lane) 為 key**——不同模型的違規／漂移模式不同，混在一起會互相稀釋訊號。
4. **protocol 文件裡的執行語法要 provider-neutral**：行為規格寫主文，各 CLI 的 subagent 呼叫方式寫對照表——不能假設執行者是 Claude（2026-08-09 invest 事故的教訓：假設別家會讀你的 context 就是事故源）。
5. score 生產方式的任何改變**必 shadow-first**、權重/門檻/翻預設**使用者拍板**（沿用 invest L 路線既有紀律）。

## TODO

### T1 — Phase 2.5 補 export 欄位 + validator ✅ **已完成（V4.122.0，2026-08-10）**

- [x] `phase5_export_schema.md` 新增 `conflict_bias` block：`schema` / `tentative_decision` / `lane_signals` / `triggers_fired[]` / `conflict_summary` / `t4_detail` / `t5_detail` / `proceed_to_phase3`。僅記錄、**不動決策數學**。日期閘 `export_date >= 2026-08-10`（沿用 V4.116.3 `valuation_reviewer_gate` 前例，不為純紀錄區塊擴 session_export_version）；舊 entry 整段跳過、**不回填**（同 §15：補一塊看起來很完整的觸發紀錄＝在稽核軌跡放假證據）。
- [x] `validate_session_export.py` **§16**：`evaluate_conflict_triggers()` 依 export 自己的欄位重算 T1–T5 應觸發集合，與宣稱的 `triggers_fired` 比對，**少報／多報一律 rc=1**。缺輸入的 trigger 回 `None`（不猜成 False）、退出比對並留 warning——同 `valuation_reviewer_gate` 的「gate 讀不到權威輸入時不得猜」。
- [x] **新自陳輸入補錨**（沒有錨的重算會退化成自己跟自己比對）：`lane_signals.<lane>` 不得與同 lane score 反向（score 受 §13 保護）；`lane_signals.valuation` 必須等於 `valuation_lane.signal`。
- [x] **後果雙向鎖**：`t4_detail.resolution == "OVERRIDE_BURRY"` ⟺ `burry_override_active == true`（該布林餵 Phase 4 的 ×0.5，鏈尾受 §14 重算——本節唯一錨在「已經在改倉位的數字」上的檢查）；`proceed_to_phase3 = false` ⟹ `final_action == "CANCEL"`。
- [x] 測試 `test_validate_session_export_gates.py` 兩層：字面輸入的重算契約（19 條，含每條不等式的邊界與 5 個 indeterminate 案例）+ 真 validator subprocess 接線（14 個 case）。**8 個種回 bug 全部驗紅**：拆掉 main() 呼叫、T1 嚴格不等式放寬、T4 門檻翻向、indeterminate 改猜 False、T5 偷偷變 error、拿掉反向 override 鎖、拿掉 valuation signal 錨、拿掉 CANCEL 檢查。cutoff 日期在測試裡寫死不讀被測常數（MAINTENANCE §2c）。
- [x] 副產物：schema doc 的 FULL EXAMPLE 五個 lane 全正卻 `devils_advocate_filed: false`——「5 lane 同向」這條在範例自己身上也沒被接住，一併修正為 `true` + `triggers_fired: ["ANTI_BIAS"]`。
- [ ] **待累積**：≥20 session 後做 Phase 2.5 版的 V4.70 audit——各 trigger fire 率、T4 裁決分布（CANCEL/DOWNGRADE/OVERRIDE 熵）、T5 與 30d outcome 相關性。
- **多模型**：觸發判定重算在 validator 端＝provider-agnostic by construction，claude / codex / 未來 gemini 走同一條；audit 報表按 provider 分欄，先確認 T1–T5 fire 率是否同分布，不同再談規則問題。

### T2 —「有文件、無產生器」規則處置：prompt 模板 + Fan-In cap（**部分完成，V4.123.0**）

- [x] **Fan-In fallback `confidence cap 0.6`** → **validator §17 完成**。實作繞過了「per-lane confidence 沒進 export」這個障礙：`c_eff()` 量化成三檔（`<0.45→0.35`/`<0.675→0.60`/`else 0.72`），所以「confidence ≤ 0.6」等價於「`calculation_steps` 的 C_eff 不得為 0.72」，**零偽陽**；而 C_eff 受 §13 重算與 §5l engine parity 保護，是偽造者改不動的錨。附帶收緊 `FULL_FALLBACK` ⟹ 5 degraded + STRONG_COUNTER、≥2 degraded ⟹ 非 PARALLEL_SUBAGENT。**恰好 1 個 degraded 只 warning**（protocol 沒定義單一失敗的 mode，不單方面收緊）。
- [x] **順帶修好「欄位不可機器讀」**：`degraded_analysts` 過去 10 種寫法指涉 5 個 lane、`phase2_fanout_mode` 出現過表外值 `FULL`——**這才是 cap 從 V4.8 起接不上去的真正原因**。現在要求每個元素以 canonical lane 名開頭（前綴比對，附註照留）。
- [x] **web-search 違規懲罰 → 第三條路（shadow ledger）已完成，V4.124.0**。`investment/scripts/websearch_shadow.py` 從 **run log** 讀每個 lane 的實際 web call 數並寫 jsonl ledger，**不扣分、不進決策**。證據取自 log 而非 PM 自陳——違規的 session 正是最不會自我回報的那個。Claude 的 stream-json 用 `parent_tool_use_id` 把每個工具呼叫掛回 spawn 它的 `Agent`，所以歸屬精確到 lane。codex 的 JSONL **沒有任何 web 工具事件型別**，一律記 `observable: false` 而非 `web_calls: 0`（看不到 ≠ 沒發生）。

  **意外收穫：不必等 20 場，203 支歷史 log 立刻給出答案**（`--backfill`）：

  | 月份 | 可觀測 run | 超額 run | 超額率 | 總 web call |
  |---|---|---|---|---|
  | 2026-04 | 83 | 55 | **66%** | 281 |
  | 2026-05 | 54 | 0 | 0% | 11 |
  | 2026-06 | 35 | 2 | 6% | 13 |
  | 2026-07 | 5 | 0 | 0% | 0 |
  | 2026-08 | 6 | 0 | 0% | 2 |

  lane 分布：Sentiment 52 次超額 / News 35 / Fundamentals 6 / **Technical 與 Valuation 幾乎零**。
  超額全部集中在 4 月；**5 月起連續 100 場、三個多月維持合規，而且從來沒有任何機制在執行這條規則**。

  **不能宣稱因果**：v4_8（4 月當時）與 v5.0 都有「≤ 1 次」額度，所以不是拿新規則量舊行為；但 V5.0 上線那天同時改了很多東西（5 lane 改制、bundle/factpack 成熟），ledger 說不出是哪一項讓它歸零。

- [ ] **T2 剩餘的拍板**：依上表，我的建議從原本的「傾向 (b) 刪宣稱」**改為 (c) 三者皆不做**——(a) 補產生器會是為了一個近 100 場沒發生過的情況去建跨 session 計數器；(b) 刪宣稱有風險，因為我們不知道現在的合規是什麼在維持，而 prompt 裡那段文字是候選之一。**保留文字、讓 shadow ledger 繼續看**，違規率若回升就會被看到。這一項請你拍板。
- [x] **模板 output shape 對 lane_contract（C1/V4.90）核一次** → **V4.125.0 完成，四條差異**：
  1. **`signal` 已從敘述欄變成決策軌輸入**（V4.122.0 §16 用它重算 T2/T3），但模板沒說。已補：PM 必須把五個 lane 的 signal 原樣填進 `conflict_bias.lane_signals`。
  2. **`score` 的 −5..+5 只適用四個 LLM lane**；valuation 不自填、verbatim 抄 `valuation_pack.score`。歷史唯一超界的 −4.0（2026-06-14 RGTI）**沒有 valuation_pack**，是 pack 成為必填前的自由填寫，之後不可能再發生。已在模板寫明。
  3. **Fan-In 表的 `subagent_execution_failed` 是個沒有產生器也沒有消費端的欄位名**——189 筆 export 零出現，全 repo 只有它自己和一份 4 月報告提過。實際被持久化、且 V4.123.0 §17 開始驗的是 `degraded_analysts`。已把表指向真實欄位（純事實更正，不改行為）。
  4. **`skill_execution_failed` 是真的**（`momentum.py:792` / `technical-analyst/analyze.py:216` 失敗時輸出），不是模板自創——與 #3 是兩個不同概念，不要合併。
  另補一條負向規範：subagent **不得**產 `provenance` / `producer_version` / `input_hash` / `shadow_score`，那四個是 Step 1.5 post-processor 的，LLM 手寫等於偽造 provenance（§15 會擋）。
- **多模型**：§17 全在 validator 端，claude/codex 走同一條；唯一真實樣本（PLTR 2026-08-09）就是 codex 跑出來的，且合規。

### T3 — Fan-Out 執行段 provider-neutral 化 ✅ **已完成（V4.123.0）——但缺口比原本記載的窄**

> **原本的判斷有誤，先更正**：這一項原寫成「protocol 是 Claude-only 語法、需要補各 CLI 對照表」。
> 實際查證後，**翻譯層早就存在而且有測試**——`dashboard_server._adapt_protocol_prompt()`
> （V4.114.0）會對每個非 claude provider 注入「把 `Agent(...)` 對應到一個隔離 subagent，
> 平行 fan-out 時先全開再等待」的詞彙對照，`run_protocol_manual.py` 呼叫**同一支**（無第二份
> 定義，沒踩 §2c #8），`tests/test_protocol_model_routing.py` 逐 provider 斷言涵蓋範圍。
> 真正缺的只有一件：**protocol 文件自己沒說那些工具名是抽象的**，只讀文件的人（或未來的
> 編輯）合理會以為執行者必須是 Claude。

- [x] Fan-Out 段改成**先列五條行為契約**（獨立 context／先全開再等待／只注入自己那份／失敗 retry 1 次後 inline + cap 0.6／如實記錄 mode），再說明 Claude 語法只是其中一種實現、全文工具名是抽象操作詞彙，並指向 `_adapt_protocol_prompt()` 與它的測試。
- [x] 明標 `protocol_providers.invest` 今天只開 claude + codex，gemini 執行能力未驗、沒過不得加白名單。
- [ ] gemini 的實跑驗證維持 `TODO.md` 既有項的判準，不在本項範圍。

### T4 — Fundamentals lane 錨盤點 ✅ **已完成（V4.128.0）**

**盤點結果**：Fundamentals rubric 的計分成分裡，**六條是純門檻運算、四項是真判斷**。

| 成分 | 型態 | 資料源 |
|---|---|---|
| `peer_pe_median` 差距 >30% → ±1、>50% → ±2 | **可 script** | PEER_BUNDLE |
| `altman_zone == danger` → −1；`piotroski_strength` strong/weak → ±1 | **可 script** | FMP_SUPP_BUNDLE |
| `owner_earnings.qoq_growth` >0.15 註記、<−0.30 → −0.5 | **可 script** | FMP_SUPP_BUNDLE |
| `employee_history` 5Y CAGR >15% → +0.5；1Y −5% → −0.5 | **可 script** | FMP_SUPP_BUNDLE |
| 強訊號 `FCF yield >5% AND rev_growth >20%` → +3/+4 | **半可 script**（門檻確定，+3 vs +4 是判斷） | us-stock-analysis |
| `quality_flags` 觸發 → ±1 | **可 script** | EARNINGS_ANALYST_BUNDLE |
| base score（P/E・rev YoY・FCF margin・D/E・earnings date・EPS growth 的**加權**） | 真判斷 | — |
| `moat_assessment` / `near_term_catalysts` / bull・bear thesis | 真判斷 | — |

**缺口與 Technical 在 V4.116.3 之前完全同形**：`skills/us-stock-analysis/scripts/analyze.py`
算得出全部六個 rubric scalar，但**只印到 stdout**——數字最後躺在 lane subagent 的 transcript 裡，
validator 構不到。Technical 的 `analyze.py` 早已落地 `cache/<T>_technical_payload.json`。

- [x] **走便宜路線：producer 留下物證**。`analyze.py` 收尾無條件寫
  `skills/us-stock-analysis/cache/<T>_fundamentals_payload.json`（含 valuation / growth /
  margins_cash / balance_sheet / earnings_calendar / analyst 六塊），與 Technical 同一個 pattern，
  不擴 lane 契約。`test_bundle_merge.py` 加兩類斷言（接線＋形狀），種回驗紅。
- [x] **刻意不做 `rubric_hint`**：Technical 的 hint 是「stage 結構 → 分數帶」的既有翻譯；
  Fundamentals **沒有議定過的 base-score 公式**（rubric 給的是調整項不是基準分），
  現在發明一個等於寫進一條新的計分規則。**證據先落地，公式待拍板。**
- [ ] **待拍板**：要不要用這份 payload 建 Fundamentals 的 `rubric_hint`／validator 硬閘。
  前置是先定 base-score 公式。σ 量測（TODO 既有的 MU/AAOI 12-run）建議連 Fundamentals 一起量，
  且**按 provider 分開統計**，先分清漂移是模型性質還是 lane 性質。

### ~~T4 — Fundamentals lane 補進錨盤點~~（原始描述，已由上方取代）

- [ ] TODO.md 的錨盤點（2026-08-09 BAC 三跑診斷）列了 Valuation（pack 硬閘）、Technical（`rubric_hint` 硬閘）、Sentiment（`sentiment_det` shadow）、News（已立項）——**Fundamentals 是唯一連「有沒有錨」都沒被盤點的 lane**。先盤點：rubric（365-407）裡哪些計分成分 script 算得出（bundle 內 scalar 佔比高，可能比 News 還容易接）、哪些是真判斷留 LLM。
- [ ] 盤點產出後，若要接錨，走 Technical V4.116.3 的便宜路線：**producer 留物證**（落 cache payload，validator 直接讀），不擴 lane 契約。
- [ ] 與 TODO.md 既有的 MU/AAOI 12-run σ 量測併批：Fundamentals 的三跑全距一起量，帶寬用量出來的數字定。
- **多模型**：deterministic producer + validator 讀物證＝天然 provider-agnostic；σ 量測按 provider 分開統計（claude 3 跑 + codex 3 跑），先確認漂移是模型性質還是 lane 性質。

### T5 — 決策後回饋迴路腳本翻新 ✅ **已完成（V4.128.0）——四支裡兩支我原本的判斷都錯了**

- [x] **`register_thesis.py`（05-10）→ 從上線起就沒運作過，這是四支裡最嚴重的**。
  它 import trader-memory-core 的 `thesis_store`，而 **`~/.claude/skills/` 底下只有 `grill-me`，
  TMC 從來沒安裝過**。實跑：`trader-memory-core unavailable (No module named 'thesis_store')`，
  **rc=0**（non-fatal hook，照設計不紅）。後果實測：**183 筆 trade 的 `thesis_id` 全部是 null**。
  連帶 **V20-F1 sector concentration 從來沒生效過**——11 筆帶 `sector_concentration_f1` 的 entry 裡
  7 筆 `registry_unavailable`、4 筆 `explicit_count`，**`applied=true` 是 0 筆**。
  這正是 reviewer session 這次在 live run 觀察到的 `registry_unavailable`。
  **未修，需拍板**：裝 TMC、或改用 history.json 自算同 sector active 部位（＝建新功能）、
  或承認 F1 為 inert 並把文件講清楚。三條都改變風控行為。
- [x] **`backtest_postmortem.py`（06-15）→ 對 V4.87.0 renderer 靜默半殘，已修**。
  renderer 把 action 摺進決策格（`| Final Decision | HOLD（action: CANCEL） |`），舊 regex 要求
  決策字後直接接 `|`，於是 **145 份 NEW-format 報告裡 decision 漏 33 份、action 漏 126 份**，
  而工具 rc=0 照吐一張 None 表。修 regex 後 decision 112→131、action 19→35（其餘是報告本身
  真的沒有那一列，非 regex 問題）。**更重要的是加了解析缺口彙總警告**——下次 renderer 再變格式
  會先出聲，不必等人發現整欄都是 None。
- [x] **`backtest_watchlist.py`（05-10）→ 完全正常**，`--dry-run` rc=0 產出完整報告。
  順帶：TODO 的 `[V20-D2] 加 --dry-run flag` **早就做完了沒勾銷**。
  ⚠️ 但 `watchlist_lifecycle.jsonl` 的 881 筆事件停在 **2026-07-20**，三週沒有新事件——
  **輸入停止累積**，要查 news 端的 producer 還在不在跑（已記 TODO）。
- [x] **`validate_v219.py`（05-10）→ 不是 legacy，我原本猜錯**。16 個 fixture 全過，
  而且它 import 的是**真 producer**（`apply_det_shadow.compute_polarization` /
  `classify_red_team_basis`），沒有複製一份邏輯，驗的 4-tier polarization 與 RT basis 今天仍是
  §13 的活規則。真正的問題是**它不在 OPS §7 對照表裡**——改 polarization 的人不會知道要跑它。
  已補進 §7。

### ~~T5 — 決策後回饋迴路腳本翻新~~（原始描述，已由上方取代）

- [ ] `register_thesis.py`（05-10）：Phase 5 Step 6 是 non-fatal hook，壞了不會紅。對 V5.1+ export schema 跑一次 round-trip 確認還能吃當前 entry shape；順手補一條 smoke test 進 §7 測試對照表。
- [ ] `backtest_watchlist.py`（05-10）/ `backtest_postmortem.py`（06-15）：整條決策鏈 V4.80–4.117 script 化之後，這兩支還在讀舊世界的欄位假設。確認對 `calculation_steps` / `decision_cap` / `speculative_grade` 等新欄位的相容性；探索層定位不變（產出永不進決策）。
- [ ] `validate_v219.py`（05-10）：疑 legacy。確認無 caller 後刪除或移 `archive/`。
- **多模型**：這三支是純 python 離線工具，本身 provider-agnostic；唯一要求是它們讀的 history.json 欄位以 schema 為準，不假設某家模型的填寫習慣（例如 null vs 缺鍵——V4.116 的教訓）。

### T7 — T5 自動降階 ✅（V4.131.13）；Anti-Bias 同向定義仍待拍板

T1 動工時發現兩條「protocol 寫了、沒有產生器」的規則。T5 已由使用者於 2026-08-16
拍板成「先做 forward validation、完整 FAIL 才硬降級」；Anti-Bias 仍維持 warning。

**T7a — T5 的「valuation −3 → 自動 downgrade」✅ 已完成（V4.131.13）**

- [x] `compute_price_framework.py` 產 `forward_validation.v1`：eligible DCF gap ≤−30% 時，
  交叉檢查 archetype shadow、forward earnings、revenue path；至少 2 項可判讀。
- [x] 任一可信支持成立 → PASS/STRETCHED，valuation score 最低 −1；`NO_DATA` 不猜 FAIL。
- [x] 可判讀項全部失敗 → FAIL；decision engine 1.1.0 只在 FAIL + score ≤−3 時降一階，
  並讓 T5 優先於 Rec 11 probe（hard downgrade 不得被熱區例外重新打開）。
- [x] Validator／schema／export／renderer／replay 接線。歷史完整 artifact cohort：NOW、PLTR
  分數上修但 final decision 不變；SNDK 原 score 已 −1，仍 STAGED_ENTRY。

**T7b — Anti-Bias 的「5 lane 同向」沒有定義**

- protocol 只寫「5 lane 同向 → News 追加 `devils_advocate[]`」，沒說同向是看 score 正負還是看 signal。§16 本版採 **score 正負一致**當定義、**只出 warning**——把一句沒定義過的話變成 rc=1 是單方面收緊。
- 附帶發現：schema doc 的 FULL EXAMPLE 自己就是五 lane 全正卻 `devils_advocate_filed: false`（已於 V4.122.0 修正）。連範例都沒遵守，是這條規則從未被接住的旁證。
- **選項**：(a) 定義為 score 同號 + 升為 error；(b) 定義為 signal 全等 + 升為 error；(c) 維持 warning。決策前置同 T7a：等樣本。

### T6 — 反面確認（記錄，不動工）

- Red Team V4.70 分級懲罰承諾「≥20 session 後校準 strength 分級」；實測 history.json 帶 `counter_evidence_strength` 的只有 **1 筆**（2026-08-09）——欄位最近才真的開始寫入。**分級懲罰已在改決策數學、校準資料近乎零**。不是現在的 review 對象；等累積到 20 筆再開校準項，且屆時按 provider 分組看 strength 分布是否一致。
