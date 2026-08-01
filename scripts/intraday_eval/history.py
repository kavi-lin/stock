#!/usr/bin/env python3
"""
Intraday Evaluation — recurrence history.

Tracks which strategy cards fire in each 10-minute window so the UI can add
"repeated strategy" effects:
  - streak     : consecutive recent windows (incl. current) a strategy fired
                 → drives the pulsing-glow highlight (streak >= 2)
  - day_count  : total windows today a strategy fired
                 → drives the ×N full-day count badge

State lives in Dashboard/intraday_eval_history_<DATE>.json (one file per
trading day; a fresh day starts clean). Deterministic, 0-LLM.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from . import engine as _eng  # atomic write + paths (package import)

# Windows recorded within this many seconds of the previous one REPLACE it,
# so manual /refresh spam doesn't inflate streak / day_count.
_DEDUPE_SEC = 240

# streak >= this fires the highlight; day_count >= this flags a day-long motif.
STREAK_HIGHLIGHT = 2
DAY_MOTIF_MIN = 3


def _history_path(date_str):
    return os.path.join(_eng.DASHBOARD_DIR, f"intraday_eval_history_{date_str}.json")


def _load(date_str):
    path = _history_path(date_str)
    data = _eng._read_json(path)
    if not isinstance(data, dict) or "windows" not in data:
        return {"date": date_str, "windows": []}
    return data


def annotate_and_record(payload):
    """Attach streak/day_count to each strategy card, record this window, and
    write the per-day history file. Returns the mutated payload."""
    date_str = (payload.get("as_of_et") or "")[:10] or \
        datetime.now(timezone.utc).date().isoformat()
    hist = _load(date_str)
    windows = hist.get("windows") or []

    current_ids = [c["id"] for c in payload.get("strategies", [])]
    now_iso = payload.get("as_of") or datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Decide append vs replace-last (dedupe rapid refreshes).
    replace_last = False
    if windows:
        try:
            prev = datetime.fromisoformat(windows[-1]["as_of"].replace("Z", "+00:00"))
            cur = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
            if (cur - prev).total_seconds() < _DEDUPE_SEC:
                replace_last = True
        except Exception:
            pass

    new_window = {"as_of": now_iso, "strategy_ids": current_ids,
                  "regime_label": (payload.get("regime") or {}).get("label")}

    # Build the full sequence used for streak/day_count (with current appended
    # or replacing the last window).
    seq = [w.get("strategy_ids") or [] for w in windows]
    if replace_last and seq:
        seq[-1] = current_ids
    else:
        seq.append(current_ids)

    for card in payload.get("strategies", []):
        cid = card["id"]
        # streak: walk backward from the newest window while present
        streak = 0
        for ids in reversed(seq):
            if cid in ids:
                streak += 1
            else:
                break
        day_count = sum(1 for ids in seq if cid in ids)
        card["streak"] = streak
        card["day_count"] = day_count
        card["highlight"] = streak >= STREAK_HIGHLIGHT
        card["day_motif"] = day_count >= DAY_MOTIF_MIN

    payload["recurrence"] = {
        "window_index": len(seq),
        "windows_today": len(seq),
        "highlighted": [c["id"] for c in payload.get("strategies", []) if c.get("highlight")],
        "day_motifs": [c["id"] for c in payload.get("strategies", []) if c.get("day_motif")],
        "streak_highlight_min": STREAK_HIGHLIGHT,
        "day_motif_min": DAY_MOTIF_MIN,
    }

    # Persist window
    if replace_last and windows:
        windows[-1] = new_window
    else:
        windows.append(new_window)
    hist["windows"] = windows
    hist["date"] = date_str
    try:
        _eng._write_atomic(_history_path(date_str), hist)
    except Exception:
        payload.setdefault("warnings", []).append("history write failed")

    return payload


def load_history(date_str=None):
    """Read a day's window timeline for the /history API + timeline viz."""
    date_str = date_str or _eng._now_et().date().isoformat()
    hist = _load(date_str)
    windows = hist.get("windows") or []
    # per-strategy day_count for a compact legend
    counts = {}
    for w in windows:
        for cid in (w.get("strategy_ids") or []):
            counts[cid] = counts.get(cid, 0) + 1
    return {
        "date": date_str,
        "windows": windows,
        "counts": counts,
        "windows_today": len(windows),
    }
