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
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CLAUDE_BIN = os.environ.get("CLAUDE_BIN") or "/Users/kavi/.local/bin/claude"
AGY_BIN = os.environ.get("AGY_BIN") or "agy"
CODEX_BIN = os.environ.get("CODEX_BIN") or "/usr/local/bin/codex"
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
    """Scan a claude `--output-format stream-json` protocol log and return the
    token usage from its terminal `result` event. {} when none found.

    Used by the dashboard protocol runner (sector / news / invest) to attribute
    per-run tokens to the model that produced them."""
    last_result = None
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
                if isinstance(ev, dict) and ev.get("type") == "result":
                    last_result = ev
    except OSError:
        return {}
    return _usage_from_envelope(last_result) if last_result else {}


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


def _run_cli(cmd: list[str], timeout: int) -> tuple[int, str, str, int, str | None]:
    """Returns (rc, stdout, stderr, latency_ms, error)."""
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            check=False,
        )
        latency = int((time.time() - t0) * 1000)
        return proc.returncode, proc.stdout or "", proc.stderr or "", latency, None
    except subprocess.TimeoutExpired:
        latency = int((time.time() - t0) * 1000)
        return -1, "", "", latency, f"timeout after {timeout}s"
    except FileNotFoundError as e:
        return -2, "", "", 0, f"binary not found: {e}"
    except OSError as e:
        return -3, "", "", 0, f"os error: {e}"


def run_claude(system_prompt: str, user_prompt: str,
               timeout: int = LLM_TIMEOUT_SEC) -> LLMResult:
    cmd = [
        CLAUDE_BIN, "-p", user_prompt,
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",
        "--append-system-prompt", system_prompt,
    ]
    rc, out, err, latency, error = _run_cli(cmd, timeout)
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
               timeout: int = LLM_TIMEOUT_SEC) -> LLMResult:
    # agy CLI uses --print/-p and --dangerously-skip-permissions.
    full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
    cmd = [
        AGY_BIN, "--print", full_prompt,
        "--dangerously-skip-permissions",
    ]
    rc, out, err, latency, error = _run_cli(cmd, timeout)
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
              timeout: int = LLM_TIMEOUT_SEC) -> LLMResult:
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
    rc, out, err, latency, error = _run_cli(cmd, timeout)
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


# ── model registry + config ───────────────────────────────────────────────
_RUNNERS = {"claude": run_claude, "gemini": run_gemini, "codex": run_codex}
VALID_MODELS = tuple(_RUNNERS)

# Full governance config. Old `{primary,secondary}` files still parse — missing
# keys are filled from these defaults. `tertiary` extends the fallback chain;
# `enabled` / `budgets` / `cooldown_hours` drive the model_router governor.
_DEFAULT_CONFIG = {
    "primary":   "gemini",
    "secondary": "codex",
    "tertiary":  "claude",
    "enabled":   {"claude": True, "gemini": True, "codex": True},
    "budgets":   {"claude": {"daily_max_calls": 200},
                  "gemini": {"daily_max_calls": 500},
                  "codex":  {"daily_max_calls": 200}},
    "cooldown_hours": 4,
    # Break News debate uses its OWN two-model pair, independent of the general
    # primary/secondary above — so the Claude×Gemini divergence can be tuned
    # without affecting supply-chain / protocol routing.
    "break_news": {"primary": "gemini", "secondary": "codex"},
}


def run_llm(model: str, system_prompt: str, user_prompt: str,
            timeout: int = LLM_TIMEOUT_SEC) -> LLMResult:
    """Dispatch to a model runner by name. Unknown name → gemini."""
    runner = _RUNNERS.get((model or "").lower().strip(), run_gemini)
    return runner(system_prompt, user_prompt, timeout=timeout)


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
            if isinstance(mb, dict) and "daily_max_calls" in mb:
                try:
                    cfg["budgets"][m]["daily_max_calls"] = max(0, int(mb["daily_max_calls"]))
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
    return cfg


def break_news_pair() -> list[str]:
    """The two Break-News debaters [primary, secondary] — its own config
    section, independent of the general primary/secondary chain."""
    cfg = load_llm_config()
    bn = cfg.get("break_news") or {}
    pair = [bn.get("primary"), bn.get("secondary")]
    return pair if all(m in _RUNNERS for m in pair) else ["gemini", "codex"]


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
    """Quick smoke test. Returns 0 on success."""
    sys_p = ("Reply with a SINGLE fenced ```json``` block matching: "
             "{\"x\":int, \"ok\":bool}. No prose outside the block.")
    usr_p = "Probe. Return x=4, ok=true."
    if agent not in _RUNNERS:
        print(f"unknown agent: {agent}", file=sys.stderr)
        return 2
    r = run_llm(agent, sys_p, usr_p, timeout=120)
    print(f"agent={r.agent} rc={r.exit_code} latency_ms={r.latency_ms} "
          f"parse_status={r.parse_status} error={r.error}")
    print(f"raw_text={r.raw_text[:200]!r}")
    print(f"parsed={r.parsed}")
    return 0 if (r.exit_code == 0 and r.parsed) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--agent", choices=list(VALID_MODELS), required=True)
    args = ap.parse_args()
    if args.probe:
        return probe(args.agent)
    print("nothing to do", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
