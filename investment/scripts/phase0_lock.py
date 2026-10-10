#!/usr/bin/env python3
"""Phase 0 rebuild lock — stops concurrent `分析 <TICKER>` runs from each
independently re-running the same 4-skill L3 chain + FRED fetch when the
shared canonical `invest_logs/*_phase0.json` snapshot is stale.

Problem this fixes: two protocol runs launched moments apart (e.g. GOOG and
JPM dispatched ~8s apart) each read the same stale canonical file and each
kick off a full L3 rebuild, paying the external-API cost twice for the one
market snapshot they'll both end up sharing.

Ownership model: each `acquire`/`release` invocation is its own short-lived
process (the agent calls this via a one-shot bash command), so there is no
long-lived PID to check liveness against. Ownership is instead a random
token handed back by `acquire` — the caller must pass it back to `release`.
Staleness is purely time-based (no L3 rebuild observed so far has taken
longer than ~20 min; see investment/scan_logs/invest_20260902_220140_2906.log).

Usage (called directly by the agent via bash, per investment_protocol_v5_0.md
Phase 0 L3 section):

    python3 investment/scripts/phase0_lock.py acquire
        # rc=0 + {"status":"acquired","token":"..."} -> caller does the L3
        #                                                rebuild, then MUST
        #                                                call `release --token ...`.
        # rc=1 + {"status":"held", ...}                -> someone else is rebuilding.

    python3 investment/scripts/phase0_lock.py wait --timeout 900
        # rc=0 + {"status":"released"}    -> lock is free; re-check canonical
        #                                    phase0.json freshness before
        #                                    deciding to rebuild again.
        # rc=1 + {"status":"timeout", ...} -> stop and report to the user; do
        #                                    NOT steal the lock or rebuild anyway.

    python3 investment/scripts/phase0_lock.py release --token <token>
        # rc=0 + {"status":"released"}         -> normal handoff.
        # rc=1 + {"status":"bad_token", ...}    -> token didn't match (or lock
        #                                          already gone); nothing removed.

A lock older than LOCK_MAX_AGE_SEC is treated as abandoned and is reaped
automatically by the next `acquire` or `wait` call — a crashed or killed
agent process must not leave every later run blocked forever.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK_DIR = ROOT / "investment" / "invest_logs" / "protocol_tmp" / "phase0.lock"
OWNER_FILE = LOCK_DIR / "owner.json"

DEFAULT_WAIT_TIMEOUT_SEC = 900   # 15 min — comfortably above a normal L3 rebuild
POLL_INTERVAL_SEC = 5
LOCK_MAX_AGE_SEC = 1200          # 20 min — above the slowest observed L3 rebuild


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_owner() -> dict | None:
    try:
        return json.loads(OWNER_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _lock_age_sec(owner: dict | None) -> float | None:
    if not owner or "acquired_at" not in owner:
        return None
    try:
        acquired = datetime.fromisoformat(owner["acquired_at"])
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - acquired).total_seconds()


def _force_remove_lock() -> None:
    try:
        if OWNER_FILE.exists():
            OWNER_FILE.unlink()
        LOCK_DIR.rmdir()
    except OSError:
        # Lost a race with another reaper/release; fine either way.
        pass


def _reap_if_stale() -> bool:
    """Remove LOCK_DIR if it doesn't exist, or exists but is older than
    LOCK_MAX_AGE_SEC / has an unreadable owner file. Returns True if the
    lock is (now) free."""
    if not LOCK_DIR.exists():
        return True
    owner = _read_owner()
    age = _lock_age_sec(owner)
    if age is None or age > LOCK_MAX_AGE_SEC:
        _force_remove_lock()
        return True
    return False


def cmd_acquire(_args) -> int:
    LOCK_DIR.parent.mkdir(parents=True, exist_ok=True)
    _reap_if_stale()
    try:
        LOCK_DIR.mkdir()
    except FileExistsError:
        owner = _read_owner() or {}
        print(json.dumps({
            "status": "held",
            "held_since": owner.get("acquired_at"),
            "age_sec": _lock_age_sec(owner),
        }))
        return 1
    token = secrets.token_hex(8)
    OWNER_FILE.write_text(json.dumps({
        "token": token,
        "acquired_at": _now_iso(),
    }))
    print(json.dumps({"status": "acquired", "token": token}))
    return 0


def cmd_wait(args) -> int:
    deadline = time.monotonic() + args.timeout
    while True:
        if _reap_if_stale():
            print(json.dumps({"status": "released"}))
            return 0
        if time.monotonic() >= deadline:
            owner = _read_owner() or {}
            print(json.dumps({
                "status": "timeout",
                "waited_sec": args.timeout,
                "held_since": owner.get("acquired_at"),
                "age_sec": _lock_age_sec(owner),
            }))
            return 1
        time.sleep(min(POLL_INTERVAL_SEC, max(0, deadline - time.monotonic())))


def cmd_release(args) -> int:
    if not LOCK_DIR.exists():
        print(json.dumps({"status": "released"}))
        return 0
    owner = _read_owner()
    owner_token = owner.get("token") if owner else None
    if owner_token != args.token:
        print(json.dumps({"status": "bad_token"}))
        return 1
    _force_remove_lock()
    print(json.dumps({"status": "released"}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("acquire").set_defaults(func=cmd_acquire)
    p_wait = sub.add_parser("wait")
    p_wait.add_argument("--timeout", type=int, default=DEFAULT_WAIT_TIMEOUT_SEC)
    p_wait.set_defaults(func=cmd_wait)
    p_release = sub.add_parser("release")
    p_release.add_argument("--token", required=True)
    p_release.set_defaults(func=cmd_release)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
