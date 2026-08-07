#!/usr/bin/env python3
"""Sector protocol — Phase 1+3 prefetch aggregator (read-only / 0-LLM).

Collapses the sector protocol's sequential data-fetch turns into ONE parallel
subprocess sweep + a single aggregated JSON. The protocol agent reads that one
file instead of issuing ~9 separate Bash/MCP turns (each re-paying the growing
context as cache_read — the dominant sector cost; see CHANGELOG 3.44.0).

Mirrors investment/scripts/phase1_factpack.py (CHANGELOG 3.42.0): pure
aggregation over EXISTING fetch scripts — no scoring, no decision logic, no
cache mutation beyond what each underlying script already writes.

Tasks (run in parallel):
  HARD (rc!=0 → overall hard_fail=true, protocol should abort):
    valuation       fetch_sector_valuation.py        → sector/cache/sector_valuation_<D>.json
    earnings_pulse  fetch_earnings_pulse.py          → sector/cache/sector_earnings_pulse_<D>.json
    smart_money     fetch_smart_money.py             → sector/cache/sector_smart_money_<D>.json
    sector_news     fetch_sector_news.py             → sector/cache/sector_news_<D>.json
  SOFT (rc!=0 recorded, not fatal):
    general_news    fetch_general_news.py            → sector/cache/general_news_<D>.json
    sentiment       market-sentiment-analyzer        → stdout JSON (inlined)
    econ_calendar   economic-calendar-fetcher        → stdout JSON (inlined; /stable since V3.44.1)
    earnings_cal    earnings-calendar                → stdout JSON (inlined; /stable since V3.44.1)
    digest          sector_digest.py                 → stdout (inlined)

rc: 0 when no HARD task failed, 1 otherwise (so the protocol's existing
"valuation HARD FAIL → abort" contract still holds via a single check).

Usage:
  python3 sector/scripts/phase_prefetch.py --date 2026-06-10 \
          --out /tmp/sector_prefetch_2026-06-10.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable or "python3"

# Per-task subprocess wall cap. Most fetches are <30s, but fetch_smart_money
# issues ~131 sequential per-ticker insider-stat calls and, under the central
# fmp_pool RPM cap + 9-way sweep contention, can run 3-5 min — so the cap must
# clear it or the whole HARD task spuriously trips hard_fail. 360s leaves slack.
TASK_TIMEOUT_SEC = int(os.getenv("SECTOR_PREFETCH_TIMEOUT_SEC", "360"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _plus_days(d: str, n: int) -> str:
    try:
        return (date.fromisoformat(d) + timedelta(days=n)).isoformat()
    except ValueError:
        return d


def _run(cmd: list[str]) -> tuple[int, str, str]:
    """Run a subprocess; return (rc, stdout, stderr). Never raises."""
    try:
        p = subprocess.run(
            cmd, cwd=str(ROOT), capture_output=True, text=True,
            timeout=TASK_TIMEOUT_SEC, stdin=subprocess.DEVNULL, check=False,
        )
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", f"timeout after {TASK_TIMEOUT_SEC}s"
    except (OSError, ValueError) as e:
        return -2, "", f"exec error: {e}"


def _parse_json(text: str):
    """Best-effort: parse stdout as JSON, else return trimmed raw text."""
    s = (text or "").strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        start = s.find("{")
        end = s.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(s[start:end + 1])
            except json.JSONDecodeError:
                pass
    return {"_raw": s[:4000]}


def _resolve_cache(glob_pat: str) -> str | None:
    matches = sorted(ROOT.glob(glob_pat), key=lambda p: p.stat().st_mtime, reverse=True)
    return str(matches[0].relative_to(ROOT)) if matches else None


def _cache_task(name: str, cmd: list[str], glob_pat: str, hard: bool) -> tuple[str, dict]:
    rc, _out, err = _run(cmd)
    return name, {
        "kind": "cache", "hard": hard, "rc": rc,
        "cache": _resolve_cache(glob_pat),
        "error": (err.strip()[-300:] or None) if rc != 0 else None,
    }


def _stdout_task(name: str, cmd: list[str], hard: bool) -> tuple[str, dict]:
    rc, out, err = _run(cmd)
    return name, {
        "kind": "stdout", "hard": hard, "rc": rc,
        "data": _parse_json(out) if rc == 0 else None,
        "error": (err.strip()[-300:] or None) if rc != 0 else None,
    }


def build_tasks(d: str):
    d7 = _plus_days(d, 7)

    def s(script):  # sector-local script path
        return str(ROOT / "sector" / "scripts" / script)

    econ = str(ROOT / "skills/economic-calendar-fetcher/scripts/get_economic_calendar.py")
    earn = s("fetch_earnings_calendar.py")
    senti = str(ROOT / "skills/market-sentiment-analyzer/scripts/sentiment.py")

    # (fn, name, cmd, [glob_pat], hard)
    return [
        (_cache_task, "valuation",
         [PY, s("fetch_sector_valuation.py"), "--date", d],
         "sector/cache/sector_valuation_*.json", True),
        (_cache_task, "earnings_pulse",
         [PY, s("fetch_earnings_pulse.py"), "--date", d],
         "sector/cache/sector_earnings_pulse_*.json", True),
        (_cache_task, "smart_money",
         [PY, s("fetch_smart_money.py"), "--date", d],
         "sector/cache/sector_smart_money_*.json", True),
        (_cache_task, "sector_news",
         [PY, s("fetch_sector_news.py"), "--date", d, "--lookback-days", "2"],
         "sector/cache/sector_news_*.json", True),
        (_cache_task, "general_news",
         [PY, s("fetch_general_news.py"), "--date", d],
         "sector/cache/general_news_*.json", False),
        (_stdout_task, "sentiment", [PY, senti, "--json"], False),
        (_stdout_task, "econ_calendar",
         [PY, econ, "--from", d, "--to", d7, "--format", "json"], False),
        (_stdout_task, "earnings_calendar", [PY, earn, d, d7], False),
        (_stdout_task, "digest", [PY, s("sector_digest.py"), "--date", d], False),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Sector Phase 1+3 prefetch aggregator")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--out", default=None,
                    help="output JSON path (default sector/cache/phase_prefetch_<date>.json)")
    args = ap.parse_args()

    d = args.date
    out = args.out or str(ROOT / "sector" / "cache" / f"phase_prefetch_{d}.json")

    t0 = datetime.now(timezone.utc)
    tasks = build_tasks(d)
    results: dict[str, dict] = {}

    def _submit(ex, entry):
        fn, name, cmd, *extra = entry      # cache: extra=[glob, hard]; stdout: extra=[hard]
        return ex.submit(fn, name, cmd, *extra)

    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futs = [_submit(ex, entry) for entry in tasks]
        for fut in futs:
            name, payload = fut.result()
            results[name] = payload

    hard_fail = any(r.get("hard") and r.get("rc", 0) != 0 for r in results.values())
    elapsed = (datetime.now(timezone.utc) - t0).total_seconds()

    out_doc = {
        "schema": "sector_phase_prefetch/v1",
        "date": d,
        "generated_at": _now_iso(),
        "elapsed_sec": round(elapsed, 1),
        "hard_fail": hard_fail,
        "results": results,
    }

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(out_doc, f, ensure_ascii=False, indent=2)

    # Human-readable one-line summary to stderr (protocol agent reads stdout path).
    soft_fail = [n for n, r in results.items() if not r.get("hard") and r.get("rc", 0) != 0]
    sys.stderr.write(
        f"[phase_prefetch] {d} elapsed={elapsed:.0f}s hard_fail={hard_fail} "
        f"soft_fail={soft_fail or '-'} → {out}\n")
    print(out)
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
