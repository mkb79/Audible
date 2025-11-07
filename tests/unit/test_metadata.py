"""Tests for audible.metadata module."""

from __future__ import annotations

import json

import pytest

from audible.metadata import (
    METADATA_KEY,
    XXTEA,
    XXTEAException,
    _bytes_to_longs,
    _generate_hex_checksum,
    _longs_to_bytes,
    decrypt_metadata,
    encrypt_metadata,
    meta_audible_app,
    metadata_crypter,
    now_to_unix_ms,
    raw_xxtea,
)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_bytes_to_longs_with_bytes(self) -> None:
        """_bytes_to_longs converts bytes to list of integers."""
        data = b"test"
        result = _bytes_to_longs(data)
        assert isinstance(result, list)
        assert all(isinstance(x, int) for x in result)

    def test_bytes_to_longs_with_string(self) -> None:
        """_bytes_to_longs converts string to list of integers."""
        data = "test"
        result = _bytes_to_longs(data)
        assert isinstance(result, list)
        assert all(isinstance(x, int) for x in result)

    def test_longs_to_bytes_returns_bytes(self) -> None:
        """_longs_to_bytes converts list of integers to bytes."""
        # Create a simple list of ints
        data = [1, 2]
        result = _longs_to_bytes(data)
        assert isinstance(result, bytes)
        assert len(result) == 8  # 2 ints * 4 bytes each

    def test_bytes_longs_roundtrip(self) -> None:
        """Bytes -> longs -> bytes roundtrip preserves data."""
        original = b"test data for roundtrip"
        # Pad to multiple of 4 bytes
        padded = original + b"\x00" * (4 - len(original) % 4)
        longs = _bytes_to_longs(padded)
        recovered = _longs_to_bytes(longs)
        assert recovered == padded

    def test_generate_hex_checksum_returns_8_chars(self) -> None:
        """_generate_hex_checksum returns 8-character hex string."""
        result = _generate_hex_checksum("test data")
        assert len(result) == 8
        assert all(c in "0123456789ABCDEF" for c in result)

    def test_generate_hex_checksum_is_deterministic(self) -> None:
        """_generate_hex_checksum returns same value for same input."""
        data = "test data"
        checksum1 = _generate_hex_checksum(data)
        checksum2 = _generate_hex_checksum(data)
        assert checksum1 == checksum2

    def test_generate_hex_checksum_pads_short_values(self) -> None:
        """_generate_hex_checksum pads checksums shorter than 8 chars."""
        # Use data that produces a short checksum
        result = _generate_hex_checksum("x")
        assert len(result) == 8

    def test_now_to_unix_ms_returns_int(self) -> None:
        """now_to_unix_ms returns integer milliseconds."""
        result = now_to_unix_ms()
        assert isinstance(result, int)
        assert result > 0

    def test_now_to_unix_ms_is_reasonable(self) -> None:
        """now_to_unix_ms returns reasonable current timestamp."""
        result = now_to_unix_ms()
        # Should be after 2020-01-01 and before 2100-01-01
        assert 1577836800000 < result < 4102444800000


class TestRawXXTEA:
    """Tests for raw_xxtea function."""

    def test_raw_xxtea_validates_v_is_list(self) -> None:
        """raw_xxtea raises ValueError if v is not a list."""
        with pytest.raises(ValueError, match="arg `v` is not of type list"):
            raw_xxtea("not a list", 1, [1, 2, 3, 4])  # type: ignore[arg-type]

    def test_raw_xxtea_validates_k_is_list_or_tuple(self) -> None:
        """raw_xxtea raises ValueError if k is not list or tuple."""
        with pytest.raises(ValueError, match="arg `key` is not of type list or tuple"):
            raw_xxtea([1, 2, 3, 4], 2, "not a list")  # type: ignore[arg-type]

    def test_raw_xxtea_validates_n_is_int(self) -> None:
        """raw_xxtea raises ValueError if n is not int."""
        with pytest.raises(ValueError, match="arg `n` is not of type int"):
            raw_xxtea([1, 2, 3, 4], "not an int", [1, 2, 3, 4])  # type: ignore[arg-type]

    def test_raw_xxtea_encoding_returns_zero(self) -> None:
        """raw_xxtea returns 0 for successful encoding (n > 1)."""
        v = [1, 2, 3, 4]
        k = [1, 2, 3, 4]
        result = raw_xxtea(v, 4, k)
        assert result == 0

    def test_raw_xxtea_decoding_returns_zero(self) -> None:
        """raw_xxtea returns 0 for successful decoding (n < -1)."""
        v = [1, 2, 3, 4]
        k = [1, 2, 3, 4]
        # First encrypt
        raw_xxtea(v, 4, k)
        # Then decrypt
        result = raw_xxtea(v, -4, k)
        assert result == 0

    def test_raw_xxtea_invalid_n_returns_one(self) -> None:
        """raw_xxtea returns 1 for invalid n values."""
        v = [1, 2, 3, 4]
        k = [1, 2, 3, 4]
        # n = 0, -1, or 1 should return 1
        assert raw_xxtea(v, 0, k) == 1
        assert raw_xxtea(v, 1, k) == 1
        assert raw_xxtea(v, -1, k) == 1


class TestXXTEAClass:
    """Tests for XXTEA class."""

    def test_xxtea_init_with_bytes_key(self) -> None:
        """XXTEA can be initialized with bytes key."""
        key = b"0123456789ABCDEF"  # 16 bytes
        xxtea = XXTEA(key)
        assert xxtea.key is not None

    def test_xxtea_init_with_string_key(self) -> None:
        """XXTEA can be initialized with string key."""
        key = "0123456789ABCDEF"  # 16 characters
        xxtea = XXTEA(key)
        assert xxtea.key is not None

    def test_xxtea_init_raises_on_invalid_key_length(self) -> None:
        """XXTEA raises XXTEAException for invalid key length."""
        with pytest.raises(XXTEAException, match="Invalid key"):
            XXTEA(b"short")

        with pytest.raises(XXTEAException, match="Invalid key"):
            XXTEA(b"this key is way too long for XXTEA")

    def test_xxtea_encrypt_returns_bytes(self) -> None:
        """XXTEA.encrypt returns bytes."""
        xxtea = XXTEA(METADATA_KEY)
        result = xxtea.encrypt("test data")
        assert isinstance(result, bytes)

    def test_xxtea_decrypt_returns_bytes(self) -> None:
        """XXTEA.decrypt returns bytes."""
        xxtea = XXTEA(METADATA_KEY)
        encrypted = xxtea.encrypt("test data")
        result = xxtea.decrypt(encrypted)
        assert isinstance(result, bytes)

    def test_xxtea_encrypt_decrypt_roundtrip_with_string(self) -> None:
        """XXTEA encrypt/decrypt roundtrip preserves string data."""
        xxtea = XXTEA(METADATA_KEY)
        original = "test data for encryption"
        encrypted = xxtea.encrypt(original)
        decrypted = xxtea.decrypt(encrypted).decode("utf-8")
        assert decrypted == original

    def test_xxtea_encrypt_decrypt_roundtrip_with_bytes(self) -> None:
        """XXTEA encrypt/decrypt roundtrip preserves bytes data."""
        xxtea = XXTEA(METADATA_KEY)
        original = b"test data for encryption"
        encrypted = xxtea.encrypt(original)
        decrypted = xxtea.decrypt(encrypted)
        assert decrypted == original

    def test_xxtea_decrypt_strips_null_bytes(self) -> None:
        """XXTEA.decrypt strips trailing null bytes from padding."""
        xxtea = XXTEA(METADATA_KEY)
        # String shorter than 8 bytes will have padding
        original = "test123"  # 7 bytes, will be padded to 8
        encrypted = xxtea.encrypt(original)
        decrypted = xxtea.decrypt(encrypted).decode("utf-8")
        assert decrypted == original
        assert "\x00" not in decrypted


class TestMetadataCrypter:
    """Tests for metadata_crypter instance."""

    def test_metadata_crypter_is_xxtea_instance(self) -> None:
        """metadata_crypter is an XXTEA instance."""
        assert isinstance(metadata_crypter, XXTEA)

    def test_metadata_crypter_can_encrypt(self) -> None:
        """metadata_crypter can encrypt data."""
        result = metadata_crypter.encrypt("test data")  # At least 8 bytes
        assert isinstance(result, bytes)

    def test_metadata_crypter_can_decrypt(self) -> None:
        """metadata_crypter can decrypt data."""
        encrypted = metadata_crypter.encrypt("test data")  # At least 8 bytes
        result = metadata_crypter.decrypt(encrypted)
        assert isinstance(result, bytes)


class TestEncryptMetadata:
    """Tests for encrypt_metadata function."""

    def test_encrypt_metadata_returns_string(self) -> None:
        """encrypt_metadata returns string."""
        result = encrypt_metadata("test metadata")
        assert isinstance(result, str)

    def test_encrypt_metadata_has_prefix(self) -> None:
        """encrypt_metadata result starts with ECdITeCs: prefix."""
        result = encrypt_metadata("test metadata")
        assert result.startswith("ECdITeCs:")

    def test_encrypt_metadata_is_deterministic(self) -> None:
        """encrypt_metadata returns same result for same input."""
        data = "test metadata"
        result1 = encrypt_metadata(data)
        result2 = encrypt_metadata(data)
        assert result1 == result2

    def test_encrypt_metadata_different_for_different_input(self) -> None:
        """encrypt_metadata returns different results for different input."""
        result1 = encrypt_metadata("data1")
        result2 = encrypt_metadata("data2")
        assert result1 != result2


class TestDecryptMetadata:
    """Tests for decrypt_metadata function."""

    def test_decrypt_metadata_raises_on_malformed_input(self) -> None:
        """decrypt_metadata raises Exception for malformed input."""
        with pytest.raises(Exception, match="malformed encrypted metadata"):
            decrypt_metadata("invalid metadata")

    def test_decrypt_metadata_raises_on_wrong_prefix(self) -> None:
        """decrypt_metadata raises Exception if prefix is not at position 0."""
        with pytest.raises(Exception, match="malformed encrypted metadata"):
            decrypt_metadata("wrongECdITeCs:data")

    def test_decrypt_metadata_raises_on_tampered_data(self) -> None:
        """decrypt_metadata raises exception on tampered data."""
        # Create valid encrypted metadata
        encrypted = encrypt_metadata("test metadata content")
        # Tamper with it (change a character in the middle to avoid base64 padding issues)
        mid = len(encrypted) // 2
        char = encrypted[mid]
        new_char = "A" if char != "A" else "B"
        tampered = encrypted[:mid] + new_char + encrypted[mid + 1 :]

        # Tampering causes either UnicodeDecodeError or XXTEAException
        with pytest.raises((XXTEAException, UnicodeDecodeError)):
            decrypt_metadata(tampered)

    def test_encrypt_decrypt_metadata_roundtrip(self) -> None:
        """encrypt_metadata/decrypt_metadata roundtrip preserves data."""
        original = "test metadata content"
        encrypted = encrypt_metadata(original)
        decrypted = decrypt_metadata(encrypted)
        assert decrypted == original

    def test_encrypt_decrypt_metadata_with_special_chars(self) -> None:
        """encrypt_metadata/decrypt_metadata works with special characters."""
        original = '{"key": "value", "number": 123}'
        encrypted = encrypt_metadata(original)
        decrypted = decrypt_metadata(encrypted)
        assert decrypted == original


class TestMetaAudibleApp:
    """Tests for meta_audible_app function."""

    def test_meta_audible_app_returns_string(self) -> None:
        """meta_audible_app returns string."""
        result = meta_audible_app("Test UserAgent", "https://test.url")
        assert isinstance(result, str)

    def test_meta_audible_app_returns_valid_json(self) -> None:
        """meta_audible_app returns valid JSON."""
        result = meta_audible_app("Test UserAgent", "https://test.url")
        # Should not raise
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_meta_audible_app_contains_required_fields(self) -> None:
        """meta_audible_app output contains required fields."""
        result = meta_audible_app("Test UserAgent", "https://test.url")
        data = json.loads(result)

        # Check for key fields
        assert "start" in data
        assert "version" in data
        assert "userAgent" in data
        assert "location" in data
        assert "interaction" in data
        assert "scripts" in data
        assert "capabilities" in data
        assert "performance" in data
        assert "form" in data

    def test_meta_audible_app_includes_user_agent(self) -> None:
        """meta_audible_app includes the provided user agent."""
        user_agent = "Custom UserAgent String"
        result = meta_audible_app(user_agent, "https://test.url")
        data = json.loads(result)
        assert data["userAgent"] == user_agent

    def test_meta_audible_app_includes_oauth_url(self) -> None:
        """meta_audible_app includes the provided OAuth URL."""
        oauth_url = "https://custom.oauth.url"
        result = meta_audible_app("UserAgent", oauth_url)
        data = json.loads(result)
        assert data["location"] == oauth_url

    def test_meta_audible_app_timestamps_are_reasonable(self) -> None:
        """meta_audible_app generates reasonable timestamps."""
        result = meta_audible_app("UserAgent", "https://test.url")
        data = json.loads(result)

        # start and end should be reasonable timestamps
        assert isinstance(data["start"], int)
        assert isinstance(data["end"], int)
        assert data["start"] > 1577836800000  # After 2020-01-01
        assert data["end"] > 1577836800000

    def test_meta_audible_app_has_correct_structure(self) -> None:
        """meta_audible_app generates correct data structure."""
        result = meta_audible_app("UserAgent", "https://test.url")
        data = json.loads(result)

        # Check nested structures
        assert isinstance(data["interaction"], dict)
        assert isinstance(data["scripts"], dict)
        assert isinstance(data["capabilities"], dict)
        assert isinstance(data["capabilities"]["js"], dict)
        assert isinstance(data["capabilities"]["css"], dict)
        assert isinstance(data["performance"], dict)
        assert isinstance(data["performance"]["timing"], dict)
        assert isinstance(data["form"], dict)
        assert "email" in data["form"]
        assert "password" in data["form"]
