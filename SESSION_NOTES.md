# INTEL COMMAND — Session Notes & System State

> **Last Updated**: 2026-08-03 (v4.90.4)
> **Role**: This file serves as the "Short-term Memory" and "Handoff Cache" for AI Agents. It contains market regime states, token optimization logs, and data integrity notes. **Task backlog has been moved to TODO.md; full version history to CHANGELOG.md.**

## 🟢 Session Note (v4.90.0) — C1 統一 lane 資料契約（契約的價值在保留規則，不在形狀）
- **這塊最容易壞的地方不是形狀，是「被自己的 post-processor 覆寫」。** 契約值域寫錯會被 validator 擋，但 `build_lane_contract()` 若無條件重算，L5/L6/L8 在自己 phase 寫好的 `provenance: "deterministic"` 會在 Step 1.5 被靜默改回 `llm` 預設——契約還在、值域還對、validator 全綠，只是每個 lane 都變成 LLM 產出，而 Phase 6 就是照這個欄位分層的。所以 producer 的規則是「只補 None 的欄」，`test_lane_contract.py` 的保留 case 也最多（含 `llm_invoked=False` 與 `shadow_score=0.0` 這兩個 falsy-but-not-empty 的坑）。**判準：一個純 metadata 欄位的失效模式通常是靜默的，測試要照著「壞掉之後看起來仍然正常」去設計。**
- **`apply_det_shadow.py --inplace history.json` 會掃過全部 181 筆，不是只有末筆。** protocol 的 Step 1.5 說明寫「寫入最新一筆」，但 code 是 `for entry in payload`。det_shadow 這樣做無害（冪等），契約不行——給 V4.6 的四 lane session 補一份六 lane provenance 就是在稽核軌跡放假證據。所以 producer 收 `entry_version`，只寫 `V5.3+`。**判準：新增一個「事後補寫」的欄位之前，先確認那支 post-processor 實際掃過的範圍，而不是它文件裡寫的範圍。**
- **red_team 當第六個 lane，不是另立欄位。** L8 條目原本規劃 `red_team_provenance: deterministic_skip`。RT 併進同一張表之後，L8 只要改 `lanes.red_team.provenance` —— 另開平行欄位正是 C1 要消滅的東西。TODO 的 L8 已改。
- **「勿兩套並存」的實作解**：`det_shadow.valuation_score_det` 有五個現存消費端（shadow_report / bridge / Dashboard / 兩支測試），硬搬會炸一片。做法是**同一次計算寫兩處**（不是兩條計算路徑），validator §15 硬性比對相等 —— 自然漂移不可能，不等只可能是有人手改。舊欄降為別名，等契約全面上線再落日。
- **原計畫「renderer 三處相容碼在 C1 落地後刪」我沒做，因為那跟「舊 entry 豁免」互相矛盾。** 形狀鎖只對 V5.3+ 生效，而 renderer 讀得到 181 筆 V5.0 以下的 entry；刪了相容碼＝渲染舊 entry 時靜默掉字。刪除的正確條件是「舊 entry 淡出 render 路徑」，不是「C1 落地」。**判準：規劃階段寫下的清理動作，落地時要用實際的資料分布重新驗一次前提。**
- **e2e 實跑逼出一個我自己種下的偽造面。** 把 FULL EXAMPLE 走一次真 CLI（PM 寫完 → `apply_det_shadow --inplace` → validator）之後，契約長出 `llm_skipped_lanes: [fundamentals, sentiment, news, technical]` —— 因為那份範例從來沒有 `lane_scores`，而我用「有沒有分數」推導 `absent`。protocol 從 V2.10.0 就寫 `lane_scores` 必填，validator 卻從未擋過；於是「少寫一個欄位」＝ 讓四個跑過的 lane 自稱沒產出，事後從 entry 完全看不出來。修法是 V5.3 起硬性要求 `lane_scores`，並把範例補齊（值與 `calculation_steps` 五段乘積一致）。**判準：新欄位若由既有欄位推導，要先確認那個既有欄位真的被強制——protocol 寫「必填」不等於 validator 擋得住。**
- **順手補的下游洞**：Dashboard `VERSION_COLOR` / tooltip 缺 `V5.2`（L2 當時就漏了）與 `V5.3`，新 entry 會落到 LEGACY 的灰色 `ARCHIVE` badge——最新的 entry 被標成最舊的。
- **驗收**：`test_lane_contract.py` rc=0（producer 6 組 + validator §15 tamper 19 例）；e2e 走真 CLI（含一筆 V5.0 混在同檔，確認不回填）；`test_session_export_schema.py` / `test_valuation_pack_consistency.py` / `test_decision_engine.py` / `test_trade_plan_builder.py` / `test_render_investment_report.py` / `validate_session_export.py` 全 rc=0；`shadow_report.py` / `replay_decision_engine.py` / `validate_v219.py` 照跑 rc=0；SYNC OK 4.90.0。
- **未驗**：history 目前**沒有任何 V5.1/V5.2/V5.3 entry**（181 筆全在 V5.0 以下），所以 §15 與 §2e 只在 fixture 上驗過，真實 export 路徑要等下一次 `分析 [TICKER]` session 才會第一次走到。同理 `input_hash` 恆 null、五個非 valuation lane 的 `shadow_score` 恆 null，要等 L9 / L5 才有值。
- **（4.90.1 review 修正）我把保留規則套到了不該套的欄位上，而且測試把錯的行為鎖了進去。** `lanes.valuation.shadow_score` 的 producer 就是 post-processor 自己，`det_shadow` 那塊又每次整塊重建 —— 對它套「非 None 就不動」等於自己的舊值擋住自己的新值：上游 pack 一改就兩邊分歧、§15 吸收閘**永久 rc=1**，而我寫的錯誤訊息叫人「重跑 `apply_det_shadow.py`」根本修不好，唯一出路是手改契約，正是那道閘要禁止的事。**判準：套保留規則之前要先問「這個欄位是誰產的」——保留只對『外來 producer 先寫好的欄位』成立；同一個 producer 自己的欄位，重算永遠該贏。**
  - 修法必須是**無條件**同步，不能是「`val_det` 非 None 才覆寫」：`val_det` 變回 None（pack/fvs 都沒了）時，契約守著舊的非 None 值會留下同一個死結。complementary 的一條：其餘五個 lane 的保留規則完全不動，那條界線現在有測試釘著。
  - **測試把錯的行為當契約鎖住，比 bug 本身更值得記。** 原本那條 `既有 shadow_score 勝過傳入的 val_det` 是我照著「保留規則」的直覺寫的，fixture 還特地捏了一個 valuation 帶外來 `shadow_score` 的狀態——而那個狀態天生過不了 validator。**寫測試時若 fixture 需要捏一個現實中不會出現的狀態才能成立，那多半是在驗證一個不該存在的行為。**
- **（4.90.2 自審）§15 只驗了契約的內部自洽，沒驗契約對外部事實——兩條繞道實跑全綠。** (A) `lanes.sentiment: null` + session 清單配合列進 skipped → 五欄檢查整組被 `if blk is None: continue` 跳過（註解宣稱 absent_lanes 報過，但那只抓缺 key 不抓 null 值）；(B) 有分數的 lane 手改 `provenance: "absent"` → llm_invoked 一致、清單對齊，全部通過——而 Phase 6 分層會把這筆從 LLM 池靜默剔除，正是 C1 要防的 selection bias。修法：per-lane 檢查改為「key 不在才跳過、非 dict 一律 error」；provenance 雙向錨在偽造者改不動的東西上（lane_scores 受 §13 算術鏈保護、`red_team_execution_failed` 是 schema 必填），推導**與 producer 共用同一條** `compute_polarization().missing_lanes`，兩邊不可能因實作分歧吵架。**判準：一致性檢查若只比對「偽造者可以一起改的欄位」，改得夠齊就能過閘；至少一端要錨在他改不動的外部事實上。**
- **（4.90.3 複審 4.90.2 自己）我在修漂移面的那次修補裡，親手引入一個漂移面。** 4.90.2 的註解寫「validator 用**同一條**推導」——`compute_polarization` 確實是共用的，但**它的輸入我重寫了一份**（authoritative valuation score 的取值順序）。producer 哪天改取值來源，validator 這份不跟著動，就會對合法 entry 報 rc=1。抽成 `authoritative_valuation_score()` 兩端 import 才算數。**判準：說「共用同一條推導」之前，把那條推導的『輸入』也數進去——共用一個函式但各自餵不同來源的參數，不是共用。**（抄過去時還漏了 `bool` 排除，`isinstance(True, int)` 為真——重寫一份的代價從來不只是「未來會漂」。）
- **同一輪抓到 4.90.0 那個洞的零售版**：`lane_scores` 只擋了「整塊省略」，`{"fundamentals": 4}` 這種部分省略照樣把三個 lane 推成 `absent`，而 producer 與 validator **一致同意** → 全綠。**「兩邊算出來一樣」不是保護，當兩邊讀的是同一份被動過手腳的輸入時，它只證明兩邊都被騙了。**四個 key 現在必須都在，沒產出的明寫 `null`——與契約「六個 lane 全列、缺席明寫 absent」同一條紀律，只是往上游推一層。
- **（4.90.4，第四輪 code review）修 P2 時我對症不對病——同一個病三天後在旁邊一格復發。** P2 的修法只把「同 producer 重算贏」用在出事的 `valuation.shadow_score` 上；這輪拿同一判準**逐欄位重掃整張表**，發現 `provenance` 的 `llm`/`absent` 與 `llm_invoked` 一樣是 post-processor 自己的推導、一樣被保留規則鎖住，而且**真實操作序列就會踩到**（PM 漏填 lane score → 推成 absent → 補分數重跑 → 上一輪的 absent 被自己保留住 → §15 的「重跑可修」變謊話）。修法是把界線寫成常數 `EXTERNAL_PROVENANCE`：保留域=外來聲明（det/hybrid + producer_version/input_hash/非 val shadow_score），推導域=自己的輸出（llm/absent、llm_invoked 投影、val shadow_score），L5 shadow 形態（provenance=llm + 外來 shadow_score）有測試釘住。**判準：修一個「規則套錯對象」的 bug 時，不能只把出事的那個對象搬走——要拿同一條判準把規則覆蓋的每個對象重新分類一遍，否則同型 bug 就躺在下一格等著。**

## 🟢 Session Note (v4.89.0) — L4b 條件式 Valuation reviewer（前提實測後被修正）
- **「沒有數字權 = 跳過不改決策」被實測推翻。** 條目與我收到的規劃都寫「Specialist 的 score 是 pack projection，所以跳過 LLM 不動任何決策數字」。grep 下去發現 `decision_engine.compute_transition_gate()` 吃兩個**純 LLM 欄位**（`cited_transition_overlay` / `transition_dissent_basis`）；lane 不跑 → `cited` 缺 → `valuation_confirmed_transition=False` → Phase 3 cascade rule #2 的 ×0.95 軟化落回 ×0.85（raw_total 100 即 95 vs 85，門檻附近足以翻 BUY/HOLD）。實跑兩次 `compute_transition_gate()` 對照確認。**判準：「這個 lane 有沒有數字權」要看的是 decision engine 讀了它哪些欄位，不是看它的 score 怎麼來的。**修法是加第 5 條 mandatory trigger，不是放寬前提。
- **方向是保守，但保守不等於沒事。** 跳過會讓懲罰更重（×0.85 而非 ×0.95），是 fail-safe 方向。但這仍然是決策數字被改了——如果只看「會不會變得更敢買」就放行，等於默認「往保守偏移不算 regression」，那條線一鬆，之後任何省成本的改動都可以用同一個理由過關。
- **`no_peer_cohort` 今天 100% 命中，所以 discovery cache 是核心不是附件。** `config/peer_cohorts.json` 只有 MU 一個 curated cohort。沒有 discovery cache 的話，shadow 數據只會告訴你「每次都該跑」，省不到任何東西也學不到任何東西。
- **discovery cache 刻意不餵 `build_pe_cohort`。** 只餵 gate。餵下去的話 LLM 發現的 peer 會流進 `valuation_explained_range` 這條 **live 數字路徑**——那超出 shadow-first 的範圍。同理 `record_discovered_cohort()` 對已有 curated cohort 的 ticker 直接拒絕寫入：人工核准的那份永遠贏，不讓兩份悄悄分歧。config 那個檔帶 `approved_by: user`，任何 agent 不得寫入。
- **validator 擋 `shadow_only=false`（error 不是 warning）。** 翻預設要使用者拍板；把它做成 warning 等於允許某個 session 自己決定然後留一行沒人看的黃字。六種情形逐一實跑驗過（缺 block 靜默、would_invoke 與 triggers 矛盾 → warning、未知 trigger 名 → warning、shadow_only=false → error）。
- **shadow 窗口我不建議用固定 session 數**：前幾個 session 會被 discovery cache 暖機主導（今天除 MU 外全部命中 `no_peer_cohort`），那段期間的命中率不反映穩態。既有前例在 `shadow_report.py` 裡是兩個具名常數——`ARCHETYPE_CHECKPOINT_N = 20`（翻 live 行為）與 `NEWS_FREEZE_N = 10`（降級後監看）。L4b 是翻 live 行為，形狀接近前者。建議停止規則寫成「discovery 覆蓋率穩定後再數 N」而不是「跑滿 N 個 session」。
- **驗收**：`test_valuation_reviewer_gate.py` rc=0（5 條 trigger 各自獨立 + 全靜默、mandatory 唯一性、proxy 兩側、TTL 第 30/31 天邊界、拒絕覆寫 curated、壞 cache 不偽裝、artifact 四種不可用 rc=1）；`test_comps.py` / `test_dcf.py` / `test_session_export_schema.py` / `validate_session_export.py` 全 rc=0；live NVDA gate 實跑 would_invoke=true（`no_peer_cohort` + `anchor_conflict_severe`，cv 0.4314 未達門檻但 span 9.73x 達標）；SYNC OK 4.89.0。
- **review 收尾：補 P3 時測試逼出一個真缺陷。** 三條 P3（缺 `shadow_only` 繞道 / leaf key 只驗 block / protocol 小節插錯位置）都是幾行的事，但補「leaf 值為 null 仍合法」那條測試時炸了——我的 `possible_buy` 寫成 `verdict is not None and verdict not in OVERVALUED_BANDS`，於是 `verdict_band=null`（無 eligible anchor、pack 根本算不出估值）會判成「不是可能 BUY」→ 不叫 reviewer。**估值完全未知 + 資料品質低，正是最該叫人看的情形，我的邏輯卻讓它最不會被叫。**改成 `verdict not in OVERVALUED_BANDS`（null 視為不在高估側）。**判準：寫「非高估側」這種否定條件時，要分開想「已知不高估」與「不知道」——把未知歸到跳過側，等於在最不確定的地方省事。**
- **未驗**：gate 尚未接進 `shadow_report.py` 的讀出端（它只掃 history.json，要等 session export 真的帶 `valuation_reviewer_gate` 才有樣本）。翻預設所需的統計面板是下一版的事。

## 🟢 Session Note (v4.88.0) — L4 估值 quant 提前 Phase 1.5（等價用結構保證，不用比對）
- **「兩段合併 == 單發」不該靠測試比對，該讓它無法不成立。** 第一個設計是分別寫 quant 路徑與 mhp 路徑，再用 regression 檢查兩者相等——那等於把契約託付給我未來記得同步改兩處。改成把 `main()` 拆成 `build_quant_stage()` + `build_full_output()`，**單發模式本身就是這兩段的組合**，staged 只是把中間物存進檔案再讀回來。等價成了結構事實，測試從此只是防呆而不是唯一防線。**判準：當驗收條件是「兩條路徑必須等價」時，先問能不能讓它們是同一條路徑。**
- **`compute_mhp` 到底吃什麼，得去讀而不是照 protocol 抄。** protocol 說 MHP 要 technical/news lane 的東西，但實際簽名只讀 6 個欄位（`current_price`/`volatility` + 4 個 qualitative），anchors 是走 `fvs` 進去的。確認這點之後 mhp 段的輸入可以縮成那 6 欄，`MHP_QUALITATIVE_KEYS` 也才有資格當常數釘住——並補一條測試鎖那份名單，名單漂掉會讓分段悄悄漏餵而不報錯。
- **分段真正的風險不是算錯，是價格漂移。** 兩段之間隔著整個 Phase 2 fan-out（實際上是幾十分鐘）。若 mhp 段重抓 quote/OHLCV，Valuation lane 看過的 pack 就與最終輸出的價格基準不同——數字全對，基準不同。所以 `current_price` 與 `volatility` 在 Phase 1.5 定版並隨 artifact 持久化，mhp 段只讀不抓。同理 `--from-quant` 檔壞掉一律 rc=1：**靜默 fallback 成「用 Phase 2.4 的價格重算」正是這功能要消滅的東西。**
- **`built_at` 是唯一豁免欄位，而且它本來就不可比。** 兩次單發跑也不會相同（`dt.datetime.now()`）。除它之外連 key 順序都逐位元比——`build_full_output` 的 dict literal 順序就是舊 `main()` 的順序，所以舊消費者看到的 shape 一個欄位都沒動。
- **順手修了文件裡三處過期的 phase 標籤**（`protocol_appendix_price_framework.md` / `phase5_export_schema.md` / OPS §7）。這批不在原摘要表裡，但留著就是新的自相矛盾——L4 修的就是這種矛盾。
- **驗收**：`test_compute_price_framework.py`（新增 staged 區段：CLI 兩段合併 == 單發逐位元、6 個 block verbatim 併回、qualitative 全缺降級不擋、artifact 壞掉/schema 不符/缺 block/旗標誤用四種 rc=1）、`test_valuation_pack_consistency.py`、`test_session_export_schema.py` 全 rc=0；**live NVDA 實跑**（`--self-assemble --stage quant` → `--stage mhp`）與單發輸出 bitwise identical，20 個欄位自組、fv 150.71、band [177.09, 203.09, 210.0]；SYNC OK 4.88.0。
- **未驗的邊界**：live 對照是在收盤時段跑的，兩次 quote 相同，所以「價格凍結」這條在**盤中**的真實行為（單發會漂、staged 不會）尚未實測——那正是分段的價值所在，但也意味著盤中跑時兩者本來就**不該**相等。下次盤中 deep dive 時值得記一筆實際落差。
- **review 收尾：一條紙上機制被新時序推成明確的假話。** `suppression_proposals[]` 全庫零消費端（只出現在 protocol 兩行），engine 真正的 suppression 閘是 `structural_shift` typed input，來源是 earnings-analyst cache 不是 lane。這在 L4 之前就是虛文；但 L4 之後 pack 在 lane 之前定版，「proposal 影響 pack」從「沒接線」升級成**結構上不可能**。改標 advisory / audit-only + 指明真正的閘在哪。**判準：改動時序之後要回頭掃一遍「誰的輸出流向誰」的敘述——原本只是沒實作的句子，可能已經變成明確錯誤的句子。**

## 🟢 Session Note (v4.87.0) — L3 Phase 5 deterministic renderer（原假設被實測推翻）
- **條目寫「history entry → MD」，實測發現 history 撐不起這份報告。** 動工前先逐欄比對 MSFT/MU 兩筆真 entry 與它們的 MD：五個 lane 的 `risk_flags` **全部**沒持久化、`key_factors` 只有 news 有、`sentiment_lane` 整塊不存在、per-lane raw signal/confidence 只有 valuation 有。單輸入會讓報告掉約 80 行——而那 80 行正是人真正在讀的證據段。**判準：backlog 條目描述的是動工前的理解，動工第一件事是驗證那個理解還成立。**這跟 4.83.0 記的「UI 類 TODO 先 grep 現況」同一形狀，但這次過期的不是 UI 狀態而是**資料模型假設**，代價大得多。
- **修法選「多一個 artifact」而不是「改 schema」，理由是避免跟 C1 對撞。** 把 lane 欄位補進 export schema 看起來更乾淨，但「per-lane 該持久化哪些欄位」正是 C1 要定的主題——現在定等於預判 C1 的設計，C1 落地時同一塊結構要再遷移一次、向後相容矩陣做兩遍。**判準：當一個修法會替尚未定案的上游決策先做選擇時，改走不預判的那條路，即使它多一個中間產物。**缺口清單已原文寫進 C1 條目當 design 輸入，`phase_inputs/` 那批檔案順帶成為 C1 的實測樣本。
- **雙輸入的代價是兩源漂移，所以硬閘先於渲染。** bundle 與 history 重疊 12 欄，任一不符 rc=1 且**不產出任何檔案**。最有價值的是拿 `calculation_steps` 的 step 字串當證人——那裡記著決策數學實際吃到的 score 與量化後 c_eff，比兩份 JSON 互比更接近真相。
- **硬閘第一版就差點誤判每一筆 CONFIRMED entry。** MU 的 `calculation_steps.val` 是 `0.15 × -1.5 × 0.60 = …  // Step 1.5 CONFIRMED: … score 0.0 → -1.5`，而 `valuation_lane.score` 是 0.0——兩者**應該**不同，那是 Step 1.5 的設計。若照「step 分數必須等於 lane 分數」硬比，每筆 CONFIRMED 都會被判漂移。改成：帶 `//` 註記的 step 只驗 c_eff 不驗 score。**教訓：寫一致性檢查時，先找出「合法的不一致」有哪些，否則檢查會把設計當成 bug。**
- **`--polish` 的真正風險是編數字，不是文筆。** 三道守衛裡數字圍堵最關鍵：潤飾段每個數字都要能在事實集合裡找到（含百分比與 0-4 dp 四捨五入形式）。寫測試時我第一版拿「Azure +43%」當假數字，結果守衛放行——查下去 43 確實在 bundle 的 news key_factors 裡，**守衛是對的、我的 fixture 挑錯數字**。換成 91.7% 才真的測到。**判準：負向測試要先確認「那個壞值真的壞」，否則測到的是自己的誤解。**
- **全部守衛 fail-open**：LLM 回非 JSON、router 拋例外、段落夾帶 `#`／`|`／HTML 註解、數字編造——一律丟棄該段回退制式句，rc 恆為 0。報告永遠產得出來，polish 只能讓它更好看不能讓它產不出來。
- **review 之後：量了才知道數字圍堵比我寫的說法弱。** reviewer 指出「上漲 9%」這種小整數百分比會被 `≤12 豁免` 放行，我去收緊「帶單位不吃豁免」，結果測試還是綠的——查下去發現 **9.0 / 7.0 / 8.0 本身就是 entry 裡的原始數字**，而且一筆 MSFT 的事實集合覆蓋 1–30 幾乎所有整數（原始值 + 大數字 0-dp 四捨五入）。也就是說 reviewer 提的修法治不了他提的症狀。**教訓：收緊一道檢查之前先量它現在到底擋掉多少，否則你改的是自己想像中的守衛。**最後做三件事：單位規則照留（豁免不該無條件給）、移除 `_fact_forms` 的 `v/100` 分支（prose 不會把 6.47 寫成 0.0647，那分支純粹放寬）、**把上限寫進 docstring 與測試**——擋的是「從無到有」，不是「剛好撞上」。
- **回填只回填得起的那一份。** phase_inputs 樣本數為零違反這功能自己立的教義，所以回填 MSFT（內容逐字取自已發布報告，標 `provenance.captured=backfill`，過硬閘 0 error）。**MU 刻意不回填**——它在測試裡的 lane 證據是我為了測 calculation_steps 硬閘現編的合成資料，寫進稽核目錄等於放一份假 Phase 2 證據。已發布報告一律不覆寫。**判準：補樣本是為了讓稽核軌跡完整，用假資料補會讓它比空的更糟。**
- **驗收**：`test_render_investment_report.py` A-F 六組 rc=0（golden 逐位元穩定 + FACTS 與 `inject_report_facts` 同源、decision-lock 逐項到頁、12 欄逐一漂移偵測、Step 1.5 覆寫不誤判、polish 三守衛含圍堵上限、CLI rc=1 不產檔）；`test_trade_plan_builder.py` 補 Fixture R 6 組補上 4.86.2 反解 cap 的零覆蓋；MSFT 347 行 / MU 307 行實渲染（輸出到暫存區驗證，未覆寫已發布報告）皆過 `validate_markdown_export.py` rc=0；SYNC OK 4.87.0。
- **覆蓋率邊界（使用者要求明寫，免得「測試全綠」被誤讀成「真實資料驗證過」）**。收尾時掃了全庫 172 筆 trade：**渲染 172/172 不崩、逐筆過 `validate_markdown_export` 172/172、0 筆輸出 <150 行**——形狀相容性是真的驗過了（那三處相容碼本來就是加第 2 筆才逼出來的，掃完其餘 170 筆沒再冒出第 4 種形狀）。但兩條路徑**仍靠合成 fixture 撐著**：(a) `calculation_steps` 全庫只有 **2 筆**，且 corpus 裡**沒有任何一筆 stamped V5.1**，所以硬閘最強的那半（比對 step 字串的 score / c_eff）真實樣本 = 1 筆 MU；(b) replay 反解的兩個 Phase 3 cap 在真實語料裡**全部是 100/100**（factor 1.0），Fixture R 的 50/25 路徑六組全是合成的。另有 **94 筆（55%）是 V4.6/V4.8 4-lane 時代，沒有 MHP / fair_value_summary**，渲染出來 §6 整段 N/A——骨架正確但不適合拿去回填舊報告。這三條都要等實際跑幾次 deep dive 才會長出真樣本，與 `phase_inputs/` 樣本數同一情況。

## 🟢 Session Note (v4.86.2) — P3 尾款四件（sector 同義詞 / 反解漏 cap / spec 補值 / backoff 釘死）
- **兩個標成 P3 的其實會產生錯誤數字，不只是噪音。** sector 同義詞看起來是「消 warning」，但四個 FMP 拼法裡三個落在保守側只是吵，`Consumer Defensive` 是**真的誤類**——staples 被當 cyclical 收緊停損。反解漏 cap 看起來是「replay 精度」，實際是一筆 50/25 雙 cap 的 entry 會偽裝成 `matched`（實測 size 5% 應反解出 40% base、超上限，修前 matched 修後 mismatched）。**判準：P3 的嚴重度標記是憑第一印象給的，動工時要用「這條會不會讓某個數字錯」重問一次。**
- **backoff 那條原本的修法會失效，寫測試前先在紙上跑才發現。** 我第一版用 `fetched == 0` 當 outage 判準：全批失敗 = FMP 掛了，就不累計 streak。但第二輪之後殘餘批次**只剩那些永遠空的 symbol**，`fetched` 必然是 0 → 永遠判成 outage → 隔離永遠不會發生，正是要修的情境。**教訓：用「整批表現」推斷單一 symbol 的性質，在殘餘批次收斂之後必然失真。**改成讓 `_fetch_pe_ttm` 直接分辨「三個 endpoint 都回了、都沒 row」（`PE_ABSENT`）與「根本沒答」（`None`）——這是 4.85.0 那條「加 retry 之前先讓函式有能力表達失敗」的下一格：**先讓函式有能力表達「答了但沒有」，重試策略才有東西可依據。**
- **反解的兩種缺值要分開處理。** V5.1+ 的 cap 躺在 `calculation_steps` 裡但欄位讀不到 → 退出 cohort（不假設 1.0）；pre-V5.1 根本沒紀錄 → 仍假設 1.0，但寫成具名 factor 進輸出。**「無從得知」與「讀取失敗」的降級方向不同：前者標記後續行，後者退出。**
- **驗收**：`test_trade_plan_builder.py`（sector 補 5 條）/ `test_heatmap_pe_retry.py`（補契約 6、7：空資料隔離 + outage 不得隔離）/ `test_decision_engine.py` / `validate_session_export.py` / `replay_trade_plan.py` 全 rc=0；replay 三 cohort 覆蓋數與修前一致（eligible 47、mismatch 0）；OPS §7 heatmap 那列同步新契約；SYNC OK 4.86.2。

## 🟢 Session Note (v4.86.1) — `sized_for_decision` 防偽收尾
- **我為了修 P1 引入一個豁免欄位，然後只測了它會報錯的那一側。** `sized_for_decision` 的作用就是覆寫 STAGED_ENTRY 折半規則，所以在 STAGED_ENTRY 的 export 上宣告 `"BUY"`，兩倍大的鏈就原地過關（實測 errors=0）。tamper 測試蓋的是「sized_for=STAGED 但沒折半 → rc=1」，那是**會觸發檢查**的方向；漏的是**把檢查關掉**的方向。**判準：一個用來豁免某條規則的欄位，最該測的是它被拿來濫用豁免的情形。**這跟 4.81.0 記的「tamper 要包含標籤說謊而不只是數字說謊」是同一個形狀——同一課我在新欄位上又犯一次，說明那條教訓當初只記成了「cascade 標籤」的特例，沒抽象成「凡是能改變檢查行為的欄位都要反向測」。
- **第一次重現失敗，差點誤判成不存在**：照 reviewer 的描述постро fixture 直接跑，結果 rc=1，看起來像是已經擋住了。細看錯誤訊息才發現擋它的是 §13 的 band 可達性（fixture 的 final_score 2.1888 band 到 BUY，STAGED_ENTRY 本來就不可達），跟 §14 無關。改用 `run_phase3()` 現跑一條**真的落在 STAGED 帶**的鏈（final_score 1.08）才暴露出來。**教訓：rc=1 不等於「被你想測的那條規則擋住」，要讀錯誤訊息確認是誰擋的。**新的 `staged_entry_fixture()` 就是為此存在，並且在 engine 不回 STAGED_ENTRY 時直接讓測試紅掉，不讓 fixture 悄悄退化。
- **修法是列舉合法分歧而不是放寬**：Phase 4 定倉之後能合法改寫決策的只有兩件事（`approval=REJECTED`、`decision_cap_active=true`），其餘一律要求 `sized_for == final_decision`。實跑 builder 三種決策輸入確認都自然滿足這條，不會誤傷正常路徑。
- **驗收**：schema battery 55 條（新增逃逸方向 5 條）；8 支測試 + validator + 兩個 replay 全 rc=0；builder 實跑 BUY / STAGED_ENTRY / HOLD 三種輸入 `sized_for` 皆與 `final_decision` 一致；SYNC OK 4.86.1。

## 🟢 Session Note (v4.86.0) — 4.82–4.85 review 修正（1 P1 + 7 P2）
- **八條先逐一複跑重現才動手**，沒有照單全收。結果全部屬實，但有一條的嚴重度我下修了：reviewer 說 §14 有「三條路徑全炸」，實測第三條（probe capped）的失敗是 fixture 產物（那條鏈是照 BUY 算的），probe 分支本身是對的。P1 是**兩條** Phase 4.6 路徑。**判準：確認 bug 為真之後，仍要確認它的邊界在哪。**
- **七個 P2 裡有五個是我自己在 4.82–4.85 引入的**，其中兩個是同一種病：**修了 A 卻打開 B**。`_fetch_pe_ttm` 的失敗語意一改，radar 懶抓那條路就從「每天 3 個 call」變成「每小時 60 個、無限期」，因為它的重試原本就是靠「失敗會被快取」這個副作用擋住的。**教訓：改共用函式的失敗語意時，先列出所有呼叫端，逐一問「這條路的重試由誰負責」**——radar 的答案是「沒有人」，而我在程式註解裡寫的是「warm-up 的 sweep 會管」，事實上那個 sweep 只掃 universe。**註解寫了一個我沒驗證的機制，這比程式錯更危險，因為下一個人會信它。**
- **cooldown 跨日被清除是最刺的一條**：我當時就在重寫那個 rollover 分支、還特地寫了「時間戳不能歸零」的長註解，卻只搬了 `call_timestamps`，沒問「同一個 blank 重建還丟掉了什麼別的、也不屬於 UTC 日的東西」。**判準：把某欄位從「隨日重置」救出來時，要掃過同一個 reset 裡的每一欄，逐欄問它到底屬不屬於那個週期。**
- **P1 選擇補欄而不是放寬檢查**：Phase 4.6 改寫決策後，`final_decision` 不再能解釋 sizing 鏈（折半該不該套）。可以把檢查放寬成「兩種都接受」，但那會讓真正該折半卻沒折半的鏈也過關。改成讓 engine 記下 `sized_for_decision`（它自己的輸入），檢查照舊嚴格。**歧義的正解是消除歧義，不是接受兩種答案。**
- **有一條刻意不修**：window 管不到 protocol subprocess 路徑（`note_run` 一次 agentic run 只記 1 筆，實際幾十到幾百 turn）。把那條路納管會讓使用者主動點的操作被背景配額擋掉——那是行為變更，該由使用者定奪。我只把 docstring 改成事實（「governed calls，不是 API turns」）並明講依此 cap 對應 provider turn budget 保護不了那條路。**說謊的 docstring 要修；要不要改行為是另一個決定。**
- **併發鎖補在對的層**：`llm_usage.json` 的單次寫入本來就 atomic，壞的是 read-modify-write。flock 加在**獨立的 `.lock` 檔**上，因為 `os.replace` 會把 usage 檔的 inode 換掉，鎖在它自己身上沒有意義。
- **驗收**：8 支測試 + 3 個 validator/replay 全 rc=0；`test_session_export_schema.py` 50 案（新增 §14 × Phase 4.6 五案）；router 新增 cooldown 跨日 / 過期不復活 / >48h window / 時鐘故障 / roundtrip / 24 執行緒併發；heatmap 新增 mid-batch 429 partial / 非重入 / lazy retry floor。commit 排除 `data.json` / `llm_usage.json` 兩個 runtime artifact（上一版夾帶進去被 review 點名）。SYNC OK 4.86.0。

## 🟢 Session Note (v4.85.0) — heatmap PE warm-up 重試（V325.X-PE-WARMUP-RETRY）
- **TODO 描述的症狀對，病因更嚴重**：記的是「cache 空到下次重啟」。實際讀 code 發現 `_fetch_pe_ttm` 在 429 熔斷期回傳**全 None 的 dict** —— 跟「這支股票本來就沒 P/E」完全同形。而 `val_snapshot` 的過濾條件是 `isinstance(v[1], dict)`，全 None dict **通過了**。所以失敗值不只被快取 24 小時，還會被當成事實**蓋掉既有的好值**。**教訓：修 bug 前先讀清楚失敗值長什麼樣，不要照 TODO 的描述直接動手。**
- **根因是型別分不出兩件事**：「抓到了但沒有資料」vs「根本沒去抓 / 抓失敗」在原本的回傳型別上是同一個東西。加 retry 之前要先讓函式**有能力表達失敗**（改回 `None`），否則重試邏輯只是在重試一個它以為成功的東西。
- **失敗不進快取，比「快取失敗但標記」更簡單也更安全**：舊值留著就是最好的降級（stale 好過空白），而失敗的 ticker 自動落回 `todo`（因為 `not isinstance(cached[1], dict)`），不需要第二份失敗清單。
- **429 熔斷不該計 backoff**：熔斷期根本沒發請求，記一次失敗是懲罰錯對象；改成把下次嘗試時間對齊熔斷解除時間。
- **兩個 caller 都要修**：radar 的 lazy fetch `_bg()` 也在快取 None，會佔住 24h TTL 並讓 warm-up 的重試掃描看不到那支 ticker。
- **驗收**：`tests/test_heatmap_pe_retry.py` rc=0（部分失敗 / backoff 抑制 / 補抓不重抓已成功者 / 失敗不洗掉好值 / escalate 且有上限 / 429 不計失敗 / 全暖零 HTTP）；`dashboard_server.py` 語法 OK；SYNC OK 4.85.0。

## 🟢 Session Note (v4.84.0) — model router rolling window（V321.X-ROUTER）
- **本版最重要的一行是「不要歸零」**：`_load_usage()` 原本在 UTC 換日時整份重建。日計數該歸零，但 `call_timestamps` **不能** —— session window 不理會午夜，跟著清空等於在 00:00 UTC 憑空發還一整個 window 的額度，正好是這個計數器要防的事故。這是整個功能唯一真正微妙的地方，測試特地寫了一條跨午夜案例。
- **測試通過但功能沒生效，抓到的是最典型的一種假綠燈**：`--status` 顯示 `window_max_calls: null`，查下去發現 `load_llm_config()` 是**逐鍵白名單**不是 merge，只複製 `daily_max_calls`，我新加的兩個 key 被靜默丟掉。單元測試全過是因為它們餵手搭的 cfg dict，繞過了 loader。**教訓：新增 config key 一定要有一條走真 loader + 真 config 檔的 end-to-end 斷言**，否則測的是自己餵進去的東西。已加，並寫進 OPS §7。
- **降級方向再次一致**：時鐘偏移到未來的時間戳「照算」（丟掉會少算 window）、naive timestamp 當 UTC 讀（丟掉同樣少算）、解析失敗的才忽略。原則是**寧可少給額度也不要多給**。
- **兩道閘獨立而不是取代**：daily budget 與 window 各自能單獨擋下一個 model，`model_headroom()` 回較緊者 —— 呼叫端打算連發 N 次時，不能被日額度騙過去。
- **只有 session-window 制的 CLI 設 window**（claude / codex）；gemini / grok 是 per-minute rate limit，硬套 5hr window 是張冠李戴，留空 = 不設閘（與 `daily_max_calls` 缺/0 同慣例）。
- **驗收**：`test_model_router_window.py` rc=0（含跨午夜、舊 shape、corrupt 檔、loader end-to-end）；`--status` 四個 model 的 window 欄位皆正確（claude 0/120、codex 0/80、gemini/grok null）；`/api/llm-config` POST 的 merge 不會洗掉新 key；SYNC OK 4.84.0。

## 🟢 Session Note (v4.83.0) — decision badge 改吃決策時真值（V20-A5）
- **TODO 過期了，動工前先查證**：V20-A1 / A2 寫著「已存 data.json，UI 沒秀」，實際上 badge 與 `SIGNAL_TIPS` 兩邊都在，更早的版本就做掉了（`ALIGNED` / `unclassified` 兩個良性值刻意不發 badge，與 `macro_alignment` 只標 CONTRARIAN 同一慣例——那是設計不是遺漏）。**教訓：UI 類 TODO 動工前先跑一次 grep 確認現況，backlog 會比 code 舊。**
- **但 A5 不是「只省一層 `.det_shadow`」**：renderer 原本**只**讀 `det_shadow`，那是 `apply_det_shadow.py` 事後補寫的 shadow；V5.1+ entry 的 `calculation_steps` 才是決策當下真的動了分數的值（confidence 乘數 / position cap / buy_threshold / cascade 罰則）。兩者理應相同但來源不同，badge 顯示錯的那個不會有人發現。改成 **決策時優先、shadow fallback**，並把 `*_source` 一起送出去。
- **有了兩個來源就該驗它們一致**：加 `*_disagrees` + 兩個 SPLIT badge（與既有 `RT DISAGREE` / `VAL DISAGREE` 同一套視覺語言）。不一致代表後處理跑的時候看到的 lane scores / counter_thesis 文字跟決策當下不同 —— 通常是 entry 被事後編輯。現行 172 筆 0 不一致（健康），但這是往後才會用到的哨兵。
- **fallback 留著是為了不綁 bridge 重跑**：renderer 讀不到攤平欄位就退回 `det_shadow`，還沒重生成的 `data.json` 照樣渲染。
- **驗收**：`bridge.extract_audit_history()` 實跑 192 筆，2 筆 source=calculation_steps（V5.1 那兩筆）、67/170 筆 source=det_shadow、0 筆 disagree；`node --check` 兩檔語法 OK；SYNC OK 4.83.0。

## 🟢 Session Note (v4.82.0) — Phase 4 script 化（TODO L2）
- **起因**：Phase 3 已在 4.80.0 script 化，Phase 4 是最後一塊仍靠 LLM 手算的決策數學（九段乘法鏈 + 兩張查表 + 一個條件 reject + 兩個獨立導出的停損價要調和）。
- **先跑 feasibility 再定分母，這次證明是對的**：動工前掃 172 筆 history —— `vol_adjusted_limit_pct` 持久化 **0 筆**、`tail_risk_score` 1 筆。sizing 鏈根本無法前向 replay，硬做出來的「100% parity」會是假的。改用 **inverse solve**（把已知乘數除回去、檢查隱含 base 是否落在 (0, 20%] 可行區間），47/172 全過。**教訓：replay harness 的第一步是量分母，不是寫比對邏輯。**
- **`min()` 不可逆這件事值得記**：macro cap 是 `min(tail_adj, 0.03)` 不是乘法，鏈上只留數字就無法從尾部反推它有沒有觸發。這批 trade 直接整批排除（`macro_cap_min_not_invertible`）而不是硬解一個假因子。存 `sizing_chain.steps[]` 就是為了讓未來的 entry 不必再走這條退路。
- **replay 抓到 engine 的真 bug**（不是它本來要找的東西）：`band_capped` 是 `[max(band_lower, support), band_point, min(band_upper, resistance)]`，support 高過 band_point 時兩軌會產出 `[高, 低]` —— 歷史上 AAPL/PLTR/TSM 三筆命中。**教訓：replay 跑歷史資料時，異常的「replay 值」和異常的「stored 值」一樣值得看。**我第一眼只在讀 stored 那欄。
- **rule-era 一開始標錯，rc=1 是假的**：R/R cohort 我先寫死 `era="current"`，40 筆全變 NEEDS_TRIAGE。但 V4.82.0 之前根本沒有任何 script 強制 entry = band 或 R/R = 區間隱含值 —— 那 40 筆量的是本版要消除的漂移，不是 engine 缺陷。三個 cohort 統一綁 `CURRENT_RULES_SINCE`。**判準：問「這條規則當時存在嗎」，不是「這個欄位當時存在嗎」。**
- **protocol 有三處原文沒定義，script 化才浮出來**：① `base_stop_pct` 從未被獨立定義（採「結構停損價相對 entry reference 的百分比」，唯一能讓 Step 1 與 Step 4 談論同一個部位的讀法）；② binary `× 0.5-0.7` 是區間，一律取保守端 0.5 才可重現；③「R/R 不足 → 收緊 entry 或降級 HOLD」沒說收到哪，定為 aggressive 中點 → conservative 中點 → conservative 下界。**三處都寫回 protocol，不是只寫進 code。**
- **降級一律往保守側，且要說出口**：tail_risk 拿不到時取 `MODERATE ×0.75` 不取 ROBUST（把最大乘數給最不了解的情況）；表外 sector 取 cyclical；day-21 reject 的 RS/distance 兩個輸入都缺時「不 reject 但維持 ×0.50」並註記「無法判定」——**缺料 ≠ 通過**。同理 F1 registry 不可得時標 `registry_unavailable` 而不是回報 0 個部位。
- **順手補一個洞**：`fragility_label` 值域從來沒驗過（§6 只驗非 null），歷史上有 6 筆用了表外標籤（`RESILIENT` / `MEDIUM`），Step 3 乘數無從對應。是 replay 的 sizing cohort 排除表跳出來的。
- **驗收**：`test_trade_plan_builder.py` 17 組 rc=0；`test_session_export_schema.py` 45 條（含 18 條新 §14 tamper）rc=0；`replay_trade_plan.py` 三 cohort `current_rule_mismatched=0` rc=0；`replay_decision_engine.py` / `test_decision_engine.py` / live validator 全 rc=0；SYNC OK 4.82.0。

<!-- 批次輪替制：主檔超過 20 個 Session Note 時跑 `python3 scripts/rotate_session_notes.py`，最舊 10 個自動切成 archive/session_notes_v<A>_to_v<B>.md。查舊版本：Grep 版號於 archive/session_notes_v*.md（規則：docs/agent-ops/MAINTENANCE.md §3） -->

## 🔵 Momentum Context (Multi-Universe)
**動能選股 Universe 整合機制**。
- **(1) 市場狀態**：目前預設掃描 `all` (SP500 + Nasdaq 100 + Watchlist)，總數 527 檔。
- **(5) 數據結構**：CSV/JSON 新增 `in_nasdaq100` 布林欄位。
- **(4) UI 連動**：Dashboard 預設顯示 Top 200，但透過 `isWatchlist` 邏輯，自選股不受 Universe 篩選器影響，始終顯示。

---

> **📜 完整版本歷史已移至 [`CHANGELOG.md`](./CHANGELOG.md)** — 自 v1.0.0（2026-04-09 初始）至目前全部 entries，含 git commit 引用與 evolution highlights。

---

## 📋 Bridge 資料流對照（System Manifest）

| Protocol | 輸出 Log | Bridge 讀取欄位 | Dashboard 顯示 |
|---|---|---|---|
| `investment_v5_0` | `invest_logs/history.json` | `final_decision`, `score`, `macro_alignment`, `key_risks` | decisions 頁全部 |
| `sector_v1.3` | `sector_logs/*_intel.json` | `market_regime`, `_phase0` (breadth/FTD/MT), `today_verdict` | index + sector |
| `news_v2.1` | `news_logs/*_digest.json` | `verdicts[]`, `trump_signals`, `catalysts` | news 頁 + sidebar |
| `breadth_analyzer`| `breadth_cache/*.json` | 6 組件 breadth + trend | index 廣度 gauge |
| `positions.json`  | — | lots → avg_cost / live_position | decisions 持倉 |
