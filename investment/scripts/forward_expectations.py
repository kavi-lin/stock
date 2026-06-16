#!/usr/bin/env python3
"""forward_expectations.py — V1.1 deterministic forward-expectations engine (shadow).

Phase 1 of the Forward Expectations Layer. Answers "公司未來會賺多少？現價要求的未來
是否合理？" WITHOUT inventing a forward fair-value price. It produces three GROUNDED
forward views and the gap between them — never a single forward fair value (that needs
a driver tree, deferred to Phase 2).

Three lanes (all data-derived, 0 LLM arithmetic):
  1. consensus   — FMP analyst annual_estimates → estimate-window revenue/EPS CAGR +
                   low/high spread + analyst count + rating-revision direction.
                   Uses the ESTIMATE WINDOW (nearest→furthest estimate year), NOT a
                   trailing base — depressed-earnings growth names (ARM eps_ttm 0.75)
                   would otherwise show absurd from-base CAGR.
  2. market_implied — reverse DCF implied 5Y FCF CAGR (reuses compute_price_framework).
  3. base_rate   — peer historical revenue-CAGR distribution (anti-fantasy ceiling) +
                   self trailing revenue YoY.

Output: an expectations matrix. Numeric gaps and verdicts are emitted only when both
values use the same metric. Cross-metric observations remain descriptive.
SHADOW ONLY — does not touch the live fair_value blend or any decision logic.

A point-in-time snapshot is written to investment/invest_logs/forward_expectations/.
No forecast-vs-actual calibration engine (deferred until valuation approach stabilizes).

Usage:
  python3 investment/scripts/forward_expectations.py --ticker ARM --self-assemble
  python3 investment/scripts/forward_expectations.py --ticker ARM --self-assemble --no-fetch
  cat inputs.json | python3 investment/scripts/forward_expectations.py
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import glob as _glob
import json
import math
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "investment", "scripts"))

ENGINE_VERSION = "forward_expectations.py v1.13 (Future Price Range shadow)"

CAGR_CLAMP = (-0.50, 1.50)
MAX_PEERS = 10
SNAPSHOT_DIR = os.path.join(BASE_DIR, "investment", "invest_logs", "forward_expectations")
EVIDENCE_REQUIRED_FIELDS = (
    "metric", "value", "unit", "value_type", "source_type", "source_ref",
    "published_at", "retrieved_at", "confidence",
)
EVIDENCE_VALUE_TYPES = {"observed", "guided", "consensus", "derived", "assumption", "unknown"}


# ── numeric helpers ───────────────────────────────────────────────────────────
def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None


def _pos(x):
    v = _num(x)
    return v if v is not None and v > 0 else None


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


@contextlib.contextmanager
def _stdout_to_stderr():
    """Imported FMP/supplementary modules print progress to stdout; keep our stdout
    pure JSON by redirecting their chatter to stderr during fetch-heavy calls."""
    saved = sys.stdout
    sys.stdout = sys.stderr
    try:
        yield
    finally:
        sys.stdout = saved


def _years_between(d_old: str, d_new: str):
    try:
        a = _dt.date.fromisoformat(d_old[:10])
        b = _dt.date.fromisoformat(d_new[:10])
    except Exception:
        return None
    days = (b - a).days
    return days / 365.25 if days > 0 else None


def _cagr(v0, v1, years):
    v0, v1, years = _pos(v0), _pos(v1), _num(years)
    if v0 is None or v1 is None or years is None or years <= 0:
        return None
    return (v1 / v0) ** (1 / years) - 1


def _pct(vals, q):
    s = sorted(vals)
    if not s:
        return None
    k = (len(s) - 1) * q
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def _utc_now():
    return _dt.datetime.now(_dt.timezone.utc)


def evidence_record(metric, value, unit, value_type, source_type, source_ref,
                    published_at, retrieved_at, confidence="medium"):
    """Create an auditable model input. Unknown values are retained but rejected."""
    return {
        "metric": metric,
        "value": value,
        "unit": unit,
        "value_type": value_type,
        "source_type": source_type,
        "source_ref": source_ref,
        "published_at": published_at,
        "retrieved_at": retrieved_at,
        "confidence": confidence,
    }


def validate_evidence(records: list[dict]) -> dict:
    accepted, rejected = [], []
    for record in records:
        missing = [key for key in EVIDENCE_REQUIRED_FIELDS if record.get(key) is None]
        reason = None
        if missing:
            reason = f"missing_fields:{','.join(missing)}"
        elif record.get("value_type") not in EVIDENCE_VALUE_TYPES:
            reason = "invalid_value_type"
        elif record.get("value_type") == "unknown":
            reason = "unknown_not_model_input"
        if reason:
            rejected.append({**record, "rejection_reason": reason})
        else:
            accepted.append(record)
    return {
        "status": "pass" if not rejected else "degraded",
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "accepted": accepted,
        "rejected": rejected,
    }


# ── Lane 1: consensus (analyst annual_estimates) ──────────────────────────────
def consensus_lane(earnings_cache: dict) -> dict:
    out = {
        "available": False,
        "revenue_cagr": None, "eps_cagr": None,
        "window_from": None, "window_to": None, "window_years": None,
        "eps_spread_pct": None, "num_analysts_eps": None, "num_analysts_revenue": None,
        "analyst_rating_direction": None,
        "note": "",
    }
    est = earnings_cache.get("annual_estimates")
    if not isinstance(est, list) or len(est) < 2:
        out["note"] = "annual_estimates 缺或 <2 年，consensus lane 跳過"
        return out
    # entries are most-distant-first; sort ascending by date to get nearest→furthest
    rows = sorted([e for e in est if e.get("date")], key=lambda e: e["date"])
    near, far = rows[0], rows[-1]
    years = _years_between(near["date"], far["date"])
    rev_cagr = _cagr(near.get("revenue_avg"), far.get("revenue_avg"), years)
    eps_cagr = _cagr(near.get("eps_avg"), far.get("eps_avg"), years)
    # spread from low/high on the furthest year (analyst dispersion on the terminal view)
    eps_lo, eps_hi, eps_av = _pos(far.get("eps_low")), _pos(far.get("eps_high")), _pos(far.get("eps_avg"))
    spread = ((eps_hi - eps_lo) / eps_av * 100) if (eps_lo and eps_hi and eps_av) else None

    out.update({
        "available": rev_cagr is not None or eps_cagr is not None,
        "revenue_cagr": round(clamp(rev_cagr, *CAGR_CLAMP), 4) if rev_cagr is not None else None,
        "eps_cagr": round(clamp(eps_cagr, *CAGR_CLAMP), 4) if eps_cagr is not None else None,
        "window_from": near["date"], "window_to": far["date"],
        "window_years": round(years, 2) if years else None,
        "eps_spread_pct": round(spread, 1) if spread is not None else None,
        "num_analysts_eps": far.get("num_analysts_eps"),
        "num_analysts_revenue": far.get("num_analysts_revenue"),
        "analyst_rating_direction": _analyst_rating_direction(earnings_cache),
        "note": ("estimate-window CAGR（{}→{}）；非 trailing-base（避免低基期失真）"
                 .format(near["date"][:7], far["date"][:7])),
    })
    return out


def _analyst_rating_direction(earnings_cache: dict):
    """Net-bull rating trend from analyst_grades (most-recent vs ~2 snapshots prior)."""
    grades = earnings_cache.get("analyst_grades")
    if not isinstance(grades, list) or len(grades) < 2:
        return None
    rows = sorted([g for g in grades if g.get("date")], key=lambda g: g["date"])

    def net_bull(g):
        sb = (g.get("analystRatingsStrongBuy") or 0) + (g.get("analystRatingsBuy") or 0)
        ss = (g.get("analystRatingsSell") or 0) + (g.get("analystRatingsStrongSell") or 0)
        total = sb + (g.get("analystRatingsHold") or 0) + ss
        return (sb - ss) / total if total else None

    new, old = net_bull(rows[-1]), net_bull(rows[0])
    if new is None or old is None:
        return None
    delta = new - old
    return "UP" if delta > 0.03 else "DOWN" if delta < -0.03 else "FLAT"


# ── Lane 2: market_implied (reverse DCF) ──────────────────────────────────────
def market_implied_lane(ticker: str, inp: dict, no_fetch: bool) -> dict:
    out = {"available": False, "required_fcf_cagr": None, "out_of_range": None,
           "fcf_base_per_share": None, "wacc_used": None, "note": ""}
    try:
        import compute_price_framework as cpf
    except Exception as e:
        out["note"] = f"compute_price_framework import 失敗: {e}"
        return out
    work = {"ticker": ticker, "current_price": inp.get("current_price"),
            "reverse_dcf": dict(inp.get("reverse_dcf") or {}), "fred": dict(inp.get("fred") or {})}
    # self-assemble owner-earnings / fred / price unless caller supplied them
    if not no_fetch:
        try:
            cpf.assemble_inputs(ticker, work)
        except Exception:
            pass
    if not _pos(work.get("current_price")):
        out["note"] = "current_price 缺，market_implied 跳過"
        return out
    ie = cpf.compute_implied_expectations(work)
    out.update({
        "available": ie.get("implied_5y_fcf_cagr") is not None,
        "required_fcf_cagr": ie.get("implied_5y_fcf_cagr"),
        "out_of_range": ie.get("implied_out_of_range"),
        "fcf_base_per_share": ie.get("fcf_base"),
        "wacc_used": ie.get("wacc_used"),
        "note": ie.get("sanity_note") or "",
    })
    return out


# ── Lane 3: base_rate (peer historical revenue-CAGR distribution) ─────────────
def base_rate_lane(ticker: str, earnings_cache: dict, no_fetch: bool) -> dict:
    out = {"available": False, "peer_rev_cagr_median": None, "peer_rev_cagr_p25": None,
           "peer_rev_cagr_p75": None, "peers_used": [], "self_revenue_yoy": None,
           "growth_acceleration": None, "note": ""}
    yoy = (earnings_cache.get("derived") or {}).get("yoy_growth") or {}
    out["self_revenue_yoy"] = _num(yoy.get("revenue_yoy"))
    out["growth_acceleration"] = yoy.get("growth_acceleration")
    if no_fetch:
        out["note"] = "--no-fetch：跳過 peer 歷史抓取"
        return out
    try:
        from skills._shared.company_context import get_peers
        from scripts._shared import fmp_pool
    except Exception as e:
        out["note"] = f"peer/fmp 模組 import 失敗: {e}"
        return out
    peers = (get_peers(ticker) or [])[:MAX_PEERS]
    cagrs, used = [], []
    for p in peers:
        rows = fmp_pool.get("income-statement", {"symbol": p, "limit": 6},
                            stable=True, retries=1, timeout=15, hard_fail=False)
        if not isinstance(rows, list) or len(rows) < 4:
            continue
        rows = sorted([r for r in rows if r.get("date") and _pos(r.get("revenue"))], key=lambda r: r["date"])
        if len(rows) < 4:
            continue
        c = _cagr(rows[0]["revenue"], rows[-1]["revenue"], _years_between(rows[0]["date"], rows[-1]["date"]))
        if c is not None:
            cagrs.append(clamp(c, *CAGR_CLAMP))
            used.append(p)
    if len(cagrs) >= 3:
        out.update({
            "available": True,
            "peer_rev_cagr_median": round(_pct(cagrs, 0.50), 4),
            "peer_rev_cagr_p25": round(_pct(cagrs, 0.25), 4),
            "peer_rev_cagr_p75": round(_pct(cagrs, 0.75), 4),
            "peers_used": used,
            "note": f"{len(used)} 同業歷史營收 CAGR 分布（防過度樂觀 base rate）",
        })
    else:
        out["note"] = f"可用 peer <3（{len(cagrs)}），base_rate 跳過"
    return out


# ── Same-metric expectations matrix ──────────────────────────────────────────
def _fmt_pct(x):
    return f"{x * 100:.0f}%" if isinstance(x, (int, float)) else "N/A"


def assemble_expectations_matrix(consensus: dict, market: dict, base_rate: dict,
                                 independent: dict | None = None) -> dict:
    mi = market.get("required_fcf_cagr")
    cons_eps = consensus.get("eps_cagr")
    cons_rev = consensus.get("revenue_cagr")
    br = base_rate.get("peer_rev_cagr_median")
    ind_rev = (independent or {}).get("revenue_cagr") if (independent or {}).get("available") else None

    metrics = {
        "revenue_cagr": {"market_implied": None, "consensus": cons_rev,
                         "independent": ind_rev, "base_rate": br},
        "eps_cagr": {"market_implied": None, "consensus": cons_eps,
                     "independent": None, "base_rate": None},
        "fcf_cagr": {"market_implied": mi, "consensus": None,
                     "independent": None, "base_rate": None},
    }
    parts, comparisons = [], []
    if mi is not None:
        parts.append(f"市場隱含 5Y FCF CAGR {_fmt_pct(mi)}" + ("（out_of_range）" if market.get("out_of_range") else ""))
    if cons_eps is not None:
        parts.append(f"分析師共識 EPS CAGR {_fmt_pct(cons_eps)}")
    if cons_rev is not None:
        parts.append(f"分析師共識營收 CAGR {_fmt_pct(cons_rev)}")
    if br is not None:
        parts.append(f"同業歷史營收 base-rate 中位 {_fmt_pct(br)}")
    if ind_rev is not None:
        parts.append(f"委員會 Independent 營收 CAGR {_fmt_pct(ind_rev)}")

    if cons_rev is not None and br is not None:
        if cons_rev > br * 1.5:
            verdict = "consensus_above_base_rate"
            assessment = "分析師共識營收增速高於同業歷史 base-rate >1.5×"
        elif cons_rev < br * 0.7:
            verdict = "consensus_below_base_rate"
            assessment = "分析師共識營收增速低於同業歷史 base-rate"
        else:
            verdict = "consensus_near_base_rate"
            assessment = "分析師共識營收增速接近同業歷史 base-rate"
        comparisons.append({
            "metric": "revenue_cagr",
            "left": "consensus",
            "right": "base_rate",
            "delta": round(cons_rev - br, 4),
            "verdict": verdict,
            "assessment": assessment,
        })
    if ind_rev is not None and cons_rev is not None:
        comparisons.append({
            "metric": "revenue_cagr",
            "left": "independent",
            "right": "consensus",
            "delta": round(ind_rev - cons_rev, 4),
            "verdict": "independent_above_consensus" if ind_rev > cons_rev
            else "independent_below_consensus" if ind_rev < cons_rev
            else "independent_equals_consensus",
            "assessment": "委員會 Independent 與分析師共識營收增速的同口徑差異",
        })
    if ind_rev is not None and br is not None:
        comparisons.append({
            "metric": "revenue_cagr",
            "left": "independent",
            "right": "base_rate",
            "delta": round(ind_rev - br, 4),
            "verdict": "independent_above_base_rate" if ind_rev > br
            else "independent_below_base_rate" if ind_rev < br
            else "independent_equals_base_rate",
            "assessment": "委員會 Independent 與同業歷史 base-rate 的同口徑差異",
        })

    return {
        "metrics": metrics,
        "same_metric_comparisons": comparisons,
        "verdict": "same_metric_gap_available" if comparisons else "comparison_unavailable",
        "assessment": "；".join(parts),
        "cross_metric_policy": "FCF、EPS、營收 CAGR 不互減、不產生跨口徑 verdict。",
    }


def build_evidence_contract(earnings_cache: dict, consensus: dict, market: dict,
                            base_rate: dict, retrieved_at: str) -> dict:
    published_at = earnings_cache.get("as_of_date") or earnings_cache.get("last_earnings_date") or "unknown"
    records = []
    for metric, value in (
        ("consensus_revenue_cagr", consensus.get("revenue_cagr")),
        ("consensus_eps_cagr", consensus.get("eps_cagr")),
    ):
        if value is not None:
            records.append(evidence_record(
                metric, value, "ratio", "consensus", "fmp_analyst_estimates",
                "earnings-analyst cache annual_estimates", published_at, retrieved_at,
            ))
    if market.get("required_fcf_cagr") is not None:
        records.append(evidence_record(
            "market_implied_fcf_cagr", market["required_fcf_cagr"], "ratio", "derived",
            "reverse_dcf", "compute_price_framework.compute_implied_expectations",
            retrieved_at[:10], retrieved_at,
        ))
    if base_rate.get("peer_rev_cagr_median") is not None:
        records.append(evidence_record(
            "base_rate_peer_revenue_cagr_median", base_rate["peer_rev_cagr_median"], "ratio",
            "derived", "fmp_peer_history", ",".join(base_rate.get("peers_used") or []),
            retrieved_at[:10], retrieved_at,
        ))
    return validate_evidence(records)


# ── self-assemble earnings cache ──────────────────────────────────────────────
def _latest_earnings_cache(ticker: str) -> dict | None:
    files = [f for f in _glob.glob(os.path.join(
        BASE_DIR, "skills", "earnings-analyst", "cache", f"{ticker.upper()}_*.json"))
        if ".infographic." not in f]
    if not files:
        return None
    try:
        with open(sorted(files)[-1], encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _current_price(ticker: str, inp: dict, earnings_cache: dict, no_fetch: bool):
    if _pos(inp.get("current_price")):
        return inp["current_price"]
    snap_px = _pos((earnings_cache.get("snapshot") or {}).get("price"))
    if no_fetch:
        return snap_px
    try:
        from scripts._shared import fmp_pool
        q = fmp_pool.get("quote", {"symbol": ticker}, stable=True, retries=1, timeout=15, hard_fail=False)
        row = q[0] if isinstance(q, list) and q else (q if isinstance(q, dict) else {})
        return _pos(row.get("price")) or snap_px
    except Exception:
        return snap_px


def write_snapshot(payload: dict) -> str | None:
    try:
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        path = os.path.join(SNAPSHOT_DIR, f"{payload['ticker']}_{payload['run_id']}.json")
        with open(path, "x", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path
    except FileExistsError:
        print(f"WARN: immutable snapshot exists for run_id={payload.get('run_id')}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"WARN: snapshot write failed: {e}", file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser(description="Forward expectations engine (Phase 1 shadow)")
    ap.add_argument("--ticker")
    ap.add_argument("--from-file", help="input JSON path (default: stdin if no --ticker)")
    ap.add_argument("--self-assemble", action="store_true",
                    help="讀 earnings-analyst cache + FMP（owner earnings / peers / quote）自組")
    ap.add_argument("--no-fetch", action="store_true", help="不打 FMP（只用 cache + 輸入）")
    ap.add_argument("--no-snapshot", action="store_true", help="不寫 point-in-time 快照")
    ap.add_argument("--primary-source-file",
                    help="explicit primary-source JSON bundle（cache-first；不主動上網）")
    ap.add_argument("--acquire-documents", action="store_true",
                    help="opt-in SEC filing document download/normalization from source discovery")
    ap.add_argument("--max-documents", type=int, default=3,
                    help="max allowlisted documents to acquire when --acquire-documents is set")
    args = ap.parse_args()

    inp = {}
    if args.from_file or (not args.ticker and not sys.stdin.isatty()):
        try:
            raw = open(args.from_file).read() if args.from_file else sys.stdin.read()
            inp = json.loads(raw) if raw.strip() else {}
        except Exception as e:
            print(json.dumps({"error": f"unparseable input: {e}"}))
            sys.exit(1)
    if args.primary_source_file:
        try:
            with open(args.primary_source_file, encoding="utf-8") as handle:
                inp["primary_source_bundle"] = json.load(handle)
        except Exception as e:
            print(json.dumps({"error": f"unparseable primary-source file: {e}"}))
            sys.exit(1)

    ticker = (args.ticker or inp.get("ticker") or "").upper()
    if not ticker:
        print(json.dumps({"error": "ticker required (--ticker or in input JSON)"}))
        sys.exit(1)

    ec = _latest_earnings_cache(ticker) or {}
    if not ec and not inp.get("annual_estimates"):
        print(json.dumps({"error": f"no earnings-analyst cache for {ticker}; run 財報 {ticker} first"}))
        sys.exit(1)
    if inp.get("annual_estimates"):
        ec = {**ec, **{k: inp[k] for k in ("annual_estimates", "analyst_grades", "derived") if k in inp}}

    with _stdout_to_stderr():
        cp = _current_price(ticker, inp, ec, args.no_fetch)
    if cp is not None:
        inp["current_price"] = cp

    consensus = consensus_lane(ec)
    with _stdout_to_stderr():
        market = market_implied_lane(ticker, inp, args.no_fetch)
        base_rate = base_rate_lane(ticker, ec, args.no_fetch)
    from forward_expectations_adapters import evaluate_adapters
    adapter_evaluation = evaluate_adapters(ticker, ec, inp)
    selected_adapter = adapter_evaluation["selected_adapter"]
    from forward_expectations_evidence import build_inventory
    from forward_expectations_document_acquisition import acquire_documents
    from forward_expectations_primary_sources import acquire_primary_evidence
    from forward_expectations_revisions import build_revision_snapshot
    from forward_expectations_source_discovery import discover_sources
    from forward_expectations_financial_bridge import build_financial_bridge
    from forward_expectations_gap import build_expectations_gap
    from forward_expectations_scenario_policy import build_scenario_policy
    from forward_expectations_scenario_builder import build_operating_driver_scenarios
    from forward_expectations_price_range import build_future_price_range
    generated = _utc_now()
    generated_at = generated.isoformat(timespec="microseconds")
    run_id = generated.strftime("%Y%m%dT%H%M%S%fZ")
    source_discovery = discover_sources(
        ticker, ec, inp.get("source_discovery"), no_fetch=args.no_fetch,
    )
    document_acquisition = acquire_documents(
        source_discovery,
        no_fetch=(not args.acquire_documents) or args.no_fetch,
        max_documents=args.max_documents,
    )
    primary_bundle = inp.get("primary_source_bundle")
    if document_acquisition.get("documents"):
        base_documents = list((primary_bundle or {}).get("documents") or [])
        primary_bundle = {**(primary_bundle or {}), "documents": base_documents + document_acquisition["documents"]}
    primary_acquisition = acquire_primary_evidence(ec, primary_bundle)
    guidance_extraction = {
        "summary": {
            "candidate_count": primary_acquisition["summary"].get("guidance_candidate_count", 0),
            "promoted_count": primary_acquisition["summary"].get("guidance_promoted_count", 0),
            "provisional_count": len(primary_acquisition.get("guidance_provisional") or []),
        },
        "promoted": primary_acquisition.get("guidance_promoted") or [],
        "provisional": primary_acquisition.get("guidance_provisional") or [],
        "policy": "Management guidance is structured evidence; ranges remain ranges.",
    }
    revision_snapshot = build_revision_snapshot(ticker, ec, generated_at)
    financial_bridge = build_financial_bridge(
        ec, primary_acquisition.get("guidance_promoted") or [], generated_at,
    )
    evidence_inventory = build_inventory(
        ticker, ec, selected_adapter.get("adapter_id"), generated_at,
        primary_acquisition=primary_acquisition,
        source_discovery=source_discovery,
        revision_snapshot=revision_snapshot,
    )
    adapter_evaluation = evaluate_adapters(ticker, ec, {**inp, "evidence_inventory": evidence_inventory})
    selected_adapter = adapter_evaluation["selected_adapter"]
    independent = selected_adapter.get("independent_lane") or {
        "available": False, "revenue_cagr": None, "reason": "adapter_output_missing",
    }
    matrix = assemble_expectations_matrix(consensus, market, base_rate, independent)
    expectations_gap = build_expectations_gap(
        consensus, market, independent, base_rate, financial_bridge,
    )
    scenario_policy = build_scenario_policy(
        consensus, independent, adapter_evaluation, financial_bridge, guidance_extraction,
    )
    operating_driver_scenarios = build_operating_driver_scenarios(
        scenario_policy, independent, adapter_evaluation, financial_bridge, guidance_extraction,
    )
    future_price_range = build_future_price_range(
        ticker, inp.get("current_price"), financial_bridge, ec, inp.get("valuation_multiples") or {},
    )
    evidence = build_evidence_contract(ec, consensus, market, base_rate, generated_at)

    out = {
        "engine": ENGINE_VERSION,
        "ticker": ticker,
        "run_id": run_id,
        "generated_at": generated_at,
        "as_of_earnings_date": ec.get("as_of_date") or ec.get("last_earnings_date"),
        "current_price": inp.get("current_price"),
        "shadow_only": True,
        "consensus_lane": consensus,
        "market_implied_lane": market,
        "base_rate_lane": base_rate,
        "independent_lane": independent,
        "adapter_evaluation": adapter_evaluation,
        "evidence_inventory": evidence_inventory,
        "source_discovery": source_discovery,
        "document_acquisition": document_acquisition,
        "primary_source_acquisition": primary_acquisition,
        "guidance_extraction": guidance_extraction,
        "estimate_revision_snapshot": revision_snapshot,
        "forward_financial_bridge": financial_bridge,
        "expectations_gap": expectations_gap,
        "scenario_policy": scenario_policy,
        "operating_driver_scenarios": operating_driver_scenarios,
        "future_price_range": future_price_range,
        "expectations_matrix": matrix,
        "evidence_contract": evidence,
    }
    if not args.no_snapshot:
        sp = write_snapshot(out)
        if sp:
            out["snapshot_path"] = sp
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
