"""Research entry points: provenance, triggers, delivery, budgets and accounting."""
from __future__ import annotations

import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._shared import research_accounting as accounting
from scripts.research import api, engine, experiment, intake, report, schema, triggers
from scripts.research.store import Repository, digest

NOW = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def standalone_intake(monkeypatch):
    # These exercise the engine on intake-built events; the break-news
    # escalation filter has its own tests in test_research_handoff.py.
    monkeypatch.setattr(engine, 'profile', lambda: {'intake': 'self'})


@pytest.fixture
def repo(tmp_path):
    return Repository(tmp_path / "research.sqlite3")


def raw(**changes):
    return {"headline": "TEST reports revenue growth and raises guidance",
            "url": "https://example.com/earnings", "source": "Reuters",
            "source_credibility": "HIGH", "published": NOW.isoformat(),
            "raw_summary": "TEST revenue was 100 units, up from 90 units.", "symbol": "TEST", **changes}


def event(repo):
    intake.ingest_items(repo, [raw()], NOW)
    item = repo.all("events")[0]
    item.update(eligible=True, state="pending", evidence_health=[])
    repo.update_event(item)
    return item


def analysis(item):
    return {"claims": [{"id": "c1", "text": "Revenue rose.", "kind": "fact", "direction": "mixed",
                        "tickers": ["TEST"], "horizon": "next quarter",
                        "evidence_refs": [{"evidence_id": item["evidence"][0]["id"],
                                           "quote": "TEST revenue was 100 units"}],
                        "falsifier": "A corrected filing changes reported revenue.",
                        "followup": {"due_at": (NOW+timedelta(days=1)).isoformat(),
                                     "condition": "Next original filing"}}]}


def challenge(item, status="contested"):
    return {"assessments": [{"claim_id": "c1", "status": status, "reason": "Margin evidence is missing.",
                             "evidence_refs": analysis(item)["claims"][0]["evidence_refs"]}]}


def test_syndication_does_not_rearm_and_source_update_does(repo):
    item = event(repo)
    item["state"] = "researched"
    item["debate_id"] = "prior-debate"
    item["evidence_health"] = [{"status":"fetched"}]
    repo.update_event(item)
    counts = intake.ingest_items(repo, [raw(url="https://other.example/same", provider="FMP")], NOW)
    assert counts["duplicates"] == 1
    assert len(repo.all("events")) == 1
    counts = intake.ingest_items(repo, [raw(raw_summary="Corrected revenue is 80 units.")], NOW)
    updated = repo.all("events")[0]
    assert counts["new_revisions"] == 1 and updated["revision"] != item["revision"]
    assert updated["prior_revision"] == item["revision"]
    assert "debate_id" not in updated and "evidence_health" not in updated


def test_enriched_evidence_survives_next_feed_poll(repo):
    item = event(repo)
    item["evidence"].append({**item["evidence"][0], "id": "page", "text": "Original filing"})
    item = repo.enrich_event(item)
    item["state"] = "researched"
    repo.update_event(item)
    intake.ingest_items(repo, [raw()], NOW)
    saved = repo.all("events")[0]
    assert saved["state"] == "researched" and saved["revision"] == item["revision"]
    assert len(saved["evidence"]) == 2


@pytest.mark.parametrize("published", [None, "broken", (NOW-timedelta(days=2)).isoformat()])
def test_unknown_or_stale_dates_cannot_promote(repo, published):
    intake.ingest_items(repo, [raw(published=published)], NOW)
    assert not repo.all("events")[0]["eligible"]


def test_quote_hallucination_is_rejected_before_publication(repo):
    item = event(repo)
    payload = analysis(item)
    schema.validate_analysis(payload, item["evidence"])
    payload["claims"][0]["evidence_refs"][0]["quote"] = "revenue was 9000"
    with pytest.raises(ValueError, match="not present"):
        schema.validate_analysis(payload, item["evidence"])


def test_challenge_must_cover_each_claim_exactly_once(repo):
    item = event(repo)
    with pytest.raises(ValueError, match="every claim"):
        schema.validate_challenge({"assessments": []}, analysis(item), item["evidence"])


def test_deadline_between_stages_does_not_start_second_call(repo):
    item = event(repo)
    calls = []
    def invoke(*args, **kwargs):
        calls.append(kwargs['call_id'])
        repo.set('experiment', {'deadline':(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()})
        return analysis(item), {'call_id':kwargs['call_id']}
    cards = engine.debate(repo,item,experiment_id='exp',phase='live',invoke=invoke)
    assert cards == [] and len(calls) == 1
    assert repo.all('events')[0]['state'] == 'deferred_deadline'
    assert repo.all('cards') == []


def test_real_debate_entry_preserves_disagreement_for_all_lanes(repo, monkeypatch):
    item = event(repo)
    calls = []
    def fake(role, system, user, **kwargs):
        value = analysis(item) if role.endswith("analysis") else challenge(item)
        kwargs["validate"](value)
        calls.append(kwargs)
        return value, {"call_id": kwargs["call_id"]}
    cards = engine.debate(repo, item, experiment_id="test", phase="live", invoke=fake)
    assert len(calls) == 2 and calls[0]["context"]["stage"] == "analysis"
    assert cards[0]["status"] == "contested" and cards[0]["direction"] == "mixed"
    for lane in ("invest", "earnings", "momentum", "nexus"):
        assert engine.cards_for(repo, lane=lane, ticker="TEST")[0]["id"] == cards[0]["id"]
    assert api.nexus_candidates(repo)[0]["eligible_for_node_promotion"] is False
    query = api.query(lane="invest", ticker="TEST", repo=repo)
    with pytest.raises(ValueError, match="changed"):
        api.observe({"lane": "invest", "ticker": "TEST", "revision": "wrong"}, repo)
    assert api.observe({"lane": "invest", "ticker": "TEST", "revision": query["revision"]}, repo)["ok"]
    assert api.track({"claim_id": cards[0]["id"], "revision": cards[0]["revision"]}, repo)["ok"]


def test_calendar_without_release_never_calls_llm(repo):
    row = {"id": "calendar1", "date": "2026-10-05", "time": "BMO", "category": "earnings",
           "title": "TEST earnings", "tickers": ["TEST"]}
    assert triggers.scan(repo, NOW, [row]) == 0
    assert repo.get("schedules")[0]["state"] == "awaiting_release"
    assert not engine.pending(repo, NOW)
    event(repo)
    assert triggers.scan(repo, NOW, [row]) == 1
    assert repo.all("events")[0]["trigger"] == "calendar"


def test_dst_and_unknown_calendar_time():
    assert triggers.scheduled_time({"date": "2026-07-01", "time": "08:30 ET"}).hour == 12
    assert triggers.scheduled_time({"date": "2026-12-01", "time": "08:30 ET"}).hour == 13
    assert triggers.scheduled_time({"date": "2026-12-01"}) is None


def test_followup_requires_new_published_evidence(repo):
    item = event(repo)
    cards = engine.materialize(item, analysis(item), challenge(item), "debate1", "test", "live")
    cards[0]["created_at"] = (NOW-timedelta(days=2)).isoformat()
    cards[0]["followup"]["due_at"] = (NOW-timedelta(days=1)).isoformat()
    repo.publish(item, cards)
    assert triggers.scan(repo, NOW, []) == 0
    intake.ingest_items(repo, [raw(url="https://example.com/correction", headline="TEST corrects earnings", raw_summary="Revenue is 80 units.")], NOW)
    latest = next(e for e in repo.all("events") if e["id"] != item["id"])
    latest.update(eligible=True, state="pending")
    repo.update_event(latest)
    assert triggers.scan(repo, NOW, []) == 1
    assert next(e for e in repo.all("events") if e["id"] == latest["id"])["trigger"] == "followup"


def record(call_id="call1", **changes):
    result = SimpleNamespace(raw_stdout=json.dumps({"type":"turn.completed", "usage":{
        "input_tokens":100,"output_tokens":20,"cached_input_tokens":80,"reasoning_output_tokens":10}}),
        error=None, exit_code=0)
    body, _ = accounting.settlement(result, "gpt-6-luna")
    body["settlement_id"] = call_id
    return {"call_id":call_id, "reservation_id":"res1", "status":"pending", "schema_valid":True,
            "started_at":NOW.isoformat(), "settlement":body,
            "context":{"experiment_id":"test","phase":"live","debate_id":call_id,"stage":"analysis","trigger":"news"}, **changes}


def test_ack_loss_replays_same_payload_without_inference(tmp_path):
    row = record()
    accounting.atomic_json(tmp_path / "call1.json", row)
    bodies = []
    def request(method, path, body):
        bodies.append(copy.deepcopy(body))
        if len(bodies) == 1:
            raise accounting.BrokerError("lost ack")
        return {"reservation":{"reservation_id":"res1"}, "execution":{
            "execution_id":"exec1","usage":body["usage"],"usage_details":body["usage_details"]}}
    client = SimpleNamespace(request=request)
    with pytest.raises(accounting.BrokerError):
        accounting.flush(client, tmp_path)
    accounting.flush(client, tmp_path)
    assert bodies[0] == bodies[1]
    assert accounting.records(tmp_path)[0]["status"] == "acknowledged"


def test_wrong_token_positive_control_and_subset_accounting():
    row = record()
    body = row["settlement"]
    item = {"task":{"task_id":"call1", "context":row["context"]},
            "reservation":{"reservation_id":"res1"}, "execution":{
                "execution_id":"exec1","usage":body["usage"].copy(),"usage_details":body["usage_details"]}}
    assert not report.reconcile_history([row], [item])
    extra = copy.deepcopy(item)
    extra['reservation']['reservation_id'] = 'res2'
    extra['execution']['execution_id'] = 'exec2'
    assert any(e['error'] == 'multiple_broker_executions'
               for e in report.reconcile_history([row], [extra,item]))
    item["execution"]["usage"]["input_tokens"] += 1
    assert report.reconcile_history([row], [item])
    assert report.tokens(row)["comparable_tokens"] == 120
    assert report.tokens(row)["comparable_tokens"] != 210


def test_missing_usage_excluded_from_denominator_not_zero():
    known = record(status="acknowledged")
    missing = record("call2", settlement={"usage_details":{"status":"missing","facts":[]}}, schema_valid=False)
    result = report.summarize([known, missing], [])
    assert result["call_metrics"]["comparable_tokens"]["mean"] == 120
    assert result["call_metrics"]["comparable_tokens"]["missing"] == 1
    assert result["failed_calls"] == 1


def test_empty_ticker_schema_still_rejects_invented_symbol(repo):
    item = event(repo)
    native = schema.output_schema(item['evidence'], tickers=[])
    assert native['properties']['claims']['items']['properties']['tickers']['maxItems'] > 0
    with pytest.raises(ValueError, match='ticker was not identified'):
        schema.validate_analysis(analysis(item), item['evidence'], [])


def test_failed_call_without_usage_blocks_instead_of_schema_skip(repo, monkeypatch):
    event(repo)
    repo.set('experiment', {'id':'exp','status':'live','heartbeat_at':NOW.isoformat(),
                           'deadline':(NOW+timedelta(hours=1)).isoformat(), 'gaps':[]})
    repo.set('last_poll', {'at':NOW.isoformat()})
    failed = record('failed', schema_valid=False, validation_error='process_failed',
                    settlement={'error_class':'invalid_output','usage_details':{'status':'missing','facts':[]}})
    monkeypatch.setattr(experiment,'call_records',lambda *args:[failed])
    monkeypatch.setattr(experiment.triggers,'scan',lambda *args:None)
    def fail(*args, **kwargs):
        raise RuntimeError('missing usage')
    state = experiment.tick(repo, now=NOW, debate_fn=fail)
    assert state['status'] == 'live_blocked' and 'rejected_debates' not in state


def test_source_report_excludes_development_poll():
    old = {'at':(NOW-timedelta(minutes=1)).isoformat(),'sources':{'Test':{'status':'error'}}}
    live = {'at':NOW.isoformat(),'sources':{'Test':{'status':'ok','fetched':2}}}
    result = report.source_summary([old,live],NOW.isoformat(),(NOW+timedelta(hours=6)).isoformat())
    assert result['polls'] == 1 and result['sources']['Test']['statuses'] == {'ok':1}


def test_provider_busy_waits_for_broker_change_then_resumes_same_event(repo, monkeypatch):
    item=event(repo)
    repo.set('experiment', {'id':'test','status':'live','heartbeat_at':NOW.isoformat(),
                           'deadline':(NOW+timedelta(hours=1)).isoformat(),'gaps':[]})
    repo.set('last_poll',{'at':NOW.isoformat()})
    old=record('earlier-invalid',status='acknowledged',schema_valid=False)
    old['settlement']['error_class']='invalid_output'
    monkeypatch.setattr(experiment,'call_records',lambda *args:[old])
    monkeypatch.setattr(experiment.triggers,'scan',lambda *args:None)
    def refuse(*args,**kwargs):
        raise RuntimeError('broker:refused(provider_busy)')
    state=experiment.tick(repo,now=NOW,debate_fn=refuse)
    assert state['status']=='live_blocked' and state['blocked_event_id']==item['id']
    assert not state.get('rejected_debates')  # a prior event's failure must not hide this refusal
    active=[{'provider':'codex'}]
    monkeypatch.setattr(experiment.broker_gate,'broker_client',lambda:SimpleNamespace(
        request=lambda method,path:{'active_reservations':active}))
    calls=[]
    assert experiment.tick(repo,now=NOW,debate_fn=lambda *a,**k:calls.append(k))['status']=='live_blocked'
    assert not calls
    active.clear()
    state=experiment.tick(repo,now=NOW,debate_fn=lambda *a,**k:calls.append(k))
    assert state['status']=='live' and len(calls)==1
    assert state['provider_waits'][0]['event_id']==item['id']


@pytest.mark.parametrize('blocker',['broker:refused(quota)','research call failed: auth'])
def test_quota_and_auth_do_not_use_provider_busy_resume(repo,monkeypatch,blocker):
    item=event(repo)
    repo.set('experiment',{'id':'test','status':'live_blocked','blocker':blocker,
        'blocked_event_id':item['id'],'heartbeat_at':NOW.isoformat(),
        'deadline':(NOW+timedelta(hours=1)).isoformat(),'gaps':[]})
    repo.set('last_poll',{'at':NOW.isoformat()})
    monkeypatch.setattr(experiment,'call_records',lambda *args:[])
    monkeypatch.setattr(experiment.triggers,'scan',lambda *args:None)
    monkeypatch.setattr(experiment.broker_gate,'broker_client',lambda:pytest.fail('unexpected retry'))
    state=experiment.tick(repo,now=NOW,debate_fn=lambda *a,**k:pytest.fail('unexpected inference'))
    assert state['status']=='live_blocked'


def test_budget_counts_failed_calls_and_hourly_limit(monkeypatch):
    rows = [record(str(i), schema_valid=False) for i in range(5)]
    monkeypatch.setattr(experiment, "call_records", lambda *args: rows)
    assert not experiment.budget("test", phase="live", now=NOW)["can_start"]
    assert experiment.budget("test", phase="preflight", now=NOW)["can_start"]
    rows[:] = [record(str(i)) for i in range(22)]
    assert experiment.budget("test", phase="preflight", now=NOW)["can_start"]
    rows[:] = [record(str(i), started_at=(NOW-timedelta(hours=2)).isoformat()) for i in range(60)]
    assert not experiment.budget("test", phase="live", now=NOW)["can_start"]


def test_observation_cannot_start_before_tests_and_preflight(repo):
    with pytest.raises(ValueError, match="twelve"):
        experiment.start(repo, "test")
    with pytest.raises(ValueError, match="deterministic"):
        experiment.preflight(repo, "test")


def test_start_requires_reconciled_history_not_just_preflight_label(repo, monkeypatch):
    repo.set("experiment", {"id":"test","status":"preflight_passed",
                            "cases":{str(i):{"status":"passed"} for i in range(12)}})
    repo.set("validation", {"passed":True})
    monkeypatch.setattr(experiment.broker_gate,"broker_client",lambda:SimpleNamespace(
        request=lambda *a:{"status":"ok"}))
    monkeypatch.setattr(accounting,"flush",lambda client:None)
    monkeypatch.setattr(experiment,"call_records",lambda *args:[record(str(i),status="acknowledged",
                        requested_model="gpt-6-luna",reasoning_effort="max") for i in range(12)])
    monkeypatch.setattr(report,"broker_history",lambda _:[])
    with pytest.raises(ValueError,match="reconciliation"):
        experiment.start(repo,"test")
    assert repo.get("experiment")["status"] == "preflight_passed"


def test_followup_calls_are_classified_as_rechecks(repo):
    item=event(repo);item['trigger']='followup';repo.update_event(item)
    roles=[]
    def fake(role, system, user, **kwargs):
        roles.append(role)
        value=analysis(item) if role.endswith('analysis') else challenge(item)
        kwargs['validate'](value)
        return value,{'call_id':kwargs['call_id']}
    engine.debate(repo,item,experiment_id='test',phase='live',invoke=fake)
    assert roles==['research-recheck-analysis','research-recheck-challenge']


def test_lost_ack_resumes_publication_even_at_call_limit(repo, monkeypatch):
    now=datetime.now(timezone.utc)
    item=event(repo);item.update(state='failed',debate_id='last-debate',published_at=now.isoformat())
    repo.update_event(item)
    fresh=copy.deepcopy(item)
    fresh.update(id='fresh-event',state='pending',source_priority=999)
    fresh.pop('debate_id')
    repo.update_event(fresh)
    repo.set('experiment',{'id':'test','status':'live_blocked','started_at':now.isoformat(),
                          'heartbeat_at':now.isoformat(),'deadline':(now+timedelta(hours=1)).isoformat(),'gaps':[]})
    repo.set('last_poll',{'at':now.isoformat()})
    rows=[record(str(i),status='acknowledged') for i in range(58)]
    for stage in ['analysis','challenge']:
        r=record(stage,status='pending' if stage=='challenge' else 'acknowledged',result={'ok':True})
        r['context'].update(event_id=item['id'],event_revision=item['revision'],debate_id='last-debate',stage=stage)
        rows.append(r)
    monkeypatch.setattr(experiment,'call_records',lambda *args:rows)
    monkeypatch.setattr(experiment.broker_gate,'broker_client',lambda:object())
    def flush(client):
        for row in rows:row['status']='acknowledged'
    monkeypatch.setattr(accounting,'flush',flush)
    called=[]
    state=experiment.tick(repo,now=now,poll_fn=lambda repo:None,
                          debate_fn=lambda repo,event,**kw:called.append(event['debate_id']))
    assert state['status']=='live' and called==['last-debate']
    assert state['budget']['calls']==60


def test_rss_error_is_not_empty_success(monkeypatch):
    from news import fetch_news_rss as rss
    def fail(*args, **kwargs):
        raise rss.requests.HTTPError("rate limit")
    monkeypatch.setattr(rss.requests, "get", fail)
    health = {}
    assert rss.fetch_feed("test", "https://example.com", "HIGH", health=health) == []
    assert health["status"] == "error"
