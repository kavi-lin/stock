# Forward Expectations Schema (Phase 1 Foundation — shadow)

> Engine: `investment/scripts/forward_expectations.py` v1.13  
> Renderer: `investment/scripts/forward_expectations_report.py` v1.0
> Status: shadow-only. It must not change `fair_value_summary`, `decision_lock`,
> buy thresholds, or position sizing.

## Purpose

Phase 1 compares grounded forward expectations without inventing a forward fair-value
price. It preserves three available views:

- `consensus_lane`: analyst annual revenue/EPS estimates.
- `market_implied_lane`: reverse-DCF implied FCF growth.
- `base_rate_lane`: peer historical revenue growth distribution.

The `independent` lane uses business-model adapters and operating drivers. Implemented
adapters: `royalty_ip` (IP/royalty licensors, e.g. ARM) and `semiconductor` (product/chip
vendors with end-market segments — Data Center / Gaming / Client / Automotive / DRAM /
NAND …, e.g. NVDA / AMD / MU). The registry picks the highest-confidence deterministic
match; `semiconductor` defers IP-licensing names to `royalty_ip`. Each lane stays
unavailable until its numeric drivers, driver evidence, and transmission evidence all pass.

## Non-Negotiable Comparison Rule

Numeric gaps and verdicts require the same metric:

```text
Revenue CAGR <-> Revenue CAGR
EPS CAGR     <-> EPS CAGR
FCF CAGR     <-> FCF CAGR
```

FCF, EPS, and revenue growth may be displayed together descriptively, but they must
not be subtracted or used to produce a cross-metric verdict. If no same-metric pair
exists, the engine returns `comparison_unavailable`.

## Evidence Contract

Every numeric model input must carry:

```json
{
  "metric": "consensus_revenue_cagr",
  "value": 0.38,
  "unit": "ratio",
  "value_type": "consensus",
  "source_type": "fmp_analyst_estimates",
  "source_ref": "earnings-analyst cache annual_estimates",
  "published_at": "2026-05-07",
  "retrieved_at": "2026-06-15T00:00:00+00:00",
  "confidence": "medium"
}
```

Allowed `value_type` values:

| Type | Meaning |
|---|---|
| `observed` | Published historical or market data |
| `guided` | Company management guidance |
| `consensus` | Analyst consensus |
| `derived` | Deterministic calculation from sourced evidence |
| `assumption` | Explicit committee scenario assumption |
| `unknown` | Missing or unverified; rejected as model input |

Rules:

1. Missing source lineage is rejected.
2. `unknown` is retained for audit but cannot enter arithmetic.
3. Guidance ranges remain ranges.
4. Assumptions require explicit source/reason and later bear/base/bull bounds.
5. LLM text extraction may propose evidence; deterministic validation admits it.

## Output Shape

```jsonc
{
  "engine": "forward_expectations.py v1.8 (Estimate Revision Snapshot shadow)",
  "ticker": "ARM",
  "run_id": "20260615T103000123456Z",
  "generated_at": "2026-06-15T10:30:00.123456+00:00",
  "as_of_earnings_date": "2026-05-07",
  "shadow_only": true,

  "consensus_lane": {
    "available": true,
    "revenue_cagr": 0.3842,
    "eps_cagr": 0.3999,
    "analyst_rating_direction": "UP"
  },
  "market_implied_lane": {
    "available": true,
    "required_fcf_cagr": 0.60,
    "out_of_range": true
  },
  "base_rate_lane": {
    "available": true,
    "peer_rev_cagr_median": 0.132
  },
  "independent_lane": {
    "available": false,
    "revenue_cagr": null,
    "reason": "insufficient_evidence",
    "missing_numeric_drivers": ["royalty_bearing_units", "royalty_rate_or_value_per_unit"],
    "missing_driver_evidence": ["royalty_bearing_units", "royalty_rate_or_value_per_unit"],
    "numeric_transmission_paths": 0
  },
  "adapter_evaluation": {
    "selected_adapter": {
      "adapter_id": "royalty_ip",
      "match": {"status": "matched", "score": 100},
      "revenue_exposure_map": {},
      "driver_tree": {},
      "transmission_graph": {}
    }
  },
  "evidence_inventory": {
    "summary": {
      "accepted_count": 7,
      "provisional_count": 12,
      "missing_source_count": 1,
      "missing_driver_count": 4,
      "numeric_transmission_evidence_count": 0
    },
    "accepted": [],
    "provisional": [],
    "missing_sources": [],
    "missing_drivers": []
  },
  "primary_source_acquisition": {
    "cache_first": true,
    "network_fetch_used": false,
    "summary": {
      "candidate_count": 0,
      "promoted_count": 0,
      "provisional_count": 0,
      "driver_candidate_count": 0,
      "guidance_candidate_count": 0,
      "guidance_promoted_count": 0
    },
    "promoted": [],
    "provisional": [],
    "guidance_promoted": [],
    "guidance_provisional": []
  },
  "guidance_extraction": {
    "summary": {
      "candidate_count": 0,
      "promoted_count": 0,
      "provisional_count": 0
    },
    "promoted": [],
    "provisional": []
  },
  "estimate_revision_snapshot": {
    "available": true,
    "estimate_revision_delta_available": false,
    "estimate_revision_delta_reason": "annual_estimates cache has latest forward curve only; compare future ledger snapshots for deltas",
    "annual_estimate_snapshot": {},
    "latest_year": {},
    "rating_momentum": {}
  },
  "forward_financial_bridge": {
    "available": true,
    "status": "available",
    "forecast_basis": "consensus_annual_estimates_plus_historical_conversion",
    "historical_conversion": {
      "gross_margin": 0.9543,
      "operating_margin": 0.1865,
      "net_margin": 0.1715,
      "fcf_margin": 0.1498,
      "diluted_share_count": 1069000000,
      "tax_and_other_rate": 0.0804
    },
    "rows": [
      {
        "date": "2028-03-31",
        "forecast_basis": "consensus_annual_estimates",
        "revenue": {"point": 7580380675, "low": 7459492424, "high": 7735248599},
        "gross_profit": {"point": 7233880000, "low": 7118520000, "high": 7381620000},
        "operating_income": {"point": 1413540000, "low": 1390990000, "high": 1442410000},
        "net_income_from_margin": {"point": 1300130000, "low": 1279400000, "high": 1326690000},
        "eps_consensus": {"point": 2.9394, "low": 2.8784, "high": 3.0175},
        "eps_implied_net_income": {"point": 3142200000, "low": 3077040000, "high": 3228100000},
        "free_cash_flow": {"point": 1135550000, "low": 1117440000, "high": 1158740000},
        "guidance_overlay": {},
        "consistency_checks": []
      }
    ],
    "missing_inputs": [],
    "warnings": []
  },
  "expectations_gap": {
    "available": true,
    "summary": {
      "status": "same_metric_gap_available",
      "same_metric_gap_count": 1,
      "unavailable_metric_count": 2,
      "bridge_risk_count": 1
    },
    "metrics": {
      "revenue_cagr": {
        "market_implied": null,
        "consensus": 0.3842,
        "independent": null,
        "base_rate": 0.132
      },
      "eps_cagr": {
        "market_implied": null,
        "consensus": 0.3999,
        "independent": null,
        "base_rate": null
      },
      "fcf_cagr": {
        "market_implied": 0.60,
        "consensus": null,
        "independent": null,
        "base_rate": null
      }
    },
    "same_metric_gaps": [
      {
        "metric": "revenue_cagr",
        "left": "consensus",
        "right": "base_rate",
        "delta": 0.2522,
        "verdict": "consensus_above_base_rate"
      }
    ],
    "unavailable_same_metric": [
      {"metric": "eps_cagr", "available_sources": ["consensus"], "status": "no_same_metric_comparator"},
      {"metric": "fcf_cagr", "available_sources": ["market_implied"], "status": "no_same_metric_comparator"}
    ],
    "cross_metric_observations": [],
    "financial_bridge_risks": []
  },
  "scenario_policy": {
    "available": true,
    "status": "range_or_overlay_only",
    "gates": {
      "base_metric": {"status": "pass", "reason": "consensus_growth_available"},
      "driver_evidence": {"status": "fail", "reason": "missing_numeric_drivers"},
      "conversion_method": {"status": "fail", "reason": "no_numeric_transmission_conversion"},
      "bridge": {"status": "pass", "reason": "forward_bridge_available"},
      "range_discipline": {"status": "pass", "reason": "ranges_must_remain_ranges"}
    },
    "allowed_modes": [
      {"mode": "qualitative_driver_watchlist", "status": "allowed"},
      {"mode": "consensus_range_bridge", "status": "allowed"}
    ],
    "forbidden_methods": [
      "fixed_pct_eps_pe_haircut",
      "fixed_pct_revenue_haircut_without_driver",
      "llm_invented_tam_or_penetration",
      "cross_metric_gap_as_numeric_driver",
      "single_point_guidance_range_collapse"
    ]
  },
  "source_discovery": {
    "profile_origin": "profile_cache",
    "filing_metadata_origin": "filing_metadata_cache",
    "network_fetch_used": false,
    "candidate_count": 2,
    "filing_family_counts": {"annual_report": 1},
    "candidates": []
  },
  "document_acquisition": {
    "cache_first": true,
    "network_fetch_used": false,
    "summary": {
      "document_count": 0,
      "skipped_count": 2,
      "cache_hit_count": 0,
      "network_fetch_count": 0
    },
    "documents": [],
    "skipped": []
  },

  "expectations_matrix": {
    "metrics": {
      "revenue_cagr": {
        "market_implied": null,
        "consensus": 0.3842,
        "independent": null,
        "base_rate": 0.132
      },
      "eps_cagr": {
        "market_implied": null,
        "consensus": 0.3999,
        "independent": null,
        "base_rate": null
      },
      "fcf_cagr": {
        "market_implied": 0.60,
        "consensus": null,
        "independent": null,
        "base_rate": null
      }
    },
    "same_metric_comparisons": [],
    "verdict": "comparison_unavailable",
    "cross_metric_policy": "FCF、EPS、營收 CAGR 不互減、不產生跨口徑 verdict。"
  },
  "evidence_contract": {
    "status": "pass",
    "accepted_count": 3,
    "rejected_count": 0,
    "accepted": [],
    "rejected": []
  }
}
```

`base_rate_lane.peer_rev_cagr_*` is populated only when the deterministic cohort gate
finds at least three comparable businesses. A broad raw provider peer list may be retained
under `raw_peer_distribution` for disclosure, but remains unavailable to numeric gap
comparisons and cannot serve as the anti-fantasy base-rate anchor.

## Immutable Forecast Ledger

Every run receives a UTC microsecond `run_id` and writes:

```text
investment/invest_logs/forward_expectations/<TICKER>_<run_id>.json
```

Snapshots use exclusive-create semantics and cannot overwrite a prior run. Each
snapshot stores `generated_at`, source lineage, engine version, market price, and
available lanes. It also stores the point-in-time Evidence Inventory, including
provisional and missing evidence. Forecast-vs-actual calibration remains a later phase.

## Evidence Inventory Promotion

`forward_expectations_evidence.py` classifies local evidence:

- `accepted`: structured company/financial facts, analyst consensus, or corroborated
  causal relations carrying a numeric conversion method.
- `provisional`: associations, Nexus `CO_THEME`, uncorroborated causal relations, and
  narratives without conversion evidence.
- `missing_sources`: required source artifacts that are unavailable.
- `missing_drivers`: adapter-specific acquisition targets and preferred primary sources.

Provisional evidence is preserved for research direction but cannot satisfy numeric
Independent-lane gates.

## Primary-Source Acquisition

`forward_expectations_primary_sources.py` reads only:

- an existing earnings-cache transcript; or
- an explicit filing/IR/transcript text bundle supplied with `--primary-source-file`.

It does not fetch the web and does not use LLM inference. Royalty/IP extraction is
limited to explicit statements for units, royalty rate/value per unit, license
conversion, and data-center exposure.

A candidate is promoted only when value, unit, period, publication date, supported
primary source type, and source URL/ref are all present. Incomplete or unsupported
documents remain provisional. Promoted direct-driver values may populate the adapter,
but cannot create a forecast CAGR or transmission conversion by themselves.

## Management Guidance Extraction

`forward_expectations_guidance.py` extracts explicit company guidance / outlook
statements from primary-source documents. It is ticker-neutral and accepts only
company filings, IR documents, or earnings transcripts. Supported initial metrics:

- revenue / sales;
- EPS / diluted EPS;
- gross margin;
- operating margin;
- free cash flow;
- capex.

Guidance ranges remain ranges. A midpoint may be emitted as a derived helper, but it
is not treated as management's original value. Historical results without guidance
verbs are ignored; investment reports and unsupported narratives remain provisional.
Accepted guidance enters the Evidence Inventory with `value_type=guided`.

## Estimate Revision Snapshot

`forward_expectations_revisions.py` records point-in-time market expectations from
the earnings-analyst cache:

- annual revenue / EPS consensus by future fiscal year;
- low / high dispersion and analyst counts;
- rating momentum from dated analyst grade snapshots.

The current cache stores the latest forward estimate curve, not historical versions
of the same estimate. Therefore true revenue/EPS estimate revision deltas are marked
`estimate_revision_delta_available=false` until future forecast-ledger snapshots can
be compared. This prevents the engine from fabricating analyst up/down revisions from
a single static snapshot.

Accepted revision evidence appears as `consensus_revision:<metric>` and remains a
market-expectations record, not a management guidance record and not a live valuation
input.

## Forward Financial Bridge

`forward_expectations_financial_bridge.py` maps sourced forward revenue/EPS
expectations into a simplified financial statement bridge:

```text
Revenue → gross profit → operating income → tax/other → net income → FCF / EPS implied net income
```

Inputs are limited to existing structured evidence:

- `annual_estimates` revenue/EPS consensus;
- historical gross/operating/net margins from `derived.margins_8q` or `quarterly_pnl`;
- FCF margin and capex intensity from `derived.cash_flow_quality` or recent cash-flow rows;
- diluted share count from `quarterly_pnl` or enterprise-value metadata;
- promoted management guidance as overlay evidence only.

The bridge is ticker-neutral and does not contain ARM-specific logic. It degrades to
`insufficient_inputs` when core conversion inputs are missing. Guidance ranges remain
ranges and do not overwrite consensus by default. The bridge may emit consistency
checks, such as consensus EPS implied net income versus historical-margin implied net
income, but it does not produce fair value, valuation upside, decision locks, or
position-sizing changes.

## Expectations Gap

`forward_expectations_gap.py` summarizes the gap between available forward views:

- `market_implied`: reverse-DCF required FCF CAGR;
- `consensus`: analyst revenue/EPS CAGR;
- `independent`: committee adapter output when numeric evidence gates pass;
- `base_rate`: peer historical revenue-CAGR distribution.

Numeric gaps require the same metric. For example, consensus revenue CAGR may be
compared with base-rate revenue CAGR or independent revenue CAGR. Market-implied FCF
CAGR must not be subtracted from consensus EPS or revenue CAGR. When a metric has only
one source, the gap block emits `no_same_metric_comparator`; when cross-metric
pressure exists, it emits a descriptive `cross_metric_observation`.

Financial bridge warnings and consistency checks are surfaced as
`financial_bridge_risks`. These describe narrative risk, such as EPS-implied net
income diverging from historical-margin implied net income, but they are not valuation
verdicts and must not alter live decisions.

## Scenario Policy

`forward_expectations_scenario_policy.py` authorizes which scenario modes are allowed
from the current evidence. It does not generate bear/base/bull numbers. Supported
statuses:

| Status | Meaning |
|---|---|
| `numeric_scenario_allowed` | Driver evidence and numeric transmission conversion exist; a later builder may produce driver-based bear/base/bull. |
| `range_or_overlay_only` | Consensus bridge and/or management guidance overlay can be shown, but numeric driver scenarios are blocked. |
| `qualitative_only` | Only qualitative driver watchlist is allowed. |
| `insufficient_inputs` | No forward base metric is available. |

Required gates for numeric driver scenarios:

- `base_metric`: a sourced forward metric exists;
- `driver_evidence`: explicit operating driver values have source lineage;
- `conversion_method`: transmission from driver to financial output is numeric and sourced;
- `bridge`: financial bridge is available when financial statement consistency is required;
- `range_discipline`: ranges remain ranges.

Forbidden methods include fixed EPS/P-E percentage haircuts, LLM-invented TAM or
penetration assumptions, using cross-metric gaps as numeric drivers, and collapsing
guidance ranges into single-point assumptions.

## Shadow Report Renderer

`forward_expectations_report.py` renders a snapshot into a Markdown advisory section:

- Expectations Matrix;
- Expectations Gap;
- Financial Bridge Risk;
- Operating-Driver Scenarios;
- Future Price Range;
- Shadow-only policy footer.

The renderer is read-only. It does not calculate valuation, mutate the snapshot,
write session exports, or alter protocol validators. Its output may be pasted or
included in a report as an advisory section, but it must not replace
`fair_value_summary`, `decision_lock`, or live verdict fields.

## Future Price Range

`forward_expectations_price_range.py` maps sourced forward bridge rows into a
shadow-only future price range. It is the first forward layer output that may answer
"what future price range does this ticker imply?", but it is still not live fair value.

Top-level snapshot field:

```json
"future_price_range": {
  "engine": "forward_expectations_price_range.py v1.3",
  "ticker": "ARM",
  "available": true,
  "status": "available",
  "shadow_only": true,
  "valuation_output": "future_price_range_shadow",
  "changes_live_decision": false,
  "horizon_date": "2030-03-31",
  "horizon_basis": "terminal_margin_normalized",
  "horizon_years": 4.6,
  "horizon_coverage": 11,
  "horizon_interpretation": "multi_year_terminal_value_not_12m_price_target",
  "horizon_coverage_quality": "thin",
  "reporting_to_trading_fx": 1.0,
  "method": "eps_x_pe",
  "range": {"low": 60.0, "base": 100.0, "high": 150.0},
  "cases": {
    "bear": {"target_price": 60.0, "upside_pct": -40.0, "annualized_pct": -10.5, "metric": "eps_consensus", "metric_value": 4.0, "multiple": 15.0},
    "base": {"target_price": 100.0, "upside_pct": 0.0, "annualized_pct": 0.0, "metric": "eps_consensus", "metric_value": 5.0, "multiple": 20.0},
    "bull": {"target_price": 150.0, "upside_pct": 50.0, "annualized_pct": 9.2, "metric": "eps_consensus", "metric_value": 6.0, "multiple": 25.0}
  },
  "trajectory": [
    {"date": "2028-03-31", "years_out": 2.6, "coverage": 30, "thin_coverage": false, "consensus_eps": 4.0,
     "is_terminal": false, "targets": {"bear": 80.0, "base": 88.0, "bull": 110.0},
     "cumulative_upside_pct": {"base": 41.6}, "annualized_pct": {"base": 14.2}},
    {"date": "2030-03-31", "years_out": 4.6, "coverage": 11, "thin_coverage": true, "consensus_eps": 5.0,
     "is_terminal": true, "targets": {"bear": 60.0, "base": 100.0, "high": 150.0},
     "cumulative_upside_pct": {"base": 0.0}, "annualized_pct": {"base": 0.0}}
  ]
}
```

**Currency normalization (V4.42.0).** For a foreign-domiciled ADR, FMP statements/estimates
are in the company's **reporting currency** (TSM→TWD, ASML/SAP→EUR) while the ADR price /
market cap / multiple anchor are in the **trading currency** (USD). `reporting_to_trading_fx`
is the divisor that converts reporting-currency EPS / revenue / FCF into the trading currency
before any price-currency multiple is applied (1.0 = no conversion). It is resolved in the
top-level `currency_normalization` node via `resolve_reporting_fx()` — priority: income
statement `reportedCurrency==USD` → 1.0; FMP forex `{CUR}USD` → 1/rate; else implied from the
statement-vs-ADR EPS ratio when the gap is currency-scale (>5×); else parity. A
defense-in-depth **sanity gate** flags `currency_unit_suspect` and falls back to the
self-consistent advisory band whenever a price-basis forecast's base target lands >6× or <1/6
of the current price (a currency-unit mismatch that slipped through). Shadow-only; never
alters live decisions.

**Per-FY annualized glide trajectory (V4.40.0).** `trajectory[]` gives a target price for
each forward fiscal year as a geometric glide path TO the headline terminal target
(`implied = current × (terminal/current)^(t/T)`), so the annualized rate is constant along
the path. It is NOT a per-year re-valuation: for a hypergrowth name the near-year price is
dominated by an unknowable multiple assumption, and re-valuing each FY at today's rich
multiple explodes the target (tautology trap). Each row carries `years_out`, analyst
`coverage`, a `thin_coverage` flag (<20 analysts), that FY's `consensus_eps` for context,
`is_terminal`, and bear/base/bull `targets` + `cumulative_upside_pct` + `annualized_pct`.
Past/already-reported fiscal years (`years_out ≤ 0`) are excluded. The headline
`horizon_date` remains the terminal (farthest) row — that is where growth has cooled enough
for the mature multiple + margin normalization to apply (`horizon_basis:
terminal_margin_normalized`). It is explicitly labelled a multi-year terminal value, not a
12-month target. Headline cases include both cumulative `upside_pct` and
`annualized_pct`; terminal coverage below 20 analysts is flagged as thin and a
price-independent forecast is downgraded to `low_confidence_terminal_range`.

Supported mapping order:

1. `eps_x_pe`: forward EPS consensus × P/E range.
2. `revenue_per_share_x_ps`: forward revenue per share × P/S range.
3. `fcf_per_share_x_pfcf`: forward FCF per share × P/FCF range.

Multiple source priority (EXP-R1):

1. Explicit `valuation_multiples` input (`pe_range`, `ps_range`, `pfcf_range`, etc.) →
   `multiple_quality: explicit`.
2. **Historical multiple regime** (`forward_expectations_multiple_anchor.py`): the
   ticker's own FMP `ratios` annual P/E, P/S, P/FCF history. Each year uses that year's
   price, so the median/p25/p75 band is INDEPENDENT of today's price. A metric's regime
   is used only when it has ≥2 positive years and p75/p25 dispersion ≤ 3.0 (noisy regimes
   are rejected so a stabler metric can be chosen). → `multiple_quality: historical`,
   `multiple_range.method: historical_multiple_regime`.
3. Derived current-market multiple band (`current_price / horizon_eps_consensus`, etc.).
   This band's base case mathematically equals today's price — it is a ±15% volatility
   band, **not a forecast**. When this is the only available path the output is downgraded
   to `status: advisory_band_only` with warnings `derived_current_market_multiple_used` and
   `current_price_volatility_band_not_forecast`. → `multiple_quality: derived`.

**Multiple compression (EXP-3.4 / V4.40.0 PEG terminal P/E).** The historical regime
reflects PAST growth, so applying a hyper-growth-era multiple onto a horizon metric
overshoots (NVDA ~57x, ARM ~151x). `forward_expectations_multiple_compression.py` haircuts
the historical band toward the level FORWARD growth justifies.

- **P/E — bound to TERMINAL growth (not the calendar year).**
  `terminal_pe = clamp(2.2 × terminal_growth_pct, 20, 60)`, then the historical P/E band is
  pulled to `min(historical_p50, terminal_pe)` with the dispersion scaled proportionally.
  `terminal_growth` is the revenue YoY entering the terminal (horizon) year, with a
  thin-coverage noise guard: if the terminal year RE-ACCELERATES vs the prior step and its
  analyst coverage is thin (<20), the prior, better-grounded YoY is used instead
  (`terminal_growth_basis = prior_year_yoy_terminal_noise_guard`). This avoids both a flat
  ceiling that wrongly caps durable AI-infra compounders and freezing today's hypergrowth
  multiple forever — as growth decelerates the deserved P/E compresses automatically.
  The applied band carries `growth_tier: peg_terminal`, `terminal_pe_peg`,
  `compression_factor`, `historical_band`; method `peg_terminal_growth_bound`. The anchor's
  `compression` block echoes `terminal_growth`, `terminal_growth_basis`, `terminal_pe_peg`.
  Because compression now needs the per-FY revenue path, `compress_anchor` runs AFTER the
  financial bridge is built. (NVDA: hist 57x, terminal growth 13.7% → PEG 30x. ARM: hist
  151x, growth >27% → clamped to the 60x ceiling.) The PEG constants (2.2 / 20 / 60) are the
  calibration lever.
- **P/S, P/FCF (and P/E fallback when no terminal-growth signal):** legacy growth-tier
  factor `effective = historical × growth_factor` on the consensus estimate-window CAGR.
  Tiers: hypergrowth ≥0.25 (×1.00) · growth ≥0.15 (×0.82) · moderate ≥0.07 (×0.66) ·
  slowing ≥0.03 (×0.52) · mature <0.03 (×0.40). Method `historical_regime_growth_compressed`.

**Margin normalization (EXP-3.4b).** The bridge holds today's net margin to the horizon,
which bakes monopoly economics into the EPS for a supernormal-margin company. When the
held net margin exceeds 40%, `forward_expectations_margin_normalization.py` builds a
bear/base/bull margin PATH using durable-platform RETENTION factors (bear 0.62 / base 0.80
/ bull 1.00 — bull keeps today's margin, a tail) — deliberately NOT a sector mean reversion,
which would underestimate a genuine platform franchise. A floor at the company's own recent
margin × 0.85 protects structurally high-margin franchises. The bridge is
revenue_scenario × margin_scenario → normalized net income → normalized EPS, and that EPS
band overrides the held-margin consensus EPS in the price-range eps path
(`eps_basis=margin_normalized`). NVDA: held 60% → bear/base/bull 37/48/60%; combined with the
PEG terminal P/E (30x on 13.7% terminal growth) the terminal base ≈ $562 (ann ~+24%/yr).
(NB: an earlier ≈$252 base was an artifact of a truncated `limit=3` estimate fetch that made
far-out revenue look flat → mis-tiered NVDA as "mature" → 22x; the `limit=6` fix + PEG
correct it.)

The builder prefers an explicit/historical forecast over the derived advisory band, and
auto-selects the metric whose historical regime is usable (e.g. P/S over a noisy P/E).
With `--no-fetch` the historical regime is skipped and the output degrades to the labelled
advisory band. The selected `horizon_date` is the farthest forward bridge row. The output
is a future estimate-horizon range, not today's live fair-value anchor. Applying a
persisted historical multiple to a much larger forward metric assumes regime persistence;
the band's dispersion and `multiple_quality` are surfaced so the reader can judge it.

## Success Criteria (EXP-0.4)

`forward_expectations_success_criteria.py` is the read-only acceptance yardstick and the
gate that EXP-4.5 (shadow → live) must clear. Success is **never** "valuation went up";
it is measured on eight falsifiable criteria:

| Criterion | Source | Pass condition |
|---|---|---|
| `sample_sufficiency` | calibration | comparable rows ≥ `min_sample_n` (15) |
| `forecast_error_wape` | calibration | worst lane WAPE ≤ 0.30 |
| `directional_accuracy` | calibration | worst lane directional ≥ 0.60 |
| `forecast_bias` | calibration rows | \|mean signed relative error\| ≤ 0.20 (no systematic over/under) |
| `driver_explainability` | snapshot evidence_contract | accepted > 0 and rejected = 0 (numbers trace to evidence) |
| `source_completeness` | snapshot | evidence_contract `pass` and missing sources = 0 |
| `expectations_gap_verifiability` | snapshot | ≥ 1 auditable same-metric gap |
| `not_valuation_inflation` | snapshot | shadow_only flags intact; success not defined by higher fair value |

Verdict: any `fail` → `fail`; any `insufficient_sample`/`insufficient_data` → `insufficient_evidence`;
all `pass` → `pass`. `shadow_to_live_gate` is true only on `pass`. A `pass` is **necessary, not
sufficient**, for live wiring — user approval is still required. Thresholds tighten only with
evidence and never to make the valuation look better. The evaluator changes no live decision.

```bash
python3 investment/scripts/forward_expectations_success_criteria.py                       # run calibration + gate
python3 investment/scripts/forward_expectations_success_criteria.py --snapshot-file <snap> # add explainability/source/gap checks
```

## Calibration Scaffold

`forward_expectations_calibration.py` is read-only. It scans immutable forecast
snapshots and later earnings-analyst caches, then emits forecast-vs-actual rows where
comparison is valid.

Supported comparisons:

- `consensus.revenue_cagr` vs realized CAGR over the same fiscal-year window;
- `consensus.eps_cagr` vs realized net-income CAGR proxy over the same fiscal-year window;
- point-in-time `consensus_revision` revenue/EPS levels vs completed Q1-Q4 fiscal-year sums.

Future-level snapshots remain `actual_not_comparable_yet` until matching actual fiscal-year
levels exist. A snapshot generated on or after the target fiscal year-end is rejected as
`not_point_in_time_forecast`. Re-run duplicates are collapsed to the earliest vintage for
each ticker/target/basis so later refreshes cannot erase or multiply the original forecast.
The scaffold reports:

- absolute percent error;
- directional hit / miss;
- per-lane sample counts;
- WAPE proxy;
- directional accuracy;
- `insufficient_sample` when `n < min_required_n`.

Calibration output must not alter live decisions, weights, fair value, or position
sizing.

## Ticker-Neutral Source Discovery

`forward_expectations_source_discovery.py` identifies candidate source locations for
any ticker. It reads the shared company-profile cache for website/CIK, reuses a
24-hour filing-metadata cache, and may query FMP `sec-filings-financials` when fetch
is allowed. It classifies forms from observed filing metadata:

- annual reports: `10-K`, `20-F`, `40-F`;
- interim reports: `10-Q`;
- foreign-issuer reports: `6-K` remains neutral because metadata alone cannot tell
  whether it contains interim results or a material event;
- current reports, proxy filings, registration filings, and unknown forms.

Discovery is independent of ticker, country, sector, archetype, and adapter. Company
website roots, SEC submissions manifests, filing URLs, and transcript locations remain
`metadata_only` or `content_available`, provisional, and never numeric eligible.
Discovery does not download filing text and cannot satisfy an adapter driver.

## Bounded Document Acquisition

`forward_expectations_document_acquisition.py` is an opt-in bridge from discovery
metadata to normalized text bundles. It is disabled by default; `forward_expectations.py`
only uses it when `--acquire-documents` is supplied. With `--no-fetch`, it remains
cache-only.

Allowed fetch scope is deliberately narrow:

- source must come from the discovery manifest;
- source type must be `company_filing`;
- host must be `sec.gov`, `www.sec.gov`, or `data.sec.gov`;
- `data.sec.gov` submission manifests remain metadata-only and are not downloaded as
  document evidence;
- SEC document URLs must be under `/Archives/edgar/data/` and end in `.htm`, `.html`,
  or `.txt`;
- company website / IR roots are not fetched by this layer.

Downloaded HTML is normalized to plain text and passed as a primary-source bundle.
The normalized text is still not evidence. Only `forward_expectations_primary_sources.py`
can promote explicit metric statements after value/unit/period/date/source gates pass.

## Adapter Boundary

Cross-industry Independent forecasts must implement
`investment/forward_expectations_adapter_contract.md`. A matched adapter may produce
an exposure map and qualitative transmission graph, but it cannot emit a numeric
Independent lane until all operating-driver and evidence gates pass.

## Invocation

```bash
python3 investment/scripts/forward_expectations.py --ticker ARM --self-assemble
python3 investment/scripts/forward_expectations.py --ticker ARM --self-assemble --no-fetch
python3 investment/scripts/forward_expectations.py --ticker ARM --self-assemble --primary-source-file primary.json
python3 investment/scripts/forward_expectations_source_discovery.py ARM --no-fetch
python3 investment/scripts/forward_expectations.py --ticker ARM --self-assemble --acquire-documents
python3 investment/scripts/forward_expectations_guidance.py --primary-source-file primary.json
python3 investment/scripts/forward_expectations_revisions.py --ticker ARM --earnings-cache-file skills/earnings-analyst/cache/ARM_2025-12-31.json
python3 investment/scripts/forward_expectations_calibration.py
python3 investment/scripts/forward_expectations_report.py --snapshot-file investment/invest_logs/forward_expectations/ARM_<run_id>.json
cat inputs.json | python3 investment/scripts/forward_expectations.py
```
