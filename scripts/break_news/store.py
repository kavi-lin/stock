"""Atomic JSON store for break news items.

One file per news item at `news/break_news_logs/<news_id>.json`. Atomic writes
via tmp + rename. Per-id in-process lock so the poller + debater workers don't
clobber each other. `_seen_index.json` maps URL/headline hashes to news_id so
the poller can dedupe across polls. `_state.json` tracks poller + debater
health for the dashboard status pill.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STORE_DIR = ROOT / "news" / "break_news_logs"
RAW_DIR = STORE_DIR / "_raw"
SEEN_FILE = STORE_DIR / "_seen_index.json"
STATE_FILE = STORE_DIR / "_state.json"
RAW_STREAM_FILE = STORE_DIR / "_raw_stream.json"
SCHEMA_VERSION = 1

_locks: dict[str, threading.Lock] = {}
_locks_master = threading.Lock()
_seen_lock = threading.Lock()
_state_lock = threading.Lock()
_raw_stream_lock = threading.Lock()


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_dirs() -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)


def get_lock(news_id: str) -> threading.Lock:
    with _locks_master:
        lk = _locks.get(news_id)
        if lk is None:
            lk = threading.Lock()
            _locks[news_id] = lk
        return lk


def _atomic_write_json(path: Path, payload: dict) -> None:
    _ensure_dirs()
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def item_path(news_id: str) -> Path:
    return STORE_DIR / f"{news_id}.json"


def hash_key(url: str | None, headline_fp: str | None) -> str:
    base = (url or "") + "||" + (headline_fp or "")
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def make_news_id(url: str | None, headline_fp: str | None) -> str:
    h = hash_key(url, headline_fp)[:8]
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"bn_{today}_{h}"


def load_item(news_id: str) -> dict | None:
    p = item_path(news_id)
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def write_item(news_id: str, payload: dict) -> None:
    with get_lock(news_id):
        payload["last_activity_ts"] = _utc_iso()
        _atomic_write_json(item_path(news_id), payload)


def init_item(source: dict, triage: dict, headline: str, raw_summary: str) -> str:
    """Create a fresh `pending_debate` item. Returns news_id. Idempotent on hash."""
    url = source.get("url")
    fp = source.get("feed_fingerprint")
    seen = load_seen()
    key = hash_key(url, fp)
    if key in seen:
        return seen[key]["news_id"]

    news_id = make_news_id(url, fp)
    source = {**source, "url_hash": "sha1:" + hashlib.sha1((url or "").encode()).hexdigest()}
    payload = {
        "news_id": news_id,
        "schema_version": SCHEMA_VERSION,
        "state": "pending_debate",
        "fetched_at": _utc_iso(),
        "last_activity_ts": _utc_iso(),
        "source": source,
        "headline": headline,
        "headline_zh": None,
        "raw_summary": raw_summary,
        "triage": triage,
        "thread": [],
        "summary": None,
        "errors": [],
        "graph_promoted_at": None,
        "graph_status": "pending",
    }
    write_item(news_id, payload)
    mark_seen(key, news_id)
    return news_id


def set_state(news_id: str, state: str, **extra: Any) -> None:
    p = load_item(news_id)
    if p is None:
        return
    p["state"] = state
    for k, v in extra.items():
        p[k] = v
    write_item(news_id, p)


def append_comment(news_id: str, comment: dict) -> None:
    """Append a comment record to thread[]. Auto-assigns comment_id."""
    with get_lock(news_id):
        p = load_item(news_id)
        if p is None:
            return
        cid = f"c{len(p['thread'])}"
        comment = {"comment_id": cid, **comment}
        p["thread"].append(comment)
        p["last_activity_ts"] = _utc_iso()
        _atomic_write_json(item_path(news_id), p)


def set_summary(news_id: str, summary: dict) -> None:
    p = load_item(news_id)
    if p is None:
        return
    p["summary"] = summary
    write_item(news_id, p)


def push_error(news_id: str, where: str, msg: str) -> None:
    p = load_item(news_id)
    if p is None:
        return
    p.setdefault("errors", []).append({"ts": _utc_iso(), "where": where, "msg": msg[:500]})
    write_item(news_id, p)


def write_raw_stdout(news_id: str, comment_id: str, text: str) -> str:
    """Save raw CLI stdout. Return relative path stored on the comment."""
    _ensure_dirs()
    rel = f"news/break_news_logs/_raw/{news_id}.{comment_id}.txt"
    full = ROOT / rel
    full.write_text(text, encoding="utf-8")
    return rel


# ── seen index ───────────────────────────────────────────────────────────


def load_seen() -> dict:
    with _seen_lock:
        if not SEEN_FILE.exists():
            return {}
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}


def mark_seen(key: str, news_id: str) -> None:
    with _seen_lock:
        idx = {}
        if SEEN_FILE.exists():
            try:
                with open(SEEN_FILE, "r", encoding="utf-8") as f:
                    idx = json.load(f)
            except (OSError, json.JSONDecodeError):
                idx = {}
        idx[key] = {"news_id": news_id, "first_seen": _utc_iso()}
        _atomic_write_json(SEEN_FILE, idx)


def rebuild_seen_from_items() -> int:
    """Rescan all bn_*.json and rebuild the seen index. Returns count."""
    rebuilt: dict[str, dict] = {}
    for p in STORE_DIR.glob("bn_*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        src = d.get("source") or {}
        url = src.get("url")
        fp = src.get("feed_fingerprint")
        rebuilt[hash_key(url, fp)] = {
            "news_id": d.get("news_id"),
            "first_seen": d.get("fetched_at", _utc_iso()),
        }
    _atomic_write_json(SEEN_FILE, rebuilt)
    return len(rebuilt)


# ── state file ───────────────────────────────────────────────────────────


def load_state() -> dict:
    with _state_lock:
        if not STATE_FILE.exists():
            return {"poller": {}, "debater": {}}
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {"poller": {}, "debater": {}}


def update_state(section: str, patch: dict) -> None:
    with _state_lock:
        state = {"poller": {}, "debater": {}}
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except (OSError, json.JSONDecodeError):
                pass
        cur = state.get(section) or {}
        cur.update(patch)
        state[section] = cur
        _atomic_write_json(STATE_FILE, state)


def list_items_by_state(states: list[str] | None = None) -> list[dict]:
    """Return summary dicts (not full thread) for feed endpoint."""
    out: list[dict] = []
    for p in STORE_DIR.glob("bn_*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if states and d.get("state") not in states:
            continue
        out.append({
            "news_id": d.get("news_id"),
            "state": d.get("state"),
            "headline": d.get("headline"),
            "headline_zh": d.get("headline_zh"),
            "source": (d.get("source") or {}).get("name"),
            "credibility": (d.get("source") or {}).get("credibility"),
            "url": (d.get("source") or {}).get("url"),
            "published": (d.get("source") or {}).get("published"),
            "fetched_at": d.get("fetched_at"),
            "last_activity_ts": d.get("last_activity_ts"),
            "shallow_score": (d.get("triage") or {}).get("shallow_score"),
            "news_type": (d.get("triage") or {}).get("news_type"),
            "binary_flag": (d.get("triage") or {}).get("binary_flag"),
            "comment_count": len(d.get("thread") or []),
            "consensus_verdict": ((d.get("summary") or {}) or {}).get("consensus_verdict"),
        })
    out.sort(key=lambda x: x.get("last_activity_ts") or "", reverse=True)
    return out


# ── raw stream (un-gated breaking-news feed) ─────────────────────────────
# Every RSS item the poller fetches — gated AND un-gated — lands here so the
# break-news UI can show a real-time feed before the score gate. The gate
# still governs *automatic* debates; this is just the manual-trigger surface.


def load_raw_stream() -> list[dict]:
    """All recently-fetched RSS items (gated + un-gated), newest first."""
    with _raw_stream_lock:
        if not RAW_STREAM_FILE.exists():
            return []
        try:
            with open(RAW_STREAM_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []


def _raw_entry_ts(e: dict) -> float:
    try:
        return datetime.strptime(
            e.get("fetched_at", ""), "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return 0.0


def save_raw_stream(entries: list[dict], cap: int = 150, max_age_h: int = 24) -> int:
    """Merge `entries` into the rolling raw-stream file. Dedupe by `key`
    (newer entry wins, but a kept `news_id` is never lost), keep newest `cap`,
    drop anything older than `max_age_h`. Returns kept count."""
    cutoff = datetime.now(timezone.utc).timestamp() - max_age_h * 3600
    with _raw_stream_lock:
        existing: list[dict] = []
        if RAW_STREAM_FILE.exists():
            try:
                with open(RAW_STREAM_FILE, "r", encoding="utf-8") as f:
                    d = json.load(f)
                existing = d if isinstance(d, list) else []
            except (OSError, json.JSONDecodeError):
                existing = []
        merged: dict[str, dict] = {}
        for e in existing + list(entries):
            k = e.get("key")
            if not k:
                continue
            prev = merged.get(k)
            if prev and prev.get("news_id") and not e.get("news_id"):
                # carry forward an existing promotion so a re-poll can't wipe it
                e = {**e, "news_id": prev["news_id"],
                     "promoted_at": prev.get("promoted_at")}
            merged[k] = e
        kept = [e for e in merged.values() if _raw_entry_ts(e) >= cutoff]
        kept.sort(key=_raw_entry_ts, reverse=True)
        kept = kept[:cap]
        _atomic_write_json(RAW_STREAM_FILE, kept)
        return len(kept)


def mark_raw_promoted(key: str, news_id: str) -> bool:
    """Tag a raw-stream entry as promoted to a debate item. Returns True if found."""
    with _raw_stream_lock:
        if not RAW_STREAM_FILE.exists():
            return False
        try:
            with open(RAW_STREAM_FILE, "r", encoding="utf-8") as f:
                items = json.load(f)
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(items, list):
            return False
        hit = False
        for e in items:
            if e.get("key") == key:
                e["news_id"] = news_id
                e["promoted_at"] = _utc_iso()
                hit = True
        if hit:
            _atomic_write_json(RAW_STREAM_FILE, items)
        return hit


def sweep_stuck_debating(stuck_secs: int = 900) -> int:
    """Reset items with state=debating older than stuck_secs to pending_debate.
    Returns count of items reset. Called at server startup."""
    n = 0
    now = time.time()
    for p in STORE_DIR.glob("bn_*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if d.get("state") != "debating":
            continue
        ts = d.get("last_activity_ts") or d.get("fetched_at") or ""
        try:
            t = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            t = 0
        if now - t < stuck_secs:
            continue
        d["state"] = "pending_debate"
        d.setdefault("errors", []).append({
            "ts": _utc_iso(), "where": "startup_sweep",
            "msg": f"reset from debating after {int(now - t)}s",
        })
        _atomic_write_json(item_path(d["news_id"]), d)
        n += 1
    return n


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild-seen", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--state", action="store_true")
    args = ap.parse_args()
    if args.rebuild_seen:
        print(f"rebuilt seen index: {rebuild_seen_from_items()} entries")
    if args.sweep:
        print(f"reset {sweep_stuck_debating()} stuck items")
    if args.state:
        print(json.dumps(load_state(), indent=2))
