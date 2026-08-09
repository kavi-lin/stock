# Nexus Bounded Gap-Fill Schema v1

`Dashboard/nexus_gap_fills.json` is an exploration-only proposal ledger. A
manual runner invocation may process one evidence draft and make at most one
governed LLM call:

```bash
python3 -m scripts.nexus.gap_fill --dry-run
python3 -m scripts.nexus.gap_fill --topic topic:ai_capex
python3 -m scripts.nexus.gap_fill --topic topic:advanced_packaging --agent gemini
python3 -m scripts.nexus.gap_fill --check
```

It is intentionally absent from `daily_update.sh` and `build_graph.py`; daily
automation must not spend model quota.

Without `--topic`, selection preserves score order but skips empty skeletons
and prefers a draft with at least one claim-level corroborated directional edge.
The first model turn should fill around evidence, not construct a chain from an
empty canvas.

## Hard boundaries

- `artifact_class: exploration_only`
- `decision_use: forbidden`
- every entry has `decision_eligible: false`
- one topic may have at most one entry with `inference_turns: 1`
- quota refusal before a call is `blocked` with `inference_turns: 0`
- failure after a call is `failed` and is not retried automatically
- the source draft is pinned by `base_draft_digest`
- output is a sidecar proposal; it never edits the evidence draft or
  `nexus/supply_chains/*.yaml`

`--agent` pins exactly one provider; the router does not fall back to a second
model. Claude runs as text-only Sonnet with one turn, no tools, and strict MCP
isolation. The default 360-second hard deadline is a final process guard;
`--timeout` changes that deadline, not the inference-turn cap.

## Proposal gates

- maximum 8 nodes and 10 edges;
- nodes may only fill private / pre-IPO / foreign / material / component /
  equipment / infrastructure gaps;
- every node and edge cites existing packet `source_id` / `excerpt_id` values;
- every proposal item includes at least one `fetched_page` excerpt; analyst
  extracts alone cannot support a new node or edge;
- a non-empty proposal cites at least two independent source domains overall;
- proposed IDs and tickers cannot duplicate base nodes;
- every edge must touch a proposed node and cannot duplicate an immutable base
  edge;
- relations are limited to `SUPPLIES_TO`, `CONTRACT_MFG_FOR`, and
  `CO_DEVELOPS_WITH`;
- all relationships remain `evidence_level: llm_proposed` until human review.

The validator rejects promotion, duplicate inference turns, invented endpoints,
missing citations, and base-edge rewrites. A valid proposal is still not a
curated supply chain.
