#!/usr/bin/env python3
"""驗收一次 invest run 對 V4.117.0 三道閘的實際行為。

用法：
    python3 <這支> <log 路徑>

只讀不寫。回報的是「閘有沒有被繞過」，不是「分析好不好」。
"""
import json
import os
import re
import sys
import subprocess
import collections
import datetime

ROOT = "/Users/kavi/Developer/Claude/Projects/ai-investment-committee"
HIST = os.path.join(ROOT, "investment/invest_logs/history.json")


def _command_outputs(log: str, cmd_pattern: str) -> str:
    """Outputs of the commands whose invocation matches `cmd_pattern`."""
    out, want = [], re.compile(cmd_pattern)
    for line in log.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        su = (d.get("step_update") or {})
        ti = (su.get("tool_info") or {})
        params = ti.get("parameters") or {}
        item = d.get("item") or {}
        cmd = params.get("CommandLine") or params.get("command") or item.get("command") or ""
        if not (isinstance(cmd, str) and want.search(cmd)):
            continue
        for blob in (ti.get("output"), item.get("aggregated_output")):
            if isinstance(blob, str):
                out.append(blob)
    return "\n".join(out)


def _run_window(log_path):
    """(start, end) in UTC for this run: filename stamp → log mtime.

    Open-ended windows were the bug: `>= start` counted a LATER run's entries as
    this one's, so a second engine on the same ticker read as "this run wrote
    two". The log stops being written when the run ends, so its mtime is the
    honest upper bound.
    """
    m = re.search(r"_(\d{8})_(\d{6})", os.path.basename(log_path))
    if not m:
        return None
    local = datetime.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    start = local.astimezone().astimezone(datetime.timezone.utc)
    end = datetime.datetime.fromtimestamp(
        os.path.getmtime(log_path), datetime.timezone.utc)
    return start, end + datetime.timedelta(minutes=2)


def _executed_commands(log: str) -> str:
    """只回傳引擎實際下的指令，不含它讀進 context 的檔案內容。

    掃全文會把 protocol 裡「不得用 `h.pop()`」那句禁令本身算成一次手寫痕跡——
    引擎 `sed` 出 protocol 全文，輸出進了 log，於是讀了規則反而被記一筆違規。
    命中的必須是它做了什麼，不是它看了什麼，所以 command 欄位要取、輸出欄位
    (`aggregated_output`) 一律不取。

    兩種 log 形狀：
      gemini  {"step_update": {"tool_info": {"parameters": {"CommandLine": ...}}}}
      codex   {"item": {"type": "command_execution", "command": ...}}
    """
    out = []
    for line in log.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        params = (((d.get("step_update") or {}).get("tool_info") or {}).get("parameters") or {})
        for cmd in (params.get("CommandLine"), params.get("command"),
                    (d.get("item") or {}).get("command")):
            if isinstance(cmd, str):
                out.append(cmd)
    if not out:
        # 未知 log 形狀：寧可偽陽也不要漏，但要說出來，否則讀數會被當成乾淨的。
        out.append(log)
        print("    (⚠ 認不得的 log 形狀，以下手寫計數掃了全文，可能含引擎讀到的檔案內容)")
    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        sys.exit("用法: python3 audit_run.py <investment/scan_logs/....log>")
    log_path = sys.argv[1]
    if not os.path.isabs(log_path):
        log_path = os.path.join(ROOT, log_path)
    log = open(log_path, encoding="utf-8", errors="replace").read()
    cmds = _executed_commands(log)

    hist = json.load(open(HIST, encoding="utf-8"))
    # 挑「本次 run 蓋章的那筆」，不是 hist[-1]。之後又跑了別的 run 的話，hist[-1]
    # 是別人的 entry，而 ticker 相同時連防呆都攔不住——報告會把兩次 run 的數字
    # 混在一起，比沒有報告更糟。
    win = _run_window(log_path)
    entry = None
    if win:
        start, end = win
        for e in hist:
            at = (e.get("export_provenance") or {}).get("appended_at")
            try:
                when = datetime.datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=datetime.timezone.utc)
            except (ValueError, TypeError):
                continue
            if start <= when <= end:
                entry = e   # 同一 run 若重寫多次，取最後一筆
    if entry is None:
        entry = hist[-1]
        print("    (⚠ 找不到本次 run 蓋章的 entry — 退回 history 最後一筆，"
              "若期間跑過別的 run，以下欄位可能不屬於這份 log)\n")
    trade = entry["trades_this_session"][0]
    tk = trade.get("ticker") or entry.get("ticker")

    print(f"=== {tk} / {entry.get('export_date')} · history {len(hist)} 筆 ===\n")

    # log 檔名帶 job id（invest_manual_<provider>_<TICKER>_<stamp>.log）。對不上就是
    # 拿舊 log 配現在的最後一筆——讀數會混兩次 run，比沒有讀數更糟。
    m = re.search(r"invest_manual_(\w+?)_([A-Z0-9.\-]+)_\d{8}_\d{6}", os.path.basename(log_path))
    if m and m.group(2).upper() != str(tk).upper():
        print(f"⚠ log 是 {m.group(1)}/{m.group(2)} 但 history 最後一筆是 {tk} —— "
              f"兩者不是同一次 run，以下讀數不可用\n")
        sys.exit(2)
    if m:
        print(f"    provider = {m.group(1)}\n")

    # ── 1. validator 現況 ────────────────────────────────────────────────
    proc = subprocess.run([sys.executable,
                           os.path.join(ROOT, "investment/scripts/validate_session_export.py")],
                          capture_output=True, text=True, cwd=ROOT)
    print(f"[1] validator rc={proc.returncode}（驗的是 history 現況末筆，非本次 run）")
    for line in (proc.stdout + proc.stderr).strip().splitlines()[:8]:
        print(f"    | {line}")

    # ── 2. Gate 1：有沒有繞過 append_session_export.py ───────────────────
    print("\n[2] Gate 1 — history.json 寫入路徑")
    prov = entry.get("export_provenance")
    print(f"    export_provenance: {'有' if isinstance(prov, dict) else '✗ 缺'}")
    if isinstance(prov, dict):
        sys.path.insert(0, os.path.join(ROOT, "investment/scripts"))
        import append_session_export as A
        ok = prov.get("entry_digest") == A.entry_digest(entry)
        print(f"    digest 相符    : {'✓' if ok else '✗ append 之後被就地改過'}")
        print(f"    writer         : {prov.get('writer')}")
    # log 裡的手寫痕跡
    # 錨在 `history.json` 這個字面上，且不得跨行/跨括號——舊版的 `[^)]*` 會從
    # 「json.dump(session, f...」一路吃到後面 log 文字裡的「(history len=188)」，
    # 把寫 /tmp staging 檔誤報成手寫決策紀錄。
    hand = {
        "json.dump 到 history": len(re.findall(r"json\.dump\([^)\n]{0,120}history\.json", cmds)),
        "history .pop()":       len(re.findall(r"h\.pop\(\)|hist\.pop\(\)|history\.pop\(\)", cmds)),
        "open(history,'w')":    len(re.findall(r"history\.json['\"]?,\s*['\"]w", cmds)),
    }
    for k, v in hand.items():
        print(f"    {k:22s}: {v} {'✓' if v == 0 else '← 手寫痕跡'}")
    rl = len(re.findall(r"--replace-last", cmds))
    print(f"    {'--replace-last 使用':22s}: {rl} "
          f"{'（用了受控修法路徑）' if rl else ''}")

    # 同 session 重複筆
    dup = collections.Counter((e.get("ticker"), e.get("export_date")) for e in hist)
    mine = dup[(entry.get("ticker"), entry.get("export_date"))]
    # 同鍵多筆不一定是修法留下的重複——同一天跑兩次本來就會這樣。能區分的是
    # stamp：本次 run 只該貢獻一筆。
    # 同鍵多筆不代表修法留下重複——同一天跑兩次本來就會這樣。要分辨的是**本次 run**
    # 貢獻了幾筆，所以用 log 檔名的起跑時間切 `appended_at`（UTC）。
    this_run = 0
    for e in hist:
        if (e.get("ticker"), e.get("export_date")) != (entry.get("ticker"), entry.get("export_date")):
            continue
        at = (e.get("export_provenance") or {}).get("appended_at")
        if not at or not win:
            continue
        try:
            when = datetime.datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
        if win[0] <= when <= win[1]:
            this_run += 1
    print(f"    同 ticker+date 筆數: {mine}（本次 run 貢獻 {this_run} 筆）"
          f"{' ✓' if this_run <= 1 else ' ← 本次 run 留下多筆，修法走了 re-append'}")

    # ── 3. Gate 2：pt_revision_momentum ──────────────────────────────────
    print("\n[3] Gate 2 — pt_revision_momentum")
    prm = (trade.get("news_lane") or {}).get("pt_revision_momentum")
    print(f"    export 寫的: {json.dumps(prm, ensure_ascii=False)}")
    # fetch.py 在 log 裡實際回了什麼
    # 只看 news fetch.py 這支指令的輸出。掃全文會命中 schema doc 的 FULL EXAMPLE
    # ——那是引擎讀到的範例，不是它抓到的資料，拿它當「script 有回值」的證據就等於
    # 用文件反證文件。
    hits = re.findall(r'"pt_revision_momentum"\s*:\s*(\{[^}]*\})',
                      _command_outputs(log, r"market-news-analyst[/\w.-]*fetch\.py"))
    if hits:
        print(f"    fetch.py 回 : {hits[0][:160]}")
        if isinstance(prm, dict) and prm.get("direction") == "UNKNOWN" \
                and '"direction": null' not in hits[0] and "UNKNOWN" not in hits[0]:
            print("    ⚠ script 有資料但 export 寫 UNKNOWN — 閘被滿足、紀律沒有")
    else:
        print("    fetch.py 回 : (log 中找不到，需人工翻)")

    # ── 4. Gate 3：calculation_steps vs engine artifact ──────────────────
    print("\n[4] Gate 3 — calculation_steps parity")
    art = os.path.join(ROOT, f"investment/invest_logs/decision_engine/{tk}_decision_engine.json")
    if not os.path.exists(art):
        print("    ✗ artifact 不存在 — engine 沒跑或版本沒生效，閘等於靜音")
    elif win and datetime.datetime.fromtimestamp(
            os.path.getmtime(art), datetime.timezone.utc) > win[1]:
        # 單槽快取：同一支股票的後續 run 會蓋掉它。回溯稽核到這裡就沒有證據了，
        # 印 diff 只會把「後來有人跑過」誤報成「這次抄錯」。
        print("    ↷ artifact 已被本次 run 之後的執行覆蓋 — 無法回溯比對。"
              "Gate 3 的結果要在該 run 剛跑完時看")
    else:
        a = json.load(open(art, encoding="utf-8"))
        sys.path.insert(0, os.path.join(ROOT, "investment/scripts"))
        import validate_session_export as V
        diffs = V._diff_steps(a.get("calculation_steps") or {},
                              trade.get("calculation_steps") or {})
        print(f"    artifact final_score: {a.get('final_score')}  "
              f"export: {trade.get('final_score')}")
        print(f"    逐欄差異: {diffs if diffs else '無 ✓'}")
    de_calls = len(re.findall(r"decision_engine\.py", cmds))
    print(f"    decision_engine 呼叫次數(log): {de_calls}")

    # ── 5. 既有閘 ────────────────────────────────────────────────────────
    print("\n[5] V4.116.x 既有閘")
    print(f"    valuation_reviewer_gate: "
          f"{'有' if isinstance(trade.get('valuation_reviewer_gate'), dict) else '✗ 缺'}")
    tp = os.path.join(ROOT, f"skills/technical-analyst/cache/{tk}_technical_payload.json")
    if os.path.exists(tp):
        hint = (json.load(open(tp, encoding="utf-8")).get("signal_hints") or {}).get("rubric_hint")
        sc = (trade.get("lane_scores") or {}).get("technical")
        ovr = (trade.get("technical_lane") or {}).get("rubric_override_reason")
        print(f"    technical {sc} vs hint {hint!r} | override: "
              f"{'有' if ovr else '無'}")
    drift = len(re.findall(r"\[validate_session_export\] ✗ schema drift", log))
    print(f"\n    schema drift 輪數: {drift}")


if __name__ == "__main__":
    main()
