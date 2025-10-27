"""Tests for the crypto module."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from audible.crypto.legacy_provider import (
    LegacyAESProvider,
    LegacyHashProvider,
    LegacyPBKDF2Provider,
    LegacyRSAProvider,
)
from audible.crypto.registry import CryptoProviderRegistry, get_crypto_providers


if TYPE_CHECKING:
    from audible.crypto.pycryptodome_provider import (
        PycryptodomeAESProvider,
        PycryptodomeHashProvider,
        PycryptodomePBKDF2Provider,
        PycryptodomeRSAProvider,
    )

# Valid RSA private key in PKCS#1 format (1024-bit for testing)
TEST_RSA_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQCckEdw6Hd8Pwm1YRtinw2UQkTmRM5QQcfsUxi86w6mxXRomETI
FPZaFS6q9D1x1Zgzhk+tXS6MBl8tJrDjaAUROeoajdNylvunvdyLNQhoaGOcbRSr
0DFV/an6oKv6IsLQzI7UP91ZSbg4fDb5/LqqD4devp5QpShJMEtw2OUUzwIDAQAB
AoGAdqJtQAUm5SLvPF2E3sofBATjKIlivDXcRBsDV8PVqlFc0BTxqZsYwVHjtu6z
0JpFZmWT4o4FQ11gqVn0F50umJuPoS/slfBGiV3TE2b3o+uLy6EcVDoOtH7cUO6l
gTvejvv6rCpuvHHLkDf8mUEtN+WJDGwYamyHfCIChSAIrMECQQDMIdhGmNg7ckpb
KnrJ2rAj38QrUO0t1m/t+i/76vyvPN65o6lnvI/SHNXUf/asQbmHeUT3b75ApqoV
BLSGWG15AkEAxFg++zayNfGHl99xYpB0g4gom/UqGC87hiVJYXpoXCld4kmguW4j
ov3rRDKQGZwh/DQyX0BvxDHmfGzTXNmqhwJAS+m6OGbW4ySZqlWd3DtLjcvFdCZg
Tc+VSHbmKVU2KyUD3x2R/lYNViILEz+TSHQYvtzGXQ5dPkW8spxRVjTEYQJAGowH
7/VkQRDoEWu/q+D2L/aP7w5F48E3HhsagdiIFbXuILNtzMSMgvQsBCuF+kB3A9+W
0/QlaHSKwlYAefRgLwJBAMQc+jY9eymjJ08KVZrVC8NhYEliWTPkpfjeh4CTTfNY
Ho8KYXsQV2M4btI7FJO1CMb2SV5sP09IRvBdX1hEqzY=
-----END RSA PRIVATE KEY-----"""

# Try to import pycryptodome providers
try:
    from audible.crypto.pycryptodome_provider import (
        PycryptodomeAESProvider,
        PycryptodomeHashProvider,
        PycryptodomePBKDF2Provider,
        PycryptodomeRSAProvider,
    )

    PYCRYPTODOME_AVAILABLE = True
except ImportError:
    PYCRYPTODOME_AVAILABLE = False


# =============================================================================
# AES Tests
# =============================================================================


def test_legacy_aes_encrypt_decrypt() -> None:
    """Test legacy AES provider encrypt/decrypt round-trip."""
    provider = LegacyAESProvider()
    key = b"sixteen byte key"
    iv = b"sixteen byte iv!"
    plaintext = "test data to encrypt"

    ciphertext = provider.encrypt(key, iv, plaintext)
    decrypted = provider.decrypt(key, iv, ciphertext)

    assert decrypted == plaintext
    assert ciphertext != plaintext.encode()


def test_legacy_aes_no_padding() -> None:
    """Test legacy AES with exact block size (no padding needed)."""
    provider = LegacyAESProvider()
    key = b"sixteen byte key"
    iv = b"sixteen byte iv!"
    plaintext = "exactly16bytes!!"  # 16 bytes = 1 AES block

    ciphertext = provider.encrypt(key, iv, plaintext, padding="none")
    decrypted = provider.decrypt(key, iv, ciphertext, padding="none")

    assert decrypted == plaintext


@pytest.mark.skipif(not PYCRYPTODOME_AVAILABLE, reason="pycryptodome not installed")
def test_pycryptodome_aes_encrypt_decrypt() -> None:
    """Test pycryptodome AES provider encrypt/decrypt round-trip."""
    provider: PycryptodomeAESProvider = PycryptodomeAESProvider()
    key = b"sixteen byte key"
    iv = b"sixteen byte iv!"
    plaintext = "test data to encrypt"

    ciphertext = provider.encrypt(key, iv, plaintext)
    decrypted = provider.decrypt(key, iv, ciphertext)

    assert decrypted == plaintext
    assert ciphertext != plaintext.encode()


@pytest.mark.skipif(not PYCRYPTODOME_AVAILABLE, reason="pycryptodome not installed")
def test_aes_cross_provider_compatibility() -> None:
    """Test that both AES providers produce identical ciphertext."""
    legacy_provider = LegacyAESProvider()
    pycryptodome_provider: PycryptodomeAESProvider = PycryptodomeAESProvider()

    key = b"sixteen byte key"
    iv = b"sixteen byte iv!"
    plaintext = "test data to encrypt"

    # Both providers should produce identical ciphertext
    legacy_ciphertext = legacy_provider.encrypt(key, iv, plaintext)
    pycryptodome_ciphertext = pycryptodome_provider.encrypt(key, iv, plaintext)

    assert legacy_ciphertext == pycryptodome_ciphertext

    # Each provider should be able to decrypt the other's output
    assert legacy_provider.decrypt(key, iv, pycryptodome_ciphertext) == plaintext
    assert pycryptodome_provider.decrypt(key, iv, legacy_ciphertext) == plaintext


# =============================================================================
# PBKDF2 Tests
# =============================================================================


def test_legacy_pbkdf2_derive_key() -> None:
    """Test legacy PBKDF2 key derivation."""
    provider = LegacyPBKDF2Provider()
    password = "test_password"  # noqa: S105
    salt = b"test_salt_16byte"
    iterations = 1000
    key_size = 32

    key = provider.derive_key(password, salt, iterations, key_size, hashlib.sha256)

    assert len(key) == key_size
    assert isinstance(key, bytes)


def test_legacy_pbkdf2_deterministic() -> None:
    """Test that PBKDF2 produces deterministic output."""
    provider = LegacyPBKDF2Provider()
    password = "test_password"  # noqa: S105
    salt = b"test_salt_16byte"
    iterations = 1000
    key_size = 32

    key1 = provider.derive_key(password, salt, iterations, key_size, hashlib.sha256)
    key2 = provider.derive_key(password, salt, iterations, key_size, hashlib.sha256)

    assert key1 == key2


@pytest.mark.skipif(not PYCRYPTODOME_AVAILABLE, reason="pycryptodome not installed")
def test_pycryptodome_pbkdf2_derive_key() -> None:
    """Test pycryptodome PBKDF2 key derivation."""
    provider: PycryptodomePBKDF2Provider = PycryptodomePBKDF2Provider()
    password = "test_password"  # noqa: S105
    salt = b"test_salt_16byte"
    iterations = 1000
    key_size = 32

    key = provider.derive_key(password, salt, iterations, key_size, hashlib.sha256)

    assert len(key) == key_size
    assert isinstance(key, bytes)


@pytest.mark.skipif(not PYCRYPTODOME_AVAILABLE, reason="pycryptodome not installed")
def test_pbkdf2_cross_provider_compatibility() -> None:
    """Test that both PBKDF2 providers produce identical keys."""
    legacy_provider = LegacyPBKDF2Provider()
    pycryptodome_provider: PycryptodomePBKDF2Provider = PycryptodomePBKDF2Provider()

    password = "test_password"  # noqa: S105
    salt = b"test_salt_16byte"
    iterations = 1000
    key_size = 32

    legacy_key = legacy_provider.derive_key(
        password, salt, iterations, key_size, hashlib.sha256
    )
    pycryptodome_key = pycryptodome_provider.derive_key(
        password, salt, iterations, key_size, hashlib.sha256
    )

    assert legacy_key == pycryptodome_key


@pytest.mark.skipif(not PYCRYPTODOME_AVAILABLE, reason="pycryptodome not installed")
def test_pycryptodome_pbkdf2_invalid_hashmod() -> None:
    """Test error handling for invalid hashmod parameter."""
    provider: PycryptodomePBKDF2Provider = PycryptodomePBKDF2Provider()

    # Test with unsupported hash algorithm
    class UnsupportedHash:
        """Mock hash object with unsupported name."""

        name = "unsupported_algo"

    with pytest.raises(ValueError, match="Unsupported hash algorithm"):
        provider.derive_key("password", b"salt", 1000, 32, lambda: UnsupportedHash())


# =============================================================================
# Hash Tests
# =============================================================================


def test_legacy_hash_sha256() -> None:
    """Test legacy SHA-256 hashing."""
    provider = LegacyHashProvider()
    data = b"test data"

    digest = provider.sha256(data)

    assert len(digest) == 32  # SHA-256 produces 32 bytes
    assert digest == hashlib.sha256(data).digest()


def test_legacy_hash_sha1() -> None:
    """Test legacy SHA-1 hashing."""
    provider = LegacyHashProvider()
    data = b"test data"

    digest = provider.sha1(data)

    assert len(digest) == 20  # SHA-1 produces 20 bytes
    assert digest == hashlib.sha1(data, usedforsecurity=False).digest()


@pytest.mark.skipif(not PYCRYPTODOME_AVAILABLE, reason="pycryptodome not installed")
def test_pycryptodome_hash_sha256() -> None:
    """Test pycryptodome SHA-256 hashing."""
    provider: PycryptodomeHashProvider = PycryptodomeHashProvider()
    data = b"test data"

    digest = provider.sha256(data)

    assert len(digest) == 32
    assert digest == hashlib.sha256(data).digest()


@pytest.mark.skipif(not PYCRYPTODOME_AVAILABLE, reason="pycryptodome not installed")
def test_hash_cross_provider_compatibility() -> None:
    """Test that both hash providers produce identical digests."""
    legacy_provider = LegacyHashProvider()
    pycryptodome_provider: PycryptodomeHashProvider = PycryptodomeHashProvider()

    data = b"test data"

    assert legacy_provider.sha256(data) == pycryptodome_provider.sha256(data)
    assert legacy_provider.sha1(data) == pycryptodome_provider.sha1(data)


# =============================================================================
# RSA Tests
# =============================================================================


def test_legacy_rsa_load_key() -> None:
    """Test legacy RSA key loading."""
    provider = LegacyRSAProvider()

    key = provider.load_private_key(TEST_RSA_KEY)

    assert key is not None


def test_legacy_rsa_key_caching() -> None:
    """Test that RSA keys are cached properly."""
    provider = LegacyRSAProvider()

    key1 = provider.load_private_key(TEST_RSA_KEY)
    key2 = provider.load_private_key(TEST_RSA_KEY)

    # Should return the same cached object
    assert key1 is key2


@pytest.mark.skipif(not PYCRYPTODOME_AVAILABLE, reason="pycryptodome not installed")
def test_pycryptodome_rsa_load_key() -> None:
    """Test pycryptodome RSA key loading."""
    provider: PycryptodomeRSAProvider = PycryptodomeRSAProvider()

    key = provider.load_private_key(TEST_RSA_KEY)

    assert key is not None


@pytest.mark.skipif(not PYCRYPTODOME_AVAILABLE, reason="pycryptodome not installed")
def test_pycryptodome_rsa_unsupported_algorithm() -> None:
    """Test error handling for unsupported RSA algorithms."""
    provider: PycryptodomeRSAProvider = PycryptodomeRSAProvider()
    key = provider.load_private_key(TEST_RSA_KEY)

    with pytest.raises(ValueError, match="Unsupported algorithm"):
        provider.sign(key, b"data", "unsupported_algo")


# =============================================================================
# Registry Tests
# =============================================================================


def test_registry_singleton() -> None:
    """Test that registry is a singleton."""
    registry1 = CryptoProviderRegistry()
    registry2 = CryptoProviderRegistry()
    registry3 = get_crypto_providers()

    assert registry1 is registry2
    assert registry2 is registry3


def test_registry_provider_name() -> None:
    """Test that provider name is correctly set."""
    registry = get_crypto_providers()

    provider_name = registry.provider_name

    assert provider_name in ("legacy", "pycryptodome")


def test_registry_provides_all_protocols() -> None:
    """Test that registry provides all required protocols."""
    registry = get_crypto_providers()

    # All properties should be accessible
    assert registry.aes is not None
    assert registry.pbkdf2 is not None
    assert registry.rsa is not None
    assert registry.hash is not None


def test_registry_aes_operations() -> None:
    """Test AES operations through registry."""
    registry = get_crypto_providers()

    key = b"sixteen byte key"
    iv = b"sixteen byte iv!"
    plaintext = "test data"

    ciphertext = registry.aes.encrypt(key, iv, plaintext)
    decrypted = registry.aes.decrypt(key, iv, ciphertext)

    assert decrypted == plaintext


def test_registry_hash_operations() -> None:
    """Test hash operations through registry."""
    registry = get_crypto_providers()

    data = b"test data"

    sha256_digest = registry.hash.sha256(data)
    sha1_digest = registry.hash.sha1(data)

    assert len(sha256_digest) == 32
    assert len(sha1_digest) == 20


def test_registry_provider_selection() -> None:
    """Test that registry selects appropriate provider based on availability."""
    registry = get_crypto_providers()

    # Verify provider is selected (either pycryptodome or legacy)
    provider_name = registry.provider_name
    assert provider_name in ("legacy", "pycryptodome")

    # Verify all required providers are initialized correctly
    assert registry.aes is not None
    assert registry.pbkdf2 is not None
    assert registry.rsa is not None
    assert registry.hash is not None

    # Test that operations work regardless of which provider is selected
    # This ensures fallback to legacy works if pycryptodome is unavailable

    # Test AES
    key = b"sixteen byte key"
    iv = b"sixteen byte iv!"
    plaintext = "test data"
    ciphertext = registry.aes.encrypt(key, iv, plaintext)
    assert registry.aes.decrypt(key, iv, ciphertext) == plaintext

    # Test PBKDF2
    derived_key = registry.pbkdf2.derive_key(
        "password",
        b"salt",
        1000,
        32,
        hashlib.sha256,
    )
    assert len(derived_key) == 32

    # Test Hash
    assert len(registry.hash.sha256(b"test")) == 32
    assert len(registry.hash.sha1(b"test")) == 20

    # Test RSA
    rsa_key = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQCckEdw6Hd8Pwm1YRtinw2UQkTmRM5QQcfsUxi86w6mxXRomETI
FPZaFS6q9D1x1Zgzhk+tXS6MBl8tJrDjaAUROeoajdNylvunvdyLNQhoaGOcbRSr
0DFV/an6oKv6IsLQzI7UP91ZSbg4fDb5/LqqD4devp5QpShJMEtw2OUUzwIDAQAB
AoGAdqJtQAUm5SLvPF2E3sofBATjKIlivDXcRBsDV8PVqlFc0BTxqZsYwVHjtu6z
0JpFZmWT4o4FQ11gqVn0F50umJuPoS/slfBGiV3TE2b3o+uLy6EcVDoOtH7cUO6l
gTvejvv6rCpuvHHLkDf8mUEtN+WJDGwYamyHfCIChSAIrMECQQDMIdhGmNg7ckpb
KnrJ2rAj38QrUO0t1m/t+i/76vyvPN65o6lnvI/SHNXUf/asQbmHeUT3b75ApqoV
BLSGWG15AkEAxFg++zayNfGHl99xYpB0g4gom/UqGC87hiVJYXpoXCld4kmguW4j
ov3rRDKQGZwh/DQyX0BvxDHmfGzTXNmqhwJAS+m6OGbW4ySZqlWd3DtLjcvFdCZg
Tc+VSHbmKVU2KyUD3x2R/lYNViILEz+TSHQYvtzGXQ5dPkW8spxRVjTEYQJAGowH
7/VkQRDoEWu/q+D2L/aP7w5F48E3HhsagdiIFbXuILNtzMSMgvQsBCuF+kB3A9+W
0/QlaHSKwlYAefRgLwJBAMQc+jY9eymjJ08KVZrVC8NhYEliWTPkpfjeh4CTTfNY
Ho8KYXsQV2M4btI7FJO1CMb2SV5sP09IRvBdX1hEqzY=
-----END RSA PRIVATE KEY-----"""
    key_obj = registry.rsa.load_private_key(rsa_key)
    signature = registry.rsa.sign(key_obj, b"test data")
    assert len(signature) > 0
