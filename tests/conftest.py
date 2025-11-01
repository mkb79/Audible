"""Pytest configuration and fixtures for audible tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest


# Test password for encrypted fixtures
TEST_AUTH_PASSWORD = "test_password_123"  # noqa: S105


@pytest.fixture
def auth_fixture_path() -> Path:
    """Path to unencrypted auth fixture.

    Returns:
        Path to the unencrypted auth fixture JSON file.
    """
    return Path(__file__).parent / "fixtures" / "auth_fixture.json"


@pytest.fixture
def auth_fixture_encrypted_json_path() -> Path:
    """Path to JSON-encrypted auth fixture.

    Returns:
        Path to the JSON-encrypted auth fixture file.
    """
    return Path(__file__).parent / "fixtures" / "auth_fixture_encrypted_json.json"


@pytest.fixture
def auth_fixture_encrypted_bytes_path() -> Path:
    """Path to bytes-encrypted auth fixture.

    Returns:
        Path to the bytes-encrypted auth fixture file.
    """
    return Path(__file__).parent / "fixtures" / "auth_fixture_encrypted_bytes.bin"


@pytest.fixture
def auth_fixture_data(auth_fixture_path: Path) -> dict[str, Any]:
    """Load unencrypted auth fixture data.

    Args:
        auth_fixture_path: Path to the unencrypted fixture file.

    Returns:
        Dictionary containing the auth fixture data.
    """
    return cast(dict[str, Any], json.loads(auth_fixture_path.read_text()))


@pytest.fixture
def auth_fixture_encrypted_json_data(
    auth_fixture_encrypted_json_path: Path,
) -> dict[str, Any]:
    """Load JSON-encrypted auth fixture data (encrypted content).

    Args:
        auth_fixture_encrypted_json_path: Path to the JSON-encrypted fixture file.

    Returns:
        Dictionary containing salt, iv, and ciphertext.
    """
    return cast(
        dict[str, Any], json.loads(auth_fixture_encrypted_json_path.read_text())
    )


@pytest.fixture
def auth_fixture_encrypted_bytes_data(auth_fixture_encrypted_bytes_path: Path) -> bytes:
    """Load bytes-encrypted auth fixture data (raw encrypted bytes).

    Args:
        auth_fixture_encrypted_bytes_path: Path to the bytes-encrypted fixture file.

    Returns:
        Raw bytes of the encrypted fixture.
    """
    return auth_fixture_encrypted_bytes_path.read_bytes()


@pytest.fixture
def auth_fixture_password() -> str:
    """Password for encrypted auth fixtures.

    Returns:
        The test password used for encryption/decryption.
    """
    return TEST_AUTH_PASSWORD


@pytest.fixture
def rsa_private_key(auth_fixture_data: dict[str, Any]) -> str:
    """RSA private key from auth fixture data."""
    return cast(str, auth_fixture_data["device_private_key"])
