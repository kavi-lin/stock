# Nexus Evidence-Only Draft Schema v1

`Dashboard/nexus_evidence_drafts.json` is a deterministic projection of the
highest-ranked uncovered topics in `Dashboard/nexus_topics.json`. It is rebuilt
after topic discovery and uses zero LLM calls.

These drafts belong to the **exploration layer**:

- `artifact_class` is always `exploration_only`;
- `decision_use` is always `forbidden`;
- every draft has `status: evidence_only` and `decision_eligible: false`;
- drafts never write `nexus/supply_chains/*.yaml` and never affect an investment
  verdict, buy threshold, score, or position size.

## Deterministic projection

The builder takes the 12 highest-score `new_chain_candidates` (velocity and
source count break ties). It may only create ticker nodes already listed by the
source topic. `SUPPLIES_TO` and
`CONTRACT_MFG_FOR` form the upstream → intermediate → downstream flow;
`COMPETES_WITH` and `CO_DEVELOPS_WITH` remain context edges.

Layers are graph-derived:

- outgoing flow only → `upstream`;
- incoming and outgoing flow → `intermediate`;
- incoming flow only → `downstream`;
- no directional flow → `unresolved`.

The builder does not guess private companies, foreign suppliers, materials, or
equipment vendors. Those omissions are explicit `known_gaps` for later human
review or one bounded gap-fill pass.

Relation evidence is `corroborated` only when the canonical triple exists in
the claim ledger and shares a source artifact with the topic. Otherwise it is
labelled `topic_context`; the draft never upgrades it silently.

## Commands

```bash
python3 -m scripts.nexus.evidence_drafts
python3 -m scripts.nexus.evidence_drafts --check
```

The validator rejects invented nodes, unknown edge endpoints, duplicate source
keys, invalid URLs, sub-threshold source topics, and any attempt to mark a draft
as decision-eligible.
