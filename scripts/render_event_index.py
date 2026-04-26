"""Render event_index_milestone1.json into a human-readable markdown report."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = ROOT / "reports/decision_review"


def _latest_event_index() -> Path:
    """挑 reports/decision_review/event_index_YYYY-MM-DD.json 中最新的一份."""
    candidates = sorted(REVIEW_DIR.glob("event_index_*.json"))
    if not candidates:
        raise SystemExit("No event_index_*.json found in reports/decision_review/")
    return candidates[-1]


JSON_PATH = _latest_event_index()
MD_PATH = JSON_PATH.with_suffix(".md")

VERDICT_EMOJI = {
    "hit": "✅", "miss": "❌", "neutral": "⚪",
    "pending": "⏳", "n/a": "—",
}


def fmt_pct(v):
    if v is None:
        return "—"
    return f"{v:+.2f}%"


def render_deep_dive(r: dict) -> str:
    dc = r["decision_content"]
    rl = (r["reality_at_eval"] or {}).get("ticker_reality") or {}
    ag = r["agent_breakdown"]
    th = r["tuning_hooks"]
    v = r["verdict"]

    lines = [
        f"### {VERDICT_EMOJI[v['label']]} **{r['tickers'][0]}** deep-dive ({r['decision_date']})",
        "",
        f"**raw**: `{r['raw_path']}`",
        "",
        "**當時系統說了什麼**",
        f"- Final score: **{dc['final_score']}**, Action: **{dc['final_action']}**, Position: {dc['position_size']}",
    ]
    tp = dc.get("trader_proposal") or {}
    if tp:
        lines.append(f"- Trader 提案: entry={tp.get('entry')} / TP={tp.get('tp')} / SL={tp.get('sl')}")
    if ag:
        lines.append("- Agent 分數:")
        for a in ag:
            lines.append(f"  - {a['agent']:<14} {a['signal']:<6} score={a['score']:+.1f} conf={a['confidence']:.2f}")

    lines.append("")
    lines.append("**今天 (2026-04-26) 現實**")
    if rl:
        lines.append(f"- 價格: {rl['price_at_decision']} ({rl['price_at_decision_date']}) → "
                     f"{rl['price_at_eval']} ({rl['price_at_eval_date']})  **return: {rl['return_pct']:+.2f}%**")
        lines.append(f"- 期間 max: {rl['max_runup_since']} / min: {rl['max_drawdown_since']}")

    lines.append("")
    lines.append(f"**Verdict**: {VERDICT_EMOJI[v['label']]} **{v['label']}** — {v['rationale']}")

    lines.append("")
    lines.append(f"**信心評斷**: decisive_agent=**{th['decisive_agent']}**, "
                 f"agent_conf 範圍 {th['min_agent_confidence']}-{th['max_agent_confidence']}, "
                 f"window 完成 {r['reality_at_eval']['window_complete_pct']}% "
                 f"({r['reality_at_eval']['days_elapsed']}/{r['reality_at_eval']['window_days']}d)")
    return "\n".join(lines)


def render_sector_scan(r: dict) -> str:
    dc = r["decision_content"]
    re_block = r["reality_at_eval"] or {}
    etf_returns = re_block.get("etf_returns") or {}
    spy = etf_returns.get("SPY", 0)
    v = r["verdict"]

    lines = [
        f"### {VERDICT_EMOJI[v['label']]} **Sector Scan** ({r['decision_date']})",
        "",
        f"**raw**: `{r['raw_path']}`",
        "",
        f"**Regime**: {dc.get('market_regime')} | Breadth: {dc.get('breadth_score')} | Exposure: {dc.get('exposure_ceiling')}",
        "",
        "**評級 vs 實際 (相對 SPY):**",
        "",
        "| Sector | Rating | ETF | actual | vs SPY |",
        "|---|---|---|---|---|",
    ]
    for rating in dc.get("sector_ratings") or []:
        etf = rating.get("etf")
        ret = etf_returns.get(etf)
        rel = (ret - spy) if (ret is not None and spy is not None) else None
        lines.append(f"| {rating['sector']} | {rating['rating']} | {etf} | "
                     f"{fmt_pct(ret)} | {fmt_pct(rel)} |")

    lines.append("")
    lines.append(f"**SPY**: {fmt_pct(spy)} (window {re_block.get('window_days')}d, "
                 f"{re_block.get('days_elapsed')}d elapsed)")
    lines.append("")
    lines.append(f"**Verdict**: {VERDICT_EMOJI[v['label']]} **{v['label']}** — {v['rationale']}")
    return "\n".join(lines)


def render_news_digest(r: dict) -> str:
    dc = r["decision_content"]
    re_block = r["reality_at_eval"] or {}
    v = r["verdict"]
    lines = [
        f"### {VERDICT_EMOJI[v['label']]} **News Digest** ({r['decision_date']})",
        "",
        f"**raw**: `{r['raw_path']}`",
        "",
        f"- macro_delta: **{dc.get('macro_delta')}**, items: {dc.get('items_analyzed')}, "
        f"impact cards: {len(dc.get('impact_cards') or [])}",
    ]
    cards = dc.get("impact_cards") or []
    if cards:
        lines.append("- 主要 cards:")
        for c in cards[:5]:
            lines.append(f"  - [{c['type']} {c['score']}] {c['title']}")
    lines.append("")
    lines.append(f"**SPY {re_block.get('window_days')}d 實際**: {fmt_pct(re_block.get('spy_return_pct'))}")
    lines.append("")
    lines.append(f"**Verdict**: {VERDICT_EMOJI[v['label']]} **{v['label']}** — {v['rationale']}")
    return "\n".join(lines)


def render_theme_detector(r: dict) -> str:
    dc = r["decision_content"]
    re_block = r["reality_at_eval"] or {}
    etf_returns = re_block.get("etf_returns") or {}
    spy = etf_returns.get("SPY", 0)
    v = r["verdict"]
    lines = [
        f"### {VERDICT_EMOJI[v['label']]} **Theme Detector** ({r['decision_date']})",
        "",
        f"**raw**: `{r['raw_path']}`",
        "",
        "**LEAD 主題 vs 代表 ETF (vs SPY):**",
        "",
        "| Theme | Stage | Conf | ETF | actual | vs SPY |",
        "|---|---|---|---|---|---|",
    ]
    for t in dc.get("themes") or []:
        if t.get("direction") != "LEAD":
            continue
        for etf in (t.get("proxy_etfs") or []):
            ret = etf_returns.get(etf)
            rel = (ret - spy) if (ret is not None and spy is not None) else None
            lines.append(f"| {t['name'][:24]} | {t.get('stage')} | {t.get('confidence')} | "
                         f"{etf} | {fmt_pct(ret)} | {fmt_pct(rel)} |")
    lines.append("")
    lines.append(f"**SPY {re_block.get('window_days')}d**: {fmt_pct(spy)}")
    lines.append("")
    lines.append(f"**Verdict**: {VERDICT_EMOJI[v['label']]} **{v['label']}** — {v['rationale']}")
    return "\n".join(lines)


def render_momentum(r: dict) -> str:
    dc = r["decision_content"]
    re_block = r["reality_at_eval"] or {}
    per_ticker = re_block.get("per_ticker") or []
    v = r["verdict"]

    lines = [
        f"### {VERDICT_EMOJI[v['label']]} **Momentum Screen** ({r['decision_date']})",
        "",
        f"**raw**: `{r['raw_path']}` (snap_id={dc['snap_id']})",
        "",
        f"- 全宇宙 {dc['n_total_screened']} 檔 → top {dc['n_evaluated']} 評估",
        f"- label 分佈: {dc.get('label_distribution')}",
        f"- warning 統計: {dc.get('warning_counts') or '—'}",
        "",
        f"**Verdict (aggregate)**: {VERDICT_EMOJI[v['label']]} **{v['label']}** — {v['rationale']}",
        "",
    ]
    if per_ticker:
        lines.append("| ticker | score | label | warnings | return | verdict |")
        lines.append("|---|---|---|---|---|---|")
        for x in per_ticker[:10]:
            warnings = ",".join(x.get("warnings") or []) or "—"
            ret = x.get("return_pct")
            ret_s = f"{ret:+.2f}%" if ret is not None else "—"
            lines.append(f"| {x['ticker']} | {x.get('score')} | {x.get('label')} | "
                         f"{warnings} | {ret_s} | "
                         f"{VERDICT_EMOJI.get(x['verdict'],'?')} {x['verdict']} |")
        if len(per_ticker) > 10:
            lines.append(f"| ... | ... | ... | ... | ... | (其餘 {len(per_ticker)-10} 筆省略) |")
    return "\n".join(lines)


def render_thematic_screener(r: dict) -> str:
    dc = r["decision_content"]
    re_block = r["reality_at_eval"] or {}
    v = r["verdict"]
    lines = [
        f"### {VERDICT_EMOJI[v['label']]} **Thematic Screener (radar)** ({r['decision_date']})",
        "",
        f"**raw**: `{r['raw_path']}`",
        "",
        f"- Regime: {(dc.get('regime_snapshot') or {}).get('regime_label')}, "
        f"warnings: {len(dc.get('global_warnings') or [])}",
    ]
    th = dc.get("themes") or []
    lines.append(f"- Top {len(th)} themes:")
    for t in th[:5]:
        lines.append(f"  - {t['name']} ({t['direction']}, lifecycle={t['lifecycle_stage']}, conf={t['confidence']})"
                     f" → movers: {', '.join(m['ticker'] for m in t.get('top_movers') or [])}")
    lines.append("")
    lines.append(f"**Verdict**: {VERDICT_EMOJI[v['label']]} **{v['label']}** — {v['rationale']}")
    lines.append(f"  → window 完成 {re_block.get('window_complete_pct')}% "
                 f"({re_block.get('days_elapsed')}/{re_block.get('window_days')}d), "
                 f"5/1 後即可填入完整 verdict")
    return "\n".join(lines)


def render_earnings(r: dict) -> str:
    dc = r["decision_content"]
    re_block = r["reality_at_eval"] or {}
    v = r["verdict"]
    summary = dc.get("summary") or {}
    lines = [
        f"### {VERDICT_EMOJI[v['label']]} **Earnings Analyzer** ({r['decision_date']})",
        "",
        f"**raw**: `{r['raw_path']}`",
        "",
        f"- 檢視 {summary.get('total','?')} 檔，A:{summary.get('grade_a',0)} "
        f"B:{summary.get('grade_b',0)} C:{summary.get('grade_c',0)} D:{summary.get('grade_d',0)}",
    ]
    a_b = [r2 for r2 in (dc.get("results") or [])
           if r2.get("grade") in ("A", "B")]
    if a_b:
        lines.append("- A/B 級樣本:")
        for r2 in a_b:
            lines.append(f"  - {r2['symbol']} ({r2['grade']}, score={r2['composite_score']}, "
                         f"gap={r2['gap_pct']}%, sector={r2['sector']})")
    lines.append("")
    lines.append(f"**Verdict**: {VERDICT_EMOJI[v['label']]} **{v['label']}** — {v['rationale']}")
    lines.append(f"  → 5/1 後 (eval window 5d 完成) 可驗 grade A/B 是否 outperform")
    return "\n".join(lines)


def render_weekly(r: dict) -> str:
    dc = r["decision_content"]
    v = r["verdict"]
    lines = [
        f"### {VERDICT_EMOJI[v['label']]} **Short-Term Weekly Review** ({r['decision_date']})",
        "",
        f"**raw**: `{r['raw_path']}`",
        "",
        f"- pending: {dc.get('pending')}",
        f"- hit_rate: {dc.get('hit_rate')}, alpha: {dc.get('avg_alpha_pct')}, n_evaluated: {dc.get('n_evaluated')}",
        "",
        f"**Verdict**: {VERDICT_EMOJI[v['label']]} **{v['label']}** — {v['rationale']}",
        "  → weekly review 本週為空 (radar 4/25 才 1d), 5/1 跑下次 weekly 才有資料",
    ]
    return "\n".join(lines)


def render_postmortem(r: dict) -> str:
    dc = r["decision_content"]
    v = r["verdict"]
    lines = [
        f"### {VERDICT_EMOJI[v['label']]} **Postmortem** ({r['decision_date']})",
        "",
        f"**raw**: `{r['raw_path']}`",
        "",
        f"- 分析了 {dc.get('reports_parsed')} 份 deep-dive，{dc.get('with_outcome')} 份有價格 outcome",
    ]
    buckets = dc.get("decision_buckets") or []
    if buckets:
        lines.append("- 決策 bucket:")
        for b in buckets:
            lines.append(f"  - {b['bucket']}: n={b['n']}, ret_so_far={b['ret_so_far']}")
    lines.append("")
    lines.append(f"**Verdict**: {VERDICT_EMOJI[v['label']]} **{v['label']}** — {v['rationale']}")
    return "\n".join(lines)


RENDER_DISPATCH = {
    "deep-dive":         render_deep_dive,
    "sector-scan":       render_sector_scan,
    "news-digest":       render_news_digest,
    "theme-detector":    render_theme_detector,
    "momentum-screen":   render_momentum,
    "thematic-screener": render_thematic_screener,
    "earnings-analyzer": render_earnings,
    "short-term-weekly": render_weekly,
    "postmortem":        render_postmortem,
}


def main():
    data = json.loads(JSON_PATH.read_text())
    sections = []
    sections.append(f"# Milestone 1 — Event Index Review (today = {data['today']})")
    sections.append("")
    sections.append(f"**Records**: {data['decision_count']} | "
                    f"**Generated**: {data['generated_at']}")
    sections.append("")
    sections.append("> 每筆 record 顯示：raw 來源 → 當時決策 → 今天現實 → verdict + 信心評斷")
    sections.append("")

    # 依 source 分組
    by_src: dict[str, list[dict]] = {}
    for r in data["decisions"]:
        by_src.setdefault(r["source"], []).append(r)

    order = ["deep-dive", "sector-scan", "news-digest", "theme-detector",
             "momentum-screen", "thematic-screener", "earnings-analyzer",
             "short-term-weekly", "postmortem"]

    sections.append("## 一覽表")
    sections.append("")
    sections.append("| # | source | date | tickers | verdict | rationale |")
    sections.append("|---|---|---|---|---|---|")
    for i, r in enumerate(data["decisions"], 1):
        tk = ",".join((r.get("tickers") or [])[:3])[:25]
        e = VERDICT_EMOJI.get(r["verdict"]["label"], "?")
        sections.append(f"| {i} | {r['source']} | {r['decision_date']} | "
                        f"{tk} | {e} {r['verdict']['label']} | "
                        f"{r['verdict']['rationale'][:70]} |")
    sections.append("")

    for src in order:
        if src not in by_src:
            continue
        sections.append(f"---")
        sections.append("")
        sections.append(f"## {src}")
        sections.append("")
        for r in by_src[src]:
            sections.append(RENDER_DISPATCH[src](r))
            sections.append("")

    MD_PATH.write_text("\n".join(sections))
    print(f"Rendered → {MD_PATH}")


if __name__ == "__main__":
    main()
