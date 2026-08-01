#!/usr/bin/env python3
"""build_fact_pack.py — Aggregate 12-section facts + decision_lock hash.

Reads (no new network calls beyond profile/peers which are 24h-cached):
- _shared.company_context.get_profile / get_peers / get_quote
- skills/earnings-analyst/cache/<T>_<earnings_date>.json (latest non-infographic)
- investment/invest_logs/history.json (latest trades_this_session[] entry for ticker)
- skills/ic-memo-writer/cache/peer_descriptor/<T>.json (stub OK)

Writes:
- skills/ic-memo-writer/cache/<T>_<DATE>_fact_pack.json

Exit codes:
  0  ok (memo can be composed)
  2  fatal: profile fetch failed
  3  fatal: no protocol history entry for ticker
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

from skills._shared import company_context as cc  # noqa: E402
from peer_rosters import get_peer_roster  # noqa: E402

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
PEER_DESC_DIR = CACHE_DIR / "peer_descriptor"
HISTORY_PATH = ROOT / "investment" / "invest_logs" / "history.json"
EARNINGS_CACHE_DIR = ROOT / "skills" / "earnings-analyst" / "cache"

LOCK_FIELDS = [
    "final_decision", "final_action", "position_size_pct", "analysis_price",
    "fair_value_summary", "scenario_odds", "watch_conditions", "key_risks",
    "red_team_counter_thesis", "red_team_kill_conditions", "lane_scores",
]

SCHEMA_VERSION = "1.0"
COMPOSER_VERSION = "V1.0.0"


def _round_floats(obj):
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, dict):
        return {k: _round_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(x) for x in obj]
    return obj


def _as_dict(v) -> dict:
    """LLM-written history fields can drift to string/list (moat_assessment 前科).
    Coerce non-dict to {} so renderers never crash on .get()/.items()."""
    return v if isinstance(v, dict) else {}


def _as_list(v) -> list:
    return v if isinstance(v, list) else ([] if v is None else [v])


def compute_decision_lock(trade: dict) -> dict:
    payload = {k: _round_floats(trade.get(k)) for k in LOCK_FIELDS if k in trade}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    h = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {"fields": LOCK_FIELDS, "payload": payload, "hash": h}


def load_latest_history_entry(ticker: str) -> tuple[dict, dict, int] | None:
    """Return (session_entry, trade_entry, trade_index) for latest matching session."""
    if not HISTORY_PATH.exists():
        return None
    h = json.loads(HISTORY_PATH.read_text())
    if not isinstance(h, list):
        return None
    for idx in range(len(h) - 1, -1, -1):
        e = h[idx]
        if e.get("ticker") == ticker:
            trades = e.get("trades_this_session") or []
            for t_idx, t in enumerate(trades):
                if isinstance(t, dict) and t.get("ticker") == ticker:
                    return e, t, idx
            # No trade matching this ticker in the session — keep scanning older
            # entries. Falling back to trades[0] here would hash a DIFFERENT
            # ticker's decision into decision_lock.
    return None


def load_latest_earnings_cache(ticker: str) -> tuple[dict | None, str | None, int | None]:
    pattern = str(EARNINGS_CACHE_DIR / f"{ticker}_*.json")
    files = [f for f in glob.glob(pattern) if "infographic" not in f]
    if not files:
        return None, None, None
    files.sort()
    latest = files[-1]
    try:
        d = json.loads(Path(latest).read_text())
    except Exception:
        return None, None, None
    earnings_date = d.get("last_earnings_date") or d.get("as_of_date") or ""
    stale_days = None
    if earnings_date:
        try:
            ed = datetime.fromisoformat(earnings_date[:10])
            stale_days = (datetime.now() - ed).days
        except Exception:
            pass
    return d, latest, stale_days


def load_or_init_peer_descriptor(ticker: str) -> dict:
    PEER_DESC_DIR.mkdir(parents=True, exist_ok=True)
    p = PEER_DESC_DIR / f"{ticker}.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    stub = {
        "ticker": ticker,
        "peers": {},
        "status": "stub_no_llm",
        "llm_model": None,
        "generated_at": None,
        "ttl_days": 14,
        "note": "First-version stub. Phase A.5 will swap to Haiku 4.5 one-shot batch.",
    }
    p.write_text(json.dumps(stub, indent=2, ensure_ascii=False))
    return stub


def safe_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(k)
        else:
            return default
    return cur if cur is not None else default


def _safe_float(v):
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _sum_optional(*vals):
    nums = [_safe_float(v) for v in vals if v is not None]
    if not nums:
        return None
    return sum(nums)


def _derive_surprise_pct(row: dict) -> dict:
    out = dict(row)
    if out.get("surprise_pct") is not None or out.get("surprisePercentage") is not None:
        return out
    actual = _safe_float(out.get("epsActual") or out.get("eps_actual"))
    estimated = _safe_float(out.get("epsEstimated") or out.get("eps_estimated"))
    if actual is not None and estimated not in (None, 0):
        out["surprise_pct"] = round((actual - estimated) / abs(estimated) * 100, 2)
    return out


def _flatten_ttm_metrics(ttm: dict) -> dict:
    out = dict(ttm or {})
    ratios = out.get("from_ratios_ttm") or {}
    key_metrics = out.get("from_key_metrics_ttm") or {}
    if out.get("gross_margin") is None:
        out["gross_margin"] = ratios.get("grossProfitMarginTTM")
    if out.get("operating_margin") is None:
        out["operating_margin"] = ratios.get("operatingProfitMarginTTM")
    if out.get("net_margin") is None:
        out["net_margin"] = ratios.get("netProfitMarginTTM")
    if out.get("fcf_yield") is None:
        out["fcf_yield"] = key_metrics.get("freeCashFlowYieldTTM")
    return out


def _latest_ttm_from_quarters(earnings_cache: dict) -> dict:
    qpnl = earnings_cache.get("quarterly_pnl") or []
    cflow = earnings_cache.get("cash_flow") or []
    out = {}

    def _sum_rows(rows, field):
        vals = [_safe_float(r.get(field)) for r in rows[:4]]
        vals = [v for v in vals if v is not None]
        return sum(vals) if vals else None

    out["revenue_ttm"] = _sum_rows(qpnl, "revenue")
    out["net_income_ttm"] = _sum_rows(qpnl, "netIncome")
    out["fcf_ttm"] = _sum_rows(cflow, "freeCashFlow")
    return {k: v for k, v in out.items() if v is not None}


def section_1_summary(profile: dict, trade: dict) -> dict:
    fv = trade.get("fair_value_summary") or {}
    live_spot = profile.get("price")
    weighted_fv = fv.get("weighted_fair_value")
    live_spot_f = _safe_float(live_spot)
    weighted_fv_f = _safe_float(weighted_fv)
    fv_vs_live_pct = None
    if live_spot_f not in (None, 0) and weighted_fv_f is not None:
        fv_vs_live_pct = round((weighted_fv_f - live_spot_f) / live_spot_f * 100, 2)
    return {
        "ticker": profile.get("symbol"),
        "company_name": profile.get("companyName"),
        "current_price": live_spot,
        "live_spot": live_spot,
        "analysis_price": trade.get("analysis_price") or fv.get("current_price"),
        "range": profile.get("range"),
        "market_cap": profile.get("marketCap"),
        "sector": profile.get("sector"),
        "industry": profile.get("industry"),
        "final_action": trade.get("final_action"),
        "final_decision": trade.get("final_decision"),
        "verdict_band": fv.get("verdict_band"),
        "weighted_fair_value": weighted_fv,
        "fv_vs_current_pct": fv.get("vs_current_pct"),
        "fv_vs_analysis_pct": fv.get("vs_current_pct"),
        "fv_vs_live_pct": fv_vs_live_pct,
        "decision_confidence_pct": trade.get("decision_confidence_pct"),
        "position_size_pct": trade.get("position_size_pct"),
        "entry_aggressive": trade.get("entry_aggressive"),
        "entry_conservative": trade.get("entry_conservative"),
        "stop_loss": trade.get("stop_loss"),
        "take_profit": trade.get("take_profit"),
        "risk_reward_ratio": trade.get("risk_reward_ratio"),
        "time_horizon": trade.get("time_horizon"),
        "fragility_label": trade.get("fragility_label"),
    }


def section_2_company(profile: dict) -> dict:
    return {
        "description": profile.get("description") or "",
        "ceo": profile.get("ceo"),
        "full_time_employees": profile.get("fullTimeEmployees"),
        "ipo_date": profile.get("ipoDate"),
        "city": profile.get("city"),
        "state": profile.get("state"),
        "country": profile.get("country"),
        "website": profile.get("website"),
    }


def section_3_revenue(earnings_cache: dict | None) -> dict:
    if not earnings_cache:
        return {"_stub": True}
    segs = earnings_cache.get("segments") or {}
    overlay = earnings_cache.get("business_mix_shift_overlay") or {}
    return {
        "product_fy": segs.get("product_fy") or [],
        "geographic_fy": segs.get("geographic_fy") or [],
        "business_mix_overlay": overlay,
    }


def section_4_competitive(trade: dict, peers: list, peer_descriptor: dict, ticker: str | None = None) -> dict:
    fund = trade.get("fundamentals_lane") or {}
    moat = fund.get("moat_assessment") or {}
    # V3.49.0 — 近期 entry 的 moat_assessment 被 LLM 寫成 string（schema 要求 dict）。
    # 容錯：string → 當 evidence 全文塞 evidence 欄，level/type 缺 → degraded 不 crash。
    if isinstance(moat, str):
        moat = {"level": None, "type": None, "evidence_one_line": moat}
    elif not isinstance(moat, dict):
        moat = {}
    roster = get_peer_roster(ticker or trade.get("ticker") or "")
    return {
        "moat_level": moat.get("level"),
        "moat_type": moat.get("type"),
        "moat_evidence": moat.get("evidence_one_line"),
        "peers": roster or peers or [],
        "peer_source": "local_roster" if roster else "fmp_peers",
        "peer_descriptor": peer_descriptor,
    }


def section_5_financials(earnings_cache: dict | None) -> dict:
    if not earnings_cache:
        return {"_stub": True}
    ttm = _flatten_ttm_metrics(earnings_cache.get("ttm_metrics") or {})
    for k, v in _latest_ttm_from_quarters(earnings_cache).items():
        ttm.setdefault(k, v)
    return {
        "quarterly_pnl": earnings_cache.get("quarterly_pnl") or [],
        "ttm_metrics": ttm,
        "earnings_surprises": [_derive_surprise_pct(s) for s in (earnings_cache.get("earnings_surprises") or [])],
    }


def section_6_balance_cash(earnings_cache: dict | None) -> dict:
    if not earnings_cache:
        return {"_stub": True}
    balance = []
    for b in (earnings_cache.get("balance_sheet") or [])[:1]:
        row = dict(b)
        row["cash_and_st_investments"] = _sum_optional(
            row.get("cashAndShortTermInvestments"),
            row.get("cashAndCashEquivalents"),
            row.get("shortTermInvestments"),
        )
        row["total_stockholders_equity"] = (
            row.get("totalStockholdersEquity")
            or row.get("stockholders_equity")
            or row.get("totalEquity")
        )
        balance.append(row)
    return {
        "balance_sheet": balance,
        "cash_flow": (earnings_cache.get("cash_flow") or [])[:1],
        "cash_conversion_quality": earnings_cache.get("cash_conversion_quality"),
        "quality_flags": earnings_cache.get("quality_flags") or {},
    }


def section_7_profitability(earnings_cache: dict | None) -> dict:
    if not earnings_cache:
        return {"_stub": True}
    return {
        "annual_growth": earnings_cache.get("annual_growth") or {},
        "annual_estimates": earnings_cache.get("annual_estimates") or [],
        "structural_shift": earnings_cache.get("structural_shift") or {},
        "transition_signature": earnings_cache.get("transition_signature"),
    }


def section_8_valuation(trade: dict, earnings_cache: dict | None) -> dict:
    fv = _as_dict(trade.get("fair_value_summary"))
    pt_news = []
    if earnings_cache:
        val = _as_dict(earnings_cache.get("valuation"))
        pt_news = _as_list(val.get("pt_news"))[:10]
    return {
        "fair_value_summary": fv,
        "pt_news": pt_news,
        # V3.49.0 — V3.45.x+ sibling blocks（舊 entry 缺 → {}，render 自動略過；
        # 全部 advisory，不在 11-field decision_lock 內，§11 verbatim 不受影響）
        "fair_value_range": _as_dict(trade.get("fair_value_range")),
        "implied_expectations": _as_dict(trade.get("implied_expectations"))
            or _as_dict(_as_dict(trade.get("valuation_lane")).get("implied_expectations")),
        "multi_horizon": _as_dict(trade.get("multi_horizon_price_framework")),
        "archetype_shadow": _as_dict(trade.get("valuation_archetype_shadow")),
    }


def section_9_catalysts_risks(trade: dict) -> dict:
    fund = _as_dict(trade.get("fundamentals_lane"))
    news = _as_dict(trade.get("news_lane"))
    return {
        "near_term_catalysts": _as_list(fund.get("near_term_catalysts")),
        "cross_asset_spillover": _as_list(news.get("cross_asset_spillover")),
        "decision_point_days": news.get("decision_point_days"),
        "key_risks": _as_list(trade.get("key_risks")),
        "watch_conditions": trade.get("watch_conditions") or {},
    }


def section_10_scenarios(trade: dict) -> dict:
    return {
        "scenario_odds": _as_dict(trade.get("scenario_odds")),
        "red_team_counter_thesis": trade.get("red_team_counter_thesis") or "",
        "red_team_kill_conditions": _as_list(trade.get("red_team_kill_conditions")),
    }


def section_11_decision(trade: dict) -> dict:
    """§11 is the protocol decision verbatim — composer must NOT alter."""
    return {
        "final_action": trade.get("final_action"),
        "final_decision": trade.get("final_decision"),
        "entry_aggressive": trade.get("entry_aggressive"),
        "entry_conservative": trade.get("entry_conservative"),
        "stop_loss": trade.get("stop_loss"),
        "take_profit": trade.get("take_profit"),
        "position_size_pct": trade.get("position_size_pct"),
        "position_size_method": trade.get("position_size_method"),
        "staged_split": trade.get("staged_split"),
        "watch_conditions": trade.get("watch_conditions") or {},
    }


def section_12_appendix(trade: dict, degraded: list, provenance: dict) -> dict:
    return {
        "lane_scores": trade.get("lane_scores") or {},
        "decision_confidence_pct": trade.get("decision_confidence_pct"),
        "provenance": provenance,
        "degraded_sections": degraded,
    }


VM_CACHE_DIR = ROOT / "skills" / "valuation-modeler" / "cache"


def load_valuation_model(ticker: str) -> tuple[dict | None, list[str]]:
    """V4.69.0 --initiation：讀 valuation-modeler 的 dcf/comps payload cache。
    缺檔回 (None, [確切補跑指令])——deterministic，不自動抓。"""
    missing = []
    out = {}
    for kind, fname in (("dcf", f"{ticker}_dcf_payload.json"),
                        ("comps", f"{ticker}_comps_payload.json")):
        p = VM_CACHE_DIR / fname
        if not p.exists():
            missing.append(
                f"python3 skills/valuation-modeler/scripts/{kind}.py {ticker} --json-only")
            continue
        try:
            out[kind] = json.loads(p.read_text())
        except Exception:
            missing.append(
                f"python3 skills/valuation-modeler/scripts/{kind}.py {ticker} --json-only  # cache 損毀，重跑")
    return (out if not missing else None), missing


def build(ticker: str, *, output_dir: Path | None = None, initiation: bool = False) -> tuple[Path, dict]:
    ticker = ticker.upper()
    output_dir = output_dir or CACHE_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Profile (fatal if fail)
    try:
        profile = cc.get_profile(ticker)
    except Exception as exc:
        print(f"[ic-memo] FATAL: profile fetch failed for {ticker}: {exc}", file=sys.stderr)
        sys.exit(2)
    if not profile or not profile.get("symbol"):
        print(f"[ic-memo] FATAL: empty profile for {ticker}", file=sys.stderr)
        sys.exit(2)

    # History entry (fatal if missing)
    hist = load_latest_history_entry(ticker)
    if not hist:
        print(
            f"[ic-memo] FATAL: no protocol history entry for {ticker}. "
            f"Run `分析 {ticker}` first.",
            file=sys.stderr,
        )
        sys.exit(3)
    session_entry, trade, hist_idx = hist

    # Peers (local IC-memo roster first; shared FMP peers as fallback)
    degraded: list[str] = []
    local_roster = get_peer_roster(ticker)
    if local_roster:
        peers = local_roster
        peer_source_path = "skills/ic-memo-writer/peer_rosters.py"
        peer_source_type = "peers.local_roster"
    else:
        try:
            peers = cc.get_peers(ticker) or []
        except Exception:
            peers = []
            degraded.append("sec_4_peers")
        print(
            f"[ic-memo] peer_roster fallback to shared FMP peers for {ticker}",
            file=sys.stderr,
        )
        peer_source_path = f"_shared/cache/peers/{ticker}.json (24h)"
        peer_source_type = "peers.shared"

    # Earnings cache (degraded if missing)
    earnings_cache, earnings_path, earnings_stale_days = load_latest_earnings_cache(ticker)
    if not earnings_cache:
        for sec in ("sec_3", "sec_5", "sec_6", "sec_7"):
            degraded.append(sec)

    # Peer descriptor (always stub in V1.0)
    peer_descriptor = load_or_init_peer_descriptor(ticker)
    if peer_descriptor.get("status") == "stub_no_llm":
        degraded.append("sec_4_peer_descriptor_stub")

    # Phase 4.5 confidence flag
    fv = _as_dict(trade.get("fair_value_summary"))
    if (fv.get("anchors_available") or 0) < 3:
        degraded.append("sec_8_low_confidence")

    # Provenance roster
    now_iso = datetime.now(timezone.utc).isoformat()
    provenance = {
        "profile": {
            "path": f"live:fmp/profile/{ticker}",
            "fetched_at": now_iso,
            "type": "profile.live",
        },
        "protocol_history": {
            "path": f"investment/invest_logs/history.json#entry[{hist_idx}]",
            "session_date": session_entry.get("date") or session_entry.get("export_date"),
            "session_export_version": session_entry.get("session_export_version"),
            "type": "protocol.history",
        },
        "earnings_cache": {
            "path": str(Path(earnings_path).relative_to(ROOT)) if earnings_path else None,
            "stale_days": earnings_stale_days,
            "type": "earnings_analyst.cache",
            "available": earnings_cache is not None,
        },
        "peers": {
            "path": peer_source_path,
            "count": len(peers),
            "type": peer_source_type,
        },
        "peer_descriptor": {
            "path": str((PEER_DESC_DIR / f"{ticker}.json").relative_to(ROOT)),
            "status": peer_descriptor.get("status"),
            "llm_model": peer_descriptor.get("llm_model"),
            "type": "llm_synth.peer_descriptor",
        },
    }

    # Compose facts
    facts = {
        "sec_1": section_1_summary(profile, trade),
        "sec_2": section_2_company(profile),
        "sec_3": section_3_revenue(earnings_cache),
        "sec_4": section_4_competitive(trade, peers, peer_descriptor, ticker=ticker),
        "sec_5": section_5_financials(earnings_cache),
        "sec_6": section_6_balance_cash(earnings_cache),
        "sec_7": section_7_profitability(earnings_cache),
        "sec_8": section_8_valuation(trade, earnings_cache),
        "sec_9": section_9_catalysts_risks(trade),
        "sec_10": section_10_scenarios(trade),
        "sec_11": section_11_decision(trade),
        "sec_12": section_12_appendix(trade, degraded, provenance),
    }

    decision_lock = compute_decision_lock(trade)

    fact_pack = {
        "schema_version": SCHEMA_VERSION,
        "composer_version": COMPOSER_VERSION,
        "ticker": ticker,
        "as_of": datetime.now().strftime("%Y-%m-%d"),
        "composed_at": now_iso,
        "sources": provenance,
        "facts": facts,
        "degraded_sections": degraded,
        "_protocol_decision_lock": decision_lock,
    }

    # V4.69.0 — initiation 模式：嵌入 valuation-modeler 自建 DCF/comps payload
    if initiation:
        vm, missing_cmds = load_valuation_model(ticker)
        if vm is None:
            print("[ic-memo] --initiation 需要 valuation-modeler cache，先跑：", file=sys.stderr)
            for cmd in missing_cmds:
                print(f"  {cmd}", file=sys.stderr)
            sys.exit(4)
        fact_pack["valuation_model"] = vm
        provenance["valuation_model"] = {
            "dcf_path": str((VM_CACHE_DIR / f"{ticker}_dcf_payload.json").relative_to(ROOT)),
            "comps_path": str((VM_CACHE_DIR / f"{ticker}_comps_payload.json").relative_to(ROOT)),
            "dcf_asof": vm["dcf"].get("asof"),
            "comps_asof": vm["comps"].get("asof"),
            "type": "valuation_modeler.payload",
        }

    # Stable hash for fact_pack (excluding composed_at)
    stable_copy = {k: v for k, v in fact_pack.items() if k != "composed_at"}
    fact_pack_canonical = json.dumps(stable_copy, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    fact_pack["fact_pack_hash"] = hashlib.sha256(fact_pack_canonical.encode("utf-8")).hexdigest()

    date_str = datetime.now().strftime("%Y%m%d")
    out_path = output_dir / f"{ticker}_{date_str}_fact_pack.json"
    out_path.write_text(json.dumps(fact_pack, indent=2, ensure_ascii=False))

    return out_path, fact_pack


def main():
    ap = argparse.ArgumentParser(description="Build IC Memo fact_pack from protocol cache.")
    ap.add_argument("ticker", help="Stock ticker (case-insensitive)")
    ap.add_argument("--output-dir", type=Path, default=None, help="Override output dir")
    ap.add_argument("--initiation", action="store_true",
                    help="V4.69.0 首次覆蓋模式：嵌入 valuation-modeler DCF/comps payload（缺 cache 即失敗）")
    args = ap.parse_args()

    out_path, fact_pack = build(args.ticker, output_dir=args.output_dir, initiation=args.initiation)
    print(f"[ic-memo] fact_pack written: {out_path}")
    print(f"  ticker:              {fact_pack['ticker']}")
    print(f"  as_of:               {fact_pack['as_of']}")
    print(f"  degraded_sections:   {fact_pack['degraded_sections']}")
    print(f"  decision_lock_hash:  {fact_pack['_protocol_decision_lock']['hash'][:16]}...")
    print(f"  fact_pack_hash:      {fact_pack['fact_pack_hash'][:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
