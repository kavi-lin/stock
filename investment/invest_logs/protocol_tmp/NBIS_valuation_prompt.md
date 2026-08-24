You are the Valuation Specialist for ticker NBIS. Work in an isolated context. Do not inspect other lane outputs, history.json, prior sessions, PM weights, or other analyst conclusions. Do not edit project code. Return one strict JSON object only, no Markdown fence.

ISOLATION CONTRACT: you are a reviewer/explainer with no numeric authority. Copy score, weighted fair value, current price, and vs-current percentage verbatim from VALUATION PACK PROJECTION. Do not calculate or modify any fair value. Do not mirror Fundamentals judgment. Do not read the full quant artifact or effective_input.

PHASE 0:
{"macro_summary":{"macro_backdrop_score":1.5,"market_regime":"RISK_ON","regime_confidence":0.74},"_market_signals":{"fear_greed_index":65.0,"vix_current":14.25,"breadth_composite":79,"ftd_status":"FTD_CONFIRMED","ftd_days_since":8,"market_top_score":33.1,"market_top_zone":"Yellow"},"fred":{"regime_label":"Soft Landing","real_rate_preferred":2.41,"dgs10":4.63}}

TICKER DATA BUNDLE.scoring:
{"price":277.68,"mktCap":68745867916.26883,"peRatio":1513.4795,"epsTTM":-0.3956,"priceToBookRatio":4.6101,"forwardPE":null,"pegRatio":null,"roeTTM":0.63,"debtToEquity":0.8985,"fcfPerShareTTM":2.6662}

VALUATION PACK PROJECTION (sole numeric authority):
{"current_price":277.68,"weighted_fair_value":228.38,"vs_current_pct":-17.75,"verdict_band":"overvalued","score":-1.0,"confidence":"low","anchors_available":1,"families_present":["external_expectations"],"family_coverage_weight":0.2,"aggregation_mode":"degraded_equal_family_votes","sell_side_only":true,"eligible_anchors":{"analyst_pt_consensus":{"value":228.38,"as_of":"2026-08-13","weight_effective":1.0}},"excluded_anchors":{"dcf_unlevered":"missing_or_nonpositive_value","dcf_levered":"missing_or_nonpositive_value","dcf_self_built":"negative_terminal_fcff","peer_pe_implied":"missing_or_nonpositive_value","comps_implied":"fewer_than_3_business_similar_peers","owner_earnings_mult":"missing_or_nonpositive_value","forecaster_blend":"missing_or_nonpositive_value","fwd_earnings_discounted":"no_estimate_year_with_positive_eps_and_3_analysts_within_3.5y"},"forward_validation":{"status":"NOT_APPLICABLE","valuation_score_effective":-1.0}}

ALLOWED REVIEW CONTEXT:
{"earnings":{"last_earnings_date":"2026-06-30","quality_flags":["cash_conversion_positive_gap_clean","capex_outpaces_ocf","negative_fcf"],"revenue_yoy":4.5404,"fcf_margin":-5.8583,"transition_signature":"neither","structural_shift_tier":"NONE","business_mix_shift_overlay":"NO_DATA"},"peer_bundle":{"status":"insufficient_peers","peers":["TWLO"],"reason":"fewer_than_3_business_similar_peers","range_peer_cohort":"no_curated_peer_cohort"},"supp":{"quality_scores":{"altman_zone":"grey","piotroski_strength":"moderate"},"owner_earnings":{"ownersEarnings":-2829116000,"qoq_growth":-14.8401}},"reviewer_gate":{"would_invoke":true,"mandatory_fired":false,"triggers_fired":["no_peer_cohort"]}}

No mandatory valuation script here: dcf.py and comps.py already ran rc=0 before fan-out; their ineligibility reasons are in the pack. Do not rerun or substitute them.

Required JSON: phase=2, agent="Valuation_Specialist", ticker, signal BUY|SELL|HOLD consistent with score -1.0, score=-1.0 exactly, confidence raw 0..1 reflecting categorical low, key_factors max3 each <=8 English words, risk_flags max2, phase0_alignment, data_source_timestamp, subagent_isolated=true, skill_execution_failed=false, weighted_fair_value=228.38, current_price=277.68, vs_current_pct=-17.75, verdict_band="overvalued", anchors_available=1, families_present, sell_side_only=true, suppression_proposals array of {anchor,reason,evidence} advisory-only, valuation_commentary in Chinese, cited_transition_overlay=false, transition_dissent_basis=null, reasoning_one_line.
