"""Subprocess wrappers for the Claude and Gemini CLIs.

Both binaries are run with `--output-format json`. The envelope shape differs:
  - Claude envelope:  `{"result": "<text>", ...}`
  - Gemini envelope:  `{"response": "<text>", ...}`

We extract the inner text, then run a 3-stage JSON parser:
  1. ```json fenced block``` regex
  2. whole-string json.loads
  3. brace-balanced walk from first `{`

If all 3 fail we still surface the raw text so the calling debate loop can keep
going (the other agent may push the thread to close). The raw stdout is saved
to disk for forensic review.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CLAUDE_BIN = os.environ.get("CLAUDE_BIN") or "/Users/kavi/.local/bin/claude"
AGY_BIN = os.environ.get("AGY_BIN") or "agy"
CODEX_BIN = os.environ.get("CODEX_BIN") or "/usr/local/bin/codex"
GROK_BIN = os.environ.get("GROK_BIN") or "/Users/kavi/.grok/bin/grok"
GEMINI_MODEL = os.environ.get("BREAK_NEWS_GEMINI_MODEL", "gemini-2.5-flash-lite")
LLM_TIMEOUT_SEC = int(os.environ.get("BREAK_NEWS_LLM_TIMEOUT_SEC", "180"))

# Server-side LLM config — which CLI is primary (generation) vs secondary
# (debate / review). Python scripts read this; the dashboard writes it via
# POST /api/llm-config. localStorage cannot be used — scripts are not browsers.
CONFIG_FILE = ROOT / "config" / "llm_config.json"

FENCED_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


@dataclass
class LLMResult:
    agent: str
    parsed: dict | None     # the extracted JSON object, or None on total failure
    raw_text: str           # inner text from CLI envelope
    raw_stdout: str         # the entire stdout (including envelope)
    exit_code: int
    latency_ms: int
    parse_status: str       # ok | fallback | failed
    error: str | None       # error message if exit_code != 0 / timeout / etc.
    # Token accounting (best-effort; 0 when the CLI envelope omits usage).
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0


def _usage_from_envelope(envelope: dict) -> dict:
    """Pull token counts + cost out of a claude `--output-format json` envelope
    (or any dict carrying a `usage` block). Missing keys → 0."""
    if not isinstance(envelope, dict):
        return {}
    u = envelope.get("usage") or {}
    if not isinstance(u, dict):
        u = {}
    return {
        "input_tokens": int(u.get("input_tokens", 0) or 0),
        "output_tokens": int(u.get("output_tokens", 0) or 0),
        "cache_read_tokens": int(u.get("cache_read_input_tokens", 0) or 0),
        "cache_write_tokens": int(u.get("cache_creation_input_tokens", 0) or 0),
        "cost_usd": float(envelope.get("total_cost_usd", 0.0) or 0.0),
    }


def parse_stream_log_usage(log_path: str) -> dict:
    """Scan a provider JSONL protocol log and return terminal token usage.

    Claude reports a ``result`` envelope; Codex reports ``turn.completed`` with
    ``cached_input_tokens``; Agy reports ``{"event": "result", "result": {...}}``
    — payload nested under a key named after the event, not at the top level.
    Returns {} when no terminal event is present.

    The Agy branch arrived in V4.109.1. Until the quota broker started assigning
    providers, the protocol always ran on the configured chain default (claude),
    so this path had never executed once — and the first governed run the broker
    routed to Agy settled with zero tokens. That same nesting caught the broker
    out in its own Agy adapter during its Phase 5 live testing; the shape here is
    taken from the fixture that fix produced.

    Used by the dashboard protocol runner (sector / news / invest) to attribute
    per-run tokens to the model that produced them."""
    last_result = None
    last_codex_usage = None
    last_agy_usage = None
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(ev, dict):
                    continue
                if ev.get("type") == "result":
                    last_result = ev
                elif ev.get("type") == "turn.completed":
                    usage = ev.get("usage")
                    if isinstance(usage, dict):
                        last_codex_usage = usage
                elif ev.get("event") == "result":
                    payload = ev.get("result")
                    usage = payload.get("usage") if isinstance(payload, dict) else None
                    if isinstance(usage, dict):
                        last_agy_usage = usage
    except OSError:
        return {}
    if last_result:
        return _usage_from_envelope(last_result)
    if last_codex_usage:
        return {
            "input_tokens": int(last_codex_usage.get("input_tokens", 0) or 0),
            "output_tokens": int(last_codex_usage.get("output_tokens", 0) or 0),
            "cache_read_tokens": int(last_codex_usage.get("cached_input_tokens", 0) or 0),
            "cache_write_tokens": 0,
            "cost_usd": 0.0,
        }
    if last_agy_usage:
        # `thinking_tokens` is a subset of Agy's output count, so it is not added
        # in — the broker's TokenUsage keeps the two apart for the same reason.
        return {
            "input_tokens": int(last_agy_usage.get("input_tokens", 0) or 0),
            "output_tokens": int(last_agy_usage.get("output_tokens", 0) or 0),
            "cache_read_tokens": int(last_agy_usage.get("cache_read_tokens", 0) or 0),
            "cache_write_tokens": 0,
            "cost_usd": 0.0,
        }
    return {}


def _extract_json(text: str) -> tuple[dict | None, str]:
    """Return (parsed_dict, status). status ∈ {ok, fallback, failed}."""
    if not text:
        return None, "failed"
    m = FENCED_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1)), "ok"
        except json.JSONDecodeError:
            pass
    stripped = text.strip()
    try:
        return json.loads(stripped), "ok"
    except json.JSONDecodeError:
        pass
    start = stripped.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(stripped)):
            ch = stripped[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = stripped[start:i + 1]
                    try:
                        return json.loads(candidate), "fallback"
                    except json.JSONDecodeError:
                        break
    return None, "failed"


def _run_cli(
    cmd: list[str],
    timeout: int,
    process_callback: Callable[[int, int], None] | None = None,
) -> tuple[int, str, str, int, str | None]:
    """Returns (rc, stdout, stderr, latency_ms, error)."""
    t0 = time.time()
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        if process_callback is not None:
            try:
                process_callback(proc.pid, os.getpgid(proc.pid))
            except Exception as exc:
                try:
                    os.killpg(os.getpgid(proc.pid), 15)
                    proc.wait(timeout=5)
                except (ProcessLookupError, PermissionError, OSError,
                        subprocess.TimeoutExpired):
                    try:
                        os.killpg(os.getpgid(proc.pid), 9)
                    except (ProcessLookupError, PermissionError, OSError):
                        pass
                latency = int((time.time() - t0) * 1000)
                return -3, "", "", latency, f"broker process attach failed: {exc}"
        out, err = proc.communicate(timeout=timeout)
        latency = int((time.time() - t0) * 1000)
        return proc.returncode, out or "", err or "", latency, None
    except subprocess.TimeoutExpired as exc:
        if "proc" in locals():
            try:
                os.killpg(os.getpgid(proc.pid), 15)
                proc.wait(timeout=5)
            except (ProcessLookupError, PermissionError, OSError, subprocess.TimeoutExpired):
                try:
                    os.killpg(os.getpgid(proc.pid), 9)
                except (ProcessLookupError, PermissionError, OSError):
                    pass
        latency = int((time.time() - t0) * 1000)
        return -1, exc.stdout or "", exc.stderr or "", latency, f"timeout after {timeout}s"
    except FileNotFoundError as e:
        return -2, "", "", 0, f"binary not found: {e}"
    except OSError as e:
        return -3, "", "", 0, f"os error: {e}"


def run_claude(system_prompt: str, user_prompt: str,
               timeout: int = LLM_TIMEOUT_SEC,
               model: str | None = None,
               max_turns: int | None = None,
               strict_mcp: bool = False,
               no_tools: bool = False,
               process_callback: Callable[[int, int], None] | None = None) -> LLMResult:
    """`model` / `max_turns` / `strict_mcp` / `no_tools` let text-only callers
    (AI Office debate turns) pin a model and disable the agentic loop + MCP
    startup + built-in tools — a bare `claude -p` in this repo goes agentic on
    analysis prompts (WebSearch etc.) and either blows past the timeout or dies
    with error_max_turns. `no_tools` also REPLACES the built-in Claude Code
    system prompt (--system-prompt vs --append-system-prompt): with the default
    prompt present the model keeps hallucinating textual tool calls
    ("**Tool: read**") even when every tool is disabled. Defaults preserve
    Break News behavior."""
    cmd = [
        CLAUDE_BIN, "-p", user_prompt,
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",
        ("--system-prompt" if no_tools else "--append-system-prompt"),
        system_prompt,
    ]
    if model:
        cmd += ["--model", model]
    if max_turns is not None:
        cmd += ["--max-turns", str(max_turns)]
    if strict_mcp:
        cmd += ["--strict-mcp-config"]
    if no_tools:
        cmd += ["--tools", ""]
    rc, out, err, latency, error = _run_cli(cmd, timeout, process_callback)
    text = ""
    usage: dict = {}
    if rc == 0 and out:
        try:
            envelope = json.loads(out)
            text = envelope.get("result") or ""
            usage = _usage_from_envelope(envelope)
        except json.JSONDecodeError:
            # Some claude CLI runs prefix lines (e.g. login banner); try the last
            # JSON-looking line.
            for line in reversed(out.splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        envelope = json.loads(line)
                        text = envelope.get("result") or ""
                        usage = _usage_from_envelope(envelope)
                        break
                    except json.JSONDecodeError:
                        continue
    parsed, status = _extract_json(text or out)
    return LLMResult(
        agent="claude",
        parsed=parsed,
        raw_text=text,
        raw_stdout=out,
        exit_code=rc,
        latency_ms=latency,
        parse_status=status,
        error=error or (err[:300] if rc != 0 and err else None),
        **usage,
    )


def run_gemini(system_prompt: str, user_prompt: str,
               timeout: int = LLM_TIMEOUT_SEC, model: str = "",
               process_callback: Callable[[int, int], None] | None = None) -> LLMResult:
    # agy CLI uses --print/-p and --dangerously-skip-permissions.
    full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
    cmd = [
        AGY_BIN, "--print", full_prompt,
        "--dangerously-skip-permissions",
    ]
    # V4.129.0 — `model` is the quota broker's assigned model, and passing it is
    # what makes the reservation true. Agy meters its Gemini models and its
    # Claude/GPT models in two pools that refill independently; with no
    # `--model` the CLI uses whatever is selected in its own TUI, so a hold
    # taken against the Gemini pool could be spent out of the other one. Left
    # empty the old behaviour stands, which is what an ungoverned caller wants.
    if model:
        cmd += ["--model", model]
    rc, out, err, latency, error = _run_cli(cmd, timeout, process_callback)
    # agy --print returns the raw agent output directly (no JSON envelope
    # unless specifically requested, but we handle that in _extract_json).
    text = out.strip()
    parsed, status = _extract_json(text)
    return LLMResult(
        agent="gemini",
        parsed=parsed,
        raw_text=text,
        raw_stdout=out,
        exit_code=rc,
        latency_ms=latency,
        parse_status=status,
        error=error or (err[:300] if rc != 0 and err else None),
    )


def run_codex(system_prompt: str, user_prompt: str,
              timeout: int = LLM_TIMEOUT_SEC,
              process_callback: Callable[[int, int], None] | None = None) -> LLMResult:
    """Run Codex non-interactively and parse its JSONL event stream.

    `codex exec --json` emits JSONL events. Recent builds put the final
    assistant text in `item.completed.item.text`, while older / alternate
    builds may use content parts. `--output-last-message` is a second source
    of truth when the event stream shape changes.
    """
    full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
    tmp_path = ""
    try:
        fd, tmp_path = tempfile.mkstemp(prefix="break_news_codex_", suffix=".txt")
        os.close(fd)
    except OSError:
        tmp_path = ""
    cmd = [
        CODEX_BIN, "exec",
        "--json",
        "-C", str(ROOT),
        "--sandbox", "read-only",
        "--skip-git-repo-check",
        "--ephemeral",
        "--color", "never",
    ]
    if tmp_path:
        cmd.extend(["--output-last-message", tmp_path])
    cmd.append(full_prompt)
    rc, out, err, latency, error = _run_cli(cmd, timeout, process_callback)
    text = ""
    codex_error = ""
    if out:
        for line in out.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            item = event.get("item") if isinstance(event, dict) else None
            if event.get("type") == "error":
                codex_error = str(event.get("message") or codex_error)
            elif event.get("type") == "turn.failed":
                ev_err = event.get("error")
                if isinstance(ev_err, dict):
                    codex_error = str(ev_err.get("message") or codex_error)
            if (
                event.get("type") == "item.completed"
                and isinstance(item, dict)
                and item.get("type") == "agent_message"
            ):
                text = _codex_item_text(item) or text
    if not text and tmp_path:
        try:
            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read().strip()
        except OSError:
            pass
    if tmp_path:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    parsed, status = _extract_json(text or out)
    return LLMResult(
        agent="codex",
        parsed=parsed,
        raw_text=text,
        raw_stdout=out,
        exit_code=rc,
        latency_ms=latency,
        parse_status=status,
        error=error or codex_error or (err[:300] if rc != 0 and err else None),
    )


def _codex_item_text(item: dict) -> str:
    """Extract assistant text from known Codex JSONL item shapes."""
    text = item.get("text")
    if isinstance(text, str) and text.strip():
        return text
    content = item.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                val = part.get("text") or part.get("content")
                if isinstance(val, str):
                    parts.append(val)
        return "\n".join(p for p in parts if p)
    return ""


def run_grok(system_prompt: str, user_prompt: str,
             timeout: int = LLM_TIMEOUT_SEC,
             process_callback: Callable[[int, int], None] | None = None) -> LLMResult:
    """Run the Grok CLI single-turn (`grok -p ... --output-format json`).

    Envelope shape: `{"text": "<response>", "usage": {...}, ...}`. Web search
    and subagent spawning are disabled so a headless probe can't hang waiting
    on a permission prompt the CLI never surfaces in `-p` mode.
    """
    full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
    cmd = [
        GROK_BIN, "-p", full_prompt,
        "--output-format", "json",
        "--permission-mode", "dontAsk",
        "--disable-web-search",
        "--no-subagents",
    ]
    rc, out, err, latency, error = _run_cli(cmd, timeout, process_callback)
    text = ""
    usage: dict = {}
    if rc == 0 and out:
        try:
            envelope = json.loads(out)
            text = envelope.get("text") or ""
            usage = _usage_from_envelope(envelope)
        except json.JSONDecodeError:
            for line in reversed(out.splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        envelope = json.loads(line)
                        text = envelope.get("text") or ""
                        usage = _usage_from_envelope(envelope)
                        break
                    except json.JSONDecodeError:
                        continue
    parsed, status = _extract_json(text or out)
    return LLMResult(
        agent="grok",
        parsed=parsed,
        raw_text=text,
        raw_stdout=out,
        exit_code=rc,
        latency_ms=latency,
        parse_status=status,
        error=error or (err[:300] if rc != 0 and err else None),
        **usage,
    )


# ── model registry + config ───────────────────────────────────────────────
_RUNNERS = {"claude": run_claude, "gemini": run_gemini, "codex": run_codex, "grok": run_grok}
VALID_MODELS = tuple(_RUNNERS)

# Full governance config. Old `{primary,secondary}` files still parse — missing
# keys are filled from these defaults. `tertiary` extends the fallback chain;
# `enabled` / `budgets` / `cooldown_hours` drive the model_router governor.
_DEFAULT_CONFIG = {
    "primary":   "gemini",
    "secondary": "codex",
    "tertiary":  "claude",
    "enabled":   {"claude": True, "gemini": True, "codex": True, "grok": True},
    "budgets":   {"claude": {"daily_max_calls": 200},
                  "gemini": {"daily_max_calls": 500},
                  "codex":  {"daily_max_calls": 200},
                  "grok":   {"daily_max_calls": 100}},
    "cooldown_hours": 4,
    # Break News debate pair — since V4.109.0 this is the FALLBACK, used only
    # when the quota broker cannot answer or can name fewer than two providers
    # that are able to serve (`debater._turn_order`). It stays independent of
    # the general primary/secondary chain so the Claude×Gemini divergence
    # AGENTS.md calls a core signal can be tuned without touching
    # supply-chain / protocol routing.
    #
    # The value used to be `gemini` / `codex`, which never matched that stated
    # intent — nor the docstring of `break_news_pair`'s own caller, which has
    # always claimed a claude↔gemini fallback.
    "break_news": {"primary": "claude", "secondary": "gemini"},
    # V4.106.0 — quota broker. Empty here on purpose: `broker_gate.broker_config`
    # holds the defaults, and an absent block means "on with defaults" so a config
    # file written before Phase 7 does not silently opt out of governance.
    "broker": {},
    # V4.114.0 — per-protocol provider allowlist, read by
    # `model_router.protocol_provider_allowlist`. Empty here means unrestricted,
    # which is the pre-V4.114.0 behaviour: a config file that predates this key
    # keeps routing exactly as it did.
    "protocol_providers": {},
}


def run_llm(model: str, system_prompt: str, user_prompt: str,
            timeout: int = LLM_TIMEOUT_SEC, provider_model: str = "",
            process_callback: Callable[[int, int], None] | None = None) -> LLMResult:
    """Dispatch to a model runner by name. Unknown name → gemini.

    `provider_model` is the vendor-native model id the quota broker assigned
    (`gemini-3.6-flash-medium`), as distinct from `model`, which is this repo's
    runner name (`gemini`). Only the agy runner can act on it — it is the only
    provider here whose quota is split into pools that a model selects between
    — so it is passed on where it means something and dropped where it does not.
    """
    runner = _RUNNERS.get((model or "").lower().strip(), run_gemini)
    if provider_model and runner is run_gemini:
        return runner(
            system_prompt,
            user_prompt,
            timeout=timeout,
            model=provider_model,
            process_callback=process_callback,
        )
    return runner(
        system_prompt, user_prompt, timeout=timeout, process_callback=process_callback
    )


def _default_config() -> dict:
    import copy
    return copy.deepcopy(_DEFAULT_CONFIG)


def load_llm_config() -> dict:
    """Read config/llm_config.json → the full governance config dict.
    Backward compatible: an old `{primary,secondary}` file still parses; any
    missing key is filled from `_DEFAULT_CONFIG`. Unknown model names ignored."""
    cfg = _default_config()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return cfg
    if not isinstance(raw, dict):
        return cfg
    for key in ("primary", "secondary", "tertiary"):
        v = str(raw.get(key, "")).lower().strip()
        if v in _RUNNERS:
            cfg[key] = v
    en = raw.get("enabled")
    if isinstance(en, dict):
        for m in _RUNNERS:
            if m in en:
                cfg["enabled"][m] = bool(en[m])
    bg = raw.get("budgets")
    if isinstance(bg, dict):
        for m in _RUNNERS:
            mb = bg.get(m)
            if not isinstance(mb, dict):
                continue
            if "daily_max_calls" in mb:
                try:
                    cfg["budgets"][m]["daily_max_calls"] = max(0, int(mb["daily_max_calls"]))
                except (TypeError, ValueError):
                    pass
            # V4.84.0 — rolling-window budget (model_router._window_cfg reads these).
            # This loader whitelists keys rather than merging, so a new budget key that
            # is not named here is silently dropped and the cap never takes effect.
            if "window_max_calls" in mb:
                try:
                    cfg["budgets"][m]["window_max_calls"] = max(0, int(mb["window_max_calls"]))
                except (TypeError, ValueError):
                    pass
            if "window_hours" in mb:
                try:
                    wh = float(mb["window_hours"])
                    if wh > 0:
                        cfg["budgets"][m]["window_hours"] = wh
                except (TypeError, ValueError):
                    pass
    try:
        ch = float(raw.get("cooldown_hours", cfg["cooldown_hours"]))
        if ch > 0:
            cfg["cooldown_hours"] = ch
    except (TypeError, ValueError):
        pass
    bn = raw.get("break_news")
    if isinstance(bn, dict):
        for key in ("primary", "secondary"):
            v = str(bn.get(key, "")).lower().strip()
            if v in _RUNNERS:
                cfg["break_news"][key] = v
    # V4.106.0 — quota broker settings. Carried through whole rather than
    # key-whitelisted: `broker_gate.broker_config()` owns their defaults and
    # validation, and this loader silently dropping a key it had not been taught
    # about is exactly the trap noted above for the window budget.
    bk = raw.get("broker")
    if isinstance(bk, dict):
        cfg["broker"] = dict(bk)
    # V4.114.0 — per-protocol provider allowlist. Carried through whole for the
    # same reason as `broker`: its keys are protocol names, so there is no fixed
    # set to whitelist against, and `model_router.protocol_provider_allowlist`
    # owns the validation. Whitelisting here is what would silently drop it —
    # the trap the window-budget comment above already records once.
    pp = raw.get("protocol_providers")
    if isinstance(pp, dict):
        cfg["protocol_providers"] = dict(pp)
    return cfg


def break_news_pair() -> list[str]:
    """The configured Break-News debate pair [primary, secondary].

    Since V4.109.0 this is the *fallback* for `debater._turn_order()`, which
    normally takes the quota broker's live top two. The last-resort literal is
    claude↔gemini to match AGENTS.md and that caller's docstring; it used to be
    gemini↔codex, so a config file that failed validation silently produced a
    pair neither document described.
    """
    cfg = load_llm_config()
    bn = cfg.get("break_news") or {}
    pair = [bn.get("primary"), bn.get("secondary")]
    return pair if all(m in _RUNNERS for m in pair) else ["claude", "gemini"]


def model_chain(cfg: dict | None = None) -> list[str]:
    """Ordered fallback chain [primary, secondary, tertiary] — deduped."""
    cfg = cfg or load_llm_config()
    seen, chain = set(), []
    for key in ("primary", "secondary", "tertiary"):
        m = cfg.get(key)
        if m in _RUNNERS and m not in seen:
            seen.add(m)
            chain.append(m)
    return chain or ["gemini"]


def primary_model() -> str:
    return load_llm_config()["primary"]


def secondary_model() -> str:
    return load_llm_config()["secondary"]


def probe(agent: str) -> int:
    """Quick broker-pinned smoke test. Returns 0 on success."""
    sys_p = ("Reply with a SINGLE fenced ```json``` block matching: "
             "{\"x\":int, \"ok\":bool}. No prose outside the block.")
    usr_p = "Probe. Return x=4, ok=true."
    if agent not in _RUNNERS:
        print(f"unknown agent: {agent}", file=sys.stderr)
        return 2
    # Lazy import avoids the model_router -> llm_drivers import cycle at module
    # load time. The probe is not an escape hatch: it takes a real broker lease.
    from scripts._shared.model_router import run_with_fallback
    r = run_with_fallback(agent, "capability_probe", sys_p, usr_p, timeout=120)
    print(f"agent={r.agent} rc={r.exit_code} latency_ms={r.latency_ms} "
          f"parse_status={r.parse_status} error={r.error}")
    print(f"raw_text={r.raw_text[:200]!r}")
    print(f"parsed={r.parsed}")
    return 0 if (r.exit_code == 0 and r.parsed) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--agent", choices=["claude", "gemini", "codex"], required=True)
    args = ap.parse_args()
    if args.probe:
        return probe(args.agent)
    print("nothing to do", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
