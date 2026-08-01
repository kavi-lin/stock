#!/usr/bin/env python3
"""
valuation-modeler · auditable 5-year through-cycle FCFF DCF engine.

Every number is computed here — no LLM hand-math. Base assumptions are
auto-derived from FMP historicals + analyst estimates (each field carries
provenance: analyst / derived / override / default) and are overridable via
--overrides file or --set k=v flags. Output JSON's top-level
`fair_value_per_share` is the investment protocol's `dcf_self_built` anchor.

Usage:
    export FMP_API_KEY=...
    python3 dcf.py NVDA --json-only
    python3 dcf.py MSFT --set wacc=0.09 --set terminal_growth=0.03
    python3 dcf.py AAPL --overrides my_assumptions.json --xlsx

Method (see ../SKILL.md):
    revenue growth y1-2 : analyst revenue estimates (clamp [-20%, +60%]);
                          fallback hist CAGR × 0.7 damping (clamp [-10%, +40%])
    revenue growth y3-5 : linear fade to terminal_growth
    structural-shift case: current-FY quarterly roll-forward, capped analyst
                          revenue path, EBIT/D&A/capex fade to normalized state
    legacy case          : 3y historical margin / capex / D&A / NWC averages
    tax rate            : 3y effective, clamp [10%, 35%]
    WACC                : CAPM (beta from FMP profile, rf from fred-macro cache,
                          ERP 4.5% default), clamp [6%, 15%], wacc − g ≥ 2%
    FCFF                : NOPAT + D&A − capex − ΔNWC → Gordon terminal value
    sensitivity         : 5×5 grid, WACC ±1.0% × terminal growth ±0.5%
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

PROJECTION_YEARS = 5
TERMINAL_GROWTH_DEFAULT = 0.025
ERP_DEFAULT = 0.045
DEBT_SPREAD_DEFAULT = 0.015
BETA_OBSERVED_WEIGHT = 2 / 3  # Blume-style mean reversion toward market beta 1.0
WACC_MIN, WACC_MAX = 0.06, 0.15
MIN_WACC_G_SPREAD = 0.02
G1_ANALYST_CLAMP = (-0.20, 0.60)
G1_DERIVED_CLAMP = (-0.10, 0.40)
TAX_CLAMP = (0.10, 0.35)
CAGR_DAMPING = 0.7  # same decay factor as earnings-valuation-forecaster Step 1
THROUGH_CYCLE_GROWTH_CAPS = (0.45, 0.30, 0.20, 0.12, 0.08)
THROUGH_CYCLE_GROWTH_FLOOR = -0.20
EBIT_MARGIN_CLAMP = (-0.10, 0.85)
DA_PCT_CLAMP = (0.01, 0.40)
CAPEX_PCT_CLAMP = (0.02, 0.45)
SALES_TO_CAPITAL_CLAMP = (0.25, 3.0)

OVERRIDABLE = {
    "revenue_growth_y1", "revenue_growth_y2", "terminal_growth", "ebitda_margin",
    "da_pct", "capex_pct", "nwc_pct", "tax_rate", "wacc", "beta", "risk_free",
    "erp", "cost_of_debt",
    "ebit_margin_start", "ebit_margin_terminal", "da_pct_start",
    "da_pct_terminal", "capex_pct_start", "capex_pct_terminal",
}


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _avg_pct(rows: list, num_key: str, den_key: str, n: int = 3, absval: bool = False) -> float | None:
    """Mean of rows[i][num_key] / rows[i][den_key] over the newest n rows."""
    vals = []
    for r in (rows or [])[:n]:
        num, den = _num(r.get(num_key)), _num(r.get(den_key))
        if num is None or not den:
            continue
        vals.append(abs(num) / den if absval else num / den)
    return sum(vals) / len(vals) if vals else None


def _median(values: list[float]) -> float | None:
    vals = sorted(v for v in values if _num(v) is not None)
    if not vals:
        return None
    n = len(vals)
    return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2


def _latest_earnings_context(ticker: str) -> dict:
    """Latest non-infographic earnings cache; deterministic and read-only."""
    cache_dir = BASE_DIR / "skills" / "earnings-analyst" / "cache"
    candidates = sorted(
        (p for p in cache_dir.glob(f"{ticker.upper()}_*.json")
         if not p.name.endswith(".infographic.json")),
        key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        return {}
    try:
        payload = json.loads(candidates[-1].read_text())
        if isinstance(payload, dict):
            payload["_cache_path"] = str(candidates[-1].relative_to(BASE_DIR))
            return payload
    except Exception:
        pass
    return {}


# ── inputs ────────────────────────────────────────────────────────────────
def load_inputs(ticker: str, *, no_cache: bool = False) -> dict:
    """Gather FMP + shared-cache inputs. Missing pieces stay None (degrade)."""
    from skills._shared import company_context
    import fmp_client

    profile = company_context.get_profile(ticker) or {}
    rf, rf_src = fmp_client.risk_free_rate()
    return {
        "ticker": ticker.upper(),
        "profile": profile,
        "income": fmp_client.income_annual(ticker, no_cache=no_cache) or [],
        "cashflow": fmp_client.cashflow_annual(ticker, no_cache=no_cache) or [],
        "balance": fmp_client.balance_annual(ticker, no_cache=no_cache) or [],
        "estimates": fmp_client.analyst_estimates(ticker, no_cache=no_cache) or [],
        "quote": fmp_client.quote(ticker, no_cache=no_cache) or {},
        "risk_free": rf,
        "risk_free_src": rf_src,
        "earnings_context": _latest_earnings_context(ticker),
    }


# ── assumptions ───────────────────────────────────────────────────────────
def _field(value, provenance):
    return {"value": value, "provenance": provenance}


def _hist_revenue_cagr(income: list) -> float | None:
    revs = [_num(y.get("revenue")) for y in income if _num(y.get("revenue"))]
    if len(revs) < 2 or revs[-1] <= 0 or revs[0] <= 0:
        return None
    years = len(revs) - 1
    return (revs[0] / revs[-1]) ** (1 / years) - 1  # newest-first


def _analyst_growth(income: list, estimates: list) -> list[float]:
    """Forward revenue growth rates from analyst estimates vs prior year.
    Returns [] when estimates unusable."""
    rev_now = _num(income[0].get("revenue")) if income else None
    if not rev_now:
        return []
    # estimates rows carry a fiscal 'date'; keep future ones, oldest first
    latest_fy = str(income[0].get("date", ""))[:4]
    fwd = sorted(
        [e for e in estimates
         if _num(e.get("revenueAvg")) and str(e.get("date", ""))[:4] > latest_fy],
        key=lambda e: str(e.get("date", "")),
    )
    growths, prev = [], rev_now
    for e in fwd[:2]:
        rev_e = _num(e.get("revenueAvg"))
        if not rev_e or prev <= 0:
            break
        growths.append(_clamp(rev_e / prev - 1, *G1_ANALYST_CLAMP))
        prev = rev_e
    return growths


def derive_base_assumptions(inputs: dict) -> dict:
    """Every field: {"value": float|None, "provenance": str}."""
    income, cashflow = inputs.get("income") or [], inputs.get("cashflow") or []
    a: dict = {}

    # revenue growth y1-2: analyst first, damped hist CAGR fallback
    analyst_g = _analyst_growth(income, inputs.get("estimates") or [])
    cagr = _hist_revenue_cagr(income)
    derived_g = _clamp(cagr * CAGR_DAMPING, *G1_DERIVED_CLAMP) if cagr is not None else None
    for i, key in enumerate(("revenue_growth_y1", "revenue_growth_y2")):
        if i < len(analyst_g):
            a[key] = _field(round(analyst_g[i], 4), "analyst")
        elif derived_g is not None:
            a[key] = _field(round(derived_g, 4), "derived")
        else:
            a[key] = _field(0.05, "default")

    a["terminal_growth"] = _field(TERMINAL_GROWTH_DEFAULT, "default")

    # margins / capex / D&A / NWC — 3y historical averages
    m = _avg_pct(income, "ebitda", "revenue")
    a["ebitda_margin"] = _field(round(m, 4), "derived") if m is not None else _field(0.20, "default")
    joined = _join_revenue(cashflow, income)  # cashflow rows lack revenue — join by fiscal year
    d = _avg_pct(joined, "depreciationAndAmortization", "revenue_joined")
    a["da_pct"] = _field(round(d, 4), "derived") if d is not None else _field(0.04, "default")
    c = _avg_pct(joined, "capitalExpenditure", "revenue_joined", absval=True)
    a["capex_pct"] = _field(round(c, 4), "derived") if c is not None else _field(0.05, "default")

    # NWC: avg ΔNWC / Δrevenue over 3y, clamp [0, 0.30]
    nwc = _nwc_pct(cashflow, income)
    a["nwc_pct"] = _field(round(nwc, 4), "derived") if nwc is not None else _field(0.05, "default")

    # tax: 3y effective
    t = _avg_pct(income, "incomeTaxExpense", "incomeBeforeTax")
    a["tax_rate"] = (_field(round(_clamp(t, *TAX_CLAMP), 4), "derived")
                     if t is not None else _field(0.21, "default"))

    # WACC building blocks
    beta = _num((inputs.get("profile") or {}).get("beta"))
    a["beta"] = _field(beta, "derived") if beta is not None else _field(1.0, "default")
    a["risk_free"] = _field(inputs.get("risk_free", 0.042),
                            "derived" if inputs.get("risk_free_src", "").startswith("fred") else "default")
    a["erp"] = _field(ERP_DEFAULT, "default")
    a["cost_of_debt"] = _field(round(a["risk_free"]["value"] + DEBT_SPREAD_DEFAULT, 4), "default")
    a["wacc"] = _field(None, "derived")  # computed by compute_wacc unless overridden
    through_cycle = _derive_through_cycle_assumptions(inputs, a)
    if through_cycle:
        a.update(through_cycle)
    else:
        a["projection_mode"] = _field("legacy_constant_ratio", "derived")
    return a


def _join_revenue(cashflow: list, income: list) -> list:
    """Attach income revenue to cashflow rows by fiscal date prefix."""
    rev_by_year = {str(y.get("date", ""))[:4]: _num(y.get("revenue")) for y in income}
    out = []
    for r in cashflow:
        row = dict(r)
        row["revenue_joined"] = rev_by_year.get(str(r.get("date", ""))[:4])
        out.append(row)
    return out


def _nwc_pct(cashflow: list, income: list) -> float | None:
    revs = [_num(y.get("revenue")) for y in income]
    ratios = []
    for i, r in enumerate((cashflow or [])[:3]):
        chg = _num(r.get("changeInWorkingCapital"))
        if chg is None or i + 1 >= len(revs):
            continue
        d_rev = (revs[i] or 0) - (revs[i + 1] or 0)
        if d_rev > 0:
            # FMP sign convention: negative changeInWorkingCapital = cash use (NWC grew)
            ratios.append(_clamp(-chg / d_rev, 0.0, 0.30))
    return sum(ratios) / len(ratios) if ratios else None


def _derive_through_cycle_assumptions(inputs: dict, base: dict) -> dict:
    """Build a normalized path when a confirmed structural shift is available.

    Quarterly revenue/operating income is preferred over provider EBITDA because
    the latter can be internally inconsistent around restatements.  Analyst
    revenue targets are bounded by a declining growth envelope; they inform the
    path but cannot create an unbounded terminal base.  Terminal capex equals
    normalized D&A plus growth reinvestment implied by sales-to-capital.
    """
    ctx = inputs.get("earnings_context") or {}
    shift = ctx.get("structural_shift") or {}
    confirmed = (shift.get("confirmed") is True or
                 str(shift.get("tier") or shift.get("status") or "").upper() == "CONFIRMED")
    quarterly = [r for r in (ctx.get("quarterly_pnl") or []) if isinstance(r, dict)]
    if not confirmed or not quarterly:
        return {}

    latest = quarterly[0]
    current_fy = str(latest.get("fiscalYear") or "")
    current_rows = [r for r in quarterly if str(r.get("fiscalYear") or "") == current_fy]
    actual_revenue = sum(_num(r.get("revenue")) or 0.0 for r in current_rows)
    next_revenue = _num(ctx.get("next_earnings_revenue_estimate"))
    estimate_rows = [r for r in (ctx.get("annual_estimates") or []) if isinstance(r, dict)]
    estimates_by_year = {
        str(r.get("date") or "")[:4]: _num(r.get("revenue_avg") or r.get("revenueAvg"))
        for r in estimate_rows
    }
    year1_revenue = None
    year1_source = None
    if len(current_rows) == 3 and actual_revenue > 0 and next_revenue and next_revenue > 0:
        year1_revenue = actual_revenue + next_revenue
        year1_source = "quarterly_actuals_plus_next_quarter_estimate"
    elif estimates_by_year.get(current_fy):
        year1_revenue = estimates_by_year[current_fy]
        year1_source = "annual_analyst_estimate"
    if not year1_revenue or year1_revenue <= 0:
        return {}

    notes: list[str] = []
    current_fy_revenue = year1_revenue
    revenue_path = []
    try:
        fy0 = int(current_fy)
    except ValueError:
        return {}
    prev = current_fy_revenue
    for index in range(PROJECTION_YEARS):
        forecast_year = fy0 + index + 1
        target = estimates_by_year.get(str(forecast_year))
        cap = THROUGH_CYCLE_GROWTH_CAPS[index]
        if target and target > 0:
            raw_growth = target / prev - 1
            bounded_growth = _clamp(raw_growth, THROUGH_CYCLE_GROWTH_FLOOR, cap)
            if abs(raw_growth - bounded_growth) > 1e-9:
                notes.append(
                    f"FY{forecast_year} analyst growth {raw_growth:.1%} capped to {bounded_growth:.1%}"
                )
        else:
            if revenue_path:
                prior_base = revenue_path[-2] if len(revenue_path) > 1 else current_fy_revenue
                prior_growth = revenue_path[-1] / prior_base - 1
            else:
                prior_growth = cap
            bounded_growth = _clamp(prior_growth, THROUGH_CYCLE_GROWTH_FLOOR, cap)
            notes.append(f"FY{forecast_year} revenue estimate missing; bounded fade used")
        prev = prev * (1 + bounded_growth)
        revenue_path.append(prev)

    # Start EBIT margin: current-FY actual operating profit plus one estimated
    # quarter at the latest observed margin.  Provider EBITDA is intentionally
    # ignored when it is below operating income.
    actual_operating = sum(_num(r.get("operatingIncome")) or 0.0 for r in current_rows)
    latest_rev = _num(latest.get("revenue"))
    latest_op = _num(latest.get("operatingIncome"))
    latest_margin = latest_op / latest_rev if latest_rev and latest_op is not None else None
    projected_operating = actual_operating
    if len(current_rows) == 3 and next_revenue and latest_margin is not None:
        projected_operating += next_revenue * _clamp(latest_margin, *EBIT_MARGIN_CLAMP)
    start_ebit_margin = projected_operating / year1_revenue if year1_revenue else None

    # Long-run EBIT/D&A margins use forward analyst operating structure, not
    # peak-quarter margins or a three-year trough average.
    forward = inputs.get("estimates") or []
    forward_ebit_margins = []
    forward_da_margins = []
    for row in forward:
        rev = _num(row.get("revenueAvg"))
        ebit = _num(row.get("ebitAvg"))
        ebitda = _num(row.get("ebitdaAvg"))
        if rev and rev > 0 and ebit is not None:
            forward_ebit_margins.append(ebit / rev)
        if rev and rev > 0 and ebit is not None and ebitda is not None and ebitda >= ebit:
            forward_da_margins.append((ebitda - ebit) / rev)
    terminal_ebit_margin = _median(forward_ebit_margins)
    terminal_da_pct = _median(forward_da_margins)
    if start_ebit_margin is None or terminal_ebit_margin is None or terminal_da_pct is None:
        return {}
    start_ebit_margin = _clamp(start_ebit_margin, *EBIT_MARGIN_CLAMP)
    terminal_ebit_margin = _clamp(terminal_ebit_margin, *EBIT_MARGIN_CLAMP)

    income = inputs.get("income") or []
    start_da_pct = _avg_pct(income, "depreciationAndAmortization", "revenue", n=1)
    if start_da_pct is None:
        start_da_pct = terminal_da_pct
    start_da_pct = _clamp(start_da_pct, *DA_PCT_CLAMP)
    terminal_da_pct = _clamp(terminal_da_pct, *DA_PCT_CLAMP)

    # TTM capex from quarterly rows.  abs() repairs provider sign drift; an
    # explicit quality note records any OCF/FCF reconciliation failure.
    qcf = [r for r in (ctx.get("cash_flow") or []) if isinstance(r, dict)][:4]
    ttm_capex = sum(abs(_num(r.get("capitalExpenditure")) or 0.0) for r in qcf)
    start_capex_pct = ttm_capex / year1_revenue if ttm_capex > 0 else base["capex_pct"]["value"]
    for row in qcf:
        ocf, capex, fcf = (_num(row.get("operatingCashFlow")),
                           _num(row.get("capitalExpenditure")), _num(row.get("freeCashFlow")))
        if None not in (ocf, capex, fcf):
            expected = ocf - abs(capex)
            if abs(expected - fcf) > max(abs(ocf) * 0.05, 1.0):
                notes.append("cashflow sign inconsistency: abs(capex) used, reported FCF ignored")
                break
    start_capex_pct = _clamp(start_capex_pct, *CAPEX_PCT_CLAMP)

    latest_income = income[0] if income else {}
    latest_balance = (inputs.get("balance") or [{}])[0]
    hist_revenue = _num(latest_income.get("revenue"))
    net_ppe = _num(latest_balance.get("propertyPlantEquipmentNet"))
    sales_to_capital = hist_revenue / net_ppe if hist_revenue and net_ppe else 1.0
    sales_to_capital = _clamp(sales_to_capital, *SALES_TO_CAPITAL_CLAMP)
    terminal_capex_pct = terminal_da_pct + base["terminal_growth"]["value"] / sales_to_capital
    terminal_capex_pct = _clamp(terminal_capex_pct, *CAPEX_PCT_CLAMP)

    latest_ebitda = _num(latest.get("ebitda"))
    if latest_ebitda is not None and latest_op is not None and latest_ebitda < latest_op:
        notes.append("quarterly EBITDA below operating income: EBITDA field ignored")

    cache_path = ctx.get("_cache_path") or "earnings_analyst_cache"
    return {
        "projection_mode": _field("structural_shift_through_cycle", "derived"),
        "projection_as_of": _field(ctx.get("as_of_date"), cache_path),
        "projection_base_revenue": _field(round(current_fy_revenue), year1_source),
        "revenue_path": _field([round(v) for v in revenue_path], year1_source),
        "ebit_margin_start": _field(round(start_ebit_margin, 4), "quarterly_rollforward"),
        "ebit_margin_terminal": _field(round(terminal_ebit_margin, 4), "analyst_normalized"),
        "da_pct_start": _field(round(start_da_pct, 4), "latest_fiscal_year"),
        "da_pct_terminal": _field(round(terminal_da_pct, 4), "analyst_normalized"),
        "capex_pct_start": _field(round(start_capex_pct, 4), "quarterly_ttm_abs_capex"),
        "capex_pct_terminal": _field(round(terminal_capex_pct, 4), "normalized_reinvestment"),
        "sales_to_capital": _field(round(sales_to_capital, 4), "latest_fiscal_year"),
        "projection_notes": _field(notes, "quality_gate"),
    }


def apply_overrides(assumptions: dict, overrides: dict) -> tuple[dict, list[str]]:
    """Merge user overrides; unknown keys are rejected loudly."""
    a = {k: dict(v) for k, v in assumptions.items()}
    errors = []
    for k, v in (overrides or {}).items():
        if k not in OVERRIDABLE:
            errors.append(f"unknown override key: {k} (allowed: {sorted(OVERRIDABLE)})")
            continue
        try:
            a[k] = _field(float(v), "override")
        except (TypeError, ValueError):
            errors.append(f"override {k} not numeric: {v!r}")
    return a, errors


# ── WACC ──────────────────────────────────────────────────────────────────
def compute_wacc(assumptions: dict, inputs: dict) -> dict:
    """CAPM cost of equity + after-tax cost of debt, market-value weights."""
    if assumptions["wacc"]["provenance"] == "override" and assumptions["wacc"]["value"]:
        w = _clamp(assumptions["wacc"]["value"], WACC_MIN, WACC_MAX)
        return {"wacc": round(w, 4), "provenance": "override", "components": {}}

    rf = assumptions["risk_free"]["value"]
    beta_raw = assumptions["beta"]["value"]
    projection_mode = (assumptions.get("projection_mode") or {}).get("value")
    beta_is_override = assumptions["beta"].get("provenance") == "override"
    if projection_mode == "structural_shift_through_cycle" and not beta_is_override:
        # A spot regression beta can be dominated by the same dislocation that
        # triggered the structural-shift model.  Mean-revert it for a matching
        # through-cycle cost of capital; explicit user beta remains untouched.
        beta = BETA_OBSERVED_WEIGHT * beta_raw + (1 - BETA_OBSERVED_WEIGHT) * 1.0
        beta_method = "blume_mean_reversion"
    else:
        beta = beta_raw
        beta_method = "observed_or_override"
    erp = assumptions["erp"]["value"]
    kd = assumptions["cost_of_debt"]["value"]
    tax = assumptions["tax_rate"]["value"]
    ke = rf + beta * erp

    mcap = _num((inputs.get("profile") or {}).get("marketCap")) or _num((inputs.get("quote") or {}).get("marketCap"))
    bal = (inputs.get("balance") or [{}])[0]
    debt = _num(bal.get("totalDebt")) or 0.0
    if mcap and mcap > 0:
        we = mcap / (mcap + debt)
    else:
        we = 1.0  # no market cap → all-equity fallback
    wacc = we * ke + (1 - we) * kd * (1 - tax)
    return {
        "wacc": round(_clamp(wacc, WACC_MIN, WACC_MAX), 4),
        "provenance": ("derived_mean_reverting_beta"
                       if beta_method == "blume_mean_reversion" else "derived"),
        "components": {
            "cost_of_equity": round(ke, 4), "cost_of_debt": round(kd, 4),
            "beta": round(beta, 4), "beta_observed": beta_raw,
            "beta_method": beta_method, "risk_free": rf, "erp": erp,
            "equity_weight": round(we, 4), "tax_rate": tax,
        },
    }


# ── DCF core ──────────────────────────────────────────────────────────────
def growth_path(assumptions: dict) -> list[float]:
    """y1, y2 explicit; y3-5 linear fade from y2 to terminal growth."""
    g1 = assumptions["revenue_growth_y1"]["value"]
    g2 = assumptions["revenue_growth_y2"]["value"]
    tg = assumptions["terminal_growth"]["value"]
    fade = [(g2 + (tg - g2) * i / 3) for i in (1, 2, 3)]
    return [g1, g2] + [round(g, 4) for g in fade]


def _fade_path(start: float, end: float, n: int = PROJECTION_YEARS) -> list[float]:
    if n <= 1:
        return [end]
    return [start + (end - start) * i / (n - 1) for i in range(n)]


def _fade_forward_path(start: float, end: float, n: int = PROJECTION_YEARS) -> list[float]:
    """Future periods only: current state is t0; final projected year reaches end."""
    return [start + (end - start) * (i + 1) / n for i in range(n)]


def run_dcf(assumptions: dict, inputs: dict, wacc_override: float | None = None) -> dict:
    """5y FCFF projection → Gordon terminal → EV → equity → per-share."""
    warnings: list[str] = []
    income = inputs.get("income") or []
    rev0 = _num(income[0].get("revenue")) if income else None
    if not rev0 or rev0 <= 0:
        return {"fair_value_per_share": None, "error": "no base revenue",
                "model_eligibility": {"eligible": False, "reason": "no_base_revenue"},
                "warnings": ["no base revenue"]}

    wacc_info = compute_wacc(assumptions, inputs)
    wacc = wacc_override if wacc_override is not None else wacc_info["wacc"]
    tg = assumptions["terminal_growth"]["value"]
    if wacc - tg < MIN_WACC_G_SPREAD:
        tg = wacc - MIN_WACC_G_SPREAD
        warnings.append(f"terminal_growth lowered to {tg:.4f} to keep wacc−g ≥ {MIN_WACC_G_SPREAD}")

    nwc_pct = assumptions["nwc_pct"]["value"]
    tax = assumptions["tax_rate"]["value"]
    projection_mode = (assumptions.get("projection_mode") or {}).get("value")

    if projection_mode == "structural_shift_through_cycle":
        revenue_path = list((assumptions.get("revenue_path") or {}).get("value") or [])
        if len(revenue_path) != PROJECTION_YEARS or any(_num(v) is None or v <= 0 for v in revenue_path):
            return {"fair_value_per_share": None, "error": "invalid through-cycle revenue path",
                    "model_eligibility": {"eligible": False, "reason": "invalid_revenue_path"},
                    "warnings": ["invalid through-cycle revenue path"]}
        ebit_margin_path = _fade_forward_path(
            assumptions["ebit_margin_start"]["value"],
            assumptions["ebit_margin_terminal"]["value"],
        )
        da_path = _fade_forward_path(
            assumptions["da_pct_start"]["value"], assumptions["da_pct_terminal"]["value"],
        )
        capex_path = _fade_forward_path(
            assumptions["capex_pct_start"]["value"], assumptions["capex_pct_terminal"]["value"],
        )
        warnings.extend((assumptions.get("projection_notes") or {}).get("value") or [])
    else:
        growths = growth_path(assumptions)
        revenue_path = []
        rev_build = rev0
        for growth in growths:
            rev_build *= 1 + growth
            revenue_path.append(rev_build)
        da_const = assumptions["da_pct"]["value"]
        ebit_margin_const = assumptions["ebitda_margin"]["value"] - da_const
        ebit_margin_path = [ebit_margin_const] * PROJECTION_YEARS
        da_path = [da_const] * PROJECTION_YEARS
        capex_path = [assumptions["capex_pct"]["value"]] * PROJECTION_YEARS

    rev_prev = ((assumptions.get("projection_base_revenue") or {}).get("value")
                if projection_mode == "structural_shift_through_cycle" else rev0)
    rows, pv_sum = [], 0.0
    for t, (rev, ebit_margin, da_pct, capex_pct) in enumerate(
            zip(revenue_path, ebit_margin_path, da_path, capex_path), start=1):
        g = rev / rev_prev - 1
        ebit = rev * ebit_margin
        da = rev * da_pct
        ebitda = ebit + da
        nopat = ebit * (1 - tax)
        capex = rev * capex_pct
        d_nwc = (rev - rev_prev) * nwc_pct
        fcff = nopat + da - capex - d_nwc
        pv = fcff / (1 + wacc) ** t
        pv_sum += pv
        rows.append({"year": t, "growth": round(g, 4), "revenue": round(rev),
                     "ebit_margin": round(ebit_margin, 4),
                     "da_pct": round(da_pct, 4), "capex_pct": round(capex_pct, 4),
                     "ebitda": round(ebitda), "ebit": round(ebit), "nopat": round(nopat),
                     "capex": round(capex), "d_nwc": round(d_nwc),
                     "fcff": round(fcff), "pv_fcff": round(pv)})
        rev_prev = rev

    fcff_5 = rows[-1]["fcff"]
    tv = fcff_5 * (1 + tg) / (wacc - tg)
    pv_tv = tv / (1 + wacc) ** PROJECTION_YEARS
    ev = pv_sum + pv_tv

    # A Gordon terminal value with non-positive terminal FCFF is not a low
    # valuation; it means this steady-state model is ineligible.  Preserve the
    # projection for audit/shadow use, but never emit a live fair-value anchor.
    terminal_eligible = fcff_5 > 0 and tv > 0
    eligibility_reason = None if terminal_eligible else "negative_terminal_fcff"

    bal = (inputs.get("balance") or [{}])[0]
    debt = _num(bal.get("totalDebt")) or 0.0
    cash = _num(bal.get("cashAndShortTermInvestments")) or _num(bal.get("cashAndCashEquivalents")) or 0.0
    net_debt = debt - cash
    earnings_context = inputs.get("earnings_context") or {}
    if projection_mode == "structural_shift_through_cycle":
        latest_net_cash = _num(
            ((earnings_context.get("derived") or {}).get("balance_health") or {}).get("net_cash")
        )
        if latest_net_cash is not None:
            net_debt = -latest_net_cash
            warnings.append("net debt sourced from latest quarterly earnings context")
    equity = ev - net_debt

    latest_ev = earnings_context.get("enterprise_value") or {}
    shares = (_num(latest_ev.get("numberOfShares"))
              if projection_mode == "structural_shift_through_cycle" else None)
    shares = shares or _num(income[0].get("weightedAverageShsOutDil")) or _num(income[0].get("weightedAverageShsOut"))
    if not shares or shares <= 0:
        mcap = _num((inputs.get("profile") or {}).get("marketCap"))
        price = _num((inputs.get("quote") or {}).get("price")) or _num((inputs.get("profile") or {}).get("price"))
        shares = mcap / price if mcap and price else None
        if shares:
            warnings.append("diluted shares unavailable — derived from marketCap/price")
    if not shares:
        return {"fair_value_per_share": None, "error": "no share count",
                "model_eligibility": {"eligible": False, "reason": "no_share_count"},
                "warnings": warnings}

    fv = equity / shares if terminal_eligible and equity > 0 else None
    if fv is None:
        warnings.append(
            "negative terminal FCFF — model ineligible" if not terminal_eligible
            else "negative implied equity value — fair value null"
        )
        if eligibility_reason is None:
            eligibility_reason = "negative_implied_equity"
    if ev > 0 and pv_tv > 0 and pv_tv / ev > 0.85:
        warnings.append(f"terminal value is {pv_tv / ev:.0%} of EV — projection carries little weight")

    return {
        "fair_value_per_share": round(fv, 2) if fv else None,
        "wacc_used": round(wacc, 4), "terminal_growth_used": round(tg, 4),
        "wacc_detail": wacc_info,
        "enterprise_value": round(ev), "pv_explicit": round(pv_sum),
        "pv_terminal": round(pv_tv), "terminal_value": round(tv),
        "net_debt": round(net_debt), "equity_value": round(equity),
        "shares": round(shares), "fcff_table": rows, "warnings": warnings,
        "projection_mode": projection_mode,
        "model_eligibility": {"eligible": fv is not None, "reason": eligibility_reason},
    }


def sensitivity_grid(assumptions: dict, inputs: dict, base: dict) -> dict:
    """5×5: WACC ±1.0% (0.5% steps) × terminal growth ±0.5% (0.25% steps)."""
    w0, tg0 = base["wacc_used"], base["terminal_growth_used"]
    wacc_vals = [round(w0 + d, 4) for d in (-0.01, -0.005, 0, 0.005, 0.01)]
    tg_vals = [round(tg0 + d, 4) for d in (-0.005, -0.0025, 0, 0.0025, 0.005)]
    grid = []
    for w in wacc_vals:
        row = []
        for tg in tg_vals:
            a = {k: dict(v) for k, v in assumptions.items()}
            a["terminal_growth"] = _field(tg, "sensitivity")
            if (a.get("projection_mode") or {}).get("value") == "structural_shift_through_cycle":
                # Terminal reinvestment must move with terminal growth.  Holding
                # capex fixed here would make the sensitivity grid internally
                # inconsistent and overstate the benefit of a higher g.
                sales_to_capital = (a.get("sales_to_capital") or {}).get("value")
                terminal_da = (a.get("da_pct_terminal") or {}).get("value")
                if sales_to_capital and terminal_da is not None:
                    a["capex_pct_terminal"] = _field(
                        round(_clamp(terminal_da + tg / sales_to_capital,
                                     *CAPEX_PCT_CLAMP), 4),
                        "sensitivity_reinvestment",
                    )
            r = run_dcf(a, inputs, wacc_override=max(w, tg + MIN_WACC_G_SPREAD))
            row.append(r.get("fair_value_per_share"))
        grid.append(row)
    return {"wacc_values": wacc_vals, "terminal_growth_values": tg_vals, "grid": grid}


# ── report ────────────────────────────────────────────────────────────────
def render_md(payload: dict) -> str:
    a, r = payload["assumptions"], payload["dcf"]
    s = payload["sensitivity"]
    t = payload["ticker"]
    lines = [
        f"# {t} · Driver-based DCF Model — {payload['asof']}",
        "",
        f"> fair value **${r.get('fair_value_per_share')}** vs current "
        f"${payload.get('current_price')} → **{payload.get('upside_pct')}%**"
        f" · WACC {r.get('wacc_used'):.2%} · terminal g {r.get('terminal_growth_used'):.2%}",
        f"> projection mode `{r.get('projection_mode')}`",
        "",
        "## Assumptions（value / provenance）",
        "",
        "| 假設 | 值 | 來源 |",
        "|---|---|---|",
    ]
    for k, f in a.items():
        v = f.get("value")
        vv = f"{v:.4f}" if isinstance(v, float) else str(v)
        lines.append(f"| {k} | {vv} | {f.get('provenance')} |")
    lines += ["", "## FCFF Projection", "",
              "| Yr | g | Revenue | EBIT % | EBITDA | NOPAT | Capex % | Capex | ΔNWC | FCFF | PV |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in r.get("fcff_table", []):
        lines.append("| {year} | {growth:.1%} | {revenue:,} | {ebit_margin:.1%} | {ebitda:,} "
                     "| {nopat:,} | {capex_pct:.1%} | {capex:,} | {d_nwc:,} "
                     "| {fcff:,} | {pv_fcff:,} |".format(**row))
    lines += ["",
              f"- PV explicit ${r.get('pv_explicit'):,} + PV terminal ${r.get('pv_terminal'):,} "
              f"= EV ${r.get('enterprise_value'):,}",
              f"- − net debt ${r.get('net_debt'):,} = equity ${r.get('equity_value'):,} "
              f"÷ {r.get('shares'):,} shares",
              "", "## Sensitivity（WACC × terminal growth，fair value $）", "",
              "| WACC \\ g | " + " | ".join(f"{g:.2%}" for g in s["terminal_growth_values"]) + " |",
              "|---|" + "---|" * len(s["terminal_growth_values"])]
    for w, row in zip(s["wacc_values"], s["grid"]):
        lines.append(f"| {w:.2%} | " + " | ".join(str(v) if v else "—" for v in row) + " |")
    if r.get("warnings"):
        lines += ["", "## Warnings", ""] + [f"- {w}" for w in r["warnings"]]
    lines += ["", "---", "*valuation-modeler · deterministic engine · 數字全由 script 計算*", ""]
    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────
def build_payload(ticker: str, overrides: dict, *, no_cache: bool = False) -> dict:
    inputs = load_inputs(ticker, no_cache=no_cache)
    assumptions = derive_base_assumptions(inputs)
    assumptions, errs = apply_overrides(assumptions, overrides)
    dcf = run_dcf(assumptions, inputs)
    sens = (sensitivity_grid(assumptions, inputs, dcf)
            if dcf.get("fair_value_per_share") else {"wacc_values": [], "terminal_growth_values": [], "grid": []})
    price = _num((inputs.get("quote") or {}).get("price")) or _num((inputs.get("profile") or {}).get("price"))
    fv = dcf.get("fair_value_per_share")
    upside = round((fv / price - 1) * 100, 1) if fv and price else None
    return {
        "ticker": ticker.upper(),
        "asof": dt.date.today().isoformat(),
        "fair_value_per_share": fv,          # ← dcf_self_built anchor
        "current_price": price,
        "upside_pct": upside,
        "assumptions": assumptions,
        "dcf": dcf,
        "sensitivity": sens,
        "model_eligibility": dcf.get("model_eligibility") or {
            "eligible": fv is not None,
            "reason": None if fv is not None else "unknown_model_failure",
        },
        "override_errors": errs,
        "degraded": fv is None,
    }


def main():
    ap = argparse.ArgumentParser(description="Driver-based DCF (valuation-modeler)")
    ap.add_argument("ticker")
    ap.add_argument("--json-only", action="store_true")
    ap.add_argument("--overrides", help="JSON file of assumption overrides")
    ap.add_argument("--set", action="append", default=[], metavar="K=V",
                    help="single override, repeatable (e.g. --set wacc=0.09)")
    ap.add_argument("--xlsx", action="store_true", help="also export Excel workbook")
    ap.add_argument("--output-dir", default=str(BASE_DIR / "reports"))
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    overrides = {}
    if args.overrides:
        overrides.update(json.loads(Path(args.overrides).read_text()))
    for kv in args.set:
        if "=" not in kv:
            sys.exit(f"--set expects K=V, got {kv!r}")
        k, v = kv.split("=", 1)
        overrides[k.strip()] = v.strip()

    payload = build_payload(args.ticker, overrides, no_cache=args.no_cache)
    if payload["override_errors"]:
        for e in payload["override_errors"]:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Persist payload for downstream consumers (ic-memo-writer --initiation fact pack)
    payload_cache = SCRIPT_DIR.parent / "cache" / f"{payload['ticker']}_dcf_payload.json"
    payload_cache.parent.mkdir(exist_ok=True)
    payload_cache.write_text(json.dumps(payload, ensure_ascii=False, indent=1))

    if args.xlsx:
        import export_xlsx
        out = Path(args.output_dir) / f"{dt.date.today():%Y%m%d}_{payload['ticker']}_valuation_model.xlsx"
        xp = export_xlsx.build_workbook(dcf_json=payload, comps_json=None, out_path=str(out))
        payload["xlsx_path"] = xp

    if args.json_only:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        out_md = Path(args.output_dir) / f"{dt.date.today():%Y%m%d}_{payload['ticker']}_dcf_model.md"
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(render_md(payload))
        print(f"report → {out_md}")
        print(json.dumps({k: payload[k] for k in
                          ("ticker", "fair_value_per_share", "current_price", "upside_pct", "degraded")},
                         ensure_ascii=False))
    sys.exit(0 if not payload["degraded"] else 1)


if __name__ == "__main__":
    main()
