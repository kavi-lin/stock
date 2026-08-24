#!/usr/bin/env python3
"""Fail-closed static audit for the repository's LLM execution boundary."""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._shared import llm_task_registry  # noqa: E402

ROUTER_CALLS = {"run_role": 0, "run_with_fallback": 1, "governed_call": 0}
LOW_LEVEL_CALLS = {"run_llm", "run_claude", "run_gemini", "run_codex", "run_grok"}
LOW_LEVEL_ALLOW = {
    "scripts/_shared/model_router.py",
    "scripts/wind/reasoning_adapter.py",
    "scripts/break_news/llm_drivers.py",
}
LAUNCHER_ALLOW = {
    "dashboard_server.py",
    "investment/scripts/run_protocol_manual.py",
}
SKIP_PARTS = {".git", "node_modules", "__pycache__"}
SKIP_PREFIXES = ("config/office_claude/", "reference/", ".claude/", "archive/")


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _python_files() -> list[Path]:
    return [path for path in ROOT.rglob("*.py")
            if not any(part in SKIP_PARTS for part in path.parts)
            and not _rel(path).startswith(SKIP_PREFIXES)
            and "tests" not in path.parts]


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _protocol_names() -> set[str]:
    tree = ast.parse((ROOT / "dashboard_server.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "PROTOCOL_PROMPTS"
                for target in node.targets):
            if isinstance(node.value, ast.Dict):
                return {key.value for key in node.value.keys
                        if isinstance(key, ast.Constant) and isinstance(key.value, str)}
    return set()


def audit() -> list[str]:
    errors: list[str] = []
    registry = llm_task_registry.load_registry()
    tasks = set(registry["tasks"])
    official = set(llm_task_registry.official_models())

    cfg_path = ROOT / "config/llm_config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    if not (cfg.get("broker") or {}).get("enabled"):
        errors.append("config/llm_config.json: broker.enabled must be true")
    if (cfg.get("broker") or {}).get("degradable_roles"):
        errors.append("config/llm_config.json: degradable_roles must be empty")
    if (cfg.get("enabled") or {}).get("grok") is not False:
        errors.append("config/llm_config.json: Grok must remain disabled")
    if set(registry.get("official_models") or []) != {"claude", "gemini", "codex"}:
        errors.append("config/llm_task_registry.json: official_models must be Claude/Agy/Codex")

    for protocol in _protocol_names():
        task_id = llm_task_registry.protocol_task_id(protocol)
        if task_id not in tasks:
            errors.append(f"dashboard_server.py: protocol {protocol!r} lacks registry task {task_id}")

    for path in _python_files():
        rel = _rel(path)
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError) as exc:
            errors.append(f"{rel}: cannot audit Python AST: {exc}")
            continue
        sdk_ctor = "Anthropic" + "("
        sdk_import = "from anthropic" + " import"
        if rel not in LOW_LEVEL_ALLOW and (
                sdk_ctor in source or sdk_import in source):
            errors.append(f"{rel}: direct Anthropic SDK use is forbidden")
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node)
            if name in LOW_LEVEL_CALLS and rel not in LOW_LEVEL_ALLOW:
                errors.append(f"{rel}:{node.lineno}: low-level {name}() bypasses model_router")
            if name not in ROUTER_CALLS:
                continue
            index = ROUTER_CALLS[name]
            if len(node.args) <= index or not isinstance(node.args[index], ast.Constant):
                continue
            role = node.args[index].value
            if isinstance(role, str) and role not in tasks:
                errors.append(f"{rel}:{node.lineno}: router role {role!r} is not registered")

        # Agentic CLI subprocess launchers are allowed only where a protocol
        # lease is visibly acquired and settled in the same file.
        if rel not in LAUNCHER_ALLOW and re.search(
                r"subprocess\.(?:Popen|run)\([^\n]*(?:claude|agy|codex|grok)", source):
            errors.append(f"{rel}: direct agentic CLI subprocess is forbidden")

    for path in ROOT.rglob("*.sh"):
        if any(part in SKIP_PARTS for part in path.parts) or _rel(path).startswith(SKIP_PREFIXES):
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(source.splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if re.search(r"(^|[;&|]\s*)(?:\$[A-Z_]+|[^ ]*/)?(?:claude|agy|codex|grok)(?:\s|$)", line):
                errors.append(f"{_rel(path)}:{lineno}: shell launches an LLM CLI directly")

    certs = llm_task_registry.load_certifications()
    unknown = set(certs.get("task_models") or {}) - tasks
    if unknown:
        errors.append("config/llm_certifications.json: unknown task rows: "
                      + ", ".join(sorted(unknown)))
    for task_id in tasks:
        invalid = set(llm_task_registry.certified_models(task_id)) - official
        if invalid:
            errors.append(f"{task_id}: non-official certified models {sorted(invalid)}")
    return errors


def main() -> int:
    try:
        errors = audit()
    except (llm_task_registry.TaskRegistryError, OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    if errors:
        print("LLM governance audit FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"LLM governance audit PASS: {len(llm_task_registry.all_tasks())} tasks, "
          f"{len(llm_task_registry.official_models())} official providers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
