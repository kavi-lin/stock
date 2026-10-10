"""Real HTTP route and historical projection; no background workers or network data."""
import copy
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'skills/earnings-analyst/tests'))
from test_earnings_history import bundle, expectation
from scripts.earnings_detail import load_earnings_detail, history
with patch('threading.Thread.start'):
    import dashboard_server as server


class EarningsDetailTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / 'tmp')
        self.root = Path(self.tmp.name)
        self.cache = self.root / 'skills/earnings-analyst/cache'
        self.cache.mkdir(parents=True)
        self.put(bundle(1), narrative=True)
        self.put(bundle(2), narrative=True)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, data, narrative=False):
        path = self.cache / f"TEST_{data['last_earnings_date']}.json"
        path.write_text(json.dumps(data))
        if narrative:
            history.narrative_path(path).write_text(json.dumps({'ticker':'TEST', 'last_earnings_date':data['last_earnings_date'],
                'as_of_date':data['as_of_date'], 'headline_oneliner':'Saved narrative', 'expectations':[]}))
        return path

    def load(self, **kw):
        return load_earnings_detail('TEST', root=self.root, **kw)

    def save(self, data, at):
        narrative={'ticker':'TEST', 'last_earnings_date':data['last_earnings_date'],
                   'as_of_date':data['as_of_date'], 'expectations':[expectation()]}
        comparison=history.build_comparison(data,self.cache,narrative)
        report=self.root/'reports'/'test.md'; report.parent.mkdir(exist_ok=True); report.write_text('Saved report')
        with patch.object(history,'ROOT',self.root),patch.object(history,'utcnow',return_value=at):
            return history.save_snapshot(data,narrative,comparison,self.cache,report)

    def test_latest_period_and_comparison(self):
        d=self.load()
        self.assertEqual(d['view']['selected_period'],'2026-06-30')
        self.assertEqual(len(d['view']['periods']),2)
        self.assertEqual(d['comparison']['previous_analysis']['period_end'],'2026-03-31')
        self.assertEqual(d['comparison']['financial_changes'][0]['qoq']['delta'],10)
        self.assertEqual(d['comparison']['context']['earnings_release_date'],'2026-07-15')

    def test_missing_latest_narrative_does_not_show_old_quarter(self):
        history.narrative_path(self.cache/'TEST_2026-06-30.json').unlink()
        d=self.load()
        self.assertFalse(d['view']['narrative_available'])
        self.assertEqual(d['view']['selected_period'],'2026-06-30')
        self.assertEqual(d['infographic'],{})
        self.assertEqual(len(d['comparison']['financial_changes']),5)

    def test_mismatched_narrative_not_displayed(self):
        p=history.narrative_path(self.cache/'TEST_2026-06-30.json'); d=json.loads(p.read_text()); d['last_earnings_date']='2026-03-31'; p.write_text(json.dumps(d))
        self.assertFalse(self.load()['view']['narrative_available'])

    def test_historical_quarter_and_first_analysis(self):
        d=self.load(period='2026-03-31')
        self.assertEqual(d['comparison']['context']['fiscal_period']['period'],'Q1')
        self.assertEqual(d['comparison']['previous_analysis']['status'],'no_previous_analysis')

    def test_read_has_no_side_effects(self):
        def state(): return {str(p):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        before=state(); self.load(); self.load(period='2026-03-31'); self.assertEqual(before,state())

    def test_missing_period_never_falls_back(self):
        with self.assertRaises(FileNotFoundError): self.load(period='2024-01-31')

    def test_reject_bad_identifiers(self):
        for ticker in ('../TEST','*','TEST/foo','TEST?x',''):
            with self.subTest(ticker=ticker), self.assertRaises(ValueError): load_earnings_detail(ticker,root=self.root)
        for period in ('','../../secret','2026-02-31','2026-07-15x'):
            with self.subTest(period=period), self.assertRaises(ValueError): self.load(period=period)
        with self.assertRaises(ValueError): self.load(revision='../secret')

    def test_completed_history_preserves_old_revision(self):
        data=bundle(1); first=self.save(data,'2026-04-16T00:00:00+00:00')
        data['quarterly_pnl'][0]['revenue']=999
        second=self.save(data,'2026-04-17T00:00:00+00:00')
        latest=self.load(period='2026-03-31')
        old=self.load(period='2026-03-31',revision=first.stem)
        self.assertNotEqual(first,second)
        self.assertEqual(latest['cache']['quarterly_pnl'][0]['revenue'],999)
        self.assertEqual(old['cache']['quarterly_pnl'][0]['revenue'],110)
        self.assertTrue((self.root/old['cache']['report_path']).is_file())
        self.assertIsNotNone(old['cache']['margins_8q'][0]['gross'])
        self.assertEqual(old['view']['kind'],'completed')
        with self.assertRaises(FileNotFoundError): self.load(period='2026-06-30',revision=first.stem)

    def test_tampered_snapshot_is_visible_as_warning(self):
        path=self.save(bundle(1),'2026-04-16T00:00:00+00:00')
        d=json.loads(path.read_text()); d['content']['bundle']['verdict']='STRONG';path.write_text(json.dumps(d))
        self.assertEqual(self.load()['view']['warnings'],['history_unavailable'])

    def test_http_entry_validates_and_forwards_selection(self):
        with patch.object(server,'ROOT',str(self.root)):
            httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
            worker=threading.Thread(target=httpd.serve_forever,daemon=True);worker.start()
            try:
                base=f'http://127.0.0.1:{httpd.server_port}/api/earnings-infographic/'
                for tail,code in [('TEST',200),('TEST?period=2026-03-31',200),('TEST?period=2024-01-31',404),('TEST?period=',400),('../TEST',400),('TEST?revision=bad',400),('TEST?revision='+'0'*64,404)]:
                    with self.subTest(tail=tail):
                        try:
                            response=urllib.request.urlopen(base+tail)
                        except urllib.error.HTTPError as error: response=error
                        self.assertEqual(response.status,code)
                        d=json.load(response)
                        if tail=='TEST?period=2026-03-31': self.assertEqual(d['view']['selected_period'],'2026-03-31')
                        if tail=='TEST': self.assertIn('comparison',d)
            finally:
                httpd.shutdown();httpd.server_close();worker.join(timeout=2)

if __name__=='__main__': unittest.main()
