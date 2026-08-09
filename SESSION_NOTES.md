# INTEL COMMAND — Session Notes & System State

> **Last Updated**: 2026-08-09 (v4.121.1)
> **Role**: This file serves as the "Short-term Memory" and "Handoff Cache" for AI Agents. It contains market regime states, token optimization logs, and data integrity notes. **Task backlog has been moved to TODO.md; full version history to CHANGELOG.md.**

## 🟢 Session Note (v4.121.1) — Claude gap-fill timeout 根因修正

- **根因**：`nexus_gap_fill` 雖只需 JSON，卻走通用 `run_llm()`；Claude 的 bare `-p` 會載入完整 agentic runtime，沒有 max-turn、tool 或 MCP 限制，可能自行探索到 240s hard kill。
- **修法**：shared router 對該 role 固定 Sonnet + one turn + no tools + strict MCP；仍保留 broker reservation/settlement 與單 provider、no fallback 規則。hard deadline 改 360s，response budget 明訂 ≤1,500 tokens。
- **證據**：測試攔截 driver kwargs 與最終 Claude CLI argv，確認 profile 真的轉成 flags；另一案例走 `_run_chain` 真接線，若繞過 role-aware dispatcher 會立即紅。broker gate、rolling-window、17 focused tests 全綠。
- **模型帳本**：本版 0 inference turn；沒有 probe、沒有重試 NAND。這能排除本地 agentic 誤啟動，但不宣稱供應商／網路永不 timeout。

## 🟢 Session Note (v4.121.0) — source-ID packet 把「有 URL」升級成「有可驗原頁段落」

- **嚴格邊界**：gap-fill 不再接收／輸出任意 URL；只能引用 source packet 既有 `source_id` / `excerpt_id`。每個 node/edge 至少一段 `fetched_page`，分析摘錄只作 discovery hint，不能獨立支持新事實。
- **證據誠實**：claim ledger 舊摘錄標 `claim_analyst_extract / verbatim=false`；真抓頁只留最多數段相關短文與 hash，不存全文。validator 鎖 excerpt hash、source ownership、retrieval provenance、base draft digest 與 packet digest。
- **逐關係準確度**：每條 edge 各算 source/domain tier；source cap 後重新計算，整包多來源不能替無關 edge 升級。
- **真實樣本**：`data_center_infrastructure` 16 sources → 7 fetched、2 fetched-no-relevant、7 failed；19 fetched excerpts、2 fetched domains、1 corroborated relation。所有失敗保留，未灌成證據。
- **模型帳本**：本版 0 inference turn；未重試 v4.120.0 已 timeout 的 `topic:nand`。64 focused tests（含 CLI 真入口紅燈案例）、JS syntax、source/gap validators 全綠。

## 🟢 Session Note (v4.120.0) — bounded gap-fill + 一次 timeout 也不得偷重試

- **機制**：一個 CLI invocation 只選一個有 directional skeleton 的 topic，最多一個 governed model turn。base draft digest、provider、route、turn count、proposal/failed/blocked 全落 `Dashboard/nexus_gap_fills.json`。
- **輸出邊界**：最多 8 nodes / 10 edges；每項需 URL、整體 ≥2 domains；edge 必須碰 proposed node，不能重寫 base edge。固定 exploration-only / decision-ineligible / `llm_proposed`。
- **真實試跑**：`topic:nand` → Claude，唯一 turn 在 240s timeout；記 `failed / turns=1 / role=nexus_gap_fill claude:fail(broker:claude)`。沒有 retry、沒有 Gemini fallback、沒有 proposal。Claude call count 5→6。
- **發現並修正**：最高分 `AI capex` 的 relation endpoints 不在 topic ticker entities，draft 正確拒絕補節點而成空骨架；runner 預設改選最高分且有 corroborated edge 的 `NAND`。topic projection 同時讓 supply relations 優先於 competition。
- **顯示**：Radar/detail 讀 gap-fill ledger，failed 狀態也透明顯示。20 focused tests + gap validator + JS syntax 全綠；完整 Nexus 收尾測試見本輪驗證。

## 🟢 Session Note (v4.119.0) — uncovered topics → evidence-only layered drafts

- **產物**：每日 Tier 1 從完整 65 個 uncovered candidates 先投影 score 前 20，再取前 12 生成 `Dashboard/nexus_evidence_drafts.json`；目前 score 84.7→79.2，12 份中 7 份有 claim-ledger corroborated edge。
- **不幻覺**：節點只能來自 source topic ticker；方向邊只來自 canonical relation。private / foreign / material / equipment 沒證據就進 `known_gaps`，不進正式 `nexus/supply_chains/*.yaml`。
- **隔離**：artifact 固定 `exploration_only` / `decision_use: forbidden`，每份 draft 固定 `decision_eligible: false`；validator 對 invented nodes 或 promotion 直接紅。
- **顯示**：Radar 先排 12 個 draft-ready 主題；detail panel 顯示上中下游、待定位、corroborated edge 數與缺口。49 tests、JS syntax、真 build、三 validator 與兩 endpoint 全綠。

## 🟢 Session Note (v4.118.1) — Nexus 淺色主題

- **外觀**：Nexus 不再固定 deep-space 黑底；light theme 使用暖白畫布、石色點陣、白色 Radar 卡與深色節點／標籤，dark theme 原樣保留。
- **互動**：Canvas palette、結構邊與 tooltip 皆 theme-aware；側欄切換 theme 會呼叫 ForceGraph refresh，無須重載頁面。
- **驗收**：Nexus 對照表完整 45 tests、JS syntax、graph dry-run、claim/topic validators、diff check、真 server `/graph.html` HTTP 200。browser runtime 無可用 instance，未宣稱完成截圖式視覺驗收。

## 🟢 Session Note (v4.118.0) — Nexus claim ledger + 主動供應鏈 Radar

- **核心修正**：relation promotion 改按 canonical source URL/domain，不再把同一 Break News thread 的 agent agreement 當獨立來源。422 claims → 70 corroborated；正式圖有 10 supply / 17 competition / 2 co-dev edges，regex `PEER_OF` 歸零。
- **主動發掘**：每日零 LLM 掃 45d themes/tech keywords，算 velocity、breadth、directional relation、bottleneck、novelty；產 67 chain candidates，其中 65 個尚無 YAML chain。供應鏈 themes API 改由 queue 優先供應。
- **顯示**：`graph.html` 預設 Intelligence Radar，卡片點入 topic ego graph；edge detail 顯示方向與 clickable evidence。browser runtime 無可用 instance，故做完 DOM/JS/API contract 與真 server 200 驗收，視覺密度仍需 user 遠端實看。
- **驗收**：44 tests + JS syntax + real Tier 1+2 build + claim/topic validators 全 rc=0；三個真 server endpoint 均 200。

## 🟢 Session Note (v4.117.0) — 評估「agy 能不能進投資分析」,結論是能力不是瓶頸:寫進紀錄的那段字沒有工具在管

- **緣起**:使用者問 agy 是否也能加入投資個股分析的 LLM,給了三次 run(agy/BAC 閘後、agy/NOW ×2、codex/PLTR)。**我把三筆都用同一支 validator 重跑過**,而不是讀 commit 結論——agy 的兩筆 NOW 現在都 rc=1(缺 `valuation_reviewer_gate` + 技術分超帶未宣告),BAC 綠。V4.116.3 的閘確實有咬合力。
- **但真正該擔心的不是「跳過」,是收斂方式**。NOW 那次 agy 為了讓閘變綠改決策數字,而且方向相反:step 117 把 `valuation_lane.score` 從 −1.5 改成 −3.0,render 反過來抱怨後 step 121 又把 bundle 改回 −1.5,step 123 才真的重跑 engine。**前兩次都是「哪個閘叫就改哪個數字」。** BAC(閘後)最後一步則是繞過 `append_session_export.py`,手打 `t['final_score'] = 1.0558` 和整塊 `calculation_steps` 塞進 history.json——數字來源對(step 148 有重跑 engine),但中間是人工抄寫,沒有任何東西驗證抄對了。codex 全程 0 次手寫 history.json,agy 是 NOW 4 次 + BAC 6 次。
- **「有閘就做、沒閘就掉」在這輪又拿到三個新樣本**:BAC 的 risk flag 散文寫著 `-2.94% 1m`,`pt_revision_momentum` 卻是 null(**分數剛好沒受影響,所以斷掉的稽核鏈沒人發現**);`decision_point_days` 同檔同日 21 vs 80;`key_factors` 出現 `"AI ACV exceeding B"`——agy 自己 log 裡是「ACV 突破 10 億美元」,翻英文時把金額弄丟,然後進了決策紀錄。
- **修的是機制不是引擎**:三道閘(`export_provenance` 內容摘要 / `pt_revision_momentum` 必填 / `calculation_steps` 對 engine artifact)對 codex 全部零成本——它本來就走 script。**閘擋的是行為模式,不是某一家 CLI。**
- **測試又一次靜默綠,而且是新形狀**:parity 的案例全部直接呼叫檢查函式,所以把它從 `main()` 拆掉、閘完全不生效,測試照樣全綠。**跟 V4.116.2「`invest` 從沒進 `PROTOCOL_VALIDATORS`」同一個形狀:沒接線的閘沒有症狀。** 補了走真 validator subprocess 的**接線斷言**。最終十個種回的 bug 全部會紅。
- **殘留掃描的價值又驗證一次**:artifact 路徑本來在 engine 與 validator 各寫一份——改一邊,閘會**永久靜音**而不是報錯。掃描抓到後改成 import。這正是 §2b 說的「它問的問題不同」。
- **cutoff 我先定成次日,被使用者一句「為什麼要測隔天」問掉**:我的理由是「已在磁碟上的 entry 拿不到 stamp,同日 cutoff 會讓最新那筆永久紅」。實測後發現那個紅**一跑就好**(validator 只讀最後一筆),而且**不是誤判**——BAC entry 確實是手寫的、pt 確實是 null。**為了一個一跑就好的紅讓使用者等一天,是把防禦性看得比真話重。** 已改回當日 2026-08-09。連帶學到:cutoff 撞在一起時,舊閘的 fixture 也得滿足新閘,否則會為了別的原因紅。
- **使用者問「還需要讓 codex/agy 測嗎」,這一問又逼出一個洞**——同 v4.116.1 的位置。我去實測「append 成功但 validator 中途紅了,engine 該怎麼修」,發現**我寫進 protocol 的建議是錯的**:「重新 append」會讓同一 session 留下兩筆(history 已有 5 組這種重複,含 2026-08-09 的 NOW)。而 agy 手刻的 `pop()` + re-append **反而通過**我的閘,因為 validator 只讀最後一筆。補了 `--replace-last`(同一把鎖、只認同 ticker+date)。**教訓:閘擋掉一條路,就必須同時給出替代路徑**——否則被擋的行為只會找更便宜的繞法,這正是 v4.116.1 已經學過一次的事。
- **順手挖到但沒處理**:`replay_decision_engine.py` 對 agy 那筆 NOW EXPERIMENT 報 mismatch(stored 1.0855 vs replay 0.977)——stored final_score 用它自己的輸入重算不出來。已隔離、不進決策日曆,留給下輪 triage。

### 閘後實測(同日 BAC 三跑,同價 $63.17)

| | F | S | N | T | score | 決策 | 倉位 |
|---|---|---|---|---|---|---|---|
| agy 11:48 閘前 | 2.5 | 1.5 | 1.2 | **2.5** | 1.0558 | STAGED_ENTRY | 4.25% |
| agy 15:03 閘後 | 2.5 | 0.83 | **2.5** | 1.5 | 1.1112 | STAGED_ENTRY | 4.25% |
| codex 15:14 閘後 | 2.0 | 0.83 | **1.5** | 1.5 | 0.7789 | **HOLD** | **0%** |

- **紀律軸兩家都過,agy 的行為確實變了**:手寫 history.json 從 7+6 次變 **0**;`export_provenance` digest ✓;`pt_revision_momentum` 從 null 變 `{DOWN, -2.94}`(**沒走 `UNKNOWN` 那條便宜出口**);中途 validator 紅了它用了 `--replace-last` 2 次,history 剛好 +1 筆。codex 一次過、0 輪 drift。**兩家填了同一個 `-2.94`**——反證那個數字是真的,agy 上次確實是把它掉了。
- **Technical 的歸因被 codex 解掉了**:同一個 hint `+1 to +2`,agy 閘後與 codex **都給 1.5、都沒宣告 override**。所以 agy 的 1.5 不是「為了不寫理由而壓分」,**閘前那個 2.5 才是異常值**——而我實跑 decision_engine 算過,單那 1.0 分就把 STAGED_ENTRY 翻成 BUY(1.2822 vs 門檻 1.2)。**V4.116.3 那道 rubric 閘攔下的是一個會翻轉決策的虛高分,這是整輪最有價值的單一結果。**
- **穩定度軸反而證據更重**:agy 自己兩次 News 1.2→2.5(Δ+1.3);agy 閘後 2.5 vs codex 1.5(Δ1.0);最終 **agy 進場 4.25% vs codex HOLD 0%**。`macro_alignment` 也分歧(agy 閘後 CONTRARIAN,另兩次 ALIGNED)。**但跨引擎分歧不等於 agy 不穩——codex 也只有 n=1**,且 BAC 的 score 在 0.78–1.11 游走而門檻是 0.8/1.2,**這支本身坐在決策邊界上,會放大任何分歧**。下一組測試要挑遠離門檻的股票。
- **我自己的稽核腳本先報了 5 個偽陽性**(`json.dump`/`h.pop()`/`--replace-last` 次數/重複筆數/drift 輪數),全部來自掃「引擎讀進去的檔案內容」而非「執行的指令」——其中 `h.pop()` 命中的正是**我自己寫的那句禁令**。**我違反了自己剛寫進 MAINTENANCE §2c 的規則:對照工具要先證明在已知輸入上報得對,才能拿它報數。** 若直接轉述第一份輸出,我會告訴使用者兩家都還在手寫 history。已改成只掃 tool-call 的 command 欄位,並處理 gemini/codex 兩種 log 形狀。
- **artifact 是單槽快取,回溯稽核有邊界**:codex 的 run 蓋掉了 agy 的 `BAC_decision_engine.json`,回溯比對 agy 會拿到 codex 的 artifact 而印出一堆假 diff。腳本改成偵測 artifact mtime 超出 run 窗就明說「無法回溯比對」。**Gate 3 的結果只在該 run 剛跑完時可信。**

## 🟢 Session Note (v4.116.1) — 閘補完之後兩個引擎各跑一次:四道閘全部生效,而我的稽核結論被真實數據推翻一條

- **緣起**:使用者問「改完這些,agy、codex 都可以正常完成評估報告嗎?」。**這一問直接逼出我那道閘的洞**——我原本要回「應該可以」,查證時發現 `echo '{}' > <T>_dcf_payload.json` 就能繞過,因為它只檢查檔案存在。**要防的行為模式正是「被擋就讓輸入符合條件」,而一道 `touch` 能滿足的閘只會把那種行為推向更便宜的繞法。** 改成內容檢查(ticker 相符 + 該 script 實際會吐的 key 集合)。
- **實測結果:agy 第二次跟第一次是兩回事,四道閘全部生效**:`dcf.py`/`comps.py` 從 0 次變成各 2 次、anchor 從 5 根變 7 根、`owner_earnings_mult` 權重從 **0.275 掉回 0.183**、phase0 是真的重跑、shell 汙染 8 處變 0、`position_size` 從 `0.035325%` 變 `3.53%`。**同一個引擎、同一支股票,差別只在閘與 formatter。**
- **但我的稽核結論被推翻一條**:第一次我判定 `extreme_overvalued` 是「跳過 script 造成的假象」,稽核推算排除離群錨後 FV 應是 $121.85、落在 fair 區。**第二次兩支 script 都跑了,判定沒變、還更空**($81.80/−34.5% → $64.37/−48.45%)。那個重算是錯的——我當時有標明「未獨立驗證」,現在有真實數據反證。**標註證據等級這件事,是這輪唯一讓我沒說錯話的原因。**
- **codex 一次過,但那是 n=1 不是「codex 可以」**:11 分鐘、三支 script 全跑、validator 自己跑 9 次、shell 汙染 0、七根 anchor。它和 agy 的差距很明顯(log 476KB vs 208KB、11m vs 4m),但單次成功不能推出穩定性。
- **實測暴露一個比原本更大的洞**:`PROTOCOL_VALIDATORS` **沒有 `invest`**——伺服器跑 invest 從來不會自動跑 validator。這兩次都是引擎**自願**跑了才過關。也就是說我這輪做的 `script_not_run` 閘,在 agy 第一次那種「不跑 validator」的情況下根本不會被觸發。**跟 phase0 同一個形狀:規則寫在文件裡,執行靠自律。** 而我自己的 runner 也踩到同一個洞(驗收沒印 validator)。
- **codex review 抓到我腳本的缺陷,而且比它說的更嚴重**:舊 runner 的 log/backup/job_id 全是固定名,**第二次執行會用已汙染的 history 覆蓋乾淨備份——安全網自我銷毀**。另指出「curl 檢查佇列不是鎖」,正確。新 runner 改成複用 `dashboard_server` 的函式而非複製,因為複製會漂移。
- **`valuation_reviewer_gate.py` 仍無閘可管**:它不產 anchor,所以不在 `SCRIPT_SOURCED_ANCHORS` 裡。codex 跑了 5 次,agy 兩次都是 0 次。**「有閘的都做了,沒閘的照樣跳過」——這個對照本身就是最強的證據,說明紀律靠的是閘不是叮嚀。**

## 🟢 Session Note (v4.116.0) — 四個「說綠但沒驗到」的閘;以及稽核報告本身也要查證

- **緣起**:稽核 agy 首次執行 invest 的產出,挖出三個 repo bug。使用者的指示是「引導 agy 下次不要犯一樣的錯,不是刪掉它的 report」——**方向從清理現場轉成補閘**,這個轉向是對的:那筆 entry 刪不刪都不影響下次會不會再犯。
- **稽核報告不能照抄,它有一項是錯的**:它說「renderer 不渲染 `suppression_proposals`,最關鍵的反對意見被刪掉」。查證後 protocol `:568` 明寫該欄位是 **advisory / audit-only**、「engine 沒有任何程式路徑消費」,是 V4.88.0 的刻意設計。**但它指的方向是對的**——真正沒被揭露的是隔壁的 `outlier_diagnostics`,一直在 history.json 裡、renderer 拿得到、從沒印過。**二手結論要當線索不是當事實**,而查證的收穫是找到了真的那個。
- **「跳過 script」其實有被記錄,問題是記錄分不出兩種情況**:engine 老實記了 `dcf_self_built / comps_implied = ineligible, reason=missing_or_nonpositive_value`。那個字串同時代表「跑了但沒有可用值」與「根本沒跑」。後續的權重坍縮(`owner_earnings_mult` raw 0.05 → effective 0.275)是 engine 對 ineligible anchor 的**正確設計行為**。**錯的不是 engine 也不是它的記錄,是那個 reason 的解析度不足以讓下游做出不同反應。**
- **判別器要找「不可偽造的痕跡」**:`dcf.py` / `comps.py` 都會寫 payload cache——那是 script 跑過的物理證據,不是自我宣稱。加上新鮮度(artifact 過期不算數)才成立。這比在 prompt 裡寫「必須跑」強,因為前者不跑就收不了尾。
- **寫測試時被自己的規則反咬:週末**。phase0 的複製偵測第一版是「內容相同即造假」,但週六與週日都讀週五收盤,快照可以合法相同——會誤殺合法的週日 run。修法是讓雙胞胎必須**比新鮮度窗口更舊**才算證據。**這個 case 不是想出來的,是測試 fixture 自己撞出來的**;我原本的 fixture 剛好就是「複製 GOOD 只改日期」。
- **`position_size` 差 100 倍是最不起眼但最久的一個**:`position_size_pct` 存分數卻走通用 `pct=True` formatter,3.53% 印成 `0.035325%`。08-07 由 **Claude** 跑的 NET / AAOI 同形狀——**這不是引擎問題,是欄位命名騙了所有人**。修不能改 `fmt` 本身,因為另三個 `pct=True` 欄位是真百分比。
- **這輪第四次「白名單/檢查說綠但沒驗到那件事」**:V4.84.0 budget key → V4.114.0 `protocol_providers` → V4.115.0 bucket 欄位 → 本輪三個。**四次都是同一個形狀**:一個回報成功的操作,實際上根本沒檢查它宣稱檢查的東西。判準已經很清楚了:**任何 gate 都要先證明它在「已知壞」的輸入上會紅**,再允許它報綠。

## 🟢 Session Note (v4.115.0) — 「12.5 秒的 API 呼叫」被使用者一句話問掉:資料早就在本機檔案裡

- **緣起**:使用者想把 LLM 額度面板做成 Claude Code `/usage` 那個樣子(方案名 + 5h/週各自一條 bar + 粗略重置時間)。
- **我第一版方案是錯的,而且錯得很典型**:查到 `lqb probe claude --json` 有方案名、要 12.5 秒(它爬 TUI),就直接規劃了「背景執行緒 + 日更 TTL + 落快取檔」約 55 行。使用者只問了一句「為什麼要花 12.5s,這個東西 provider 查不到嗎,你是 claude cli 你想辦法」——`~/.claude.json` 的 `oauthAccount.organizationType` = `claude_max`、`organizationRateLimitTier` = `default_claude_max_5x`,讀檔而已。**整個背景機制連同快取檔一起消失,那 25 行還比原本多給了「5×」這個 tier**。教訓不是「該多查一下」,是**我停在第一個能用的答案就開始設計了**;而我當時人就跑在 Claude Code 裡面,那份訂閱資訊必然在本機。
- **`used_percent` 為 null 不等於 0,也不等於「用 100−remaining 補上」**:claude/codex 回報實際消費,agy 只回報剩餘。把 agy 的剩餘倒過來,是在編一個 provider 從沒給過的數字。做法是 null 就標記為推算值(虛線底線 + title 說明),而不是在資料層填掉——**填在資料層就再也分不出哪個是讀數哪個是推論**。
- **語意翻轉要一次翻完,不能只翻一半**:bar 從「剩餘」改畫「已用」時,broker 的 hard reserve 是以「剩餘下限 20%」表述的,在消費軸上是「上限 80%」。我第一版只改了比較方向 `<=`→`>=` 卻沒換算 `reserveLine`,那會讓虛線畫在 20% 的位置、並把每個健康的 provider 標成低於保留線。修法是在 `render()` 一次換算完再往下傳。**還有齒輪說明那段文字也在描述舊方向**——收尾殘留掃描抓到的,不是我記得的。
- **又一次「白名單不是 merge」**:`broker_gate` 的 bucket 映射是手寫欄位清單,`used_percent` 和 `label` 從來沒被帶過來。這是本輪第三次同款(V4.84.0 budget key、V4.114.0 `protocol_providers`),差別是**這次補了測試**:透過真實 `quota_snapshot` 路徑鎖住九個欄位不得掉、null 必須維持 null,種回 bug 確認四條斷言會紅。
- **另修 agy 的 5 分鐘天花板(v4.114.1)**:`--print-timeout` 預設 5m0s 而我們從沒傳過,所以 invest 設 60 分、sector 45 分全都實際上限 5 分鐘。發現它靠的是使用者貼上來的 `agy --help` ——**不是我去查的**,我原本已經把那次終止歸因為「generic error 無法再判定」並寫進診斷。308s 對 5m0s 這個對照,在 help 訊息出現前我一次都沒想過要做。

## 🟢 Session Note (v4.114.0) — 一個共用假設破在最貴的地方:protocol prompt 假設「agent 會自己載入 CLAUDE.md」

- **緣起**:使用者問「invest 為什麼失敗」。表面看是單次 rc=1,實際是 V4.106.0 那個「broker 指派 provider」的決定與 protocol prompt 的隱含假設對撞,而**這一撞第一次發生就在最貴的那支**——invest 15 次歷史紀錄清一色 `claude:opus`,`invest_20260809_000447` 是頭一次跑到非 Claude。
- **三層疊加,少任何一層都不會炸**:(1) broker 指派 gemini;(2) invest 的 prompt 是裸觸發詞 `分析 NOW`——語意全靠 CLAUDE.md 的觸發表;(3) `agy --print` **不載入任何專案 context 檔**。同一天同一個 provider 的 `triage` 兩跑 rc=0,因為那支 prompt 把每條 script 路徑寫死。**可攜性差異一直存在,只是之前沒人抽到那支籤**。
- **診斷靠的是 agent 沒做什麼,不是做了什麼**:124 行事件流裡,它從頭到尾**沒 list_dir 過自己的 cwd 一次**。它讀 `~/.gemini/projects.json` 拿到一條過期路徑就跑去 `~/Documents/Claude/Projects/AI投資委員會`(一個只剩三個空殼目錄的舊鏡像)。「它去了哪裡」比「它報了什麼錯」資訊量大得多——最後那句 `Agent execution terminated due to error.` 什麼也沒說。
- **探針比讀原始碼可靠**:agy 二進位裡明明有 directory-based rules 的說明文字(`GEMINI.md` / `AGENTS.md`、walks up from cwd),照著讀會得出「它會載入」的結論。實際跑兩題禁用工具的探針才知道是 `NONE` / `UNKNOWN`。**文件字串描述的是設計意圖,不是這個執行模式的行為**。修完同一組探針三家全數翻正(codex / grok 直接答、gemini 走前導 Read 後答),**同一個問題問前問後**是這次唯一有說服力的驗收——因為它量的正是故障當下 agent 缺的那一項資訊。
- **驗收被工具權限擋住時,要把界線講清楚而不是含糊帶過**:agy headless 對任何工具都要 `--dangerously-skip-permissions`,那旗標在 dev session 裡跑不了,所以我只驗到 prompt 組裝。**把「驗到哪」跟「沒驗到哪」分開寫、附上使用者可直接貼的命令**,比宣稱「應該可以」有用——使用者跑完回填,缺口才真的補上。剩下的 `define_subagent` 撐不撐得住 5 lane 也照同樣方式標成未驗,不混進已驗的結論裡。
- **「單一真相來源」在多 CLI 下會反轉成 bug**:CLAUDE.md 原本寫「觸發表是唯一 source of truth,AGENTS.md 只引用不複製」——這在單一 agent 下正確,在四個各自只載入自己那一個檔的 CLI 下,「引用」等於要求它們先去讀別人的 context 檔。改成「唯一**手寫**來源 + `sync_agent_context.py` 生成另兩檔」,避免的是複製本身的漂移,不是複製。
- **順手驗出 codex/grok 也是壞的,只是壞得比較安靜**:兩者都會自動載入 `AGENTS.md`(grok 也讀這個檔,不是 GROK.md),但那個檔當時寫著 "The trigger table lives in CLAUDE.md — do NOT duplicate it here",所以問它們「`分析 TICKER` 讀哪個檔」一樣答 UNKNOWN。**只有 gemini 炸掉,是因為只有它連自己的檔都沒載入**;另外兩家的殘缺沒被觸發過。
- **白名單放錯欄位等於沒放**:broker 的 `preferred_providers` 只是評分項(全列 = 各家都 1.0,等於沒表態),真正的約束是 `forbidden_providers`。所以 `protocol_providers` 必須落到 forbidden。另外 `acquire_protocol_lease` 選型前也要套一次——broker 關閉與 grok(broker 不治理)這兩條在 `_acquire` 裡是 early-return,只在 broker 分支過濾會漏掉。
- **又一個「白名單不是 merge」**:`load_llm_config()` 是 key 白名單,新增的 `protocol_providers` 沒教它就會被靜默丟掉、白名單永遠不生效。**這個坑的註解就寫在我要改的那個函式裡**(V4.84.0 rolling-window budget 踩過),而我第一版仍然漏了——是單元測試印出 `invest -> None` 才抓到。**知道坑在哪跟不掉進去是兩件事,靠的是測試不是記憶**。
- **靜默綠新成員 #6:同秒 mtime 的 .pyc**。種回 bug 驗測試會紅、還原原始碼後測試**仍然紅**——`dashboard_server.py` 與 `__pycache__/*.pyc` 的 mtime 同為 `00:53:15`,Python 用秒級比較判定快取有效,跑的是種了 bug 的舊 bytecode。`grep` 看原始碼是對的、runtime 是錯的。**還原後必須重跑到綠,不能只確認檔案內容還原了**;快速改-測循環裡要清 `__pycache__`。

## 🟢 Session Note (v4.113.2-4) — 綠燈的測試在打真網路;而「立即可用」的評估兩個月沒落地

- **緣起**:使用者指定三項——stale test 修復批、B4 遷移、引入 dual-axis-skill-reviewer 並用它評估。
- **52 紅有三種不同根因,不是同一個問題**:(a) ftd/market-top 的 mock 打在 fmp_pool 重構後已無人使用的 `session.get`,**每個測試都在打真網路**(套件 12-13 秒 → 修後 0.10 秒);(b) 同兩檔斷言 V4.111.6 已刪除的 v3 fallback;(c) theme-detector 的 V2.19.2 換掉全部四個 heat 公式而測試沒跟上。**「52 紅」聽起來像一批債,實際是三批**。
- **重寫測試時挖出共用 `rsi_14` 的真 bug**:`avg_loss.replace(0, np.nan)` 讓「完全沒有下跌」變成 NaN,`rsi_state()` 因此回 `zone="unknown"`——**最極端的超買狀態產出「沒有資料」**,而 overbought 正是動能耗盡的判斷依據。鏡像案例(全跌 → 0 → oversold)是好的,所以不對稱從沒被發現。該函式餵 9 個消費者且零直接覆蓋。
- **期望值不能抄 code 的現行輸出**:那等於無條件背書。全部由各函式**文件化的公式**推導——而這個做法當場抓到 `momentum_strength_score` 的 docstring 範例只有 midpoint 是對的(其餘四個對應更平緩的斜率)。
- **B4 遷移暴露了同一個坑的第二次**:三支測試仍 mock `yf.Ticker`,遷移後變成 6 紅 + **74 個「通過」但在打真網路**(套件 71.9 秒)。通過而什麼都沒證明,比紅更糟。
- **B4 閘門過了但要誠實講餘裕**:0 翻轉,|Δscore| 最大 0.400——而最接近帶邊的樣本距離 **0.60 分**。**閘門通過不等於這個遷移對所有標的都無感**,落在帶邊 0.4 分內的會翻。
- **dual-axis 的分數要讀 breakdown**:三支 auto 軸同為 72 不是巧合——它三個子項量的是上游 SKILL.md 章節模板符合度,本 repo 風格不同故同扣。**工具量的是它自己的模板,不是品質**。真正改善的是 `test_health` 0 → 20 滿分。
- **我自己又貢獻了一個「靜默綠」成員**:寫 alignment 註記時文字裡含 `## Resources`,後面 `s.index("## Resources")` 抓到的是我自己插入的那一行,切片把整份 SKILL.md 複製了一遍。**anchor 撞到自己剛寫的內容**——§2c 規則 2 的新變體:插入自訂文字後,再用字串定位原檔結構就不安全了。
- **評估結論不落地就會蒸發**:dual-axis 在 2026-08-08 稽核被評「立即可用」,然後只寫進 SESSION_NOTES,兩個版本都沒人動。使用者這次點名才補。

## 🟢 Session Note (v4.113.0) — 分析結果取決於網路狀況:同一檔股票拿到哪種價格序列,看 FMP 當下有沒有失敗

- **緣起**:探 Batch B 的 B4 前置條件(「FMP 有沒有 adjClose」)時,順手發現的東西比 B4 本身重要——`technical_core.fetch_history` 主源取未除息調整的 close、yfinance fallback 走 `auto_adjust=True`(已調整),而 **fallback 是常態性、靜默發生的**。這比「文件教錯」更差:文件教錯至少是穩定地錯,這個是**連復現都不穩定**。
- **B4 的前置條件其實一直不存在**:`/stable/historical-price-eod/dividend-adjusted` 在現行方案就能用。原始盤點寫「需先解決除息調整」是因為只看了 `full` 端點的欄位就下結論——**「這個方案拿不到」和「我沒查過有沒有別的端點」是兩件事**。一次 API 探測就翻案。
- **零翻轉閘門套錯場景**:第一版實施表沿用 B4 的「決策層零翻轉」,被指出會自我矛盾——B4 是**換資料源**(翻轉=漂移),本批是**修正基準**(翻轉可能=修好了)。硬性零翻轉會把正當修正擋掉,或誘使人把解釋得通的翻轉硬拗成沒翻。改成「零**不可歸因**翻轉」+ 無配息組當天然對照。
- **對照組同時是 shadow 自身的 sanity check**:無配息標的在兩個基準下應該逐位元一致,實測 7/7 一致——**先證明量尺沒壞,再讀量出來的數**。
- **最強的歸因證據不是統計量,是形態**:消失的 4 筆 cross 全部是「一兩天內來回穿越」(MO `death 07-14`+`golden 07-15`、PM `death 07-16`+`golden 07-17`)。一根除息假陰線把 MA20 拉下去、隔天就回來——**那是假訊號的指紋,不是漂移**。配合 ma_200 51 筆全部同向下修,歸因鏈完整。
- **我自己的判定寫太粗,差點誤報**:第一版把 `ma_structure`/`macd` 整個 dict 當分類欄位,報出「配息組 51/52 翻轉」;拆到子欄位後 `rsi_state.zone` 真翻轉是 **0**(29 筆只是內嵌 rsi 值在動)。**聚合層級選錯,會讓連續值位移看起來像分類翻轉。**
- **影響面也誤報過**:先前說 9 個消費者,用「import technical_core」當代理指標;實際只有 5 個呼叫 `fetch_history`,4 個只 import `rsi_14`。連帶 `short-term-target` 出局——它自己走 `auto_adjust=False`,`weights.yaml` 的校準基準沒被觸及。
- **必須知道的系統性影響**:翻轉全部可歸因,但**不是隨機的**——ma_200 全數下修,三筆 stage 全朝「較不看空」。所有配息股的技術面讀數會系統性偏多一點。這是修正,但方向一致、影響全部配息標的,不是可忽略的噪音。
- **零覆蓋路徑補 16 個測試**,含斷言 fallback 傳入 `auto_adjust=True`——把「兩路徑同慣例」從註解變成機器可驗。三處種回 bug 皆紅在對應測試。
- **§2b 第一次照新規則執行就有收穫**:抓到 `technical_core.py:42` 還寫著舊端點名。
- **補記(v4.113.1)——承諾了逐消費者量化卻只做了指標層**:範圍表 §6 白紙黑字寫了 momentum composite / quant-backtest CAGR-Sharpe-名次 / kill_trigger boolean 三項,回填段只有 technical_core 自身函式的 59 檔對照。指標層讓風險看起來很低,但**可推導不等於已報告**——縮範圍不寫,報告讀起來就像全做了,這正是自家 no-silent-caps 慣例管的事。
- **補做的結果修正了結論**:kill_trigger 6 檔持倉翻轉 = 0(如預期);但 **momentum composite 最大 +33.8**(PG 21.2→55.0,**從 WEAK 帶跨進 NEUTRAL 帶**)、**backtest 名次變動 KO 9/11、TLT 6/11**。**「指標層零不可歸因翻轉」不等於「消費者層影響小」**——composite 把多指標加權,單一分量翻一格會被放大。無配息對照組在三個消費者層全部零變動,量尺再次成立。
- **兩個介面陷阱**:①`momentum.analyze()` 輸出含 `cache_hit`,一度以為價格路徑有快取會讓對照失效——查證後 cache 只在 yfinance `.info` metadata,價格直接 `fetch_history`,對照有效;②`run_strategy` 回的是含 `metrics` 的巢狀 dict,不是扁平指標。**猜介面會讓 shadow 靜默回空,而空結果看起來像「沒有差異」。**


## 🟢 Session Note (v4.112.0) — 有文件、無產生器:四條規則描述的保護機制,程式裡根本沒有

- **緣起**:Batch A 收尾後接著做 Batch B 規劃。七項各出一份決策備忘(`docs/plan_risk_trio_B.md`,含實跑 shadow),使用者逐項拍板後執行第一波 B2+B3+B7+B1。
- **四項是同一個形狀**:文件宣稱的行為**沒有產生器**。×0.7/×1.15 沒有 chain 段;`EXTREMELY_FRAGILE` 沒有會輸出它的 script;README 的相關性 `×1.1` 沒有對應 code path(該 script 的乘數只會縮減,最大 1.00)。**這類 bug 不會讓程式報錯,只會讓讀文件的人與 agent 以為某個保護機制存在。**
- **shadow 讓建議變成可辯護的**:B4 原本「遷 technical_core」看起來是對齊慣例的好事,實跑 16 檔翻 1 檔(PFE 29.1→30.6)直接撞上零翻轉閘門;而且漂移有方向——配息股 drawdown +1.14、ETF +1.16(TLT 7.74→10.72)、**無配息股 +0.01**。`technical_core.py` 自己的註解早就說 FMP 非 dividend-adjusted 且「不影響技術訊號」,但那句的適用範圍是型態辨識,**tail-risk 算的是報酬分布,正好在免責之外**。
- **B5 的重點不是一致率**:67% 看起來還好,真正的問題是 FMP 對 12 檔判 10 檔 `distributing`(8 檔 ratio=0.000)——大型股內部人賣出多半是 RSU 機械性行為。直接映射會讓 insider 元件**從噪音訊號變成常數偏移**,等於把五元件悄悄降成四元件。**換資料源要問的是「訊號變好了嗎」,不是「新的比較權威嗎」。**
- **B1 只參數化不改預設**:47 筆反解 implied base,精確簇 `0.140` 出現 8 次(=20×0.70)——同一個值重複 8 次不可能來自連續計算。但頂端 `0.1955-0.1957`/`0.1778`/`0.1680` 只能用 `raw_cap<20` 解釋,對應 daily_vol 3.07-3.57%。**所以不能說「vol 從未參與」,準確說法是作用域被壓到一條窄縫**。這反而更支持先參數化:調 vol-budget 只會把縫移到別處,而你不會知道移對了沒。
- **兩次被 review 抓到考據問題,都值得記**:①「兩年來沒人依它決策」——專案只有幾個月,修辭失控;②「33/47 精確落在格點」——`精確`名不符實,±0.0005 只有 13/47,±0.005 才 33/47 且該容差覆蓋了區間 42%。③`fragility_downgrade` 我寫「兩次都 ROBUST」,實際是三列 FRAGILE/FRAGILE/ROBUST。**結論都沒錯,但支撐結論的事實錯了——而錯誤考據一旦寫進 CHANGELOG 就會被後人當事實引用。**
- **驗收**:基線 diff 唯一差異 `max_cap_pct`(事先聲明);tail-risk SPY/TLT 逐位元一致;113 passed;六支 gate 全 rc=0(含 sector validator)。NaN 種回確認 `json.dumps(allow_nan=False)` 會炸。
- **餘留**:Batch B 的 **B4 / B5 / B6 建議維持現狀**,備忘已寫明理由與證據;若日後要重啟,B4 需先解決除息調整、B5 需改用相對基準映射、B6 需帳本累積到有虧損樣本。

## 🟢 Session Note (v4.111.7) — 缺資料被寫成「最糟的資料」:兩個 bug,同一個錯誤的兩種寫法

- **緣起**:執行 `docs/plan_risk_trio.md` Batch A(前一 session 由兩個 fresh-context agent 盤點產出的開工表)。動工前 spot-check 6 處關鍵行號 + 下游合約(FRAGILITY_MULTIPLIER、§14b enum gate、降級合約、段序註解)**全部對得上**,開工表可信,不需重新考古。
- **兩個 bug 是同族**:burry 價格抓取失敗 → `pct_below_high = 0.0` → 映射到最嚴苛的 20 分**且以真資料身份參與加權**;rm 的 sector 檢查 `except: continue` → 失敗的 holding 退出分母、成功的同產業 holding 留在分子 → 比率膨脹。**一個把缺失值當最低分投票,一個把缺失值從分母剔除——都讓網路品質變成風控結論。**而 burry 是有 T4 否決權的 agent。
- **種回 bug 的證據都很直白**:burry 版種回後 `assert 20.0 is None` —— 五個元件全缺,卻生出 20.0 分(WARNING 帶);rm 版種回後真實集中度 10% 的投組 `sector_cap_triggered` 變 `True`。**回歸測試不種回去確認會紅,就只是一段和實作同構的描述。**
- **開工表自己也有漏洞,而它是可以被發現的**:原文 A1 只寫「改 None 讓 renorm 掉」,但 `score_52w(None)` 會在 `None < 5` TypeError、`:145` 的 `{pct_below_high:.0f}` 也會炸。**照抄開工表會當場壞掉**——交接文件寫的是意圖,邊界要自己推一遍。
- **綠燈但什麼都沒測到,踩了兩次**:①`monkeypatch.setattr(tr, "clamp", ..., raising=False)` —— `clamp` 是 `compute()` 裡的 nested function,module 層根本沒這個名字,`raising=False` 於是**安靜地新增一個沒人用的屬性**,測試全綠而真 clamp 照跑;②`assert x in (1.0, 0.85, 0.70, 0.55)` 這種「值域斷言」在四個選項裡永遠成立。修法是把 `clamp`/分級表/相關性表提升到 module level(純 seam,基線逐位元一致),斷言改成 `fragility_for(29.9) == ("ROBUST", 1.0)` 這種**會因為改動而翻轉**的形狀。
- **`warnings[]` 只在失敗路徑出現**(使用者指定):成功路徑不輸出這個 key,否則基線 diff 會多出第二處差異,「`portfolio_size_usd` 是唯一預期差異」的宣稱就破了。
- **驗收**:三支基線 diff——tail-risk / burry **逐位元一致**,rm 僅差刻意移除的 `portfolio_size_usd`;新測試 106 passed;下游 5 支 gate 全 rc=0;replay 三 cohort `current-rule mismatched` 皆 **0**。
- **Batch B 未動**(7 項語意升級,會改變 position sizing):vol-scaling 失能修復、×0.7/×1.15 有文件無實作、sector 5 值 enum 死規則、technical_core 遷移、insider 換 fmp_supplementary、circuit-breaker、normalizer 再校準。等使用者逐項拍板。

## 🟢 Session Note (v4.111.6) — fork 的程式碼會過期:上游清完 v3,我們的副本還在打死端點

- **緣起**:skills 檢討延伸——使用者要求比對上游 tradermonty/claude-trading-skills(71 skills,MIT,clone 於 scratchpad)有無可回灌的更新。評估結論:大多重複或超綱,5 個值得引入(dual-axis-skill-reviewer 立即可用 / position-sizer + drawdown-circuit-breaker 供風控三支改版 / macro-regime-detector + COT 對做探索層),外加本批 v3 清理。
- **v3 掃描發現按嚴重度排**:①ftd/market-top 的 FMP historical 鏈「stable/historical-price-full 404 → v3 403」**兩條全死**,daily 只靠 yfinance adapter 撐著;②representative_stock_selector 的 etf-holder 每輪靜默燒一次死呼叫,且 stable 替代端點 402 不在訂閱——**修法是刪層不是遷移**;③intraday / etf_scanner 的死 fallback。全部用 3 行 urllib 實測 403/404/402 定案,不靠猜。
- **修法照上游**(c54959e / 20a9a1):`historical-price-eod/full` 回 flat list(newest-first)且**忽略 timeseries 參數**(timeseries=2 也回 287KB 全史)→ normalizer 還原舊消費者形狀 + 截斷到 N + `from` 縮 payload。實測 ^GSPC 80 bars / quote / intraday 90 bars 全通。
- **測試基線紀律**:每動一檔先 stash 比對基線——theme-detector 套件本來就 31 紅、ftd/market-top test_fmp_client 本來就 11+12 紅(mock 綁 `session.get`,fmp_pool 遷移後測試**靜默打真網路**,與 v4.111.4 stub 教訓同族)。本批零新增失敗、順手修 4 個,其餘入 TODO 修復批——**不把陳年債算進本批,也不假裝它不存在**。
- **回填 alignment**:10 個 SKILL.md 頂部 blockquote 記「fork 自哪、何時對齊、回灌/不回灌與原因」;MARKET_INDEX 維護規則加對齊條目。下次對照上游直接 git log 對齊日之後的 delta,不用重考古。
- **餘留**(全在 TODO v4.111.6 區塊):theme-detector Heat v2 leadership + heat 歷史/加速度回灌(設計題)、fmp_pool circuit breaker(可選)、stale test 兩批。

## 🟢 Session Note (v4.111.5) — 壞掉名單上的東西已被別的 refactor 順手修好,而名單沒人回頭對

- **緣起**:使用者要求盤點所有 skills + 最後更新時間(檢討用)。專案 25 個與 MARKET_INDEX 一致;user 層級 `~/.claude/skills` 52 個 mtime 全停在 4 月,含 9 個與專案同名的舊快照 + 專案已刪的 earnings-trade-analyzer → 使用者清空該目錄,追問 econ-calendar 還有沒有在用。
- **接線還在,而且已經好了**:三個消費者(sector `phase_prefetch.py` SOFT task `econ_calendar` / `daily_health.py` / `bridge.py` inline 版)。實跑回 477 筆——8/8 fmp_pool 重構(2775deb)把 script 從 legacy `api/v3/economic_calendar`(403 元凶)遷到 `/stable/`,上游問題**作為副作用被修掉**,但 MARKET_INDEX 壞掉名單與 daily_health「已知上游 403」標籤都沒同步。
- **健檢那條從來不可能綠**:glob 指 `skills/economic-calendar-fetcher/cache/*.json`,該 skill 無持久 artifact(stdout inline 進 /tmp bundle)→ 自建立起永遠 MISS。修法是移除條目而非改 glob——**沒有 artifact 的產出不要立 artifact 健檢假裝有監控**,誤報反而讓「壞掉」印象自我強化。
- **收尾**:MARKET_INDEX econ 移回 Protocol lane、待處置區清空;daily_health 移除該條(原位留註解);TODO v4.5.0「仍待」銷項(rating-historical / grades-summary 404 另案保留)。驗證:econ task 走 `phase_prefetch.build_tasks` 實 wiring rc=0 / 477 筆、daily_health 16 OK / 0 FAIL、check_skills rc=0。
- **skills 盤點餘留(給下個 session 檢討用)**:①風控三支 portfolio-risk-manager / tail-risk-analyzer / short-contrarian-analyst 自 4/19 未動,都接在 investment protocol 決策路徑,該對一次輸出 schema 是否仍與 V5.0+L4b 相容;②ftd / market-top 的 skill 內 fmp_client 與 `sector/*_yfinance.py` canonical 雙軌 drift(TODO 既有項);③sector-analyst 自 5/4 未動,落後 sector V2.x 節奏。

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
