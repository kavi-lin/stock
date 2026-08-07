#!/usr/bin/env python3
"""
phase1_factpack.py — Phase 0/1 single-call data aggregator for investment_protocol_v5_0.

WHY: A normal `分析 <TICKER>` run spent ~13-16 separate Bash *turns* just gathering
Phase 0 cache + the 4 Phase-1 bundles (sector_intel → dual_fetch → peers →
supplementary → earnings cache). Each turn re-bills the whole (growing) context as
cache_read. Collapsing them into ONE deterministic call removes those turns.

Contract (deliberately narrow so it can NEVER change a decision):
  - Reuses the exact same source functions the protocol already used
    (run_dual_fetch.sh, company_context.get_peers/get_profile,
    fmp_supplementary.get_supplementary_bundle, earnings-analyst cache).
  - Read-only w.r.t. invest_logs / history / reports. V4.106.0-4.107.0 added TWO write
    paths, both into the owning skill's own cache dir, both 0-LLM, both fail-soft:
    prewarm_earnings_cache() (earnings-analyst) and prewarm_forecaster_cache()
    (earnings-valuation-forecaster). Neither skill is ever run by the protocol
    otherwise — it only globs their caches — so a same-day earnings release would
    reach Phase 1.5 as 0/8 anchors. Both are disabled by --no-prewarm. See each
    function for cost, ordering and freshness rules.
  - 0 LLM. Fail-soft: any bundle that fails → status string, never raises, never aborts.
  - Strips dual_fetch `_audit` (Phase 1 isolation contract — lanes must not see it).
  - Does NOT run the heavy L3 Phase-0 skill chain. If phase0 cache is stale it reports
    `phase0_source: "STALE_NEEDS_L3"` and lets the protocol decide.
  - Writes NOTHING to invest_logs / history. Pure aggregation to stdout / --out file.

Usage:
  python3 investment/scripts/phase1_factpack.py MRVL
  python3 investment/scripts/phase1_factpack.py MRVL --out /tmp/MRVL_factpack.json

Output JSON shape (mirrors what the protocol pastes into the 5 lanes):
  {
    "ticker", "generated_at",
    "phase0_source", "phase0_stale_hours", "phase0": {...extracted core fields...},
    "phase0_validator_rc",
    "earnings_prewarm":   "ok | disabled | skipped: … | timeout: … | failed: … | error: …",
    "forecaster_prewarm": "ok | ok (refetched: earnings newer) | disabled | unavailable: … | …",
    "bundles_loaded": {ticker_data_bundle, earnings_analyst_bundle, peer_bundle, fmp_supp_bundle},
    "bundles": {
       "ticker_data_bundle": {"status", "scoring": {...15 scalar...}},
       "earnings_analyst_bundle": {...appendix shape... | "status"},
       "peer_bundle": {...appendix shape... | "status"},
       "fmp_supp_bundle": {...full supp bundle... | "status"}
    }
  }
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time
from datetime import date, datetime
from statistics import median

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRESH_SECONDS = 3 * 3600  # Phase 0 cache FRESH window (mtime < 3h), matches protocol


def _mtime_age_hours(path):
    return round((time.time() - os.path.getmtime(path)) / 3600.0, 2)


# ---------------------------------------------------------------- Phase 0 (cache only)
def load_phase0(ticker):
    """L1 sector_intel → L2 invest phase0. No L3 (heavy skill chain stays in protocol)."""
    # L1: latest sector_intel
    l1 = sorted(glob.glob(os.path.join(REPO, "sector/sector_logs/*_sector_intel.json")))
    if l1:
        path = l1[-1]
        age_h = _mtime_age_hours(path)
        try:
            d = json.load(open(path))
        except Exception as e:
            d = None
        if d is not None:
            p0 = d.get("_phase0", {}) or {}
            ftd = p0.get("ftd", {}) or {}
            core = {
                "market_regime": d.get("market_regime") or (d.get("macro_summary") or {}).get("market_regime"),
                "exposure_ceiling": d.get("exposure_ceiling"),
                "political_risk_summary": d.get("political_risk_summary"),
                "actionable_themes": d.get("actionable_themes") or d.get("themes"),
                "ftd_days_since": ftd.get("days_since_ftd"),
                "ftd_status_text": ftd.get("ftd_status_text") or ftd.get("status"),
                "macro_summary": d.get("macro_summary"),
                "_market_signals": d.get("_market_signals"),
            }
            src = "SECTOR_CACHE" if age_h * 3600 < FRESH_SECONDS else "STALE_NEEDS_L3"
            return src, age_h, core
    # L2: invest_logs phase0
    l2 = sorted(glob.glob(os.path.join(REPO, "investment/invest_logs/*_phase0.json")))
    if l2:
        path = l2[-1]
        age_h = _mtime_age_hours(path)
        try:
            d = json.load(open(path))
        except Exception:
            d = None
        if d is not None:
            core = {
                "macro_summary": d.get("macro_summary"),
                "_market_signals": d.get("_market_signals"),
                "fred_snapshot": d.get("fred_snapshot"),
                "phase3_macro_multiplier": d.get("phase3_macro_multiplier"),
            }
            src = "INVEST_CACHE" if age_h * 3600 < FRESH_SECONDS else "STALE_NEEDS_L3"
            return src, age_h, core
    return "STALE_NEEDS_L3", None, {}


def validate_phase0_rc(ticker):
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(REPO, "investment/scripts/validate_phase0.py"), "--ticker", ticker],
            cwd=REPO, capture_output=True, text=True, timeout=120,
        )
        return r.returncode
    except Exception:
        return None


# ---------------------------------------------------------------- TICKER_DATA_BUNDLE
def load_ticker_data_bundle(ticker):
    """run_dual_fetch.sh → read scoring (15 scalar). Strips _audit per isolation contract."""
    today = date.today().isoformat()
    out_path = os.path.join(REPO, f"skills/finnhub-client/data/{today}/{ticker}.json")
    # reuse today's fetch if present; else run dual_fetch
    if not os.path.exists(out_path):
        if not (os.environ.get("FINNHUB_API_KEY") and os.environ.get("FMP_API_KEY")):
            return {"status": "unavailable", "reason": "missing FINNHUB_API_KEY/FMP_API_KEY"}
        try:
            subprocess.run(
                ["bash", os.path.join(REPO, "skills/finnhub-client/scripts/run_dual_fetch.sh"),
                 "--tickers", ticker],
                cwd=REPO, capture_output=True, text=True, timeout=180,
            )
        except Exception as e:
            return {"status": "unavailable", "reason": f"dual_fetch failed: {e}"}
    if not os.path.exists(out_path):
        return {"status": "unavailable", "reason": "dual_fetch produced no file"}
    try:
        d = json.load(open(out_path))
    except Exception as e:
        return {"status": "unavailable", "reason": f"read failed: {e}"}
    scoring = d.get("scoring")
    if not scoring:
        return {"status": "unavailable", "reason": "no scoring block"}
    # isolation: never surface _audit
    return {"status": "ok", "fetched_at": d.get("fetched_at"), "scoring": scoring}


# ---------------------------------------------------------------- EARNINGS_ANALYST_BUNDLE
PREWARM_TIMEOUT_S = int(os.environ.get("FACTPACK_EARNINGS_PREWARM_TIMEOUT", "300"))


def prewarm_earnings_cache(ticker):
    """Build/refresh the earnings-analyst cache before the bundle is read.

    WHY: nothing in the invest protocol ever *runs* the earnings-analyst skill — both
    readers (this file and compute_price_framework._latest_earnings_cache) are plain
    globs over the cache dir. So on a day a company reports, Phase 1.5 freezes
    valuation_pack against a missing (or previous-quarter) bundle, all 8 anchors come
    back `missing_or_nonpositive_value`, and the run ends at the `insufficient_anchors`
    decision cap. Silently — the bundle contract is fail-soft, so nothing warns.
    Observed 2026-08-07 on AAOI: analysis ran 16:39, cache landed ~16:5x, 0/8 anchors.

    COST: fetch.py self-gates. It resolves last_earnings_date from one
    income-statement call and returns early on a (TICKER, last_earnings_date) cache
    hit, so steady state is a single FMP call; the full 17-endpoint pull happens only
    when the ticker has actually reported since the cached quarter. That "ask FMP what
    the latest quarter is" call is also a better freshness probe than an earnings
    calendar — a calendar says the release was announced, this says the numbers are
    queryable, and only the latter is what the anchors need.

    SCOPE: fetch + analyze only. Both are 0-LLM. The narrate/render/validate steps
    belong to `財報 <T>` and produce the MD report + infographic, which no anchor
    reads. analyze.py is mandatory, not optional — load_earnings_bundle rejects a
    cache with no composite_score, so fetch alone would still yield not_available.

    Returns (status, refreshed). `refreshed` is True when fetch.py actually pulled a
    new quarter rather than returning on a cache hit. Downstream needs that distinction
    and cannot derive it from the filesystem: analyze.py rewrites the cache in place on
    every run, so its mtime always reads as "just now" and cannot tell "a new quarter
    landed" apart from "we recomputed the same quarter". Never raises: any failure
    leaves the caller on its existing not_available path.
    """
    scripts = os.path.join(REPO, "skills", "earnings-analyst", "scripts")
    steps = [("fetch", os.path.join(scripts, "fetch.py")),
             ("analyze", os.path.join(scripts, "analyze.py"))]
    refreshed = False
    for name, script in steps:
        if not os.path.exists(script):
            return f"skipped: {name}.py missing", refreshed
        try:
            p = subprocess.run([sys.executable, script, ticker],
                               capture_output=True, text=True,
                               timeout=PREWARM_TIMEOUT_S, cwd=REPO)
        except subprocess.TimeoutExpired:
            return f"timeout: {name} exceeded {PREWARM_TIMEOUT_S}s", refreshed
        except Exception as e:                                    # noqa: BLE001 — fail-soft by contract
            return f"error: {name} {type(e).__name__}: {e}", refreshed
        if p.returncode != 0:
            # fetch.py sys.exit()s on a missing FMP_API_KEY / invalid ticker; both are
            # legitimate degraded states for the protocol, not reasons to abort Phase 1.
            tail = (p.stderr or p.stdout or "").strip().splitlines()
            return f"failed: {name} rc={p.returncode} {tail[-1][:120] if tail else ''}", refreshed
        if name == "fetch":
            # fetch.py announces its own decision on stderr; absence of the cache-hit
            # line means it wrote a new (TICKER, last_earnings_date) file.
            refreshed = "cache hit:" not in (p.stderr or "")
    return ("ok (refreshed)" if refreshed else "ok"), refreshed


def _earnings_cache_path(ticker):
    cands = [p for p in glob.glob(os.path.join(REPO, f"skills/earnings-analyst/cache/{ticker}_*.json"))
             if ".infographic." not in p]
    return sorted(cands)[-1] if cands else None


def prewarm_forecaster_cache(ticker, earnings_refreshed=False):
    """Build/refresh the earnings-valuation-forecaster cache. Same disease as above.

    compute_price_framework only does `if os.path.exists(fc_path)` — the protocol
    documents the generating command (forecast.py <T> --json-only) but never runs it,
    so `forecaster_blend` is absent by default. Small on its own (weight 0.05), but it
    also feeds `forecaster.transition_case`, and that is the ONLY mandatory trigger in
    valuation_reviewer_gate. With no cache the gate reads transition_case=False —
    absence silently rendered as a negative finding rather than as "not checked".

    ORDER: must run after prewarm_earnings_cache. forecast.py reads the
    earnings-analyst cache for its own inputs.

    FRESHNESS: forecast.py self-gates on a 4h wall-clock TTL, which is blind to
    earnings — a forecast written 3h before this morning's release would still be
    served as fresh. So we force a refetch exactly when the caller reports that the
    earnings prewarm pulled a NEW quarter; otherwise the TTL is left to do its job
    (cache hit = 0 FMP calls, miss is ~6 endpoints). 0 LLM either way.

    Do NOT try to infer this by comparing cache mtimes: analyze.py rewrites the
    earnings cache in place every run, so it is always the newer file and the
    comparison is unconditionally true — that costs a full refetch on every single
    protocol run (measured: 27s for MSFT) while looking like a targeted invalidation.

    Returns a status string; never raises. Reported separately from earnings_prewarm
    because the blast radii differ by an order of magnitude: this gates one 0.05
    anchor, that one gates six anchors plus the Fundamentals lane.
    """
    script = os.path.join(REPO, "skills", "earnings-valuation-forecaster", "scripts", "forecast.py")
    if not os.path.exists(script):
        return "skipped: forecast.py missing"
    argv = [sys.executable, script, ticker, "--json-only"]
    if earnings_refreshed:
        argv.append("--no-cache")

    try:
        p = subprocess.run(argv, capture_output=True, text=True,
                           timeout=PREWARM_TIMEOUT_S, cwd=REPO)
    except subprocess.TimeoutExpired:
        return f"timeout: exceeded {PREWARM_TIMEOUT_S}s"
    except Exception as e:                            # noqa: BLE001 — fail-soft by contract
        return f"error: {type(e).__name__}: {e}"
    if p.returncode != 0:
        # forecast.py exits 1 whenever status != "ok", which includes legitimate
        # "this ticker cannot be forecast" cases (negative EPS has no PE percentile
        # band). Surface its own reason so that reads differently from a transport
        # failure — neither is a reason to hold up Phase 1.
        reason = ""
        try:
            reason = (json.loads(p.stdout or "{}").get("reason") or "")[:120]
        except Exception:
            reason = (p.stderr or "").strip().splitlines()[-1][:120] if p.stderr else ""
        return f"unavailable: {reason or f'rc={p.returncode}'}"
    return "ok (refetched: new quarter)" if earnings_refreshed else "ok"


def load_earnings_bundle(ticker):
    cands = [p for p in glob.glob(os.path.join(REPO, f"skills/earnings-analyst/cache/{ticker}_*.json"))
             if ".infographic." not in p]
    if not cands:
        return {"status": "not_available"}
    path = sorted(cands)[-1]
    age_days = (time.time() - os.path.getmtime(path)) / 86400.0
    if age_days > 90:
        return {"status": "not_available", "reason": f"stale {age_days:.0f}d > 90d"}
    try:
        ea = json.load(open(path))
    except Exception as e:
        return {"status": "not_available", "reason": f"read failed: {e}"}
    if "composite_score" not in ea:
        return {"status": "not_available", "reason": "no composite_score (analyze.py incomplete)"}
    val = ea.get("valuation") or {}
    ana = ea.get("analyst") or {}
    der = ea.get("derived") or {}
    return {
        "status": "ok",
        "last_earnings_date": ea.get("last_earnings_date"),
        "next_earnings_est": ea.get("next_earnings_est"),
        "composite_score": ea.get("composite_score"),
        "verdict": ea.get("verdict"),
        "score_components": ea.get("score_components"),
        "quality_flags": ea.get("quality_flags") or [],
        "margins_8q": der.get("margins_8q"),
        "yoy_growth": der.get("yoy_growth"),
        "balance_health": der.get("balance_health"),
        "cash_flow_quality": der.get("cash_flow_quality"),
        "valuation": {
            "dcf_intrinsic": val.get("dcf_intrinsic"),
            "dcf_levered_intrinsic": val.get("dcf_levered_intrinsic"),
            "dcf_vs_price_pct": val.get("dcf_vs_price_pct"),
            "price_target_consensus": val.get("price_target_consensus"),
            "pt_upside_pct": val.get("pt_upside_pct"),
            "pt_dispersion_pct": val.get("pt_dispersion_pct"),
            "pt_news": val.get("pt_news") or [],
        },
        "analyst": {
            "rating_trend": ana.get("rating_trend"),
            "grades_summary": ana.get("grades_summary"),
            "grades_news": ana.get("grades_news") or [],
        },
        "report_path": os.path.basename(path).replace(".json", ""),
    }


# ---------------------------------------------------------------- PEER_BUNDLE
def load_peer_bundle(ticker):
    sys.path.insert(0, REPO)
    try:
        from skills._shared.company_context import (
            get_profile, get_ratios_ttm, select_valuation_peers,
        )
    except Exception as e:
        return {"status": "unavailable", "reason": f"import failed: {e}"}
    try:
        selection = select_valuation_peers(ticker)
        peers_raw = selection.get("peers") or []
    except Exception as e:
        return {"status": "unavailable", "reason": f"get_peers failed: {e}"}
    range_peer_cohort = None
    range_peer_scenario = None
    try:
        vm_scripts = os.path.join(REPO, "skills", "valuation-modeler", "scripts")
        if vm_scripts not in sys.path:
            sys.path.insert(0, vm_scripts)
        import peer_cohorts
        range_peer_cohort = peer_cohorts.build_pe_cohort(ticker)
        self_ratios_for_range = get_ratios_ttm(ticker) or {}
        self_profile_for_range = get_profile(ticker) or {}
        range_value = peer_cohorts.implied_pe_value({
            "price": self_profile_for_range.get("price"),
            "pe": self_ratios_for_range.get("pe_ttm"),
        }, range_peer_cohort)
        range_peer_scenario = {
            **range_peer_cohort,
            "value": range_value,
            "eligible": bool(range_peer_cohort.get("eligible") and range_value),
        }
    except Exception:
        range_peer_cohort = None
    if not selection.get("eligible"):
        return {
            "status": "insufficient_peers",
            "peers": peers_raw,
            "peer_selector": selection.get("selector"),
            "peer_exclusions": selection.get("dropped") or [],
            "reason": selection.get("reason"),
            "range_peer_cohort": range_peer_cohort,
            "range_peer_scenario": range_peer_scenario,
        }
    peer_profiles = selection.get("profiles") or {}
    if len(peer_profiles) < 3:
        return {"status": "insufficient_peers", "peers": list(peer_profiles.keys())}

    def _med(field):
        vals = [prof.get(field) for prof in peer_profiles.values() if prof.get(field) is not None]
        return median(vals) if vals else None

    try:
        self_prof = get_profile(ticker) or {}
    except Exception:
        self_prof = {}

    # V3.46.0 — peer TTM ratio medians for valuation archetype shadow (#3).
    # 2 FMP calls per ticker first run (key-metrics-ttm + ratios-ttm), 24h cached.
    peer_ratios = {}
    for p in peer_profiles:
        try:
            r = get_ratios_ttm(p)
        except Exception:
            r = None
        if r:
            peer_ratios[p] = r

    def _med_ratio(field):
        vals = [r.get(field) for r in peer_ratios.values()
                if isinstance(r.get(field), (int, float)) and r.get(field) > 0]
        return median(vals) if vals else None

    try:
        self_ratios = get_ratios_ttm(ticker)
    except Exception:
        self_ratios = None

    # V3.48.0 — /stable/profile 已無 peRatio（FMP stable migration 後 _med("peRatio")
    # 默默回 None，peer_pe_implied anchor 失效）→ 改用 peer ratios-ttm pe_ttm median
    pe_med = _med("peRatio")
    if pe_med is None:
        pe_vals = [r.get("pe_ttm") for r in peer_ratios.values()
                   if isinstance(r.get("pe_ttm"), (int, float)) and r.get("pe_ttm") > 0]
        pe_med = median(pe_vals) if pe_vals else None

    return {
        "status": "ok",
        "peers": list(peer_profiles.keys()),
        "peer_selector": selection.get("selector"),
        "peer_exclusions": selection.get("dropped") or [],
        "subject_industry": selection.get("subject_industry"),
        "peer_pe_median": pe_med,
        "peer_market_cap_median": _med("marketCap"),
        "peer_beta_median": _med("beta"),
        "peer_sector": self_prof.get("sector") or self_prof.get("industry"),
        "peer_ev_ebitda_median": _med_ratio("ev_to_ebitda_ttm"),
        "peer_ev_sales_median":  _med_ratio("ev_to_sales_ttm"),
        "peer_pb_median":        _med_ratio("price_to_book_ttm"),
        "peer_ratios_n":         len(peer_ratios),
        "self_ratios_ttm":       self_ratios,
        "range_peer_cohort":     range_peer_cohort,
        "range_peer_scenario":   range_peer_scenario,
    }


# ---------------------------------------------------------------- FMP_SUPP_BUNDLE
def load_supp_bundle(ticker):
    sys.path.insert(0, REPO)
    try:
        from skills._shared.fmp_supplementary import get_supplementary_bundle
    except Exception as e:
        return {"status": "unavailable", "reason": f"import failed: {e}"}
    try:
        b = get_supplementary_bundle(ticker)
    except Exception as e:
        return {"status": "unavailable", "reason": f"fetch failed: {e}"}
    if b is None:
        return {"status": "unavailable", "reason": "no API key + no cache"}
    return b


# ---------------------------------------------------------------- main
def build(ticker, run_validator=True, prewarm_earnings=True):
    ticker = ticker.upper()
    phase0_source, stale_h, phase0 = load_phase0(ticker)
    out = {
        "ticker": ticker,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "phase0_source": phase0_source,
        "phase0_stale_hours": stale_h,
        "phase0": phase0,
        "phase0_validator_rc": validate_phase0_rc(ticker) if run_validator else None,
        "bundles": {},
        "bundles_loaded": {},
    }
    tdb = load_ticker_data_bundle(ticker)
    # Refresh before the read, so a same-day earnings release is in the bundle that
    # Phase 1.5 freezes its valuation_pack against. Status is surfaced for audit.
    if prewarm_earnings:
        out["earnings_prewarm"], _refreshed = prewarm_earnings_cache(ticker)
        # Strictly after the earnings refresh — forecast.py reads that cache — and it
        # needs to know whether a new quarter landed, because its own TTL can't tell.
        out["forecaster_prewarm"] = prewarm_forecaster_cache(ticker, _refreshed)
    else:
        out["earnings_prewarm"] = out["forecaster_prewarm"] = "disabled"
    eab = load_earnings_bundle(ticker)
    pb = load_peer_bundle(ticker)
    fsb = load_supp_bundle(ticker)
    out["bundles"] = {
        "ticker_data_bundle": tdb,
        "earnings_analyst_bundle": eab,
        "peer_bundle": pb,
        "fmp_supp_bundle": fsb,
    }
    out["bundles_loaded"] = {
        "ticker_data_bundle": tdb.get("status", "ok") if isinstance(tdb, dict) else "unavailable",
        "earnings_analyst_bundle": eab.get("status", "ok") if isinstance(eab, dict) else "not_available",
        "peer_bundle": pb.get("status", "ok") if isinstance(pb, dict) else "unavailable",
        "fmp_supp_bundle": "ok" if isinstance(fsb, dict) and "status" not in fsb else
                           (fsb.get("status", "unavailable") if isinstance(fsb, dict) else "unavailable"),
    }
    return out


def main():
    ap = argparse.ArgumentParser(description="Phase 0/1 single-call data aggregator (0 LLM)")
    ap.add_argument("ticker")
    ap.add_argument("--out", help="also write JSON to this path")
    ap.add_argument("--no-validator", action="store_true", help="skip validate_phase0 subprocess")
    ap.add_argument("--no-prewarm", action="store_true",
                    help="skip the earnings-analyst cache refresh (offline / zero-FMP runs)")
    args = ap.parse_args()
    out = build(args.ticker, run_validator=not args.no_validator,
                prewarm_earnings=not args.no_prewarm)
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
        print(f"[phase1_factpack] wrote {args.out}", file=sys.stderr)
    print(text)


if __name__ == "__main__":
    main()
