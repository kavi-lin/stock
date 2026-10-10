"""V5.5 offline entry-point contracts, including intentionally bad evidence."""
import copy
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import run_data as D
import run_investment as R
from skills._shared.investment_data import SourceCache


def test_phase0_assembly_entry_preserves_clock_and_rejects_conflict(tmp_path):
    import assemble_phase0 as A
    data = package()["sources"]["phase0"]["data"]
    data["fred_available"] = True
    data["macro_multiplier_rationale"] = "FRED unavailable fixture replaced with real fields"
    data["fred_snapshot"] = {"regime_label": "Goldilocks", "regime_signals": {
        "yield_curve_inverted": False, "credit_stress_elevated": False,
        "financial_stress_above_avg": False, "fed_rate_direction": "flat"}}
    draft, out = tmp_path / "draft.json", tmp_path / "canonical.json"
    D.atomic_json(draft, data)
    assert A.main(["--input", str(draft), "--out", str(out)]) == 0
    result = D.read_json(out)
    assert result["fetched_at"] == data["fetched_at"]
    assert result["fred_snapshot"]["credit_stress_elevated"] is False
    assert result["fred_snapshot"]["regime_signals"] == data["fred_snapshot"]["regime_signals"]
    assert A.main(["--input", str(draft), "--out", str(out)]) == 1
    data["fred_snapshot"]["credit_stress_elevated"] = True
    with pytest.raises(ValueError, match="disagrees"):
        A.assemble(data)
    data["fetched_at"] = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()
    with pytest.raises(ValueError, match="expired"):
        A.assemble(data)


def test_manual_waits_for_capacity_without_retrying_quota(monkeypatch):
    import run_protocol_manual as M
    calls, clock = [], [0]
    monkeypatch.setattr(M.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(M.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    def acquire(role, protocol, pinned_model):
        calls.append((role, protocol, pinned_model))
        if len(calls) == 1:
            raise M.ds._mrouter.ProtocolBlocked("broker:refused(provider_busy)")
        return "codex", "lease", "broker:codex"
    monkeypatch.setattr(M.ds._mrouter, "acquire_protocol_lease", acquire)
    assert M.acquire_with_wait("codex", "invest", 10)[0] == "codex"
    assert len(calls) == 2 and clock[0] == 5
    def quota(*args, **kwargs):
        calls.append("quota")
        raise M.ds._mrouter.ProtocolBlocked("broker:refused(quota_exhausted)")
    monkeypatch.setattr(M.ds._mrouter, "acquire_protocol_lease", quota)
    with pytest.raises(M.ds._mrouter.ProtocolBlocked, match="quota"):
        M.acquire_with_wait("codex", "invest", 10)
    assert calls.count("quota") == 1 and clock[0] == 5


def package():
    now = D.utcnow()
    p0 = {"scan_date": datetime.now().date().isoformat(), "fetched_at": now,
          "macro_summary": {"market_regime": "RISK_ON", "macro_backdrop_score": 0}, "_market_signals": {}, "fred_available": False,
          "phase3_macro_multiplier": 1, "macro_multiplier_rationale": "FRED unavailable fixture"}
    return {"sources": {"phase0": D.source(p0, kind="phase0", fetched_at=now),
                        "quote": D.source([{"price": 100}], kind="quote", fetched_at=now)},
            "quant_input": {"ticker": "ZZRUN", "current_price": 100,
                            "anchors": {"dcf_unlevered": 100, "analyst_pt_consensus": 100, "peer_pe_implied": 100,
                                        "dcf_self_built": 100, "comps_implied": 100},
                            "anchor_meta": {n: {"provenance": "fixture", "as_of": now[:10], "peer_count": 4}
                                            for n in ("dcf_unlevered", "analyst_pt_consensus", "peer_pe_implied", "dcf_self_built", "comps_implied")},
                            "volatility": {"sigma_daily": .02}},
            "lane_inputs": {n: {"script_output": {}} for n in D.LANES},
            "classification": {"sector": "Technology", "regime": "RISK_ON"}}


@pytest.fixture
def run(tmp_path, monkeypatch, capsys, request):
    monkeypatch.setattr(R, "RUNS", tmp_path / "runs")
    monkeypatch.setenv("AIC_INVEST_RUNS_ROOT", str(tmp_path / "runs"))
    pkg = tmp_path / "package.json"
    data = package()
    scenario = getattr(request, "param", "profitable")
    if scenario == "loss":
        data["quant_input"]["anchors"]["dcf_self_built"] = None
        data["quant_input"]["anchors"]["dcf_unlevered"] = None
        data["quant_input"]["script_artifacts"] = {"dcf_self_built": {"ticker": "ZZRUN", "asof": D.utcnow()[:10],
            "fair_value_per_share": None, "degraded": True, "assumptions": {"reason": "negative FCF"}}}
    if scenario == "insufficient_peers":
        data["quant_input"]["anchors"]["comps_implied"] = None
        data["quant_input"]["anchors"]["peer_pe_implied"] = None
        data["quant_input"]["script_artifacts"] = {"comps_implied": {"ticker": "ZZRUN", "asof": D.utcnow()[:10],
            "comps_implied_value": None, "degraded": True, "table": []}}
    D.atomic_json(pkg, data)
    assert R.main(["prepare", "--ticker", "ZZRUN", "--package", str(pkg)]) == 0
    info = json.loads(capsys.readouterr().out)
    return info["run_id"], R.run_dir(info["run_id"])


def complete_engines(run, tmp_path, capsys, burry_input=None, confidence=.6, low_quality=False):
    rid, directory = run
    for lane in D.LANES:
        assert R.main(["claim", rid, "--stage", lane, "--model", "offline-fixture"]) == 0
        output = {"ticker": "ZZRUN", "score": 0, "confidence": confidence, "signal": "HOLD",
                  "key_factors": ["fixture evidence"], "risk_flags": [], "subagent_isolated": True}
        if lane == "news":
            output["pt_revision_momentum"] = {"direction": "UNKNOWN", "unavailable_reason": "offline fixture"}
        if lane == "technical":
            output["pattern_taxonomy"] = {"pattern": "consolidation", "confirmation_criteria": "fixture confirmation"}
        path = tmp_path / (lane + ".json")
        D.atomic_json(path, output)
        assert R.main(["accept", rid, "--stage", lane, "--result", str(path)]) == 0
    burry = burry_input if burry_input is not None else {"score": 50, "veto_flag": False}
    cb = {"schema": "conflict_bias.v1", "tentative_decision": "HOLD", "proceed_to_phase3": True,
          "triggers_fired": [], "t4_detail": None, "t5_detail": None}
    D.atomic_json(tmp_path / "context.json", {"burry": burry, "conflict_bias": cb})
    assert R.main(["claim", rid, "--stage", "red_team", "--model", "offline-fixture",
                   "--context", str(tmp_path / "context.json")]) == 0
    assert D.read_json(directory / "prompts/red_team.json")["phase0"] == D.read_json(
        directory / "snapshot.json")["sources"]["phase0"]["data"]
    rt = {"ticker": "ZZRUN", "verdict": "MODERATE_COUNTER", "counter_thesis": "fixture downside evidence",
          "kill_conditions": ["IF revenue declines THEN revisit thesis"], "counter_evidence_strength": 3,
          "thesis_break_probability": .5, "subagent_isolated": True}
    D.atomic_json(tmp_path / "rt.json", rt)
    assert R.main(["accept", rid, "--stage", "red_team", "--result", str(tmp_path / "rt.json")]) == 0
    qb = D.read_json(directory / "quant.json")["quant_blocks"]
    p3 = {"ticker": "ZZRUN", "lane_scores": dict.fromkeys(D.LANES, 0), "lane_confidence": dict.fromkeys(D.LANES, confidence),
          "macro": {"macro_multiplier": 1, "market_regime": "RISK_ON", "macro_backdrop_score": 0},
          "burry": burry, "red_team": rt, "forward_validation": qb["forward_validation"],
          "gates": {"proceed_to_phase3": True, "phase2_fanout_mode": "PARALLEL_SUBAGENT", "risk_reward_ratio": 2},
          "decision_cap": {"anchors_available": qb["fair_value_summary"]["anchors_available"],
                           "fair_value_confidence": qb["fair_value_summary"]["confidence"], "lane_data_quality_low": low_quality}}
    D.atomic_json(tmp_path / "p3.json", p3)
    assert R.main(["compute", rid, "--p3-input", str(tmp_path / "p3.json")]) == 0
    decision = D.read_json(directory / "decision.json")
    from compute_price_framework import build_full_output
    mhp = build_full_output(D.read_json(directory / "quant.json"), {})["multi_horizon_price_framework"]
    D.atomic_json(tmp_path / "mhp_input.json", {})
    p4 = {"ticker": "ZZRUN", "final_decision": decision["final_decision"], "analysis_price": 100,
          "time_horizon": "mid", "sector": "Technology",
          "multi_horizon_price_framework": mhp,
          "technical": {"key_levels": {"support": 90, "resistance": 120}, "rs_rating": 60, "distance_50ma_pct": 0},
          "phase0": {"ftd": {"state": "NO_SIGNAL", "days_since_ftd": None}, "macro_backdrop_score": 0},
          "phase3": {"position_size_cap_pct": 100, "polar_position_cap_pct": 100, "hot_zone_probe": False,
                     "t4_resolution": "NONE", "binary_classification": "positive", "binary_event_within_48h": False},
          "mandatory_risk_flags": [], "concentration": {"active_same_sector_confirmed": 0},
          "risk_manager": {"final_position_cap_pct": 5}, "tail_risk": {"fragility_label": "ROBUST", "tail_risk_score": 12}}
    D.atomic_json(tmp_path / "p4.json", p4)
    assert R.main(["compute", rid, "--p3-input", str(tmp_path / "p3.json"), "--p4-input", str(tmp_path / "p4.json"),
                   "--mhp-input", str(tmp_path / "mhp_input.json")]) == 0
    qual = {"schema": "p5-qualitative/1.0", "ticker": "ZZRUN", "date": D.read_json(directory / "snapshot.json")["analysis_at"][:10],
            "lanes": {n: {"signal": "HOLD", "key_factors": ["fixture evidence"], "risk_flags": []} for n in D.LANES},
            "red_team": {k: v for k, v in rt.items() if k not in {"ticker", "subagent_isolated"}},
            "burry_narrative": "fixture", "conflict_bias": cb, "macro_context": "fixture",
            "lane_detail": {"news": {"pt_revision_momentum": {"direction": "UNKNOWN", "unavailable_reason": "offline fixture"}}},
            "watch_conditions": {"revenue": "next filing", "price": "next close", "risk": "next window"},
            "key_risks": ["fixture uncertainty"], "bias_notes": "fixture",
            "phase2_fanout_mode": "PARALLEL_SUBAGENT", "degraded_analysts": [], "decision_point_days": 21,
            "devils_advocate_filed": True, "trade_metadata": {"event_tag": "none"}, "last_outcome": "UNKNOWN"}
    D.atomic_json(tmp_path / "qual.json", qual)
    capsys.readouterr()
    return qual


def test_phase46_cap_wired_through_final_commit(run, tmp_path, capsys):
    rid, directory = run
    complete_engines(run, tmp_path, capsys, confidence=.8, low_quality=True)
    history = tmp_path / "history.json"
    D.atomic_json(history, [])
    assert R.main(["finalize", rid, "--qualitative", str(tmp_path / "qual.json"),
                   "--history", str(history)]) == 0
    entry = D.read_json(history)[0]
    trade = entry["trades_this_session"][0]
    assert D.read_json(directory / "decision.json")["avg_confidence"] == .8
    assert trade["avg_confidence"] == .65
    assert trade["position_size_pct"] == 0.0
    assert trade["final_action"] == "CANCEL"
    assert trade["phase4_6"]["decision_cap_reason"] == "low_data_quality"
    assert D.read_json(directory / "bundle.json")["phase4"]["position_size_pct"] == 0.0
    # Re-stamping cannot conceal a disconnected governor or a null position.
    import append_session_export as A
    for field, value in (("phase4_6", None), ("position_size_pct", None), ("avg_confidence", .8)):
        bad = copy.deepcopy(entry)
        bad["trades_this_session"][0][field] = value
        A._stamp_provenance(bad)
        path = tmp_path / ("bad_" + field + ".json")
        D.atomic_json(path, bad)
        with pytest.raises(ValueError, match="Phase 4.6"):
            R.command(["investment/scripts/validate_session_export.py", "--history", path])


def test_finalize_failure_is_observed_and_retry_commits_once(run, tmp_path, capsys):
    rid, directory = run
    qual = complete_engines(run, tmp_path, capsys)
    bad = copy.deepcopy(qual)
    bad["schema"] = "invalid"
    D.atomic_json(tmp_path / "bad_qual.json", bad)
    history = tmp_path / "history.json"
    D.atomic_json(history, [])
    assert R.main(["finalize", rid, "--qualitative", str(tmp_path / "bad_qual.json"),
                   "--history", str(history)]) == 1
    st = D.read_json(directory / "manifest.json")["stages"]["finalize"]
    assert st["failure_kind"] == "schema" and st["attempts"] == 1
    assert st["elapsed_seconds"] >= 0 and len(st["failures"]) == 1
    assert D.read_json(history) == []
    argv = ["finalize", rid, "--qualitative", str(tmp_path / "qual.json"), "--history", str(history)]
    assert R.main(argv) == 0 and R.main(argv) == 0
    assert len(D.read_json(history)) == 1
    assert D.read_json(directory / "manifest.json")["stages"]["finalize"]["attempts"] == 2


def test_strategy_replay_applies_final_cap(run, tmp_path, capsys, monkeypatch):
    import run_observability as O
    rid, directory = run
    complete_engines(run, tmp_path, capsys, confidence=.8, low_quality=True)
    p3 = D.read_json(directory / "p3_input.json")
    decision = D.read_json(directory / "decision.json")
    decision["final_decision"] = "BUY"
    governed = O.final_replay(directory, p3, decision)
    assert governed["final_decision"] == "HOLD" and governed["avg_confidence"] == .65
    assert governed["position_size_pct"] <= .003
    history = tmp_path / "history.json"
    D.atomic_json(history, [])
    assert R.main(["finalize", rid, "--qualitative", str(tmp_path / "qual.json"),
                   "--history", str(history)]) == 0
    calls = []
    real = O.final_replay
    def recorded(*args):
        calls.append(args[0])
        return real(*args)
    monkeypatch.setattr(O, "final_replay", recorded)
    proposals = O.strategy_proposals(directory.parent)
    assert len(calls) >= 3
    assert proposals["automatic_activation"] is False
    assert len(proposals["candidates"][2]["affected_runs"]) == 2


def test_red_team_factor_touch_rates_keep_unknown_and_stock_clusters():
    from run_observability import calibrate
    records = []
    for i, (ticker, touch) in enumerate((("A", True), ("A", True), ("B", False), ("C", None))):
        records.append({"source": "deep-dive", "decision_id": str(i), "tickers": [ticker],
            "evaluation": {"calibration_eligible": True},
            "decision_content": {"execution_quality": "complete", "red_team_verdict": "STRONG_COUNTER"},
            "reality_at_eval": {"ticker_reality": {"return_pct": -3, "max_drawdown_pct": -5},
                                "trade_condition_evaluation": {"stop_loss_touched": touch}}})
    report = calibrate({"decisions": records})
    stats = report["groups"]["verdict"]["STRONG_COUNTER"]["stop_loss_touched"]
    assert stats["observations"] == 3 and stats["independent_tickers"] == 2
    assert stats["ticker_weighted_mean"] == .5
    assert stats["max_ticker_share"] == 2 / 3
    assert stats["cluster_bootstrap_95ci"] is not None


def test_health_reports_uncommitted_prompt_tamper(run):
    from run_observability import health
    _, directory = run
    manifest = D.read_json(directory / "manifest.json")
    manifest["offline_fixture"] = False  # exercise production observations, no network
    D.atomic_json(directory / "manifest.json", manifest)
    D.atomic_json(directory / "prompts/news.json", {"tampered": True})
    report = health(directory.parent)
    assert report["invalid_evidence_runs"] == 1
    assert report["evidence_failure_rate"] == 1
    assert report["committed"] == 0 and report["errors"][0]["error"] == "run_evidence_failed"


def test_raw_burry_skill_value_reaches_engine_veto(run, tmp_path, capsys):
    complete_engines(run, tmp_path, capsys, {"burry_score": 15, "verdict": "AVOID"})
    _, directory = run
    p3 = D.read_json(directory / "p3_input.json")
    assert p3["burry"]["score"] == 15 and p3["burry"]["veto_flag"] is True
    assert D.read_json(directory / "decision.json")["auto_reject"]["triggered"] is True
    context = D.read_json(directory / "prompts/red_team.json")["pm_context"]
    assert context["burry"] == p3["burry"]
    bad = copy.deepcopy(p3)
    bad["burry"]["score"] = 90
    D.atomic_json(tmp_path / "bad-burry.json", bad)
    assert R.main(["compute", run[0], "--p3-input", str(tmp_path / "bad-burry.json")]) == 1


def test_burry_missing_and_conflicting_source_rejected():
    with pytest.raises(ValueError, match="missing"):
        R.canonical_burry({})
    with pytest.raises(ValueError, match="disagrees"):
        R.canonical_burry({"burry_score": 15, "score": 90})
    with pytest.raises(ValueError, match="veto_flag"):
        R.canonical_burry({"burry_score": 15, "veto_flag": False})
    assert R.canonical_burry({"score": None, "missing_reason": "source transport failed"})["veto_flag"] is None


@pytest.mark.parametrize("run", ["profitable", "loss", "insufficient_peers"], indirect=True)
def test_full_entry_commit_and_shadow_tamper(run, tmp_path, capsys):
    rid, directory = run
    qual = complete_engines(run, tmp_path, capsys)
    history = tmp_path / "history.json"
    D.atomic_json(history, [])
    argv = ["finalize", rid, "--qualitative", str(tmp_path / "qual.json"), "--history", str(history)]
    assert R.main(argv) == 0
    assert R.main(argv) == 0
    entries = D.read_json(history)
    assert len(entries) == 1 and entries[0]["session_export_version"] == "V5.5"
    assert entries[0]["trades_this_session"][0]["sentiment_det"]
    assert (directory / "report.md").is_file()
    assert entries[0]["trades_this_session"][0]["technical_lane"]["pattern_taxonomy"]["pattern"] == "consolidation"
    assert "fixture confirmation" in (directory / "report.md").read_text()
    # A new valid provenance stamp cannot conceal tampered program-owned inputs.
    import append_session_export as A
    bad = copy.deepcopy(entries[0])
    bad["trades_this_session"][0]["det_inputs"]["altman_z"] = 42
    A._stamp_provenance(bad)
    D.atomic_json(tmp_path / "bad_export.json", bad)
    with pytest.raises(ValueError, match="V5.5 run evidence"):
        R.command(["investment/scripts/validate_session_export.py", "--history", tmp_path / "bad_export.json"])
    # Seed a disconnected gate in an isolated namespace. This same bad export
    # passes there, proving the real-entry rejection above depends on the wire.
    validator = HERE / "validate_session_export.py"
    original = validator.read_text()
    wire = "    check_run_evidence(entry, errors)"
    assert wire in original
    scope = {"__file__": str(validator), "__name__": "v55_disconnected_gate_mutant"}
    exec(compile(original.replace(wire, "    pass  # deliberately disconnected"), str(validator), "exec"), scope)
    with pytest.raises(SystemExit) as bypass:
        scope["main"](["--history", str(tmp_path / "bad_export.json")])
    assert bypass.value.code == 0, "mutation must specifically disconnect the run-evidence guard"
    bad_burry = copy.deepcopy(entries[0])
    bad_burry["trades_this_session"][0]["burry_score"] = None
    A._stamp_provenance(bad_burry)
    D.atomic_json(tmp_path / "bad_burry_export.json", bad_burry)
    with pytest.raises(ValueError, match="Burry export score"):
        R.command(["investment/scripts/validate_session_export.py", "--history", tmp_path / "bad_burry_export.json"])
    from scripts.extractors.committed_investment import load_committed
    D.atomic_json(tmp_path / "bad_burry_history.json", [bad_burry])
    records, diagnostics, covered = load_committed(tmp_path / "bad_burry_history.json")
    assert records == [] and diagnostics[0]["reason"] == "run_evidence_mismatch"
    assert (entries[0]["export_date"], "ZZRUN") in covered  # cannot launder through Markdown
    qual["bias_notes"] = "different"
    D.atomic_json(tmp_path / "qual.json", qual)
    assert R.main(argv) == 1


@pytest.mark.parametrize("slots", [1, 2, 3])
def test_five_lanes_bounded_independent_and_resume(run, tmp_path, capsys, slots):
    rid, directory = run
    before = {n: D.read_json(directory / f"prompts/{n}.json") for n in D.LANES}
    completed = set()
    for _ in range(5):
        assert R.main(["claim", rid, "--slots", str(slots), "--model", "offline-fixture"]) == 0
        claimed = json.loads(capsys.readouterr().out)["claimed"]
        assert 0 < len(claimed) <= slots
        for n in claimed:
            score = D.read_json(directory / "quant.json")["quant_blocks"]["valuation_pack"]["score"] if n == "valuation" else 1
            output = {"ticker": "ZZRUN", "score": score, "confidence": .6, "signal": "HOLD",
                      "key_factors": ["independent fixture"], "risk_flags": [], "subagent_isolated": True}
            if n == "news":
                output["pt_revision_momentum"] = {"direction": "UNKNOWN", "unavailable_reason": "fixture"}
            path = tmp_path / (n + ".json")
            D.atomic_json(path, output)
            assert R.main(["accept", rid, "--stage", n, "--result", str(path)]) == 0
            capsys.readouterr()
            completed.add(n)
        assert R.main(["resume", rid]) == 0
        status = json.loads(capsys.readouterr().out)
        assert not (completed & set(status["ready"]))
        for n in D.LANES:
            assert D.read_json(directory / f"prompts/{n}.json") == before[n]
            assert "independent fixture" not in json.dumps(before[n]["input"])
        if len(completed) == 5:
            break
    assert completed == set(D.LANES)


def test_tampered_snapshot_refused_through_status(run):
    rid, directory = run
    snap = D.read_json(directory / "snapshot.json")
    snap["price"] = 999
    D.atomic_json(directory / "snapshot.json", snap)
    assert R.main(["status", rid]) == 1


def test_prompt_tamper_refused_through_claim(run):
    rid, directory = run
    D.atomic_json(directory / "prompts/news.json", {"contaminated": True})
    assert R.main(["claim", rid, "--model", "fixture"]) == 1


def test_expired_resume_refused(run, monkeypatch):
    rid, directory = run
    now = D.timestamp(D.read_json(directory / "snapshot.json")["analysis_at"])
    monkeypatch.setattr(D, "utcnow", lambda: (now + timedelta(hours=4)).isoformat())
    assert R.main(["resume", rid]) == 1


def test_missing_fresh_quote_prepare_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "RUNS", tmp_path / "runs")
    data = package()
    data["sources"]["quote"]["fetched_at"] = (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat()
    path = tmp_path / "stale.json"
    D.atomic_json(path, data)
    assert R.main(["prepare", "--ticker", "ZZRUN", "--package", str(path)]) == 1


def test_prepare_collects_optional_failure_without_stale_fallback(tmp_path, monkeypatch, capsys):
    import subprocess
    from types import SimpleNamespace
    import collect_run_inputs as C
    import compute_price_framework as Q
    import skills._shared.investment_data as I
    period = "2026-06-30"
    calls = []
    real_run = subprocess.run
    def script(args, **kwargs):
        if "--worker" not in args:
            return real_run(args, **kwargs)
        name = args[args.index("--worker") + 1]
        calls.append(name)
        fail = name == "forecaster"
        payload = {"status": "error", "reason": "insufficient PE history from ratios endpoint"} if fail else {"ticker": "ZZRUN"}
        return SimpleNamespace(returncode=1 if fail else 0, stdout=json.dumps(payload), stderr="")
    monkeypatch.setattr(C.subprocess, "run", script)
    monkeypatch.setattr(R, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(R, "ROOT", tmp_path)
    monkeypatch.setattr(R, "producer_version", lambda: "fixture-producer")
    original_command = R.command
    def command(args, **kwargs):
        if "phase1_factpack.py" in str(args[0]):
            assert len(calls) == 0  # earnings refresh precedes lane scripts
            return json.dumps({"ticker": "ZZRUN", "source_records": {}, "bundles": {}})
        # Production validator runs against the exact copied Phase 0.
        return original_command([D.ROOT / args[0], *args[1:]], **kwargs)
    monkeypatch.setattr(R, "command", command)
    class Cache:
        def __init__(self, *args):
            self.sources, self.metrics = {}, {}
        def get(self, path, params, **kwargs):
            if path.endswith("income-statement"):
                return [{"date": period}]
            if path.endswith("quote"):
                assert len(calls) == 7  # quote is fetched only after collection
                data = [{"price": 100}]
                self.sources["quote"] = D.source(data, kind="quote", fetched_at=D.utcnow())
                return data
            return []
    monkeypatch.setattr(I, "SourceCache", Cache)
    ea = tmp_path / f"skills/earnings-analyst/cache/ZZRUN_{period}.json"
    D.atomic_json(ea, {"source_records": {"income": D.source([{"date": period}], kind="financial", fetched_at=D.utcnow(), period=period)}})
    # A previously successful cache must not hide this run's source failure.
    old = tmp_path / "skills/earnings-valuation-forecaster/cache/ZZRUN.json"
    D.atomic_json(old, {"source_fetched_at": D.utcnow(), "financial_period": period, "sentinel": "old"})
    monkeypatch.setattr(Q, "fetch_volatility", lambda *args, **kw: {"sigma_daily": .02})
    monkeypatch.setattr(Q, "assemble_inputs", lambda ticker, inp, **kw: inp.update(package()["quant_input"]))
    p0 = tmp_path / "phase0_source.json"
    D.atomic_json(p0, package()["sources"]["phase0"]["data"])
    assert R.main(["prepare", "--ticker", "ZZRUN", "--phase0", str(p0)]) == 0
    info = json.loads(capsys.readouterr().out)
    directory = R.run_dir(info["run_id"])
    snap = D.load_snapshot(directory / "snapshot.json")
    assert snap["sources"]["forecaster"]["data"] is None
    assert snap["sources"]["forecaster"]["status"] == "unavailable"
    assert "PE history" in snap["sources"]["forecaster"]["reason"]
    assert D.read_json(directory / "raw/forecaster.receipt.json")["returncode"] == 1
    assert D.read_json(directory / "raw/forecaster.json")["status"] == "error"
    assert len(list((directory / "prompts").glob("*.json"))) == 5
    assert R.main(["status", info["run_id"]]) == 0


def test_failed_result_and_quota_do_not_repeat_model(run, capsys, tmp_path):
    rid, directory = run
    assert R.main(["claim", rid, "--model", "fixture"]) == 0
    lane = json.loads(capsys.readouterr().out)["claimed"][0]
    bad = tmp_path / "bad.json"
    D.atomic_json(bad, {"ticker": "ZZRUN", "score": float(2), "provenance": "llm"})
    assert R.main(["accept", rid, "--stage", lane, "--result", str(bad)]) == 1
    assert R.main(["claim", rid, "--stage", lane, "--model", "fixture"]) == 0
    assert R.main(["fail", rid, "--stage", lane, "--reason", "quota"]) == 0
    assert R.main(["claim", rid, "--model", "fixture"]) == 1
    assert D.read_json(directory / "manifest.json")["stages"][lane]["attempts"] == 2


def test_cache_source_clock_period_and_failures(tmp_path):
    calls = []
    status = {"value": "ok"}
    def transport(path, params, **kwargs):
        calls.append(path)
        return {"status": status["value"], "data": [{"date": "2026-06-30", "price": 100}] if status["value"] == "ok" else None}
    cache = SourceCache(tmp_path, period="2026-06-30", transport=transport)
    cache.get("/stable/discounted-cash-flow", {"symbol": "T"})
    record = copy.deepcopy(next(iter(cache.sources.values())))
    cache.get("/stable/discounted-cash-flow", {"symbol": "T"})
    assert len(calls) == 1 and cache.metrics["cache_hits"] == 1
    assert next(iter(cache.sources.values()))["fetched_at"] == record["fetched_at"]
    # Rewriting a source file does not renew its TTL.
    dest = next((tmp_path / "market").glob("*.json"))
    expired = copy.deepcopy(record)
    expired["fetched_at"] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    D.atomic_json(dest, expired)
    status["value"] = "rate_limited"
    assert cache.get("/stable/discounted-cash-flow", {"symbol": "T"}) is None
    assert D.read_json(dest)["fetched_at"] == expired["fetched_at"]
    assert next(iter(cache.sources.values()))["status"] == "rate_limited"
    status["value"] = "ok"
    cache.period = "2026-09-30"
    cache.get("/stable/discounted-cash-flow", {"symbol": "T"})
    assert D.read_json(dest)["financial_period"] == "2026-09-30"


def test_quote_legacy_mtime_not_trusted(tmp_path):
    calls = []
    def transport(*a, **kw):
        calls.append(1)
        return {"status": "empty", "data": []}
    cache = SourceCache(tmp_path, transport=transport)
    key = D.digest({"path": "/stable/quote", "params": {"symbol": "T"}}).split(":")[1]
    D.atomic_json(tmp_path / "quote" / (key + ".json"), {"data": [{"price": 100}]})
    assert cache.get("/stable/quote", {"symbol": "T"}) is None
    assert calls


def test_specified_phase0_wins(monkeypatch, tmp_path):
    import compute_price_framework as C
    p0 = tmp_path / "selected.json"
    D.atomic_json(p0, {"fred_snapshot": {"real_rate_preferred": 2.0}})
    sources = {"earnings": {}, "quote": [{"price": 100}], "risk_free": (None, None)}
    inp = {"ticker": "T", "current_price": 100}
    C.assemble_inputs("T", inp, phase0_path=p0, sources=sources)
    assert inp["fred"]["treasury_10y_real"] == .02


def test_finalize_requires_dependency_gate(run, tmp_path):
    rid, _ = run
    assert R.main(["finalize", rid, "--qualitative", str(tmp_path / "missing.json")]) == 1


def test_shadow_protection_and_idempotent_append(tmp_path):
    import append_session_export as A
    path = tmp_path / "history.json"
    D.atomic_json(path, [])
    entry = {"session_export_version": "V5.5", "run_context": {"run_id": "T_one"},
             "trades_this_session": [{"ticker": "T", "det_shadow": {"x": 1}, "lane_contract": {"a": 1}}]}
    A._stamp_provenance(entry)
    assert A._atomic_append(entry, path) == 1
    assert A._atomic_append(entry, path) == 1
    entry["trades_this_session"][0]["det_shadow"]["x"] = 2
    assert not A._valid_provenance(entry)
    with pytest.raises(SystemExit):
        A._atomic_append(entry, path)


def test_json_authority_synthetic_and_cluster_exclusions(tmp_path):
    from scripts.extractors.committed_investment import load_committed, evaluation_metadata
    from run_observability import calibrate, cluster_summary
    import append_session_export as A
    e = {"session_export_version": "V5.4", "export_date": "2026-09-01", "ticker": "T",
         "trades_this_session": [{"ticker": "T", "final_decision": "HOLD", "final_action": "CANCEL"}]}
    A._stamp_provenance(e)
    path = tmp_path / "history.json"
    D.atomic_json(path, [e, e])
    rows, diagnostics, covered = load_committed(path)
    assert len(rows) == 1 and not diagnostics and ("2026-09-01", "T") in covered
    assert rows[0]["decision_content"]["final_decision"] == "HOLD"
    assert rows[0]["classification"]["industry"] is None
    pending = evaluation_metadata(rows[0], {"pending": True, "window_complete_pct": 50}, today="2026-09-30")
    assert not pending["calibration_eligible"]
    rows[0]["evaluation"] = {"calibration_eligible": True}
    rows[0]["decision_content"]["red_team_synthetic"] = True
    assert calibrate({"decisions": rows})["excluded"]["synthetic_red_team"] == 1
    stats = cluster_summary([{"ticker": "T", "return_pct": 2}] * 10, "return_pct")
    assert stats["independent_tickers"] == 1 and stats["cluster_bootstrap_95ci"] is None


def test_lane_visibility_and_audit_isolation():
    factpack = {"ticker": "T", "bundles": {"earnings_analyst_bundle": {"secret": "earnings"},
        "peer_bundle": {"peers": ["PEER"]}, "ticker_data_bundle": {"scoring": {"price": 100}, "_audit": {"price": 999}},
        "fmp_supp_bundle": {"quality_scores": {"z": 3}, "ma_events": ["news"], "insider_summary": {"ratio": 2}, "source_records": {"raw": "all"}}}}
    assert R.lane_factpack(factpack, "technical")["bundles"] == {"fmp_supp_bundle": {"insider_summary": {"ratio": 2}}}
    news = R.lane_factpack(factpack, "news")["bundles"]
    assert set(news) == {"ticker_data_bundle", "fmp_supp_bundle"}
    assert news["fmp_supp_bundle"] == {"ma_events": ["news"]}
    assert "_audit" not in json.dumps(news) and "source_records" not in json.dumps(news)


def test_program_shadow_known_values_and_immutable_classification(run):
    from run_exports import attach
    rid, directory = run
    snap = D.read_json(directory / "snapshot.json")
    snap["lane_inputs"]["sentiment"]["script_output"] = {"composite_score": 60,
        "ticker_signals": {"short_pct_float": 5, "insider_stats": [{"acquired_disposed_ratio": 2}]}}
    snap["sources"]["raw_inputs"] = {"data": {"supplementary": {"quality_scores": {"altmanZScore": 3.5}},
        "earnings": {"ttm_metrics": {"from_key_metrics_ttm": {"freeCashFlowYieldTTM": .03},
                                    "from_ratios_ttm": {"debtToEquityRatioTTM": .4}}}}}
    entry = {"trades_this_session": [{"ticker": "ZZRUN", "lane_scores": dict.fromkeys(D.LANES, 0)}]}
    attach(entry, directory, D.read_json(directory / "manifest.json"), snap)
    trade = entry["trades_this_session"][0]
    assert trade["sentiment_det"]["score"] is not None
    assert trade["det_inputs"]["altman_z"] == 3.5
    assert trade["det_inputs"]["insider_ratio_q"] == 2
    assert trade["det_inputs"]["fcf_yield"] == .03
    assert entry["run_context"]["classification"] == snap["classification"]


def test_evaluation_identity_ambiguity_and_label_preservation(tmp_path):
    from scripts.extractors.committed_investment import resolve_record, preserve_evaluations
    records = [{"source": "deep-dive", "decision_id": n, "decision_date": "2026-09-01", "tickers": ["T"],
                "legacy_ids": ["deep-dive_T_2026-09-01"], "classification": {"industry": "then"},
                "verdict": {"label": "new"}, "original_label": "original"} for n in ("run_one", "run_two")]
    with pytest.raises(ValueError, match="ambiguous"):
        resolve_record(records, date="2026-09-01", ticker="T")
    assert resolve_record(records, decision_id="run_two")["decision_id"] == "run_two"
    previous = {"decisions": [{"decision_id": "run_one", "verdict": {"label": "old"}}]}
    ids = preserve_evaluations(records, previous, tmp_path, "2026-09-30")
    assert ids["ambiguous_legacy_ids"]
    assert records[0]["prior_evaluations"] == [{"label": "old"}]
    assert records[0]["classification"]["industry"] == "then"
    assert any(D.read_json(p)["original_label"] == "original" for p in tmp_path.glob("*.json"))


def test_engine_input_tamper_fails_status(run, tmp_path, capsys):
    rid, directory = run
    complete_engines(run, tmp_path, capsys)
    data = D.read_json(directory / "p4_input.json")
    data["analysis_price"] = 999
    D.atomic_json(directory / "p4_input.json", data)
    assert R.main(["status", rid]) == 1


def test_frozen_quant_does_not_read_latest_artifacts(monkeypatch):
    import compute_price_framework as C
    inp = package()["quant_input"]
    inp["anchors"]["dcf_self_built"] = None
    inp["script_artifacts"] = {}
    monkeypatch.setattr(C.os.path, "getmtime", lambda p: pytest.fail("mutable cache read"))
    out = C.build_quant_stage(inp)
    assert out["quant_blocks"]["valuation_pack"]["anchors"]["dcf_self_built"]["reason"] == C.SCRIPT_NOT_RUN


def test_index_entry_json_beats_conflicting_markdown(tmp_path, monkeypatch):
    import scripts.build_event_index as index
    import scripts._sector_heat as heat
    import append_session_export as A
    entry = {"session_export_version": "V5.4", "export_date": "2026-09-01", "ticker": "T",
             "phase0_macro_snapshot": {"market_regime": "THEN"},
             "trades_this_session": [{"ticker": "T", "final_decision": "HOLD", "final_action": "CANCEL"}]}
    A._stamp_provenance(entry)
    D.atomic_json(tmp_path / "investment/invest_logs/history.json", [entry])
    report = tmp_path / "reports/20260901_T.md"
    report.parent.mkdir(parents=True)
    report.write_text("conflicting Markdown BUY")
    monkeypatch.setattr(index, "ROOT", tmp_path)
    monkeypatch.setattr(index, "discover_sources", lambda: {"deep-dive": [report]})
    monkeypatch.setitem(index.EXTRACTOR_DISPATCH, "deep-dive", lambda p: {"decision_date": "2026-09-01", "tickers": ["T"], "decision_content": {"final_decision": "BUY"}})
    monkeypatch.setattr(index, "build_eval_block", lambda rec, today: ({"pending": True, "window_complete_pct": 50}, {"label": "pending"}))
    monkeypatch.setattr(heat, "enrich_ticker_heat", lambda t: {"industry": "TODAY"})
    index.main(datetime.now().date())
    result = D.read_json(tmp_path / "reports/decision_review/event_index_latest.json")
    rows = result["decisions"]
    assert len(rows) == 1 and rows[0]["decision_content"]["final_decision"] == "HOLD"
    assert rows[0]["classification"]["regime"] == "THEN"
    assert rows[0]["classification"]["industry"] is None
    assert not rows[0]["evaluation"]["calibration_eligible"]


def test_phase0_copy_tamper_rejected(run):
    rid, directory = run
    p0 = D.read_json(directory / "phase0.json")
    p0["macro_summary"]["market_regime"] = "OTHER"
    D.atomic_json(directory / "phase0.json", p0)
    assert R.main(["status", rid]) == 1


def test_pattern_shape_rejected_at_accept(run, tmp_path):
    rid, directory = run
    assert R.main(["claim", rid, "--stage", "technical", "--model", "fixture"]) == 0
    output = {"ticker": "ZZRUN", "score": 0, "confidence": .6, "signal": "HOLD",
              "key_factors": [], "risk_flags": [], "subagent_isolated": True,
              "pattern_taxonomy": "consolidation"}
    path = tmp_path / "bad_technical.json"
    D.atomic_json(path, output)
    assert R.main(["accept", rid, "--stage", "technical", "--result", str(path)]) == 1
    assert D.read_json(directory / "manifest.json")["stages"]["technical"]["status"] == "retry"


def test_finalize_cannot_bypass_producer_change(run, tmp_path, capsys, monkeypatch):
    rid, directory = run
    complete_engines(run, tmp_path, capsys)
    monkeypatch.setattr(R, "producer_version", lambda: "changed")
    assert R.main(["finalize", rid, "--qualitative", str(tmp_path / "qual.json"), "--history", str(tmp_path / "history.json")]) == 1
    assert not (tmp_path / "history.json").exists()


@pytest.mark.parametrize("name", ["fundamentals", "sentiment", "news", "technical", "dcf", "comps", "forecaster"])
def test_collector_worker_bootstraps_real_script_imports(name, tmp_path, monkeypatch):
    import collect_run_inputs as C
    mapping = C.commands("T")
    monkeypatch.setattr(C, "commands", lambda ticker: {k: [v[0], "--help"] for k, v in mapping.items()})
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(sys, "argv", list(sys.argv))
    monkeypatch.setenv("AIC_INVESTMENT_PERIOD", "fixture")
    receipt = tmp_path / "sources.json"
    with pytest.raises(SystemExit) as result:
        C.worker(name, "T", "2026-06-30", receipt)
    assert result.value.code == 0
    assert D.read_json(receipt)["source_records"] == {}


def test_legacy_summary_fills_only_unambiguous_markdown_gaps():
    from scripts.extractors.committed_investment import from_entry, supplement_legacy
    raw = {"date": "2026-04-07", "ticker": "T", "final_action": "CANCEL", "metadata": {"final_score": -2.1}}
    rec = from_entry(raw, "history#0")
    md = {"decision_date": "2026-04-07", "tickers": ["T"], "raw_path": "report.md",
          "decision_content": {"final_score": 5, "final_action": "EXECUTE", "final_decision": "HOLD"}}
    result = supplement_legacy(rec, [md])
    assert result["decision_content"]["final_score"] == -2.1
    assert result["decision_content"]["final_action"] == "CANCEL"
    assert result["decision_content"]["final_decision"] == "HOLD"
    assert supplement_legacy(from_entry(raw, "history#0"), [md, md])["identity_ambiguous"] is True


def test_complete_index_window_ignores_only_outside_nan(tmp_path, monkeypatch):
    import scripts.build_event_index as index
    import scripts._sector_heat as heat
    import append_session_export as A
    entry = {"session_export_version": "V5.4", "export_date": "2026-04-07", "ticker": "T",
             "trades_this_session": [{"ticker": "T", "final_decision": "HOLD", "final_action": "CANCEL",
                                      "entry_aggressive": ["$90", "$110"], "take_profit": "125.0", "stop_loss": 80}]}
    A._stamp_provenance(entry)
    D.atomic_json(tmp_path / "investment/invest_logs/history.json", [entry])
    monkeypatch.setattr(index, "ROOT", tmp_path)
    monkeypatch.setattr(index, "discover_sources", lambda: {})
    monkeypatch.setattr(heat, "enrich_ticker_heat", lambda t: {})
    start = datetime(2026, 4, 7).date()
    prices = {(start + timedelta(days=i)).isoformat(): 100 + i for i in range(31)}
    prices["2026-09-30"] = float("nan")
    monkeypatch.setattr(index, "fetch_history", lambda *args: prices)
    index.main(datetime(2026, 10, 1).date())
    path = tmp_path / "reports/decision_review/event_index_latest.json"
    row = D.read_json(path)["decisions"][0]
    assert row["evaluation"]["calibration_eligible"] is True
    assert row["reality_at_eval"]["ticker_reality"]["return_pct"] == 30
    assert row["decision_content"]["trader_proposal"]["entry"] is None
    assert row["decision_content"]["trader_proposal_raw"]["entry"] == ["$90", "$110"]
    assert row["reality_at_eval"]["trade_condition_evaluation"]["entry_price_touched"] is None
    prices["2026-04-10"] = float("nan")
    index.main(datetime(2026, 10, 1).date())
    assert D.read_json(path)["decisions"][0]["evaluation"]["calibration_eligible"] is False


def test_lane_fmp_helpers_share_cache_limiter_and_classified_status(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from skills._shared.investment_data import source_context
    import skills._shared.fmp_supplementary as supp
    def module(name, relative):
        spec = importlib.util.spec_from_file_location(name, D.ROOT / relative)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    fund = module("fund_route", "skills/us-stock-analysis/scripts/analyze.py")
    news = module("news_route", "skills/market-news-analyst/scripts/fetch.py")
    sentiment = module("sent_route", "skills/market-sentiment-analyzer/scripts/sentiment.py")
    dual = module("dual_route", "skills/finnhub-client/scripts/dual_fetch.py")
    calls = []
    def transport(path, params, **kwargs):
        calls.append(path)
        if path.endswith("sector-pe-snapshot"):
            return {"status": "ok", "data": [{"pe": 12}], "http_calls": 1}
        if path.endswith("insider-trading/statistics"):
            return {"status": "ok", "data": [{"year": 2026, "quarter": 2, "acquiredDisposedRatio": 2}], "http_calls": 1}
        return {"status": "permission_denied", "data": None, "http_status": 402, "http_calls": 1}
    cache = SourceCache(tmp_path / "sources", period="2026-06-30", transport=transport)
    monkeypatch.setenv("FMP_API_KEY", "offline-fixture")
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("AIC_INVESTMENT_PERIOD", raising=False)
    monkeypatch.setattr(supp, "get_supplementary_bundle", lambda *a: {})
    monkeypatch.setattr(sentiment.yf, "Ticker", lambda *a: SimpleNamespace(info={}))
    monkeypatch.setattr(sentiment.requests, "get", lambda *a, **kw: pytest.fail("unlimited direct HTTP"))
    with source_context(cache):
        assert fund._fmp_sector_pe("Tech", "offline-fixture") == 12
        assert fund._fmp_sector_pe("Tech", "offline-fixture") == 12
        assert sentiment._fetch_ticker_signals("T")["insider_stats"][0]["acquired_disposed_ratio"] == 2
        assert news._fmp_get("price-target-consensus", "offline-fixture", {"symbol": "T"}) is None
        audit, status = dual.fetch_fmp("T", "offline-fixture", None)
        assert status == "permission_denied" and audit["_source"] == "fmp"
    assert calls.count("/stable/sector-pe-snapshot") == 1
    assert cache.metrics["cache_hits"] == 1
    assert cache.metrics["outcomes"]["permission_denied"] > 0


def test_forecaster_shared_cache_keeps_four_hour_source_clock(tmp_path):
    from skills._shared.investment_data import source_context
    spec = importlib.util.spec_from_file_location("forecast_cache_route", D.ROOT / "skills/earnings-valuation-forecaster/scripts/forecast.py")
    forecast = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(forecast)
    calls = []
    def transport(path, params, **kwargs):
        calls.append(path)
        return {"status": "ok", "data": [{"pe": 12}], "http_calls": 1}
    cache = SourceCache(tmp_path / "sources", period="2026-06-30", transport=transport)
    cache.get("/stable/ratios", {"symbol": "T", "limit": 5})
    path = next((tmp_path / "sources/market").glob("*.json"))
    row = D.read_json(path)
    row["fetched_at"] = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    D.atomic_json(path, row)
    with source_context(cache):
        client = forecast.FMP("offline-fixture")
        assert client.ratios_annual("T") == [{"pe": 12}]
        clock = next(iter(client.sources.values()))["fetched_at"]
        assert clock != row["fetched_at"]
        assert client.ratios_annual("T") == [{"pe": 12}]
        assert next(iter(client.sources.values()))["fetched_at"] == clock
    assert calls == ["/stable/ratios", "/stable/ratios"]


def test_frozen_fred_actual_schema():
    p0 = {"fred_snapshot": {"series": {"DGS10": {"value": 4.75}}}}
    assert R.phase0_risk_free(p0) == (.0475, "fred_phase0")
    assert R.phase0_risk_free({}) == (None, None)
