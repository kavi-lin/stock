"""Committed JSON is the authority; historical labels never read today's heat."""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "investment/scripts"))
from append_session_export import _valid_provenance, entry_digest
from run_data import digest

LANES = ("fundamentals", "sentiment", "news", "technical", "valuation")


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def scalar_price(value):
    if isinstance(value, str):
        try:
            value = float(value.replace("$", "").replace(",", "").strip())
        except ValueError:
            return None
    return value if finite(value) and value > 0 else None


def from_entry(entry, location):
    is_summary = not entry.get("trades_this_session")
    trade = ({**(entry.get("metadata") or {}), **entry} if is_summary else entry["trades_this_session"][0])
    ticker = trade.get("ticker") or entry.get("ticker")
    date = entry.get("export_date") or entry.get("date")
    ctx = entry.get("run_context") or {}
    identity = ctx.get("run_id") or (entry.get("export_provenance") or {}).get("entry_digest")
    identity = identity or digest({"entry": entry, "source": location})
    agents = []
    for lane in LANES:
        block = trade.get(lane + "_lane") or {}
        score = (trade.get("lane_scores") or {}).get(lane, block.get("score"))
        if finite(score):
            a = {"agent": lane.title(), "score": score, "signal": block.get("signal")}
            if finite(block.get("confidence")):
                a["confidence"] = block["confidence"]
            agents.append(a)
    method = "score_x_confidence" if agents and all("confidence" in a for a in agents) else "abs_score_only"
    decisive = max(agents, key=lambda a: abs(a["score"] * (a["confidence"] if method == "score_x_confidence" else 1)))["agent"] if agents else None
    classification = copy.deepcopy(ctx.get("classification") or {})
    macro = entry.get("phase0_macro_snapshot") or {}
    classification.setdefault("regime", macro.get("market_regime"))
    for key in ("sector", "industry", "data_as_of"):
        classification.setdefault(key, None)
    dc = {k: copy.deepcopy(trade.get(k)) for k in (
        "final_score", "final_decision", "final_action", "position_size_pct", "analysis_price",
        "decision_cap_active", "decision_cap_reason", "hot_zone_probe", "hot_zone_eval",
        "red_team_verdict", "red_team_counter_evidence_strength", "red_team_thesis_break_probability",
        "red_team_execution_failed", "red_team_synthetic", "red_team_kill_conditions",
        "execution_quality", "kill_condition_evaluation", "sentiment_det", "det_inputs", "lane_contract",
        "burry_score", "risk_reward_ratio", "entry_aggressive", "entry_conservative", "calculation_steps", "risk_audit",
        "technical_lane", "red_team_counter_thesis", "phase2_fanout_mode", "degraded_analysts")}
    dc.update(final_action_modifier=trade.get("final_action"),
              position_size=trade.get("position_size_pct"), macro_regime=classification["regime"],
              macro_multiplier=trade.get("macro_multiplier"),
              trader_proposal={"entry": scalar_price(trade.get("entry_reference_price", trade.get("entry_aggressive"))),
                               "tp": scalar_price(trade.get("take_profit")), "sl": scalar_price(trade.get("stop_loss"))},
              trader_proposal_raw={"entry": trade.get("entry_aggressive"), "tp": trade.get("take_profit"), "sl": trade.get("stop_loss")},
              trader_proposal_method="explicit_scalar_only; range or conditional entry remains unknown",
              red_team_basis=(trade.get("det_shadow") or {}).get("red_team_basis"))
    if dc["execution_quality"] is None:
        failed = bool(trade.get("red_team_execution_failed") or trade.get("phase2_fanout_mode") == "FULL_FALLBACK")
        dc["red_team_synthetic"] = failed
        dc["execution_quality"] = ("incomplete" if failed else "degraded" if trade.get("degraded_analysts") else
                                   "complete" if trade.get("phase2_fanout_mode") == "PARALLEL_SUBAGENT" else "unknown")
        dc["execution_quality_method"] = "legacy_execution_fields"
    return {"source": "deep-dive", "decision_id": identity, "decision_date": date,
            "legacy_ids": [f"deep-dive_{ticker}_{date}"], "scope": "ticker", "tickers": [ticker],
            "raw_path": location, "authority": "committed_json", "provenance_digest": entry_digest(entry),
            "summary": f"{ticker}: {dc['final_decision']} / {dc['final_action']}",
            "decision_content": dc, "agent_breakdown": agents, "classification": classification,
            "original_label": copy.deepcopy(trade.get("last_outcome") or entry.get("last_outcome")),
            "tuning_hooks": {"decisive_agent": decisive, "decisive_agent_method": method,
                             "macro_regime": classification["regime"], "macro_regime_source": "committed_json",
                             "sub_industry_heat": {"ticker_sector": classification["sector"],
                                                   "ticker_industry": classification["industry"],
                                                   "industry_top_30pct": None}},
            "models": {n: s.get("model") for n, s in ctx.get("stages", {}).items()},
            "identity_ambiguous": False, "needs_legacy_supplement": is_summary}


def supplement_legacy(record, candidates):
    """Only fill gaps in old committed summaries; never override JSON values."""
    if not record.get("needs_legacy_supplement"):
        return record
    matches = [row for row in candidates if row.get("decision_date") == record["decision_date"]
               and row.get("tickers") == record["tickers"]]
    if len(matches) != 1:
        record["legacy_supplement_status"] = "ambiguous" if matches else "missing"
        record["identity_ambiguous"] = bool(matches)
        return record
    other = matches[0]
    content = record["decision_content"]
    filled = []
    for key, value in other.get("decision_content", {}).items():
        if content.get(key) is None and value is not None:
            content[key] = copy.deepcopy(value)
            filled.append(key)
    if not record["agent_breakdown"]:
        record["agent_breakdown"] = copy.deepcopy(other.get("agent_breakdown") or [])
        for key in ("decisive_agent", "decisive_agent_method"):
            record["tuning_hooks"][key] = other.get("tuning_hooks", {}).get(key)
    if record["classification"].get("regime") is None:
        record["classification"]["regime"] = content.get("macro_regime")
        record["tuning_hooks"]["macro_regime"] = content.get("macro_regime")
        record["tuning_hooks"]["macro_regime_source"] = other.get("tuning_hooks", {}).get("macro_regime_source")
    record["legacy_supplement_status"] = "filled_gaps_only"
    record["legacy_supplement"] = {"path": other.get("raw_path"), "fields": filled}
    return record


def load_committed(path=None):
    path = Path(path or ROOT / "investment/invest_logs/history.json")
    entries = json.loads(path.read_text())
    if not isinstance(entries, list):
        raise ValueError("committed history must be an array")
    records, diagnostics, covered = [], [], set()
    seen = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        trade = (entry.get("trades_this_session") or [{}])[0]
        key = (entry.get("export_date") or entry.get("date"), trade.get("ticker") or entry.get("ticker"))
        covered.add(key)
        prov = entry.get("export_provenance")
        if prov is not None and not _valid_provenance(entry):
            diagnostics.append({"index": index, "reason": "provenance_mismatch", "key": key})
            continue
        if prov is None and str(key[0]) >= "2026-08-09":
            diagnostics.append({"index": index, "reason": "missing_provenance", "key": key})
            continue
        if entry.get("session_export_version") == "V5.5":
            from run_exports import check
            evidence_errors = []
            check(entry, evidence_errors)
            if evidence_errors:
                diagnostics.append({"index": index, "reason": "run_evidence_mismatch", "key": key,
                                    "run_id": (entry.get("run_context") or {}).get("run_id"), "errors": evidence_errors})
                continue
        rec = from_entry(entry, str(path) + f"#{index}")
        prior = seen.get(rec["decision_id"])
        if prior:
            if prior["provenance_digest"] == rec["provenance_digest"]:
                continue
            prior["identity_ambiguous"] = rec["identity_ambiguous"] = True
            diagnostics.append({"decision_id": rec["decision_id"], "reason": "identity_conflict"})
            rec["decision_id"] += ":conflict:" + rec["provenance_digest"]
        seen[rec["decision_id"]] = rec
        records.append(rec)
    return records, diagnostics, covered


def resolve_record(records, *, decision_id=None, date=None, ticker=None):
    matches = [r for r in records if (r["decision_id"] == decision_id if decision_id else
               r["decision_date"] == date and ticker in r.get("tickers", []))]
    if len(matches) != 1 or matches[0].get("identity_ambiguous"):
        raise ValueError("decision lookup absent or ambiguous; use a verified run_id/digest")
    return matches[0]


def preserve_evaluations(records, previous, directory, today):
    """Immutable evaluation sidecars; preserve old labels without reclassifying history."""
    from run_data import atomic_json
    directory = Path(directory)
    previous_rows = (previous or {}).get("decisions", [])
    legacy_map = {}
    for record in records:
        for old_id in record.get("legacy_ids", []):
            legacy_map.setdefault(old_id, []).append(record["decision_id"])
    for record in records:
        if record.get("source") != "deep-dive":
            continue
        record["prior_evaluations"] = [copy.deepcopy(r.get("verdict")) for r in previous_rows
            if r.get("decision_id") == record["decision_id"] or
            (r.get("decision_id") in record.get("legacy_ids", []) and len(legacy_map.get(r["decision_id"], [])) == 1)]
        evaluation = {"decision_id": record["decision_id"], "evaluation": record.get("evaluation"),
                      "reality": record.get("reality_at_eval"), "verdict": record.get("verdict"),
                      "original_label": record.get("original_label"), "prior_evaluations": record["prior_evaluations"]}
        path = directory / (digest(evaluation).split(":")[1] + ".json")
        if not path.exists():
            atomic_json(path, evaluation)
    return {"legacy_to_stable": legacy_map,
            "ambiguous_legacy_ids": {k: v for k, v in legacy_map.items() if len(v) > 1}}


def evaluation_metadata(record, reality, *, today):
    prices = (reality or {}).get("ticker_reality") or {}
    reasons = []
    if record.get("identity_ambiguous"):
        reasons.append("identity_ambiguous")
    if reality.get("pending") or reality.get("window_complete_pct") != 100 or not prices.get("price_window_complete"):
        reasons.append("window_incomplete")
    if not all(finite(prices.get(k)) for k in ("return_pct", "max_drawdown_pct")):
        reasons.append("prices_missing_or_nonfinite")
    if record.get("authority") != "committed_json":
        reasons.append("legacy_unverified")
    return {"version": "investment-evaluation/2.0", "evaluated_at": str(today),
            "source": record.get("raw_path"), "window_complete": "window_incomplete" not in reasons,
            "calibration_eligible": not reasons, "exclusion_reasons": reasons}
