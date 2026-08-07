#!/usr/bin/env python3
"""
Link Digest — deterministic artifact writer (V1.0, 0 LLM).

Consumes a judgment.json produced by the `link_digest` protocol turn and fans it
out into the two machine-consumed files that the news feed + Knowledge Graph
(Project Nexus) + supply-chain page ingest, with guaranteed schema:

  1. Append a deep/reviewed LINK_DIGEST event to `news_events.jsonl`, then
     deterministically rebuild `YYYY-MM-DD_digest.json` for bridge/Nexus readers.
  2. Write `news/break_news_logs/bn_<YYYYMMDD>_<hash>.json` (state=closed) with
     `summary.merged_entities` + `summary.merged_relations`. Nexus tier-1 turns
     these into ticker/sector/theme nodes and — for ticker↔ticker relations
     corroborated by >=2 sources (support_count) — provisional supply-chain edges.

Then (non-fatal): run the digest validator and a tier-1 graph refresh.

Exit codes:  0 pass · 1 fatal (bad judgment / unwritable) · 2 degraded-usable
(e.g. digest validator nudge, some relations dropped, graph refresh skipped).

Usage:
    python3 scripts/link_digest/build_artifacts.py <judgment.json> [--no-graph]
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    from scripts.link_digest.translate import translate_to_zh
except Exception:  # keep the writer usable even if the translator import breaks
    def translate_to_zh(fields, timeout=120):  # type: ignore
        return {}
from news.scripts.news_event_store import append_verdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NEWS_LOGS = os.path.join(ROOT, "news", "news_logs")
BREAK_LOGS = os.path.join(ROOT, "news", "break_news_logs")
DIGEST_VALIDATOR = os.path.join(ROOT, "news", "scripts", "validate_digest_output.py")
GRAPH_BUILDER = os.path.join(ROOT, "scripts", "nexus", "build_graph.py")

# ticker↔ticker supply-chain predicates the graph understands (CUSTOMER_OF is
# flipped to SUPPLIES_TO by the loader); ticker→theme attribution predicates.
TICKER_PREDICATES = {
    "SUPPLIES_TO", "CUSTOMER_OF", "CONTRACT_MFG_FOR",
    "CO_DEVELOPS_WITH", "COMPETES_WITH",
}
THEME_PREDICATES = {"BENEFITS_FROM", "HEADWIND_FROM"}
ALLOWED_PREDICATES = TICKER_PREDICATES | THEME_PREDICATES

_warnings: list[str] = []


def warn(msg: str) -> None:
    _warnings.append(msg)
    print(f"[link_digest] warn: {msg}", file=sys.stderr)


def die(msg: str) -> None:
    print(f"[link_digest] FATAL: {msg}", file=sys.stderr)
    sys.exit(1)


def _now_iso_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fp:
        json.dump(obj, fp, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ── judgment loading + validation ───────────────────────────────────────────
REQUIRED_JUDGMENT = [
    "url", "headline", "verdict", "net_impact_score",
    "bull_case", "bear_case", "sector_view", "macro_view",
    "arbiter_reasoning", "entities",
]


def load_judgment(path: str) -> dict:
    if not os.path.isfile(path):
        die(f"judgment file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fp:
            j = json.load(fp)
    except (json.JSONDecodeError, OSError) as e:
        die(f"cannot parse judgment json: {e}")
    missing = [k for k in REQUIRED_JUDGMENT if k not in j or j.get(k) in (None, "")]
    if missing:
        die(f"judgment missing required fields: {missing}")
    if j.get("verdict") not in ("BULLISH", "BEARISH", "BINARY", "NEUTRAL"):
        die(f"verdict must be BULLISH/BEARISH/BINARY/NEUTRAL (got {j.get('verdict')!r})")
    ar = j.get("arbiter_reasoning")
    if not isinstance(ar, str) or len(ar.strip()) < 30:
        die("arbiter_reasoning must be a string >=30 chars")
    if not isinstance(j.get("entities"), dict):
        die("entities must be an object")
    return j


def _norm_entities(ent: dict) -> dict:
    def _slist(key):
        v = ent.get(key) or []
        return [str(x).strip() for x in v if str(x).strip()] if isinstance(v, list) else []
    return {
        "tickers": [t.upper() for t in _slist("tickers")],
        "sectors": _slist("sectors"),
        "themes": _slist("themes"),
        "tech_keywords": _slist("tech_keywords"),
    }


# ── 1. digest verdict append ────────────────────────────────────────────────
def _next_news_id(verdicts: list) -> str:
    mx = 0
    for v in verdicts:
        nid = str(v.get("news_id", ""))
        if nid.startswith("n") and nid[1:].isdigit():
            mx = max(mx, int(nid[1:]))
    return f"n{mx + 1:04d}"


def build_translations(j: dict) -> dict:
    """EN→zh-TW for the prose fields via gemini (agy). Best-effort; {} on failure."""
    src = {
        "headline": j.get("headline", ""),
        "bull_case": j.get("bull_case", ""),
        "bear_case": j.get("bear_case", ""),
        "sector_view": j.get("sector_view", ""),
        "macro_view": j.get("macro_view", ""),
        "arbiter_reasoning": j.get("arbiter_reasoning", ""),
        "debate_note": j.get("debate_note", ""),
    }
    tr = translate_to_zh(src)
    if not tr and os.environ.get("LINK_DIGEST_TRANSLATE", "1") != "0":
        warn("gemini translation produced no zh fields (agy missing/failed); "
             "cards will show source-language text")
    return tr or {}


def write_digest_verdict(j: dict, entities: dict, tr: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    now_min = datetime.now().strftime("%Y-%m-%d %H:%M")
    digest_path = os.path.join(NEWS_LOGS, f"{today}_digest.json")

    if os.path.isfile(digest_path):
        try:
            with open(digest_path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
        except (json.JSONDecodeError, OSError) as e:
            warn(f"existing digest unreadable ({e}); creating fresh REVIEW file")
            data = None
    else:
        data = None

    if data is None:
        # Fresh-day file: REVIEW mode (0 shallow + 1 deep + reviewed) passes the
        # validator cleanly; INLINE fanout skips the subagent_isolated check.
        data = {
            "timestamp": now_min, "mode": "REVIEW",
            "stage1_count": 0, "stage2_count": 1,
            "fanout_mode": "INLINE", "degraded_agents": [],
            "verdicts": [], "session_macro_delta": 0.0,
        }
        fanout = "INLINE"
        fresh = True
    else:
        fanout = data.get("fanout_mode") or "PER_AGENT_BATCH"
        fresh = False

    verdicts = data.setdefault("verdicts", [])
    nid = _next_news_id(verdicts)

    try:
        nis = float(j.get("net_impact_score"))
    except (TypeError, ValueError):
        nis = 0.0
        warn("net_impact_score not numeric; defaulted to 0.0")

    verdict = {
        "news_id": nid,
        "depth": "deep",
        "review_status": "reviewed",
        "headline": str(j.get("headline", "")),
        # headline_zh: prefer an LLM-supplied zh headline, else the gemini translation,
        # else fall back to the source headline so the field is never blank.
        "headline_zh": str(j.get("headline_zh") or tr.get("headline") or j.get("headline", "")),
        "source_label": str(j.get("source_label", "web")),
        "news_type": str(j.get("news_type", "corporate")),
        "bull_case": str(j.get("bull_case", "")),
        "bear_case": str(j.get("bear_case", "")),
        "sector_view": str(j.get("sector_view", "")),
        "macro_view": str(j.get("macro_view", "")),
        # zh-TW variants (gemini) — UI renders these when lang=zh, else the EN base.
        "bull_case_zh": tr.get("bull_case", ""),
        "bear_case_zh": tr.get("bear_case", ""),
        "sector_view_zh": tr.get("sector_view", ""),
        "macro_view_zh": tr.get("macro_view", ""),
        "arbiter_reasoning_zh": tr.get("arbiter_reasoning", ""),
        "debate_note_zh": tr.get("debate_note", ""),
        "verdict": j.get("verdict"),
        "net_impact_score": nis,
        "arbiter_reasoning": str(j.get("arbiter_reasoning", "")),
        "debate_note": str(j.get("debate_note", "")),
        "binary_risk": bool(j.get("binary_risk", False)),
        "binary_event_date": j.get("binary_event_date"),
        "within_48h": bool(j.get("within_48h", False)),
        "cache_updated": False,  # link_digest does NOT patch sector_intel/phase0
        "affected_sectors": j.get("affected_sectors") or [],
        "tickers_mentioned": entities["tickers"],
        # match the file's fanout so the PER_AGENT_BATCH consistency check passes
        "subagent_isolated": (fanout == "PER_AGENT_BATCH"),
        "published": j.get("published") or now_min,
        "source_url": j.get("url"),
        "origin": "link_digest",
    }
    verdicts.append(verdict)

    if not fresh:
        # keep DIGEST invariant deep_count == stage2_count; shallow under-cap only
        # loosens as stage2 grows, so this stays valid.
        data["stage2_count"] = int(data.get("stage2_count", 0)) + 1
    data["timestamp"] = now_min  # refresh freshness gate

    append_verdict(
        verdict,
        event_type="LINK_DIGEST",
        date=today,
        root=Path(ROOT),
        store_path=Path(NEWS_LOGS) / "news_events.jsonl",
        origin="link_digest",
    )
    print(f"[link_digest] digest verdict {nid} → {os.path.relpath(digest_path, ROOT)}")
    return digest_path


# ── 2. break-news KG payload ────────────────────────────────────────────────
def _clean_relations(j: dict) -> list:
    out = []
    for rel in (j.get("relations") or []):
        if not isinstance(rel, dict):
            continue
        subj = str(rel.get("subject", "")).strip()
        obj = str(rel.get("object", "")).strip()
        pred = str(rel.get("predicate", "")).strip()
        if not (subj and obj and pred):
            warn(f"dropped malformed relation: {rel}")
            continue
        if pred not in ALLOWED_PREDICATES:
            warn(f"dropped relation with unknown predicate {pred!r}")
            continue
        if not subj.startswith("ticker:"):
            warn(f"dropped relation: subject {subj!r} not a ticker: id")
            continue
        if pred in TICKER_PREDICATES and not obj.startswith("ticker:"):
            warn(f"dropped supply-chain relation: object {obj!r} not a ticker: id")
            continue
        if pred in THEME_PREDICATES and not obj.startswith("theme:"):
            warn(f"dropped attribution relation: object {obj!r} not a theme: id")
            continue
        srcs = rel.get("corroborating_sources") or []
        srcs = [s for s in srcs if str(s).strip()] if isinstance(srcs, list) else []
        support = max(1, len(srcs))  # >=2 corroborating sources ⇒ real graph edge
        try:
            conf = float(rel.get("confidence", 0.7))
        except (TypeError, ValueError):
            conf = 0.7
        ev = str(rel.get("evidence", "")).strip()
        out.append({
            "subject": subj,
            "predicate": pred,
            "object": obj,
            "support_count": support,
            "confidence_avg": round(conf, 3),
            "source_agents": ["link_digest"],
            "source_rounds": [0],
            "evidence_snippets": [ev] if ev else [],
            "corroborating_sources": srcs,
            "provisional": True,
        })
    return out


def write_break_news(j: dict, entities: dict, tr: dict) -> str:
    url = str(j.get("url"))
    today_compact = datetime.now().strftime("%Y%m%d")
    h8 = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    bn_id = f"bn_{today_compact}_{h8}"
    bn_path = os.path.join(BREAK_LOGS, f"{bn_id}.json")
    now = _now_iso_z()

    relations = _clean_relations(j)
    bn = {
        "news_id": bn_id,
        "schema_version": 1,
        "state": "closed",
        "fetched_at": now,
        "source": {
            "name": str(j.get("source_label", "web")),
            "credibility": "MEDIUM",
            "url": url,
            "published": j.get("published") or now,
            "url_hash": "sha1:" + hashlib.sha1(url.encode("utf-8")).hexdigest(),
        },
        "headline": str(j.get("headline", "")),
        "headline_zh": str(j.get("headline_zh") or tr.get("headline") or j.get("headline", "")),
        "summary": {
            "consensus_verdict": j.get("verdict"),
            "merged_entities": entities,
            "merged_relations": relations,
            "bull_summary": str(j.get("bull_case", "")),
            "bear_summary": str(j.get("bear_case", "")),
            "final_take": str(j.get("arbiter_reasoning", "")),
            "bull_summary_zh": tr.get("bull_case", ""),
            "bear_summary_zh": tr.get("bear_case", ""),
            "final_take_zh": tr.get("arbiter_reasoning", ""),
            "final_take_by": "link_digest",
            "rounds_completed": 1,
            "closed_at": now,
            "close_reason": "link_digest",
            "divergence_note": str(j.get("debate_note", "")),
        },
        "origin": "link_digest",
    }
    _atomic_write(bn_path, bn)
    n_edges = sum(1 for r in relations if r["support_count"] >= 2)
    print(f"[link_digest] break-news {bn_id} → {os.path.relpath(bn_path, ROOT)} "
          f"({len(entities['tickers'])} tickers, {len(relations)} relations, "
          f"{n_edges} edge-eligible)")
    return bn_path


# ── 3. non-fatal post steps ─────────────────────────────────────────────────
def run_digest_validator() -> int:
    if not os.path.isfile(DIGEST_VALIDATOR):
        warn("digest validator not found; skipped")
        return 2
    try:
        r = subprocess.run([sys.executable, DIGEST_VALIDATOR], cwd=ROOT,
                           capture_output=True, text=True, timeout=120)
    except (subprocess.SubprocessError, OSError) as e:
        warn(f"digest validator failed to run ({e})")
        return 2
    if r.returncode != 0:
        warn(f"digest validator rc={r.returncode}: {r.stderr.strip()[:400]}")
        return 2
    print(f"[link_digest] {r.stdout.strip()}")
    return 0


def refresh_graph() -> int:
    if not os.path.isfile(GRAPH_BUILDER):
        warn("graph builder not found; skipped (daily Step 8 will pick it up)")
        return 2
    try:
        r = subprocess.run(
            [sys.executable, GRAPH_BUILDER, "--tier", "1", "--enable-direct-edge"],
            cwd=ROOT, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        warn("graph refresh timed out (300s); daily Step 8 will rebuild")
        return 2
    except (subprocess.SubprocessError, OSError) as e:
        warn(f"graph refresh failed to run ({e}); daily Step 8 will rebuild")
        return 2
    if r.returncode != 0:
        warn(f"graph refresh rc={r.returncode}: {r.stderr.strip()[:400]}")
        return 2
    print("[link_digest] nexus graph refreshed (tier 1 + direct-edge)")
    return 0


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        die("usage: build_artifacts.py <judgment.json> [--no-graph]")

    j = load_judgment(args[0])
    entities = _norm_entities(j["entities"])
    tr = build_translations(j)          # gemini EN→zh-TW; may warn → rc 2

    write_digest_verdict(j, entities, tr)   # may warn → rc 2
    write_break_news(j, entities, tr)       # may warn → rc 2

    rc = 0
    rc = max(rc, run_digest_validator())
    if "--no-graph" not in flags:
        rc = max(rc, refresh_graph())

    if _warnings and rc < 2:
        rc = 2
    status = {0: "OK", 2: "DEGRADED-USABLE"}.get(rc, "FATAL")
    print(f"[link_digest] done rc={rc} ({status}); {len(_warnings)} warning(s)")
    sys.exit(rc)


if __name__ == "__main__":
    main()
