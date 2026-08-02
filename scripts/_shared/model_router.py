"""Multi-model governance — role-based routing, per-model daily call budget,
rolling-window call budget, quota cooldown, auto-fallback.

Every governed model call goes through `run_role()` / `run_with_fallback()`:
they walk the configured fallback chain (primary → secondary → tertiary), skip
models that are disabled / over their daily budget / over their rolling-window
budget / in a quota cooldown, and on a quota or hard failure transparently fall
back to the next model.

Two independent budgets, both enforced (V4.84.0):
  * `daily_max_calls`  — resets on UTC date rollover
  * `window_max_calls` over `window_hours` — a rolling window that does NOT reset
    at midnight, because the provider's session window does not either.
    Absent / 0 = uncapped, same convention as the daily budget.

**What the window does and does not govern** (corrected in V4.86.0 — the original
claim that it makes "protocol runs self-throttle" was wrong on both halves):
  * It DOES gate `run_role()` / `run_with_fallback()` / `pick_model()`, i.e. the
    single-shot governed calls, and it removes an exhausted model from the chain.
  * It does NOT gate the agentic protocol subprocess path. `dashboard_server`
    deliberately bypasses `pick_model` there (a user-clicked protocol is an explicit
    model choice, see its comment) and only reports the outcome afterwards through
    `note_run()`. That records **one** timestamp for a run that may spend dozens to
    hundreds of API turns, so the window under-counts the largest consumer by design.
    Treat `window_calls` as "governed calls", not "API turns"; sizing the cap as if it
    were the provider's turn budget will not protect that path.

Usage counters + cooldowns persist in `config/llm_usage.json`. The daily counters
auto-reset on UTC date rollover; `call_timestamps` deliberately survive that reset
(see `_load_usage`) so a window straddling midnight is measured correctly.

The returned `LLMResult` is annotated with `.model_used`, `.fell_back`,
`.route_note`.

Standalone: `python3 scripts/_shared/model_router.py --status`
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:      # non-POSIX — the usage lock degrades to a no-op
    fcntl = None

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.break_news.llm_drivers import (  # noqa: E402
    LLMResult, LLM_TIMEOUT_SEC, VALID_MODELS, load_llm_config, model_chain, run_llm,
)

USAGE_FILE = _ROOT / "config" / "llm_usage.json"

# Best-effort quota / rate-limit wall signatures (case-insensitive). CLIs do
# not return a structured quota code, so we sniff error text + stdout.
_QUOTA_RE = re.compile(
    r"usage limit|rate.?limit|rate_limit|\b429\b|too many requests|"
    r"resource[ _]exhausted|quota|insufficient_quota|overloaded|"
    r"out of (?:credit|quota)", re.I)


# ─────────────────────────── usage state ────────────────────────────────────
def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _blank_tokens() -> dict:
    return {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cost_usd": 0.0}


def _blank_usage() -> dict:
    return {
        "date": _today(),
        "models": {m: {"calls": 0, "cooldown_until": None, "last_error": None,
                       "tokens": _blank_tokens(), "call_timestamps": []}
                   for m in VALID_MODELS},
    }


# ───────────────────── rolling window (V4.84.0) ─────────────────────────────
DEFAULT_WINDOW_HOURS = 5.0
# A timestamp further ahead than this is a clock fault, not a call. Counting it would
# wedge the window shut with no way to recover; ignoring near-future skew would let a
# fast clock hand back slots. Kept generous so ordinary NTP drift still counts.
_MAX_FUTURE_SKEW_HOURS = 24.0


def _window_cfg(model: str, cfg: dict) -> tuple[int, float]:
    """(window_max_calls, window_hours) for `model`. max 0 = uncapped."""
    b = (cfg.get("budgets", {}) or {}).get(model, {}) or {}
    try:
        cap = int(b.get("window_max_calls", 0) or 0)
    except (TypeError, ValueError):
        cap = 0
    try:
        hours = float(b.get("window_hours", DEFAULT_WINDOW_HOURS) or DEFAULT_WINDOW_HOURS)
    except (TypeError, ValueError):
        hours = DEFAULT_WINDOW_HOURS
    return max(0, cap), (hours if hours > 0 else DEFAULT_WINDOW_HOURS)


def _parse_ts(v) -> datetime | None:
    if not isinstance(v, str) or not v:
        return None
    try:
        d = datetime.fromisoformat(v)
    except (TypeError, ValueError):
        return None
    # A naive timestamp from an older writer is read as UTC rather than dropped —
    # discarding it would silently under-count the window.
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _prune_timestamps(stamps, hours: float) -> list[str]:
    """Keep only stamps inside the model's own window, and drop clock-fault stamps.

    Retention is exactly `hours`: nothing older can affect `_window_calls`, and
    shrinking `window_hours` in config drops the now-irrelevant stamps on the next
    load rather than stranding them. (V4.86.0 — this used to clamp to a 48h ceiling,
    which silently truncated any window configured longer than that.)
    """
    if not isinstance(stamps, list):
        return []
    now = _now()
    cutoff = now - timedelta(hours=max(hours, 0.0))
    horizon = now + timedelta(hours=_MAX_FUTURE_SKEW_HOURS)
    out = []
    for s in stamps:
        d = _parse_ts(s)
        if d is not None and cutoff <= d <= horizon:
            out.append(d.isoformat())
    return out


def _window_calls(entry: dict, hours: float) -> int:
    """How many calls this model made inside the trailing `hours`.

    Near-future stamps still count (a slightly fast clock must not free up slots), but
    one beyond `_MAX_FUTURE_SKEW_HOURS` is a clock fault and is ignored — otherwise a
    single bad stamp wedges the window shut with no path to recovery.
    """
    now = _now()
    cutoff = now - timedelta(hours=hours)
    horizon = now + timedelta(hours=_MAX_FUTURE_SKEW_HOURS)
    n = 0
    for s in entry.get("call_timestamps") or []:
        d = _parse_ts(s)
        if d is not None and cutoff <= d <= horizon:
            n += 1
    return n


def _accumulate_tokens(entry: dict, tok: dict | None) -> None:
    """Add a single run's token counts into a model's running daily totals.
    Accepts either llm_drivers field names (input_tokens/…) or the compact
    persisted names (input/…). No-op on empty/invalid input."""
    if not isinstance(tok, dict) or not tok:
        return
    t = entry.setdefault("tokens", _blank_tokens())
    for dst, srcs in (("input", ("input", "input_tokens")),
                      ("output", ("output", "output_tokens")),
                      ("cache_read", ("cache_read", "cache_read_tokens")),
                      ("cache_write", ("cache_write", "cache_write_tokens"))):
        for s in srcs:
            if s in tok:
                t[dst] = int(t.get(dst, 0) or 0) + int(tok.get(s, 0) or 0)
                break
    cost = tok.get("cost_usd")
    if cost:
        t["cost_usd"] = round(float(t.get("cost_usd", 0.0) or 0.0) + float(cost), 6)


def _load_usage(cfg: dict | None = None) -> dict:
    """Read llm_usage.json; auto-reset the daily counters on UTC date rollover.

    Three things deliberately SURVIVE the rollover, because none of them is a
    property of the UTC day:

      * `call_timestamps` — the rolling window tracks the provider's session window,
        which pays no attention to midnight. Zeroing it would hand back a full
        window's worth of headroom at 00:00 UTC.
      * `cooldown_until` — a 4h quota cooldown tripped at 23:30 is still in force at
        00:00. Dropping it (V4.84.0 did) sent traffic straight back into a wall the
        provider had not lifted yet.
      * `last_error` — the operator-facing explanation for that cooldown; clearing it
        while the cooldown stands leaves an unexplained block.

    What DOES reset is the daily call counter and the token totals, which are exactly
    the per-UTC-day quantities.

    Entries written before V4.84.0 have no `call_timestamps`. They get an empty list,
    so the window starts measuring from now rather than pretending to know history.
    """
    cfg = cfg if isinstance(cfg, dict) else load_llm_config()
    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            u = json.load(f)
    except (OSError, json.JSONDecodeError):
        u = None
    if not isinstance(u, dict) or not isinstance(u.get("models"), dict):
        u = None

    carried = {}
    if u is not None:
        for m, e in (u.get("models") or {}).items():
            if isinstance(e, dict):
                carried[m] = e

    if u is None or u.get("date") != _today():
        fresh = _blank_usage()
        for m, e in fresh["models"].items():
            prev = carried.get(m) or {}
            _, hours = _window_cfg(m, cfg)
            e["call_timestamps"] = _prune_timestamps(prev.get("call_timestamps"), hours)
            # Carry a cooldown only while it is still in the future — an expired one
            # would otherwise be resurrected every load.
            cu = prev.get("cooldown_until")
            if _parse_ts(cu) is not None and _parse_ts(cu) > _now():
                e["cooldown_until"] = cu
                e["last_error"] = prev.get("last_error")
        return fresh

    for m in VALID_MODELS:
        e = u["models"].setdefault(
            m, {"calls": 0, "cooldown_until": None, "last_error": None})
        if not isinstance(e.get("tokens"), dict):
            e["tokens"] = _blank_tokens()
        else:
            for k, v in _blank_tokens().items():
                e["tokens"].setdefault(k, v)
        _, hours = _window_cfg(m, cfg)
        e["call_timestamps"] = _prune_timestamps(e.get("call_timestamps"), hours)
    return u


def _save_usage(u: dict) -> None:
    try:
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(USAGE_FILE.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(u, f, ensure_ascii=False, indent=2)
        os.replace(tmp, USAGE_FILE)
    except OSError:
        pass


@contextlib.contextmanager
def _usage_write_lock():
    """Serialise the load → mutate → save cycle ACROSS PROCESSES (V4.86.0).

    The individual write is atomic (mkstemp + os.replace), which is why a torn file
    was never the problem. The problem is the read-modify-write: the dashboard server,
    the break-news poller and a CLI invocation each load the same counters, increment
    their own, and save — so concurrent recorders overwrite each other and the budget
    under-counts, letting real usage exceed a cap that looks respected on disk.

    A separate `.lock` file is used rather than the usage file itself, because
    `os.replace` swaps the inode out from under any lock held on it.

    Best-effort: if flock is unavailable or the lock cannot be taken, the body still
    runs. Losing an occasional increment is strictly better than dropping the call.
    """
    lock_path = USAGE_FILE.with_suffix(".lock")
    fh = None
    try:
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        fh = open(lock_path, "a+")
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
    except (OSError, NameError, AttributeError):
        if fh is not None:
            try:
                fh.close()
            except OSError:
                pass
            fh = None
    try:
        yield
    finally:
        if fh is not None:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            finally:
                fh.close()


# ─────────────────────────── availability ───────────────────────────────────
def is_quota_error(result: LLMResult) -> bool:
    """Best-effort: did this result hit a quota / rate-limit wall?"""
    if result is None or (result.exit_code == 0 and result.parsed):
        return False
    blob = f"{result.error or ''} {result.raw_stdout or ''}"
    return bool(_QUOTA_RE.search(blob))


def _in_cooldown(entry: dict) -> bool:
    cu = entry.get("cooldown_until")
    if not cu:
        return False
    try:
        return datetime.fromisoformat(cu) > _now()
    except (ValueError, TypeError):
        return False


def model_available(model: str, cfg: dict, usage: dict) -> tuple[bool, str]:
    """Return (available, reason-if-not).

    The two budgets are independent gates: `budget` = the UTC-day cap, `window` = the
    rolling session-window cap. Either alone takes the model out of the chain.
    """
    if not cfg.get("enabled", {}).get(model, True):
        return False, "disabled"
    entry = usage["models"].get(model, {})
    if _in_cooldown(entry):
        return False, "cooldown"
    budget = cfg.get("budgets", {}).get(model, {}).get("daily_max_calls", 0)
    if budget and entry.get("calls", 0) >= budget:
        return False, "budget"
    win_cap, win_hours = _window_cfg(model, cfg)
    if win_cap and _window_calls(entry, win_hours) >= win_cap:
        return False, "window"
    return True, ""


def window_state(model: str, cfg: dict, usage: dict) -> dict:
    """Rolling-window snapshot for `model` — for --status and the Office UI."""
    cap, hours = _window_cfg(model, cfg)
    entry = usage["models"].get(model, {}) or {}
    used = _window_calls(entry, hours)
    stamps = sorted(s for s in (entry.get("call_timestamps") or []) if _parse_ts(s))
    oldest = _parse_ts(stamps[0]) if stamps else None
    return {
        "window_hours": hours,
        "window_max_calls": cap or None,
        "window_calls": used,
        "window_remaining": (max(0, cap - used) if cap else None),
        # When the cap is hit, this is when the oldest call ages out and one slot
        # frees up — more actionable than "blocked" with no horizon.
        "window_resets_at": ((oldest + timedelta(hours=hours)).isoformat()
                             if (cap and used >= cap and oldest) else None),
    }


def model_status() -> dict:
    """Per-model snapshot — for GET /api/llm-config."""
    cfg = load_llm_config()
    usage = _load_usage(cfg)
    models = {}
    for m in VALID_MODELS:
        e = usage["models"].get(m, {})
        avail, reason = model_available(m, cfg, usage)
        models[m] = {
            "calls": e.get("calls", 0),
            "daily_max": cfg.get("budgets", {}).get(m, {}).get("daily_max_calls", 0),
            "enabled": cfg.get("enabled", {}).get(m, True),
            "available": avail,
            "unavailable_reason": reason,
            "cooldown_until": e.get("cooldown_until"),
            "last_error": e.get("last_error"),
            "tokens": e.get("tokens") or _blank_tokens(),
            **window_state(m, cfg, usage),
        }
    return {"date": usage["date"], "chain": model_chain(cfg), "models": models}


def model_headroom(model: str, cfg: dict | None = None, usage: dict | None = None) -> tuple[int | None, bool, str]:
    """Remaining governed calls for `model`.

    Returns (headroom, available, reason). `headroom is None` means the model is
    enabled and available with no configured daily call cap.
    """
    cfg = cfg or load_llm_config()
    usage = usage or _load_usage(cfg)
    avail, reason = model_available(model, cfg, usage)
    if not avail:
        return 0, False, reason
    budget = cfg.get("budgets", {}).get(model, {}).get("daily_max_calls", 0)
    entry = usage.get("models", {}).get(model) or {}
    limits = []
    if budget:
        limits.append(max(0, int(budget) - int(entry.get("calls", 0) or 0)))
    win_cap, win_hours = _window_cfg(model, cfg)
    if win_cap:
        limits.append(max(0, win_cap - _window_calls(entry, win_hours)))
    # Headroom is the tighter of the two budgets — a caller planning N calls must
    # not be told it has daily room when the rolling window will stop it first.
    if not limits:
        return None, True, ""
    return min(limits), True, ""


def _stamp_call(entry: dict) -> None:
    """Record this call against both budgets: the daily counter and the rolling window."""
    entry["calls"] = entry.get("calls", 0) + 1
    stamps = entry.get("call_timestamps")
    if not isinstance(stamps, list):
        stamps = []
    stamps.append(_now().isoformat())
    entry["call_timestamps"] = stamps


def _record(model: str, result: LLMResult, cfg: dict) -> None:
    """Increment the call counters; trip a cooldown on a quota wall.

    The whole load → mutate → save cycle is held under `_usage_write_lock` so a
    concurrent recorder in another process cannot clobber this increment.
    """
    with _usage_write_lock():
        usage = _load_usage(cfg)
        e = usage["models"].setdefault(
            model, {"calls": 0, "cooldown_until": None, "last_error": None})
        _stamp_call(e)
        _accumulate_tokens(e, {
            "input_tokens": getattr(result, "input_tokens", 0),
            "output_tokens": getattr(result, "output_tokens", 0),
            "cache_read_tokens": getattr(result, "cache_read_tokens", 0),
            "cache_write_tokens": getattr(result, "cache_write_tokens", 0),
            "cost_usd": getattr(result, "cost_usd", 0.0),
        })
        if result.exit_code != 0 or not result.parsed:
            e["last_error"] = (result.error or f"parse={result.parse_status}")[:200]
        if is_quota_error(result):
            hrs = float(cfg.get("cooldown_hours", 4))
            e["cooldown_until"] = (_now() + timedelta(hours=hrs)).isoformat()
        _save_usage(usage)


# ─────────────────────────── routing ────────────────────────────────────────
def _run_chain(preferred: str | None, role: str, system_prompt: str,
               user_prompt: str, timeout: int) -> LLMResult:
    cfg = load_llm_config()
    chain = model_chain(cfg)
    # Cancel fallback: only try preferred, or default to the primary model
    if preferred in VALID_MODELS:
        order = [preferred]
    else:
        order = [chain[0]] if chain else ["gemini"]

    tried: list[str] = []
    last: LLMResult | None = None
    for model in order:
        usage = _load_usage(cfg)
        avail, reason = model_available(model, cfg, usage)
        if not avail:
            tried.append(f"{model}:skip({reason})")
            continue
        result = run_llm(model, system_prompt, user_prompt, timeout=timeout)
        _record(model, result, cfg)
        if result.exit_code == 0 and result.parsed is not None:
            result.model_used = model
            result.fell_back = bool(tried)
            result.route_note = f"role={role} " + " ".join(tried + [f"{model}:ok"])
            return result
        tried.append(f"{model}:fail")
        last = result

    if last is None:
        last = LLMResult(
            agent=(order[0]), parsed=None, raw_text="", raw_stdout="",
            exit_code=-9, latency_ms=0, parse_status="failed",
            error="all models unavailable (disabled / over budget / in cooldown)")
    last.model_used = getattr(last, "agent", order[0])
    # Nothing succeeded — the caller got no substitute model, so this is a
    # failure, not a fallback. (fell_back=True here previously mislabeled
    # timed-out turns as "fell back" in the Office UI.)
    last.fell_back = False
    last.route_note = f"role={role} " + " ".join(tried) + " ALL_FAILED"
    return last


def pick_model(role: str = "protocol") -> str:
    """First available model in the chain — for spawning a long subprocess
    (e.g. an agentic protocol) where run_role's call-and-fallback doesn't fit.
    Falls back to chain[0] when every model is unavailable."""
    cfg = load_llm_config()
    chain = model_chain(cfg)
    usage = _load_usage(cfg)
    for m in chain:
        avail, _ = model_available(m, cfg, usage)
        if avail:
            return m
    return chain[0] if chain else "gemini"


def note_run(model: str, ok: bool, error_text: str = "", tokens: dict | None = None) -> None:
    """Record a protocol / long-run subprocess against `model`'s daily budget;
    trip a cooldown when `error_text` looks like a quota wall. `tokens` (parsed
    from the run's stream-json `result` event) is added to the model's daily
    token totals when supplied."""
    cfg = load_llm_config()
    with _usage_write_lock():
        usage = _load_usage(cfg)
        e = usage["models"].setdefault(
            model, {"calls": 0, "cooldown_until": None, "last_error": None})
        _stamp_call(e)
        _accumulate_tokens(e, tokens)
        if not ok:
            e["last_error"] = (error_text or "run failed")[:200]
        if error_text and _QUOTA_RE.search(error_text):
            hrs = float(cfg.get("cooldown_hours", 4))
            e["cooldown_until"] = (_now() + timedelta(hours=hrs)).isoformat()
        _save_usage(usage)


def run_role(role: str, system_prompt: str, user_prompt: str,
             timeout: int = LLM_TIMEOUT_SEC) -> LLMResult:
    """Run an LLM call for `role`, walking the fallback chain from the
    configured primary. Returns the first success, or the last failure."""
    return _run_chain(None, role, system_prompt, user_prompt, timeout)


def run_with_fallback(preferred: str, role: str, system_prompt: str,
                      user_prompt: str, timeout: int = LLM_TIMEOUT_SEC) -> LLMResult:
    """Like run_role but try `preferred` first (used by the debater so each
    turn keeps its intended model, yet still falls back when it is down)."""
    return _run_chain(preferred, role, system_prompt, user_prompt, timeout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true", help="print model status")
    ap.add_argument("--probe", metavar="ROLE", help="run a probe call for a role")
    args = ap.parse_args()
    if args.status:
        print(json.dumps(model_status(), indent=2, ensure_ascii=False))
        return 0
    if args.probe:
        r = run_role(args.probe,
                     'Reply with ONE fenced ```json``` block: {"ok":true}.',
                     "Probe.")
        print(f"model_used={getattr(r,'model_used','?')} "
              f"fell_back={getattr(r,'fell_back','?')} rc={r.exit_code} "
              f"parse={r.parse_status}")
        print(f"route_note={getattr(r,'route_note','')}")
        return 0 if (r.exit_code == 0 and r.parsed) else 1
    print("nothing to do — use --status or --probe ROLE", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
