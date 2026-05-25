#!/usr/bin/env python3
"""
narrative-pulse-detector — input fetcher (8 inputs, 5 reused + 3 new).

Reuses:
  1. skills/momentum-monitor/scripts/technical_core.fetch_history / rsi_14 / ma_structure
  2. skills/market-top-detector/scripts/fmp_client.FMPClient.quote
  3. skills/finnhub-client/scripts/finnhub_client.FinnhubClient.upgrade_downgrade
  4. scripts/break_news/social_sources.fetch_reddit + fetch_hacker_news
  5. skills/market-top-detector/scripts/calculators/distribution_day_calculator (forked per-stock)

New helpers (本檔內):
  6. consecutive_overbought_days
  7. gap_up_density_4w
  8. news mention aggregator (掃 news/news_logs/*_raw.json)

Output: dict with all raw measurements for classify_stage.py to consume.
"""
import json
import os
import re
import sys
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

# ── Path bootstrapping ─────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]
for sub in (
    "skills/momentum-monitor/scripts",
    "skills/market-top-detector/scripts",
    "skills/finnhub-client/scripts",
    "scripts/break_news",
):
    p = REPO_ROOT / sub
    if p.is_dir() and str(p) not in sys.path:
        sys.path.insert(0, str(p))


# ── Component 1-2: OHLCV + RSI + SMA ───────────────────────────────────
def fetch_price_volume(ticker: str, period: str = "1y") -> dict:
    """OHLCV df + RSI series + MA structure. All deterministic from technical_core."""
    import technical_core as tc

    hist, _yfh = tc.fetch_history(ticker, period=period)
    if hist is None or hist.empty or len(hist) < 50:
        return {"ok": False, "reason": f"insufficient history ({len(hist) if hist is not None else 0} bars)"}

    close = hist["Close"]
    rsi = tc.rsi_14(close)
    ma = tc.ma_structure(hist)

    # Latest values
    price = float(close.iloc[-1])
    sma50 = float(close.tail(50).mean())
    sma200 = float(close.tail(200).mean()) if len(close) >= 200 else float(close.mean())
    rsi_latest = float(rsi.iloc[-1]) if not rsi.empty else None
    rsi_peak_30d = float(rsi.tail(30).max()) if len(rsi) >= 30 else (rsi_latest or 0.0)

    # SMA200 breakout 距今多少日 (close > sma200 連續站上多少天)
    # V1.1 fix: 若當前收盤未站上 SMA200,回傳 None (而非 0)。
    # 舊版會在 close<sma200 時 break 在第一根 below 並回 0,被 Stage 1 brewing
    # rule `0 <= sma200_breakout_days_ago <= 30` 誤判為「剛突破」。
    if len(close) >= 200:
        rolling_sma200 = close.rolling(200).mean()
        above = close > rolling_sma200
        if not above.iloc[-1] or pd.isna(above.iloc[-1]):
            # 當前低於 SMA200 (或最新值缺) — 沒有 fresh breakout window
            sma200_breakout_days_ago = None
        else:
            last_above_streak = 0
            for i in range(len(above) - 1, -1, -1):
                if pd.isna(above.iloc[i]) or not above.iloc[i]:
                    break
                last_above_streak += 1
            sma200_breakout_days_ago = last_above_streak
    else:
        sma200_breakout_days_ago = None

    return {
        "ok": True,
        "hist": hist,  # full DataFrame (volumetric helpers need this)
        "rsi_series": rsi,
        "price": price,
        "sma50": sma50,
        "sma200": sma200,
        "rsi_14_latest": rsi_latest,
        "rsi_peak_recent": rsi_peak_30d,
        "price_to_sma50_ratio": round(price / sma50, 3) if sma50 else None,
        "price_to_sma200_ratio": round(price / sma200, 3) if sma200 else None,
        "sma200_breakout_days_ago": sma200_breakout_days_ago,
        "ma_structure": ma,
    }


# ── Component (new helper): RSI overbought episode tracking ────────────
def consecutive_overbought_days(rsi_series: pd.Series, threshold: float = 70.0,
                                reset_below: float = 50.0) -> int:
    """Strict consecutive-day count: walk back from the latest bar; every bar
    with RSI >= threshold adds 1, the first bar with RSI < threshold ends the
    streak. Does NOT use `reset_below` (kept for backward signature compat —
    use `overbought_episode_days` if you want the looser definition).
    """
    if rsi_series is None or rsi_series.empty:
        return 0
    count = 0
    for i in range(len(rsi_series) - 1, -1, -1):
        v = rsi_series.iloc[i]
        if pd.isna(v):
            continue
        if v >= threshold:
            count += 1
        else:
            break
    return count


def overbought_episode_days(rsi_series: pd.Series, threshold: float = 70.0,
                            reset_below: float = 50.0) -> int:
    """Loose episode-length count: walk back from the latest bar; the episode
    runs until RSI drops decisively below `reset_below`. Bars in the
    [reset_below, threshold) buffer zone are tolerated — counted toward
    episode length but do NOT increment the overbought-bar tally. Returns
    the number of bars where RSI >= threshold inside the episode.

    Rationale: narrative-trade rallies routinely dip below 70 for 1-3 days
    without breaking the underlying euphoria. Strict streak (above) under-
    counts these episodes. The loose count better matches the visual sense
    of "stock has been overbought for weeks".
    """
    if rsi_series is None or rsi_series.empty:
        return 0
    overbought_bars = 0
    for i in range(len(rsi_series) - 1, -1, -1):
        v = rsi_series.iloc[i]
        if pd.isna(v):
            continue
        if v < reset_below:
            break  # episode ended — RSI broke through the floor
        if v >= threshold:
            overbought_bars += 1
        # else: in [reset_below, threshold) buffer — tolerate, keep walking
    return overbought_bars


# ── Component (new helper): impulse-day density ────────────────────────
def gap_up_density(hist: pd.DataFrame, window_days: int = 20, gap_pct: float = 5.0) -> int:
    """Count `impulse days` in last `window_days` — bars where close-to-close
    percent change >= gap_pct. This captures narrative-driven buying that
    can manifest as intraday rallies (open low, close high) just as much as
    overnight gaps. Using close-to-close is the more relevant signal for
    narrative trade stage detection (vs strict open-vs-prev-close gap).
    """
    if hist is None or len(hist) < 2:
        return 0
    recent = hist.tail(window_days + 1)
    closes = recent["Close"].values
    count = 0
    for i in range(1, len(recent)):
        prev_close = closes[i - 1]
        if prev_close <= 0:
            continue
        pct = (closes[i] / prev_close - 1) * 100
        if pct >= gap_pct:
            count += 1
    return count


# ── Component (new helper): volume baseline + recent ratio ─────────────
def volume_dynamics(hist: pd.DataFrame) -> dict:
    """Compare recent 20d avg volume vs early 30d baseline (90d ago).
    Returns multiplier indicating how many x baseline current activity is.
    """
    if hist is None or len(hist) < 60:
        return {"baseline": None, "recent": None, "multiplier": None}
    vol = hist["Volume"]
    # Baseline: 30 bars starting 90d ago (or earliest 30 if not enough history)
    if len(vol) >= 90:
        baseline = float(vol.iloc[-90:-60].mean())
    else:
        baseline = float(vol.iloc[: max(1, len(vol) - 60)].mean())
    recent = float(vol.tail(20).mean())
    mult = round(recent / baseline, 2) if baseline > 0 else None
    return {
        "baseline": int(baseline) if baseline > 0 else 0,
        "recent": int(recent),
        "multiplier": mult,
    }


# ── Component 3: 52w high/low (from FMP quote) ─────────────────────────
def fetch_quote(ticker: str) -> dict:
    """FMPClient.quote → simplified dict."""
    try:
        from fmp_client import FMPClient
    except Exception:
        return {"ok": False, "reason": "fmp_client import failed"}
    try:
        c = FMPClient()
    except ValueError:
        return {"ok": False, "reason": "FMP_API_KEY missing"}
    data = c._request_with_fallback("quote", ticker)
    if not data or not isinstance(data, list):
        return {"ok": False, "reason": "no quote data"}
    q = data[0]
    return {
        "ok": True,
        "price": q.get("price"),
        "change_pct": q.get("changesPercentage") or q.get("changePercentage"),
        "volume": q.get("volume"),
        "year_high": q.get("yearHigh"),
        "year_low": q.get("yearLow"),
        "market_cap": q.get("marketCap"),
    }


# ── Component 4: per-stock distribution day (forked from market-top-detector) ──
def distribution_days_per_stock(hist: pd.DataFrame, window: int = 25) -> dict:
    """Per-stock O'Neil distribution day (≥0.2% drop on higher volume) + stalling.
    Adapted from skills/market-top-detector/scripts/calculators/distribution_day_calculator.py:94
    but operates on single-stock OHLCV instead of index pair.
    """
    if hist is None or len(hist) < window + 1:
        return {"distribution_days": 0, "stalling_days": 0, "failed_rally": False, "details": []}

    rows = hist.tail(window + 1)
    distribution_days = 0
    stalling_days = 0
    details = []

    closes = rows["Close"].values
    volumes = rows["Volume"].values
    highs = rows["High"].values
    dates = rows.index

    for i in range(1, len(rows)):
        today_close = closes[i]
        prev_close = closes[i - 1]
        today_vol = volumes[i]
        prev_vol = volumes[i - 1]
        if prev_close == 0 or prev_vol == 0:
            continue
        pct = (today_close - prev_close) / prev_close * 100
        vol_up = today_vol > prev_vol
        date_str = dates[i].strftime("%Y-%m-%d") if hasattr(dates[i], "strftime") else str(dates[i])

        if pct <= -0.2 and vol_up:
            distribution_days += 1
            details.append({"date": date_str, "type": "distribution", "pct": round(pct, 2)})
        elif vol_up and 0 <= pct < 0.1:
            stalling_days += 1
            details.append({"date": date_str, "type": "stalling", "pct": round(pct, 2)})

    # Failed rally: new high in window then close back below prior swing low
    failed_rally = False
    if len(highs) >= 10:
        recent_high = float(max(highs[-10:]))
        prior_low = float(min(closes[-20:-10])) if len(closes) >= 20 else float(min(closes[:-10]))
        if closes[-1] < prior_low and recent_high == max(highs[-20:] if len(highs) >= 20 else highs):
            failed_rally = True

    return {
        "distribution_days": distribution_days,
        "stalling_days": stalling_days,
        "failed_rally": failed_rally,
        "details": details,
    }


# ── Component 5: sell-side analyst positive actions (Finnhub) ──────────
# Codex review #6: this counts Finnhub /stock/upgrade-downgrade events
# matching an "upgrade / raise / initiate-buy" pattern. That's a proxy for
# "sell-side getting more positive" — NOT strictly a price-target raise event.
# We emit both names: legacy `pt_raise_30d` (used by stage_weights.yaml
# rules and existing tests) AND the more accurate `analyst_positive_actions_30d`.
# Future V1.1: add FMP `historical-grades` / `price-target` as a true PT-raise
# event stream and consider deprecating the legacy name.
def fetch_pt_cadence(ticker: str) -> dict:
    """Count of analyst upgrade / raise / initiate-buy events in last 30/60 days.
    NOTE: this is a proxy for `pt_raise` — see comment above the function."""
    try:
        from finnhub_client import FinnhubClient
    except Exception:
        return {"ok": False, "pt_raise_30d": 0, "pt_raise_60d": 0, "reason": "finnhub import failed"}
    try:
        c = FinnhubClient()
    except Exception as e:
        return {"ok": False, "pt_raise_30d": 0, "pt_raise_60d": 0, "reason": str(e)[:80]}

    try:
        events = c.upgrade_downgrade(ticker)
    except Exception as e:
        # Finnhub /stock/upgrade-downgrade requires paid plan; fail gracefully.
        return {"ok": False, "pt_raise_30d": 0, "pt_raise_60d": 0,
                "reason": f"finnhub_premium_required: {str(e)[:60]}"}
    if not events or not isinstance(events, list):
        return {"ok": True, "pt_raise_30d": 0, "pt_raise_60d": 0, "events": []}

    now = datetime.now(timezone.utc)
    cutoff_30 = now - timedelta(days=30)
    cutoff_60 = now - timedelta(days=60)
    raise_30 = 0
    raise_60 = 0
    for e in events:
        # Finnhub returns 'gradeTime' (unix) or 'date' depending on version
        ts = e.get("gradeTime") or e.get("date") or e.get("publishedDate")
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        elif isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
        else:
            continue
        # Action: prefer toGrade upgrade vs fromGrade downgrade; also catch raise/lift keywords
        action = (e.get("action") or "").lower()
        from_g = (e.get("fromGrade") or "").lower()
        to_g = (e.get("toGrade") or "").lower()
        is_raise = (
            action in ("upgrade", "up", "raise", "raised", "initiated buy")
            or ("buy" in to_g and "buy" not in from_g)
            or ("overweight" in to_g and "overweight" not in from_g)
            or ("strong buy" in to_g and "strong buy" not in from_g)
        )
        if not is_raise:
            continue
        if dt >= cutoff_30:
            raise_30 += 1
        if dt >= cutoff_60:
            raise_60 += 1

    return {"ok": True, "pt_raise_30d": raise_30, "pt_raise_60d": raise_60, "events_total": len(events)}


# ── Component 6: retail sentiment ($TICKER cashtag) ────────────────────
_CASHTAG_RE = None


def _build_cashtag_re(ticker: str):
    # $TICKER (case insensitive) — word boundary on both sides
    return re.compile(rf"\${re.escape(ticker)}\b", re.IGNORECASE)


def fetch_retail_mentions(ticker: str, window_hours: int = 24) -> dict:
    """Count Reddit + HN $TICKER cashtag mentions in last window_hours.
    Reuses scripts/break_news/social_sources.fetch_reddit + fetch_hacker_news.

    Returns absolute count (24h) + 7d-rolling baseline multiplier.
    """
    try:
        import social_sources as ss
    except Exception:
        return {"ok": False, "mention_24h": 0, "baseline_7d_avg": 0, "multiplier": None,
                "reason": "social_sources import failed"}

    cashtag = _build_cashtag_re(ticker)
    ticker_word = re.compile(rf"\b{re.escape(ticker)}\b", re.IGNORECASE)

    def _count_in(items):
        n = 0
        for it in items or []:
            text = (it.get("headline") or "") + " " + (it.get("summary") or "")
            # Strict: cashtag $TICKER OR plain TICKER if length >= 4 (avoid $A/$T false positives)
            if cashtag.search(text):
                n += 1
            elif len(ticker) >= 4 and ticker_word.search(text):
                n += 1
        return n

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            reddit_items, _ = ss.fetch_reddit(window_hours=window_hours)
    except Exception:
        reddit_items = []
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            hn_items, _ = ss.fetch_hacker_news(window_hours=window_hours)
    except Exception:
        hn_items = []

    mention_24h = _count_in(reddit_items) + _count_in(hn_items)

    # Baseline: same fetch for 168h, divide by 7, exclude latest 24h to avoid double-count
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            reddit_7d, _ = ss.fetch_reddit(window_hours=168)
            hn_7d, _ = ss.fetch_hacker_news(window_hours=168)
        total_7d = _count_in(reddit_7d) + _count_in(hn_7d)
        prior_6d = max(0, total_7d - mention_24h)
        baseline_avg = prior_6d / 6.0
    except Exception:
        baseline_avg = 0.0

    mult = round(mention_24h / baseline_avg, 2) if baseline_avg > 0 else None
    return {
        "ok": True,
        "mention_24h": mention_24h,
        "baseline_7d_avg": round(baseline_avg, 1),
        "multiplier": mult,
    }


# ── Component 7: news mention aggregator ───────────────────────────────
def fetch_news_mentions(ticker: str, days: int = 30) -> dict:
    """Scan news/news_logs/*_raw.json + *_digest.json for ticker mentions.
    Returns count + unique source diversity index.
    """
    logs_dir = REPO_ROOT / "news" / "news_logs"
    if not logs_dir.is_dir():
        return {"ok": False, "mention_30d": 0, "source_diversity": 0, "reason": "news_logs missing"}

    cutoff = datetime.now(timezone.utc).date() - timedelta(days=days)
    pattern = re.compile(rf"\b{re.escape(ticker)}\b")
    mention_count = 0
    sources: set = set()

    # Iterate recent log files (filename has date prefix)
    for fp in sorted(logs_dir.glob("*.json"), reverse=True):
        # Parse date from filename like "2026-05-22_digest.json" or "2026-05-22_raw.json"
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", fp.name)
        if not m:
            continue
        try:
            fdate = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if fdate < cutoff:
            continue
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        # Flatten: digest is {sections: [{headlines: [...]}]}; raw is list of items
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for k in ("items", "headlines", "news", "raw_items", "sections"):
                if k in data and isinstance(data[k], list):
                    for x in data[k]:
                        if isinstance(x, dict) and "headlines" in x:
                            items.extend(x["headlines"])
                        else:
                            items.append(x)
                    break

        for it in items:
            if not isinstance(it, dict):
                continue
            text = " ".join(str(it.get(k, "")) for k in ("headline", "title", "summary", "tickers", "ticker"))
            if pattern.search(text):
                mention_count += 1
                src = it.get("source") or it.get("feed") or it.get("publisher") or "unknown"
                sources.add(str(src)[:60])

    return {
        "ok": True,
        "mention_30d": mention_count,
        "source_diversity": len(sources),
        "sources_sample": list(sources)[:10],
    }


# ── Component 8: macro snapshot (VIX + breadth) ────────────────────────
def fetch_macro_snapshot() -> dict:
    """VIX + breadth 200dma — light snapshot, all cached upstream."""
    out = {"ok": True, "vix": None, "breadth_200dma_pct": None}
    # VIX via yfinance (cheap, doesn't need FMP)
    try:
        import yfinance as yf
        v = yf.Ticker("^VIX").history(period="5d", auto_adjust=False)
        if not v.empty:
            out["vix"] = round(float(v["Close"].iloc[-1]), 2)
    except Exception:
        out["ok"] = False
    # Breadth via TraderMonty public CSV
    try:
        sys.path.insert(0, str(REPO_ROOT / "skills/market-top-detector/scripts"))
        from breadth_csv_client import fetch_breadth_200dma
        data = fetch_breadth_200dma()
        if data and isinstance(data, dict):
            out["breadth_200dma_pct"] = data.get("latest_pct") or data.get("current_pct")
    except Exception:
        pass
    return out


# ── Orchestrator ───────────────────────────────────────────────────────
def fetch_all(ticker: str) -> dict:
    """Run all 8 fetchers, return single dict consumable by classify_stage.py.
    Each sub-fetcher is wrapped — single failure doesn't crash the whole bundle.
    """
    ticker = ticker.upper().strip()
    out: dict = {
        "ticker": ticker,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "input_health": {},
    }

    pv = fetch_price_volume(ticker)
    out["input_health"]["ohlcv_ok"] = pv.get("ok", False)
    if pv.get("ok"):
        rsi_series = pv["rsi_series"]
        hist = pv["hist"]
        vol_dyn = volume_dynamics(hist)
        out["components"] = {
            "rsi_14_latest": pv["rsi_14_latest"],
            "rsi_peak_recent": pv["rsi_peak_recent"],
            "rsi_overbought_days": consecutive_overbought_days(rsi_series),
            "rsi_overbought_episode_days": overbought_episode_days(rsi_series),
            "price_to_sma50_ratio": pv["price_to_sma50_ratio"],
            "price_to_sma200_ratio": pv["price_to_sma200_ratio"],
            "sma200_breakout_days_ago": pv["sma200_breakout_days_ago"],
            "volume_baseline_30d_avg": vol_dyn["baseline"],
            "volume_recent_20d_avg": vol_dyn["recent"],
            "volume_multiplier": vol_dyn["multiplier"],
            "gap_up_density_4w": gap_up_density(hist, window_days=20, gap_pct=5.0),
        }
        out["data_window"] = {
            "ohlcv_from": hist.index[0].strftime("%Y-%m-%d") if hasattr(hist.index[0], "strftime") else str(hist.index[0]),
            "ohlcv_to":   hist.index[-1].strftime("%Y-%m-%d") if hasattr(hist.index[-1], "strftime") else str(hist.index[-1]),
            "ohlcv_bars": len(hist),
        }
        # Distribution days from same hist
        dd = distribution_days_per_stock(hist, window=25)
        out["components"]["distribution_days_25d"] = dd["distribution_days"]
        out["components"]["stalling_days_25d"] = dd["stalling_days"]
        out["components"]["failed_rally_signal"] = dd["failed_rally"]
        out["distribution_detail"] = dd["details"]
    else:
        out["components"] = {}
        out["reason"] = pv.get("reason")

    q = fetch_quote(ticker)
    out["input_health"]["quote_ok"] = q.get("ok", False)
    if q.get("ok"):
        out["quote"] = {k: q[k] for k in ("price", "change_pct", "volume", "year_high", "year_low", "market_cap")}

    pt = fetch_pt_cadence(ticker)
    out["input_health"]["finnhub_pt_ok"] = pt.get("ok", False)
    # Codex review #6 — emit accurate name AND legacy alias so YAML rules
    # / fixtures keep working while consumers can migrate.
    pt_30 = pt.get("pt_raise_30d", 0)
    pt_60 = pt.get("pt_raise_60d", 0)
    out["components"]["pt_raise_30d"] = pt_30                       # legacy
    out["components"]["pt_raise_60d"] = pt_60                       # legacy
    out["components"]["analyst_positive_actions_30d"] = pt_30       # accurate
    out["components"]["analyst_positive_actions_60d"] = pt_60       # accurate

    rs = fetch_retail_mentions(ticker, window_hours=24)
    out["input_health"]["social_ok"] = rs.get("ok", False)
    out["components"]["retail_mention_24h"] = rs.get("mention_24h", 0)
    out["components"]["retail_mention_baseline_7d_avg"] = rs.get("baseline_7d_avg", 0)
    out["components"]["retail_mention_multiplier"] = rs.get("multiplier")

    nm = fetch_news_mentions(ticker, days=30)
    out["input_health"]["news_ok"] = nm.get("ok", False)
    out["components"]["media_mention_30d"] = nm.get("mention_30d", 0)
    out["components"]["media_source_diversity"] = nm.get("source_diversity", 0)

    macro = fetch_macro_snapshot()
    out["input_health"]["macro_ok"] = macro.get("ok", False)
    out["components"]["vix_now"] = macro.get("vix")
    out["components"]["breadth_200dma_pct"] = macro.get("breadth_200dma_pct")

    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    args = ap.parse_args()
    result = fetch_all(args.ticker)
    # Drop pandas objects before JSON dump
    if "components" in result:
        pass  # already scalar
    # Don't dump hist df
    safe = {k: v for k, v in result.items() if not isinstance(v, pd.DataFrame)}
    print(json.dumps(safe, indent=2, default=str))
