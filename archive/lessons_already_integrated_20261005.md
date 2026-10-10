# 已回寫規則的教訓（2026-10-05 維護封存）

依 MAINTENANCE §4 從活躍教訓移出；每條原文完整保存，正式規則以各條所列來源為準。

## 2026-10-04 ｜HTTP 成功與 shell 有 key 都不足以證明接線健康
- 情境：skills endpoint 稽核發現 FMP 月度推薦數被當成升降評事件，launchd server 缺少呼叫端的 data API 環境。
- 坑：非空 HTTP 200 壓住有效 fallback；盤中資料全缺仍 last_error=null。Sector fallback 文件亦殘留 home skill 路徑。
- 修法：按 consumer 欄位／方向做 HTTP 邊界測試與修正前紅測試；真 subprocess 模擬 launchd 空環境，private socket 交付、不存秘密；正式 restart 後只驗 key 存在性及完整資料。文件回指 repo canonical 路徑。
- 已回寫規則？：是（`tests/test_skill_endpoint_contracts.py`／`test_dashboard_launcher.py`、OPS_COMMANDS §7、MARKET_INDEX、sector fallback）；未放寬 validator。

## 2026-10-04 ｜多驗證器 registry 必須驗證實際派送
- 情境：財報完成閘從一支增加為主快取／infographic 兩支，各自手動驗證皆成功。
- 坑：server 把 registry 當 argv 展開，形成 `python validate.py validate_infographic.py MU`；路徑存在測試抓不到，合法報告被 host 判成 rc=2。
- 修法：兩個 host 共用逐支 subprocess dispatcher；測試實際 argv、每一閘失敗、第一失敗不得被後續覆蓋，並種回合併 argv 確認會紅。
- 已回寫規則？：是（routing contract 與 OPS_COMMANDS 驗證範圍）；未降低任何 validator 規則。

## 2026-10-04 ｜重啟服務只選監聽 PID
- 情境：財報比較 UI 需重啟 Dashboard 載入新 API；佇列與子程序已確認閒置。
- 坑：`lsof -ti:8080` 同時列出 FTNN 連線端，原重啟腳本會將它當成服務程序；預檢攔下，未送出 kill。
- 修法：限定 `lsof -nP -t -iTCP:8080 -sTCP:LISTEN`。初次以隔離副本完成 UI 驗收；v4.139.4 經使用者授權後正式修正原重啟腳本的三處 PID 查詢，保留其他工作區改動。
- 已回寫規則？：是（`scripts/restart_dashboard.sh` 與 `tests/test_dashboard_launcher.py`）。

## 2026-10-04 ｜低影響結論不能用來判定分析缺漏
- 情境：四個 News lane 已完成分析，三則例行／背景新聞均低增量，finalizer 仍拒絕整批，UI 只顯示 digest 缺檔。
- 坑：把多數低分直接等同未辯論；例行核准 regex 要求固定 the，來源／類型加分又把行政公告推到前排。
- 修法：先驗四 lane 完整性及 Arbiter/binary 欄位，再依全四方影響判定降級；用真實原輸入重播、完整 main 篩選回歸，錯誤顯示取 completed command 的未恢復失敗。
- 已回寫規則？：是（News Protocol、debate schema、finalizer、Stage 1 與入口測試）。

## 2026-10-03 ｜FINVIZ 403 先比較請求，再決定換資料源
- 情境：DIGEST 缺檔，實際前因是 Theme Detector 取不到 FINVIZ 產業資料，但瀏覽器可開。
- 坑：直接建議 FMP fallback 太早；finvizfinance 1.3.0 的 User-Agent 多行字串帶 13 個連續空白，HTTP 403 內有 `cf-mitigated: challenge`。
- 修法：同機比較原始／正規化 UA；只合併空白即取得 144 產業，原解析器可用。快取只認主報告，逾時需保留已取資料並揭露覆蓋率。
- 已回寫規則？：是（Theme Detector SKILL、OPS_COMMANDS 測試對照與 HTTP 邊界回歸）；未更改評分權重。

## 2026-10-01 ｜完整入口測試還需要跨過會觸發上限的輸入
- 情境：V5.5 Luna/max 試跑 NVDA，五線與風控完成，最後 export 被信心上限擋下。
- 坑：新控制器漏接既有 Phase 4.6；離線樣本 confidence=.6，低於 cap .65，未暴露斷線。組裝器另漏讀 risk_audit.position_size_pct，null 被舊 schema 寬容放過。
- 修法：走 prepare→finalize 的 .8 信心／low_data_quality 案例；必驗 .65、非 null 部位與 Phase 4.6 trace；用保存的 NVDA/BE 真實輸入離線重播完整 JSON/Markdown 閘。模型執行完成不等於成功提交。
- 已回寫規則？：是（run_workflow_v55.md、test_run_investment.py、V5.5 run evidence gate）；未修改策略門檻。

## 2026-08-10｜落地的 artifact 是子集卻長得像全集，就是在等一個長 run 來踩

- 情境：META invest run 兩次失敗，UI 報 `rc=0 but required artifact missing/stale`。使用者初判是 codex 的硬傷。
- 坑：兩個。(a) `decision_engine.py:_persist_artifact` 只寫 6/24 欄，但檔名、路徑、內容、protocol 文字四項都在宣稱它是完整的 phase-3 輸出——長 run 的 stdout 一被擠出 context，模型就會去讀它，然後 `KeyError`。(b) `comps.py:918` 把「同業不足」（一個正確答案）映射成 rc=1，撞上 V4.116.1 的 rc≠0 停機規則，PM 只好自行裁量，同一天裁了四次兩種結果。
- 修法：(a) 落地完整輸出——**裁剪的理由若來自寫入端的方便，就不該變成讀取端的契約**；(b) **修訊號不修規則**——V4.116.1 一個字不改，改的是「這件事不該回 rc≠0」。判斷句：**script 跑完了、答案是 null，那是答案；script 沒跑完，那才是失敗。**
- 已回寫規則？：是（`investment_protocol_v5_0.md` 估值錨表補明文；`MAINTENANCE.md` §2b 殘留掃描再次證明有效——掃到 `dcf.py:918` 同型缺陷，因語意不同刻意未動並記 TODO）。

## 2026-08-10 ｜zsh 把 `--include=*.md` 吃掉，殘留掃描整個沒跑卻看起來像「已清乾淨」
- 情境：V4.122.0 收尾做 §2b 殘留掃描，一次跑四條 `grep -rn "..." --include=*.md --include=*.py .`。
- 坑：zsh 對未加引號的 `*.md` 做 globbing，CWD 沒有 `.md` 檔就直接 `no matches found` 並**中止整條命令**——四條全部 0 命中。輸出長得跟「掃過了，沒有殘留」一模一樣。這是 §2c 成員 #5 的近親（pattern 自己壞掉），但機制不同：不是 pattern 比對失敗，是**命令根本沒執行**。加引號重跑後，同樣四條抓到 2 處實施表沒列到的規則鏡像（`investment/README.md` 的 OVERRIDE_BURRY 三項成本、OPS §7 的「五道紀律閘」）。
- 修法：(1) `--include` 的值一律加引號 `--include="*.md"`；(2) **殘留掃描第一條永遠是 sanity check**——先 grep 一個「已知一定存在」的字串並確認命中數 > 0，再信任後面那幾條的 0 命中。MAINTENANCE §2b 的成員 #5 已寫「驗證命令自己也要先確認 pattern 抓得到已知存在的東西」，我這次是隔了一輪才想起來套用。
- 已回寫規則？：是 —— 本條即為 §2c 成員 #5 補上 zsh 這個具體形態；掃描腳本的 sanity-check-first 慣例同時寫進 `MAINTENANCE.md` §2b。

## 2026-08-09 ｜「怕誤殺」把 cutoff 推遲一天，代價是讓真話晚一天說
- 情境：V4.117.0 三道 export 閘要挑生效日。我選了次日（2026-08-10），理由寫成「已在磁碟上的 entry 拿不到 stamp，同日 cutoff 會讓最新那筆永久紅，而紅了修不好的閘教出無視」。
- 坑：那個「永久」是我沒查證就寫下的。validator **只讀最後一筆**——下一次 run 一 append 就換掉了，紅期是一次 run 的時間。而且它**不是誤判**：當天那筆 BAC entry 確實是手寫的（7 次 `json.dump` + 6 次 `open(w)`）、`pt_revision_momentum` 確實是 null。我等於為了迴避一個一跑就好、而且說的是實話的紅，讓使用者多等一天才能驗證。使用者一句「為什麼要測隔天，是單天報告看不出來嗎」才把它問出來。
- 修法：**寫「這樣會永久壞掉」之前先把它跑出來**——我後來一行 sed 改常數就量到了真實代價，那件事在下判斷之前就做得到。通則：防禦性的預設值要標明代價量測過沒有，沒量過就不算理由。另一半教訓是連帶影響——cutoff 一改，舊閘（`valuation_reviewer_gate`，同日）的 fixture 立刻為了新閘的原因紅，**同日生效的閘彼此的 fixture 要互相滿足**。
- 已回寫規則？：是——cutoff 改回 2026-08-09，CHANGELOG／SESSION_NOTES 的原理由段一併更正（不留錯誤考據，見 2026-08-08 那條）。

## 2026-08-09 ｜靜默綠第七種：測試**繞過呼叫點**，於是「閘沒接線」測不出來
- 情境：V4.117.0 三道 export 閘。前兩道的合約走真 validator subprocess，第三道（`calculation_steps` parity）為了餵 artifact 方便，全部改成直接呼叫 `V._check_calculation_steps_parity(...)`。
- 坑：種回 bug 時把該 check 從 `main()` 拆成 `pass`——**閘完全不生效，測試十項全綠**。這與 §2c 既有五個成員不同：那些是「操作寬容失敗」，這個是**測試自己選了一條不經過真實呼叫點的路**。形狀與 V4.116.2「`invest` 從沒進 `PROTOCOL_VALIDATORS`」完全一致：沒接線的閘沒有症狀，而直呼式測試把「函式行為對」誤當成「閘生效」。
- 修法：任何閘的合約**至少要有一個案例走完整入口**（此處是 validator subprocess），哪怕為此得多準備 fixture（我為它造了 `ZZWIRED` ticker + 臨時 artifact）。判準：**問自己「把這個 check 從 main() 刪掉，測試會紅嗎」**——答不出來就是還沒測到接線。
- 已回寫規則？：是——`OPS_COMMANDS.md` §7 新增該測試列並寫明含接線斷言；`MAINTENANCE.md` §2c 家族第 7 項。

## 2026-08-09 ｜共用假設在「換執行者」時才會現形，而它挑最貴的那支現形
- 情境：`invest_20260809_000447` rc=1，208K token 零產出。V4.106.0 起 quota broker 為 protocol run 指派 provider；這是 invest 15 次歷史裡**第一次**跑到非 Claude（前 14 次全是 `claude:opus`）。
- 坑：invest 的 prompt 是裸觸發詞 `分析 {ticker}`，語意完全靠 agent 自動載入 CLAUDE.md 的觸發表——**這個假設從沒被寫下來，因為在單一 agent 時代它永遠成立**。`agy --print` 不載入任何專案 context 檔，於是 agent 從頭到尾沒 list 過自己的 cwd，循 `~/.gemini/projects.json` 的過期路徑跑去舊鏡像目錄亂找。同天同 provider 的 `triage` 兩跑 rc=0——那支 prompt 把每條 script 路徑寫死，**可攜性差異一直存在，只是之前沒抽到那支籤**。
- 修法：(a) 診斷看「agent 沒做什麼」——沒進 cwd 比任何錯誤訊息資訊量大，最後那句 `Agent execution terminated due to error.` 什麼也沒說；(b) **CLI 行為用探針測，不要讀它二進位裡的說明文字**——agy 內含 directory-based rules 的完整描述，照讀會得出「它會載入」的錯誤結論，兩題禁用工具的探針才問出 `NONE`；(c) 把假設寫進 prompt：每個非 claude provider 的前導點名自己的 context 檔 + 本次 protocol 規範路徑 + cwd 邊界；(d) 可攜性用 `protocol_providers` 白名單顯式編碼，別讓 broker 靠運氣。
- 已回寫規則？：是——`CLAUDE.md` 檔頭「唯一手寫來源 + 生成」、`MAINTENANCE.md` §2 加 `sync_agent_context.py --check`、`OPS_COMMANDS.md` §7 兩列、`tests/test_protocol_model_routing.py` 擴充。

## 2026-08-09 ｜「單一真相來源」在多 CLI 下會反轉成 bug
- 情境：同上。CLAUDE.md 原本明文「觸發表是唯一 source of truth，AGENTS.md 只引用不複製」。
- 坑：這條規則在單一 agent 下正確，在四個**各自只自動載入自己那一個檔**的 CLI 下，「引用」等於要求它們先去讀別人的 context 檔。順手驗出 codex 與 grok 也是壞的——兩者都確實自動載入 `AGENTS.md`（grok 讀的也是這個檔，不是 GROK.md），但那個檔當時就寫著「表在 CLAUDE.md，不要複製」，所以問它們 `分析 TICKER` 讀哪個檔一樣答 UNKNOWN。**只有 gemini 炸掉，是因為只有它連自己的檔都沒載入**；另外兩家的殘缺沒被觸發過，也就沒人知道。
- 修法：改成「唯一**手寫**來源 + `scripts/sync_agent_context.py` 生成另兩檔的 delimited 區塊」，`--check` 進收尾 checklist。要避免的是**複製造成的漂移**，不是複製本身——當消費者彼此隔離時，生成比引用正確。
- 已回寫規則？：是（同上）。

## 2026-08-08 ｜結論對、但支撐結論的事實錯了——錯誤考據會被後人當事實引用
- 情境：風控三支 Batch B 決策備忘（v4.112.0），三處被 review 抓到考據不實。
- 坑：(a)「兩年來沒人依它決策」——專案只有幾個月歷史，修辭失控；(b)「33/47 **精確**落在格點」——±0.0005 其實只有 13/47，±0.005 才 33/47，而該容差的 8 個 bin 覆蓋了觀測區間 42%，所以 70% 是支持性不是決定性；(c)「fragility_downgrade 兩次都 ROBUST」——實際是三列 FRAGILE/FRAGILE/ROBUST。**三處的結論都成立**（該刪的還是該刪），但寫進 CHANGELOG 的理由段會被後人當事實引用，錯的考據比沒有考據更糟。
- 修法：(a) 涉及時間跨度、次數、比例的斷言，先跑一次確認再寫，不要憑印象修辭；(b) 「精確／完全／全部」這類詞出現時，回頭確認容差是多少、分母是什麼——本例正確寫法是「精確簇 0.140 出現 8 次」（那才是決定性證據），而非籠統的 70%；(c) 引用歷史產物的統計（出現幾次、每次什麼值）要逐列印出來看，`grep -l` 只給檔數不給列數。
- 已回寫規則？：**是（2026-08-08 補）——家族湊滿五個後固化為 `MAINTENANCE.md` §2c「靜默綠」防線。** 後續三個成員：③shadow 猜錯被測介面回空 dict，空結果被讀成「零差異」；④`str.replace` 錨點打錯**原樣返回**，寫回去等於沒改而回報說已更新（就發生在回報 ③ 的那個 commit 裡）；⑤驗證用的 grep pattern 自己漏了反引號，回 0 命中。五個共同的成因是 **API 為了方便而選擇寬容失敗**，而寬容失敗在寫入路徑上讓「沒做到」和「做到了」產生相同的觀測結果。

## 2026-08-06 ｜Projection metadata 不能取代 record contract
- 情境：同日 append-only News projection 同時包含 DIGEST 與 FLASH。
- 坑：validator 用頂層 DIGEST/PER_AGENT_BATCH 規則檢查所有 deep records，把合法 pending/INLINE FLASH 誤判失敗；artifact 已存在但 Dashboard 任務顯示消失。
- 修法：混合 projection 的 review/cache/isolation/算分一律按每筆 `event_type` 與 `fanout_mode` 驗證，頂層 mode 只描述 anchor；回歸測試必含異質 records。
- 已回寫規則？：是（v4.99.1 record-level validator 與 mixed DIGEST+FLASH test）。

## 2026-08-06 ｜對抗 lane 的分數距離不是事件狀態
- 情境：News Arbiter 用四 lane 最大分差判定 BINARY，而 Bull 契約限定 +1..+5、Bear 限定 -5..-1
- 坑：拿刻意設計成異號的對抗分數做 max-min≥4，幾乎必然觸發；連續五份 digest 25/25 全成 BINARY，測試仍綠，因為只驗 enum/shape、不驗分布與事件語意
- 修法：事件狀態（binary/pending/date）與方向強度（net score/debate spread）分欄；validator 由共用 deterministic 規則重算。任何分類規則上線前，用至少數日真實 artifact 檢查 label distribution，不能只測單筆 fixture
- 已回寫規則？：是（News Protocol V2.3、`arbiter_rules.py`、semantic validator 與 distribution 觀察 TODO）

## 2026-08-06 ｜API 回 200 不代表區間資料完整，enrichment 前要先縮 universe
- 情境：修 sector prefetch 的 earnings calendar 360 秒 timeout；中央 limiter 已把流量壓在 220 RPM，仍跑不完
- 坑：未來 7 日 calendar 回 2,837 symbols，程式對每支逐一打 `/profile` 才篩 market cap；同時過去 30 日 calendar 回剛好 4,000 rows、HTTP 200，實際日期卻只覆蓋最後 8–9 天。前者是 filter-after-fetch 的 2,837-call fan-out，後者是無錯誤訊息的 response cap 截斷
- 修法：enrichment 前先用一次 bulk/screener snapshot 本機交集，禁止把「篩選所需 metadata」做成逐 symbol 請求；範圍 API 若筆數碰到已知 cap，必須切段、去重並在單日仍飽和時 fail closed，不能把 HTTP 200 當 completeness 證明
- 已回寫規則？：是（4.95.7：`sector/lib/earnings_calendar.py` 分段完整性；Step 3 改 cached company-screener join；`sector/scripts/README.md` 記錄契約）

## 2026-08-02 ｜估值引擎驗收只驗 happy path，等於沒驗
- 情境：4.76.0 交付 MU structural-shift DCF + range-only peer fallback，驗收是「MU 跑出 $762.13、測試 rc=0、validator rc=0」，看起來很完整
- 坑：後續 review 找到 12 項問題，**全部**在 degraded / fallback 分支，happy path 一項都沒錯——因為 MU 剛好是「3 季已公布 + 有 next-quarter estimate + estimates 有 ebitAvg」的最順情境。實際踩到的：2 季 ticker 會拿已公布季度獲利除全年營收估計（`dcf.py` start EBIT margin）；缺年度估計時整條成長路徑直接套成長上限表 45/30/20/12/8（把「證據上界」當「預設值」）；confirmed shift 建不起來時靜默退回 legacy 而 legacy 對該股會算出負 terminal FCFF；資料缺失的 ticker 在非 `--json-only` 模式直接 TypeError 而不是 degraded
- 修法：引擎類交付的 DoD 加一條——**每個 early-return / fallback / except 分支都要有一條 regression test**，且測試 fixture 不能只有一個「資料齊全」版本。寫 fallback 時問一句「這個預設值是保守還是最寬鬆？」缺資料一律往保守 + 出聲（寫 reason 進 payload + warnings），不准往上界靠
- 已回寫規則？：是（`skills/valuation-modeler/SKILL.md` 新增「缺資料時的紀律（degraded path）」段；本條記通則，其他引擎同樣適用）

## 2026-08-14 ｜報錯的閘不是壞掉的閘：UI 只截得到第一行
- 情境：使用者貼 `validator rc=1: [validate_digest_output] ✗ schema drift (expected V2.3):; - FR` 問為什麼。
- 坑：validator 完全正常。當天沒產出 digest，它退回抓兩天前那份 → freshness fail，而 `dashboard_server` 把前 5 行用 `"; "` 接起來、UI 再截到約 60 字元，於是**只有標題行倖存**，標題行說的是 schema drift。真正的 rc=1 在 `news/scan_logs/` 的 `finalize_digest.py`。
- 修法：(a) 診斷從 `news/scan_logs/<protocol>_*.log` 的**最後一個非 0 rc** 開始，不要從 validator 訊息往回推；(b) 寫 gate 的失敗輸出時，**第一行就要是結論**——後面的 bullet 在這條管線上等於不存在。`validate_digest_output.fail()` 因此加了 header 參數。
- 已回寫規則？：是（`news/scripts/validate_digest_output.py` 的 `fail()` 註解寫明第一行是唯一倖存的行）
