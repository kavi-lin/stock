#!/usr/bin/env python3
"""Base-rate cohort library for Forward Expectations (EXP-3.2).

The base-rate lane is the anti-fantasy ceiling: "what growth do comparable businesses
actually achieve?" A raw FMP peer list is not a cohort — it mixes growth stages, margin
profiles, and sizes, and invites post-hoc cherry-picking. This module selects a cohort
by EXPLICIT, RECORDED criteria (sector, growth stage, margin profile, size) with fixed
tolerances, and stores the selection rationale + per-member match reasons so the choice
is reproducible and auditable.

Pure deterministic engine (0 LLM, 0 network). The caller assembles candidate
classifications; this module only classifies and matches.
"""
from __future__ import annotations

import math

ENGINE_VERSION = "forward_expectations_cohort.py v1.0"
MIN_COHORT_MEMBERS = 3
MIN_DIM_MATCHES = 2  # of the 3 non-sector dims, with +/-1 tier adjacency

# Ordered tiers so adjacency (+/-1) is meaningful.
GROWTH_TIERS = ["declining", "mature", "growth", "hypergrowth"]
MARGIN_TIERS = ["low", "mid", "high"]
SIZE_TIERS = ["small", "mid", "large", "mega"]


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _pct(vals, q):
    s = sorted(vals)
    if not s:
        return None
    k = (len(s) - 1) * q
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def _growth_tier(rev_yoy):
    v = _num(rev_yoy)
    if v is None:
        return None
    if v >= 0.30:
        return "hypergrowth"
    if v >= 0.10:
        return "growth"
    if v >= 0.0:
        return "mature"
    return "declining"


def _margin_tier(gross_margin):
    v = _num(gross_margin)
    if v is None:
        return None
    if v >= 0.60:
        return "high"
    if v >= 0.35:
        return "mid"
    return "low"


def _size_tier(market_cap):
    v = _num(market_cap)
    if v is None:
        return None
    if v >= 2e11:
        return "mega"
    if v >= 1e10:
        return "large"
    if v >= 2e9:
        return "mid"
    return "small"


def classify(sector, market_cap, rev_yoy, gross_margin) -> dict:
    return {
        "sector": sector or None,
        "growth_stage": _growth_tier(rev_yoy),
        "margin_tier": _margin_tier(gross_margin),
        "size_tier": _size_tier(market_cap),
    }


def _adjacent(tiers, a, b):
    if a is None or b is None or a not in tiers or b not in tiers:
        return False
    return abs(tiers.index(a) - tiers.index(b)) <= 1


def match_member(subject_key: dict, member_key: dict) -> dict:
    """Sector must match exactly; >=MIN_DIM_MATCHES of the 3 graded dims must be within
    +/-1 tier. Returns the verdict plus the reasons so the selection is auditable."""
    sector_ok = bool(subject_key.get("sector")) and subject_key.get("sector") == member_key.get("sector")
    dims = [
        ("growth_stage", GROWTH_TIERS),
        ("margin_tier", MARGIN_TIERS),
        ("size_tier", SIZE_TIERS),
    ]
    reasons, mismatches = [], []
    dim_hits = 0
    for name, tiers in dims:
        if _adjacent(tiers, subject_key.get(name), member_key.get(name)):
            dim_hits += 1
            reasons.append(f"{name}:{member_key.get(name)}~{subject_key.get(name)}")
        else:
            mismatches.append(f"{name}:{member_key.get(name)}!={subject_key.get(name)}")
    matched = sector_ok and dim_hits >= MIN_DIM_MATCHES
    return {
        "matched": matched,
        "sector_match": sector_ok,
        "dim_matches": dim_hits,
        "match_reasons": reasons,
        "mismatches": ([] if sector_ok else ["sector"]) + mismatches,
    }


def build_cohort(subject: dict, candidates: list[dict], min_members: int = MIN_COHORT_MEMBERS) -> dict:
    """subject: {ticker, sector, market_cap, rev_yoy, gross_margin}.
    candidates: [{ticker, sector, market_cap, rev_yoy, gross_margin, revenue_cagr}]."""
    subject_key = classify(subject.get("sector"), subject.get("market_cap"),
                           subject.get("rev_yoy"), subject.get("gross_margin"))
    rationale = {
        "criteria": ["sector(exact)", "growth_stage(+/-1)", "margin_tier(+/-1)", "size_tier(+/-1)"],
        "rule": f"sector must match and >={min_members} members each matching >={MIN_DIM_MATCHES}/3 graded dims",
        "subject_classification": subject_key,
        "tolerances": {"dim_adjacency": 1, "min_dim_matches": MIN_DIM_MATCHES},
        "anti_cherry_pick": "Criteria and tolerances are fixed before selection; every member records its match reasons.",
    }
    members, considered = [], 0
    for cand in candidates or []:
        cagr = _num(cand.get("revenue_cagr"))
        if not cand.get("ticker") or cagr is None:
            continue
        considered += 1
        member_key = classify(cand.get("sector"), cand.get("market_cap"),
                             cand.get("rev_yoy"), cand.get("gross_margin"))
        verdict = match_member(subject_key, member_key)
        if verdict["matched"]:
            members.append({
                "ticker": cand["ticker"],
                "revenue_cagr": round(cagr, 4),
                "classification": member_key,
                "match_reasons": verdict["match_reasons"],
                "dim_matches": verdict["dim_matches"],
            })
    base = {
        "engine": ENGINE_VERSION,
        "available": False,
        "subject_classification": subject_key,
        "rationale": rationale,
        "candidates_considered": considered,
        "members": members,
        "member_count": len(members),
        "distribution": {"median": None, "p25": None, "p75": None},
    }
    if len(members) < min_members:
        return {**base, "status": "insufficient_cohort",
                "note": f"only {len(members)} matched members (<{min_members}); caller should fall back to raw peers"}
    cagrs = [m["revenue_cagr"] for m in members]
    return {
        **base,
        "available": True,
        "status": "cohort_available",
        "distribution": {
            "median": round(_pct(cagrs, 0.50), 4),
            "p25": round(_pct(cagrs, 0.25), 4),
            "p75": round(_pct(cagrs, 0.75), 4),
        },
    }
