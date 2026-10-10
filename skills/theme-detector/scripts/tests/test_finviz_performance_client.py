"""FINVIZ request, source-data validation, and winsorization regressions."""

import pandas as pd
import pytest
import requests
import finviz_performance_client as client

from finviz_performance_client import (
    HARD_CAPS,
    _apply_hard_caps,
    _parse_perf_value,
    cap_outlier_performances,
)


class TestParsePerfValue:
    @pytest.mark.parametrize("value", [float("nan"), float("inf"), "NaN", "inf%", "-inf", True])
    def test_nonfinite_and_boolean_values_are_missing(self, value):
        assert _parse_perf_value(value) is None

    def test_sub_one_percent_strings_convert_to_decimal(self):
        assert _parse_perf_value("0.54%") == 0.0054
        assert _parse_perf_value("-0.49%") == -0.0049

    def test_multi_percent_string_converts_to_decimal(self):
        assert _parse_perf_value("12.34%") == 0.1234


@pytest.mark.parametrize("group", ["Industry", "Sector"])
def test_public_entry_normalizes_header_before_real_library_parser(monkeypatch, group):
    """Removing the fix must reproduce the 403 at the actual HTTP boundary."""
    old_ua = "Mozilla/5.0 (Macintosh)             AppleWebKit/537.36 Chrome/81.0"
    original_headers = {"User-Agent": old_ua, "Accept-Language": "en-US"}
    monkeypatch.setattr(client.fvutil, "headers", original_headers)
    columns = ["No.", *client.COLUMN_MAP]
    values = ["1", "Semiconductors", "0.54%", "1%", "2%", "3%", "4%", "5%"]
    html = ("<table class='groups_table'><tr>" + "".join(f"<th>{x}</th>" for x in columns)
            + "</tr><tr>" + "".join(f"<td>{x}</td>" for x in values) + "</tr></table>")
    seen = []

    def get(url, **kwargs):
        seen.append(kwargs)
        response = requests.Response()
        response.url = url
        response.status_code = 403 if "  " in kwargs["headers"]["User-Agent"] else 200
        response._content = html.encode()
        return response

    monkeypatch.setattr(client.fvutil.session, "get", get)
    fetch = client.get_industry_performance if group == "Industry" else client.get_sector_performance
    rows = fetch(strict=True)
    assert rows[0]["perf_1w"] == 0.0054
    assert rows[0]["perf_1m"] == 0.01
    assert seen[0]["params"]["g"] == group.lower()
    assert seen[0]["headers"] == {**original_headers, "User-Agent": " ".join(old_ua.split())}
    assert original_headers["User-Agent"] == old_ua


@pytest.mark.parametrize("fault", ["missing_column", "missing_value", "duplicate", "unnamed", "empty"])
def test_unusable_table_fails_before_scoring(monkeypatch, fault):
    frame = pd.DataFrame([{column: "Industry A" if column == "Name" else "1%"
                           for column in client.COLUMN_MAP}])
    if fault == "missing_column":
        frame = frame.drop(columns=["Perf Month"])
    elif fault == "missing_value":
        frame.loc[0, "Perf Week"] = "inf%"
    elif fault == "duplicate":
        frame = pd.concat([frame, frame])
    elif fault == "unnamed":
        frame.loc[0, "Name"] = None
    else:
        frame = frame.iloc[:0]
    monkeypatch.setattr(client.fvperf.Performance, "screener_view", lambda *a, **kw: frame)
    with pytest.raises(client.FinvizDataError, match="FINVIZ Industry table"):
        client.get_industry_performance(strict=True)


@pytest.mark.parametrize("error, expected", [
    (requests.HTTPError("HTTP error: 403 Client Error: Forbidden"), "HTTP 403; access denied"),
    (requests.Timeout("sensitive context"), "request timed out"),
    (requests.ConnectionError("sensitive context"), "check DNS/network"),
])
def test_failure_reason_survives_without_leaking_raw_error(monkeypatch, capsys, error, expected):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(client.fvperf.Performance, "screener_view", fail)
    with pytest.raises(client.FinvizDataError, match=expected):
        client.get_industry_performance(strict=True)
    assert client.get_industry_performance() == []
    message = capsys.readouterr().err
    assert expected in message
    assert "sensitive context" not in message


class TestCapOutlierPerformances:
    def test_no_outliers(self):
        """Normal data should pass through unchanged."""
        data = [
            {"name": "A", "perf_1w": 2.0, "perf_1m": 5.0, "perf_3m": 10.0, "perf_6m": 15.0},
            {"name": "B", "perf_1w": -1.0, "perf_1m": 3.0, "perf_3m": 8.0, "perf_6m": 12.0},
        ]
        result = cap_outlier_performances(data)
        assert result[0]["perf_1w"] == 2.0
        assert result[1]["perf_1w"] == -1.0

    def test_outlier_capped(self):
        """Extreme outlier should be capped to z_threshold boundary."""
        data = [
            {"name": f"I{i}", "perf_1w": 2.0, "perf_1m": 5.0, "perf_3m": 10.0, "perf_6m": 15.0}
            for i in range(20)
        ]
        # Add extreme outlier
        data.append(
            {"name": "Outlier", "perf_1w": 99.0, "perf_1m": 5.0, "perf_3m": 10.0, "perf_6m": 15.0}
        )
        result = cap_outlier_performances(data)
        outlier = next(r for r in result if r["name"] == "Outlier")
        # Should be capped and original preserved
        assert outlier["perf_1w"] < 99.0
        assert outlier.get("raw_perf_1w") == 99.0

    def test_raw_fields_preserved(self):
        """When an outlier is capped, raw_perf_* should store original value."""
        data = [
            {"name": f"I{i}", "perf_1w": 2.0, "perf_1m": 5.0, "perf_3m": 10.0, "perf_6m": 15.0}
            for i in range(20)
        ]
        data.append(
            {"name": "Extreme", "perf_1w": -99.0, "perf_1m": 5.0, "perf_3m": 10.0, "perf_6m": 15.0}
        )
        result = cap_outlier_performances(data)
        extreme = next(r for r in result if r["name"] == "Extreme")
        assert "raw_perf_1w" in extreme
        assert extreme["raw_perf_1w"] == -99.0

    def test_none_values_skipped(self):
        """None performance values should not cause errors."""
        data = [
            {"name": "A", "perf_1w": 2.0, "perf_1m": None, "perf_3m": 10.0, "perf_6m": 15.0},
            {"name": "B", "perf_1w": None, "perf_1m": 3.0, "perf_3m": 8.0, "perf_6m": 12.0},
        ]
        result = cap_outlier_performances(data)
        assert result[0]["perf_1m"] is None
        assert result[1]["perf_1w"] is None

    def test_empty_input(self):
        assert cap_outlier_performances([]) == []

    def test_small_dataset_skipped(self):
        """With fewer than 5 entries, z-score winsorization should not apply
        but hard caps still apply."""
        data = [
            {"name": "A", "perf_1w": 99.0, "perf_1m": 5.0, "perf_3m": 10.0, "perf_6m": 15.0},
        ]
        result = cap_outlier_performances(data)
        # Hard cap clips to 30.0 even for small datasets
        assert result[0]["perf_1w"] == HARD_CAPS["perf_1w"]


class TestApplyHardCaps:
    def test_perf_1w_capped_positive(self):
        """perf_1w exceeding +30% should be capped to +30%."""
        data = [{"name": "A", "perf_1w": 87.0}]
        _apply_hard_caps(data)
        assert data[0]["perf_1w"] == 30.0
        assert data[0]["raw_perf_1w"] == 87.0

    def test_perf_1w_capped_negative(self):
        """perf_1w below -30% should be capped to -30%."""
        data = [{"name": "A", "perf_1w": -100.0}]
        _apply_hard_caps(data)
        assert data[0]["perf_1w"] == -30.0
        assert data[0]["raw_perf_1w"] == -100.0

    def test_within_cap_unchanged(self):
        """Values within hard cap range should not be modified."""
        data = [{"name": "A", "perf_1w": 15.0, "perf_1m": -40.0, "perf_3m": 50.0}]
        _apply_hard_caps(data)
        assert data[0]["perf_1w"] == 15.0
        assert data[0]["perf_1m"] == -40.0
        assert data[0]["perf_3m"] == 50.0
        assert "raw_perf_1w" not in data[0]
        assert "raw_perf_1m" not in data[0]
        assert "raw_perf_3m" not in data[0]

    def test_raw_not_overwritten_by_second_stage(self):
        """raw_perf_* set by hard cap should not be overwritten by z-score stage."""
        data = [{"name": f"I{i}", "perf_1w": 5.0} for i in range(20)]
        # Add one that triggers hard cap
        data.append({"name": "Extreme", "perf_1w": 50.0})
        cap_outlier_performances(data)
        extreme = next(r for r in data if r["name"] == "Extreme")
        # raw_perf_1w should store original 50.0 (from hard cap), not 30.0
        assert extreme["raw_perf_1w"] == 50.0

    def test_none_values_skipped(self):
        """None perf values should be skipped without error."""
        data = [{"name": "A", "perf_1w": None, "perf_1m": 70.0}]
        _apply_hard_caps(data)
        assert data[0]["perf_1w"] is None
        assert data[0]["perf_1m"] == 60.0

    def test_all_perf_keys_capped(self):
        """All perf_* keys should be capped at their respective limits."""
        data = [
            {
                "name": "A",
                "perf_1w": 999.0,
                "perf_1m": 999.0,
                "perf_3m": 999.0,
                "perf_6m": 999.0,
                "perf_1y": 999.0,
                "perf_ytd": 999.0,
            }
        ]
        _apply_hard_caps(data)
        for key, cap in HARD_CAPS.items():
            assert data[0][key] == cap
