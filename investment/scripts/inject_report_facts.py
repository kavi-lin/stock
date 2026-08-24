#!/usr/bin/env python3
"""Deterministic fact injection for Phase 5 MD reports (V4.66.0, 0 LLM).

The Sonnet MD Formatter writes placeholder lines instead of hand-copying
decision-critical numbers; this script replaces them with blocks rendered
verbatim from history.json. Rationale: transcription IS arithmetic — the LLM
must never touch byte-level-faithful content (same philosophy as「禁止手算」).

Placeholders (each on its own line in the MD):
    <!--INJECT:decision_summary-->
    <!--INJECT:lane_scores-->
    <!--INJECT:fair_value_anchors-->
    <!--INJECT:kill_conditions-->
    <!--INJECT:key_risks-->
    <!--INJECT:watch_conditions-->

Each injected block is wrapped in <!--FACTS:<name>:start--> / <!--FACTS:<name>:end-->
markers, so re-running the script refreshes content idempotently.

Usage:
    python3 investment/scripts/inject_report_facts.py                # latest report + history[-1]
    python3 investment/scripts/inject_report_facts.py --report R.md --history H.json   # tests

rc=0 injected (or nothing to do); rc=1 unknown placeholder / leftover INJECT
token / missing files / ticker-date mismatch.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HISTORY_JSON = os.path.join(ROOT, "investment", "invest_logs", "history.json")
REPORTS_DIR = os.path.join(ROOT, "reports")

LANE_LABEL = {"fundamentals": "Fundamentals", "sentiment": "Sentiment",
              "news": "News", "technical": "Technical", "valuation": "Valuation"}


def fmt(v, money=False, pct=False):
    if v is None or v == "":
        return "N/A"
    if isinstance(v, (int, float)):
        if money:
            return f"${v:,.2f}"
        if pct:
            return f"{v}%"
        return f"{v}"
    return str(v)


def fmt_position_size(v):
    """`position_size_pct` is a FRACTION of the portfolio despite its name.

    `trade_plan_builder` builds it from `BASE_POSITION = 0.05` and
    `vol_adjusted_limit_pct / 100.0`, then multiplies fractions the whole way
    down the sizing chain — so 0.035325 means **3.53%**, not 0.035%.

    Every other `pct=True` field really is a percent (`decision_confidence_pct`
    67, `vs_current_pct` -34.5), so this one cannot be fixed in `fmt`; it needs
    its own formatter. Until V4.116.0 it went through the generic one, which
    appends a bare '%' — publishing a hundredfold understatement of every sized
    position. 2026-08-09 NOW printed "0.035325%" for a 3.53% position, and
    2026-08-07 NET / AAOI carry the same shape.

    Renaming the field is the real fix. It appears in history.json, the export
    schema and the validator, so the conversion lives here until that is worth
    doing — and the name is called out above so the next reader does not have to
    re-derive which of the two units this is.
    """
    if v is None or v == "":
        return "N/A"
    try:
        return f"{float(v) * 100:.2f}%"
    except (TypeError, ValueError):
        return str(v)


def render_decision_summary(t):
    odds = t.get("scenario_odds") or {}
    odds_s = (f"bull {odds.get('bull', 'N/A')} / base {odds.get('base', 'N/A')} / "
              f"bear {odds.get('bear', 'N/A')}") if odds else "N/A"
    fvs = t.get("fair_value_summary") or {}
    fv_label = ("DCF 主FV／加權合理價 (weighted_fair_value)"
                if fvs.get("primary_method") == "dcf_self_built"
                else "加權合理價 (weighted_fair_value)")
    rows = [
        ("Final Decision", f"{fmt(t.get('final_decision'))}（action: {fmt(t.get('final_action'))}）"),
        ("Final Score", f"{fmt(t.get('final_score'))} / 3.0"),
        ("Decision Confidence", fmt(t.get("decision_confidence_pct"), pct=True)),
        ("Position Size", fmt_position_size(t.get("position_size_pct"))),
        ("分析時價格", fmt(t.get("analysis_price"), money=True)),
        (fv_label,
         f"{fmt(fvs.get('weighted_fair_value'), money=True)}（vs 現價 {fmt(fvs.get('vs_current_pct'), pct=True)}，{fmt(fvs.get('verdict_band'))}）"),
        ("Scenario Odds", odds_s),
        ("Entry（保守 / 積極）",
         f"{fmt(t.get('entry_conservative'), money=True)} / {fmt(t.get('entry_aggressive'), money=True)}"),
        ("TP / SL", f"{fmt(t.get('take_profit'), money=True)} / {fmt(t.get('stop_loss'), money=True)}"),
        ("R/R・staged_split", f"{fmt(t.get('risk_reward_ratio'))}・{fmt(t.get('staged_split'))}"),
        ("Burry Score", f"{fmt(t.get('burry_score'))} / 100"),
        ("Red Team", fmt(t.get("red_team_verdict"))),
    ]
    out = ["| 欄位 | 值 |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in rows]
    return "\n".join(out)


def render_lane_scores(t):
    scores = t.get("lane_scores") or {}
    out = ["| Lane | Score（−3 … +3） |", "|---|---|"]
    for key in ("fundamentals", "sentiment", "news", "technical", "valuation"):
        if key in scores:
            out.append(f"| {LANE_LABEL[key]} | {fmt(scores[key])} |")
    for key in scores:  # any non-standard lane keys, keep verbatim
        if key not in LANE_LABEL:
            out.append(f"| {key} | {fmt(scores[key])} |")
    out.append(f"| Burry（獨立否決軌） | {fmt(t.get('burry_score'))} / 100 |")
    out.append(f"| Red Team | {fmt(t.get('red_team_verdict'))} |")
    return "\n".join(out)


def render_fair_value_anchors(t):
    fvs = t.get("fair_value_summary") or {}
    anchors = fvs.get("anchors") or {}
    weights = fvs.get("weights_used") or {}
    out = ["**合理股價（fair_value_summary — decision_lock 保護，engine 原值）**", "",
           "| Anchor | 值 | 權重 |", "|---|---|---|"]
    for name, val in anchors.items():
        w = weights.get(name)
        out.append(f"| {name} | {fmt(round(val, 2) if isinstance(val, (int, float)) else val, money=True)} | {fmt(w)} |")
    out += ["",
            f"- {'DCF 主FV／加權合理價' if fvs.get('primary_method') == 'dcf_self_built' else '加權合理價'} "
            f"(weighted_fair_value): {fmt(fvs.get('weighted_fair_value'), money=True)}"
            f"（vs 現價 {fmt(fvs.get('vs_current_pct'), pct=True)}）",
            f"- Verdict band: {fmt(fvs.get('verdict_band'))}｜confidence: {fmt(fvs.get('confidence'))}"
            f"｜current_price: {fmt(fvs.get('current_price'), money=True)}"]
    fvr = t.get("fair_value_range") or {}
    if fvr:
        out += [f"- 區間 (fair_value_range): P25 {fmt(fvr.get('p25'), money=True)} / "
                f"P50 {fmt(fvr.get('p50'), money=True)} / P75 {fmt(fvr.get('p75'), money=True)}"
                f"｜min–max anchor {fmt(fvr.get('min_anchor'), money=True)}–{fmt(fvr.get('max_anchor'), money=True)}"
                f"｜{fmt(fvr.get('range_verdict'))}｜錨一致度 {fmt(fvr.get('agreement_grade'))}"]
    explained = t.get("valuation_explained_range") or {}
    if explained.get("available"):
        out += [
            f"- DCF 主區間: {fmt((explained.get('primary_sensitivity') or {}).get('low'), money=True)}–"
            f"{fmt((explained.get('primary_sensitivity') or {}).get('high'), money=True)}；"
            f"主 FV {fmt(explained.get('primary_fv'), money=True)}",
            f"- Anchor 情境: 不含 peer {fmt(explained.get('scenario_without_peer'), money=True)} / "
            f"含 peer {fmt(explained.get('scenario_with_peer'), money=True)}；"
            f"完整解釋帶 {fmt(explained.get('range_low'), money=True)}–"
            f"{fmt(explained.get('range_high'), money=True)}",
            f"- Peer range-only: {fmt(explained.get('peer_pe_range_anchor'), money=True)} "
            f"({', '.join(explained.get('peer_symbols') or [])}；n={explained.get('peer_count', 0)})；"
            "不取代 DCF 主 FV",
        ]
        other = explained.get("other_eligible_anchors") or {}
        if other:
            out += ["- 其他 eligible anchors: " + " / ".join(
                f"{name} {fmt(value, money=True)}" for name, value in other.items()
            )]
    ie = t.get("implied_expectations") or {}
    if ie:
        cagr = ie.get("implied_5y_fcf_cagr")
        cagr_s = f"{cagr * 100:.1f}%" if isinstance(cagr, (int, float)) else "N/A"
        out += [f"- 隱含預期 (implied_expectations): 現價隱含 5Y FCF CAGR {cagr_s}"
                f"（out_of_range: {fmt(ie.get('implied_out_of_range'))}，WACC {fmt(ie.get('wacc_used'))}）"]
    forward = t.get("forward_validation") or {}
    if forward:
        out += [
            f"- 前瞻驗證 (forward_validation): **{fmt(forward.get('status'))}**；"
            f"DCF gap {fmt(forward.get('dcf_gap_pct'), pct=True)}；"
            f"支持 {', '.join(forward.get('supported_checks') or []) or '無'}；"
            f"失敗 {', '.join(forward.get('failed_checks') or []) or '無'}",
            f"- Valuation score: {fmt(forward.get('valuation_score_before'))} → "
            f"{fmt(forward.get('valuation_score_effective'))}；"
            f"T5 hard downgrade eligible: {fmt(forward.get('t5_hard_downgrade_eligible'))}",
        ]
    return "\n".join(out)


def render_kill_conditions(t):
    conds = t.get("red_team_kill_conditions") or []
    if not conds:
        return "N/A（本 session 無 red_team_kill_conditions）"
    return "\n".join(f"{i}. {c}" for i, c in enumerate(conds, 1))


def render_key_risks(t):
    risks = t.get("key_risks") or []
    if not risks:
        return "N/A（本 session 無 key_risks）"
    return "\n".join(f"- {r}" for r in risks)


def render_watch_conditions(t):
    wc = t.get("watch_conditions") or {}
    if not wc:
        return "N/A（本 session 無 watch_conditions）"
    if isinstance(wc, dict):
        return "\n".join(f"- **{k}**: {v}" for k, v in wc.items())
    return "\n".join(f"- {v}" for v in wc)


RENDERERS = {
    "decision_summary": render_decision_summary,
    "lane_scores": render_lane_scores,
    "fair_value_anchors": render_fair_value_anchors,
    "kill_conditions": render_kill_conditions,
    "key_risks": render_key_risks,
    "watch_conditions": render_watch_conditions,
}

INJECT_RE = re.compile(r"<!--INJECT:([a-z_]+)-->")


def resolve_latest(history_path):
    with open(history_path, encoding="utf-8") as fp:
        hist = json.load(fp)
    if not isinstance(hist, list) or not hist:
        print("[inject_report_facts] ✗ history.json 空或格式錯", file=sys.stderr)
        sys.exit(1)
    last = hist[-1]
    ticker = last.get("ticker") or (last.get("trades_this_session") or [{}])[0].get("ticker")
    export_date = last.get("export_date")
    if not ticker or not export_date:
        print("[inject_report_facts] ✗ history 末筆缺 ticker / export_date", file=sys.stderr)
        sys.exit(1)
    report = os.path.join(REPORTS_DIR, f"{export_date.replace('-', '')}_{ticker}.md")
    return report, last


def inject(report_path, entry):
    trades = entry.get("trades_this_session") or []
    if not trades:
        print("[inject_report_facts] ✗ history 末筆無 trades_this_session", file=sys.stderr)
        return 1
    t = trades[0]
    with open(report_path, encoding="utf-8") as fp:
        text = fp.read()

    # 先重新渲染既有 FACTS 區塊（idempotent re-run）
    refreshed = []
    for name, renderer in RENDERERS.items():
        marker = re.compile(
            rf"<!--FACTS:{name}:start-->.*?<!--FACTS:{name}:end-->", re.DOTALL)
        if marker.search(text):
            text = marker.sub(
                f"<!--FACTS:{name}:start-->\n{renderer(t)}\n<!--FACTS:{name}:end-->", text)
            refreshed.append(name)

    # 再替換 placeholder
    injected = []
    unknown = []
    def _sub(m):
        name = m.group(1)
        if name not in RENDERERS:
            unknown.append(name)
            return m.group(0)
        injected.append(name)
        return f"<!--FACTS:{name}:start-->\n{RENDERERS[name](t)}\n<!--FACTS:{name}:end-->"
    text = INJECT_RE.sub(_sub, text)

    if unknown:
        print(f"[inject_report_facts] ✗ 未知 placeholder: {unknown}（可用: {sorted(RENDERERS)}）",
              file=sys.stderr)
        return 1
    leftover = INJECT_RE.findall(text)
    if leftover:
        print(f"[inject_report_facts] ✗ 仍有未處理 INJECT token: {leftover}", file=sys.stderr)
        return 1

    with open(report_path, "w", encoding="utf-8") as fp:
        fp.write(text)
    if injected or refreshed:
        print(f"[inject_report_facts] ✓ {os.path.relpath(report_path, ROOT)} — "
              f"injected: {injected or '—'}; refreshed: {refreshed or '—'}")
    else:
        print(f"[inject_report_facts] ✓ 無 placeholder（舊格式報告或已定稿），未改動")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", help="MD 報告路徑（預設由 history 末筆推導）")
    ap.add_argument("--history", default=HISTORY_JSON)
    args = ap.parse_args()

    if not os.path.exists(args.history):
        print(f"[inject_report_facts] ✗ history 不存在: {args.history}", file=sys.stderr)
        sys.exit(1)
    if args.report:
        report = args.report
        with open(args.history, encoding="utf-8") as fp:
            hist = json.load(fp)
        entry = hist[-1] if isinstance(hist, list) else hist
    else:
        report, entry = resolve_latest(args.history)
    if not os.path.exists(report):
        print(f"[inject_report_facts] ✗ 報告不存在: {report}", file=sys.stderr)
        sys.exit(1)
    sys.exit(inject(report, entry))


if __name__ == "__main__":
    main()
