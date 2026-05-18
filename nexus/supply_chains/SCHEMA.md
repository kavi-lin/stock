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
- `heat` per node — `hot|warm|cold|none` from the Nexus node's mention count.

## Notes

- `listing` is LLM-asserted — treat `private`/`pre_ipo` nodes as research leads,
  not tradeable.
- Do not invent ticker symbols. `ticker: null` is correct for any non-US-listed
  or private company.
- Edges flow upstream → downstream (`SUPPLIES_TO` source is the supplier).
