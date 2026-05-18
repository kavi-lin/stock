"""Tier 1 loaders — read pre-structured JSON sources into nodes + edges."""
from __future__ import annotations

import glob
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .schema import (
    Edge,
    EdgeType,
    Node,
    NodeType,
    make_catalyst_id,
    make_narrative_id,
    make_sector_id,
    make_theme_id,
    make_thesis_id,
    make_ticker_id,
)


TODAY = datetime.utcnow().date().isoformat()


def _safe_read_json(path: str) -> dict | list | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _date_from_filename(path: str) -> str | None:
    name = os.path.basename(path)
    for token in name.replace("_", "-").split("-"):
        if len(token) == 4 and token.isdigit():
            try:
                y = int(token)
                if 2020 <= y <= 2099:
                    parts = name.split("_")
                    for p in parts:
                        if p.startswith(token) and len(p) >= 10:
                            return p[:10]
            except ValueError:
                continue
    return None


def load_ticker_universe(path: str) -> set[str]:
    data = _safe_read_json(path)
    if not data:
        return set()
    raw = data["tickers"] if isinstance(data, dict) and "tickers" in data else data
    out: set[str] = set()
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                out.add(item.upper())
            elif isinstance(item, dict):
                sym = item.get("ticker") or item.get("symbol")
                if sym:
                    out.add(str(sym).upper())
    elif isinstance(raw, dict):
        out = {str(k).upper() for k in raw.keys()}
    return out


def load_ticker_sector_map(path: str) -> dict[str, str]:
    """Return {TICKER: sector_string} from heatmap_universe.json.

    Sector values are the exact strings present in the source — caller
    should use these (e.g., "Financial Services", not "Financial").
    Tickers not in heatmap_universe (ADRs like TSM, foreign listings)
    are simply absent — callers should treat absent → "unknown" and
    skip cross-domain narrative linkage (conservative default).
    """
    data = _safe_read_json(path)
    if not data:
        return {}
    raw = data["tickers"] if isinstance(data, dict) and "tickers" in data else data
    out: dict[str, str] = {}
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                sym = item.get("ticker") or item.get("symbol")
                sector = item.get("sector")
                if sym and sector:
                    out[str(sym).upper()] = str(sector)
    return out


def load_theme_detector(
    glob_pattern: str, universe: set[str]
) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    seen_tickers: dict[str, Node] = {}
    seen_themes: dict[str, Node] = {}

    matches = sorted(glob.glob(glob_pattern))
    if not matches:
        return nodes, edges
    latest = matches[-1]
    data = _safe_read_json(latest)
    if not data:
        return nodes, edges

    themes_block = data.get("themes") or {}
    theme_list = (
        themes_block.get("all")
        if isinstance(themes_block, dict) and "all" in themes_block
        else themes_block if isinstance(themes_block, list) else []
    )
    if not theme_list and isinstance(themes_block, dict):
        theme_list = []
        for v in themes_block.values():
            if isinstance(v, list):
                theme_list.extend(v)

    source_tag = f"theme_detector:{os.path.basename(latest)}"
    file_date = _date_from_filename(latest) or TODAY

    for t in theme_list:
        if not isinstance(t, dict):
            continue
        name = t.get("name")
        if not name:
            continue
        tid = make_theme_id(name)
        if tid not in seen_themes:
            n = Node(
                id=tid,
                type=NodeType.THEME.value,
                label=name,
                last_seen=file_date,
                metadata={
                    "direction": t.get("direction"),
                    "heat": t.get("heat"),
                    "stage": t.get("stage"),
                    "maturity": t.get("maturity"),
                    "confidence": t.get("confidence"),
                },
            )
            n.sources.add(source_tag)
            seen_themes[tid] = n
            nodes.append(n)

        heat = float(t.get("heat") or 0.0) / 100.0
        for sym in (t.get("representative_stocks") or []):
            sym = str(sym).upper()
            if universe and sym not in universe:
                continue
            tk_id = make_ticker_id(sym)
            if tk_id not in seen_tickers:
                tk = Node(
                    id=tk_id,
                    type=NodeType.TICKER.value,
                    label=sym,
                    last_seen=file_date,
                )
                tk.sources.add(source_tag)
                seen_tickers[tk_id] = tk
                nodes.append(tk)
            seen_tickers[tk_id].mentions += 1

            edges.append(
                Edge(
                    source=tk_id,
                    target=tid,
                    type=EdgeType.BELONGS_TO_THEME.value,
                    raw_frequency=1.0,
                    weight=max(heat, 0.5),
                    tier="tier1",
                    confidence=1.0,
                    last_seen=file_date,
                    sources={source_tag},
                )
            )

    return nodes, edges


def load_event_index(path: str, universe: set[str]) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    data = _safe_read_json(path)
    if not data or not isinstance(data, dict):
        return nodes, edges

    # Only single-stock-focused decision sources build a catalyst node +
    # OUTCOME_FOR edges. Batch screeners (momentum-screen, theme-detector
    # market scope, thematic-screener, sector-scan) bundle dozens of
    # unrelated tickers under one decision and turn that catalyst into a
    # noise hub. Their ticker→theme edges remain useful — only the
    # decision-as-catalyst is filtered.
    SINGLE_STOCK_SOURCES = {
        "deep-dive", "deep_dive",
        "news-digest", "news_digest",
        "postmortem",
        "earnings-analyzer", "earnings_analyzer",
    }
    decisions = data.get("decisions") or []
    seen_nodes: dict[str, Node] = {}

    def get_or_make(nid: str, ntype: str, label: str, date: str | None) -> Node:
        if nid not in seen_nodes:
            n = Node(id=nid, type=ntype, label=label, last_seen=date)
            seen_nodes[nid] = n
            nodes.append(n)
        else:
            if date and (seen_nodes[nid].last_seen or "") < date:
                seen_nodes[nid].last_seen = date
        return seen_nodes[nid]

    for dec in decisions:
        if not isinstance(dec, dict):
            continue
        source = dec.get("source") or "event-index"
        decision_date = dec.get("decision_date")
        source_tag = f"event_index:{source}:{decision_date or 'unknown'}"

        # ticker nodes + theme edges
        for sym in (dec.get("tickers") or []):
            sym = str(sym).upper()
            if universe and sym not in universe:
                continue
            tk_id = make_ticker_id(sym)
            tk = get_or_make(tk_id, NodeType.TICKER.value, sym, decision_date)
            tk.sources.add(source_tag)
            tk.mentions += 1

            content = dec.get("decision_content") or {}
            for theme in (content.get("themes") or []):
                if not isinstance(theme, dict):
                    continue
                tname = theme.get("name")
                if not tname:
                    continue
                tid = make_theme_id(tname)
                tn = get_or_make(tid, NodeType.THEME.value, tname, decision_date)
                tn.sources.add(source_tag)
                edges.append(
                    Edge(
                        source=tk_id,
                        target=tid,
                        type=EdgeType.BELONGS_TO_THEME.value,
                        raw_frequency=1.0,
                        weight=float(theme.get("heat") or 0.5) / 100.0 or 0.5,
                        tier="tier1",
                        confidence=1.0,
                        last_seen=decision_date,
                        sources={source_tag},
                    )
                )

            # verdict edge (decision -> outcome) — only for single-stock sources
            verdict = dec.get("verdict") or {}
            label = verdict.get("label")
            if (label and label not in ("pending", "n/a")
                    and source in SINGLE_STOCK_SOURCES):
                cid = make_catalyst_id(f"{source}_decision", decision_date)
                cn = get_or_make(
                    cid, NodeType.CATALYST.value, f"{source} {decision_date}", decision_date
                )
                cn.sources.add(source_tag)
                edges.append(
                    Edge(
                        source=cid,
                        target=tk_id,
                        type=EdgeType.OUTCOME_FOR.value,
                        raw_frequency=1.0,
                        weight=0.6,
                        tier="tier1",
                        confidence=1.0,
                        last_seen=decision_date,
                        sources={source_tag},
                    )
                )

    return nodes, edges


def load_news_digests(
    glob_pattern: str, universe: set[str], since_days: int = 30
) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    seen: dict[str, Node] = {}

    # Only single-stock-focused news types build a catalyst-as-ticker hub.
    # Macro / geopolitical / sentiment / sector news cover many unrelated
    # tickers; bundling them under one catalyst creates noise hubs (e.g.,
    # "Dow futures surge 260 points" linking LLY ↔ NVDA ↔ XOM).
    SINGLE_STOCK_NEWS_TYPES = {"earnings", "corporate"}
    # Sector-level news still link to sector nodes (handled below) but
    # skip the ticker→catalyst hub.
    SECTOR_LEVEL_NEWS_TYPES = {"sector_news"}
    # Everything else (macro_data, monetary_policy, geopolitical, sentiment)
    # is excluded from catalyst hubs entirely — they're macro context, not
    # actionable per-ticker signals.

    cutoff = (datetime.utcnow().date()).toordinal() - since_days

    def get_or_make(nid: str, ntype: str, label: str, date: str | None) -> Node:
        if nid not in seen:
            n = Node(id=nid, type=ntype, label=label, last_seen=date)
            seen[nid] = n
            nodes.append(n)
        return seen[nid]

    for path in sorted(glob.glob(glob_pattern)):
        name = os.path.basename(path)
        if "_digest" not in name:
            continue
        date_part = name.split("_")[0]
        try:
            d = datetime.fromisoformat(date_part).date()
        except ValueError:
            continue
        if d.toordinal() < cutoff:
            continue

        data = _safe_read_json(path)
        if not data or not isinstance(data, dict):
            continue

        source_tag = f"news_digest:{date_part}"
        for v in (data.get("verdicts") or []):
            if not isinstance(v, dict):
                continue
            news_id = v.get("news_id") or v.get("headline") or "unknown"
            headline = v.get("headline") or news_id
            verdict_label = v.get("verdict") or "UNCERTAIN"
            net = float(v.get("net_impact_score") or 0.0)
            news_type = (v.get("news_type") or "").lower()

            build_ticker_catalyst = news_type in SINGLE_STOCK_NEWS_TYPES
            build_sector_catalyst = news_type in SECTOR_LEVEL_NEWS_TYPES
            # Macro / geopolitical / sentiment news skip catalyst hub entirely.
            if not build_ticker_catalyst and not build_sector_catalyst:
                continue

            cat_id = make_catalyst_id(news_id, date_part)
            cn = get_or_make(cat_id, NodeType.CATALYST.value, headline[:80], date_part)
            cn.sources.add(source_tag)
            cn.metadata.setdefault("verdict", verdict_label)
            cn.metadata.setdefault("net_impact", net)
            cn.metadata.setdefault("news_type", news_type)
            cn.mentions += 1

            if build_ticker_catalyst:
                for sym in (v.get("tickers_mentioned") or []):
                    sym = str(sym).upper()
                    if universe and sym not in universe:
                        continue
                    tk_id = make_ticker_id(sym)
                    tk = get_or_make(tk_id, NodeType.TICKER.value, sym, date_part)
                    tk.sources.add(source_tag)
                    tk.mentions += 1

                    edge_type = (
                        EdgeType.BULL_CASE_FOR.value
                        if verdict_label == "BULLISH"
                        else EdgeType.BEAR_CASE_FOR.value
                        if verdict_label == "BEARISH"
                        else EdgeType.MENTIONED_IN.value
                    )
                    edges.append(
                        Edge(
                            source=cat_id,
                            target=tk_id,
                            type=edge_type,
                            raw_frequency=1.0,
                            weight=min(abs(net) / 10.0 + 0.4, 1.0),
                            tier="tier1",
                            confidence=1.0,
                            last_seen=date_part,
                            sources={source_tag},
                        )
                    )

            for sector_block in (v.get("affected_sectors") or []):
                if isinstance(sector_block, dict):
                    sname = sector_block.get("sector")
                else:
                    sname = str(sector_block)
                if not sname:
                    continue
                sid = make_sector_id(sname)
                sn = get_or_make(sid, NodeType.SECTOR.value, sname, date_part)
                sn.sources.add(source_tag)
                edges.append(
                    Edge(
                        source=cat_id,
                        target=sid,
                        type=EdgeType.MENTIONED_IN.value,
                        raw_frequency=1.0,
                        weight=0.5,
                        tier="tier1",
                        confidence=1.0,
                        last_seen=date_part,
                        sources={source_tag},
                    )
                )

    return nodes, edges


def load_break_news(
    break_news_dir: str, universe: set[str], since_days: int = 14,
    digest_url_hashes: set[str] | None = None,
) -> tuple[list[Node], list[Edge]]:
    """Load `news/break_news_logs/bn_*.json` items (closed or partial_closed
    only) and emit catalyst-type nodes with edges to tickers, sectors, themes,
    narratives. Maps onto existing CATALYST NodeType (no schema change); the
    `metadata.is_break_news=true` flag lets graph.html style differently if
    desired.

    Dedupe vs daily DIGEST: if `digest_url_hashes` is provided and the item's
    `source.url_hash` is in it, skip — digest verdicts are deeper.
    """
    nodes: list[Node] = []
    edges: list[Edge] = []
    seen: dict[str, Node] = {}

    if not os.path.isdir(break_news_dir):
        return nodes, edges

    cutoff = datetime.utcnow().date().toordinal() - since_days

    def get_or_make(nid: str, ntype: str, label: str, date: str | None) -> Node:
        if nid not in seen:
            n = Node(id=nid, type=ntype, label=label, last_seen=date)
            seen[nid] = n
            nodes.append(n)
        else:
            if date and (seen[nid].last_seen or "") < date:
                seen[nid].last_seen = date
        return seen[nid]

    for path in sorted(glob.glob(os.path.join(break_news_dir, "bn_*.json"))):
        data = _safe_read_json(path)
        if not data or not isinstance(data, dict):
            continue
        state = data.get("state")
        if state not in ("closed", "partial_closed"):
            continue  # only graph-promote items with a finished thread
        url_hash = (data.get("source") or {}).get("url_hash") or ""
        if digest_url_hashes and url_hash in digest_url_hashes:
            continue
        fetched = (data.get("fetched_at") or "")[:10]
        try:
            d = datetime.fromisoformat(fetched).date()
        except ValueError:
            continue
        if d.toordinal() < cutoff:
            continue

        news_id = data.get("news_id") or os.path.basename(path)
        headline = data.get("headline") or news_id
        summary = data.get("summary") or {}
        merged = summary.get("merged_entities") or {}
        consensus = summary.get("consensus_verdict") or "NEUTRAL"
        source_tag = f"break_news:{news_id}"
        date_part = fetched or TODAY

        cat_id = make_catalyst_id(f"news_{news_id}", date_part)
        cn = get_or_make(cat_id, NodeType.CATALYST.value, headline[:80], date_part)
        cn.sources.add(source_tag)
        cn.metadata.setdefault("is_break_news", True)
        cn.metadata.setdefault("verdict", consensus)
        cn.metadata.setdefault("rounds", summary.get("rounds_completed"))
        cn.mentions += 1

        edge_type = (
            EdgeType.BULL_CASE_FOR.value if consensus == "BULLISH"
            else EdgeType.BEAR_CASE_FOR.value if consensus == "BEARISH"
            else EdgeType.MENTIONED_IN.value
        )

        for sym in (merged.get("tickers") or []):
            sym = str(sym).upper()
            if universe and sym not in universe:
                continue
            tk_id = make_ticker_id(sym)
            tk = get_or_make(tk_id, NodeType.TICKER.value, sym, date_part)
            tk.sources.add(source_tag)
            tk.mentions += 1
            edges.append(Edge(
                source=cat_id, target=tk_id, type=edge_type,
                raw_frequency=1.0, weight=0.5,
                tier="tier1", confidence=1.0, last_seen=date_part,
                sources={source_tag},
            ))

        for sector_name in (merged.get("sectors") or []):
            if not sector_name:
                continue
            sid = make_sector_id(sector_name)
            sn = get_or_make(sid, NodeType.SECTOR.value, sector_name, date_part)
            sn.sources.add(source_tag)
            edges.append(Edge(
                source=cat_id, target=sid, type=EdgeType.MENTIONED_IN.value,
                raw_frequency=1.0, weight=0.4,
                tier="tier1", confidence=1.0, last_seen=date_part,
                sources={source_tag},
            ))

        for theme_name in (merged.get("themes") or []):
            if not theme_name:
                continue
            tid = make_theme_id(theme_name)
            tn = get_or_make(tid, NodeType.THEME.value, theme_name, date_part)
            tn.sources.add(source_tag)
            edges.append(Edge(
                source=cat_id, target=tid, type=EdgeType.MENTIONED_IN.value,
                raw_frequency=1.0, weight=0.4,
                tier="tier1", confidence=1.0, last_seen=date_part,
                sources={source_tag},
            ))

        for tech_kw in (merged.get("tech_keywords") or []):
            if not tech_kw:
                continue
            nid = make_narrative_id(tech_kw.lower().replace(" ", "_"))
            nn = get_or_make(nid, NodeType.NARRATIVE.value, tech_kw, date_part)
            nn.sources.add(source_tag)
            nn.metadata.setdefault("status", "provisional")
            edges.append(Edge(
                source=cat_id, target=nid, type=EdgeType.MENTIONED_IN.value,
                raw_frequency=1.0, weight=0.4,
                tier="tier1", confidence=1.0, last_seen=date_part,
                sources={source_tag},
            ))

    return nodes, edges


def load_theses(theses_dir: str) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    if not os.path.isdir(theses_dir):
        return nodes, edges

    for path in glob.glob(os.path.join(theses_dir, "*.json")):
        data = _safe_read_json(path)
        if not data or not isinstance(data, dict):
            continue
        thesis_id = data.get("thesis_id") or os.path.basename(path).replace(".json", "")
        ticker = data.get("ticker")
        if not ticker:
            continue
        ticker = str(ticker).upper()
        node_id = make_thesis_id(thesis_id)
        tk_id = make_ticker_id(ticker)
        last_seen = (data.get("thesis_registered_at") or "")[:10] or None
        source_tag = f"thesis:{thesis_id}"

        nodes.append(
            Node(
                id=node_id,
                type=NodeType.THESIS.value,
                label=f"{ticker}: {data.get('thesis_oneliner', '')[:60]}",
                last_seen=last_seen,
                sources={source_tag},
                metadata={
                    "verdict_band": data.get("verdict_band"),
                    "final_decision": data.get("final_decision"),
                    "final_score": data.get("final_score"),
                    "confidence": data.get("confidence"),
                },
            )
        )
        nodes.append(
            Node(id=tk_id, type=NodeType.TICKER.value, label=ticker, last_seen=last_seen)
        )

        edges.append(
            Edge(
                source=node_id,
                target=tk_id,
                type=EdgeType.BULL_CASE_FOR.value
                if (data.get("final_decision") or "").upper() in ("BUY", "STAGED_ENTRY")
                else EdgeType.BEAR_CASE_FOR.value,
                raw_frequency=1.0,
                weight=0.9,
                tier="tier1",
                confidence=1.0,
                last_seen=last_seen,
                sources={source_tag},
            )
        )
    return nodes, edges


def load_dashboard_data(path: str, universe: set[str]) -> tuple[list[Node], list[Edge]]:
    """Extract earnings-analyses + theme/sector taxonomy from Dashboard/data.json."""
    nodes: list[Node] = []
    edges: list[Edge] = []
    data = _safe_read_json(path)
    if not data or not isinstance(data, dict):
        return nodes, edges

    seen: dict[str, Node] = {}

    def get_or_make(nid: str, ntype: str, label: str, date: str | None) -> Node:
        if nid not in seen:
            n = Node(id=nid, type=ntype, label=label, last_seen=date)
            seen[nid] = n
            nodes.append(n)
        return seen[nid]

    market = data.get("market") or {}
    today = data.get("generated_at", TODAY)[:10] if data.get("generated_at") else TODAY

    for theme_name in (market.get("themes") or []):
        if not theme_name:
            continue
        tid = make_theme_id(theme_name)
        tn = get_or_make(tid, NodeType.THEME.value, theme_name, today)
        tn.sources.add("dashboard_data:market.themes")

    # earnings analyses → ticker + catalyst
    for entry in (data.get("earnings_analyses") or []):
        if not isinstance(entry, dict):
            continue
        sym = (entry.get("ticker") or "").upper()
        if not sym or (universe and sym not in universe):
            continue
        tk_id = make_ticker_id(sym)
        tk = get_or_make(tk_id, NodeType.TICKER.value, sym, today)
        tk.sources.add(f"dashboard_data:earnings:{sym}")
        tk.mentions += 1
        nxt = entry.get("next_earnings_date")
        if nxt:
            cid = make_catalyst_id(f"{sym}_EARNINGS", nxt)
            cn = get_or_make(cid, NodeType.CATALYST.value, f"{sym} earnings {nxt}", nxt)
            cn.sources.add(f"dashboard_data:earnings:{sym}")
            edges.append(
                Edge(
                    source=cid,
                    target=tk_id,
                    type=EdgeType.CATALYST_FOR.value,
                    raw_frequency=1.0,
                    weight=0.8,
                    tier="tier1",
                    confidence=1.0,
                    last_seen=nxt,
                    sources={f"dashboard_data:earnings:{sym}"},
                )
            )
    return nodes, edges
