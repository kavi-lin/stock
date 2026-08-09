#!/usr/bin/env python3
"""Build source-ID packets for text-only Nexus gap filling.

The packet combines canonical source metadata, claim-ledger analyst extracts,
and optional deterministic page retrieval.  It stores only short relevant
passages plus hashes, never a full copyrighted page.  No LLM is used.
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

import requests
from bs4 import BeautifulSoup

from .claim_ledger import canonical_url, read_jsonl, source_domain


SCHEMA_VERSION = 1
MAX_SOURCES = 16
MAX_EXCERPTS_PER_SOURCE = 4
USER_AGENT = "Mozilla/5.0 (compatible; NexusEvidenceBot/1.0; local research)"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest(value: Any) -> str:
    return _sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _source_id(url: str) -> str:
    return "src:" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _excerpt_id(source_id: str, text: str) -> str:
    return "excerpt:" + hashlib.sha1(f"{source_id}|{text}".encode("utf-8")).hexdigest()[:16]


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


def _clean_text(value: Any, limit: int = 700) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def _page_passages(html: str, terms: list[str]) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
        tag.decompose()
    blocks = []
    for tag in soup.find_all(["p", "li"]):
        text = _clean_text(tag.get_text(" ", strip=True), 1200)
        if 80 <= len(text) <= 1200:
            blocks.append(text)
    normalized = "\n".join(blocks)
    needles = [term.casefold() for term in terms if len(term) >= 2]
    ranked = sorted(
        enumerate(blocks),
        key=lambda pair: (sum(term in pair[1].casefold() for term in needles), len(pair[1])),
        reverse=True,
    )
    passages, seen = [], set()
    for _, text in ranked:
        if needles and not any(term in text.casefold() for term in needles):
            continue
        clipped = text[:700]
        if clipped not in seen:
            seen.add(clipped)
            passages.append(clipped)
        if len(passages) >= 3:
            break
    return normalized, passages


def fetch_page(url: str, terms: list[str], timeout: int = 12) -> dict[str, Any]:
    try:
        response = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=timeout,
            allow_redirects=True,
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "html" not in content_type.lower():
            return {"status": "unsupported_content", "http_status": response.status_code, "excerpts": []}
        page_text, passages = _page_passages(response.text, terms)
        return {
            "status": "fetched" if passages else "fetched_no_relevant_excerpt",
            "http_status": response.status_code,
            "resolved_url": canonical_url(response.url),
            "fetched_at": _now(),
            "content_digest": _sha(page_text),
            "excerpts": passages,
        }
    except requests.RequestException as exc:
        return {"status": "fetch_failed", "error": str(exc)[:240], "excerpts": []}


def _add_excerpt(source: dict[str, Any], text: str, provenance: str, *, claim_id: str | None = None) -> str | None:
    text = _clean_text(text)
    if len(text) < 20:
        return None
    excerpt_id = _excerpt_id(source["source_id"], text)
    if any(row["excerpt_id"] == excerpt_id for row in source["excerpts"]):
        return excerpt_id
    # Reserve one slot for text fetched from the page. Analyst extracts are
    # useful discovery hints, but must never crowd out the stronger evidence
    # required by the gap-fill gate.
    limit = MAX_EXCERPTS_PER_SOURCE if provenance == "fetched_page" else MAX_EXCERPTS_PER_SOURCE - 1
    if len(source["excerpts"]) >= limit:
        return None
    source["excerpts"].append({
        "excerpt_id": excerpt_id,
        "text": text,
        "text_digest": _sha(text),
        "provenance": provenance,
        "verbatim_page_text": provenance == "fetched_page",
        "claim_id": claim_id,
    })
    return excerpt_id


def build_packet(
    draft: dict[str, Any],
    claims_by_id: dict[str, dict[str, Any]],
    *,
    fetch: bool = False,
    fetch_fn: Callable[[str, list[str], int], dict[str, Any]] = fetch_page,
    timeout: int = 12,
) -> dict[str, Any]:
    topic = draft.get("source_topic") or {}
    terms = [str(topic.get("label") or ""), *(topic.get("tickers") or [])]
    source_map: dict[str, dict[str, Any]] = {}

    def ensure_source(raw: dict[str, Any]) -> dict[str, Any] | None:
        url = canonical_url(raw.get("url"))
        if not url:
            return None
        sid = _source_id(url)
        source = source_map.setdefault(sid, {
            "source_id": sid,
            "source_key": raw.get("source_key"),
            "url": url,
            "domain": source_domain(url),
            "headline": _clean_text(raw.get("headline"), 180),
            "published": str(raw.get("published") or "")[:10],
            "retrieval": {"status": "not_fetched"},
            "excerpts": [],
        })
        return source

    for raw in draft.get("evidence") or []:
        ensure_source(raw)

    relation_rows = []
    for edge in (draft.get("edges") or []) + (draft.get("context_edges") or []):
        citations = []
        relation_claims = []
        for claim_id in edge.get("claim_ids") or []:
            claim = claims_by_id.get(claim_id)
            if not claim:
                continue
            relation_claims.append(claim)
            for raw in claim.get("evidence") or []:
                source = ensure_source(raw)
                if not source:
                    continue
                excerpt_ids = []
                for snippet in raw.get("evidence_snippets") or []:
                    eid = _add_excerpt(source, snippet, "claim_analyst_extract", claim_id=claim_id)
                    if eid:
                        excerpt_ids.append(eid)
                citations.append({"source_id": source["source_id"], "excerpt_ids": excerpt_ids})
        unique_sources = {row["source_id"] for row in citations}
        domains = {source_map[sid]["domain"] for sid in unique_sources if sid in source_map}
        if len(unique_sources) >= 2 and len(domains) >= 2:
            level = "corroborated_claim"
        elif unique_sources:
            level = "single_source_claim"
        else:
            level = "unsupported"
        relation_rows.append({
            "edge_key": f"{edge.get('from')}|{edge.get('rel')}|{edge.get('to')}",
            "from": edge.get("from"), "to": edge.get("to"), "rel": edge.get("rel"),
            "base_evidence_level": edge.get("evidence_level"),
            "packet_evidence_level": level,
            "source_count": len(unique_sources),
            "source_domain_count": len(domains),
            "claim_ids": sorted({c.get("claim_id") for c in relation_claims if c.get("claim_id")}),
            "citations": citations,
        })

    sources = list(source_map.values())[:MAX_SOURCES]
    allowed_source_ids = {source["source_id"] for source in sources}
    for relation in relation_rows:
        relation["citations"] = [c for c in relation["citations"] if c["source_id"] in allowed_source_ids]
        cited_sources = {c["source_id"] for c in relation["citations"]}
        cited_domains = {
            source_map[sid]["domain"] for sid in cited_sources
            if sid in source_map and source_map[sid].get("domain")
        }
        relation["source_count"] = len(cited_sources)
        relation["source_domain_count"] = len(cited_domains)
        relation["packet_evidence_level"] = (
            "corroborated_claim" if len(cited_sources) >= 2 and len(cited_domains) >= 2
            else "single_source_claim" if cited_sources else "unsupported"
        )

    if fetch:
        for source in sources:
            retrieval = fetch_fn(source["url"], terms, timeout)
            source["retrieval"] = {k: v for k, v in retrieval.items() if k != "excerpts"}
            for passage in retrieval.get("excerpts") or []:
                _add_excerpt(source, passage, "fetched_page")

    return {
        "packet_id": "packet:" + str(topic.get("topic_id") or "topic:unknown").split(":", 1)[-1],
        "topic_id": topic.get("topic_id"),
        "topic_label": topic.get("label"),
        "base_draft_digest": _digest(draft),
        "generated_at": _now(),
        "known_gaps": list(draft.get("known_gaps") or []),
        "immutable_nodes": [
            {"id": n.get("id"), "ticker": n.get("ticker"), "layer": n.get("layer")}
            for n in (draft.get("nodes") or [])
        ],
        "immutable_edges": [
            {"from": e.get("from"), "to": e.get("to"), "rel": e.get("rel"), "evidence_level": e.get("evidence_level")}
            for e in (draft.get("edges") or []) + (draft.get("context_edges") or [])
        ],
        "sources": sources,
        "relation_evidence": relation_rows,
        "quality": {
            "source_count": len(sources),
            "source_domain_count": len({s["domain"] for s in sources if s["domain"]}),
            "fetched_source_count": sum(s["retrieval"].get("status") == "fetched" for s in sources),
            "verbatim_excerpt_count": sum(
                e["verbatim_page_text"] for s in sources for e in s["excerpts"]
            ),
            "corroborated_relation_count": sum(
                r["packet_evidence_level"] == "corroborated_claim" for r in relation_rows
            ),
        },
    }


def build_payload(
    draft_payload: dict[str, Any], claims: list[dict[str, Any]], *,
    fetch_topic: str | None = None, timeout: int = 12,
    fetch_fn: Callable[[str, list[str], int], dict[str, Any]] = fetch_page,
) -> dict[str, Any]:
    claims_by_id = {c.get("claim_id"): c for c in claims if c.get("claim_id")}
    packets = [
        build_packet(
            draft, claims_by_id,
            fetch=bool(fetch_topic and (draft.get("source_topic") or {}).get("topic_id") == fetch_topic),
            fetch_fn=fetch_fn, timeout=timeout,
        )
        for draft in (draft_payload.get("drafts") or [])
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_class": "exploration_only",
        "decision_use": "forbidden",
        "generated_at": _now(),
        "counts": {
            "packets": len(packets),
            "sources": sum(len(p["sources"]) for p in packets),
            "fetched_sources": sum(p["quality"]["fetched_source_count"] for p in packets),
            "verbatim_excerpts": sum(p["quality"]["verbatim_excerpt_count"] for p in packets),
        },
        "packets": packets,
    }


def validate_payload(payload: dict[str, Any], drafts: dict[str, dict[str, Any]] | None = None) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be 1")
    if payload.get("artifact_class") != "exploration_only" or payload.get("decision_use") != "forbidden":
        errors.append("source packets must remain exploration-only and forbidden for decisions")
    packets = payload.get("packets")
    if not isinstance(packets, list):
        return errors + ["packets must be a list"]
    packet_ids, topic_ids = [], []
    for i, packet in enumerate(packets, 1):
        packet_ids.append(packet.get("packet_id")); topic_ids.append(packet.get("topic_id"))
        draft = drafts.get(packet.get("topic_id")) if drafts else None
        if draft and packet.get("base_draft_digest") != _digest(draft):
            errors.append(f"packet {i}: base_draft_digest mismatch")
        sources = packet.get("sources") or []
        source_ids = [s.get("source_id") for s in sources]
        if len(source_ids) != len(set(source_ids)):
            errors.append(f"packet {i}: duplicate source_id")
        excerpt_ids = set()
        excerpt_owner: dict[str, str] = {}
        for j, source in enumerate(sources, 1):
            if canonical_url(source.get("url")) != source.get("url"):
                errors.append(f"packet {i} source {j}: URL is not canonical")
            if source.get("source_id") != _source_id(source.get("url") or ""):
                errors.append(f"packet {i} source {j}: source_id mismatch")
            for excerpt in source.get("excerpts") or []:
                eid, text = excerpt.get("excerpt_id"), excerpt.get("text") or ""
                if eid in excerpt_ids:
                    errors.append(f"packet {i}: duplicate excerpt_id")
                excerpt_ids.add(eid)
                excerpt_owner[eid] = source.get("source_id")
                if excerpt.get("text_digest") != _sha(text) or eid != _excerpt_id(source["source_id"], text):
                    errors.append(f"packet {i}: excerpt hash mismatch")
                if excerpt.get("verbatim_page_text") != (excerpt.get("provenance") == "fetched_page"):
                    errors.append(f"packet {i}: invalid verbatim flag")
                if excerpt.get("provenance") == "fetched_page" and source.get("retrieval", {}).get("status") != "fetched":
                    errors.append(f"packet {i} source {j}: fetched excerpt without fetched retrieval")
        for j, relation in enumerate(packet.get("relation_evidence") or [], 1):
            cited_sources = {c.get("source_id") for c in relation.get("citations") or []}
            if cited_sources - set(source_ids):
                errors.append(f"packet {i} relation {j}: unknown source citation")
            for citation in relation.get("citations") or []:
                for excerpt_id in citation.get("excerpt_ids") or []:
                    if excerpt_id not in excerpt_ids:
                        errors.append(f"packet {i} relation {j}: unknown excerpt citation")
                    elif excerpt_owner.get(excerpt_id) != citation.get("source_id"):
                        errors.append(f"packet {i} relation {j}: excerpt/source mismatch")
            domains = {s["domain"] for s in sources if s["source_id"] in cited_sources and s.get("domain")}
            expected = "corroborated_claim" if len(cited_sources) >= 2 and len(domains) >= 2 else ("single_source_claim" if cited_sources else "unsupported")
            if relation.get("packet_evidence_level") != expected:
                errors.append(f"packet {i} relation {j}: evidence level mismatch")
        expected_quality = {
            "source_count": len(sources),
            "source_domain_count": len({s.get("domain") for s in sources if s.get("domain")}),
            "fetched_source_count": sum(s.get("retrieval", {}).get("status") == "fetched" for s in sources),
            "verbatim_excerpt_count": sum(
                e.get("verbatim_page_text") is True for s in sources for e in (s.get("excerpts") or [])
            ),
            "corroborated_relation_count": sum(
                r.get("packet_evidence_level") == "corroborated_claim"
                for r in (packet.get("relation_evidence") or [])
            ),
        }
        if packet.get("quality") != expected_quality:
            errors.append(f"packet {i}: quality counts mismatch")
    if len(packet_ids) != len(set(packet_ids)) or len(topic_ids) != len(set(topic_ids)):
        errors.append("duplicate packet_id or topic_id")
    if int((payload.get("counts") or {}).get("packets") or 0) != len(packets):
        errors.append("counts.packets mismatch")
    expected_counts = {
        "packets": len(packets),
        "sources": sum(len(p.get("sources") or []) for p in packets),
        "fetched_sources": sum((p.get("quality") or {}).get("fetched_source_count") or 0 for p in packets),
        "verbatim_excerpts": sum((p.get("quality") or {}).get("verbatim_excerpt_count") or 0 for p in packets),
    }
    if payload.get("counts") != expected_counts:
        errors.append("aggregate counts mismatch")
    return errors


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Build deterministic Nexus source packets")
    parser.add_argument("--drafts", type=Path, default=root / "Dashboard/nexus_evidence_drafts.json")
    parser.add_argument("--claims", type=Path, default=root / "nexus/claim_ledger.jsonl")
    parser.add_argument("--output", type=Path, default=root / "Dashboard/nexus_source_packets.json")
    parser.add_argument("--fetch-topic")
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        drafts_payload = json.loads(args.drafts.read_text(encoding="utf-8"))
        draft_map = {(d.get("source_topic") or {}).get("topic_id"): d for d in (drafts_payload.get("drafts") or [])}
        if args.check:
            payload = json.loads(args.output.read_text(encoding="utf-8"))
        else:
            payload = build_payload(
                drafts_payload, read_jsonl(args.claims),
                fetch_topic=args.fetch_topic, timeout=args.timeout,
            )
        errors = validate_payload(payload, draft_map)
        if errors:
            print("[nexus-source-packets] INVALID: " + "; ".join(errors[:12]), file=sys.stderr)
            return 1
        if not args.check:
            _atomic_json(args.output, payload)
        print(
            f"[nexus-source-packets] VALID: {len(payload.get('packets') or [])} packets / "
            f"{(payload.get('counts') or {}).get('verbatim_excerpts', 0)} verbatim excerpts"
        )
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"[nexus-source-packets] FATAL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
