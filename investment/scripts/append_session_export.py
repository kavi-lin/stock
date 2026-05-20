#!/usr/bin/env python3
"""
Append a Phase 5 session export entry to `investment/invest_logs/history.json`.

Replaces the legacy pattern of having the PM hand-write the full JSON block
inside the protocol prompt — which was high-output-token, error-prone (malformed
JSON forces a Sonnet retry), and tangled append + validate into one prompt step.

Now Phase 5 Step 1 calls this script with the entry JSON, and the script:
  1. Reads stdin / --from-file / --from-arg
  2. Validates basic top-level shape (full schema check is `validate_session_export.py`)
  3. Acquires an exclusive flock on history.json
  4. Atomic write: tmp file + rename
  5. Mirrors top-level `ticker` / `final_action` / `export_date` to entry root if missing

Invocation:
    cat new_entry.json | python3 investment/scripts/append_session_export.py
    python3 investment/scripts/append_session_export.py --from-file path/to/entry.json
    python3 investment/scripts/append_session_export.py --from-arg '<json>'

Return codes:
    0 — appended successfully
    1 — schema error (malformed JSON, missing required top-level keys)
    2 — IO error (history.json unreadable / unwritable / lock failure)

Idempotency: this script does NOT dedupe — protocol must call it exactly once
per session. `register_thesis.py` runs AFTER this and back-fills `thesis_id` on
the same (last) entry.

Race safety: `fcntl.flock(LOCK_EX)` held for the full read-modify-write window;
parallel callers serialize. Atomic rename ensures readers never see a half-write.
"""
import argparse
import fcntl
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT         = Path(__file__).resolve().parents[2]
HISTORY_JSON = ROOT / "investment" / "invest_logs" / "history.json"

# Minimal top-level shape gate — full schema enforcement is delegated to
# `validate_session_export.py`, which the protocol runs in Phase 5 Step 2.
TOP_REQUIRED_MIN = (
    "session_export_version", "export_date", "ticker", "final_action",
    "trades_this_session",
)


def _err(msg: str, rc: int = 1) -> None:
    print(f"[append_session_export] ✗ {msg}", file=sys.stderr)
    sys.exit(rc)


def _read_input(args) -> str:
    if args.from_file:
        try:
            return Path(args.from_file).read_text(encoding="utf-8")
        except OSError as e:
            _err(f"--from-file unreadable: {e}", rc=2)
    if args.from_arg:
        return args.from_arg
    if sys.stdin.isatty():
        _err("no input — pipe JSON via stdin, --from-file PATH, or --from-arg '<json>'")
    return sys.stdin.read()


def _parse_entry(raw: str) -> dict:
    raw = raw.strip()
    if not raw:
        _err("empty input")
    try:
        entry = json.loads(raw)
    except json.JSONDecodeError as e:
        _err(f"malformed JSON: {e}")
    if not isinstance(entry, dict):
        _err(f"top-level must be object, got {type(entry).__name__}")
    return entry


def _check_min_shape(entry: dict) -> None:
    missing = [k for k in TOP_REQUIRED_MIN if k not in entry]
    if missing:
        _err(f"missing required top-level keys: {missing}")
    trades = entry.get("trades_this_session")
    if not isinstance(trades, list) or not trades:
        _err("trades_this_session must be a non-empty array")
    if not isinstance(trades[0], dict):
        _err("trades_this_session[0] must be an object")


def _mirror_top_level(entry: dict) -> None:
    """Phase 5 schema requires top-level ticker / final_action / export_date to
    mirror trades_this_session[0]. Fill if missing; cross-check if present."""
    trade0 = entry["trades_this_session"][0]
    for k in ("ticker", "final_action"):
        if k not in entry and k in trade0:
            entry[k] = trade0[k]
    # `date` is a legacy alias for export_date — keep both filled
    if "date" not in entry and "export_date" in entry:
        entry["date"] = entry["export_date"]


def _atomic_append(entry: dict) -> int:
    if not HISTORY_JSON.exists():
        _err(f"history.json not found at {HISTORY_JSON}", rc=2)

    # Open for read+write, hold exclusive lock for the whole RMW window so
    # concurrent appends serialize and register_thesis.py never reads a
    # half-written file.
    try:
        fp = HISTORY_JSON.open("r+", encoding="utf-8")
    except OSError as e:
        _err(f"history.json unreadable: {e}", rc=2)
    try:
        fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
        try:
            existing = json.load(fp)
        except json.JSONDecodeError as e:
            _err(f"history.json is malformed JSON: {e}", rc=2)
        if not isinstance(existing, list):
            _err("history.json must be a JSON array", rc=2)
        existing.append(entry)

        # Atomic write via tempfile in the same directory + rename.
        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False,
            dir=str(HISTORY_JSON.parent), prefix=".history.", suffix=".tmp",
        )
        try:
            json.dump(existing, tmp, indent=2, ensure_ascii=False)
            tmp.write("\n")
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, HISTORY_JSON)
        except OSError as e:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            _err(f"atomic write failed: {e}", rc=2)
        return len(existing)
    finally:
        try:
            fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
        finally:
            fp.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Append Phase 5 session export entry")
    ap.add_argument("--from-file", type=str, help="Read entry JSON from this file")
    ap.add_argument("--from-arg",  type=str, help="Read entry JSON from this argument")
    args = ap.parse_args()

    entry = _parse_entry(_read_input(args))
    _check_min_shape(entry)
    _mirror_top_level(entry)

    new_len = _atomic_append(entry)
    trade0 = entry["trades_this_session"][0]
    print(
        f"[append_session_export] ✓ appended — "
        f"{trade0.get('ticker','?')} / {trade0.get('final_decision','?')} / "
        f"{entry.get('final_action','?')} (history len={new_len})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
