#!/usr/bin/env python3
"""
Intraday Evaluation Engine — the unified intraday data hub.

Design contract (per user spec 2026-07-01):
  ONE worker consolidates ALL intraday artifacts listed in
  docs/STOCK_DATA_FETCH_INVENTORY.md instead of each feature fetching on its
  own. `load_sources()` is the single consolidation point (reads the JSON that
  the existing daemons already produce — ZERO extra API calls), and `build()`
  is the single accessor every downstream consumer (the 盤中策略 page, any
  future feature) reads through.

Discipline:
  - `evaluate()` is 0-LLM, deterministic and golden-fixture tested. It turns the
    consolidated snapshot into a regime read + ranked sectors + stock ideas +
    STRATEGY CARDS (each with a stable `id` so streaks can be tracked).
  - Optional LLM narration is layered on in `build()` via narrate.py, and is
    best-effort (never blocks the deterministic payload).
  - Exploration layer ONLY. Does NOT feed investment_protocol decisions.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover - zoneinfo always present on 3.9+
    _ET = timezone(timedelta(hours=-4))

SCHEMA_VERSION = "1.0"

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
DASHBOARD_DIR = os.path.join(ROOT, "Dashboard")

# ── Sub-industry groups (heatmap only carries broad GICS sector; we need finer
#    granularity to see the semis↔software rotation that broad "Technology"
#    masks). Tunable in one place. ────────────────────────────────────────────
SEMI_TICKERS = {
    "NVDA", "AVGO", "AMD", "MU", "WDC", "STX", "SNDK", "KLAC", "LRCX", "AMAT",
    "TER", "ASML", "INTC", "MRVL", "COHR", "LITE", "GLW", "ONTO", "TSM", "QCOM",
    "TXN", "ADI", "MCHP", "NXPI", "ON", "SWKS", "MPWR", "ARM", "ALAB", "CRDO",
}
SOFTWARE_TICKERS = {
    "MSFT", "ORCL", "CRM", "NOW", "ADBE", "PLTR", "APP", "TTD", "TEAM", "SHOP",
    "WDAY", "SNOW", "DDOG", "NET", "PANW", "CRWD", "ZS", "FTNT", "INTU", "EPAM",
    "ADSK", "WDAY", "MDB", "HUBS", "DOCU", "OKTA", "SNPS", "CDNS",
}
CRYPTO_FINTECH = {
    "COIN", "HOOD", "MSTR", "SQ", "PYPL", "SOFI", "AFRM", "BLOCK", "GLXY",
}

# Files consolidated by the hub (all produced by existing daemons / daily jobs).
_SOURCE_FILES = {
    "intraday_mood": os.path.join(DASHBOARD_DIR, "intraday_mood.json"),
    "market_mood": os.path.join(DASHBOARD_DIR, "market_mood.json"),
    "heatmap": os.path.join(DASHBOARD_DIR, "heatmap.json"),
    "intraday_spikes": os.path.join(DASHBOARD_DIR, "intraday_spikes.json"),
    "retail_sector_pulse": os.path.join(DASHBOARD_DIR, "retail_sector_pulse.json"),
    "kill_triggers": os.path.join(DASHBOARD_DIR, "kill_triggers.json"),
}


# ─────────────────────────── helpers ────────────────────────────────────────
def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_atomic(path, payload):
    """Atomic JSON write (mirrors intraday.py._write_atomic convention)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _now_et():
    return datetime.now(_ET)


def _is_market_open(now_et=None):
    now_et = now_et or _now_et()
    if now_et.weekday() >= 5:
        return False
    open_t = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    close_t = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    return open_t <= now_et <= close_t


def _session_fraction(now_et=None):
    now_et = now_et or _now_et()
    open_t = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    total = 6.5 * 3600
    elapsed = (now_et - open_t).total_seconds()
    return round(max(0.0, min(1.0, elapsed / total)), 3)


def _heatmap_rows(heatmap):
    """Normalize heatmap into [(symbol, change_pct, sector)]."""
    if not heatmap:
        return []
    items = heatmap.get("tickers") or heatmap.get("stocks") or heatmap.get("data") or []
    if not items and isinstance(heatmap, dict):
        for v in heatmap.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                items = v
                break
    rows = []
    for x in items:
        if not isinstance(x, dict):
            continue
        sym = x.get("symbol") or x.get("ticker")
        chg = x.get("change_pct", x.get("changesPercentage", x.get("chg_pct")))
        if sym is None or chg is None:
            continue
        try:
            rows.append((str(sym).upper(), float(chg), x.get("sector")))
        except (TypeError, ValueError):
            continue
    return rows


def _group_stats(rows, universe):
    """Return {avg, up, down, n, worst:[...], best:[...]} for a ticker set."""
    sel = [(s, c) for (s, c, _sec) in rows if s in universe]
    if not sel:
        return {"avg": None, "up": 0, "down": 0, "n": 0, "best": [], "worst": []}
    chgs = [c for _s, c in sel]
    sel.sort(key=lambda r: r[1])
    return {
        "avg": round(sum(chgs) / len(chgs), 2),
        "up": sum(1 for c in chgs if c > 0),
        "down": sum(1 for c in chgs if c < 0),
        "n": len(chgs),
        "worst": [{"ticker": s, "chg": round(c, 2)} for s, c in sel[:6]],
        "best": [{"ticker": s, "chg": round(c, 2)} for s, c in sel[-6:][::-1]],
    }


# ─────────────────────────── consolidation ──────────────────────────────────
def load_sources():
    """THE single consolidation point. Reads every intraday artifact the hub
    represents. Returns dict keyed by source name (value None if missing)."""
    out = {}
    for key, path in _SOURCE_FILES.items():
        out[key] = _read_json(path)
    # today's thematic recommendations (date-stamped filename)
    today = _now_et().date().isoformat()
    out["thematic"] = _read_json(os.path.join(
        ROOT, "skills", "thematic-screener", "data", "recommendations", f"{today}.json"))
    # committee stance (light parse — optional)
    out["sector_stance"] = _read_sector_stance(today)
    return out


def _read_sector_stance(today):
    path = os.path.join(ROOT, "reports", f"{today}_sector_report.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            head = f.read(4000)
    except Exception:
        return None
    # strip markdown emphasis so "**Stance**: DEFENSIVE" matches
    flat = head.replace("*", "")
    stance = None
    for tok in ("DEFENSIVE", "OFFENSIVE", "NEUTRAL", "BALANCED"):
        if f"Stance: {tok}" in flat:
            stance = tok
            break
    return {"stance": stance} if stance else None


# ─────────────────────────── evaluation (0-LLM) ─────────────────────────────
def evaluate(sources, now_et=None):
    """Deterministic evaluation. Returns the structured payload WITHOUT streak
    info or narration (those are layered in build())."""
    now_et = now_et or _now_et()
    warnings = []

    mood = sources.get("intraday_mood") or {}
    mkt = sources.get("market_mood") or {}
    rows = _heatmap_rows(sources.get("heatmap"))
    pulse = sources.get("retail_sector_pulse") or {}
    spikes = sources.get("intraday_spikes") or {}
    thematic = sources.get("thematic") or {}
    stance = (sources.get("sector_stance") or {}).get("stance")

    # ── mood block ──
    agg = (mood.get("aggregate") or {})
    intraday_score = agg.get("score")
    by_sym = {t.get("symbol"): t for t in (mood.get("tickers") or [])}
    spy = by_sym.get("SPY") or {}
    qqq = by_sym.get("QQQ") or {}
    iwm = by_sym.get("IWM") or {}
    dist_days = spy.get("distribution_days")
    mood_block = {
        "intraday_score": intraday_score,
        "intraday_label": agg.get("risk_label"),
        "headline_zh": agg.get("headline_zh"),
        "mood_score": (mkt.get("mood") or {}).get("score"),
        "vix": (mkt.get("vix") or {}).get("current"),
        "vix_regime": (mkt.get("vix") or {}).get("regime"),
        "skew": (mkt.get("skew") or {}).get("current"),
        "skew_label": (mkt.get("skew") or {}).get("label"),
        "fear_greed": (mkt.get("fear_greed") or {}).get("index"),
        "fear_greed_label": (mkt.get("fear_greed") or {}).get("label"),
        "distribution_days": dist_days,
        "spy_chg": spy.get("intraday_return_prevclose_pct"),
        "qqq_chg": qqq.get("intraday_return_prevclose_pct"),
        "iwm_chg": iwm.get("intraday_return_prevclose_pct"),
        "open_pattern_zh": spy.get("open_pattern_zh"),
    }

    # ── breadth ──
    if rows:
        chgs = [c for _s, c, _sec in rows]
        adv = sum(1 for c in chgs if c > 0)
        dec = sum(1 for c in chgs if c < 0)
        breadth = {
            "n": len(chgs),
            "advancers": adv,
            "decliners": dec,
            "adv_pct": round(100 * adv / len(chgs), 1),
            "median_chg": round(sorted(chgs)[len(chgs) // 2], 2),
        }
    else:
        breadth = {"n": 0, "advancers": 0, "decliners": 0, "adv_pct": None, "median_chg": None}
        warnings.append("heatmap unavailable — breadth degraded")

    # ── sub-group rotation (semis vs software vs crypto) ──
    semis = _group_stats(rows, SEMI_TICKERS)
    software = _group_stats(rows, SOFTWARE_TICKERS)
    cryptofin = _group_stats(rows, CRYPTO_FINTECH)
    groups = {"semiconductors": semis, "software_platforms": software, "crypto_fintech": cryptofin}

    # ── sectors (fuse heatmap intraday breadth + retail pulse forward view) ──
    sectors = _rank_sectors(rows, pulse)

    # ── stock ideas (from live spikes trends + heatmap leaders) ──
    ideas = _stock_ideas(rows, spikes)

    # ── regime read ──
    regime = _regime(mood_block, breadth, stance)

    # ── STRATEGY CARDS (the recurrence-tracked core) ──
    strategies = _strategy_cards(
        regime, mood_block, breadth, groups, sectors, ideas, thematic, warnings)

    themes = _top_themes(thematic)

    return {
        "version": SCHEMA_VERSION,
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "as_of_et": now_et.isoformat(timespec="seconds"),
        "market_open": _is_market_open(now_et),
        "session_fraction": _session_fraction(now_et),
        "regime": regime,
        "mood": mood_block,
        "breadth": breadth,
        "groups": groups,
        "sectors": sectors,
        "rotation": _rotation_notes(groups, sectors),
        "themes": themes,
        "ideas": ideas,
        "strategies": strategies,
        "warnings": warnings,
        "_sources": {k: (v is not None) for k, v in sources.items()},
    }


def _regime(mood_block, breadth, stance):
    """Blend intraday tape score, breadth and committee stance into a posture."""
    score = mood_block.get("intraday_score")
    adv_pct = breadth.get("adv_pct")
    dist = mood_block.get("distribution_days") or 0
    drivers = []

    tape = 0
    if score is not None:
        tape = 1 if score >= 25 else (-1 if score <= -25 else 0)
        drivers.append(f"盤中分數 {score}（{mood_block.get('intraday_label') or '—'}）")
    if adv_pct is not None:
        drivers.append(f"市寬 {adv_pct}% 上漲")
        if adv_pct >= 60:
            tape += 1
        elif adv_pct <= 40:
            tape -= 1
    if dist and dist >= 5:
        drivers.append(f"近25日出貨日 {dist} 天")
        tape -= 1

    # committee stance is a strong prior toward caution
    forced_defensive = stance == "DEFENSIVE"
    if stance:
        drivers.append(f"委員會 stance {stance}")

    if forced_defensive or tape <= -1:
        label, posture, ceiling = "RISK-OFF 偏防禦", "defensive", "0-25%"
    elif tape >= 2:
        label, posture, ceiling = "RISK-ON 偏積極", "offensive", "60-75%"
    else:
        label, posture, ceiling = "中性/區間", "neutral", "40-60%"

    # SKEW / F&G caution overlay
    skew = mood_block.get("skew")
    fg = mood_block.get("fear_greed")
    cautions = []
    if skew and skew >= 145:
        cautions.append(f"SKEW {round(skew)} 機構買尾部避險")
    if fg is not None and fg <= 35:
        cautions.append(f"F&G {round(fg)} Fear")

    return {
        "label": label,
        "posture": posture,
        "exposure_ceiling": ceiling,
        "tape_bias": tape,
        "committee_stance": stance,
        "drivers": drivers,
        "cautions": cautions,
    }


def _rank_sectors(rows, pulse):
    """Per-sector intraday breadth from heatmap + forward 5d view from pulse."""
    # heatmap uses GICS-style long names; pulse uses underscore names — bridge.
    pulse_by = {}
    for s in (pulse.get("sectors") or []):
        pulse_by[_norm_sector(s.get("sector"))] = s

    agg = {}
    for sym, chg, sec in rows:
        if not sec:
            continue
        key = _norm_sector(sec)
        d = agg.setdefault(key, {"chgs": [], "up": 0, "down": 0})
        d["chgs"].append(chg)
        if chg > 0:
            d["up"] += 1
        elif chg < 0:
            d["down"] += 1

    out = []
    for key, d in agg.items():
        chgs = d["chgs"]
        avg = sum(chgs) / len(chgs)
        breadth_pct = round(100 * d["up"] / len(chgs), 1)
        p = pulse_by.get(key) or {}
        pred5d = p.get("predicted_5d_median_pct")
        comp_dir = p.get("composite_direction")
        # rank score: today's breadth + tilt from forward pulse
        rank = avg + (0.5 * (pred5d or 0))
        out.append({
            "sector": key,
            "intraday_avg": round(avg, 2),
            "breadth_pct": breadth_pct,
            "n": len(chgs),
            "pred5d": pred5d,
            "pulse_direction": comp_dir,
            "rank_score": round(rank, 2),
            "verdict": _sector_verdict(avg, breadth_pct, pred5d),
        })
    out.sort(key=lambda r: r["rank_score"], reverse=True)
    return out


def _sector_verdict(avg, breadth_pct, pred5d):
    if avg is not None and avg <= -1.5 and (breadth_pct or 0) < 40:
        return "AVOID"
    if (pred5d or 0) >= 1.5 and (breadth_pct or 0) >= 55:
        return "FAVOR"
    if avg is not None and avg >= 0.5:
        return "WARM"
    return "NEUTRAL"


def _norm_sector(name):
    if not name:
        return "Unknown"
    m = {
        "Financial Services": "Financials",
        "Consumer Cyclical": "Consumer_Discretionary",
        "Consumer Defensive": "Consumer_Staples",
        "Communication Services": "Communication",
        "Basic Materials": "Materials",
        "Real Estate": "Real_Estate",
    }
    return m.get(name, name.replace(" ", "_"))


def _stock_ideas(rows, spikes):
    """Top actionable single-stock reads: live trend-continuation + heatmap leaders."""
    ideas = []
    seen = set()
    chg_map = {s: c for (s, c, _sec) in rows}
    sec_map = {s: sec for (s, _c, sec) in rows}

    def _enrich(sym):
        return (round(chg_map[sym], 2) if sym in chg_map else None,
                sec_map.get(sym))

    # 1) live 順勢續攻 from spikes watchlist (strongest technical signal)
    for x in (spikes.get("trends") or []):
        sym = (x.get("symbol") or "").upper()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        chg, sec = _enrich(sym)
        ideas.append({
            "ticker": sym, "chg": chg, "sector": sec,
            "tag": "trend", "dir": x.get("direction"),
            "reason": x.get("dir_zh") or "順勢", "strength": x.get("strength"),
        })
    # 2) fresh reversals with alert
    for x in (spikes.get("reversals") or []):
        sym = (x.get("symbol") or "").upper()
        if not sym or sym in seen or not x.get("alert"):
            continue
        seen.add(sym)
        chg, sec = _enrich(sym)
        ideas.append({
            "ticker": sym, "chg": chg, "sector": sec,
            "tag": "reversal", "dir": x.get("direction"),
            "reason": x.get("dir_zh") or "反轉", "strength": x.get("strength"),
        })
    # 3) heatmap breadth leaders (top gainers) not already captured
    rows_sorted = sorted(rows, key=lambda r: r[1], reverse=True)
    for sym, chg, sec in rows_sorted[:8]:
        if sym in seen:
            # enrich the existing idea with chg/sector
            for it in ideas:
                if it["ticker"] == sym:
                    it["chg"], it["sector"] = round(chg, 2), sec
            continue
        seen.add(sym)
        ideas.append({
            "ticker": sym, "chg": round(chg, 2), "sector": sec,
            "tag": "leader", "dir": "up", "reason": "盤中漲幅領先", "strength": None,
        })
    return ideas[:12]


def _rotation_notes(groups, sectors):
    notes = []
    semis = groups["semiconductors"]
    sw = groups["software_platforms"]
    if semis["avg"] is not None and sw["avg"] is not None:
        if semis["avg"] <= -2 and sw["avg"] >= 1:
            notes.append({
                "from": "半導體", "to": "軟體/平台",
                "note": f"半導體均 {semis['avg']}% vs 軟體 {sw['avg']}%：科技股內部輪動",
            })
    # value/defensive rotation
    favor = [s["sector"] for s in sectors if s["verdict"] in ("FAVOR", "WARM")
             and s["sector"] in ("Industrials", "Financials", "Healthcare", "Materials")]
    if favor:
        notes.append({"from": "高估值成長", "to": "／".join(favor),
                      "note": "資金流向價值/防禦板塊"})
    return notes


def _top_themes(thematic):
    out = []
    for t in (thematic.get("themes") or [])[:6]:
        out.append({
            "name": t.get("theme") or t.get("name"),
            "direction": t.get("direction") or t.get("sentiment"),
            "lifecycle": t.get("lifecycle_stage") or t.get("lifecycle"),
            "heat": t.get("heat") or t.get("temperature"),
        })
    return out


# ── strategy card rules ──────────────────────────────────────────────────────
# Each card has a STABLE id so history.py can detect recurrence across windows.
def _strategy_cards(regime, mood, breadth, groups, sectors, ideas, thematic, warnings):
    cards = []

    def add(cid, title, stance, conf, rationale, tickers=None, evidence=None):
        cards.append({
            "id": cid, "title": title, "stance": stance,
            "confidence": round(conf, 2),
            "rationale": rationale,
            "tickers": tickers or [],
            "evidence": evidence or [],
        })

    semis = groups["semiconductors"]
    sw = groups["software_platforms"]
    cf = groups["crypto_fintech"]

    # 1) defensive / cash discipline
    if regime["posture"] == "defensive":
        ev = list(regime["drivers"]) + list(regime["cautions"])
        add("defensive_cash", "控曝險、守成為主", "defensive", 0.7,
            f"防禦環境（曝險上限 {regime['exposure_ceiling']}）：反彈未確認、市寬/出貨日偏弱，不追高。",
            evidence=ev[:4])

    # 2) semiconductor de-risk (falling knife)
    if semis["avg"] is not None and semis["avg"] <= -2 and semis["down"] >= semis["up"]:
        add("semis_derisk", "半導體全鏈回檔，不接刀", "avoid", 0.75,
            f"半導體族群均跌 {semis['avg']}%（{semis['down']}/{semis['n']} 下跌），"
            f"記憶體/設備同步走弱，等同一日收紅再談回補。",
            tickers=[w["ticker"] for w in semis["worst"][:5]],
            evidence=[f"最弱：{w['ticker']} {w['chg']}%" for w in semis["worst"][:3]])

    # 3) software/platform momentum
    if sw["avg"] is not None and sw["avg"] >= 1 and sw["up"] > sw["down"]:
        add("software_momentum", "軟體/平台順勢", "favor", 0.6,
            f"軟體/平台族群均漲 {sw['avg']}%，資金自硬體換手至軟體；強勢股回踩不追高。",
            tickers=[b["ticker"] for b in sw["best"][:5]],
            evidence=[f"領漲：{b['ticker']} +{b['chg']}%" for b in sw["best"][:3]])

    # 4) crypto/fintech risk appetite
    if cf["avg"] is not None and cf["avg"] >= 2 and cf["up"] >= cf["down"]:
        add("crypto_fintech_riskon", "加密/fintech 風險偏好升溫", "favor", 0.5,
            f"加密-fintech 族群均漲 {cf['avg']}%，高 beta 風險偏好回補；事件前控部位。",
            tickers=[b["ticker"] for b in cf["best"][:4]])

    # 5) semis→software rotation
    if semis["avg"] is not None and sw["avg"] is not None and semis["avg"] <= -2 and sw["avg"] >= 1:
        add("semis_to_software_rotation", "科技股內部輪動：半導體→軟體", "rotation", 0.65,
            f"半導體 {semis['avg']}% vs 軟體 {sw['avg']}%，指數被軟體撐住、市寬集中。")

    # 6) value/defensive rotation
    favor_val = [s for s in sectors if s["verdict"] in ("FAVOR", "WARM")
                 and s["sector"] in ("Industrials", "Financials", "Healthcare", "Materials")]
    if favor_val:
        names = "／".join(s["sector"] for s in favor_val[:3])
        add("value_defensive_rotation", f"資金輪動至 {names}", "favor", 0.55,
            f"價值/防禦板塊今日領先且前瞻偏多（{names}）；反彈確認後優先佈局。",
            tickers=[s["sector"] for s in favor_val[:3]])

    # 7) small-cap risk-on
    spy_c, qqq_c, iwm_c = mood.get("spy_chg"), mood.get("qqq_chg"), mood.get("iwm_chg")
    if all(v is not None for v in (spy_c, qqq_c, iwm_c)) and iwm_c > spy_c > qqq_c:
        add("smallcap_riskon", "小型股領漲、風險偏好回補", "favor", 0.45,
            f"IWM {iwm_c}% > SPY {spy_c}% > QQQ {qqq_c}%，低開高走買盤回補，但 QQQ 落後顯示壓力在 mega-tech。")

    # 8) avoid persistent laggards
    avoid = [s["sector"] for s in sectors if s["verdict"] == "AVOID"]
    if avoid:
        add("avoid_laggards", f"迴避弱勢板塊：{'／'.join(avoid[:3])}", "avoid", 0.5,
            f"{'／'.join(avoid[:3])} 今日最弱且前瞻偏空，低曝險環境不參與。",
            tickers=avoid[:3])

    # 9) event-risk guard (heuristic — presence of high distribution + defensive)
    if (mood.get("distribution_days") or 0) >= 6 and regime["posture"] != "offensive":
        add("event_risk_guard", "二元事件前控部位", "defensive", 0.5,
            "出貨日堆疊 + 機構買尾部避險，重大數據/財報前先降槓桿、留現金彈性。",
            evidence=regime["cautions"][:2])

    cards.sort(key=lambda c: c["confidence"], reverse=True)
    return cards


# ─────────────────────────── public build() ─────────────────────────────────
def build(with_narration=True):
    """Full hub build: consolidate → evaluate → attach streaks → narrate.
    Returns the payload dict (also what gets written to intraday_eval.json)."""
    sources = load_sources()
    payload = evaluate(sources)

    # attach recurrence (streak + day count) — import here to avoid cycle
    try:
        from . import history as _hist
    except ImportError:  # running as a loose script
        import history as _hist  # type: ignore
    payload = _hist.annotate_and_record(payload)

    if with_narration:
        try:
            from . import narrate as _narr
        except ImportError:
            import narrate as _narr  # type: ignore
        try:
            payload["narrative_zh"] = _narr.narrate(payload)
        except Exception as e:
            payload["narrative_zh"] = _fallback_narrative(payload)
            payload.setdefault("warnings", []).append(f"narration failed: {str(e)[:120]}")
    else:
        payload["narrative_zh"] = _fallback_narrative(payload)

    return payload


def _fallback_narrative(payload):
    r = payload.get("regime", {})
    tops = payload.get("strategies", [])[:2]
    bits = [f"{r.get('label', '—')}（曝險上限 {r.get('exposure_ceiling', '—')}）。"]
    for c in tops:
        bits.append(f"{c['title']}。")
    return "".join(bits)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Intraday Evaluation hub")
    ap.add_argument("--output", default=os.path.join(DASHBOARD_DIR, "intraday_eval.json"))
    ap.add_argument("--no-llm", action="store_true", help="skip LLM narration")
    ap.add_argument("--json-only", action="store_true", help="print payload, don't write")
    args = ap.parse_args()
    data = build(with_narration=not args.no_llm)
    if args.json_only:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        _write_atomic(args.output, data)
        s = data.get("strategies", [])
        print(f"[intraday_eval] wrote {args.output} · regime={data['regime']['label']} "
              f"· {len(s)} strategies · market_open={data['market_open']}")
