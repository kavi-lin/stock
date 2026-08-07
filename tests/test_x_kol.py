#!/usr/bin/env python3
"""Contract tests for the X KOL collector. Fully hermetic — no network, no key.

The budget guard is the load-bearing piece here: X bills per resource RETURNED,
so an optimistic guard cannot protect a fixed pilot budget. These tests pin the
pessimistic pre-flight, the since_id watermark that makes sweeps cheap, and the
"stop, don't crash" behaviour when the ceiling is reached.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.x_kol import budget as budget_mod  # noqa: E402
from scripts.x_kol import collect as collect_mod  # noqa: E402
from scripts.x_kol import pending as pending_mod  # noqa: E402
from scripts.x_kol.client import XClient, cashtags, normalize  # noqa: E402


def _config(total=10.0, reserve=0.0, max_results=10, first_run_max=5, roster=None):
    return {
        "budget": {
            "total_usd": total,
            "price_per_post_read_usd": 0.005,
            "price_per_user_read_usd": 0.010,
            "reserve_usd": reserve,
        },
        "pacing": {"min_interval_sec": 0, "backoff_sec": 0.01,
                   "backoff_max_sec": 0.05, "timeout_sec": 5},
        "collect": {"max_results": max_results, "first_run_max": first_run_max,
                    "shadow_log": "news/x_kol_logs/x_kol_events.jsonl"},
        "roster": roster if roster is not None else [
            {"handle": "aleabitoreddit", "label": "Serenity", "enabled": True},
            {"handle": "REPLACE_ME", "label": "example", "enabled": False},
        ],
    }


class FakeClient:
    """Stands in for XClient; records what the sweep asked for."""

    def __init__(self, pages):
        self.pages = pages          # handle -> (posts, meta)
        self.calls = []

    def resolve_user_id(self, handle):
        return f"id-{handle}"

    def fetch_timeline(self, user_id, *, since_id=None, max_results=None,
                       paginate=True, stop_after=None):
        handle = user_id.replace("id-", "")
        self.calls.append({"handle": handle, "since_id": since_id,
                           "max_results": max_results, "paginate": paginate,
                           "stop_after": stop_after})
        return self.pages.get(handle, ([], {"result_count": 0}))


def _post(pid, text="hello $NVDA", tags=("NVDA",)):
    return {
        "id": pid, "text": text, "created_at": "2026-08-06T14:00:00.000Z", "lang": "en",
        "entities": {"cashtags": [{"tag": t} for t in tags]},
        "public_metrics": {"like_count": 5, "reply_count": 1,
                           "retweet_count": 2, "impression_count": 900},
    }


# ── budget guard ─────────────────────────────────────────────────────────
def test_preflight_refuses_worst_case_over_cap(tmp_path):
    usage = tmp_path / "usage.json"
    cfg = _config(total=0.02)          # $0.02 = 4 post reads
    assert budget_mod.check(cfg, posts=4, usage_path=usage) == pytest.approx(0.02)
    with pytest.raises(budget_mod.BudgetExceeded):
        budget_mod.check(cfg, posts=5, usage_path=usage)
    # the refusal itself is booked, so a wall of refusals is visible in --status
    assert budget_mod.load_ledger(usage)["refusals"] == 1


def test_reserve_is_withheld_from_spendable(tmp_path):
    usage = tmp_path / "usage.json"
    cfg = _config(total=1.0, reserve=0.9)
    assert budget_mod.remaining_usd(cfg, usage_path=usage) == pytest.approx(0.1)
    with pytest.raises(budget_mod.BudgetExceeded):
        budget_mod.check(cfg, posts=21, usage_path=usage)   # $0.105 > $0.10


def test_record_accumulates_and_never_auto_resets(tmp_path):
    usage = tmp_path / "usage.json"
    cfg = _config()
    budget_mod.record(cfg, posts=10, users=1, usage_path=usage)
    budget_mod.record(cfg, posts=10, usage_path=usage)
    ledger = budget_mod.load_ledger(usage)
    assert ledger["post_reads"] == 20 and ledger["user_reads"] == 1
    assert ledger["spent_usd"] == pytest.approx(20 * 0.005 + 0.010)
    assert budget_mod.remaining_usd(cfg, usage_path=usage) == pytest.approx(10.0 - 0.11)


def test_empty_result_costs_nothing(tmp_path):
    """The whole affordability argument: a sweep that finds no new posts is free."""
    usage = tmp_path / "usage.json"
    cfg = _config()
    budget_mod.record(cfg, posts=0, usage_path=usage)
    assert budget_mod.load_ledger(usage)["spent_usd"] == 0.0
    assert budget_mod.load_ledger(usage)["requests"] == 1


# ── sweep behaviour ──────────────────────────────────────────────────────
def test_first_run_is_capped_then_switches_to_since_id(tmp_path):
    cfg = _config(first_run_max=5, max_results=10)
    state, log = tmp_path / "state.json", tmp_path / "log.jsonl"
    client = FakeClient({"aleabitoreddit": ([_post("111"), _post("110")],
                                            {"newest_id": "111", "result_count": 2})})

    first = collect_mod.sweep(cfg, client=client, state_path=state, log_path=log)
    assert first["new_posts"] == 2
    assert client.calls[0]["since_id"] is None
    assert client.calls[0]["max_results"] == 5, "cold start must use first_run_max"

    client.pages["aleabitoreddit"] = ([], {"result_count": 0})
    second = collect_mod.sweep(cfg, client=client, state_path=state, log_path=log)
    assert second["new_posts"] == 0
    assert client.calls[1]["since_id"] == "111", "watermark must carry across sweeps"
    assert client.calls[1]["max_results"] is None


def test_shadow_log_is_append_only(tmp_path):
    cfg = _config()
    state, log = tmp_path / "state.json", tmp_path / "log.jsonl"
    c1 = FakeClient({"aleabitoreddit": ([_post("200")], {"newest_id": "200"})})
    collect_mod.sweep(cfg, client=c1, state_path=state, log_path=log)
    c2 = FakeClient({"aleabitoreddit": ([_post("201")], {"newest_id": "201"})})
    collect_mod.sweep(cfg, client=c2, state_path=state, log_path=log)

    rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert [r["post_id"] for r in rows] == ["200", "201"], "earlier records must survive"


def test_budget_ceiling_stops_sweep_without_losing_prior_data(tmp_path):
    """Hitting the cap is a deliberate stop, not a crash — and whatever was already
    collected stays on disk."""
    cfg = _config(roster=[
        {"handle": "aaa", "label": "A", "enabled": True},
        {"handle": "bbb", "label": "B", "enabled": True},
    ])
    state, log = tmp_path / "state.json", tmp_path / "log.jsonl"

    class Stingy(FakeClient):
        def fetch_timeline(self, user_id, *, since_id=None, max_results=None,
                           paginate=True, stop_after=None):
            if user_id == "id-bbb":
                raise budget_mod.BudgetExceeded("refused: worst case $9 > $0 remaining")
            return super().fetch_timeline(user_id, since_id=since_id,
                                          max_results=max_results, paginate=paginate,
                                          stop_after=stop_after)

    client = Stingy({"aaa": ([_post("300")], {"newest_id": "300"})})
    result = collect_mod.sweep(cfg, client=client, state_path=state, log_path=log)

    assert result["budget_stopped"] is True
    assert result["new_posts"] == 1
    rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert [r["post_id"] for r in rows] == ["300"]
    assert json.loads(state.read_text())["handles"]["aaa"]["since_id"] == "300"


def test_one_bad_handle_does_not_sink_the_sweep(tmp_path):
    from scripts.x_kol.client import XClientError
    cfg = _config(roster=[
        {"handle": "broken", "label": "X", "enabled": True},
        {"handle": "good", "label": "Y", "enabled": True},
    ])
    state, log = tmp_path / "state.json", tmp_path / "log.jsonl"

    class Flaky(FakeClient):
        def fetch_timeline(self, user_id, *, since_id=None, max_results=None,
                           paginate=True, stop_after=None):
            if user_id == "id-broken":
                raise XClientError("404 on /users/id-broken/tweets")
            return super().fetch_timeline(user_id, since_id=since_id,
                                          max_results=max_results, paginate=paginate,
                                          stop_after=stop_after)

    client = Flaky({"good": ([_post("400")], {"newest_id": "400"})})
    result = collect_mod.sweep(cfg, client=client, state_path=state, log_path=log)
    assert result["new_posts"] == 1 and len(result["errors"]) == 1


def test_placeholder_roster_entries_are_never_swept():
    cfg = _config()
    assert [m["handle"] for m in collect_mod.active_roster(cfg)] == ["aleabitoreddit"]


# ── pagination: a busy account must not fall into a silent gap ───────────
class PagedSession:
    """Serves pages newest-first, mimicking X: under-filled pages + next_token."""

    def __init__(self, pages):
        self.pages = pages          # list of (posts, next_token)
        self.seen_params = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.seen_params.append(dict(params or {}))
        token = (params or {}).get("pagination_token")
        idx = 0 if token is None else next(
            i + 1 for i, (_, t) in enumerate(self.pages) if t == token)
        posts, nxt = self.pages[idx]
        meta = {"result_count": len(posts)}
        if posts:
            meta["newest_id"] = posts[0]["id"]
            meta["oldest_id"] = posts[-1]["id"]
        if nxt:
            meta["next_token"] = nxt

        class R:
            status_code = 200
            headers: dict = {}

            def json(self_inner):
                return {"data": posts, "meta": meta}
        return R()


def _client(cfg, tmp_path, session):
    return XClient(cfg, token="t", usage_path=tmp_path / "u.json",
                   session=session, sleep=lambda _s: None)


def test_pagination_follows_next_token_to_close_the_gap(tmp_path):
    """Asked-for count is a ceiling and pages arrive under-filled, so one fetch
    can miss posts that are still newer than the watermark. Advancing the
    watermark then loses them permanently — pagination is what prevents that."""
    cfg = _config()
    session = PagedSession([
        ([_post("30"), _post("29")], "tok1"),
        ([_post("28")], None),
    ])
    posts, meta = _client(cfg, tmp_path, session).fetch_timeline("id-x", since_id="10")

    assert [p["id"] for p in posts] == ["30", "29", "28"], "every new post must be collected"
    assert meta["newest_id"] == "30", "watermark comes from the newest page"
    assert meta["pages"] == 2 and meta["truncated"] is False
    assert session.seen_params[0].get("since_id") == "10"
    assert session.seen_params[1].get("pagination_token") == "tok1"


def test_page_cap_reports_truncation_instead_of_hiding_the_gap(tmp_path):
    cfg = _config()
    cfg["collect"]["max_pages_per_sweep"] = 2
    session = PagedSession([
        ([_post("30")], "t1"), ([_post("29")], "t2"), ([_post("28")], None),
    ])
    posts, meta = _client(cfg, tmp_path, session).fetch_timeline("id-x", since_id="10")
    assert len(posts) == 2 and meta["truncated"] is True


def test_cold_start_does_not_paginate_into_years_of_history(tmp_path):
    cfg = _config()
    session = PagedSession([([_post("30")], "tok1"), ([_post("29")], None)])
    posts, meta = _client(cfg, tmp_path, session).fetch_timeline(
        "id-x", since_id=None, stop_after=2)
    assert [p["id"] for p in posts] == ["30", "29"], \
        "cold start paginates to a RECORD cap, because pages arrive under-filled"
    assert meta["pages"] == 2


def test_stop_after_trims_an_overshooting_page(tmp_path):
    """A page can return more than the remaining cap; the caller asked for N."""
    cfg = _config()
    session = PagedSession([([_post("30"), _post("29"), _post("28")], "tok1")])
    posts, _ = _client(cfg, tmp_path, session).fetch_timeline(
        "id-x", since_id=None, stop_after=2)
    assert [p["id"] for p in posts] == ["30", "29"]


def test_every_page_is_billed_for_what_it_actually_returned(tmp_path):
    cfg = _config()
    usage = tmp_path / "u.json"
    session = PagedSession([([_post("30"), _post("29")], "tok1"), ([_post("28")], None)])
    XClient(cfg, token="t", usage_path=usage, session=session,
            sleep=lambda _s: None).fetch_timeline("id-x", since_id="10")
    ledger = budget_mod.load_ledger(usage)
    assert ledger["post_reads"] == 3, "3 posts across 2 pages"
    assert ledger["requests"] == 2


def test_sweep_surfaces_truncation_as_an_error_row(tmp_path):
    cfg = _config()
    cfg["collect"]["max_pages_per_sweep"] = 1
    state, log = tmp_path / "s.json", tmp_path / "l.jsonl"
    json.dump({"version": 1, "handles": {"aleabitoreddit": {
        "user_id": "id-aleabitoreddit", "since_id": "10"}}},
        open(state, "w"))
    session = PagedSession([([_post("30")], "t1"), ([_post("29")], None)])
    client = _client(cfg, tmp_path, session)
    result = collect_mod.sweep(cfg, client=client, state_path=state, log_path=log)
    assert any("truncated" in e for e in result["errors"])
    assert "TRUNCATED" in result["per_handle"][0]["note"]


# ── analysis watermark: only new content ever reaches the LLM ────────────
def _sweep_with(cfg, tmp_path, posts, newest, state=None, log=None):
    state = state or tmp_path / "state.json"
    log = log or tmp_path / "log.jsonl"
    client = FakeClient({"aleabitoreddit": (posts, {"newest_id": newest})})
    return collect_mod.sweep(cfg, client=client, state_path=state, log_path=log), log


def test_pending_serves_each_record_exactly_once_after_commit(tmp_path):
    cfg = _config()
    cursor = tmp_path / "cursor.json"
    _, log = _sweep_with(cfg, tmp_path, [_post("111"), _post("110")], "111")

    first = pending_mod.read_pending(log, cursor)
    assert [r["post_id"] for r in first.records] == ["111", "110"]
    pending_mod.commit(cursor, first.offset, analyzed=len(first))

    # nothing new appended → nothing to analyze
    assert len(pending_mod.read_pending(log, cursor)) == 0

    _sweep_with(cfg, tmp_path, [_post("112")], "112",
                state=tmp_path / "state.json", log=log)
    second = pending_mod.read_pending(log, cursor)
    assert [r["post_id"] for r in second.records] == ["112"], \
        "only the newly appended record may reach the LLM"


def test_uncommitted_batch_is_reserved_not_dropped(tmp_path):
    """Crash between read and commit must re-serve, never silently skip."""
    cfg = _config()
    cursor = tmp_path / "cursor.json"
    _, log = _sweep_with(cfg, tmp_path, [_post("200")], "200")

    first = pending_mod.read_pending(log, cursor)
    assert len(first) == 1
    # ...analysis dies here, no commit...
    again = pending_mod.read_pending(log, cursor)
    assert [r["post_id"] for r in again.records] == ["200"]


def test_partial_trailing_line_is_not_served(tmp_path):
    """A writer mid-append must not hand the LLM half a JSON record."""
    cursor = tmp_path / "cursor.json"
    log = tmp_path / "log.jsonl"
    log.write_text(json.dumps({"post_id": "1"}) + "\n" + '{"post_id": "2", "tex',
                   encoding="utf-8")
    batch = pending_mod.read_pending(log, cursor)
    assert [r["post_id"] for r in batch.records] == ["1"]

    # once the writer finishes the line, the next pass picks it up whole
    pending_mod.commit(cursor, batch.offset, analyzed=len(batch))
    log.write_text(json.dumps({"post_id": "1"}) + "\n" + json.dumps({"post_id": "2"}) + "\n",
                   encoding="utf-8")
    assert [r["post_id"] for r in pending_mod.read_pending(log, cursor).records] == ["2"]


def test_limit_advances_cursor_only_over_what_was_served(tmp_path):
    cursor = tmp_path / "cursor.json"
    log = tmp_path / "log.jsonl"
    log.write_text("".join(json.dumps({"post_id": str(i)}) + "\n" for i in range(5)),
                   encoding="utf-8")
    batch = pending_mod.read_pending(log, cursor, limit=2)
    assert [r["post_id"] for r in batch.records] == ["0", "1"]
    pending_mod.commit(cursor, batch.offset, analyzed=len(batch))
    assert [r["post_id"] for r in pending_mod.read_pending(log, cursor).records] == ["2", "3", "4"]


def test_truncated_log_restarts_rather_than_seeking_past_eof(tmp_path):
    cursor = tmp_path / "cursor.json"
    log = tmp_path / "log.jsonl"
    log.write_text("".join(json.dumps({"post_id": str(i)}) + "\n" for i in range(5)),
                   encoding="utf-8")
    batch = pending_mod.read_pending(log, cursor)
    pending_mod.commit(cursor, batch.offset, analyzed=len(batch))
    log.write_text(json.dumps({"post_id": "fresh"}) + "\n", encoding="utf-8")
    reread = pending_mod.read_pending(log, cursor)
    assert [r["post_id"] for r in reread.records] == ["fresh"]


def test_sweep_returns_the_new_records_for_in_process_consumers(tmp_path):
    cfg = _config()
    result, _ = _sweep_with(cfg, tmp_path, [_post("300"), _post("299")], "300")
    assert [r["post_id"] for r in result["records"]] == ["300", "299"]
    assert result["new_posts"] == len(result["records"])


# ── parsing ──────────────────────────────────────────────────────────────
def test_cashtags_come_from_x_entities_deduped():
    assert cashtags(_post("1", tags=("NVDA", "nvda", "AMD"))) == ["NVDA", "AMD"]
    assert cashtags({"entities": {}}) == []
    assert cashtags({}) == []


def test_normalize_shape():
    rec = normalize(_post("500"), handle="aleabitoreddit", label="Serenity")
    assert rec["post_id"] == "500"
    assert rec["url"] == "https://x.com/aleabitoreddit/status/500"
    assert rec["cashtags"] == ["NVDA"]
    assert rec["metrics"]["impression"] == 900
    assert rec["collected_at"], "observation time is needed to measure lead/lag later"


# ── auth / dry-run ───────────────────────────────────────────────────────
def test_dry_run_needs_no_token_and_issues_nothing(tmp_path):
    cfg = _config()
    client = XClient(cfg, token="", dry_run=True, usage_path=tmp_path / "u.json")
    posts, meta = client.fetch_timeline("id-x")
    assert posts == [] and meta["dry_run"] is True
    assert client.calls == 0
    assert budget_mod.load_ledger(tmp_path / "u.json")["spent_usd"] == 0.0


def test_rate_limit_headers_are_captured_from_responses(tmp_path):
    """Frequency headroom must be measured, not assumed. X ships x-rate-limit-*
    on every response at no extra cost."""
    class Resp:
        status_code = 200
        headers = {"x-rate-limit-limit": "900", "x-rate-limit-remaining": "873",
                   "x-rate-limit-reset": "1780000000"}

        def json(self):
            return {"data": [_post("700")], "meta": {"newest_id": "700"}}

    class Sess:
        def get(self, *a, **kw):
            return Resp()

    cfg = _config()
    client = XClient(cfg, token="t", usage_path=tmp_path / "u.json",
                     session=Sess(), sleep=lambda _s: None)
    posts, _ = client.fetch_timeline("id-x")
    assert len(posts) == 1
    seen = client.rate_limit["tweets"]
    assert seen["limit"] == 900 and seen["remaining"] == 873


def test_live_client_without_token_refuses_to_construct(tmp_path):
    from scripts.x_kol.client import XAuthMissing
    with pytest.raises(XAuthMissing):
        XClient(_config(), token="", dry_run=False, usage_path=tmp_path / "u.json")


# ── secrets handling ─────────────────────────────────────────────────────
def test_env_file_parses_export_and_quotes_without_leaking(tmp_path, monkeypatch):
    from scripts.x_kol import client as client_mod
    env = tmp_path / "secrets.env"
    env.write_text(
        "# comment\n"
        "FMP_API_KEY=abc123\n"
        "export X_BEARER_TOKEN='tok-with-quotes'\n"
        "MALFORMED_NO_EQUALS\n"
        '  OTHER="dq"  \n',
        encoding="utf-8",
    )
    monkeypatch.setenv("X_KOL_ENV_FILE", str(env))
    parsed = client_mod.load_env_file()
    assert parsed["X_BEARER_TOKEN"] == "tok-with-quotes"
    assert parsed["FMP_API_KEY"] == "abc123"
    assert parsed["OTHER"] == "dq"
    assert "MALFORMED_NO_EQUALS" not in parsed


def test_real_environment_beats_the_file(tmp_path, monkeypatch):
    from scripts.x_kol import client as client_mod
    env = tmp_path / "secrets.env"
    env.write_text("X_BEARER_TOKEN=from-file\n", encoding="utf-8")
    monkeypatch.setenv("X_KOL_ENV_FILE", str(env))

    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    assert client_mod.resolve_token() == ("from-file", "env_file")

    monkeypatch.setenv("X_BEARER_TOKEN", "from-env")
    assert client_mod.resolve_token() == ("from-env", "env")


def test_loose_permissions_on_secrets_file_are_detected(tmp_path, monkeypatch):
    from scripts.x_kol import client as client_mod
    env = tmp_path / "secrets.env"
    env.write_text("X_BEARER_TOKEN=t\n", encoding="utf-8")
    monkeypatch.setenv("X_KOL_ENV_FILE", str(env))

    env.chmod(0o644)
    assert client_mod.env_file_is_private() is False, "world-readable must be flagged"
    env.chmod(0o600)
    assert client_mod.env_file_is_private() is True
    monkeypatch.setenv("X_KOL_ENV_FILE", str(tmp_path / "absent.env"))
    assert client_mod.env_file_is_private() is None


def test_missing_token_message_points_at_the_secrets_file(tmp_path, monkeypatch):
    from scripts.x_kol.client import ENV_FILE_DEFAULT, XAuthMissing
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("X_KOL_ENV_FILE", str(tmp_path / "absent.env"))
    with pytest.raises(XAuthMissing) as exc:
        XClient(_config(), dry_run=False, usage_path=tmp_path / "u.json")
    assert str(ENV_FILE_DEFAULT) in str(exc.value)
