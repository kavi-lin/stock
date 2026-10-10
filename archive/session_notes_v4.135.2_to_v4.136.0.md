# Session Notes 歸檔 v4.135.2 → v4.136.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v4.136.0) — 盤前 brief 的四類錯誤，以及 archive 如何吃掉修正

- 使用者回報 9/17 盤前檢查「錯誤很多」。cron 本身 rc=0、16 OK / 1 WARN，error 數量與前 10 天持平（12 vs 9~13）——**不是 regression，是長期帶病運轉**。真正的問題全在報告內容。
- 四類：(1) §10 印出 Python dict 原文（`r.get('title', r)`，`binary_risks` 的鍵是 `event`，fallback 把整個 dict 交給 f-string）；(2) §6 全表時間晚 4 小時（FMP `economic-calendar` 的 `date` 是 UTC，舊碼直接接 `" ET"` 當標籤）；(3) 標題被 `title[:36]` 切成 `…(Sep/1`；(4) 同一份房市數據列三次（fmp-econ 英文 `econ` ＋ sector-protocol 中文 `macro`，Pass 1 看不出是同一件事）。
- **最花時間的是第五個，修完前四個才浮出來**：改完 `_from_fmp_econ` 重跑 bridge，輸出**完全沒變**。原因是 `_merge_two` 只在 impact 較高時換主記錄，archive 裡的舊版本與 fresh 版本同為 `high` → 舊的原樣留下。函式 docstring 明寫「fresh raw entries overwrite stale archive versions」，實際行為不是。加 `pin_primary=True` ＋ `_repair_archived_times()` 一次性遷移（146 筆）後才落地。這是 §2c「靜默綠」的寫入路徑版本：**改對了、跑完了、rc=0、輸出沒動，而沒有任何東西報錯**。
- `_slugify` 的 `[^a-z0-9]+` 會把中文整段丟掉（`8 月新屋開工與建照` → `'8'`），所以跨語言去重不可能靠 slug。改為保留 CJK，另建 `_CANONICAL_RELEASES` 關鍵字表做跨語言對應。表刻意保守——規則必須指名發布序列本身（要求 `ISM`、要求 `Fed Interest Rate Decision`），因為**誤併會靜默刪掉一個真事件，漏併只是多一行**。複合標題（同時命中 ≥2 個 series）不合併，改由 Pass 1c 在其涵蓋的每個 series 都已有更完整記錄時才吸收。
- Screener 每日 4 errors 的來源是名單過期：ANSS（併入 Synopsys）、WBA（下市）該刪；`BRK.B`/`BF.B` 對 yfinance 要用 dash（實測 dot 拼法回 0 rows，dash 回 5 rows）。`skills/_shared/company_context.py` 早就是 `BRK-B`，兩邊不一致了很久。
- morning_brief 當時回報「0 warnings」。渲染層 fallback 命中不進 warning 通道，所以報告裡有原始 dict 也照樣「綠」。已讓缺鍵的 binary_risks 推 `_warnings`。
- 測試：新增 `tests/test_event_calendar_hygiene.py` 40 項全綠；既有 `test_premarket_daily_outcome` / `test_bridge_cache_loading` / `test_premarket_chain_ui` 14 項未受影響。bridge 實跑 rc=0，重生成的 `reports/PREMARKET_2026-09-17.md` 四類錯誤全消（9 筆事件 → 8 筆，時間 08:30 ET，FDX 只出現一次且帶 AMC）。
- **未處理**：sector-protocol 自己產的裸 `HH:MM`（非 FMP 轉手那批）沒有可靠的時區依據，只轉換了能確認的；archive 裡已被截斷的舊標題無法還原（原文未留存），未來事件會被 fresh feed 蓋回完整版，過期事件維持原狀。

## 🟢 Session Note (v4.135.11) — open_dashboard.sh 的 [Errno 48] 與「假的啟動成功」

- 使用者跑 `./open_dashboard.sh` 撞 `OSError: [Errno 48] Address already in use`，但 script 照樣往下印「Wind dispatcher already running」＋「Dashboard running (PID 24472)」——輸出完全看不出 server 到底活著沒有（實際上該輪確實有一隻 server 活著在 :8080，PID 24475，HTTP 200；死的是搶輸的另一隻 python）。
- 根因：舊版 `lsof -ti:$PORT | xargs kill -9` 之後**立刻** bind。kill 是非同步的，process 還沒收屍前 socket 不釋放，bind 就落進那個空隙。
- 修法：`stop_port()` TERM → KILL 逐級升，每級輪詢 `lsof` 到 port 真的空（各 5s），都收不掉就 abort 並印佔用者 PID；啟動後改 health poll（curl 最多 10s）確認 listening，沒起來直接 `exit 1`，不再往下開瀏覽器／派工器／印「Dashboard running」。
- `scripts/restart_dashboard.sh` 早就是這個做法（它的註解還在說 open_dashboard.sh「goes straight to -9」），註解已同步更新。
- 測試：在 :8099 用假 server 跑過「殺舊→起新」(rc=0) 與「起不來」(rc=1) 兩條路徑；沒有動到線上那隻 8080 server，也沒發起任何 LLM inference。

## 🟢 Session Note (v4.135.10) — Phase 0 重建加鎖

- 2026-09-02 22:01 GOOG(claude) 與 JPM(codex) 相差 8 秒派工，兩邊都判 canonical Phase 0 快照 stale，各自跑了一次完整 4-skill L3 重建；`sector/breadth_cache/` 等目錄 90 分鐘內被連寫 3 波，外部 API 成本重複付了兩次。
- 新增 `investment/scripts/phase0_lock.py`（mkdir lock，token-based release，20 分鐘 time-based staleness 回收）；`investment_protocol_v5_0.md` L3 段落改成先 `acquire`，拿不到就 `wait --timeout 900`，逾時停下回報而不是搶鎖硬重建，鎖釋放後先重查 canonical 是否已變新鮮再決定要不要自己重建。
- **設計上踩過一次坑**：一開始用 PID liveness 判斷 abandoned lock，但 `acquire`/`release` 都是 agent 用 bash 呼叫的一次性 process，PID 一呼叫完就死，第二次 acquire 會把第一個 run 的鎖誤判成 abandoned 直接放行——鎖形同虛設。改成 token-based ownership + 純時間過期後修正，已跑過 acquire/held/wait-timeout/bad-token/release/stale-reap 全套手動測試。
- 純腳本/文件改動，未跑既有 investment protocol 全套 pytest（`investment/scripts/` 沒有既有測試涵蓋這支新檔）；未發起 LLM inference。

## 🟢 Session Note (v4.135.9) — FINVIZ 小數週報酬不再放大 100 倍

- Radar 的 `±30.0%` 不是前端算錯，而是 FINVIZ `Perf Week` 的 `0.54%` 字串被當成 decimal `0.54`，後續乘 100 成 `54%` 再遭 hard cap 截成 `30%`。
- `finviz_performance_client._parse_perf_value()` 現在對任何含 `%` 的字串一律除以 100；新增正負小數百分比回歸。另加入 FinancialJuice RSS。
- 單檔 14 項、theme-detector 全套 462 項通過；種回舊條件時新測試 rc=1。重建 `theme_detector_2026-09-03_004140.json` 並跑 bridge 後，Dashboard 的 30 個產業榜列已無 `±30.0`。
- 完整重建首次卡在 FMP ETF 逐檔請求，停止後改走既有 yfinance fallback，120.7 秒完成；無 LLM inference。

## 🟢 Session Note (v4.135.8) — 產業成分股清單按市值排

- Radar 產業面板點開的 finviz 完整清單原本照 finviz 回傳順序（字母序）排，43 檔的 Health Information Services 要逐個掃才看得出 VEEV / BTSG / TEM 是龍頭。
- `Dashboard/page-radar.js` 的 `showIndustryStocks()` 改在 render 前依市值降冪排；新增 `_mktCapNum()` 解析 "12.13B" / "197.6M" 字串，缺值沉底。fallback（本地大型股）路徑維持按漲跌幅排，未動。
- `node --check Dashboard/page-radar.js` 通過；純前端排序，無 LLM inference。

## 🟢 Session Note (v4.135.7) — 「等待額度釋放」時額度是滿的

- 盤前 chain 的 News Digest 卡在 `quota_wait #8` 二十五分鐘，CODEX 83% / GEMINI 96.8% / CLAUDE 100%。實際 `last_dispatch_error` 是 `broker:refused(stale_snapshot)`，本 repo 卻把所有 refused 都寫成「no provider has quota outside its hard reserve」。
- 根因在 broker 之外：筆電在電池下持續 Maintenance Sleep，`pmset -g log` 與 snapshot 表對得上（今日刷新間隔 1527 / 4989 / 4348 / 3170 / 6224 秒，排程是 300 秒）。macOS 的單調時鐘在睡眠中不走，掛鐘的 900 秒新鮮度門檻照走，刷新永遠追不上。喚醒後 broker 自行復原，News Digest 隨即取得 codex lease。
- 本 repo 這側只修「說法」：`stale_snapshot` / `not_authenticated` 各自分流，佇列有獨立 waiting reason 與 15 秒重試。broker 側（`llm-quota-broker`）補睡醒即刷新與拒絕時就地重新偵測。
- `test_protocol_cooldown.py`、`test_protocol_model_routing.py`、`test_broker_gate.py`、`test_model_router_window.py`、`audit_llm_governance.py` 全綠；5 支 Dashboard JS `node --check` 通過。本輪未發起任何 LLM inference。

## 🟢 Session Note (v4.135.5) — 額度主卡要畫出派選原因

- 主條原本固定畫 5h 消耗，但 broker 以會被任務碰到的最緊 bucket 派選；因此 Claude `5h 2%` 會遮住實際限制它的 `weekly 27%`。
- 主卡現在從 routable pool 取最緊 bucket，直接標 `週` / `5h`；排序與 tooltip 箭頭共用同一個決定。不強制全畫 weekly，避免 Gemini 真正被 5h 限制時反而顯示錯的派選理由。
- JS 語法、diff check 與 live broker payload 驗算通過；Dashboard server 當時未在 8080 埠執行，Browser 也無連線實例，未假稱已目視驗收。

## 🟢 Session Note (v4.135.4) — broker 拒絕是等待，不是殘缺辯論

- 2026-08-21 共 59 筆 Break News，僅 10 closed；Codex 28、Gemini 27、Claude 1 次 `rc=-9 / 0 ms`。這不是 CLI timeout，而是兩個 item workers 同時搶 broker exclusive slots。
- Break News 現固定跨 item 序列執行；turn 若被 broker 擋下，item 回到 `pending_debate` 並保存 route/error，scan 另計 deferred，不進 partial/failed terminal state。
- 部署時另抓到 launchd PATH 缺 Node/Agy：restart script 現明示 CLI/runtime 目錄；未預期 worker 例外立即回 pending，超時 orphan `debating` 也會復原。
- 未補跑 2026-08-21 的 46 筆 partial/failed，避免未經確認消耗額度。47 項 Break News tests、broker gate 與全量既有 artifact validator 全綠；本輪未主動發起 LLM inference。

## 🟢 Session Note (v4.135.3) — 一個任務只在一個跨頁狀態面出現

- 橘色盤前 chain pill 與紫色 protocol pill 重複顯示 News/Sector，並在同時存在時互相堆疊。橘色跨頁 pill 與 CSS 已移除；盤前 modal 本身保留。
- queue payload 早已保留 `source="premarket_chain"`，前端現在把 News/Sector 顯示為 `盤前檢查 · <task>`，不改變 server orchestrator 與 phase order。
- `daily_update` 只留在 modal progress，沒有加進 `PREMARKET_PROTOCOL_LABELS`，因此不會被當成 provider slot。5 個盤前 UI tests、routing contract、JS syntax 與 diff check 已通過。

## 🟢 Session Note (v4.135.2) — 三個並行工作在每個狀態表面都是同一件事

- broker v0.3 的 live `active_reservations` 是 flat rows，沒有 `project`；同一個 local lease 因此曾被 protocol queue 畫綠燈、quota snapshot 又畫藍燈。每 provider 實際仍只有一個互斥 slot，未重複執行。
- UI 現在以 local run 作為該 provider 的所有權證據，壓掉同一 slot 的 unknown/external 重複燈；收合標題同時列出全部 active tickers。
- pending 列以 queue ID 刪除，不用 ticker 猜測，不會碰執行中的 jobs。目標 routing test、JS syntax 與 diff check 已通過。
