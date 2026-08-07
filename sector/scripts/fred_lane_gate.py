#!/usr/bin/env python3
"""fred_lane_gate.py — Phase 4a FRED Macro lane 的條件式觸發判定（SE5，**shadow-only**）。

判斷「這場該不該跑 FRED Macro lane subagent」。**本版一律 shadow**：`would_invoke`
只被記錄，PS 照跑 lane、決策數字一個都不動。翻預設是使用者拍板的事（照 L4b 前例）。

**零新計算**：所有訊號讀 `skills/fred-macro/cache/fred_latest.json` 與既有 sector_intel，
不打 API、不重算 regime。

lane 的增量價值在哪（trigger 為何長這樣）
----------------------------------------
`sector_rotation` 有兩層（見 `SECTOR_ROTATION_GUIDE.md`）：

    favor[]       base map，**已由 `step6_overlay.py` deterministic 套進分數**
    adjustments[] 由當前 macro 數值觸發的 override 規則，RULE 1「overrides favor」、
                  RULE 2 有明確優先序（credit_stress > yield_curve_inverted >
                  real_rate_high > yield_curve_steep）

實查（V4.94.0）：`adjustments` **沒有任何腳本消費** —— `step6_overlay.py` 只讀
favor/avoid（step6_overlay.py:81-82），`_slim_fred()` 的 11 欄也不含它。也就是說
**FRED lane 是 adjustments 的唯一消費者**。adjustments 為空時（RULE 4「base map
valid as-is」）lane 只會覆述 step6 已經算過的 favor[]，增量趨近於零；非空時
lane 是唯一會套 RULE 1/2 的角色 —— 所以 `adjustments_active` 設為 **mandatory**。

⚠️ **同時發現的既有缺口（本版不修，僅記錄）**：lane 的資料切片是
`_phase0.fred_snapshot`（slim 11 欄），而那 11 欄**不含 `adjustments`**。protocol 卻
要求 lane「`adjustments[]` overrides favor（不可只重複 favor）」—— lane 被要求套用一份
它從未收到的資料。gate 會在 `notes` 標出這件事；修法（把 adjustments 併進 lane 切片）
會改變 lane 產出，屬於行為變更，不與 shadow-only 的 gate 同版動。

跳過是否會改決策數字（L4b 的必答題）
------------------------------------
**不會**，與 L4b 的 valuation lane 相反：
  - STEP G.5 直接讀 `fred_snapshot.sector_rotation_avoid`，不經 lane
  - Step 6 乘數走 `step6_overlay.py`，不經 lane
  - `consensus_warning` 只定義在 rotation / theme / news 三 lane 上
所以跳過只影響 Arbiter 讀到的質化論述。**翻預設時唯一要小心的**：skip 不得寫進
`degraded_agents`（那會觸發 PARTIAL_FALLBACK 的 confidence cap 與 stance 限制）。
protocol 既有先例：`fred_available=false → FRED lane skip，不算 degraded`。

Usage
-----
    python3 sector/scripts/fred_lane_gate.py --date 2026-08-03 --hot "Technology,Energy"
    python3 sector/scripts/fred_lane_gate.py --date 2026-08-03 --write   # 落盤累積 shadow
    python3 sector/scripts/fred_lane_gate.py --status                    # 讀出端統計

rc=0 正常（含 would_invoke=false）；rc=1 只在 fred cache 不可讀 —— gate 讀不到權威
輸入時不得猜，否則 shadow 統計會混進假樣本。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import date as _date, datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sector.lib.sector_utils import canonicalize_sector_name  # noqa: E402
from phase0_read_caches import _fred_sector_rotation, _slim_fred  # noqa: E402

GATE_VERSION = "fred_lane_gate.py v1.2 (V4.95.3)"
GATE_SCHEMA = "sector_fred_lane_gate.v1"

CACHE_DIR = os.path.join(ROOT, "sector", "cache")
LOGS_DIR = os.path.join(ROOT, "sector", "sector_logs")
FRED_CACHE = os.path.join(ROOT, "skills", "fred-macro", "cache", "fred_latest.json")

LOW_CONFIDENCE_THRESHOLD = 0.40   # 與 protocol 的 "LOW-CONFIDENCE" 前綴規則同值
# RULE 2 優先序（高→低），衝突偵測用
ADJUSTMENT_PRIORITY = ("credit_stress", "yield_curve_inverted",
                       "real_rate_high", "yield_curve_steep")


class GateInputError(Exception):
    """權威輸入不可用 — main() 轉成 {"error": ...} + rc=1。"""


def _canon_list(xs):
    """只吃 list-of-str。

    非 list（含字串）一律回空：字串會被逐字元迭代，產生一堆單字元「板塊」進到
    conflict 統計裡；list 內的非字串元素會讓 `canonicalize_sector_name` 直接
    `AttributeError`（rc=1 但 stdout 空，違反本檔的 rc 契約）。壞形狀要靜靜略過，
    由 `_shape_warnings()` 標到 notes 讓人看得見，而不是炸掉或產生垃圾。
    """
    if not isinstance(xs, list):
        return []
    return [canonicalize_sector_name(x, silent=True) for x in xs if isinstance(x, str)]


def _read_sector_rotation(raw_fred: dict) -> dict:
    """取 `sector_rotation` —— **直接共用 `_slim_fred()` 走的那條 fallback**。

    本檔已呼叫 `_slim_fred()` 取 avoid/regime_label；`adjustments` 若走另一份
    手抄的 fallback，兩邊只在「形狀清單一致」時等價 —— `_slim_fred` 長出第三種
    形狀的那天，avoid 與 adjustments 就會來自不同來源（4.95.1 修過「只讀頂層」
    版本的同型分歧）。所以這裡薄封裝、不複製邏輯。
    """
    return _fred_sector_rotation(raw_fred)


def _shape_warnings(rot: dict, adjustments_raw) -> list[str]:
    """壞形狀不誤判，但要留痕 —— 靜默略過與「確實沒有」在輸出上無法分辨。"""
    warns = []
    # avoid 與 raise/lower 同一條規則：它是 macro_theme_conflict 的判定輸入，
    # `_canon_list`/`_slim_fred` 靜默丟掉的元素若不留痕，「資料壞了」會被讀成
    # 「HOT 沒撞上 avoid」。
    avoid_raw = rot.get("avoid")
    if avoid_raw is not None and not isinstance(avoid_raw, list):
        warns.append(f"sector_rotation.avoid 不是 list（{type(avoid_raw).__name__}），已當空處理")
    elif isinstance(avoid_raw, list) and any(not isinstance(x, str) for x in avoid_raw):
        warns.append("sector_rotation.avoid 含非字串元素，已略過該元素")
    if adjustments_raw is not None and not isinstance(adjustments_raw, list):
        warns.append(f"sector_rotation.adjustments 不是 list（{type(adjustments_raw).__name__}），已當空處理")
    elif isinstance(adjustments_raw, list):
        for i, a in enumerate(adjustments_raw):
            if not isinstance(a, dict):
                warns.append(f"adjustments[{i}] 不是 object（{type(a).__name__}），已略過")
                continue
            for key in ("raise", "lower"):
                v = a.get(key)
                if v is not None and not isinstance(v, list):
                    warns.append(f"adjustments[{i}].{key} 不是 list（{type(v).__name__}），已當空處理")
                elif isinstance(v, list) and any(not isinstance(x, str) for x in v):
                    warns.append(f"adjustments[{i}].{key} 含非字串元素，已略過該元素")
    return warns


def load_fred(path: str | None = None) -> dict:
    p = path or FRED_CACHE
    if not os.path.exists(p):
        raise GateInputError(f"fred cache missing: {p}")
    try:
        with open(p, encoding="utf-8") as fp:
            raw = json.load(fp)
    except Exception as e:
        raise GateInputError(f"fred cache unreadable: {e}")
    if not isinstance(raw, dict):
        raise GateInputError("fred cache is not an object")
    return raw


def previous_regime_label(logs_dir: str | None = None,
                          before_date: str | None = None) -> tuple[str | None, str | None]:
    """從最近一份 sector_intel 取上一場的 regime_label。回傳 (label, source_file)。"""
    files = sorted(glob.glob(os.path.join(logs_dir or LOGS_DIR, "*_sector_intel.json")))
    if before_date:
        files = [f for f in files if os.path.basename(f)[:10] < before_date]
    for path in reversed(files):
        try:
            with open(path, encoding="utf-8") as fp:
                intel = json.load(fp)
        except Exception:
            continue
        # 壞形狀 intel（頂層不是 object、`_phase0`/`fred_snapshot` 被寫成
        # list/str、label 非字串）一律跳過往前找。這裡任何 AttributeError 都會
        # 讓 main() 直接 traceback —— rc=1 且 stdout 空，違反「rc=1 只在 fred
        # cache 不可讀」的契約，還讓一份壞歷史檔拖死之後的每一場 gate。
        if not isinstance(intel, dict):
            continue
        phase0 = intel.get("_phase0")
        snap = phase0.get("fred_snapshot") if isinstance(phase0, dict) else None
        label = snap.get("regime_label") if isinstance(snap, dict) else None
        if isinstance(label, str) and label:
            return label, os.path.basename(path)
    return None, None


def evaluate_triggers(raw_fred: dict, *, hot_sectors: list[str],
                      prev_regime: str | None) -> dict:
    slim = _slim_fred(raw_fred)
    rot = _read_sector_rotation(raw_fred)
    adjustments_raw = rot.get("adjustments")
    adjustments = adjustments_raw if isinstance(adjustments_raw, list) else []
    shape_warnings = _shape_warnings(rot, adjustments_raw)

    hot = [canonicalize_sector_name(s, silent=True) for s in hot_sectors]
    avoid = set(_canon_list(slim.get("sector_rotation_avoid")))

    triggers = []

    # 1. adjustments_active — MANDATORY（lane 是 RULE 1/2 的唯一執行者）
    if adjustments:
        factors = [a.get("factor") for a in adjustments if isinstance(a, dict)]
        triggers.append({
            "name": "adjustments_active",
            "mandatory": True,
            "detail": f"sector_rotation.adjustments 非空（{', '.join(str(f) for f in factors)}）"
                      f" → RULE 1 要求 override favor，本專案無其他消費者",
        })

    # 2. adjustment_conflict — 同一 sector 被不同 adjustment 一升一降（RULE 2 仲裁）
    raised, lowered = {}, {}
    for a in adjustments:
        if not isinstance(a, dict):
            continue
        f = a.get("factor")
        for s in _canon_list(a.get("raise")):
            raised.setdefault(s, []).append(f)
        for s in _canon_list(a.get("lower")):
            lowered.setdefault(s, []).append(f)
    conflicted = sorted(set(raised) & set(lowered))
    if conflicted:
        triggers.append({
            "name": "adjustment_conflict",
            "mandatory": False,
            "detail": "同一 sector 同時被 raise 與 lower，需 RULE 2 優先序仲裁："
                      + "；".join(f"{s}(raise={','.join(map(str, raised[s]))} / "
                                  f"lower={','.join(map(str, lowered[s]))})"
                                  for s in conflicted),
        })

    # 3. macro_theme_conflict — HOT sector 撞上 avoid 或 adjustment.lower
    clashes = []
    for s in hot:
        why = []
        if s in avoid:
            why.append("FRED avoid")
        if s in lowered:
            why.append(f"adjustment.lower({','.join(map(str, lowered[s]))})")
        if why:
            clashes.append(f"{s}（{' + '.join(why)}）")
    if clashes:
        triggers.append({
            "name": "macro_theme_conflict",
            "mandatory": False,
            "detail": "Phase 4a HOT 與 macro 方向相左：" + "；".join(clashes),
        })

    # 4. regime_transition — regime 換檔，敘事需要人講
    cur = slim.get("regime_label")
    if prev_regime and cur and prev_regime != cur:
        triggers.append({
            "name": "regime_transition",
            "mandatory": False,
            "detail": f"regime_label 由 {prev_regime} → {cur}",
        })

    conf = slim.get("regime_confidence")
    notes = []
    if isinstance(conf, (int, float)) and conf < LOW_CONFIDENCE_THRESHOLD:
        # 不是 trigger：低信心時 step6 乘數本來就被 confidence gating 壓回 1.0 附近，
        # lane 的論述也必須自標 LOW-CONFIDENCE，增量更低。記錄供 shadow 分析。
        notes.append(f"regime_confidence {conf} < {LOW_CONFIDENCE_THRESHOLD}"
                     f"（lane 須自標 LOW-CONFIDENCE；非 trigger）")
    if adjustments:
        notes.append("⚠️ 既有缺口：`_phase0.fred_snapshot` 的 slim 11 欄不含 "
                     "`adjustments`，lane 目前收不到它卻被要求套用（見檔頭）")
    notes.extend(f"⚠️ 形狀異常：{w}" for w in shape_warnings)

    return {
        "would_invoke": bool(triggers),
        "triggers_fired": [t["name"] for t in triggers],
        "mandatory_fired": [t["name"] for t in triggers if t["mandatory"]],
        "triggers": triggers,
        "notes": notes,
        "context": {
            "regime_label": cur,
            "regime_confidence": conf,
            "adjustment_count": len(adjustments),
            "hot_sectors": hot,
            "previous_regime_label": prev_regime,
        },
    }


def build_gate_record(raw_fred: dict, *, scan_date: str, hot_sectors: list[str],
                      prev_regime: str | None, prev_source: str | None) -> dict:
    rec = evaluate_triggers(raw_fred, hot_sectors=hot_sectors, prev_regime=prev_regime)
    rec.update({
        "schema": GATE_SCHEMA,
        "gate_version": GATE_VERSION,
        "scan_date": scan_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        # 本版一律 shadow：lane 照跑。validator 端若日後要擋翻預設，看這個欄位。
        "shadow_only": True,
        "previous_regime_source": prev_source,
    })
    return rec


def gate_path(scan_date: str, cache_dir: str | None = None) -> str:
    return os.path.join(cache_dir or CACHE_DIR, f"fred_lane_gate_{scan_date}.json")


def write_gate_record(rec: dict, *, cache_dir: str | None = None) -> str:
    path = gate_path(rec["scan_date"], cache_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 原子寫入（與 write_shadow_report 同款）：半份 JSON 只該是 --status 的
    # malformed 噪音來源，不該有機會存在。
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fp:
        json.dump(rec, fp, ensure_ascii=False, indent=2)
        fp.write("\n")
    os.replace(tmp, path)
    return path


def collect_gate_status(cache_dir: str | None = None) -> dict:
    """統計 shadow 樣本：這個 lane 到底多常真的有事做。"""
    rows, malformed = [], []
    for path in sorted(glob.glob(os.path.join(cache_dir or CACHE_DIR,
                                              "fred_lane_gate_*.json"))):
        try:
            with open(path, encoding="utf-8") as fp:
                rec = json.load(fp)
        except Exception as e:
            malformed.append({"file": os.path.basename(path), "error": str(e)})
            continue
        if not isinstance(rec, dict) or rec.get("schema") != GATE_SCHEMA:
            malformed.append({"file": os.path.basename(path), "error": "schema mismatch"})
            continue
        # `bool(rec.get("would_invoke"))` 會把 null／缺欄靜默記成一張 skip 票 ——
        # 「檔案壞了」與「判定為 skip」在統計上必須分得出來。
        wi = rec.get("would_invoke")
        if not isinstance(wi, bool):
            malformed.append({"file": os.path.basename(path),
                              "error": "would_invoke is not a bool"})
            continue
        rows.append({
            "scan_date": rec.get("scan_date"),
            "would_invoke": wi,
            "triggers_fired": rec.get("triggers_fired") or [],
            "mandatory_fired": rec.get("mandatory_fired") or [],
        })

    n = len(rows)
    invoke = sum(1 for r in rows if r["would_invoke"])
    freq = {}
    for r in rows:
        for t in r["triggers_fired"]:
            freq[t] = freq.get(t, 0) + 1
    return {
        "schema": "sector_fred_lane_gate_status.v1",
        "gate_version": GATE_VERSION,
        "sessions": n,
        "would_invoke": invoke,
        "would_skip": n - invoke,
        "invoke_rate": round(invoke / n, 3) if n else None,
        "trigger_frequency": dict(sorted(freq.items(), key=lambda kv: -kv[1])),
        "malformed_files": malformed,
        "rows": rows,
    }


def _iso_date(s: str) -> str:
    """擋非 ISO 日期：`--date 8/3/2026` 會被塞進檔名，`--write` 靜默寫出
    `fred_lane_gate_8/3/…` 子目錄，`--status` 的 glob 永遠看不到那份樣本。"""
    try:
        return _date.fromisoformat(s).isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError(f"--date 必須是 YYYY-MM-DD，收到 {s!r}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="FRED Macro lane 條件式觸發 gate（shadow-only，零新計算）")
    ap.add_argument("--date", type=_iso_date, default=_date.today().isoformat(),
                    help="YYYY-MM-DD")
    ap.add_argument("--hot", default="", help="Phase 4a HOT sectors，逗號分隔（可省）")
    ap.add_argument("--fred", default=None, help="覆寫 fred_latest.json 路徑")
    ap.add_argument("--logs-dir", default=None, help="覆寫 sector_logs 路徑")
    ap.add_argument("--cache-dir", default=None, help="覆寫 sector/cache 路徑")
    ap.add_argument("--write", action="store_true",
                    help="落盤到 sector/cache/fred_lane_gate_<DATE>.json（累積 shadow）")
    ap.add_argument("--status", action="store_true", help="統計已累積的 shadow 樣本")
    args = ap.parse_args()

    if args.status:
        print(json.dumps(collect_gate_status(args.cache_dir), ensure_ascii=False, indent=2))
        return 0

    try:
        raw = load_fred(args.fred)
    except GateInputError as e:
        print(json.dumps({"error": str(e), "schema": GATE_SCHEMA}, ensure_ascii=False))
        return 1

    hot = [s.strip() for s in args.hot.split(",") if s.strip()]
    prev, prev_src = previous_regime_label(args.logs_dir, before_date=args.date)
    rec = build_gate_record(raw, scan_date=args.date, hot_sectors=hot,
                            prev_regime=prev, prev_source=prev_src)
    if args.write:
        rec["written_to"] = write_gate_record(rec, cache_dir=args.cache_dir)
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
