"""Client for the broker's local REST API, for the projects that call it.

**This file is vendored verbatim into the calling projects** (Phase 7). It is
the canonical copy; the copies are byte-identical and carry no local edits.
``lqb client sync`` writes them, ``lqb client sync --check`` and
``tests/test_client_vendored.py`` fail when one has drifted.

Three constraints follow from being vendored, and none of them may be relaxed
without breaking a consumer:

* **Standard library only.** The AI investment committee runs its scripts with
  the system ``python3`` and has no virtualenv, so pydantic — which the rest of
  this package depends on — is not available there.
* **No imports from :mod:`llm_quota_broker`.** The copies live inside unrelated
  packages (``scripts._shared`` and ``app.llm``) where this package is not
  importable at all.
* **Python 3.11.** The floor shared by all three projects.

The wire format is therefore hand-written dicts rather than the Phase 1 models.
That is a real cost — a schema change will not be caught by a type error here —
which is why :mod:`tests.test_client` drives this module against a live server
and validates in both directions against those models.

Reserve, run, settle
--------------------

The whole point of the broker is that quota is spent against a reservation, so
the intended shape is a lease::

    with client.lease(task_id="verify-2317", task_type="verify",
                      estimated_input_tokens=8_000,
                      estimated_output_tokens=2_000) as lease:
        result = run_the_cli(provider=lease.provider)
        lease.complete(usage={"input_tokens": ..., "output_tokens": ...},
                       exit_code=result.returncode, model=result.model)

The context manager cancels an unsettled lease on the way out, including when
the body raises, so a hold cannot leak on any path. A hold that does leak is
reclaimed at TTL, but until then every other project sees less headroom than
really exists — so settle promptly, and size
``reservation_ttl_seconds`` for how long the work actually takes.

The error taxonomy is the policy boundary
-----------------------------------------

DESIGN §8 lets a low-risk flow fall back to its own local limits when the broker
is unavailable, and Phase 7 fixed which flows those are. That permission hangs
entirely on this distinction:

* :class:`BrokerUnavailable` — the broker could not answer (down, unreachable,
  timed out, 5xx, or refusing our token). A flow that is allowed to degrade may
  fall back to its local budget here.
* :class:`BrokerRefused` — the broker answered, and the answer was no: no
  capacity, or every provider excluded. **No flow may fall back from this**,
  ever. Falling back here would spend the 20% hard reserve that the broker just
  declined to spend, which is the one thing the whole system exists to prevent.
* :class:`BrokerRejected` — the broker rejected the request itself (4xx). That
  is a bug in the caller, not a quota condition; falling back would hide it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any

__all__ = [
    "BASE_URL_ENV_VAR",
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT_SECONDS",
    "ERROR_CLASSES",
    "TOKEN_ENV_VAR",
    "BrokerAuthError",
    "BrokerClient",
    "BrokerError",
    "BrokerRefused",
    "BrokerRejected",
    "BrokerUnavailable",
    "Lease",
    "default_base_url",
    "load_token",
]

#: The broker binds loopback by default (DESIGN §3); Phase 8 fronts it with a
#: private network rather than moving the listener.
DEFAULT_BASE_URL = "http://127.0.0.1:8787"
BASE_URL_ENV_VAR = "LQB_BASE_URL"
TOKEN_ENV_VAR = "LQB_API_TOKEN"

#: Kept short on purpose. Every call here sits in front of work that is about to
#: spend real quota, and a caller blocked on a wedged daemon is worse off than
#: one told promptly that the broker is unavailable.
DEFAULT_TIMEOUT_SECONDS = 10.0

#: Keychain coordinates, mirroring ``llm_quota_broker.server.tokens``. Duplicated
#: rather than imported because this file is vendored; the drift test keeps the
#: copies honest, and these two strings changing would be an API break anyway.
KEYCHAIN_SERVICE = "llm-quota-broker"
KEYCHAIN_ACCOUNT = "api-token"
_KEYCHAIN_NOT_FOUND = 44
_KEYCHAIN_TIMEOUT_SECONDS = 15.0

#: `ErrorClass` (taxonomy.py). Settling with the right one matters: ``quota``
#: puts the provider into cooldown, and claiming it wrongly sidelines a healthy
#: provider for hours.
ERROR_CLASSES = ("auth", "quota", "timeout", "transient", "invalid_output", "cancelled")


class BrokerError(Exception):
    """Base class for every failure this client reports."""


class BrokerUnavailable(BrokerError):
    """The broker could not answer.

    The only condition under which DESIGN §8 permits a flow to fall back to its
    own local limits — and only for flows explicitly designated low-risk.
    """


class BrokerAuthError(BrokerUnavailable):
    """The broker refused our credentials.

    A subclass of :class:`BrokerUnavailable` so that fallback policy needs only
    one branch: from the caller's side a broker that will not talk to us is a
    broker that cannot answer. It is a distinct type so that logs can say
    "check `lqb token show`" instead of "is the daemon running".
    """


class BrokerRefused(BrokerError):
    """The broker answered, and the answer was no.

    Never fall back from this. See the module docstring.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "",
        decision_id: str = "",
        candidates: Sequence[Mapping[str, Any]] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.decision_id = decision_id
        #: Full per-provider evaluation, including why each was excluded. Worth
        #: logging: "why did nothing run at 03:00" is answerable only from this.
        self.candidates = list(candidates)


class BrokerRejected(BrokerError):
    """The broker rejected the request itself — a caller bug, not a quota state."""

    def __init__(self, message: str, *, status: int = 0, code: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.code = code


def default_base_url(env: Mapping[str, str] | None = None) -> str:
    environ = os.environ if env is None else env
    return (environ.get(BASE_URL_ENV_VAR) or "").strip() or DEFAULT_BASE_URL


def load_token(env: Mapping[str, str] | None = None, *, use_keychain: bool = True) -> str | None:
    """The broker API token: environment first, then the macOS Keychain.

    Same precedence as the daemon's own ``load_token``, so pinning
    ``LQB_API_TOKEN`` for a test or a one-off run affects both ends the same way.
    Returns ``None`` rather than raising when there is no token: an unconfigured
    caller should reach its own policy branch (fail-closed, or degrade if
    permitted), not die inside the client.
    """
    environ = os.environ if env is None else env
    from_env = (environ.get(TOKEN_ENV_VAR) or "").strip()
    if from_env:
        return from_env
    if not use_keychain:
        return None
    security = shutil.which("security")
    if security is None:
        return None
    try:
        found = subprocess.run(
            [
                security,
                "find-generic-password",
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                KEYCHAIN_ACCOUNT,
                "-w",
            ],
            capture_output=True,
            text=True,
            timeout=_KEYCHAIN_TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if found.returncode != 0:
        # 44 is errSecItemNotFound. Any other code means the Keychain is
        # unhappy (locked, no prompt available) rather than empty, but either
        # way this client has no token to present.
        return None
    return found.stdout.strip() or None


@dataclass
class Lease:
    """One reservation, from ``recommend`` through to settlement.

    Created by :meth:`BrokerClient.acquire`; not constructed directly.
    """

    client: BrokerClient
    reservation_id: str
    provider: str
    decision_id: str
    task_id: str
    expires_at: str
    #: Every candidate's evaluation, winners and losers alike. The losers carry
    #: the exclusion reasons, which is what an operator needs when the winner
    #: was not the expected provider.
    candidates: list[dict[str, Any]] = field(default_factory=list)
    fallback_used: bool = False
    started: bool = False
    settled: bool = False

    def start(self, *, model: str | None = None) -> dict[str, Any]:
        """Move the reservation to ACTIVE and open its execution row.

        Settlement needs that row, so :meth:`complete` calls this itself when a
        caller has not. ``model`` is recorded here and nowhere else — the
        settlement request has no field for it.
        """
        response = self.client.request(
            "POST",
            f"/v1/reservations/{self.reservation_id}/start",
            body={} if model is None else {"model": model},
        )
        self.started = True
        return response

    def complete(
        self,
        *,
        usage: Mapping[str, int] | None = None,
        exit_code: int | None = None,
        error_class: str | None = None,
        error_detail: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Settle with what the run actually used, releasing the difference.

        ``error_class="quota"`` also puts the provider into cooldown, so pass it
        only for an actual quota wall.
        """
        if error_class is not None and error_class not in ERROR_CLASSES:
            raise ValueError(
                f"unknown error_class {error_class!r}; expected one of {ERROR_CLASSES}"
            )
        if not self.started:
            self.start(model=model)
        body: dict[str, Any] = {"usage": _clean_usage(usage)}
        if exit_code is not None:
            body["exit_code"] = int(exit_code)
        if error_class is not None:
            body["error_class"] = error_class
        if error_detail:
            # The broker caps this at 2000 characters; trim here so a long CLI
            # traceback becomes a short explanation rather than a 422.
            body["error_detail"] = str(error_detail)[:2_000]
        response = self.client.request(
            "POST", f"/v1/reservations/{self.reservation_id}/complete", body=body
        )
        self.settled = True
        return response

    def cancel(self, reason: str | None = None) -> dict[str, Any]:
        """Release the hold without recording a run."""
        body = {"reason": str(reason)[:500]} if reason else {}
        response = self.client.request(
            "POST", f"/v1/reservations/{self.reservation_id}/cancel", body=body
        )
        self.settled = True
        return response


class BrokerClient:
    """Talks to one broker daemon.

    Stateless apart from its configuration, and safe to share between threads:
    :mod:`urllib` opens a fresh connection per request, so nothing is carried
    between calls.

    No retries, deliberately. A retry after a timeout cannot tell "the broker
    never saw it" from "the broker did it and the reply was lost", and guessing
    wrong on ``complete`` double-settles. The reservation TTL is the backstop
    for a settle that never lands.
    """

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        *,
        project: str = "",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        opener: Any | None = None,
    ) -> None:
        self.base_url = (base_url or default_base_url()).rstrip("/")
        self.token = token if token is not None else load_token()
        self.project = project
        self.timeout = float(timeout)
        self._opener = opener or urllib.request.build_opener()

    # ------------------------------------------------------------------ HTTP
    def request(
        self,
        method: str,
        path: str,
        *,
        body: Mapping[str, Any] | None = None,
        query: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        """One API call. Every failure leaves as one of this module's errors."""
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(dict(query))}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(url=url, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")

        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            raise self._from_http_error(exc) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise BrokerUnavailable(f"cannot reach the broker at {self.base_url}: {exc}") from exc

        if not payload:
            return {}
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            # A body this client cannot read is not a quota answer, so it must
            # not be reported as one.
            raise BrokerUnavailable(f"broker returned an unreadable body: {exc}") from exc
        return decoded if isinstance(decoded, dict) else {"data": decoded}

    def _from_http_error(self, exc: urllib.error.HTTPError) -> BrokerError:
        status = int(exc.code)
        detail = _error_detail(exc)
        code = str(detail.get("code") or "")
        message = str(detail.get("message") or exc.reason or "no detail")
        if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            return BrokerAuthError(
                f"the broker rejected this client's token ({status}): {message}. "
                "Check `lqb token show` or $" + TOKEN_ENV_VAR
            )
        if status >= HTTPStatus.INTERNAL_SERVER_ERROR:
            return BrokerUnavailable(f"broker error {status}: {message}")
        if code == "no_capacity":
            # Reachable from `complete`/`start` only in odd states; `recommend`
            # reports capacity in a 200 body. Classified as an answer either way.
            return BrokerRefused(message, code=code)
        return BrokerRejected(
            f"the broker rejected this request ({status}): {message}", status=status, code=code
        )

    # --------------------------------------------------------------- queries
    def health(self) -> dict[str, Any]:
        return self.request("GET", "/v1/health")

    def status(self) -> dict[str, Any]:
        return self.request("GET", "/v1/status")

    def providers(self) -> dict[str, Any]:
        return self.request("GET", "/v1/providers")

    def available(self) -> bool:
        """Whether the broker is answering at all — for a status line, not a gate.

        A gate must call the operation it actually needs and branch on the error
        it gets: between this check and the call, the daemon can stop.
        """
        try:
            self.health()
        except BrokerError:
            return False
        return True

    # -------------------------------------------------------------- routing
    def build_task(
        self,
        *,
        task_id: str,
        task_type: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
        project: str = "",
        requires_web: bool = False,
        preferred_providers: Sequence[str] = (),
        forbidden_providers: Sequence[str] = (),
        model: str | None = None,
        reservation_ttl_seconds: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """A ``Task`` body, with the project's own routing rules folded in.

        ``preferred_providers`` / ``forbidden_providers`` are how a project keeps
        its domain rules while the broker keeps the quota decision: the project
        states which providers are acceptable for this piece of work, and the
        broker picks among them on quota, confidence and success rate.
        """
        task: dict[str, Any] = {
            "project": project or self.project,
            "task_id": task_id,
            "task_type": task_type,
            "estimated_input_tokens": max(0, int(estimated_input_tokens)),
            "estimated_output_tokens": max(0, int(estimated_output_tokens)),
            "requires_web": bool(requires_web),
        }
        if not task["project"]:
            raise ValueError("a task needs a project; pass project= or set it on the client")
        if preferred_providers:
            task["preferred_providers"] = list(preferred_providers)
        if forbidden_providers:
            task["forbidden_providers"] = list(forbidden_providers)
        if model:
            task["model"] = model
        if reservation_ttl_seconds is not None:
            task["reservation_ttl_seconds"] = int(reservation_ttl_seconds)
        if idempotency_key:
            task["idempotency_key"] = idempotency_key
        return task

    def recommend(self, task: Mapping[str, Any], *, reserve: bool = True) -> dict[str, Any]:
        """Ask which provider should run this task. Reserves unless told not to.

        Returns the raw response, including the losing candidates. Raises
        :class:`BrokerRefused` when nothing could be recommended.
        """
        response = self.request(
            "POST", "/v1/recommend", body={"task": dict(task), "reserve": bool(reserve)}
        )
        error = response.get("error")
        if response.get("recommended") is None or error:
            detail = error if isinstance(error, Mapping) else {}
            raise BrokerRefused(
                str(detail.get("message") or "the broker recommended no provider"),
                code=str(detail.get("code") or "no_capacity"),
                decision_id=str(response.get("decision_id") or ""),
                candidates=_candidates(response),
            )
        return response

    def acquire(self, **task_fields: Any) -> Lease:
        """Reserve capacity for a task and return the lease to settle it with.

        Raises :class:`BrokerRefused` when the broker declines, and
        :class:`BrokerUnavailable` when it cannot answer — the two conditions
        calling projects must treat differently.
        """
        task = self.build_task(**task_fields)
        response = self.recommend(task, reserve=True)
        reservation = response.get("reservation")
        if not isinstance(reservation, Mapping) or not reservation.get("reservation_id"):
            # A recommendation without a reservation is a preview, and running
            # on a preview spends quota nobody is holding.
            raise BrokerRefused(
                "the broker recommended a provider but opened no reservation",
                code="no_reservation",
                decision_id=str(response.get("decision_id") or ""),
                candidates=_candidates(response),
            )
        return Lease(
            client=self,
            reservation_id=str(reservation["reservation_id"]),
            provider=str(response.get("recommended") or reservation.get("provider_id") or ""),
            decision_id=str(response.get("decision_id") or ""),
            task_id=str(response.get("task_id") or task["task_id"]),
            expires_at=str(reservation.get("expires_at") or ""),
            candidates=_candidates(response),
            fallback_used=bool(response.get("fallback_used")),
        )

    @contextmanager
    def lease(self, **task_fields: Any) -> Iterator[Lease]:
        """Acquire a lease and guarantee it is released.

        An unsettled lease is cancelled on the way out, including when the body
        raises, so no path leaks a hold. The cancel is best-effort: if the
        broker has gone away meanwhile there is nothing useful left to do, and
        raising here would mask whatever the body was already raising.
        """
        acquired = self.acquire(**task_fields)
        try:
            yield acquired
        finally:
            if not acquired.settled:
                try:
                    acquired.cancel("caller did not settle")
                except BrokerError:
                    pass


def _clean_usage(usage: Mapping[str, int] | None) -> dict[str, int]:
    """Keep only the fields ``TokenUsage`` declares.

    That model is ``extra="forbid"``, and a caller passing its own extra key
    (``cost_usd``, say) would otherwise turn a settlement into a 4xx and leak
    the hold until TTL.
    """
    if not usage:
        return {}
    allowed = (
        "input_tokens",
        "output_tokens",
        "cache_read_tokens",
        "cache_write_tokens",
        "thinking_tokens",
        "reasoning_tokens",
        "total_tokens",
        "model_calls",
    )
    return {key: max(0, int(usage.get(key) or 0)) for key in allowed if key in usage}


def _candidates(response: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = response.get("candidates")
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, Mapping)]


def _error_detail(exc: urllib.error.HTTPError) -> dict[str, Any]:
    """The error envelope from a failed response, or an empty dict."""
    try:
        payload = exc.read()
    except (OSError, ValueError):
        return {}
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return {}
    error = decoded.get("error") if isinstance(decoded, dict) else None
    return dict(error) if isinstance(error, dict) else {}
