"""Promote finished break-news debates into research events (zero LLM).

Break News is the wide first pass: every gated headline gets a broker-picked
two-model debate. Research is the expensive deep dive, so it no longer runs its
own intake — it only sees debates whose outcome says a closer look is worth the
tokens. The decision is a deterministic score over what the debate already
produced; asking a model "is this worth researching?" would spend a call on
every item to save calls on a few.

Escalation still has to clear the research gate (public-company link or an
explicit economic channel, no opinion columns) and the six-hour freshness
window, and the service's rolling budget decides how many actually run.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from news.fetch_news_rss import headline_fingerprint
from scripts.research import intake
from scripts.research.store import ROOT, Repository, now_iso, parse_time, profile

BREAK_NEWS_DIR = ROOT / "news" / "break_news_logs"
WINDOW = timedelta(hours=6)
SEEN_KEY = "handoff_seen"
SEEN_RETENTION = timedelta(days=2)

# Close reasons where the two debaters never settled the contested point.
UNSETTLED = {"arbitrated", "unresolved_no_arbiter", "unresolved_timeout"}
STRONG_CONFIDENCE = 0.75
ECHO_SOURCES = 3


def min_score():
    return int(profile().get("handoff_min_score", 3))


def escalation(item, universe=None):
    """Score a closed debate. Returns (score, reasons, tickers).

    Weights were calibrated on 2026-10-01..04 debates: at 3 points a busy
    session yields ~30-36 candidates and a quiet one 5-10, against a research
    cap of 30 per day. A stated dispute alone is NOT enough — B disputes at
    least one point in ~60-80% of debates, so it only tips an item over.
    """
    from scripts.break_news.debater import is_high_priority_item, _load_universe_tickers

    summary = item.get("summary") or {}
    universe = universe if universe is not None else _load_universe_tickers()
    entities = summary.get("merged_entities") or {}
    tickers = sorted({str(t).upper() for t in entities.get("tickers") or []} & universe)
    if not tickers:
        return 0, ["no_universe_ticker"], tickers
    score, reasons = 0, []
    if summary.get("close_reason") in UNSETTLED:
        score += 3
        reasons.append("debate_unsettled")
    if (item.get("triage") or {}).get("binary_flag") is True:
        score += 3
        reasons.append("binary_event")
    if ((item.get("cluster") or {}).get("echo_count") or 0) >= ECHO_SOURCES:
        score += 2
        reasons.append("multi_source_echo")
    if is_high_priority_item(item):
        score += 1
        reasons.append("high_priority")
    confidences = [r.get("confidence") for r in summary.get("final_takes_by_round") or []]
    best = max((float(c) for c in confidences if isinstance(c, (int, float))), default=0.0)
    if summary.get("consensus_verdict") in {"BULLISH", "BEARISH"} and best >= STRONG_CONFIDENCE:
        score += 1
        reasons.append("strong_verdict")
    if (summary.get("stated_dispute_count") or 0) > 0:
        score += 1
        reasons.append("stated_dispute")
    return score, reasons, tickers


def _raw(item):
    """Shape a break-news item like an intake provider row."""
    source = item.get("source") or {}
    raw = {"headline": item.get("headline") or "", "url": source.get("url") or "",
           "raw_summary": item.get("raw_summary") or "", "published": source.get("published"),
           "source": source.get("name") or "", "source_credibility": source.get("credibility"),
           "provider": "Break News"}
    if source.get("kind"):
        raw["source_kind"] = source["kind"]
    return raw


def _closed_recently(item, now):
    if item.get("state") not in {"closed", "partial_closed"}:
        return False
    closed = parse_time((item.get("summary") or {}).get("closed_at"))
    return closed is not None and now - closed <= WINDOW


def promote(repo, item, score, reasons, now):
    """Create or re-arm the research event for one escalated debate."""
    event = intake.normalize(_raw(item), now)
    if event is None:
        return None, "no_public_url"
    # The materiality gate already ran upstream and the debate is the second
    # opinion on it; what research still owns is freshness and relevance.
    # normalize() skips the relevance check once materiality fails, so both
    # are re-run here rather than read back from `gate_reason`.
    published = parse_time(event["published_at"])
    if published is None or not timedelta(minutes=-5) <= now - published <= WINDOW:
        return None, "missing_or_stale_publication_time"
    if event["source_kind"] == "social":
        return None, "social_discovery_requires_primary_evidence"
    relevant, reason = intake.research_gate(event["headline"], event["evidence"][0]["text"],
                                            event["identified_tickers"], event["source_kind"])
    if not relevant:
        return None, reason
    event.update(eligible=True, gate_reason="break_news_escalation")
    day = (event["published_at"] or event["received_at"])[:10]
    aliases = ["url:" + event["url"],
               "headline:" + day + ":" + headline_fingerprint(event["headline"])]
    saved, changed = repo.ingest(event, aliases)
    if not changed and saved["state"] == "discovery" and not saved.get("debate_id"):
        # Seen earlier by the old intake but held below its own threshold.
        saved.update(state="pending", eligible=True, gate_reason="break_news_escalation")
    # Echoed coverage folds into one event by URL/headline alias, so several
    # debates can point at the same research; keep the strongest escalation.
    ids = saved.get("break_news_ids") or []
    if item["news_id"] not in ids:
        ids.append(item["news_id"])
    saved["break_news_ids"] = ids
    if score >= (saved.get("escalation") or {}).get("score", 0):
        saved["escalation"] = {"score": score, "reasons": reasons, "at": now.isoformat()}
    repo.update_event(saved)
    return saved, None


def poll(repo=None, now=None):
    """Service poll step: hand recently closed, high-scoring debates to research."""
    from scripts.break_news.debater import _load_universe_tickers

    repo = repo or Repository()
    now = now or datetime.now(timezone.utc)
    threshold = min_score()
    universe = _load_universe_tickers()
    seen = {k: v for k, v in repo.get(SEEN_KEY, {}).items()
            if (parse_time(v.get("at")) or now) > now - SEEN_RETENTION}
    counts = {"evaluated": 0, "escalated": 0, "promoted": 0, "rejected": 0}
    for path in sorted(BREAK_NEWS_DIR.glob("bn_*.json")):
        news_id = path.stem
        if news_id in seen:
            continue
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not _closed_recently(item, now):
            continue
        counts["evaluated"] += 1
        score, reasons, tickers = escalation(item, universe)
        record = {"at": now.isoformat(), "score": score, "reasons": reasons,
                  "tickers": tickers, "escalated": score >= threshold}
        if record["escalated"]:
            counts["escalated"] += 1
            event, rejected = promote(repo, item, score, reasons, now)
            if event is not None:
                counts["promoted"] += 1
                record["event_id"] = event["id"]
            else:
                counts["rejected"] += 1
                record["rejected"] = rejected
        seen[news_id] = record
    repo.set(SEEN_KEY, seen)
    health = {"feed": "Break News", "status": "ok", "checked_at": now.isoformat(),
              "fetched": counts["evaluated"], "fresh": counts["promoted"],
              "min_score": threshold}
    repo.set("source_health", {"Break News": health})
    repo.set("last_poll", {"at": now_iso(), **counts})
    return counts


def status_for(news_id, repo=None):
    """What research did with one debate, for the break-news detail panel."""
    repo = repo or Repository()
    record = repo.get(SEEN_KEY, {}).get(news_id)
    event = next((e for e in repo.all("events") if news_id in (e.get("break_news_ids") or [])), None)
    if event is None:
        return {"news_id": news_id, "handoff": record, "event": None, "cards": []}
    cards = [c for c in repo.all("cards")
             if c["event_id"] == event["id"] and not c.get("superseded")]
    keep = ("id", "state", "escalation", "error", "debate_id", "published_at", "tickers")
    return {"news_id": news_id, "handoff": record,
            "event": {k: event.get(k) for k in keep}, "cards": cards}
