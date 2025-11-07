"""Tests for audible.activation_bytes module."""

from __future__ import annotations

import base64
import pathlib
import struct
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

from audible import Authenticator
from audible.activation_bytes import (
    extract_activation_bytes,
    fetch_activation,
    fetch_activation_sign_auth,
    get_activation_bytes,
    get_player_id,
    get_player_token,
)
from audible.exceptions import AuthFlowError


if TYPE_CHECKING:
    from typing import Any


class TestGetPlayerId:
    """Tests for get_player_id function."""

    def test_get_player_id_returns_string(self) -> None:
        """get_player_id returns a string."""
        result = get_player_id()
        assert isinstance(result, str)

    def test_get_player_id_is_base64(self) -> None:
        """get_player_id returns valid base64 string."""
        result = get_player_id()
        # Should be decodable as base64
        decoded = base64.b64decode(result)
        assert isinstance(decoded, bytes)

    def test_get_player_id_is_deterministic(self) -> None:
        """get_player_id returns same value every time."""
        result1 = get_player_id()
        result2 = get_player_id()
        assert result1 == result2

    def test_get_player_id_is_sha1_based(self) -> None:
        """get_player_id uses SHA1 hash."""
        result = get_player_id()
        # SHA1 produces 20 bytes, base64 of 20 bytes is 28 chars
        assert len(result) == 28


class TestGetPlayerToken:
    """Tests for get_player_token function."""

    def test_get_player_token_raises_without_locale(
        self, auth_fixture_data: dict[str, Any]
    ) -> None:
        """get_player_token raises if authenticator has no locale."""
        auth = Authenticator.from_dict(auth_fixture_data)
        auth.locale = None
        with pytest.raises(Exception, match="No locale set"):
            get_player_token(auth)

    @patch("audible.activation_bytes.httpx.Client")
    def test_get_player_token_makes_request(
        self, mock_client_class: Mock, auth_fixture_data: dict[str, Any]
    ) -> None:
        """get_player_token makes HTTP request to player-auth-token."""
        import httpx

        auth = Authenticator.from_dict(auth_fixture_data)

        # Mock the session and response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.url = httpx.URL(
            "https://www.audible.com/callback?playerToken=mock_token_123"
        )
        mock_session.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_session

        result = get_player_token(auth)

        assert result == "mock_token_123"
        mock_session.get.assert_called_once()

    @patch("audible.activation_bytes.httpx.Client")
    def test_get_player_token_raises_if_no_token_found(
        self, mock_client_class: Mock, auth_fixture_data: dict[str, Any]
    ) -> None:
        """get_player_token raises if playerToken not in response."""
        import httpx

        auth = Authenticator.from_dict(auth_fixture_data)

        # Mock response without playerToken
        mock_session = Mock()
        mock_response = Mock()
        mock_response.url = httpx.URL("https://www.audible.com/no-token")
        mock_session.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_session

        with pytest.raises(Exception, match="No player token found"):
            get_player_token(auth)


class TestExtractActivationBytes:
    """Tests for extract_activation_bytes function."""

    def test_extract_activation_bytes_validates_bad_login(self) -> None:
        """extract_activation_bytes raises on BAD_LOGIN in data."""
        data = b"BAD_LOGIN: Authentication failed"
        with pytest.raises(ValueError, match="data wrong"):
            extract_activation_bytes(data)

    def test_extract_activation_bytes_validates_whoops(self) -> None:
        """extract_activation_bytes raises on Whoops in data."""
        data = b"Whoops! Something went wrong"
        with pytest.raises(ValueError, match="data wrong"):
            extract_activation_bytes(data)

    def test_extract_activation_bytes_validates_group_id(self) -> None:
        """extract_activation_bytes raises if group_id not in data."""
        # Create data without "group_id" string anywhere
        # The validation happens BEFORE we try to extract the last 0x238 bytes
        data = b"Valid looking data but missing the required marker"
        with pytest.raises(ValueError, match="data wrong"):
            extract_activation_bytes(data)

    def test_extract_activation_bytes_with_valid_blob(self) -> None:
        """extract_activation_bytes extracts bytes from valid blob."""
        # Create a valid activation blob
        # The function takes last 0x238 (568) bytes
        activation_value = struct.pack("<I", 0x12345678)  # 4 bytes at start

        # Create 8 lines of 70 bytes + newline (total 568 bytes)
        line_data = activation_value + b"\x00" * (70 - len(activation_value))
        lines = []
        for i in range(8):
            if i == 0:
                lines.append(line_data)
            else:
                lines.append(b"\x00" * 70)
            lines.append(b"\n")

        formatted = b"".join(lines)
        assert len(formatted) == 568

        # Prepend metadata (must contain "group_id")
        full_blob = b"group_id=123&metadata=test&" + b"\x00" * 500 + formatted

        result = extract_activation_bytes(full_blob)

        assert isinstance(result, str)
        assert len(result) == 8
        # Format is direct hex representation of little-endian 32-bit int
        assert result == "12345678"

    def test_extract_activation_bytes_pads_short_values(self) -> None:
        """extract_activation_bytes pads values shorter than 8 chars."""
        # Create blob with small activation bytes value (0x00000001)
        activation_value = struct.pack("<I", 0x00000001)

        line_data = activation_value + b"\x00" * (70 - len(activation_value))
        lines = []
        for i in range(8):
            if i == 0:
                lines.append(line_data)
            else:
                lines.append(b"\x00" * 70)
            lines.append(b"\n")

        formatted = b"".join(lines)
        full_blob = b"group_id=456&data=test&" + b"\x00" * 500 + formatted

        result = extract_activation_bytes(full_blob)

        assert len(result) == 8
        assert result == "00000001"  # Padded with zeros


class TestFetchActivation:
    """Tests for fetch_activation function."""

    @patch("audible.activation_bytes.httpx.Client")
    def test_fetch_activation_makes_requests(self, mock_client_class: Mock) -> None:
        """fetch_activation makes register and deregister requests."""
        mock_activation = b"mock_activation_blob_with_group_id"

        # Mock the session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = mock_activation
        mock_session.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_session

        result = fetch_activation("test_player_token")

        assert result == mock_activation
        # Should make 3 calls: deregister, register, deregister
        assert mock_session.get.call_count == 3

    @patch("audible.activation_bytes.httpx.Client")
    def test_fetch_activation_uses_correct_headers(
        self, mock_client_class: Mock
    ) -> None:
        """fetch_activation uses Audible Download Manager user agent."""
        mock_activation = b"test_blob"

        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = mock_activation
        mock_session.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_session

        fetch_activation("test_token")

        # Check that Client was initialized with correct headers
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args[1]
        assert "headers" in call_kwargs
        assert call_kwargs["headers"]["User-Agent"] == "Audible Download Manager"

    @patch("audible.activation_bytes.httpx.Client")
    def test_fetch_activation_deregisters_after_error(
        self, mock_client_class: Mock
    ) -> None:
        """fetch_activation calls deregister even if register fails."""
        mock_session = Mock()

        # First call: deregister (success)
        # Second call: register (fails with exception)
        # Third call: deregister in finally block (success)
        def get_side_effect(*args: object, **kwargs: object) -> Mock:
            call_count = mock_session.get.call_count
            if call_count == 2:  # Register call fails
                raise Exception("Register failed")
            mock_resp = Mock()
            mock_resp.content = b"test"
            return mock_resp

        mock_session.get.side_effect = get_side_effect
        mock_client_class.return_value.__enter__.return_value = mock_session

        with pytest.raises(Exception, match="Register failed"):
            fetch_activation("test_token")

        # Should still call all 3 gets (deregister, register, deregister in finally)
        assert mock_session.get.call_count == 3


class TestFetchActivationSignAuth:
    """Tests for fetch_activation_sign_auth function."""

    def test_fetch_activation_sign_auth_raises_without_signing(
        self, auth_fixture_data: dict[str, Any]
    ) -> None:
        """fetch_activation_sign_auth raises if signing not available."""
        # Create auth without signing capability
        auth_data = auth_fixture_data.copy()
        # Remove private key to make signing unavailable
        if "device_private_key" in auth_data:
            del auth_data["device_private_key"]

        auth = Authenticator.from_dict(auth_data)

        with pytest.raises(AuthFlowError):
            fetch_activation_sign_auth(auth)

    @patch("audible.activation_bytes.httpx.Client")
    def test_fetch_activation_sign_auth_makes_request(
        self, mock_client_class: Mock, auth_fixture_data: dict[str, Any]
    ) -> None:
        """fetch_activation_sign_auth makes request with auth."""
        auth = Authenticator.from_dict(auth_fixture_data)
        mock_activation = b"mock_activation_with_group_id"

        # Mock the client and response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = mock_activation
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = fetch_activation_sign_auth(auth)

        assert result == mock_activation
        mock_client.get.assert_called_once()
        # Verify params are included
        call_args = mock_client.get.call_args
        assert call_args is not None


class TestGetActivationBytes:
    """Tests for get_activation_bytes function."""

    @patch("audible.activation_bytes.fetch_activation_sign_auth")
    def test_get_activation_bytes_with_signing_auth(
        self, mock_fetch: Mock, auth_fixture_data: dict[str, Any]
    ) -> None:
        """get_activation_bytes uses signing auth when available."""
        auth = Authenticator.from_dict(auth_fixture_data)

        # Create valid activation blob
        activation_value = struct.pack("<I", 0x12345678)
        line_data = activation_value + b"\x00" * 66
        lines = []
        for i in range(8):
            if i == 0:
                lines.append(line_data)
            else:
                lines.append(b"\x00" * 70)
            lines.append(b"\n")
        formatted = b"".join(lines)
        full_blob = b"group_id=123&data=test&" + b"\x00" * 500 + formatted

        mock_fetch.return_value = full_blob

        result = get_activation_bytes(auth)

        assert isinstance(result, str)
        assert len(result) == 8
        mock_fetch.assert_called_once_with(auth)

    @patch("audible.activation_bytes.get_player_token")
    @patch("audible.activation_bytes.fetch_activation")
    def test_get_activation_bytes_with_cookies_auth(
        self,
        mock_fetch_activation: Mock,
        mock_get_token: Mock,
        auth_fixture_data: dict[str, Any],
    ) -> None:
        """get_activation_bytes uses cookies auth when signing unavailable."""
        # Create auth without signing
        auth_data = auth_fixture_data.copy()
        if "device_private_key" in auth_data:
            del auth_data["device_private_key"]

        auth = Authenticator.from_dict(auth_data)

        # Create valid activation blob
        activation_value = struct.pack("<I", 0xABCDEF12)
        line_data = activation_value + b"\x00" * 66
        lines = []
        for i in range(8):
            if i == 0:
                lines.append(line_data)
            else:
                lines.append(b"\x00" * 70)
            lines.append(b"\n")
        formatted = b"".join(lines)
        full_blob = b"group_id=456&more=data&" + b"\x00" * 500 + formatted

        mock_get_token.return_value = "mock_player_token"
        mock_fetch_activation.return_value = full_blob

        result = get_activation_bytes(auth, extract=True)

        assert isinstance(result, str)
        assert len(result) == 8
        mock_get_token.assert_called_once_with(auth)
        mock_fetch_activation.assert_called_once_with("mock_player_token")

    def test_get_activation_bytes_raises_without_valid_auth(
        self, auth_fixture_data: dict[str, Any]
    ) -> None:
        """get_activation_bytes raises if no valid auth mode available."""
        # Create auth and mock available_auth_modes property
        auth = Authenticator.from_dict(auth_fixture_data)

        # Mock the property to return empty list
        with patch.object(
            type(auth),
            "available_auth_modes",
            new_callable=lambda: property(lambda self: []),
        ):
            with pytest.raises(AuthFlowError, match="No valid auth mode"):
                get_activation_bytes(auth)

    @patch("audible.activation_bytes.fetch_activation_sign_auth")
    def test_get_activation_bytes_saves_to_file(
        self,
        mock_fetch: Mock,
        auth_fixture_data: dict[str, Any],
        tmp_path: pathlib.Path,
    ) -> None:
        """get_activation_bytes saves blob to file when filename provided."""
        auth = Authenticator.from_dict(auth_fixture_data)

        # Create valid activation blob
        activation_value = struct.pack("<I", 0x11223344)
        line_data = activation_value + b"\x00" * 66
        lines = []
        for i in range(8):
            if i == 0:
                lines.append(line_data)
            else:
                lines.append(b"\x00" * 70)
            lines.append(b"\n")
        formatted = b"".join(lines)
        full_blob = b"group_id=789&test=data&" + b"\x00" * 500 + formatted

        mock_fetch.return_value = full_blob

        output_file = tmp_path / "activation.blob"
        result = get_activation_bytes(auth, filename=str(output_file), extract=True)

        assert output_file.exists()
        assert output_file.read_bytes() == full_blob
        assert isinstance(result, str)

    @patch("audible.activation_bytes.fetch_activation_sign_auth")
    def test_get_activation_bytes_returns_blob_when_extract_false(
        self, mock_fetch: Mock, auth_fixture_data: dict[str, Any]
    ) -> None:
        """get_activation_bytes returns raw blob when extract=False."""
        auth = Authenticator.from_dict(auth_fixture_data)

        # Create valid activation blob
        activation_value = struct.pack("<I", 0xDEADBEEF)
        line_data = activation_value + b"\x00" * 66
        lines = []
        for i in range(8):
            if i == 0:
                lines.append(line_data)
            else:
                lines.append(b"\x00" * 70)
            lines.append(b"\n")
        formatted = b"".join(lines)
        full_blob = b"group_id=999&blob=data&" + b"\x00" * 500 + formatted

        mock_fetch.return_value = full_blob

        result = get_activation_bytes(auth, extract=False)

        assert isinstance(result, bytes)
        assert result == full_blob
