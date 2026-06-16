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

ENGINE_VERSION = "forward_expectations_price_range.py v1.0"
DEFAULT_MULTIPLE_BAND = (0.85, 1.0, 1.15)


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


def _latest_bridge_row(financial_bridge: dict):
    rows = [row for row in (financial_bridge or {}).get("rows") or [] if isinstance(row, dict)]
    if not rows:
        return None
    return sorted(rows, key=lambda row: row.get("date") or "")[-1]


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


def _eps_path(row: dict, current_price, explicit: dict, anchor: dict | None = None):
    eps = _range_values(row.get("eps_consensus"))
    if _pos(eps.get("point")) is None:
        return None
    derived_base = _pos(current_price) / eps["point"] if _pos(current_price) and _pos(eps.get("point")) else None
    multiples, quality = _resolve_multiple(
        explicit, ("pe_range", "forward_pe_range", "multiple_range_effective", "multiple_range"),
        anchor, "pe", derived_base, "current_price / horizon_eps_consensus",
    )
    if not multiples:
        return None
    return {
        "method": "eps_x_pe",
        "multiple_quality": quality,
        "multiple_range": multiples,
        "cases": {
            "bear": _case("bear", eps["low"] * multiples["p25"], current_price, eps["low"], multiples["p25"], "eps_consensus"),
            "base": _case("base", eps["point"] * multiples["p50"], current_price, eps["point"], multiples["p50"], "eps_consensus"),
            "bull": _case("bull", eps["high"] * multiples["p75"], current_price, eps["high"], multiples["p75"], "eps_consensus"),
        },
    }


def _per_share(value, shares):
    value = _num(value)
    shares = _pos(shares)
    if value is None or shares is None:
        return None
    return value / shares


def _revenue_path(row: dict, current_price, explicit: dict, shares, market_cap, anchor: dict | None = None):
    revenue = _range_values(row.get("revenue"))
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


def _fcf_path(row: dict, current_price, explicit: dict, shares, anchor: dict | None = None):
    fcf = _range_values(row.get("free_cash_flow"))
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


def build_future_price_range(
    ticker: str,
    current_price,
    financial_bridge: dict,
    earnings_cache: dict | None = None,
    explicit_multiples: dict | None = None,
    multiple_anchor: dict | None = None,
) -> dict:
    row = _latest_bridge_row(financial_bridge or {})
    base = {
        "engine": ENGINE_VERSION,
        "ticker": ticker,
        "available": False,
        "status": "insufficient_inputs",
        "shadow_only": True,
        "valuation_output": "future_price_range_shadow",
        "changes_live_decision": False,
        "horizon_date": row.get("date") if row else None,
        "method": None,
        "multiple_quality": None,
        "cases": {},
        "range": {"low": None, "base": None, "high": None},
        "multiple_range": None,
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
    shares = _shares(financial_bridge)
    market_cap = _market_cap(earnings_cache, current_price)
    attempts = [
        _eps_path(row, current_price, explicit_multiples, multiple_anchor),
        _revenue_path(row, current_price, explicit_multiples, shares, market_cap, multiple_anchor),
        _fcf_path(row, current_price, explicit_multiples, shares, multiple_anchor),
    ]
    # Prefer a genuine forecast (explicit / price-independent historical regime).
    # Only fall back to the current-price-derived band as a labelled advisory band —
    # that band's base case equals today's price (EXP-R1 tautology), so it is not a forecast.
    forecast = next((a for a in attempts if a and a["multiple_quality"] in ("explicit", "historical")), None)
    advisory = next((a for a in attempts if a and a["multiple_quality"] == "derived"), None)
    chosen = forecast or advisory
    if not chosen:
        return {
            **base,
            "status": "unavailable",
            "warnings": ["no_supported_metric_or_multiple_path"],
        }

    is_advisory = chosen is not forecast
    warnings = []
    if chosen["multiple_range"].get("method") == "current_market_multiple_band":
        warnings.append("derived_current_market_multiple_used")
    if is_advisory:
        warnings.append("current_price_volatility_band_not_forecast")
        if (multiple_anchor or {}).get("warnings"):
            warnings.extend(multiple_anchor["warnings"])
    cases = chosen["cases"]
    return {
        **base,
        "available": True,
        "status": "advisory_band_only" if is_advisory else "available",
        "method": chosen["method"],
        "multiple_quality": chosen["multiple_quality"],
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
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
