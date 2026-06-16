#!/usr/bin/env python3
"""Margin-normalization path for the future price range (EXP-3.4b).

The forward bridge holds the current net margin constant to the horizon. For a company
earning a SUPERNORMAL margin (NVDA ~60%, driven by AI-accelerator scarcity + CUDA /
networking / rack-scale system lock-in + hyperscaler urgency), freezing that to 2031
silently bakes monopoly economics into the headline EPS.

This layer does NOT mechanically revert to a sector mean — that would underestimate a
genuine platform franchise. Instead it builds a bear/base/bull MARGIN PATH using
durable-platform RETENTION factors (how much of today's premium margin persists), with
a floor at a discount to the company's own recent margin so a structurally high-margin
franchise is not over-normalized. It then bridges:

  forward revenue (scenario) × scenario net margin → normalized net income
    → normalized EPS → valuation input

Only triggers when the held margin is supernormal. SHADOW ONLY — feeds no live decision.
"""
from __future__ import annotations

import argparse
import json
import math
import sys

ENGINE_VERSION = "forward_expectations_margin_normalization.py v1.0"

MARGIN_ELEVATED = 0.40          # only normalize net margins above this (supernormal)
# Durable-platform RETENTION of today's margin — deliberately generous, NOT sector mean reversion.
RETENTION = {"bear": 0.62, "base": 0.80, "bull": 1.00}
OWN_HISTORY_FLOOR_FRAC = 0.85   # base/bull margin not pushed below own recent median × this


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _pos(value):
    value = _num(value)
    return value if value is not None and value > 0 else None


def _eps(net_income, shares):
    net_income, shares = _num(net_income), _pos(shares)
    return round(net_income / shares, 4) if (net_income is not None and shares) else None


def build_margin_normalization(financial_bridge: dict, own_hist_net_margin=None) -> dict:
    hc = (financial_bridge or {}).get("historical_conversion") or {}
    rows = [r for r in (financial_bridge or {}).get("rows") or [] if isinstance(r, dict)]
    held = _num(hc.get("net_margin"))
    shares = _pos(hc.get("diluted_share_count"))
    base = {
        "engine": ENGINE_VERSION,
        "applied": False,
        "shadow_only": True,
        "held_net_margin": round(held, 4) if held is not None else None,
        "elevated_threshold": MARGIN_ELEVATED,
        "policy": "Durable-platform retention margin path; NOT sector mean reversion; shadow only.",
    }
    if held is None or shares is None or not rows:
        return {**base, "reason": "insufficient_bridge_inputs"}
    if held <= MARGIN_ELEVATED:
        return {**base, "reason": "margin_not_supernormal_no_normalization"}

    row = sorted(rows, key=lambda r: r.get("date") or "")[-1]
    rev = row.get("revenue") or {}
    rev_low, rev_base, rev_high = _pos(rev.get("low")), _pos(rev.get("point")), _pos(rev.get("high"))
    if rev_base is None:
        return {**base, "reason": "no_forward_revenue"}
    rev_low = rev_low or rev_base
    rev_high = rev_high or rev_base

    floor = (own_hist_net_margin * OWN_HISTORY_FLOOR_FRAC) if _pos(own_hist_net_margin) else None
    margins = {
        "bear": held * RETENTION["bear"],
        "base": max(held * RETENTION["base"], floor) if floor else held * RETENTION["base"],
        "bull": held * RETENTION["bull"],
    }
    rev_by_case = {"bear": rev_low, "base": rev_base, "bull": rev_high}
    norm_ni = {c: rev_by_case[c] * margins[c] for c in ("bear", "base", "bull")}
    norm_eps = {c: _eps(norm_ni[c], shares) for c in ("bear", "base", "bull")}

    return {
        **base,
        "applied": True,
        "reason": None,
        "own_recent_net_margin": round(own_hist_net_margin, 4) if _pos(own_hist_net_margin) else None,
        "floor_net_margin": round(floor, 4) if floor else None,
        "retention_factors": RETENTION,
        "scenario_net_margins": {c: round(margins[c], 4) for c in margins},
        "scenario_revenue": {c: round(rev_by_case[c], 0) for c in rev_by_case},
        "normalized_net_income": {c: round(norm_ni[c], 0) for c in norm_ni},
        # mapped to the price-range EPS band: bear->low, base->point, bull->high
        "normalized_eps": {"low": norm_eps["bear"], "point": norm_eps["base"], "high": norm_eps["bull"]},
        "held_margin_eps_base": _eps(rev_base * held, shares),
        "method": "durable_platform_retention_path",
        "note": ("Bear/base/bull combine the analyst revenue envelope with a retained-margin "
                 "path; bull keeps today's margin (monopoly persists) and is a tail, not the base."),
    }


def main():
    ap = argparse.ArgumentParser(description="Margin-normalization path (EXP-3.4b)")
    ap.add_argument("--snapshot-file", required=True)
    args = ap.parse_args()
    with open(args.snapshot_file, encoding="utf-8") as handle:
        snap = json.load(handle)
    print(json.dumps(build_margin_normalization(snap.get("forward_financial_bridge") or {}),
                     ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
