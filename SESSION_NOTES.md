# INTEL COMMAND — Session Notes & System State

> **Last Updated**: 2026-08-02 (v4.78.0)
> **Role**: This file serves as the "Short-term Memory" and "Handoff Cache" for AI Agents. It contains market regime states, token optimization logs, and data integrity notes. **Task backlog has been moved to TODO.md; full version history to CHANGELOG.md.**

## 🟢 Session Note (v4.78.0) — Forward Expectations 前瞻預測修正
- **範圍**：正式 `forward_expectations` shadow engine；未混入舊 12m EPS×P/E forecaster，也未改 live DCF/FV/decision。
- **修正**：三個 annual-estimate 消費者統一 future-only cutoff；終端區間加 horizon/年化/coverage 降級；calibration 能在完整 FY 實績後核對 level 並保留最早 vintage；base-rate 需 metric-specific scope，MU 的 P/E `range_only` cohort 不自動擴成 growth anchor。
- **MU 影響**：排除 1 筆 elapsed FY 後，consensus revenue/EPS CAGR `66.72%/100.90%` → `41.34%/40.40%`；2030 終端 coverage 8，明確 thin。SNDK/WDC/STX 多年 revenue CAGR 中位 `-9%` 因 cohort 僅核准 P/E range，保留揭露但不進 numeric gap。
- **驗收**：23 支 Forward Expectations regression scripts rc=0；核心 55/33/41/61/16 asserts；682 snapshots → 99 dedup forecast points，0 comparable（尚未真正成熟，誠實維持 insufficient sample）；SYNC OK 4.78.0。

## 🟢 Session Note (v4.77.0) — 估值引擎 review 修正（degraded path 治理）
- **起因**：4.76.0 的外部 Claude review 因 CLI 未登入中斷，改由本 session 直接完成 review（範圍 A = commit `4e54e79`；B = 未提交的 DCF-primary + range-only peer fallback），共 12 項發現；使用者指示「你來負責修正」。
- **關鍵判斷**：12 項全部落在 degraded / fallback 分支，happy path（MU）完全正確。所以修法統一為「缺資料 → 保守且出聲」，而不是原本的「缺資料 → 套最寬鬆的合法上界」。
- **做掉(firm)**：① start EBIT margin 期間對齊（3 季 roll-forward vs 已公布季度兩種基礎，provenance 可分辨）；② `_render_degraded_md` 讓無 FV 的 run 產出 `DEGRADED` 報告而非 TypeError；③ 缺年度估計時成長種子改用 base growth 假設（原本直接套 45% cap）；④ `projection_degrade_reason` 5 種 reason 進 payload + warnings，禁止靜默退回 legacy；⑤ mode 讀不到的 override 列入 warnings；⑥ earnings cache 改 parse 檔名日期（mtime 會被 git checkout 重置）；⑦ `_eps_growth` 只取最近兩個未來 FY、超 clamp 回 None（原本會拿歷史成長或改抓更後面高成長年度）；⑧ cohort schema 驗證 + `pe_min/max` 離散度；⑨ canonical peer set 健康時不渲染第二張 peer 表；⑩ 新增 `--projection-mode auto|legacy`、`--xlsx` graceful skip、報告「本次採用」欄與 sensitivity 下限註記。
- **MU 迴歸**：FV `$762.13`、WACC `12.49%`、sensitivity `$693.74–853.60` 與 4.76.0 逐項一致（MU 走 3 季 roll-forward，不受修正影響）。快取宇宙 25 檔中 PEG 僅 CSCO 變動（`11.95%` → `10.15%`，修正值）。
- **驗收**：`test_dcf` 104 / `test_comps` 52 / `test_export_xlsx` 13 asserts 全 rc=0（新增 27 條對應 regression）；`test_compute_price_framework.py` + `test_valuation_pack_consistency.py` + `check_skills.py` + `validate_session_export.py` rc=0；SYNC OK 4.77.0。
- **下一步**：範圍 B 的 6 個檔案（SKILL.md / config / comps.py / peer_cohorts.py / export_xlsx.py / 2 支測試）仍是 untracked——review 發現 #9 指出 commit `4e54e79` 的 `--xlsx` 會 import 到不存在的 `export_xlsx`，已加 graceful skip 擋住 crash，但根本解是把 B 一起 commit。等使用者決定。

## 🟢 Session Note (v4.76.0) — DCF-primary + audited peer range
- **使用者定案**：DCF commit 結果作主 FV；LLM 找到的同產業候選若 provider peer endpoint 漏掉，可進 skill，但數字與 eligibility 必須由 Python；其他 anchors 只解釋區間。
- **做掉**：DCF commit `4e54e79`；audited `peer_cohorts.json` 只存候選/限制，P/E 由 shared adapter 重抓且 ≥3；`range_only` 永不補 live peer anchor。Structural DCF 改 primary FV，新增 explained range 與 report injection。
- **MU**：primary `$762.13`；sensitivity `$693.74–853.60`；without peer `$797.32`；SNDK/WDC/STX P/E anchor `$1,785.39`、with-peer `$1,291.36`；含 PT 的完整帶 `$693.74–1,468.26`。
- **驗收**：comps/framework/inject regression、pack consistency、invest validator、skill validator、Claude same-session review（結果見本 session 後續）與 version sync。

## 🟢 Session Note (v4.75.1) — MU through-cycle DCF 重建
- **起因**：MU 舊 vendor DCF `$384–446` 與多個估值落差過大；使用者要求聚焦重建 DCF。
- **做掉**：confirmed shift 改以 FY26 quarterly roll-forward 作 t0、FY27 起折現；分析師營收套 45/30/20/12/8% caps；EBIT/D&A/capex fade 到 normalized state；terminal capex 含成長再投資；最新 net cash/shares；異常 EBITDA/FCF sign fail-visible；beta 用 Blume mean reversion，override 保留原意。
- **MU 結果**：DCF `$762.13`，WACC `12.49%`，terminal g `2.5%`；cached `$823.03` 下 upside `-7.4%`，使用者報價 `$812` 下約 `-6.1%`；sensitivity `$693.74–853.60`。舊 vendor DCF 保留 audit、退出 live vote。
- **驗收**：DCF / canonical framework regression、py_compile、invest validator、version sync rc=0；報告 `reports/20260802_MU_dcf_model.md`。

## 🟢 Session Note (v4.75.0) — canonical valuation pack + eligibility fail-closed
- **起因**：使用者質疑個股估值可信度，要求盤點、提出修正方案，先與同一個 Claude Fable 5 session 討論到共識，再實作並由該 session review 到全部修完。
- **做掉**：唯一 `valuation_pack`；correlation group → family → portfolio 聚合；下游只能 projection；LLM 不得改估值；DCF/forecaster/peer/PT eligibility fail-closed；`--self-assemble` 清除 input-file anchor 注入；validator hard consistency；protocol/schema/skill 文件與測試同步。
- **MU 實測**：只剩 fundamental family，FV `$623.79`、vs `-24.21%`、score `-1`、confidence `low`；self DCF、PT、relative、forecaster 均依明確原因排除，audit 在 `reports/20260802_MU_valuation_pack_audit.md`。
- **外部複審**：Claude Fable 5 session `edfd3440-bc86-4328-9b94-90edf31b1193` 首輪提出 F1–F5；修正 injection、peer_count、PT freshness、fallback correlation 與 MU artifact 後逐項判定 resolved，最終 `ACCEPT`。

## 🟢 Session Note (v4.74.1) — 專案全面更名為英文（路徑 + 顯示名稱）
- **起因**：使用者要求「全面更名把中文的 AI投資委員會 改成英文，包含專案路徑，但是保留中文名稱」；澄清後定案：資料夾用 `ai-investment-committee`，中文名稱只保留在 README/CLAUDE.md 標題副標與 Dashboard UI 顯示文字。
- **做掉(firm)**：① `mv` 專案資料夾 `AI投資委員會` → `ai-investment-committee`（git 歷史完整保留，move 前確認無進程持有該目錄檔案）；② unload → 改 repo 內與 `~/Library/LaunchAgents/` 兩份 `com.kavi.aicommittee.premarket.plist` 路徑 → reload，`launchctl list` 確認重新載入；③ 修正硬編絕對路徑：`premarket_cron.sh` / `run_weekly_review.sh` / `p0_param_replay_2026-07-16.py` / `audit_stats_2026-07-16.py` / `DELEGATION_TEMPLATES.md` / `MAINTENANCE.md` / `ARCHITECTURE_DIAGRAM.md`（順手修正這些檔案原本就漂移到 `Documents/` 而非實際 `Developer/` 的舊路徑，見 LESSONS.md 同日條目）；④ 修正 `thematic_screener_extractor.py` / `earnings_analyzer_extractor.py` 裡 `str(path).split("AI投資委員會/")[-1]` 的硬編舊資料夾名（不修會讓 raw_path 欄位 split 失敗）；⑤ 活文件（README/CLAUDE/AGENTS/GEMINI/TODO/sector 相關/docs/news/daily_update.sh/REVIEW_PROMPT）標題與內文專案名稱改英文 "AI Investment Committee"，README/CLAUDE/AGENTS/GEMINI 標題保留中文為括號副標。
- **刻意不動**：`Dashboard/**`（使用者指定保留中文 UI）；`archive/**`、已封存個股/週報 `reports/*.md`（歷史快照，僅例外修正 6 天內最新一份 `SHORT_TERM_WEEKLY_2026-07-15.md` 的可執行指令路徑）；`CHANGELOG.md` 既有歷史條目（歷史不回寫）；`config/office_claude/**`、`cache/projects.json`（巢狀 office 模擬 Claude 執行狀態，指向另一條 `Documents/` 路徑，判斷為與本次更名無關的獨立狀態檔，未動——已告知使用者）。
- **驗收**：`py_compile` 兩支 extractor + 兩支 decision_review script 過；`bash -n` premarket_cron.sh / run_weekly_review.sh / daily_update.sh 過；`plutil -lint` plist 過；`launchctl list` 確認 `com.kavi.aicommittee.premarket` 重新載入且 ProgramArguments 指向新路徑；SYNC OK 4.74.1。
- **下一步**：使用者尚未要求 commit——785 個既有未 commit 檔案（多為每日操作性資料快取更新，與本次更名無關）與本次更名改動都還在 working tree，待使用者決定如何分批 commit。

## 🟢 Session Note (v4.74.0) — AI 辦公室辯論 v2 + Claude 無輸出修復 + launchd 時區事故
- **起因**：使用者回報 ① 盤前 launchd 沒跑（插電）② AI 辦公室 Lead(Claude) 連兩輪 `(no output)`，並要求重設計辯論機制（省 token 讀上輪、辯出有用資料）。
- **時區事故（環境層，非 repo）**：7/5 系統時區台北→America/Vancouver，但 UserEventAgent(Aqua) 自 6/11 開機未重啟、仍以台北時間註冊 StartCalendarInterval → 「週五 04:30-08:00」被排到溫哥華週四下午。已 `killall UserEventAgent` + bootout/bootstrap 兩個 agent（premarket / llm-review），log 驗證新註冊時間正確，並 kickstart 補跑 7/17 盤前 rc=0。**遺留**：建議使用者重開機讓 powerd 等 daemon 也吃新時區；未來跨時區改時區後記得重開機。
- **Claude 無輸出根因**：headless `claude -p` cwd=專案根 → 載 CLAUDE.md/MCP/工具進 agentic 模式，分析類任務跑不完 180s 被 SIGKILL；且 `_run_chain` preferred 模式不做真 fallback（設計如此）但 ALL_FAILED 誤標 `fell_back=True`。
- **做掉(firm)**：① `run_claude` 加 `model`/`max_turns`/`strict_mcp`/`no_tools` 參數（Break News 預設不變）——**三旗標缺一不可**：不加 `--tools ""` 時 sonnet 對分析 prompt 會嘗試 WebSearch 死於 error_max_turns；另有偶發 transient 失敗，claude 腿含一次 retry；② office orchestrator+roles 重寫四階段平行辯論 pipeline（平行獨立稿→分歧萃取→定點交鋒→opus 終局裁決），token 從 O(輪²) 全 transcript 重讀降到 O(分歧數) 定點 context；起草四席：Lead / Critic / Verifier / **Trader（盤面派，使用者指示加入 grok 成第四方）**；**Lead 固定 claude、Critic 只派 codex/grok、Verifier/Trader 隨機**（使用者觀察 gemini 內容品質不穩→實測格式最穩但激進主張 concede 率最高 3/5→依使用者指示轉型：**新增 Phase 0 Researcher 席固定 gemini**，agentic 讀 repo caches 產 facts-only fact pack（≤12 條含出處）餵給全部起草席+opus 裁決，實測從 market_mood/data.json/breadth_cache 撈出帶數字日期出處的實料；rebuttal 用 run 的 team 不用 registry pinned）。grok JSON 紀律鬆散（prose 前綴靠 `_extract_json` fallback、偶發整段 parse 失敗、小 prompt 也要 90-150s → `OFFICE_GROK_TIMEOUT_SEC` 預設 300）→ `_call_role` 全引擎 parse 失敗一次重試；claude text-only 必須用 `--system-prompt` 整替內建 prompt（append 會幻覺 `**Tool: read**` 文字工具呼叫，壓測 3/3 clean）；③ router `fell_back` 誤標修正；④ office UI 四段式展示（舊 run 事件相容）。模型配置：草稿/交鋒 sonnet + gemini + codex，裁決 `OFFICE_STRONG_MODEL`=opus（env 可換 fable）。
- **驗收**：py_compile + node --check 過；claude 新旗標實測 2-5s（sonnet/opus alias 均解析正確）；端到端 office run（HBM 供需小任務）全 pipeline 跑通；SYNC OK 4.74.0。
- **下一步**：實戰觀察分歧萃取品質（分歧太少=各稿太同質時，可調 Critic 的 contrarian prompt）；`OFFICE_MAX_DISAGREEMENTS` 預設 5 可依 token 預算調。

## 🟢 Session Note (v4.73.0) — 新增 Grok CLI 進 LLM 治理鏈
- **起因**：使用者本機已裝 grok CLI，要求先測可用性、可行就加進 LLM 列表。
- **測試**：`grok -p ... --output-format json --permission-mode dontAsk --disable-web-search --no-subagents` 端到端跑通（`grok-4.5`，session auth，envelope `{"text":...,"usage":{...}}`）；`--permission-mode bypassPermissions` 會被 Claude Code 自己的 auto-mode classifier 擋，改用 `dontAsk` 過。
- **做掉(firm)**：① `scripts/break_news/llm_drivers.py` 新增 `run_grok()` + `GROK_BIN`，註冊進 `_RUNNERS`/`VALID_MODELS`，`_DEFAULT_CONFIG` 加 grok（enabled/budgets）；② `config/llm_config.json` 加 `enabled.grok`/`budgets.grok`（daily_max_calls=100，先保守）；③ `dashboard_server.py` `/api/llm-config` 的 `valid` 集合加 grok；④ `Dashboard/utils.js` 側邊欄下拉選單＋usage 面板加 grok。
- **刻意不動**：預設 `primary/secondary/tertiary` 鏈（維持 codex→claude→gemini）與 `_protocol_command`（grok 尚未接進整段 protocol 執行器）——grok 目前只是「可被選、可被治理」，要不要拉進實際 routing 由使用者在側邊欄手動選。
- **驗收**：`model_router.py --status` 顯示 grok enabled/available、budget 100；`run_llm('grok', ...)` 實跑 rc=0 parse=ok；`py_compile` + `node --check` 語法過；SYNC OK 4.73.0。
- **踩坑**：`config/llm_config.json` 屬 MAINTENANCE §1 使用者手動校準區，改前應先備份卻先動手才補——已用 `git show HEAD:` 補回原檔存進 `docs/agent-ops/backups/llm_config.json.bak-20260717`（LESSONS.md 已記一筆，下次治理檔 Edit 前先 cp 再改）。
- **下一步**：若使用者之後決定把 grok 拉進實際 routing 鏈（primary/secondary/tertiary 或 break_news pair），留意其 daily_max_calls=100 是否需要依實際用量調整；目前無 cost_usd 回報（envelope 無 `total_cost_usd`），token 用量仍可追蹤。

## 🟢 Session Note (v4.72.0) — P2 斷鏈修補 + validator 補強（審計 F6 收尾）
- **起因**：使用者「p2繼續」。AUDIT_2026-07-16 F6 四項文件↔實作斷鏈全數處理。
- **做掉(firm)**：① P2-9：`parabolic_severity_tag` 抽到 `_shared/technical_core.py` 單一源，momentum.py + technical-analyst 共用（後者補 marketCap via company_context），protocol Technical lane 引用斷鏈修復；② P2-10：forecaster SKILL.md 聲明改「soft-wired」與 engine 實作一致；③ P2-11：validator §12 新增 final_score ±4.5 / scenario_odds=100 / lane±5 / conf 0-1 hard checks（合成壞 entry 4/4 抓到 rc=1）；④ P2-12：ftd_yfinance.py 的 `~/.claude/skills/` hardcode 改 repo canonical（diff 先確認未漂移；兩 adapter 實跑 rc=0）；⑤ 順手修 schema `lane_scores` −3..+3 誤註（協議量表是 −5..+5，歷史 9 筆 ±4 是合法分）。
- **驗收**：engine golden 61 asserts、validate_session_export（正反雙向）、check_skills 25/0 warnings、momentum+technical-analyst NVDA 實跑、兩 adapter 實跑——全 rc=0；SYNC OK 4.72.0。
- **重點紀律**：P0→P1→P2 全系列完成後，審計遺留的開放項只剩「校準債」（見 TODO 📊 段）與 shadow 檢查點兩個 user 決策。
- **下一步**：下次 `分析 [TICKER]` 實戰是 P0/P1/P2 新規則的第一次全鏈驗證——重點盯：Red Team 新欄位、C_eff 量化、rationale 機械格式、anchor 修剪是否如 spec 執行。

## 🟢 Session Note (v4.71.0) — P1 砍白產（同 session 接續 v4.70.0 P0）
- **起因**：使用者「ok 繼續p1」授權 P1 四項（含前輪對話同意的 market_regime 規則化評估）。
- **偵察先行（兩項原提案被證據修正）**：① P1-6 消費者掃描發現 moat/institutional_lens/decision_confidence_pct/cross_asset 有 Dashboard 決策頁與 ic-memo 渲染——範圍收窄為只砍零消費者的 `market_position`(TAM) 與 `medium_term_shift_20d`；② regime 規則表化被 76 個 phase0 校準**否決**（存檔訊號無法重建標籤：breadth 中位數 SIDEWAYS 50 > BULL 32，而標籤有 outcome 鑑別力 BULL +27.6% vs RISK_OFF −19.8%）——改為只加確定性一致性 caps。
- **做掉(firm)**：① P1-5：systemic_backdrop stub 刪除、Forward Expectations 35 行移 appendix（協議本文 -27 行）、shadow_report 檢查點跑出；② P1-6：兩欄位落日（protocol+schema）；③ P1-7：predict.py sector 過期改優雅降級（根因 96% 拒算只因 sector>72h；合成測試 6 asserts + NVDA 實跑 5d 恢復 ok）；④ P1-8：backdrop score 一致性 caps + rationale 機械式 trace 格式。
- **驗收**：engine golden 61 asserts rc=0、validate_session_export rc=0、validate_phase0 rc=0、predict 降級分支 6/6；SYNC OK 4.71.0。
- **⏳ 待 user 決策（shadow 檢查點，數據在 SHADOW_REPORT_2026-07-16.md）**：① archetype shadow 31/20 sessions 翻轉率 22.6%（≥15% → 按規則維持 live 不切，需 backtest 驗證方向性才議）；② dispersion 門檻校準提案 0.375/0.52（現 0.15/0.35 會把幾乎全部 session 判 low）；③ oe shadow 11/20 累積中正常。
- **下一步**：P2 四項（斷鏈修補、validator 補強）待指示；下次 分析 實戰驗證新 rationale 格式與 caps 是否被 PM 遵守。

## 🟢 Session Note (v4.70.0) — 分析協議審計 + P0 四項決策品質改制
- **起因**：使用者要求以財經專家視角全面檢討「分析 [TICKER]」skills/phases（冗餘、LLM 白產、幻覺、決策設計），要有歷史數據佐證；plan 核准後指示「開始 P0」。
- **審計（新產物）**：`reports/decision_review/AUDIT_2026-07-16_protocol_v5.md` — 168 筆 history + 134 筆已完成 30d 窗口 join。兩個關鍵新檢驗：① Red Team STRONG_COUNTER 佔 80.4% 且與 outcome **零相關**（STRONG 組 +12.52% vs 對照 +8.64%，p=0.689；被否決且 CANCEL 的 60 筆 57% 照漲）；② confidence 0.6/0.7 bucket 命中率同 67%（核心帶無鑑別度，唯一訊號在 <0.45 低尾）。重現腳本同目錄（audit_stats / p0_param_replay）。
- **做掉(firm) P0 四項**：① P0-1 Rec 11 probe 分數分層（≥0.4 → t2 ≤30bps / <0.4 → t1 ≤15bps；新欄 `hot_zone_probe_tier`）；② P0-2 Red Team 懲罰分級（pure_forward strength=5 才 ×0.85、=4 ×0.925；default ×0.85→×0.95）+ 新 export 欄 strength / `thesis_break_probability`（僅記錄，≥20 session 校準）；③ P0-3 引擎 `trim_anchor_outliers()`（錨中位數 ×1/3..×3 外剔除；NVDA-like $31.80 壞錨案例 fair value $272→$296）；④ P0-4 lane confidence 三檔量化 C_eff 0.35/0.60/0.72（切點 0.45/0.675，scale-preserving 免重校準 threshold）。
- **驗收**：engine golden test 7 fixtures 61 asserts rc=0（新 fixture 手工驗算）；validator 對既有 history rc=0（舊 entry 僅 warning 向後相容）；每項參數皆由 replay 選定（模糊區分數帶 / tier3 flips 中性 / trim 不誤剪全低錨）；SYNC OK 4.70.0。
- **重點紀律**：樣本期 4-7 月為多頭段——P0-1/P0-2 放寬方向的改動依賴 regime guard 與 tier 上限 bound 下檔；thesis_break_probability 與 strength 分級是**待驗假說**，≥20 session 後必須跑 outcome 校準決定去留。
- **下一步**：P1（砍白產：shadow 落日、敘事移 --memo、macro multiplier 規則表化）與 P2（斷鏈修補、validator 補強 final_score 界限）待使用者指示；下次 `分析 [TICKER]` 實戰盯 Red Team 是否照新 prompt 輸出 strength/probability 兩欄。

## 🟢 Session Note (v4.69.0) — valuation-modeler + 8-anchor + 首次覆蓋（官方 FS 套件差距移植）
- **起因**：使用者貼 Anthropic「Claude for Financial Services」公告要求對照架構。差距分析：已有且更嚴謹的不取代（earnings/sector/news/ic-memo/screening）；四缺口 = 自建 DCF、多指標 comps、initiating coverage、xlsx。使用者選「移植為原生 skill + 四項全做 + 直接接 valuation lane」（plan mode 核准）。
- **做掉(firm)**：① `skills/valuation-modeler/`（第 25 skill）— dcf.py（driver-based FCFF、假設 provenance、CAPM WACC、5×5 sensitivity）/ comps.py（4 指標 IQR winsorize、P/E 排除防重複計權）/ export_xlsx.py（5-sheet workbook、graceful degrade）＋80 asserts。② **決策路徑**：ANCHOR_WEIGHTS 6→8（+dcf_self_built 0.15 / +comps_implied 0.10，家族層不變）、confidence 門檻 ≥6/4-5/<4、ARCHETYPE 11 池配平、protocol 本文＋兩 appendix（新 §4 VALUATION_MODEL_BUNDLE）＋schema＋validator 容錯；golden test 按新權重人工重驗算（51 asserts）。③ 首次覆蓋：compose_initiation.py＋template_initiation.md＋build_fact_pack --initiation（缺 vm cache rc=4 印指令）＋validate --initiation（F-I1/I2/I3）；28 asserts。
- **驗收**：全部測試 rc=0（dcf 43 / comps 24 / xlsx 13 / price_framework 51 / initiation 28 / ic-memo 舊測 3 檔）；validator 對既有 6-anchor history rc=0（向後相容 gate）；NVDA 端到端：dcf $84.95（WACC 14.5% 嚴格保守屬預期）、comps $167.89、initiation 報告 442 行 validator rc=2（僅既有 peer_descriptor stub）；check_skills 25 skills 0 warnings；SYNC OK 4.69.0。
- **重點紀律**：新 anchor 缺值走既有重分配（vm script 失敗不阻塞 protocol）；comps anchor 排除 P/E；官方 plugin 不安裝（LLM 手算違紀律）、付費連接器不引入。
- **下一步**：下次 `分析 [TICKER]` 實戰時 PM 記得跑 VALUATION_MODEL_BUNDLE 兩 script（appendix §4）；跑幾個 session 後觀察 dcf_self_built 與 FMP dcf_unlevered 的分歧幅度，評估權重是否再調。

## 🟢 Session Note (v4.68.1) — 盤前 launchd 排程補跑機制（電池闔蓋喚醒失效修復）
- **起因**：使用者回報 4:30 盤前排程裝了但資料沒更新，「檢查整條路」。
- **診斷**：plist 已載入、腳本手動跑 rc=0、pmset 4:27 喚醒有設——斷點在 **Mac 電池供電＋闔蓋過夜時排程喚醒被 macOS 跳過**（pmset log 證實 4:27 無喚醒事件，只有零星 2 秒 DarkWake，GUI LaunchAgent 不執行）；且 06:34 開蓋後 launchd 實測**沒有**補跑 missed calendar job。
- **做掉(firm)**：① `premarket_cron.sh` 加 already-succeeded-today guard（當日 log 有 `daily_update.sh rc=0` → 記 skip 退出）。② plist `StartCalendarInterval` 擴成 04:30/05:00/06:00/07:00/08:00 ×週一~五（25 entries），開蓋後下一時段自動補跑。③ 已 cp 至 `~/Library/LaunchAgents/` 並 bootout/bootstrap 重載。
- **驗收**：plutil lint OK、`bash -n` OK、launchctl print 25 個 calendar trigger、kickstart 實跑補回 2026-07-16 當日資料。
- **重點紀律**：排程喚醒只有**接電源**才保證生效——交易日前夜插電仍是首選；補跑機制只是降級保險（漏更新 → 開蓋後最多等到下一個整點）。
- **提醒**：repo 副本與 `~/Library/LaunchAgents/` 那份需同步維護（同 a14bbfe 慣例）。

## 🟢 Session Note (v4.68.0) — SESSION_NOTES 批次輪替制 + rotate script
- **起因**：使用者定案 v2 輪替制——每 10 個舊 note 串成一個 archive 檔、以版號範圍命名（ex `session_notes_v4.44_to_v4.54.md`）。
- **做掉(firm)**：① `scripts/rotate_session_notes.py` — 主檔 >20 note 切最舊 10 個成批次檔（≤20 no-op；不覆蓋既有檔）；`--split-legacy` 拆舊 rolling archive。② 舊 archive 239 note 拆成 24 個版號範圍檔（v1.40.0→v4.54.2），總數驗證無遺失。③ MAINTENANCE §3 / SESSION_NOTES 指標 / OPS_COMMANDS §1 同步改批次制。
- **踩坑**：第一輪拆分 6 檔命名壞掉——舊標題有範圍式 `(v2.10.0 → v2.11.0)` 格式，regex 沒吃到 → 從備份還原重拆（regex 已修，`\(v(\d[\w.\-]*)`）。
- **驗收**：合成 fixture 測 rotate/no-op/尾端保留/批內排序 PASS；真檔拆分後 `grep -c` 總數 239 = 原數；版本同步 SYNC OK。
- **重點紀律**：輪替一律走 script 不手搬；收尾流程 = 寫 note → 跑 `rotate_session_notes.py`（多數時候 no-op）。

<!-- 批次輪替制：主檔超過 20 個 Session Note 時跑 `python3 scripts/rotate_session_notes.py`，最舊 10 個自動切成 archive/session_notes_v<A>_to_v<B>.md。查舊版本：Grep 版號於 archive/session_notes_v*.md（規則：docs/agent-ops/MAINTENANCE.md §3） -->

## 🔵 Momentum Context (Multi-Universe)
**動能選股 Universe 整合機制**。
- **(1) 市場狀態**：目前預設掃描 `all` (SP500 + Nasdaq 100 + Watchlist)，總數 527 檔。
- **(5) 數據結構**：CSV/JSON 新增 `in_nasdaq100` 布林欄位。
- **(4) UI 連動**：Dashboard 預設顯示 Top 200，但透過 `isWatchlist` 邏輯，自選股不受 Universe 篩選器影響，始終顯示。

---

> **📜 完整版本歷史已移至 [`CHANGELOG.md`](./CHANGELOG.md)** — 自 v1.0.0（2026-04-09 初始）至目前全部 entries，含 git commit 引用與 evolution highlights。

---

## 📋 Bridge 資料流對照（System Manifest）

| Protocol | 輸出 Log | Bridge 讀取欄位 | Dashboard 顯示 |
|---|---|---|---|
| `investment_v5_0` | `invest_logs/history.json` | `final_decision`, `score`, `macro_alignment`, `key_risks` | decisions 頁全部 |
| `sector_v1.3` | `sector_logs/*_intel.json` | `market_regime`, `_phase0` (breadth/FTD/MT), `today_verdict` | index + sector |
| `news_v2.1` | `news_logs/*_digest.json` | `verdicts[]`, `trump_signals`, `catalysts` | news 頁 + sidebar |
| `breadth_analyzer`| `breadth_cache/*.json` | 6 組件 breadth + trend | index 廣度 gauge |
| `positions.json`  | — | lots → avg_cost / live_position | decisions 持倉 |
