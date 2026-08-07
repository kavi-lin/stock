import json

import pytest

from sector.lib.earnings_calendar import FetchStats, fetch_calendar_range
from sector.scripts import fetch_earnings_calendar as mod
from sector.scripts.phase_prefetch import build_tasks


def _company(symbol="AAPL", market_cap=3_000_000_000, **overrides):
    row = {
        "symbol": symbol,
        "companyName": symbol,
        "marketCap": market_cap,
        "country": "US",
        "exchangeShortName": "NASDAQ",
        "sector": "Technology",
        "industry": "Hardware",
        "isActivelyTrading": True,
        "isEtf": False,
        "isFund": False,
    }
    row.update(overrides)
    return row


def test_company_screener_replaces_per_symbol_profile_fanout(monkeypatch, tmp_path):
    seen = []

    def fake_get(path, params, **kwargs):
        seen.append((path, params, kwargs))
        return [_company(), _company("TINY", market_cap=10)]

    monkeypatch.setattr(mod.fmp_pool, "get", fake_get)
    result, cache_hit = mod.fetch_company_universe(
        api_key="test-key", cache_path=tmp_path / "screener.json"
    )

    assert cache_hit is False
    assert result["AAPL"]["symbol"] == "AAPL"
    assert "TINY" not in result
    assert len(seen) == 1
    assert seen[0][0] == "company-screener"
    assert seen[0][1]["marketCapMoreThan"] == mod.MIN_MARKET_CAP


def test_company_screener_cache_avoids_second_api_call(monkeypatch, tmp_path):
    cache_path = tmp_path / "screener.json"
    cache_path.write_text(json.dumps({"companies": [_company()]}), encoding="utf-8")
    monkeypatch.setattr(
        mod.fmp_pool,
        "get",
        lambda *args, **kwargs: pytest.fail("fresh screener cache must avoid FMP"),
    )

    result, cache_hit = mod.fetch_company_universe(cache_path=cache_path)

    assert cache_hit is True
    assert list(result) == ["AAPL"]


def test_calendar_saturated_range_splits_and_dedupes(tmp_path):
    calls = []

    def fake_get(_path, params, **_kwargs):
        key = (params["from"], params["to"])
        calls.append(key)
        responses = {
            ("2026-08-01", "2026-08-04"): [
                {"symbol": "CAP1", "date": "2026-08-04"},
                {"symbol": "CAP2", "date": "2026-08-04"},
                {"symbol": "CAP3", "date": "2026-08-04"},
            ],
            ("2026-08-01", "2026-08-02"): [
                {"symbol": "AAPL", "date": "2026-08-01"},
                {"symbol": "MSFT", "date": "2026-08-02"},
            ],
            ("2026-08-03", "2026-08-04"): [
                {"symbol": "NVDA", "date": "2026-08-03"},
                {"symbol": "AAPL", "date": "2026-08-04"},
            ],
        }
        return responses[key]

    stats = FetchStats()
    rows = fetch_calendar_range(
        "2026-08-01",
        "2026-08-04",
        cache_dir=tmp_path,
        response_cap=3,
        stats=stats,
        getter=fake_get,
    )

    assert [row["symbol"] for row in rows] == ["AAPL", "MSFT", "NVDA", "AAPL"]
    assert stats.api_calls == 3
    assert stats.splits == 1
    assert len(calls) == 3


def test_calendar_exact_range_cache_avoids_second_api_call(tmp_path):
    first_stats = FetchStats()
    fetch_calendar_range(
        "2026-08-01",
        "2026-08-02",
        cache_dir=tmp_path,
        stats=first_stats,
        getter=lambda *_args, **_kwargs: [{"symbol": "AAPL", "date": "2026-08-01"}],
    )
    second_stats = FetchStats()
    rows = fetch_calendar_range(
        "2026-08-01",
        "2026-08-02",
        cache_dir=tmp_path,
        stats=second_stats,
        getter=lambda *_args, **_kwargs: pytest.fail("fresh calendar cache must avoid FMP"),
    )

    assert rows[0]["symbol"] == "AAPL"
    assert first_stats.api_calls == 1
    assert second_stats.cache_hits == 1


def test_calendar_single_day_saturation_fails_closed(tmp_path):
    with pytest.raises(RuntimeError, match="cannot prove completeness"):
        fetch_calendar_range(
            "2026-08-01",
            "2026-08-01",
            cache_dir=tmp_path,
            response_cap=2,
            getter=lambda *_args, **_kwargs: [
                {"symbol": "A", "date": "2026-08-01"},
                {"symbol": "B", "date": "2026-08-01"},
            ],
        )


def test_build_output_preserves_prefetch_shape_and_filters():
    earnings = [
        {"symbol": "AAPL", "date": "2026-08-06", "time": "amc", "epsEstimated": 1.2},
        {"symbol": "TINY", "date": "2026-08-06", "time": "bmo"},
    ]
    companies = {
        "AAPL": {
            "companyName": "Apple", "marketCap": 3_000_000_000,
            "exchangeShortName": "NASDAQ", "sector": "Technology", "industry": "Hardware",
        },
        "TINY": {"marketCap": 10, "exchangeShortName": "NASDAQ"},
    }

    output = mod.build_output(earnings, companies)

    assert len(output) == 1
    assert output[0]["symbol"] == "AAPL"
    assert output[0]["timing"] == "AMC"
    assert output[0]["marketCapFormatted"] == "$3.0B"


def test_prefetch_uses_repo_owned_governed_calendar_scripts():
    tasks = {task[1]: task[2] for task in build_tasks("2026-08-05")}
    assert tasks["earnings_calendar"][1].endswith(
        "/sector/scripts/fetch_earnings_calendar.py"
    )
    assert tasks["econ_calendar"][1].endswith(
        "/skills/economic-calendar-fetcher/scripts/get_economic_calendar.py"
    )
    assert "/.claude/skills/" not in " ".join(tasks["earnings_calendar"])
    assert "/.claude/skills/" not in " ".join(tasks["econ_calendar"])
