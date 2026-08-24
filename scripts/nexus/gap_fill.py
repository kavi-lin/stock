#!/usr/bin/env python3
"""One-turn, evidence-backed gap fill for a Nexus evidence draft.

The runner is deliberately not part of the automatic daily build.  One user
action processes one topic and makes at most one governed LLM call.  Results
are proposals in an exploration-only sidecar; the base draft and curated chain
YAML files are never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from scripts._shared.model_router import run_role, run_with_fallback


SCHEMA_VERSION = 1
MAX_NODES = 8
MAX_EDGES = 10
ENTITY_TYPES = {
    "private_company", "foreign_company", "material", "component",
    "equipment", "infrastructure",
}
LAYERS = {"upstream", "intermediate", "downstream", "unresolved"}
LISTINGS = {"private", "pre_ipo", "foreign_listed", "not_applicable", "unknown"}
RELATIONS = {"SUPPLIES_TO", "CONTRACT_MFG_FOR", "CO_DEVELOPS_WITH"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]{1,63}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


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


def empty_ledger() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_class": "exploration_only",
        "decision_use": "forbidden",
        "updated_at": None,
        "entries": [],
    }


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_ledger()
    return json.loads(path.read_text(encoding="utf-8"))


def _citations(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out, seen = [], set()
    for value in raw[:8]:
        if not isinstance(value, dict):
            continue
        source_id = str(value.get("source_id") or "").strip()
        excerpt_ids = []
        for excerpt_id in value.get("excerpt_ids") or []:
            excerpt_id = str(excerpt_id or "").strip()
            if excerpt_id and excerpt_id not in excerpt_ids:
                excerpt_ids.append(excerpt_id)
        key = (source_id, tuple(excerpt_ids))
        if source_id and key not in seen:
            seen.add(key)
            out.append({"source_id": source_id, "excerpt_ids": excerpt_ids[:6]})
    return out


def _normalize_response(raw: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    nodes = []
    for item in (raw.get("proposed_nodes") or []):
        if not isinstance(item, dict):
            continue
        nodes.append({
            "id": str(item.get("id") or "").strip().lower().replace("-", "_"),
            "label": str(item.get("label") or "").strip()[:100],
            "entity_type": str(item.get("entity_type") or "").strip().lower(),
            "layer": str(item.get("layer") or "").strip().lower(),
            "role": str(item.get("role") or "").strip()[:240],
            "ticker": str(item.get("ticker") or "").strip().upper() or None,
            "listing": str(item.get("listing") or "unknown").strip().lower(),
            "market": str(item.get("market") or "UNKNOWN").strip().upper()[:16],
            "citations": _citations(item.get("citations")),
            "external_source_attempted": bool(item.get("source_urls") or item.get("url")),
            "reason": str(item.get("reason") or "").strip()[:300],
        })
    edges = []
    for item in (raw.get("proposed_edges") or []):
        if not isinstance(item, dict):
            continue
        edges.append({
            "from": str(item.get("from") or "").strip(),
            "to": str(item.get("to") or "").strip(),
            "rel": str(item.get("rel") or "").strip().upper(),
            "citations": _citations(item.get("citations")),
            "external_source_attempted": bool(item.get("source_urls") or item.get("url")),
            "rationale": str(item.get("rationale") or "").strip()[:300],
            "evidence_level": "llm_proposed",
        })
    return {
        "topic_id": (draft.get("source_topic") or {}).get("topic_id"),
        "proposed_nodes": nodes,
        "proposed_edges": edges,
        "unresolved_gaps": [str(x).strip()[:300] for x in (raw.get("unresolved_gaps") or [])[:12] if str(x).strip()],
        "notes": [str(x).strip()[:300] for x in (raw.get("notes") or [])[:8] if str(x).strip()],
    }


def _proposal_errors(
    proposal: dict[str, Any], draft: dict[str, Any], source_packet: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    expected_topic = (draft.get("source_topic") or {}).get("topic_id")
    if proposal.get("topic_id") != expected_topic:
        errors.append("topic_id does not match base draft")
    if source_packet.get("topic_id") != expected_topic:
        errors.append("source packet topic_id does not match base draft")
    if source_packet.get("base_draft_digest") != _digest(draft):
        errors.append("source packet base_draft_digest mismatch")
    source_map = {
        str(source.get("source_id")): source
        for source in (source_packet.get("sources") or [])
    }
    excerpt_map = {
        str(excerpt.get("excerpt_id")): (source_id, excerpt)
        for source_id, source in source_map.items()
        for excerpt in (source.get("excerpts") or [])
    }

    def citation_errors(item: dict[str, Any], label: str) -> tuple[list[str], set[str]]:
        item_errors: list[str] = []
        cited_sources: set[str] = set()
        has_fetched_page = False
        if item.get("external_source_attempted"):
            item_errors.append(f"{label}: external URLs are forbidden")
        citations = item.get("citations") or []
        if not citations:
            item_errors.append(f"{label}: packet citations required")
        for citation in citations:
            source_id = citation.get("source_id")
            if source_id not in source_map:
                item_errors.append(f"{label}: unknown source_id")
                continue
            cited_sources.add(source_id)
            excerpt_ids = citation.get("excerpt_ids") or []
            if not excerpt_ids:
                item_errors.append(f"{label}: excerpt_ids required")
            for excerpt_id in excerpt_ids:
                owner = excerpt_map.get(excerpt_id)
                if not owner or owner[0] != source_id:
                    item_errors.append(f"{label}: unknown or mismatched excerpt_id")
                    continue
                excerpt = owner[1]
                if excerpt.get("provenance") == "fetched_page" and excerpt.get("verbatim_page_text") is True:
                    has_fetched_page = True
        if citations and not has_fetched_page:
            item_errors.append(f"{label}: at least one fetched_page excerpt required")
        return item_errors, cited_sources

    nodes = proposal.get("proposed_nodes") or []
    edges = proposal.get("proposed_edges") or []
    if len(nodes) > MAX_NODES or len(edges) > MAX_EDGES:
        errors.append("proposal exceeds node/edge cap")
    base_ids = {str(node.get("id")) for node in (draft.get("nodes") or [])}
    base_tickers = {str(node.get("ticker") or "").upper() for node in (draft.get("nodes") or [])}
    node_ids = [str(node.get("id") or "") for node in nodes]
    if len(node_ids) != len(set(node_ids)):
        errors.append("duplicate proposed node id")
    for i, node in enumerate(nodes, 1):
        if not ID_RE.match(str(node.get("id") or "")):
            errors.append(f"node {i}: invalid id")
        if node.get("id") in base_ids or (node.get("ticker") and node.get("ticker") in base_tickers):
            errors.append(f"node {i}: duplicates an existing node")
        if not node.get("label") or not node.get("role") or not node.get("reason"):
            errors.append(f"node {i}: label/role/reason required")
        if node.get("entity_type") not in ENTITY_TYPES:
            errors.append(f"node {i}: invalid entity_type")
        if node.get("layer") not in LAYERS:
            errors.append(f"node {i}: invalid layer")
        if node.get("listing") not in LISTINGS:
            errors.append(f"node {i}: invalid listing")
        item_errors, _ = citation_errors(node, f"node {i}")
        errors.extend(item_errors)
    valid_ids = base_ids | set(node_ids)
    proposed_ids = set(node_ids)
    base_edges = {
        (str(edge.get("from")), str(edge.get("to")), str(edge.get("rel")))
        for edge in (draft.get("edges") or []) + (draft.get("context_edges") or [])
    }
    for i, edge in enumerate(edges, 1):
        triple = (edge.get("from"), edge.get("to"), edge.get("rel"))
        if edge.get("from") not in valid_ids or edge.get("to") not in valid_ids:
            errors.append(f"edge {i}: endpoint not found")
        if not ({edge.get("from"), edge.get("to")} & proposed_ids):
            errors.append(f"edge {i}: must connect a proposed node")
        if edge.get("rel") not in RELATIONS:
            errors.append(f"edge {i}: invalid relation")
        if triple in base_edges:
            errors.append(f"edge {i}: duplicates immutable base edge")
        if not edge.get("rationale"):
            errors.append(f"edge {i}: rationale required")
        item_errors, _ = citation_errors(edge, f"edge {i}")
        errors.extend(item_errors)
    cited_source_ids = {
        citation.get("source_id")
        for item in nodes + edges for citation in (item.get("citations") or [])
        if citation.get("source_id") in source_map
    }
    domains = {
        source_map[source_id].get("domain") for source_id in cited_source_ids
        if source_map[source_id].get("domain")
    }
    if nodes and len(domains) < 2:
        errors.append("proposal requires at least two independent source domains")
    if not nodes and not proposal.get("unresolved_gaps"):
        errors.append("empty proposal must explain unresolved gaps")
    return errors


def validate_ledger(
    payload: dict[str, Any], drafts: dict[str, dict[str, Any]] | None = None,
    source_packets: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be 1")
    if payload.get("artifact_class") != "exploration_only" or payload.get("decision_use") != "forbidden":
        errors.append("ledger must remain exploration-only and forbidden for decisions")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return errors + ["entries must be a list"]
    topics = []
    for i, entry in enumerate(entries, 1):
        topic_id = entry.get("topic_id")
        topics.append(topic_id)
        if entry.get("decision_eligible") is not False:
            errors.append(f"entry {i}: decision_eligible must be false")
        if entry.get("artifact_class") != "exploration_only":
            errors.append(f"entry {i}: artifact_class must be exploration_only")
        if entry.get("inference_turns") not in {0, 1}:
            errors.append(f"entry {i}: inference_turns must be 0 or 1")
        if entry.get("status") not in {"proposed", "failed", "blocked"}:
            errors.append(f"entry {i}: invalid status")
        if entry.get("status") == "proposed":
            draft = drafts.get(topic_id) if drafts else None
            source_packet = source_packets.get(topic_id) if source_packets else None
            if draft and source_packet:
                if entry.get("base_draft_digest") != _digest(draft):
                    errors.append(f"entry {i}: base_draft_digest mismatch")
                if entry.get("source_packet_digest") != _digest(source_packet):
                    errors.append(f"entry {i}: source_packet_digest mismatch")
                errors.extend(
                    f"entry {i}: {err}"
                    for err in _proposal_errors(entry.get("proposal") or {}, draft, source_packet)
                )
            elif drafts is not None or source_packets is not None:
                errors.append(f"entry {i}: matching draft and source packet required")
            if not entry.get("model_used") or entry.get("inference_turns") != 1:
                errors.append(f"entry {i}: proposed entry requires one model turn")
        elif not entry.get("error"):
            errors.append(f"entry {i}: failed/blocked entry requires error")
    spent_topics = [entry.get("topic_id") for entry in entries if entry.get("inference_turns") == 1]
    if len(spent_topics) != len(set(spent_topics)):
        errors.append("a topic consumed more than one inference turn")
    return errors


def _packet(draft: dict[str, Any], source_packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "topic_id": (draft.get("source_topic") or {}).get("topic_id"),
        "topic_label": (draft.get("source_topic") or {}).get("label"),
        "known_gaps": draft.get("known_gaps") or [],
        "existing_nodes": source_packet.get("immutable_nodes") or [],
        "immutable_edges": source_packet.get("immutable_edges") or [],
        "sources": [
            {
                "source_id": source.get("source_id"),
                "domain": source.get("domain"),
                "headline": source.get("headline"),
                "published": source.get("published"),
                "excerpts": [
                    {
                        "excerpt_id": excerpt.get("excerpt_id"),
                        "text": excerpt.get("text"),
                        "provenance": excerpt.get("provenance"),
                        "verbatim_page_text": excerpt.get("verbatim_page_text"),
                    }
                    for excerpt in (source.get("excerpts") or [])
                ],
            }
            for source in (source_packet.get("sources") or [])
        ],
        "relation_evidence": source_packet.get("relation_evidence") or [],
    }


def select_draft(draft_payload: dict[str, Any], ledger: dict[str, Any], topic_id: str | None = None) -> dict[str, Any]:
    drafts = draft_payload.get("drafts") or []
    spent = {entry.get("topic_id") for entry in (ledger.get("entries") or []) if entry.get("inference_turns") == 1}
    if topic_id:
        matches = [draft for draft in drafts if (draft.get("source_topic") or {}).get("topic_id") == topic_id]
        if not matches:
            raise ValueError(f"topic not found in evidence drafts: {topic_id}")
        if topic_id in spent:
            raise ValueError(f"topic already consumed its one inference turn: {topic_id}")
        return matches[0]
    available = [
        draft for draft in drafts
        if (draft.get("source_topic") or {}).get("topic_id") not in spent
    ]
    # Default trial target: preserve score order, but require a usable directed
    # skeleton. Prefer claim-level corroboration so the single model turn fills
    # around evidence rather than constructing a chain from an empty canvas.
    for pool in (
        [d for d in available if int((d.get("evidence_summary") or {}).get("corroborated_edge_count") or 0) > 0],
        [d for d in available if d.get("edges")],
        available,
    ):
        if pool:
            return pool[0]
    raise ValueError("no draft remains eligible for a first inference turn")


def execute_once(
    draft: dict[str, Any],
    source_packet: dict[str, Any],
    system_prompt: str,
    call_fn: Callable[..., Any] = run_role,
) -> dict[str, Any]:
    packet = _packet(draft, source_packet)
    result = call_fn(
        "nexus_gap_fill", system_prompt,
        "Fill only the named gaps in this immutable evidence draft:\n" + json.dumps(packet, ensure_ascii=False),
        timeout=360,
    )
    ran = getattr(result, "exit_code", -9) != -9
    entry = {
        "topic_id": packet["topic_id"],
        "base_draft_digest": _digest(draft),
        "source_packet_digest": _digest(source_packet),
        "created_at": _now(),
        "artifact_class": "exploration_only",
        "decision_eligible": False,
        "model_used": getattr(result, "model_used", getattr(result, "agent", None)),
        "inference_turns": 1 if ran else 0,
        "status": "failed" if ran else "blocked",
        "route_note": str(getattr(result, "route_note", ""))[:500],
    }
    if getattr(result, "exit_code", 1) != 0 or not isinstance(getattr(result, "parsed", None), dict):
        entry["error"] = str(getattr(result, "error", "unparseable model output") or "unparseable model output")[:500]
        return entry
    proposal = _normalize_response(result.parsed, draft)
    errors = _proposal_errors(proposal, draft, source_packet)
    if errors:
        entry["error"] = "; ".join(errors[:12])
        return entry
    entry["status"] = "proposed"
    entry["proposal"] = proposal
    entry["proposal_digest"] = _digest(proposal)
    return entry


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Run one bounded Nexus gap-fill turn")
    parser.add_argument("--drafts", type=Path, default=root / "Dashboard/nexus_evidence_drafts.json")
    parser.add_argument("--source-packets", type=Path, default=root / "Dashboard/nexus_source_packets.json")
    parser.add_argument("--output", type=Path, default=root / "Dashboard/nexus_gap_fills.json")
    parser.add_argument("--prompt", type=Path, default=root / "scripts/nexus/prompts/evidence_gap_fill_system.md")
    parser.add_argument("--topic")
    parser.add_argument("--agent", choices=("claude", "gemini", "codex"))
    parser.add_argument("--timeout", type=int, default=360)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        draft_payload = json.loads(args.drafts.read_text(encoding="utf-8"))
        draft_map = {(d.get("source_topic") or {}).get("topic_id"): d for d in (draft_payload.get("drafts") or [])}
        source_payload = json.loads(args.source_packets.read_text(encoding="utf-8"))
        source_map = {p.get("topic_id"): p for p in (source_payload.get("packets") or [])}
        ledger = load_ledger(args.output)
        if args.check:
            errors = validate_ledger(ledger, draft_map, source_map)
            if errors:
                print("[nexus-gap-fill] INVALID: " + "; ".join(errors[:12]), file=sys.stderr)
                return 1
            print(f"[nexus-gap-fill] VALID: {len(ledger.get('entries') or [])} entries")
            return 0
        draft = select_draft(draft_payload, ledger, args.topic)
        topic_id = (draft.get("source_topic") or {}).get("topic_id")
        source_packet = source_map.get(topic_id)
        if not source_packet:
            raise ValueError(f"source packet not found for topic: {topic_id}")
        if source_packet.get("base_draft_digest") != _digest(draft):
            raise ValueError(f"source packet is stale for topic: {topic_id}")
        if args.dry_run:
            print(json.dumps(_packet(draft, source_packet), ensure_ascii=False, indent=2))
            return 0
        selected_call = run_role
        if args.agent:
            selected_call = lambda role, system, user, timeout: run_with_fallback(
                args.agent, role, system, user, timeout=timeout
            )
        entry = execute_once(
            draft, source_packet, args.prompt.read_text(encoding="utf-8"),
            call_fn=lambda role, system, user, timeout: selected_call(
                role, system, user, timeout=args.timeout
            ),
        )
        ledger.setdefault("entries", []).append(entry)
        ledger["updated_at"] = _now()
        errors = validate_ledger(ledger, draft_map, source_map)
        if errors:
            raise ValueError("ledger validation failed: " + "; ".join(errors[:8]))
        _atomic_json(args.output, ledger)
        print(f"[nexus-gap-fill] {entry['status']}: {entry['topic_id']} model={entry.get('model_used')} turns={entry['inference_turns']}")
        return 0 if entry["status"] == "proposed" else 1
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"[nexus-gap-fill] FATAL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
