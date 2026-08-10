#!/usr/bin/env python3
"""websearch_shadow.py — Phase 2 lane 的 web search 用量 shadow ledger（V4.124.0）。

protocol 共通 subagent 模板寫著：「✅ ALLOWED web search (≤ 1 call, narrative tone only)」，
違規則「PM 自動扣 confidence 0.2；連 3 次 → 該 lane 視為 degraded」。**這條規則零實作、
零追蹤**——沒有任何東西在數那個「連 3 次」，它是跨 session 狀態，而沒有人保存過。

補實作與刪宣稱都會改變行為（前者今天開始扣分、後者今天放棄一條紀律），兩者都需要
使用者拍板。本檔走第三條路：**只記錄，不扣分**。累積夠了再由使用者決定 (a) 補產生器
還是 (b) 刪宣稱——與 `conflict_bias`（V4.122.0）同一套路，先讓它可觀測，再談生效。

**探索層**：產出永不進入 investment_protocol 的決策（buy_threshold / position_size /
verdict），validator 不讀本 ledger，本檔也不寫 history.json。

證據來源是 **run log 而非 PM 自陳**：違規的 session 正是最不會自我回報的那個。Claude 的
stream-json 用 `parent_tool_use_id` 把每個工具呼叫掛回 spawn 它的 `Agent`，所以
web search 能精確歸屬到 lane。

只掃工具**呼叫**（`tool_use` block），不掃輸出——2026-08-09 的稽核工具就是把 log 裡
引擎讀到的檔案內容當成它做的事，五個偽陽全指控引擎違規（見 LESSONS）。

**認不得的 log 形狀一律記 `observable: false`，不是 `count: 0`**：codex 的 JSONL 沒有任何
web 工具事件型別，那是「看不到」不是「沒發生」。兩者混為一談就是一個新的靜默綠。

Usage:
  python3 investment/scripts/websearch_shadow.py --log <path>   # 記一筆
  python3 investment/scripts/websearch_shadow.py --backfill     # 掃全部 invest log 建基線
  python3 investment/scripts/websearch_shadow.py --report       # 統計（拍板用）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# lane 標籤 → canonical lane 名。與 validator 共用同一支，不另寫一份前綴表
# （§2c 成員 #8：producer/consumer 各寫一份，失效方式是永久靜音而不是報錯）。
from validate_session_export import (  # noqa: E402
    CONFLICT_LANES,
    resolve_degraded_lane,
)

SCHEMA = "websearch_shadow.v1"
LEDGER = os.path.join(ROOT, "investment/invest_logs/websearch_shadow.jsonl")
LOG_DIR = os.path.join(ROOT, "investment/scan_logs")

#: protocol 共通模板的 narrative 允許額度。超過就是「數量上」已經違規，
#: 不需要對內容做語意判斷 —— 本 ledger 刻意只記可數的那一半。
NARRATIVE_ALLOWANCE = 1

WEB_TOOLS = ("WebSearch", "WebFetch")


def _iter_json(path):
    with open(path, encoding="utf-8", errors="replace") as fp:
        for line in fp:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                yield json.loads(line)
            except (ValueError, TypeError):
                continue


def _header(path):
    """第一行的 runner header：`=== protocol=invest model=... prompt='...' started=... ===`"""
    with open(path, encoding="utf-8", errors="replace") as fp:
        head = fp.readline()
    provider = ticker = started = None
    m = re.search(r"model=(\S+)", head)
    if m:
        provider = m.group(1)
    m = re.search(r"started=(\S+?)\s*===", head)
    if m:
        started = m.group(1)
    m = re.search(r"分析\s+([A-Z][A-Z0-9.\-]{0,9})", head)
    if m:
        ticker = m.group(1)
    return provider, ticker, started


def scan_log(path):
    """回傳一筆 ledger record。認不得的形狀 → `observable: false`。"""
    provider, ticker, started = _header(path)
    rec = {
        "schema": SCHEMA,
        "log": os.path.basename(path),
        "provider": provider,
        "ticker": ticker,
        "run_started": started,
        "log_shape": "unknown",
        "observable": False,
        "agent_spawns": 0,
        "lanes": {},
        "pm_level_web_calls": 0,
        "other_agent_web_calls": 0,
        "notes": [],
    }

    agent_by_id = {}          # tool_use_id → 該 Agent 的 description
    web_by_parent = defaultdict(Counter)
    saw_claude_shape = False
    saw_codex_shape = False

    for obj in _iter_json(path):
        if obj.get("item"):                       # codex JSONL
            saw_codex_shape = True
            continue
        msg = obj.get("message")
        if not isinstance(msg, dict):
            continue
        for blk in msg.get("content") or []:
            if not isinstance(blk, dict) or blk.get("type") != "tool_use":
                continue
            saw_claude_shape = True
            name = blk.get("name")
            if name == "Agent":
                agent_by_id[blk.get("id")] = str(
                    (blk.get("input") or {}).get("description") or "")
            elif name in WEB_TOOLS:
                # 掛回 spawn 它的 Agent；PM 自己呼叫的 parent 是 None。
                web_by_parent[obj.get("parent_tool_use_id")][name] += 1

    if saw_claude_shape:
        rec["log_shape"] = "claude_stream_json"
        rec["observable"] = True
    elif saw_codex_shape:
        # codex 的 JSONL 只有 command_execution / file_change / agent_message /
        # collab_tool_call —— **沒有任何 web 工具事件型別**。看不到 ≠ 沒發生。
        rec["log_shape"] = "codex_jsonl"
        rec["notes"].append("codex JSONL 沒有 web 工具事件型別，本 run 的 web 用量不可觀測")
        return rec
    else:
        rec["notes"].append("log 形狀不認得（既非 claude stream-json 也非 codex JSONL）")
        return rec

    rec["agent_spawns"] = len(agent_by_id)
    lanes = {}
    for parent, tools in web_by_parent.items():
        total = sum(tools.values())
        if parent is None:
            rec["pm_level_web_calls"] += total
            continue
        desc = agent_by_id.get(parent)
        lane = resolve_degraded_lane(desc) if desc else None
        if lane is None:
            rec["other_agent_web_calls"] += total
            continue
        slot = lanes.setdefault(lane, {"agent_description": desc, "web_calls": 0,
                                       "tools": {}})
        slot["web_calls"] += total
        for k, v in tools.items():
            slot["tools"][k] = slot["tools"].get(k, 0) + v
    for lane, slot in lanes.items():
        slot["over_allowance"] = slot["web_calls"] > NARRATIVE_ALLOWANCE
    rec["lanes"] = lanes

    if agent_by_id and not any(resolve_degraded_lane(d) for d in agent_by_id.values()):
        rec["notes"].append(
            f"{len(agent_by_id)} 個 Agent 的 description 都對不回 lane 名 "
            f"{list(CONFLICT_LANES)} — 歸屬失效，lane 層數字不可信")
    return rec


def append_ledger(records, path=LEDGER):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fp:
        for r in records:
            fp.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_ledger(path=LEDGER):
    if not os.path.exists(path):
        return []
    return [json.loads(x) for x in open(path, encoding="utf-8") if x.strip()]


def report(records):
    total = len(records)
    obs = [r for r in records if r.get("observable")]
    print(f"ledger 共 {total} 筆；可觀測 {len(obs)} 筆、"
          f"不可觀測 {total - len(obs)} 筆（形狀認不得或該 CLI 不上報）")
    by_shape = Counter(r.get("log_shape") for r in records)
    print("  log 形狀:", dict(by_shape))
    if not obs:
        print("  （沒有可觀測樣本，以下統計省略——0 筆不等於 0 次違規）")
        return

    lane_runs = Counter()
    lane_over = Counter()
    lane_calls = Counter()
    prov_over = Counter()
    prov_runs = Counter()
    for r in obs:
        prov = (r.get("provider") or "?").split(":")[0]
        prov_runs[prov] += 1
        hit = False
        for lane, slot in (r.get("lanes") or {}).items():
            lane_runs[lane] += 1
            lane_calls[lane] += slot.get("web_calls", 0)
            if slot.get("over_allowance"):
                lane_over[lane] += 1
                hit = True
        if hit:
            prov_over[prov] += 1

    print(f"\n  narrative 允許額度 = {NARRATIVE_ALLOWANCE} call/lane；"
          "超過即「數量上違規」（內容是否屬禁用類別本 ledger 不判斷）")
    print(f"  {'lane':14s} {'有web的run':>10s} {'超額run':>8s} {'總call':>7s}")
    for lane in CONFLICT_LANES:
        print(f"  {lane:14s} {lane_runs[lane]:10d} {lane_over[lane]:8d} {lane_calls[lane]:7d}")
    print(f"\n  依 provider（超額 run / 可觀測 run）:")
    for p in sorted(prov_runs):
        print(f"    {p:10s} {prov_over[p]:4d} / {prov_runs[p]:4d}")
    pm = sum(r.get("pm_level_web_calls", 0) for r in obs)
    other = sum(r.get("other_agent_web_calls", 0) for r in obs)
    spawn0 = sum(1 for r in obs if r.get("agent_spawns") == 0)
    print(f"\n  PM 層（非 lane）web call 合計 {pm}；非 lane subagent {other}")
    print(f"  可觀測 run 中 Agent spawn = 0 的有 {spawn0} 筆 "
          "（該 run 沒有開任何子代理，lane 歸屬自然為空）")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--log", help="單一 run log 路徑")
    g.add_argument("--backfill", action="store_true",
                   help=f"掃 {LOG_DIR} 全部 invest_*.log 重建 ledger")
    g.add_argument("--report", action="store_true", help="統計現有 ledger")
    ap.add_argument("--ledger", default=LEDGER)
    ap.add_argument("--stdout", action="store_true", help="只印不寫檔")
    args = ap.parse_args(argv)

    if args.report:
        report(load_ledger(args.ledger))
        return 0

    if args.log:
        rec = scan_log(args.log)
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        if not args.stdout:
            append_ledger([rec], args.ledger)
        return 0

    import glob
    paths = sorted(glob.glob(os.path.join(LOG_DIR, "invest_*.log")))
    if not paths:
        print(f"[websearch_shadow] {LOG_DIR} 下沒有 invest_*.log", file=sys.stderr)
        return 1
    recs = [scan_log(p) for p in paths]
    if args.stdout:
        for r in recs:
            print(json.dumps(r, ensure_ascii=False))
    else:
        if os.path.exists(args.ledger):
            os.replace(args.ledger, args.ledger + ".bak")
        append_ledger(recs, args.ledger)
        print(f"[websearch_shadow] 掃了 {len(recs)} 支 log → {args.ledger}")
    report(recs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
