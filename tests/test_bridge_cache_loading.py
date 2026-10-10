"""Which file counts as "the newest snapshot", and what happens if it isn't one.

Both halves come from a live failure on 2026-08-26: the whole bridge run died
with `TypeError: list indices must be integers` because `market_breadth_*.json`
also matches `market_breadth_history.json` — an aggregate list of past runs that
the analyzer rewrites in the same second as the snapshot. Which of the two won
`max(mtime)` came down to the order `glob.glob()` happened to return.

The reason it was expensive to diagnose is that nothing failed where the wrong
file was read. `"generated_at" not in some_list` is perfectly legal Python, so
the guard in front of the crash passed, and the error surfaced three thousand
lines later with no mention of the file that caused it.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bridge  # noqa: E402


def _write(path: Path, payload) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_an_aggregate_file_never_wins_newest(tmp_path: Path) -> None:
    snapshot = _write(tmp_path / "market_breadth_2026-08-26_224407.json", {"composite": {}})
    history = _write(tmp_path / "market_breadth_history.json", [{"score": 1}])
    # The real collision: same mtime to the second, so ordering decided it.
    same_moment = (1_787_755_447, 1_787_755_447)
    os.utime(snapshot, same_moment)
    os.utime(history, same_moment)

    assert bridge.get_latest_file(str(tmp_path / "market_breadth_*.json")) == str(snapshot)


def test_a_newer_aggregate_file_still_does_not_win(tmp_path: Path) -> None:
    """The analyzer writes the history file last often enough to matter."""
    snapshot = _write(tmp_path / "ftd_detector_2026-08-26_224407.json", {"market_state": {}})
    history = _write(tmp_path / "ftd_detector_history.json", [])
    os.utime(snapshot, (1_787_755_400, 1_787_755_400))
    os.utime(history, (1_787_755_999, 1_787_755_999))

    assert bridge.get_latest_file(str(tmp_path / "ftd_detector_*.json")) == str(snapshot)


def test_a_cache_that_is_not_an_object_is_skipped_where_it_is_read(tmp_path: Path) -> None:
    """Named, at the point of reading — not a TypeError somewhere downstream."""
    history = _write(tmp_path / "market_breadth_history.json", [{"score": 1}])

    assert bridge.load_snapshot_json(str(history), "Breadth cache") is None


def test_a_well_formed_snapshot_still_loads(tmp_path: Path) -> None:
    snapshot = _write(tmp_path / "market_top_2026-08-26_224421.json", {"composite": {"score": 38}})

    loaded = bridge.load_snapshot_json(str(snapshot), "Market Top cache")

    assert loaded == {"composite": {"score": 38}}


def test_an_unreadable_file_is_skipped_rather_than_raised(tmp_path: Path) -> None:
    broken = tmp_path / "market_top_2026-08-26_224421.json"
    broken.write_text("{not json", encoding="utf-8")

    assert bridge.load_snapshot_json(str(broken), "Market Top cache") is None
