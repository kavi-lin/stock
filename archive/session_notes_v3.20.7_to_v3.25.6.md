# Session Notes 歸檔 v3.20.7 → v3.25.6（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v3.25.6) — Column tooltips switched to styled card UI

User screenshot showed the V3.25.5 column tooltips rendering as the OS
native black box (Image #2), wanted them as the white-card style that
the sector heatmap uses for GOOGL row hover (Image #3).

Fix: instead of native `title="..."` attribute, wire `data-col-tip="<key>"`
on each annotated `<th>` and dispatch through the existing
`#mom-pill-tooltip` element + `showTip()` handler that already powers
the signal / warning / preset cards on this page. New CSS class
`.mpt-col` (emerald-accent title, 440px max-width) + `.mpt-body`
(`white-space: pre-line` so the `\n` in i18n strings renders cleanly).
Removed the now-redundant `setTitle` block — native title + styled card
were both firing on slow hovers and competed visually.

No new tooltip system, no popup framework, no hydration. The momentum
page now has exactly one tooltip component handling four content types
(signal / warning / preset / column). Consistent UX across hover
surfaces.

## 🟢 Session Note (v3.25.5) — Tooltips + Fund-tab i18n + 100% PE coverage

User flagged three follow-ups on the V3.25.x momentum work:

1. `MU` still showed empty 本益比 even after V3.25.2's backfill.
2. Fund-tab column headers (P/S / GM% / Rev YoY / 5D%) had no zh
   translation; left as raw English in the HTML.
3. Score vs Rank columns needed an in-UI tooltip explaining the
   difference, same UX pattern as the sector page's tooltips.

### MU root cause + 100% backfill

The `scripts/backfill_heatmap_pe.py` parallel run (15 workers) was
consistently dropping ~250/517 tickers in the SAME alphabetic cluster
(EQR, EQT, ERIE, ES, ESS, ETN, ETR…) — looked like an FMP rate-limit /
worker-batch failure that the script swallowed silently because every
network exception in `fetch_valuation` just falls through to the
all-None default.

Workaround: keep the parallel run for speed, then sequential second-pass
through the still-missing list with `time.sleep(0.08)` between calls
and `timeout=20`. Sequential pass filled all 236 remaining; MU now
reports `pe=41.79` end-to-end (heatmap.json → bridge → data.json).

Final coverage: heatmap.json `517/517`, data.json momentum rows
`515/528` (the residual ~13 are tickers genuinely missing TTM PE on
FMP, mostly negative-earnings names — not a bug).

There was also a `__pycache__` ghost that made an isolated `python3 -c`
import of `fetch_valuation` return all-None until the cache was wiped.
Likely the cached `.pyc` came from a half-saved earlier version of the
script. Cleared with `find scripts -name __pycache__ -exec rm -rf {} +`
before re-running. Not a long-term concern because the CLI script
recompiles cleanly each invocation; just a footgun when debugging via
`-c` snippets.

### Tooltips + Fund-tab labels

Pattern intentionally minimal: inline `title="..."` attribute set in
`applyLanguage()` via a small `setTitle` helper, mirroring the sector
page's heatmap-cell tooltips (`page-sector.js:1295-1297`). No new popup
component, no hover JS — browsers render multi-line tooltips natively.
Same UX as the macd column's existing tooltip already had.

Added 9 tooltip keys + 4 label keys (zh+en) to `i18n.js`. Score vs Rank
tooltip explicitly enumerates the bonus/penalty table from
`screen.py:_rank_score()` so users no longer have to ask "why is rank
80 when score is 65?".

### Operational note

If PE goes empty again later, run:

```bash
find scripts -name __pycache__ -exec rm -rf {} + 2>/dev/null
python3 scripts/backfill_heatmap_pe.py
# then sequential pass on still-missing if parallel left holes:
python3 -c "
import os, sys, json, time
sys.path.insert(0, 'scripts')
from backfill_heatmap_pe import fetch_valuation, HEATMAP, _safe_round
api = os.environ['FMP_API_KEY']
with open(HEATMAP) as f: d = json.load(f)
for row in d['tickers']:
    if row.get('pe') is not None: continue
    v = fetch_valuation(row['ticker'], api, timeout=20)
    if v.get('pe_ttm') is not None: row['pe'] = v['pe_ttm']
    if v.get('ev_ebitda') is not None: row['ev_ebitda'] = v['ev_ebitda']
    if v.get('fwd_eps') and row.get('price'):
        try: row['forward_pe'] = _safe_round(float(row['price'])/v['fwd_eps'], 2)
        except: pass
    time.sleep(0.08)
with open(HEATMAP+'.tmp','w') as f: json.dump(d, f, ensure_ascii=False)
os.replace(HEATMAP+'.tmp', HEATMAP)"
python3 bridge.py
```

V325.X-PE-WARMUP-RETRY (already in TODO) should fold this two-pass
shape into the dashboard_server daemon so the manual rescue isn't
needed; out of scope for this hot-fix.

## 🟢 Session Note (v3.25.4) — IC Memo MU Data-Gap Patch

MU smoke on the new IC Memo Writer exposed readable-output bugs that the
V1.0 hash validator did not catch: live spot and protocol analysis price were
mixed in the header, entry ranges stored as lists rendered as `—`, populated
earnings-cache fields were missed due to key-name mismatches, and §7 printed
a truncated raw structural-shift JSON fragment.

Patch shape:

- Dual price basis in fact_pack + memo: `Live Spot` and `Analysis Price` are
  both shown, and FV downside is split vs analysis and vs live.
- `fmt_price_range()` renders list/dict/scalar entry zones in §1 and §11.
- §5-§7 flatten TTM aliases, derive surprise %, alias balance-sheet fields,
  and support snake_case analyst estimates.
- §3 splits MU's FY2025 DRAM/NAND presentation from legacy CNBU/MBU/EBU/SBU.
- §4 uses a skill-local `peer_rosters.py` override for MU/NVDA/AMD/INTC/TSM
  instead of changing `_shared.company_context.get_peers()`.
- Validator gained MD-level checks for price-basis labels, lost entry ranges,
  raw structural JSON, and dead §10 consensus/differentiated headers.

Verification: `python3 -m pytest skills/ic-memo-writer/tests -q` → 59 passed.
Rebuilt MU/NVDA/CRWD fact packs and memos. MU and NVDA validate rc=2 only
because `sec_4_peer_descriptor_stub` remains Phase A.5 work; CRWD keeps the
expected missing-earnings-cache + low-anchor degraded findings. MU report was
regenerated at `reports/20260527_MU_ic_memo.md`.

## 🟢 Session Note (v3.25.3) — Fund tab color parity with Tech tab

User screenshot showed the Fund tab with an emerald tint on every
`.col-fund` cell (P/E header + body). After V3.25.2 pushed score/signals
into `col-tech`, the Fund tab's visible columns alternated between
untinted (`col-anchor`: #/ticker/price) and tinted (`col-fund`: P/E,
short, P/S, GM%, Rev YoY, 5D%) which read as broken stripes rather
than a unified group.

Fix: removed the `.col-fund` tint rules entirely. Both tabs now share
the same neutral cell background; emerald identity lives only in the
active tab pill in the rail above. Single-line CSS deletion. No JS,
no markup, no data changes.

## 🟢 Session Note (v3.25.2) — 2-Tab Refinements + P/E Backfill

User opened the new 2-tab view and reported two things: (a) `本益比` (P/E)
column was empty for every row, (b) score battery and signal pills should
only render on the Tech tab — Fund tab should read as raw fundamentals.

Root cause of P/E empty: `dashboard_server._heatmap_refresh_pe_universe()`
runs exactly once on server startup with a 24h TTL. The current
`Dashboard/heatmap.json` had 0/517 P/E entries — the warm-up either errored
mid-run or the server hadn't restarted in the meantime. Since
`bridge.py:ingest_momentum_screen` joins P/E from heatmap.json, every
momentum row got `pe=null`.

Fix: new `scripts/backfill_heatmap_pe.py` mirrors the daemon's three-call
fetch (ratios-ttm + key-metrics-ttm + analyst-estimates) out of process,
parallel via ThreadPoolExecutor, writes back atomically. Backfilled
269/517 entries (the remaining ~half are negative-earnings tickers where
FMP correctly returns no TTM PE). Re-ran `bridge.py` → data.json now
shows real P/E values on the Fund tab.

UI refinement: moved `score` + `signals` from `col-anchor` to `col-tech`.
New anchor set: `# · ticker · price` only. The 2-tab counts shifted to
Tech 12 / Fund 9. Fund badge updated. Class-based hide model meant zero
CSS work — just swap class on 2 `<th>` and 2 `<td>` cells.

Operational note: if P/E goes empty again later, run
`python3 scripts/backfill_heatmap_pe.py && python3 bridge.py`. Long-term
the dashboard_server PE warm-up should retry on failure instead of
silently leaving the cache empty — that's a deeper fix worth scheduling
separately, not for this patch.

## 🟢 Session Note (v3.25.1) — Momentum Table 2-Tab Column View

User pointed out the "More columns" toggle no longer fits after V3.22 added
the Fundamentals group. Default view hid the new P/S · GM% · Rev YoY · 5D%
work; expanded view ballooned to 18 cols. The boolean lens was the wrong
mental model — Tech and Fundamentals are two different ways of reading the
same row, not "less / more" of the same thing.

Replacement design (planned in `/Users/kavi/.claude/plans/more-column-colume-zany-cascade.md`):

- Two named tabs styled like the existing preset rail: 📊 技術面 (12 cols)
  and 💰 基本面 (11 cols). Each tab carries an inline count badge.
- 5 anchor columns (`# · ticker · price · score · signals`) render in both;
  the other 13 split by domain (7 tech, 6 fund). Hide control is purely
  class-based — `[data-view="tech"] .col-fund { display: none }` and inverse.
  No `nth-child` indexing, no fragility on column-reorder.
- Lag disclaimer (`#mom-fnd-note`) only shows when `#table-wrap[data-view=
  "fund"]` — it's a fundamentals-only message, so the Tech tab stays clean.
- localStorage key changed `momentum_cols_extra` → `momentum_table_view ∈
  {tech, fund}`. Legacy key intentionally ignored; default is `tech` to
  preserve the existing mental model for users who haven't touched anything.
- `.col-fund` doubles as visibility class and visual tint. The previous
  `.col-fnd` tint only covered the 4 V3.22 cells; reusing `.col-fund` now
  also tints P/E + short, which unifies the Fund lens visually.

No CSV / `bridge.py` / data shape changes — every field still ships in the
row payload; this is purely client-side rendering. Filters and presets work
identically across tabs (they operate on the underlying row data, not the
visible columns).

## 🟢 Session Note (v3.25.0) — IC Memo Writer (deterministic readable memo)

User shared a long Chinese Planet Labs (PL) analyst memo and asked whether
the project could surface that kind of "readable research report" view —
not Dashboard panels, but a narrative MD covering business model, revenue
segments, peers, scenarios, and DCF triangulation. Codex round-tripped on
the design and pushed back on five things that became the final spec:

1. `fact_pack.json` middle layer between cache and Memo MD (so template
   changes can re-render without re-fetching).
2. Per-section provenance tags (`<!-- src: ... -->` + Provenance Roster
   table) so every fact is traceable to its source.
3. **Decision-lock SHA256 over 11 fields** (not just `lane_scores`) —
   `final_decision`, `final_action`, `position_size_pct`, `analysis_price`,
   `fair_value_summary`, `scenario_odds`, `watch_conditions`, `key_risks`,
   `red_team_counter_thesis`, `red_team_kill_conditions`, `lane_scores`.
   Floats `round(x, 4)` before canonicalization to avoid IEEE drift.
4. LLM peer descriptor is isolated to the skill's own cache, not
   `_shared/cache` — that keeps the deterministic FMP-derived shared cache
   pristine. V1.0 ships the descriptor as a `status: stub_no_llm` empty
   shell; Phase A.5 will swap in a single Haiku 4.5 batch call.
5. `compose.py` is **deterministic-only** in V1.0 (zero LLM calls);
   `--llm-polish` flag is reserved but raises `NotImplementedError` so
   nobody accidentally re-introduces narrative drift.

Validator rc ladder: `0` pass / `1` fatal / `2` degraded-usable. Fatal
codes (F-1.1/1.2/1.3/2/3/4/5/6) cover hash self-inconsistency, history
mismatch, §11 verbatim mismatch, FV mismatch, missing §11 block, and
forbidden re-scoring phrases. Degraded codes (D-1..D-5) cover missing
earnings cache, low FV anchor count, missing provenance comments, and
missing Provenance Roster.

Smoke-tested on CRWD (no earnings cache → 6 degraded sections, rc=2 as
expected) and NVDA (full data path → only peer_descriptor stub degraded,
rc=2). 44 pytest cases pass, including all 11 single-field decision_lock
breach parametrized cases.

### Files touched

| File | Lines | Purpose |
|---|---|---|
| `skills/ic-memo-writer/SKILL.md` | new ~180 | skill spec + decision_lock + rc ladder |
| `skills/ic-memo-writer/template.md` | new ~150 | 12-section reference skeleton |
| `skills/ic-memo-writer/scripts/build_fact_pack.py` | new ~360 | aggregator + hash |
| `skills/ic-memo-writer/scripts/compose.py` | new ~430 | deterministic renderer |
| `skills/ic-memo-writer/scripts/validate_ic_memo.py` | new ~270 | rc=0/1/2 validator |
| `skills/ic-memo-writer/scripts/fetch_peer_descriptor.py` | new ~70 | V1.0 stub |
| `skills/ic-memo-writer/tests/test_validator.py` | new ~240 | 24 tests incl 11 breach sub-cases |
| `skills/ic-memo-writer/tests/test_fact_pack.py` | new ~115 | 11 tests |
| `skills/ic-memo-writer/tests/test_compose.py` | new ~135 | 9 tests |
| `skills/ic-memo-writer/tests/fixtures/*.json` | new ~660 | minimal NVDA history + earnings |
| `investment/investment_protocol_v5_0.md` | +20 | Phase 5 Step 7 IC Memo hook |
| `CLAUDE.md` | +5 | Protocol Triggers row + Ops Shortcuts |
| `CHANGELOG.md` | +60 | V3.25.0 entry |
| `VERSION`, `Dashboard/utils.js` | sync | 3.22.0 → 3.25.0 |

### Last Session Note

Phase A (IC Memo Writer V1.0.0) shipped. Composer is deterministic, no
network calls beyond profile/peers (24h-cached). Decision-lock SHA256 over
11 history fields means the memo cannot silently change committee output —
mutation of any single field flips validator to rc=1 fatal. Phase A.5
follow-up will swap `fetch_peer_descriptor.py` from stub to Haiku 4.5
one-shot batch call; Phase B will be a Dashboard `stock-detail.html` that
renders the memo + live FMP quote / 6-anchor bar chart. Neither is on the
critical path — Phase A alone delivers the requested "readable memo".

---

## 📦 Previous Session Note (v3.22.0) — Momentum Fundamentals Layer (P/S · GM% · Rev YoY TTM)

User asked to add P/S + "營收股價比值" to the momentum page. Round-tripped
through Gemini Codex review which flagged the two obvious failure modes of
naive valuation overlays on a momentum table:

1. A hard P/S cap on the breakout preset strips the strongest leaders
   (NVDA / LLY) precisely at their thrust moment.
2. A naked low-P/S filter is a value trap without a gross-margin floor +
   non-shrinking revenue guard (retail / commodity names look "cheap"
   because they earn nothing).

Final shape:

- New fundamentals derive block on `momentum.py` (schema `v2.2`) computes
  `ps_ttm`, `gm_ttm_pct`, `rev_yoy_ttm_pct`, `ttm_revenue_usd`, plus 1D/5D
  price return. All TTM (8 quarters of FMP `income-statement?period=quarter`)
  to dampen single-quarter noise.
- Shared cache at `skills/_shared/cache/quarterly_income/{TICKER}.json`
  with 7-day TTL — fundamentals only refresh once per earnings cycle.
- `daily_update.sh` Step 9.6 prefetches the screener universe (~532 tickers
  across SP500 + Nasdaq100 + SOX) so ad-hoc `screen.py` runs cost zero
  FMP calls on the fundamentals side.
- 7 new CSV columns appended (not inserted) so legacy `bridge.py` column
  parsers stay compatible; bridge already used `DictReader` so by-name
  lookup was free.
- Dashboard adds a tinted Fundamentals column group (P/S · GM% · Rev YoY ·
  5D%) hidden behind the "More columns" toggle. Two new Featured presets:
  `🚀 Sales Breakout` (no P/S cap; Stage 2 + RS≥80 + RevYoY≥15%) and
  `💎 Value Momentum` (P/S≤5 stacked with GM%≥15 + RevYoY>0 + exclude
  parabolic).

Smoke test on NVDA: P/S=20.36, GM=74.15%, Rev YoY=+70.7%, TTM rev=$253B,
lag=30d. Sales Breakout includes NVDA; Value Momentum correctly excludes.

Discipline kept: fundamentals are **information-only**, never feed into
`momentum_composite.score` or `rank_score`. Cross-industry P/S comparisons
aren't trustworthy enough to weight a momentum signal — they're guardrails
the user reads, not gradients the system optimizes.

Deferred to a follow-up PR (per user agreement to ship in two slices):
ATR-normalized Gap Up detector, `Catalyst Gap-Up` preset, sector-relative
P/S, Pocket Pivot. Ship V3.22 first, watch a couple of weeks of screen
output to calibrate Value Momentum's GM/P-S thresholds before piling on.

## 🟢 Session Note (v3.21.0) — Break News Hourly Cap + Stale-Backlog Guard

Diagnosis: previous 5-6hr session burned the Anthropic 5hr quota window.
Forensic counts: 106 break-news debates in ~6hr × MAX_ROUNDS=3 Claude voice =
~300+ `claude` CLI subprocess spawns, plus 3 large protocols (`分析 CRWD` +
`產業掃描` + `新聞分析`) running concurrently. `config/llm_usage.json` showed
claude in cooldown (34 calls, tripped early), gemini fell back to 404 calls
(over its 200 budget — only daily counters, no 5hr window awareness).

Fix shape: throttle the explore layer at the admission stage, not after-the-fact.

- `BREAK_NEWS_HOURLY_CAP=25` rolling 1hr admission cap, slot = 2.4 min/item;
  quiet periods accumulate slot tokens, bursts still bounded by hourly_left.
- `BREAK_NEWS_BACKFILL_MINUTES=30` freshness gate — auto-admission only for
  news published within the last 30 min. Older stuff still visible in raw
  stream, just not in the auto-debate queue.
- `BREAK_NEWS_PENDING_MAX_AGE_HOURS=2` stops `scan_and_debate` from
  re-processing stale `pending_debate` after a long idle. Stale queue surfaces
  in a new UI panel with per-item manual 🔥 Debate button.
- Feed sort key changed `last_activity_ts` → `fetched_at` so news ordering
  reflects arrival time (debating items no longer float to top).

Endpoints: `GET /api/break-news/stale-pending`, `POST /api/break-news/item/<id>/debate-now`.

Dry-run verified: hourly_used=8, hourly_left=17, slot_tokens=0 (slot未滿),
allowed_this_cycle=0 — correctly throttled. Model headroom side still has
room (model_debate_capacity=11), but hourly cap is now the binding constraint.

Followup-ish: still need a real 5hr-rolling-window counter in `model_router.py`
for protocol runs (this PR only governs break_news). Defer until next quota
incident.

## 🟢 Session Note (v3.20.7) — Momentum Volume Regime Alpha UI

- `journal.py` extended momentum journal evidence with `volume_trend`,
  `ratio_20d_bucket`, and `by_volume_regime` (`trend × stage × ratio bucket`).
  Existing historical journal rows are not rewritten; stats backfills old
  fields from matching cached `screen_*.csv` snapshots when available.
- Existing sample check: 23,986 entries, 12,342 filled 20d returns, 100% volume
  regime field coverage via cache. `expanding + Stage 2 + ratio_20d>=1.3`
  showed n=113, 20d win=73.5%, median=+9.56%. `volume_expansion` alone was
  weak, confirming regime-dependent volume interpretation.
- Momentum Dashboard Journal section now shows `Volume Regime Alpha` cells that
  pass exploratory gate `n>=5`, `20d win_rate>=55%`, `20d median>=+2%`.
  Composite score and row ranking intentionally unchanged.
