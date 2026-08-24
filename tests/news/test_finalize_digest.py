import json
from datetime import datetime
from pathlib import Path

import pytest

from news.scripts.finalize_digest import DebateInputError, _event_id, finalize


DATE = datetime.now().strftime("%Y-%m-%d")


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _item(i: int, *, news_type="earnings", binary=False):
    return {
        "news_id": f"n{i:04d}", "headline": f"Company {i} material event",
        "headline_zh": None, "source": "Reuters", "source_kind": "wire",
        "source_credibility": "HIGH", "effective_credibility": "HIGH",
        "published": f"{DATE}T{i:02d}:00:00Z", "url": f"https://example.com/{i}",
        "raw_summary": "Material event summary", "news_type": news_type,
        "content_genre": "straight_news", "shallow_score": 2.0,
        "materiality_score": 6.0, "binary_flag": binary,
        "bull_case": "shallow bull", "bear_case": "shallow bear",
        "sector_view": "shallow sector", "macro_view": "shallow macro",
    }


def _setup(tmp_path: Path):
    items = [_item(i, news_type="macro_data" if i == 1 else "earnings", binary=i == 1) for i in range(12)]
    _write(tmp_path / f"news/news_logs/{DATE}_triage.json", {
        "timestamp": f"{DATE}T09:00:00", "raw_count": 12, "items_scored": 12,
        "items_blocked": 0, "items_dedup_dropped": 0, "advanced_count": 2,
        "blocked_counts": {}, "template_dedup_dropped": 0,
        "shallow_verdicts": items, "stage2_items": items[:2],
    })
    _write(tmp_path / "sector/sector_logs/phase0.json", {
        "macro_backdrop_score": 0.5, "news_patch_count": 10, "binary_risks": [],
    })
    _write(tmp_path / f"sector/sector_logs/{DATE}_sector_intel.json", {"top_catalysts": []})

    debate = {
        "fanout_mode": "PER_AGENT_BATCH", "degraded_agents": [],
        "translations": {f"n{i:04d}": f"公司 {i} 重大事件" for i in range(12)},
        "lanes": {
            "bull": {"subagent_isolated": True, "per_item": {
                "n0000": {"interpretation": "需求與財測改善", "impact_score": 4, "confidence": .8},
                "n0001": {"interpretation": "正面結果仍有上行", "impact_score": 2, "confidence": .7},
            }},
            "bear": {"subagent_isolated": True, "per_item": {
                "n0000": {"interpretation": "估值與執行風險", "impact_score": -2, "confidence": .7},
                "n0001": {"interpretation": "負面結果有尾部風險", "impact_score": -4, "confidence": .8, "binary_risk": True},
            }},
            "sector": {"subagent_isolated": True, "per_item": {
                "n0000": {"impact_score": 3, "confidence": .8, "primary_sectors": [{"sector": "Tech", "direction": "bullish", "magnitude": "strong"}], "supply_chain_impact": "suppliers benefit", "tickers_mentioned": ["AAA"]},
                "n0001": {"impact_score": -1, "confidence": .7, "primary_sectors": [{"sector": "Financials", "direction": "bearish", "magnitude": "moderate"}], "supply_chain_impact": "credit tightens", "tickers_mentioned": []},
            }},
            "macro": {"subagent_isolated": True, "per_item": {
                "n0000": {"impact_score": 0, "confidence": .7, "fed_path_delta": "neutral", "yield_curve_impact": "none", "fx_commodity_impact": "none", "historical_analogue": "none"},
                "n0001": {"impact_score": -3, "confidence": .8, "binary_risk": True, "fed_path_delta": "dovish", "yield_curve_impact": "bull steepening", "fx_commodity_impact": "USD firm", "historical_analogue": "prior shock"},
            }},
        },
        "arbiter": {"per_item": {
            "n0000": {"binary_risk": False, "macro_backdrop_delta": .2, "reasoning_note": "基本面偏多。", "debate_note": "成長與估值分歧", "evidence_urls": ["https://example.com/0"]},
            "n0001": {"binary_risk": True, "binary_event_date": "2026-08-07", "within_48h": True, "macro_backdrop_delta": -.3, "reasoning_note": "事件結果未決。", "debate_note": "政策結果分支", "evidence_urls": []},
        }},
    }
    debate_path = tmp_path / f"news/news_logs/{DATE}_debate.json"
    _write(debate_path, debate)
    return debate_path


def test_finalize_builds_artifacts_and_patches_idempotently(tmp_path):
    debate_path = _setup(tmp_path)
    result = finalize(DATE, debate_path, root=tmp_path, now=f"{DATE} 10:30", validate=False)

    digest = json.loads(Path(result["digest"]).read_text())
    assert digest["arbiter_rule_version"] == "V2.3"
    assert digest["stage1_count"] == 12
    assert digest["stage2_count"] == 2
    assert len(digest["verdicts"]) == 12
    deep = digest["verdicts"][:2]
    assert deep[0]["verdict"] == "BULLISH"
    assert deep[0]["net_impact_score"] == 1.7
    assert deep[1]["verdict"] == "BINARY"
    assert deep[1]["directional_bias"] == "BEARISH"
    assert "Deep Analysis" in Path(result["report"]).read_text()
    first_digest_bytes = Path(result["digest"]).read_bytes()

    phase0_path = tmp_path / "sector/sector_logs/phase0.json"
    phase0 = json.loads(phase0_path.read_text())
    assert phase0["news_patch_count"] == 12
    assert phase0["macro_backdrop_score"] == 0.4
    assert len(phase0["binary_risks"]) == 1
    assert len(phase0["applied_news_event_ids"]) == 2

    # Same debate replay: no counter, score, risk, or catalyst duplication.
    second = finalize(DATE, debate_path, root=tmp_path, now=f"{DATE} 10:30", validate=False)
    phase0_again = json.loads(phase0_path.read_text())
    intel = json.loads(Path(second["cache"]["sector_intel"]).read_text())
    assert phase0_again == phase0
    assert len(intel["top_catalysts"]) == 2
    assert second["cache"]["new_events"] == 0
    assert second["events"]["appended"] == 0
    assert Path(second["digest"]).read_bytes() == first_digest_bytes


def test_finalize_rejects_missing_lane_confidence(tmp_path):
    debate_path = _setup(tmp_path)
    debate = json.loads(debate_path.read_text())
    del debate["lanes"]["bull"]["per_item"]["n0000"]["confidence"]
    _write(debate_path, debate)
    with pytest.raises(DebateInputError, match="confidence"):
        finalize(DATE, debate_path, root=tmp_path, now=f"{DATE} 10:30", validate=False)


def test_finalize_rejects_binary_without_lane_flags(tmp_path):
    debate_path = _setup(tmp_path)
    debate = json.loads(debate_path.read_text())
    del debate["lanes"]["macro"]["per_item"]["n0001"]["binary_risk"]
    _write(debate_path, debate)
    with pytest.raises(DebateInputError, match="Bear and Macro"):
        finalize(DATE, debate_path, root=tmp_path, now=f"{DATE} 10:30", validate=False)


def test_event_id_ignores_tracking_query_and_triage_rank():
    first = {"news_id": "n0001", "headline": "Event", "url": "https://EXAMPLE.com/a/?utm_source=x"}
    second = {"news_id": "n0099", "headline": "Changed translation", "url": "https://example.com/a"}
    assert _event_id(first) == _event_id(second)


def test_finalize_output_passes_real_validator(tmp_path):
    debate_path = _setup(tmp_path)
    result = finalize(
        DATE, debate_path, root=tmp_path, now=f"{DATE} 10:30",
        validate=True, patch_caches=False,
    )
    assert Path(result["digest"]).exists()


def _flatten(debate: dict, news_id: str):
    """Make one item's Bull/Bear come back inside the non-substantive band."""
    debate["lanes"]["bull"]["per_item"][news_id]["impact_score"] = 1
    debate["lanes"]["bear"]["per_item"][news_id]["impact_score"] = -1


def test_flat_item_is_demoted_to_shallow_not_fatal(tmp_path):
    debate_path = _setup(tmp_path)
    debate = json.loads(debate_path.read_text())
    _flatten(debate, "n0000")
    _write(debate_path, debate)

    result = finalize(
        DATE, debate_path, root=tmp_path, now=f"{DATE} 10:30",
        validate=True, patch_caches=False,
    )
    digest = json.loads(Path(result["digest"]).read_text())

    assert digest["demoted_stage2"] == ["n0000"]
    assert digest["stage2_count"] == 1
    deep = [v for v in digest["verdicts"] if v["depth"] == "deep"]
    shallow = [v for v in digest["verdicts"] if v["depth"] == "shallow"]
    assert [v["news_id"] for v in deep] == ["n0001"]
    # Demoted row is present, marked, and took a slot rather than a seat past
    # the projection's 10-row shallow cap.
    assert len(shallow) == 10
    demoted_rows = [v for v in shallow if v["news_id"] == "n0000"]
    assert len(demoted_rows) == 1
    assert demoted_rows[0]["demoted_from"] == "stage2_non_substantive"
    assert demoted_rows[0]["verdict"] is None
    assert "n0000" in Path(result["report"]).read_text()


def test_majority_flat_debate_still_fails(tmp_path):
    debate_path = _setup(tmp_path)
    debate = json.loads(debate_path.read_text())
    _flatten(debate, "n0000")
    _flatten(debate, "n0001")
    _write(debate_path, debate)
    with pytest.raises(DebateInputError, match="absent debate"):
        finalize(DATE, debate_path, root=tmp_path, now=f"{DATE} 10:30", validate=False)


def test_flat_item_with_empty_interpretation_still_fails(tmp_path):
    """Demotion must not become the cheap exit for a lane that wrote nothing."""
    debate_path = _setup(tmp_path)
    debate = json.loads(debate_path.read_text())
    _flatten(debate, "n0000")
    debate["lanes"]["bear"]["per_item"]["n0000"]["interpretation"] = "   "
    _write(debate_path, debate)
    with pytest.raises(DebateInputError, match="interpretation must be non-empty"):
        finalize(DATE, debate_path, root=tmp_path, now=f"{DATE} 10:30", validate=False)


def test_partial_fallback_caps_degraded_lane_confidence(tmp_path):
    debate_path = _setup(tmp_path)
    debate = json.loads(debate_path.read_text())
    debate["fanout_mode"] = "PARTIAL_FALLBACK"
    debate["degraded_agents"] = ["Bull_Analyst"]
    debate["lanes"]["bull"]["subagent_isolated"] = False
    _write(debate_path, debate)
    with pytest.raises(DebateInputError, match="degraded lane confidence"):
        finalize(DATE, debate_path, root=tmp_path, now=f"{DATE} 10:30", validate=False)
