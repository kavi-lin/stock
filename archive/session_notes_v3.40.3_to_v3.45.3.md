# Session Notes 歸檔 v3.40.3 → v3.45.3（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v3.45.3) — Price Framework Engine script 化 + Phase 2.4
- **起因**：protocol review 抓到 B1（P0）：3.45.x spec 累積 weighted percentile / CV / reverse DCF 迭代解，LLM inline 算不可靠，卻寫「PM inline deterministic 計算」。user 拍板：order 對調（先 script 後 #4）、script 整包。
- **`compute_price_framework.py`**：一個 call 算 4 block（fvs blend byte-identical / range / MHP / reverse DCF bisection）。ticker 給了且缺 vol → 自抓 FMP OHLCV（消 LLM 抄寫）。降級=data 非 failure → rc=0。
- **新 Phase 2.4**：phase order `0→1→2→2.4→2.5→2.8→3→4→4.5→5`。一次解 B2 時序 fudge：T5(2.5) 直接用 mhp_signal、Red Team(2.8) 直接收 kill_seed、Phase 3/4/4.5 引用既存輸出。**注意**：本來打算放 Phase 3 Step 0，發現 implied_expectations 餵 2.8 Red Team → 必須 2.4。
- **Phase 4.5 降格為封裝呈現層**；implied_expectations 歸屬 Specialist→engine；B3 常數註記（ERP 0.04 real vs 0.045 nominal，用途不同非筆誤）；convergence low-conf guard。
- **驗證**：full / degraded（1 anchor、無 vol、FCF<0、FRED 缺）/ live FMP fetch（AAPL σ=0.0143）三路徑 rc=0。
- **版號**：3.45.2 跳過（原配 #4 PT 去重，對調後移後）。**下一步**：#4（注入層剝 PT + pt_revision_momentum 改 engine/deterministic 算 + news_lane 文字持久化 + leakage classifier）。
- **檔案**：新 script + protocol（Phase 2.4 新章 + 4.5/T5/RedTeam/Phase3/4 措辭）+ schema + CLAUDE.md + VERSION×3。

## 🟢 Session Note (v3.45.1) — 估值層 external review P0+P1 批次
- **起因**：外部 AI model review V5.1 protocol 給 10 點建議。本批做 P0（bug）+ P1（advisory/sibling，零決策衝擊）。user 釐清 4 點全收。
- **#7 bug 修**：`high_conviction_long_zone` 是 dead code（band_lower 必 < current）→ 改 `band_point<LT AND mid_target>current AND current<LT×0.9`。
- **#1 `fair_value_range`**：anchor 分布 P25/P50/P75 + `range_verdict` 位置判定。解決「加權平均沒人信、分歧被銷毀」。退化 n<4→minmax、n<2→null。
- **#2 拆半**：CV + `agreement_grade` **純展示**進 P1（**不**接 Phase 4.6 cap，接線+winsorize 留 P2，待歷史分布校準門檻）。
- **#5 `implied_expectations`**：reverse DCF 現價隱含 5Y FCF CAGR。WACC=FRED10Y+0.045、FCF base=owner earnings、FCF≤0→null。餵 Red Team `red_team_kill_seed`。不進加權。
- **#6 shadow (option a)**：live anchor 仍 static ×15（weighted_fair_value 不變），shadow-log rate-linked 倍數。確認翻轉率後才切換。
- **契約鐵律**：`fair_value_summary` byte-for-byte 不動 → decision_lock / val_det / validator / 舊 entry 全相容。新 block 全 sibling、warning-only rc=0。實測 MRVL entry rc=0。
- **未做（待議）**：P2 改決策數學各項（#2 cap 接線 / #3 archetype+EV/Sales/EBITDA/PB anchor / #4 PT 去重 / #9 verdict vol-normalize）逐項 review；#8b DECAY backtest；#10 anchor 校準 cron（獨立 infra）。
- **檔案**：protocol / schema / validator / VERSION×3 + SESSION_NOTES。

## 🟢 Session Note (v3.45.0) — investment Phase 4.5 → Multi-Horizon Price Framework
- **起因**：user 提案把單點 `fair_value_summary` 擴成三時間框架（5d 機率帶 / 60d target / 長期 6-anchor），各用該尺度合適方法 + 三框收斂成交易語意，並補 protocol 原本沒定義的 trade_plan TP/SL 來源。
- **做法**：Phase 4.5 升級成 Multi-Horizon Price Framework（仍 inline deterministic、0 LLM 重評）。
  - 5d band = 波動率錨定（σ_daily·√5 ± 1.28 + drift 查表 + catalyst override + key_level 反射）。
  - 60d = 0.40 momentum + 0.35 pt_60d + 0.25 earnings_revision。
  - convergence → `mhp_signal` 4 態，餵 Phase 3 T5 reasoning + Phase 4 entry/TP/SL provenance。
- **契約零破壞關鍵**：`fair_value_summary` key/shape **不動**（被 ic-memo 11-field decision_lock + apply_det_shadow val_det + validator 鎖死）→ 新框架另存 sibling `multi_horizon_price_framework`，長期層引用不重算。MHP **不**進 decision_lock（derived/advisory）。
- **新缺料輸入**：technical_lane 加 `volatility` sub-block（atr_14 / hist_vol_20d_daily / momentum_20d_pct，deterministic FMP read，缺 → 降級不擋）。
- **validator**：MHP warning-only（rc 維持 0），驗 long_term_ref 一致性 + mhp_signal enum + sub-block 完整度。實測既有 V5.0 MRVL entry rc=0 + 印 degraded warning。
- **檔案**：protocol / schema / validator / VERSION×3。

## 🟢 Session Note (v3.43.0 + v3.44.0) — token 計量上線 + sector 三招砍 cache_read
- **起因**：user 要盤前檢查的 per-stage token 報表。診斷發現系統只記 per-model **call 數**、
  從不記 token；真 token 全在 agentic protocol(sector/news/invest)+ break-news debate 的
  stream-json log 裡沒被聚合。
- **盤前實測 (2026-06-09→10)**：daily_update.sh 全 deterministic = 0 token；TOKEN 消費 =
  news DIGEST $2.75 + sector $4.25 = **claude 今日 $7.00**（in 27.8K / out 77.6K /
  cache_read 3.09M → cache_read 佔 89%）。
- **v3.43.0 token 計量**：`llm_drivers`(LLMResult +5 token 欄 + `parse_stream_log_usage`) +
  `model_router`(per-model `tokens` dict、`_record`/`note_run(tokens=)` 累加、migrate 舊檔) +
  `dashboard_server`(run_protocol 結束解析 log→note_run) + sidebar 顯示 in/out/cache/$。
  **已重啟 dashboard server (PID 變)**，今日 $7 已 backfill。break-news daemon 重啟回常駐。
- **v3.44.0 sector**：解剖 sector log = 24 Bash turn、cache_read 16K→131K 雪球。三招(同 3.42.0
  invest 模式)：① `phase_prefetch.py`(NEW 0-LLM 並行聚合 9 取數→1 JSON，Phase 3 FAST PATH) ②
  4 lane + Devil's Advocate 加 `model="sonnet"`(Arbiter 留 Opus) ③ GLOBAL RULES 禁 fmp MCP
  ToolSearch。**決策邏輯零變動**。
- ⚠️ **未跑真實驗證**：phase_prefetch 結構測過(valuation/sector_news/sentiment/digest rc0)，
  但 econ/earnings calendar 撞 FMP **legacy endpoint 退役**(403→SOFT null，非本次 bug)；
  smart_money ~131 ticker 慢(timeout 調 360s)。**下次真實「產業掃描」需確認 FAST PATH 真省 turn +
  Sonnet lane 品質不掉**。

## 🟢 Session Note (v3.41.0) — Rec 11 熱區保守性鬆綁（首個決策層 weekly-review 調整）
- 依 REVIEW_2026-06-07 + 上週(05-31) READY 項，promote **TODO-001 + TODO-002 → Rec 11**：
  Pattern A（Semis HOLD-miss 86% N=22）+ Pattern B（CANCEL-miss 71% N=21）同根，miss avg runup
  +30.5% vs drawdown −3.2%（Rec 9 證實真錯過）→ 鬆綁 V5.0 decision band。
- 改 `investment_protocol_v5_0.md`：正分模糊區 `[0,+staged)` × `industry_top_30pct` ×
  `RISK_ON/BULL` → default HOLD 降為 `STAGED_ENTRY (hot_zone_probe)`，15bps 上限；cap 規則不 force CANCEL。
  **3 道硬保險**：regime guard / `decision_cap_active!=true` / `mandatory_risk_flags 空`；硬閘（Auto REJECT /
  burry≤1 / proceed_to_phase3=false）全部優先。
- schema 加 `hot_zone_probe`；validator §11 enforcement（4-case smoke 綠：valid rc0 / HOLD・20bps・cap 衝突 rc1）。
- ledger Rec 11 target_metric：Semis HOLD-miss<60% / CANCEL-miss<60% / deep-dive hit 不退；
  **Semis HOLD-miss 回升>70% → paused**（user 指定）。
- 順手修 `build_event_index.py` ledger loader（`startswith("active")`，補抓 Rec 10）→ active 7→8。
- ⚠️ **user 提示 2026-06 中旬將大幅回檔**：回檔期 regime 應轉 VOLATILE/SIDEWAYS → 規則自動 dormant；
  首兩週需確認 `hot_zone_probe` 觸發數 ≈0、Semis HOLD-miss 走勢。
- **待**：下次真實 `分析 [TICKER]` deep-dive run 帶 hot_zone_probe 欄做真實 smoke；下輪 REVIEW 評 Rec 11。
- 留待累積：TODO-003（momentum-screen 8-12週）/ TODO-009（News-decisive N≥40）/ TODO-011（強訊號 N≥15 精校）；
  TODO-010 flip 12% observe band，續觀察 1 輪。

## 🟢 Session Note (v3.40.8) — Market Mood scoring 修正
- 使用者指出 mood page 每天都是「偏樂觀」。查證：`Dashboard/market_mood.json` 有更新，但 CBOE raw put/call 抓不到時退回 CNN `put_call_options=96.6`，被當成 `pc_signed=+93.2` 強訊號，壓過 SKEW high、breadth/strength 弱、junk bond demand 低。
- 修：CNN put/call fallback 改弱 proxy（cap ±50、權重 0.10）；新增 `fg_quality_signed` 聚合 stock_price_strength / stock_price_breadth / junk_bond_demand，權重 0.15。
- 重跑 mood producer（需網路權限）與 bridge：`data.json.market_mood.mood.score` 從 `+36 Greed` 變 `+2 Neutral`。

## 🟢 Session Note (v3.40.7) — Break News 源整理：移除 StockTwits + 補 3 RSS

User 觀察 StockTwits 很少被選到、沒用 → 要求移除並找新 RSS。先驗證：StockTwits 每
cycle 抓 ~35 則但只 63/1304（~5%）bn files 以它為 primary source，幾乎純雜訊進 Raw 流，
claim 成立。`social_sources.py` 移除 `fetch_stocktwits` 函式 + `STOCKTWITS_*` 3 個 env
var + adapter-list entry（社群源剩 truth_social / reddit / bluesky / hacker_news /
google_trends）。新 RSS 先 live curl + 過專案 `fetch_feed` 驗證才接：Fed Press(HIGH)、
Nasdaq Markets(MEDIUM)、Benzinga(MEDIUM) 全部 200 + 有效 item + 日期新鮮 → 加進共用
`FEEDS`（9→12，news protocol 與 break news 同步受惠）。淘汰 WSJ（item 全凍結 2025-01-27
dead endpoint）、GlobeNewswire（外語 micro-cap 噪訊）、Fool/FT(301)、SEC(403)。
TODO BN-2 closed。

## 🟢 Session Note (v3.40.5) — 新聞戰情室卡片可點開原文
- 修：新聞頁卡片無法點開原文。`url` 在 `*_raw.json` 抓取階段有，但 triage/digest 只保留 `news_id`、丟掉 `url`。
- `bridge.py` `_raw_pub_map` 改回傳 `{published, url}`，`extract_news()` 用 `news_id` 重新 join url；`page-news.js` source_label → clickable `↗`（新分頁），舊 digest 無 url 時 fallback 純文字。
- 驗：當前 11 筆全帶 url，`data.json` 已重生。

## 🟢 Session Note (v3.40.4) — 短期雷達：產業趨勢榜可點 → 列出**完整**成分股（finvizfinance）

user 要 radar 產業趨勢榜「點產業列出該類**所有**股票」。`industry_trend` 只有產業漲幅、無成分股。
先做輕量版（heatmap 大型股，Solar 1/半導體設備 0），user 追問「免費 api 也拿不到嗎」→ 查到 **`finvizfinance`**
（theme-detector 既有依賴、免 key、公開爬）Screener 可 by-industry 撈**完整**清單 → user 同意升級完整版。

最終實作（完整版）：
- **server**：`GET /api/industry/<name>` → `finvizfinance` Screener(`filters_dict={'Industry':name}`) → `{ticker,company,sector,market_cap}` list
  + **12h TTL 快取**（`_industry_cache`，`INDUSTRY_CACHE_TTL_SEC`）+ lazy import 防呆 + `_INDUSTRY_NAME_RE` 驗證 + `unquote`（名稱含空白/&）。
- **`page-radar.js`** `showIndustryStocks()`：主打 `/api/industry/`（完整），失敗才 fallback `_ensureHeatmapIndustries()`（本地大型股）；
  chip 沿用 `analyze-ticker-btn`→深度分析；`_industryRow` 加 `data-industry`+clickable；click 委派 + 關閉。`radar.html` 加 `#ind-stock-panel`。
- 保留 `_finvizIndustryUrl()`「在 finviz 看全部」連結（雙保險）。

驗證（fresh server live test）：Communication Equipment 44 / Semiconductor Equipment & Materials 29（& 名稱 OK）/ Solar 22；
2nd call cached 即時；bad name 400。node/py syntax 全過。

⚠️ user 的**跑著的 server 需重啟**才有 `/api/industry` route（route 是 boot 時註冊）。需瀏覽器實點驗收。
finviz 偶爾擋爬 → 自動 fallback 本地大型股 + finviz 連結。

## 🟢 Session Note (v3.40.3) — TODO-011 止血：news-digest verdict 門檻（接 3.40.1 回測檢討）

接 3.40.1 回測檢討。user 問 TODO-011 現在改不改 → 建議「現在改」並執行。

**root cause（確定 bug 非假設）**：`verdict_news_digest` 用單股設計的 `HIT_THRESHOLD_PCT=2.0`
評 SPY 市場級 call。SPY 窗口內幾乎不動 ±2% → 強訊號全壓 neutral → news-digest hit 結構性 0%
（連兩週 0524/0531 列盲點卻沒人開 TODO）。

**為何敢直接改**：純回測 verdict 標籤規則,**不碰任何 live 決策 / protocol** → 零下單風險、可逆。
跟 TODO-001/002 protocol threshold（必須等 drawdown 驗收）本質不同。

**改動**：`scripts/verdict_rules.py` 加 `NEWS_HIT_THRESHOLD_PCT = 1.0`,`verdict_news_digest` 改用之
（deep-dive 2.0% 不動）。±1.0% 經現有 7 筆強訊號驗算最優（救回 05-14 看空 SPY−1.93%,不像 ±0.5%
製造 sub-1% 雜訊假 miss）。rebuild 後 hit **0→1**。→ Rec 10。

**剩餘（TODO-011 in_progress）**：N≥15 強訊號 digest 累積後 grid 精校 ±1.0% 值。
**同時補建 TODO-010**（verdict <100% 窗口翻轉追蹤,資料已存在 9 snapshot,缺 diff 工具,下輪可跑）。

⚠️ **並行 session 注意**：本分支有另一條 session 同時在動（momentum journal v3.40.2）。VERSION
被推進數次,我的 review 改動最終落 **3.40.3**（3.40.1 = drawdown+parser / 3.40.3 = news 門檻止血;
3.40.2 是 momentum journal 那條 session 的）。
