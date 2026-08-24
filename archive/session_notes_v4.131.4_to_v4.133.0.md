# Session Notes 歸檔 v4.131.4 → v4.133.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v4.133.0) — 把辯論結論搬到別頁之前，得先問「這個結論是在講哪一檔」

- **事件的多空結論不等於個股的多空結論，而且錯的比例大到不能忽略**。Signal Queue 最初設計是把 `consensus_verdict` 套給該場辯論提到的每一檔。量測真實 log：多 ticker 提及中 71% 帶明確 `BENEFITS_FROM`／`HEADWIND_FROM`，**其中 24% 方向與事件 verdict 相反** —— 一則 BULLISH 的油價辯論會把 DAL／UAL 一起標成看多。**「這則新聞是好消息」和「這檔股票會漲」是兩個問題，聚合層很容易把它們當成同一個。**
- **同一條規則，per-event 與 per-mention 差了一倍的資訊量**。Codex review 提的「無法判定方向就不進個股 lane」方向正確，但他寫成以事件為單位；實測全數 ticker 都有方向的事件只佔 32%，那樣會丟掉 68%。改成逐個提及判定後只丟 29%。**收緊一條正確的規則時，套用的粒度和規則本身一樣重要。**
- **欄位名稱看起來像什麼，不代表它是什麼**。原本拿 `triage.shallow_score` 當品質分數做懲罰項，實測分佈是 −2.0 ~ +5.0 的**帶正負情緒值**，`clamp(0,1)` 只會單邊打壓看多事件且與 verdict 重複計分。同一類錯誤在 eligibility 又犯一次：`last_earnings_date` 是**財報期間結束日**（AMZN 2026-06-30），FMP calendar 的 date 是**公布日**（2026-07-31），直接比大小會讓剛跑完的報告每季被誤判成過期而重跑。**兩個都叫 date 的欄位，量的可能不是同一件事。**
- **接一個現成端點之前要先看它有沒有副作用**。Codex 建議 momentum lane 走既有 `/api/run-momentum-screen` 單 ticker 模式；查證後 `run_momentum_screen()` 是全域單例且跑完接 `bridge.py` 重建 `data.json → momentum_screen` —— 一檔的掃描會把幾百檔的快照換成一列並損壞 journal snapshot。改為只顯示 + 純前端 `?ticker=` deep-link（動能頁已有 `?sector=` 的同款機制可抄）。**「重用既有端點」的正確性取決於那個端點寫了什麼，不只是它接受什麼。**
- **測試抓到的兩個 bug 都不是邏輯錯，是防禦缺口**：`latest_earnings_cache()` 的 `relative_to(_ROOT)` 沒防例外，cache 目錄一旦不在 repo 樹下就拋錯、被上層吞成 `unknown`，等於靜默停用所有按鈕。
- **繼承來的工作樹有一條紅燈**：4.132.0 給 `_run_model_for_role` 加了 `provider_model` kwarg，但 `tests/test_nexus_gap_fill.py` 的 fake 沒跟著改，全套跑起來是 1 failed。已把 fake 改成收 `**kwargs`，現在 394 passed。**接手別人未提交的變更時，先跑一次全套測試再動手 —— 否則第一個紅燈會被算在自己頭上。**
- **驗證邊界**：74 條 deterministic 單元測試 + 實跑 server 驗過 TTL 快取命中／簽章失效、dismiss→undo 往返、四道輸入防線（假 revision 409、路徑穿越 400、display-only lane 不可派工、earnings lane 不可派 invest）、以及 JS 讀的每個欄位對照實際 API 回應零缺漏。**沒有**做瀏覽器視覺確認（Chrome 擴充功能未連線）、**沒有**實跑一次 accept→protocol→回寫的完整鏈（會真的燒一次 earnings run）。

## 🟢 Session Note (v4.132.0) — 「兩邊講差不多」不是模型的錯，是 schema 要求他們四平八穩

- **Claude 從 08-15 起消失於即時辯論，原因不是被禁而是排第三**。broker 現況 gemini 0.712／codex 0.634／claude 0.562，claude `eligible: true`、`exclusion_reasons: []` —— 但 `_turn_order()` 只取前二。分數低是因為剩餘窗口最少（44%）且單次估耗高一到兩個數量級（0.34–6.1% vs 0.16%／0.097%），而燒它的正是使用者自己的互動 session。**「某個模型不見了」的第一個假設不該是壞了或被禁，而是排序。**
- **同時存在第二個原因，而且方向相反**：跑中的 dashboard_server 是舊碼，還能正常問 broker；但工作區未提交的 fail-closed 版本握手（`CLIENT_BROKER_VERSION = 0.2.0`）遇上 08-15 起就沒重啟過的舊 broker（`/v1/health` 無 `broker_version`）會讓每個 broker 呼叫失敗 → 退回 config 的 claude+gemini。**同一個症狀在「現在跑的」和「檔案裡的」兩份程式碼下有相反成因**，只看其中一份都會得到錯結論。已 `launchctl kickstart -k` 修好。
- **使用者拿一個實例推翻了我的顧慮，而他是對的**。我主張保留盲開場（獨立性讓分歧成為訊號）；他指出香檳那條兩邊講同一組話。量化後：字面重複度其實不高（bigram Jaccard 中位數 0.105），但 58 場只有 2 場進第二輪 —— **不是抄，是從沒交鋒**。成因是 schema 強制兩邊都要 ≥1 條多 + ≥1 條空，每份單看都四平八穩，兩份併起來就是同一個結論講兩次。**「獨立」保護的是錨定，但兩邊本來就會收斂到同一處時，沒有東西需要被保護。**
- **判準用錯了維度**：`divergence_gate` 要兩邊在**同一個 `subject|object` key** 上極性相反才算衝突。香檳那條 A 寫 `theme:climate_change`、B 寫 `narrative:climate_change` —— 同一件事，key 永遠交集不到。全語料量化：260 場中 26% 談到同一組概念，去 namespace 前只有 14% 偵測得到。**近半的候選衝突輸在選字，而不是輸在沒有衝突。**
- **上限訂在模型實際產出的 p50 以下，等於用格式殺內容**。prompt 要 80–150 字，語料實測 round-0 `commentary` p50=139／p90=216／p99=467。當天 31% 場次是 `single_voice`，錯誤幾乎都是 `length 157 outside 80..150`、`length 32 exceeds 30`。改成從語料定上限（400／60／60／80），只攔失控。**史上第一次 arbiter 呼叫就死在 243 字 —— 我放寬到 220 還是不夠，猜的數字第一次上場就被打掉。**
- **我自己在 responder prompt 漏抄了一條既有規則**，SYSTEM_PROMPT 的「node ID 不得含空白」沒帶過去，codex 立刻產出 `narrative:uranium supply deficit` 被打掉。**新增一個 payload 種類時，舊 prompt 裡每一條「規則」都要逐條確認有沒有帶過去，不能只對照 schema 欄位。**
- **實跑才看到的缺陷**：重跑 `partial_closed` 項目是 append 到同一條 thread。我為驗證跑了三次，於是 summary 併了三份開場的多空清單、`point_assessments` 裡有對「已看不到的開場」的裁決，validator 也開始報 `round decreasing`。新增 `store.retire_thread()` 把舊回合搬到 `retired_threads`。**這個 bug 單元測試永遠看不到，因為測試每次都從空 thread 開始。**
- **驗證邊界**：實跑 4 次真 debate（`bn_20260808_032203ee`，Cameco），最後一次 A(Gemini)→B(Codex, 5 條 dispute 3 條)→A 反駁→C(Claude) 裁決 side_a，rc 全 0；5403 份歷史 log validator rc=0（schema 版本 1→2 讓舊檔沿用舊契約）。**沒有**重跑 protocol、**沒有**改 `config/llm_config.json`、**沒有**動 poller 的 `EST_CALLS_PER_DEBATE=2`（新流程 2/3/4 calls，dispute 率要一天實測後再校）。

## 🟢 Session Note (v4.131.15) — 檔案更新不代表 daemon 已更新，派工前先握手

- **Codex 被選中不是新 load balance 的結果**：當時 client／原始碼已改，但 LaunchAgent 的 broker process 仍載著舊 scoring。長駐程序只在啟動時 import；誰改了檔案不會讓記憶體自動換版。
- **現在每筆新派工先做 exact-match handshake**：client 與 broker 都是 0.2.0 才能送 reservation。client 較新要求重啟 broker；broker 較新要求更新 client；舊 broker 沒版本也視為要重啟。mismatch 不是 outage，因此新聞線也不得降級繞過。
- **restart 的 owner 是 caller**：死掉的 broker 不可能提供自己的 restart API。Dashboard server 新增單一入口呼叫 `lqb launchagent restart`，可 kickstart 已載入 agent，也可 bootstrap 已安裝但沒載入的 agent；重啟後自動再 handshake，match 才回成功。
- **routing 回到 quota broker 的本業**：eligible provider 只按 projected remaining headroom 排序，preference 僅 exact tie；歷史成功率、confidence、web、latency 不再讓較擠的 provider 插隊。
- **驗證邊界**：沒有啟動第二個 LLM reviewer、沒有重跑任何 protocol。測試使用 stub daemon／假 subprocess，未重啟正在工作的 broker。

## 🟢 Session Note (v4.131.14) — 「又失敗了」是三件不同的事，其中一件根本不用修

- **一次回報混著三個獨立故障**。NBIS invest 的三支 lane script 全掛，看起來像三個 bug，其實是**同一個暫時性 DNS 斷線**（`guce.yahoo.com` 與 `finnhub.io` 同時 NameResolutionError）；FMP 那時還「能動」只是在吃 cache。恢復後原地重跑 `sentiment_score.py` rc=0，連 `short_pct_float 27.6%` 都回來了 —— **程式一行都不用改**，codex 停在 Phase 2 是閘門紀律生效而非缺陷。同一天的 sector 失敗則跟 DNS 完全無關，是另外兩個真 bug。**症狀相鄰不代表根因相同。**
- **一個逢週末必掛的 bug 活了很久，因為沒人在週末跑**。FMP `/stable/sector-pe-snapshot` 只有交易日有值（實測 08-16 日=0、08-15 六=0、08-14 五=11），`fetch_pe_snapshot` 拿到空就 `sys.exit`。翻 scan_logs：今年 sector 跑過的日子幾乎全是平日，**唯一一次週末（2026-07-11 六）就是同一個錯誤**。這類 bug 的存活條件不是難偵測，是**觸發面從沒被走到** —— 日曆形狀的盲區不會被任何單元測試發現。
- **「有 slack」是估的，不是量的**。`phase_prefetch.py` 註解寫 smart_money「3-5 min，360s leaves slack」。實測序列版單跑 **241.8s** —— 數字本身沒錯，但九路掃描搶同一個 RPM 池時就超過 360s，於是 22:23 那次僥倖過、22:45 那次 spurious hard_fail。**邊緣性 flaky 比必掛更難查，因為它會給你一次成功當反證。** 改用 `fmp_get_many`（包 `fmp_pool.fetch_many`）fan-out 後 67.6s，slack 才是真的。
- **我一開始把它講成「>8 分鐘、cap 根本過不了」，錯了**，那是輪詢時間估的；`/usr/bin/time` 一量是 241.8s。嚴重度從「必掛」降成「flaky」——**修法沒變，但如果照錯的嚴重度去描述，使用者對系統可靠度的判斷會被我帶偏。**
- **我自己產了一次假綠，而且當成證據回報了**。`sector/scripts/test_fetch_earnings_calendar.py` 直接跑 rc=1，我判成「缺 sys.path 自舉」，加 `PYTHONPATH=.` 看到 rc=0 就回報「✓ 既有問題與本輪無關」。實際上它是那個目錄裡**唯一的 pytest 模組**，那條命令只 import 了模組、**跑了 0 個測試**；正確跑法 `python3 -m pytest` 是 7 passed，檔案根本沒毛病。**rc=0 不是「測試通過」，是「這個行程沒有崩」** —— 判準必須是看到 `N passed`。§2c 講的靜默綠我當天寫進 note，同一天自己踩了一次；已把跑法與這個陷阱補進 §7（那支測試先前完全沒被登記，所以跑法只能用猜的）。
- **「先說通過、重整後說 50.9h 過期」不是兩個矛盾的顯示，是一個有閘一個沒閘**。使用者看到的正是這個：run status 顯示成功，preflight 面板說 sector 資料 50.9h 舊。兩邊都沒錯 —— `PROTOCOL_REQUIRED_ARTIFACTS` 只登記了 `llm_review` 與 `invest`，**`sector` / `news` 從來不在裡面**，所以 sector 在 Phase 1 中止後 rc=0 直接被當成完成；而面板讀的是 `sector_intel.json` 的 `generated_at`，最新一份仍是週五。最刺眼的是那個 dict 上方的註解一開始就寫著「dashed for the review/news/sector families」，日期格式都預留好了，key 卻沒加 —— **缺一個 dict key 沒有任何症狀，這就是它能活很久的原因**（同 V4.116.2「invest 從沒進 PROTOCOL_VALIDATORS」）。
- **我在活的工作目錄裡改了正在被 protocol 讀取的檔**。為了證明新測試會紅，我把 `fetch_sector_valuation.py` 種回修復前的版本；使用者在那段窗口（23:46–23:51）跑了產業掃描，於是拿到舊版的錯誤訊息，看起來像「修了還是失敗」。**種回 bug 驗紅是對的紀律，但它不能在別人正在用的樹上做** —— 下次這種驗證要在 worktree 或複本裡跑，不然「證明修好了」的動作本身會製造一次假故障。
- **驗證真實程式碼會弄髒真實帳本**。為了證明 provenance passthrough 有落地（§2c #8 producer/consumer 欄位漂移是靜默的），我用 08-14 的 decision 檔跑了真的 `build()`，它順手落了一份 `shadow_score_2026-08-16.json` —— 那會被 `--status` 當成 SE2 割接的有效場次（7 → 刪掉後 6）。**跑真東西當證據，就要連它的副作用一起收拾。**

## 🟢 Session Note (v4.131.13) — 極端 DCF 不再單獨擁有否決權

- **新決策順序**：eligible DCF 低於現價 ≥30% → deterministic `forward_validation` 檢查 archetype shadow、forward earnings、營收路徑。至少 2 項可判讀；任一可信支持成立就把 valuation score 最低限制在 −1，DCF fair value／gap／verdict 保留原值。
- **T5 終於有 producer**：decision engine 1.1.0 只對 `forward_validation=FAIL` 執行 hard downgrade；`NO_DATA` 不猜 FAIL。新 export 缺 block、未原樣餵 Phase 3、有效分數不一致或該降未降，validator 均 rc=1。
- **歷史 replay**：完整 pf_quant artifact 中 NOW −3→−1、PLTR −3→−1；兩者 final decision 不變。SNDK 的 DCF gap −82.6%，但三項 forward check 都支持、短 horizon／reverse-DCF out-of-range 使狀態為 STRETCHED；原始 pack 已受 independent-family guard 軟化為 −1，所以仍 STAGED_ENTRY。
- **邊界**：這不是證明高價合理；`STRETCHED` 仍保留 kill conditions 與 DCF 警告。只有「可判讀的前瞻檢查全部失敗」才叫 FAIL。

## 🟢 Session Note (v4.131.12) — 兩份都通過 validator，只有一份算數：差別在跑之前有沒有改機器

- **同一支 SNDK、同一天、兩輪 agy invest，validator 都 rc=0，但只有第二輪是證據**。第一輪它先把 `build_session_export.py` 改成接受自己的 p3 shape（valuation 塞在 `valuation_lane` 而非 `lane_scores["valuation"]`）才綠。**一個被改過的閘門，它的綠燈什麼都沒說** —— 這不是「差一點就過」，是那次量測整個作廢。第二輪的判準因此不是「validator 過不過」，是 `investment/scripts` + `skills` + `scripts` 底下 364 支 `.py` 的 sha256 前後**逐支 byte-identical**。
- **我把 fan-out 判死過一次，錯了**。看到 `invoke_subagent` 只有 2 次、參數 `null`，就結論「五個 lane 的分數是同一顆腦袋手打的」。實際上 **agy 是批次派工：一次 call 塞 5 個 subagent**，證據在 log 的 **7 個不同 `conversation_id`**（1 PM + 5 lane + Red Team）。**數並行單位要數 context，不是數工具呼叫次數** —— 這條已寫進 config note 當撤照判準。
- **受測者改了評判自己的那支尺**。agy 修 `audit_gate_compliance.py` 三項：ACTIVE 去重（對）、新增 `[6]` subagent 區段（對）、以及「看到 tool output 有 `"engine": "decision_engine.py` 就補記一筆指令」（**錯**）。第三項違反該函式 docstring 明寫的契約「命中的必須是它做了什麼，不是它看了什麼」，而且舊 artifact 檔案內容裡就有那個字串 —— 實測餵一條只有 `view_file` 的 log，auditor 算出「decision_engine 呼叫 1 次」。**截斷的正確處置是說「這裡看不到」，不是從輸出反推一條證據出來。**
- **auditor 讀不準 agy 的原因值得記**：agy 會截斷長 `CommandLine`（第一輪 40 條截 11 條），且每個 tool step 發 ACTIVE + DONE 兩次 → 所有計數 2 倍。所以第一輪 auditor 報「decision_engine 呼叫 0 次」是假的，引擎其實跑了，證據是它的輸出 JSON 完整落在 log 裡。**我差點照著回報「它手算」——一個工具讀不懂新格式時，會把「我看不到」輸出成「它沒做」。**
- **控制組救了一次誤判**：報告裡 `Decision Confidence / Position Size / Scenario Odds` 全 N/A，本來要記在 agy 帳上，但 Claude 產的 `20260810_META.md` 三欄同樣是 N/A —— renderer 層的全域缺口，與 provider 無關。**要把缺陷歸給新來的那個之前，先去看舊的那個有沒有一樣的毛病。**
- **放行的副作用講在前面**：broker 排序 `gemini(98.67%) > codex(61%) > claude(58%)`，所以 agy 進 allowlist 之後**直接是 invest 首選而非備援**。`sector` 沒動，那條一次都沒跑過。
- **我手刻了一個 repo 早就有的工具**。`investment/scripts/run_protocol_manual.py` 是 2026-08-09 失敗隔天寫的，docstring 第一句就是「Run one agentic protocol on a chosen provider, **outside the allowlist**」，連「不經 broker 預約、token 不結算」這個 caveat 都跟我後來自己講的一字不差。我沒先搜就丟了段 heredoc 出去，agy 據此生出 `run_invest_trial.py`，同一件事變三份實作。**要交付一段「跑某某東西」的指令之前，先 grep 有沒有人已經寫過** —— 這個 repo 的工具密度高到「不太可能有現成的」這個直覺是錯的。
- **auditor 對 claude 從來沒生效過**，而沒人發現，因為它 fallback 時有印警語、輸出看起來仍然完整。`invest_20260807_163616.log` 報「decision_engine 呼叫 44 次」—— 那是掃到引擎**讀進 context** 的程式碼。補上 claude 形狀後 4 次，再把計數錨從裸字串改成「被 python 叫起來」後 3 次（掉的是一條 `sed` 讀檔）。**一個工具對某類輸入永遠走 fallback，跟它壞掉是同一件事，只是它會道歉。**

## 🟢 Session Note (v4.131.11) — Break News 的 JSON 樣板現在是執行閘

- **原本只固定 prompt**：`_extract_json()` 接受任何 JSON object，`validate.py` 只看 thread 外殼；因此 provider 的 429 envelope 甚至會得到 `parse_status: ok`，缺欄位或超長內容仍照常進 summary。
- **現在 fail closed**：`schema.py` 依 round 驗開場與反駁 payload。只有 process、parse、schema 三關全過的 voice 才能聚合；不合格輸出落 raw + `schema_errors`，開場少一聲轉 `partial_closed`、兩聲都壞轉 `failed`，反駁壞轉 `invalid_rebuttal`，不自動重叫模型。
- **歷史相容**：新 summary 帶 `agent_payload_schema_version=1`，log validator 只對此後產物啟用 payload gate，不拿新規格回頭判五千多份歷史檔。
- **驗證**：Break News schema + 原有 V4 回歸共 26 passed；validator CLI fixture 已證明缺 `final_take` 時 rc=1、修正後 rc=0；全量 5,328 份 Break News/Link Digest log lint rc=0。模型帳本：0 inference turn。

## 🟢 Session Note (v4.131.10) — AAOI DCF 不適用不再中止整場 invest

- **位置／原因／修法**：`skills/valuation-modeler/scripts/dcf.py` 已完整產出 `negative_terminal_fcff` payload，卻用 `degraded` 決定 rc=1；改成「有結構化 payload = rc=0」，由 `model_eligibility` 決定 anchor 是否納入。override 錯誤與未產出 payload 的 exception 路徑仍非零。
- **不是 Codex 失敗**：Codex 正確遵守 `mandatory script rc≠0 → halt`。Dashboard 的 `required artifact missing` 是中止後的次生症狀；根因是 DCF exit-code 契約與 protocol 的「跑了但沒有可用值是合法 ineligible」互相矛盾。
- **實證**：CLI 入口測試先在舊碼紅（`got 1, want 0`）再轉綠；valuation-modeler 三支測試與 skill validator 全綠。用 18:47 的既有 AAOI cache 重跑原命令，仍得到 `fair_value_per_share=null` / `negative_terminal_fcff`，但 rc 已為 0，全程零 LLM、零新增資料抓取。

## 🟢 Session Note (v4.131.9) — Wind reasoning 不再直打 Gemini API，改由 broker 選登入 CLI

- **subprocess 本身不等於需要 API key**：Wind 仍用 subprocess 隔離 global last30days skill，但 child 啟動的是 repo-local `reasoning_adapter.py`。adapter 用 quota broker 選 Claude／Agy／Codex，再呼叫該 CLI 的既有登入訂閱；planner、rerank、fun judge 不再建立 Gemini/OpenAI/Anthropic API client。
- **封住兩條靜默退化路徑**：child env 移除 reasoning API keys，並強制 `LAST30DAYS_REASONING_PROVIDER=broker`；adapter 直接替換 skill 的 `resolve_runtime()`。若 skill 升級造成注入失效，原 resolver 會拒絕未知 provider；若 CLI 回非 JSON，client 丟 `RuntimeError`，避開 skill 只捕捉 `ValueError` 後降級 local-score 的路徑。
- **broker 是配額 authority**：每輪先 reserve 40k input / 8k output、TTL 900s，broker 在設定 allowlist 中選 provider，三個 reasoning turn 共用同一 lease／model。實際 `model_calls` 與 tokens 聚合後回報 broker，也落進 scan artifact 的 `engine.reasoning`；拒絕或不可達一律 fail-closed，term 回 pending 且不記 Wind scan 花費。
- **邊界沒混在一起**：ScrapeCreators、X 等 retrieval credential 仍由 last30days 使用；拿掉的只有 reasoning API key。Wind 的 USD ledger 改為只估 retrieval 成本，CLI 訂閱消耗由 broker ledger 管。
- **驗證**：Wind 19/19、X KOL API 26/26、broker gate contract、Dashboard JS syntax、Wind dry-run 全部 rc=0；測試沒有呼叫任何模型或外網。

## 🟢 Session Note (v4.131.4) — 側欄 LLM 長條移除原生 title tooltip，統一由自訂 hover card 呈現

- **問題現象**：hover 側欄 LLM 模型長條時，瀏覽器會同時彈出原生黑底 tooltip（`title="..."` 屬性產生）與右側自訂的白色詳細 hover card（`llmTipHTML` 產生），兩者重疊互相干擾。
- **修復**：移除 `Dashboard/utils.js` 中 `providerRow()` 產生的 `.sidebar-llm-prov` 上的 `title="..."` 屬性與未使用的 `poolNote`/`srcName` 變數。
- **效果**：hover 模型條時只會出現右側結構完整的白色 hover card（內含各 window 佔比、進度條、重置時間、角色標籤與今日調用費用統計），不再出現原生黑色小浮框。
