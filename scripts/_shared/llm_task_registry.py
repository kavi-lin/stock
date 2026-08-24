"""Single source of truth for every LLM-consuming task in this repository.

Runtime routing is fail-closed: an unknown task or a task with no certified
broker-governed provider cannot spend quota.  Human-readable documentation and
the static governance audit are both derived from the same registry.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "config" / "llm_task_registry.json"
CERTIFICATIONS_PATH = ROOT / "config" / "llm_certifications.json"
PASSING_STATUSES = frozenset({"passed", "accepted_existing"})


class TaskRegistryError(RuntimeError):
    """The LLM task catalog is absent, malformed, or internally inconsistent."""


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TaskRegistryError(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(payload, dict):
        raise TaskRegistryError(f"{path.relative_to(ROOT)} must contain an object")
    return payload


@lru_cache(maxsize=1)
def load_registry() -> dict:
    payload = _read_json(REGISTRY_PATH)
    if payload.get("schema_version") != 1:
        raise TaskRegistryError("llm_task_registry schema_version must be 1")
    official = payload.get("official_models")
    categories = payload.get("categories")
    tasks = payload.get("tasks")
    if not isinstance(official, list) or not official:
        raise TaskRegistryError("official_models must be a non-empty list")
    if not isinstance(categories, dict) or not isinstance(tasks, dict) or not tasks:
        raise TaskRegistryError("categories/tasks must be non-empty objects")
    official_set = {str(model) for model in official}
    for task_id, task in tasks.items():
        if not isinstance(task, dict) or task.get("category") not in categories:
            raise TaskRegistryError(f"task {task_id!r} has an unknown category")
        override = task.get("certified_models")
        if override is not None:
            if not isinstance(override, list) or any(model not in official_set for model in override):
                raise TaskRegistryError(f"task {task_id!r} has invalid certified_models")
    return payload


@lru_cache(maxsize=1)
def load_certifications() -> dict:
    payload = _read_json(CERTIFICATIONS_PATH)
    if payload.get("schema_version") != 1:
        raise TaskRegistryError("llm_certifications schema_version must be 1")
    if not isinstance(payload.get("category_models"), dict):
        raise TaskRegistryError("llm_certifications.category_models must be an object")
    return payload


def official_models() -> tuple[str, ...]:
    return tuple(str(model) for model in load_registry()["official_models"])


def protocol_task_id(protocol: str | None) -> str:
    name = str(protocol or "").strip().lower()
    return f"agentic_protocol-{name}" if name else "agentic_protocol"


def task_definition(task_id: str) -> dict:
    key = str(task_id or "").strip().lower()
    task = (load_registry().get("tasks") or {}).get(key)
    if not isinstance(task, dict):
        raise TaskRegistryError(f"unregistered LLM task: {key or '<empty>'}")
    category = load_registry()["categories"][task["category"]]
    return {"id": key, **category, **task}


def certified_models(task_id: str) -> tuple[str, ...]:
    task = task_definition(task_id)
    official = official_models()
    task_cert = (load_certifications().get("task_models") or {}).get(task["id"])
    if task_cert is not None:
        if not isinstance(task_cert, list):
            raise TaskRegistryError(f"task_models[{task['id']}] must be a list")
        return tuple(model for model in official if model in task_cert)
    if "certified_models" in task:
        return tuple(model for model in official if model in task["certified_models"])
    category_rows = (load_certifications()["category_models"].get(task["category"]) or {})
    return tuple(
        model for model in official
        if isinstance(category_rows.get(model), dict)
        and category_rows[model].get("status") in PASSING_STATUSES
    )


def outage_policy(task_id: str) -> str:
    task = task_definition(task_id)
    return str(task.get("outage_policy") or task.get("default_outage_policy")
               or "daemon_defer")


def token_estimate(task_id: str, prompt_chars: int = 0, chars_per_token: int = 3) -> tuple[int, int]:
    task = task_definition(task_id)
    estimated_input = task.get("input_tokens")
    if estimated_input is None:
        estimated_input = max(1, (max(0, int(prompt_chars)) + max(1, chars_per_token) - 1)
                              // max(1, chars_per_token))
    return max(1, int(estimated_input)), max(1, int(task.get("output_tokens") or 2000))


def requires_web(task_id: str) -> bool:
    return task_definition(task_id).get("requires_web") is True


def all_tasks() -> dict[str, dict]:
    return {task_id: task_definition(task_id) for task_id in load_registry()["tasks"]}


def clear_cache() -> None:
    load_registry.cache_clear()
    load_certifications.cache_clear()
