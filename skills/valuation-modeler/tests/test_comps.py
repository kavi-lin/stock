#!/usr/bin/env python3
"""test_comps.py — valuation-modeler comps engine test.

純 stdlib、零網路：以 fixture universe dict 直接呼叫 build_comps_table /
comps_implied_anchor（fetch_peer_metrics 不碰）。
Run: python3 skills/valuation-modeler/tests/test_comps.py
"""
import json
import os
import sys
import tempfile
import types
from pathlib import Path

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(TESTS_DIR), "scripts"))

# comps._eps_growth imports fmp_client lazily; register a stub first so the
# test stays offline.
_EPS_CASES: dict = {}
_fake_fmp = types.ModuleType("fmp_client")
_fake_fmp.analyst_estimates = lambda ticker, no_cache=False: _EPS_CASES.get(ticker, [])
sys.modules.setdefault("fmp_client", _fake_fmp)

import comps  # noqa: E402
import peer_cohorts  # noqa: E402
from skills._shared import company_context  # noqa: E402

FAILS = []


def eq(label, got, want, tol=0.01):
    ok = (got == want) if not isinstance(want, float) else (
        got is not None and abs(got - want) <= tol)
    if not ok:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


# ── fixture universe（手算友善數字） ──────────────────────────────────────
# subject: EV 1000, net debt 100 → mcap 900; shares 10 → price 90
# self multiples: pe 30, ev_ebitda 20 (EBITDA=50), ev_sales 10 (Sales=100),
# growth 0.20 → peg 1.5
SELF = {
    "symbol": "SUBJ", "name": "Subject Co", "market_cap": 900.0, "price": 90.0,
    "pe": 30.0, "ev_ebitda": 20.0, "ev_sales": 10.0,
    "eps_growth_fwd": 0.20, "peg": 1.5,
    "enterprise_value": 1000.0, "net_debt": 100.0, "shares": 10.0,
}
# 5 peers: ev_ebitda values 16,18,20,22,24 (median 20); ev_sales 6,8,10,12,14
# (median 10); pe 20,25,30,35,40 (median 30); peg 1.0,1.25,1.5,1.75,2.0 (median 1.5)
PEERS = {}
for i, (pe, eve, evs, peg) in enumerate(
        [(20, 16, 6, 1.0), (25, 18, 8, 1.25), (30, 20, 10, 1.5),
         (35, 22, 12, 1.75), (40, 24, 14, 2.0)]):
    PEERS[f"P{i}"] = {"name": f"Peer {i}", "market_cap": 500.0, "pe": float(pe),
                      "ev_ebitda": float(eve), "ev_sales": float(evs),
                      "eps_growth_fwd": 0.20, "peg": float(peg)}

DATA = {"self": SELF, "peers": PEERS, "dropped": [], "peer_source": "fixture"}

T = comps.build_comps_table(DATA)

# peer medians equal self multiples → implied ≈ current structure
# ev_ebitda: EBITDA = 1000/20 = 50; equity = 20×50 − 100 = 900; /10 = 90
eq("ev_ebitda.implied", T["metrics"]["ev_ebitda"]["implied_value"], 90.0)
eq("ev_ebitda.median", T["metrics"]["ev_ebitda"]["quartiles"]["median"], 20.0)
eq("ev_ebitda.n", T["metrics"]["ev_ebitda"]["n"], 5)
# ev_sales: Sales = 100; equity = 10×100 − 100 = 900; /10 = 90
eq("ev_sales.implied", T["metrics"]["ev_sales"]["implied_value"], 90.0)
# pe: eps = 90/30 = 3; implied = 30×3 = 90
eq("pe.implied", T["metrics"]["pe"]["implied_value"], 90.0)
# peg: implied_pe = 1.5×0.20×100 = 30 → ×3 = 90
eq("peg.implied", T["metrics"]["peg"]["implied_value"], 90.0)

anchor, detail = comps.comps_implied_anchor(T)
eq("anchor.value", anchor, 90.0)
eq("anchor.pe_excluded", "pe" not in detail["used_metrics"], True)
eq("anchor.metrics_n", len(detail["used_metrics"]), 3)

# ── peer median above self → implied above price ─────────────────────────
rich = {sym: dict(p, ev_ebitda=p["ev_ebitda"] * 1.5) for sym, p in PEERS.items()}
T2 = comps.build_comps_table({"self": SELF, "peers": rich, "dropped": [], "peer_source": "fixture"})
# median 30: equity = 30×50 − 100 = 1400; /10 = 140
eq("rich.implied", T2["metrics"]["ev_ebitda"]["implied_value"], 140.0)

# ── IQR winsorize: single wild outlier barely moves the median ───────────
wild = {sym: dict(p) for sym, p in PEERS.items()}
wild["P4"]["ev_sales"] = 400.0
T3 = comps.build_comps_table({"self": SELF, "peers": wild, "dropped": [], "peer_source": "fixture"})
eq("winsor.median_stable", T3["metrics"]["ev_sales"]["quartiles"]["median"], 10.0)

# ── <3 peers per metric → metric excluded ────────────────────────────────
sparse = {sym: dict(p, ev_sales=None) for sym, p in list(PEERS.items())[:2]}
sparse.update({sym: dict(p) for sym, p in list(PEERS.items())[2:]})
for sym in list(sparse)[:3]:
    sparse[sym]["ev_ebitda"] = None
T4 = comps.build_comps_table({"self": SELF, "peers": sparse, "dropped": [], "peer_source": "fixture"})
eq("sparse.excluded", T4["metrics"]["ev_ebitda"]["implied_value"], None)
eq("sparse.reason", "peers" in (T4["metrics"]["ev_ebitda"].get("excluded_reason") or ""), True)

# ── anchor needs ≥2 metrics ──────────────────────────────────────────────
only_one = {sym: {"name": p["name"], "market_cap": 500.0, "pe": None,
                  "ev_ebitda": p["ev_ebitda"], "ev_sales": None,
                  "eps_growth_fwd": None, "peg": None} for sym, p in PEERS.items()}
T5 = comps.build_comps_table({"self": SELF, "peers": only_one, "dropped": [], "peer_source": "fixture"})
anchor5, detail5 = comps.comps_implied_anchor(T5)
eq("anchor.min_metrics", anchor5, None)
eq("anchor.min_metrics_reason", "usable metrics" in detail5.get("reason", ""), True)

# ── negative implied equity → null ───────────────────────────────────────
heavy_debt = dict(SELF, net_debt=5000.0)
T6 = comps.build_comps_table({"self": heavy_debt, "peers": PEERS, "dropped": [], "peer_source": "fixture"})
eq("negeq.null", T6["metrics"]["ev_ebitda"]["implied_value"], None)

# ── helpers ──────────────────────────────────────────────────────────────
eq("winsorize.noop_small", comps._iqr_winsorize([1.0, 2.0, 3.0]), [1.0, 2.0, 3.0])
q = comps._quartiles([16.0, 18.0, 20.0, 22.0, 24.0])
eq("quartiles.median", q["median"], 20.0)
eq("quartiles.small_n", comps._quartiles([5.0, 7.0])["q1"], None)

# Shared selector excludes broad FMP peers outside the subject's exact industry.
_orig_profile = company_context.get_profile
_orig_peers = company_context.get_peers
_orig_bulk = company_context.get_profiles_bulk
try:
    company_context.get_profile = lambda ticker: {"industry": "Semiconductors"}
    company_context.get_peers = lambda ticker: ["GOOD1", "SAAS", "GOOD2", "GOOD3"]
    company_context.get_profiles_bulk = lambda tickers: {
        "GOOD1": {"industry": "Semiconductors"},
        "GOOD2": {"industry": "Semiconductors"},
        "GOOD3": {"industry": "Semiconductors"},
        "SAAS": {"industry": "Software - Application"},
    }
    selection = company_context.select_valuation_peers("SUBJ")
finally:
    company_context.get_profile = _orig_profile
    company_context.get_peers = _orig_peers
    company_context.get_profiles_bulk = _orig_bulk
eq("selector.exact_industry", selection["peers"], ["GOOD1", "GOOD2", "GOOD3"])
eq("selector.eligible_three", selection["eligible"], True)
eq("selector.exclusion_reason", selection["dropped"][0]["reason"], "industry_mismatch")

# Curated discovery supplies candidates only; all P/E values still come from
# the deterministic ratio loader and remain range-only.
fixture_pes = {"SNDK": 39.8436, "WDC": 29.1514, "STX": 58.8810}
cohort = peer_cohorts.build_pe_cohort(
    "MU",
    ratios_loader=lambda ticker: {"pe_ttm": fixture_pes.get(ticker)},
    profile_loader=lambda ticker: {"companyName": ticker},
    as_of="2026-08-02",
)
eq("cohort.eligible_three", cohort["eligible"], True)
eq("cohort.count", cohort["peer_count"], 3)
eq("cohort.median", cohort["median_pe"], 39.8436)
eq("cohort.scope", cohort["scope"], "range_only")
eq("cohort.no_embedded_values",
   all(p["metric_source"] == "company_context.get_ratios_ttm"
       for p in cohort["peers"].values()), True)

range_data = {
    "self": dict(SELF, price=823.03, pe=18.367105556795355),
    "range_peer_cohort": cohort,
}
scenario = comps.peer_pe_range_scenario(range_data)
eq("cohort.implied", scenario["value"], 1785.39)
eq("cohort.range_only", scenario["scope"], "range_only")

cohort_sparse = peer_cohorts.build_pe_cohort(
    "MU",
    ratios_loader=lambda ticker: {"pe_ttm": fixture_pes.get(ticker) if ticker != "STX" else None},
    profile_loader=lambda ticker: {"companyName": ticker},
)
eq("cohort.sparse_ineligible", cohort_sparse["eligible"], False)
eq("cohort.sparse_count", cohort_sparse["peer_count"], 2)
eq("cohort.sparse_no_median", cohort_sparse["median_pe"], None)

# ── 2026-08-02 review fixes ──────────────────────────────────────────────
# Fix 10: forward EPS growth uses the two nearest FUTURE fiscal years.
_EPS_CASES["PASTYEARS"] = [
    {"date": "2024-09-01", "epsAvg": 1.00},   # past FY — must not be used
    {"date": "2025-09-01", "epsAvg": 1.20},   # past FY (would imply 20%)
    {"date": "2027-09-01", "epsAvg": 1.25},
    {"date": "2028-09-01", "epsAvg": 1.30},   # true forward growth = 4%
]
eq("fix10.drops_past_years", comps._eps_growth("PASTYEARS", as_of="2026-08-02"), 0.04)
# A next-FY growth outside the PEG clamp returns None instead of silently
# substituting a later, faster-growing year pair.
_EPS_CASES["OUTOFCLAMP"] = [
    {"date": "2027-09-01", "epsAvg": 1.00},
    {"date": "2028-09-01", "epsAvg": 1.01},   # 1% — below the 2% floor
    {"date": "2029-09-01", "epsAvg": 1.50},   # 48.5% — must not be substituted
]
eq("fix10.no_silent_walk_forward", comps._eps_growth("OUTOFCLAMP", as_of="2026-08-02"), None)
_EPS_CASES["THIN"] = [{"date": "2027-09-01", "epsAvg": 1.00}]
eq("fix10.needs_two_forward_years", comps._eps_growth("THIN", as_of="2026-08-02"), None)

# Fix 11: cohort P/E dispersion is published (3 names are too few to winsorize)
# and an unreadable schema is reported rather than read as "no cohort".
eq("fix11.pe_min", cohort["pe_min"], 29.1514)
eq("fix11.pe_max", cohort["pe_max"], 58.881)
_low, _high = peer_cohorts.implied_pe_range(range_data["self"], cohort)
eq("fix11.range_low", _low, 1306.27)
eq("fix11.range_high", _high, 2638.46)
eq("fix11.range_brackets_median", _low < scenario["value"] < _high, True)
eq("fix11.scenario_carries_range", scenario["value_low"], 1306.27)
eq("fix11.schema_ok", peer_cohorts.load_cohort("MU")[1], None)
with tempfile.TemporaryDirectory() as _td:
    _bad = Path(_td) / "peer_cohorts.json"
    _bad.write_text(json.dumps({"schema": "valuation_peer_cohorts.v99",
                                "cohorts": {"MU": {"name": "x"}}}))
    eq("fix11.schema_guard", peer_cohorts.load_cohort("MU", _bad)[1],
       "unsupported_cohort_schema:valuation_peer_cohorts.v99")
    eq("fix11.schema_guard_no_cohort", peer_cohorts.load_cohort("MU", _bad)[0], None)

# ── render ───────────────────────────────────────────────────────────────
payload = {"ticker": "SUBJ", "asof": "2026-01-01", "comps_implied_value": anchor,
           "anchor_detail": detail, "universe": dict(DATA, peer_count_used=5),
           "table": T, "degraded": True,
           "model_eligibility": {"eligible": False,
                                 "reason": "insufficient_exact_industry_peers"},
           "peer_pe_range_scenario": scenario}
md = comps.render_md(payload)
eq("md.header", md.startswith("# SUBJ"), True)
eq("md.subject_bold", "**SUBJ**" in md, True)
eq("md.anchor_note", "peer_pe_implied" in md, True)
eq("md.range_scenario", "Range-only peer P/E scenario" in md, True)
eq("md.range_not_primary", "not the primary FV" in md, True)
eq("md.range_shows_spread", "1306.27" in md and "2638.46" in md, True)

# Fix 12: with a healthy canonical peer set the second peer table is suppressed
# so a reader cannot blend two universes; the payload still carries it.
md_ok = comps.render_md(dict(payload, degraded=False,
                             model_eligibility={"eligible": True, "reason": None}))
eq("fix12.range_body_suppressed", "not the primary FV" in md_ok, False)
eq("fix12.range_suppression_noted", "略過渲染" in md_ok, True)

# ──────────────────────────────────────────────────────────────────────────
# V4.125.0 — "no usable peer anchor" is an ANSWER, not an execution failure.
#
# Seeded regression: `sys.exit(0 if not payload["degraded"] else 1)` mapped a
# complete, correct verdict (comps_implied_value=null, reason=
# fewer_than_3_business_similar_peers) onto rc=1, which collides with V4.116.1's
# gate discipline ("mandatory script rc≠0 → halt"). The PM then decided halt-vs-
# degrade on the spot and decided differently run to run: 2026-08-10 NVDA 08:36
# halted / 08:43 continued / META 09:03 halted / 09:14 continued. Restore the
# conditional exit and this goes red.
import contextlib  # noqa: E402
import io  # noqa: E402

_CACHE_DIR = Path(comps.SCRIPT_DIR).parent / "cache"
_orig_build = comps.build_payload
_orig_argv = sys.argv[:]


def _exit_code_for(degraded):
    """Run comps.main() over a stubbed payload; return its exit code."""
    tk = "ZZCOMPS"
    comps.build_payload = lambda ticker, no_cache=False: {
        "ticker": tk, "asof": "2026-08-10",
        "comps_implied_value": None if degraded else 123.4,
        "anchor_detail": {}, "universe": {}, "table": [],
        "peer_pe_range_scenario": None,
        "model_eligibility": {
            "eligible": not degraded,
            "reason": "fewer_than_3_business_similar_peers" if degraded else None},
        "degraded": degraded,
    }
    sys.argv = ["comps.py", tk, "--json-only"]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            comps.main()
    except SystemExit as e:
        return e.code if e.code is not None else 0
    finally:
        comps.build_payload = _orig_build
        sys.argv = _orig_argv[:]
        with contextlib.suppress(OSError):
            os.remove(_CACHE_DIR / f"{tk}_comps_payload.json")
    return None


eq("exit.degraded_is_not_a_failure", _exit_code_for(True), 0)
eq("exit.healthy", _exit_code_for(False), 0)

# ──────────────────────────────────────────────────────────────────────────
if FAILS:
    print(f"✗ {len(FAILS)} failure(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ test_comps: all pass")
