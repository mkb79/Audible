"""Crypto abstraction layer for optional pycryptodome support.

This module provides a clean abstraction layer for cryptographic operations,
allowing the library to use either the high-performance pycryptodome library
or fall back to the legacy pure-Python libraries (pyaes, rsa, pbkdf2).

The provider is automatically selected at runtime based on availability,
with pycryptodome preferred for performance.

Example:
    >>> from audible.crypto import get_crypto_providers
    >>> providers = get_crypto_providers()
    >>> key = bytes([0]) * 16
    >>> iv = bytes([1]) * 16
    >>> ciphertext = providers.aes.encrypt(key, iv, "hello")
    >>> providers.aes.decrypt(key, iv, ciphertext)
    'hello'
"""

from .registry import get_crypto_providers


__all__ = ["get_crypto_providers"]
