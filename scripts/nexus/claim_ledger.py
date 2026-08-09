#!/usr/bin/env python3
"""Deterministic evidence ledger for Nexus ticker relationships.

The old Nexus direct-edge path counted analyst agreement inside one Break News
thread as if it were independent evidence.  This module instead rebuilds a
claim-centric ledger from source URLs.  A relationship becomes graph-eligible
only when at least two distinct URLs on at least two domains support the same
canonical triple.

This remains an exploration-layer artifact.  ``corroborated`` means the
relationship cleared the source-diversity gate; it does not mean an investment
decision or a legally verified customer contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .schema import Edge, Node, NodeType


SCHEMA_VERSION = 1
TICKER_RELATIONS = {
    "SUPPLIES_TO",
    "CONTRACT_MFG_FOR",
    "COMPETES_WITH",
    "CO_DEVELOPS_WITH",
}
TRACKING_QUERY_KEYS = {
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "src", "source",
    "utm_campaign", "utm_content", "utm_medium", "utm_source", "utm_term",
    "yptr",
}
ENTITY_RE = re.compile(r"^ticker:([A-Z][A-Z0-9.\-]{0,14})$")


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def canonical_url(raw: str) -> str:
    """Return a stable URL fingerprint input without common tracking noise."""
    raw = str(raw or "").strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
    except ValueError:
        return ""
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return ""
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query = urlencode(sorted(
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in TRACKING_QUERY_KEYS
    ))
    return urlunsplit(("https", host, path, query, ""))


def source_domain(url: str) -> str:
    try:
        return urlsplit(url).netloc.lower()
    except ValueError:
        return ""


def canonical_entity(raw: str) -> str | None:
    raw = str(raw or "").strip()
    if not raw.lower().startswith("ticker:"):
        return None
    symbol = raw.split(":", 1)[1].strip().upper()
    entity = f"ticker:{symbol}"
    return entity if ENTITY_RE.match(entity) else None


def canonical_triple(subject: str, predicate: str, obj: str) -> tuple[str, str, str] | None:
    subj = canonical_entity(subject)
    target = canonical_entity(obj)
    pred = str(predicate or "").strip().upper()
    if not subj or not target or subj == target:
        return None
    if pred == "CUSTOMER_OF":
        subj, target, pred = target, subj, "SUPPLIES_TO"
    if pred not in TICKER_RELATIONS:
        return None
    if pred in {"COMPETES_WITH", "CO_DEVELOPS_WITH"} and target < subj:
        subj, target = target, subj
    return subj, pred, target


def _date_part(raw: Any) -> str | None:
    text = str(raw or "")[:10]
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return None


def _float(raw: Any, default: float = 0.0) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _source_urls(rel: dict[str, Any], source: dict[str, Any]) -> list[str]:
    explicit = rel.get("corroborating_sources")
    urls: list[str] = []
    if isinstance(explicit, list):
        urls.extend(str(x) for x in explicit)
    # Normal Break News relations do not carry relation-level URLs.  In that
    # case the article itself is the sole evidence item.  For link digests the
    # explicit list is authoritative and already identifies which fetched
    # pages affirmed the relationship.
    if not urls:
        urls.append(str(source.get("url") or ""))
    out, seen = [], set()
    for raw in urls:
        url = canonical_url(raw)
        if url and url not in seen:
            seen.add(url)
            out.append(url)
    return out


def build_records(
    break_news_dir: Path,
    *,
    since_days: int = 45,
    anchor_date: datetime | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build canonical claims and a quality summary from Break News artifacts."""
    anchor = anchor_date or datetime.now(timezone.utc)
    cutoff = anchor.date() - timedelta(days=since_days)
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    counters: Counter[str] = Counter()

    for path in sorted(break_news_dir.glob("bn_*.json")):
        counters["artifacts_scanned"] += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            counters["artifacts_unreadable"] += 1
            continue
        if data.get("state") not in ("closed", "partial_closed"):
            counters["artifacts_not_closed"] += 1
            continue
        observed = _date_part(data.get("fetched_at"))
        if not observed or datetime.fromisoformat(observed).date() < cutoff:
            counters["artifacts_outside_window"] += 1
            continue
        counters["artifacts_eligible"] += 1
        source = data.get("source") if isinstance(data.get("source"), dict) else {}
        relations = (data.get("summary") or {}).get("merged_relations") or []
        for rel in relations:
            counters["relations_seen"] += 1
            if not isinstance(rel, dict):
                counters["relations_malformed"] += 1
                continue
            triple = canonical_triple(
                rel.get("subject"), rel.get("predicate"), rel.get("object")
            )
            if not triple:
                counters["relations_not_ticker_structural"] += 1
                continue
            urls = _source_urls(rel, source)
            if not urls:
                counters["relations_without_source_url"] += 1
                continue
            counters["relations_normalized"] += 1
            slot = groups.setdefault(triple, {
                "observed_dates": set(),
                "artifacts": set(),
                "evidence": {},
                "agent_support_max": 0,
                "confidence_values": [],
            })
            slot["observed_dates"].add(observed)
            slot["artifacts"].add(f"break_news:{data.get('news_id') or path.stem}")
            try:
                agent_support = int(rel.get("support_count") or 1)
            except (TypeError, ValueError):
                agent_support = 1
            slot["agent_support_max"] = max(slot["agent_support_max"], agent_support)
            confidence = max(0.0, min(1.0, _float(rel.get("confidence_avg"), 0.5)))
            slot["confidence_values"].append(confidence)
            snippets = [str(x)[:240] for x in (rel.get("evidence_snippets") or []) if str(x).strip()]
            for url in urls:
                key = _sha1(url)
                evidence = slot["evidence"].setdefault(key, {
                    "source_key": f"url:{key}",
                    "url": url,
                    "domain": source_domain(url),
                    "published": _date_part(source.get("published")) or observed,
                    "artifacts": set(),
                    "headline": str(data.get("headline") or "")[:180],
                    "confidence": confidence,
                    "evidence_snippets": [],
                })
                evidence["artifacts"].add(f"break_news:{data.get('news_id') or path.stem}")
                evidence["confidence"] = max(evidence["confidence"], confidence)
                for snippet in snippets:
                    if snippet not in evidence["evidence_snippets"] and len(evidence["evidence_snippets"]) < 3:
                        evidence["evidence_snippets"].append(snippet)

    records: list[dict[str, Any]] = []
    for (subject, predicate, obj), slot in sorted(groups.items()):
        evidence_rows = []
        for evidence in slot["evidence"].values():
            evidence_rows.append({
                **evidence,
                "artifacts": sorted(evidence["artifacts"]),
            })
        evidence_rows.sort(key=lambda x: (x["published"], x["source_key"]), reverse=True)
        domains = sorted({e["domain"] for e in evidence_rows if e["domain"]})
        source_count = len(evidence_rows)
        domain_count = len(domains)
        confidence = round(
            sum(e["confidence"] for e in evidence_rows) / max(source_count, 1), 4
        )
        status = (
            "corroborated"
            if source_count >= 2 and domain_count >= 2 and confidence >= 0.65
            else "provisional"
        )
        normalized = f"{subject}|{predicate}|{obj}"
        record = {
            "schema_version": SCHEMA_VERSION,
            "claim_id": f"claim:{_sha1(normalized)[:16]}",
            "subject": subject,
            "predicate": predicate,
            "object": obj,
            "status": status,
            "confidence": confidence,
            "first_seen": min(slot["observed_dates"]),
            "last_seen": max(slot["observed_dates"]),
            "source_count": source_count,
            "source_domain_count": domain_count,
            "source_domains": domains,
            "agent_support_max": slot["agent_support_max"],
            "artifacts": sorted(slot["artifacts"]),
            "evidence": evidence_rows,
        }
        records.append(record)

    counters["claims_total"] = len(records)
    counters["claims_corroborated"] = sum(r["status"] == "corroborated" for r in records)
    counters["claims_provisional"] = sum(r["status"] == "provisional" for r in records)
    supply_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        if record["predicate"] == "SUPPLIES_TO":
            pair = tuple(sorted((record["subject"], record["object"])))
            supply_by_pair.setdefault(pair, []).append(record)
    direction_conflicts = []
    for pair, pair_records in sorted(supply_by_pair.items()):
        directions = {(r["subject"], r["object"]) for r in pair_records}
        if len(directions) > 1:
            direction_conflicts.append({
                "pair": list(pair),
                "claims": [{
                    "claim_id": r["claim_id"],
                    "source": r["subject"],
                    "target": r["object"],
                    "status": r["status"],
                    "source_count": r["source_count"],
                } for r in pair_records],
            })
    counters["direction_conflicts"] = len(direction_conflicts)

    def compact(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "claim_id": record["claim_id"],
            "subject": record["subject"],
            "predicate": record["predicate"],
            "object": record["object"],
            "status": record["status"],
            "confidence": record["confidence"],
            "source_count": record["source_count"],
            "source_domain_count": record["source_domain_count"],
            "last_seen": record["last_seen"],
        }

    top_corroborated = sorted(
        (r for r in records if r["status"] == "corroborated"),
        key=lambda r: (r["source_domain_count"], r["source_count"], r["confidence"]),
        reverse=True,
    )[:40]
    review_queue = sorted(
        (r for r in records if r["status"] == "provisional" and r["source_count"] >= 2),
        key=lambda r: (r["source_count"], r["confidence"]),
        reverse=True,
    )[:40]
    quality = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": anchor.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "window_days": since_days,
        "window_start": cutoff.isoformat(),
        "counts": dict(sorted(counters.items())),
        "claims_by_predicate": dict(sorted(Counter(r["predicate"] for r in records).items())),
        "corroborated_by_predicate": dict(sorted(Counter(
            r["predicate"] for r in records if r["status"] == "corroborated"
        ).items())),
        "top_corroborated_claims": [compact(r) for r in top_corroborated],
        "review_queue": [compact(r) for r in review_queue],
        "direction_conflicts": direction_conflicts,
    }
    return records, quality


def validate_records(records: Iterable[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for i, record in enumerate(records, 1):
        prefix = f"record {i}"
        cid = record.get("claim_id")
        if not isinstance(cid, str) or not cid.startswith("claim:"):
            errors.append(f"{prefix}: invalid claim_id")
        elif cid in seen_ids:
            errors.append(f"{prefix}: duplicate claim_id {cid}")
        else:
            seen_ids.add(cid)
        triple = canonical_triple(
            record.get("subject"), record.get("predicate"), record.get("object")
        )
        if triple != (record.get("subject"), record.get("predicate"), record.get("object")):
            errors.append(f"{prefix}: non-canonical triple")
        evidence = record.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{prefix}: evidence must be a non-empty list")
            evidence = []
        keys = [e.get("source_key") for e in evidence if isinstance(e, dict)]
        domains = {e.get("domain") for e in evidence if isinstance(e, dict) and e.get("domain")}
        if len(keys) != len(set(keys)):
            errors.append(f"{prefix}: duplicate evidence source_key")
        if record.get("source_count") != len(evidence):
            errors.append(f"{prefix}: source_count mismatch")
        if record.get("source_domain_count") != len(domains):
            errors.append(f"{prefix}: source_domain_count mismatch")
        eligible = (
            len(evidence) >= 2
            and len(domains) >= 2
            and _float(record.get("confidence")) >= 0.65
        )
        expected_status = "corroborated" if eligible else "provisional"
        if record.get("status") != expected_status:
            errors.append(f"{prefix}: status must be {expected_status}")
    return errors


def to_graph(records: Iterable[dict[str, Any]], universe: set[str]) -> tuple[list[Node], list[Edge]]:
    """Convert corroborated claims into graph nodes and typed direct edges."""
    rows = list(records)
    supply_directions: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for record in rows:
        if record.get("predicate") != "SUPPLIES_TO" or record.get("status") != "corroborated":
            continue
        pair = tuple(sorted((record["subject"], record["object"])))
        supply_directions.setdefault(pair, set()).add((record["subject"], record["object"]))
    conflicted_pairs = {pair for pair, directions in supply_directions.items() if len(directions) > 1}

    nodes: dict[str, Node] = {}
    edges: list[Edge] = []
    for record in rows:
        if record.get("status") != "corroborated":
            continue
        subject, obj = record["subject"], record["object"]
        if (
            record.get("predicate") == "SUPPLIES_TO"
            and tuple(sorted((subject, obj))) in conflicted_pairs
        ):
            continue
        s_symbol, o_symbol = subject[7:], obj[7:]
        if universe and (s_symbol not in universe or o_symbol not in universe):
            continue
        for entity, symbol in ((subject, s_symbol), (obj, o_symbol)):
            node = nodes.setdefault(entity, Node(
                id=entity,
                type=NodeType.TICKER.value,
                label=symbol,
                last_seen=record.get("last_seen"),
            ))
            node.mentions += int(record.get("source_count") or 0)
            node.sources.update(record.get("artifacts") or [])
        confidence = _float(record.get("confidence"), 0.65)
        source_count = int(record.get("source_count") or 2)
        weight = min(0.65, 0.25 + 0.25 * confidence + 0.05 * max(source_count - 2, 0))
        edges.append(Edge(
            source=subject,
            target=obj,
            type=record["predicate"],
            raw_frequency=float(source_count),
            weight=weight,
            tier="claim_ledger",
            confidence=confidence,
            last_seen=record.get("last_seen"),
            sources=set(record.get("artifacts") or []),
            metadata={
                "claim_id": record["claim_id"],
                "evidence_status": record["status"],
                "source_count": source_count,
                "source_domain_count": record.get("source_domain_count"),
                "source_domains": record.get("source_domains") or [],
                "evidence_urls": [e.get("url") for e in record.get("evidence") or []][:12],
            },
        ))
    return list(nodes.values()), edges


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no}: record must be an object")
        records.append(row)
    return records


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def write_artifacts(
    records: list[dict[str, Any]], quality: dict[str, Any],
    ledger_path: Path, quality_path: Path,
) -> None:
    errors = validate_records(records)
    if errors:
        raise ValueError("claim ledger validation failed: " + "; ".join(errors[:8]))
    payload = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records)
    _atomic_write_text(ledger_path, payload)
    _atomic_write_text(quality_path, json.dumps(quality, ensure_ascii=False, indent=2) + "\n")
    ledger_path.chmod(0o644)
    quality_path.chmod(0o644)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or validate the Nexus claim ledger")
    parser.add_argument("--break-news-dir", type=Path, default=Path("news/break_news_logs"))
    parser.add_argument("--output", type=Path, default=Path("nexus/claim_ledger.jsonl"))
    parser.add_argument("--quality-output", type=Path, default=Path("Dashboard/nexus_quality.json"))
    parser.add_argument("--since-days", type=int, default=45)
    parser.add_argument("--check", action="store_true", help="validate the existing ledger")
    args = parser.parse_args(argv)
    if args.check:
        try:
            records = read_jsonl(args.output)
        except (OSError, ValueError) as exc:
            print(f"[nexus-claims] INVALID: {exc}", file=sys.stderr)
            return 1
        errors = validate_records(records)
        if errors:
            print("[nexus-claims] INVALID: " + "; ".join(errors[:12]), file=sys.stderr)
            return 1
        print(f"[nexus-claims] VALID: {len(records)} claims")
        return 0
    records, quality = build_records(args.break_news_dir, since_days=args.since_days)
    try:
        write_artifacts(records, quality, args.output, args.quality_output)
    except (OSError, ValueError) as exc:
        print(f"[nexus-claims] FATAL: {exc}", file=sys.stderr)
        return 1
    counts = quality["counts"]
    print(
        f"[nexus-claims] wrote {len(records)} claims; "
        f"{counts.get('claims_corroborated', 0)} corroborated → {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
