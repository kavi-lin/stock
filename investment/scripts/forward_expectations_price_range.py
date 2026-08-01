"""Future price range mapper for Forward Expectations.

This module converts sourced forward financial bridge rows into a shadow-only
future price range. It is not a live fair-value engine and must not write to
decision locks, buy thresholds, or position sizing.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date

ENGINE_VERSION = "forward_expectations_price_range.py v1.3 (explicit terminal horizon + annualized return)"
DEFAULT_MULTIPLE_BAND = (0.85, 1.0, 1.15)
# Terminal coverage is a confidence gate, not a reason to silently substitute a nearer
# fiscal year: compression and margin normalization are terminal-horizon assumptions.
MIN_ANALYSTS = 20

# V4.41.0 — currency normalization. FMP statements/estimates for a foreign-domiciled ADR
# (TSM→TWD, ASML/SAP→EUR, …) are reported in the company's reporting currency, while the
# ADR price / market cap / multiple anchor are in the trading currency (USD). Feeding a
# reporting-currency EPS into a trading-currency P/E inflates the target by the FX rate
# (TSM ~32×). `reporting_to_trading_fx` is the divisor that converts a reporting-currency
# monetary value into the trading currency (e.g. 32.0 for TWD→USD). 1.0 = no conversion.
TRADING_CURRENCY = "USD"
# implied EPS-ratio above which a statement-vs-trading gap is treated as a currency-scale
# mismatch (not estimate noise). TWD≈32 / JPY≈150 / KRW≈1300 all clear this; EUR/GBP (≈1)
# do not and need no conversion (their ≤~10% gap cannot explode a target).
CURRENCY_SCALE_MIN = 5.0
# Defense-in-depth: a base target this far from the current price almost always means a
# currency-unit mismatch slipped through. Drop the (price-basis) forecast to the
# self-consistent advisory band and flag it, rather than write a garbage value to the card.
SANITY_TARGET_CEIL = 6.0
SANITY_TARGET_FLOOR = 1.0 / 6.0


def resolve_reporting_fx(reporting_currency=None, forex_to_usd=None,
                         statement_ttm_eps=None, trading_eps=None) -> dict:
    """Resolve the reporting→trading FX divisor (pure; testable offline).

    Priority: reporting currency == USD → 1.0; explicit FMP forex rate ({CUR}USD price =
    USD per 1 unit of reporting currency) → 1/rate; else an implied ratio from
    statement TTM EPS vs trading (ADR) EPS when the gap is currency-scale; else parity.
    The price-range sanity gate is the backstop when this returns parity but a mismatch
    still exists (no-fetch / missing inputs)."""
    cur = (reporting_currency or "").upper() or None
    if cur == TRADING_CURRENCY:
        return {"fx": 1.0, "source": "reporting_currency_usd", "reporting_currency": cur}
    rate = _pos(forex_to_usd)
    if cur and rate:
        return {"fx": round(1.0 / rate, 6), "source": "fmp_forex", "reporting_currency": cur}
    se, te = _num(statement_ttm_eps), _pos(trading_eps)
    if se is not None and te:
        ratio = se / te
        if ratio > CURRENCY_SCALE_MIN or 0 < ratio < (1.0 / CURRENCY_SCALE_MIN):
            return {"fx": round(ratio, 6), "source": "implied_from_trading_eps",
                    "reporting_currency": cur}
    return {"fx": 1.0, "source": "assumed_parity", "reporting_currency": cur}


def _fx_range(node, fx):
    """Divide the low/point/high monetary fields of a range node by the FX divisor."""
    fx = _pos(fx) or 1.0
    if fx == 1.0 or not isinstance(node, dict):
        return node
    return {k: (v / fx if (k in {"point", "low", "high"} and _num(v) is not None) else v)
            for k, v in node.items()}


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _pos(value):
    value = _num(value)
    return value if value is not None and value > 0 else None


def _round(value, digits=2):
    value = _num(value)
    return round(value, digits) if value is not None else None


def _ratio_upside(target, current_price):
    target = _num(target)
    current_price = _pos(current_price)
    if target is None or current_price is None:
        return None
    return round((target / current_price - 1) * 100, 1)


def _range_values(node: dict):
    if not isinstance(node, dict):
        return {"low": None, "point": None, "high": None}
    low = _num(node.get("low"))
    point = _num(node.get("point"))
    high = _num(node.get("high"))
    return {
        "low": low if low is not None else point,
        "point": point,
        "high": high if high is not None else point,
    }


def _explicit_range(explicit: dict, names: tuple[str, ...]):
    for name in names:
        value = (explicit or {}).get(name)
        if isinstance(value, dict):
            p25 = _pos(value.get("p25") or value.get("pe_p25") or value.get("ps_p25") or value.get("pfcf_p25"))
            p50 = _pos(value.get("p50") or value.get("pe_p50") or value.get("ps_p50") or value.get("pfcf_p50"))
            p75 = _pos(value.get("p75") or value.get("pe_p75") or value.get("ps_p75") or value.get("pfcf_p75"))
            if p25 and p50 and p75:
                return {
                    "p25": p25,
                    "p50": p50,
                    "p75": p75,
                    "source": value.get("source") or f"explicit:{name}",
                    "method": "explicit_multiple_range",
                }
    return None


def _derived_band(base_multiple: float, source: str):
    base = _pos(base_multiple)
    if base is None:
        return None
    lo, mid, hi = DEFAULT_MULTIPLE_BAND
    return {
        "p25": round(base * lo, 4),
        "p50": round(base * mid, 4),
        "p75": round(base * hi, 4),
        "source": source,
        "method": "current_market_multiple_band",
        "band_policy": "p25/p75 are +/-15% around current implied forward multiple; shadow only.",
    }


def _historical_band(anchor: dict, metric_key: str):
    """Price-independent multiple from the ticker's own historical regime (EXP-R1)."""
    band = ((anchor or {}).get("by_metric") or {}).get(metric_key)
    if not isinstance(band, dict) or not band.get("usable"):
        return None
    p25, p50, p75 = _pos(band.get("p25")), _pos(band.get("p50")), _pos(band.get("p75"))
    if not (p25 and p50 and p75):
        return None
    compressed = bool(band.get("compressed"))
    return {
        "p25": p25,
        "p50": p50,
        "p75": p75,
        "source": band.get("source") or "fmp_ratios_annual_history",
        "method": "historical_regime_growth_compressed" if compressed else "historical_multiple_regime",
        "history_points": band.get("n"),
        "dispersion_ratio": band.get("dispersion_ratio"),
        # EXP-3.4 compression transparency
        "compressed": compressed,
        "growth_tier": band.get("growth_tier"),
        "growth_used": band.get("growth_used"),
        "compression_factor": band.get("compression_factor"),
        "pe_ceiling_applied": band.get("pe_ceiling_applied"),
        "historical_band": band.get("historical_band"),
        "band_policy": ("p25/p50/p75 = historical regime compressed toward forward-growth-justified level (EXP-3.4); shadow only."
                        if compressed else
                        "p25/p50/p75 from the ticker's own historical valuation regime; price-independent; shadow only."),
    }


def _resolve_multiple(explicit, names, anchor, metric_key, derived_base, derived_source):
    """Priority: explicit input > historical regime anchor > derived current-price band.
    Returns (multiple_range, quality) with quality in explicit|historical|derived."""
    m = _explicit_range(explicit, names)
    if m:
        return m, "explicit"
    hist = _historical_band(anchor, metric_key)
    if hist:
        return hist, "historical"
    derived = _derived_band(derived_base, derived_source)
    if derived:
        return derived, "derived"
    return None, None


def _bridge_rows(financial_bridge: dict):
    rows = [row for row in (financial_bridge or {}).get("rows") or [] if isinstance(row, dict)]
    return sorted(rows, key=lambda row: row.get("date") or "")


def _latest_bridge_row(financial_bridge: dict):
    rows = _bridge_rows(financial_bridge)
    return rows[-1] if rows else None


def _parse_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def _years_between(as_of, target):
    d0, d1 = _parse_date(as_of), _parse_date(target)
    if d0 is None or d1 is None:
        return None
    return (d1 - d0).days / 365.25


def _annualized(target, current_price, years):
    target = _num(target)
    current_price = _pos(current_price)
    years = _num(years)
    if target is None or current_price is None or years is None or years <= 0 or target <= 0:
        return None
    return round(((target / current_price) ** (1.0 / years) - 1.0) * 100, 1)


def _coverage_count(row: dict):
    cov = (row or {}).get("coverage") or {}
    counts = [_num(cov.get("num_analysts_revenue")), _num(cov.get("num_analysts_eps"))]
    counts = [c for c in counts if c is not None]
    return min(counts) if counts else None


def _shares(financial_bridge: dict):
    return _pos(((financial_bridge or {}).get("historical_conversion") or {}).get("diluted_share_count"))


def _market_cap(earnings_cache: dict, current_price):
    snap = earnings_cache.get("snapshot") or {}
    cap = _pos(snap.get("marketCap"))
    if cap:
        return cap
    shares = _pos((earnings_cache.get("enterprise_value") or {}).get("numberOfShares"))
    price = _pos(current_price)
    if shares and price:
        return shares * price
    return None


def _case(label, target, current_price, metric_value, multiple, metric_name):
    return {
        "case": label,
        "target_price": _round(target),
        "upside_pct": _ratio_upside(target, current_price),
        "metric": metric_name,
        "metric_value": _round(metric_value, 4),
        "multiple": _round(multiple, 4),
    }


def _eps_path(row: dict, current_price, explicit: dict, anchor: dict | None = None,
              eps_override: dict | None = None, fx: float = 1.0):
    # EXP-3.4b: a margin-normalized EPS band replaces held-margin consensus EPS when supplied.
    override_ok = isinstance(eps_override, dict) and _pos(_range_values(eps_override).get("point")) is not None
    # V4.41.0: convert reporting-currency EPS into the trading currency before it meets a
    # trading-currency (price-derived / historical / explicit) multiple.
    eps = _range_values(_fx_range(eps_override if override_ok else row.get("eps_consensus"), fx))
    eps_basis = "margin_normalized" if override_ok else "consensus"
    if _pos(eps.get("point")) is None:
        return None
    derived_base = _pos(current_price) / eps["point"] if _pos(current_price) and _pos(eps.get("point")) else None
    multiples, quality = _resolve_multiple(
        explicit, ("pe_range", "forward_pe_range", "multiple_range_effective", "multiple_range"),
        anchor, "pe", derived_base, "current_price / horizon_eps_consensus",
    )
    if not multiples:
        return None
    metric_label = "eps_margin_normalized" if override_ok else "eps_consensus"
    return {
        "method": "eps_x_pe",
        "multiple_quality": quality,
        "eps_basis": eps_basis,
        "multiple_range": multiples,
        "cases": {
            "bear": _case("bear", eps["low"] * multiples["p25"], current_price, eps["low"], multiples["p25"], metric_label),
            "base": _case("base", eps["point"] * multiples["p50"], current_price, eps["point"], multiples["p50"], metric_label),
            "bull": _case("bull", eps["high"] * multiples["p75"], current_price, eps["high"], multiples["p75"], metric_label),
        },
    }


def _per_share(value, shares):
    value = _num(value)
    shares = _pos(shares)
    if value is None or shares is None:
        return None
    return value / shares


def _revenue_path(row: dict, current_price, explicit: dict, shares, market_cap,
                  anchor: dict | None = None, fx: float = 1.0):
    # market_cap is trading-currency; convert reporting-currency revenue to match.
    revenue = _range_values(_fx_range(row.get("revenue"), fx))
    rev_ps = {key: _per_share(value, shares) for key, value in revenue.items()}
    if _pos(rev_ps.get("point")) is None:
        return None
    derived_base = market_cap / revenue["point"] if _pos(market_cap) and _pos(revenue.get("point")) else None
    multiples, quality = _resolve_multiple(
        explicit, ("ps_range", "price_to_sales_range"),
        anchor, "ps", derived_base, "current_market_cap / horizon_revenue_consensus",
    )
    if not multiples:
        return None
    return {
        "method": "revenue_per_share_x_ps",
        "multiple_quality": quality,
        "multiple_range": multiples,
        "cases": {
            "bear": _case("bear", rev_ps["low"] * multiples["p25"], current_price, rev_ps["low"], multiples["p25"], "revenue_per_share"),
            "base": _case("base", rev_ps["point"] * multiples["p50"], current_price, rev_ps["point"], multiples["p50"], "revenue_per_share"),
            "bull": _case("bull", rev_ps["high"] * multiples["p75"], current_price, rev_ps["high"], multiples["p75"], "revenue_per_share"),
        },
    }


def _fcf_path(row: dict, current_price, explicit: dict, shares, anchor: dict | None = None, fx: float = 1.0):
    fcf = _range_values(_fx_range(row.get("free_cash_flow"), fx))
    fcf_ps = {key: _per_share(value, shares) for key, value in fcf.items()}
    if _pos(fcf_ps.get("point")) is None:
        return None
    derived_base = _pos(current_price) / fcf_ps["point"] if _pos(current_price) and _pos(fcf_ps.get("point")) else None
    multiples, quality = _resolve_multiple(
        explicit, ("pfcf_range", "price_to_fcf_range", "fcf_multiple_range"),
        anchor, "pfcf", derived_base, "current_price / horizon_fcf_per_share",
    )
    if not multiples:
        return None
    return {
        "method": "fcf_per_share_x_pfcf",
        "multiple_quality": quality,
        "multiple_range": multiples,
        "cases": {
            "bear": _case("bear", fcf_ps["low"] * multiples["p25"], current_price, fcf_ps["low"], multiples["p25"], "fcf_per_share"),
            "base": _case("base", fcf_ps["point"] * multiples["p50"], current_price, fcf_ps["point"], multiples["p50"], "fcf_per_share"),
            "bull": _case("bull", fcf_ps["high"] * multiples["p75"], current_price, fcf_ps["high"], multiples["p75"], "fcf_per_share"),
        },
    }


def _glide(current_price, terminal_target, t_years, total_years):
    """Geometric glide-path price at t_years given a terminal target at total_years.
    implied = current * (terminal/current) ** (t / T). Constant annualized rate."""
    cur = _pos(current_price)
    term = _pos(terminal_target)
    t = _num(t_years)
    total = _num(total_years)
    if None in (cur, term, t, total) or total <= 0 or t <= 0:
        return None
    return cur * (term / cur) ** (t / total)


def build_trajectory(financial_bridge, current_price, terminal_cases, terminal_date, as_of, fx: float = 1.0):
    """Per-fiscal-year ANNUALIZED glide path TO the terminal valuation (the headline
    cases). For a hypergrowth name the near-year price is dominated by an unknowable
    multiple assumption, so re-valuing each FY at today's rich multiple would explode the
    target (tautology trap). Instead we anchor on the terminal margin-normalized fair
    value and report the annualized level implied for each FY along the way, with that
    FY's consensus EPS shown for context. Shadow-only."""
    total_years = _years_between(as_of, terminal_date)
    targets_terminal = {c: _pos((terminal_cases.get(c) or {}).get("target_price")) for c in ("bear", "base", "bull")}
    out = []
    for row in _bridge_rows(financial_bridge):
        yrs = _years_between(as_of, row.get("date"))
        if yrs is None or yrs <= 0:
            continue  # past or already-reported fiscal year — no forward target
        cov = _coverage_count(row)
        fx_div = _pos(fx) or 1.0
        eps_pt = _num((row.get("eps_consensus") or {}).get("point"))
        if eps_pt is not None and fx_div != 1.0:
            eps_pt = eps_pt / fx_div
        implied = {c: _glide(current_price, targets_terminal[c], yrs, total_years) for c in ("bear", "base", "bull")}
        out.append({
            "date": row.get("date"),
            "years_out": round(yrs, 2),
            "coverage": cov,
            "thin_coverage": bool(cov is not None and cov < MIN_ANALYSTS),
            "consensus_eps": _round(eps_pt, 2),
            "is_terminal": row.get("date") == terminal_date,
            "targets": {c: _round(implied[c]) for c in ("bear", "base", "bull")},
            "cumulative_upside_pct": {c: _ratio_upside(implied[c], current_price) for c in ("bear", "base", "bull")},
            "annualized_pct": {c: _annualized(implied[c], current_price, yrs) for c in ("bear", "base", "bull")},
        })
    return out


def build_future_price_range(
    ticker: str,
    current_price,
    financial_bridge: dict,
    earnings_cache: dict | None = None,
    explicit_multiples: dict | None = None,
    multiple_anchor: dict | None = None,
    eps_override: dict | None = None,
    reporting_to_trading_fx: float = 1.0,
    as_of_date=None,
) -> dict:
    # Headline valuation = terminal (farthest) row: that is where growth has cooled enough
    # for the mature-compressed multiple + margin normalization to apply. Near-year targets
    # are derived as an annualized glide path to this terminal (see build_trajectory), NOT
    # by re-valuing each near FY at today's rich multiple.
    row = _latest_bridge_row(financial_bridge or {})
    horizon_basis = "terminal_margin_normalized"
    horizon_years = (round(_years_between(as_of_date, row.get("date")), 2)
                     if row and _years_between(as_of_date, row.get("date")) is not None else None)
    horizon_coverage = _coverage_count(row) if row else None
    base = {
        "engine": ENGINE_VERSION,
        "ticker": ticker,
        "available": False,
        "status": "insufficient_inputs",
        "shadow_only": True,
        "valuation_output": "future_price_range_shadow",
        "changes_live_decision": False,
        "horizon_date": row.get("date") if row else None,
        "horizon_basis": horizon_basis,
        "horizon_years": horizon_years,
        "horizon_coverage": horizon_coverage,
        "horizon_interpretation": "multi_year_terminal_value_not_12m_price_target",
        "horizon_coverage_quality": (
            "unknown" if horizon_coverage is None
            else "adequate" if horizon_coverage >= MIN_ANALYSTS
            else "thin"
        ),
        "reporting_to_trading_fx": round(_pos(reporting_to_trading_fx) or 1.0, 6),
        "method": None,
        "multiple_quality": None,
        "cases": {},
        "range": {"low": None, "base": None, "high": None},
        "multiple_range": None,
        "trajectory": [],
        "warnings": [],
        "policy": (
            "Future price range is shadow-only and must not alter live fair_value_summary, "
            "decision_lock, thresholds, or sizing without explicit user approval."
        ),
    }
    if not row:
        return {**base, "warnings": ["forward_financial_bridge_rows_missing"]}
    if not _pos(current_price):
        return {**base, "warnings": ["current_price_missing"]}

    earnings_cache = earnings_cache or {}
    explicit_multiples = explicit_multiples or {}
    fx = _pos(reporting_to_trading_fx) or 1.0
    shares = _shares(financial_bridge)
    market_cap = _market_cap(earnings_cache, current_price)
    attempts = [
        _eps_path(row, current_price, explicit_multiples, multiple_anchor, eps_override, fx),
        _revenue_path(row, current_price, explicit_multiples, shares, market_cap, multiple_anchor, fx),
        _fcf_path(row, current_price, explicit_multiples, shares, multiple_anchor, fx),
    ]
    # Prefer a genuine forecast (explicit / price-independent historical regime).
    # Only fall back to the current-price-derived band as a labelled advisory band —
    # that band's base case equals today's price (EXP-R1 tautology), so it is not a forecast.
    forecast = next((a for a in attempts if a and a["multiple_quality"] in ("explicit", "historical")), None)
    advisory = next((a for a in attempts if a and a["multiple_quality"] == "derived"), None)

    # V4.41.0 sanity gate: a price-basis forecast whose base target is wildly off the current
    # price (>6× or <1/6) almost certainly means a reporting-vs-trading currency-unit mismatch
    # slipped through (e.g. TWD EPS × USD P/E). Drop it to the self-consistent advisory band
    # (base ≈ current price; FX cancels) rather than write a garbage value to the card.
    def _suspect(attempt):
        if not attempt:
            return False
        ratio = _ratio_upside((attempt["cases"].get("base") or {}).get("target_price"), current_price)
        if ratio is None:
            return False
        mult = ratio / 100.0 + 1.0
        return mult > SANITY_TARGET_CEIL or 0 < mult < SANITY_TARGET_FLOOR

    currency_unit_suspect = False
    if forecast and _suspect(forecast):
        currency_unit_suspect = True
        if not advisory:
            # No price-independent fallback existed (the anchor was usable, so every path
            # returned a historical multiple). Synthesize a current-price-derived band — its
            # base ≈ current price, so the FX unit cancels and it cannot explode.
            advisory = next((a for a in (
                _eps_path(row, current_price, {}, None, eps_override, fx),
                _revenue_path(row, current_price, {}, shares, market_cap, None, fx),
                _fcf_path(row, current_price, {}, shares, None, fx),
            ) if a and a["multiple_quality"] == "derived"), None)
        chosen = advisory or forecast
    else:
        chosen = forecast or advisory
        currency_unit_suspect = bool(chosen and _suspect(chosen))
    if not chosen:
        return {
            **base,
            "status": "unavailable",
            "warnings": ["no_supported_metric_or_multiple_path"],
        }

    is_advisory = chosen is not forecast
    thin_terminal = horizon_coverage is None or horizon_coverage < MIN_ANALYSTS
    warnings = []
    if chosen["multiple_range"].get("method") == "current_market_multiple_band":
        warnings.append("derived_current_market_multiple_used")
    if is_advisory:
        warnings.append("current_price_volatility_band_not_forecast")
        if (multiple_anchor or {}).get("warnings"):
            warnings.extend(multiple_anchor["warnings"])
    if chosen.get("eps_basis") == "margin_normalized":
        warnings.append("eps_margin_normalized")
    if currency_unit_suspect:
        warnings.append("currency_unit_suspect")
    cases = chosen["cases"]
    for case in cases.values():
        case["annualized_pct"] = _annualized(case.get("target_price"), current_price, horizon_years)
    if horizon_years is not None and horizon_years > 1.25:
        warnings.append("multi_year_terminal_range_not_12m_target")
    if horizon_coverage is None:
        warnings.append("terminal_analyst_coverage_unknown")
    elif horizon_coverage < MIN_ANALYSTS:
        warnings.append("thin_terminal_analyst_coverage")
    trajectory = build_trajectory(
        financial_bridge, current_price, cases, row.get("date") if row else None, as_of_date, fx,
    )
    return {
        **base,
        "available": True,
        "status": (
            "advisory_band_only" if is_advisory
            else "low_confidence_terminal_range" if thin_terminal
            else "available"
        ),
        "method": chosen["method"],
        "multiple_quality": chosen["multiple_quality"],
        "trajectory": trajectory,
        "eps_basis": chosen.get("eps_basis", "consensus"),
        "cases": cases,
        "range": {
            "low": cases["bear"]["target_price"],
            "base": cases["base"]["target_price"],
            "high": cases["bull"]["target_price"],
        },
        "multiple_range": chosen["multiple_range"],
        "warnings": warnings,
    }


def main():
    ap = argparse.ArgumentParser(description="Build Future Price Range from a Forward Expectations snapshot")
    ap.add_argument("--snapshot-file", required=True)
    args = ap.parse_args()
    try:
        with open(args.snapshot_file, encoding="utf-8") as handle:
            snapshot = json.load(handle)
    except Exception as exc:
        print(json.dumps({"error": f"unparseable snapshot: {exc}"}))
        sys.exit(1)
    result = build_future_price_range(
        snapshot.get("ticker") or "UNKNOWN",
        snapshot.get("current_price"),
        snapshot.get("forward_financial_bridge") or {},
        snapshot.get("earnings_cache_snapshot") or {},
        snapshot.get("valuation_multiples") or {},
        reporting_to_trading_fx=((snapshot.get("currency_normalization") or {}).get("fx") or 1.0),
        as_of_date=snapshot.get("generated_at") or snapshot.get("as_of_earnings_date"),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
