# Nexus Claim Ledger Schema v1

`nexus/claim_ledger.jsonl` is a deterministic, generated evidence ledger for
ticker-to-ticker structural relationships. It is rebuilt from closed Break News
and Link Digest artifacts by `scripts/nexus/claim_ledger.py`; do not hand-edit
it. The ledger is part of the **exploration layer** and never changes an
investment verdict, buy threshold, or position size.

## Record

Each JSONL row is one canonical relationship claim:

```json
{
  "schema_version": 1,
  "claim_id": "claim:<stable hash of canonical triple>",
  "subject": "ticker:TSM",
  "predicate": "SUPPLIES_TO",
  "object": "ticker:NVDA",
  "status": "provisional | corroborated",
  "confidence": 0.84,
  "first_seen": "2026-07-01",
  "last_seen": "2026-08-08",
  "source_count": 4,
  "source_domain_count": 3,
  "source_domains": ["reuters.com"],
  "agent_support_max": 2,
  "artifacts": ["break_news:bn_..."],
  "evidence": [
    {
      "source_key": "url:<sha1>",
      "url": "https://...",
      "domain": "reuters.com",
      "published": "2026-08-08",
      "artifacts": ["break_news:bn_..."],
      "headline": "...",
      "confidence": 0.84,
      "evidence_snippets": ["..."]
    }
  ]
}
```

## Canonical relationship rules

- Entities must be `ticker:<UPPERCASE SYMBOL>`.
- `CUSTOMER_OF A→B` normalizes to `SUPPLIES_TO B→A`.
- Symmetric `COMPETES_WITH` and `CO_DEVELOPS_WITH` endpoints are sorted so the
  same relationship cannot exist in two orientations.
- Allowed v1 predicates are `SUPPLIES_TO`, `CONTRACT_MFG_FOR`,
  `COMPETES_WITH`, and `CO_DEVELOPS_WITH`.
- URL identity strips fragments and common tracking parameters. Repeated
  artifacts carrying the same canonical URL remain one evidence source.

## Promotion gate

`corroborated` requires all of:

1. at least two distinct canonical source URLs;
2. at least two distinct source domains;
3. average evidence confidence at least 0.65.

`agent_support_max` is retained for audit but never satisfies the independent
source gate. Two analysts agreeing about one article is still one source.

The word `corroborated` does **not** mean a legally confirmed commercial
contract. It only means the exploration graph has source diversity sufficient
to render a provisional structural edge.

## Generated outputs and validation

- Ledger: `nexus/claim_ledger.jsonl`
- Quality summary: `Dashboard/nexus_quality.json`
- Graph projection: corroborated records whose two tickers belong to the Nexus
  universe become directed edges in `Dashboard/nexus_graph.json`.

Commands:

```bash
python3 -m scripts.nexus.claim_ledger
python3 -m scripts.nexus.claim_ledger --check
python3 scripts/nexus/build_graph.py --tier 1,2 --dry-run
```

The validator checks canonical triples, unique claim IDs and evidence keys,
derived source/domain counts, and exact promotion status. Validation failure is
fatal to the Nexus build; an old graph must not be silently presented as a new
claim-ledger build.
