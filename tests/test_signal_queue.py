"""Tests for the cross-page signal queue.

Deterministic: every test builds its own break-news fixtures in a tmp store and
pins `now`, so nothing depends on what the live log directory happens to hold.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.signal_queue as sq  # noqa: E402
from scripts.break_news import store  # noqa: E402

NOW = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)


# ── Fixtures ─────────────────────────────────────────────────────────
@pytest.fixture
def bn_store(tmp_path, monkeypatch):
    """Point the break-news store at a scratch dir for the duration of a test."""
    d = tmp_path / "break_news_logs"
    d.mkdir()
    monkeypatch.setattr(store, "STORE_DIR", d)
    return d


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    p = tmp_path / "signals" / "queue_state.json"
    monkeypatch.setattr(sq, "STATE_PATH", p)
    return p


def write_item(bn_store, *, news_id=None, hours_ago=1.0, verdict="BULLISH",
               tickers=("FN",), relations=(), materiality=3.5, credibility="HIGH",
               news_type="earnings", headline="Fabrinet beats on Q4 revenue",
               state="closed", cluster_id=None, echo=1, day=None, extra=None):
    when = NOW - timedelta(hours=hours_ago)
    stamp = (day or when).strftime("%Y%m%d")
    news_id = news_id or f"bn_{stamp}_{abs(hash((headline, tuple(tickers)))) % (16 ** 8):08x}"
    payload = {
        "news_id": news_id,
        "state": state,
        "fetched_at": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "headline": headline,
        "headline_zh": None,
        "source": {"name": "Reuters", "credibility": credibility,
                   "url": "https://example.com/x",
                   "published": when.strftime("%Y-%m-%dT%H:%M:%SZ")},
        "triage": {"news_type": news_type, "materiality_score": materiality,
                   "content_genre": "straight_news", "shallow_score": 0.0},
        "cluster": {"cluster_id": cluster_id, "echo_count": echo},
        "summary": {
            "consensus_verdict": verdict,
            "merged_entities": {"tickers": list(tickers), "sectors": ["Technology"],
                                "themes": ["Optics"]},
            "merged_relations": [{"subject": f"ticker:{t}", "predicate": p,
                                  "object": "theme:x"} for t, p in relations],
            "final_take": "take",
            "closed_at": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    }
    payload.update(extra or {})
    (bn_store / f"{news_id}.json").write_text(json.dumps(payload), encoding="utf-8")
    return news_id


def compute(**kw):
    kw.setdefault("now", NOW)
    kw.setdefault("min_score", 0.0)
    return sq.compute_signal_queue(**kw)


# ── Scanning ─────────────────────────────────────────────────────────
def test_window_includes_trailing_day(bn_store, state_file):
    """A debate that closed after UTC midnight still lives under yesterday's
    filename, so the window must reach one day past its nominal edge."""
    edge = NOW - timedelta(days=3, hours=1)
    write_item(bn_store, hours_ago=73, day=edge, headline="Edge Q3 results")
    assert compute(window_days=3)["scanned_files"] >= 1


def test_ignores_files_outside_window(bn_store, state_file):
    write_item(bn_store, hours_ago=24 * 30, day=NOW - timedelta(days=30))
    assert compute(window_days=3)["usable_events"] == 0


def test_unreadable_file_does_not_abort_the_scan(bn_store, state_file):
    write_item(bn_store, headline="Good Q3 results")
    (bn_store / f"bn_{NOW:%Y%m%d}_deadbeef.json").write_text("{not json", encoding="utf-8")
    out = compute(window_days=3)
    assert out["dropped"]["unreadable"] == 1
    assert out["usable_events"] == 1


def test_non_terminal_states_are_skipped(bn_store, state_file):
    write_item(bn_store, state="debating")
    assert compute(window_days=3)["usable_events"] == 0


def test_partial_closed_is_usable(bn_store, state_file):
    write_item(bn_store, state="partial_closed")
    assert compute(window_days=3)["usable_events"] == 1


def test_materiality_read_from_triage_not_top_level(bn_store, state_file):
    """The score lives at `triage.materiality_score`; reading a top-level key
    would silently treat every item as materiality 0 and drop the lot."""
    write_item(bn_store, materiality=1.0)
    assert compute(window_days=3)["dropped"]["low_materiality"] == 1


def test_neutral_and_split_never_enter(bn_store, state_file):
    write_item(bn_store, verdict="NEUTRAL", headline="A Q1 results")
    write_item(bn_store, verdict="SPLIT", headline="B Q1 results")
    out = compute(window_days=3)
    assert out["dropped"]["neutral_split"] == 2
    assert out["counts"]["earnings"] == 0


# ── Dedupe ───────────────────────────────────────────────────────────
def test_cluster_dedupe_collapses_syndication(bn_store, state_file):
    for i in range(4):
        write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_0000000{i}",
                   cluster_id="cl_1", headline=f"Fabrinet Q4 results {i}")
    c = compute(window_days=3)["lanes"]["earnings"][0]
    assert c["hits"] == 1 and c["raw_mentions"] == 4


def test_distinct_clusters_count_separately(bn_store, state_file):
    write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_0000000a", cluster_id="cl_1")
    write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_0000000b", cluster_id="cl_2")
    assert compute(window_days=3)["lanes"]["earnings"][0]["hits"] == 2


def test_junk_tickers_are_rejected(bn_store, state_file):
    write_item(bn_store, tickers=("FN", "N/A", "toolongsymbol"))
    out = compute(window_days=3)
    assert out["dropped"]["bad_ticker"] == 2
    assert [c["ticker"] for c in out["lanes"]["earnings"]] == ["FN"]


def test_broad_event_is_dropped_instead_of_truncated(bn_store, state_file):
    """Source order is not a relevance ranking; keeping the first eight names
    would turn a broad market recap into eight arbitrary ticker signals."""
    tickers = tuple(f"T{i}" for i in range(sq.MAX_TICKERS_PER_EVENT + 1))
    write_item(
        bn_store,
        news_type="macro_data",
        materiality=4.0,
        headline="Market recap names every major mover",
        tickers=tickers,
        relations=tuple((ticker, "BENEFITS_FROM") for ticker in tickers),
    )
    out = compute(window_days=3)
    assert out["dropped"]["too_many_tickers"] == 1
    assert out["usable_events"] == 0
    assert all(not candidates for candidates in out["lanes"].values())


# ── Direction ────────────────────────────────────────────────────────
def test_single_ticker_inherits_event_verdict(bn_store, state_file):
    write_item(bn_store, verdict="BEARISH", tickers=("FN",))
    assert compute(window_days=3)["lanes"]["earnings"][0]["direction"] == "bearish"


def test_oil_spike_splits_energy_from_airlines(bn_store, state_file):
    """The case the whole per-mention rule exists for.

    One BULLISH debate names both oil majors and airlines. Propagating the event
    verdict to every ticker would mark DAL/UAL as buys off a story that says
    they eat the cost — measured at 24% of multi-ticker mentions in real logs.
    """
    write_item(
        bn_store, verdict="BULLISH", news_type="geopolitical", materiality=4.0,
        headline="Brent rises to $91 as Iran escalates",
        tickers=("XOM", "CVX", "DAL", "UAL"),
        relations=(("XOM", "BENEFITS_FROM"), ("CVX", "BENEFITS_FROM"),
                   ("DAL", "HEADWIND_FROM"), ("UAL", "HEADWIND_FROM")))
    got = {c["ticker"]: c["direction"] for c in compute(window_days=3)["lanes"]["momentum"]}
    assert got == {"XOM": "bullish", "CVX": "bullish",
                   "DAL": "bearish", "UAL": "bearish"}


def test_multi_ticker_without_direction_is_dropped_not_guessed(bn_store, state_file):
    write_item(bn_store, verdict="BULLISH", materiality=4.0,
               tickers=("XOM", "DAL"), relations=(("XOM", "BENEFITS_FROM"),))
    out = compute(window_days=3)
    assert out["dropped"]["ambiguous_ticker_direction"] == 1
    assert all(c["ticker"] != "DAL" for lane in out["lanes"].values() for c in lane)


def test_dropping_a_mention_keeps_the_rest_of_the_event(bn_store, state_file):
    """Gate per mention, not per event: requiring full coverage would discard
    68% of multi-ticker events instead of 29% of mentions."""
    write_item(bn_store, verdict="BULLISH", materiality=4.0,
               tickers=("XOM", "DAL"), relations=(("XOM", "BENEFITS_FROM"),))
    tickers = {c["ticker"] for lane in compute(window_days=3)["lanes"].values() for c in lane}
    assert "XOM" in tickers


# ── Scoring ──────────────────────────────────────────────────────────
def test_agreement_is_one_when_debates_concur(bn_store, state_file):
    for i in range(3):
        write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_0000010{i}",
                   cluster_id=f"cl_{i}", verdict="BULLISH")
    c = compute(window_days=3)["lanes"]["earnings"][0]
    assert c["agreement"] == 1.0 and c["conflict"] is False


def test_conflicting_debates_lower_the_score_and_flag(bn_store, state_file):
    for i, verdict in enumerate(["BULLISH", "BEARISH", "BULLISH", "BEARISH"]):
        write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_0000020{i}",
                   cluster_id=f"cl_{i}", verdict=verdict)
    c = compute(window_days=3)["lanes"]["earnings"][0]
    assert c["agreement"] < 0.5 and c["conflict"] is True


def test_agreement_stays_in_unit_range(bn_store, state_file):
    for i, verdict in enumerate(["BULLISH", "BEARISH", "BULLISH"]):
        write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_0000030{i}",
                   cluster_id=f"cl_{i}", verdict=verdict)
    for lane in compute(window_days=3)["lanes"].values():
        for c in lane:
            assert 0.0 <= c["agreement"] <= 1.0


def test_future_timestamp_does_not_amplify_score(bn_store, state_file):
    """A clock-skewed `published` in the future gives a negative age; without a
    clamp the decay term becomes >1 and inflates the item above everything."""
    write_item(bn_store, hours_ago=-6.0)
    c = compute(window_days=3)["lanes"]["earnings"][0]
    assert c["score"] <= 100.0
    write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_000000ff", hours_ago=0.0,
               cluster_id="cl_now", headline="Other Q4 results", tickers=("ZZ",))
    fresh = next(c for c in compute(window_days=3)["lanes"]["earnings"]
                 if c["ticker"] == "ZZ")
    assert compute(window_days=3)["lanes"]["earnings"][0]["score"] <= fresh["score"] + 1e-6


def test_recency_decay_favours_the_newer_debate(bn_store, state_file):
    write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_000000a1", tickers=("AAA",),
               hours_ago=1, headline="AAA Q4 results")
    write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_000000b1", tickers=("BBB",),
               hours_ago=48, headline="BBB Q4 results")
    scores = {c["ticker"]: c["score"] for c in compute(window_days=3)["lanes"]["earnings"]}
    assert scores["AAA"] > scores["BBB"]


def test_lone_low_materiality_item_is_suppressed(bn_store, state_file):
    write_item(bn_store, materiality=2.5, credibility="MEDIUM")
    out = sq.compute_signal_queue(window_days=3, now=NOW)
    assert out["counts"]["earnings"] == 0
    assert out["dropped"]["low_score"] == 1


# ── Lane routing ─────────────────────────────────────────────────────
def test_earnings_news_type_routes_to_earnings(bn_store, state_file):
    write_item(bn_store, news_type="earnings", headline="Anything at all")
    assert compute(window_days=3)["counts"]["earnings"] == 1


def test_market_recap_naming_many_tickers_is_not_an_earnings_item(bn_store, state_file):
    """The headline regex is a backstop for mislabelled single-name stories. A
    market recap matches the same words while being about none of the names."""
    write_item(bn_store, news_type="macro_data", materiality=4.0,
               headline="Stock Market Today: Investors await earnings",
               tickers=("AAA", "BBB", "CCC"),
               relations=(("AAA", "BENEFITS_FROM"), ("BBB", "BENEFITS_FROM"),
                          ("CCC", "BENEFITS_FROM")))
    assert compute(window_days=3)["counts"]["earnings"] == 0


def test_headline_backstop_catches_mislabelled_single_name(bn_store, state_file):
    write_item(bn_store, news_type="corporate", tickers=("BIDU",),
               headline="Baidu Q2 results preview: what to watch")
    assert compute(window_days=3)["counts"]["earnings"] == 1


def test_earnings_items_stay_out_of_the_invest_lane(bn_store, state_file):
    """An invest run is a 60-minute LLM job; spending one on something the free
    earnings skill already covers is the expensive kind of duplicate."""
    write_item(bn_store, news_type="earnings", tickers=("FN",))
    out = compute(window_days=3)
    assert out["counts"]["earnings"] == 1 and out["counts"]["invest"] == 0


def test_corporate_single_name_routes_to_invest(bn_store, state_file):
    write_item(bn_store, news_type="corporate", tickers=("LHX",),
               headline="L3Harris ousts CEO over conduct")
    assert compute(window_days=3)["counts"]["invest"] == 1


# ── Revision ─────────────────────────────────────────────────────────
def test_revision_is_stable_for_the_same_evidence(bn_store, state_file):
    write_item(bn_store, cluster_id="cl_1")
    first = compute(window_days=3)["lanes"]["earnings"][0]["revision"]
    second = compute(window_days=3)["lanes"]["earnings"][0]["revision"]
    assert first == second


def test_revision_changes_when_evidence_arrives(bn_store, state_file):
    write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_000000c1", cluster_id="cl_1")
    before = compute(window_days=3)["lanes"]["earnings"][0]["revision"]
    write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_000000c2", cluster_id="cl_2")
    assert compute(window_days=3)["lanes"]["earnings"][0]["revision"] != before


# ── Delivery ledger ──────────────────────────────────────────────────
def test_dismiss_hides_the_candidate(bn_store, state_file):
    write_item(bn_store)
    c = compute(window_days=3)["lanes"]["earnings"][0]
    sq.record_action(c["candidate_id"], c["revision"], "dismiss", candidate=c, now=NOW)
    assert compute(window_days=3)["counts"]["earnings"] == 0
    assert compute(window_days=3, include_dismissed=True)["counts"]["earnings"] == 1


def test_dismiss_survives_an_unchanged_recompute(bn_store, state_file):
    write_item(bn_store)
    c = compute(window_days=3)["lanes"]["earnings"][0]
    sq.record_action(c["candidate_id"], c["revision"], "dismiss", candidate=c, now=NOW)
    assert compute(window_days=3)["counts"]["earnings"] == 0


def test_dismiss_rearms_on_a_material_new_cluster(bn_store, state_file):
    """A dismissal answers "not interesting given this". Letting it silence the
    ticker forever means the next real catalyst never surfaces."""
    write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_000000d1", cluster_id="cl_1")
    c = compute(window_days=3)["lanes"]["earnings"][0]
    sq.record_action(c["candidate_id"], c["revision"], "dismiss", candidate=c, now=NOW)
    assert compute(window_days=3)["counts"]["earnings"] == 0

    write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_000000d2", cluster_id="cl_2",
               materiality=4.5, hours_ago=0.5)
    assert compute(window_days=3)["counts"]["earnings"] == 1


def test_accept_then_consumed_then_shows_report(bn_store, state_file):
    write_item(bn_store)
    c = compute(window_days=3)["lanes"]["earnings"][0]
    sq.record_action(c["candidate_id"], c["revision"], "accept",
                     candidate=c, job_id="pq_1", now=NOW)
    assert compute(window_days=3)["lanes"]["earnings"][0]["delivery"]["status"] == "queued"

    sq.record_delivery(c["candidate_id"], c["revision"], status=sq.STATUS_CONSUMED,
                       refs=c["source_refs"], protocol="earnings", ticker="FN",
                       report_path="reports/2026-08-18_FN_earnings.md", now=NOW)
    delivery = compute(window_days=3)["lanes"]["earnings"][0]["delivery"]
    assert delivery["status"] == "consumed"
    assert delivery["report_path"] == "reports/2026-08-18_FN_earnings.md"


def test_failed_run_reopens_the_button(bn_store, state_file):
    """A failed or cancelled run must not leave the card stuck on `queued` with
    no way to retry."""
    write_item(bn_store)
    c = compute(window_days=3)["lanes"]["earnings"][0]
    sq.record_action(c["candidate_id"], c["revision"], "accept", candidate=c, now=NOW)
    sq.record_delivery(c["candidate_id"], c["revision"], status=sq.STATUS_FAILED,
                       protocol="earnings", ticker="FN", error="boom", now=NOW)
    delivery = compute(window_days=3)["lanes"]["earnings"][0]["delivery"]
    assert delivery["status"] == "pending"
    assert delivery["previous_status"] == "failed"
    assert delivery["error"] == "boom"


def test_consumed_revision_reopens_when_new_evidence_arrives(bn_store, state_file):
    write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_000000e8", cluster_id="cl_old")
    c = compute(window_days=3)["lanes"]["earnings"][0]
    sq.record_action(c["candidate_id"], c["revision"], "accept", candidate=c, now=NOW)
    sq.record_delivery(c["candidate_id"], c["revision"], status=sq.STATUS_CONSUMED,
                       refs=c["source_refs"], protocol="earnings", ticker="FN",
                       report_path="reports/old.md", now=NOW)
    assert compute(window_days=3)["lanes"]["earnings"][0]["delivery"]["status"] == "consumed"

    write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_000000e9", cluster_id="cl_new",
               hours_ago=0.5)
    delivery = compute(window_days=3)["lanes"]["earnings"][0]["delivery"]
    assert delivery["status"] == "pending"
    assert delivery["previous_status"] == "consumed"
    assert delivery["revision"] != c["revision"]


def test_clear_action_is_scoped_to_its_revision(bn_store, state_file):
    write_item(bn_store)
    c = compute(window_days=3)["lanes"]["earnings"][0]
    sq.record_action(c["candidate_id"], c["revision"], "dismiss", candidate=c, now=NOW)
    assert sq.clear_action(c["candidate_id"], "not-the-revision") is False
    assert sq.clear_action(c["candidate_id"], c["revision"]) is True
    assert compute(window_days=3)["counts"]["earnings"] == 1


def test_corrupt_ledger_degrades_to_empty(bn_store, state_file):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    write_item(bn_store)
    state_file.write_text("{ broken", encoding="utf-8")
    assert sq.load_state()["entries"] == {}
    assert compute(window_days=3)["counts"]["earnings"] == 1


def test_ledger_prunes_stale_and_overflowing_entries(bn_store, state_file):
    old = (NOW - timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries = {f"earnings:T{i}": {"status": "dismissed", "at": old} for i in range(3)}
    entries["earnings:FRESH"] = {"status": "dismissed",
                                 "at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ")}
    entries["not a candidate id"] = {"status": "dismissed", "at": old}
    sq._save_state({"entries": entries}, NOW)
    kept = sq.load_state()["entries"]
    assert set(kept) == {"earnings:FRESH"}


def test_ledger_write_is_atomic_and_leaves_no_tmp(bn_store, state_file):
    sq._save_state({"entries": {}}, NOW)
    assert state_file.exists()
    assert not list(state_file.parent.glob("*.tmp"))


# ── Input validation ─────────────────────────────────────────────────
@pytest.mark.parametrize("bad", [
    "earnings:../../etc/passwd", "../earnings:FN", "bogus_lane:FN",
    "earnings:", "earnings:toolong", "", None, 42,
])
def test_bad_candidate_ids_are_rejected(bad):
    assert sq.parse_candidate_id(bad) is None


@pytest.mark.parametrize("bad", [
    "../../etc/passwd", "bn_2026081_short", "bn_20260817_ZZZZZZZZ",
    "bn_20260817_fff6adeb/../x", "", None,
])
def test_bad_artifact_ids_are_rejected(bad):
    assert sq.valid_artifact_id(sq.SOURCE_BREAK_NEWS, bad) is False


def test_good_artifact_id_is_accepted():
    assert sq.valid_artifact_id(sq.SOURCE_BREAK_NEWS, "bn_20260817_fff6adeb") is True


def test_record_action_rejects_bad_input():
    for args in [("bogus:FN", "r", "accept"), ("earnings:FN", "r", "explode"),
                 ("earnings:FN", "", "accept")]:
        with pytest.raises(ValueError):
            sq.record_action(*args)


def test_backlink_ignores_refs_it_cannot_validate(bn_store, state_file, monkeypatch):
    """Refs make a round trip through an HTTP body before becoming a path."""
    seen = []
    monkeypatch.setattr(store, "add_consumed_by",
                        lambda nid, rec: seen.append(nid) or True)
    sq._write_backlinks(
        [{"source": "break_news", "artifact_id": "../../etc/passwd"},
         {"source": "evil", "artifact_id": "bn_20260817_fff6adeb"},
         {"source": "break_news", "artifact_id": "bn_20260817_fff6adeb"},
         "not-a-dict"],
        protocol="earnings", lane="earnings", ticker="FN",
        report_path=None, now=NOW)
    assert seen == ["bn_20260817_fff6adeb"]


def test_window_days_is_clamped():
    assert sq._clamp_days(99) == sq.MAX_WINDOW_DAYS
    assert sq._clamp_days(0) == 1
    assert sq._clamp_days("junk") == sq.DEFAULT_WINDOW_DAYS


def test_normalize_ticker_strips_node_prefix():
    assert sq.normalize_ticker("ticker:NVDA") == "NVDA"
    assert sq.normalize_ticker("nvda") == "NVDA"
    assert sq.normalize_ticker("N/A") is None


# ── consumed_by writeback ────────────────────────────────────────────
def test_add_consumed_by_refuses_a_still_debating_item(bn_store):
    """`set_state`/`set_summary` rewrite the whole dict without the per-id lock,
    so a writeback racing a closing debate could lose the key. An item mid-debate
    cannot have been consumed anyway, which closes the only reachable window."""
    nid = write_item(bn_store, state="debating")
    assert store.add_consumed_by(nid, {"protocol": "earnings", "ticker": "FN"}) is False


def test_add_consumed_by_dedupes_on_protocol_and_ticker(bn_store):
    nid = write_item(bn_store)
    store.add_consumed_by(nid, {"protocol": "earnings", "ticker": "FN", "at": "t1"})
    store.add_consumed_by(nid, {"protocol": "earnings", "ticker": "FN", "at": "t2"})
    store.add_consumed_by(nid, {"protocol": "invest", "ticker": "FN", "at": "t3"})
    records = store.load_item(nid)["consumed_by"]
    assert [r["at"] for r in records] == ["t2", "t3"]


def test_add_consumed_by_preserves_the_rest_of_the_item(bn_store):
    nid = write_item(bn_store)
    store.add_consumed_by(nid, {"protocol": "earnings", "ticker": "FN"})
    item = store.load_item(nid)
    assert item["summary"]["consensus_verdict"] == "BULLISH"
    assert item["state"] == "closed"


def test_consumed_by_surfaces_on_the_candidate(bn_store, state_file):
    nid = write_item(bn_store)
    store.add_consumed_by(nid, {"protocol": "earnings", "ticker": "FN",
                                "report_path": "reports/x.md"})
    c = compute(window_days=3)["lanes"]["earnings"][0]
    assert c["consumed_by"][0]["report_path"] == "reports/x.md"


# ── Earnings eligibility ─────────────────────────────────────────────
@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    d = tmp_path / "earnings_cache"
    d.mkdir()
    monkeypatch.setattr(sq, "EARNINGS_CACHE_DIR", d)
    return d


def write_cache(cache_dir, ticker, as_of, last_earnings, report_path=None):
    (cache_dir / f"{ticker}_{as_of}.json").write_text(json.dumps({
        "as_of_date": as_of, "last_earnings_date": last_earnings,
        "report_path": report_path, "composite_score": 70,
    }), encoding="utf-8")


def test_no_cache_state(cache_dir):
    assert sq.earnings_eligibility("FN", calendar={}, now=NOW)["state"] == "no_cache"


def test_pre_earnings_window_beats_everything(cache_dir):
    """The quarter a full run would analyse is about to be superseded, so the
    right move is the free preview, not the expensive re-analysis."""
    write_cache(cache_dir, "FN", "2026-05-01", "2026-04-28")
    out = sq.earnings_eligibility("FN", calendar={"FN": ["2026-08-21"]}, now=NOW)
    assert out["state"] == "pre_earnings_window" and out["days_until"] == 3


def test_cache_current_when_latest_quarter_already_analysed(cache_dir):
    write_cache(cache_dir, "FN", "2026-08-10", "2026-08-08")
    out = sq.earnings_eligibility("FN", calendar={"FN": ["2026-08-08"]}, now=NOW)
    assert out["state"] == "cache_current"


def test_cache_stale_after_a_new_quarter_reports(cache_dir):
    """A company announced after we last looked, so our report is a quarter behind."""
    write_cache(cache_dir, "FN", "2026-05-01", "2026-03-31")
    out = sq.earnings_eligibility("FN", calendar={"FN": ["2026-04-28", "2026-08-08"]},
                                  now=NOW)
    assert out["state"] == "cache_stale"


def test_period_end_is_not_compared_against_the_announcement_date(cache_dir):
    """`last_earnings_date` is the fiscal period END (AMZN: 2026-06-30) while the
    calendar carries the ANNOUNCEMENT date (2026-07-31). The announcement always
    postdates the period it reports on, so comparing the two directly would mark
    a freshly-run report stale every single quarter."""
    write_cache(cache_dir, "AMZN", "2026-08-08", "2026-06-30")
    out = sq.earnings_eligibility("AMZN", calendar={"AMZN": ["2026-07-31"]}, now=NOW)
    assert out["state"] == "cache_current"


def test_cache_stale_when_older_than_the_ttl(cache_dir):
    write_cache(cache_dir, "FN", "2026-01-05", "2026-01-03")
    assert sq.earnings_eligibility("FN", calendar={}, now=NOW)["state"] == "cache_stale"


def test_infographic_sibling_is_not_mistaken_for_a_cache(cache_dir):
    (cache_dir / "FN_2026-08-10.infographic.json").write_text("{}", encoding="utf-8")
    assert sq.earnings_eligibility("FN", calendar={}, now=NOW)["state"] == "no_cache"


def test_newest_cache_wins(cache_dir):
    write_cache(cache_dir, "FN", "2026-05-01", "2026-04-28")
    write_cache(cache_dir, "FN", "2026-08-10", "2026-08-08")
    out = sq.earnings_eligibility("FN", calendar={"FN": ["2026-08-08"]}, now=NOW)
    assert out["as_of_date"] == "2026-08-10" and out["state"] == "cache_current"


def test_invalid_ticker_is_unknown(cache_dir):
    assert sq.earnings_eligibility("N/A", calendar={}, now=NOW)["state"] == "unknown"


def test_missing_calendar_degrades_to_cache_only(cache_dir, monkeypatch):
    """No `data.json` must not mean an exception — eligibility just loses the
    pre-earnings branch. This feature adds no network call under any path."""
    monkeypatch.setattr(sq, "_DATA_JSON", Path("/nonexistent/data.json"))
    write_cache(cache_dir, "FN", "2026-08-10", "2026-08-08")
    assert sq.earnings_eligibility("FN", now=NOW)["state"] == "cache_current"


def test_attach_eligibility_only_touches_the_earnings_lane(bn_store, state_file,
                                                           cache_dir, monkeypatch):
    monkeypatch.setattr(sq, "_DATA_JSON", Path("/nonexistent/data.json"))
    write_item(bn_store, news_type="corporate", tickers=("LHX",),
               headline="L3Harris ousts CEO")
    write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_000000f1", news_type="earnings",
               tickers=("FN",))
    out = sq.attach_eligibility(compute(window_days=3), now=NOW)
    assert "eligibility" in out["lanes"]["earnings"][0]
    assert "eligibility" not in out["lanes"]["invest"][0]


# ── Cache signature ──────────────────────────────────────────────────
def test_signature_changes_when_a_debate_lands(bn_store, state_file):
    before = sq.scan_signature(3, now=NOW)
    write_item(bn_store, news_id=f"bn_{NOW:%Y%m%d}_000000aa")
    assert sq.scan_signature(3, now=NOW) != before


def test_signature_changes_when_the_ledger_moves(bn_store, state_file):
    write_item(bn_store)
    before = sq.scan_signature(3, now=NOW)
    sq._save_state({"entries": {}}, NOW)
    assert sq.scan_signature(3, now=NOW) != before


def test_signature_is_stable_when_nothing_changes(bn_store, state_file):
    write_item(bn_store)
    assert sq.scan_signature(3, now=NOW) == sq.scan_signature(3, now=NOW)


# ── Lane protocol whitelist ──────────────────────────────────────────
def test_display_only_lane_cannot_launch_a_protocol():
    """Momentum's screener run is a global singleton that rewrites the whole
    snapshot, so the lane must have no protocol it is allowed to start."""
    assert sq.LANE_PROTOCOLS.get("momentum") is None
    assert sq.LANE_PROTOCOLS["earnings"] == {"earnings", "earnings_preview"}
    assert sq.LANE_PROTOCOLS["invest"] == {"invest"}


# ── Frontend lifecycle / deep-link wiring ───────────────────────────────────
def test_signal_card_uses_delivery_ledger_not_old_backlink():
    src = (ROOT / "Dashboard" / "signal-queue.js").read_text(encoding="utf-8")
    assert "candidate.delivery?.status === 'consumed' || done" not in src
    assert "candidate.delivery?.previous_status === 'failed'" in src


def test_break_news_deep_link_is_not_limited_to_feed_membership():
    src = (ROOT / "Dashboard" / "page-break-news.js").read_text(encoding="utf-8")
    assert "currentItems.some(it => it.news_id === wanted)" not in src
    assert "selectItem(wanted);" in src
    assert "/api/break-news/item/${encodeURIComponent(id)}" in src
