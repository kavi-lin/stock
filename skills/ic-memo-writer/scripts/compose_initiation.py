#!/usr/bin/env python3
"""compose_initiation.py — Deterministic fact_pack → Initiating Coverage 報告。

V4.69.0：首次覆蓋長格式報告（`首次覆蓋 [TICKER]` / `分析 --initiation`）。
與 compose.py 同紀律：ZERO LLM、不重評分、decision_lock 欄位 verbatim。
重用 compose.py 的 12 個 section renderer，額外渲染 valuation_model block
（valuation-modeler 自建 DCF 假設表 + FCFF 投影 + sensitivity + comps 全表 +
8-anchor fair_value_summary）。

前置：fact_pack 需以 `build_fact_pack.py <T> --initiation` 產生（含 valuation_model）。

Usage:
  python3 compose_initiation.py NVDA
  python3 compose_initiation.py --fact-pack <path> --output-dir reports/

Exit codes:
  0  ok
  1  fact_pack not found
  2  fact_pack schema mismatch
  3  fact_pack 缺 valuation_model（非 initiation fact_pack）
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compose as base  # noqa: E402  # 12 個 section renderer 重用

ROOT = Path(__file__).resolve().parents[3]
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"

COMPOSER_VERSION = "V1.0.0-initiation"


def _f(v, places=2, default="—"):
    if not isinstance(v, (int, float)):
        return default
    return f"{v:,.{places}f}"


def _pct(v, default="—"):
    if not isinstance(v, (int, float)):
        return default
    return f"{v:.2%}"


def render_initiation_header(fp: dict) -> str:
    f1 = fp["facts"]["sec_1"]
    return (
        f"# {fp['ticker']} ({f1.get('company_name') or '—'}) — Initiating Coverage 首次覆蓋報告\n\n"
        f"> **{f1.get('final_action') or '—'}** · 加權合理價 {base.fmt_money(f1.get('weighted_fair_value'))} "
        f"vs Analysis Price {base.fmt_money(f1.get('analysis_price'))}"
        f"（{base.fmt_num(f1.get('fv_vs_analysis_pct'))}%） · {f1.get('verdict_band') or '—'}\n>\n"
        f"> Live Spot: {base.fmt_money(f1.get('live_spot'))}"
        f"（vs FV {base.fmt_num(f1.get('fv_vs_live_pct'))}%） · "
        f"Sector: {f1.get('sector') or '—'} / {f1.get('industry') or '—'} · "
        f"Market Cap: {base.fmt_money(f1.get('market_cap'))} · as of {fp.get('as_of')}\n\n"
        f"*Deterministic render（0 LLM）；決策數字 verbatim 自 protocol history，"
        f"estimation 數字 verbatim 自 valuation-modeler engine。*"
    )


def render_dcf_model(vm_dcf: dict) -> str:
    """§8b 自建 DCF：假設（含 provenance）+ FCFF 投影 + sensitivity。"""
    a = vm_dcf.get("assumptions") or {}
    d = vm_dcf.get("dcf") or {}
    s = vm_dcf.get("sensitivity") or {}
    lines = ["### §8b 自建 driver-based DCF（valuation-modeler）", "",
             f"**Fair value: {base.fmt_money(vm_dcf.get('fair_value_per_share'))}** · "
             f"WACC {_pct(d.get('wacc_used'))} · terminal g {_pct(d.get('terminal_growth_used'))} · "
             f"asof {vm_dcf.get('asof') or '—'}", "",
             "**假設（value / provenance）** — override 過的假設會標 `override`：", ""]
    rows = [(k, _f(v.get("value"), 4), v.get("provenance"))
            for k, v in a.items() if isinstance(v, dict)]
    lines.append(base.md_table(["假設", "值", "來源"], rows))
    ft = d.get("fcff_table") or []
    if ft:
        lines += ["", "**FCFF 投影（$）**", "",
                  base.md_table(
                      ["Yr", "g", "Revenue", "EBITDA", "NOPAT", "Capex", "ΔNWC", "FCFF", "PV"],
                      [(r.get("year"), _pct(r.get("growth")), base.fmt_money(r.get("revenue")),
                        base.fmt_money(r.get("ebitda")), base.fmt_money(r.get("nopat")),
                        base.fmt_money(r.get("capex")), base.fmt_money(r.get("d_nwc")),
                        base.fmt_money(r.get("fcff")), base.fmt_money(r.get("pv_fcff"))) for r in ft])]
        lines += ["",
                  f"- PV explicit {base.fmt_money(d.get('pv_explicit'))} + PV terminal "
                  f"{base.fmt_money(d.get('pv_terminal'))} = EV {base.fmt_money(d.get('enterprise_value'))}"
                  f"；− net debt {base.fmt_money(d.get('net_debt'))} → equity "
                  f"{base.fmt_money(d.get('equity_value'))}"]
    grid = s.get("grid") or []
    if grid:
        tgs = s.get("terminal_growth_values") or []
        waccs = s.get("wacc_values") or []
        lines += ["", "**Sensitivity（WACC × terminal g，fair value $）**", "",
                  base.md_table(["WACC \\ g"] + [_pct(g) for g in tgs],
                                [tuple([_pct(w)] + [_f(v) for v in row])
                                 for w, row in zip(waccs, grid)])]
    for w in d.get("warnings") or []:
        lines.append(f"- ⚠ {w}")
    lines.append("\n<!-- src: valuation_modeler.dcf_payload -->")
    return "\n".join(lines)


def render_comps_model(vm_comps: dict) -> str:
    """§4b / §8c comps 全表：peer multiples + implied values + anchor。"""
    u = vm_comps.get("universe") or {}
    t = (vm_comps.get("table") or {}).get("metrics") or {}
    s = u.get("self") or {}
    lines = ["### §8c 同業比較（valuation-modeler comps）", "",
             f"**comps_implied anchor: {base.fmt_money(vm_comps.get('comps_implied_value'))}**"
             f"（EV/EBITDA + EV/Sales + PEG implied 中位數；P/E 排除防與 peer_pe_implied 重複計權）", "",
             "**Peer multiples**（本體 **粗體**）：", ""]

    def _row(sym, p, bold=False):
        b = "**" if bold else ""
        return (f"{b}{sym}{b}",
                base.fmt_money(p.get("market_cap")),
                _f(p.get("pe")), _f(p.get("ev_ebitda")), _f(p.get("ev_sales")),
                _pct(p.get("eps_growth_fwd")), _f(p.get("peg")))

    rows = [_row(s.get("symbol"), s, bold=True)]
    rows += [_row(sym, p) for sym, p in (u.get("peers") or {}).items()]
    lines.append(base.md_table(
        ["Ticker", "Mkt Cap", "P/E", "EV/EBITDA", "EV/Sales", "EPS g fwd", "PEG"], rows))

    lines += ["", "**Implied values（peer median × 本體指標）**", ""]
    irows = []
    for m, row in t.items():
        q = row.get("quartiles") or {}
        irows.append((m + (" *(anchor 排除)*" if m == "pe" else ""), row.get("n"),
                      _f(q.get("q1")), _f(q.get("median")), _f(q.get("q3")),
                      _f(row.get("self_value")), base.fmt_money(row.get("implied_value"))))
    lines.append(base.md_table(["Metric", "n", "Q1", "Median", "Q3", "Self", "Implied"], irows))
    dropped = u.get("dropped") or []
    if dropped:
        lines.append(f"\n- 市值門檻剔除 peer：{', '.join(x.get('symbol', '?') for x in dropped)}")
    lines.append("\n<!-- src: valuation_modeler.comps_payload -->")
    return "\n".join(lines)


def render_anchor_table(fp: dict) -> str:
    """§8a 8-anchor fair_value_summary（verbatim 自 decision_lock payload）。"""
    fvs = base._safe_float  # noqa: F841 — keep import surface identical
    sec8 = fp["facts"].get("sec_8") or {}
    summary = sec8.get("fair_value_summary") or {}
    anchors = summary.get("anchors") or {}
    weights = summary.get("weights_used") or {}
    lines = ["### §8a Fair-value anchors（protocol verbatim）", "",
             base.md_table(["Anchor", "值", "重分配後權重"],
                           [(k, base.fmt_money(v), _f(weights.get(k), 4))
                            for k, v in anchors.items()]),
             "",
             f"- 加權合理價 **{base.fmt_money(summary.get('weighted_fair_value'))}** vs 現價 "
             f"{base.fmt_money(summary.get('current_price'))} → {base.fmt_num(summary.get('vs_current_pct'))}% · "
             f"{summary.get('verdict_band') or '—'} · confidence {summary.get('confidence') or '—'}"
             f"（{summary.get('anchors_available', '—')} anchors）",
             f"- methodology: {summary.get('methodology_note') or '—'}",
             "\n<!-- src: protocol.history.fair_value_summary (decision_lock verbatim) -->"]
    return "\n".join(lines)


def compose_initiation(fp: dict, *, validator_rc: int | None = None) -> str:
    if fp.get("schema_version") != base.EXPECTED_SCHEMA:
        raise ValueError(
            f"fact_pack schema_version mismatch: expected {base.EXPECTED_SCHEMA}, "
            f"got {fp.get('schema_version')}")
    vm = fp.get("valuation_model")
    if not isinstance(vm, dict) or "dcf" not in vm or "comps" not in vm:
        raise KeyError("fact_pack lacks valuation_model — rebuild with build_fact_pack.py --initiation")

    facts = fp["facts"]
    sec_8 = dict(facts["sec_8"])
    sec_8["_sec_1"] = facts["sec_1"]
    sections = [
        render_initiation_header(fp),
        base.render_sec_1(facts["sec_1"], facts["sec_12"]),
        base.render_sec_2(facts["sec_2"]),
        base.render_sec_3(facts["sec_3"]),
        base.render_sec_4(facts["sec_4"]),
        base.render_sec_5(facts["sec_5"]),
        base.render_sec_6(facts["sec_6"]),
        base.render_sec_7(facts["sec_7"]),
        base.render_sec_8(sec_8),
        render_anchor_table(fp),
        render_dcf_model(vm["dcf"]),
        render_comps_model(vm["comps"]),
        base.render_sec_9(facts["sec_9"]),
        base.render_sec_10(facts["sec_10"]),
        base.render_sec_11(facts["sec_11"]),
        base.render_sec_12(facts["sec_12"], fp, validator_rc=validator_rc),
    ]
    body = "\n\n---\n\n".join(sections)
    footer = (
        f"\n\n---\n\n*Composed by ic-memo-writer {COMPOSER_VERSION} (deterministic, 0 LLM call) — "
        f"fact_pack hash {fp.get('fact_pack_hash', '—')[:16]}...*\n"
    )
    return body + footer


def main():
    ap = argparse.ArgumentParser(description="Deterministic Initiating Coverage composer.")
    ap.add_argument("ticker", nargs="?", help="Ticker (auto-locates latest fact_pack)")
    ap.add_argument("--fact-pack", type=Path, help="Explicit fact_pack JSON path")
    ap.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    args = ap.parse_args()

    if args.fact_pack:
        fp_path = args.fact_pack
    elif args.ticker:
        fp_path = base.locate_latest_fact_pack(args.ticker.upper())
        if fp_path is None:
            print(f"[initiation] fact_pack not found for {args.ticker}. "
                  f"Run build_fact_pack.py {args.ticker.upper()} --initiation first.", file=sys.stderr)
            sys.exit(1)
    else:
        ap.error("Provide either ticker or --fact-pack")

    if not fp_path.exists():
        print(f"[initiation] fact_pack file not found: {fp_path}", file=sys.stderr)
        sys.exit(1)
    try:
        fp = json.loads(fp_path.read_text())
    except Exception as exc:
        print(f"[initiation] fact_pack parse error: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        md = compose_initiation(fp)
    except KeyError as exc:
        print(f"[initiation] {exc}", file=sys.stderr)
        sys.exit(3)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    out_path = args.output_dir / f"{date_str}_{fp['ticker']}_initiation.md"
    out_path.write_text(md)
    print(f"[initiation] report written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
