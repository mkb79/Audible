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
    auth.access_token = "new_access_token"  # noqa: S105
    auth.refresh_token = "new_refresh_token"  # noqa: S105

    # Verify cache is still intact
    assert auth._cached_rsa_key is cached_key
    assert auth._cached_rsa_key is not None


# Device Integration Tests


def test_authenticator_with_device_parameter(auth_fixture_data: dict[str, str]) -> None:
    """Test that Authenticator stores device when provided."""
    from audible.device import IPHONE

    auth = Authenticator.from_dict(auth_fixture_data, device=IPHONE)

    assert auth.device is not None
    assert auth.device.device_type == IPHONE.device_type
    assert auth.device.device_model == IPHONE.device_model
    assert auth.device.os_family == "ios"


def test_authenticator_without_device_parameter(auth_fixture_data: dict[str, str]) -> None:
    """Test that Authenticator works without device (backward compatibility)."""
    auth = Authenticator.from_dict(auth_fixture_data)

    assert auth.device is None


def test_authenticator_to_dict_includes_device(auth_fixture_data: dict[str, str]) -> None:
    """Test that to_dict() includes device field when device is set."""
    from audible.device import ANDROID

    auth = Authenticator.from_dict(auth_fixture_data, device=ANDROID)
    auth_dict = auth.to_dict()

    assert "device" in auth_dict
    assert auth_dict["device"]["device_type"] == ANDROID.device_type
    assert auth_dict["device"]["device_model"] == ANDROID.device_model
    assert auth_dict["device"]["os_family"] == "android"


def test_authenticator_to_dict_excludes_device_when_none(
    auth_fixture_data: dict[str, str],
) -> None:
    """Test that to_dict() excludes device field when device is None."""
    auth = Authenticator.from_dict(auth_fixture_data)
    auth_dict = auth.to_dict()

    assert "device" not in auth_dict


def test_authenticator_from_dict_with_device_field() -> None:
    """Test that from_dict() restores device from dictionary."""
    from audible.device import IPHONE_16

    auth_data = {
        "access_token": "Atna|test_access_token_1234567890",  # noqa: S105
        "refresh_token": "Atnr|test_refresh_token_1234567890",  # noqa: S105
        "device_private_key": (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEpAIBAAKCAQEA1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJ\n"
            "-----END RSA PRIVATE KEY-----\n"
        ),
        "device": IPHONE_16.to_dict(),
    }

    auth = Authenticator.from_dict(auth_data)

    assert auth.device is not None
    assert auth.device.device_type == IPHONE_16.device_type
    assert auth.device.device_model == IPHONE_16.device_model
    assert auth.device.app_version == IPHONE_16.app_version
    assert auth.device.os_version == IPHONE_16.os_version


def test_authenticator_from_dict_backward_compatibility() -> None:
    """Test that from_dict() works with old auth files without device field."""
    auth_data = {
        "access_token": "Atna|test_access_token_1234567890",  # noqa: S105
        "refresh_token": "Atnr|test_refresh_token_1234567890",  # noqa: S105
        "device_private_key": (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEpAIBAAKCAQEA1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJ\n"
            "-----END RSA PRIVATE KEY-----\n"
        ),
        # No "device" field
    }

    auth = Authenticator.from_dict(auth_data)

    assert auth.access_token == "Atna|test_access_token_1234567890"
    assert auth.refresh_token == "Atnr|test_refresh_token_1234567890"
    assert auth.device is None  # Should be None for old auth files


def test_authenticator_device_round_trip_serialization(
    auth_fixture_data: dict[str, str],
) -> None:
    """Test that device survives to_dict() -> from_dict() round-trip."""
    from audible.device import ANDROID_PIXEL_7

    # Create auth with device
    original = Authenticator.from_dict(auth_fixture_data, device=ANDROID_PIXEL_7)

    # Serialize and deserialize
    auth_dict = original.to_dict()
    restored = Authenticator.from_dict(auth_dict)

    # Verify device was preserved
    assert restored.device is not None
    assert restored.device.device_type == ANDROID_PIXEL_7.device_type
    assert restored.device.device_model == ANDROID_PIXEL_7.device_model
    assert restored.device.device_product == ANDROID_PIXEL_7.device_product
    assert restored.device.app_version == ANDROID_PIXEL_7.app_version
    assert restored.device.os_version == ANDROID_PIXEL_7.os_version
    assert restored.device.os_family == "android"
    # Serial should be the same (not regenerated)
    assert restored.device.device_serial == original.device.device_serial


def test_authenticator_file_round_trip_with_device(
    auth_fixture_data: dict[str, str], tmp_path
) -> None:
    """Test that device survives to_file() -> from_file() round-trip."""
    from pathlib import Path

    from audible.device import IPHONE

    # Create auth with device
    original = Authenticator.from_dict(auth_fixture_data, device=IPHONE)

    # Save to file
    auth_file = tmp_path / "auth_with_device.json"
    original.to_file(auth_file, encryption=False)

    # Load from file
    restored = Authenticator.from_file(auth_file)

    # Verify device was preserved
    assert restored.device is not None
    assert restored.device.device_type == IPHONE.device_type
    assert restored.device.device_model == IPHONE.device_model
    assert restored.device.app_version == IPHONE.app_version
    assert restored.device.user_agent == IPHONE.user_agent
    assert restored.device.device_serial == original.device.device_serial


def test_authenticator_file_round_trip_without_device(
    auth_fixture_data: dict[str, str], tmp_path
) -> None:
    """Test that auth files without device still work (backward compatibility)."""
    from pathlib import Path

    # Create auth without device
    original = Authenticator.from_dict(auth_fixture_data)

    # Save to file
    auth_file = tmp_path / "auth_without_device.json"
    original.to_file(auth_file, encryption=False)

    # Load from file
    restored = Authenticator.from_file(auth_file)

    # Verify no device
    assert restored.device is None
    assert restored.access_token == original.access_token


def test_authenticator_encrypted_file_with_device(
    auth_fixture_data: dict[str, str], tmp_path, auth_fixture_password: str
) -> None:
    """Test encrypted file storage with device parameter."""
    from audible.device import ANDROID

    # Create auth with device
    original = Authenticator.from_dict(auth_fixture_data, device=ANDROID)

    # Save encrypted
    auth_file = tmp_path / "auth_encrypted_with_device.json"
    original.to_file(auth_file, password=auth_fixture_password, encryption="json")

    # Load encrypted
    restored = Authenticator.from_file(auth_file, password=auth_fixture_password)

    # Verify device survived encryption/decryption
    assert restored.device is not None
    assert restored.device.device_type == ANDROID.device_type
    assert restored.device.os_family == "android"


def test_authenticator_device_parameter_overrides_dict_device() -> None:
    """Test that explicit device parameter overrides device in dict."""
    from audible.device import ANDROID, IPHONE

    auth_data = {
        "access_token": "Atna|test_access_token_1234567890",  # noqa: S105
        "refresh_token": "Atnr|test_refresh_token_1234567890",  # noqa: S105
        "device_private_key": (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEpAIBAAKCAQEA1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJ\n"
            "-----END RSA PRIVATE KEY-----\n"
        ),
        "device": ANDROID.to_dict(),  # Android in dict
    }

    # But override with iPhone
    auth = Authenticator.from_dict(auth_data, device=IPHONE)

    # Should use IPHONE, not ANDROID
    assert auth.device is not None
    assert auth.device.device_type == IPHONE.device_type
    assert auth.device.os_family == "ios"
