"""Pycryptodome crypto provider using native C extensions.

This module implements the crypto protocols using the pycryptodome library,
which provides high-performance cryptographic operations via C extensions.

This is significantly faster than the pure Python implementations but requires
pycryptodome to be installed as an optional dependency.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from functools import lru_cache
from typing import Any


# Optional import - only available if pycryptodome is installed
try:
    from Crypto.Cipher import AES  # type: ignore[import-not-found]
    from Crypto.Hash import SHA1, SHA256  # type: ignore[import-not-found]
    from Crypto.Protocol.KDF import PBKDF2  # type: ignore[import-not-found]
    from Crypto.PublicKey import RSA  # type: ignore[import-not-found]
    from Crypto.Signature import pkcs1_15  # type: ignore[import-not-found]
    from Crypto.Util.Padding import pad, unpad  # type: ignore[import-not-found]

    PYCRYPTODOME_AVAILABLE = True
except ImportError:
    PYCRYPTODOME_AVAILABLE = False


logger = logging.getLogger("audible.crypto.pycryptodome")


# Module-level cached function to avoid memory leaks with lru_cache on methods
@lru_cache(maxsize=8)
def _load_rsa_private_key_pycryptodome(pem_data: str) -> Any:
    """Load and cache an RSA private key from PEM using pycryptodome.

    This function caches up to 8 different keys. For the same PEM string,
    the cached key object will be returned instead of re-parsing.

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
        """
        cipher = AES.new(key, AES.MODE_CBC, iv)
        data_bytes = data.encode("utf-8")

        if padding == "default":
            # Apply PKCS7 padding using pycryptodome's built-in function
            data_bytes = pad(data_bytes, AES.block_size, style="pkcs7")

        return cipher.encrypt(data_bytes)  # type: ignore[no-any-return]

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
        """
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(encrypted_data)

        if padding == "default":
            # Remove PKCS7 padding using pycryptodome's built-in function
            # This includes validation and raises ValueError if padding is invalid
            decrypted = unpad(decrypted, AES.block_size, style="pkcs7")

        return decrypted.decode("utf-8")  # type: ignore[no-any-return]


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
        hashmod: Callable[[], Any],
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
        """
        # Map hashmod callable to hash module name
        hash_name = hashmod().name  # e.g., "sha256"

        # Get the corresponding hashlib module for pycryptodome
        hash_module = getattr(hashlib, hash_name)

        return PBKDF2(  # type: ignore[no-any-return]
            password,
            salt,
            key_size,
            count=min(iterations, 65535),
            hmac_hash_module=hash_module,
        )


class PycryptodomeRSAProvider:
    """High-performance RSA provider using pycryptodome with key caching.

    This implementation uses native C extensions from pycryptodome for
    faster RSA operations. Keys are cached to avoid re-parsing.
    """

    def load_private_key(self, pem_data: str) -> Any:
        """Load and cache an RSA private key from PEM.

        This method uses a module-level cached function to avoid memory leaks
        that occur when using lru_cache on instance methods.

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
            algorithm: The hash algorithm (default: "SHA-256").

        Returns:
            The signature bytes.

        Raises:
            ValueError: If algorithm is not supported.
        """
        # Create hash object
        if algorithm == "SHA-256":
            hash_obj = SHA256.new(data)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        # Sign using PKCS#1 v1.5
        # Type checking is unnecessary - pycryptodome will raise clear errors
        return pkcs1_15.new(key).sign(hash_obj)  # type: ignore[no-any-return]


class PycryptodomeHashProvider:
    """High-performance hash provider using pycryptodome.

    This implementation uses native C extensions from pycryptodome for
    faster hashing operations.
    """

    def sha256(self, data: bytes) -> bytes:
        """Compute SHA-256 digest using pycryptodome.

        Args:
            data: The data to hash.

        Returns:
            The SHA-256 digest.
        """
        return SHA256.new(data).digest()  # type: ignore[no-any-return]

    def sha1(self, data: bytes) -> bytes:
        """Compute SHA-1 digest using pycryptodome.

        Args:
            data: The data to hash.

        Returns:
            The SHA-1 digest.

        Note:
            SHA-1 is cryptographically broken. Use only for legacy compatibility.
        """
        return SHA1.new(data).digest()  # type: ignore[no-any-return]
