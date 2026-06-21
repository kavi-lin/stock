# Supply-Chain Map — YAML Schema

One `<slug>.yaml` per supply chain in this directory. Files are LLM-drafted
(`scripts/nexus/supply_chain.py`) then hand-editable. Only the **skeleton** is
stored — `grounding` and `heat` are computed live at serve time, never stored.

```yaml
id: cpo                              # slug — must match filename stem
title: "CPO 共封裝光學供應鏈"          # display title
theme: "CPO / co-packaged optics"    # the theme prompt used
generated_at: 2026-05-17T00:00:00Z   # ISO8601 UTC
generated_by: claude                 # model/agent that drafted it
refresh_mode: full_generate          # full_generate | rerun_incremental
source_scope: "recent local context + model-available public sources"
previous_generated_at: ""            # set on rerun_incremental
previous_generated_by: ""            # set on rerun_incremental
status: draft                        # draft | reviewed (set to reviewed after a human check)

layers:                              # ordered upstream -> downstream; each = one column
  - materials
  - components
  - integration
  - systems
  - end_customer

modules:                             # 2-3 industry sub-groups per layer
  components:
    - { id: lasers, label: Lasers }
    - { id: optics, label: Optical Components }
  integration:
    - { id: chiplet, label: Optical I/O }

spine: [laser_src, ayar_labs, switch_asic, hyperscaler]   # node ids on the highlighted main flow

nodes:
  - id: ayar_labs                    # unique within this file; lowercase slug
    label: Ayar Labs                 # display name
    layer: integration               # must be one of `layers`
    module: chiplet                   # must be one of that layer's module ids
    role: "光學 I/O chiplet"          # one-line function in the chain
    ticker: null                      # US ticker symbol, or null if not US-listed
    listing: private                  # us_listed | foreign_listed | private | pre_ipo
    market: PRIVATE                   # US | TW | KR | JP | HK | CN | EU | FOREIGN | PRIVATE | PREIPO
    exchange: ""                      # optional exchange code (NASDAQ / TWSE / KRX / TSE...)
    local_ticker: ""                  # non-US local ticker (2330 / 005930 / 8035...), if known
    adr_ticker: ""                    # US ADR / proxy ticker if directly relevant (e.g. TSM)
    country: ""                       # optional country/region label
    investability: ""                 # optional override: direct_us | adr_or_us_proxy
                                      # | international_broker | not_tradeable | unknown
    proxy_tickers: []                 # optional public substitutes for private / pre-IPO nodes
    stage: revenue                    # design_partner | sampling | qualification | production | revenue | unknown
    note: ""                          # optional extra context

edges:
  - from: coherent                    # node id
    to: ayar_labs                     # node id
    rel: SUPPLIES_TO                  # SUPPLIES_TO | CUSTOMER_OF | CONTRACT_MFG_FOR
                                      # | CO_DEVELOPS_WITH | INVESTOR_IN
    note: "EML 雷射"                   # optional
```

## Computed at serve time (not in YAML)

- `grounding` per node — `verified` (ticker in `heatmap_universe.json`) /
  `seen` (in `nexus_graph.json` or recent news) / `llm_only` (no trace).
- `heat` per node — `hot|warm|cold|none`, graded against this chain's own
  mention spread (33/67 percentile) rather than a global threshold, with an
  absolute floor so a low-activity chain cannot mint a `hot` node. Falls back to
  the absolute ladder when fewer than 4 nodes have any mentions.
- `stale` / `stale_reason` per node — `true` when a node has no live
  corroboration (`grounding: llm_only` + `heat: none` + `verification_level:
  llm_only`) on a chain older than `SUPPLY_CHAIN_STALE_DAYS` (default 45). UI
  greys it; the node is never auto-removed. FMP-off is deliberately *not* stale.
- `market_label`, `display_symbol`, and `investability` per node — derived from
  YAML fields plus FMP profile when available. A `foreign_listed` node whose
  FMP name-match resolves to a US exchange has that symbol promoted to
  `adr_ticker`, lifting it to a tradeable proxy.
- `relation_evidence` per edge — `level` (corroborated_relation /
  break_news_provisional / llm_relation) + `weight` + `co_mention_count_30d` +
  `direction`. `direction` (`confirmed|conflict|unverified`) validates the LLM
  arrow against Nexus *directed* supply edges; a `corroborated_relation` whose
  direction is `conflict` has its weight halved (1.0 → 0.5). The co-mention
  threshold stays absolute by design — a relative threshold would make an edge's
  confidence depend on unrelated nodes and break reproducibility.
- `chain_report` — deterministic dashboard summary of investable nodes,
  bottlenecks, private/proxy nodes, and relation-confidence counts.
- `data_quality` — FMP/verification rollup plus `stale_node_count`,
  `chain_age_days`, `override_count`, `fmp_peers_deferred`, and
  `fmp_budget_headroom`.
- `user_status` / `user_note` / `user_override` per node — merged from the user
  override sidecar (see below) when present.

Corroborated, direction-clean edges can be lifted back into the Knowledge Graph
via the opt-in `supply_chain.py --export-edges` batch path (writes a `bn_*.json`
tagged `source_agents: ["supply_chain"]`). `enrich()` itself never writes — the
serve path stays strictly read-only.

## User overrides (sidecar)

User corrections live in `nexus/supply_chains/overrides/<slug>.json`, keyed by
node id: `{node_id: {status, note, fields, updated_at}}`. `enrich()` merges them
first, so corrected `fields` (ticker / market / listing / adr_ticker /
local_ticker / note / proxy_tickers) win over the LLM draft and flow through
grounding + FMP verification — exactly like a manual YAML edit, but the
LLM-drafted YAML is never rewritten. `status` is `confirmed | flagged | none`;
clearing to `none` with no note/fields removes the entry. Written via
`POST /api/supply-chain/<slug>/override`.

## FMP budget tiering

When the daily FMP call budget is more than half spent, `enrich()` verifies
priority nodes first — those on the `spine`, carrying a `ticker`, or with ≥2
downstream edges. Peripheral nodes then serve cached peers only and skip
name-search, so a budget wipe-out can't strip verification from the
structurally important nodes. Profile cache TTL is 30 days.

## Notes

- `listing` is LLM-asserted — treat `private`/`pre_ipo` nodes as research leads,
  not tradeable.
- `generated_at` is the chain draft timestamp, not proof that every underlying
  source was refreshed at that exact time. Use `source_scope` and note-level
  evidence markers to judge freshness.
- `refresh_mode: rerun_incremental` means the LLM was given the prior YAML as a
  baseline and asked to preserve valid structure while updating with recent
  local context / available public sources. It is not a deterministic diff.
- Do not invent ticker symbols. `ticker: null` is correct for any non-US-listed
  or private company.
- For non-US listed companies, prefer explicit `market` + `local_ticker` over
  pretending they are private. Examples: TSMC = `market: TW`, `local_ticker:
  "2330"`, `adr_ticker: TSM`; Samsung Electronics = `market: KR`,
  `local_ticker: "005930"`; Tokyo Electron = `market: JP`, `local_ticker:
  "8035"`.
- `proxy_tickers` are research substitutes, not proof that the private company
  can be traded.
- Edges flow upstream → downstream (`SUPPLIES_TO` source is the supplier).
- `note` should carry evidence hygiene when needed:
  - use `publicly confirmed` / `公開確認` for announced relationships;
  - use `inferred` / `推測` / `unconfirmed` for plausible but unannounced links;
  - keep upstream vendor nodes at `stage: unknown` when the company is important
    structurally but the direct customer relationship is not public.
- For company/ticker themes, include recent listing status, anchor customers,
  hyperscaler or channel partners, and API/marketplace distribution routes when
  publicly known. A map that only contains generic upstream vendors can be
  structurally valid but commercially incomplete.
