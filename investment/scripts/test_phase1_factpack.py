#!/usr/bin/env python3
"""test_phase1_factpack.py — locks the V4.106.0 earnings-analyst prewarm contract.

The prewarm is the one write path in an otherwise read-only aggregator, and it runs
two subprocesses that touch the network. Everything that can go wrong there (missing
key, invalid ticker, hung FMP, script moved) has to degrade into a status string and
leave Phase 1 running — a raise here would abort a protocol run for a bundle the
contract already declares optional.

Run: python3 investment/scripts/test_phase1_factpack.py   (rc=0 required)
"""
import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase1_factpack as fp  # noqa: E402

FAILURES = []


def check(label, got, want):
    ok = got == want
    if not ok:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")
    print(f"  {'✓' if ok else '✗'} {label}")


def check_prefix(label, got, prefix):
    ok = isinstance(got, str) and got.startswith(prefix)
    if not ok:
        FAILURES.append(f"{label}: got {got!r}, want prefix {prefix!r}")
    print(f"  {'✓' if ok else '✗'} {label}")


class FakeRun:
    """Records invocations and replays a scripted result per step."""

    def __init__(self, results):
        self.results = results          # list of (returncode, stderr) or Exception
        self.calls = []

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        item = self.results[min(len(self.calls) - 1, len(self.results) - 1)]
        if isinstance(item, BaseException):
            raise item
        rc, err = item[:2]
        out = item[2] if len(item) > 2 else ""
        return subprocess.CompletedProcess(argv, rc, stdout=out, stderr=err)


CACHE_HIT = "[fetch] cache hit: skills/earnings-analyst/cache/X_2026-06-30.json"
WROTE     = "[fetch] wrote skills/earnings-analyst/cache/X_2026-06-30.json (32,428 bytes)"


def with_fake(results, fn):
    real = subprocess.run
    fake = FakeRun(results)
    subprocess.run = fake
    try:
        return fn(), fake
    finally:
        subprocess.run = real


def main():
    print("── shared Phase 0 resolver ──")
    real_repo = fp.REPO
    with tempfile.TemporaryDirectory() as d:
        invest_dir = os.path.join(d, "investment/invest_logs")
        sector_dir = os.path.join(d, "sector/sector_logs")
        os.makedirs(invest_dir)
        os.makedirs(sector_dir)
        canonical = os.path.join(invest_dir, "2026-08-21_phase0.json")
        sector = os.path.join(sector_dir, "2026-08-21_sector_intel.json")
        payload = {
            "macro_summary": {"market_regime": "Goldilocks"},
            "_market_signals": {"vix": 14.9},
            "fred_snapshot": {"regime_label": "Goldilocks"},
            "fred_available": True,
            "phase3_macro_multiplier": 1.0,
            "macro_multiplier_rationale": "FRED benign",
        }
        with open(canonical, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        with open(sector, "w", encoding="utf-8") as f:
            json.dump({"market_regime": "risk-on"}, f)
        now = time.time()
        os.utime(canonical, (now - 1, now - 1))
        os.utime(sector, (now, now))  # newer but schema-incomplete
        fp.REPO = d
        try:
            source, _age, core, frozen = fp.load_phase0("GEV")
            check("canonical beats newer sector context", source, "INVEST_CACHE")
            check("different ticker reuses shared snapshot",
                  frozen, "investment/invest_logs/2026-08-21_phase0.json")
            check("shared macro_summary survives", core.get("macro_summary"),
                  payload["macro_summary"])
            os.unlink(canonical)
            source, _age, _core, frozen = fp.load_phase0("GEV")
            check("sector-only cache requires L3", source, "INCOMPLETE_NEEDS_L3")
            check("incomplete sector has no frozen path", frozen, None)
        finally:
            fp.REPO = real_repo

    print("── prewarm_earnings_cache ──")

    # Happy path on a cache hit: both steps run, in order, and refreshed stays False.
    ((res, refreshed), fake) = with_fake([(0, CACHE_HIT), (0, "")],
                                         lambda: fp.prewarm_earnings_cache("AAOI"))
    check("cache hit → 'ok'", res, "ok")
    check("cache hit → refreshed False", refreshed, False)
    check("ran exactly 2 subprocesses", len(fake.calls), 2)
    check("step 1 is fetch.py", os.path.basename(fake.calls[0][1]), "fetch.py")
    check("step 2 is analyze.py", os.path.basename(fake.calls[1][1]), "analyze.py")
    check("ticker forwarded", fake.calls[0][2], "AAOI")

    # New quarter: fetch.py wrote a file, so the flag the forecaster depends on flips.
    # This cannot be inferred from mtimes — analyze.py rewrites the cache either way.
    ((res, refreshed), _) = with_fake([(0, WROTE), (0, "")],
                                      lambda: fp.prewarm_earnings_cache("AAOI"))
    check("new quarter → 'ok (refreshed)'", res, "ok (refreshed)")
    check("new quarter → refreshed True", refreshed, True)

    # fetch failing must short-circuit — analyze.py on a stale cache would refresh its
    # mtime and make a previous-quarter bundle look freshly built.
    ((res, refreshed), fake) = with_fake([(1, "[ERROR] ZZZZ: no income-statement available")],
                                         lambda: fp.prewarm_earnings_cache("ZZZZ"))
    check_prefix("fetch rc!=0 → 'failed:'", res, "failed: fetch rc=1")
    check("analyze skipped after fetch failure", len(fake.calls), 1)
    check("failure never claims refreshed", refreshed, False)

    # analyze failing is still fail-soft, and is reported as its own step.
    ((res, _r), _) = with_fake([(0, CACHE_HIT), (2, "boom")],
                               lambda: fp.prewarm_earnings_cache("AAOI"))
    check_prefix("analyze rc!=0 → 'failed: analyze'", res, "failed: analyze rc=2")

    # A hung FMP call must not hang the protocol.
    ((res, _r), _) = with_fake([subprocess.TimeoutExpired("fetch.py", 300)],
                               lambda: fp.prewarm_earnings_cache("AAOI"))
    check_prefix("TimeoutExpired → 'timeout:'", res, "timeout: fetch exceeded")

    # Any other exception (OSError, permissions, interpreter missing) degrades too.
    ((res, _r), _) = with_fake([OSError("exec format error")],
                               lambda: fp.prewarm_earnings_cache("AAOI"))
    check_prefix("unexpected exception → 'error:'", res, "error: fetch OSError")

    # Scripts relocated/renamed → skip, never raise.
    real_repo = fp.REPO
    fp.REPO = os.path.join(real_repo, "__does_not_exist__")
    try:
        res, _r = fp.prewarm_earnings_cache("AAOI")
        check_prefix("missing script → 'skipped:'", res, "skipped: fetch.py missing")
    finally:
        fp.REPO = real_repo

    print("── prewarm_forecaster_cache ──")

    (res, fake) = with_fake([(0, "", '{"status":"ok"}')],
                            lambda: fp.prewarm_forecaster_cache("MSFT"))
    check("steady state → 'ok'", res, "ok")
    check("passes --json-only", "--json-only" in fake.calls[0], True)
    check("no --no-cache when quarter unchanged", "--no-cache" in fake.calls[0], False)

    (res, fake) = with_fake([(0, "", '{"status":"ok"}')],
                            lambda: fp.prewarm_forecaster_cache("MSFT", earnings_refreshed=True))
    check("new quarter → forces --no-cache", "--no-cache" in fake.calls[0], True)
    check("new quarter → status says so", res, "ok (refetched: new quarter)")

    # forecast.py exits 1 for unprofitable names; that is a fact about the ticker, not
    # a transport failure, so its own reason has to survive into the audit trail.
    (res, _) = with_fake([(1, "", '{"status":"error","reason":"negative_or_missing_ttm_eps"}')],
                         lambda: fp.prewarm_forecaster_cache("AAOI"))
    check("rc=1 → 'unavailable: <reason>'", res, "unavailable: negative_or_missing_ttm_eps")

    (res, _) = with_fake([subprocess.TimeoutExpired("forecast.py", 300)],
                         lambda: fp.prewarm_forecaster_cache("AAOI"))
    check_prefix("forecaster timeout fail-soft", res, "timeout: exceeded")

    print("── build() wiring ──")
    real_prewarm = fp.prewarm_earnings_cache
    real_fc = fp.prewarm_forecaster_cache
    fp.prewarm_earnings_cache = lambda t: ("sentinel", True)
    fp.prewarm_forecaster_cache = lambda t, r=False: f"fc:{r}"
    try:
        # Everything except the prewarm is stubbed: this asserts wiring, not data.
        stubs = {"load_phase0": lambda t: (
                    "INVEST_CACHE", 0.0, {}, "investment/invest_logs/phase0.json"),
                 "validate_phase0_rc": lambda t, p=None: 0,
                 "load_ticker_data_bundle": lambda t: {"status": "ok"},
                 "load_earnings_bundle": lambda t: {"status": "ok"},
                 "load_peer_bundle": lambda t: {"status": "ok"},
                 "load_supp_bundle": lambda t: {"status": "ok"}}
        saved = {k: getattr(fp, k) for k in stubs}
        for k, v in stubs.items():
            setattr(fp, k, v)
        try:
            out = fp.build("AAOI", run_validator=False)
            check("prewarm runs by default", out.get("earnings_prewarm"), "sentinel")
            check("refreshed flag reaches the forecaster",
                  out.get("forecaster_prewarm"), "fc:True")
            check("frozen Phase 0 path is exported", out.get("phase0_path"),
                  "investment/invest_logs/phase0.json")
            fp.validate_phase0_rc = lambda t, p=None: 1
            invalid = fp.build("AAOI", run_validator=True, prewarm_earnings=False)
            check("fresh snapshot failing gate requires L3",
                  invalid.get("phase0_source"), "INVALID_NEEDS_L3")
            out = fp.build("AAOI", run_validator=False, prewarm_earnings=False)
            check("--no-prewarm → earnings 'disabled'", out.get("earnings_prewarm"), "disabled")
            check("--no-prewarm → forecaster 'disabled'",
                  out.get("forecaster_prewarm"), "disabled")
        finally:
            for k, v in saved.items():
                setattr(fp, k, v)
    finally:
        fp.prewarm_earnings_cache = real_prewarm
        fp.prewarm_forecaster_cache = real_fc

    print()
    if FAILURES:
        print(f"✗ {len(FAILURES)} failure(s):")
        for f in FAILURES:
            print(f"   - {f}")
        return 1
    print("✓ phase1_factpack prewarm contract holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
