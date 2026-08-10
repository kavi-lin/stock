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
from news.source_policy import infer_source_kind, source_priority  # noqa: E402
from news.scripts.stage1_triage import (  # noqa: E402
    classify_news_type, calc_shallow_score, gen_4view_snaps,
    calc_materiality_score, classify_content_genre, detect_binary_event,
    effective_credibility,
)
from scripts.break_news import store, cluster  # noqa: E402
from scripts.break_news.llm_drivers import break_news_pair  # noqa: E402
from scripts._shared import model_router  # noqa: E402
from scripts.break_news.llm_drivers import VALID_MODELS  # noqa: E402

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
# V6 blind-open + strict divergence gate: converged items cost 2 calls and the
# gate only re-opens on a true verdict conflict, so 2 ≈ expected average.
EST_CALLS_PER_DEBATE = max(1, int(os.environ.get("BREAK_NEWS_EST_CALLS_PER_DEBATE", "2")))
# V6 sentiment damping: generic market-mood headlines (56% of historic volume)
# are clustered + counted, NOT debated, unless binary / HIGH-cred / strong score.
SENTIMENT_DEBATE_MIN_SCORE = float(os.environ.get("BREAK_NEWS_SENTIMENT_MIN_SCORE", "3"))
HOURLY_CAP = max(1, int(os.environ.get("BREAK_NEWS_HOURLY_CAP", "25")))
SLOT_MINUTES = 60.0 / HOURLY_CAP
BACKFILL_MINUTES = max(1, int(os.environ.get("BREAK_NEWS_BACKFILL_MINUTES", "30")))
MATERIALITY_MIN = float(os.environ.get("BREAK_NEWS_MATERIALITY_MIN", "2.5"))
POOL_MATERIALITY_MIN = float(os.environ.get("BREAK_NEWS_POOL_MATERIALITY_MIN", "3.5"))
SESSION_TZ = ZoneInfo("America/New_York")
# Mirrors debater.PENDING_MAX_AGE_HOURS (same env var) so the backlog count
# below only reflects items debater.scan_pending() will actually pick up.
PENDING_MAX_AGE_HOURS = float(os.environ.get("BREAK_NEWS_PENDING_MAX_AGE_HOURS", "2"))

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
    """Count pending_debate items still eligible for auto-debate.

    debater.scan_pending() skips items older than PENDING_MAX_AGE_HOURS —
    they sit in pending_debate forever awaiting manual triage and will never
    consume future call budget. Counting them here previously starved
    `model_debate_capacity` to 0 permanently once the stale backlog alone
    exceeded available headroom, blocking new admissions with no error and
    no way to recover (see CHANGELOG stale-backlog deadlock, 2026-08-07).
    """
    now_utc = datetime.now(timezone.utc)
    n = 0
    for p in store.STORE_DIR.glob("bn_*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if d.get("state") != "pending_debate":
            continue
        fetched = d.get("fetched_at")
        if fetched:
            try:
                dt = datetime.fromisoformat(fetched.replace("Z", "+00:00"))
                if (now_utc - dt).total_seconds() / 3600.0 > PENDING_MAX_AGE_HOURS:
                    continue
            except ValueError:
                pass
        n += 1
    return n


def _parse_iso_utc(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _admissions_in_window(window_minutes: int = 60) -> list[datetime]:
    """fetched_at UTC of bn_*.json items admitted within rolling window."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    out: list[datetime] = []
    for p in store.STORE_DIR.glob("bn_*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        dt = _parse_iso_utc(d.get("fetched_at"))
        if dt is None:
            continue
        if dt >= cutoff:
            out.append(dt)
    return out


def _hourly_slot_capacity(now_utc: datetime | None = None) -> dict:
    """Rolling 1-hour admission cap with time-slot pacing.

    HOURLY_CAP=25 → slot=2.4 min → at most 1 admission per slot. Quiet periods
    accumulate slot tokens (catch-up). Burst cycles still bounded by hourly_left.
    """
    now = now_utc or datetime.now(timezone.utc)
    window_start = now - timedelta(hours=1)
    admissions = _admissions_in_window(60)
    hourly_used = len(admissions)
    hourly_left = max(0, HOURLY_CAP - hourly_used)
    last_ts = max(admissions) if admissions else window_start
    elapsed_min = max(0.0, (now - last_ts).total_seconds() / 60.0)
    slot_tokens = int(elapsed_min // SLOT_MINUTES) if SLOT_MINUTES > 0 else hourly_left
    allowed = min(hourly_left, slot_tokens)
    return {
        "hourly_cap": HOURLY_CAP,
        "hourly_used": hourly_used,
        "hourly_left": hourly_left,
        "slot_minutes": round(SLOT_MINUTES, 3),
        "slot_tokens": slot_tokens,
        "allowed_this_cycle": int(allowed),
        "last_admission_ts": last_ts.isoformat() if admissions else None,
    }


def _voice_order(preferred: str, chain: list[str]) -> list[str]:
    # Cancel fallback: only evaluate the preferred/voice model
    if preferred in VALID_MODELS:
        return [preferred]
    return [chain[0]] if chain else ["gemini"]


def _model_call_headroom(pair: list[str]) -> dict:
    """Admission capacity for new debates, in LLM-call units.

    V4.106.0 — a *planning* estimate, no longer the gate. The quota broker
    decides at dispatch time, in tokens, across both projects that share these
    subscriptions. What remains here is the local call budget, which since Phase
    7 only binds on the degraded path; while the broker is reachable it is
    deliberately not treated as a cap, or the poller would throttle itself
    against a counter nothing else enforces any more. The counts stay in the
    response regardless, because the Break News status panel displays them.
    """
    cfg = model_router.load_llm_config()
    status = model_router.model_status()
    chain = model_router.model_chain(cfg)
    usage_date = status.get("date")
    broker = status.get("broker") or {}
    broker_governs = bool(broker.get("enabled")) and broker.get("reachable") is True
    details = {}
    voice_headrooms: list[int] = []
    fallback_backed = False
    for voice in pair:
        order = _voice_order(voice, chain)
        route = []
        selected = None
        for model in order:
            headroom, available, reason = model_router.model_headroom(model, cfg=cfg)
            local_headroom = headroom
            model_state = (status.get("models") or {}).get(model, {})
            if broker_governs:
                # `None` means "no local cap in force", which is the truth while
                # the broker is the authority. `local_headroom` keeps the number
                # visible for the panel without letting it gate.
                headroom, available, reason = None, True, ""
            rec = {
                "model": model,
                "headroom": headroom,
                "local_headroom": local_headroom,
                "available": available,
                "reason": reason,
                "governed_by": "broker" if broker_governs else "local_budget",
                "calls": model_state.get("calls"),
                "daily_max": model_state.get("daily_max"),
            }
            route.append(rec)
            if available and (headroom is None or headroom >= EST_CALLS_PER_DEBATE):
                selected = rec
                break
        details[voice] = {"order": order, "selected": selected, "route": route}
        if not selected:
            return {
                "ok": False,
                "binding_call_headroom": 0,
                "usage_date": usage_date,
                "voices": details,
                "models": details,
                "blocked_reason": f"{voice}:no_available_route",
                "fallback_backed": fallback_backed,
            }
        if selected["model"] != voice:
            fallback_backed = True
        voice_headrooms.append(
            selected["headroom"] if selected["headroom"] is not None
            else MAX_ITEMS_PER_CYCLE * EST_CALLS_PER_DEBATE
        )

    # No configured cap on either voice: admission is governed by per-cycle gate
    # and optional BREAK_NEWS_DAILY_MAX_DEBATES emergency ceiling.
    binding = min(voice_headrooms) if voice_headrooms else 0
    return {
        "ok": True,
        "binding_call_headroom": max(0, int(binding)),
        "usage_date": usage_date,
        "voices": details,
        "models": details,
        "blocked_reason": None,
        "fallback_backed": fallback_backed,
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

    hourly_slot = _hourly_slot_capacity(now_utc)
    hourly_allowed = int(hourly_slot.get("allowed_this_cycle") or 0)

    emergency_remaining = None
    admission_remaining = min(model_debate_capacity, hourly_allowed)
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
        "fallback_backed_capacity": bool(model_cap.get("fallback_backed")),
        "us_news_window_open": in_window,
        "hourly_slot": hourly_slot,
        "backfill_minutes": BACKFILL_MINUTES,
    }


def gate(materiality: float, binary: bool) -> tuple[bool, str | None]:
    if binary:
        return True, "binary"
    if materiality >= MATERIALITY_MIN:
        return True, "materiality"
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
    materiality = float(c.get("materiality_score") or 0.0)
    score = abs(float(c.get("score") or 0.0))
    cred_rank = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}.get(
        str(c.get("credibility") or "").upper(), 0)
    dt = c.get("published_dt")
    ts = dt.astimezone(timezone.utc).timestamp() if dt else 0.0
    return (
        materiality,
        score,
        1 if c.get("binary") else 0,
        cred_rank,
        0 if c.get("is_social") else 1,
        1 if c.get("is_futu") else 0,
        ts,
    )


def _score_materiality(raw: dict, headline: str, summary: str,
                       news_type: str, shallow_score: float) -> tuple[float, str, str]:
    """Return materiality plus the credibility/genre inputs used to derive it."""
    item = {
        "source": raw.get("source"),
        "source_credibility": raw.get("source_credibility") or raw.get("credibility") or "MEDIUM",
        "source_kind": raw.get("source_kind") or infer_source_kind(raw.get("source", "")),
    }
    cred_eff = effective_credibility(item, headline, summary)
    genre = classify_content_genre(item, headline, summary)
    materiality = calc_materiality_score(
        item, headline, summary, news_type, shallow_score, cred_eff, genre,
    )
    return materiality, cred_eff, genre


def _pool_candidate(entry: dict, seen: dict, started: datetime,
                    window_hours: int) -> dict | None:
    """Re-score one raw-stream entry for the quiet-cycle fallback pool."""
    key = entry.get("key")
    if not key or key in seen or entry.get("news_id"):
        return None
    published_dt = _parse_iso_utc(entry.get("published")) or _parse_iso_utc(entry.get("fetched_at"))
    if published_dt is None:
        return None
    age = started - published_dt.astimezone(timezone.utc)
    if age < timedelta(minutes=BACKFILL_MINUTES) or age > timedelta(hours=window_hours):
        return None

    headline = entry.get("headline") or ""
    summary = entry.get("raw_summary") or ""
    if not headline:
        return None
    news_type = classify_news_type(headline, summary)
    score = float(calc_shallow_score(headline, summary, news_type))
    materiality, cred_eff, genre = _score_materiality(
        entry, headline, summary, news_type, score,
    )
    binary = detect_binary_event(headline, summary)
    # Pool items are no longer breaking news, so require both a stronger score
    # and effective HIGH credibility. This prevents idle quota from promoting
    # evergreen advice/listicles that happen to mention the Fed or earnings.
    if materiality < POOL_MATERIALITY_MIN or cred_eff != "HIGH":
        return None
    if entry.get("is_social"):
        passed, _ = social_gate(score, binary)
        if not passed:
            return None

    reason = "pool_binary" if binary else "pool_materiality"
    bull_case, bear_case, sector_view, macro_view = gen_4view_snaps(headline, news_type)
    triage = {
        "news_type": news_type,
        "shallow_score": score,
        "materiality_score": materiality,
        "effective_credibility": cred_eff,
        "content_genre": genre,
        "bull_case": entry.get("bull_case") or bull_case,
        "bear_case": entry.get("bear_case") or bear_case,
        "sector_view": entry.get("sector_view") or sector_view,
        "macro_view": entry.get("macro_view") or macro_view,
        "binary_flag": binary,
        "advance_reason": reason,
    }
    source_kind = entry.get("source_kind") or infer_source_kind(entry.get("source", ""))
    source = {
        "name": entry.get("source"),
        "credibility": entry.get("credibility") or "MEDIUM",
        "kind": source_kind,
        "url": entry.get("url"),
        "feed_fingerprint": entry.get("feed_fingerprint"),
        "published": entry.get("published"),
    }
    raw_entry = {**entry, "gate_passed": True, "gate_reason": reason,
                 "materiality_score": materiality, "effective_credibility": cred_eff,
                 "content_genre": genre}
    return {
        "key": key,
        "headline": headline[:200],
        "raw_summary": summary[:400],
        "source": source,
        "triage": triage,
        "cluster": {"cluster_id": entry.get("cluster_id"), "echo_count": entry.get("echo_count"),
                    "sources": None, "escalated": False, "prior_summary": None},
        "raw_entry": raw_entry,
        "score": score,
        "materiality_score": materiality,
        "binary": binary,
        "credibility": source["credibility"],
        "published_dt": published_dt,
        "is_futu": bool(entry.get("is_futu")),
        "is_social": bool(entry.get("is_social")),
        "from_pool": True,
    }


def fetch_fresh_items(window_hours: int) -> list[dict]:
    global _last_feed_stats
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    out: list[dict] = []
    feed_stats: list[dict] = []
    for name, url, cred in FEEDS:
        items = fetch_feed(name, url, cred)
        feed_stats.append({
            "feed": name,
            "source_kind": infer_source_kind(name),
            "credibility": cred,
            "fetched": len(items),
        })
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

    # Newest first, keep the source closest to the original event on collision.
    seen: dict[str, dict] = {}
    for x in out:
        fp = x.get("_fp") or ""
        if not fp:
            continue
        prev = seen.get(fp)
        if prev is None:
            seen[fp] = x
        elif source_priority(x) > source_priority(prev):
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
    gated_echo = 0
    gated_sentiment = 0
    pool_candidates = 0
    pool_selected = 0
    escalations = 0
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
        materiality, cred_eff, genre = _score_materiality(
            raw, headline, summary, news_type, score,
        )
        binary = detect_binary_event(headline, summary)
        is_futu = raw.get("source") == "Futu Push"
        is_social = bool(raw.get("_social_source"))

        if is_futu:
            # Futu items carry a zh-aware shallow score (`_zh_score`) computed
            # in parse_futu_notifications.score_zh. English keyword scorer
            # would return 0 for zh headlines.
            zh_s = raw.get("_zh_score")
            if zh_s is not None:
                score = float(zh_s)
                materiality, cred_eff, genre = _score_materiality(
                    raw, headline, summary, news_type, score,
                )
            binary = binary or bool(raw.get("_zh_binary"))
            # Futu pre-filter already enforced US ticker / no ads / no HK-CN.
            # Trust the upstream filter for gate decision; score is informational.
            passed, reason = True, "futu_news"
        elif is_social:
            passed, reason = social_gate(score, binary)
        else:
            passed, reason = gate(materiality, binary)

        # ── V6 event clustering (0 LLM) ──────────────────────────────────
        # Every non-dup item joins a rolling event cluster. Echoes of an
        # already-debated story are counted, not re-debated; a cluster that
        # keeps growing escalates one follow-up debate at echo milestones.
        cl = {"cluster_id": None, "is_echo": False, "echo_count": 1,
              "should_escalate": False, "prior_news_ids": []}
        if not dry_run:  # cluster store is a write — keep dry-run write-free
            try:
                cl = cluster.assign_item(
                    headline, summary, news_type, score,
                    raw.get("source"), key=key)
            except Exception as _cl_e:  # clustering must never break the poll
                sys.stderr.write(f"[poller] cluster assign failed: {_cl_e}\n")

        if (passed and news_type == "sentiment" and not binary
                and cred_eff != "HIGH"
                and abs(score) < SENTIMENT_DEBATE_MIN_SCORE):
            # Generic market-mood headline: cluster count feeds the trend
            # index (Raw Pulse line); no LLM debate.
            passed, reason = False, "sentiment_cluster_only"
            gated_sentiment += 1

        if passed and cl["is_echo"] and not cl["should_escalate"] \
                and cl.get("prior_news_ids"):
            # Same story already debated — record the echo, spend nothing.
            passed, reason = False, "cluster_echo"
            gated_echo += 1
        elif cl["should_escalate"]:
            passed, reason = True, "cluster_escalation"
            escalations += 1

        triage = {
            "news_type": news_type,
            "shallow_score": score,
            "materiality_score": materiality,
            "effective_credibility": cred_eff,
            "content_genre": genre,
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
            "kind": raw.get("source_kind") or infer_source_kind(raw.get("source", "")),
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
            "source_kind": raw.get("source_kind") or infer_source_kind(raw.get("source", "")),
            "url": raw.get("url"),
            "feed_fingerprint": raw.get("_fp"),
            "published": raw.get("published"),
            "fetched_at": store._utc_iso(),
            "news_type": news_type,
            "shallow_score": score,
            "materiality_score": materiality,
            "effective_credibility": cred_eff,
            "content_genre": genre,
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
            "cluster_id": cl.get("cluster_id"),
            "echo_count": cl.get("echo_count"),
        }
        raw_entries.append(raw_entry)

        if not passed:
            gated_out += 1
            continue

        # Cluster context stored on the item — debater reads `escalated` +
        # `prior_summary` to run an increment-only follow-up round.
        cluster_block = {
            "cluster_id": cl.get("cluster_id"),
            "echo_count": cl.get("echo_count"),
            "sources": None,
            "escalated": bool(cl.get("should_escalate")),
            "prior_summary": None,
        }
        if cl.get("should_escalate") and cl.get("prior_news_ids"):
            prior = store.load_item(cl["prior_news_ids"][-1]) or {}
            ps = prior.get("summary") or {}
            if ps:
                cluster_block["prior_summary"] = {
                    "consensus_verdict": ps.get("consensus_verdict"),
                    "final_take": ps.get("final_take"),
                }

        debate_candidates.append({
            "key": key,
            "headline": headline[:200],
            "raw_summary": summary[:400],
            "source": source,
            "triage": triage,
            "cluster": cluster_block,
            "raw_entry": raw_entry,
            "score": score,
            "materiality_score": materiality,
            "binary": binary,
            "credibility": raw.get("source_credibility", "MEDIUM"),
            "published_dt": raw.get("_dt"),
            "is_futu": is_futu,
            "is_social": is_social,
        })

    # Fresh items always win. If there is no fresh qualifying event, admit at
    # most one stronger item from the rolling raw-stream pool. This spends an
    # otherwise-idle hourly slot without replaying a large stale backlog.
    backfill_cutoff = started - timedelta(minutes=BACKFILL_MINUTES)
    backfill_dropped = 0
    fresh_candidates: list[dict] = []
    old_candidates: list[dict] = []
    for c in debate_candidates:
        dt = c.get("published_dt")
        if dt is not None and dt.astimezone(timezone.utc) < backfill_cutoff:
            backfill_dropped += 1
            if (float(c.get("materiality_score") or 0) >= POOL_MATERIALITY_MIN
                    and c.get("triage", {}).get("effective_credibility") == "HIGH"):
                c["from_pool"] = True
                c["triage"]["advance_reason"] = (
                    "pool_binary" if c.get("binary") else "pool_materiality"
                )
                c["raw_entry"]["gate_reason"] = c["triage"]["advance_reason"]
                old_candidates.append(c)
            continue
        fresh_candidates.append(c)

    if fresh_candidates:
        debate_candidates = fresh_candidates
    elif cost_guard_remaining > 0:
        pooled_by_key = {c["key"]: c for c in old_candidates}
        for entry in store.load_raw_stream():
            c = _pool_candidate(entry, seen, started, window_hours)
            if c is not None:
                pooled_by_key[c["key"]] = c
        pool_candidates = len(pooled_by_key)
        ranked_pool = sorted(pooled_by_key.values(), key=_candidate_priority, reverse=True)
        debate_candidates = ranked_pool[:1]
        pool_selected = len(debate_candidates)
    else:
        debate_candidates = []

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
            cluster=c.get("cluster"),
        )
        if (c.get("cluster") or {}).get("cluster_id"):
            try:
                cluster.mark_debated(c["cluster"]["cluster_id"], nid)
            except Exception as _md_e:
                sys.stderr.write(f"[poller] cluster mark_debated failed: {_md_e}\n")
        c["raw_entry"]["news_id"] = nid
        if c.get("from_pool"):
            store.mark_raw_promoted(c["key"], nid)
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
        "items_gated_backfill": backfill_dropped,
        "pool_candidates": pool_candidates,
        "pool_selected": pool_selected,
        "items_echo_merged": gated_echo,
        "items_sentiment_clustered": gated_sentiment,
        "items_escalated": escalations,
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
        "fallback_backed_capacity": budget["fallback_backed_capacity"],
        "session_reserve": SESSION_RESERVE,
        "us_news_window_open": budget["us_news_window_open"],
        "hourly_slot": budget["hourly_slot"],
        "backfill_minutes": budget["backfill_minutes"],
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
