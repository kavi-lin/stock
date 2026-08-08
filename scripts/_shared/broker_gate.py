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

import re
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
    "BrokerUnavailable", "TASK_TYPE_PATTERN", "broker_client", "broker_config",
    "estimate_tokens", "governed_models",
    "is_degradable", "new_task_id", "protocol_estimate", "protocol_task_type",
    "provider_for", "provider_quota", "quota_snapshot",
    "ranked_models", "sanitize_task_type", "usage_for_broker",
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
#: hard reserve. It is the floor under an *unrecognised* protocol name — every
#: protocol we have measured overrides it from `config/llm_config.json` under
#: `broker.protocol_tokens`, keyed by protocol name. Tune it there, not here.
PROTOCOL_INPUT_TOKENS = 200_000
PROTOCOL_OUTPUT_TOKENS = 40_000

#: Protocol runs are reported to the broker as `agentic_protocol:<name>` rather
#: than one flat `agentic_protocol`, because these protocols differ by an order
#: of magnitude — `triage` is one sonnet pass filling in headlines, `invest` is
#: a five-lane opus debate that runs for forty minutes. One shared prior cannot
#: serve both: sized for `triage` it leaves the largest consumer effectively
#: unreserved, and sized for `invest` it falsely refuses the cheap one, which is
#: fail-closed and stops both calling projects. Separate task types also make
#: `lqb history --stats` report a row per protocol, so each one calibrates from
#: its own runs instead of from an average of things that are not alike.
PROTOCOL_TASK_TYPE_PREFIX = "agentic_protocol"

#: The broker's own schema for `task_type`. Names are built to satisfy it here
#: rather than discovered as a 400 at acquire time, because a rejected request is
#: not a quota state: `_acquire` classifies it as this repo's bug and fails
#: closed, so one invalid character stops every protocol run. V4.110.0 did
#: exactly that — it joined the protocol name on with a colon, which this pattern
#: does not allow, and every `分析` / `產業掃描` / triage run raised
#: `ProtocolBlocked` while `lqb status` showed a healthy daemon with quota to
#: spare. Fixed in V4.111.4; the separator is now a hyphen.
TASK_TYPE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

#: Joins the prefix to the protocol name. A hyphen, because protocol names carry
#: underscores of their own (`llm_review`) and the boundary has to stay readable
#: in `lqb history --stats --task-type agentic_protocol-invest`.
PROTOCOL_TASK_TYPE_SEPARATOR = "-"

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
    roles = raw.get("degradable_roles")
    return {
        "enabled": raw.get("enabled", True) is not False,
        "base_url": str(raw.get("base_url") or "").strip() or None,
        "timeout_sec": _positive_float(raw.get("timeout_sec"), 10.0),
        "degradable_roles": tuple(str(r).strip().lower() for r in roles if str(r).strip())
                            if isinstance(roles, list) else DEFAULT_DEGRADABLE_ROLES,
        "protocol_tokens": _protocol_token_table(raw.get("protocol_tokens")),
    }


def _protocol_token_table(raw: object) -> dict:
    """`broker.protocol_tokens` → `{protocol name: (input, output)}`.

    Two shapes are accepted. The nested one keys estimates by protocol name and
    reserves `default` for the rest. The flat `{"input": …, "output": …}` is the
    pre-measurement shape from V4.106.0; it is read as `default` alone, so a
    config written before per-protocol estimates keeps its old meaning instead
    of silently falling back to the constants.
    """
    if not isinstance(raw, dict):
        return {}
    entries = {"default": raw} if ("input" in raw or "output" in raw) else raw
    table = {}
    for name, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        table[str(name).strip().lower()] = (
            _positive_int(entry.get("input"), PROTOCOL_INPUT_TOKENS),
            _positive_int(entry.get("output"), PROTOCOL_OUTPUT_TOKENS),
        )
    return table


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


def protocol_estimate(cfg: dict | None = None, protocol: str | None = None) -> tuple[int, int]:
    """(input, output) prior for one run of `protocol`. See the constants above.

    An unrecognised name falls back to `default`, never to zero: a protocol we
    have no numbers for is the one most likely to surprise us.
    """
    table = broker_config(cfg)["protocol_tokens"]
    fallback = table.get("default", (PROTOCOL_INPUT_TOKENS, PROTOCOL_OUTPUT_TOKENS))
    return table.get(str(protocol or "").strip().lower(), fallback)


def sanitize_task_type(name: object, default: str = "") -> str:
    """`name` reduced to something `TASK_TYPE_PATTERN` accepts, or `default`.

    Substitution rather than rejection: the caller is naming its own work, and a
    name the broker will not take should cost a mangled history row, never a
    refused run. Non-ASCII letters are replaced too — `str.isalnum()` is true for
    CJK, and the broker's pattern is ASCII-only.
    """
    cleaned = "".join(
        character if (character.isascii() and character.isalnum()) or character in "_-" else "-"
        for character in str(name or "").strip().lower()
    ).lstrip("-_")
    return cleaned or default


def protocol_task_type(protocol: str | None = None) -> str:
    """The ledger task type for one run of `protocol`.

    Unnamed runs keep the bare `agentic_protocol`, which is also what every run
    recorded before V4.110.0 is filed under — those rows are an average across
    protocols and should not be read as any single protocol's history. Runs
    between V4.110.0 and V4.111.4 recorded nothing at all: the name they built
    was rejected by the broker before it reached the ledger.
    """
    name = sanitize_task_type(protocol)
    if not name:
        return PROTOCOL_TASK_TYPE_PREFIX
    return f"{PROTOCOL_TASK_TYPE_PREFIX}{PROTOCOL_TASK_TYPE_SEPARATOR}{name}"


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

    `buckets` carries the individual windows behind that minimum, tightest
    first. The min alone is not enough to act on: "claude 54%" is a weekly pool
    that refills on Aug 13, while "gemini 78%" sits next to a 5h window at 94%
    that refills in two hours. Same headline number, completely different answer
    to "can I run the protocol now or should I wait?". Each bucket keeps
    whichever reset hint the provider gave — `resets_at`, a `reset_label`
    string, or `refresh_in_seconds` — because no provider reports all three.
    """
    return quota_snapshot(cfg)["providers"]


def quota_snapshot(cfg: dict | None = None) -> dict:
    """`provider_quota()` plus the broker-wide `hard_reserve_percent`, one call.

    The sidebar needs both on every poll and they come from the same `/v1/status`
    response; fetching twice would double the broker traffic for no new
    information. Shape: `{"providers": {...}, "hard_reserve_percent": float|None}`.
    """
    client = broker_client(cfg)
    empty = {"providers": {}, "hard_reserve_percent": None}
    if client is None:
        return empty
    try:
        status = client.status()
    except BrokerError:
        return empty

    out: dict[str, dict] = {}
    for entry in status.get("providers") or []:
        if not isinstance(entry, dict):
            continue
        provider_id = str((entry.get("info") or {}).get("id") or "")
        model = MODEL_FOR_PROVIDER.get(provider_id)
        if model is None:
            continue
        snapshot = entry.get("snapshot") or {}
        raw_buckets = snapshot.get("buckets") if isinstance(snapshot, dict) else None
        remaining = None
        buckets: list[dict] = []
        if isinstance(raw_buckets, dict) and raw_buckets:
            for name, window in raw_buckets.items():
                if not isinstance(window, dict):
                    continue
                buckets.append({
                    "name": str(name),
                    "remaining_percent": window.get("remaining_percent"),
                    "resets_at": window.get("resets_at"),
                    "reset_label": window.get("reset_label"),
                    "refresh_in_seconds": window.get("refresh_in_seconds"),
                    "window_minutes": window.get("window_minutes"),
                    "reserve_only": bool(window.get("reserve_only")),
                })
            values = [b["remaining_percent"] for b in buckets
                      if b["remaining_percent"] is not None]
            if values:
                remaining = min(float(v) for v in values)
            # Tightest first: the binding window is the one worth reading first,
            # and a bucket with no percentage cannot bind anything.
            buckets.sort(key=lambda b: (b["remaining_percent"] is None,
                                        b["remaining_percent"]))
        out[model] = {
            "provider": provider_id,
            "remaining_percent": remaining,
            "buckets": buckets,
            "plan": snapshot.get("plan") if isinstance(snapshot, dict) else None,
            "reserve_only": bool(entry.get("reserve_only")),
            "cooldown_until": entry.get("cooldown_until"),
            "authenticated": entry.get("authenticated"),
            "confidence": (entry.get("provenance") or {}).get("confidence"),
            "age_seconds": (entry.get("provenance") or {}).get("age_seconds"),
        }

    # The floor the broker will not dispatch below. Surfaced so the sidebar can
    # draw it on the quota bars rather than leaving the user to wonder why a
    # provider showing 15% left is being refused. None rather than a guessed
    # default — a made-up number drawn as a hard line is worse than no line.
    try:
        reserve = float(status.get("hard_reserve_percent"))
    except (TypeError, ValueError):
        reserve = None
    return {"providers": out, "hard_reserve_percent": reserve}


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
