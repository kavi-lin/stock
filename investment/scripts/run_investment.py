#!/usr/bin/env python3
"""Resumable investment artifact controller; model dispatch stays with the host/broker.

prepare freezes all five prompts before claim can expose work. accept validates
one returned lane immediately. resume only reuses verified hashes and versions.
finalize runs the existing assembler, validators and deterministic renderer.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

from run_data import (ROOT, RUNS, VERSION, LANES, atomic_json, digest, file_lock,
                      freeze_snapshot, fresh, load_snapshot, read_json, safe_id,
                      source, timestamp, utcnow)

sys.path.insert(0, str(ROOT))
PROTOCOL = ROOT / "investment/investment_protocol_v5_0.md"
DEPS = {"quant": (), **{n: ("quant",) for n in LANES},
        "red_team": LANES, "decision": (*LANES, "red_team"),
        "mhp": LANES, "risk": ("decision", "mhp"), "finalize": ("risk",)}
TERMINAL = {"complete", "degraded"}


def command(args, *, capture=True, env=None):
    p = subprocess.run([sys.executable, *map(str, args)], cwd=ROOT,
                       capture_output=capture, text=True, env=env)
    if p.returncode:
        raise ValueError(f"{Path(args[0]).name} failed rc={p.returncode}: {(p.stderr or p.stdout)[-1200:]}")
    return p.stdout


def run_dir(run_id):
    return RUNS / safe_id(run_id)


def _load(run_id, *, resume=False):
    directory = run_dir(run_id)
    manifest = read_json(directory / "manifest.json")
    snap = load_snapshot(directory / "snapshot.json", resume=resume)
    if manifest["snapshot_hash"] != snap["snapshot_hash"]:
        raise ValueError("manifest/snapshot mismatch")
    if read_json(directory / "phase0.json") != snap["sources"]["phase0"]["data"]:
        raise ValueError("Phase 0 copy differs from frozen source")
    if resume and manifest["producer_version"] != producer_version():
        raise ValueError("producer version changed: prepare a new run")
    for name, st in manifest["stages"].items():
        if st.get("status") in TERMINAL:
            if st.get("input_artifact") and digest(read_json(directory / st["input_artifact"])) != st.get("input_hash"):
                raise ValueError(f"{name}: engine input hash mismatch")
            if digest(read_json(directory / st["artifact"])) != st.get("output_hash"):
                raise ValueError(f"{name}: completed artifact hash mismatch")
            if name in (*LANES, "red_team") and st.get("input_hash") != manifest["prompts"].get(name):
                raise ValueError(f"{name}: input hash differs from frozen prompt")
            if st.get("dependency_hash") != dependency_hash(manifest, name):
                raise ValueError(f"{name}: dependencies changed")
    for name in manifest["prompts"]:
        if digest(read_json(directory / "prompts" / f"{name}.json")) != manifest["prompts"][name]:
            raise ValueError(f"{name}: frozen prompt changed")
    if manifest["status"] == "committed":
        receipt = read_json(directory / "finalize.json")
        if digest((directory / "report.md").read_text()) != receipt.get("report_hash"):
            raise ValueError("committed report hash mismatch")
    return directory, manifest, snap


def producer_version():
    return digest({"controller": VERSION, "repo": (ROOT / "VERSION").read_text().strip(),
                   "protocol": PROTOCOL.read_text(),
                   "engines": {n: (ROOT / "investment/scripts" / n).read_text()
                               for n in ("compute_price_framework.py", "decision_engine.py",
                                         "trade_plan_builder.py", "run_investment.py", "run_data.py", "run_exports.py", "collect_run_inputs.py",
                                         "build_session_export.py", "validate_session_export.py", "apply_det_shadow.py",
                                         "append_session_export.py", "render_investment_report.py")},
                   "sources": {n: (ROOT / n).read_text() for n in (
                       "skills/_shared/investment_data.py", "skills/us-stock-analysis/scripts/analyze.py",
                       "skills/market-news-analyst/scripts/fetch.py", "skills/market-sentiment-analyzer/scripts/sentiment.py",
                       "skills/finnhub-client/scripts/dual_fetch.py", "skills/valuation-modeler/scripts/fmp_client.py",
                       "skills/earnings-valuation-forecaster/scripts/forecast.py")},
                   "sentiment": (ROOT / "skills/market-sentiment-analyzer/scripts/sentiment_score.py").read_text()})


def dependency_hash(manifest, stage):
    return digest({"snapshot": manifest["snapshot_hash"], "producer": manifest["producer_version"],
                   "deps": {n: manifest["stages"][n].get("output_hash") for n in DEPS[stage]}})


def canonical_burry(raw):
    """Map the skill's burry_score into the existing engine's score/veto contract."""
    if not isinstance(raw, dict):
        raise ValueError("Burry input must be an object")
    result = copy.deepcopy(raw)
    score = raw.get("score", raw.get("burry_score"))
    if "score" in raw and "burry_score" in raw and raw["score"] != raw["burry_score"]:
        raise ValueError("Burry score disagrees with burry_score source")
    if score is None:
        if not (raw.get("missing_reason") or raw.get("degraded_reason")):
            raise ValueError("Burry score missing without a source failure reason")
        veto = None
    else:
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 100:
            raise ValueError("Burry score must be finite and within 0..100")
        veto = score < 20  # existing protocol, no threshold change
    if "veto_flag" in raw and raw["veto_flag"] is not veto:
        raise ValueError("Burry veto_flag disagrees with score < 20")
    result.update(score=score, veto_flag=veto)
    if "label" not in result and raw.get("verdict") is not None:
        result["label"] = raw["verdict"]
    return result


def mark_complete(directory, manifest, stage, result, *, degraded=False):
    filename = f"{stage}.json"
    atomic_json(directory / filename, result)
    st = manifest["stages"][stage]
    st.update(status="degraded" if degraded else "complete", artifact=filename,
              output_hash=digest(result), dependency_hash=dependency_hash(manifest, stage),
              finished_at=utcnow())
    if st.get("started_at"):
        st["elapsed_seconds"] = (timestamp(st["finished_at"]) - timestamp(st["started_at"])).total_seconds()
    atomic_json(directory / "manifest.json", manifest)


def _optional_file(path, kind, period):
    if not Path(path).exists():
        return source(None, kind=kind, status="missing", reason="artifact missing")
    data = read_json(path)
    record = source(data, kind=kind, fetched_at=data.get("source_fetched_at") or data.get("generated_at"),
                    data_as_of=data.get("asof"), period=data.get("financial_period"))
    if not fresh(record, period=period):
        return source(None, kind=kind, status="stale", reason="source timestamp or financial period unavailable/stale")
    return record


def prepare(args):
    ticker = safe_id(args.ticker.upper())
    with file_lock(RUNS / ".locks" / f"{ticker}.lock", blocking=False):
        started = time.monotonic()
        run_id = f"{ticker}_{time.strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:10]}"
        directory = run_dir(run_id)
        directory.mkdir(parents=True)
        if args.package:
            package = read_json(args.package)
        else:
            package = acquire_package(ticker, args, directory)
        package["quant_input"].setdefault("script_artifacts", {})
        p0 = package["sources"]["phase0"]["data"]
        atomic_json(directory / "phase0.json", p0)
        command(["investment/scripts/validate_phase0.py", "--path", directory / "phase0.json"])
        snap = freeze_snapshot(directory / "snapshot.json", ticker=ticker,
                               sources=package["sources"], quant_input=package["quant_input"],
                               lane_inputs=package["lane_inputs"], classification=package.get("classification"))
        from compute_price_framework import build_quant_stage
        quant = build_quant_stage(copy.deepcopy(snap["quant_input"]))
        protocol = PROTOCOL.read_text()
        import re
        common = protocol.split("### 共通 Subagent Prompt 模板", 1)[1].split("#### Fundamentals Subagent", 1)[0]
        prompts = {}
        for lane in LANES:
            prompt = {"run_id": run_id, "lane": lane, "ticker": ticker,
                      "snapshot_hash": snap["snapshot_hash"], "input": snap["lane_inputs"][lane],
                      "phase0": p0,
                      "protocol": ("\n".join(protocol.splitlines()[:43]) + common +
                                   re.split(r"\n#{3,4} ", protocol.split({
                                       "fundamentals": "#### Fundamentals Subagent", "sentiment": "#### Sentiment Subagent",
                                       "news": "#### News Subagent", "technical": "#### Technical Subagent",
                                       "valuation": "#### Valuation Specialist Subagent"}[lane], 1)[1], maxsplit=1)[0]),
                      "instruction": "Execute only your assigned Phase 2 lane in a fresh isolated context. "
                      "Use frozen inputs. Do not read other lane outputs or mutable caches. "
                      "Return protocol lane JSON; no provenance fields. No other phases or history writes."}
            if lane == "valuation":
                prompt["valuation_pack"] = quant["quant_blocks"]["valuation_pack"]
            atomic_json(directory / "prompts" / f"{lane}.json", prompt)
            prompts[lane] = digest(prompt)
        manifest = {"schema": VERSION, "run_id": run_id, "ticker": ticker,
                    "analysis_at": snap["analysis_at"], "snapshot_hash": snap["snapshot_hash"],
                    "producer_version": producer_version(), "protocol_version": "V5.5",
                    "prompts": prompts, "status": "ready", "created_at": utcnow(),
                    "offline_fixture": bool(args.package),
                    "host_job_id": os.getenv("AIC_PROTOCOL_JOB_ID"),
                    "telemetry": {"prepare_seconds": time.monotonic() - started,
                                  "fmp": package.get("fmp_telemetry"),
                                  "raw_scripts": package.get("raw_script_receipts"),
                                  "tokens": {"input": None, "output": None, "cached": None}},
                    "stages": {n: {"status": "pending", "attempts": 0} for n in DEPS}}
        mark_complete(directory, manifest, "quant", quant)
        return {"run_id": run_id, "directory": str(directory), "ready": list(LANES),
                "snapshot_hash": snap["snapshot_hash"]}


def acquire_package(ticker, args, directory):
    """Prepare from explicit Phase 0 + factpack; all live reads happen here once."""
    from compute_price_framework import assemble_inputs, fetch_volatility
    from skills._shared.investment_data import SourceCache
    if not args.phase0:
        raise ValueError("prepare requires --phase0 (validated source path)")
    p0path = Path(args.phase0).resolve()
    command(["investment/scripts/validate_phase0.py", "--path", p0path])
    p0 = read_json(p0path)
    # Legacy Phase 0 has no sub-day timestamp. It must be generated again and
    # carry fetched_at; a copy or stat/mtime cannot renew its source lifetime.
    p0rec = source(p0, kind="phase0", fetched_at=p0.get("fetched_at") or p0.get("generated_at"),
                   data_as_of=p0.get("scan_date"))
    if not fresh(p0rec):
        raise ValueError("Phase 0 needs a source timestamp within 3 hours; rebuild Phase 0")
    cache = SourceCache(ROOT / "skills/earnings-analyst/cache/sources")
    income = cache.get("/stable/income-statement", {"symbol": ticker, "period": "quarter", "limit": 8}, refresh=True)
    if not income or not income[0].get("date"):
        raise ValueError("cannot confirm latest financial period")
    period = income[0]["date"]
    cache.period = period
    for rec in cache.sources.values():
        rec["financial_period"] = period
    if args.factpack:
        factpack = read_json(args.factpack)
    else:
        factpack = json.loads(command(["investment/scripts/phase1_factpack.py", ticker, "--no-prewarm-forecaster"],
                                     env={**os.environ, "AIC_INVESTMENT_PERIOD": period}))
    if factpack.get("ticker") != ticker:
        raise ValueError("factpack ticker mismatch")
    fact_sources = factpack.get("source_records")
    if fact_sources is None or any(r.get("status") == "ok" and not fresh(r) for r in fact_sources.values()):
        raise ValueError("factpack lacks reliable fresh source records; rerun phase1_factpack.py")
    bundle_period = (factpack.get("bundles", {}).get("earnings_analyst_bundle") or {}).get("last_earnings_date")
    if bundle_period and bundle_period != period:
        raise ValueError("financial period changed during preparation; prepare a new run")
    # Factpack refreshes earnings before scripts consume their bundle. This
    # prevents a new quarter's quote/quant from mixing with an old lane bundle.
    receipts = {}
    if args.lane_data:
        lane_data = read_json(args.lane_data)
    else:
        from collect_run_inputs import collect
        lane_data, receipts = collect(ticker, directory, period=period)
    ea_path = ROOT / f"skills/earnings-analyst/cache/{ticker}_{period}.json"
    ea = read_json(ea_path) if ea_path.exists() else {}
    if not ea.get("source_records"):
        raise ValueError("legacy earnings cache needs refresh with fetch.py + analyze.py")
    # Re-read via fetch to update stale optionals, never silently consume them.
    if any(r.get("status") == "ok" and not fresh(r, period=period) for r in ea["source_records"].values()):
        command(["skills/earnings-analyst/scripts/fetch.py", ticker])
        command(["skills/earnings-analyst/scripts/analyze.py", ticker])
        ea = read_json(ea_path)
    sources = {"phase0": p0rec}
    for key, rec in ea["source_records"].items():
        sources["fmp_" + key] = rec
    for key, rec in fact_sources.items():
        sources["factpack_fmp_" + key] = rec
    for name, receipt in receipts.items():
        for key, rec in receipt.get("source_records", {}).items():
            sources[f"script_{name}_{key}"] = rec
    raw = {"earnings": ea,
           "peers": factpack.get("bundles", {}).get("peer_bundle", {}),
           "supplementary": factpack.get("bundles", {}).get("fmp_supp_bundle", {}),
           "profile": cache.get("/stable/profile", {"symbol": ticker}) or []}
    raw["profile"] = raw["profile"][0] if raw["profile"] else {}
    raw["estimates"] = cache.get("/stable/analyst-estimates", {"symbol": ticker, "period": "annual", "limit": 6}) or []
    for key, path, kind in (("dcf", f"skills/valuation-modeler/cache/{ticker}_dcf_payload.json", "market"),
                            ("comps", f"skills/valuation-modeler/cache/{ticker}_comps_payload.json", "market"),
                            ("forecaster", f"skills/earnings-valuation-forecaster/cache/{ticker}.json", "forecaster")):
        if receipts.get(key, {}).get("status") == "unavailable":
            sources[key] = source(None, kind=kind, status="unavailable", reason=receipts[key]["reason"])
        else:
            sources[key] = _optional_file(ROOT / path, kind, period)
        raw[key] = sources[key]["data"] or {}
    raw["risk_free"] = phase0_risk_free(p0)
    volatility = fetch_volatility(ticker, fetcher=lambda path, params, **kw: cache.get("/stable/" + path, params))
    # Long-running collection precedes the final price fetch so a fresh quote
    # cannot expire while optional scripts are still running.
    quote = cache.get("/stable/quote", {"symbol": ticker})
    if not quote:
        raise ValueError("fresh quote unavailable")
    sources["quote"] = next(r for r in cache.sources.values() if r["kind"] == "quote")
    raw["quote"] = quote
    inp = {"ticker": ticker, "current_price": quote[0]["price"]}
    assemble_inputs(ticker, inp, authoritative_anchors=True, phase0_path=p0path, sources=raw)
    inp["script_artifacts"] = {"dcf_self_built": raw["dcf"], "comps_implied": raw["comps"]}
    inp["volatility"] = volatility
    # Preserve raw values alongside the effective inputs without changing the
    # Finnhub scoring / FMP audit split inside ticker_data_bundle.
    sources["raw_inputs"] = source(raw, kind="market", fetched_at=utcnow(), period=period)
    for key, rec in cache.sources.items():
        if rec["kind"] != "quote":
            sources["prepare_fmp_" + key] = rec
    for rec in sources.values():
        if rec.get("status") == "ok" and not fresh(rec):
            rec.update(status="stale", reason="source expired during preparation; original source time retained")
    if receipts:
        lane_data["valuation"] = {k: raw[k] or None for k in ("dcf", "comps", "forecaster")}
        lane_data["valuation"]["missing_reasons"] = {k: sources[k]["reason"] for k in ("dcf", "comps", "forecaster") if sources[k]["status"] != "ok"}
    def script_status(lane):
        payload = lane_data.get(lane)
        if not payload or receipts.get(lane, {}).get("status") == "unavailable":
            return "unavailable"
        if isinstance(payload, dict) and payload.get("status") in {"error", "unavailable", "missing"}:
            return "unavailable"
        return "ok"
    inputs = {lane: {"factpack": lane_factpack(factpack, lane), "script_output": lane_data.get(lane),
                     "script_status": script_status(lane),
                     "missing_reason": receipts.get(lane, {}).get("reason")} for lane in LANES}
    audit_fmp_metrics = None
    audit_path = ROOT / f"skills/finnhub-client/data/{time.strftime('%Y-%m-%d')}/{ticker}.json"
    if audit_path.exists():
        audit = read_json(audit_path)
        audit_source = source(audit, kind="quote", fetched_at=audit.get("fetched_at"))
        if fresh(audit_source):
            sources["finnhub_fmp_audit"] = audit_source  # never exposed in lane prompts
            audit_fmp_metrics = ((audit.get("_audit") or {}).get("fmp") or {}).get("source_telemetry")
    return {"sources": sources, "quant_input": inp, "lane_inputs": inputs,
            "raw_script_receipts": receipts,
            "fmp_telemetry": {"preparation": cache.metrics, "earnings": ea.get("source_telemetry"), "factpack": factpack.get("source_telemetry"), "fmp_audit": audit_fmp_metrics,
                              **{name: receipt.get("source_telemetry") for name, receipt in receipts.items()}},
            "classification": {"sector": raw["profile"].get("sector"),
                               "industry": raw["profile"].get("industry"),
                               "regime": (p0.get("macro_summary") or {}).get("market_regime"),
                               "data_as_of": p0rec["fetched_at"]}}


def lane_factpack(factpack, lane):
    """Appendix injection rules; raw provider/audit envelopes stay outside prompts."""
    allowed = {"fundamentals": {"ticker_data_bundle", "earnings_analyst_bundle", "peer_bundle", "fmp_supp_bundle"},
               "valuation": {"earnings_analyst_bundle", "peer_bundle", "fmp_supp_bundle"},
               "sentiment": {"ticker_data_bundle", "fmp_supp_bundle"},
               "news": {"ticker_data_bundle", "fmp_supp_bundle"}, "technical": {"fmp_supp_bundle"}}
    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items() if k not in {"_audit", "source_records", "source_telemetry"}}
        return [clean(v) for v in value] if isinstance(value, list) else value
    result = {"ticker": factpack["ticker"], "bundles": {
        k: clean(v) for k, v in factpack.get("bundles", {}).items() if k in allowed[lane]}}
    sections = {"fundamentals": {"quality_scores", "owner_earnings", "employee_history"},
                "sentiment": {"insider_summary", "institutional", "congressional_trades", "executive_compensation"},
                "news": {"ma_events"}, "valuation": {"quality_scores", "owner_earnings"}, "technical": {"insider_summary"}}
    supp = result["bundles"].get("fmp_supp_bundle")
    if isinstance(supp, dict):
        result["bundles"]["fmp_supp_bundle"] = {k: v for k, v in supp.items() if k in sections[lane] or k in {"status", "reason"}}
    return result


def phase0_risk_free(p0):
    fred = p0.get("fred_snapshot") or {}
    value = ((fred.get("series") or {}).get("DGS10") or {}).get("value")
    if value is None:
        value = fred.get("treasury_10y")
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 < value < 20:
        return round(value / 100, 5), "fred_phase0"
    return None, None


def ready_stages(manifest):
    return [n for n, st in manifest["stages"].items() if st["status"] in {"pending", "retry"}
            and all(manifest["stages"][d]["status"] in TERMINAL for d in DEPS[n])]


def claim(directory, manifest, args):
    if manifest["status"] == "blocked":
        raise ValueError("quota/authentication stop: resume only after external state changes")
    selected = os.getenv("AIC_PROTOCOL_MODEL_TIER")
    effort = os.getenv("AIC_PROTOCOL_EFFORT")
    if selected and selected != "cli-default" and args.model != selected:
        raise ValueError("stage model differs from broker-governed host model selection")
    if effort and effort != "unknown" and args.effort != effort:
        raise ValueError("stage effort differs from host selection")
    cap = min(3, max(1, args.slots or 1))
    active = sum(s["status"] == "running" for s in manifest["stages"].values())
    ready = [n for n in ready_stages(manifest) if n in (*LANES, "red_team")]
    if args.fallback and args.stage == "red_team":
        raise ValueError("Red Team failure uses synthetic compatibility verdict, never inline")
    if args.fallback:
        ready = [n for n, st in manifest["stages"].items() if n in LANES and st["status"] == "needs_fallback"]
    if args.stage:
        ready = [n for n in ready if n == args.stage]
    claimed = ready[:max(0, cap - active)]
    if "red_team" in claimed:
        if not args.context:
            raise ValueError("Red Team claim requires --context containing burry and conflict_bias")
        context = read_json(args.context)
        if not isinstance(context.get("burry"), dict) or not isinstance(context.get("conflict_bias"), dict):
            raise ValueError("Red Team context requires burry and conflict_bias objects")
        context["burry"] = canonical_burry(context["burry"])
        prompt = read_json(directory / "prompts/red_team.json")
        if "pm_context" in prompt and prompt["pm_context"] != context:
            raise ValueError("Red Team context is frozen across retries")
        prompt["pm_context"] = context
        atomic_json(directory / "prompts/red_team.json", prompt)
        manifest["prompts"]["red_team"] = digest(prompt)
    for lane in claimed:
        st = manifest["stages"][lane]
        ready_at = st.get("ready_at") or max(
            [manifest["created_at"]] + [manifest["stages"][d].get("finished_at") or manifest["created_at"] for d in DEPS[lane]],
            key=timestamp)
        st.update(status="running", attempts=st["attempts"] + (0 if args.fallback else 1), fallback=bool(args.fallback), started_at=utcnow(),
                  model=args.model, effort=args.effort,
                  input_hash=manifest["prompts"].get(lane) or dependency_hash(manifest, lane),
                  queued_seconds=(timestamp(utcnow()) - timestamp(ready_at)).total_seconds(),
                  tokens={"input": None, "output": None, "cached": None})
    atomic_json(directory / "manifest.json", manifest)
    return {"claimed": claimed, "concurrency": cap,
            "prompt_paths": {n: str(directory / "prompts" / f"{n}.json") for n in claimed}}


def validate_lane(result, lane, ticker, *, degraded=False):
    if not isinstance(result, dict) or result.get("ticker") != ticker:
        raise ValueError("lane must be object with matching ticker")
    if any(k in result for k in ("provenance", "input_hash", "producer_version", "lane_contract")):
        raise ValueError("LLM must not provide provenance")
    digest(result)  # rejects nested NaN/Infinity before a stage is accepted
    if lane == "red_team":
        if result.get("subagent_isolated") is not True:
            raise ValueError("Red Team requires an isolated subagent")
        for key, lo, hi in (("counter_evidence_strength", 1, 5), ("thesis_break_probability", 0, 1)):
            value = result.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
                raise ValueError(f"invalid Red Team {key}")
        required = {"verdict", "counter_thesis", "kill_conditions", "counter_evidence_strength", "thesis_break_probability"}
        if required - result.keys() or result["verdict"] not in {"STRONG_COUNTER", "MODERATE_COUNTER", "NO_VIABLE_COUNTER"}:
            raise ValueError("invalid Red Team schema")
        if not isinstance(result["kill_conditions"], list) or not result["kill_conditions"]:
            raise ValueError("Red Team kill_conditions must be non-empty list")
        return
    if result.get("signal") not in {"BUY", "SELL", "HOLD"}:
        raise ValueError("invalid lane signal")
    if lane == "technical" and "pattern_taxonomy" in result:
        pattern = result["pattern_taxonomy"]
        if pattern is not None and not isinstance(pattern, dict):
            raise ValueError("technical pattern_taxonomy must be an object with pattern and confirmation_criteria")
    for key, lo, hi in (("score", -5, 5), ("confidence", 0, 0.6 if degraded else 1)):
        v = result.get(key)
        if lane == "valuation" and key == "score" and v is None:
            continue  # insufficient anchors remains an explicit null + decision cap
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
            raise ValueError(f"invalid lane {key}")
    for key in ("key_factors", "risk_flags"):
        if not isinstance(result.get(key), list):
            raise ValueError(f"invalid lane {key}")
    if not degraded and result.get("subagent_isolated") is not True:
        raise ValueError("isolated subagent required; use explicit degraded fallback")
    from validate_session_export import LANE_SHAPE_LOCKS, _check_pt_revision_momentum
    for key, field, body, nullable in LANE_SHAPE_LOCKS:
        if key != lane + "_lane" or field not in result:
            continue
        value = result[field]
        if value is None and nullable:
            continue
        if not isinstance(value, dict) or (body and body not in value and "note" in value):
            raise ValueError(f"invalid {lane}.{field} shape")
    if lane == "news":
        errors = []
        _check_pt_revision_momentum({"export_date": utcnow()[:10]}, {"news_lane": result}, errors, [])
        if errors:
            raise ValueError("; ".join(errors))


def accept(directory, manifest, snap, args):
    lane = args.stage
    if lane not in (*LANES, "red_team"):
        raise ValueError("accept is for lane and Red Team results")
    st = manifest["stages"][lane]
    if st["status"] != "running":
        raise ValueError("claim this stage before accepting a result")
    if bool(st.get("fallback")) != bool(args.degraded):
        raise ValueError("fallback results require explicit --degraded and confidence cap")
    try:
        result = read_json(args.result)
        validate_lane(result, lane, manifest["ticker"], degraded=args.degraded)
        if lane == "valuation" and result.get("score") != read_json(directory / "quant.json")["quant_blocks"]["valuation_pack"]["score"]:
            raise ValueError("valuation score must equal frozen quant score")
    except (ValueError, OSError) as exc:
        st.update(failure_kind="schema", status="retry" if st["attempts"] < 2 else "needs_fallback", ready_at=utcnow())
        if lane == "red_team" and st["status"] == "needs_fallback":
            synthetic_red_team(directory, manifest)
        atomic_json(directory / "manifest.json", manifest)
        raise ValueError(f"{lane} validation failed: {exc}") from exc
    if args.usage:
        usage = read_json(args.usage)
        if any(usage.get(k) is not None and (type(usage[k]) is not int or usage[k] < 0) for k in ("input", "output", "cached")):
            raise ValueError("token usage must be non-negative integer or null")
        st["tokens"] = {k: usage.get(k) for k in ("input", "output", "cached")}
    mark_complete(directory, manifest, lane, result, degraded=args.degraded)
    if all(manifest["stages"][n]["status"] in TERMINAL for n in LANES):
        rt = {"ticker": manifest["ticker"], "run_id": manifest["run_id"],
              "instruction": "Execute protocol Phase 2.8 Red Team in an isolated context; return JSON.",
              "protocol": PROTOCOL.read_text().split("## PHASE 2.8", 1)[1].split("## PHASE 3", 1)[0], "snapshot_hash": snap["snapshot_hash"],
              "phase0": snap["sources"]["phase0"]["data"],
              "lanes": {n: read_json(directory / f"{n}.json") for n in LANES},
              "quant": read_json(directory / "quant.json")}
        if manifest["stages"]["red_team"]["status"] == "pending":
            atomic_json(directory / "prompts/red_team.json", rt)
            manifest["prompts"]["red_team"] = digest(rt)
            atomic_json(directory / "manifest.json", manifest)
    return {"accepted": lane, "ready": ready_stages(manifest)}


def synthetic_red_team(directory, manifest):
    full_fallback = all(manifest["stages"][n]["status"] == "degraded" for n in LANES)
    synthetic = {"ticker": manifest["ticker"], "verdict": "STRONG_COUNTER" if full_fallback else "MODERATE_COUNTER", "basis": "unclassified",
                 "counter_thesis": "Red Team execution failed; no investment counter-thesis established",
                 "kill_conditions": ["Unknown: Red Team execution incomplete"],
                 "counter_evidence_strength": None, "thesis_break_probability": None,
                 "execution_failed": True, "synthetic": True}
    mark_complete(directory, manifest, "red_team", synthetic, degraded=True)


def fail_stage(directory, manifest, args):
    st = manifest["stages"][args.stage]
    if st["status"] != "running":
        raise ValueError("only running work can fail")
    st["failure_kind"] = args.reason
    if args.reason in {"quota", "authentication"}:
        manifest["status"] = "blocked"
        st["status"] = "blocked"
    else:
        st["status"] = "retry" if st["attempts"] < 2 else "needs_fallback"
    if args.stage == "red_team" and st["status"] == "needs_fallback":
        synthetic_red_team(directory, manifest)
    atomic_json(directory / "manifest.json", manifest)
    return {"stage": args.stage, "status": st["status"], "attempts": st["attempts"]}


def compute(directory, manifest, snap, args):
    if any(manifest["stages"][n]["status"] not in TERMINAL for n in (*LANES, "red_team")):
        raise ValueError("all lanes and Red Team must be accepted before decision")
    p3 = read_json(args.p3_input)
    p3["burry"] = canonical_burry(p3.get("burry"))
    p4 = read_json(args.p4_input) if args.p4_input else None
    for n in LANES:
        lane = read_json(directory / f"{n}.json")
        if p3.get("lane_scores", {}).get(n) != lane["score"] or p3.get("lane_confidence", {}).get(n) != lane["confidence"]:
            raise ValueError(f"{n}: decision input differs from accepted result")
    qb = read_json(directory / "quant.json")["quant_blocks"]
    if p3.get("forward_validation") != qb.get("forward_validation"):
        raise ValueError("decision forward_validation differs from frozen quant")
    fvs = qb["fair_value_summary"]
    if any(p3.get("decision_cap", {}).get(k) != fvs.get(v) for k, v in
           (("anchors_available", "anchors_available"), ("fair_value_confidence", "confidence"))):
        raise ValueError("decision cap inputs differ from frozen quant")
    if p4 is not None and p4.get("analysis_price") != snap["price"]:
        raise ValueError("sizing must use frozen analysis_price")
    for data in (p3, *([p4] if p4 is not None else [])):
        if data.get("ticker") != manifest["ticker"]:
            raise ValueError("engine input ticker mismatch")
    degraded_lanes = [n for n in LANES if manifest["stages"][n]["status"] == "degraded"]
    fanout_mode = "FULL_FALLBACK" if len(degraded_lanes) == 5 else "PARTIAL_FALLBACK" if len(degraded_lanes) >= 2 else "PARALLEL_SUBAGENT"
    if p3.get("gates", {}).get("phase2_fanout_mode") != fanout_mode:
        raise ValueError("fanout mode differs from controller execution state")
    accepted_rt = read_json(directory / "red_team.json")
    pm_context = read_json(directory / "prompts/red_team.json").get("pm_context", {})
    if p3.get("burry") != pm_context.get("burry"):
        raise ValueError("Burry input differs from frozen Red Team context")
    for key in ("verdict", "counter_thesis", "kill_conditions", "counter_evidence_strength", "thesis_break_probability"):
        if p3.get("red_team", {}).get(key) != accepted_rt.get(key):
            raise ValueError(f"Red Team {key} differs from accepted result")
    p0 = snap["sources"]["phase0"]["data"]
    expected_macro = {"macro_multiplier": p0.get("phase3_macro_multiplier"),
                      "macro_backdrop_score": (p0.get("macro_summary") or {}).get("macro_backdrop_score"),
                      "market_regime": (p0.get("macro_summary") or {}).get("market_regime")}
    if any(p3.get("macro", {}).get(k) != v for k, v in expected_macro.items()):
        raise ValueError("decision macro differs from frozen Phase 0")
    if manifest["stages"]["decision"]["status"] in TERMINAL:
        if read_json(directory / "p3_input.json") != p3:
            raise ValueError("completed engine inputs are immutable; prepare a new run")
        decision = read_json(directory / "decision.json")
    else:
        from decision_engine import run_phase3
        manifest["stages"]["decision"].update(started_at=utcnow(), input_artifact="p3_input.json", input_hash=digest(p3))
        decision = run_phase3(p3)
        decision["ticker"] = manifest["ticker"]
        atomic_json(directory / "p3_input.json", p3)
        mark_complete(directory, manifest, "decision", decision)
    if p4 is None:
        return {"decision": decision, "next": "compute with --p4-input"}
    if args.mhp_input:
        mhp_input = read_json(args.mhp_input)
        if manifest["stages"]["mhp"]["status"] in TERMINAL:
            if mhp_input != read_json(directory / "mhp_input.json"):
                raise ValueError("MHP inputs are immutable")
        else:
            from compute_price_framework import build_full_output
            manifest["stages"]["mhp"].update(started_at=utcnow(), input_artifact="mhp_input.json", input_hash=digest(mhp_input))
            atomic_json(directory / "mhp_input.json", mhp_input)
            mark_complete(directory, manifest, "mhp", build_full_output(read_json(directory / "quant.json"), mhp_input))
    if manifest["stages"]["mhp"]["status"] not in TERMINAL:
        raise ValueError("risk requires --mhp-input to compute a frozen price framework")
    if p4.get("multi_horizon_price_framework") != read_json(directory / "mhp.json")["multi_horizon_price_framework"]:
        raise ValueError("risk price framework differs from program-produced MHP")
    if p4.get("final_decision") != decision.get("final_decision"):
        raise ValueError("risk input final_decision differs from decision engine")
    if manifest["stages"]["risk"]["status"] in TERMINAL:
        if read_json(directory / "p4_input.json") != p4:
            raise ValueError("completed risk inputs are immutable; prepare a new run")
        return {"decision": decision, "risk": read_json(directory / "risk.json")}
    atomic_json(directory / "p4_input.json", p4)
    manifest["stages"]["risk"].update(started_at=utcnow(), input_artifact="p4_input.json", input_hash=digest(p4))
    plan = json.loads(command(["investment/scripts/trade_plan_builder.py", "--from-file", directory / "p4_input.json"]))
    if accepted_rt.get("execution_failed") and (plan.get("trade_plan", {}).get("position_size_pct") or 0) > 0:
        raise ValueError("synthetic Red Team requires zero new position")
    mark_complete(directory, manifest, "risk", plan)
    return {"decision": decision, "risk": plan}


def finalize(directory, manifest, snap, args):
    """Retain failed final gates as observations, without changing their outcome."""
    if manifest["status"] == "committed":
        return _finalize(directory, manifest, snap, args)
    st = manifest["stages"]["finalize"]
    st.update(attempts=st.get("attempts", 0) + 1, started_at=utcnow())
    try:
        return _finalize(directory, manifest, snap, args)
    except (ValueError, OSError, KeyError) as exc:
        st.update(finished_at=utcnow(), failure_kind=("schema" if any(
            name in str(exc) for name in ("validate_", "build_session_export.py")) else "execution"))
        st["elapsed_seconds"] = (timestamp(st["finished_at"]) - timestamp(st["started_at"])).total_seconds()
        st.setdefault("failures", []).append({"at": st["finished_at"], "kind": st["failure_kind"]})
        atomic_json(directory / "manifest.json", manifest)
        raise


def _finalize(directory, manifest, snap, args):
    if manifest.get("offline_fixture") and not args.history:
        raise ValueError("offline fixture runs require an isolated --history")
    if args.history and Path(args.history).resolve() == (ROOT / "investment/invest_logs/history.json").resolve():
        raise ValueError("--history override must be isolated from production history")
    if manifest["stages"]["risk"]["status"] not in TERMINAL:
        raise ValueError("compute decision and risk before finalize")
    qualitative = read_json(args.qualitative)
    if manifest["status"] == "committed":
        if digest(qualitative) != manifest.get("qualitative_hash"):
            raise ValueError("same run_id has different qualitative content")
        return {"status": "already_committed", "run_id": manifest["run_id"]}
    manifest["qualitative_hash"] = digest(qualitative)
    manifest["stages"]["finalize"].update(started_at=utcnow(), input_artifact="qualitative.json", input_hash=digest(qualitative))
    atomic_json(directory / "qualitative.json", qualitative)
    atomic_json(directory / "manifest.json", manifest)
    prior_thesis = {}
    if (directory / "session.json").exists():
        prior_trade = read_json(directory / "session.json")["trades_this_session"][0]
        prior_thesis = {k: prior_trade[k] for k in ("thesis_id", "thesis_registered_at") if prior_trade.get(k)}
    date = snap["analysis_at"][:10]
    command(["investment/scripts/build_session_export.py", "--ticker", manifest["ticker"],
             "--date", date, "--qualitative", args.qualitative,
             "--p3-input", directory / "p3_input.json", "--p4-input", directory / "p4_input.json",
             "--run-dir", directory, "--session-out", directory / "session.json",
             "--bundle-out", directory / "bundle.json"])
    command(["investment/scripts/append_session_export.py", "--from-file", directory / "session.json",
             "--stamp-only", "--stamped-out", directory / "session.json"])
    command(["investment/scripts/validate_session_export.py", "--history", directory / "session.json"])
    report = directory / "report.md"
    command(["investment/scripts/render_investment_report.py", "--history", directory / "session.json",
             "--phase-inputs", directory / "bundle.json", "--out", report])
    command(["investment/scripts/validate_markdown_export.py", "--report", report,
             "--history", directory / "session.json"])
    if not manifest.get("offline_fixture"):
        if prior_thesis:
            session = read_json(directory / "session.json")
            session["trades_this_session"][0].update(prior_thesis)
            atomic_json(directory / "session.json", session)
        # Existing non-fatal lifecycle integration; never substitutes for a gate.
        receipt = subprocess.run([sys.executable, "investment/scripts/register_thesis.py", "--session", str(directory / "session.json")],
                                 cwd=ROOT, capture_output=True, text=True)
        manifest["thesis_registration"] = {"returncode": receipt.returncode,
            "status": "registered" if read_json(directory / "session.json")["trades_this_session"][0].get("thesis_id") else "unavailable"}
        atomic_json(directory / "manifest.json", manifest)
    # Commit only
    # the exact stamped object validated above, using the stable history lock.
    command(["investment/scripts/append_session_export.py", "--from-file", directory / "session.json", "--preserve-stamp",
             *(["--history", args.history] if args.history else [])])
    # Compatibility publication uses atomic replace; the unique run report is
    # retained even if another same-day run later updates the dashboard alias.
    import tempfile
    alias = ROOT / "reports" / f"{date.replace('-', '')}_{manifest['ticker']}.md"
    if args.history:
        alias = directory / "published_report.md"
    fd, tmp = tempfile.mkstemp(dir=alias.parent, prefix=".investment-report-")
    with os.fdopen(fd, "w") as stream:
        stream.write(report.read_text())
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, alias)
    manifest["status"] = "committed"
    mark_complete(directory, manifest, "finalize", {"entry_digest": read_json(directory / "session.json")["export_provenance"]["entry_digest"],
                                                   "report": str(report), "report_hash": digest(report.read_text())})
    return {"status": "committed", "run_id": manifest["run_id"], "report": str(report)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--ticker", required=True)
    for opt in ("phase0", "factpack", "lane-data", "package"):
        prep.add_argument("--" + opt)
    for name in ("status", "resume", "claim", "accept", "fail", "compute", "finalize"):
        p = sub.add_parser(name)
        p.add_argument("run_id")
        if name == "claim":
            p.add_argument("--slots", type=int)
            p.add_argument("--model", required=True)
            p.add_argument("--effort", default=None)
            p.add_argument("--stage", choices=(*LANES, "red_team"))
            p.add_argument("--fallback", action="store_true")
            p.add_argument("--context", help="Red Team Burry/conflict-bias input JSON")
        if name == "resume":
            p.add_argument("--recovered", help="evidence that quota/authentication state changed; never retries automatically")
        if name in ("accept", "fail"):
            p.add_argument("--stage", choices=(*LANES, "red_team"), required=True)
        if name == "accept":
            p.add_argument("--result", required=True)
            p.add_argument("--degraded", action="store_true")
            p.add_argument("--usage")
        if name == "fail":
            p.add_argument("--reason", choices=("quota", "authentication", "schema", "execution"), required=True)
        if name == "compute":
            p.add_argument("--p3-input", required=True)
            p.add_argument("--p4-input")
            p.add_argument("--mhp-input", help="qualitative MHP inputs; quant values remain frozen")
        if name == "finalize":
            p.add_argument("--qualitative", required=True)
            p.add_argument("--history", help="isolated history for offline end-to-end acceptance")
    args = ap.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args)
        else:
            with file_lock(run_dir(args.run_id) / ".lock"):
                directory, manifest, snap = _load(args.run_id, resume=args.command in {"resume", "claim"})
                if args.command not in {"status", "fail"} and manifest["status"] != "committed" and manifest["producer_version"] != producer_version():
                    raise ValueError("producer version changed: prepare a new run; completed evidence retained")
                if args.command == "resume" and not manifest.get("offline_fixture"):
                    from skills._shared.investment_data import SourceCache
                    probe = SourceCache(ROOT / "skills/earnings-analyst/cache/sources")
                    income = probe.get("/stable/income-statement", {"symbol": manifest["ticker"], "period": "quarter", "limit": 8}, refresh=True)
                    period = ((snap["sources"].get("raw_inputs") or {}).get("data") or {}).get("earnings", {}).get("last_earnings_date")
                    if not income or not period or income[0].get("date") != period:
                        raise ValueError("financial period changed or unconfirmed: prepare a new run")
                if args.command in {"status", "resume"}:
                    if args.command == "resume" and args.recovered and manifest["status"] == "blocked":
                        manifest.setdefault("recoveries", []).append({"at": utcnow(), "evidence": args.recovered})
                        for st in manifest["stages"].values():
                            if st["status"] == "blocked":
                                st["status"] = "retry"
                        manifest["status"] = "ready"
                        atomic_json(directory / "manifest.json", manifest)
                    result = {"manifest": manifest, "ready": ready_stages(manifest)}
                elif args.command == "claim":
                    result = claim(directory, manifest, args)
                elif args.command == "accept":
                    result = accept(directory, manifest, snap, args)
                elif args.command == "fail":
                    result = fail_stage(directory, manifest, args)
                elif args.command == "compute":
                    result = compute(directory, manifest, snap, args)
                else:
                    result = finalize(directory, manifest, snap, args)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
