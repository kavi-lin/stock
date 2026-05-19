"""Break-news poller.

Pulls RSS feeds (reuses news/fetch_news_rss FEEDS + parsers), dedupes via
`_seen_index.json`, runs stage1 triage in-process, gates items past a
shallow_score threshold, and writes one bn_*.json per new item in
`pending_debate` state. Designed to be invoked every ~10 min by the dashboard
server background thread, or ad-hoc with --once.

Does NOT touch the daily DIGEST `news/news_logs/YYYY-MM-DD_raw.json` —
break-news has its own dedupe and its own dedicated store.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from news.fetch_news_rss import FEEDS, fetch_feed, headline_fingerprint  # noqa: E402
from news.scripts.stage1_triage import (  # noqa: E402
    classify_news_type, calc_shallow_score, gen_4view_snaps, BINARY_KEYS,
)
from scripts.break_news import store  # noqa: E402
from scripts.break_news.llm_drivers import break_news_pair  # noqa: E402
from scripts._shared import model_router  # noqa: E402

try:
    from scripts.break_news import social_sources as _social_sources  # noqa: E402
    SOCIAL_AVAILABLE = True
except Exception as _e:
    _social_sources = None
    SOCIAL_AVAILABLE = False

try:
    import scripts.parse_futu_notifications as _futu  # noqa: E402
    FUTU_AVAILABLE = True
except Exception as _e:
    _futu = None
    FUTU_AVAILABLE = False

DEFAULT_INTERVAL = int(os.environ.get("BREAK_NEWS_INTERVAL_SEC", "600"))
GATE_MIN_SCORE = float(os.environ.get("BREAK_NEWS_GATE_MIN_SCORE", "2"))
MAX_ITEMS_PER_CYCLE = int(os.environ.get("BREAK_NEWS_MAX_PER_CYCLE", "10"))
DAILY_MAX = int(os.environ.get("BREAK_NEWS_DAILY_MAX_DEBATES", "0"))
WINDOW_HOURS = int(os.environ.get("BREAK_NEWS_WINDOW_HOURS", "6"))
FUTU_ENABLED = os.environ.get("BREAK_NEWS_FUTU_ENABLED", "1") not in ("0", "false", "no")
FUTU_MAX_PER_CYCLE = int(os.environ.get("BREAK_NEWS_FUTU_MAX_PER_CYCLE", "30"))
SOCIAL_ENABLED = os.environ.get("BREAK_NEWS_SOCIAL_ENABLED", "1") not in ("0", "false", "no")
SOCIAL_GATE_MIN_SCORE = float(os.environ.get("BREAK_NEWS_SOCIAL_GATE_MIN_SCORE", "3"))
SESSION_RESERVE = int(os.environ.get("BREAK_NEWS_SESSION_RESERVE", "25"))
EST_CALLS_PER_DEBATE = max(1, int(os.environ.get("BREAK_NEWS_EST_CALLS_PER_DEBATE", "6")))
SESSION_TZ = ZoneInfo("America/New_York")

_last_feed_stats: list[dict] = []


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _count_today() -> int:
    """How many items already created today (any state) — for cost guard."""
    today = _today_utc().replace("-", "")
    n = 0
    for p in store.STORE_DIR.glob(f"bn_{today}_*.json"):
        n += 1
    return n


def _in_us_news_window(now_utc: datetime | None = None) -> bool:
    """True during the high-value US market news window.

    Uses America/New_York so DST is handled by the stdlib. The window starts
    before regular session for pre-market news and extends past close for
    late-day headlines.
    """
    now = (now_utc or datetime.now(timezone.utc)).astimezone(SESSION_TZ)
    start = now.replace(hour=7, minute=0, second=0, microsecond=0)
    end = now.replace(hour=18, minute=0, second=0, microsecond=0)
    return start <= now <= end


def _pending_backlog_count() -> int:
    n = 0
    for p in store.STORE_DIR.glob("bn_*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                if json.load(f).get("state") == "pending_debate":
                    n += 1
        except (OSError, json.JSONDecodeError):
            continue
    return n


def _model_call_headroom(pair: list[str]) -> dict:
    cfg = model_router.load_llm_config()
    status = model_router.model_status()
    usage_date = status.get("date")
    details = {}
    finite: list[int] = []
    for model in pair:
        headroom, available, reason = model_router.model_headroom(model, cfg=cfg)
        model_state = (status.get("models") or {}).get(model, {})
        details[model] = {
            "headroom": headroom,
            "available": available,
            "reason": reason,
            "calls": model_state.get("calls"),
            "daily_max": model_state.get("daily_max"),
        }
        if not available:
            return {
                "ok": False,
                "binding_call_headroom": 0,
                "usage_date": usage_date,
                "models": details,
                "blocked_reason": f"{model}:{reason}",
            }
        if headroom is not None:
            finite.append(headroom)

    # No configured cap on either voice: admission is governed by per-cycle gate
    # and optional BREAK_NEWS_DAILY_MAX_DEBATES emergency ceiling.
    binding = min(finite) if finite else MAX_ITEMS_PER_CYCLE * EST_CALLS_PER_DEBATE
    return {
        "ok": True,
        "binding_call_headroom": max(0, int(binding)),
        "usage_date": usage_date,
        "models": details,
        "blocked_reason": None,
    }


def _auto_budget_limit(now_utc: datetime | None = None, today_count: int = 0) -> dict:
    """Model-aware admission capacity for new debate items.

    `BREAK_NEWS_DAILY_MAX_DEBATES > 0` is only an emergency item ceiling. Normal
    capacity comes from the configured Break News A/B voices, in LLM-call units.
    """
    in_window = _in_us_news_window(now_utc)
    pair = break_news_pair()
    model_cap = _model_call_headroom(pair)
    pending_backlog = _pending_backlog_count()
    call_headroom = int(model_cap.get("binding_call_headroom") or 0)
    reserve_calls = 0 if in_window else max(0, SESSION_RESERVE)
    usable_calls = max(0, call_headroom - reserve_calls)
    queued_calls = pending_backlog * EST_CALLS_PER_DEBATE
    model_debate_capacity = max(0, (usable_calls - queued_calls) // EST_CALLS_PER_DEBATE)

    emergency_remaining = None
    admission_remaining = model_debate_capacity
    if DAILY_MAX > 0:
        emergency_remaining = max(0, DAILY_MAX - today_count)
        admission_remaining = min(admission_remaining, emergency_remaining)

    return {
        "admission_remaining": int(max(0, admission_remaining)),
        "model_debate_capacity": int(model_debate_capacity),
        "binding_call_headroom": call_headroom,
        "pending_backlog": pending_backlog,
        "estimated_calls_per_debate": EST_CALLS_PER_DEBATE,
        "reserved_session_calls": reserve_calls,
        "emergency_item_limit": DAILY_MAX,
        "emergency_items_remaining": emergency_remaining,
        "break_news_pair": pair,
        "model_capacity": model_cap,
        "us_news_window_open": in_window,
    }


def gate(score: float, credibility: str, binary: bool) -> tuple[bool, str | None]:
    if binary:
        return True, "binary"
    if abs(score) >= GATE_MIN_SCORE:
        return True, "score"
    if credibility == "HIGH" and abs(score) >= 1.0:
        return True, "hi_cred"
    return False, None


def social_gate(score: float, binary: bool) -> tuple[bool, str | None]:
    """Social/trend sources are high-noise. They still land in raw stream, but
    auto-debate only when the score is stronger than normal RSS gating."""
    if abs(score) >= SOCIAL_GATE_MIN_SCORE:
        return True, "social_score"
    if binary and abs(score) >= GATE_MIN_SCORE:
        return True, "social_binary_score"
    return False, None


def _candidate_priority(c: dict) -> tuple:
    """Higher tuple wins. Spend LLM budget on high-impact fresh items first."""
    score = abs(float(c.get("score") or 0.0))
    cred_rank = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}.get(
        str(c.get("credibility") or "").upper(), 0)
    dt = c.get("published_dt")
    ts = dt.astimezone(timezone.utc).timestamp() if dt else 0.0
    return (
        score,
        1 if c.get("binary") else 0,
        cred_rank,
        0 if c.get("is_social") else 1,
        1 if c.get("is_futu") else 0,
        ts,
    )


def fetch_fresh_items(window_hours: int) -> list[dict]:
    global _last_feed_stats
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    out: list[dict] = []
    feed_stats: list[dict] = []
    for name, url, cred in FEEDS:
        items = fetch_feed(name, url, cred)
        feed_stats.append({"feed": name, "fetched": len(items)})
        for x in items:
            dt = x.get("_dt")
            if dt is not None and dt < cutoff:
                continue
            out.append(x)
    # Futu push channel — US-only news, pre-filtered (no HK/CN, no ads).
    # Source field stays "Futu Push" so we can distinguish in store / UI.
    if FUTU_ENABLED and FUTU_AVAILABLE:
        try:
            futu_items, _stats = _futu.load_for_break_news(
                window_hours=window_hours, max_items=FUTU_MAX_PER_CYCLE,
            )
            for x in futu_items:
                dt = x.get("_dt")
                if dt is not None:
                    # _dt is local-tz aware — convert to UTC for cutoff compare
                    if dt.astimezone(timezone.utc) < cutoff:
                        continue
                out.append(x)
            feed_stats.append({"feed": "Futu Push", "fetched": len(futu_items)})
        except Exception as _e:
            feed_stats.append({"feed": "Futu Push", "error": str(_e)[:120]})

    # Free social/trend sources. These are noisy discovery signals, so they are
    # tagged and later gated more conservatively than official RSS/Futu.
    if SOCIAL_ENABLED and SOCIAL_AVAILABLE:
        try:
            social_items, social_stats = _social_sources.fetch_social_items(window_hours)
            for x in social_items:
                dt = x.get("_dt")
                if dt is not None and dt.astimezone(timezone.utc) < cutoff:
                    continue
                out.append(x)
            feed_stats.extend(social_stats)
        except Exception as _e:
            feed_stats.append({"feed": "Social Sources", "error": str(_e)[:120]})
    elif SOCIAL_ENABLED and not SOCIAL_AVAILABLE:
        feed_stats.append({"feed": "Social Sources", "error": "module unavailable"})

    _last_feed_stats = feed_stats

    # Newest first, keep best credibility on fingerprint collision.
    # RSS HIGH/MEDIUM > Futu MEDIUM > social LOW, so high-quality sources win.
    seen: dict[str, dict] = {}
    cred_rank = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}
    for x in out:
        fp = x.get("_fp") or ""
        if not fp:
            continue
        prev = seen.get(fp)
        if prev is None:
            seen[fp] = x
        elif cred_rank.get(x.get("source_credibility"), 0) > cred_rank.get(prev.get("source_credibility"), 0):
            seen[fp] = x
        elif x.get("source") != "Futu Push" and prev.get("source") == "Futu Push":
            # Same cred tie → prefer non-Futu (real RSS URL beats synthetic futu://).
            seen[fp] = x
        elif not x.get("_social_source") and prev.get("_social_source"):
            # Same cred tie → prefer a publisher feed over social echo.
            seen[fp] = x
    deduped = list(seen.values())
    deduped.sort(
        key=lambda x: (x.get("_dt").astimezone(timezone.utc) if x.get("_dt") else
                       datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )
    return deduped


def run_once(window_hours: int = WINDOW_HOURS, dry_run: bool = False) -> dict:
    started = datetime.now(timezone.utc)
    try:
        items = fetch_fresh_items(window_hours)
    except Exception as e:  # network catastrophe
        store.update_state("poller", {
            "last_run": store._utc_iso(),
            "last_status": "network_error",
            "last_error": str(e)[:300],
        })
        return {"ok": False, "error": str(e)}

    seen = store.load_seen()
    today_count = _count_today()
    budget = _auto_budget_limit(started, today_count=today_count)
    cost_guard_remaining = budget["admission_remaining"]

    new_items = 0
    new_items_futu = 0
    new_items_social = 0
    gated_out = 0
    gated_cost = 0
    duplicates = 0
    advanced_ids: list[str] = []
    raw_entries: list[dict] = []   # every fetched non-dup item, for the un-gated UI feed
    debate_candidates: list[dict] = []

    for raw in items:
        key = store.hash_key(raw.get("url"), raw.get("_fp"))
        if key in seen:
            duplicates += 1
            continue

        headline = raw.get("headline") or ""
        summary = raw.get("raw_summary") or ""
        if not headline:
            continue
        news_type = classify_news_type(headline, summary)
        score = float(calc_shallow_score(headline, summary, news_type))
        bull_case, bear_case, sector_view, macro_view = gen_4view_snaps(headline, news_type)
        binary = any(kw in headline.lower() for kw in BINARY_KEYS)
        is_futu = raw.get("source") == "Futu Push"
        is_social = bool(raw.get("_social_source"))

        if is_futu:
            # Futu items carry a zh-aware shallow score (`_zh_score`) computed
            # in parse_futu_notifications.score_zh. English keyword scorer
            # would return 0 for zh headlines.
            zh_s = raw.get("_zh_score")
            if zh_s is not None:
                score = float(zh_s)
            binary = binary or bool(raw.get("_zh_binary"))
            # Futu pre-filter already enforced US ticker / no ads / no HK-CN.
            # Trust the upstream filter for gate decision; score is informational.
            passed, reason = True, "futu_news"
        elif is_social:
            passed, reason = social_gate(score, binary)
        else:
            passed, reason = gate(score, raw.get("source_credibility", "MEDIUM"), binary)

        triage = {
            "news_type": news_type,
            "shallow_score": score,
            "bull_case": bull_case,
            "bear_case": bear_case,
            "sector_view": sector_view,
            "macro_view": macro_view,
            "binary_flag": binary,
            "advance_reason": reason,
        }
        source = {
            "name": raw.get("source"),
            "credibility": raw.get("source_credibility"),
            "url": raw.get("url"),
            "feed_fingerprint": raw.get("_fp"),
            "published": raw.get("published"),
        }
        # Raw-stream entry — recorded for EVERY fetched non-dup item, gated or
        # not, so the UI can show an un-gated feed + offer a manual debate
        # trigger. `news_id` is filled below only if the item also auto-advances.
        raw_entry = {
            "key": key,
            "headline": headline[:200],
            "raw_summary": summary[:400],
            "source": raw.get("source"),
            "credibility": raw.get("source_credibility", "MEDIUM"),
            "url": raw.get("url"),
            "feed_fingerprint": raw.get("_fp"),
            "published": raw.get("published"),
            "fetched_at": store._utc_iso(),
            "news_type": news_type,
            "shallow_score": score,
            "binary_flag": binary,
            "bull_case": bull_case,
            "bear_case": bear_case,
            "sector_view": sector_view,
            "macro_view": macro_view,
            "gate_passed": passed,
            "gate_reason": reason,
            "is_futu": is_futu,
            "is_social": is_social,
            "source_meta": raw.get("_source_meta") or {},
            "news_id": None,
        }
        raw_entries.append(raw_entry)

        if not passed:
            gated_out += 1
            continue

        debate_candidates.append({
            "key": key,
            "headline": headline[:200],
            "raw_summary": summary[:400],
            "source": source,
            "triage": triage,
            "raw_entry": raw_entry,
            "score": score,
            "binary": binary,
            "credibility": raw.get("source_credibility", "MEDIUM"),
            "published_dt": raw.get("_dt"),
            "is_futu": is_futu,
            "is_social": is_social,
        })

    debate_candidates.sort(key=_candidate_priority, reverse=True)

    for c in debate_candidates:
        if cost_guard_remaining <= 0:
            gated_cost += 1
            continue
        if new_items >= MAX_ITEMS_PER_CYCLE:
            gated_cost += 1
            continue
        if dry_run:
            new_items += 1
            if c["is_futu"]:
                new_items_futu += 1
            if c["is_social"]:
                new_items_social += 1
            cost_guard_remaining -= 1
            continue

        nid = store.init_item(
            source=c["source"], triage=c["triage"],
            headline=c["headline"], raw_summary=c["raw_summary"],
        )
        c["raw_entry"]["news_id"] = nid
        advanced_ids.append(nid)
        new_items += 1
        if c["is_futu"]:
            new_items_futu += 1
        if c["is_social"]:
            new_items_social += 1
        cost_guard_remaining -= 1

    raw_stream_size = 0
    if not dry_run:
        try:
            raw_stream_size = store.save_raw_stream(raw_entries)
        except Exception as e:  # raw stream is best-effort, never fail the poll
            sys.stderr.write(f"[poller] raw_stream save failed: {e}\n")

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    state_patch = {
        "last_run": store._utc_iso(),
        "last_status": "ok",
        "last_error": None,
        "elapsed_sec": round(elapsed, 1),
        "items_added": new_items,
        "items_added_futu": new_items_futu,
        "items_added_social": new_items_social,
        "items_gated_out": gated_out,
        "items_gated_cost": gated_cost,
        "duplicates_skipped": duplicates,
        "debate_candidates": len(debate_candidates),
        "raw_stream_size": raw_stream_size,
        "cost_guard_remaining": cost_guard_remaining,
        "admission_remaining": cost_guard_remaining,
        "auto_budget_limit": budget["model_debate_capacity"],
        "model_debate_capacity": budget["model_debate_capacity"],
        "binding_call_headroom": budget["binding_call_headroom"],
        "pending_debate_backlog": budget["pending_backlog"],
        "estimated_calls_per_debate": budget["estimated_calls_per_debate"],
        "reserved_session_calls": budget["reserved_session_calls"],
        "emergency_item_limit": budget["emergency_item_limit"],
        "emergency_items_remaining": budget["emergency_items_remaining"],
        "break_news_pair": budget["break_news_pair"],
        "model_capacity": budget["model_capacity"],
        "session_reserve": SESSION_RESERVE,
        "us_news_window_open": budget["us_news_window_open"],
        "advanced_ids": advanced_ids,
        "futu_enabled": FUTU_ENABLED and FUTU_AVAILABLE,
        "social_enabled": SOCIAL_ENABLED and SOCIAL_AVAILABLE,
        "feed_stats": _last_feed_stats,
        "next_run": (datetime.now(timezone.utc) + timedelta(seconds=DEFAULT_INTERVAL))
                    .strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if not dry_run:
        store.update_state("poller", state_patch)
    return {"ok": True, "dry_run": dry_run, **state_patch}


def main() -> int:
    ap = argparse.ArgumentParser(description="Break news RSS poller")
    ap.add_argument("--once", action="store_true", help="Single cycle, then exit")
    ap.add_argument("--dry-run", action="store_true", help="No writes")
    ap.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                    help=f"Seconds between cycles (default {DEFAULT_INTERVAL})")
    ap.add_argument("--window-hours", type=int, default=WINDOW_HOURS,
                    help=f"RSS time window (default {WINDOW_HOURS}h)")
    args = ap.parse_args()

    if args.once or args.dry_run:
        res = run_once(window_hours=args.window_hours, dry_run=args.dry_run)
        print(res)
        return 0 if res.get("ok") else 1

    while True:
        try:
            res = run_once(window_hours=args.window_hours)
            print(f"[poller] {res}")
        except KeyboardInterrupt:
            print("interrupted")
            return 0
        except Exception as e:  # pragma: no cover
            print(f"[poller] cycle error: {e}", file=sys.stderr)
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
