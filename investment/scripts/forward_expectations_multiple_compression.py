#!/usr/bin/env python3
"""Growth-tier multiple compression for the future price range (EXP-3.4).

The historical multiple-regime anchor (EXP-R1) holds the ticker's PAST valuation
multiple. For a maturing franchise that is what produces absurd targets: applying a
hyper-growth-era P/E (e.g. NVDA ~57x, ARM ~151x) onto a horizon EPS that consensus
says has already plateaued double-counts optimism.

This layer compresses the historical multiple toward a level the FORWARD growth
justifies. It is deterministic and transparent:

  effective = historical × growth_factor        (dimension-agnostic; P/E, P/S, P/FCF)
  for P/E only: effective = min(effective, absolute_pe_ceiling[tier])

The forward growth signal is the consensus estimate-window CAGR (terminal growth a
horizon-year buyer would actually pay for). Both the historical band and the applied
band are kept so the haircut is auditable. SHADOW ONLY — feeds no live decision.
"""
from __future__ import annotations

import argparse
import json
import math
import sys

ENGINE_VERSION = "forward_expectations_multiple_compression.py v1.0"

# (min_growth, tier_name, compression_factor, absolute_pe_ceiling)
# factor scales the whole historical band; pe_ceiling caps P/E absolute insanity.
GROWTH_TIERS = [
    (0.25, "hypergrowth", 1.00, 55),
    (0.15, "growth", 0.82, 45),
    (0.07, "moderate", 0.66, 35),
    (0.03, "slowing", 0.52, 28),
    (None, "mature", 0.40, 22),
]
# which consensus CAGR drives each metric's compression
METRIC_GROWTH = {"pe": "eps", "ps": "revenue", "pfcf": "eps"}


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _tier(growth):
    for threshold, name, factor, pe_ceiling in GROWTH_TIERS:
        if threshold is None or growth >= threshold:
            return name, factor, pe_ceiling
    return GROWTH_TIERS[-1][1:]


def compress_band(hist_band: dict, growth, metric: str) -> dict:
    """Return a band with compressed p25/p50/p75, preserving the historical band for audit."""
    if not isinstance(hist_band, dict) or not hist_band.get("usable"):
        return dict(hist_band or {})
    g = _num(growth)
    if g is None:
        return {**hist_band, "compressed": False, "compression_reason": "no_forward_growth_signal"}
    h25, h50, h75 = hist_band.get("p25"), hist_band.get("p50"), hist_band.get("p75")
    if not all(_num(x) for x in (h25, h50, h75)):
        return {**hist_band, "compressed": False, "compression_reason": "incomplete_historical_band"}
    tier_name, factor, pe_ceiling = _tier(g)
    applied = {"p25": h25 * factor, "p50": h50 * factor, "p75": h75 * factor}
    pe_capped = False
    # P/E absolute ceiling: cap the MEDIAN and scale the band proportionally so the
    # historical dispersion shape survives (per-percentile min() would collapse it).
    if metric == "pe" and applied["p50"] > pe_ceiling:
        ratio = pe_ceiling / applied["p50"]
        applied = {k: v * ratio for k, v in applied.items()}
        pe_capped = True
    compressed = applied["p50"] < h50 - 1e-9
    return {
        **hist_band,
        "p25": round(applied["p25"], 4),
        "p50": round(applied["p50"], 4),
        "p75": round(applied["p75"], 4),
        "compressed": compressed,
        "growth_tier": tier_name,
        "growth_used": round(g, 4),
        "compression_factor": factor,
        "pe_absolute_ceiling": pe_ceiling if metric == "pe" else None,
        "pe_ceiling_applied": pe_capped,
        "historical_band": {"p25": round(h25, 4), "p50": round(h50, 4), "p75": round(h75, 4)},
        "method": "historical_regime_growth_compressed",
    }


def compress_anchor(multiple_anchor: dict, growth_signals: dict) -> dict:
    """growth_signals: {'eps': consensus_eps_cagr, 'revenue': consensus_revenue_cagr}.
    Returns a new anchor whose by_metric bands are growth-compressed (historical kept)."""
    if not isinstance(multiple_anchor, dict):
        return multiple_anchor
    by_metric = multiple_anchor.get("by_metric") or {}
    out_metrics, any_compressed = {}, False
    for metric, band in by_metric.items():
        growth_key = METRIC_GROWTH.get(metric)
        growth = (growth_signals or {}).get(growth_key) if growth_key else None
        compressed_band = compress_band(band, growth, metric)
        out_metrics[metric] = compressed_band
        if compressed_band.get("compressed"):
            any_compressed = True
    return {
        **multiple_anchor,
        "by_metric": out_metrics,
        "compression": {
            "engine": ENGINE_VERSION,
            "applied": any_compressed,
            "growth_signals": {k: (round(v, 4) if _num(v) is not None else None)
                               for k, v in (growth_signals or {}).items()},
            "policy": "Historical multiple compressed toward forward-growth-justified level; shadow only.",
        },
    }


def main():
    ap = argparse.ArgumentParser(description="Growth-tier multiple compression (EXP-3.4)")
    ap.add_argument("--snapshot-file", required=True, help="a Forward Expectations snapshot")
    args = ap.parse_args()
    with open(args.snapshot_file, encoding="utf-8") as handle:
        snap = json.load(handle)
    cons = snap.get("consensus_lane") or {}
    result = compress_anchor(snap.get("multiple_anchor") or {},
                             {"eps": cons.get("eps_cagr"), "revenue": cons.get("revenue_cagr")})
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
