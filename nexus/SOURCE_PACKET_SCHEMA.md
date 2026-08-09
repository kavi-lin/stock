# Nexus Source Packet Schema v1

`Dashboard/nexus_source_packets.json` is the deterministic evidence boundary
between evidence drafts and any later text-only LLM gap-fill pass.

```bash
python3 -m scripts.nexus.source_packets
python3 -m scripts.nexus.source_packets --fetch-topic topic:advanced_packaging
python3 -m scripts.nexus.source_packets --check
```

The default build performs no network access. It combines canonical URLs and
claim-ledger extracts. `--fetch-topic` deterministically retrieves only that
topic's sources and stores short relevant page passages, never the full page.

## Evidence honesty

- `claim_analyst_extract` is a locally stored analyst/agent extract. It is not
  labelled as a verbatim quotation.
- `fetched_page` is text extracted directly from the retrieved HTML and has
  `verbatim_page_text: true`.
- every excerpt has a content hash and stable `excerpt_id`;
- every source has a stable ID derived from its canonical URL;
- the full normalized fetched page is represented only by `content_digest`.

## Relation-level evidence

Each immutable edge has its own citations and independently derived tier:

- `corroborated_claim`: at least two cited URLs across two domains;
- `single_source_claim`: one cited URL or one source family;
- `unsupported`: no claim-level source citation in the packet.

An overall packet with many domains cannot promote an unrelated edge. This is
the key difference from the earlier whole-response domain count.

## Boundaries

- `artifact_class: exploration_only`
- `decision_use: forbidden`
- packet `base_draft_digest` must match the immutable evidence draft
- a later model may cite only packet `source_id` / `excerpt_id`
- unknown or unsupported gaps remain unresolved
