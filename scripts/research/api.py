"""Shared dashboard read/observation API; never updates investment artifacts."""
from __future__ import annotations

import json
import re

from scripts.research.engine import cards_for
from scripts.research.store import ROOT, Repository, digest, now_iso, parse_time, profile


def last_analysis(ticker):
    try:
        data = json.loads((ROOT / "Dashboard/data.json").read_text())
        # Dashboard's normalized deep-dive history is read-only context.
        candidates = []
        for key in ("recent_analysis",):
            rows = data.get(key, [])
            if isinstance(rows, list):
                candidates.extend(row for row in rows if isinstance(row, dict) and row.get("ticker") == ticker)
        times = [row.get("time") for row in candidates]
        return max((t for t in times if parse_time(t)), default=None)
    except (OSError, ValueError):
        return None


def query(*, lane="all", ticker="", since=None, limit=30, repo=None):
    repo = repo or Repository()
    ticker = ticker.strip().upper()
    if ticker and not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", ticker):
        raise ValueError("invalid ticker")
    if since and parse_time(since) is None:
        raise ValueError("invalid since timestamp")
    since = since or (last_analysis(ticker) if ticker and lane == "invest" else None)
    cards = cards_for(repo, lane=lane, ticker=ticker, since=since, limit=3 if ticker else limit)
    observation = repo.observation(lane, ticker) if ticker else None
    return {"schema_version": 1, "generated_at": now_iso(), "enabled": profile().get("enabled", False),
            "lane": lane, "ticker": ticker, "since": since, "cards": cards,
            "revision": digest([(c["id"], c["revision"]) for c in cards]),
            "observation": observation, "experiment": repo.get("experiment"),
            "service": repo.get("service"),
            "source_health": repo.get("source_health", {}),
            "last_poll": repo.get("last_poll"), "triggers": repo.get("trigger_health"),
            "schedules": repo.get("schedules", []), "exploratory": True}


def observe(body, repo=None):
    repo = repo or Repository()
    lane, ticker = body.get("lane", ""), body.get("ticker", "")
    if not ticker:
        raise ValueError("ticker is required")
    current = query(lane=lane, ticker=ticker, repo=repo)
    if body.get("revision") != current["revision"]:
        raise ValueError("research changed; refresh before marking it read")
    repo.observe(lane, current["ticker"], current["revision"])
    return {"ok": True, "observation": repo.observation(lane, current["ticker"])}


def nexus_candidates(repo=None):
    """Candidates only. Existing independent-report promotion gates still own the graph."""
    repo = repo or Repository()
    cards = cards_for(repo, lane="nexus", limit=100)
    return [{"claim_id": c["id"], "status": "provisional", "research_status": c["status"],
             "text": c["text"], "tickers": c["tickers"], "evidence": c["evidence"],
             "independent_reports": 0, "eligible_for_node_promotion": False}
            for c in cards if c["status"] != "retracted"]


def track(body, repo=None):
    from datetime import datetime, timedelta, timezone

    repo = repo or Repository()
    card = next((c for c in repo.all("cards") if c["id"] == body.get("claim_id")), None)
    if not card or card.get("superseded") or body.get("revision") != card["revision"]:
        raise ValueError("claim missing or changed; refresh before tracking")
    tracking = {"claim_id": card["id"], "event_id": card["event_id"], "tickers": card["tickers"],
                "condition": card["followup"]["condition"], "created_at": now_iso(),
                "due_at": card["followup"].get("due_at") or (
                    datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}
    tracked = repo.get("tracked_claims", {})
    tracked[card["id"]] = tracking
    repo.set("tracked_claims", tracked)
    return {"ok": True, "tracking": tracking}
