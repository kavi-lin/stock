"""LLM Quota Broker gate — this project's half of the Phase 7 integration.

`model_router.py` used to be the whole quota authority for this repo: a daily
call budget, a rolling five-hour window, and a cooldown, all counted in
`config/llm_usage.json`. The problem those counters cannot solve is that the
Taiwan-stock project is spending the *same* subscriptions and has never been
able to see this file. Two independent budgets against one pool cannot add up.

So the broker is now the authority, and this module is the boundary:

* **What the broker decides** — whether there is quota to spend, and on which
  provider. It sees every project's holds in one ledger and enforces the 20%
  hard reserve that neither project can turn off.
* **What this project still decides** — which providers are acceptable for a
  given role (the debater pins a model per voice on purpose), what the prompts
  are, and what to do with the answer. Those rules travel to the broker as
  `preferred_providers` / `forbidden_providers`; none of them moved.

Local counters keep recording (see `model_router._record`), because they are
what the degraded path below runs on. They no longer *block* while the broker
is answering — two enforcers against one pool is the same mistake in miniature.

Failure policy (Phase 7, decided 2026-08-08)
--------------------------------------------

Fail-closed by default. A flow that cannot reach the broker does not run.

The single exception is the news line — the Break News debate and brief, and
the link digest — which may fall back to the local budget. Those are continuous,
non-decision-bearing flows where hours of silence costs more than the
imprecision of a local counter, and their spend is still bounded by
`config/llm_config.json`.

That permission applies **only** when the broker could not answer. When the
broker answers "no capacity", every flow stops, news included: falling back
there would spend exactly the reserve the broker just declined to spend.
`BrokerRefused` and `BrokerUnavailable` exist to keep those two cases from ever
being confused, and `_run_chain` branches on the type, never on a message.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts._shared.broker_client import (  # noqa: E402
    BrokerAuthError, BrokerClient, BrokerError, BrokerRefused, BrokerRejected, BrokerUnavailable,
)

__all__ = [
    "BROKER_PROJECT", "BrokerAuthError", "BrokerError", "BrokerRefused", "BrokerRejected",
    "BrokerUnavailable", "broker_client", "broker_config", "estimate_tokens", "governed_models",
    "is_degradable", "new_task_id", "protocol_estimate", "provider_for", "provider_quota",
    "ranked_models", "usage_for_broker",
]

#: Namespaces this project's tasks in the shared ledger. Task ids are unique per
#: project there, so two projects may use the same id without colliding.
BROKER_PROJECT = "ai-investment-committee"

#: This repo's model names → broker provider ids. `gemini` is the odd one: the
#: runner it names has invoked the `agy` binary since llm_drivers was written
#: (see `run_gemini`), and the broker calls that provider what it is.
PROVIDER_FOR_MODEL = {
    "claude": "claude",
    "gemini": "agy",
    "codex": "codex",
    # `grok` has no entry on purpose. The broker keeps the id dormant (Phase 3
    # deferred it: its weekly pool is only readable by scraping a logged-in
    # settings page), so it can neither reserve nor be recommended. A grok call
    # therefore stays governed by this repo's local budget alone, which is
    # stated here rather than discovered later from a KeyError.
}
MODEL_FOR_PROVIDER = {provider: model for model, provider in PROVIDER_FOR_MODEL.items()}

#: Roles permitted to degrade to the local budget when the broker cannot answer.
DEFAULT_DEGRADABLE_ROLES = ("debate", "brief", "link_digest")

#: Rough per-role output priors, in tokens. Input is measured from the actual
#: prompt; only the reply has to be guessed.
DEFAULT_OUTPUT_TOKENS = 2_000
OUTPUT_TOKEN_PRIORS = {
    "debate": 3_000,
    "brief": 2_000,
    "office": 3_000,
    "generate": 4_000,
    "report_polish": 6_000,
    "intraday_eval": 1_500,
    "link_digest": 2_000,
}

#: An agentic protocol run is dozens to hundreds of turns behind one governed
#: call, so no prompt-derived number describes it. This prior is deliberately
#: large: DESIGN §6 requires missing data to be treated conservatively, never as
#: zero, and over-reserving costs a refused run while under-reserving eats the
#: hard reserve. It is a starting point, not a measurement — every run reports
#: its real tokens back, which is what the broker's own estimator calibrates on.
#: Tune it in `config/llm_config.json` under `broker.protocol_tokens` once a few
#: runs have been recorded, rather than editing this file.
PROTOCOL_INPUT_TOKENS = 200_000
PROTOCOL_OUTPUT_TOKENS = 40_000

#: Reservation TTLs. The broker reclaims a hold when its TTL passes — including
#: one that is still running — and a reclaimed hold cannot then be settled, so
#: these must cover the slowest realistic run rather than the typical one.
#: `LLM_TIMEOUT_SEC` bounds a single call; a protocol run has no such bound,
#: hence six hours.
SINGLE_CALL_TTL_SECONDS = 1_800
PROTOCOL_TTL_SECONDS = 21_600

#: Characters per token. Deliberately low: these prompts carry a lot of Chinese,
#: where a character is close to a token, and the usual 4:1 English ratio would
#: under-state the input by three times. Over-stating is the safe direction.
CHARS_PER_TOKEN = 3


def broker_config(cfg: dict | None = None) -> dict:
    """The `broker` block of `config/llm_config.json`, with defaults filled in.

    Absent block = enabled with defaults, because the point of Phase 7 is that
    the broker governs; a config file that predates it must not silently opt out.
    """
    raw = (cfg or {}).get("broker")
    raw = raw if isinstance(raw, dict) else {}
    protocol = raw.get("protocol_tokens")
    protocol = protocol if isinstance(protocol, dict) else {}
    roles = raw.get("degradable_roles")
    return {
        "enabled": raw.get("enabled", True) is not False,
        "base_url": str(raw.get("base_url") or "").strip() or None,
        "timeout_sec": _positive_float(raw.get("timeout_sec"), 10.0),
        "degradable_roles": tuple(str(r).strip().lower() for r in roles if str(r).strip())
                            if isinstance(roles, list) else DEFAULT_DEGRADABLE_ROLES,
        "protocol_input_tokens": _positive_int(
            protocol.get("input"), PROTOCOL_INPUT_TOKENS),
        "protocol_output_tokens": _positive_int(
            protocol.get("output"), PROTOCOL_OUTPUT_TOKENS),
    }


def broker_client(cfg: dict | None = None) -> BrokerClient | None:
    """A client, or `None` when this project is configured not to use the broker.

    `None` means "the broker is switched off here", which is a different state
    from "the broker is down": the caller keeps its old local-budget behaviour
    rather than taking the degraded path or refusing.
    """
    settings = broker_config(cfg)
    if not settings["enabled"]:
        return None
    return BrokerClient(
        settings["base_url"],
        project=BROKER_PROJECT,
        timeout=settings["timeout_sec"],
    )


def is_degradable(role: str, cfg: dict | None = None) -> bool:
    """Whether this role may fall back to the local budget when the broker is down."""
    return str(role or "").strip().lower() in set(broker_config(cfg)["degradable_roles"])


def provider_for(model: str) -> str | None:
    """Broker provider id for one of this repo's model names, if it has one."""
    return PROVIDER_FOR_MODEL.get(str(model or "").strip().lower())


def governed_models() -> tuple[str, ...]:
    """This repo's model names that the broker can actually route."""
    return tuple(PROVIDER_FOR_MODEL)


def new_task_id(role: str) -> str:
    """A fresh ledger task id. Unique per call so history reads as a sequence."""
    return f"{(role or 'call').strip().lower()}-{uuid.uuid4().hex[:12]}"


def estimate_tokens(role: str, *prompts: str, cfg: dict | None = None) -> tuple[int, int]:
    """(input, output) token estimate for one governed call.

    Input is measured from the prompts actually being sent, which is the one
    number here that is not a guess. Output is a per-role prior.
    """
    characters = sum(len(part or "") for part in prompts)
    estimated_input = max(1, -(-characters // CHARS_PER_TOKEN))
    key = str(role or "").strip().lower()
    return estimated_input, int(OUTPUT_TOKEN_PRIORS.get(key, DEFAULT_OUTPUT_TOKENS))


def protocol_estimate(cfg: dict | None = None) -> tuple[int, int]:
    """(input, output) prior for one agentic protocol run. See the constants above."""
    settings = broker_config(cfg)
    return settings["protocol_input_tokens"], settings["protocol_output_tokens"]


def usage_for_broker(tokens: dict | None) -> dict:
    """This repo's token dict → the broker's `TokenUsage` field names.

    Accepts both shapes in circulation: the `llm_drivers` names
    (`input_tokens`…) and the compact persisted ones (`input`…). `cost_usd` is
    dropped — the broker's model forbids unknown fields, and a settlement
    rejected over a stray key would leak the hold until its TTL.
    """
    if not isinstance(tokens, dict) or not tokens:
        return {}
    mapping = (
        ("input_tokens", ("input_tokens", "input")),
        ("output_tokens", ("output_tokens", "output")),
        ("cache_read_tokens", ("cache_read_tokens", "cache_read")),
        ("cache_write_tokens", ("cache_write_tokens", "cache_write")),
    )
    usage: dict[str, int] = {}
    for target, sources in mapping:
        for source in sources:
            if source in tokens:
                usage[target] = max(0, int(tokens.get(source) or 0))
                break
    if usage:
        # One governed call. The broker never sums tokens across providers, but
        # it does count calls, and this is the honest count for this path.
        usage["model_calls"] = 1
    return usage


#: Representative size of one debate turn, for the ranking preview below. The
#: preview has no prompt to measure yet, and asking with a token estimate of ~0
#: would make every provider look eligible — including one whose remaining quota
#: cannot actually cover a turn. These numbers are the `debate` role's own prior.
DEBATE_PREVIEW_TOKENS = (12_000, 3_000)


def ranked_models(role: str = "debate", *, count: int = 0, requires_web: bool = False,
                  cfg: dict | None = None) -> list[str] | None:
    """The broker's current ranking of providers that can actually serve, best first.

    Returned as **this repo's** model names. Three outcomes, and callers must
    tell them apart:

    * `None` — the broker is switched off or could not answer. The caller falls
      back to its own configuration (the news line is allowed to; see the module
      docstring).
    * `[]` — the broker answered and *nothing* is eligible. Not a fallback
      condition: that answer is about the hard reserve.
    * a list — ranked best first, already filtered to providers with capacity.

    Uses a preview (`reserve=false`), so it holds no quota. The broker records
    the preview as a decision, which is why this is called once per debate and
    never on a UI poll — a decision log buried under status-panel traffic stops
    being able to answer "why did nothing run at 03:00".
    """
    client = broker_client(cfg)
    if client is None:
        return None
    estimated_input, estimated_output = DEBATE_PREVIEW_TOKENS
    task = client.build_task(
        task_id=new_task_id(f"{role}-rank"),
        task_type=f"{role}_ranking",
        estimated_input_tokens=estimated_input,
        estimated_output_tokens=estimated_output,
        requires_web=requires_web,
    )
    try:
        candidates = (client.recommend(task, reserve=False).get("candidates") or [])
    except BrokerRefused as exc:
        # Still an answer: the candidate list explains who was excluded and why.
        candidates = exc.candidates
    except BrokerError:
        return None

    ranked = sorted(
        (c for c in candidates
         if isinstance(c, dict) and c.get("eligible") and c.get("rank") is not None),
        key=lambda c: int(c["rank"]),
    )
    models: list[str] = []
    for candidate in ranked:
        model = MODEL_FOR_PROVIDER.get(str(candidate.get("provider") or ""))
        if model and model not in models:
            models.append(model)
    return models[:count] if count else models


def provider_quota(cfg: dict | None = None) -> dict:
    """Live remaining quota per model, straight from the broker. For the UI.

    Keyed by **this repo's** model names (`gemini`, not `agy`) so the sidebar can
    render without knowing the mapping. Returns `{}` when the broker is off or
    unreachable — the caller shows "unknown", never a stale number, because a
    percentage from an unknown time is exactly the false precision DESIGN §2.1
    forbids.

    `remaining_percent` is the **worst** bucket, matching what `lqb status`
    prints. Agy's two pools are separate, so a global minimum can under-report
    headroom for a task aimed at the healthier group; under-reporting is the
    safe direction and keeps this number comparable across providers.
    """
    client = broker_client(cfg)
    if client is None:
        return {}
    try:
        status = client.status()
    except BrokerError:
        return {}

    out: dict[str, dict] = {}
    for entry in status.get("providers") or []:
        if not isinstance(entry, dict):
            continue
        provider_id = str((entry.get("info") or {}).get("id") or "")
        model = MODEL_FOR_PROVIDER.get(provider_id)
        if model is None:
            continue
        snapshot = entry.get("snapshot") or {}
        buckets = snapshot.get("buckets") if isinstance(snapshot, dict) else None
        remaining = None
        if isinstance(buckets, dict) and buckets:
            values = [w.get("remaining_percent") for w in buckets.values()
                      if isinstance(w, dict) and w.get("remaining_percent") is not None]
            if values:
                remaining = min(float(v) for v in values)
        out[model] = {
            "provider": provider_id,
            "remaining_percent": remaining,
            "reserve_only": bool(entry.get("reserve_only")),
            "cooldown_until": entry.get("cooldown_until"),
            "authenticated": entry.get("authenticated"),
            "confidence": (entry.get("provenance") or {}).get("confidence"),
            "age_seconds": (entry.get("provenance") or {}).get("age_seconds"),
        }
    return out


def _positive_int(value, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _positive_float(value, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default
