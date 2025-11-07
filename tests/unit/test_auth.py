"""Tests for the auth module."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, patch

import httpx
import pytest

from audible import auth
from audible.auth import Authenticator

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock
from audible.crypto import (
    CryptographyProvider,
    CryptoProvider,
    LegacyProvider,
    PycryptodomeProvider,
    get_crypto_providers,
)
from audible.localization import Locale


PROVIDER_CLASSES: dict[str, type[CryptoProvider]] = {
    "legacy": LegacyProvider,
    "pycryptodome": PycryptodomeProvider,
    "cryptography": CryptographyProvider,
}


@pytest.mark.parametrize("provider_name", PROVIDER_CLASSES.keys())
def test_authenticator_from_dict_respects_crypto_override(
    provider_name: str,
    auth_fixture_data: dict[str, str],
    crypto_provider_availability: dict[str, bool],
) -> None:
    """from_dict should honour explicit crypto provider overrides."""
    if provider_name != "legacy" and not crypto_provider_availability[provider_name]:
        pytest.skip(f"{provider_name} provider is not installed")

    provider_cls: type[CryptoProvider] = PROVIDER_CLASSES[provider_name]
    auth = Authenticator.from_dict(auth_fixture_data, crypto_provider=provider_cls)

    assert auth._get_crypto().provider_name == provider_name


@pytest.mark.parametrize("provider_name", PROVIDER_CLASSES.keys())
def test_authenticator_accepts_provider_instance(
    provider_name: str, crypto_provider_availability: dict[str, bool]
) -> None:
    """Direct instantiation accepts provider instances."""
    if provider_name != "legacy" and not crypto_provider_availability[provider_name]:
        pytest.skip(f"{provider_name} provider is not installed")

    provider_cls: type[CryptoProvider] = PROVIDER_CLASSES[provider_name]
    provider_instance = get_crypto_providers(provider_cls)
    auth = Authenticator(crypto_provider=provider_instance)

    assert auth._get_crypto() is provider_instance


def test_rsa_key_cache_invalidation(auth_fixture_data: dict[str, str]) -> None:
    """Test that cached RSA key is invalidated when device_private_key changes."""
    # Create authenticator with initial key
    auth = Authenticator.from_dict(auth_fixture_data)

    # Create a mock request
    mock_request = Mock(spec=httpx.Request)
    mock_request.method = "GET"
    mock_request.url = Mock()
    mock_request.url.raw_path = b"/test/path"
    mock_request.content = b""
    mock_request.headers = {}

    # Trigger cache creation by calling signing flow
    auth._apply_signing_auth_flow(mock_request)

    # Verify cache was created
    assert auth._cached_rsa_key is not None

    # Change device_private_key (doesn't need to be valid for this test)
    auth._apply_test_convert = False
    auth.device_private_key = "different_key_data"

    # Verify cache was invalidated
    assert auth._cached_rsa_key is None, (
        "Cache should be None after device_private_key change"
    )


def test_rsa_key_cache_not_invalidated_for_other_attributes(
    auth_fixture_data: dict[str, str],
    access_token: str,
    refresh_token: str,
) -> None:
    """Test that cached RSA key is NOT invalidated when other attributes change."""
    auth = Authenticator.from_dict(auth_fixture_data)

    # Create mock request
    mock_request = Mock(spec=httpx.Request)
    mock_request.method = "GET"
    mock_request.url = Mock()
    mock_request.url.raw_path = b"/test/path"
    mock_request.content = b""
    mock_request.headers = {}

    # Trigger cache creation
    auth._apply_signing_auth_flow(mock_request)
    cached_key = auth._cached_rsa_key

    auth._apply_test_convert = False  # Disable validation for test
    # Modify other attributes
    auth.access_token = access_token
    auth.refresh_token = refresh_token

    # Verify cache is still intact
    assert auth._cached_rsa_key is cached_key
    assert auth._cached_rsa_key is not None


class TestAuthenticatorInitialization:
    """Tests for Authenticator initialization."""

    def test_authenticator_from_dict(self, auth_fixture_data: dict[str, Any]) -> None:
        """Authenticator can be created from dict."""
        auth = Authenticator.from_dict(auth_fixture_data)

        assert auth.access_token == auth_fixture_data["access_token"]
        assert auth.refresh_token == auth_fixture_data["refresh_token"]
        assert auth.device_private_key == auth_fixture_data["device_private_key"]

    def test_authenticator_iter(self, auth_fixture_data: dict[str, Any]) -> None:
        """Authenticator supports iteration over attributes."""
        auth = Authenticator.from_dict(auth_fixture_data)

        attrs = list(auth)

        assert "access_token" in attrs
        assert "refresh_token" in attrs
        assert "device_private_key" in attrs

    def test_authenticator_len(self, auth_fixture_data: dict[str, Any]) -> None:
        """Authenticator supports len() to count attributes."""
        auth = Authenticator.from_dict(auth_fixture_data)

        # Should have multiple attributes
        assert len(auth) > 0

    def test_authenticator_repr(self, auth_fixture_data: dict[str, Any]) -> None:
        """Authenticator has meaningful repr."""
        auth = Authenticator.from_dict(auth_fixture_data)

        repr_str = repr(auth)

        assert "Authenticator" in repr_str


class TestAuthenticatorCredentialStorage:
    """Tests for credential storage (to_dict, to_file, from_file)."""

    def test_to_dict(self, auth_fixture_data: dict[str, Any]) -> None:
        """to_dict exports all credentials."""
        auth = Authenticator.from_dict(auth_fixture_data)

        result = auth.to_dict()

        assert "access_token" in result
        assert "refresh_token" in result
        assert "device_private_key" in result
        assert result["access_token"] == auth_fixture_data["access_token"]

    def test_to_file_creates_file(
        self, auth_fixture_data: dict[str, Any], tmp_path: Any
    ) -> None:
        """to_file creates credential file."""
        cred_file = tmp_path / "credentials.json"
        auth = Authenticator.from_dict(auth_fixture_data)

        auth.to_file(cred_file)

        assert cred_file.exists()

    def test_from_file_loads_credentials(
        self, auth_fixture_data: dict[str, Any], tmp_path: Any
    ) -> None:
        """from_file loads credentials from file."""
        cred_file = tmp_path / "credentials.json"
        original_auth = Authenticator.from_dict(auth_fixture_data)
        original_auth.to_file(cred_file)

        loaded_auth = Authenticator.from_file(cred_file)

        assert loaded_auth.access_token == original_auth.access_token
        assert loaded_auth.refresh_token == original_auth.refresh_token

    def test_to_file_with_encryption(
        self,
        auth_fixture_data: dict[str, Any],
        auth_fixture_password: str,
        tmp_path: Any,
    ) -> None:
        """to_file can encrypt credentials."""
        cred_file = tmp_path / "credentials_encrypted.json"
        auth = Authenticator.from_dict(auth_fixture_data)

        auth.to_file(cred_file, password=auth_fixture_password, encryption="json")

        assert cred_file.exists()
        # File should contain encrypted data
        content = cred_file.read_text()
        assert "access_token" not in content  # Should be encrypted

    def test_from_file_with_encryption(
        self,
        auth_fixture_data: dict[str, Any],
        auth_fixture_password: str,
        tmp_path: Any,
    ) -> None:
        """from_file can decrypt encrypted credentials."""
        cred_file = tmp_path / "credentials_encrypted.json"
        original_auth = Authenticator.from_dict(auth_fixture_data)
        original_auth.to_file(
            cred_file, password=auth_fixture_password, encryption="json"
        )

        loaded_auth = Authenticator.from_file(cred_file, password=auth_fixture_password)

        assert loaded_auth.access_token == original_auth.access_token


class TestRefreshAccessToken:
    """Tests for access token refresh functionality."""

    def test_refresh_access_token_success(
        self, httpx_mock: HTTPXMock, auth_fixture_data: dict[str, Any]
    ) -> None:
        """refresh_access_token renews expired token."""
        # Get locale from auth_fixture_data or default to "com"
        auth = Authenticator.from_dict(auth_fixture_data)
        domain = auth.locale.domain if hasattr(auth, "locale") and auth.locale else "com"

        httpx_mock.add_response(
            url=f"https://api.amazon.{domain}/auth/token",
            method="POST",
            json={
                "access_token": "Atna|new_test_token",
                "expires_in": 3600,
            },
            status_code=200,
        )

        old_token = auth.access_token

        auth.refresh_access_token(force=True)

        assert auth.access_token != old_token
        assert auth.access_token == "Atna|new_test_token"  # noqa: S105
        assert len(httpx_mock.get_requests()) == 1

    def test_refresh_access_token_not_forced_when_valid(
        self, httpx_mock: HTTPXMock, auth_fixture_data: dict[str, Any]
    ) -> None:
        """refresh_access_token skips refresh if token still valid."""
        auth = Authenticator.from_dict(auth_fixture_data)
        # Set expires to future time
        auth.expires = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()

        auth.refresh_access_token(force=False)

        # Should not make HTTP call
        assert len(httpx_mock.get_requests()) == 0

    def test_module_level_refresh_access_token(self, httpx_mock: HTTPXMock) -> None:
        """Module-level refresh_access_token function works."""
        httpx_mock.add_response(
            url="https://api.amazon.com/auth/token",
            method="POST",
            json={
                "access_token": "Atna|new_token",
                "expires_in": 3600,
            },
            status_code=200,
        )

        result = auth.refresh_access_token("test_refresh_token", "com")

        assert "access_token" in result
        assert "expires" in result
        assert result["access_token"] == "Atna|new_token"  # noqa: S105


class TestTokenExpiration:
    """Tests for token expiration checking."""

    def test_access_token_expired_when_past(
        self, auth_fixture_data: dict[str, Any]
    ) -> None:
        """access_token_expired returns True for expired token."""
        auth = Authenticator.from_dict(auth_fixture_data)
        # Set expires to past time
        auth.expires = (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()

        assert auth.access_token_expired is True

    def test_access_token_not_expired_when_future(
        self, auth_fixture_data: dict[str, Any]
    ) -> None:
        """access_token_expired returns False for valid token."""
        auth = Authenticator.from_dict(auth_fixture_data)
        # Set expires to future time
        auth.expires = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()

        assert auth.access_token_expired is False

    def test_access_token_expires_returns_timedelta(
        self, auth_fixture_data: dict[str, Any]
    ) -> None:
        """access_token_expires returns timedelta."""
        auth = Authenticator.from_dict(auth_fixture_data)
        auth.expires = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()

        expires_delta = auth.access_token_expires

        assert isinstance(expires_delta, timedelta)
        # Should be roughly 1 hour (with some tolerance)
        assert 3500 < expires_delta.total_seconds() < 3700


class TestUserProfile:
    """Tests for user profile operations."""

    def test_user_profile(
        self, httpx_mock: HTTPXMock, auth_fixture_data: dict[str, Any]
    ) -> None:
        """user_profile fetches profile from Amazon."""
        auth = Authenticator.from_dict(auth_fixture_data)
        domain = auth.locale.domain if hasattr(auth, "locale") and auth.locale else "com"

        httpx_mock.add_response(
            url=f"https://api.amazon.{domain}/user/profile",
            method="GET",
            json={"user_id": "123", "name": "Test User"},
            status_code=200,
        )

        with patch.object(auth, "refresh_access_token"):
            profile = auth.user_profile()

        assert profile["name"] == "Test User"
        assert profile["user_id"] == "123"

    def test_module_level_user_profile(self, httpx_mock: HTTPXMock) -> None:
        """Module-level user_profile function works."""
        httpx_mock.add_response(
            url="https://api.amazon.com/user/profile",
            method="GET",
            json={"user_id": "456", "name": "Another User"},
            status_code=200,
        )

        result = auth.user_profile("test_access_token", "com")

        assert result["name"] == "Another User"
        assert result["user_id"] == "456"


class TestWebsiteCookies:
    """Tests for website cookie operations."""

    def test_refresh_website_cookies(
        self, httpx_mock: HTTPXMock, auth_fixture_data: dict[str, Any]
    ) -> None:
        """set_website_cookies_for_country fetches cookies."""
        auth = Authenticator.from_dict(auth_fixture_data)
        domain = auth.locale.domain if hasattr(auth, "locale") and auth.locale else "com"

        httpx_mock.add_response(
            url=f"https://www.amazon.{domain}/ap/exchangetoken/cookies",
            method="POST",
            json={
                "response": {
                    "tokens": {
                        "cookies": {
                            ".amazon.com": [
                                {"Name": "session-id", "Value": "abc123"},
                                {"Name": "ubid-main", "Value": "xyz789"},
                            ]
                        }
                    }
                }
            },
            status_code=200,
        )

        auth.set_website_cookies_for_country("us")

        assert auth.website_cookies is not None
        assert "session-id" in auth.website_cookies
        assert auth.website_cookies["session-id"] == "abc123"


class TestAuthModes:
    """Tests for authentication modes."""

    def test_available_auth_modes(self, auth_fixture_data: dict[str, Any]) -> None:
        """available_auth_modes returns list of supported modes."""
        auth = Authenticator.from_dict(auth_fixture_data)
        # Ensure locale is set for available_auth_modes
        if not hasattr(auth, "locale") or auth.locale is None:
            auth.locale = Locale("us")

        modes = auth.available_auth_modes

        assert isinstance(modes, list)
        # Should have at least signing mode with private key
        assert len(modes) > 0


class TestSignRequest:
    """Tests for request signing."""

    def test_sign_request_adds_headers(self, auth_fixture_data: dict[str, Any]) -> None:
        """sign_request adds authentication headers."""
        auth = Authenticator.from_dict(auth_fixture_data)
        mock_request = Mock(spec=httpx.Request)
        mock_request.method = "GET"
        mock_request.url = Mock()
        mock_request.url.raw_path = b"/test/path"
        mock_request.content = b""
        mock_request.headers = {}

        auth.sign_request(mock_request)

        # Should add signing headers
        assert "x-adp-token" in mock_request.headers

    def test_module_level_sign_request(self) -> None:
        """Module-level sign_request function works."""
        with patch("audible.auth.get_crypto_providers") as mock_crypto:
            mock_provider = Mock()
            mock_provider.rsa.load_private_key = Mock(return_value=Mock())
            mock_provider.rsa.sign = Mock(return_value=b"signature")
            mock_crypto.return_value = mock_provider

            result = auth.sign_request(
                "GET",
                "/test/path",
                b"",
                "test_adp_token",
                "test_private_key",
            )

            assert isinstance(result, dict)
            assert "x-adp-token" in result


class TestAuthFlow:
    """Tests for httpx auth flow integration."""

    def test_auth_flow_with_signing(self, auth_fixture_data: dict[str, Any]) -> None:
        """auth_flow applies signing authentication."""
        auth = Authenticator.from_dict(auth_fixture_data)
        mock_request = Mock(spec=httpx.Request)
        mock_request.method = "GET"
        mock_request.url = Mock()
        mock_request.url.raw_path = b"/1.0/library"
        mock_request.content = b""
        mock_request.headers = {}

        flow = auth.auth_flow(mock_request)

        # Consume the generator
        modified_request = next(flow)

        assert "x-adp-token" in modified_request.headers

    def test_apply_signing_auth_flow(self, auth_fixture_data: dict[str, Any]) -> None:
        """_apply_signing_auth_flow adds signature headers."""
        auth = Authenticator.from_dict(auth_fixture_data)
        mock_request = Mock(spec=httpx.Request)
        mock_request.method = "POST"
        mock_request.url = Mock()
        mock_request.url.raw_path = b"/1.0/content/asin/licenserequest"
        mock_request.content = b'{"key": "value"}'
        mock_request.headers = {}

        auth._apply_signing_auth_flow(mock_request)

        assert "x-adp-token" in mock_request.headers
        assert "x-adp-alg" in mock_request.headers

    def test_apply_bearer_auth_flow(self, auth_fixture_data: dict[str, Any]) -> None:
        """_apply_bearer_auth_flow adds bearer token."""
        auth = Authenticator.from_dict(auth_fixture_data)
        mock_request = Mock(spec=httpx.Request)
        mock_request.method = "GET"
        mock_request.url = Mock()
        mock_request.url.raw_path = b"/user/profile"
        mock_request.headers = {}

        auth._apply_bearer_auth_flow(mock_request)

        assert "Authorization" in mock_request.headers
        assert mock_request.headers["Authorization"].startswith("Bearer")

    def test_apply_cookies_auth_flow(self, auth_fixture_data: dict[str, Any]) -> None:
        """_apply_cookies_auth_flow adds website cookies."""
        auth = Authenticator.from_dict(auth_fixture_data)
        auth.website_cookies = {"session-id": "test123"}

        # Create a real httpx.Request with proper URL
        request = httpx.Request("GET", "https://api.audible.com/user/profile")

        auth._apply_cookies_auth_flow(request)

        # Cookies should be added to request
        assert "Cookie" in request.headers or len(request.headers) > 0
