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
from datetime import date, datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT          = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.join(ROOT, "Dashboard")
POSITIONS     = os.path.join(ROOT, "positions.json")
WATCHLIST_PATH = os.path.join(ROOT, "skills", "momentum-monitor", "scripts",
                              "universes", "watchlist.txt")
PORT          = int(os.environ.get("DASHBOARD_PORT", "8080"))

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

# ── Heatmap (S&P 500 + NDX 100 live treemap) ─────────────────────────
# Background polling thread refreshes single-ticker quotes (fan-out) every 10 min
# during US market hours. Universe loaded from static Dashboard/heatmap_universe.json
# (FMP `sp500-constituent` / `nasdaq-constituent` / `batch-quote` are 402 on the
# current plan — see V2.15.x changelog for the migration).
HEATMAP_REFRESH_SEC      = int(os.getenv("HEATMAP_REFRESH_SEC", "600"))   # 10 min
HEATMAP_NEWS_TTL_SEC     = int(os.getenv("HEATMAP_NEWS_TTL_SEC", "1800"))  # 30 min
HEATMAP_UNIVERSE_TTL_SEC = int(os.getenv("HEATMAP_UNIVERSE_TTL_SEC", "64800"))  # 18h
HEATMAP_OUTPUT_FILE      = os.path.join(ROOT, "Dashboard", "heatmap.json")
HEATMAP_UNIVERSE_FILE    = os.path.join(ROOT, "Dashboard", "heatmap_universe.json")
HEATMAP_QUOTE_WORKERS    = int(os.getenv("HEATMAP_QUOTE_WORKERS", "20"))
_HEATMAP_TICKER_RE       = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
# 429 circuit breaker — when FMP rate-limits, pause quote refresh for this long
# instead of re-firing ~500 calls every cycle (and flooding the log).
HEATMAP_RATELIMIT_COOLDOWN = int(os.getenv("HEATMAP_RATELIMIT_COOLDOWN", "1800"))  # 30 min
_heatmap_ratelimit_until = 0.0   # epoch; quote refresh skipped until this time

_heatmap_state = {
    "last_update":         None,   # ISO timestamp (last quote refresh)
    "universe_built_at":   None,   # ISO timestamp (last universe rebuild)
    "tickers":             {},     # ticker → {sector, industry, market_cap, name, price, change_pct, day_low, day_high, volume, prev_close}
    "error":               None,
}
_heatmap_lock      = threading.Lock()
_heatmap_news_cache = {}           # ticker → {ts: epoch, items: [{title, url, published, source}, ...]}
# V2.12.0 — intraday 5-min OHLCV cache for radar K-line drill-down
_heatmap_intraday_cache = {}       # ticker → {ts: epoch, data: {symbol, bars: [...], market_open}}
HEATMAP_INTRADAY_TTL_SEC_OPEN   = int(os.getenv("HEATMAP_INTRADAY_TTL_SEC_OPEN",   "15"))
HEATMAP_INTRADAY_TTL_SEC_CLOSED = int(os.getenv("HEATMAP_INTRADAY_TTL_SEC_CLOSED", "300"))
# V2.12.0 — per-theme mini-heatmap composite cache (theme-detector + heatmap quotes)
_theme_heatmap_cache = {"data": None, "ts": 0}
THEME_HEATMAP_TTL_SEC = int(os.getenv("THEME_HEATMAP_TTL_SEC", "180"))   # 3 min
# V2.13.3 — per-ticker quote cache for theme-heatmap fallback fetch (covers
# small/mid caps in theme-detector representative_stocks that aren't in the
# S&P-500-based heatmap universe). Keyed by ticker, single TTL.
_theme_extra_quote_cache = {}                                            # {sym: (ts, dict)}
THEME_EXTRA_QUOTE_TTL_SEC = int(os.getenv("THEME_EXTRA_QUOTE_TTL_SEC", "180"))
# V2.13.10 — per-ticker PE TTM cache. FMP /stable/ratios-ttm has no batch
# endpoint, so cache aggressively (24h). Filled by background daemon for the
# heatmap universe and lazy-fetched on demand for radar extras.
_heatmap_pe_cache = {}                                                   # {sym: (ts, {pe_ttm, ev_ebitda, fwd_eps})}
_heatmap_pe_lock  = threading.Lock()
HEATMAP_PE_TTL_SEC = int(os.getenv("HEATMAP_PE_TTL_SEC", "86400"))       # 24h
# V2.13.5 — fast live-quote cache for radar K-line tail (5s TTL, single ticker
# per request, FMP quote-short endpoint). Decoupled from intraday-bars cache so
# the K-line popup can build a 15s tick tail between 5-min bar boundaries.
_heatmap_quote_cache = {}                                                # {sym: (ts, dict)}
HEATMAP_QUOTE_TTL_SEC = int(os.getenv("HEATMAP_QUOTE_TTL_SEC", "5"))

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
# Lets the Dashboard trigger a model CLI to execute a protocol (sector/news/invest).
# Single-job lock: one protocol at a time to avoid runaway token burn.
CLAUDE_BIN = os.environ.get("CLAUDE_BIN") or "/Users/kavi/.local/bin/claude"
AGY_BIN    = os.environ.get("AGY_BIN")    or "agy"
CODEX_BIN  = os.environ.get("CODEX_BIN")  or "/usr/local/bin/codex"

# Multi-model governance — protocols route through the governor (claude first;
# gemini/codex only as quota fallback). Soft-import so the server still boots
# if the module is missing.
try:
    from scripts._shared import model_router as _mrouter
    MODEL_ROUTER_AVAILABLE = True
except Exception as _mr_e:
    MODEL_ROUTER_AVAILABLE = False
    sys.stderr.write(f"[model_router] load failed: {_mr_e}\n")


def _protocol_command(model, prompt):
    """Build the CLI argv for running an agentic protocol on `model`.
    The stdout reader just pipes to the log, so only the command differs."""
    if model == "gemini":
        return [AGY_BIN, "--print", prompt,
                "--dangerously-skip-permissions"]
    if model == "codex":
        return [CODEX_BIN, "exec", prompt, "--json", "-C", ROOT,
                "--dangerously-bypass-approvals-and-sandbox", "--color", "never"]
    claude_bin = CLAUDE_BIN if os.path.exists(CLAUDE_BIN) else "claude"
    return [claude_bin, "-p", prompt,
            "--output-format", "stream-json", "--verbose",
            "--permission-mode", "bypassPermissions"]
# Global default (25 min); news DIGEST normally finishes in 1-2 min, so give it
# a tighter ceiling (12 min) — past runs that crossed 10 min have all been
# pathological (e.g. Claude looping on a Bash-heredoc write that hits Stream
# Idle Timeout, burning 2h+ of tokens for nothing).
PROTOCOL_TIMEOUT_SEC = int(os.getenv("PROTOCOL_TIMEOUT_SEC", "1500"))
PROTOCOL_TIMEOUT_OVERRIDES = {
    # V3.6.1 — a 2026-05-18 run hit 33 min (52 turns) and got killed despite
    # succeeding. The build_sector_intel.py refactor should pull turn count back
    # down; 45 min cap is headroom so a slow-but-valid run is never killed.
    "sector":     int(os.getenv("SECTOR_TIMEOUT_SEC",     "2700")),  # 45 min
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
    # LLM Review of decision_review/event_index — 3-step statistical analysis,
    # event_index can be 300KB+ JSON, expect deeper reasoning pass.
    "llm_review": int(os.getenv("LLM_REVIEW_TIMEOUT_SEC", "900")),   # 15 min
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
    "earnings": "非互動模式：照 skills/earnings-analyst/SKILL.md 跑完整 6 步驟（含 LLM narrate phase），不要中途停下等使用者確認。**MUST** sequentially run:\n1. `python3 skills/earnings-analyst/scripts/fetch.py {ticker}`（cache hit 也 OK；V1.73 抓 17 endpoints 含 transcript）\n2. `python3 skills/earnings-analyst/scripts/analyze.py {ticker}`\n3. `python3 skills/earnings-analyst/scripts/validate.py {ticker}` — 必須 rc=0\n4. **NARRATE phase（LLM in-conversation, NEW）** — 用 Read 工具讀 `skills/earnings-analyst/cache/{ticker}_<DATE>.json`（含 ~50K 字 transcript.content），用 Write 工具寫 `skills/earnings-analyst/cache/{ticker}_<DATE>.infographic.json`。Schema 見 `skills/earnings-analyst/schema.md` 「Infographic Cache (V1.0)」section。必抽：headline_oneliner / surprise / segments_q（**優先從 transcript CFO 段抽季度數字，無則退化 FY**） / capital_returns（buyback authorization、dividend hike、announcements）/ ceo_quote / key_highlights (≥3) / summary (≥2)\n5. `python3 skills/earnings-analyst/scripts/render.py {ticker}`\n6. `python3 skills/earnings-analyst/scripts/validate_infographic.py {ticker}` — 必須 rc=0\n\n結束條件：reports/<DATE>_{ticker}_earnings.md + cache/<TICKER>_<DATE>.infographic.json 都寫入 + 兩個 validate 都 rc=0。**禁止**：跳步驟、跳 validate、跑到一半停下問問題。\n\n財報 {ticker}",
    "llm_review": "非互動模式：對決策日曆做統計檢討，一個 turn 跑完不要中途停下。流程：\n0. **必須先 rebuild event_index**：`python3 scripts/build_event_index.py` — 此 indexer 掃 reports/ + investment/invest_logs/ + news/news_logs/ + sector/sector_logs/ 重建 `reports/decision_review/event_index_latest.json`（含每筆 decision 的 verdict、新增 `industry_rollup` + `adjustment_ledger_active` 兩個 top-level 欄位）。**rc 必須 0** 才繼續；rc≠0 就 fail 整個 protocol、不要硬跑舊 index。預期 ~30-60 秒。\n1. **Read** `reports/decision_review/REVIEW_PROMPT.md` 拿到完整 prompt 規範（**四步驟**：Step 0 Adjustment Evaluation + Step 1 Pattern + Step 2 Root Cause + Step 3 Recommendations）\n2. **Read** 剛 rebuild 的 `reports/decision_review/event_index_latest.json`（過去決策 + verdict 集合 + industry_rollup + adjustment_ledger_active，可能 300KB+）。確認 `generated_at` 是今天日期，否則 abort\n3. 依 REVIEW_PROMPT 四步驟執行：\n   - **Step 0 — Adjustment Evaluation（先做）**：對 `adjustment_ledger_active` 中每筆 active Rec，從 industry_rollup / decisions / 外部資料拉出 `target_metric` 當週數值，對照 ledger 的 `evaluation_history` 上次值，下 improved / no_change / regressed 判斷。連 3 週 no_change 建議 paused；regressed 建議 rolled-back。完整 ledger 在 `reports/decision_review/ADJUSTMENT_LEDGER.md`，schema 在 `ADJUSTMENT_LEDGER_SCHEMA.md`\n   - Step 1 — Pattern Detection：依 source / verdict / window_complete_pct / decisive_agent / regime / sub_industry_heat 統計顯著 pattern (N≥5 才算 pattern；N=3-4 標 preliminary；N≤2 標 speculation)。**必看 `industry_rollup`** 找 sub-industry / sector 集中性\n   - Step 2 — Root Cause Hypotheses：對每個 pattern 提出 1-2 個假設，引用 specific decision_id 為證據\n   - Step 3 — Adjustment Recommendations：給 protocol/config 具體調整建議（agent 權重、score 閾值、cycle phase 規則等），標 confidence (high/med/low) + 影響範圍\n4. **Write** 結果到 `reports/decision_review/REVIEW_<TODAY>.md`（YYYY-MM-DD 為今天日期）。Markdown 結構：\n```markdown\n# LLM Review · YYYY-MM-DD\n\n_event_index_at: <event_index 的 generated_at>_  \n_decisions_analyzed: <N>_\n\n## 0. Adjustment Evaluation\n| Rec | applied_date | target_metric | last_value | this_week_value | judgement |\n|---|---|---|---|---|---|\n\n## Pattern Detection\n### <Pattern Title> (n=N, N≥5 robust / N=3-4 preliminary / N≤2 speculation)\n- 證據：<引用 specific decisions>\n- 統計：<numbers>\n\n## Industry Rollup\n| industry | sector | n | miss_rate | avg_miss_return | tickers | top_30%? |\n|---|---|---|---|---|---|---|\n\n## Root Cause Hypotheses\n### <Hypothesis>\n- 對應 pattern：<which>\n- 推論：<reasoning>\n\n## Adjustment Recommendations\n### <Recommendation Title>\n- 動作：<concrete config change>\n- Confidence：high|med|low\n- 影響：<scope>\n```\n5. **禁止**：跳過 Step 0 indexer rebuild、跳過 Adjustment Evaluation、跑到一半停下問問題、輸出意見徵詢、未產出 MD 就結束。\n\n決策日曆 LLM Review",
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
    "llm_review": "reports/decision_review",
    "earnings_preview": "skills/earnings-valuation-forecaster/cache",
    "supply_chain_generate": "nexus/supply_chain_logs",
}

# V2.15.0 — Script protocols: bypass Claude conversation, run a Python script
# directly. Cheaper (~$0/run vs $0.02-0.05 per Claude turn) and faster (~30s vs
# 30-60s Claude wrap). Reuses the same _protocol_queue / _protocol_state /
# status polling infra so UX is identical to other protocols (banner / cancel /
# history). The cmd is a list with `{ticker}` placeholders substituted at
# dispatch time.
SCRIPT_PROTOCOLS = {
    "earnings_preview": {
        "cmd": ["python3", "skills/earnings-valuation-forecaster/scripts/forecast.py",
                "--pre-earnings", "--output-dir", "reports/", "{ticker}"],
        "label_template": "📋 Preview {ticker}",
        "timeout": int(os.getenv("PREVIEW_TIMEOUT_SEC", "180")),  # 3 min
        "requires": ["ticker"],
    },
}

CUSTOM_PROTOCOLS = {
    "supply_chain_generate": {
        "requires": ["theme"],
        "timeout": int(os.getenv("SUPPLY_CHAIN_GENERATE_TIMEOUT_SEC", "360")),
    },
}

# Post-run validator gate. Catches Claude returning rc=0 while leaving the
# protocol artifact incomplete (e.g. sector run halts after Phase 4 without
# emitting Phase 5 synthesis). If validator rc≠0, status flips to "error".
PROTOCOL_VALIDATORS = {
    "sector": ["sector/scripts/validate_sector_intel.py"],
    "news":   ["news/scripts/validate_digest_output.py"],
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

# V2.7.17 — daily_update.sh shell pipeline state (parallel to Claude protocol queue)
# Tracks the bash daily_update.sh subprocess used by the new pre-market check
# orchestrator. Independent from Claude protocols so it can run in parallel
# with news / sector queue jobs.
_daily_update_state = {
    "job_id":      None,
    "status":      "idle",     # idle | running | done | error
    "started_at":  None,
    "ended_at":    None,
    "log_path":    None,
    "returncode":  None,
    "current_step": 0,
    "total_steps":  6,
    "elapsed_sec": 0,
    "log_tail":    "",
}
_daily_update_lock = threading.Lock()
_daily_update_proc = {"p": None}


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


def _run_script_protocol(name, params=None):
    """V2.15.0 — dispatch a SCRIPT_PROTOCOLS entry as a plain subprocess.
    Mirrors run_protocol's state machine (status / log / cancel hook) so the
    Dashboard banner / polling / queue history all work identically.
    """
    spec = SCRIPT_PROTOCOLS[name]
    params = params or {}
    for req in spec.get("requires", []):
        if not params.get(req):
            return None, f"protocol '{name}' requires '{req}'"

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
            "ticker":      params.get("ticker"),
        })

    def _run():
        start = datetime.now()
        # Substitute placeholders in cmd
        cmd = []
        for tok in spec["cmd"]:
            for k, v in params.items():
                tok = tok.replace("{" + k + "}", str(v))
            cmd.append(tok)
        rc = -1
        try:
            lf = open(log_path, "w", buffering=1)
            lf.write(f"=== script_protocol={name} cmd={cmd!r} started={_now_iso()} ===\n")
            lf.flush()
            proc = subprocess.Popen(
                cmd, cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, bufsize=1,
                env={**os.environ, "PATH": os.environ.get("PATH", "") + ":/Users/kavi/.local/bin"},
            )
            _protocol_proc["p"] = proc

            def _reader():
                try:
                    for line in iter(proc.stdout.readline, ''):
                        if not line: break
                        lf.write(line); lf.flush()
                except Exception as re:
                    try: lf.write(f"[reader error: {re}]\n")
                    except Exception: pass
                finally:
                    try: proc.stdout.close()
                    except Exception: pass

            rt = threading.Thread(target=_reader, daemon=True)
            rt.start()
            try:
                rc = proc.wait(timeout=spec.get("timeout", 180))
            except subprocess.TimeoutExpired:
                proc.kill()
                rc = -1
                with _protocol_lock:
                    _protocol_state["error"] = f"timeout after {spec.get('timeout', 180)}s (hard kill)"
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
                        _protocol_state["error"] = f"script exited rc={rc}"
            _protocol_proc["p"] = None
            # No bridge re-run for script protocols — they don't change data.json
        except Exception as e:
            with _protocol_lock:
                _protocol_state["status"]      = "error"
                _protocol_state["error"]       = str(e)
                _protocol_state["ended_at"]    = _now_iso()
                _protocol_state["elapsed_sec"] = int((datetime.now() - start).total_seconds())
            _protocol_proc["p"] = None

    threading.Thread(target=_run, daemon=True).start()
    return job_id, None


def _run_custom_protocol(name, params=None):
    """Dispatch in-process queued jobs that are not agentic protocols."""
    params = params or {}
    spec = CUSTOM_PROTOCOLS[name]
    for req in spec.get("requires", []):
        if not params.get(req):
            return None, f"protocol '{name}' requires '{req}'"
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
            "ticker":      None,
            "params":      params,
        })

    def _run():
        start = datetime.now()
        try:
            with open(log_path, "w", buffering=1, encoding="utf-8") as lf:
                lf.write(f"=== custom_protocol={name} params={params!r} started={_now_iso()} ===\n")
                if name == "supply_chain_generate":
                    if not SUPPLY_CHAIN_AVAILABLE:
                        raise RuntimeError("supply_chain module not loaded")
                    theme = str(params.get("theme") or "").strip()
                    if not theme:
                        raise RuntimeError("missing theme")
                    lf.write(f"theme={theme}\n")
                    chain = _sc.enrich(_sc.generate(theme))
                    _sc_cache[chain["id"]] = {"data": chain, "ts": time.time()}
                    lf.write(f"generated id={chain.get('id')} nodes={len(chain.get('nodes') or [])} "
                             f"edges={len(chain.get('edges') or [])}\n")
                else:
                    raise RuntimeError(f"unknown custom protocol: {name}")
                lf.write(f"=== ended={_now_iso()} ok ===\n")
            with _protocol_lock:
                _protocol_state["ended_at"] = _now_iso()
                _protocol_state["elapsed_sec"] = int((datetime.now() - start).total_seconds())
                if _protocol_state["status"] != "cancelled":
                    _protocol_state["status"] = "done"
        except Exception as e:
            try:
                with open(log_path, "a", encoding="utf-8") as lf:
                    lf.write(f"\n=== error={_now_iso()} ===\n{e}\n")
            except Exception:
                pass
            with _protocol_lock:
                _protocol_state["status"] = "error"
                _protocol_state["error"] = str(e)
                _protocol_state["ended_at"] = _now_iso()
                _protocol_state["elapsed_sec"] = int((datetime.now() - start).total_seconds())

    threading.Thread(target=_run, daemon=True).start()
    return job_id, None


def run_protocol(name, params=None):
    """Spawn `claude -p "<prompt>"` in a daemon thread. Single-job lock.
    params: optional dict for template substitution (e.g. {ticker: "NVDA"}).

    V2.15.0: when name is in SCRIPT_PROTOCOLS, dispatch via _run_script_protocol
    instead of spawning Claude — bypasses LLM for pure subprocess work.
    """
    if name in CUSTOM_PROTOCOLS:
        return _run_custom_protocol(name, params)
    if name in SCRIPT_PROTOCOLS:
        return _run_script_protocol(name, params)
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
        # Governor picks the model — claude first, gemini/codex only when
        # claude is over budget / in a quota cooldown.
        proto_model = _mrouter.pick_model("protocol") if MODEL_ROUTER_AVAILABLE else "claude"
        rc = -1
        try:
            lf = open(log_path, "w", buffering=1)
            lf.write(f"=== protocol={name} model={proto_model} prompt={prompt!r} started={_now_iso()} ===\n")
            lf.flush()
            # stream-json: every event is one line of JSON → naturally line-buffered.
            # Intentionally NOT passing --include-partial-messages: those emit char-by-char
            # input_json_delta events (~4000 deltas per 34KB Write) which bloat the log
            # without providing info we actually parse. tool_use/tool_result/result events
            # arrive at block-level completion, which is plenty for event tracking.
            proc = subprocess.Popen(
                _protocol_command(proto_model, prompt),
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

            # Record this run against the model's daily budget; a quota wall in
            # the log tail trips its cooldown so the next run routes elsewhere.
            if MODEL_ROUTER_AVAILABLE:
                try:
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as _lf:
                        _tail = _lf.read()[-4000:]
                    _mrouter.note_run(proto_model, rc == 0, "" if rc == 0 else _tail)
                except Exception:
                    pass

            # Validator gate: rc=0 alone is not enough — Claude can finish a
            # turn without emitting the required artifact. Run the per-protocol
            # validator and downgrade to "error" when rc≠0.
            validator_err = None
            if rc == 0 and name in PROTOCOL_VALIDATORS:
                try:
                    vr = subprocess.run(
                        [sys.executable, *[os.path.join(ROOT, p) for p in PROTOCOL_VALIDATORS[name]]],
                        cwd=ROOT, capture_output=True, text=True, timeout=60,
                    )
                    if vr.returncode != 0:
                        tail = (vr.stdout or vr.stderr or "").strip().splitlines()
                        head_lines = "; ".join(tail[:5])[:400]
                        validator_err = f"validator rc={vr.returncode}: {head_lines}"
                        try:
                            with open(log_path, "a") as _lf:
                                _lf.write(f"\n=== validator FAILED rc={vr.returncode} ===\n")
                                _lf.write((vr.stdout or "") + (vr.stderr or ""))
                        except Exception:
                            pass
                except Exception as ve:
                    validator_err = f"validator exception: {ve}"

            with _protocol_lock:
                _protocol_state["ended_at"]    = _now_iso()
                _protocol_state["elapsed_sec"] = int((datetime.now() - start).total_seconds())
                if _protocol_state["status"] == "cancelled":
                    pass
                elif rc == 0 and validator_err is None:
                    _protocol_state["status"] = "done"
                else:
                    _protocol_state["status"] = "error"
                    if not _protocol_state["error"]:
                        _protocol_state["error"] = validator_err or _extract_error_from_log(log_path, rc)
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
    if name == "supply_chain_generate":
        theme = str(p.get("theme") or "?")[:24]
        return f"🔗 Supply {theme}"
    if name in SCRIPT_PROTOCOLS:
        tpl = SCRIPT_PROTOCOLS[name].get("label_template", name)
        return tpl.replace("{ticker}", str(p.get("ticker", "?")))
    return name


def enqueue_protocol(name, params=None, source="direct"):
    """Generic enqueue — accepts any protocol name in PROTOCOL_PROMPTS.
    Returns (state, err). err='duplicate' for invest with same ticker pending.
    state: {queued, position, total_ahead, label, id, enqueued_at}.
    """
    if name not in PROTOCOL_PROMPTS and name not in SCRIPT_PROTOCOLS and name not in CUSTOM_PROTOCOLS:
        return None, f"unknown protocol: {name}"
    params = dict(params or {})
    label  = _label_for(name, params)

    # Script protocols: validate required params + dedup by ticker
    if name in SCRIPT_PROTOCOLS:
        spec = SCRIPT_PROTOCOLS[name]
        for req in spec.get("requires", []):
            if not params.get(req):
                return None, f"missing {req}"
        ticker = (params.get("ticker") or "").upper().strip()
        if ticker:
            params["ticker"] = ticker
            with _protocol_lock:
                cur = _protocol_state
                if (cur.get("status") == "running" and cur.get("name") == name
                        and (cur.get("ticker") or "").upper() == ticker):
                    return {"queued": False, "reason": "duplicate_active", "ticker": ticker}, "duplicate"
            with _protocol_queue_lock:
                if any(q.get("name") == name and (q.get("params") or {}).get("ticker") == ticker
                       for q in _protocol_queue):
                    return {"queued": False, "reason": "duplicate_pending", "ticker": ticker}, "duplicate"

    if name == "supply_chain_generate":
        theme = str(params.get("theme") or "").strip()
        if not theme:
            return None, "missing theme"
        params["theme"] = theme
        slug = _sc.slugify(theme) if SUPPLY_CHAIN_AVAILABLE else theme.lower().replace(" ", "_")[:48]
        params["slug"] = slug
        with _protocol_lock:
            cur = _protocol_state
            if (cur.get("status") == "running" and cur.get("name") == name
                    and ((cur.get("params") or {}).get("slug") == slug
                         or cur.get("queue_label") == _label_for(name, params))):
                return {"queued": False, "reason": "duplicate_active", "theme": theme}, "duplicate"
        with _protocol_queue_lock:
            if any(q.get("name") == name and (q.get("params") or {}).get("slug") == slug
                   for q in _protocol_queue):
                return {"queued": False, "reason": "duplicate_pending", "theme": theme}, "duplicate"

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
                "ticker":      _protocol_state.get("analyze_ticker"),     # any ticker-scoped protocol; None for DIGEST/sector
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
                # Always overwrite analyze_ticker — None for ticker-less protocols
                # (news/DIGEST, sector, triage, flash_text, review). Conditional set
                # caused stale-ticker leak: a prior invest CRWV would persist into
                # the next news run's proto-pill ("news · CRWV") because the field
                # wasn't cleared on dispatch. Bug 2026-05-03.
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


# V2.7.17 — daily_update.sh shell pipeline runner
_DAILY_UPDATE_STEP_RE = re.compile(r"\[\s*(\d+(?:\.\d+)?)\s*/\s*(\d+)\s*\]")

def run_daily_update():
    """Spawn bash daily_update.sh in a background thread, parse [N/6] step
    markers from stdout, expose status via _daily_update_state. Used by the
    pre-market check Phase 1 orchestrator (parallel to news Claude protocol)."""
    script = os.path.join(ROOT, "daily_update.sh")
    if not os.path.exists(script):
        return None, f"daily_update.sh not found at {script}"

    job_id = "daily_update_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(ROOT, "sector", "scan_logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{job_id}.log")

    with _daily_update_lock:
        _daily_update_state.update({
            "job_id":       job_id,
            "status":       "running",
            "started_at":   _now_iso(),
            "ended_at":     None,
            "log_path":     log_path,
            "returncode":   None,
            "current_step": 0,
            "total_steps":  6,
            "elapsed_sec":  0,
            "log_tail":     "",
            "error":        None,
        })

    def _run():
        try:
            with open(log_path, "w", encoding="utf-8") as logf:
                proc = subprocess.Popen(
                    ["/bin/bash", script],
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env={**os.environ, "PATH": os.environ.get("PATH", "")},
                )
                _daily_update_proc["p"] = proc
                # Stream stdout line-by-line; parse [N/6] step markers
                for line in proc.stdout:
                    logf.write(line)
                    logf.flush()
                    m = _DAILY_UPDATE_STEP_RE.search(line)
                    if m:
                        try:
                            step_num = float(m.group(1))
                            total    = int(m.group(2))
                            with _daily_update_lock:
                                # Sub-steps like 5.5 → floor for progress bar
                                _daily_update_state["current_step"] = int(step_num)
                                _daily_update_state["total_steps"]  = total
                        except Exception:
                            pass
                rc = proc.wait()
            with _daily_update_lock:
                _daily_update_state["returncode"] = rc
                _daily_update_state["ended_at"]   = _now_iso()
                _daily_update_state["status"]     = "done" if rc == 0 else "error"
                if rc != 0:
                    _daily_update_state["error"] = f"daily_update.sh exited rc={rc}"
                _daily_update_state["current_step"] = _daily_update_state["total_steps"]
        except Exception as e:
            with _daily_update_lock:
                _daily_update_state["status"]   = "error"
                _daily_update_state["ended_at"] = _now_iso()
                _daily_update_state["error"]    = str(e)
        finally:
            _daily_update_proc["p"] = None

    threading.Thread(target=_run, daemon=True).start()
    return job_id, None


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


# V2.13.11 — server-side pre-market chain orchestrator. Replaces the old
# frontend-driven chain in script.js::runPremarketChain which was race-prone
# (could miss the 'done' transition between news → sector and never enqueue
# sector). State machine runs in a daemon thread, polls _daily_update_state +
# _protocol_history (durable record of completions), so transitions can't be
# missed even if the UI tab is closed.
_premarket_chain_lock = threading.Lock()
_premarket_chain_state = {
    "status":      "idle",     # idle | running | done | error
    "started_at":  None,
    "ended_at":    None,
    "phase":       None,       # phase_1 | phase_2 | done
    "elapsed_sec": 0,
    "items": {
        "daily":  {"status": "idle", "elapsed_sec": 0, "reason": None, "error": None},
        "news":   {"status": "idle", "elapsed_sec": 0, "reason": None, "error": None},
        "sector": {"status": "idle", "elapsed_sec": 0, "reason": None, "error": None},
    },
    "error":       None,
}


def _wait_protocol_completion(name, history_baseline, timeout_sec, on_progress=None):
    """Block until a fresh entry for protocol `name` appears in _protocol_history
    (i.e. completion happened AFTER history_baseline). Calls on_progress(running,
    elapsed) every 2s while waiting. Returns the history entry dict on success,
    raises RuntimeError on timeout."""
    t0 = time.time()
    while True:
        time.sleep(2)
        with _protocol_lock:
            cur_name    = _protocol_state.get("name")
            cur_status  = _protocol_state.get("status")
            cur_started = _protocol_state.get("started_at")
        cur_elapsed = (
            int((datetime.now() - datetime.fromisoformat(cur_started)).total_seconds())
            if cur_started else 0
        )
        with _protocol_queue_lock:
            history = list(_protocol_history)
        # New completions are at index [0..N-baseline)
        new_completions = history[: max(0, len(history) - history_baseline)]
        match = next((h for h in new_completions if h.get("name") == name), None)
        if match:
            return match
        if on_progress:
            running = (cur_name == name and cur_status == "running")
            on_progress(running, cur_elapsed if running else int(time.time() - t0))
        if time.time() - t0 > timeout_sec:
            raise RuntimeError(f"{name} timeout (>{timeout_sec}s)")


def run_premarket_chain():
    """Server-side daily → news → sector orchestrator with freshness skip per item.
    Idempotent: returns ("duplicate_active", reason) if already running.
    Spawns a daemon thread; immediately returns ("started", None)."""
    with _premarket_chain_lock:
        if _premarket_chain_state.get("status") == "running":
            return None, "duplicate_active"
        _premarket_chain_state.update({
            "status":      "running",
            "started_at":  _now_iso(),
            "ended_at":    None,
            "phase":       "phase_1",
            "elapsed_sec": 0,
            "items": {
                "daily":  {"status": "idle", "elapsed_sec": 0, "reason": None, "error": None},
                "news":   {"status": "idle", "elapsed_sec": 0, "reason": None, "error": None},
                "sector": {"status": "idle", "elapsed_sec": 0, "reason": None, "error": None},
            },
            "error":       None,
        })

    def _set_item(key, **kv):
        with _premarket_chain_lock:
            _premarket_chain_state["items"][key].update(kv)
            _premarket_chain_state["elapsed_sec"] = int(
                (datetime.now() - datetime.fromisoformat(_premarket_chain_state["started_at"])).total_seconds()
            )

    def _run():
        start = datetime.now()
        try:
            # ── Phase 1: daily_update + news (concurrent) ──────────
            # V2.17.6 — daily_update.sh and news protocol are independent
            # (daily writes data.json, news fetches RSS/Finnhub/FMP/SEC; no
            # cross-dependency). Run them in parallel to halve Phase 1 wall
            # clock. Phase 2 sector waits for both.
            phase1_errors = []

            def _run_daily():
                checks = preflight_check()
                free = [c for c in checks if c.get("free")]
                free_stale = [c for c in free if c.get("status") != "FRESH"]
                if free and not free_stale:
                    _set_item("daily", status="skipped", reason="all_free_caches_fresh")
                    return
                _set_item("daily", status="running")
                try:
                    run_daily_update()
                except Exception as e:
                    _set_item("daily", status="error", error=str(e))
                    phase1_errors.append(("daily", str(e)))
                    return
                while True:
                    time.sleep(2)
                    with _daily_update_lock:
                        s = _daily_update_state.get("status")
                        sa = _daily_update_state.get("started_at")
                    elapsed = int((datetime.now() - datetime.fromisoformat(sa)).total_seconds()) if sa else 0
                    _set_item("daily", elapsed_sec=elapsed)
                    if s in ("done", "error"):
                        break
                with _daily_update_lock:
                    final = _daily_update_state.get("status")
                    err = _daily_update_state.get("error")
                _set_item("daily", status=final, error=err)
                if final == "error":
                    phase1_errors.append(("daily", err or "unknown"))

            def _run_news():
                news_check = next((c for c in preflight_check() if c["key"] == "news"), None)
                if news_check and news_check.get("status") == "FRESH":
                    _set_item("news", status="skipped", reason="today_digest_fresh")
                    return
                with _protocol_queue_lock:
                    history_baseline = len(_protocol_history)
                try:
                    state, err = enqueue_protocol("news", source="premarket_chain")
                    if err and err != "duplicate":
                        raise RuntimeError(f"news enqueue failed: {err}")
                except Exception as e:
                    _set_item("news", status="error", error=str(e))
                    phase1_errors.append(("news", str(e)))
                    return
                _set_item("news", status="queued")
                done_entry = _wait_protocol_completion(
                    "news", history_baseline, timeout_sec=1500,
                    on_progress=lambda running, sec: _set_item(
                        "news", status="running" if running else "queued", elapsed_sec=sec),
                )
                _set_item("news",
                          status=done_entry.get("status") or "done",
                          error=done_entry.get("error"))
                if done_entry.get("status") == "error":
                    phase1_errors.append(("news", done_entry.get("error") or "unknown"))

            t_daily = threading.Thread(target=_run_daily, daemon=True, name="premarket_daily")
            t_news  = threading.Thread(target=_run_news,  daemon=True, name="premarket_news")
            t_daily.start()
            t_news.start()
            t_daily.join()
            t_news.join()
            if phase1_errors:
                # Both items have already had their state set to "error"; stop the chain.
                first = phase1_errors[0]
                raise RuntimeError(f"phase 1 failed ({first[0]}): {first[1]}")

            # ── Phase 2: sector ─────────────────────────────────
            with _premarket_chain_lock:
                _premarket_chain_state["phase"] = "phase_2"
            sector_check = next((c for c in preflight_check() if c["key"] == "sector"), None)
            if sector_check and sector_check.get("status") == "FRESH":
                _set_item("sector", status="skipped", reason="today_intel_fresh")
            else:
                with _protocol_queue_lock:
                    history_baseline = len(_protocol_history)
                state, err = enqueue_protocol("sector", source="premarket_chain")
                if err and err != "duplicate":
                    raise RuntimeError(f"sector enqueue failed: {err}")
                _set_item("sector", status="queued")
                # V2.20.1 — sector V1.4 PARALLEL_SUBAGENT typically takes 15-21 min
                # (p95 ~21 min). Old 1200s/20min cap was too tight, hit timeout on 5/10
                # despite sector still running. Bumped to 1800s/30min for headroom.
                done_entry = _wait_protocol_completion(
                    "sector", history_baseline, timeout_sec=1800,
                    on_progress=lambda running, sec: _set_item(
                        "sector", status="running" if running else "queued", elapsed_sec=sec),
                )
                _set_item("sector",
                          status=done_entry.get("status") or "done",
                          error=done_entry.get("error"))
                if done_entry.get("status") == "error":
                    raise RuntimeError(f"sector failed: {done_entry.get('error')}")

            # ── Done ────────────────────────────────────────────
            with _premarket_chain_lock:
                _premarket_chain_state["phase"]      = "done"
                _premarket_chain_state["status"]     = "done"
                _premarket_chain_state["ended_at"]   = _now_iso()
                _premarket_chain_state["elapsed_sec"] = int((datetime.now() - start).total_seconds())
        except Exception as e:
            with _premarket_chain_lock:
                _premarket_chain_state["status"]     = "error"
                _premarket_chain_state["error"]      = str(e)
                _premarket_chain_state["ended_at"]   = _now_iso()
                _premarket_chain_state["elapsed_sec"] = int((datetime.now() - start).total_seconds())

    threading.Thread(target=_run, daemon=True).start()
    return "started", None


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

        # Auto-regenerate stats.json so bridge.py picks up fresh data
        if params.get("journal"):
            with _momentum_lock:
                _momentum_state["phase"] = "computing journal stats…"
            try:
                subprocess.run(
                    [sys.executable,
                     os.path.join(ROOT, "skills", "momentum-monitor", "scripts", "journal.py"),
                     "stats"],
                    cwd=ROOT, capture_output=True, text=True, timeout=120,
                )
            except Exception as e:
                print(f"[momentum-screen] journal stats failed: {e}", flush=True)

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


_journal_update_lock = threading.Lock()
_journal_update_state = {"status": "idle", "phase": None, "ended_at": None, "error": None}

JOURNAL_PY = os.path.join(ROOT, "skills", "momentum-monitor", "scripts", "journal.py")


def run_journal_update():
    """Fill forward returns + regenerate stats.json + refresh bridge, in background."""
    with _journal_update_lock:
        if _journal_update_state["status"] == "running":
            return _journal_update_state.copy(), "running"
        _journal_update_state.update({"status": "running", "phase": "updating returns…", "error": None})

    def _worker():
        try:
            with _journal_update_lock:
                _journal_update_state["phase"] = "filling forward returns…"
            subprocess.run([sys.executable, JOURNAL_PY, "update"],
                           cwd=ROOT, capture_output=True, text=True, timeout=300)
            with _journal_update_lock:
                _journal_update_state["phase"] = "computing stats…"
            subprocess.run([sys.executable, JOURNAL_PY, "stats"],
                           cwd=ROOT, capture_output=True, text=True, timeout=120)
            with _journal_update_lock:
                _journal_update_state["phase"] = "refreshing data…"
            subprocess.run([sys.executable, os.path.join(ROOT, "bridge.py")],
                           cwd=ROOT, capture_output=True, text=True, timeout=BRIDGE_TIMEOUT_SEC)
            with _journal_update_lock:
                _journal_update_state.update({"status": "done", "phase": "complete",
                                               "ended_at": datetime.now().timestamp()})
        except Exception as e:
            with _journal_update_lock:
                _journal_update_state.update({"status": "error", "error": str(e),
                                               "ended_at": datetime.now().timestamp()})

    threading.Thread(target=_worker, daemon=True).start()
    return _journal_update_state.copy(), None


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


# ── Heatmap helpers (FMP batch quotes + per-ticker news) ─────────────
# Polling thread keeps Dashboard/heatmap.json warm during US market hours.
# Universe = S&P 500 ∪ NDX 100 deduped (~550 tickers), profile fetched once a day.

try:
    from zoneinfo import ZoneInfo as _ZoneInfo
    _HEATMAP_ET = _ZoneInfo("America/New_York")
except ImportError:
    from datetime import timezone as _tz
    _HEATMAP_ET = _tz(timedelta(hours=-4))


def _is_us_market_hours():
    """True if current ET time is Mon-Fri 09:30-16:00."""
    now_et = datetime.now(_HEATMAP_ET)
    if now_et.weekday() >= 5:
        return False
    open_t  = now_et.replace(hour=9,  minute=30, second=0, microsecond=0)
    close_t = now_et.replace(hour=16, minute=0,  second=0, microsecond=0)
    return open_t <= now_et <= close_t


def _heatmap_atomic_write(payload):
    """Write Dashboard/heatmap.json atomically (tmp + rename)."""
    tmp = HEATMAP_OUTPUT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, HEATMAP_OUTPUT_FILE)


def _heatmap_load_from_cache():
    """Warm up state from Dashboard/heatmap.json on startup so /api/heatmap/data
    returns prior-session data immediately instead of an empty dict (especially
    important after-hours / weekends when we wait for next market open)."""
    if not os.path.exists(HEATMAP_OUTPUT_FILE):
        return False
    try:
        with open(HEATMAP_OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        tickers = {(t.get("ticker") or "").upper(): t for t in data.get("tickers", []) if t.get("ticker")}
        if not tickers:
            return False
        with _heatmap_lock:
            _heatmap_state["tickers"] = tickers
            _heatmap_state["last_update"]       = data.get("last_update")
            _heatmap_state["universe_built_at"] = data.get("universe_built_at")
        sys.stderr.write(f"[heatmap] cache loaded: {len(tickers)} tickers (last_update={data.get('last_update')})\n")
        return True
    except (OSError, ValueError) as e:
        sys.stderr.write(f"[heatmap] cache read error: {e}\n")
        return False


def _heatmap_has_quote_data(min_fraction=0.5):
    """True if at least `min_fraction` of universe has a non-zero market_cap.
    Used to decide whether startup needs a quote refresh."""
    with _heatmap_lock:
        rows = list(_heatmap_state["tickers"].values())
    if not rows:
        return False
    populated = sum(1 for r in rows if (r.get("market_cap") or 0) > 0 and r.get("price") is not None)
    return populated >= len(rows) * min_fraction


def _fmp_get_json(url, timeout=20):
    """Stdlib HTTP GET → parse JSON. Returns None on failure.

    On HTTP 429 (rate-limited) it trips the heatmap circuit breaker
    (`_heatmap_ratelimit_until`) and logs only once per cooldown window — so a
    fan-out of ~500 calls all 429-ing produces one line, not 500."""
    global _heatmap_ratelimit_until
    from urllib.request import Request, urlopen
    from urllib.error  import URLError, HTTPError
    try:
        req = Request(url, headers={"User-Agent": "ai-invest-dashboard/heatmap"})
        with urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        if getattr(e, "code", None) == 429:
            now = time.time()
            with _heatmap_lock:
                first = now >= _heatmap_ratelimit_until
                _heatmap_ratelimit_until = now + HEATMAP_RATELIMIT_COOLDOWN
            if first:
                sys.stderr.write(f"[heatmap] FMP rate-limited (429) — pausing quote "
                                 f"refresh {HEATMAP_RATELIMIT_COOLDOWN}s\n")
        else:
            sys.stderr.write(f"[heatmap] HTTP error: HTTPError {getattr(e, 'code', '?')}\n")
        return None
    except (URLError, TimeoutError, json.JSONDecodeError) as e:
        sys.stderr.write(f"[heatmap] HTTP error: {type(e).__name__}: {str(e)[:100]}\n")
        return None


def _heatmap_build_universe():
    """Load S&P 500 ∪ NDX 100 universe from static Dashboard/heatmap_universe.json.
    Migrated from FMP `sp500-constituent` + `nasdaq-constituent` (402 on the
    current plan) — refresh the static file manually each quarter."""
    if not os.path.exists(HEATMAP_UNIVERSE_FILE):
        sys.stderr.write(f"[heatmap] static universe file missing: {HEATMAP_UNIVERSE_FILE}\n")
        return False
    try:
        with open(HEATMAP_UNIVERSE_FILE, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"[heatmap] static universe read error: {e}\n")
        return False

    entries = doc.get("tickers") if isinstance(doc, dict) else doc
    if not isinstance(entries, list):
        sys.stderr.write("[heatmap] static universe: unexpected schema\n")
        return False

    profiles = {}
    for entry in entries:
        sym = (entry.get("ticker") or entry.get("symbol") or "").strip().upper()
        if not sym or not _HEATMAP_TICKER_RE.match(sym):
            continue
        if sym in profiles:
            continue
        profiles[sym] = {
            "ticker":      sym,
            "name":        entry.get("name")     or sym,
            "sector":      entry.get("sector")   or "Other",
            "industry":    entry.get("industry") or entry.get("subSector") or entry.get("sector") or "Other",
            "market_cap":  0.0,
            "price":       None,
            "change_pct":  None,
            "day_low":     None,
            "day_high":    None,
            "volume":      None,
            "prev_close":  None,
        }

    if not profiles:
        sys.stderr.write("[heatmap] static universe parsed 0 rows\n")
        return False

    with _heatmap_lock:
        # Preserve existing quote fields if ticker is still in universe
        existing = _heatmap_state["tickers"]
        for sym, prof in profiles.items():
            if sym in existing:
                for k in ("price", "change_pct", "day_low", "day_high", "volume", "prev_close", "market_cap"):
                    if existing[sym].get(k) not in (None, 0, 0.0):
                        prof[k] = existing[sym][k]
        _heatmap_state["tickers"] = profiles
        _heatmap_state["universe_built_at"] = _now_iso()
        _heatmap_state["error"] = None

    sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] [heatmap] universe built: {len(profiles)} tickers\n")
    return True


def _heatmap_refresh_quotes():
    """Fan-out single-ticker `stable/quote` calls via thread pool.
    Migrated from `batch-quote` (402 on the current plan). `quote` returns
    marketCap, so we still patch market_cap inline."""
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return False

    # 429 circuit breaker — skip the whole ~500-call fan-out while cooling down.
    if time.time() < _heatmap_ratelimit_until:
        sys.stderr.write("[heatmap] skip quote refresh — FMP rate-limit cooldown\n")
        return False

    with _heatmap_lock:
        symbols = list(_heatmap_state["tickers"].keys())
    if not symbols:
        return False

    base = "https://financialmodelingprep.com/stable"

    def _fetch_one(sym):
        # If a 429 trips the breaker mid-fan-out, stop hitting the API for the
        # remaining (still-queued) symbols instead of firing them all.
        if time.time() < _heatmap_ratelimit_until:
            return sym, None
        rows = _fmp_get_json(f"{base}/quote?symbol={sym}&apikey={api_key}", timeout=10) or []
        return sym, (rows[0] if isinstance(rows, list) and rows else None)

    from concurrent.futures import ThreadPoolExecutor, as_completed
    quotes = {}
    with ThreadPoolExecutor(max_workers=HEATMAP_QUOTE_WORKERS) as ex:
        futs = [ex.submit(_fetch_one, s) for s in symbols]
        for fut in as_completed(futs):
            try:
                sym, q = fut.result()
            except Exception:
                continue
            if q:
                quotes[sym] = q

    updated = 0
    with _heatmap_lock:
        for sym, q in quotes.items():
            row = _heatmap_state["tickers"].get(sym)
            if not row:
                continue
            row["price"]      = q.get("price")
            row["change_pct"] = q.get("changePercentage")
            row["day_low"]    = q.get("dayLow")
            row["day_high"]   = q.get("dayHigh")
            row["volume"]     = q.get("volume")
            row["prev_close"] = q.get("previousClose")
            mcap = q.get("marketCap")
            if mcap:
                row["market_cap"] = float(mcap)
            # Attach cached valuation bundle (filled by _heatmap_refresh_pe_universe).
            # Forward PE is computed live (price / fwd_eps) so price drift within
            # 24h cache window stays accurate.
            with _heatmap_pe_lock:
                pe_entry = _heatmap_pe_cache.get(sym)
            if pe_entry and isinstance(pe_entry[1], dict):
                val = pe_entry[1]
                row["pe"]        = val.get("pe_ttm")
                row["ev_ebitda"] = val.get("ev_ebitda")
                fwd_eps = val.get("fwd_eps")
                p = q.get("price")
                if fwd_eps and fwd_eps != 0 and p:
                    try:
                        row["forward_pe"] = round(float(p) / float(fwd_eps), 2)
                    except (TypeError, ValueError, ZeroDivisionError):
                        row["forward_pe"] = None
                else:
                    row["forward_pe"] = None
            updated += 1

    with _heatmap_lock:
        _heatmap_state["last_update"] = _now_iso()
        snapshot = {
            "last_update":       _heatmap_state["last_update"],
            "universe_built_at": _heatmap_state["universe_built_at"],
            "market_open":       _is_us_market_hours(),
            "tickers":           list(_heatmap_state["tickers"].values()),
        }

    try:
        _heatmap_atomic_write(snapshot)
    except OSError as e:
        sys.stderr.write(f"[heatmap] write error: {e}\n")
        return False

    sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] [heatmap] quotes refreshed: {updated}/{len(symbols)}\n")
    return True


def _fetch_heatmap_news(ticker, limit=2):
    """Fetch up to `limit` recent news items for a single ticker via FMP stable.
    Returns list of {title, url, published, source}."""
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return []
    url = (f"https://financialmodelingprep.com/stable/news/stock"
           f"?symbols={ticker}&limit={limit}&apikey={api_key}")
    data = _fmp_get_json(url, timeout=10) or []
    items = []
    for n in data[:limit]:
        items.append({
            "title":     n.get("title") or "",
            "url":       n.get("url")   or "",
            "published": n.get("publishedDate") or "",
            "source":    n.get("site") or n.get("publisher") or "",
        })
    return items


def _fetch_theme_extra_quotes(symbols):
    """Batch-fetch quotes for tickers outside the heatmap universe (small/mid
    caps in TD representative_stocks). Returns {sym: quote-dict} in the same
    shape as `_heatmap_state["tickers"]` rows. Per-ticker TTL cache keeps FMP
    usage low (1 batch call per render at most). FMP miss = sym omitted."""
    if not symbols:
        return {}
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return {}

    now = time.time()
    out = {}
    to_fetch = []
    for sym in symbols:
        cached = _theme_extra_quote_cache.get(sym)
        if cached and (now - cached[0]) < THEME_EXTRA_QUOTE_TTL_SEC:
            out[sym] = cached[1]
        else:
            to_fetch.append(sym)
    if not to_fetch:
        return out

    base = "https://financialmodelingprep.com/stable"
    BATCH = 200
    fetched_syms = []
    for i in range(0, len(to_fetch), BATCH):
        chunk = to_fetch[i:i + BATCH]
        url = f"{base}/batch-quote?symbols={','.join(chunk)}&apikey={api_key}"
        rows = _fmp_get_json(url, timeout=15) or []
        for q in rows:
            sym = (q.get("symbol") or "").strip().upper()
            if not sym:
                continue
            with _heatmap_pe_lock:
                pe_entry = _heatmap_pe_cache.get(sym)
            val = pe_entry[1] if pe_entry and isinstance(pe_entry[1], dict) else {}
            price = q.get("price")
            fwd_eps = val.get("fwd_eps")
            forward_pe = None
            if fwd_eps and fwd_eps != 0 and price:
                try:
                    forward_pe = round(float(price) / float(fwd_eps), 2)
                except (TypeError, ValueError, ZeroDivisionError):
                    forward_pe = None
            row = {
                "ticker":     sym,
                "name":       q.get("name") or sym,
                "sector":     "",
                "industry":   "",
                "price":      price,
                "change_pct": q.get("changePercentage"),
                "volume":     q.get("volume"),
                "market_cap": float(q.get("marketCap")) if q.get("marketCap") else 0,
                "pe":         val.get("pe_ttm"),
                "ev_ebitda":  val.get("ev_ebitda"),
                "forward_pe": forward_pe,
            }
            _theme_extra_quote_cache[sym] = (now, row)
            out[sym] = row
            if not pe_entry:
                fetched_syms.append(sym)

    # Lazy PE fetch for newly-seen symbols (background — populates next render)
    if fetched_syms:
        def _bg():
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=5) as ex:
                futs = {ex.submit(_fetch_pe_ttm, s, api_key): s for s in fetched_syms}
                for fut in as_completed(futs):
                    s = futs[fut]
                    try:
                        pe = fut.result()
                    except Exception:
                        pe = None
                    with _heatmap_pe_lock:
                        _heatmap_pe_cache[s] = (time.time(), pe)
        threading.Thread(target=_bg, daemon=True).start()
    return out


def _build_theme_heatmap_payload():
    """Compose per-theme mini-heatmap data: pin to the same theme-detector cache
    that the latest recommendations.json was generated from (so radar-page card
    bodies and the heatmap show identical theme names + tickers). Falls back to
    the newest TD cache when recommendations meta is missing.

    Tickers not in `_heatmap_state.tickers` are skipped — quote data stays live;
    only the theme structure is pinned."""
    import glob
    cache_dir = os.path.join(ROOT, "skills", "theme-detector", "cache")
    files = sorted(glob.glob(os.path.join(cache_dir, "theme_detector_*.json")))
    if not files:
        return {"themes": [], "error": "no theme-detector cache found",
                "as_of": _now_iso(), "market_open": _is_us_market_hours()}

    # Pin to the TD cache the latest recommendations.json points at.
    pinned_path = None
    pinned_source = "latest"
    rec_dir = os.path.join(ROOT, "skills", "thematic-screener", "data", "recommendations")
    rec_files = sorted(glob.glob(os.path.join(rec_dir, "*.json")))
    if rec_files:
        try:
            with open(rec_files[-1], "r", encoding="utf-8") as rf:
                rec_meta = (json.load(rf) or {}).get("theme_detector_meta") or {}
            td_filename = rec_meta.get("file")
            if td_filename:
                candidate = os.path.join(cache_dir, td_filename)
                if os.path.isfile(candidate):
                    pinned_path = candidate
                    pinned_source = f"pinned_to_recommendations:{os.path.basename(rec_files[-1])}"
        except Exception:
            pass  # rec read failed — fall through to latest TD

    chosen = pinned_path or files[-1]
    try:
        with open(chosen, "r", encoding="utf-8") as f:
            td_data = json.load(f)
    except Exception as e:
        return {"themes": [], "error": f"theme-detector cache read failed: {e}",
                "as_of": _now_iso(), "market_open": _is_us_market_hours()}

    all_themes = (td_data.get("themes") or {}).get("all") or []
    with _heatmap_lock:
        ticker_lookup = dict(_heatmap_state["tickers"])  # snapshot

    # Pass 1 — collect tickers in TD themes that aren't in the S&P-500-based
    # heatmap universe. Theme-detector covers small/mid-cap (e.g. CDE/AU/GFI/HL
    # in Gold & Precious Metals), so theme cards otherwise look near-empty.
    missing = set()
    for th in all_themes:
        for sym in (th.get("representative_stocks") or []):
            sym = (sym or "").strip().upper()
            if sym and sym not in ticker_lookup:
                missing.add(sym)

    # Fetch missing quotes via FMP batch-quote (single call, TTL-cached). Failure
    # is non-fatal — those tickers stay skipped.
    extra_lookup = _fetch_theme_extra_quotes(missing) if missing else {}

    def _resolve(sym):
        return ticker_lookup.get(sym) or extra_lookup.get(sym)

    themes_out = []
    for th in all_themes:
        rep = th.get("representative_stocks") or []
        details = th.get("stock_details") or []
        tickers = []
        for sym in rep:
            sym = (sym or "").strip().upper()
            if not sym:
                continue
            q = _resolve(sym)
            if not q:
                continue   # quote unavailable (FMP miss / not in any cache)
            tickers.append({
                "ticker":      q.get("ticker", sym),
                "name":        q.get("name") or sym,
                "sector":      q.get("sector") or "",
                "industry":    q.get("industry") or "",
                "price":       q.get("price"),
                "change_pct":  q.get("change_pct"),
                "volume":      q.get("volume"),
                "market_cap":  q.get("market_cap") or 0,
                "pe":          q.get("pe"),
                "forward_pe":  q.get("forward_pe"),
                "ev_ebitda":   q.get("ev_ebitda"),
            })
        if not tickers:
            continue   # theme has no covered ticker

        themes_out.append({
            "name":            th.get("name", ""),
            "direction":       th.get("direction", ""),
            "heat":            th.get("heat"),
            "heat_label":      th.get("heat_label"),
            "lifecycle_stage": th.get("stage") or th.get("lifecycle_stage"),
            "confidence":      th.get("confidence"),
            "industries":      th.get("industries") or [],
            "proxy_etfs":      th.get("proxy_etfs") or [],
            "representative_count": len(rep),
            "covered_count":   len(tickers),
            "tickers":         tickers,
        })

    return {
        "as_of":               _now_iso(),
        "market_open":         _is_us_market_hours(),
        "theme_detector_at":   td_data.get("generated_at"),
        "theme_detector_file": os.path.basename(chosen),
        "pin_source":          pinned_source,
        "heatmap_last_update": _heatmap_state.get("last_update"),
        "themes":              themes_out,
    }


def _fetch_heatmap_intraday(ticker):
    """Fetch today's 5-minute OHLCV bars via FMP /stable/historical-chart/5min.

    Returns {symbol, as_of, market_open, bars: [{time, o, h, l, c, v}, ...]}.
    On weekend / pre-market when today is empty, falls back to last 7 days.
    """
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return {"symbol": ticker, "error": "FMP_API_KEY not set", "bars": [],
                "as_of": _now_iso(), "market_open": False}

    today = date.today().isoformat()
    url = (f"https://financialmodelingprep.com/stable/historical-chart/5min"
           f"?symbol={ticker}&from={today}&to={today}&apikey={api_key}")
    rows = _fmp_get_json(url, timeout=10)

    if not isinstance(rows, list) or not rows:
        # Empty response (weekend / pre-market / holiday) — pull last 7 days
        seven_ago = (date.today() - timedelta(days=7)).isoformat()
        url = (f"https://financialmodelingprep.com/stable/historical-chart/5min"
               f"?symbol={ticker}&from={seven_ago}&to={today}&apikey={api_key}")
        rows = _fmp_get_json(url, timeout=10) or []

    bars = []
    for r in (rows or []):
        try:
            bars.append({
                "time": r.get("date"),
                "o":    float(r.get("open", 0)),
                "h":    float(r.get("high", 0)),
                "l":    float(r.get("low", 0)),
                "c":    float(r.get("close", 0)),
                "v":    int(r.get("volume", 0)),
            })
        except (TypeError, ValueError):
            continue
    # FMP returns newest-first → reverse to oldest-first for chart rendering
    bars.reverse()

    return {
        "symbol":      ticker,
        "as_of":       _now_iso(),
        "market_open": _is_us_market_hours(),
        "bars":        bars,
    }


def _fetch_pe_ttm(ticker, api_key):
    """Single-ticker valuation bundle: PE TTM + EV/EBITDA TTM + forward EPS
    estimate (next fiscal year). Three FMP calls per ticker, cache 24h.

    Returns {"pe_ttm", "ev_ebitda", "fwd_eps"} (any field may be None on miss).
    Forward PE is computed live in quote refresh (price / fwd_eps), so price
    drift within the 24h cache window stays accurate."""
    base = "https://financialmodelingprep.com/stable"
    out = {"pe_ttm": None, "ev_ebitda": None, "fwd_eps": None}
    # honor the 429 breaker — skip the 3 calls if cooling down
    if time.time() < _heatmap_ratelimit_until:
        return out

    def _safe_round(v, n=2):
        try:
            return round(float(v), n) if v is not None else None
        except (TypeError, ValueError):
            return None

    # 1) PE TTM
    rows = _fmp_get_json(f"{base}/ratios-ttm?symbol={ticker}&apikey={api_key}", timeout=10) or []
    if isinstance(rows, list) and rows:
        out["pe_ttm"] = _safe_round(rows[0].get("priceToEarningsRatioTTM"), 2)

    # 2) EV/EBITDA TTM
    rows = _fmp_get_json(f"{base}/key-metrics-ttm?symbol={ticker}&apikey={api_key}", timeout=10) or []
    if isinstance(rows, list) and rows:
        out["ev_ebitda"] = _safe_round(rows[0].get("evToEBITDATTM"), 2)

    # 3) Forward EPS (closest future fiscal year, sorted asc)
    rows = _fmp_get_json(
        f"{base}/analyst-estimates?symbol={ticker}&period=annual&limit=4&apikey={api_key}",
        timeout=10,
    ) or []
    if isinstance(rows, list) and rows:
        today_iso = date.today().isoformat()
        future = sorted(
            [r for r in rows if (r.get("date") or "") > today_iso],
            key=lambda r: r.get("date") or "",
        )
        if future:
            out["fwd_eps"] = _safe_round(future[0].get("epsAvg"), 4)

    return out


def _heatmap_refresh_pe_universe(max_workers=10):
    """Daily refresh of PE TTM for entire heatmap universe. Uses thread pool to
    parallelise the 600 single-ticker calls (FMP has no batch ratios-ttm)."""
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return False
    if time.time() < _heatmap_ratelimit_until:
        sys.stderr.write("[heatmap-pe] skip — FMP rate-limit cooldown\n")
        return False
    with _heatmap_lock:
        symbols = list(_heatmap_state["tickers"].keys())
    if not symbols:
        return False
    now = time.time()
    todo = []
    with _heatmap_pe_lock:
        for sym in symbols:
            cached = _heatmap_pe_cache.get(sym)
            if not cached or (now - cached[0]) >= HEATMAP_PE_TTL_SEC:
                todo.append(sym)
    if not todo:
        return True

    from concurrent.futures import ThreadPoolExecutor, as_completed
    sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] [heatmap-pe] fetching {len(todo)} tickers...\n")
    fetched = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_fetch_pe_ttm, sym, api_key): sym for sym in todo}
        for fut in as_completed(futures):
            sym = futures[fut]
            try:
                pe = fut.result()
            except Exception:
                pe = None
            with _heatmap_pe_lock:
                _heatmap_pe_cache[sym] = (time.time(), pe)
            fetched += 1
    sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] [heatmap-pe] done: {fetched}/{len(todo)}\n")

    # Patch _heatmap_state ticker rows with new valuation bundle. forward_pe
    # computed live from row's current price + cached fwd_eps.
    with _heatmap_pe_lock:
        val_snapshot = {s: v[1] for s, v in _heatmap_pe_cache.items()
                        if isinstance(v[1], dict)}
    with _heatmap_lock:
        for sym, row in _heatmap_state["tickers"].items():
            val = val_snapshot.get(sym)
            if not val:
                continue
            row["pe"]        = val.get("pe_ttm")
            row["ev_ebitda"] = val.get("ev_ebitda")
            fwd_eps = val.get("fwd_eps")
            p = row.get("price")
            if fwd_eps and fwd_eps != 0 and p:
                try:
                    row["forward_pe"] = round(float(p) / float(fwd_eps), 2)
                except (TypeError, ValueError, ZeroDivisionError):
                    row["forward_pe"] = None
            else:
                row["forward_pe"] = None
    return True


def _fetch_heatmap_quote(ticker):
    """Live last-price + change_pct for a single ticker via FMP /stable/quote.
    Used by radar K-line tail (15s tick between 5-min bar boundaries). Single
    ticker per call, ~500 bytes payload."""
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return {"symbol": ticker, "error": "FMP_API_KEY not set",
                "as_of": _now_iso(), "market_open": False}
    url = (f"https://financialmodelingprep.com/stable/quote"
           f"?symbol={ticker}&apikey={api_key}")
    rows = _fmp_get_json(url, timeout=8) or []
    row = rows[0] if isinstance(rows, list) and rows else {}
    return {
        "symbol":      ticker,
        "price":       row.get("price"),
        "change_pct":  row.get("changePercentage"),
        "volume":      row.get("volume"),
        "as_of":       _now_iso(),
        "market_open": _is_us_market_hours(),
    }


def heatmap_refresh_loop():
    """Background daemon: rebuild universe daily, refresh quotes every 3 min during market hours.
    On startup: warm up from cache file → ensure we have at least one quote snapshot
    (even after-hours, since FMP returns last close which is what the heatmap should
    show until the next session opens)."""
    if _shutdown.wait(5):
        return  # Server shutting down before we even start

    # 1) Warm up from cache so /api/heatmap/data is responsive instantly after restart
    cache_loaded = _heatmap_load_from_cache()

    # 2) Universe build (cheap — 2 calls; preserves cached quote fields per-ticker)
    try:
        _heatmap_build_universe()
    except Exception as e:
        sys.stderr.write(f"[heatmap] startup universe error: {e}\n")
        with _heatmap_lock:
            _heatmap_state["error"] = str(e)

    # 3) Quote refresh on startup if we don't already have usable data.
    #    Honors user spec: "if after-hours and no prior-day data, fetch a snapshot".
    #    During market hours we always refresh on startup so the first user sees current data.
    need_initial_quotes = _is_us_market_hours() or not _heatmap_has_quote_data()
    if need_initial_quotes:
        try:
            _heatmap_refresh_quotes()
        except Exception as e:
            sys.stderr.write(f"[heatmap] startup quote error: {e}\n")
            with _heatmap_lock:
                _heatmap_state["error"] = str(e)
    else:
        sys.stderr.write(f"[heatmap] startup: using cache (market closed, {len(_heatmap_state['tickers'])} tickers ready)\n")

    # 4) PE TTM warm-up — runs in its own thread so server stays responsive
    #    (~600 sequential calls capped to 10-thread pool ≈ 60s). 24h TTL means
    #    one full refresh per day; subsequent loop iterations no-op until expiry.
    threading.Thread(target=_heatmap_refresh_pe_universe, daemon=True).start()

    while not _shutdown.is_set():
        if _shutdown.wait(HEATMAP_REFRESH_SEC):
            break
        try:
            # Universe rebuild once per HEATMAP_UNIVERSE_TTL_SEC (~18h)
            with _heatmap_lock:
                last_built = _heatmap_state["universe_built_at"]
            need_rebuild = True
            if last_built:
                try:
                    last_dt = datetime.fromisoformat(last_built)
                    age_sec = (datetime.now() - last_dt).total_seconds()
                    need_rebuild = age_sec >= HEATMAP_UNIVERSE_TTL_SEC
                except ValueError:
                    need_rebuild = True
            if need_rebuild:
                _heatmap_build_universe()

            # Quote refresh only during market hours
            if _is_us_market_hours():
                _heatmap_refresh_quotes()
        except Exception as e:
            sys.stderr.write(f"[heatmap] loop error: {e}\n")
            with _heatmap_lock:
                _heatmap_state["error"] = str(e)


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


# ── Break News (RSS poller + Claude/Gemini debate) ───────────────────
# Periodic RSS pull every BREAK_NEWS_INTERVAL_SEC (default 600s = 10 min).
# Surviving items get a Claude<->Gemini debate written into per-item JSON at
# news/break_news_logs/<news_id>.json. Has its own dedicated lock pool so it
# never blocks the existing Claude protocol queue.
BREAK_NEWS_INTERVAL_SEC = int(os.getenv("BREAK_NEWS_INTERVAL_SEC", "600"))
AGY_BIN = os.environ.get("AGY_BIN") or "agy"
_break_news_state = {
    "last_poll": None,
    "last_debate_scan": None,
    "in_flight": [],
    "last_error": None,
}
_break_news_lock = threading.Lock()
_break_news_dispatch_lock = threading.Lock()   # serializes calls into debater scan

try:
    sys.path.insert(0, ROOT)
    from scripts.break_news import store as _bn_store
    from scripts.break_news import poller as _bn_poller
    from scripts.break_news import debater as _bn_debater
    from scripts.break_news import trend_rollup as _bn_trend
    BREAK_NEWS_AVAILABLE = True
except Exception as _bn_e:
    BREAK_NEWS_AVAILABLE = False
    sys.stderr.write(f"[break_news] module load failed: {_bn_e}\n")

# 3-day trend leaderboard — computed on-demand, behind a short TTL cache.
_bn_trend_cache = {"data": None, "ts": 0.0}
BN_TREND_TTL_SEC = 60

# Supply-chain explorer — LLM-drafted value chains + live grounding.
try:
    from scripts.nexus import supply_chain as _sc
    SUPPLY_CHAIN_AVAILABLE = True
except Exception as _sc_e:
    SUPPLY_CHAIN_AVAILABLE = False
    sys.stderr.write(f"[supply_chain] module load failed: {_sc_e}\n")
_sc_cache = {}            # slug -> {"data": enriched_chain, "ts": float}
SC_TTL_SEC = 60
_sc_slug_re = re.compile(r"^[a-z0-9_]{1,48}$")


def break_news_poll_loop():
    """Poll RSS feeds every BREAK_NEWS_INTERVAL_SEC. Stops on _shutdown.
    First poll fires immediately at boot so `_state.poller.next_run` is seeded
    fresh — otherwise the UI shows a stale `next_run` left over from the
    previous process for up to BREAK_NEWS_INTERVAL_SEC."""
    if not BREAK_NEWS_AVAILABLE:
        return
    def _one(reason):
        try:
            res = _bn_poller.run_once()
            with _break_news_lock:
                _break_news_state["last_poll"] = datetime.now().isoformat(timespec="seconds")
                _break_news_state["last_error"] = (res or {}).get("last_error")
        except Exception as e:
            with _break_news_lock:
                _break_news_state["last_error"] = str(e)[:300]
            sys.stderr.write(f"[break_news] poll error ({reason}): {e}\n")
    # Boot poll — short delay so http.server has finished binding first.
    if _shutdown.wait(10):
        return
    _one("startup")
    while not _shutdown.wait(BREAK_NEWS_INTERVAL_SEC):
        _one("periodic")


def break_news_debate_loop():
    """Continuously scan for pending_debate items and run debates. One scan
    per BREAK_NEWS_INTERVAL_SEC (paced so cost doesn't run away)."""
    if not BREAK_NEWS_AVAILABLE:
        return
    # Run one scan ~30s after server boot, then every BREAK_NEWS_INTERVAL_SEC.
    if _shutdown.wait(30):
        return
    while True:
        try:
            with _break_news_dispatch_lock:
                res = _bn_debater.scan_and_debate(verbose=False)
            with _break_news_lock:
                _break_news_state["last_debate_scan"] = datetime.now().isoformat(timespec="seconds")
                _break_news_state["last_error"] = None
        except Exception as e:
            with _break_news_lock:
                _break_news_state["last_error"] = str(e)[:300]
            sys.stderr.write(f"[break_news] debate scan error: {e}\n")
        if _shutdown.wait(BREAK_NEWS_INTERVAL_SEC):
            return


def _bn_kick_debate_scan():
    """Run one debate scan in the background. Used by the manual raw-debate
    trigger so a freshly-promoted item starts debating without waiting for the
    periodic debate loop."""
    if not BREAK_NEWS_AVAILABLE:
        return
    try:
        with _break_news_dispatch_lock:
            _bn_debater.scan_and_debate(verbose=False)
        with _break_news_lock:
            _break_news_state["last_debate_scan"] = datetime.now().isoformat(timespec="seconds")
    except Exception as e:
        with _break_news_lock:
            _break_news_state["last_error"] = str(e)[:300]
        sys.stderr.write(f"[break_news] manual debate kick error: {e}\n")


_BREAK_NEWS_ID_RE = re.compile(r"^bn_\d{8}_[0-9a-f]{6,16}$")
_BREAK_NEWS_KEY_RE = re.compile(r"^[0-9a-f]{40}$")   # raw-stream entry key = sha1 hex


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {fmt % args}\n")

    def _json(self, code, body):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)
        except BrokenPipeError:
            return

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
        if path == "/api/llm-config":
            # Full governance config + live per-model usage/status.
            if MODEL_ROUTER_AVAILABLE:
                try:
                    cfg = _mrouter.load_llm_config()
                    return self._json(200, {**cfg, "status": _mrouter.model_status()})
                except Exception as e:
                    sys.stderr.write(f"[llm-config] status error: {e}\n")
            cfg_path = os.path.join(ROOT, "config", "llm_config.json")
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except (OSError, json.JSONDecodeError):
                cfg = {"primary": "claude", "secondary": "gemini"}
            return self._json(200, cfg)
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

        if path == "/api/journal-update/status":
            with _journal_update_lock:
                return self._json(200, _journal_update_state.copy())

        if path == "/api/heatmap/data":
            with _heatmap_lock:
                payload = {
                    "last_update":       _heatmap_state["last_update"],
                    "universe_built_at": _heatmap_state["universe_built_at"],
                    "tickers":           list(_heatmap_state["tickers"].values()),
                    "market_open":       _is_us_market_hours(),
                    "error":             _heatmap_state["error"],
                }
            return self._json(200, payload)

        # ── Project Nexus V3.0 — Knowledge Graph ────────────────────────
        if path == "/api/graph/data":
            graph_path = os.path.join(DASHBOARD_DIR, "nexus_graph.json")
            if not os.path.exists(graph_path):
                return self._json(404, {"error": "nexus_graph.json not built yet",
                                        "hint": "run scripts/nexus/build_graph.py"})
            try:
                with open(graph_path, "r", encoding="utf-8") as f:
                    return self._json(200, json.load(f))
            except (OSError, json.JSONDecodeError) as e:
                return self._json(500, {"error": str(e)})

        if path.startswith("/api/graph/centrality/"):
            ticker = path.rsplit("/", 1)[-1].strip().upper()
            if not re.match(r"^[A-Z][A-Z0-9.\-]{0,8}$", ticker):
                return self._json(400, {"error": "invalid ticker"})
            graph_path = os.path.join(DASHBOARD_DIR, "nexus_graph.json")
            if not os.path.exists(graph_path):
                return self._json(404, {"error": "nexus_graph.json not built yet"})
            try:
                with open(graph_path, "r", encoding="utf-8") as f:
                    graph = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                return self._json(500, {"error": str(e)})
            tk_id = f"ticker:{ticker}"
            node = next((n for n in graph.get("nodes", []) if n.get("id") == tk_id), None)
            if not node:
                return self._json(404, {"error": f"{ticker} not in graph"})
            connected_themes = []
            connected_catalysts = []
            connected_narratives = []
            connected_peers = []
            for e in graph.get("edges", []):
                other = None
                if e.get("source") == tk_id:
                    other = e.get("target")
                elif e.get("target") == tk_id:
                    other = e.get("source")
                if not other:
                    continue
                other_node = next((n for n in graph.get("nodes", []) if n.get("id") == other), None)
                if not other_node:
                    continue
                rec = {"id": other, "label": other_node.get("label"),
                       "weight": e.get("weight"), "type": e.get("type")}
                ot = other_node.get("type")
                if ot == "theme":
                    connected_themes.append(rec)
                elif ot == "catalyst":
                    connected_catalysts.append(rec)
                elif ot == "narrative":
                    connected_narratives.append(rec)
                elif ot == "ticker":
                    connected_peers.append(rec)
            connected_themes.sort(key=lambda r: r["weight"] or 0, reverse=True)
            connected_catalysts.sort(key=lambda r: r["weight"] or 0, reverse=True)
            connected_narratives.sort(key=lambda r: r["weight"] or 0, reverse=True)
            connected_peers.sort(key=lambda r: r["weight"] or 0, reverse=True)
            return self._json(200, {
                "ticker": ticker,
                "degree_centrality": node.get("weight"),
                "pagerank": node.get("pagerank"),
                "mentions": node.get("mentions"),
                "last_seen": node.get("last_seen"),
                "status": node.get("status"),
                "connected_themes": connected_themes[:20],
                "connected_catalysts": connected_catalysts[:20],
                "connected_narratives": connected_narratives[:20],
                "connected_peers": connected_peers[:20],
                "graph_generated_at": graph.get("generated_at"),
            })

        if path.startswith("/api/heatmap/news/"):
            ticker = path.rsplit("/", 1)[-1].strip().upper()
            if not _HEATMAP_TICKER_RE.match(ticker):
                return self._json(400, {"error": "invalid ticker"})
            cached = _heatmap_news_cache.get(ticker)
            if cached and (time.time() - cached["ts"]) < HEATMAP_NEWS_TTL_SEC:
                return self._json(200, {"items": cached["items"], "cached": True})
            items = _fetch_heatmap_news(ticker, limit=2)
            _heatmap_news_cache[ticker] = {"ts": time.time(), "items": items}
            return self._json(200, {"items": items, "cached": False})

        if path == "/api/theme-heatmap":
            now = time.time()
            cached = _theme_heatmap_cache
            if cached["data"] and (now - cached["ts"]) < THEME_HEATMAP_TTL_SEC:
                payload = dict(cached["data"])
                payload["cached"] = True
                return self._json(200, payload)
            data = _build_theme_heatmap_payload()
            # Only cache non-empty results (heatmap state may not be warm yet on startup)
            if data.get("themes"):
                _theme_heatmap_cache["data"] = data
                _theme_heatmap_cache["ts"]   = now
            payload = dict(data)
            payload["cached"] = False
            return self._json(200, payload)

        if path.startswith("/api/heatmap/intraday/"):
            ticker = path.rsplit("/", 1)[-1].strip().upper()
            if not _HEATMAP_TICKER_RE.match(ticker):
                return self._json(400, {"error": "invalid ticker"})
            # Cache TTL: 15s when market open, 5min when closed
            ttl = (HEATMAP_INTRADAY_TTL_SEC_OPEN if _is_us_market_hours()
                   else HEATMAP_INTRADAY_TTL_SEC_CLOSED)
            cached = _heatmap_intraday_cache.get(ticker)
            if cached and (time.time() - cached["ts"]) < ttl:
                payload = dict(cached["data"])
                payload["cached"] = True
                return self._json(200, payload)
            data = _fetch_heatmap_intraday(ticker)
            _heatmap_intraday_cache[ticker] = {"ts": time.time(), "data": data}
            payload = dict(data)
            payload["cached"] = False
            return self._json(200, payload)

        if path.startswith("/api/heatmap/quote/"):
            ticker = path.rsplit("/", 1)[-1].strip().upper()
            if not _HEATMAP_TICKER_RE.match(ticker):
                return self._json(400, {"error": "invalid ticker"})
            cached = _heatmap_quote_cache.get(ticker)
            if cached and (time.time() - cached[0]) < HEATMAP_QUOTE_TTL_SEC:
                payload = dict(cached[1])
                payload["cached"] = True
                return self._json(200, payload)
            data = _fetch_heatmap_quote(ticker)
            _heatmap_quote_cache[ticker] = (time.time(), data)
            payload = dict(data)
            payload["cached"] = False
            return self._json(200, payload)

        # ── Break News API ────────────────────────────────────────
        if path == "/api/break-news/feed":
            if not BREAK_NEWS_AVAILABLE:
                return self._json(503, {"error": "break_news module not loaded"})
            qs = urlparse(self.path).query
            params = {}
            for kv in qs.split("&"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    params[k] = v
            try:
                limit = max(1, min(int(params.get("limit", "50")), 200))
            except ValueError:
                limit = 50
            states_param = params.get("state", "")
            states = [s for s in states_param.split(",") if s] if states_param else None
            items = _bn_store.list_items_by_state(states)[:limit]
            return self._json(200, {
                "items": items, "count": len(items),
                "state_filter": states,
            })
        if path.startswith("/api/break-news/item/"):
            tail = path[len("/api/break-news/item/"):]
            if not _BREAK_NEWS_ID_RE.match(tail):
                return self._json(400, {"error": "invalid news_id"})
            if not BREAK_NEWS_AVAILABLE:
                return self._json(503, {"error": "break_news module not loaded"})
            d = _bn_store.load_item(tail)
            if d is None:
                return self._json(404, {"error": "not found"})
            return self._json(200, d)
        if path == "/api/break-news/raw-stream":
            if not BREAK_NEWS_AVAILABLE:
                return self._json(503, {"error": "break_news module not loaded"})
            qs = urlparse(self.path).query
            params = {}
            for kv in qs.split("&"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    params[k] = v
            try:
                limit = max(1, min(int(params.get("limit", "100")), 200))
            except ValueError:
                limit = 100
            items = _bn_store.load_raw_stream()[:limit]
            return self._json(200, {"items": items, "count": len(items)})
        if path == "/api/break-news/state":
            if not BREAK_NEWS_AVAILABLE:
                return self._json(503, {"error": "break_news module not loaded"})
            persisted = _bn_store.load_state()
            with _break_news_lock:
                live = dict(_break_news_state)
            return self._json(200, {
                "live": live, "persisted": persisted,
                "interval_sec": BREAK_NEWS_INTERVAL_SEC,
            })
        if path == "/api/break-news/trends":
            if not BREAK_NEWS_AVAILABLE:
                return self._json(503, {"error": "break_news module not loaded"})
            now_ts = time.time()
            cache = _bn_trend_cache
            if cache["data"] and (now_ts - cache["ts"]) < BN_TREND_TTL_SEC:
                return self._json(200, {**cache["data"], "cached": True})
            try:
                data = _bn_trend.compute_trends()
            except Exception as e:
                return self._json(500, {"error": str(e)})
            cache["data"] = data
            cache["ts"] = now_ts
            return self._json(200, {**data, "cached": False})

        # ── Supply-Chain Explorer API ──────────────────────────────
        if path == "/api/supply-chain/list":
            if not SUPPLY_CHAIN_AVAILABLE:
                return self._json(503, {"error": "supply_chain module not loaded"})
            return self._json(200, {"chains": _sc.list_chains()})
        if path == "/api/supply-chain/themes":
            if not SUPPLY_CHAIN_AVAILABLE:
                return self._json(503, {"error": "supply_chain module not loaded"})
            return self._json(200, {"themes": _sc.nexus_themes()})
        if path.startswith("/api/supply-chain/"):
            slug = path[len("/api/supply-chain/"):]
            if not _sc_slug_re.match(slug):
                return self._json(400, {"error": "invalid slug"})
            if not SUPPLY_CHAIN_AVAILABLE:
                return self._json(503, {"error": "supply_chain module not loaded"})
            now_ts = time.time()
            hit = _sc_cache.get(slug)
            if hit and (now_ts - hit["ts"]) < SC_TTL_SEC:
                return self._json(200, {**hit["data"], "cached": True})
            chain = _sc.load(slug)
            if chain is None:
                return self._json(404, {"error": "chain not found"})
            try:
                chain = _sc.enrich(chain)
            except Exception as e:
                return self._json(500, {"error": str(e)})
            _sc_cache[slug] = {"data": chain, "ts": now_ts}
            return self._json(200, {**chain, "cached": False})

        if path == "/api/analyze-queue" or path == "/api/protocol-queue":
            return self._json(200, get_queue_state())

        if path == "/api/momentum-watchlist":
            return self._json(200, {"tickers": load_watchlist()})

        if path.startswith("/api/preview-cache/"):
            # V2.16.0 — GET /api/preview-cache/<TICKER> → forecaster --pre-earnings cache JSON
            # Used by Dashboard preview modal. Returns the cached payload (status, ticker,
            # current_price, ttm_eps, pre_earnings.{next_earnings,seasonality_4q,watch_metrics},
            # scenarios) — same shape as forecast.py --json-only output.
            ticker = path.split("/api/preview-cache/", 1)[1].strip().upper()
            if not ticker or "/" in ticker:
                return self._json(400, {"error": "invalid ticker"})
            cache_path = os.path.join(ROOT, "skills", "earnings-valuation-forecaster", "cache", f"{ticker}.json")
            if not os.path.exists(cache_path):
                return self._json(404, {"error": "no preview cache for ticker", "ticker": ticker})
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                return self._json(500, {"error": f"failed to read cache: {e}"})
            if not data.get("pre_earnings"):
                return self._json(404, {"error": "cache exists but lacks pre_earnings block (run forecast.py --pre-earnings first)", "ticker": ticker})
            data["cache_age_sec"] = int(time.time() - os.path.getmtime(cache_path))
            return self._json(200, data)

        if path.startswith("/api/earnings-cache/"):
            # GET /api/earnings-cache/<TICKER>  → cache existence + summary
            ticker = path.split("/api/earnings-cache/", 1)[1].strip().upper()
            if not ticker or "/" in ticker:
                return self._json(400, {"error": "invalid ticker"})
            cache_dir = os.path.join(ROOT, "skills", "earnings-analyst", "cache")
            # Filter out *.infographic.json (V1.73 sibling) — only V1.0 data-layer
            matches = sorted(p for p in glob.glob(os.path.join(cache_dir, f"{ticker}_*.json"))
                             if not p.endswith(".infographic.json"))
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

        if path.startswith("/api/earnings-infographic/"):
            # GET /api/earnings-infographic/<TICKER>  → V1.73 infographic page payload
            # Returns merged cache (subset) + full infographic.json + report_path
            ticker = path.split("/api/earnings-infographic/", 1)[1].strip().upper()
            if not ticker or "/" in ticker:
                return self._json(400, {"error": "invalid ticker"})
            cache_dir = os.path.join(ROOT, "skills", "earnings-analyst", "cache")
            inf_matches = sorted(glob.glob(os.path.join(cache_dir, f"{ticker}_*.infographic.json")))
            if not inf_matches:
                return self._json(404, {"ticker": ticker, "error": "infographic not generated"})
            inf_latest = inf_matches[-1]
            # Pair with same-date V1.0 data-layer cache
            base_cache = inf_latest.replace(".infographic.json", ".json")
            cache_payload = {}
            if os.path.exists(base_cache):
                try:
                    with open(base_cache, "r", encoding="utf-8") as f:
                        cache_payload = json.load(f)
                except Exception as e:
                    print(f"[infographic] base cache read fail: {e}", file=sys.stderr)
            try:
                with open(inf_latest, "r", encoding="utf-8") as f:
                    inf_payload = json.load(f)
            except Exception as e:
                return self._json(500, {"ticker": ticker, "error": f"infographic read fail: {e}"})
            run_date = cache_payload.get("as_of_date") or inf_payload.get("as_of_date")
            report_path = None
            if run_date:
                cand = os.path.join(ROOT, "reports", f"{run_date}_{ticker}_earnings.md")
                if os.path.exists(cand):
                    report_path = os.path.relpath(cand, ROOT)
            # V2.7.15 — slim trend slices (last 8Q) for infographic chart row
            qpnl_slim = [
                {"date": q.get("date"), "period": q.get("period"),
                 "fiscalYear": q.get("fiscalYear"),
                 "revenue": q.get("revenue"), "netIncome": q.get("netIncome"),
                 "eps": q.get("eps"), "epsDiluted": q.get("epsDiluted")}
                for q in (cache_payload.get("quarterly_pnl") or [])[:8]
            ]
            cf_slim = [
                {"date": q.get("date"), "period": q.get("period"),
                 "operatingCashFlow": q.get("operatingCashFlow"),
                 "freeCashFlow": q.get("freeCashFlow")}
                for q in (cache_payload.get("cash_flow") or [])[:8]
            ]
            margins_slim = list((cache_payload.get("derived") or {}).get("margins_8q") or [])[:8]
            return self._json(200, {
                "ticker":      ticker,
                "infographic": inf_payload,
                "cache": {
                    "snapshot":           cache_payload.get("snapshot"),
                    "verdict":            cache_payload.get("verdict"),
                    "composite_score":    cache_payload.get("composite_score"),
                    "score_components":   cache_payload.get("score_components"),
                    "quality_flags":      cache_payload.get("quality_flags"),
                    "as_of_date":         run_date,
                    "last_earnings_date": cache_payload.get("last_earnings_date"),
                    "report_path":        report_path,
                    # Trend slices for chart row (V2.7.15)
                    "quarterly_pnl":      qpnl_slim,
                    "cash_flow":          cf_slim,
                    "margins_8q":         margins_slim,
                },
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

        # V2.13.11 — server-side pre-market chain status (replaces frontend polling)
        if path == "/api/run-premarket-chain/status":
            with _premarket_chain_lock:
                state = dict(_premarket_chain_state)
                state["items"] = {k: dict(v) for k, v in state["items"].items()}
            if state.get("status") == "running" and state.get("started_at"):
                try:
                    state["elapsed_sec"] = int(
                        (datetime.now() - datetime.fromisoformat(state["started_at"])).total_seconds()
                    )
                except Exception:
                    pass
            return self._json(200, state)

        # V2.7.17 — daily_update.sh shell-pipeline status
        if path == "/api/run-daily-update/status":
            with _daily_update_lock:
                state = dict(_daily_update_state)
            if state.get("status") == "running" and state.get("started_at"):
                try:
                    state["elapsed_sec"] = int(
                        (datetime.now() - datetime.fromisoformat(state["started_at"])).total_seconds()
                    )
                except Exception:
                    pass
            state["log_tail"] = _tail_log(state.get("log_path"), lines=40)
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
        if path == "/api/llm-config":
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception as e:
                return self._json(400, {"error": f"invalid JSON: {e}"})
            valid = {"claude", "gemini", "codex"}
            # Merge onto existing config so a partial POST (e.g. only the
            # dropdowns) keeps budgets / enabled / cooldown intact.
            cfg_path = os.path.join(ROOT, "config", "llm_config.json")
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if not isinstance(cfg, dict):
                    cfg = {}
            except (OSError, json.JSONDecodeError):
                cfg = {}
            for key in ("primary", "secondary", "tertiary"):
                if key not in body:
                    continue
                v = str(body.get(key, "")).lower().strip()
                if v not in valid:
                    return self._json(400, {"error": f"invalid {key}: {body.get(key)!r}"})
                cfg[key] = v
            if isinstance(body.get("enabled"), dict):
                cfg.setdefault("enabled", {})
                for m in valid:
                    if m in body["enabled"]:
                        cfg["enabled"][m] = bool(body["enabled"][m])
            if isinstance(body.get("budgets"), dict):
                cfg.setdefault("budgets", {})
                for m in valid:
                    mb = body["budgets"].get(m)
                    if isinstance(mb, dict) and "daily_max_calls" in mb:
                        try:
                            cfg["budgets"].setdefault(m, {})["daily_max_calls"] = \
                                max(0, int(mb["daily_max_calls"]))
                        except (TypeError, ValueError):
                            return self._json(400, {"error": f"invalid budget for {m}"})
            if "cooldown_hours" in body:
                try:
                    ch = float(body["cooldown_hours"])
                    if ch > 0:
                        cfg["cooldown_hours"] = ch
                except (TypeError, ValueError):
                    return self._json(400, {"error": "invalid cooldown_hours"})
            if isinstance(body.get("break_news"), dict):
                cfg.setdefault("break_news", {})
                for key in ("primary", "secondary"):
                    if key not in body["break_news"]:
                        continue
                    v = str(body["break_news"].get(key, "")).lower().strip()
                    if v not in valid:
                        return self._json(400, {"error": f"invalid break_news.{key}"})
                    cfg["break_news"][key] = v
            try:
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
            except OSError as e:
                return self._json(500, {"error": f"write failed: {e}"})
            return self._json(200, cfg)
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

        # V2.13.11 — server-side pre-market chain (daily → news → sector with skip)
        if path == "/api/run-premarket-chain":
            res, err = run_premarket_chain()
            if err == "duplicate_active":
                with _premarket_chain_lock:
                    snapshot = dict(_premarket_chain_state)
                return self._json(409, {
                    "error": "duplicate_active",
                    "started_at": snapshot.get("started_at"),
                    "phase": snapshot.get("phase"),
                })
            return self._json(202, {"status": "started"})

        # V2.7.17 — pre-market check Phase 1: spawn bash daily_update.sh
        # V2.13.9 — skip when all free caches already fresh (user already ran
        # daily_update.sh externally → don't re-burn 5min + FMP usage).
        if path == "/api/run-daily-update":
            with _daily_update_lock:
                if _daily_update_state.get("status") == "running":
                    return self._json(409, {
                        "error": "duplicate_active",
                        "job_id": _daily_update_state.get("job_id"),
                        "started_at": _daily_update_state.get("started_at"),
                    })
            # Idempotency guard: if every "free" preflight item is FRESH, skip.
            # Surfaces as `{skipped: true, reason}` so the chain UI can mark
            # Phase 1 ✓ and proceed to Phase 2 instead of re-running.
            try:
                checks = preflight_check()
                free = [c for c in checks if c.get("free")]
                free_stale = [c for c in free if c.get("status") != "FRESH"]
                if free and not free_stale:
                    return self._json(200, {
                        "skipped":   True,
                        "reason":    "all_free_caches_fresh",
                        "items":     [c["key"] for c in free],
                        "ages":      {c["key"]: c.get("age_str") for c in free},
                    })
            except Exception as e:
                # Soft-fail: if freshness check itself errors, fall through to
                # actually run daily_update (safer than skipping incorrectly).
                sys.stderr.write(f"[run-daily-update] freshness check failed: {e}\n")
            job_id, err = run_daily_update()
            if err:
                return self._json(500, {"error": err})
            return self._json(202, {"job_id": job_id, "name": "daily_update"})

        if path == "/api/break-news/refresh":
            if not BREAK_NEWS_AVAILABLE:
                return self._json(503, {"error": "break_news module not loaded"})
            try:
                res = _bn_poller.run_once()
            except Exception as e:
                return self._json(500, {"error": str(e)[:300]})
            return self._json(202, res)

        if path == "/api/supply-chain/generate":
            if not SUPPLY_CHAIN_AVAILABLE:
                return self._json(503, {"error": "supply_chain module not loaded"})
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception as e:
                return self._json(400, {"error": f"invalid JSON: {e}"})
            theme = (body.get("theme") or "").strip()
            if not theme:
                return self._json(400, {"error": "missing theme"})
            state, err = enqueue_protocol("supply_chain_generate", {"theme": theme}, source="supply_chain")
            if err == "duplicate":
                return self._json(409, state)
            if err:
                return self._json(400, {"error": err})
            return self._json(202, state)
        if path == "/api/break-news/raw/debate":
            if not BREAK_NEWS_AVAILABLE:
                return self._json(503, {"error": "break_news module not loaded"})
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception as e:
                return self._json(400, {"error": f"invalid JSON: {e}"})
            key = (body.get("key") or "").strip()
            if not _BREAK_NEWS_KEY_RE.match(key):
                return self._json(400, {"error": "invalid key"})
            entry = next((e for e in _bn_store.load_raw_stream()
                          if e.get("key") == key), None)
            if entry is None:
                return self._json(404, {"error": "raw item not found"})
            if entry.get("news_id"):
                # already a debate item — just re-queue it
                _bn_store.set_state(entry["news_id"], "pending_debate")
                nid = entry["news_id"]
            else:
                triage = {
                    "news_type":      entry.get("news_type"),
                    "shallow_score":  entry.get("shallow_score"),
                    "bull_case":      entry.get("bull_case"),
                    "bear_case":      entry.get("bear_case"),
                    "sector_view":    entry.get("sector_view"),
                    "macro_view":     entry.get("macro_view"),
                    "binary_flag":    entry.get("binary_flag"),
                    "advance_reason": "manual_raw",
                }
                source = {
                    "name":             entry.get("source"),
                    "credibility":      entry.get("credibility"),
                    "url":              entry.get("url"),
                    "feed_fingerprint": entry.get("feed_fingerprint"),
                    "published":        entry.get("published"),
                }
                nid = _bn_store.init_item(
                    source=source, triage=triage,
                    headline=(entry.get("headline") or "")[:200],
                    raw_summary=(entry.get("raw_summary") or "")[:400],
                )
                _bn_store.mark_raw_promoted(key, nid)
            threading.Thread(target=_bn_kick_debate_scan, daemon=True).start()
            return self._json(202, {"news_id": nid, "state": "pending_debate"})

        if path.startswith("/api/break-news/item/") and path.endswith("/replay"):
            tail = path[len("/api/break-news/item/"):-len("/replay")]
            if not _BREAK_NEWS_ID_RE.match(tail):
                return self._json(400, {"error": "invalid news_id"})
            if not BREAK_NEWS_AVAILABLE:
                return self._json(503, {"error": "break_news module not loaded"})
            d = _bn_store.load_item(tail)
            if d is None:
                return self._json(404, {"error": "not found"})
            # Reset to pending_debate so the next debate scan picks it up.
            _bn_store.set_state(tail, "pending_debate")
            return self._json(202, {"news_id": tail, "state": "pending_debate"})

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

        if path == "/api/journal-update":
            state, err = run_journal_update()
            if err:
                return self._json(409, {"error": err, "state": state})
            return self._json(202, {"status": "running", "state": state})

        if path == "/api/journal-update/status":
            with _journal_update_lock:
                return self._json(200, _journal_update_state.copy())

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
    print(f"Heatmap refresh:    every {HEATMAP_REFRESH_SEC}s, fan-out {HEATMAP_QUOTE_WORKERS} workers (static universe, market hours)")

    # Fresh prices on boot so the first Dashboard load is not stale
    run_bridge(reason="startup")
    # Warm the FRED cache on startup so the first Dashboard load has macro data.
    run_fred_refresh(reason="startup")
    # Background periodic refresh
    refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
    refresh_thread.start()
    fred_thread = threading.Thread(target=fred_refresh_loop, daemon=True)
    fred_thread.start()
    heatmap_thread = threading.Thread(target=heatmap_refresh_loop, daemon=True)
    heatmap_thread.start()

    # Break News (RSS poller + Claude/Gemini debate scanner)
    if BREAK_NEWS_AVAILABLE:
        try:
            reset = _bn_store.sweep_stuck_debating()
            if reset:
                print(f"break_news startup sweep: reset {reset} stuck debating items")
        except Exception as e:
            sys.stderr.write(f"[break_news] startup sweep failed: {e}\n")
        bn_poll_thread = threading.Thread(target=break_news_poll_loop, daemon=True,
                                          name="break_news_poll")
        bn_poll_thread.start()
        bn_debate_thread = threading.Thread(target=break_news_debate_loop, daemon=True,
                                            name="break_news_debate")
        bn_debate_thread.start()
        print(f"Break News:         poll every {BREAK_NEWS_INTERVAL_SEC}s "
              f"(Claude + Gemini CLI debate)")
    else:
        sys.stderr.write("[break_news] disabled (module not loaded)\n")

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nshutdown")
        _shutdown.set()
        srv.server_close()
