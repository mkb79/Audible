"""Tests for x-amz-access-token bearer auth and race-safe token refresh."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

import audible.auth as auth_mod
import audible.register as register_mod
from audible import AsyncClient
from audible.auth import Authenticator
from audible.exceptions import AuthFlowError
from audible.utils import build_access_token_header


# Far-future / epoch timestamps to control token expiry deterministically.
TOKEN_VALID = 9_999_999_999.0
TOKEN_EXPIRED = 0.0

NEW_ACCESS_TOKEN = "Atna|NEWTOKENForUnitTestingOnlyNotReal1234567890"  # noqa: S105


def _bearer_auth(auth_fixture_data: dict[str, Any], *, expires: float) -> Authenticator:
    """Build a fake-credential authenticator that selects bearer auth.

    Args:
        auth_fixture_data: The shared fake auth fixture data.
        expires: The access token expiry timestamp to set.

    Returns:
        An authenticator with signing credentials removed so that
        :meth:`Authenticator._select_auth_mode` picks ``"bearer"``.
    """
    auth = Authenticator.from_dict(auth_fixture_data)
    auth.adp_token = None
    auth.device_private_key = None
    auth.website_cookies = None
    auth.expires = expires
    return auth


async def _apply_async_auth_flow(auth: Authenticator, request: httpx.Request) -> None:
    """Drive ``async_auth_flow`` once (apply auth) and close the generator."""
    gen = auth.async_auth_flow(request)
    await gen.__anext__()
    await gen.aclose()


def test_build_access_token_header() -> None:
    """The helper builds the x-amz-access-token header, not Bearer."""
    assert build_access_token_header("Atna|TOKEN") == {
        "x-amz-access-token": "Atna|TOKEN"
    }


def test_sync_bearer_flow_sets_x_amz_access_token(
    auth_fixture_data: dict[str, Any],
) -> None:
    """The sync bearer flow sends x-amz-access-token and drops client-id/Bearer."""
    auth = _bearer_auth(auth_fixture_data, expires=TOKEN_VALID)
    request = httpx.Request("GET", "https://api.audible.de/1.0/library")

    auth._apply_bearer_auth_flow(request)

    assert request.headers["x-amz-access-token"] == auth.access_token
    assert "authorization" not in request.headers
    assert "client-id" not in request.headers


def test_async_bearer_flow_sets_x_amz_access_token(
    auth_fixture_data: dict[str, Any],
) -> None:
    """The async bearer flow sends x-amz-access-token and drops client-id/Bearer."""
    auth = _bearer_auth(auth_fixture_data, expires=TOKEN_VALID)
    request = httpx.Request("GET", "https://api.audible.de/1.0/library")

    asyncio.run(auth._async_apply_bearer_auth_flow(request))

    assert request.headers["x-amz-access-token"] == auth.access_token
    assert "authorization" not in request.headers
    assert "client-id" not in request.headers


def test_select_auth_mode_prefers_signing(
    auth_fixture_data: dict[str, Any],
) -> None:
    """Signing is preferred over bearer when both are available."""
    auth = Authenticator.from_dict(auth_fixture_data)

    assert "signing" in auth.available_auth_modes
    assert "bearer" in auth.available_auth_modes
    assert auth._select_auth_mode() == "signing"


def test_select_auth_mode_falls_back_to_bearer(
    auth_fixture_data: dict[str, Any],
) -> None:
    """Bearer is selected once signing credentials are unavailable."""
    auth = _bearer_auth(auth_fixture_data, expires=TOKEN_VALID)

    assert auth.available_auth_modes == ["bearer"]
    assert auth._select_auth_mode() == "bearer"


def test_select_auth_mode_raises_without_modes(
    auth_fixture_data: dict[str, Any],
) -> None:
    """No signing and no bearer credentials raise AuthFlowError."""
    auth = _bearer_auth(auth_fixture_data, expires=TOKEN_VALID)
    auth.access_token = None

    with pytest.raises(AuthFlowError):
        auth._select_auth_mode()


def test_async_auth_flow_uses_signing_when_available(
    auth_fixture_data: dict[str, Any],
) -> None:
    """A full auth file signs requests; x-amz-access-token is not used."""
    auth = Authenticator.from_dict(auth_fixture_data)
    request = httpx.Request("GET", "https://api.audible.de/1.0/library")

    asyncio.run(_apply_async_auth_flow(auth, request))

    assert "x-adp-token" in request.headers
    assert "x-amz-access-token" not in request.headers


def test_sync_refresh_skips_when_not_expired(
    auth_fixture_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-expired token is not refreshed over the network."""
    auth = _bearer_auth(auth_fixture_data, expires=TOKEN_VALID)
    calls = 0

    def fake_refresh(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"access_token": NEW_ACCESS_TOKEN, "expires": TOKEN_VALID}

    monkeypatch.setattr(auth_mod, "refresh_access_token", fake_refresh)

    auth.refresh_access_token()

    assert calls == 0


def test_sync_refresh_runs_when_expired(
    auth_fixture_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An expired token triggers exactly one sync refresh."""
    auth = _bearer_auth(auth_fixture_data, expires=TOKEN_EXPIRED)
    calls = 0

    def fake_refresh(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"access_token": NEW_ACCESS_TOKEN, "expires": TOKEN_VALID}

    monkeypatch.setattr(auth_mod, "refresh_access_token", fake_refresh)

    auth.refresh_access_token()

    assert calls == 1
    assert auth.access_token == NEW_ACCESS_TOKEN


def test_async_refresh_coalesces_concurrent_requests(
    auth_fixture_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ten concurrent expired-token requests trigger a single async refresh."""
    auth = _bearer_auth(auth_fixture_data, expires=TOKEN_EXPIRED)
    calls = 0

    async def fake_refresh(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)  # widen the race window
        return {"access_token": NEW_ACCESS_TOKEN, "expires": TOKEN_VALID}

    monkeypatch.setattr(auth_mod, "async_refresh_access_token", fake_refresh)

    async def drive() -> list[httpx.Request]:
        requests = [
            httpx.Request("GET", "https://api.audible.de/1.0/library")
            for _ in range(10)
        ]
        await asyncio.gather(
            *[auth._async_apply_bearer_auth_flow(req) for req in requests]
        )
        return requests

    requests = asyncio.run(drive())

    assert calls == 1
    assert auth.access_token == NEW_ACCESS_TOKEN
    assert all(
        req.headers["x-amz-access-token"] == NEW_ACCESS_TOKEN for req in requests
    )


def test_async_refresh_lock_reused_across_event_loops(
    auth_fixture_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same authenticator can refresh in successive asyncio.run() loops."""
    auth = _bearer_auth(auth_fixture_data, expires=TOKEN_EXPIRED)

    async def fake_refresh(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"access_token": NEW_ACCESS_TOKEN, "expires": TOKEN_EXPIRED}

    monkeypatch.setattr(auth_mod, "async_refresh_access_token", fake_refresh)

    # A lock bound to the first loop would raise "bound to a different loop".
    asyncio.run(auth.async_refresh_access_token(force=True))
    asyncio.run(auth.async_refresh_access_token(force=True))


def test_asyncclient_concurrent_requests_single_refresh(
    auth_fixture_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """End to end: concurrent AsyncClient calls refresh once and send the token."""
    auth = _bearer_auth(auth_fixture_data, expires=TOKEN_EXPIRED)
    calls = 0

    async def fake_refresh(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return {"access_token": NEW_ACCESS_TOKEN, "expires": TOKEN_VALID}

    monkeypatch.setattr(auth_mod, "async_refresh_access_token", fake_refresh)

    sent_tokens: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent_tokens.append(request.headers.get("x-amz-access-token"))
        return httpx.Response(200, json={"items": []})

    async def drive() -> None:
        async with AsyncClient(
            auth=auth, transport=httpx.MockTransport(handler)
        ) as client:
            await asyncio.gather(*[client.get("library") for _ in range(10)])

    asyncio.run(drive())

    assert calls == 1
    assert sent_tokens == [NEW_ACCESS_TOKEN] * 10


def test_deregister_sends_x_amz_access_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """register.deregister authenticates with x-amz-access-token, not Bearer."""
    captured: dict[str, Any] = {}

    def fake_post(
        url: str, json: Any = None, headers: Any = None, **kwargs: Any
    ) -> httpx.Response:
        captured["headers"] = headers
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(httpx, "post", fake_post)

    result = register_mod.deregister("Atna|TOKEN", "de")

    assert result == {"ok": True}
    assert captured["headers"] == {"x-amz-access-token": "Atna|TOKEN"}
    assert "Authorization" not in captured["headers"]
