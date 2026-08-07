#!/usr/bin/env python3
"""Hard spend ledger for the X KOL collector.

X's pay-per-use API bills **per resource returned**, not per request, so cost is
not knowable before a call completes. That makes a post-hoc counter useless as a
guard: by the time it notices, the money is gone. This module therefore does two
separate things —

  * `check(...)`  BEFORE a request: refuses unless the request's WORST case (every
    resource the request could return, at list price) still fits under the cap.
    Pessimistic on purpose; a $10 pilot cannot afford an optimistic guess.
  * `record(...)` AFTER a request: books what actually came back.

State lives in `config/x_kol_usage.json` (same convention as `config/llm_usage.json`)
and is written atomically under an flock, so parallel invocations cannot lose an
increment and interleave themselves past the ceiling.

The ledger is cumulative and never auto-resets — a pilot budget is a total, not a
daily allowance. Raise `budget.total_usd` in `config/x_kol.json` to extend it, or
run `--reset` deliberately.

Standalone:
    python3 scripts/x_kol/budget.py --status
    python3 scripts/x_kol/budget.py --reset
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from contextlib import contextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - POSIX only, same as fmp_pool
    fcntl = None

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config/x_kol.json"
USAGE_PATH = ROOT / "config/x_kol_usage.json"


class BudgetExceeded(RuntimeError):
    """Raised instead of issuing a request that could cross the ceiling."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_config(path: Path | None = None) -> dict:
    with open(path or CONFIG_PATH, encoding="utf-8") as fp:
        return json.load(fp)


def _empty_ledger() -> dict:
    return {
        "version": 1,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "post_reads": 0,
        "user_reads": 0,
        "spent_usd": 0.0,
        "requests": 0,
        "refusals": 0,
    }


def load_ledger(path: Path | None = None) -> dict:
    path = path or USAGE_PATH
    try:
        with open(path, encoding="utf-8") as fp:
            data = json.load(fp)
    except (OSError, json.JSONDecodeError):
        return _empty_ledger()
    base = _empty_ledger()
    base.update({k: v for k, v in data.items() if k in base})
    return base


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
            fp.write("\n")
        os.replace(tmp, path)
    except Exception:
        with suppress(OSError):
            os.unlink(tmp)
        raise


@contextmanager
def _locked(path: Path):
    """Serialize read-modify-write across processes. Held only for the update."""
    if fcntl is None:
        yield
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with open(lock_path, "w") as fp:
        fcntl.flock(fp, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fp, fcntl.LOCK_UN)


def spent_usd(ledger: dict, config: dict) -> float:
    prices = config["budget"]
    return round(
        ledger["post_reads"] * prices["price_per_post_read_usd"]
        + ledger["user_reads"] * prices["price_per_user_read_usd"],
        6,
    )


def remaining_usd(config: dict, *, usage_path: Path | None = None) -> float:
    ledger = load_ledger(usage_path)
    budget = config["budget"]
    cap = budget["total_usd"] - budget.get("reserve_usd", 0.0)
    return round(cap - spent_usd(ledger, config), 6)


def check(config: dict, *, posts: int = 0, users: int = 0, usage_path: Path | None = None) -> float:
    """Worst-case pre-flight. Returns projected cost; raises BudgetExceeded if it
    would cross the cap. `posts` must be the MAXIMUM the request could return."""
    prices = config["budget"]
    cost = posts * prices["price_per_post_read_usd"] + users * prices["price_per_user_read_usd"]
    left = remaining_usd(config, usage_path=usage_path)
    if cost > left:
        path = usage_path or USAGE_PATH
        with _locked(path):
            ledger = load_ledger(path)
            ledger["refusals"] += 1
            ledger["updated_at"] = _now_iso()
            _atomic_write(path, ledger)
        raise BudgetExceeded(
            f"refused: worst case ${cost:.4f} > ${left:.4f} remaining "
            f"(cap ${prices['total_usd']:.2f} − reserve ${prices.get('reserve_usd', 0.0):.2f})"
        )
    return round(cost, 6)


def record(config: dict, *, posts: int = 0, users: int = 0, usage_path: Path | None = None) -> dict:
    """Book what a completed request actually returned."""
    path = usage_path or USAGE_PATH
    with _locked(path):
        ledger = load_ledger(path)
        ledger["post_reads"] += int(posts)
        ledger["user_reads"] += int(users)
        ledger["requests"] += 1
        ledger["spent_usd"] = spent_usd(ledger, config)
        ledger["updated_at"] = _now_iso()
        _atomic_write(path, ledger)
        return ledger


def status_line(config: dict, *, usage_path: Path | None = None) -> str:
    ledger = load_ledger(usage_path)
    spent = spent_usd(ledger, config)
    cap = config["budget"]["total_usd"]
    return (
        f"[x_kol.budget] spent ${spent:.4f} / ${cap:.2f} "
        f"(remaining ${remaining_usd(config, usage_path=usage_path):.4f}) · "
        f"{ledger['post_reads']} posts · {ledger['user_reads']} users · "
        f"{ledger['requests']} requests · {ledger['refusals']} refusals"
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="X KOL spend ledger")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--reset", action="store_true", help="zero the ledger (deliberate act)")
    args = ap.parse_args(argv)
    config = load_config()
    if args.reset:
        with _locked(USAGE_PATH):
            _atomic_write(USAGE_PATH, _empty_ledger())
        print("[x_kol.budget] ledger reset")
    print(status_line(config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
