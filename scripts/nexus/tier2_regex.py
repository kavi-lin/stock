"""Tier 2 — regex enrichment with sector-scoped, paragraph-level matching.

Sweeps recent MD reports for catalyst keywords, peer mentions, and
sector-specific narrative terms. Critical fix (2026-05-13): all narrative
matching is now paragraph-scoped AND filtered by `narrative_sector_scope`
in config.yaml — eliminates cross-domain contamination (e.g., LLY no longer
linked to HBM / CoWoS because Healthcare sector is not in HBM's scope).
"""
from __future__ import annotations

import glob
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from .schema import (
    Edge,
    EdgeType,
    Node,
    NodeType,
    make_catalyst_id,
    make_narrative_id,
    make_ticker_id,
)
from .tier1_loaders import load_ticker_universe, load_ticker_sector_map


CATALYST_PATTERN = re.compile(
    r"(?i)\b(FOMC|CPI|FY\d+Q\d+ earnings|GTC \d{4}|Computex|WWDC \d{4}|"
    r"OpenAI DevDay|Apple Event|NVIDIA GTC|Microsoft Ignite|AWS re:Invent)\b"
)

SUPPLY_CHAIN_GENERIC_PATTERN = re.compile(
    r"(?i)\b(supply chain|pull[- ]through|wafer allocation|capacity expansion|"
    r"yield ramp|bottleneck|capex supercycle|substrate constraint)\b"
)

# ─── Per-sector narrative dictionaries ──────────────────────────────────
# Each entry: narrative_key → regex. The key MUST appear in
# `narrative_sector_scope` of config.yaml. Pattern produces a label that
# is canonicalized via `make_narrative_id(label)`.
TECH_PATTERNS: dict[str, re.Pattern[str]] = {
    "hbm":         re.compile(r"(?i)\bHBM(?!3|4|3e)\b"),
    "hbm3e":       re.compile(r"(?i)\bHBM3e\b"),
    "hbm4":        re.compile(r"(?i)\bHBM4\b"),
    "gddr":        re.compile(r"(?i)\bGDDR[567]\w*\b"),
    "lpddr":       re.compile(r"(?i)\bLPDDR[567]\w*\b"),
    "cowos":       re.compile(r"(?i)\bCoWoS(?![-_])\b"),
    "cowos_l":     re.compile(r"(?i)\bCoWoS-L\b"),
    "cowos_s":     re.compile(r"(?i)\bCoWoS-S\b"),
    "info":        re.compile(r"(?i)\bInFO\b"),
    "soic":        re.compile(r"(?i)\bSoIC\b"),
    "chiplet":     re.compile(r"(?i)\bchiplet\b"),
    "foplp":       re.compile(r"(?i)\b(?:FOPLP|panel[- ]level packaging)\b"),
    "n3":          re.compile(r"(?i)\bN3(?!P)\b|\b3nm\b"),
    "n3p":         re.compile(r"(?i)\bN3P\b"),
    "n2":          re.compile(r"(?i)\bN2\b|\b2nm\b"),
    "a14":         re.compile(r"(?i)\bA14\b"),
    "a16":         re.compile(r"(?i)\bA16\b"),
    "18a":         re.compile(r"(?i)\b18A\b"),
    "gaa":         re.compile(r"(?i)\bGAA\b"),
    "nanosheet":   re.compile(r"(?i)\bnanosheet\b"),
    "blackwell":   re.compile(r"(?i)\bBlackwell\b"),
    "rubin":       re.compile(r"(?i)\bRubin\b"),
    "mi300":       re.compile(r"(?i)\bMI300X?\b"),
    "mi325":       re.compile(r"(?i)\bMI325\b"),
    "mi350":       re.compile(r"(?i)\bMI350\b"),
    "trainium":    re.compile(r"(?i)\bTrainium\b"),
    "inferentia":  re.compile(r"(?i)\bInferentia\b"),
    "tpu":         re.compile(r"(?i)\bTPU\s*v?[345]\b|\bTPU\s*v?6\b"),
    "maia":        re.compile(r"(?i)\bMaia\b"),
    "silicon_photonics": re.compile(r"(?i)\bsilicon photonics\b"),
    "cpo":         re.compile(r"(?i)\bCPO\b|\bco[- ]packaged optics\b"),
    "800g":        re.compile(r"(?i)\b800G\b"),
    "1_6t":        re.compile(r"(?i)\b1\.6T\b"),
    "lpo":         re.compile(r"(?i)\bLPO\b"),
    # Power semis cross multiple sectors (handled by sector scope)
    "gan":             re.compile(r"(?i)\bGaN\b"),
    "sic":             re.compile(r"(?i)\bSiC\b"),
    "silicon_carbide": re.compile(r"(?i)\bsilicon carbide\b"),
    "wide_bandgap":    re.compile(r"(?i)\bwide bandgap\b"),
}

HEALTHCARE_PATTERNS: dict[str, re.Pattern[str]] = {
    "glp1":         re.compile(r"(?i)\b(?:GLP-1|GLP1|semaglutide|tirzepatide|retatrutide|orforglipron)\b"),
    "weight_loss":  re.compile(r"(?i)\b(?:obesity|weight[- ]loss|Wegovy|Mounjaro|Zepbound|Ozempic)\b"),
    "peptide_mfg":  re.compile(r"(?i)\b(?:peptide synthesis|biologics capacity|CDMO|fill[- ]finish|sterile injectable)\b"),
    "oncology":     re.compile(r"(?i)\b(?:KRAS|PD-[L]?1|antibody[- ]drug conjugate|ADC|CAR[- ]T|bispecific)\b"),
    "gene_therapy": re.compile(r"(?i)\b(?:AAV|CRISPR|gene therapy|cell therapy)\b"),
    "alzheimer":    re.compile(r"(?i)\b(?:amyloid|Leqembi|Kisunla|donanemab|lecanemab)\b"),
    "biosimilars":  re.compile(r"(?i)\b(?:biosimilar|interchangeable biologic)\b"),
}

ENERGY_PATTERNS: dict[str, re.Pattern[str]] = {
    "shale":    re.compile(r"(?i)\b(?:Permian|Bakken|Eagle Ford|shale)\b"),
    "lng":      re.compile(r"(?i)\b(?:LNG|liquefied natural gas|export terminal|Henry Hub)\b"),
    "refining": re.compile(r"(?i)\b(?:crack spread|crude differential|refining margin)\b"),
    "nuclear":  re.compile(r"(?i)\b(?:SMR|small modular reactor|enriched uranium|HALEU)\b"),
    "grid":     re.compile(r"(?i)\b(?:transmission backlog|interconnection queue|datacenter power|grid capacity)\b"),
}

FINANCIAL_PATTERNS: dict[str, re.Pattern[str]] = {
    "nim":             re.compile(r"(?i)\b(?:net interest margin|NIM|deposit beta)\b"),
    "credit_cycle":    re.compile(r"(?i)\b(?:net charge[- ]offs|delinquency|credit loss)\b"),
    "capital_markets": re.compile(r"(?i)\b(?:IPO pipeline|M&A backlog|underwriting fees)\b"),
}

CONSUMER_PATTERNS: dict[str, re.Pattern[str]] = {
    "ecommerce":  re.compile(r"(?i)\b(?:GMV|take rate|fulfillment cost|last[- ]mile)\b"),
    "ad_spend":   re.compile(r"(?i)\b(?:CPM|programmatic|retail media)\b"),
    "travel":     re.compile(r"(?i)\b(?:RevPAR|load factor)\b"),
}

ALL_DOMAIN_PATTERNS: dict[str, re.Pattern[str]] = {
    **TECH_PATTERNS,
    **HEALTHCARE_PATTERNS,
    **ENERGY_PATTERNS,
    **FINANCIAL_PATTERNS,
    **CONSUMER_PATTERNS,
}

DATE_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")
PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")
SENTENCE_SPLIT  = re.compile(r"(?<=[.。!?])\s+")


def _scan_reports(reports_dir: Path, since_days: int = 30) -> list[Path]:
    cutoff = datetime.utcnow().date() - timedelta(days=since_days)
    out: list[Path] = []
    if not reports_dir.is_dir():
        return out
    for p in reports_dir.rglob("*.md"):
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
    return out


def _extract_ticker_from_filename(path: Path) -> str | None:
    stem = path.stem
    if len(stem) >= 10 and stem[:8].isdigit() and stem[8] == "_":
        return stem[9:].split("_")[0].upper()
    return None


def _path_date(path: Path) -> str | None:
    m = DATE_IN_NAME.search(path.name)
    if m:
        return m.group(1)
    stem = path.stem
    if len(stem) >= 8 and stem[:8].isdigit():
        try:
            d = datetime.strptime(stem[:8], "%Y%m%d").date()
            return d.isoformat()
        except ValueError:
            return None
    return None


def _split_paragraphs(text: str, max_chars: int = 800) -> list[str]:
    """Split MD body into paragraphs. Long paragraphs split by sentence
    so the proximity window stays within max_chars."""
    paragraphs = PARAGRAPH_SPLIT.split(text or "")
    out: list[str] = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if len(p) <= max_chars:
            out.append(p)
            continue
        # paragraph too long — sub-split by sentence
        sentences = SENTENCE_SPLIT.split(p)
        buf = ""
        for s in sentences:
            if len(buf) + len(s) > max_chars and buf:
                out.append(buf.strip())
                buf = s
            else:
                buf = (buf + " " + s).strip() if buf else s
        if buf:
            out.append(buf.strip())
    return out


def _build_ticker_re(safe_universe: set[str]) -> re.Pattern[str] | None:
    if not safe_universe:
        return None
    return re.compile(r"\b(" + "|".join(sorted(safe_universe, key=len, reverse=True)) + r")\b")


def collect(cfg: dict[str, Any], project_root: Path) -> tuple[list[Node], list[Edge]]:
    sources = cfg["sources"]
    universe = load_ticker_universe(str(project_root / sources["heatmap_universe"]))
    ticker_sector = load_ticker_sector_map(str(project_root / sources["heatmap_universe"]))
    narrative_scope: dict[str, list[str]] = cfg.get("narrative_sector_scope") or {}
    weights = cfg.get("tier2_weights") or {}
    w_primary = float(weights.get("primary_ticker", 1.0))
    w_peer    = float(weights.get("peer_in_body", 0.35))

    reports_dir = project_root / sources["reports_dir"]
    files = _scan_reports(reports_dir, since_days=30)

    nodes: list[Node] = []
    edges: list[Edge] = []
    seen: dict[str, Node] = {}

    FP_BLACKLIST = {
        "A", "C", "D", "F", "G", "K", "L", "M", "O", "R", "T", "V", "X",
        "MA", "MS", "GS", "JP", "BA", "GE", "AI", "IT", "US", "UK", "EU",
        "NEW", "OLD", "ALL", "OUT", "FED", "CPI", "GDP", "EPS", "USA",
    }
    safe_universe = {sym for sym in universe if len(sym) >= 3 and sym not in FP_BLACKLIST}
    ticker_word_re = _build_ticker_re(safe_universe)

    def get_or_make(nid: str, ntype: str, label: str, date: str | None) -> Node:
        if nid not in seen:
            n = Node(id=nid, type=ntype, label=label, last_seen=date)
            seen[nid] = n
            nodes.append(n)
        elif date and (seen[nid].last_seen or "") < date:
            seen[nid].last_seen = date
        return seen[nid]

    def is_in_scope(ticker: str, narrative_key: str) -> bool:
        """Reject ticker → narrative edge if ticker's sector is not in
        the narrative's allowed sector scope."""
        scope = narrative_scope.get(narrative_key)
        if not scope:
            # No scope declared — be conservative, reject
            return False
        sector = ticker_sector.get(ticker)
        if not sector:
            # Unknown sector (e.g., ADR ticker not in heatmap_universe)
            # → conservative reject; only known-sector tickers get linked
            return False
        return sector in scope

    # Audit counters for build log (filled per narrative)
    audit_emitted: dict[str, dict[str, int]] = {}

    def bump_audit(narrative_key: str, in_scope: bool) -> None:
        rec = audit_emitted.setdefault(narrative_key, {"emitted": 0, "rejected_oos": 0})
        if in_scope:
            rec["emitted"] += 1
        else:
            rec["rejected_oos"] += 1

    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        date = _path_date(path)
        source_tag = f"tier2_md:{path.relative_to(project_root)}"
        primary_ticker = _extract_ticker_from_filename(path)

        # ── Paragraph-scoped narrative matching ─────────────────────────
        # For each paragraph: find ticker mentions AND narrative matches
        # in that paragraph only. Emit ticker→narrative edge only when
        # both co-occur AND ticker's sector ∈ narrative scope.
        paragraphs = _split_paragraphs(text)
        for para in paragraphs:
            # Find tickers in this paragraph
            para_tickers: set[str] = set()
            if primary_ticker and (not universe or primary_ticker in universe):
                # Primary ticker always considered present in every paragraph
                # of its own deep-dive — captures cases where author refers
                # to "the company" without re-naming it
                para_tickers.add(primary_ticker)
            if ticker_word_re:
                para_tickers.update(
                    sym for sym in ticker_word_re.findall(para) if sym in safe_universe
                )

            # Find narrative matches in this paragraph
            para_narratives: dict[str, str] = {}   # narrative_key -> matched label
            for n_key, pattern in ALL_DOMAIN_PATTERNS.items():
                m = pattern.search(para)
                if m:
                    para_narratives[n_key] = (m.group(0) or n_key).strip()

            if not para_tickers or not para_narratives:
                continue

            for n_key, n_label in para_narratives.items():
                nar_id = make_narrative_id(n_key)
                for sym in para_tickers:
                    if not is_in_scope(sym, n_key):
                        bump_audit(n_key, False)
                        continue
                    bump_audit(n_key, True)

                    # Only create narrative node once we have an in-scope ticker
                    nar = get_or_make(nar_id, NodeType.NARRATIVE.value, n_label, date)
                    nar.sources.add(source_tag)
                    nar.metadata.setdefault("category", n_key)
                    nar.mentions += 1

                    tk_id = make_ticker_id(sym)
                    get_or_make(tk_id, NodeType.TICKER.value, sym, date)

                    edge_weight = w_primary if sym == primary_ticker else w_peer
                    edges.append(
                        Edge(
                            source=tk_id,
                            target=nar_id,
                            type=EdgeType.SUPPLY_CHAIN_HOP.value,
                            raw_frequency=1.0,
                            weight=edge_weight,
                            tier="tier2",
                            confidence=0.7,
                            last_seen=date,
                            sources={source_tag},
                        )
                    )

        # ── Generic supply-chain signal (paragraph-scoped) ──────────────
        for para in paragraphs:
            if not SUPPLY_CHAIN_GENERIC_PATTERN.search(para):
                continue
            if not (primary_ticker and (not universe or primary_ticker in universe)):
                continue
            if not is_in_scope(primary_ticker, "supply_chain_signal"):
                bump_audit("supply_chain_signal", False)
                continue
            bump_audit("supply_chain_signal", True)
            nar_id = make_narrative_id("supply_chain_signal")
            nar = get_or_make(
                nar_id, NodeType.NARRATIVE.value, "supply_chain_signal", date
            )
            nar.sources.add(source_tag)
            nar.mentions += 1
            tk_id = make_ticker_id(primary_ticker)
            edges.append(
                Edge(
                    source=tk_id,
                    target=nar_id,
                    type=EdgeType.SUPPLY_CHAIN_HOP.value,
                    raw_frequency=1.0,
                    weight=w_primary * 0.6,
                    tier="tier2",
                    confidence=0.7,
                    last_seen=date,
                    sources={source_tag},
                )
            )

        # ── Catalyst keywords → catalyst node + edge to primary ticker ──
        # Catalysts are not sector-scoped — they're events, all tickers
        # affected. Keep doc-level here.
        for cat_match in CATALYST_PATTERN.findall(text):
            label = cat_match.strip()
            cid = make_catalyst_id(label, date)
            cn = get_or_make(cid, NodeType.CATALYST.value, label, date)
            cn.sources.add(source_tag)
            cn.mentions += 1
            if primary_ticker and (not universe or primary_ticker in universe):
                tk_id = make_ticker_id(primary_ticker)
                get_or_make(tk_id, NodeType.TICKER.value, primary_ticker, date)
                edges.append(
                    Edge(
                        source=cid,
                        target=tk_id,
                        type=EdgeType.CATALYST_FOR.value,
                        raw_frequency=1.0,
                        weight=0.55,
                        tier="tier2",
                        confidence=0.7,
                        last_seen=date,
                        sources={source_tag},
                    )
                )

        # ── Peer-mention pairs (paragraph-scoped to reduce noise) ───────
        if primary_ticker and ticker_word_re:
            tk_main = make_ticker_id(primary_ticker)
            get_or_make(tk_main, NodeType.TICKER.value, primary_ticker, date)
            # Collect peers from any paragraph that ALSO contains primary
            for para in paragraphs:
                if primary_ticker not in para and not _extract_ticker_from_filename(path) == primary_ticker:
                    continue
                peers = {p for p in ticker_word_re.findall(para)
                         if p in safe_universe and p != primary_ticker}
                for peer in peers:
                    tk_peer = make_ticker_id(peer)
                    get_or_make(tk_peer, NodeType.TICKER.value, peer, date)
                    edges.append(
                        Edge(
                            source=tk_main,
                            target=tk_peer,
                            type=EdgeType.PEER_OF.value,
                            raw_frequency=1.0,
                            weight=0.35,
                            tier="tier2",
                            confidence=0.7,
                            last_seen=date,
                            sources={source_tag},
                        )
                    )

    # Stash audit counters on the first node's metadata for build_graph to harvest
    # (clean piggyback — build_graph reads this via a known sentinel id)
    audit_node = Node(
        id="__tier2_audit__",
        type="internal_audit",
        label="tier2 narrative attribution audit",
        metadata={"counts": audit_emitted},
    )
    nodes.append(audit_node)

    return nodes, edges


if __name__ == "__main__":
    import argparse
    import yaml

    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    project_root = here.parent.parent
    with open(here / "config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    nodes, edges = collect(cfg, project_root)
    # Strip audit node from print
    real_nodes = [n for n in nodes if n.type != "internal_audit"]
    audit = next((n.metadata.get("counts") for n in nodes if n.type == "internal_audit"), {})
    print(f"tier2: {len(real_nodes)} nodes / {len(edges)} edges")
    if audit:
        print("\nNarrative attribution audit (emitted / rejected_oos):")
        for k in sorted(audit.keys()):
            v = audit[k]
            print(f"  {k:24s}  emitted={v['emitted']:4d}  rejected_oos={v['rejected_oos']:4d}")
    if args.print:
        print("\nSample edges:")
        for e in edges[:20]:
            print(f"  {e.source} --{e.type}--> {e.target}  (w={e.weight}, src={list(e.sources)[:1]})")
