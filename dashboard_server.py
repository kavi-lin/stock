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

import fnmatch
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
from urllib.parse import parse_qs, urlparse, unquote

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
# A 401 is not a transient per-symbol failure. Once one request proves the
# credential is rejected, stop every heatmap FMP path for a long window. A
# corrected environment requires a server restart anyway, so retrying 517 symbols
# every poll only burns calls and floods stderr.
HEATMAP_AUTH_COOLDOWN = int(os.getenv("HEATMAP_AUTH_COOLDOWN", "21600"))  # 6h
_heatmap_breaker_reason = None  # None | "rate_limit" | "auth_<status>"
# Optional soft sub-cap so the always-on dashboard server doesn't starve a
# concurrent daily_update.sh run of the shared 250/min FMP budget. 0 = use the
# pool's full DEFAULT_TARGET_RPM. The pool's cross-process window is the actual
# ceiling; this just biases how much of it the dashboard claims.
FMP_DASHBOARD_RPM = int(os.getenv("FMP_DASHBOARD_RPM", "0"))

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
HEATMAP_INTRADAY_TTL_SEC_OPEN   = int(os.getenv("HEATMAP_INTRADAY_TTL_SEC_OPEN",   "60"))
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
# V4.85.0 — retry state for the PE warm-up. A cache entry whose value is not a dict
# is a *failure* and is retried under this backoff; only a real bundle gets the 24h TTL.
# V4.86.0 — `_heatmap_pe_run_lock` makes the warm-up non-reentrant: the boot thread and
# the refresh loop can otherwise start the same ~600-ticker residual batch at once,
# doubling the spend and racing the backoff globals.
_heatmap_pe_next_attempt_at = 0.0
_heatmap_pe_backoff_sec     = 0
_heatmap_pe_run_lock        = threading.Lock()
HEATMAP_PE_RETRY_BASE_SEC = int(os.getenv("HEATMAP_PE_RETRY_BASE_SEC", "300"))    # 5 min
HEATMAP_PE_RETRY_MAX_SEC  = int(os.getenv("HEATMAP_PE_RETRY_MAX_SEC", "3600"))    # 1h
# V4.86.0 — per-symbol retry floor for the radar lazy-fetch path. Those symbols live
# OUTSIDE `_heatmap_state["tickers"]`, so the warm-up's retry sweep never reaches them;
# without a floor of their own, a symbol whose three endpoints are genuinely empty gets
# refetched on every 180s quote-TTL expiry — ~60 FMP calls/hour, forever.
_heatmap_pe_attempted_at = {}                                            # {sym: epoch}
HEATMAP_PE_LAZY_RETRY_SEC = int(os.getenv("HEATMAP_PE_LAZY_RETRY_SEC", "21600"))  # 6h
# V4.86.2 — known-empty quarantine for the warm-up path. A handful of universe members
# have no ratios bundle at FMP at all (recent listings, non-operating shells, symbols FMP
# spells differently). They came back empty on every single pass, which pinned
# `_heatmap_pe_backoff_sec` at its ceiling forever and made the warm-up's
# `return not failed` permanently False — so the health signal stopped distinguishing
# "FMP is down" from "these four tickers have no P/E". `PE_ABSENT` is the fetcher's way
# of saying "answered, and there is nothing"; after N such results in a row a symbol is
# quarantined — skipped from the batch until the re-probe TTL. A transport failure
# (None) never counts toward the streak, so an outage cannot quarantine the universe.
# One success clears both the streak and the quarantine.
PE_ABSENT = "pe_absent"
_heatmap_pe_empty_streak = {}                                            # {sym: int}
_heatmap_pe_quarantined  = {}                                            # {sym: epoch marked}
HEATMAP_PE_EMPTY_STREAK_MAX = int(os.getenv("HEATMAP_PE_EMPTY_STREAK_MAX", "3"))
HEATMAP_PE_QUARANTINE_SEC   = int(os.getenv("HEATMAP_PE_QUARANTINE_SEC", "86400"))  # 24h
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

# ── Reverse-call to model CLI (protocol runner) ─────────────────────────
# Lets the Dashboard trigger the configured primary model CLI to execute a
# protocol (sector/news/invest). Provider selection happens once at launch.
# Single-job lock: one protocol at a time to avoid runaway token burn.
CLAUDE_BIN = os.environ.get("CLAUDE_BIN") or "/Users/kavi/.local/bin/claude"
AGY_BIN    = os.environ.get("AGY_BIN")    or "agy"
CODEX_BIN  = os.environ.get("CODEX_BIN")  or "/usr/local/bin/codex"
GROK_BIN   = os.environ.get("GROK_BIN")   or "/Users/kavi/.grok/bin/grok"

# Multi-model governance. Soft-import so the server still boots if the module
# is missing; that degraded path retains Claude as the safe legacy default.
try:
    from scripts._shared import model_router as _mrouter
    MODEL_ROUTER_AVAILABLE = True
except Exception as _mr_e:
    MODEL_ROUTER_AVAILABLE = False
    sys.stderr.write(f"[model_router] load failed: {_mr_e}\n")


# Per-protocol Claude model tier. Deep-reasoning protocols (multi-lane debate,
# valuation judgment, statistical root-cause) → opus; script-first / structured-
# extraction protocols (triage already deterministic, LLM only fills gaps) →
# sonnet (cheaper + faster, no quality loss). Values are passed verbatim to
# `claude --model`, so CLI aliases ("opus"/"sonnet") OR full ids
# ("claude-opus-4-8[1m]") both work. Override one protocol at runtime with env
# PROTOCOL_MODEL_<NAME> (e.g. PROTOCOL_MODEL_SECTOR=sonnet). Empty string / None
# → omit --model (inherit CLI global default).
PROTOCOL_MODEL = {
    "invest":      "opus",    # 5-lane debate + valuation + Red Team + price framework
    "llm_review":  "opus",    # statistical pattern + root-cause over 300KB index
    "sector":      "opus",    # Phase 5 cross-sector synthesis
    "news":        "sonnet",  # script-first triage, LLM debates ≤5
    "flash":       "sonnet",  # single-event 4-view debate
    "flash_text":  "sonnet",
    "review":      "sonnet",
    "link_digest": "sonnet",  # single-article extract + debate
    "triage":      "sonnet",  # headline_zh translation only
    "earnings":    "sonnet",  # structured infographic extraction
    "playbook":    "opus",    # 3-basket $100k portfolio construction + selection judgment
}
PROTOCOL_MODEL_DEFAULT = "sonnet"  # unlisted claude protocols → sonnet floor


# V4.115.0 — Subscription tier for the LLM quota panel.
#
# The broker reports a `plan` only for codex; claude comes back null and agy is
# intermittent. `lqb probe claude` does know ("max"), but it scrapes a TUI and
# takes 12.5s — far too slow for a panel that refreshes on a timer, and not
# worth a background thread for a string that changes once a year.
#
# Claude Code already wrote it to disk at login. Two fields, read on demand.
#
# This couples the dashboard to Claude Code's own state file, whose shape can
# change without notice, so every lookup is optional and a miss simply drops the
# chip. Nothing else on the panel depends on it. Only these two keys are read —
# the same file holds OAuth account identifiers that must never reach the API
# response, so the whole object is never returned, logged, or merged.
_CLAUDE_STATE = os.path.expanduser("~/.claude.json")

_RATE_TIER_SUFFIX = {"5x": "5×", "20x": "20×"}


def _claude_plan_label():
    """`MAX 5×` / `PRO` / None, from Claude Code's own login state."""
    try:
        with open(_CLAUDE_STATE, "r", encoding="utf-8") as f:
            acct = (json.load(f) or {}).get("oauthAccount") or {}
    except (OSError, json.JSONDecodeError, AttributeError):
        return None
    org = str(acct.get("organizationType") or "").strip()
    if not org:
        return None
    # "claude_max" → MAX, "claude_pro" → PRO. An unrecognised value is passed
    # through rather than dropped: a new tier name should show up as itself
    # instead of silently vanishing from the panel.
    base = org.replace("claude_", "").replace("_", " ").upper() or None
    if not base:
        return None
    # "default_claude_max_5x" → "5×". The multiplier is the part that actually
    # differs between two accounts on the same named plan.
    tier = str(acct.get("organizationRateLimitTier") or "")
    for key, suffix in _RATE_TIER_SUFFIX.items():
        if tier.endswith("_" + key):
            return f"{base} {suffix}"
    return base


def _annotate_plans(status):
    """Fill in public plan labels the broker could not supply.

    ``plan`` stays provider-native diagnostic data. UI clients consume only
    ``plan_label`` so an internal code such as Codex ``prolite`` never becomes
    product copy.
    """
    try:
        providers = ((status or {}).get("broker") or {}).get("providers") or {}
        if (
            isinstance(providers.get("claude"), dict)
            and not providers["claude"].get("plan_label")
        ):
            label = _claude_plan_label()
            if label:
                providers["claude"]["plan_label"] = label
    except Exception as e:  # noqa: BLE001 — a cosmetic chip must never 500 the panel
        sys.stderr.write(f"[llm-config] plan annotation skipped: {e}\n")
    return status


def _protocol_model_for(name):
    """Resolve the Claude model for a protocol. Env PROTOCOL_MODEL_<NAME> wins."""
    env = os.getenv("PROTOCOL_MODEL_" + name.upper())
    if env is not None:
        return env.strip()  # "" → caller omits --model
    return PROTOCOL_MODEL.get(name, PROTOCOL_MODEL_DEFAULT)


def _protocol_command(model, prompt, claude_model=None, timeout_sec=None):
    """Build the CLI argv for running an agentic protocol on `model`.
    The stdout reader just pipes to the log, so only the command differs.
    `claude_model` (when truthy) pins `claude --model` for tier control.
    `timeout_sec` is this protocol's budget; a CLI with its own shorter default
    must be told about it or that default silently wins."""
    if model == "gemini":
        # V4.109.1: `--output-format stream-json` added. This was the only one of
        # the four branches not asking for structured output, so the log was plain
        # prose and `parse_stream_log_usage` had nothing to read — every Agy run
        # settled with zero tokens. That never showed before the quota broker
        # started assigning providers, because the protocol had always taken the
        # configured chain default (claude).
        cmd = [AGY_BIN, "--print", prompt,
               "--output-format", "stream-json",
               "--dangerously-skip-permissions"]
        # V4.114.1 — `agy --print-timeout` defaults to 5m. Nothing here ever set
        # it, so PROTOCOL_TIMEOUT_OVERRIDES governed only the parent's
        # `proc.wait()` and every agy run was really capped at five minutes.
        #
        # That is what killed `invest_20260809_000447`: 308s wall — 5m08s — and
        # the stream ends on a bare "Agent execution terminated due to error."
        # The two agy `triage` runs that succeeded the day before took 1.7 and
        # 2.4 minutes, which is why the cap had never shown itself. Every
        # protocol except triage/flash budgets more than 5 minutes, so all of
        # them were exposed.
        #
        # The child is given slightly less than the parent so it times out first
        # and still emits a final result event to parse; the parent's hard kill
        # stays as the backstop for a child that ignores its own deadline.
        if timeout_sec:
            cmd += ["--print-timeout", f"{max(60, int(timeout_sec) - 30)}s"]
        return cmd
    if model == "codex":
        return [CODEX_BIN, "exec", "--json", "-C", ROOT,
                "--dangerously-bypass-approvals-and-sandbox", "--color", "never",
                "--ephemeral", prompt]
    if model == "grok":
        grok_bin = GROK_BIN if os.path.exists(GROK_BIN) else "grok"
        return [grok_bin, "--output-format", "streaming-json", "--cwd", ROOT,
                "--always-approve", "--no-memory", prompt]
    if model != "claude":
        raise ValueError(f"unsupported protocol model: {model}")
    claude_bin = CLAUDE_BIN if os.path.exists(CLAUDE_BIN) else "claude"
    cmd = [claude_bin, "-p", prompt,
           "--output-format", "stream-json", "--verbose",
           "--permission-mode", "bypassPermissions"]
    if claude_model:
        cmd += ["--model", claude_model]
    return cmd


def _select_protocol_model(name=None):
    """Resolve the launch-time provider AND reserve its quota. Returns (model, lease).

    `name` is the protocol being launched. It sizes the reservation and keys the
    ledger, because a `triage` run and an `invest` run are not the same order of
    magnitude — see `broker_gate.PROTOCOL_TASK_TYPE_PREFIX`.

    `acquire_protocol_lease()` preserves the UI's documented primary → secondary
    → tertiary availability policy, but settles it against the quota broker's
    view of what is actually left rather than a local call count. Agentic
    protocols cannot safely replay after a half-completed failure, so both the
    selection and the reservation happen once, before the subprocess starts.

    Raises when the run must not start — the broker unreachable, or no provider
    with capacity outside its 20% hard reserve. The caller turns that into a
    visible protocol error. It must not be swallowed into a default provider,
    which is what this function used to do and what left the largest consumer in
    this repo effectively ungoverned.

    Pass `lease` back to `note_run()` so the hold is settled with real tokens.
    """
    if MODEL_ROUTER_AVAILABLE:
        model, lease, _note = _mrouter.acquire_protocol_lease("agentic_protocol", name)
        return model, lease
    return "claude", None


# V4.114.0 — Each CLI has exactly one project context file it treats as its own.
# The preamble below names that file and no other, so a run never has to read a
# different provider's rules. Auto-load behaviour verified by probe 2026-08-09,
# each run from this repo's cwd with no tools allowed:
#   claude → CLAUDE.md   auto-loaded.
#   codex  → AGENTS.md   auto-loaded (answered validate_sector_intel.py →
#                        sector/schema.md, a pairing only AGENTS.md carries).
#   grok   → AGENTS.md   auto-loaded, same file as codex (quoted the AGENTS.md
#                        `rg` line verbatim, even under --no-memory).
#   gemini → GEMINI.md   **NOT auto-loaded** by `agy --print`. Two probes came
#                        back NONE and UNKNOWN. The preamble is the only thing
#                        that puts GEMINI.md in front of that model.
PROVIDER_CONTEXT_FILE = {
    "claude": "CLAUDE.md",
    "gemini": "GEMINI.md",
    "codex":  "AGENTS.md",
    "grok":   "AGENTS.md",
}

# Protocol → its own spec document, named directly in the prompt so a run never
# depends on the agent first locating a trigger table.
#
# The 2026-08-09 invest failure was exactly that dependency. `分析 NOW` carries
# no meaning to a CLI that has not loaded a trigger table, and agy loads none:
# the agent never once listed its own cwd, chased a stale mirror it found in
# ~/.gemini/projects.json, and died mid-`grep -rn` across the home directory
# after 208K tokens and zero artifacts.
PROTOCOL_DOC = {
    "invest":      "investment/investment_protocol_v5_0.md",
    "sector":      "sector/sector_protocol_main.md",
    "news":        "news/news_protocol_v2.md",
    "triage":      "news/news_protocol_v2.md",
    "flash":       "news/news_protocol_v2.md",
    "flash_text":  "news/news_protocol_v2.md",
    "review":      "news/news_protocol_v2.md",
    "link_digest": "news/link_digest_protocol.md",
    "earnings":    "skills/earnings-analyst/SKILL.md",
    "playbook":    "skills/weekly-tech-playbook/SKILL.md",
    "llm_review":  "reports/decision_review/REVIEW_PROMPT.md",
}


def _adapt_protocol_prompt(model, prompt, name=None):
    """Prefix the provider's own bootstrap without changing protocol semantics.

    Claude is returned untouched: it auto-loads CLAUDE.md, and every
    PROTOCOL_PROMPTS entry was written against that assumption. Every other CLI
    gets three things the Claude-shaped prompt silently assumed — its own
    context file, this protocol's spec path, and the tool-vocabulary mapping
    that used to be codex-only.

    The cwd clause is not boilerplate. It is the direct lesson of the failed
    run: given no protocol path, the agent searched `~/Documents`, `~/Stock` and
    `~/.claude` for this project while sitting inside it.
    """
    if model == "claude":
        return prompt
    ctx = PROVIDER_CONTEXT_FILE.get(model)
    doc = PROTOCOL_DOC.get(name)
    lines = []
    if ctx:
        lines.append(
            f"專案 context：本 repo 給你這個 CLI 的規範入口是 `{ctx}`（你只需要讀這一個檔，"
            f"不要去讀其他 provider 的 context 檔）。若你的 system prompt 裡沒有它的內容，"
            f"第一件事就是 Read `{ctx}`。")
    if doc:
        lines.append(
            f"本次要執行的 protocol 規範在 `{doc}` — 直接 Read 這個路徑，不要用搜尋去找它。")
    lines.append(
        "工具詞彙對照：protocol 文件用 Claude 的工具名當抽象操作。把 "
        "Read/Write/Edit/Grep/Bash/WebFetch/WebSearch 對應到你自己的檔案、shell、網路工具；"
        "把每個 Agent(...) 需求對應到一個隔離 subagent，protocol 要求平行 fan-out 時"
        "先把全部 agent 開起來再等待。每一道 validator 與 required-artifact gate 原封不動保留。")
    lines.append(
        "作業範圍：一律在目前工作目錄（cwd）這個 repo 內作業。cwd 以外的路徑"
        "（家目錄、~/Documents、~/Stock、其他 CLI 的 state 目錄）都不是本專案，"
        "禁止去那裡搜尋專案檔案。")
    return "\n".join(lines) + "\n\n" + prompt
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
    # link_digest: WebFetch article + WebSearch + fetch 3-5 related + 4-view debate
    # + build_artifacts (digest append + bn + graph refresh). 15 min headroom.
    "link_digest": int(os.getenv("LINK_DIGEST_TIMEOUT_SEC", "900")),  # 15 min
    "triage":     int(os.getenv("TRIAGE_TIMEOUT_SEC",      "600")),   # 10 min (fetch 30s + script triage + top-15 headline_zh)
    # V4.8 invest protocol: Phase 0-5 with subagents typically takes 30-45 min.
    # Default 25 min (1500s) is too short; 60 min gives comfortable headroom.
    "invest":     int(os.getenv("INVEST_TIMEOUT_SEC",     "3600")),  # 60 min
    # LLM Review of decision_review/event_index — 3-step statistical analysis,
    # event_index can be 300KB+ JSON, expect deeper reasoning pass. V4.47.3 — Step 0
    # (build_event_index.py) alone now takes ~8min (yfinance fetch volume has grown
    # with decision history); 900s left too little runway for the review+write steps
    # that follow, causing weekly hard-kills (rc=-1) mid-write. Bumped to match the
    # sector-protocol precedent for the same "history outgrew the timeout" reason.
    "llm_review": int(os.getenv("LLM_REVIEW_TIMEOUT_SEC", "1800")),  # 30 min
    # weekly-tech-playbook: build_pack (yfinance ~1 min) + LLM selection of 3×10
    # picks + validate-loop + render. 30 min headroom for an opus selection pass.
    "playbook":   int(os.getenv("PLAYBOOK_TIMEOUT_SEC",   "1800")),  # 30 min
}

PROTOCOL_PROMPTS = {
    "sector": "非互動模式：依 sector_protocol_main.md GLOBAL RULES 直接執行 Phase 0→5 完整流程，"
              "不要輸出「準備好進入 Phase X 嗎？」「請確認」這類停頓等候，一個 turn 完整收尾。"
              "Cache 衝突自動處理：若 sector_intel.json 的 mtime 看起來新但內部 `generated_at` 距今 ≥ 3 小時 "
              "（通常是 news protocol Phase 4 patch top_catalysts 造成的 mtime touch），"
              "視為 STALE 必須重跑 Phase 0–1，不要當成 FRESH 跳過。\n\n產業掃描",
    "news":   "非互動模式 + 硬規定（V2.2 script-first triage）：\n0. **必須先執行** `python3 news/fetch_all_news.py --hours 24 --output news/news_logs/` 重撈 4 個源（RSS + Finnhub + FMP + SEC EDGAR）合併成 unified raw.json\n1. **必須執行** `python3 news/scripts/stage1_triage.py`（deterministic triage：block/dedup/credibility/score/snap/晉級 gate，寫 YYYY-MM-DD_triage.json + stdout 印 triage 表）。**禁止讀 raw.json 全文、禁止 LLM 手工 triage** — 只讀 script stdout + triage.json 的 `stage2_items`（≤5 則）與 `shallow_verdicts` top-25\n2. **必須 dispatch 4 個 Agent tool_use**（Bull_Analyst / Bear_Analyst / Sector_Analyst / Macro_Analyst），不得在 thinking block 裡自己幻想 4 視角\n3. **必須 Write news_logs/YYYY-MM-DD_digest.json**（timestamp 必須是今天日期）。`stage1_count` = triage.json `shallow_verdicts` 長度；shallow 取 top 10、snaps 照抄 triage.json 不重寫；validator 有 freshness gate + triage cross-check 會擋\n4. 晉級名單 = triage.json `stage2_items`（script 已依 gate + |shallow_score| 取前 5）**不要停下等使用者確認**\n5. 跑完 Phase 3 Arbiter + Phase 4 cache patch + validator + 產出 reports/YYYY-MM-DD_news_digest.md（Shallow Digest top 10 照抄 snaps）\n6. **禁止**：讀昨天 MD 當範本、跳過 Stage 1/2 直接寫 MD、單 model 編 4-view 辯論\n7. 一個 turn 跑完整條 pipeline，不要中途停下。\n8. **每筆 verdict（不論 shallow/deep）必須帶 `published` 欄位**（從 triage.json 對應 news_id 抄過來的 ISO timestamp）— UI 用此算「Xm/Xh ago」freshness；deep 5 + shallow 10 補 `headline_zh`。\n\n新聞分析 DIGEST",
    "invest": "SESSION CONFIG: RISK_TOLERANCE={risk_tolerance}\n非互動模式：照 protocol 規則直接執行，不要輸出「請確認」類摘要表停下來等候。Phase 0 cache 策略：< 3h 用現有、否則 L3 重跑。\n\n分析 {ticker}",
    "flash":  "非互動模式：一個 turn 跑完 Stage 2 inline Deep Debate + Arbiter。依 news/news_protocol_v2.md 的 FLASH event-store 流程，只寫單筆 payload JSON，再呼叫 news_event_store.py append；禁止直接修改 digest.json 或 cache。最後產出 reports Impact Card。\n\n新聞分析 FLASH {ticker} 近期動態",
    "flash_text": "非互動模式：一個 turn 跑完 Stage 2 inline Deep Debate + Arbiter + event append，不要中途停下。輸入是富途推播原文（中英混排）：\n1. 抽出主體並 WebFetch 最近 24h 上下文。\n2. 跑 Bull/Bear/Sector/Macro 四視角。\n3. 寫單筆 payload 到 `news/news_logs/event_payloads/YYYY-MM-DD_HHMM_flash.json`。必含完整 prose、published ISO、source、affected_sectors、tickers、binary fields、macro_backdrop_delta，以及四 lane 的 `lane_scores` / `lane_confidences`；禁止自行計算 net score/weights/verdict。\n4. 執行 `python3 news/scripts/news_event_store.py append --mode FLASH --date YYYY-MM-DD --payload <payload>`；腳本會 deterministic 計分、產 stable event_id、append `news_events.jsonl` 並重建 digest projection。禁止直接 Write/Edit digest.json 或 cache。\n5. 產 `reports/YYYY-MM-DD_HHMM_news_flash.md`，標記 CLI 回傳的 event_id 與 review_status=pending。\n6. 執行 `python3 news/scripts/validate_digest_output.py`，rc=0 才完成。\n\n新聞分析 FLASH \"{headline}\"",
    "review": "非互動模式：一個 turn 跑完擴展辯論 + Arbiter + event append + cache projection + MD。先執行 `python3 news/scripts/news_event_store.py pending` 列出 pending events，再於 JSON 輸出中精確匹配本次 headline，取得唯一 event_id；0 筆或多筆皆停止並清楚回報。禁止把 untrusted headline 拼進 shell command，也不得用 headline 直接覆寫 digest。讀該 event payload，跑四 lane review，寫 `event_payloads/YYYY-MM-DD_HHMM_review.json`（含 lane_scores/lane_confidences 與完整 verdict prose，但禁止自行計算 net score/weights/verdict），再執行 `python3 news/scripts/news_event_store.py review --event-id <EVENT_ID> --payload <payload>`。腳本負責 append REVIEW event、deterministic projection 與 cache patch。禁止直接修改 digest.json、phase0.json 或 sector_intel.json。最後產 REVIEWED Impact Card 並跑 News validator rc=0。\n\n新聞分析 審核 \"{headline}\"",
    "link_digest": "非互動模式：一個 turn 跑完整條 link digest pipeline，不要中途停下等使用者回話。輸入是使用者提供的一條文章 URL：{url}\n依照 `news/link_digest_protocol.md` 規範執行：\n1. WebFetch({url}) 讀完整文章（headline / publisher / 發布時間 ISO / 主體）\n2. WebSearch 找 3-5 則相關報導並 WebFetch 前 3-5 篇讀全文（交叉佐證 + 找上下游/客戶/競品/產業/總經）\n3. 跑 4 視角 inline 辯論（Bull/Bear/Sector/Macro）+ Arbiter（net_impact_score -5~+5、verdict BULLISH/BEARISH/BINARY/NEUTRAL、arbiter_reasoning ≥150 字、debate_note 一行）\n4. 抽 entities（tickers/sectors/themes/tech_keywords）+ supply-chain relations（ticker↔ticker：SUPPLIES_TO/CUSTOMER_OF/CONTRACT_MFG_FOR/CO_DEVELOPS_WITH/COMPETES_WITH，格式 subject/object 用 \"ticker:NVDA\"；ticker→theme：BENEFITS_FROM/HEADWIND_FROM，object 用 \"theme:hbm\"），每條 relation 標 corroborating_sources（**≥2 源才會晉升為 KG 供應鏈 directed edge**）\n5. **必須產兩個檔（缺一不可）**：\n   (a) `reports/YYYY-MM-DD_HHMM_link_digest.md` — 人讀判斷 digest（來源摘要+原文連結 / 相關新聞綜述（附引用連結）/ 4 視角辯論 / Arbiter 裁決 / KG payload 附錄列出 entities+relations）\n   (b) `news/news_logs/link_digest/<id>.judgment.json` — 機器記錄，schema 見 link_digest_protocol.md（<id> = `ld_YYYYMMDD_<url 的 sha1 前 8 碼>`）\n6. **必須執行**：`python3 scripts/link_digest/build_artifacts.py news/news_logs/link_digest/<id>.judgment.json`（它負責 append LINK_DIGEST event、重建 digest projection、寫 bn_*.json KG payload、驗證與刷新 nexus graph；rc=0 或 rc=2 皆可收尾，rc=1 要修 judgment.json 重跑）\n7. **禁止**：自己手寫 digest.json / news_events.jsonl / bn_*.json（schema 由 build_artifacts 保證）、跳過 WebSearch、跑到一半停下問問題。\n\n連結分析 {url}",
    "triage": "非互動模式：只跑 Stage 1 deterministic triage，**禁止跑 Stage 2 deep debate**，**禁止寫 digest.json**，**禁止 patch sector_intel.json / phase0.json**。流程：\n1. **必須先執行** `python3 news/fetch_all_news.py --hours 24 --output news/news_logs/` 重撈 4 個源（RSS + Finnhub + FMP + SEC EDGAR）合併成 unified raw.json — 不能直接讀現有 raw，避免吃到舊資料\n2. **必須執行** `python3 news/scripts/stage1_triage.py` — script deterministic 寫 `news/news_logs/YYYY-MM-DD_triage.json`（block/dedup/credibility downgrade/news_type/score/4-view snap/晉級 gate 全內建）\n3. **禁止讀 raw.json 全文、禁止 LLM 重新 triage**。讀 triage.json 的 `shallow_verdicts` top-15，對這 15 則補 `headline_zh`（script 留 null），用單次 Edit 寫回 triage.json — 其餘欄位不動\n4. 一個 turn 跑完，不要中途停下等候。\n\n新聞分析 TRIAGE",
    "earnings": "非互動模式：照 skills/earnings-analyst/SKILL.md 跑完整 6 步驟（含 LLM narrate phase），不要中途停下等使用者確認。**MUST** sequentially run:\n1. `python3 skills/earnings-analyst/scripts/fetch.py {ticker}`（cache hit 也 OK；V1.73 抓 17 endpoints 含 transcript）\n2. `python3 skills/earnings-analyst/scripts/analyze.py {ticker}`\n3. `python3 skills/earnings-analyst/scripts/validate.py {ticker}` — 必須 rc=0\n4. **NARRATE phase（LLM in-conversation, NEW）** — 用 Read 工具讀 `skills/earnings-analyst/cache/{ticker}_<DATE>.json`（含 ~50K 字 transcript.content），用 Write 工具寫 `skills/earnings-analyst/cache/{ticker}_<DATE>.infographic.json`。Schema 見 `skills/earnings-analyst/schema.md` 「Infographic Cache (V1.0)」section。必抽：headline_oneliner / surprise / segments_q（**優先從 transcript CFO 段抽季度數字，無則退化 FY**） / capital_returns（buyback authorization、dividend hike、announcements）/ ceo_quote / key_highlights (≥3) / summary (≥2)\n5. `python3 skills/earnings-analyst/scripts/render.py {ticker}`\n6. `python3 skills/earnings-analyst/scripts/validate_infographic.py {ticker}` — 必須 rc=0\n\n結束條件：reports/<DATE>_{ticker}_earnings.md + cache/<TICKER>_<DATE>.infographic.json 都寫入 + 兩個 validate 都 rc=0。**禁止**：跳步驟、跳 validate、跑到一半停下問問題。\n\n財報 {ticker}",
    "llm_review": "非互動模式：對決策日曆做統計檢討，一個 turn 跑完不要中途停下。流程：\n0. **必須先 rebuild event_index**：`python3 scripts/build_event_index.py` — 此 indexer 掃 reports/ + investment/invest_logs/ + news/news_logs/ + sector/sector_logs/ 重建 `reports/decision_review/event_index_latest.json`（含每筆 decision 的 verdict、新增 `industry_rollup` + `adjustment_ledger_active` 兩個 top-level 欄位）。**rc 必須 0** 才繼續；rc≠0 就 fail 整個 protocol、不要硬跑舊 index。預期 ~30-60 秒。\n1. **Read** `reports/decision_review/REVIEW_PROMPT.md` 拿到完整 prompt 規範（**四步驟**：Step 0 Adjustment Evaluation + Step 1 Pattern + Step 2 Root Cause + Step 3 Recommendations）\n2. **Read** 剛 rebuild 的 `reports/decision_review/event_index_latest.json`（過去決策 + verdict 集合 + industry_rollup + adjustment_ledger_active，可能 300KB+）。確認 `generated_at` 是今天日期，否則 abort\n3. 依 REVIEW_PROMPT 四步驟執行：\n   - **Step 0 — Adjustment Evaluation（先做）**：對 `adjustment_ledger_active` 中每筆 active Rec，從 industry_rollup / decisions / 外部資料拉出 `target_metric` 當週數值，對照 ledger 的 `evaluation_history` 上次值，下 improved / no_change / regressed 判斷。連 3 週 no_change 建議 paused；regressed 建議 rolled-back。完整 ledger 在 `reports/decision_review/ADJUSTMENT_LEDGER.md`，schema 在 `ADJUSTMENT_LEDGER_SCHEMA.md`\n   - Step 1 — Pattern Detection：依 source / verdict / window_complete_pct / decisive_agent / regime / sub_industry_heat 統計顯著 pattern (N≥5 才算 pattern；N=3-4 標 preliminary；N≤2 標 speculation)。**必看 `industry_rollup`** 找 sub-industry / sector 集中性\n   - Step 2 — Root Cause Hypotheses：對每個 pattern 提出 1-2 個假設，引用 specific decision_id 為證據\n   - Step 3 — Adjustment Recommendations：給 protocol/config 具體調整建議（agent 權重、score 閾值、cycle phase 規則等），標 confidence (high/med/low) + 影響範圍\n4. **Write** 結果到 `reports/decision_review/REVIEW_<TODAY>.md`（YYYY-MM-DD 為今天日期）。Markdown 結構：\n```markdown\n# LLM Review · YYYY-MM-DD\n\n_event_index_at: <event_index 的 generated_at>_  \n_decisions_analyzed: <N>_\n\n## 0. Adjustment Evaluation\n| Rec | applied_date | target_metric | last_value | this_week_value | judgement |\n|---|---|---|---|---|---|\n\n## Pattern Detection\n### <Pattern Title> (n=N, N≥5 robust / N=3-4 preliminary / N≤2 speculation)\n- 證據：<引用 specific decisions>\n- 統計：<numbers>\n\n## Industry Rollup\n| industry | sector | n | miss_rate | avg_miss_return | tickers | top_30%? |\n|---|---|---|---|---|---|---|\n\n## Root Cause Hypotheses\n### <Hypothesis>\n- 對應 pattern：<which>\n- 推論：<reasoning>\n\n## Adjustment Recommendations\n### <Recommendation Title>\n- 動作：<concrete config change>\n- Confidence：high|med|low\n- 影響：<scope>\n```\n5. **禁止**：跳過 Step 0 indexer rebuild、跳過 Adjustment Evaluation、跑到一半停下問問題、輸出意見徵詢、未產出 MD 就結束。\n\n決策日曆 LLM Review",
    "playbook": "非互動模式：一個 turn 跑完整條 weekly-tech-playbook 生成流程，不要中途停下等使用者確認，不要輸出「請確認」摘要表。本流程為前瞻探索層，**不**進入也不回寫 investment_protocol 決策。完整規範見 `skills/weekly-tech-playbook/SKILL.md`。流程：\n1. 確定今天日期 DATE（YYYY-MM-DD）。\n2. **執行** `python3 skills/weekly-tech-playbook/scripts/build_pack.py`（即時抓 yfinance 報價）。它會寫 `skills/weekly-tech-playbook/data/pack_<DATE>.json`（含 regime、熱題、候選宇宙行情+動能、近 14 天委員會 verdict）與 `blind_pack_<DATE>.json`。stdout 會印出實際 DATE。\n3. **Read** `skills/weekly-tech-playbook/data/pack_<DATE>.json`。\n4. 依「最夯題材 + 委員會 verdict + 估值/動能紀律」為三個籃子各選 **10 檔**，寫 `skills/weekly-tech-playbook/data/selections_<DATE>.json`（schema 見 SKILL.md「selections JSON schema」）：\n   - 配重鐵律：每籃 tier_weights = 核心 $15k×3 + 標準 $10k×4 + 輕倉 $5k×3，**每籃 sum(weight_usd) 必須 == 100000**，每籃 10 檔，每檔必帶 `price`（直接抄 pack 報價）、`mom_5d`、`mom_1mo`、`theme`、`committee`、`reason`、`data`、`kill`。\n   - 🛡️保險(conservative)：megacap 質地 + 現金流 + 控估值，可較滿配；近月回檔的優質股視為再進場價值。\n   - 🔥激進(aggressive)：押最夯題材高 beta；近月已大漲 / 委員會標 extreme_overvalued / decision_cap 者降級為輕倉並標「等回檔」。\n   - ⚖️混合(hybrid)：保險 sleeve($65k) + 激進 sleeve($35k)，每檔加 `sleeve`(保險/激進) 欄位，整籃加總仍 == 100000。\n   - top-level 另填 `as_of`(=DATE)、`week_label`、`capital_per_basket`(100000)、`tier_weights`、`discipline_note`、`macro`(regime/exposure_ceiling/breadth/market_top/sentiment/real_rate_10y/key_events/playbook_logic — 從 pack 帶入)。\n   - （選配但建議）`codex_review`：第二意見。為求單 turn 穩定，用 `review_mode=\"committee_informed\"`（**不要**用 committee_blind_then_reconcile，那需要另存 blind_artifact 否則 render 會 fatal）。必填 label/reviewed_on/review_mode/committee_dependency/dependency_note/verdict + 至少 3 組 comparison_notes(title/original/note) + recommended_allocation(含現金且 sum(weight_pct)==100、ticker/role/weight_pct 齊全、無重複 ticker) + execution(≥1) + sources(≥2)。\n5. **驗證迴圈**：先跑 `python3 skills/weekly-tech-playbook/scripts/render.py --selections skills/weekly-tech-playbook/data/selections_<DATE>.json --validate-only`。若 rc==1（fatal），依錯誤訊息修 selections_<DATE>.json 再驗，直到 rc==0 或 rc==2。**rc==1 絕不可進下一步。**\n6. **正式渲染**：`python3 skills/weekly-tech-playbook/scripts/render.py --selections skills/weekly-tech-playbook/data/selections_<DATE>.json`。它會寫 `Dashboard/playbook.json`（餵 Dashboard）+ `reports/<DATE>_TECH_PLAYBOOK.md`（人讀）+ dated snapshot `data/playbook_<DATE>.json`。\n7. 結束條件：`Dashboard/playbook.json` + `reports/<DATE>_TECH_PLAYBOOK.md` 都寫入，且最終 render rc∈{0,2}。**禁止**：跳過 build_pack、跳過 validate-only、用假資料、價格欄位留空、跑到一半停下問問題、未產出 playbook.json 就結束。\n\n產生本週投資方案",
}

# Keep the runtime packet short: the detailed contract lives in the protocol
# and schema, while this prompt pins the non-negotiable execution gates.
PROTOCOL_PROMPTS["news"] = (
    # V4.114.0 — names the protocol doc directly. It used to route via "CLAUDE.md
    # trigger 對應的 …", which is a Claude-only instruction: this protocol runs on
    # agy and codex too, and sending them to another provider's context file is
    # the indirection the per-provider preamble exists to remove.
    "非互動執行 News V2.3，一個 turn 完整收尾。先讀 "
    "news/news_protocol_v2.md；依序跑 fetch_all_news.py、stage1_triage.py、"
    "build_digest_packet.py。之後只使用 compact packet：Stage 2 名單完全採用 "
    "stage2_items（可少於 5），直接 fetch packet URL，每篇交給四個隔離 lane 的 bundle "
    "最多 3000 chars；URL 缺失/失敗才 search。Arbiter 依 news/arbiter_rules.py，只有 "
    "binary_risk=true 可判 BINARY。依 news/debate_input_schema.md 只寫 compact debate JSON；"
    "禁止手寫 digest/MD/cache。最後只跑一次 finalize_digest.py，須 validator rc=0，"
    "完成 digest、idempotent cache patch 與 report，不得停下等確認。"
)
PROTOCOL_LOG_DIRS = {
    "sector":     "sector/scan_logs",
    "news":       "news/scan_logs",
    "invest":     "investment/scan_logs",
    "flash":      "news/scan_logs",
    "flash_text": "news/scan_logs",
    "review":     "news/scan_logs",
    "triage":     "news/scan_logs",
    "link_digest": "news/scan_logs",
    "earnings":   "skills/earnings-analyst/cache",
    "llm_review": "reports/decision_review",
    "playbook":   "skills/weekly-tech-playbook/logs",
    "earnings_preview": "skills/earnings-valuation-forecaster/cache",
    "supply_chain_generate": "nexus/supply_chain_logs",
    "weekly_review":       "logs/ops_protocols",
    "shadow_report":       "logs/ops_protocols",
    "backtest_postmortem": "logs/ops_protocols",
    "quant_backtest":      "logs/ops_protocols",
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
    # V4.6 — 節奏自動化: ops registry scripts runnable from UI / ops_auto_loop.
    # All read-only producers (weekly_review only SUGGESTS weights; never writes
    # weights.yaml).
    "weekly_review": {
        "cmd": ["python3", "skills/short-term-target/scripts/weekly_review.py"],
        "label_template": "📊 Weekly Review",
        "timeout": int(os.getenv("WEEKLY_REVIEW_TIMEOUT_SEC", "600")),
        "requires": [],
    },
    "shadow_report": {
        "cmd": ["python3", "investment/scripts/shadow_report.py"],
        "label_template": "🌓 Shadow Report",
        "timeout": int(os.getenv("SHADOW_REPORT_TIMEOUT_SEC", "300")),
        "requires": [],
    },
    "backtest_postmortem": {
        "cmd": ["python3", "investment/scripts/backtest_postmortem.py"],
        "label_template": "🔬 Postmortem",
        "timeout": int(os.getenv("POSTMORTEM_TIMEOUT_SEC", "900")),
        "requires": [],
    },
    # V4.63.0 — quant-backtest 策略回測 (探索層, 0 LLM, 不入 investment_protocol)。
    # requires 列出全部參數: placeholder 不吃預設值, 前端 (backtest.html) 必須
    # 每個 key 都送, 否則 "{...}" 字面殘留會被 argparse 擋下。模板各自的參數
    # 由前端打包成 params_json 字串 (JSON), 引擎端 resolve_params 解析。
    "quant_backtest": {
        "cmd": ["python3", "skills/quant-backtest/scripts/backtest.py", "{ticker}",
                "--template", "{template}", "--period", "{period}",
                "--cost-bps", "{cost_bps}", "--params-json", "{params_json}"],
        "label_template": "🧪 Backtest {ticker}",
        "timeout": int(os.getenv("QUANT_BACKTEST_TIMEOUT_SEC", "300")),
        "requires": ["ticker", "template", "period", "cost_bps", "params_json"],
    },
}

# quant-backtest 模板白名單 — 同步 skills/quant-backtest/scripts/backtest.py
# 的 STRATEGIES keys (result API 檔名驗證用)。
QUANT_BACKTEST_TEMPLATES = frozenset([
    "momentum", "ma_cross", "roc_trend", "donchian", "obv_trend",
    "boll_reversion", "supertrend", "triple_ma", "rsi_reversion",
    "high_52w", "keltner",
])

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
    "flash":  ["news/scripts/validate_digest_output.py"],
    "flash_text": ["news/scripts/validate_digest_output.py"],
    "review": ["news/scripts/validate_digest_output.py"],
}

# Post-run required-artifact gate. Catches a model returning rc=0 while leaving
# the expected output file unwritten (e.g. a fallback model timing out without
# producing the MD, yet the CLI still exiting 0). At least ONE listed path must
# exist AND be fresher than the run start, else status flips to "error" instead
# of being silently marked "done". `{today}` = run-start date (YYYY-MM-DD).
PROTOCOL_REQUIRED_ARTIFACTS = {
    "llm_review": ["reports/decision_review/REVIEW_{today}.md"],
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
    # V4.114.0 — which LLM the broker assigned to this run. None until the lease
    # is acquired, which is after the run is already marked "running".
    "model":      None,   # claude | gemini | codex | grok
    "model_tier": None,   # opus | sonnet | … for claude; "cli-default" elsewhere
}
_protocol_lock = threading.Lock()
_protocol_proc = {"p": None}  # mutable holder so cancel can reach it

# V2.7.17 — daily_update.sh shell pipeline state (parallel to Claude protocol queue)
# Tracks the bash daily_update.sh subprocess used by the new pre-market check
# orchestrator. Independent from Claude protocols so it can run in parallel
# with news / sector queue jobs.
_daily_update_state = {
    "job_id":      None,
    "status":      "idle",     # idle | running | done | degraded | error
    "started_at":  None,
    "ended_at":    None,
    "log_path":    None,
    "returncode":  None,
    "current_step": 0,
    "total_steps":  10,
    "elapsed_sec": 0,
    "log_tail":    "",
    "warning":     None,
    "error":       None,
}
_daily_update_lock = threading.Lock()
_daily_update_proc = {"p": None}


def _daily_update_outcome(returncode):
    """Map the shell contract without treating usable degradation as fatal."""
    if returncode == 0:
        return "done", None
    if returncode == 2:
        return "degraded", "daily_update.sh degraded (rc=2); usable artifacts were published"
    return "error", f"daily_update.sh exited rc={returncode}"


def _daily_update_is_terminal(status):
    return status in ("done", "degraded", "error")


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
        if t == "thread.started":
            thread_id = str(ev.get("thread_id") or "")
            events.append({"icon": "🚀", "text": f"Codex session started ({thread_id[:12]})"})
        elif t == "turn.started":
            events.append({"icon": "▸", "text": "Codex turn started"})
        elif t in ("item.started", "item.completed"):
            item = ev.get("item") or {}
            kind = item.get("type", "item")
            if kind == "agent_message" and t == "item.completed":
                text = str(item.get("text") or "").strip()
                if text:
                    events.append({"icon": "💬", "text": text[:160]})
            elif kind == "command_execution":
                cmd = str(item.get("command") or "")[:140]
                if t == "item.started":
                    events.append({"icon": "💻", "text": f"Command: {cmd}"})
                else:
                    rc = item.get("exit_code")
                    events.append({"icon": "✓" if rc in (0, None) else "✗",
                                   "text": f"Command rc={rc}: {cmd}"})
            elif kind in ("mcp_tool_call", "tool_call"):
                name = item.get("name") or item.get("tool") or "tool"
                events.append({"icon": "⚙", "text": f"{name}"})
        elif t == "turn.completed":
            usage = ev.get("usage") or {}
            bits = []
            if usage.get("input_tokens") is not None:
                bits.append(f"in {usage['input_tokens']}")
            if usage.get("output_tokens") is not None:
                bits.append(f"out {usage['output_tokens']}")
            events.append({"icon": "✅", "text": "Result: " + (" · ".join(bits) or "success")})
        elif t in ("turn.failed", "error"):
            err = ev.get("error") or ev.get("message") or "unknown error"
            if isinstance(err, dict):
                err = err.get("message") or str(err)
            events.append({"icon": "✗", "text": str(err)[:180]})
        elif t == "system":
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
        # V4.109.1 — Agy keys its events off `event`, not `type`, and nests each
        # payload under a key named after the event. Without this branch its
        # stream-json lines all fall through and the panel shows nothing but the
        # `===` header, which is worse than the plain prose the log used to hold.
        elif (e := ev.get("event")):
            payload = ev.get(e) if isinstance(ev.get(e), dict) else {}
            if e == "init":
                events.append({"icon": "🚀", "text": "Session started (agy)"})
            elif e == "step_update":
                step = payload.get("step_type") or "step"
                state = payload.get("state") or ""
                events.append({"icon": "▸", "text": f"{step} {state}".strip()})
            elif e == "result":
                usage = payload.get("usage") or {}
                bits = []
                if usage.get("input_tokens") is not None:
                    bits.append(f"in {usage['input_tokens']}")
                if usage.get("output_tokens") is not None:
                    bits.append(f"out {usage['output_tokens']}")
                if payload.get("num_turns") is not None:
                    bits.append(f"{payload['num_turns']} turns")
                # Agy reports SUCCESS in upper case; compared case-insensitively
                # so a healthy run is not flagged as a warning.
                status = str(payload.get("status") or "").upper()
                events.append({"icon": "✅" if status in ("", "SUCCESS", "OK") else "⚠",
                               "text": "Result: " + (" · ".join(bits) or status or "done")})

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
    """When a model subprocess exits non-zero, mine its JSONL log for the
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
            if t in ("turn.failed", "error"):
                msg = obj.get("error") or obj.get("message") or ""
                if isinstance(msg, dict):
                    msg = msg.get("message") or str(msg)
                if isinstance(msg, str) and msg.strip():
                    return msg.strip().splitlines()[0][:280]
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
        if params.get(req) is None or params.get(req) == "":
            # 0 是合法值 (如 cost_bps=0) — 只擋 None / 空字串
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
                    rerun = bool(params.get("rerun"))
                    slug = str(params.get("slug") or _sc.slugify(theme))
                    previous = _sc.load(slug) if rerun else None
                    lf.write(f"theme={theme} rerun={rerun} previous={bool(previous)}\n")
                    chain = _sc.enrich(_sc.generate(
                        theme,
                        previous_chain=previous,
                        rerun=rerun and previous is not None,
                    ))
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
    if "{url}" in PROTOCOL_PROMPTS[name] and not params.get("url"):
        return None, f"protocol '{name}' requires a 'url' parameter"
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
            # Cleared here, not left over from the previous run: the provider is
            # chosen per run, and a stale badge is worse than no badge.
            "model":       None,
            "model_tier":  None,
        })

    def _run():
        start = datetime.now()
        # Manual token replacement instead of str.format(**params): some prompts
        # embed JSON examples with literal {…}, which str.format would treat as
        # placeholders and raise KeyError (e.g. KeyError: '\n  "timestamp"').
        prompt = PROTOCOL_PROMPTS[name]
        for _k, _v in (params or {}).items():
            prompt = prompt.replace("{" + _k + "}", str(_v))
        # Select once from the shared primary → secondary → tertiary chain, and
        # reserve the quota before spending it. We do not replay a partially
        # completed agentic run on another provider: required artifact +
        # validator gates below are the safe failure boundary.
        #
        # A refusal here ends the run before it starts. That is deliberate: this
        # path is the largest single consumer in the repo, and it is the one the
        # 20% hard reserve exists to keep out of the last fifth of a window.
        proto_lease = None
        try:
            proto_model, proto_lease = _select_protocol_model(name)
        except Exception as e:
            with _protocol_lock:
                _protocol_state["status"]      = "error"
                _protocol_state["error"]       = f"quota broker: {e}"
                _protocol_state["ended_at"]    = _now_iso()
                _protocol_state["elapsed_sec"] = int((datetime.now() - start).total_seconds())
            _protocol_proc["p"] = None
            return
        prompt = _adapt_protocol_prompt(proto_model, prompt, name)
        claude_model = (_protocol_model_for(name) if proto_model == "claude" else None)
        # V4.114.0 — publish the winning provider so the run is attributable
        # everywhere it surfaces: the queue pill, the recent-runs line, and the
        # rendered report. The broker picks the provider at launch, so the only
        # place this is knowable is here.
        model_tier = claude_model or "cli-default"
        with _protocol_lock:
            _protocol_state["model"]      = proto_model
            _protocol_state["model_tier"] = model_tier
        # Resolved BEFORE the command is built, not after Popen as it used to be:
        # a CLI with its own shorter default deadline has to be told this number
        # or it silently overrides it (see the agy --print-timeout note above).
        timeout_sec = PROTOCOL_TIMEOUT_OVERRIDES.get(name, PROTOCOL_TIMEOUT_SEC)
        rc = -1
        telemetry_usage = {}
        try:
            lf = open(log_path, "w", buffering=1)
            lf.write(f"=== protocol={name} model={proto_model}:{claude_model or 'cli-default'} prompt={prompt!r} started={_now_iso()} ===\n")
            lf.flush()
            # stream-json: every event is one line of JSON → naturally line-buffered.
            # Intentionally NOT passing --include-partial-messages: those emit char-by-char
            # input_json_delta events (~4000 deltas per 34KB Write) which bloat the log
            # without providing info we actually parse. tool_use/tool_result/result events
            # arrive at block-level completion, which is plenty for event tracking.
            proc = subprocess.Popen(
                _protocol_command(proto_model, prompt, claude_model=claude_model,
                                  timeout_sec=timeout_sec),
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
                    # V4.114.0 — attribution for anything the run writes. Renderers
                    # invoked inside the protocol (render_investment_report.py and
                    # friends) stamp these into the report, so a reader can tell
                    # which engine produced it. Absent → the script was run by hand.
                    "AIC_PROTOCOL_MODEL":      proto_model,
                    "AIC_PROTOCOL_MODEL_TIER": model_tier,
                    "AIC_PROTOCOL_NAME":       name,
                    "AIC_PROTOCOL_JOB_ID":     job_id,
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

            # Record this run against the selected model's daily budget; a quota
            # wall in the log tail makes the next launch select another provider.
            if MODEL_ROUTER_AVAILABLE:
                try:
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as _lf:
                        _tail = _lf.read()[-4000:]
                    # Attribute this run's tokens by mining the provider JSONL.
                    try:
                        from scripts.break_news.llm_drivers import parse_stream_log_usage
                        _tok = parse_stream_log_usage(log_path)
                        telemetry_usage = _tok or {}
                    except Exception:
                        _tok = None
                    _mrouter.note_run(proto_model, rc == 0, "" if rc == 0 else _tail,
                                      tokens=_tok, lease=proto_lease)
                    proto_lease = None   # settled; the cleanup below must not cancel it
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

            # Required-artifact gate: rc=0 + validator pass still is not enough if
            # the run produced no fresh output file (fallback/timeout can exit 0
            # while writing nothing). At least one listed path must exist and be
            # newer than the run start; otherwise downgrade to "error".
            artifact_err = None
            if rc == 0 and validator_err is None and name in PROTOCOL_REQUIRED_ARTIFACTS:
                today = start.strftime("%Y-%m-%d")
                start_ts = start.timestamp()
                wanted = [a.replace("{today}", today) for a in PROTOCOL_REQUIRED_ARTIFACTS[name]]
                fresh = False
                for rel in wanted:
                    fp = os.path.join(ROOT, rel)
                    try:
                        if os.path.exists(fp) and os.path.getmtime(fp) >= start_ts - 1:
                            fresh = True
                            break
                    except OSError:
                        pass
                if not fresh:
                    artifact_err = (
                        "rc=0 but required artifact missing/stale: "
                        + ", ".join(wanted)
                        + " (model may have finished without writing output)"
                    )
                    try:
                        with open(log_path, "a") as _lf:
                            _lf.write(f"\n=== artifact gate FAILED: {artifact_err} ===\n")
                    except Exception:
                        pass

            with _protocol_lock:
                _protocol_state["ended_at"]    = _now_iso()
                _protocol_state["elapsed_sec"] = int((datetime.now() - start).total_seconds())
                if _protocol_state["status"] == "cancelled":
                    pass
                elif rc == 0 and validator_err is None and artifact_err is None:
                    _protocol_state["status"] = "done"
                else:
                    _protocol_state["status"] = "error"
                    if not _protocol_state["error"]:
                        _protocol_state["error"] = (
                            validator_err or artifact_err
                            or _extract_error_from_log(log_path, rc)
                        )
            _protocol_proc["p"] = None

            # Success → refresh data.json so Dashboard picks up new state
            if _protocol_state["status"] == "done":
                if name == "news":
                    try:
                        from news.scripts.news_event_store import append_run_telemetry
                        today = start.strftime("%Y-%m-%d")
                        with open(os.path.join(ROOT, "news", "news_logs", f"{today}_digest.json"), encoding="utf-8") as fp:
                            digest = json.load(fp)
                        triage_path = os.path.join(ROOT, "news", "news_logs", f"{today}_triage.json")
                        try:
                            with open(triage_path, encoding="utf-8") as fp:
                                stage2_items = json.load(fp).get("stage2_items") or []
                        except (OSError, json.JSONDecodeError):
                            stage2_items = []
                        sources, genres = {}, {}
                        for item in stage2_items:
                            source = str(item.get("source") or "unknown")
                            genre = str(item.get("content_genre") or "unknown")
                            sources[source] = sources.get(source, 0) + 1
                            genres[genre] = genres.get(genre, 0) + 1
                        deep = [v for v in (digest.get("verdicts") or []) if v.get("event_type", "DIGEST") == "DIGEST" and v.get("depth") == "deep"]
                        append_run_telemetry(
                            os.path.join(ROOT, "news", "news_logs", "news_events.jsonl"),
                            run_id=job_id, date=today,
                            payload={
                                "model": proto_model,
                                "stage2_count": len(deep),
                                "binary_count": sum(v.get("binary_risk") is True for v in deep),
                                "source_distribution": sources,
                                "genre_distribution": genres,
                                "input_tokens": telemetry_usage.get("input_tokens", 0),
                                "output_tokens": telemetry_usage.get("output_tokens", 0),
                                "cache_read_tokens": telemetry_usage.get("cache_read_tokens", 0),
                                "cache_write_tokens": telemetry_usage.get("cache_write_tokens", 0),
                                "cost_usd": telemetry_usage.get("cost_usd", 0.0),
                                "elapsed_sec": int((datetime.now() - start).total_seconds()),
                            },
                            recorded_at=_now_iso(),
                        )
                    except Exception as telemetry_error:
                        try:
                            with open(log_path, "a") as _lf:
                                _lf.write(f"\n=== telemetry warning: {telemetry_error} ===\n")
                        except Exception:
                            pass
                # zh-TW localise any new deep verdicts BEFORE bridge reads the digest,
                # so data.json carries the *_zh fields the News page renders. Best-effort
                # (gemini/agy); never blocks the pipeline on a translation hiccup.
                if name in ("news", "flash_text", "flash", "review"):
                    try:
                        subprocess.run(
                            [sys.executable, os.path.join(ROOT, "news", "scripts", "translate_digest.py")],
                            cwd=ROOT, capture_output=True, text=True, timeout=180,
                        )
                    except Exception:
                        pass
                run_bridge(reason=f"after {name} scan")
        except Exception as e:
            with _protocol_lock:
                _protocol_state["status"]    = "error"
                _protocol_state["error"]     = str(e)
                _protocol_state["ended_at"]  = _now_iso()
                _protocol_state["elapsed_sec"] = int((datetime.now() - start).total_seconds())
            _protocol_proc["p"] = None
        finally:
            # A hold that outlives its run makes every other project — and the
            # next protocol launch — see less headroom than really exists. The
            # broker reclaims it at TTL regardless, but six hours is a long time
            # to under-report a whole provider.
            if proto_lease is not None and MODEL_ROUTER_AVAILABLE:
                try:
                    proto_lease.cancel("protocol run ended without settling")
                except Exception:
                    pass

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
    if name == "link_digest":
        u = (p.get("url") or "")
        try:
            from urllib.parse import urlparse as _up
            host = _up(u).netloc or u
        except Exception:
            host = u
        return f"🔗 Link «{host[:24]}»"
    if name == "news":
        return "📰 DIGEST"
    if name == "triage":
        return "🗂 Triage"
    if name == "sector":
        return "🏭 Sector Scan"
    if name == "playbook":
        return "📋 本週方案"
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
            if params.get(req) is None or params.get(req) == "":
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
        else:
            # V4.6 — parameterless script protocols (weekly_review 等): dedup by name
            with _protocol_lock:
                if _protocol_state.get("status") == "running" and _protocol_state.get("name") == name:
                    return {"queued": False, "reason": "duplicate_active"}, "duplicate"
            with _protocol_queue_lock:
                if any(q.get("name") == name for q in _protocol_queue):
                    return {"queued": False, "reason": "duplicate_pending"}, "duplicate"

    if name == "supply_chain_generate":
        theme = str(params.get("theme") or "").strip()
        if not theme:
            return None, "missing theme"
        params["theme"] = theme
        params["rerun"] = bool(params.get("rerun"))
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

    # playbook dedup: parameterless generator — reject if already running/queued
    if name == "playbook":
        with _protocol_lock:
            if _protocol_state.get("status") == "running" and _protocol_state.get("name") == "playbook":
                return {"queued": False, "reason": "duplicate_active"}, "duplicate"
        with _protocol_queue_lock:
            if any(q.get("name") == "playbook" for q in _protocol_queue):
                return {"queued": False, "reason": "duplicate_pending"}, "duplicate"

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
                # None for the first seconds of a run — the broker has not
                # answered yet. The UI omits the badge rather than guessing.
                "model":       _protocol_state.get("model"),
                "model_tier":  _protocol_state.get("model_tier"),
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
                        # Rejected before dispatch, so no provider was ever
                        # chosen. Keys kept for a uniform shape in the UI.
                        "model":      None,
                        "model_tier": None,
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
                final_model  = _protocol_state.get("model")
                final_tier   = _protocol_state.get("model_tier")
            with _protocol_queue_lock:
                _protocol_history.insert(0, {
                    "name":     name,
                    "label":    label,
                    "ticker":   params.get("ticker"),
                    "status":   final_status,
                    "error":    final_error if final_status == "error" else None,
                    "ended_at": _now_iso(),
                    # Which engine actually ran it. The 2026-08-09 invest failure
                    # was only diagnosable by opening the log header; a run that
                    # went to an unexpected provider should be visible in the UI.
                    "model":      final_model,
                    "model_tier": final_tier,
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
    """Spawn bash daily_update.sh in a background thread, parse [N/10] step
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
            "total_steps":  10,
            "elapsed_sec":  0,
            "log_tail":     "",
            "warning":      None,
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
                # Stream stdout line-by-line; parse [N/10] step markers
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
                status, message = _daily_update_outcome(rc)
                _daily_update_state["returncode"] = rc
                _daily_update_state["ended_at"]   = _now_iso()
                _daily_update_state["status"]     = status
                _daily_update_state["warning"]    = message if status == "degraded" else None
                _daily_update_state["error"]      = message if status == "error" else None
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
# ── X KOL theme heat (exploration layer) ─────────────────────────────────
# Heat itself is recomputed per request — it is a pure read of an append-only
# JSONL and costs nothing. The FMP price/identity enrichment is what costs, so
# only that is cached; a stale price on a thermometer is harmless, a stale
# promote/reject decision is not (POST clears the cache).
# `attempted` is what stops an endless refresh loop: a ticker with no price
# series (e.g. $SIVE) never appears in `prices`, so keying "do we still need a
# refresh?" off `prices` would re-fan-out on every single request forever.
_X_KOL_CACHE = {"at": 0.0, "prices": {}, "identity": {}, "unanalyzable": {},
                "attempted": set()}
_X_KOL_PRICE_TTL_SEC = 600
_X_KOL_REFRESH_LOCK = threading.Lock()
_X_KOL_REFRESHING = {"active": False}


def _x_kol_refresh_prices(symbols):
    """Enrich in the BACKGROUND, never inside the request.

    The enrichment is ~3 FMP calls per ticker, and fmp_pool is a shared 220/min
    window — when the heatmap's 517-ticker / 20-worker fan-out is mid-flight our
    handful of calls queue behind it and the HTTP request hangs for minutes
    (observed: prices=0 answered in 9ms, prices=1 timed out past 90s). A
    thermometer must never hold a page hostage to someone else's fan-out, so the
    request serves whatever is cached and the refresh catches up.
    """
    from scripts.x_kol import heat as _xheat
    try:
        prices = _xheat.fetch_price_context(symbols)
        identity = _xheat.resolve_identity(symbols)
        stats = {s: {} for s in symbols}
        with _X_KOL_REFRESH_LOCK:
            _X_KOL_CACHE.update({
                "at": time.time(), "prices": prices, "identity": identity,
                "unanalyzable": _xheat.mark_unanalyzable(stats, prices, identity),
                "attempted": set(symbols),
            })
    except Exception as e:
        print(f"[x-kol] price refresh failed: {e}")
    finally:
        with _X_KOL_REFRESH_LOCK:
            _X_KOL_REFRESHING["active"] = False


def _x_kol_candidates_path():
    from scripts.x_kol import budget as _xbudget
    config = _xbudget.load_config()
    return os.path.join(ROOT, (config.get("heat") or {}).get(
        "candidates_path", "news/x_kol_logs/x_kol_candidates.json"))


def _x_kol_heat_payload(*, with_prices=True):
    from pathlib import Path

    from scripts.x_kol import budget as _xbudget
    from scripts.x_kol import heat as _xheat

    config = _xbudget.load_config()
    heat_cfg = config.get("heat") or {}
    data = _xheat.build(config, with_prices=False)

    prices_pending = False
    if with_prices:
        symbols = [t["ticker"] for t in data["tickers"]]
        with _X_KOL_REFRESH_LOCK:
            stale = (time.time() - _X_KOL_CACHE["at"]) >= _X_KOL_PRICE_TTL_SEC
            missing = bool(set(symbols) - _X_KOL_CACHE["attempted"])
            busy = _X_KOL_REFRESHING["active"]
            if (stale or missing) and not busy and symbols:
                _X_KOL_REFRESHING["active"] = True
                prices_pending = True
                threading.Thread(target=_x_kol_refresh_prices, args=(symbols,),
                                 daemon=True, name="x_kol_prices").start()
            elif busy:
                prices_pending = True
            data["prices"] = dict(_X_KOL_CACHE["prices"])
            data["identity_flags"] = dict(_X_KOL_CACHE["identity"])
            data["unanalyzable"] = dict(_X_KOL_CACHE["unanalyzable"])

    cand_path = Path(_x_kol_candidates_path())
    cands = _xheat.refresh_candidates(
        {t["ticker"]: t for t in data["tickers"]}, cand_path,
        surface_min=float(heat_cfg.get("surface_min_score", 0.3)))
    for sym, reason in (data.get("unanalyzable") or {}).items():
        if sym in cands.get("tickers", {}):
            cands["tickers"][sym]["unanalyzable"] = reason

    ledger = _xbudget.load_ledger()
    log_path = os.path.join(ROOT, config["collect"]["shadow_log"])
    return {
        "heat": data,
        "prices_pending": prices_pending,
        "candidates": cands.get("tickers", {}),
        "budget": {
            "spent_usd": _xbudget.spent_usd(ledger, config),
            "total_usd": config["budget"]["total_usd"],
            "post_reads": ledger["post_reads"],
        },
        # Sort explicitly: within one sweep the API already returns newest-first,
        # so reversing the append order would show a sweep backwards. File order
        # is an implementation detail; created_at is the contract.
        "posts": sorted(_xheat.load_records(Path(log_path)),
                        key=lambda r: r.get("created_at") or "", reverse=True)[:60],
        "roster": [r for r in (config.get("roster") or []) if r.get("enabled")],
    }


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
    "warnings":    [],         # non-blocking phase-1 failures; chain still finishes
    "error":       None,
}

# Phase-1 items whose failure must NOT stop the chain. `sector` reads the breadth
# / FTD / market-top caches that daily_update refreshes, so a daily failure is a
# real dependency and still aborts. News has no such edge — sector never reads
# the digest — so a news failure used to cost the whole sector run for nothing
# (2026-08-06: digest was complete, only over-cap by the shallow validator, and
# sector never ran). It now records a warning and the chain proceeds.
_PREMARKET_NONBLOCKING = {"news"}


def _wait_protocol_completion(name, baseline_ts, timeout_sec, on_progress=None):
    """Block until a fresh completion entry for protocol `name` appears in
    _protocol_history with ended_at >= baseline_ts. Calls on_progress(running,
    elapsed) every 2s while waiting. Returns the history entry dict on success,
    raises RuntimeError on timeout.

    NOTE: baseline is a TIMESTAMP, not a list length. _protocol_history is capped
    at _PROTOCOL_HISTORY_MAX (insert(0) + del[MAX:]), so its length stays constant
    once full — the old count-based baseline (history[:len-baseline]) sliced to
    empty forever and never matched, forcing every wait to its full timeout even
    when the protocol had completed. Bug 2026-06-15 (premarket chain false-advance:
    news/sector frozen at timeout wall while the next phase launched anyway)."""
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
        # Match the newest completion for `name` that ended at/after baseline_ts.
        match = None
        for h in history:
            if h.get("name") != name:
                continue
            ended = h.get("ended_at")
            if not ended:
                continue
            try:
                if datetime.fromisoformat(ended) >= baseline_ts:
                    match = h
                    break
            except ValueError:
                continue
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
            "warnings":    [],
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
                    if _daily_update_is_terminal(s):
                        break
                with _daily_update_lock:
                    final = _daily_update_state.get("status")
                    warning = _daily_update_state.get("warning")
                    err = _daily_update_state.get("error")
                _set_item("daily", status=final, reason=warning, error=err)
                if final == "error":
                    phase1_errors.append(("daily", err or "unknown"))

            def _run_news():
                news_check = next((c for c in preflight_check() if c["key"] == "news"), None)
                if news_check and news_check.get("status") == "FRESH":
                    _set_item("news", status="skipped", reason="today_digest_fresh")
                    return
                baseline_ts = datetime.now().replace(microsecond=0)
                try:
                    state, err = enqueue_protocol("news", source="premarket_chain")
                    if err and err != "duplicate":
                        raise RuntimeError(f"news enqueue failed: {err}")
                except Exception as e:
                    _set_item("news", status="error", error=str(e))
                    phase1_errors.append(("news", str(e)))
                    return
                _set_item("news", status="queued")
                # _run_news runs on its own thread — a RuntimeError (timeout) here
                # would escape silently, leaving phase1_errors empty so the chain
                # would false-advance to sector. Catch it and record the failure.
                try:
                    done_entry = _wait_protocol_completion(
                        "news", baseline_ts, timeout_sec=1500,
                        on_progress=lambda running, sec: _set_item(
                            "news", status="running" if running else "queued", elapsed_sec=sec),
                    )
                except Exception as e:
                    _set_item("news", status="error", error=str(e))
                    phase1_errors.append(("news", str(e)))
                    return
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
            # Items have already had their own state set to "error". Only a
            # blocking item aborts the chain; non-blocking ones (see
            # _PREMARKET_NONBLOCKING) downgrade to a warning so phase 2 still runs.
            blocking = [e for e in phase1_errors if e[0] not in _PREMARKET_NONBLOCKING]
            if blocking:
                raise RuntimeError(f"phase 1 failed ({blocking[0][0]}): {blocking[0][1]}")
            if phase1_errors:
                with _premarket_chain_lock:
                    _premarket_chain_state["warnings"] = [
                        f"{key}: {msg}" for key, msg in phase1_errors
                    ]

            # ── Phase 2: sector ─────────────────────────────────
            with _premarket_chain_lock:
                _premarket_chain_state["phase"] = "phase_2"
            sector_check = next((c for c in preflight_check() if c["key"] == "sector"), None)
            if sector_check and sector_check.get("status") == "FRESH":
                _set_item("sector", status="skipped", reason="today_intel_fresh")
            else:
                baseline_ts = datetime.now().replace(microsecond=0)
                state, err = enqueue_protocol("sector", source="premarket_chain")
                if err and err != "duplicate":
                    raise RuntimeError(f"sector enqueue failed: {err}")
                _set_item("sector", status="queued")
                # V2.20.1 — sector V1.4 PARALLEL_SUBAGENT typically takes 15-21 min
                # (p95 ~21 min). Old 1200s/20min cap was too tight, hit timeout on 5/10
                # despite sector still running. Bumped to 1800s/30min for headroom.
                try:
                    done_entry = _wait_protocol_completion(
                        "sector", baseline_ts, timeout_sec=1800,
                        on_progress=lambda running, sec: _set_item(
                            "sector", status="running" if running else "queued", elapsed_sec=sec),
                    )
                except Exception as e:
                    # Surface timeout on the sector item too (the outer try sets the
                    # chain to error, but leaves the item frozen at "queued" otherwise).
                    _set_item("sector", status="error", error=str(e))
                    raise
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
    min_score = params.get("min_score")
    if min_score is None and not params.get("tickers"):
        min_score = 65
    if min_score is not None:
        cmd += ["--min-score", str(min_score)]
    if params.get("top") is not None:
        cmd += ["--top", str(params["top"])]
    if params.get("stage"):
        cmd += ["--stage", str(params["stage"])]
    min_rs = params.get("min_rs")
    if min_rs is None and not params.get("tickers"):
        min_rs = 60
    if min_rs is not None:
        cmd += ["--min-rs", str(min_rs)]
    min_nhp = params.get("min_nhp")
    if min_nhp is None and not params.get("tickers"):
        min_nhp = -10
    if min_nhp is not None:
        cmd += ["--min-nhp", str(min_nhp)]
    if params.get("top_sectors") is not None:
        cmd += ["--top-sectors", str(params["top_sectors"])]
    if params.get("cooldown_snapshots") is not None:
        cmd += ["--cooldown-snapshots", str(params["cooldown_snapshots"])]
    for sig in params.get("signals", []) or []:
        cmd += ["--signal", str(sig)]
    exclude_signals = list(params.get("exclude_signals", []) or [])
    exclude_warnings = list(params.get("exclude_warnings", []) or [])
    if not params.get("tickers"):
        for sig in ("squeeze_candidate", "dtc_squeeze_candidate"):
            if sig not in exclude_signals:
                exclude_signals.append(sig)
        for w in ("fresh_death_cross_20_50", "fresh_death_cross_50_200"):
            if w not in exclude_warnings:
                exclude_warnings.append(w)
    for sig in exclude_signals:
        cmd += ["--exclude-signal", str(sig)]
    for w in exclude_warnings:
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
    global _heatmap_ratelimit_until, _heatmap_breaker_reason
    from urllib.request import Request, urlopen
    from urllib.error  import URLError, HTTPError
    # All FMP-backed heatmap features share this helper. This early check keeps
    # news/intraday/lazy quote calls quiet too, not only the main quote fan-out.
    if time.time() < _heatmap_ratelimit_until:
        return None
    # Count this call against the shared cross-process 250/min window so the
    # dashboard's ~500-ticker fan-out and a concurrent daily_update.sh run never
    # collectively exceed FMP's limit. Keeps the urllib transport (so the 429
    # circuit breaker below stays intact) — only the pacing is delegated.
    try:
        from scripts._shared import fmp_pool
        fmp_pool.acquire_slot(block=True,
                              target_rpm=FMP_DASHBOARD_RPM or None)
    except Exception:
        pass
    try:
        req = Request(url, headers={"User-Agent": "ai-invest-dashboard/heatmap"})
        with urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        if getattr(e, "code", None) == 429:
            now = time.time()
            with _heatmap_lock:
                first = now >= _heatmap_ratelimit_until
                _heatmap_ratelimit_until = max(
                    _heatmap_ratelimit_until, now + HEATMAP_RATELIMIT_COOLDOWN)
                if first:
                    _heatmap_breaker_reason = "rate_limit"
            if first:
                sys.stderr.write(f"[heatmap] FMP rate-limited (429) — pausing quote "
                                 f"refresh {HEATMAP_RATELIMIT_COOLDOWN}s\n")
        elif getattr(e, "code", None) == 401:
            code = int(e.code)
            now = time.time()
            with _heatmap_lock:
                reason = f"auth_{code}"
                first = now >= _heatmap_ratelimit_until or _heatmap_breaker_reason != reason
                _heatmap_ratelimit_until = max(
                    _heatmap_ratelimit_until, now + HEATMAP_AUTH_COOLDOWN)
                _heatmap_breaker_reason = reason
            if first:
                sys.stderr.write(
                    f"[heatmap] FMP authorization rejected ({code}) — pausing all "
                    f"heatmap FMP requests for {HEATMAP_AUTH_COOLDOWN}s; verify "
                    "FMP_API_KEY and restart the Dashboard\n")
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

    # Shared 429/auth circuit breaker — skip the whole ~500-call fan-out.
    if time.time() < _heatmap_ratelimit_until:
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

    # A permanent auth/plan error can trip mid-fan-out. Do not overwrite a good
    # cached snapshot's timestamp with a misleading 0/N "refresh".
    if not quotes and time.time() < _heatmap_ratelimit_until:
        return False

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
            # V4.86.0 — rate-limit the retry of symbols that have no bundle yet. These
            # are outside the heatmap universe, so `_heatmap_refresh_pe_universe`'s
            # retry sweep never covers them; the only thing standing between a
            # permanently-empty symbol and an unbounded refetch loop is this floor.
            if not pe_entry:
                with _heatmap_pe_lock:
                    last_try = _heatmap_pe_attempted_at.get(sym, 0.0)
                if (now - last_try) >= HEATMAP_PE_LAZY_RETRY_SEC:
                    fetched_syms.append(sym)

    # Lazy PE fetch for newly-seen symbols (background — populates next render)
    if fetched_syms:
        with _heatmap_pe_lock:
            for s in fetched_syms:
                _heatmap_pe_attempted_at[s] = now

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
                    # V4.85.0 — only a real bundle is cached. Caching a failure would
                    # park an empty entry against the 24h TTL and make the symbol look
                    # resolved. The retry floor above is what bounds the cost instead.
                    if isinstance(pe, dict):
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
    """Fetch today's 1-minute OHLCV bars via FMP /stable/historical-chart/1min.

    Returns {symbol, as_of, market_open, bars: [{time, o, h, l, c, v}, ...]}.
    On weekend / pre-market when today is empty, falls back to last 7 days.
    """
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return {"symbol": ticker, "error": "FMP_API_KEY not set", "bars": [],
                "as_of": _now_iso(), "market_open": False}

    today = date.today().isoformat()
    url = (f"https://financialmodelingprep.com/stable/historical-chart/1min"
           f"?symbol={ticker}&from={today}&to={today}&apikey={api_key}")
    rows = _fmp_get_json(url, timeout=10)

    if not isinstance(rows, list) or not rows:
        # Empty response (weekend / pre-market / holiday) — pull last 7 days
        seven_ago = (date.today() - timedelta(days=7)).isoformat()
        url = (f"https://financialmodelingprep.com/stable/historical-chart/1min"
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

    Three distinct return values:
      dict          — {"pe_ttm", "ev_ebitda", "fwd_eps"} (any field may be None on miss)
      `PE_ABSENT`   — all three endpoints answered, none had a row: FMP has no valuation
                      bundle for this symbol at all
      None          — nothing was actually fetched (rate-limit breaker open, or the
                      transport failed)

    V4.85.0 — previously an unattempted fetch returned the all-None dict, which the
    caller could not tell apart from a genuine "this ticker has no P/E" and cached for
    the full 24h TTL. V4.86.2 splits the remaining ambiguity: "answered with nothing"
    and "did not answer" were both None, so the warm-up could not tell a permanently
    data-less universe member apart from an outage and retried it on every pass forever.
    Forward PE is computed live in quote refresh (price / fwd_eps), so price
    drift within the 24h cache window stays accurate."""
    base = "https://financialmodelingprep.com/stable"
    out = {"pe_ttm": None, "ev_ebitda": None, "fwd_eps": None}
    # honor the 429 breaker — skip the 3 calls if cooling down
    if time.time() < _heatmap_ratelimit_until:
        return None

    def _safe_round(v, n=2):
        try:
            return round(float(v), n) if v is not None else None
        except (TypeError, ValueError):
            return None

    # `responded` tracks whether ANY endpoint actually came back with rows. A ticker
    # whose three calls all return empty is indistinguishable from an outage at this
    # level, so it is reported as a failure and retried rather than cached as fact.
    #
    # V4.86.0 — `responded` alone is not enough. If the 429 breaker trips partway
    # through, the first endpoint's value is real but the other two are None *because
    # of the outage*, and returning that bundle caches a half-filled record as fact for
    # 24h — the very "store a failure as data" bug this function was changed to stop,
    # just at field rather than record granularity. So the breaker is re-checked at the
    # end: if it tripped during these calls, the partial bundle is discarded.
    responded = False
    breaker_at_entry = _heatmap_ratelimit_until

    # `answered` counts endpoints that came back well-formed, empty list included. That
    # is what separates "this symbol has nothing" from "the transport is down" — the
    # latter surfaces as None out of `_fmp_get_json`, never as a list.
    answered = 0

    def _rows(url):
        nonlocal answered
        raw = _fmp_get_json(url, timeout=10)
        if isinstance(raw, list):
            answered += 1
            return raw
        return []

    # 1) PE TTM
    rows = _rows(f"{base}/ratios-ttm?symbol={ticker}&apikey={api_key}")
    if rows:
        responded = True
        out["pe_ttm"] = _safe_round(rows[0].get("priceToEarningsRatioTTM"), 2)

    # 2) EV/EBITDA TTM
    rows = _rows(f"{base}/key-metrics-ttm?symbol={ticker}&apikey={api_key}")
    if rows:
        responded = True
        out["ev_ebitda"] = _safe_round(rows[0].get("evToEBITDATTM"), 2)

    # 3) Forward EPS (closest future fiscal year, sorted asc)
    rows = _rows(
        f"{base}/analyst-estimates?symbol={ticker}&period=annual&limit=4&apikey={api_key}")
    if rows:
        responded = True
        today_iso = date.today().isoformat()
        future = sorted(
            [r for r in rows if (r.get("date") or "") > today_iso],
            key=lambda r: r.get("date") or "",
        )
        if future:
            out["fwd_eps"] = _safe_round(future[0].get("epsAvg"), 4)

    if not responded:
        # Every endpoint answered and none had a row → the symbol is genuinely absent
        # from FMP's valuation coverage. Anything less is an outage, and stays retryable.
        return PE_ABSENT if answered == 3 else None
    if _heatmap_ratelimit_until != breaker_at_entry:
        # Rate limit tripped mid-ticker: whatever is still None here may well exist.
        return None
    return out


def _heatmap_refresh_pe_universe(max_workers=10):
    """Refresh PE TTM for the heatmap universe. Uses a thread pool to parallelise the
    ~600 single-ticker calls (FMP has no batch ratios-ttm).

    V4.85.0 — retry-on-failure. Previously this ran exactly once, from a startup
    thread, and wrote `(now, result)` for every ticker regardless of outcome. A batch
    that failed mid-way (or an FMP rate-limit window at boot) therefore cached an
    empty bundle against the full 24h TTL, and since the heatmap loop never called
    this again, `heatmap.json` — and everything joined off it, including momentum-screen
    P/E — rendered blank until the next server restart.

    Now: failures are never cached, partial successes are kept, residual failures are
    retried on the next loop pass under an exponential backoff, and what got dropped
    is logged rather than left to look like a completed refresh.
    """
    global _heatmap_pe_next_attempt_at, _heatmap_pe_backoff_sec
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return False
    # Non-reentrant. The boot thread and the refresh loop both call this, and a residual
    # batch of ~600 tickers × 3 calls takes minutes — long enough for the loop to come
    # round and start the same batch again, doubling the spend and racing the backoff
    # globals below. Whoever is already running will finish the work.
    if not _heatmap_pe_run_lock.acquire(blocking=False):
        return False
    try:
        return _heatmap_refresh_pe_universe_locked(max_workers)
    finally:
        _heatmap_pe_run_lock.release()


def _heatmap_refresh_pe_universe_locked(max_workers):
    global _heatmap_pe_next_attempt_at, _heatmap_pe_backoff_sec
    api_key = os.getenv("FMP_API_KEY")
    now = time.time()
    if now < _heatmap_pe_next_attempt_at:
        return False
    if now < _heatmap_ratelimit_until:
        # Nothing was attempted, so do not treat this as a failed batch. The helper
        # already emitted the single actionable 401/429 line when it tripped.
        _heatmap_pe_next_attempt_at = _heatmap_ratelimit_until
        return False
    with _heatmap_lock:
        symbols = list(_heatmap_state["tickers"].keys())
    if not symbols:
        return False
    todo = []
    quarantined = 0
    with _heatmap_pe_lock:
        for sym in symbols:
            cached = _heatmap_pe_cache.get(sym)
            # A cached failure (value None) is retried as soon as the backoff allows;
            # only a real bundle earns the 24h TTL.
            if (cached and isinstance(cached[1], dict)
                    and (now - cached[0]) < HEATMAP_PE_TTL_SEC):
                continue
            marked = _heatmap_pe_quarantined.get(sym)
            if marked is not None and (now - marked) < HEATMAP_PE_QUARANTINE_SEC:
                quarantined += 1
                continue
            todo.append(sym)
    if not todo:
        _heatmap_pe_backoff_sec = 0
        _heatmap_pe_next_attempt_at = 0.0
        if quarantined:
            sys.stderr.write(f"[heatmap-pe] nothing to fetch — {quarantined} symbol(s) "
                             f"quarantined as known-empty\n")
        return True

    from concurrent.futures import ThreadPoolExecutor, as_completed
    sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] [heatmap-pe] fetching {len(todo)} tickers...\n")
    fetched = 0
    failed = []      # transport failures — retryable, these drive the backoff
    absent = []      # answered with nothing — a fact about the symbol, not a fault
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_fetch_pe_ttm, sym, api_key): sym for sym in todo}
        for fut in as_completed(futures):
            sym = futures[fut]
            try:
                pe = fut.result()
            except Exception:
                pe = None
            if isinstance(pe, dict):
                with _heatmap_pe_lock:
                    _heatmap_pe_cache[sym] = (time.time(), pe)
                fetched += 1
            elif pe is PE_ABSENT:
                absent.append(sym)
            else:
                # Leave any previously-good bundle in place — a failed refresh must not
                # blank out data that is merely stale.
                failed.append(sym)

    # Streak accounting. Only `absent` counts: a transport failure says nothing about
    # whether the symbol has data, so an outage can never quarantine the universe.
    stamp = datetime.now().strftime("%H:%M:%S")
    absent_set, failed_set = set(absent), set(failed)
    newly_quarantined = []
    with _heatmap_pe_lock:
        for sym in todo:
            if sym in absent_set:
                streak = _heatmap_pe_empty_streak.get(sym, 0) + 1
                _heatmap_pe_empty_streak[sym] = streak
                if streak >= HEATMAP_PE_EMPTY_STREAK_MAX:
                    _heatmap_pe_quarantined[sym] = time.time()
                    newly_quarantined.append(sym)
            elif sym not in failed_set:
                _heatmap_pe_empty_streak.pop(sym, None)
                _heatmap_pe_quarantined.pop(sym, None)
    if absent:
        sample = ", ".join(sorted(absent)[:8]) + (" …" if len(absent) > 8 else "")
        sys.stderr.write(
            f"[{stamp}] [heatmap-pe] {len(absent)} symbol(s) have no FMP valuation "
            f"bundle ({len(newly_quarantined)} newly quarantined for "
            f"{HEATMAP_PE_QUARANTINE_SEC}s) [{sample}]\n")

    if failed:
        # Escalating backoff, capped at the refresh interval that the loop polls on, so
        # a persistent outage costs one retry per pass rather than a tight loop.
        _heatmap_pe_backoff_sec = min(
            max(HEATMAP_PE_RETRY_BASE_SEC, _heatmap_pe_backoff_sec * 2),
            HEATMAP_PE_RETRY_MAX_SEC)
        _heatmap_pe_next_attempt_at = time.time() + _heatmap_pe_backoff_sec
        sample = ", ".join(sorted(failed)[:8]) + (" …" if len(failed) > 8 else "")
        sys.stderr.write(
            f"[{stamp}] [heatmap-pe] done: {fetched}/{len(todo)} — "
            f"{len(failed)} failed, retrying in {int(_heatmap_pe_backoff_sec)}s "
            f"[{sample}]\n")
    else:
        _heatmap_pe_backoff_sec = 0
        _heatmap_pe_next_attempt_at = 0.0
        no_data = f" ({len(absent)} with no FMP bundle)" if absent else ""
        sys.stderr.write(f"[{stamp}] [heatmap-pe] done: {fetched}/{len(todo)}{no_data}\n")

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
    return not failed


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

            # V4.85.0 — PE warm-up re-attempt: the only thing that gets a partially
            # failed warm-up back to full coverage without a server restart.
            # V4.86.0 — dispatched to its own thread. A residual batch can run for
            # minutes, and inline it would hold up the quote refresh above for the
            # rest of the loop period, freezing the heatmap mid-session. The
            # non-reentrancy lock inside makes a redundant dispatch a cheap no-op.
            threading.Thread(target=_heatmap_refresh_pe_universe, daemon=True).start()
        except Exception as e:
            sys.stderr.write(f"[heatmap] loop error: {e}\n")
            with _heatmap_lock:
                _heatmap_state["error"] = str(e)


_positions_lock = threading.Lock()


# ---------------------------------------------------------------- Ops Script 工具箱 (V3.47.0)
# Registry @ config/ops_scripts.json。last run 由 artifact_globs 最新 mtime 推斷（零侵入，
# 不要求 script 自己寫 run log）。cadence 超期 → status="due"；on_demand 不催。
_OPS_CADENCE_HOURS = {"daily": 26, "weekly": 8 * 24, "monthly": 32 * 24}


def _glob_ci(pattern):
    """glob with case-insensitive fallback. macOS filesystems are
    case-insensitive but Python's glob is not — a registry pattern like
    `*postmortem*` silently missing `POSTMORTEM_*.md` produced a false
    never_run badge (V4.6.1). Falls back to a lowercased fnmatch scan of the
    pattern's directory when the exact glob hits nothing."""
    hits = glob.glob(pattern)
    if hits:
        return hits
    d, _, name = pattern.rpartition(os.sep)
    if not d or any(ch in d for ch in "*?["):
        return []
    try:
        return [os.path.join(d, f) for f in os.listdir(d)
                if fnmatch.fnmatch(f.lower(), name.lower())]
    except OSError:
        return []


def ops_scripts_status():
    cfg_path = os.path.join(ROOT, "config", "ops_scripts.json")
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            registry = json.load(f).get("scripts", [])
    except (OSError, json.JSONDecodeError) as e:
        return {"error": f"ops_scripts.json unreadable: {e}", "scripts": []}

    now = time.time()
    out = []
    for s in registry:
        newest = None
        for pat in s.get("artifact_globs", []):
            for p in _glob_ci(os.path.join(ROOT, pat)):
                try:
                    m = os.path.getmtime(p)
                except OSError:
                    continue
                if newest is None or m > newest:
                    newest = m
        age_h = (now - newest) / 3600 if newest else None
        cadence = s.get("cadence", "on_demand")
        limit = _OPS_CADENCE_HOURS.get(cadence)
        if cadence == "on_demand":
            status = "on_demand"
        elif age_h is None:
            status = "never_run"
        elif age_h > limit:
            status = "due"
        else:
            status = "fresh"
        out.append({
            "id": s.get("id"), "name": s.get("name"), "cmd": s.get("cmd"),
            "desc": s.get("desc"), "cadence": cadence,
            "last_run_ts": int(newest) if newest else None,
            "last_run_age_hours": round(age_h, 1) if age_h is not None else None,
            "status": status,
            # V4.6 — 節奏自動化 passthrough
            "protocol_id": s.get("protocol_id"),
            "endpoint": s.get("endpoint"),
            "auto": bool(s.get("auto")),
        })
    order = {"due": 0, "never_run": 1, "fresh": 2, "on_demand": 3}
    out.sort(key=lambda r: (order.get(r["status"], 9), r["name"] or ""))
    return {"generated_at": int(now), "scripts": out}


# ── Ops auto-runner (V4.6 節奏自動化) ─────────────────────────────────────
# Every 30 min: any registry entry with auto:true that is due/never_run gets
# auto-dispatched. Whitelist = SCRIPT_PROTOCOLS (0-LLM scripts) + the journal
# endpoint. Claude protocols (e.g. llm_review) are NEVER auto-run here unless
# the OPS_AUTO_LLM=1 env opt-in is set AND the entry says auto:true — default
# is reminder-only (llm_review already has its own launchd weekly trigger).
OPS_AUTO_INTERVAL_SEC = int(os.getenv("OPS_AUTO_INTERVAL_SEC", "1800"))
OPS_AUTO_BACKOFF_SEC = int(os.getenv("OPS_AUTO_BACKOFF_SEC", "21600"))  # 6h — failed run leaves status due forever
_ops_auto_attempts = {}   # id -> last attempt ts


def ops_auto_loop():
    while True:
        time.sleep(OPS_AUTO_INTERVAL_SEC)
        try:
            now = time.time()
            for s in ops_scripts_status().get("scripts", []):
                if not s.get("auto") or s["status"] not in ("due", "never_run"):
                    continue
                sid = s.get("id")
                if now - _ops_auto_attempts.get(sid, 0) < OPS_AUTO_BACKOFF_SEC:
                    continue
                pid = s.get("protocol_id")
                if s.get("endpoint") == "/api/journal-update":
                    _ops_auto_attempts[sid] = now
                    print(f"[ops_auto] dispatch journal-update ({sid} {s['status']})", flush=True)
                    run_journal_update()
                elif pid in SCRIPT_PROTOCOLS:
                    _ops_auto_attempts[sid] = now
                    print(f"[ops_auto] enqueue {pid} ({sid} {s['status']})", flush=True)
                    enqueue_protocol(pid, source="ops_auto")
                elif pid and os.getenv("OPS_AUTO_LLM", "0") == "1":
                    _ops_auto_attempts[sid] = now
                    print(f"[ops_auto] enqueue LLM protocol {pid} (OPS_AUTO_LLM=1)", flush=True)
                    enqueue_protocol(pid, source="ops_auto")
        except Exception as e:
            print(f"[ops_auto] loop error: {e}", flush=True)


# ── Today Workbench (V4.6) ────────────────────────────────────────────────
# /api/today — server-side aggregation for the index.html workbench. Pulls
# from existing truth sources (ops_scripts_status / preflight_check /
# _list_reports_cached); deliberately NOT in bridge.py/data.json — due/staleness
# must be computed at request time, not on the 300s bridge cadence.

_REPORT_SUMMARY_CACHE = {}   # (path, mtime) -> list[str]
_BRIEF_REGIME_RE = re.compile(r"- \*\*(Breadth|FTD|Market-Top|Regime)\*\*:\s*(.+)")


def _extract_report_summary(full_path, type_key, mtime):
    """Deterministic key-line extraction per report type. 0 LLM; failure → []."""
    key = (full_path, mtime)
    if key in _REPORT_SUMMARY_CACHE:
        return _REPORT_SUMMARY_CACHE[key]
    out = []
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(4096)
        if type_key == "ic_memo":
            m = re.search(r"- \*\*Final Action\*\*:\s*(.+)", head)
            if m:
                out.append(m.group(1).replace("**", "").strip()[:120])
        elif type_key == "weekly_short":
            m = re.search(r"\*\*Total predictions evaluated\*\*:\s*(\d+)", head)
            h = re.search(r"\|\s*1d\s*\|\s*\d+\s*\|\s*([\d.]+%)", head)
            parts = ([f"{m.group(1)} preds"] if m else []) + ([f"1d hit {h.group(1)}"] if h else [])
            if parts:
                out.append(" · ".join(parts))
        elif type_key == "shadow":
            m = re.search(r"history entries scanned:\s*(\d+)", head)
            if m:
                out.append(f"{m.group(1)} entries scanned")
        elif type_key == "llm_review":
            m = re.search(r"_decisions_analyzed:\s*(\d+)_", head)
            if m:
                out.append(f"{m.group(1)} decisions analyzed")
        elif type_key == "premarket":
            for b in _BRIEF_REGIME_RE.finditer(head):
                out.append(f"{b.group(1)}: {b.group(2).replace('**', '').strip()[:80]}")
        if not out:
            for ln in head.splitlines():
                ln = ln.strip()
                if ln.startswith("## ") or ln.startswith("> "):
                    out.append(ln.lstrip("#> ").strip()[:120])
                    break
    except Exception:
        out = []
    if len(_REPORT_SUMMARY_CACHE) > 400:
        _REPORT_SUMMARY_CACHE.clear()
    _REPORT_SUMMARY_CACHE[key] = out
    return out


def _parse_morning_brief():
    """Latest reports/PREMARKET_<date>.md → regime bullets + top-5 movers."""
    files = sorted(glob.glob(os.path.join(REPORTS_DIR, "PREMARKET_*.md")))
    if not files:
        return None
    path = files[-1]
    name = os.path.basename(path)
    date_str = name[len("PREMARKET_"):-3]
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read(16384)
    except OSError:
        return None

    regime_lines = [f"{m.group(1)}: {m.group(2).replace('**', '').strip()}"
                    for m in _BRIEF_REGIME_RE.finditer(text)]

    def _movers(section):
        m = re.search(rf"### {section}\n((?:\|.*\n)+)", text)
        rows = []
        if m:
            for row in m.group(1).splitlines():
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                if len(cells) >= 2 and cells[0] and cells[0] not in ("Ticker", "---") \
                        and not set(cells[0]) <= {"-", ":"}:
                    rows.append([cells[0], cells[1]])
                if len(rows) >= 5:
                    break
        return rows

    return {
        "filename": name,
        "date": date_str,
        "is_today": date_str == datetime.now().strftime("%Y-%m-%d"),
        "regime_lines": regime_lines,
        "gainers": _movers("Gainers"),
        "losers": _movers("Losers"),
    }


def today_digest():
    """Aggregate due actions + latest outputs + morning brief for index workbench."""
    due_actions = []
    for s in ops_scripts_status().get("scripts", []):
        if s["status"] in ("due", "never_run") and s["cadence"] != "on_demand":
            due_actions.append({
                "kind": "ops_script", "id": s["id"], "name": s["name"],
                "status": s["status"], "age_hours": s["last_run_age_hours"],
                "cadence": s["cadence"], "cmd": s["cmd"],
                "protocol_id": s.get("protocol_id"), "endpoint": s.get("endpoint"),
                "auto": s.get("auto"),
            })
    try:
        for c in preflight_check():
            if c["status"] in ("STALE", "MISSING") and not c.get("free"):
                due_actions.append({
                    "kind": "protocol_stale", "key": c["key"], "label": c["label"],
                    "label_en": c["label_en"], "age_str": c["age_str"], "status": c["status"],
                })
    except Exception:
        pass

    items, _counts = _list_reports_cached()
    latest_outputs = []
    for it in sorted(items, key=lambda x: x["mtime"], reverse=True)[:10]:
        entry = dict(it)
        entry["summary_lines"] = _extract_report_summary(
            os.path.join(REPORTS_DIR, it["filename"]), it["type"], it["mtime"])
        latest_outputs.append(entry)

    return {
        "generated_at": int(time.time()),
        "due_actions": due_actions,
        "latest_outputs": latest_outputs,
        "morning_brief": _parse_morning_brief(),
    }


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

# ── Intraday market-weakness engine (companion to market_mood.json) ──────────
# Refreshes Dashboard/intraday_mood.json from FMP intraday 5-min bars + daily
# bars during US market hours (+ one post-close snapshot). FMP-only — Finnhub
# intraday candles are premium-gated. Read-only exploration layer; never feeds
# investment_protocol decisions.
INTRADAY_MOOD_INTERVAL_SEC = int(os.getenv("INTRADAY_MOOD_INTERVAL_SEC", "300"))
INTRADAY_MOOD_OUTPUT = os.path.join(DASHBOARD_DIR, "intraday_mood.json")
_intraday_mood_state = {"last_poll": None, "last_error": None, "last_score": None}
_intraday_mood_lock = threading.Lock()
try:
    _ia_scripts = os.path.join(ROOT, "skills", "market-sentiment-analyzer", "scripts")
    if _ia_scripts not in sys.path:
        sys.path.insert(0, _ia_scripts)
    import intraday as _intraday_engine
    INTRADAY_MOOD_AVAILABLE = True
except Exception as _ia_e:
    INTRADAY_MOOD_AVAILABLE = False
    sys.stderr.write(f"[intraday_mood] module load failed: {_ia_e}\n")

# ── Individual-stock 急拉/急殺 fast lane (Alpaca 1-min; separate lane) ────────
# Polls Alpaca 1-min bars for the spike_watchlist every 60s during market hours.
# Graceful no-op without ALPACA_API_KEY/SECRET. Read-only exploration layer.
INTRADAY_SPIKES_INTERVAL_SEC = int(os.getenv("INTRADAY_SPIKES_INTERVAL_SEC", "60"))
INTRADAY_SPIKES_OUTPUT = os.path.join(DASHBOARD_DIR, "intraday_spikes.json")
_intraday_spikes_state = {"last_poll": None, "last_error": None, "count": None}
_intraday_spikes_lock = threading.Lock()
try:
    import intraday_spikes as _spikes_engine   # same _ia_scripts dir already on sys.path
    INTRADAY_SPIKES_AVAILABLE = True
except Exception as _sp_e:
    INTRADAY_SPIKES_AVAILABLE = False
    sys.stderr.write(f"[intraday_spikes] module load failed: {_sp_e}\n")

# ── Intraday Evaluation hub (盤中策略) ───────────────────────────────────────
# ONE worker consolidates every intraday artifact in
# docs/STOCK_DATA_FETCH_INVENTORY.md (reads the JSON the other daemons already
# produce — ZERO extra API calls), evaluates a regime + strategy cards (0-LLM),
# tracks strategy recurrence (streak / day-count) for the UI effects, and adds
# an optional change-gated LLM briefing. Exploration layer — never feeds
# investment_protocol. Runs every 10 min during US market hours.
INTRADAY_EVAL_INTERVAL_SEC = int(os.getenv("INTRADAY_EVAL_INTERVAL_SEC", "600"))
INTRADAY_EVAL_OUTPUT = os.path.join(DASHBOARD_DIR, "intraday_eval.json")
INTRADAY_EVAL_USE_LLM = os.getenv("INTRADAY_EVAL_USE_LLM", "1") != "0"
_intraday_eval_state = {"last_poll": None, "last_error": None, "last_regime": None}
_intraday_eval_lock = threading.Lock()
try:
    sys.path.insert(0, ROOT)
    from scripts.intraday_eval import engine as _eval_engine
    from scripts.intraday_eval import load_history as _eval_load_history
    INTRADAY_EVAL_AVAILABLE = True
except Exception as _ie_e:
    INTRADAY_EVAL_AVAILABLE = False
    sys.stderr.write(f"[intraday_eval] module load failed: {_ie_e}\n")

try:
    sys.path.insert(0, ROOT)
    from scripts.break_news import store as _bn_store
    from scripts.break_news import poller as _bn_poller
    from scripts.break_news import debater as _bn_debater
    from scripts.break_news import trend_rollup as _bn_trend
    from scripts.break_news import cluster as _bn_cluster
    from scripts.break_news import market_brief as _bn_brief
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

# ── AI Office (V3.39 — autonomous multi-agent collaboration) ─────────────
# scripts/office/. A team of role-pinned CLI agents (Lead=claude / Critic=gemini
# / Verifier=codex) collaborates on a task to completion via model_router (daily
# budgets + cooldown + fallback), reusing the same `-p` drivers Break News runs
# — no new billing surface. Turns stream to the UI as structured events (SSE).
# Security: 127.0.0.1 bind (already) + per-process session token + Origin allowlist.
import hmac
import secrets as _secrets
from urllib.parse import parse_qs, unquote

try:
    from scripts.office import orchestrator as _office_orch
    from scripts.office import store as _office_store
    OFFICE_AVAILABLE = True
except Exception as _office_e:  # noqa: BLE001
    OFFICE_AVAILABLE = False
    sys.stderr.write(f"[office] module load failed: {_office_e}\n")

# ── Industry constituents (radar drill-down — full list via finvizfinance) ──
# industry_trend has no constituent lists; heatmap covers only large caps. This
# scrapes the full finviz industry membership (incl. small/mid caps) on demand,
# behind a long TTL cache since industry membership rarely changes intraday.
INDUSTRY_CACHE_TTL_SEC = int(os.getenv("INDUSTRY_CACHE_TTL_SEC", str(12 * 3600)))
_industry_cache = {}                 # industry_lower -> {"ts": float, "data": dict}
_industry_cache_lock = threading.Lock()
_INDUSTRY_NAME_RE = re.compile(r"^[A-Za-z0-9 &/\-.,'()]{1,80}$")


def _fetch_industry_constituents(name):
    """Full ticker list for a finviz industry via finvizfinance Screener.
    Returns {industry, count, tickers:[{ticker,company,sector,market_cap}], ...}
    or {error}. No API key required (public finviz scrape)."""
    try:
        from finvizfinance.screener.overview import Overview
    except Exception as e:  # noqa: BLE001
        return {"error": f"finvizfinance unavailable: {e}"}
    try:
        ov = Overview()
        ov.set_filter(filters_dict={"Industry": name})
        df = ov.screener_view(limit=300, verbose=0)
    except Exception as e:  # noqa: BLE001
        return {"error": f"finviz fetch failed: {str(e)[:200]}"}
    rows = []
    if df is not None and len(df):
        for _, r in df.iterrows():
            tk = str(r.get("Ticker") or "").strip()
            if not tk:
                continue
            rows.append({
                "ticker": tk,
                "company": str(r.get("Company") or "")[:80],
                "sector": str(r.get("Sector") or ""),
                "market_cap": str(r.get("Market Cap") or ""),
            })
    return {"industry": name, "count": len(rows), "tickers": rows,
            "source": "finviz",
            "as_of": datetime.now().isoformat(timespec="seconds")}

# Only one autonomous run at a time (it fans out to 3 CLIs per round).
_office_run_lock = threading.Lock()

# Per-process secret minted at boot. The same-origin office page fetches it via
# GET /api/office/token (Origin-gated); every other office call must present it.
_OFFICE_TOKEN = _secrets.token_urlsafe(32)
_OFFICE_ALLOWED_ORIGINS = {
    f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}",
}


def _office_token_ok(token):
    return bool(token) and hmac.compare_digest(str(token), _OFFICE_TOKEN)


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
        # Market brief — TTL-gated inside (1 LLM call per BRIEF_INTERVAL_SEC,
        # default 2h); piggybacks on this loop so no extra thread.
        try:
            _bn_brief.maybe_generate()
        except Exception as e:
            sys.stderr.write(f"[break_news] market brief error: {e}\n")
        if _shutdown.wait(BREAK_NEWS_INTERVAL_SEC):
            return


def _intraday_mood_refresh(reason):
    """Rebuild intraday_mood.json once; record state. Never raises."""
    try:
        payload = _intraday_engine.build()
        _intraday_engine._write_atomic(INTRADAY_MOOD_OUTPUT, payload)
        with _intraday_mood_lock:
            _intraday_mood_state["last_poll"] = datetime.now().isoformat(timespec="seconds")
            _intraday_mood_state["last_error"] = None
            _intraday_mood_state["last_score"] = (payload.get("aggregate") or {}).get("score")
    except Exception as e:
        with _intraday_mood_lock:
            _intraday_mood_state["last_error"] = str(e)[:300]
        sys.stderr.write(f"[intraday_mood] refresh error ({reason}): {e}\n")


def intraday_mood_poll_loop():
    """Refresh intraday_mood.json every INTRADAY_MOOD_INTERVAL_SEC while the US
    market is open, plus one snapshot at boot and one per weekday after the close
    so the panel reflects the final session overnight instead of going stale."""
    if not INTRADAY_MOOD_AVAILABLE:
        return
    if _shutdown.wait(15):
        return
    _intraday_mood_refresh("startup")
    last_close_snapshot = None
    while not _shutdown.wait(INTRADAY_MOOD_INTERVAL_SEC):
        if _is_us_market_hours():
            _intraday_mood_refresh("intraday")
        else:
            now_et = datetime.now(_HEATMAP_ET)
            today = now_et.date().isoformat()
            if now_et.weekday() < 5 and now_et.hour >= 16 and last_close_snapshot != today:
                _intraday_mood_refresh("post-close")
                last_close_snapshot = today


def _intraday_spikes_refresh(reason):
    """Rebuild intraday_spikes.json once; record state. Never raises."""
    try:
        payload = _spikes_engine.build()
        _spikes_engine._write_atomic(INTRADAY_SPIKES_OUTPUT, payload)
        with _intraday_spikes_lock:
            _intraday_spikes_state["last_poll"] = datetime.now().isoformat(timespec="seconds")
            _intraday_spikes_state["last_error"] = None
            _intraday_spikes_state["count"] = len(payload.get("spikes", []))
    except Exception as e:
        with _intraday_spikes_lock:
            _intraday_spikes_state["last_error"] = str(e)[:300]
        sys.stderr.write(f"[intraday_spikes] refresh error ({reason}): {e}\n")


def intraday_spikes_poll_loop():
    """Poll Alpaca 1-min bars for the watchlist every INTRADAY_SPIKES_INTERVAL_SEC
    (default 60s) during US market hours. One boot snapshot so the panel isn't
    blank; otherwise idle outside market hours (spikes are intraday-only)."""
    if not INTRADAY_SPIKES_AVAILABLE:
        return
    if _shutdown.wait(20):
        return
    _intraday_spikes_refresh("startup")
    while not _shutdown.wait(INTRADAY_SPIKES_INTERVAL_SEC):
        if _is_us_market_hours():
            _intraday_spikes_refresh("intraday")


def _intraday_eval_refresh(reason):
    """Rebuild intraday_eval.json once (consolidate → evaluate → streaks →
    optional LLM briefing). Records state; never raises."""
    try:
        payload = _eval_engine.build(with_narration=INTRADAY_EVAL_USE_LLM)
        _eval_engine._write_atomic(INTRADAY_EVAL_OUTPUT, payload)
        with _intraday_eval_lock:
            _intraday_eval_state["last_poll"] = datetime.now().isoformat(timespec="seconds")
            _intraday_eval_state["last_error"] = None
            _intraday_eval_state["last_regime"] = (payload.get("regime") or {}).get("label")
    except Exception as e:
        with _intraday_eval_lock:
            _intraday_eval_state["last_error"] = str(e)[:300]
        sys.stderr.write(f"[intraday_eval] refresh error ({reason}): {e}\n")


def intraday_eval_poll_loop():
    """Refresh intraday_eval.json every INTRADAY_EVAL_INTERVAL_SEC (default 600s)
    while the US market is open, plus one boot snapshot and one post-close
    snapshot per weekday so the panel doesn't go stale overnight."""
    if not INTRADAY_EVAL_AVAILABLE:
        return
    if _shutdown.wait(30):   # after the other intraday daemons have produced files
        return
    _intraday_eval_refresh("startup")
    last_close_snapshot = None
    while not _shutdown.wait(INTRADAY_EVAL_INTERVAL_SEC):
        if _is_us_market_hours():
            _intraday_eval_refresh("intraday")
        else:
            now_et = datetime.now(_HEATMAP_ET)
            today = now_et.date().isoformat()
            if now_et.weekday() < 5 and now_et.hour >= 16 and last_close_snapshot != today:
                _intraday_eval_refresh("post-close")
                last_close_snapshot = today


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


# ── Reports Center (V3.26.0) ─────────────────────────────────────────────
# Read-only browser over reports/*.md (262+ files spanning ic_memo, earnings,
# sector_report, news_digest, news_flash, pre_earnings, weekly variants, etc).
# Used by /reports.html — does NOT touch decision/skill layer.
REPORTS_DIR = os.path.join(ROOT, "reports")
_REPORTS_FILENAME_RE = re.compile(r"^[A-Za-z0-9_\-.]+\.md$")
_REPORTS_DATE_RE = re.compile(r"^(\d{4}-?\d{2}-?\d{2})(?:[_-]|$)")
_REPORTS_TICKER_RE = re.compile(r"_([A-Z]{1,5})_")
_REPORT_TYPE_RULES = [
    # (regex matched against filename, type key, label_zh, label_en)
    (re.compile(r"_ic_memo\.md$"),                  "ic_memo",      "IC Memo",      "IC Memo"),
    (re.compile(r"pre[_-]?earnings", re.I),         "pre_earnings", "財報前瞻",     "Pre-Earnings"),
    (re.compile(r"_earnings\.md$"),                 "earnings",     "財報分析",     "Earnings"),
    (re.compile(r"_sector_report\.md$"),            "sector",       "產業掃描",     "Sector"),
    (re.compile(r"_news_digest\.md$"),              "news_digest",  "新聞 Digest",  "News Digest"),
    (re.compile(r"_news_flash\.md$"),               "news_flash",   "新聞 Flash",   "News Flash"),
    (re.compile(r"_link_digest\.md$"),              "link_digest",  "連結分析",     "Link Digest"),
    (re.compile(r"^SHORT_TERM_WEEKLY"),             "weekly_short", "短期週報",     "Short-term Weekly"),
    (re.compile(r"^WEEKLY"),                        "weekly",       "週報",         "Weekly"),
    # V4.6 — 產出閉環: previously editor-only outputs surfaced in reports browser
    (re.compile(r"^SHADOW_REPORT"),                 "shadow",       "影子實驗",     "Shadow"),
    (re.compile(r"^PREMARKET_"),                    "premarket",    "盤前簡報",     "Pre-Market"),
    (re.compile(r"^POSTMORTEM_", re.I),             "postmortem",   "回測覆盤",     "Postmortem"),
    (re.compile(r"^decision_review/REVIEW_"),       "llm_review",   "決策檢討",     "LLM Review"),
    (re.compile(r"^decision_review/ADJUSTMENT_LEDGER\.md$"),
                                                    "ledger",       "調整 Ledger",  "Adj. Ledger"),
    (re.compile(r"SENTIMENT_PHASE2"),               "sentiment",    "情緒分析",     "Sentiment"),
    (re.compile(r"_valuation", re.I),               "valuation",    "估值專題",     "Valuation"),
    (re.compile(r"theme_(detector|report)"),        "theme",        "主題報告",     "Theme"),
    # YYYYMMDD_TICKER.md  or  YYYY-MM-DD_TICKER.md — V5.0 deep-dive reports.
    # Match must be exact end-of-name to avoid catching e.g. _earnings/_ic_memo.
    (re.compile(r"^\d{4}-?\d{2}-?\d{2}_[A-Z]{1,5}\.md$"),
                                                    "deep_dive",    "個股深度",     "Deep Dive"),
]
_REPORTS_CACHE = {"ts": 0.0, "dir_mtime": 0.0, "items": None, "counts": None}
_REPORTS_CACHE_TTL_SEC = 60


def _classify_report(filename: str) -> dict:
    for rx, tkey, zh, en in _REPORT_TYPE_RULES:
        if rx.search(filename):
            type_key, label_zh, label_en = tkey, zh, en
            break
    else:
        type_key, label_zh, label_en = "other", "其他", "Other"

    # date/ticker parsed from basename (filename may carry a subdir, e.g. decision_review/)
    base = filename.rsplit("/", 1)[-1]
    m_date = _REPORTS_DATE_RE.match(base)
    if not m_date:                              # REVIEW_/SHADOW_REPORT_<date> style (date after prefix)
        m_date = re.search(r"(\d{4}-\d{2}-\d{2})", base)
    date_str = ""
    if m_date:
        raw = m_date.group(1)
        if len(raw) == 8:                       # YYYYMMDD
            date_str = f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
        else:
            date_str = raw                      # YYYY-MM-DD

    ticker = ""
    m_tk = _REPORTS_TICKER_RE.search("_" + base)
    if m_tk:
        cand = m_tk.group(1)
        # Drop common non-ticker tokens that look uppercase
        if cand not in {"IC", "FY", "MD", "ET", "US"}:
            ticker = cand

    return {
        "filename": filename,
        "type": type_key,
        "label_zh": label_zh,
        "label_en": label_en,
        "date": date_str,
        "ticker": ticker,
    }


# V4.6 — decision_review/ sub-dir: only the human-facing outputs (REVIEW_<date> +
# ADJUSTMENT_LEDGER), not PROMPT/TODO/SCHEMA scaffolding or event_index machine files.
_DECISION_REVIEW_FILE_RE = re.compile(r"^(REVIEW_\d{4}-\d{2}-\d{2}|ADJUSTMENT_LEDGER)\.md$")


def _list_reports_cached() -> tuple:
    """Returns (items, counts). Caches 60s, invalidated when reports/ mtime changes."""
    now = time.time()
    dr_dir = os.path.join(REPORTS_DIR, "decision_review")
    try:
        dir_mtime = os.path.getmtime(REPORTS_DIR)
    except OSError:
        return ([], {})
    try:
        dir_mtime = max(dir_mtime, os.path.getmtime(dr_dir))
    except OSError:
        pass
    if (_REPORTS_CACHE["items"] is not None
            and now - _REPORTS_CACHE["ts"] < _REPORTS_CACHE_TTL_SEC
            and _REPORTS_CACHE["dir_mtime"] == dir_mtime):
        return (_REPORTS_CACHE["items"], _REPORTS_CACHE["counts"])

    rel_names = []
    try:
        rel_names += [n for n in os.listdir(REPORTS_DIR)
                      if n.endswith(".md") and _REPORTS_FILENAME_RE.match(n)]
    except OSError:
        pass
    try:
        rel_names += [f"decision_review/{n}" for n in os.listdir(dr_dir)
                      if _DECISION_REVIEW_FILE_RE.match(n)]
    except OSError:
        pass

    items = []
    counts = {}
    for name in rel_names:
        full = os.path.join(REPORTS_DIR, name)
        if not os.path.isfile(full):
            continue
        try:
            st = os.stat(full)
        except OSError:
            continue
        meta = _classify_report(name)
        meta["size_kb"] = round(st.st_size / 1024.0, 1)
        meta["mtime"] = int(st.st_mtime)
        # V4.6 — key-line summary for the surfaced ops/review outputs
        if meta["type"] in ("shadow", "premarket", "postmortem", "llm_review", "ledger", "weekly_short"):
            meta["summary"] = " · ".join(
                _extract_report_summary(full, meta["type"], meta["mtime"])[:2])
        items.append(meta)
        counts[meta["type"]] = counts.get(meta["type"], 0) + 1

    # Sort: by date (desc) when present, else by mtime (desc). Same-key tiebreak by filename.
    items.sort(key=lambda x: (x["date"] or "", x["mtime"], x["filename"]), reverse=True)

    _REPORTS_CACHE["ts"] = now
    _REPORTS_CACHE["dir_mtime"] = dir_mtime
    _REPORTS_CACHE["items"] = items
    _REPORTS_CACHE["counts"] = counts
    return (items, counts)


# ── V4.6 — Adjustment Ledger parser (read-only; writes stay with llm_review/human) ──
_LEDGER_CACHE = {"mtime": 0.0, "data": None}


def adjustment_ledger():
    """Parse reports/decision_review/ADJUSTMENT_LEDGER.md → structured entries."""
    path = os.path.join(REPORTS_DIR, "decision_review", "ADJUSTMENT_LEDGER.md")
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return {"entries": [], "active": 0, "error": "ADJUSTMENT_LEDGER.md not found"}
    if _LEDGER_CACHE["data"] is not None and _LEDGER_CACHE["mtime"] == mtime:
        return _LEDGER_CACHE["data"]
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError as e:
        return {"entries": [], "active": 0, "error": str(e)}

    entries = []
    for b in re.split(r"\n## ", text)[1:]:
        title = b.splitlines()[0].strip()

        def field(name, _b=b):
            m = re.search(rf"- \*\*{name}\*\*:\s*(.+)", _b)
            return m.group(1).strip() if m else ""

        tm = field("target_metric")
        if not tm:
            m = re.search(r"- \*\*target_metric\*\*:\s*\n((?:\s+- .+\n?)+)", b)
            if m:
                tm = "; ".join(ln.strip().lstrip("- ").strip()
                               for ln in m.group(1).splitlines() if ln.strip())
        latest_eval = ""
        m = re.search(r"- \*\*evaluation_history\*\*:\s*\n((?:\s+- .+\n?)+)", b)
        if m:
            evals = [ln.strip().lstrip("- ").strip()
                     for ln in m.group(1).splitlines() if ln.strip()]
            if evals:
                latest_eval = evals[-1]
        entries.append({
            "title": title,
            "applied_date": field("applied_date"),
            "status": field("status") or "unknown",
            "target_metric": tm[:400],
            "latest_eval": latest_eval[:400],
        })

    data = {"generated_at": int(time.time()), "entries": entries,
            "active": sum(1 for e in entries if e["status"] == "active")}
    _LEDGER_CACHE.update({"mtime": mtime, "data": data})
    return data


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

    # ── Office helpers (security) ─────────────────────────────────────────
    def _office_origin_ok(self):
        """Reject cross-origin callers. Absent Origin (same-origin navigation /
        non-browser) is allowed; a present Origin must be in the allowlist."""
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        return origin in _OFFICE_ALLOWED_ORIGINS

    def _office_guard(self, need_token=True):
        """Returns None if the request may proceed, else an (code, body) the
        caller should hand to _json. Token may arrive as an X-Office-Token
        header or a ?token= query param (EventSource can't set headers)."""
        if not OFFICE_AVAILABLE:
            return 503, {"error": "office module not loaded"}
        if not self._office_origin_ok():
            return 403, {"error": "bad origin"}
        if need_token:
            tok = self.headers.get("X-Office-Token")
            if tok is None:
                qs = parse_qs(urlparse(self.path).query)
                tok = (qs.get("token") or [None])[0]
            if not _office_token_ok(tok):
                return 403, {"error": "bad token"}
        return None

    def _office_sse_stream(self, run_id):
        """Tail a run's event log as Server-Sent Events until it terminates.
        Replays from seq 0 so a late/refreshed client gets the full history."""
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
        except OSError:
            return
        since = 0
        idle = 0
        while not _shutdown.is_set():
            events = _office_store.load_events(run_id, since=since)
            for ev in events:
                since = ev.get("seq", since) + 1
                try:
                    self.wfile.write(
                        f"data: {json.dumps(ev, ensure_ascii=False)}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except OSError:
                    return
            meta = _office_store.load_meta(run_id)
            terminal = meta and meta.get("status") in ("done", "stopped", "failed")
            if terminal and not events:
                # Flush a final sentinel and close.
                try:
                    self.wfile.write(b"event: end\ndata: {}\n\n")
                    self.wfile.flush()
                except OSError:
                    pass
                return
            if not events:
                idle += 1
                if idle % 15 == 0:  # ~15s keepalive comment
                    try:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                    except OSError:
                        return
                time.sleep(1.0)
            else:
                idle = 0

    def do_GET(self):
        path = urlparse(self.path).path

        # ── V4.63.0 quant-backtest read-only artifacts ───────────────────
        if path == "/api/backtest/list":
            data_dir = os.path.join(ROOT, "skills", "quant-backtest", "data")
            items = []
            if os.path.isdir(data_dir):
                for fn in sorted(os.listdir(data_dir)):
                    if not fn.endswith(".json"):
                        continue
                    try:
                        with open(os.path.join(data_dir, fn), encoding="utf-8") as f:
                            d = json.load(f)
                        if not d.get("ticker"):
                            continue  # strategy_rank.json 等非回測 artifact
                        items.append({
                            "ticker": d.get("ticker"), "template": d.get("template"),
                            "template_label": d.get("template_label"),
                            "period": d.get("period"), "params": d.get("params"),
                            "generated_at": d.get("generated_at"),
                            "metrics": d.get("metrics"), "degraded": d.get("degraded"),
                        })
                    except Exception:
                        continue
            items.sort(key=lambda x: x.get("generated_at") or "", reverse=True)
            return self._json(200, {"results": items})

        # V4.63.0 — 策略模板基準排名 (rank_strategies.py 產出, 卡片 badge 用)
        if path == "/api/backtest/strategies":
            fp = os.path.join(ROOT, "skills", "quant-backtest", "data",
                              "strategy_rank.json")
            if not os.path.exists(fp):
                return self._json(404, {"error": "strategy_rank.json not generated; "
                                        "run rank_strategies.py"})
            try:
                with open(fp, encoding="utf-8") as f:
                    return self._json(200, json.load(f))
            except Exception as e:
                return self._json(500, {"error": str(e)})

        if path == "/api/backtest/result":
            qs = parse_qs(urlparse(self.path).query)
            ticker = (qs.get("ticker", [""])[0]).strip().upper()
            template = (qs.get("template", ["momentum"])[0]).strip()
            if not re.match(r"^[A-Z][A-Z0-9.\-]{0,8}$", ticker) \
                    or template not in QUANT_BACKTEST_TEMPLATES:
                return self._json(400, {"error": "invalid ticker/template"})
            fp = os.path.join(ROOT, "skills", "quant-backtest", "data",
                              f"{ticker}_{template}.json")
            if not os.path.exists(fp):
                return self._json(404, {"error": f"no result for {ticker}/{template}"})
            try:
                with open(fp, encoding="utf-8") as f:
                    return self._json(200, json.load(f))
            except Exception as e:
                return self._json(500, {"error": str(e)})

        # ── Industry constituents (radar drill-down full list) ──────────
        if path.startswith("/api/industry/"):
            name = unquote(path[len("/api/industry/"):]).strip()
            if not _INDUSTRY_NAME_RE.match(name):
                return self._json(400, {"error": "bad industry name"})
            key = name.lower()
            now = time.time()
            with _industry_cache_lock:
                ent = _industry_cache.get(key)
                if ent and now - ent["ts"] < INDUSTRY_CACHE_TTL_SEC:
                    return self._json(200, {**ent["data"], "cached": True})
            data = _fetch_industry_constituents(name)
            if data.get("error"):
                return self._json(502, data)
            with _industry_cache_lock:
                _industry_cache[key] = {"ts": now, "data": data}
            return self._json(200, {**data, "cached": False})

        # ── AI Office (autonomous multi-agent collaboration) ────────────
        if path == "/api/office/token":
            # Origin-gated token mint (no token needed to fetch the token).
            guard = self._office_guard(need_token=False)
            if guard:
                return self._json(*guard)
            return self._json(200, {"token": _OFFICE_TOKEN})
        if path == "/api/office/runs":
            guard = self._office_guard()
            if guard:
                return self._json(*guard)
            return self._json(200, {"runs": _office_store.list_runs(),
                                    "active": _office_store.active_run()})
        if path.startswith("/api/office/run/"):
            guard = self._office_guard()
            if guard:
                return self._json(*guard)
            tail = path[len("/api/office/run/"):]
            stream = tail.endswith("/stream")
            run_id = tail[:-len("/stream")] if stream else tail
            meta = _office_store.load_meta(run_id)
            if meta is None:
                return self._json(404, {"error": "run not found"})
            if stream:
                return self._office_sse_stream(run_id)
            return self._json(200, {
                "meta": meta,
                "events": _office_store.load_events(run_id),
                "deliverable": _office_store.load_deliverable(run_id),
            })

        if path == "/api/positions":
            return self._json(200, load_positions())
        if path == "/api/ops/scripts":
            # V3.47.0 — Script 工具箱：registry + artifact-mtime 推斷 last run + 到期判定
            return self._json(200, ops_scripts_status())
        if path == "/api/today":
            # V4.6 — Today 工作台：due actions + 最新產出 feed + 晨報 digest
            return self._json(200, today_digest())
        if path == "/api/adjustment-ledger":
            # V4.6 — 產出閉環：ADJUSTMENT_LEDGER.md 結構化（唯讀）
            return self._json(200, adjustment_ledger())
        if path == "/api/llm-config":
            # Full governance config + live per-model usage/status.
            if MODEL_ROUTER_AVAILABLE:
                try:
                    cfg = _mrouter.load_llm_config()
                    return self._json(200, {**cfg,
                                            "status": _annotate_plans(_mrouter.model_status())})
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
        if path == "/api/x-kol/heat":
            qs = parse_qs(urlparse(self.path).query)
            want_prices = (qs.get("prices", ["1"])[0] or "1") not in ("0", "false", "no")
            try:
                return self._json(200, _x_kol_heat_payload(with_prices=want_prices))
            except Exception as e:
                return self._json(500, {"error": f"x-kol heat failed: {e}"})

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
        if path == "/api/break-news/stale-pending":
            if not BREAK_NEWS_AVAILABLE:
                return self._json(503, {"error": "break_news module not loaded"})
            try:
                items = _bn_debater.list_stale_pending()
            except AttributeError:
                items = []
            except Exception as e:
                return self._json(500, {"error": str(e)[:200]})
            return self._json(200, {"items": items, "count": len(items)})
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
        if path == "/api/intraday-mood/data":
            try:
                with open(INTRADAY_MOOD_OUTPUT, "r", encoding="utf-8") as f:
                    return self._json(200, json.load(f))
            except FileNotFoundError:
                return self._json(404, {"error": "intraday_mood.json not generated yet"})
            except Exception as e:
                return self._json(500, {"error": str(e)[:200]})
        if path == "/api/intraday-mood/state":
            with _intraday_mood_lock:
                live = dict(_intraday_mood_state)
            return self._json(200, {"live": live, "interval_sec": INTRADAY_MOOD_INTERVAL_SEC,
                                    "available": INTRADAY_MOOD_AVAILABLE})
        if path == "/api/intraday-spikes/data":
            try:
                with open(INTRADAY_SPIKES_OUTPUT, "r", encoding="utf-8") as f:
                    return self._json(200, json.load(f))
            except FileNotFoundError:
                return self._json(404, {"error": "intraday_spikes.json not generated yet",
                                        "available": INTRADAY_SPIKES_AVAILABLE})
            except Exception as e:
                return self._json(500, {"error": str(e)[:200]})
        if path == "/api/intraday-spikes/watchlist":
            if not INTRADAY_SPIKES_AVAILABLE:
                return self._json(503, {"error": "intraday_spikes module not loaded"})
            try:
                return self._json(200, {"watchlist": _spikes_engine.load_watchlist()})
            except Exception as e:
                return self._json(500, {"error": str(e)[:200]})
        if path == "/api/intraday-eval/data":
            try:
                with open(INTRADAY_EVAL_OUTPUT, "r", encoding="utf-8") as f:
                    return self._json(200, json.load(f))
            except FileNotFoundError:
                return self._json(404, {"error": "intraday_eval.json not generated yet",
                                        "available": INTRADAY_EVAL_AVAILABLE})
            except Exception as e:
                return self._json(500, {"error": str(e)[:200]})
        if path == "/api/intraday-eval/history":
            if not INTRADAY_EVAL_AVAILABLE:
                return self._json(503, {"error": "intraday_eval module not loaded"})
            qs = parse_qs(urlparse(self.path).query)
            date_arg = (qs.get("date") or [None])[0]
            try:
                return self._json(200, _eval_load_history(date_arg))
            except Exception as e:
                return self._json(500, {"error": str(e)[:200]})
        if path == "/api/intraday-eval/state":
            with _intraday_eval_lock:
                live = dict(_intraday_eval_state)
            return self._json(200, {"live": live, "interval_sec": INTRADAY_EVAL_INTERVAL_SEC,
                                    "available": INTRADAY_EVAL_AVAILABLE,
                                    "use_llm": INTRADAY_EVAL_USE_LLM})
        if path == "/api/break-news/brief":
            if not BREAK_NEWS_AVAILABLE:
                return self._json(503, {"error": "break_news module not loaded"})
            try:
                data = _bn_brief.load_brief()
            except Exception as e:
                return self._json(500, {"error": str(e)[:200]})
            payload = {
                "current": data.get("current"),
                "history_count": len(data.get("history") or []),
                "interval_sec": _bn_brief.BRIEF_INTERVAL_SEC,
            }
            if "history=1" in (urlparse(self.path).query or ""):
                payload["history"] = data.get("history") or []
            return self._json(200, payload)
        if path == "/api/break-news/clusters":
            if not BREAK_NEWS_AVAILABLE:
                return self._json(503, {"error": "break_news module not loaded"})
            qs = urlparse(self.path).query
            params = dict(kv.split("=", 1) for kv in qs.split("&") if "=" in kv)
            try:
                hours = max(1.0, min(float(params.get("hours", "24")), 72.0))
            except ValueError:
                hours = 24.0
            try:
                min_echo = max(1, min(int(params.get("min_echo", "2")), 50))
            except ValueError:
                min_echo = 2
            try:
                items = _bn_cluster.cluster_feed(hours=hours, min_echo=min_echo)
            except Exception as e:
                return self._json(500, {"error": str(e)[:200]})
            return self._json(200, {"clusters": items, "count": len(items),
                                    "hours": hours, "min_echo": min_echo})
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

        # V3.26.0 — Reports Center: list reports/*.md classified by type
        if path == "/api/reports":
            items, counts = _list_reports_cached()
            return self._json(200, {"reports": items, "counts": counts, "total": len(items)})

        # V3.26.0 — Reports Center: serve a single reports/*.md (whitelist + no traversal)
        if path.startswith("/api/reports/view/"):
            rel = unquote(path[len("/api/reports/view/"):])
            # V4.6 — explicit decision_review/ branch; base regex still rejects "/" and "..".
            if rel.startswith("decision_review/"):
                tail = rel[len("decision_review/"):]
                if not _DECISION_REVIEW_FILE_RE.match(tail):
                    self.send_error(400, "bad filename")
                    return
            elif not _REPORTS_FILENAME_RE.match(rel):
                self.send_error(400, "bad filename")
                return
            full = os.path.join(REPORTS_DIR, rel)
            if not os.path.isfile(full):
                self.send_error(404, "not found")
                return
            try:
                with open(full, "rb") as f:
                    body = f.read()
            except OSError as e:
                self.send_error(500, f"read error: {e}")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return

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

        # ── X KOL promotion gate ────────────────────────────────────────
        # Records a human decision. Deliberately does NOT launch 分析 — the
        # exploration layer never triggers the decision layer (CLAUDE.md global
        # discipline); it only puts the ticker on a list the user then acts on.
        if path == "/api/x-kol/decide":
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception as e:
                return self._json(400, {"error": f"invalid JSON: {e}"})
            ticker = str(body.get("ticker") or "").strip().upper().lstrip("$")
            decision = str(body.get("decision") or "").strip()
            if not ticker or not re.fullmatch(r"[A-Z0-9.\-]{1,12}", ticker):
                return self._json(400, {"error": "bad ticker"})
            try:
                from scripts.x_kol import heat as _xheat
                entry = _xheat.decide(_x_kol_candidates_path(), ticker, decision,
                                      note=(body.get("note") or None))
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            except Exception as e:
                return self._json(500, {"error": f"decide failed: {e}"})
            _X_KOL_CACHE["at"] = 0.0          # queue changed; next GET re-reads
            return self._json(200, {"ticker": ticker, "entry": entry})

        # ── AI Office (autonomous multi-agent collaboration) ────────────
        if path == "/api/office/run":
            guard = self._office_guard()
            if guard:
                return self._json(*guard)
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception as e:
                return self._json(400, {"error": f"invalid JSON: {e}"})
            task = (body.get("task") or "").strip()
            if not task:
                return self._json(400, {"error": "missing 'task'"})
            if len(task) > 8000:
                return self._json(400, {"error": "task too long (max 8000 chars)"})
            with _office_run_lock:
                if _office_store.active_run():
                    return self._json(409, {"error": "a run is already in progress",
                                            "active": _office_store.active_run()})
                try:
                    max_rounds = int(body.get("max_rounds") or _office_orch.MAX_ROUNDS)
                except (TypeError, ValueError):
                    max_rounds = _office_orch.MAX_ROUNDS
                max_rounds = max(1, min(max_rounds, 6))
                meta = _office_orch.start_run(task, max_rounds=max_rounds)
            return self._json(202, meta)
        if path.startswith("/api/office/run/") and path.endswith("/stop"):
            guard = self._office_guard()
            if guard:
                return self._json(*guard)
            run_id = path[len("/api/office/run/"):-len("/stop")]
            if _office_store.load_meta(run_id) is None:
                return self._json(404, {"error": "run not found"})
            stopped = _office_orch.request_stop(run_id)
            return self._json(202, {"run_id": run_id, "stop_requested": stopped})

        if path == "/api/llm-config":
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception as e:
                return self._json(400, {"error": f"invalid JSON: {e}"})
            valid = {"claude", "gemini", "codex", "grok"}
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

        if path == "/api/intraday-mood/refresh":
            if not INTRADAY_MOOD_AVAILABLE:
                return self._json(503, {"error": "intraday_mood module not loaded"})
            # ~6 FMP calls (few seconds) — run in background; UI polls GET /data.
            threading.Thread(target=lambda: _intraday_mood_refresh("manual"),
                             daemon=True, name="intraday-mood-refresh").start()
            return self._json(202, {"status": "refreshing"})

        if path == "/api/intraday-eval/refresh":
            if not INTRADAY_EVAL_AVAILABLE:
                return self._json(503, {"error": "intraday_eval module not loaded"})
            # Reads existing snapshots (no API calls) + optional 1 LLM briefing.
            threading.Thread(target=lambda: _intraday_eval_refresh("manual"),
                             daemon=True, name="intraday-eval-refresh").start()
            return self._json(202, {"status": "refreshing"})

        if path == "/api/intraday-spikes/watchlist":
            if not INTRADAY_SPIKES_AVAILABLE:
                return self._json(503, {"error": "intraday_spikes module not loaded"})
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception as e:
                return self._json(400, {"error": f"invalid JSON: {e}"})
            tickers = body.get("tickers")
            if not isinstance(tickers, list):
                return self._json(400, {"error": "missing 'tickers' (list)"})
            try:
                saved = _spikes_engine.save_watchlist(tickers)
            except ValueError as e:
                return self._json(400, {"error": str(e)[:200]})
            except Exception as e:
                return self._json(500, {"error": str(e)[:200]})
            # Rebuild immediately so the UI reflects the new list on its next poll.
            threading.Thread(target=lambda: _intraday_spikes_refresh("watchlist-edit"),
                             daemon=True, name="intraday-spikes-refresh").start()
            return self._json(200, {"watchlist": saved, "status": "saved"})

        if path == "/api/break-news/brief/refresh":
            if not BREAK_NEWS_AVAILABLE:
                return self._json(503, {"error": "break_news module not loaded"})
            # 1 LLM call (~30-60s) — run in background; UI polls GET /brief.
            threading.Thread(
                target=lambda: _bn_brief.generate(force=True),
                daemon=True, name="bn-brief-refresh",
            ).start()
            return self._json(202, {"status": "generating"})

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
            state, err = enqueue_protocol(
                "supply_chain_generate",
                {"theme": theme, "rerun": bool(body.get("rerun"))},
                source="supply_chain",
            )
            if err == "duplicate":
                return self._json(409, state)
            if err:
                return self._json(400, {"error": err})
            return self._json(202, state)
        if path.startswith("/api/supply-chain/") and path.endswith("/override"):
            # V4.45.0 — user node correction sidecar. Writes nexus/supply_chains/
            # overrides/<slug>.json; never rewrites the LLM-drafted YAML. enrich()
            # merges it at serve time (corrected fields win, like a manual edit).
            if not SUPPLY_CHAIN_AVAILABLE:
                return self._json(503, {"error": "supply_chain module not loaded"})
            slug = path[len("/api/supply-chain/"):-len("/override")]
            if not _sc_slug_re.match(slug):
                return self._json(400, {"error": "invalid slug"})
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception as e:
                return self._json(400, {"error": f"invalid JSON: {e}"})
            node_id = str(body.get("node_id") or "").strip()
            chain = _sc.load(slug)
            if chain is None:
                return self._json(404, {"error": "chain not found"})
            if node_id not in {str(n.get("id")) for n in chain.get("nodes") or []}:
                return self._json(400, {"error": "unknown node_id"})
            try:
                _sc.save_override(
                    slug, node_id,
                    status=body.get("status"),
                    fields=body.get("fields") if isinstance(body.get("fields"), dict) else None,
                    note=body.get("note"),
                )
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            _sc_cache.pop(slug, None)  # force re-enrich on next GET
            return self._json(200, {"status": "ok", "slug": slug, "node_id": node_id})
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

        if path.startswith("/api/break-news/item/") and path.endswith("/debate-now"):
            # Manual single-item debate. Bypasses scan_and_debate (which honors
            # PENDING_MAX_AGE_HOURS), so user can spend LLM budget on a stale
            # backlog item explicitly.
            tail = path[len("/api/break-news/item/"):-len("/debate-now")]
            if not _BREAK_NEWS_ID_RE.match(tail):
                return self._json(400, {"error": "invalid news_id"})
            if not BREAK_NEWS_AVAILABLE:
                return self._json(503, {"error": "break_news module not loaded"})
            d = _bn_store.load_item(tail)
            if d is None:
                return self._json(404, {"error": "not found"})
            if d.get("state") not in ("pending_debate", "partial_closed", "failed"):
                return self._json(409, {"error": "item not eligible",
                                        "state": d.get("state")})

            def _run_single(nid=tail):
                try:
                    with _break_news_dispatch_lock:
                        _bn_debater.debate_item(nid, verbose=False)
                    with _break_news_lock:
                        _break_news_state["last_debate_scan"] = \
                            datetime.now().isoformat(timespec="seconds")
                except Exception as ex:
                    with _break_news_lock:
                        _break_news_state["last_error"] = str(ex)[:300]
                    sys.stderr.write(f"[break_news] debate-now {nid} error: {ex}\n")

            threading.Thread(target=_run_single, daemon=True).start()
            return self._json(202, {"news_id": tail, "state": "debating"})

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
    # V4.6 — 節奏自動化: due 的 auto:true registry scripts 自動跑（0-LLM 白名單）
    threading.Thread(target=ops_auto_loop, daemon=True, name="ops_auto").start()

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

    # Intraday market-weakness engine (FMP intraday + daily, market-hours gated)
    if INTRADAY_MOOD_AVAILABLE:
        threading.Thread(target=intraday_mood_poll_loop, daemon=True,
                         name="intraday_mood_poll").start()
        print(f"Intraday Mood:      poll every {INTRADAY_MOOD_INTERVAL_SEC}s "
              f"(FMP intraday, US market hours + post-close)")
    else:
        sys.stderr.write("[intraday_mood] disabled (module not loaded)\n")

    # Individual-stock 急拉/急殺 fast lane (Alpaca 1-min, market-hours gated)
    if INTRADAY_SPIKES_AVAILABLE:
        threading.Thread(target=intraday_spikes_poll_loop, daemon=True,
                         name="intraday_spikes_poll").start()
        _sp_keyed = bool(os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY"))
        print(f"Intraday Spikes:    poll every {INTRADAY_SPIKES_INTERVAL_SEC}s "
              f"(Alpaca 1-min, {'IEX feed' if _sp_keyed else 'NO KEY — set ALPACA_API_KEY/SECRET'})")
    else:
        sys.stderr.write("[intraday_spikes] disabled (module not loaded)\n")

    # Intraday Evaluation hub (盤中策略) — consolidates all intraday artifacts,
    # evaluates strategy cards + recurrence, market-hours gated.
    if INTRADAY_EVAL_AVAILABLE:
        threading.Thread(target=intraday_eval_poll_loop, daemon=True,
                         name="intraday_eval_poll").start()
        print(f"Intraday Eval:      poll every {INTRADAY_EVAL_INTERVAL_SEC}s "
              f"(hub: consolidate + strategy cards, {'LLM briefing' if INTRADAY_EVAL_USE_LLM else '0-LLM'}, "
              f"US market hours + post-close)")
    else:
        sys.stderr.write("[intraday_eval] disabled (module not loaded)\n")

    if OFFICE_AVAILABLE:
        print("AI Office:          autonomous team at /office.html "
              "(Lead=claude / Critic=gemini / Verifier=codex; token + Origin gated)")
    else:
        sys.stderr.write("[office] disabled (module not loaded)\n")

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nshutdown")
        _shutdown.set()
        srv.server_close()
