"""Tests for audible.register module."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import pytest

from audible import register


@pytest.fixture
def mock_register_response_success() -> dict[str, Any]:
    """Fixture for successful registration response (anonymized mock data)."""
    return {
        "response": {
            "success": {
                "extensions": {
                    "device_info": {
                        "device_name": "Test User's Audible Device",
                        "device_serial_number": "MOCK1234567890ABCDEF",
                        "device_type": "A2CZJZGLK2JJVM",
                    },
                    "customer_info": {
                        "account_pool": "Amazon",
                        "user_id": "amzn1.account.MOCKUSERID123456",
                        "home_region": "NA",
                        "name": "Test User",
                        "given_name": "Test",
                    },
                },
                "tokens": {
                    "website_cookies": [
                        {
                            "Name": "session-id",
                            "Value": "mock-session-123",
                            "Domain": ".amazon.com",
                            "Path": "/",
                            "Secure": "true",
                            "HttpOnly": "false",
                            "Expires": "01 Jan 2030 00:00:00 GMT",
                        },
                        {
                            "Name": "ubid-main",
                            "Value": "mock-ubid-456",
                            "Domain": ".amazon.com",
                            "Path": "/",
                            "Secure": "true",
                            "HttpOnly": "false",
                            "Expires": "01 Jan 2030 00:00:00 GMT",
                        },
                        {
                            "Name": "x-main",
                            "Value": '"mock-x-value-789"',
                            "Domain": ".amazon.com",
                            "Path": "/",
                            "Secure": "true",
                            "HttpOnly": "false",
                            "Expires": "01 Jan 2030 00:00:00 GMT",
                        },
                    ],
                    "mac_dms": {
                        "device_private_key": "-----BEGIN RSA PRIVATE KEY-----\nMOCK_PRIVATE_KEY_DATA_HERE\n-----END RSA PRIVATE KEY-----\n",  # noqa: S105
                        "adp_token": "{enc:MOCK_ENCRYPTED_ADP_TOKEN}{key:MOCK_KEY}{iv:MOCK_IV}{name:MOCK_NAME}{serial:MOCK_SERIAL}",  # noqa: S105
                    },
                    "bearer": {
                        "access_token": "Atna|MOCK_ACCESS_TOKEN_1234567890",  # noqa: S105
                        "refresh_token": "Atnr|MOCK_REFRESH_TOKEN_0987654321",  # noqa: S105
                        "expires_in": "3600",
                    },
                    "store_authentication_cookie": {
                        "cookie": "MOCK_STORE_AUTH_COOKIE_DATA"  # noqa: S105
                    },
                },
                "customer_id": "amzn1.account.MOCKUSERID123456",
            }
        },
        "request_id": "mock-request-id-abcd-1234",
    }


@pytest.fixture
def mock_register_response_no_cookies() -> dict[str, Any]:
    """Fixture for registration response without website_cookies."""
    return {
        "response": {
            "success": {
                "extensions": {
                    "device_info": {
                        "device_name": "Test Device",
                        "device_serial_number": "MOCK_SERIAL",
                        "device_type": "A2CZJZGLK2JJVM",
                    },
                    "customer_info": {
                        "account_pool": "Amazon",
                        "user_id": "amzn1.account.TEST",
                        "home_region": "NA",
                        "name": "Test",
                        "given_name": "Test",
                    },
                },
                "tokens": {
                    "mac_dms": {
                        "device_private_key": "-----BEGIN RSA PRIVATE KEY-----\nMOCK_KEY\n-----END RSA PRIVATE KEY-----\n",  # noqa: S105
                        "adp_token": "{enc:MOCK}",  # noqa: S105
                    },
                    "bearer": {
                        "access_token": "Atna|MOCK_TOKEN",  # noqa: S105
                        "refresh_token": "Atnr|MOCK_TOKEN",  # noqa: S105
                        "expires_in": "3600",
                    },
                },
                "customer_id": "amzn1.account.TEST",
            }
        },
        "request_id": "mock-id",
    }


@pytest.fixture
def mock_deregister_response_success() -> dict[str, Any]:
    """Fixture for successful deregistration response."""
    return {
        "response": {"success": {}},
        "request_id": "mock-deregister-request-id-5678",
    }


class TestRegisterFunction:
    """Tests for register() function."""

    @patch("audible.register.httpx.post")
    def test_register_success(
        self, mock_post: Mock, mock_register_response_success: dict[str, Any]
    ) -> None:
        """register() successfully registers device and returns credentials."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_register_response_success
        mock_post.return_value = mock_response

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
        assert result["access_token"] == "Atna|MOCK_ACCESS_TOKEN_1234567890"
        assert result["refresh_token"] == "Atnr|MOCK_REFRESH_TOKEN_0987654321"

        # Verify httpx.post was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "https://api.amazon.com/auth/register" in call_args[0]

    @patch("audible.register.httpx.post")
    def test_register_with_username_domain(
        self, mock_post: Mock, mock_register_response_success: dict[str, Any]
    ) -> None:
        """register() uses audible domain when with_username=True."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_register_response_success
        mock_post.return_value = mock_response

        register.register(
            authorization_code="MOCK_CODE",
            code_verifier=b"MOCK_VERIFIER",
            domain="com",
            serial="MOCK_SERIAL",
            with_username=True,
        )

        call_args = mock_post.call_args
        assert "https://api.audible.com/auth/register" in call_args[0]

    @patch("audible.register.httpx.post")
    def test_register_website_cookies_parsing(
        self, mock_post: Mock, mock_register_response_success: dict[str, Any]
    ) -> None:
        """register() correctly parses website cookies."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_register_response_success
        mock_post.return_value = mock_response

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

    @patch("audible.register.httpx.post")
    def test_register_without_website_cookies(
        self, mock_post: Mock, mock_register_response_no_cookies: dict[str, Any]
    ) -> None:
        """register() handles response without website_cookies."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_register_response_no_cookies
        mock_post.return_value = mock_response

        result = register.register(
            authorization_code="MOCK_CODE",
            code_verifier=b"MOCK_VERIFIER",
            domain="com",
            serial="MOCK_SERIAL",
        )

        assert result["website_cookies"] is None

    @patch("audible.register.httpx.post")
    def test_register_expires_calculation(
        self, mock_post: Mock, mock_register_response_success: dict[str, Any]
    ) -> None:
        """register() calculates expires timestamp correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_register_response_success
        mock_post.return_value = mock_response

        result = register.register(
            authorization_code="MOCK_CODE",
            code_verifier=b"MOCK_VERIFIER",
            domain="com",
            serial="MOCK_SERIAL",
        )

        # Expires should be a timestamp (float) in the future
        assert isinstance(result["expires"], float)
        assert result["expires"] > 0

    @patch("audible.register.httpx.post")
    def test_register_error_response(self, mock_post: Mock) -> None:
        """register() raises exception on error response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "Invalid authorization code"}
        }
        mock_post.return_value = mock_response

        with pytest.raises(Exception):
            register.register(
                authorization_code="INVALID_CODE",
                code_verifier=b"MOCK_VERIFIER",
                domain="com",
                serial="MOCK_SERIAL",
            )

    @patch("audible.register.httpx.post")
    def test_register_request_body_structure(
        self, mock_post: Mock, mock_register_response_success: dict[str, Any]
    ) -> None:
        """register() sends correct request body structure."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_register_response_success
        mock_post.return_value = mock_response

        register.register(
            authorization_code="MOCK_CODE",
            code_verifier=b"MOCK_VERIFIER",
            domain="de",
            serial="MOCK_SERIAL_456",
        )

        # Verify request body structure
        call_kwargs = mock_post.call_args[1]
        body = call_kwargs["json"]

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

    @patch("audible.register.httpx.post")
    def test_deregister_success(
        self, mock_post: Mock, mock_deregister_response_success: dict[str, Any]
    ) -> None:
        """deregister() successfully deregisters device."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_deregister_response_success
        mock_post.return_value = mock_response

        result = register.deregister(
            access_token="Atna|MOCK_ACCESS_TOKEN",  # noqa: S106
            domain="com",
        )

        assert "response" in result
        assert "success" in result["response"]
        assert "request_id" in result

        # Verify httpx.post was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "https://api.amazon.com/auth/deregister" in call_args[0]

    @patch("audible.register.httpx.post")
    def test_deregister_with_username_domain(
        self, mock_post: Mock, mock_deregister_response_success: dict[str, Any]
    ) -> None:
        """deregister() uses audible domain when with_username=True."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_deregister_response_success
        mock_post.return_value = mock_response

        register.deregister(
            access_token="Atna|MOCK_TOKEN",  # noqa: S106
            domain="com",
            with_username=True,
        )

        call_args = mock_post.call_args
        assert "https://api.audible.com/auth/deregister" in call_args[0]

    @patch("audible.register.httpx.post")
    def test_deregister_all_devices(
        self, mock_post: Mock, mock_deregister_response_success: dict[str, Any]
    ) -> None:
        """deregister() can deregister all devices."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_deregister_response_success
        mock_post.return_value = mock_response

        register.deregister(
            access_token="Atna|MOCK_TOKEN",  # noqa: S106
            domain="com",
            deregister_all=True,
        )

        # Verify request body
        call_kwargs = mock_post.call_args[1]
        body = call_kwargs["json"]
        assert body["deregister_all_existing_accounts"] is True

    @patch("audible.register.httpx.post")
    def test_deregister_authorization_header(
        self, mock_post: Mock, mock_deregister_response_success: dict[str, Any]
    ) -> None:
        """deregister() sends correct Authorization header."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_deregister_response_success
        mock_post.return_value = mock_response

        test_token = "Atna|TEST_ACCESS_TOKEN_123"  # noqa: S105
        register.deregister(
            access_token=test_token,
            domain="com",
        )

        # Verify Authorization header
        call_kwargs = mock_post.call_args[1]
        headers = call_kwargs["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {test_token}"

    @patch("audible.register.httpx.post")
    def test_deregister_error_response(self, mock_post: Mock) -> None:
        """deregister() raises exception on error response."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Unauthorized"}}
        mock_post.return_value = mock_response

        with pytest.raises(Exception):
            register.deregister(
                access_token="INVALID_TOKEN",  # noqa: S106
                domain="com",
            )

    @patch("audible.register.httpx.post")
    def test_deregister_single_device_default(
        self, mock_post: Mock, mock_deregister_response_success: dict[str, Any]
    ) -> None:
        """deregister() defaults to single device deregistration."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_deregister_response_success
        mock_post.return_value = mock_response

        register.deregister(
            access_token="Atna|MOCK_TOKEN",  # noqa: S106
            domain="com",
        )

        # Verify default is deregister_all=False
        call_kwargs = mock_post.call_args[1]
        body = call_kwargs["json"]
        assert body["deregister_all_existing_accounts"] is False
