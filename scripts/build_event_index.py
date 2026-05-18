"""Production indexer — scans all decision sources, computes verdicts, writes
`reports/decision_review/event_index_<TODAY>.json`.

Usage:
    python3 scripts/build_event_index.py [--today YYYY-MM-DD]

Discovery rules:
    deep-dive         reports/<YYYYMMDD>_<TICKER>.md (excludes sector/news/theme/HTML)
    sector-scan       reports/<YYYY-MM-DD>_sector_report.md
    news-digest       reports/<YYYY-MM-DD>_news_digest.md
    theme-detector    reports/*theme_report*.md, reports/theme_detector_*.md
    momentum-screen   skills/momentum-monitor/journal/journal.jsonl (aggregated per snap_id, top 20)
    thematic-screener skills/thematic-screener/data/recommendations/*.json
    earnings-analyzer reports/earnings_trade_analyzer_*.json
    short-term-weekly reports/SHORT_TERM_WEEKLY_*.md
    postmortem        reports/POSTMORTEM_*.md
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yfinance as yf  # noqa: E402

from scripts.extractors import (  # noqa: E402
    deep_dive_extractor,
    sector_extractor,
    news_digest_extractor,
    theme_detector_extractor,
    momentum_extractor,
    thematic_screener_extractor,
    earnings_analyzer_extractor,
    weekly_review_extractor,
    postmortem_extractor,
)
from scripts.verdict_rules import EVAL_WINDOW_DAYS, VERDICT_DISPATCH, verdict_momentum_aggregate  # noqa: E402

DEEP_DIVE_RE = re.compile(r"^\d{8}_[A-Z][A-Z0-9]+\.md$")


def discover_sources() -> dict[str, list[Path]]:
    """Glob all decision source files."""
    reports = ROOT / "reports"
    found: dict[str, list[Path]] = {}

    # deep-dive: YYYYMMDD_TICKER.md (must match strict pattern, exclude others)
    found["deep-dive"] = sorted(
        p for p in reports.glob("[0-9]" * 8 + "_*.md")
        if DEEP_DIVE_RE.match(p.name)
        and "_theme" not in p.name
        and "_news" not in p.name
        and "_sector" not in p.name
        and "_valuation" not in p.name)

    found["sector-scan"] = sorted(reports.glob("*_sector_report.md"))
    found["news-digest"] = sorted(reports.glob("*_news_digest.md"))
    # theme reports come in two forms:
    found["theme-detector"] = sorted(
        list(reports.glob("*_theme_report.md")) +
        list(reports.glob("theme_detector_*.md")))
    found["thematic-screener"] = sorted(
        (ROOT / "skills/thematic-screener/data/recommendations").glob("*.json"))
    found["earnings-analyzer"] = sorted(reports.glob("earnings_trade_analyzer_*.json"))
    found["short-term-weekly"] = sorted(reports.glob("SHORT_TERM_WEEKLY_*.md"))
    found["postmortem"] = sorted(reports.glob("POSTMORTEM_*.md"))

    # momentum journal handled separately (single jsonl produces multiple records)
    found["momentum-screen"] = [ROOT / "skills/momentum-monitor/journal/journal.jsonl"]

    return found


# ────────────────────────────────────────────────────────────────────
# Price helpers
# ────────────────────────────────────────────────────────────────────

PRICE_CACHE: dict[str, dict] = {}


def fetch_history(ticker: str, start: date, end: date) -> dict:
    if not ticker:
        return {}
    # Wide-window cache key: round to month boundaries to maximize reuse
    key = f"{ticker}|{start.isoformat()}|{end.isoformat()}"
    if key in PRICE_CACHE:
        return PRICE_CACHE[key]
    try:
        h = yf.Ticker(ticker).history(start=start.isoformat(),
                                      end=(end + timedelta(days=1)).isoformat(),
                                      auto_adjust=False)
        out = {d.strftime("%Y-%m-%d"): float(c) for d, c in zip(h.index, h["Close"])}
    except Exception as e:
        print(f"  ! yfinance fail {ticker}: {e}", file=sys.stderr)
        out = {}
    PRICE_CACHE[key] = out
    return out


def closest_price(prices: dict, target: date, direction: str = "after") -> tuple[str | None, float | None]:
    keys = sorted(prices.keys())
    target_s = target.isoformat()
    if direction == "after":
        for k in keys:
            if k >= target_s:
                return k, prices[k]
    else:
        for k in reversed(keys):
            if k <= target_s:
                return k, prices[k]
    return None, None


def compute_reality_for_ticker(ticker: str, decision_date: date, eval_date: date) -> dict | None:
    if not ticker:
        return None
    prices = fetch_history(ticker, decision_date - timedelta(days=4),
                                   eval_date + timedelta(days=4))
    if not prices:
        return None
    d_key, p_dec = closest_price(prices, decision_date, "after")
    e_key, p_eval = closest_price(prices, eval_date, "before")
    if p_dec is None or p_eval is None:
        return None
    # V2.17.22 — when eval price falls back to decision-day bar (yfinance
    # has no later bar yet), the window is genuinely incomplete. Treat as
    # pending so verdict layer downgrades it.
    if e_key == d_key:
        return None

    in_window = {k: v for k, v in prices.items() if d_key <= k <= (e_key or d_key)}
    if not in_window:
        in_window = {d_key: p_dec, e_key: p_eval}

    return {
        "price_at_decision": round(p_dec, 4),
        "price_at_decision_date": d_key,
        "price_at_eval": round(p_eval, 4),
        "price_at_eval_date": e_key,
        "return_pct": round((p_eval - p_dec) / p_dec * 100, 3),
        "max_runup_since": round(max(in_window.values()), 4),
        "max_drawdown_since": round(min(in_window.values()), 4),
    }


def compute_returns_for_tickers(tickers: list[str], decision_date: date, eval_date: date) -> dict:
    out = {}
    for t in tickers:
        r = compute_reality_for_ticker(t, decision_date, eval_date)
        if r:
            out[t] = r["return_pct"]
    return out


# ────────────────────────────────────────────────────────────────────
# Per-record reality + verdict
# ────────────────────────────────────────────────────────────────────

def parse_decision_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def build_eval_block(record: dict, today: date) -> tuple[dict, dict]:
    src = record["source"]
    window_days = EVAL_WINDOW_DAYS.get(src, 0)
    decision_d = parse_decision_date(record.get("decision_date"))
    if decision_d is None:
        return ({"days_elapsed": None, "window_complete_pct": None,
                 "window_days": window_days, "eval_date": None,
                 "today": today.isoformat(), "pending": False},
                {"label": "n/a", "rationale": "缺 decision_date"})

    eval_d = min(decision_d + timedelta(days=window_days), today)
    days_elapsed = (today - decision_d).days
    pct = min(100, int(100 * days_elapsed / window_days)) if window_days else None

    base = {
        "decision_date": decision_d.isoformat(),
        "eval_date": eval_d.isoformat(),
        "today": today.isoformat(),
        "window_days": window_days,
        "days_elapsed": days_elapsed,
        "window_complete_pct": pct,
        "pending": (window_days > 0 and days_elapsed < window_days),
    }

    verdict_fn = VERDICT_DISPATCH.get(src)
    dc = record.get("decision_content", {})

    if src == "deep-dive":
        ticker = (record.get("tickers") or [None])[0]
        ticker_reality = compute_reality_for_ticker(ticker, decision_d, eval_d)
        base["ticker_reality"] = ticker_reality
        verdict = verdict_fn(dc, ticker_reality) if verdict_fn else {"label": "n/a", "rationale": ""}

    elif src == "sector-scan":
        etfs = list({r.get("etf") for r in (dc.get("sector_ratings") or []) if r.get("etf")}) + ["SPY"]
        sector_returns = compute_returns_for_tickers(etfs, decision_d, eval_d)
        base["etf_returns"] = sector_returns
        verdict = verdict_fn(dc, sector_returns) if verdict_fn else {"label": "n/a", "rationale": ""}

    elif src == "news-digest":
        spy_returns = compute_returns_for_tickers(["SPY"], decision_d, eval_d)
        base["spy_return_pct"] = spy_returns.get("SPY")
        verdict = verdict_fn(dc, spy_returns.get("SPY")) if verdict_fn else {"label": "n/a", "rationale": ""}

    elif src == "theme-detector":
        etfs = list({e for t in (dc.get("themes") or []) for e in (t.get("proxy_etfs") or [])}) + ["SPY"]
        etf_returns = compute_returns_for_tickers(etfs, decision_d, eval_d)
        base["etf_returns"] = etf_returns
        verdict = verdict_fn(dc, etf_returns) if verdict_fn else {"label": "n/a", "rationale": ""}

    elif src == "momentum-screen":
        # Aggregated form: dc.tickers[] is list of mini per-ticker records
        per_ticker_results = []
        for t_data in dc.get("tickers") or []:
            tk = t_data.get("ticker")
            tk_reality = compute_reality_for_ticker(tk, decision_d, eval_d)
            tk_verdict = VERDICT_DISPATCH["momentum-screen"](t_data, tk_reality)
            per_ticker_results.append({
                "ticker": tk,
                "score": t_data.get("score"),
                "label": t_data.get("label"),
                "warnings": t_data.get("warnings") or [],
                "return_pct": (tk_reality or {}).get("return_pct"),
                "verdict": tk_verdict["label"],
                "rationale": tk_verdict["rationale"],
            })
        base["per_ticker"] = per_ticker_results
        verdict = verdict_momentum_aggregate(per_ticker_results)

    elif src == "thematic-screener":
        if base["pending"]:
            verdict = {"label": "pending", "rationale": f"eval window {window_days}d 未到"}
        else:
            tickers = [m["ticker"] for m in (dc.get("top_movers") or [])]
            mover_returns = compute_returns_for_tickers(tickers, decision_d, eval_d)
            base["mover_returns"] = mover_returns
            verdict = verdict_fn(dc, mover_returns) if verdict_fn else {"label": "n/a", "rationale": ""}

    elif src == "earnings-analyzer":
        if base["pending"]:
            verdict = {"label": "pending", "rationale": f"eval window {window_days}d 未到 (post-earnings)"}
        else:
            tickers = [r["symbol"] for r in (dc.get("results") or [])]
            ticker_returns = compute_returns_for_tickers(tickers, decision_d, eval_d)
            base["ticker_returns"] = ticker_returns
            verdict = verdict_fn(dc, ticker_returns) if verdict_fn else {"label": "n/a", "rationale": ""}

    elif src in ("short-term-weekly", "postmortem"):
        verdict = verdict_fn(dc) if verdict_fn else {"label": "n/a", "rationale": ""}
    else:
        verdict = {"label": "n/a", "rationale": f"未知 source {src}"}

    return base, verdict


# ────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────

EXTRACTOR_DISPATCH = {
    "deep-dive":         lambda p: deep_dive_extractor.extract(p),
    "sector-scan":       lambda p: sector_extractor.extract(p),
    "news-digest":       lambda p: news_digest_extractor.extract(p),
    "theme-detector":    lambda p: theme_detector_extractor.extract(p),
    "thematic-screener": lambda p: thematic_screener_extractor.extract(p),
    "earnings-analyzer": lambda p: earnings_analyzer_extractor.extract(p),
    "short-term-weekly": lambda p: weekly_review_extractor.extract(p),
    "postmortem":        lambda p: postmortem_extractor.extract(p),
}


# Rec 8 (V2.17.16) — industry rollup so REVIEW can surface "CPU/memory: 3 ticker / +63% miss"
# instead of only ticker-level repeat-miss lists.
def _build_industry_rollup(records: list[dict]) -> list[dict]:
    """Group deep-dive records by sub_industry_heat.ticker_industry (fallback to
    ticker_sector). Returns rows sorted by descending count."""
    buckets: dict[str, dict] = {}
    for r in records:
        if r.get("source") != "deep-dive":
            continue
        th = r.get("tuning_hooks") or {}
        heat = th.get("sub_industry_heat") or {}
        key = heat.get("ticker_industry") or heat.get("ticker_sector") or "Unknown"
        b = buckets.setdefault(key, {
            "industry":              key,
            "sector":                heat.get("ticker_sector"),
            "n":                     0,
            "hit":                   0,
            "miss":                  0,
            "neutral":               0,
            "pending":               0,
            "tickers":               set(),
            "miss_returns":          [],
            "industry_top_30pct":    heat.get("industry_top_30pct"),
            "sector_top_3":          heat.get("sector_top_3"),
            "sector_composite_score": heat.get("sector_composite_score"),
        })
        b["n"] += 1
        if r.get("tickers"):
            b["tickers"].add(r["tickers"][0])
        v = (r.get("verdict") or {}).get("label") or "n/a"
        if v in ("hit", "miss", "neutral", "pending"):
            b[v] = b.get(v, 0) + 1
        if v == "miss":
            rl = ((r.get("reality_at_eval") or {}).get("ticker_reality") or {})
            ret = rl.get("return_pct")
            if ret is not None:
                b["miss_returns"].append(round(float(ret), 2))

    rows = []
    for b in buckets.values():
        n = b["n"]
        miss = b.get("miss", 0)
        miss_returns = b["miss_returns"]
        rows.append({
            "industry":               b["industry"],
            "sector":                 b["sector"],
            "n":                      n,
            "hit":                    b.get("hit", 0),
            "miss":                   miss,
            "neutral":                b.get("neutral", 0),
            "pending":                b.get("pending", 0),
            "miss_rate":              round(miss / n, 3) if n else None,
            "tickers":                sorted(b["tickers"]),
            "avg_miss_return_pct":    round(sum(miss_returns) / len(miss_returns), 2) if miss_returns else None,
            "max_miss_return_pct":    max(miss_returns) if miss_returns else None,
            "industry_top_30pct":     b["industry_top_30pct"],
            "sector_top_3":           b["sector_top_3"],
            "sector_composite_score": b["sector_composite_score"],
        })
    rows.sort(key=lambda r: (-r["n"], -(r["miss"] or 0)))
    return rows


def _load_adjustment_ledger() -> list[dict]:
    """Read reports/decision_review/ADJUSTMENT_LEDGER.md and surface active
    Rec entries' summary header so REVIEW pass can evaluate them. Format-tolerant:
    we only look for ## Rec N ... blocks with status: active."""
    ledger = ROOT / "reports/decision_review/ADJUSTMENT_LEDGER.md"
    if not ledger.exists():
        return []
    text = ledger.read_text(encoding="utf-8")
    entries: list[dict] = []
    blocks = re.split(r"\n## (?=Rec )", text)
    for blk in blocks[1:]:
        first = blk.splitlines()[0].strip()
        meta: dict = {"title": first}
        for k in ("applied_date", "applied_version", "status", "target_metric", "rec_source"):
            m = re.search(rf"^- \*\*{k}\*\*:\s*(.+)$", blk, re.MULTILINE)
            if m:
                meta[k] = m.group(1).strip().rstrip("`").lstrip("`")
        if (meta.get("status") or "").lower() == "active":
            entries.append(meta)
    return entries


def main(today: date):
    print(f"Building event_index (today = {today})", file=sys.stderr)
    sources = discover_sources()

    out_records: list[dict] = []
    for cat, paths in sources.items():
        if not paths:
            continue
        if cat == "momentum-screen":
            print(f"\n→ momentum-screen: aggregating {paths[0]}", file=sys.stderr)
            recs = momentum_extractor.extract_aggregated_runs(paths[0])
            print(f"  {len(recs)} aggregate records", file=sys.stderr)
            for rec in recs:
                rec["reality_at_eval"], rec["verdict"] = build_eval_block(rec, today)
                out_records.append(rec)
            continue

        print(f"\n→ {cat}: {len(paths)} files", file=sys.stderr)
        for p in paths:
            try:
                rec = EXTRACTOR_DISPATCH[cat](p)
                rec["reality_at_eval"], rec["verdict"] = build_eval_block(rec, today)
                out_records.append(rec)
            except Exception as e:
                print(f"  !! {p.name}: {e}", file=sys.stderr)

    industry_rollup = _build_industry_rollup(out_records)
    adjustment_ledger = _load_adjustment_ledger()

    out = {
        "version": "1.1",
        "generated_at": datetime.now().isoformat(),
        "today": today.isoformat(),
        "decision_count": len(out_records),
        "industry_rollup": industry_rollup,
        "adjustment_ledger_active": adjustment_ledger,
        "decisions": out_records,
    }
    out_dir = ROOT / "reports/decision_review"
    out_path = out_dir / f"event_index_{today.isoformat()}.json"
    latest_path = out_dir / "event_index_latest.json"
    payload = json.dumps(out, indent=2, ensure_ascii=False)
    out_path.write_text(payload)
    latest_path.write_text(payload)
    print(f"\nWrote {len(out_records)} records → {out_path}", file=sys.stderr)
    print(f"Also wrote latest copy → {latest_path}", file=sys.stderr)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=None,
                    help="Override 'today' (YYYY-MM-DD)，預設今天")
    args = ap.parse_args()
    today = (datetime.strptime(args.today, "%Y-%m-%d").date()
             if args.today else date.today())
    main(today)
