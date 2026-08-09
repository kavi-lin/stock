# Session Notes 歸檔 v4.100.1 → v4.111.4（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v4.111.4) — 錯誤訊息指著兩個不成立的原因;而測試 stub 比真 daemon 寬鬆

- **緣起**:使用者貼上 `quota broker: ... (broker:rejected). Check lqb status; the daemon may be down, or every provider is inside its 20% hard reserve.` 問「這是什麼錯誤」。跑 `lqb status`:daemon 正常、claude 51% / agy 78%,**訊息點名的兩個原因都不成立**。
- **真因是上一個 commit 自己種的**:V4.110.0 把 protocol 的 task type 改成 `agentic_protocol:<name>`,broker 的欄位 pattern 是 `^[a-z0-9][a-z0-9_-]*$` —— 冒號不在裡面。每次 acquire 拿 400 → `_acquire` 歸類為「本 repo 的 bug,不准降級」→ fail-closed。**`分析`/`產業掃描`/triage 全線停擺,而面板顯示額度充足。**
- **診斷用 preview 重現,不燒額度**:`client.recommend(task, reserve=False)` 走同一條驗證路徑但不開 reservation,直接印出 daemon 的 `string_pattern_mismatch`。**要驗「請求合不合法」不需要真的佔額度。**
- **為什麼測試沒抓到**:`tests/test_broker_gate.py` 的 stub server 收下任何 `task_type`。**stub 比真服務寬鬆 = 這支測試對 fail-closed 回歸完全無感** —— production 每一次 protocol run 都 400,測試卻全綠。修法是把 daemon 的 pattern 搬進 stub;把分隔符改回 `:` 重跑,測試如實炸在 `ProtocolBlocked`。
- **兩份 sanitiser 是這個 bug 的成因**:單發路徑的 `_task_type()` 一直有清洗(所以它沒事),`protocol_task_type()` 是後來寫的第二份、沒有。這版合併成 `broker_gate.sanitize_task_type()` 一份,放在 pattern 旁邊。**同一條約束有兩個執行點,遲早只有一個會被更新。**
- **順手修掉誤導**:三個 note(`refused` / `unavailable` / `rejected`)本來共用一句話,而那句點名的兩個原因正好都不是 `rejected` 的意思。改成 `_blocked_reason()` 分流。**錯誤訊息把人送去看 `lqb status`,而 `lqb status` 一切正常時,人會先懷疑監控壞了,不會懷疑訊息本身。**
- **驗收**:`test_broker_gate` / `test_model_router_window` / `test_protocol_model_routing` 三支 rc=0;對真 daemon preview `agentic_protocol-invest` / `-triage` / 無名三種皆 200(recommended=agy)。冒號形態從未進過 ledger,無 history 需要遷移。

## 🟢 Session Note (v4.111.3) — 交接文件把假設寫成了事實;真的去 profile 只花了 20 分鐘

- **緣起**:使用者回報開委員會 Dashboard 系統會卡頓,並附上另一個 session 寫的交接文件。該文件量測扎實(時間軸、`/v1/status` 30 秒節奏證明分頁開啟時刻、關閉前後程序對比),但**它的結論段和它自己的證據段互相矛盾而沒有被察覺**:第 2 段花大篇幅列出 56 個 `setInterval`、只有 10 處 `document.hidden` 保護,第 3 段又誠實寫下「每分鐘 166 次小 JSON 請求在算術上燒不掉一整顆核」。**它自己已經否證了自己的主張,卻仍在第 4 段規劃 `pollEvery()` 收口 46 處的重構。**
- **它說「沒有人 profile 過」是對的,而這正是唯一該做的事**:Safari 沒有可程式化接上的 profiler,但 Chrome 有 —— `--headless=new --remote-debugging-port` + CDP,用 node 22 內建的 `WebSocket` 直接講 protocol,不需要裝 puppeteer。`Performance.getMetrics` 拆出 Script/Layout/RecalcStyle,`Tracing` 數 Paint/Commit/RasterTask。**「手邊沒有那個瀏覽器的 profiler」不等於「量不到」。**
- **timer 假設當場出局**:各頁 ScriptDuration 只有 0.4%–2.8% 一顆核。index.html 閒置 3.0%、sector 1.8%、momentum 1.3%。**真正的訊號在 Paint**:decisions.html 閒置時 110 Paint/s、56 Commit/s、50 秒 2789 次 style recalc,而 index/sector 是 0.1–0.6 Paint/s。同樣掛著那 56 個 timer,差異卻是 100 倍——**差異在哪,元凶就在哪;共通項不可能解釋差異。**
- **根因是一行 CSS 配一個 1 秒 timer**:`decisions.html:35` 的環帶 `transition: stroke-dashoffset 0.9s linear`,`updateRefreshStatus` 每 **1.0** 秒寫一次 `strokeDashoffset`。**每秒啟動一個 0.9 秒的 transition,永遠接不完**,而 `stroke-dashoffset` 不可合成,每格都要主執行緒重新光柵化。這頁從開啟那刻起就沒有 idle 過。0.9 < 1.0 看起來還「留了 0.1 秒餘裕」,實際上餘裕從來不存在——**只要 transition 沒結束前下一次寫入到達,它就會續上,而它每次都到達。**
- **A/B 是唯一能結案的證據**:只把那一個 transition 關掉、其他不動 → Paint 111.9→3.1/s、Commit 56.0→1.1/s、`document.getAnimations()` 從 1 變 0。**證明它是這頁唯一在跑的動畫**,不是「疑似相關」。
- **一併排除的,每一條都有量測**:記憶體洩漏(掛 3 分鐘,元素數固定 13,921、heap 與 listener 都在降)、`dashboard_server.py`(開機至今累計 1:10 CPU)、backdrop-filter(86 個 blur 全關掉,Chrome 每格反而 0.65ms→1.15ms,**因為少了分層,推翻我自己原本的假設**)。
- **沒有結案的部分要講清楚**:Chrome 上此頁最高 8% 一顆核,而使用者在 Safari 看到的是燒掉一整顆核。**我無法證明這一行 100% 解釋 Safari 那顆核**,只能說 56 fps 的零產值重繪在任何引擎上都是純浪費。修完仍卡就得回到 Safari Web Inspector。
- **同類問題留了一個沒動**:`intraday-eval.html` 閒置 241 Paint/s,來自 3 張**可見**的 `.ie-scard.repeat-strong` 在動 `box-shadow`(`style.css:4874-4875`)——同樣不可合成。它是刻意的視覺設計,改會動到外觀,屬於使用者的美術決定而不是我的 bug 修復,所以只回報不擅改。
- **值得記住的偵測手法**:`getComputedStyle(el).animationIterationCount === 'infinite'` 掃出來的東西會騙人——decisions/index/sector 三頁都掃到同一個隱形的 `chain-pill-head-icon` 旋轉圖示,但只有 decisions 在燒。**`document.getAnimations()` 才是權威清單**(它涵蓋 transition,而 transition 正是本案元凶,`animationIterationCount` 永遠看不到它)。

## 🟢 Session Note (v4.111.0 ~ v4.111.2) — 一個數字有四套門檻時,錯的通常不是門檻,是「誰有資格著色」

- **緣起**:使用者兩個要求。(a)「llm_quota_broker 傳進來的東西視覺化,永遠顯示,不用再放齒輪裡」,外加一個問題「本地用量現在還重要嗎」。(b) 看到 AI 裁決卡的 tooltip 後說「顏色應該跟裡面 popup 一致,應該要偏綠色;dialog 有 75~90 跟下面黃燈 60~85 邏輯上 conflict,給一個統一的標準」。
- **本地用量的答案是「一半死了、一半是唯一來源」**:`calls / daily_max` 在 broker 在線時完全不參與決策,只有 broker 關掉/連不上才是真閘門;但 `tokens` / `cost_usd` **broker 根本不報**,本地帳本是全專案唯一的花費紀錄。所以不是「留」或「砍」,是拆開:次數階梯改成只在降級狀態顯示(那時它才是真限制),花費壓成常駐一行。**「這個欄位還重要嗎」這種問題,答案常常是「要看是哪一半」。**
- **面板原本丟掉的資訊比顯示的多**:`provider_quota()` 只回傳所有 bucket 的 min。但 min 藏住的正是可行動的部分——claude 54% 是週池要等 8/13,gemini 78% 旁邊有個今晚就重置的 5h 窗。**同樣的 headline 數字,對「現在跑還是等等跑」是相反的答案。** 補回 per-bucket 明細 + 20% 硬保留線(以前使用者看到「還剩 15%」卻被拒派,面板不給任何解釋)。
- **順手避掉的成本 bug**:一開始把 `hard_reserve_percent` 寫成獨立函式,等於每次輪詢打兩次 `/v1/status`。改成 `quota_snapshot()` 一次取回 — 兩者本來就在同一個 response 裡。**這種「多一倍流量但功能正常」的寫法不會讓任何測試變紅**,和 v4.107.0 那個 mtime 恆真是同一類。
- **曝險門檻的根因不在門檻,在著色權**:程式裡有**五份**互相矛盾的定義(exposure guide 85/60/30、synth guide 75/50/25、sector pill 75/50、`script.js` pill 又一份 85/60/30),但真正讓使用者看到紅色的是第五個——`components.js` 的曝險卡寫 `color: sty.fg`,`sty` 是**裁決 stance**。它是整個 grid 裡唯一一張「顏色與自己的數字無關」的卡。所以 75-90% 被畫成 DEFENSIVE 紅,而它自己的 tooltip 說那是標準區。**四套門檻是噪音,一張卡不看自己的數值才是 bug。**
- **同一張卡還有第二個分岔**:圓環填充用中位數 82.5,環上印的數字卻是上界 90 — 一個環同時講兩個數。統一成「區間取中位數 → 同時決定顏色、填充、數字」。
- **統一標準選 75/50/25 的理由不是偏好**:synth guide 與 sector pill 已是這套(2:1),而且它是 synth 公式「三個中位數取 min」當初寫的邊界。抽成 `UI.EXPOSURE_TIERS` 後五個 consumer 全部改讀它,連 `STAGE_DOTS` 的燈號也從 tier 表生成——**日後改門檻不可能漏掉某一份。**
- **回報時明講了行為變更**:這次改完,目前的上限會從紅變綠。這是移除 stance 污染後的正確結果,但它改變使用者每天看盤的顏色語意,所以動手前先講、等使用者點頭才做。
- **驗收**:`test_broker_gate` / `test_protocol_model_routing` / `scripts/_shared/tests` rc=0(7 passed)。曝險 tier 用 node 實跑 9 個輸入驗證邊界連續且 75-90%→82.5→進攻/綠。LLM 面板用 DOM stub 對**實際 broker payload** 渲染四種狀態(正常 / broker 連不上 / broker 關閉 / 無 broker key)與中英雙語,均正確。瀏覽器擴充當時未連線,故未做視覺截圖驗證。
- **v4.111.1 續:同一個 bug class 還有三例,而我第一輪只修了被指出的那一個。** 使用者接著回報頂部風控 31.6 顯示綠色但 tooltip 說 🟡。根因與曝險完全相同——卡片用通用 `colorByScore(n, inverse)`,tooltip 各有五段級距表,那個 helper 的 35/65 兩個切點和任何一份都對不上,而且沒有橘色。廣度同一個 helper(60/40 剛好對得上,但把 25-39 🟠 與 0-24 🔴 併成一個紅)。**教訓:抓到「同一個量有兩套定義」時,要把同一個 render 迴圈裡的其他項目一併盤過,而不是只修被指到的那張卡。** 五張卡裡我第一輪只查了一張。
- **Macro 卡的 popup 從來沒有存在過**:掛著 `data-tip-key: 'macro_briefing_tip'`,但沒有任何一頁的 `PILL_TIPS` 有這個 key,`showTip()` 每次第一行就 return。**看起來接好了、實際靜默沒有**——和 v4.106.0 那組 fail-silent 同族。移除時還要一併拿掉 `data-tip-text`/`title`,否則 sector.html 上 `[data-tip-key]` 監聽器會與新的 signal tip 同時觸發,一次 hover 疊兩個 tooltip。
- **面板收斂**:使用者要求灰字全收進 hover、兩句說明移除。常駐區只剩長條;細節(全部窗口、重置時間、plan/confidence/新鮮度、逐 provider 今日花費)進 hover card。花費改逐 provider 是順勢而為——本地帳本本來就逐 model 記。broker 掛掉時沒有 provider 列可 hover,所以降級路徑保留常駐花費行。
- **一個差點犯的錯**:hover listener 綁在 `_initLlmPanel()` 裡,而 `renderSidebar()` 會在語言切換時重跑——綁兩次會讓同一個元素被兩組 listener 一顯一隱地閃爍。加了 `UI._llmTipBound` 一次性旗標。
- **v4.111.2 sidebar 重整**:主題/風險容忍/語言/日誌四個控制項原本佔滿 footer,風險容忍還是整條寬按鈕——**設定幾天才動一次的東西,拿走了視線最常落下的位置**。全部收進 header 齒輪的 popup,footer 只留額度面板。語言列順勢改成顯示**當前**語言而非「點了會切到哪」:它原本是獨立 toggle,`English` 意思是「切到英文」;放進 popup 與「主題 · 深色」並排後,同樣的字會被讀成現況陳述。**同一個字串的意思會隨它旁邊的鄰居改變。**
- **同一個一次性綁定坑,這輪又出現一次**:popup 的 outside-click / Escape 監聽也不能綁在 `renderSidebar()` 裡。而且主題與語言切換本身就會重繪 sidebar、把 popup 銷毀,所以要 `UI._reopenSettings` 切完自動重開——在選單裡切主題不該順手把選單關掉。

## 🟢 Session Note (v4.108.0) — 「拒絕判斷」不該是唯一選項;不獨立的證據要標出來,不要假裝獨立

- **緣起**:使用者說「還在虧損、但市場明顯已經在追逐的題材股,需要有特別的一個 anchor 去判斷」。我上一輪的結論是「AAOI 轉盈前結構上拿不到 decision-grade 估值」——`insufficient_anchors` 正在正確地拒絕替一個所有內在價值法都無定義的標的製造數字。那個結論本身沒錯,但它把「拒絕判斷」當成唯一選項。
- **動手前先驗兩件事**:(a) 八根全滅是**結構問題疊加時序問題**——`pf_quant` 16:39 跑、earnings cache 19:01 才寫入,裡面其實有 `price_target_consensus $160`。修掉時序後仍只有 1 根,所以結構問題是主因,但起點從「0 根救起」變成「只差 1 根」。(b) 上一輪構想的 EV/Sales 分位錨對 AAOI **根本救不了**:`select_valuation_peers` 回 0 家,shadow 層本來就為 hypergrowth 準備的 `peer_ev_sales_implied` 同樣 null。不是方法不適用,是沒有同業中位數可乘——**任何吃 peer median 的設計在題材股上都會重複踩這個坑,因為題材股常常正是「沒有可比同業」的那種股票**。
- **做了什麼**:第 9 根 `fwd_earnings_discounted`(peer-free:覆蓋 ≥3 家的最遠獲利年度 EPS × justified PE ÷ CAPM 折現)+ `market_implied_revenue`(FCF ≤ 0 時 reverse DCF 的替代)+ Phase 4.6 speculative governor。AAOI:0 根 → 2 根、conf medium、FV $156.56 vs 現價 $133.5。
- **最關鍵的誠實性取捨**:新錨與 `analyst_pt_consensus` **都源自同一批賣方分析師**,family topology 卻會給它們各一票。我沒有假裝它們獨立(那會讓 confidence=medium 名不副實),而是讓 pack 明說 `evidence_independence.sell_side_only`,由 governor 用**籌碼**回應:size ≤ 1%、conf ≤ 0.70,但 `final_decision` 不動。系統因此從「拒絕判斷」變成「判斷可以,但這個判斷的前提是相信賣方 FY 預估,所以只給探針倉」。
- **差點重犯的錯**:governor 縮小倉位後,export 會在 validator §14 撞上「倉位必須等於 sizing_chain 鏈尾」——決策放行了卻卡在 Phase 5,等於白做。這正是 V4.86.0 對 decision cap 犯過的同一個錯(當時 cap 讓每一份 export 都被拒)。寫 governor 時同步補了 §14 的合法出路,並加兩條 integrity 檢查防「用新錨解鎖決策卻不掛 governor」。
- **紀律備忘**:**新增一根 anchor 時,要能證明它沒有動到既有的任何一根。** 初版把 hypergrowth archetype 的權重重新分配來騰出 0.15,`hyper.shadow_wfv` 立刻從 262.91 變 276.65、verdict 翻轉——那是不必要的附帶損害。改成「條件錨的權重掛在 1.0 預算之外」後既有 fixture 全綠,而全綠本身就是「零附帶損害」的證明。同理 #3b 翻轉率報告日後才能把差異單一歸因到「多了這根」。
- **接著使用者問「clamp 值要怎麼校準」——答案是反解,不是等待**:把公式倒過來得出市場隱含 justified PE(`price × (1+r)^h ÷ target_eps`),即「同一個目標年度 EPS、同一個折現率下,市場實際付幾倍」。實測 11 檔:全母體中位數 36.7、上限 35 實際綁到 8/11、AAOI 的隱含 PE 31.6。做成 `shadow_report.py` 的常設區段 + `test_shadow_report.py`。
- **為什麼不能沿用 `#2 dispersion` 那套 percentile 手法**:`agreement_grade` 的門檻是**描述性**的,切在它所描述的那個分布上;PE clamp 是**因果**參數,直接決定輸出——拿它自己的輸出來校準它會循環。市場隱含 PE 外生於這根錨,才是合法的校準標的。同理**不可自動跟隨中位數**:泡沫期中位數上移、上限跟著上移,錨就永遠不會說貴——與被我拒絕的 EV/S 分位錨同一個陷阱、方向相反。所以判準只出報告,改值一律 user 核准。
- **兩個被實測否決的設計**:(a) 校準原本要讀 `history.json`(其餘 shadow section 都讀它),但那要等 session 累積,直接違背「立即可用」這個提案理由——改讀 `*_pf_quant.json`,每次 Phase 1.5 都產出且對 shadow anchor 一樣留有原料。(b) 原本想用 archetype 分層母體,實測 11 檔有 6 檔是 `balanced / rule=no_inputs`(缺 earnings-analyst cache,不是真的不屬於 hypergrowth),拿它過濾會靜默丟掉多數樣本;改用 anchor 自己的 scope 判定——引擎算的、必然存在、定義上就等於「這根錨真正服務的母體」。
- **今天的判準是 `accumulating`,而那是誠實的**:live cohort 只有 AAOI 一檔。全母體那組(中位數 36.7)只當背景脈絡印出來並明確標註「不是校準目標」,因為 MSFT 23.5x 與 NET 182.7x 混在同一個分位裡沒有意義。
- **量完之後,兩個常數的問題方向相反**:`FWD_PE_CLAMP` 上限 35 撐得住(全母體隱含 PE 中位數 36.7);但 `TERMINAL_EV_SALES = 4.0` 被我在文件裡誤稱為「成熟中樞」——實測成熟獲利公司 median EV/S 是半導體 13.9 / 通訊設備 8.3 / 軟體 8.0 / 工業包裝 2.8,**4.0 其實在工業水準**。改成雙情境輸出(4x 需 32% / 8x 需 15%),並把 4.0 正名為壓力測試用的規範性假設。**校準的第一個產出常常不是新數字,而是發現舊註解在說謊**——那句誤述會讓人把壓力情境當中性基準讀。
- **順手抓到 4.106.0 那個家族的第三個實例**:SPCX beta=0(IPO 2026-06-12,歷史不足兩個月)。舊行為讓它落到折現率**下限 10%**,是 11 檔樣本裡最寬鬆的一檔——新上市 → 歷史不足 → beta=0 → 最低折現率 → 最高估值,整條鏈沒有任何一步會報錯。改成 `beta ≤ 0`／缺值 → 母體中位數 2.73(n=14 實測),r=16.9%,anchor $115.18→$99.50(現價 $129,由 +0.2% 轉 −23%)。有效 beta 的標的完全不動。判準記成一句:**無效輸入必須落到保守預設,不是中性預設**(CAPM 的 `beta=1.0` 就是中性預設,對這個母體剛好是錯的方向)。
- **一個必須寫進 docstring 的限制**:`market_implied_pe` 是「**在我們假設的折現率下**」市場付的倍數,不是無假設的市場觀測——SPCX 的 beta 修正把它從 38.8 推到 45.3。所以倍數校準與折現率校準不能同時做,要先釘住折現率再看 PE 分布。
- **驗收**:`test_compute_price_framework`(+Fixture 11,約 60 個新斷言)/ `test_shadow_report`(新檔)/ `test_decision_engine`(+Fixture L2)/ `test_session_export_schema`(+§10b 八案例)/ `test_valuation_pack_consistency` / `test_lane_contract` / `test_phase1_factpack` 全 rc=0。實跑對照:AAOI 新錨 live($153.13、3 位分析師、horizon 1.399y)、MSFT 值算出 $452.66 但正確判 `ineligible: cashflow_intrinsic_anchors_live` 且 live FV 394.02 不動。

## 🟢 Session Note (v4.107.0) — mtime 不是新鮮度,除非「寫入」等於「內容真的變了」

- **緣起**:4.106.0 修完,使用者問「剩下的所有 anchor 各是什麼」。逐根盤點八根時發現第 8 根 `forecaster_blend` 是**同一個 pattern 的第二例**——`compute_price_framework.py:1330` 只做 `os.path.exists`,protocol `:582` 列了生成指令卻沒人跑。補進 factpack prewarm(0 LLM、4h TTL、命中 0 call),MSFT 實測 `anchors_available` 8/8、`forecaster_blend $598.42`。
- **我自己踩的坑**:初版新鮮度判斷寫成「earnings cache 比 forecaster cache 新 → 強制 refetch」。恆真。因為 `analyze.py` 每次都**就地改寫** earnings cache,mtime 永遠是「剛剛」。結果每跑一次 protocol 就多一次完整 refetch,MSFT 27.6s。是實跑時間異常才抓到——測試不會抓,因為它 mock 掉 subprocess。
- **修法**:改由 `prewarm_earnings_cache()` 解析 `fetch.py` 自己在 stderr 宣告的 `cache hit:` / `wrote`,回傳 `(status, refreshed)`。fetch.py 的 cache key 是 `(TICKER, last_earnings_date)`,它的決定才是「季度有沒有換」的權威。修後 1.33s。
- **紀律備忘**:**mtime 只在「檔案被寫入 == 內容有意義地改變」時才是新鮮度訊號。** augment-in-place 型的 cache(analyze.py 這類把 derived 欄位寫回原檔的流程)一律不成立。要嘛用內容鍵,要嘛讓真正做決定的那一層自己回報。另外:這種「成本 bug」不會讓任何測試變紅,只會讓每次執行慢一點、多燒一點配額——只能靠實跑計時抓。
- **順帶釐清**:使用者問「8/7 財報 EPS 明明是 0.06,為何系統說負的」。$0.06 是**非 GAAP 單季**(beat $0.03 est),系統用的是 **GAAP TTM** −0.78(−0.28/−0.19/−0.03/−0.28 四季相加),FMP 的 `priceToEarningsRatioTTM` 也是 −159.5。`forecast.py:1114` 明訂 TTM EPS ≤ 0 時 PE-multiple math 無效。兩個數字都對,基礎不同;`peer_pe_implied` 掛掉是同一個原因。
- **一個未收口的洞**:cache 缺席時 `valuation_reviewer_gate` 的 `transition_case_active`(五個 trigger 裡唯一 mandatory)會讀到 `transition_case=False`——把「沒查過」渲染成「查過了不是」。protocol 判讀規則已加註,但 gate 本身仍不區分 false 與 unknown,列為待辦。
- **驗收**:`test_phase1_factpack.py` 擴到 27 案例(新增換季旗標、forecaster 五條路徑);MSFT 8/8 錨、AAOI 回報 `unavailable: negative_or_missing_ttm_eps`;穩態計時 MSFT 1.33s / AAOI 2.60s。

## 🟢 Session Note (v4.106.0) — 只讀不生的快取依賴,會在「當天發財報」那天靜默崩掉

- **緣起**:使用者問兩件事——「為什麼 V5.3 的卡片沒有現股估值跟未來前瞻」、「今天 AAOI 的個股分析有參考今天的財報嗎」。追下去是同一條線。
- **卡片空白**:`page-decisions.js` 的版本閘是列舉白名單 `version === 'V5.0' || version === 'V5.1'`。4.90.0 把 schema 推到 V5.3 時只補了 `VERSION_COLOR` 色票、漏補這行,V5.2/V5.3 卡片因此整段 Layer 3(現值估值 + 未來前瞻)與 Red Team 區塊不渲染。資料一直好的(`data.json` 的 `forward_expectations.range` 三點俱全)。改成 `versionAtLeast()` 數值比較。
- **估值 0/8**:protocol 從來只**讀** earnings-analyst cache,沒有任何一步會**生**它——`phase1_factpack.load_earnings_bundle()` 與 `compute_price_framework._latest_earnings_cache()` 都是純 glob + fail-soft。AAOI 當天發財報,16:39 Phase 1.5 跑時 cache 還不在(`pf_quant` 的 `earnings_asof` 為 null、lineage 寫成 `earnings_analyst:AAOI:unknown`),8 個 anchor 全 `missing_or_nonpositive_value` → `insufficient_anchors` cap。16:59 的 forward_expectations 快照已讀到 Q2 數字——cache 是在估值 pack 凍結**之後**才生出來的。修法:factpack 讀 bundle 前先跑 `fetch.py` + `analyze.py`(0 LLM)。
- **順手挖到的第三個**:`us-stock-analysis/analyze.py` 的 bundle merge 用 `locals().get(block_name)` 解析目標,`_derive_from_bundle()` emit 的 5 個 key 有 **3 個對不上區域變數名**(`margins_cash`/`earnings_calendar`/`balance_sheet`),覆寫算完就被丟掉。所以 bundle 就算新鮮,margins 仍然輸給 yfinance。另 `revenue_yoy_pct` 只走 yfinance `info.revenueGrowth`,該欄位落後財報發布(報告寫 +51.4% 是 Q1,FMP 當下已是 Q2 的 +86.4%)。
- **紀律備忘**:三個 bug 共用一個形狀——**失效方向都是靜默且 fail closed 在最新的資料上**。列舉白名單對新版本 fail closed、`locals()` 對改名 fail silent、fail-soft 的快取依賴對「今天剛發生的事」fail silent。`fetch.py` 自帶 `(TICKER, last_earnings_date)` 快取閘,所以「先確認再撈」不必另接 calendar:income-statement 的最新日期回答的是「數字可查」,calendar 只回答「已宣布」,anchor 要的是前者。
- **驗收**:新增 `test_phase1_factpack.py`(13 案例,鎖 fail-soft 五條路徑 + fetch 失敗必須不跑 analyze)與 `test_bundle_merge.py`(15 案例,鎖 registry 與 emit 端漂移;此測試在撰寫當下就抓到我 registry 少一格 `balance_sheet`)。既有 `test_compute_price_framework` / `test_lane_contract` / `test_valuation_pack_consistency` 三支 rc=0。AAOI 實跑:`revenue_yoy_pct` 51.4→86.42、`gross_margin_pct` 接上 28.92、prewarm 快取命中 1 FMP call ~1s、無效 ticker 走 fail-soft 不中止。

## 🟢 Session Note (v4.105.1) — 預算閘不能把「永遠不會被消耗的需求」算進未來需求

- **現象**:使用者發現 `/break-news.html` 最新辯論停在 2026-08-04 23:56,已 2+ 天靜默無新辯論。`dashboard_server.py` 的 poll/debate 兩條 daemon 執行緒都活著、health check 200、`last_status` 全程顯示 `ok`——沒有任何錯誤訊號可查。
- **根因**:`poller._auto_budget_limit()` 把 `_pending_backlog_count()`(無條件數所有 `pending_debate` 狀態項)乘 `EST_CALLS_PER_DEBATE` 當「未來呼叫需求」去扣減可用額度。但 `debater.scan_pending()` 只吃 `age <= PENDING_MAX_AGE_HOURS`(2h)內的項目——超齡項目永遠留在 `pending_debate` 等人工 triage,根本不會被自動辯論消耗。backlog 累積到 43 筆(最舊回溯到 2026-05-27,全部早已 stale)後,`43*2=86` 恆大於當下 headroom,`model_debate_capacity` 卡死在 0 → 新 admission 恆 0 → backlog 只增不減 → 自我鎖死,永遠不會自然恢復。
- **修法**:`_pending_backlog_count()` 改用與 `debater.py` 相同的 `PENDING_MAX_AGE_HOURS` 判準(同一個 env var,新增同名常數保持同步),只數「debater 實際還會處理」的新鮮 backlog。修前 `43`(`model_debate_capacity=0`),修後 `0`(`model_debate_capacity=32`)。
- **紀律備忘**:兩個獨立的「stale 判準」(一個決定要不要處理、一個決定要不要算進預算)只要不同源,就可能互相打架且互相看不見對方——這類 silent deadlock 不會出現在任何 error log,只能靠「預期行為 vs 實際數字」的落差抓到。43 筆歷史 stale backlog 本身沒清,留給使用者透過既有的 `list_stale_pending()` 手動 triage。
- **驗收**:`tests/test_break_news_v4.py` 3 passed(1 個既有無關失敗,stash 前後行為一致,非本次改動所致);修前後 `_pending_backlog_count()` / `_auto_budget_limit()` 手動對照數字。

## 🟢 Session Note (v4.105.0) — tab 是縫合痕,不是資訊架構

- **緣起**:使用者問「為什麼盤中要分兩個 tab」。盤點確認:mood 面板先出、eval hub 後出,tab 是合併時的縫合痕。實害三條:警報/擊殺橫幅鎖在 mood tab(停在策略 tab 看不到)、盤中分數與三大 ETF 兩處各顯示一次、ideas 表(10 分 lane)與 spike 卡(60 秒 lane)同源不同步會互相矛盾。
- **修法**:單頁重排「決策→環境→個股→策略→板塊」;重複顯示各留較深的一份(ETF 深度卡>stat 格);ideas 只留熱圖領漲;族群統計升級密集卡(名/均幅/N 檔·上漲%/領漲 chips)。`#mood` 錨點保留讓 redirect 殼不斷鏈。
- **紀律備忘**:「連 N 窗」因 history API 無族群層資料而略過——前端需求不做穿透後端的擅自擴充,列 TODO 由使用者決定。
- **驗收**:fresh-context 逐行對帳 git diff(433+138 行),「搬丟的東西=0」;id 交叉核對(驗收者自寫腳本)44/44 存在;雙 JS node --check rc=0;4.104.1 推播三事件源確認完好。

## 🟢 Session Note (v4.104.0) — 反轉訊號的門檻要長在偵測層,不是顯示層

- **根因**:`detect_reversal` 3 根 1 分 K 內任一 KDJ/MACD 交叉就報「反轉」,無振幅門檻;前端雖有三道閘(區間需 spike 確認/逆勢不顯示/推播去重)但卡片狀態行照樣翻面。修在偵測層:雙確認 + σ 位移(1.5σ,退 0.3%)+ 翻面冷卻(10 分內反向需 zone 或 2.5σ)+ 開盤 15 分加嚴。同批即時 bars 誤報 9/14 檔 → 0。
- **設計選擇**:冷卻靠讀前輪 `intraday_spikes.json` 實現有狀態,前檔缺/壞/跨日退無狀態;所有時間比較用 bar 時間戳不用 wall clock(可測性);被降級的交叉仍在 `build_signal_flow` 訊號流,資訊不丟失。
- **駁回一條盤點發現**:「IEX 量能低估 → VOL_MULT 確認結構性弱」不成立——`vol_mult` 是同 feed 內「本分鐘 vs 前 15 分均量」的比值,低估在分子分母同時出現、大致抵消。子代理的推論性結論採用前要自己重推導(已記 LESSONS)。
- **未做(已入 TODO)**:spikes 無收盤快照、daily_health 不監控 spikes/eval;跨資產環境層 + 事件時間軸 + 說故事層(A–D)是下一輪主菜。盤中檢討全文結論:反轉降噪(本次)→ narrate 餵 spikes/kill_triggers(小改)→ 跨資產 ring + 事件日誌 → 鏈接器 + 敘事。
- **驗收**:test_intraday_spikes(新增 13 組)+ test_intraday 皆 rc=0;fresh-context 驗收 8/8 PASS,位移基準(交叉完成前一根 close)以獨立腳本實測吻合。
- **連動修正(.1)**:偵測層變嚴後,推播唯一事件源(反轉 alert)近乎歸零 → 前端推播擴充為三事件源(合格反轉★/急拉擊殺/高強度 spike),並移除 `isDirectionalAlert` 的區間二次過濾——閘門收緊後,下游為舊噪音加的補丁要跟著拆,否則合格訊號被雙重攔截。

## 🟢 Session Note (v4.100.1) — 抓取只抓新的,不等於下游只看新的

- **缺口**:`since_id` 保證只「抓」新貼文,但 append-only log 上沒有任何東西標記哪幾筆分析過。下游 LLM 階段若直接讀 log,會每次重讀整份 —— 付費試點會付錢重讀同一批推文。
- **修法**:byte offset cursor(`scripts/x_kol/pending.py`)。log 嚴格 append-only,offset 就是精確游標,往後讀必然是新的。不在記錄加旗標(要改寫 append-only 檔)、不留無上限 seen-id 集合。
- **崩潰語意選 at-least-once**:`read_pending()` 不移動游標,`commit()` 只在分析成功後呼叫。中途崩潰會重送而非靜默丟失 —— 探索 log 該往「重複」而不是「漏掉」的方向失敗。半行(writer 正在 append)不送出。
- **頻率不是瓶頸**(查證後別再重算):`/2/users/:id/tweets` = 10,000 req/15min per app、900 per user。20 帳號每 5 分鐘一輪只用 60 req/15min。**成本與掃描頻率無關,只跟 KOL 實際發文量有關**,所以掃密一點不會比較貴。
- **待實測驗證**:「0 則回傳 = $0」是依官方「按回傳資源計費」推得,尚未用真 key 對過 X 帳單。第一次 live sweep 後要拿 `--status` 的花費對 X billing dashboard。
- **驗收**:20 支 hermetic 測試 rc=0,含 4 週期端到端(冷啟 2 → 閒置 0 → 新增 1 → 閒置 0,log 3 筆、0 筆重分析)。
