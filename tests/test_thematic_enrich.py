import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "thematic_enrich",
    ROOT / "skills" / "thematic-screener" / "scripts" / "enrich.py",
)
enrich = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(enrich)


def test_fmp_get_routes_through_shared_pool(monkeypatch):
    calls = []

    def fake_get(path, params, **kwargs):
        calls.append((path, params, kwargs))
        return [{"ok": True}]

    monkeypatch.setattr(enrich.fmp_pool, "get", fake_get)

    result = enrich._fmp_get("price-target-consensus", {"symbol": "AAPL"}, timeout=7)

    assert result == [{"ok": True}]
    assert calls == [(
        "price-target-consensus",
        {"symbol": "AAPL"},
        {"stable": True, "retries": 2, "timeout": 7},
    )]


def test_enrich_movers_collects_parallel_results(monkeypatch):
    monkeypatch.setattr(enrich, "_prune_enrich_cache", lambda: None)
    monkeypatch.setattr(
        enrich,
        "enrich_one",
        lambda ticker, force=False: {"ticker": ticker, "force": force},
    )

    result = enrich.enrich_movers(["AAPL", "MSFT", "NVDA"], force=True, workers=3)

    assert set(result) == {"AAPL", "MSFT", "NVDA"}
    assert all(item["force"] is True for item in result.values())

