#!/usr/bin/env python3
"""Concurrency contract for isolated Phase 5 prepare/commit writes."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "append_session_export.py"
FAILS: list[str] = []


def check(label: str, condition: bool, detail="") -> None:
    if not condition:
        FAILS.append(f"{label}: {detail}")


def entry(ticker: str) -> dict:
    return {
        "session_export_version": "V5.3",
        "export_date": "2026-08-21",
        "ticker": ticker,
        "final_action": "CANCEL",
        "trades_this_session": [{
            "ticker": ticker,
            "final_decision": "HOLD",
            "final_action": "CANCEL",
        }],
    }


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
    )


with tempfile.TemporaryDirectory() as tmp_raw:
    tmp = Path(tmp_raw)
    history = tmp / "history.json"
    history.write_text("[]\n", encoding="utf-8")
    session = tmp / "session.json"
    session.write_text(json.dumps(entry("PREP")), encoding="utf-8")

    prepared = run(
        "--from-file", str(session), "--history", str(history),
        "--stamp-only", "--stamped-out", str(session),
    )
    check("prepare.rc", prepared.returncode == 0, prepared.stderr)
    check("prepare.no_history_write", json.loads(history.read_text()) == [])
    stamped = json.loads(session.read_text())
    check("prepare.stamped", "entry_digest" in stamped.get("export_provenance", {}), stamped)

    tampered_path = tmp / "tampered.json"
    tampered = json.loads(json.dumps(stamped))
    tampered["final_action"] = "BUY"
    tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
    rejected = run(
        "--from-file", str(tampered_path), "--history", str(history), "--preserve-stamp",
    )
    check("tamper.rc", rejected.returncode == 1, rejected.stderr)
    check("tamper.rejected", "digest mismatch" in rejected.stderr, rejected.stderr)
    check("tamper.no_history_write", json.loads(history.read_text()) == [])

    committed = run(
        "--from-file", str(session), "--history", str(history), "--preserve-stamp",
    )
    check("commit.rc", committed.returncode == 0, committed.stderr)
    check("commit.exact_entry", json.loads(history.read_text()) == [stamped])
    check("commit.stable_lock", Path(str(history) + ".lock").exists())

    # Start enough writers together to expose the old lock-on-replaced-inode
    # race. Every process must survive and every ticker must land exactly once.
    history.write_text("[]\n", encoding="utf-8")
    inputs = []
    for index in range(18):
        path = tmp / f"T{index:02d}.json"
        path.write_text(json.dumps(entry(f"T{index:02d}")), encoding="utf-8")
        inputs.append(path)
    procs = [
        subprocess.Popen(
            [sys.executable, str(SCRIPT), "--from-file", str(path),
             "--history", str(history)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        for path in inputs
    ]
    results = [proc.communicate(timeout=15) + (proc.returncode,) for proc in procs]
    check("parallel.all_rc0", all(result[2] == 0 for result in results), results)
    landed = json.loads(history.read_text())
    tickers = [item.get("ticker") for item in landed]
    check("parallel.no_lost_entries", len(landed) == len(inputs), tickers)
    check("parallel.no_duplicates", len(set(tickers)) == len(inputs), tickers)

if FAILS:
    print(f"✗ {len(FAILS)} failure(s)")
    for failure in FAILS:
        print("  -", failure)
    raise SystemExit(1)
print("✓ append_session_export: isolated prepare + 18 concurrent commits are lossless")
