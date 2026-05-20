#!/usr/bin/env python3
"""
Theme narrative confirmation — sidecar to `theme_detector.py` output.

The quant `theme_detector.py` caps `confidence` at Medium. This script reads its
latest cache, picks the top-N themes by heat, and asks an LLM (via the
multi-model router) whether the past ~14 days have produced material narrative
support — credible reporting, primary-source events, analyst escalation. When
the LLM confirms a theme, downstream consumers (Dashboard sector / bridge.py)
may surface it as `confidence=High`.

**Evidence-grounded** (v3.14.3): the script no longer asks the model to "find"
evidence — it gathers candidate news verdicts from the last 14 days of
`news/news_logs/*_digest.json` (filtered by each theme's representative_stocks)
and asks the model to **pick** evidence from that closed list. Bumps from
unknown `news_id` / hallucinated URLs are rejected at the validator. When no
evidence exists for a theme, the model is told to emit `none`.

Codex-compatibility: router-driven via `model_router.run_role(...)`, any of
claude / gemini / codex can drive it. Router exhausted → `narrate_mode=skipped`,
no error.

Usage:
    python3 skills/theme-detector/scripts/narrative_confirm.py            # latest cache
    python3 skills/theme-detector/scripts/narrative_confirm.py --input <path>
    python3 skills/theme-detector/scripts/narrative_confirm.py --top-n 5
    python3 skills/theme-detector/scripts/narrative_confirm.py --since-days 14
    python3 skills/theme-detector/scripts/narrative_confirm.py --dry-run

Output:
    skills/theme-detector/cache/theme_detector_<ts>.narrative.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from scripts._shared.model_router import run_role  # type: ignore
except Exception:
    run_role = None  # noqa: N816

CACHE_DIR        = PROJECT_ROOT / "skills/theme-detector/cache"
NEWS_DIGEST_DIR  = PROJECT_ROOT / "news/news_logs"
EVIDENCE_PER_THEME = 6   # cap LLM context

SYSTEM_PROMPT = (
    "You are a market-narrative analyst.\n\n"
    "For each theme below, decide whether the listed candidate evidence "
    "contains MATERIAL narrative support for the past ~14 days — credible "
    "first-party reporting, dated events (earnings / regulatory filings / "
    "official guidance), or notable analyst escalation across ≥2 independent "
    "sources.\n\n"
    "STRICT RULES:\n"
    "- You may ONLY cite from each theme's `evidence_candidates` block. "
    "Do NOT invent URLs or news_ids.\n"
    "- `confidence_bump = medium->high` REQUIRES a non-empty "
    "`primary_evidence_id` that exists in that theme's candidate list AND "
    "carries verdict=BULLISH/BEARISH matching the theme direction.\n"
    "- If the theme has NO candidate evidence, you MUST emit "
    "`confidence_bump = none` with `primary_evidence_id = null`.\n"
    "- Be conservative: a single mention is not material; opinion threads do "
    "not count.\n\n"
    "Respond with ONE fenced ```json``` block, NOTHING else. Schema:\n"
    "{\n"
    '  "confirmations": [\n'
    "    {\n"
    '      "theme": "<exact theme name from input>",\n'
    '      "confidence_bump": "none" | "medium->high",\n'
    '      "rationale": "<1-2 sentence summary>",\n'
    '      "primary_evidence_id": "<news_id from candidates, or null>"\n'
    "    }\n"
    "  ]\n"
    "}\n"
)


def _err(msg: str, rc: int = 1) -> None:
    print(f"[narrative_confirm] ✗ {msg}", file=sys.stderr)
    sys.exit(rc)


def _latest_cache() -> Path | None:
    if not CACHE_DIR.exists():
        return None
    cands = sorted(CACHE_DIR.glob("theme_detector_*.json"))
    cands = [p for p in cands if ".narrative." not in p.name]
    return cands[-1] if cands else None


def _load_themes(path: Path, top_n: int) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _err(f"cache unreadable {path}: {e}", rc=2)
    raw = (data.get("themes") or {}).get("all") or data.get("themes") or []
    if not isinstance(raw, list):
        _err("theme_detector cache: `themes.all` is not a list")
    def _key(t: dict) -> tuple:
        try:
            heat = float(t.get("heat") or t.get("heat_score") or 0.0)
        except (TypeError, ValueError):
            heat = 0.0
        return (heat, len(t.get("representative_stocks") or []))
    return sorted(raw, key=_key, reverse=True)[:top_n]


def _digests_within(since_days: int) -> list[Path]:
    """Return digest paths from the last `since_days`, newest first."""
    if not NEWS_DIGEST_DIR.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    out: list[tuple[str, Path]] = []
    for p in NEWS_DIGEST_DIR.glob("*_digest.json"):
        try:
            stem = p.name.split("_digest.json")[0]  # YYYY-MM-DD
            dt = datetime.strptime(stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if dt >= cutoff:
            out.append((stem, p))
    out.sort(reverse=True)
    return [p for _, p in out]


def _load_evidence_pool(since_days: int) -> list[dict]:
    """Flatten verdicts from recent digest files into a single evidence list."""
    pool: list[dict] = []
    for path in _digests_within(since_days):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for v in (d.get("verdicts") or []):
            if not isinstance(v, dict):
                continue
            nid = str(v.get("news_id") or "").strip()
            if not nid:
                continue
            pool.append({
                "news_id":   nid,
                "headline":  str(v.get("headline") or "")[:240],
                "verdict":   str(v.get("verdict") or "").upper() or None,
                "net_impact": v.get("net_impact_score"),
                "published": v.get("published") or v.get("news_date") or d.get("timestamp"),
                "tickers":   list(v.get("tickers_mentioned") or []),
                "sectors":   [
                    (s.get("sector") if isinstance(s, dict) else s)
                    for s in (v.get("affected_sectors") or [])
                ],
            })
    return pool


def _evidence_for_theme(theme: dict, pool: list[dict]) -> list[dict]:
    """Filter the pool by ticker / sector intersection with the theme, sorted
    newest-first then by |net_impact|, capped to EVIDENCE_PER_THEME."""
    stocks = set(theme.get("representative_stocks") or [])
    industries = {str(i).lower() for i in (theme.get("industries") or [])}
    matched: list[dict] = []
    for ev in pool:
        ticker_hit = bool(stocks.intersection(ev.get("tickers") or []))
        sector_hit = bool(industries.intersection(
            {str(s).lower() for s in (ev.get("sectors") or [])}
        ))
        if ticker_hit or sector_hit:
            matched.append(ev)
    def _key(e: dict) -> tuple:
        pub = str(e.get("published") or "")
        try:
            imp = abs(float(e.get("net_impact") or 0.0))
        except (TypeError, ValueError):
            imp = 0.0
        return (pub, imp)
    matched.sort(key=_key, reverse=True)
    return matched[:EVIDENCE_PER_THEME]


def _build_user_prompt(themes: list[dict],
                       evidence_by_theme: dict[str, list[dict]]) -> str:
    out: list[str] = ["Themes to assess (the candidate evidence is closed — do not invent more):\n"]
    for t in themes:
        name = t.get("name") or "?"
        direction = t.get("direction") or "?"
        heat_lbl = t.get("heat_label") or "?"
        maturity = t.get("maturity") or "?"
        stocks = ", ".join((t.get("representative_stocks") or [])[:8])
        evs = evidence_by_theme.get(name, [])
        ev_block = "  (no candidate evidence in window)" if not evs else "\n".join(
            f"  - id={e['news_id']}  pub={str(e.get('published') or '')[:10]}  "
            f"verdict={e.get('verdict') or '?'}  "
            f"impact={e.get('net_impact') if e.get('net_impact') is not None else '?'}\n"
            f"    head: {e.get('headline','')}"
            for e in evs
        )
        out.append(
            f"### {name}\n"
            f"direction={direction}, heat={heat_lbl}, maturity={maturity}\n"
            f"representative_stocks: {stocks}\n"
            f"evidence_candidates:\n{ev_block}\n"
        )
    return "\n".join(out)


def _try_llm(themes: list[dict],
             evidence_by_theme: dict[str, list[dict]]) -> tuple[dict | None, str | None]:
    if run_role is None:
        return None, None
    try:
        res = run_role(
            "narrative_confirm",
            SYSTEM_PROMPT,
            _build_user_prompt(themes, evidence_by_theme),
            timeout=120,
        )
    except Exception as e:
        print(f"[narrative_confirm] LLM router raised: {e}", file=sys.stderr)
        return None, None
    if not res or res.parse_status != "ok" or not res.parsed:
        return None, getattr(res, "agent", None)
    parsed = res.parsed
    if not isinstance(parsed.get("confirmations"), list):
        return None, getattr(res, "agent", None)
    return parsed, getattr(res, "agent", None)


def _normalize_confirmations(parsed: dict, theme_names: set[str],
                             allowed_ids_by_theme: dict[str, set[str]]
                             ) -> tuple[list[dict], int]:
    """Reject any bump that fails the evidence gate. Returns (confirmations,
    dropped_bumps_count)."""
    out: list[dict] = []
    dropped = 0
    for c in (parsed.get("confirmations") or []):
        if not isinstance(c, dict):
            continue
        name = str(c.get("theme") or "").strip()
        if not name or name not in theme_names:
            continue
        bump = str(c.get("confidence_bump") or "none").strip()
        if bump not in ("none", "medium->high"):
            bump = "none"
        evidence_id = c.get("primary_evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            evidence_id = None
        # Enforce: bump=medium->high requires evidence_id in the theme's
        # closed candidate set. Hallucinated IDs / nulls are downgraded.
        if bump == "medium->high":
            allowed = allowed_ids_by_theme.get(name, set())
            if not evidence_id or evidence_id not in allowed:
                dropped += 1
                bump = "none"
                evidence_id = None
        out.append({
            "theme": name,
            "confidence_bump": bump,
            "rationale": str(c.get("rationale") or "").strip()[:600],
            "primary_evidence_id": evidence_id,
        })
    return out, dropped


def main() -> int:
    ap = argparse.ArgumentParser(description="Theme narrative confirmation sidecar (evidence-grounded)")
    ap.add_argument("--input", type=Path, default=None, help="theme_detector JSON path; default = latest in cache/")
    ap.add_argument("--top-n", type=int, default=5, help="how many top themes to confirm (default 5)")
    ap.add_argument("--since-days", type=int, default=14, help="evidence window in days (default 14)")
    ap.add_argument("--dry-run", action="store_true", help="print plan + evidence counts, no LLM write")
    args = ap.parse_args()

    src = args.input or _latest_cache()
    if not src or not src.exists():
        _err(f"no theme_detector cache found (looked in {CACHE_DIR})", rc=2)

    themes = _load_themes(src, max(1, args.top_n))
    if not themes:
        _err("theme_detector cache has no themes")

    pool = _load_evidence_pool(max(1, args.since_days))
    evidence_by_theme: dict[str, list[dict]] = {
        (t.get("name") or ""): _evidence_for_theme(t, pool) for t in themes
    }
    allowed_ids_by_theme: dict[str, set[str]] = {
        name: {e["news_id"] for e in evs}
        for name, evs in evidence_by_theme.items()
    }

    if args.dry_run:
        print(f"[narrative_confirm] would confirm {len(themes)} themes from {src.name}")
        print(f"  evidence_window={args.since_days}d  pool_size={len(pool)}")
        for t in themes:
            name = t.get("name") or "?"
            n_ev = len(evidence_by_theme.get(name, []))
            print(f"  - {name}  heat={t.get('heat_label')}  direction={t.get('direction')}  evidence={n_ev}")
        return 0

    theme_names = {str(t.get("name") or "") for t in themes}
    parsed, agent = _try_llm(themes, evidence_by_theme)

    dropped_bumps = 0
    if parsed:
        confirmations, dropped_bumps = _normalize_confirmations(
            parsed, theme_names, allowed_ids_by_theme,
        )
        narrate_mode = "llm"
        model_used = agent
    else:
        confirmations = [
            {"theme": name, "confidence_bump": "none",
             "rationale": "", "primary_evidence_id": None}
            for name in theme_names
        ]
        narrate_mode = "skipped"
        model_used = None

    sidecar_path = src.with_name(src.name.replace(".json", ".narrative.json"))
    payload = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source_cache": src.name,
        "evidence_window_days": args.since_days,
        "evidence_pool_size": len(pool),
        "narrate_mode": narrate_mode,
        "model_used": model_used,
        "themes_assessed": len(themes),
        "bumped_count": sum(1 for c in confirmations if c["confidence_bump"] == "medium->high"),
        "dropped_bumps_no_evidence": dropped_bumps,
        "confirmations": confirmations,
    }
    sidecar_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
    print(f"[narrative_confirm] ✓ wrote {sidecar_path.name} "
          f"(mode={narrate_mode}, model={model_used or '—'}, "
          f"bumped={payload['bumped_count']}/{len(themes)}, "
          f"dropped={dropped_bumps})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
