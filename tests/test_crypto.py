"""Tests for the crypto module."""

from __future__ import annotations

import concurrent.futures
import hashlib
from typing import TYPE_CHECKING, Any

import pytest

from audible.crypto.legacy_provider import (
    LegacyAESProvider,
    LegacyHashProvider,
    LegacyPBKDF2Provider,
    LegacyRSAProvider,
)
from audible.crypto.registry import get_crypto_providers


if TYPE_CHECKING:
    from audible.crypto.pycryptodome_provider import (
        PycryptodomeAESProvider,
        PycryptodomeHashProvider,
        PycryptodomePBKDF2Provider,
        PycryptodomeRSAProvider,
    )

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


@pytest.mark.skipif(not PYCRYPTODOME_AVAILABLE, reason="pycryptodome not installed")
def test_pycryptodome_aes_decrypt_unicode_error() -> None:
    """Test that decryption errors produce descriptive ValueError.

    When decryption fails (wrong key, IV, or corrupted data), the provider
    should raise a descriptive ValueError to help with debugging.
    """
    provider: PycryptodomeAESProvider = PycryptodomeAESProvider()
    correct_key = b"sixteen byte key"
    wrong_key = b"wrong_key_16byte"
    iv = b"sixteen byte iv!"

    # Encrypt with correct key
    plaintext = "test data"
    encrypted = provider.encrypt(correct_key, iv, plaintext)

    # Attempting to decrypt with wrong key should raise ValueError
    with pytest.raises(ValueError):
        provider.decrypt(wrong_key, iv, encrypted)


def test_aes_decrypt_error_consistency() -> None:
    """Test that both providers raise consistent ValueError for decryption errors.

    Both legacy and pycryptodome providers should handle decryption errors
    identically, raising ValueError with descriptive messages.
    """
    legacy_provider = LegacyAESProvider()
    correct_key = b"sixteen byte key"
    wrong_key = b"wrong_key_16byte"
    iv = b"sixteen byte iv!"

    # Encrypt with correct key
    plaintext = "test data"
    legacy_encrypted = legacy_provider.encrypt(correct_key, iv, plaintext)

    # Legacy provider should raise ValueError when decrypting with wrong key
    with pytest.raises(ValueError):
        legacy_provider.decrypt(wrong_key, iv, legacy_encrypted)

    # If pycryptodome is available, verify it behaves identically
    if PYCRYPTODOME_AVAILABLE:
        pycryptodome_provider: PycryptodomeAESProvider = PycryptodomeAESProvider()
        pycryptodome_encrypted = pycryptodome_provider.encrypt(
            correct_key, iv, plaintext
        )

        # Both providers should raise ValueError
        with pytest.raises(ValueError):
            pycryptodome_provider.decrypt(wrong_key, iv, pycryptodome_encrypted)


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


def test_legacy_rsa_load_key(rsa_private_key: str) -> None:
    """Test legacy RSA key loading."""
    provider = LegacyRSAProvider()

    key = provider.load_private_key(rsa_private_key)

    assert key is not None


def test_legacy_rsa_key_caching(rsa_private_key: str) -> None:
    """Test that RSA keys are cached properly."""
    provider = LegacyRSAProvider()

    key1 = provider.load_private_key(rsa_private_key)
    key2 = provider.load_private_key(rsa_private_key)

    # Should return the same cached object
    assert key1 is key2


@pytest.mark.skipif(not PYCRYPTODOME_AVAILABLE, reason="pycryptodome not installed")
def test_pycryptodome_rsa_load_key(rsa_private_key: str) -> None:
    """Test pycryptodome RSA key loading."""
    provider: PycryptodomeRSAProvider = PycryptodomeRSAProvider()

    key = provider.load_private_key(rsa_private_key)

    assert key is not None


@pytest.mark.skipif(not PYCRYPTODOME_AVAILABLE, reason="pycryptodome not installed")
def test_pycryptodome_rsa_unsupported_algorithm(rsa_private_key: str) -> None:
    """Test error handling for unsupported RSA algorithms."""
    provider: PycryptodomeRSAProvider = PycryptodomeRSAProvider()
    key = provider.load_private_key(rsa_private_key)

    with pytest.raises(ValueError, match="Unsupported algorithm"):
        provider.sign(key, b"data", "unsupported_algo")


@pytest.mark.skipif(not PYCRYPTODOME_AVAILABLE, reason="pycryptodome not installed")
def test_pycryptodome_rsa_sign_invalid_key_type() -> None:
    """Test that signing with invalid key type raises TypeError.

    The provider should validate the key type and raise a descriptive
    TypeError instead of allowing pycryptodome to raise cryptic errors.
    """
    provider: PycryptodomeRSAProvider = PycryptodomeRSAProvider()
    data = b"test data to sign"

    # Test with various invalid key types
    invalid_keys: list[Any] = [
        None,
        "not_a_key",
        123,
        b"bytes_key",
        {},
        [],
    ]

    for invalid_key in invalid_keys:
        with pytest.raises(TypeError, match=r"Expected RSA\.RsaKey"):
            provider.sign(invalid_key, data)


# =============================================================================
# Registry Tests
# =============================================================================


def test_registry_singleton() -> None:
    """Test that get_crypto_providers() returns the same auto-detected instance."""
    provider1 = get_crypto_providers()
    provider2 = get_crypto_providers()
    provider3 = get_crypto_providers(None)

    assert provider1 is provider2
    assert provider2 is provider3


def test_registry_provider_name() -> None:
    """Test that provider name is correctly set."""
    registry = get_crypto_providers()

    provider_name = registry.provider_name

    assert provider_name in ("legacy", "pycryptodome", "cryptography")


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


def test_registry_provider_selection(rsa_private_key: str) -> None:
    """Test that registry selects appropriate provider based on availability."""
    registry = get_crypto_providers()

    # Verify provider is selected (either pycryptodome or legacy)
    provider_name = registry.provider_name
    assert provider_name in ("legacy", "pycryptodome", "cryptography")

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
    key_obj = registry.rsa.load_private_key(rsa_private_key)
    signature = registry.rsa.sign(key_obj, b"test data")
    assert len(signature) > 0


def test_singleton_thread_safety() -> None:
    """Test that singleton pattern is thread-safe.

    Creates 100 registry instances concurrently from 20 threads
    to verify that all threads receive the same singleton instance.
    """
    instances = []
    instance_ids = []

    def create_registry() -> None:
        """Create a registry instance and record it."""
        provider = get_crypto_providers()
        instances.append(provider)
        instance_ids.append(id(provider))

    # Create 100 registries concurrently from 20 threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(create_registry) for _ in range(100)]
        concurrent.futures.wait(futures)

    # Verify all instances are the same object
    unique_ids = set(instance_ids)
    assert len(unique_ids) == 1, (
        f"Multiple singleton instances created! Found {len(unique_ids)} unique instances. "
        f"All threads should receive the same singleton instance."
    )
    assert all(inst is instances[0] for inst in instances), (
        "Not all registry instances are identical objects"
    )
