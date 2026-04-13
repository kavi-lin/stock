import json
import os
import glob
import re
import requests
from datetime import datetime, date

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
OUTPUT_FILE   = os.path.join(BASE_DIR, 'Dashboard', 'data.json')


def get_latest_file(pattern):
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None


# ─────────────────────────────────────────────
# MARKET BREADTH ANALYZER CACHE
# ─────────────────────────────────────────────

def load_breadth_cache():
    """Load today's market-breadth-analyzer output from breadth_cache/.
    Returns parsed JSON dict, or None if not found."""
    today_str = date.today().strftime("%Y-%m-%d")
    pattern = os.path.join(BREADTH_CACHE, f"market_breadth_{today_str}_*.json")
    files = glob.glob(pattern)
    if not files:
        return None
    latest = max(files, key=os.path.getmtime)
    try:
        with open(latest, 'r') as f:
            data = json.load(f)
        print(f"[OK] Breadth cache: {os.path.basename(latest)}")
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
        "notes":            s_data.get("session_notes", ""),
    }


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
            "proxy_etf":        s.get("proxy_etf", ""),
            "risk_flags":       s.get("risk_flags", []),
            "key_reason":       (s.get("key_reasons") or [""])[0],
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
        risks.append({
            "event":            ev.get("event", ""),
            "date":             ev_date_str,
            "days_until":       days_until,
            "affected_sectors": ev.get("affected_sectors", []),
            "within_48h":       ev.get("within_48h", False),
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


def extract_audit_history():
    """Build recent_analysis[] with full watchlist metadata"""
    audit_map = {}
    audits    = []

    history_file = os.path.join(INVEST_LOGS, 'history.json')
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                history_data = json.load(f)

            for item in reversed(history_data[-10:]):
                ticker    = item.get("ticker", "UNKNOWN")
                date_raw  = item.get("date", "Unknown")
                date_clean = date_raw.replace("-", "")
                meta      = item.get("metadata", {})

                report_path = _find_report(ticker, date_clean)
                decision    = item.get("final_action", "HOLD")
                score       = meta.get("final_score") or item.get("final_score", 0.0)

                # Price targets
                tp    = meta.get("take_profit") or item.get("take_profit")
                sl    = meta.get("stop_loss") or item.get("stop_loss")
                watch = meta.get("watch_price") or meta.get("trigger_price")
                entry = meta.get("entry_range") or meta.get("entry_price")

                if not entry and not watch:
                    ctx = meta.get("macro_context", "")
                    pm  = re.findall(r"\$(\d+[\-\d]*)", ctx)
                    if pm:
                        entry = pm[-1]

                if isinstance(entry, list):
                    entry = " - ".join(str(e) for e in entry)

                # Backtest P/L
                perf = None
                if FMP_API_KEY and isinstance(meta.get("entry_range"), list):
                    try:
                        res = requests.get(
                            f"https://financialmodelingprep.com/api/v3/quote/{ticker}"
                            f"?apikey={FMP_API_KEY}", timeout=5
                        ).json()
                        if res:
                            curr  = res[0].get("price")
                            ep    = float(str(meta["entry_range"][0]).replace("$", ""))
                            chg   = ((curr - ep) / ep) * 100
                            perf  = {"current": curr, "entry": ep, "change": round(chg, 2)}
                    except Exception as e:
                        print(f"[WARN] Backtest {ticker}: {e}")

                # ── Watchlist metadata ──────────────────────────────
                watch_conditions = meta.get("watch_conditions")  # dict entry_A/B/C
                key_risks        = meta.get("key_risks", [])
                rr_ratio         = meta.get("risk_reward_ratio")
                position_pct     = meta.get("position_size_pct")
                avg_conf         = meta.get("avg_confidence")
                time_horizon     = meta.get("time_horizon")
                da_filed         = meta.get("devils_advocate_filed", False)
                # Determine if this ticker belongs on watchlist
                on_watchlist = (
                    decision == "EXECUTE" or
                    bool(watch_conditions) or
                    bool(watch)
                )

                audits.append({
                    "ticker":           ticker,
                    "decision":         decision,
                    "score":            round(float(score), 2) if score is not None else 0.0,
                    "time":             date_raw,
                    "report_url":       report_path,
                    "performance":      perf,
                    "targets":          {"tp": tp, "sl": sl, "watch": watch, "entry": entry},
                    # Watchlist fields
                    "on_watchlist":     on_watchlist,
                    "watch_conditions": watch_conditions,
                    "key_risks":        key_risks,
                    "rr_ratio":         rr_ratio,
                    "position_pct":     position_pct,
                    "avg_confidence":   avg_conf,
                    "time_horizon":     time_horizon,
                    "da_filed":         da_filed,
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
    pattern = os.path.join(FTD_CACHE, "ftd_detector_*.json")
    files = glob.glob(pattern)
    if not files:
        return None
    latest = max(files, key=os.path.getmtime)
    try:
        with open(latest, 'r') as f:
            data = json.load(f)
        print(f"[OK] FTD cache: {os.path.basename(latest)}")
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
    pattern = os.path.join(MARKET_TOP_CACHE, "market_top_*.json")
    files = glob.glob(pattern)
    if not files:
        return None
    latest = max(files, key=os.path.getmtime)
    try:
        with open(latest, 'r') as f:
            data = json.load(f)
        print(f"[OK] Market Top cache: {os.path.basename(latest)}")
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
    news_dates_seen = set()
    for news_file in sorted(glob.glob(os.path.join(NEWS_LOGS, "*_digest.json")), reverse=True)[:3]:
        try:
            with open(news_file, 'r') as f:
                n_data = json.load(f)
            file_date = n_data.get("timestamp", "")[:10]
            news_dates_seen.add(file_date)
            for v in n_data.get("verdicts", []):
                sector_names = [s.get("sector", "Unknown") for s in v.get("affected_sectors", [])]
                news.append({
                    "headline":          v.get("headline"),
                    "headline_zh":       v.get("headline_zh", ""),
                    "impact":            v.get("verdict", "NEUTRAL").lower(),
                    "score":             v.get("net_impact_score"),
                    "date":              file_date,
                    "sectors":           sector_names,
                    "source":            "news_protocol",
                    "source_label":      v.get("source_label", ""),
                    "type":              v.get("type", ""),
                    "bull_case":         v.get("bull_case", ""),
                    "bear_case":         v.get("bear_case", ""),
                    "arbiter_reasoning": v.get("arbiter_reasoning", ""),
                    "debate_note":       v.get("debate_note", ""),
                    "binary_risk":       v.get("binary_risk", False),
                    "within_48h":        v.get("within_48h", False),
                })
        except Exception as e:
            print(f"[ERROR] News log {news_file}: {e}")

    # 2. Supplement from sector_intel (upcoming_binary_events + top_catalysts)
    latest_sector = get_latest_file(os.path.join(SECTOR_LOGS, "*_sector_intel.json"))
    if latest_sector:
        try:
            with open(latest_sector, 'r') as f:
                s_data = json.load(f)
            sector_date = s_data.get("verdict_date", s_data.get("generated_at", ""))[:10]

            # upcoming_binary_events → treat as news items
            for ev in s_data.get("upcoming_binary_events", []):
                ev_date = ev.get("date") or ev.get("dates", "")
                # Normalise: take first date if range (e.g. "2026-04-13 to 2026-04-15")
                ev_date_clean = ev_date.split(" to ")[0].strip() if ev_date else sector_date
                direction = ev.get("direction", "BINARY").split("—")[0].strip().lower()
                impact_map = {"bullish": "bullish", "bearish": "bearish", "binary": "binary", "neutral": "neutral"}
                impact = impact_map.get(direction.lower().split()[0] if direction else "binary", "binary")
                news.append({
                    "headline": ev.get("event", ""),
                    "impact":   impact,
                    "score":    0.0,
                    "date":     ev_date_clean,
                    "sectors":  ev.get("impact_sectors", []),
                    "source":   "sector_intel",
                })

            # top_catalysts (old schema key, may exist)
            for cat in s_data.get("top_catalysts", []) or []:
                if not cat.get("event"):
                    continue
                direction = cat.get("direction", "neutral").lower()
                news.append({
                    "headline": cat.get("event", ""),
                    "impact":   direction if direction in ("bullish", "bearish", "binary") else "neutral",
                    "score":    float(cat.get("impact_score", 0)),
                    "date":     (cat.get("updated_at") or sector_date)[:10],
                    "sectors":  cat.get("affected_sectors", []),
                    "source":   "sector_intel",
                })

        except Exception as e:
            print(f"[ERROR] Sector intel news extraction: {e}")

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
            print(f"[OK] Sector: {os.path.basename(latest_sector)} | "
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
    data["recent_analysis"] = extract_audit_history()
    wl_count = sum(1 for a in data["recent_analysis"] if a.get("on_watchlist"))
    print(f"[OK] Audit history: {len(data['recent_analysis'])} entries ({wl_count} on watchlist)")

    # 3. News
    data["news"] = extract_news()
    print(f"[OK] News: {len(data['news'])} items")

    # Write
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

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
