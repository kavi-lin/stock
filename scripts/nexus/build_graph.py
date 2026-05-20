#!/usr/bin/env python3
"""Project Nexus V3.0 — knowledge graph builder.

Reads Tier 1 (structured JSON) + Tier 2 (regex) + Tier 3 (LLM NER) outputs,
applies multi-dim decay + confidence weighting, computes centrality, prunes,
emits Dashboard/nexus_graph.json.

Usage:
    python3 scripts/nexus/build_graph.py --tier 1
    python3 scripts/nexus/build_graph.py --tier 1,2,3 --full
    python3 scripts/nexus/build_graph.py --tier 1 --dry-run
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, date
from pathlib import Path
from typing import Any

import yaml

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.nexus.schema import (  # noqa: E402
    EDGE_TO_DECAY_KEY,
    Edge,
    EdgeType,
    Node,
    NodeType,
)
from scripts.nexus import tier1_loaders  # noqa: E402
from scripts.nexus.pagerank_lite import pagerank_lite, degree_centrality  # noqa: E402


def _log(msg: str) -> None:
    print(f"[nexus] {msg}", file=sys.stderr)


def load_config() -> dict[str, Any]:
    cfg_path = THIS_DIR / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def half_life_for_edge(edge_type: str, cfg: dict[str, Any]) -> float:
    try:
        key = EDGE_TO_DECAY_KEY[EdgeType(edge_type)]
    except ValueError:
        key = "default"
    return float(cfg["decay_strategies"].get(key, cfg["decay_strategies"]["default"]))


def decay_factor(age_days: float, half_life: float) -> float:
    if half_life <= 0:
        return 1.0
    return 0.5 ** (age_days / half_life)


def age_days(last_seen: str | None, anchor: date) -> float:
    if not last_seen:
        return 0.0
    try:
        d = datetime.fromisoformat(last_seen[:10]).date()
    except ValueError:
        return 0.0
    return max((anchor - d).days, 0)


def merge_edges(edges: list[Edge]) -> list[Edge]:
    """Combine edges with identical (source, target, type), summing frequencies."""
    merged: dict[tuple[str, str, str], Edge] = {}
    for e in edges:
        k = e.key
        if k in merged:
            cur = merged[k]
            cur.raw_frequency += e.raw_frequency
            cur.weight = max(cur.weight, e.weight)
            cur.sources.update(e.sources)
            if (e.last_seen or "") > (cur.last_seen or ""):
                cur.last_seen = e.last_seen
        else:
            merged[k] = Edge(
                source=e.source,
                target=e.target,
                type=e.type,
                weight=e.weight,
                raw_frequency=e.raw_frequency,
                tier=e.tier,
                confidence=e.confidence,
                last_seen=e.last_seen,
                sources=set(e.sources),
            )
    return list(merged.values())


def merge_nodes(nodes: list[Node]) -> dict[str, Node]:
    merged: dict[str, Node] = {}
    for n in nodes:
        if n.id in merged:
            cur = merged[n.id]
            cur.mentions += n.mentions
            cur.sources.update(n.sources)
            if (n.last_seen or "") > (cur.last_seen or ""):
                cur.last_seen = n.last_seen
            for k, v in n.metadata.items():
                cur.metadata.setdefault(k, v)
        else:
            merged[n.id] = Node(
                id=n.id,
                type=n.type,
                label=n.label,
                last_seen=n.last_seen,
                mentions=n.mentions,
                sources=set(n.sources),
                metadata=dict(n.metadata),
                status=n.status,
            )
    return merged


def apply_decay_and_confidence(
    edges: list[Edge], cfg: dict[str, Any], anchor: date
) -> list[Edge]:
    for e in edges:
        hl = half_life_for_edge(e.type, cfg)
        decay = decay_factor(age_days(e.last_seen, anchor), hl)
        tier_conf = cfg["tier_confidence"].get(e.tier, 1.0)
        e.confidence = tier_conf
        base = max(e.weight, 0.0) * tier_conf
        e.weight = base * decay * max(math.log1p(e.raw_frequency), 1.0)
    return edges


def prune(
    nodes: dict[str, Node], edges: list[Edge], cfg: dict[str, Any]
) -> tuple[dict[str, Node], list[Edge], dict[str, int]]:
    stats = {"dropped_edges_low_weight": 0, "dropped_isolated_nodes": 0,
             "dropped_provisional_low_mentions": 0, "dropped_for_cap": 0}
    min_w = float(cfg["min_edge_weight"])
    promo_min = int(cfg["provisional_promotion_doc_count"])

    kept_edges = []
    for e in edges:
        if e.weight < min_w:
            stats["dropped_edges_low_weight"] += 1
            continue
        kept_edges.append(e)

    edges = kept_edges
    degree: dict[str, int] = defaultdict(int)
    for e in edges:
        degree[e.source] += 1
        degree[e.target] += 1

    survivors: dict[str, Node] = {}
    for nid, n in nodes.items():
        deg = degree.get(nid, 0)
        if deg == 0:
            stats["dropped_isolated_nodes"] += 1
            continue
        if n.status == "provisional" and len(n.sources) < promo_min:
            stats["dropped_provisional_low_mentions"] += 1
            continue
        survivors[nid] = n

    edges = [e for e in edges if e.source in survivors and e.target in survivors]

    max_n = int(cfg["max_nodes"])
    if len(survivors) > max_n:
        edge_strength: dict[str, float] = defaultdict(float)
        for e in edges:
            edge_strength[e.source] += e.weight
            edge_strength[e.target] += e.weight
        ranked = sorted(survivors.values(), key=lambda n: edge_strength.get(n.id, 0.0), reverse=True)
        kept_ids = {n.id for n in ranked[:max_n]}
        stats["dropped_for_cap"] = len(survivors) - max_n
        survivors = {nid: n for nid, n in survivors.items() if nid in kept_ids}
        edges = [e for e in edges if e.source in survivors and e.target in survivors]

    return survivors, edges, stats


def compute_centrality(
    nodes: dict[str, Node], edges: list[Edge]
) -> dict[str, dict[str, float]]:
    edge_triples = [(e.source, e.target, e.weight) for e in edges]
    try:
        import networkx as nx  # type: ignore
        G = nx.Graph()
        for nid in nodes:
            G.add_node(nid)
        for s, t, w in edge_triples:
            G.add_edge(s, t, weight=w)
        deg = nx.degree_centrality(G)
        try:
            pr = nx.pagerank(G, weight="weight", alpha=0.85, max_iter=50, tol=1e-4)
        except Exception as e:
            _log(f"networkx pagerank failed ({e}); fallback to pagerank_lite")
            pr = pagerank_lite(edge_triples)
        return {nid: {"degree": deg.get(nid, 0.0), "pagerank": pr.get(nid, 0.0)} for nid in nodes}
    except ImportError:
        _log("networkx not installed; using pagerank_lite + degree fallback")
        deg = degree_centrality(edge_triples)
        pr = pagerank_lite(edge_triples)
        return {nid: {"degree": deg.get(nid, 0.0), "pagerank": pr.get(nid, 0.0)} for nid in nodes}


def _to_ticker_centric(
    nodes: dict[str, Node],
    edges: list[Edge],
    cfg: dict[str, Any],
) -> tuple[dict[str, Node], list[Edge], dict[str, int]]:
    """Collapse a mixed-type graph into a ticker-only graph.

    Aggregates non-ticker neighbours of each ticker into that ticker's
    metadata so the UI tooltip can surface news / themes / sector / narrative
    context without the graph itself rendering those as standalone nodes.

    Returns (survivors, ticker_only_edges, stats). Original `nodes`/`edges`
    are not mutated; this rebuilds fresh dataclass instances for survivors.
    """
    per_ticker_news_cap = int(cfg.get("ticker_centric_recent_news_per_ticker", 8))

    # Index by id for O(1) neighbour lookup
    by_id = nodes  # already dict[id -> Node]

    # adjacency: ticker_id -> list of (other_node_id, edge)
    adj: dict[str, list[tuple[str, Edge]]] = defaultdict(list)
    for e in edges:
        s = by_id.get(e.source); t = by_id.get(e.target)
        if not s or not t:
            continue
        if s.type == "ticker" and t.type != "ticker":
            adj[e.source].append((e.target, e))
        elif t.type == "ticker" and s.type != "ticker":
            adj[e.target].append((e.source, e))

    # Build per-ticker rolled-up metadata
    stats = {"news_attached": 0, "themes_attached": 0, "narratives_attached": 0,
             "theses_attached": 0, "sectors_attached": 0}

    for tid, node in list(by_id.items()):
        if node.type != "ticker":
            continue
        recent_news: list[dict[str, Any]] = []
        themes: list[str] = []
        narratives: list[str] = []
        theses: list[str] = []
        sector: str | None = None

        for nbr_id, e in adj.get(tid, []):
            nbr = by_id.get(nbr_id)
            if not nbr:
                continue
            md = nbr.metadata or {}
            if nbr.type == "catalyst":
                recent_news.append({
                    "id": nbr.id,
                    "headline": nbr.label,
                    "verdict": md.get("verdict") or md.get("news_type") or "",
                    "net_impact": md.get("net_impact"),
                    "published": nbr.last_seen,
                    "edge_type": e.type,
                    "weight": round(float(e.weight or 0.0), 4),
                })
            elif nbr.type == "theme":
                themes.append(nbr.label)
            elif nbr.type == "narrative":
                narratives.append(nbr.label)
            elif nbr.type == "thesis":
                theses.append(nbr.label)
            elif nbr.type == "sector":
                # there can be only one sector per ticker; keep the heaviest edge
                if sector is None:
                    sector = nbr.label

        # Sort news by recency desc, then by |net_impact|, cap to N. The cap is
        # what keeps the JSON below the 5 MB ceiling — without it a high-mention
        # ticker like NVDA accrues 100+ items.
        def _news_key(x: dict[str, Any]) -> tuple:
            pub = x.get("published") or ""
            try:
                impact = abs(float(x.get("net_impact") or 0.0))
            except (TypeError, ValueError):
                impact = 0.0
            return (pub, impact)
        recent_news.sort(key=_news_key, reverse=True)
        recent_news = recent_news[:per_ticker_news_cap]

        # Dedupe themes / narratives / theses by label preserving order
        def _uniq(xs: list[str]) -> list[str]:
            seen, out = set(), []
            for x in xs:
                if x and x not in seen:
                    seen.add(x); out.append(x)
            return out

        themes = _uniq(themes)[:12]
        narratives = _uniq(narratives)[:12]
        theses = _uniq(theses)[:6]

        # Mutate metadata in place — node.to_json() will serialize this.
        node.metadata = {
            **(node.metadata or {}),
            "recent_news": recent_news,
            "themes": themes,
            "narratives": narratives,
            "theses": theses,
            "sector": sector or (node.metadata or {}).get("sector"),
        }
        stats["news_attached"]      += len(recent_news)
        stats["themes_attached"]    += len(themes)
        stats["narratives_attached"]+= len(narratives)
        stats["theses_attached"]    += len(theses)
        if sector:
            stats["sectors_attached"] += 1

    # Filter survivors to ticker nodes only
    survivors = {nid: n for nid, n in by_id.items() if n.type == "ticker"}

    # Keep only ticker↔ticker edges
    ticker_ids = set(survivors)
    ticker_only_edges = [
        e for e in edges
        if e.source in ticker_ids and e.target in ticker_ids
    ]

    # Synthesize CO_THEME edges between tickers sharing a theme/narrative. The
    # raw pipeline only emits PEER_OF / SUPPLIES_TO directly, leaving most
    # tickers isolated once non-ticker nodes are dropped. Theme co-membership
    # is a legitimate ticker↔ticker relation; capping per-theme prevents the
    # well-known "everyone in AI" 200-clique explosion.
    co_theme_cap_tickers_per_theme = 12
    co_theme_cap_themes_per_ticker = 3
    # Build theme/narrative -> [(ticker_id, edge_weight)] map
    grp: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for e in edges:
        s = by_id.get(e.source); t = by_id.get(e.target)
        if not s or not t:
            continue
        if s.type == "ticker" and t.type in ("theme", "narrative"):
            grp[t.id].append((s.id, float(e.weight or 0.0)))
        elif t.type == "ticker" and s.type in ("theme", "narrative"):
            grp[s.id].append((t.id, float(e.weight or 0.0)))

    # Cap memberships per ticker (only top-K themes per ticker get CO_THEME edges)
    ticker_top_themes: dict[str, set[str]] = defaultdict(set)
    by_ticker_themes: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for theme_id, members in grp.items():
        for tid, w in members:
            by_ticker_themes[tid].append((theme_id, w))
    for tid, themes_w in by_ticker_themes.items():
        themes_w.sort(key=lambda x: x[1], reverse=True)
        ticker_top_themes[tid] = {th for th, _ in themes_w[:co_theme_cap_themes_per_ticker]}

    seen_pairs: set[tuple[str, str]] = set()
    synth_edges: list[Edge] = []
    for theme_id, members in grp.items():
        # Limit per-theme participants to the heaviest-edge tickers
        members = sorted(members, key=lambda x: x[1], reverse=True)[:co_theme_cap_tickers_per_theme]
        for i, (a, wa) in enumerate(members):
            if theme_id not in ticker_top_themes.get(a, set()):
                continue
            for b, wb in members[i + 1:]:
                if theme_id not in ticker_top_themes.get(b, set()):
                    continue
                key = (a, b) if a < b else (b, a)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                synth_edges.append(Edge(
                    source=key[0], target=key[1], type="CO_THEME",
                    weight=round(min(wa, wb), 4),
                    raw_frequency=1.0, tier="synth",
                    confidence=0.6, last_seen=None,
                    sources={f"co_theme:{theme_id}"},
                ))
    ticker_only_edges.extend(synth_edges)
    stats["co_theme_synthesized"] = len(synth_edges)

    stats["ticker_nodes"]      = len(survivors)
    stats["ticker_edges"]      = len(ticker_only_edges)
    return survivors, ticker_only_edges, stats


def collect_tier1(cfg: dict[str, Any]) -> tuple[list[Node], list[Edge]]:
    sources = cfg["sources"]
    universe = tier1_loaders.load_ticker_universe(
        str(PROJECT_ROOT / sources["heatmap_universe"])
    )
    _log(f"ticker universe: {len(universe)} symbols")

    all_nodes: list[Node] = []
    all_edges: list[Edge] = []

    n, e = tier1_loaders.load_theme_detector(
        str(PROJECT_ROOT / sources["theme_detector_glob"]), universe
    )
    _log(f"theme_detector: +{len(n)} nodes / +{len(e)} edges")
    all_nodes += n
    all_edges += e

    n, e = tier1_loaders.load_event_index(
        str(PROJECT_ROOT / sources["event_index"]), universe
    )
    _log(f"event_index: +{len(n)} nodes / +{len(e)} edges")
    all_nodes += n
    all_edges += e

    n, e = tier1_loaders.load_news_digests(
        str(PROJECT_ROOT / sources["news_logs_glob"]), universe
    )
    _log(f"news_digests: +{len(n)} nodes / +{len(e)} edges")
    all_nodes += n
    all_edges += e

    # Break News (V3.1) — closed/partial_closed items only; dedupes against
    # daily digest by url_hash so the same URL doesn't double-promote.
    bn_dir = sources.get("break_news_dir")
    if bn_dir:
        digest_hashes: set[str] = set()
        import glob as _glob
        for p in _glob.glob(str(PROJECT_ROOT / sources["news_logs_glob"])):
            d = tier1_loaders._safe_read_json(p)
            if not d:
                continue
            for v in (d.get("verdicts") or []):
                h = v.get("url_hash") or v.get("url")
                if h:
                    digest_hashes.add(h)
        n, e = tier1_loaders.load_break_news(
            str(PROJECT_ROOT / bn_dir), universe,
            digest_url_hashes=digest_hashes,
        )
        _log(f"break_news: +{len(n)} nodes / +{len(e)} edges")
        all_nodes += n
        all_edges += e

    n, e = tier1_loaders.load_theses(str(PROJECT_ROOT / sources["thesis_dir"]))
    _log(f"theses: +{len(n)} nodes / +{len(e)} edges")
    all_nodes += n
    all_edges += e

    n, e = tier1_loaders.load_dashboard_data(
        str(PROJECT_ROOT / sources["dashboard_data"]), universe
    )
    _log(f"dashboard_data: +{len(n)} nodes / +{len(e)} edges")
    all_nodes += n
    all_edges += e

    return all_nodes, all_edges


def collect_tier2(cfg: dict[str, Any]) -> tuple[list[Node], list[Edge]]:
    try:
        from scripts.nexus import tier2_regex
        return tier2_regex.collect(cfg, PROJECT_ROOT)
    except (ImportError, AttributeError) as e:
        _log(f"tier 2 unavailable: {e}")
        return [], []


def collect_tier3(cfg: dict[str, Any], full: bool) -> tuple[list[Node], list[Edge]]:
    try:
        from scripts.nexus import tier3_llm_ner
        return tier3_llm_ner.collect(cfg, PROJECT_ROOT, full=full)
    except (ImportError, AttributeError) as e:
        _log(f"tier 3 unavailable: {e}")
        return [], []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", default="1", help="Comma-separated: 1, 2, 3 (e.g. '1,2,3')")
    ap.add_argument("--dry-run", action="store_true", help="Print stats, write nothing")
    ap.add_argument("--full", action="store_true", help="Tier 3: process full backfill")
    args = ap.parse_args()

    cfg = load_config()
    tiers = {t.strip() for t in args.tier.split(",") if t.strip()}
    enabled = cfg["tiers_enabled"]

    nodes: list[Node] = []
    edges: list[Edge] = []

    # Tier 2 stashes a narrative-attribution audit on a sentinel node id;
    # harvest it here before merge_nodes so it never reaches the rendered graph.
    tier2_audit: dict[str, Any] = {}

    if "1" in tiers and enabled.get("tier1", True):
        n, e = collect_tier1(cfg)
        nodes += n
        edges += e
    if "2" in tiers and enabled.get("tier2", True):
        n, e = collect_tier2(cfg)
        # Pull out audit sentinel
        kept = []
        for node in n:
            if node.id == "__tier2_audit__":
                tier2_audit = node.metadata.get("counts", {}) or {}
            else:
                kept.append(node)
        n = kept
        _log(f"tier2 regex: +{len(n)} nodes / +{len(e)} edges  (audit narratives: {len(tier2_audit)})")
        nodes += n
        edges += e
    if "3" in tiers and enabled.get("tier3", True):
        n, e = collect_tier3(cfg, full=args.full)
        _log(f"tier3 LLM: +{len(n)} nodes / +{len(e)} edges")
        nodes += n
        edges += e

    merged_nodes = merge_nodes(nodes)
    merged_edges = merge_edges(edges)
    _log(f"after merge: {len(merged_nodes)} nodes / {len(merged_edges)} edges")

    anchor = datetime.utcnow().date()
    merged_edges = apply_decay_and_confidence(merged_edges, cfg, anchor)

    survivors, edges_out, prune_stats = prune(merged_nodes, merged_edges, cfg)
    _log(
        "prune: " + ", ".join(f"{k}={v}" for k, v in prune_stats.items())
    )

    # ─── P4: narrative attribution audit + auto-quarantine ─────────────
    # For every narrative node, count distinct tickers linked to it. If any
    # narrative links to >80% of all ticker nodes, treat it as a contaminating
    # universal attractor and drop all its edges.
    narrative_attribution: dict[str, dict[str, Any]] = {}
    ticker_node_count = sum(1 for n in survivors.values() if n.type == "ticker")
    quarantine_threshold = 0.80 * max(ticker_node_count, 1)
    quarantined: set[str] = set()
    if ticker_node_count > 0:
        per_nar: dict[str, set[str]] = defaultdict(set)
        for e in edges_out:
            if e.source.startswith("narrative:") and e.target.startswith("ticker:"):
                per_nar[e.source].add(e.target)
            elif e.target.startswith("narrative:") and e.source.startswith("ticker:"):
                per_nar[e.target].add(e.source)
        for nar_id, ticker_set in per_nar.items():
            linked = len(ticker_set)
            entry = {
                "linked_tickers": linked,
                "linked_pct_of_universe": round(linked / ticker_node_count, 3),
            }
            if linked >= quarantine_threshold:
                entry["quarantined"] = True
                quarantined.add(nar_id)
            narrative_attribution[nar_id] = entry
        if quarantined:
            _log(f"auto-quarantine: dropping edges to {len(quarantined)} contaminating narratives")
            edges_out = [
                e for e in edges_out
                if e.source not in quarantined and e.target not in quarantined
            ]

    centrality = compute_centrality(survivors, edges_out)
    for nid, n in survivors.items():
        c = centrality.get(nid, {})
        n.weight = c.get("degree", 0.0)
        n.pagerank = c.get("pagerank", 0.0)

    # ─── V3.1.0 — ticker-centric collapse ──────────────────────────────────
    # Knowledge-graph page only wants ticker↔ticker relations. Move all other-
    # type context (news, themes, sector, narrative, thesis) into each ticker's
    # metadata block, then drop non-ticker nodes + edges. Internal pipeline
    # (Tier 1/2/3) is unchanged — only the OUTPUT shape collapses.
    ticker_centric = bool(cfg.get("ticker_centric", True))
    if ticker_centric:
        survivors, edges_out, tc_stats = _to_ticker_centric(
            survivors, edges_out, cfg,
        )
        _log(
            "ticker_centric: " + ", ".join(f"{k}={v}" for k, v in tc_stats.items())
        )
        # Re-compute centrality on the collapsed graph so degree / pagerank
        # reflect the ticker-only topology (was previously inflated by hub-y
        # theme / catalyst nodes acting as bridges).
        centrality = compute_centrality(survivors, edges_out)
        for nid, n in survivors.items():
            c = centrality.get(nid, {})
            n.weight = c.get("degree", 0.0)
            n.pagerank = c.get("pagerank", 0.0)

    graph = {
        "version": "3.0.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "decay_anchor_date": anchor.isoformat(),
        "tiers_applied": sorted(tiers),
        "nodes": [n.to_json() for n in survivors.values()],
        "edges": [e.to_json() for e in edges_out],
        "meta": {
            "node_count": len(survivors),
            "edge_count": len(edges_out),
            "nodes_by_type": _count_by(survivors.values(), "type"),
            "edges_by_type": _count_by_attr(edges_out, "type"),
            "prune_stats": prune_stats,
            "decay_strategies": cfg["decay_strategies"],
            "tier_confidence": cfg["tier_confidence"],
        },
    }

    payload = json.dumps(graph, ensure_ascii=False)
    size = len(payload.encode("utf-8"))
    _log(f"graph payload: {size} bytes / cap {cfg['max_json_bytes']}")

    if size > cfg["max_json_bytes"]:
        _log("size exceeds cap — emergency edge prune by weight")
        edges_out = sorted(edges_out, key=lambda e: e.weight, reverse=True)
        while edges_out and len(json.dumps(graph, ensure_ascii=False).encode("utf-8")) > cfg["max_json_bytes"]:
            edges_out.pop()
            graph["edges"] = [e.to_json() for e in edges_out]

    if args.dry_run:
        _log("dry-run: would write to " + cfg["sources"]["output"])
        print(json.dumps(graph["meta"], indent=2, ensure_ascii=False))
        return 0

    out_path = PROJECT_ROOT / cfg["sources"]["output"]
    out_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(f"wrote {out_path} ({size} bytes)")

    log_dir = PROJECT_ROOT / cfg["sources"]["build_log_dir"]
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"build_log_{anchor.isoformat()}.json"
    log_path.write_text(
        json.dumps(
            {
                "generated_at": graph["generated_at"],
                "tiers_applied": graph["tiers_applied"],
                "meta": graph["meta"],
                "size_bytes": size,
                "tier2_narrative_attribution_audit": tier2_audit,
                "narrative_attribution_in_graph": narrative_attribution,
                "quarantined_narratives": sorted(quarantined),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return 0


def _count_by(items, attr: str) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for it in items:
        out[getattr(it, attr)] += 1
    return dict(out)


def _count_by_attr(items, attr: str) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for it in items:
        out[getattr(it, attr)] += 1
    return dict(out)


if __name__ == "__main__":
    sys.exit(main())
