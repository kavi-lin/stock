#!/usr/bin/env python3
"""Deterministically assemble sector_logs/<DATE>_sector_intel.json (產業掃描 V1.4).

Why: the `產業掃描` protocol's LLM agent currently hand-writes a 15+-key nested
`sector_intel.json` every run, copying mechanical fields out of the phase caches
by eye. That causes turn bloat and transcription drift. This script moves the
mechanical assembly into code: the LLM only authors a compact *decision* JSON
(judgment fields), and this script merges it with the on-disk phase caches into
the full intel file that `validate_sector_intel.py` gates and
`render_sector_report.py` consumes.

Usage:
    python3 sector/scripts/build_sector_intel.py --date 2026-05-18
    python3 sector/scripts/build_sector_intel.py --date 2026-05-18 --decision path/to/decision.json

Inputs
------
(a) On-disk phase caches (assembled BY THIS SCRIPT, not the LLM):
    - phase0_read_caches.py stdout            -> _phase0
    - sector/cache/sector_valuation_<DATE>.json   -> _phase1.sectors[].sector_valuation
    - sector/cache/sector_earnings_pulse_<DATE>.json -> _phase3.sector_earnings_pulse
    - sector/cache/sector_smart_money_<DATE>.json -> _phase3.smart_money_signals

(b) Decision JSON (LLM-authored, judgment-only). Default path:
    sector/cache/sector_decision_<DATE>.json

Decision JSON schema (the ONLY file the protocol LLM hand-writes)
----------------------------------------------------------------
Top-level keys:
    verdict_date            str  "YYYY-MM-DD"
    market_regime           str  e.g. "RISK_ON"
    exposure_ceiling        str  e.g. "40-60%"
    synthesized_exposure    str  e.g. "40-60%"
    cycle_phase             str  e.g. "Late"
    phase4_fanout_mode      str  one of PARALLEL_SUBAGENT / PARTIAL_FALLBACK /
                                 FULL_FALLBACK / INLINE
    degraded_agents         list[str]
    regime_stance           str  AGGRESSIVE / NEUTRAL / DEFENSIVE  (-> _phase4c)
    sectors                 list[obj], each:
        name                str   canonical sector name (matches caches)
        verdict             str   HOT / WARM / COLD / AVOID
        composite_score     int   0-100
        score_components    obj   {breadth_momentum, theme_heat, news_catalyst,
                                   rotation_signal, valuation_penalty}  (valuation_penalty REQUIRED)
        risk_flags          list[str]
        proxy_etf           str   (REQUIRED when verdict == HOT)
        sector_actions      list[str]   (optional free-text actions; -> key_reasons fallback)
        rotation_signal     str   INFLOW / OUTFLOW / NEUTRAL  (-> _phase1.sectors[])
        uptrend_ratio       float 0-1   (-> _phase1.sectors[])
        key_reasons         list[str]   (optional)
        devils_advocate_note str        (optional)
        tail_risk_label     str         (optional, default "N/A")
        step6_fred_multiplier float     (optional)
        cyclical_or_defensive str       (optional, -> _phase1.sectors[])
    summary                 obj  {hot_sectors, warm_sectors, cold_sectors, avoid_sectors}
    today_verdict           obj  {headline, stance, one_liner, key_takeaways[],
                                  sector_actions[], watch_next[], confidence}  (-> _phase4c)
    actionable_themes       list[str]
    political_risk_summary  obj
    session_notes           str
    top_catalysts           list[obj]  >= 5 entries (rank/event/type/impact_score/...)
    political_overlay       obj  (fear_greed_index, vix_current, ...)
    sentiment_snapshot      obj  {composite_score, fear_greed_label, vix, put_call_ratio,
                                  extreme_sentiment_triggered}   (optional - see below)
Optional pass-through keys copied verbatim if present:
    upcoming_events, upcoming_binary_risks, sector_news_sentiment,
    sector_divergence_watch, step6_overlay, _phase2, _phase4a, _phase4b,
    rotation_theme, hot_sectors (phase1), cold_sectors (phase1)

Sentiment: if `sentiment_snapshot` is absent from the decision file the script
pulls it from political_overlay (fear_greed_index/vix_current/put_call_ratio).

Output: sector/sector_logs/<DATE>_sector_intel.json  (protocol_version="V1.4")

Exit codes: 0 success, 1 missing/malformed cache or decision file.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "sector" / "cache"
LOGS_DIR = ROOT / "sector" / "sector_logs"
PHASE0_SCRIPT = ROOT / "sector" / "scripts" / "phase0_read_caches.py"
VALIDATOR = ROOT / "sector" / "scripts" / "validate_sector_intel.py"


def die(msg: str) -> None:
    print(f"[build_sector_intel] ✗ {msg}", file=sys.stderr)
    sys.exit(1)


def load_json(path: Path, label: str) -> dict:
    if not path.exists():
        die(f"required {label} cache missing: {path}")
    try:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except json.JSONDecodeError as e:
        die(f"{label} cache malformed JSON ({path}): {e}")
    return {}  # unreachable


def build_phase0(date: str) -> dict:
    """Run phase0_read_caches.py and reshape its layered output into _phase0."""
    if not PHASE0_SCRIPT.exists():
        die(f"phase0_read_caches.py not found: {PHASE0_SCRIPT}")
    try:
        proc = subprocess.run(
            [sys.executable, str(PHASE0_SCRIPT)],
            capture_output=True, text=True, timeout=120,
        )
    except subprocess.TimeoutExpired:
        die("phase0_read_caches.py timed out")
    if not proc.stdout.strip():
        die(f"phase0_read_caches.py produced no output (rc={proc.returncode}): "
            f"{proc.stderr.strip()[:200]}")
    try:
        p0raw = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        die(f"phase0_read_caches.py output not valid JSON: {e}")

    layers = p0raw.get("layers", {})
    breadth = (layers.get("breadth") or {}).get("data") or {}
    ftd = (layers.get("ftd") or {}).get("data") or {}
    mtop = (layers.get("market_top") or {}).get("data") or {}
    fred = (layers.get("fred") or {}).get("data") or {}
    fred_available = bool((layers.get("fred") or {}).get("available"))

    bcomp = breadth.get("composite") or {}
    bcomps = breadth.get("components") or {}

    # warning flags from breadth signals
    warning_flags = []
    bsig = (bcomps.get("bearish_signal") or {})
    if bsig.get("score", 100) <= 40:
        warning_flags.append("Bearish_Signal_Active")
    mac = (bcomps.get("ma_crossover") or {})
    if mac.get("gap") is not None and mac.get("gap") < 0:
        warning_flags.append("Below_200MA")
    hp = (bcomps.get("historical_percentile") or {})
    if hp.get("score", 100) <= 40:
        warning_flags.append("Low_Historical_Percentile")
    if bcomp.get("zone") in ("Weakening", "Weak"):
        warning_flags.append("Weakening_Zone")

    mt_comp = mtop.get("composite") or {}
    ftd_state = (ftd.get("market_state") or {})
    ftd_qual = (ftd.get("quality_score") or {})

    phase0 = {
        "phase": 0,
        "agent": "Macro_Regime_Analyst",
        "scan_date": date,
        "breadth_source": "market-breadth-analyzer",
        "breadth_score": bcomp.get("composite_score"),
        "breadth_zone": bcomp.get("zone"),
        "breadth_components": {
            "overall_breadth": bcomp.get("composite_score"),
        },
        "market_regime": None,            # filled by merge() from decision
        "cycle_phase": None,              # filled by merge() from decision
        "uptrend_ratio_overall": None,    # filled by merge() (from phase1 avg)
        "warning_flags": warning_flags,
        "exposure_ceiling": None,         # filled by merge() from decision
        "regime_confidence": 0.9,
        "ftd": {
            "state": ftd_state.get("combined_state")
                     or ftd_state.get("state"),
            "quality_score": (ftd_qual.get("total_score")
                              if ftd_qual.get("total_score") is not None
                              else ftd_qual.get("quality_score")
                              if ftd_qual.get("quality_score") is not None
                              else ftd_qual.get("score")),
            "exposure_range": ftd_state.get("exposure_range")
                              or ftd_state.get("recommended_exposure"),
            "source": "ftd_cache",
        },
        "market_top": {
            "composite_score": mt_comp.get("composite_score"),
            "zone": mt_comp.get("zone"),
            "risk_budget": mt_comp.get("risk_budget"),
            "source": "market_top_cache",
        },
        "synthesized_exposure": None,     # filled by merge() from decision
        "signal_conflict": False,         # filled by merge()
        "fred_available": fred_available,
    }
    if fred_available and fred:
        phase0["fred_snapshot"] = {
            "generated_at": fred.get("generated_at"),
            "regime_label": fred.get("regime_label"),
            "regime_confidence": fred.get("regime_confidence"),
            "macro_scores_composite": fred.get("macro_scores_composite"),
            "yield_curve_value": fred.get("yield_curve_value"),
            "yield_curve_inverted": fred.get("yield_curve_inverted"),
            "credit_stress_elevated": fred.get("credit_stress_elevated"),
            "financial_stress_above_avg": fred.get("financial_stress_above_avg"),
            "fed_rate_direction": fred.get("fed_rate_direction"),
            "real_rate_preferred": fred.get("real_rate_preferred"),
            "sector_rotation_favor": fred.get("sector_rotation_favor") or [],
            "sector_rotation_avoid": fred.get("sector_rotation_avoid") or [],
            "velocity_highlights": fred.get("velocity_highlights") or [],
        }
    else:
        phase0["fred_snapshot"] = None
    return phase0


def require(decision: dict, key: str):
    if key not in decision:
        die(f"decision file missing required key: {key}")
    return decision[key]


def build(date: str, decision_path: Path) -> dict:
    # ── decision file ─────────────────────────────────────────────────────
    if not decision_path.exists():
        die(f"decision file not found: {decision_path}\n"
            f"  The 產業掃描 protocol LLM must author this judgment-only JSON "
            f"(schema in this script's docstring).")
    try:
        with decision_path.open("r", encoding="utf-8") as fp:
            decision = json.load(fp)
    except json.JSONDecodeError as e:
        die(f"decision file malformed JSON ({decision_path}): {e}")
    if not isinstance(decision, dict):
        die("decision file root must be a JSON object")

    # ── phase caches ──────────────────────────────────────────────────────
    valuation = load_json(CACHE_DIR / f"sector_valuation_{date}.json", "sector_valuation")
    earnings = load_json(CACHE_DIR / f"sector_earnings_pulse_{date}.json", "sector_earnings_pulse")
    smartmoney = load_json(CACHE_DIR / f"sector_smart_money_{date}.json", "sector_smart_money")
    val_sectors = valuation.get("sectors") or {}
    sep = earnings.get("sectors") or {}
    sms = smartmoney.get("sectors") or {}
    if not val_sectors:
        die("sector_valuation cache has empty sectors{}")
    if not sep:
        die("sector_earnings_pulse cache has empty sectors{}")
    if not sms:
        die("sector_smart_money cache has empty sectors{}")

    phase0 = build_phase0(date)

    # ── decision-driven scalars ───────────────────────────────────────────
    dec_sectors = require(decision, "sectors")
    if not isinstance(dec_sectors, list) or not dec_sectors:
        die("decision.sectors must be a non-empty array")

    phase0["market_regime"] = require(decision, "market_regime")
    phase0["cycle_phase"] = require(decision, "cycle_phase")
    phase0["exposure_ceiling"] = require(decision, "exposure_ceiling")
    phase0["synthesized_exposure"] = require(decision, "synthesized_exposure")
    phase0["signal_conflict"] = bool(decision.get("signal_conflict", False))

    # ── _phase1.sectors[] : uptrend/rotation from decision, valuation from cache ─
    p1_sectors = []
    uptrend_vals = []
    for s in dec_sectors:
        name = s.get("name")
        if not name:
            die("a decision.sectors[] entry is missing 'name'")
        sv = val_sectors.get(name)
        if not isinstance(sv, dict):
            die(f"sector_valuation cache has no entry for sector '{name}' "
                f"(decision and cache sector names must match)")
        ur = s.get("uptrend_ratio")
        if ur is None:
            die(f"decision.sectors[{name}] missing uptrend_ratio")
        if "rotation_signal" not in s:
            die(f"decision.sectors[{name}] missing rotation_signal")
        uptrend_vals.append(ur)
        p1_sectors.append({
            "name": name,
            "uptrend_ratio": ur,
            "rotation_signal": s["rotation_signal"],
            "cyclical_or_defensive": s.get("cyclical_or_defensive"),
            "sector_valuation": sv,
        })

    if uptrend_vals:
        phase0["uptrend_ratio_overall"] = round(
            sum(uptrend_vals) / len(uptrend_vals), 3)

    phase1 = {
        "phase": 1,
        "agent": "Sector_Rotation_Analyst",
        "cycle_position": decision["cycle_phase"],
        "sectors": p1_sectors,
        "hot_sectors": (decision.get("summary") or {}).get("hot_sectors", []),
        "cold_sectors": (decision.get("summary") or {}).get("cold_sectors", []),
        "rotation_theme": decision.get("rotation_theme", ""),
    }

    # ── _phase3 : catalysts/overlay from decision, pulse/smartmoney from cache ─
    top_catalysts = require(decision, "top_catalysts")
    if not isinstance(top_catalysts, list) or len(top_catalysts) < 5:
        die(f"decision.top_catalysts must have >= 5 entries (got "
            f"{len(top_catalysts) if isinstance(top_catalysts, list) else 0})")
    phase3 = {
        "phase": 3,
        "agent": "News_Catalyst_Analyst",
        "scan_window": decision.get("scan_window", "past 10 days + next 7 days"),
        "top_catalysts": top_catalysts,
        "political_overlay": require(decision, "political_overlay"),
        "sector_earnings_pulse": sep,
        "smart_money_signals": sms,
    }
    for opt in ("upcoming_events", "upcoming_binary_risks", "sector_news_sentiment"):
        if opt in decision:
            phase3[opt] = decision[opt]

    # ── top-level sectors[] (final verdicts) ──────────────────────────────
    sectors_out = []
    for s in dec_sectors:
        name = s["name"]
        sc = s.get("score_components") or {}
        if "valuation_penalty" not in sc:
            die(f"decision.sectors[{name}].score_components missing "
                f"valuation_penalty (V1.4 hard-required)")
        verdict = s.get("verdict")
        if verdict == "HOT" and not s.get("proxy_etf"):
            die(f"decision.sectors[{name}] verdict=HOT requires proxy_etf")
        key_reasons = s.get("key_reasons")
        if not key_reasons:
            key_reasons = s.get("sector_actions") or []
        entry = {
            "name": name,
            "verdict": verdict,
            "composite_score": s.get("composite_score"),
            "score_components": sc,
            "key_reasons": key_reasons,
            "devils_advocate_note": s.get("devils_advocate_note", ""),
            "tail_risk_label": s.get("tail_risk_label", "N/A"),
            "proxy_etf": s.get("proxy_etf"),
            "risk_flags": s.get("risk_flags", []),
        }
        if s.get("step6_fred_multiplier") is not None:
            entry["step6_fred_multiplier"] = s["step6_fred_multiplier"]
        sectors_out.append(entry)

    # ── _phase4c (today_verdict + stance) ─────────────────────────────────
    today_verdict = require(decision, "today_verdict")
    if not isinstance(today_verdict, dict):
        die("decision.today_verdict must be an object")
    phase4c = {
        "phase": "4c",
        "agent": "Portfolio_Strategist",
        "final_regime_stance": require(decision, "regime_stance"),
        "today_verdict": today_verdict,
    }

    # ── sentiment_snapshot (decision-supplied or derived from overlay) ────
    sentiment = decision.get("sentiment_snapshot")
    if not isinstance(sentiment, dict):
        ov = phase3["political_overlay"] or {}
        sentiment = {
            "composite_score": ov.get("fear_greed_index"),
            "fear_greed_label": ov.get("fear_greed_label"),
            "vix": ov.get("vix_current"),
            "put_call_ratio": ov.get("put_call_ratio"),
            "extreme_sentiment_triggered": ov.get("extreme_sentiment_triggered", False),
        }

    # ── assemble ──────────────────────────────────────────────────────────
    out = {
        "verdict_date": require(decision, "verdict_date"),
        "protocol_version": "V1.4",
        "phase4_fanout_mode": require(decision, "phase4_fanout_mode"),
        "degraded_agents": decision.get("degraded_agents", []),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "market_regime": decision["market_regime"],
        "exposure_ceiling": decision["exposure_ceiling"],
        "synthesized_exposure": decision["synthesized_exposure"],
        "cycle_phase": decision["cycle_phase"],
        "_phase0": phase0,
        "_phase1": phase1,
        "_phase3": phase3,
        "_phase4c": phase4c,
        "sentiment_snapshot": sentiment,
        "sectors": sectors_out,
        "summary": require(decision, "summary"),
        "political_risk_summary": require(decision, "political_risk_summary"),
        "actionable_themes": require(decision, "actionable_themes"),
        "session_notes": require(decision, "session_notes"),
    }
    # optional verbatim pass-through blocks
    for opt in ("_phase2", "_phase4a", "_phase4b", "sector_divergence_watch",
                "step6_overlay"):
        if opt in decision:
            out[opt] = decision[opt]

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Assemble sector_intel.json from caches + decision file")
    ap.add_argument("--date", required=True, help="Scan date YYYY-MM-DD")
    ap.add_argument("--decision", default=None,
                    help="Path to LLM-authored decision JSON "
                         "(default: sector/cache/sector_decision_<DATE>.json)")
    args = ap.parse_args()

    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        die(f"--date must be YYYY-MM-DD (got {args.date!r})")

    decision_path = (Path(args.decision) if args.decision
                     else CACHE_DIR / f"sector_decision_{args.date}.json")

    intel = build(args.date, decision_path)

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = LOGS_DIR / f"{args.date}_sector_intel.json"
    with out_path.open("w", encoding="utf-8") as fp:
        json.dump(intel, fp, indent=2, ensure_ascii=False)
        fp.write("\n")

    summary = intel.get("summary", {})
    print(f"[build_sector_intel] ✓ wrote {out_path.relative_to(ROOT)} — "
          f"{len(intel['sectors'])} sectors, "
          f"{len(summary.get('hot_sectors', []))} HOT / "
          f"{len(summary.get('warm_sectors', []))} WARM / "
          f"{len(summary.get('cold_sectors', []))} COLD / "
          f"{len(summary.get('avoid_sectors', []))} AVOID, "
          f"fanout={intel['phase4_fanout_mode']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
