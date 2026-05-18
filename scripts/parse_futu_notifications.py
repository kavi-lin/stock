#!/usr/bin/env python3
"""
parse_futu_notifications.py
解析富途牛牛推播（IM 系統訊息頻道）

用法：
  python3 parse_futu_notifications.py                  # CLI list (default 10)
  python3 parse_futu_notifications.py -n 5 -k 英偉達   # 篩選關鍵字
  python3 parse_futu_notifications.py --json -n 5      # JSON 輸出（含 ticker 辨識）

資料來源: ~/Library/Containers/cn.futu.Niuniu/.../msg_0.db
"""

import datetime
import glob
import json
import os
import re
import sqlite3
import sys

FUTU_CONTAINER = os.path.expanduser(
    "~/Library/Containers/cn.futu.Niuniu/Data"
)
MSG_DB_PATTERN = os.path.join(
    FUTU_CONTAINER,
    "Documents/com_tencent_imsdk_data/*/msg_0.db"
)

# ── 中文公司名 → US ticker 對照表 ──────────────────────────────────────
# 富途推播以中文簡體為主，這裡涵蓋常出現在頭條的標的。多寫法並列同一 ticker。
# Order matters: longer keys first to avoid `蘋果` 命中 `蘋果汽車` 之類短語誤判。
_NAME_TO_TICKER = {
    # Mag-7 / mega-tech
    "英偉達": "NVDA", "輝達": "NVDA", "Nvidia": "NVDA",
    "谷歌": "GOOGL", "Google": "GOOGL", "Alphabet": "GOOGL",
    "微軟": "MSFT", "Microsoft": "MSFT",
    "特斯拉": "TSLA", "Tesla": "TSLA",
    "蘋果公司": "AAPL", "蘋果": "AAPL", "Apple": "AAPL",
    "亞馬遜": "AMZN", "Amazon": "AMZN",
    "元宇宙": "META", "Meta": "META", "臉書": "META",
    # Semis / hardware
    "台積電": "TSM", "台積": "TSM",
    "美光": "MU",
    "高通": "QCOM",
    "博通": "AVGO",
    "英特爾": "INTC",
    "超微": "AMD", "AMD": "AMD",
    "閃迪": "SNDK",
    "天弘科技": "CLS", "Celestica": "CLS",
    "戴爾": "DELL",
    "惠普": "HPQ",
    "思科": "CSCO",
    "ARM": "ARM",
    "甲骨文": "ORCL", "Oracle": "ORCL",
    # SaaS / internet
    "賽富時": "CRM", "Salesforce": "CRM",
    "奈飛": "NFLX", "網飛": "NFLX",
    "Snowflake": "SNOW",
    "Adobe": "ADBE",
    "Palantir": "PLTR",
    "Shopify": "SHOP",
    # China ADR
    "阿里巴巴": "BABA", "阿里": "BABA",
    "京東": "JD",
    "拼多多": "PDD",
    "百度": "BIDU",
    "網易": "NTES",
    "蔚來": "NIO",
    "理想汽車": "LI", "理想": "LI",
    "小鵬汽車": "XPEV", "小鵬": "XPEV",
    "比亞迪": "BYDDY",
    # Financials
    "高盛": "GS",
    "摩根大通": "JPM",
    "摩根士丹利": "MS",
    "花旗": "C",
    "富國銀行": "WFC",
    "美國銀行": "BAC",
    "伯克希爾": "BRK.B", "巴菲特": "BRK.B",
    # Energy / industrial
    "雪佛龍": "CVX",
    "埃克森": "XOM",
    "Bloom Energy": "BE",
    "波音": "BA",
    "洛克希德": "LMT",
    "雷神": "RTX",
    "卡特彼勒": "CAT", "開拓重工": "CAT",
    # Consumer
    "沃爾瑪": "WMT",
    "麥當勞": "MCD",
    "可口可樂": "KO",
    "百事": "PEP",
    "寶潔": "PG",
    "迪士尼": "DIS",
    "Costco": "COST",
    # Healthcare
    "強生": "JNJ",
    "輝瑞": "PFE",
    "默克": "MRK",
    "禮來": "LLY",
    "諾和諾德": "NVO",
    # Crypto / others
    "比特幣": "BTC", "Bitcoin": "BTC",
    "以太坊": "ETH",
    "Coinbase": "COIN",
    "MicroStrategy": "MSTR",
    "Palantir": "PLTR",
}

# 把 dict 排序：長 key 先比對，避免短 key 吃掉長 key 的命中
_NAME_PATTERNS = sorted(_NAME_TO_TICKER.items(), key=lambda kv: -len(kv[0]))

# 英文 ticker regex：2-5 字大寫字母，前後不接字母/數字。
# 過濾常見英文 stopword 與單位簡寫，降低誤判（NEWS/AND/THE/CEO/AI/etc）。
_EN_TICKER_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z]{2,5})(?![A-Za-z0-9])")
_EN_TICKER_STOPWORDS = {
    "AI", "AND", "API", "APP", "ARM", "BUT", "CDC", "CEO", "CFO", "CIA",
    "COO", "CPI", "CTO", "DOJ", "ECB", "EPS", "ETF", "EU", "EUR", "FBI",
    "FDA", "FED", "FOMC", "FOR", "FY", "GDP", "GMT", "GOP", "ID", "IPO",
    "IRA", "IRS", "ISM", "IT", "JPY", "KPI", "M&A", "NATO", "NBA", "NFL",
    "NEW", "OECD", "OK", "OPEC", "OS", "PCE", "PMI", "PPI", "Q1", "Q2",
    "Q3", "Q4", "RSI", "SEC", "SP", "TBD", "THE", "TLT", "UK", "UN", "US",
    "USA", "USD", "VAT", "VIX", "VS", "WHO", "WSJ", "YOY", "YTD", "QOQ",
    "POS", "RD", "ROE", "ROI", "ROIC", "ATH", "ATL", "DAX", "FTSE",
    "NDX", "SPX", "DXY", "ESG", "AGM", "GAAP", "FCF", "NIM",
    # 蛋白/生物學/醫學縮寫（常出現在生技推播但非股票代碼）
    "RAS", "DNA", "RNA", "MRNA", "TNF", "VEGF", "PD", "PDL",
    # 其它常見非 ticker
    "LED", "LCD", "OLED", "SUV", "EV", "AC", "DC",
}

# ── HK / 中國 A 股相關內容過濾 ──────────────────────────────────────────
# 富途推播以中港 A 股為主要受眾，但本系統聚焦美股，需把與 HK 市場 / 中國市場
# 直接相關的推播濾掉。策略分兩層：
#   (1) HARD 關鍵字：明確指向 HK/CN 市場，命中即過濾
#   (2) HK/CN 唯一公司名：不在 US 名單內、屬於 HK 或 A 股本土上市
# 雙重上市名（阿里/京東/蔚來/理想/小鵬/比亞迪 等）保留，因可能是 US ADR 新聞；
# 若上下文同時帶有 HARD 關鍵字才會被過濾。
_HK_CN_HARD_KEYWORDS = [
    # HK
    "港股", "恒生", "恆生", "恒指", "恆指", "港交所", "港股通", "港元", "藍籌",
    "南向資金", "南下資金",
    # CN A-share / market
    "A股", "Ａ股", "滬深", "上證", "深證", "創業板", "科創板",
    "滬指", "深指", "創指", "北證", "新三板", "中金所", "中概股",
    "人民幣", "離岸人民幣", "在岸人民幣",
    # 交易所代碼後綴
    ".HK", ".SH", ".SZ",
]
# HK / CN 本土主要上市公司（不在 _NAME_TO_TICKER 美股名單內）
_HK_CN_ONLY_NAMES = [
    # HK 科技
    "騰訊", "美團", "小米", "快手", "網易雲音樂", "京東健康", "京東物流",
    # 中國電信 / 公用
    "中國移動", "中國電信", "中國聯通", "中國海油", "中國石化", "中國石油",
    "中石油", "中石化", "中海油",
    # 銀行 / 金融
    "工商銀行", "建設銀行", "農業銀行", "中國銀行", "招商銀行", "交通銀行",
    "中信銀行", "民生銀行", "興業銀行", "浦發銀行", "光大銀行",
    "中國人壽", "中國平安", "平安保險", "中國太保", "新華保險",
    "中信證券", "華泰證券", "海通證券", "國泰君安", "中金公司",
    # 白酒 / 消費
    "貴州茅台", "茅台", "五糧液", "瀘州老窖", "山西汾酒", "洋河",
    "海天味業", "海天", "伊利", "蒙牛",
    # 地產 / 基建
    "萬科", "保利", "碧桂園", "恒大", "融創", "華潤置地", "龍湖", "新城控股",
    "中國建築", "中國中車", "中國中鐵", "中國交建",
    # A 股科技 / 製造
    "寧德時代", "京東方", "海康威視", "立訊精密", "歌爾股份",
    "中芯國際", "華虹半導體", "韋爾股份", "兆易創新",
    "比亞迪電子", "美的集團", "格力電器", "海爾智家",
    # 其他知名 A/HK
    "三一重工", "三花智控", "牧原股份", "邁瑞醫療", "藥明康德", "藥明生物",
    "恒瑞醫藥", "智飛生物", "金域醫學",
]
# HK/CN 數字代碼樣式：5 位 HK code（前置 0）；後綴 .HK / .SH / .SZ 已在 HARD list
_HK_CODE_RE = re.compile(r"(?<!\d)(0\d{4})(?!\d)")           # 00700 / 09988 etc.
_CN_CODE_RE = re.compile(r"(?<!\d)([036]\d{5})(?!\d)")       # 600519 / 300750 / 000858


# ── 廣告 / 系統通知過濾 ───────────────────────────────────────────────
# Break News 用：只收真實新聞，廣告、教學、系統推播全部丟。
_AD_HARD_KEYWORDS = [
    # 系統 / 富途 自家服務
    "您關注的", "更新了資訊", "富途早晚報", "富途研選", "富途精選",
    "認證投資者", "申請開通", "立即查看", "立即下載", "立即體驗",
    # 開戶 / 推廣
    "開戶", "贈金", "贈股", "禮券", "推薦碼", "邀請好友", "新人禮",
    "限時優惠", "限時福利", "免費領取", "首充", "充值",
    # 行銷 CTA
    "報名參加", "報名鏈接", "立即報名", "立即購買", "立即訂閱",
    "掃碼領取", "點擊參與", "點擊查看詳情",
    # 直播 / 教學
    "直播間", "直播預告", "今晚直播", "在線直播", "視頻教程",
    "牛友圈", "課堂", "課程", "公開課", "投教",
    # 衍生品 / 平台廣告
    "牛牛繁星", "牛人榜", "moomoo",
]
# 教學 / 知識文 — headline 結尾帶問號且無 ticker 多為點閱誘餌
_HOWTO_PATTERNS = [
    re.compile(r"如何.*?[？?]$"),
    re.compile(r"怎麼.*?[？?]$"),
    re.compile(r"教你.*"),
    re.compile(r"一文(讀懂|看懂|搞懂).*"),
    re.compile(r"^\d+\s*(個|大|個方法|個技巧).*"),
    re.compile(r".*技巧$"),
]


def _is_ad(text):
    """True 即視為廣告 / 系統通知 / 教學內容，predicate 排序由廉價到昂貴。
    回傳 (matched, reason) 方便 debug。"""
    if not text:
        return True, "empty"
    stripped = text.strip()
    if len(stripped) < 10:
        return True, "too_short"
    for kw in _AD_HARD_KEYWORDS:
        if kw in stripped:
            return True, f"keyword:{kw}"
    for pat in _HOWTO_PATTERNS:
        if pat.search(stripped):
            return True, "howto_pattern"
    return False, None


def _is_hk_cn_related(text):
    """True 即視為 HK/中股相關，predicate 命中順序由廉價到昂貴。
    回傳 (matched, reason) 方便 debug。"""
    if not text:
        return False, None
    for kw in _HK_CN_HARD_KEYWORDS:
        if kw in text:
            return True, f"keyword:{kw}"
    for name in _HK_CN_ONLY_NAMES:
        if name in text:
            return True, f"name:{name}"
    if _HK_CODE_RE.search(text):
        return True, "hk_code"
    if _CN_CODE_RE.search(text):
        return True, "cn_code"
    return False, None


def extract_tickers(text):
    """從推播文字抽 ticker — 中文 dict 命中優先；剩餘文字用英文 regex 補。
    回傳排序後 unique list（最多 5 筆）。"""
    if not text:
        return []
    found = []
    seen = set()
    remaining = text
    # 中文命中：找到後從 remaining 裁掉，避免英文 regex 重抓相同片段
    for name, tk in _NAME_PATTERNS:
        if name in remaining:
            if tk not in seen:
                found.append(tk)
                seen.add(tk)
            remaining = remaining.replace(name, " ")
    # 英文 ticker：剩餘文字（含中英混排）跑 regex，過濾 stopword
    for m in _EN_TICKER_RE.finditer(remaining):
        candidate = m.group(1)
        if candidate in _EN_TICKER_STOPWORDS:
            continue
        if candidate in seen:
            continue
        found.append(candidate)
        seen.add(candidate)
        if len(found) >= 5:
            break
    return found[:5]


def _ts_iso(epoch):
    try:
        return datetime.datetime.fromtimestamp(float(epoch)).isoformat(
            timespec="seconds"
        )
    except Exception:
        return None


def _ts_str(epoch):
    try:
        return datetime.datetime.fromtimestamp(float(epoch)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    except Exception:
        return str(epoch)


def load_notifications(limit=10, keyword=None, with_tickers=True,
                       filter_hk_cn=True, filter_ads=False,
                       require_us_ticker=False, return_stats=False):
    """純資料函式 — 給 dashboard_server.py 的 endpoint 用。
    回傳 list[dict]，每筆 {time, time_iso, sender, text, tickers[]}。
    DB 不存在或無資料 → 回 []（caller 自己判斷 available）。

    filter_hk_cn=True 時自動丟掉 HK/A 股相關推播（_is_hk_cn_related 命中）。
    filter_ads=True 時丟掉廣告 / 教學 / 系統通知（_is_ad 命中）。
    require_us_ticker=True 時只保留 extract_tickers 至少一檔 US ticker 的推播。
    return_stats=True 時改回 (items, stats)，stats 含 filtered_* 各分項計數。"""
    db_paths = glob.glob(MSG_DB_PATTERN)
    stats = {"filtered_hk_cn": 0, "filtered_ads": 0, "filtered_no_ticker": 0, "scanned": 0}
    if not db_paths:
        return ([], stats) if return_stats else []

    rows = []
    for db_path in db_paths:
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.execute(
                "SELECT time, sender, element_descriptions "
                "FROM message ORDER BY time DESC LIMIT 500"
            )
            rows.extend(cur.fetchall())
            conn.close()
        except sqlite3.Error:
            continue

    rows.sort(key=lambda r: r[0], reverse=True)

    out = []
    for time_, sender, desc in rows:
        if not desc:
            continue
        text = desc.strip()
        if keyword and keyword not in text:
            continue
        stats["scanned"] += 1
        if filter_ads:
            matched, _reason = _is_ad(text)
            if matched:
                stats["filtered_ads"] += 1
                continue
        if filter_hk_cn:
            matched, _reason = _is_hk_cn_related(text)
            if matched:
                stats["filtered_hk_cn"] += 1
                continue
        tickers = extract_tickers(text) if (with_tickers or require_us_ticker) else []
        if require_us_ticker and not tickers:
            stats["filtered_no_ticker"] += 1
            continue
        item = {
            "time":     float(time_) if time_ else None,
            "time_iso": _ts_iso(time_),
            "sender":   sender,
            "text":     text,
        }
        if with_tickers:
            item["tickers"] = tickers
        out.append(item)
        if len(out) >= limit:
            break
    if return_stats:
        return out, stats
    return out


# ── Break News adapter ────────────────────────────────────────────────
# Returns items in fetch_news_rss.fetch_feed shape so scripts/break_news/poller.py
# can merge Futu pushes with RSS items into the same downstream pipeline.
# Strict pre-filter: US ticker required, no HK/CN, no ads.

def _futu_headline(text):
    """Build a short headline from a Futu push body."""
    # Trim trailing link marker '>>' / '》》'
    cleaned = text.strip().rstrip(">》 ").strip()
    # Take first sentence-ish segment
    first = re.split(r"[。！；\n]", cleaned, maxsplit=1)[0]
    first = first.strip(" ，,")
    if len(first) > 120:
        first = first[:120] + "…"
    return first or cleaned[:120]


def _futu_url(time_epoch, text):
    """Synthetic URL for dedupe + storage. Futu pushes have no native URL."""
    import hashlib as _h
    h = _h.sha1((str(time_epoch) + "||" + text[:60]).encode("utf-8")).hexdigest()[:12]
    return f"futu://push/{h}"


# ── zh-aware shallow score (Futu pushes are mostly 繁中/簡中) ──────────
# The English keyword scorer in news/scripts/stage1_triage.py returns 0 for
# zh-only headlines, so every Futu item shows up as 0.0 in the UI. Add a
# parallel zh scorer for them.
_ZH_POS = [
    ("飆升", 3.0), ("暴漲", 3.0), ("狂飆", 3.0), ("漲停", 3.0),
    ("大漲", 2.0), ("漲超", 2.0), ("漲幅", 1.5), ("再破頂", 2.5),
    ("創新高", 2.5), ("新高", 1.5), ("創歷史新高", 3.0),
    ("超預期", 2.0), ("勝預期", 1.5), ("優於預期", 2.0),
    ("看多", 1.5), ("利多", 1.5), ("利好", 1.5), ("受惠", 1.0),
    ("上修", 1.5), ("調升", 1.5), ("上調", 1.5),
    ("買進", 1.5), ("加碼", 1.5),
    ("強勢", 1.0), ("反彈", 1.0), ("拉升", 1.5),
    ("績後勁升", 2.5), ("拉抬", 1.5), ("漲", 0.8),
]
_ZH_NEG = [
    ("暴跌", -3.0), ("崩跌", -3.0), ("跌停", -3.0), ("重挫", -2.5),
    ("大跌", -2.0), ("跌超", -2.0), ("跌幅", -1.5),
    ("創新低", -2.5), ("破底", -2.0),
    ("不及預期", -2.0), ("低於預期", -2.0), ("失望", -1.5),
    ("看空", -1.5), ("利空", -1.5), ("利淡", -1.5), ("利空消息", -2.0),
    ("下修", -1.5), ("調降", -1.5), ("下調", -1.5),
    ("賣出", -1.5), ("減持", -1.0),
    ("疲軟", -1.0), ("回檔", -1.0), ("修正", -0.8),
    ("違約", -2.5), ("破產", -3.0), ("退市", -2.5),
    ("地緣風險", -1.5), ("斷供", -2.0), ("衰退", -1.5),
    ("跌", -0.8),
]
_ZH_BINARY = [
    "選舉", "公投", "決議", "併購", "收購", "破產", "聯儲", "FOMC",
    "升息", "降息",
]


def score_zh(text):
    """Return shallow score (-5..+5) for zh text. Word-boundary not needed
    because zh has no whitespace separators — substring match is canonical."""
    if not text:
        return 0.0
    score = 0.0
    pos_hits = 0
    neg_hits = 0
    for word, w in _ZH_POS:
        if word in text:
            score += w
            pos_hits += 1
    for word, w in _ZH_NEG:
        if word in text:
            score += w
            neg_hits += 1
    # Cap +/-5, half-step rounding
    score = max(-5.0, min(5.0, round(score * 2) / 2))
    return score


def is_zh_binary(text):
    if not text:
        return False
    return any(kw in text for kw in _ZH_BINARY)


def _futu_fingerprint(headline, tickers):
    """zh-CN-safe fingerprint. The RSS helper `headline_fingerprint` only keeps
    [a-z0-9] tokens — zh headlines collapse to "" or noise like "20", causing
    every Futu push to dedupe-collide. Build a stable string from ticker set
    plus a hash of the headline so dedupe stays per-headline."""
    import hashlib as _h
    tk = ",".join(sorted(set((t or "").upper() for t in (tickers or []))))
    body = (headline or "").strip()
    body_hash = _h.sha1(body.encode("utf-8")).hexdigest()[:10]
    return f"futu:{tk}:{body_hash}"


def load_for_break_news(window_hours=6, max_items=50):
    """Return Futu pushes in fetch_news_rss.fetch_feed shape — strict US-news filter:
      - drop HK / A-share related
      - drop ads / promotions / system notices / how-to clickbait
      - require at least one US ticker (via _NAME_TO_TICKER + _EN_TICKER_RE)
    Each item: {headline, url, raw_summary, source, source_credibility,
                published, _fp, _dt, tickers}
    The _fp / _dt fields match what news/fetch_news_rss.fetch_feed emits so
    downstream dedupe + time-window code reuses without change."""
    items, stats = load_notifications(
        limit=max_items,
        with_tickers=True,
        filter_hk_cn=True,
        filter_ads=True,
        require_us_ticker=True,
        return_stats=True,
    )
    if not items:
        return [], stats

    cutoff_epoch = datetime.datetime.now().timestamp() - window_hours * 3600
    out = []
    for it in items:
        t = it.get("time")
        if t is None or t < cutoff_epoch:
            continue
        text = it["text"]
        headline = _futu_headline(text)
        dt = datetime.datetime.fromtimestamp(t).astimezone()
        tickers = it.get("tickers", [])
        zh_score = score_zh(headline + " " + text[:300])
        zh_binary = is_zh_binary(headline)
        out.append({
            "headline": headline,
            "url": _futu_url(t, text),
            "raw_summary": text[:500],
            "source": "Futu Push",
            "source_credibility": "MEDIUM",
            "published": dt.isoformat(timespec="seconds"),
            "_fp": _futu_fingerprint(headline, tickers),
            "_dt": dt,
            "tickers": tickers,
            "_zh_score": zh_score,
            "_zh_binary": zh_binary,
        })
    stats["window_kept"] = len(out)
    return out, stats


def is_available():
    """檢查富途 DB 路徑是否存在 — 給 endpoint 區分『未安裝』 vs 『安裝但暫時無新推播』。"""
    return bool(glob.glob(MSG_DB_PATTERN))


def _print_cli(limit, keyword, filter_hk_cn):
    items, stats = load_notifications(
        limit=limit, keyword=keyword, filter_hk_cn=filter_hk_cn, return_stats=True,
    )
    if not is_available():
        print("❌ 找不到富途 IM 資料庫")
        sys.exit(1)
    print(f"\n{'='*65}")
    title = "  富途牛牛推播通知"
    if keyword:        title += f" (篩選: {keyword})"
    if filter_hk_cn:   title += "  [HK/A 股已過濾]"
    print(title)
    print(f"{'='*65}")
    if not items:
        print("  （無符合條件的推播）")
    for it in items:
        ticker_tag = f"  [{', '.join(it['tickers'])}]" if it.get("tickers") else ""
        print(f"\n🔔 {_ts_str(it['time'])}{ticker_tag}")
        print(f"   {it['text']}")
    print(f"\n{'='*65}")
    print(f"共 {len(items)} 筆"
          + (f"（已過濾 HK/A 股 {stats['filtered_hk_cn']} 筆）" if filter_hk_cn else "")
          + f" / 掃描 {stats['scanned']}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="富途牛牛推播解析器")
    parser.add_argument("-n", "--limit", type=int, default=10, help="顯示幾筆（預設10）")
    parser.add_argument("-k", "--keyword", type=str, default=None, help="關鍵字過濾")
    parser.add_argument("--json", action="store_true", help="輸出 JSON（含 ticker 辨識）")
    parser.add_argument("--no-filter", action="store_true",
                        help="不過濾 HK/A 股相關推播（預設會過濾）")
    args = parser.parse_args()
    filter_hk_cn = not args.no_filter

    if args.json:
        items, stats = load_notifications(
            limit=args.limit, keyword=args.keyword,
            filter_hk_cn=filter_hk_cn, return_stats=True,
        )
        payload = {
            "available":      is_available(),
            "filter_hk_cn":   filter_hk_cn,
            "filtered_count": stats["filtered_hk_cn"],
            "scanned":        stats["scanned"],
            "notifications":  items,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_cli(args.limit, args.keyword, filter_hk_cn)
