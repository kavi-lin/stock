#!/usr/bin/env python3
"""Every argparse `help=` literal in the repo must survive add_argument().

    python3 tests/test_argparse_help_strings.py
    python3 -m pytest -q tests/test_argparse_help_strings.py

WHY THIS EXISTS. Python 3.14 moved help-string validation from render time to
`add_argument()` time (`argparse._check_help`). A bare `%` in a help string used
to fail only when someone actually ran `--help`; on 3.14 it raises ValueError at
parser-construction time, which for a CLI script means it dies on startup.

Real breakage, 2026-08-16: `sector/market_top_yfinance.py` had
`help="% S&P 500 above 50DMA ..."`. After Homebrew moved the default python3 to
3.14, step 3 of daily_update.sh died with `ValueError: badly formed help string`.
Phase 1 is fatal, so the whole daily_update.sh exited rc=1 and the pre-market
chain showed only "exited rc=1" with no cause. Two characters, whole pipeline.

The fix is `%%`, which argparse still renders as a single `%`.

This scans literals rather than importing modules on purpose: importing every
CLI in the repo would execute module-level code and need every third-party
dependency present, which is a much heavier and flakier check than the one bug
class it is guarding.
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOTS = ("scripts", "skills", "investment", "news", "sector", "nexus", "tests", "Dashboard")
SKIP = ("/archive/", "/__pycache__/", "/reference/", "/vendor/", "/.claude/", "/node_modules/")

# %% is the escape; %(name)s is a legitimate argparse conversion.
_ESCAPE = re.compile(r"%%")
_CONVERSION = re.compile(r"%\([a-zA-Z_]+\)[sdrfgi]")


def _leftover_percent(text: str) -> bool:
    probe = _CONVERSION.sub("", _ESCAPE.sub("", text))
    return "%" in probe


def iter_help_literals():
    """Yield (path, lineno, help_string) for every constant help= in the repo."""
    for root in ROOTS:
        base = ROOT / root
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            rel = str(path.relative_to(ROOT))
            if any(s.strip("/") in rel.split("/") for s in ("archive", "__pycache__", "reference", "vendor")):
                continue
            if any(s in f"/{rel}" for s in SKIP):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call)
                        and getattr(node.func, "attr", None) == "add_argument"):
                    continue
                for kw in node.keywords:
                    if kw.arg == "help" and isinstance(kw.value, ast.Constant) \
                            and isinstance(kw.value.value, str):
                        yield rel, node.lineno, kw.value.value


def test_no_bare_percent_in_help_strings():
    offenders = [(f, ln, h) for f, ln, h in iter_help_literals() if _leftover_percent(h)]
    assert not offenders, (
        "argparse help strings with a bare '%' die at add_argument() on Python 3.14+. "
        "Use '%%' (argparse renders it as a single '%'):\n"
        + "\n".join(f"  {f}:{ln}  {h!r}" for f, ln, h in offenders)
    )


def test_the_rule_this_guards_is_real():
    """Pin the actual interpreter behaviour, so the guard cannot outlive its reason.

    If a future Python stops rejecting a bare %, this fails and tells whoever is
    reading that the scan above is now enforcing a rule the runtime dropped.
    """
    # Built at runtime, not written as a literal: the scan above walks the AST
    # for constant help= strings and would otherwise flag this deliberate
    # fixture. Assembling it keeps the scan free of path exclusions, which are
    # how a guard quietly stops covering the file it lives next to.
    bare = "%" + " of S&P 500 above 50DMA"
    parser = argparse.ArgumentParser()
    try:
        parser.add_argument("--bare", help=bare)
    except ValueError:
        rejected = True
    else:
        rejected = False
    assert rejected or sys.version_info < (3, 14), (
        f"Python {sys.version.split()[0]} accepted a bare '%' in a help string; "
        "test_no_bare_percent_in_help_strings is now stricter than the runtime."
    )
    # The escape must keep working regardless, and must still render as one '%'.
    escaped = argparse.ArgumentParser(prog="t")
    escaped.add_argument("--escaped", help="%" * 2 + " of S&P 500 above 50DMA")
    assert "% of S&P 500 above 50DMA" in escaped.format_help()


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    for fn in TESTS:
        fn()
    total = sum(1 for _ in iter_help_literals())
    print(f"argparse help-string tests: OK ({len(TESTS)} cases, {total} help literals scanned)")
