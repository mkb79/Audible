"""Protocol checks for generated device identities and the iPhone profile."""

from __future__ import annotations

import asyncio
import base64
import json
import re
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

import audible.auth as auth_mod
import audible.register as register_mod
from audible.login import (
    USER_AGENT,
    build_device_serial,
    build_init_cookies,
    build_oauth_url,
)


TEST_ACCESS_TOKEN = "test-access-token"  # noqa: S105
TEST_REFRESH_TOKEN = "test-refresh-token"  # noqa: S105


def test_generated_serial_format() -> None:
    """New devices use 40 ASCII alphanumeric characters without separators."""
    serials = [build_device_serial() for _ in range(32)]

    assert all(re.fullmatch(r"[A-Za-z0-9]{40}", serial) for serial in serials)
    assert len(set(serials)) == len(serials)


@pytest.mark.parametrize("with_username", [False, True])
@pytest.mark.parametrize("serial", [None, "A" * 32, "aB3" * 13 + "Z"])
def test_oauth_client_id_preserves_serial(
    with_username: bool, serial: str | None
) -> None:
    """OAuth encodes the entire serial unchanged for both account types."""
    url, actual_serial = build_oauth_url(
        "de", "de", "AN7V1F1VY261K", b"test-verifier", serial, with_username
    )
    params = parse_qs(urlsplit(url).query)
    client_id = params["openid.oa2.client_id"][0]

    if serial is None:
        assert re.fullmatch(r"[A-Za-z0-9]{40}", actual_serial)
    else:
        assert actual_serial == serial
    assert (
        bytes.fromhex(client_id.removeprefix("device:"))
        == (actual_serial + "#A2CZJZGLK2JJVM").encode()
    )
    expected_host = "www.audible.de" if with_username else "www.amazon.de"
    assert urlsplit(url).hostname == expected_host


@pytest.mark.parametrize("with_username", [False, True])
@pytest.mark.parametrize("serial", ["A" * 32, "aB3" * 13 + "Z"])
def test_registration_sends_updated_profile(
    monkeypatch: pytest.MonkeyPatch, with_username: bool, serial: str
) -> None:
    """Register sends the new versions while preserving supplied serials."""
    requests: list[dict[str, Any]] = []
    target = "audible" if with_username else "amazon"

    def fake_post(url: str, *, json: dict[str, Any]) -> httpx.Response:
        assert url == f"https://api.{target}.de/auth/register"
        requests.append(json)
        return httpx.Response(
            200,
            json={
                "response": {
                    "success": {
                        "tokens": {
                            "mac_dms": {
                                "adp_token": "test-adp-token",
                                "device_private_key": "test-private-key",
                            },
                            "bearer": {
                                "access_token": "test-access-token",
                                "refresh_token": "test-refresh-token",
                                "expires_in": "3600",
                            },
                        },
                        "extensions": {
                            "device_info": {"device_serial_number": serial},
                            "customer_info": {},
                        },
                    }
                }
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    result = register_mod.register(
        "test-code", b"test-verifier", "de", serial, with_username
    )

    assert len(requests) == 1
    body = requests[0]
    profile = body["registration_data"]
    assert profile["device_serial"] == serial
    assert profile["device_type"] == "A2CZJZGLK2JJVM"
    assert profile["app_version"] == "4.60"
    assert profile["os_version"] == "26.2"
    assert profile["software_version"] == "46000856"
    assert profile["domain"] == "Device"
    assert profile["device_model"] == "iPhone"
    assert profile["app_name"] == "Audible"
    assert (
        bytes.fromhex(body["auth_data"]["client_id"])
        == (serial + "#A2CZJZGLK2JJVM").encode()
    )
    assert body["auth_data"]["authorization_code"] == "test-code"
    assert body["auth_data"]["code_verifier"] == "test-verifier"
    assert result["device_info"]["device_serial_number"] == serial


def test_login_versions_match_registration() -> None:
    """The initial MAP cookie and browser identity use the same profile."""
    encoded = build_init_cookies()["map-md"]
    metadata = json.loads(base64.b64decode(encoded + "=" * (-len(encoded) % 4)))

    assert metadata["device_registration_data"]["software_version"] == "46000856"
    assert metadata["app_identifier"]["app_version"] == "4.60"
    assert "iPhone OS 26_2 like Mac OS X" in USER_AGENT


@pytest.mark.parametrize("with_username", [False, True])
def test_sync_refresh_sends_updated_app_version(
    monkeypatch: pytest.MonkeyPatch, with_username: bool
) -> None:
    """Synchronous token refresh uses the updated version on either domain."""
    target = "audible" if with_username else "amazon"

    def fake_post(url: str, *, data: dict[str, str]) -> httpx.Response:
        assert url == f"https://api.{target}.de/auth/token"
        assert data["app_version"] == "4.60"
        assert data["source_token"] == TEST_REFRESH_TOKEN
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"access_token": "test-access-token", "expires_in": 3600},
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    result = auth_mod.refresh_access_token("test-refresh-token", "de", with_username)

    assert result["access_token"] == TEST_ACCESS_TOKEN


@pytest.mark.parametrize("with_username", [False, True])
def test_async_refresh_sends_updated_app_version(
    monkeypatch: pytest.MonkeyPatch, with_username: bool
) -> None:
    """Asynchronous refresh uses the same version as synchronous refresh."""
    target = "audible" if with_username else "amazon"

    async def fake_post(
        self: httpx.AsyncClient, url: str, *, data: dict[str, str]
    ) -> httpx.Response:
        assert url == f"https://api.{target}.de/auth/token"
        assert data["app_version"] == "4.60"
        assert data["source_token"] == TEST_REFRESH_TOKEN
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"access_token": "test-access-token", "expires_in": 3600},
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = asyncio.run(
        auth_mod.async_refresh_access_token("test-refresh-token", "de", with_username)
    )

    assert result["access_token"] == TEST_ACCESS_TOKEN


@pytest.mark.parametrize("with_username", [False, True])
def test_cookie_refresh_sends_updated_app_version(
    monkeypatch: pytest.MonkeyPatch, with_username: bool
) -> None:
    """Cookie exchange keeps the app version consistent with registration."""
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

    assert (
        auth_mod.refresh_website_cookies(
            "test-refresh-token", "de", "de", with_username
        )
        == {}
    )
