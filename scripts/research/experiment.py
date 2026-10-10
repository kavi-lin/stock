"""Durable, bounded experiment runner; six-hour clock starts after preflight."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import time
from datetime import datetime, timedelta, timezone

from scripts._shared import broker_gate, research_accounting
from scripts.research import engine, intake, triggers
from scripts.research.store import CACHE, ROOT, Repository, digest, now_iso, parse_time, profile


def call_records(experiment_id, phase=None):
    return [row for row in research_accounting.records()
            if row["context"]["experiment_id"] == experiment_id
            and (phase is None or row["context"]["phase"] == phase)]


def measured(record):
    facts = record.get("settlement", {}).get("usage_details", {}).get("facts", [])
    return bool(facts) and all(all(f["tokens"].get(k) is not None for k in
                                  ("input_tokens", "output_tokens")) for f in facts)


def budget(experiment_id, *, phase, now=None):
    now = now or datetime.now(timezone.utc)
    records = call_records(experiment_id, phase)
    debates = {r["context"]["debate_id"] for r in records}
    recent = {r["context"]["debate_id"] for r in records
              if parse_time(r["started_at"]) > now - timedelta(hours=1)}
    call_cap = 24 if phase == "preflight" else 60
    return {"calls": len(records), "debates": len(debates), "hourly_debates": len(recent),
            "remaining_calls": max(0, call_cap-len(records)),
            "can_start": len(records)+2 <= call_cap and (phase == "preflight" or len(debates) < 30)
            and (phase == "preflight" or len(recent) < 5)}


def fixtures():
    """Explicitly synthetic preflight cases; never enter the live research store."""
    for trigger in ("news", "filing", "calendar", "followup"):
        for variant, description in (
            ("supported", "TestCo (TEST) reports quarterly revenue of 100 units, up from 90 units. The company expects next-quarter revenue of 95 to 105 units."),
            ("conflict", "TestCo (TEST) reports revenue rose from 90 to 100 units. Its corrected release states operating margin declined from 20% to 15%; no explanation is given."),
            ("insufficient", "TestCo (TEST) will publish quarterly results tomorrow. Revenue and earnings have not been released. A social post speculates about a revenue beat without naming a source."),
        ):
            case = trigger + "-" + variant
            raw = {"headline": "SYNTHETIC PREFLIGHT: " + case, "raw_summary": description,
                   "url": "https://example.com/research-preflight/" + case,
                   "published": now_iso(), "source": "Synthetic fixture", "symbol": "TEST"}
            event = intake.normalize(raw)
            event.update(id="pre_" + digest(case), trigger=trigger, eligible=True,
                         materiality=3, state="pending", revision=digest(description),
                         prior_revision=None, updated_at=now_iso(), synthetic=True)
            yield case, event


def preflight(repo, experiment_id):
    checks = repo.get("validation", {})
    if not checks.get("passed"):
        raise ValueError("deterministic validation must pass before paid preflight")
    current = repo.get("experiment")
    if current and current["id"] != experiment_id and current["status"] not in {"complete", "complete_with_gaps"}:
        raise ValueError("another experiment is unfinished")
    state = current or {"id": experiment_id, "status": "preflight", "created_at": now_iso(),
                        "model": "gpt-6-luna", "reasoning_effort": "max", "cases": {}}
    if state["status"] == "preflight_passed":
        return state
    if state["status"] != "preflight":
        raise ValueError("preflight is stopped; resolve the recorded blocker before continuing")
    repo.set("experiment", state)
    fixture_repo = Repository(CACHE / "preflight" / (experiment_id + ".sqlite3"))
    for case, event in fixtures():
        if case in state["cases"]:
            continue
        if not budget(experiment_id, phase="preflight")["can_start"]:
            raise ValueError("preflight budget exhausted")
        event = next((saved for saved in fixture_repo.all("events")
                      if saved["id"] == event["id"]), event)
        fixture_repo.update_event(event)
        try:
            cards = engine.debate(fixture_repo, event, experiment_id=experiment_id, phase="preflight")
            records = call_records(experiment_id, "preflight")
            if any(row["status"] != "acknowledged" or not measured(row) for row in records):
                raise ValueError("preflight token accounting is incomplete")
            state["cases"][case] = {"status": "passed", "cards": len(cards)}
            print(json.dumps({"case": case, "status": "passed", "calls": len(records)}), flush=True)
        except Exception as exc:
            state.update(status="preflight_blocked", blocker=str(exc)[:160], blocked_at=now_iso())
            state["cases"][case] = {"status": "failed", "error": type(exc).__name__}
            repo.set("experiment", state)
            raise
        repo.set("experiment", state)
    state.update(status="preflight_passed", preflight_finished_at=now_iso())
    repo.set("experiment", state)
    return state


def start(repo, experiment_id):
    state = repo.get("experiment", {})
    if state.get("id") != experiment_id or state.get("status") != "preflight_passed":
        raise ValueError("twelve preflight cases must pass before starting the observation")
    if len(state.get("cases", {})) != 12 or not repo.get("validation", {}).get("passed"):
        raise ValueError("preflight or deterministic checks incomplete")
    if any(case.get("status") != "passed" for case in state["cases"].values()):
        raise ValueError("preflight still contains unresolved cases")
    measured_calls = call_records(experiment_id, "preflight")
    if not 12 <= len(measured_calls) <= 24 or any(
            r["status"] != "acknowledged" or not measured(r)
            or r.get("requested_model") != "gpt-6-luna" or r.get("reasoning_effort") != "max"
            for r in measured_calls):
        raise ValueError("preflight model/usage evidence incomplete")
    client = broker_gate.broker_client()
    if client.request("GET", "/v1/ready").get("status") != "ok":
        raise ValueError("broker is not ready")
    research_accounting.flush(client)
    from scripts.research.report import broker_history, reconcile_history
    if reconcile_history(measured_calls, broker_history(experiment_id)):
        raise ValueError("preflight broker history reconciliation failed")
    now = datetime.now(timezone.utc)
    state.update(status="live", started_at=now.isoformat(), deadline=(now+timedelta(hours=6)).isoformat(),
                 heartbeat_at=now.isoformat(), gaps=[], total_debates_limit=30, total_calls_limit=60)
    repo.set("experiment", state)
    settings = profile()
    settings["enabled"] = True
    research_accounting.atomic_json(ROOT / "config/research.json", settings)
    return state


def recover_preflight(repo, experiment_id):
    """Resume only after a resolved accounting outage, never repeat inference."""
    state = repo.get("experiment", {})
    if state.get("id") != experiment_id or state.get("status") != "preflight_blocked":
        raise ValueError("no blocked preflight to recover")
    client = broker_gate.broker_client()
    if client.request("GET", "/v1/ready").get("status") != "ok":
        raise ValueError("broker is not ready")
    research_accounting.flush(client)
    records = call_records(experiment_id, "preflight")
    if not records or any(r["status"] != "acknowledged" or not r.get("schema_valid") or not measured(r)
                          for r in records):
        raise ValueError("recovery requires validated, measured, acknowledged calls")
    fixture_repo = Repository(CACHE / "preflight" / (experiment_id + ".sqlite3"))
    events = fixture_repo.all("events")
    for case, result in state["cases"].items():
        if result["status"] != "failed":
            continue
        event_id = "pre_" + digest(case)
        case_records = [r for r in records if r["context"]["event_id"] == event_id]
        if len(case_records) == 1 and not case_records[0].get("result"):
            # First activation exposed missing durable output before a lost ACK.
            # Its schema gate and measured settlement are proven; do not invent
            # a recovered transcript or buy another inference to replace it.
            result.update(status="passed", coverage="analysis_validation_and_settlement_recovery",
                          limitation="analysis transcript was not persisted; no B turn for this case")
        else:
            state["cases"].pop(case)
            saved = next(e for e in events if e["id"] == event_id)
            saved["state"] = "pending"
            fixture_repo.update_event(saved)
            break
    state.setdefault("recovered_faults", []).append({"at": now_iso(), "blocker": state.pop("blocker", None)})
    state["status"] = "preflight"
    repo.set("experiment", state)
    return state


def retry_invalid_preflight(repo, experiment_id):
    """A repaired schema path may spend the remaining approved budget once."""
    state = repo.get("experiment", {})
    if state.get("id") != experiment_id or state.get("status") != "preflight_blocked":
        raise ValueError("no blocked preflight")
    records = call_records(experiment_id, "preflight")
    if any(r["status"] != "acknowledged" or not measured(r) for r in records):
        raise ValueError("all usage must be reconciled before another call")
    latest = max(records, key=lambda r: r["started_at"])
    if latest.get("settlement", {}).get("error_class") != "invalid_output":
        raise ValueError("only schema-invalid output may use this retry path")
    remaining_cases = 12 - sum(c["status"] == "passed" for c in state["cases"].values())
    if len(records) + remaining_cases * 2 > 24:
        raise ValueError("remaining approved preflight budget cannot cover all cases")
    fixture_repo = Repository(CACHE / "preflight" / (experiment_id + ".sqlite3"))
    for case, outcome in list(state["cases"].items()):
        if outcome["status"] == "failed":
            state.setdefault("failed_attempts", []).append({"case":case, "call_id":latest["call_id"],
                "reason":"invalid source quotation rejected; constrained citation schema added"})
            del state["cases"][case]
            item = next(e for e in fixture_repo.all("events") if e["id"] == "pre_"+digest(case))
            item.pop("debate_id", None)
            item.update(state="pending")
            fixture_repo.update_event(item)
    state.update(status="preflight", blocker=None)
    repo.set("experiment", state)
    return state


def tick(repo, *, now=None, poll_fn=intake.poll, debate_fn=engine.debate,
         state_key="experiment", budget_fn=budget):
    if state_key not in {"experiment", "service"}:
        raise ValueError("invalid research runtime")
    now = now or datetime.now(timezone.utc)
    state = repo.get(state_key, {})
    if state.get("status") not in {"live", "live_blocked"}:
        return state
    if state_key == "experiment" and now >= parse_time(state["deadline"]):
        return finish(repo)
    previous = parse_time(state.get("heartbeat_at"))
    if previous and (now-previous).total_seconds() > 180:
        state["gaps"].append({"from": previous.isoformat(), "to": now.isoformat(),
                              "seconds": (now-previous).total_seconds()})
    state["heartbeat_at"] = now.isoformat()
    state["budget"] = budget_fn(state["id"], phase="live", now=now)
    repo.set(state_key, state)
    last_poll = parse_time((repo.get("last_poll") or {}).get("at"))
    if last_poll is None or (now-last_poll).total_seconds() >= 600:
        poll_fn(repo)
    triggers.scan(repo, now)
    if state['status'] == 'live_blocked' and state.get('blocker') == 'broker:refused(provider_busy)':
        # Availability reads are not inference retries. Only a changed broker
        # state permits another reserve; quota/auth failures stay stopped.
        try:
            snapshot = broker_gate.broker_client().request('GET', '/v1/status')
            active = snapshot['active_reservations']
        except Exception:
            return state
        if not isinstance(active, list) or any(row.get('provider') == 'codex' for row in active):
            return state
        item = next((e for e in repo.all('events') if e['id'] == state.get('blocked_event_id')), None)
        if item is None:
            return state
        prior = [r for r in call_records(state['id'], 'live')
                 if r['context']['debate_id'] == item.get('debate_id')]
        if any(r['status'] != 'acknowledged' or not r.get('schema_valid') or not measured(r)
               or not r.get('result') for r in prior):
            return state
        item['state'] = 'pending'
        repo.update_event(item)
        state.setdefault('provider_waits', []).append({
            'from':state.get('blocked_at'), 'to':now.isoformat(), 'event_id':item['id'],
            'reason':'provider_busy', 'resume_evidence':'broker reports no active codex reservation'})
        state.update(status='live', blocker=None)
        repo.set(state_key, state)
    if state["status"] == "live_blocked":
        pending_delivery = [r for r in call_records(state["id"], "live") if r["status"] == "pending"]
        if not pending_delivery:
            return state
        try:
            research_accounting.flush(broker_gate.broker_client())
        except Exception:
            return state
        delivered = {r['call_id']:r for r in call_records(state['id'], 'live')}
        if any(not measured(delivered[r['call_id']]) or
               delivered[r['call_id']].get('settlement', {}).get('error_class') in
               {'quota', 'auth', 'timeout', 'transient', 'cancelled'} for r in pending_delivery):
            # Delivery recovery settles a failure; it does not authorize new inference.
            return state
        for item in repo.all("events"):
            matching = [r for r in pending_delivery if r["context"]["event_id"] == item["id"]
                        and r["context"]["event_revision"] == item["revision"]]
            if item["state"] == "failed" and matching and all(r.get("schema_valid") for r in matching):
                item["state"] = "pending"
                repo.update_event(item)
        state.update(status="live", blocker=None)
        repo.set(state_key, state)
    allowance = budget_fn(state["id"], phase="live", now=now)
    candidates = engine.pending(repo, now)
    resumable = False
    if candidates and candidates[0].get("debate_id"):
        previous_calls = [r for r in call_records(state["id"], "live")
                          if r["context"]["debate_id"] == candidates[0]["debate_id"]]
        valid_stages = {r["context"]["stage"] for r in previous_calls
                        if r["status"] == "acknowledged" and r.get("schema_valid") and r.get("result")}
        resumable = bool(valid_stages) and allowance["remaining_calls"] >= 2-len(valid_stages)
    if candidates and (allowance["can_start"] or resumable):
        try:
            debate_fn(repo, candidates[0], experiment_id=state["id"], phase="live")
        except Exception as exc:
            current = next(e for e in repo.all('events') if e['id'] == candidates[0]['id'])
            latest = sorted([r for r in call_records(state["id"], "live")
                             if r['context']['debate_id'] == current.get('debate_id')],
                            key=lambda r:r["started_at"])
            rejected = latest and latest[-1]["status"] == "acknowledged" and measured(latest[-1]) and (
                latest[-1].get("validation_error") != "process_failed") and (
                latest[-1].get("settlement", {}).get("error_class") == "invalid_output")
            if rejected:
                state.setdefault("rejected_debates", []).append(latest[-1]["context"]["debate_id"])
            else:
                state.update(status="live_blocked", blocker=str(exc)[:160], blocked_at=now_iso(),
                             blocked_event_id=candidates[0]['id'])
    state["budget"] = budget_fn(state["id"], phase="live")
    state["heartbeat_at"] = now_iso()
    repo.set(state_key, state)
    return state


def finish(repo):
    state = repo.get("experiment", {})
    if not state.get("deadline") or datetime.now(timezone.utc) < parse_time(state["deadline"]):
        raise ValueError("six hours have not elapsed")
    try:
        research_accounting.flush(broker_gate.broker_client())
    except Exception as exc:
        state["settlement_error"] = type(exc).__name__
    records = call_records(state["id"], "live")
    issues = state.get("gaps") or state.get("blocker") or any(
        r["status"] != "acknowledged" or not measured(r) for r in records)
    state.update(status="complete_with_gaps" if issues else "complete", finished_at=now_iso(),
                 budget=budget(state["id"], phase="live"))
    repo.set("experiment", state)
    from scripts.research.report import write_report
    write_report(repo, state["id"])
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["preflight", "recover-preflight", "retry-invalid-preflight", "start", "run", "status", "report"])
    parser.add_argument("experiment_id")
    args = parser.parse_args()
    if not __import__("re").fullmatch(r"[a-zA-Z0-9_.-]{1,100}", args.experiment_id):
        parser.error("invalid experiment id")
    # The existing launcher hands off the caller environment through a private
    # socket. No new dotenv dependency or credential file is needed.
    repo = Repository()
    if args.action == "status":
        print(json.dumps(repo.get("experiment"), ensure_ascii=False, indent=2))
        return 0
    if args.action == "report":
        from scripts.research.report import write_report
        print(write_report(repo, args.experiment_id))
        return 0
    CACHE.mkdir(parents=True, exist_ok=True)
    with (CACHE / "experiment.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("research worker already running")
        if args.action == "recover-preflight":
            recover_preflight(repo, args.experiment_id)
        elif args.action == "retry-invalid-preflight":
            retry_invalid_preflight(repo, args.experiment_id)
        elif args.action == "preflight":
            preflight(repo, args.experiment_id)
        elif args.action == "start":
            print(json.dumps(start(repo, args.experiment_id)))
        else:
            if repo.get("experiment", {}).get("id") != args.experiment_id:
                raise SystemExit("experiment id mismatch")
            repo.set("worker", {"pid": os.getpid(), "started_at": now_iso()})
            while repo.get("experiment", {}).get("status") in {"live", "live_blocked"}:
                state = tick(repo)
                print(json.dumps({k: state.get(k) for k in ("id", "status", "heartbeat_at", "budget")}), flush=True)
                if state["status"].startswith("complete"):
                    break
                time.sleep(30)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
