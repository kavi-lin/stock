# Session Notes 歸檔 v4.48.1 → v4.54.2（新在上，共 9 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v4.54.2) — REVIEW_2026-06-28 收尾：Rec 11 hot_zone_eval instrumentation (TODO-015)
- **起因**：weekly REVIEW_2026-06-28 點名本週最高風險盲點 —— 決策層 Rec 11（熱區保守性鬆綁）上線 21 天，首個 qualifying 場景 **TXN 06-22** 出現，卻**無任何欄位**可確認規則是否被評估（`hot_zone_probe` extractor=0/160），無法區分「評估後被 risk_flag 正確抑制」vs「規則根本沒被評估」＝驗收盲飛。
- **做掉(firm)**：補 instrumentation（**純記錄，0 下單/評分邏輯改動**）。① protocol Rec 11 段 + export JSON 強制寫 `hot_zone_eval` enum；② `deep_dive_extractor.py` 讀權威值 + 對缺欄歷史報告反推 `hot_zone_eval_derived`（含 `qualifying_unexplained` bug 告警 + `not_evaluated_pre_rec11` 去除 go-live 前誤報），160 份歷史即時回填；③ validator §11b 強制 `probe⟺fired`；④ `replay_rec11.py` 改讀 eval 不再 assume-pass。
- **驗收結果**：全樣本 qualifying=16 → suppressed_by_risk_flag **14**（含 TXN，Valuation SELL −3.0 + Burry WARNING）+ not_evaluated_pre_rec11 **2**（SNA/HPE 皆 pre-go-live）+ **真 qualifying_unexplained = 0** → **確認 Rec 11 有被評估且 TXN 正確抑制，非 bug**。replay TXN 從「would fire」正確剔除。+10 unit test 全 PASS（既有 news_digest 1 fail 為 pre-existing，與本案無關）。
- **carry-over 清理**：TODO-013 done(refuted) / TODO-004 dropped / TODO-006 休眠。解鎖 TODO-012（Rec 11 真驗收）。
- **下一步**：下輪 REVIEW 用 `hot_zone_eval_derived` 分布驗收 Rec 11，盯 `qualifying_unexplained` 須維持 0；遇 score∈[0,0.8) 且無硬 flag 的 top30 半導體即啟動首次正向 `fired` 驗收。

## 🟢 Session Note (v4.54.1) — 修逆勢假反轉 + 訊號流收合
- **起因**：4.54.0 趨勢偵測上線後，user 看 MU 卡片爆「★⤴ 反轉向上 KDJ金叉+MACD金叉·超賣翻揚」，但實際圖是均線空頭排列、破低急跌。根因：`detect_reversal` 對下跌趨勢中的超賣小金叉（dead-cat bounce）誤判為反轉，且前端優先序「反轉>趨勢」讓假反轉蓋過正確的順勢續跌。
- **做掉(firm)**：`apply_trend_context(rv, tr)` —— 反轉方向 vs 嚴格均線排列趨勢相反 → `counter_trend=True` + `alert=False` + 改稱「逆勢反彈/回測」；`build()` 套用（`rv = apply_trend_context(detect_reversal(...), tr)`）。前端 `counter_trend` 反轉不當頭條,落回趨勢。另 user 要求訊號流不要連三次 → `_collapse_flow()` 把連續同向收合成一筆(spike 保留 ⚡),`max_events` 4→3。**+4 case 全 PASS**;live build 驗 flow 已去重、counter_trend 邏輯由單元測試覆蓋。
- **已知取捨**：counter_trend 只在**嚴格**對向排列下觸發;趨勢未成強排列時(tr=None)逆勢反轉仍會報(設計如此,避免過度壓抑真反轉)。
- **限制**：Alpaca 免費 IEX 僅美股。探索層,不入 investment_protocol。

## 🟢 Session Note (v4.54.0) — 個股急拉/急殺：加「順勢續攻/續跌」趨勢延續偵測器
- **起因**：user 指一張明顯多頭續攻分鐘圖（均線多頭排列 + KDJ 高檔順勢金叉 + 創高）面板仍顯示「尚無訊號」。Review 後確認根因：面板原只有兩個**瞬間變化**偵測器 —— `detect_spikes`(|1分|≥1% / |3分|≥2%,平滑緩漲碰不到)、`detect_reversal`(近 3 根**新**交叉,順勢延續時早過期)。缺的是**狀態型**「趨勢仍在續攻」。
- **做掉(firm)**：`detect_trend()`（狀態型,雙向）—— 多頭 = **嚴格疊排 ma5>ma10>ma20** + 收 ≥ ma5 + ma5 上揚 + KDJ `K>D & K≥TREND_K_MIN`(50) + 收盤貼近近 20 根窗高（tol 0.1%）；空頭鏡像。`strength=strong` 當 K≥70/≤30。`_sma()` helper。payload 1.3→**1.4**,每 reading 掛 `trend` + top-level `trends[]`。面板狀態行優先序 **反轉 > 順勢趨勢 > 尚無訊號**,趨勢卡左緣穩定色條(非 pulse)。`test_intraday_spikes.py` +5 case / +19 asserts ALL PASS。**Live 驗**：原 12 檔全「尚無訊號」→ 6 檔跳訊號（GOOGL/META 續攻、AVGO/AAPL/NVDA/TSLA 續跌）。
- **可調 / 已知取捨**：多頭排列採**嚴格疊排**（user 指定,訊號少而準）。優先序把**非 alert 的小反轉**(如單純 MACD DIF 翻)排在 strong 趨勢之前 —— 若覺得 strong 趨勢更該優先,可調 render 邏輯。`TREND_K_MIN`/`TREND_HIGH_WINDOW`/`TREND_HIGH_TOL` 為 tuning 常數。
- **限制**：Alpaca 免費 IEX **僅美股**。探索層,不入 investment_protocol。

## 🟢 Session Note (v4.53.0) — 個股急拉/急殺：反轉偵測 + 訊號流卡片 + KDJ+MACD alert
- **演進**：4.52.0 攤出每檔即時% → user 嫌 0.X% 噪音、不要每分鐘亂跳,要「真的篩出正在反轉的」。兩輪確認鎖定：(1) 純動能交叉、雙向；(2) UX = 每檔一張卡片 + 橫向訊號流 + 對應時間；核心情境 = SNDK「KDJ 剛上翻 + MACD 轉正 → 趕快提示」。
- **做掉(firm)**：`detect_reversal()`（KDJ K×D 交叉 or MACD 轉向[金叉/柱翻/DIF零軸] within 3 bars；**alert = KDJ+MACD 同向** → strength strong）+ `build_signal_flow()`（重建近 30 分事件流,帶時間,新到舊）。payload 1.2→1.3,每 reading 掛 reversal/flow/alert + top-level alerts[]。面板重做成緊湊卡片 grid（固定序不 reshuffle）+ alert 卡 pulse 發光 + 頂部 banner + 🔔 桌面通知 opt-in。時間改 ET。33 asserts ALL PASS;SNDK V-shape fixture 驗到 alert=True/basis KDJ金叉+MACD金叉/超賣翻揚。
- **可調**：`REVERSAL_LOOKBACK`(sticky 分鐘數=3)、`KDJ_OS/OB`。純交叉在 1 分線偏敏感(現況 12 檔常 3-7 檔在反轉),探索期可加幅度/zone gate 收斂。
- **限制**：Alpaca 免費 IEX **僅美股**；1 分粒度交叉最快 ~1 分偵測,sub-minute 需 SIP tick。探索層,不入 investment_protocol。

## 🟢 Session Note (v4.52.0) — 個股急拉/急殺：每檔獨立訊號 + UI 可編輯名單
- **起因**：user 看富途某檔明顯急拉沒被標,問「目前監控哪 10 檔」「這樣不算急拉嗎」。根因：面板只在過門檻時才顯示 chip,平時只露計數,看不到在監控誰 / 未達 ±1%/±2% 門檻的即時狀態,且名單只能手改 `spike_watchlist.txt`。
- **做掉(firm)**：(1) 引擎 `latest_reading()` → payload 新增 `readings[]`（每檔即時 1分/3分 % + last + spiking flag,不論是否過門檻）+ `watchlist[]`,version 1.0→1.1;`save_watchlist()` 驗證/dedupe/≤50/保留檔頭/atomic。(2) server `GET/POST /api/intraday-spikes/watchlist`。(3) 面板改每檔一個獨立訊號 chip（spiking 高亮 ⚡★✓badge,其餘淡色顯示即時 %,無資料標「無資料」）+ ✎ inline 編輯器存檔即重偵測。
- **驗**：test_intraday_spikes 24 asserts ALL PASS;save_watchlist round-trip（dedupe/case/validation/restore）✓;server compiles ✓。
- **重點警語**：Alpaca 免費 IEX 只覆蓋**美股**。截圖那種 ~2303 價、單位「萬股」的標的（港股/陸股）這條 lane 抓不到,要另接資料源 — 不是門檻問題。
- **紀律**：探索層,不入 investment_protocol。

## 🟢 Session Note (v4.51.0) — 急拉/急殺加 MACD/KDJ/量 確認層
- **起因**：user 看富途 SNDK 急拉(放量 + MACD DIF 上穿 + KDJ 88/91 + 資金淨流入特大單綠),要「MACD or KDJ 加上量去判斷急拉/急殺」+「如果能看資金流向/單進來更好」。
- **做掉(firm)**：`detect_spikes()` 在同批 1min bar 重用 `intraday.compute_macd`/`compute_kdj` → confirmations(MACD/KDJ/量) + confirmed(價 + ≥2 同向),fetch 窗口 40→90 分(1min MACD 需 ~35 根)。頁面 chip 加 ✓badge + ★。24 asserts ALL PASS;live demo(降門檻)驗到 META 急拉 ✓MACD✓KDJ✓量 confirmed。
- **資金流向/特大單(未做,待 user 選)**：tick 級按單大小,免費 IEX 給不了。三條路:(a) **Futu OpenAPI/moomoo OpenD**——可拿截圖那個確切的特大單/大單/中單/小單(免費,用 user 自己 Futu 帳號,但要裝 futu-api + 跑 OpenD gateway;repo 現只有 parse_futu_notifications 解析推播、無 OpenD);(b) **Alpaca SIP $99/mo** tick → 自己按 $ 大小+方向分類(近似 Futu);(c) **免費 bar 近似**(OBV/上下量比/MFI,只有方向無單大小)。已 AskUserQuestion 詢問中。
- **紀律**：探索層,不入 investment_protocol。

## 🟢 Session Note (v4.50.0) — 個股急拉/急殺快線（Alpaca 1 分鐘，獨立 lane）
- **起因**：user 要對**個股**抓 1 分鐘急拉/急殺，大盤維持 FMP 5min。查證：FMP 1min 被 402 鎖、Polygon(Massive) 免費無即時 WS、**Alpaca 免費 IEX 是唯一 $0 即時 1min**（但量被低估，VWAP/RVOL 不準；準量需 $99 SIP）。
- **拍板(AskUserQuestion)**：REST 輪詢(非 WS) + 自訂 config 清單 + intraday 頁新增區塊。
- **實作**：新獨立模組 `intraday_spikes.py`（0 LLM，純 `detect_spikes()` core + Alpaca REST 多檔一次抓）+ `config/spike_watchlist.txt`（可手編，種子 10 mega-cap）。偵測：近 5 分鐘 `|1分|≥1%` 或 `|3分|≥2%`，severity high/med，量增 3× 為次要確認（IEX 量不準故價格為主）。
- **接線**：`dashboard_server` `intraday_spikes_poll_loop`（預設 60s，盤中 + 開機快照，獨立 lock）+ GET `/api/intraday-spikes/data` + `intraday-mood.html` 頂部「個股急拉/急殺」區塊（▲綠/▼紅 chip）。無 `ALPACA_API_KEY`/`ALPACA_SECRET_KEY` 時 graceful no-op、面板顯示提示。
- **驗收**：18-assert 測試 ALL PASS；no-key build graceful；server boot → endpoint `no_alpaca_key` wl10 feed iex、頁面 200。
- **待 user**：去 alpaca.markets 免費註冊 + paper account → 設 `ALPACA_API_KEY`/`ALPACA_SECRET_KEY` 環境變數才會真的抓資料（我不幫註冊帳號）。`ALPACA_FEED=sip` 可切付費全量。
- **紀律**：探索層，不入 investment_protocol。

## 🟢 Session Note (v4.49.0) — 盤中評估：MACD/KDJ 動能確認層（下殺/反轉）
- **起因**：user 問「即時化有沒有 MACD/KDJ 反轉/下殺提示」。本來只有純價格行為。`technical_core.py` 有 pandas 版 `compute_macd`+`rsi_14` 但無 KDJ，且引擎刻意 pure-python，故在引擎內自寫輕量 MACD/KDJ。
- **拍板（AskUserQuestion）**：(1) 日線+盤中5min 雙框；(2) **只出旗標、不動綜合分數**。
- **做法**：`compute_macd`/`compute_kdj`（pure-python，末根交叉偵測，資料量不足回 None 守門）→ 日線(regime)+5min(時機)。旗標 confluence-gated：下殺=盤中 KDJ 高檔死叉 或 MACD 死叉+跌破VWAP；反轉=盤中 KDJ 低檔金叉 或 日線 MACD 柱轉升(弱勢脈絡)；macd_daily=日線金叉/死叉 context。每檔 `momentum` 數值永遠透出，頁面卡片加讀數+交叉箭頭。
- **驗收**：47 asserts ALL PASS；live smoke 三檔 momentum 都算出且**旗標選擇性正確**（QQQ 5min MACD 死叉但無 VWAP 確認→正確不噴；刻意 gate whipsaw）。週期/門檻皆檔頭常數可調。
- **未做（user 待決，盤中 Tier-1）**：盤中 VIX / 類股輪動 / HYG 信用 / 時段化 RVOL。

## 🟢 Session Note (v4.48.1) — 盤中評估：即時 quote 混合（破底偵測秒級化）
- **起因**：user 問「盤中評估是不是可以拿 FMP 即時 K 棒判斷」。答：本來就是用 5-min K，但實測點出**最後一根未收的 K 最多落後 ~5-6 分鐘**（12:30 K vs 12:36 quote），破底/急殺剛好在那幾分鐘。
- **做法**：`assess()` 加 `live=` 參數；`build()` 多抓 FMP `quote`（`_fetch_live_quote`）。即時 quote（~2s 新）覆蓋 **spot/當日高低/當日量/昨收**，5-min K 仍管 VWAP + 型態。→ 破底/止跌偵測秒級化；當日量改官方累計（原本是已收 K 量加總、少算尾端）。
- **透出**：每檔加 `data_source`（live_quote+5min / 5min）+ `quote_timestamp`；頁面 pill 顯示「· 即時報價」。
- **驗收**：34-assert（+8 live-override）ALL PASS；live smoke 三檔 `live_quote+5min`，官方量 + 秒級 timestamp。1min K 不可用（stable 回 None）→ 型態最細維持 5-min。
- **未做（user 待決，上一輪 Tier-1）**：盤中 VIX context 分量、類股輪動快照、HYG 信用佐證、時段化 RVOL 曲線——都可走同一支 quote/5min，等 user 點。
