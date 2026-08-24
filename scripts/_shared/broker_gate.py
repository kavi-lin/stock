"""Strict broker boundary shared by every repository LLM adapter.

The task registry supplies the certified provider set; llm-quota-broker owns
selection, reservation, and settlement. Local counters are telemetry only.
Broker off, unreachable, incompatible, or out of capacity always means no LLM
process starts. Daemon callers may defer or use deterministic output, but may
not start an unleased model.
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
    CLIENT_BROKER_VERSION, BrokerAuthError, BrokerClient, BrokerError, BrokerRefused,
    BrokerRejected, BrokerUnavailable, BrokerVersionMismatch,
)
from scripts._shared import llm_task_registry  # noqa: E402

__all__ = [
    "BROKER_PROJECT", "CLIENT_BROKER_VERSION", "BrokerAuthError", "BrokerError", "BrokerRefused",
    "BrokerRejected", "BrokerUnavailable", "BrokerVersionMismatch", "TASK_TYPE_PATTERN",
    "assigned_model", "broker_client", "broker_config",
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
    # Grok remains disabled until llm-quota-broker can reserve its quota pool.
}
MODEL_FOR_PROVIDER = {provider: model for model, provider in PROVIDER_FOR_MODEL.items()}

#: Broker-only means there is no inference fallback.  Callers may still fall
#: back to deterministic prose/data, but no LLM process starts without a lease.
DEFAULT_DEGRADABLE_ROLES: tuple[str, ...] = ()

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
    return {
        "enabled": raw.get("enabled", True) is not False,
        "base_url": str(raw.get("base_url") or "").strip() or None,
        "timeout_sec": _positive_float(raw.get("timeout_sec"), 10.0),
        "degradable_roles": DEFAULT_DEGRADABLE_ROLES,
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
    """A client, or `None` when configured off; callers must fail closed."""
    settings = broker_config(cfg)
    if not settings["enabled"]:
        return None
    return BrokerClient(
        settings["base_url"],
        project=BROKER_PROJECT,
        timeout=settings["timeout_sec"],
    )


def is_degradable(role: str, cfg: dict | None = None) -> bool:
    """No LLM role may run without broker authorisation."""
    return False


def assigned_model(lease) -> str:
    """The vendor-native model the broker assigned to `lease`, or `""`.

    Only agy ever fills this in, and there it is not advisory. That CLI meters
    its Gemini models and its Claude/GPT models in two pools that refill
    independently, so the broker picks a pool when the task names no model —
    and a hold taken against one pool is only true while the run stays inside
    it. Passing this to the CLI as `--model` is what keeps those two facts the
    same fact; running whatever the TUI happens to have selected spends a
    window nothing is holding.

    Empty for every single-pool provider, so a caller may pass it on
    unconditionally. Read defensively because `broker_client.py` is vendored:
    a copy predating the field is a stale sync, not a crash.
    """
    if lease is None:
        return ""
    return str(getattr(lease, "model", "") or "")


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
    key = str(role or "").strip().lower()
    characters = sum(len(part or "") for part in prompts)
    return llm_task_registry.token_estimate(key, characters, CHARS_PER_TOKEN)


def protocol_estimate(cfg: dict | None = None, protocol: str | None = None) -> tuple[int, int]:
    """(input, output) prior for one run of `protocol`. See the constants above.

    An unrecognised name falls back to `default`, never to zero: a protocol we
    have no numbers for is the one most likely to surprise us.
    """
    task_id = llm_task_registry.protocol_task_id(protocol)
    registry_estimate = llm_task_registry.token_estimate(task_id)
    # Keep measured operator overrides in llm_config until they are migrated to
    # the catalog; the registry is the conservative required fallback.
    table = broker_config(cfg)["protocol_tokens"]
    return table.get(str(protocol or "").strip().lower(), registry_estimate)


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
        # Ordinary governed paths are one inference.  Long-running adapters may
        # aggregate several same-provider inference turns behind one lease; if
        # they measured that count, preserve it rather than flattening it to 1.
        usage["model_calls"] = max(1, int(tokens.get("model_calls") or 1))
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

    * `None` — the broker is switched off or could not answer. Callers defer.
    * `[]` — the broker answered and *nothing* is eligible. Callers defer.
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


SHARED_POOL_LEAF = "all_models"

#: Upper bound, in minutes, for the short rolling window the panel reads. Sized
#: to cover a five-hour window reported with slack, and to stay far below the
#: daily/weekly pools it must never match.
SHORT_WINDOW_MINUTES = 360

#: Window names that mean the short rolling window. claude calls its five-hour
#: window `session`; agy namespaces `five_hour` under each pool.
SHORT_WINDOW_NAMES = ("five_hour", "session")


def _is_short_window(bucket: dict) -> bool:
    """The five-hour window, however this provider happens to name it.

    Three signals because no provider sends all three: the namespaced name
    (`gemini.five_hour`, `session`), `window_minutes` when the provider reports
    it (only codex does, and only for its weekly pool), and the provider's own
    `label` as a last resort.
    """
    name = str(bucket.get("name") or "")
    if any(seg in SHORT_WINDOW_NAMES for seg in name.split(".")):
        return True
    try:
        if 0 < float(bucket.get("window_minutes")) <= SHORT_WINDOW_MINUTES:
            return True
    except (TypeError, ValueError):
        pass
    label = str(bucket.get("label") or "").lower()
    return "five hour" in label or "5h" in label or "session" in label


def _headline_bucket(buckets: list[dict], routable_pool: str | None = None) -> dict | None:
    """The five-hour window the panel's headline reads, or None if there is none.

    The bars answer "how much have I burned in the last few hours", so all of
    them read the same kind of window. The broker's own headline cannot serve
    that: it is the minimum across everything it sees, which on 2026-08-14 drew
    claude at 45% from `weekly.fable` — one model's weekly pool — while the
    five-hour window was at 8%. Which window is tightest is a routing question,
    and the broker still answers it: `reserve_only` and `cooldown_until` are
    passed through untouched, so a provider the broker will not send work to is
    drawn as unusable no matter what this returns.

    Returns None when the provider reports no such window (codex sends only a
    weekly `primary`). The caller keeps the broker's headline there rather than
    presenting a weekly figure as if it were five-hour; `headline_bucket` names
    the window either way, so the panel can say which one it is showing.

    Two tie-breaks, in order: stay inside the pool the broker would route to
    (agy meters `gemini.*` and `claude_gpt.*` independently), then prefer a
    shared sub-pool over a per-model one. Anything still tied resolves to the
    tightest.
    """
    short = [b for b in buckets
             if _is_short_window(b) and b.get("remaining_percent") is not None]
    if not short:
        return None
    pool = str(routable_pool or "")
    if pool:
        short = [b for b in short
                 if str(b["name"]) == pool or str(b["name"]).startswith(pool + ".")]
        if not short:
            # The only five-hour windows belong to pools the broker will not
            # route to. Borrowing one of them is the exact failure V4.129.0 fixed
            # — agy drawn at 0% from `claude_gpt.five_hour` while dispatching
            # Gemini work — so this reports no five-hour window instead.
            return None
    shared = [b for b in short
              if str(b["name"]).partition(".")[2] == SHARED_POOL_LEAF]
    if shared:
        short = shared
    return min(short, key=lambda b: float(b["remaining_percent"]))


def provider_quota(cfg: dict | None = None) -> dict:
    """Live remaining quota per model, straight from the broker. For the UI.

    Keyed by **this repo's** model names (`gemini`, not `agy`) so the sidebar can
    render without knowing the mapping. Returns `{}` when the broker is off or
    unreachable — the caller shows "unknown", never a stale number, because a
    percentage from an unknown time is exactly the false precision DESIGN §2.1
    forbids.

    `remaining_percent` is the broker's own headline, matching what `lqb status`
    prints: the tightest window among the ones a run would actually touch. For
    agy that is the pool the router would charge (`routable_pool`), not the
    minimum across both — V4.129.0. Until then this recomputed the global
    minimum locally, which on 2026-08-10 drew agy as "0% left / 保留區" from a
    `claude_gpt` five-hour window the router had already ruled out, while it was
    dispatching Gemini work to a pool with 100% of its five-hour window free. A
    panel that disagrees with the router about whether a provider is usable is
    worse than no panel, and the rule belongs in the one place that makes the
    routing decision.

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
    empty = {"providers": {}, "hard_reserve_percent": None, "active_reservations": []}
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
        buckets: list[dict] = []
        if isinstance(raw_buckets, dict) and raw_buckets:
            for name, window in raw_buckets.items():
                if not isinstance(window, dict):
                    continue
                buckets.append({
                    "name": str(name),
                    "remaining_percent": window.get("remaining_percent"),
                    # V4.115.0 — `used_percent` and `label` were dropped here,
                    # so a UI showing consumption had to derive it as
                    # 100 - remaining. That is right for claude and wrong for
                    # agy, whose windows report a remaining percent with
                    # `used_percent: null` — the broker does not claim to know
                    # what was consumed there, and inverting the one number it
                    # does give invents a figure it never made.
                    "used_percent": window.get("used_percent"),
                    # The provider's own name for the window ("allmodels",
                    # "Fable"), which is more specific than the namespaced key
                    # this repo has to reverse-engineer in `bucketLabel`.
                    "label": window.get("label"),
                    "resets_at": window.get("resets_at"),
                    "reset_label": window.get("reset_label"),
                    "refresh_in_seconds": window.get("refresh_in_seconds"),
                    "window_minutes": window.get("window_minutes"),
                    "reserve_only": bool(window.get("reserve_only")),
                })
            # Tightest first: the binding window is the one worth reading first,
            # and a bucket with no percentage cannot bind anything.
            buckets.sort(key=lambda b: (b["remaining_percent"] is None,
                                        b["remaining_percent"]))
        try:
            remaining = float(entry["remaining_percent"])
        except (KeyError, TypeError, ValueError):
            # Only a broker too old to send the field, or one with no snapshot
            # to reduce. The local minimum is the honest fallback: it is what
            # this computed before the field existed, and it errs low.
            values = [b["remaining_percent"] for b in buckets
                      if b["remaining_percent"] is not None]
            remaining = min((float(v) for v in values), default=None)
        # The panel reads the five-hour window; the broker's headline is whatever
        # window is tightest, which is the routing answer, not this one. A
        # provider with no such window keeps the broker's figure rather than
        # having a weekly number relabelled as five-hour.
        headline = _headline_bucket(buckets, entry.get("routable_pool"))
        if headline is not None:
            remaining = float(headline["remaining_percent"])
        out[model] = {
            "provider": provider_id,
            "remaining_percent": remaining,
            # Which pool the broker would charge, for a provider metering more
            # than one. `None` = one pool. Left exactly as the broker sent it:
            # it is a routing fact, and `headline_bucket` below is the separate
            # question of which window the number above was read from.
            "routable_pool": entry.get("routable_pool"),
            # The window `remaining_percent` came from, so the panel can name it
            # and mark the matching row. `None` = the broker's own headline.
            "headline_bucket": str(headline["name"]) if headline is not None else None,
            "buckets": buckets,
            # Display identity is supplied by the broker. `plan` below remains
            # the provider-native value for diagnostics and must not leak into
            # UI copy (Codex currently reports the internal slug `prolite`).
            "plan": snapshot.get("plan") if isinstance(snapshot, dict) else None,
            "plan_label": entry.get("plan_label"),
            "current_model": entry.get("current_model"),
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
    active = []
    for row in status.get("active_reservations") or []:
        if not isinstance(row, dict):
            continue
        reservation = row.get("reservation") if isinstance(row.get("reservation"), dict) else row
        task = row.get("task") if isinstance(row.get("task"), dict) else {}
        provider_id = str(reservation.get("provider") or row.get("provider") or "")
        model = MODEL_FOR_PROVIDER.get(provider_id)
        if not model:
            continue
        project = task.get("project") or reservation.get("project") or row.get("project")
        active.append({
            "reservation_id": reservation.get("reservation_id"),
            "provider": provider_id,
            "model": model,
            "project": project,
            # Missing attribution is external by default. A shared broker row
            # must prove it belongs to this repo before the Dashboard may paint
            # the local green light.
            "is_local_project": project == BROKER_PROJECT,
            "task_type": task.get("task_type") or row.get("task_type"),
            "task_id": task.get("task_id") or reservation.get("task_id") or row.get("task_id"),
            "state": reservation.get("state") or row.get("state"),
            "created_at": reservation.get("created_at") or row.get("created_at"),
        })
    return {"providers": out, "hard_reserve_percent": reserve,
            "active_reservations": active}


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
