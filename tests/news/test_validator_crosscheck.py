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


DATE = "2026-08-16"


def _store_record(event_id: str, recorded_at: str, date: str = DATE) -> dict:
    """One append-only store line, shaped so load_events accepts it."""
    return {
        "effective_date": date, "event_id": event_id, "event_type": "DIGEST",
        "origin": "digest_finalizer", "payload": {}, "position": 0,
        "record_id": f"nev_{event_id}", "recorded_at": recorded_at,
        "schema_version": 1,
    }


def _second_run_pair(tmp_path, *, store_records, triage_ts="2026-08-16T22:10:53.356302"):
    """The 2026-08-16 shape: run 2's triage renumbered run 1's deep away.

    Stage 1 advanced n0060 only; the projection finalize writes also carries
    n0087 from the 14:39 run, whose id this run's raw fetch reassigned to a
    different article entirely.
    """
    triage = {
        "timestamp": triage_ts,
        "shallow_verdicts": [{"news_id": f"n{i:04d}"} for i in range(50)],
        "stage2_items": [{"news_id": "n0060"}],
    }
    digest = {
        "stage1_count": 50, "stage2_count": 2,
        "verdicts": [
            {"news_id": "n0060", "depth": "deep", "event_id": "news_run2aaaa"},
            {"news_id": "n0087", "depth": "deep", "event_id": "news_run1aaaa"},
        ],
    }
    digest_path = _write_pair(tmp_path, DATE, triage, digest)
    if store_records is not None:
        (tmp_path / "news_events.jsonl").write_text(
            "\n".join(json.dumps(r) for r in store_records) + "\n", encoding="utf-8"
        )
    return digest, digest_path


class TestSecondRunCarryOver:
    """A date can hold more than one DIGEST run; Stage 1 is not append-only."""

    def test_deep_from_earlier_run_is_allowed(self, tmp_path):
        digest, digest_path = _second_run_pair(
            tmp_path,
            store_records=[
                _store_record("news_run1aaaa", "2026-08-16 14:39"),
                _store_record("news_run2aaaa", "2026-08-16 22:16"),
            ],
        )
        assert _cross_check_files(digest, str(digest_path)) == []

    def test_event_recorded_after_stage1_does_not_excuse_it(self, tmp_path):
        # Same store entry, but written *after* this run's triage — that is
        # this run's own output, not a carry-over, so it cannot vouch.
        digest, digest_path = _second_run_pair(
            tmp_path,
            store_records=[_store_record("news_run1aaaa", "2026-08-16 22:16")],
        )
        errors = _cross_check_files(digest, str(digest_path))
        assert any("n0087" in e for e in errors), errors

    def test_hand_added_verdict_still_fails_with_a_store_present(self, tmp_path):
        # The laziness pattern the cross-check exists for: an id with no store
        # record at all. An unrelated earlier event must not launder it.
        digest, digest_path = _second_run_pair(
            tmp_path,
            store_records=[_store_record("news_unrelated1", "2026-08-16 14:39")],
        )
        errors = _cross_check_files(digest, str(digest_path))
        assert any("n0087" in e for e in errors), errors

    def test_earlier_event_under_another_date_does_not_vouch(self, tmp_path):
        digest, digest_path = _second_run_pair(
            tmp_path,
            store_records=[
                _store_record("news_run1aaaa", "2026-08-15 14:39", date="2026-08-15"),
            ],
        )
        errors = _cross_check_files(digest, str(digest_path))
        assert any("n0087" in e for e in errors), errors

    def test_no_store_file_stays_strict(self, tmp_path):
        digest, digest_path = _second_run_pair(tmp_path, store_records=None)
        errors = _cross_check_files(digest, str(digest_path))
        assert any("n0087" in e for e in errors), errors
        assert any("cannot confirm an earlier run" in e for e in errors), errors

    def test_triage_without_timestamp_stays_strict(self, tmp_path):
        digest, digest_path = _second_run_pair(
            tmp_path,
            store_records=[_store_record("news_run1aaaa", "2026-08-16 14:39")],
            triage_ts="",
        )
        errors = _cross_check_files(digest, str(digest_path))
        assert any("n0087" in e for e in errors), errors

    def test_only_the_orphan_is_reported(self, tmp_path):
        # n0087 is a genuine carry-over; n0999 is not in the store at all.
        triage = {
            "timestamp": "2026-08-16T22:10:53.356302",
            "shallow_verdicts": [{"news_id": f"n{i:04d}"} for i in range(50)],
            "stage2_items": [{"news_id": "n0060"}],
        }
        digest = {
            "stage1_count": 50, "stage2_count": 3,
            "verdicts": [
                {"news_id": "n0060", "depth": "deep", "event_id": "news_run2aaaa"},
                {"news_id": "n0087", "depth": "deep", "event_id": "news_run1aaaa"},
                {"news_id": "n0999", "depth": "deep", "event_id": "news_ghostaaa"},
            ],
        }
        digest_path = _write_pair(tmp_path, DATE, triage, digest)
        (tmp_path / "news_events.jsonl").write_text(
            json.dumps(_store_record("news_run1aaaa", "2026-08-16 14:39")) + "\n",
            encoding="utf-8",
        )
        errors = _cross_check_files(digest, str(digest_path))
        assert any("n0999" in e for e in errors), errors
        assert not any("n0087" in e for e in errors), errors

    def test_flash_events_remain_out_of_scope(self, tmp_path):
        # FLASH/REVIEW deeps were never checked against stage2_items; the new
        # branch must not drag them in.
        triage = {
            "timestamp": "2026-08-16T22:10:53.356302",
            "shallow_verdicts": [{"news_id": "n0060"}],
            "stage2_items": [{"news_id": "n0060"}],
        }
        digest = {
            "stage1_count": 1, "stage2_count": 1,
            "verdicts": [
                {"news_id": "n0060", "depth": "deep", "event_id": "news_run2aaaa"},
                {"news_id": "n0500", "depth": "deep", "event_id": "news_flashaaa",
                 "event_type": "FLASH"},
            ],
        }
        digest_path = _write_pair(tmp_path, DATE, triage, digest)
        assert _cross_check_files(digest, str(digest_path)) == []
