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
                       filter_hk_cn=True, return_stats=False):
    """純資料函式 — 給 dashboard_server.py 的 endpoint 用。
    回傳 list[dict]，每筆 {time, time_iso, sender, text, tickers[]}。
    DB 不存在或無資料 → 回 []（caller 自己判斷 available）。

    filter_hk_cn=True 時自動丟掉 HK/A 股相關推播（_is_hk_cn_related 命中）。
    return_stats=True 時改回 (items, stats)，stats 含 filtered_hk_cn 計數。"""
    db_paths = glob.glob(MSG_DB_PATTERN)
    if not db_paths:
        return ([], {"filtered_hk_cn": 0, "scanned": 0}) if return_stats else []

    rows = []
    for db_path in db_paths:
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.execute(
                "SELECT time, sender, element_descriptions "
                "FROM message ORDER BY time DESC LIMIT 200"
            )
            rows.extend(cur.fetchall())
            conn.close()
        except sqlite3.Error:
            continue

    rows.sort(key=lambda r: r[0], reverse=True)

    out = []
    filtered_hk_cn = 0
    scanned = 0
    for time_, sender, desc in rows:
        if not desc:
            continue
        text = desc.strip()
        if keyword and keyword not in text:
            continue
        scanned += 1
        if filter_hk_cn:
            matched, _reason = _is_hk_cn_related(text)
            if matched:
                filtered_hk_cn += 1
                continue
        item = {
            "time":     float(time_) if time_ else None,
            "time_iso": _ts_iso(time_),
            "sender":   sender,
            "text":     text,
        }
        if with_tickers:
            item["tickers"] = extract_tickers(text)
        out.append(item)
        if len(out) >= limit:
            break
    if return_stats:
        return out, {"filtered_hk_cn": filtered_hk_cn, "scanned": scanned}
    return out


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
