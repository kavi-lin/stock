"""Collect deterministic inputs; unavailable optional data is an explicit receipt."""
from concurrent.futures import ThreadPoolExecutor
import json
import argparse
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time

from run_data import ROOT, atomic_json, digest, read_json, utcnow


def commands(ticker):
    return {
        "fundamentals": ["skills/us-stock-analysis/scripts/analyze.py", ticker, "--json-only"],
        "sentiment": ["skills/market-sentiment-analyzer/scripts/sentiment.py", "--ticker", ticker, "--json-only"],
        "news": ["skills/market-news-analyst/scripts/fetch.py", ticker, "--hours", "48", "--json-only"],
        "technical": ["skills/technical-analyst/scripts/analyze.py", ticker, "--json-only"],
        "dcf": ["skills/valuation-modeler/scripts/dcf.py", ticker, "--json-only"],
        "comps": ["skills/valuation-modeler/scripts/comps.py", ticker, "--json-only"],
        "forecaster": ["skills/earnings-valuation-forecaster/scripts/forecast.py", ticker, "--json-only"],
    }


def worker(name, ticker, period, receipt_path):
    sys.path.insert(0, str(ROOT))
    from skills._shared.investment_data import SourceCache, source_context
    cache = SourceCache(ROOT / "skills/earnings-analyst/cache/sources", period=period)
    args = commands(ticker)[name]
    sys.path.insert(0, str((ROOT / args[0]).parent))
    sys.argv = args
    os.environ["AIC_INVESTMENT_PERIOD"] = period
    try:
        with source_context(cache):
            runpy.run_path(str(ROOT / args[0]), run_name="__main__")
    finally:
        atomic_json(receipt_path, {"source_records": cache.sources, "source_telemetry": cache.metrics})


def collect(ticker, directory, *, period):

    def execute(item):
        name, args = item
        started, clock = utcnow(), time.monotonic()
        payload, rc, reason = None, None, None
        source_path = directory / "raw" / f"{name}.sources.json"
        argv = [sys.executable, str(Path(__file__).resolve()), "--worker", name,
                "--ticker", ticker, "--period", period, "--sources-out", str(source_path)]
        try:
            result = subprocess.run(argv, cwd=ROOT, capture_output=True,
                                    text=True, timeout=600)
            rc = result.returncode
            try:
                payload = json.loads(result.stdout)
                digest(payload)  # reject NaN / Infinity as invalid source data
            except (ValueError, TypeError):
                payload, reason = None, "script did not return finite JSON"
            if isinstance(payload, dict) and payload.get("status") in {"error", "unavailable", "missing"}:
                reason = payload.get("reason") or payload.get("error") or "source unavailable"
            if rc and not reason:
                reason = f"script exited with rc={rc}"
        except subprocess.TimeoutExpired:
            reason = "script exceeded 600 second timeout"
        receipt = {"command": args, "started_at": started, "finished_at": utcnow(),
                   "elapsed_seconds": time.monotonic() - clock, "returncode": rc,
                   "status": "unavailable" if reason else "ok", "reason": reason,
                   "content_hash": digest(payload)}
        if source_path.exists():
            receipt.update(read_json(source_path))
        # Receipt clocks measure execution, never replace upstream source clocks.
        atomic_json(directory / "raw" / f"{name}.json", payload)
        atomic_json(directory / "raw" / f"{name}.receipt.json", receipt)
        return name, payload, receipt

    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(execute, commands(ticker).items()))
    return {n: p for n, p, _ in rows}, {n: r for n, _, r in rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=list(commands("T")), required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--period", required=True)
    parser.add_argument("--sources-out", type=Path, required=True)
    args = parser.parse_args()
    worker(args.worker, args.ticker, args.period, args.sources_out)
