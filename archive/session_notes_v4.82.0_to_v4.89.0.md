# Session Notes 歸檔 v4.82.0 → v4.89.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

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
