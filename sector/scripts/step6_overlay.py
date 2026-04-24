"""
Step 6 — FRED Regime Overlay computation.

Deterministic Python helper for sector_protocol_main.md SCORING RUBRIC §Step 6.
Used by:
  - patch_step6.py to backfill historical sector_intel.json
  - backtest_step6_overlay.py to verify alpha
  - Sector protocol Phase 4c (LLM may invoke or replicate manually)

Returns per-sector multiplier (with confidence gating) and an overlay metadata dict.
"""
from __future__ import annotations

# Base regime × cyclical/defensive matrix (raw multipliers, pre-confidence-gate)
REGIME_MATRIX = {
    "Goldilocks":             {"cyclical": 1.05, "defensive": 0.95},
    "Soft Landing":           {"cyclical": 1.05, "defensive": 0.95},
    "Reflation":              {"cyclical": 1.10, "defensive": 0.90},
    "Benign Easing":          {"cyclical": 1.05, "defensive": 0.95},
    "Overheating":            {"cyclical": 0.95, "defensive": 1.00},
    "Late Cycle Tightening":  {"cyclical": 0.85, "defensive": 1.05},
    "Stagflation":            {"cyclical": 0.75, "defensive": 1.10},
    "Recession Easing":       {"cyclical": 0.95, "defensive": 1.05},
    "Recession Risk":         {"cyclical": 0.70, "defensive": 1.15},
    "Transitional":           {"cyclical": 1.00, "defensive": 1.00},
}

# GICS-ish classification used by sector protocol
DEFENSIVE_SECTORS = {"Healthcare", "Utilities", "Consumer_Staples", "Real_Estate"}
# Everything else (Tech, Materials, Energy, Financials, Industrials, Cons_Disc, Comm) → cyclical

OVERRIDE_FAVOR_FACTOR = 1.05  # × on top of raw
OVERRIDE_AVOID_FACTOR = 0.90
OVERRIDE_CAP_HIGH     = 1.15
OVERRIDE_CAP_LOW      = 0.70


def classify(name: str) -> str:
    """Return 'cyclical' or 'defensive'. Tolerates 'Real Estate' / 'Real_Estate' etc."""
    n = name.replace(" ", "_")
    return "defensive" if n in DEFENSIVE_SECTORS else "cyclical"


def _matches(sector: str, lst) -> bool:
    """Sector name match tolerant of space/underscore differences."""
    if not lst:
        return False
    target = sector.replace(" ", "_").lower()
    for s in lst:
        if s.replace(" ", "_").lower() == target:
            return True
    return False


def compute_multiplier(sector_name: str, fred_snapshot: dict | None) -> dict:
    """
    Returns {
      'raw': float,           # before confidence gating
      'effective': float,     # after gating (this is the actual score multiplier)
      'classification': 'cyclical' | 'defensive',
      'override': 'favor' | 'avoid' | None,
      'rationale': str,
    }
    fred_snapshot=None or fred_available=false → effective=1.0 (no-op).
    """
    if not fred_snapshot:
        return {
            "raw": 1.0, "effective": 1.0,
            "classification": classify(sector_name),
            "override": None,
            "rationale": "fred_unavailable → no-op",
        }

    regime = fred_snapshot.get("regime_label", "Transitional")
    confidence = float(fred_snapshot.get("regime_confidence") or 0.0)
    favor = fred_snapshot.get("sector_rotation_favor") or []
    avoid = fred_snapshot.get("sector_rotation_avoid") or []

    matrix = REGIME_MATRIX.get(regime, REGIME_MATRIX["Transitional"])
    klass  = classify(sector_name)
    raw    = matrix[klass]

    override = None
    if _matches(sector_name, favor):
        raw      = min(raw * OVERRIDE_FAVOR_FACTOR, OVERRIDE_CAP_HIGH)
        override = "favor"
    elif _matches(sector_name, avoid):
        raw      = max(raw * OVERRIDE_AVOID_FACTOR, OVERRIDE_CAP_LOW)
        override = "avoid"

    # Confidence gating: effective = 1.0 + (raw - 1.0) × confidence
    effective = round(1.0 + (raw - 1.0) * confidence, 3)
    raw       = round(raw, 3)

    parts = [f"{regime}", f"conf={confidence:.2f}", klass, f"raw={raw}"]
    if override:
        parts.append(f"override={override}")
    parts.append(f"effective={effective}")
    rationale = " · ".join(parts)

    return {
        "raw": raw,
        "effective": effective,
        "classification": klass,
        "override": override,
        "rationale": rationale,
    }


def build_overlay_metadata(fred_snapshot: dict | None, per_sector_results: list[dict]) -> dict:
    """
    Build the top-level `step6_overlay` block from per-sector compute results.
    per_sector_results: [{'name': ..., **compute_multiplier output}, ...]
    """
    if not fred_snapshot:
        return {
            "applied": False, "replaces_step1": True,
            "regime_label": None, "regime_confidence": None,
            "rationale": "fred_unavailable → Step 1 cycle_phase remains active",
        }

    regime = fred_snapshot.get("regime_label")
    conf   = fred_snapshot.get("regime_confidence")

    favor_ex = [r for r in per_sector_results if r.get("override") == "favor"]
    avoid_ex = [r for r in per_sector_results if r.get("override") == "avoid"]
    def _mult(r):
        # Accept either CLI shape ('step6_fred_multiplier') or compute_multiplier shape ('effective')
        return r.get("effective", r.get("step6_fred_multiplier", "?"))
    def _fmt(rs):
        return ", ".join(f"{r['name']}×{_mult(r)}" for r in rs[:3])
    examples = []
    if favor_ex:
        examples.append("favor: " + _fmt(favor_ex))
    if avoid_ex:
        examples.append("avoid: " + _fmt(avoid_ex))

    rationale = f"{regime} regime, conf {conf}"
    if examples:
        rationale += " → " + "; ".join(examples)

    return {
        "applied": True,
        "replaces_step1": True,
        "regime_label": regime,
        "regime_confidence": conf,
        "rationale": rationale,
    }


def _slim_from_fred_cache(fred_cache_path: str) -> dict:
    """Build the slim fred_snapshot shape from the full fred-macro cache JSON."""
    import json as _json
    with open(fred_cache_path) as f:
        full = _json.load(f)
    rs = full.get("regime_signals", {})
    sr = full.get("sector_rotation", {})
    return {
        "regime_label":          full.get("regime_label"),
        "regime_confidence":     full.get("regime_confidence"),
        "sector_rotation_favor": sr.get("favor", []),
        "sector_rotation_avoid": sr.get("avoid", []),
        "yield_curve_inverted":  rs.get("yield_curve_inverted"),
        "real_rate_preferred":   rs.get("real_rate_preferred"),
    }


def _parse_input_arg(s: str):
    """Parse `Industrials:73,Technology:62,...` → [{'name': 'Industrials', 'score': 73}, ...]"""
    out = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            name, raw = part.split(":", 1)
            try:
                score = float(raw)
            except ValueError:
                score = 0
            out.append({"name": name.strip(), "score": score})
        else:
            out.append({"name": part, "score": 0})
    return out


def main():
    """CLI for Phase 4c — paste-ready Step 6 output for the LLM."""
    import argparse
    import json as _json
    import os
    import sys

    here     = os.path.dirname(os.path.abspath(__file__))
    fred_default = os.path.abspath(
        os.path.join(here, "..", "..", "skills/fred-macro/cache/fred_latest.json")
    )

    ap = argparse.ArgumentParser(
        description="Step 6 FRED Regime Overlay — deterministic computation for Phase 4c"
    )
    ap.add_argument("--fred-cache", default=fred_default,
                    help="path to fred-macro cache JSON (default: skills/fred-macro/cache/fred_latest.json)")
    ap.add_argument("--snapshot-stdin", action="store_true",
                    help="read slim fred_snapshot JSON from stdin instead of fred-cache")
    ap.add_argument("--input",
                    help='comma-separated sectors with scores: "Industrials:73,Technology:62,..."')
    ap.add_argument("--smoke", action="store_true", help="run smoke test (ignores --input)")
    args = ap.parse_args()

    if not args.smoke and not args.input:
        ap.error("--input is required (unless --smoke)")

    if args.smoke:
        snap = {
            "regime_label": "Overheating",
            "regime_confidence": 0.71,
            "sector_rotation_favor": ["Energy", "Materials", "Financials"],
            "sector_rotation_avoid": ["Technology", "Real Estate", "Consumer Discretionary"],
        }
        for sect in ["Industrials", "Technology", "Energy", "Real_Estate", "Healthcare",
                     "Financials", "Consumer_Discretionary", "Basic Materials"]:
            r = compute_multiplier(sect, snap)
            print(f"  {sect:25s} → effective={r['effective']:.3f}  ({r['rationale']})")
        return

    if args.snapshot_stdin:
        snap = _json.load(sys.stdin)
    else:
        if not os.path.exists(args.fred_cache):
            print(f"ERROR: fred cache not found at {args.fred_cache}", file=sys.stderr)
            print("Hint: run `python3 skills/fred-macro/scripts/fetch.py --json-only` first", file=sys.stderr)
            sys.exit(1)
        snap = _slim_from_fred_cache(args.fred_cache)

    sectors = _parse_input_arg(args.input)
    results = []
    for s in sectors:
        r = compute_multiplier(s["name"], snap)
        results.append({
            "name":                   s["name"],
            "raw_score":              s["score"],
            "step6_fred_multiplier":  r["effective"],
            "adjusted_score":         round(s["score"] * r["effective"], 2),
            "classification":         r["classification"],
            "override":               r["override"],
            "rationale":              r["rationale"],
        })

    overlay = build_overlay_metadata(snap, results)
    out = {"step6_overlay": overlay, "sectors": results}
    _json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
