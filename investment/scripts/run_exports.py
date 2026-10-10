"""Program-owned V5.5 export evidence and strict validation."""
from __future__ import annotations

import importlib.util
import copy
from pathlib import Path

from run_data import ROOT, LANES, digest, read_json, accepted_lane_detail


def attach(entry, directory, manifest, snapshot):
    directory = Path(directory)
    trade = entry["trades_this_session"][0]
    entry["session_export_version"] = "V5.5"
    entry["run_context"] = {
        "run_id": manifest["run_id"], "snapshot_hash": snapshot["snapshot_hash"],
        "analysis_at": snapshot["analysis_at"], "protocol_version": "V5.5",
        "producer_version": manifest["producer_version"],
        "classification": snapshot.get("classification", {}),
        "stages": {n: {k: s.get(k) for k in ("input_hash", "output_hash", "model", "effort", "status",
                                              "dependency_hash", "attempts", "tokens", "elapsed_seconds", "queued_seconds")}
                   for n, s in manifest["stages"].items() if n != "finalize"},
    }
    script = ROOT / "skills/market-sentiment-analyzer/scripts/sentiment_score.py"
    spec = importlib.util.spec_from_file_location("investment_sentiment_score", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sentiment = snapshot["lane_inputs"]["sentiment"].get("script_output") or {}
    raw = (snapshot["sources"].get("raw_inputs") or {}).get("data") or {}
    supp = raw.get("supplementary") or {}
    trade["sentiment_det"] = mod.build_sentiment_det(manifest["ticker"], sentiment, supp)
    ts = sentiment.get("ticker_signals") or {}
    insider_q0 = mod._insider_q0(ts)
    ea = raw.get("earnings") or {}
    metrics = (ea.get("ttm_metrics") or {}).get("from_key_metrics_ttm") or {}
    ratios = (ea.get("ttm_metrics") or {}).get("from_ratios_ttm") or {}
    trade["det_inputs"] = {
        "altman_z": (supp.get("quality_scores") or {}).get("altmanZScore"),
        "debt_to_equity": ratios.get("debtToEquityRatioTTM"),
        "fcf_yield": metrics.get("freeCashFlowYieldTTM"),
        "insider_ratio_q": insider_q0.get("acquired_disposed_ratio"),
        "short_interest_pct": ts.get("short_pct_float"),
        "fred_in_sector_avoid": None,
    }
    trade["det_inputs_metadata"] = {"producer_version": "run_exports/1.0", "shadow_only": True,
                                    "input_hash": digest({"sentiment": sentiment, "supp": supp, "earnings": ea}),
                                    "missing_reasons": {k: "not available in frozen source" for k, v in trade["det_inputs"].items() if v is None}}
    quote = snapshot["sources"]["quote"]
    audit = snapshot["sources"].get("finnhub_fmp_audit") or {}
    audit_data = audit.get("data") or {}
    prices = [("FMP frozen quote", snapshot["price"], quote.get("fetched_at"), quote.get("data_as_of")),
              ("Finnhub scoring", (audit_data.get("scoring") or {}).get("price"), audit.get("fetched_at"), audit.get("data_as_of")),
              ("FMP audit", ((audit_data.get("_audit") or {}).get("fmp") or {}).get("price"), audit.get("fetched_at"), audit.get("data_as_of"))]
    trade["price_sources"] = [{"source": name, "price": value, "fetched_at": fetched,
                                "data_as_of": asof, "difference_from_frozen": value - snapshot["price"] if isinstance(value, (int, float)) else None,
                                "status": "ok" if isinstance(value, (int, float)) else "unavailable"}
                               for name, value, fetched, asof in prices]
    from apply_det_shadow import apply_to_session_export
    apply_to_session_export(entry)
    for lane in (*LANES, "red_team"):
        st = manifest["stages"][lane]
        slot = trade["lane_contract"]["lanes"][lane]
        slot.update(input_hash=st.get("input_hash"), producer_version=manifest["producer_version"],
                    model=st.get("model"), execution_status=st["status"])
    degraded = any(manifest["stages"][n]["status"] == "degraded" for n in (*LANES, "red_team"))
    trade["execution_quality"] = "incomplete" if trade.get("red_team_execution_failed") else "degraded" if degraded else "complete"
    trade["red_team_synthetic"] = bool(trade.get("red_team_execution_failed"))
    trade["kill_condition_evaluation"] = {"status": "unknown", "event_evidence": [],
                                           "reason": "requires subsequent event evidence; price return is not thesis proof"}
    return entry


def check(entry, errors):
    if entry.get("session_export_version") != "V5.5":
        if entry.get("run_context"):
            errors.append("run_context requires V5.5; downgrade forbidden")
        return
    try:
        from run_investment import _load, canonical_burry
        context = entry["run_context"]
        directory, manifest, snap = _load(context["run_id"])
        if entry.get("ticker") != manifest["ticker"]:
            raise ValueError("run ticker mismatch")
        for key in ("snapshot_hash", "analysis_at", "producer_version"):
            if context.get(key) != manifest.get(key):
                raise ValueError(f"run_context.{key} mismatch")
        trade = entry["trades_this_session"][0]
        burry = read_json(directory / "p3_input.json").get("burry")
        if canonical_burry(burry) != burry:
            raise ValueError("Burry engine input is not canonical; score/veto mapping missing")
        if trade.get("burry_score") != burry["score"]:
            raise ValueError("Burry export score differs from engine input")
        if trade.get("analysis_price") != snap["price"]:
            raise ValueError("analysis price differs from snapshot")
        if context.get("classification") != snap.get("classification"):
            raise ValueError("historical classification differs from snapshot")
        expected = {"trades_this_session": [copy.deepcopy(trade)]}
        # Recompute program-owned fields; assertions cover the entire block,
        # including explicit null reasons and per-lane provenance.
        attach(expected, directory, manifest, snap)
        for key in ("sentiment_det", "det_inputs", "det_inputs_metadata", "lane_contract",
                    "execution_quality", "red_team_synthetic", "kill_condition_evaluation", "price_sources"):
            if trade.get(key) != expected["trades_this_session"][0].get(key):
                raise ValueError(f"{key} missing or not program-produced")
        if context != expected["run_context"]:
            raise ValueError("run_context stage evidence mismatch")
        for lane in (*LANES, "red_team"):
            st = manifest["stages"][lane]
            if st["status"] not in {"complete", "degraded"} or not st.get("input_hash") or not st.get("model"):
                raise ValueError(f"{lane}: incomplete execution evidence")
            accepted = read_json(directory / (lane + ".json"))
            if lane in LANES:
                block = trade.get(lane + "_lane") or {}
                for field in ("score", "confidence", "signal", "key_factors", "risk_flags"):
                    if block.get(field) != accepted.get(field):
                        raise ValueError(f"{lane}.{field}: accepted artifact mismatch")
                for field, value in accepted_lane_detail(accepted).items():
                    if block.get(field) != value:
                        raise ValueError(f"{lane}.{field}: accepted detail missing or changed")
        decision = read_json(directory / "decision.json")
        if trade.get("calculation_steps") != decision.get("calculation_steps"):
            raise ValueError("decision evidence mismatch")
        from build_session_export import final_governance
        governed = final_governance({"engine": decision,
            "plan": read_json(directory / "risk.json"),
            "p3": read_json(directory / "p3_input.json"),
            "quant": read_json(directory / "quant.json")})
        if trade.get("phase4_6") != governed:
            raise ValueError("Phase 4.6 evidence missing or differs from frozen engines")
        for key in ("final_decision", "final_action", "avg_confidence", "position_size_pct",
                    "decision_cap_active", "decision_cap_reason", "cap_override_reason",
                    "speculative_grade", "speculative_reasons"):
            if trade.get(key) != governed[key]:
                raise ValueError(f"Phase 4.6 {key} differs from governed output")
        if trade["red_team_synthetic"] and (trade.get("position_size_pct") or 0) > 0:
            raise ValueError("synthetic Red Team forbids new positions")
    except (ValueError, OSError, KeyError, TypeError, SystemExit) as exc:
        errors.append(f"V5.5 run evidence: {exc}")
