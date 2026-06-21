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
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.break_news.llm_drivers import run_llm, primary_model, VALID_MODELS  # noqa: E402, F401
from scripts._shared.model_router import run_role, run_with_fallback  # noqa: E402
from scripts._shared import fmp_pool  # noqa: E402

CHAINS_DIR = _ROOT / "nexus" / "supply_chains"
# User corrections live in a sidecar (keyed by node id) so the LLM-drafted YAML
# is never rewritten by the dashboard. enrich() merges them at serve time.
OVERRIDES_DIR = CHAINS_DIR / "overrides"
_OVERRIDE_FIELDS = {"ticker", "market", "listing", "adr_ticker", "local_ticker", "note", "proxy_tickers"}
_OVERRIDE_UPPER = {"ticker", "adr_ticker", "local_ticker", "market"}
_OVERRIDE_STATUS = {"confirmed", "flagged", "none"}
PROMPT_FILE = _ROOT / "scripts" / "nexus" / "prompts" / "supply_chain_system.md"
UNIVERSE_FILE = _ROOT / "Dashboard" / "heatmap_universe.json"
NEXUS_FILE = _ROOT / "Dashboard" / "nexus_graph.json"
REPORTS_DIR = _ROOT / "reports"
NEWS_LOG_DIR = _ROOT / "news" / "news_logs"
BREAK_NEWS_DIR = _ROOT / "news" / "break_news_logs"
FMP_SC_CACHE_DIR = _ROOT / "skills" / "_shared" / "fmp_supp_cache" / "supply_chain"

_LISTINGS = {"us_listed", "foreign_listed", "private", "pre_ipo"}
_RELS = {"SUPPLIES_TO", "CUSTOMER_OF", "CONTRACT_MFG_FOR", "CO_DEVELOPS_WITH", "INVESTOR_IN"}
# Commercialization stage of a company within the chain's theme (vs the spine
# subject). LLM seeds it from public evidence; the user refines it in the YAML.
_STAGES = {"design_partner", "sampling", "qualification", "production",
           "revenue", "unknown"}
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_FMP_BASE = "https://financialmodelingprep.com"
# Company profiles barely change; a long TTL keeps core nodes verified across
# many serves without re-spending budget (marketCap can drift but is not a
# decision input on this page).
_FMP_PROFILE_TTL_SEC = 30 * 86400
_FMP_PEERS_TTL_SEC = 86400
_FMP_SEARCH_TTL_SEC = 86400
# Paid-plan budget: RPM pacing is now the central fmp_pool's job, so this is
# just a per-day call-COUNT safety cap (raised from the old free-tier 150).
_FMP_DAILY_BUDGET = int(os.getenv("FMP_SUPP_DAILY_BUDGET", "2000"))
_FMP_NAME_SEARCH_LIMIT = int(os.getenv("SUPPLY_CHAIN_FMP_NAME_SEARCH_LIMIT", "20"))
_US_EXCHANGES = {"NASDAQ", "NYSE", "AMEX"}
_RELATION_CORMENTION_THRESHOLD = 3
# Heat: hot tercile is relative to the chain's own mention spread, but a node
# still needs this absolute floor so a dead chain can't manufacture a "hot" node.
_HEAT_HOT_FLOOR = 8
# A node with no live corroboration (llm_only grounding, no heat, no FMP profile)
# on a chain older than this is flagged stale for UI greying — never auto-deleted.
_STALE_DAYS = int(os.getenv("SUPPLY_CHAIN_STALE_DAYS", "45"))
_MARKET_LABELS = {
    "US": "US-listed",
    "TW": "Taiwan-listed",
    "KR": "Korea-listed",
    "JP": "Japan-listed",
    "CN": "China-listed",
    "HK": "Hong Kong-listed",
    "EU": "Europe-listed",
    "PRIVATE": "Private",
    "PREIPO": "Pre-IPO",
}
_EXCHANGE_MARKET = {
    "NASDAQ": "US", "NYSE": "US", "AMEX": "US",
    "TWSE": "TW", "TPEX": "TW", "TAI": "TW",
    "KRX": "KR", "KOE": "KR", "KSC": "KR", "KOSDAQ": "KR",
    "TSE": "JP", "TYO": "JP", "JPX": "JP",
    "HKSE": "HK", "HKG": "HK",
    "SSE": "CN", "SZSE": "CN", "SHH": "CN", "SHZ": "CN",
}

_ALIAS_TO_TICKER = {
    "TSMC": "TSM",
    "TAIWAN SEMICONDUCTOR": "TSM",
    "TAIWAN SEMICONDUCTOR MANUFACTURING": "TSM",
    "GOOG": "GOOGL",
    "GOOGL": "GOOGL",
    "ALPHABET": "GOOGL",
    "BRK.A": "BRK-B",
    "BRK-A": "BRK-B",
    "BRK.B": "BRK-B",
    "BRK-B": "BRK-B",
    "BERKSHIRE HATHAWAY": "BRK-B",
    "META PLATFORMS": "META",
    "FACEBOOK": "META",
}
_CLASS_SHARE_ALIASES = {"GOOG": "GOOGL", "BRK.A": "BRK-B", "BRK-A": "BRK-B", "BRK.B": "BRK-B"}

_FOREIGN_LISTING_BACKFILL = {
    "TSMC": {"market": "TW", "exchange": "TWSE", "local_ticker": "2330", "adr_ticker": "TSM", "country": "Taiwan"},
    "TAIWAN SEMICONDUCTOR": {"market": "TW", "exchange": "TWSE", "local_ticker": "2330", "adr_ticker": "TSM", "country": "Taiwan"},
    "SAMSUNG ELECTRONICS": {"market": "KR", "exchange": "KRX", "local_ticker": "005930", "country": "South Korea"},
    "SK HYNIX": {"market": "KR", "exchange": "KRX", "local_ticker": "000660", "country": "South Korea"},
    "LG INNOTEK": {"market": "KR", "exchange": "KRX", "local_ticker": "011070", "country": "South Korea"},
    "TOKYO ELECTRON": {"market": "JP", "exchange": "TSE", "local_ticker": "8035", "country": "Japan"},
    "ADVANTEST": {"market": "JP", "exchange": "TSE", "local_ticker": "6857", "country": "Japan"},
    "DISCO": {"market": "JP", "exchange": "TSE", "local_ticker": "6146", "country": "Japan"},
    "LASERTEC": {"market": "JP", "exchange": "TSE", "local_ticker": "6920", "country": "Japan"},
    "RENESAS": {"market": "JP", "exchange": "TSE", "local_ticker": "6723", "country": "Japan"},
    "MURATA": {"market": "JP", "exchange": "TSE", "local_ticker": "6981", "country": "Japan"},
    "IBIDEN": {"market": "JP", "exchange": "TSE", "local_ticker": "4062", "country": "Japan"},
    "SHINKO ELECTRIC": {"market": "JP", "exchange": "TSE", "local_ticker": "6967", "country": "Japan"},
    "HON HAI": {"market": "TW", "exchange": "TWSE", "local_ticker": "2317", "country": "Taiwan"},
    "FOXCONN": {"market": "TW", "exchange": "TWSE", "local_ticker": "2317", "country": "Taiwan"},
    "QUANTA": {"market": "TW", "exchange": "TWSE", "local_ticker": "2382", "country": "Taiwan"},
    "WISTRON": {"market": "TW", "exchange": "TWSE", "local_ticker": "3231", "country": "Taiwan"},
    "INVENTEC": {"market": "TW", "exchange": "TWSE", "local_ticker": "2356", "country": "Taiwan"},
    "PEGATRON": {"market": "TW", "exchange": "TWSE", "local_ticker": "4938", "country": "Taiwan"},
    "WIWYNN": {"market": "TW", "exchange": "TWSE", "local_ticker": "6669", "country": "Taiwan"},
    "DELTA ELECTRONICS": {"market": "TW", "exchange": "TWSE", "local_ticker": "2308", "country": "Taiwan"},
    "MEDIATEK": {"market": "TW", "exchange": "TWSE", "local_ticker": "2454", "country": "Taiwan"},
    "ASE": {"market": "TW", "exchange": "TWSE", "local_ticker": "3711", "adr_ticker": "ASX", "country": "Taiwan"},
    "ASE TECHNOLOGY": {"market": "TW", "exchange": "TWSE", "local_ticker": "3711", "adr_ticker": "ASX", "country": "Taiwan"},
    "GLOBALWAFERS": {"market": "TW", "exchange": "TPEX", "local_ticker": "6488", "country": "Taiwan"},
    "NANYA": {"market": "TW", "exchange": "TWSE", "local_ticker": "2408", "country": "Taiwan"},
    "WINBOND": {"market": "TW", "exchange": "TWSE", "local_ticker": "2344", "country": "Taiwan"},
    "ASML": {"market": "EU", "exchange": "EURONEXT", "local_ticker": "ASML", "adr_ticker": "ASML", "country": "Netherlands"},
    "ASM INTERNATIONAL": {"market": "EU", "exchange": "EURONEXT", "local_ticker": "ASM", "country": "Netherlands"},
    "INFINEON": {"market": "EU", "exchange": "XETRA", "local_ticker": "IFX", "country": "Germany"},
    "STMICROELECTRONICS": {"market": "EU", "exchange": "EURONEXT", "local_ticker": "STMPA", "adr_ticker": "STM", "country": "Switzerland"},
}


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


# ─────────────────────────── user overrides (sidecar) ───────────────────────
def _overrides_path(slug: str) -> Path:
    return OVERRIDES_DIR / f"{slugify(slug)}.json"


def load_overrides(slug: str) -> dict:
    """Per-node user corrections for a chain: {node_id: {status, note, fields}}."""
    try:
        data = json.loads(_overrides_path(slug).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_override(slug: str, node_id: str, *, status: str | None = None,
                  fields: dict | None = None, note: str | None = None) -> dict:
    """Upsert one node's override; clearing to status='none' with no note/fields
    removes the entry. Returns the full override map for the chain."""
    node_id = str(node_id or "").strip()
    if not node_id:
        raise ValueError("node_id required")
    data = load_overrides(slug)
    entry = dict(data.get(node_id) or {})
    if status is not None:
        if status not in _OVERRIDE_STATUS:
            raise ValueError(f"invalid status {status!r}")
        entry["status"] = status
    if note is not None:
        entry["note"] = str(note)[:280]
    if fields:
        clean = {}
        for k, v in fields.items():
            if k not in _OVERRIDE_FIELDS:
                continue
            if k == "proxy_tickers":
                clean[k] = [_normalise_symbol(x) for x in (v or []) if _normalise_symbol(x)][:8]
            elif k in _OVERRIDE_UPPER:
                clean[k] = str(v).strip().upper()
            else:
                clean[k] = str(v).strip()
        entry.setdefault("fields", {}).update(clean)
    entry["updated_at"] = _now_iso()
    if entry.get("status", "none") == "none" and not entry.get("fields") and not entry.get("note"):
        data.pop(node_id, None)
    else:
        data[node_id] = entry
    OVERRIDES_DIR.mkdir(parents=True, exist_ok=True)
    _cache_write(_overrides_path(slug), data)
    return data


def _apply_overrides(chain: dict) -> int:
    """Merge sidecar corrections into the chain before live enrichment.

    User fields win over the LLM draft (same precedence as a manual YAML edit),
    and a `user_status` / `user_note` is attached for the UI. Runs first so a
    corrected ticker flows through grounding + FMP verification.
    """
    overrides = load_overrides(str(chain.get("id") or ""))
    if not overrides:
        return 0
    applied = 0
    for n in chain.get("nodes", []):
        ov = overrides.get(str(n.get("id")))
        if not ov:
            continue
        for k, v in (ov.get("fields") or {}).items():
            if k in _OVERRIDE_FIELDS:
                n[k] = v
        n["user_status"] = ov.get("status") or ""
        n["user_note"] = ov.get("note") or ""
        n["user_override"] = True
        applied += 1
    return applied


# ─────────────────────────── local context helpers ──────────────────────────
def _theme_terms(theme: str) -> list[str]:
    """Search terms for local context. Keep narrow to avoid noisy prompts."""
    raw = (theme or "").strip()
    terms = {raw.lower(), slugify(raw).replace("_", " ").lower()}
    for part in re.split(r"[\s/_:;,\-]+", raw):
        part = part.strip().lower()
        if len(part) >= 4:
            terms.add(part)
    if slugify(raw) == "cerebras":
        terms.add("cbrs")
    return sorted(t for t in terms if t)


def _recent_context_paths(limit: int = 220) -> list[Path]:
    paths = [NEXUS_FILE]
    for root, patterns in (
        (REPORTS_DIR, ("*.md", "*.json")),
        (NEWS_LOG_DIR, ("*.json", "*.jsonl")),
        (BREAK_NEWS_DIR, ("*.json", "_raw/*.txt")),
    ):
        if not root.is_dir():
            continue
        for pat in patterns:
            paths.extend(root.glob(pat))
    uniq = []
    seen = set()
    for p in paths:
        if p in seen or not p.is_file():
            continue
        seen.add(p)
        uniq.append(p)
    uniq.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return uniq[:limit]


def _context_date(path: Path) -> str:
    m = re.search(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})", str(path))
    if not m:
        return ""
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def _clean_snippet(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:360]


def _compact_chain_for_prompt(chain: dict | None) -> str:
    """Small JSON snapshot of the prior chain for incremental reruns."""
    if not isinstance(chain, dict):
        return ""
    keep = {
        "id": chain.get("id"),
        "title": chain.get("title"),
        "theme": chain.get("theme"),
        "generated_at": chain.get("generated_at"),
        "generated_by": chain.get("generated_by"),
        "layers": chain.get("layers") or [],
        "modules": chain.get("modules") or {},
        "spine": chain.get("spine") or [],
        "nodes": [
            {k: n.get(k) for k in (
                "id", "label", "layer", "module", "role", "ticker", "listing",
                "market", "exchange", "local_ticker", "adr_ticker", "country",
                "proxy_tickers", "stage", "note"
            )}
            for n in (chain.get("nodes") or [])[:40]
            if isinstance(n, dict)
        ],
        "edges": [
            {k: e.get(k) for k in ("from", "to", "rel", "note")}
            for e in (chain.get("edges") or [])[:80]
            if isinstance(e, dict)
        ],
    }
    return json.dumps(keep, ensure_ascii=False, indent=2)


def _local_context_for_theme(theme: str, max_items: int = 18) -> str:
    """Extract small, repeatable local context for the LLM draft.

    This is deliberately local-only: no web calls from dashboard generation, but
    recent news/Nexus artifacts still keep ticker/company maps from going stale.
    """
    terms = _theme_terms(theme)
    if not terms:
        return ""
    items = []
    for path in _recent_context_paths():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lower = text.lower()
        hits = []
        for term in terms:
            start = lower.find(term)
            if start >= 0:
                hits.append(start)
        if not hits:
            continue
        for start in sorted(set(hits))[:2]:
            lo, hi = max(0, start - 180), min(len(text), start + 360)
            rel = path.relative_to(_ROOT)
            date = _context_date(path)
            prefix = f"{date} " if date else ""
            items.append(f"- {prefix}{rel}: {_clean_snippet(text[lo:hi])}")
            if len(items) >= max_items:
                return "\n".join(items)
    return "\n".join(items)


def _audit_chain(chain: dict, context: str) -> list[str]:
    warnings: list[str] = []
    ctx = (context or "").lower()
    labels = {
        str(n.get("id", "")).lower()
        for n in chain.get("nodes", [])
    } | {
        str(n.get("label", "")).lower()
        for n in chain.get("nodes", [])
    } | {
        str(n.get("ticker", "")).lower()
        for n in chain.get("nodes", []) if n.get("ticker")
    }

    important = {
        "openai": "OpenAI",
        "amazon web services": "Amazon Web Services / AWS",
        "aws": "Amazon Web Services / AWS",
        "g42": "G42",
        "tsmc": "TSMC",
        "alphasense": "AlphaSense",
        "cognition": "Cognition",
        "mistral": "Mistral AI",
        "openrouter": "OpenRouter",
        "hugging face": "Hugging Face",
        "meta llama": "Meta Llama API",
    }
    for needle, display in important.items():
        if needle in ctx and not any(needle in lbl for lbl in labels):
            warnings.append(f"recent context mentions {display}, but generated nodes omit it")

    for n in chain.get("nodes", []):
        label = str(n.get("label", "")).lower()
        if "cerebras" in label and ("nasdaq" in ctx or "ticker symbol" in ctx or "cbrs" in ctx):
            if n.get("listing") != "us_listed" or not n.get("ticker"):
                warnings.append("theme company appears public in context but node is not us_listed with ticker")
        note = str(n.get("note") or "").lower()
        if any(x in note for x in ("推測", "unconfirmed", "未公開")) and n.get("stage") != "unknown":
            warnings.append(f"node {n.get('id')} has unconfirmed note but stage={n.get('stage')}")

    customer_layers = {"end_customer", "customer", "customers", "cloud_deployment", "systems"}
    customer_count = sum(1 for n in chain.get("nodes", []) if n.get("layer") in customer_layers)
    if customer_count < 4:
        warnings.append("downstream/customer side is sparse; check anchor customers and distribution channels")
    return warnings[:12]


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
            "market": str(n.get("market") or "").strip().upper(),
            "exchange": str(n.get("exchange") or "").strip().upper(),
            "local_ticker": str(n.get("local_ticker") or "").strip().upper(),
            "adr_ticker": _normalise_symbol(n.get("adr_ticker")),
            "country": str(n.get("country") or "").strip(),
            "investability": str(n.get("investability") or "").strip().lower(),
            "proxy_tickers": [
                _normalise_symbol(x) for x in (n.get("proxy_tickers") or [])
                if _normalise_symbol(x)
            ][:8],
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


def generate(theme: str, agent: str | None = None, *,
             previous_chain: dict | None = None, rerun: bool = False) -> dict:
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
    local_context = _local_context_for_theme(theme)
    prior = _compact_chain_for_prompt(previous_chain) if rerun else ""
    if rerun and prior:
        user_prompt = (
            f"Theme: {theme}\n\n"
            f"Refresh mode: incremental rerun\n\n"
            + (f"Recent local context (treat as latest mandatory source context):\n"
               f"{local_context}\n\n" if local_context else "")
            + "Previous chain JSON:\n"
            + prior
            + "\n\nUpdate the previous chain rather than rebuilding from scratch. "
              "Preserve nodes, layers, modules, and edges that still look valid; "
              "add, remove, or relabel only when the recent context or latest public "
              "market/source information justifies it. If your runtime has web/search "
              "access, use current public sources to refresh market developments, but "
              "do not invent private design-ins. Mark notes with confirmed / "
              "industry_report / inferred / stale / contested as appropriate. Return "
              "the full JSON block per the schema."
        )
    else:
        user_prompt = (
            f"Theme: {theme}\n\n" +
            (f"Recent local context:\n{local_context}\n\n" if local_context else "") +
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
    chain["refresh_mode"] = "rerun_incremental" if rerun and previous_chain else "full_generate"
    chain["source_scope"] = (
        "previous_chain + recent local context + model-available public sources"
        if rerun and previous_chain else
        "recent local context + model prior knowledge / model-available public sources"
    )
    if rerun and isinstance(previous_chain, dict):
        chain["previous_generated_at"] = previous_chain.get("generated_at") or ""
        chain["previous_generated_by"] = previous_chain.get("generated_by") or ""
    if not chain["nodes"]:
        raise RuntimeError("LLM returned no usable nodes")
    warnings = _audit_chain(chain, local_context)
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)

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


def _percentile(sorted_vals: list[int], pct: float) -> float:
    """Nearest-rank percentile on a pre-sorted ascending list."""
    if not sorted_vals:
        return 0.0
    k = max(0, min(len(sorted_vals) - 1, int(round((pct / 100.0) * (len(sorted_vals) - 1)))))
    return float(sorted_vals[k])


def _heat_relative(mentions: int, positives: list[int]) -> str:
    """Heat graded against this chain's own mention spread.

    `positives` is the ascending list of >0 mention counts across the chain's
    nodes. With a thin sample (<4 active nodes) the absolute `_heat` ladder is
    used so a 2-node chain can't crown a "hot" node off a single mention. The
    `_HEAT_HOT_FLOOR` guard keeps a low-activity chain from minting "hot".
    """
    if mentions <= 0:
        return "none"
    if len(positives) < 4:
        return _heat(mentions)
    hi = _percentile(positives, 67)
    lo = _percentile(positives, 33)
    if mentions >= hi and mentions >= _HEAT_HOT_FLOOR:
        return "hot"
    if mentions >= lo:
        return "warm"
    return "cold"


def _chain_age_days(chain: dict) -> float | None:
    """Days since the chain YAML was generated; None if unparseable."""
    raw = str(chain.get("generated_at") or "").strip()
    if not raw:
        return None
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).total_seconds() / 86400.0


def _cache_dir(kind: str) -> Path:
    p = FMP_SC_CACHE_DIR / kind
    p.mkdir(parents=True, exist_ok=True)
    return p


def _cache_read(path: Path, ttl_sec: int):
    try:
        if not path.is_file() or (time.time() - path.stat().st_mtime) > ttl_sec:
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _cache_write(path: Path, payload) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def _budget_path(day: str | None = None) -> Path:
    day = day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    FMP_SC_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return FMP_SC_CACHE_DIR / f"_budget_{day}.json"


def _budget_state() -> dict:
    p = _budget_path()
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("date") == day:
            data.setdefault("calls_used", 0)
            data.setdefault("budget", _FMP_DAILY_BUDGET)
            data.setdefault("budget_exhausted", False)
            return data
    except (OSError, json.JSONDecodeError):
        pass
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
    return {
        "date": day,
        "calls_used": 0,
        "budget": _FMP_DAILY_BUDGET,
        "budget_exhausted": False,
        "reset_at": f"{tomorrow}T00:00:00Z",
    }


def _budget_save(state: dict) -> None:
    _cache_write(_budget_path(state.get("date")), state)


def _budget_can_call() -> bool:
    state = _budget_state()
    return not state.get("budget_exhausted") and int(state.get("calls_used", 0)) < int(state.get("budget", _FMP_DAILY_BUDGET))


def _budget_headroom() -> float:
    """Fraction of the daily FMP call budget still unspent (0.0–1.0)."""
    state = _budget_state()
    budget = max(1, int(state.get("budget", _FMP_DAILY_BUDGET)))
    return max(0.0, 1.0 - int(state.get("calls_used", 0)) / budget)


def _budget_note_call(status_code: int | None = None) -> None:
    state = _budget_state()
    state["calls_used"] = int(state.get("calls_used", 0)) + 1
    if state["calls_used"] >= int(state.get("budget", _FMP_DAILY_BUDGET)):
        state["budget_exhausted"] = True
    if status_code in (401, 402, 403, 429):
        state["budget_exhausted"] = True
        state["last_status"] = status_code
    _budget_save(state)


def _fmp_get(path: str, params: dict, *, timeout: int = 12):
    api_key = os.getenv("FMP_API_KEY")
    if not api_key or not _budget_can_call():
        return None, "unavailable"
    status = None
    try:
        # Count this call against the shared 250/min window before issuing
        # (keeps the (raw, status) tuple + budget_exhausted contract intact —
        # we keep our own transport so status_code stays observable downstream).
        fmp_pool.acquire_slot(block=True)
        r = requests.get(
            f"{_FMP_BASE}{path}",
            params={**params, "apikey": api_key},
            timeout=timeout,
        )
        status = r.status_code
        _budget_note_call(status)
        if status in (401, 402, 403, 429):
            return None, "budget_exhausted"
        if status != 200:
            return None, f"http_{status}"
        return r.json(), "ok"
    except Exception:
        _budget_note_call(status)
        return None, "network_error"


def _profile_cache_path(ticker: str) -> Path:
    return _cache_dir("profile") / f"{ticker.upper()}.json"


def _peers_cache_path(ticker: str) -> Path:
    return _cache_dir("peers") / f"{ticker.upper()}.json"


def _search_cache_path(name: str) -> Path:
    h = hashlib.sha1(name.strip().lower().encode("utf-8")).hexdigest()[:12]
    return _cache_dir("search_name") / f"{h}.json"


def _exchange_ok(profile: dict) -> bool:
    ex = str(profile.get("exchangeShortName") or "").upper().strip()
    ex_full = str(profile.get("exchange") or "").upper()
    return ex in _US_EXCHANGES or any(token in ex_full for token in _US_EXCHANGES)


def _slim_profile(profile: dict) -> dict:
    return {
        "symbol": profile.get("symbol"),
        "companyName": profile.get("companyName"),
        "exchange": profile.get("exchangeShortName") or profile.get("exchange"),
        "country": profile.get("country"),
        "currency": profile.get("currency"),
        "sector": profile.get("sector"),
        "industry": profile.get("industry"),
        "marketCap": profile.get("marketCap"),
    }


def _market_from_exchange(exchange: str | None) -> str:
    ex = str(exchange or "").upper().strip()
    if not ex:
        return ""
    if ex in _EXCHANGE_MARKET:
        return _EXCHANGE_MARKET[ex]
    if ex.endswith(".TW"):
        return "TW"
    if ex.endswith(".KS") or ex.endswith(".KQ"):
        return "KR"
    if ex.endswith(".T"):
        return "JP"
    return ""


def _foreign_backfill_for_node(node: dict) -> dict:
    if str(node.get("listing") or "") != "foreign_listed":
        return {}
    haystack = " ".join([
        str(node.get("label") or ""),
        str(node.get("id") or "").replace("_", " "),
    ]).upper()
    haystack = re.sub(r"[^A-Z0-9]+", " ", haystack).strip()
    for needle, meta in _FOREIGN_LISTING_BACKFILL.items():
        key = re.sub(r"[^A-Z0-9]+", " ", needle.upper()).strip()
        if key and key in haystack:
            return meta
    return {}


def _apply_foreign_listing_backfill(node: dict) -> None:
    meta = _foreign_backfill_for_node(node)
    if not meta:
        return
    for key in ("market", "exchange", "local_ticker", "adr_ticker", "country"):
        if not node.get(key) and meta.get(key):
            node[key] = meta[key]


def _infer_market(node: dict, profile: dict | None = None) -> str:
    explicit = str(node.get("market") or "").upper().strip()
    if explicit:
        return explicit
    listing = str(node.get("listing") or "")
    if listing == "private":
        return "PRIVATE"
    if listing == "pre_ipo":
        return "PREIPO"
    if listing == "us_listed":
        return "US"
    ex = str(node.get("exchange") or "").upper().strip()
    prof_ex = str((profile or {}).get("exchange") or "").upper().strip()
    return _market_from_exchange(ex) or _market_from_exchange(prof_ex) or ("US" if node.get("ticker") else "FOREIGN")


def _market_label(market: str) -> str:
    m = str(market or "").upper().strip()
    return _MARKET_LABELS.get(m, f"{m}-listed" if m else "Unknown")


def _investability(node: dict, market: str) -> str:
    explicit = str(node.get("investability") or "").strip().lower()
    if explicit:
        return explicit
    listing = str(node.get("listing") or "")
    if listing == "us_listed" or market == "US":
        return "direct_us"
    if node.get("adr_ticker") or (node.get("ticker") and listing == "foreign_listed"):
        return "adr_or_us_proxy"
    if listing in ("private", "pre_ipo") or market in ("PRIVATE", "PREIPO"):
        return "not_tradeable"
    if listing == "foreign_listed":
        return "international_broker"
    return "unknown"


def _node_display_symbol(node: dict) -> str:
    market = str(node.get("market") or "").upper()
    if node.get("ticker") and market == "US":
        return f"US:{node['ticker']}"
    if node.get("local_ticker") and market and market not in ("PRIVATE", "PREIPO", "FOREIGN"):
        return f"{market}:{node['local_ticker']}"
    if node.get("adr_ticker"):
        return f"ADR:{node['adr_ticker']}"
    if node.get("ticker"):
        return str(node["ticker"])
    if market == "PREIPO":
        return "PRE-IPO"
    if market == "PRIVATE":
        return "PRIVATE"
    if market and market != "FOREIGN":
        return market
    return "FOREIGN" if node.get("listing") == "foreign_listed" else "PRIVATE"


def _node_investable(node: dict) -> bool:
    return str(node.get("investability") or "") in ("direct_us", "adr_or_us_proxy", "international_broker")


def _chain_report(chain: dict) -> dict:
    nodes = chain.get("nodes") or []
    edges = chain.get("edges") or []
    by_id = {n.get("id"): n for n in nodes}
    downstream_count: dict[str, int] = {}
    upstream_count: dict[str, int] = {}
    for e in edges:
        downstream_count[e.get("from")] = downstream_count.get(e.get("from"), 0) + 1
        upstream_count[e.get("to")] = upstream_count.get(e.get("to"), 0) + 1

    investable = [
        {
            "id": n.get("id"),
            "label": n.get("label"),
            "symbol": n.get("display_symbol") or _node_display_symbol(n),
            "market": n.get("market"),
            "market_label": n.get("market_label"),
            "investability": n.get("investability"),
            "stage": n.get("stage"),
            "heat": n.get("heat"),
            "verification_level": n.get("verification_level"),
            "downstream_links": downstream_count.get(n.get("id"), 0),
        }
        for n in nodes if _node_investable(n)
    ]
    investable.sort(key=lambda x: (
        0 if x.get("market") == "US" else 1,
        -int(x.get("downstream_links") or 0),
        str(x.get("label") or ""),
    ))

    private_proxy = []
    for n in nodes:
        if _node_investable(n):
            continue
        proxies = n.get("proxy_tickers") or []
        nearby = []
        for e in edges:
            other_id = e.get("to") if e.get("from") == n.get("id") else e.get("from") if e.get("to") == n.get("id") else None
            other = by_id.get(other_id)
            if other and _node_investable(other):
                nearby.append(other.get("display_symbol") or _node_display_symbol(other))
        private_proxy.append({
            "id": n.get("id"),
            "label": n.get("label"),
            "market": n.get("market"),
            "symbol": n.get("display_symbol") or _node_display_symbol(n),
            "proxy_tickers": sorted(set(proxies + nearby))[:8],
        })

    confidence = {"corroborated_relation": 0, "break_news_provisional": 0, "llm_relation": 0}
    high_conf_edges = []
    for e in edges:
        ev = e.get("relation_evidence") or {}
        level = str(ev.get("level") or "llm_relation")
        confidence[level] = confidence.get(level, 0) + 1
        if level in ("corroborated_relation", "break_news_provisional"):
            high_conf_edges.append({
                "from": (by_id.get(e.get("from")) or {}).get("label", e.get("from")),
                "to": (by_id.get(e.get("to")) or {}).get("label", e.get("to")),
                "rel": e.get("rel"),
                "level": level,
                "sources": (ev.get("sources") or [])[:3],
            })

    bottlenecks = [
        {
            "id": n.get("id"),
            "label": n.get("label"),
            "symbol": n.get("display_symbol") or _node_display_symbol(n),
            "role": n.get("role"),
            "market": n.get("market"),
            "downstream_links": downstream_count.get(n.get("id"), 0),
            "upstream_links": upstream_count.get(n.get("id"), 0),
            "stage": n.get("stage"),
            "heat": n.get("heat"),
        }
        for n in nodes
        if downstream_count.get(n.get("id"), 0) >= 2 or n.get("id") in set(chain.get("spine") or [])
    ]
    bottlenecks.sort(key=lambda x: (-int(x.get("downstream_links") or 0), str(x.get("label") or "")))

    return {
        "investable_nodes": investable[:12],
        "private_or_watch_only": private_proxy[:12],
        "bottlenecks": bottlenecks[:8],
        "relation_confidence": confidence,
        "high_confidence_edges": high_conf_edges[:8],
        "summary": {
            "investable_count": len(investable),
            "watch_only_count": len(private_proxy),
            "edge_count": len(edges),
        },
    }


def _normalise_symbol(symbol: str | None) -> str | None:
    if not symbol:
        return None
    sym = str(symbol).strip().upper().replace(".", "-")
    return _CLASS_SHARE_ALIASES.get(sym, sym)


def _node_alias_symbol(node: dict) -> str | None:
    parts = [
        str(node.get("ticker") or ""),
        str(node.get("label") or ""),
        str(node.get("id") or "").replace("_", " "),
    ]
    for raw in parts:
        key = raw.upper().strip()
        if key in _ALIAS_TO_TICKER:
            return _ALIAS_TO_TICKER[key]
        for alias, ticker in _ALIAS_TO_TICKER.items():
            if alias in key:
                return ticker
    return None


def _fetch_profiles_batch(symbols: list[str], errors: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    misses = []
    clean_symbols = {
        sym for sym in (_normalise_symbol(s) for s in symbols if s) if sym
    }
    for sym in sorted(clean_symbols):
        if not sym:
            continue
        cached = _cache_read(_profile_cache_path(sym), _FMP_PROFILE_TTL_SEC)
        if isinstance(cached, dict):
            out[sym] = cached
        else:
            misses.append(sym)
    if not misses:
        return out
    if not os.getenv("FMP_API_KEY") or not _budget_can_call():
        errors.append("profile_fetch_skipped")
        return out
    raw, status = _fmp_get("/stable/profile", {"symbol": ",".join(misses)})
    if status != "ok":
        errors.append(f"profile_fetch_{status}")
        return out
    rows = raw if isinstance(raw, list) else [raw] if isinstance(raw, dict) else []
    for row in rows:
        if not isinstance(row, dict) or not row.get("symbol"):
            continue
        sym = _normalise_symbol(row.get("symbol"))
        if not sym or not _exchange_ok(row):
            continue
        slim = _slim_profile(row)
        out[sym] = slim
        _cache_write(_profile_cache_path(sym), slim)
    return out


def _fetch_peers(symbol: str, errors: list[str], *, allow_network: bool = True) -> list[str]:
    sym = _normalise_symbol(symbol)
    if not sym:
        return []
    cached = _cache_read(_peers_cache_path(sym), _FMP_PEERS_TTL_SEC)
    if isinstance(cached, list):
        return cached[:8]
    # Budget tiering: a deferred (low-priority) node serves cache only — no call.
    if not allow_network:
        return []
    if not os.getenv("FMP_API_KEY") or not _budget_can_call():
        return []
    raw, status = _fmp_get("/stable/stock-peers", {"symbol": sym})
    if status != "ok":
        errors.append(f"peers_{sym}_{status}")
        return []
    peers: list[str] = []
    for row in raw if isinstance(raw, list) else []:
        peer = row.get("symbol") if isinstance(row, dict) else row if isinstance(row, str) else None
        peer = _normalise_symbol(peer)
        if peer and peer != sym and peer not in peers:
            peers.append(peer)
    peers = peers[:8]
    _cache_write(_peers_cache_path(sym), peers)
    return peers


def _search_name(name: str, errors: list[str]) -> dict | None:
    name = (name or "").strip()
    if not name:
        return None
    path = _search_cache_path(name)
    cached = _cache_read(path, _FMP_SEARCH_TTL_SEC)
    if isinstance(cached, dict):
        return cached or None
    if not os.getenv("FMP_API_KEY") or not _budget_can_call():
        return None
    raw, status = _fmp_get("/stable/search-name", {"query": name, "limit": 5})
    if status != "ok":
        errors.append(f"search_name_{status}")
        return None
    rows = raw if isinstance(raw, list) else []
    best = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        # search-name is a weak fallback; accept only US exchange matches so
        # foreign/common-name ambiguity does not get promoted as Company OK.
        if _exchange_ok(row):
            best = row
            break
    payload = _slim_profile(best) if isinstance(best, dict) else {}
    _cache_write(path, payload)
    return payload or None


def _digest_paths_30d() -> list[Path]:
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=30)
    out = []
    if not NEWS_LOG_DIR.is_dir():
        return out
    for path in NEWS_LOG_DIR.glob("*_digest.json"):
        date = _context_date(path)
        if not date:
            continue
        try:
            if datetime.fromisoformat(date).date() >= cutoff:
                out.append(path)
        except ValueError:
            continue
    return sorted(out)


def _digest_comention_index() -> dict[tuple[str, str], dict]:
    idx: dict[tuple[str, str], dict] = {}
    for path in _digest_paths_30d():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for v in data.get("verdicts") or []:
            tickers = sorted({
                _normalise_symbol(t)
                for t in (v.get("tickers_mentioned") or [])
                if _normalise_symbol(t)
            })
            if len(tickers) < 2:
                continue
            nid = str(v.get("news_id") or "")
            src = f"{path.name}:{nid}" if nid else path.name
            for i, a in enumerate(tickers):
                for b in tickers[i + 1:]:
                    if not a or not b or a == b:
                        continue
                    key = tuple(sorted((a, b)))
                    slot = idx.setdefault(key, {"count": 0, "sources": []})
                    slot["count"] += 1
                    if len(slot["sources"]) < 8:
                        slot["sources"].append(src)
    return idx


def _nexus_edge_index() -> dict:
    """Return ticker↔ticker Nexus edges indexed by unordered pair.

    Each entry keeps directed edge records so supply-chain enrichment can
    distinguish true upstream→downstream evidence from unrelated co-mentions or
    competitor/headwind edges.
    """
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
                              {"count": 0, "types": set(), "sources": set(), "edges": []})
        slot["count"] += 1
        if e.get("type"):
            slot["types"].add(str(e["type"]))
        for src in e.get("sources") or []:
            slot["sources"].add(str(src))
        slot["edges"].append({
            "source": a,
            "target": b,
            "type": str(e.get("type") or ""),
            "sources": set(str(src) for src in (e.get("sources") or [])),
            "metadata": e.get("metadata") if isinstance(e.get("metadata"), dict) else {},
        })
    return idx


def _normalise_chain_rel(rel: str | None, src: str, dst: str) -> tuple[str, str, str]:
    """Return comparable (upstream, relation, downstream) for a chain edge."""
    rel = str(rel or "SUPPLIES_TO").upper()
    if rel == "CUSTOMER_OF":
        return dst, "SUPPLIES_TO", src
    return src, rel, dst


def _node_primary_ticker(n: dict) -> str | None:
    """Best tradeable symbol for relation/edge indexing (ticker > alias > FMP)."""
    prof = n.get("fmp_profile") if isinstance(n.get("fmp_profile"), dict) else {}
    return _normalise_symbol(n.get("ticker") or n.get("alias_used") or prof.get("symbol"))


def _direction_check(nexus_hit: dict | None, src: str, dst: str,
                     chain_rel: str | None) -> str:
    """Validate the LLM edge direction against Nexus *directed* supply edges.

    Digest co-mentions are symmetric — they corroborate that two tickers are
    related, not who supplies whom. Nexus SUPPLIES_TO / CONTRACT_MFG_FOR edges
    (from link_digest / break_news relation extraction) carry real direction, so
    we use them to confirm or contradict the LLM's arrow:

      confirmed  — a directed supply edge agrees with the LLM orientation
      conflict   — directed supply edge(s) exist only in the opposite orientation
      unverified — no directed supply edge for this pair (default; no penalty)
    """
    if not nexus_hit:
        return "unverified"
    want_src, want_rel, want_dst = _normalise_chain_rel(chain_rel, src, dst)
    if want_rel != "SUPPLIES_TO":
        # Only flow relations have a meaningful upstream→downstream direction.
        return "unverified"
    agree = oppose = False
    for edge in nexus_hit.get("edges") or []:
        e_src = str(edge.get("source") or "").upper()
        e_dst = str(edge.get("target") or "").upper()
        e_rel = str(edge.get("type") or "").upper()
        e_src, e_rel, e_dst = _normalise_chain_rel(e_rel, e_src, e_dst)
        if e_rel not in ("SUPPLIES_TO", "CONTRACT_MFG_FOR"):
            continue
        if e_src == want_src and e_dst == want_dst:
            agree = True
        elif e_src == want_dst and e_dst == want_src:
            oppose = True
    if agree:
        return "confirmed"
    if oppose:
        return "conflict"
    return "unverified"


def _break_news_relation_evidence(nexus_hit: dict | None, src: str, dst: str,
                                  chain_rel: str | None) -> tuple[bool, list[str]]:
    """Does Nexus contain a compatible provisional Break News edge?"""
    if not nexus_hit:
        return False, []
    want_src, want_rel, want_dst = _normalise_chain_rel(chain_rel, src, dst)
    matched_sources: set[str] = set()
    for edge in nexus_hit.get("edges") or []:
        srcs = set(edge.get("sources") or set())
        if not any(s.startswith("break_news:") for s in srcs):
            continue
        meta = edge.get("metadata") or {}
        if meta and not meta.get("provisional"):
            continue
        edge_src = str(edge.get("source") or "").upper()
        edge_dst = str(edge.get("target") or "").upper()
        edge_rel = str(edge.get("type") or "").upper()
        edge_src, edge_rel, edge_dst = _normalise_chain_rel(edge_rel, edge_src, edge_dst)

        compatible = False
        if want_rel == "SUPPLIES_TO":
            compatible = edge_rel in ("SUPPLIES_TO", "CONTRACT_MFG_FOR") and edge_src == want_src and edge_dst == want_dst
        elif want_rel in ("CO_DEVELOPS_WITH", "COMPETES_WITH"):
            compatible = edge_rel == want_rel and {edge_src, edge_dst} == {want_src, want_dst}

        if compatible:
            matched_sources.update(s for s in srcs if s.startswith("break_news:"))
    return bool(matched_sources), sorted(matched_sources)


def enrich(chain: dict) -> dict:
    """Add live verification fields to nodes and relation evidence to edges.

    The YAML remains an LLM-drafted skeleton. FMP only verifies company/ticker
    existence and peer context; it never verifies supply-chain relations.
    Relation evidence is a local 30d digest co-mention count.
    """
    override_count = _apply_overrides(chain)
    universe = _universe_symbols()
    nexus_labels, nexus_tickers = _nexus_index()
    fmp_errors: list[str] = []
    fmp_key_present = bool(os.getenv("FMP_API_KEY"))

    # Budget tiering: spine, tickered, and high-fan-out (>=2 downstream) nodes are
    # verified first. When the daily FMP budget is more than half spent, peripheral
    # nodes serve cached peers only and skip name-search, so the structurally
    # important nodes never lose verification to a budget wipe-out.
    spine_ids = set(chain.get("spine") or [])
    _dstream: dict = {}
    for _e in chain.get("edges", []):
        _dstream[_e.get("from")] = _dstream.get(_e.get("from"), 0) + 1

    def _is_priority(node: dict) -> bool:
        nid = node.get("id")
        return (nid in spine_ids or bool(_normalise_symbol(node.get("ticker")))
                or _dstream.get(nid, 0) >= 2)

    budget_healthy = _budget_headroom() > 0.5
    deferred_count = 0

    profile_candidates: list[str] = []
    alias_by_node: dict[str, str] = {}
    for n in chain.get("nodes", []):
        exact = _normalise_symbol(n.get("ticker"))
        if exact:
            profile_candidates.append(exact)
        adr = _normalise_symbol(n.get("adr_ticker"))
        if adr:
            profile_candidates.append(adr)
        alias = _node_alias_symbol(n)
        if alias:
            alias_by_node[str(n.get("id"))] = alias
            profile_candidates.append(alias)
    profiles = _fetch_profiles_batch(profile_candidates, fmp_errors)

    # Pre-pass: collect each node's Nexus mention count so heat can be graded
    # against this chain's own spread (relative), not a global magic threshold.
    node_mentions: dict[str, int] = {}
    for n in chain.get("nodes", []):
        ticker = _normalise_symbol(n.get("ticker")) or ""
        nx = nexus_tickers.get(ticker) if ticker else None
        node_mentions[str(n.get("id"))] = int(nx.get("mentions", 0)) if nx else 0
    heat_positives = sorted(m for m in node_mentions.values() if m > 0)
    age_days = _chain_age_days(chain)

    name_searches_used = 0
    for n in chain.get("nodes", []):
        ticker = _normalise_symbol(n.get("ticker")) or ""
        label = (n.get("label") or "").strip().lower()
        if ticker and ticker in universe:
            n["grounding"] = "verified"
        elif ticker or label in nexus_labels:
            # a real symbol we don't track, or a name the Nexus graph has seen
            n["grounding"] = "seen"
        else:
            n["grounding"] = "llm_only"
        n["heat"] = _heat_relative(node_mentions.get(str(n.get("id")), 0), heat_positives)

        reasons: list[str] = []
        exact_profile = profiles.get(ticker) if ticker else None
        adr = _normalise_symbol(n.get("adr_ticker"))
        alias = alias_by_node.get(str(n.get("id")))
        adr_profile = profiles.get(adr) if adr else None
        alias_profile = profiles.get(alias) if alias else None
        profile = exact_profile or adr_profile or alias_profile
        if profile:
            if exact_profile:
                reasons.append("FMP profile matched ticker")
            elif adr_profile:
                reasons.append(f"FMP profile matched ADR {adr}")
            else:
                reasons.append(f"FMP profile matched alias {alias}")
                n["alias_used"] = alias
            n["verification_level"] = "fmp_profile"
            n["fmp_profile"] = profile
            peers_priority = budget_healthy or _is_priority(n)
            n["fmp_peers"] = _fetch_peers(
                str(profile.get("symbol") or ticker or alias), fmp_errors,
                allow_network=peers_priority)
            if not peers_priority and not n["fmp_peers"]:
                deferred_count += 1
        else:
            n["fmp_profile"] = None
            n["fmp_peers"] = []
            can_search = (
                fmp_key_present and _budget_can_call()
                and name_searches_used < _FMP_NAME_SEARCH_LIMIT
                and n.get("grounding") != "verified"
                and (budget_healthy or _is_priority(n))
            )
            match = None
            if can_search:
                name_searches_used += 1
                match = _search_name(str(n.get("label") or ""), fmp_errors)
            if match:
                n["verification_level"] = "name_match"
                n["fmp_profile"] = match
                reasons.append("FMP weak company-name match")
                # A foreign-listed name that resolves to a US exchange symbol is
                # almost always that company's ADR — promote it so the node
                # becomes a tradeable adr_or_us_proxy instead of an opaque
                # FOREIGN tile. search-name already gates on US exchanges.
                msym = _normalise_symbol(match.get("symbol"))
                if msym and n.get("listing") == "foreign_listed" and not n.get("adr_ticker"):
                    n["adr_ticker"] = msym
                    reasons.append(f"promoted name-match {msym} as ADR")
            elif not fmp_key_present or _budget_state().get("budget_exhausted"):
                n["verification_level"] = "fmp_unavailable"
                reasons.append("FMP verification skipped")
            elif n.get("grounding") in ("verified", "seen"):
                n["verification_level"] = "corroborated"
                reasons.append("Local universe/Nexus data supports company existence")
            else:
                n["verification_level"] = "llm_only"
                reasons.append("No local or FMP company corroboration")
        n["verification_reasons"] = reasons
        _apply_foreign_listing_backfill(n)
        market = _infer_market(n, n.get("fmp_profile") if isinstance(n.get("fmp_profile"), dict) else None)
        n["market"] = market
        n["market_label"] = _market_label(market)
        if not n.get("exchange") and isinstance(n.get("fmp_profile"), dict):
            n["exchange"] = str(n["fmp_profile"].get("exchange") or "").upper()
        if not n.get("country") and isinstance(n.get("fmp_profile"), dict):
            n["country"] = str(n["fmp_profile"].get("country") or "")
        n["investability"] = _investability(n, market)
        n["display_symbol"] = _node_display_symbol(n)

        # Stale: no live corroboration (llm_only grounding, no heat, no FMP
        # profile) on an aged chain. Advisory flag for UI greying — the node is
        # never dropped, since a real-but-quiet supplier can look identical.
        no_signal = (
            n.get("grounding") == "llm_only"
            and n.get("heat") == "none"
            and n.get("verification_level") == "llm_only"
        )
        if no_signal and age_days is not None and age_days > _STALE_DAYS:
            n["stale"] = True
            n["stale_reason"] = f"no live signal in {int(age_days)}d (>{_STALE_DAYS}d threshold)"
        else:
            n["stale"] = False
            n["stale_reason"] = ""

    # Relation evidence: strict ticker co-mentions in recent digest verdicts.
    node_ticker = {n.get("id"): _node_primary_ticker(n) for n in chain.get("nodes", [])}
    nexus_edges = _nexus_edge_index()
    edge_idx = _digest_comention_index()
    for e in chain.get("edges", []):
        ta, tb = node_ticker.get(e.get("from")), node_ticker.get(e.get("to"))
        pair = tuple(sorted((ta, tb))) if (ta and tb and ta != tb) else None
        hit = edge_idx.get(pair) if pair else None
        count = int((hit or {}).get("count") or 0)
        sources = list((hit or {}).get("sources") or [])[:8]
        ok = count >= _RELATION_CORMENTION_THRESHOLD

        # Check Nexus directed edges once: provisional break-news compatibility
        # and (separately) whether the LLM arrow direction is confirmed/conflicted.
        nexus_hit = nexus_edges.get(pair) if pair else None
        is_bn_provisional, bn_sources = (
            _break_news_relation_evidence(nexus_hit, ta, tb, e.get("rel"))
            if pair else (False, [])
        )
        direction = _direction_check(nexus_hit, ta, tb, e.get("rel")) if pair else "unverified"

        if ok:
            level = "corroborated_relation"
            weight = 1.0
            # A directed Nexus edge pointing the opposite way contradicts the LLM
            # arrow; co-mentions are symmetric so they can't rescue it — halve
            # confidence and flag rather than trust the orientation.
            if direction == "conflict":
                weight = 0.5
        elif is_bn_provisional:
            level = "break_news_provisional"
            weight = 0.2
            sources = sorted(list(set(sources + bn_sources)))[:8]
        else:
            level = "llm_relation"
            weight = 0.4

        e["relation_evidence"] = {
            "level": level,
            "weight": weight,
            "co_mention_count_30d": count,
            "threshold": _RELATION_CORMENTION_THRESHOLD,
            "direction": direction,
            "sources": sources,
            "method": "digest_tickers_mentioned_30d",
        }
        if ok:
            e["corroboration"] = {
                "count": count,
                "nexus_types": ["digest_co_mention"],
                "sources": sources,
                "weight": weight,
            }
        elif is_bn_provisional:
            e["corroboration"] = {
                "count": 0,
                "nexus_types": ["break_news_provisional"],
                "sources": sources,
                "weight": weight,
            }
        else:
            e["corroboration"] = None

    breakdown: dict[str, int] = {}
    for n in chain.get("nodes", []):
        lvl = str(n.get("verification_level") or "unknown")
        breakdown[lvl] = breakdown.get(lvl, 0) + 1
    bstate = _budget_state()
    chain["data_quality"] = {
        "fmp_enabled": fmp_key_present,
        "fmp_budget_exhausted": bool(bstate.get("budget_exhausted")),
        "fmp_calls_used_today": int(bstate.get("calls_used", 0)),
        "fmp_daily_budget": int(bstate.get("budget", _FMP_DAILY_BUDGET)),
        "fmp_nodes_checked": len(chain.get("nodes") or []),
        "fmp_errors": sorted(set(fmp_errors))[:12],
        "verification_breakdown": breakdown,
        "llm_only_count": breakdown.get("llm_only", 0),
        "corroborated_count": breakdown.get("corroborated", 0),
        "stale_node_count": sum(1 for n in chain.get("nodes", []) if n.get("stale")),
        "chain_age_days": round(age_days, 1) if age_days is not None else None,
        "override_count": override_count,
        "fmp_peers_deferred": deferred_count,
        "fmp_budget_headroom": round(_budget_headroom(), 2),
        "enriched_at": _now_iso(),
    }
    chain["chain_report"] = _chain_report(chain)
    return chain


# ─────────────────── corroborated-edge write-back (opt-in) ───────────────────
# enrich() stays strictly read-only (serve path). This explicit batch path is
# the *only* place supply-chain findings flow back into the Knowledge Graph: it
# lifts digest-corroborated, direction-clean edges into a bn_*.json that Nexus
# tier-1 promotes to provisional supply-chain edges. Sources are tagged
# `supply_chain` (never `break_news:`) so the next enrich() can't recycle them
# as independent break-news corroboration — no reinforcement loop.
def _corroborated_relations(chain: dict) -> list[dict]:
    by_id = {n.get("id"): n for n in chain.get("nodes", [])}
    out: list[dict] = []
    for e in chain.get("edges", []):
        ev = e.get("relation_evidence") or {}
        if ev.get("level") != "corroborated_relation" or ev.get("direction") == "conflict":
            continue
        ta = _node_primary_ticker(by_id.get(e.get("from")) or {})
        tb = _node_primary_ticker(by_id.get(e.get("to")) or {})
        if not ta or not tb or ta == tb:
            continue
        want_src, want_rel, want_dst = _normalise_chain_rel(e.get("rel"), ta, tb)
        count = int(ev.get("co_mention_count_30d") or 0)
        note = str(e.get("note") or "").strip()
        out.append({
            "subject": f"ticker:{want_src}",
            "predicate": want_rel,
            "object": f"ticker:{want_dst}",
            "support_count": max(2, count),
            "confidence_avg": round(float(ev.get("weight") or 1.0), 3),
            "source_agents": ["supply_chain"],
            "source_rounds": [0],
            "evidence_snippets": [note] if note else [],
            "corroborating_sources": list(ev.get("sources") or [])[:8],
            "provisional": True,
        })
    return out


def _build_edge_bn(relations: list[dict], tickers: list[str]) -> dict:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    sig = "|".join(sorted(f"{r['subject']}>{r['predicate']}>{r['object']}" for r in relations))
    h8 = hashlib.sha1(sig.encode("utf-8")).hexdigest()[:8]
    bn_id = f"bn_{today}_sc_{h8}"
    now = _now_iso()
    return {
        "news_id": bn_id,
        "schema_version": 1,
        "state": "closed",
        "fetched_at": now,
        "source": {
            "name": "supply_chain", "credibility": "MEDIUM", "url": "",
            "published": now,
            "url_hash": "sha1:" + hashlib.sha1(bn_id.encode("utf-8")).hexdigest(),
        },
        "headline": f"Supply-chain corroborated edges ({len(relations)})",
        "summary": {
            "consensus_verdict": "NEUTRAL",
            "merged_entities": {"tickers": tickers, "sectors": [], "themes": [], "tech_keywords": []},
            "merged_relations": relations,
            "final_take": "Digest-corroborated supply-chain edges promoted from the supply-chain explorer.",
            "final_take_by": "supply_chain",
            "rounds_completed": 1,
            "closed_at": now,
            "close_reason": "supply_chain_edge_export",
        },
        "origin": "supply_chain",
    }


def _refresh_graph_tier1() -> bool:
    import subprocess
    builder = _ROOT / "scripts" / "nexus" / "build_graph.py"
    if not builder.is_file():
        return False
    try:
        r = subprocess.run(
            [sys.executable, str(builder), "--tier", "1", "--enable-direct-edge"],
            cwd=str(_ROOT), capture_output=True, text=True, timeout=300)
        return r.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def export_corroborated_edges(slugs: list[str] | None = None, *,
                              refresh_graph: bool = False) -> dict:
    """Enrich saved chains and write corroborated edges to a bn_*.json for Nexus.

    Returns a summary dict; does nothing (written=None) when no corroborated,
    direction-clean edges exist. Deduplicates the same relation across chains,
    keeping the highest support_count and the union of corroborating sources.
    """
    if slugs:
        chains = [c for c in (load(s) for s in slugs) if c]
    else:
        chains = [c for c in (load(h["id"]) for h in list_chains()) if c]
    merged: dict[tuple, dict] = {}
    tickers: set[str] = set()
    for c in chains:
        enrich(c)
        for rel in _corroborated_relations(c):
            key = (rel["subject"], rel["predicate"], rel["object"])
            tickers.add(rel["subject"].split(":", 1)[1])
            tickers.add(rel["object"].split(":", 1)[1])
            cur = merged.get(key)
            if cur is None:
                merged[key] = rel
            else:
                cur["support_count"] = max(cur["support_count"], rel["support_count"])
                cur["corroborating_sources"] = sorted(
                    set(cur["corroborating_sources"]) | set(rel["corroborating_sources"])
                )[:8]
    relations = list(merged.values())
    if not relations:
        return {"written": None, "relations": 0, "edge_eligible": 0, "chains": len(chains)}
    payload = _build_edge_bn(relations, sorted(tickers))
    path = BREAK_NEWS_DIR / f"{payload['news_id']}.json"
    _cache_write(path, payload)
    eligible = sum(1 for r in relations if r["support_count"] >= 2)
    out = {
        "written": str(path.relative_to(_ROOT)),
        "relations": len(relations),
        "edge_eligible": eligible,
        "chains": len(chains),
        "graph_refreshed": False,
    }
    if refresh_graph:
        out["graph_refreshed"] = _refresh_graph_tier1()
    return out


# ─────────────────────────── CLI ────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", default=None, help="theme / technology to map")
    ap.add_argument("--agent", choices=list(VALID_MODELS), default=None,
                    help="LLM to draft the chain (default: configured primary)")
    ap.add_argument("--rerun", action="store_true",
                    help="refresh an existing chain incrementally using its prior YAML as context")
    ap.add_argument("--export-edges", action="store_true",
                    help="write digest-corroborated, direction-clean edges to a bn_*.json for Nexus (opt-in write-back)")
    ap.add_argument("--chain", action="append", default=None,
                    help="limit --export-edges to one or more chain slugs (repeatable)")
    ap.add_argument("--export-graph-refresh", action="store_true",
                    help="run a tier-1 graph refresh after --export-edges")
    args = ap.parse_args()

    if args.export_edges:
        res = export_corroborated_edges(args.chain, refresh_graph=args.export_graph_refresh)
        if not res.get("written"):
            print(f"no corroborated edges to export ({res['chains']} chains scanned)")
            return 0
        print(f"wrote {res['written']} — {res['relations']} relations "
              f"({res['edge_eligible']} edge-eligible) from {res['chains']} chains; "
              f"graph_refreshed={res['graph_refreshed']}")
        return 0

    if not args.theme:
        ap.error("--theme is required unless --export-edges is used")
    try:
        previous = load(slugify(args.theme)) if args.rerun else None
        chain = generate(args.theme, agent=args.agent,
                         previous_chain=previous,
                         rerun=args.rerun and previous is not None)
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
