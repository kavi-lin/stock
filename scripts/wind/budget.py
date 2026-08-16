#!/usr/bin/env python3
"""Hard spend ledger for the Wind social-scan dispatcher.

Same shape as `scripts/x_kol/budget.py`, one deliberate difference: X bills per
resource RETURNED, so its cost is unknowable before a call completes and its
`check()` has to price the request's worst case. A last30days scan bills per
SCAN — one subprocess invocation fans out across ScrapeCreators, Brave and a
reasoning provider, but the unit we buy is "one scan". So `check()` here
pre-authorizes exactly `price_per_scan_usd` and `record()` books the same
amount once the scan actually completes (a scan that fails before producing
output is not booked — we did not get the resource).

Two independent ceilings, both enforced:
  * cumulative USD  — `config/wind_usage.json`, never auto-resets
  * scans per day   — a pricing mistake cannot silently burn the cap in one day

State is written atomically under an flock, so the hourly daemon and a manual
dashboard-triggered scan cannot lose an increment and interleave past a ceiling.

Standalone:
    python3 scripts/wind/budget.py --status
    python3 scripts/wind/budget.py --reset
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
CONFIG_PATH = ROOT / "config/wind.json"
USAGE_PATH = ROOT / "config/wind_usage.json"


class BudgetExceeded(RuntimeError):
    """Raised instead of launching a scan that could cross a ceiling."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_config(path: Path | None = None) -> dict:
    with open(path or CONFIG_PATH, encoding="utf-8") as fp:
        return json.load(fp)


def _empty_ledger() -> dict:
    return {
        "version": 1,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "scans": 0,
        "spent_usd": 0.0,
        "refusals": 0,
        "day": _today(),
        "scans_today": 0,
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


def _rolled(ledger: dict) -> dict:
    """Reset the per-day counter when the UTC date advances. The cumulative USD
    total is deliberately NOT reset — a pilot budget is a total, not an allowance."""
    today = _today()
    if ledger.get("day") != today:
        ledger["day"] = today
        ledger["scans_today"] = 0
    return ledger


def spent_usd(ledger: dict, config: dict) -> float:
    return round(ledger["scans"] * config["budget"]["price_per_scan_usd"], 6)


def remaining_usd(config: dict, *, usage_path: Path | None = None) -> float:
    ledger = load_ledger(usage_path)
    budget = config["budget"]
    cap = budget["total_usd"] - budget.get("reserve_usd", 0.0)
    return round(cap - spent_usd(ledger, config), 6)


def scans_left_today(config: dict, *, usage_path: Path | None = None) -> int:
    ledger = _rolled(load_ledger(usage_path))
    cap = int(config["dispatch"]["max_scans_per_day"])
    return max(0, cap - int(ledger.get("scans_today", 0)))


def check(config: dict, *, scans: int = 1, usage_path: Path | None = None) -> float:
    """Pre-flight both ceilings. Returns the projected cost; raises BudgetExceeded
    without launching anything if either ceiling would be crossed."""
    path = usage_path or USAGE_PATH
    cost = scans * config["budget"]["price_per_scan_usd"]
    left = remaining_usd(config, usage_path=usage_path)
    day_left = scans_left_today(config, usage_path=usage_path)

    reason = None
    if cost > left:
        budget = config["budget"]
        reason = (
            f"worst case ${cost:.4f} > ${left:.4f} remaining "
            f"(cap ${budget['total_usd']:.2f} − reserve ${budget.get('reserve_usd', 0.0):.2f})"
        )
    elif scans > day_left:
        reason = (
            f"{scans} scan(s) > {day_left} left today "
            f"(max_scans_per_day {config['dispatch']['max_scans_per_day']})"
        )
    if reason:
        with _locked(path):
            ledger = _rolled(load_ledger(path))
            ledger["refusals"] += 1
            ledger["updated_at"] = _now_iso()
            _atomic_write(path, ledger)
        raise BudgetExceeded(f"refused: {reason}")
    return round(cost, 6)


def record(config: dict, *, scans: int = 1, usage_path: Path | None = None) -> dict:
    """Book scans that actually completed and produced output."""
    path = usage_path or USAGE_PATH
    with _locked(path):
        ledger = _rolled(load_ledger(path))
        ledger["scans"] += int(scans)
        ledger["scans_today"] = int(ledger.get("scans_today", 0)) + int(scans)
        ledger["spent_usd"] = spent_usd(ledger, config)
        ledger["updated_at"] = _now_iso()
        _atomic_write(path, ledger)
        return ledger


def status_line(config: dict, *, usage_path: Path | None = None) -> str:
    ledger = _rolled(load_ledger(usage_path))
    spent = spent_usd(ledger, config)
    cap = config["budget"]["total_usd"]
    return (
        f"[wind.budget] spent ${spent:.4f} / ${cap:.2f} "
        f"(remaining ${remaining_usd(config, usage_path=usage_path):.4f}) · "
        f"{ledger['scans']} scans · {ledger['scans_today']}/"
        f"{config['dispatch']['max_scans_per_day']} today · "
        f"{ledger['refusals']} refusals"
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Wind social-scan spend ledger")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--reset", action="store_true", help="zero the ledger (deliberate act)")
    args = ap.parse_args(argv)
    config = load_config()
    if args.reset:
        with _locked(USAGE_PATH):
            _atomic_write(USAGE_PATH, _empty_ledger())
        print("[wind.budget] ledger reset")
    print(status_line(config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
