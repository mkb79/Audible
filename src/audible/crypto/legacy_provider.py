"""Legacy crypto provider using pure Python libraries.

This module implements the crypto protocols using the existing pure-Python
libraries: pyaes for AES, pbkdf2 for key derivation, and rsa for RSA signing.

These implementations are slower than native C extensions but are pure Python
and work in all environments without compilation.
"""

import hmac
import logging
from collections.abc import Callable
from functools import lru_cache
from hashlib import sha1, sha256
from typing import Any

import rsa
from pbkdf2 import PBKDF2  # type: ignore[import-untyped]
from pyaes import (  # type: ignore[import-untyped]
    AESModeOfOperationCBC,
    Decrypter,
    Encrypter,
)


logger = logging.getLogger("audible.crypto.legacy")


# Module-level cached function to avoid memory leaks with lru_cache on methods
@lru_cache(maxsize=8)
def _load_rsa_private_key_cached(pem_data: str) -> rsa.PrivateKey:
    """Load and cache an RSA private key from PEM.

    This function caches up to 8 different keys. For the same PEM string,
    the cached key object will be returned instead of re-parsing.

    Args:
        pem_data: RSA private key in PEM format.

    Returns:
        A parsed rsa.PrivateKey object.
    """
    logger.debug("Loading RSA private key (legacy provider)")
    return rsa.PrivateKey.load_pkcs1(pem_data.encode("utf-8"))


class LegacyAESProvider:
    """AES-CBC provider using the pyaes library.

    This implementation uses pure Python AES from the pyaes library.
    While slower than native implementations, it works everywhere and
    requires no compilation.
    """

    def encrypt(
        self, key: bytes, iv: bytes, data: str, padding: str = "default"
    ) -> bytes:
        """Encrypt data using AES-CBC with pyaes.

        Args:
            key: The AES encryption key.
            iv: The initialization vector.
            data: The plaintext data to encrypt.
            padding: Padding mode ("default" for PKCS7, "none" for no padding).

        Returns:
            The encrypted ciphertext.
        """
        encrypter = Encrypter(AESModeOfOperationCBC(key, iv), padding=padding)
        encrypted: bytes = encrypter.feed(data) + encrypter.feed()
        return encrypted

    def decrypt(
        self, key: bytes, iv: bytes, encrypted_data: bytes, padding: str = "default"
    ) -> str:
        """Decrypt data using AES-CBC with pyaes.

        Args:
            key: The AES decryption key.
            iv: The initialization vector.
            encrypted_data: The ciphertext to decrypt.
            padding: Padding mode ("default" for PKCS7, "none" for no padding).

        Returns:
            The decrypted plaintext as a string.
        """
        decrypter = Decrypter(AESModeOfOperationCBC(key, iv), padding=padding)
        decrypted: bytes = decrypter.feed(encrypted_data) + decrypter.feed()
        return decrypted.decode("utf-8")


class LegacyPBKDF2Provider:
    """PBKDF2 provider using the pbkdf2 library.

    This implementation uses pure Python PBKDF2 from the pbkdf2 library.
    """

    def derive_key(
        self,
        password: str,
        salt: bytes,
        iterations: int,
        key_size: int,
        hashmod: Callable[[], Any],
    ) -> bytes:
        """Derive a key using PBKDF2 with the pbkdf2 library.

        Args:
            password: The password to derive from.
            salt: Random salt for derivation.
            iterations: Number of iterations (clamped to 65535 max).
            key_size: Desired key size in bytes.
            hashmod: Hash function factory.

        Returns:
            The derived key.
        """
        kdf = PBKDF2(password, salt, min(iterations, 65535), hashmod, hmac)
        key: bytes = kdf.read(key_size)
        return key


class LegacyRSAProvider:
    """RSA provider using the rsa library with key caching.

    This implementation uses pure Python RSA from the rsa library.
    Keys are cached via a module-level function to avoid re-parsing the same PEM
    string multiple times, which significantly improves performance.
    """

    def load_private_key(self, pem_data: str) -> rsa.PrivateKey:
        """Load and cache an RSA private key from PEM.

        This method uses a module-level cached function to avoid memory leaks
        that occur when using lru_cache on instance methods.

        Args:
            pem_data: RSA private key in PEM format.

        Returns:
            A parsed rsa.PrivateKey object.
        """
        return _load_rsa_private_key_cached(pem_data)

    def sign(self, key: Any, data: bytes, algorithm: str = "SHA-256") -> bytes:
        """Sign data with an RSA private key using PKCS#1 v1.5.

        Args:
            key: A parsed rsa.PrivateKey object.
            data: The data to sign.
            algorithm: The hash algorithm (default: "SHA-256").

        Returns:
            The signature bytes.

        Raises:
            TypeError: If key is not an rsa.PrivateKey instance.
        """
        if not isinstance(key, rsa.PrivateKey):
            raise TypeError(f"Expected rsa.PrivateKey, got {type(key).__name__}")
        return rsa.pkcs1.sign(data, key, algorithm)


class LegacyHashProvider:
    """Hash provider using Python's standard hashlib.

    This implementation uses the standard library hashlib module.
    """

    def sha256(self, data: bytes) -> bytes:
        """Compute SHA-256 digest using hashlib.

        Args:
            data: The data to hash.

        Returns:
            The SHA-256 digest.
        """
        return sha256(data).digest()

    def sha1(self, data: bytes) -> bytes:
        """Compute SHA-1 digest using hashlib.

        Args:
            data: The data to hash.

        Returns:
            The SHA-1 digest.

        Note:
            SHA-1 is cryptographically broken. Use only for legacy compatibility.
        """
        return sha1(data, usedforsecurity=False).digest()
