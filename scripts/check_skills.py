#!/usr/bin/env python3
"""
check_skills.py — lenient cross-reference linter for skills/*/SKILL.md.

V2.14.0 — modeled on `reference/financial-services/scripts/check.py`. Lenient mode:
warnings only, rc=0 always. Designed to surface drift without blocking commits.

What it checks (per skill folder under `skills/`):

  1. SKILL.md exists.
  2. SKILL.md has YAML frontmatter (---\\n...\\n---) at top OR an opening H1 with
     a bolded `**Trigger**` / `**Version**` line (legacy project convention).
  3. Frontmatter has `name` (or H1 starts with skill folder name).
  4. Frontmatter / opening section has a `description` (or skill purpose 段落).
  5. `scripts/` subdirectory referenced in SKILL.md actually exists on disk.
  6. Each `python3 skills/<name>/scripts/<file.py>` invocation in SKILL.md
     points at a file that exists.
  7. `cache/` directory mentioned in SKILL.md exists (auto-created scripts may
     not have it yet — flag as info, not warn).
  8. SKILL.md doesn't reference removed sibling skills (cross-skill imports).

Output:
    [check_skills] scanning N skills...
    [<skill>] WARN: <reason>
    [<skill>] INFO: <reason>
    [check_skills] ✓ N skills, X warnings, Y info — see notes above

Invocation:
    python3 scripts/check_skills.py            # full project scan
    python3 scripts/check_skills.py --strict   # rc=1 on any WARN (CI mode)
    python3 scripts/check_skills.py --skill <name>   # single skill audit

Always rc=0 in default mode. Add `--strict` for blocking behaviour later.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"

# Findings tally
WARNINGS: list[tuple[str, str]] = []
INFOS: list[tuple[str, str]] = []


def warn(skill: str, msg: str) -> None:
    WARNINGS.append((skill, msg))
    print(f"[{skill}] WARN: {msg}")


def info(skill: str, msg: str) -> None:
    INFOS.append((skill, msg))
    print(f"[{skill}] INFO: {msg}")


def _read_skill_md(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        warn(path.parent.name, f"could not read SKILL.md: {e}")
        return None


_FM_SCAN_LIMIT = 4000  # YAML descriptions can be ~1KB+; widen scan window


def _has_frontmatter(text: str) -> bool:
    return text.startswith("---\n") and "\n---\n" in text[4:_FM_SCAN_LIMIT]


def _extract_frontmatter(text: str) -> dict:
    """Tiny YAML-ish parser — only handles `key: value` flat lines."""
    if not _has_frontmatter(text):
        return {}
    end = text.index("\n---\n", 4)
    body = text[4:end]
    out: dict[str, str] = {}
    for line in body.splitlines():
        if ":" in line and not line.startswith("#"):
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip().strip("'\"")
    return out


_LEGACY_HDR_RE = re.compile(r"^#\s+([\w-]+)\s*[—\-–]\s*(.+)$", re.MULTILINE)


def _legacy_header(text: str) -> tuple[str | None, str | None]:
    """Match legacy convention: `# skill-name — purpose`. Skip past frontmatter
    so that body H1s don't shadow it (and so frontmatter `name:` doesn't masquerade
    as a misnamed legacy header)."""
    body = text
    if _has_frontmatter(text):
        end = text.index("\n---\n", 4)
        body = text[end + 5:]
    m = _LEGACY_HDR_RE.search(body)
    return (m.group(1), m.group(2).strip()) if m else (None, None)


_PY_INVOKE_RE = re.compile(r"python3\s+(skills/[\w/.\-]+\.py)")


def _check_skill(skill_dir: Path) -> None:
    skill = skill_dir.name
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        warn(skill, "SKILL.md missing")
        return

    text = _read_skill_md(skill_md)
    if text is None:
        return

    # Check 1-4: frontmatter OR legacy header convention
    fm = _extract_frontmatter(text)
    legacy_name, legacy_desc = _legacy_header(text)

    if fm:
        if "name" not in fm:
            warn(skill, "frontmatter missing `name` key")
        elif fm["name"] != skill:
            warn(skill, f"frontmatter name='{fm['name']}' but folder='{skill}'")
        if "description" not in fm or len(fm.get("description", "")) < 20:
            warn(skill, "frontmatter `description` missing or < 20 chars (won't help auto-trigger)")
    elif legacy_name:
        if legacy_name != skill:
            info(skill, f"legacy H1 name='{legacy_name}' differs from folder='{skill}'")
        if not legacy_desc:
            warn(skill, "legacy H1 missing purpose suffix after `—`")
    else:
        warn(skill, "no YAML frontmatter and no legacy `# name — purpose` header")

    # Check 5-6: referenced script files exist
    invokes = _PY_INVOKE_RE.findall(text)
    seen: set[str] = set()
    for rel in invokes:
        if rel in seen:
            continue
        seen.add(rel)
        target = ROOT / rel
        if not target.exists():
            warn(skill, f"references missing script: `{rel}`")

    # Check 7: cache/ mention vs disk presence
    if "cache/" in text or "/cache/" in text:
        cache_dir = skill_dir / "cache"
        if not cache_dir.exists():
            info(skill, "SKILL.md mentions cache/ but skills/<name>/cache/ doesn't exist (auto-created OK)")

    # Check 8: cross-skill references (e.g. skills/foo/) — sibling skill must exist
    cross_refs = re.findall(r"skills/([a-z0-9_\-]+)/", text)
    for ref in set(cross_refs):
        if ref == skill:
            continue
        if not (SKILLS_DIR / ref).exists():
            warn(skill, f"references sibling `skills/{ref}/` which does not exist")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true",
                    help="rc=1 on any warning (default: always rc=0 lenient mode)")
    ap.add_argument("--skill", help="audit single skill folder name")
    args = ap.parse_args()

    if not SKILLS_DIR.exists():
        print(f"[check_skills] skills/ dir not found: {SKILLS_DIR}", file=sys.stderr)
        return 1

    if args.skill:
        target = SKILLS_DIR / args.skill
        if not target.is_dir():
            print(f"[check_skills] skill not found: {args.skill}", file=sys.stderr)
            return 1
        skills = [target]
    else:
        skills = sorted(p for p in SKILLS_DIR.iterdir()
                        if p.is_dir() and not p.name.startswith("_"))

    print(f"[check_skills] scanning {len(skills)} skills (lenient mode={'OFF' if args.strict else 'ON'})...")
    for s in skills:
        _check_skill(s)

    n_warn = len(WARNINGS)
    n_info = len(INFOS)
    print(f"\n[check_skills] ✓ scanned {len(skills)} skills, {n_warn} warnings, {n_info} info notes")

    if args.strict and n_warn > 0:
        print(f"[check_skills] strict mode: {n_warn} warnings → rc=1", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
