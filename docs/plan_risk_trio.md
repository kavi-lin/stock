# 風控三支改版開工表 — portfolio-risk-manager / tail-risk-analyzer / short-contrarian-analyst

> 產生:2026-08-08(repo 狀態 V4.111.6)。給執行 session(Opus 5)的完整交接。
> 盤點由兩個 fresh-context Explore agent 完成,所有 `file:line` 以產生當日 working tree 為準——**動工前先 spot-check 幾個關鍵行號仍對得上**(中間若有其他 session 改過檔案,行號會漂)。
> 本表分兩批:**Batch A = 修正批**(不改 protocol 語意,確認表後可直接做);**Batch B = 語意升級**(每項只準備決策備忘,未經使用者逐項拍板不准動手)。

---

## 0. 執行守則(先讀,不可跳過)

1. 必讀:`CLAUDE.md`(Workflow Rules)、`docs/agent-ops/MAINTENANCE.md`(版本 bump + 巨檔讀寫規則)、`docs/agent-ops/OPS_COMMANDS.md` §7/§8(驗收命令)。
2. **Workflow Rule 1**:Batch A 改動 ≥2 檔 → 動工前輸出摘要表(File / Action / Est. Lines / Description)等使用者「OK」;使用者本輪已明確授權自主時免。
3. **Batch B 是紅線**:每一項都會改變 position sizing 或 protocol 行為。只產出決策備忘(選項 + shadow 證據 + blast radius),等使用者逐項選擇。
4. 禁區:`skills/short-term-target/config/weights.yaml`、`config/llm_config.json`、`positions.json`、`investment/invest_logs/history.json` 既有資料。sizing chain 的段序被 `validate_session_export.py` §14 逐段鎖定——未拍板不得增刪段。
5. 收尾 checklist:三處版本 bump + SYNC OK 驗證命令、`SESSION_NOTES.md`/`TODO.md` 按 MAINTENANCE §3 規則更新(禁整檔 Read)、`skills/MARKET_INDEX.md` 同步、踩坑寫 `LESSONS.md`。
6. 測試紀律(LESSONS 2026-08-08 兩條):(a) 新測試寫完要**故意把 bug 種回去確認會紅**;(b) mock 要打在真實 code path 上(本 repo 曾有整套測試 mock `session.get` 而 code 走 `fmp_pool`,靜默打真網路)。

---

## 1. 背景與動機

三支 skills 自 **2026-04-16** 後程式碼未動(4/19 只補 frontmatter),期間 investment protocol 演進到 V5.0 + L4b、專案慣例演進到 fmp_pool / technical_core / 每 skill 帶測試。三支全部:

- 單檔 flat script、**零測試**、零 cache
- 繞過 `skills/_shared/technical_core.py`(canonical 價格源,FMP 主 + yfinance fallback)與 `scripts/_shared/fmp_pool.py`(共享 250/min 限流),直打 yfinance
- 下游唯一測試 `investment/scripts/test_trade_plan_builder.py` 只用 hardcoded fixture 測**消費端**(`--no-subprocess`),三支 producer 本體從未被驗證

它們的位置卻是全 protocol 風險最高的:short-contrarian 有 **T4 否決權**(可強制 HOLD),另兩支直接決定 **Phase 4 倉位**。

---

## 2. 現況事實(審計摘要)

### 2a. portfolio-risk-manager(`skills/portfolio-risk-manager/scripts/risk_manager.py`,167 行)

- 演算法:vol-budget 縮放(`--vol-budget` 預設 0.6%/日)→ 相關性乘數(`<0.3→1.00 / <0.6→0.85 / <0.8→0.70 / else 0.55`,`:106-109`)→ 產業集中懲罰(`>0.30` 觸發 ×0.5,`:126,:131`)。
- 輸出:`{"final_position_cap_pct", "raw_vol_adjusted_cap_pct", "correlation_multiplier", "sector_cap_triggered", "ticker_stats", ...}`(`:140-159`)。
- **缺陷 P1【失能】**:`raw_cap = vol_budget/daily_vol*100`(`:101`)配 20% 硬 ceiling(`:102`)→ daily vol ≤3%(≈48% 年化)就頂到 20。**對所有正常股票輸出恆定 20.0**,主打的 vol-scaling 實際不工作,唯一活的差異化只剩相關性乘數。實測 NVDA(38.6% 年化 vol)仍 20.0。
- **缺陷 P2【bug】**:sector 檢查對每個 holding 開 2 個 `yf.Ticker`(`:118-119`)串行無 cache;`except: continue`(`:124-125`)把 fetch 失敗的 holding 從 `portfolio_value` 分母移除 → **膨脹 sector_exposure 比率**,一次網路閃斷就可能誤觸 ×0.5 懲罰。
- **缺陷 P3【dead code】**:`--portfolio-size` 讀進來(`:61`)、echo 出去(`:147`),從未參與計算。
- **缺陷 P4【robustness】**:無 top-level try/except(對比另兩支都有)——yfinance 掛掉 = 未捕捉 traceback + 空 stdout。Consumer(`trade_plan_builder.py:358-372`)雖有 fallback(缺 `final_position_cap_pct` → `RULE_BASED` base 0.05),但拿不到結構化 error 訊息。
- **缺陷 P5【路徑】**:`--positions` 預設 `"positions.json"` 是 CWD-relative;`trade_plan_builder.py:337` 用 `cwd=ROOT` 所以整合路徑安全,手跑就看 CWD。
- 語意疑點(不是 bug,B 批討論):sector exposure 的 positions 清單未排除 candidate 自身(`:116`)——已持有 candidate 時,它自己的部位會墊高自己產業的集中度。

### 2b. tail-risk-analyzer(`skills/tail-risk-analyzer/scripts/tail_risk.py`,115 行)

- 演算法:1y 日報酬 → excess kurtosis / skew / VaR95 / maxDD / ann vol / downside dev → normalizer(`:51-55`,2026-04 校準)→ 加權 `kurt .10 / skew .10 / var .15 / dd .30 / vol .35`(`:58-65`)→ 分級 `<30 ROBUST×1.0 / <60 MODERATE×0.75 / else FRAGILE×0.5`(`:67-72`)。
- **缺陷 T1【文件教錯】**:`SKILL.md:42` 寫的權重(kurt 30%/skew 20%/VaR 20%/DD 20%/vol 10%)與 code 完全不符;`SKILL.md:43-45` 寫分級 35/65,code 與所有 consumer(protocol `:1371`、`trade_plan_builder.py:392`)都是 **30/60**。SKILL.md 是唯一異端,會教壞任何讀它的 agent。**code 為 canonical,修文件。**
- **缺陷 T2【schema 漏欄】**:SKILL.md 輸出表漏 `sample_days`(code `:78`)。
- 邊界行為正確:`<30` bars → `{"error"...}` stdout + exit 1(`:100-102`),consumer 正確解析並降級 `MODERATE ×0.75` 不當 ROBUST(`trade_plan_builder.py:373-389`)。
- Off-band 引用(B 批討論):`sector/phase_1-2-3.md:207` 用 `tail_risk < 40`、`sector/phase_4-5.md:268` 用 `>70 OR kurtosis>5`——與 30/60 分級帶不對齊。

### 2c. short-contrarian-analyst(`skills/short-contrarian-analyst/scripts/burry_score.py`,184 行)

- 演算法:FCF yield / EV-EBIT / D-E / 52w 距離 / insider 五元件 piecewise 打分 → 權重 `.35/.25/.15/.15/.10`、None 元件重新正規化(`:126-128`)→ verdict `<20 T4_VETO / <35 WARNING / ≥60 VALUE_BONUS / else NEUTRAL`(`:130-139`)。
- **缺陷 B1【真 bug,最高優先】**:價格抓取失敗時 `pct_below_high = 0.0`(`:109-111`)→ `score_52w` 映射到**最嚴苛的 20 分**且以真資料身份參與加權——網路閃斷可以憑空製造 WARNING 甚至 T4_VETO,**而這是有否決權的 agent**。正確行為 = `None` → 權重 renorm 掉(與 insider 的處理一致)。
- **缺陷 B2【文件詐欺】**:frontmatter `data_sources: [FMP API, yfinance]`——script 裡**沒有任何 FMP**。`skills/MARKET_INDEX.md:41` 重複同一錯誤宣稱。
- **缺陷 B3【刻度殘留】**:`investment/README.md:144,145,203,285` 還在用 pre-V4.4 的 0-10 刻度(`T4 Veto | burry_score ≤ 2` 等)。script 出 0-100,protocol `:792` 已註明修正——README 漏改。
- **缺陷 B4【命名誤導】**:`:92-95` EBIT 拿不到、用 EBITDA 代打,輸出 key 仍叫 `ev_ebit`,SKILL.md 表仍寫 "EV / EBIT"(`reasoning` 字串倒是誠實寫 EV/EBITDA)。**key 不能改**(history/render 依賴),文件要註明。
- **缺陷 B5【protocol 死規則】**:`investment_protocol_v5_0.md:722` 條件 `component_scores.insider == 0`——script 只會出 80/50/20/None,0 不可達,規則永不觸發。
- **缺陷 B6【合約留白】**:protocol `:728-739` 期望的 Phase 2 JSON 含 `burry_voice` 與 `veto_flag`,script 都不輸出,由 LLM 合成——SKILL.md 未說明此分工。
- 其他:insider 判讀靠 string-sniffing yfinance 列值(`:53-72`),極脆弱但 fail-safe(炸掉 → UNKNOWN → renorm 掉)。SKILL.md 輸出表漏 `weights_active`。

### 2d. 下游合約(改動前必須背下來)

- **呼叫方式**:`trade_plan_builder.py:73-74,337-340` subprocess 跑 rm/tail(`--json-only`);burry 由 PM 在 Phase 2 末 inline Bash 跑(protocol `:701`),**無程式化 caller**。
- **Burry 不是 lane**:`apply_det_shadow.py:368` 的 `LANE_NAMES` 六 lane 不含 burry;它以平鋪欄位落在 `trades_this_session[0]`(`burry_score`/`burry_override_active`/`burry_override_recheck_date` 皆 TRADE_REQUIRED,`validate_session_export.py:83`)。
- **sizing chain 段序**(`trade_plan_builder.py:593-595`,§14 逐段驗算):`base → tail_adj → macro_cap → binary_adj → burry_override_adj → ftd_adj → f1_adj → shift_adj → polar_adj → final`。
- **fragility 表三處鏡像**:`trade_plan_builder.py:102`、`validate_session_export.py:386`、`replay_trade_plan.py` 的 `FRAGILITY_MULTIPLIER`;§14b enum gate(`validate_session_export.py:1541-1549`)只認 `ROBUST/MODERATE/FRAGILE`。
- **降級合約**(protocol `:1310-1313`):Step 2 失敗 → RULE_BASED 0.05;Step 3 失敗 → MODERATE ×0.75 **不得當 ROBUST**。
- **T4**(protocol `:787-800`):`veto_flag=true`(score<20)AND tentative BUY → T4;`<10` 建議 CANCEL;`OVERRIDE_BURRY` 三成本(×0.5 / justification ≥20 字 / recheck +5 交易日)。
- **sector Phase 4b**(`sector/phase_4-5.md:259-272`):prose 指令,DA 把 `tail_risk_checks[]` 貼進輸出;`sector/scripts/validate_sector_intel.py` **完全不驗這些欄位**。
- history 有舊值(`RESILIENT`/`EXTREMELY FRAGILE`/0-12 刻度 burry)——**不清洗**,replay cohort 靠它們測排除路徑。

### 2e. 合約級 mismatch(兩位盤點者交叉確認)

| # | Mismatch | 事實 |
|---|---|---|
| M1 | **WARNING ×0.7 / VALUE_BONUS ×1.15 有文件無實作** | protocol `:706-711` + SKILL.md 都寫 Phase 4 要乘;`trade_plan_builder.py` 九段 chain 沒有這段,§14 validator 也沒有。目前 WARNING/VALUE_BONUS 對倉位**零影響**(只有 OVERRIDE ×0.5 是真的) |
| M2 | **sector 端 EXTREMELY_FRAGILE 降級規則永不觸發** | `sector/phase_4-5.md:310-316` STEP D 依據 `fragility_label = EXTREMELY_FRAGILE` 降 HOT→WARM;`sector/schema.md:487` enum 有 5 值——但 `tail_risk.py` 只會輸出 3 值,規則死的 |
| M3 | tail-risk SKILL.md 權重/門檻與 code 及全部 consumer 不符 | 見 T1(這條 Batch A 直接修文件) |

---

## 3. Batch A — 修正批(不改 protocol 語意;逐項可獨立驗收)

> 原則:**code 行為只在「失敗路徑」改變**(修 bug),成功路徑的數字/欄位/shape 一律不動。改前先對 NVDA / SPY / KO 各跑一次三支存基線 JSON,改後 diff,成功路徑必須逐位元一致(僅 `generated_at` 豁免)。

| # | File | Action | Est. Lines | Description |
|---|---|---|---|---|
| A1 | `skills/short-contrarian-analyst/scripts/burry_score.py` | 修 bug | ~6 | `:109-111` 價格抓取失敗 → `pct_below_high = None`(而非 0.0),讓 `:126-128` renorm 掉;`reasoning` 註明該元件缺席 |
| A2 | `skills/portfolio-risk-manager/scripts/risk_manager.py` | 修 bug + robustness | ~25 | (a) top-level try/except → `{"error", "ticker"}` stdout + exit 1(對齊另兩支;consumer `:358-372` 已支援);(b) sector 檢查:holding fetch 失敗**不得**縮分母——失敗改為「本次不觸發 sector cap + `warnings[]` 註明」(寧可少罰不誤罰);(c) `--positions` 預設改 ROOT-relative;(d) 移除死參數 `--portfolio-size`(輸出 `inputs` 塊同步拿掉 `portfolio_size_usd`) |
| A3 | `skills/tail-risk-analyzer/SKILL.md` | 文件修正 | ~10 | 權重改為 code 實況(.10/.10/.15/.30/.35)、分級 30/60、輸出表補 `sample_days`;註明「code 為 canonical,分級表三處鏡像位置」 |
| A4 | `skills/short-contrarian-analyst/SKILL.md` + frontmatter | 文件修正 | ~12 | 移除 FMP 宣稱;`ev_ebit` 註明實為 EV/EBITDA(key 因 history 相容不改);補 `weights_active` 欄;說明 `burry_voice`/`veto_flag` 由 LLM 於 Phase 2 合成(引 protocol `:728-739`) |
| A5 | `skills/MARKET_INDEX.md` | 同步 | ~2 | `:41` short-contrarian 資料源改 `yfinance`(移除 FMP);三支的接線描述如有變動一併同步 |
| A6 | `investment/README.md` | 刻度清理 | ~4 | `:144,145,203,285` 0-10 舊刻度改 0-100(對照 protocol `:706-711` 的現行表) |
| A7 | `investment/investment_protocol_v5_0.md` | 死規則清理 | ~2 | `:722` `insider == 0` 不可達 → 改成 `insider_net == "SELL"`(score 20)或直接刪;**只刪死規則,不動其他行為條款** |
| A8 | 三支各建 `scripts/tests/` | 補測試 | ~350 total | 全部 mock 資料、零網路。鎖:(a) 輸出 JSON shape(golden keys);(b) 分級/verdict 邊界(30/60;20/35/60);(c) 降級路徑——0 bars → error JSON、burry 價格失敗 → renorm(A1 的回歸測試,先種 bug 確認紅);(d) rm 的 sector 分母行為(A2b 回歸);(e) None-renorm 權重和 = 1。mock 打在模組函式層(如 patch `yf.Ticker`),不准打不存在的 code path |
| A9 | `skills/portfolio-risk-manager/SKILL.md` | 文件同步 | ~6 | CLI 區補 `--json-only`、移除 `--portfolio-size`、註明 positions 預設路徑行為與 P1 失能現況(「vol-scaling 對 daily vol ≤3% 恆頂 20%——修復方案見 Batch B1」) |

**明確不做(屬 Batch B)**:改 20% ceiling / vol-budget 語意、動 sizing chain、改分級門檻數值、sector enum、資料源遷移。

### Batch A 驗收(全部要貼實際輸出,rc=0 才算過)

```bash
# 1. 基線 diff:改前後各跑,成功路徑逐位元一致(僅 generated_at 豁免)
python3 skills/portfolio-risk-manager/scripts/risk_manager.py NVDA --json-only
python3 skills/tail-risk-analyzer/scripts/tail_risk.py SPY --json-only
python3 skills/short-contrarian-analyst/scripts/burry_score.py KO --json-only

# 2. 新測試(A8)+ 種回 bug 紅一次的證據
python3 -m pytest skills/portfolio-risk-manager/scripts/tests/ skills/tail-risk-analyzer/scripts/tests/ skills/short-contrarian-analyst/scripts/tests/ -q

# 3. 下游 gates(OPS_COMMANDS §7 :107、:109、:129)
python3 investment/scripts/test_trade_plan_builder.py
python3 investment/scripts/validate_session_export.py
python3 investment/scripts/test_session_export_schema.py
python3 scripts/check_skills.py

# 4. replay 基線(本批不動表,跑一次確認沒被波及;current_rule_mismatched 必須 0)
python3 investment/scripts/replay_trade_plan.py
```

---

## 4. Batch B — 語意升級(只出決策備忘,逐項等拍板)

每項備忘固定格式:**現況 → 選項(含「不做」)→ 每選項 blast radius(要動哪些檔,含 validator/schema/replay/fixtures)→ shadow 證據 → 建議 + 一句話理由**。

| # | 題目 | 核心問題 | 最小證據要求 |
|---|---|---|---|
| B1 | **vol-scaling 失能**(P1) | 20% ceiling 恆綁,cap 恆 20。選項:(i) vol-budget 降到讓 cap 有分布;(ii) 引入上游 position-sizer 的 stop-distance / ATR sizing 取代;(iii) ceiling 參數化交使用者 | 對 history.json 全部 VOL_ADJUSTED 案例(`replay_trade_plan.py` 有 cohort)重算各選項的 cap 分布對照表 |
| B2 | **M1:WARNING ×0.7 / VALUE_BONUS ×1.15** | 實作(動 chain = §14 validator + `phase5_export_schema.md` FULL EXAMPLE + `test_session_export_schema` fixtures + `replay_trade_plan.py` 全要動,段序是鎖的)或刪文件(protocol `:706-711` + SKILL.md 同步降級為「無倉位影響」)。**兩個方向都改變「文件=現實」,必須拍板** | 若實作:列出全部 9 處要動的檔與行;若刪:列出全部宣稱此乘數的文件行 |
| B3 | **M2:sector 5 值 enum 死規則** | script 加 sector 模式輸出 5 級,或 sector 文件收斂為 3 級(STEP D 改以 FRAGILE 觸發) | 對 top-3 HOT proxy ETF 實跑,看 5 級制下是否真的會出現 EXTREMELY_FRAGILE |
| B4 | **資料源遷移 technical_core** | 三支遷 `fetch_history`(FMP 主源)。風險:調整口徑差異(auto_adjust vs FMP eod)會漂移 vol/dd → 分級可能在帶邊翻轉 | 兩源對 ≥10 ticker 平行算,列 metrics 差異與 label 翻轉數;0 翻轉才可視為 A 級安全遷移 |
| B5 | **insider 換 fmp_supplementary** | string-sniffing(`:53-72`)換 `skills/_shared/fmp_supplementary.py` 的 insider 資料(24h cache) | 對 ≥10 ticker 對照兩法的 BUY/NEUTRAL/SELL 一致率 |
| B6 | **drawdown-circuit-breaker 概念**(上游) | 帳戶層連敗冷卻/週月虧損上限 → 「今天可否開新倉」。需先解決 realized P&L 資料源(positions.json 只有現況) | 設計文檔即可,不寫 code |
| B7 | tail-risk normalizer 再校準 + sector off-band 門檻(`<40`/`>70`)對齊 | 2026-04 校準已老 | shadow:新舊校準對 history cohort 的 label 翻轉表 |

**B 批共同紅線**:任何會改變歷史 replay 結果的常數變更,必須先跑 `replay_trade_plan.py` 三 cohort 拿基線,變更後 `current_rule_mismatched` 的變化要能逐筆解釋。

---

## 5. 參考素材

- 上游 repo(MIT):https://github.com/tradermonty/claude-trading-skills
  - `skills/position-sizer/scripts/position_sizer.py` — fixed-fractional / ATR-based / Kelly 三法 + `apply_constraints`(max position % / max sector %)+ 整股 floor。B1 選項 (ii) 的機制來源
  - `skills/drawdown-circuit-breaker/scripts/check_circuit_breaker.py` — `TRADING_ALLOWED/COOLDOWN/HALTED` 三態、日/週/月虧損門檻(帳戶 %)、連敗冷卻。B6 的機制來源
- 本 repo 慣例樣板:`skills/valuation-modeler/`(多模組 + tests)、`skills/momentum-monitor/scripts/momentum.py:175`(atomic write)、`skills/_shared/technical_core.py:97`(fetch_history)
- fork 系 skill 的 upstream alignment 紀錄慣例:見任一 SKILL.md 頂部 blockquote(V4.111.6 起)——本批完成後三支也要補(它們是專案原生,格式參照 market-sentiment-analyzer 的 native 標註)

## 6. 回報格式(三件套)

- **Batch A 收尾回報 ≤30 行**:改了哪些檔(路徑:行號區間)| 每條驗收的證據(rc + 末行輸出)| 基線 diff 結論(成功路徑 0 差異的證明)| 種 bug 紅過的截圖行
- **Batch B 回報**:每項一份備忘(落檔 `docs/plan_risk_trio_B<N>.md` 或併入本檔附錄),對話只回結論行
- 兩次嘗試後驗收仍不過 → 停手,回報兩次失敗軌跡(做了什麼、卡哪條驗收、報錯原文),不要硬繞
- 收尾:版本 bump(patch)三處 + SYNC OK、SESSION_NOTES 新 note、TODO v4.111.6 區塊的風控三支項銷掉、MARKET_INDEX 同步、LESSONS(若踩坑)
