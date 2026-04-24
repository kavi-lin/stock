# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + [SemVer](https://semver.org).
Single source of truth for version history. Current version authority is `VERSION` file + `Dashboard/utils.js`.

> **Purpose**: Let future Claude sessions (and humans) understand the evolution
> of the system — what changed, where to look, why. Entries link back to git
> commits where applicable; for un-committed work, dates reflect local VERSION
> bump time.

---

## [1.42.2] — 2026-04-25
### Changed — Sector protocol token diet (round 2)
- **`sector_protocol_main.md`**: Step 1 / Step 6 sections trimmed of explanatory parentheticals (confidence-gating tutorial, replaces-Step-1 rationale, renderer note for users). Step 6 now points to `step6_overlay.py` script as authoritative; spec table compressed (10 regimes → 8 rows by grouping equal weights).
- **`sector/phase_0.md`**: (already lean — script `--skip-if-fresh 10800` flag adopted in protocol so LLM no longer needs to compare mtime manually).
- **`sector/phase_1-2-3.md`**:
  - Phase 2: replaced manual mtime check with `theme_detector.py --skip-if-fresh 10800` (script self-manages cache); trimmed historical 4-25 observation comment.
  - Phase 3: collapsed step descriptions, dropped budget comparison footnote.
- **`sector/phase_4-5.md`**:
  - Phase 4a Fan-In rules + FRED Macro Lane Prompt: removed parenthetical explanations.
  - Phase 4b consensus_warning: tighter table form.
  - Phase 4c STEP C.6: dropped "比 LLM 心算快 1 分鐘" timing footnote.
  - Phase 4c STEP G.5: removed dotcom/SPAC historical lesson narrative.
  - Phase 4c STEP H today_verdict: dropped Dashboard localization explanation paragraph + concrete chinese examples; kept rules + schema only.
- **`sector/README.md`**: absorbed all moved rationale into 5 new sections (Step 1 vs Step 6 / confidence gating / G.5 historical evidence / Phase 3 budget origin / Phase 4c Step 6 script / theme_detector timeout warning).
### Why
- Each `產業掃描` run loads sector_protocol_main + phase_0 + phase_1-2-3 + phase_4-5 + schema (~1300 lines). Every removed line × every run = real LLM token savings.
- This is the second pass after v1.41.1 (which moved older v1.2/v1.3 narrative). v1.42.0/v1.42.1 added FRED-related explanations that needed similar treatment.
- Net change: protocol files 1464→1423 lines (-3%, -41 lines) but ~70 lines of explanation moved out of LLM hot path → README.

---

## [1.42.1] — 2026-04-25
### Changed — Sector protocol speed pass (3 bottlenecks)
- **Phase 3 web fetch budget**: 4-25 run did 19 WebSearch in a subagent. New rule forces structured tools first (`market-sentiment-analyzer` → `economic-calendar-fetcher` → `earnings-calendar` → reuse `_phase0.fred_snapshot`), then HARD CAP ≤ 5 narrative WebSearch. Provided exact 5-query template + ban list (Russia/Ukraine, FDA PDUFA, bank earnings dates, copper price, AI capex, DOJ Powell — out of sector-level scope). Expected: 3.5min → 1.5min.
- **Phase 2 theme_detector runtime documented**: Added explicit warning that script needs 140-180s; ban `timeout < 240` wrappers (4-25 run wasted 145s on a `timeout 150` kill+retry); ban `--output-dir reports/` + cp dance. Expected: 3.3min → 0.8min.
- **Phase 4c Step 6 multiplier via script** (not LLM hand-computation): `step6_overlay.py` got a real CLI (`--input "Sector:Score,..."`). Phase 4c protocol now MANDATES script execution — paste JSON output directly into `sectors[].step6_fred_multiplier`. Expected: 6.9min → 5.9min.
### Why
- 4-25 sector scan ran 20 min. Phase-by-phase decomposition: Phase 0=63s / Phase 1=52s / Phase 2=3m17s / Phase 3=3m34s (subagent + 19 WebSearch) / Phase 4a=109s (verified parallel via single-message agent calls) / Phase 4b=2m7s / Phase 4c=6m52s (LLM thinking + 27KB JSON write) / Phase 5=18s.
- Phase 4a parallelism confirmed working (4 lanes in `msg_01U6D4...` single message, wall-clock = max lane = 109s vs sequential 372s).
- Estimated combined impact: 20min → ~14-15min after these 3 changes land.

---

## [1.42.0] — 2026-04-25
### Added — FRED 整合（兩 protocol + 強化 Red Team）
- **`sector/scripts/step6_overlay.py`**: deterministic Step 6 multiplier calculator. Base regime × cyclical/defensive matrix (10 regimes) + sector-specific favor/avoid override + regime_confidence gating (`effective = 1.0 + (raw − 1.0) × confidence`). Used by patcher, renderer, backtest harness.
- **`sector/scripts/backtest_step6_overlay.py`**: backtest harness using `fred-macro --asof DATE` + yfinance forward returns. Top-3 vs bottom-3 spread comparison with/without Step 6 multiplier. Currently smoke-test (n≈5 sessions) — becomes statistically valid as logs accumulate (target n ≥ 50).
- **`investment/scripts/validate_phase0.py`**: V4.9 mini-gate. Catches LLM skipping FRED L4 (most common drift mode). Checks `fred_available` / `fred_snapshot.regime_label` / `macro_multiplier_rationale` references FRED.
- **Sector Phase 4a 4th lane (`FRED_Macro_Analyst`)**: parallel subagent reads `_phase0.fred_snapshot` + `SECTOR_ROTATION_GUIDE.md`, proposes favor/avoid per regime.
- **Sector Phase 4c STEP G.5 — Macro/Theme conflict**: when FRED-Avoid sector is HOT-promoted by Theme/Rotation lane → cap WARM, +`macro_theme_divergence` flag, ×0.90 confidence. Anti-1999-dotcom/2021-SPAC rule (theme heat + macro warning = bubble top).
- **Sector Phase 4b DA prompt**: now receives slim FRED snapshot. Conflict rule: yield_curve_inverted / real_rate>2 / credit_stress / Recession-Risk regime / sector ∈ avoid → MUST construct kill_conditions citing **specific FRED values**, not vague "macro 轉差".
- **Investment Phase 2.8 Red Team prompt**: same slim FRED paste + same conflict rule. `counter_evidence_strength` ≥ 4 auto-applied when ≥ 2 FRED conflict signals trip.
- **Sector schema**: `_phase0.fred_snapshot` slim (11 fields) + `sectors[].step6_fred_multiplier` + top-level `step6_overlay` block.
- **Sector renderer**: new `FRED×` column in FINAL VERDICT TABLE (when overlay applied) + new "Step 6 — FRED Regime Overlay" section.
- **Sector validator**: enforces `_phase0.fred_available` + `fred_snapshot` slim shape compliance.
### Changed
- **`skills/fred-macro/scripts/fetch.py`**: composite score now uses **latency-weighted** average. Real-time series (rates / credit / NFCI) weight 1.0; ICSA-mixed employment 0.7; CPI/PCE inflation 0.5. Solves the "Lag Trap" (54-day-stale CPI driving today's regime overlay). composite changed 60→62 in current snapshot (negative inflation_score down-weighted).
- **Sector Step 1 cycle_phase multiplier**: now SKIPPED when `fred_available=true` (Step 6 takes over). Avoids double-counting regime via two LLM heuristics.
- **Sector Phase 0**: new Layer E (FRED MUST-run) parallel to A-D.
### Why
- Audit revealed: across 7 recent investment runs (4-23 to 4-24), **0/7** populated `fred_available` / `fred_snapshot` / `macro_multiplier_rationale` despite V4.9 spec marking these MUST-run. `validate_session_export.py` only checks Phase 5 export, never gates phase0.
- Sector protocol had **zero** FRED integration. Today's run produced HOT for Industrials and WARM for Tech while FRED simultaneously flagged "Overheating regime, avoid Tech/Real Estate/Cons Disc" — major macro-vs-sector divergence with no mechanism to surface it.
- Gemini review caught Lag Trap + double-count + token bloat issues; partially adopted (lagging-tier weighting fix; Step 6 replaces Step 1; slim FRED paste). Disagreed on lane-conflict resolution (Gemini wanted theme to override macro; reversed direction per dotcom/SPAC history).

---

## [1.41.1] — 2026-04-24
### Changed
- **Sector protocol 檔案瘦身**：`sector_protocol_main.md` / `phase_0.md` / `phase_1-2-3.md` / `phase_4-5.md` 全面移除人類向敘述、計算範例、歷史沿革，僅保留 LLM 執行所需的規則與步驟。Protocol 總行數 702 → 641（-9%）。
- **`sector/README.md` 擴充**：吸收移走的內容（Phase 0 三訊號合成計算範例 ×2、Phase 5 機械化背景與動機、文檔分工說明、V1.4 changelog 條目）。檔案分工原則寫入 README 開頭：protocol 檔只給 LLM 看，README 只給人看，避免雙邊漂移。

---

## [1.41.0] — 2026-04-24
### Added
- **`sector/scripts/render_sector_report.py`** — deterministic JSON→Markdown renderer for Phase 5. Reads latest `sector_logs/*_sector_intel.json`, emits `reports/YYYY-MM-DD_sector_report.md` with 7 sections (Verdict table, Macro, Today's Verdict, DA challenges, Divergence, Themes, Handoff). Zero LLM calls.
### Changed
- **Sector protocol V1.4**: Phase 5 is now a mechanical step (JSON write → validator → renderer → user summary). Portfolio Strategist MUST NOT rewrite markdown; if output is wrong, fix the JSON or the renderer.
- `sector/phase_4-5.md` Phase 5 section rewritten with 4 discrete steps and an explicit "≤ 10 行 summary, do not repeat today_verdict" instruction to the model.
- `sector/sector_protocol_main.md` Rule 5 updated to reflect renderer ownership of markdown output.
### Why
- Today's sector scan took 26 min (`sector/scan_logs/sector_20260424_210620.log`). Timeline reconstruction showed 663s of pure LLM generation for Phase 5 markdown + 225s for the final summary — both redundant because `_phase4c.today_verdict` already carries the zh-TW narrative. Rendering from JSON reclaims ~15 min per run.

---

## [1.40.0] — 2026-04-24
### Added
- **Phase 0 L4 FRED integration** in `investment_protocol_v4_8.md` — MUST-run `fred-macro` skill alongside existing 3-layer cache cascade, outputs `fred_snapshot` block with 12 official series (rates / inflation / employment / credit / stress).
- **Macro multiplier blending rules** — LLM baseline from headline-score table + up to 4 FRED-derived caps (yield_curve_inverted 0.75 / credit_stress 0.85 / NFCI>0 0.9 / real_rate>2 0.9) taking min. All-clear bonus × 1.05.
- **`macro_multiplier_rationale` field** (mandatory) documenting the blend decision per run.
- **Dashboard FRED refresh thread** — `dashboard_server.py` adds `fred_refresh_loop` daemon at 15-min cadence (`FRED_REFRESH_SEC=900`), independent of the 5-min bridge loop.
- **`bridge.py` injects `fred_macro` into `data.json`** so Dashboard pages have access without each page re-fetching.
### Changed
- GLOBAL RULES §8 MUST-run list adds `fred-macro` (failure non-blocking; `fred_available=false` continues flow).

---

## [1.39.0] — 2026-04-24
### Added
- **`fred-macro` skill** (`skills/fred-macro/`) — fetches 12 key FRED series via free API (120 req/min, no daily cap). Output: per-series `{value, date, yoy/mom change, percentile_1y, trend_30d}` + aggregate `regime_signals` (yield curve, fed direction, real rate estimate, credit stress).
- Parallel fetch via `ThreadPoolExecutor(6)` → 2-second run for 12 series.
- 15-minute atomic-write cache at `skills/fred-macro/cache/fred_latest.json`.

---

## [1.38.4] — 2026-04-24
### Changed
- Preset tooltip criteria now show translated label (`強多` not `STRONGLY_BULLISH`) and clarify that "Hot Sector" (dynamic from sector scan) differs from the manual "Sector" dropdown (page-momentum.js).

## [1.38.3] — 2026-04-24
### Added
- **Preset-button hover tooltip** — reuses existing pill-tooltip system; new `PRESET_DETAIL_ZH/EN` dicts with 3-section layout (criteria / strategy / action) for all 10 presets.
- `data-preset-tip` attribute + purple accent CSS class.

## [1.38.2] — 2026-04-24
### Added
- **MACD column click popup** mirrors RSI popup structure — header values + zero-axis position bar + 4-quadrant regime map (strongest_bull / weakening_bull / reversal_bull / strongest_bear) + personalised advice.
### Changed
- MACD cell: removed native `title=` tooltip, cell is now clickable.

## [1.38.1] — 2026-04-24
### Added
- MACD column sortable (`data-sort="macd_hist"`).
- **Custom pill hover tooltip** for 11 signals + 7 warnings — replaces ugly native `title=` with a themed card (green for signals, red for warnings), each with description + actionable hint.

## [1.38.0] — 2026-04-23 (commit 4ff7849)
### Added
- Leader button + i18n fixes; MACD column first appearance.
- Earlier (commit f07847c): MACD field wiring in momentum-monitor — `compute_macd()` added to `technical_core.py`; `screen.py` CSV columns + bridge.py + Dashboard row render pipeline.

---

## [1.37.0] — 2026-04-23
### Changed
- **SKILL.md slim** (3 files): `market-news-analyst` 727 → 253 lines, `us-stock-analysis` 297 → 137, `technical-analyst` 241 → 137. Pedagogy / tone / example queries moved to new per-skill `README.md` (3 new files).
- **`technical_core.py` extracted** as shared module between `momentum-monitor` and `technical-analyst` (Option C refactor — no duplication of MA / RSI / volume / stage / crosses primitives).
- **New `us-stock-analysis/scripts/analyze.py`** (fundamentals), **`market-news-analyst/scripts/fetch.py`** (news + analyst actions via finvizfinance), **`technical-analyst/scripts/analyze.py`** (adds MACD + swing-pivot S/R on top of shared core) — addressed "missing script" bug that caused V4.8 Phase 2 subagents to fall back to 30-min WebSearch loops.
### Fixed
- **FMP 429 short-circuit** (3 skills): `theme-detector/etf_scanner.py` + `market-top-detector/fmp_client.py` + `earnings-valuation-forecaster/forecast.py` — first 429 sets flag, subsequent calls skip HTTP. Removes 60-second retry sleep and infinite recursion.
- `theme-detector` daemon-thread timeout for `batch_stock_metrics` (replaces ThreadPoolExecutor which waited on exit).

## [1.36.1] — 2026-04-22 (commit f9caed0)
### Fixed
- **`bug.md` four tickets cleared**: scan banner lost on cross-page nav (sector + news resume covers running/done/error states within 5-min window); `bridge.py` `data.json` writes now atomic (`os.replace`); `scan_confirm` dialog notes preflight phase timing; `AnalyzeQueue` closes BUG-004.
### Added
- `supply-chain-event-analyst` skill.

## [1.36.0] — 2026-04-22
### Added
- **Momentum watchlist feature** — `universes/watchlist.txt` for non-SP500 tickers (APLD / ALAB / RKLB seed), merged automatically when `--universe sp500`; CSV `in_sp500` flag.
- Three REST endpoints on `dashboard_server.py`: `GET/POST/DELETE /api/momentum-watchlist`; atomic file write + `_TICKER_RE` regex validation.
- `momentum.html` ⭐ button + modal with chip list (add/remove with ×) + filter panel "Watchlist 範圍" three-way chip; purple accent row tint for non-SP500.

## [1.35.0] — 2026-04-22
### Fixed
- **Intraday volume pollution** — `momentum.py:_volume_block` used yfinance's partial-day bar directly, triggering `volume_dry_up` on ~500 tickers when scanning during session hours. New `_intraday_state(hist)` three-way classifier (`complete` / `partial` / `too_early`); partial scales `today_v × 390/elapsed_min` to project full-day equivalent; too_early suppresses volume signals entirely.
- `volume_trend` v5/v10 comparison now uses prior-days-only to avoid intraday drift.

## [1.34.x] — 2026-04-21
### Added
- **Protocol-run session exclusion** rule in CLAUDE.md — sector scan / news / invest protocols do NOT trigger VERSION bump or todolist update (root-caused a stuck subagent rc=1 loop).
- CLAUDE.md slim (165 → 81 lines); README expanded (148 → 244 lines) absorbing market classification / protocol evolution / rule rationale.
- Sector banner UI: title/status/latest-log wrapped in `flex-1 min-w-0 overflow-hidden` container; long 401 JSON no longer deforms card.

## [1.32.0] — 2026-04-21
### Changed
- **Dashboard M1+M2+M3 overhaul**: Layer 1 hero = Today's Verdict (stance + headline + 3-col takeaways/sector_actions/watch_next); Layer 2 binary-risk banner + warning_flags strip; Layer 3 three-column teaser (HOT sectors / reviewed news / momentum top 3); cross-module ⭐ intersection signals (`recent_analysis.decision ∈ {BUY,EXECUTE} ∩ momentum top 30`).

## [1.30.0] — 2026-04-19 (commit 02162a9)
### Added
- **Global analyze queue** (`AnalyzeQueue` module) — per-ticker 🔍 button enqueues ticker; background worker thread runs `run_protocol("invest")` serially; dedupe active/pending; decisions page widget shows NOW ANALYZING / QUEUE / RECENT history.
- Market-hours-aware cache freshness (`_market_minutes_between` helper; weekend / post-close cache stays FRESH).
- Deep-links from sector card → momentum page with sector filter pre-applied.

## [1.28.0] — 2026-04-20
### Added
- Today's Verdict structured object on sector page (stance + confidence + key_takeaways + sector_actions + watch_next) — consumed later by index dashboard.

## [1.27.0] — 2026-04-19
### Changed
- Three-page scan log UI unified — inline glass-card with expandable live-log, replaces fixed banner / compact pill. Live stderr tail via new `log_tail` field in status endpoint.

## [1.23.0] — 2026-04-19 (commit 38ce105)
### Added
- Momentum screener Dashboard first ship — covers v1.13 → v1.23 (new `momentum-monitor` skill, full momentum page, filter panel with 6 presets, score battery UI, stage/rsi/volume popups, GICS sector dimension, intraday volume projection).

## [1.22.x] — 2026-04-18
### Added
- RSI column clickable popup (blood bar + zone legend + personalised advice).
- Stage classification popup (MA stack visualization + rule checklist + transition conditions).

## [1.21.0] — 2026-04-18
### Fixed
- **Volume ratio intraday projection** — clickable popup shows "projected full-day volume" when ET 9:30-16:00; `_avg_prev(n)` excludes today to avoid self-dilution.

## [1.20.0] — 2026-04-18
### Added
- **GICS sector dimension** in momentum selector — `sp500_sectors.json` from Wikipedia S&P 500 list (503 tickers × 11 sectors); sector subscript on ticker cell + filter dropdown.

## [1.18.x] — 2026-04-18
### Fixed
- JSON.parse NaN bug — `momentum.py` / `bridge.py` sanitize NaN → None; `json.dump(allow_nan=False)`.
- Scan real-time progress via `Popen` + background reader thread parsing `screen.py` stderr.

## [1.17.0] — 2026-04-18
### Changed
- Momentum to **client-side real-time filtering** (previously server-side `min_score=60`) — backend returns all 503 rows, client filters live. Enables instant slider changes without rescan.

## [1.15.0–1.16.0] — 2026-04-17
### Added
- RSI-14 (Wilder smoothing) in `momentum.py`.
- 10-cell battery UI for score display.
- `ThreadingHTTPServer` to prevent scan blocking other requests.

## [1.13.0] — 2026-04-17 (commit 38ce105 begins)
### Added
- `momentum-monitor` skill (per-ticker volume / MA / short interest / composite score 0-100) + CLI + cache.

---

## [1.12.0] — 2026-04-16
### Added
- `feat: V4.8 protocol` (commit b955a5c) — **Parallel Blind Analyst Subagents** (4 Phase 2 analysts now run in single-message parallel Agent tool calls with `subagent_isolated:true` sentinel).
- Per-card refresh on decisions page.
- `market-sentiment-analyzer` skill file-based cache (15-min TTL).

## [1.11.0] — 2026-04-16
### Added
- Pre-market preflight cache health modal (`/api/preflight`, `/api/preflight/run-free`) — one-click refresh for stale breadth/FTD/market-top caches.
- Reverse-call from Dashboard to Claude CLI (`/api/run-protocol` covering invest/flash/digest/review).

## [1.10.0] — 2026-04-16 (commit 0f3bcd2)
### Added
- **News review workflow** — REVIEW mode + Dashboard `reviewed` / `pending` filter pills + submit-for-review button.
- FLASH/DIGEST buttons on Dashboard news page trigger reverse-call.

## [1.9.0] — 2026-04-16 (commit 62fdabe)
### Added
- News V2 protocol — RSS two-stage funnel + 4-agent roundtable (Bull/Bear/Sector/Macro).
- 4 missing skills added; protocol MUST-run rules; calibration doc.

## [1.5.0–1.8.0] — 2026-04-13 (commits d34f2b1, b03f806, 90e6034, 54bc9a0)
### Added
- `market-breadth-analyzer` skill (C-BREADTH) with TraderMonty CSV data source — 6-component 0-100 composite.
- `ftd-detector` skill (C-FTD) via yfinance adapter — dual-index tracking (S&P 500 + NASDAQ), rally-attempt state machine.
- `market-top-detector` skill (C-TOP) — O'Neil Distribution Days + Minervini leadership deterioration + Monty defensive rotation.
- Hover tooltip explanations on `breadth.html` indicator cells.

## [1.3.0–1.4.0] — 2026-04-12 (commits 304da30, 062bdee, dd61383)
### Added
- 4 risk/sentiment skills integrated into protocols (V4.5 / V1.1):
  `short-contrarian-analyst` (Burry) / `market-sentiment-analyzer` / `portfolio-risk-manager` (vol-adjusted caps) / `tail-risk-analyzer`.
- Historical, news, sector pages added to Dashboard.
### Fixed
- Safari compatibility; UI icon issues; dash logic bugs.

## [1.2.0] — 2026-04-11 (commit 35d23f6)
### Changed
- Project structure reorganization; protocol upgrades (Sector V1.2 multi-file + Investment V4.4).

## [1.1.0] — 2026-04-11
### Added
- `investment/` / `sector/` / `news/` protocol directories with per-module README.

## [1.0.0] — 2026-04-09 (commit 98cce74)
### Added
- **Initial commit**: AI投資委員會 multi-protocol investment system.
  - `investment_protocol_v4_3`: individual stock analysis with 8-agent debate.
  - `sector_protocol_v1`: pre-market sector intelligence with bull/bear debate.
  - `news_protocol_v1`: real-time news analysis with cache patching.
  - Three-layer Phase 0 cache: sector_intel → phase0 → web search.
  - Skills: `us-stock-analysis`, `market-news-analyst`, `technical-analyst`.

---

## Evolution highlights

For quick orientation of future Claude sessions:

- **Weeks 1-2** (v1.0 → v1.12): foundational skills + protocols; sector/news/invest three-way split; Dashboard first pages.
- **Week 3** (v1.13 → v1.30): momentum-monitor ecosystem (screener + journal + live Dashboard page with every interaction clickable); analyze queue; watchlist.
- **Week 4** (v1.31 → v1.38): UX polish phase — banner layout, MACD/RSI/Stage popups, preset strategy tooltips, custom tooltip system; bug.md triage.
- **Week 5** (v1.39 → v1.40): macro data enrichment — FRED API integration for authoritative rates/inflation/employment/credit feed into Phase 0 multiplier calibration.

Protocol evolution: investment V4.3 → V4.8 (parallel blind analysts); sector V1 → V1.3 (multi-file with Phase 0-5 split + validator gate); news V1 → V2.1 (RSS two-stage + 4-agent roundtable + per-agent batch subagent).
