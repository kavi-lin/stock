#!/usr/bin/env python3
"""Offline health, clustered Red Team calibration and strategy proposals. Never activates changes."""
from __future__ import annotations

import argparse
import collections
import copy
import math
import random
import statistics
import sys
from pathlib import Path

from run_data import ROOT, RUNS, atomic_json, read_json, utcnow


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def percentile(values, q):
    values = sorted(v for v in values if finite(v))
    if not values:
        return None
    i = (len(values) - 1) * q
    lo, hi = math.floor(i), math.ceil(i)
    return values[lo] * (hi - i) + values[hi] * (i - lo) if hi != lo else values[lo]


def health(runs=RUNS):
    stages, errors, caps = collections.defaultdict(list), [], collections.Counter()
    coverage, count, committed, raw_committed = 0, 0, 0, 0
    invalid_runs = 0
    fmp_rows = []
    for path in Path(runs).glob("*/manifest.json"):
        try:
            m = read_json(path)
            if m.get("offline_fixture"):
                continue
            count += 1
            raw_committed += m.get("status") == "committed"
            fmp_rows.extend(v for v in (m.get("telemetry", {}).get("fmp") or {}).values() if isinstance(v, dict))
            for name, stage in m["stages"].items():
                stages[name].append(stage)
            from run_investment import _load
            try:
                _load(path.parent.name)
            except (ValueError, KeyError, OSError) as exc:
                invalid_runs += 1
                errors.append({"path": str(path), "error": "run_evidence_failed", "details": [str(exc)]})
                continue
            session = path.parent / "session.json"
            if session.exists():
                entry = read_json(session)
                from run_exports import check
                from append_session_export import _valid_provenance
                evidence_errors = []
                check(entry, evidence_errors)
                if not _valid_provenance(entry):
                    evidence_errors.append("invalid export provenance")
                if evidence_errors:
                    invalid_runs += 1
                    errors.append({"path": str(path), "error": "post_run_evidence_failed", "details": evidence_errors})
                    continue
                if m.get("status") == "committed":
                    committed += 1
                t = entry["trades_this_session"][0]
                coverage += finite((t.get("sentiment_det") or {}).get("score"))
                if t.get("decision_cap_active"):
                    caps[str(t.get("decision_cap_reason"))] += 1
        except (ValueError, KeyError, OSError) as exc:
            errors.append({"path": str(path), "error": str(exc)})
    result = {}
    for name, rows in stages.items():
        times = [r.get("elapsed_seconds") for r in rows]
        result[name] = {"n": len(rows), "timed_n": sum(finite(v) for v in times),
                        "p50_seconds": percentile(times, .5), "p95_seconds": percentile(times, .95),
                        "queue_p50_seconds": percentile([r.get("queued_seconds") for r in rows], .5),
                        "queue_p95_seconds": percentile([r.get("queued_seconds") for r in rows], .95),
                        "retries": sum(max(0, r.get("attempts", 0) - 1) for r in rows),
                        "degraded_rate": sum(r["status"] == "degraded" for r in rows) / len(rows),
                        "validation_failure_rate": sum(r.get("failure_kind") == "schema" for r in rows) / len(rows),
                        "tokens": {key: {"known_n": sum(finite((r.get("tokens") or {}).get(key)) for r in rows),
                                          "known_sum": sum((r.get("tokens") or {}).get(key) for r in rows if finite((r.get("tokens") or {}).get(key))),
                                          "unknown_n": sum(not finite((r.get("tokens") or {}).get(key)) for r in rows)}
                                   for key in ("input", "output", "cached")}}
    host_jobs = []
    if Path(runs) == RUNS:
        for path in (ROOT / "investment/scan_logs").glob("*.telemetry.json"):
            try:
                job = read_json(path)
                if job.get("runner") == "v55" and job.get("protocol") == "invest":
                    host_jobs.append(job)
            except (ValueError, OSError) as exc:
                errors.append({"path": str(path), "error": str(exc)})
    called = [j for j in host_jobs if j.get("model_called")]
    return {"version": "investment-health/1.0", "generated_at": utcnow(), "runs": count,
            "committed": committed, "raw_committed": raw_committed,
            "invalid_evidence_runs": invalid_runs,
            "evidence_failure_rate": invalid_runs / count if count else None,
            "completion_rate": committed / count if count else None,
            "host_jobs": {"attempts": len(host_jobs), "model_calls": len(called),
                          "complete": sum(j.get("status") == "complete" and j.get("accepted_for_pilot", True) for j in called),
                          "completion_rate": sum(j.get("status") == "complete" and j.get("accepted_for_pilot", True) for j in called) / len(called) if called else None,
                          "queue_p50_seconds": percentile([j.get("queued_seconds") for j in host_jobs], .5),
                          "queue_p95_seconds": percentile([j.get("queued_seconds") for j in host_jobs], .95),
                          "elapsed_p50_seconds": percentile([j.get("elapsed_seconds") for j in called], .5),
                          "elapsed_p95_seconds": percentile([j.get("elapsed_seconds") for j in called], .95),
                          "tokens": {key: {"known_sum": sum((j.get("tokens") or {})[key] for j in called if finite((j.get("tokens") or {}).get(key))),
                                            "unknown_n": sum(not finite((j.get("tokens") or {}).get(key)) for j in called)}
                                     for key in ("input", "output", "cached")},
                          "token_scope": "host receipts; not added to lane receipts to avoid double counting",
                          "jobs": host_jobs},
            "stages": result, "shadow_coverage": {"valid": coverage, "total": count},
            "fmp": {key: {"known_sum": sum(row[key] for row in fmp_rows if finite(row.get(key))),
                           "known_n": sum(finite(row.get(key)) for row in fmp_rows),
                           "unknown_n": sum(not finite(row.get(key)) for row in fmp_rows)}
                    for key in ("requests", "cache_hits", "http_calls_known", "http_calls_unknown")},
            "decision_caps": dict(caps), "errors": errors,
            "rollout": {"pilot_target": 5, "observation_target": 20, "automatic_activation": False}}


def cluster_summary(rows, metric):
    clusters = collections.defaultdict(list)
    for row in rows:
        val = row.get(metric)
        if finite(val):
            clusters[row["ticker"]].append(val)
    means = [statistics.mean(v) for v in clusters.values()]
    counts = [len(v) for v in clusters.values()]
    ci = None
    if len(means) > 1:
        rng = random.Random(55)
        draws = [statistics.mean(rng.choices(means, k=len(means))) for _ in range(1000)]
        ci = [percentile(draws, .025), percentile(draws, .975)]
    return {"observations": sum(counts), "independent_tickers": len(means),
            "max_ticker_share": max(counts) / sum(counts) if counts else None,
            "ticker_weighted_mean": statistics.mean(means) if means else None,
            "cluster_bootstrap_95ci": ci}


def calibrate(index):
    eligible, excluded = [], collections.Counter()
    for record in index.get("decisions", []):
        if record.get("source") != "deep-dive":
            continue
        dc = record.get("decision_content") or {}
        evaluation = record.get("evaluation") or {}
        if not evaluation.get("calibration_eligible"):
            excluded["incomplete_or_unverified"] += 1
            continue
        if dc.get("red_team_synthetic") or dc.get("red_team_execution_failed"):
            excluded["synthetic_red_team"] += 1
            continue
        if dc.get("execution_quality") != "complete":
            excluded["execution_not_complete"] += 1
            continue
        price = (record.get("reality_at_eval") or {}).get("ticker_reality") or {}
        if not all(finite(price.get(k)) for k in ("return_pct", "max_drawdown_pct")):
            excluded["nonfinite_prices"] += 1
            continue
        classification = record.get("classification") or {}
        conditions = (record.get("reality_at_eval") or {}).get("trade_condition_evaluation") or {}
        eligible.append({"decision_id": record["decision_id"], "ticker": record["tickers"][0],
                         "return_pct": price["return_pct"], "max_drawdown_pct": price["max_drawdown_pct"],
                         "verdict": dc.get("red_team_verdict"), "strength": dc.get("red_team_counter_evidence_strength"),
                         "basis": dc.get("red_team_basis"), "model": (record.get("models") or {}).get("red_team"),
                         "regime": classification.get("regime"), "industry": classification.get("industry"),
                         "execution_quality": dc.get("execution_quality"),
                         "directional_outcome_label": (record.get("verdict") or {}).get("label"),
                         "trade_condition_evaluation": conditions,
                         "trade_condition_label": ("unknown" if not conditions or any(conditions.get(k) is None for k in ("entry_price_touched", "take_profit_touched", "stop_loss_touched")) else
                             ";".join(f"{k}={conditions[k]}" for k in ("entry_price_touched", "take_profit_touched", "stop_loss_touched"))),
                         "kill_condition_evaluation": dc.get("kill_condition_evaluation") or {"status": "unknown"}})
        for key in ("entry_price_touched", "take_profit_touched", "stop_loss_touched"):
            value = conditions.get(key)
            eligible[-1][key] = int(value) if type(value) is bool else None
    groups = {}
    for dimension in ("verdict", "strength", "basis", "model", "regime", "industry", "execution_quality", "trade_condition_label"):
        buckets = collections.defaultdict(list)
        for row in eligible:
            buckets[str(row.get(dimension) or "unknown")].append(row)
        groups[dimension] = {key: {metric: cluster_summary(rows, metric) for metric in (
            "return_pct", "max_drawdown_pct", "entry_price_touched", "take_profit_touched", "stop_loss_touched")}
                             for key, rows in buckets.items()}
    return {"version": "red-team-calibration/1.0", "shadow_only": True,
            "eligible_n": len(eligible), "excluded": dict(excluded), "groups": groups, "samples": eligible,
            "thesis_rule": "Kill conditions require event evidence; returns alone leave status unknown.",
            "touch_rate_method": "Ticker-weighted daily-close touch rates; unknown excluded per metric; no intraday order or execution inference."}


def final_replay(directory, p3, decision):
    """Replay existing sizing and Phase 4.6 so proposals compare final decisions."""
    from trade_plan_builder import run_phase4
    from build_session_export import final_governance
    p4 = copy.deepcopy(read_json(directory / "p4_input.json"))
    p4["final_decision"] = decision["final_decision"]
    for key in ("position_size_cap_pct", "polar_position_cap_pct", "hot_zone_probe"):
        if key in decision:
            p4.setdefault("phase3", {})[key] = decision[key]
    plan = run_phase4(p4, use_subprocess=False)
    return final_governance({"engine": decision, "plan": plan, "p3": p3,
                             "quant": read_json(directory / "quant.json")})


def strategy_proposals(runs=RUNS):
    from decision_engine import run_phase3
    from run_investment import _load
    samples, exclusions, rt_samples = [], [], []
    models = collections.Counter()
    for path in Path(runs).glob("*/manifest.json"):
        try:
            d, m, _ = _load(path.parent.name)
            if m["status"] != "committed":
                continue
            t = read_json(d / "session.json")["trades_this_session"][0]
            from run_exports import check
            evidence_errors = []
            check(read_json(d / "session.json"), evidence_errors)
            if evidence_errors:
                raise ValueError("; ".join(evidence_errors))
            score = (t.get("sentiment_det") or {}).get("score")
            original = read_json(d / "p3_input.json")
            before = run_phase3(original)
            final_before = final_replay(d, original, before)
            for multiplier in (.95, 1.0):
                after = replay_penalty(original, multiplier)
                final_after = final_replay(d, original, after)
                rt_samples.append({"run_id": m["run_id"], "ticker": m["ticker"],
                                   "proposed_strong_counter_multiplier": multiplier,
                                   "synthetic": bool(t.get("red_team_synthetic")),
                                   "decision_before": final_before["final_decision"], "decision_after": final_after["final_decision"],
                                   "position_before": final_before["position_size_pct"], "position_after": final_after["position_size_pct"],
                                   "score_before": before["final_score"], "score_after": after["final_score"]})
            llm = original.get("lane_scores", {}).get("sentiment")
            if not finite(score) or not finite(llm):
                exclusions.append({"run_id": m["run_id"], "reason": "missing_sentiment_score"})
                continue
            shadow = copy.deepcopy(original)
            shadow["lane_scores"]["sentiment"] = score
            before, after = run_phase3(original), run_phase3(shadow)
            final_after = final_replay(d, shadow, after)
            models[str(m["stages"]["sentiment"].get("model"))] += 1
            samples.append({"run_id": m["run_id"], "ticker": m["ticker"],
                            "direction_flip": (score > 0) != (llm > 0) if score and llm else False,
                            "llm_score": llm, "det_score": score,
                            "decision_before": final_before["final_decision"], "decision_after": final_after["final_decision"],
                            "confidence_before": final_before["avg_confidence"], "confidence_after": final_after["avg_confidence"],
                            "position_before": final_before["position_size_pct"], "position_after": final_after["position_size_pct"],
                            "score_before": before.get("final_score"), "score_after": after.get("final_score")})
        except (ValueError, OSError, KeyError, SystemExit) as exc:
            exclusions.append({"run_id": path.parent.name, "reason": str(exc)})
    n = len(samples)
    flips = sum(s["direction_flip"] for s in samples)
    return {"version": "strategy-proposals/1.0", "automatic_activation": False, "approval_required": True,
            "sentiment": {"n": n, "direction_flip_rate": flips / n if n else None,
                          "existing_threshold_met": n >= 20 and flips / n < .2,
                          "model_distribution": dict(models), "missing_or_invalid": exclusions,
                          "affected_runs": samples},
            "candidates": [
                {"name": "retain_current_strategy", "status": "current"},
                {"name": "deterministic_sentiment", "status": "proposal_only", "replay": "sentiment"},
                {"name": "red_team_penalty", "status": "proposal_only_requires_complete_window_evidence",
                 "candidates": ["uniform STRONG_COUNTER multiplier 0.95", "no numeric penalty (1.0); verdict gates retained"],
                 "affected_runs": rt_samples},
                {"name": "synthetic_failure_semantics", "status": "label_only_no_decision_change"}],
            "valuation_lane_omission": "shadow_only"}


def replay_penalty(original, multiplier):
    """Isolated module namespace; the live decision engine is never patched."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("shadow_penalty_engine", ROOT / "investment/scripts/decision_engine.py")
    shadow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shadow)
    original_step = shadow.compute_step2
    def candidate(raw_total, *args, **kwargs):
        result = original_step(raw_total, *args, **kwargs)
        if result.get("penalty_applied"):
            result.update(penalty_value=multiplier, raw_after_bonus=raw_total * multiplier)
        return result
    shadow.compute_step2 = candidate
    return shadow.run_phase3(copy.deepcopy(original))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", default=str(ROOT / "reports/decision_review/event_index_latest.json"))
    p.add_argument("--out", default=str(ROOT / "reports/decision_review/investment_process_health.json"))
    args = p.parse_args()
    index = read_json(args.index)
    result = {"health": health(), "red_team": calibrate(index), "strategy_proposals": strategy_proposals()}
    atomic_json(args.out, result)
    print(f"wrote {args.out}; runs={result['health']['runs']}; eligible RT={result['red_team']['eligible_n']}")


if __name__ == "__main__":
    main()
