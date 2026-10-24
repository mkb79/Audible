"""Tests for registering a new device with DeviceCodeLogin and ExternalLogin."""

from __future__ import annotations

import asyncio
import base64
import functools
import hashlib
import json
import re
import threading
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

import audible
import audible.login as login_mod
from audible._device import IPHONE
from audible._registration import build_client_id
from audible.auth import (
    Authenticator,
    _refresh_token_request_body,
    refresh_website_cookies,
)
from audible.crypto_provider import PycryptodomeProvider
from audible.exceptions import (
    LoginAbortedError,
    LoginExpiredError,
    LoginFailedError,
    LoginStateError,
)
from audible.login import (
    DeviceCodeLogin,
    ExternalLogin,
    LoginStatus,
    create_login,
)


SERIAL = "0123456789ABCDEF0123456789ABCDEF"
INTERVAL = 5.0

Reply = httpx.Response | Callable[[httpx.Request], httpx.Response]


class FakeClock:
    """Replaces the login clock; sleeping only advances the time."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []
        self.on_read: Callable[[], object] | None = None

    def monotonic(self) -> float:
        if self.on_read is not None:
            hook, self.on_read = self.on_read, None
            hook()
        return self.now

    def sleep(self, seconds: float, wakeup: Any) -> None:
        self.slept.append(seconds)
        self.now += seconds

    async def async_sleep(self, seconds: float, wakeup: Any) -> None:
        self.slept.append(seconds)
        self.now += seconds
        await asyncio.sleep(0)


class FakeAmazon:
    """Answers requests in order and records them."""

    def __init__(self, *replies: Reply) -> None:
        self.replies = list(replies)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        reply = self.replies.pop(0)
        return reply(request) if callable(reply) else reply

    @property
    def paths(self) -> list[str]:
        return [request.url.path for request in self.requests]

    def body(self, index: int) -> dict[str, Any]:
        data: dict[str, Any] = json.loads(self.requests[index].content)
        return data

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self))

    def async_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self))


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    fake = FakeClock()
    monkeypatch.setattr(login_mod, "_clock", fake)
    return fake


def code_pair(expires_in: float = 600, interval: float = INTERVAL) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "public_code": "ABCDE",
            "private_code": "PRIVATE-CODE",
            "expires_in": expires_in,
            "polling_interval_in_seconds": interval,
        },
    )


def pending() -> httpx.Response:
    return httpx.Response(401, json={"response": {"error": {"code": "Unauthorized"}}})


def registered(credentials: dict[str, Any], serial: str = SERIAL) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "response": {
                "success": {
                    "tokens": {
                        "bearer": {
                            "access_token": credentials["access_token"],
                            "refresh_token": credentials["refresh_token"],
                            "expires_in": "3600",
                        },
                        "mac_dms": {
                            "adp_token": credentials["adp_token"],
                            "device_private_key": credentials["device_private_key"],
                        },
                        "website_cookies": [
                            {"Name": "session-id", "Value": '"123-4567890"'}
                        ],
                        "store_authentication_cookie": {"cookie": "STORE"},
                    },
                    "extensions": {
                        "device_info": {"device_serial_number": serial},
                        "customer_info": {"user_id": "amzn1.account.TEST"},
                    },
                }
            }
        },
    )


def started_device_login(amazon: FakeAmazon) -> DeviceCodeLogin:
    login = DeviceCodeLogin("de", serial=SERIAL, client=amazon.client())
    login.start()
    return login


# create_login


def test_create_login_selects_the_flow_by_account_type() -> None:
    assert isinstance(create_login("de"), DeviceCodeLogin)
    assert isinstance(create_login("uk", with_username=True), ExternalLogin)
    assert audible.create_login is create_login


def test_pre_amazon_login_is_refused_outside_de_us_uk() -> None:
    with pytest.raises(ValueError, match="DE, US and UK"):
        create_login("fr", with_username=True)


def test_generated_serials_are_40_ascii_letters_and_digits() -> None:
    serials = {DeviceCodeLogin("de").serial for _ in range(32)}

    assert len(serials) == 32
    assert all(re.fullmatch(r"[A-Za-z0-9]{40}", serial) for serial in serials)


@pytest.mark.parametrize("serial", ["A" * 32, "aB3" * 13 + "Z"])
def test_a_supplied_serial_is_kept_whole_in_the_client_id(serial: str) -> None:
    login = ExternalLogin("de", serial=serial)

    params = parse_qs(urlsplit(login.start().login_url).query)
    client_id = params["openid.oa2.client_id"][0].removeprefix("device:")

    assert login.serial == serial
    assert bytes.fromhex(client_id) == f"{serial}#A2CZJZGLK2JJVM".encode()


# DeviceCodeLogin


def test_device_code_login_registers_once_the_code_is_confirmed(
    clock: FakeClock, auth_fixture_data: dict[str, Any]
) -> None:
    amazon = FakeAmazon(code_pair(), pending(), registered(auth_fixture_data))
    login = DeviceCodeLogin("de", serial=SERIAL, client=amazon.client())

    prompt = login.start()
    auth = login.wait()

    assert prompt.public_code == "ABCDE"
    assert prompt.verification_url == "https://www.amazon.de/code"
    assert prompt.expires_in == 600
    assert amazon.paths == ["/auth/create/codepair", "/auth/register", "/auth/register"]
    assert clock.slept == [INTERVAL, INTERVAL]
    assert login.status is LoginStatus.FINISHED
    assert login.result() is auth
    assert auth.access_token == auth_fixture_data["access_token"]
    assert auth.with_username is False
    assert auth.locale is not None and auth.locale.country_code == "de"
    assert auth.website_cookies == {"session-id": "123-4567890"}
    assert auth.device_info == {"device_serial_number": SERIAL}
    assert auth.expires is not None and auth.expires > time.time() + 3500


def test_device_code_requests_carry_the_confirmed_wire_format(
    clock: FakeClock, auth_fixture_data: dict[str, Any]
) -> None:
    amazon = FakeAmazon(code_pair(), registered(auth_fixture_data))
    login = started_device_login(amazon)
    login.wait()

    create, register = amazon.requests
    assert str(create.url) == "https://api.amazon.de/auth/create/codepair"
    assert create.headers["x-amzn-identity-auth-domain"] == "api.amazon.de"
    assert create.headers["user-agent"] == (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    )
    assert amazon.body(0)["code_data"] == {
        "device_serial": SERIAL,
        "device_type": "A2CZJZGLK2JJVM",
        "domain": "Device",
    }

    assert str(register.url) == "https://api.amazon.de/auth/register"
    body = amazon.body(1)
    assert body["auth_data"] == {
        "code_pair": {"public_code": "ABCDE", "private_code": "PRIVATE-CODE"},
        "use_global_authentication": "true",
    }
    assert body["requested_token_type"] == ["bearer", "mac_dms", "website_cookies"]
    assert body["registration_data"]["device_serial"] == SERIAL
    assert body["registration_data"]["domain"] == "Device"
    assert body["registration_data"]["app_version"] == "4.60"
    assert body["registration_data"]["software_version"] == "46000856"
    assert body["registration_data"]["os_version"] == "26.2"


def test_async_device_code_login_registers_once_the_code_is_confirmed(
    clock: FakeClock, auth_fixture_data: dict[str, Any]
) -> None:
    amazon = FakeAmazon(code_pair(), pending(), registered(auth_fixture_data))

    async def run() -> Authenticator:
        login = DeviceCodeLogin("de", serial=SERIAL, async_client=amazon.async_client())
        await login.async_start()
        return await login.async_wait()

    auth = asyncio.run(run())

    assert amazon.paths == ["/auth/create/codepair", "/auth/register", "/auth/register"]
    assert auth.refresh_token == auth_fixture_data["refresh_token"]


def test_poll_sends_nothing_before_the_next_attempt_is_due(clock: FakeClock) -> None:
    amazon = FakeAmazon(code_pair(), pending())
    login = started_device_login(amazon)

    assert login.poll() is LoginStatus.PENDING
    assert login.next_poll_delay == INTERVAL
    assert len(amazon.requests) == 1

    clock.now += INTERVAL
    assert login.poll() is LoginStatus.PENDING
    assert len(amazon.requests) == 2
    assert login.next_poll_delay == INTERVAL


def test_a_poll_while_a_request_is_in_flight_sends_nothing(clock: FakeClock) -> None:
    login: DeviceCodeLogin
    seen: list[tuple[LoginStatus, float]] = []

    def poll_again(request: httpx.Request) -> httpx.Response:
        seen.append((login.poll(), login.next_poll_delay))
        return pending()

    amazon = FakeAmazon(code_pair(), poll_again)
    login = started_device_login(amazon)

    clock.now += INTERVAL
    login.poll()

    assert seen == [(LoginStatus.PENDING, 0.0)]
    assert len(amazon.requests) == 2
    assert login.next_poll_delay == INTERVAL


def test_an_unknown_error_ends_the_login_instead_of_polling_on(
    clock: FakeClock,
) -> None:
    amazon = FakeAmazon(
        code_pair(), httpx.Response(400, json={"error": "invalid_device_type"})
    )
    login = started_device_login(amazon)

    with pytest.raises(LoginFailedError) as excinfo:
        login.wait()

    assert login.status is LoginStatus.FAILED
    assert excinfo.value.status_code == 400
    assert excinfo.value.error_code == "invalid_device_type"
    with pytest.raises(LoginFailedError):
        login.result()


def test_only_unauthorized_401_counts_as_waiting(clock: FakeClock) -> None:
    amazon = FakeAmazon(
        code_pair(),
        httpx.Response(401, json={"response": {"error": {"code": "InvalidToken"}}}),
    )
    login = started_device_login(amazon)

    clock.now += INTERVAL
    assert login.poll() is LoginStatus.FAILED


def test_the_code_expires_when_nobody_confirms_it(clock: FakeClock) -> None:
    amazon = FakeAmazon(code_pair(expires_in=12), pending(), pending())
    login = started_device_login(amazon)

    with pytest.raises(LoginExpiredError):
        login.wait()

    assert login.status is LoginStatus.EXPIRED
    assert len(amazon.requests) == 3
    assert login.poll() is LoginStatus.EXPIRED
    assert len(amazon.requests) == 3


def test_overload_backs_off_and_honours_retry_after(
    clock: FakeClock, auth_fixture_data: dict[str, Any]
) -> None:
    amazon = FakeAmazon(
        code_pair(),
        httpx.Response(503, headers={"Retry-After": "30"}, text="<html>busy</html>"),
        registered(auth_fixture_data),
    )
    login = started_device_login(amazon)

    clock.now += INTERVAL
    assert login.poll() is LoginStatus.PENDING
    assert login.next_poll_delay == 30

    login.wait()
    assert login.status is LoginStatus.FINISHED


def test_a_network_error_while_polling_is_retried(
    clock: FakeClock, auth_fixture_data: dict[str, Any]
) -> None:
    def network_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unreachable", request=request)

    amazon = FakeAmazon(code_pair(), network_error, registered(auth_fixture_data))
    login = started_device_login(amazon)

    login.wait()

    assert login.status is LoginStatus.FINISHED
    assert len(amazon.requests) == 3


def test_a_wait_timeout_leaves_the_login_pending(
    clock: FakeClock, auth_fixture_data: dict[str, Any]
) -> None:
    amazon = FakeAmazon(code_pair(), pending(), registered(auth_fixture_data))
    login = started_device_login(amazon)

    with pytest.raises(TimeoutError):
        login.wait(timeout=7)

    assert login.status is LoginStatus.PENDING
    assert login.wait() is login.result()


def test_cancel_ends_a_pending_login(clock: FakeClock) -> None:
    amazon = FakeAmazon(code_pair())
    login = started_device_login(amazon)

    assert login.cancel() is True
    assert login.cancel() is False
    assert login.status is LoginStatus.ABORTED
    clock.now += INTERVAL
    assert login.poll() is LoginStatus.ABORTED
    assert len(amazon.requests) == 1
    with pytest.raises(LoginAbortedError):
        login.wait()


def test_a_registration_after_cancel_does_not_revive_the_login(
    clock: FakeClock, auth_fixture_data: dict[str, Any]
) -> None:
    login: DeviceCodeLogin

    def cancel_in_flight(request: httpx.Request) -> httpx.Response:
        login.cancel()
        return registered(auth_fixture_data)

    amazon = FakeAmazon(code_pair(), cancel_in_flight)
    login = started_device_login(amazon)

    clock.now += INTERVAL
    assert login.poll() is LoginStatus.ABORTED
    with pytest.raises(LoginAbortedError):
        login.result()


def test_cancelling_the_async_wait_task_cancels_the_login(clock: FakeClock) -> None:
    amazon = FakeAmazon(code_pair(), *[pending() for _ in range(50)])

    async def run() -> DeviceCodeLogin:
        login = DeviceCodeLogin("de", serial=SERIAL, async_client=amazon.async_client())
        await login.async_start()
        task = asyncio.create_task(login.async_wait())
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return login

    login = asyncio.run(run())

    assert login.status is LoginStatus.ABORTED


def test_the_prompt_counts_the_lifetime_from_before_the_request(
    clock: FakeClock,
) -> None:
    def slow_code_pair(request: httpx.Request) -> httpx.Response:
        clock.now += 3
        return code_pair()

    login = DeviceCodeLogin("de", client=FakeAmazon(slow_code_pair).client())

    assert login.start().expires_in == 597


def test_a_tiny_polling_interval_is_raised_to_one_second(clock: FakeClock) -> None:
    login = started_device_login(FakeAmazon(code_pair(interval=0.01)))

    assert login.next_poll_delay == 1.0


def test_a_code_pair_without_codes_fails_start(clock: FakeClock) -> None:
    empty = httpx.Response(
        200,
        json={
            "public_code": "",
            "private_code": "",
            "expires_in": 600,
            "polling_interval_in_seconds": INTERVAL,
        },
    )
    login = DeviceCodeLogin("de", client=FakeAmazon(empty).client())

    with pytest.raises(LoginFailedError, match="lacks a code"):
        login.start()


def test_cancel_during_start_does_not_hand_out_a_code(clock: FakeClock) -> None:
    login: DeviceCodeLogin

    def cancel_in_flight(request: httpx.Request) -> httpx.Response:
        login.cancel()
        return code_pair()

    login = DeviceCodeLogin("de", client=FakeAmazon(cancel_in_flight).client())

    with pytest.raises(LoginAbortedError):
        login.start()
    assert login.status is LoginStatus.ABORTED
    assert login.poll() is LoginStatus.ABORTED


def test_a_refused_code_pair_fails_start(clock: FakeClock) -> None:
    amazon = FakeAmazon(httpx.Response(400, json={"error": "invalid_device_type"}))
    login = DeviceCodeLogin("de", client=amazon.client())

    with pytest.raises(LoginFailedError):
        login.start()

    assert login.status is LoginStatus.FAILED
    with pytest.raises(LoginFailedError):
        login.wait()


def test_a_network_error_fails_start(clock: FakeClock) -> None:
    def network_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unreachable", request=request)

    login = DeviceCodeLogin("de", client=FakeAmazon(network_error).client())

    with pytest.raises(LoginFailedError, match="Network error"):
        login.start()
    assert login.status is LoginStatus.FAILED


def interrupt(request: httpx.Request) -> httpx.Response:
    raise KeyboardInterrupt


def test_an_interrupted_start_aborts_the_login(clock: FakeClock) -> None:
    login = DeviceCodeLogin("de", client=FakeAmazon(interrupt).client())

    with pytest.raises(KeyboardInterrupt):
        login.start()

    assert login.status is LoginStatus.ABORTED
    with pytest.raises(LoginAbortedError, match="interrupted"):
        login.result()


def test_cancelling_the_async_start_task_aborts_the_login(clock: FakeClock) -> None:
    async def never_answer(request: httpx.Request) -> httpx.Response:
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    async def run() -> DeviceCodeLogin:
        client = httpx.AsyncClient(transport=httpx.MockTransport(never_answer))
        login = DeviceCodeLogin("de", async_client=client)
        starting = asyncio.create_task(login.async_start())
        await asyncio.sleep(0)
        starting.cancel()
        with pytest.raises(asyncio.CancelledError):
            await starting
        return login

    login = asyncio.run(run())

    assert login.status is LoginStatus.ABORTED


def test_methods_called_out_of_order_raise_state_errors(clock: FakeClock) -> None:
    amazon = FakeAmazon(code_pair())
    login = DeviceCodeLogin("de", client=amazon.client())

    with pytest.raises(LoginStateError):
        login.poll()
    with pytest.raises(LoginStateError):
        login.result()
    login.start()
    with pytest.raises(LoginStateError):
        login.start()


def test_a_registration_for_another_device_is_rejected(
    clock: FakeClock, auth_fixture_data: dict[str, Any]
) -> None:
    amazon = FakeAmazon(code_pair(), registered(auth_fixture_data, serial="OTHER"))
    login = started_device_login(amazon)

    with pytest.raises(LoginFailedError, match="another device"):
        login.wait()


def test_the_repr_shows_no_codes(clock: FakeClock) -> None:
    login = started_device_login(FakeAmazon(code_pair()))

    assert repr(login) == "DeviceCodeLogin(locale='de', status=PENDING)"


# Several logins at once


def in_daemon_threads(*functions: Callable[[], Any], timeout: float = 10) -> list[Any]:
    """Run each function in a thread of its own and return the results in order.

    The threads are daemons, so a deadlocked login fails the test after
    ``timeout`` instead of keeping the test run from ever finishing.
    """
    results: list[Any] = [None] * len(functions)
    errors: list[BaseException] = []

    def run(index: int, function: Callable[[], Any]) -> None:
        try:
            results[index] = function()
        except BaseException as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=run, args=(index, function), daemon=True)
        for index, function in enumerate(functions)
    ]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + timeout
    for thread in threads:
        thread.join(max(0.0, deadline - time.monotonic()))
    if any(thread.is_alive() for thread in threads):
        pytest.fail(f"A login did not finish within {timeout} seconds.")
    if errors:
        raise errors[0]
    return results


def parallel_logins(
    auth_fixture_data: dict[str, Any], count: int = 5, *, use_async: bool = False
) -> list[DeviceCodeLogin]:
    logins = []
    for index in range(count):
        serial = f"SERIAL{index}".ljust(40, "0")
        amazon = FakeAmazon(
            code_pair(), pending(), registered(auth_fixture_data, serial)
        )
        if use_async:
            login = DeviceCodeLogin(
                "de", serial=serial, async_client=amazon.async_client()
            )
        else:
            login = DeviceCodeLogin("de", serial=serial, client=amazon.client())
        logins.append(login)
    return logins


def test_device_code_logins_in_parallel_threads_all_finish(
    clock: FakeClock, auth_fixture_data: dict[str, Any]
) -> None:
    logins = parallel_logins(auth_fixture_data)
    for login in logins:
        login.start()

    results = in_daemon_threads(*(login.wait for login in logins))

    assert [auth.device_info for auth in results] == [
        {"device_serial_number": login.serial} for login in logins
    ]
    assert {login.status for login in logins} == {LoginStatus.FINISHED}


def test_device_code_logins_in_one_event_loop_all_finish(
    clock: FakeClock, auth_fixture_data: dict[str, Any]
) -> None:
    logins = parallel_logins(auth_fixture_data, use_async=True)

    async def run() -> list[Authenticator]:
        await asyncio.gather(*(login.async_start() for login in logins))
        return await asyncio.gather(*(login.async_wait() for login in logins))

    [results] = in_daemon_threads(functools.partial(asyncio.run, run()))

    assert [auth.device_info for auth in results] == [
        {"device_serial_number": login.serial} for login in logins
    ]


def test_cancel_from_another_thread_wakes_a_sleeping_wait() -> None:
    amazon = FakeAmazon(code_pair(interval=60))
    login = DeviceCodeLogin("de", serial=SERIAL, client=amazon.client())
    login.start()

    def cancel_soon() -> None:
        time.sleep(0.1)
        login.cancel()

    with pytest.raises(LoginAbortedError):
        in_daemon_threads(login.wait, cancel_soon, timeout=5)

    assert amazon.paths == ["/auth/create/codepair"]


def test_cancel_from_another_thread_wakes_a_sleeping_async_wait() -> None:
    amazon = FakeAmazon(code_pair(interval=60))

    async def run() -> None:
        login = DeviceCodeLogin("de", serial=SERIAL, async_client=amazon.async_client())
        await login.async_start()
        waiting = asyncio.create_task(login.async_wait())
        await asyncio.sleep(0.1)
        threading.Thread(target=login.cancel).start()
        with pytest.raises(LoginAbortedError):
            await waiting

    in_daemon_threads(functools.partial(asyncio.run, run()), timeout=5)

    assert amazon.paths == ["/auth/create/codepair"]


def test_a_poll_overtaken_by_cancel_sends_nothing(clock: FakeClock) -> None:
    amazon = FakeAmazon(code_pair())
    login = started_device_login(amazon)
    clock.now += INTERVAL
    # cancel() lands after poll() checked the status, before it claims the
    # request: the moment poll() reads the clock.
    clock.on_read = login.cancel

    assert login.poll() is LoginStatus.ABORTED
    assert amazon.paths == ["/auth/create/codepair"]


def test_wait_starts_no_attempt_once_its_timeout_has_passed(
    clock: FakeClock,
) -> None:
    amazon = FakeAmazon(code_pair())
    login = started_device_login(amazon)

    with pytest.raises(TimeoutError):
        login.wait(timeout=INTERVAL)

    assert amazon.paths == ["/auth/create/codepair"]
    assert login.status is LoginStatus.PENDING


def test_no_attempt_is_claimed_from_the_deadline_on(clock: FakeClock) -> None:
    amazon = FakeAmazon(code_pair())
    login = started_device_login(amazon)
    clock.now += INTERVAL

    # wait() checks its deadline before polling; this is the claim itself
    # reached only at the deadline, after a delay in between.
    assert login._poll(deadline=clock.now) is LoginStatus.PENDING
    assert amazon.paths == ["/auth/create/codepair"]


def test_a_crypto_provider_is_resolved_before_any_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(provider: object) -> object:
        raise ImportError("not installed")

    monkeypatch.setattr(login_mod, "get_crypto_providers", unavailable)

    with pytest.raises(ImportError):
        DeviceCodeLogin("de", crypto_provider=PycryptodomeProvider)


def test_a_failure_while_building_the_authenticator_ends_the_login(
    clock: FakeClock,
    auth_fixture_data: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(*args: object, **kwargs: object) -> Authenticator:
        raise RuntimeError("broken")

    amazon = FakeAmazon(code_pair(), registered(auth_fixture_data))
    login = started_device_login(amazon)
    monkeypatch.setattr(Authenticator, "from_dict", broken)

    with pytest.raises(RuntimeError):
        login.wait()

    assert login.status is LoginStatus.ABORTED


# ExternalLogin


MAPLANDING = "https://www.audible.co.uk/ap/maplanding"


def test_external_login_url_targets_the_audible_sign_in() -> None:
    login = ExternalLogin("uk", serial=SERIAL)

    url = urlsplit(login.start().login_url)
    params = {key: values[0] for key, values in parse_qs(url.query).items()}

    assert (url.scheme, url.hostname, url.path) == (
        "https",
        "www.audible.co.uk",
        "/ap/signin",
    )
    assert params["openid.assoc_handle"] == "amzn_audible_ios_lap_uk"
    assert params["pageId"] == "amzn_audible_ios_privatepool"
    assert params["openid.return_to"] == MAPLANDING
    assert params["openid.oa2.client_id"] == f"device:{build_client_id(IPHONE, SERIAL)}"
    assert params["openid.oa2.code_challenge_method"] == "S256"


def test_external_login_registers_with_the_returned_code(
    auth_fixture_data: dict[str, Any],
) -> None:
    audible_api = FakeAmazon(registered(auth_fixture_data))
    login = ExternalLogin("uk", serial=SERIAL, client=audible_api.client())
    params = parse_qs(urlsplit(login.start().login_url).query)

    auth = login.complete(f"{MAPLANDING}?openid.oa2.authorization_code=CODE&x=1")

    request = audible_api.requests[0]
    body = audible_api.body(0)
    verifier = body["auth_data"]["code_verifier"]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    assert str(request.url) == "https://api.audible.co.uk/auth/register"
    assert body["auth_data"]["authorization_code"] == "CODE"
    assert body["auth_data"]["client_id"] == build_client_id(IPHONE, SERIAL)
    assert challenge.rstrip(b"=").decode() == params["openid.oa2.code_challenge"][0]
    assert "store_authentication_cookie" in body["requested_token_type"]
    assert body["registration_data"]["app_version"] == "4.60"
    assert body["registration_data"]["software_version"] == "46000856"
    assert body["registration_data"]["os_version"] == "26.2"
    assert login.status is LoginStatus.FINISHED
    assert auth.with_username is True
    assert auth.store_authentication_cookie == {"cookie": "STORE"}
    assert auth.locale is not None and auth.locale.country_code == "uk"


def test_async_external_login_registers_with_the_returned_code(
    auth_fixture_data: dict[str, Any],
) -> None:
    audible_api = FakeAmazon(registered(auth_fixture_data))
    login = ExternalLogin("de", serial=SERIAL, async_client=audible_api.async_client())
    login.start()

    auth = asyncio.run(
        login.async_complete(
            "https://www.audible.de/ap/maplanding?openid.oa2.authorization_code=CODE"
        )
    )

    assert auth.with_username is True
    assert audible_api.paths == ["/auth/register"]


@pytest.mark.parametrize(
    "url",
    [
        "http://www.audible.co.uk/ap/maplanding?openid.oa2.authorization_code=C",
        "https://www.amazon.co.uk/ap/maplanding?openid.oa2.authorization_code=C",
        "https://www.audible.de/ap/maplanding?openid.oa2.authorization_code=C",
        "https://www.audible.co.uk/ap/signin?openid.oa2.authorization_code=C",
        "https://user@www.audible.co.uk/ap/maplanding?openid.oa2.authorization_code=C",
        "https://www.audible.co.uk:8443/ap/maplanding?openid.oa2.authorization_code=C",
        f"{MAPLANDING}?openid.oa2.authorization_code=",
        f"{MAPLANDING}?openid.oa2.authorization_code=A&openid.oa2.authorization_code=B",
        MAPLANDING,
    ],
)
def test_a_wrong_url_is_refused_and_the_login_stays_pending(url: str) -> None:
    audible_api = FakeAmazon()
    login = ExternalLogin("uk", client=audible_api.client())
    login.start()

    with pytest.raises(ValueError):
        login.complete(url)

    assert login.status is LoginStatus.PENDING
    assert audible_api.requests == []


def test_a_refused_registration_fails_the_external_login() -> None:
    audible_api = FakeAmazon(
        httpx.Response(400, json={"error": {"code": "InvalidValue"}})
    )
    login = ExternalLogin("uk", client=audible_api.client())
    login.start()

    with pytest.raises(LoginFailedError) as excinfo:
        login.complete(f"{MAPLANDING}?openid.oa2.authorization_code=CODE")

    assert login.status is LoginStatus.FAILED
    assert excinfo.value.error_code == "invalidvalue"


def test_an_interrupted_complete_aborts_the_external_login() -> None:
    login = ExternalLogin("uk", client=FakeAmazon(interrupt).client())
    login.start()

    with pytest.raises(KeyboardInterrupt):
        login.complete(f"{MAPLANDING}?openid.oa2.authorization_code=CODE")

    assert login.status is LoginStatus.ABORTED
    with pytest.raises(LoginStateError):
        login.complete(f"{MAPLANDING}?openid.oa2.authorization_code=CODE")


def test_a_network_error_after_cancel_reports_the_cancellation() -> None:
    login: ExternalLogin

    def cancel_then_fail(request: httpx.Request) -> httpx.Response:
        login.cancel()
        raise httpx.ConnectError("unreachable", request=request)

    login = ExternalLogin("uk", client=FakeAmazon(cancel_then_fail).client())
    login.start()

    with pytest.raises(LoginAbortedError):
        login.complete(f"{MAPLANDING}?openid.oa2.authorization_code=CODE")
    assert login.status is LoginStatus.ABORTED


def test_an_external_login_accepts_one_url_only(
    auth_fixture_data: dict[str, Any],
) -> None:
    audible_api = FakeAmazon(registered(auth_fixture_data))
    login = ExternalLogin("uk", serial=SERIAL, client=audible_api.client())

    with pytest.raises(LoginStateError):
        login.complete(f"{MAPLANDING}?openid.oa2.authorization_code=CODE")
    login.start()
    login.complete(f"{MAPLANDING}?openid.oa2.authorization_code=CODE")
    with pytest.raises(LoginStateError):
        login.complete(f"{MAPLANDING}?openid.oa2.authorization_code=CODE")
    assert len(audible_api.requests) == 1


# Integration with the authenticator


def test_a_registered_device_round_trips_through_to_dict(
    clock: FakeClock, auth_fixture_data: dict[str, Any]
) -> None:
    amazon = FakeAmazon(code_pair(), registered(auth_fixture_data))
    auth = started_device_login(amazon).wait()

    reloaded = Authenticator.from_dict(auth.to_dict())

    assert reloaded.to_dict() == auth.to_dict()
    assert reloaded.with_username is False


def test_token_refresh_reports_the_registered_app_version() -> None:
    body = _refresh_token_request_body("Atnr|TOKEN")

    assert body["app_version"] == "4.60"


@pytest.mark.parametrize("with_username", [False, True])
def test_cookie_refresh_reports_the_registered_app_version(
    monkeypatch: pytest.MonkeyPatch, with_username: bool
) -> None:
    target = "audible" if with_username else "amazon"

    def fake_post(url: str, *, data: dict[str, str]) -> httpx.Response:
        assert url == f"https://www.{target}.de/ap/exchangetoken/cookies"
        assert data["app_version"] == "4.60"
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"response": {"tokens": {"cookies": {}}}},
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    assert refresh_website_cookies("Atnr|TOKEN", "de", "de", with_username) == {}
