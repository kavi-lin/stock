#!/usr/bin/env python3
"""Contract for broker-backed multi-active protocol scheduling (V4.134.0)."""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.argv = ["dashboard_server.py"]

import dashboard_server as ds  # noqa: E402

failures = []


def check(name, condition, detail=""):
    if not condition:
        failures.append(f"{name}: {detail}")


# Different tickers own isolated Phase 5 session exports; the same ticker still
# remains single-writer so a rerun cannot overwrite its per-session files.
check("domain.invest_per_ticker",
      ds._protocol_artifact_key("invest", {"ticker": "AAA"})
      != ds._protocol_artifact_key("invest", {"ticker": "BBB"}))
check("domain.invest_same_ticker",
      ds._protocol_artifact_key("invest", {"ticker": "AAA"})
      == ds._protocol_artifact_key("invest", {"ticker": "aaa"}))
check("domain.news_global",
      ds._protocol_artifact_key("news") == ds._protocol_artifact_key("flash"))
check("domain.earnings_per_ticker",
      ds._protocol_artifact_key("earnings", {"ticker": "AAA"})
      != ds._protocol_artifact_key("earnings", {"ticker": "BBB"}))
check("broker_busy.retryable", ds._retryable_dispatch_error("broker:refused(provider_busy)"))
check("broker_unavailable.retryable", ds._retryable_dispatch_error(
      "quota broker: did not authorise (broker:unavailable)"))
check("hard_reserve.waits_in_queue", ds._retryable_dispatch_error(
      "broker:refused(no_capacity): every provider is reserve-only"))

with ds._protocol_queue_lock:
    ds._protocol_queue.clear()
ds._requeue_protocol_entry(
    {"id": "retry-quota", "name": "invest", "params": {"ticker": "NVDA"}},
    "broker:refused(no_capacity): every provider is reserve-only",
)
with ds._protocol_queue_lock:
    quota_entry = ds._protocol_queue.pop(0)
check("hard_reserve.reason_visible", quota_entry.get("waiting_reason") == "quota_wait",
      repr(quota_entry))

with ds._protocol_queue_lock:
    ds._protocol_queue.clear()
ds._requeue_protocol_entry(
    {"id": "retry-intc", "name": "invest", "params": {"ticker": "INTC"}},
    "quota broker: broker:unavailable",
)
with ds._protocol_queue_lock:
    retry_entry = ds._protocol_queue.pop(0)
check("broker_unavailable.reason_visible",
      retry_entry.get("waiting_reason") == "broker_unavailable", repr(retry_entry))
check("broker_unavailable.attempt_tracked", retry_entry.get("attempts") == 1,
      repr(retry_entry))
check("broker_unavailable.backoff_bounded",
      0 < retry_entry.get("retry_at", 0) - time.time() <= 3.1, repr(retry_entry))

# A run has a short broker-select -> Popen window. Cancelling while no child is
# published must not mark it terminal and free its artifact/scheduler slot.
starting_state = {
    "job_id": "starting_cancel_guard",
    "name": "news",
    "status": "running",
    "started_at": ds._now_iso(),
    "ended_at": None,
    "artifact_key": ds._protocol_artifact_key("news"),
}
with ds._protocol_lock:
    ds._register_protocol_run(starting_state["job_id"], starting_state, {"p": None})
check("cancel.starting_rejected", not ds.cancel_protocol(job_id=starting_state["job_id"]))
check("cancel.starting_keeps_slot", starting_state["status"] == "running"
      and starting_state["ended_at"] is None, repr(starting_state))
with ds._protocol_lock:
    ds._protocol_runs.pop(starting_state["job_id"], None)

release = threading.Event()
dispatched = []
peak_active = 0
real_run_protocol = ds.run_protocol


def fake_run_protocol(name, params=None):
    """Register a real per-job state while avoiding vendor CLIs and quota."""
    global peak_active
    params = params or {}
    job_id = f"fake_{len(dispatched) + 1}"
    state = {
        "job_id": job_id,
        "name": name,
        "status": "running",
        "started_at": ds._now_iso(),
        "ended_at": None,
        "error": None,
        "ticker": params.get("ticker"),
        "model": ["claude", "codex", "gemini"][len(dispatched) % 3],
        "model_tier": "test",
        "artifact_key": ds._protocol_artifact_key(name, params),
    }
    with ds._protocol_lock:
        ds._register_protocol_run(job_id, state, {"p": None})
        dispatched.append((name, params.get("ticker"), time.monotonic()))
        peak_active = max(peak_active, len(ds._active_protocol_states()))

    def finish():
        release.wait(timeout=10)
        with ds._protocol_lock:
            state.update({"status": "done", "ended_at": ds._now_iso()})

    threading.Thread(target=finish, daemon=True).start()
    return job_id, None


try:
    with ds._protocol_queue_lock:
        ds._protocol_queue.clear()
        ds._protocol_history.clear()
    with ds._protocol_lock:
        ds._protocol_runs.clear()
        ds._protocol_inflight.clear()
    ds.run_protocol = fake_run_protocol

    # Four different invest tickers: three occupy the three broker slots and
    # the fourth stays queued. This is the user-visible research concurrency
    # contract, not merely a mixed-protocol scheduler test.
    ds.enqueue_protocol("invest", {"ticker": "AAAA"})
    ds.enqueue_protocol("invest", {"ticker": "BBBB"})
    ds.enqueue_protocol("invest", {"ticker": "CCCC"})
    ds.enqueue_protocol("invest", {"ticker": "DDDD"})

    deadline = time.monotonic() + 6
    while time.monotonic() < deadline and len(dispatched) < 3:
        time.sleep(0.05)

    state = ds.get_queue_state()
    check("worker.three_parallel", len(dispatched) == 3, repr(dispatched))
    check("worker.active_array", len(state["active"]) == 3, repr(state["active"]))
    check("worker.capacity_exact", peak_active == ds.PROTOCOL_MAX_ACTIVE == 3,
          f"peak={peak_active}, capacity={ds.PROTOCOL_MAX_ACTIVE}")
    check("worker.fourth_waits", len(state["queue"]) == 1, repr(state["queue"]))

    release.set()
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline and len(dispatched) < 4:
        time.sleep(0.05)
    check("worker.refills_slot", len(dispatched) == 4, repr(dispatched))
finally:
    release.set()
    ds.run_protocol = real_run_protocol
    time.sleep(1.2)
    with ds._protocol_queue_lock:
        ds._protocol_queue.clear()
    with ds._protocol_lock:
        ds._protocol_runs.clear()
        ds._protocol_inflight.clear()

if failures:
    print("FAIL")
    for failure in failures:
        print(" -", failure)
    sys.exit(1)
print("OK — broker-backed protocol scheduler (3 parallel, bounded, refill verified)")
