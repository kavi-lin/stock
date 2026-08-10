#!/usr/bin/env python3
"""
valuation-modeler · multi-metric comparable company analysis.

Peer universe from skills/_shared/company_context (FMP stock-peers, 24h cache);
per-peer TTM multiples from company_context.get_ratios_ttm. Four metrics:
P/E, EV/EBITDA, EV/Sales, PEG — each with peer Q1/median/Q3 and an implied
per-share value for the subject (EV math identical to
investment/scripts/compute_price_framework.py compute_new_anchors).

The anchor value `comps_implied_value` is the MEDIAN of the ev_ebitda /
ev_sales / peg implied values — P/E is deliberately EXCLUDED because the
protocol's existing `peer_pe_implied` anchor already covers it (anti
double-count). Each metric needs ≥3 peers; the anchor needs ≥2 metrics,
else null (protocol weight redistribution handles it).

Usage:
    export FMP_API_KEY=...
    python3 comps.py NVDA --json-only
    python3 comps.py MSFT --xlsx
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics as stats
import sys
from pathlib import Path

import peer_cohorts

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

MIN_PEERS_PER_METRIC = 3
MIN_METRICS_FOR_ANCHOR = 2
MCAP_FLOOR_DIVISOR = 20          # drop peers with mcap < self/20
PEG_GROWTH_CLAMP = (0.02, 0.60)  # growth below 2% makes PEG explode — exclude
METRICS = ("pe", "ev_ebitda", "ev_sales", "peg")
ANCHOR_METRICS = ("ev_ebitda", "ev_sales", "peg")  # pe excluded (see docstring)


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _pos(v):
    v = _num(v)
    return v if v is not None and v > 0 else None


def _iqr_winsorize(vals: list[float]) -> list[float]:
    """Clamp outliers to [Q1 − 1.5·IQR, Q3 + 1.5·IQR]. Needs ≥4 points to act."""
    if len(vals) < 4:
        return vals
    q = stats.quantiles(vals, n=4)
    lo, hi = q[0] - 1.5 * (q[2] - q[0]), q[2] + 1.5 * (q[2] - q[0])
    return [min(max(v, lo), hi) for v in vals]


def _quartiles(vals: list[float]) -> dict:
    if len(vals) >= 4:
        q = stats.quantiles(vals, n=4)
        return {"q1": round(q[0], 2), "median": round(q[1], 2), "q3": round(q[2], 2)}
    return {"q1": None, "median": round(stats.median(vals), 2), "q3": None}


# ── data gathering ────────────────────────────────────────────────────────
def _eps_growth(ticker: str, *, no_cache: bool = False, as_of: str | None = None) -> float | None:
    """Forward EPS growth from the two nearest future fiscal years.

    Past fiscal years are dropped so a historical growth rate can never stand in
    for a forward one, and a next-FY growth outside the PEG clamp returns None
    rather than silently substituting a later, faster-growing year pair.
    """
    import fmp_client
    ref = as_of or dt.date.today().isoformat()
    est = fmp_client.analyst_estimates(ticker, no_cache=no_cache) or []
    rows = sorted([e for e in est
                   if _num(e.get("epsAvg")) and str(e.get("date", ""))[:10] >= ref],
                  key=lambda e: str(e.get("date", "")))
    if len(rows) < 2:
        return None
    ea, eb = _num(rows[0].get("epsAvg")), _num(rows[1].get("epsAvg"))
    if not (ea and eb and ea > 0):
        return None
    g = eb / ea - 1
    return round(g, 4) if PEG_GROWTH_CLAMP[0] <= g <= PEG_GROWTH_CLAMP[1] else None


def fetch_peer_metrics(ticker: str, *, no_cache: bool = False) -> dict:
    """Subject + peer multiples. Structure:
    {self: {...}, peers: {sym: {...}}, dropped: [...], peer_source}"""
    from skills._shared import company_context
    import fmp_client

    t = ticker.upper()
    self_profile = company_context.get_profile(t) or {}
    self_ratios = company_context.get_ratios_ttm(t) or {}
    self_mcap = _pos(self_profile.get("marketCap"))
    quote = fmp_client.quote(t, no_cache=no_cache) or {}
    price = _pos(quote.get("price")) or _pos(self_profile.get("price"))

    selection = company_context.select_valuation_peers(t)
    peers = selection["peers"]
    dropped = list(selection["dropped"])
    peer_rows: dict[str, dict] = {}
    if peers:
        profiles = selection["profiles"]
        for sym in peers:
            prof = profiles.get(sym) or {}
            mcap = _pos(prof.get("marketCap"))
            if self_mcap and (not mcap or mcap < self_mcap / MCAP_FLOOR_DIVISOR):
                dropped.append({"symbol": sym, "reason": "mcap floor"})
                continue
            ratios = company_context.get_ratios_ttm(sym) or {}
            growth = _eps_growth(sym, no_cache=no_cache)
            pe = _pos(ratios.get("pe_ttm"))
            peer_rows[sym] = {
                "name": prof.get("companyName") or sym,
                "market_cap": mcap,
                "pe": pe,
                "ev_ebitda": _pos(ratios.get("ev_to_ebitda_ttm")),
                "ev_sales": _pos(ratios.get("ev_to_sales_ttm")),
                "eps_growth_fwd": growth,
                "peg": round(pe / (growth * 100), 3) if pe and growth else None,
            }

    self_growth = _eps_growth(t, no_cache=no_cache)
    self_pe = _pos(self_ratios.get("pe_ttm"))
    bal = (fmp_client.balance_annual(t, no_cache=no_cache) or [{}])[0]
    debt = _num(bal.get("totalDebt")) or 0.0
    cash = _num(bal.get("cashAndShortTermInvestments")) or _num(bal.get("cashAndCashEquivalents")) or 0.0
    net_debt = debt - cash
    ev = (self_mcap + net_debt) if self_mcap else None
    shares = self_mcap / price if self_mcap and price else None

    range_peer_cohort = peer_cohorts.build_pe_cohort(t)

    return {
        "self": {
            "symbol": t, "name": self_profile.get("companyName") or t,
            "market_cap": self_mcap, "price": price,
            "pe": self_pe,
            "ev_ebitda": _pos(self_ratios.get("ev_to_ebitda_ttm")),
            "ev_sales": _pos(self_ratios.get("ev_to_sales_ttm")),
            "eps_growth_fwd": self_growth,
            "peg": round(self_pe / (self_growth * 100), 3) if self_pe and self_growth else None,
            "enterprise_value": ev, "net_debt": net_debt, "shares": shares,
        },
        "peers": peer_rows,
        "dropped": dropped,
        "peer_source": selection["selector"],
        "subject_industry": selection["subject_industry"],
        "peer_selection_eligible": selection["eligible"],
        "peer_selection_reason": selection["reason"],
        "range_peer_cohort": range_peer_cohort,
    }


# ── table & anchor ────────────────────────────────────────────────────────
def _implied_per_share(metric: str, peer_median: float, s: dict) -> float | None:
    """Subject per-share value implied by peer median multiple."""
    ev, nd, sh, price = s.get("enterprise_value"), s.get("net_debt") or 0.0, s.get("shares"), s.get("price")
    if metric == "pe":
        eps = price / s["pe"] if price and _pos(s.get("pe")) else None
        return round(peer_median * eps, 2) if eps else None
    if metric == "peg":
        g = s.get("eps_growth_fwd")
        eps = price / s["pe"] if price and _pos(s.get("pe")) else None
        if not (g and eps):
            return None
        implied_pe = peer_median * g * 100
        return round(implied_pe * eps, 2)
    # EV metrics — same math as compute_price_framework._ev_implied
    self_mult = _pos(s.get(metric))
    if not (peer_median and self_mult and ev and sh):
        return None
    metric_abs = ev / self_mult                     # EBITDA or Sales (absolute)
    equity = peer_median * metric_abs - nd
    return round(equity / sh, 2) if equity > 0 else None


def build_comps_table(data: dict) -> dict:
    s, peers = data["self"], data["peers"]
    table: dict = {"metrics": {}, "peer_count_total": len(peers)}
    for metric in METRICS:
        vals = [(sym, p[metric]) for sym, p in peers.items() if _pos(p.get(metric))]
        if len(vals) < MIN_PEERS_PER_METRIC:
            table["metrics"][metric] = {"peer_values": dict(vals), "n": len(vals),
                                        "quartiles": None, "implied_value": None,
                                        "excluded_reason": f"<{MIN_PEERS_PER_METRIC} peers"}
            continue
        wins = _iqr_winsorize([v for _, v in vals])
        q = _quartiles(wins)
        implied = _implied_per_share(metric, q["median"], s)
        table["metrics"][metric] = {
            "peer_values": dict(vals), "n": len(vals),
            "quartiles": q, "self_value": s.get(metric),
            "implied_value": implied,
        }
    return table


def comps_implied_anchor(table: dict) -> tuple[float | None, dict]:
    """Median of ANCHOR_METRICS implied values (P/E excluded). ≥2 metrics required."""
    used = {m: table["metrics"][m]["implied_value"]
            for m in ANCHOR_METRICS
            if table["metrics"].get(m, {}).get("implied_value")}
    if len(used) < MIN_METRICS_FOR_ANCHOR:
        return None, {"used_metrics": used, "reason": f"<{MIN_METRICS_FOR_ANCHOR} usable metrics"}
    return round(stats.median(used.values()), 2), {"used_metrics": used}


def peer_pe_range_scenario(data: dict) -> dict:
    """Range-only relative valuation when exact-industry peers are sparse."""
    cohort = data.get("range_peer_cohort") or {}
    subject = data.get("self") or {}
    value = peer_cohorts.implied_pe_value(subject, cohort)
    value_low, value_high = peer_cohorts.implied_pe_range(subject, cohort)
    eligible = bool(cohort.get("eligible") and value is not None)
    return {
        "value": value,
        "value_low": value_low,
        "value_high": value_high,
        "eligible": eligible,
        "reason": None if eligible else cohort.get("reason") or "subject_eps_unavailable",
        "scope": "range_only",
        "peer_count": cohort.get("peer_count", 0),
        "median_pe": cohort.get("median_pe"),
        "pe_min": cohort.get("pe_min"),
        "pe_max": cohort.get("pe_max"),
        "peers": cohort.get("peers") or {},
        "as_of": cohort.get("as_of"),
        "provenance": cohort.get("candidate_provenance") or {},
        "rationale": cohort.get("rationale"),
        "limitations": cohort.get("limitations") or [],
    }


# ── report ────────────────────────────────────────────────────────────────
_METRIC_LABEL = {"pe": "P/E (TTM)", "ev_ebitda": "EV/EBITDA (TTM)",
                 "ev_sales": "EV/Sales (TTM)", "peg": "PEG (fwd)"}


def render_md(payload: dict) -> str:
    s = payload["universe"]["self"]
    t = payload["ticker"]
    lines = [
        f"# {t} · Comparable Company Analysis — {payload['asof']}",
        "",
        f"> comps implied value **${payload.get('comps_implied_value')}** "
        f"vs current ${s.get('price')} · peers used {payload['universe']['peer_count_used']}"
        f"/{len(payload['universe']['peers'])} (mcap floor drop {len(payload['universe']['dropped'])})",
        "",
        "## Peer multiples",
        "",
        "| Ticker | Mkt Cap ($B) | P/E | EV/EBITDA | EV/Sales | EPS g fwd | PEG |",
        "|---|---|---|---|---|---|---|",
    ]

    def _row(sym, p, bold=False):
        b = "**" if bold else ""
        mc = f"{p['market_cap'] / 1e9:,.0f}" if p.get("market_cap") else "—"
        cells = [f"{p.get(k):.2f}" if _num(p.get(k)) else "—"
                 for k in ("pe", "ev_ebitda", "ev_sales")]
        g = f"{p['eps_growth_fwd']:.1%}" if _num(p.get("eps_growth_fwd")) else "—"
        peg = f"{p['peg']:.2f}" if _num(p.get("peg")) else "—"
        return f"| {b}{sym}{b} | {mc} | {cells[0]} | {cells[1]} | {cells[2]} | {g} | {peg} |"

    lines.append(_row(s["symbol"], s, bold=True))
    for sym, p in payload["universe"]["peers"].items():
        lines.append(_row(sym, p))

    lines += ["", "## Implied values（peer median × subject metric）", "",
              "| Metric | n | Q1 | Median | Q3 | Self | Implied $ |",
              "|---|---|---|---|---|---|---|"]
    for m in METRICS:
        row = payload["table"]["metrics"].get(m, {})
        q = row.get("quartiles") or {}
        note = " *(anchor 排除)*" if m == "pe" else ""
        lines.append(
            f"| {_METRIC_LABEL[m]}{note} | {row.get('n', 0)} | {q.get('q1') or '—'} "
            f"| {q.get('median') or '—'} | {q.get('q3') or '—'} "
            f"| {row.get('self_value') or '—'} | {row.get('implied_value') or '—'} |")
    lines += ["",
              f"**comps_implied anchor = ${payload.get('comps_implied_value')}**"
              f"（{', '.join(payload['anchor_detail'].get('used_metrics', {}))} 中位數；P/E 排除防與"
              " peer_pe_implied 重複計權）",
              ""]
    scenario = payload.get("peer_pe_range_scenario") or {}
    canonical_ok = bool((payload.get("model_eligibility") or {}).get("eligible"))
    if scenario.get("eligible") and not canonical_ok:
        lines += [
            "", "## Range-only peer P/E scenario", "",
            f"> **${scenario.get('value')}** from {scenario.get('peer_count')} adjacent peers "
            f"at median P/E {scenario.get('median_pe')}× "
            f"(spread {scenario.get('pe_min')}×–{scenario.get('pe_max')}× → "
            f"${scenario.get('value_low')}–${scenario.get('value_high')}). "
            "This is not the primary FV and does not enter the canonical comps anchor.",
            "", "| Ticker | Role | P/E TTM | Source |", "|---|---|---:|---|",
        ]
        for symbol, peer in (scenario.get("peers") or {}).items():
            lines.append(
                f"| {symbol} | {peer.get('role')} | {peer.get('pe_ttm')} | "
                f"{peer.get('metric_source')} |"
            )
        lines += ["", "Limitations:"] + [f"- {item}" for item in scenario.get("limitations") or []]
    elif scenario.get("eligible"):
        # Canonical peers are healthy — showing a second peer table here would
        # invite readers to blend two universes. Payload keeps it for audit.
        lines += ["", "## Range-only peer P/E scenario", "",
                  f"> 略過渲染：canonical exact-industry peer set 本次 eligible，"
                  f"curated cohort（{scenario.get('peer_count')} 檔）僅留於 JSON payload 供審計。"]
    lines += ["", "---", "*valuation-modeler · deterministic engine · 數字全由 script 計算*", ""]
    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────
def build_payload(ticker: str, *, no_cache: bool = False) -> dict:
    universe = fetch_peer_metrics(ticker, no_cache=no_cache)
    table = build_comps_table(universe)
    anchor, detail = comps_implied_anchor(table)
    range_scenario = peer_pe_range_scenario(universe)
    used = len({sym for m in table["metrics"].values() for sym in (m.get("peer_values") or {})})
    universe["peer_count_used"] = used
    eligible = bool(anchor is not None and universe.get("peer_selection_eligible"))
    reason = None
    if not universe.get("peer_selection_eligible"):
        reason = universe.get("peer_selection_reason") or "insufficient_exact_industry_peers"
    elif anchor is None:
        reason = detail.get("reason") or "insufficient_usable_metrics"
    return {
        "ticker": ticker.upper(),
        "asof": dt.date.today().isoformat(),
        "comps_implied_value": anchor,       # ← comps_implied anchor
        "anchor_detail": detail,
        "universe": universe,
        "table": table,
        "peer_pe_range_scenario": range_scenario,
        "model_eligibility": {"eligible": eligible, "reason": reason},
        "degraded": not eligible,
    }


def main():
    ap = argparse.ArgumentParser(description="Multi-metric comps (valuation-modeler)")
    ap.add_argument("ticker")
    ap.add_argument("--json-only", action="store_true")
    ap.add_argument("--xlsx", action="store_true")
    ap.add_argument("--output-dir", default=str(BASE_DIR / "reports"))
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    payload = build_payload(args.ticker, no_cache=args.no_cache)

    # Persist payload for downstream consumers (ic-memo-writer --initiation fact pack)
    payload_cache = SCRIPT_DIR.parent / "cache" / f"{payload['ticker']}_comps_payload.json"
    payload_cache.parent.mkdir(exist_ok=True)
    payload_cache.write_text(json.dumps(payload, ensure_ascii=False, indent=1))

    if args.xlsx:
        try:
            import export_xlsx
        except ImportError as e:  # export_xlsx.py absent from this checkout
            print(f"WARN: xlsx export unavailable ({e}) — skipped", file=sys.stderr)
            payload["xlsx_skipped"] = True
        else:
            out = Path(args.output_dir) / f"{dt.date.today():%Y%m%d}_{payload['ticker']}_valuation_model.xlsx"
            xp = export_xlsx.build_workbook(dcf_json=None, comps_json=payload, out_path=str(out))
            payload["xlsx_path"] = xp

    if args.json_only:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        out_md = Path(args.output_dir) / f"{dt.date.today():%Y%m%d}_{payload['ticker']}_comps.md"
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(render_md(payload))
        print(f"report → {out_md}")
        print(json.dumps({k: payload[k] for k in ("ticker", "comps_implied_value", "degraded")},
                         ensure_ascii=False))
    # V4.125.0 — exit 0 whenever a payload was produced, degraded or not.
    #
    # `degraded` means "no usable comps anchor" (e.g. <3 business-similar peers). That
    # is a COMPLETE AND CORRECT ANSWER, not an execution failure: the run fetched, the
    # cohort was screened, and the verdict is `comps_implied_value: null` with a reason
    # in `model_eligibility.reason`. Mapping it to rc=1 collided with V4.116.1's gate
    # discipline ("mandatory script rc≠0 → halt and report"), which is written for
    # tools that FAILED. The PM was left to decide on the spot whether a null anchor
    # was a halt or a degrade, and it decided differently run to run: on 2026-08-10
    # alone, NVDA 08:36 halted / NVDA 08:43 continued / META 09:03 halted / META 09:14
    # continued — same ticker, same day, same data gap, opposite treatment.
    #
    # Fixing the signal rather than the halt rule keeps V4.116.1 absolute: rc≠0 still
    # means "the tool failed, stop". Genuine failures (fetch error, bad ticker, crash)
    # still surface as a non-zero exit via the raised exception. A null anchor now flows
    # into the machinery already built for it — eligibility-before-aggregation (V4.75.0)
    # and the `no_peer_cohort` trigger in valuation_reviewer_gate.py — instead of
    # aborting the analysis. This is the same "no data ≠ bad value ≠ didn't run"
    # distinction already made by PE_ABSENT (V4.86.2) and script_not_run (V4.116.0).
    #
    # Consumers read `.comps_implied_value` / `.degraded` from the JSON, never the exit
    # code (verified 2026-08-10: no script branches on it), so nothing silently starts
    # accepting a degraded anchor as a good one.
    sys.exit(0)


if __name__ == "__main__":
    main()
