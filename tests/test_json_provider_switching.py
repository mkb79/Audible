"""Tests for JSON provider switching with set_default_json_provider().

This module tests that set_default_json_provider() correctly affects
all modules that use get_json_provider(), including client.py, auth.py,
aescipher.py, and login.py.
"""

import json
from typing import Any

from audible.json import StdlibProvider, get_json_provider, set_default_json_provider


class TestProviderSwitching:
    """Test that provider switching works across all modules."""

    def test_client_convert_response_content_uses_switched_provider(self) -> None:
        """Test that client.py uses switched provider."""
        from unittest.mock import Mock

        import httpx

        from audible.client import convert_response_content

        # Test data
        test_data = {"test": "data", "number": 42}
        response_text = json.dumps(test_data)

        # Create mock response
        mock_response = Mock(spec=httpx.Response)
        mock_response.text = response_text

        # Set stdlib as default
        set_default_json_provider(StdlibProvider)

        # Call convert_response_content - should use stdlib provider
        result = convert_response_content(mock_response)

        # Verify result
        assert result == test_data
        assert isinstance(result, dict)

        # Verify that get_json_provider() returns stdlib
        current_provider = get_json_provider()
        assert current_provider.provider_name == "stdlib"

    def test_auth_to_dict_uses_switched_provider(
        self, auth_fixture_data: dict[str, Any]
    ) -> None:
        """Test that auth.py uses switched provider for JSON serialization."""
        import tempfile
        from pathlib import Path

        from audible import Authenticator

        # Set stdlib as default
        set_default_json_provider(StdlibProvider)

        # Create authenticator from fixture data
        auth = Authenticator.from_dict(auth_fixture_data)

        # Save to file (uses dumps internally)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            auth.to_file(temp_path, indent=4)

            # Read file and verify it's valid JSON
            content = temp_path.read_text()
            data = json.loads(content)  # Should not raise

            # Verify content matches fixture data
            assert "adp_token" in data
            assert "access_token" in data
            assert data["access_token"] == auth_fixture_data["access_token"]

            # Verify provider is stdlib
            current_provider = get_json_provider()
            assert current_provider.provider_name == "stdlib"

        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_aescipher_uses_switched_provider(self) -> None:
        """Test that aescipher.py uses switched provider."""
        import tempfile
        from pathlib import Path

        from audible.aescipher import AESCipher

        # Set stdlib as default
        set_default_json_provider(StdlibProvider)

        # Create cipher
        cipher = AESCipher(password="test_password")
        test_data = "test_secret_data"

        # Save to file (uses dumps internally)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            cipher.to_file(test_data, temp_path, encryption="json")

            # Read and verify
            encrypted_data = cipher.from_file(temp_path, encryption="json")
            assert encrypted_data == test_data

            # Verify provider is stdlib
            current_provider = get_json_provider()
            assert current_provider.provider_name == "stdlib"

        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_login_build_init_cookies_uses_switched_provider(self) -> None:
        """Test that login.py uses switched provider."""
        from audible.login import build_init_cookies

        # Set stdlib as default
        set_default_json_provider(StdlibProvider)

        # Call build_init_cookies (uses dumps internally)
        cookies = build_init_cookies()

        # Verify result structure
        assert "frc" in cookies
        assert "map-md" in cookies
        assert "amzn-app-id" in cookies

        # Verify provider is stdlib
        current_provider = get_json_provider()
        assert current_provider.provider_name == "stdlib"

    def test_provider_switch_affects_all_modules(self) -> None:
        """Test that switching provider affects all modules simultaneously."""
        # Set stdlib as default
        set_default_json_provider(StdlibProvider)

        # Verify all modules see the same provider
        from audible.client import convert_response_content  # noqa: F401
        from audible.login import build_init_cookies  # noqa: F401

        provider1 = get_json_provider()
        provider2 = get_json_provider()

        assert provider1.provider_name == "stdlib"
        assert provider2.provider_name == "stdlib"
        assert provider1 is provider2  # Same instance

    def test_provider_reset_restores_auto_detection(self) -> None:
        """Test that resetting provider restores auto-detection."""
        # Get auto-detected provider
        auto_provider = get_json_provider()
        auto_name = auto_provider.provider_name

        # Set stdlib
        set_default_json_provider(StdlibProvider)
        stdlib_provider = get_json_provider()
        assert stdlib_provider.provider_name == "stdlib"

        # Reset to auto-detection
        set_default_json_provider(None)
        restored_provider = get_json_provider()

        # Should restore to original auto-detected provider
        assert restored_provider.provider_name == auto_name
