"""Tests for the auth module."""

from __future__ import annotations

from unittest.mock import Mock

import httpx

from audible.auth import Authenticator


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
