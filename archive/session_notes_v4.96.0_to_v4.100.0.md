# Session Notes 歸檔 v4.96.0 → v4.100.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

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
