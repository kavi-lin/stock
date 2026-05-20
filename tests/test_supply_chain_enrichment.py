import json
from pathlib import Path

from scripts.nexus import supply_chain as sc


def _write_local_indexes(tmp_path: Path, monkeypatch, *, universe=None, nexus_nodes=None):
    universe_path = tmp_path / "heatmap_universe.json"
    nexus_path = tmp_path / "nexus_graph.json"
    universe_path.write_text(
        json.dumps({"tickers": [{"ticker": t} for t in (universe or [])]}),
        encoding="utf-8",
    )
    nexus_path.write_text(json.dumps({"nodes": nexus_nodes or [], "edges": []}), encoding="utf-8")
    monkeypatch.setattr(sc, "UNIVERSE_FILE", universe_path)
    monkeypatch.setattr(sc, "NEXUS_FILE", nexus_path)
    monkeypatch.setattr(sc, "FMP_SC_CACHE_DIR", tmp_path / "fmp_cache")
    monkeypatch.setattr(sc, "_digest_paths_30d", lambda: [])


def _chain(nodes, edges=None):
    return {
        "id": "test",
        "title": "Test",
        "nodes": nodes,
        "edges": edges or [],
        "layers": ["upstream", "downstream"],
    }


def test_no_fmp_key_marks_fmp_unavailable_without_llm_on_tracked_ticker(tmp_path, monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    _write_local_indexes(tmp_path, monkeypatch, universe=["NVDA"])
    chain = _chain([
        {"id": "nvda", "label": "NVIDIA", "ticker": "NVDA", "listing": "us_listed"},
    ])

    out = sc.enrich(chain)
    node = out["nodes"][0]

    assert node["grounding"] == "verified"
    assert node["verification_level"] == "fmp_unavailable"
    assert out["data_quality"]["fmp_enabled"] is False


def test_alias_profile_uses_batch_fmp_and_sets_alias(tmp_path, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    _write_local_indexes(tmp_path, monkeypatch)
    calls = []

    def fake_fmp(path, params, *, timeout=12):
        calls.append((path, params))
        if path == "/stable/profile":
            assert params["symbol"] == "TSM"
            return ([{
                "symbol": "TSM",
                "companyName": "Taiwan Semiconductor Manufacturing Company Limited",
                "exchangeShortName": "NYSE",
                "sector": "Technology",
                "industry": "Semiconductors",
                "marketCap": 900_000_000_000,
            }], "ok")
        if path == "/stable/stock-peers":
            return ([{"symbol": "NVDA"}, {"symbol": "AMD"}], "ok")
        return ([], "ok")

    monkeypatch.setattr(sc, "_fmp_get", fake_fmp)
    chain = _chain([
        {"id": "tsmc", "label": "TSMC", "listing": "foreign_listed"},
    ])

    node = sc.enrich(chain)["nodes"][0]

    assert node["verification_level"] == "fmp_profile"
    assert node["alias_used"] == "TSM"
    assert node["fmp_profile"]["symbol"] == "TSM"
    assert node["fmp_peers"] == ["NVDA", "AMD"]
    assert calls[0][0] == "/stable/profile"


def test_budget_exhausted_serves_cache_only_and_sets_quality_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    _write_local_indexes(tmp_path, monkeypatch)
    cache_dir = tmp_path / "fmp_cache"
    cache_dir.mkdir(parents=True)
    day = sc.datetime.now(sc.timezone.utc).strftime("%Y-%m-%d")
    (cache_dir / f"_budget_{day}.json").write_text(
        json.dumps({"date": day, "calls_used": 150, "budget": 150, "budget_exhausted": True}),
        encoding="utf-8",
    )

    def fail_fmp(*args, **kwargs):
        raise AssertionError("FMP should not be called after budget exhaustion")

    monkeypatch.setattr(sc, "_fmp_get", fail_fmp)
    out = sc.enrich(_chain([
        {"id": "mu", "label": "Micron", "ticker": "MU", "listing": "us_listed"},
    ]))

    assert out["nodes"][0]["verification_level"] == "fmp_unavailable"
    assert out["data_quality"]["fmp_budget_exhausted"] is True


def test_search_name_requires_us_exchange_and_emits_name_match(tmp_path, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    _write_local_indexes(tmp_path, monkeypatch)

    def fake_fmp(path, params, *, timeout=12):
        if path == "/stable/search-name":
            return ([{
                "symbol": "META",
                "companyName": "Meta Platforms, Inc.",
                "exchangeShortName": "NASDAQ",
                "sector": "Communication Services",
                "industry": "Internet Content & Information",
            }], "ok")
        return ([], "ok")

    monkeypatch.setattr(sc, "_fmp_get", fake_fmp)
    node = sc.enrich(_chain([
        {"id": "meta", "label": "Meta Platforms", "listing": "private"},
    ]))["nodes"][0]

    assert node["verification_level"] == "name_match"
    assert node["fmp_profile"]["symbol"] == "META"


def test_relation_evidence_counts_only_strict_digest_ticker_mentions(tmp_path, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    _write_local_indexes(tmp_path, monkeypatch, universe=["NVDA", "TSM"])
    digest = tmp_path / "2026-05-21_digest.json"
    digest.write_text(json.dumps({
        "verdicts": [
            {"news_id": "n1", "tickers_mentioned": ["NVDA", "TSM"], "bull_case": "NVDA mentions TSM"},
            {"news_id": "n2", "tickers_mentioned": ["TSM", "NVDA"]},
            {"news_id": "n3", "tickers_mentioned": ["NVDA", "TSM", "AMD"]},
            {"news_id": "prose-only", "tickers_mentioned": ["NVDA"], "bear_case": "TSM appears only in prose"},
        ]
    }), encoding="utf-8")
    monkeypatch.setattr(sc, "_digest_paths_30d", lambda: [digest])
    monkeypatch.setattr(sc, "_fmp_get", lambda *args, **kwargs: ([], "ok"))

    out = sc.enrich(_chain(
        [
            {"id": "nvda", "label": "NVIDIA", "ticker": "NVDA", "listing": "us_listed"},
            {"id": "tsmc", "label": "TSMC", "ticker": "TSM", "listing": "us_listed"},
        ],
        [{"from": "nvda", "to": "tsmc", "rel": "SUPPLIES_TO"}],
    ))
    ev = out["edges"][0]["relation_evidence"]

    assert ev["level"] == "corroborated_relation"
    assert ev["co_mention_count_30d"] == 3
    assert ev["method"] == "digest_tickers_mentioned_30d"
