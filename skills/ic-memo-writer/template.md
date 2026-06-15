# {{ticker}} ({{company_name}}) — IC Memo

- **Date**: {{as_of}}
- **Live Spot**: ${{live_spot}} | 52w: ${{range_low}} – ${{range_high}}
- **Analysis Price**: ${{analysis_price}} (protocol session {{protocol_session_date}})
- **Market Cap**: ${{market_cap_human}}
- **Sector / Industry**: {{sector}} / {{industry}}
- **Final Action**: **{{final_action}}** | Verdict: {{verdict_band}} | FV ${{weighted_fair_value}} ({{fv_vs_current_pct}}%)
- **Source**: investment_protocol V5.0 session {{protocol_session_date}} | Memo composer V1.0.0

> {{one_line_thesis}}

<!-- src: profile.live + protocol.history.phase5 -->

---

## §1 一頁摘要

| Field | Value |
|---|---|
| Final Action | **{{final_action}}** |
| Confidence | {{decision_confidence_pct}}% |
| Position Size | {{position_size_pct}}% |
| Entry (aggr / cons) | ${{entry_aggressive}} / ${{entry_conservative}} |
| Stop Loss | ${{stop_loss}} |
| Take Profit | ${{take_profit}} |
| Risk/Reward | {{risk_reward_ratio}}x |
| Time Horizon | {{time_horizon}} |
| Fragility | {{fragility_label}} |

<!-- src: protocol.history.phase5 -->

---

## §2 公司與商業模式

{{company_description}}

- **CEO**: {{ceo}}
- **Employees**: {{full_time_employees}}
- **IPO**: {{ipo_date}}
- **HQ**: {{city}}, {{state}}, {{country}}
- **Website**: {{website}}

<!-- src: profile.live -->

---

## §3 收入結構與成長驅動

### Product Segment (FY trend)

{{product_segment_table}}

### Geographic Segment (FY trend)

{{geographic_segment_table}}

### Business Mix Shift

- **Tier**: {{business_mix_tier}}
- **New segment**: {{new_segment_name}} (share {{new_segment_share}}, YoY {{new_segment_yoy}})
- **Note**: {{business_mix_note}}

<!-- src: earnings_analyst.cache ({{earnings_cache_stale_days}}d stale) -->

---

## §4 客戶 / 供應商 / 競爭格局

### Moat

- **Level**: {{moat_level}}
- **Type**: {{moat_type}}
- **Evidence**: {{moat_evidence}}

### Peers Comparison

{{peers_comp_table}}

> Focus Area / Market Share descriptor 為**第一版 stub**，後續 Phase A.5 將以 Haiku 4.5 一次性生成。

<!-- src: peers.live_fmp + llm_synth.peer_descriptor (stub) -->

---

## §5 最新財務與申報重點

### Latest Quarter Snapshot

{{latest_quarter_table}}

### TTM Metrics

{{ttm_metrics_table}}

### Earnings Surprises (last 4Q)

{{earnings_surprises_table}}

<!-- src: earnings_analyst.cache -->

---

## §6 資產負債表與現金流品質

### Balance Sheet (latest)

{{balance_sheet_table}}

### Cash Flow Quality

- **Cash conversion**: {{cash_conversion_quality}}
- **Quality flags**: {{quality_flags_summary}}

<!-- src: earnings_analyst.cache -->

---

## §7 盈利能力與 2-3 年模型

### Annual Growth Trajectory

{{annual_growth_table}}

### Structural Shift

- **Signature**: {{transition_signature}}
- **Detail**: {{structural_shift_note}}

### Forward Estimates

{{annual_estimates_table}}

<!-- src: earnings_analyst.cache -->

---

## §8 估值：DCF + Multiples + Analyst PT + Peer

### Fair Value 6-Anchor Blend

{{fair_value_anchor_table}}

- **Weighted FV**: ${{weighted_fair_value}}
- **vs Current**: {{fv_vs_current_pct}}% ({{verdict_band}})
- **Confidence**: {{confidence}} ({{anchors_available}}/6 anchors used)
- **Methodology**: {{methodology_note}}

### Individual Analyst PT (from earnings cache)

{{analyst_pt_list}}

<!-- src: protocol.history.phase4_5 + earnings_analyst.cache.valuation -->

---

## §9 催化劑與風險

### Catalysts (sorted by date)

{{catalysts_table}}

### Cross-Asset Spillover

{{cross_asset_table}}

### Key Risks

{{key_risks_list}}

### Decision Point

- **Days to next binary**: {{decision_point_days}}d

<!-- src: protocol.history.phase2.news + phase2.fundamentals -->

---

## §10 Bull / Bear / Base case

### Scenario Odds

| Scenario | Odds |
|---|---|
| Bull | {{scenario_bull}}% |
| Base | {{scenario_base}}% |
| Bear | {{scenario_bear}}% |

### Red Team Counter Thesis

{{red_team_counter_thesis}}

### Kill Conditions

{{red_team_kill_conditions}}

<!-- src: protocol.history.red_team -->

---

## §11 委員會結論

> **此章節 verbatim 來自 protocol.history.phase5，受 decision_lock hash 保護。**

### 當下動作

**{{final_action}}** — {{final_decision}}

### 進場計畫

- Entry (aggressive): ${{entry_aggressive}}
- Entry (conservative): ${{entry_conservative}}
- Stop Loss: ${{stop_loss}}
- Take Profit: ${{take_profit}}
- Position Size: {{position_size_pct}}% ({{position_size_method}})
- Staged Split: {{staged_split}}

### Watch / Re-eval 條件

{{watch_conditions_table}}

<!-- src: protocol.history.phase5 (decision-locked) -->

---

## §12 附錄

### Lane Scores

{{lane_scores_table}}

### Provenance Roster

{{provenance_roster_table}}

### Degraded Sections

{{degraded_sections_list}}

### Validator Result

- rc: {{validator_rc}}
- Decision-lock hash verified: {{decision_lock_verified}}

<!-- src: meta.composed -->

---

*Composed by ic-memo-writer V1.0.0 (deterministic, 0 LLM call) — fact_pack hash {{fact_pack_hash}}*
