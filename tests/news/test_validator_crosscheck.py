"""Unit tests for the v3.14.3 validator cross-check.

`validate_digest_output.py` now reads the sibling triage.json and asserts:
  - digest.stage1_count == len(triage.shallow_verdicts)
  - every deep verdict's news_id appears in triage.stage2_items

Tests bypass the freshness-gate by calling `_cross_check_files` directly with
synthetic dict / path inputs (so we don't have to mock today's date).
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from news.scripts.validate_digest_output import _cross_check_files  # noqa: E402


def _write_pair(tmp_path: Path, date: str, triage: dict, digest: dict):
    """Helper: dump triage + digest to a tmp dir mimicking news_logs/ layout."""
    digest_path = tmp_path / f"{date}_digest.json"
    triage_path = tmp_path / f"{date}_triage.json"
    triage_path.write_text(json.dumps(triage), encoding="utf-8")
    digest_path.write_text(json.dumps(digest), encoding="utf-8")
    return digest_path


class TestCrossCheck:
    def test_consistent_pair_returns_no_errors(self, tmp_path):
        triage = {
            "shallow_verdicts": [{"news_id": f"n{i:04d}"} for i in range(50)],
            "stage2_items":     [{"news_id": f"n{i:04d}"} for i in range(5)],
            "blocked_counts":   {"law_firm_solicitation": 2},
            "template_dedup_dropped": 1,
        }
        digest = {
            "stage1_count": 50,
            "stage2_count": 5,
            "verdicts": [
                {"news_id": f"n{i:04d}", "depth": "deep"} for i in range(5)
            ] + [
                {"news_id": f"n{i:04d}", "depth": "shallow"} for i in range(5, 15)
            ],
        }
        digest_path = _write_pair(tmp_path, "2026-05-20", triage, digest)
        errors = _cross_check_files(digest, str(digest_path))
        assert errors == [], f"unexpected errors: {errors}"

    def test_stage1_count_mismatch_is_flagged(self, tmp_path):
        triage = {
            "shallow_verdicts": [{"news_id": f"n{i:04d}"} for i in range(50)],
            "stage2_items":     [{"news_id": "n0001"}],
        }
        digest = {
            "stage1_count": 30,   # mismatch with triage shallow=50
            "stage2_count": 1,
            "verdicts": [{"news_id": "n0001", "depth": "deep"}],
        }
        digest_path = _write_pair(tmp_path, "2026-05-20", triage, digest)
        errors = _cross_check_files(digest, str(digest_path))
        assert any("stage1_count mismatch" in e for e in errors), errors

    def test_deep_verdict_not_in_triage_is_flagged(self, tmp_path):
        triage = {
            "shallow_verdicts": [{"news_id": "n0001"}],
            "stage2_items":     [{"news_id": "n0001"}],
        }
        digest = {
            "stage1_count": 1,
            "stage2_count": 1,
            "verdicts": [
                {"news_id": "n0999", "depth": "deep"},  # never advanced
            ],
        }
        digest_path = _write_pair(tmp_path, "2026-05-20", triage, digest)
        errors = _cross_check_files(digest, str(digest_path))
        assert any("not in triage.stage2_items" in e for e in errors), errors
        assert any("n0999" in e for e in errors), errors

    def test_missing_triage_loose_mode_is_tolerated(self, tmp_path, monkeypatch):
        # No triage.json next to digest, NEWS_RUN_START_MS not set → soft skip.
        monkeypatch.delenv("NEWS_RUN_START_MS", raising=False)
        digest = {"stage1_count": 5, "stage2_count": 1, "verdicts": []}
        digest_path = tmp_path / "2026-05-20_digest.json"
        digest_path.write_text(json.dumps(digest), encoding="utf-8")
        errors = _cross_check_files(digest, str(digest_path))
        assert errors == []

    def test_missing_triage_strict_mode_hard_fails(self, tmp_path, monkeypatch):
        # NEWS_RUN_START_MS set → today's run; missing triage = hard fail.
        monkeypatch.setenv("NEWS_RUN_START_MS", "1700000000000")
        digest = {"stage1_count": 5, "stage2_count": 1, "verdicts": []}
        digest_path = tmp_path / "2026-05-20_digest.json"
        digest_path.write_text(json.dumps(digest), encoding="utf-8")
        errors = _cross_check_files(digest, str(digest_path))
        assert errors, "strict mode should hard-fail when triage.json missing"
        assert any("triage.json missing" in e for e in errors)

    def test_unreadable_triage_returns_clear_error(self, tmp_path):
        digest = {"stage1_count": 5, "stage2_count": 1, "verdicts": []}
        triage_path = tmp_path / "2026-05-20_triage.json"
        triage_path.write_text("{ not json", encoding="utf-8")
        digest_path = tmp_path / "2026-05-20_digest.json"
        digest_path.write_text(json.dumps(digest), encoding="utf-8")
        errors = _cross_check_files(digest, str(digest_path))
        assert any("unreadable" in e for e in errors), errors
