import json
import math
import os
import glob
import re
import requests
from datetime import datetime, date, timedelta, timezone


def _safe_float(v):
    """Parse v as float; return None for empty, 'nan', or NaN floats.
    Browsers' JSON.parse strictly rejects NaN tokens, so we must sanitize."""
    if v in (None, '', 'nan', 'NaN', 'None'):
        return None
    try:
        x = float(v)
        return None if math.isnan(x) or math.isinf(x) else x
    except (TypeError, ValueError):
        return None


def _clean_nan(obj):
    """Recursively replace NaN/Infinity floats with None. Prevents invalid JSON."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_nan(v) for v in obj]
    return obj

FMP_API_KEY = os.getenv("FMP_API_KEY")

# Paths
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
SECTOR_LOGS   = os.path.join(BASE_DIR, 'sector', 'sector_logs')
BREADTH_CACHE     = os.path.join(BASE_DIR, 'sector', 'breadth_cache')
FTD_CACHE         = os.path.join(BASE_DIR, 'sector', 'ftd_cache')
MARKET_TOP_CACHE  = os.path.join(BASE_DIR, 'sector', 'market_top_cache')
INVEST_LOGS   = os.path.join(BASE_DIR, 'investment', 'invest_logs')
NEWS_LOGS     = os.path.join(BASE_DIR, 'news', 'news_logs')
REPORTS_DIR   = os.path.join(BASE_DIR, 'reports')
POSITIONS_FILE = os.path.join(BASE_DIR, 'positions.json')
MOMENTUM_CACHE = os.path.join(BASE_DIR, 'skills', 'momentum-monitor', 'cache')
MOMENTUM_JOURNAL = os.path.join(BASE_DIR, 'skills', 'momentum-monitor', 'journal')
OUTPUT_FILE   = os.path.join(BASE_DIR, 'Dashboard', 'data.json')


def load_positions_by_ticker():
    """Load positions.json and group by ticker. Fetch current price once per ticker."""
    if not os.path.exists(POSITIONS_FILE):
        return {}, []
    try:
        with open(POSITIONS_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[WARN] positions.json: {e}")
        return {}, []

    all_positions = data.get('positions', [])
    by_ticker = {}
    # Group active (non-closed) lots for live overlay; closed lots stay in all_positions
    for p in all_positions:
        # Normalize realized_pl display fields for closed/trimmed lots
        if p.get('exit_price') is not None and p.get('closed_shares') is not None:
            p['realized_pl'] = round(
                (float(p['exit_price']) - float(p['entry_price'])) * float(p['closed_shares']), 2
            )
            p['realized_pct'] = round(
                (float(p['exit_price']) / float(p['entry_price']) - 1) * 100, 2
            )
        if p.get('status') == 'closed':
            continue
        by_ticker.setdefault(p['ticker'], []).append(p)

    # Fetch current prices (yfinance, single call per ticker)
    try:
        import yfinance as yf
        for tk, plist in by_ticker.items():
            try:
                info = yf.Ticker(tk).fast_info
                curr = info.last_price if hasattr(info, 'last_price') else None
                for p in plist:
                    if curr:
                        p['current_price'] = round(curr, 2)
                        p['unrealized_pl'] = round((curr - p['entry_price']) * p['shares'], 2)
                        p['unrealized_pct'] = round((curr / p['entry_price'] - 1) * 100, 2)
            except Exception as e:
                print(f"[WARN] positions price {tk}: {e}")
    except ImportError:
        pass

    return by_ticker, all_positions


def get_latest_file(pattern):
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None


# Unified cache freshness rule: 3h of market-open time elapsed since mtime.
# Market-open = Mon-Fri 9:30-16:00 ET. Weekend / pre-post market minutes don't
# count — a Saturday scan stays FRESH until Monday's market open, since no
# price data changes over the weekend.
CACHE_TTL_SEC = 10800  # 3h of market-open minutes

try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except ImportError:
    _ET = timezone(timedelta(hours=-4))  # fallback: EDT (off by 1h in winter)

def _market_minutes_between(t_start, t_end):
    """Minutes of US equity regular session (Mon-Fri 9:30-16:00 ET) elapsed.
    Holidays ignored — a Mon-holiday weekend stays FRESH slightly longer than strict."""
    if t_end <= t_start:
        return 0
    start = datetime.fromtimestamp(t_start, tz=_ET)
    end   = datetime.fromtimestamp(t_end,   tz=_ET)
    total = 0.0
    cursor = start
    while cursor < end:
        if cursor.weekday() < 5:
            day_open  = cursor.replace(hour=9,  minute=30, second=0, microsecond=0)
            day_close = cursor.replace(hour=16, minute=0,  second=0, microsecond=0)
            ws = max(cursor, day_open)
            we = min(end,    day_close)
            if we > ws:
                total += (we - ws).total_seconds() / 60
        cursor = (cursor + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int(total)

def _is_fresh(path, ttl_sec=CACHE_TTL_SEC):
    """True when market-open minutes since mtime < ttl_sec."""
    try:
        mtime = os.path.getmtime(path)
        return _market_minutes_between(mtime, datetime.now().timestamp()) * 60 < ttl_sec
    except OSError:
        return False

def _freshness_label(path):
    """Human-readable '(FRESH, 45m)' or '(STALE, 5h)' for log output.
    Verdict uses market-open minutes; age label uses wall-clock for readability."""
    try:
        mtime = os.path.getmtime(path)
        age_sec = datetime.now().timestamp() - mtime
        if age_sec < 60:
            age_str = f"{int(age_sec)}s"
        elif age_sec < 3600:
            age_str = f"{int(age_sec // 60)}m"
        else:
            age_str = f"{age_sec / 3600:.1f}h"
        market_min = _market_minutes_between(mtime, datetime.now().timestamp())
        state = "FRESH" if market_min * 60 < CACHE_TTL_SEC else "STALE"
        return state, age_str
    except OSError:
        return "MISSING", "-"


# ─────────────────────────────────────────────
# MARKET BREADTH ANALYZER CACHE
# ─────────────────────────────────────────────

def load_breadth_cache():
    """Load newest market-breadth-analyzer output from breadth_cache/ (mtime-based).
    Returns parsed JSON dict, or None if no files at all."""
    latest = get_latest_file(os.path.join(BREADTH_CACHE, "market_breadth_*.json"))
    if not latest:
        return None
    try:
        with open(latest, 'r') as f:
            data = json.load(f)
        state, age = _freshness_label(latest)
        tag = "[OK]" if state == "FRESH" else "[STALE]"
        print(f"{tag} Breadth cache: {os.path.basename(latest)} ({state}, {age})")
        return data
    except Exception as e:
        print(f"[WARN] Breadth cache read error: {e}")
        return None


def extract_breadth_from_analyzer(raw):
    """Map market-breadth-analyzer JSON → data.breadth{} with full 6-component data."""
    comp   = raw.get("composite", {})
    comps  = raw.get("components", {})
    trend  = raw.get("trend_summary", {})
    meta   = raw.get("metadata", {})
    fresh  = meta.get("data_freshness", {})
    c_scores = comp.get("component_scores", {})

    # ── cycle_phase from cycle_position signal ──
    cyc_signal = comps.get("cycle_position", {}).get("signal", "")
    if "extreme_trough" in cyc_signal.lower() or ("TROUGH" in cyc_signal and "PEAK" not in cyc_signal):
        cycle_phase = "Early"
    elif "PEAK" in cyc_signal and "recovery" in cyc_signal.lower():
        cycle_phase = "Mid"
    elif "PEAK" in cyc_signal:
        cycle_phase = "Late"
    else:
        cycle_phase = "Mid"

    # ── warning_flags from quantitative triggers ──
    warning_flags = []
    if comps.get("bearish_signal", {}).get("signal_active"):
        warning_flags.append("Bearish_Signal_Active")
    if comps.get("ma_crossover", {}).get("gap", 0) < 0:
        warning_flags.append("Below_200MA")
    if comps.get("historical_percentile", {}).get("percentile_rank", 50) < 30:
        warning_flags.append("Low_Historical_Percentile")
    if comps.get("divergence", {}).get("early_warning"):
        warning_flags.append("Early_Warning_Divergence")
    zone = comp.get("zone", "")
    if zone == "Critical":
        warning_flags.append("Critical_Zone")
    elif zone == "Weakening":
        warning_flags.append("Weakening_Zone")

    # ── backward-compat 4-field breadth_components ──
    components_compat = {
        "overall_breadth":      round(comp.get("composite_score", 0)),
        "sector_participation": c_scores.get("breadth_level_trend", {}).get("score", 0),
        "momentum":             c_scores.get("ma_crossover", {}).get("score", 0),
        "mean_reversion_risk":  100 - c_scores.get("cycle_position", {}).get("score", 100),
    }

    # ── full 6-component dict for breadth.html ──
    components_full = {
        k: {
            "score":  v.get("score"),
            "signal": comps.get(k, {}).get("signal", ""),
            "label":  v.get("label", k),
            "weight": round(v.get("effective_weight", 0) * 100),
        }
        for k, v in c_scores.items()
    }

    # ── regime_confidence from data quality ──
    dq_label = comp.get("data_quality", {}).get("label", "")
    if "Complete" in dq_label:
        regime_confidence = 0.9
    elif "Partial" in dq_label:
        regime_confidence = 0.7
    else:
        regime_confidence = 0.4

    return {
        "score":             comp.get("composite_score"),
        "zone":              zone,
        "zone_color":        comp.get("zone_color", "gray"),
        "exposure_ceiling":  comp.get("exposure_guidance", "60-75%"),
        "guidance":          comp.get("guidance", ""),
        "actions":           comp.get("actions", []),
        "components":        components_compat,
        "components_full":   components_full,
        "uptrend_ratio":     comps.get("breadth_level_trend", {}).get("current_8ma"),
        "current_8ma":       comps.get("breadth_level_trend", {}).get("current_8ma"),
        "current_200ma":     comps.get("breadth_level_trend", {}).get("current_200ma"),
        "cycle_phase":       cycle_phase,
        "warning_flags":     warning_flags,
        "regime_confidence": regime_confidence,
        "trend_direction":   trend.get("direction", "stable"),
        "trend_entries":     trend.get("entries", []),
        "data_quality":      dq_label,
        "key_levels":        raw.get("key_levels", {}),
        "data_date":         fresh.get("latest_date", ""),
        "days_old":          fresh.get("days_old"),
        "source":            "market-breadth-analyzer",
        "notes":             "",
    }


# ─────────────────────────────────────────────
# SECTOR / MARKET
# ─────────────────────────────────────────────

def extract_market_data(s_data):
    """Market regime + pulse from sector_intel.json"""
    phase0   = s_data.get("_phase0", {})
    phase3   = s_data.get("_phase3", {})
    political = phase3.get("political_overlay", {})
    summary  = s_data.get("summary", {})

    breadth = phase0.get("breadth_score")
    mult    = f"{0.60 + (breadth / 100) * 0.60:.2f}x" if breadth is not None else "--"

    return {
        "regime":           s_data.get("market_regime", "UNKNOWN"),
        "cycle_phase":      phase0.get("cycle_phase", "Unknown"),
        "regime_confidence": phase0.get("regime_confidence", 0),
        "fear_greed":       political.get("fear_greed_index", 50),
        "fear_greed_label": political.get("fear_greed_label", ""),
        "themes":           s_data.get("actionable_themes", []),
        "hot_sectors":      summary.get("hot_sectors", []),
        "warm_sectors":     summary.get("warm_sectors", []),
        "cold_sectors":     summary.get("cold_sectors", []),
        "avoid_sectors":    summary.get("avoid_sectors", []),
        "exposure_ceiling": phase0.get("exposure_ceiling", "100%"),
        "macro_multiplier": mult,
        "breadth_score":    breadth,
        "breadth_components": phase0.get("breadth_components", {}),
        "uptrend_ratio":    phase0.get("uptrend_ratio_overall"),
        "warning_flags":    phase0.get("warning_flags", []),
        "trump_signals":    political.get("trump_trade_signals", []),
        "named_targets":    political.get("named_targets_today", []),
        "top_catalysts":    _normalize_catalysts(phase3.get("top_catalysts", [])),
        "today_verdict":    (s_data.get("_phase4c") or {}).get("today_verdict"),
        "verdict_date":     s_data.get("verdict_date"),
        "generated_at":     s_data.get("generated_at"),
        "notes":            s_data.get("session_notes", ""),
    }


def _normalize_catalysts(items, limit=10):
    """Normalise _phase3.top_catalysts entries for the Dashboard catalyst feed.
    Keeps fields the sector page actually reads; trims to `limit`."""
    out = []
    for c in (items or [])[:limit]:
        event = c.get("event") or c.get("headline") or ""
        if not event:
            continue
        out.append({
            "event":            event,
            "type":             c.get("type", ""),
            "impact_score":     c.get("impact_score"),
            "direction":        (c.get("direction") or "").lower(),  # bullish|bearish|binary|neutral
            "affected_sectors": c.get("affected_sectors", []),
            "timing":           c.get("timing", ""),                 # past|upcoming|rolling
            "rank":             c.get("rank"),
        })
    return out


def extract_sectors(s_data):
    """Merge phase-4 verdicts with phase-1 rotation signals"""
    # Build lookup from _phase1 per sector name
    p1_map = {}
    for s in s_data.get("_phase1", {}).get("sectors", []):
        p1_map[s["name"]] = s

    result = []
    for s in s_data.get("sectors", []):
        name = s.get("name", "Unknown")
        p1   = p1_map.get(name, {})
        result.append({
            "name":             name,
            "verdict":          s.get("verdict", "COLD"),
            "score":            s.get("composite_score", 0),
            "score_components": s.get("score_components", {}),
            "proxy_etf":        s.get("proxy_etf", ""),
            "risk_flags":       s.get("risk_flags", []),
            "key_reason":       (s.get("key_reasons") or [""])[0],
            "key_reasons":      s.get("key_reasons") or [],
            "tail_risk_label":  s.get("tail_risk_label", "N/A"),
            "devils_advocate":  s.get("devils_advocate_note", ""),
            # Phase-1 additions
            "rotation_signal":  p1.get("rotation_signal", "NEUTRAL"),
            "uptrend_ratio":    p1.get("uptrend_ratio"),
            "overbought_risk":  p1.get("overbought_risk", ""),
            "ytd_perf_note":    p1.get("ytd_perf_note", ""),
        })
    return result


def extract_binary_risks(s_data):
    """Upcoming binary events with days-until countdown"""
    today = date.today()
    risks = []
    for ev in s_data.get("_phase3", {}).get("upcoming_binary_risks", []):
        ev_date_str = ev.get("date", "")
        days_until = None
        try:
            ev_date = datetime.strptime(ev_date_str, "%Y-%m-%d").date()
            days_until = (ev_date - today).days
        except Exception:
            pass
        # Skip past events — the list is titled "Upcoming Binary Risks",
        # and an expired event e.g. yesterday's ceasefire headline no longer
        # belongs. Events with unparseable dates are kept (days_until=None)
        # so data-quality problems stay visible.
        if days_until is not None and days_until < 0:
            continue
        # Recompute within_48h from days_until so the banner auto-ages each
        # bridge.py run instead of relying on the stale flag baked into
        # sector_intel.json at scan time.
        within_48h = days_until is not None and 0 <= days_until <= 2
        risks.append({
            "event":            ev.get("event", ""),
            "date":             ev_date_str,
            "days_until":       days_until,
            "affected_sectors": ev.get("affected_sectors", []),
            "within_48h":       within_48h,
        })
    # Sort by date ascending
    risks.sort(key=lambda x: x["date"])
    return risks


def extract_divergence_watch(s_data):
    return s_data.get("sector_divergence_watch", [])


# ─────────────────────────────────────────────
# AUDIT HISTORY + WATCHLIST
# ─────────────────────────────────────────────

def _find_report(ticker, date_clean):
    for pattern in [
        f"{date_clean}_{ticker}.md",
        f"{date_clean}_{ticker}.html",
        f"*_{ticker}.md",
        f"*_{ticker}.html",
    ]:
        matches = glob.glob(os.path.join(REPORTS_DIR, pattern))
        if matches:
            return os.path.join('reports', os.path.basename(matches[0]))
    return None


def _batch_current_prices(tickers):
    """yfinance batch price fetch for a list of tickers. Returns {ticker: price or None}.
    Graceful degradation — rate limit / network errors leave entries as None so the
    frontend can still render the card without a live price."""
    result = {t: None for t in tickers if t and t != "UNKNOWN"}
    if not result:
        return result
    try:
        import yfinance as yf
        # fast_info per ticker is cheap; batch via list comprehension (yf caches inside session)
        for t in list(result.keys()):
            try:
                info = yf.Ticker(t).fast_info
                p = info.last_price if hasattr(info, 'last_price') else None
                if p is not None:
                    result[t] = round(float(p), 2)
            except Exception:
                pass
    except ImportError:
        pass
    return result


def extract_audit_history(positions_by_ticker=None):
    """Build recent_analysis[] with full watchlist metadata + live current_price"""
    positions_by_ticker = positions_by_ticker or {}
    audit_map = {}
    audits    = []

    history_file = os.path.join(INVEST_LOGS, 'history.json')
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                history_data = json.load(f)

            # Batch-fetch live prices for all tickers in history (one yfinance round).
            # Reuses positions_by_ticker price when available to avoid double-fetch.
            all_tickers = {item.get("ticker") for item in history_data if item.get("ticker")}
            cached = {t: (positions_by_ticker.get(t, [{}])[0] or {}).get('current_price')
                      for t in all_tickers if positions_by_ticker.get(t)}
            to_fetch = [t for t in all_tickers if cached.get(t) is None]
            fresh = _batch_current_prices(to_fetch)
            live_prices = {**fresh, **{t: p for t, p in cached.items() if p is not None}}

            # Process all history entries (was [-10:], caused older cards to fall
            # through to the ARCHIVE fallback and lose all metadata).
            for item in reversed(history_data):
                ticker    = item.get("ticker", "UNKNOWN")
                date_raw  = item.get("date") or item.get("export_date", "Unknown")
                date_clean = date_raw.replace("-", "")
                # V4.6 canonical source = trades_this_session[0]; legacy `metadata` block
                # (pre-V4.6 duplication) layered underneath so older entries still resolve.
                trade0    = (item.get("trades_this_session") or [{}])[0] or {}
                legacy    = item.get("metadata") or {}
                meta      = {**legacy, **trade0}

                report_path = _find_report(ticker, date_clean)
                # V4.6: final_action ∈ {EXECUTE, STAGED, CANCEL}; prefer final_decision for detail
                decision         = item.get("final_action") or meta.get("final_action") or "HOLD"
                final_decision   = meta.get("final_decision") or item.get("final_decision")  # BUY/STAGED_ENTRY/HOLD/SELL
                # Score extraction — handle legacy shapes: item.final_score, meta.final_score, or both
                raw_score = meta.get("final_score")
                if raw_score is None:
                    raw_score = item.get("final_score", 0.0)
                score = raw_score if raw_score is not None else 0.0

                # V4.6 dual-track entry ranges
                entry_aggr  = meta.get("entry_aggressive")     # [min, max] or None
                entry_cons  = meta.get("entry_conservative")   # [min, max] or None

                # Price targets
                tp    = meta.get("take_profit") or item.get("take_profit")
                sl    = meta.get("stop_loss") or item.get("stop_loss")
                watch = meta.get("watch_price") or meta.get("trigger_price")
                # Legacy fallback: old single entry_range / entry_price
                entry = entry_aggr or meta.get("entry_range") or meta.get("entry_price")

                if not entry and not watch:
                    ctx = meta.get("macro_context", "")
                    pm  = re.findall(r"\$(\d+[\-\d]*)", ctx)
                    if pm:
                        entry = pm[-1]

                def _range_str(rng):
                    if isinstance(rng, list):
                        return " - ".join(str(e) for e in rng)
                    return rng

                entry_display = _range_str(entry)
                entry_aggr_display = _range_str(entry_aggr)
                entry_cons_display = _range_str(entry_cons)

                # Backtest P/L — prefer aggressive[0], fall back to legacy entry_range
                perf = None
                backtest_entry = entry_aggr if isinstance(entry_aggr, list) else meta.get("entry_range")
                if FMP_API_KEY and isinstance(backtest_entry, list) and backtest_entry:
                    try:
                        res = requests.get(
                            f"https://financialmodelingprep.com/api/v3/quote/{ticker}"
                            f"?apikey={FMP_API_KEY}", timeout=5
                        ).json()
                        if res:
                            curr  = res[0].get("price")
                            ep    = float(str(backtest_entry[0]).replace("$", ""))
                            chg   = ((curr - ep) / ep) * 100
                            perf  = {"current": curr, "entry": ep, "change": round(chg, 2)}
                    except Exception as e:
                        print(f"[WARN] Backtest {ticker}: {e}")

                # ── Watchlist metadata ──────────────────────────────
                watch_conditions     = meta.get("watch_conditions")
                key_risks            = meta.get("key_risks", [])
                rr_ratio             = meta.get("risk_reward_ratio")
                position_pct         = meta.get("position_size_pct")
                avg_conf             = meta.get("avg_confidence")
                time_horizon         = meta.get("time_horizon")
                da_filed             = meta.get("devils_advocate_filed", False)
                # V4.6 additions
                consensus_bonus      = meta.get("consensus_bonus_applied", False)
                macro_alignment      = meta.get("macro_alignment")          # ALIGNED | CONTRARIAN
                staged_split         = meta.get("staged_split")             # {aggressive_pct, conservative_pct}
                binary_class         = meta.get("binary_classification")    # positive|unknown|negative|none

                # Join active positions (open) for this ticker
                active_positions = positions_by_ticker.get(ticker, [])
                has_live_position = len(active_positions) > 0
                position_summary = None
                if has_live_position:
                    total_shares = sum(p['shares'] for p in active_positions)
                    total_cost   = sum(p['cost_basis'] for p in active_positions)
                    avg_cost     = total_cost / total_shares if total_shares else 0
                    curr_px      = active_positions[0].get('current_price')
                    upl_pct      = ((curr_px / avg_cost - 1) * 100) if (curr_px and avg_cost) else None
                    position_summary = {
                        "total_shares": round(total_shares, 2),
                        "avg_cost":     round(avg_cost, 2),
                        "total_cost":   round(total_cost, 2),
                        "current_price": curr_px,
                        "unrealized_pct": round(upl_pct, 2) if upl_pct is not None else None,
                        "unrealized_pl": round((curr_px - avg_cost) * total_shares, 2) if curr_px else None,
                        "lots": len(active_positions),
                    }

                # Determine if this ticker belongs on watchlist
                # V4.6: STAGED and STAGED_ENTRY are active staged entries; active position forces inclusion
                on_watchlist = (
                    decision in ("EXECUTE", "STAGED") or
                    final_decision in ("BUY", "STAGED_ENTRY") or
                    bool(watch_conditions) or
                    bool(watch) or
                    has_live_position
                )

                audits.append({
                    "ticker":           ticker,
                    "decision":         decision,
                    "final_decision":   final_decision,
                    "score":            round(float(score), 2) if score is not None else 0.0,
                    "time":             date_raw,
                    "report_url":       report_path,
                    "performance":      perf,
                    "targets":          {
                        "tp": tp, "sl": sl, "watch": watch,
                        "entry": entry_display,
                        "entry_aggressive":   entry_aggr_display,
                        "entry_conservative": entry_cons_display,
                    },
                    # Watchlist fields
                    "on_watchlist":     on_watchlist,
                    "watch_conditions": watch_conditions,
                    "key_risks":        key_risks,
                    "rr_ratio":         rr_ratio,
                    "position_pct":     position_pct,
                    "avg_confidence":   avg_conf,
                    "time_horizon":     time_horizon,
                    "da_filed":         da_filed,
                    # V4.6 fields
                    "consensus_bonus":  consensus_bonus,
                    "macro_alignment":  macro_alignment,
                    "staged_split":     staged_split,
                    "binary_class":     binary_class,
                    # Price fields (current = yfinance live; analysis = snapshot at decision time)
                    "current_price":    live_prices.get(ticker),
                    "analysis_price":   meta.get("analysis_price"),
                    # Live position overlay (positions.json)
                    "live_position":    position_summary,
                    "position_lots":    active_positions,
                })
                audit_map[ticker] = True

        except Exception as e:
            print(f"[ERROR] history.json: {e}")

    # Fallback: scan reports/ for unlisted tickers
    try:
        for rep in sorted(glob.glob(os.path.join(REPORTS_DIR, "*_*.*")), reverse=True):
            fname  = os.path.basename(rep)
            parts  = fname.split("_")
            if len(parts) >= 2:
                t_part = parts[1].split(".")[0]
                if t_part not in audit_map and len(t_part) <= 6 and t_part.isupper():
                    d_part   = parts[0]
                    date_fmt = f"{d_part[:4]}-{d_part[4:6]}-{d_part[6:8]}" if len(d_part) == 8 else d_part
                    audits.append({
                        "ticker":       t_part,
                        "decision":     "ARCHIVE",
                        "score":        0.0,
                        "time":         date_fmt,
                        "report_url":   os.path.join('reports', fname),
                        "on_watchlist": False,
                        "key_risks":    [],
                    })
                    audit_map[t_part] = True
    except Exception as e:
        print(f"[ERROR] Scanning reports/: {e}")

    return audits


# ─────────────────────────────────────────────
# FTD DETECTOR CACHE
# ─────────────────────────────────────────────

def load_ftd_cache():
    """Load most recent ftd_detector_*.json from ftd_cache/. Returns None if not found."""
    latest = get_latest_file(os.path.join(FTD_CACHE, "ftd_detector_*.json"))
    if not latest:
        return None
    try:
        with open(latest, 'r') as f:
            data = json.load(f)
        state, age = _freshness_label(latest)
        tag = "[OK]" if state == "FRESH" else "[STALE]"
        print(f"{tag} FTD cache: {os.path.basename(latest)} ({state}, {age})")
        return data
    except Exception as e:
        print(f"[WARN] FTD cache read error: {e}")
        return None


def extract_ftd_data(raw):
    """Map ftd_detector JSON → data.ftd{}"""
    ms      = raw.get("market_state", {})
    sp      = raw.get("sp500", {})
    nq      = raw.get("nasdaq", {})
    quality = raw.get("quality_score", {})
    dist    = raw.get("post_ftd_distribution", {})
    inv     = raw.get("ftd_invalidation", {})
    pt      = raw.get("power_trend", {})
    meta    = raw.get("metadata", {})
    prices  = meta.get("index_prices", {})

    state = ms.get("combined_state", "NO_SIGNAL")

    # FTD details (from whichever index confirmed first)
    sp_ftd = sp.get("ftd") or {}
    nq_ftd = nq.get("ftd") or {}
    ftd    = sp_ftd if sp_ftd.get("ftd_detected") else nq_ftd

    sp_swing = sp.get("swing_low") or {}
    sp_rally = sp.get("rally_attempt") or {}

    return {
        "state":              state,
        "dual_confirmation":  ms.get("dual_confirmation", False),
        "quality_score":      quality.get("total_score", 0),
        "signal":             quality.get("signal", ""),
        "guidance":           quality.get("guidance", ""),
        "exposure_range":     quality.get("exposure_range", ""),
        # FTD event details
        "ftd_detected":       ftd.get("ftd_detected", False),
        "ftd_date":           ftd.get("ftd_date"),
        "ftd_day_number":     ftd.get("ftd_day_number"),
        "ftd_gain_pct":       ftd.get("gain_pct"),
        # Swing low
        "swing_low_date":     sp_swing.get("swing_low_date"),
        "swing_low_price":    sp_swing.get("swing_low_price"),
        "decline_pct":        sp_swing.get("decline_pct"),
        # Rally attempt
        "rally_day1_date":    sp_rally.get("day1_date"),
        "rally_day_count":    sp_rally.get("current_day_count"),
        # Post-FTD health
        "distribution_days":  dist.get("distribution_count", 0),
        "days_monitored":     dist.get("days_monitored", 0),
        "power_trend":        pt.get("power_trend", False),
        "power_trend_cond":   pt.get("conditions_met", 0),
        "invalidated":        inv.get("invalidated", False),
        "invalidation_date":  inv.get("invalidation_date"),
        # Current prices
        "sp500_price":        prices.get("sp500"),
        "qqq_price":          prices.get("qqq"),
        "generated_at":       meta.get("generated_at", ""),
    }


# ─────────────────────────────────────────────
# MARKET TOP DETECTOR CACHE
# ─────────────────────────────────────────────

def load_market_top_cache():
    """Load most recent market_top_*.json from market_top_cache/. Returns None if not found."""
    latest = get_latest_file(os.path.join(MARKET_TOP_CACHE, "market_top_*.json"))
    if not latest:
        return None
    try:
        with open(latest, 'r') as f:
            data = json.load(f)
        state, age = _freshness_label(latest)
        tag = "[OK]" if state == "FRESH" else "[STALE]"
        print(f"{tag} Market Top cache: {os.path.basename(latest)} ({state}, {age})")
        return data
    except Exception as e:
        print(f"[WARN] Market Top cache read error: {e}")
        return None


def extract_market_top_data(raw):
    """Map market_top_detector JSON → data.market_top{}"""
    comp   = raw.get("composite", {})
    comps  = raw.get("components", {})
    ftd    = raw.get("follow_through_day", {})
    delta  = raw.get("delta", {})
    meta   = raw.get("metadata", {})
    idx    = meta.get("index_data", {})

    # 6-component breakdown
    comp_scores = comp.get("component_scores", {})
    components = {}
    for key, v in comp_scores.items():
        raw_comp = comps.get(key, {})
        components[key] = {
            "score":    v.get("score", 0),
            "label":    v.get("label", key),
            "signal":   raw_comp.get("signal", ""),
            "weight":   round(v.get("weight", 0) * 100),
            "weighted": v.get("weighted_contribution", 0),
        }

    return {
        "composite_score": comp.get("composite_score", 0),
        "zone":            comp.get("zone", ""),
        "zone_color":      comp.get("zone_color", "gray"),
        "risk_budget":     comp.get("risk_budget", ""),
        "guidance":        comp.get("guidance", ""),
        "actions":         comp.get("actions", []),
        "data_quality":    comp.get("data_quality", {}).get("label", ""),
        "strongest_warning": comp.get("strongest_warning", {}),
        "weakest_warning":   comp.get("weakest_warning", {}),
        "components":      components,
        # Follow-Through Day from market-top scorer
        "ftd_applicable":  ftd.get("applicable", False),
        "ftd_detected":    ftd.get("ftd_detected", False),
        "ftd_reason":      ftd.get("reason", ""),
        "rally_day_count": ftd.get("rally_day_count"),
        # Delta vs previous run
        "delta_direction": delta.get("composite_direction", "first_run"),
        "delta_value":     delta.get("composite_delta", 0),
        # Index context
        "sp500_price":          idx.get("sp500_price"),
        "sp500_year_high":      idx.get("sp500_year_high"),
        "sp500_dist_from_high": idx.get("sp500_distance_from_high_pct"),
        "vix_level":            idx.get("vix_level"),
        "generated_at":         meta.get("generated_at", ""),
    }


# ─────────────────────────────────────────────
# NEWS
# ─────────────────────────────────────────────

def extract_news():
    news = []

    # 1. Read from news_logs (primary — news protocol output)
    # Supports both legacy format (verdict / net_impact_score / affected_sectors as list of dicts)
    # and 2026-04-15+ format (impact / score / affected_sectors as list of strings)
    news_dates_seen = set()
    for news_file in sorted(glob.glob(os.path.join(NEWS_LOGS, "*_digest.json")), reverse=True)[:3]:
        try:
            with open(news_file, 'r') as f:
                n_data = json.load(f)
            file_date = n_data.get("scan_date") or n_data.get("timestamp", "")[:10] or os.path.basename(news_file)[:10]
            news_dates_seen.add(file_date)
            for v in n_data.get("verdicts", []):
                # v2 protocol: skip shallow (Stage 1) items — they're preserved in
                # the final MD's Shallow Digest section but should not clutter Dashboard.
                # Missing depth field = legacy v1 item → treat as deep.
                if v.get("depth") == "shallow":
                    continue
                # Sectors: handle both [dict] and [str] shapes
                raw_sectors = v.get("affected_sectors", [])
                if raw_sectors and isinstance(raw_sectors[0], dict):
                    sector_names = [s.get("sector", "Unknown") for s in raw_sectors]
                else:
                    sector_names = [s if isinstance(s, str) else "Unknown" for s in raw_sectors]
                # Impact: prefer "impact" field, fall back to "verdict"
                impact_val = v.get("impact") or v.get("verdict") or "NEUTRAL"
                impact = impact_val.lower() if isinstance(impact_val, str) else "neutral"
                # Score: prefer "score", fall back to "net_impact_score"
                score_val = v.get("score") if v.get("score") is not None else v.get("net_impact_score")
                # news_type: v2 uses "news_type", v1 used "type"
                type_val = v.get("news_type") or v.get("type", "")
                news.append({
                    "headline":          v.get("headline"),
                    "headline_zh":       v.get("headline_zh", ""),
                    "impact":            impact,
                    "score":             score_val,
                    "date":              v.get("date") or file_date,
                    "sectors":           sector_names,
                    "source":            "news_protocol",
                    "source_label":      v.get("source_label", ""),
                    "type":              type_val,
                    "bull_case":         v.get("bull_case", ""),
                    "bear_case":         v.get("bear_case", ""),
                    # v2 new agents
                    "sector_view":       v.get("sector_view", ""),
                    "macro_view":        v.get("macro_view", ""),
                    "arbiter_reasoning": v.get("arbiter_reasoning", ""),
                    "debate_note":       v.get("debate_note", ""),
                    "binary_risk":       v.get("binary_risk", False),
                    "within_48h":        v.get("within_48h", False),
                    "tickers_mentioned": v.get("tickers_mentioned", []),
                    "depth":             v.get("depth", "deep"),
                    "review_status":     v.get("review_status", "reviewed"),
                })
        except Exception as e:
            print(f"[ERROR] News log {news_file}: {e}")

    # NOTE: Intentionally NOT supplementing from sector_intel here anymore.
    # Sector _phase3.top_catalysts render in sector page's catalyst-feed (via
    # market.top_catalysts). _phase3.upcoming_binary_risks render in sector page's
    # Binary Risk Alert (via data.binary_risks). The news page should only carry
    # AI-debated digest items with bull_case/bear_case/arbiter_reasoning/debate_note —
    # raw sector events don't have those fields and render as half-empty cards.

    # Deduplicate by headline, sort by date desc
    seen_headlines = set()
    deduped = []
    for item in sorted(news, key=lambda x: x.get("date", ""), reverse=True):
        h = (item.get("headline") or "").strip()
        if h and h not in seen_headlines:
            seen_headlines.add(h)
            deduped.append(item)

    return deduped


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def ingest_momentum_screen():
    """
    Read the latest momentum screen CSV + up to 30 days of history + journal stats.
    Returns dict for data.json.momentum_screen. Gracefully returns {"status":"no_data"}
    when nothing is available.
    """
    import csv as _csv

    out = {"status": "no_data"}
    if not os.path.isdir(MOMENTUM_CACHE):
        return out

    csv_files = sorted(glob.glob(os.path.join(MOMENTUM_CACHE, "screen_*.csv")),
                       key=os.path.getmtime)
    if not csv_files:
        return out

    # Prefer the latest "substantial" scan (≥ 50 rows) from the last 72h as the
    # Dashboard baseline. Tiny filtered snapshots (e.g. dev tests producing 5 rows)
    # shouldn't override a weekend's full-universe 500-ticker baseline.
    SUBSTANTIAL_ROWS = 50
    LOOKBACK_SEC    = 72 * 3600
    now_ts = datetime.now().timestamp()
    def _row_count(p):
        try:
            with open(p, "r", encoding="utf-8") as fp:
                return sum(1 for _ in fp) - 1  # minus header
        except Exception:
            return 0
    recent_substantial = [
        p for p in csv_files
        if (now_ts - os.path.getmtime(p)) < LOOKBACK_SEC
        and _row_count(p) >= SUBSTANTIAL_ROWS
    ]
    latest_csv = recent_substantial[-1] if recent_substantial else csv_files[-1]

    # If a newer (smaller) watchlist-only CSV exists after the base, merge its rows in.
    # This ensures watchlist rescans update tickers without replacing the full base.
    base_mtime = os.path.getmtime(latest_csv)
    newer_small = [
        p for p in csv_files
        if os.path.getmtime(p) > base_mtime and _row_count(p) < SUBSTANTIAL_ROWS
    ]

    def _parse_csv_rows(path):
        rows = []
        try:
            with open(path, "r", encoding="utf-8") as fp:
                reader = _csv.DictReader(fp)
                for row in reader:
                    rows.append(row)
        except Exception:
            pass
        return rows

    def _build_row(row):
        return {
            "rank":     int(row["rank"]) if row.get("rank") else None,
            "ticker":   row.get("ticker"),
            "in_sp500": row.get("in_sp500", "1") != "0",
            "sector":   row.get("sector") or "Unknown",
            "price":    _safe_float(row.get("price")),
            "score":    _safe_float(row.get("score")),
            "label":    row.get("label"),
            "stage":    row.get("stage"),
            "volume_today":   _safe_float(row.get("volume_today")),
            "avg_20d":        _safe_float(row.get("avg_20d")),
            "ratio_20d":      _safe_float(row.get("ratio_20d")),
            "spike_label":    row.get("spike_label"),
            "intraday_state": row.get("intraday_state"),
            "elapsed_min":    _safe_float(row.get("elapsed_min")),
            "ma_20":   _safe_float(row.get("ma_20")),
            "ma_50":   _safe_float(row.get("ma_50")),
            "ma_200":  _safe_float(row.get("ma_200")),
            "above_ma20_pct":  _safe_float(row.get("above_ma20_pct")),
            "above_ma50_pct":  _safe_float(row.get("above_ma50_pct")),
            "above_ma200_pct": _safe_float(row.get("above_ma200_pct")),
            "rsi_14":          _safe_float(row.get("rsi_14")),
            "rsi_zone":        row.get("rsi_zone"),
            "short_pct_float": _safe_float(row.get("short_pct_float")),
            "short_interpretation": row.get("short_interpretation"),
            "signals":  row.get("signals", "").split("|") if row.get("signals") else [],
            "warnings": row.get("warnings", "").split("|") if row.get("warnings") else [],
        }

    latest_rows = []
    try:
        with open(latest_csv, "r", encoding="utf-8") as fp:
            reader = _csv.DictReader(fp)
            for row in reader:
                latest_rows.append(_build_row(row))
    except Exception as e:
        print(f"[WARN] momentum CSV parse {latest_csv}: {e}")
        return out

    # Merge newer watchlist-only CSVs (< SUBSTANTIAL_ROWS) on top of the base.
    # Existing tickers get updated data; new tickers get appended.
    if newer_small:
        row_by_ticker = {r["ticker"]: r for r in latest_rows}
        for small_csv in newer_small:
            for raw in _parse_csv_rows(small_csv):
                tk = raw.get("ticker")
                if not tk:
                    continue
                row_by_ticker[tk] = _build_row(raw)
        latest_rows = list(row_by_ticker.values())
        # Use the newest small CSV's mtime for freshness display
        latest_csv = newer_small[-1]

    # Extract snap_id from filename
    snap_id = os.path.splitext(os.path.basename(latest_csv))[0]
    snap_date = None
    parts = snap_id.split("_")
    if len(parts) >= 2 and len(parts[1]) == 8:
        snap_date = f"{parts[1][:4]}-{parts[1][4:6]}-{parts[1][6:8]}"

    state, age = _freshness_label(latest_csv)
    mtime = datetime.fromtimestamp(os.path.getmtime(latest_csv)).strftime("%Y-%m-%d %H:%M")

    # Per-ticker score history from last ~30 days of CSVs (so UI can render a sparkline)
    history_by_ticker = {}
    for csv_path in csv_files[-30:]:
        fname = os.path.basename(csv_path)
        try:
            with open(csv_path, "r", encoding="utf-8") as fp:
                reader = _csv.DictReader(fp)
                for row in reader:
                    tk = row.get("ticker")
                    if not tk or not row.get("score"):
                        continue
                    history_by_ticker.setdefault(tk, []).append({
                        "snap_id": os.path.splitext(fname)[0],
                        "score":   _safe_float(row.get("score")),
                        "price":   _safe_float(row.get("price")),
                    })
        except Exception:
            continue

    # Journal stats (if available)
    stats = None
    stats_file = os.path.join(MOMENTUM_JOURNAL, "stats.json")
    journal_total = 0
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r", encoding="utf-8") as fp:
                stats = json.load(fp)
            journal_total = stats.get("total_entries", 0)
        except Exception as e:
            print(f"[WARN] momentum stats: {e}")

    out = {
        "status":       "success",
        "snap_id":      snap_id,
        "snap_date":    snap_date,
        "generated_at": mtime,
        "freshness":    state,
        "age_label":    age,
        "total_rows":   len(latest_rows),
        "rows":         latest_rows,
        "history_by_ticker": history_by_ticker,
        "journal": {
            "total_entries": journal_total,
            "stats":         stats,
        },
        "snapshot_count": len(csv_files),
    }
    return out


def run_bridge():
    data = {
        "status":          "success",
        "last_updated":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market":          {},
        "breadth":         {},
        "ftd":             {},
        "market_top":      {},
        "sectors":         [],
        "binary_risks":    [],
        "divergence_watch": [],
        "recent_analysis": [],
        "news":            [],
        "momentum_screen": {"status": "no_data"},
    }

    # 1. Sector / Market / Breadth (base from sector_intel)
    latest_sector = get_latest_file(os.path.join(SECTOR_LOGS, "*_sector_intel.json"))
    if latest_sector:
        try:
            with open(latest_sector, 'r') as f:
                s_data = json.load(f)
            data["market"]           = extract_market_data(s_data)
            data["sectors"]          = extract_sectors(s_data)
            data["binary_risks"]     = extract_binary_risks(s_data)
            data["divergence_watch"] = extract_divergence_watch(s_data)
            # breadth sub-object: start with sector_intel estimates
            data["breadth"] = {
                "score":             data["market"].get("breadth_score"),
                "components":        data["market"].get("breadth_components", {}),
                "uptrend_ratio":     data["market"].get("uptrend_ratio"),
                "warning_flags":     data["market"].get("warning_flags", []),
                "cycle_phase":       data["market"].get("cycle_phase"),
                "regime_confidence": data["market"].get("regime_confidence"),
                "exposure_ceiling":  data["market"].get("exposure_ceiling"),
                "notes":             s_data.get("_phase0", {}).get("notes", ""),
                "source":            "sector_intel",
            }
            state, age = _freshness_label(latest_sector)
            tag = "[OK]" if state == "FRESH" else "[STALE]"
            print(f"{tag} Sector: {os.path.basename(latest_sector)} ({state}, {age}) | "
                  f"{len(data['sectors'])} sectors | "
                  f"F&G={data['market']['fear_greed']} | "
                  f"binary_risks={len(data['binary_risks'])}")
        except Exception as e:
            print(f"[ERROR] Sector log: {e}")
    else:
        print("[WARN] No sector_intel.json found.")

    # 1b. Override breadth with market-breadth-analyzer cache (quantitative, higher precision)
    raw_breadth = load_breadth_cache()
    if raw_breadth:
        analyzer_breadth = extract_breadth_from_analyzer(raw_breadth)
        # Overwrite data.breadth entirely with quantitative data
        data["breadth"] = analyzer_breadth
        # Also sync back key fields to data.market so other pages stay consistent
        data["market"]["breadth_score"]      = analyzer_breadth["score"]
        data["market"]["breadth_components"] = analyzer_breadth["components"]
        data["market"]["uptrend_ratio"]      = analyzer_breadth["uptrend_ratio"]
        data["market"]["warning_flags"]      = analyzer_breadth["warning_flags"]
        data["market"]["cycle_phase"]        = analyzer_breadth["cycle_phase"]
        data["market"]["regime_confidence"]  = analyzer_breadth["regime_confidence"]
        data["market"]["exposure_ceiling"]   = analyzer_breadth["exposure_ceiling"]
        print(f"[OK] Breadth override: score={analyzer_breadth['score']} "
              f"zone={analyzer_breadth['zone']} "
              f"trend={analyzer_breadth['trend_direction']} "
              f"flags={analyzer_breadth['warning_flags']}")
    else:
        print("[INFO] No breadth cache for today — using sector_intel estimates")

    # 1c. FTD cache
    raw_ftd = load_ftd_cache()
    if raw_ftd:
        data["ftd"] = extract_ftd_data(raw_ftd)
        print(f"[OK] FTD: state={data['ftd']['state']} "
              f"score={data['ftd']['quality_score']} "
              f"signal={data['ftd']['signal']}")
    else:
        print("[INFO] No FTD cache found — run sector/ftd_yfinance.py")

    # 1d. Market Top cache
    raw_market_top = load_market_top_cache()
    if raw_market_top:
        data["market_top"] = extract_market_top_data(raw_market_top)
        print(f"[OK] Market Top: score={data['market_top']['composite_score']} "
              f"zone={data['market_top']['zone']} "
              f"budget={data['market_top']['risk_budget']}")
    else:
        print("[INFO] No Market Top cache found — run sector/market_top_yfinance.py")

    # 2. Audit history + watchlist
    positions_by_ticker, all_positions = load_positions_by_ticker()
    data["positions"] = all_positions
    data["recent_analysis"] = extract_audit_history(positions_by_ticker)
    wl_count = sum(1 for a in data["recent_analysis"] if a.get("on_watchlist"))
    live_count = sum(1 for a in data["recent_analysis"] if a.get("live_position"))
    print(f"[OK] Audit history: {len(data['recent_analysis'])} entries ({wl_count} watchlist, {live_count} live positions)")

    # 3. News
    data["news"] = extract_news()
    print(f"[OK] News: {len(data['news'])} items")

    # 4. Momentum screen (latest snapshot + history + journal stats)
    try:
        data["momentum_screen"] = ingest_momentum_screen()
        ms = data["momentum_screen"]
        if ms.get("status") == "success":
            print(f"[OK] Momentum screen: {ms['total_rows']} rows @ {ms['snap_id']} "
                  f"({ms['freshness']}, {ms['age_label']}) | "
                  f"history={len(ms['history_by_ticker'])} tickers | "
                  f"journal={ms['journal']['total_entries']} entries")
        else:
            print("[INFO] No momentum screen CSV found yet")
    except Exception as e:
        print(f"[WARN] Momentum screen ingest: {e}")

    # Write — strict JSON (no NaN/Infinity, which browsers reject)
    clean = _clean_nan(data)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(clean, f, indent=2, ensure_ascii=False, allow_nan=False)

    print(f"\n✅ Bridge complete → {OUTPUT_FILE}")
    print(f"   Regime     : {data['market'].get('regime')}  ({data['market'].get('cycle_phase')})")
    print(f"   Fear&Greed : {data['market'].get('fear_greed')}")
    print(f"   Breadth    : {data['market'].get('breadth_score')} | "
          f"Zone={data['breadth'].get('zone','–')} | "
          f"Trend={data['breadth'].get('trend_direction','–')} | "
          f"Src={data['breadth'].get('source','–')}")
    print(f"   8MA/200MA  : {data['breadth'].get('current_8ma','–')} / {data['breadth'].get('current_200ma','–')}")
    print(f"   Exposure   : {data['market'].get('exposure_ceiling')}  Mult {data['market'].get('macro_multiplier')}")
    print(f"   HOT        : {data['market'].get('hot_sectors')}")
    print(f"   Flags      : {data['market'].get('warning_flags')}")


if __name__ == "__main__":
    run_bridge()
