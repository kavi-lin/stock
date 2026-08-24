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
* :class:`BrokerVersionMismatch` — the client and daemon are different protocol
  versions. This is fail-closed like a rejected request; callers must never
  bypass a stale broker and spend quota behind its back.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
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
    "CLIENT_BROKER_VERSION",
    "BrokerAuthError",
    "BrokerClient",
    "BrokerError",
    "BrokerHandshake",
    "BrokerRefused",
    "BrokerRejected",
    "BrokerUnavailable",
    "BrokerVersionMismatch",
    "Lease",
    "RunStream",
    "default_base_url",
    "load_token",
    "parse_run_stream",
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

#: Wire-contract version expected by this vendored client. It intentionally
#: moves with the broker package version: every caller sends new work only when
#: the daemon it reached was started from the same release.
CLIENT_BROKER_VERSION = "0.3.0"
HEARTBEAT_INTERVAL_SECONDS = 15.0

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


class BrokerVersionMismatch(BrokerError):
    """The reachable daemon and this client do not speak the same release."""

    def __init__(self, handshake: BrokerHandshake) -> None:
        super().__init__(handshake.message)
        self.client_version = handshake.client_version
        self.broker_version = handshake.broker_version
        self.status = handshake.status


@dataclass(frozen=True)
class BrokerHandshake:
    """Compatibility result from the public liveness endpoint."""

    client_version: str
    broker_version: str | None
    status: str
    message: str

    @property
    def compatible(self) -> bool:
        return self.status == "compatible"

    @property
    def restart_required(self) -> bool:
        return self.status == "broker_restart_required"


def default_base_url(env: Mapping[str, str] | None = None) -> str:
    environ = os.environ if env is None else env
    return (environ.get(BASE_URL_ENV_VAR) or "").strip() or DEFAULT_BASE_URL


def _version_key(value: str) -> tuple[int, int, int] | None:
    """Comparable release core for direction hints; compatibility stays exact."""
    core = value.strip().removeprefix("v").split("+", 1)[0].split("-", 1)[0]
    parts = core.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        return None
    return int(parts[0]), int(parts[1]), int(parts[2])


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
    #: The model the broker chose; empty when it chose none. **Run this model.**
    #: Agy meters its Gemini models and its Claude/GPT models in two pools that
    #: refill independently, so a hold taken against one of them is true only
    #: while the run stays inside it — dispatching something else spends quota
    #: no reservation covers. Empty for every single-pool provider, and for a
    #: task that pinned a model of its own, where the caller's choice stands.
    model: str = ""
    #: Every candidate's evaluation, winners and losers alike. The losers carry
    #: the exclusion reasons, which is what an operator needs when the winner
    #: was not the expected provider.
    candidates: list[dict[str, Any]] = field(default_factory=list)
    fallback_used: bool = False
    started: bool = False
    settled: bool = False
    _heartbeat_stop: threading.Event = field(default_factory=threading.Event, repr=False)
    _heartbeat_thread: threading.Thread | None = field(default=None, repr=False)

    def start(
        self,
        *,
        model: str | None = None,
        process_pid: int | None = None,
        process_pgid: int | None = None,
    ) -> dict[str, Any]:
        """Move the reservation to ACTIVE and open its execution row.

        Settlement needs that row, so :meth:`complete` calls this itself when a
        caller has not. ``model`` is recorded here and nowhere else — the
        settlement request has no field for it.

        Defaults to :attr:`model` when the broker chose one, so the ledger
        records what the reservation is actually against. Pass ``model``
        explicitly only when the run really used something else; the recorded
        value is what later calibrates that pool's burn rate, and a convenient
        alias there ("gemini") costs a real observation.
        """
        chosen = model if model is not None else (self.model or None)
        body: dict[str, Any] = {} if chosen is None else {"model": chosen}
        if process_pid is not None:
            body["process_pid"] = int(process_pid)
        if process_pgid is not None:
            body["process_pgid"] = int(process_pgid)
        response = self.client.request(
            "POST",
            f"/v1/reservations/{self.reservation_id}/start",
            body=body,
        )
        self.started = True
        self._start_heartbeat()
        return response

    def heartbeat(
        self, *, process_pid: int | None = None, process_pgid: int | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if process_pid is not None:
            body["process_pid"] = int(process_pid)
        if process_pgid is not None:
            body["process_pgid"] = int(process_pgid)
        return self.client.request(
            "POST", f"/v1/reservations/{self.reservation_id}/heartbeat", body=body
        )

    def attach_process(self, process_pid: int, process_pgid: int | None = None) -> None:
        """Bind the lease to the real CLI child so a crashed owner cannot free it early."""
        if not self.started:
            self.start(process_pid=process_pid, process_pgid=process_pgid)
            return
        self.heartbeat(process_pid=process_pid, process_pgid=process_pgid)

    def _start_heartbeat(self) -> None:
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_stop.clear()

        def beat() -> None:
            while not self._heartbeat_stop.wait(HEARTBEAT_INTERVAL_SECONDS):
                try:
                    self.heartbeat()
                except BrokerError:
                    # A daemon restart is recoverable. Persisted process identity
                    # keeps the provider locked while this request cannot land.
                    time.sleep(0)

        self._heartbeat_thread = threading.Thread(
            target=beat,
            name=f"lqb-heartbeat-{self.reservation_id[:8]}",
            daemon=True,
        )
        self._heartbeat_thread.start()

    def _stop_heartbeat(self) -> None:
        self._heartbeat_stop.set()
        thread = self._heartbeat_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)

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
        self._stop_heartbeat()
        try:
            response = self.client.request(
                "POST", f"/v1/reservations/{self.reservation_id}/complete", body=body
            )
            self.settled = True
            return response
        finally:
            self._stop_heartbeat()

    def cancel(self, reason: str | None = None) -> dict[str, Any]:
        """Release the hold without recording a run."""
        body = {"reason": str(reason)[:500]} if reason else {}
        self._stop_heartbeat()
        try:
            response = self.client.request(
                "POST", f"/v1/reservations/{self.reservation_id}/cancel", body=body
            )
            self.settled = True
            return response
        finally:
            self._stop_heartbeat()


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

    def handshake(self) -> BrokerHandshake:
        """Compare this client with the daemon before dispatching new work."""
        health = self.health()
        raw_version = health.get("broker_version")
        broker_version = str(raw_version).strip() if raw_version is not None else ""
        if not broker_version:
            return BrokerHandshake(
                client_version=CLIENT_BROKER_VERSION,
                broker_version=None,
                status="broker_restart_required",
                message=(
                    "the broker is running an older release without version handshake; "
                    "restart the broker"
                ),
            )

        client_key = _version_key(CLIENT_BROKER_VERSION)
        broker_key = _version_key(broker_version)
        if client_key is None or broker_key is None:
            return BrokerHandshake(
                client_version=CLIENT_BROKER_VERSION,
                broker_version=broker_version,
                status="broker_restart_required",
                message=(
                    f"cannot compare client {CLIENT_BROKER_VERSION} with broker "
                    f"{broker_version}; restart the broker"
                ),
            )
        if broker_version == CLIENT_BROKER_VERSION:
            return BrokerHandshake(
                client_version=CLIENT_BROKER_VERSION,
                broker_version=broker_version,
                status="compatible",
                message=f"client and broker are both {broker_version}",
            )
        if client_key >= broker_key:
            return BrokerHandshake(
                client_version=CLIENT_BROKER_VERSION,
                broker_version=broker_version,
                status="broker_restart_required",
                message=(
                    f"client {CLIENT_BROKER_VERSION} is newer than broker {broker_version}; "
                    "restart the broker"
                ),
            )
        return BrokerHandshake(
            client_version=CLIENT_BROKER_VERSION,
            broker_version=broker_version,
            status="client_update_required",
            message=(
                f"broker {broker_version} is newer than client {CLIENT_BROKER_VERSION}; "
                "update this client"
            ),
        )

    def ensure_compatible(self) -> BrokerHandshake:
        """Fail closed unless the public version handshake is an exact match."""
        handshake = self.handshake()
        if not handshake.compatible:
            raise BrokerVersionMismatch(handshake)
        return handshake

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
        broker picks among them by projected quota headroom.
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
        self.ensure_compatible()
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
        provider = str(response.get("recommended") or reservation.get("provider_id") or "")
        return Lease(
            client=self,
            reservation_id=str(reservation["reservation_id"]),
            provider=provider,
            decision_id=str(response.get("decision_id") or ""),
            task_id=str(response.get("task_id") or task["task_id"]),
            expires_at=str(reservation.get("expires_at") or ""),
            model=_selected_model(response, provider),
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


@dataclass(frozen=True)
class RunStream:
    """What one CLI run said about itself, read from its structured output.

    ``usage`` is ready to hand to :meth:`Lease.complete` unchanged, and empty
    when the run reported nothing — which is a different fact from "it cost
    nothing", and the broker records it as such.
    """

    answer: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    model: str | None = None
    events_parsed: int = 0


def parse_run_stream(provider: str, stdout: str) -> RunStream:
    """Read a vendor CLI's structured run output: the answer and what it cost.

    Every caller needs both, from the same bytes, and getting the second one
    wrong is invisible. Before this existed each project extracted the answer
    itself and reported usage only for the vendors whose envelope it happened to
    understand, which on the live ledger meant 96% of Agy runs and 90% of Codex
    runs settling as "no tokens" — indistinguishable, to anything reading the
    ledger later, from runs that were free.

    The field maps are the ones this repository validated against captured live
    output (``adapters/parsers.py``, and the fixtures beside its tests), which is
    the only reason they can be trusted: every one of them was wrong at some
    point in a way that produced plausible small numbers rather than an error.

    **The CLI has to be asked for this output.** In plain-text mode there is no
    usage anywhere in the stream, and no parser recovers what was never printed:

    * ``codex exec --json``
    * ``agy --print <prompt> --output-format stream-json``
    * ``claude -p --output-format json`` (or ``stream-json``)
    * ``grok --single <prompt> --output-format json``

    An unrecognised provider, unparseable output, or a run that simply said
    nothing all return an empty :class:`RunStream` rather than raising. This
    sits between a finished run and its settlement; refusing to parse must not
    be the reason a hold leaks.
    """
    reader = _STREAM_READERS.get((provider or "").strip().lower())
    if reader is None:
        return RunStream()

    answer: str | None = None
    usage: dict[str, int] = {}
    model: str | None = None
    parsed = 0

    for line in (stdout or "").splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        parsed += 1
        # Later wins for all three: these streams restate the running total and
        # end with the final answer, so the last statement is the complete one.
        found_answer, found_usage, found_model = reader(event)
        if found_answer is not None:
            answer = found_answer
        if found_usage is not None:
            usage = found_usage
        if found_model:
            model = found_model

    return RunStream(answer=answer, usage=usage, model=model, events_parsed=parsed)


_StreamFields = tuple[str | None, dict[str, int] | None, str | None]


def _codex_event(event: Mapping[str, Any]) -> _StreamFields:
    """``codex exec --json``: session events nest their payload under ``msg``."""
    nested = event.get("msg")
    payload: Mapping[str, Any] = nested if isinstance(nested, Mapping) else event

    usage = None
    block = payload.get("total_token_usage") or payload.get("last_token_usage")
    if isinstance(block, Mapping):
        usage = _usage_fields(
            block,
            input_tokens="input_tokens",
            output_tokens="output_tokens",
            cache_read_tokens="cached_input_tokens",
            reasoning_tokens="reasoning_output_tokens",
            total_tokens="total_tokens",
        )

    answer = None
    message = payload.get("last_agent_message")
    if isinstance(message, str) and message:
        answer = message
    elif payload.get("type") == "agent_message":
        candidate = payload.get("message")
        if isinstance(candidate, str) and candidate:
            answer = candidate

    model = None
    for key in ("model", "model_name"):
        candidate = payload.get(key)
        if isinstance(candidate, str) and candidate:
            model = candidate
    return answer, usage, model


def _agy_event(event: Mapping[str, Any]) -> _StreamFields:
    """``--output-format stream-json``: each line names its event and nests it.

    Both envelopes are read because Agy emits both, and looking only at the top
    level is how this returned zero tokens for every real run once already.
    """
    name = event.get("event") or event.get("type")
    nested = event.get(name) if isinstance(name, str) else None
    bodies: list[Mapping[str, Any]] = [event]
    if isinstance(nested, Mapping):
        bodies.append(nested)

    usage = None
    model = None
    for body in bodies:
        block = body.get("usage")
        if not isinstance(block, Mapping) and {"input_tokens", "total_tokens"} <= set(body):
            block = body
        if isinstance(block, Mapping):
            usage = _usage_fields(
                block,
                input_tokens="input_tokens",
                output_tokens="output_tokens",
                thinking_tokens="thinking_tokens",
                cache_read_tokens="cache_read_tokens",
                total_tokens="total_tokens",
            )
        candidate = body.get("model")
        if isinstance(candidate, str) and candidate:
            model = candidate

    answer = None
    if name == "result":
        text = event.get("result")
        if isinstance(text, str):
            answer = text
        elif isinstance(nested, Mapping) and isinstance(nested.get("response"), str):
            answer = nested["response"]
    return answer, usage, model


def _claude_event(event: Mapping[str, Any]) -> _StreamFields:
    """``--output-format json`` and ``stream-json`` share one envelope."""
    message = event.get("message")
    block = event.get("usage")
    if not isinstance(block, Mapping) and isinstance(message, Mapping):
        block = message.get("usage")
    usage = None
    if isinstance(block, Mapping):
        usage = _usage_fields(
            block,
            input_tokens="input_tokens",
            output_tokens="output_tokens",
            cache_read_tokens="cache_read_input_tokens",
            cache_write_tokens="cache_creation_input_tokens",
        )

    candidate = event.get("model")
    if not isinstance(candidate, str) and isinstance(message, Mapping):
        candidate = message.get("model")
    model = candidate if isinstance(candidate, str) and candidate else None

    answer = None
    if event.get("type") == "result":
        text = event.get("result")
        if isinstance(text, str):
            answer = text
    return answer, usage, model


def _grok_event(event: Mapping[str, Any]) -> _StreamFields:
    """``--output-format json``: one envelope, camelCase usage."""
    block = event.get("usage")
    usage = None
    if isinstance(block, Mapping):
        usage = _usage_fields(
            block,
            input_tokens="inputTokens",
            output_tokens="outputTokens",
            cache_read_tokens="cachedReadTokens",
            reasoning_tokens="reasoningTokens",
            total_tokens="totalTokens",
            model_calls="modelCalls",
        )

    answer = None
    for key in ("result", "response", "text"):
        text = event.get(key)
        if isinstance(text, str) and text:
            answer = text
            break

    candidate = event.get("model")
    model = candidate if isinstance(candidate, str) and candidate else None
    return answer, usage, model


#: Provider id (as the broker names it) to the reader for that CLI's output.
_STREAM_READERS = {
    "codex": _codex_event,
    "agy": _agy_event,
    "claude": _claude_event,
    "grok": _grok_event,
}


def _usage_fields(block: Mapping[str, Any], **sources: str) -> dict[str, int]:
    """Pull ``TokenUsage`` fields out of one vendor's usage block.

    Absent keys are dropped rather than sent as ``0``: the broker distinguishes
    "the vendor does not report this" from "this was zero", and filling in zeros
    here would erase that distinction at the only point where it is still known.
    """
    usage: dict[str, int] = {}
    for target, source in sources.items():
        if source not in block:
            continue
        try:
            usage[target] = max(0, int(block.get(source) or 0))
        except (TypeError, ValueError):
            continue
    return usage


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


def _selected_model(response: Mapping[str, Any], provider: str) -> str:
    """The winning candidate's ``model``, or ``""`` when the broker chose none.

    Read from the candidate rather than from the reservation because the pool
    choice belongs to the routing decision: the reservation records *which*
    pool is held, and the model is how a caller lands in it.
    """
    if not provider:
        return ""
    for candidate in _candidates(response):
        if str(candidate.get("provider") or "") == provider:
            return str(candidate.get("model") or "")
    return ""


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
