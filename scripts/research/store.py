"""Transactional event revisions, claim cards and research observations."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "news" / "research_cache"
DATABASE = CACHE / "research.sqlite3"
PROFILE = ROOT / "config" / "research.json"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()[:20]


def parse_time(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def profile():
    return json.loads(PROFILE.read_text()) if PROFILE.exists() else {"enabled": False}


class Repository:
    def __init__(self, path=DATABASE):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS aliases (key TEXT PRIMARY KEY, event_id TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS revisions (
                    event_id TEXT, revision TEXT, payload TEXT NOT NULL,
                    PRIMARY KEY(event_id, revision));
                CREATE TABLE IF NOT EXISTS cards (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS observations (
                    lane TEXT, ticker TEXT, revision TEXT, observed_at TEXT,
                    PRIMARY KEY(lane, ticker));
                CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, payload TEXT NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def all(self, table):
        if table not in {"events", "cards"}:
            raise ValueError("invalid research table")
        with self.connect() as conn:
            return [json.loads(row[0]) for row in conn.execute(f"SELECT payload FROM {table}")]

    def get(self, key, default=None):
        with self.connect() as conn:
            row = conn.execute("SELECT payload FROM state WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        with self.connect() as conn:
            conn.execute("INSERT OR REPLACE INTO state VALUES (?,?)", (key, json.dumps(value)))

    def ingest(self, incoming, alias_keys):
        """URL/headline aliases share an event; duplicate retrieval is not new evidence."""
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = None
            for alias in alias_keys:
                row = conn.execute("SELECT event_id FROM aliases WHERE key=?", (alias,)).fetchone()
                if row:
                    existing = json.loads(conn.execute("SELECT payload FROM events WHERE id=?",
                                                       (row[0],)).fetchone()[0])
                    break
            event = dict(existing or incoming)
            event_id = event["id"]
            for alias in alias_keys:
                conn.execute("INSERT OR IGNORE INTO aliases VALUES (?,?)", (alias, event_id))
            if existing:
                event["last_seen_at"] = incoming["received_at"]
                # Same syndicated headline adds lineage, not an independent vote.
                event["lineage"] = sorted(set(event["lineage"] + incoming["lineage"]))
                same_origin = incoming["url"] == event["url"]
                better_origin = incoming["source_priority"] > event["source_priority"]
                incoming_source_revision = digest({"headline": incoming["headline"],
                    "evidence": [(e["id"], e["text"]) for e in incoming["evidence"]]})
                original_unchanged = incoming_source_revision == existing.get("source_revision", existing["revision"])
                if same_origin:
                    event["tickers"] = incoming["tickers"]
                    for key in ('identified_tickers','provider_tickers','eligible','gate_reason'):
                        if key in incoming:
                            event[key] = incoming[key]
                    if event['state'] == 'pending' and not event['eligible']:
                        event['state'] = 'discovery'
                if (same_origin or better_origin) and not original_unchanged:
                    for key in ("headline", "evidence", "url", "source", "source_kind",
                                "source_priority", "published_at", "tickers", "eligible",
                                "materiality", "gate_reason", "content_genre"):
                        event[key] = incoming[key]
            # Exclude fetch time / provider echoes from the evidence revision.
            revision = digest({"headline": event["headline"],
                               "evidence": [(e["id"], e["text"]) for e in event["evidence"]]})
            changed = not existing or revision != existing["revision"]
            event["revision"] = revision
            if changed:
                event["source_revision"] = revision
                for key in ("evidence_health", "debate_id", "calls", "analysis", "challenge", "error"):
                    event.pop(key, None)
                event["updated_at"] = incoming["received_at"]
                event["state"] = "pending" if event["eligible"] else "discovery"
                event["trigger"] = incoming["trigger"]
                event["prior_revision"] = existing["revision"] if existing else None
                conn.execute("INSERT OR IGNORE INTO revisions VALUES (?,?,?)",
                             (event_id, revision, json.dumps(event)))
                for row in conn.execute("SELECT id,payload FROM cards").fetchall():
                    card = json.loads(row[1])
                    if card["event_id"] == event_id and not card.get("superseded"):
                        card["new_evidence_pending"] = True
                        conn.execute("UPDATE cards SET payload=? WHERE id=?", (json.dumps(card), row[0]))
            conn.execute("INSERT OR REPLACE INTO events VALUES (?,?)", (event_id, json.dumps(event)))
        return event, changed

    def enrich_event(self, event):
        """Version a newly fetched evidence pack without rearming on a feed echo."""
        event["revision"] = digest({"headline": event["headline"],
            "evidence": [(e["id"], e["text"]) for e in event["evidence"]]})
        with self.connect() as conn:
            conn.execute("INSERT OR IGNORE INTO revisions VALUES (?,?,?)",
                         (event["id"], event["revision"], json.dumps(event)))
            conn.execute("UPDATE events SET payload=? WHERE id=?", (json.dumps(event), event["id"]))
        return event

    def update_event(self, event):
        with self.connect() as conn:
            conn.execute("INSERT OR REPLACE INTO events VALUES (?,?)", (event["id"], json.dumps(event)))

    def publish(self, event, cards):
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute("SELECT payload FROM events WHERE id=?", (event["id"],)).fetchone()
            if not current or json.loads(current[0])["revision"] != event["revision"]:
                raise ValueError("stale event revision; refusing to publish")
            for row in conn.execute("SELECT id,payload FROM cards").fetchall():
                old = json.loads(row[1])
                if old["event_id"] == event["id"]:
                    old["superseded"] = True
                    conn.execute("UPDATE cards SET payload=? WHERE id=?", (json.dumps(old), row[0]))
            for card in cards:
                conn.execute("INSERT OR REPLACE INTO cards VALUES (?,?)", (card["id"], json.dumps(card)))
            event["state"] = "researched"
            conn.execute("UPDATE events SET payload=? WHERE id=?", (json.dumps(event), event["id"]))

    def observe(self, lane, ticker, revision):
        with self.connect() as conn:
            conn.execute("INSERT OR REPLACE INTO observations VALUES (?,?,?,?)",
                         (lane, ticker, revision, now_iso()))

    def observation(self, lane, ticker):
        with self.connect() as conn:
            row = conn.execute("SELECT revision, observed_at FROM observations WHERE lane=? AND ticker=?",
                               (lane, ticker)).fetchone()
        return {"revision": row[0], "observed_at": row[1]} if row else None
