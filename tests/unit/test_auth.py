"""Tests for the auth module."""

from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest

from audible.auth import Authenticator
from audible.crypto import (
    CryptographyProvider,
    CryptoProvider,
    LegacyProvider,
    PycryptodomeProvider,
    get_crypto_providers,
)


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
