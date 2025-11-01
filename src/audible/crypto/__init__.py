"""Crypto abstraction layer with support for multiple backends.

This module provides a clean abstraction layer for cryptographic operations,
supporting multiple backend libraries: cryptography, pycryptodome, and legacy
pure-Python implementations.

The provider is automatically selected at runtime based on availability:
1. cryptography (preferred - Rust-accelerated)
2. pycryptodome (C-based)
3. legacy (pure Python fallback)

Users can explicitly select a provider using the class-based API.

Example:
    >>> from audible.crypto import get_crypto_providers
    >>> providers = get_crypto_providers()  # Auto-detect
    >>> key = bytes([0]) * 16
    >>> iv = bytes([1]) * 16
    >>> ciphertext = providers.aes.encrypt(key, iv, "hello")
    >>> providers.aes.decrypt(key, iv, ciphertext)
    'hello'

    >>> from audible.crypto import CryptographyProvider  # doctest: +SKIP
    >>> providers = get_crypto_providers(CryptographyProvider)  # doctest: +SKIP
    >>> providers.provider_name  # doctest: +SKIP
    'cryptography'
"""

from .cryptography_provider import CryptographyProvider
from .legacy_provider import LegacyProvider
from .pycryptodome_provider import PycryptodomeProvider
from .registry import get_crypto_providers, set_default_crypto_provider


__all__ = [
    "CryptographyProvider",
    "LegacyProvider",
    "PycryptodomeProvider",
    "get_crypto_providers",
    "set_default_crypto_provider",
]
