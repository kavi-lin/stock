# News Event Store Schema V1

`news/news_logs/news_events.jsonl` is the append-only source of truth for News
judgments. `YYYY-MM-DD_digest.json` is a deterministic projection retained for
Dashboard and legacy readers.

## Record envelope

Each physical line is one complete JSON object:

```json
{
  "schema_version": 1,
  "record_id": "nev_<24 hex>",
  "event_id": "news_<stable id>",
  "event_type": "DIGEST|FLASH|REVIEW|LINK_DIGEST|TELEMETRY",
  "effective_date": "YYYY-MM-DD",
  "recorded_at": "ISO or YYYY-MM-DD HH:MM",
  "origin": "digest_finalizer|protocol_cli|legacy_migration|...",
  "position": 0,
  "projection_meta": {},
  "payload": {}
}
```

- `record_id` identifies an immutable physical record. It is a deterministic
  hash of event type, stable event ID, and non-volatile payload.
- `event_id` identifies the underlying news item. URL identity ignores query
  parameters; headline/date is the fallback.
- A REVIEW record keeps the same `event_id` and adds
  `supersedes_record_id`. It never rewrites the FLASH record.
- Replaying an identical producer payload appends zero records.
- TELEMETRY records are stored in the same log but excluded from digest
  projection.

## Projection

For one `effective_date`, scan records in file order and keep the latest record
for every `event_id`. Order the active records by their stable `position`, then
write the existing digest contract plus:

```json
{
  "event_projection_version": 1,
  "projection_date": "YYYY-MM-DD"
}
```

Each projected verdict also carries additive `event_id` and `event_type`
fields. Existing Dashboard fields are unchanged.

The News validator rebuilds the projection in memory and requires exact object
equality with the on-disk digest.

## Commands

```bash
# FLASH: payload contains prose + lane_scores/lane_confidences; script owns math
python3 news/scripts/news_event_store.py append \
  --mode FLASH --date YYYY-MM-DD --payload payload.json

# Locate pending events, then REVIEW by stable identity
python3 news/scripts/news_event_store.py pending --headline "..."
python3 news/scripts/news_event_store.py review \
  --event-id news_... --payload review.json

# Rebuild projection without LLM
python3 news/scripts/news_event_store.py project --date YYYY-MM-DD

# Migrate one or all legacy digests; backups are created once
python3 news/scripts/news_event_store.py migrate --path news/news_logs/YYYY-MM-DD_digest.json
python3 news/scripts/news_event_store.py migrate --all

# Restore the pre-migration digest while preserving the JSONL audit trail
python3 news/scripts/news_event_store.py rollback --date YYYY-MM-DD

# Last ten DIGEST telemetry records
python3 news/scripts/news_event_store.py telemetry --limit 10
```

Backups live under `news/news_logs/legacy_digest_backup/`. Rollback does not
delete event records; a later `project` command can safely re-enable the
projection.

## Telemetry

Successful server-triggered DIGEST runs append one TELEMETRY record containing:

- Stage 2 count and BINARY count
- source and `content_genre` distributions
- input/output/cache tokens
- elapsed seconds and reported cost

Keep `materiality threshold = 4.5` until at least ten records exist.
