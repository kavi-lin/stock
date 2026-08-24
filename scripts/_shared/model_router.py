"""Broker-only routing for every LLM inference in this repository.

The task registry defines which providers are certified for each capability.
The quota broker chooses among that certified set and owns the only execution
reservation.  If the registry, broker, or certification is unavailable, the
call does not run.  Local usage counters remain telemetry only.

`run_role()` lets the broker choose. `run_with_fallback()` is retained as a
compatibility name for ensemble code, but pins the already broker-selected
voice and never substitutes another model after inference starts.
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

from scripts._shared import broker_gate, llm_task_registry  # noqa: E402
from scripts.break_news import llm_drivers  # noqa: E402
from scripts._shared.broker_gate import (  # noqa: E402
    BrokerError, BrokerRefused, BrokerUnavailable,
)
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

# Text-only roles must not inherit Claude Code's agentic runtime. A bare
# `claude -p` loads tools/MCP and may start exploring even when the contract asks
# for one JSON object; the Nexus trial hit its 240s hard wall on exactly that
# path. Keep this policy next to the shared dispatcher so broker governance and
# token settlement still wrap the call.
_CLAUDE_TEXT_ONLY_PROFILES = {
    "nexus_gap_fill": {
        "model": "sonnet",
        "max_turns": 1,
        "strict_mcp": True,
        "no_tools": True,
    },
    "office": {
        "model": "sonnet",
        "max_turns": 1,
        "strict_mcp": True,
        "no_tools": True,
    },
    "office_verdict": {
        "model": "opus",
        "max_turns": 1,
        "strict_mcp": True,
        "no_tools": True,
    },
}


def _run_model_for_role(
    model: str, role: str, system_prompt: str, user_prompt: str, timeout: int,
    provider_model: str = "", lease=None,
) -> LLMResult:
    """Run one call. `provider_model` is the broker's assigned vendor model id.

    Empty for every provider whose quota is one pool; for agy it is what makes
    the reservation true, because that CLI's Gemini and Claude/GPT models draw
    on windows that refill independently (see `run_gemini`).
    """
    profile = _CLAUDE_TEXT_ONLY_PROFILES.get(role) if model == "claude" else None
    if profile:
        return llm_drivers.run_claude(
            system_prompt,
            user_prompt,
            timeout=timeout,
            process_callback=(lease.attach_process if lease is not None else None),
            **profile,
        )
    return run_llm(model, system_prompt, user_prompt, timeout=timeout,
                   provider_model=provider_model,
                   process_callback=(lease.attach_process if lease is not None else None))


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
    """Local telemetry availability retained for status/backward compatibility.

    This function never authorises inference. Only a broker lease can do that.
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
    return {
        "date": usage["date"],
        "chain": model_chain(cfg),
        "models": models,
        "broker": broker_status(cfg),
    }


def broker_status(cfg: dict | None = None) -> dict:
    """The quota authority's live state — for `--status` and the sidebar.

    Reported alongside local telemetry counters rather than replacing them.
    Those counters never authorise inference.

    `providers` carries live remaining quota per model; `routes` says which model
    each dispatch path will actually use. Those two together are what the sidebar
    shows now that it no longer offers a choice — the broker only ever assigns a
    certified provider with quota.
    """
    cfg = cfg if isinstance(cfg, dict) else load_llm_config()
    settings = broker_gate.broker_config(cfg)
    state = {
        "enabled": settings["enabled"],
        "authority": False,
        "reachable": None,
        "client_version": broker_gate.CLIENT_BROKER_VERSION,
        "broker_version": None,
        "handshake_status": "disabled" if not settings["enabled"] else "unknown",
        "restart_required": False,
        "degradable_roles": list(settings["degradable_roles"]),
        "error": None,
        "providers": {},
        "active_reservations": [],
        "routes": routes(cfg),
    }
    if not settings["enabled"]:
        return state
    client = broker_gate.broker_client(cfg)
    state["base_url"] = getattr(client, "base_url", None)
    try:
        handshake = client.handshake()
    except BrokerError as exc:
        state["reachable"] = False
        state["handshake_status"] = "unreachable"
        state["restart_required"] = True
        state["error"] = str(exc)[:300]
        return state

    state["reachable"] = True
    state["broker_version"] = handshake.broker_version
    state["handshake_status"] = handshake.status
    state["restart_required"] = handshake.restart_required
    if not handshake.compatible:
        state["error"] = handshake.message[:300]
        return state

    try:
        snapshot = broker_gate.quota_snapshot(cfg)
    except BrokerError as exc:
        state["handshake_status"] = "broker_error"
        state["error"] = str(exc)[:300]
        return state
    state["authority"] = True
    state["providers"] = snapshot["providers"]
    state["active_reservations"] = snapshot.get("active_reservations") or []
    state["hard_reserve_percent"] = snapshot["hard_reserve_percent"]
    return state


def routes(cfg: dict | None = None) -> list[dict]:
    """Describe dispatch ownership without creating preview decisions."""
    cfg = cfg if isinstance(cfg, dict) else load_llm_config()
    governed = list(llm_task_registry.official_models())
    return [
        {"key": "general", "model": None, "decided_by": "broker",
         "picks": 1, "eligible": governed},
        {"key": "debate", "model": None, "decided_by": "broker", "picks": 2,
         "eligible": governed},
        {"key": "protocol", "model": None, "decided_by": "broker", "picks": 1,
         "eligible": governed},
    ]


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


# ──────────────────────── broker gate (V4.106.0) ────────────────────────────
class RunBlocked(RuntimeError):
    """The quota broker did not authorise this call. Carries the operator-facing why."""


class ProtocolBlocked(RunBlocked):
    """`RunBlocked` for the agentic protocol path, named for clearer tracebacks."""


def _task_type(role: str) -> str:
    """Role name → a ledger task type the broker's schema accepts.

    One sanitiser for both paths, in `broker_gate`, next to the pattern it
    enforces. Two copies is how V4.110.0 shipped a protocol task type with a
    colon in it: this path cleaned its names and the protocol path did not.
    """
    return broker_gate.sanitize_task_type(role, default="call")


def _blocked_reason(note: str) -> str:
    """Why a run was not authorised, in the operator's terms, from `note`.

    These three notes mean three unrelated things and only one of them is about
    quota. Until V4.111.4 they shared one sentence that named the other two
    causes ("the daemon may be down, or every provider is inside its 20% hard
    reserve"), so a malformed request — a bug in this repo — sent the operator to
    `lqb status`, which showed a healthy daemon with quota to spare.
    """
    if "provider_busy" in note:
        return ("all eligible provider execution slots are busy. The queue will "
                "retry when a broker-owned slot is released.")
    if note.startswith("broker:refused"):
        return ("no provider has quota outside its hard reserve. `lqb status` "
                "shows what is left in each pool and when it refills.")
    if note.startswith("broker:unavailable"):
        return ("the broker could not be reached — check the daemon is up "
                "(`lqb status`). Broker-only mode stops every LLM task.")
    if note.startswith("broker:rejected"):
        return ("the broker rejected the request itself. That is a bug in this "
                "repo, not a quota state — the daemon's reason is on stderr above, "
                "and no amount of waiting will clear it.")
    if note.startswith("broker:version"):
        return ("the broker and this client are different releases. Restart the "
                "broker from the Dashboard, then retry after the handshake matches.")
    if note.startswith("broker:not-allowed"):
        return ("this protocol is restricted to providers listed under "
                "`protocol_providers` in config/llm_config.json, and none of them "
                "is enabled with capacity right now. This is a portability limit, "
                "not a quota state — waiting only helps if the listed provider "
                "refills.")
    if note.startswith("broker:not-certified"):
        return ("this task has no enabled, certified broker provider. Complete "
                "the capability canary or fix its registry entry before retrying.")
    if note.startswith("broker:unregistered"):
        return ("this LLM task is missing from config/llm_task_registry.json. "
                "Register and certify it before any inference can run.")
    if note.startswith("broker:off"):
        return ("broker-only mode is enabled for this project, but the broker "
                "client is disabled. Enable/restart llm-quota-broker before retrying.")
    return "see the note above."


def protocol_provider_allowlist(cfg: dict | None = None,
                                protocol: str | None = None) -> list[str] | None:
    """Models this protocol may run on. `None` means unrestricted.

    Protocols are not equally portable. `triage` and `news` name every script
    path inline and ran clean on agy; `invest` and `sector` fan out to parallel
    lane subagents and assume Claude-shaped semantics end to end. Treating those
    as interchangeable is what happened on 2026-08-09: the broker sent an
    `invest` run to agy — the first non-Claude invest run ever — and it spent
    208K tokens searching the filesystem for a protocol it never found.

    Config is `protocol_providers` in `config/llm_config.json`. A missing key
    falls back to `_default`; a missing `_default` means unrestricted.

    An empty list comes back for a present-but-unusable value (empty, malformed,
    or naming only models this repo does not have). That is deliberately NOT
    read as "unrestricted": a typo in the allowlist for `invest` must fail loudly
    rather than silently reopen the door this function exists to close.
    """
    cfg = cfg if cfg is not None else load_llm_config()
    table = cfg.get("protocol_providers")
    if not isinstance(table, dict) or not protocol:
        return None
    if protocol in table:
        allowed = table[protocol]
    elif "_default" in table:
        allowed = table["_default"]
    else:
        return None
    if allowed is None:
        return None
    if not isinstance(allowed, list):
        sys.stderr.write(
            f"[model_router] protocol_providers[{protocol}] is not a list; "
            f"blocking rather than assuming unrestricted\n")
        return []
    return [m for m in allowed if m in VALID_MODELS]


def _acquire(role: str, model: str | None, cfg: dict, *,
             prompts: tuple[str, ...] = (), protocol: bool = False,
             protocol_name: str | None = None, pinned: bool = False,
             certification: bool = False):
    """Reserve the only authorisation that may start an LLM process.

    Normal calls offer every certified provider to the broker.  Ensemble turns
    and explicit certification probes may pin one provider, but are still
    refused unless that provider is broker-governed.  There is no unleased
    success state: `(None, note, True)` is intentionally impossible.
    """
    task_id = (llm_task_registry.protocol_task_id(protocol_name)
               if protocol else str(role or "").strip().lower())
    try:
        task = llm_task_registry.task_definition(task_id)
        certified = (llm_task_registry.official_models() if certification
                     else llm_task_registry.certified_models(task_id))
    except llm_task_registry.TaskRegistryError as exc:
        sys.stderr.write(f"[broker] {role}: task registry blocked the call ({exc})\n")
        return None, "broker:unregistered", False

    enabled = cfg.get("enabled") or {}
    candidates = [candidate for candidate in certified
                  if enabled.get(candidate, True) and broker_gate.provider_for(candidate)]
    if protocol:
        allow = protocol_provider_allowlist(cfg, protocol_name)
        if allow is not None:
            candidates = [candidate for candidate in candidates if candidate in allow]
    if pinned:
        candidates = [candidate for candidate in candidates if candidate == model]
    if not candidates:
        return None, f"broker:not-certified({task_id})", False

    acceptable = [broker_gate.provider_for(candidate) for candidate in candidates]
    acceptable = [provider for provider in acceptable if provider]
    forbidden = [provider for provider in broker_gate.PROVIDER_FOR_MODEL.values()
                 if provider not in set(acceptable)]
    if protocol:
        estimated_input, estimated_output = broker_gate.protocol_estimate(cfg, protocol_name)
        ttl = broker_gate.PROTOCOL_TTL_SECONDS
    else:
        estimated_input, estimated_output = llm_task_registry.token_estimate(
            task_id, sum(len(prompt) for prompt in prompts))
        ttl = broker_gate.SINGLE_CALL_TTL_SECONDS

    client = broker_gate.broker_client(cfg)
    if client is None:
        return None, "broker:off", False

    try:
        lease = client.acquire(
            task_id=broker_gate.new_task_id(role),
            task_type=_task_type(task_id),
            estimated_input_tokens=estimated_input,
            estimated_output_tokens=estimated_output,
            requires_web=bool(task.get("requires_web")),
            preferred_providers=acceptable,
            forbidden_providers=forbidden,
            reservation_ttl_seconds=ttl,
        )
    except BrokerRefused as exc:
        # The broker answered. Never degrade from this: the answer is that the
        # quota it would take is inside the hard reserve.
        return None, f"broker:refused({exc.code})", False
    except BrokerUnavailable as exc:
        sys.stderr.write(f"[broker] {role}: unavailable ({exc}); not running (fail-closed)\n")
        return None, "broker:unavailable", False
    except broker_gate.BrokerVersionMismatch as exc:
        sys.stderr.write(f"[broker] {role}: version mismatch ({exc}); not running\n")
        return None, f"broker:version({exc.status})", False
    except BrokerError as exc:
        # A malformed request is this repo's bug. Degrading would hide it behind
        # months of quietly ungoverned spending.
        sys.stderr.write(f"[broker] {role}: request rejected ({exc}); not running\n")
        return None, "broker:rejected", False

    # Open the execution row *before* the call rather than letting `complete()`
    # do it on the way out. The client opens one either way, so skipping this
    # does not lose the settlement — it loses the duration: `started_at` lands
    # microseconds before `finished_at`, and `execution_stats` derives
    # `p50_duration_seconds` from exactly that difference. Every governed call
    # was reporting itself as instantaneous, which pins the broker's latency
    # score at its maximum for whoever it is scoring and leaves the component
    # unable to tell a fast provider from a slow one. Found in the Phase 7 live
    # smoke test: runs dispatched through `/v1/run` recorded 6-10s while these
    # recorded 0.003-0.010s.
    #
    # `start()` also records the model, and it is the only request that carries
    # it — so it must be the model that will actually run, which is the broker's
    # assigned provider, not the one we asked for.
    #
    # V4.129.0 — the broker's own assignment wins over this repo's alias where
    # there is one. `MODEL_FOR_PROVIDER` yields "gemini", which names a runner
    # here and nothing at the vendor; the ledger uses what it records to
    # calibrate each pool's burn rate, and an alias is not a pool.
    try:
        assigned = broker_gate.MODEL_FOR_PROVIDER.get(lease.provider, model or "")
        lease.start(model=(broker_gate.assigned_model(lease) or assigned))
    except BrokerError as exc:
        # The hold is real and the call may proceed; only the timing is lost.
        sys.stderr.write(f"[broker] {role}: could not open the execution row ({exc})\n")
    return lease, f"broker:{lease.provider}", True


def _settle(lease, model: str, result: LLMResult, *, accepts_text: bool = False) -> None:
    """Report a finished call to the broker. Never raises into the caller.

    A settlement that cannot be delivered leaves the hold to expire at its TTL.
    That is a worse outcome than settling — until it expires, the other project
    sees less headroom than really exists — but it is not a reason to fail a call
    whose answer is already in hand.
    """
    if lease is None:
        return
    error_class = None
    has_answer = result.parsed is not None or (
        accepts_text and bool((result.raw_text or result.raw_stdout or "").strip()))
    if result.exit_code != 0 or not has_answer:
        if is_quota_error(result):
            error_class = "quota"
        elif "timeout" in (result.error or "").lower():
            error_class = "timeout"
        elif result.exit_code != 0:
            error_class = "transient"
        else:
            # Ran fine, produced nothing parseable.
            error_class = "invalid_output"
    try:
        lease.complete(
            usage=broker_gate.usage_for_broker({
                "input_tokens": getattr(result, "input_tokens", 0),
                "output_tokens": getattr(result, "output_tokens", 0),
                "cache_read_tokens": getattr(result, "cache_read_tokens", 0),
                "cache_write_tokens": getattr(result, "cache_write_tokens", 0),
            }),
            exit_code=result.exit_code,
            error_class=error_class,
            error_detail=(result.error or "")[:2000] or None,
            model=model,
        )
    except BrokerError as exc:
        sys.stderr.write(f"[broker] settle failed for {model}: {exc}\n")


def _release(lease, reason: str) -> None:
    """Drop a hold for a call that never ran. Best-effort, same reasoning as above."""
    if lease is None:
        return
    try:
        lease.cancel(reason)
    except BrokerError as exc:
        sys.stderr.write(f"[broker] cancel failed: {exc}\n")


class _Hold:
    """A reservation handed to a caller that runs the CLI itself."""

    def __init__(self, lease, model: str, note: str) -> None:
        self.lease = lease
        self.model = model
        self.note = note
        #: Vendor-native model the broker assigned, or `""`. A caller driving
        #: agy must pass this as `--model`: the hold is against one of that
        #: CLI's two quota pools and only the model decides which one is spent.
        self.provider_model = broker_gate.assigned_model(lease)

    def settle(self, result: LLMResult) -> None:
        """Report the finished call. Safe to call once; ignored afterwards."""
        _settle(self.lease, self.model, result)
        self.lease = None

    def attach_process(self, pid: int, pgid: int) -> None:
        if self.lease is not None:
            self.lease.attach_process(pid, pgid)


@contextlib.contextmanager
def governed_call(role: str, model: str, *prompts: str):
    """Reserve a broker-pinned lease for a specialized low-level adapter.

    New ordinary call sites should use :func:`run_role`. This context manager
    exists only when an adapter must drive a provider-specific process itself::

        with governed_call("office", "claude", system_prompt, user_prompt) as hold:
            result = llm_drivers.run_claude(...)
            hold.settle(result)

    `hold.provider_model` carries the model the broker assigned; a site driving
    agy has to pass it as `--model`, or the hold and the spend land in different
    quota pools. Empty for every other provider, so it is safe to pass on
    unconditionally.

    Raises :class:`RunBlocked` when the call must not happen. An unsettled hold
    is cancelled on the way out, so no path leaks one.
    """
    cfg = load_llm_config()
    lease, note, allowed = _acquire(role, model, cfg, prompts=prompts, pinned=True)
    if not allowed:
        raise RunBlocked(f"the quota broker did not authorise this {role} call "
                         f"({note}): {_blocked_reason(note)}")
    assigned = broker_gate.MODEL_FOR_PROVIDER.get(lease.provider, model)
    hold = _Hold(lease, assigned, note)
    try:
        yield hold
    finally:
        _release(hold.lease, "caller did not settle")


# ─────────────────────────── routing ────────────────────────────────────────
def _run_chain(preferred: str | None, role: str, system_prompt: str,
               user_prompt: str, timeout: int, *,
               certification: bool = False) -> LLMResult:
    cfg = load_llm_config()
    pinned = preferred in VALID_MODELS
    lease, broker_note, allowed = _acquire(
        role, preferred if pinned else None, cfg,
        prompts=(system_prompt, user_prompt), pinned=pinned,
        certification=certification,
    )
    if not allowed or lease is None:
        requested = preferred if pinned else "broker"
        result = LLMResult(
            agent=requested, parsed=None, raw_text="", raw_stdout="",
            exit_code=-9, latency_ms=0, parse_status="blocked",
            error=f"LLM call blocked ({broker_note}): {_blocked_reason(broker_note)}",
        )
        result.model_used = ""
        result.fell_back = False
        result.route_note = f"role={role} blocked({broker_note})"
        return result

    model = broker_gate.MODEL_FOR_PROVIDER.get(lease.provider)
    if not model:
        _release(lease, f"broker assigned unsupported provider {lease.provider}")
        result = LLMResult(
            agent=str(lease.provider), parsed=None, raw_text="", raw_stdout="",
            exit_code=-9, latency_ms=0, parse_status="blocked",
            error=f"broker assigned unsupported provider {lease.provider}",
        )
        result.model_used = ""
        result.fell_back = False
        result.route_note = f"role={role} blocked(unsupported-provider)"
        return result
    try:
        result = _run_model_for_role(
            model, role, system_prompt, user_prompt, timeout,
            provider_model=broker_gate.assigned_model(lease), lease=lease,
        )
    except BaseException:
        _release(lease, "the call raised before producing a result")
        raise
    _record(model, result, cfg)
    task = llm_task_registry.task_definition(role)
    accepts_text = task.get("response_format") == "text"
    _settle(lease, model, result, accepts_text=accepts_text)
    result.model_used = model
    result.fell_back = False
    has_answer = result.parsed is not None or (
        accepts_text and bool((result.raw_text or result.raw_stdout or "").strip()))
    outcome = "ok" if result.exit_code == 0 and has_answer else "fail"
    result.route_note = f"role={role} {model}:{outcome}({broker_note})"
    return result


def pick_model(role: str = "protocol", allow: list[str] | None = None) -> str:
    """First locally-available model in the chain. Takes NO broker reservation.

    Selection only — kept for callers that want to know which provider would be
    chosen without committing to spend. A long subprocess must use
    :func:`acquire_protocol_lease` instead, which reserves the quota it is about
    to spend and can refuse.

    `allow` restricts the answer to a protocol's allowlist. When no chain member
    is on that list the allowlist supplies the order itself, because it names
    what can run and the chain only names what is preferred.
    """
    cfg = load_llm_config()
    chain = model_chain(cfg)
    if allow is not None:
        chain = [m for m in chain if m in allow] or list(allow)
    usage = _load_usage(cfg)
    for m in chain:
        avail, _ = model_available(m, cfg, usage)
        if avail:
            return m
    return chain[0] if chain else "gemini"


def acquire_protocol_lease(role: str = "agentic_protocol",
                           protocol: str | None = None,
                           pinned_model: str | None = None) -> tuple[str, object, str]:
    """Reserve quota for one agentic protocol run: returns (model, lease, note).

    `protocol` is required and resolves an exact registry task. The broker
    chooses from that task's certified provider set and returns the only lease
    permitted to launch the subprocess. Any registry/broker failure raises
    :class:`ProtocolBlocked` before inference starts.

    `pinned_model` is for explicit capability certification only. Normal
    protocol launches leave it empty and the broker selects the provider.
    """
    cfg = load_llm_config()
    if not protocol:
        raise ProtocolBlocked("protocol name is required for a broker reservation")
    allow = protocol_provider_allowlist(cfg, protocol)
    if allow is not None and not allow:
        raise ProtocolBlocked(
            f"protocol_providers[{protocol}] in config/llm_config.json lists no "
            f"model this repo can run. Fix the allowlist — an empty one is read "
            f"as a mistake, not as permission to use any provider.")
    if pinned_model is not None and pinned_model not in VALID_MODELS:
        raise ProtocolBlocked(f"unknown pinned model: {pinned_model}")
    lease, note, allowed = _acquire(
        role, pinned_model, cfg, protocol=True, protocol_name=protocol,
        pinned=pinned_model is not None,
    )
    if not allowed or lease is None:
        raise ProtocolBlocked(
            f"the quota broker did not authorise this run ({note}): {_blocked_reason(note)}")
    model = broker_gate.MODEL_FOR_PROVIDER.get(lease.provider)
    if not model:
        _release(lease, f"broker assigned unsupported provider {lease.provider}")
        raise ProtocolBlocked(f"broker assigned unsupported provider: {lease.provider}")
    return model, lease, note


def note_run(model: str, ok: bool, error_text: str = "", tokens: dict | None = None,
             lease: object | None = None) -> None:
    """Record a protocol / long-run subprocess and settle its broker reservation.

    The local counters are updated as telemetry only. When
    `lease` is supplied (from :func:`acquire_protocol_lease`) the hold is settled
    with the tokens the run actually reported, releasing the difference between
    the estimate and reality.
    """
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

    if lease is None:
        return
    error_class = None
    if not ok:
        # Only a real quota wall may say `quota`: the broker puts the provider
        # into cooldown on that word, so a mislabelled timeout would sideline a
        # healthy provider for hours.
        if error_text and _QUOTA_RE.search(error_text):
            error_class = "quota"
        elif "timeout" in (error_text or "").lower():
            error_class = "timeout"
        else:
            error_class = "transient"
    try:
        lease.complete(
            usage=broker_gate.usage_for_broker(tokens),
            exit_code=0 if ok else 1,
            error_class=error_class,
            error_detail=(error_text or "")[:2000] or None,
            model=model,
        )
    except BrokerError as exc:
        sys.stderr.write(f"[broker] settle failed for protocol run on {model}: {exc}\n")


def run_role(role: str, system_prompt: str, user_prompt: str,
             timeout: int = LLM_TIMEOUT_SEC) -> LLMResult:
    """Let the broker choose one certified provider and run exactly once."""
    return _run_chain(None, role, system_prompt, user_prompt, timeout)


def run_with_fallback(preferred: str, role: str, system_prompt: str,
                      user_prompt: str, timeout: int = LLM_TIMEOUT_SEC) -> LLMResult:
    """Run one broker-authorised call pinned to an already selected provider.

    The compatibility name remains because ensemble call sites use it. It does
    not start a second inference on another provider after failure.
    """
    return _run_chain(preferred, role, system_prompt, user_prompt, timeout)


def run_certification_probe(provider: str, role: str, system_prompt: str,
                            user_prompt: str,
                            timeout: int = LLM_TIMEOUT_SEC) -> LLMResult:
    """Run one isolated, broker-pinned canary before enabling a task provider."""
    if provider not in llm_task_registry.official_models():
        raise ValueError(f"not an official broker provider: {provider}")
    return _run_chain(provider, role, system_prompt, user_prompt, timeout,
                      certification=True)


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
