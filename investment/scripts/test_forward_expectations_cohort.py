#!/usr/bin/env python3
"""Golden fixtures for the Forward Expectations base-rate cohort engine (EXP-3.2)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_cohort as co  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}: got {got!r}, want {want!r}")


# ── classification tiers ───────────────────────────────────────────────────────
check("growth hypergrowth", co.classify("Tech", 5e11, 0.40, 0.90)["growth_stage"], "hypergrowth")
check("growth mature", co.classify("Tech", 5e11, 0.05, 0.90)["growth_stage"], "mature")
check("growth declining", co.classify("Tech", 5e11, -0.10, 0.90)["growth_stage"], "declining")
check("margin high", co.classify("Tech", 5e11, 0.4, 0.70)["margin_tier"], "high")
check("margin low", co.classify("Tech", 5e11, 0.4, 0.20)["margin_tier"], "low")
check("size mega", co.classify("Tech", 5e11, 0.4, 0.7)["size_tier"], "mega")
check("size mid", co.classify("Tech", 5e9, 0.4, 0.7)["size_tier"], "mid")

# ── match: sector required ─────────────────────────────────────────────────────
subj = {"sector": "Technology", "growth_stage": "hypergrowth", "margin_tier": "high", "size_tier": "mega"}
diff_sector = {"sector": "Energy", "growth_stage": "hypergrowth", "margin_tier": "high", "size_tier": "mega"}
check("sector mismatch rejected", co.match_member(subj, diff_sector)["matched"], False)
check("sector mismatch reason", "sector" in co.match_member(subj, diff_sector)["mismatches"], True)

# ── match: adjacency counts (>=2/3) ────────────────────────────────────────────
adj = {"sector": "Technology", "growth_stage": "growth", "margin_tier": "high", "size_tier": "large"}  # all +/-1
check("3 adjacent dims -> match", co.match_member(subj, adj)["matched"], True)
check("dim_matches=3", co.match_member(subj, adj)["dim_matches"], 3)
one_dim = {"sector": "Technology", "growth_stage": "declining", "margin_tier": "low", "size_tier": "mega"}  # only size
check("only 1 dim match -> reject", co.match_member(subj, one_dim)["matched"], False)

# ── build_cohort: >=3 matched -> distribution, members carry reasons ───────────
SUBJECT = {"ticker": "ARM", "sector": "Technology", "market_cap": 4e11, "rev_yoy": 0.35, "gross_margin": 0.95}
candidates = [
    {"ticker": "NVDA", "sector": "Technology", "market_cap": 3e12, "rev_yoy": 0.40, "gross_margin": 0.75, "revenue_cagr": 0.50},
    {"ticker": "AVGO", "sector": "Technology", "market_cap": 8e11, "rev_yoy": 0.30, "gross_margin": 0.65, "revenue_cagr": 0.20},
    {"ticker": "AMD", "sector": "Technology", "market_cap": 2.5e11, "rev_yoy": 0.25, "gross_margin": 0.50, "revenue_cagr": 0.30},
    {"ticker": "XOM", "sector": "Energy", "market_cap": 5e11, "rev_yoy": 0.05, "gross_margin": 0.30, "revenue_cagr": 0.04},
    {"ticker": "BADCAGR", "sector": "Technology", "market_cap": 4e11, "rev_yoy": 0.35, "gross_margin": 0.9, "revenue_cagr": None},
]
cohort = co.build_cohort(SUBJECT, candidates)
check("cohort available", cohort["available"], True)
check("cohort excludes Energy", "XOM" not in [m["ticker"] for m in cohort["members"]], True)
check("cohort excludes None-cagr", "BADCAGR" not in [m["ticker"] for m in cohort["members"]], True)
check("cohort member_count 3", cohort["member_count"], 3)
check("cohort median = median(0.50,0.20,0.30)=0.30", cohort["distribution"]["median"], 0.30)
check("cohort members carry match_reasons", bool(cohort["members"][0]["match_reasons"]), True)
check("cohort records anti-cherry-pick rationale", "anti_cherry_pick" in cohort["rationale"], True)
check("cohort records subject classification", cohort["rationale"]["subject_classification"]["sector"], "Technology")

# ── insufficient cohort -> degrade with note (caller falls back) ───────────────
thin = co.build_cohort(SUBJECT, candidates[:1] + [candidates[3]])  # 1 tech + 1 energy
check("insufficient status", thin["status"], "insufficient_cohort")
check("insufficient not available", thin["available"], False)
check("insufficient member_count 1", thin["member_count"], 1)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
