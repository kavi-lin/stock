# Session Notes 歸檔 v4.133.1 → v4.135.1（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v4.135.1) — 跨專案 broker 使用不再假冒本專案綠燈

- quota panel 現在綠燈只代表 `ai-investment-committee`，藍燈代表 `tw-stock-wonwon` 等其他 broker project；同 provider 雙邊使用時可同時亮兩燈。
- ownership 由 `broker_gate.quota_snapshot()` 輸出 `is_local_project`，前端不複製 project ID；缺少 attribution 時 fail-safe 為外部藍燈。
- Browser 未連線，未假稱目視驗收；後端 local/external/unknown fixtures、UI/CSS 合約、JS 語法與 402 項主測試均通過。

## 🟢 Session Note (v4.135.0) — LLM 只有一個分配權威

- 24 個 LLM task 已按 agentic / ensemble / structured / narrative / external-tool 分類；正式 provider 僅 Claude、Agy、Codex，Grok 停用。
- 全部 inference 必須先取得 broker lease；一般任務由 broker 選模型，ensemble/認證可 pinned，但失敗不跨模型重播。互動 protocol 留 queue 重試，daemon/cron defer。
- Tier 3 三家隔離 canary 均通過（各 2 entities / 1 triple），正式 graph/cache 未寫入；audit 與 402 項主測試、targeted router/queue/Nexus/Wind/JS tests 全綠。

## 🟢 Session Note (v4.134.5) — 派送層的暫時失聯不能變成 ticker 消失

- live queue recent 明確記錄 INTC 兩次 `broker:unavailable`；不是 Claude 額度錯誤。Claude 當時剩 23%、hard reserve 20%，broker preview 的確把 Claude 排除，但 Agy／Codex 仍可在 slot 釋放後接手。
- `broker:unavailable` 現在回 queue 並 bounded exponential backoff；panel 顯示等待原因、attempts 與最近 10 分鐘失敗，派送尚未開始 inference 時不再靜默消失。
- 驗證：`tests/` 402 passed、queue/UI targeted tests、JS syntax、diff check 全綠。Browser skill 無已連線 browser，未假稱目視通過。

## 🟢 Session Note (v4.134.4) — Phase UI 要表達順序，不是把 list 換三張卡

- 盤前檢查改成緊湊橫向三階段進度軌；Phase node、connector 與 task progress chip 同時表達 active / complete / error / waiting。
- modal 以 viewport 動態限高，小螢幕才退回直向；chain 啟動後只留主按鈕，移除底部三顆按鈕同時撐高的情況。
- Browser skill 無已連線 browser，未假稱目視通過；改以 live-served DOM/CSS/JS、viewport contract、JS syntax 與 401 項主測試驗收。

## 🟢 Session Note (v4.134.3) — 全市場資料不能用 ticker 檔名當 ownership boundary

- GEV 失敗時，當日 canonical `2026-08-21_phase0.json` 已存在且與 AAOI snapshot 完整一致；真正缺陷是 factpack 優先讀 schema 不完整的 sector cache，validator/builder 又只猜 `phase0_<ticker>.json`。
- resolver 現在先取 shared investment snapshot；legacy ticker 檔只作 migration fallback。sector cache 只供 L3 重建，不能直接通過 gate。
- factpack 輸出 frozen `phase0_path`，validator 用 `--path` 驗同一檔，Phase 5 也明確接收同一路徑；並行 ticker 不會在中途換 snapshot。
- 實測 GEV 解析 canonical、`macro_summary` / `_market_signals` 均存在、validator rc=0；三支 Phase 0 / factpack / builder contract 與 `tests/` 398 項全綠。

## 🟢 Session Note (v4.134.2) — UI 有三格之後，backend 也必須有三條獨立寫入路徑

- 先前只修 UI，`_protocol_artifact_key("invest")` 仍回傳 `investment-global`，所以不同 ticker 還是全排在一個 active 後面。現改為 `invest:<ticker>`，同 ticker 才互斥。
- 不能只改 scheduler key：validator、renderer、thesis register 原本都抓 `history[-1]`，而 history 的 flock 還鎖在會被 rename 掉的 inode。新流程先處理 per-ticker isolated session，最後用 stable lock commit。
- server post-run gate 除了驗 isolated session，還會確認同一 digest 已進 global history，不會把「報告寫了但沒 commit」靜默標成 done。
- 驗證：398 pytest passed；scheduler 3 active + 1 waiting；18 路並行 history commit 無遺失；Phase 5 schema、renderer、broker、JS 合約全綠。

## 🟢 Session Note (v4.134.1) — capacity 要畫成 slot，pending 不能偽裝成佔用

- 全域 protocol pill 現在固定畫出三格 execution slots：active 依 broker provider 上色並顯示 job／時間／model，空位用虛線「空閒」呈現。
- pending queue 移到獨立「等待中」區塊；摘要只顯示 `active/capacity` 與 waiting 數量，不再重複 primary model。
- live API fixture 為 `ECHO / Gemini active + AAOI waiting + capacity 3`；JS syntax、diff check、server-served asset 均通過。Browser skill 無可用瀏覽器實例，因此未產出視覺截圖。

## 🟢 Session Note (v4.134.0) — quota 與 execution slot 都只能有一個跨專案權威

- AIC 不再用本機單一 active state 或 invest cooldown 決定哪家 LLM 可以工作；broker 的 Claude／Agy／Codex exclusive slot 才是跨 `ai-investment-committee` 與 `tw-stock-wonwon` 的權威，AIC scheduler 最多同派三件。
- execution lock 不能只靠 TTL：owner heartbeat 失聯時先看已登記的 PID／PGID／UID／start token。child 還活著就保留鎖；退出才釋放；TTL 到期則終止 process group 並確認死亡後解鎖。
- start→attach 的窄窗口也要收尾：active reservation 尚無 PID 且 heartbeat 逾時時必須 expire，否則 caller 在 Popen 前 crash 會永久卡死。
- 並行不等於允許 artifact race：invest/news/sector 是 global single-writer domain，不同 ticker earnings 才可同時跑。status 與 cancel 必須帶 job/queue identity，不能再拿一個全域 current job 猜。
- 升級相容：schema 2 的舊 pending row 沒有 `start_deadline`，0.3.0 會按 `created_at + 30s` 回收；migration 也把舊 pending 標成可立即回收，避免升級後沿用舊 30 分鐘 TTL。
- 驗證／部署：AIC 398 pytest passed + routing/broker/scheduler contracts；broker 1063 full-suite passed，補升級相容後 5 provider-slot regressions passed，Ruff/mypy 全綠。broker 0.3.0/schema 3 與 Dashboard 已重啟；active reservation 0、queue capacity 3。

## 🟢 Session Note (v4.133.2) — backlink 不是狀態，每條終止路徑都必須收尾

- Signal Queue 的 `consumed_by` 只是來源頁 backlink，不能當 delivery authority；否則新 revision 即使已重開，前端仍會被舊 backlink 壓成「已產出分析」。
- `failed` 的意義是「本次沒消耗掉候選」，所以同 evidence revision 必須立即可重試；`consumed` 只對完成分析時的 revision 有效。
- 一個 queue job 不只有「跑完」一種終點：pending remove 與 dispatch 前拒絕也必須走同一個 terminal writeback，否則 UI 會永久卡 `queued`。
- rc=0 不代表報告存在。`earnings` 與 script-family `earnings_preview` 各自要在真實執行入口接 fresh artifact gate，報告連結也要限定 mtime 新於 run start。
- 列表分頁不是詳情頁的存取邊界；`?news_id=` 可直接取 item。同理，ticker cap 若說「超過就排除」，實作必須 `continue`，不能安靜地截前 8 檔。

## 🟢 Session Note (v4.133.1) — quota 有百分比還不夠，小卡直接說還要等多久

- 側欄現在為每個 provider 選擇 weekly bucket：Agy 優先用 broker 正在路由的 pool，Claude 優先 `weekly.all_models`，Codex 用 `primary` 的 10080 分鐘窗口。倒數統一顯示成 `3D23H reset`；滿額但 broker 沒給時間時不虛構倒數。
- 實際 broker payload 三種時間形狀並存：Codex `resets_at`、Agy `refresh_in_seconds`、Claude `reset_label`，前端三者都有 fallback。驗證為 JS 語法、broker gate 合約、三組倒數 fixture；Browser skill 當時沒有可用瀏覽器實例，未做視覺截圖。
