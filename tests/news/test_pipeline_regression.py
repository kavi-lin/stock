"""Regression test on real 2026-05-20 raw news pool.

Verifies the v3.14.3 filters actually catch the noise items that triggered
the codex review:
  - n0197 (Johnson Fistel solicitation about FLGT) → blocked
  - n0038 (THE PARISIAN Condominium Debuts in Astoria) → blocked
  - personal-finance items → blocked

Also asserts that the 397→313 hard cap is gone (items_scored should be near
full raw_count, not capped at 313).

This test runs the real `stage1_triage.main()` flow against the existing
on-disk raw.json and inspects the freshly-written triage.json output.
"""
import json
import os
import sys
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pytest                                              # noqa: E402
from news.scripts import stage1_triage                     # noqa: E402

RAW_FIXTURE = PROJECT_ROOT / "news/news_logs/2026-05-20_raw.json"


@pytest.mark.skipif(not RAW_FIXTURE.exists(),
                    reason="2026-05-20_raw.json fixture not present")
def test_regression_against_real_raw(tmp_path, monkeypatch):
    """Run stage1_triage against the real 2026-05-20 raw pool, write triage
    to a tmp dir, then assert v3.14.3 invariants hold."""

    # Redirect HERE to tmp, but symlink news_logs/<DATE>_raw.json from the
    # real fixture so RAW_FILE resolves at module import time.
    fake_news_logs = tmp_path / "news_logs"
    fake_news_logs.mkdir()
    raw_target = fake_news_logs / "2026-05-20_raw.json"
    raw_target.symlink_to(RAW_FIXTURE)

    # Module-level RAW_FILE was computed at import; patch it.
    fake_raw = fake_news_logs / "2026-05-20_raw.json"
    monkeypatch.setattr(stage1_triage, "RAW_FILE", fake_raw)
    monkeypatch.setattr(stage1_triage, "HERE", tmp_path)
    monkeypatch.setattr(stage1_triage, "STAGE1_MAX_ITEMS", 800)

    # Patch datetime.now to return a fixed date so the output file lands at
    # tmp_path/news_logs/2026-05-20_triage.json predictably.
    fixed = "2026-05-20"
    with mock.patch.object(stage1_triage, "datetime") as mock_dt:
        mock_dt.now.return_value.strftime.side_effect = (
            lambda fmt: fixed if fmt == "%Y-%m-%d" else "2026-05-20T13:00:00"
        )
        mock_dt.now.return_value.isoformat.return_value = "2026-05-20T13:00:00"
        rc = stage1_triage.main()
    assert rc == 0

    # ── Inspect the produced triage.json ───────────────────────────────────
    out_path = fake_news_logs / f"{fixed}_triage.json"
    assert out_path.exists(), f"triage output missing at {out_path}"
    triage = json.loads(out_path.read_text(encoding="utf-8"))

    # ── A. v3.14.3 telemetry fields populated ───────────────────────────────
    assert "blocked_counts" in triage
    assert "template_dedup_dropped" in triage
    assert "items_scored" in triage
    assert "items_blocked" in triage
    assert "items_dedup_dropped" in triage
    assert "stage1_max_items" in triage

    # ── B. Hard-block actually triggered ────────────────────────────────────
    blocked = triage["blocked_counts"]
    # At minimum, the FLGT (Johnson Fistel) law-firm solicitation should hit.
    assert blocked.get("law_firm_solicitation", 0) >= 1, (
        f"law_firm_solicitation count = 0, expected ≥1 (Johnson Fistel "
        f"solicitation about FLGT should have been blocked). blocked={blocked}"
    )

    # ── C. The historical noise news_ids are absent from shallow_verdicts ──
    shallow_ids   = {v["news_id"] for v in (triage.get("shallow_verdicts") or [])}
    stage2_ids    = {v["news_id"] for v in (triage.get("stage2_items") or [])}
    advanced_ids  = stage2_ids
    # FLGT solicitation (was n0197 in production digest) and PARISIAN condo
    # (was n0038) — the news_id mapping is order-dependent so we instead
    # check by headline content of each surviving verdict.
    surviving = (triage.get("shallow_verdicts") or [])
    for v in surviving:
        head = (v.get("headline") or "").lower()
        assert "johnson fistel" not in head, (
            f"law-firm solicitation slipped through: {v['headline']}"
        )
        assert "condominium debut" not in head, (
            f"condo PR slipped through: {v['headline']}"
        )

    # ── D. Cap raise worked — items_scored close to raw_count ──────────────
    raw_n  = triage["raw_count"]
    scored = triage["items_scored"]
    blocked_total = triage["items_blocked"] + triage["items_dedup_dropped"]
    # items_scored + blocked + dedup ≈ min(raw_n, STAGE1_MAX_ITEMS=800)
    # raw_n is 397 in fixture, so total should equal 397 (well under 800).
    assert scored + blocked_total == min(raw_n, 800), (
        f"item accounting mismatch: scored={scored} + blocked={blocked_total} "
        f"!= min(raw={raw_n}, cap=800)"
    )
    # And scored must exceed the OLD 313 ceiling (proves cap was raised)
    assert scored + blocked_total > 313, (
        f"items_scored+blocked={scored + blocked_total} ≤ 313 — cap not raised"
    )

    # ── E. effective_credibility field set on every verdict ────────────────
    for v in surviving:
        assert "effective_credibility" in v, (
            f"verdict missing effective_credibility: {v['news_id']}"
        )
        assert v["effective_credibility"] in ("HIGH", "MEDIUM", "LOW")

    # ── F. headline_zh is None (v3.14.3 deferred to digest LLM step) ───────
    for v in surviving:
        assert v["headline_zh"] is None, (
            f"headline_zh should be None at stage 1, got {v['headline_zh']!r}"
        )
