"""Multi-model governance — role-based routing, per-model daily call budget,
quota cooldown, auto-fallback.

Every governed model call goes through `run_role()` / `run_with_fallback()`:
they walk the configured fallback chain (primary → secondary → tertiary), skip
models that are disabled / over their daily budget / in a quota cooldown, and
on a quota or hard failure transparently fall back to the next model.

Usage counters + cooldowns persist in `config/llm_usage.json` (auto-resets on
UTC date rollover).

The returned `LLMResult` is annotated with `.model_used`, `.fell_back`,
`.route_note`.

Standalone: `python3 scripts/_shared/model_router.py --status`
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

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


def _blank_usage() -> dict:
    return {
        "date": _today(),
        "models": {m: {"calls": 0, "cooldown_until": None, "last_error": None}
                   for m in VALID_MODELS},
    }


def _load_usage() -> dict:
    """Read llm_usage.json; auto-reset on UTC date rollover."""
    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            u = json.load(f)
    except (OSError, json.JSONDecodeError):
        return _blank_usage()
    if not isinstance(u, dict) or u.get("date") != _today():
        return _blank_usage()
    models = u.get("models")
    if not isinstance(models, dict):
        return _blank_usage()
    for m in VALID_MODELS:
        models.setdefault(m, {"calls": 0, "cooldown_until": None, "last_error": None})
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
    """Return (available, reason-if-not)."""
    if not cfg.get("enabled", {}).get(model, True):
        return False, "disabled"
    entry = usage["models"].get(model, {})
    if _in_cooldown(entry):
        return False, "cooldown"
    budget = cfg.get("budgets", {}).get(model, {}).get("daily_max_calls", 0)
    if budget and entry.get("calls", 0) >= budget:
        return False, "budget"
    return True, ""


def model_status() -> dict:
    """Per-model snapshot — for GET /api/llm-config."""
    cfg, usage = load_llm_config(), _load_usage()
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
        }
    return {"date": usage["date"], "chain": model_chain(cfg), "models": models}


def _record(model: str, result: LLMResult, cfg: dict) -> None:
    """Increment the call counter; trip a cooldown on a quota wall."""
    usage = _load_usage()
    e = usage["models"].setdefault(
        model, {"calls": 0, "cooldown_until": None, "last_error": None})
    e["calls"] = e.get("calls", 0) + 1
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
    if preferred in VALID_MODELS:
        order = [preferred] + [m for m in chain if m != preferred]
    else:
        order = list(chain)
    if not order:
        order = ["claude"]

    tried: list[str] = []
    last: LLMResult | None = None
    for model in order:
        usage = _load_usage()
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
    last.fell_back = bool(tried)
    last.route_note = f"role={role} " + " ".join(tried) + " ALL_FAILED"
    return last


def pick_model(role: str = "protocol") -> str:
    """First available model in the chain — for spawning a long subprocess
    (e.g. an agentic protocol) where run_role's call-and-fallback doesn't fit.
    Falls back to chain[0] when every model is unavailable."""
    cfg = load_llm_config()
    chain = model_chain(cfg)
    usage = _load_usage()
    for m in chain:
        avail, _ = model_available(m, cfg, usage)
        if avail:
            return m
    return chain[0] if chain else "claude"


def note_run(model: str, ok: bool, error_text: str = "") -> None:
    """Record a protocol / long-run subprocess against `model`'s daily budget;
    trip a cooldown when `error_text` looks like a quota wall."""
    cfg = load_llm_config()
    usage = _load_usage()
    e = usage["models"].setdefault(
        model, {"calls": 0, "cooldown_until": None, "last_error": None})
    e["calls"] = e.get("calls", 0) + 1
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
