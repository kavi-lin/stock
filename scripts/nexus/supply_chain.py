"""US supply-chain explorer — LLM-drafted value chains + live data grounding.

Workflow:
  1. `generate(theme)` — Claude drafts the upstream->downstream value chain
     (layers, companies, directional edges, spine) -> saved as an editable YAML
     skeleton in `nexus/supply_chains/<slug>.yaml`.
  2. `enrich(chain)` — at serve time, each node is cross-checked against existing
     data: `grounding` (verified / seen / llm_only) + `heat` (from Nexus mention
     counts). These are computed live, never stored.

The Nexus auto-graph is only *read* for validation — never modified.

Standalone: `python3 scripts/nexus/supply_chain.py --theme CPO`
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.break_news.llm_drivers import run_llm, primary_model, VALID_MODELS  # noqa: E402, F401
from scripts._shared.model_router import run_role, run_with_fallback  # noqa: E402

CHAINS_DIR = _ROOT / "nexus" / "supply_chains"
PROMPT_FILE = _ROOT / "scripts" / "nexus" / "prompts" / "supply_chain_system.md"
UNIVERSE_FILE = _ROOT / "Dashboard" / "heatmap_universe.json"
NEXUS_FILE = _ROOT / "Dashboard" / "nexus_graph.json"

_LISTINGS = {"us_listed", "foreign_listed", "private", "pre_ipo"}
_RELS = {"SUPPLIES_TO", "CUSTOMER_OF", "CONTRACT_MFG_FOR", "CO_DEVELOPS_WITH", "INVESTOR_IN"}
# Commercialization stage of a company within the chain's theme (vs the spine
# subject). LLM seeds it from public evidence; the user refines it in the YAML.
_STAGES = {"design_partner", "sampling", "qualification", "production",
           "revenue", "unknown"}
_SLUG_RE = re.compile(r"[^a-z0-9]+")


# ─────────────────────────── slug / IO helpers ──────────────────────────────
def slugify(text: str) -> str:
    s = _SLUG_RE.sub("_", (text or "").strip().lower()).strip("_")
    return s[:48] or "chain"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load(slug: str) -> dict | None:
    """Read one chain YAML by slug."""
    path = CHAINS_DIR / f"{slug}.yaml"
    if not path.is_file():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None


def list_chains() -> list[dict]:
    """List saved chains (lightweight header fields only)."""
    out = []
    if not CHAINS_DIR.is_dir():
        return out
    for path in sorted(CHAINS_DIR.glob("*.yaml")):
        try:
            d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (yaml.YAMLError, OSError):
            continue
        out.append({
            "id": d.get("id", path.stem),
            "title": d.get("title", path.stem),
            "theme": d.get("theme", ""),
            "generated_at": d.get("generated_at", ""),
            "status": d.get("status", "draft"),
            "node_count": len(d.get("nodes") or []),
        })
    out.sort(key=lambda c: c.get("generated_at", ""), reverse=True)
    return out


# ─────────────────────────── normalisation ──────────────────────────────────
def _normalise(raw: dict, theme: str, slug: str) -> dict:
    """Coerce an LLM JSON draft into a valid chain skeleton."""
    layers = [str(x).strip() for x in (raw.get("layers") or []) if str(x).strip()]
    if not layers:
        layers = ["upstream", "midstream", "downstream"]

    # modules: {layerId: [{id,label}]} — 2-3 industry sub-groups per stage.
    # A layer with no modules falls back to a single unlabelled `_default`.
    raw_modules = raw.get("modules") or {}
    modules: dict = {}
    for layer in layers:
        clean, seen_m = [], set()
        for m in raw_modules.get(layer) or []:
            if isinstance(m, dict):
                mid = slugify(str(m.get("id") or m.get("label") or ""))
                mlabel = str(m.get("label") or m.get("id") or "").strip()
            else:
                mid, mlabel = slugify(str(m)), str(m).strip()
            if not mid or mid in seen_m:
                continue
            seen_m.add(mid)
            clean.append({"id": mid, "label": mlabel or mid})
        modules[layer] = clean or [{"id": "_default", "label": ""}]

    nodes, seen_ids = [], set()
    for n in raw.get("nodes") or []:
        nid = slugify(str(n.get("id") or n.get("label") or ""))
        if not nid or nid in seen_ids:
            continue
        seen_ids.add(nid)
        layer = str(n.get("layer") or "").strip()
        if layer not in layers:
            layer = layers[len(layers) // 2]  # park unknowns mid-chain
        layer_mod_ids = {m["id"] for m in modules[layer]}
        module = slugify(str(n.get("module") or ""))
        if module not in layer_mod_ids:
            module = modules[layer][0]["id"]
        ticker = n.get("ticker")
        ticker = str(ticker).strip().upper() if ticker else None
        listing = str(n.get("listing") or "").strip().lower()
        if listing not in _LISTINGS:
            listing = "us_listed" if ticker else "private"
        stage = str(n.get("stage") or "").strip().lower()
        if stage not in _STAGES:
            stage = "unknown"
        nodes.append({
            "id": nid, "label": str(n.get("label") or nid).strip(),
            "layer": layer, "module": module,
            "role": str(n.get("role") or "").strip(),
            "ticker": ticker, "listing": listing, "stage": stage,
            "note": str(n.get("note") or "").strip(),
        })

    valid_ids = {n["id"] for n in nodes}
    edges = []
    for e in raw.get("edges") or []:
        src, dst = slugify(str(e.get("from") or "")), slugify(str(e.get("to") or ""))
        if src not in valid_ids or dst not in valid_ids or src == dst:
            continue
        rel = str(e.get("rel") or "SUPPLIES_TO").strip().upper()
        if rel not in _RELS:
            rel = "SUPPLIES_TO"
        edges.append({"from": src, "to": dst, "rel": rel,
                      "note": str(e.get("note") or "").strip()})

    spine = [slugify(str(s)) for s in (raw.get("spine") or [])]
    spine = [s for s in spine if s in valid_ids]

    return {
        "id": slug,
        "title": str(raw.get("title") or theme).strip(),
        "theme": theme,
        "generated_at": _now_iso(),
        "generated_by": "claude",
        "status": "draft",
        "layers": layers,
        "modules": modules,
        "spine": spine,
        "nodes": nodes,
        "edges": edges,
    }


def generate(theme: str, agent: str | None = None) -> dict:
    """LLM-draft a supply chain for `theme` and persist it as YAML.

    `agent` overrides which LLM drafts the chain; when None the configured
    primary model (config/llm_config.json) is used.

    Raises RuntimeError on LLM failure / unparseable output.
    """
    theme = (theme or "").strip()
    if not theme:
        raise RuntimeError("empty theme")
    slug = slugify(theme)
    system_prompt = PROMPT_FILE.read_text(encoding="utf-8")
    user_prompt = (
        f"Theme: {theme}\n\n"
        "Build the US-equity supply chain for this theme. Return the JSON block "
        "per the schema."
    )
    # Governed call: `--agent X` pins a preferred model; otherwise the
    # configured chain is used. Either way it falls back on quota / failure.
    if agent:
        res = run_with_fallback(agent.lower().strip(), "generate",
                                system_prompt, user_prompt, timeout=240)
    else:
        res = run_role("generate", system_prompt, user_prompt, timeout=240)
    model = getattr(res, "model_used", res.agent)
    if res.exit_code != 0:
        raise RuntimeError(f"LLM failed (rc={res.exit_code}, route={getattr(res,'route_note','')}): {res.error}")
    if not res.parsed:
        raise RuntimeError(f"could not parse LLM output (status={res.parse_status})")

    chain = _normalise(res.parsed, theme, slug)
    chain["generated_by"] = model
    if not chain["nodes"]:
        raise RuntimeError("LLM returned no usable nodes")

    CHAINS_DIR.mkdir(parents=True, exist_ok=True)
    path = CHAINS_DIR / f"{slug}.yaml"
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(chain, fh, allow_unicode=True, sort_keys=False, width=100)
    return chain


# ─────────────────────────── enrichment ─────────────────────────────────────
def _universe_symbols() -> set[str]:
    try:
        d = json.loads(UNIVERSE_FILE.read_text(encoding="utf-8"))
        return {str(t.get("ticker", "")).upper() for t in d.get("tickers", [])}
    except (json.JSONDecodeError, OSError):
        return set()


def _nexus_index() -> tuple[set[str], dict[str, dict]]:
    """Return (lowercased label set, ticker->node dict) from the Nexus graph."""
    labels: set[str] = set()
    tickers: dict[str, dict] = {}
    try:
        d = json.loads(NEXUS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return labels, tickers
    for n in d.get("nodes", []):
        lbl = str(n.get("label", "")).strip().lower()
        if lbl:
            labels.add(lbl)
        if n.get("type") == "ticker":
            tickers[str(n.get("label", "")).upper()] = n
    return labels, tickers


def nexus_themes() -> list[str]:
    """Theme / narrative node labels from the Nexus graph — quick-pick options."""
    try:
        d = json.loads(NEXUS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    seen, out = set(), []
    for n in d.get("nodes", []):
        if n.get("type") not in ("theme", "narrative"):
            continue
        lbl = str(n.get("label", "")).strip()
        key = lbl.lower()
        if lbl and key not in seen:
            seen.add(key)
            out.append(lbl)
    return sorted(out)


def _heat(mentions: int) -> str:
    if mentions >= 40:
        return "hot"
    if mentions >= 15:
        return "warm"
    if mentions > 0:
        return "cold"
    return "none"


def _nexus_edge_index() -> dict:
    """Return {(ticker_a, ticker_b): {count, types, sources}} for ticker↔ticker
    edges in the Nexus graph. The key pair is sorted so lookups are
    direction-agnostic. Nexus edges already fold in break-news debate relations
    (SUPPLIES_TO / BENEFITS_FROM / COMPETES_WITH …), so this is how a supply-
    chain edge gets cross-checked against real debates."""
    idx: dict = {}
    try:
        d = json.loads(NEXUS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return idx
    for e in d.get("edges", []):
        s, tg = str(e.get("source", "")), str(e.get("target", ""))
        if not s.startswith("ticker:") or not tg.startswith("ticker:"):
            continue
        a, b = s[7:].upper(), tg[7:].upper()
        if not a or not b or a == b:
            continue
        slot = idx.setdefault(tuple(sorted((a, b))),
                              {"count": 0, "types": set(), "sources": set()})
        slot["count"] += 1
        if e.get("type"):
            slot["types"].add(str(e["type"]))
        for src in e.get("sources") or []:
            slot["sources"].add(str(src))
    return idx


def enrich(chain: dict) -> dict:
    """Add live `grounding` + `heat` to each node and `corroboration` to each
    edge. Returns the same dict."""
    universe = _universe_symbols()
    nexus_labels, nexus_tickers = _nexus_index()
    for n in chain.get("nodes", []):
        ticker = (n.get("ticker") or "").upper()
        label = (n.get("label") or "").strip().lower()
        if ticker and ticker in universe:
            n["grounding"] = "verified"
        elif ticker or label in nexus_labels:
            # a real symbol we don't track, or a name the Nexus graph has seen
            n["grounding"] = "seen"
        else:
            n["grounding"] = "llm_only"
        nx = nexus_tickers.get(ticker) if ticker else None
        n["heat"] = _heat(int(nx.get("mentions", 0))) if nx else "none"

    # Edge corroboration — is this LLM-drafted chain edge backed by a Nexus
    # ticker↔ticker edge (which carries break-news + digest relations)?
    node_ticker = {n.get("id"): (n.get("ticker") or "").upper()
                   for n in chain.get("nodes", [])}
    edge_idx = _nexus_edge_index()
    for e in chain.get("edges", []):
        ta, tb = node_ticker.get(e.get("from")), node_ticker.get(e.get("to"))
        hit = edge_idx.get(tuple(sorted((ta, tb)))) if (ta and tb and ta != tb) else None
        if hit:
            sources = sorted(hit["sources"])
            e["corroboration"] = {
                "count":       len(sources) or hit["count"],
                "nexus_types": sorted(hit["types"]),
                "sources":     sources[:8],
            }
        else:
            e["corroboration"] = None
    return chain


# ─────────────────────────── CLI ────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", required=True, help="theme / technology to map")
    ap.add_argument("--agent", choices=list(VALID_MODELS), default=None,
                    help="LLM to draft the chain (default: configured primary)")
    args = ap.parse_args()
    try:
        chain = generate(args.theme, agent=args.agent)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    enrich(chain)
    print(f"wrote {CHAINS_DIR / (chain['id'] + '.yaml')} (generated_by={chain.get('generated_by')})")
    print(f"  {len(chain['nodes'])} nodes, {len(chain['edges'])} edges, "
          f"{len(chain['layers'])} layers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
