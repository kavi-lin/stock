#!/usr/bin/env python3
"""test_heatmap_pe_retry.py — V4.85.0 heatmap PE warm-up retry contract.

The bug this pins down: `_heatmap_refresh_pe_universe()` ran exactly once from a
startup thread and wrote `(now, result)` for every ticker regardless of outcome.
`_fetch_pe_ttm` returned an all-None dict when it had not actually fetched anything
(rate-limit breaker open), so a bad boot cached empty bundles against the 24h TTL —
and since the heatmap loop never called the warm-up again, `heatmap.json` and
everything joined off it stayed blank until the next server restart.

What must hold now:
  1. A failure is never cached — a stale-but-good bundle survives a failed refresh.
  2. Partial success is kept; only the failures are retried.
  3. Retries are backed off, and the backoff escalates while the failure persists.
  4. The rate-limit breaker is not charged as a failed batch (nothing was attempted).
  5. A fully-warm cache costs zero HTTP calls.
  6. A symbol FMP has no bundle for is `PE_ABSENT`, not a failure — it is quarantined
     after a streak instead of pinning the backoff at its ceiling forever (V4.86.2).
  7. A transport outage never quarantines anything, however long it lasts (V4.86.2).

Run: python3 tests/test_heatmap_pe_retry.py   # rc=0 全過 / rc=1 fail
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("FMP_API_KEY", "dummy-key-for-test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.argv = ["dashboard_server.py"]

import dashboard_server as ds  # noqa: E402

FAILS: list[str] = []


def eq(label, got, want):
    if got != want:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


BUNDLE_A = {"pe_ttm": 20.0, "ev_ebitda": 12.0, "fwd_eps": 5.0}
BUNDLE_B = {"pe_ttm": 30.0, "ev_ebitda": 9.0, "fwd_eps": 4.0}


def _reset(tickers=("AAA", "BBB", "CCC", "DDD")):
    ds._heatmap_state["tickers"] = {t: {"price": 100.0} for t in tickers}
    ds._heatmap_pe_cache.clear()
    ds._heatmap_pe_empty_streak.clear()
    ds._heatmap_pe_quarantined.clear()
    ds._heatmap_pe_next_attempt_at = 0.0
    ds._heatmap_pe_backoff_sec = 0
    ds._heatmap_ratelimit_until = 0.0


_orig_fetch = ds._fetch_pe_ttm
try:
    # ── Round 1: half the batch fails ───────────────────────────────────────
    _reset()
    ds._fetch_pe_ttm = lambda sym, key: BUNDLE_A if sym in ("AAA", "BBB") else None
    eq("round1.partial_returns_false", ds._heatmap_refresh_pe_universe(max_workers=4), False)
    eq("round1.successes_cached", sorted(ds._heatmap_pe_cache), ["AAA", "BBB"])
    eq("round1.failures_not_cached", "CCC" in ds._heatmap_pe_cache, False)
    eq("round1.backoff_armed", ds._heatmap_pe_backoff_sec, ds.HEATMAP_PE_RETRY_BASE_SEC)
    eq("round1.rows_patched", ds._heatmap_state["tickers"]["AAA"]["pe"], 20.0)
    eq("round1.failed_row_untouched", "pe" in ds._heatmap_state["tickers"]["CCC"], False)

    # Backoff suppresses an immediate retry.
    eq("backoff.suppresses_retry", ds._heatmap_refresh_pe_universe(max_workers=4), False)

    # ── Round 2: backoff expires, the rest succeed ──────────────────────────
    ds._heatmap_pe_next_attempt_at = 0.0
    ds._fetch_pe_ttm = lambda sym, key: BUNDLE_B
    eq("round2.full_success", ds._heatmap_refresh_pe_universe(max_workers=4), True)
    eq("round2.all_cached", sorted(ds._heatmap_pe_cache), ["AAA", "BBB", "CCC", "DDD"])
    eq("round2.backoff_cleared", ds._heatmap_pe_backoff_sec, 0)
    # The already-good tickers are NOT refetched — their round-1 values survive.
    eq("round2.good_values_kept", ds._heatmap_pe_cache["AAA"][1]["pe_ttm"], 20.0)
    eq("round2.failed_recovered", ds._heatmap_pe_cache["CCC"][1]["pe_ttm"], 30.0)
    eq("round2.forward_pe_computed", ds._heatmap_state["tickers"]["CCC"]["forward_pe"], 25.0)

    # ── A fully-warm cache costs no HTTP ────────────────────────────────────
    called: list[str] = []

    def _spy(sym, key):
        called.append(sym)
        return BUNDLE_B

    ds._fetch_pe_ttm = _spy
    eq("warm.returns_true", ds._heatmap_refresh_pe_universe(max_workers=4), True)
    eq("warm.no_fetches", called, [])

    # ── A failed refresh must not blank an existing good bundle ─────────────
    ds._heatmap_pe_next_attempt_at = 0.0
    ds._heatmap_pe_cache["CCC"] = (0.0, BUNDLE_B)      # force TTL expiry on one ticker
    ds._fetch_pe_ttm = lambda sym, key: None
    ds._heatmap_refresh_pe_universe(max_workers=4)
    eq("stale.good_bundle_survives", ds._heatmap_pe_cache["CCC"][1], BUNDLE_B)
    eq("stale.row_keeps_value", ds._heatmap_state["tickers"]["CCC"]["pe"], 30.0)

    # ── Backoff escalates while the failure persists ────────────────────────
    _reset()
    ds._fetch_pe_ttm = lambda sym, key: None
    ds._heatmap_refresh_pe_universe(max_workers=4)
    b1 = ds._heatmap_pe_backoff_sec
    ds._heatmap_pe_next_attempt_at = 0.0
    ds._heatmap_refresh_pe_universe(max_workers=4)
    b2 = ds._heatmap_pe_backoff_sec
    eq("escalate.base", b1, ds.HEATMAP_PE_RETRY_BASE_SEC)
    eq("escalate.doubles", b2, min(b1 * 2, ds.HEATMAP_PE_RETRY_MAX_SEC))
    # ...and is capped.
    for _ in range(12):
        ds._heatmap_pe_next_attempt_at = 0.0
        ds._heatmap_refresh_pe_universe(max_workers=4)
    eq("escalate.capped", ds._heatmap_pe_backoff_sec, ds.HEATMAP_PE_RETRY_MAX_SEC)

    # ── Rate-limit breaker is not a failed batch ────────────────────────────
    _reset()
    ds._fetch_pe_ttm = lambda sym, key: BUNDLE_A
    ds._heatmap_ratelimit_until = time.time() + 900
    eq("ratelimit.skips", ds._heatmap_refresh_pe_universe(max_workers=4), False)
    eq("ratelimit.no_backoff_charged", ds._heatmap_pe_backoff_sec, 0)
    eq("ratelimit.waits_for_breaker",
       int(ds._heatmap_pe_next_attempt_at), int(ds._heatmap_ratelimit_until))

    # ── _fetch_pe_ttm signals "did not fetch" as None, not an empty bundle ──
    ds._fetch_pe_ttm = _orig_fetch
    ds._heatmap_ratelimit_until = time.time() + 900
    eq("fetch.breaker_returns_none", ds._fetch_pe_ttm("AAPL", "k"), None)

    # ── V4.86.0: a 429 tripping MID-ticker must not cache a half-filled bundle ──
    # The first endpoint's value is real; the other two are None because of the
    # outage, not because the ticker lacks them.
    _orig_get = ds._fmp_get_json
    try:
        state = {"n": 0}

        def _partial(url, timeout=10):
            state["n"] += 1
            if state["n"] == 1:
                return [{"priceToEarningsRatioTTM": 18.5}]
            ds._heatmap_ratelimit_until = time.time() + 1800   # breaker trips
            return None

        ds._fmp_get_json = _partial
        ds._heatmap_ratelimit_until = 0.0
        eq("partial.mid_batch_429_discarded", ds._fetch_pe_ttm("AAPL", "k"), None)

        # ...but a genuinely data-less ticker with no outage is still a real answer:
        # responded=True on at least one endpoint, breaker untouched.
        ds._heatmap_ratelimit_until = 0.0
        ds._fmp_get_json = lambda url, timeout=10: (
            [{"priceToEarningsRatioTTM": None}] if "ratios-ttm" in url else [])
        eq("partial.no_data_but_responded",
           ds._fetch_pe_ttm("LOSSCO", "k"), {"pe_ttm": None, "ev_ebitda": None,
                                             "fwd_eps": None})
        # V4.86.2 — all three endpoints answered with an empty list: the symbol has no
        # bundle at FMP. That is a fact, reported as PE_ABSENT, not a retryable failure.
        ds._fmp_get_json = lambda url, timeout=10: []
        eq("partial.total_silence_is_absent", ds._fetch_pe_ttm("GHOST", "k"), ds.PE_ABSENT)
        # ...but an endpoint that did not answer at all (None ≠ list) is still an outage.
        ds._fmp_get_json = lambda url, timeout=10: ([] if "ratios-ttm" in url else None)
        eq("partial.transport_failure_is_none", ds._fetch_pe_ttm("GHOST", "k"), None)
    finally:
        ds._fmp_get_json = _orig_get
        ds._heatmap_ratelimit_until = 0.0

    # ── V4.86.0: warm-up is non-reentrant ───────────────────────────────────
    import threading
    _reset()
    started = threading.Event()
    release = threading.Event()
    concurrent = {"count": 0, "max": 0}
    guard = threading.Lock()

    def _slow(sym, key):
        with guard:
            concurrent["count"] += 1
            concurrent["max"] = max(concurrent["max"], concurrent["count"])
        started.set()
        release.wait(5)
        with guard:
            concurrent["count"] -= 1
        return BUNDLE_A

    ds._fetch_pe_ttm = _slow
    t1 = threading.Thread(target=ds._heatmap_refresh_pe_universe, kwargs={"max_workers": 2})
    t1.start()
    started.wait(5)
    # Second caller (the refresh loop) must bounce off the lock, not start a 2nd batch.
    eq("reentrancy.second_call_is_noop", ds._heatmap_refresh_pe_universe(max_workers=2), False)
    release.set()
    t1.join(10)
    eq("reentrancy.single_pass_only", concurrent["max"] <= 2, True)   # == max_workers
    eq("reentrancy.batch_completed", sorted(ds._heatmap_pe_cache), ["AAA", "BBB", "CCC", "DDD"])

    # ── V4.86.0: radar lazy fetch has a per-symbol retry floor ──────────────
    # Without it a permanently-empty symbol is refetched every 180s quote TTL.
    ds._heatmap_pe_attempted_at.clear()
    now = time.time()
    ds._heatmap_pe_attempted_at["GHOST"] = now
    eq("lazy.floor_blocks_immediate_retry",
       (now - ds._heatmap_pe_attempted_at["GHOST"]) >= ds.HEATMAP_PE_LAZY_RETRY_SEC, False)
    ds._heatmap_pe_attempted_at["GHOST"] = now - ds.HEATMAP_PE_LAZY_RETRY_SEC - 1
    eq("lazy.floor_expires",
       (now - ds._heatmap_pe_attempted_at["GHOST"]) >= ds.HEATMAP_PE_LAZY_RETRY_SEC, True)
    eq("lazy.floor_is_hours_not_minutes", ds.HEATMAP_PE_LAZY_RETRY_SEC >= 3600, True)

    # ── V4.86.2: permanently-empty symbols are quarantined, not retried forever ──
    # The bug: CCC/DDD have no FMP valuation bundle at all, so every pass left them in
    # `failed` — the backoff sat pinned at its ceiling and `return not failed` was
    # permanently False, which made the health signal meaningless.
    _reset()
    ds._fetch_pe_ttm = lambda sym, key: (BUNDLE_A if sym in ("AAA", "BBB") else ds.PE_ABSENT)
    for i in range(ds.HEATMAP_PE_EMPTY_STREAK_MAX):
        ds._heatmap_pe_next_attempt_at = 0.0
        # An absent symbol is not a failure: the batch is healthy from pass 1.
        eq(f"absent.pass{i}_is_healthy", ds._heatmap_refresh_pe_universe(max_workers=4), True)
        eq(f"absent.pass{i}_no_backoff", ds._heatmap_pe_backoff_sec, 0)
    eq("absent.quarantined_after_streak", sorted(ds._heatmap_pe_quarantined), ["CCC", "DDD"])
    eq("absent.not_cached_as_data", "CCC" in ds._heatmap_pe_cache, False)

    # Quarantined symbols leave the batch entirely — zero HTTP for them.
    probed: list[str] = []

    def _count(sym, key):
        probed.append(sym)
        return ds.PE_ABSENT

    ds._fetch_pe_ttm = _count
    ds._heatmap_pe_next_attempt_at = 0.0
    eq("absent.quarantine_returns_true", ds._heatmap_refresh_pe_universe(max_workers=4), True)
    eq("absent.quarantine_skips_fetch", probed, [])

    # The quarantine expires and the symbol gets exactly one re-probe.
    ds._heatmap_pe_quarantined["CCC"] = time.time() - ds.HEATMAP_PE_QUARANTINE_SEC - 1
    ds._heatmap_pe_next_attempt_at = 0.0
    ds._heatmap_refresh_pe_universe(max_workers=4)
    eq("absent.reprobe_after_expiry", probed, ["CCC"])
    eq("absent.reprobe_requarantines", "CCC" in ds._heatmap_pe_quarantined, True)

    # A symbol that starts answering again clears both the streak and the quarantine.
    ds._heatmap_pe_quarantined["DDD"] = time.time() - ds.HEATMAP_PE_QUARANTINE_SEC - 1
    ds._fetch_pe_ttm = lambda sym, key: BUNDLE_B
    ds._heatmap_pe_next_attempt_at = 0.0
    ds._heatmap_refresh_pe_universe(max_workers=4)
    eq("absent.recovery_clears_quarantine", "DDD" in ds._heatmap_pe_quarantined, False)
    eq("absent.recovery_clears_streak", "DDD" in ds._heatmap_pe_empty_streak, False)
    eq("absent.recovery_cached", ds._heatmap_pe_cache["DDD"][1]["pe_ttm"], 30.0)

    # ── V4.86.2: an outage must never quarantine the universe ───────────────
    # Every symbol failing on transport looks identical to "every symbol is empty" if
    # you only count failures — which is why the fetcher distinguishes the two.
    _reset()
    ds._fetch_pe_ttm = lambda sym, key: None
    for _ in range(ds.HEATMAP_PE_EMPTY_STREAK_MAX + 2):
        ds._heatmap_pe_next_attempt_at = 0.0
        ds._heatmap_refresh_pe_universe(max_workers=4)
    eq("outage.nothing_quarantined", dict(ds._heatmap_pe_quarantined), {})
    eq("outage.no_streaks", dict(ds._heatmap_pe_empty_streak), {})
    eq("outage.backoff_still_armed", ds._heatmap_pe_backoff_sec > 0, True)
finally:
    ds._fetch_pe_ttm = _orig_fetch
    ds._heatmap_ratelimit_until = 0.0

if FAILS:
    print(f"✗ {len(FAILS)} failure(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ heatmap PE warm-up retry contract holds")
