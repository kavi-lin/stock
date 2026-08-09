# Nexus Topic Discovery Schema v1

`Dashboard/nexus_topics.json` is rebuilt on every Tier-1 Nexus build. It turns
the themes and technology keywords already extracted from closed Break News
items into an evidence-ranked topic queue, so supply-chain exploration does not
depend on the user thinking of a theme first.

The builder is deterministic and uses zero LLM calls:

```bash
python3 -m scripts.nexus.topic_discovery
python3 -m scripts.nexus.topic_discovery --check
```

## State gate

- `seed`: one source, one domain, or score below the emerging threshold.
- `emerging`: at least two source URLs across two domains and score ≥20.
- `validated`: at least three source URLs across two domains and score ≥35.
- `decaying`: last evidence is more than 14 days old.

This satisfies the Nexus rule that a newly discovered concept needs at least
three independent documents before promotion. State is exploration metadata;
it does not affect investment scores or verdicts.

## Topic score

The 0–100 score combines source count, source-domain diversity, ticker breadth,
structural relation count, seven-day source velocity versus the earlier window,
bottleneck vocabulary, and topic novelty. Every topic carries the raw component
metrics and a deterministic `why_now` list, so the UI never presents an opaque
model score.

## `chain_candidates`

The top-level `chain_candidates` projection is the actionable subset used by
the Nexus Radar. A candidate must:

1. be `emerging` or `validated`;
2. have at least three source URLs across at least two domains;
3. span at least two tickers;
4. contain a directional supply relation; and
5. contain either supply-chain-specific topic vocabulary or explicit bottleneck
language.

`draft_candidates` is a separate top-20 projection sorted by topic score first
(velocity and source count break ties). It is selected from the complete
uncovered candidate set before the UI-oriented `new_chain_candidates` list is
truncated, so evidence-draft generation cannot mistake a display slice for the
highest-score candidates.

The stricter fifth rule prevents broad labels such as “market rotation” or
“earnings momentum” from becoming supply-chain drafts merely because the same
news item happened to contain a company relationship.

## Important fields

- `topic_id`, `label`, `state`, `score`
- `first_seen`, `last_seen`, `recent_7d_source_count`, `velocity_ratio`
- `source_count`, `source_domain_count`, `evidence[]`
- `tickers[]`, `ticker_count`
- `structural_relation_count`, `supply_relation_count`, `top_relations[]`
- `bottleneck_terms[]`, `supply_topic_hint`, `why_now[]`

`top_relations` always projects directional supply predicates before symmetric
competition/co-development context. A chain candidate must not lose its only
flow edge merely because higher-frequency competition pairs fill the display
cap.

The validator enforces unique IDs and evidence keys, promotion thresholds, and
the extra chain-candidate gates. A failed validator aborts the Nexus refresh
instead of silently publishing an apparently empty or stale Radar.
