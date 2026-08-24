# Session Notes 歸檔 v4.129.1 → v4.131.8（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v4.131.8) — 我昨天加的 log 是空的；一個 daemon 要能被看見才算裝好

- **上一輪自己種的坑**：V4.131.7 加了 `>>"$WIND_LOG"` 卻沒加 `-u`。使用者 18:03 重開、18:04 掃完一輪，log 還是 **0 bytes**。Python 的 stdout **導到檔案時是 block buffering（4-8KB）**，互動終端機才是 line buffering；一輪只印三四行，等於給了一個要好幾小時才吐第一個字的 log。**我加了一個觀測手段，卻沒驗證它觀測得到東西** —— 加 log / metric / status 欄位之後要當成功能去驗，不是寫完就算。
- **重現而非推論**：兩個並行程序，無 `-u` 2 秒後 0 bytes、有 `-u` 7 bytes，程序結束才一起吐。症狀（log 空的）本來也可以解釋成「daemon 沒印東西」或「重導向寫錯地方」，實測才排除掉。
- **順手修掉一條實務上走不到的路徑**：resident loop 的 `time.sleep(interval)` 在 `try` 外面，而 `except KeyboardInterrupt` 只包 `tick()`。迴圈每 3600 秒有 **3599 秒待在 sleep 裡**，Ctrl-C 幾乎必然落在那 —— 所以 `[wind] stopped` 那條分支寫了等於沒寫，daemon 一律死在 traceback。**「錯誤處理寫在哪」要對著時間分布看，不是對著程式碼行數看。**
- **`os.kill(pid, 0)` 不足以判定「那隻 daemon 還在」**：PID 會被回收，死掉的心跳會借屍還魂成繼承該號碼的無關程序，頁面就會替陌生人跑倒數。加驗 `ps -p PID -o command=` 含 `wind/dispatch.py`。**測試就拿 pytest 自己的 PID 當樣本** —— 保證活著、保證不是 dispatcher，正是要防的那個混淆；再用實際在跑的 77046 對照確認正例會回 True（不是靠負例全過就宣稱有效）。
- **「沒心跳」不等於「沒 daemon」**：舊版起的那隻仍在花每日 8 次額度。若報成「已停止」，使用者會再開第二隻，兩隻各自吃上限。所以無心跳時 `pgrep` 補一刀，頁面顯示「運行中(無心跳)」並在 tooltip 說明要重開才有倒數。**狀態面板最貴的錯誤不是漏顯示，是顯示成相反的那一種。**
- **測試第一次跑就抓到自己的環境相依**：`test_daemon_status_is_none_when_no_heartbeat...` 斷言 None，但這台機器正好有 daemon 在跑 → 紅。已改成 stub 掉 pgrep。**一個「在我機器上綠」的測試，比沒有測試更難察覺。**
- **順帶查清楚使用者問的第一件事**：風向與 X KOL **都沒接 broker**，`scripts/x_kol/` 與 `scripts/wind/` 對 `model_router`/`broker_gate` 零命中。X KOL 直接打 X API v2、風向 subprocess 叫 last30days（引擎用自己那把 key）。**兩者花費都不會出現在側欄 LLM 面板上**，只能 `budget.py --status`。（此為 v4.131.8 當時狀態；Wind reasoning 已於 v4.131.9 改走 broker。）

## 🟢 Session Note (v4.131.7) — 風向排程綁 open_dashboard.sh；順手驗掉 v4.131.3 留的那條「未做」

- **v4.131.3 的尾巴收了**：使用者自己重啟 dashboard server 後，`/api/x-kol/heat` 由 `prices_pending: true / prices=0` 收斂成 `false / 25 檔有價`。**驗的是 in-process 那條路徑，不是 out-of-process 重跑一次**——後者早就通了（`fetch_price_context(['AAOI','NVDA','AMD'])` 直接有值），它證明的是套件裝好了，不是那個長命 process 吃到了。長命 process 的 import 停在啟動那天，這是 `restart_dashboard.sh` 整支存在的理由。
- **驗證要等背景執行緒**：第一次打 `/api/x-kol/heat` 回 `prices_pending: true, prices=0`，看起來跟壞掉一模一樣。價格 enrich 刻意丟到背景（22 檔 × ~3 FMP calls 會卡在共用的 220/min window 後面），**請求本身永遠只回快取**。約一分鐘後才收斂。**「第一次打是空的」在這個端點是設計，不是症狀。**
- **排程位置是使用者選的，取捨明說**：三選一（launchd / `open_dashboard.sh` / 維持手動）選了綁 `open_dashboard.sh`。代價寫進 CHANGELOG 與 OPS_COMMANDS：daemon **啟動即跑第一輪**，所以開 dashboard = 花一次額度；關終端機 = 停止掃描。**這種「順手加個背景 daemon」的改動會安靜地把花錢跟開頁面綁在一起，值得在文件裡講白，而不是讓半年後的人自己從 shell 讀出來。**
- **`trap` 用單引號不是雙引號**：原本 `trap "kill $SERVER_PID ..."` 在定義時展開，加了第二個 PID 後若 `WIND_PID` 為空會展成 `kill 123 `（無害但脆）。改單引號延後到觸發時展開。
- **防重複用 `pgrep` 而非 PID 檔**：孤兒 daemon 的來源是關終端機／`kill -9`，那正是 PID 檔不會被清掉的情境。兩隻同時跑會各自吃 `budget.py` 的每日 8 次上限——**上限是共用的，執行個體不是。**
- **殘留掃描抓到一處**：`docs/wind_evaluation_criteria.md:76` 的「不及格就砍掉派工器（`dispatch.py` 與排程）」原本沒有「排程」的具體位置，現在補上指向 `open_dashboard.sh` 的 `WIND_DISPATCH` 區塊。**判準寫在資料之前是對的，但它指涉的東西後來才長出來——這種指標會在最需要它的那天失效。**

## 🟢 Session Note (v4.131.6) — 兩個字元讓整條 daily_update 掛掉；同一次 Python 升級的第二顆地雷

- **`daily_update.sh exited rc=1`，而且是秒掛**。第一直覺是鎖（那症狀最像），但讀 `acquire_run_lock()` 發現它會 `kill -0` 判斷 stale、而且真被鎖住是 **exit 75 不是 1**，直接排除。**排除一個假設要看程式碼，不是看症狀像不像。**
- **成因在 step log 裡，不在 UI**：盤前 chain 只顯示 `exited rc=1`。真正的話在 `$TMPDIR/daily_update_<date>_<pid>_3_market_top.log`：`ValueError: badly formed help string`。**Python 3.14 把 argparse 的 help 驗證從渲染時移到 `add_argument()` 時**，所以 `help="% S&P 500 above 50DMA"` 這種裸 `%` 從「跑 `--help` 才炸」變成「建 parser 就炸」——CLI 一啟動即死。Phase 1 是 fatal，整支中止。**兩個字元。**
- **跟 v4.131.3 是同一次 Homebrew 升級的兩顆地雷，但性質不同**：那顆是「套件沒跟過去」，補裝就好；這顆是「語言語意變了」，程式碼本身要改。**升級後只驗「import 得到嗎」是不夠的**，行為變更不會在 import 層現形。
- **這 bug 藏在沒人跑的 `--help` 路徑**，所以升級前後任何測試都不會變色。跟本輪另外兩個同族——`Claude` 的查詢樣板（只有 ticker 樣本時隱形）、preflight 的 `space-y-3`（只有一個子元素時隱形）。**三個都是「改動當下無症狀，特定形狀的輸入才暴露」。**
- **防線刻意走 AST 而非 import**：`tests/test_argparse_help_strings.py` 掃全 repo 367 個 help 常數。import 每支 CLI 會執行 module 層程式碼、需要所有第三方相依到齊，比它要守的那一類 bug 重得多也脆得多。第二條測試**把 3.14 的實際行為釘住**，未來 Python 若不再拒絕裸 `%`，它會失敗並說明「這道掃描現在比 runtime 嚴」——而不是留一條沒人知道為何存在的規則。
- **測試的壞字串 fixture 用執行期組字串**（`"%" + " of ..."`）而非字面值，這樣掃描不必排除自己所在的檔案。**路徑排除正是一道 guard 悄悄停止覆蓋鄰近檔案的方式。**

## 🟢 Session Note (v4.131.3) — 頁面說 FMP 沒有 NVDA 的價格；FMP 好得很，是這台機器沒裝 requests

- **使用者回報「AAOI 怎麼會撈不到值，你是搜成 `$AAOI` 嗎」**。猜測合理（cashtag 沒去掉 `$` 是這類 bug 的常見成因），但方向被錯誤訊息帶偏了——真正的線索是**整份清單連 NVDA / AMZN / GOOGL / TSM 都在裡面**。一個「找不到資料」的清單如果**連最不可能缺的標的都在**，那就不是資料問題，是查詢從沒發生。
- **根因**：Homebrew 把預設 `python3` 換成 3.14.7，user-site 全空。`fetch_price_context()` 的 `try: from scripts._shared import fmp_pool / except Exception: return {}` 把 ImportError 吞掉，於是每一支都不在 `prices` 裡，`mark_unanalyzable()` 一律標「no price series in FMP」。**FMP 從頭到尾沒被呼叫過。**
- **破口比回報的大得多**：dashboard server、`daily_update.sh`、`premarket_cron.sh` 全部走裸 `python3`，所以整條 pipeline 都在 import 層斷了。物證是 `Dashboard/nexus_graph.json` 與 `market_mood.json` 的 mtime 停在 8/14 20:33。**使用者以為在報一個頁面 bug，實際上是兩天沒跑的 pipeline 從這個角落露出來。**
- **為什麼藏得住**：identity 解析看起來還在動（頁面照樣印 `NVDA.NE (NEO)`、`AMZN.L (LSE)`），讓人以為 FMP 通。那其實是 `config/x_kol_symbol_identity.json` 的永久快取，8/14 22:59 環境還沒斷時寫的。**一個子系統「部分還會動」比全滅更難診斷**——全滅會有人立刻發現。
- **修法分兩半，程式碼那半才是長期價值**：套件補裝是一次性的；`price_backend_status()` 讓「FMP 說沒有」與「沒問到 FMP」不再共用一句話，是下次再斷時能少走兩小時冤枉路的東西。**錯誤訊息指向錯的子系統，代價是讀的人去 debug 錯的東西。**
- **測試為什麼沒擋住**：`tests/test_x_kol_api.py` 用 monkeypatch 注入假 prices，**刻意繞過真實 import**，所以環境斷掉時 37 個測試照樣全綠。已在 OPS_COMMANDS §7 補上這條與環境健檢指令。同理，本輪風向模組一路綠燈是因為它純 stdlib——**測試綠不等於環境健康**。
- **未做**：dashboard server 由使用者自己重啟（`scripts/restart_dashboard.sh`），沿用 v4.130.2 的做法，沒動他的 process。

## 🟢 Session Note (v4.131.0) — 風向：排序指標第一版是錯的，用真資料跑一次才看得出來

- **接一個外部 skill 之前，先讀它的執行紀錄而不是它的文件**。last30days 的 AAOI 報告 40% 是雜訊，但根因不在工具：`~/.config/last30days/last-report.json` 的 `provider_runtime` 寫著 `reasoning_provider: "local"` —— **一把 reasoning key 都沒有，整個 LLM 層沒開**，planner 退化成 deterministic（把財經查詢分類成 `intent=opinion` / `cluster_mode=debate`），rerank 全走 fallback（獎勵第一手作者身分，於是 KOL 的健身閒聊排進前 25）。這份 report cache 每次執行都會寫，是評估任何外部研究工具最便宜的物證。**兩把 key 至今未補，這是接線完成但尚未真正可用的狀態。**
- **先找 repo 裡已經有的那一半**。使用者要的「收集熱門關鍵字 → 優先佇列 → 取最高者分析 → 分析後移除」，關鍵字抽取已存在（Break News 的 `summary.merged_entities` 是辯論產出的結構化實體），容器也已存在八成（`scripts/x_kol/heat.py` 有衰減計分 + `DECISIONS` 佇列 + 原子寫入 + 代號身分閘）。真正要寫的只有第二個生產者、關鍵字鍵空間、自動派工、頁面。**「這要做什麼」問完之後，接著要問的是「這裡面有多少已經在了」。**
- **排序指標第一版錯了，而且只有用真資料跑才會發現**。用絕對聲量排，14 天 Break News 回的是 NVDA / AI capex / SPY / AMZN / MSFT / QQQ —— 那量到的是**覆蓋量**不是風向，mega-cap 每天每篇宏觀文都被提到，永遠贏，派工器會每小時去掃 NVDA。改成 `surprise`（快慢兩條衰減各自還原成每日速率後相除）後，頂端變成 RCAT / UMAC / AVAV / KTOS / ONDS + FPV Drones / NDAA Compliance / counter-UAS 這個連貫族群，而第一次實跑撈到了成因：Trump 對進口無人機課最高 100% 關稅。**單元測試不會抓到這個 —— 它不是壞掉，是量錯東西。**
- **修正一個偏誤時，順手檢查有沒有製造反向偏誤**。改用 surprise 之後榜首立刻變成 IYR / JEPI / QYLD / XYLD，全部 `mentions: 1` —— 同一篇 ETF 清單文提一次，對近乎零的基線就是最大加速度。所以 `min_mentions=3` 的佐證閘是必需的，不是防禦性寫法。
- **「分析後移除」是使用者的原話，但直接照做會漏財**：熱門詞下一小時就重新累積、再次被選中、重複付費。改成 `cooldown_until`，且只能被「分數較掃描當時 +50%」打破 —— 重新越過 surface 門檻不算，那是上次付錢時就已經在的狀態。
- **紀律沒被繞過**：`TODO.md:440` 明訂社群訊號未過領先性驗證不得接進 mood 面板，所以 `docs/wind_evaluation_criteria.md` 在**任何資料累積之前**寫成並鎖死判準（含最可能砍掉這件事的第三項：`median(fwd) ≥ 0.4 × median(pre)`，直接測 heat.py docstring 自己記載的「社群訊號對個股同步或落後」）。派工器自動跑的只有唯讀社群掃描，`分析 [TICKER]` 的人工閘完全不動。`grep -rn "wind_logs\|wind_terms" investment/` 為 0。
- **第三個真實案例才暴露的洞（v4.131.1）**：前兩次掃的 RCAT / UMAC 都是 ticker，`$RCAT stock news...` 的樣板剛好沒問題。使用者看到佇列第三名是 `Claude` 時問「這個關鍵字你要怎麼打」，跑出來是 `Claude stocks investor discussion` —— **在搜尋一支不存在的股票**。ticker 會自我錨定、主題不會，這個差別在只有 ticker 的樣本裡是隱形的。修法是用同框代號錨定（`Claude $AMZN $GOOGL $MSFT`，那三篇本來就是 Anthropic 營收 + IPO 的 read-through）。**這類 bug 不是 code review 找得到的，要等不同形狀的真實資料流過去才會現形——所以「跑一次真的」跟「測試綠」是兩件事。**
- **未親眼確認 → 已確認**：使用者開了頁面截圖回來，版面正常（L435 那個老問題這次沒重演）。`related_tickers` 也順手上了頁面——主題→代號對照本身就是三個用途裡「上下游供應鏈線索」要的東西。

## 🟢 Session Note (v4.130.3) — 根目錄清倉：先 grep 引用再動，不是看檔名猜

- **使用者要求**：掃根目錄、把檔案歸位，**動之前**先確認程式有沒有引用該路徑。這句話本身就是驗收標準——不是「看起來像垃圾就搬」，是每個候選都要交叉確認過 code/cron/launchd 零引用才動手。
- **判斷孤兒檔的方法**：不是只看檔名像不像 debug 殘留，是三條線索交叉——(1) 全 repo grep 檔名找不到任何 `.py`/`.sh`/plist 引用，(2) `git log -1` 看最後修改是哪次 commit（10 個 `.out/.json` 全是同一次 `chore: snapshot` 帶進來的，非刻意 commit），(3) 找不找得到「現在的替代品」——`breadth/burry/df/fc/fred/ftd/mtop/rm/sentiment/tr` 這批舊 flat-script debug capture，逐一對得上 `skills/*/cache/` 或 `sector/*_cache/` 底下功能對應的現行 skill，證實是重構前遺留、非現役。
- **唯一一個有真實引用的檔案要單獨處理**：`fred.json` 被 `skills/valuation-modeler/scripts/fmp_client.py:101` 列為 risk-free rate 的 fallback 候選路徑。沒有因為「大部分同類檔案都是死的」就連坐歸檔——另外查了 primary 路徑 `skills/fred-macro/cache/fred_latest.json` 確認存在且當天更新，fallback 實務不會被走到，才判定歸檔風險可接受並照舊處理。**批次處理時，混在裡面的唯一例外要單獨驗證，不能被批次結論蓋過。**
- **`reference/` 是整個被 `.gitignore` 排除的目錄**：`FMP_MCP_TOOLS_中文參考_v5_03.md` 依現有文件（`sector/BACKLOG.md`、CHANGELOG）該搬去那裡，但搬過去等於讓一份目前 tracked 的檔案變成 untracked。這種「搬移會改變版控狀態」的情況先攤給使用者選（搬 reference/ / 搬 archive/root_stray / 刪除），不要自己選一個看似「合規」的答案就動手——使用者選了刪除。
- **`.cache_bridge/` 47 個檔案卡在 git tracking 但目錄已被 `.gitignore` 排除**：這不是「檔案放錯位置」，是「規則加了但沒回頭套用到既有 tracked 檔案」的另一種殘留，`git rm -r --cached` 才能解，檔案本體留在硬碟不動。跟本次歸檔任務性質不同（不是搬家，是補做 gitignore 該做的事），順便一起做掉。
- **驗收**：三處版本同步（`SYNC OK: 4.130.3`）；根目錄現在跟 `README.md` §專案結構記載的清單完全對得上，多一個不少一個。

## 🟢 Session Note (v4.130.2) — 面板說 claude 在冷卻，ledger 說它跑完了四次工；往回查是方案降級當天空燒八小時

- **使用者的診斷方向對、機制猜錯，兩者都要說清楚**：回報是「方案從 Max 5× 改 Pro，broker 還死守三個 model，把 claude 變成保留區」。查下去：**沒有任何「保留 N 家 provider」的邏輯**（兩個 repo grep `quorum` / `min_providers` 皆零命中；`ACTIVE_PROVIDERS` 是 3-tuple 但那只是「哪幾家可路由」的清單；失敗列的 `model` 欄位全是 `claude`，沒被塞舊方案的 model 名）。但「broker 對 claude 的認知沒跟上方案變更」這個直覺是對的，而且比畫面上看到的嚴重得多。
- **先證明路由沒壞，再談顯示壞了**：`lqb history` 顯示 claude 今天 00:19 / 02:19 / 04:20 / 06:21 各跑完一次 brief，`reserve_only=false`，三條 route 都還是候選。**面板與 ledger 直接矛盾時，先問哪一邊有獨立物證**——execution 列是物證，徽章不是。
- **真正的損害在前一天**（翻 `broker.sqlite3` 的 `quota_snapshots` + `executions` 才看得到）：16:37 最後一張 Max 形狀 snapshot 帶 `weekly.fable 45%`（Pro 沒這個 per-model 週池）；16:42 方案切換，`weekly.fable` 消失、剩下兩個 bucket **全部讀成 0.0% used / 100% remaining**；16:43→23:58 claude **每一次** execution 都 `error_class=quota`，而同一段時間 **140 張連續 snapshot 用 `confidence: observed` 宣稱 100% 空著**。面板畫全綠、broker 宣稱滿手額度、底下每通呼叫被擋——這是 20% hard reserve 想防的事情的**完全相反面**。
- **為什麼會撞 24 次而不是停下來**：`_cooldown_deadline_locked()` 的階梯是 `resets_at` → `refresh_in_seconds` → 900 秒預設，而 **claude 兩個都不給**，只給 `"3:40pm(Asia/Taipei)"` 這種字串。所以每次都拿 900 秒，等於每 20 分鐘再撞一次牆。已補上 `reset_label` 這一階（Python 版解析，含時區與「落在過去就算下一次」；實測那天的 label 會給出 +2.68h 而不是 +15m）。
- **徽章為什麼卡住六小時**：cooldown 到期後**沒有任何東西會抹掉那個 deadline**——`clear_provider_cooldown()` 在此之前只有 `lqb cooldown clear` 一個呼叫點。路由層走 `in_cooldown(now)` 所以正常，回報層原封轉送所以說謊。**同一個欄位、兩種讀法，這就是 V4.129.0 那條「一個外部約束只有一個執行點」的原則被違反的樣子。**
- **修在哪一層是有講究的**：`broker_gate.py:586` 的 pass-through **刻意不動**（`tests/test_broker_gate.py` 明文把它寫成刻意行為；在 gate 層長第二套過期解讀正是 V4.129.0 論證要避免的）。權威判斷放 broker（`service.py` 一處改完，`lqb status` / `cooldown show` / web UI 三個消費端自動跟著對），面板那條 `Date.parse(...) > Date.now()` 是**重複防線**：daemon 可能跑舊建置，而把一家還能用的 provider 畫暗是這個面板能犯的最嚴重的錯，所以解析不出來一律當「不在冷卻」。
- **append-only 擋下了第一版**：想把矛盾的 snapshot 事後 `UPDATE confidence` → `sqlite3.IntegrityError: quota_snapshots is append-only`。改成**入庫前決定**（`model_copy(update=...)`），反而更對：一張抵達時就已被推翻的讀數，本來就不該以 `observed` 存進去。判準刻意不是數值本身——真的剛重置的窗口長得一模一樣——而是**矛盾**。
- **測試踩到凍結時間的坑**：`lqb cooldown show` 改成跟 now 比之後，`test_cooldown_show_then_clear_round_trip` 紅了——它用套件的凍結 `NOW`（2026-08-07）設 deadline。第一次只把 `until` 改成牆鐘還是紅，因為 `_bound_cooldown` 的天花板是 `now + 7d`，**`now` 也得一起動**。舊測試會過只是因為舊程式碼根本沒比時間。
- **驗收**：broker `pytest` **1053 passed** + `ruff check` + `ruff format --check` + `mypy src` 全綠（新增 7 個 cooldown 案例 + 2 個 status 案例）；AIC `test_broker_gate.py` / `test_protocol_model_routing.py` / `test_protocol_cooldown.py` / `test_model_router_window.py` 全 rc=0；`node --check Dashboard/utils.js`。**新增的 UI 斷言用種回 bug 驗過會紅**，清 `__pycache__` 後重跑確認還原到綠。daemon 已 `launchctl kickstart` 重啟，`lqb status` 的 `[cooldown until …]` 消失、`lqb cooldown show` 回「no provider is on cooldown」。
- **未做**：Dashboard server 由使用者自己重啟（`scripts/restart_dashboard.sh`，我沒動他的 process）。該 script 的驗證段已對線上 API 實測，正確判出目前這支 8/12 啟動的舊 process 三家都回 `headline_bucket: null`。
- **模型帳本**：本輪 dev 0 inference turn。

## 🟢 Session Note (v4.130.1) — 一張寫死的黑卡，牽出 style.css 一直沒配平的大括號

- **回報的 bug**：短期雷達熱力圖的個股 tooltip 在淺色模式是黑底。原因單純 —— `#radar-heatmap-tooltip` 的背景與邊框寫死在 `radar.html` 的 inline style，內容全是 `text-zinc-*` / `text-white`。同一頁的 `#radar-term-tooltip` 早就走 token，這張只是漏了。**顏色寫進 markup 就跟不了主題**，樣式移進 style.css 才是修法，不是把 inline 值改成另一個顏色。
- **截圖裡還有第二個深色 tooltip，但那個不是我們的**：`card.title = ...`（page-radar.js:1067）是瀏覽器原生 tooltip，深色來自 Chrome/OS，CSS 碰不到。先確認這件事才不會去改一個不存在的樣式。
- **殘留掃描抓到同型的 3 處**（`text-zinc-200` 值、`hover:text-zinc-300`），同頁同一種病：寫死的近白色文字落在主題卡片上。順手一起修，因為它們是同一次 grep 的產物。
- **驗證用的 sanity check 反而抓到主菜**：我用「大括號配對」當 CSS 改動的粗檢，結果 1134 vs 1135。**先確認是不是自己弄的** —— `git show HEAD:` 比對，HEAD 本來就 −1，不是本輪造成。追下去是 `[data-theme="light"] #history-drill-rail .glass-card` 的 `border` 宣告被切離規則、以孤兒形式留在第 285 行頂層，parser 連同一個裸 `}` 一起丟棄，**淺色模式那批卡片因此繼承深色規則的白邊 = 沒有邊框**。用 `git log -S` 找回原始歸屬（`b955a5c`）才敢把它放回去，而不是猜一個選擇器。
- **瀏覽器驗證做不成，據實說**：Chrome 擴充功能沒連上，無法實際 hover 截圖。退而求其次驗到「伺服器實際送出的三個檔都含新規則、JS 類名與 CSS 兩邊對齊（rht-label 11/1、rht-value 5/1、rht-divider 1/1）」，視覺結果未經我親眼確認。

## 🟢 Session Note (v4.130.0) — UI 報「schema drift」，真正的死因在上一步；順手修了額度條看錯池

- **報錯的地方不是壞掉的地方**：使用者看到 `validator rc=1: schema drift (expected V2.3):; - FR`。validator 完全正常——今天根本沒產出 `2026-08-14_digest.json`，它退回抓 8/12 那份，於是報 freshness fail，而 UI 只截得到第一行。真正的 rc=1 在 `news/scan_logs/news_20260814_203225.log`：`finalize_digest.py` 吐 `n0376 Bull/Bear both have |impact|<=1`。**下次先看 scan_logs 的最後一個非 0 rc，不要從 validator 的訊息往回推。**
- **閘的實作比它的規範嚴格**：`news_protocol_v2.md` 寫「退回**該則**要求 re-analyze」，`finalize_digest.py:217` 寫成整批 `raise`。一則 Stage 1 誤晉級的廢新聞（Fed 對某銀行前員工的處分）作廢了一整份跑完的四 lane 辯論。改成該則降級 shallow，過半才整批紅。
- **codex 的行為是對的，不要因為結果難看就怪它**：它照閘門紀律停在 rc≠0、沒去改 debate 分數闖關。事實上分數區間（bull 1~5 / bear −5~−1）讓「這則沒料」只能寫成 ±1 —— **唯一能過閘的寫法就是灌水**，而灌水正是 prompt 明令禁止的。閘與編碼互相矛盾時，模型無論怎麼選都是錯的。
- **通用解被資料否決，這是本輪最該記的一次**：我第一版想用「內容零訊號就扣 1.5 分」取代關鍵字。模擬近 6 天 triage：8/12 會少 16 則、8/14 少 21 則，全是 Hormuz 封鎖／制裁／海上攻擊這類 wire 2.0 + geopolitical 2.0 + HIGH 0.5 = 4.5 剛好卡線、標題裡沒有數字的真新聞。**改用窄得多的 genre 規則（對個人的 enforcement 通知），近 8 天 triage + 4 天 raw 只命中 n0376。** 通用規則看起來比較「有原則」，但這裡的地板分本來就不是內容分。
- **額度條的 45% 是單一 model 的週池；使用者拍板改讀 5 小時窗口**：broker headline 取全窗口最小值 → `weekly.fable` 勝出。第一版我改成「排除 per-model 子池後取最小」，使用者先說要週用量、再更正為 5h，最後定案 = **固定讀 5h 窗口**（claude 叫 `session`、agy 叫 `<pool>.five_hour`）。取最小值真正的毛病不是選錯池，是**長條的意義會隨當天哪個窗口比較緊而改變**，三家之間也不可比。
- **面板與派工是兩個問題**：使用者明確說 broker 的 `min_remaining_percent` 沒問題 —— 派工本來就該看最緊的窗口。所以 `routable_pool` 保持 broker 原值不動，另開 `headline_bucket` 回答「面板讀哪個窗口」，`reserve_only` / `cooldown_until` 原樣傳遞，broker 不派的 provider 在面板上照樣是暗的。
- **「claude 為什麼沒有 5h 用量」的答案是標籤，不是資料**（使用者追問後去 broker 查的）：claude 有 5h 窗口，只是 Claude Code `/usage` 叫它 "Current session"、broker 鍵名 `session`（parser docstring 自稱 "the short window"），而 `five_hour` 這個名字在 broker 裡**只屬於 agy**（`gemini.five_hour` / `claude_gpt.five_hour`，後者是 agy 那包 Claude/GPT model 的池，與 claude provider 無關）。面板把它標成「本節」，跟 agy 的 `5h` 並排就像 claude 沒有這個讀數。**驗證方法值得記**：翻 `broker.sqlite3` 的 `quota_snapshots` 最近 400 筆，`session` 重置時間 9:40am → 2:40pm → 7:40pm → 12:40am，5 小時一跳 —— 這比讀 parser 註解更硬。順帶看到今早該窗口燒到 **91%** 而週池仍寬鬆，正是要看 5h 的理由。已把 `bucketLabel` 的 `session` 改標 `5h`。
- **兩個「不要無中生有」的邊界**：codex 只送一個 `primary`（週），沒有 5h 窗口 → 保留 broker 原數字並回 `headline_bucket: null`，tooltip 明寫「該家未回報 5h 窗口」，不把週數字當 5h 用。routable pool 內沒有 5h 窗口時也回 null，**不借別的池的窗口** —— 舊測試 `headline_from_broker` 正是在這裡把我的第一版擋下來的（agy 會被 `claude_gpt.five_hour` 的 12% 綁架，那就是 V4.129.0 修掉的同一個事故）。
- **驗收**：`pytest tests/news` **107 passed**（新增 3 個 finalizer 降級案例 + 5 個 stage1 genre 案例，含「機構級處分仍須晉級」反向斷言）；`tests/test_broker_gate.py` rc=0（新增 5 檢查、改寫 1 條舊契約，含「5h 勝過更緊的週池」「pool 內無 5h 不借別池」「codex 無 5h 不冒充」）；`node --check Dashboard/utils.js`；live `quota_snapshot()` 實測 claude 8%/session、gemini 4%/gemini.five_hour、codex 19%/null。三處種回 bug 全驗紅。
- **未做（使用者決定）**：8/14 的 digest 不補跑。`2026-08-14_debate.json` 完整躺在 news_logs，要補只需重跑 finalizer。
- **模型帳本**：本輪 dev 0 inference turn。

## 🟢 Session Note (v4.129.1) — X KOL 頁面的重新整理現在真的會抓一輪

- **修正**：右上角「重新整理」從純 GET 熱度重算改為 `POST /api/x-kol/collect`，由 server 執行一次 `scripts/x_kol/collect.py` 的增量 sweep，再重載熱度與價格。
- **安全**：collector 有 process-level lock，並行點擊回 409；錯誤回應不回傳可能含 request detail 的原始 exception。
- **邊界**：仍是探索層，只新增貼文到 shadow log，不會自動觸發投資分析；promote/reject 閘維持人工決定。
- **驗收**：新增 `_x_kol_collect_once` contract test 與 collect route 邊界測試；X KOL API/collector 契約測試共 **52 passed**，Python/JS 語法與版本同步檢查全綠。
