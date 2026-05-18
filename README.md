# AI 投資委員會

多 Agent 投資分析系統，由三個 Claude Code protocol + 短期戰術層 + 23 個 skill + 本地 Dashboard 組成。

**當前版本**：`v2.20.0` (2026-05-10)

**三層時間維度設計**：
- **長期 (12 月)**：`earnings-valuation-forecaster`（基本面合理價）
- **中期 (3-6 月)**：`investment_protocol_v5_0.md`（5-lane 委員會辯論 + Burry + Red Team → BUY/HOLD/SELL）
- **短期 (1-15 天)**：`thematic-screener` + `short-term-target`（**Tactical Opportunity Radar**）

**V2.18-V2.20 系統升級**（解 MU/QCOM 超級週期錯失系統 bug）：
- V2.18 Structural Shift Modulation：earnings tier (NONE/CANDIDATE/CONFIRMED) → Phase 3 modulation 解除 backward-looking lane 三重壓制
- V2.19 Lane Cross-Talk Wiring：polarization 4-tier (BIPOLAR/OUTLIER/MIXED/ALIGNED) + Red Team anti-spoofing classifier (mr veto)
- V2.20 UI Decision Layer + Backtest 深化 + Dynamic Threshold + Lane Freshness

---

## 快速開始

```bash
./open_dashboard.sh       # 啟動 Dashboard + positions API + 定時刷新
```
→ `http://localhost:8080/decisions.html`

### 常用指令（在 Claude Code 內）

| 指令 | 執行 | 用途 |
|---|---|---|
| `產業掃描` | `sector/sector_protocol_main.md` | 產業熱度 + macro regime → sector_intel.json |
| `分析 [TICKER]` | `investment/investment_protocol_v5_0.md` | 中期深度 5-lane + Burry + Red Team |
| `財報 [TICKER]` | `skills/earnings-analyst/SKILL.md` | FMP 三表 8Q + 品質 flag + structural_shift tier |
| `新聞分析 DIGEST` | `news/news_protocol_v2.md` | RSS 多源 → 兩階段漏斗 + Debate |
| `新聞分析 FLASH [text]` | `news/news_protocol_v2.md` | Deep Debate only |
| `動能 [TICKER]` | `skills/momentum-monitor/scripts/momentum.py` | 個股動能 0-100 |
| `動能選股` | `skills/momentum-monitor/scripts/screen.py` | S&P500 universe scan |
| `更新 journal` | `skills/momentum-monitor/scripts/journal.py` | 5/20/60d forward return 追蹤 |
| `財報前瞻 [TICKER]` | `skills/earnings-valuation-forecaster/scripts/forecast.py --pre-earnings` | UI 自動 morph (≤7d) |

---

## 一個禮拜的工作流程 (Weekly Workflow)

### 📅 Mon-Fri 盤前 (Daily, ~3-5 min auto)

```bash
./daily_update.sh       # 7 step 全自動
```

| Step | 動作 | 輸出 |
|---|---|---|
| 1 | 市場廣度（TraderMonty CSV） | `sector/breadth_cache/` |
| 2 | FTD 偵測（yfinance） | `sector/ftd_cache/` |
| 3 | 市場頂部偵測（yfinance） | `sector/market_top_cache/` |
| 4 | FRED 宏觀 12+ series | `skills/fred-macro/cache/` |
| 5 | 整合 → Dashboard | `Dashboard/data.json` |
| 5.5 | ETF holdings 90-day 自動 refresh check | `skills/thematic-screener/etf_meta.yaml` |
| 6 | Thematic Screener (Tactical Opportunity Radar) | `skills/thematic-screener/data/recommendations/<DATE>.json` |
| 7 | **Structural Watchlist (V2.19.1)** | `news/news_logs/structural_watchlist.json` + `watchlist_history/<DATE>.json` + `watchlist_lifecycle.jsonl` |

**設計原則**：所有 step 純讀 cache（除 FRED API），無 production trade 行為，failure non-fatal。

### 📅 Mon (週初定調)

1. **盤前**：`./daily_update.sh`
2. **開盤前 30 min**：開 Dashboard `http://localhost:8080`
   - 看 Layer 1 macro regime + breadth zone
   - 看 Layer 5 **Structural Watchlist tile**（V2.19.1 加）
3. **產業掃描**：手動跑（週一更新最完整 sector intel）
   ```
   產業掃描
   ```
   → `sector/logs/sector_intel.json`（決定本週 sector 偏好）

### 📅 Tue-Thu (Active)

每日固定：
- `./daily_update.sh` 跑（auto）
- 開 Dashboard 看：
  - watchlist tile 新進 candidate（NEW badge 綠色）
  - earnings 卡片 SHIFT⚡⚡ / SHIFT⚡ badge（V2.20.0）
  - decisions 卡片 BIPOLAR/OUTLIER + RT MR-ONLY/CONTAM 警示

事件驅動：
- 重要財報報出 → 自動 trigger `python3 skills/earnings-analyst/scripts/fetch.py + analyze.py`（再開 dashboard 刷新）
- 重大新聞 → `新聞分析 FLASH "<headline>"`
- 想做交易 → `分析 [TICKER]`（5-lane 委員會 5-10 min）
- 財報前 7 天內 → 開 dashboard 在 earnings card 點 📋 **前瞻** button

### 📅 Fri (週末準備)

1. 盤後 `./daily_update.sh`
2. 視需求 `產業掃描` 重跑（更新 sector_intel）

### 📅 Sat-Sun (週末 Review，~10-15 min)

```bash
# 1. 戰術層校準（短期 5d hit rate）
python3 skills/short-term-target/scripts/weekly_review.py
# → reports/SHORT_TERM_WEEKLY_<DATE>.md

# 2. 投資 protocol 決策回顧
python3 investment/scripts/backtest_postmortem.py
# → 過去 N 天決策 vs yfinance 實際走勢 / phase 失準點

# 3. Watchlist signal quality 拆解 (V2.19.2 / V2.20.0)
python3 investment/scripts/backtest_watchlist.py
# → reports/WATCHLIST_BACKTEST_<DATE>.md
# → 含 random sector baseline / per-keyword / per-credibility / horizon sweep

# 4. (Optional) Provider drift check
python3 skills/finnhub-client/scripts/audit_drift_check.py
```

**校準紀律**：
- `weekly_review.py` 只**建議** weights.yaml 調整 — 由 user 手動編輯 + bump `weights_version`
- `backtest_*.py` 純讀檔 + 輸出 report，**永不**自動覆寫 config / protocol parameters
- 看 V2.19.2 Backtest Out-of-Scope 清單：n<50 期間只當 directional sanity，不當 production rule

---

## Backtest 列表（V2.20.0 現有 3 套）

| Backtest 腳本 | 對象 | 輸入 | 輸出 |
|---|---|---|---|
| **`investment/scripts/backtest_postmortem.py`** | 投資 protocol decisions | `reports/<DATE>_<T>.md` + yfinance 實際走勢 | 過去 N 天每筆決策的 phase-by-phase 失準分析 (Phase 0/1/2/3 哪段判錯) |
| **`investment/scripts/backtest_watchlist.py`** (V2.19.1+) | News structural_watchlist signal quality | `news/news_logs/watchlist_lifecycle.jsonl` + earnings cache + FMP price | (1) tier graduation rate + lead time<br>(2) forward returns 5d/15d/45d/90d vs SPY/sector ETF<br>(3) random sector baseline (B1)<br>(4) per-keyword α 拆解 (B2)<br>(5) per-credibility 切片 (B3)<br>(6) horizon sweep (B4) |
| **`sector/scripts/backtest_step6_overlay.py`** | Sector daily Step 6 overlay | sector_intel + step6 cache | sector overlay 偏好對比 |

`backtest_watchlist.py` 旗標：
- `--dry-run` (V2.20.0)：純 stdout 不寫 reports/

**真實驗證需 watchlist accrue**：
- E1: lifecycle ≥ 30 events，覆蓋 ≥ 3 sector
- E2: ≥ 5 個 evicted_no_graduation 樣本（算 false positive rate）
- E3: ≥ 3 個自然 graduated_confirmed（算真 lead time，不是 lookback artificial）

詳見 `TODO.md` 路線 V20 V2.20.X section。

---

## Skills 索引（24 個 skill）

詳細描述 + integration 點見 `skills/MARKET_INDEX.md`。

### 📊 Market State Layer（市場狀態，daily auto）

| Skill | 主腳本 | 用途 | 觸發 |
|---|---|---|---|
| `fred-macro` | `scripts/fetch.py` | FRED 12+ series → regime signals (real_rate / yield_curve / NFCI) | daily Step 4 |
| `market-breadth-analyzer` | `scripts/market_breadth_analyzer.py` | TraderMonty CSV → 5-component 0-100 score | daily Step 1 |
| `market-top-detector` | `scripts/market_top_detector.py` | O'Neil DD + Minervini + Monty defensive rotation 0-100 | daily Step 3 |
| `ftd-detector` | `scripts/ftd_detector.py` + `post_ftd_monitor.py` + `rally_tracker.py` | Follow-Through Day 偵測 + state machine | daily Step 2 |

### 🔍 Sector / Theme Layer（產業 / 主題）

| Skill | 主腳本 | 用途 |
|---|---|---|
| `theme-detector` | `scripts/theme_detector.py` | 主題熱度 + lifecycle 偵測（V2.19.2 加 structural_shift_bonus） |
| `thematic-screener` | `scripts/screen.py` + `enrich.py` + `refresh_etf_holdings.py` | Top N themes × Top M movers → recommendations |
| `sector-analyst` | `scripts/analyze_sector_rotation.py` | 11 sector rotation 分析 |

### 💰 Earnings Layer（財報層）

| Skill | 主腳本 | 用途 |
|---|---|---|
| `earnings-analyst` | `scripts/fetch.py` + `analyze.py` + `render.py` | FMP 三表 8Q + composite 0-100 + **structural_shift tier** (V2.18) |
| `earnings-valuation-forecaster` | `scripts/forecast.py` | 12mo Bull/Base/Bear FV + `--pre-earnings` cheat sheet |
| `earnings-trade-analyzer` | `scripts/analyze_earnings_trades.py` | 5-factor scoring (gap/trend/volume/MA200/MA50) |
| `economic-calendar-fetcher` | `scripts/get_economic_calendar.py` | FMP econ calendar |

### 🎯 Decision Layer（決策層）

| Skill | 主腳本 | 用途 |
|---|---|---|
| `short-contrarian-analyst` | `scripts/burry_score.py` | Burry-style contrarian Inline 用 |
| `tail-risk-analyzer` | `scripts/tail_risk.py` | Tail risk fragility 評估 |
| `portfolio-risk-manager` | `scripts/risk_manager.py` | Portfolio-level concentration / volatility |
| `market-news-analyst` | (Claude Code skill) | 新聞 protocol 多 agent debate |
| `market-sentiment-analyzer` | (Claude Code skill) | Phase 0 sentiment lane |

### 📈 Stock-Level Tools（個股工具）

| Skill | 主腳本 | 用途 |
|---|---|---|
| `momentum-monitor` | `scripts/momentum.py` + `screen.py` + `journal.py` | 動能 0-100 + S&P500 scan + forward return tracking |
| `technical-analyst` | `scripts/analyze.py` | 技術面 lane（用於投資 protocol Phase 2） |
| `us-stock-analysis` | `scripts/analyze.py` | 通用個股 deep-dive |
| `short-term-target` | `scripts/predict.py` + `weekly_review.py` | 1d/5d/15d 目標價 + 戰術建議 |
| `supply-chain-event-analyst` | `scripts/chain_mapper.py` | 供應鏈事件影響鏈分析 |

### 🔌 Data Provider Layer（資料抓取）

| Skill | 主腳本 | 用途 |
|---|---|---|
| `finnhub-client` | `scripts/finnhub_client.py` + `dual_fetch.py` + `diff_tool.py` + `audit_drift_check.py` | Finnhub API throttle/cache + Finnhub vs FMP cross-check |
| `_shared` | `company_context.py` + `fmp_supplementary.py` | 共用 FMP profile/peers (24h cache) |

---

## 專案結構

```
AI投資委員會/
├── bridge.py                  ← 整合所有 cache → Dashboard/data.json
├── dashboard_server.py        ← Local HTTP server + positions API + mtime auto-refresh
├── daily_update.sh            ← 7-step daily auto refresh
├── positions.json             ← 使用者手動持倉
│
├── Dashboard/                 ← Pure HTML/JS (index/decisions/sector/news/earnings/calendar/momentum/radar)
├── investment/                ← 個股分析 protocol_v5_0 + scripts + invest_logs
├── sector/                    ← 產業掃描 protocol + scripts + breadth/ftd/market_top cache
├── news/                      ← 新聞 protocol_v2 + scripts + news_logs (含 V2.19 watchlist)
├── reports/                   ← 所有最終 MD 報告 (audit trail) + decision_review/
├── skills/                    ← 24 個 Claude Code skills
└── archive/                   ← 歷史版本歸檔
```

---

## 腳本用途速查（Script Index）

### Ops / 自動化（被 daily_update.sh 串起）

| 腳本 | 用途 | 觸發 |
|---|---|---|
| `daily_update.sh` | 7-step 全自動 daily refresh | 每日早上手動或 cron |
| `bridge.py` | 整合 cache + watchlist + theme overrides → `Dashboard/data.json` | daily Step 5 |
| `dashboard_server.py` | Local HTTP server + positions API + auto-refresh | `./open_dashboard.sh` |
| `news/scripts/build_structural_watchlist.py` (V2.19.1) | 14d hit / 21d eviction / 2-source gate watchlist + lifecycle log | daily Step 7 |

### 投資 Protocol Layer

| 腳本 | 用途 |
|---|---|
| `investment/scripts/validate_phase0.py` | Phase 0 macro JSON 校驗 gate |
| `investment/scripts/validate_session_export.py` | Phase 5 export schema 校驗（V2.19+ 加 polarization + red_team_basis 必填） |
| `investment/scripts/validate_v219.py` | V2.19 fixture 16 case test (polarization 4-tier + RT basis 4-tier) |
| `investment/scripts/validate_markdown_export.py` | MD 報告格式校驗 |
| `investment/scripts/apply_det_shadow.py` | Phase 5 後處理：polarization + red_team_basis classifier (V2.19+) + lane_freshness (V2.20+) |
| `investment/scripts/register_thesis.py` | Phase 5.5 thesis registry 註冊（含 structural_shift pickup） |
| `investment/scripts/backtest_postmortem.py` | 投資 protocol decisions backtest |
| `investment/scripts/backtest_watchlist.py` (V2.19.1+) | News watchlist signal quality backtest (4-layer 拆解) |
| `investment/scripts/fmp_endpoint_probe.py` | FMP 端點可用性探測 |

### News Protocol Layer

| 腳本 | 用途 |
|---|---|
| `news/scripts/stage1_triage.py` | Shallow triage 30 items |
| `news/scripts/assemble_digest.py` | Stage 2 deep debate digest assembly |
| `news/scripts/build_structural_watchlist.py` (V2.19.1) | Structural keyword watchlist + decay rules |
| `news/scripts/validate_digest_output.py` | Digest schema 校驗 |

### Sector Protocol Layer

| 腳本 | 用途 |
|---|---|
| `sector/scripts/fetch_general_news.py` | Macro news ingestion |
| `sector/scripts/fetch_sector_news.py` | Per-sector news |
| `sector/scripts/fetch_sector_valuation.py` | Sector valuation overlay (FMP) |
| `sector/scripts/fetch_smart_money.py` | Smart money flow proxy |
| `sector/scripts/fetch_earnings_pulse.py` | Sector earnings pulse |
| `sector/scripts/render_sector_report.py` | Sector MD report render |
| `sector/scripts/validate_sector_intel.py` | sector_intel JSON 校驗 |
| `sector/scripts/step6_overlay.py` | Step 6 daily overlay (sector preference) |
| `sector/scripts/backtest_step6_overlay.py` | Sector overlay backtest |

### 其他 root scripts

| 腳本 | 用途 |
|---|---|
| `scripts/build_event_index.py` | Calendar event indexer |
| `scripts/render_event_index.py` | Calendar markdown render |
| `scripts/check_skills.py` | skills/*/SKILL.md frontmatter 校驗 |
| `scripts/verdict_rules.py` | Decision verdict 規則校驗（pass/miss judgment） |
| `scripts/parse_firstrade_notifications.py` | Firstrade 推播解析 |
| `scripts/parse_futu_notifications.py` | 富途牛牛推播解析 |

---

## V2.18-V2.20 系統變更摘要

詳細紀錄見 `CHANGELOG.md`。本節是高層導覽。

### V2.18 Structural Shift Modulation
**問題**：MU/QCOM 超級週期被三個 backward-looking lane (Valuation/Red Team/Macro) 同時壓制 → DEFENSIVE HOLD 錯失主升段。

**解法**：earnings-analyst 計算 `structural_shift.tier`（NONE/CANDIDATE/CONFIRMED）→ Phase 3 Step 1.5 modulation 解除 backward-looking 攻擊。

**觸發 signals (≥2 of 3)**：
- EPS QoQ ≥ 30%
- 毛利率 ≥ 歷史 8Q 平均 + 2σ
- 營收 YoY ≥ 25% AND 加速

### V2.19 Lane Cross-Talk Wiring
**問題**：lane 各自為政，PM 沒做 divergence detection。

**解法**：
- `compute_polarization` 升 4-tier（BIPOLAR / **OUTLIER** 新增 / MIXED / ALIGNED）
- Red Team anti-spoofing classifier 4-tier (`pure_forward` / `pure_mean_reversion` / `contaminated` / `unclassified`)
- News structural_watchlist (14d/21d decay) — leading metadata，不入決策
- Phase 2.8 Red Team prompt 加 STRUCTURAL_SHIFT_TIER input

### V2.19.1 / V2.19.2 / V2.20.0
- V2.19.1：watchlist archival (daily snapshot + lifecycle.jsonl) + UI tile + backtest skeleton
- V2.19.2：theme heat bonus + ⚡ badge cross-page + backtest forward returns (FMP price + sector ETF α)
- V2.20.0：UI Decision Layer (decisions/earnings/sector 三頁 surface 全部 V2.18+ badges) + Backtest 4-layer 深化 (random baseline / per-keyword / per-credibility / horizon sweep) + Dynamic threshold (CONFIRMED+ALIGNED → 1.0 / BIPOLAR → 1.5) + Lane freshness penalty (5 lane 各自 fresh window)

---

## 環境需求

- **Runtime**: Python 3.9.6+ (系統路徑 `/usr/bin/python3`)
- **Dependencies**: `requests`, `beautifulsoup4`, `lxml`, `pandas`, `numpy`, `yfinance`, `finvizfinance`
- **Frontend**: 現代瀏覽器（Dashboard 為純靜態 HTML/JS/CSS）
- **Tooling**: Claude Code CLI / Gemini CLI
- **API Keys** (env vars): `FMP_API_KEY` / `FRED_API_KEY` / `FINNHUB_API_KEY` / `FINVIZ_API_KEY` (optional)

---

## 工作流規則與設計哲學

### 1. 實作前確認 (Pre-implementation Confirmation)
**觸發**：≥ 2 個檔案 OR 單一檔案 ≥ 50 行。
**摘要表**：File / Action / Est. Lines / Description + total tokens。
**排除**：reports/* 報告、*_logs/* 緩存 JSON、Dashboard/data.json 自動產出。

### 2. Session 完成檢查清單
**Session 定義**：人為發起的 dev / refactor / fix。
1. **Bump VERSION**：三處同步 — `VERSION` + `Dashboard/utils.js` + `CHANGELOG.md`（major/minor/patch 適度選擇）
2. **更新 SESSION_NOTES.md / TODO.md**

**🚫 EXCLUSION**：所有 protocol run（`產業掃描`、`分析 [TICKER]` 等）**不算** session，不 bump version。

### 3. Anti-Adversarial 鐵律 (V2.19+)
1. **mr 一票否決**：mean-reversion keyword 一旦出現都觸發 Red Team dampening (`contaminated` ≠ `mixed`)
2. **OUTLIER 不誤殺**：4-vs-1 outlier ×0.85，不像 BIPOLAR 砍倉 75%
3. **Watchlist 強制衰減**：14d/21d 防幽靈數據，single-source 不入榜
4. **Backtest 不自動寫 config**：所有校準由 user 手動 + bump `weights_version` / `params_version`

---

## 文件索引

- `CLAUDE.md` — Agent 核心執行規範（極簡）
- `CHANGELOG.md` — 版本歷史完整紀錄（V2.18-V2.20 細節）
- `SESSION_NOTES.md` — 市場 regime 狀態 + Token 優化紀錄
- `TODO.md` — 當前 backlog (V2.20.X / V2.21+) + 歷史 archive
- `investment/investment_protocol_v5_0.md` — 5-lane 委員會 protocol
- `investment/phase5_export_schema.md` — session_export schema (V2.19+ polarization + red_team_basis 必填)
- `news/news_protocol_v2.md` — RSS 兩階段漏斗 + Phase 4.5 watchlist
- `sector/sector_protocol_main.md` — 產業掃描 protocol
- `skills/MARKET_INDEX.md` — 24 個 skill 索引 + integration map
- `skills/earnings-analyst/SKILL.md` + `schema.md` — earnings tier 設計
- `skills/short-term-target/README.md` — 短期戰術詮釋
- `skills/thematic-screener/README.md` — 戰術推薦聚合用法
- `skills/finnhub-client/README.md` — dual-fetch + audit drift 用法

---

## Tactical Opportunity Radar — 短期戰術層

**目的**：補足 investment_protocol 的 1-15 天空白。**完全並行運作不影響投資協議決策**。

```
每天 (auto):
  daily_update.sh Step 6
    → thematic-screener
        → 讀 theme-detector cache (Top 5 themes by heat)
        → 對每個 theme 的 representative_stocks
            → 呼叫 short-term-target.predict() (subprocess)
        → 加 concentration WARNING (同主題 ≥2 picks → 標警示)
        → 加 regime snapshot (SPY/RSI/MA50/VIX/FRED)
    → 寫 data/recommendations/<DATE>.json

  daily_update.sh Step 7 (V2.19.1):
    → build_structural_watchlist
        → 14d hit / 21d eviction / 2-source first-hit gate
        → daily snapshot 寫 watchlist_history/<DATE>.json
        → append lifecycle.jsonl (5 event enum)

每週末 (manual):
  weekly_review.py        → reports/SHORT_TERM_WEEKLY_<DATE>.md
  backtest_postmortem.py  → 投資 protocol decisions vs 實際走勢
  backtest_watchlist.py   → reports/WATCHLIST_BACKTEST_<DATE>.md (含 random baseline)
```

### KPI gate（自我退役機制）

連續 8 週 5d hit rate < 50% **OR** 中位 alpha vs benchmark < 0% (N≥30) → 整套 thematic-screener 退役。Per `plan_short.md §6 + §12.H`。

V2.19+ watchlist 額外 KPI：
- watchlist 6 個月後若 false positive rate > 50% (evicted_no_graduation 比例) → 砍 keyword whitelist 或廢 watchlist
- 真 graduated_confirmed 樣本 ≥ 5 後可推 V2.21 News provisional → tier modulation 設計
