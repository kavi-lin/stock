#!/usr/bin/env python3
"""
parse_firstrade_notifications.py — Phase 1 discovery (v0.1)

讀 macOS NotificationCenter DB，列出所有來源 app + sample notification body，
協助辨識 Firstrade trade-confirmation push 的真實格式。

前置條件（**重要**）：
  System Settings → Privacy & Security → Full Disk Access → 加入你的 Terminal.app
  （iTerm 用戶就加 iTerm.app）→ **重啟 Terminal**。
  否則 sqlite3 會因為 TCC 拒絕讀取 DB（unable to open database file）。

用法：
  # 最近 7 天所有 app 的 push 數量 + 最近 30 筆樣本
  python3 scripts/parse_firstrade_notifications.py --hours 168 -n 30

  # 鎖定 firstrade 關鍵字（filter by app id / title / body）
  python3 scripts/parse_firstrade_notifications.py -k firstrade --hours 720 -n 50

  # 看純文字 dump 不解 plist（debug 用）
  python3 scripts/parse_firstrade_notifications.py --raw-blob -n 5
"""

import argparse
import datetime
import os
import plistlib
import shutil
import sqlite3
import sys
import tempfile

NC_DB = os.path.expanduser(
    "~/Library/Group Containers/group.com.apple.usernoted/db2/db"
)
# Apple NSDate 用 2001-01-01 UTC 為 epoch
NSDATE_EPOCH = datetime.datetime(2001, 1, 1).timestamp()


def _ts(ns_date):
    """NSDate 秒數（自 2001-01-01）→ 本地 ISO 字串"""
    if ns_date is None:
        return None
    try:
        return datetime.datetime.fromtimestamp(
            NSDATE_EPOCH + float(ns_date)
        ).isoformat(timespec="seconds")
    except Exception:
        return str(ns_date)


def _unpack(blob):
    """record.data BLOB 是 binary plist（NSKeyedArchiver 可能 wrap）。
    回傳 dict / list / None；解碼失敗回 {"_decode_error": ...}。"""
    if not blob:
        return None
    try:
        return plistlib.loads(blob)
    except Exception as e:
        return {"_decode_error": str(e), "_blob_size": len(blob)}


def _extract_title_body(plist):
    """嘗試從 plist 抽出 title / body / subtitle。
    macOS NotificationCenter 會把 UNNotificationRequest 包進 NSKeyedArchiver。
    常見 key:
      - 'req' (dict)：直接 'titl'/'body'/'subt'
      - '$objects' (list)：NSKeyedArchiver 物件圖 — 字串散落在 list 中
    回傳 (title, body, subtitle)。
    """
    if not isinstance(plist, dict):
        return None, None, None

    # Path 1: 'req' 直接是 dict
    req = plist.get("req")
    if isinstance(req, dict):
        return req.get("titl"), req.get("body"), req.get("subt")

    # Path 2: NSKeyedArchiver $objects list — 撈所有 short str candidate
    objs = plist.get("$objects")
    if isinstance(objs, list):
        # 過濾出可讀字串（非 NSDictionary 內部 key 那種短碼）
        BAD_TOKENS = {
            "$null", "NSDictionary", "NSMutableDictionary", "NSArray",
            "NSMutableArray", "NSString", "NSMutableString", "NSDate",
            "NSData", "NSNumber", "NSURL", "NS.string", "NS.objects",
            "NS.keys", "NS.time",
        }
        candidates = []
        for o in objs:
            if isinstance(o, str) and 1 < len(o) < 500 and o not in BAD_TOKENS:
                # 排除明顯 plist 內部 key（短全大寫）
                if o.startswith("$") or (o.isupper() and len(o) <= 8):
                    continue
                candidates.append(o)
        # 直觀經驗：title 通常 < 80 字，body 較長；前幾個有意義字串多半是 app
        # name / title / body / subtitle
        title = candidates[1] if len(candidates) > 1 else None
        body = candidates[2] if len(candidates) > 2 else None
        subtitle = candidates[3] if len(candidates) > 3 else None
        return title, body, subtitle

    return None, None, None


def discover(keyword=None, limit=30, since_hours=168, raw_blob=False):
    if not os.path.exists(NC_DB):
        sys.exit(f"❌ NotificationCenter DB 找不到：{NC_DB}")

    # 複製到 tmp 避免 -wal/-shm journal 卡鎖
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    try:
        shutil.copy(NC_DB, tmp)
    except PermissionError:
        sys.exit(
            "❌ PermissionError 讀 DB —\n"
            "   你的 Terminal/Python 沒有 Full Disk Access。\n"
            "   修法：System Settings → Privacy & Security → Full Disk Access\n"
            "       → 加入 Terminal.app（或 iTerm.app）→ 重啟 Terminal\n"
        )
    except Exception as e:
        sys.exit(f"❌ 複製 DB 失敗：{e}")

    try:
        conn = sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
    except sqlite3.OperationalError as e:
        sys.exit(f"❌ sqlite open 失敗：{e}")

    cutoff_ns = (
        datetime.datetime.now().timestamp() - since_hours * 3600
    ) - NSDATE_EPOCH

    # 1) App 分布
    print("=" * 72)
    print(f"  macOS NotificationCenter — 最近 {since_hours}h 各 app push 計數")
    print("=" * 72)
    try:
        rows = conn.execute(
            """
            SELECT a.identifier, COUNT(*) as n
            FROM record r LEFT JOIN app a ON r.app_id = a.app_id
            WHERE r.delivered_date > ?
            GROUP BY a.identifier ORDER BY n DESC
            """,
            (cutoff_ns,),
        ).fetchall()
    except sqlite3.OperationalError as e:
        sys.exit(f"❌ schema 不符（macOS 版本差異？）：{e}")

    if not rows:
        print(f"  （沒有 {since_hours}h 內的 push）")
    for ident, n in rows:
        marker = ""
        if ident:
            low = ident.lower()
            if "firstrade" in low:
                marker = " ← FIRSTRADE 命中"
            elif "fst" in low or "trade" in low or "broker" in low:
                marker = " ← 可疑（含 fst/trade/broker）"
        print(f"  {n:5} | {ident or '(null)'}{marker}")
    print()

    # 2) Sample notifications
    print(f"--- 樣本 (keyword={keyword!r}, limit={limit}) ---")
    samples = conn.execute(
        """
        SELECT a.identifier, r.delivered_date, r.data, r.uuid
        FROM record r LEFT JOIN app a ON r.app_id = a.app_id
        WHERE r.delivered_date > ?
        ORDER BY r.delivered_date DESC
        LIMIT ?
        """,
        (cutoff_ns, limit * 5 if keyword else limit),
    ).fetchall()

    shown = 0
    for ident, ts, blob, uuid in samples:
        plist = _unpack(blob)
        title, body, subtitle = _extract_title_body(plist)

        # keyword filter — 命中任一欄位即顯示
        if keyword:
            kw = keyword.lower()
            haystack = " ".join(
                str(x or "")
                for x in (ident, title, body, subtitle)
            ).lower()
            if kw not in haystack:
                continue

        print(f"\n[{_ts(ts)}] {ident or '(null)'}")
        print(f"   uuid:     {uuid}")
        print(f"   title:    {title!r}")
        print(f"   subtitle: {subtitle!r}")
        print(f"   body:     {body!r}")
        if raw_blob:
            print(f"   raw:      {plist!r}"[:600])
        shown += 1
        if shown >= limit:
            break

    if shown == 0 and keyword:
        print(f"  （keyword={keyword!r} 沒命中任何 push）")

    print(f"\n{'=' * 72}\n  共顯示 {shown} 筆\n{'=' * 72}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="macOS NotificationCenter discovery — Phase 1 of Firstrade tracker"
    )
    p.add_argument("--keyword", "-k", default=None,
                   help="filter by app id / title / body / subtitle keyword（不分大小寫）")
    p.add_argument("--limit", "-n", type=int, default=20,
                   help="最多顯示幾筆樣本（default 20）")
    p.add_argument("--hours", type=int, default=168,
                   help="掃過去多久內的 push（default 168 = 7 天）")
    p.add_argument("--raw-blob", action="store_true",
                   help="連原始 plist 都印出來（debug 用，會很長）")
    args = p.parse_args()
    discover(args.keyword, args.limit, args.hours, args.raw_blob)
