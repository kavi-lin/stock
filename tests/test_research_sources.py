"""Source adapters distinguish absence, failure, pagination and original evidence."""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from news import fetch_news_rss as rss
from news import fetch_sec_edgar as sec
from scripts.research import evidence, intake
from scripts.research.store import Repository


def test_conditional_rss_304_is_explicit(monkeypatch):
    seen = {}
    def get(url, **kwargs):
        seen.update(kwargs)
        return SimpleNamespace(status_code=304, headers={})
    monkeypatch.setattr(rss.requests, "get", get)
    health = {}
    assert rss.fetch_feed("test", "https://example.com/rss", "HIGH", health=health,
                          conditional={"etag":"v1"}) == []
    assert health["status"] == "not_modified"
    assert health['etag'] == 'v1'
    assert seen["headers"]["If-None-Match"] == "v1"


def test_html_error_page_is_not_successful_empty_feed(monkeypatch):
    monkeypatch.setattr(rss.requests,"get",lambda *a,**k:SimpleNamespace(
        status_code=200,headers={},content=b'<html><body>Access denied</body></html>',raise_for_status=lambda:None))
    health={}
    assert not rss.fetch_feed("test","https://example.com/rss","HIGH",health=health)
    assert health["error"] == "not_a_feed"


def test_company_name_resolution_without_holdings():
    event = intake.normalize({"headline":"NVIDIA announces quarterly results", "raw_summary":"Revenue increased.",
                              "url":"https://nvidianews.nvidia.com/test", "source":"NVIDIA IR",
                              "published":datetime.now(timezone.utc).isoformat()})
    assert event["tickers"] == ["NVDA"]
    assert event["trigger"] == "filing"
    summary_event = intake.normalize({'headline':'Tariff refunds are delayed',
        'raw_summary':'FedEx has released hundreds of millions in refunds.',
        'url':'https://example.com/refunds','source':'WSJ',
        'published':datetime.now(timezone.utc).isoformat()})
    assert summary_event['tickers'] == ['FDX']
    alias_event = intake.normalize({'headline':"Micron's latest earnings report",
        'raw_summary':'Google increases capital spending.',
        'url':'https://example.com/micron','source':'Nasdaq',
        'published':datetime.now(timezone.utc).isoformat()})
    assert alias_event['tickers'] == ['GOOGL','MU']


def test_research_relevance_keeps_transmission_channels_not_generic_politics(monkeypatch):
    assert not intake.research_gate('Justice considers retirement', 'Senate election may affect nominees', [], 'news')[0]
    assert not intake.research_gate("Delta, Pepsi, Levi's, and More to Watch This Week", '', ['LEVI'], 'news')[0]
    assert intake.research_gate('Attacks on shipping resumed', 'Oil route through Hormuz affected', [], 'news')[0]
    assert intake.research_gate('Court overturns tariffs', '', [], 'news')[0]
    assert not intake.research_gate("3 Numbers That Explain Why I'm Buying PepsiCo With My Next $5,000", '', ['PEP'], 'news')[0]
    assert intake.research_gate('PepsiCo raises full-year revenue guidance', '', ['PEP'], 'news')[0]
    assert intake.research_gate('AkzoNobel could sell unit for over $1 billion', '', [], 'news')[0]
    monkeypatch.setattr(intake, '_score_materiality', lambda *args:(5.0,'HIGH','straight_news'))
    unrelated = intake.normalize({'headline':'Former researcher to testify at New York City hearing',
        'raw_summary':'A hearing on artificial intelligence.', 'symbol':'CHCO',
        'url':'https://example.com/hearing','source':'Reuters',
        'published':datetime.now(timezone.utc).isoformat()})
    assert unrelated['provider_tickers'] == ['CHCO']
    assert not unrelated['eligible'] and unrelated['gate_reason'] == 'no_identified_financial_channel'


def test_edgar_paginates_and_maps_cik_without_inventing_symbol(tmp_path, monkeypatch):
    now=datetime.now(timezone.utc)
    pages=[]
    def get(url,params,**kwargs):
        offset=params.get('start',0);pages.append(offset)
        date=now if offset==0 else now-timedelta(hours=7)
        data=f'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>6-K - TESTCO (0000000001) (Filer)</title><updated>{date.isoformat()}</updated><link href="https://www.sec.gov/Archives/test-{offset}-index.html"/><summary>Quarterly results</summary></entry></feed>'''
        return SimpleNamespace(content=data.encode(),raise_for_status=lambda:None)
    monkeypatch.setattr(sec.requests,"get",get)
    monkeypatch.setattr(sec.time,"sleep",lambda _:None)
    monkeypatch.setattr(sec,"company_tickers",lambda headers:{"0000000001":"TEST"})
    monkeypatch.setattr(sys,"argv",['fetch_sec_edgar.py','--form','6-K','--count','1','--hours','6','--output',str(tmp_path)])
    sec.main()
    output=json.loads(next(tmp_path.glob('*_edgar_raw.json')).read_text())
    assert pages == [0,1] and output['pages_fetched']==2
    assert output['items'][0]['symbol']=='TEST'
    assert output['items'][0]['headline'].startswith('[6-K]')


def test_page_evidence_has_separate_provenance():
    event={'headline':'Test release','tickers':['TEST'],'url':'https://example.com/release',
           'source':'Test IR','source_kind':'company_ir','published_at':datetime.now(timezone.utc).isoformat(),
           'evidence':[{'id':'feed','text':'A feed summary'}]}
    result=evidence.enrich(event,fetch=lambda url,terms:{'status':'fetched','url':url,'excerpts':['Original page passage.']})
    assert result['evidence'][1]['content_type']=='original_page_excerpt'
    assert result['evidence'][0]['text']=='A feed summary'


def test_optional_local_source_timeout_does_not_drop_primary_poll(tmp_path, monkeypatch):
    from scripts.break_news import poller as legacy
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs['timeout']))
        raise subprocess.TimeoutExpired(command, kwargs['timeout'])
    monkeypatch.setattr(intake.subprocess, 'run', run)
    monkeypatch.setattr(intake, 'FEEDS', [('NVIDIA IR','https://example.com/rss','HIGH')])
    monkeypatch.setattr(intake, 'profile', lambda: {})
    monkeypatch.setattr(legacy, 'SOCIAL_ENABLED', False)
    monkeypatch.setattr(legacy, 'FUTU_ENABLED', True)
    monkeypatch.setattr(legacy, 'FUTU_AVAILABLE', True)
    def feed(name, url, credibility, **kwargs):
        kwargs['health'].update(status='ok')
        return [{'headline':'NVIDIA announces quarterly revenue growth of 20%',
                 'raw_summary':'Quarterly earnings release.', 'url':'https://example.com/news',
                 'source':name, 'published':datetime.now(timezone.utc).isoformat()}]
    monkeypatch.setattr(intake, 'fetch_feed', feed)
    monkeypatch.setattr(intake, '_provider', lambda name, script: ([], {'feed':name,'status':'ok'}))
    repo = Repository(tmp_path/'research.sqlite3')
    result = intake.poll(repo)
    assert result['received'] == 1 and len(repo.all('events')) == 1
    assert repo.get('source_health')['Futu Push']['error'] == 'TimeoutExpired'
    assert calls[0][1] == 15
    assert calls[0][0][-2:] == ['scripts.research.discovery', 'futu']
