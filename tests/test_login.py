"""Tests for registering a new device with DeviceCodeLogin and ExternalLogin."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
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
from audible.auth import Authenticator, _refresh_token_request_body
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

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float, wakeup: Any) -> None:
        self.slept.append(seconds)
        self.now += seconds

    async def async_sleep(self, seconds: float) -> None:
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
    assert "iPhone OS 27_0_1 like Mac OS X" in create.headers["user-agent"]
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
    assert body["registration_data"]["app_version"] == "4.56.2"
    assert body["registration_data"]["software_version"] == "45602826"
    assert body["registration_data"]["os_version"] == "27.0.1"


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

    assert body["app_version"] == "4.56.2"
