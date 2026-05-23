#!/usr/bin/env python3
"""
narrative-pulse-detector — render cache JSON to markdown summary.

Usage:
    python3 skills/narrative-pulse-detector/scripts/render.py NOK
    python3 skills/narrative-pulse-detector/scripts/render.py NOK --output reports/<DATE>_NOK_pulse.md
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parents[1] / "cache"
REPO_ROOT = Path(__file__).resolve().parents[3]


# Codex review #4 fix: None-safe formatters so partial-quote / partial-component
# bundles don't crash the markdown render.
def _fmt_int(v, default: str = "—") -> str:
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return default


def _fmt_market_cap(v) -> str:
    try:
        return f"${float(v) / 1e9:.1f}B"
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(v, default: str = "—") -> str:
    try:
        return f"{float(v):.2f}%"
    except (TypeError, ValueError):
        return default


def _fmt_money(v, default: str = "—") -> str:
    try:
        return f"${float(v):.2f}"
    except (TypeError, ValueError):
        return default


def _fmt_or_dash(v, default: str = "—"):
    return default if v is None else v


def render_markdown(data: dict) -> str:
    t = data["ticker"]
    q = data.get("quote") or {}
    c = data.get("components") or {}
    stage = data.get("stage")
    stage_zh = data.get("stage_label_zh", "未知")
    stage_en = data.get("stage_label_en", "?")
    conf = data.get("stage_confidence", 0)
    er = data.get("expected_return_pct", 0)
    action = data.get("recommended_action", "?")
    next_warn = data.get("next_warning_condition") or "—"

    # Stage emoji
    se = {1: "🟢", 2: "🟡", 3: "🟡", 4: "🟠", 5: "🔴"}.get(stage, "⚪")

    out = []
    out.append(f"# {t} — Narrative Pulse Stage {stage} {se} {stage_zh}\n")
    out.append(f"> Run: {data.get('run_at', '?')} · Weights: {data.get('weights_version', '?')} · "
               f"Cache: skills/narrative-pulse-detector/cache/\n")
    out.append("---\n")

    # TL;DR
    out.append("## TL;DR\n")
    out.append(f"> **Stage {stage} ({stage_zh} / {stage_en})** · confidence={conf:.2f} · "
               f"E[R]={er:+.1f}% · action=**{action}**\n>\n"
               f"> Next warning: {next_warn}\n\n")

    # Quote (Codex #4: all fields routed through None-safe formatters)
    out.append("## Quote\n")
    if q:
        out.append(
            f"| Price | Change | Volume | 52w High | 52w Low | Market Cap |\n"
            f"|---|---|---|---|---|---|\n"
            f"| {_fmt_money(q.get('price'))} | {_fmt_pct(q.get('change_pct'))} | "
            f"{_fmt_int(q.get('volume'))} | {_fmt_money(q.get('year_high'))} | "
            f"{_fmt_money(q.get('year_low'))} | {_fmt_market_cap(q.get('market_cap'))} |\n\n"
        )
    else:
        out.append("*quote unavailable*\n\n")

    # Components
    out.append("## Components (raw measurements)\n")
    out.append("| 維度 | 數值 |\n|---|---|\n")
    rows = [
        ("RSI(14) latest", c.get("rsi_14_latest")),
        ("RSI 連續超買日數 (≥70)", c.get("rsi_overbought_days")),
        ("RSI 30d 峰值", c.get("rsi_peak_recent")),
        ("Price / SMA50", c.get("price_to_sma50_ratio")),
        ("Price / SMA200", c.get("price_to_sma200_ratio")),
        ("SMA200 突破多少日前", c.get("sma200_breakout_days_ago")),
        ("成交量 baseline 30d avg", f"{(c.get('volume_baseline_30d_avg') or 0):,}"),
        ("成交量 recent 20d avg", f"{(c.get('volume_recent_20d_avg') or 0):,}"),
        ("Volume multiplier", c.get("volume_multiplier")),
        ("Gap-up (≥5%) 4w 個數", c.get("gap_up_density_4w")),
        ("Distribution days 25d", c.get("distribution_days_25d")),
        ("Stalling days 25d", c.get("stalling_days_25d")),
        ("Failed rally signal", c.get("failed_rally_signal")),
        ("Sell-side PT raise 30d", c.get("pt_raise_30d")),
        ("Sell-side PT raise 60d", c.get("pt_raise_60d")),
        ("Retail mention 24h ($cashtag)", c.get("retail_mention_24h")),
        ("Retail mention 倍數 vs 7d", c.get("retail_mention_multiplier")),
        ("News mention 30d", c.get("media_mention_30d")),
        ("News source diversity", c.get("media_source_diversity")),
        ("VIX", c.get("vix_now")),
        ("Breadth 200dma %", c.get("breadth_200dma_pct")),
    ]
    for k, v in rows:
        out.append(f"| {k} | {v if v is not None else '—'} |\n")
    out.append("\n")

    # Triggered conditions
    trig = data.get("stage_components_triggered") or []
    if trig:
        out.append(f"## 命中條件 (Stage {stage})\n")
        for t_str in trig:
            out.append(f"- ✓ {t_str}\n")
        out.append("\n")

    # Scenarios
    sc = data.get("scenarios") or []
    if sc:
        out.append("## 4-Scenario R/R\n")
        out.append("| 情境 | 機率 | 目標% | 目標價 |\n|---|---|---|---|\n")
        for s in sc:
            out.append(f"| {s['label']} | {s['prob']*100:.0f}% | "
                       f"{s['target_pct']:+.1f}% | ${s.get('target_price', '—')} |\n")
        out.append(f"\n**期望值: E[R] = {er:+.2f}%**\n\n")

    # All stage scores (audit trail)
    all_scores = data.get("all_stage_scores") or {}
    if all_scores:
        out.append("## 全 Stage 評分 (audit)\n")
        out.append("| Stage | Confidence | Triggered |\n|---|---|---|\n")
        for skey, sd in all_scores.items():
            trig_count = len(sd.get("triggered", []))
            out.append(f"| {skey} | {sd.get('confidence', 0):.2f} | {trig_count} |\n")
        out.append("\n")

    # Input health
    ih = data.get("input_health") or {}
    if ih:
        out.append("## Input Health\n")
        for k, v in ih.items():
            mark = "✅" if v else "⚠️"
            out.append(f"- {mark} `{k}` = {v}\n")
        out.append("\n")

    out.append("---\n")
    out.append("*Generated by `skills/narrative-pulse-detector` — 探索層,不進入 investment_protocol Arbiter。*\n")

    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--output", default="", help="output .md path (default: stdout)")
    ap.add_argument("--date", default="", help="cache date YYYY-MM-DD (default: today)")
    args = ap.parse_args()

    date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_fp = CACHE_DIR / f"{args.ticker.upper()}_{date}.json"
    if not cache_fp.exists():
        print(f"[render] cache miss: {cache_fp}; run pulse.py first", file=sys.stderr)
        sys.exit(1)

    with open(cache_fp, encoding="utf-8") as f:
        data = json.load(f)

    md = render_markdown(data)
    if args.output:
        out_p = REPO_ROOT / args.output if not Path(args.output).is_absolute() else Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"[render] wrote {out_p}", file=sys.stderr)
    else:
        print(md)


if __name__ == "__main__":
    main()
