# Session Notes 歸檔 v3.25.7 → v3.30.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v3.30.0) — 短期雷達加「個股動向」panel

接 V3.29.0(產業級趨勢榜)。痛點:產業榜看不出**產業內個股強弱分化**(光通 case —
強勢產業裡某股連跌多天)。

**關鍵**:個股 Weinstein stage / RS / Stage4 warning 系統每日算好且**已在
`data.json.momentum_screen.rows[]`**(daily Step 9.7 momentum-monitor ~529 檔),radar
沒用。→ **純前端、零 backend**。

做的:radar 新 `#radar-stock-movers` 區塊 + `renderStockMovers()`:
- 對稱 📈領漲個股(Stage2+RS≥70/新高) ↔ 📉走弱個股(Stage4/Stage3/WEAK·BEARISH),
  各 top 12,走弱按 composite score 由低到高。
- **🔥強勢產業中走弱 strip**:走弱 ∩ `sector_rs_rank≤3`(用 row 內建欄位,免 sector
  名對映)。實測抓到 BSX(RS-46/-14.9% 5d, Health Care #2)、ISRG、MDT 等。
- stage chip(S1-S4) + warning dots(🔻✗💀🪫) + freshness badge + 2 tooltip。

陷阱修正:走弱判定**不**用 `rs_3m_pct<0`(強 SPY 盤 412/529 會被誤標),改「Stage3/4
OR WEAK/BEARISH」→ 193 檔,UI top12 worst-first。校準:今日光通(COHR/CIEN/MRVL/LITE)
其實是 Stage2 強勢 parabolic,非走弱 — 引擎對,只是今天讀數異於印象。

驗證:node --check 過;data.json momentum_screen success/529/snap 2026-05-29;
consistency 印 leaders95/laggards193/weak-in-strong67 對得上。版本 3.30.0 三處同步。

## 🟢 Session Note (v3.29.0) — 短期雷達改用真實近期趨勢

痛點:radar 只反映 forward 預測 → ① narrative pulse 數據死板無參考價值
② 短期看多率結構性永遠 >50、看不到看空 ③ 看不出真實近期趨勢
(SaaS/CPU/AI server 巔峰、光通走弱)。

**關鍵**:使用者要的真實 trailing 資料系統**早已算好、卻被 radar 棄置** —
`theme-detector` cache 的 `industry_rankings.top/bottom` (140 finviz 產業真實
`perf_1w/1m/3m`) + `sector_uptrend`。修法 = surface 既有真實資料 + 顯示指標換真實。

四件事:
1. **`predict.py`** 輸出加 top-level `trailing_return_5d_pct` / `_20d_pct`
   (純價格 trailing,可負)。
2. **`screen.py`** `compute_theme_short_term` 加 `trailing` 區塊
   (`trailing_breadth_5d_pct` = 成分股近 5d **實際**上漲比例 + median 5d/20d +
   median momentum)。保留 bullish_breadth 不當主顯示。預設排序改 trailing。
3. **`bridge.py`** `load_industry_trend()` → `data['industry_trend']`
   (leaders/laggards/sector_uptrend/summary + freshness)。
4. **radar UI**:headline 新 `#radar-industry-board` (領漲↔領跌 + 1週/1月/3月
   toggle + 11-sector strip);theme card 改「真實上漲率」+「中位漲幅」+ 看多/看空
   badge;**Narrative Pulse 隱藏** (`NPD_RADAR_ENABLED=false`,generator 保留到
   5/31 觀察期)。

驗證:predict NVDA real 5d -1.77% / IONQ +16%;screen 重跑後 Oil&Gas REAL_up
10% med -5.37% (forward 是 40%)、多主題 <50、負中位 — 對稱看空生效;
smoking gun = 舊版 direction=bearish 主題仍顯示 bullish_breadth 83/66%。
JS node --check 過;bridge 餵 industry_trend OK (leaders top1=Computer Hardware
+17.98% 1w = AI server 巔峰);data.json 確認帶 industry_trend + theme trailing。
**注意** theme-detector cache 非每日強制重跑 (≤7天舊),趨勢榜帶 freshness badge。

## 🟢 Session Note (v3.28.0) — Market Mood 市場氛圍 page + retail social expansion

新增 Dashboard 專頁「市場氛圍」(`mood.html`/`page-mood.js`, nav group market)。
動機:radar Sector Pulse 看似情緒、實為純技術 — 散戶社群太稀 (整天 ~41 post)，
composite 塌縮成 5d 價格預測。

三件事:
1. **`mood.py`** → `Dashboard/market_mood.json`:VIX + ^VIX3M term structure +
   ^SKEW + CBOE/CNN put-call + Fear&Greed 7 子指標 → signed -100..+100 氛圍分。
   CBOE put/call CDN 目前 **403 封鎖**,fallback 到 CNN `put_call_options` 子指標
   proxy (有效)。缺源時權重 re-normalize。import sentiment.py 不改它。
2. **社群擴充** `social_sources.py`:新增 StockTwits source (trending → 各檔
   streams,native Bull/Bear tag 進 meta;env-gate + 429 graceful) + 加寬
   subreddit + 提高上限。實測 post 41→110、tickers[] 0→6+。契約不變,
   trending_tickers.py/aggregate.py 零改。
3. **新頁 UI**:hero gauge (Chart.js 半圓 + deterministic needle) + 3 訊號 tile
   (期權/VIX-SKEW/F&G+7子指標 bar) + 散戶熱股 strip + sector grid (情緒在前、
   技術 lane 灰底降權標「技術面參考」)。bridge 烤進 data.json (market_mood top-level
   + tactical.trending slim 投影,+7.7KB),無新 server route。

期權誠實講:無 live IV chain (FMP 付費也沒),用市場級 put/call + VIX + SKEW proxy。
驗證:mood.py CBOE 403 仍 score=41 不報錯;server serve mood.html/page-mood.js 200;
data.json 含 market_mood + trending;JS node --check 全過。

## 🟢 Session Note (v3.27.0) — Pre-Market Pipeline Redesign + Morning Brief

Redesigned the pre-market flow (`daily_update.sh`) to exploit the FMP **paid**
250/min plan, which the old free-tier-shaped pipeline (serialized FMP lane,
300ms per-client throttles, 150-call budgets, 6 workers) left unused.

Core: new `scripts/_shared/fmp_pool.py` — a single **cross-process** rate
limiter. It models FMP's "calls per rolling minute" via a JSON timestamp window
in `~/.cache_bridge/fmp_pool_window.json` guarded by an `fcntl.flock` lockfile,
targeting 220/min. The lock is held only for the read-trim-write (microseconds),
released before any backoff sleep, so the parallel subprocesses + threaded
workers `daily_update.sh` spawns share one budget without serializing. Verified
hermetically: 8 procs × 3 threads × 6 calls under cap 30/min held to exactly 30
per 60s window over ~240s.

All 6+ previously-uncoordinated FMP clients now delegate pacing to the pool
(signatures + caches unchanged). FMP lane de-serialized into two parallel chains
(thematic ∥ momentum); workers 6→20/16; supply_chain call-count cap 150→2000.
`dashboard_server.py` heatmap fan-out calls `acquire_slot()` so the always-on
server + a daily run never collectively exceed 250/min (optional
`FMP_DASHBOARD_RPM` soft sub-cap).

New `scripts/premarket/morning_brief.py` (step 9.8, non-fatal) → deterministic
`reports/PREMARKET_<DATE>.md`, 10 sections, cache-reuse + ~5-25 pooled fresh
calls, graceful when `FMP_API_KEY` unset, 36h staleness guard. Verified render
with and without the key.

## 🟢 Session Note (v3.26.1) — Break News Debate Scroll Reset

User reported that clicking a different Break News debate left the right-side
chat room at the previous item's scroll position instead of starting from the
top.

Fix: `Dashboard/page-break-news.js` now passes `resetScroll` only when
`selectedId` actually changes, and `renderDetail()` sets
`#bn-thread-panel.scrollTop = 0` after replacing the panel HTML. The 5s
same-item polling path does not pass `resetScroll`, so an active debate can
refresh without yanking the reader back to the top.

## 🟢 Session Note (v3.26.0) — Reports Center

Built a Dashboard reading layer over the existing 251 MD files in `reports/`.
Triggered by user wanting to visually browse the new IC memo outputs
(V3.25.0) plus 10 other report families in one place instead of using finder.

Implementation:
- `dashboard_server.py` adds two read-only routes — `/api/reports` (classified
  list, 60s cache, mtime-invalidated) and `/api/reports/view/<filename>` (raw
  markdown, ASCII whitelist + traversal guard). Cloned the existing
  `/decision_review/` static-serve pattern for consistency.
- New page `Dashboard/reports.html` + `Dashboard/page-reports.js` — master
  list (search + 12 type tabs with counts) on left, marked.js-rendered
  viewer with TOC on right.
- IC-memo-specific post-processing: verdict badge (BUY/HOLD/SELL/CANCEL
  colour), 🔒 `decision_lock` chip with 11-field SHA256 tooltip, degraded
  banner from footer flag, summary card extracting Date/Live Spot/Analysis
  Price/Market Cap/Sector from the YAML-ish header.
- Filename classifier handles 12 type families. `deep_dive` rule
  (`^YYYYMMDD_TICKER.md$` or `^YYYY-MM-DD_TICKER.md$`) catches 126 of the
  legacy V5.0 single-stock reports; only 9 misc files fall to `other`.

Strict discipline: pure viewer — no edit/delete/regeneration. Decision-lock
hash *verification* stays with `validate_ic_memo.py`; the page only displays
the lock. No protocol or skill behaviour touched.

**Server restart required** to load the new `/api/reports` routes (the
running `dashboard_server.py` process pre-dates this commit).

## 🟢 Session Note (v3.25.10) — Daily Update Hybrid Parallelism

User asked to implement the earlier dependency analysis for `daily_update.sh`
while respecting FMP's 250 calls/minute limit.

Implemented hybrid scheduling:
- Phase 1 runs breadth / FTD / market-top / FRED in parallel, then joins
  before `bridge.py`.
- Post-bridge FMP lane remains serialized: ETF holdings check → thematic
  screener → momentum fundamentals prefetch → full momentum screen.
- Non-FMP lane runs structural watchlist / Nexus / trending discovery in
  parallel, then retail sector pulse.
- Narrative Pulse runs after both lanes complete so thematic recommendations
  and structural watchlist are available.
- A final lightweight `bridge.py` refresh runs after Narrative Pulse so
  `Dashboard/data.json` includes same-run narrative / retail / momentum screen
  outputs instead of waiting for the next daily run.

Live timing correction: the first run showed Step 6 thematic can take ~948s
on a cold path, while `9.7` momentum screen took ~106s. User clarified both
are intended daily signals, so they remain enabled by default.

Optimization added:
- `skills/thematic-screener/scripts/screen.py` now supports
  `--predict-workers` for bounded parallel `predict.py` subprocess fanout.
  `daily_update.sh` uses `THEMATIC_PREDICT_WORKERS=6` by default.
- FMP-heavy enrichment remains serialized to avoid bursting the 250/min FMP
  limit.
- Temporary escape hatches exist for incident response:
  `DAILY_RUN_THEMATIC=0`, `DAILY_RUN_MOMENTUM_SCREEN=0`,
  `DAILY_FORCE_THEMATIC=1`.

Added temp-log background helpers so parallel jobs do not interleave stdout,
with elapsed seconds printed for every background job after join.
When enabled, `9.7` uses full universe with `MOMENTUM_SCREEN_WORKERS=6` by
default; caller can override the env var after observing 429/rate-limit logs.

Validation: `bash -n daily_update.sh` passes. Full live run intentionally not
executed during implementation because it would hit external APIs.

## 🟢 Session Note (v3.25.9) — Momentum 3D Volume Window

User asked for a quick-scan read of "**最近 3 天是量縮或放量**" without
clicking into the per-ticker volume modal. The existing 量比 column
only shows today vs 20D, which flips around on intraday noise. The 5D
average inside `_compute_dry_up_spike` was already there but too
smoothed for "recent" reading. 3D sits in the middle.

Compute (`momentum.py:_compute_dry_up_spike`): added `avg_3d_vs_20d`
(last-3-day avg / 20D avg, both excluding today, `iloc[-4:-1]`) +
`vol_3d_state` ∈ `{expanding, neutral, drying_up}` with thresholds
≥1.3 / [0.75,1.3] / ≤0.75 mirroring the existing dry-up cutoff.
Schema bumped `v2.2 → v2.3`; `_load_cache` gate updated to invalidate
old caches.

UI placement (per user pick): subscript under the existing 量比 cell.
Three stacked lines — today × ratio (existing, colored by today's
tier), then `3D X.XX×` dim subscript, then small colored state pill
(放量 / 中性 / 量縮). The cell stays clickable; the modal also gained a
new "3D 均量 / 20D" row. Single `_vol3dSubHTML(r)` helper renders the
two new lines so the rowHTML stays compact.

Smoke (NVDA, AMD, WMT, ULTA on real OHLCV):
- NVDA  today=1.12 3d=1.14 state=neutral
- WMT   today=1.50 3d=1.94 state=expanding (放量)
- AMD   today=0.88 3d=0.77 state=neutral   (just above 0.75 cutoff)
- ULTA  today=0.96 3d=0.85 state=neutral

Tooltip wording (`col_volume_tip`) updated zh + en so users discover
the subscript on header hover. No new tooltip component; reused the
existing styled card.

Out of scope: filter / preset wiring on `vol_3d_state`. If user wants
it later as a screening axis, the field is already in the CSV and
JSON path — only need `--min-vol-3d` flag + a defaultFilter() entry.

## 🟢 Session Note (v3.25.8) — IC Memo F-8 §1 Dedup

Cosmetic followup to V3.25.7 review. F-8 §1 entry-range check sat inside
the per-key for-loop, so when both `entry_aggressive` and
`entry_conservative` were non-null and §1 row was broken, validator emitted
two identical findings. Moved the §1 check out of the loop with an
`any_entry_set` guard preserving the original "skip when both keys null"
semantics. Added `test_md_entry_range_sec1_finding_not_duplicated` to lock
the behavior; 60 tests pass. No LOCK_FIELDS / decision_lock contract
touched — committee `decision_lock_hash` invariance preserved across
V3.25.4 → V3.25.7 → V3.25.8.

## 🟢 Session Note (v3.25.7) — IC Memo Validator Narrowing

Claude review of the V3.25.4 IC Memo patch found two real low-risk issues:
D-6 scanned the whole memo for `{"tier": ...}` and D-7 scanned the whole memo
for `Consensus View` / `Differentiated View`. Both were useful regression
checks but too broad — an appendix example or quoted phrase could trip them.

Fix: `validate_ic_memo.py` now extracts section blocks and limits D-6 to §7
and D-7 to §10 markdown headers. D-6 also catches Python-dict style
`{'tier': ...}` inside §7. Added a small stderr log when `build_fact_pack.py`
falls back to shared FMP peers because no IC Memo local roster exists.

Verification: `python3 -m pytest skills/ic-memo-writer/tests -q` → 59 passed.
MU memo validator remains rc=2 with only `sec_4_peer_descriptor_stub`.
