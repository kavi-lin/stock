"""AI Office — run lifecycle + append-only event log.

Each run lives under reports/office/<run_id>/:
  - meta.json       run metadata + status (running | done | stopped | failed)
  - events.jsonl    append-only stream of turn/system events (replayable)
  - deliverable.md  final deliverable (written when the run completes)

The append-only JSONL is the single source of truth the UI tails over SSE, so a
browser refresh / late attach replays the whole collaboration for free.
"""

import json
import os
import threading
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OFFICE_DIR = os.path.join(ROOT, "reports", "office")

_TERMINAL = {"done", "stopped", "failed"}
_lock = threading.Lock()  # serializes meta read-modify-write + event appends


def _run_dir(run_id):
    return os.path.join(OFFICE_DIR, run_id)


def _valid_run_id(run_id):
    return bool(run_id) and run_id.replace("-", "").replace("_", "").isalnum()


def new_run_id():
    # Sortable + unique enough for a single-user dashboard.
    return datetime.now().strftime("%Y%m%d-%H%M%S-") + os.urandom(2).hex()


def create_run(task, roles):
    run_id = new_run_id()
    os.makedirs(_run_dir(run_id), exist_ok=True)
    meta = {
        "run_id": run_id,
        "task": task,
        "status": "running",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "finished_at": None,
        "rounds_completed": 0,
        "close_reason": None,
        "roles": [{"key": r.key, "name": r.name, "engine": r.engine} for r in roles],
        "spend": {},          # engine -> call count made by this run
        "error": None,
    }
    _write_meta(run_id, meta)
    append_event(run_id, {"type": "run_started", "task": task,
                          "roles": meta["roles"]})
    return run_id, meta


def _meta_path(run_id):
    return os.path.join(_run_dir(run_id), "meta.json")


def _write_meta(run_id, meta):
    tmp = _meta_path(run_id) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _meta_path(run_id))


def load_meta(run_id):
    if not _valid_run_id(run_id):
        return None
    try:
        with open(_meta_path(run_id), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def update_meta(run_id, **fields):
    with _lock:
        meta = load_meta(run_id)
        if meta is None:
            return None
        meta.update(fields)
        _write_meta(run_id, meta)
        return meta


def bump_spend(run_id, engine):
    with _lock:
        meta = load_meta(run_id)
        if meta is None:
            return
        meta.setdefault("spend", {})
        meta["spend"][engine] = meta["spend"].get(engine, 0) + 1
        _write_meta(run_id, meta)


def set_terminal(run_id, status, close_reason=None, error=None):
    assert status in _TERMINAL
    return update_meta(run_id, status=status, close_reason=close_reason,
                       error=error,
                       finished_at=datetime.now().isoformat(timespec="seconds"))


def append_event(run_id, event):
    """Append one event (dict). Stamps seq + ts. Returns the stored event."""
    with _lock:
        path = os.path.join(_run_dir(run_id), "events.jsonl")
        seq = 0
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                seq = sum(1 for _ in f)
        event = {"seq": seq, "ts": datetime.now().isoformat(timespec="seconds"),
                 **event}
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event


def load_events(run_id, since=0):
    """Events with seq >= since."""
    path = os.path.join(_run_dir(run_id), "events.jsonl")
    out = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if ev.get("seq", 0) >= since:
                    out.append(ev)
    except OSError:
        pass
    return out


def load_deliverable(run_id):
    path = os.path.join(_run_dir(run_id), "deliverable.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def write_deliverable(run_id, markdown):
    with open(os.path.join(_run_dir(run_id), "deliverable.md"), "w",
              encoding="utf-8") as f:
        f.write(markdown)


def list_runs(limit=50):
    if not os.path.isdir(OFFICE_DIR):
        return []
    runs = []
    for name in os.listdir(OFFICE_DIR):
        meta = load_meta(name)
        if meta:
            runs.append({k: meta.get(k) for k in
                         ("run_id", "task", "status", "created_at",
                          "finished_at", "rounds_completed", "close_reason")})
    runs.sort(key=lambda m: m.get("created_at") or "", reverse=True)
    return runs[:limit]


def active_run():
    """Return the run_id of a currently-running run, or None."""
    for r in list_runs(limit=20):
        if r.get("status") == "running":
            return r["run_id"]
    return None
