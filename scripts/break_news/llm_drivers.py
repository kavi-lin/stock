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
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CLAUDE_BIN = os.environ.get("CLAUDE_BIN") or "/Users/kavi/.local/bin/claude"
GEMINI_BIN = os.environ.get("GEMINI_BIN") or "/usr/local/bin/gemini"
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
    if rc == 0 and out:
        try:
            envelope = json.loads(out)
            text = envelope.get("result") or ""
        except json.JSONDecodeError:
            # Some claude CLI runs prefix lines (e.g. login banner); try the last
            # JSON-looking line.
            for line in reversed(out.splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        envelope = json.loads(line)
                        text = envelope.get("result") or ""
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
    )


def run_gemini(system_prompt: str, user_prompt: str,
               timeout: int = LLM_TIMEOUT_SEC) -> LLMResult:
    # Gemini CLI does not have --append-system-prompt — we concatenate.
    full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
    cmd = [
        GEMINI_BIN, "-p", full_prompt,
        "--output-format", "json",
        "--approval-mode", "plan",
        "-m", GEMINI_MODEL,
    ]
    rc, out, err, latency, error = _run_cli(cmd, timeout)
    text = ""
    if rc == 0 and out:
        # Gemini sometimes prints non-JSON banner lines ("Ripgrep is not
        # available..."). Find the first '{' that begins a valid object.
        start = out.find("{")
        if start >= 0:
            try:
                envelope = json.loads(out[start:])
                text = envelope.get("response") or ""
            except json.JSONDecodeError:
                # Try last JSON-looking blob (sometimes 2 are emitted).
                m = re.findall(r"\{.*?\"response\".*?\}", out, re.DOTALL)
                if m:
                    try:
                        envelope = json.loads(m[-1])
                        text = envelope.get("response") or ""
                    except json.JSONDecodeError:
                        pass
    parsed, status = _extract_json(text or out)
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

    `codex exec --json` emits JSONL events; the final assistant text is in the
    last `item.completed` event whose item has `type=agent_message`.
    """
    full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
    cmd = [
        CODEX_BIN, "exec",
        "--json",
        "-C", str(ROOT),
        "--sandbox", "read-only",
        "--skip-git-repo-check",
        "--ephemeral",
        "--color", "never",
        full_prompt,
    ]
    rc, out, err, latency, error = _run_cli(cmd, timeout)
    text = ""
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
            if (
                event.get("type") == "item.completed"
                and isinstance(item, dict)
                and item.get("type") == "agent_message"
            ):
                text = item.get("text") or text
    parsed, status = _extract_json(text or out)
    return LLMResult(
        agent="codex",
        parsed=parsed,
        raw_text=text,
        raw_stdout=out,
        exit_code=rc,
        latency_ms=latency,
        parse_status=status,
        error=error or (err[:300] if rc != 0 and err else None),
    )


# ── model registry + config ───────────────────────────────────────────────
_RUNNERS = {"claude": run_claude, "gemini": run_gemini, "codex": run_codex}
VALID_MODELS = tuple(_RUNNERS)

# Full governance config. Old `{primary,secondary}` files still parse — missing
# keys are filled from these defaults. `tertiary` extends the fallback chain;
# `enabled` / `budgets` / `cooldown_hours` drive the model_router governor.
_DEFAULT_CONFIG = {
    "primary":   "claude",
    "secondary": "gemini",
    "tertiary":  "codex",
    "enabled":   {"claude": True, "gemini": True, "codex": True},
    "budgets":   {"claude": {"daily_max_calls": 200},
                  "gemini": {"daily_max_calls": 500},
                  "codex":  {"daily_max_calls": 200}},
    "cooldown_hours": 4,
    # Break News debate uses its OWN two-model pair, independent of the general
    # primary/secondary above — so the Claude×Gemini divergence can be tuned
    # without affecting supply-chain / protocol routing.
    "break_news": {"primary": "claude", "secondary": "gemini"},
}


def run_llm(model: str, system_prompt: str, user_prompt: str,
            timeout: int = LLM_TIMEOUT_SEC) -> LLMResult:
    """Dispatch to a model runner by name. Unknown name → claude."""
    runner = _RUNNERS.get((model or "").lower().strip(), run_claude)
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
    return chain or ["claude"]


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
