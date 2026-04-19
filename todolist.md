# INTEL COMMAND — Todo List

> **Last Updated**: 2026-04-18
> **Last Session Note (hygiene)**: Audit 所有 protocol 引用的 skills 都有完整本地副本。12 個被 protocols 引用的 skills：economic-calendar-fetcher / market-breadth-analyzer / market-news-analyst / market-sentiment-analyzer / momentum-monitor / portfolio-risk-manager / sector-analyst / short-contrarian-analyst / tail-risk-analyzer / technical-analyst / theme-detector / us-stock-analysis。發現 `theme-detector` 本地只有 `cache/`（靠 global fallback 跑），從 `~/.claude/skills/theme-detector/` 補齊 SKILL.md + README.md + scripts + references + assets。`ftd-detector` / `market-top-detector` 不是走 skill 系統而是 `sector/ftd_yfinance.py` / `market_top_yfinance.py` Python script，不算在此 audit 範圍。專案自此可自給自足，clone 下來不需要 global skills 也能跑所有 protocol。不 bump VERSION（純 data hygiene）。
> **Last Session Note (prev ux)**: 動能表格 **5 欄可點擊排序** —— 價格 / 分數 / 階段 / 距 200MA / RSI，預設降冪（最大值在上）。`th` 加 `.sortable` class + `data-sort="<field>"` + 動態 `.sort-arrow` span。`_state.sort = {field,dir}` 預設 `{score, desc}`；新 `_sortKey(r,f)` / `_compareRows()` 處理 null（排最後不論方向）+ stage 用 `STAGE_ORDER` ordinal map（Stage 2=4、Stage 1=3、Stage 3=2、Stage 4=1、unknown=0），降冪 = 最多頭先列。點 active column 再點切反向；點別的 column 切預設降冪。`_updateSortHeaders()` 每次 renderTable 時重繪箭頭（active ▼/▲ 綠色、inactive dim ▼）。`.mom-th.sortable:hover` 綠色 hint 可點。Visible 集合 sort 後再 re-rank（# 欄反映當前排序視圖的位次）。bump VERSION 1.22.1 → **1.23.0**（minor，新互動）。
> **Last Session Note (prev rsi)**: 動能 **RSI 欄可點擊 popup** 血條視覺化。CSS `.rsi-bar`（橫向 4 段彩色區）+ `.rsi-pointer`（三角形指針帶數字 + 垂直線穿過 bar）+ `.rsi-ticks`（0/30/50/70/100 刻度）。**馬卡龍調色**：超賣 #93c5fd 淡天藍、偏弱 #fcd34d 奶油黃、健康 #86efac 薄荷綠、超買 #fca5a5 珊瑚粉，30/20/20/30% 寬度對應 RSI 區間邊界。Popup 4 區塊：(1) header 當下 RSI 大字 + zone tag + 色碼、(2) 血條 + 指針精準定位於 `rsi%`、(3) 4 條分區意義說明（色塊 + 文字）、(4) **你目前的狀況** 依 rsi_zone 動態挑一段個人化建議 + 搭配 Stage 警語（例如超賣區提醒「Stage 2 中是回檔買點，Stage 3/4 是弱勢延續」、超買區提醒「強勢股能在 70+ 停留數週不要只看 RSI」）。RSI cell 加虛線底線提示可點。Modal 關閉 X / 背景 / ESC 三種。i18n 15 個 RSI 字串 zh/en，使用 `{rsi}` template 替換。bump VERSION 1.22.0 → **1.22.1**（patch，純 UI 擴充用既有資料）。
> **Last Session Note (prev stage)**: 動能 **Stage 階段欄可點擊 popup** 顯示分類邏輯。先在 `momentum.py` `_ma_block` 補 `above_ma50_pct`；`screen.py` CSV 加 `ma_20` / `ma_50` / `ma_200` / `above_ma50_pct`；`bridge.py` 全部帶到 data.json。動能頁 Stage cell 加虛線底線可點 → `openStagePopup(r)`，popup 三區塊：(1) 當前階段色碼 label pill、(2) **MA Stack 視覺化**：Price / MA 20 / MA 50 / MA 200 按數值高低排序，每條橫條寬度 = 相對高度（20-100% 範圍，避免平盤全扁），各自顏色（price 綠 / MA 20 藍 / MA 50 黃 / MA 200 橙）+ 右側顯示絕對值與 `距 price %` delta、(3) **規則 checklist**：對應 `_classify_stage` 的 Python 邏輯，Stage 2/3/4 各自列條件 ☑/☐（成立/未達）+ Stage 1 與 unknown 走 note。底部 「何時轉換到下一階段」的文字敘述（2→3 價跌破 MA 20、3→4 MA 50 跌破 200、4→1 price 回 MA 20 上、1→2 三 MA 排列 + price 上）。色碼：Stage 2 綠 / 3 黃 / 4 紅 / 1 灰。Modal 關閉：X / 背景 / ESC 三種。i18n 18 個 stage 字串 zh/en。重跑 full SP500 fresh scan → 501 rows 帶新 MA 欄位。bump VERSION 1.21.1 → **1.22.0**（minor，新互動 + 新資料欄位）。Session 稍早釐清 MA 50 意義：對 Stage 分類有用、50/200 golden cross 有 institutional self-fulfilling、單獨當支撐意義不大（建議看 swing high/low、breakout pivot、MA 200）。
> **Last Session Note (prev volume)**: 動能 **量比算法修正 + 可點擊 popup 顯示盤中全日推估**。(1) `momentum.py` `_volume_block` 新 `_avg_prev(n)` helper，`avg_20` / `avg_50` 改用**前 N 日**（`volume.iloc[-(n+1):-1]`）排除今日，避免今日放量時稀釋自己的 ratio；並處理 NaN / 歷史不足的邊界。(2) `screen.py` CSV 加 `volume_today` / `avg_20d` raw 欄位；(3) `bridge.py` momentum row 帶 `_safe_float` 版 volume_today / avg_20d。(4) 動能頁表格量比欄加 `.vol-cell` `cursor:pointer` + 虛線底線提示可點 → 觸發 `openVolumePopup(r)` modal。(5) Modal 內容：raw 今日量 / 20 日均量（人類可讀 M/B 格式 via `_fmtShares`）/ 量比數字帶色碼；若當下為 ET 盤中 9:30–16:00 → 顯示「全日推估」區塊（ET 時間、經過比例%、線性推估全日量、推估量比套 spike 門檻 2×/3× + 三色警示）；盤前/盤後/週末顯示 closed note，兩端邊界（<2% 或 >98%）顯示 too_early。警語提醒實際量非線性分布。(6) `_etNowInfo()` 用 `Intl.DateTimeFormat('America/New_York')` 解析 ET 日期/時間/weekday，計算 570–960 分鐘區間的 elapsed_fraction。(7) i18n zh/en 共 13 個 popup 字串。(8) Modal 關閉：X 按鈕 / 背景點擊 / ESC 三種。bump VERSION 1.20.0 → **1.21.0**（minor，算法修正 + 新互動）。重跑 full SP500 scan → 501 rows 帶新 volume 欄位。
> **Last Session Note (prev sector)**: 動能選股加 **GICS 產業分類維度**。從 Wikipedia S&P 500 表抓 `{ticker: GICS_sector}` 對照 → `skills/momentum-monitor/scripts/universes/sp500_sectors.json`（503 ticker × 11 sector：Industrials 79 / Financials 76 / Info Tech 73 / Health Care 58 / Cons Discr 48 / Cons Staples 36 / Utilities 31 / Real Estate 31 / Materials 26 / Comm Svcs 23 / Energy 22）。`screen.py` 加 `_SECTOR_MAP` 載入 + CSV `sector` 欄；`bridge.py` momentum row 帶 `sector`（missing → "Unknown"）。Dashboard filter panel Stage/搜尋欄改 3-col grid 中間塞 Sector dropdown（單選，11 option）；`_state.filter.sector` + `matchesFilter` check；每個 PRESETS 補 `sector:'any'` 保持跨產業；row 的 Ticker cell 下方加 9px 灰色 subscript 顯示中文產業名（Unknown 不顯示避免雜訊）。i18n `sectors_map` zh 11 個全翻 + en 用縮寫版（Cons. Discr. / Comm. Svcs. 省空間）；`filter_sector` label 中英版。跑 full S&P 500 fresh scan → data.json 501 rows 全帶 sector，distribution 正確。bump VERSION 1.19.0 → **1.20.0**（minor，新資料維度）。
> **Last Session Note (prev ux)**: 動能選股 filter panel 加 **6 組預設策略** 按鈕（新手友善），每個一鍵套用經典 filter 組合 + hover tooltip 解釋「找什麼、為什麼」。(🔥 強勢突破 Stage2+黃金交叉+量擴-超買 / 💪 穩定上升 score≥65+Stage2-過熱 / 📉 上升股回檔 Stage2+RSI 超賣 / ⚡ 軋空候選 squeeze_candidate / 🎯 無過熱精選 score≥60-過熱-拋物線 / 📊 全部 = reset)。`page-momentum.js` 新 `PRESETS` dict + `applyPreset(key)`（覆蓋 state 避免累加混淆）+ `renderPresetRow` 呼叫進 `renderFilterPanel`。`momentum.html` filter panel 最上方加 `#f-presets` 按鈕列 + `.preset-btn` CSS（灰色 pill hover 轉綠）。i18n zh/en 每個 preset 有 label+tip 物件（tooltip 講完 filter 值也講交易意義）。`translate()` 切語言時重 render preset row 讓 tooltip 跟著變。bump VERSION 1.18.2 → **1.19.0**（minor，新功能）。
> **Last Session Note (prev bugfix 真正根因)**: 各頁資料載不出來（Safari `JSON.parse` 拋 SyntaxError "The string did not match the expected pattern"）根因找到 —— **data.json 含 `NaN` token**（例：新上市 `Q` ticker 歷史 < 200 天，`ma200` = NaN，Python `json.dump` 預設允許 NaN 字面量但 **JSON 規範不允許**，瀏覽器嚴格拒絕）。Chart.js revert 其實無關（已把 Chart.js CDN 加回 index/sector/momentum.html，`page-momentum.js` 回到同步 openHistory）。修三層：(1) `momentum.py` `_ma_block` 新 `_clean()` helper 在 MA 值取出當下就 `!= NaN` 判定（因為 `bool(NaN)` 是 True 會騙過舊三元式），none 的就設 None；末端 `round()` 加 None 保護；(2) `bridge.py` 新 `_safe_float(v)` 處理 `'nan'` 字串 + NaN/Infinity float + 新 `_clean_nan(obj)` 遞迴 sanitizer；(3) `json.dump(..., allow_nan=False)` 最後保險桿，下次真有漏網 NaN 會當場拋 ValueError 而不是寫出壞 JSON。另移除之前寫的 `UI.isFetchCancellation` suppression（太貪婪把真錯誤也吞掉 → 頁面空白），helper 保留但不 callers。逐步 log 儀器化完成使命拿掉。重跑 bridge → data.json 乾淨（`Q.above_ma200_pct=null`）。bump VERSION 1.18.1 → **1.18.2**（patch，critical bug fix）。
> **Last Session Note (prev plan A)**: 動能 scan **即時進度** (plan A)。`dashboard_server.py` 的 `_worker()` 從 `subprocess.run(capture_output)` 改 `Popen` + 背景 reader thread，regex `_MOM_PROGRESS_RE` 解析 screen.py stderr 的 `[screen] 150/503 (0 errors, 23 cache hits)` 逐行更新 `_momentum_state.{done,total,errors_count,cache_hits_count}`。Reader 也即時抓 `CSV:` 路徑（用 ref dict 避免 nonlocal）+ 保留最後 50 行供 error 回報。Timeout 用 `proc.wait()` + `proc.kill()` 替代舊 `subprocess.TimeoutExpired` 處理，乾淨。前端 `showScanIndicator` 加第 4 個 `progress` 參數，running 狀態時 status 文字變成 `SCANNING  150/503`；hover tooltip 顯示 `scanning sp500… · cache hits 501 · fetch errors 2`。實測 POST → 3s 拿到完整進度（501 cache 命中 + 2 fetch 失敗）。另順手加 `loadMomentumData` catch 的 stack trace（`e.stack.slice(1,3)` + `console.error`），下次 user 再遇到 pattern error 可直接定位行號。bump VERSION 1.17.2 → **1.18.0**（minor，即時進度新功能）。
> **Last Session Note (prev perf)**: Chart.js 載入優化。(A) 移除 `index.html` + `sector.html` 的 Chart.js CDN 引用（兩頁都沒在用，純遺物）→ 每次開這兩頁少抓 ~80KB。(B) `momentum.html` 改 **lazy-load**：移除 eager `<script src="chart.js">`，`page-momentum.js` 加 `loadChartJs()` helper（動態 append script tag，Promise cache 只載一次），`openHistory()` 改 async 並 `await loadChartJs()` 後才 `new Chart()`。首次開動能頁省 80KB，第一次點 ticker row 開歷史走勢時才抓（帶 error 處理）。順便清 `page-sector.js` 註解（移除過期的「Requires Chart.js」聲明）。bump VERSION 1.17.1 → 1.17.2（patch）。
> **Last Session Note (prev ui)**: 動能選股的 scan progress 從全寬 banner（top-16 fixed，蓋 header 下方）改 **header 右上角 compact pill**（`#scan-indicator`）—— loader-2 icon + SCANNING/REFRESHING/DONE/ERROR 狀態文字 + MM:SS elapsed 一行，不擋內容。done/error 5 秒後自動隱藏（`_indicatorHideTimer` clearTimeout 避免洩漏）；點 pill 本身可立即隱藏；phase 文字改當 tooltip 用（hover 顯示）。舊 `showScanBanner/hideScanBanner` 保留為 alias 以減少 churn。順便澄清 user 的一個誤會：**開網頁不會 auto-scan**，`loadMomentumData` 只讀 data.json、`checkExistingScan` 只 GET /status（兩者都不觸發 scan）—— 之前看到 banner 是因為上次按 rescan 還沒掃完。感覺變慢是新 filter panel 的 DOM + Chart.js CDN 抓 ~80KB 造成，不是 scan。bump VERSION 1.17.0 → 1.17.1（patch）。
> **Last Session Note (prev ux)**: 動能選股頁改 **客戶端即時篩選**（回應 user 挑戰：screener 反正全撈 503 檔，min_score 只是最後過濾 → 那就伺服端不過濾、客戶端毫秒篩）。`momentum.html` 新 filter 面板：Score slider（0-100 step 5）/ RSI range（min + max 獨立 input）/ Stage select（Any / Stage 1-4）/ 代號搜尋 / 必含訊號 chips（9 個：stage2 / 量擴 / 黃金交叉 20-50 / 50-200 / 爆量 / 軋空 / RSI 超賣回檔 / low/high short）/ 排除警告 chips（6 個：RSI 超買 / 拋物線 / stage4 / 量縮 / 死叉 20-50 / 50-200）。`page-momentum.js` 拋掉舊 preset FILTERS dict，改 `_state.filter` object（`minScore/maxScore/minRsi/maxRsi/stage/requiredSignals:Set/excludedWarnings:Set/search`）+ `matchesFilter(r)` + `renderFilterPanel()` + `renderSignalChips/WarningChips`。所有 UI 控件 oninput/onchange → 更新 state → renderTable()，**完全不打 API**。表格 rank 重新計算（反映當前 filter view 的排名）。`triggerRescan` 移除 `min_score:60` / `top:30`，Dashboard 按「重新掃描」後 server 回全 503 檔，客戶端愛怎麼切怎麼切。新「重設」按鈕恢復預設 filter。filter-chip CSS 新增（綠色 active = required signal / 紅色 active = excluded warning）。i18n 10+ 新字串 zh/en。bump VERSION 1.16.0 → **1.17.0**（minor，重大 UX 改善）。Server 端不用改（`_build_screen_cmd` 本來就是 param 沒帶就不加 flag）。
> **Last Session Note (prev RSI)**: 動能選股加 **RSI-14（Wilder smoothing）**。`momentum.py` 新 `_rsi_14()` + `_rsi_block()`（zone: oversold/neutral/bullish/overbought）輸出加 `rsi` 區塊；signals 新增 `oversold_rsi`（RSI<30 **且** Stage 2 uptrend 才觸發，下跌股超賣是弱勢非機會）；warnings 新增 `overbought_rsi`（RSI>70）。**RSI 不進 composite score** 保留舊 score 可比性（避免跟 trend_acceleration 重複計入）。`screen.py` 加 `--min-rsi` / `--max-rsi` CLI flag，CSV + MD table 加 RSI 欄；`journal.py` snapshot 寫 `rsi_14` / `rsi_zone`；`bridge.py` 帶到 `momentum_screen.rows`。Dashboard 加第 11 欄 RSI 帶 tier 色碼（>70 紅 / 50-70 綠 / 30-50 黃 / <30 藍）；i18n 兩個新 signal 中英對照（RSI 超賣回檔 / RSI 超買）。新 `journal.py clear [--yes]` 子命令（互動確認防誤刪）。用 `clear --yes` 清空舊 176 筆 journal + stats（舊資料沒有 rsi_14 欄位，重新累積確保 signal stats 一致）。bump VERSION 1.15.4 → **1.16.0**（minor，新欄位 + 新 signals + journal schema 升級）。
> **Last Session Note (prev i18n)**: 動能選股 signals / warnings / stage / composite label 全部加 zh+en 翻譯表（`i18n.js.momentum.{signals_map, warnings_map, stages_map, labels_map}`，各 8/5/5/5 筆），`page-momentum.js` 加 `sigLabel/warnLabel/stageLabel/labelText` helper，table row + Journal stats 兩邊都套。Label pill 的 CSS class 維持英文 key（`.label-BULLISH` 色碼），顯示文字翻譯。原始 key 加 `title=` 保留 tooltip 對照。未登記 key fallback 為 `replace(/_/g, ' ')` 不爆。切語言由既有 `UI.boot reload` hook 自動觸發 `loadMomentumData` → re-render。bump VERSION 1.15.3 → 1.15.4（patch）。
> **Last Session Note (prev bugfix)**: dashboard_server `HTTPServer` → `ThreadingHTTPServer` —— 1.15.1 雖然把 scan 丟背景執行緒，但單執行緒 server 處理 request 排隊，跑 scan 時 poll+切頁+data.json 撞一起就卡幾秒。改多執行緒後每 request 獨立，實測 5 並發 request 全部 <4ms（scan 同時在背景跑）。另加 `_positions_lock` 防並發 POST positions.json race。`srv.daemon_threads = True` 確保 Ctrl+C 不等 in-flight request。bump VERSION 1.15.2 → 1.15.3（patch）。
> **Last Session Note (prev ui)**: 動能選股 score 欄從純數字改 **10 格 battery UI** —— cells 1-3 紅（0-30）/ 4-5 黃（30-50）/ 6-7 綠（50-70）/ 8-10 藍（70-100），未填格灰，最後一格 partial 用 linear-gradient 渲染（score 62.5 → 6 滿 + 第 7 格 25% 綠）。右側保留數字 `62.5` 精度參考，顏色跟最高填滿 tier 一致。`momentum.html` 加 `.score-battery`/`.cell`/`.score-num` CSS；`page-momentum.js` 新 `scoreBatteryHTML(score)` + 常數 `BATTERY_COLORS` / `BATTERY_UNFILLED`，`rowHTML` 呼叫之。NASDAQ-100 universe 一度考慮但 user 挑戰回「真的需要嗎」→ 確認 S&P 500 和 NASDAQ-100 重疊 ~85%（獨有 10-15 檔），當前階段不需要加；journal universe 欄位 / dedupe 邏輯同步省略。bump VERSION 1.15.1 → 1.15.2（patch，UI 改動）。
> **Last Session Note (prev bugfix)**: 動能頁 **async scan** 修復（1.15.0 單執行緒 `HTTPServer` 碰上同步 `subprocess.run(screen.py)` 會卡整個伺服器 40-60s，使用者反映「按下重新掃描整個網頁不動」）。`dashboard_server.py` 改背景執行緒 pattern（仿 `_preflight_state`）：`_momentum_lock` + `_momentum_state{status, phase, started_at, ended_at, csv_path, error}`，POST `/api/run-momentum-screen` 立即回 202 + state snapshot，worker 跑 screen.py → update state to `bridging` → 跑 bridge.py → `done`；新增 GET `/api/run-momentum-screen/status` 帶 `elapsed_sec`。前端 `page-momentum.js` 加 `triggerRescan` POST + `startScanPolling` 1.5s 週期 poll，固定 `scan-banner`（top-16 sticky）顯示 loader icon + `SCANNING/REFRESHING/DONE/ERROR` 色碼 + MM:SS elapsed + phase 文字 + done/error 時可關閉按鈕。`checkExistingScan` 頁面進入時 poll 一次，若別的 tab 正在跑 scan，也顯示同個 banner。重複點擊防呆（`btn.dataset.busy`）+ 409 狀態降級為「已有 scan 在跑，繼續 poll」。i18n zh/en 補 banner 字串。bump VERSION 1.15.0 → 1.15.1（patch，bug fix）。下階段依序：(A) 跑全 S&P 500 看 score 分布確認 filter 合理、(B) 考慮加 nasdaq100 universe、(C) 等 journal 累積 4-6 週接 edge pipeline。
> **Last Session Note (prev)**: momentum-monitor **Scope A.5（Dashboard 頁）+ Scope B（Forward-return journal）**。(A) 新增 `skills/momentum-monitor/scripts/journal.py`（~350 行）3 子命令：`snapshot <csv>` append 到 `journal/journal.jsonl`（one JSON / snap×ticker；entry_price + signals + returns.5d/20d/60d + mae_20d/mfe_20d）；`update` 掃 journal 找 target_date ≤ today 的 pending return bucket，按 ticker group 一次 yfinance 抓完整 history range，切片填返報（含 MAE/MFE high/low 搜尋）；`stats` 按 signal / score_bin / stage 分組算 n / win_rate / mean / median / p25 / p75，寫 `journal/stats.json` 兼印 MD top-15 signal 勝率榜。`screen.py` 加 `--journal` 旗標 post-scan auto-append。(B) `bridge.py` 加 `ingest_momentum_screen()`：讀最新 screen_*.csv + 最近 30 份 CSV per-ticker score 歷史 + stats.json → `data.json.momentum_screen = {rows, history_by_ticker, journal:{stats}}`。(C) 新增 Dashboard 頁 `momentum.html`（~230 行）+ `page-momentum.js`（~340 行）：meta strip（snapshot time / matched / journal total / snapshot count）+ filter chips（Bullish only / Fresh breakout / Squeeze / Exclude blow-off）+ 可搜尋 table（rank/ticker/price/score bar/label/stage/vol×/vs200MA/signals/short）+ 點 row 彈 Chart.js 30 天 score 走勢 overlay + Journal stats 雙欄（by signal 20d winrate bar / by score bin 5-20-60d mean）。`utils.js` NAV_ITEMS 加 trending-up icon，`i18n.js` zh/en 雙語 40+ 字串。(D) `dashboard_server.py` 加 `POST /api/run-momentum-screen`（body 支援 universe / tickers / min_score / signals / journal 等）→ 同步跑 screen.py → 跑 bridge.py → 回 csv_path，前端 refresh 按鈕用之。Smoke test：journal snapshot 10 + 3 = 13 entries / update 全 pending / stats 0 matured（day 0 正常）。bump VERSION 1.14.0 → 1.15.0（minor，新 Dashboard 頁 + 新 journal）。下階段（Scope C）等 journal 累積 4-6 週 signal n ≥ 30 再接 edge-candidate-agent / edge-pipeline-orchestrator / backtest-expert。
> **Last Session Note (prev)**: momentum-monitor **Scope A — 批次動能選股 screener**。新增 `skills/momentum-monitor/scripts/screen.py`（~240 行），直接 import `momentum.py` 的 `analyze()`，`ThreadPoolExecutor(workers=15)` 平行跑 universe，充分 reuse 15-min cache。CLI filter：`--min-score` / `--max-score` / `--stage` / `--label` / `--signal X`（可重複 AND）/ `--exclude-signal` / `--exclude-warning`。Universe 三來源：`--universe sp500`（內建 `scripts/universes/sp500.txt` 503 ticker，Wikipedia 抓）/ `--tickers AAPL,MSFT,...` / `--tickers-file path.txt`。輸出 ranked MD table + `cache/screen_YYYYMMDD_HHMM.csv`（完整數據）。Smoke test 10 mega-cap fresh 0.9s → 全命中 cache 0.0s；filter `--stage "Stage 2 uptrend" --min-score 55` 正確篩出 INTC+AMD。新增 slash `/momentum-screen`（`.claude/commands/momentum-screen.md`）+ CLAUDE.md 觸發方式。bump VERSION 1.13.0 → 1.14.0（minor，新 Scope A 功能）。下階段選項：Scope B（具體策略 backtest.py + 接 backtest-expert 驗證 robust）或觀察幾週實際選股結果後再決定。
> **Last Session Note (prev)**: 新 skill `momentum-monitor` — 單 ticker 動能/流量讀數：volume 今日 vs 20/50D avg + spike 偵測（>2x MILD / >3x HEAVY / last-10d spike days）、MA 結構（20/50/200 Weinstein 4 stage 分類 + last-30d golden/death cross 事件偵測）、short interest（shares_short / % float / days-to-cover / squeeze candidate flag）、composite score 0-100（四組件等權：volume_flow / ma_stage / short_squeeze_potential / trend_acceleration）。Per-ticker file cache TTL 900s。CLI 旗標 --no-cache / --max-age。Smoke test TSLA (WEAK 41.2，death_cross_50_200) + AMD (NEUTRAL 58.8，fresh golden_cross_20_50 + Stage 2 uptrend)。觸發方式 3 種：直接 `python3 skills/momentum-monitor/scripts/momentum.py TSLA` / 自然語言「動能 TSLA」/ slash `/momentum-monitor TSLA`（`.claude/commands/momentum-monitor.md` 新增）。暫不接入 investment protocol Phase 2 Technical，user 先試跑再決定。bump VERSION 1.12.3 → 1.13.0（minor，新 skill）。
> **Last Session Note (prev)**: 分析 INTC → HOLD（final_score +0.092，CANCEL）。V4.8 PARALLEL_SUBAGENT 4/4 isolated；四 analyst 分歧明顯（Fund SELL -2.5 / Sent HOLD 0 / News BUY +3 / Tech HOLD +1）raw +0.108；Red Team STRONG_COUNTER（counter_evidence=4）→ ×0.85 penalty = +0.0918；macro -1 + sign(+) mismatch → CONTRARIAN 不 ×0.9 → final +0.092。Burry 25 WARNING（FCF yield -1.3 / forward PE 65x / 沒有 contrarian 反向 bonus 因為股價 +85% YTD 已被市場追捧）。觀察：Q1 earnings 2026-04-23 + RSI 冷卻 < 60 + 回測 MA20/MA50 叢集 $48-53 → 重評。關鍵風險：RSI 89.7、83% above MA200、binary earnings 5 天內、AI theme Exhausting。bump VERSION 1.12.2 → 1.12.3。
> **Last Session Note (prev)**: 卡片新增股價顯示 — bridge.py 加 `_batch_current_prices()` yfinance 抓所有 recent_analysis tickers 即時價（positions 已有價的 reuse，避免重複抓），填入 data.json 每筆 `current_price`。Protocol `phase5_export_schema.md` + `validate_session_export.py` 新增 `analysis_price` 必填欄位（分析當下快照），V4.8 session 寫入時從 Phase 2 Technical skill 抓取。卡片 header ticker 右邊顯示 `$XXX.XX`；若 analysis_price 存在且漂移 ≥ 0.5% 額外顯示 `+X.X%`（多頭綠 / 空頭紅），日期行補 `@ $原分析價`。bump VERSION 1.12.1 → 1.12.2。
> **Last Session Note (prev)**: 決策中心卡片去重 — `dedupeByTicker()` helper（保留每 ticker 最新 time 的 entry，透過 drill-down overlay 仍可看歷史），在 `renderCards` 與 summary stats（execCount / waitCount / avg_conf / avg_rr）都套用。卡片日期右側加「↻ +N」徽章（N = 該 ticker 歷史總數 −1），提示使用者點擊可看之前分析。`_allAnalysis` 全量保留供 drill-down 用；只 `_watchlistData` + render 輸出去重。bump VERSION 1.12.0 → 1.12.1。
> **Last Session Note (prev)**: Sector Protocol V1.2 → V1.3（架構補齊，與 investment V4.8 / news V2.1 同步）：(A) Phase 4a 三 agent 提案（Sector Rotation / Theme Intelligence / News Catalyst）改為 **3 個平行 Agent subagent**，isolation contract + per-lane data slice + `subagent_isolated` sentinel + fanout_mode PARALLEL_SUBAGENT / PARTIAL_FALLBACK / FULL_FALLBACK / INLINE 階梯；(B) Phase 4b Devil's Advocate 改為**獨立 subagent**（只收 Phase 0-4a 輸出 + tail-risk 結果、看不到自己前文），`risk_scenario` 要求 falsifiable (IF/WITHIN/THEN) 格式；(C) 新增 `sector/scripts/validate_sector_intel.py`（~160 行，檢測 protocol_version、`_phase0/_phase1/_phase3` 必填 key、`top_catalysts` ≥ 5 筆、HOT sector 必有 proxy_etf、V1.3 fanout metadata）；(D) schema.md 頂層加 `phase4_fanout_mode` / `degraded_agents`，Phase 4a/4b 加 `subagent_isolated`，header 標 Schema Version V1.3。Phase 5 Step 2 新增 validator gate（rc=0 才可進 Step 3 MD 報告）。Schema 已有（V1.2 就抽離了）不用重做。bump VERSION 1.11.0 → 1.12.0（minor）。
> **Last Session Note (prev)**: News Protocol V2.0 → V2.1（Stage 2/REVIEW 四 agent per-agent batch subagent、Phase 4 digest schema 抽離至 `digest_output_schema.md` + validator）。Validator 首跑抓到 2026-04-16 DIGEST 丟 52/77 shallow verdicts。bump VERSION → 1.11.0。
> **Last Session Note (prev)**: Phase 5 schema 抽離 — investment/phase5_export_schema.md + validate_session_export.py。Protocol Phase 5 正文瘦身（-70 行）指向 schema + validator gate。MSFT V4.8 entry 補頂層 ticker/final_action/date mirrors（validator 首發捕獲）。bump VERSION → 1.10.0。
> **Last Session Note (prev)**: 分析 MSFT → HOLD（final_score -0.09，CANCEL）。V4.8 PARALLEL_SUBAGENT 4/4 isolated；四 analyst 分歧（Fund +1 / Sent -1 / News +2 / Tech -2）raw -0.1 × macro 0.9 ALIGNED = -0.09。Burry 41.6 NEUTRAL，Red Team MODERATE_COUNTER。觀察：MA200 $470 收復或 Q3 earnings beat → 重啟評估。bump VERSION → 1.9.10。
> **Last Session Note (prev)**: V4.8 MU (2026-04-18) 同樣被 Claude 寫成 legacy shape，缺 rr_ratio / TP / SL / entry_aggressive / entry_conservative / watch_conditions 等。從 reports/20260418_MU.md 回填後改寫成 V4.8 shape → bridge.py 重跑 → data.json 現在有 rr_ratio=2.13、TP $540 / SL $415、雙軌 entry、5 條 watch_conditions、binary_class=unknown。另修 i18n：CONTRARIAN / POS BINARY / NEG BINARY / ×1.15 CONSENSUS 4 個徽章加中文翻譯（逆勢訊號 / 正向事件 / 負向事件 / 四軍同向）。bump VERSION → 1.9.9。
> **Last Session Note (prev)**: V4.8 AMD legacy shape 修正同樣思路，protocol Phase 5 Schema 契約加強「禁止 legacy shape + HOLD/CANCEL 必填觀察欄位」。bump VERSION → 1.9.8。
> **Last Session Note (prev)**: `dashboard_server._extract_error_from_log` — rc!=0 時解析 stream-json log 尾端的 `result` event `.result` 欄位，取代 "exit code 1"。bump VERSION → 1.9.7。
> **Last Session Note (prev)**: Toast 改版（極簡卡片 + 左邊色條 + 關閉 ✕）+ 預設 6/8/10s；RISK_TOLERANCE 前端 localStorage + sidebar L/M/H chip。bump VERSION → 1.9.6/1.9.5。
> **Last Session Note (prev)**: RISK_TOLERANCE 從前端帶給 dashboard_server — localStorage `dash_risk_tolerance` + sidebar L/M/H chip 循環；POST body 同步帶；V4.8 protocol 加非互動強制條款；CLAUDE.md 實作前確認規則加邊界。bump VERSION → 1.9.5。
> **Last Session Note (prev)**: 持久化 Debug Log — localStorage ring buffer cap 300 + DOMContentLoaded auto-replay + bridge/protocol handshake monitor + 動態 Clear 按鈕 + 10-line 高度限制。awaitBridgeAndReload 取代平倉 1.5s race。bump VERSION → 1.9.4。
> **Last Session Note (prev)**: market-sentiment-analyzer 加 file-based cache（TTL 15min），多 ticker 同 session 共用市場層，每 ticker 省 ~$0.1。bump VERSION → 1.9.3。
> **Last Session Note (prev)**: V4.8 TSLA 實測 11:23 / $4.00 / 31 turns。改動：PROTOCOL_TIMEOUT_SEC 600 → 1500；Dashboard confirm dialog 改 10-15min & ~$4；Phase 5 MD 報告委派 Sonnet 4.6 subagent（純排版、禁改決策數值）每次省 ~$0.5。bump VERSION → 1.9.2。
> **Last Session Note (prev)**: 決策中心 UX 升級：點卡片 → 橫向 scroll overlay 顯示該 ticker 所有歷次分析（buildCard 複用、日期近到遠、ESC/背景/✕ 關閉）；每張 card 右上 refresh icon + 計時；Global UI lock（server singleton → 所有 refresh/FLASH 按鈕同步鎖定）。bump VERSION → 1.9.1。
> **Last Session Note (prev)**: Investment Protocol V4.7 → V4.8 Parallel Blind Analyst Subagents（D）：Phase 2 四個 analyst 改 4 個 Agent subagent 平行；Burry 保留 inline；Isolation contract + subagent_isolated sentinel + PARTIAL/FULL_FALLBACK 階梯。bump VERSION → 1.9.0。
> **Last Session Note (prev)**: Investment Protocol V4.6 → V4.7 Anti-Self-Deception Patch（ABC）：Consensus Bonus 改 Red-Team-gated（NO_VIABLE_COUNTER 才 ×1.15、STRONG_COUNTER ×0.85）、新增 Phase 2.8 Red Team Adversary、Burry OVERRIDE_BURRY 強制成本化。另修 dashboard_server.py 漏 `import glob` 導致盤前檢查 500。bump VERSION → 1.8.0
> **Last Session Note (prev)**: 產業掃描 2026-04-18 → NEUTRAL 0.68；HOT=Industrials only (78)；Materials+Tech 雙雙 tail-risk 降級 HOT→WARM（consensus_warning + AI/Semis EXHAUSTING + SPY RSI 96.9 extreme）。Synthesized 60-75%（breadth 最保守）。bump VERSION → 1.7.2
> **Last Session Note (prev)**: 分析 BAC → STAGED_ENTRY 7%（雙軌 3.5/3.5）final_score +1.110；四 Agent 一致看多 + Burry WARNING 20.4 ×0.7；R/R 2.05。打破連續半導體集中。bump VERSION → 1.7.1
> **Last Session Note (prev)**: 啟動 News Protocol V2 重構（RSS 兩階段漏斗 + 4 agent 圓桌 + Dashboard 個股新聞按鈕）— 草擬中
> **Last Session Note (prev)**: 資料夾大整理 — archive/ 分類建立、過期 protocol/doc/log 歸檔、根目錄清潔；5 個 README + todolist 對齊 V4.6 現況；V4.6 session 前半段已完成雙軌 entry / STAGED_ENTRY / consensus bonus / directional macro / dashboard_server 定時刷新 / positions tracker / decisions.html 整合 / server-side mtime cache-busting

---

## Current State (2026-04-15)

- **Investment Protocol**: V4.8（V4.7 基礎 + Phase 2 四 analyst 平行 subagent 真獨立 + fallback 階梯 + degraded_mode 保護）
- **Sector Protocol**: V1.2（multi-file: main + phase_0/1-2-3/4-5/schema）
- **News Protocol**: V2（RSS 兩階段漏斗 + 5 agent 圓桌 + FLASH/DIGEST/REVIEW 三模式）
- **Dashboard**: index / decisions / sector / news 四頁（watchlist + history 已合併至 decisions；news 新增 reviewed/pending 切換 + 送審按鈕）
- **Positions Tracker**: `dashboard_server.py` + `/api/positions` + modal form + live_position overlay
- **Cache-Busting**: server-side mtime 自動注入（不再需要手動 bump `?v=`）
- **Auto Refresh**: `bridge.py` 每 5 分鐘背景刷新（可用 `DASH_REFRESH_SEC` 覆蓋）

---

## 🎯 活動 Backlog

### 路線 S — Skill 最小替代實作 + Review
**狀態**：4 個 missing skill 已建立最小可行實作並通過 smoke test，但需實戰驗證與閾值調整。
- [x] ~~**[S-BUILD-01]** `skills/market-sentiment-analyzer/` — yfinance VIX/SPY RSI + CNN F&G backend + PCR（~150 行）~~
- [x] ~~**[S-BUILD-02]** `skills/tail-risk-analyzer/` — 1y daily returns → kurt/skew/VaR/DD → fragility label（~120 行）~~
- [x] ~~**[S-BUILD-03]** `skills/portfolio-risk-manager/` — vol scaling + correlation + sector cap（~180 行）~~
- [x] ~~**[S-BUILD-04]** `skills/short-contrarian-analyst/` — Burry Score + T4 veto（~180 行）~~
- [x] ~~**[S-COPY]** 複製 9 個現有 skill 到 `skills/`~~
- [x] ~~**[S-REVIEW-01]** market-sentiment-analyzer 驗證：composite 63.9 (Greed)，VIX 18.2 NORMAL，CNN F&G backend 成功回傳 56.5；PCR endpoint 當前 null（CBOE JSON 不穩）— 可接受 fallback~~
- [x] ~~**[S-REVIEW-02]** tail-risk-analyzer 閾值校準完成：跑 7 檔 SPY/TLT/NVDA/TSLA/COIN/RIVN/BTC；重新加權 kurt 10% / skew 10% / var 15% / DD 30% / vol 35%（原本 kurt 30% 過高）；校準後 SPY/TLT=ROBUST, NVDA/TSLA=MODERATE, COIN/RIVN/BTC=FRAGILE ✓~~
- [x] ~~**[S-REVIEW-03]** portfolio-risk-manager 驗證：讀取 positions.json (3 筆) 成功，avg_corr=0.393 合理，Tech sector cap 正確觸發 → final cap 8.5%~~
- [x] ~~**[S-REVIEW-04]** short-contrarian-analyst 修正完成：~~
  - ~~D/E 單位：yf 一致返回 percentage（NVDA 7.26, KO 139.79, PG 68.72）→ 改為 always `/100`，NVDA 現在正確顯示 0.07~~
  - ~~FCF fallback：KO `freeCashflow` 回傳 -1.46B 錯誤，`operatingCashflow` 正確 7.4B → 加入 `if FCF<=0 and OpCF>0: FCF = OpCF * 0.85` fallback~~
  - ~~7 檔測試（NVDA/KO/PG/JNJ/TSLA/RIVN/COIN）Burry Score 分布 25-45 合理~~
- [x] ~~**[S-REVIEW-05]** 4 skill 整合測試完成：以 NVDA 為目標按 investment_protocol_v4_6 Phase 2/Phase 4 序列呼叫 4 skill，全部回傳合法 JSON，串接計算 final_position=4.46%（8.5% × 0.75 fragility × 0.7 Burry WARNING）。protocol 需手動指示 Claude 執行 `python3 skills/<name>/scripts/...` 而非自行模擬~~

### 路線 N — News Protocol V2（RSS 兩階段 + 4 Agent 圓桌 + Dashboard 整合）
- [x] ~~**[N-PROTO]** 草擬 `news/news_protocol_v2.md`~~
  - 兩階段漏斗：Stage 1 RSS shallow triage → Stage 2 WebFetch deep debate
  - Team 從 3 人擴至 5 人：News Collector + Bull + Bear + **Sector Analyst** + **Macro/Policy Expert** + Arbiter
  - Arbiter 加權：平權 25/25/25/25，或依新聞類型動態（FOMC→Macro 40%, Earnings→Sector 40%）
  - Stage 1 晉級門檻：`|score|≥3` OR `binary+within_48h` OR `HIGH credibility + |score|≥2`；硬上限 5 則
  - Stage 1 輸出「Triage 篩選表」給人類審核（可手動加選）
  - 只有 Stage 2 才能 patch `sector_intel.json` / `phase0.json`
  - `news_logs` verdict 新增欄位：`depth: shallow|deep`、`tickers_mentioned[]`、`sector_view`、`macro_view`
  - FLASH mode 保持單階段 deep
- [x] ~~**[N-RSS]** 撰寫 `news/fetch_news_rss.py`~~
  - 來源：Reuters / Bloomberg / Yahoo Finance / MarketWatch / CNBC RSS
  - 輸出：`news/news_logs/YYYY-MM-DD_raw.json`（標題 + 摘要 + source + timestamp + url）
  - 去重（headline 相似度）、時間視窗參數（default 24h）
- [x] ~~**[N-ARCHIVE]** `news_protocol_v1.md` 移至 `archive/old_protocols/news/`~~
- [x] ~~**[N-CLAUDEMD]** `CLAUDE.md` 更新 news protocol 路徑 → v2 + VERSION bump 1.7.0~~
- [x] ~~**[N-DASH-BTN]** `page-decisions.js` 每張卡 footer 新增 📰 FLASH 按鈕 → 複製單股 prompt 到剪貼簿 + toast~~
- [x] ~~**[N-DASH-NEWS]** `page-news.js` 更新按鈕合併 reload + 複製「新聞分析 DIGEST」prompt + toast~~
- [x] ~~**[N-TOAST]** `utils.js` 新增 `UI.showToast()` + `UI.copyToClipboard()` 共用元件~~
- [x] ~~**[N-I18N]** `i18n.js` 新增 `flash_btn` / `flash_toast` / `digest_toast` 鍵值（中英雙語）~~
- [x] ~~**[N-BRIDGE]** `bridge.py` 過濾 v2 `depth=shallow`；支援 `tickers_mentioned` / `sector_view` / `macro_view` / `news_type` 新欄位~~

### 路線 B — Calendar 頁面（財報 & 事件日曆）
- [ ] **[B-BRIDGE]** `bridge.py` 導出 `upcoming_binary_risks[]` + `sector_news_sentiment{}` 至 data.json 頂層
- [ ] **[B-PAGE]** 建立 `calendar.html`
  - 週曆視圖，顯示財報日期、FOMC、地緣政治 binary events
  - 每個事件顯示受影響產業 + direction（bullish/bearish/binary）
  - 資料來源：`_phase3.upcoming_binary_risks` + `earnings-calendar` skill
- [ ] **[B-SKILL]** 整合 `earnings-calendar` skill（FMP API），產出 JSON cache 讓 bridge 讀取

### 路線 C — Positions Tracker 強化
- [ ] **[C-IMPORT]** `import_firstrade_csv.py` — 解析 Firstrade 月結單 CSV → `positions.json`（避免手動輸入，安全方式取代非官方 API）
- [ ] **[C-CLOSE]** Dashboard 新增「平倉」動作：將 position status 改 closed，自動記錄 exit_price + realized_pl
- [ ] **[C-ADD]** 同一 ticker 加碼時提示「併入現有 avg cost」vs「另開 lot」兩個選項

### 路線 D — 效能優化（低優先）
- [ ] **[ARCH-11]** `lucide.createIcons()` debounce（`requestAnimationFrame` 批次）
- [ ] **[ARCH-12]** Chart.js 惰性載入（只在 sector.html 載入）
- [ ] **[ARCH-13]** marked.js 惰性載入（viewReport 觸發時才載）
- [ ] **[ARCH-14]** `innerHTML` XSS 防護（`escapeHTML()` helper，已有 `UI.escapeHTML`，套用到剩餘欄位）

---

## ✅ 已完成（session 2026-04-12 to 2026-04-15）

### V4.6 投資協議
- [x] 雙軌 entry（aggressive + conservative ranges）
- [x] STAGED_ENTRY / STAGED_EXIT 決策狀態
- [x] Consensus bonus ×1.15（4 agent 同向 + Burry 不 veto）
- [x] Directional macro multiplier（只作用於同向訊號）
- [x] 移除 Phase 3 VOLATILE × 0.85 雙重懲罰
- [x] HOLD 不再強制 Auto-REJECT，改交由 Phase 4 dual-track 彈性處理
- [x] Binary risk 三分類（positive / unknown / negative）
- [x] README + todolist 對齊 V4.6
- [x] `CLAUDE.md` protocol 路徑更新

### Sector Protocol V1.2
- [x] 主檔案 + 4 子檔拆分（main / phase_0 / phase_1-2-3 / phase_4-5 / schema）
- [x] 三層訊號合成（breadth + FTD + market_top → synthesized_exposure）
- [x] Phase 4c 決策樹 STEP A-G
- [x] Extreme Sentiment Playbook（Greed 防守 / Fear 逆向）
- [x] consensus_warning 三條件精確定義

### Dashboard 整合
- [x] 合併 watchlist.html + history.html → `decisions.html`（5 filter tabs: all/active/waiting/historical/positions）
- [x] Sidebar 更新（watch_radar + audit_history → decisions）
- [x] `decisions.html?view=...` URL 深連結支援
- [x] ARCH-4/5 DataStore singleton + 各頁改用 DataStore.get()
- [x] ARCH-7/8/9/10 各頁 inline script 抽出為 `page-*.js`（presenter 層）

### Server 與 Infrastructure
- [x] `dashboard_server.py` — static file server + `/api/positions` GET/POST/DELETE
- [x] Position modal form（ticker/date/price/shares/track/status/notes + delete per lot）
- [x] `bridge.py` 整合 positions.json：`live_position` overlay + yfinance 即時報價
- [x] Server-side mtime cache-busting（移除所有 HTML 的 `?v=` 硬編碼）
- [x] `bridge.py` 每 5 分鐘定時刷新（背景 daemon thread）
- [x] `open_dashboard.sh` 整合跑 `dashboard_server.py`

### 文件整理（2026-04-15）
- [x] 根目錄 stray 檔歸檔 → `archive/root_stray/`
- [x] 舊 investment protocols (v4_3/v4_4/v4_5) → `archive/old_protocols/investment/`
- [x] 舊 sector protocols (v1/v1_1/v1_2/v1_2_optimized) → `archive/old_protocols/sector/`
- [x] `reports/optimized/` → `archive/old_reports/`
- [x] `Dashboard/ARCHITECTURE_REVIEW.md` + `CHANGELOG.md` → `archive/old_docs/`
- [x] 舊 `session_export_*` + phase0 cache → `archive/old_invest_logs/`
- [x] 5 個 README 改寫對齊（root + investment + sector + news 已更新；CLAUDE.md 已對齊）

---

## 📋 Bridge 資料流對照（current）

| Protocol | 輸出 Log | Bridge 讀取欄位 | Dashboard 顯示 |
|---|---|---|---|
| `investment_protocol_v4_8` | `invest_logs/history.json` | `final_action`, `final_decision`, `final_score`, `entry_aggressive/conservative`, `consensus_bonus_applied`, `red_team_verdict`, `burry_override_active`, `phase2_fanout_mode`, `degraded_analysts`, `macro_alignment`, `staged_split`, `binary_classification`, `key_risks` | decisions 頁全部 tabs |
| `sector_protocol_main` (V1.2) | `sector_logs/*_sector_intel.json` | `market_regime`, `_phase0` (breadth/FTD/MT synth), `_phase1` (sectors[]), `_phase3` (binary_risks/trump_signals), `hot_sectors/cold_sectors` | index + sector + news binary sidebar |
| `news_protocol_v1` | `news_logs/*_digest.json` | `verdicts[]`, `trump_signals`, `upcoming_events` | news 頁 |
| `market-breadth-analyzer` | `breadth_cache/*.json` | 6 組件 breadth + trend | index 廣度 gauge |
| `ftd_yfinance.py` | `ftd_cache/*.json` | FTD state + quality score | index FTD card |
| `market_top_yfinance.py` | `market_top_cache/*.json` | top_score + zone + budget | index 頂部風險 card |
| `positions.json` | — | lots → avg_cost / unrealized_pct / live_position | decisions 持倉頁 + watchlist overlay |
