#!/usr/bin/env python3
"""
thematic-screener enrich.py — per-mover guardrail + tier enrichment.

Reads existing caches (zero-cost) + light FMP HTTP fetches (PT consensus,
recent grades). Tags each mover with:
  - market_cap_tier: large / mid / small / micro / unknown
  - earnings landmine: days_to_earnings, earnings_within_5d / 10d
  - quality flags: Altman Z + Piotroski F → red_flag / premium
  - smart money: insider 90d net buy, institutional QoQ accumulation
  - forward consensus: analyst PT upside %, recent rating upgrades
  - enrichment_multiplier: composite for downstream final score

Usage (standalone smoke test):
  python3 enrich.py AAPL MSFT NVDA
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = Path(__file__).resolve().parent.parent
SHARED_CACHE = ROOT / "skills" / "_shared" / "cache"
SUPP_CACHE = ROOT / "skills" / "_shared" / "fmp_supp_cache"
EARNINGS_CACHE = ROOT / "skills" / "earnings-analyst" / "cache"
ENRICH_CACHE = SKILL_DIR / "cache" / "enrich"
ENRICH_CACHE.mkdir(parents=True, exist_ok=True)

# Fall back to company_context.get_profile() for ticker not in shared cache
sys.path.insert(0, str(ROOT / "skills" / "_shared"))
try:
    from company_context import get_profile as _get_profile_remote
except ImportError:
    _get_profile_remote = None

ENRICH_TTL_SEC = 6 * 3600  # 6h

# Market-cap tier thresholds (USD)
TIER_BREAKS = [
    (10_000_000_000, "large_cap"),
    (2_000_000_000,  "mid_cap"),
    (300_000_000,    "small_cap"),
    (0,              "micro_cap"),
]


# ---------- read-only helpers (zero new API call) ----------

def _latest_glob(pattern: str) -> Path | None:
    files = sorted(glob.glob(pattern), reverse=True)
    return Path(files[0]) if files else None


def read_profile(ticker: str) -> dict:
    """company_context profile (24h cache, FMP fallback fetch).

    Reads cache first; if missing AND company_context importable AND FMP key
    available, fetches via company_context.get_profile (which writes cache for
    next call). Returns {} only when both unavailable.
    """
    p = SHARED_CACHE / f"{ticker}_profile.json"
    if p.exists():
        try:
            return json.load(open(p))
        except Exception:
            pass
    if _get_profile_remote is None:
        return {}
    try:
        prof = _get_profile_remote(ticker)
        return prof or {}
    except Exception:
        return {}


def read_earnings_cache(ticker: str) -> dict:
    """Latest earnings-analyst bundle (per-quarter file)."""
    p = _latest_glob(str(EARNINGS_CACHE / f"{ticker}_*.json"))
    if not p or "infographic" in p.name:
        # Skip the infographic sidecar
        p2 = _latest_glob(str(EARNINGS_CACHE / f"{ticker}_*[0-9].json"))
        p = p2 or p
    if not p:
        return {}
    try:
        return json.load(open(p))
    except Exception:
        return {}


def read_supp_bundle(ticker: str) -> dict:
    """Latest fmp_supp_cache bundle for ticker (today's preferred)."""
    today = date.today().isoformat()
    p = SUPP_CACHE / f"{ticker}_{today}_supp.json"
    if not p.exists():
        p = _latest_glob(str(SUPP_CACHE / f"{ticker}_*_supp.json"))
    if not p or not Path(p).exists():
        return {}
    try:
        return json.load(open(p))
    except Exception:
        return {}


# ---------- light FMP fetch (PT consensus + grades) ----------

def _fmp_get(path: str, params: dict, timeout: int = 12) -> list | dict | None:
    api_key = os.environ.get("FMP_API_KEY", "")
    if not api_key:
        return None
    qs = urllib.parse.urlencode({**params, "apikey": api_key})
    url = f"https://financialmodelingprep.com/stable/{path}?{qs}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "thematic-screener/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def fetch_pt_consensus(ticker: str) -> dict:
    """Returns {target, high, low, count} or {}."""
    data = _fmp_get("price-target-consensus", {"symbol": ticker}) or []
    if not data:
        return {}
    d = data[0] if isinstance(data, list) else data
    return {
        "target":  d.get("targetConsensus"),
        "high":    d.get("targetHigh"),
        "low":     d.get("targetLow"),
        "median":  d.get("targetMedian"),
    }


def fetch_grades_recent(ticker: str, days_back: int = 30) -> dict:
    """Count recent rating upgrades vs downgrades."""
    data = _fmp_get("grades-historical", {"symbol": ticker, "limit": 20}) or []
    if not data:
        return {"upgrades": 0, "downgrades": 0, "since_days": days_back}
    cutoff = (date.today() - timedelta(days=days_back)).isoformat()
    up = down = 0
    for r in data:
        d = r.get("date", "")
        if d < cutoff:
            continue
        action = (r.get("action") or "").lower()
        if action == "upgrade":
            up += 1
        elif action == "downgrade":
            down += 1
    return {"upgrades": up, "downgrades": down, "since_days": days_back}


# ---------- per-mover enrichment ----------

def classify_market_cap(mc: float | int | None) -> tuple[str, float | None]:
    if mc is None or not isinstance(mc, (int, float)) or mc <= 0:
        return ("unknown", None)
    for threshold, label in TIER_BREAKS:
        if mc >= threshold:
            return (label, float(mc))
    return ("unknown", float(mc))


def days_until(target_iso: str | None) -> int | None:
    if not target_iso:
        return None
    try:
        d = datetime.strptime(target_iso, "%Y-%m-%d").date()
        return (d - date.today()).days
    except (ValueError, TypeError):
        return None


def insider_net_signal(insider_summary: dict) -> str | None:
    """Aggregate quarterly buckets to net signal.
    Returns 'buying' / 'selling' / 'neutral' / None."""
    qs = insider_summary.get("quarters") or []
    if not qs:
        return None
    buys = sells = 0
    for q in qs:
        # `acquiredCount` / `disposedCount` per quarter from FMP
        buys += q.get("acquiredTransactions") or q.get("acquired_count") or 0
        sells += q.get("disposedTransactions") or q.get("disposed_count") or 0
    if buys + sells == 0:
        return None
    if buys >= sells * 1.5:
        return "buying"
    if sells >= buys * 1.5:
        return "selling"
    return "neutral"


def enrich_one(ticker: str, *, force: bool = False) -> dict:
    """Enrich a single ticker. Caches per-day for cheap re-runs."""
    today = date.today().isoformat()
    cache_path = ENRICH_CACHE / f"{ticker}_{today}.json"

    if not force and cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < ENRICH_TTL_SEC:
            try:
                return json.load(open(cache_path))
            except Exception:
                pass

    profile = read_profile(ticker)
    earnings = read_earnings_cache(ticker)
    supp = read_supp_bundle(ticker)

    # ---- market cap tier
    mc = profile.get("marketCap")
    tier, mc_usd = classify_market_cap(mc)

    # ---- earnings landmine
    next_e_iso = earnings.get("next_earnings_est")
    next_e_src = earnings.get("next_earnings_source")
    days_e = days_until(next_e_iso)

    # ---- quality
    qs = supp.get("quality_scores") or {}
    altman = qs.get("altmanZScore")
    piotroski = qs.get("piotroskiScore")
    quality_red_flag = bool(
        (altman is not None and altman < 1.8) or
        (piotroski is not None and piotroski <= 2)
    )
    quality_premium = bool(
        (altman is not None and altman > 3.0) and
        (piotroski is not None and piotroski >= 7)
    )

    # ---- smart money
    insider_signal = insider_net_signal(supp.get("insider_summary") or {})
    inst = supp.get("institutional") or supp.get("institutional_qoq") or {}
    inst_delta = inst.get("ownership_pct_delta") or inst.get("investorHoldingChange")
    institutional_accumulation = bool(inst_delta is not None and inst_delta > 5.0)

    # ---- analyst (light fetch)
    pt = fetch_pt_consensus(ticker)
    grades = fetch_grades_recent(ticker)
    cur_price = profile.get("price")
    pt_target = pt.get("target")
    upside_pct = None
    if pt_target and cur_price and cur_price > 0:
        upside_pct = round((pt_target / cur_price - 1) * 100, 2)
    analyst_tailwind = bool(grades.get("upgrades", 0) > grades.get("downgrades", 0))

    # ---- composite enrichment multiplier (applied on top of base score)
    m = 1.0
    if days_e is not None:
        if 0 <= days_e <= 5:
            m *= 0.5
        elif days_e <= 10:
            m *= 0.8
    if quality_red_flag:
        m *= 0.6
    elif quality_premium:
        m *= 1.2
    if insider_signal == "buying":
        m *= 1.3
    elif insider_signal == "selling":
        m *= 0.85
    if institutional_accumulation:
        m *= 1.2
    if upside_pct is not None:
        # bounded ±30% adjustment, halved magnitude
        adj = max(-0.3, min(0.3, upside_pct / 200.0))  # /200 = /100/2
        m *= (1 + adj)
    if analyst_tailwind:
        m *= 1.15

    out = {
        "ticker": ticker,
        "as_of": today,
        "market_cap_tier": tier,
        "market_cap_usd": mc_usd,
        "earnings": {
            "next_date": next_e_iso,
            "source": next_e_src,
            "days_to_earnings": days_e,
            "within_5d": (days_e is not None and 0 <= days_e <= 5),
            "within_10d": (days_e is not None and 0 <= days_e <= 10),
        },
        "quality": {
            "altmanZScore": altman,
            "piotroskiScore": piotroski,
            "red_flag": quality_red_flag,
            "premium": quality_premium,
        },
        "smart_money": {
            "insider_signal": insider_signal,
            "institutional_accumulation": institutional_accumulation,
            "institutional_pct_delta": inst_delta,
        },
        "analyst": {
            "pt_target": pt_target,
            "current_price": cur_price,
            "upside_pct": upside_pct,
            "upgrades_30d": grades.get("upgrades", 0),
            "downgrades_30d": grades.get("downgrades", 0),
            "tailwind": analyst_tailwind,
        },
        "enrichment_multiplier": round(m, 4),
        "data_sources": {
            "profile_cache": bool(profile),
            "earnings_cache": bool(earnings),
            "supp_cache": bool(supp),
            "fmp_pt_fetched": bool(pt),
            "fmp_grades_fetched": bool(grades and grades.get("upgrades", 0) + grades.get("downgrades", 0) > 0),
        },
    }

    try:
        with open(cache_path, "w") as f:
            json.dump(out, f, indent=2)
    except Exception:
        pass

    return out


def enrich_movers(tickers: list[str], *, force: bool = False) -> dict:
    """Batch entry. Returns {ticker: enrichment_dict}."""
    out = {}
    for t in tickers:
        try:
            out[t] = enrich_one(t, force=force)
        except Exception as e:
            print(f"[enrich] WARN {t}: {e}", file=sys.stderr)
            out[t] = {"ticker": t, "error": str(e)[:200]}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tickers", nargs="+", type=str.upper)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    out = enrich_movers(args.tickers, force=args.force)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
