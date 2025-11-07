"""Tests for audible.register module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from audible import register


if TYPE_CHECKING:
    from typing import Any

    from pytest_httpx import HTTPXMock

pytest_plugins = ["tests.fixtures.register_fixtures"]


class TestRegisterFunction:
    """Tests for register() function."""

    def test_register_success(
        self, httpx_mock: HTTPXMock, mock_register_response_success: dict[str, Any]
    ) -> None:
        """register() successfully registers device and returns credentials."""
        httpx_mock.add_response(
            url="https://api.amazon.com/auth/register",
            method="POST",
            json=mock_register_response_success,
            status_code=200,
        )

        result = register.register(
            authorization_code="MOCK_AUTH_CODE",
            code_verifier=b"MOCK_CODE_VERIFIER",
            domain="com",
            serial="MOCK_SERIAL_123",
        )

        # Verify all expected keys are present
        assert "access_token" in result
        assert "refresh_token" in result
        assert "adp_token" in result
        assert "device_private_key" in result
        assert "expires" in result
        assert "website_cookies" in result
        assert "device_info" in result
        assert "customer_info" in result
        assert "store_authentication_cookie" in result

        # Verify token values
        assert result["access_token"] == "Atna|MOCK_ACCESS_TOKEN_1234567890"  # noqa: S105
        assert result["refresh_token"] == "Atnr|MOCK_REFRESH_TOKEN_0987654321"  # noqa: S105

        # Verify request was made
        assert len(httpx_mock.get_requests()) == 1
        request = httpx_mock.get_requests()[0]
        assert request.url == "https://api.amazon.com/auth/register"
        assert request.method == "POST"

    def test_register_with_username_domain(
        self, httpx_mock: HTTPXMock, mock_register_response_success: dict[str, Any]
    ) -> None:
        """register() uses audible domain when with_username=True."""
        httpx_mock.add_response(
            url="https://api.audible.com/auth/register",
            method="POST",
            json=mock_register_response_success,
            status_code=200,
        )

        register.register(
            authorization_code="MOCK_CODE",
            code_verifier=b"MOCK_VERIFIER",
            domain="com",
            serial="MOCK_SERIAL",
            with_username=True,
        )

        request = httpx_mock.get_requests()[0]
        assert request.url == "https://api.audible.com/auth/register"

    def test_register_website_cookies_parsing(
        self, httpx_mock: HTTPXMock, mock_register_response_success: dict[str, Any]
    ) -> None:
        """register() correctly parses website cookies."""
        httpx_mock.add_response(
            url="https://api.amazon.com/auth/register",
            method="POST",
            json=mock_register_response_success,
            status_code=200,
        )

        result = register.register(
            authorization_code="MOCK_CODE",
            code_verifier=b"MOCK_VERIFIER",
            domain="com",
            serial="MOCK_SERIAL",
        )

        assert result["website_cookies"] is not None
        assert "session-id" in result["website_cookies"]
        assert result["website_cookies"]["session-id"] == "mock-session-123"
        assert "ubid-main" in result["website_cookies"]
        # Verify quotes are stripped from x-main value
        assert result["website_cookies"]["x-main"] == "mock-x-value-789"

    def test_register_without_website_cookies(
        self, httpx_mock: HTTPXMock, mock_register_response_no_cookies: dict[str, Any]
    ) -> None:
        """register() handles response without website_cookies."""
        httpx_mock.add_response(
            url="https://api.amazon.com/auth/register",
            method="POST",
            json=mock_register_response_no_cookies,
            status_code=200,
        )

        result = register.register(
            authorization_code="MOCK_CODE",
            code_verifier=b"MOCK_VERIFIER",
            domain="com",
            serial="MOCK_SERIAL",
        )

        assert result["website_cookies"] is None

    def test_register_expires_calculation(
        self, httpx_mock: HTTPXMock, mock_register_response_success: dict[str, Any]
    ) -> None:
        """register() calculates expires timestamp correctly."""
        httpx_mock.add_response(
            url="https://api.amazon.com/auth/register",
            method="POST",
            json=mock_register_response_success,
            status_code=200,
        )

        result = register.register(
            authorization_code="MOCK_CODE",
            code_verifier=b"MOCK_VERIFIER",
            domain="com",
            serial="MOCK_SERIAL",
        )

        # Expires should be a timestamp (float) in the future
        assert isinstance(result["expires"], float)
        assert result["expires"] > 0

    def test_register_error_response(self, httpx_mock: HTTPXMock) -> None:
        """register() raises exception on error response."""
        httpx_mock.add_response(
            url="https://api.amazon.com/auth/register",
            method="POST",
            json={"error": {"message": "Invalid authorization code"}},
            status_code=400,
        )

        with pytest.raises(Exception):  # noqa: B017
            register.register(
                authorization_code="INVALID_CODE",
                code_verifier=b"MOCK_VERIFIER",
                domain="com",
                serial="MOCK_SERIAL",
            )

    def test_register_request_body_structure(
        self, httpx_mock: HTTPXMock, mock_register_response_success: dict[str, Any]
    ) -> None:
        """register() sends correct request body structure."""
        httpx_mock.add_response(
            url="https://api.amazon.de/auth/register",
            method="POST",
            json=mock_register_response_success,
            status_code=200,
        )

        register.register(
            authorization_code="MOCK_CODE",
            code_verifier=b"MOCK_VERIFIER",
            domain="de",
            serial="MOCK_SERIAL_456",
        )

        # Verify request body structure
        request = httpx_mock.get_requests()[0]
        import json

        body = json.loads(request.content)

        assert "requested_token_type" in body
        assert "bearer" in body["requested_token_type"]
        assert "mac_dms" in body["requested_token_type"]
        assert "website_cookies" in body["requested_token_type"]

        assert "registration_data" in body
        assert body["registration_data"]["device_serial"] == "MOCK_SERIAL_456"

        assert "auth_data" in body
        assert body["auth_data"]["authorization_code"] == "MOCK_CODE"
        assert body["auth_data"]["code_verifier"] == "MOCK_VERIFIER"

        assert "cookies" in body
        assert body["cookies"]["domain"] == ".amazon.de"

        assert "requested_extensions" in body
        assert "device_info" in body["requested_extensions"]
        assert "customer_info" in body["requested_extensions"]


class TestDeregisterFunction:
    """Tests for deregister() function."""

    def test_deregister_success(
        self, httpx_mock: HTTPXMock, mock_deregister_response_success: dict[str, Any]
    ) -> None:
        """deregister() successfully deregisters device."""
        httpx_mock.add_response(
            url="https://api.amazon.com/auth/deregister",
            method="POST",
            json=mock_deregister_response_success,
            status_code=200,
        )

        result = register.deregister(
            access_token="Atna|MOCK_ACCESS_TOKEN",
            domain="com",
        )

        assert "response" in result
        assert "success" in result["response"]
        assert "request_id" in result

        # Verify request was made
        assert len(httpx_mock.get_requests()) == 1
        request = httpx_mock.get_requests()[0]
        assert request.url == "https://api.amazon.com/auth/deregister"

    def test_deregister_with_username_domain(
        self, httpx_mock: HTTPXMock, mock_deregister_response_success: dict[str, Any]
    ) -> None:
        """deregister() uses audible domain when with_username=True."""
        httpx_mock.add_response(
            url="https://api.audible.com/auth/deregister",
            method="POST",
            json=mock_deregister_response_success,
            status_code=200,
        )

        register.deregister(
            access_token="Atna|MOCK_TOKEN",
            domain="com",
            with_username=True,
        )

        request = httpx_mock.get_requests()[0]
        assert request.url == "https://api.audible.com/auth/deregister"

    def test_deregister_all_devices(
        self, httpx_mock: HTTPXMock, mock_deregister_response_success: dict[str, Any]
    ) -> None:
        """deregister() can deregister all devices."""
        httpx_mock.add_response(
            url="https://api.amazon.com/auth/deregister",
            method="POST",
            json=mock_deregister_response_success,
            status_code=200,
        )

        register.deregister(
            access_token="Atna|MOCK_TOKEN",
            domain="com",
            deregister_all=True,
        )

        # Verify request body
        request = httpx_mock.get_requests()[0]
        import json

        body = json.loads(request.content)
        assert body["deregister_all_existing_accounts"] is True

    def test_deregister_authorization_header(
        self, httpx_mock: HTTPXMock, mock_deregister_response_success: dict[str, Any]
    ) -> None:
        """deregister() sends correct Authorization header."""
        httpx_mock.add_response(
            url="https://api.amazon.com/auth/deregister",
            method="POST",
            json=mock_deregister_response_success,
            status_code=200,
        )

        test_token = "Atna|TEST_ACCESS_TOKEN_123"  # noqa: S105
        register.deregister(
            access_token=test_token,
            domain="com",
        )

        # Verify Authorization header
        request = httpx_mock.get_requests()[0]
        assert "Authorization" in request.headers
        assert request.headers["Authorization"] == f"Bearer {test_token}"

    def test_deregister_error_response(self, httpx_mock: HTTPXMock) -> None:
        """deregister() raises exception on error response."""
        httpx_mock.add_response(
            url="https://api.amazon.com/auth/deregister",
            method="POST",
            json={"error": {"message": "Unauthorized"}},
            status_code=401,
        )

        with pytest.raises(Exception):  # noqa: B017
            register.deregister(
                access_token="INVALID_TOKEN",
                domain="com",
            )

    def test_deregister_single_device_default(
        self, httpx_mock: HTTPXMock, mock_deregister_response_success: dict[str, Any]
    ) -> None:
        """deregister() defaults to single device deregistration."""
        httpx_mock.add_response(
            url="https://api.amazon.com/auth/deregister",
            method="POST",
            json=mock_deregister_response_success,
            status_code=200,
        )

        register.deregister(
            access_token="Atna|MOCK_TOKEN",
            domain="com",
        )

        # Verify default is deregister_all=False
        request = httpx_mock.get_requests()[0]
        import json

        body = json.loads(request.content)
        assert body["deregister_all_existing_accounts"] is False
