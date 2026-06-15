# Skills 稽核報告 — 2026-06-11

> 範圍：專案 `skills/`（24 個 + `_shared`）。證據：daily_update.sh / dashboard_server / bridge / protocol 接線 grep、cache 最新檔 mtime、git 90 天活動、`scripts/check_skills.py` linter、MARKET_INDEX.md 比對。

## 一、健康度總表

### 🟢 核心日常（daily_update.sh 接線、cache 新鮮、活躍）— 8 個

| Skill | 角色 | 證據 |
|---|---|---|
| market-breadth-analyzer | Step 1 廣度 | cache @ sector/breadth_cache 每日 |
| fred-macro | Step 4 宏觀 | cache 2026-06-11 |
| thematic-screener | Step 6 戰術雷達 | cache 06-10 |
| theme-detector | Step 6 前置主題 | cache 06-10、90d 10 commits |
| market-sentiment-analyzer | Step 9.x mood | cache 06-10 |
| retail-sector-pulse | Step 9.x 散戶脈搏 | cache（trending_tickers）每日 |
| momentum-monitor | Step 9.7 動能 screen | cache 06-10、90d 10 commits |
| short-term-target | 戰術層 predict/weekly | cache 06-10 |

### 🔵 Protocol lane（觸發式，prompt/script 由 `分析`/`產業掃描`/`財報` 呼叫）— 11 個

earnings-analyst（cache 06-04）、earnings-valuation-forecaster（06-03，V2.15 已接 dashboard 前瞻 button）、finnhub-client（06-10）、ic-memo-writer（V3.25，**未 commit**）、sector-analyst、technical-analyst、tail-risk-analyzer、portfolio-risk-manager、short-contrarian-analyst（Burry lane）、us-stock-analysis、market-news-analyst。
prompt-only lane 無 cache 屬正常；使用證據 = protocol 文件引用。

### 🔴 沒在用 / 殭屍 / 壞掉 — 5 個

| Skill | 問題 | 建議 |
|---|---|---|
| **earnings-trade-analyzer** | 0 接線（grep 全專案無引用，僅 earnings-analyst SKILL.md 一行提及）；最後活動 4/27 | 二選一：接進 earnings.html post-earnings tab（5 因子評分本身有用），或刪除 |
| **supply-chain-event-analyst** | 0 接線；供應鏈頁實際走 `scripts/nexus/supply_chain.py`；cache 僅一個誤跑 artifact（`--HELP_chain.json`） | 已被 Nexus 取代 → 刪除，SKILL.md 有用的 prompt 段落併入 nexus 文件 |
| **economic-calendar-fetcher** | 上游壞掉：FMP econ-calendar legacy endpoint 403（sector Step 2/3 因此 silent SOFT fail）| 修：換 FMP /stable 對應 endpoint 或 Finnhub calendar；修不了就拔掉 sector protocol 引用，別留 silent fail |
| **ftd-detector（skill 目錄）** | daily 實跑的是 `sector/ftd_yfinance.py`（複製改寫版）；skill 內 fmp_client 版閒置；且 ftd_yfinance.py 竟引用 `~/.claude/skills/ftd-detector`（user-level 路徑）— lineage 三頭馬車 | 整併：sector/ftd_yfinance.py 搬回 skills/ftd-detector/scripts/ 當唯一實作，sector 只留呼叫 |
| **market-top-detector（skill 目錄）** | 同上 — 實跑 `sector/market_top_yfinance.py` | 同上整併 |

## 二、可加強（現有 skill 品質債）

1. **`skills/MARKET_INDEX.md` 過時** — 只列 16/24 個；earnings-valuation-forecaster 標「未整合至 protocol」但 V2.15 已接 dashboard；缺 ic-memo-writer / retail-sector-pulse / thematic-screener / short-term-target / fred-macro / finnhub-client / momentum… 該檔自稱 source of truth，先修它。
2. **retail-sector-pulse SKILL.md 引用已退役的 `narrative-pulse-detector`**（linter WARN；narrative pulse V3.34 已退役且 user 判定無價值）— 清掉。
3. **fmp_client.py 複製四份** — earnings-trade-analyzer / ftd-detector / market-top-detector 各持一份 + `skills/_shared/`（git status 顯示常一起改）。收斂到 `_shared`，殭屍清掉後此債自動少一半。
4. **market-news-analyst** — WebSearch 舊式流程，與 news protocol V2（RSS→Triage→Debate）功能重疊度高；sector protocol 仍引用。檢視是否降級為 sector Phase 3 的工具函式，或乾脆讓 sector 直接吃 news_logs。
5. **ic-memo-writer 未進 git** — V3.25 功能整包在 working tree。commit。

## 三、缺口（值得補的新 skill）

按「掃描→分析→決策→持倉→復盤」找洞：

| 優先 | 缺口 | 理由 / 素材 |
|---|---|---|
| ★★★ | **kill-trigger monitor（推翻條件監控）** | V4.2 剛把 Red Team `IF/THEN/WITHIN` 條件上畫面，但沒有東西每天去「檢查是否觸發」。sector_intel devils_advocate + thesis registry invalidation 條件都是 deterministic 可驗證的（RS 轉負、PPI > x、財報後跌 >5%）。daily_update 加一步，觸發 → Dashboard 紅 banner。整個委員會閉環就差這塊 |
| ★★☆ | **insider/smart-money per-ticker** | sector 層有 smart_money_signals，但 `分析 [TICKER]` 沒有個股 insider/13F lane。FMP insiderTrades/form13F endpoint 都在。可做成 quant 輸入餵 Phase 2 |
| ★★☆ | **implied-move / options 前哨** | earnings 前瞻（V2.15）算 scenario 但沒有市場隱含波動對照 — binary risk ×0.70 降權現在是拍腦袋常數，IV implied move 可讓它變 data-driven |
| ★☆☆ | **position-sizer（規則化倉位計算）** | portfolio-risk-manager 是 prompt lane；缺 deterministic sizing 計算（ATR stop 距離 × 風險預算 → 股數）。exposure ceiling 已有，每筆 trade 的 sizing 還是人腦 |
| ★☆☆ | **economic-calendar 修復**（見上）兼補 earnings calendar 統一源 | calendar.html 已有 FMP confirmed earnings；macro 事件目前靠 sector Phase 3 LLM 手抓，修好 fetcher 可 deterministic 化 |

**不建議補**（探索期紀律，見 memory）：backtest/journal/edge-pipeline 類形式化工具 — user 明示策略還在變，先不固化。

## 四之二、活躍 19 skills 深度檢視（4 並行 agent 讀碼）

### 🔴 真 Bug（會 crash / 輸出錯資料 / 邏輯失效）

| # | Skill | 問題 | 修法 |
|---|---|---|---|
| 1 | **ic-memo-writer** | `compose.py:401` `quality_flags` 是 list（analyze.py 寫 `list[str]`）但 render_sec_6 呼叫 `.items()` → **任何有品質 flag 的 ticker 必 crash**（AMD/INTC/ORCL/GOOGL/MSFT cache 全都有 flag；之前 MU/NVDA 能跑只因 flag 為空）。moat string-drift 同類病 | isinstance guard ~4 行；另 `build_fact_pack.py:84` ticker 不符時 fallback `trades[0]` 會 hash 到**別家公司的決策** — 拿掉 fallback |
| 2 | **short-contrarian-analyst**（protocol 端） | v5_0 L585 期待 `*_pts` keys — 腳本根本不輸出；L638 T4 仲裁 CANCEL 門檻用舊 0-12 刻度套在 0-100 分數上 → **CANCEL 分支實質不可達** | 改 protocol JSON 欄位名 + 門檻改 0-100 刻度（<10 / 10-20） |
| 3 | **short-term-target** | `predict.py:665` `news_age_hr=0.5` 寫死，v2 算出的真實 age_hr 被丟棄 → SKILL.md 承諾的 news>8h/24h 新鮮度閘**永遠不會觸發** | 把 v2 age_hr 傳through |
| 4 | **retail-sector-pulse** | `trending_tickers.py:532` 市場話題比對用 `headline + source`（source 是**feed 名**不是內文）；`raw_summary` 在 process_post 被丟掉 → 宏觀話題 recall 砍半 + feed 名誤匹配 | 帶 raw_summary 過去、比對 headline+summary |
| 5 | **earnings-analyst** | `render.py:316` flag 描述表還是舊 key（`accruals_warning`），V3.17 新 key（`accruals_warning_negative` 等）→ §9 印生 snake_case 無說明（HPE/NOK cache 實證） | 補 3 個新 flag 描述 ~6 行 |
| 6 | **us-stock-analysis** | SKILL.md §Data Sources 教 lane 用 web search 抓數字 — **直接違反 protocol DATA SOURCE DISCIPLINE（web search FORBIDDEN）**；全文不提 lane 實際必跑的 analyze.py | 重寫 Data Sources 段 |
| 7 | **technical-analyst** | SKILL.md 整份寫成「收 chart 圖片」工作流，protocol lane 跑的 `analyze.py --json-only` 與必輸出欄位（smart_money_analysis/volatility/key_levels）隻字未提 | 補 lane-mode 契約段 |

### 🟡 浪費 / 脆弱（高價值修復）

**效能（每日白跑的網路/CPU）**
- thematic-screener `screen.py:136` — 每 ticker spawn 一個 `python3 predict.py` 子行程（интерп+import ~1-2s × 100+/日）→ 改 in-process import
- retail-sector-pulse `aggregate.py:313` — 55 個 predict 子行程**串行**跑（Step 9.5 最慢尾巴）→ ThreadPool ×8
- momentum-monitor `momentum.py:146` — 529 ticker × Yahoo `.info`（只為 short interest + marketCap，雙週才更新）→ 24h sidecar cache
- short-term-target `predict.py:685` — SPY benchmark 每 horizon 抓一次 ×3、每 ticker 重抓（~300 SPY hits/run）→ 抓一次切片
- finnhub-client `dual_fetch.py:186` — **整個市場** 120 天 earnings calendar 每 ticker 抓一次 → memoize 或帶 symbol filter
- earnings-analyst `fetch.py` — ~22 個 FMP call 純串行（7-10s）+ income-statement 重抓兩次
- weekly_review — 每 (日×ticker×horizon) 一次 yfinance history，1000+ 次 → 每 ticker 抓一次 30d

**靜默失敗（daily_update 看不見的壞）**
- fred-macro `fetch.py:1354` — 全 series 失敗回 stale cache 仍 rc=0 → Step 4 永遠 ✅
- market-sentiment `mood.py:383` — 全掛寫 `_partial` 骨架仍 return 0 → Step 9.3 永遠 ✅
- theme-detector — daily_update.sh:228 季度重跑 `>/dev/null 2>&1` 無 rc 檢查 → 失敗則舊 universe 餵 thematic 一整季
- breadth Step 1 在 fatal 群組 — TraderMonty 掛掉會**中止整個 daily run**，但 bridge 本來就有 stale fallback → 改 non-fatal
- forecaster `_load_real_rate` bare except → fred cache 壞掉默默用 4.5%（全部目標價 −18%）

**Cache 衛生**
- thematic enrich cache **8,386 檔**未清、breadth_cache 222 檔未清 → keep-last-N prune
- forecaster cache key 不分 pre-earnings/plain 模式 → 交替跑互相覆蓋永遠 miss（SKILL.md 說有 suffix，code 沒有）

**契約/文件漂移（量大，列代表）**
- fred-macro SKILL.md：12/13 series 實為 17、TTL 15min 實為 1hr
- thematic SKILL.md：`--top-themes` flag 不存在、`fred_alignment` 欄位不存在
- momentum SKILL.md：data_sources 還寫 yfinance（實為 FMP 主源）、缺一半 payload 欄位；step 9.7 沒接 `--journal`（文件承諾的 forward-return 迴圈沒在餵）
- short-term-target `weekly_review.py:123` — weights_version 永遠 "unknown"（讀錯層級）→ before/after 權重比較流程死的
- tail-risk SKILL.md 權重/門檻數字與腳本不符（腳本 2026-04 校準過、protocol 對、SKILL.md 舊）
- sector/phase_4-5.md 叫 DA 用「COVID 情境回測 >40%」— 腳本根本不算這個 → 不可執行指令
- market-news-analyst — SKILL.md 253 行寫 WebSearch 宏觀報告流程，protocol 實跑 fetch.py（FMP per-ticker 48h）— 同名兩個產品

### 跨 skill 結構債（一次修、多處受益）

1. **共用價格歷史 helper** — SPY/OHLCV 被 momentum、predict、thematic、etf_scanner 四套 cache 各抓各的（15min/4h/in-proc/無）→ 把 `technical_core.fetch_history` 升進 `_shared/`
2. **find-latest-earnings-cache 三份實作**（analyze/forecast/build_fact_pack）只有 forecast 的 regex 安全 → 升 `_shared/`
3. **RSI 三種算法**（Wilder EMA / 15-bar mean / etf_scanner 自製）→ 同 ticker 不同頁面數字不同 → 統一 technical_core.rsi_14
4. **SKILL.md「lane 契約」模式** — 4 個 prompt-lane skill 文件還活在 pre-protocol 人設，真契約只活在 v5_0 protocol 文 → 每個 SKILL.md 加「protocol lane mode」段

## 四、建議執行順序

1. **🔴 Bug 批**（半天）：ic-memo quality_flags crash + trades[0] 錯 ticker hash、short-contrarian protocol 刻度/欄位、short-term-target news_age、retail-pulse 比對欄位、earnings-analyst flag 描述
2. **靜默失敗批**（1-2hr）：fred/mood rc=0-on-degraded、theme-detector 季度重跑 rc、breadth 改 non-fatal、forecaster real_rate WARN
3. 清殭屍：刪 supply-chain-event-analyst、處置 earnings-trade-analyzer、整併 ftd/market-top 雙實作（小時級）
4. **效能批**（半天）：thematic in-process predict、retail-pulse ThreadPool、momentum sidecar、SPY 共用 helper、finnhub calendar memoize
5. 文件批：MARKET_INDEX.md + 各 SKILL.md 契約段 + lane-mode 模式（可分次）
6. 補 kill-trigger monitor（半天級，新功能價值最高）
7. econ-calendar 修復、insider lane、implied-move 視需求排
