#!/usr/bin/env python3
"""V3.17.3 — Data alignment audit.

Cross-validates two FMP read paths for the same ticker and surfaces price /
PE / market cap divergences > 1%. Catches:
  - one skill's FMPClient holding stale cache while another fetches fresh
  - endpoint version drift (v3 vs /stable) returning different fields
  - currency / split adjustment bugs (US-only tickers shouldn't diverge)

Two paths compared (both call the same upstream FMP /stable/quote):
  PATH_A — skills/market-top-detector/scripts/fmp_client.FMPClient.quote
  PATH_B — direct requests.get to https://financialmodelingprep.com/stable/quote

Per Wave 1 plan + Codex risk discussion:
  - Soft-fail rc=0 on API errors / quota exhaustion (FMP_UNAVAILABLE) —
    audit is a measurement layer, not a release gate
  - Diff threshold default 1% (relative); breach → alert + status=ALERT
  - Original spec mentioned MCP-vs-script alignment; in practice MCP tools
    only execute inside Claude's harness so a standalone script cannot
    drive them. The two-path FMPClient-vs-REST check below is the
    pragmatic substitute that catches the same class of bugs (path-level
    inconsistency).

Usage:
    export FMP_API_KEY=...
    python3 scripts/_shared/audit_data_alignment.py
    python3 scripts/_shared/audit_data_alignment.py --tickers NVDA,AAPL,MSFT
    python3 scripts/_shared/audit_data_alignment.py --threshold 0.02
    python3 scripts/_shared/audit_data_alignment.py --output reports/alignment_<DATE>.md
    python3 scripts/_shared/audit_data_alignment.py --json
"""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests not installed", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "market-top-detector" / "scripts"))

DEFAULT_TICKERS = ["NVDA", "AAPL", "MSFT", "GOOGL", "NOK"]
DEFAULT_THRESHOLD = 0.01   # 1% relative diff
FMP_STABLE_QUOTE = "https://financialmodelingprep.com/stable/quote"


def _path_a_fmpclient(ticker: str) -> dict | None:
    """PATH_A — skills/market-top-detector/scripts/fmp_client.FMPClient.quote"""
    try:
        from fmp_client import FMPClient
    except ImportError as e:
        return {"_error": f"fmp_client import: {e}"}
    try:
        c = FMPClient()
    except ValueError as e:
        return {"_error": f"FMPClient init: {e}"}
    data = c._request_with_fallback("quote", ticker)
    if not data or not isinstance(data, list):
        return None
    q = data[0]
    return {
        "price":     q.get("price"),
        "pe":        q.get("pe"),
        "market_cap": q.get("marketCap"),
        "_path":     "fmp_client.FMPClient",
    }


def _path_b_rest_direct(ticker: str) -> dict | None:
    """PATH_B — direct requests.get to /stable/quote (parallel impl)."""
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return {"_error": "FMP_API_KEY missing"}
    try:
        r = requests.get(FMP_STABLE_QUOTE,
                         params={"symbol": ticker, "apikey": api_key},
                         timeout=30)
    except requests.RequestException as e:
        return {"_error": f"REST exception: {e}"}
    if r.status_code == 429:
        return {"_error": "REST 429 (quota exhausted)"}
    if r.status_code != 200:
        return {"_error": f"REST status {r.status_code}"}
    try:
        data = r.json()
    except ValueError:
        return {"_error": "REST JSON parse failed"}
    if not isinstance(data, list) or not data:
        return None
    q = data[0]
    return {
        "price":     q.get("price"),
        "pe":        q.get("pe"),
        "market_cap": q.get("marketCap"),
        "_path":     "REST direct",
    }


def _relative_diff(a, b) -> float | None:
    """Return abs((a-b)/avg) or None when either side missing or zero."""
    if a is None or b is None:
        return None
    try:
        a = float(a)
        b = float(b)
    except (TypeError, ValueError):
        return None
    avg = (abs(a) + abs(b)) / 2
    if avg == 0:
        return None
    return abs(a - b) / avg


def audit_one(ticker: str, threshold: float) -> dict:
    a = _path_a_fmpclient(ticker)
    b = _path_b_rest_direct(ticker)

    # Hard skip — one or both paths unavailable
    if a is None or (isinstance(a, dict) and a.get("_error")):
        return {"ticker": ticker, "status": "PATH_A_UNAVAILABLE",
                "reason": (a or {}).get("_error", "no data"),
                "path_a": a, "path_b": b}
    if b is None or (isinstance(b, dict) and b.get("_error")):
        return {"ticker": ticker, "status": "PATH_B_UNAVAILABLE",
                "reason": (b or {}).get("_error", "no data"),
                "path_a": a, "path_b": b}

    diffs = {
        "price":      _relative_diff(a["price"], b["price"]),
        "pe":         _relative_diff(a["pe"], b["pe"]),
        "market_cap": _relative_diff(a["market_cap"], b["market_cap"]),
    }
    alerted = [k for k, v in diffs.items() if v is not None and v > threshold]
    status = "ALERT" if alerted else "OK"
    return {
        "ticker":         ticker,
        "status":         status,
        "alerted_fields": alerted,
        "path_a":         a,
        "path_b":         b,
        "diffs":          diffs,
    }


def render_markdown(results: list, threshold: float) -> str:
    today = dt.date.today().isoformat()
    md = [f"# Data Alignment Audit — {today}\n",
          f"> Threshold: {threshold:.1%} relative diff "
          f"(price / PE / market_cap)",
          f"> Paths: A=`skills/market-top-detector/scripts/fmp_client.FMPClient.quote` · "
          f"B=`requests.get /stable/quote`",
          "",
          "## Summary\n",
          "| Ticker | Status | Alerted Fields | Notes |",
          "|---|---|---|---|"]
    for r in results:
        if r["status"] == "OK":
            md.append(f"| {r['ticker']} | ✅ OK | — | both paths agree within {threshold:.1%} |")
        elif r["status"] == "ALERT":
            md.append(f"| {r['ticker']} | 🔴 ALERT | {', '.join(r['alerted_fields'])} | "
                      f"path divergence > {threshold:.1%} |")
        else:
            md.append(f"| {r['ticker']} | ⚠ {r['status']} | — | {r.get('reason', '')} |")
    md.append("")
    md.append("## Per-Ticker Detail\n")
    for r in results:
        md.append(f"### {r['ticker']} — `{r['status']}`")
        if r["status"] in {"PATH_A_UNAVAILABLE", "PATH_B_UNAVAILABLE"}:
            md.append(f"- Reason: `{r.get('reason')}`")
            md.append("")
            continue
        a = r.get("path_a") or {}
        b = r.get("path_b") or {}
        d = r.get("diffs") or {}
        md.append(f"| Field | A (FMPClient) | B (REST) | Diff |")
        md.append(f"|---|---|---|---|")
        for k in ("price", "pe", "market_cap"):
            dv = d.get(k)
            dv_s = "n/a" if dv is None else f"{dv:.2%}"
            alert_icon = " 🔴" if (dv is not None and dv > threshold) else ""
            md.append(f"| {k} | {a.get(k)} | {b.get(k)} | {dv_s}{alert_icon} |")
        md.append("")
    md.append("---")
    md.append("")
    md.append("**Soft-fail policy**: rc=0 always. Acceptance is reported, "
              "not enforced. Treat ALERTs as investigation triggers, not blockers.")
    return "\n".join(md)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", default=",".join(DEFAULT_TICKERS),
                    help="comma-separated ticker list (default: 5 mega-caps)")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help=f"relative diff threshold (default {DEFAULT_THRESHOLD})")
    ap.add_argument("--output", default="",
                    help="markdown report path (default: reports/alignment_<DATE>.md)")
    ap.add_argument("--json", action="store_true",
                    help="emit JSON to stdout instead of markdown")
    args = ap.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    results = [audit_one(t, args.threshold) for t in tickers]

    n_ok = sum(1 for r in results if r["status"] == "OK")
    n_alert = sum(1 for r in results if r["status"] == "ALERT")
    n_unavail = len(results) - n_ok - n_alert

    if args.json:
        print(json.dumps({"threshold": args.threshold, "results": results,
                          "summary": {"ok": n_ok, "alert": n_alert,
                                      "unavailable": n_unavail}}, indent=2))
        return 0

    md = render_markdown(results, args.threshold)
    out_path = args.output or str(
        REPO_ROOT / "reports" / f"alignment_{dt.date.today().isoformat()}.md")
    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(md, encoding="utf-8")

    print(f"[alignment] {len(tickers)} tickers → {out_path}", file=sys.stderr)
    print(f"  ok={n_ok}  alert={n_alert}  unavailable={n_unavail}  "
          f"threshold={args.threshold:.1%}", file=sys.stderr)
    # Soft-fail policy — rc=0 even on ALERT (per Wave 1 plan)
    return 0


if __name__ == "__main__":
    sys.exit(main())
