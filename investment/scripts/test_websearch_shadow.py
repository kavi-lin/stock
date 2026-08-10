#!/usr/bin/env python3
"""Contract for `websearch_shadow.py` — Phase 2 lane 的 web search shadow ledger。

這支工具的用途是**替一條沒有產生器的規則收集拍板證據**，所以它自己不可信就毫無價值。
2026-08-09 的 `audit_gate_compliance.py` 是前車之鑑：沒驗就拿它下結論，五個偽陽全指控
引擎違規，第一份輸出若直接轉述會得出完全相反的結論。

因此本檔鎖三件事：
  1. **偵測器在「已知有」的輸入上會報非零**——否則它報 0 沒有意義（MAINTENANCE §2c 規則 1）。
     用真實 log 當案例，不是合成的。
  2. **歸屬走 `parent_tool_use_id`**——lane 層數字的全部意義都在這條連結上。拆掉它，
     數字必須塌成 unattributed 而不是靜靜換一個 lane。
  3. **看不到 ≠ 沒發生**——codex 的 JSONL 沒有 web 工具事件型別，必須記 `observable: false`
     而不是 `web_calls: 0`。這兩者混為一談就是一個新的靜默綠。

Usage: python3 investment/scripts/test_websearch_shadow.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import websearch_shadow as W  # noqa: E402
import validate_session_export as V  # noqa: E402

failures: list[str] = []


def check(name, cond, detail=""):
    if not cond:
        failures.append(f"{name}: {detail}")


def write_log(lines, header="=== protocol=invest model=claude:opus "
                            "prompt='分析 ZZTEST' started=2026-08-10T00:00:00 ==="):
    fp = tempfile.NamedTemporaryFile("w", suffix=".log", delete=False, encoding="utf-8")
    fp.write(header + "\n")
    for o in lines:
        fp.write(json.dumps(o, ensure_ascii=False) + "\n")
    fp.close()
    return fp.name


def tool_use(name, tid, parent=None, description=None):
    inp = {"description": description} if description else {}
    return {"type": "assistant", "parent_tool_use_id": parent,
            "message": {"content": [{"type": "tool_use", "id": tid,
                                     "name": name, "input": inp}]}}


# ── 1. 真實 log：偵測器必須報得出非零 ────────────────────────────────────────
# 合成 fixture 只能證明「照我寫的解析邏輯跑得通」。要證明它對得上真實世界，
# 必須有一個來自實跑的案例。這支 log 是 2026-04-18 MSFT，Agent×6 + WebFetch×2 + WebSearch×6。
REAL = os.path.join(W.ROOT, "investment/scan_logs/invest_20260418_141121.log")
if os.path.exists(REAL):
    rec = W.scan_log(REAL)
    check("real.observable", rec["observable"] is True, json.dumps(rec)[:200])
    check("real.shape", rec["log_shape"] == "claude_stream_json", rec["log_shape"])
    check("real.agent_spawns", rec["agent_spawns"] == 6, rec["agent_spawns"])
    total = sum(s["web_calls"] for s in rec["lanes"].values())
    check("real.reports_nonzero", total > 0,
          "偵測器在已知有 web search 的 log 上報了 0 —— 它報的 0 從此不可信")
    check("real.lane_attribution", set(rec["lanes"]) == {"fundamentals", "sentiment", "news"},
          sorted(rec["lanes"]))
    check("real.news_count", rec["lanes"].get("news", {}).get("web_calls") == 4,
          rec["lanes"].get("news"))
    check("real.ticker", rec["ticker"] == "MSFT", rec["ticker"])
else:
    check("real.log_present", False, f"{REAL} 不在 —— 本檔最重要的案例無法執行")

# ── 2. 歸屬走 parent_tool_use_id ─────────────────────────────────────────────
p = write_log([
    tool_use("Agent", "toolu_F", description="Fundamentals analyst ZZ"),
    tool_use("Agent", "toolu_N", description="News analyst ZZ"),
    tool_use("WebSearch", "w1", parent="toolu_F"),
    tool_use("WebSearch", "w2", parent="toolu_N"),
    tool_use("WebSearch", "w3", parent="toolu_N"),
    tool_use("WebFetch", "w4", parent=None),          # PM 自己呼叫
])
rec = W.scan_log(p)
os.unlink(p)
check("attr.fundamentals", rec["lanes"].get("fundamentals", {}).get("web_calls") == 1,
      rec["lanes"])
check("attr.news", rec["lanes"].get("news", {}).get("web_calls") == 2, rec["lanes"])
check("attr.pm_level", rec["pm_level_web_calls"] == 1, rec["pm_level_web_calls"])
# 額度是 1：剛好 1 次不算超，2 次才算。
check("attr.allowance_boundary",
      rec["lanes"]["fundamentals"]["over_allowance"] is False
      and rec["lanes"]["news"]["over_allowance"] is True, rec["lanes"])

# 拆掉 parent 連結 → 必須塌成 PM 層，不得靜靜歸給某個 lane
p = write_log([
    tool_use("Agent", "toolu_F", description="Fundamentals analyst ZZ"),
    tool_use("WebSearch", "w1", parent=None),
])
rec = W.scan_log(p)
os.unlink(p)
check("attr.no_parent_is_not_a_lane", not rec["lanes"] and rec["pm_level_web_calls"] == 1,
      json.dumps(rec, ensure_ascii=False)[:200])

# 非 lane 的 subagent（Red Team）不得被算進五個 lane 任何一個
p = write_log([
    tool_use("Agent", "toolu_R", description="Red Team adversary"),
    tool_use("WebSearch", "w1", parent="toolu_R"),
])
rec = W.scan_log(p)
os.unlink(p)
check("attr.red_team_not_a_lane",
      not rec["lanes"] and rec["other_agent_web_calls"] == 1,
      json.dumps(rec, ensure_ascii=False)[:200])

# ── 3. 看不到 ≠ 沒發生 ───────────────────────────────────────────────────────
p = write_log([{"type": "item.completed",
                "item": {"id": "i1", "type": "command_execution", "command": "ls"}}],
              header="=== protocol=invest model=codex:cli-default "
                     "prompt='分析 ZZ' started=2026-08-10T00:00:00 ===")
rec = W.scan_log(p)
os.unlink(p)
check("unobservable.codex_marked", rec["observable"] is False, json.dumps(rec)[:200])
check("unobservable.codex_shape", rec["log_shape"] == "codex_jsonl", rec["log_shape"])
check("unobservable.codex_has_note", bool(rec["notes"]), rec["notes"])
check("unobservable.codex_no_fake_zero", rec["lanes"] == {},
      "codex 不可觀測卻回報了 lane 數字 —— 那會被讀成『這家沒違規』")

p = write_log([{"hello": "world"}], header="not a runner header")
rec = W.scan_log(p)
os.unlink(p)
check("unobservable.unknown_marked", rec["observable"] is False, json.dumps(rec)[:200])
check("unobservable.unknown_shape", rec["log_shape"] == "unknown", rec["log_shape"])

# ── 4. report 不得把「不可觀測」算成分母 ─────────────────────────────────────
# 20 筆不可觀測混進分母會把違規率稀釋，而稀釋後的數字正是拍板要用的那個。
import io                                                            # noqa: E402
import contextlib                                                    # noqa: E402
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    W.report([
        {"observable": True, "log_shape": "claude_stream_json", "provider": "claude:opus",
         "lanes": {"news": {"web_calls": 3, "over_allowance": True}},
         "pm_level_web_calls": 0, "other_agent_web_calls": 0, "agent_spawns": 5},
        {"observable": False, "log_shape": "codex_jsonl", "provider": "codex:cli-default",
         "lanes": {}, "pm_level_web_calls": 0, "other_agent_web_calls": 0},
    ])
out = buf.getvalue()
check("report.counts_observable_only", "可觀測 1 筆" in out and "不可觀測 1 筆" in out, out[:200])
check("report.no_observable_short_circuits", "0 筆不等於 0 次違規" not in out,
      "有可觀測樣本時不該印那句提示")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    W.report([{"observable": False, "log_shape": "codex_jsonl", "lanes": {}}])
check("report.zero_observable_says_so", "0 筆不等於 0 次違規" in buf.getvalue(),
      buf.getvalue()[:200])

# ── 5. lane 解析器與 validator 共用同一支 ────────────────────────────────────
# 兩份前綴表一致時全綠，任一方改動後這支會走「解析不出 → unattributed」的靜默分支
# （§2c 成員 #8）。所以綁定關係本身要有斷言。
check("shared.resolver_is_the_validator_one",
      W.resolve_degraded_lane is V.resolve_degraded_lane,
      "websearch_shadow 自己複製了一份 lane 前綴表")
check("shared.lane_names", tuple(W.CONFLICT_LANES) == tuple(V.CONFLICT_LANES),
      f"{W.CONFLICT_LANES} vs {V.CONFLICT_LANES}")

if failures:
    print("✗ websearch shadow contract violated:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("✓ websearch shadow contract holds "
      "(real-log non-zero + parent attribution + unobservable≠zero + shared resolver)")
