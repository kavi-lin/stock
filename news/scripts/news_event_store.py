#!/usr/bin/env python3
"""Append-only News event store and deterministic daily digest projection.

The JSONL file is the source of truth.  ``*_digest.json`` remains a projection
so Dashboard and existing readers do not need a contract change.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from news.arbiter_rules import ARBITER_RULE_VERSION, classify_verdict, compute_net_impact, directional_bias

DEFAULT_STORE = Path("news/news_logs/news_events.jsonl")
BACKUP_DIR = Path("news/news_logs/legacy_digest_backup")
SCHEMA_VERSION = 1
EVENT_TYPES = {"DIGEST", "FLASH", "REVIEW", "LINK_DIGEST", "TELEMETRY"}
# Shallow verdicts kept in the daily projection. Must stay at the protocol's
# soft target (news_protocol_v2.md Phase 4: top 10 by materiality_score), not at
# validate_digest_output.py's hard ceiling of 15 — the ceiling is the gate, this
# is the target the gate checks against.
SHALLOW_PROJECTION_CAP = 10


class EventStoreError(ValueError):
    pass


def _validate_date(value: str) -> str:
    try:
        parsed = datetime.strptime(str(value), "%Y-%m-%d")
    except ValueError as exc:
        raise EventStoreError(f"date must be YYYY-MM-DD: {value!r}") from exc
    normalized = parsed.strftime("%Y-%m-%d")
    if normalized != str(value):
        raise EventStoreError(f"date must be YYYY-MM-DD: {value!r}")
    return normalized


def _canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_event_id(verdict: dict, *, date: str = "") -> str:
    existing = str(verdict.get("event_id") or "").strip()
    if existing.startswith("news_"):
        return existing
    url = str(verdict.get("source_url") or verdict.get("url") or "").strip()
    if url:
        parts = urlsplit(url)
        identity = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))
    else:
        headline = " ".join(str(verdict.get("headline") or "").lower().split())
        identity = f"{date}|{headline}" if headline else f"{date}|{verdict.get('news_id', '')}"
    return "news_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def _record_id(event_type: str, event_id: str, payload: dict, *, effective_date: str = "") -> str:
    # Exclude volatile projection timestamps. A deterministic replay of the
    # same judgment must not append another physical record.
    body = {k: v for k, v in payload.items() if k not in {"timestamp", "updated_at"}}
    raw = _canonical_json({
        "event_type": event_type, "event_id": event_id,
        "effective_date": effective_date, "payload": body,
    })
    return "nev_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


@contextmanager
def _locked(store_path: Path):
    lock_path = store_path.with_suffix(store_path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def load_events(store_path: Path) -> list[dict]:
    if not store_path.exists():
        return []
    events = []
    for lineno, line in enumerate(store_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EventStoreError(f"{store_path}:{lineno}: invalid JSON: {exc}") from exc
        if not isinstance(event, dict):
            raise EventStoreError(f"{store_path}:{lineno}: event must be an object")
        if event.get("schema_version") != SCHEMA_VERSION:
            raise EventStoreError(f"{store_path}:{lineno}: unsupported schema_version")
        if event.get("event_type") not in EVENT_TYPES:
            raise EventStoreError(f"{store_path}:{lineno}: invalid event_type")
        if not str(event.get("event_id") or "").startswith("news_"):
            raise EventStoreError(f"{store_path}:{lineno}: invalid event_id")
        events.append(event)
    return events


def append_records(store_path: Path, records: list[dict]) -> list[dict]:
    """Append unseen record_ids under an exclusive lock; never rewrite JSONL."""
    if not records:
        return []
    store_path.parent.mkdir(parents=True, exist_ok=True)
    with _locked(store_path):
        existing_ids = {x.get("record_id") for x in load_events(store_path)}
        appended = []
        with store_path.open("a", encoding="utf-8") as fp:
            for record in records:
                if record["record_id"] in existing_ids:
                    continue
                fp.write(_canonical_json(record) + "\n")
                existing_ids.add(record["record_id"])
                appended.append(record)
            fp.flush()
            os.fsync(fp.fileno())
    return appended


def _make_record(
    event_type: str,
    date: str,
    verdict: dict,
    *,
    recorded_at: str,
    projection_meta: dict,
    position: int,
    origin: str,
    supersedes_record_id: str | None = None,
) -> dict:
    if event_type not in EVENT_TYPES:
        raise EventStoreError(f"unsupported event_type: {event_type}")
    payload = dict(verdict)
    event_id = stable_event_id(payload, date=date)
    payload["event_id"] = event_id
    record = {
        "schema_version": SCHEMA_VERSION,
        "record_id": _record_id(event_type, event_id, payload, effective_date=date),
        "event_id": event_id,
        "event_type": event_type,
        "effective_date": date,
        "recorded_at": recorded_at,
        "origin": origin,
        "position": position,
        "projection_meta": projection_meta,
        "payload": payload,
    }
    if supersedes_record_id:
        record["supersedes_record_id"] = supersedes_record_id
    return record


def normalize_deep_verdict(verdict: dict, *, event_type: str) -> dict:
    """Own FLASH/REVIEW arithmetic so LLM payloads cannot drift from V2.3."""
    payload = dict(verdict)
    if payload.get("depth", "deep") != "deep":
        return payload
    lane_scores = payload.get("lane_scores")
    if event_type == "LINK_DIGEST" and not isinstance(lane_scores, dict):
        payload.update({
            "depth": "deep", "review_status": "reviewed", "cache_updated": False,
            "subagent_isolated": False,
        })
        return payload
    if not isinstance(lane_scores, dict):
        raise EventStoreError("deep payload requires lane_scores")
    try:
        score, weights = compute_net_impact(
            lane_scores,
            payload.get("news_type"),
            payload.get("source_credibility", "MEDIUM"),
            payload.get("fanout_mode", "INLINE"),
        )
    except (TypeError, ValueError) as exc:
        raise EventStoreError(f"invalid lane_scores: {exc}") from exc
    binary = payload.get("binary_risk") is True
    if binary and not payload.get("binary_event_date"):
        raise EventStoreError("binary event requires binary_event_date")
    payload.update({
        "depth": "deep",
        "review_status": "pending" if event_type == "FLASH" else "reviewed",
        "cache_updated": event_type != "FLASH",
        "net_impact_score": score,
        "weights_used": weights,
        "verdict": classify_verdict(score, binary),
        "directional_bias": directional_bias(score),
        "subagent_isolated": bool(payload.get("subagent_isolated", False)),
    })
    required_text = (
        "headline", "headline_zh", "source_label", "news_type", "published",
        "bull_case", "bear_case", "sector_view", "macro_view",
        "arbiter_reasoning", "debate_note",
    )
    missing = [key for key in required_text if not str(payload.get(key) or "").strip()]
    if missing:
        raise EventStoreError(f"deep payload missing text fields: {missing}")
    if len(str(payload["arbiter_reasoning"]).strip()) < 30:
        raise EventStoreError("arbiter_reasoning must be at least 30 characters")
    try:
        datetime.fromisoformat(str(payload["published"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise EventStoreError("published must be ISO-8601") from exc
    confidences = payload.get("lane_confidences")
    lanes = ("bull", "bear", "sector", "macro")
    if not isinstance(confidences, dict) or any(lane not in confidences for lane in lanes):
        raise EventStoreError("deep payload requires four lane_confidences")
    for lane in lanes:
        value = confidences[lane]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise EventStoreError(f"lane_confidences.{lane} must be within 0..1")
        if payload.get("source_credibility") == "LOW" and value > 0.5:
            raise EventStoreError(f"LOW source lane_confidences.{lane} exceeds 0.5")
    if not isinstance(payload.get("affected_sectors"), list):
        raise EventStoreError("affected_sectors must be an array")
    if not isinstance(payload.get("tickers_mentioned"), list):
        raise EventStoreError("tickers_mentioned must be an array")
    if type(payload.get("binary_risk")) is not bool or type(payload.get("within_48h")) is not bool:
        raise EventStoreError("binary_risk and within_48h must be booleans")
    macro_delta = payload.get("macro_backdrop_delta", 0.0)
    if isinstance(macro_delta, bool) or not isinstance(macro_delta, (int, float)):
        raise EventStoreError("macro_backdrop_delta must be numeric")
    return payload


def records_from_digest(data: dict, *, date: str, origin: str = "digest_finalizer") -> list[dict]:
    mode = str(data.get("mode") or "DIGEST").upper()
    event_type = mode if mode in EVENT_TYPES else "DIGEST"
    recorded_at = str(data.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M"))
    meta = {k: v for k, v in data.items() if k != "verdicts"}
    records = []
    for position, verdict in enumerate(data.get("verdicts") or []):
        if not isinstance(verdict, dict):
            continue
        verdict = dict(verdict)
        projected_type = verdict.pop("event_type", None)
        verdict_type = projected_type if projected_type in EVENT_TYPES else event_type
        if verdict.get("review_status") == "pending":
            verdict_type = "FLASH"
        elif verdict.get("origin") == "link_digest":
            verdict_type = "LINK_DIGEST"
        records.append(_make_record(
            verdict_type, date, verdict, recorded_at=recorded_at,
            projection_meta=meta, position=position, origin=origin,
        ))
    return records


def latest_by_event_id(events: list[dict], date: str) -> list[dict]:
    latest: dict[str, tuple[int, dict]] = {}
    for index, event in enumerate(events):
        if event.get("effective_date") == date and event.get("event_type") != "TELEMETRY":
            latest[event["event_id"]] = (index, event)
    # Keep the source batch order stable; later REVIEW records retain the
    # original event's slot through append_review().
    return [x[1] for x in sorted(latest.values(), key=lambda pair: (pair[1].get("position", 0), pair[0]))]


def _shallow_rank(verdict: dict) -> float:
    """Selection key for the shallow top-N cut. `materiality_score` is the
    protocol's ranking field (news_protocol_v2.md Phase 4); legacy rows written
    before it existed fall back to |shallow_score|, which the digest carries as
    `net_impact_score`."""
    score = verdict.get("materiality_score")
    if isinstance(score, (int, float)):
        return float(score)
    return abs(float(verdict.get("net_impact_score") or 0.0))


def _cap_shallow(verdicts: list[dict]) -> list[dict]:
    """Keep only the top SHALLOW_PROJECTION_CAP shallow verdicts, deep untouched.

    build_digest_packet.py caps shallow at 10 *per run*, but the projection is a
    union of every event recorded for the date (latest_by_event_id dedups by
    event_id, not by run). On a day with more than one news run each run
    contributes its own top-10 — picked from a triage snapshot that moved during
    the day, so the event_ids differ and the union exceeds the cap. 2026-08-06:
    3 runs → 20 distinct shallow → validate_digest_output rc=1 (>15) → premarket
    chain phase 1 failed and sector never ran. Deep is deliberately NOT capped:
    intraday FLASH/REVIEW accumulating across the day is by design.

    Order is preserved (the surviving rows keep their projection slots) so the
    cut only removes rows and never reshuffles; ties break on that same slot,
    which keeps the projection deterministic for a given store.
    """
    shallow_idx = [i for i, v in enumerate(verdicts) if v.get("depth") == "shallow"]
    if len(shallow_idx) <= SHALLOW_PROJECTION_CAP:
        return verdicts
    keep = set(sorted(
        shallow_idx,
        key=lambda i: (-_shallow_rank(verdicts[i]), i),
    )[:SHALLOW_PROJECTION_CAP])
    return [v for i, v in enumerate(verdicts) if v.get("depth") != "shallow" or i in keep]


def build_projection(events: list[dict], date: str) -> dict:
    active = latest_by_event_id(events, date)
    if not active:
        raise EventStoreError(f"no events for {date}")
    record_order = {x.get("record_id"): i for i, x in enumerate(events)}
    digest_events = [x for x in active if x["event_type"] == "DIGEST"]
    base_pool = digest_events or active
    anchor = max(base_pool, key=lambda x: record_order.get(x.get("record_id"), -1))
    activity_anchor = max(active, key=lambda x: record_order.get(x.get("record_id"), -1))
    meta = dict(anchor.get("projection_meta") or {})
    activity_meta = activity_anchor.get("projection_meta") or {}
    verdicts = []
    for event in active:
        verdict = dict(event["payload"])
        verdict["event_type"] = event["event_type"]
        verdicts.append(verdict)
    verdicts = _cap_shallow(verdicts)
    deep_count = sum(v.get("depth") == "deep" for v in verdicts)
    shallow_count = sum(v.get("depth") == "shallow" for v in verdicts)
    mode = "DIGEST" if digest_events else str(anchor.get("event_type") or "FLASH")
    if mode == "LINK_DIGEST":
        mode = "REVIEW"
    data = {
        **meta,
        "timestamp": str(activity_meta.get("timestamp") or activity_anchor.get("recorded_at")),
        "mode": mode,
        "stage1_count": int(meta.get("stage1_count", shallow_count + deep_count)),
        "stage2_count": deep_count,
        "fanout_mode": meta.get("fanout_mode") or "INLINE",
        "degraded_agents": meta.get("degraded_agents") or [],
        "verdicts": verdicts,
        "session_macro_delta": meta.get("session_macro_delta", 0.0),
        "event_projection_version": SCHEMA_VERSION,
        "projection_date": date,
    }
    return data


def project_date(store_path: Path, date: str, *, root: Path = ROOT) -> dict:
    date = _validate_date(date)
    data = build_projection(load_events(store_path), date)
    out = root / f"news/news_logs/{date}_digest.json"
    _atomic_json(out, data)
    return data


def ingest_digest(
    data: dict,
    *,
    date: str,
    root: Path = ROOT,
    store_path: Path | None = None,
    origin: str = "digest_finalizer",
) -> dict:
    date = _validate_date(date)
    store = store_path or root / DEFAULT_STORE
    records = records_from_digest(data, date=date, origin=origin)
    appended = append_records(store, records)
    projected = project_date(store, date, root=root)
    return {"appended": len(appended), "records": appended, "projection": projected, "store": str(store)}


def append_verdict(
    verdict: dict,
    *,
    event_type: str,
    date: str,
    root: Path = ROOT,
    store_path: Path | None = None,
    projection_meta: dict | None = None,
    origin: str = "protocol_cli",
) -> dict:
    date = _validate_date(date)
    store = store_path or root / DEFAULT_STORE
    verdict = normalize_deep_verdict(verdict, event_type=event_type)
    if not verdict.get("news_id"):
        verdict["news_id"] = "n" + stable_event_id(verdict, date=date)[5:9]
    existing = latest_by_event_id(load_events(store), date)
    position = max((int(x.get("position", 0)) for x in existing), default=-1) + 1
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    meta = dict(projection_meta or {})
    meta.setdefault("timestamp", now)
    meta.setdefault("arbiter_rule_version", ARBITER_RULE_VERSION)
    record = _make_record(
        event_type, date, verdict, recorded_at=now, projection_meta=meta,
        position=position, origin=origin,
    )
    appended = append_records(store, [record])
    return {"appended": len(appended), "record": record, "projection": project_date(store, date, root=root)}


def append_review(
    event_id: str,
    verdict: dict,
    *,
    root: Path = ROOT,
    store_path: Path | None = None,
    origin: str = "review_protocol",
) -> dict:
    store = store_path or root / DEFAULT_STORE
    events = load_events(store)
    matches = [(i, x) for i, x in enumerate(events) if x.get("event_id") == event_id]
    if not matches:
        raise EventStoreError(f"event_id not found: {event_id}")
    prior = matches[-1][1]
    prior_payload = prior.get("payload") or {}
    if prior_payload.get("review_status") != "pending":
        raise EventStoreError(f"event_id is not pending: {event_id}")
    raw_payload = dict(verdict)
    for key in ("news_id", "published", "source_url", "source_label", "headline"):
        if not raw_payload.get(key) and prior_payload.get(key):
            raw_payload[key] = prior_payload[key]
    payload = normalize_deep_verdict(raw_payload, event_type="REVIEW")
    payload["event_id"] = event_id
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    meta = dict(prior.get("projection_meta") or {})
    meta["timestamp"] = now
    meta["arbiter_rule_version"] = ARBITER_RULE_VERSION
    record = _make_record(
        "REVIEW", prior["effective_date"], payload, recorded_at=now,
        projection_meta=meta, position=int(prior.get("position", 0)), origin=origin,
        supersedes_record_id=prior.get("record_id"),
    )
    appended = append_records(store, [record])
    projection = project_date(store, prior["effective_date"], root=root)
    from news.scripts.news_cache_projection import patch_news_caches
    cache = patch_news_caches(projection, root)
    return {
        "appended": len(appended), "record": record,
        "projection": projection, "cache": cache,
    }


def pending_events(store_path: Path, headline: str | None = None) -> list[dict]:
    events = load_events(store_path)
    latest = {}
    for event in events:
        if event.get("event_type") != "TELEMETRY":
            latest[event["event_id"]] = event
    active = list(latest.values())
    pending = [x for x in active if (x.get("payload") or {}).get("review_status") == "pending"]
    if headline:
        needle = " ".join(headline.lower().split())
        pending = [
            x for x in pending
            if " ".join(str((x.get("payload") or {}).get("headline") or "").lower().split()) == needle
        ]
    return [{
        "event_id": x["event_id"],
        "effective_date": x["effective_date"],
        "headline": (x.get("payload") or {}).get("headline"),
        "news_id": (x.get("payload") or {}).get("news_id"),
    } for x in pending]


def append_run_telemetry(
    store_path: Path,
    *,
    run_id: str,
    date: str,
    payload: dict,
    recorded_at: str | None = None,
) -> dict:
    date = _validate_date(date)
    store_path = Path(store_path)
    event_id = "news_run_" + hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:16]
    body = dict(payload)
    body["run_id"] = run_id
    record = {
        "schema_version": SCHEMA_VERSION,
        "record_id": _record_id("TELEMETRY", event_id, body, effective_date=date),
        "event_id": event_id,
        "event_type": "TELEMETRY",
        "effective_date": date,
        "recorded_at": recorded_at or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "origin": "dashboard_protocol_runner",
        "position": 0,
        "projection_meta": {},
        "payload": body,
    }
    return {"appended": len(append_records(store_path, [record])), "record": record}


def telemetry_summary(store_path: Path, limit: int = 10) -> dict:
    rows = [x.get("payload") or {} for x in load_events(store_path) if x.get("event_type") == "TELEMETRY"][-limit:]
    n = len(rows)
    return {
        "runs": n,
        "stage2_average": round(sum(float(x.get("stage2_count", 0) or 0) for x in rows) / n, 2) if n else None,
        "binary_rate": round(sum(float(x.get("binary_count", 0) or 0) for x in rows) / max(1, sum(float(x.get("stage2_count", 0) or 0) for x in rows)), 4) if n else None,
        "input_tokens": sum(int(x.get("input_tokens", 0) or 0) for x in rows),
        "output_tokens": sum(int(x.get("output_tokens", 0) or 0) for x in rows),
        "elapsed_sec": sum(int(x.get("elapsed_sec", 0) or 0) for x in rows),
        "cost_usd": round(sum(float(x.get("cost_usd", 0) or 0) for x in rows), 6),
        "rows": rows,
    }


def migrate_digest(path: Path, *, root: Path = ROOT, store_path: Path | None = None, backup: bool = True) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    date = _validate_date(path.name[:10])
    if backup:
        backup_path = root / BACKUP_DIR / path.name
        if not backup_path.exists():
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup_path)
    result = ingest_digest(data, date=date, root=root, store_path=store_path, origin="legacy_migration")
    return {"date": date, "appended": result["appended"], "projected": str(root / f"news/news_logs/{date}_digest.json")}


def rollback(date: str, *, root: Path = ROOT) -> Path:
    date = _validate_date(date)
    backup = root / BACKUP_DIR / f"{date}_digest.json"
    if not backup.exists():
        raise EventStoreError(f"legacy backup not found: {backup}")
    target = root / f"news/news_logs/{date}_digest.json"
    _atomic_json(target, json.loads(backup.read_text(encoding="utf-8")))
    return target


def _read_payload(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise EventStoreError("payload must be a JSON object")
    return data


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--store")
    sub = parser.add_subparsers(dest="command", required=True)
    p_append = sub.add_parser("append")
    p_append.add_argument("--mode", choices=("FLASH", "LINK_DIGEST"), required=True)
    p_append.add_argument("--date", required=True)
    p_append.add_argument("--payload", required=True)
    p_review = sub.add_parser("review")
    p_review.add_argument("--event-id", required=True)
    p_review.add_argument("--payload", required=True)
    p_project = sub.add_parser("project")
    p_project.add_argument("--date", required=True)
    p_pending = sub.add_parser("pending")
    p_pending.add_argument("--headline")
    p_telemetry = sub.add_parser("telemetry")
    p_telemetry.add_argument("--limit", type=int, default=10)
    p_telemetry_add = sub.add_parser("telemetry-add")
    p_telemetry_add.add_argument("--run-id", required=True)
    p_telemetry_add.add_argument("--date", required=True)
    p_telemetry_add.add_argument("--payload", required=True)
    p_migrate = sub.add_parser("migrate")
    migrate_source = p_migrate.add_mutually_exclusive_group(required=True)
    migrate_source.add_argument("--path")
    migrate_source.add_argument("--all", action="store_true")
    p_rollback = sub.add_parser("rollback")
    p_rollback.add_argument("--date", required=True)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    store = Path(args.store).resolve() if args.store else root / DEFAULT_STORE
    try:
        if args.command == "append":
            result = append_verdict(_read_payload(args.payload), event_type=args.mode, date=args.date, root=root, store_path=store)
        elif args.command == "review":
            result = append_review(args.event_id, _read_payload(args.payload), root=root, store_path=store)
        elif args.command == "project":
            result = project_date(store, args.date, root=root)
        elif args.command == "pending":
            result = pending_events(store, args.headline)
        elif args.command == "telemetry":
            result = telemetry_summary(store, args.limit)
        elif args.command == "telemetry-add":
            result = append_run_telemetry(
                store, run_id=args.run_id, date=args.date,
                payload=_read_payload(args.payload),
            )
        elif args.command == "migrate":
            paths = sorted((root / "news/news_logs").glob("*_digest.json")) if args.all else [Path(args.path)]
            result = [migrate_digest(p.resolve(), root=root, store_path=store) for p in paths]
        else:
            result = {"restored": str(rollback(args.date, root=root))}
    except (OSError, json.JSONDecodeError, EventStoreError) as exc:
        print(f"[news_event_store] ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
