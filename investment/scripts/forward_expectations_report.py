"""Markdown renderer for Forward Expectations shadow output.

Renders a human-readable advisory section from a forward_expectations snapshot.
This is presentation only: no valuation math, no decision changes, no schema
mutation.
"""
from __future__ import annotations

import argparse
import json
import math
import sys


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _fmt_pct(value):
    value = _num(value)
    return "N/A" if value is None else f"{value * 100:.1f}%"


def _fmt_mult(value):
    value = _num(value)
    return "N/A" if value is None else f"{value:.2f}x"


def _fmt_gap_pct(value):
    value = _num(value)
    return "N/A" if value is None else f"{value * 100:.0f}%"


def _bullet(label: str, value) -> str:
    return f"- **{label}**: {value}"


def _independent_summary(independent: dict) -> str:
    if independent.get("available"):
        return f"available, revenue CAGR {_fmt_pct(independent.get('revenue_cagr'))}"
    reason = independent.get("reason") or "unavailable"
    missing = independent.get("missing_numeric_drivers") or independent.get("missing_driver_evidence") or []
    if missing:
        return f"blocked ({reason}); missing {', '.join(missing[:5])}"
    return f"blocked ({reason})"


def _matrix_lines(snapshot: dict):
    consensus = snapshot.get("consensus_lane") or {}
    market = snapshot.get("market_implied_lane") or {}
    base = snapshot.get("base_rate_lane") or {}
    independent = snapshot.get("independent_lane") or {}
    lines = [
        "### Expectations Matrix",
        _bullet("Consensus revenue CAGR", _fmt_pct(consensus.get("revenue_cagr"))),
        _bullet("Consensus EPS CAGR", _fmt_pct(consensus.get("eps_cagr"))),
        _bullet("Market-implied FCF CAGR", _fmt_pct(market.get("required_fcf_cagr"))),
        _bullet("Independent lane", _independent_summary(independent)),
        _bullet("Base-rate revenue CAGR", _fmt_pct(base.get("peer_rev_cagr_median"))),
    ]
    if market.get("out_of_range") is True:
        lines.append("- **Market-implied pressure**: reverse DCF is out_of_range")
    return lines


def _gap_lines(snapshot: dict):
    gap = snapshot.get("expectations_gap") or {}
    summary = gap.get("summary") or {}
    lines = [
        "### Expectations Gap",
        _bullet("Status", summary.get("status") or "unavailable"),
        _bullet("Same-metric gap count", summary.get("same_metric_gap_count", 0)),
    ]
    same_metric = gap.get("same_metric_gaps") or []
    if same_metric:
        lines.append("")
        lines.append("| Metric | Left | Right | Delta | Ratio | Verdict |")
        lines.append("|---|---:|---:|---:|---:|---|")
        for row in same_metric[:8]:
            lines.append(
                "| {metric} | {left} {left_value} | {right} {right_value} | {delta} | {ratio} | {verdict} |".format(
                    metric=row.get("metric") or "",
                    left=row.get("left") or "",
                    left_value=_fmt_pct(row.get("left_value")),
                    right=row.get("right") or "",
                    right_value=_fmt_pct(row.get("right_value")),
                    delta=_fmt_pct(row.get("delta")),
                    ratio=_fmt_mult(row.get("ratio")),
                    verdict=row.get("verdict") or "",
                )
            )
    else:
        unavailable = gap.get("unavailable_same_metric") or []
        reason = "; ".join(
            f"{row.get('metric')}: {row.get('status')}" for row in unavailable[:4]
        ) or "no same-metric comparator"
        lines.append(_bullet("Same-metric gap", f"unavailable ({reason})"))
    cross = gap.get("cross_metric_observations") or []
    if cross:
        lines.append("")
        lines.append("### Cross-Metric Observations")
        for item in cross[:5]:
            lines.append(f"- {item.get('observation')}: descriptive only; no numeric verdict.")
    return lines


def _bridge_risk_lines(snapshot: dict):
    gap = snapshot.get("expectations_gap") or {}
    bridge = snapshot.get("forward_financial_bridge") or {}
    risks = gap.get("financial_bridge_risks") or []
    lines = ["### Financial Bridge Risk"]
    if not bridge.get("available"):
        missing = ", ".join(bridge.get("missing_inputs") or [])
        lines.append(f"- Bridge unavailable: {bridge.get('status') or 'insufficient_inputs'}" + (f" ({missing})" if missing else ""))
        return lines
    if not risks:
        lines.append("- No bridge risk flags emitted.")
        return lines
    for risk in risks[:8]:
        if risk.get("risk"):
            lines.append(f"- {risk['risk']} ({risk.get('severity', 'medium')})")
            continue
        date = risk.get("date") or "unknown period"
        check = risk.get("check") or "check"
        status = risk.get("status") or "flag"
        if risk.get("gap_pct") is not None:
            detail = f"{_fmt_gap_pct(risk.get('gap_pct'))} gap"
        elif risk.get("fcf_margin") is not None:
            detail = f"FCF margin {_fmt_pct(risk.get('fcf_margin'))}"
        else:
            detail = status
        lines.append(f"- {date}: {check} = {status} ({detail})")
    return lines


def _scenario_lines(snapshot: dict):
    scenarios = snapshot.get("operating_driver_scenarios") or {}
    policy = snapshot.get("scenario_policy") or {}
    lines = ["### Operating-Driver Scenarios"]
    if not scenarios:
        lines.append(f"- Scenario builder unavailable; policy status: {policy.get('status') or 'unknown'}.")
        return lines
    lines.append(_bullet("Mode", scenarios.get("mode") or scenarios.get("status") or "unavailable"))
    cases = scenarios.get("cases") or []
    if cases:
        lines.append("")
        driver_keys = []
        for case in cases:
            for key in (case.get("operating_drivers") or {}):
                if key not in driver_keys:
                    driver_keys.append(key)
        if driver_keys == ["revenue_cagr"]:
            lines.append("| Case | Revenue CAGR Driver | Method |")
            lines.append("|---|---:|---|")
        else:
            lines.append("| Case | Drivers | Method |")
            lines.append("|---|---|---|")
        for case in cases:
            drivers = case.get("operating_drivers") or {}
            changes = case.get("driver_changes") or []
            method = (changes[0] or {}).get("method") if changes else ""
            if driver_keys == ["revenue_cagr"]:
                display = _fmt_pct(drivers.get("revenue_cagr"))
            else:
                display = ", ".join(f"{key}={_fmt_pct(value) if key.endswith('_cagr') or key.endswith('_conversion') or key.endswith('_exposure') or key.endswith('_rate_or_value_per_unit') else value}" for key, value in drivers.items())
            lines.append(f"| {case.get('case') or ''} | {display} | {method or 'driver_case'} |")
        lines.append("- Scenario output is operating-driver only; no fair value or target price is produced.")
        return lines
    overlays = scenarios.get("guidance_overlays") or []
    if overlays:
        lines.append("")
        lines.append("Guidance overlays:")
        for item in overlays[:6]:
            value = item.get("value")
            if isinstance(value, dict):
                display = f"range {value.get('low')} - {value.get('high')}"
            else:
                display = value if value is not None else "N/A"
            lines.append(f"- {item.get('metric') or 'guidance'}: {display} ({item.get('policy') or 'display_only'})")
    watchlist = scenarios.get("qualitative_watchlist") or []
    if watchlist:
        lines.append("")
        lines.append("Qualitative watchlist:")
        for item in watchlist[:8]:
            missing = item.get("missing") or []
            suffix = f"; missing {', '.join(missing)}" if missing else ""
            lines.append(f"- {item.get('item')}: {item.get('reason')}{suffix}")
    if not overlays and not watchlist:
        lines.append("- No numeric scenario or overlay is allowed from current inputs.")
    return lines


def _future_price_lines(snapshot: dict):
    price_range = snapshot.get("future_price_range") or {}
    lines = ["### Future Price Range"]
    if not price_range:
        lines.append("- Future price range unavailable: mapper not run.")
        return lines
    lines.append(_bullet("Status", price_range.get("status") or "unavailable"))
    lines.append(_bullet("Method", price_range.get("method") or "N/A"))
    lines.append(_bullet("Horizon", price_range.get("horizon_date") or "N/A"))
    if price_range.get("available") and price_range.get("cases"):
        lines.append("")
        lines.append("| Case | Target Price | Upside | Metric | Multiple |")
        lines.append("|---|---:|---:|---|---:|")
        for key in ("bear", "base", "bull"):
            case = (price_range.get("cases") or {}).get(key) or {}
            target = case.get("target_price")
            upside = case.get("upside_pct")
            lines.append(
                f"| {key} | ${target:.2f} | {upside:+.1f}% | {case.get('metric') or ''} {_fmt_mult(case.get('metric_value'))} | {_fmt_mult(case.get('multiple'))} |"
                if target is not None and upside is not None
                else f"| {key} | N/A | N/A | {case.get('metric') or ''} | N/A |"
            )
        r = price_range.get("range") or {}
        lines.append(_bullet("Range", f"${r.get('low')} / ${r.get('base')} / ${r.get('high')}"))
    else:
        warnings = ", ".join(price_range.get("warnings") or [])
        lines.append(f"- Unavailable: {warnings or 'insufficient inputs'}")
    lines.append("- Shadow-only. This is not live fair_value_summary and does not change decision rules.")
    return lines


def render_markdown(snapshot: dict) -> str:
    ticker = snapshot.get("ticker") or "UNKNOWN"
    generated_at = snapshot.get("generated_at") or "unknown"
    lines = [
        "## Forward Expectations Shadow",
        "",
        f"> Ticker: `{ticker}` | Generated: `{generated_at}` | Shadow-only advisory.",
        "",
    ]
    lines.extend(_matrix_lines(snapshot))
    lines.append("")
    lines.extend(_gap_lines(snapshot))
    lines.append("")
    lines.extend(_bridge_risk_lines(snapshot))
    lines.append("")
    lines.extend(_scenario_lines(snapshot))
    lines.append("")
    lines.extend(_future_price_lines(snapshot))
    lines.extend([
        "",
        "### Policy",
        "- Shadow-only. Does not alter fair value, verdict, decision lock, thresholds, or sizing.",
        "- Numeric gaps require the same metric; FCF, EPS, and revenue CAGR are not cross-subtracted.",
    ])
    return "\n".join(lines).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser(description="Render Forward Expectations shadow markdown section")
    ap.add_argument("--snapshot-file", required=True)
    ap.add_argument("--output-file")
    args = ap.parse_args()
    try:
        with open(args.snapshot_file, encoding="utf-8") as handle:
            snapshot = json.load(handle)
    except Exception as exc:
        print(json.dumps({"error": f"unparseable snapshot: {exc}"}))
        sys.exit(1)
    markdown = render_markdown(snapshot)
    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as handle:
            handle.write(markdown)
    else:
        print(markdown, end="")


if __name__ == "__main__":
    main()
