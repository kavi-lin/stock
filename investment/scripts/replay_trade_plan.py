#!/usr/bin/env python3
"""replay_trade_plan.py — V4.82.0 history replay + mismatch triage for trade_plan_builder.

Re-derives the Phase 4 outputs from every `history.json` trade and compares them against
what was stored, so a regression in the builder shows up as a diff against the production
record rather than against itself.

Three disciplines this harness holds to (same as `replay_decision_engine.py`):

1. **No silent caps.** Every trade that cannot be replayed appears in an exclusion table
   with a machine-readable reason. Coverage numbers always reconcile per cohort:
   eligible + excluded = total.

2. **No silent assumptions.** History does not persist most Phase 4 inputs. The
   feasibility scan over the 172 stored trades measured, at the time this harness was
   written:

       vol_adjusted_limit_pct    0/172     ← the Step 2 base, i.e. the chain's entry point
       tail_risk_score           1/172
       sizing_chain              0/172     ← new in V4.82.0
       final_stop_loss_pct       0/172     ← new in V4.82.0
       mandatory_risk_flags      0/172     ← new in V4.82.0
       multi_horizon_price_fw   38/172
       technical_lane.key_levels 60/172

   A forward replay of the sizing chain is therefore impossible for essentially every
   historical trade — the denominator would be 0 and a "100% parity" headline would be a
   lie. So the chain is replayed **backwards** instead: the stored `position_size_pct` is
   divided by the multipliers that ARE recoverable, and the implied Step 2 base is checked
   for admissibility (0 < base ≤ 20%, the risk_manager hard cap). That is a real falsifier
   — a hand-written size lands outside the admissible band — without inventing an input.

3. **Rule era is not engine error.** Phase 4 rules landed in stages: staged_split
   (2026-04-15), the FTD timeline gate (V4.9, first seen 2026-04-27), MHP-sourced entry
   provenance (V3.45.3, first seen 2026-06-13). Trades decided before a rule existed are
   replayed and reported separately, auto-classified `rule_version_drift`, and never
   counted as parity failures. V20-F1 (sector concentration) is new in V4.82.0 and could
   not have applied to ANY historical trade, so the replay pins its multiplier to 1.0
   throughout — counting it would manufacture a mismatch on every entry.

Three cohorts, each with its own denominator:
  A. `trade_plan`  — entry / TP / SL re-derived from the stored MHP + key_levels
  B. `risk_reward` — R/R re-derived from the stored entry range, TP and SL
  C. `sizing`      — inverse chain solve for the implied Step 2 base

Mismatches in the current-rule cohort come out as `NEEDS_TRIAGE` with a full input dump,
for manual classification into `engine_bug` / `historical_llm_arithmetic_error` /
`unrecorded_input`.

Usage:
  python3 investment/scripts/replay_trade_plan.py
  python3 investment/scripts/replay_trade_plan.py --json /tmp/replay_p4.json
  python3 investment/scripts/replay_trade_plan.py --out reports/decision_review/p4.md

rc=0 for the pre-rule cohorts (drift is expected); rc=1 when a current-rule trade
mismatches, so this can be wired into CI once enough post-V4.82.0 entries accumulate.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trade_plan_builder import (  # noqa: E402
    FRAGILITY_MULTIPLIER,
    MACRO_CAP_LIMIT,
    MACRO_CAP_TRIGGER,
    build_trade_plan,
    entry_candidates,
    risk_reward,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HISTORY_JSON = os.path.join(ROOT, "investment/invest_logs/history.json")
OUT_DIR = os.path.join(ROOT, "reports/decision_review")

# Rule-era cutover. V4.82.0 is when Phase 4 became script-executed: before it the
# entry/TP/SL provenance rule was protocol prose the PM applied by hand, and NOTHING
# enforced entry == the MHP band or R/R == the ratio implied by the published range.
# So every pre-cutover diff measures the drift this version exists to remove, not an
# engine defect — it is reported, classified `rule_version_drift`, and never failed on.
CURRENT_RULES_SINCE = "2026-08-03"
FTD_GATE_SINCE = "2026-04-27"         # V4.9 — Step 3.5 FTD timeline gate first shipped

# risk_manager.py caps the raw vol-adjusted position at 20% before its correlation
# multiplier, so an implied base above that cannot have come from Step 2.
MAX_ADMISSIBLE_BASE = 0.20


def _f(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return float(x)


def _pair(v):
    """Stored entry ranges are `["448", "462"]` (strings) on older entries."""
    if not isinstance(v, (list, tuple)) or len(v) != 2:
        return None
    out = []
    for x in v:
        if isinstance(x, str):
            try:
                x = float(x.replace("$", "").replace(",", "").strip())
            except ValueError:
                return None
        f = _f(x)
        if f is None:
            return None
        out.append(f)
    return out


def _trades(hist):
    for entry in hist:
        date = entry.get("export_date") or entry.get("date") or ""
        for idx, trade in enumerate(entry.get("trades_this_session") or []):
            if isinstance(trade, dict):
                yield date, idx, entry, trade


# ---------------------------------------------------------------------------
# Cohort A — trade plan (entry / TP / SL) re-derivation
# ---------------------------------------------------------------------------

def replay_trade_plan(date, trade, entry):
    mhp = trade.get("multi_horizon_price_framework")
    if not isinstance(mhp, dict):
        return {"status": "excluded", "reason": "no_multi_horizon_price_framework"}
    st = mhp.get("short_term_5d") or {}
    mid = mhp.get("mid_term_60d") or {}
    band = st.get("band_capped") or st.get("band")
    if not (isinstance(band, (list, tuple)) and len(band) == 3):
        return {"status": "excluded", "reason": "mhp_band_missing"}
    if _f(mid.get("mid_target")) is None:
        return {"status": "excluded", "reason": "mhp_mid_target_missing"}
    kl = (trade.get("technical_lane") or {}).get("key_levels")
    if not isinstance(kl, dict) or not kl:
        return {"status": "excluded", "reason": "no_key_levels"}

    stored_tp = _f(trade.get("take_profit"))
    stored_agg = _pair(trade.get("entry_aggressive"))
    stored_cons = _pair(trade.get("entry_conservative"))
    if stored_tp is None and stored_agg is None and stored_cons is None:
        return {"status": "excluded", "reason": "no_stored_plan_to_compare"}

    plan = build_trade_plan(trade.get("final_decision") or "BUY", mhp, kl,
                            _f(trade.get("analysis_price")),
                            (trade.get("technical_lane") or {}).get("pattern"),
                            trade.get("time_horizon"))
    diffs = []
    if stored_tp is not None and plan["take_profit"] is not None:
        if abs(stored_tp - plan["take_profit"]) > max(0.02, stored_tp * 0.02):
            diffs.append(f"take_profit stored {stored_tp} vs replay {plan['take_profit']}")
    for label, stored in (("entry_aggressive", stored_agg), ("entry_conservative", stored_cons)):
        got = plan[label]
        if stored is None or got is None or None in got:
            continue
        if any(abs(a - b) > max(0.02, abs(a) * 0.02) for a, b in zip(stored, got)):
            diffs.append(f"{label} stored {stored} vs replay {got}")

    era = "current" if date >= CURRENT_RULES_SINCE else "pre_rule"
    return {"status": "matched" if not diffs else "mismatched", "era": era,
            "diffs": diffs, "replay": {"take_profit": plan["take_profit"],
                                       "entry_aggressive": plan["entry_aggressive"],
                                       "entry_conservative": plan["entry_conservative"]}}


# ---------------------------------------------------------------------------
# Cohort B — R/R re-derivation
# ---------------------------------------------------------------------------

def replay_risk_reward(date, trade):
    stored_rr = _f(trade.get("risk_reward_ratio"))
    if stored_rr is None:
        return {"status": "excluded", "reason": "no_stored_risk_reward_ratio"}
    tp, sl = _f(trade.get("take_profit")), _f(trade.get("stop_loss"))
    if tp is None or sl is None:
        return {"status": "excluded", "reason": "no_take_profit_or_stop_loss"}
    plan = {"entry_aggressive": _pair(trade.get("entry_aggressive")),
            "entry_conservative": _pair(trade.get("entry_conservative"))}
    cands = entry_candidates(plan, trade.get("final_decision") or "BUY")
    if not cands:
        return {"status": "excluded", "reason": "no_entry_range"}

    # The export records the ratio but not which entry produced it. Rather than assume
    # one, every candidate entry is tried; agreeing with ANY of them means the stored
    # number is reproducible, and the matching track is named in the output.
    era = "current" if date >= CURRENT_RULES_SINCE else "pre_rule"
    tried = []
    for label, price in cands:
        rr = risk_reward(price, tp, sl)
        tried.append({"track": label, "entry_ref": round(price, 2), "rr": rr})
        if rr is not None and abs(rr - stored_rr) <= 0.06:
            return {"status": "matched", "era": era,
                    "matched_track": label, "stored_rr": stored_rr, "tried": tried}
    return {"status": "mismatched", "era": era, "stored_rr": stored_rr,
            "tried": tried,
            "diffs": [f"stored R/R {stored_rr} not reproducible from any entry track "
                      f"(tried {[t['rr'] for t in tried]}) with TP {tp} / SL {sl}"]}


# ---------------------------------------------------------------------------
# Cohort C — inverse sizing chain solve
# ---------------------------------------------------------------------------

def replay_sizing(date, entry, trade):
    """Divide the stored size back out through the recoverable multipliers.

    Recoverable from history: fragility_label, the macro cap trigger (phase0 snapshot),
    binary_classification, burry_override_active, the FTD gate block, the STAGED halving.
    NOT recoverable: the Step 2 vol cap (0/172 persisted) and the two Phase 3 position
    caps on pre-V5.1 entries — which is exactly why this runs backwards.

    The macro cap is a `min()`, not a multiplication, so a trade whose chain hit it cannot
    be inverted at all; those are excluded rather than solved with a fabricated factor.
    """
    size = _f(trade.get("position_size_pct"))
    if size is None:
        return {"status": "excluded", "reason": "no_position_size_pct"}
    if size <= 0:
        return {"status": "excluded", "reason": "zero_position_no_chain_to_invert"}

    label = trade.get("fragility_label")
    if label not in FRAGILITY_MULTIPLIER:
        return {"status": "excluded", "reason": f"unusable_fragility_label:{label}"}

    backdrop = _f((entry.get("phase0_macro_snapshot") or {}).get("macro_backdrop_score"))
    if backdrop is not None and backdrop < MACRO_CAP_TRIGGER:
        return {"status": "excluded", "reason": "macro_cap_min_not_invertible"}

    factors = {"fragility": FRAGILITY_MULTIPLIER[label]}

    binary = trade.get("binary_classification")
    # `binary_event_within_48h` is not persisted. Instead of guessing, both branches are
    # swept; the trade stays eligible only if the verdict is invariant across the sweep.
    binary_options = ([0.5, 1.0] if binary in ("unknown", "negative") else [1.0])

    if trade.get("burry_override_active") is True:
        factors["burry_override"] = 0.5

    gate = trade.get("ftd_timeline_gate")
    if isinstance(gate, dict) and gate.get("applied") is True:
        m = _f(gate.get("multiplier"))
        if m is None or m <= 0:
            return {"status": "excluded", "reason": "ftd_gate_applied_without_multiplier"}
        factors["ftd_timeline"] = m
    elif date >= FTD_GATE_SINCE and gate is None:
        return {"status": "excluded", "reason": "ftd_gate_expected_but_absent"}

    if trade.get("final_decision") == "STAGED_ENTRY":
        factors["staged_halving"] = 0.5

    # V20-F1 is new in V4.82.0 — pinned to 1.0 so it can never fabricate a mismatch.
    factors["v20_f1_sector_concentration"] = 1.0

    denom = 1.0
    for v in factors.values():
        denom *= v

    verdicts = []
    for bmult in binary_options:
        implied = size / (denom * bmult)
        verdicts.append({"binary_multiplier": bmult, "implied_base": round(implied, 6),
                         "admissible": 0 < implied <= MAX_ADMISSIBLE_BASE})
    admissible = {v["admissible"] for v in verdicts}
    era = "current" if date >= CURRENT_RULES_SINCE else "pre_rule"

    if len(admissible) > 1:
        return {"status": "excluded", "reason": "decision_sensitive_unknown:binary_event_within_48h",
                "sweep": verdicts}
    if True in admissible:
        return {"status": "matched", "era": era, "factors": factors,
                "implied_base": verdicts[0]["implied_base"], "sweep": verdicts}
    return {"status": "mismatched", "era": era, "factors": factors, "sweep": verdicts,
            "diffs": [f"stored position_size_pct {size} implies a Step 2 base of "
                      f"{verdicts[0]['implied_base']} after dividing out {factors} — outside "
                      f"the admissible (0, {MAX_ADMISSIBLE_BASE}] band, so no vol cap could "
                      "have produced it"]}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

COHORTS = (("trade_plan", "Step 1 entry / TP / SL provenance"),
           ("risk_reward", "R/R re-derivation from the stored plan"),
           ("sizing", "inverse Step 4 chain solve (implied Step 2 base)"))


def run(history_path):
    with open(history_path, encoding="utf-8") as fp:
        hist = json.load(fp)
    if not isinstance(hist, list):
        raise ValueError("history.json is not a JSON array")

    rows = []
    for date, idx, entry, trade in _trades(hist):
        rows.append({
            "date": date,
            "ticker": trade.get("ticker"),
            "final_decision": trade.get("final_decision"),
            "trade_plan": replay_trade_plan(date, trade, entry),
            "risk_reward": replay_risk_reward(date, trade),
            "sizing": replay_sizing(date, entry, trade),
        })

    summary = {}
    for cohort, _desc in COHORTS:
        eligible = [r for r in rows if r[cohort]["status"] != "excluded"]
        excluded = [r for r in rows if r[cohort]["status"] == "excluded"]
        matched = [r for r in eligible if r[cohort]["status"] == "matched"]
        mismatched = [r for r in eligible if r[cohort]["status"] == "mismatched"]
        current_mismatch = [r for r in mismatched if r[cohort].get("era") == "current"]
        reasons = {}
        for r in excluded:
            reasons[r[cohort]["reason"]] = reasons.get(r[cohort]["reason"], 0) + 1
        summary[cohort] = {
            "total": len(rows),
            "eligible": len(eligible),
            "excluded": len(excluded),
            "matched": len(matched),
            "mismatched": len(mismatched),
            "current_rule_mismatched": len(current_mismatch),
            "exclusion_reasons": dict(sorted(reasons.items(), key=lambda kv: -kv[1])),
            "reconciles": len(eligible) + len(excluded) == len(rows),
        }
    return {"engine": "replay_trade_plan.py v1.0.0 (V4.82.0)",
            "history": history_path, "summary": summary, "rows": rows}


def render_markdown(result):
    lines = ["# Phase 4 trade-plan replay", "",
             f"Engine: `{result['engine']}`  ", f"History: `{result['history']}`", ""]
    for cohort, desc in COHORTS:
        s = result["summary"][cohort]
        lines += [f"## Cohort `{cohort}` — {desc}", "",
                  f"- total trades: **{s['total']}**",
                  f"- eligible: **{s['eligible']}** / excluded: **{s['excluded']}** "
                  f"(reconciles: {s['reconciles']})",
                  f"- matched: **{s['matched']}** / mismatched: **{s['mismatched']}** "
                  f"(current-rule: **{s['current_rule_mismatched']}**)", ""]
        if s["exclusion_reasons"]:
            lines += ["| exclusion reason | n |", "|---|---|"]
            lines += [f"| `{k}` | {v} |" for k, v in s["exclusion_reasons"].items()]
            lines.append("")
        bad = [r for r in result["rows"] if r[cohort]["status"] == "mismatched"]
        if bad:
            lines += ["| date | ticker | era | diff |", "|---|---|---|---|"]
            for r in bad:
                for d in r[cohort].get("diffs", []):
                    era = r[cohort].get("era", "?")
                    tag = "**NEEDS_TRIAGE**" if era == "current" else "`rule_version_drift`"
                    lines.append(f"| {r['date']} | {r['ticker']} | {tag} | {d} |")
            lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Replay Phase 4 trade plans over history.json")
    ap.add_argument("--history", default=HISTORY_JSON)
    ap.add_argument("--json", help="write the full result JSON here")
    ap.add_argument("--out", help="write a Markdown report here")
    args = ap.parse_args(argv)

    result = run(args.history)
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)) or ".", exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fp:
            json.dump(result, fp, ensure_ascii=False, indent=2)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or OUT_DIR, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fp:
            fp.write(render_markdown(result))

    print(render_markdown(result))
    rc = 0
    for cohort, _ in COHORTS:
        if result["summary"][cohort]["current_rule_mismatched"]:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
