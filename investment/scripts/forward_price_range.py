#!/usr/bin/env python3
"""Ticker-facing Future Price Range CLI.

Usage:
  python3 investment/scripts/forward_price_range.py ARM
  python3 investment/scripts/forward_price_range.py ARM --json
  python3 investment/scripts/forward_price_range.py ARM --fetch

This is a thin wrapper around forward_expectations.py. It exists so a user can
input one ticker and directly see the projected future price range without
reading the full Forward Expectations JSON snapshot.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
FORWARD_ENGINE = os.path.join(SCRIPT_DIR, "forward_expectations.py")
EARNINGS_SCRIPTS_DIR = os.path.join(BASE_DIR, "skills", "earnings-analyst", "scripts")


def _redact(text: str) -> str:
    return re.sub(r"apikey=[^&\s)]+", "apikey=<redacted>", text or "")


def _missing_earnings_cache(snapshot: dict, ticker: str) -> bool:
    if snapshot.get("returncode") != 1:
        return False
    text = " ".join(str(snapshot.get(key) or "") for key in ("stdout", "stderr"))
    return f"no earnings-analyst cache for {ticker.upper()}" in text


def ensure_earnings_cache(ticker: str) -> dict | None:
    steps = [
        ("fetch", os.path.join(EARNINGS_SCRIPTS_DIR, "fetch.py")),
        ("analyze", os.path.join(EARNINGS_SCRIPTS_DIR, "analyze.py")),
        ("validate", os.path.join(EARNINGS_SCRIPTS_DIR, "validate.py")),
    ]
    logs = []
    for name, script in steps:
        proc = subprocess.run(
            [sys.executable, script, ticker.upper()],
            cwd=BASE_DIR,
            text=True,
            capture_output=True,
        )
        logs.append({
            "step": name,
            "returncode": proc.returncode,
            "stdout": _redact(proc.stdout.strip())[-2000:],
            "stderr": _redact(proc.stderr.strip())[-2000:],
        })
        if proc.returncode != 0:
            return {
                "error": "earnings_cache_bootstrap_failed",
                "ticker": ticker.upper(),
                "failed_step": name,
                "returncode": proc.returncode,
                "logs": logs,
            }
    for log in logs:
        if log["stdout"]:
            print(log["stdout"], file=sys.stderr)
        if log["stderr"]:
            print(log["stderr"], file=sys.stderr)
    return None


def extract_range(snapshot: dict) -> dict:
    price_range = snapshot.get("future_price_range") or {}
    if not price_range:
        return {
            "available": False,
            "status": "missing_future_price_range",
            "ticker": snapshot.get("ticker") or "UNKNOWN",
            "warnings": ["forward_expectations_output_missing_future_price_range"],
        }
    cases = price_range.get("cases") or {}
    rng = price_range.get("range") or {}
    return {
        "available": bool(price_range.get("available")),
        "status": price_range.get("status") or "unavailable",
        "ticker": price_range.get("ticker") or snapshot.get("ticker") or "UNKNOWN",
        "current_price": snapshot.get("current_price"),
        "horizon_date": price_range.get("horizon_date"),
        "method": price_range.get("method"),
        "multiple_quality": price_range.get("multiple_quality"),
        "compression": {
            "compressed": bool((price_range.get("multiple_range") or {}).get("compressed")),
            "growth_tier": (price_range.get("multiple_range") or {}).get("growth_tier"),
            "historical_p50": ((price_range.get("multiple_range") or {}).get("historical_band") or {}).get("p50"),
            "applied_p50": (price_range.get("multiple_range") or {}).get("p50"),
        },
        "range": {
            "bear": rng.get("low"),
            "base": rng.get("base"),
            "bull": rng.get("high"),
        },
        "upside_pct": {
            "bear": (cases.get("bear") or {}).get("upside_pct"),
            "base": (cases.get("base") or {}).get("upside_pct"),
            "bull": (cases.get("bull") or {}).get("upside_pct"),
        },
        "warnings": price_range.get("warnings") or [],
        "policy": price_range.get("policy"),
    }


def format_text(summary: dict) -> str:
    ticker = summary.get("ticker") or "UNKNOWN"
    if not summary.get("available"):
        warnings = ", ".join(summary.get("warnings") or [])
        return f"{ticker} future price range unavailable ({summary.get('status')}). {warnings}".strip()
    rng = summary.get("range") or {}
    up = summary.get("upside_pct") or {}
    advisory = summary.get("status") == "advisory_band_only"
    header = f"{ticker} Future Price Range" + (" ⚠️ ADVISORY BAND (not a forecast)" if advisory else "")
    lines = [
        header,
        f"- Current: ${summary.get('current_price')}",
        f"- Horizon: {summary.get('horizon_date')}",
        f"- Method: {summary.get('method')} ({summary.get('multiple_quality')})",
        *( [f"- Multiple: {summary['compression']['growth_tier']}-compressed "
            f"(historical P/E {summary['compression']['historical_p50']} → {summary['compression']['applied_p50']}; EXP-3.4)"]
           if (summary.get('compression') or {}).get('compressed') else [] ),
        f"- Bear: ${rng.get('bear')} ({up.get('bear'):+.1f}%)",
        f"- Base: ${rng.get('base')} ({up.get('base'):+.1f}%)",
        f"- Bull: ${rng.get('bull')} ({up.get('bull'):+.1f}%)",
    ]
    if advisory:
        lines.append(
            "- ⚠️ No price-independent multiple anchor available: this is a +/-15% band around "
            "today's price (base ≈ current), NOT a growth-driven forecast. Run with --fetch for the "
            "historical multiple regime, or supply explicit forward multiples."
        )
    if summary.get("warnings"):
        lines.append(f"- Warnings: {', '.join(summary['warnings'])}")
    lines.append("- Policy: shadow-only; does not change live fair value or decision rules.")
    return "\n".join(lines)


def run_forward_engine(ticker: str, fetch: bool = False, acquire_documents: bool = False) -> dict:
    cmd = [
        sys.executable,
        FORWARD_ENGINE,
        "--ticker",
        ticker.upper(),
        "--self-assemble",
        "--no-snapshot",
    ]
    if not fetch:
        cmd.append("--no-fetch")
    if acquire_documents:
        cmd.append("--acquire-documents")
    proc = subprocess.run(cmd, cwd=BASE_DIR, text=True, capture_output=True)
    if proc.returncode != 0:
        return {
            "error": "forward_expectations_failed",
            "returncode": proc.returncode,
            "stderr": proc.stderr.strip(),
            "stdout": proc.stdout.strip()[:500],
        }
    try:
        return json.loads(proc.stdout)
    except Exception as exc:
        return {
            "error": f"unparseable_forward_expectations_output: {exc}",
            "stderr": proc.stderr.strip(),
            "stdout": proc.stdout.strip()[:500],
        }


def main():
    ap = argparse.ArgumentParser(description="Get ticker future price range from Forward Expectations")
    ap.add_argument("ticker")
    ap.add_argument("--json", action="store_true", help="print compact JSON instead of text")
    ap.add_argument("--fetch", action="store_true", help="allow forward_expectations.py to fetch missing market data")
    ap.add_argument("--acquire-documents", action="store_true", help="opt-in SEC document acquisition in forward engine")
    args = ap.parse_args()

    snapshot = run_forward_engine(args.ticker, fetch=args.fetch, acquire_documents=args.acquire_documents)
    if _missing_earnings_cache(snapshot, args.ticker):
        bootstrap_error = ensure_earnings_cache(args.ticker)
        if bootstrap_error:
            print(json.dumps(bootstrap_error, ensure_ascii=False, indent=2, allow_nan=False) if args.json else bootstrap_error["error"])
            sys.exit(1)
        snapshot = run_forward_engine(args.ticker, fetch=args.fetch, acquire_documents=args.acquire_documents)
    if snapshot.get("error"):
        print(json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) if args.json else snapshot["error"])
        sys.exit(1)
    summary = extract_range(snapshot)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        print(format_text(summary))
    sys.exit(0 if summary.get("available") else 2)


if __name__ == "__main__":
    main()
