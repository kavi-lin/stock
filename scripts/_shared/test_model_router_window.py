#!/usr/bin/env python3
"""test_model_router_window.py — V4.84.0 rolling-window budget contract.

What this locks down:

1. **The window is independent of the daily budget.** Either cap alone takes a model
   out of the chain, and `model_headroom` reports the tighter of the two.

2. **Midnight does not refill the window.** This is the whole point of the feature: the
   UTC-day counters reset at 00:00 but `call_timestamps` survive, because the provider's
   session window does not care what day it is. A rollover that cleared them would hand
   back a full window of headroom exactly when the session cap is still in force.

3. **Old usage files stay readable.** Entries written before V4.84.0 have no
   `call_timestamps`; they read as an empty window rather than crashing or being
   back-filled with invented history.

4. **The config actually reaches the router.** `load_llm_config()` whitelists budget keys
   rather than merging them, so a new key that is not named in the loader is dropped
   silently and the cap never takes effect — which is exactly what happened on the first
   run of this feature. The end-to-end case below goes through the real loader and the
   real `config/llm_config.json`, not a hand-built cfg dict.

Run: python3 scripts/_shared/test_model_router_window.py   # rc=0 全過 / rc=1 fail
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts._shared import model_router as mr  # noqa: E402

FAILS: list[str] = []


def eq(label, got, want):
    if got != want:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


def _cfg(cap=3, hours=5.0, daily=100, model="claude"):
    return {"enabled": {model: True},
            "budgets": {model: {"daily_max_calls": daily,
                                "window_max_calls": cap, "window_hours": hours}}}


def _usage(stamps, model="claude", calls=None, date=None):
    return {"date": date or mr._today(),
            "models": {model: {"calls": len(stamps) if calls is None else calls,
                               "cooldown_until": None, "last_error": None,
                               "tokens": mr._blank_tokens(),
                               "call_timestamps": list(stamps)}}}


def _ago(**kw):
    return (mr._now() - timedelta(**kw)).isoformat()


# ── window config parsing ───────────────────────────────────────────────────
eq("cfg.parsed", mr._window_cfg("claude", _cfg(7, 5.0)), (7, 5.0))
eq("cfg.absent_is_uncapped", mr._window_cfg("claude", {"budgets": {"claude": {}}}),
   (0, mr.DEFAULT_WINDOW_HOURS))
eq("cfg.zero_is_uncapped",
   mr._window_cfg("claude", {"budgets": {"claude": {"window_max_calls": 0}}})[0], 0)
eq("cfg.unknown_model_uncapped", mr._window_cfg("nope", _cfg())[0], 0)
eq("cfg.garbage_cap_uncapped",
   mr._window_cfg("claude", {"budgets": {"claude": {"window_max_calls": "lots"}}})[0], 0)
eq("cfg.zero_hours_falls_back",
   mr._window_cfg("claude", {"budgets": {"claude": {"window_hours": 0}}})[1],
   mr.DEFAULT_WINDOW_HOURS)


# ── counting inside / outside the window ────────────────────────────────────
entry = {"call_timestamps": [_ago(minutes=10), _ago(hours=2), _ago(hours=4, minutes=59),
                             _ago(hours=6), _ago(hours=30)]}
eq("count.5h", mr._window_calls(entry, 5.0), 3)
eq("count.1h", mr._window_calls(entry, 1.0), 1)
eq("count.24h", mr._window_calls(entry, 24.0), 4)
eq("count.empty", mr._window_calls({}, 5.0), 0)
eq("count.garbage_ignored",
   mr._window_calls({"call_timestamps": ["not-a-date", None, 42, _ago(minutes=1)]}, 5.0), 1)
# A naive timestamp from an older writer counts as UTC — dropping it would under-count.
_naive = (datetime.now(timezone.utc) - timedelta(minutes=5)).replace(tzinfo=None).isoformat()
eq("count.naive_counted", mr._window_calls({"call_timestamps": [_naive]}, 5.0), 1)
# Clock skew into the future must not silently free a slot.
_future = (mr._now() + timedelta(minutes=30)).isoformat()
eq("count.future_counted", mr._window_calls({"call_timestamps": [_future]}, 5.0), 1)


# ── availability: the two budgets are independent gates ─────────────────────
cfg = _cfg(cap=3, hours=5.0, daily=100)
eq("avail.under_both", mr.model_available("claude", cfg, _usage([_ago(hours=1)]))[0], True)
at_cap = _usage([_ago(minutes=1), _ago(hours=1), _ago(hours=2)])
eq("avail.window_blocks", mr.model_available("claude", cfg, at_cap), (False, "window"))
# Same three calls, all aged out → available again.
aged = _usage([_ago(hours=6), _ago(hours=7), _ago(hours=8)])
eq("avail.window_rolls_off", mr.model_available("claude", cfg, aged)[0], True)
# Daily budget still bites on its own, with an empty window.
eq("avail.daily_blocks",
   mr.model_available("claude", _cfg(cap=3, daily=2), _usage([], calls=2)), (False, "budget"))
# Uncapped window never blocks.
eq("avail.uncapped_window",
   mr.model_available("claude", _cfg(cap=0), _usage([_ago(minutes=i) for i in range(50)]))[0],
   True)
# Cooldown outranks both.
cd = _usage([])
cd["models"]["claude"]["cooldown_until"] = (mr._now() + timedelta(hours=1)).isoformat()
eq("avail.cooldown_first", mr.model_available("claude", cfg, cd), (False, "cooldown"))


# ── headroom is the tighter of the two budgets ──────────────────────────────
eq("headroom.window_tighter",
   mr.model_headroom("claude", _cfg(cap=3, daily=100), _usage([_ago(hours=1)]))[0], 2)
eq("headroom.daily_tighter",
   mr.model_headroom("claude", _cfg(cap=50, daily=5), _usage([_ago(hours=1)], calls=4))[0], 1)
eq("headroom.no_caps",
   mr.model_headroom("claude", {"enabled": {"claude": True},
                                "budgets": {"claude": {}}}, _usage([]))[0], None)
eq("headroom.blocked_is_zero",
   mr.model_headroom("claude", cfg, at_cap), (0, False, "window"))


# ── window_state reporting ──────────────────────────────────────────────────
st = mr.window_state("claude", cfg, at_cap)
eq("state.hours", st["window_hours"], 5.0)
eq("state.cap", st["window_max_calls"], 3)
eq("state.used", st["window_calls"], 3)
eq("state.remaining", st["window_remaining"], 0)
eq("state.reset_reported", st["window_resets_at"] is not None, True)
st_ok = mr.window_state("claude", cfg, _usage([_ago(hours=1)]))
eq("state.no_reset_when_under_cap", st_ok["window_resets_at"], None)
eq("state.remaining_under_cap", st_ok["window_remaining"], 2)
st_unc = mr.window_state("claude", _cfg(cap=0), _usage([_ago(hours=1)]))
eq("state.uncapped_reports_none", st_unc["window_max_calls"], None)
eq("state.uncapped_remaining_none", st_unc["window_remaining"], None)


# ── persistence: midnight must NOT refill the window ────────────────────────
def _with_usage_file(payload, fn):
    orig = mr.USAGE_FILE
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "llm_usage.json"
        p.write_text(json.dumps(payload), encoding="utf-8")
        mr.USAGE_FILE = p
        try:
            return fn()
        finally:
            mr.USAGE_FILE = orig


cfg_file = _cfg(cap=3, hours=5.0, daily=100)

# Yesterday's file, three calls made within the last 5 hours (i.e. across midnight).
stale_day = {"date": "1999-01-01",
             "models": {"claude": {"calls": 3, "cooldown_until": None, "last_error": None,
                                   "tokens": mr._blank_tokens(),
                                   "call_timestamps": [_ago(minutes=5), _ago(hours=1),
                                                       _ago(hours=2)]}}}
rolled = _with_usage_file(stale_day, lambda: mr._load_usage(cfg_file))
eq("rollover.daily_counter_reset", rolled["models"]["claude"]["calls"], 0)
eq("rollover.date_is_today", rolled["date"], mr._today())
eq("rollover.window_survives", mr._window_calls(rolled["models"]["claude"], 5.0), 3)
eq("rollover.still_blocked", mr.model_available("claude", cfg_file, rolled), (False, "window"))

# Timestamps older than the window are pruned rather than carried forever.
old_day = {"date": "1999-01-01",
           "models": {"claude": {"calls": 3, "cooldown_until": None, "last_error": None,
                                 "tokens": mr._blank_tokens(),
                                 "call_timestamps": [_ago(hours=20), _ago(hours=40),
                                                     _ago(hours=99)]}}}
pruned = _with_usage_file(old_day, lambda: mr._load_usage(cfg_file))
eq("rollover.pruned", pruned["models"]["claude"]["call_timestamps"], [])
eq("rollover.available_after_prune", mr.model_available("claude", cfg_file, pruned)[0], True)

# Pre-V4.84.0 shape: no call_timestamps at all.
legacy = {"date": mr._today(),
          "models": {"claude": {"calls": 7, "cooldown_until": None, "last_error": None,
                                "tokens": mr._blank_tokens()}}}
loaded = _with_usage_file(legacy, lambda: mr._load_usage(cfg_file))
eq("legacy.timestamps_defaulted", loaded["models"]["claude"]["call_timestamps"], [])
eq("legacy.daily_calls_kept", loaded["models"]["claude"]["calls"], 7)
eq("legacy.available", mr.model_available("claude", cfg_file, loaded)[0], True)

# Corrupt / missing file must not raise.
broken = _with_usage_file({"garbage": True}, lambda: mr._load_usage(cfg_file))
eq("corrupt.recovers", broken["date"], mr._today())


# ── _stamp_call writes both counters ────────────────────────────────────────
e = {"calls": 0}
mr._stamp_call(e)
mr._stamp_call(e)
eq("stamp.daily", e["calls"], 2)
eq("stamp.window", len(e["call_timestamps"]), 2)
eq("stamp.window_counted", mr._window_calls(e, 5.0), 2)
# A legacy entry whose call_timestamps is not a list is repaired, not crashed on.
e2 = {"calls": 5, "call_timestamps": None}
mr._stamp_call(e2)
eq("stamp.repairs_bad_type", len(e2["call_timestamps"]), 1)


# ── end-to-end: the shipped config must survive load_llm_config() ───────────
# Regression guard for the whitelist trap described in the docstring: asserting on a
# hand-built cfg dict passes even when the loader throws the keys away.
_live = mr.load_llm_config()
_raw = json.loads((Path(mr._ROOT) / "config" / "llm_config.json").read_text(encoding="utf-8"))
for _m, _mb in (_raw.get("budgets") or {}).items():
    if not isinstance(_mb, dict) or "window_max_calls" not in _mb:
        continue
    eq(f"loader.{_m}.window_max_calls",
       mr._window_cfg(_m, _live)[0], int(_mb["window_max_calls"]))
    if "window_hours" in _mb:
        eq(f"loader.{_m}.window_hours",
           mr._window_cfg(_m, _live)[1], float(_mb["window_hours"]))
# At least one model must actually carry a window cap, or this file is testing nothing.
eq("loader.some_model_is_capped",
   any(mr._window_cfg(m, _live)[0] > 0 for m in (_live.get("budgets") or {})), True)

# model_status() surfaces the window fields the Office UI reads.
_status = mr.model_status()
for _m in _status["models"]:
    for _k in ("window_hours", "window_max_calls", "window_calls",
               "window_remaining", "window_resets_at"):
        if _k not in _status["models"][_m]:
            FAILS.append(f"status.{_m}: missing {_k}")


# ──────────────────────────────────────────────────────────────────────────────
if FAILS:
    print(f"✗ {len(FAILS)} failure(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ model_router rolling-window contract holds")
