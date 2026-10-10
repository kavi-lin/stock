"""Break-news → research handoff: deterministic escalation, no own intake."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts.break_news import debater
from scripts.research import engine, handoff, service
from scripts.research.store import Repository

NOW = datetime.now(timezone.utc)


def bn_item(news_id, *, close_reason='converged_round1', disputes=0, binary=False,
            echo=1, tickers=('NVDA',), headline='Nvidia raises guidance as data center revenue surges',
            published=NOW - timedelta(minutes=30), closed=NOW - timedelta(minutes=5),
            url=None, hi=False, verdict='NEUTRAL', confidence=0.6):
    return {'news_id': news_id, 'state': 'closed', '_hi': hi,
            'headline': headline, 'raw_summary': 'Quarterly results beat estimates.',
            'source': {'name': 'Reuters Business', 'credibility': 'HIGH', 'kind': 'publisher',
                       'url': url or f'https://example.com/{news_id}',
                       'published': published.isoformat()},
            'triage': {'binary_flag': binary},
            'cluster': {'echo_count': echo},
            'summary': {'close_reason': close_reason, 'stated_dispute_count': disputes,
                        'consensus_verdict': verdict, 'closed_at': closed.isoformat(),
                        'merged_entities': {'tickers': list(tickers)},
                        'final_takes_by_round': [{'confidence': confidence}]}}


@pytest.fixture
def env(tmp_path, monkeypatch):
    logs = tmp_path / 'logs'
    logs.mkdir()
    monkeypatch.setattr(handoff, 'BREAK_NEWS_DIR', logs)
    monkeypatch.setattr(handoff, 'profile', lambda: {'handoff_min_score': 3})
    monkeypatch.setattr(engine, 'profile', lambda: {})   # default intake: break_news
    monkeypatch.setattr(debater, '_load_universe_tickers', lambda: {'NVDA', 'AMD'})
    monkeypatch.setattr(debater, 'is_high_priority_item', lambda item: item.get('_hi', False))

    def write(item):
        (logs / f"{item['news_id']}.json").write_text(json.dumps(item))
    return Repository(tmp_path / 'research.sqlite3'), write


def test_scoring_needs_more_than_a_routine_dispute(env):
    assert handoff.escalation(bn_item('bn_a', disputes=1))[0] == 1
    score, reasons, _ = handoff.escalation(bn_item('bn_b', close_reason='arbitrated', disputes=1))
    assert score == 4 and reasons == ['debate_unsettled', 'stated_dispute']
    assert handoff.escalation(bn_item('bn_c', binary=True))[0] == 3
    assert handoff.escalation(bn_item('bn_d', echo=4, hi=True))[0] == 3
    assert handoff.escalation(bn_item('bn_e', verdict='BULLISH', confidence=0.8, disputes=1))[0] == 2
    # Without a tracked ticker nothing escalates, however heated the debate.
    assert handoff.escalation(bn_item('bn_f', tickers=('XYZ',), binary=True)) == (0, ['no_universe_ticker'], [])


def test_poll_promotes_only_escalated_debates_once(env):
    repo, write = env
    write(bn_item('bn_20261005_aaaaaaaa', close_reason='arbitrated', disputes=1))
    write(bn_item('bn_20261005_bbbbbbbb', disputes=1))
    counts = handoff.poll(repo, now=NOW)
    assert counts == {'evaluated': 2, 'escalated': 1, 'promoted': 1, 'rejected': 0}
    assert repo.get('source_health')['Break News']['fresh'] == 1
    events = repo.all('events')
    assert len(events) == 1
    event = events[0]
    assert event['break_news_ids'] == ['bn_20261005_aaaaaaaa']
    assert event['state'] == 'pending' and event['eligible']
    assert event['escalation']['score'] == 4
    assert engine.pending(repo, NOW) == [event]
    seen = repo.get(handoff.SEEN_KEY)
    assert seen['bn_20261005_bbbbbbbb'] == {**seen['bn_20261005_bbbbbbbb'], 'escalated': False, 'score': 1}
    # A second pass neither re-scores nor re-arms anything.
    assert handoff.poll(repo, now=NOW)['evaluated'] == 0


def test_echoed_debates_share_one_research_event(env):
    repo, write = env
    write(bn_item('bn_20261005_jjjjjjjj', binary=True, url='https://a.example.com/x'))
    write(bn_item('bn_20261005_kkkkkkkk', close_reason='arbitrated', disputes=1,
                  url='https://b.example.com/y'))
    handoff.poll(repo, now=NOW)
    events = repo.all('events')
    assert len(events) == 1
    assert sorted(events[0]['break_news_ids']) == ['bn_20261005_jjjjjjjj', 'bn_20261005_kkkkkkkk']
    assert events[0]['escalation']['score'] == 4
    for news_id in events[0]['break_news_ids']:
        assert handoff.status_for(news_id, repo)['event']['id'] == events[0]['id']


@pytest.mark.parametrize('changes,reason', [
    ({'published': NOW - timedelta(hours=7)}, 'missing_or_stale_publication_time'),
    ({'headline': "3 Numbers That Explain Why I'm Buying Nvidia"}, 'opinion_requires_new_primary_evidence'),
    ({'url': 'futu://news/123'}, 'no_public_url'),
])
def test_escalated_debate_still_has_to_pass_research_gate(env, changes, reason):
    repo, write = env
    write(bn_item('bn_20261005_cccccccc', binary=True, **changes))
    assert handoff.poll(repo, now=NOW)['rejected'] == 1
    assert repo.all('events') == []
    assert repo.get(handoff.SEEN_KEY)['bn_20261005_cccccccc']['rejected'] == reason


def test_open_or_old_debates_are_not_evaluated(env):
    repo, write = env
    write({**bn_item('bn_20261005_dddddddd', binary=True), 'state': 'debating'})
    write(bn_item('bn_20261005_eeeeeeee', binary=True, closed=NOW - timedelta(hours=7)))
    assert handoff.poll(repo, now=NOW)['evaluated'] == 0


def test_stronger_escalation_is_researched_first(env):
    repo, write = env
    write(bn_item('bn_20261005_ffffffff', binary=True))
    write(bn_item('bn_20261005_gggggggg', close_reason='arbitrated', disputes=1,
                  headline='AMD wins hyperscaler order, lifting chipmaker revenue outlook',
                  tickers=('AMD',)))
    handoff.poll(repo, now=NOW)
    order = [e['break_news_ids'][0] for e in engine.pending(repo, NOW)]
    assert order == ['bn_20261005_gggggggg', 'bn_20261005_ffffffff']


def test_status_for_reports_handoff_and_cards(env):
    repo, write = env
    write(bn_item('bn_20261005_hhhhhhhh', binary=True))
    write(bn_item('bn_20261005_iiiiiiii', headline='AMD trims costs in quarterly restructuring',
                  tickers=('AMD',)))
    handoff.poll(repo, now=NOW)
    low = handoff.status_for('bn_20261005_iiiiiiii', repo)
    assert low['event'] is None and low['handoff']['escalated'] is False
    event = repo.all('events')[0]
    card = {'id': 'rc_1', 'event_id': event['id'], 'superseded': False, 'text': 'x'}
    with repo.connect() as conn:
        conn.execute('INSERT INTO cards VALUES (?,?)', (card['id'], json.dumps(card)))
        stale = {**card, 'id': 'rc_0', 'superseded': True}
        conn.execute('INSERT INTO cards VALUES (?,?)', (stale['id'], json.dumps(stale)))
    high = handoff.status_for('bn_20261005_hhhhhhhh', repo)
    assert high['event']['state'] == 'pending'
    assert [c['id'] for c in high['cards']] == ['rc_1']


def test_old_intake_leftovers_do_not_start_research(env, monkeypatch):
    repo, write = env
    monkeypatch.setattr(engine, 'profile', lambda: {})
    write(bn_item('bn_20261005_llllllll', binary=True))
    handoff.poll(repo, now=NOW)
    escalated = repo.all('events')[0]
    leftover = {**escalated, 'id': 're_old', 'escalation': None, 'break_news_ids': []}
    reserved = {**leftover, 'id': 're_reserved', 'debate_id': 'rd_1'}
    for event in (leftover, reserved):
        repo.update_event(event)
    assert {e['id'] for e in engine.pending(repo, NOW)} == {escalated['id'], 're_reserved'}
    monkeypatch.setattr(engine, 'profile', lambda: {'intake': 'self'})
    assert len(engine.pending(repo, NOW)) == 3


def test_service_intake_follows_profile(monkeypatch):
    calls = []
    monkeypatch.setattr(service.handoff, 'poll', lambda repo: calls.append('handoff'))
    monkeypatch.setattr(service.intake, 'poll', lambda repo: calls.append('self'))
    monkeypatch.setattr(service, 'profile', lambda: {})
    service.intake_poll(None)
    monkeypatch.setattr(service, 'profile', lambda: {'intake': 'self'})
    service.intake_poll(None)
    assert calls == ['handoff', 'self']
