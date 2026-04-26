#!/usr/bin/env python3
"""
Finnhub vs FMP side-by-side diff tool.

For each ticker, fetches the same canonical fields from both providers,
computes per-field percentage delta, and grades:

  PASS  <2% diff (acceptable noise)
  WARN  2-5%   (investigate before relying on this field)
  FAIL  >5%    (do not migrate this field without reconciliation)
  N/A   one side missing the value

Usage:
  python3 diff_tool.py --tickers AAPL,MSFT,SPY
  python3 diff_tool.py --tickers AAPL --output /tmp/diff.md
  python3 diff_tool.py --no-cache    # force live calls

Requires:
  FINNHUB_API_KEY  — for Finnhub
  FMP_API_KEY      — for Financial Modeling Prep
"""
import os
import sys
import json
import argparse
import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests library not found. pip install requests", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from finnhub_client import FinnhubClient, FinnhubError, FinnhubPremiumRequired
import adapters

DEFAULT_TICKERS = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMD",
    "META", "JPM", "XOM", "SPY", "QQQ",
]
REPORT_DIR = Path(__file__).resolve().parent.parent / "diff_reports"

WARN_THRESHOLD = 2.0
FAIL_THRESHOLD = 5.0

CANONICAL_FIELDS = [
    "price",
    "previousClose",
    "dayHigh",
    "dayLow",
    "mktCap",
    "peRatio",
    "epsTTM",
    "dividendYield",
    "priceToBookRatio",
]


# ---------------- providers ----------------

def fetch_finnhub(ticker, client):
    """Return canonical-field dict from Finnhub."""
    out = {}
    try:
        q_raw = client.quote(ticker)
        q = adapters.quote_to_fmp(q_raw, ticker)
        if q:
            qd = q[0]
            out["price"] = qd.get("price")
            out["previousClose"] = qd.get("previousClose")
            out["dayHigh"] = qd.get("dayHigh")
            out["dayLow"] = qd.get("dayLow")
    except FinnhubError as e:
        print(f"WARN: Finnhub quote {ticker} failed: {e}", file=sys.stderr)

    try:
        prof = adapters.profile_to_fmp(client.profile(ticker))
        if prof:
            out["mktCap"] = prof.get("mktCap")
    except FinnhubError as e:
        print(f"WARN: Finnhub profile {ticker} failed: {e}", file=sys.stderr)

    try:
        km = adapters.metric_to_fmp_key_metrics(client.metric(ticker))
        if km:
            m = km[0]
            out["peRatio"] = m.get("peRatio")
            out["epsTTM"] = m.get("epsTTM")
            out["dividendYield"] = m.get("dividendYield")
            out["priceToBookRatio"] = m.get("priceToBookRatio")
    except FinnhubError as e:
        print(f"WARN: Finnhub metric {ticker} failed: {e}", file=sys.stderr)

    return out


def fetch_fmp(ticker, api_key, session):
    """Return canonical-field dict from FMP (stable endpoints)."""
    out = {}
    base = "https://financialmodelingprep.com/stable"

    def _get(path, params=None):
        params = dict(params or {})
        params["apikey"] = api_key
        try:
            r = session.get(f"{base}/{path}", params=params, timeout=30)
            if r.status_code != 200:
                print(
                    f"WARN: FMP {path} {ticker} HTTP {r.status_code}",
                    file=sys.stderr,
                )
                return None
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"WARN: FMP {ticker} network error: {e}", file=sys.stderr)
            return None

    q = _get("quote", {"symbol": ticker})
    if isinstance(q, list) and q:
        out["price"] = q[0].get("price")
        out["previousClose"] = q[0].get("previousClose")
        out["dayHigh"] = q[0].get("dayHigh")
        out["dayLow"] = q[0].get("dayLow")
        out["mktCap"] = q[0].get("marketCap")
        out["epsTTM"] = q[0].get("eps")
        out["peRatio"] = q[0].get("pe")

    rt = _get("ratios-ttm", {"symbol": ticker, "limit": 1})
    if isinstance(rt, list) and rt:
        m = rt[0]
        if m.get("priceToEarningsRatioTTM") is not None:
            out["peRatio"] = m.get("priceToEarningsRatioTTM")
        if m.get("priceToBookRatioTTM") is not None:
            out["priceToBookRatio"] = m.get("priceToBookRatioTTM")
        if m.get("netIncomePerShareTTM") is not None and out.get("epsTTM") is None:
            out["epsTTM"] = m.get("netIncomePerShareTTM")
        # FMP returns decimal (0.0038); Finnhub returns percent (0.38). Scale to match.
        if m.get("dividendYieldTTM") is not None:
            out["dividendYield"] = m.get("dividendYieldTTM") * 100

    return out


# ---------------- diff ----------------

def grade(pct):
    if pct is None:
        return "N/A"
    a = abs(pct)
    if a < WARN_THRESHOLD:
        return "PASS"
    if a < FAIL_THRESHOLD:
        return "WARN"
    return "FAIL"


def compute_diff(fh, fmp):
    """Per-field comparison. Returns list of {field, fh, fmp, pct, grade}."""
    rows = []
    for f in CANONICAL_FIELDS:
        fh_v = fh.get(f)
        fmp_v = fmp.get(f)
        if fh_v is None or fmp_v is None:
            rows.append({
                "field": f, "fh": fh_v, "fmp": fmp_v,
                "pct": None, "grade": "N/A",
            })
            continue
        try:
            fh_n = float(fh_v)
            fmp_n = float(fmp_v)
        except (TypeError, ValueError):
            rows.append({
                "field": f, "fh": fh_v, "fmp": fmp_v,
                "pct": None, "grade": "N/A",
            })
            continue
        if fmp_n == 0 and fh_n == 0:
            pct = 0.0
        elif fmp_n == 0:
            pct = float("inf")
        else:
            pct = (fh_n - fmp_n) / abs(fmp_n) * 100
        rows.append({
            "field": f, "fh": fh_n, "fmp": fmp_n,
            "pct": pct, "grade": grade(pct),
        })
    return rows


# ---------------- rendering ----------------

def fmt_val(v):
    if v is None:
        return "—"
    if isinstance(v, float):
        if abs(v) >= 1e9:
            return f"{v / 1e9:,.2f}B"
        if abs(v) >= 1e6:
            return f"{v / 1e6:,.2f}M"
        if abs(v) >= 100:
            return f"{v:,.2f}"
        return f"{v:,.4f}"
    return str(v)


def fmt_pct(p):
    if p is None:
        return "—"
    if p == float("inf") or p == float("-inf"):
        return "∞"
    return f"{p:+.2f}%"


def render_markdown(per_ticker, when):
    lines = []
    lines.append(f"# Finnhub vs FMP Diff Report — {when:%Y-%m-%d}")
    lines.append("")
    lines.append(f"**Generated**: {when:%Y-%m-%d %H:%M UTC}")
    lines.append(f"**Tickers**: {', '.join(per_ticker.keys())}")
    lines.append("")

    # Aggregate summary
    grade_counts = {"PASS": 0, "WARN": 0, "FAIL": 0, "N/A": 0}
    for rows in per_ticker.values():
        for r in rows:
            grade_counts[r["grade"]] += 1
    total = sum(grade_counts.values())

    lines.append("## Summary")
    lines.append("")
    lines.append("| Grade | Count | Pct |")
    lines.append("|---|---:|---:|")
    for g in ("PASS", "WARN", "FAIL", "N/A"):
        c = grade_counts[g]
        pct = (c / total * 100) if total else 0
        lines.append(f"| {g} | {c} | {pct:.0f}% |")
    lines.append("")
    lines.append(f"**Threshold**: PASS <{WARN_THRESHOLD}%, "
                 f"WARN {WARN_THRESHOLD}-{FAIL_THRESHOLD}%, "
                 f"FAIL >{FAIL_THRESHOLD}%")
    lines.append("")

    # Per-field summary
    by_field = {f: {"PASS": 0, "WARN": 0, "FAIL": 0, "N/A": 0} for f in CANONICAL_FIELDS}
    for rows in per_ticker.values():
        for r in rows:
            by_field[r["field"]][r["grade"]] += 1
    lines.append("## Per-Field Summary")
    lines.append("")
    lines.append("| Field | PASS | WARN | FAIL | N/A |")
    lines.append("|---|---:|---:|---:|---:|")
    for f in CANONICAL_FIELDS:
        d = by_field[f]
        lines.append(f"| {f} | {d['PASS']} | {d['WARN']} | {d['FAIL']} | {d['N/A']} |")
    lines.append("")

    # Per-ticker detail
    lines.append("## Per-Ticker Detail")
    lines.append("")
    for ticker, rows in per_ticker.items():
        lines.append(f"### {ticker}")
        lines.append("")
        lines.append("| Field | Finnhub | FMP | Diff | Grade |")
        lines.append("|---|---:|---:|---:|:---:|")
        for r in rows:
            lines.append(
                f"| {r['field']} | {fmt_val(r['fh'])} | {fmt_val(r['fmp'])} "
                f"| {fmt_pct(r['pct'])} | {r['grade']} |"
            )
        lines.append("")

    # Failures only (quick scan)
    failures = []
    for ticker, rows in per_ticker.items():
        for r in rows:
            if r["grade"] == "FAIL":
                failures.append((ticker, r))
    if failures:
        lines.append("## FAIL Items (quick scan)")
        lines.append("")
        for ticker, r in failures:
            lines.append(
                f"- **{ticker}.{r['field']}**: "
                f"Finnhub={fmt_val(r['fh'])} vs FMP={fmt_val(r['fmp'])} "
                f"({fmt_pct(r['pct'])})"
            )
        lines.append("")

    return "\n".join(lines)


# ---------------- main ----------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--tickers", default=",".join(DEFAULT_TICKERS),
                    help="Comma-separated tickers (default: 10 reference tickers)")
    ap.add_argument("--output", default=None,
                    help="Output path (default: diff_reports/YYYYMMDD.md)")
    ap.add_argument("--no-cache", action="store_true",
                    help="Bypass Finnhub local cache (always live)")
    ap.add_argument("--print", action="store_true",
                    help="Also print the report to stdout")
    args = ap.parse_args()

    fmp_key = os.getenv("FMP_API_KEY")
    if not fmp_key:
        print("ERROR: FMP_API_KEY not set", file=sys.stderr)
        sys.exit(2)

    try:
        client = FinnhubClient(use_cache=not args.no_cache)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    fmp_session = requests.Session()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    per_ticker = {}
    for t in tickers:
        print(f"... fetching {t}", file=sys.stderr)
        fh = fetch_finnhub(t, client)
        fmp = fetch_fmp(t, fmp_key, fmp_session)
        per_ticker[t] = compute_diff(fh, fmp)

    when = datetime.datetime.utcnow()
    report = render_markdown(per_ticker, when)

    if args.output:
        out_path = Path(args.output)
    else:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = REPORT_DIR / f"{when:%Y%m%d}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report)

    if args.print:
        print(report)

    print(f"\nReport: {out_path}", file=sys.stderr)
    print(f"Finnhub stats: {client.stats()}", file=sys.stderr)


if __name__ == "__main__":
    main()
