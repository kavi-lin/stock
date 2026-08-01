# Session Notes 歸檔 v3.45.4 → v4.3.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v4.3.0) — 知識圖譜重構：theme hub-and-spoke + 聚焦模式
- **user 三抱怨**：看不懂 / zoom 不順 / 資訊量太大。診斷：280 邊中 262 是 CO_THEME 合成 clique（hairball 數學根源）；3 個錯開 auto-zoomToFit timer 跟 user 搶縮放 + 每幀 radial-gradient glow / `lighter` 合成拖累 zoom；點擊 thermographic 全圖特效資訊過載。
- **重構**（page-graph.js 全重寫 1046→~620 行，純呈現層，nexus_graph.json / build_graph.py 不動）：CO_THEME 不渲染，client-side 由 ticker.metadata.themes 合成 ~30 theme hub + MEMBER_OF spoke（邊 280→85）；點擊改 ego 聚焦模式（1/2 hop 切換、麵包屑、ESC 返回）；user 動手後永不 auto-fit；painter 只剩 circle+fillText；theme label 恆定螢幕大小（地標）。
- **控制台**：datalist 搜尋自動完成、關係類型 chip 開關、邊權重門檻 slider（取代時間衰減倍率）、聚焦深度按鈕；砍 provisional toggle。
- **驗證**：node --check 過；headless 截圖 ×2（hub 星系成形、主題 label 可讀、孤立節點自動隱藏）。聚焦模式點擊互動待 user 實測。
- **檔案**：page-graph.js / graph.html / VERSION×3。

## 🟢 Session Note (v4.2.0) — 產業掃描頁重設計：結論→辯論→證據
- **動機**：user 抱怨「掃描跑很多 token、頁面呈現很簡單」。盤點發現 sector_intel.json ~1300 行只有約 1/3 被 bridge 搬上 Dashboard — `_phase4a` 委員會 4 lane 投票、`_phase4b` Red Team IF/THEN 推翻條件、phase-1 估值（PE z1y/RS 多週期）、phase-3 盈餘脈搏/內部人/情緒全被丟掉；Today's Verdict hero 在 sector.html 還是 hidden stub（只活在 index.html）。
- **新區塊**：委員會決議矩陣（11×4 ▲▼ 投票 + 分歧高亮 + lane rationale）/ Red Team panel（反證 + IF/THEN amber 觸發塊 + DA conf 徽章）/ 量化證據矩陣（14 欄可排序熱力表）/ 宏觀 Overlay chips（FRED snapshot + step6 乘數理由 + 地緣風險）。verdict hero 上掃描頁（briefing signal grid 一併）。heatmap 移頁尾。
- **bridge.py**：market 增 `committee/da_challenges/fred_overlay/political_risk`；sectors[] 增 `valuation/earnings_pulse/smart_money/news_sentiment/fred_multiplier`。
- **驗證**：bridge 跑過、data.json 新欄位齊；node --check + ast.parse 過；headless Chrome 截圖逐區塊目視（矩陣/Red Team/quant 表/macro chips 全部 real data render）。
- **註**：新區塊文案用 isZh inline 雙語 fallback，i18n.js 未動。卡片 DA note 改 ⚔ marker（hover 全文），完整內容歸 Red Team panel。
- **檔案**：bridge.py / sector.html / page-sector.js / style.css / VERSION×3。

## 🟢 Session Note (v4.1.0) — Break News 辯論 V5：盲開局 + 分歧閘門
- **目標**：突發辯論省 token 但保有效產出。舊制 normal 固定 4 call（~10k tok）/ high 6 call，Round 2/3 大量重複 Round 1 資訊。
- **Round 1 雙盲並行**：A/B 各吃 opener、互不見 → divergence 變真訊號（舊制 B 看完 A 再寫，分歧被稀釋）。
- **Divergence gate（0 LLM）**：verdict 對立 / 同 pair predicate 極性衝突 / conf gap ≥0.4（`BREAK_NEWS_DIVERGENCE_CONF_GAP`）；`concede` 即收斂。無分歧 → 2 call 收場 `converged_round1`。舊 low-density early-stop 併入。
- **Round 2+ slim rebuttal**：新 `REBUTTAL_SYSTEM_PROMPT`+`rebuttal_user_prompt` — headline 1 行 + known state 1 行 + 確切分歧點 + 雙方 stance；output 只剩 commentary ≤60字/stance/新 relations/done，不重抽 entities。Round 3 只給 high-priority 仍分歧。
- **預算端**：`EST_CALLS_PER_DEBATE` 6→3，同 quota 可辯 ~2 倍條數。估收斂 case −70% tok、分歧 case −45%。
- **驗證**：mock 全流程 5 scenario（converge 2 call / concede relabel `divergence_resolved` / high persist 6 call / normal cap 4 call / 雙開局失敗→failed）+ gate 單測 6 case 全過。UI / build_summary_block / Nexus merge schema 相容免改。
- **注意**：validate.py 掃到 1 個 2026-05-30 舊檔缺 key — pre-existing，與本次無關。
- **檔案**：debater.py / prompts.py / poller.py / VERSION×3。

## 🟢 Session Note (v4.0.0) — Protocol 瘦身 + Model 分層（major）
- **B1 外移**：Phase 4.5 演算法 366 行 → `protocol_appendix_price_framework.md`（audit 用；engine+golden 為事實來源）。Protocol 4.5 縮成封裝呈現層 ~25 行。
- **B2**：Phase 2 reverse DCF pseudocode → 指路；2.4 時點 bullet → 1 行。**合計 1853 → 1471 行（−21%）**。
- **Model 分層第一批**：Sent/News/Tech lane → `model="sonnet"`；Fund/Val inherit（第二批候選）；**Red Team 永不降**；MD formatter Sonnet 既有。估單次 `分析` 成本 −35-50%。
- **哨兵**：shadow_report 加 lane 段（近 10 mean drift vs baseline n=31 + DISAGREE/polar 計數）。**降級後前 10 session 必看**；異常 lane 回 inherit。
- **第二批條件**：10 session 哨兵乾淨 → Fund/Val → Sonnet + MD formatter 試 Haiku。**第三批（另議，動決策）**：Valuation Specialist 裁撤（val_det 已有 deterministic 分數）。
- **驗證**：17 個 PHASE header 完整、golden 26/26、validator rc=0。
- **檔案**：protocol / 新 appendix / shadow_report / VERSION×3。

## 🟢 Session Note (v3.49.0) — 估值新 block 呈現層 + moat 容錯
- **呈現層補齊**：ic-memo §8（range/reverse DCF/MHP 三框/archetype shadow 四段，graceful skip 舊 entry，decision_lock 不動）+ decisions 頁 Valuation 卡 `buildFvExtras()` 4 行（Range/5D Band+60D+signal badge/Implied CAGR/Archetype flip ⚠）。
- **⚠️ 又抓到 pre-existing bug**：近期 entries（MRVL/PLTR/PANW）`moat_assessment` 被 LLM 寫成 string → **ic-memo 對最新 entries 一直 crash**。容錯修復，MRVL memo 重新可產（rc=2 degraded-usable）。註：根因是 LLM 沒照 schema 寫 dict — 之後 protocol 跑時 PM 應注意 fundamentals_lane shape；可考慮 validator 加 warning（未做）。
- **驗證**：render_sec_8 單測（synthetic blocks 全 render）、MRVL 全鏈 build→compose→validate rc=2、page-decisions.js syntax OK、golden 26 asserts 過。
- **Backlog 剩**：protocol token 瘦身、#10 cron 化、moat string drift 的 validator warning、shadow checkpoints（等 session）。
- **檔案**：build_fact_pack / compose / page-decisions.js / VERSION×3。

## 🟢 Session Note (v3.48.0) — Engine self-assemble + golden 測試 + peer_pe bug 修
- **P2 完成**：`--self-assemble` — quant 欄全由 engine 讀 deterministic 源（earnings cache / peer bundle / supp / forecaster cache / phase0），file 欄位優先，`self_assembled_fields[]` audit。AAPL 實測 24 欄自組、5/6 anchor。**估值鏈 0 LLM 算術 + 0 LLM 抄寫達成**（qualitative 欄 pattern/key_levels/catalyst 仍 LLM lane）。
- **⚠️ 順藤摸瓜抓到既有 bug**：FMP stable migration 後 `/stable/profile` 無 `peRatio`、`/stable/quote` 無 `eps` → **peer_pe_implied anchor 默默失效已久**。修：peer pe 用 ratios-ttm `pe_ttm` median；self eps = price/pe_ttm 反推（虧損股 → None，hypergrowth 規則退化只看 rev_yoy）。
- **#8a 修**：60d earnings_revision 折算 60/250（原直接用長期錨 = horizon mismatch）。
- **golden 測試**：`test_compute_price_framework.py` 4 fixtures × 26 asserts 全過；入 ops registry。改 engine 必跑。
- **限制註記**：self-assemble 的 fred 只補 real rate（nominal 10Y 無乾淨快取源 → engine fallback_fixed）；earnings cache 缺的 ticker（如 MRVL）→ DCF/PT/archetype 缺料降級（decision cap 接住）。
- **剩餘 backlog**：呈現層（ic-memo/Dashboard render range/implied/archetype）、protocol token 瘦身、#10 cron 化、shadow checkpoints（等 session）。
- **檔案**：engine / phase1_factpack / company_context / 新 test / protocol / CLAUDE.md / ops registry / VERSION×3。

## 🟢 Session Note (v3.47.0) — Dashboard Script 工具箱
- **起因**：user 要面板看「有哪些 script / 上次多久前用 / 需不需要跑」。
- **實作**：`config/ops_scripts.json` registry（11 支，可編輯）→ `/api/ops/scripts`（artifact-mtime 推斷 last run，零侵入；cadence 寬限 daily 26h/weekly 8d/monthly 32d）→ `/ops.html` + `page-ops.js`（badge: due/never_run/fresh/on_demand，due 排前；📋 複製指令；唯讀不執行）。
- **實測**：weekly_review 46 天未跑 → due 紅標（立刻有用的訊號）。
- **注意**：dashboard_server 需重啟才吃到新 endpoint（user 自管 daemon）。
- **檔案**：ops_scripts.json / dashboard_server.py / ops.html / page-ops.js / utils.js / i18n.js / VERSION×3。

## 🟢 Session Note (v3.46.1) — shadow_report.py 讀出端 + dispersion backfill
- **起因**：3 個 shadow 實驗（#3/#6/#4）只有寫入端沒有讀出端，checkpoint 到了要手挖 history。
- **`shadow_report.py`**：唯讀，一次算 4 section + checkpoint 進度，數學 import engine（單一事實來源），輸出 `reports/SHADOW_REPORT_<date>.md` + `--json`。#10 cron 前半身。
- **⚠️ backfill 重大發現**：歷史 37 筆 anchor CV 分布 median=0.46、P33=0.367、max=1.27 — agreement_grade 拍腦袋門檻 0.15/0.35 會把幾乎全部 session 判 low。**校準建議：high<0.367 / low>0.484**（33/66 pct），已寫進 protocol 4.5.0b 註記，#2 cap 接線前需 user 核可改 engine 常數。
- **跑法**：任何時候 `python3 investment/scripts/shadow_report.py`；#6/#3 到 20 session、#4 到 10 session 時跑它出報告。
- **檔案**：新 script + protocol 註記 + CLAUDE.md + VERSION×3。

## 🟢 Session Note (v3.46.0) — Valuation Archetype Shadow（#3，shadow-only）
- **起因**：固定 anchor 權重對未獲利成長股（DCF 0.45 雜訊、peer_pe EPS≤0 失效）與金融股（無 P/B）半殘。user 拍板：shadow 先行 + 權重表/門檻照設計初值。
- **archetype 分類**（按序首中）：financial → hypergrowth → cyclical → mature_cashflow → balanced。門檻初值：rev 25% / FCF 8% / rev 15% / margin σ 5pp。
- **3 新 anchor**：peer_ev_ebitda/ev_sales implied（精確 EV 數學，非比例近似）+ pb_roe_justified。資料：`get_ratios_ttm()`（company_context 新函數，雙 endpoint merge，24h cache）→ PEER_BUNDLE 新 5 欄。
- **紀律**：live `fair_value_summary` 完全不動；shadow 輸出 `flip_vs_live` 累積。**退出條件 ≥20 session 翻轉率報告 → #3b 切 live（cap/T5 接線同步）**。balanced fallback = shadow==live 自驗。
- **實測**：hypergrowth case live $225.7 overvalued vs shadow $270.5 fairly_valued（flip=true，EV/Sales 主錨）；financial pb_roe $76.95 手算一致；back-compat 舊 input → balanced flip=false；AAPL live peer median EV/EBITDA 20.4。validator rc=0。
- **Deferred**：forward EPS peer_pe、normalized-earnings anchor（cyclical）、cap/T5 接線 → #3b。
- **shadow 等待中清單**：#3 archetype（20 session）、#6 oe_mult（20 session）、#4 news_score 分布監測（10 session 凍結窗）。
- **檔案**：company_context / phase1_factpack / compute_price_framework / protocol / schema / validator / VERSION×3。

## 🟢 Session Note (v3.45.4) — News lane PT 去重（external review #4）
- **起因**：PT consensus 計分三次（valuation anchor 0.20 + 60d pt_60d 0.35 + News「PT vs price ±1」）。user 拍板：移除（非減半，LLM 聚合下減半不可控）+ 注入層剝離（非 rubric 層）+ revision momentum 回填 + 後驗防線。
- **fetch.py 剝離**：payload 砍 `price_target` block 全部絕對 level → `pt_revision_momentum`（30d/90d 方向+delta%+家數）。實測 AAPL：leak check 0、1m 下修 8% 有料。
- **持久化先行**：`news_lane.reasoning_one_line`+`key_factors[]` 必填第 5 欄（之前 0/134 落地，classifier 無 haystack — 這是 #4 計畫 review 抓到的致命缺陷）。
- **classifier**：`apply_det_shadow.py` `news_pt_leakage`（PT 折溢價措辭 → flag；「PT 上修/下修」合法）。warning 級。det_shadow → V3.45.4。
- **Phase 6 凍結窗**：前 10 個 News session delta.News=0（`news_weight_frozen_v3454`），防分布下移被誤判 lane 失準。
- **驗證法**：前向監測 news_score 分布 vs baseline `{-1:1,0:2,1:6,2:18,3:4}` (n=31) + leakage 累積率。history 反事實不可行（PT 子分數/reasoning/threshold 皆未落地）。
- **測試**：classifier 3 case PASS、舊 history entry back-compat（flag=None）、validator §5g warning-only rc=0。
- **待辦移交**：P2 餘項（#2 cap 接線 / #3 archetype anchor / #9 vol-normalize）、#8b DECAY backtest、#10 anchor 校準 cron、#6 oe shadow 20-session 檢查、PT 三點化 anchor（#1 後續）。
- **檔案**：fetch.py / protocol / schema / apply_det_shadow.py / validator / VERSION×3。
