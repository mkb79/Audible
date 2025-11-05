"""Cryptography provider using the cryptography library.

This module implements the crypto protocols using the cryptography library,
which provides modern, Rust-accelerated cryptographic operations.

The cryptography library is the recommended choice for new projects due to:
- Active maintenance and security updates
- Modern API design
- Rust-based performance optimizations
- Comprehensive cryptographic primitive support

This is the preferred provider when available, selected first during auto-detection.
"""

from __future__ import annotations

import logging
import warnings
from collections.abc import Callable
from typing import Any


# Optional import - only available if cryptography is installed
try:
    from cryptography.exceptions import InvalidKey, UnsupportedAlgorithm
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives import padding as sym_padding
    from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


logger = logging.getLogger("audible.crypto.cryptography")


def _load_rsa_private_key_cryptography(pem_data: str) -> Any:
    """Load an RSA private key from PEM using cryptography.

    Note:
        This function does NOT cache keys. Caching is the caller's
        responsibility (e.g., Authenticator._cached_rsa_key for performance).

    Args:
        pem_data: RSA private key in PEM format.

    Returns:
        Parsed RSA private key object.

    Raises:
        ValueError: If PEM data is invalid or not an RSA key.
    """
    try:
        key = serialization.load_pem_private_key(
            pem_data.encode("utf-8"), password=None, backend=default_backend()
        )
        if not isinstance(key, rsa.RSAPrivateKey):
            raise ValueError("Key is not an RSA private key")
        return key
    except (ValueError, TypeError, UnsupportedAlgorithm, InvalidKey) as exc:
        logger.error("Failed to load RSA private key: %s", exc)
        raise ValueError("Failed to load RSA private key") from exc


class CryptographyAESProvider:
    """AES provider using cryptography library.

    Implements AES-CBC encryption/decryption with PKCS7 padding support.
    Uses Rust-accelerated primitives from the cryptography library.
    """

    def encrypt(
        self, key: bytes, iv: bytes, data: str, padding: str = "default"
    ) -> bytes:
        """Encrypt data using AES-CBC.

        Args:
            key: AES key (16, 24, or 32 bytes for AES-128/192/256).
            iv: Initialization vector (16 bytes).
            data: Plaintext string to encrypt.
            padding: "default" for PKCS7 padding, "none" for no padding.

        Returns:
            Encrypted ciphertext as bytes.

        Raises:
            ValueError: If key/IV sizes are invalid or padding mode unknown.
        """
        if len(iv) != 16:
            raise ValueError(f"IV must be 16 bytes, got {len(iv)}")
        if len(key) not in (16, 24, 32):
            raise ValueError(f"Key must be 16, 24, or 32 bytes, got {len(key)}")

        plaintext = data.encode("utf-8")

        # Apply padding if requested
        if padding == "default":
            padder = sym_padding.PKCS7(128).padder()
            plaintext = padder.update(plaintext) + padder.finalize()
        elif padding != "none":
            raise ValueError(f"Unknown padding mode: {padding}")

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

        return ciphertext

    def decrypt(
        self, key: bytes, iv: bytes, encrypted_data: bytes, padding: str = "default"
    ) -> str:
        """Decrypt data using AES-CBC.

        Args:
            key: AES key (16, 24, or 32 bytes).
            iv: Initialization vector (16 bytes).
            encrypted_data: Ciphertext to decrypt.
            padding: "default" for PKCS7 padding, "none" for no padding.

        Returns:
            Decrypted plaintext as string.

        Raises:
            ValueError: If key/IV sizes invalid, padding incorrect, or decryption fails.
        """
        if len(iv) != 16:
            raise ValueError(f"IV must be 16 bytes, got {len(iv)}")
        if len(key) not in (16, 24, 32):
            raise ValueError(f"Key must be 16, 24, or 32 bytes, got {len(key)}")

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(encrypted_data) + decryptor.finalize()

        # Remove padding if requested
        if padding == "default":
            try:
                unpadder = sym_padding.PKCS7(128).unpadder()
                plaintext = unpadder.update(plaintext) + unpadder.finalize()
            except ValueError as e:
                msg = (
                    "Invalid PKCS7 padding - possible decryption key/IV mismatch or "
                    "corrupted ciphertext"
                )
                raise ValueError(msg) from e
        elif padding != "none":
            raise ValueError(f"Unknown padding mode: {padding}")

        # Decode decrypted bytes to string
        try:
            return plaintext.decode("utf-8")
        except UnicodeDecodeError as e:
            msg = (
                "Failed to decode decrypted data as UTF-8 - possible decryption "
                "key/IV mismatch or corrupted ciphertext"
            )
            raise ValueError(msg) from e


class CryptographyPBKDF2Provider:
    """PBKDF2 provider using cryptography library.

    Implements PBKDF2 key derivation with configurable hash algorithms.
    Uses Rust-accelerated KDF from the cryptography library.
    """

    def derive_key(
        self,
        password: str,
        salt: bytes,
        iterations: int,
        key_size: int,
        hashmod: Callable[[], Any],
    ) -> bytes:
        """Derive a key from password using PBKDF2.

        Args:
            password: Password string.
            salt: Random salt bytes.
            iterations: Number of PBKDF2 iterations (1-65535).
            key_size: Desired key length in bytes.
            hashmod: Hash function factory (e.g., hashlib.sha256).

        Returns:
            Derived key bytes.

        Raises:
            ValueError: If iterations out of range or parameters invalid.
        """
        if not (1 <= iterations <= 65535):
            raise ValueError(f"Iterations must be 1-65535, got {iterations}")

        # Map hashlib hash functions to cryptography hash algorithms
        hash_name = hashmod().name
        hash_algo_map = {
            "sha256": hashes.SHA256(),
            "sha1": hashes.SHA1(),  # noqa: S303 - legacy compatibility
            "sha224": hashes.SHA224(),
            "sha384": hashes.SHA384(),
            "sha512": hashes.SHA512(),
            "md5": hashes.MD5(),  # noqa: S303 - legacy compatibility
        }

        hash_algorithm = hash_algo_map.get(hash_name)
        if hash_algorithm is None:
            raise ValueError(f"Unsupported hash algorithm: {hash_name}")

        kdf = PBKDF2HMAC(
            algorithm=hash_algorithm,
            length=key_size,
            salt=salt,
            iterations=iterations,
            backend=default_backend(),
        )

        return kdf.derive(password.encode("utf-8"))


class CryptographyRSAProvider:
    """RSA provider using cryptography library.

    Implements RSA private key loading and PKCS#1 v1.5 signing with SHA-256.
    """

    def load_private_key(self, pem_data: str) -> Any:
        """Load an RSA private key from PEM format.

        Args:
            pem_data: RSA private key in PEM format.

        Returns:
            Parsed RSA private key object.
        """
        return _load_rsa_private_key_cryptography(pem_data)

    def sign(self, key: Any, data: bytes, algorithm: str = "SHA-256") -> bytes:
        """Sign data with RSA private key using PKCS#1 v1.5.

        Args:
            key: RSA private key from load_private_key().
            data: Data to sign.
            algorithm: Hash algorithm, only "SHA-256" supported (Audible API requirement).

        Returns:
            Signature bytes.

        Raises:
            ValueError: If algorithm is not "SHA-256" or key is invalid.
        """
        if algorithm != "SHA-256":
            raise ValueError(f"Only SHA-256 supported, got {algorithm}")

        if not isinstance(key, rsa.RSAPrivateKey):
            raise ValueError("Key must be an RSA private key")

        signature = key.sign(data, asym_padding.PKCS1v15(), hashes.SHA256())

        return signature


class CryptographyHashProvider:
    """Hash provider using cryptography library.

    Implements SHA-256 and SHA-1 hash functions.
    Uses Rust-accelerated hash primitives.
    """

    _sha1_warning_shown = False

    def sha256(self, data: bytes) -> bytes:
        """Compute SHA-256 hash.

        Args:
            data: Data to hash.

        Returns:
            SHA-256 digest bytes (32 bytes).
        """
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(data)
        return digest.finalize()

    def sha1(self, data: bytes) -> bytes:
        """Compute SHA-1 hash.

        Args:
            data: Data to hash.

        Returns:
            SHA-1 digest bytes (20 bytes).

        Note:
            SHA-1 is cryptographically broken. Only use for legacy compatibility.
        """
        if not self.__class__._sha1_warning_shown:
            warnings.warn(
                "SHA-1 is deprecated and should only be used for legacy compatibility",
                DeprecationWarning,
                stacklevel=2,
            )
            self.__class__._sha1_warning_shown = True

        digest = hashes.Hash(hashes.SHA1(), backend=default_backend())  # noqa: S303 - legacy compatibility
        digest.update(data)
        return digest.finalize()


class CryptographyProvider:
    """Unified cryptography crypto provider.

    This provider implements all cryptographic operations using the cryptography
    library, which provides modern, Rust-accelerated implementations.

    Performance characteristics:
    - Comparable or better than pycryptodome
    - Modern API and active maintenance
    - Preferred choice for new installations

    Raises:
        ImportError: If cryptography library is not installed.

    Example:
        >>> from audible.crypto import get_crypto_providers, CryptographyProvider  # doctest: +SKIP
        >>> providers = get_crypto_providers(CryptographyProvider)  # doctest: +SKIP
        >>> providers.provider_name  # doctest: +SKIP
        'cryptography'
    """

    def __init__(self) -> None:
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ImportError(  # doctest: +SKIP
                "cryptography is not installed. Install with: pip install "
                "audible[cryptography] (or audible[cryptography,pycryptodome] for full coverage)."  # doctest: +SKIP
            )

        self._aes = CryptographyAESProvider()
        self._pbkdf2 = CryptographyPBKDF2Provider()
        self._rsa = CryptographyRSAProvider()
        self._hash = CryptographyHashProvider()

    @property
    def aes(self) -> CryptographyAESProvider:
        """Get the AES provider."""
        return self._aes

    @property
    def pbkdf2(self) -> CryptographyPBKDF2Provider:
        """Get the PBKDF2 provider."""
        return self._pbkdf2

    @property
    def rsa(self) -> CryptographyRSAProvider:
        """Get the RSA provider."""
        return self._rsa

    @property
    def hash(self) -> CryptographyHashProvider:
        """Get the hash provider."""
        return self._hash

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "cryptography"


__all__ = [
    "CRYPTOGRAPHY_AVAILABLE",
    "CryptographyAESProvider",
    "CryptographyHashProvider",
    "CryptographyPBKDF2Provider",
    "CryptographyProvider",
    "CryptographyRSAProvider",
]
