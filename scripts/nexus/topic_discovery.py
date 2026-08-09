#!/usr/bin/env python3
"""Deterministic emerging-topic discovery for Project Nexus.

This turns the themes and technical keywords already produced by Break News
into a daily candidate queue.  It does not call an LLM and does not alter any
investment decision.  Promotion is evidence-based: a validated topic needs at
least three distinct source URLs across at least two domains.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from .claim_ledger import canonical_url, source_domain


SCHEMA_VERSION = 1
STRUCTURAL_PREDICATES = {
    "SUPPLIES_TO", "CUSTOMER_OF", "CONTRACT_MFG_FOR",
    "COMPETES_WITH", "CO_DEVELOPS_WITH",
}
STOP_TOPICS = {
    "ai", "artificial intelligence", "earnings", "equities", "growth",
    "market", "markets", "revenue", "stock", "stocks", "technology",
    "us equities", "wall street",
}
BOTTLENECK_TERMS = {
    "backlog", "bottleneck", "capacity constraint", "capacity expansion",
    "component allocation", "lead time", "manufacturing yield",
    "production capacity", "qualification", "shortage", "supply constraint",
    "supply tightness", "throughput", "wafer allocation", "yield ramp",
}
SUPPLY_TOPIC_TERMS = {
    "accelerator", "battery", "cable", "capacitor", "cdmo", "chip",
    "cooling", "copper", "cpo", "data center", "datacenter", "dram",
    "equipment", "fab", "foundry", "gaas", "gan", "grid", "hbm",
    "interconnect", "lithography", "memory", "mlcc", "nand", "networking",
    "nuclear", "optical", "optics", "packaging", "photonics", "power",
    "quantum", "rack", "rf", "semiconductor", "server", "sic", "silicon",
    "supply chain", "switch", "transformer", "uranium", "wafer",
}


def topic_key(raw: Any) -> tuple[str, str] | None:
    label = re.sub(r"\s+", " ", str(raw or "").strip())
    if len(label) < 3 or len(label) > 100:
        return None
    normalized = label.casefold().replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9一-鿿.+\-/ ]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip(" ./-")
    if not normalized or normalized in STOP_TOPICS:
        return None
    slug = re.sub(r"[^a-z0-9一-鿿]+", "_", normalized).strip("_")
    if not slug:
        return None
    return slug, label


def supply_topic_hint(label: str) -> bool:
    value = str(label or "").casefold().replace("-", " ")
    return any(term in value for term in SUPPLY_TOPIC_TERMS)


def _date(raw: Any) -> str | None:
    value = str(raw or "")[:10]
    try:
        return datetime.fromisoformat(value).date().isoformat()
    except ValueError:
        return None


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def existing_chain_index(supply_chain_dir: Path | None) -> dict[str, str]:
    """Map canonical topic slugs to existing curated supply-chain slugs."""
    index: dict[str, str] = {}
    if not supply_chain_dir or not supply_chain_dir.is_dir():
        return index
    for path in sorted(supply_chain_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        for raw in (path.stem.replace("_", " "), data.get("theme"), data.get("title")):
            parsed = topic_key(raw)
            if parsed:
                index.setdefault(parsed[0], path.stem)
    return index


def build_topics(
    break_news_dir: Path,
    claim_records: list[dict[str, Any]],
    *,
    since_days: int = 45,
    anchor_date: datetime | None = None,
    supply_chain_dir: Path | None = None,
) -> dict[str, Any]:
    anchor = anchor_date or datetime.now(timezone.utc)
    cutoff = anchor.date() - timedelta(days=since_days)
    recent_cutoff = anchor.date() - timedelta(days=6)
    groups: dict[str, dict[str, Any]] = {}
    counters: Counter[str] = Counter()
    chain_index = existing_chain_index(supply_chain_dir)

    for path in sorted(break_news_dir.glob("bn_*.json")):
        counters["artifacts_scanned"] += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            counters["artifacts_unreadable"] += 1
            continue
        if data.get("state") not in ("closed", "partial_closed"):
            continue
        observed = _date(data.get("fetched_at"))
        if not observed or datetime.fromisoformat(observed).date() < cutoff:
            continue
        source = data.get("source") if isinstance(data.get("source"), dict) else {}
        url = canonical_url(source.get("url"))
        if not url:
            counters["artifacts_without_url"] += 1
            continue
        source_key = f"url:{hashlib.sha1(url.encode()).hexdigest()}"
        summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
        entities = summary.get("merged_entities") if isinstance(summary.get("merged_entities"), dict) else {}
        raw_topics = [
            *((entities.get("themes") or []) if isinstance(entities.get("themes"), list) else []),
            *((entities.get("tech_keywords") or []) if isinstance(entities.get("tech_keywords"), list) else []),
        ]
        tickers = {
            str(t).strip().upper() for t in (entities.get("tickers") or [])
            if str(t).strip()
        }
        structural = []
        for relation in summary.get("merged_relations") or []:
            if not isinstance(relation, dict):
                continue
            predicate = str(relation.get("predicate") or "").upper()
            subject, obj = str(relation.get("subject") or ""), str(relation.get("object") or "")
            if predicate in STRUCTURAL_PREDICATES and subject.startswith("ticker:") and obj.startswith("ticker:"):
                structural.append((subject, predicate, obj))
        context = " ".join(str(x or "") for x in (
            data.get("headline"), data.get("raw_summary"), summary.get("final_take")
        )).casefold()
        bottlenecks = sorted(term for term in BOTTLENECK_TERMS if term in context)
        artifact = f"break_news:{data.get('news_id') or path.stem}"

        item_topics: dict[str, str] = {}
        for raw in raw_topics:
            parsed = topic_key(raw)
            if parsed:
                item_topics.setdefault(parsed[0], parsed[1])
        for slug, label in item_topics.items():
            slot = groups.setdefault(slug, {
                "labels": Counter(),
                "evidence": {},
                "dates": set(),
                "tickers": set(),
                "artifacts": set(),
                "relations": Counter(),
                "bottleneck_terms": Counter(),
            })
            slot["labels"][label] += 1
            slot["dates"].add(observed)
            slot["tickers"].update(tickers)
            slot["artifacts"].add(artifact)
            slot["bottleneck_terms"].update(bottlenecks)
            for triple in structural:
                slot["relations"][triple] += 1
            existing = slot["evidence"].setdefault(source_key, {
                "source_key": source_key,
                "url": url,
                "domain": source_domain(url),
                "published": _date(source.get("published")) or observed,
                "headline": str(data.get("headline") or "")[:180],
                "artifacts": set(),
            })
            existing["artifacts"].add(artifact)

    claim_by_artifact: dict[str, list[dict[str, Any]]] = {}
    for claim in claim_records:
        for artifact in claim.get("artifacts") or []:
            claim_by_artifact.setdefault(artifact, []).append(claim)

    topics = []
    for slug, slot in groups.items():
        evidence = []
        for row in slot["evidence"].values():
            evidence.append({**row, "artifacts": sorted(row["artifacts"])})
        evidence.sort(key=lambda r: (r["published"], r["source_key"]), reverse=True)
        source_count = len(evidence)
        domains = sorted({r["domain"] for r in evidence if r["domain"]})
        recent_sources = sum(
            datetime.fromisoformat(r["published"]).date() >= recent_cutoff
            for r in evidence if r.get("published")
        )
        prior_sources = max(source_count - recent_sources, 0)
        recent_rate = recent_sources / 7.0
        prior_days = max(since_days - 7, 1)
        prior_rate = prior_sources / prior_days
        acceleration = round(min(5.0, recent_rate / max(prior_rate, 0.05)), 3)
        relation_count = len(slot["relations"])
        supply_relation_count = sum(
            1 for triple in slot["relations"]
            if triple[1] in {"SUPPLIES_TO", "CUSTOMER_OF", "CONTRACT_MFG_FOR"}
        )
        related_claims: dict[str, dict[str, Any]] = {}
        for artifact in slot["artifacts"]:
            for claim in claim_by_artifact.get(artifact, []):
                related_claims[claim["claim_id"]] = claim
        corroborated_relations = sum(
            claim.get("status") == "corroborated" for claim in related_claims.values()
        )
        first_seen, last_seen = min(slot["dates"]), max(slot["dates"])
        novelty = 1.0 if (anchor.date() - datetime.fromisoformat(first_seen).date()).days <= 14 else 0.0
        score = (
            25 * min(source_count / 8, 1)
            + 15 * min(len(domains) / 5, 1)
            + 15 * min(len(slot["tickers"]) / 8, 1)
            + 15 * min((relation_count + corroborated_relations) / 6, 1)
            + 15 * min(math.log2(acceleration + 1) / math.log2(6), 1)
            + 10 * min(sum(slot["bottleneck_terms"].values()) / 3, 1)
            + 5 * novelty
        )
        score = round(score, 1)
        if source_count >= 3 and len(domains) >= 2 and score >= 35:
            state = "validated"
        elif source_count >= 2 and len(domains) >= 2 and score >= 20:
            state = "emerging"
        else:
            state = "seed"
        if (anchor.date() - datetime.fromisoformat(last_seen).date()).days > 14:
            state = "decaying"
        why_now = []
        if acceleration >= 1.5:
            why_now.append(f"7d source velocity {acceleration:.1f}× prior rate")
        if relation_count:
            why_now.append(f"{relation_count} structural ticker relations")
        if supply_relation_count:
            why_now.append(f"{supply_relation_count} directional supply relations")
        if corroborated_relations:
            why_now.append(f"{corroborated_relations} corroborated relation claims")
        if slot["bottleneck_terms"]:
            why_now.append("bottleneck language: " + ", ".join(
                term for term, _ in slot["bottleneck_terms"].most_common(4)
            ))
        if len(slot["tickers"]) >= 3:
            why_now.append(f"spans {len(slot['tickers'])} tickers")

        label = slot["labels"].most_common(1)[0][0]
        top_relations = sorted(
            slot["relations"].items(),
            key=lambda item: (
                item[0][1] in {"SUPPLIES_TO", "CUSTOMER_OF", "CONTRACT_MFG_FOR"},
                item[1],
                item[0],
            ),
            reverse=True,
        )[:10]
        topics.append({
            "topic_id": f"topic:{slug}",
            "label": label,
            "state": state,
            "score": score,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "source_count": source_count,
            "source_domain_count": len(domains),
            "recent_7d_source_count": recent_sources,
            "velocity_ratio": acceleration,
            "ticker_count": len(slot["tickers"]),
            "tickers": sorted(slot["tickers"])[:30],
            "structural_relation_count": relation_count,
            "supply_relation_count": supply_relation_count,
            "corroborated_relation_count": corroborated_relations,
            "bottleneck_terms": [term for term, _ in slot["bottleneck_terms"].most_common(8)],
            "supply_topic_hint": supply_topic_hint(label),
            "coverage_status": "existing_chain" if slug in chain_index else "new_candidate",
            "existing_chain_slug": chain_index.get(slug),
            "why_now": why_now,
            "artifact_count": len(slot["artifacts"]),
            "artifacts": sorted(slot["artifacts"], reverse=True)[:40],
            "evidence": evidence[:8],
            "top_relations": [{
                "subject": triple[0], "predicate": triple[1], "object": triple[2], "mentions": count,
            } for triple, count in top_relations],
        })

    state_rank = {"validated": 4, "emerging": 3, "seed": 2, "decaying": 1}
    topics.sort(key=lambda t: (state_rank[t["state"]], t["score"], t["source_count"]), reverse=True)
    chain_candidates = [
        topic for topic in topics
        if topic["state"] in {"validated", "emerging"}
        and topic["source_count"] >= 3
        and topic["source_domain_count"] >= 2
        and topic["ticker_count"] >= 2
        and topic["supply_relation_count"] >= 1
        and (topic["supply_topic_hint"] or bool(topic["bottleneck_terms"]))
    ]
    chain_candidates.sort(key=lambda t: (
        t["supply_relation_count"] > 0,
        t["velocity_ratio"],
        t["score"],
    ), reverse=True)
    new_chain_candidates = [
        topic for topic in chain_candidates if topic["coverage_status"] == "new_candidate"
    ]
    draft_candidates = sorted(new_chain_candidates, key=lambda t: (
        t["score"], t["velocity_ratio"], t["source_count"], t["topic_id"]
    ), reverse=True)[:20]
    counters["topics_total"] = len(topics)
    counters.update({f"topics_{state}": sum(t["state"] == state for t in topics)
                     for state in state_rank})
    counters["chain_candidates"] = len(chain_candidates)
    counters["new_chain_candidates"] = len(new_chain_candidates)
    projected_topics = chain_candidates[:40]
    projected_ids = {topic["topic_id"] for topic in projected_topics}
    projected_topics.extend(
        topic for topic in draft_candidates
        if topic["topic_id"] not in projected_ids
    )
    projected_ids.update(topic["topic_id"] for topic in projected_topics)
    projected_topics.extend(
        topic for topic in topics
        if topic["topic_id"] not in projected_ids
    )
    projected_topics = projected_topics[:120]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": anchor.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "window_days": since_days,
        "promotion_rule": "validated requires >=3 distinct URLs across >=2 domains and score>=35",
        "counts": dict(sorted(counters.items())),
        "topics": projected_topics,
        "chain_candidates": chain_candidates[:40],
        "new_chain_candidates": new_chain_candidates[:30],
        "draft_candidates": draft_candidates,
    }


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors = []
    topics = payload.get("topics")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be 1")
    if not isinstance(topics, list):
        return errors + ["topics must be a list"]
    ids = set()
    for i, topic in enumerate(topics, 1):
        prefix = f"topic {i}"
        tid = topic.get("topic_id")
        if not isinstance(tid, str) or not tid.startswith("topic:"):
            errors.append(f"{prefix}: invalid topic_id")
        elif tid in ids:
            errors.append(f"{prefix}: duplicate topic_id")
        ids.add(tid)
        if topic.get("state") not in {"seed", "emerging", "validated", "decaying"}:
            errors.append(f"{prefix}: invalid state")
        if topic.get("state") == "validated" and not (
            int(topic.get("source_count") or 0) >= 3
            and int(topic.get("source_domain_count") or 0) >= 2
            and float(topic.get("score") or 0) >= 35
        ):
            errors.append(f"{prefix}: validated topic does not clear promotion gate")
        evidence = topic.get("evidence") or []
        keys = [row.get("source_key") for row in evidence if isinstance(row, dict)]
        if len(keys) != len(set(keys)):
            errors.append(f"{prefix}: duplicate evidence source_key")
    topic_ids = {topic.get("topic_id") for topic in topics if isinstance(topic, dict)}
    chain_candidates = payload.get("chain_candidates") or []
    if not isinstance(chain_candidates, list):
        errors.append("chain_candidates must be a list")
    else:
        for i, topic in enumerate(chain_candidates, 1):
            if topic.get("topic_id") not in topic_ids:
                errors.append(f"chain candidate {i}: topic missing from topics projection")
            if int(topic.get("source_count") or 0) < 3:
                errors.append(f"chain candidate {i}: source_count below 3")
            if int(topic.get("supply_relation_count") or 0) < 1:
                errors.append(f"chain candidate {i}: no directional supply relation")
            if not (topic.get("supply_topic_hint") or topic.get("bottleneck_terms")):
                errors.append(f"chain candidate {i}: no supply-topic or bottleneck evidence")
    for i, topic in enumerate(payload.get("new_chain_candidates") or [], 1):
        if topic.get("coverage_status") != "new_candidate":
            errors.append(f"new chain candidate {i}: coverage_status is not new_candidate")
        if topic.get("topic_id") not in topic_ids:
            errors.append(f"new chain candidate {i}: topic missing from topics projection")
    for i, topic in enumerate(payload.get("draft_candidates") or [], 1):
        if topic.get("coverage_status") != "new_candidate":
            errors.append(f"draft candidate {i}: coverage_status is not new_candidate")
        if topic.get("topic_id") not in topic_ids:
            errors.append(f"draft candidate {i}: topic missing from topics projection")
    return errors


def write_payload(path: Path, payload: dict[str, Any]) -> None:
    errors = validate_payload(payload)
    if errors:
        raise ValueError("topic validation failed: " + "; ".join(errors[:8]))
    _atomic_json(path, payload)
    path.chmod(0o644)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Nexus emerging-topic candidates")
    parser.add_argument("--break-news-dir", type=Path, default=Path("news/break_news_logs"))
    parser.add_argument("--claim-ledger", type=Path, default=Path("nexus/claim_ledger.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("Dashboard/nexus_topics.json"))
    parser.add_argument("--supply-chain-dir", type=Path, default=Path("nexus/supply_chains"))
    parser.add_argument("--since-days", type=int, default=45)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        try:
            payload = json.loads(args.output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[nexus-topics] INVALID: {exc}", file=sys.stderr)
            return 1
        errors = validate_payload(payload)
        if errors:
            print("[nexus-topics] INVALID: " + "; ".join(errors[:12]), file=sys.stderr)
            return 1
        print(f"[nexus-topics] VALID: {len(payload.get('topics') or [])} topics")
        return 0
    claim_records = []
    if args.claim_ledger.exists():
        from .claim_ledger import read_jsonl
        claim_records = read_jsonl(args.claim_ledger)
    payload = build_topics(
        args.break_news_dir, claim_records, since_days=args.since_days,
        supply_chain_dir=args.supply_chain_dir,
    )
    try:
        write_payload(args.output, payload)
    except (OSError, ValueError) as exc:
        print(f"[nexus-topics] FATAL: {exc}", file=sys.stderr)
        return 1
    print(
        f"[nexus-topics] wrote {len(payload['topics'])} topics; "
        f"{payload['counts'].get('topics_validated', 0)} validated → {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
