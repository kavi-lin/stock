#!/usr/bin/env python3
"""
Dashboard server — static file server + positions.json CRUD API.

Run:
    python3 dashboard_server.py
    → http://localhost:8080/

API:
    GET    /api/positions         → list all
    POST   /api/positions         → add one (body: JSON, server generates id+created_at)
    PATCH  /api/positions/{id}    → update fields (notes, exit, status, shares, etc.)
    DELETE /api/positions/{id}    → remove by id
"""

import glob
import json
import os
import re
import sys
import time
import subprocess
import threading
from datetime import datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT          = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.join(ROOT, "Dashboard")
POSITIONS     = os.path.join(ROOT, "positions.json")
WATCHLIST_PATH = os.path.join(ROOT, "skills", "momentum-monitor", "scripts",
                              "universes", "watchlist.txt")
PORT          = 8080

# Lazy-import futu notification helper (optional — only used by /api/futu-notifications).
# Kept inside try/except so the server still boots when the macOS Futu app isn't installed
# (e.g. when running headless on a CI box for tests).
sys.path.insert(0, os.path.join(ROOT, "scripts"))
try:
    import parse_futu_notifications as _futu
except Exception as _e:
    _futu = None
    sys.stderr.write(f"[boot] futu helper not loaded: {_e}\n")
_futu_cache = {"ts": 0.0, "payload": None}
_futu_cache_lock = threading.Lock()
FUTU_CACHE_TTL_SEC = 5
# Periodic bridge.py refresh interval (seconds). Override via DASH_REFRESH_SEC env.
REFRESH_INTERVAL_SEC = int(os.getenv("DASH_REFRESH_SEC", "300"))
BRIDGE_TIMEOUT_SEC   = 120

_shutdown = threading.Event()

# Shared state for /api/refresh_status (queried by Dashboard countdown ring)
_refresh_state = {
    "last_ok":              None,   # ISO timestamp string or None
    "last_error":           None,   # Error message string or None
    "last_reason":          None,   # Why we triggered (startup | periodic | POST MU | ...)
    "next_scheduled":       None,   # ISO timestamp string (next periodic fire time)
    "refresh_interval_sec": REFRESH_INTERVAL_SEC,
    "in_progress":          False,
    "error_history":        [],     # Last 10 failures: [{time, reason, error}]
}
_state_lock = threading.Lock()

# ── Reverse-call to Claude CLI (protocol runner) ─────────────────────────
# Lets the Dashboard trigger Claude to execute a protocol (sector/news/invest).
# Single-job lock: one protocol at a time to avoid runaway token burn.
CLAUDE_BIN = os.environ.get("CLAUDE_BIN") or "/Users/kavi/.local/bin/claude"
# Global default (25 min); news DIGEST normally finishes in 1-2 min, so give it
# a tighter ceiling (12 min) — past runs that crossed 10 min have all been
# pathological (e.g. Claude looping on a Bash-heredoc write that hits Stream
# Idle Timeout, burning 2h+ of tokens for nothing).
PROTOCOL_TIMEOUT_SEC = int(os.getenv("PROTOCOL_TIMEOUT_SEC", "1500"))
PROTOCOL_TIMEOUT_OVERRIDES = {
    # DIGEST with "complete pipeline in one turn" prompt + chunked writes needs
    # ~12-15 min with 60+ RSS items. 20 min gives breathing room.
    "news":       int(os.getenv("NEWS_TIMEOUT_SEC",        "1200")),  # 20 min
    "flash":      int(os.getenv("FLASH_TIMEOUT_SEC",       "600")),   # 10 min
    "flash_text": int(os.getenv("FLASH_TEXT_TIMEOUT_SEC",  "600")),   # 10 min
    "review":     int(os.getenv("REVIEW_TIMEOUT_SEC",      "600")),   # 10 min
    "triage":     int(os.getenv("TRIAGE_TIMEOUT_SEC",      "600")),   # 10 min (RSS fetch 30s + 60 條 shallow snap)
    # V4.8 invest protocol: Phase 0-5 with subagents typically takes 30-45 min.
    # Default 25 min (1500s) is too short; 60 min gives comfortable headroom.
    "invest":     int(os.getenv("INVEST_TIMEOUT_SEC",     "3600")),  # 60 min
}

PROTOCOL_PROMPTS = {
    "sector": "非互動模式：依 sector_protocol_main.md GLOBAL RULES 直接執行 Phase 0→5 完整流程，"
              "不要輸出「準備好進入 Phase X 嗎？」「請確認」這類停頓等候，一個 turn 完整收尾。"
              "Cache 衝突自動處理：若 sector_intel.json 的 mtime 看起來新但內部 `generated_at` 距今 ≥ 3 小時 "
              "（通常是 news protocol Phase 4 patch top_catalysts 造成的 mtime touch），"
              "視為 STALE 必須重跑 Phase 0–1，不要當成 FRESH 跳過。\n\n產業掃描",
    "news":   "非互動模式 + 硬規定：\n0. **必須先執行** `python3 news/fetch_all_news.py --hours 24 --output news/news_logs/` 重撈 4 個源（RSS + Finnhub + FMP + SEC EDGAR）合併成 unified raw.json\n1. **必須執行** Stage 1 shallow triage（讀 raw.json 產 ≥ 20 筆 shallow_verdicts 的 triage 表）\n2. **必須 dispatch 4 個 Agent tool_use**（Bull_Analyst / Bear_Analyst / Sector_Analyst / Macro_Analyst），不得在 thinking block 裡自己幻想 4 視角\n3. **必須 Write news_logs/YYYY-MM-DD_digest.json**（timestamp 必須是今天日期），validator 有 freshness gate 會擋舊檔\n4. Stage 1 triage 表直接依 |shallow_score| 排序取前 5 則進 Stage 2 **不要停下等使用者確認**\n5. 跑完 Phase 3 Arbiter + Phase 4 cache patch + validator + 產出 reports/YYYY-MM-DD_news_digest.md\n6. **禁止**：讀昨天 MD 當範本、跳過 Stage 1/2 直接寫 MD、單 model 編 4-view 辯論\n7. 一個 turn 跑完整條 pipeline，不要中途停下。\n8. **每筆 verdict（不論 shallow/deep）必須帶 `published` 欄位**（從 raw.json 對應 news_id 抄過來的 ISO timestamp）— UI 用此算「Xm/Xh ago」freshness。\n\n新聞分析 DIGEST",
    "invest": "SESSION CONFIG: RISK_TOLERANCE={risk_tolerance}\n非互動模式：照 protocol 規則直接執行，不要輸出「請確認」類摘要表停下來等候。Phase 0 cache 策略：< 3h 用現有、否則 L3 重跑。\n\n分析 {ticker}",
    "flash":  "非互動模式：一個 turn 跑完 Stage 2 Deep Debate + Arbiter + 產出 reports MD 報告，不要中途停下等使用者回話。\n\n新聞分析 FLASH {ticker} 近期動態",
    "flash_text": "非互動模式：一個 turn 跑完 Stage 2 Deep Debate + Arbiter + 雙重 artifact 寫入，不要中途停下等使用者回話。輸入是富途推播原文（中英混排），請：\n1. 先抽出事件主體（公司/標的/ticker，若有）\n2. WebFetch 補上下文（最近 24h 相關報導）\n3. 跑 4 視角 inline 辯論（Bull/Bear/Sector/Macro）+ Arbiter\n4. **必須產兩個檔（缺一不可）**：\n   (a) `reports/YYYY-MM-DD_HHMM_news_flash.md` — 完整 Impact Card（review_status: pending）\n   (b) `news/news_logs/YYYY-MM-DD_digest.json` — 讀現有 file，append 一筆 verdict 到 `verdicts[]` 陣列（不要覆寫整個檔）。verdict 必須含：news_id (next available `nNNN`), depth: \"deep\", review_status: \"pending\", headline, headline_zh, source_label, news_type, bull_case, bear_case, sector_view, macro_view, verdict (BULLISH/BEARISH/BINARY/NEUTRAL), net_impact_score (數字), arbiter_reasoning, binary_risk (bool), within_48h (bool), affected_sectors (string list), tickers_mentioned (string list), date (YYYY-MM-DD), published (ISO timestamp — 用 WebFetch 取得的原始發布時間，UI 拿來算 freshness)。**這條是 Dashboard「待審核」tab 顯示卡片的唯一來源 — 沒寫等於沒分析過。**\n\n新聞分析 FLASH \"{headline}\"",
    "review": "非互動模式：一個 turn 跑完擴展辯論 + Arbiter 覆寫 + cache patch + MD 報告，不要中途停下。覆寫 verdict 時請保留原 `published` 欄位（若不存在，從對應 raw.json 補上）。\n\n新聞分析 審核 \"{headline}\"",
    "triage": "非互動模式：只跑 Stage 1 shallow triage，**禁止跑 Stage 2 deep debate**，**禁止寫 digest.json**，**禁止 patch sector_intel.json / phase0.json**。流程：\n1. **必須先執行** `python3 news/fetch_all_news.py --hours 24 --output news/news_logs/` 重撈 4 個源（RSS + Finnhub + FMP + SEC EDGAR）合併成 unified raw.json — 不能直接讀現有 raw，避免吃到舊資料\n2. 讀剛產出的 `news/news_logs/YYYY-MM-DD_raw.json`（已 dedupe + 按 published desc 排序）\n3. 對每則跑 shallow triage（30 字 snap，依 news_protocol_v2.md Stage 1 rubric 給 score -5~+5）\n4. **必須寫 `news/news_logs/YYYY-MM-DD_triage.json`**（不寫等於沒跑），結構：\n```\n{\n  \"timestamp\": ISO,\n  \"mode\": \"TRIAGE\",\n  \"raw_count\": N,\n  \"verdicts\": [{\n    \"news_id\": \"nNNN\", \"depth\": \"shallow\", \"review_status\": \"reviewed\",\n    \"headline\": str, \"headline_zh\": str, \"source_label\": str,\n    \"news_type\": str, \"bull_case\": str(<=30字), \"bear_case\": str(<=30字),\n    \"sector_view\": str(<=30字), \"macro_view\": str(<=30字),\n    \"verdict\": \"BULLISH\"|\"BEARISH\"|\"NEUTRAL\"|\"BINARY\",\n    \"net_impact_score\": float, \"binary_risk\": bool, \"within_48h\": bool,\n    \"affected_sectors\": [str], \"tickers_mentioned\": [str],\n    \"date\": \"YYYY-MM-DD\",\n    \"published\": str (從 raw.json 對應 news_id 抄過來的 ISO timestamp，UI 拿來算 freshness 顏色)\n  }, ...]\n}\n```\n5. 一個 turn 跑完，不要中途停下等候。\n\n新聞分析 TRIAGE",
    "earnings": "非互動模式：照 skills/earnings-analyst/SKILL.md 跑完整 fetch + analyze + validate + render 4 步驟，不要中途停下等使用者確認。**MUST** sequentially run:\n1. `python3 skills/earnings-analyst/scripts/fetch.py {ticker}`（cache hit 也 OK）\n2. `python3 skills/earnings-analyst/scripts/analyze.py {ticker}`\n3. `python3 skills/earnings-analyst/scripts/validate.py {ticker}` — 必須 rc=0\n4. `python3 skills/earnings-analyst/scripts/render.py {ticker}`\n\n結束條件：reports/<DATE>_{ticker}_earnings.md 寫入完成 + validate rc=0。**禁止**：跳步驟、跳 validate、跑到一半停下問問題。\n\n財報 {ticker}",
}
PROTOCOL_LOG_DIRS = {
    "sector":     "sector/scan_logs",
    "news":       "news/scan_logs",
    "invest":     "investment/scan_logs",
    "flash":      "news/scan_logs",
    "flash_text": "news/scan_logs",
    "review":     "news/scan_logs",
    "triage":     "news/scan_logs",
    "earnings":   "skills/earnings-analyst/cache",
}

_protocol_state = {
    "job_id":     None,   # YYYYMMDD_HHMMSS id, None when idle
    "name":       None,   # sector | news
    "status":     "idle", # idle | running | done | error | cancelled
    "started_at": None,
    "ended_at":   None,
    "log_path":   None,
    "error":      None,
    "elapsed_sec": 0,
}
_protocol_lock = threading.Lock()
_protocol_proc = {"p": None}  # mutable holder so cancel can reach it


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _parse_events(path, max_events=40):
    """Parse stream-json log into human-readable event summaries for the UI."""
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw_lines = f.readlines()
    except Exception as e:
        return [{"icon": "⚠", "text": f"log read error: {e}"}]

    events = []
    for ln in raw_lines:
        ln = ln.strip()
        if not ln:
            continue
        # Non-JSON marker lines ("=== protocol=... ===")
        if ln.startswith("==="):
            events.append({"icon": "▸", "text": ln.strip("= ")})
            continue
        if not (ln.startswith("{") or ln.startswith("[")):
            continue
        try:
            ev = json.loads(ln)
        except Exception:
            continue
        t = ev.get("type")
        if t == "system":
            sub = ev.get("subtype", "")
            if sub == "init":
                model = ev.get("model", "")
                events.append({"icon": "🚀", "text": f"Session started ({model})" if model else "Session started"})
        elif t == "assistant":
            msg = ev.get("message", {}) or {}
            for c in (msg.get("content") or []):
                ct = c.get("type")
                if ct == "text":
                    text = (c.get("text") or "").strip()
                    if text:
                        events.append({"icon": "💬", "text": text[:160]})
                elif ct == "tool_use":
                    nm = c.get("name", "tool")
                    inp = c.get("input", {}) or {}
                    if nm == "Bash":
                        cmd = (inp.get("command") or "")[:140]
                        events.append({"icon": "💻", "text": f"Bash: {cmd}"})
                    elif nm in ("Read", "Write", "Edit"):
                        events.append({"icon": "📄", "text": f"{nm}: {inp.get('file_path', '')}"})
                    elif nm in ("Grep", "Glob"):
                        events.append({"icon": "🔍", "text": f"{nm}: {inp.get('pattern') or inp.get('path', '')}"})
                    elif nm == "Skill":
                        events.append({"icon": "🛠", "text": f"Skill: {inp.get('skill', '?')}"})
                    elif nm == "Agent":
                        events.append({"icon": "🤖", "text": f"Agent: {inp.get('description', inp.get('subagent_type', '?'))}"})
                    elif nm == "TaskCreate" or nm == "TaskUpdate":
                        events.append({"icon": "📋", "text": f"{nm}"})
                    else:
                        events.append({"icon": "⚙", "text": f"{nm}"})
        elif t == "user":
            msg = ev.get("message", {}) or {}
            for c in (msg.get("content") or []):
                if c.get("type") == "tool_result":
                    is_err = c.get("is_error", False)
                    # Extract actual error/result text for visibility
                    raw = c.get("content")
                    text_bits = []
                    if isinstance(raw, str):
                        text_bits.append(raw)
                    elif isinstance(raw, list):
                        for blk in raw:
                            if isinstance(blk, dict) and blk.get("type") == "text":
                                text_bits.append(blk.get("text") or "")
                    snippet = " ".join(text_bits).strip().replace("\n", " ")[:180]
                    if is_err:
                        events.append({"icon": "✗", "text": f"tool error: {snippet or 'unknown'}"})
                    elif snippet:
                        events.append({"icon": "✓", "text": snippet})
                    else:
                        events.append({"icon": "✓", "text": "tool result"})
        elif t == "result":
            sub = ev.get("subtype", "")
            usage = ev.get("usage", {}) or {}
            cost = ev.get("total_cost_usd")
            bits = []
            if usage.get("input_tokens")  is not None: bits.append(f"in {usage['input_tokens']}")
            if usage.get("output_tokens") is not None: bits.append(f"out {usage['output_tokens']}")
            if cost is not None: bits.append(f"${cost:.4f}")
            summary = " · ".join(bits) if bits else sub
            events.append({"icon": "✅" if sub == "success" else "⚠", "text": f"Result: {summary}"})

    return events[-max_events:]


def _tail_log(path, lines=50):
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            chunk = min(size, 16384)
            f.seek(size - chunk)
            data = f.read().decode("utf-8", errors="replace")
        return "\n".join(data.splitlines()[-lines:])
    except Exception as e:
        return f"[tail error: {e}]"


def _extract_error_from_log(log_path, rc):
    """When the claude subprocess exits non-zero, mine the stream-json log for the
    actual failure message (e.g. 'API Error: Stream idle timeout') rather than
    leaving the user with a cryptic 'exit code 1'.

    Strategy: scan lines bottom-up, pick the last JSON object of type 'result'
    or 'error', extract `.result` (which claude CLI uses for the terminal
    error string). Fall back to 'exit code <rc>' if nothing parseable found.
    """
    try:
        if not log_path or not os.path.exists(log_path):
            return f"exit code {rc}"
        # Read last ~16KB — more than enough for the final result event
        with open(log_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 16384), os.SEEK_SET)
            tail = f.read().decode("utf-8", errors="replace")
        for line in reversed(tail.splitlines()):
            line = line.strip()
            if not line.startswith("{") or not line.endswith("}"):
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            t = obj.get("type")
            if t == "result":
                # claude CLI result event carries `.result` (the terminal text)
                # plus `.is_error` and `.subtype` for classification
                msg = obj.get("result") or obj.get("error") or ""
                if isinstance(msg, str) and msg.strip():
                    # Trim to a single reasonable line for log display
                    first = msg.strip().splitlines()[0]
                    return first[:280]
                if obj.get("is_error"):
                    return f"error (rc={rc}, subtype={obj.get('subtype')})"
                break
        return f"exit code {rc}"
    except Exception as e:
        return f"exit code {rc} (log parse failed: {e})"


def run_protocol(name, params=None):
    """Spawn `claude -p "<prompt>"` in a daemon thread. Single-job lock.
    params: optional dict for template substitution (e.g. {ticker: "NVDA"}).
    """
    if name not in PROTOCOL_PROMPTS:
        return None, f"unknown protocol: {name}"
    # Validate ticker-scoped protocols
    params = params or {}
    if "{ticker}" in PROTOCOL_PROMPTS[name] and not params.get("ticker"):
        return None, f"protocol '{name}' requires a 'ticker' parameter"
    if "{headline}" in PROTOCOL_PROMPTS[name] and not params.get("headline"):
        return None, f"protocol '{name}' requires a 'headline' parameter"
    # V4.8 invest: RISK_TOLERANCE is required by protocol SESSION CONFIG.
    # Default to MEDIUM when caller omits or sends an invalid value — the protocol
    # non-interactive rule says "don't ask user", so silent server-side default is correct.
    if "{risk_tolerance}" in PROTOCOL_PROMPTS[name]:
        rt = (params.get("risk_tolerance") or "").strip().upper()
        if rt not in ("LOW", "MEDIUM", "HIGH"):
            rt = "MEDIUM"
        params["risk_tolerance"] = rt

    with _protocol_lock:
        if _protocol_state["status"] == "running":
            return None, f"another protocol is running: {_protocol_state['name']}"

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_id = f"{name}_{ts}"
        log_dir = os.path.join(ROOT, PROTOCOL_LOG_DIRS[name])
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{job_id}.log")

        _protocol_state.update({
            "job_id":      job_id,
            "name":        name,
            "status":      "running",
            "started_at":  _now_iso(),
            "ended_at":    None,
            "log_path":    log_path,
            "error":       None,
            "elapsed_sec": 0,
        })

    def _run():
        start = datetime.now()
        # Manual token replacement instead of str.format(**params): some prompts
        # embed JSON examples with literal {…}, which str.format would treat as
        # placeholders and raise KeyError (e.g. KeyError: '\n  "timestamp"').
        prompt = PROTOCOL_PROMPTS[name]
        for _k, _v in (params or {}).items():
            prompt = prompt.replace("{" + _k + "}", str(_v))
        claude_bin = CLAUDE_BIN if os.path.exists(CLAUDE_BIN) else "claude"
        rc = -1
        try:
            lf = open(log_path, "w", buffering=1)
            lf.write(f"=== protocol={name} prompt={prompt!r} started={_now_iso()} ===\n")
            lf.flush()
            # stream-json: every event is one line of JSON → naturally line-buffered.
            # Intentionally NOT passing --include-partial-messages: those emit char-by-char
            # input_json_delta events (~4000 deltas per 34KB Write) which bloat the log
            # without providing info we actually parse. tool_use/tool_result/result events
            # arrive at block-level completion, which is plenty for event tracking.
            proc = subprocess.Popen(
                [claude_bin, "-p", prompt,
                 "--output-format", "stream-json",
                 "--verbose",
                 "--permission-mode", "bypassPermissions"],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env={
                    **os.environ,
                    "PATH": os.environ.get("PATH", "") + ":/Users/kavi/.local/bin",
                    # Strict-mode validator timestamp: digest.json mtime must be ≥ this
                    # to count as "written by this run". Catches Claude skipping Stage 1/2.
                    "NEWS_RUN_START_MS": str(int(start.timestamp() * 1000)),
                },
            )
            _protocol_proc["p"] = proc

            # Reader thread: pipe stdout line-by-line into log file
            def _reader():
                try:
                    for line in iter(proc.stdout.readline, ''):
                        if not line:
                            break
                        lf.write(line)
                        lf.flush()
                except Exception as re:
                    try: lf.write(f"[reader error: {re}]\n")
                    except Exception: pass
                finally:
                    try: proc.stdout.close()
                    except Exception: pass

            rt = threading.Thread(target=_reader, daemon=True)
            rt.start()

            timeout_sec = PROTOCOL_TIMEOUT_OVERRIDES.get(name, PROTOCOL_TIMEOUT_SEC)
            try:
                rc = proc.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                proc.kill()
                rc = -1
                with _protocol_lock:
                    _protocol_state["error"] = f"timeout after {timeout_sec}s (hard kill)"
            rt.join(timeout=3)
            lf.write(f"\n=== ended={_now_iso()} rc={rc} ===\n")
            lf.close()

            with _protocol_lock:
                _protocol_state["ended_at"]    = _now_iso()
                _protocol_state["elapsed_sec"] = int((datetime.now() - start).total_seconds())
                if _protocol_state["status"] == "cancelled":
                    pass
                elif rc == 0:
                    _protocol_state["status"] = "done"
                else:
                    _protocol_state["status"] = "error"
                    if not _protocol_state["error"]:
                        _protocol_state["error"] = _extract_error_from_log(log_path, rc)
            _protocol_proc["p"] = None

            # Success → refresh data.json so Dashboard picks up new state
            if _protocol_state["status"] == "done":
                run_bridge(reason=f"after {name} scan")
        except Exception as e:
            with _protocol_lock:
                _protocol_state["status"]    = "error"
                _protocol_state["error"]     = str(e)
                _protocol_state["ended_at"]  = _now_iso()
                _protocol_state["elapsed_sec"] = int((datetime.now() - start).total_seconds())
            _protocol_proc["p"] = None

    threading.Thread(target=_run, daemon=True).start()
    return job_id, None


# ── Protocol Queue ────────────────────────────────────────────────────────
# Unified FIFO queue for ALL protocol runs (invest / news / flash / flash_text /
# review / triage / sector). Worker pops next when no protocol is running.
# v1.61: extended from invest-only to all protocols. Only 2 invest items in a row
# trigger the 3-min cooldown — light news-side runs go back-to-back.
#
# Entry shape:
#   {"name": "triage", "params": {"ticker":"NVDA",...}, "enqueued_at": "...",
#    "id": "triage_1714512345_abc",  # client-side dedup tag
#    "label": "🗂 Triage" }            # for queue UI display
_protocol_queue = []
_protocol_queue_lock = threading.Lock()
_protocol_history = []  # last 10 completions
_PROTOCOL_HISTORY_MAX = 10

# Backward-compat aliases (existing analyze-queue endpoints + worker name keep working)
_analyze_queue        = _protocol_queue
_analyze_queue_lock   = _protocol_queue_lock
_analyze_history      = _protocol_history
_ANALYZE_HISTORY_MAX  = _PROTOCOL_HISTORY_MAX


def _currently_analyzing_ticker():
    """Return ticker currently being analyzed via invest protocol, or None.
    (Backward-compat for analyze-queue.js widget that only cares about invest.)"""
    with _protocol_lock:
        if _protocol_state.get("status") != "running":
            return None
        if _protocol_state.get("name") != "invest":
            return None
        return _protocol_state.get("analyze_ticker")


def _label_for(name, params):
    """Display label for queue UI — short, recognisable."""
    p = params or {}
    if name == "invest":
        return f"🔬 {p.get('ticker', '?')}"
    if name == "flash":
        return f"⚡ FLASH {p.get('ticker', '?')}"
    if name == "flash_text":
        h = (p.get("headline") or "")[:24]
        return f"⚡ FLASH «{h}»"
    if name == "review":
        h = (p.get("headline") or "")[:24]
        return f"🧑‍⚖ REVIEW «{h}»"
    if name == "news":
        return "📰 DIGEST"
    if name == "triage":
        return "🗂 Triage"
    if name == "sector":
        return "🏭 Sector Scan"
    if name == "earnings":
        return f"📊 Earnings {p.get('ticker', '?')}"
    return name


def enqueue_protocol(name, params=None, source="direct"):
    """Generic enqueue — accepts any protocol name in PROTOCOL_PROMPTS.
    Returns (state, err). err='duplicate' for invest with same ticker pending.
    state: {queued, position, total_ahead, label, id, enqueued_at}.
    """
    if name not in PROTOCOL_PROMPTS:
        return None, f"unknown protocol: {name}"
    params = dict(params or {})
    label  = _label_for(name, params)

    # invest dedup: same ticker queued or running → reject
    if name == "invest":
        ticker = (params.get("ticker") or "").upper().strip()
        if not ticker:
            return None, "missing ticker"
        rt = (params.get("risk_tolerance") or "MEDIUM").upper().strip()
        if rt not in ("LOW", "MEDIUM", "HIGH"):
            rt = "MEDIUM"
        params["ticker"] = ticker
        params["risk_tolerance"] = rt
        active = _currently_analyzing_ticker()
        with _protocol_queue_lock:
            if active == ticker:
                return {"queued": False, "reason": "duplicate_active", "ticker": ticker}, "duplicate"
            if any(q.get("name") == "invest" and (q.get("params") or {}).get("ticker") == ticker
                   for q in _protocol_queue):
                return {"queued": False, "reason": "duplicate_pending", "ticker": ticker}, "duplicate"

    # earnings dedup: same ticker queued or running → reject
    if name == "earnings":
        ticker = (params.get("ticker") or "").upper().strip()
        if not ticker:
            return None, "missing ticker"
        params["ticker"] = ticker
        with _protocol_lock:
            cur = _protocol_state
            if (cur.get("status") == "running" and cur.get("name") == "earnings"
                    and (cur.get("ticker") or "").upper() == ticker):
                return {"queued": False, "reason": "duplicate_active", "ticker": ticker}, "duplicate"
        with _protocol_queue_lock:
            if any(q.get("name") == "earnings" and (q.get("params") or {}).get("ticker") == ticker
                   for q in _protocol_queue):
                return {"queued": False, "reason": "duplicate_pending", "ticker": ticker}, "duplicate"

    entry = {
        "id":          f"{name}_{int(time.time())}_{os.urandom(2).hex()}",
        "name":        name,
        "params":      params,
        "label":       label,
        "source":      source,
        "enqueued_at": _now_iso(),
    }
    # Calc position: 1-indexed across (running + queued)
    running = 0
    with _protocol_lock:
        if _protocol_state.get("status") == "running":
            running = 1
    with _protocol_queue_lock:
        _protocol_queue.append(entry)
        position    = running + len(_protocol_queue)   # 1-indexed: this entry's slot
        total_ahead = position - 1                      # how many in front
    return {
        "queued":      True,
        "id":          entry["id"],
        "name":        name,
        "label":       label,
        "params":      params,
        "position":    position,
        "total_ahead": total_ahead,
        "enqueued_at": entry["enqueued_at"],
    }, None


def enqueue_analysis(ticker, risk_tolerance="MEDIUM"):
    """Backward-compat wrapper for /api/analyze-queue (invest-only)."""
    state, err = enqueue_protocol("invest", {"ticker": ticker, "risk_tolerance": risk_tolerance})
    if state and state.get("queued"):
        # Old endpoint returned different field names — translate
        return {"queued": True, "ticker": ticker, "position": state["position"],
                "enqueued_at": state["enqueued_at"]}, None
    return state, err


def remove_from_queue(target_id_or_ticker):
    """Remove pending entry by id (preferred) or by ticker (legacy invest path).
    Cannot cancel active run."""
    key = (target_id_or_ticker or "").strip()
    with _protocol_queue_lock:
        before = len(_protocol_queue)
        _protocol_queue[:] = [
            q for q in _protocol_queue
            if q.get("id") != key
            and (q.get("params") or {}).get("ticker", "").upper() != key.upper()
        ]
        removed = before - len(_protocol_queue)
    return removed > 0


def get_queue_state():
    """Return {active, queue, recent}.
    active: {ticker, name, label, ...} of currently running (any protocol)
    queue:  list of pending entries
    recent: last 10 completions"""
    active = None
    with _protocol_lock:
        if _protocol_state.get("status") == "running":
            started = _protocol_state.get("started_at")
            elapsed = 0
            if started:
                try:
                    elapsed = int((datetime.now() - datetime.fromisoformat(started)).total_seconds())
                except Exception:
                    pass
            active = {
                "name":        _protocol_state.get("name"),
                "ticker":      _protocol_state.get("analyze_ticker"),     # invest only
                "label":       _protocol_state.get("queue_label"),        # set on dispatch
                "job_id":      _protocol_state.get("job_id"),
                "started_at":  started,
                "elapsed_sec": elapsed,
                "source":      _protocol_state.get("analyze_source", "direct"),
            }
    with _protocol_queue_lock:
        queue_snapshot = [dict(q) for q in _protocol_queue]
        history_snapshot = list(_protocol_history)
    return {"active": active, "queue": queue_snapshot, "recent": history_snapshot}


def _analyze_worker():
    """Background loop: pull next entry off _protocol_queue, dispatch via run_protocol().
    3-min cooldown only between two consecutive invest items (token rate-limit pressure)."""
    last_finished_name = None
    while True:
        try:
            # Wait until queue has work AND no protocol is running
            with _protocol_lock:
                proto_busy = _protocol_state.get("status") == "running"
            with _protocol_queue_lock:
                queue_empty = not _protocol_queue
            if proto_busy or queue_empty:
                time.sleep(1.5)
                continue

            with _protocol_queue_lock:
                if not _protocol_queue:
                    continue
                entry = _protocol_queue.pop(0)

            name   = entry["name"]
            params = entry.get("params") or {}
            label  = entry.get("label", name)

            # Cooldown only if BOTH last and current are invest
            if last_finished_name == "invest" and name == "invest":
                cooldown = int(os.getenv("INTER_ANALYSIS_COOLDOWN_SEC", "180"))
                if cooldown > 0:
                    sys.stderr.write(f"[protocol_worker] cooldown {cooldown}s before next invest\n")
                    time.sleep(cooldown)

            job_id, err = run_protocol(name, params)
            if err:
                with _protocol_queue_lock:
                    _protocol_history.insert(0, {
                        "name":     name,
                        "label":    label,
                        "ticker":   params.get("ticker"),
                        "status":   "error",
                        "error":    err,
                        "ended_at": _now_iso(),
                    })
                    del _protocol_history[_PROTOCOL_HISTORY_MAX:]
                last_finished_name = None
                continue
            with _protocol_lock:
                if name == "invest":
                    _protocol_state["analyze_ticker"] = params.get("ticker")
                _protocol_state["analyze_source"] = entry.get("source", "queue")
                _protocol_state["queue_label"]   = label
                _protocol_state["queue_id"]      = entry.get("id")

            # Wait for run to finish.
            # Defensive: terminal status alone is enough (don't gate on ended_at).
            # Previously required `ended_at` too, but if cancel_protocol left
            # ended_at unset and _run thread hung in post-wait, worker would
            # block forever blocking the rest of the queue.
            while True:
                time.sleep(2)
                with _protocol_lock:
                    s = _protocol_state.get("status")
                if s in ("done", "error", "cancelled", "idle"):
                    break

            with _protocol_lock:
                final_status = _protocol_state.get("status")
                final_error  = _protocol_state.get("error")
            with _protocol_queue_lock:
                _protocol_history.insert(0, {
                    "name":     name,
                    "label":    label,
                    "ticker":   params.get("ticker"),
                    "status":   final_status,
                    "error":    final_error if final_status == "error" else None,
                    "ended_at": _now_iso(),
                })
                del _protocol_history[_PROTOCOL_HISTORY_MAX:]

            last_finished_name = name
        except Exception as e:
            sys.stderr.write(f"[protocol_worker error] {e}\n")
            time.sleep(3)


threading.Thread(target=_analyze_worker, daemon=True).start()


# ── Preflight cache health check ──────────────────────────────────────────
CACHE_TTL_SEC = 10800  # 3 hours — matches bridge.py

PREFLIGHT_ITEMS = [
    {"key": "breadth",    "label": "廣度分數",    "label_en": "Breadth Score",
     "pattern": "sector/breadth_cache/market_breadth_*.json",
     "free": True, "cmd": ["market_breadth_analyzer", "python3",
     os.path.join(os.path.expanduser("~"), ".claude/skills/market-breadth-analyzer/scripts/market_breadth_analyzer.py"),
     "--output-dir", "sector/breadth_cache/"]},
    {"key": "ftd",        "label": "FTD 信號",    "label_en": "FTD Signal",
     "free": True, "cmd": ["ftd", "python3", "sector/ftd_yfinance.py",
     "--output-dir", "sector/ftd_cache/"]},
    {"key": "market_top", "label": "頂部風險",    "label_en": "Top Risk",
     "free": True, "cmd": ["market_top", "python3", "sector/market_top_yfinance.py",
     "--output-dir", "sector/market_top_cache/"]},
    {"key": "rss",        "label": "RSS 新聞源",   "label_en": "RSS Feed",
     "free": True, "cmd": ["rss", "python3", "news/fetch_news_rss.py",
     "--hours", "24", "--output", "news/news_logs/"]},
    {"key": "sector",     "label": "產業情報",     "label_en": "Sector Intel",
     "pattern": "sector/sector_logs/*_sector_intel.json",
     "free": False, "protocol": "sector"},
    {"key": "news",       "label": "新聞 DIGEST",  "label_en": "News DIGEST",
     "pattern": "news/news_logs/*_digest.json",
     "free": False, "protocol": "news"},
]

def _content_timestamp_for(key, path):
    """For cache files where mtime can be touched by *another* protocol's
    cache-patch step (e.g. news Phase 4 prepends top_catalysts into
    sector_intel.json, bumping mtime without updating internal timestamp),
    read the content timestamp instead. Falls back to mtime on parse failure.
    Returns float epoch seconds.
    """
    fallback = os.path.getmtime(path)
    if key not in ("sector", "news"):
        return fallback
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception:
        return fallback
    raw = obj.get("generated_at") if key == "sector" else obj.get("timestamp")
    if not raw or not isinstance(raw, str):
        return fallback
    raw = raw.strip()
    # Try common shapes: ISO with tz, ISO no tz, "YYYY-MM-DD HH:MM:SS", "YYYY-MM-DD HH:MM"
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            # Naive timestamps assumed local time (matches project convention
            # — sector_intel.json/digest.json are written without tz).
            return dt.timestamp()
        except ValueError:
            continue
    return fallback


def preflight_check():
    """Return cache freshness status for all monitored items."""
    results = []
    for item in PREFLIGHT_ITEMS:
        pattern = item.get("pattern")
        if not pattern and item.get("cmd"):
            # For cmd-based items, derive pattern from output dir
            key = item["key"]
            if key == "breadth":  pattern = "sector/breadth_cache/market_breadth_*.json"
            elif key == "ftd":    pattern = "sector/ftd_cache/ftd_detector_*.json"
            elif key == "market_top": pattern = "sector/market_top_cache/market_top_*.json"
            elif key == "rss":    pattern = "news/news_logs/*_raw.json"
        full_pattern = os.path.join(ROOT, pattern) if pattern else None
        latest = None
        if full_pattern:
            files = sorted(glob.glob(full_pattern), key=os.path.getmtime, reverse=True)
            latest = files[0] if files else None
        if latest:
            ref_ts = _content_timestamp_for(item["key"], latest)
            age_sec = int(datetime.now().timestamp() - ref_ts)
            status = "FRESH" if age_sec < CACHE_TTL_SEC else "STALE"
            if age_sec < 60:     age_str = f"{age_sec}s"
            elif age_sec < 3600: age_str = f"{age_sec // 60}m"
            else:                age_str = f"{age_sec / 3600:.1f}h"
        else:
            age_sec = -1
            age_str = "-"
            status = "MISSING"
        results.append({
            "key":      item["key"],
            "label":    item["label"],
            "label_en": item["label_en"],
            "status":   status,
            "age_sec":  age_sec,
            "age_str":  age_str,
            "free":     item.get("free", False),
        })
    return results

_preflight_lock = threading.Lock()
_preflight_state = {"status": "idle", "items_total": 0, "items_done": 0, "errors": []}

def run_free_caches():
    """Run all STALE free caches in sequence, then bridge.py."""
    checks = preflight_check()
    stale_free = [c for c in checks if c["status"] in ("STALE", "MISSING") and c["free"]]
    if not stale_free:
        return 0, "all free caches are fresh"

    with _preflight_lock:
        if _preflight_state["status"] == "running":
            return -1, "preflight already running"
        _preflight_state.update({"status": "running", "items_total": len(stale_free),
                                  "items_done": 0, "errors": []})

    def _run():
        for item_check in stale_free:
            key = item_check["key"]
            item_def = next((i for i in PREFLIGHT_ITEMS if i["key"] == key), None)
            if not item_def or "cmd" not in item_def:
                continue
            cmd_parts = item_def["cmd"][1:]  # skip label at [0]
            try:
                r = subprocess.run(cmd_parts, cwd=ROOT, capture_output=True, text=True, timeout=120)
                if r.returncode != 0:
                    # Capture stderr + stdout tails so user can see what actually went wrong
                    stderr_tail = (r.stderr or "")[-800:]
                    stdout_tail = (r.stdout or "")[-400:]
                    with _preflight_lock:
                        _preflight_state["errors"].append({
                            "key":         key,
                            "rc":          r.returncode,
                            "stderr_tail": stderr_tail,
                            "stdout_tail": stdout_tail,
                        })
            except subprocess.TimeoutExpired:
                with _preflight_lock:
                    _preflight_state["errors"].append({
                        "key": key, "rc": -1, "error": "timeout after 120s",
                    })
            except Exception as e:
                with _preflight_lock:
                    _preflight_state["errors"].append({
                        "key": key, "rc": None, "error": str(e),
                    })
            with _preflight_lock:
                _preflight_state["items_done"] += 1

        # Refresh data.json
        try:
            subprocess.run([sys.executable, os.path.join(ROOT, "bridge.py")],
                           cwd=ROOT, capture_output=True, timeout=60)
        except Exception:
            pass
        with _preflight_lock:
            _preflight_state["status"] = "done"

    threading.Thread(target=_run, daemon=True).start()
    return len(stale_free), None


_momentum_lock = threading.Lock()
_MOM_PROGRESS_RE = re.compile(r'\[screen\]\s+(\d+)/(\d+)\s+\((\d+)\s+errors,\s+(\d+)\s+cache hits\)')
_momentum_state = {
    "status":     "idle",     # idle | running | bridging | done | error
    "phase":      None,        # human label
    "started_at": None,        # epoch float
    "ended_at":   None,
    "csv_path":   None,
    "error":      None,
    "last_params":       None,
    "done":              0,    # tickers processed so far
    "total":             0,    # universe size (set once screen.py reports it)
    "errors_count":      0,    # per-ticker fetch errors
    "cache_hits_count":  0,
    "log_tail":          [],   # last ~200 stderr lines for inline expand panel
}


def _build_screen_cmd(params):
    # Note: no --md-only; we parse stderr summary for CSV path
    cmd = [sys.executable, os.path.join(ROOT, "skills", "momentum-monitor", "scripts", "screen.py")]
    if params.get("universe"):
        cmd += ["--universe", str(params["universe"])]
    elif params.get("tickers"):
        cmd += ["--tickers", str(params["tickers"])]
    else:
        cmd += ["--universe", "all"]
    if params.get("min_score") is not None:
        cmd += ["--min-score", str(params["min_score"])]
    if params.get("top") is not None:
        cmd += ["--top", str(params["top"])]
    if params.get("stage"):
        cmd += ["--stage", str(params["stage"])]
    for sig in params.get("signals", []) or []:
        cmd += ["--signal", str(sig)]
    for w in params.get("exclude_warnings", []) or []:
        cmd += ["--exclude-warning", str(w)]
    if params.get("journal"):
        cmd += ["--journal"]
    return cmd


def run_momentum_screen(params):
    """Start a momentum screen in a background thread.

    Returns (state_snapshot, err_msg). err_msg is non-None only for caller-side
    validation errors (e.g. another scan is already running). Subprocess failures
    surface through the state dict, not this return value.
    """
    with _momentum_lock:
        if _momentum_state["status"] in ("running", "bridging"):
            return _momentum_state.copy(), "another momentum scan is already running"
        _momentum_state.update({
            "status":      "running",
            "phase":       f"scanning {params.get('universe') or 'custom list'}…",
            "started_at":  datetime.now().timestamp(),
            "ended_at":    None,
            "csv_path":    None,
            "error":       None,
            "last_params": {k: v for k, v in params.items() if k not in ()},
            "done":              0,
            "total":             0,
            "errors_count":      0,
            "cache_hits_count":  0,
            "log_tail":          [],
        })

    cmd = _build_screen_cmd(params)

    def _worker():
        ref = {"csv_path": None}
        stderr_tail = []

        try:
            proc = subprocess.Popen(
                cmd, cwd=ROOT,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1,
            )
        except Exception as e:
            with _momentum_lock:
                _momentum_state.update({
                    "status": "error", "error": f"screen.py launch failed: {e}",
                    "ended_at": datetime.now().timestamp(),
                })
            return

        def _reader():
            # Parse screen.py stderr live: "[screen] 150/503 (0 errors, 23 cache hits)"
            for line in iter(proc.stderr.readline, ''):
                stripped = line.rstrip("\n")
                stderr_tail.append(stripped)
                if len(stderr_tail) > 50:
                    stderr_tail.pop(0)  # keep only last 50 lines for error reporting

                # Live log-tail shared with client expand panel (cap 200)
                with _momentum_lock:
                    tail = _momentum_state["log_tail"]
                    tail.append(stripped)
                    if len(tail) > 200:
                        del tail[:len(tail) - 200]

                    m = _MOM_PROGRESS_RE.search(line)
                    if m:
                        _momentum_state["done"]             = int(m.group(1))
                        _momentum_state["total"]            = int(m.group(2))
                        _momentum_state["errors_count"]     = int(m.group(3))
                        _momentum_state["cache_hits_count"] = int(m.group(4))
                if "CSV:" in line:
                    ref["csv_path"] = line.split("CSV:", 1)[1].strip()

        reader = threading.Thread(target=_reader, daemon=True)
        reader.start()

        try:
            rc = proc.wait(timeout=300)
        except subprocess.TimeoutExpired:
            proc.kill()
            with _momentum_lock:
                _momentum_state.update({
                    "status": "error", "error": "screen.py timed out (>5 min)",
                    "ended_at": datetime.now().timestamp(),
                })
            return

        reader.join(timeout=2)

        if rc != 0:
            err = "".join(stderr_tail[-3:]).strip() or "unknown error"
            with _momentum_lock:
                _momentum_state.update({
                    "status": "error", "error": "screen.py failed: " + err,
                    "ended_at": datetime.now().timestamp(),
                })
            return

        with _momentum_lock:
            _momentum_state.update({
                "status":   "bridging",
                "phase":    "refreshing data.json…",
                "csv_path": ref["csv_path"],
            })

        try:
            subprocess.run([sys.executable, os.path.join(ROOT, "bridge.py")],
                           cwd=ROOT, capture_output=True, text=True, timeout=BRIDGE_TIMEOUT_SEC)
        except Exception as e:
            print(f"[momentum-screen] bridge refresh failed: {e}", flush=True)

        with _momentum_lock:
            _momentum_state.update({
                "status":   "done",
                "phase":    "complete",
                "ended_at": datetime.now().timestamp(),
            })

    threading.Thread(target=_worker, daemon=True).start()
    return _momentum_state.copy(), None


def cancel_protocol():
    with _protocol_lock:
        if _protocol_state["status"] != "running":
            # Recovery path: if previously cancelled but ended_at never got set
            # (because _run thread got stuck in proc.wait/lf.close), allow a
            # second cancel call to forcibly mark ended_at so the analyze worker
            # can dispatch the next queued item.
            if _protocol_state["status"] == "cancelled" and not _protocol_state.get("ended_at"):
                _protocol_state["ended_at"] = _now_iso()
                try:
                    started = datetime.fromisoformat(_protocol_state["started_at"])
                    _protocol_state["elapsed_sec"] = int((datetime.now() - started).total_seconds())
                except Exception:
                    pass
                _protocol_proc["p"] = None
                return True
            return False
        _protocol_state["status"] = "cancelled"
        # Set ended_at immediately so worker can proceed even if _run thread
        # gets stuck before its post-wait block runs (claude CLI sometimes
        # ignores SIGTERM / pipes hang on close after kill).
        _protocol_state["ended_at"] = _now_iso()
        try:
            started = datetime.fromisoformat(_protocol_state["started_at"])
            _protocol_state["elapsed_sec"] = int((datetime.now() - started).total_seconds())
        except Exception:
            pass
    proc = _protocol_proc.get("p")
    if proc and proc.poll() is None:
        try:
            proc.terminate()
        except Exception:
            pass
    return True


def run_bridge(reason=""):
    """Run bridge.py in a daemon thread, capture output, update _refresh_state."""
    def _run():
        with _state_lock:
            _refresh_state["in_progress"] = True
            _refresh_state["last_reason"] = reason
        ts = datetime.now().strftime("%H:%M:%S")
        try:
            result = subprocess.run(
                [sys.executable, os.path.join(ROOT, "bridge.py")],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=BRIDGE_TIMEOUT_SEC,
            )
            if result.returncode == 0:
                with _state_lock:
                    _refresh_state["last_ok"]     = _now_iso()
                    _refresh_state["last_error"]  = None
                    _refresh_state["in_progress"] = False
                print(f"[{ts}] bridge.py OK ({reason})", flush=True)
            else:
                err_tail = (result.stderr or result.stdout or f"exit {result.returncode}").strip()
                err_msg  = err_tail[-500:]  # last 500 chars
                with _state_lock:
                    _refresh_state["last_error"]  = err_msg
                    _refresh_state["in_progress"] = False
                    _refresh_state["error_history"].insert(0, {
                        "time": _now_iso(), "reason": reason, "error": err_msg,
                    })
                    _refresh_state["error_history"] = _refresh_state["error_history"][:10]
                print(f"[{ts}] bridge.py FAIL ({reason}): {err_msg[:200]}", flush=True)
        except subprocess.TimeoutExpired:
            with _state_lock:
                _refresh_state["last_error"]  = f"timeout after {BRIDGE_TIMEOUT_SEC}s"
                _refresh_state["in_progress"] = False
                _refresh_state["error_history"].insert(0, {
                    "time": _now_iso(), "reason": reason, "error": "TIMEOUT",
                })
                _refresh_state["error_history"] = _refresh_state["error_history"][:10]
            print(f"[{ts}] bridge.py TIMEOUT ({reason})", flush=True)
        except Exception as e:
            with _state_lock:
                _refresh_state["last_error"]  = str(e)
                _refresh_state["in_progress"] = False
                _refresh_state["error_history"].insert(0, {
                    "time": _now_iso(), "reason": reason, "error": str(e),
                })
                _refresh_state["error_history"] = _refresh_state["error_history"][:10]
            print(f"[{ts}] bridge.py EXCEPTION ({reason}): {e}", flush=True)

    threading.Thread(target=_run, daemon=True).start()


def refresh_loop():
    """Re-run bridge.py every REFRESH_INTERVAL_SEC. Stops on _shutdown."""
    # Seed next_scheduled immediately so UI countdown has something to show
    with _state_lock:
        _refresh_state["next_scheduled"] = (
            datetime.now() + timedelta(seconds=REFRESH_INTERVAL_SEC)
        ).isoformat(timespec="seconds")
    while not _shutdown.wait(REFRESH_INTERVAL_SEC):
        run_bridge(reason=f"periodic {REFRESH_INTERVAL_SEC}s")
        with _state_lock:
            _refresh_state["next_scheduled"] = (
                datetime.now() + timedelta(seconds=REFRESH_INTERVAL_SEC)
            ).isoformat(timespec="seconds")


# ── FRED macro cache refresh ──────────────────────────────────────────
# Runs fred-macro/scripts/fetch.py every FRED_REFRESH_SEC to keep the shared
# cache (skills/fred-macro/cache/fred_latest.json) warm. bridge.py reads from
# that cache so Dashboard always has recent macro data. FRED is free (no quota
# pressure) so we can afford a dedicated refresh cadence independent of the
# main bridge loop.
FRED_REFRESH_SEC = int(os.getenv("FRED_REFRESH_SEC", "3600"))  # 1 hour default — FRED daily series update at most once/day
_FRED_SCRIPT = os.path.join(ROOT, "skills", "fred-macro", "scripts", "fetch.py")


def run_fred_refresh(reason=""):
    """Invoke fred-macro/scripts/fetch.py --no-cache to force a fresh pull.
    Cached by the skill itself (atomic write); we just trigger the refresh."""
    if not os.path.exists(_FRED_SCRIPT):
        return
    if not os.getenv("FRED_API_KEY"):
        # Can't run without the key — skip silently (Dashboard still works via
        # LLM-derived macro in the protocol layer).
        return
    try:
        r = subprocess.run(
            ["python3", _FRED_SCRIPT, "--json-only", "--no-cache"],
            capture_output=True, text=True, timeout=30, cwd=ROOT,
        )
        if r.returncode == 0:
            sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] FRED refresh ok ({reason})\n")
        else:
            sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] FRED refresh failed ({reason}): {r.stderr[:200]}\n")
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] FRED refresh timed out ({reason})\n")
    except Exception as e:
        sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] FRED refresh error ({reason}): {e}\n")


def fred_refresh_loop():
    """Refresh FRED macro cache every FRED_REFRESH_SEC (15 min default).
    Runs as daemon thread alongside the main bridge refresh loop."""
    while not _shutdown.wait(FRED_REFRESH_SEC):
        run_fred_refresh(reason=f"periodic {FRED_REFRESH_SEC}s")


_positions_lock = threading.Lock()


def load_positions():
    if not os.path.exists(POSITIONS):
        return {"positions": []}
    with _positions_lock, open(POSITIONS, "r") as f:
        return json.load(f)


def save_positions(data):
    with _positions_lock, open(POSITIONS, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_id(ticker, entry_date):
    date_clean = entry_date.replace("-", "")
    data = load_positions()
    seq = sum(1 for p in data["positions"] if p["ticker"] == ticker and p["entry_date"] == entry_date) + 1
    return f"pos_{date_clean}_{ticker}_{seq:02d}"


# ── Momentum watchlist (non-SP500 tickers scanned alongside the universe) ──
_watchlist_lock = threading.Lock()
_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,5}$")   # NYSE/NASDAQ style symbols


def load_watchlist():
    if not os.path.exists(WATCHLIST_PATH):
        return []
    with _watchlist_lock, open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return [ln.strip().upper() for ln in f
                if ln.strip() and not ln.startswith("#")]


def save_watchlist(tickers):
    """Atomic write via tmp + rename so we never leave a half-written file."""
    os.makedirs(os.path.dirname(WATCHLIST_PATH), exist_ok=True)
    tmp = WATCHLIST_PATH + ".tmp"
    with _watchlist_lock:
        with open(tmp, "w", encoding="utf-8") as f:
            for t in tickers:
                f.write(t + "\n")
        os.replace(tmp, WATCHLIST_PATH)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {fmt % args}\n")

    def _json(self, code, body):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    # ── Asset cache-busting: inject ?v=<mtime> into .html responses ──
    # Matches src="foo.js" / href="bar.css" for relative paths only.
    # Already-present ?v=... is replaced so HTMLs can be stripped of versions.
    _ASSET_RE = re.compile(
        r'(src|href)="(?!https?:)(?!//)([^"?]+\.(?:js|css))(?:\?[^"]*)?"'
    )

    def _inject_mtimes(self, html_bytes):
        def sub(m):
            attr, asset_path = m.group(1), m.group(2)
            # Resolve mtime against DASHBOARD_DIR (asset paths are relative)
            full = os.path.join(DASHBOARD_DIR, asset_path.lstrip("/"))
            try:
                mtime = int(os.path.getmtime(full))
            except OSError:
                return m.group(0)  # file not found → leave as-is
            return f'{attr}="{asset_path}?v={mtime}"'
        return self._ASSET_RE.sub(sub, html_bytes.decode("utf-8")).encode("utf-8")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/positions":
            return self._json(200, load_positions())
        if path == "/api/refresh_status":
            with _state_lock:
                return self._json(200, dict(_refresh_state))
        if path == "/api/preflight":
            return self._json(200, {"items": preflight_check()})
        if path == "/api/preflight/status":
            with _preflight_lock:
                return self._json(200, dict(_preflight_state))
        if path == "/api/run-momentum-screen/status":
            with _momentum_lock:
                state = dict(_momentum_state)
            if state.get("started_at"):
                end = state.get("ended_at") or datetime.now().timestamp()
                state["elapsed_sec"] = int(end - state["started_at"])
            return self._json(200, state)

        if path == "/api/analyze-queue" or path == "/api/protocol-queue":
            return self._json(200, get_queue_state())

        if path == "/api/momentum-watchlist":
            return self._json(200, {"tickers": load_watchlist()})

        if path.startswith("/api/earnings-cache/"):
            # GET /api/earnings-cache/<TICKER>  → cache existence + summary
            ticker = path.split("/api/earnings-cache/", 1)[1].strip().upper()
            if not ticker or "/" in ticker:
                return self._json(400, {"error": "invalid ticker"})
            cache_dir = os.path.join(ROOT, "skills", "earnings-analyst", "cache")
            matches = sorted(glob.glob(os.path.join(cache_dir, f"{ticker}_*.json")))
            if not matches:
                return self._json(200, {"ticker": ticker, "cached": False})
            latest = matches[-1]
            try:
                with open(latest, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                return self._json(200, {"ticker": ticker, "cached": False, "error": str(e)})

            age_days = round((time.time() - os.path.getmtime(latest)) / 86400, 1)
            last_earn = data.get("last_earnings_date")
            run_date = data.get("as_of_date")
            report_path = None
            if run_date:
                candidate = os.path.join(ROOT, "reports", f"{run_date}_{ticker}_earnings.md")
                if os.path.exists(candidate):
                    report_path = os.path.relpath(candidate, ROOT)
            return self._json(200, {
                "ticker":             ticker,
                "cached":             True,
                "last_earnings_date": last_earn,
                "as_of_date":         run_date,
                "next_earnings_est":  data.get("next_earnings_est"),
                "composite_score":    data.get("composite_score"),
                "verdict":            data.get("verdict"),
                "quality_flags":      data.get("quality_flags") or [],
                "score_components":   data.get("score_components") or {},
                "report_path":        report_path,
                "cache_age_days":     age_days,
            })

        if path == "/api/futu-notifications":
            try:
                qs = urlparse(self.path).query
                params = dict(p.split("=", 1) for p in qs.split("&") if "=" in p)
                limit = max(1, min(20, int(params.get("limit", "5"))))
            except Exception:
                limit = 5
            if _futu is None:
                return self._json(200, {"available": False, "notifications": [],
                                        "error": "helper not loaded"})
            now = time.time()
            with _futu_cache_lock:
                cached = _futu_cache["payload"]
                fresh  = cached and (now - _futu_cache["ts"] < FUTU_CACHE_TTL_SEC) \
                                and cached.get("limit") == limit
            if fresh:
                return self._json(200, cached["payload"])
            try:
                items, stats = _futu.load_notifications(
                    limit=limit, filter_hk_cn=True, return_stats=True,
                )
                payload = {
                    "available":      _futu.is_available(),
                    "notifications":  items,
                    "filter_hk_cn":   True,
                    "filtered_count": stats.get("filtered_hk_cn", 0),
                    "scanned":        stats.get("scanned", 0),
                    "fetched_at":     _now_iso(),
                }
            except Exception as e:
                return self._json(500, {"available": False, "notifications": [],
                                        "error": str(e)})
            with _futu_cache_lock:
                _futu_cache["ts"]      = now
                _futu_cache["payload"] = {"limit": limit, "payload": payload}
            return self._json(200, payload)

        if path == "/api/run-protocol/status":
            with _protocol_lock:
                state = dict(_protocol_state)
            if state.get("status") == "running" and state.get("started_at"):
                try:
                    state["elapsed_sec"] = int(
                        (datetime.now() - datetime.fromisoformat(state["started_at"])).total_seconds()
                    )
                except Exception:
                    pass
            state["log_tail"] = _tail_log(state.get("log_path"), lines=60)
            state["events"]   = _parse_events(state.get("log_path"), max_events=40)
            return self._json(200, state)

        # Serve /decision_review/* from reports/decision_review/ (read-only)
        if path.startswith("/decision_review/"):
            rel = path[len("/decision_review/"):]
            # Block path traversal
            if ".." in rel or rel.startswith("/"):
                self.send_error(400, "bad path")
                return
            full = os.path.join(ROOT, "reports", "decision_review", rel)
            if os.path.isfile(full):
                ctype = ("application/json; charset=utf-8" if full.endswith(".json")
                         else "text/markdown; charset=utf-8" if full.endswith(".md")
                         else "application/octet-stream")
                with open(full, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(404, "not found")
            return

        # Intercept *.html to inject mtime cache-busters
        if path.endswith(".html") or path == "/" or path == "":
            rel = "index.html" if path in ("/", "") else path.lstrip("/")
            full = os.path.join(DASHBOARD_DIR, rel)
            if os.path.isfile(full):
                try:
                    with open(full, "rb") as f:
                        body = self._inject_mtimes(f.read())
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                except Exception as e:
                    sys.stderr.write(f"[html inject error] {e}\n")

        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/positions":
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception as e:
                return self._json(400, {"error": f"invalid JSON: {e}"})

            required = ["ticker", "entry_date", "entry_price", "shares"]
            missing = [k for k in required if not body.get(k) and body.get(k) != 0]
            if missing:
                return self._json(400, {"error": f"missing fields: {missing}"})

            ticker = body["ticker"].upper().strip()
            data = load_positions()
            entry = {
                "id":          generate_id(ticker, body["entry_date"]),
                "ticker":      ticker,
                "entry_date":  body["entry_date"],
                "entry_price": float(body["entry_price"]),
                "shares":      float(body["shares"]),
                "cost_basis":  round(float(body["entry_price"]) * float(body["shares"]), 2),
                "status":      body.get("status", "open"),
                "track":       body.get("track", "manual"),
                "notes":       body.get("notes", ""),
                "report_ref":  body.get("report_ref", ""),
                "created_at":  datetime.now().isoformat(timespec="seconds"),
            }
            data["positions"].append(entry)
            save_positions(data)
            run_bridge(reason=f"POST {entry['ticker']}")
            return self._json(201, entry)

        if path == "/api/preflight/run-free":
            count, err = run_free_caches()
            if err:
                return self._json(409, {"error": err})
            return self._json(202, {"stale_items": count, "status": "running"})

        if path == "/api/run-protocol":
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception as e:
                return self._json(400, {"error": f"invalid JSON: {e}"})
            name = body.get("name", "").strip()
            params = {k: v for k, v in body.items() if k not in ("name",)}
            job_id, err = run_protocol(name, params)
            if err:
                return self._json(409, {"error": err})
            return self._json(202, {"job_id": job_id, "name": name})

        if path == "/api/analyze-queue":
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception as e:
                return self._json(400, {"error": f"invalid JSON: {e}"})
            ticker = body.get("ticker", "")
            rt     = body.get("risk_tolerance", "MEDIUM")
            state, err = enqueue_analysis(ticker, rt)
            if err == "duplicate":
                return self._json(409, state)
            if err:
                return self._json(400, {"error": err})
            return self._json(202, state)

        if path == "/api/protocol-queue":
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception as e:
                return self._json(400, {"error": f"invalid JSON: {e}"})
            name = body.get("name", "").strip()
            params = {k: v for k, v in body.items() if k != "name"}
            state, err = enqueue_protocol(name, params)
            if err == "duplicate":
                return self._json(409, state)
            if err:
                return self._json(400, {"error": err})
            return self._json(202, state)

        if path == "/api/run-protocol/cancel":
            ok = cancel_protocol()
            return self._json(200 if ok else 409, {"cancelled": ok})

        if path == "/api/run-momentum-screen":
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception as e:
                return self._json(400, {"error": f"invalid JSON: {e}"})
            state, err = run_momentum_screen(body)
            if err:
                return self._json(409, {"error": err, "state": state})
            return self._json(202, {"status": "running", "state": state})

        if path == "/api/momentum-watchlist":
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception as e:
                return self._json(400, {"error": f"invalid JSON: {e}"})
            raw = (body.get("ticker") or "").strip().upper()
            if not _TICKER_RE.match(raw):
                return self._json(400, {"error": f"invalid ticker format: {raw!r}"})
            current = load_watchlist()
            if raw in current:
                return self._json(409, {"error": "already in watchlist", "tickers": current})
            current.append(raw)
            save_watchlist(current)
            return self._json(201, {"ticker": raw, "tickers": current})

        return self._json(404, {"error": "not found"})

    def do_PATCH(self):
        path = urlparse(self.path).path
        m = re.match(r"^/api/positions/([\w\-]+)$", path)
        if not m:
            return self._json(404, {"error": "not found"})
        pid = m.group(1)
        length = int(self.headers.get("Content-Length", 0))
        try:
            patch = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as e:
            return self._json(400, {"error": f"invalid JSON: {e}"})

        ALLOWED = {"notes", "status", "track", "shares", "entry_price",
                   "exit_date", "exit_price", "closed_shares"}
        unknown = set(patch.keys()) - ALLOWED
        if unknown:
            return self._json(400, {"error": f"unknown fields: {sorted(unknown)}"})

        data = load_positions()
        target = next((p for p in data["positions"] if p["id"] == pid), None)
        if not target:
            return self._json(404, {"error": f"id not found: {pid}"})

        for k, v in patch.items():
            if k in ("shares", "entry_price", "exit_price", "closed_shares") and v is not None:
                target[k] = float(v)
            else:
                target[k] = v

        # Recompute cost_basis if shares/entry_price changed
        target["cost_basis"] = round(float(target["entry_price"]) * float(target["shares"]), 2)

        # Compute realized_pl when closing (full or partial)
        if target.get("exit_price") is not None and target.get("closed_shares") is not None:
            closed_sh = float(target["closed_shares"])
            target["realized_pl"] = round(
                (float(target["exit_price"]) - float(target["entry_price"])) * closed_sh, 2
            )
            # Auto-set status: closed if all out, trimmed if partial
            if closed_sh >= float(target["shares"]) - 1e-6:
                target["status"] = "closed"
            elif "status" not in patch:
                target["status"] = "trimmed"

        target["updated_at"] = datetime.now().isoformat(timespec="seconds")
        save_positions(data)
        run_bridge(reason=f"PATCH {pid}")
        return self._json(200, target)

    def do_DELETE(self):
        path = urlparse(self.path).path
        m = re.match(r"^/api/positions/([\w\-]+)$", path)
        if m:
            pid = m.group(1)
            data = load_positions()
            before = len(data["positions"])
            data["positions"] = [p for p in data["positions"] if p["id"] != pid]
            if len(data["positions"]) == before:
                return self._json(404, {"error": f"id not found: {pid}"})
            save_positions(data)
            run_bridge(reason=f"DELETE {pid}")
            return self._json(200, {"deleted": pid})

        m = re.match(r"^/api/analyze-queue/([A-Za-z0-9\.\-]+)$", path)
        if m:
            ticker = m.group(1).upper()
            removed = remove_from_queue(ticker)
            if not removed:
                return self._json(404, {"error": f"ticker not in pending queue: {ticker}"})
            return self._json(200, {"removed": ticker})

        # New: cancel queued entry by id (e.g. triage_1714512345_abc)
        m = re.match(r"^/api/protocol-queue/([A-Za-z0-9_\.\-]+)$", path)
        if m:
            qid = m.group(1)
            removed = remove_from_queue(qid)
            if not removed:
                return self._json(404, {"error": f"queue entry not found: {qid}"})
            return self._json(200, {"removed": qid})

        m = re.match(r"^/api/momentum-watchlist/([A-Za-z0-9\.\-]+)$", path)
        if m:
            ticker = m.group(1).upper()
            current = load_watchlist()
            if ticker not in current:
                return self._json(404, {"error": f"not in watchlist: {ticker}"})
            current.remove(ticker)
            save_watchlist(current)
            return self._json(200, {"removed": ticker, "tickers": current})

        return self._json(404, {"error": "not found"})


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    srv.daemon_threads = True  # don't block shutdown on in-flight requests
    print(f"Dashboard server → http://localhost:{PORT}/")
    print(f"Positions API   → http://localhost:{PORT}/api/positions")
    print(f"Serving files from: {DASHBOARD_DIR}")
    print(f"Positions file:     {POSITIONS}")
    print(f"Auto-refresh:       every {REFRESH_INTERVAL_SEC}s (bridge.py)")
    print(f"FRED refresh:       every {FRED_REFRESH_SEC}s (fred-macro cache)")

    # Fresh prices on boot so the first Dashboard load is not stale
    run_bridge(reason="startup")
    # Warm the FRED cache on startup so the first Dashboard load has macro data.
    run_fred_refresh(reason="startup")
    # Background periodic refresh
    refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
    refresh_thread.start()
    fred_thread = threading.Thread(target=fred_refresh_loop, daemon=True)
    fred_thread.start()

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nshutdown")
        _shutdown.set()
        srv.server_close()
