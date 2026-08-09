You are filling explicit evidence gaps in one Project Nexus supply-chain draft.

Return exactly one JSON object and no prose. Keep the complete response under
1,500 tokens. You may propose at most 8 nodes and 10 edges. The input draft is
immutable: never rename, delete, relayer, or alter an existing node or edge.
Every proposal remains exploration-only.

Only address these gaps:

- private or pre-IPO companies;
- foreign-listed companies;
- materials, components, manufacturing equipment, or infrastructure nodes;
- unresolved roles already named by the input draft.

Evidence rules:

- You receive a closed source packet. Every proposed node and edge must cite
  packet `source_id` and `excerpt_id`; you may not add URLs or source IDs.
- Every proposal needs at least one excerpt whose packet provenance is
  `fetched_page`. Analyst extracts alone are insufficient.
- Prefer company IR, regulatory filings, official product/customer releases,
  and reputable industry reporting.
- Across the response, cite at least two independent source domains.
- A source must actually support the proposed entity or relationship. Do not
  cite a generic home page or search-result URL.
- Unknown is acceptable. Put unresolved items in `unresolved_gaps`; never fill a
  gap from model memory alone.
- Do not invent ticker symbols. Use null when uncertain.
- Do not repeat a company/ticker already present in `existing_nodes`.
- An edge must connect at least one proposed node. Never restate an existing
  edge and never change its direction.

Required JSON shape:

```json
{
  "topic_id": "topic:...",
  "proposed_nodes": [
    {
      "id": "lowercase_slug",
      "label": "Company or asset name",
      "entity_type": "private_company|foreign_company|material|component|equipment|infrastructure",
      "layer": "upstream|intermediate|downstream|unresolved",
      "role": "one concise role",
      "ticker": null,
      "listing": "private|pre_ipo|foreign_listed|not_applicable|unknown",
      "market": "PRIVATE|PREIPO|TW|KR|JP|HK|CN|EU|FOREIGN|N/A|UNKNOWN",
      "citations": [{"source_id": "src:...", "excerpt_ids": ["excerpt:..."]}],
      "reason": "why this fills a named gap"
    }
  ],
  "proposed_edges": [
    {
      "from": "existing or proposed node id",
      "to": "existing or proposed node id",
      "rel": "SUPPLIES_TO|CONTRACT_MFG_FOR|CO_DEVELOPS_WITH",
      "citations": [{"source_id": "src:...", "excerpt_ids": ["excerpt:..."]}],
      "rationale": "what the cited source supports"
    }
  ],
  "unresolved_gaps": ["gap that still lacks sufficient evidence"],
  "notes": ["optional evidence caveat"]
}
```
