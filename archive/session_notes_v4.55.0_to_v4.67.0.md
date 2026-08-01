# Session Notes 歸檔 v4.55.0 → v4.67.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v4.67.0) — 2+1 評審制接線進 protocol 本文
- **起因**：使用者 OK 提案表（4 檔 +66 行）後動工。
- **做掉(firm)**：① `investment_protocol_v5_0.md` 新小節「最強檔不可用時的 2+1 補償」— Red Team 盲開 ×2 + referee（三問制、禁重寫、單份失敗退單軌）；② `sector/phase_4-5.md` Arbiter 降級模式註記（同判準、同 referee 規則）；③ MODEL_DISPATCH §6 標註已接線。
- **設計取捨（提案時已過目）**：referee 是第 3 個 fresh-context subagent 非 PM inline；**不動任何 schema/validator**（2+1 只在生成端，輸出照舊單份 JSON，分歧以 `[2+1: …]` 記在文字欄位）；只給 Red Team/Arbiter 兩個自由推理節點，lane 不納入（有 det_shadow 哨兵）。
- **觸發判準（可觀測）**：Agent tool `model` 可用值無高於 sonnet 的檔位 → 走 2+1；有 opus 的現在零成本零行為改變。
- **驗收**：兩檔小節落地 read-back；版本同步 SYNC OK。**無法現在實測**（需真的處於無高階檔環境），已在 LETTER 註記首次降級世界跑 protocol 時盯 referee 是否守三問制。
- **下一步**：backlog 剩 llm_review 300KB 索引預切段。

## 🟢 Session Note (v4.66.0) — Phase 5 報告決策數字改 script 注入（佔位符制）
- **起因**：使用者指示做 backlog ①「§11 verbatim 改 script 注入」。
- **定位修正（重要）**：動工前覆查發現 ic-memo §11 已是 `compose.py` deterministic 渲染＋SHA256 gate；真正 LLM 手抄暴露點 = protocol Step 4 Sonnet MD Formatter（validate_markdown_export 只驗 /3.0 /100 刻度格式，**值抄錯照樣過**）。教訓入 LESSONS.md。
- **做掉(firm)**：① `inject_report_facts.py` — 6 區塊佔位符（decision_summary/lane_scores/fair_value_anchors/kill_conditions/key_risks/watch_conditions）→ history.json 末筆 verbatim 注入；FACTS 標記 idempotent 刷新；N/A-safe；rc 0/1。② protocol Step 4 prompt 佔位符強制 + 新 Step 4.5（Step 5 validator 前）。③ `test_inject_report_facts.py` 33 asserts。④ OPS_COMMANDS §3/§7、DIAGNOSIS §三.1、LETTER 同步。
- **驗收**：33/33 PASS（含注入後過 validate_markdown_export --report 相容性）；真實 history 欄位形狀（含 HOLD/CANCEL None entry）比對過；版本同步 SYNC OK。
- **重點紀律**：5 日/60 日 advisory 數字仍由 Formatter 轉寫（漂移非致命）；決策關鍵數字 100% script 化。**下次跑 `分析 [TICKER]` 實戰驗證一輪佔位符流程**。
- **下一步**：backlog 剩 2+1 評審制接線進 protocol 本文（需先提案）；llm_review 300KB 預切段。

## 🟢 Session Note (v4.65.0) — 資料源健康檢查（daily_health.py）+ SESSION_NOTES 輪替定案
- **起因**：使用者定案 SESSION_NOTES「保留最近 10 個、其餘 archive/」（v4.64.1 執行）並指示繼續 backlog 第二項 = daily 資料源 health 摘要。
- **做掉(firm)**：① `scripts/daily_health.py`（0 LLM）— 17 源 artifact 新鮮度（14 auto + 3 manual 分級；超齡 3x FAIL、manual 只 WARN/MISS）+ `--strict`/`--json`。② `daily_update.sh` final banner 前自動印表（非致命）。③ OPS_COMMANDS §1 補指令；LETTER/TODO 對應項標完成。
- **驗收**：實跑三模式 rc=0、首跑即揪出 economic-calendar MISS（正是要抓的 silent SOFT fail）；受控 mtime 分支測試 6/6 PASS；`bash -n` daily_update.sh syntax OK；版本同步 SYNC OK。
- **重點紀律**：健檢只讀 mtime 不碰資料內容；新增資料源時要同步補 SOURCES 清單（LETTER.md 有註記）。
- **下一步**：backlog 剩 ① §11 verbatim 改 script 注入；② 2+1 評審制接線進 protocol 本文（需先提案）。

## 🟢 Session Note (v4.64.0) — Agent 治理層建立：CLAUDE.md 瘦身 + docs/agent-ops/ 全套
- **起因**：使用者「未來若只有 Sonnet/Opus/Haiku，要保持同等級產出」→ 總體檢 CLAUDE.md / 各 .md / skills，把調度與判斷規則外化。
- **診斷（詳見 docs/agent-ops/DIAGNOSIS.md）**：① 父層+專案雙 CLAUDE.md 每 session 雙載 ~35KB 且父層停在 V4.13 互相矛盾；② Ops Shortcuts 68 行測試指令 + trigger 表 changelog 式膨脹；③ CHANGELOG/SESSION_NOTES append-only 巨檔被收尾規則指定必讀寫；④ 殘留強模型依賴：§11 verbatim、Arbiter/RedTeam、llm_review 300KB。
- **做掉**：CLAUDE.md 178→74 行純路由；父層改指標檔；`docs/agent-ops/` 8 檔（DIAGNOSIS / OPS_COMMANDS / MODEL_DISPATCH / JUDGMENT / DELEGATION_TEMPLATES / MAINTENANCE / LESSONS / LETTER）；v4_8 歸檔+16 條引用清零；MARKET_INDEX 補 quant-backtest + weekly-tech-playbook；AGENTS/GEMINI 去重。
- **驗收**：fresh-context 對抗審查 13 findings 全修；60+ 路徑逐一 ls 核實；MAINTENANCE §2 版本同步驗證命令實跑 SYNC OK；read-back 13 檔落地。備份：`docs/agent-ops/backups/`。
- **下一步（LETTER.md 交接表）**：CLAUDE拷貝.md 待使用者確認刪除；§11 verbatim 改 script 注入；daily health 摘要；2+1 評審制接線進 protocol 本文。（SESSION_NOTES 歸檔已於 v4.64.1 完成：保留最近 10 個區塊，其餘在 `archive/session_notes_archive.md`。）

## 🟢 Session Note (v4.63.0) — 回測策略模板擴至 11 個（20 候選實測取前 10）＋策略卡片選擇 dialog
- **起因**：使用者「策略模板太少 → 找 20 種策略、預先跑回測、取前 10 名，UI 改 card view + popup dialog，卡片淺顯易懂圖文」。
- **選型（先實測後動工）**：scratchpad 原型以 20 候選策略對 12 檔（SPY/QQQ + 跨產業 mega-cap 10）跑 5y/10bps 同基準，**中位數 Sharpe** 排名（期間修掉 supertrend band NaN 污染永不出場 bug）。前 10：ma_cross 0.61 / roc_trend 0.61 / donchian 0.56 / obv_trend 0.54 / boll_reversion 0.53 / supertrend 0.49 / triple_ma 0.49 / rsi_reversion 0.45 / high_52w 0.45 / keltner 0.43;自家 momentum 0.42 第 11 仍保留（live cache 驗證 + 分數面板整合）。落選 9 個（chandelier/rsi2/stoch/zscore/boll_breakout/adx_trend/macd_cross/dip_buy/breakout_vol）不入 registry。
- **做掉(firm)**：① `backtest.py` STRATEGIES registry 11 模板 + `--params-json`（舊 flags 相容）+ `resolve_params` 轉型;**訊號改在完整歷史算完才切窗**（修 ma_cross MA200 warmup 被吃）。② `rank_strategies.py`（新）→ `data/strategy_rank.json`。③ `test_backtest.py` 29→68 asserts。④ server：cmd 改 params_json、requires 檢查只擋 None/空字串（cost_bps=0 合法）、`QUANT_BACKTEST_TEMPLATES` 白名單、`GET /api/backtest/strategies`。⑤ `backtest.html`+`page-backtest.js`：select → 卡片按鈕 + popup dialog（11 卡:icon/中英名/分類 badge/白話一句/迷你 SVG 示意/基準 badge;ESC/backdrop/鍵盤）、參數表單 TEMPLATES spec 動態渲染、載歷史結果自動同步模板+參數、bench 烘焙+API 覆蓋。
- **驗收**：test_backtest 68/68 PASS;`node --check` PASS;`ast.parse` server PASS;CLI 端到端 SPY donchian rc=0 / 非法參數 rc=1 / 舊 flags 相容;rank_strategies 實跑 12 檔 rc=0 產出 artifact。（server 未重啟,Python 端變更待 user 重啟生效。）
- **重點紀律**：**探索層**不變。基準排名是「同一套規則+成本下的相對強弱」參考,卡片 modal note 明示非未來報酬保證。
- **下一步（需 user 動作）**：**重啟 dashboard_server** 讓新 cmd/白名單/strategies API 生效,重啟後開 `/backtest.html` 點卡片跑一輪新模板（如 donchian）確認端到端。

## 🟢 Session Note (v4.62.0) — 量化策略回測頁（quant-backtest）：動能規則 5-10y 重放 + 參數掃描熱力圖
- **起因**：使用者「想做量化交易策略頁面 + 回測過去 3y + 視覺化制定策略」。盤點結論：自家訊號歷史僅 2-3 個月（journal 2026-04 起），無法直接回測 3-5y；但 momentum-monitor 計分為純算術可**重放**。PoC（scratchpad）先驗證：FMP 10y 日線 1 次 call 1.6s、2512 天重放+回測 0.018s、重放的 ma_stage/trend_acceleration/stage 與 live cache **完全一致**（volume 差異=live 盤中投影、short_squeeze 歷史不可得→中性 40）。經確認表 OK 後動工。
- **做掉(firm)**：① `skills/quant-backtest/`（新 skill）— `backtest.py`（momentum 重放 + ma_cross 兩模板、成本內建、3y/5y/10y、6×6/3×3 參數掃描、validation_vs_live_cache、rc 0/1/2）+ `test_backtest.py`（29 asserts）+ SKILL.md。② `Dashboard/backtest.html` + `page-backtest.js`（NAV stock 群組「策略回測」）— 表單 → `/api/protocol-queue` quant_backtest → 輪詢 → tiles/權益 log/價格進出場/雙回撤/分數持倉/Sharpe 熱力圖/逐年表/交易清單/歷史 chips；caveats + 驗證 badge 常駐。③ server — SCRIPT_PROTOCOLS `quant_backtest`（requires 全 8 參數防 placeholder 殘留）+ PROTOCOL_LOG_DIRS + 只讀 `GET /api/backtest/{list,result}`（regex+白名單防遍歷）。④ `.gitignore` 加 `skills/quant-backtest/data/`。
- **驗收**：test_backtest 29/29 PASS；`check_skills.py` 0 warnings；`ast.parse` server + `node --check` 兩 JS PASS；**端到端**：以 handler-only 測試 server（:18099，不啟 daemon、不動 :8080 正式服）驗 list/result 200、壞 ticker 400、POST quant_backtest MSFT 全程跑完 artifact 可讀（+52.4% vs B&H +44.1%）。NVDA 5y 與 PoC 數字一致（+201.2%/Sharpe 0.84/MaxDD -34.8%/18 筆）。（瀏覽器擴充未連線，頁面未做視覺截圖。）
- **重點紀律**：**探索層**，結果不入 investment_protocol、不回寫任何 history/weights。UI 刻意為「模板+參數格」而非自由編輯器 — 掃描熱力圖看高原不看尖峰，對抗曲線擬合。FMP EOD 非股息調整 + 存活者偏差已入 data_caveats 常駐顯示。
- **下一步（需 user 動作）**：**重啟 dashboard_server** 讓新 API + NAV 生效；重啟後開 `/backtest.html` 實機看渲染。V2 候選：多 ticker 組合回測、walk-forward 自動分段、自家訊號源（journal/thematic）接入、股息調整報酬。

## 🟢 Session Note (v4.61.0) — 盤中頁整合（盤中評估＋盤中策略 → 單一「盤中」頁分頁）＋全中文化 hover 解釋
- **起因**：使用者「盤中評估跟盤中策略市場氛圍裡面的產業情緒排行可以整合頁面，另外盤中策略還有好多字沒翻譯或是解釋」。盤點確認：`intraday-eval.html`（盤中策略）與 `intraday-mood.html`（盤中評估）頂部氛圍資訊高度重疊，而**產業情緒排行只存在於策略頁**；策略頁大量英文原始標籤（`verdict` FAVOR/WARM、`skew_label` high、`fear_greed_label` Fear、`vix_regime` NORMAL）＋未解釋縮寫（SPY/QQQ/IWM/SKEW/F&G/RVOL/VWAP）。
- **做掉(firm)**（經 AskUserQuestion 確認：合併成單一頁＋分頁切換、全中文化＋hover）：① `intraday-eval.html` 重構為單一「盤中」頁，頂部 Tab「策略／評估」，評估內容（spikes＋aggregate＋逐檔＋K線 modal＋所有 inline CSS/JS）原封移植為第二 IIFE（scope 隔離，資料流/API 未改）；策略/評估各自 toolbar 隨分頁切換。② `page-intraday-eval.js` 加 `verdictZh/vixRegimeZh/skewZh/fearGreedZh` map + 產業評等中文＋tip、氛圍條 8 格＋逐檔體檢欄位全加 hover tooltip。③ `utils.js` NAV 兩項併一（標籤「盤中」）、`i18n.js` 同步。④ `intraday-mood.html` 改 redirect stub（→`intraday-eval.html#mood`）、`page-index-extra.js` 卡片連結同步；分頁初始 `#mood` 優先、其次 localStorage 記憶。
- **驗收**：`node -c` page-intraday-eval.js＋抽出的 inline script 皆 PASS；:8080 serve intraday-eval.html 含 tab bar＋兩 pane（5/5 marker）、page-intraday-eval.js 含新 map（8 hit）；`/api/intraday-mood/data`＋`/api/intraday-spikes/data` 皆 200。（瀏覽器擴充未連線，改以 curl 驗證，未做視覺截圖。）
- **重點紀律**：純前端呈現層整合，**不**碰 investment_protocol 決策、不改盤中 worker 資料流。
- **下一步**：實機於瀏覽器點兩個分頁確認渲染與 K 線 modal（本次無法視覺驗證）；regime driver/caution 字串內殘留的英文（如「F&G 33 Fear」）源自 `scripts/intraday_eval/engine.py` 產出字串，若要一併中文化需改後端。

## 🟢 Session Note (v4.60.0) — 盤中策略樞紐（Intraday Evaluation hub）：每 10 分鐘統整 + 策略卡 + 重複策略特效
- **起因**：使用者要一條盤中 worker「每 10 分鐘整理狀況、簡報策略」，且同一策略連續數個視窗或整日反覆出現時「加特效」視覺化，並強調**統整一次、單一 function 供下游撈，不讓每個 feature 各自撈**（規則 + LLM 導讀）。
- **做掉(firm)**：新增 `scripts/intraday_eval/`（engine/history/narrate/__init__/test，24 asserts PASS）— `load_sources()` 統整 inventory 全部盤中產物（0 額外 API call，讀既有快照）→ `evaluate()` 0-LLM 規則產 regime + 族群輪動 + 產業排序 + 個股點子 + **9 條策略卡**（stable id）→ `history.py` 記每視窗算 streak + 當日計數（240s dedupe）→ `narrate.py` change-gated LLM 導讀。server 加 daemon（每 600s，美股時段 + 收盤快照）+ `GET /api/intraday-eval/{data,history,state}`、`POST /refresh`。新頁 `intraday-eval.html`（盤中策略）+ `page-intraday-eval.js` + `style.css` `.ie-*` 特效（連續 iePulse 發光 / ×N echo 徽章 / 全日主旋律橘徽章）+ NAV/ i18n。
- **驗收**：`py_compile` server PASS；`test_engine` 24/24；streak 邏輯手測（連 3 視窗→streak3/day3/highlight/motif 正確）；`node --check` 三個 JS PASS；live engine 對 07-01 真實盤中資料產出（RISK-OFF 偏防禦、semis −5% vs software +5%、8 策略卡）與人工分析一致。
- **重點紀律**：**探索層**，**不**進入 investment_protocol 決策。既有 3 條盤中 daemon 未重寫，樞紐疊在其輸出上統整。
- **下一步（需 user 動作）**：新 daemon + `/history` `/refresh` 路由需**重啟 `dashboard_server`（./open）** 才生效；重啟前新頁以 static-file fallback 唯讀可用（無 timeline / 無手動重評估）。可選：Phase 2 把所有 fetcher 真正收斂成單一 hub（較大重構）。

## 🟢 Session Note (v4.56.0) — 投資方案頁可一鍵產生：playbook protocol + 「產生本週方案」按鈕
- **起因**：使用者「目前投資方案沒有從 UI 網頁上可以產生，做一個吧」。盤點確認 `/playbook.html` 只**呈現** `playbook.json`，產生新方案得手動跑 weekly-tech-playbook 三步（`build_pack.py` → Claude 選股寫 selections → `render.py`），無一鍵入口。（對比：per-ticker `分析` 早有 index.html 快速啟動 + decisions.html cmdbar 兩個 UI 觸發。）
- **做掉(firm)**：新增 `playbook` protocol 走既有統一佇列。① server 四 dict 條目（model=opus / timeout=30min / 完整流程 prompt / log dir）+ `_label_for`「📋 本週方案」+ `enqueue_protocol` 無參數去重；prompt 內含 `render.py --validate-only` 自我修正迴圈（rc==1 必修才續）。② `playbook.html` header「🔄 產生本週方案」按鈕 + 空狀態一鍵按鈕。③ `page-playbook.js` `generatePlaybook()`（confirm 告知 ~10–20min/~$4）+ `pollGenStatus()`（輪詢 `/api/protocol-queue`：running 顯示經過時間、完成自動 reload + toast、重開頁面接續顯示）。④ `i18n.js` `playbook_page` 區段 zh+en。**未新增端點**（沿用 `/api/protocol-queue`）。
- **驗收**：`python3 -c ast.parse` server PASS；AST 確認 4 dict 全含 playbook + prompt 無 stray placeholder（len 2410）；`node --check` page-playbook.js + i18n.js PASS；smoke-test `build_pack.py --no-fetch` rc=0 寫出 pack、`render.py --validate-only`（既有 selections）rc=0；測試產生的 no-fetch artifacts 已清掉還原。
- **重點紀律**：playbook 為**前瞻探索層**，**不**進入也不回寫 investment_protocol 決策。
- **下一步**：實機按一次按鈕跑一輪完整生成（含 yfinance fetch + opus 選股）確認端到端 happy path；若 codex_review 區段品質需提升，可考慮把 committee_blind_then_reconcile blind pass 也納入流程（須先寫 blind_artifact 否則 render fatal）。

## 🟢 Session Note (v4.55.0) — 總體儀表板「全新資訊架構」重設計：6 個最新 feed 上首頁 + 修 F&G/VIX 量表讀舊欄位
- **起因**：使用者反映「已經有很多新功能，但最新資料沒有正確反映到總體儀表板上」。盤點 `script.js` 綁定後確認 6 個每日/即時 feed（`market_mood` / `trending_tickers` / `intraday_spikes`+`intraday_mood` / `retail_sector_pulse` / `playbook` / 圖譜+供應鏈）**在首頁完全無露出**；且 `pill-fg` 讀 `data.market.fear_greed`（漂移為 49.8「Neutral」）、`pill-vix` 讀 `data.market_top.vix_level`，而權威 `market_mood.json` 實際為 F&G 25.5「Fear」/ VIX 18.97 → 量表顯示與真實情緒相反。
- **做掉(firm)**：① `index.html` 全面重排為 top-down 決策漏斗 6 段 IA（VERDICT→STATE→MOOD&TAPE→SECTORS→IDEAS→DESK），所有既有 live ID 原封保留；② 新檔 `page-index-extra.js` 把 6 個 feed 接成正確綁定的視覺化 widget（純讀取，non-blocking，`updateDashboard()` 末尾呼叫）；③ `script.js` 把 F&G/VIX 量表（含 tooltip data-attrs）改優先讀 `data.market_mood`；④ `style.css` 加 `.ix-*` widget 樣式。
- **驗收**：`node --check` 兩檔 PASS；sandbox 載入 `page-index-extra.js` + 真實 feed 跑 `IndexExtras.render(data)` → 6 widget 全部產出正確內容（mood −36 偏恐慌 / F&G 26 Fear / 社群 41 posts / 盤中 SNDK 急拉 +1.2% / 零售依 5d outlook 排序 / playbook 三籃 + Codex verdict）；F&G 量表 rebind 確認 49.8→25.5。server HTTP 200 serve 兩檔。
- **重點紀律**：新 widget 全為**探索/呈現層**，純讀 feed，**不**影響 investment_protocol 決策、不寫任何 cache/history。
- **下一步**：若使用者要更深整合，可把圖譜/供應鏈 teaser 由純導引卡升級為帶 centrality 數字的即時卡（需 `/api/graph/data` 輕量 stats endpoint）。
