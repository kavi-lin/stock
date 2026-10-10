"""Production entry points: bounded spend, explicit stops and durable restart."""
import copy
import json
import threading
from datetime import datetime, timedelta, timezone
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts._shared import broker_gate, llm_task_registry, model_router, research_accounting
from scripts.research import api, engine, experiment, intake, service
from scripts.research.store import Repository

NOW = datetime.now(timezone.utc)


@pytest.fixture(autouse=True)
def standalone_intake(monkeypatch):
    # Service mechanics on intake-built events; the break-news escalation
    # filter has its own tests in test_research_handoff.py.
    monkeypatch.setattr(engine, 'profile', lambda: {'intake': 'self'})


def record(i, at=NOW, phase='live', **changes):
    return {'call_id':str(i), 'started_at':at.isoformat(), 'status':'acknowledged',
            'schema_valid':True, 'result':{'ok':True},
            'context':{'experiment_id':'research-production', 'phase':phase,
                       'debate_id':str(i), 'stage':'analysis'},
            'settlement':{'usage_details':{'facts':[{'tokens':{'input_tokens':20000,'output_tokens':1000}}]}},
            **changes}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    repo = Repository(tmp_path/'research.sqlite3')
    trial = {'id':'old-trial','status':'complete','deadline':(NOW-timedelta(days=1)).isoformat()}
    repo.set('experiment',trial)
    repo.set('validation',{'passed':True})
    repo.set('last_poll',{'at':NOW.isoformat()})
    rows = []
    monkeypatch.setattr(research_accounting,'records',lambda:rows)
    monkeypatch.setattr(service,'profile',lambda:{'enabled':True,'service_enabled':True})
    monkeypatch.setattr(broker_gate,'broker_client',lambda *a:SimpleNamespace(
        request=lambda *a:{'providers':[{'info':{'id':'codex'},'cooldown_until':None}]}))
    service.initialize(repo)
    intake.ingest_items(repo,[{'headline':'TEST reports revenue growth and raises guidance',
        'raw_summary':'TEST revenue was 100 units, up from 90 units.', 'symbol':'TEST',
        'source':'Reuters','source_credibility':'HIGH','published':NOW.isoformat(),
        'url':'https://example.com/earnings'}], NOW)
    item=repo.all('events')[0]
    item.update(eligible=True,state='pending',evidence_health=[])
    repo.update_event(item)
    return repo, rows, item, trial


@pytest.mark.parametrize('role',['research-initial-analysis','research-initial-challenge',
                                  'research-recheck-analysis','research-recheck-challenge'])
def test_actual_acquire_sends_25k_and_native_profile(monkeypatch,role):
    llm_task_registry.clear_cache()
    sent=[];started=[]
    lease=SimpleNamespace(provider='codex',start=lambda **kw:started.append(kw))
    client=SimpleNamespace(acquire=lambda **kw:sent.append(kw) or lease)
    monkeypatch.setattr(broker_gate,'broker_client',lambda cfg=None:client)
    result=model_router._acquire(role,'codex',{},pinned=True,native_model='gpt-6-luna',
        prompts=('system','evidence'),context={'reasoning_effort':'max'},call_id='fixed-call')
    assert result[2] and sent[0]['estimated_input_tokens']==22000
    assert sent[0]['estimated_output_tokens']==3000
    assert sent[0]['model']=='gpt-6-luna' and sent[0]['context']['reasoning_effort']=='max'
    assert started==[{'model':'gpt-6-luna'}]


def test_production_tick_uses_own_clock_and_preserves_trial(setup):
    repo,rows,item,trial=setup
    stages=[]
    analysis={'claims':[{'id':'c1','text':'Revenue rose.','kind':'fact','direction':'mixed',
        'tickers':['TEST'],'horizon':'next quarter','evidence_refs':[{
            'evidence_id':item['evidence'][0]['id'],'quote':'TEST revenue was 100 units'}],
        'falsifier':'A corrected filing changes revenue.',
        'followup':{'due_at':None,'condition':'Next original filing'}}]}
    def invoke(role,system,user,**kw):
        stages.append(kw['context']['stage'])
        payload=analysis if role.endswith('analysis') else {'assessments':[{
            'claim_id':'c1','status':'supported','reason':'Revenue reported.',
            'evidence_refs':analysis['claims'][0]['evidence_refs']}]}
        kw['validate'](payload)
        row=record(kw['call_id'],context=kw['context'],result=payload)
        rows.append(row)
        return payload,row
    state=service.tick(repo,now=NOW,poll_fn=lambda repo:None,
                       debate_fn=partial(engine.debate,invoke=invoke))
    assert stages==['analysis','challenge'] and state['status']=='live'
    assert len(repo.all('cards'))==1 and repo.get('experiment')==trial
    assert api.query(repo=repo)['service']['mode']=='production'


@pytest.mark.parametrize('constraint',['hour','calls','debates'])
def test_real_tick_refuses_rolling_limits_across_run_ids(setup,constraint):
    repo,rows,item,trial=setup
    n={'hour':5,'calls':60,'debates':30}[constraint]
    at=NOW-timedelta(minutes=10 if constraint=='hour' else 120)
    rows.extend(record(i,at) for i in range(n))
    for r in rows:r['context']['experiment_id']='old-trial'
    if constraint=='calls':
        for r in rows:r['context']['debate_id']='single-debate'
    state=service.tick(repo,now=NOW,poll_fn=lambda repo:None,
                       debate_fn=lambda *a,**kw:pytest.fail('limit bypassed'))
    assert not state['budget']['can_start']
    service.initialize(repo)
    assert not service.budget('different-id',now=NOW)['can_start']
    assert service.budget(now=NOW+timedelta(hours=25))['can_start']


def test_preflight_does_not_use_live_allowance(setup):
    repo,rows,_,_=setup
    rows.extend(record(i,phase='preflight') for i in range(24))
    assert service.budget(now=NOW)['calls']==0


def test_production_stop_between_stages_never_starts_b(setup):
    repo,_,item,_=setup
    calls=[]
    def invoke(*a,**kw):
        calls.append(kw['call_id'])
        return {'claims':[]},{'call_id':kw['call_id']}
    engine.debate(repo,item,experiment_id='research-production',phase='live',
                  state_key='service',invoke=invoke,should_stop=lambda:bool(calls))
    assert len(calls)==1 and repo.all('events')[0]['state']=='deferred_stop'


@pytest.mark.parametrize('error',['quota','auth','transient'])
def test_settlement_ack_does_not_resume_failed_inference(setup,monkeypatch,error):
    repo,rows,item,_=setup
    state=repo.get('service');state.update(status='live_blocked',blocker=error)
    repo.set('service',state)
    row=record('bad',status='pending',schema_valid=False,
               settlement={'error_class':error,'usage_details':{'facts':[]}})
    rows.append(row)
    monkeypatch.setattr(broker_gate,'broker_client',lambda:object())
    monkeypatch.setattr(research_accounting,'flush',lambda client:row.update(status='acknowledged'))
    service.tick(repo,now=NOW,poll_fn=lambda repo:None,
                 debate_fn=lambda *a,**kw:pytest.fail('failure was auto-resumed'))
    assert row['status']=='acknowledged' and repo.get('service')['status']=='live_blocked'
    assert repo.get('service')['budget']['calls']==1
    service.tick(repo,now=NOW+timedelta(hours=25),poll_fn=lambda repo:None,
                 debate_fn=lambda *a,**kw:pytest.fail('quota stop expired locally'))
    assert repo.get('service')['budget']['calls']==0
    assert repo.get('service')['status']=='live_blocked'


def test_restart_requeues_valid_partial_and_keeps_quota_stop(setup,monkeypatch):
    repo,rows,item,_=setup
    item.update(state='researching',research_run_id='research-production',debate_id='partial')
    repo.update_event(item)
    row=record('partial');rows.append(row)
    monkeypatch.setattr(broker_gate,'broker_client',lambda:SimpleNamespace(request=lambda *a:{'status':'ok'}))
    monkeypatch.setattr(research_accounting,'flush',lambda client:None)
    service.recover(repo)
    assert repo.all('events')[0]['state']=='pending'
    state=repo.get('service');state.update(status='live_blocked',blocker='quota')
    repo.set('service',state)
    row['settlement']['usage_details']['facts']=[]
    service.recover(repo)
    assert repo.get('service')['blocker']=='quota'
    state.update(status='live',blocker=None,reviewed_call_ids=['partial'])
    repo.set('service',state)
    item['state']='researching';repo.update_event(item)
    row.update(schema_valid=False,result=None)
    service.recover(repo)
    assert repo.all('events')[0]['state']=='failed' and repo.get('service')['status']=='live'


def test_manual_resume_needs_eligible_preview_and_does_not_replay_failures(setup,monkeypatch):
    repo,rows,item,_=setup
    state=repo.get('service');state.update(status='live_blocked',blocker='quota')
    repo.set('service',state)
    item['state']='failed';repo.update_event(item)
    rows.append(record('unknown',schema_valid=False,settlement={'usage_details':{'facts':[]}}))
    eligible=False;previews=[]
    def preview(task,reserve):
        assert reserve is False and task['estimated_input_tokens']+task['estimated_output_tokens']==25000
        previews.append(task)
        return {'candidates':[{'provider':'codex','eligible':eligible}]}
    client=SimpleNamespace(request=lambda *a:{'status':'ok'},build_task=lambda **kw:kw,recommend=preview)
    monkeypatch.setattr(broker_gate,'broker_client',lambda:client)
    monkeypatch.setattr(research_accounting,'flush',lambda client:None)
    with pytest.raises(ValueError,match='no eligible'):service.resume(repo,'Quota reset verified')
    assert repo.get('service')['status']=='live_blocked'
    eligible=True
    service.resume(repo,'Quota reset verified')
    assert repo.get('service')['status']=='live' and repo.all('events')[0]['state']=='failed'
    assert not rows[0]['settlement']['usage_details']['facts']


def test_dashboard_start_hook_runs_background_service(monkeypatch):
    stop=threading.Event();called=[]
    monkeypatch.setattr(service,'enabled',lambda:True)
    monkeypatch.setattr(service,'run',lambda event:called.append(event))
    thread=service.start_background(stop);thread.join(timeout=1)
    assert called==[stop]
    source=Path('dashboard_server.py').read_text()
    main=source[source.index('if __name__ == "__main__":'):]
    assert 'research_thread = start_research_service(_shutdown)' in main


def test_worker_respects_existing_lock_without_mutating_state(setup,monkeypatch,tmp_path):
    repo,_,_,_=setup
    monkeypatch.setattr(service,'CACHE',tmp_path)
    before=repo.get('service')
    import fcntl
    with (tmp_path/'experiment.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        service.run(repo=repo)
    assert repo.get('service')==before


def test_broker_cooldown_wait_requires_changed_status_and_eligible_preview(setup,monkeypatch):
    repo,_,item,_=setup
    until=(NOW+timedelta(hours=2)).isoformat();eligible=False;previews=[]
    client=SimpleNamespace(request=lambda *a:{'providers':[{'info':{'id':'codex'},'cooldown_until':until}]},
        build_task=lambda **kw:kw,recommend=lambda task,reserve:previews.append(reserve) or {
            'candidates':[{'provider':'codex','eligible':eligible}]})
    monkeypatch.setattr(broker_gate,'broker_client',lambda:client)
    service.tick(repo,now=NOW,poll_fn=lambda repo:None,
                 debate_fn=lambda *a,**kw:pytest.fail('cooldown bypassed'))
    assert repo.get('service')['blocker']=='broker:refused(cooldown)' and not previews
    until=None
    service.tick(repo,now=NOW+timedelta(minutes=11),poll_fn=lambda repo:None,
                 debate_fn=lambda *a,**kw:pytest.fail('ineligible preview bypassed'))
    assert repo.get('service')['status']=='live_blocked' and previews==[False]
    eligible=True;calls=[]
    service.tick(repo,now=NOW+timedelta(minutes=22),poll_fn=lambda repo:None,
                 debate_fn=lambda *a,**kw:calls.append(kw))
    assert len(calls)==1 and repo.get('service')['status']=='live'
    assert previews==[False,False]
