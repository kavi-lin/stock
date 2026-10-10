"""Period-aware earnings comparisons and immutable completed analyses; no LLM/API calls."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from investment.scripts.run_data import atomic_json, digest, file_lock, safe_id, utcnow

VERSION = "earnings-history/1"
STATES = {"exceeded", "met", "missed", "pending", "unverifiable"}
BASIS_KEYS = ("metric", "unit", "currency", "accounting_basis", "fx_basis", "segment")
METRICS = {
    "revenue": ("營收", "quarterly_pnl", "revenue", "currency"),
    "eps_diluted": ("稀釋 EPS", "quarterly_pnl", "epsDiluted", "currency_per_share"),
    "gross_margin": ("毛利率", "quarterly_pnl", "grossProfit", "ratio"),
    "operating_margin": ("營業利益率", "quarterly_pnl", "operatingIncome", "ratio"),
    "free_cash_flow": ("自由現金流", "cash_flow", "freeCashFlow", "currency"),
}


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def iso_date(value):
    try:
        return date.fromisoformat(str(value)[:10]).isoformat()
    except (ValueError, TypeError):
        return None


def period(row):
    try:
        year, quarter = int(row.get("fiscalYear")), str(row.get("period"))
        if 1900 <= year <= 2200 and quarter in {"Q1", "Q2", "Q3", "Q4", "FY"}:
            return {"fiscal_year": year, "period": quarter}
    except (ValueError, TypeError):
        pass
    return None


def period_index(p):
    if not isinstance(p, dict):
        return None
    normalized = period({"fiscalYear": p.get("fiscal_year"), "period": p.get("period")})
    if normalized is None:
        return None
    return normalized["fiscal_year"] * 4 + (4 if normalized["period"] == "FY" else int(normalized["period"][1]))


def next_period(p):
    idx = period_index(p)
    if idx is None:
        return None
    return {"fiscal_year": idx // 4, "period": f"Q{idx % 4 + 1}"}


def period_label(p):
    if period_index(p) is None:
        return "期間不明"
    return f"FY{p['fiscal_year']} " + ("全年" if p["period"] == "FY" else p["period"])


def read_object(path):
    with Path(path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"not a JSON object: {path}")
    return value


def base_paths(cache_dir, ticker):
    safe_id(ticker)
    pattern = re.compile(re.escape(ticker) + r"_\d{4}-\d{2}-\d{2}\.json$")
    return sorted(p for p in Path(cache_dir).glob(f"{ticker}_*.json") if pattern.fullmatch(p.name))


def find_cache(cache_dir, ticker):
    paths = base_paths(cache_dir, ticker)
    return str(paths[-1]) if paths else None


def narrative_path(cache_path):
    path = Path(cache_path)
    return path.with_name(path.stem + ".infographic.json")


def source_ref(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def financial_source(bundle, row):
    filing_type = "10-K" if row.get("period") in {"Q4", "FY"} else "10-Q"
    return row.get("finalLink") or row.get("link") or (
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK="
        + bundle["ticker"] + "&type=" + filing_type)


def earnings_context(bundle):
    """A completed event must follow this fiscal end, match revenue, and be unique.

    Earnings APIs mix future calendar rows with actuals. Never take row zero,
    infer a release date from a fiscal end, or pair a stale financial quarter
    with a newer release. Without positive matching evidence, leave it unknown.
    """
    row = (bundle.get("quarterly_pnl") or [{}])[0]
    end = iso_date(row.get("date"))
    cutoff = iso_date(bundle.get("as_of_date")) or date.today().isoformat()
    candidates = []
    for event in bundle.get("earnings_surprises") or []:
        released = iso_date(event.get("date"))
        actual, revenue = number(event.get("revenueActual")), number(row.get("revenue"))
        if not end or not released or not (end <= released <= cutoff):
            continue
        if (date.fromisoformat(released) - date.fromisoformat(end)).days > 120:
            continue
        if actual is None or revenue is None or not math.isclose(actual, revenue, rel_tol=1e-6, abs_tol=1):
            continue
        candidates.append(event)
    unique = {iso_date(e["date"]): e for e in candidates}
    event = next(iter(unique.values())) if len(unique) == 1 else None
    surprise = {}
    for metric in ("revenue", "eps"):
        actual = number((event or {}).get(metric + "Actual"))
        estimated = number((event or {}).get(metric + "Estimated"))
        surprise.update({metric + "_actual": actual, metric + "_estimated": estimated,
                         metric + "_beat": actual > estimated if actual is not None and estimated is not None else None,
                         metric + "_surprise_pct": (actual - estimated) / abs(estimated)
                         if actual is not None and estimated is not None and estimated != 0 else None})
    return {"fiscal_period": period(row), "fiscal_period_end": end,
            "earnings_release_date": iso_date(event["date"]) if event else None,
            "event_match": "revenue_matched" if event else "unavailable_or_ambiguous",
            "completed_event": copy.deepcopy(event), "surprise": surprise}


def metric_actuals(bundle):
    """Align statements by date, never by position. EPS stays diluted GAAP."""
    result = []
    for row in bundle.get("quarterly_pnl") or []:
        target = period(row)
        if not target or not iso_date(row.get("date")):
            continue
        for metric, (_, table, field, unit) in METRICS.items():
            matches = [r for r in bundle.get(table) or [] if r.get("date") == row["date"]]
            raw = matches[0] if len(matches) == 1 else {}
            value = number(raw.get(field))
            if unit == "ratio":
                rev = number(row.get("revenue"))
                value = value / rev if value is not None and rev is not None and rev > 0 else None
            result.append({"metric": metric, "target_period": target, "value": value,
                           "period_end": row["date"], "unit": unit,
                           "currency": raw.get("reportedCurrency") if unit != "ratio" else None,
                           "accounting_basis": "gaap", "fx_basis": "reported", "segment": "consolidated",
                           "source_ref": financial_source(bundle, raw or row)})
    # FY totals require all four fiscal quarters and one currency. Annual EPS
    # is not a sum of quarterly diluted EPS (share denominators can differ).
    for year in sorted({r["target_period"]["fiscal_year"] for r in result}):
        for metric in METRICS:
            if metric == "eps_diluted":
                continue
            quarters = [r for r in result if r["metric"] == metric and r["target_period"]["fiscal_year"] == year]
            if len(quarters) != 4 or {r["target_period"]["period"] for r in quarters} != {"Q1", "Q2", "Q3", "Q4"}:
                continue
            if any(r["value"] is None for r in quarters) or len({r["currency"] for r in quarters}) != 1:
                continue
            value = sum(r["value"] for r in quarters)
            if quarters[0]["unit"] == "ratio":
                income = [r for r in bundle["quarterly_pnl"] if period(r) and period(r)["fiscal_year"] == year]
                revenue = [number(r.get("revenue")) for r in income]
                if len(income) != 4 or any(v is None for v in revenue) or sum(revenue) <= 0:
                    continue
                value = sum(r[METRICS[metric][2]] for r in income) / sum(revenue)
            result.append({**quarters[0], "target_period": {"fiscal_year": year, "period": "FY"},
                           "value": value, "period_end": max(r["period_end"] for r in quarters),
                           "aggregation": "four_fiscal_quarters"})
    return result


def valid_source(value):
    if not isinstance(value, str) or not value.strip():
        return False
    url = urlparse(value)
    return (url.scheme in {"https", "http"} and bool(url.netloc)
            and not url.username and not url.password
            and not any(re.search(r"key|token|secret|password", k, re.I) for k in parse_qs(url.query)))


def validate_items(items, *, observations=False):
    if not isinstance(items, list):
        return ["observed_metrics/expectations must be a list"]
    errors = []
    for i, item in enumerate(items):
        prefix = f"{'observed_metrics' if observations else 'expectations'}[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for key in BASIS_KEYS:
            if key not in item or (key != "currency" and not isinstance(item[key], str)):
                errors.append(f"{prefix}.{key} missing/invalid")
        if period_index(item.get("target_period")) is None:
            errors.append(f"{prefix}.target_period invalid")
        if item.get("unit") not in {"currency", "currency_per_share", "ratio", "number"}:
            errors.append(f"{prefix}.unit invalid")
        if item.get("accounting_basis") not in {"gaap", "non_gaap", "operational"}:
            errors.append(f"{prefix}.accounting_basis invalid")
        if item.get("fx_basis") not in {"reported", "constant_currency"}:
            errors.append(f"{prefix}.fx_basis invalid")
        if item.get("unit") in {"currency", "currency_per_share"} and not re.fullmatch(r"[A-Z]{3}", str(item.get("currency"))):
            errors.append(f"{prefix}.currency requires ISO currency")
        if not valid_source(item.get("source_ref")) or not item.get("source_quote") or not iso_date(item.get("published_at")):
            errors.append(f"{prefix} needs public source_ref, source_quote and published_at")
        if observations:
            if number(item.get("value")) is None:
                errors.append(f"{prefix}.value must be finite")
        else:
            if item.get("origin") not in {"management", "consensus", "analysis"}:
                errors.append(f"{prefix}.origin invalid")
            if not isinstance(item.get("statement"), str) or not item["statement"].strip():
                errors.append(f"{prefix}.statement required")
            op = item.get("operator")
            if op not in {"gte", "lte", "range", "qualitative"}:
                errors.append(f"{prefix}.operator invalid")
            if op in {"gte", "lte"} and number(item.get("threshold")) is None:
                errors.append(f"{prefix}.threshold must be finite")
            if op == "range":
                low, high = number(item.get("low")), number(item.get("high"))
                if low is None or high is None or low > high or item.get("better") not in {"higher", "lower", "within"}:
                    errors.append(f"{prefix}.range requires low <= high and better=higher/lower/within")
    return errors


def bind_expectations(items, recorded_at, original_ref, *, legacy=False):
    bound = []
    for item in items:
        e = copy.deepcopy(item)
        # IDs and record clocks are system-owned; model-supplied clocks cannot backdate a forecast.
        e["recorded_at"] = recorded_at
        e["original_ref"] = original_ref
        e["legacy_reconstructed"] = legacy
        e["expectation_id"] = digest({"item": item, "recorded_at": recorded_at, "source": original_ref})
        bound.append(e)
    return bound


def legacy_expectations(narrative, prior_period, ref):
    """Keep old forward-looking text visible; never invent a numeric pass criterion."""
    texts = [(str(h.get("title", "")) + "：" + str(h.get("body", ""))).strip("：")
             for h in narrative.get("key_highlights") or [] if isinstance(h, dict)]
    texts += [s for s in narrative.get("summary") or [] if isinstance(s, str)]
    out = []
    for text in dict.fromkeys(texts):
        if not re.search(r"\bguide\b|guidance|outlook|下季|下次|指引|展望", text, re.I):
            continue
        target = None
        fy = re.search(r"\bFY\s*(\d{4}|\d{2})\b", text, re.I)
        quarter = re.search(r"\bQ([1-4])\s+(?:guide|guidance|outlook)", text, re.I)
        if quarter and prior_period:
            q = int(quarter[1]); year = prior_period["fiscal_year"]
            if q <= int(prior_period["period"][1]):
                year += 1
            target = {"fiscal_year": year, "period": f"Q{q}"}
        elif fy:
            year = int(fy[1]); year = 2000 + year if year < 100 else year
            target = {"fiscal_year": year, "period": "FY"}
        if target is None and not re.search(r"next|下季|下次|full.year|全年|展望|raise|上調", text, re.I):
            continue  # "本季優於 guide" is a retrospective observation, not a future promise.
        out.append({"statement": text, "target_period": target, "operator": "qualitative",
                    "origin": "legacy", "source_ref": ref})
    return bind_expectations(out, narrative.get("as_of_date"), ref, legacy=True)


def choose_previous(bundle, cache_dir):
    """Latest different fiscal period; snapshots win over mutable legacy caches.

    Prefer a snapshot completed before the current release. No TTL applies to history.
    A legacy cache must have an actual narrative, not just background prewarming.
    """
    current = earnings_context(bundle)
    end = current["fiscal_period_end"]
    cutoff = current["earnings_release_date"]
    ticker = safe_id(bundle["ticker"])
    candidates, warnings = [], []
    for path in sorted((Path(cache_dir) / "history" / ticker).glob("*/*.json")):
        try:
            record = read_object(path)
            if record.get("schema_version") != VERSION or record.get("content_hash") != digest(record.get("content")):
                raise ValueError("history hash/schema mismatch")
            content = record["content"]
            if content["bundle"]["ticker"] != ticker:
                raise ValueError("history ticker mismatch")
            prior_end = earnings_context(content["bundle"])["fiscal_period_end"]
            if prior_end and end and prior_end < end:
                candidates.append({"period_end": prior_end, "recorded_at": record["recorded_at"],
                                   "bundle": content["bundle"], "narrative": content["narrative"],
                                   "expectations": content["open_expectations"], "source_ref": source_ref(path),
                                   "watchlist": content["comparison"]["next_watchlist"],
                                   "legacy": False})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            warnings.append(f"歷史版本不可用：{path.name} ({type(exc).__name__})")
    for path in base_paths(cache_dir, ticker):
        try:
            if not narrative_path(path).exists():
                continue
            prior = read_object(path); narrative = read_object(narrative_path(path))
            prior_end = earnings_context(prior)["fiscal_period_end"]
            if not prior_end or not end or prior_end >= end:
                continue
            if prior.get("ticker") != ticker or narrative.get("ticker") != ticker or narrative.get("last_earnings_date") != prior_end:
                raise ValueError("legacy identity mismatch")
            if not isinstance(prior.get("composite_score"), int):
                warnings.append(f"前次分析未完成：{path.name}")
                continue
            ref = source_ref(narrative_path(path))
            items = legacy_expectations(narrative, earnings_context(prior)["fiscal_period"], ref)
            candidates.append({"period_end": prior_end, "recorded_at": narrative.get("as_of_date"),
                               "bundle": prior, "narrative": narrative, "expectations": items,
                               "watchlist": [], "source_ref": ref, "legacy": True})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            warnings.append(f"前次快取不可用：{path.name} ({type(exc).__name__})")
    if not candidates:
        return None, warnings
    # A refreshed old-quarter cache can postdate the current release. Use earlier completed evidence if available.
    eligible = [c for c in candidates if cutoff and iso_date(c["recorded_at"]) and iso_date(c["recorded_at"]) < cutoff]
    pool = eligible or candidates
    latest_period = max(c["period_end"] for c in pool)
    pool = [c for c in pool if c["period_end"] == latest_period]
    frozen = [c for c in pool if not c["legacy"]]
    return max(frozen or pool, key=lambda c: c["recorded_at"] or ""), warnings


def actual_for(expectation, bundle, observed_metrics):
    target = expectation.get("target_period")
    rows = metric_actuals(bundle) + list(observed_metrics)
    rows = [r for r in rows if r.get("target_period") == target and r.get("metric") == expectation.get("metric")]
    matching = [r for r in rows if all(r.get(k) == expectation.get(k) for k in BASIS_KEYS)]
    values = {number(r.get("value")) for r in matching if number(r.get("value")) is not None}
    if len(values) > 1:
        return None, "conflicting_actuals"
    if len(values) == 1:
        return next(r for r in matching if number(r.get("value")) is not None), None
    return None, "basis_mismatch" if rows else "actual_unavailable"


def evaluate(expectation, bundle, observed_metrics):
    e = copy.deepcopy(expectation)
    result = {"expectation": e, "status": "unverifiable", "reason": None, "actual": None}
    context = earnings_context(bundle)
    target_idx, current_idx = period_index(e.get("target_period")), period_index(context["fiscal_period"])
    if target_idx is not None and current_idx is not None and target_idx > current_idx:
        result.update(status="pending", reason="target_not_reported")
        return result
    if e.get("legacy_reconstructed"):
        result["reason"] = "legacy_no_verifiable_contract"
        return result
    if target_idx is None or current_idx is None:
        result["reason"] = "target_period_unknown"
        return result
    if e.get("operator") == "qualitative":
        result["reason"] = "qualitative_no_numeric_criterion"
        return result
    errors = validate_items([e])
    if errors:
        result["reason"] = "invalid_expectation_contract"
        return result
    actual, reason = actual_for(e, bundle, observed_metrics)
    if actual is None:
        result["reason"] = reason
        return result
    result["actual"] = actual
    # Release cutoff for this target, not the latest quarter's release (carried FY goals).
    released = context["earnings_release_date"] if target_idx == current_idx else None
    if not released:
        release_period = dict(e["target_period"])
        if release_period["period"] == "FY":
            release_period["period"] = "Q4"
        target_rows = [r for r in bundle.get("quarterly_pnl") or [] if period(r) == release_period]
        if len(target_rows) == 1:
            released = earnings_context({**bundle, "quarterly_pnl": target_rows})["earnings_release_date"]
    recorded, published = iso_date(e.get("recorded_at")), iso_date(e.get("published_at"))
    if not released:
        result["reason"] = "release_date_unavailable"
        return result
    if not recorded or not published or max(recorded, published) >= released:
        result["reason"] = "not_recorded_before_release"
        return result
    value, op = actual["value"], e["operator"]
    if op == "range":
        low, high = e["low"], e["high"]
        status = "met" if low <= value <= high else "missed"
        if (e["better"] == "higher" and value > high) or (e["better"] == "lower" and value < low):
            status = "exceeded"
    else:
        delta = value - e["threshold"]
        status = "met" if math.isclose(delta, 0, abs_tol=1e-10) else (
            "exceeded" if (delta > 0 if op == "gte" else delta < 0) else "missed")
    result.update(status=status, reason="same_period_same_basis")
    return result


def financial_comparison(bundle):
    context = earnings_context(bundle)
    current = context["fiscal_period"]
    idx = period_index(current)
    actuals = metric_actuals(bundle)
    rows = []
    for metric, (label, _, _, unit) in METRICS.items():
        def at(index):
            found = [r for r in actuals if r["metric"] == metric and r["target_period"]["period"] != "FY"
                     and period_index(r["target_period"]) == index]
            return found[0] if len(found) == 1 else None
        cur = at(idx); prior = at(idx - 1) if idx is not None else None; year = at(idx - 4) if idx is not None else None
        def change(other):
            if not cur or not other or cur["value"] is None or other["value"] is None:
                return {"delta": None, "pct": None, "reason": "missing_period_or_value"}
            if cur["currency"] != other["currency"]:
                return {"delta": None, "pct": None, "reason": "currency_mismatch"}
            delta = cur["value"] - other["value"]
            return {"delta": delta, "pct": delta / other["value"] if unit != "ratio" and other["value"] > 0 else None,
                    "reason": "legacy_currency_unspecified" if unit != "ratio" and cur["currency"] is None else None}
        rows.append({"metric": metric, "label": label, "unit": unit, "current": cur, "previous_quarter": prior,
                     "year_ago": year, "qoq": change(prior), "yoy": change(year)})
    return rows


def review_watchlist(watchlist, bundle):
    """Track prior observation baselines without turning them into predictions."""
    rows = []
    for watch in watchlist:
        baseline = watch.get("baseline") or {}
        e = {**baseline, "metric": watch["metric"], "target_period": watch.get("target_period")}
        actual, reason = actual_for(e, bundle, [])
        delta = None
        if actual and number(baseline.get("value")) is not None:
            delta = actual["value"] - baseline["value"]
        rows.append({"watch": watch, "actual": actual, "delta": delta,
                     "direction": "unavailable" if delta is None else "up" if delta > 0 else "down" if delta < 0 else "flat",
                     "reason": reason, "counts_as_prediction": False})
    return rows


def build_comparison(bundle, cache_dir, narrative=None):
    narrative = narrative or {}
    previous, warnings = choose_previous(bundle, cache_dir)
    observed = narrative.get("observed_metrics") or []
    audits = [evaluate(e, bundle, observed) for e in previous["expectations"]] if previous else []
    cur_idx = period_index(earnings_context(bundle)["fiscal_period"])
    old_idx = period_index(earnings_context(previous["bundle"])["fiscal_period"]) if previous else None
    before = set(previous["bundle"].get("quality_flags") or []) if previous else set()
    after = set(bundle.get("quality_flags") or [])
    unresolved_flags = before & {"accruals_warning"} if "accruals_warning" not in after else set()
    if unresolved_flags:
        warnings.append("前次 accruals_warning 採舊版定義，本次已分拆為不同現金轉換警訊；不列為已解除。")
    watchlist = [{"statement": f"追蹤下季{label}相較本季的變化（觀察項目，非公司指引）",
                  "metric": metric, "target_period": next_period(earnings_context(bundle)["fiscal_period"]),
                  "baseline": row["current"], "kind": "observation_only"}
                 for row in financial_comparison(bundle)
                 for metric, (label, _, _, _) in METRICS.items() if row["metric"] == metric][:5]
    return {"schema_version": VERSION, "context": earnings_context(bundle),
            "previous_analysis": {"status": "available", "period_end": previous["period_end"],
                                  "fiscal_period": earnings_context(previous["bundle"])["fiscal_period"],
                                  "recorded_at": previous["recorded_at"], "source_ref": previous["source_ref"],
                                  "legacy": previous["legacy"],
                                  "quarters_apart": cur_idx - old_idx if cur_idx is not None and old_idx is not None else None}
                                 if previous else {"status": "no_previous_analysis"},
            "financial_changes": financial_comparison(bundle),
            "quality_flag_changes": {"available": previous is not None, "new": sorted(after - before),
                                     "continuing": sorted(after & before), "resolved": sorted(before - after - unresolved_flags),
                                     "definition_changed": sorted(unresolved_flags)},
            "expectation_audit": audits, "observed_metrics": observed,
            "watch_audit": review_watchlist(previous["watchlist"], bundle) if previous else [],
            "next_expectations": copy.deepcopy(narrative.get("expectations") or []),
            "next_watchlist": watchlist, "warnings": warnings}


def validate_comparison(comparison, bundle):
    if not isinstance(comparison, dict) or comparison.get("schema_version") != VERSION:
        return ["comparison.schema_version invalid"]
    errors = []
    if comparison.get("context") != earnings_context(bundle):
        errors.append("comparison.context differs from current fiscal/event data")
    if comparison.get("financial_changes") != financial_comparison(bundle):
        errors.append("comparison.financial_changes differs from deterministic calculation")
    observed = comparison.get("observed_metrics") or []
    errors.extend(validate_items(observed, observations=True))
    errors.extend(validate_items(comparison.get("next_expectations") or []))
    audits = comparison.get("expectation_audit")
    if not isinstance(audits, list):
        errors.append("comparison.expectation_audit must be a list")
    else:
        for i, row in enumerate(audits):
            if not isinstance(row, dict) or not isinstance(row.get("expectation"), dict):
                errors.append(f"comparison.expectation_audit[{i}] malformed")
            elif row != evaluate(row["expectation"], bundle, observed):
                errors.append(f"comparison.expectation_audit[{i}] differs from deterministic evaluation")
    watches = comparison.get("watch_audit")
    if not isinstance(watches, list):
        errors.append("comparison.watch_audit must be a list")
    elif watches != review_watchlist([r["watch"] for r in watches], bundle):
        errors.append("comparison.watch_audit differs from deterministic observation review")
    return errors


def snapshot_bundle(bundle):
    return {k: copy.deepcopy(bundle.get(k)) for k in (
        "ticker", "as_of_date", "last_earnings_date", "quarterly_pnl", "cash_flow", "balance_sheet",
        "earnings_surprises", "quality_flags", "composite_score", "score_components", "verdict")}


def save_snapshot(bundle, narrative, comparison, cache_dir, report_path):
    """Append-only, content-addressed successful runs. Same inputs are idempotent."""
    slim = snapshot_bundle(bundle)
    report_bytes = Path(report_path).read_bytes()
    content_input = {"bundle": slim, "narrative": narrative, "comparison": comparison,
                     "report_path": source_ref(report_path), "report_sha256": hashlib.sha256(report_bytes).hexdigest()}
    identifier = digest(content_input).split(":")[1]
    end = earnings_context(bundle)["fiscal_period_end"]
    if not end:
        raise ValueError("cannot save analysis without a fiscal period end")
    folder = Path(cache_dir) / "history" / safe_id(bundle["ticker"]) / end
    path = folder / f"{identifier}.json"
    with file_lock(folder / ".write.lock"):
        if path.exists():
            existing = read_object(path)
            if existing.get("content_hash") != digest(existing.get("content")):
                raise ValueError("existing history snapshot hash mismatch")
            return path
        recorded = utcnow()
        own = bind_expectations(narrative.get("expectations") or [], recorded, source_ref(path))
        carry = [row["expectation"] for row in comparison["expectation_audit"] if row["status"] in {"pending", "unverifiable"}]
        content = {**content_input, "open_expectations": carry + own}
        # Keep legacy text visible in future runs even before a structured narrator has been used.
        if not own and "expectations" not in narrative:
            content["open_expectations"] += legacy_expectations(narrative, comparison["context"]["fiscal_period"], source_ref(path))
        archive = Path(report_path).parent / "earnings_history" / safe_id(bundle["ticker"]) / end / f"{identifier}.md"
        archive.parent.mkdir(parents=True, exist_ok=True)
        if archive.exists() and archive.read_bytes() != report_bytes:
            raise ValueError("archived report content mismatch")
        if not archive.exists():
            archive.write_bytes(report_bytes)
        content["report_archive"] = source_ref(archive)
        atomic_json(path, {"schema_version": VERSION, "recorded_at": recorded,
                           "content_hash": digest(content), "content": content})
    return path


def validate_completion(bundle, cache_dir, narrative=None):
    """Post-run gate: completed snapshot must describe these inputs and this report."""
    try:
        path = Path(bundle["comparison_snapshot"]).resolve()
        history_root = (Path(cache_dir) / "history" / safe_id(bundle["ticker"])).resolve()
        if not path.is_relative_to(history_root):
            return ["completed snapshot outside this ticker's history"]
        record = read_object(path); content = record["content"]
        if record.get("schema_version") != VERSION or record.get("content_hash") != digest(content):
            return ["completed snapshot hash/schema mismatch"]
        if content["bundle"] != snapshot_bundle(bundle) or content["comparison"] != bundle.get("comparison"):
            return ["completed snapshot differs from current cache; rerun render"]
        if narrative is not None and content["narrative"] != narrative:
            return ["completed snapshot differs from current infographic; rerun render"]
        for key in ("report_path", "report_archive"):
            report = Path(content[key])
            if not report.is_absolute():
                report = ROOT / report
            if hashlib.sha256(report.read_bytes()).hexdigest() != content["report_sha256"]:
                return ["completed report changed after snapshot; rerun render"]
    except (OSError, KeyError, ValueError, TypeError):
        return ["completed earnings history/report missing or invalid; run render first"]
    return []
