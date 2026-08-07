# INTEL COMMAND — Session Notes & System State

> **Last Updated**: 2026-08-07 (v4.108.0)
> **Role**: This file serves as the "Short-term Memory" and "Handoff Cache" for AI Agents. It contains market regime states, token optimization logs, and data integrity notes. **Task backlog has been moved to TODO.md; full version history to CHANGELOG.md.**

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

## 🟢 Session Note (v4.100.0) — 按回傳計費,就不能用樂觀的閘

- **實測結論(別重做一遍)**:免費 syndication 端點活著、回傳 X 已解析的 cashtag,但約 8 req 觸發 429、冷卻 ~183s;**@aleabitoreddit 只回 2 則且停在 2025-11**(內容在訂閱牆後),免費路徑拿不到目標帳號 → 才走付費 API。企業官方帳號(@nvidia)20 則 0 個 cashtag,選人要挑真的打 `$TICKER` 的散戶分析型帳號。
- **預算閘的形狀**:X 按**回傳資源數**計費,所以事前不知道要花多少。事後計數器擋不住任何東西(發現時錢已經花了),因此 `check()` 一律用**最壞情況**否決、`record()` 才記實際。$10 試點賭不起樂觀估計。
- **成本能成立全靠 `since_id`**:沒有新貼文就回 0 則、$0。X 的 24h 去重是官方自稱的 soft guarantee,**不可依賴**。
- **撞天花板是停止不是失敗**:sweep 遇 `BudgetExceeded` 就 break,已收資料留在 append-only log,state 水位照存。
- **未接線**:只寫 shadow JSONL,沒碰 intraday_mood。要不要接、怎麼加權,等有真資料再說。
- **待使用者提供**:KOL 名單(目前只有 Serenity 一人 enabled)、以及 `X_BEARER_TOKEN`。
- **驗收**:13 支 hermetic 測試 rc=0、dry-run 零花費、無 token 乾淨 rc=1、gitignore 覆蓋確認。

## 🟢 Session Note (v4.99.3) — 沒有資料邊就不該有失敗邊

- **原則**：phase 1 的 fail-fast 該綁「資料相依」而不是「同一個 phase」。sector 讀 daily 刷新的 breadth/FTD/market-top cache → daily 維持阻斷；sector 從不讀 digest → news 改為非阻斷，只記 `warnings`。
- **名單化**：`_PREMARKET_NONBLOCKING = {"news"}`，之後要加 item 進 phase 1 時，先問「sector 讀不讀它的產物」再決定放不放進這個 set。
- **不可靜默**：`done` 帶 warnings 時 UI 出黃色降級 toast；失敗那列本來就顯示 ❌。降級不等於成功。
- **8 天歷史日檔已刪**：4/18、5/16-5/19、5/31、6/03、6/05。刪前確認全部落在所有消費端時間窗外（bridge 最近 3 份 / nexus 30d / retail-pulse 72h / theme-detector windowed），且 `legacy_digest_backup/` 有備份、JSONL 可 re-project。
- **驗收**：premarket chain 4 tests（3 支新增，反向驗過會紅）、News 99 tests、py_compile、`node --check` 全過。

## 🟢 Session Note (v4.99.2) — per-run 的 cap 擋不住 union

- **現象**：盤前 chain 20:27 起跑，daily done、news error、sector 停在 `idle` 從未 enqueue。digest 其實跑完了（26 verdicts、20:33 落盤），死的是收尾 validator：`shallow over-cap: got 20, max 15`。
- **根因**：top-10 cap 只在 per-run 的 `build_digest_packet.py:77`，但 digest.json 現在是 event store 投影，`latest_by_event_id()` 依 `event_id` 去重、不依 run 去重。當天 3 次 digest run（08:25/08:47/20:33）各自從不同 triage 快照挑 top-10 → union 20 shallow。
- **修法**：cap 移到 `build_projection()`（`_cap_shallow()`，`SHALLOW_PROJECTION_CAP = 10`）。deep 不設限是刻意的——盤中 FLASH/REVIEW 累積是設計。只刪不重排、tie 以 slot 決勝，投影仍逐位元穩定。
- **鏈路教訓**：phase 1 是 fail-fast（`dashboard_server.py:1918-1921`），任一 item error 就 raise，phase 2 完全不執行。news 的 validator 失敗會連坐 sector。
- **未清的債**：4/18、5/16-5/19、5/31、6/03、6/05 這 8 天磁碟 digest 是 14-20 shallow（同一 bug，只是沒越 15 硬閘），現在與修正後的投影不一致；要不要 re-project 未決。
- **驗收**：News 99 tests（新增 2 支回歸，停用 cap 時皆紅）、2026-08-06 re-project 後 validator rc=0（10 shallow + 6 deep）、其餘 78 個歷史日期投影與磁碟仍逐位元一致。

## 🟢 Session Note (v4.99.1) — Projection mode 不能覆蓋事件 mode

- **真實 canary**：WDC FLASH 已成功 append 為 `news_a0ea342405161641`、pending、cache 未更新；失敗只發生在 post-run validator。
- **根因/修法**：同日 projection 頂層保留 DIGEST/PER_AGENT_BATCH，舊 validator 卻套到 INLINE FLASH；現改依每筆 `event_type`/`fanout_mode` 驗 review、cache 與 isolation。
- **驗收**：News 97 tests、相關 health/routing 3 tests、py_compile、真實 mixed projection validator 與 diff check 全過；未重跑 LLM。

## 🟢 Session Note (v4.99.0) — News 歷史只追加，日檔只是投影

- **單一事實來源**：DIGEST／FLASH／REVIEW 全部 append `news_events.jsonl`；daily digest 維持 Dashboard contract，但由 active event deterministic 重建。
- **審核語意**：FLASH 保存 pending record；REVIEW 以同一 stable event_id append superseding record，不再搜尋 headline 後覆寫整份 digest。
- **遷移/回復**：86 份 legacy digest、1,283 judgment 完成 migration；一次性 backup 可 rollback，重投影 hash 一致，migration replay 零新增。
- **Telemetry**：server 成功 DIGEST 自動記 Stage 2/BINARY/source/genre/token/time/cost；真實 canary 已回填 1/10，materiality 仍固定 4.5。
- **驗收**：News 96 tests、server routing 3 tests、py_compile、diff check、真實 migration replay、rollback/re-project 與 News validator 全過。

## 🟢 Session Note (v4.98.0) — 模型只做判斷，程式負責產物

- **責任收斂**：Stage 2 只產 four-lane compact judgment；finalizer 統一 score/verdict、digest/MD、validator 與 cache patch。
- **一致性**：finalizer/validator 共用 `arbiter_rules.py`；validator 重算權重。stable event ID 不依賴 triage 排名，phase0 ledger 阻止 replay 重複加總。
- **Token 目標**：Phase 3–4 約 6k → 1–2k LLM tokens；protocol 同步移除手寫 digest/Impact Card 指令。
- **驗收**：News 90 tests（含 real validator integration）、py_compile、routing contract、現有 digest validator、diff check 全過。

## 🟢 Session Note (v4.97.2) — credential failure 是整批狀態，不是 517 個 ticker failure

- **根因**：Heatmap 僅對 FMP 429 熱斷；401 走一般 HTTP error，20-worker fan-out 因而對 517 檔逐一輸出同一錯誤，並每個週期重演。
- **修法**：共用 transport 首次 401 後啟動 6h process-wide breaker，只印一行「檢查 key 並重啟」；期間所有 Heatmap FMP 消費端快速返回。
- **資料完整性**：零成功的 auth-failed quote batch 不更新 `last_update`、不改寫舊 snapshot，避免將「拒絕取數」假裝成新鮮的 `0/517`。
- **驗收**：Heatmap retry contract 含新 401 fixture 全過；Python compile、diff check 與版本同步通過。

## 🟢 Session Note (v4.97.1) — degraded 是可繼續的契約，不是失敗別名

- **根因**：`daily_update.sh` 已將 `rc=2` 定義為降級可用，但 Dashboard runner 仍將所有非零 rc 映射為 `error`，盤前鏈因而錯誤中止 Sector 與裁決面板刷新。
- **修法**：上層新增明確 exit-code mapping：`0=done`、`2=degraded`、其他非零 `=error`；modal 與全站 pill 用黃色警告顯示 degraded，狀態機照常前進。
- **驗收**：新增 `test_premarket_daily_outcome.py`，並跑 Dashboard 相關回歸、JS/Python 語法、diff check 與版本同步。

## 🟢 Session Note (v4.97.0) — 分歧強度不是二元事件，方向字數也不是重要性

- **BINARY 根因**：Bull 固定正分、Bear 固定負分，再以 max-min≥4 判 BINARY，讓 7/29–8/5 五份 digest 的 25 筆 deep 全部坍縮成 BINARY。V2.3 改成事件本身須 explicit pending + date；net score 只決定 directional bias。
- **Triage 根因**：`upgrade/strong/raise/surge` 同時兼任方向與晉級排序，三篇 Zacks 加兩篇升評文可占滿 8/6 top-5。新增 materiality/genre/source/event 維度後，回放改由實際財報、Fed/私人信貸與 Reuters 事件晉級；安靜日可少於 5。
- **Token 首批落地**：triage 保存 URL；compact packet 一次輸出 Stage 2 + shallow top-10 + slim macro/theme；bundle cap 5,000→3,000 chars，避免主 Agent 重讀三份全檔與搜尋已有 URL。
- **驗收**：News 83 tests passed、py_compile、schema FULL EXAMPLE parse、現有 digest validator rc=0、diff check rc=0。舊同日 artifact loose-compatible；新 strict run 必須明示 V2.3。

## 🟢 Session Note (v4.96.0) — daily_update 可靠性與 thematic 主瓶頸

- **成功語意改正**：Phase 2 與 final artifact 的失敗會聚合成 degraded `rc=2`，cron 不再把 silent SOFT fail 記成當日成功；health gate 新增本日、可解析、`_partial` 驗證。
- **執行治理**：跨 process lock 擋 cron／Dashboard／手動重複執行，trap 清理 lock、背景程序與本輪 temp logs；日常 Nexus 固定 Tier 1+2，Tier 3 LLM full backfill 移出 daily。
- **效能**：thematic enrichment 從直接 urllib + serial 改走中央 `fmp_pool` + 12-worker bounded concurrency；兩層輸出 atomic replace。最近基線 enrichment 216 tickers/518s，預期冷跑下限改由 220 RPM pool 主導，待下一次真實 daily log 驗證。
- **降噪**：headless 無 Finnhub key 時整批 proxy fallback，只提示一次。
- **驗收**：`bash -n`、4 支 Python `py_compile`、新增/既有 targeted pytest 6 passed、single-run lock probe rc=75、`git diff --check` 均通過；未為驗收重燒一次完整外部 API daily。

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
