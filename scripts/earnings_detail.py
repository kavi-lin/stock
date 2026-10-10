"""Read-only earnings page projection. Historical views never fetch or save data."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/earnings-analyst/scripts"))
import earnings_history as history


def load_earnings_detail(ticker, period=None, revision=None, *, root=ROOT):
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]{0,19}", ticker):
        raise ValueError("invalid ticker")
    if period is not None and (not re.fullmatch(r"\d{4}-\d{2}-\d{2}", period)
                               or history.iso_date(period) != period):
        raise ValueError("invalid fiscal period")
    if revision is not None and not re.fullmatch(r"[a-f0-9]{64}", revision):
        raise ValueError("invalid analysis revision")
    root = Path(root)
    cache_dir = root / "skills/earnings-analyst/cache"
    choices, revisions = {}, {}
    for path in history.base_paths(cache_dir, ticker):
        bundle = history.read_object(path)
        context = history.earnings_context(bundle)
        end = context["fiscal_period_end"]
        if bundle.get("ticker") != ticker or not end:
            continue
        narrative = {}
        if history.narrative_path(path).exists():
            candidate = history.read_object(history.narrative_path(path))
            if candidate.get("ticker") == ticker and candidate.get("last_earnings_date") == end:
                narrative = candidate
        choices[end] = {"bundle": bundle, "narrative": narrative, "kind": "legacy",
                        "recorded_at": narrative.get("as_of_date") or bundle.get("as_of_date"),
                        "report_path": None, "comparison": None}
    warnings = []
    for path in sorted((cache_dir / "history" / ticker).glob("*/*.json")):
        try:
            record = history.read_object(path)
            content = record["content"]
            if record.get("schema_version") != history.VERSION or record.get("content_hash") != history.digest(content):
                raise ValueError("invalid completed history")
            bundle = content["bundle"]
            end = history.earnings_context(bundle)["fiscal_period_end"]
            if bundle.get("ticker") != ticker or not end or history.validate_comparison(content["comparison"], bundle):
                raise ValueError("invalid history comparison")
            old = choices.get(end, {})
            # Company identity is presentation metadata; all financials come from the saved run.
            bundle = {**bundle, "snapshot": old.get("bundle", {}).get("snapshot")}
            saved = {"bundle": bundle, "narrative": content["narrative"], "kind": "completed",
                     "recorded_at": record["recorded_at"], "report_path": content.get("report_archive"),
                     "comparison": content["comparison"]}
            revisions[path.stem] = (end, saved)
            if old.get("kind") != "completed" or str(old["recorded_at"]) < str(record["recorded_at"]):
                choices[end] = saved
        except (OSError, ValueError, KeyError, TypeError):
            warnings.append("history_unavailable")
    if not choices or (period is not None and period not in choices):
        raise FileNotFoundError("no earnings for the selected period")
    selected = period or max(choices)
    view = choices[selected]
    if revision is not None:
        if revision not in revisions or (period and revisions[revision][0] != period):
            raise FileNotFoundError("analysis revision unavailable")
        selected, view = revisions[revision]
    bundle, narrative = view["bundle"], view["narrative"]
    comparison = view["comparison"] or history.build_comparison(bundle, cache_dir, narrative)
    # Report paths are only exposed when they resolve to a real report inside this project.
    report = view["report_path"]
    if not report and narrative:
        run_date = history.iso_date(bundle.get("as_of_date"))
        report = f"reports/{run_date}_{ticker}_earnings.md" if run_date else None
    if report:
        resolved = (root / report).resolve()
        if not resolved.is_relative_to((root / "reports").resolve()) or not resolved.is_file():
            report = None
        else:
            report = resolved.relative_to(root.resolve()).as_posix()
    pnl = bundle.get("quarterly_pnl") or []
    margins = (bundle.get("derived") or {}).get("margins_8q") or [
        {"date": q.get("date"), **{name: q[field] / q["revenue"]
          if history.number(q.get(field)) is not None and history.number(q.get("revenue")) not in (None, 0) else None
          for name, field in (("gross", "grossProfit"), ("operating", "operatingIncome"), ("net", "netIncome"))}}
        for q in pnl]
    return {"ticker": ticker, "infographic": narrative, "comparison": comparison,
            "view": {"selected_period": selected, "latest_period": max(choices), "revision": revision, "kind": view["kind"],
                     "narrative_available": bool(narrative), "warnings": sorted(set(warnings)),
                     "periods": [{"period_end": end, "fiscal_period": history.earnings_context(item["bundle"])["fiscal_period"],
                                  "recorded_at": item["recorded_at"], "kind": item["kind"]}
                                 for end, item in sorted(choices.items(), reverse=True)]},
            "cache": {**{k: bundle.get(k) for k in ("snapshot", "verdict", "composite_score", "score_components",
                                                    "quality_flags", "as_of_date", "last_earnings_date")},
                      "report_path": report,
                      "quarterly_pnl": [{k: q.get(k) for k in ("date", "period", "fiscalYear", "revenue", "netIncome", "eps", "epsDiluted")}
                                        for q in pnl[:8]],
                      "cash_flow": [{k: q.get(k) for k in ("date", "period", "operatingCashFlow", "freeCashFlow")}
                                    for q in (bundle.get("cash_flow") or [])[:8]], "margins_8q": margins[:8]}}
