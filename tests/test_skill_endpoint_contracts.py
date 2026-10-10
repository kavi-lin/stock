"""HTTP request and response contracts from the 2026-10-04 live audit.

No provider calls or live Dashboard mutations. Fixtures use actual provider
field names, including the monthly-snapshot shape that previously looked OK.
"""
import importlib.util
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load(name, path):
    path = ROOT / path
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ea = load("endpoint_earnings", "skills/earnings-analyst/scripts/fetch.py")
news = load("endpoint_news", "skills/market-news-analyst/scripts/fetch.py")
fundamentals = load("endpoint_fundamentals", "skills/us-stock-analysis/scripts/analyze.py")
finnhub = load("endpoint_finnhub", "skills/finnhub-client/scripts/finnhub_client.py")
enrich = load("endpoint_enrich", "skills/thematic-screener/scripts/enrich.py")


def test_earnings_bundle_uses_stable_endpoints_and_fields(monkeypatch):
    requested = []
    ratings = [{"date": f"2026-09-{30-i:02d}", "rating": "B",
                "overallScore": score} for i, score in enumerate([4, 4, 4, 2, 2, 2])]

    def transport(path, params, **kw):
        requested.append(path)
        return {
            "/stable/profile": [{"symbol": "TEST"}],
            "/stable/quote": [{"price": 100}],
            "/stable/ratings-historical": ratings,
            "/stable/grades-consensus": [{"strongBuy": 2, "buy": 3, "hold": 1}],
            "/stable/grades-news": [{"publishedDate": "2026-09-30 09:00:00",
                "gradingCompany": "Example", "action": "upgrade", "newGrade": "Buy"}],
        }.get(path, [])

    monkeypatch.setattr(ea, "_fmp_get", transport)
    monkeypatch.setattr(ea, "_cache", lambda: SimpleNamespace(sources={}, metrics={}))
    bundle = ea.fetch_bundle("TEST", income=[{"date": "2026-06-30", "period": "Q2", "fiscalYear": 2026}])
    assert "/stable/ratings-historical" in requested
    assert "/stable/grades-consensus" in requested
    assert "/stable/grades-historical" in requested  # still correct for monthly counts
    assert bundle["analyst"]["rating_history"][0]["ratingScore"] == 4
    assert bundle["analyst"]["rating_trend"] == "improving"
    assert bundle["analyst"]["grades_summary"]["total_analysts"] == 6
    assert bundle["analyst"]["grades_news"][0]["date"] == "2026-09-30"


@pytest.mark.parametrize("scores,want", [([2, 2, 2, 4, 4, 4], "declining"),
    ([3, 3, 3, 3], "stable"), ([5], "insufficient_data")])
def test_rating_trend_higher_financial_score_is_better(scores, want):
    assert ea.compute_rating_trend([{"overallScore": x} for x in scores]) == want


def test_news_entrypoint_preserves_real_events_and_fallback(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-only-key")
    for name in ("_fmp_news_stock", "_fmp_press_releases", "_finviz_news", "_yf_news",
                 "_finnhub_company_news", "_fmp_grades_news", "_fmp_sec_8k_filings"):
        monkeypatch.setattr(news, name, lambda *a, **k: [])
    monkeypatch.setattr(news, "_fmp_sec_filings", lambda *a, **k: ([], False))
    fallback = [{"date": "2026-10-01", "action": "upgrade", "firm": "Fallback"}]
    monkeypatch.setattr(news, "_finviz_analyst_actions", lambda *a: fallback)
    event = {"date": datetime.now(timezone.utc).date().isoformat(), "action": "upgrade",
             "gradingCompany": "Example", "newGrade": "Buy", "previousGrade": "Hold"}
    calls = []

    def transport(path, *args):
        calls.append(path)
        return [event] if path == "grades" else []

    monkeypatch.setattr(news, "_fmp_get", transport)
    payload = news.fetch("TEST", 48)
    assert "grades" in calls and "grades-historical" not in calls
    assert payload["analyst_actions"][0]["firm"] == "Example"
    assert payload["analyst_actions_source"] == "fmp_grades"
    # A nonempty but semantically wrong response must not suppress fallback.
    monkeypatch.setattr(news, "_fmp_get", lambda *a: [{"date": event["date"], "analystRatingsBuy": 20}])
    payload = news.fetch("TEST", 48)
    assert payload["analyst_actions"] == fallback
    assert payload["analyst_actions_source"] == "finviz_fallback"


def test_thematic_counts_events_not_snapshots(monkeypatch):
    calls = []
    today = date.today().isoformat()
    def transport(path, params):
        calls.append(path)
        return ([{"date": today, "action": "upgrade"}, {"date": today, "action": "downgrade"},
                 {"date": today, "action": "upgrade"}, {"date": today, "action": "maintain"},
                 {"date": (date.today()-timedelta(days=90)).isoformat(), "action": "upgrade"}]
                if path == "grades" else [{"date": today, "analystRatingsBuy": 20}])
    monkeypatch.setattr(enrich, "_fmp_get", transport)
    assert enrich.fetch_grades_recent("TEST") == {"upgrades": 2, "downgrades": 1, "since_days": 30}
    assert calls == ["grades"]


def test_sector_pe_weekend_holiday_and_row_selection(monkeypatch):
    from skills._shared import investment_data
    calls = []
    def transport(path, params, **kwargs):
        calls.append(params)
        rows = ([] if params["date"] == "2026-10-02" else
                [{"sector": "Energy", "pe": 7}, {"sector": "Technology", "pe": 33.333}])
        return {"status": "ok" if rows else "empty", "data": rows}
    monkeypatch.setattr(investment_data, "fmp_result", transport)
    assert fundamentals._fmp_sector_pe("Technology", "test-key", as_of=date(2026, 10, 4)) == 33.33
    assert calls == [{"sector": "Technology", "date": "2026-10-02"},
                     {"sector": "Technology", "date": "2026-10-01"}]


def test_sector_pe_does_not_retry_permissions(monkeypatch):
    from skills._shared import investment_data
    calls = []
    def transport(*args, **kw):
        calls.append(args)
        return {"status": "permission_denied", "data": None}
    monkeypatch.setattr(investment_data, "fmp_result", transport)
    assert fundamentals._fmp_sector_pe("Technology", "test-key", as_of=date(2026, 10, 4)) is None
    assert len(calls) == 1


def test_finnhub_split_path_and_permission_error(monkeypatch):
    client = finnhub.FinnhubClient(api_key="test-only-key", use_cache=False)
    calls = []
    def get(url, **kw):
        calls.append(url)
        return SimpleNamespace(status_code=403, text="Access denied")
    monkeypatch.setattr(client.session, "get", get)
    with pytest.raises(finnhub.FinnhubPremiumRequired):
        client.splits("AAPL", "2020-01-01", "2026-10-04")
    assert calls == ["https://finnhub.io/api/v1/stock/split"]


def test_dashboard_preflight_executes_repo_breadth_and_partial_is_visible(monkeypatch):
    with patch("threading.Thread.start"):
        import dashboard_server as server
    monkeypatch.setattr(server, "preflight_check", lambda: [{"key": "breadth", "status": "STALE", "free": True}])
    monkeypatch.setattr(server, "_preflight_state", {"status": "idle", "errors": []})
    calls = []
    monkeypatch.setattr(server.subprocess, "run", lambda cmd, **kw: calls.append(cmd) or SimpleNamespace(returncode=0))
    monkeypatch.setattr(server.threading, "Thread", lambda target, **kw: SimpleNamespace(start=target))
    server.run_free_caches()
    assert Path(calls[0][1]).resolve() == ROOT / "skills/market-breadth-analyzer/scripts/market_breadth_analyzer.py"
    monkeypatch.setattr(server, "_intraday_engine", SimpleNamespace(
        build=lambda: {"_partial": True, "_source_health": {"SPY": "missing"}, "aggregate": {"score": None}},
        _write_atomic=lambda *a: None))
    monkeypatch.setattr(server, "_intraday_mood_state", {})
    server._intraday_mood_refresh("test")
    assert "SPY" in server._intraday_mood_state["last_error"]
