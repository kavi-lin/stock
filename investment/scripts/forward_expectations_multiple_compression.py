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

ENGINE_VERSION = "forward_expectations_multiple_compression.py v1.1 (PEG terminal P/E)"

# (min_growth, tier_name, compression_factor, absolute_pe_ceiling)
# factor scales the whole historical band; pe_ceiling caps P/E absolute insanity.
# Used for P/S and P/FCF, and as a P/E fallback when no terminal-growth signal exists.
GROWTH_TIERS = [
    (0.25, "hypergrowth", 1.00, 55),
    (0.15, "growth", 0.82, 45),
    (0.07, "moderate", 0.66, 35),
    (0.03, "slowing", 0.52, 28),
    (None, "mature", 0.40, 22),
]
# which consensus CAGR drives each metric's compression
METRIC_GROWTH = {"pe": "eps", "ps": "revenue", "pfcf": "eps"}

# V4.40.0 — Terminal P/E is bound to TERMINAL growth (not the calendar year), PEG-style:
#   terminal_pe = clamp(PEG_MULTIPLIER * terminal_growth_pct, FLOOR, CEILING)
# This avoids two failure modes: (a) a flat ceiling (e.g. 35x) that wrongly caps durable
# AI-infra compounders (NVDA/AVGO/ARM/CRWV), and (b) freezing today's hypergrowth multiple
# forever. As forward growth decelerates the deserved P/E compresses automatically.
PEG_MULTIPLIER     = 2.2
TERMINAL_PE_FLOOR  = 20.0
TERMINAL_PE_CEILING = 60.0


def _terminal_growth(financial_bridge: dict):
    """Decelerated terminal revenue growth = YoY entering the terminal (horizon) year.
    Guard against far-year thin-coverage noise: if the terminal year re-accelerates vs the
    prior step (implausible for a maturing franchise) and its coverage is thin, fall back to
    the prior, better-grounded YoY (deceleration assumption). Returns (growth_fraction, basis)."""
    rows = [r for r in (financial_bridge or {}).get("rows") or [] if isinstance(r, dict)]
    rows = sorted(rows, key=lambda r: r.get("date") or "")
    revs = [(_num((r.get("revenue") or {}).get("point")), r) for r in rows]
    revs = [(v, r) for v, r in revs if v and v > 0]
    if len(revs) < 2:
        return None, "insufficient_rows"
    yoy = [(revs[i][0] / revs[i - 1][0] - 1.0, revs[i][1]) for i in range(1, len(revs))]
    term_g, term_row = yoy[-1]
    if len(yoy) >= 2:
        prior_g = yoy[-2][0]
        cov = (term_row.get("coverage") or {})
        counts = [c for c in (cov.get("num_analysts_revenue"), cov.get("num_analysts_eps"))
                  if isinstance(c, (int, float))]
        thin = bool(counts) and min(counts) < 20
        if term_g > prior_g and thin:
            return prior_g, "prior_year_yoy_terminal_noise_guard"
    return term_g, "terminal_year_yoy"


def _peg_terminal_pe(growth_fraction):
    g = _num(growth_fraction)
    if g is None:
        return None
    return max(TERMINAL_PE_FLOOR, min(TERMINAL_PE_CEILING, PEG_MULTIPLIER * g * 100.0))


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _tier(growth):
    for threshold, name, factor, pe_ceiling in GROWTH_TIERS:
        if threshold is None or growth >= threshold:
            return name, factor, pe_ceiling
    return GROWTH_TIERS[-1][1:]


def compress_band(hist_band: dict, growth, metric: str, terminal_pe=None) -> dict:
    """Return a band with compressed p25/p50/p75, preserving the historical band for audit.

    P/E (when a PEG terminal_pe is supplied): the median is pulled to min(historical, PEG)
    and the band scaled proportionally so the historical dispersion shape survives. The P/E
    is thus bound to TERMINAL growth, not the calendar year.
    P/S, P/FCF (and P/E fallback when terminal_pe is None): the legacy growth-tier factor."""
    if not isinstance(hist_band, dict) or not hist_band.get("usable"):
        return dict(hist_band or {})
    g = _num(growth)
    h25, h50, h75 = hist_band.get("p25"), hist_band.get("p50"), hist_band.get("p75")
    if not all(_num(x) for x in (h25, h50, h75)):
        return {**hist_band, "compressed": False, "compression_reason": "incomplete_historical_band"}

    if metric == "pe" and _num(terminal_pe) is not None:
        target_p50 = min(h50, terminal_pe)
        ratio = target_p50 / h50 if h50 else 1.0
        applied = {"p25": h25 * ratio, "p50": h50 * ratio, "p75": h75 * ratio}
        compressed = applied["p50"] < h50 - 1e-9
        return {
            **hist_band,
            "p25": round(applied["p25"], 4),
            "p50": round(applied["p50"], 4),
            "p75": round(applied["p75"], 4),
            "compressed": compressed,
            "growth_tier": "peg_terminal",
            "growth_used": round(g, 4) if g is not None else None,
            "compression_factor": round(ratio, 4),
            "terminal_pe_peg": round(terminal_pe, 4),
            "pe_ceiling_applied": bool(terminal_pe < h50 - 1e-9),
            "historical_band": {"p25": round(h25, 4), "p50": round(h50, 4), "p75": round(h75, 4)},
            "method": "peg_terminal_growth_bound",
        }

    if g is None:
        return {**hist_band, "compressed": False, "compression_reason": "no_forward_growth_signal"}
    tier_name, factor, pe_ceiling = _tier(g)
    applied = {"p25": h25 * factor, "p50": h50 * factor, "p75": h75 * factor}
    pe_capped = False
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


def compress_anchor(multiple_anchor: dict, growth_signals: dict, financial_bridge: dict = None) -> dict:
    """growth_signals: {'eps': consensus_eps_cagr, 'revenue': consensus_revenue_cagr}.
    financial_bridge (optional): supplies the per-FY revenue path → terminal growth → PEG P/E.
    Returns a new anchor whose by_metric bands are growth-compressed (historical kept)."""
    if not isinstance(multiple_anchor, dict):
        return multiple_anchor
    terminal_g, terminal_basis = _terminal_growth(financial_bridge or {})
    terminal_pe = _peg_terminal_pe(terminal_g)
    by_metric = multiple_anchor.get("by_metric") or {}
    out_metrics, any_compressed = {}, False
    for metric, band in by_metric.items():
        growth_key = METRIC_GROWTH.get(metric)
        growth = (growth_signals or {}).get(growth_key) if growth_key else None
        # P/E uses the terminal (decelerated) growth for the PEG bound; P/S keeps revenue CAGR.
        if metric == "pe" and terminal_pe is not None:
            compressed_band = compress_band(band, terminal_g, metric, terminal_pe=terminal_pe)
        else:
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
            "terminal_growth": round(terminal_g, 4) if _num(terminal_g) is not None else None,
            "terminal_growth_basis": terminal_basis,
            "terminal_pe_peg": round(terminal_pe, 4) if _num(terminal_pe) is not None else None,
            "peg_policy": f"terminal_pe = clamp({PEG_MULTIPLIER} * terminal_growth_pct, "
                          f"{TERMINAL_PE_FLOOR}, {TERMINAL_PE_CEILING}); bound to terminal growth, not year.",
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
                             {"eps": cons.get("eps_cagr"), "revenue": cons.get("revenue_cagr")},
                             snap.get("forward_financial_bridge") or {})
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
