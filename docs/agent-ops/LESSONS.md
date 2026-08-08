# 踩坑教訓（格式見 MAINTENANCE.md §4；>150 行時精簡）

## 2026-08-08 ｜共通項不能解釋差異；效能問題沒 profile 之前的因果都是猜的
- 情境：接手另一個 session 的交接文件查「開 Dashboard 系統卡頓」。該文件已把根因定調為「56 個 `setInterval` 缺 `document.hidden` 保護」，並排好 `pollEvery()` 收口 46 處的重構計畫。
- 坑：那份文件第 3 段自己寫著「每分鐘 166 次小 JSON 請求在算術上燒不掉一整顆核」——**它已經否證了自己第 2 段的主張，卻沒有察覺，仍照著被否證的假設規劃重構**。實際 profile 後：各頁 JS 執行只佔 0.4%–2.8% 一顆核，timer 完全不是元凶。真兇是 `decisions.html:35` 的 `transition: stroke-dashoffset 0.9s linear` 撞上每 1.0 秒寫一次的 `updateRefreshStatus`——每秒續一個 0.9 秒的不可合成 transition，頁面永遠不 idle（110 Paint/s、56 Commit/s）。照原計畫做完 46 處重構，這個 bug 一個字都不會被碰到。
- 修法：(a) 效能歸因**一律先量再修**，缺 Safari profiler 不等於量不到——`Chrome --headless=new --remote-debugging-port` + CDP，node 22 內建 `WebSocket` 直接講 protocol，不必裝 puppeteer；`Performance.getMetrics` 拆 Script/Layout/RecalcStyle，`Tracing` 數 Paint/Commit。(b) **鎖定元凶要找差異項，不是共通項**：56 個 timer 每頁都有，但 index 0.6 Paint/s、decisions 110 Paint/s——差 100 倍的東西不可能由共通項解釋。(c) 結案必須做 A/B（只關那一行 → 56 fps 掉到 1.1 fps）才算證明，不是「疑似相關」。(d) 掃永久動畫用 `document.getAnimations()`，**不要用 `getComputedStyle().animationIterationCount === 'infinite'`**——後者看不見 transition，而本案元凶正是 transition；三個頁面都掃到同一個隱形旋轉圖示，但只有一頁在燒。
- 已回寫規則？：否（本條是診斷紀律，非流程規則）。同批修復見 CHANGELOG v4.111.3；`intraday-eval.html` 的 `box-shadow` 動畫（241 Paint/s）已知未修，屬視覺設計決定。

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

## 2026-08-06 ｜檢查 env 名稱也要用 parser，不要用只涵蓋裸賦值的 regex
- 情境：review `daily_update.sh` 的 launchd 環境能力，只想列出 cron env 的變數名稱並遮罩值
- 坑：遮罩式只匹配行首 `KEY=...`，實檔使用 `export KEY=...`，導致工具輸出意外帶出本機 secret。即使檔案 git-ignored、目的只是讀名稱，輸出仍會進 session transcript
- 修法：任何 env inventory 一律只輸出 parser 取得的 key 名；shell 檔先移除可選 `export` 再解析，或以不回顯內容的檢查逐一測 key 是否存在。禁止先整檔讀出再靠顯示端 regex 遮罩；已曝光的 credential 立即輪替
- 已回寫規則？：否（本條保留可執行的診斷紀律；未記錄任何 key 值）

## 2026-08-06 ｜API 回 200 不代表區間資料完整，enrichment 前要先縮 universe
- 情境：修 sector prefetch 的 earnings calendar 360 秒 timeout；中央 limiter 已把流量壓在 220 RPM，仍跑不完
- 坑：未來 7 日 calendar 回 2,837 symbols，程式對每支逐一打 `/profile` 才篩 market cap；同時過去 30 日 calendar 回剛好 4,000 rows、HTTP 200，實際日期卻只覆蓋最後 8–9 天。前者是 filter-after-fetch 的 2,837-call fan-out，後者是無錯誤訊息的 response cap 截斷
- 修法：enrichment 前先用一次 bulk/screener snapshot 本機交集，禁止把「篩選所需 metadata」做成逐 symbol 請求；範圍 API 若筆數碰到已知 cap，必須切段、去重並在單日仍飽和時 fail closed，不能把 HTTP 200 當 completeness 證明
- 已回寫規則？：是（4.95.7：`sector/lib/earnings_calendar.py` 分段完整性；Step 3 改 cached company-screener join；`sector/scripts/README.md` 記錄契約）

## 2026-08-05 ｜中央 limiter 的上限只對納管流量成立
- 情境：Starter 方案 300 RPM、中央 pool 設 220 RPM，sector prefetch 仍在 valuation/smart-money 收到 429
- 坑：只檢查 `fmp_pool_window.json` 會錯判「不可能超量」；同一個 prefetch 還平行呼叫 `~/.claude` calendar scripts，其中 earnings calendar 用 16 threads 逐 symbol 直接 `requests.get(/stable/profile)`，完全不進中央 window。另：HTTP client 丟掉 429 body/Retry-After，使 RPM、bandwidth、權限限制看起來一樣
- 修法：排查共享配額時先列出整個 execution graph 的所有 HTTP 出口，不只檢查名義上的 shared client；所有 fan-out 必須先取得同一個 cross-process slot。429 保存去 query、去 key 的 endpoint/body/Retry-After artifact；401 這種整批 credential failure 必須在共用 transport 首次命中就熱斷並聚合 log，不得繼續逐檔 fan-out
- 已回寫規則？：是（4.95.5：phase_prefetch calendar 全改 repo-owned `fmp_pool` client；`fmp_pool.py` 新增安全診斷 artifact）

## 2026-08-03 ｜修 bug class 的那輪，要拿修法判準回頭掃自己新增的程式碼
- 情境：4.95.2 對 4.95.1（「韌性從檔案層下沉到欄位層」的 review 修正輪）做第二輪 review
- 坑：四個修正各自把守衛下沉了一層就停，同一 bug class 在再下一層原樣復發——`uncovered[]` 修到 key 層（`{"Utilities": null}` 仍讀成「查過了、乾淨」，da_pretrigger.py 舊 `_uncovered`）、擋了「版號缺失」放行「版號非字串」（sector_score_calculator.py 舊 L488，float 版號讓 `sorted()` TypeError 掛掉 --status）、修了 gate 的 `_canon_list` 沒修共用源頭 `_slim_fred`。測試全綠，因為回歸案例只釘到修正做到的那一層
- 修法：修 bug class 的 PR 收尾加一步——用修法那條判準（「不可用的最小單位是什麼」「這條規則覆蓋的對象還有誰」）重掃 PR 自己新增/修改的程式碼與測試 fixture；並用 revert 模擬驗證新測試在「往下一層的變體」上也會紅，而不只在原 bug 上會紅。另：恆 null 的合法欄位是 doc-vs-code 矛盾的藏身處（FTD `exposure_range` 讀錯 dict 恆 null 一直沒人發現），review 時對「永遠是 null 的欄位」要問一句是設計還是讀錯位置
- 已回寫規則？：否（與 4.90.4 Session Note 的判準同源；已在 CHANGELOG 4.95.2 / SESSION_NOTES 記錄，再犯則升格進 MAINTENANCE §2 收尾 checklist）

## 2026-08-02 ｜帶前置篩選的計數欄位，0 可能是「被篩掉」而不是「沒有」
- 情境：v4.79.0 給 calibration 加 `point_in_time_caveat_count`，統計有多少預測不是完全 out-of-sample
- 坑：欄位只數 `status == "comparable"` 的 row。真實語料跑出來是 **0**，看起來像「沒有任何 caveat」——實際有 19 筆帶 caveat 的 row 卡在 `actual_not_comparable_yet`，只是還沒成熟。因為今天 comparable 恰好是 0，這個欄位在最需要它示警的時候永遠顯示 0，測試也照樣全綠（fixture 裡 comparable 不是 0）
- 修法：任何「計數 / 比例」欄位若有前置篩選，落地前先問「這個 0 是真的沒有，還是被篩選條件擋掉」；把被擋掉的那一群也給一個欄位（本次拆成 `scored_with_` / `pending_with_`）。驗收不能只跑 fixture，要在真實語料上看一次數字並解釋每個 0
- 已回寫規則？：否（屬驗收通則，與 LESSONS 既有「只驗 happy path 等於沒驗」同源；若再犯則合併寫進 MAINTENANCE 收尾 checklist）

## 2026-08-02 ｜修引擎不重跑 snapshot，archive 最新一筆仍是壞資料
- 情境：review v4.78.0 forward-expectations 修正（5274299 cutoff + 77642f4 scope gate）
- 坑：`MU_20260801T230255Z.json` 生成於兩個 commit 之間（07:02，scope fix 07:04 才進），base_rate_lane 帶著被自動晉升的 -9% cohort median 與錯誤 note，成為 archive 最新 MU snapshot——任何讀 latest snapshot 的報表都會拿到 fix 前的數值。程式碼與測試全對，壞的是資料層
- 修法：引擎行為修正的收尾 checklist 加一步：受影響 ticker 重跑一次 snapshot（ledger 不可變，用新檔蓋 latest 而非刪舊檔）；review 引擎變更時，除了 diff 與測試，一定抽 archive 最新 snapshot 核對關鍵欄位是否已是 post-fix 行為
- 已回寫規則？：否（先記 LESSONS；若再犯考慮寫進 MAINTENANCE §2 收尾 checklist）

## 2026-08-02 ｜估值引擎驗收只驗 happy path，等於沒驗
- 情境：4.76.0 交付 MU structural-shift DCF + range-only peer fallback，驗收是「MU 跑出 $762.13、測試 rc=0、validator rc=0」，看起來很完整
- 坑：後續 review 找到 12 項問題，**全部**在 degraded / fallback 分支，happy path 一項都沒錯——因為 MU 剛好是「3 季已公布 + 有 next-quarter estimate + estimates 有 ebitAvg」的最順情境。實際踩到的：2 季 ticker 會拿已公布季度獲利除全年營收估計（`dcf.py` start EBIT margin）；缺年度估計時整條成長路徑直接套成長上限表 45/30/20/12/8（把「證據上界」當「預設值」）；confirmed shift 建不起來時靜默退回 legacy 而 legacy 對該股會算出負 terminal FCFF；資料缺失的 ticker 在非 `--json-only` 模式直接 TypeError 而不是 degraded
- 修法：引擎類交付的 DoD 加一條——**每個 early-return / fallback / except 分支都要有一條 regression test**，且測試 fixture 不能只有一個「資料齊全」版本。寫 fallback 時問一句「這個預設值是保守還是最寬鬆？」缺資料一律往保守 + 出聲（寫 reason 進 payload + warnings），不准往上界靠
- 已回寫規則？：是（`skills/valuation-modeler/SKILL.md` 新增「缺資料時的紀律（degraded path）」段；本條記通則，其他引擎同樣適用）

## 2026-07-03 ｜開處方前先確認「這件事實際是誰在做」
- 情境：實作「§11 verbatim 改 script 注入」backlog
- 坑：診斷時把 verbatim 風險定位在 ic-memo §11，動工前覆查才發現 ic-memo 的 §11 早就是 `compose.py` deterministic 渲染；真正由 LLM 手抄數字的是 protocol Step 4 的 Sonnet MD Formatter，且其 validator 只驗刻度格式不驗值
- 修法：任何「叫 X 改為 script 做」的處方，動工第一步先讀原始碼確認 X 目前的執行者到底是 LLM 還是 script（grep 該欄位在 protocol/scripts 兩邊的出現點），再定改動對象
- 已回寫規則？：是（DIAGNOSIS §三.1 已改為正確定位；本條記過程）

## 2026-07-03 ｜兩層 CLAUDE.md 會同時載入且會脫鉤
- 情境：治理文件總體檢
- 坑：父層 `/Users/kavi/Documents/CLAUDE.md` 是舊拷貝，與專案版一起被載入，內容停在 V4.13 → 每 session 浪費 ~14KB 且指令互相矛盾
- 修法：父層永遠只放指標；規則只寫專案 CLAUDE.md 一處
- 已回寫規則？：是（父層已改指標檔；MAINTENANCE.md §1「永遠不准」）

## 2026-07-03 ｜檔名帶版號的 protocol 換版時要清引用
- 情境：v4_8 歸檔
- 坑：16 個活文件（skills SKILL.md/README、sector/news README、docs/plan_short.md、兩個 .py docstring）仍指向 investment_protocol_v4_8，弱模型會照舊檔名去找；且第一輪 grep 漏了 plan_short.md 的 2 條（自以為「歷史文件」而排除，但它被 CLAUDE.md 指名為活文件）——排除清單要保守
- 修法：protocol 換版的 DoD 含 `grep -rn "舊檔名" --include="*.md" --include="*.py"` 清零（排除 archive/CHANGELOG/SESSION_NOTES/reports）
- 已回寫規則？：部分（本條即記錄；未來換 v5_1 時照此 grep）

## 2026-07-21 ｜治理檔裡的絕對路徑會悄悄漂移（Documents vs Developer）且不會報錯
- 情境：專案全面更名搬遷（`AI投資委員會` → `ai-investment-committee`，含實體資料夾）
- 坑：`docs/agent-ops/MAINTENANCE.md`、`DELEGATION_TEMPLATES.md`、`scripts/run_weekly_review.sh`、`config/office_claude/.claude.json` 等多處硬編路徑寫的是 `/Users/kavi/Documents/Claude/Projects/AI投資委員會`，但實際專案早就在 `/Users/kavi/Developer/Claude/Projects/...`——兩者長期並存、沒有任何 script 會因此報錯（cd 失敗只在真的執行到那條指令時才會發現），純文件型路徑（範本、註解）尤其容易漂移沒人發現
- 修法：全面更名這類 session 動工前，除了 grep 專案名稱字串，另外 grep 完整絕對路徑（含所有已知歷史路徑變體，不只目前 cwd 這個）——本次順手修正 Documents 變體；`config/office_claude/**`、`cache/projects.json` 是巢狀 Claude 執行狀態（office 模擬功能用）指向另一條路徑，判斷為 out-of-scope 不動，已告知使用者
- 已回寫規則？：否（本條屬一次性事件記錄；MAINTENANCE.md §1 的「路徑不存在可自行修正」規則已足夠涵蓋，不需新增規則）

## 2026-07-17 ｜治理檔改前備份是動手前一步，不是事後補
- 情境：新增 grok CLI 進 LLM 治理鏈（`config/llm_config.json` 屬 §1 使用者手動校準區）
- 坑：使用者已 OK 改動摘要表後直接下手 Edit `config/llm_config.json`，改完才想到 §1「永遠不准做」的無備份改治理檔規則，靠 `git show HEAD:` 補回原始內容才補上備份——若該檔當時不是 clean（已有未 commit 的異動），git show HEAD 補的會是錯的版本
- 修法：治理檔（`config/llm_config.json`、`weights.yaml`、`positions.json`…）的 Edit 前，先跑 `cp X docs/agent-ops/backups/X.bak-YYYYMMDD`，跟「先問使用者」同一步驟做，不要等改完
- 已回寫規則？：否（規則本身在 MAINTENANCE.md §1 已存在且夠清楚，這條純記過程疏漏）

## 2026-08-03 ｜「spec 說乘數套在 X」不等於「JSON 欄位存的是套用前的 X」
- 情境：SE1 要修 sector shadow calculator 的覆蓋率（`sector/scripts/sector_score_calculator.py`）
- 坑：我從 `sector_protocol_main.md` Step 5 的「特殊條件乘數（套用於 Score_adjusted）」推論
  calculator 漏模 ×0.70，補模後**實跑 2026-07-31 當場產生 diff=20 的假 hard diff**。掃過全部
  帶 `binary_risk_within_48h` 的 33 筆歷史 decision 檔才發現：31 筆的
  `sum(score_components) × step6_mult` 直接等於 `composite_score` —— LLM 是把乘數**烙進四個
  分項之後**才寫下的（Energy 那筆的 `key_reasons` 白紙黑字寫「已套用 binary ×0.70（91.8 →
  64.3）」，64.3 正是四分項的和）。補模 = 雙重計分，會把 31 筆正確樣本全打成 hard diff。
- 修法：**要重算一個 LLM 寫下的數字之前，先用歷史樣本反查該欄位的實際語意**
  （`sum(components) × mult == composite?` 這種一行 pandas/字典比對就夠）。spec 描述的是
  計算順序，不保證中間值落在哪個欄位。反查不出來就「偵測不重算」+ 標 unverified，
  不要猜。同理適用任何 shadow / replay engine 的欄位對齊。
- 已回寫規則？：否（屬動工方法而非治理規則；SE2 割接的規格已在 TODO 記下「engine 必須改吃
  未經乘數的原始分項，否則同一乘數套兩次」）

## 2026-08-03 ｜Python 內建 `round()` 用在給人看的分數上是靜默錯誤源
- 情境：同上，SE1 對照 LLM 的 `composite_score`
- 坑：`round()` 是銀行家捨入（`round(42.5) == 42`），而 protocol 的整數分慣例是 half-up。
  473 筆歷史樣本實測 half-up 相符 92.2% vs banker's 91.5%，差的 3 筆全是 `.5` 邊界且 LLM
  三次都進位。用錯不會炸，只會產生整批 ±1 的差異——**剛好落在 soft diff 門檻內**，看起來
  像「LLM 心算有點飄」而不是「我的捨入方式錯了」，很容易被當成雜訊接受。
- 修法：任何要與 LLM/人工產出的整數分對照的 script，捨入一律寫成具名函式
  （`_round_half_up = math.floor(v + 0.5)`）+ 註解 + 邊界測試，不要直接呼叫 `round()`。
- 已回寫規則？：否（已在 `OPS_COMMANDS.md` §7 的測試表註明「不可換回內建 `round()`」，
  由測試守住）

## 2026-08-03 ｜「資料不可用」守衛要問「不可用的最小單位是什麼」
- 情境：SE1/SE3/SE5 三支 script 的 code review（`sector_score_calculator.py` /
  `da_pretrigger.py` / `fred_lane_gate.py`）
- 坑：三支是不同時間分開寫的，卻各自在同一個位置漏同一種守衛 —— 都**已經**在整檔層級
  寫了正確的守衛（`missing_score_components` / `_load_hard_cache` rc=1 /
  `isinstance(a, dict)`），但規則沒往下延伸一層：`_num(...) or 0` 讓單一 null 分項變
  0 分（產生假 hard diff，而累計上限是 0，一筆就永久擋死割接且理由是假的）、
  `cache.get(s) or {}` 讓缺席板塊變「查過了、沒事」、`_canon_list` 讓 list 內非字串
  炸出 traceback。**三支的測試全綠，因為現有資料剛好乾淨。**
- 修法：寫「資料不可用」守衛時先問「不可用的最小單位是什麼」——檔案、板塊、還是欄位。
  答案幾乎都是最小的那個。測試要照那個粒度設計（缺一格、空 dict、型別錯），而不是只
  測「整份不見」。
- 已回寫規則？：否（屬動工方法；三支的具名守衛已由 `OPS_COMMANDS.md` §7 的測試表釘住）

## 2026-08-03 ｜做了 audit/live 分離之後，要列一遍「還有誰能寫進這個池子」
- 情境：同上，SE1 的割接證據池
- 坑：`--audit-decisions` 刻意設計成唯讀、不寫 shadow 樣本（正門守得很好），但
  `build_sector_intel.py --date <過去日期>` 重跑舊場次會照常落盤進 live 分母 ——
  而且 `build_phase0()` 讀的是**今天**的 FRED/breadth cache，存下的 `context` 根本不是
  掃描日的狀態。repo 裡的 `.prev-0101` 備份證明重跑舊日期是實際會發生的操作。
- 修法：新增一個「證據池」概念時，把**所有**寫入路徑列出來逐一判定，而不是只守自己
  新增的那條。這裡的修法是 `scan_date != today` → `sample_valid=false` +
  `invalid_reasons=["backfill_rebuild"]`。
- 已回寫規則？：否

## 2026-08-03 ｜資料無法裁決時，要說出「這一項是按原則定的」
- 情境：同上，half-up 捨入的第二輪修正
- 坑：473 筆歷史樣本對四個捨入變體給出**完全相同**的結果（沒有樣本落在邊界），所以
  「實測 92.2%」這個數字**無法**支持「中間那道 `round(x, 2)` 該不該留」。差點又用一次
  同一組數字去背書一個它證明不了的決定。
- 修法：改用兩個可獨立驗證的事實決定 ——(a) `round(x,2)` 是銀行家捨入，造成雙重捨入
  （`64.25 × 1.035` → 67 而非 66）；(b) 實掃乘數表 × 0.5 間隔分數，
  `50.0 × 1.15 == 57.49999999999999` 等 3 例真值恰為 `.5`，裸 `floor(v+0.5)` 會少 1 分，
  所以 eps 是必要不是保險。**在 CHANGELOG 明寫「這一項是按原則而非資料定的」**，
  免得下一個人以為它有樣本背書。
- 已回寫規則？：否

## 2026-08-07 ｜子代理的推論性結論是主張,不是事實
- 情境：盤中系統盤點,Explore 子代理回報「IEX 免費 feed 量能系統性低估 → `VOL_MULT` 量能確認結構性弱」,差點被寫進變更表當成要修的問題。
- 坑：低估「水位」不等於扭曲「比值」——`vol_mult` 是同 feed 內本分鐘 vs 前 15 分均量的比值,低估在分子分母同時出現、大致抵消。子代理把一個正確事實(量被低估)外推成一個錯誤結論(確認失效),而事實部分的正確性讓結論看起來可信。
- 修法：子代理回報裡「事實」(檔案:行號、實跑輸出)直接採用,「推論」(所以…因此…結構性…)一律自己重推導一遍再放進變更表;動工前確認表就是做這件事的最後閘門。
- 已回寫規則？：否(單一案例,先記中繼站;重複發生再進 MODEL_DISPATCH §4 回報合約)
