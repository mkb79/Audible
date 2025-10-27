"""Provider registry for crypto backend selection.

This module implements a singleton registry that automatically detects and
selects the best available crypto provider (pycryptodome or legacy) at runtime.

The registry uses lazy initialization - providers are only loaded when first
accessed, minimizing import overhead.
"""

import logging
import warnings
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .protocols import AESProvider, HashProvider, PBKDF2Provider, RSAProvider


logger = logging.getLogger("audible.crypto")


class CryptoProviderRegistry:
    """Singleton registry for crypto provider management.

    This class implements the singleton pattern to ensure only one provider
    set is active per process. Providers are selected automatically based on
    availability, with pycryptodome preferred for performance.

    The registry uses lazy initialization - providers are only instantiated
    when first accessed through the property methods.

    Example:
        >>> registry = CryptoProviderRegistry()
        >>> registry.provider_name in {"legacy", "pycryptodome"}
        True
        >>> key = bytes([2]) * 16
        >>> iv = bytes([3]) * 16
        >>> isinstance(registry.aes.encrypt(key, iv, "data"), bytes)
        True
    """

    _instance: "CryptoProviderRegistry | None" = None
    _initialized: bool = False

    def __new__(cls) -> "CryptoProviderRegistry":
        """Ensure only one instance exists (singleton pattern).

        Returns:
            The singleton CryptoProviderRegistry instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the registry (only once due to singleton pattern)."""
        if self._initialized:
            return

        self._aes: AESProvider | None = None
        self._pbkdf2: PBKDF2Provider | None = None
        self._rsa: RSAProvider | None = None
        self._hash: HashProvider | None = None
        self._provider_name: str | None = None
        self._warning_shown: bool = False
        self._initialized = True

    def _select_provider(self) -> str:
        """Auto-detect and select the best available crypto provider.

        Returns:
            "pycryptodome" or "legacy".
        """
        try:
            from .pycryptodome_provider import PYCRYPTODOME_AVAILABLE  # noqa: PLC0415

            if PYCRYPTODOME_AVAILABLE:
                logger.info("Using pycryptodome crypto provider (high performance)")
                return "pycryptodome"
        except ImportError:
            pass

        logger.info("Using legacy crypto provider (pyaes + rsa + pbkdf2)")
        return "legacy"

    def _initialize_providers(self) -> None:
        """Lazy initialization of crypto providers.

        This method is called automatically on first provider access.
        It selects the best available backend and instantiates all providers.
        """
        if self._aes is not None:
            # Already initialized
            return

        provider_name = self._select_provider()
        self._provider_name = provider_name

        if provider_name == "pycryptodome":
            from .pycryptodome_provider import (  # noqa: PLC0415
                PycryptodomeAESProvider,
                PycryptodomeHashProvider,
                PycryptodomePBKDF2Provider,
                PycryptodomeRSAProvider,
            )

            self._aes = PycryptodomeAESProvider()
            self._pbkdf2 = PycryptodomePBKDF2Provider()
            self._rsa = PycryptodomeRSAProvider()
            self._hash = PycryptodomeHashProvider()

        else:
            # Legacy provider
            from .legacy_provider import (  # noqa: PLC0415
                LegacyAESProvider,
                LegacyHashProvider,
                LegacyPBKDF2Provider,
                LegacyRSAProvider,
            )

            self._aes = LegacyAESProvider()
            self._pbkdf2 = LegacyPBKDF2Provider()
            self._rsa = LegacyRSAProvider()
            self._hash = LegacyHashProvider()

            # Show warning only once, only on first crypto operation
            if not self._warning_shown:
                warnings.warn(
                    "Using legacy crypto libraries (pyaes, rsa, pbkdf2). "
                    "For better performance, install pycryptodome: "
                    "pip install audible[crypto]",
                    UserWarning,
                    stacklevel=4,
                )
                self._warning_shown = True

        logger.debug("Initialized %s crypto providers", provider_name)

    @property
    def aes(self) -> "AESProvider":
        """Get the AES encryption/decryption provider.

        Returns:
            An AESProvider instance (lazy-loaded on first access).
        """
        self._initialize_providers()
        assert self._aes is not None  # noqa: S101
        return self._aes

    @property
    def pbkdf2(self) -> "PBKDF2Provider":
        """Get the PBKDF2 key derivation provider.

        Returns:
            A PBKDF2Provider instance (lazy-loaded on first access).
        """
        self._initialize_providers()
        assert self._pbkdf2 is not None  # noqa: S101
        return self._pbkdf2

    @property
    def rsa(self) -> "RSAProvider":
        """Get the RSA signing provider.

        Returns:
            An RSAProvider instance (lazy-loaded on first access).
        """
        self._initialize_providers()
        assert self._rsa is not None  # noqa: S101
        return self._rsa

    @property
    def hash(self) -> "HashProvider":
        """Get the cryptographic hash provider.

        Returns:
            A HashProvider instance (lazy-loaded on first access).
        """
        self._initialize_providers()
        assert self._hash is not None  # noqa: S101
        return self._hash

    @property
    def provider_name(self) -> str:
        """Get the name of the active crypto provider.

        Returns:
            "pycryptodome" or "legacy".
        """
        self._initialize_providers()
        assert self._provider_name is not None  # noqa: S101
        return self._provider_name


# Global singleton instance
_registry = CryptoProviderRegistry()


def get_crypto_providers() -> CryptoProviderRegistry:
    """Get the global crypto provider registry.

    This is the main entry point for accessing crypto operations.
    The registry automatically selects the best available provider
    and caches it for subsequent calls.

    Returns:
        The global CryptoProviderRegistry singleton.

    Example:
        >>> from audible.crypto import get_crypto_providers
        >>> providers = get_crypto_providers()
        >>> providers is get_crypto_providers()
        True
        >>> key = bytes([4]) * 16
        >>> iv = bytes([5]) * 16
        >>> plaintext = "demo"
        >>> ciphertext = providers.aes.encrypt(key, iv, plaintext)
        >>> providers.aes.decrypt(key, iv, ciphertext)
        'demo'
    """
    return _registry
