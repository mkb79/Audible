"""Register a new Audible device for an Amazon or a pre-Amazon account.

Amazon accounts register with a device code. :class:`DeviceCodeLogin`
creates a code pair, the user confirms the public code on
``https://www.amazon.<tld>/code``, and polling ``/auth/register`` returns the
device credentials once the code is confirmed. Pre-Amazon accounts, which
sign in with an Audible username and exist on the DE, US and UK
marketplaces only, use :class:`ExternalLogin`: the user signs in through a
browser and hands the URL the browser ended on back to the library.
:func:`create_login` picks the class from the account type.

Both classes end with a registered device, so ``FINISHED`` always means that
:meth:`~DeviceCodeLogin.result` returns a ready
:class:`~audible.auth.Authenticator`. The library never prints, reads input
or opens a browser; showing the code or the URL is the caller's job.

The methods follow :class:`subprocess.Popen` and :class:`asyncio.Future`:
``status`` is read without I/O, ``poll()`` sends at most one request and
never sleeps, ``wait()`` returns once the login has ended, and ``result()``
never blocks. Every method that talks to the network has an ``async_``
counterpart. One caller at a time may drive a login; any number of callers
may read its status. Nothing is persisted: a login lives as long as its
object.
"""

from __future__ import annotations

import asyncio
import contextlib
import enum
import logging
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, NoReturn, overload

import httpx

from ._device import IPHONE
from ._registration import (
    PRE_AMAZON_DOMAINS,
    CodePair,
    PollOutcome,
    RequestSpec,
    authorization_code_registration_request,
    build_device_serial,
    classify_poll,
    code_pair_registration_request,
    code_pair_request,
    create_code_verifier,
    error_code,
    extract_authorization_code,
    parse_code_pair,
    pre_amazon_login_url,
    registration_credentials,
    retry_delay,
    verification_url,
)
from .auth import Authenticator
from .crypto_provider import get_crypto_providers
from .exceptions import (
    LoginAbortedError,
    LoginError,
    LoginExpiredError,
    LoginFailedError,
    LoginStateError,
)
from .utils import test_convert


if TYPE_CHECKING:
    from collections.abc import Iterator

    from .crypto_provider.protocols import CryptoProvider
    from .localization import Locale


logger = logging.getLogger("audible.login")

_TIMEOUT = httpx.Timeout(25.0)


class _Clock:
    """Time source of the login classes; the tests replace :data:`_clock`."""

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float, wakeup: threading.Event) -> None:
        wakeup.wait(seconds)

    async def async_sleep(self, seconds: float, wakeup: asyncio.Event) -> None:
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(wakeup.wait(), seconds)


_clock = _Clock()


def _reraise(error: LoginError) -> NoReturn:
    """Raise a stored error.

    pydoclint matches a Raises section against literal ``raise`` statements,
    so a public method re-raising a stored error does it through here.
    """
    raise error


class LoginStatus(enum.Enum):
    """The state of a login."""

    PENDING = "pending"
    """Waiting for the user, or for the next polling attempt."""
    FINISHED = "finished"
    """The device is registered; ``result()`` returns its authenticator."""
    FAILED = "failed"
    """Amazon or Audible rejected the login, or the network failed."""
    EXPIRED = "expired"
    """The device code expired before the user confirmed it."""
    ABORTED = "aborted"
    """The login was cancelled."""


@dataclass(frozen=True)
class DeviceCodePrompt:
    """What the user needs to confirm a device code.

    Attributes:
        public_code: The code the user enters.
        verification_url: The page on which the user enters the code.
        expires_in: Seconds the code stays valid after
            :meth:`DeviceCodeLogin.start` returned.
    """

    public_code: str
    verification_url: str
    expires_in: float


@dataclass(frozen=True)
class ExternalLoginPrompt:
    """What the user needs to sign in with a browser.

    Attributes:
        login_url: The page on which the user signs in. Afterwards the
            browser shows a "page not found" error; the URL in its address
            bar is what :meth:`ExternalLogin.complete` expects.
    """

    login_url: str


class _Login:
    """Status and result handling shared by both login classes."""

    def __init__(
        self,
        locale: str | Locale,
        *,
        serial: str | None,
        crypto_provider: CryptoProvider | type[CryptoProvider] | None,
        client: httpx.Client | None,
        async_client: httpx.AsyncClient | None,
        with_username: bool,
    ) -> None:
        self._locale: Locale = test_convert("locale", locale)
        self._device = IPHONE
        self._serial = serial or build_device_serial()
        # Resolved here, so that a library that is not installed fails before
        # a device is registered rather than after.
        self._crypto_provider = (
            None if crypto_provider is None else get_crypto_providers(crypto_provider)
        )
        self._client = client
        self._async_client = async_client
        self._with_username = with_username
        self._status = LoginStatus.PENDING
        self._started = False
        self._authenticator: Authenticator | None = None
        self._error: LoginError | None = None
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(locale={self._locale.country_code!r}, "
            f"status={self._status.name})"
        )

    @property
    def status(self) -> LoginStatus:
        """The current state of the login. Reading it sends no request."""
        return self._status

    @property
    def locale(self) -> Locale:
        """The marketplace the device is registered with."""
        return self._locale

    @property
    def serial(self) -> str:
        """The serial of the device to register."""
        return self._serial

    def result(self) -> Authenticator:
        """Return the authenticator of the registered device.

        Never blocks and never sends a request. If the login has ended
        without a device, the error that ended it is raised again:
        :exc:`~audible.exceptions.LoginFailedError`,
        :exc:`~audible.exceptions.LoginExpiredError` or
        :exc:`~audible.exceptions.LoginAbortedError`.

        Returns:
            The authenticator, once the status is ``FINISHED``.

        Raises:
            LoginStateError: If the login is still pending.
        """
        with self._lock:
            authenticator, error = self._authenticator, self._error
        if authenticator is not None:
            return authenticator
        if error is None:
            raise LoginStateError("The login is still pending.")
        _reraise(error)

    def cancel(self) -> bool:
        """Cancel the login if it is still pending.

        The status changes to ``ABORTED`` at once. A sleeping ``wait()`` or
        ``async_wait()`` wakes up immediately, also when called from another
        thread; either finishes a request in progress first. Cancelling the
        task that runs ``async_wait()`` stops it at once instead. A
        registration request already sent cannot be taken back: should
        Amazon register the device anyway, it appears in the device list of
        the account without credentials and has to be removed there.

        Returns:
            ``True`` if the login was cancelled, ``False`` if it had already
            ended.
        """
        return self._end(
            LoginStatus.ABORTED, error=LoginAbortedError("The login was cancelled.")
        )

    def _end(
        self,
        status: LoginStatus,
        *,
        error: LoginError | None = None,
        authenticator: Authenticator | None = None,
    ) -> bool:
        """Move to a final status. The first one wins; later calls are ignored."""
        with self._lock:
            if self._status is not LoginStatus.PENDING:
                return False
            self._error = error
            self._authenticator = authenticator
            # Last, so that a reader seeing the final status sees its result.
            self._status = status
        logger.info("Login ended with status %s: %s", status.name, error or "")
        return True

    def _fail(self, error: LoginFailedError) -> None:
        self._end(LoginStatus.FAILED, error=error)

    @contextlib.contextmanager
    def _ending_on_failure(self) -> Iterator[None]:
        """End the login if the step inside does not complete.

        A :exc:`LoginFailedError` ends it as ``FAILED``; if the login had
        already ended, typically by :meth:`cancel` while a request was in
        flight, the error that ended it is raised instead. Anything else, such
        as ``KeyboardInterrupt`` or the cancellation of the awaiting task,
        ends it as ``ABORTED``: the request may have reached Amazon, so the
        step cannot simply be repeated.
        """
        try:
            yield
        except LoginFailedError as error:
            if not self._end(LoginStatus.FAILED, error=error) and (
                self._error is not None
            ):
                raise self._error from error
            raise
        except BaseException:
            self._end(
                LoginStatus.ABORTED,
                error=LoginAbortedError("The login was interrupted."),
            )
            raise

    def _raise_if_ended(self) -> None:
        """Raise the error that ended the login, if it ended without a device."""
        if self._status is not LoginStatus.PENDING and self._error is not None:
            _reraise(self._error)

    def _claim_start(self) -> None:
        """Mark the login as started, so that a second ``start()`` fails."""
        with self._lock:
            if self._started or self._status is not LoginStatus.PENDING:
                raise LoginStateError("The login was already started or has ended.")
            self._started = True

    def _require_started(self) -> None:
        if not self._started and self._status is LoginStatus.PENDING:
            raise LoginStateError("Call start() first.")

    def _finish(self, response: httpx.Response) -> None:
        """Turn a registration response into the authenticator."""
        try:
            credentials = registration_credentials(response, self._serial)
            authenticator = Authenticator.from_dict(
                {**credentials, "with_username": self._with_username},
                locale=self._locale,
                crypto_provider=self._crypto_provider,
            )
        except LoginFailedError as error:
            self._fail(error)
            return
        except (TypeError, ValueError) as exc:
            self._fail(LoginFailedError(f"Invalid registration credentials: {exc}"))
            return
        if not self._end(LoginStatus.FINISHED, authenticator=authenticator):
            logger.warning(
                "Amazon registered the device after the login had ended with "
                "status %s. Remove it from the device list of the account.",
                self._status.name,
            )

    def _send(self, request: RequestSpec) -> httpx.Response:
        if self._client is not None:
            return self._client.post(
                request.url, json=request.body, headers=request.headers
            )
        with httpx.Client(timeout=_TIMEOUT) as client:
            return client.post(request.url, json=request.body, headers=request.headers)

    async def _async_send(self, request: RequestSpec) -> httpx.Response:
        if self._async_client is not None:
            return await self._async_client.post(
                request.url, json=request.body, headers=request.headers
            )
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            return await client.post(
                request.url, json=request.body, headers=request.headers
            )


class DeviceCodeLogin(_Login):
    """Register a new device for an Amazon account with a device code.

    Construction sends no request. :meth:`start` creates the code pair and
    returns the code to show; the user then confirms it on the verification
    page while :meth:`poll` or :meth:`wait` ask Amazon whether that has
    happened. Amazon answers with the device credentials as soon as it has,
    which also registers the device.

    Args:
        locale: The ``country_code`` or :class:`~audible.localization.Locale`
            of the marketplace to register with.
        serial: The device serial. If ``None``, a random one is created.
        crypto_provider: Optional crypto provider for the resulting
            authenticator (class or instance). If its library is not
            installed, :exc:`ImportError` is raised here, before any request.
        client: HTTP client for the sync methods. If ``None``, each request
            uses a short-lived client with a 25-second timeout. A client of
            your own needs a timeout too, or a stalled connection blocks the
            login.
        async_client: HTTP client for the async methods. If ``None``, each
            request uses a short-lived client with a 25-second timeout.
    """

    def __init__(
        self,
        locale: str | Locale,
        *,
        serial: str | None = None,
        crypto_provider: CryptoProvider | type[CryptoProvider] | None = None,
        client: httpx.Client | None = None,
        async_client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            locale,
            serial=serial,
            crypto_provider=crypto_provider,
            client=client,
            async_client=async_client,
            with_username=False,
        )
        self._code_pair: CodePair | None = None
        self._expires_at = 0.0
        self._next_poll_at = 0.0
        self._in_flight = False
        self._failures = 0
        self._wakeup = threading.Event()
        self._async_wakeups: list[tuple[asyncio.AbstractEventLoop, asyncio.Event]] = []

    @property
    def next_poll_delay(self) -> float:
        """Seconds until :meth:`poll` sends its next request.

        ``0.0`` if a request is due now or the login is not pending.
        """
        if self._status is not LoginStatus.PENDING or self._code_pair is None:
            return 0.0
        return max(0.0, self._next_poll_at - _clock.monotonic())

    def start(self) -> DeviceCodePrompt:
        """Create the code pair the user has to confirm.

        A login can be started once; a second call raises
        :exc:`~audible.exceptions.LoginStateError`.

        Returns:
            The code to show and where to enter it.

        Raises:
            LoginFailedError: If the network failed or Amazon refused to
                create a code pair. The status is ``FAILED`` then.
        """
        self._claim_start()
        started_at = _clock.monotonic()
        request = code_pair_request(self._device, self._locale.domain, self._serial)
        with self._ending_on_failure():
            try:
                response = self._send(request)
            except httpx.RequestError as exc:
                raise LoginFailedError(f"Network error: {exc}") from exc
            return self._accept_code_pair(response, started_at)

    async def async_start(self) -> DeviceCodePrompt:
        """Create the code pair the user has to confirm.

        Async counterpart of :meth:`start`.

        A login can be started once; a second call raises
        :exc:`~audible.exceptions.LoginStateError`.

        Returns:
            The code to show and where to enter it.

        Raises:
            LoginFailedError: If the network failed or Amazon refused to
                create a code pair. The status is ``FAILED`` then.
        """
        self._claim_start()
        started_at = _clock.monotonic()
        request = code_pair_request(self._device, self._locale.domain, self._serial)
        with self._ending_on_failure():
            try:
                response = await self._async_send(request)
            except httpx.RequestError as exc:
                raise LoginFailedError(f"Network error: {exc}") from exc
            return self._accept_code_pair(response, started_at)

    def _accept_code_pair(
        self, response: httpx.Response, started_at: float
    ) -> DeviceCodePrompt:
        code_pair = parse_code_pair(response)
        self._raise_if_ended()
        now = _clock.monotonic()
        self._code_pair = code_pair
        # Counted from before the request, so the code never outlives Amazon's.
        self._expires_at = started_at + code_pair.expires_in
        self._next_poll_at = now + code_pair.interval
        logger.info("Created a device code for %s.", self._locale.country_code)
        return DeviceCodePrompt(
            code_pair.public_code,
            verification_url(self._locale.domain),
            self._expires_at - now,
        )

    def poll(self) -> LoginStatus:
        """Ask Amazon once whether the code was confirmed, if that is due.

        Sends at most one request and never sleeps. Before the next attempt
        is due, it returns the current status without a request, so it may
        be called as often as convenient. :meth:`start` must have been
        called before.

        Returns:
            The status after the attempt.
        """
        request = self._due_request()
        if request is None:
            return self._status
        response: httpx.Response | None
        try:
            try:
                response = self._send(request)
            except httpx.RequestError as exc:
                logger.warning("Network error while polling: %s", exc)
                response = None
            with self._ending_on_failure():
                return self._handle_poll(response)
        finally:
            # Released only now, so that a second caller finds the next
            # attempt already scheduled instead of repeating this one.
            self._in_flight = False

    async def async_poll(self) -> LoginStatus:
        """Ask Amazon once whether the code was confirmed, if that is due.

        Async counterpart of :meth:`poll`.

        Returns:
            The status after the attempt.
        """
        request = self._due_request()
        if request is None:
            return self._status
        response: httpx.Response | None
        try:
            try:
                response = await self._async_send(request)
            except httpx.RequestError as exc:
                logger.warning("Network error while polling: %s", exc)
                response = None
            with self._ending_on_failure():
                return self._handle_poll(response)
        finally:
            # Released only now, so that a second caller finds the next
            # attempt already scheduled instead of repeating this one.
            self._in_flight = False

    def _due_request(self) -> RequestSpec | None:
        if self._status is not LoginStatus.PENDING:
            return None
        if self._code_pair is None:
            raise LoginStateError("Call start() first.")
        now = _clock.monotonic()
        if now >= self._expires_at:
            self._end(
                LoginStatus.EXPIRED,
                error=LoginExpiredError(
                    "The device code expired before it was confirmed."
                ),
            )
            return None
        # A second poll() while a request is in flight must not send another,
        # and neither may a poll() that a concurrent cancel() overtook.
        with self._lock:
            if (
                self._status is not LoginStatus.PENDING
                or now < self._next_poll_at
                or self._in_flight
            ):
                return None
            self._in_flight = True
        return code_pair_registration_request(
            self._device, self._locale.domain, self._serial, self._code_pair
        )

    def _handle_poll(self, response: httpx.Response | None) -> LoginStatus:
        if response is None:
            return self._retry(None)
        outcome = classify_poll(response)
        if outcome is PollOutcome.REGISTERED:
            self._finish(response)
            return self._status
        if self._status is not LoginStatus.PENDING:
            return self._status
        if outcome is PollOutcome.RETRY:
            return self._retry(response)
        if outcome is PollOutcome.PENDING:
            self._failures = 0
            self._schedule(self._interval)
        else:
            self._fail(
                LoginFailedError(
                    f"Amazon rejected the device code (HTTP {response.status_code}).",
                    status_code=response.status_code,
                    error_code=error_code(response),
                )
            )
        return self._status

    def _retry(self, response: httpx.Response | None) -> LoginStatus:
        if self._status is LoginStatus.PENDING:
            self._failures += 1
            self._schedule(retry_delay(response, self._interval, self._failures))
        return self._status

    @property
    def _interval(self) -> float:
        return self._code_pair.interval if self._code_pair else 0.0

    def _schedule(self, delay: float) -> None:
        self._next_poll_at = _clock.monotonic() + delay

    def _sleep_time(self, deadline: float | None) -> float:
        """Return how long to sleep before the next attempt or the deadline."""
        wake_at = min(self._next_poll_at, self._expires_at)
        if deadline is not None:
            wake_at = min(wake_at, deadline)
        return max(0.0, wake_at - _clock.monotonic())

    @staticmethod
    def _past(deadline: float | None) -> bool:
        return deadline is not None and _clock.monotonic() >= deadline

    def wait(self, timeout: float | None = None) -> Authenticator:
        """Poll until the login ends and return the authenticator.

        :meth:`start` must have been called before. If the login ends
        without a device, the error :meth:`result` raises propagates. No
        attempt starts once the timeout has passed; a request in progress is
        finished first.

        Args:
            timeout: Seconds to wait at most. ``None`` waits until the device
                code expires.

        Returns:
            The authenticator of the registered device.

        Raises:
            TimeoutError: If ``timeout`` passed first. The login stays
                pending and can be waited for again.
        """
        self._require_started()
        deadline = None if timeout is None else _clock.monotonic() + timeout
        while not self._past(deadline) and self.poll() is LoginStatus.PENDING:
            _clock.sleep(self._sleep_time(deadline), self._wakeup)
        if self._status is LoginStatus.PENDING:
            raise TimeoutError("The login is still pending.")
        return self.result()

    async def async_wait(
        self,
        timeout: float | None = None,  # noqa: ASYNC109 - unlike asyncio.timeout, keeps the login pending
    ) -> Authenticator:
        """Poll until the login ends and return the authenticator.

        Async counterpart of :meth:`wait`. Cancelling the awaiting task
        cancels the login, while ``timeout`` leaves it pending. No attempt
        starts once the timeout has passed; a request in progress is
        finished first.

        Args:
            timeout: Seconds to wait at most. ``None`` waits until the device
                code expires.

        Returns:
            The authenticator of the registered device.

        Raises:
            TimeoutError: If ``timeout`` passed first. The login stays
                pending and can be waited for again.
            asyncio.CancelledError: If the awaiting task was cancelled.
        """
        self._require_started()
        deadline = None if timeout is None else _clock.monotonic() + timeout
        wakeup = (asyncio.get_running_loop(), asyncio.Event())
        with self._lock:
            self._async_wakeups.append(wakeup)
        try:
            while (
                not self._past(deadline)
                and await self.async_poll() is LoginStatus.PENDING
            ):
                await _clock.async_sleep(self._sleep_time(deadline), wakeup[1])
        except asyncio.CancelledError:
            self.cancel()
            raise
        finally:
            with self._lock:
                self._async_wakeups.remove(wakeup)
        if self._status is LoginStatus.PENDING:
            raise TimeoutError("The login is still pending.")
        return self.result()

    def _end(
        self,
        status: LoginStatus,
        *,
        error: LoginError | None = None,
        authenticator: Authenticator | None = None,
    ) -> bool:
        ended = super()._end(status, error=error, authenticator=authenticator)
        self._wakeup.set()
        with self._lock:
            wakeups = list(self._async_wakeups)
        for loop, event in wakeups:
            # The loop may already be closed if its async_wait() was abandoned.
            with contextlib.suppress(RuntimeError):
                loop.call_soon_threadsafe(event.set)
        return ended


class ExternalLogin(_Login):
    """Register a new device for a pre-Amazon account through a browser.

    Pre-Amazon accounts sign in with an Audible username and exist on the
    DE, US and UK marketplaces only. Construction sends no request.
    :meth:`start` returns the URL to open in a browser. After signing in,
    the browser lands on a "page not found" error; its address is handed to
    :meth:`complete`, which registers the device.

    Args:
        locale: The ``country_code`` or :class:`~audible.localization.Locale`
            of the marketplace to register with.
        serial: The device serial. If ``None``, a random one is created.
        crypto_provider: Optional crypto provider for the resulting
            authenticator (class or instance). If its library is not
            installed, :exc:`ImportError` is raised here, before any request.
        client: HTTP client for :meth:`complete`. If ``None``, a short-lived
            client with a 25-second timeout is used. A client of your own
            needs a timeout too, or a stalled connection blocks the login.
        async_client: HTTP client for :meth:`async_complete`. If ``None``, a
            short-lived client with a 25-second timeout is used.

    Raises:
        ValueError: If the marketplace has no pre-Amazon accounts.
    """

    def __init__(
        self,
        locale: str | Locale,
        *,
        serial: str | None = None,
        crypto_provider: CryptoProvider | type[CryptoProvider] | None = None,
        client: httpx.Client | None = None,
        async_client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            locale,
            serial=serial,
            crypto_provider=crypto_provider,
            client=client,
            async_client=async_client,
            with_username=True,
        )
        if self._locale.domain not in PRE_AMAZON_DOMAINS:
            raise ValueError(
                "Pre-Amazon accounts exist on the DE, US and UK marketplaces only."
            )
        self._code_verifier = ""
        self._submitted = False

    def start(self) -> ExternalLoginPrompt:
        """Prepare the browser sign-in. Sends no request.

        Returns:
            The URL to open in a browser.
        """
        self._claim_start()
        self._code_verifier = create_code_verifier()
        return ExternalLoginPrompt(
            pre_amazon_login_url(
                self._device, self._locale, self._serial, self._code_verifier
            )
        )

    def complete(self, redirect_url: str) -> Authenticator:
        """Register the device with the URL the browser ended on.

        A URL that is not the expected page raises :exc:`ValueError` and
        leaves the login pending, so the call can be repeated with the right
        URL. Without :meth:`start`, or once the login has ended, it raises
        :exc:`~audible.exceptions.LoginStateError`.

        Args:
            redirect_url: The full URL from the browser's address bar after
                signing in.

        Returns:
            The authenticator of the registered device.

        Raises:
            LoginFailedError: If the network failed or Audible refused the
                registration. The status is ``FAILED`` then.
        """
        request = self._registration_request(redirect_url)
        with self._ending_on_failure():
            try:
                response = self._send(request)
            except httpx.RequestError as exc:
                raise LoginFailedError(f"Network error: {exc}") from exc
            self._finish(response)
        return self.result()

    async def async_complete(self, redirect_url: str) -> Authenticator:
        """Register the device with the URL the browser ended on.

        Async counterpart of :meth:`complete`.

        A URL that is not the expected page raises :exc:`ValueError` and
        leaves the login pending, so the call can be repeated with the right
        URL. Without :meth:`start`, or once the login has ended, it raises
        :exc:`~audible.exceptions.LoginStateError`.

        Args:
            redirect_url: The full URL from the browser's address bar after
                signing in.

        Returns:
            The authenticator of the registered device.

        Raises:
            LoginFailedError: If the network failed or Audible refused the
                registration. The status is ``FAILED`` then.
        """
        request = self._registration_request(redirect_url)
        with self._ending_on_failure():
            try:
                response = await self._async_send(request)
            except httpx.RequestError as exc:
                raise LoginFailedError(f"Network error: {exc}") from exc
            self._finish(response)
        return self.result()

    def _registration_request(self, redirect_url: str) -> RequestSpec:
        self._require_started()
        with self._lock:
            if self._status is not LoginStatus.PENDING or self._submitted:
                raise LoginStateError("The login is no longer waiting for a URL.")
            authorization_code = extract_authorization_code(
                redirect_url, self._locale.domain
            )
            # The code is single-use; a second complete() must not send it again.
            self._submitted = True
        return authorization_code_registration_request(
            self._device,
            self._locale.domain,
            self._serial,
            authorization_code,
            self._code_verifier,
        )


@overload
def create_login(
    locale: str | Locale,
    *,
    with_username: Literal[False] = False,
    serial: str | None = None,
    crypto_provider: CryptoProvider | type[CryptoProvider] | None = None,
) -> DeviceCodeLogin: ...


@overload
def create_login(
    locale: str | Locale,
    *,
    with_username: Literal[True],
    serial: str | None = None,
    crypto_provider: CryptoProvider | type[CryptoProvider] | None = None,
) -> ExternalLogin: ...


@overload
def create_login(
    locale: str | Locale,
    *,
    with_username: bool,
    serial: str | None = None,
    crypto_provider: CryptoProvider | type[CryptoProvider] | None = None,
) -> DeviceCodeLogin | ExternalLogin: ...


def create_login(
    locale: str | Locale,
    *,
    with_username: bool = False,
    serial: str | None = None,
    crypto_provider: CryptoProvider | type[CryptoProvider] | None = None,
) -> DeviceCodeLogin | ExternalLogin:
    """Create the login that registers a new device for the account type.

    Sends no request; the returned login is started by the caller.

    Args:
        locale: The ``country_code`` or :class:`~audible.localization.Locale`
            of the marketplace to register with.
        with_username: ``True`` for a pre-Amazon account, which signs in with
            an Audible username (DE, US and UK only); ``False`` for an Amazon
            account.
        serial: The device serial. If ``None``, a random one is created.
        crypto_provider: Optional crypto provider for the resulting
            authenticator (class or instance). If its library is not
            installed, :exc:`ImportError` is raised here, before any request.

    Returns:
        A :class:`DeviceCodeLogin` for an Amazon account, an
        :class:`ExternalLogin` for a pre-Amazon account.
    """
    if with_username:
        return ExternalLogin(locale, serial=serial, crypto_provider=crypto_provider)
    return DeviceCodeLogin(locale, serial=serial, crypto_provider=crypto_provider)


__all__ = [
    "DeviceCodeLogin",
    "DeviceCodePrompt",
    "ExternalLogin",
    "ExternalLoginPrompt",
    "LoginStatus",
    "create_login",
]
