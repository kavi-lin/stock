#!/usr/bin/env python3
"""Analysis watermark over the append-only shadow log.

The collector guarantees only NEW posts are *fetched* (`since_id`). This module
gives the same guarantee to whatever consumes them — the LLM stage must only ever
see posts it has not already analyzed, or a $10 pilot pays an LLM to re-read the
same tweets every sweep.

Mechanism: a byte offset into the log. The log is strictly append-only, so an
offset is an exact, O(1) cursor — seek there, read forward, and everything you get
is new by construction. No per-record "analyzed" flag (that would mean rewriting
an append-only file) and no unbounded set of seen ids.

Crash safety: `read_pending()` returns records plus the offset they end at, but
does NOT move the cursor. Call `commit()` only after the analysis actually
succeeded. A crash mid-analysis therefore re-serves the same records rather than
silently dropping them — at-least-once, which for an exploration log is the right
side to fail on.

    from scripts.x_kol import pending
    batch = pending.read_pending(log_path, cursor_path)
    ...analyze batch.records...
    pending.commit(cursor_path, batch.offset)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CURSOR_PATH = ROOT / "config/x_kol_analysis_cursor.json"


@dataclass
class Batch:
    records: list[dict] = field(default_factory=list)
    offset: int = 0          # byte offset AFTER the last record in `records`
    start_offset: int = 0
    malformed: int = 0

    def __len__(self) -> int:
        return len(self.records)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_cursor(cursor_path: Path | None = None) -> dict:
    try:
        with open(cursor_path or CURSOR_PATH, encoding="utf-8") as fp:
            data = json.load(fp)
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "offset": 0, "analyzed": 0, "updated_at": None}
    data.setdefault("offset", 0)
    data.setdefault("analyzed", 0)
    return data


def commit(cursor_path: Path | None, offset: int, *, analyzed: int = 0) -> dict:
    """Advance the watermark. Call only after analysis succeeded."""
    path = cursor_path or CURSOR_PATH
    cursor = load_cursor(path)
    cursor["offset"] = int(offset)
    cursor["analyzed"] = int(cursor.get("analyzed", 0)) + int(analyzed)
    cursor["updated_at"] = _now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fp:
        json.dump(cursor, fp, ensure_ascii=False, indent=2, sort_keys=True)
        fp.write("\n")
    os.replace(tmp, path)
    return cursor


def read_pending(log_path: Path, cursor_path: Path | None = None, *,
                 limit: int | None = None) -> Batch:
    """Records appended since the last commit. Does not move the cursor."""
    cursor = load_cursor(cursor_path)
    start = int(cursor.get("offset", 0))
    batch = Batch(offset=start, start_offset=start)
    if not Path(log_path).exists():
        return batch

    size = os.path.getsize(log_path)
    if start > size:
        # Log shrank (rotated/truncated). Re-reading from 0 would re-analyze the
        # whole file, so restart from the top only because there is no longer any
        # way to know what the old offset referred to — and say so loudly.
        batch.start_offset = start = 0
        batch.offset = 0

    with open(log_path, "r", encoding="utf-8") as fp:
        fp.seek(start)
        while True:
            pos = fp.tell()
            line = fp.readline()
            if not line:
                break
            if not line.endswith("\n"):
                # Partial trailing line — a writer is mid-append. Stop before it;
                # the next pass picks it up whole.
                batch.offset = pos
                return batch
            stripped = line.strip()
            if stripped:
                try:
                    batch.records.append(json.loads(stripped))
                except json.JSONDecodeError:
                    batch.malformed += 1
            batch.offset = fp.tell()
            if limit is not None and len(batch.records) >= limit:
                break
    return batch


def status(log_path: Path, cursor_path: Path | None = None) -> dict:
    cursor = load_cursor(cursor_path)
    size = os.path.getsize(log_path) if Path(log_path).exists() else 0
    batch = read_pending(log_path, cursor_path)
    return {
        "log_bytes": size,
        "cursor_offset": cursor.get("offset", 0),
        "analyzed_total": cursor.get("analyzed", 0),
        "pending_records": len(batch.records),
        "malformed": batch.malformed,
        "updated_at": cursor.get("updated_at"),
    }
