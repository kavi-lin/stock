# CHANGELOG — short-term-target

## v0.1.0 — 2026-04-25

### Added (initial release — Step 1 of plan_short.md)

- **`scripts/predict.py`** — main entry. Outputs 1d / 5d / 15d targets per ticker with full confidence breakdown.
- **`config/weights.yaml`** — hand-editable parameters: per-horizon weights, hard clamps, freshness thresholds, benchmark map.
- **`SKILL.md`** — formal spec.
- **`README.md`** — usage walkthrough + interpretation guide.

### Architecture decisions baked in

- **Per-horizon independent weights**: 1d (news-heavy 0.6) / 5d (momentum-heavy 0.4) / 15d (sector-persistence-heavy 0.4). Not collapsed to single set.
- **Hard clamps**: 1d ±5%, 5d ±15%, 15d ±30%. Prevents cold-start absurd predictions. Clamped predictions auto-penalize confidence by 0.15.
- **Confidence breakdown is fully transparent**: 7 contributors exposed, sum equals final confidence.
- **Benchmark-relative output**: each horizon shows ETF benchmark realized + implied_alpha. Default ETF is SPY (sub-industry GICS lookup deferred to v0.2).
- **Refuses to fabricate**: when source data is stale per horizon's freshness rules → returns `status: insufficient_data` with `missing` and `would_need` populated.
- **Trading meta included**: stop_suggestion (1.5×ATR), position_size_hint (0.33/ATR%, capped 0.5-5%), tx_cost estimate, exit_trigger string.
- **EXPERIMENTAL flag**: every output marks `metadata.experimental: true` + framework label `Tactical Opportunity Radar v0.1`.

### Known limitations (documented in SKILL.md / README.md)

- News driver is **volume/gap proxy**, not real news API. Real Finnhub `/company-news` integration deferred to v0.2.
- GICS sub-industry lookup not implemented — benchmark defaults to SPY.
- No persistent cache layer — every call hits yfinance.
- dual_fetch consumption is best-effort; not enforced.
- No outcome validation yet — Step 5 outcome log accumulates from day 1; weekly_review tool (Step 7) builds on top.

### Smoke test results (2026-04-25)

| Ticker | Profile | 1d conf | 5d target | 15d conf | Notes |
|---|---|---:|---:|---:|---|
| AMD | Stage 2, +13.9% gap | 0.59 | +3.28% | 0.43 | News driver picked up gap correctly; clamp not triggered |
| CEG | Low-vol utility | 0.61 | +1.52% | 0.47 | Predictions modest; confidence highest |
| IONQ | High-ATR (8.18%) quantum | 0.17 | +2.40% | 0.03 | Confidence collapsed correctly for high vol; 15d ≈ "no opinion" |

All three tickers verified:
- ✅ Hard clamp not triggered
- ✅ Confidence breakdown sums correctly
- ✅ High ATR → low confidence
- ✅ Long horizon → lower confidence (1d > 5d > 15d)
- ✅ Benchmark relative populated
- ✅ Trading meta complete
- ✅ EXPERIMENTAL flag in metadata

### Next steps (per plan_short.md)

- **Step 2**: Add 6 new themes to `cross_sector_themes.md` (Space, Nuclear, Quantum, Robotics, Utilities Defensive, Healthcare Defensive)
- **Step 3**: Build `thematic-screener` skill — consume short-term-target outputs across hot-theme constituents
- **Step 4**: Dashboard "Tactical Opportunity Radar" panel
- **Step 5**: outcome tracking log → `data/recommendations/<DATE>.json`
- **Step 7**: `weekly_review.py` — every weekend, suggest weights.yaml diffs

### Validation roadmap

This skill is launched **without backtest validation** — by design, per plan_short.md §6. Outcomes will be collected from day 1 via Step 5 log; first formal evaluation at N≥30 samples (~3-4 weeks of daily runs) via Step 7 weekly_review tool.

Failure threshold (per plan §6 + §12.H): if 8-week hit rate < 50% **OR** median alpha vs benchmark < 0% → entire system retired.
