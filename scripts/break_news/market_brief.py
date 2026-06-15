"""Market brief — periodic 1-LLM-call 市場現況導讀 over break-news output.

Deterministically aggregates the last BRIEF_WINDOW_H hours of break-news
artifacts (event clusters by heat, closed debate verdicts, verdict tallies,
news-type mix), then makes exactly ONE LLM call to write a 200-300 字繁中導讀:
current regime read, key drivers, bull/bear pressure, watch items.

Output: `news/break_news_logs/_market_brief.json`
    {"current": {...}, "history": [...last 12 briefs...]}

TTL-gated: `maybe_generate()` is a no-op until BRIEF_INTERVAL_SEC has elapsed
since the last brief (the debate loop calls it every cycle; cost stays at
~12 calls/day at the 2h default). `--once --force` for manual runs.

探索層紀律: brief is a reading aid for the human — it feeds NO decision logic.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.break_news import store, cluster, prompts  # noqa: E402
from scripts.break_news.llm_drivers import break_news_pair  # noqa: E402
from scripts._shared.model_router import run_with_fallback  # noqa: E402

BRIEF_FILE = store.STORE_DIR / "_market_brief.json"
BRIEF_INTERVAL_SEC = int(os.environ.get("BREAK_NEWS_BRIEF_INTERVAL_SEC", "7200"))
BRIEF_WINDOW_H = float(os.environ.get("BREAK_NEWS_BRIEF_WINDOW_H", "24"))
BRIEF_HISTORY_KEEP = 12
_TOP_CLUSTERS = 10
_TOP_DEBATES = 12

_gen_lock = threading.Lock()


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _recent_closed_items(hours: float) -> list[dict]:
    now = datetime.now(timezone.utc)
    out = []
    for p in store.STORE_DIR.glob("bn_*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if d.get("state") not in ("closed", "partial_closed"):
            continue
        ts = _parse_iso(d.get("fetched_at"))
        if ts is None or (now - ts).total_seconds() / 3600.0 > hours:
            continue
        out.append(d)
    return out


def build_context(hours: float = BRIEF_WINDOW_H) -> dict:
    """Deterministic aggregation — everything the LLM sees, 0 LLM cost."""
    closed = _recent_closed_items(hours)
    verdicts = Counter()
    type_mix = Counter()
    debates = []
    for d in closed:
        s = d.get("summary") or {}
        tri = d.get("triage") or {}
        v = s.get("consensus_verdict") or "NEUTRAL"
        verdicts[v] += 1
        type_mix[tri.get("news_type") or "unknown"] += 1
        try:
            impact = abs(float(tri.get("shallow_score") or 0.0))
        except (TypeError, ValueError):
            impact = 0.0
        debates.append({
            "headline": (d.get("headline") or "")[:140],
            "verdict": v,
            "final_take": s.get("final_take"),
            "tickers": (s.get("merged_entities") or {}).get("tickers") or [],
            "news_type": tri.get("news_type"),
            "impact": impact,
        })
    debates.sort(key=lambda x: x["impact"], reverse=True)

    clusters = cluster.cluster_feed(hours=hours, min_echo=2)[:_TOP_CLUSTERS]
    return {
        "window_hours": hours,
        "generated_at": _utc_iso(),
        "verdict_tally": dict(verdicts),
        "news_type_mix": dict(type_mix),
        "closed_debate_count": len(closed),
        "top_debates": debates[:_TOP_DEBATES],
        "hot_clusters": clusters,
    }


def load_brief() -> dict:
    if not BRIEF_FILE.exists():
        return {"current": None, "history": []}
    try:
        with open(BRIEF_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            return {"current": d.get("current"),
                    "history": d.get("history") or []}
    except (OSError, json.JSONDecodeError):
        pass
    return {"current": None, "history": []}


def _save_brief(current: dict) -> None:
    data = load_brief()
    hist = data.get("history") or []
    if data.get("current"):
        hist.insert(0, data["current"])
    payload = {"current": current, "history": hist[:BRIEF_HISTORY_KEEP]}
    store.STORE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = BRIEF_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    os.replace(tmp, BRIEF_FILE)


def _age_sec(brief: dict | None) -> float:
    ts = _parse_iso((brief or {}).get("generated_at"))
    if ts is None:
        return float("inf")
    return (datetime.now(timezone.utc) - ts).total_seconds()


def generate(force: bool = False) -> dict:
    """Build context + 1 LLM call + persist. Returns the brief record (or a
    {skipped|error} dict). Serialized; concurrent callers no-op."""
    if not _gen_lock.acquire(blocking=False):
        return {"skipped": "generation_in_progress"}
    try:
        current = load_brief().get("current")
        if not force and _age_sec(current) < BRIEF_INTERVAL_SEC:
            return {"skipped": "ttl", "age_sec": int(_age_sec(current))}

        ctx = build_context()
        if not ctx["closed_debate_count"] and not ctx["hot_clusters"]:
            return {"skipped": "no_signal"}

        voice = break_news_pair()[0]
        res = run_with_fallback(voice, "brief", prompts.BRIEF_SYSTEM_PROMPT,
                                prompts.brief_user_prompt(ctx))
        if res.exit_code != 0 or not res.parsed:
            return {"error": f"llm rc={res.exit_code} parse={res.parse_status}",
                    "agent": res.agent}
        parsed = res.parsed
        record = {
            "generated_at": ctx["generated_at"],
            "window_hours": ctx["window_hours"],
            "model": getattr(res, "model_used", res.agent) or res.agent,
            "regime": str(parsed.get("regime") or "")[:40],
            "regime_confidence": parsed.get("regime_confidence"),
            "brief_text": str(parsed.get("brief_text") or "")[:1200],
            "drivers": [str(x)[:80] for x in (parsed.get("drivers") or [])][:5],
            "bull_pressure": [str(x)[:80] for x in (parsed.get("bull_pressure") or [])][:4],
            "bear_pressure": [str(x)[:80] for x in (parsed.get("bear_pressure") or [])][:4],
            "watch": [str(x)[:80] for x in (parsed.get("watch") or [])][:5],
            "stats": {
                "verdict_tally": ctx["verdict_tally"],
                "news_type_mix": ctx["news_type_mix"],
                "closed_debate_count": ctx["closed_debate_count"],
                "hot_cluster_count": len(ctx["hot_clusters"]),
            },
        }
        _save_brief(record)
        return record
    finally:
        _gen_lock.release()


def maybe_generate() -> dict:
    """TTL-gated generate — safe to call every debate-loop cycle."""
    return generate(force=False)


def main() -> int:
    ap = argparse.ArgumentParser(description="Break-news market brief")
    ap.add_argument("--once", action="store_true", help="generate (TTL-gated)")
    ap.add_argument("--force", action="store_true", help="ignore TTL")
    ap.add_argument("--context", action="store_true", help="print context only (0 LLM)")
    args = ap.parse_args()
    if args.context:
        print(json.dumps(build_context(), ensure_ascii=False, indent=2))
        return 0
    if args.once or args.force:
        res = generate(force=args.force)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if not res.get("error") else 1
    print(json.dumps(load_brief().get("current") or {}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
