#!/usr/bin/env python3
"""V3.22 — prefetch quarterly income for the momentum screener universe.

Walks the same universe files screen.py uses (sp500 + nasdaq100 + sox, ≈532
unique tickers) and primes the shared 7-day quarterly-income cache so the
next `momentum_screen.py` run is fully cache-hot. Intended to be called
from daily_update.sh as a non-fatal step — missing FMP_API_KEY exits 0
quietly so cron pipelines on machines without the key keep running.

Output is intentionally terse: one progress line per 50 tickers, final
summary with hit/miss counts. Failures on individual tickers (paid blocker,
network) collapse to None inside the helper, so this script can never raise.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
UNIVERSE_DIR = os.path.join(SCRIPT_DIR, "universes")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _load_universe(name: str) -> list[str]:
    path = os.path.join(UNIVERSE_DIR, f"{name}.txt")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fp:
        return [ln.strip().upper() for ln in fp if ln.strip() and not ln.startswith("#")]


def main() -> int:
    ap = argparse.ArgumentParser(description="Prefetch quarterly income (7d cache)")
    ap.add_argument("--universes", default="sp500,nasdaq100,sox",
                    help="Comma-separated universe names under scripts/universes/")
    ap.add_argument("--limit", type=int, default=8,
                    help="Quarterly rows per ticker (8 = 2 years; enough for TTM YoY)")
    ap.add_argument("--max-tickers", type=int, default=None,
                    help="Optional cap (debugging / partial backfill)")
    args = ap.parse_args()

    if not os.environ.get("FMP_API_KEY"):
        print("[prefetch_fundamentals] FMP_API_KEY not set — skipping (non-fatal)")
        return 0

    # Imported lazily so a missing FMP key (handled above) doesn't trigger
    # the sys.exit inside company_context's _fmp_get.
    from skills._shared.company_context import get_quarterly_income

    tickers = sorted({
        t for name in args.universes.split(",") for t in _load_universe(name.strip()) if t
    })
    if args.max_tickers:
        tickers = tickers[: args.max_tickers]

    if not tickers:
        print("[prefetch_fundamentals] empty universe — nothing to prefetch")
        return 0

    print(f"[prefetch_fundamentals] {len(tickers)} tickers across {args.universes}")
    t0 = time.time()
    ok = miss = 0
    for i, t in enumerate(tickers, 1):
        rows = get_quarterly_income(t, n=args.limit) or []
        if rows:
            ok += 1
        else:
            miss += 1
        if i % 50 == 0 or i == len(tickers):
            print(f"[prefetch_fundamentals] {i}/{len(tickers)} "
                  f"(ok={ok}, miss={miss}, elapsed={int(time.time() - t0)}s)")
    print(f"[prefetch_fundamentals] done — ok={ok}, miss={miss}, "
          f"elapsed={int(time.time() - t0)}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
