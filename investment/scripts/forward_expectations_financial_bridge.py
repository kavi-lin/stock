"""Ticker-neutral forward financial bridge for Forward Expectations.

This module maps sourced forward revenue/EPS expectations into a simplified
P&L/FCF bridge. It is deliberately conservative: no LLM arithmetic, no sector
special cases, no valuation output, and no invented inputs. Missing conversion
inputs degrade the bridge instead of filling precise assumptions.
"""
from __future__ import annotations

import argparse
import json
import math
import sys

DEFAULT_TAX_RATE = 0.21
MIN_CORE_ROWS = 1


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _pos(value):
    value = _num(value)
    return value if value is not None and value > 0 else None


def _ratio(value):
    value = _num(value)
    return value if value is not None and -1.0 <= value <= 2.0 else None


def _round(value, digits=4):
    value = _num(value)
    if value is None:
        return None
    return round(value, digits)


def _median(values):
    values = sorted(v for v in (_num(v) for v in values) if v is not None)
    if not values:
        return None
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


def _last_four(rows):
    return [row for row in (rows or []) if isinstance(row, dict)][:4]


def _latest_annual_estimates(earnings_cache: dict):
    rows = [
        row for row in (earnings_cache.get("annual_estimates") or [])
        if isinstance(row, dict) and row.get("date")
    ]
    return sorted(rows, key=lambda row: row["date"])


def _historical_margins(earnings_cache: dict):
    derived = earnings_cache.get("derived") or {}
    margins = _last_four(derived.get("margins_8q") or [])

    gross = _median([row.get("gross") for row in margins])
    operating = _median([row.get("operating") for row in margins])
    net = _median([row.get("net") for row in margins])
    source = "derived.margins_8q_latest4_median"

    if gross is None or operating is None or net is None:
        pnl = _last_four(earnings_cache.get("quarterly_pnl") or [])
        if gross is None:
            gross = _median([
                row.get("grossProfit") / row.get("revenue")
                for row in pnl
                if _pos(row.get("grossProfit")) and _pos(row.get("revenue"))
            ])
        if operating is None:
            operating = _median([
                row.get("operatingIncome") / row.get("revenue")
                for row in pnl
                if _num(row.get("operatingIncome")) is not None and _pos(row.get("revenue"))
            ])
        if net is None:
            net = _median([
                row.get("netIncome") / row.get("revenue")
                for row in pnl
                if _num(row.get("netIncome")) is not None and _pos(row.get("revenue"))
            ])
        source = "quarterly_pnl_latest4_median"

    return {
        "gross_margin": _ratio(gross),
        "operating_margin": _ratio(operating),
        "net_margin": _ratio(net),
        "source": source,
    }


def _fcf_margin(earnings_cache: dict):
    derived = earnings_cache.get("derived") or {}
    cf_quality = derived.get("cash_flow_quality") or {}
    margin = _ratio(cf_quality.get("fcf_margin"))
    if margin is not None:
        return margin, "derived.cash_flow_quality.fcf_margin"

    pnl = _last_four(earnings_cache.get("quarterly_pnl") or [])
    cash_flow = _last_four(earnings_cache.get("cash_flow") or [])
    revenue = sum(row.get("revenue") for row in pnl if _pos(row.get("revenue")))
    fcf = sum(row.get("freeCashFlow") for row in cash_flow if _num(row.get("freeCashFlow")) is not None)
    if revenue:
        return _ratio(fcf / revenue), "cash_flow_latest4_sum/free_revenue_latest4_sum"
    return None, None


def _capex_intensity(earnings_cache: dict):
    derived = earnings_cache.get("derived") or {}
    cf_quality = derived.get("cash_flow_quality") or {}
    intensity = _ratio(cf_quality.get("capex_intensity"))
    if intensity is not None:
        return intensity, "derived.cash_flow_quality.capex_intensity"

    pnl = _last_four(earnings_cache.get("quarterly_pnl") or [])
    cash_flow = _last_four(earnings_cache.get("cash_flow") or [])
    revenue = sum(row.get("revenue") for row in pnl if _pos(row.get("revenue")))
    capex = sum(abs(row.get("capitalExpenditure")) for row in cash_flow if _num(row.get("capitalExpenditure")) is not None)
    if revenue:
        return _ratio(capex / revenue), "cash_flow_latest4_sum/revenue_latest4_sum"
    return None, None


def _share_count(earnings_cache: dict):
    for row in _last_four(earnings_cache.get("quarterly_pnl") or []):
        shares = _pos(row.get("weightedAverageShsOutDil"))
        if shares:
            return shares, "quarterly_pnl.weightedAverageShsOutDil"
    ev = earnings_cache.get("enterprise_value") or {}
    shares = _pos(ev.get("numberOfShares"))
    if shares:
        return shares, "enterprise_value.numberOfShares"
    return None, None


def _tax_and_other_rate(operating_margin, net_margin):
    operating_margin = _ratio(operating_margin)
    net_margin = _ratio(net_margin)
    if operating_margin is None or operating_margin <= 0 or net_margin is None:
        return DEFAULT_TAX_RATE, "fallback_default_tax_rate"
    rate = 1 - (net_margin / operating_margin)
    return _round(rate, 4), "observed_net_to_operating_bridge"


def _amount(value, margin):
    value = _num(value)
    margin = _num(margin)
    if value is None or margin is None:
        return None
    return value * margin


def _range_amount(source: dict, multiplier):
    if source is None or multiplier is None:
        return {"point": None, "low": None, "high": None}
    low = _amount(source.get("low"), multiplier)
    high = _amount(source.get("high"), multiplier)
    point = _amount(source.get("point"), multiplier)
    return {
        "point": _round(point, 0),
        "low": _round(low, 0),
        "high": _round(high, 0),
    }


def _consensus_value(row: dict, metric: str):
    avg = _pos(row.get(f"{metric}_avg"))
    low = _pos(row.get(f"{metric}_low"))
    high = _pos(row.get(f"{metric}_high"))
    return {
        "point": avg,
        "low": low,
        "high": high,
        "source": "annual_estimates",
    }


def _guidance_by_period(guidance_promoted: list[dict]):
    by_period = {}
    for item in guidance_promoted or []:
        if not isinstance(item, dict) or not item.get("numeric_eligible"):
            continue
        period = item.get("period")
        metric = item.get("metric")
        if not period or not metric:
            continue
        by_period.setdefault(str(period), {}).setdefault(metric, []).append({
            "metric": metric,
            "value": item.get("value"),
            "unit": item.get("unit"),
            "source_ref": item.get("source_ref"),
            "published_at": item.get("published_at"),
            "guidance_kind": item.get("guidance_kind"),
            "policy": "Guidance is overlay evidence; ranges remain ranges and do not overwrite consensus by default.",
        })
    return by_period


def _period_guidance(overlays: dict, date: str):
    year = date[:4] if date else None
    matches = {}
    if not year:
        return matches
    for period, metrics in overlays.items():
        if year in str(period):
            matches.update(metrics)
    return matches


def _consistency_checks(row: dict):
    checks = []
    eps_net = _num((row.get("eps_implied_net_income") or {}).get("point"))
    margin_net = _num((row.get("net_income_from_margin") or {}).get("point"))
    if eps_net is not None and margin_net is not None and abs(eps_net) + abs(margin_net) > 0:
        gap = (eps_net - margin_net) / max(abs(margin_net), 1)
        checks.append({
            "check": "eps_vs_margin_net_income",
            "gap_pct": _round(gap, 4),
            "status": "wide_gap" if abs(gap) > 0.30 else "ok",
            "note": "Compares consensus EPS implied net income with historical-margin implied net income.",
        })
    fcf = _num((row.get("free_cash_flow") or {}).get("point"))
    revenue = _num((row.get("revenue") or {}).get("point"))
    if fcf is not None and revenue is not None:
        checks.append({
            "check": "fcf_margin_sign",
            "status": "negative_fcf" if fcf < 0 else "ok",
            "fcf_margin": _round(fcf / revenue, 4) if revenue else None,
        })
    return checks


def build_financial_bridge(earnings_cache: dict, guidance_promoted: list[dict] | None = None,
                           generated_at: str | None = None) -> dict:
    """Build a conservative forward financial bridge from sourced estimates."""
    estimates = _latest_annual_estimates(earnings_cache)
    margins = _historical_margins(earnings_cache)
    fcf_margin, fcf_source = _fcf_margin(earnings_cache)
    capex_intensity, capex_source = _capex_intensity(earnings_cache)
    shares, shares_source = _share_count(earnings_cache)
    tax_rate, tax_source = _tax_and_other_rate(margins.get("operating_margin"), margins.get("net_margin"))

    missing = []
    if not estimates:
        missing.append("annual_estimates")
    for key in ("gross_margin", "operating_margin", "net_margin"):
        if margins.get(key) is None:
            missing.append(key)
    if fcf_margin is None:
        missing.append("fcf_margin")
    if shares is None:
        missing.append("diluted_share_count")

    overlays = _guidance_by_period(guidance_promoted or [])
    rows = []
    for estimate in estimates:
        revenue = _consensus_value(estimate, "revenue")
        eps = _consensus_value(estimate, "eps")
        if revenue["point"] is None:
            continue
        row = {
            "date": estimate.get("date"),
            "forecast_basis": "consensus_annual_estimates",
            "revenue": {k: _round(v, 0) if k in {"point", "low", "high"} else v for k, v in revenue.items()},
            "gross_profit": _range_amount(revenue, margins.get("gross_margin")),
            "operating_income": _range_amount(revenue, margins.get("operating_margin")),
            "tax_and_other_rate": {
                "point": tax_rate,
                "source": tax_source,
                "note": "Includes tax plus below-operating items because cache provides net margin, not a clean tax schedule.",
            },
            "net_income_from_margin": _range_amount(revenue, margins.get("net_margin")),
            "eps_consensus": {
                "point": _round(eps.get("point"), 4),
                "low": _round(eps.get("low"), 4),
                "high": _round(eps.get("high"), 4),
                "source": eps.get("source"),
            },
            "eps_implied_net_income": _range_amount(eps, shares),
            "free_cash_flow": _range_amount(revenue, fcf_margin),
            "capex": _range_amount(revenue, capex_intensity),
            "guidance_overlay": _period_guidance(overlays, estimate.get("date")),
        }
        row["consistency_checks"] = _consistency_checks(row)
        rows.append(row)

    warnings = []
    if tax_source == "observed_net_to_operating_bridge" and _num(tax_rate) is not None and tax_rate < 0:
        warnings.append("negative_observed_tax_and_other_rate_non_operating_items_or_timing_effects")
    if margins.get("gross_margin") is not None and margins.get("gross_margin") > 1:
        warnings.append("gross_margin_above_100pct_check_cache_quality")
    if len(rows) < MIN_CORE_ROWS:
        warnings.append("no_forward_revenue_rows")

    available = bool(rows) and not missing
    status = "available" if available else "insufficient_inputs"
    return {
        "available": available,
        "status": status,
        "generated_at": generated_at,
        "forecast_basis": "consensus_annual_estimates_plus_historical_conversion",
        "historical_conversion": {
            "gross_margin": _round(margins.get("gross_margin")),
            "operating_margin": _round(margins.get("operating_margin")),
            "net_margin": _round(margins.get("net_margin")),
            "source": margins.get("source"),
            "fcf_margin": _round(fcf_margin),
            "fcf_margin_source": fcf_source,
            "capex_intensity": _round(capex_intensity),
            "capex_intensity_source": capex_source,
            "diluted_share_count": _round(shares, 0),
            "diluted_share_count_source": shares_source,
            "tax_and_other_rate": tax_rate,
            "tax_and_other_rate_source": tax_source,
        },
        "rows": rows,
        "missing_inputs": missing,
        "warnings": warnings,
        "policy": (
            "Shadow-only financial bridge. It maps sourced forward estimates through observed "
            "historical conversion ratios; it is not a valuation model and must not alter live decisions."
        ),
    }


def main():
    ap = argparse.ArgumentParser(description="Build Forward Expectations financial bridge from an earnings cache")
    ap.add_argument("--earnings-cache-file", required=True)
    args = ap.parse_args()
    try:
        with open(args.earnings_cache_file, encoding="utf-8") as handle:
            earnings_cache = json.load(handle)
    except Exception as exc:
        print(json.dumps({"error": f"unparseable earnings cache: {exc}"}))
        sys.exit(1)
    print(json.dumps(build_financial_bridge(earnings_cache), ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
