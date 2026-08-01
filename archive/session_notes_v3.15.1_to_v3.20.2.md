# Session Notes 歸檔 v3.15.1 → v3.20.2（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v3.20.2 → v3.20.3) — Truth Social Filter + Wire-News Polarity

User ran daily_update + refreshed UI after V3.20.2 ship; reported "目測還是
沒什麼變". Diagnosis showed retail polarity all 0 across sectors despite 3
qualified tickers because:

1. Lexicon偏 WSB slang (moon/puts/diamond hands/tendies),但 RSS feed 抓到
   的多是 wire-news 風格 (surge/plunge/dip/downside/buying opportunity)。
   49 live posts → 0 lexicon hits。
2. DJT 4 mentions 全來自 Trump Truth Social 簽名 "— President DJT",政治
   貼文不該被當 DJT 股票訊號。

User 提示 「川普的貼文有公信力,只是要濾掉政治貼文,只看股票或經濟」,
所以方向是 **relevance filter,不是 blanket reject**。

V3.20.3 修法:

**A. Wire-news polarity vocabulary** — lexicon v1.2 → v1.3:
- Bull ~37 新詞:buying opportunity / upside potential / extends gains /
  outperforms / surge(s|d|ing) / soar(s|ed) / jumps / climbs / advances /
  rebounds / recovers / gain(s|ed) / rises / rose
- Bear ~43 新詞:downside (risk) / extends losses / underperforms /
  headwind(s) / plunge(s|d|ing) / tumble(s|d) / slump(s|ed) / slides /
  slid / slip(ped|ping) / drops / drop / declines / declined / falls /
  fell / sinks / sank / retreats / weakens
- 標題詞 RDDT "great buying opportunity, ... downside" 現在能匹配兩端

**B. Truth Social filter** — 新 `truth_social_filter` block in yaml:
- Signature regex strip: `"— President DJT"` / `"-DJT"` / `"RT @ realDonaldTrump"`
- Relevance check:post 必須含一個 economic/market keyword (economy /
  tariff / fed / stock / earnings / jobs / oil / dollar / 經濟 / 關稅 等
  38 keyword + macro topic lexicon 全部 macro term)
- 不含 → drop 整篇 (政治 endorsement 砍掉)
- 含 → 保留 + signature stripped 後跑正常 pipeline
- 套用範圍:只 Truth Social,其他 platform 不影響
- `trending_tickers.py` 新 `apply_truth_social_filter()` 在 `run()` 內
  fetch 後 process 前呼叫

Live verification:
- 49 posts → 41 (7 政治貼被 drop)
- DJT 從 V3.20.2 qualified 列表完全消失 (簽名 strip 後沒 hit)
- RDDT 從 matched_terms=[] → matched_terms=[great buying opportunity, downside]
  (wire-news 詞庫第一次 hit live data)
- RDDT polarity 還是 0.0 — 但原因從「lexicon 0 hit」變「真實 mixed
  (bull + bear 各 1)」,這是 honest signal

Validation:
- `tests/test_trending_tickers.py` → 39 OK (+5 V3.20.3 tests:政治 drop /
  經濟 keep / 簽名 strip / $DJT body 保留 / wire-news polarity hit)
- `tests/test_aggregate.py` → 22 OK
- Live trending output 寫入 Dashboard/trending_tickers.json + 跑 aggregate +
  bridge → data.json[tactical][retail_sector_pulse] FRESH

下一輪改進可能方向 (defer):
- Reddit JSON API (取代 RSS) — 拿真實 upvote 數
- Question-form polarity heuristic ("Is X a buy?" 偏多)
- Topic matcher 改 word-boundary (現在還是 substring,Codex V3.20.1 留的)

---

## 🟢 Session Note (v3.20.1 → v3.20.2) — Dual-Gate + Retail Override + Broad ETF Routing

V3.20.1 ship 後 user 反映 XLK 卡片 retail polarity = None,只剩 price + 2-篇
news,參考價值偏弱。診斷後三個 root cause:

1. **Lexicon 污染** — live trending output 14 個 low_confidence 全是
   `LONG`/`CALLS`/`EARLY`/`GPU`/`NYSE`/`TRUMP`/`NIFTY`/`RINOS`/`FOSS` 這類
   非 ticker (WSB 動詞、英文常用字、組織名、政治 meme)。Lexicon v1.1
   blocklist 漏抓。
2. **Threshold 單閘太嚴** — 真實 ticker (NVDA) 只有 1 Reddit mention
   (engagement=1.0 fallback,RSS feed 不給 upvote 數)。
   `min_mention_count: 2 + min_total_engagement: 5.0` 把它跟 garbage 一起
   demote。
3. **Sector 對映漏** — `DJT` / `SMCI` / `RDDT` / `GME` 等 retail-heavy
   ticker 不在 `SECTOR_UNIVERSE` (mega-cap roster) → `sector=None` →
   silently dropped。`SPY` / `QQQ` 即使被抽到也不該進單一 sector
   (broad index)。

Codex 提出三向修法,我採納並補三點:

- **Dual-gate** instead of naive threshold drop:
  - known_sector: 1 mention, 1.0 engagement (NVDA single Reddit 過閘)
  - unknown_sector: 3 mentions, 8.0 engagement (long-tail garbage 不過閘)
- **retail_only_sector_overrides** in lexicon yaml — DJT/GME/AMC/HOOD/
  COIN/SOFI/SMCI/RDDT/ARM/MU/MARA/RIOT/OXY/MRNA 對映到 GICS sector,
  **不動 SECTOR_UNIVERSE** (避免污染 narrative-pulse-detector / sector
  protocol 等其他 skill)。
- **broad_market_etfs** in lexicon yaml — SPY/QQQ/IWM/DIA/VOO/VTI/
  TLT/VXX/UVXY/SQQQ/TQQQ/SPXS/SPXL 抽到後不進 sector,改 contribute
  到 `market_wide_buzz` 的 `broad_etf` + `market_direction` topic。
- 補:blocklist 擴 9 個 (LONG/CALLS/EARLY/GPU/NYSE/TRUMP/NIFTY/RINOS/FOSS)
- 補:UI card retail polarity 行加 `· n=X` mention 警告,thin sample
  時 dim 字體
- 補:legacy single-gate config backward compat shim

實作層面:
- `aggregate_tickers` 改 return 3-tuple (qualified / low_conf /
  broad_etf_posts);ETF posts 直接 pipe 到 `aggregate_market_wide`
- 加 `build_extended_sector_map(lex)` + `get_broad_etf_set(lex)` 兩個
  helper
- `qualified` 每 ticker 帶 `_gate: "known" | "unknown"` field 供 audit
- 7 條新 V3.20.2 test:blocklist verification, known-sector 1 mention 過閘,
  unknown 不過閘,retail override (DJT→Cons Disc),ETF route to market_wide
  (兩條:aggregate_tickers 層 + 端到端 `run()` 層),legacy config 兼容

Live verification:
- 49 posts → 3 qualified (DJT/RDDT/NVDA),2 unknown demoted,1 market_wide
  topic (ai_capex)。V3.20.1 是 0 qualified / 14 garbage in low_conf。
- Lexicon v1.2:50 blocklist + 15 retail overrides + 13 broad ETFs。

Validation:
- `python3 skills/retail-sector-pulse/tests/test_trending_tickers.py` → 34 OK
- `python3 skills/retail-sector-pulse/tests/test_aggregate.py` → 22 OK
- Live `trending_tickers.py --window-hours 24` → 3 qualified, 2 sectors
  with retail data, blocklist working (LONG/CALLS/NYSE/TRUMP 全擋掉)

---

## 🟢 Session Note (v3.20.0 → v3.20.1) — Polarity-First 3-Lane Sector Pulse

User flagged V3.20.0 retail layer was volume only — `retail_mention_multiplier`
told you Reddit was hot on NVDA but not whether retail was buying or selling.
Wanted to infer "what would a retail investor conclude" from public info.
Through plan → multiple Codex reviews → lexicon-curated implementation:

**Architecture refactor**:

- New `scripts/trending_tickers.py` pulls Reddit / HN / Bluesky / Google Trends
  via existing `social_sources.py`. Per post: extract tickers (with strict
  disambiguation), compute engagement = `log(upvotes+1) + log(comments+1)`,
  and compute bull/bear polarity via **span-masked lexicon match** (longest
  term first; matched span consumed so `short squeeze` does not also fire
  `short`).
- Per-ticker rollup → per-sector engagement-weighted polarity. Thresholds
  (`>= 2 mentions`, `engagement >= 5.0`) demote long-tail garbage to
  `low_confidence[]`. Posts with no ticker or `> 5` tickers go to
  `market_wide_buzz` bucket classified by 9-topic macro lexicon.
- `aggregate.py` refactored: composite formula now **3-lane polarity-first**
  (price 0.30 / retail polarity 0.50 / retail attention 0.20). News digest
  is secondary context only — displayed on card but does NOT enter composite.

**Lexicon (v1.1)** — `config/retail_lexicon.yaml`:

- 120 bull + 138 bear terms covering English / Chinese / WSB / PTT slang.
- Curated by Gemini suggestions filtered by Codex. Skipped high-noise
  emoji (🔥💪🤡💩), ambiguous META/COIN naked whitelist, substring-risk
  qt/qe; corrected 軋多 from bull → bear (it's a long squeeze).
- 137 cashtag-only tickers (AI / ON / X / IT / FOMO / etc. require `$`).
- 41 blocklist acronyms rejected even with `$` (USA / IPO / FED / CPI /
  ATH / YOLO / FUD / DCA / GAAP / FCF / ROIC / ROE / NAV / ESG / etc.).
- 12 high-liquidity naked whitelist (NVDA / TSLA / AAPL / AMD / SMCI /
  PLTR / MSFT / AMZN / GOOG / GOOGL / NFLX / BABA).
- 141 macro topic terms across 9 buckets.

**Codex review must-fix verified by 49 unit tests**:

1. `$NVDA` cashtag always wins; naked rejected for ambiguous English-word
   tickers; blocklist blocks even cashtag form.
2. Span-masked polarity — `short squeeze` → bull (1 hit), not `short` →
   bear; `pump and dump` → bear (1 hit), not pump + dump.
3. Market-wide bucket fires for sectorless macro posts.
4. Inclusion thresholds demote single-mention tickers to `low_confidence`.

**Composite formula trace** (Tech sector smoke):

- trending_tickers: NVDA polarity +0.761, engagement 11.32
- polarity lane: 0.50 × 0.761 = +0.3805
- attention lane: min(11.32, 50)/50 × sign(+) = 0.226 → 0.20 × 0.226 = +0.045
- price lane skipped (smoke used --skip-predict)
- total_w = 0.70; composite = 0.426 / 0.70 = **+0.608** → strong_bull ✓
- framing: "散戶 polarity +0.76 (NVDA); 新聞 2 篇中性。資料部分缺。"

**UI changes** (page-radar.js + radar.html):

- Card 3-line metrics reordered: **Price 5d → Retail polarity → News
  context** (polarity now primary).
- Visual polarity bar (−1 to +1) anchored at center; green right, red
  left, stone-grey within ±0.20.
- Card hover tooltip shows `signal_lanes` breakdown + top 3 sample posts
  for audit.
- New market-wide buzz strip above sector grid renders topic pills with
  polarity (`Fed +0.45`, `recession -0.55`).
- Tooltip `RADAR_TERMS.retail_sector_pulse` rewritten to document 3-lane
  composite formula and polarity-first philosophy.

**daily_update.sh changes**:

- Added Step 9.4 (`trending_tickers.py`) before Step 9.5 (`aggregate.py`).
  Both non-fatal.

Validation:
- `tests/test_aggregate.py` → 22 OK
- `tests/test_trending_tickers.py` → 27 OK
- `node --check Dashboard/page-radar.js` → no syntax errors
- E2E smoke (fixture 8 posts → trending → aggregate): Tech sector composite
  +0.608 strong_bull verified, formula traceable.

---

## 🟢 Session Note (v3.19.1 → v3.20.0) — Retail Sector Pulse · 散戶視角分產業

User asked for a new Tactical Opportunity Radar layer that surfaces, per
sector, the retail-perspective sentiment + multi-day direction. Existing
infrastructure had per-ticker stage (narrative-pulse), per-theme heat
(thematic-screener), and market-wide regime, but nothing per-sector that
combined "news polarity + Reddit chatter + 5d direction" into a single
view for the 11 GICS sectors.

Built `skills/retail-sector-pulse/`:

- `scripts/aggregate.py` reads `news_logs/*_digest.json` (verdicts with
  `affected_sectors[]` + `net_impact_score`), `narrative-pulse-detector/
  cache/<TICKER>_<DATE>.json` (retail_mention_multiplier), and
  subprocesses `short-term-target/predict.py` for each `SECTOR_TOP_5`
  ticker (55 total). Per-sector record carries news / retail / 5d
  signals plus composite_score and rule-based framing.
- `config/weights.yaml` keeps the composite formula declarative: 0.4
  news + 0.4 predicted + 0.2 retail_signed. Sector_aliases map handles
  messy digest values (`"Real Estate"`, `"Tech"`, `"Semiconductors"`,
  `"Defense"`, etc.) — verified against actual digest fixtures during
  exploration.
- 21 unit tests cover bucket boundaries, alias normalization, weighted
  decay, composite traceability, partial-signal re-normalization, and
  framing template output.
- `bridge.py` loads the JSON into `data['tactical']['retail_sector_pulse']`.
- `daily_update.sh` Step 9.5 runs the aggregator after narrative_pulse,
  before bridge.
- `Dashboard/radar.html` has a new section above Narrative Pulse;
  `Dashboard/page-radar.js` adds `renderRetailSectorPulse()` + a new
  `RADAR_TERMS.retail_sector_pulse` tooltip entry. 11-card 4-column
  responsive grid with composite pill, 3-line metric rows, framing
  one-liner, and top-tickers footer.

Codex review during planning caught two contradictions in the draft
plan:

1. "Daily + intraday 4h refresh" in Assumptions vs "intraday deferred"
   in Non-Goals. Picked daily-only for V1 — defers the
   dashboard_server daemon + cache invalidation surface to V3.21+.
2. UI E2E originally said "刻意把 cache 拿掉". Replaced with
   `--sector-override Sector=insufficient_data` CLI flag so testers
   never need to touch real cache.

Known coverage limitation: `SECTOR_TOP_5` tickers (AAPL, LLY, XOM,
BRK-B, AMZN, …) are mostly NOT in the narrative-pulse `batch_scan`
universe today, so `retail_mention_multiplier` is None for most
sectors on initial ship. Aggregator falls back gracefully
(re-normalizes composite weights to available signals). V3.20.1
backlog: expand narrative-pulse universe to include SECTOR_TOP_5 so
retail volume signal is always populated.

Validation:
- `python3 skills/retail-sector-pulse/tests/test_aggregate.py` → 21 OK
- `node --check Dashboard/page-radar.js` → no syntax errors
- `python3 skills/retail-sector-pulse/scripts/aggregate.py --skip-predict
  --output /tmp/rsp.json` → 11 sectors, framing zh+en correct, news
  sentiment correctly joined via alias map
- Full integration with predict.py (55 tickers) running at session
  close — verifies E[R] dispersion across sectors

---

## 🟢 Session Note (v3.19.0 → v3.19.1) — Codex review fixes for V1.1

Codex did a post-implementation review of V3.19.0 and surfaced three real
bugs:

1. **Stage 1 SMA200 "hard gate" was not hard.** Weights `0.4 / 0.3 / 0.3`
   meant `media_quiet + no_sell_side_raise = 0.6 = min_conf`, so a
   below-SMA200 ticker could still classify as Stage 1 brewing as long as
   it was media-quiet with no sell-side raise. Reproduced with
   `sma200_breakout_days_ago=None, price_to_sma200_ratio=0.95`,
   `media_mention_30d=5, pt_raise_60d=0` → stage=1, conf=0.6.
2. **Post-normalize probs could exceed clamp `[0.05, 0.80]`.** Clamp
   happened first, then simple proportional `prob *= scale` could re-inflate
   a clamped 0.80 above the cap. Reproduced with raw `[0.90, 0.05, 0.05]`
   → final `[0.889, 0.056, 0.056]`. The existing test only asserted
   `0 ≤ prob ≤ 1`, so it missed the bug.
3. **batch_scan emitted `"version": "1.0"`** despite the V1.1 breaking
   payload; `schema.md` still documented the V1.0 shape and never
   mentioned `prob_base`, `prob_breakdown`, `expected_return_pct_base`,
   or the shifted `expected_return_pct_pre_macro` semantics.

Fixes:

- **#1**: weights re-balanced `0.5 / 0.25 / 0.25`. `media + no_sell_side = 0.50 < 0.60`,
  so the breakout signal is now effectively mandatory for Stage 1.
- **#2**: replaced naive normalize with `_bounded_normalize()` — water-filling
  iteration that distributes deficit/excess proportional to each scenario's
  headroom toward the relevant bound. Post-normalize values respect
  `[clamp_lo, clamp_hi]` AND `Σ = 1`. Breakdown's `_normalize` entry now
  annotates the bounded behavior.
- **#3**: `batch_scan.py` → `"version": "1.1"`; `schema.md` rewritten
  with V1.1 scenario shape, three-layer E[R], snapshot archive path,
  and an explicit "V1.1 Breaking Schema Changes" table.

Added 2 regression tests reproducing Codex's exact fixtures
(`test_below_sma200_quiet_does_not_classify_stage_1` +
`test_bounded_normalize_respects_clamp`). 30/30 tests pass.

Validation:
- `python3 skills/narrative-pulse-detector/tests/test_stage_classifier.py` → 30 OK
- `python3 skills/narrative-pulse-detector/tests/test_fetch_inputs.py` → 3 OK

### Codex round 3 follow-up — cache + dashboard staleness

After the V1.1.1 commit Codex flagged two more release-hygiene issues:

1. **`weights_version` was not bumped after the post-review fixes.** YAML still
   read `v1.1`; `pulse._cache_fresh()` invalidates on version-string mismatch,
   so existing morning V1.1 cache files (under
   `skills/narrative-pulse-detector/cache/`) would survive into evaluations
   that should have triggered the fixed code paths. Bumped to `v1.1.1` with a
   history comment block in the YAML.
2. **`Dashboard/narrative_pulse.json` was still V1.0.** The daily flow had not
   re-run since the V1.1 series shipped, so the live dashboard payload was
   `version: 1.0`, `weights_version: v1.0`, and lacked
   `expected_return_pct_base` / `scenario_model_version`. Re-ran
   `batch_scan.py --no-cache` to regenerate the full universe under V1.1.1.

Both fixes folded into the V3.19.1 release. No code change beyond the
weights_version string + the batch_scan rerun.

---

## 🟢 Session Note (v3.18.4 → v3.19.0) — Narrative Pulse V1.1 per-ticker scenario math

User flagged that the short-term radar showed every Stage 1 ticker with
identical `+11.2%` E[R] and identical 55/25/20 scenario probabilities — no
information density. Codex's review surfaced a second issue: `fetch_inputs.py`
returned `sma200_breakout_days_ago = 0` when the latest close was *below*
SMA200, which satisfied the Stage 1 brewing rule and let below-SMA200 tickers
masquerade as fresh breakouts.

User priority: not a black-box capped delta. Wants every probability movement
to map to a named YAML rule with a condition and a delta, so weekly
calibration is "edit YAML, not Python."

- Fixed SMA200 breakout semantics at fetch layer (close<SMA200 → None).
- Tightened Stage 1 `sma200_breakout_recent` rule with explicit `is not None`
  + `price_to_sma200_ratio >= 1.0` hard gate.
- Bumped `weights_version: v1.0 → v1.1` so cache invalidates automatically.
- Added `scenario_adjustments:` block to `stage_weights.yaml` for Stage 1, 2,
  4, 5 — Stage 3 (acceleration) intentionally not adjusted. Global
  `prob_clamp: [0.05, 0.80]` + `normalize: true`.
- Implemented `_apply_scenario_adjustments()` in `classify_stage.py` —
  reads YAML, applies deltas, clamps, normalizes, records full breakdown
  per rule.
- Output now carries three E[R] layers: `_base` (V1.0 prior, control for
  5/31 review), `_pre_macro` (V1.1 ticker-adjusted, no macro), and the
  final value. Dashboard renders only the final; the others sit in the
  JSON for analytics.
- `expected_return_pct_pre_macro` semantics shifted (raw prior → adjusted
  sum). Original V1.0 meaning moved to new `expected_return_pct_base`.
  CHANGELOG records this as a breaking schema change.
- `batch_scan.py` now writes a daily snapshot to
  `skills/narrative-pulse-detector/snapshots/<YYYY-MM-DD>.json` for the
  5/31 review (will join momentum-journal forward returns to compute IC /
  hit rate for `base` vs `pre_macro` vs `final`).
- 31 unit tests pass (3 new fetch tests + 7 new V1.1 adjustment tests +
  21 pre-existing). Smoke run on 8 Stage 1 tickers shows V1.0 baseline =
  11.15 (identical) → V1.1 = 5 unique E[R] values across 8 tickers.

Validation:
- `python3 skills/narrative-pulse-detector/tests/test_stage_classifier.py` → 28 OK
- `python3 skills/narrative-pulse-detector/tests/test_fetch_inputs.py` → 3 OK
- `python3 skills/narrative-pulse-detector/scripts/batch_scan.py --tickers AAPL,CSCO,TXN,ASML,WFC,MA,AXP,STM --no-cache` → 8/8 successful, dispersion confirmed.

Tooltip showing `prob_breakdown` on the radar Dashboard is deferred to
V3.19.1 — `Dashboard/page-radar.js` is monolithic and a hover patch is a
separate diff.

5/31 review path: if `pre_macro` IC does not beat `base`, set every
`scenario_adjustments.*.prob_deltas[].delta = 0` in YAML — equivalent to
V1.0 fallback with no code rollback.

---

## 🟢 Session Note (v3.18.3 → v3.18.4) — Momentum rank-score UI wiring

User asked whether the momentum dashboard page had corresponding UI changes for
the new calibrated momentum ranking. It did not: V3.18.2 generated `rank_score`
in the screen/journal/event-index path, but the dashboard table still displayed
and sorted only by raw `score`.

- Added `rank_score` ingestion in `bridge.py`.
- Added a dedicated rank-score table column in `Dashboard/momentum.html`.
- Updated `Dashboard/page-momentum.js` to default-sort by calibrated
  `rank_score`, with fallback to raw `score` for legacy rows.
- Kept the raw `score` slider as the quality threshold so the page now separates
  "base score passes" from "calibrated rank prefers this ticker".

Validation:
- `python3 -m py_compile bridge.py`
- `node --check Dashboard/page-momentum.js`
- `node --check Dashboard/i18n.js`

---

## 🟢 Session Note (v3.18.1 → v3.18.2) — Momentum-screen calibration

User asked why momentum review showed very low screen-run hit rate, then asked
to implement the improvement plan. Implemented momentum-specific calibration
without changing investment protocol buy thresholds:

- Added `rank_score` to momentum screen output and journal flow. Raw `score`
  remains unchanged; Top-N ranking now uses calibrated `rank_score`.
- Ranking rewards Stage 2 / RS leader / fresh 20-50 cross / near-high strength
  and penalizes squeeze/high-short/VCP-only/death-cross/bearish-MACD/extension
  patterns that were dragging recent per-ticker results.
- Added soft cooldown for names repeatedly appearing in recent journal Top-20.
- Dashboard momentum runs now default to conservative leader filters:
  min score 65, RS >= 60, NHP >= -10%, and exclusion of squeeze/death-cross names.
- Added event-index momentum aggregate metrics so future reviews can separate
  screen-run hit rate from per-ticker hit rate and neutral-heavy outcomes.
- Fixed `screen.py --tickers ...` being ignored because `--universe` had a
  default inside a mutually-exclusive group.

Validation:
- `python3 -m py_compile scripts/verdict_rules.py scripts/build_event_index.py scripts/extractors/momentum_extractor.py skills/momentum-monitor/scripts/screen.py skills/momentum-monitor/scripts/journal.py dashboard_server.py`
- `python3 skills/momentum-monitor/scripts/screen.py --tickers AAPL,MSFT,NVDA --max-age 9999999 --output-dir /private/tmp --md-only --cooldown-snapshots 0 --top 3`
- Conservative custom-ticker filter smoke with cached data.

---

## 🟢 Session Note (v3.17.0 → v3.17.1) — Transition overlay review fixes

User asked Codex to first commit the previous feature work, then fix Codex review
findings so Claude can review the fix separately.

- Created feature baseline commit `684b5e7 feat(protocol): add transition overlays`.
- Fixed `earnings-analyst` segment parsing: `business_mix_shift_overlay` now
  flattens `products` / `regions` nested rows from `fetch.py`, excludes metadata
  such as `fiscal_year`, and includes the 25% EMERGING boundary.
- Fixed `earnings-valuation-forecaster`: markdown now renders the
  Revenue-Margin Matrix, `transition_case` emits `transition_case_mtime`, and
  loaded EA bundles backfill `transition_signature_mtime` from cache mtime when
  older caches lack it.
- Renamed V3.17 test files to unique module names, eliminating pytest import
  mismatch when both skill test directories are collected together.
- Aligned protocol/schema/changelog wording for annual PE + FY segment YoY
  numeric anomaly.

Validation:
- `python3 -m pytest skills/earnings-analyst/tests/test_earnings_analyst_v3_17.py skills/earnings-valuation-forecaster/tests/test_forecaster_v3_17.py` → 31 passed
- `python3 -m pytest skills/earnings-analyst/tests/test_earnings_analyst_v3_17.py skills/earnings-valuation-forecaster/tests/test_forecaster_v3_17.py skills/narrative-pulse-detector/tests/test_stage_classifier.py` → 52 passed
- NVDA cache smoke: business mix candidate is `Data Center`, not `fiscal_year`.

---

## 🟢 Session Note (v3.15.1 → v3.15.2) — Break News V4 final-gate polish

Opus final-gate review of Gemini's V4 implementation + codex's V4 review fixes.
Four downstream gaps caught; each would have silently degraded the V4 KG-first
design without breaking tests.

- **Depth-policy shallow_score threshold mis-scaled** (`debater.py:143`):
  `abs(score) >= 7.0` never fires — Stage 1 triage emits values on a ~0–3 scale
  (`abs(s) >= 1.5` important, `>= 3` strong). Dropped to `3.0` to match the
  existing strong gate. Sample real bn item: `shallow_score=2.0`.
- **Futu Push round-cap regression** (`debater.py:189`):
  `item.get("source") == "Futu Push"` compared a dict to a string, so
  `MAX_ROUNDS_FUTU=2` never applied. Fixed to read `.get("name")`.
- **Mega-cap regex case-sensitive** (`debater.py:156`): added `re.IGNORECASE`
  so headlines that render tickers as `Nvda` still trigger high-priority.
- **Dashboard supply-chain UI missing provisional badge**
  (`page-supply-chain.js:53-64`): `RELATION_EVIDENCE` only had `corroborated`
  and `llm` entries; new `break_news_provisional` level was rendering as
  raw key string with no styling. Added amber `◐` badge with BN source-count
  suffix.

Validation:
- `pytest tests/` → 75 passed
- `python3 scripts/break_news/validate.py` → rc=0, 458 files
- `python3 scripts/nexus/build_graph.py --tier 1,2 --dry-run --enable-direct-edge` → 166 nodes / 594 edges / 638kB (under 5MB cap)

Not fixed (out of scope / contested):
- BN-provisional weight (0.2) < llm_relation (0.4) — semantically odd (some
  evidence rates lower than no evidence) but locked in V4 plan + tests.
- `merge_edges` keeps only first edge's metadata — no real impact today since
  `cross_item_count` is identical across duplicates, but worth revisiting.
- Symmetric predicates (`COMPETES_WITH`, `CO_DEVELOPS_WITH`) not order-
  normalized; (A↔B) and (B↔A) would dedupe as 2 edges. Minor.
- `validate.py` uses date-based strict gate instead of `summary.schema_version`
  field — works but a replayed old debate would be marked strict.

---
