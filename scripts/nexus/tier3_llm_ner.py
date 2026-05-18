"""Tier 3 — Haiku 4.5 LLM named-entity / relationship extraction.

Reads MD reports (deep-dive, sector, news, postmortem), prompts Haiku 4.5 with
prompt-cached system instruction, parses JSON triples, applies two-stage alias
canonicalization, and emits Node + Edge lists.

Cost containment:
  - SHA256 cache per (md_path + mtime). Cached docs cost $0 on rerun.
  - `--backfill-limit` (default 10) caps documents per run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from .schema import (
    Edge,
    EdgeType,
    Node,
    NodeType,
    make_catalyst_id,
    make_narrative_id,
    make_sector_id,
    make_theme_id,
    make_ticker_id,
)
from .tier1_loaders import load_ticker_universe


VALID_EDGE_TYPES = {
    # Membership / classification
    "BELONGS_TO_THEME", "BELONGS_TO_SECTOR", "BELONGS_TO_NARRATIVE",
    # Catalyst
    "CATALYST_FOR", "BULL_CASE_FOR", "BEAR_CASE_FOR",
    # Generic
    "SUPPLY_CHAIN_HOP", "PEER_OF", "MENTIONED_IN", "BENEFITS",
    # Tier 3 directional supply-chain
    "SUPPLIES_TO", "CUSTOMER_OF", "CONTRACT_MFG_FOR",
    "COMPETES_WITH", "CO_DEVELOPS_WITH",
    # Tier 3 narrative attribution
    "BENEFITS_FROM", "HEADWIND_FROM",
}

# Map LLM-emitted edge labels onto schema EdgeType strings
EDGE_NORMALIZE = {
    "BENEFITS": EdgeType.BENEFITS_FROM.value,   # legacy → new
}

DATE_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _log(msg: str) -> None:
    print(f"[nexus-tier3] {msg}", file=sys.stderr)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        h.update(f.read())
    return h.hexdigest()[:16]


def _cache_key(path: Path) -> str:
    try:
        mtime = int(path.stat().st_mtime_ns)
    except OSError:
        mtime = 0
    raw = f"{path}-{mtime}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _list_mds(reports_dir: Path, since_days: int) -> list[Path]:
    cutoff = datetime.utcnow().date() - timedelta(days=since_days)
    out: list[Path] = []
    if not reports_dir.is_dir():
        return out
    for p in reports_dir.rglob("*.md"):
        if p.name.startswith("."):
            continue
        m = DATE_IN_NAME.search(p.name)
        if m:
            try:
                d = datetime.fromisoformat(m.group(1)).date()
            except ValueError:
                continue
            if d >= cutoff:
                out.append(p)
        else:
            stem = p.stem
            if len(stem) >= 8 and stem[:8].isdigit():
                try:
                    d = datetime.strptime(stem[:8], "%Y%m%d").date()
                except ValueError:
                    continue
                if d >= cutoff:
                    out.append(p)
    return sorted(out, key=lambda p: p.stat().st_mtime, reverse=True)


def _slice_md(text: str, max_chars: int = 24000) -> str:
    """Crude token control — Haiku 4.5 handles ~6k tokens easily, 24k chars ~6k tokens."""
    if len(text) <= max_chars:
        return text
    head = text[: max_chars // 2]
    tail = text[-max_chars // 2 :]
    return head + "\n\n[... TRUNCATED ...]\n\n" + tail


def _build_alias_resolver(cfg: dict[str, Any], project_root: Path):
    from .tier1_loaders import load_ticker_sector_map
    alias_map = {k.lower(): v for k, v in (cfg.get("alias_map") or {}).items()}
    universe = load_ticker_universe(
        str(project_root / cfg["sources"]["heatmap_universe"])
    )
    _ = load_ticker_sector_map  # keep import live for caller convenience

    def resolve(entity_id: str, label: str, etype: str) -> tuple[str, str, str]:
        """Return (canonical_id, canonical_type, status). status ∈ {promoted, provisional}."""
        norm_label = (label or "").strip().lower()
        if norm_label in alias_map:
            cid = alias_map[norm_label]
            return cid, cid.split(":", 1)[0], "promoted"

        if etype == "ticker":
            sym = (label or entity_id.split(":", 1)[-1]).upper()
            if sym in universe:
                return make_ticker_id(sym), "ticker", "promoted"
            return make_narrative_id(label or sym), "narrative", "provisional"

        if etype in ("theme", "narrative", "catalyst", "sector"):
            if etype == "theme":
                return make_theme_id(label or entity_id), "theme", "promoted"
            if etype == "narrative":
                return make_narrative_id(label or entity_id), "narrative", "provisional"
            if etype == "catalyst":
                return make_catalyst_id(label or entity_id), "catalyst", "promoted"
            if etype == "sector":
                return make_sector_id(label or entity_id), "sector", "promoted"

        return make_narrative_id(label or entity_id), "narrative", "provisional"

    return resolve, alias_map, universe


def _call_haiku(client, system_prompt: str, doc: str, model: str, max_tokens: int) -> str:
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {"role": "user", "content": [{"type": "text", "text": doc}]}
        ],
    )
    parts = []
    for block in resp.content:
        if hasattr(block, "text"):
            parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block["text"])
    return "".join(parts)


def _parse_llm_json(raw: str) -> dict[str, Any] | None:
    raw = raw.strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None


def collect(cfg: dict[str, Any], project_root: Path, full: bool = False) -> tuple[list[Node], list[Edge]]:
    tier3_cfg = cfg.get("tier3") or {}
    api_key_env = tier3_cfg.get("api_key_env", "ANTHROPIC_API_KEY")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        _log(f"{api_key_env} not set — skipping Tier 3 (Tier 1+2 already populate graph)")
        return [], []

    try:
        from anthropic import Anthropic
    except ImportError:
        _log("anthropic SDK not installed (pip install anthropic) — skipping Tier 3")
        return [], []

    reports_dir = project_root / cfg["sources"]["reports_dir"]
    cache_dir = project_root / cfg["sources"]["build_log_dir"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    tier3_cache_dir = cache_dir / "tier3"
    tier3_cache_dir.mkdir(parents=True, exist_ok=True)
    rejected_path = cache_dir / "rejected.jsonl"

    since_days = int(tier3_cfg.get("since_days", 30))
    mds = _list_mds(reports_dir, since_days=since_days)
    backfill_limit = int(tier3_cfg.get("backfill_limit", 10))

    system_path = Path(__file__).resolve().parent / "prompts" / "ner_system.md"
    system_prompt = system_path.read_text(encoding="utf-8")

    client = Anthropic(api_key=api_key)
    resolve, alias_map, universe = _build_alias_resolver(cfg, project_root)

    # Defense in depth — same sector scope guard as Tier 2.
    from .tier1_loaders import load_ticker_sector_map
    ticker_sector = load_ticker_sector_map(
        str(project_root / cfg["sources"]["heatmap_universe"])
    )
    narrative_scope: dict[str, list[str]] = cfg.get("narrative_sector_scope") or {}

    def violates_sector_scope(src_id: str, tgt_id: str) -> bool:
        """Reject Tier-3 edges where ticker is linked to a narrative
        whose sector scope excludes that ticker's sector. Same rule as Tier 2."""
        # Identify the (ticker, narrative) pair, regardless of edge direction
        if src_id.startswith("ticker:") and tgt_id.startswith("narrative:"):
            tk, nar = src_id, tgt_id
        elif tgt_id.startswith("ticker:") and src_id.startswith("narrative:"):
            tk, nar = tgt_id, src_id
        else:
            return False   # not a ticker↔narrative edge
        sym = tk.split(":", 1)[-1]
        nar_key = nar.split(":", 1)[-1]
        scope = narrative_scope.get(nar_key)
        if not scope:
            return False   # narrative not registered in scope → allow (LLM-discovered novel)
        sector = ticker_sector.get(sym)
        if not sector:
            return True    # ticker has unknown sector → conservative reject
        return sector not in scope

    all_nodes: list[Node] = []
    all_edges: list[Edge] = []
    nodes_seen: dict[str, Node] = {}
    rejected_lines: list[str] = []

    processed = 0
    for md_path in mds:
        if not full and processed >= backfill_limit:
            break
        ck = _cache_key(md_path)
        cache_file = tier3_cache_dir / f"{ck}.json"
        if cache_file.exists():
            try:
                payload = json.loads(cache_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = None
        else:
            try:
                text = md_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            doc = _slice_md(text, max_chars=int(tier3_cfg.get("window_tokens", 6000)) * 4)
            try:
                raw = _call_haiku(
                    client,
                    system_prompt,
                    doc,
                    model=tier3_cfg.get("model", "claude-haiku-4-5"),
                    max_tokens=int(tier3_cfg.get("max_tokens", 1500)),
                )
            except Exception as e:
                _log(f"haiku call failed for {md_path.name}: {e}")
                continue
            payload = _parse_llm_json(raw) or {}
            cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            processed += 1
            time.sleep(0.2)  # gentle rate-limit cushion

        if not payload:
            continue

        m = DATE_IN_NAME.search(md_path.name)
        path_date = m.group(1) if m else None
        if not path_date and md_path.stem[:8].isdigit():
            try:
                path_date = datetime.strptime(md_path.stem[:8], "%Y%m%d").date().isoformat()
            except ValueError:
                pass

        source_tag = f"tier3:{md_path.relative_to(project_root)}"

        local_id_map: dict[str, tuple[str, str, str]] = {}
        for ent in payload.get("entities") or []:
            if not isinstance(ent, dict):
                continue
            eid = ent.get("id") or ""
            label = ent.get("label") or eid.split(":", 1)[-1]
            etype = (ent.get("type") or "narrative").lower()
            canon_id, canon_type, status = resolve(eid, label, etype)
            local_id_map[eid] = (canon_id, canon_type, status)

            if canon_id not in nodes_seen:
                n = Node(
                    id=canon_id,
                    type=canon_type,
                    label=label,
                    last_seen=path_date,
                    status=status,
                )
                n.sources.add(source_tag)
                nodes_seen[canon_id] = n
                all_nodes.append(n)
            else:
                existing = nodes_seen[canon_id]
                if path_date and (existing.last_seen or "") < path_date:
                    existing.last_seen = path_date
                existing.sources.add(source_tag)
                if status == "promoted":
                    existing.status = "promoted"
            nodes_seen[canon_id].mentions += 1

        for tri in payload.get("triples") or []:
            if not isinstance(tri, dict):
                continue
            src_raw = tri.get("source") or ""
            tgt_raw = tri.get("target") or ""
            edge_label = (tri.get("edge") or "").upper().strip()
            conf = float(tri.get("confidence") or 0.5)

            if edge_label not in VALID_EDGE_TYPES:
                rejected_lines.append(json.dumps({
                    "reason": "unknown_edge",
                    "source_doc": str(md_path.relative_to(project_root)),
                    "triple": tri,
                }, ensure_ascii=False))
                continue
            edge_type = EDGE_NORMALIZE.get(edge_label, edge_label)

            src_canon = local_id_map.get(src_raw)
            tgt_canon = local_id_map.get(tgt_raw)
            if not src_canon or not tgt_canon:
                rejected_lines.append(json.dumps({
                    "reason": "entity_not_declared",
                    "source_doc": str(md_path.relative_to(project_root)),
                    "triple": tri,
                }, ensure_ascii=False))
                continue

            # Defense in depth: cross-domain narrative reject (LLY → HBM etc.)
            if violates_sector_scope(src_canon[0], tgt_canon[0]):
                rejected_lines.append(json.dumps({
                    "reason": "sector_scope_violation",
                    "source_doc": str(md_path.relative_to(project_root)),
                    "src_canon": src_canon[0],
                    "tgt_canon": tgt_canon[0],
                    "edge": edge_label,
                }, ensure_ascii=False))
                continue

            all_edges.append(
                Edge(
                    source=src_canon[0],
                    target=tgt_canon[0],
                    type=edge_type,
                    raw_frequency=1.0,
                    weight=max(conf, 0.2),
                    tier="tier3",
                    confidence=0.85,
                    last_seen=path_date,
                    sources={source_tag},
                )
            )

    if rejected_lines:
        with rejected_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(rejected_lines) + "\n")

    _log(f"processed {processed} new MDs (cache hits: {len(mds) - processed})")
    return all_nodes, all_edges


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="30d", help="e.g. 7d, 30d")
    ap.add_argument("--limit", type=int, default=None, help="override backfill_limit")
    ap.add_argument("--full", action="store_true", help="process all matching MDs")
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    project_root = here.parent.parent
    with open(here / "config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if args.since.endswith("d"):
        cfg["tier3"]["since_days"] = int(args.since[:-1])
    if args.limit is not None:
        cfg["tier3"]["backfill_limit"] = args.limit

    nodes, edges = collect(cfg, project_root, full=args.full)
    print(f"tier3: {len(nodes)} nodes / {len(edges)} edges")
    if args.print and edges:
        for e in edges[:20]:
            print(f"  {e.source} --{e.type}--> {e.target}  (w={e.weight:.2f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
