"""Continuous research with durable stops and rolling, cross-restart budgets."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import threading
from datetime import datetime, timedelta, timezone

from scripts._shared import broker_gate, llm_task_registry, research_accounting
from scripts.research import engine, experiment, handoff, intake
from scripts.research.store import CACHE, Repository, now_iso, parse_time, profile

STATE_KEY = 'service'
CONTROL_KEY = 'service_control'


def limits():
    settings = profile()
    # Configuration may tighten the approved launch limits, never raise them.
    return {'hourly_debates': max(1, min(5, int(settings.get('hourly_debates', 5)))),
            'daily_debates': max(1, min(30, int(settings.get('daily_debates', 30)))),
            'daily_calls': max(2, min(60, int(settings.get('daily_calls', 60))))}


def budget(experiment_id=None, *, phase='live', now=None):
    now = now or datetime.now(timezone.utc)
    # All real research calls count, including the previous trial. A restart or
    # a different run ID must not reset the rolling allowance. Preflight is separate.
    rows = [r for r in research_accounting.records() if r['context']['phase'] == 'live'
            and now-timedelta(hours=24) < parse_time(r['started_at']) <= now]
    cap = limits()
    debates = {r['context']['debate_id'] for r in rows}
    recent = {r['context']['debate_id'] for r in rows
              if parse_time(r['started_at']) > now-timedelta(hours=1)}
    return {'calls':len(rows), 'debates':len(debates), 'hourly_debates':len(recent),
            'remaining_calls':max(0, cap['daily_calls']-len(rows)), 'window_hours':24,
            'limits':cap, 'can_start':len(rows)+2 <= cap['daily_calls']
            and len(debates) < cap['daily_debates'] and len(recent) < cap['hourly_debates']}


def enabled():
    settings = profile()
    return bool(settings.get('enabled') and settings.get('service_enabled'))


def initialize(repo):
    state = repo.get(STATE_KEY)
    if state:
        return state  # includes blocked/stopped; process restart is not approval to resume
    trial = repo.get('experiment', {})
    if not trial.get('status', '').startswith('complete') or not repo.get('validation', {}).get('passed'):
        raise ValueError('completed observation and deterministic validation required')
    state = {'id':profile().get('service_id', 'research-production'), 'status':'live',
             'mode':'production', 'started_at':now_iso(), 'heartbeat_at':now_iso(),
             'model':'gpt-6-luna', 'reasoning_effort':'max', 'gaps':[],
             'estimated_tokens_per_call':sum(llm_task_registry.token_estimate('research-initial-analysis')),
             'budget':budget(), 'blocker':None}
    repo.set(STATE_KEY, state)
    return state


def recover(repo):
    """Recover delivery/publication, never repeat an interrupted model process."""
    state = repo.get(STATE_KEY)
    if state['status'] == 'stopped':
        return
    try:
        client = broker_gate.broker_client()
        if client is None or client.request('GET', '/v1/ready').get('status') != 'ok':
            raise ValueError('broker_not_ready')
        research_accounting.flush(client)
        rows = experiment.call_records(state['id'], 'live')
        reviewed = set(state.get('reviewed_call_ids', []))
        if any(r['call_id'] not in reviewed and (r['status'] != 'acknowledged'
               or not experiment.measured(r)) for r in rows):
            raise ValueError('unresolved_usage')
        for event in repo.all('events'):
            if event.get('research_run_id') != state['id'] or event['state'] not in {'researching','deferred_stop'}:
                continue
            calls = [r for r in rows if r['context']['debate_id'] == event.get('debate_id')]
            invalid = [r for r in calls if not r.get('schema_valid') or not r.get('result')]
            if invalid and all(r['call_id'] in reviewed for r in invalid):
                event.update(state='failed', error='reviewed_interruption')
                repo.update_event(event)
                continue
            if invalid:
                raise ValueError('interrupted_result')
            event['state'] = 'pending'
            repo.update_event(event)
    except Exception as exc:
        if state['status'] != 'live_blocked':
            state.update(status='live_blocked', blocker='startup_recovery:'+type(exc).__name__,
                         blocked_at=now_iso())
        repo.set(STATE_KEY, state)


def intake_poll(repo):
    """`intake: break_news` (default) researches only escalated debates;
    `intake: self` restores the standalone multi-source intake."""
    if profile().get('intake', 'break_news') == 'self':
        return intake.poll(repo)
    return handoff.poll(repo)


def tick(repo, *, now=None, poll_fn=intake_poll, debate_fn=engine.debate, should_stop=lambda:False):
    now = now or datetime.now(timezone.utc)
    refresh_capacity(repo, now)
    def call(repository, event, **kwargs):
        return debate_fn(repository, event, **kwargs, state_key=STATE_KEY, should_stop=should_stop)
    return experiment.tick(repo, now=now, poll_fn=poll_fn, debate_fn=call,
                           state_key=STATE_KEY, budget_fn=budget)


def capacity_preview(client):
    inp, out = llm_task_registry.token_estimate('research-initial-analysis')
    task = client.build_task(task_id=broker_gate.new_task_id('research-capacity'),
        task_type='research-initial-analysis', estimated_input_tokens=inp,
        estimated_output_tokens=out, requires_web=False, model='gpt-6-luna',
        preferred_providers=['codex'], forbidden_providers=['claude','agy'])
    preview = client.recommend(task, reserve=False)
    return any(c.get('provider') == 'codex' and c.get('eligible') for c in preview.get('candidates', []))


def refresh_capacity(repo, now):
    """Wait out a broker refusal; actual inference quota/auth errors stay stopped."""
    state = repo.get(STATE_KEY)
    refusal = 'broker:refused(cooldown)'
    if state['status'] != 'live' and state.get('blocker') != refusal:
        return
    checked = parse_time(state.get('broker_checked_at'))
    until = parse_time(state.get('wait_until'))
    if checked and (now-checked).total_seconds() < 600:
        return
    # Status reads do not launch a model or take a reservation.
    try:
        client = broker_gate.broker_client()
        snapshot = client.request('GET', '/v1/status')
        codex = next(p for p in snapshot['providers'] if p['info']['id'] == 'codex')
    except Exception:
        return  # the real acquire remains fail-closed if Broker is unavailable
    state['broker_checked_at'] = now.isoformat()
    until = parse_time(codex.get('cooldown_until'))
    if until and until > now:
        if state['status'] == 'live':
            state['blocked_at'] = now.isoformat()
        state.update(status='live_blocked', blocker=refusal, wait_until=until.isoformat())
    elif state.get('blocker') == refusal:
        try:
            eligible = capacity_preview(client)
        except Exception:
            eligible = False
        if eligible:
            item = next((e for e in repo.all('events') if e['id'] == state.get('blocked_event_id')), None)
            if item:
                rows = [r for r in experiment.call_records(state['id'], 'live')
                        if r['context']['debate_id'] == item.get('debate_id')]
                if any(r['status'] != 'acknowledged' or not r.get('schema_valid')
                       or not experiment.measured(r) or not r.get('result') for r in rows):
                    repo.set(STATE_KEY,state)
                    return
                item['state'] = 'pending'
                repo.update_event(item)
            state.setdefault('provider_waits', []).append({'from':state.get('blocked_at'),
                'to':now.isoformat(), 'reason':'broker_cooldown',
                'resume_evidence':'cooldown cleared and no-reservation Codex preview eligible'})
            state.update(status='live', blocker=None, wait_until=None)
    repo.set(STATE_KEY,state)


def request_stop(repo):
    repo.set(CONTROL_KEY, {'stop_requested':True, 'at':now_iso()})


def resume(repo, reason):
    """Explicit operator action; an eligible no-reservation preview is required."""
    if not reason or not reason.strip():
        raise ValueError('resume requires a reason describing the resolved blocker')
    state = repo.get(STATE_KEY)
    if not state or state['status'] not in {'live_blocked','stopped'}:
        raise ValueError('no stopped service to resume')
    client = broker_gate.broker_client()
    if client is None or client.request('GET', '/v1/ready').get('status') != 'ok':
        raise ValueError('broker_not_ready')
    research_accounting.flush(client)
    rows = experiment.call_records(state['id'], 'live')
    if any(r['status'] != 'acknowledged' for r in rows):
        raise ValueError('unacknowledged calls remain')
    if not capacity_preview(client):
        raise ValueError('broker has no eligible codex capacity')
    state.setdefault('resumes', []).append({'at':now_iso(), 'reason':reason.strip()[:200],
                                           'previous_blocker':state.get('blocker')})
    # Reviewed failures remain unknown and failed, never replayed or zero-filled.
    state['reviewed_call_ids'] = [r['call_id'] for r in rows if not experiment.measured(r)]
    state.update(status='live', blocker=None)
    repo.set(STATE_KEY, state)
    repo.set(CONTROL_KEY, {'stop_requested':False, 'at':now_iso()})
    return state


def run(stop_event=None, *, repo=None):
    stop_event = stop_event or threading.Event()
    repo = repo or Repository()
    if not enabled():
        return
    CACHE.mkdir(parents=True, exist_ok=True)
    with (CACHE/'experiment.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return  # another research owner; do not overwrite its state
        initialize(repo)
        recover(repo)
        state = repo.get(STATE_KEY)
        state.update(worker_pid=os.getpid(), worker_started_at=now_iso())
        repo.set(STATE_KEY, state)
        def stopping():
            return stop_event.is_set() or not enabled() or repo.get(CONTROL_KEY, {}).get('stop_requested', False)
        try:
            while not stopping() and repo.get(STATE_KEY)['status'] in {'live','live_blocked'}:
                try:
                    state = tick(repo, should_stop=stopping)
                except Exception as exc:
                    state = repo.get(STATE_KEY)
                    state.update(status='live_blocked', blocker='service:'+type(exc).__name__,
                                 blocked_at=now_iso(), heartbeat_at=now_iso())
                    repo.set(STATE_KEY, state)
                print(json.dumps({'research_service':state['status'], 'at':state['heartbeat_at'],
                                  'budget':state.get('budget'), 'blocker':state.get('blocker')}), flush=True)
                stop_event.wait(30)
        finally:
            state = repo.get(STATE_KEY)
            # A host shutdown must not erase a quota/auth/accounting blocker.
            if state['status'] == 'live' and repo.get(CONTROL_KEY, {}).get('stop_requested'):
                state['status'] = 'stopped'
            state.update(worker_pid=None, worker_stopped_at=now_iso())
            repo.set(STATE_KEY, state)


def start_background(stop_event):
    if not enabled():
        return None
    thread = threading.Thread(target=run, args=(stop_event,), daemon=True, name='research_service')
    thread.start()
    return thread


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['run','status','stop','resume'])
    parser.add_argument('--reason')
    args = parser.parse_args()
    repo = Repository()
    if args.action == 'status':
        print(json.dumps({'service':repo.get(STATE_KEY), 'budget':budget(),
                          'control':repo.get(CONTROL_KEY)}, ensure_ascii=False, indent=2))
    elif args.action == 'stop':
        request_stop(repo)
    elif args.action == 'resume':
        print(json.dumps(resume(repo, args.reason), ensure_ascii=False))
    else:
        stop = threading.Event()
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, lambda *_:stop.set())
        run(stop, repo=repo)


if __name__ == '__main__':
    main()
