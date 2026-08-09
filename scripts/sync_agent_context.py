#!/usr/bin/env python3
"""Mirror CLAUDE.md's routing sections into the other providers' context files.

Why this exists
---------------
Every CLI in this repo auto-loads exactly one project context file, and until
V4.114.0 three of the four could not route a protocol from it:

    claude  → CLAUDE.md   auto-loaded, holds the trigger table.
    codex   → AGENTS.md   auto-loaded, but the table said "see CLAUDE.md".
    grok    → AGENTS.md   same file, same gap.
    gemini  → GEMINI.md   NOT auto-loaded at all by `agy --print`.

Probed 2026-08-09 from this repo's cwd with no tools allowed: codex answered
UNKNOWN to "which protocol file does 分析 TICKER read first", and agy answered
NONE to "which context files are loaded". The invest run that morning was the
consequence — it searched ~/Documents, ~/Stock and ~/.claude for a project it
was already sitting inside, then died having produced nothing.

So each provider's file has to carry the routing itself. Hand-copying three
tables is how they drift, which is exactly what CLAUDE.md's old "只引用不複製"
rule was protecting against. This script keeps CLAUDE.md as the single *written*
source and generates the rest, with `--check` for the session-close checklist.

Usage
-----
    python3 scripts/sync_agent_context.py            # rewrite the blocks
    python3 scripts/sync_agent_context.py --check    # rc=0 in sync, rc=1 stale
"""
from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = "CLAUDE.md"

#: Sections copied verbatim from CLAUDE.md, matched by `## ` heading prefix.
#: The set is "everything a non-Claude agent needs to work without opening
#: CLAUDE.md": where a trigger routes, which outputs are exploration-only and
#: must never reach a decision, which validator must return rc=0, and the
#: dev-session discipline. What stays behind is reference material an agent
#: reads on demand anyway (Output Paths, Ops, Shared Modules, 治理文件索引).
SECTIONS = ("Protocol Triggers", "自動層", "Validator Gates", "Workflow Rules")

BEGIN = "<!-- BEGIN generated from CLAUDE.md — do not edit by hand -->"
END = "<!-- END generated from CLAUDE.md -->"

#: Target file → the note printed above the generated block. Each says which CLI
#: reads the file, because "your own context file" is only actionable if the file
#: names itself.
TARGETS = {
    "GEMINI.md": (
        "> **本區塊由 `scripts/sync_agent_context.py` 從 `CLAUDE.md` 生成，不要手改。**\n"
        "> 本檔是 Antigravity (`agy`) 的 context 檔。實測 2026-08-09：`agy --print` "
        "**不會**自動載入本檔，所以 protocol prompt 會明確要求你先 Read 它。\n"
        "> 你只需要這一個 context 檔 —— 不必去讀 `CLAUDE.md` 或 `AGENTS.md`。"
    ),
    "AGENTS.md": (
        "> **本區塊由 `scripts/sync_agent_context.py` 從 `CLAUDE.md` 生成，不要手改。**\n"
        "> 本檔是 Codex 與 Grok 共用的 context 檔（兩者實測都會自動載入，2026-08-09）。\n"
        "> 你只需要這一個 context 檔 —— 不必去讀 `CLAUDE.md` 或 `GEMINI.md`。"
    ),
}


def read(path: str) -> str:
    with open(os.path.join(ROOT, path), "r", encoding="utf-8") as f:
        return f.read()


def extract_sections(src: str) -> str:
    """Pull each named `## ` section out of CLAUDE.md, heading included.

    A section runs to the next `## ` heading or EOF. A missing section is fatal
    rather than skipped: silently emitting a context file with no trigger table
    reproduces the exact bug this script was written for.
    """
    out = []
    for name in SECTIONS:
        m = re.search(
            r"^(## " + re.escape(name) + r".*?)(?=^## |\Z)",
            src, re.MULTILINE | re.DOTALL)
        if not m:
            sys.stderr.write(
                f"[sync_agent_context] section '## {name}' not found in {SOURCE}. "
                f"Either it was renamed — update SECTIONS — or it was deleted.\n")
            raise SystemExit(2)
        out.append(m.group(1).strip())
    return "\n\n".join(out)


def render_block(path: str, body: str) -> str:
    return f"{BEGIN}\n\n{TARGETS[path]}\n\n{body}\n\n{END}"


def splice(current: str, block: str) -> str:
    """Replace an existing generated block, or append one if absent."""
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)
    if pattern.search(current):
        return pattern.sub(lambda _: block, current, count=1)
    return current.rstrip("\n") + "\n\n" + block + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify only; rc=1 when a target is stale")
    args = ap.parse_args(argv)

    body = extract_sections(read(SOURCE))
    stale = []
    for path in TARGETS:
        current = read(path)
        updated = splice(current, render_block(path, body))
        if updated == current:
            print(f"  ok     {path}")
            continue
        stale.append(path)
        if args.check:
            print(f"  STALE  {path}")
        else:
            with open(os.path.join(ROOT, path), "w", encoding="utf-8") as f:
                f.write(updated)
            print(f"  wrote  {path}")

    if args.check and stale:
        print(f"\nDESYNC — {', '.join(stale)} 與 {SOURCE} 不一致。"
              f"跑 `python3 scripts/sync_agent_context.py` 重生成。")
        return 1
    print(f"\nCONTEXT SYNC OK — {SOURCE} → {', '.join(TARGETS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
