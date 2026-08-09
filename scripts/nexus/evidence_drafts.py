#!/usr/bin/env python3
"""Build deterministic, evidence-only supply-chain drafts from Nexus topics.

Drafts are exploration artifacts, not curated chains.  They contain only
ticker nodes and relations already present in the topic queue / claim ledger;
missing private, foreign, material, and equipment nodes are recorded as gaps
instead of being invented.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from .claim_ledger import canonical_triple, canonical_url, read_jsonl


SCHEMA_VERSION = 1
LAYERS = ("upstream", "intermediate", "downstream", "unresolved")
FLOW_PREDICATES = {"SUPPLIES_TO", "CONTRACT_MFG_FOR"}
CONTEXT_PREDICATES = {"COMPETES_WITH", "CO_DEVELOPS_WITH"}


def _ticker(entity: str) -> str:
    return str(entity or "").split(":", 1)[-1].upper()


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


def _claim_index(records: list[dict[str, Any]]) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for claim in records:
        triple = canonical_triple(claim.get("subject"), claim.get("predicate"), claim.get("object"))
        if triple:
            index[triple].append(claim)
    return index


def _topic_sources(topic: dict[str, Any]) -> list[dict[str, Any]]:
    out, seen = [], set()
    for raw in topic.get("evidence") or []:
        if not isinstance(raw, dict):
            continue
        url = canonical_url(raw.get("url"))
        key = str(raw.get("source_key") or "")
        if not url or not key or key in seen:
            continue
        seen.add(key)
        out.append({
            "source_key": key,
            "url": url,
            "domain": str(raw.get("domain") or ""),
            "published": str(raw.get("published") or "")[:10],
            "headline": str(raw.get("headline") or "")[:180],
        })
    return out


def _draft_for_topic(topic: dict[str, Any], claim_index: dict[tuple[str, str, str], list[dict[str, Any]]]) -> dict[str, Any]:
    topic_artifacts = set(topic.get("artifacts") or [])
    topic_tickers = {str(t).upper() for t in (topic.get("tickers") or []) if str(t).strip()}
    sources = _topic_sources(topic)
    source_keys = {row["source_key"] for row in sources}
    edges: list[dict[str, Any]] = []
    context_edges: list[dict[str, Any]] = []
    seen_triples: set[tuple[str, str, str]] = set()

    for relation in topic.get("top_relations") or []:
        if not isinstance(relation, dict):
            continue
        triple = canonical_triple(
            relation.get("subject"), relation.get("predicate"), relation.get("object")
        )
        if not triple or triple in seen_triples:
            continue
        seen_triples.add(triple)
        subject, predicate, obj = triple
        if _ticker(subject) not in topic_tickers or _ticker(obj) not in topic_tickers:
            continue
        matching_claims = [
            claim for claim in claim_index.get(triple, [])
            if topic_artifacts.intersection(claim.get("artifacts") or [])
        ]
        evidence_keys = sorted({
            row.get("source_key")
            for claim in matching_claims
            for row in (claim.get("evidence") or [])
            if row.get("source_key") in source_keys
        })
        corroborated = [claim for claim in matching_claims if claim.get("status") == "corroborated"]
        row = {
            "from": _ticker(subject),
            "to": _ticker(obj),
            "rel": predicate,
            "mentions": int(relation.get("mentions") or 0),
            "evidence_level": "corroborated" if corroborated else "topic_context",
            "claim_ids": sorted(claim["claim_id"] for claim in matching_claims if claim.get("claim_id")),
            "evidence_source_keys": evidence_keys,
        }
        if predicate in FLOW_PREDICATES:
            edges.append(row)
        elif predicate in CONTEXT_PREDICATES:
            context_edges.append(row)

    incoming: dict[str, int] = defaultdict(int)
    outgoing: dict[str, int] = defaultdict(int)
    for edge in edges:
        outgoing[edge["from"]] += 1
        incoming[edge["to"]] += 1

    nodes = []
    for ticker in sorted(topic_tickers):
        if outgoing[ticker] and not incoming[ticker]:
            layer = "upstream"
        elif outgoing[ticker] and incoming[ticker]:
            layer = "intermediate"
        elif incoming[ticker] and not outgoing[ticker]:
            layer = "downstream"
        else:
            layer = "unresolved"
        nodes.append({
            "id": ticker,
            "label": ticker,
            "ticker": ticker,
            "layer": layer,
            "evidence_basis": "topic_ticker_entity",
        })

    present_layers = [layer for layer in LAYERS if any(n["layer"] == layer for n in nodes)]
    corroborated_edges = sum(edge["evidence_level"] == "corroborated" for edge in edges)
    unresolved = [node["ticker"] for node in nodes if node["layer"] == "unresolved"]
    gaps = [
        "private_and_foreign_company_coverage_not_available_in_ticker_only_evidence",
        "materials_and_equipment_layers_require_additional_evidence",
    ]
    if unresolved:
        gaps.append("unresolved_ticker_roles: " + ", ".join(unresolved))
    if corroborated_edges < len(edges):
        gaps.append("some_directional_relations_lack_claim_level_corroboration")

    return {
        "draft_id": "draft:" + str(topic.get("topic_id") or "topic:unknown").split(":", 1)[-1],
        "status": "evidence_only",
        "decision_eligible": False,
        "source_topic": {
            "topic_id": topic.get("topic_id"),
            "label": topic.get("label"),
            "state": topic.get("state"),
            "score": topic.get("score"),
            "first_seen": topic.get("first_seen"),
            "last_seen": topic.get("last_seen"),
            "source_count": topic.get("source_count"),
            "source_domain_count": topic.get("source_domain_count"),
            "tickers": sorted(topic_tickers),
            "why_now": list(topic.get("why_now") or []),
        },
        "layers": present_layers,
        "nodes": nodes,
        "edges": edges,
        "context_edges": context_edges,
        "evidence": sources,
        "evidence_summary": {
            "source_count": len(sources),
            "source_domain_count": len({row["domain"] for row in sources if row["domain"]}),
            "directional_edge_count": len(edges),
            "corroborated_edge_count": corroborated_edges,
        },
        "known_gaps": gaps,
        "next_action": "human_review_or_bounded_gap_fill",
    }


def build_drafts(
    topic_payload: dict[str, Any],
    claim_records: list[dict[str, Any]],
    *,
    limit: int = 12,
) -> dict[str, Any]:
    candidate_source = topic_payload.get("draft_candidates") or topic_payload.get("new_chain_candidates") or []
    candidates = [
        topic for topic in candidate_source
        if isinstance(topic, dict) and topic.get("coverage_status") == "new_candidate"
    ]
    candidates.sort(key=lambda topic: (
        float(topic.get("score") or 0),
        float(topic.get("velocity_ratio") or 0),
        int(topic.get("source_count") or 0),
        str(topic.get("topic_id") or ""),
    ), reverse=True)
    candidates = candidates[:max(0, limit)]
    claim_index = _claim_index(claim_records)
    drafts = [_draft_for_topic(topic, claim_index) for topic in candidates]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": topic_payload.get("generated_at"),
        "artifact_class": "exploration_only",
        "decision_use": "forbidden",
        "generation_rule": "highest-score uncovered Nexus candidates; deterministic ticker-only evidence projection",
        "counts": {
            "available_new_candidates": int((topic_payload.get("counts") or {}).get("new_chain_candidates") or len(candidates)),
            "drafts_generated": len(drafts),
            "drafts_with_corroborated_edges": sum(
                bool(draft["evidence_summary"]["corroborated_edge_count"]) for draft in drafts
            ),
        },
        "drafts": drafts,
    }


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be 1")
    if payload.get("artifact_class") != "exploration_only":
        errors.append("artifact_class must be exploration_only")
    if payload.get("decision_use") != "forbidden":
        errors.append("decision_use must be forbidden")
    drafts = payload.get("drafts")
    if not isinstance(drafts, list):
        return errors + ["drafts must be a list"]
    seen_ids = set()
    for i, draft in enumerate(drafts, 1):
        prefix = f"draft {i}"
        draft_id = draft.get("draft_id")
        if not isinstance(draft_id, str) or not draft_id.startswith("draft:"):
            errors.append(f"{prefix}: invalid draft_id")
        elif draft_id in seen_ids:
            errors.append(f"{prefix}: duplicate draft_id")
        seen_ids.add(draft_id)
        if draft.get("status") != "evidence_only" or draft.get("decision_eligible") is not False:
            errors.append(f"{prefix}: draft must remain evidence-only and decision-ineligible")
        source = draft.get("source_topic") or {}
        if int(source.get("source_count") or 0) < 3 or int(source.get("source_domain_count") or 0) < 2:
            errors.append(f"{prefix}: source topic does not clear evidence gate")
        source_tickers = set(source.get("tickers") or [])
        evidence = draft.get("evidence") or []
        evidence_keys = [row.get("source_key") for row in evidence if isinstance(row, dict)]
        if len(evidence_keys) != len(set(evidence_keys)):
            errors.append(f"{prefix}: duplicate evidence source_key")
        if any(not canonical_url(row.get("url")) for row in evidence if isinstance(row, dict)):
            errors.append(f"{prefix}: invalid evidence URL")
        nodes = draft.get("nodes") or []
        node_ids = [node.get("id") for node in nodes if isinstance(node, dict)]
        if len(node_ids) != len(set(node_ids)):
            errors.append(f"{prefix}: duplicate node id")
        if set(node_ids) - source_tickers:
            errors.append(f"{prefix}: contains nodes not present in source topic")
        if any(node.get("layer") not in LAYERS for node in nodes if isinstance(node, dict)):
            errors.append(f"{prefix}: invalid node layer")
        for j, edge in enumerate((draft.get("edges") or []) + (draft.get("context_edges") or []), 1):
            if edge.get("from") not in node_ids or edge.get("to") not in node_ids:
                errors.append(f"{prefix} edge {j}: endpoint missing from nodes")
            if edge.get("rel") not in FLOW_PREDICATES | CONTEXT_PREDICATES:
                errors.append(f"{prefix} edge {j}: invalid relation")
            if set(edge.get("evidence_source_keys") or []) - set(evidence_keys):
                errors.append(f"{prefix} edge {j}: unknown evidence source key")
    if int((payload.get("counts") or {}).get("drafts_generated") or 0) != len(drafts):
        errors.append("counts.drafts_generated mismatch")
    return errors


def write_payload(path: Path, payload: dict[str, Any]) -> None:
    errors = validate_payload(payload)
    if errors:
        raise ValueError("draft validation failed: " + "; ".join(errors[:8]))
    _atomic_json(path, payload)
    path.chmod(0o644)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build evidence-only Nexus supply-chain drafts")
    parser.add_argument("--topics", type=Path, default=Path("Dashboard/nexus_topics.json"))
    parser.add_argument("--claim-ledger", type=Path, default=Path("nexus/claim_ledger.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("Dashboard/nexus_evidence_drafts.json"))
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        try:
            payload = json.loads(args.output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[nexus-drafts] INVALID: {exc}", file=sys.stderr)
            return 1
        errors = validate_payload(payload)
        if errors:
            print("[nexus-drafts] INVALID: " + "; ".join(errors[:12]), file=sys.stderr)
            return 1
        print(f"[nexus-drafts] VALID: {len(payload.get('drafts') or [])} drafts")
        return 0
    try:
        topics = json.loads(args.topics.read_text(encoding="utf-8"))
        claims = read_jsonl(args.claim_ledger) if args.claim_ledger.exists() else []
        payload = build_drafts(topics, claims, limit=args.limit)
        write_payload(args.output, payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"[nexus-drafts] FATAL: {exc}", file=sys.stderr)
        return 1
    print(f"[nexus-drafts] wrote {len(payload['drafts'])} drafts → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
