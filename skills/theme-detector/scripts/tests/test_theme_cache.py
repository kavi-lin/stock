"""Exercise cache freshness through the actual Theme Detector CLI entry."""

import json
import os
import sys
import time

import pytest
import theme_detector as detector
import finviz_performance_client as client


def write_cache(directory, name, payload, age=0):
    path = directory / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    stamp = time.time() - age
    os.utime(path, (stamp, stamp))
    return path


PRIMARY = {"report_type": "theme_detector", "themes": {"all": []}}


def test_latest_primary_ignores_newer_sidecar_and_corrupt_report(tmp_path):
    primary = write_cache(tmp_path, "theme_detector_2026-10-03_170000.json", PRIMARY, age=300)
    write_cache(tmp_path, "theme_detector_2026-10-03_170001.narrative.json", {"confirmations": []})
    corrupt = tmp_path / "theme_detector_2026-10-03_170002.json"
    corrupt.write_text('{"themes":', encoding="utf-8")
    path, age = detector._find_latest_cache(str(tmp_path))
    assert path == str(primary)
    assert 299 <= age < 310


def test_main_reuses_valid_cache_from_requested_output_dir(tmp_path, monkeypatch, capsys):
    primary = write_cache(tmp_path, "theme_detector_2026-10-03_170000.json", PRIMARY)
    monkeypatch.setattr(sys, "argv", ["theme_detector.py", "--output-dir", str(tmp_path), "--skip-if-fresh", "10800"])
    def must_not_fetch(**kwargs):
        pytest.fail("fresh requested cache must skip the network")
    monkeypatch.setattr(client, "get_industry_performance", must_not_fetch)
    with pytest.raises(SystemExit) as result:
        detector.main()
    assert result.value.code == 0
    assert str(primary) in capsys.readouterr().err


@pytest.mark.parametrize("payload, name, age", [
    ({"confirmations": []}, "theme_detector_2026-10-03_170000.narrative.json", 0),
    ({"report_type": "theme_detector", "themes": {}}, "theme_detector_2026-10-03_170000.json", 0),
    (PRIMARY, "theme_detector_2026-10-03_170000.json", 20000),
])
def test_main_rebuilds_unusable_cache_and_reports_upstream_failure(tmp_path, monkeypatch, capsys, payload, name, age):
    write_cache(tmp_path, name, payload, age)
    monkeypatch.setattr(sys, "argv", ["theme_detector.py", "--output-dir", str(tmp_path), "--skip-if-fresh", "10800"])
    calls = []
    def fail(**kwargs):
        calls.append(kwargs)
        raise client.FinvizDataError("FINVIZ Industry HTTP 403; access denied/site verification")
    monkeypatch.setattr(client, "get_industry_performance", fail)
    with pytest.raises(SystemExit) as result:
        detector.main()
    assert result.value.code == 1
    assert calls == [{"strict": True}]
    assert "ERROR: FINVIZ Industry HTTP 403" in capsys.readouterr().err
