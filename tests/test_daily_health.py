import importlib.util
import json
import os
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "daily_health", ROOT / "scripts" / "daily_health.py"
)
daily_health = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(daily_health)


def _src(name="sample"):
    return {
        "name": name,
        "glob": "cache/*.json",
        "max_age_hours": 30,
        "kind": "auto",
    }


def _set_local_date(path: Path, date_text: str):
    stamp = datetime.strptime(date_text + " 12:00:00", "%Y-%m-%d %H:%M:%S").timestamp()
    os.utime(path, (stamp, stamp))


def test_run_date_rejects_previous_day(monkeypatch, tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    artifact = cache / "sample.json"
    artifact.write_text(json.dumps({"ok": True}))
    _set_local_date(artifact, "2026-08-05")
    monkeypatch.setattr(daily_health, "ROOT", str(tmp_path))

    result = daily_health.check(_src(), run_date="2026-08-06")

    assert result["status"] == "FAIL"
    assert "not refreshed" in result["reason"]


def test_run_date_allows_intentionally_disabled_source(monkeypatch, tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    artifact = cache / "sample.json"
    artifact.write_text(json.dumps({"ok": True}))
    _set_local_date(artifact, "2026-08-05")
    monkeypatch.setattr(daily_health, "ROOT", str(tmp_path))

    result = daily_health.check(
        _src("optional"), run_date="2026-08-06", allow_stale={"optional"}
    )

    assert result["status"] in {"OK", "WARN"}


def test_corrupt_and_partial_json_fail(monkeypatch, tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    artifact = cache / "sample.json"
    monkeypatch.setattr(daily_health, "ROOT", str(tmp_path))

    artifact.write_text("{")
    assert daily_health.check(_src())["status"] == "FAIL"

    artifact.write_text(json.dumps({"_partial": True}))
    result = daily_health.check(_src())
    assert result["status"] == "FAIL"
    assert "_partial" in result["reason"]

