"""Regression tests for the pre-market calendar defects found on 2026-09-17.

The 09-17 brief shipped a raw Python dict into section 10, listed one housing
release three times, put every morning econ print 4 hours late, and cut
"Jobless Claims 4-Week Average (Sep/12)" into "...(Sep/1". Each test below
pins one of those.
"""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, relpath))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except SystemExit:  # bridge.py runs work at import under __main__ only
        pass
    return mod


@pytest.fixture(scope="module")
def bridge():
    return _load("_bridge_under_test", "bridge.py")


@pytest.fixture(scope="module")
def brief():
    return _load("_brief_under_test", "scripts/premarket/morning_brief.py")


# ── UTC → ET ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("utc_hhmm,date_str,expected", [
    ("12:30", "2026-09-17", "08:30 ET"),   # jobless claims, EDT
    ("14:00", "2026-05-05", "10:00 ET"),   # ISM services, EDT
    ("18:00", "2026-04-29", "14:00 ET"),   # FOMC decision, EDT
    ("12:30", "2026-01-15", "07:30 ET"),   # EST side of the DST boundary
])
def test_utc_hhmm_to_et(bridge, utc_hhmm, date_str, expected):
    assert bridge._utc_hhmm_to_et(utc_hhmm, date_str) == expected


@pytest.mark.parametrize("bad", [None, "", "bad", "08:30 ET", "25:00", "12:99"])
def test_utc_hhmm_to_et_rejects_junk(bridge, bad):
    assert bridge._utc_hhmm_to_et(bad, "2026-09-17") is None


# ── title truncation ───────────────────────────────────────────────────────
def test_truncate_keeps_the_date_tag_intact(bridge):
    t = "Jobless Claims 4-Week Average (Sep/12)"
    assert bridge._truncate_title(t) == t          # fits: must not be cut at all


def test_truncate_breaks_on_a_word_boundary(bridge):
    out = bridge._truncate_title("Continuing Jobless Claims Advance Estimate For The Week", 30)
    assert out.endswith("…")
    assert not out.rstrip("…").endswith(" ")
    assert " " not in out[-2:]                      # no dangling partial token


def test_truncate_falls_back_to_hard_cut_without_a_boundary(bridge):
    out = bridge._truncate_title("A" * 80, 20)
    assert out == "A" * 20 + "…"


# ── slug stability / CJK ───────────────────────────────────────────────────
def test_slug_is_stable_across_upstream_truncation(bridge):
    assert (bridge._slugify("Jobless Claims 4-Week Average (Sep/1")
            == bridge._slugify("Jobless Claims 4-Week Average…"))


def test_slug_distinguishes_chinese_titles(bridge):
    a = bridge._slugify("8 月新屋開工與建照")
    b = bridge._slugify("8 月零售銷售")
    assert a != b and a not in ("8", "untitled")


# ── canonical release matching ─────────────────────────────────────────────
@pytest.mark.parametrize("title,expected", [
    ("Housing Starts (Aug)",        ["housing-starts"]),
    ("Fed Interest Rate Decision",  ["fomc-rate-decision"]),
    ("FOMC 利率決議",                ["fomc-rate-decision"]),
    ("ISM Manufacturing PMI (Apr)", ["ism-manufacturing"]),
    ("ISM 製造業 PMI",               ["ism-manufacturing"]),
    ("4 月非農就業 NFP",             ["nonfarm-payrolls"]),
])
def test_canonical_release_matches_both_languages(bridge, title, expected):
    assert bridge._canonical_releases(title) == expected


def test_composite_headline_reports_every_series(bridge):
    # "8月新屋開工與建照" = housing starts AND building permits; collapsing it
    # onto either one alone would delete the other from the calendar.
    assert set(bridge._canonical_releases("8 月新屋開工與建照")) == {
        "housing-starts", "building-permits"}


@pytest.mark.parametrize("title", [
    "Fed Williams Speech",
    "Mag-7 財報週",
    "5月製造業 PMI 初值與費城聯儲",     # S&P Global flash, NOT the ISM print
])
def test_canonical_release_does_not_over_match(bridge, title):
    assert bridge._canonical_releases(title) == []


def test_release_key_ignores_events_with_a_ticker(bridge):
    assert bridge._release_dedupe_key(
        {"date": "2026-09-17", "category": "econ", "title": "Housing Starts (Aug)",
         "tickers": ["TOL"]}) is None


def test_release_key_merges_identical_titles_across_categories(bridge):
    econ = {"date": "2026-05-05", "category": "econ", "tickers": [],
            "title": "ISM Non-Manufacturing Prices (Apr)"}
    macro = dict(econ, category="macro")
    assert bridge._release_dedupe_key(econ) == bridge._release_dedupe_key(macro)


def test_release_merge_prefers_the_record_with_time_and_numbers(bridge):
    rich = {"time": "08:30 ET", "source": "fmp-econ",
            "source_payload": {"previous": 1.2, "estimate": 1.3}}
    poor = {"time": "12:30", "source": "sector-protocol", "source_payload": {}}
    assert bridge._release_merge_score(rich) > bridge._release_merge_score(poor)


# ── archive repair + fresh-wins merge ──────────────────────────────────────
def test_archive_repair_converts_unstamped_fmp_econ_times(bridge):
    archived = [{"date": "2026-09-17", "time": "12:30 ET", "source": "fmp-econ",
                 "source_payload": {}}]
    bridge._repair_archived_times(archived)
    assert archived[0]["time"] == "08:30 ET"


def test_archive_repair_is_idempotent(bridge):
    row = {"date": "2026-09-17", "time": "12:30 ET", "source": "fmp-econ",
           "source_payload": {}}
    bridge._repair_archived_times([row])
    bridge._repair_archived_times([row])          # raw_utc now present → skip
    assert row["time"] == "08:30 ET"


def test_archive_repair_leaves_other_sources_alone(bridge):
    row = {"date": "2026-09-17", "time": "14:00 ET", "source": "sector-protocol",
           "source_payload": {}}
    bridge._repair_archived_times([row])
    assert row["time"] == "14:00 ET"


def test_pinned_merge_keeps_the_fresh_record_but_takes_higher_impact(bridge):
    fresh = {"impact": "med", "title": "Housing Starts (Aug)", "time": "08:30 ET",
             "source": "fmp-econ", "tickers": [], "sectors": [], "is_binary": False}
    stale = {"impact": "high", "title": "Housing Starts (Aug", "time": "12:30 ET",
             "source": "fmp-econ", "tickers": [], "sectors": [], "is_binary": True}
    merged = bridge._merge_two(fresh, stale, pin_primary=True)
    assert merged["title"] == "Housing Starts (Aug)"
    assert merged["time"] == "08:30 ET"
    assert merged["impact"] == "high"      # impact still escalates
    assert merged["is_binary"] is True


# ── morning brief rendering ────────────────────────────────────────────────
def test_binary_risks_never_render_a_dict_repr(brief):
    data = {"binary_risks": [{"event": "FDX 財報（盤後）", "date": "2026-09-17",
                              "days_until": 0, "within_48h": True}],
            "upcoming_events": []}
    out = "\n".join(brief.section_binary(data, "2026-09-17"))
    assert "FDX 財報（盤後）" in out
    assert "{" not in out and "'date'" not in out


def test_binary_risk_suppressed_when_the_event_list_already_has_it(brief):
    data = {"binary_risks": [{"event": "FDX 財報（盤後）", "date": "2026-09-17"}],
            "upcoming_events": [{"date": "2026-09-17", "title": "FDX 財報",
                                 "tickers": ["FDX"], "is_binary": True,
                                 "impact": "high", "category": "earnings"}]}
    out = "\n".join(brief.section_binary(data, "2026-09-17"))
    assert out.count("FDX") == 1


def test_tickerless_binary_risk_is_not_swallowed(brief):
    # A risk with no recoverable ticker must survive even when a ticker-less
    # event shares its date.
    data = {"binary_risks": [{"event": "美中關稅談判最後期限", "date": "2026-09-17"}],
            "upcoming_events": [{"date": "2026-09-17", "title": "Housing Starts (Aug)",
                                 "tickers": [], "impact": "high", "category": "econ"}]}
    out = "\n".join(brief.section_binary(data, "2026-09-17"))
    assert "美中關稅談判最後期限" in out


def test_binary_risk_without_a_label_is_warned_not_printed(brief):
    brief._warnings.clear()
    data = {"binary_risks": [{"date": "2026-09-17", "days_until": 0}],
            "upcoming_events": []}
    out = "\n".join(brief.section_binary(data, "2026-09-17"))
    assert "{" not in out
    assert any("no event/title key" in w for w in brief._warnings)


@pytest.mark.parametrize("event,expected", [
    ({"source_payload": {"raw_event": {"time": "AMC"}}}, "AMC"),   # nested tag
    ({"time": "BMO", "source_payload": {}}, "BMO"),
    ({"source_payload": {"time": "AMC"}}, "AMC"),
    ({"time": None, "source_payload": {"time": ""}}, "—"),         # genuinely absent
])
def test_earnings_time_digs_for_the_session_tag(brief, event, expected):
    assert brief._earnings_time(event) == expected
