import json
from pathlib import Path

from scripts.nexus import supply_chain as sc


def _write_local_indexes(tmp_path: Path, monkeypatch, *, universe=None, nexus_nodes=None, nexus_edges=None):
    universe_path = tmp_path / "heatmap_universe.json"
    nexus_path = tmp_path / "nexus_graph.json"
    universe_path.write_text(
        json.dumps({"tickers": [{"ticker": t} for t in (universe or [])]}),
        encoding="utf-8",
    )
    nexus_path.write_text(
        json.dumps({"nodes": nexus_nodes or [], "edges": nexus_edges or []}),
        encoding="utf-8",
    )
    monkeypatch.setattr(sc, "UNIVERSE_FILE", universe_path)
    monkeypatch.setattr(sc, "NEXUS_FILE", nexus_path)
    monkeypatch.setattr(sc, "FMP_SC_CACHE_DIR", tmp_path / "fmp_cache")
    monkeypatch.setattr(sc, "OVERRIDES_DIR", tmp_path / "overrides")
    monkeypatch.setattr(sc, "_digest_paths_30d", lambda: [])


def _seed_budget(tmp_path, calls_used, budget=2000):
    cache_dir = tmp_path / "fmp_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    day = sc.datetime.now(sc.timezone.utc).strftime("%Y-%m-%d")
    (cache_dir / f"_budget_{day}.json").write_text(json.dumps(
        {"date": day, "calls_used": calls_used, "budget": budget,
         "budget_exhausted": False}), encoding="utf-8")


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


def test_foreign_listing_keeps_local_market_display_and_investability(tmp_path, monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    _write_local_indexes(tmp_path, monkeypatch)
    node = sc.enrich(_chain([
        {
            "id": "tsmc",
            "label": "TSMC",
            "ticker": None,
            "listing": "foreign_listed",
            "market": "TW",
            "exchange": "TWSE",
            "local_ticker": "2330",
            "adr_ticker": "TSM",
        },
    ]))["nodes"][0]

    assert node["market"] == "TW"
    assert node["market_label"] == "Taiwan-listed"
    assert node["display_symbol"] == "TW:2330"
    assert node["investability"] == "adr_or_us_proxy"


def test_foreign_listing_backfill_common_asian_names(tmp_path, monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    _write_local_indexes(tmp_path, monkeypatch)
    out = sc.enrich(_chain([
        {"id": "tsmc", "label": "TSMC", "ticker": None, "listing": "foreign_listed"},
        {"id": "samsung", "label": "Samsung Electronics", "ticker": None, "listing": "foreign_listed"},
        {"id": "tel", "label": "Tokyo Electron", "ticker": None, "listing": "foreign_listed"},
    ]))
    by_id = {n["id"]: n for n in out["nodes"]}

    assert by_id["tsmc"]["display_symbol"] == "TW:2330"
    assert by_id["tsmc"]["adr_ticker"] == "TSM"
    assert by_id["tsmc"]["investability"] == "adr_or_us_proxy"
    assert by_id["samsung"]["display_symbol"] == "KR:005930"
    assert by_id["samsung"]["investability"] == "international_broker"
    assert by_id["tel"]["display_symbol"] == "JP:8035"


def test_foreign_listing_backfill_does_not_override_manual_fields(tmp_path, monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    _write_local_indexes(tmp_path, monkeypatch)
    node = sc.enrich(_chain([
        {
            "id": "tsmc",
            "label": "TSMC",
            "ticker": None,
            "listing": "foreign_listed",
            "market": "TW",
            "exchange": "TPEX",
            "local_ticker": "CUSTOM",
            "country": "Manual",
        },
    ]))["nodes"][0]

    assert node["exchange"] == "TPEX"
    assert node["local_ticker"] == "CUSTOM"
    assert node["country"] == "Manual"
    assert node["display_symbol"] == "TW:CUSTOM"


def test_chain_report_surfaces_investable_bottlenecks_and_private_proxies(tmp_path, monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    _write_local_indexes(tmp_path, monkeypatch, universe=["NVDA", "TSM"])
    chain = _chain(
        [
            {"id": "tsmc", "label": "TSMC", "ticker": "TSM", "listing": "us_listed", "role": "foundry"},
            {"id": "nvda", "label": "NVIDIA", "ticker": "NVDA", "listing": "us_listed", "role": "accelerator"},
            {
                "id": "private_optics",
                "label": "Private Optics",
                "ticker": None,
                "listing": "private",
                "role": "optical engine",
                "proxy_tickers": ["COHR"],
            },
        ],
        [
            {"from": "tsmc", "to": "nvda", "rel": "SUPPLIES_TO"},
            {"from": "private_optics", "to": "nvda", "rel": "SUPPLIES_TO"},
        ],
    )
    chain["spine"] = ["tsmc", "nvda"]
    out = sc.enrich(chain)
    report = out["chain_report"]

    assert report["summary"]["investable_count"] == 2
    assert any(n["symbol"] == "US:NVDA" for n in report["investable_nodes"])
    assert any(n["label"] == "TSMC" and n["downstream_links"] == 1 for n in report["bottlenecks"])
    assert report["private_or_watch_only"][0]["proxy_tickers"] == ["COHR", "US:NVDA"]
    assert report["relation_confidence"]["llm_relation"] == 2


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


def test_break_news_provisional_requires_compatible_relation_direction(tmp_path, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    monkeypatch.setattr(sc, "_fmp_get", lambda *args, **kwargs: ([], "ok"))
    base_edges = [
        {
            "source": "ticker:NVDA",
            "target": "ticker:TSM",
            "type": "SUPPLIES_TO",
            "sources": ["break_news:wrong_direction"],
            "metadata": {"provisional": True},
        },
        {
            "source": "ticker:TSM",
            "target": "ticker:NVDA",
            "type": "COMPETES_WITH",
            "sources": ["break_news:wrong_type"],
            "metadata": {"provisional": True},
        },
    ]
    _write_local_indexes(
        tmp_path, monkeypatch, universe=["NVDA", "TSM"], nexus_edges=base_edges
    )

    out = sc.enrich(_chain(
        [
            {"id": "tsmc", "label": "TSMC", "ticker": "TSM", "listing": "us_listed"},
            {"id": "nvda", "label": "NVIDIA", "ticker": "NVDA", "listing": "us_listed"},
        ],
        [{"from": "tsmc", "to": "nvda", "rel": "SUPPLIES_TO"}],
    ))

    assert out["edges"][0]["relation_evidence"]["level"] == "llm_relation"
    assert out["edges"][0]["relation_evidence"]["weight"] == 0.4


def test_break_news_provisional_marks_compatible_supply_chain_edge(tmp_path, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    monkeypatch.setattr(sc, "_fmp_get", lambda *args, **kwargs: ([], "ok"))
    _write_local_indexes(
        tmp_path,
        monkeypatch,
        universe=["NVDA", "TSM"],
        nexus_edges=[{
            "source": "ticker:TSM",
            "target": "ticker:NVDA",
            "type": "SUPPLIES_TO",
            "sources": ["break_news:compatible"],
            "metadata": {"provisional": True},
        }],
    )

    out = sc.enrich(_chain(
        [
            {"id": "tsmc", "label": "TSMC", "ticker": "TSM", "listing": "us_listed"},
            {"id": "nvda", "label": "NVIDIA", "ticker": "NVDA", "listing": "us_listed"},
        ],
        [{"from": "tsmc", "to": "nvda", "rel": "SUPPLIES_TO"}],
    ))
    ev = out["edges"][0]["relation_evidence"]

    assert ev["level"] == "break_news_provisional"
    assert ev["weight"] == 0.2
    assert ev["sources"] == ["break_news:compatible"]


# ── Wave A: direction validation / stale / heat-relative / ADR / write-back ──
def _corroborated_chain(tmp_path, monkeypatch, *, nexus_edges=None):
    """NVDA←TSM chain with 3 digest co-mentions (corroborated) + optional edges."""
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    monkeypatch.setattr(sc, "_fmp_get", lambda *args, **kwargs: ([], "ok"))
    digest = tmp_path / "2026-05-21_digest.json"
    digest.write_text(json.dumps({"verdicts": [
        {"news_id": "n1", "tickers_mentioned": ["NVDA", "TSM"]},
        {"news_id": "n2", "tickers_mentioned": ["NVDA", "TSM"]},
        {"news_id": "n3", "tickers_mentioned": ["NVDA", "TSM"]},
    ]}), encoding="utf-8")
    _write_local_indexes(tmp_path, monkeypatch, universe=["NVDA", "TSM"],
                         nexus_edges=nexus_edges)
    monkeypatch.setattr(sc, "_digest_paths_30d", lambda: [digest])
    return _chain(
        [
            {"id": "tsmc", "label": "TSMC", "ticker": "TSM", "listing": "us_listed"},
            {"id": "nvda", "label": "NVIDIA", "ticker": "NVDA", "listing": "us_listed"},
        ],
        [{"from": "tsmc", "to": "nvda", "rel": "SUPPLIES_TO"}],
    )


def test_direction_confirmed_keeps_full_weight(tmp_path, monkeypatch):
    chain = _corroborated_chain(tmp_path, monkeypatch, nexus_edges=[{
        "source": "ticker:TSM", "target": "ticker:NVDA", "type": "SUPPLIES_TO",
        "sources": ["digest:x"],
    }])
    ev = sc.enrich(chain)["edges"][0]["relation_evidence"]
    assert ev["level"] == "corroborated_relation"
    assert ev["direction"] == "confirmed"
    assert ev["weight"] == 1.0


def test_direction_conflict_halves_corroborated_weight(tmp_path, monkeypatch):
    # Nexus says NVDA→TSM but the LLM drew TSM→NVDA: contradiction.
    chain = _corroborated_chain(tmp_path, monkeypatch, nexus_edges=[{
        "source": "ticker:NVDA", "target": "ticker:TSM", "type": "SUPPLIES_TO",
        "sources": ["digest:x"],
    }])
    ev = sc.enrich(chain)["edges"][0]["relation_evidence"]
    assert ev["level"] == "corroborated_relation"
    assert ev["direction"] == "conflict"
    assert ev["weight"] == 0.5


def test_stale_flag_on_aged_uncorroborated_node(tmp_path, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    monkeypatch.setattr(sc, "_fmp_get", lambda *args, **kwargs: ([], "ok"))
    _write_local_indexes(tmp_path, monkeypatch)
    ghost = {"id": "ghost", "label": "Ghost Co", "ticker": None, "listing": "private"}

    aged = _chain([dict(ghost)])
    aged["generated_at"] = "2020-01-01T00:00:00Z"
    out = sc.enrich(aged)
    assert out["nodes"][0]["verification_level"] == "llm_only"
    assert out["nodes"][0]["stale"] is True
    assert out["data_quality"]["stale_node_count"] == 1

    fresh = _chain([dict(ghost)])
    fresh["generated_at"] = sc._now_iso()
    assert sc.enrich(fresh)["nodes"][0]["stale"] is False


def test_heat_relative_downgrades_absolute_hot_in_high_spread_chain(tmp_path, monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    nexus_nodes = [
        {"type": "ticker", "label": "AAA", "mentions": 100},
        {"type": "ticker", "label": "BBB", "mentions": 90},
        {"type": "ticker", "label": "CCC", "mentions": 80},
        {"type": "ticker", "label": "DDD", "mentions": 12},
        {"type": "ticker", "label": "EEE", "mentions": 5},
    ]
    _write_local_indexes(tmp_path, monkeypatch, nexus_nodes=nexus_nodes)
    out = sc.enrich(_chain([
        {"id": "a", "label": "A", "ticker": "AAA", "listing": "us_listed"},
        {"id": "b", "label": "B", "ticker": "BBB", "listing": "us_listed"},
        {"id": "c", "label": "C", "ticker": "CCC", "listing": "us_listed"},
        {"id": "d", "label": "D", "ticker": "DDD", "listing": "us_listed"},
        {"id": "e", "label": "E", "ticker": "EEE", "listing": "us_listed"},
    ]))
    by_id = {n["id"]: n for n in out["nodes"]}
    assert by_id["a"]["heat"] == "hot"
    # 80 mentions is absolute-hot but below this chain's 67th pct → relative warm
    assert by_id["c"]["heat"] == "warm"
    assert by_id["e"]["heat"] == "cold"


def test_foreign_name_match_promotes_adr_to_tradeable(tmp_path, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    _write_local_indexes(tmp_path, monkeypatch)

    def fake_fmp(path, params, *, timeout=12):
        if path == "/stable/search-name":
            return ([{"symbol": "XYZ", "companyName": "Foreign Co",
                      "exchangeShortName": "NASDAQ"}], "ok")
        return ([], "ok")

    monkeypatch.setattr(sc, "_fmp_get", fake_fmp)
    node = sc.enrich(_chain([
        {"id": "fco", "label": "Foreign Co", "ticker": None, "listing": "foreign_listed"},
    ]))["nodes"][0]

    assert node["verification_level"] == "name_match"
    assert node["adr_ticker"] == "XYZ"
    assert node["display_symbol"] == "ADR:XYZ"
    assert sc._node_investable(node) is True


def test_corroborated_relations_emit_directed_supply_chain_payload(tmp_path, monkeypatch):
    chain = _corroborated_chain(tmp_path, monkeypatch)
    sc.enrich(chain)
    rels = sc._corroborated_relations(chain)
    assert len(rels) == 1
    r = rels[0]
    assert (r["subject"], r["predicate"], r["object"]) == ("ticker:TSM", "SUPPLIES_TO", "ticker:NVDA")
    assert r["support_count"] == 3
    assert r["source_agents"] == ["supply_chain"]
    assert r["provisional"] is True


def test_corroborated_relations_excludes_direction_conflict(tmp_path, monkeypatch):
    chain = _corroborated_chain(tmp_path, monkeypatch, nexus_edges=[{
        "source": "ticker:NVDA", "target": "ticker:TSM", "type": "SUPPLIES_TO",
        "sources": ["digest:x"],
    }])
    sc.enrich(chain)
    assert sc._corroborated_relations(chain) == []


# ── Wave B: user override / budget tiering ──────────────────────────────────
def test_override_corrects_field_and_attaches_status(tmp_path, monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    _write_local_indexes(tmp_path, monkeypatch, universe=["NVDA"])
    sc.save_override("test", "x", status="confirmed", fields={"ticker": "nvda"})
    out = sc.enrich(_chain([
        {"id": "x", "label": "Mystery", "ticker": None, "listing": "private"},
    ]))
    n = out["nodes"][0]
    assert n["ticker"] == "NVDA"          # corrected + uppercased by the sidecar
    assert n["grounding"] == "verified"   # correction flows into grounding
    assert n["user_status"] == "confirmed"
    assert n["user_override"] is True
    assert out["data_quality"]["override_count"] == 1


def test_override_clear_removes_entry(tmp_path, monkeypatch):
    _write_local_indexes(tmp_path, monkeypatch)
    sc.save_override("test", "x", status="flagged", note="bad ticker")
    assert "x" in sc.load_overrides("test")
    sc.save_override("test", "x", status="none", note="")
    assert "x" not in sc.load_overrides("test")


def test_override_rejects_bad_status(tmp_path, monkeypatch):
    _write_local_indexes(tmp_path, monkeypatch)
    import pytest
    with pytest.raises(ValueError):
        sc.save_override("test", "x", status="bogus")


def test_budget_tiering_skips_peripheral_name_search_when_low(tmp_path, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    _write_local_indexes(tmp_path, monkeypatch)
    _seed_budget(tmp_path, calls_used=1800)  # headroom 0.1 → tiering active
    searches = []

    def fake_fmp(path, params, *, timeout=12):
        if path == "/stable/search-name":
            searches.append(params["query"])
        return ([], "ok")

    monkeypatch.setattr(sc, "_fmp_get", fake_fmp)
    out = sc.enrich(_chain([
        {"id": "ghost", "label": "Ghost Private Co", "ticker": None, "listing": "private"},
    ]))
    # peripheral (no ticker / not spine / no downstream) + low budget → no search
    assert searches == []
    assert out["nodes"][0]["verification_level"] == "llm_only"


def test_budget_healthy_allows_peripheral_name_search(tmp_path, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    _write_local_indexes(tmp_path, monkeypatch)  # fresh budget → headroom 1.0
    searches = []

    def fake_fmp(path, params, *, timeout=12):
        if path == "/stable/search-name":
            searches.append(params["query"])
        return ([], "ok")

    monkeypatch.setattr(sc, "_fmp_get", fake_fmp)
    sc.enrich(_chain([
        {"id": "ghost", "label": "Ghost Co", "ticker": None, "listing": "private"},
    ]))
    assert searches == ["Ghost Co"]
