#!/usr/bin/env python3
"""
momentum-monitor — batch screener across a universe.

Scans a list of tickers in parallel using the same `analyze()` function as
momentum.py (so results are identical to per-ticker runs), applies filters,
ranks by composite score, and writes both a CSV and a Markdown table.

Usage:
    python3 screen.py --universe sp500 --min-score 70
    python3 screen.py --tickers AAPL,MSFT,NVDA,AMD --min-score 60
    python3 screen.py --tickers-file my_watchlist.txt --signal fresh_golden_cross_20_50
    python3 screen.py --universe sp500 --stage "Stage 2 uptrend" --exclude-warning parabolic_blowoff_risk --top 25
    python3 screen.py --universe sp500 --no-cache --workers 20
"""
import argparse
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Reuse analyze() and cache helpers from momentum.py
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from momentum import (  # noqa: E402
    analyze,
    _load_cache,
    _write_cache,
    DEFAULT_TTL_SEC,
)

UNIVERSE_DIR = os.path.join(SCRIPT_DIR, "universes")
CACHE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "cache"))


def _load_sector_map():
    """Return {ticker: GICS_sector} mapping by merging all *_sectors.json in universes dir."""
    merged = {}
    if not os.path.exists(UNIVERSE_DIR):
        return merged
    for filename in os.listdir(UNIVERSE_DIR):
        if filename.endswith("_sectors.json"):
            path = os.path.join(UNIVERSE_DIR, filename)
            try:
                with open(path, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    if isinstance(data, dict):
                        merged.update(data)
            except Exception as e:
                print(f"Warning: failed to load sector map {path}: {e}", file=sys.stderr)
    return merged


_SECTOR_MAP = _load_sector_map()


# ── Universe loading ─────────────────────────────────────────────────────
WATCHLIST_PATH = os.path.join(UNIVERSE_DIR, "watchlist.txt")


def _load_universe(name):
    path = os.path.join(UNIVERSE_DIR, f"{name}.txt")
    if not os.path.exists(path):
        raise SystemExit(f"universe not found: {path}")
    with open(path, "r", encoding="utf-8") as fp:
        return [ln.strip().upper() for ln in fp if ln.strip() and not ln.startswith("#")]


def _load_watchlist():
    """User-editable list of non-SP500 tickers to scan alongside the main universe.
    Missing file = empty list (no-op). Comments (#) and blank lines ignored."""
    if not os.path.exists(WATCHLIST_PATH):
        return []
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as fp:
        return [ln.strip().upper() for ln in fp if ln.strip() and not ln.startswith("#")]


def _load_tickers_file(path):
    if not os.path.exists(path):
        raise SystemExit(f"tickers file not found: {path}")
    out = []
    with open(path, "r", encoding="utf-8") as fp:
        for ln in fp:
            for tok in ln.replace(",", " ").split():
                tok = tok.strip().upper()
                if tok and not tok.startswith("#"):
                    out.append(tok)
    return out


# ── Worker ───────────────────────────────────────────────────────────────
def _scan_one(ticker, use_cache, max_age):
    """Return (ticker, payload_or_None, error_or_None)."""
    if use_cache:
        cached = _load_cache(ticker, max_age)
        if cached is not None:
            return ticker, cached, None
    try:
        payload = analyze(ticker)
        _write_cache(ticker, payload)
        return ticker, payload, None
    except Exception as e:
        return ticker, None, str(e)


# ── Filters ──────────────────────────────────────────────────────────────
def _passes(payload, args):
    comp = payload.get("momentum_composite", {})
    score = comp.get("score", 0)
    if score < args.min_score:
        return False
    if args.max_score is not None and score > args.max_score:
        return False

    stage = payload.get("ma_structure", {}).get("stage", "")
    if args.stage and stage != args.stage:
        return False

    rsi = payload.get("rsi", {}).get("rsi_14")
    if args.min_rsi is not None and (rsi is None or rsi < args.min_rsi):
        return False
    if args.max_rsi is not None and (rsi is None or rsi > args.max_rsi):
        return False

    signals = set(payload.get("signals", []))
    warnings = set(payload.get("warnings", []))
    for required in args.signal:
        if required not in signals:
            return False
    for excluded in args.exclude_warning:
        if excluded in warnings:
            return False
    for excluded in args.exclude_signal:
        if excluded in signals:
            return False

    label = comp.get("label", "")
    if args.label and label != args.label:
        return False

    return True


# ── Output ───────────────────────────────────────────────────────────────
CSV_COLUMNS = [
    "rank", "ticker", "in_sp500", "in_nasdaq100", "sector", "price", "score", "label", "stage",
    "volume_today", "avg_20d", "ratio_20d", "spike_label", "volume_trend",
    "intraday_state", "elapsed_min",
    "ma_20", "ma_50", "ma_200",
    "above_ma20_pct", "above_ma50_pct", "above_ma200_pct",
    "rsi_14", "rsi_zone",
    "macd_line", "macd_signal", "macd_hist", "macd_bullish_cross", "macd_bearish_cross",
    "short_pct_float", "short_interpretation",
    "signals", "warnings",
    "cache_hit", "cache_age_sec",
]


def _row_from_payload(rank, p, sp500_set=None, n100_set=None):
    v = p.get("volume", {})
    m = p.get("ma_structure", {})
    s = p.get("short_interest", {})
    c = p.get("momentum_composite", {})
    r = p.get("rsi", {})
    ticker = p.get("ticker")
    # If set is None, we assume it's NOT in that universe (unless it's a custom scan where we didn't check)
    # Actually, better: if we have the ref set, use it.
    in_sp500 = (ticker in sp500_set) if sp500_set is not None else False
    in_n100  = (ticker in n100_set) if n100_set is not None else False

    return {
        "rank": rank,
        "ticker": ticker,
        "in_sp500": int(in_sp500),
        "in_nasdaq100": int(in_n100),
        "sector": _SECTOR_MAP.get(ticker) or "Unknown",
        "price": p.get("price"),
        "score": c.get("score"),
        "label": c.get("label"),
        "stage": m.get("stage"),
        "volume_today":   v.get("today"),
        "avg_20d":        v.get("avg_20d"),
        "ratio_20d":      v.get("ratio_20d"),
        "spike_label":    v.get("spike_label"),
        "volume_trend":   v.get("volume_trend"),
        "intraday_state": v.get("intraday_state"),
        "elapsed_min":    v.get("elapsed_min"),
        "ma_20":   m.get("ma_20"),
        "ma_50":   m.get("ma_50"),
        "ma_200":  m.get("ma_200"),
        "above_ma20_pct":  m.get("above_ma20_pct"),
        "above_ma50_pct":  m.get("above_ma50_pct"),
        "above_ma200_pct": m.get("above_ma200_pct"),
        "rsi_14":   r.get("rsi_14"),
        "rsi_zone": r.get("zone"),
        "macd_line":         p.get("macd", {}).get("macd_line"),
        "macd_signal":       p.get("macd", {}).get("signal_line"),
        "macd_hist":         p.get("macd", {}).get("histogram"),
        "macd_bullish_cross": p.get("macd", {}).get("bullish_cross", False),
        "macd_bearish_cross": p.get("macd", {}).get("bearish_cross", False),
        "short_pct_float": s.get("short_pct_float"),
        "short_interpretation": s.get("interpretation"),
        "signals": "|".join(p.get("signals", [])),
        "warnings": "|".join(p.get("warnings", [])),
        "cache_hit": p.get("cache_hit"),
        "cache_age_sec": p.get("cache_age_sec"),
    }


def _write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(rows)


def _render_md(rows, top, meta):
    lines = [
        f"## Momentum Screener — {meta['generated_at']}",
        "",
        f"- Universe: **{meta['universe_desc']}** ({meta['scanned']} scanned, "
        f"{meta['errors']} errors, {meta['matched']} matched)",
        f"- Filters: {meta['filters'] or '_none_'}",
        f"- Elapsed: {meta['elapsed_sec']}s │ cache hits: {meta['cache_hits']}/{meta['scanned']}",
        "",
        "| # | Ticker | Price | Score | Label | Stage | Vol× | Above 200MA | RSI | Signals |",
        "|---|--------|-------|-------|-------|-------|------|-------------|-----|---------|",
    ]
    for r in rows[:top]:
        sig = r["signals"].replace("|", ", ") or "—"
        am200 = r["above_ma200_pct"]
        am200_txt = f"{am200:+.1f}%" if am200 is not None else "—"
        rsi_txt = f"{r['rsi_14']:.0f}" if r.get("rsi_14") is not None else "—"
        lines.append(
            f"| {r['rank']} | **{r['ticker']}** | ${r['price']} | "
            f"{r['score']} | {r['label']} | {r['stage']} | "
            f"{r['ratio_20d']}× | {am200_txt} | {rsi_txt} | {sig} |"
        )
    if len(rows) > top:
        lines.append("")
        lines.append(f"_…{len(rows) - top} more rows in CSV_")
    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Batch momentum screener")
    src = ap.add_mutually_exclusive_group(required=False)
    src.add_argument("--universe", default="all", help="Universe name under scripts/universes/ (e.g. sp500, nasdaq100, all)")
    src.add_argument("--tickers", help="Comma-separated ticker list")
    src.add_argument("--tickers-file", help="Path to file with one ticker per line")

    # Filters
    ap.add_argument("--min-score", type=float, default=0, help="Minimum composite score (default 0)")
    ap.add_argument("--max-score", type=float, default=None)
    ap.add_argument("--min-rsi", type=float, default=None, help="Minimum RSI-14 (e.g. 30 to exclude oversold)")
    ap.add_argument("--max-rsi", type=float, default=None, help="Maximum RSI-14 (e.g. 70 to exclude overbought)")
    ap.add_argument("--stage", help='e.g. "Stage 2 uptrend"')
    ap.add_argument("--label", help="e.g. BULLISH | STRONGLY_BULLISH")
    ap.add_argument("--signal", action="append", default=[],
                    help="Require signal (repeatable, AND). e.g. fresh_golden_cross_20_50")
    ap.add_argument("--exclude-signal", action="append", default=[])
    ap.add_argument("--exclude-warning", action="append", default=[],
                    help="Exclude tickers with this warning (repeatable)")

    # Execution
    ap.add_argument("--workers", type=int, default=15)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--max-age", type=int, default=DEFAULT_TTL_SEC)
    ap.add_argument("--top", type=int, default=30, help="Rows to display in MD table (CSV has all)")

    # Output
    ap.add_argument("--output-dir", default=CACHE_DIR, help="Where to write CSV")
    ap.add_argument("--json", action="store_true", help="Also emit JSON summary to stdout")
    ap.add_argument("--md-only", action="store_true", help="Only print MD table (no stderr summary)")
    ap.add_argument("--journal", action="store_true",
                    help="Auto-append results to momentum-monitor journal for forward-return tracking")

    args = ap.parse_args()

    # Primary universe selection
    if args.universe:
        if args.universe == "all":
            u1 = _load_universe("sp500")
            u2 = _load_universe("nasdaq100")
            base_tickers = sorted(list(set(u1 + u2)))
            universe_desc = "all (SP500 + Nasdaq100)"
        else:
            base_tickers = _load_universe(args.universe)
            universe_desc = args.universe
    elif args.tickers:
        base_tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        universe_desc = f"custom ({len(base_tickers)} tickers)"
    else:
        base_tickers = _load_tickers_file(args.tickers_file)
        universe_desc = f"file:{os.path.basename(args.tickers_file)}"

    # Track membership for flagging.
    sp500_ref = set(_load_universe("sp500"))
    n100_ref  = set(_load_universe("nasdaq100"))

    # Watchlist is merged when primary universe is a standard one
    base_set = set(base_tickers)
    watchlist = _load_watchlist() if args.universe in ("sp500", "nasdaq100", "all") else []
    extra = [t for t in watchlist if t not in base_set]
    tickers = base_tickers + extra
    if extra:
        universe_desc = f"{universe_desc} +{len(extra)} watchlist"

    if not tickers:
        raise SystemExit("empty ticker list")

    print(f"[screen] scanning {len(tickers)} tickers with {args.workers} workers…", file=sys.stderr)
    t0 = time.time()
    results = []
    errors = []
    cache_hits = 0
    use_cache = not args.no_cache

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(_scan_one, t, use_cache, args.max_age): t for t in tickers}
        done = 0
        for fut in as_completed(futures):
            t, payload, err = fut.result()
            done += 1
            if err:
                errors.append({"ticker": t, "error": err})
            else:
                results.append(payload)
                if payload.get("cache_hit"):
                    cache_hits += 1
            if done % 50 == 0 or done == len(tickers):
                print(f"[screen] {done}/{len(tickers)} ({len(errors)} errors, {cache_hits} cache hits)",
                      file=sys.stderr)

    # Filter + rank
    matched = [p for p in results if _passes(p, args)]
    matched.sort(
        key=lambda p: (
            -(p.get("momentum_composite", {}).get("score") or 0),
            -(p.get("volume", {}).get("ratio_20d") or 0),  # None → 0 (too_early state)
        )
    )

    rows = [_row_from_payload(i + 1, p, sp500_set=sp500_ref, n100_set=n100_ref)
            for i, p in enumerate(matched)]

    # Write CSV
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    csv_path = os.path.join(args.output_dir, f"screen_{ts}.csv")
    _write_csv(rows, csv_path)

    # Describe filters for MD header
    filter_bits = []
    if args.min_score > 0:
        filter_bits.append(f"score≥{args.min_score}")
    if args.max_score is not None:
        filter_bits.append(f"score≤{args.max_score}")
    if args.min_rsi is not None:
        filter_bits.append(f"rsi≥{args.min_rsi}")
    if args.max_rsi is not None:
        filter_bits.append(f"rsi≤{args.max_rsi}")
    if args.stage:
        filter_bits.append(f'stage="{args.stage}"')
    if args.label:
        filter_bits.append(f"label={args.label}")
    for s in args.signal:
        filter_bits.append(f"+{s}")
    for s in args.exclude_signal:
        filter_bits.append(f"-sig:{s}")
    for w in args.exclude_warning:
        filter_bits.append(f"-warn:{w}")

    meta = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "universe_desc": universe_desc,
        "scanned": len(tickers),
        "errors": len(errors),
        "matched": len(matched),
        "filters": ", ".join(filter_bits),
        "elapsed_sec": round(time.time() - t0, 1),
        "cache_hits": cache_hits,
    }

    md = _render_md(rows, args.top, meta)
    print(md)

    if args.json:
        print(json.dumps({
            "meta": meta,
            "csv_path": csv_path,
            "rows": rows,
            "errors": errors,
        }, ensure_ascii=False, indent=2, default=str))

    if args.journal and rows:
        try:
            from journal import cmd_snapshot
            cmd_snapshot(csv_path)
        except Exception as e:
            print(f"[screen] journal snapshot failed: {e}", file=sys.stderr)

    if not args.md_only:
        print(
            f"\n→ {meta['scanned']} scanned, {meta['matched']} matched, "
            f"{meta['errors']} errors in {meta['elapsed_sec']}s │ CSV: {csv_path}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
