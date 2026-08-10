#!/usr/bin/env python3
"""Build the deterministic market-atmosphere block for the Mood dashboard.

This is deliberately separate from ``mood.py``.  The legacy mood fields are
kept for compatibility; this producer adds a human-readable, 17-indicator
dashboard and seven hard-trigger states.  Missing or stale inputs remain
missing/uncertain -- the producer never fills a hole with an LLM judgment.

Usage:
    python3 market_atmosphere.py --output Dashboard/market_mood.json
    python3 market_atmosphere.py --offline --output /tmp/market_mood.json
"""
from __future__ import annotations

import argparse
import calendar
import concurrent.futures
import html
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except Exception:  # pragma: no cover - offline/test environments
    requests = None


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
UA = "AI-Investment-Committee/1.0 (deterministic market dashboard)"
TIMEOUT = 8


def _num(value):
    try:
        value = float(value)
        return None if math.isnan(value) or math.isinf(value) else value
    except (TypeError, ValueError):
        return None


def _round(value, digits=2):
    value = _num(value)
    return round(value, digits) if value is not None else None


def _load(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError):
        return None


def _write_atomic(path, payload):
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
    os.replace(tmp, path)


def _clean(text):
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def _fetch(url):
    if requests is None:
        return ""
    try:
        response = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        response.raise_for_status()
        return response.text
    except Exception:
        return ""


def _fetch_pdf_text(url):
    """Fetch a public PDF and extract text when Poppler is available."""
    if requests is None:
        return ""
    try:
        response = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        response.raise_for_status()
        if not response.content.startswith(b"%PDF"):
            return ""
        result = subprocess.run(
            ["pdftotext", "-layout", "-", "-"],
            input=response.content,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT,
            check=False,
        )
        return result.stdout.decode("utf-8", errors="replace") if result.returncode == 0 else ""
    except Exception:
        return ""


def _source_status(value, source="local"):
    return "ok" if value is not None else ("unavailable" if source != "local" else "missing")


def _record(key, group, name, value, date, threshold, status, note, source,
            *, display=None, interpretation=None, history_value=None, source_status=None):
    return {
        "key": key,
        "group": group,
        "name": name,
        "value": value,
        "display_value": display if display is not None else ("—" if value is None else str(value)),
        "data_date": date,
        "threshold": threshold,
        "status": status,
        "signal": {"green": "🟢", "yellow": "🟡", "red": "🔴", "gray": "⚪"}.get(status, "⚪"),
        "interpretation_zh": interpretation or note,
        "note_zh": note,
        "source": source,
        "source_status": source_status or _source_status(value, source),
        "history_value": history_value if history_value is not None else value,
    }


def _local_inputs(output_path):
    current = _load(output_path) or {}
    mood = current
    fred = _load(ROOT / "skills/fred-macro/cache/fred_latest.json") or {}
    breadth_dir = ROOT / "sector/breadth_cache"
    breadth_files = sorted(breadth_dir.glob("market_breadth_*.json"), key=lambda p: p.stat().st_mtime)
    breadth = _load(breadth_files[-1]) if breadth_files else None
    return current, mood, fred.get("series", {}), breadth or {}


def _external_pages(offline):
    if offline:
        return {"_fetch_errors": {}}
    urls = {
        "aaii_sentiment": "https://www.aaii.com/sentimentsurvey",
        "aaii_allocation": "https://www.aaii.com/assetallocationsurvey",
        "naaim": "https://www.naaim.org/programs/naaim-exposure-index/",
        "finra_margin": "https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics",
        "margin_gdp": "https://www.gurufocus.com/economic_indicators/4266/finra-investor-margin-debt-relative-to-gdp",
        "insider": "https://www.gurufocus.com/economic_indicators/4359/insider-buysell-ratio-usa-overall-market",
        "ipo": "https://www.renaissancecapital.com/IPO-Center/Stats",
        "bofa_viewpoint_july": "https://mlaem.fs.ml.com/content/dam/ML/ecomm/pdf/ML_Viewpoint_July2026_eComm.pdf",
        "bofa_viewpoint_june": "https://mlaem.fs.ml.com/content/dam/ML/ecomm/pdf/ML_Viewpoint_June2026_eComm.pdf",
        "buffett": "https://currentmarketvaluation.com/models/buffett-indicator.php",
        "cape": "https://www.multpl.com/shiller-pe/table/by-month",
        "lei": "https://www.conference-board.org/topics/us-leading-indicators",
    }
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        jobs = {
            pool.submit(_fetch_pdf_text if key.startswith("bofa_viewpoint") else _fetch, url): key
            for key, url in urls.items()
        }
        pages = {key: future.result() for future, key in ((job, jobs[job]) for job in jobs)}
    pages["_fetch_errors"] = {
        key: "empty_response"
        for key, value in pages.items()
        if key != "_fetch_errors" and not value
    }
    return pages


def _latest_percent(text, label_patterns):
    if not text:
        return None
    for pattern in label_patterns:
        match = re.search(pattern + r"[^%]{0,100}?([0-9]+(?:\.[0-9]+)?)\s*%", text, re.I)
        if match:
            return _num(match.group(1))
    return None


def _parse_number_after(text, patterns, *, percent=False):
    for pattern in patterns:
        match = re.search(pattern, text or "", re.I)
        if match:
            value = _num(match.group(1))
            if value is not None:
                return value
    return None


def _parse_aaii_sentiment(text):
    clean = _clean(text)
    return {
        "bullish": _latest_percent(clean, [r"Bullish", r"optimistic"]),
        "bearish": _latest_percent(clean, [r"Bearish", r"pessimistic"]),
        "neutral": _latest_percent(clean, [r"Neutral"]),
    }


def _parse_aaii_allocation(text):
    clean = _clean(text)
    # Page wording has changed over time. Prefer total equity allocation, then
    # the public stock-funds figure when only that series is available.
    value = _parse_number_after(clean, [
        r"(?:stocks?\s*(?:and|&)\s*stock funds|equity allocation)[^0-9]{0,80}([0-9]+(?:\.[0-9]+)?)\s*%",
        r"stocks?[^0-9]{0,80}([0-9]+(?:\.[0-9]+)?)\s*%",
    ])
    return value


def _parse_naaim(text):
    clean = _clean(text)
    return _parse_number_after(clean, [
        r"(?:exposure index|current exposure)[^0-9-]{0,60}(-?[0-9]+(?:\.[0-9]+)?)",
        r"(?:NAAIM)[^0-9-]{0,60}(-?[0-9]+(?:\.[0-9]+)?)",
    ])


def _parse_gurufocus_ratio(text):
    clean = _clean(text)
    return _parse_number_after(clean, [
        r"(?:insider buy[\s/-]*sell ratio|buy[\s/-]*sell ratio)[^0-9]{0,80}([0-9]+(?:\.[0-9]+)?)",
    ])


def _parse_finra_margin_debt(text):
    """Parse FINRA's public monthly table, newest or oldest order."""
    clean = _clean(text)
    month_names = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
    pattern = re.compile(
        rf"\b({month_names})[- ](\d{{2,4}})\s+"
        r"([0-9][0-9,]*)\s+[0-9][0-9,]*\s+[0-9][0-9,]*",
        re.I,
    )
    rows = []
    for match in pattern.finditer(clean):
        month, year, value = match.groups()
        year_i = int(year)
        year_i += 2000 if year_i < 100 else 0
        try:
            month_i = list(calendar.month_abbr).index(month.title())
            date = datetime(year_i, month_i, calendar.monthrange(year_i, month_i)[1])
        except (ValueError, IndexError):
            continue
        rows.append({
            "date": date.strftime("%Y-%m-%d"),
            "value": int(value.replace(",", "")),
        })
    return sorted({row["date"]: row for row in rows}.values(), key=lambda row: row["date"])


def _parse_margin_gdp(text):
    clean = _clean(text)
    return _parse_number_after(clean, [
        r"FINRA investor margin debt relative to GDP[^0-9]{0,100}([0-9]+(?:\.[0-9]+)?)\s*%",
        r"margin debt relative to GDP[^0-9]{0,100}([0-9]+(?:\.[0-9]+)?)\s*%",
        r"currently[^0-9]{0,30}([0-9]+(?:\.[0-9]+)?)\s*%",
    ])


def _parse_ipo_stats(text):
    clean = _clean(text)
    count = _parse_number_after(clean, [
        r"There have been\s+([0-9]+)\s+IPOs priced this year",
    ])
    count_change = _parse_number_after(clean, [
        r"IPOs priced this year[^%]*?([+-]?[0-9]+(?:\.[0-9]+)?)\s*%\s*change",
    ])
    proceeds = _parse_number_after(clean, [
        r"Total proceeds raised were\s*\$\s*([0-9]+(?:\.[0-9]+)?)\s*bil",
    ])
    proceeds_change = _parse_number_after(clean, [
        r"Total proceeds raised were[^%]*?([+-]?[0-9]+(?:\.[0-9]+)?)\s*%\s*change",
    ])
    if count is None and proceeds is None:
        return None
    return {
        "count": int(count) if count is not None else None,
        "count_change_pct": count_change,
        "proceeds_bil": proceeds,
        "proceeds_change_pct": proceeds_change,
    }


def _parse_bofa_bull_bear(text):
    clean = _clean(text)
    value = _parse_number_after(clean, [
        r"BofA Bull\s*&\s*Bear Indicator[^.]{0,160}?(?:sell signal at|unchanged at|to)\s+([0-9]+(?:\.[0-9]+)?)",
        r"BofA Bull\s*&\s*Bear Indicator[^.]{0,80}?from\s+[0-9]+(?:\.[0-9]+)?\s+to\s+([0-9]+(?:\.[0-9]+)?)",
        r"Bull\s*&\s*Bear Indicator[^.]{0,100}?\bto\s+([0-9]+(?:\.[0-9]+)?)",
    ])
    date_match = re.search(
        r"(?:DASHBOARD AS OF|data are as of)\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",
        clean,
        re.I,
    )
    date = None
    if date_match:
        try:
            date = datetime.strptime(date_match.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return {"value": value, "date": date} if value is not None else None


def _parse_cape(text):
    clean = _clean(text)
    return _parse_number_after(clean, [
        r"(?:Aug|August)\s+\d{1,2},\s*\d{4}[^0-9]{0,30}([0-9]+(?:\.[0-9]+)?)",
        r"Shiller P/E[^0-9]{0,50}([0-9]+(?:\.[0-9]+)?)",
    ])


def _parse_buffett(text):
    clean = _clean(text)
    return _parse_number_after(clean, [
        r"(?:current|latest)[^0-9]{0,60}([0-9]+(?:\.[0-9]+)?)\s*%",
        r"([0-9]+(?:\.[0-9]+)?)\s*%[^.]{0,40}(?:GDP|Buffett)",
    ])


def _parse_lei(text):
    clean = _clean(text)
    level = _parse_number_after(clean, [r"(?:to|at)\s+([0-9]+(?:\.[0-9]+)?)\s+in\s+(?:June|May|April)"])
    change = _parse_number_after(clean, [r"(?:first half|six months)[^0-9-]{0,40}(-?[0-9]+(?:\.[0-9]+)?)\s*%"])
    return level, change


def classify_indicator(value, *, red_if=None, yellow_if=None, missing_status="gray"):
    """Return a status using only explicit numeric predicates."""
    if value is None:
        return missing_status
    if red_if and red_if(value):
        return "red"
    if yellow_if and yellow_if(value):
        return "yellow"
    return "green"


def evaluate_hard_triggers(records, history):
    """Evaluate the seven user-facing hard triggers deterministically."""
    by_key = {r["key"]: r for r in records}

    def val(key):
        return _num(by_key.get(key, {}).get("value"))

    vix = val("vix")
    vix_hist = [_num(x.get("vix")) for x in history if _num(x.get("vix")) is not None]
    vix_trigger = vix is not None and vix > 25 and (not vix_hist or vix_hist[-1] > 25)

    margin_hist = [_num(x.get("margin_debt")) for x in history if _num(x.get("margin_debt")) is not None]
    margin = val("margin_debt")
    margin_series = (margin_hist + [margin]) if margin is not None else margin_hist
    margin_trigger = len(margin_series) >= 4 and all(
        margin_series[-i] < margin_series[-i - 1] for i in range(1, 4)
    )

    fg = val("fear_greed")
    fg_hist = [_num(x.get("fear_greed")) for x in history if _num(x.get("fear_greed")) is not None]
    fg_trigger = bool(fg_hist and fg_hist[-1] > 75 and fg is not None and fg < 50)

    ad = by_key.get("ad_line", {})
    ad_trigger = ad.get("hard_trigger") is True

    specs = [
        ("vix", "VIX 突破並站穩", "> 25 且連續紀錄仍在 25 以上", vix_trigger, vix is not None and vix > 20),
        ("margin_debt", "Margin Debt 月減", "連續 3 個月", margin_trigger, len(margin_series) >= 2 and margin_series[-1] < margin_series[-2]),
        ("hy_spread", "HY Spread 擴張", "> 4.5%", val("hy_spread") is not None and val("hy_spread") > 4.5, val("hy_spread") is not None and val("hy_spread") > 3.5),
        ("fear_greed", "Fear & Greed 從高位回落", ">75 跌回 <50", fg_trigger, bool(fg_hist and fg_hist[-1] > 75 and fg is not None)),
        ("ad_line", "A/D Line 頂背離", "S&P 新高但 A/D 不創新高", ad_trigger, ad.get("available") is False),
        ("bofa_bull_bear", "BofA Bull & Bear", "> 8.0", val("bofa_bull_bear") is not None and val("bofa_bull_bear") > 8, val("bofa_bull_bear") is not None and val("bofa_bull_bear") > 7),
        ("insider_ratio", "Insider Buy/Sell", "< 0.17", val("insider_ratio") is not None and val("insider_ratio") < 0.17, val("insider_ratio") is not None and val("insider_ratio") < 0.25),
    ]
    result = []
    for key, label, threshold, triggered, near in specs:
        available = by_key.get(key, {}).get("value") is not None or key == "ad_line" and ad.get("available") is not False
        result.append({
            "key": key, "label": label, "threshold": threshold,
            "status": "red" if triggered else "yellow" if near else "green" if available else "gray",
            "triggered": bool(triggered),
            "state_zh": "已觸發" if triggered else "接近／待確認" if near else "未觸發" if available else "資料不足",
        })
    return result


def build_atmosphere(current, fred_series, breadth, pages, *, generated_at=None):
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    today = generated_at[:10]
    mood = current or {}
    old = mood.get("atmosphere") or {}
    history = list(old.get("history") or [])[-179:]

    mm = mood
    vix = _num((mm.get("vix") or {}).get("current"))
    fg = _num((mm.get("fear_greed") or {}).get("index"))
    pcr = _num((mm.get("options") or {}).get("put_call_ratio"))
    pcr_date = (mm.get("options") or {}).get("asof") or today
    fred_hy = _num((fred_series.get("BAMLH0A0HYM2") or {}).get("value"))
    fred_curve = _num((fred_series.get("T10Y2Y") or {}).get("value"))
    fred_hy_date = (fred_series.get("BAMLH0A0HYM2") or {}).get("date")
    fred_curve_date = (fred_series.get("T10Y2Y") or {}).get("date")

    aaii = _parse_aaii_sentiment(pages.get("aaii_sentiment", ""))
    aaii_spread = (aaii["bullish"] - aaii["bearish"]
                   if aaii["bullish"] is not None and aaii["bearish"] is not None else None)
    allocation = _parse_aaii_allocation(pages.get("aaii_allocation", ""))
    naaim = _parse_naaim(pages.get("naaim", ""))
    finra_margin_series = _parse_finra_margin_debt(pages.get("finra_margin", ""))
    finra_margin = finra_margin_series[-1] if finra_margin_series else None
    margin_gdp = _parse_margin_gdp(pages.get("margin_gdp", ""))
    insider = _parse_gurufocus_ratio(pages.get("insider", ""))
    ipo_stats = _parse_ipo_stats(pages.get("ipo", ""))
    bofa_text = pages.get("bofa_viewpoint_july", "") or pages.get("bofa_viewpoint_june", "")
    bofa = _parse_bofa_bull_bear(bofa_text)
    cape = _parse_cape(pages.get("cape", ""))
    buffett = _parse_buffett(pages.get("buffett", ""))
    lei_level, lei_change = _parse_lei(pages.get("lei", ""))

    breadth_div = ((breadth.get("components") or {}).get("divergence") or {})
    breadth_date = (breadth.get("metadata") or {}).get("data_freshness", {}).get("latest_date")
    ad_available = False
    ad_note = "現有 breadth proxy 顯示健康對齊；NYSE 累積 A/D 線尚未接入，因此不把 proxy 當成硬觸發。"
    if breadth_div.get("data_available"):
        ad_note = "目前只有市場 breadth proxy，未直接取得 NYSE 累積 A/D 線；硬觸發維持待確認。"

    margin_values = [row["value"] for row in finra_margin_series]
    margin_red = len(margin_values) >= 4 and all(
        margin_values[-i] < margin_values[-i - 1] for i in range(1, 4)
    )
    margin_yellow = len(margin_values) >= 2 and margin_values[-1] < margin_values[-2]
    ipo_change_values = [
        value for value in (
            (ipo_stats or {}).get("count_change_pct"),
            (ipo_stats or {}).get("proceeds_change_pct"),
        ) if value is not None
    ]
    ipo_status = classify_indicator(
        max(ipo_change_values) if ipo_change_values else None,
        red_if=lambda x: x > 30,
        yellow_if=lambda x: x > 10,
    )
    records = [
        _record("vix", "short", "VIX", vix, today, "> 25", classify_indicator(vix, red_if=lambda x: x > 25, yellow_if=lambda x: x >= 20), "VIX 仍低於壓力區；單獨看不代表風險消失。", "CBOE/FRED via market_mood.json", interpretation="波動率仍在平靜區，短線沒有恐慌性去槓桿訊號。"),
        _record("fear_greed", "short", "CNN Fear & Greed", fg, today, ">75 → <50", classify_indicator(fg, red_if=lambda x: x < 50, yellow_if=lambda x: x >= 70), "恐懼與貪婪需搭配歷史方向；目前讀值未形成高位急跌觸發。", "CNN via market_mood.json", interpretation="情緒不是單向極端恐慌；若由高位快速跌破 50，才會升級為短線警報。"),
        _record("aaii_sentiment", "short", "AAII 投資人情緒", aaii_spread, today, "Bull − Bear < −20", classify_indicator(aaii_spread, red_if=lambda x: x < -20, yellow_if=lambda x: x < 0), "Bull/Bear 原始值或頁面尚未穩定取得。", "AAII", display=(f"B {aaii['bullish']:.1f}% / N {aaii['neutral']:.1f}% / B {aaii['bearish']:.1f}% (差 {aaii_spread:+.1f})" if all(aaii[k] is not None for k in ("bullish", "neutral", "bearish")) else None), interpretation="散戶多空差是情緒溫度計；負值代表悲觀擴大，但不等同市場必然下跌。"),
        _record("put_call", "short", "CBOE Equity Put/Call", pcr, pcr_date, "> 1.00", classify_indicator(pcr, red_if=lambda x: x > 1, yellow_if=lambda x: x > .85), "Put/Call 越高代表避險需求越重；目前沿用 Market Mood 的原始值或可用代理。", "CBOE/CNN via market_mood.json", interpretation="期權避險需求尚未到極端區，短線尚未出現明顯防守擁擠。"),
        _record("naaim_exposure", "short", "NAAIM Exposure", naaim, today, "> 90", classify_indicator(naaim, red_if=lambda x: x > 90, yellow_if=lambda x: x > 75), "NAAIM 公開頁可能延遲或受訂閱限制；沒有可靠讀值時保持空白。", "NAAIM", interpretation="主動管理人曝險若很高，代表市場對上行延續的共識偏擁擠；目前需先補齊公開讀值。"),
        _record("margin_debt", "mid", "FINRA Margin Debt", finra_margin["value"] if finra_margin else None,
                finra_margin["date"] if finra_margin else today, "月減連續 3 個月",
                "red" if margin_red else "yellow" if margin_yellow else "green" if finra_margin else "gray",
                "FINRA 月度 debit balance；連續下降才形成硬觸發。" if finra_margin else "FINRA 官方月度表尚未取得。",
                "FINRA", display=(f"${finra_margin['value']:,}M" if finra_margin else None),
                interpretation="保證金負債上升代表槓桿擴張；連續下降則代表去槓桿，需搭配價格與信用市場判讀。"),
        _record("margin_gdp", "mid", "Margin Debt / GDP", margin_gdp, today, "> 5%", classify_indicator(margin_gdp, red_if=lambda x: x > 5, yellow_if=lambda x: x > 4), "高槓桿提高回撤敏感度，但它是慢變指標。", "GuruFocus", interpretation="保證金負債相對 GDP 越高，市場越容易因價格下跌被動減倉；這是結構性脆弱度，不是即時賣點。"),
        _record("ipo_proceeds", "mid", "Renaissance IPO 發行量", (ipo_stats or {}).get("count"), today, "數量／募資額異常上升", ipo_status,
                "Renaissance 年初至今 IPO 統計；數量與募資額的同比變化用於判斷異常擴張。" if ipo_stats else "Renaissance IPO Stats 尚未取得。", "Renaissance Capital",
                display=(f"{ipo_stats['count']} 家 / ${ipo_stats['proceeds_bil']:.1f}B YTD" if ipo_stats and ipo_stats.get("count") is not None and ipo_stats.get("proceeds_bil") is not None else None),
                interpretation="IPO 數量或募資額快速擴張，代表資本市場風險胃納上升；需與估值和上市後表現合看。"),
        _record("insider_ratio", "mid", "Insider Buy/Sell Ratio", insider, today, "< 0.17", classify_indicator(insider, red_if=lambda x: x < .17, yellow_if=lambda x: x < .25), "內部人買賣比低於 0.17 才列為硬警報。", "GuruFocus", interpretation="內部人偏賣出是估值與信心的反向驗證；需觀察是否持續而非單月雜訊。"),
        _record("bofa_bull_bear", "mid", "BofA Bull & Bear", (bofa or {}).get("value"), (bofa or {}).get("date") or today, "> 8.0",
                classify_indicator((bofa or {}).get("value"), red_if=lambda x: x > 8, yellow_if=lambda x: x > 7),
                "BofA CIO Viewpoint 公開 PDF 的最新可驗證讀值。" if bofa else "BofA 最新公開 CIO Viewpoint 尚未取得。",
                "BofA/Merrill CIO Viewpoint", display=(f"{bofa['value']:.1f}" if bofa else None),
                interpretation="BofA Bull & Bear 高於 8 通常代表全球股市多頭擁擠，屬反向風險訊號；需注意報告日期。"),
        _record("hy_spread", "mid", "ICE BofA US HY OAS", fred_hy, fred_hy_date, "> 4.5%", classify_indicator(fred_hy, red_if=lambda x: x > 4.5, yellow_if=lambda x: x > 3.5), "信用利差仍是判斷風險是否擴散的核心中期訊號。", "FRED BAMLH0A0HYM2", display=f"{fred_hy:.2f}%" if fred_hy is not None else None, interpretation="高收益債利差仍低於壓力門檻時，表示信用市場尚未確認股市風險；一旦快速擴張，訊號權重會上升。"),
        _record("ad_line", "mid", "NYSE Advance/Decline Line", None, breadth_date or today, "S&P 新高但 A/D 不創新高", "gray", ad_note, "NYSE A/D + breadth proxy", interpretation="廣度資料目前只能作 proxy；沒有直接 NYSE 累積線，就不把『頂背離』判成已觸發。"),
        _record("buffett_indicator", "long", "Buffett Indicator", buffett, today, "> 200%", classify_indicator(buffett, red_if=lambda x: x > 200, yellow_if=lambda x: x > 150), "總市值／GDP 的方法差異很大；讀值只作估值溫度，不作短線賣點。", "CurrentMarketValuation", display=f"{buffett:.1f}%" if buffett is not None else None, interpretation="總市值相對 GDP 越高，長期預期報酬通常越受壓；它提醒再平衡，不負責抓頂。"),
        _record("cape", "long", "Shiller CAPE / PE10", cape, today, "> 30", classify_indicator(cape, red_if=lambda x: x > 30, yellow_if=lambda x: x > 25), "CAPE 位於高估值區時，應降低對未來報酬的樂觀假設。", "Multpl", interpretation="CAPE 是長期估值錨；高位意味著未來 1–3 年的安全邊際較薄，但不代表立即反轉。"),
        _record("yield_curve", "long", "10Y−2Y Treasury Curve", fred_curve, fred_curve_date, "< 0%", classify_indicator(fred_curve, red_if=lambda x: x < 0, yellow_if=lambda x: x < .25), "曲線已重新正斜率；仍需觀察是否伴隨成長與信用惡化。", "FRED T10Y2Y", display=f"{fred_curve:+.2f}%" if fred_curve is not None else None, interpretation="正斜率解除倒掛警報，但重新陡峭不必然代表景氣強勁；要與 LEI、信用利差合看。"),
        _record("lei", "long", "Conference Board US LEI", lei_change, today, "6 個月 < −2%", classify_indicator(lei_change, red_if=lambda x: x < -2, yellow_if=lambda x: x < 0), "LEI 頁面若無法解析，保持空白；不以新聞敘述代替月度值。", "Conference Board", display=(f"level {lei_level:.1f}; 6M {lei_change:+.1f}%" if lei_level is not None and lei_change is not None else None), interpretation="LEI 的連續下滑是景氣轉折的慢速確認；單月變化不應獨立驅動股市交易。"),
        _record("aaii_allocation", "long", "AAII 家庭股票配置", allocation, today, "> 70%", classify_indicator(allocation, red_if=lambda x: x > 70, yellow_if=lambda x: x > 65), "家庭股票配置是長期擁擠度指標；頁面定義若改變，需以來源欄核對。", "AAII", display=f"{allocation:.1f}%" if allocation is not None else None, interpretation="家庭股票配置過高代表未來新增買盤可能有限；適合用於再平衡，不適合拿來預測本週行情。"),
    ]

    # Preserve explicit adapter metadata for the UI and future source work.
    for record in records:
        if record["value"] is None and record["source_status"] == "missing":
            record["source_status"] = "unavailable"
        if record["key"] == "ad_line":
            record["available"] = ad_available
            record["hard_trigger"] = False

    history.append({
        "date": today,
        "vix": vix,
        "fear_greed": fg,
        "margin_debt": finra_margin["value"] if finra_margin else None,
        "hy_spread": fred_hy,
        "insider_ratio": insider,
        "bofa_bull_bear": (bofa or {}).get("value"),
    })
    history = history[-180:]
    triggers = evaluate_hard_triggers(records, history[:-1])
    triggered_count = sum(1 for item in triggers if item["triggered"])
    available_count = sum(1 for item in records if item["value"] is not None)
    status_counts = {status: sum(1 for item in records if item["status"] == status) for status in ("green", "yellow", "red", "gray")}

    # Human guidance is deterministic mapping from the trigger/alert counts;
    # it is intentionally not an investment-protocol verdict or position size.
    short_alerts = sum(1 for item in records if item["group"] == "short" and item["status"] in ("yellow", "red"))
    mid_alerts = sum(1 for item in records if item["group"] == "mid" and item["status"] in ("yellow", "red"))
    long_alerts = sum(1 for item in records if item["group"] == "long" and item["status"] in ("yellow", "red"))
    guidance = {
        "short": "維持核心倉位，先不因單一情緒讀值追價；若短期警報累積，再考慮保險。" if short_alerts < 2 else "短線訊號偏熱或偏脆弱，避免追價；用分批與有限成本保險管理回撤。",
        "mid": "信用尚未確認壓力擴散；維持分散，觀察槓桿、內部人與廣度是否同時惡化。" if mid_alerts < 2 else "中期訊號正在惡化，檢查高 beta、低品質信用與高槓桿曝險。",
        "long": "估值指標只提示降低預期報酬，採再平衡而非一次性離場。" if long_alerts < 2 else "長期估值／景氣訊號偏緊，逐步提高組合韌性與資產分散。",
    }
    priority = max(records, key=lambda item: (2 if item["status"] == "red" else 1 if item["status"] == "yellow" else 0, item["value"] is not None))
    if not any(item["status"] in ("yellow", "red") for item in records):
        priority = next((item for item in records if item["value"] is not None), records[0])

    return {
        "version": "1.0",
        "method": "deterministic_thresholds_v1",
        "generated_at": generated_at,
        "indicator_count": len(records),
        "available_count": available_count,
        "status_counts": status_counts,
        "groups": {"short": 5, "mid": 7, "long": 5},
        "indicators": records,
        "hard_triggers": {
            "items": triggers,
            "triggered_count": triggered_count,
            "total": len(triggers),
            "sell_staging_threshold": "3+ simultaneously",
        },
        "guidance": guidance,
        "top_attention": {
            "key": priority["key"], "name": priority["name"],
            "status": priority["status"], "reason_zh": priority["interpretation_zh"],
        },
        "data_quality": {
            "available": available_count, "total": len(records),
            "unavailable_keys": [item["key"] for item in records if item["value"] is None],
            "fetch_errors": pages.get("_fetch_errors", {}),
            "note_zh": "未取得的原始來源維持 ⚪/資料不足，不納入已觸發計數。",
        },
        "history": history,
    }


def main():
    parser = argparse.ArgumentParser(description="Deterministic market-atmosphere dashboard producer")
    parser.add_argument("--output", default=str(ROOT / "Dashboard/market_mood.json"))
    parser.add_argument("--offline", action="store_true", help="use only local market_mood/FRED/breadth caches")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    current, _mood, fred_series, breadth = _local_inputs(args.output)
    pages = _external_pages(args.offline)
    atmosphere = build_atmosphere(current, fred_series, breadth, pages)
    payload = current or {"version": "1.0"}
    payload["atmosphere"] = atmosphere
    _write_atomic(args.output, payload)
    print(json.dumps(atmosphere, ensure_ascii=False, indent=2))
    if not args.json_only:
        print(f"\n→ Market Atmosphere {atmosphere['available_count']}/{atmosphere['indicator_count']} "
              f"available │ hard triggers {atmosphere['hard_triggers']['triggered_count']}/7 │ → {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
