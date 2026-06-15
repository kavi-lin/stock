#!/usr/bin/env python3
"""Rec 11 (熱區保守性鬆綁) shadow-replay — read-only synthetic validation.

REVIEW_2026-06-13 / TODO-012. Rec 11 turns a default HOLD into a 15bps
`hot_zone_probe` STAGED_ENTRY when:

    final_score ∈ [0, +staged) ∧ industry_top_30pct ∧ macro_regime ∈ {RISK_ON, BULL}
    ∧ decision_cap_active != true ∧ mandatory_risk_flags 空

Because June regime is defensive, the rule has fired 0 times live → the first
decision-layer adjustment is unvalidated. This replays the gate against the
*historical* deep-dive HOLD-miss records in event_index so we get a synthetic
read on (a) how often it would have fired under its real regime gate, and
(b) the what-if if the gate were widened to all regimes (the deferred decision).

NOT a backtest of trading P&L — it estimates bounded-probe capture only:
a fired probe is bullish at 15bps, so on a HOLD-miss (price rose) it would have
been directionally right, capturing ~0.0015 × return_pct of portfolio NAV.

decision_cap_active / mandatory_risk_flags are NOT surfaced in event_index, so
they are assumed-pass and flagged as the one unverifiable gate term. Read-only:
touches no protocol state, writes only a report under reports/decision_review/.
"""
from __future__ import annotations
import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "reports/decision_review/event_index_latest.json"
PROBE_BPS = 0.0015  # Rec 11 position_size_pct ≤ 15bps
FIRE_REGIMES = {"RISK_ON", "BULL"}


def _decisive(th: dict):
    da = th.get("decisive_agent")
    return (da.get("agent") if isinstance(da, dict) else da) or "Unknown"


def collect(index: dict, industry_substr: str | None):
    """Return deep-dive HOLD-miss candidates (default-HOLD only; CANCEL is out of
    Rec 11 scope per ledger cap-rule #6) with the gate terms resolved per record."""
    rows = []
    for r in index.get("decisions", []):
        if r.get("source") != "deep-dive":
            continue
        dc = r.get("decision_content") or {}
        if (dc.get("final_action") or "").upper() != "HOLD":
            continue
        if (r.get("verdict") or {}).get("label") != "miss":
            continue
        th = r.get("tuning_hooks") or {}
        heat = th.get("sub_industry_heat") or {}
        ind = heat.get("ticker_industry") or heat.get("ticker_sector") or "Unknown"
        if industry_substr and industry_substr.lower() not in ind.lower():
            continue
        rl = (r.get("reality_at_eval") or {}).get("ticker_reality") or {}
        score = dc.get("final_score")
        rows.append({
            "id": r.get("decision_id"),
            "industry": ind,
            "decisive_agent": _decisive(th),
            "final_score": score,
            "macro_regime": (th.get("macro_regime") or dc.get("macro_regime") or "").upper(),
            "top30": heat.get("industry_top_30pct") is True,
            "score_ok": isinstance(score, (int, float)) and score >= 0,
            "return_pct": rl.get("return_pct"),
            "max_drawdown_pct": rl.get("max_drawdown_pct"),
        })
    return rows


def fires(row: dict, ignore_regime: bool) -> bool:
    if not (row["score_ok"] and row["top30"]):
        return False
    if ignore_regime:
        return True
    return row["macro_regime"] in FIRE_REGIMES


def _capture(fired: list[dict]) -> dict:
    rets = [r["return_pct"] for r in fired if r["return_pct"] is not None]
    dds = [r["max_drawdown_pct"] for r in fired if r["max_drawdown_pct"] is not None]
    # Probe is bullish 15bps; on a HOLD-miss (price rose) capture = bps × return.
    nav = sum(PROBE_BPS * x for x in rets)
    return {
        "n_fired": len(fired),
        "avg_missed_return_pct": round(sum(rets) / len(rets), 2) if rets else None,
        "avg_drawdown_pct": round(sum(dds) / len(dds), 2) if dds else None,
        "synthetic_nav_capture_pct": round(nav, 4),  # portfolio NAV %, summed
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--industry", default="Semiconductor",
                    help="sub-string filter on ticker_industry (default Semiconductor; '' = all top30 HOLD-miss)")
    ap.add_argument("--report", action="store_true", help="also write MD report")
    args = ap.parse_args()

    index = json.loads(INDEX.read_text(encoding="utf-8"))
    gen = index.get("generated_at", "?")
    cands = collect(index, args.industry or None)

    strict = [r for r in cands if fires(r, ignore_regime=False)]
    exreg = [r for r in cands if fires(r, ignore_regime=True)]
    strict_cap = _capture(strict)
    exreg_cap = _capture(exreg)
    label = args.industry or "ALL"

    lines = []
    lines.append(f"# Rec 11 shadow-replay — {label} HOLD-miss")
    lines.append(f"_index generated_at: {gen}_  ·  _replay: read-only, no protocol state touched_\n")
    lines.append(f"- candidate default-HOLD miss records: **{len(cands)}**")
    lines.append(f"- **strict gate** (RISK_ON/BULL only — the live rule): would fire **{strict_cap['n_fired']}**")
    lines.append(f"- **ex-regime** (gate widened to all regimes — the deferred what-if): would fire **{exreg_cap['n_fired']}**\n")
    lines.append("| pass | n_fired | avg_missed_return% | avg_dd% | synthetic NAV capture% (@15bps) |")
    lines.append("|---|---|---|---|---|")
    lines.append(f"| strict (live gate) | {strict_cap['n_fired']} | {strict_cap['avg_missed_return_pct']} | {strict_cap['avg_drawdown_pct']} | {strict_cap['synthetic_nav_capture_pct']} |")
    lines.append(f"| ex-regime (what-if) | {exreg_cap['n_fired']} | {exreg_cap['avg_missed_return_pct']} | {exreg_cap['avg_drawdown_pct']} | {exreg_cap['synthetic_nav_capture_pct']} |")
    lines.append("")
    lines.append("⚠️ `decision_cap_active` / `mandatory_risk_flags` are not in event_index → "
                 "assumed-pass; fired counts are upper bounds on those two terms only.")
    lines.append("")
    lines.append("### fired records (strict)")
    if strict:
        lines.append("| id | regime | score | missed_ret% | dd% | decisive |")
        lines.append("|---|---|---|---|---|---|")
        for r in strict:
            lines.append(f"| {r['id']} | {r['macro_regime']} | {r['final_score']} | "
                         f"{r['return_pct']} | {r['max_drawdown_pct']} | {r['decisive_agent']} |")
    else:
        lines.append("_none — strict gate fires 0× on history (matches live: regime defensive)._")
    report = "\n".join(lines)

    print(report)
    if args.report:
        out = ROOT / f"reports/decision_review/REC11_SHADOW_REPLAY_{date.today().isoformat()}.md"
        out.write_text(report + "\n", encoding="utf-8")
        print(f"\n[wrote] {out}")


if __name__ == "__main__":
    main()
