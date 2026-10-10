"""Due dates request fresh evidence; a clock tick alone never spends tokens."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from scripts.research.store import ROOT, parse_time

ET = ZoneInfo("America/New_York")


def scheduled_time(item):
    try:
        day = datetime.strptime(item["date"], "%Y-%m-%d")
        hour = str(item.get("time") or "").upper()
        # BMO/AMC are coarse windows, labelled as such in saved schedules.
        if hour == "BMO":
            hour = "08:30"
        elif hour == "AMC":
            hour = "16:05"
        match = re.search(r"(\d{1,2}):(\d{2})", hour)
        if match is None:
            return None
        return day.replace(hour=int(match[1]), minute=int(match[2]), tzinfo=ET).astimezone(timezone.utc)
    except (KeyError, ValueError, TypeError):
        return None


def scan(repo, now=None, calendar=None):
    now = now or datetime.now(timezone.utc)
    if calendar is None:
        try:
            calendar = json.loads((ROOT / "Dashboard/data.json").read_text()).get("upcoming_events", [])
        except (OSError, ValueError):
            repo.set("calendar_health", {"status": "missing", "checked_at": now.isoformat()})
            calendar = []
    schedules = []
    for item in calendar:
        if item.get("category") not in {"earnings", "macro", "econ"}:
            continue
        due = scheduled_time(item)
        if due and now - timedelta(days=1) <= due <= now:
            schedules.append({**item, "due_at": due.isoformat(), "state": "awaiting_release"})
    tracked = repo.get("tracked_claims", {})
    all_cards = repo.all("cards")
    for card in all_cards:
        if card["id"] in tracked:
            card["followup"] = {**card["followup"], "due_at": tracked[card["id"]]["due_at"]}
    due_cards = [c for c in all_cards if not c.get("superseded")
                 and c["status"] != "retracted" and parse_time(c["followup"].get("due_at"))
                 and parse_time(c["followup"]["due_at"]) <= now]
    matched = 0
    for event in repo.all("events"):
        if event["state"] != "pending":
            continue
        published = parse_time(event["published_at"])
        if published is None:
            continue
        related = [c for c in due_cards if set(c["tickers"]) & set(event["tickers"])
                   and published > parse_time(c["created_at"])]
        if related:
            event["trigger"] = "followup"
            event["followup_claims"] = [c["id"] for c in related][:5]
            repo.update_event(event)
            matched += 1
            continue
        for schedule in schedules:
            if published < parse_time(schedule["due_at"]):
                continue
            title = event["headline"].lower()
            earnings = schedule["category"] == "earnings"
            ticker_match = set(schedule.get("tickers", [])) & set(event["tickers"])
            macro_words = ("cpi", "payroll", "employment", "inflation", "gdp", "pce", "fomc")
            topic_match = any(w in title and w in schedule.get("title", "").lower() for w in macro_words)
            if (earnings and ticker_match and re.search(r"earnings|quarter|revenue|results", title)
                    or not earnings and topic_match):
                event["trigger"] = "calendar"
                event["schedule_id"] = schedule["id"]
                repo.update_event(event)
                schedule["state"] = "release_received"
                matched += 1
                break
    repo.set("schedules", schedules)
    repo.set("trigger_health", {"checked_at": now.isoformat(), "schedules": len(schedules),
                                "due_followups": len(due_cards), "matched_new_evidence": matched})
    return matched
