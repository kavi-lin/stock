#!/usr/bin/env python3
"""
Render the latest `sector_logs/YYYY-MM-DD_sector_intel.json` into a
deterministic Markdown report at `reports/YYYY-MM-DD_sector_report.md`.

This replaces the model-driven Phase 5 markdown rewrite. The JSON produced
by Phase 4c (already in zh-TW) is the single source of truth — this script
performs zero re-interpretation, only rendering.

Invocation (from Phase 5):
    python3 sector/scripts/render_sector_report.py
        rc=0  → wrote reports/YYYY-MM-DD_sector_report.md
        rc=1  → no JSON found / required field missing

Optional flags:
    --json PATH    explicit input path (default: latest in sector_logs/)
    --out PATH     explicit output path (default: reports/<date>_sector_report.md)
    --stdout       print to stdout instead of writing a file
"""
import argparse
import glob
import json
import os
import sys
from collections import OrderedDict

ROOT      = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGS_DIR  = os.path.join(ROOT, "sector/sector_logs")
REPORT_DIR = os.path.join(ROOT, "reports")

ACTION_ORDER = ["overweight", "wait", "neutral", "underweight", "avoid"]
ACTION_LABEL = {
    "overweight":  "Overweight",
    "wait":        "Wait",
    "neutral":     "Neutral",
    "underweight": "Underweight",
    "avoid":       "Avoid",
}
CONF_ABBR = {"high": "high", "medium": "med", "low": "low"}


def find_latest():
    files = sorted(glob.glob(os.path.join(LOGS_DIR, "*_sector_intel.json")))
    return files[-1] if files else None


def fmt(v, default="—"):
    if v is None or v == "":
        return default
    return str(v)


def render_header(d):
    date  = d.get("verdict_date", "?")
    pv    = d.get("protocol_version", "?")
    fan   = d.get("phase4_fanout_mode", "?")
    p4c   = d.get("_phase4c") or {}
    conf  = p4c.get("regime_confidence")
    stance = p4c.get("final_regime_stance") or "—"
    cycle = d.get("cycle_phase", "—")
    gen   = d.get("generated_at", "")
    degraded = d.get("degraded_agents") or []
    deg_txt = ", ".join(degraded) if degraded else "none"

    lines = [
        f"# Sector Intelligence Report — {date}",
        "",
        f"> **Protocol**: {pv} · **Fan-out**: {fan} · **Regime Confidence**: {conf if conf is not None else '—'}",
        f"> **Stance**: {stance} · **Cycle**: {cycle} · **Generated**: {gen}",
        f"> **Degraded Agents**: {deg_txt}",
        "",
    ]
    return lines


def render_verdict_table(d):
    has_step6 = bool((d.get("step6_overlay") or {}).get("applied"))
    if has_step6:
        header = "| Sector | Verdict | Score | FRED× | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |"
        sep    = "|---|---|---|---|---|---|---|---|"
    else:
        header = "| Sector | Verdict | Score | Key Reasons (top 2) | Tail Risk | Proxy ETF | Risk Flags |"
        sep    = "|---|---|---|---|---|---|---|"
    lines = ["## FINAL VERDICT TABLE", "", header, sep]
    sectors = d.get("sectors") or []
    sectors_sorted = sorted(sectors, key=lambda s: s.get("composite_score", 0), reverse=True)
    for s in sectors_sorted:
        name   = s.get("name", "?")
        verd   = s.get("verdict", "?")
        score  = s.get("composite_score", "?")
        reasons = s.get("key_reasons") or []
        reasons_txt = " · ".join(reasons[:2]) if reasons else "—"
        tail   = s.get("tail_risk_label") or "N/A"
        etf    = s.get("proxy_etf") or "—"
        flags  = s.get("risk_flags") or []
        flags_txt = ", ".join(flags) if flags else "—"
        verd_md = f"**{verd}**" if verd in ("HOT", "AVOID") else verd
        if has_step6:
            mult = s.get("step6_fred_multiplier")
            mult_txt = f"{mult:.2f}" if isinstance(mult, (int, float)) else "—"
            lines.append(f"| {name} | {verd_md} | {score} | {mult_txt} | {reasons_txt} | {tail} | {etf} | {flags_txt} |")
        else:
            lines.append(f"| {name} | {verd_md} | {score} | {reasons_txt} | {tail} | {etf} | {flags_txt} |")
    lines.append("")
    return lines


def render_step6_block(d):
    so = d.get("step6_overlay") or {}
    if not so.get("applied"):
        return []
    fs = (d.get("_phase0") or {}).get("fred_snapshot") or {}
    rl = so.get("regime_label") or fs.get("regime_label", "—")
    rc = so.get("regime_confidence", fs.get("regime_confidence", "—"))
    rationale = so.get("rationale", "")
    favor = fs.get("sector_rotation_favor") or []
    avoid = fs.get("sector_rotation_avoid") or []
    velocity = fs.get("velocity_highlights") or []
    lines = [
        "## Step 6 — FRED Regime Overlay",
        "",
        f"- **Regime**: {rl} (confidence {rc})",
        f"- **Favor**: {', '.join(favor) if favor else '—'}",
        f"- **Avoid**: {', '.join(avoid) if avoid else '—'}",
    ]
    if velocity:
        lines.append(f"- **Velocity highlights**: {', '.join(velocity)}")
    if rationale:
        lines.append(f"- **Rationale**: {rationale}")
    lines.append("")
    return lines


def render_macro_block(d):
    p0 = d.get("_phase0") or {}
    snap = d.get("sentiment_snapshot") or {}
    overlay = (d.get("_phase3") or {}).get("political_overlay") or {}

    breadth_score = p0.get("breadth_score", "—")
    breadth_zone  = p0.get("breadth_zone", "—")
    breadth_ceil  = p0.get("exposure_ceiling", "—")
    syn           = d.get("synthesized_exposure", "—")
    cycle         = d.get("cycle_phase", "—")
    regime        = d.get("market_regime", "—")
    ftd           = p0.get("ftd") or {}
    ftd_state     = ftd.get("state", "—")
    ftd_q         = ftd.get("quality_score", "—")
    mt            = p0.get("market_top") or {}
    mt_score      = mt.get("composite_score", "—")
    mt_zone       = mt.get("zone", "—")
    sig_conflict  = "Yes" if p0.get("signal_conflict") else "No"
    fg            = snap.get("composite_score", overlay.get("fear_greed_index", "—"))
    fg_label      = snap.get("fear_greed_label", overlay.get("fear_greed_label", "—"))
    vix           = snap.get("vix", overlay.get("vix_current", "—"))
    pc            = snap.get("put_call_ratio", overlay.get("put_call_ratio"))
    pc_txt        = "n/a" if pc is None else pc
    rsi           = overlay.get("spy_rsi", "—")
    extreme       = "Yes" if (snap.get("extreme_sentiment_triggered") or overlay.get("extreme_sentiment_triggered")) else "No"

    lines = [
        "## Macro Context",
        "",
        "```text",
        f"Market Regime: {regime} | Breadth Ceiling: {breadth_ceil} | Synthesized: {syn} | Cycle: {cycle}",
        f"FTD: {ftd_state} (quality {ftd_q}) | Market Top: {mt_score} {mt_zone} | Breadth: {breadth_score} {breadth_zone}",
        f"Sentiment: F&G [{fg} — {fg_label}] | VIX: {vix} | Put/Call: {pc_txt} | SPY RSI: {rsi}",
        f"Signal Conflict: {sig_conflict} | Extreme Sentiment: {extreme}",
        "```",
        "",
    ]
    themes = d.get("actionable_themes") or []
    if themes:
        lines.append(f"**TOP THEMES TODAY**: {' · '.join(themes[:3])}")
        lines.append("")
    return lines


def render_today_verdict(d):
    p4c = d.get("_phase4c") or {}
    tv  = p4c.get("today_verdict") or {}
    if not tv:
        return [
            "## Today's Verdict",
            "",
            f"> {d.get('session_notes', '—')}",
            "",
        ]

    stance   = tv.get("stance", p4c.get("final_regime_stance", "—"))
    conf     = tv.get("confidence", p4c.get("regime_confidence", "—"))
    headline = tv.get("headline", "—")
    one_line = tv.get("one_liner", "")

    lines = [
        f"## Today's Verdict — {stance} (confidence {conf})",
        "",
        f"> **{headline}**",
    ]
    if one_line:
        lines += ["> ", f"> {one_line}"]
    lines.append("")

    takeaways = tv.get("key_takeaways") or []
    if takeaways:
        lines.append("### Key Takeaways")
        for i, t in enumerate(takeaways, 1):
            lines.append(f"{i}. {t}")
        lines.append("")

    actions = tv.get("sector_actions") or []
    if actions:
        lines.append("### Sector Actions")
        grouped = OrderedDict((a, []) for a in ACTION_ORDER)
        for a in actions:
            key = (a.get("action") or "").lower()
            grouped.setdefault(key, []).append(a)
        for action_key in ACTION_ORDER:
            bucket = grouped.get(action_key) or []
            if not bucket:
                continue
            label = ACTION_LABEL[action_key]
            for a in bucket:
                sect = a.get("sector", "?")
                conf_a = CONF_ABBR.get((a.get("confidence") or "").lower(), a.get("confidence", ""))
                reason = a.get("reason", "")
                tail = f" — {reason}" if reason else ""
                lines.append(f"- **{label}**: {sect} ({conf_a}){tail}")
        # any unknown action keys not in ACTION_ORDER
        for k, bucket in grouped.items():
            if k in ACTION_ORDER or not bucket:
                continue
            for a in bucket:
                sect = a.get("sector", "?")
                conf_a = CONF_ABBR.get((a.get("confidence") or "").lower(), a.get("confidence", ""))
                reason = a.get("reason", "")
                tail = f" — {reason}" if reason else ""
                lines.append(f"- **{k.title()}**: {sect} ({conf_a}){tail}")
        lines.append("")

    watch = tv.get("watch_next") or []
    if watch:
        lines.append("### Watch Next")
        for w in watch:
            lines.append(f"- {w}")
        lines.append("")

    return lines


def render_devils_advocate(d):
    p4b = d.get("_phase4b") or {}
    p4c = d.get("_phase4c") or {}
    targets = p4b.get("challenge_targets") or []
    accepted = set(p4c.get("devils_advocate_accepted") or [])
    rejected = set(p4c.get("devils_advocate_rejected") or [])
    if not targets:
        return []

    lines = [
        f"## Devil's Advocate Challenges (Accepted {len(accepted)}/{len(targets)})",
        "",
        "| Challenge | Status | Counter-Evidence |",
        "|---|---|---|",
    ]
    for t in targets:
        sect = t.get("challenged_sector", "?")
        call = t.get("challenged_call", "?")
        if sect in accepted:
            status = "**Accepted**"
        elif sect in rejected:
            status = "Rejected"
        else:
            status = "—"
        ce = (t.get("counter_evidence") or "").replace("\n", " ").replace("|", "\\|")
        # keep cell readable — trim to ~280 chars
        if len(ce) > 280:
            ce = ce[:277] + "..."
        chal = f"{sect} — {call}"
        lines.append(f"| {chal} | {status} | {ce} |")
    lines.append("")
    return lines


def render_divergence(d):
    rows = d.get("sector_divergence_watch") or []
    if not rows:
        return []
    lines = [
        "## Sector Divergence Watch",
        "",
        "| Sector | Signal | Action | Description |",
        "|---|---|---|---|",
    ]
    for r in rows:
        sect = r.get("sector", "?")
        sig  = r.get("signal", "—")
        act  = r.get("action", "—")
        desc = (r.get("description") or "").replace("|", "\\|")
        lines.append(f"| {sect} | {sig} | {act} | {desc} |")
    lines.append("")
    return lines


def render_valuation_snapshot(d):
    """V1.4 — Sector Valuation Snapshot (PE TTM, 1y z-score, RS vs SPY 3M, vol ratio)."""
    p1 = d.get("_phase1") or {}
    rows = p1.get("sectors") or []
    valuation_rows = [s for s in rows if isinstance(s.get("sector_valuation"), dict)]
    if not valuation_rows:
        return []

    header = "| Sector | PE TTM | 1y z-score | RS vs SPY 3M | ETF Vol/20d | Flag |"
    sep = "|" + "|".join(["---"] * 6) + "|"
    lines = ["## Sector Valuation Snapshot (V1.4)", "", header, sep]

    def fmt_pct(v):
        return f"{v*100:+.1f}%" if isinstance(v, (int, float)) else "—"

    def fmt_z(v):
        return f"{v:+.2f}" if isinstance(v, (int, float)) else "—"

    for s in valuation_rows:
        sv = s["sector_valuation"]
        pe   = sv.get("pe_ttm")
        z    = sv.get("pe_zscore_1y")
        rs   = sv.get("rs_vs_spy_3m")
        vol  = sv.get("etf_volume_ratio_20d")
        ur   = s.get("uptrend_ratio")

        flag = ""
        if isinstance(z, (int, float)) and isinstance(ur, (int, float)):
            if z > 2.0 and ur > 0.7:
                flag = "🔴 OVERBOUGHT"
            elif z < -1.0 and ur < 0.3:
                flag = "🟢 OVERSOLD VALUE"

        lines.append(
            f"| {s.get('name','?')} "
            f"| {fmt(pe)} "
            f"| {fmt_z(z)} "
            f"| {fmt_pct(rs)} "
            f"| {fmt(vol)} "
            f"| {flag} |"
        )
    lines.append("")
    lines.append("> z-score>2 + uptrend>0.7 → valuation_penalty −10；z-score<−1 + uptrend<0.3 → +5。完整 raw 數據見 `sector/cache/sector_valuation_<DATE>.json`。")
    lines.append("")
    return lines


def render_themes(d):
    themes = d.get("actionable_themes") or []
    if not themes:
        return []
    lines = ["## Top Actionable Themes", ""]
    for i, t in enumerate(themes, 1):
        lines.append(f"{i}. {t}")
    lines.append("")
    return lines


def render_handoff(d):
    notes = d.get("session_notes") or ""
    if not notes:
        return []
    return [
        "## HANDOFF TO INVESTMENT PROTOCOL",
        "",
        f"> {notes}",
        "",
    ]


def render(d):
    blocks = [
        render_header(d),
        render_verdict_table(d),
        render_macro_block(d),
        render_step6_block(d),
        render_valuation_snapshot(d),
        render_today_verdict(d),
        render_devils_advocate(d),
        render_divergence(d),
        render_themes(d),
        render_handoff(d),
    ]
    out = []
    for i, b in enumerate(blocks):
        if not b:
            continue
        out.extend(b)
        # separator between major blocks
        if i < len(blocks) - 1 and not (b and b[-1] == ""):
            out.append("")
        if i < len(blocks) - 1:
            out.append("---")
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="explicit sector_intel.json path")
    ap.add_argument("--out",  help="explicit output markdown path")
    ap.add_argument("--stdout", action="store_true", help="print to stdout instead of writing a file")
    args = ap.parse_args()

    src = args.json or find_latest()
    if not src or not os.path.exists(src):
        print(f"[render_sector_report] ✗ no sector_intel.json found (looked in {LOGS_DIR})", file=sys.stderr)
        sys.exit(1)

    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data.get("sectors"):
        print("[render_sector_report] ✗ sector_intel.json missing sectors[]", file=sys.stderr)
        sys.exit(1)

    md = render(data)

    if args.stdout:
        sys.stdout.write(md)
        return

    out_path = args.out
    if not out_path:
        date = data.get("verdict_date") or os.path.basename(src).split("_")[0]
        out_path = os.path.join(REPORT_DIR, f"{date}_sector_report.md")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"[render_sector_report] ✓ wrote {os.path.relpath(out_path, ROOT)} "
          f"({len(md):,} bytes, {len(md.splitlines())} lines) from {os.path.relpath(src, ROOT)}")


if __name__ == "__main__":
    main()
