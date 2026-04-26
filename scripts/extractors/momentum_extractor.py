"""Extract momentum journal records.

Each line of journal.jsonl is one snap of one ticker. We treat each line as
an independent decision record. Caller passes a `selector` dict to pick which
records to extract (e.g., specific ticker + snap_date).
"""
from __future__ import annotations
import json
from pathlib import Path


def extract_one(record: dict) -> dict:
    """Convert a single momentum journal record into our event-index format."""
    ticker = record.get("ticker")
    snap_date = record.get("snap_date")
    score = record.get("score")
    label = record.get("label")
    signals = record.get("signals") or []
    warnings = record.get("warnings") or []
    entry_price = record.get("entry_price")
    snap_id = record.get("snap_id")

    out = {
        "source": "momentum-screen",
        "decision_date": snap_date,
        "scope": "ticker",
        "tickers": [ticker] if ticker else [],
        "raw_path": "skills/momentum-monitor/journal/journal.jsonl",
        "summary": f"{ticker} momentum {label} score={score}",
        "decision_content": {
            "ticker": ticker,
            "score": score,
            "label": label,
            "stage": record.get("stage"),
            "ratio_20d": record.get("ratio_20d"),
            "above_ma200_pct": record.get("above_ma200_pct"),
            "rsi_14": record.get("rsi_14"),
            "rsi_zone": record.get("rsi_zone"),
            "signals": signals,
            "warnings": warnings,
            "entry_price": entry_price,
            "snap_id": snap_id,
        },
        "agent_breakdown": [],
        "tuning_hooks": {
            "score_band": (
                "very_high" if score and score >= 80 else
                "high"      if score and score >= 70 else
                "medium"    if score and score >= 60 else "low"),
            "warning_count": len(warnings),
            "warnings": warnings,
            "rsi_zone": record.get("rsi_zone"),
            "stage": record.get("stage"),
            "has_overbought": "overbought_rsi" in warnings,
            "has_parabolic":  "parabolic_blowoff_risk" in warnings,
            "fresh_golden_cross": any("golden_cross" in s for s in signals),
            "fresh_death_cross":  any("death_cross"  in w for w in warnings),
        },
    }
    out["decision_id"] = f"momentum-screen_{ticker}_{snap_id}"
    return out


def extract_selected(jsonl_path: Path, selector: list[dict]) -> list[dict]:
    """selector: list of {ticker, snap_id} pairs to extract."""
    keys = {(s["ticker"], s["snap_id"]) for s in selector}
    out: list[dict] = []
    with jsonl_path.open() as f:
        for ln in f:
            try:
                rec = json.loads(ln)
            except json.JSONDecodeError:
                continue
            k = (rec.get("ticker"), rec.get("snap_id"))
            if k in keys:
                out.append(extract_one(rec))
    return out


def extract_aggregated_runs(
    jsonl_path: Path,
    min_tickers_per_snap: int = 100,
    top_n_per_snap: int = 20,
) -> list[dict]:
    """產出每日 1 筆 record (per snap_date), 取當日最後一個 ticker 數 >=
    min_tickers_per_snap 的 snap, 內含 top_n_per_snap 名 ticker by score.

    過濾 debug/測試 runs (e.g. 8/7 ticker 的 partial 跑)。
    """
    # group by snap_id; keep order
    snaps: dict[str, list[dict]] = {}
    snap_meta: dict[str, dict] = {}
    with jsonl_path.open() as f:
        for ln in f:
            try:
                rec = json.loads(ln)
            except json.JSONDecodeError:
                continue
            sid = rec.get("snap_id")
            if not sid:
                continue
            snaps.setdefault(sid, []).append(rec)
            if sid not in snap_meta:
                snap_meta[sid] = {
                    "snap_id": sid,
                    "snap_date": rec.get("snap_date"),
                    "snap_timestamp": rec.get("snap_timestamp"),
                }

    # 一天可能有多次 snap, 留最後 (max snap_timestamp) 且 ticker >= threshold
    by_date: dict[str, str] = {}
    for sid, recs in snaps.items():
        if len(recs) < min_tickers_per_snap:
            continue
        d = snap_meta[sid]["snap_date"]
        ts = snap_meta[sid]["snap_timestamp"] or sid
        if d not in by_date or ts > snap_meta[by_date[d]]["snap_timestamp"]:
            by_date[d] = sid

    output: list[dict] = []
    for d in sorted(by_date.keys()):
        sid = by_date[d]
        recs = snaps[sid]
        # rank by score descending
        recs_sorted = sorted(recs,
                             key=lambda r: (r.get("score") or 0),
                             reverse=True)
        top = recs_sorted[:top_n_per_snap]

        per_ticker = []
        warnings_total: dict[str, int] = {}
        labels: dict[str, int] = {}
        for r in top:
            per_ticker.append({
                "ticker": r.get("ticker"),
                "score": r.get("score"),
                "label": r.get("label"),
                "stage": r.get("stage"),
                "rsi_14": r.get("rsi_14"),
                "rsi_zone": r.get("rsi_zone"),
                "signals": r.get("signals") or [],
                "warnings": r.get("warnings") or [],
                "entry_price": r.get("entry_price"),
            })
            labels[r.get("label") or "?"] = labels.get(r.get("label") or "?", 0) + 1
            for w in (r.get("warnings") or []):
                warnings_total[w] = warnings_total.get(w, 0) + 1

        record = {
            "decision_id": f"momentum-screen_{sid}",
            "source": "momentum-screen",
            "decision_date": d,
            "scope": "screen-run",
            "tickers": [r["ticker"] for r in per_ticker if r.get("ticker")],
            "raw_path": "skills/momentum-monitor/journal/journal.jsonl",
            "summary": (
                f"momentum screen: {len(recs)} 全宇宙 → top {len(top)} "
                f"(snap {sid})"),
            "decision_content": {
                "snap_id": sid,
                "snap_timestamp": snap_meta[sid]["snap_timestamp"],
                "n_total_screened": len(recs),
                "n_evaluated": len(top),
                "tickers": per_ticker,
                "label_distribution": labels,
                "warning_counts": warnings_total,
            },
            "agent_breakdown": [],
            "tuning_hooks": {
                "n_total_screened": len(recs),
                "n_evaluated": len(top),
                "label_distribution": labels,
                "warning_counts": warnings_total,
                "score_top": top[0].get("score") if top else None,
                "score_min_top_n": top[-1].get("score") if top else None,
            },
        }
        output.append(record)
    return output
