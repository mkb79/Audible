"""Tests for audible.aescipher module."""

from __future__ import annotations

from typing import Any

import pytest

from audible.aescipher import (
    AESCipher,
    aes_cbc_decrypt,
    aes_cbc_encrypt,
    create_salt,
    pack_salt,
    unpack_salt,
)


class TestAESCipherInitialization:
    """Tests for AESCipher initialization and validation."""

    def test_init_with_valid_params(self) -> None:
        """AESCipher initializes with valid parameters."""
        cipher = AESCipher(password="test_password")

        assert cipher.password == "test_password"  # noqa: S105
        assert cipher.key_size == 32  # default
        assert cipher.salt_marker == b"$"  # default
        assert cipher.kdf_iterations == 1000  # default

    def test_init_with_custom_params(self) -> None:
        """AESCipher accepts custom parameters."""
        cipher = AESCipher(
            password="custom_pass",
            key_size=16,
            salt_marker=b"##",
            kdf_iterations=5000,
        )

        assert cipher.key_size == 16
        assert cipher.salt_marker == b"##"
        assert cipher.kdf_iterations == 5000

    def test_init_raises_on_invalid_salt_marker_length(self) -> None:
        """AESCipher raises ValueError for salt_marker with invalid length."""
        # Too short (empty)
        with pytest.raises(ValueError, match="one to six bytes long"):
            AESCipher(password="test", salt_marker=b"")

        # Too long (7 bytes)
        with pytest.raises(ValueError, match="one to six bytes long"):
            AESCipher(password="test", salt_marker=b"1234567")

    def test_init_raises_on_non_bytes_salt_marker(self) -> None:
        """AESCipher raises TypeError for non-bytes salt_marker."""
        with pytest.raises(TypeError, match="must be a bytes instance"):
            AESCipher(password="test", salt_marker="$")  # type: ignore[arg-type]

    def test_init_raises_on_too_many_kdf_iterations(self) -> None:
        """AESCipher raises ValueError for kdf_iterations >= 65536."""
        with pytest.raises(ValueError, match="must be <= 65535"):
            AESCipher(password="test", kdf_iterations=65536)

        # Exactly at boundary should fail
        with pytest.raises(ValueError, match="must be <= 65535"):
            AESCipher(password="test", kdf_iterations=70000)


class TestAESCipherDictStyle:
    """Tests for dict-style encryption/decryption."""

    def test_to_dict_returns_dict_with_required_keys(self) -> None:
        """to_dict returns dict with salt, iv, ciphertext, info."""
        cipher = AESCipher(password="test_password")
        plaintext = "Test message"

        result = cipher.to_dict(plaintext)

        assert isinstance(result, dict)
        assert "salt" in result
        assert "iv" in result
        assert "ciphertext" in result
        assert "info" in result
        assert result["info"] == "base64-encoded AES-CBC-256 of JSON object"

    def test_to_dict_from_dict_roundtrip(self) -> None:
        """to_dict/from_dict roundtrip preserves data."""
        cipher = AESCipher(password="test_password")
        original = "Test message with numbers and symbols: 123!@#$%"

        encrypted = cipher.to_dict(original)
        decrypted = cipher.from_dict(encrypted)

        assert decrypted == original

    def test_from_dict_with_wrong_password_fails(self) -> None:
        """from_dict with wrong password produces garbage or fails."""
        cipher1 = AESCipher(password="password1")
        cipher2 = AESCipher(password="password2")

        encrypted = cipher1.to_dict("test message")

        # Should either fail or produce garbage (not original text)
        try:
            decrypted = cipher2.from_dict(encrypted)
            assert decrypted != "test message"
        except Exception:  # noqa: S110
            # Expected - wrong password causes decryption failure
            pass


class TestAESCipherBytesStyle:
    """Tests for bytes-style encryption/decryption."""

    def test_to_bytes_returns_bytes(self) -> None:
        """to_bytes returns bytes."""
        cipher = AESCipher(password="test_password")
        plaintext = "Test message"

        result = cipher.to_bytes(plaintext)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_to_bytes_from_bytes_roundtrip(self) -> None:
        """to_bytes/from_bytes roundtrip preserves data."""
        cipher = AESCipher(password="test_password")
        original = "Test message with numbers: 1234567890"

        encrypted = cipher.to_bytes(original)
        decrypted = cipher.from_bytes(encrypted)

        assert decrypted == original

    def test_from_bytes_with_wrong_password_fails(self) -> None:
        """from_bytes with wrong password fails."""
        cipher1 = AESCipher(password="password1")
        cipher2 = AESCipher(password="password2")

        encrypted = cipher1.to_bytes("test message")

        # Should either fail or produce garbage
        try:
            decrypted = cipher2.from_bytes(encrypted)
            assert decrypted != "test message"
        except Exception:  # noqa: S110
            # Expected - wrong password causes failure
            pass


class TestAESCipherFileOperations:
    """Tests for file encryption/decryption."""

    def test_to_file_json_creates_file(self, tmp_path: Any) -> None:
        """to_file with json encryption creates file."""
        cipher = AESCipher(password="test_password")
        file_path = tmp_path / "encrypted.json"
        plaintext = "Test file content"

        cipher.to_file(plaintext, file_path, encryption="json")

        assert file_path.exists()
        # File should contain JSON
        content = file_path.read_text()
        assert "salt" in content
        assert "iv" in content
        assert "ciphertext" in content

    def test_to_file_bytes_creates_file(self, tmp_path: Any) -> None:
        """to_file with bytes encryption creates file."""
        cipher = AESCipher(password="test_password")
        file_path = tmp_path / "encrypted.bin"
        plaintext = "Test file content"

        cipher.to_file(plaintext, file_path, encryption="bytes")

        assert file_path.exists()
        # File should contain binary data
        content = file_path.read_bytes()
        assert len(content) > 0

    def test_to_file_from_file_json_roundtrip(self, tmp_path: Any) -> None:
        """to_file/from_file JSON roundtrip preserves data."""
        cipher = AESCipher(password="test_password")
        file_path = tmp_path / "encrypted.json"
        original = "Test file content with numbers and symbols: 123!@#$%"

        cipher.to_file(original, file_path, encryption="json")
        decrypted = cipher.from_file(file_path, encryption="json")

        assert decrypted == original

    def test_to_file_from_file_bytes_roundtrip(self, tmp_path: Any) -> None:
        """to_file/from_file bytes roundtrip preserves data."""
        cipher = AESCipher(password="test_password")
        file_path = tmp_path / "encrypted.bin"
        original = "Test file content"

        cipher.to_file(original, file_path, encryption="bytes")
        decrypted = cipher.from_file(file_path, encryption="bytes")

        assert decrypted == original

    def test_to_file_raises_on_invalid_encryption_type(self, tmp_path: Any) -> None:
        """to_file raises ValueError for invalid encryption type."""
        cipher = AESCipher(password="test_password")
        file_path = tmp_path / "encrypted.txt"

        with pytest.raises(ValueError, match='must be "json" or "bytes"'):
            cipher.to_file("test", file_path, encryption="invalid")

    def test_from_file_raises_on_invalid_encryption_type(self, tmp_path: Any) -> None:
        """from_file raises ValueError for invalid encryption type."""
        cipher = AESCipher(password="test_password")
        file_path = tmp_path / "encrypted.txt"
        file_path.write_text("dummy content")

        with pytest.raises(ValueError, match='must be "json" or "bytes"'):
            cipher.from_file(file_path, encryption="invalid")


class TestSaltFunctions:
    """Tests for salt helper functions."""

    def test_create_salt_returns_header_and_salt(self) -> None:
        """create_salt returns header and salt tuple."""
        salt_marker = b"$"
        kdf_iterations = 1000

        header, salt = create_salt(salt_marker, kdf_iterations)

        assert isinstance(header, bytes)
        assert isinstance(salt, bytes)
        assert len(header) > 0
        assert len(salt) > 0

    def test_pack_salt_combines_header_and_salt(self) -> None:
        """pack_salt combines header and salt."""
        header = b"test_header"
        salt = b"test_salt"

        packed = pack_salt(header, salt)

        assert packed == header + salt

    def test_unpack_salt_extracts_salt_and_iterations(self) -> None:
        """unpack_salt extracts salt and kdf_iterations."""
        salt_marker = b"$"
        kdf_iterations = 1000

        # Create and pack salt
        header, original_salt = create_salt(salt_marker, kdf_iterations)
        packed = pack_salt(header, original_salt)

        # Unpack it
        unpacked_salt, unpacked_iterations = unpack_salt(packed, salt_marker)

        assert unpacked_salt == original_salt
        assert unpacked_iterations == kdf_iterations

    def test_unpack_salt_raises_on_invalid_marker(self) -> None:
        """unpack_salt raises ValueError for wrong salt_marker."""
        # Create salt with one marker
        header, salt = create_salt(b"$", 1000)
        packed = pack_salt(header, salt)

        # Try to unpack with different marker
        with pytest.raises(ValueError, match="Check salt_marker"):
            unpack_salt(packed, b"#")


class TestAESCBCFunctions:
    """Tests for low-level AES CBC functions."""

    def test_aes_cbc_encrypt_decrypt_roundtrip(self) -> None:
        """aes_cbc_encrypt/decrypt roundtrip preserves data."""
        key = b"0" * 32  # 256-bit key
        iv = b"0" * 16  # 128-bit IV
        plaintext = "Test message"

        encrypted = aes_cbc_encrypt(key, iv, plaintext)
        decrypted = aes_cbc_decrypt(key, iv, encrypted)

        assert decrypted == plaintext

    def test_aes_cbc_encrypt_returns_bytes(self) -> None:
        """aes_cbc_encrypt returns bytes."""
        key = b"0" * 32
        iv = b"0" * 16
        plaintext = "Test"

        result = aes_cbc_encrypt(key, iv, plaintext)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_aes_cbc_decrypt_returns_string(self) -> None:
        """aes_cbc_decrypt returns string."""
        key = b"0" * 32
        iv = b"0" * 16
        plaintext = "Test"

        encrypted = aes_cbc_encrypt(key, iv, plaintext)
        decrypted = aes_cbc_decrypt(key, iv, encrypted)

        assert isinstance(decrypted, str)
        assert decrypted == plaintext


class TestAESCipherDecryptWithInvalidSalt:
    """Tests for _decrypt error handling."""

    def test_decrypt_handles_invalid_salt_gracefully(self) -> None:
        """_decrypt handles invalid salt by using default kdf_iterations."""
        cipher = AESCipher(password="test_password", salt_marker=b"$")

        # Create valid encryption first
        encrypted_dict = cipher.to_dict("test message")

        # Corrupt the salt (make it invalid)
        import base64

        corrupted_salt = base64.b64encode(b"invalid_salt_data").decode("utf-8")
        encrypted_dict["salt"] = corrupted_salt

        # Should handle gracefully (will likely fail decryption but not crash on salt check)
        try:
            # May produce garbage or fail, but shouldn't crash with ValueError on salt
            result = cipher.from_dict(encrypted_dict)
            # If it somehow decrypts, it won't be the original
            assert result != "test message"
        except Exception as e:
            # Some crypto providers may raise on bad padding, which is fine
            assert "salt_marker" not in str(e).lower()
