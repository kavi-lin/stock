#!/usr/bin/env python3
"""Contract for the invest→invest cooldown (V4.121.4).

Two claims, and the second is the one that matters:
  1. `_cooldown_remaining_sec` computes the wait correctly.
  2. The **real worker loop** honours it — the waiting entry stays in the queue,
     a countdown is published, and re-queuing that ticker mid-wait is rejected.

Claim 2 goes through `_analyze_worker` itself rather than calling the helper,
because the 2026-08-10 incident was not a wrong number: it was a correct wait
that nothing could see. A helper-only test would have stayed green through it.
Delete the cooldown branch from the worker and `worker.gap_enforced` +
`worker.cooldown_visible` go red.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.argv = ["dashboard_server.py"]
# Read per call, so setting it here shortens the test without touching prod.
os.environ["INTER_ANALYSIS_COOLDOWN_SEC"] = "4"

import dashboard_server as ds  # noqa: E402

failures = []


def check(name, condition, detail=""):
    if not condition:
        failures.append(f"{name}: {detail}")


# ── 1. The wait itself ────────────────────────────────────────────────────
now = datetime(2026, 8, 10, 8, 40, 0)

check("pure.just_finished",
      ds._cooldown_remaining_sec("invest", now - timedelta(seconds=1), "invest", now) == 3,
      "1s after an invest run, 3 of the 4s cooldown remain")
check("pure.already_elapsed",
      ds._cooldown_remaining_sec("invest", now - timedelta(seconds=30), "invest", now) == 0,
      "past the window → dispatch immediately")
check("pure.non_invest_before",
      ds._cooldown_remaining_sec("news", now, "invest", now) == 0,
      "only two consecutive invest runs cool down")
check("pure.non_invest_after",
      ds._cooldown_remaining_sec("invest", now, "news", now) == 0)
check("pure.no_previous_run",
      ds._cooldown_remaining_sec("invest", None, "invest", now) == 0,
      "nothing finished yet → nothing to wait for")

os.environ["INTER_ANALYSIS_COOLDOWN_SEC"] = "0"
check("pure.disabled",
      ds._cooldown_remaining_sec("invest", now, "invest", now) == 0,
      "0 disables the cooldown entirely")
os.environ["INTER_ANALYSIS_COOLDOWN_SEC"] = "4"

# ── 2. It is exported, and the countdown moves with wall-clock ────────────
ds._publish_cooldown(120, {"label": "🔬 NVDA", "name": "invest", "id": "x"})
snap = ds.get_queue_state().get("cooldown")
check("publish.exported", snap is not None, "get_queue_state must carry the wait")
check("publish.remaining", bool(snap) and 115 <= snap["remaining_sec"] <= 120,
      f"remaining_sec={snap and snap.get('remaining_sec')}")
check("publish.label", bool(snap) and snap["label"] == "🔬 NVDA",
      "the UI names the run that is waiting, not just 'something'")
ds._publish_cooldown(0)
check("publish.cleared", ds.get_queue_state().get("cooldown") is None)


# ── 3. The worker loop actually gates on it ───────────────────────────────
dispatched = []


def fake_run_protocol(name, params=None):
    """Stand-in for a real dispatch: flips the state machine the worker polls,
    finishes fast, spawns no subprocess and spends no quota."""
    dispatched.append((name, (params or {}).get("ticker"), time.monotonic()))
    job = f"fake_{len(dispatched)}"
    with ds._protocol_lock:
        ds._protocol_state.update({
            "job_id": job, "name": name, "status": "running",
            "started_at": ds._now_iso(), "ended_at": None, "error": None,
            "model": "codex", "model_tier": "cli-default",
        })

    def _finish():
        time.sleep(0.5)
        with ds._protocol_lock:
            ds._protocol_state.update({"status": "done", "ended_at": ds._now_iso()})

    threading.Thread(target=_finish, daemon=True).start()
    return job, None


real_run_protocol = ds.run_protocol
ds.run_protocol = fake_run_protocol
try:
    with ds._protocol_queue_lock:
        ds._protocol_queue.clear()
        ds._protocol_history.clear()
    with ds._protocol_lock:
        ds._protocol_state.update({"status": "idle", "name": None, "ended_at": None})
    ds._publish_cooldown(0)

    ds.enqueue_protocol("invest", {"ticker": "AAAA"})
    ds.enqueue_protocol("invest", {"ticker": "BBBB"})

    saw_cooldown_with_entry_queued = False
    dedup_verdict = None
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline and len(dispatched) < 2:
        st = ds.get_queue_state()
        waiting = any((q.get("params") or {}).get("ticker") == "BBBB" for q in st["queue"])
        if st.get("cooldown") and waiting:
            saw_cooldown_with_entry_queued = True
            if dedup_verdict is None:
                # The root cause of the duplicate NVDA run: an entry popped
                # before the sleep was in neither the queue nor the active
                # slot, so this guard could not see it.
                _state, _err = ds.enqueue_protocol("invest", {"ticker": "BBBB"})
                dedup_verdict = (_state or {}).get("reason"), _err
        time.sleep(0.2)

    check("worker.both_dispatched", len(dispatched) == 2,
          f"dispatched={[(d[0], d[1]) for d in dispatched]}")
    check("worker.cooldown_visible", saw_cooldown_with_entry_queued,
          "the waiting invest must stay in the queue AND publish a countdown")
    check("worker.dedup_during_cooldown", dedup_verdict == ("duplicate_pending", "duplicate"),
          f"re-queue during cooldown returned {dedup_verdict}, expected a duplicate rejection")
    if len(dispatched) == 2:
        gap = dispatched[1][2] - dispatched[0][2]
        check("worker.gap_enforced", gap >= 4.0,
              f"gap={gap:.1f}s — the cooldown was not actually waited out")
finally:
    ds.run_protocol = real_run_protocol
    with ds._protocol_queue_lock:
        ds._protocol_queue.clear()
    ds._publish_cooldown(0)

if failures:
    print("FAIL")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print(f"OK — protocol cooldown contract ({len(dispatched)} dispatches through the real worker)")
