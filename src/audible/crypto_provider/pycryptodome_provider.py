"""Pycryptodome crypto provider using native C extensions.

This module implements the crypto protocols using the pycryptodome library,
which provides high-performance cryptographic operations via C extensions.

This is significantly faster than the pure Python implementations but requires
pycryptodome to be installed as an optional dependency.
"""

from __future__ import annotations

import logging
import warnings
from collections.abc import Callable
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from .protocols import HashAlgorithm


# Optional import - only available if pycryptodome is installed
try:
    from Crypto.Cipher import AES
    from Crypto.Hash import (
        MD5,
        SHA1,
        SHA224,
        SHA256,
        SHA384,
        SHA512,
    )
    from Crypto.Protocol.KDF import PBKDF2
    from Crypto.PublicKey import RSA
    from Crypto.Signature import pkcs1_15
    from Crypto.Util.Padding import pad, unpad

    PYCRYPTODOME_AVAILABLE = True
except ImportError:
    PYCRYPTODOME_AVAILABLE = False


logger = logging.getLogger("audible.crypto_provider.pycryptodome")


def _load_rsa_private_key_pycryptodome(pem_data: str) -> Any:
    """Load an RSA private key from PEM using pycryptodome.

    Note:
        This function does NOT cache keys. Caching is the caller's
        responsibility (e.g., Authenticator._cached_rsa_key for performance).

    Args:
        pem_data: RSA private key in PEM format.

    Returns:
        A parsed RSA.RsaKey object.
    """
    logger.debug("Loading RSA private key (pycryptodome provider)")
    return RSA.import_key(pem_data.encode("utf-8"))


class PycryptodomeAESProvider:
    """High-performance AES-CBC provider using pycryptodome.

    This implementation uses native C extensions from pycryptodome for
    significantly faster AES encryption/decryption compared to pure Python.
    """

    def encrypt(
        self, key: bytes, iv: bytes, data: str, padding: str = "default"
    ) -> bytes:
        """Encrypt data using AES-CBC with pycryptodome.

        Args:
            key: The AES encryption key.
            iv: The initialization vector.
            data: The plaintext data to encrypt.
            padding: Padding mode ("default" for PKCS7, "none" for no padding).

        Returns:
            The encrypted ciphertext.

        Raises:
            ValueError: If key/IV sizes are invalid or padding mode unknown.
        """
        if len(iv) != AES.block_size:
            raise ValueError(f"IV must be {AES.block_size} bytes, got {len(iv)}")
        if len(key) not in (16, 24, 32):
            raise ValueError(f"Key must be 16, 24, or 32 bytes, got {len(key)}")

        cipher = AES.new(key, AES.MODE_CBC, iv)
        data_bytes = data.encode("utf-8")

        if padding == "default":
            # Apply PKCS7 padding using pycryptodome's built-in function
            data_bytes = pad(data_bytes, AES.block_size, style="pkcs7")
        elif padding != "none":
            raise ValueError(f"Unknown padding mode: {padding}")

        return cipher.encrypt(data_bytes)

    def decrypt(
        self, key: bytes, iv: bytes, encrypted_data: bytes, padding: str = "default"
    ) -> str:
        """Decrypt data using AES-CBC with pycryptodome.

        Args:
            key: The AES decryption key.
            iv: The initialization vector.
            encrypted_data: The ciphertext to decrypt.
            padding: Padding mode ("default" for PKCS7, "none" for no padding).

        Returns:
            The decrypted plaintext as a string.

        Raises:
            ValueError: If key/IV sizes invalid, padding mode unknown, PKCS7
                padding invalid, or UTF-8 decoding fails (wrong key/IV or
                corrupted data).
        """
        if len(iv) != AES.block_size:
            raise ValueError(f"IV must be {AES.block_size} bytes, got {len(iv)}")
        if len(key) not in (16, 24, 32):
            raise ValueError(f"Key must be 16, 24, or 32 bytes, got {len(key)}")

        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(encrypted_data)

        if padding == "default":
            # Remove PKCS7 padding using pycryptodome's built-in function
            try:
                decrypted = unpad(decrypted, AES.block_size, style="pkcs7")
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
            return decrypted.decode("utf-8")
        except UnicodeDecodeError as e:
            msg = (
                "Failed to decode decrypted data as UTF-8 - possible decryption "
                "key/IV mismatch or corrupted ciphertext"
            )
            raise ValueError(msg) from e


class PycryptodomePBKDF2Provider:
    """High-performance PBKDF2 provider using pycryptodome.

    This implementation uses native C extensions from pycryptodome for
    faster key derivation compared to pure Python.
    """

    def derive_key(
        self,
        password: str,
        salt: bytes,
        iterations: int,
        key_size: int,
        hashmod: Callable[..., HashAlgorithm],
    ) -> bytes:
        """Derive a key using PBKDF2 with pycryptodome.

        Args:
            password: The password to derive from.
            salt: Random salt for derivation.
            iterations: Number of iterations (clamped to 65535 max).
            key_size: Desired key size in bytes.
            hashmod: Hash function factory.

        Returns:
            The derived key.

        Raises:
            ValueError: If hashmod is invalid or unsupported.
        """
        # Map hashmod callable to hash algorithm name
        try:
            hash_obj = hashmod()
            hash_name = hash_obj.name
        except (AttributeError, TypeError) as e:
            msg = "Invalid hashmod: must be a callable returning a hash object with 'name' attribute"
            raise ValueError(msg) from e

        # Map hash algorithm names to pycryptodome hash modules (static references)
        hash_mapping = {
            "sha256": SHA256,
            "sha1": SHA1,
            "sha512": SHA512,
            "sha224": SHA224,
            "sha384": SHA384,
            "md5": MD5,
        }

        if hash_name not in hash_mapping:
            msg = f"Unsupported hash algorithm: {hash_name}"
            raise ValueError(msg)

        # Get the hash module directly from the mapping
        pycrypto_hash = hash_mapping[hash_name]

        return PBKDF2(
            password,
            salt,
            key_size,
            count=min(iterations, 65535),
            hmac_hash_module=pycrypto_hash,
        )


class PycryptodomeRSAProvider:
    """High-performance RSA provider using pycryptodome.

    This implementation uses native C extensions from pycryptodome for
    faster RSA operations.
    """

    def load_private_key(self, pem_data: str) -> Any:
        """Load an RSA private key from PEM.

        Note:
            Caching is the caller's responsibility for optimal performance.

        Args:
            pem_data: RSA private key in PEM format.

        Returns:
            A parsed RSA.RsaKey object.
        """
        return _load_rsa_private_key_pycryptodome(pem_data)

    def sign(self, key: Any, data: bytes, algorithm: str = "SHA-256") -> bytes:
        """Sign data with an RSA private key using PKCS#1 v1.5.

        Args:
            key: A parsed RSA.RsaKey object.
            data: The data to sign.
            algorithm: The hash algorithm. Only "SHA-256" is supported.

        Returns:
            The signature bytes.

        Raises:
            TypeError: If key is not a valid RSA key object.
            ValueError: If algorithm is not "SHA-256".
        """
        # Validate key type - check for RSA key attributes
        if not hasattr(key, "n") or not hasattr(key, "e"):
            raise TypeError(
                f"Expected RSA.RsaKey object with required attributes, "
                f"got {type(key).__name__}"
            )

        # Create hash object
        if algorithm == "SHA-256":
            hash_obj = SHA256.new(data)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        # Sign using PKCS#1 v1.5
        return pkcs1_15.new(key).sign(hash_obj)


class PycryptodomeHashProvider:
    """High-performance hash provider using pycryptodome.

    This implementation uses native C extensions from pycryptodome for
    faster hashing operations.
    """

    _sha1_warning_shown = False

    def sha256(self, data: bytes) -> bytes:
        """Compute SHA-256 digest using pycryptodome.

        Args:
            data: The data to hash.

        Returns:
            The SHA-256 digest.
        """
        return SHA256.new(data).digest()

    def sha1(self, data: bytes) -> bytes:
        """Compute SHA-1 digest using pycryptodome.

        Args:
            data: The data to hash.

        Returns:
            The SHA-1 digest.

        Note:
            SHA-1 is cryptographically broken. Use only for legacy compatibility.
        """
        if not self.__class__._sha1_warning_shown:
            warnings.warn(
                "SHA-1 is deprecated and should only be used for legacy compatibility",
                DeprecationWarning,
                stacklevel=2,
            )
            self.__class__._sha1_warning_shown = True

        return SHA1.new(data).digest()


class PycryptodomeProvider:
    """Unified pycryptodome crypto provider.

    This provider implements all cryptographic operations using the pycryptodome
    library, which provides high-performance C-based implementations.

    Performance characteristics:
    - 5-10x faster AES operations vs pure Python
    - 10-20x faster RSA operations vs pure Python
    - 3-5x faster PBKDF2 key derivation vs pure Python
    - 5-10x faster hashing operations vs pure Python

    Raises:
        ImportError: If pycryptodome is not installed.

    Example:
        >>> from audible.crypto_provider import get_crypto_providers, PycryptodomeProvider  # doctest: +SKIP
        >>> providers = get_crypto_providers(PycryptodomeProvider)  # doctest: +SKIP
        >>> providers.provider_name  # doctest: +SKIP
        'pycryptodome'
    """

    def __init__(self) -> None:
        if not PYCRYPTODOME_AVAILABLE:
            raise ImportError(
                "pycryptodome is not installed. Install with: pip install "
                "audible[pycryptodome] (or audible[cryptography,pycryptodome] for full coverage)."
            )

        self._aes = PycryptodomeAESProvider()
        self._pbkdf2 = PycryptodomePBKDF2Provider()
        self._rsa = PycryptodomeRSAProvider()
        self._hash = PycryptodomeHashProvider()

    @property
    def aes(self) -> PycryptodomeAESProvider:
        """Get the AES provider."""
        return self._aes

    @property
    def pbkdf2(self) -> PycryptodomePBKDF2Provider:
        """Get the PBKDF2 provider."""
        return self._pbkdf2

    @property
    def rsa(self) -> PycryptodomeRSAProvider:
        """Get the RSA provider."""
        return self._rsa

    @property
    def hash(self) -> PycryptodomeHashProvider:
        """Get the hash provider."""
        return self._hash

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "pycryptodome"


__all__ = [
    "PYCRYPTODOME_AVAILABLE",
    "PycryptodomeAESProvider",
    "PycryptodomeHashProvider",
    "PycryptodomePBKDF2Provider",
    "PycryptodomeProvider",
    "PycryptodomeRSAProvider",
]
