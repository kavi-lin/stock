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

CHAINS_DIR = _ROOT / "nexus" / "supply_chains"
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
_FMP_PROFILE_TTL_SEC = 7 * 86400
_FMP_PEERS_TTL_SEC = 86400
_FMP_SEARCH_TTL_SEC = 86400
_FMP_DAILY_BUDGET = int(os.getenv("FMP_SUPP_DAILY_BUDGET", "150"))
_FMP_NAME_SEARCH_LIMIT = int(os.getenv("SUPPLY_CHAIN_FMP_NAME_SEARCH_LIMIT", "20"))
_US_EXCHANGES = {"NASDAQ", "NYSE", "AMEX"}
_RELATION_CORMENTION_THRESHOLD = 3

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
    local_context = _local_context_for_theme(theme)
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
        "sector": profile.get("sector"),
        "industry": profile.get("industry"),
        "marketCap": profile.get("marketCap"),
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


def _fetch_peers(symbol: str, errors: list[str]) -> list[str]:
    sym = _normalise_symbol(symbol)
    if not sym:
        return []
    cached = _cache_read(_peers_cache_path(sym), _FMP_PEERS_TTL_SEC)
    if isinstance(cached, list):
        return cached[:8]
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
    universe = _universe_symbols()
    nexus_labels, nexus_tickers = _nexus_index()
    fmp_errors: list[str] = []
    fmp_key_present = bool(os.getenv("FMP_API_KEY"))

    profile_candidates: list[str] = []
    alias_by_node: dict[str, str] = {}
    for n in chain.get("nodes", []):
        exact = _normalise_symbol(n.get("ticker"))
        if exact:
            profile_candidates.append(exact)
        alias = _node_alias_symbol(n)
        if alias:
            alias_by_node[str(n.get("id"))] = alias
            profile_candidates.append(alias)
    profiles = _fetch_profiles_batch(profile_candidates, fmp_errors)

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
        nx = nexus_tickers.get(ticker) if ticker else None
        n["heat"] = _heat(int(nx.get("mentions", 0))) if nx else "none"

        reasons: list[str] = []
        exact_profile = profiles.get(ticker) if ticker else None
        alias = alias_by_node.get(str(n.get("id")))
        alias_profile = profiles.get(alias) if alias else None
        profile = exact_profile or alias_profile
        if profile:
            if exact_profile:
                reasons.append("FMP profile matched ticker")
            else:
                reasons.append(f"FMP profile matched alias {alias}")
                n["alias_used"] = alias
            n["verification_level"] = "fmp_profile"
            n["fmp_profile"] = profile
            n["fmp_peers"] = _fetch_peers(str(profile.get("symbol") or ticker or alias), fmp_errors)
        else:
            n["fmp_profile"] = None
            n["fmp_peers"] = []
            can_search = (
                fmp_key_present and _budget_can_call()
                and name_searches_used < _FMP_NAME_SEARCH_LIMIT
                and n.get("grounding") != "verified"
            )
            match = None
            if can_search:
                name_searches_used += 1
                match = _search_name(str(n.get("label") or ""), fmp_errors)
            if match:
                n["verification_level"] = "name_match"
                n["fmp_profile"] = match
                reasons.append("FMP weak company-name match")
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

    # Relation evidence: strict ticker co-mentions in recent digest verdicts.
    node_ticker = {}
    for n in chain.get("nodes", []):
        prof = n.get("fmp_profile") if isinstance(n.get("fmp_profile"), dict) else {}
        node_ticker[n.get("id")] = _normalise_symbol(
            n.get("ticker") or n.get("alias_used") or prof.get("symbol")
        )
    nexus_edges = _nexus_edge_index()
    edge_idx = _digest_comention_index()
    for e in chain.get("edges", []):
        ta, tb = node_ticker.get(e.get("from")), node_ticker.get(e.get("to"))
        hit = edge_idx.get(tuple(sorted((ta, tb)))) if (ta and tb and ta != tb) else None
        count = int((hit or {}).get("count") or 0)
        sources = list((hit or {}).get("sources") or [])[:8]
        ok = count >= _RELATION_CORMENTION_THRESHOLD
        
        # Check if there's a compatible break-news provisional edge in Nexus.
        is_bn_provisional = False
        bn_sources: list[str] = []
        if ta and tb and ta != tb:
            nexus_hit = nexus_edges.get(tuple(sorted((ta, tb))))
            is_bn_provisional, bn_sources = _break_news_relation_evidence(
                nexus_hit, ta, tb, e.get("rel")
            )

        if ok:
            level = "corroborated_relation"
            weight = 1.0
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
        "enriched_at": _now_iso(),
    }
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
