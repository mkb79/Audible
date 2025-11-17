"""Provider registry for crypto backend selection.

This module implements a registry that automatically detects and selects the best
available crypto provider at runtime, with support for explicit provider selection.

Auto-detection priority:
1. cryptography (Rust-accelerated, modern API)
2. pycryptodome (C-based, high performance)
3. legacy (pure Python fallback)

The registry supports both automatic detection and explicit provider selection via
type-safe class-based API. Custom providers can be created by implementing the
CryptoProvider protocol.

Example:
    >>> from audible.crypto_provider import get_crypto_providers
    >>> providers = get_crypto_providers()  # Auto-detect
    >>> providers.provider_name in {"cryptography", "pycryptodome", "legacy"}
    True

    >>> from audible.crypto_provider import PycryptodomeProvider  # doctest: +SKIP
    >>> providers = get_crypto_providers(PycryptodomeProvider)  # doctest: +SKIP
    >>> providers.provider_name  # doctest: +SKIP
    'pycryptodome'

    >>> from audible.crypto_provider import CryptographyProvider  # doctest: +SKIP
    >>> providers = get_crypto_providers(CryptographyProvider)  # doctest: +SKIP
    >>> providers.provider_name  # doctest: +SKIP
    'cryptography'
"""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Any, cast  # doctest: +SKIP


# doctest: +SKIP
# doctest: +SKIP
if TYPE_CHECKING:
    from .protocols import CryptoProvider


logger = logging.getLogger("audible.crypto_provider")

# Registry state shared between helper functions
_STATE: dict[str, CryptoProvider | None] = {"auto": None, "default": None}


def _validate_provider(candidate: Any) -> CryptoProvider:
    required_attributes = ("aes", "pbkdf2", "rsa", "hash", "provider_name")
    missing = [attr for attr in required_attributes if not hasattr(candidate, attr)]
    if missing:
        joined = ", ".join(missing)
        raise TypeError(f"Object is not a CryptoProvider; missing: {joined}")
    return cast("CryptoProvider", candidate)


def _auto_detect_provider_class() -> type[CryptoProvider]:
    """Auto-detect and select the best available crypto provider class.

    Returns:
        Provider class (CryptographyProvider, PycryptodomeProvider, or LegacyProvider).
    """
    # Try cryptography first (preferred - Rust-accelerated)
    try:
        from .cryptography_provider import CRYPTOGRAPHY_AVAILABLE  # noqa: PLC0415

        if CRYPTOGRAPHY_AVAILABLE:
            from .cryptography_provider import (  # noqa: PLC0415
                CryptographyProvider,
            )

            logger.info("Using cryptography crypto provider (Rust-accelerated)")
            return CryptographyProvider
    except ImportError:
        pass

    # Try pycryptodome second (C-based)
    try:
        from .pycryptodome_provider import PYCRYPTODOME_AVAILABLE  # noqa: PLC0415

        if PYCRYPTODOME_AVAILABLE:
            from .pycryptodome_provider import PycryptodomeProvider  # noqa: PLC0415

            logger.info("Using pycryptodome crypto provider (C-based)")
            return PycryptodomeProvider
    except ImportError:
        pass

    # Fallback to legacy (always available)
    from .legacy_provider import LegacyProvider  # noqa: PLC0415

    logger.info("Using legacy crypto provider (pure Python)")
    return LegacyProvider


def _coerce_provider(
    provider: CryptoProvider | type[CryptoProvider],
) -> CryptoProvider:
    """Instantiate provider classes to obtain a validated provider instance."""
    instance: object
    if inspect.isclass(provider):
        instance = provider()
    else:
        instance = provider
    return _validate_provider(instance)


def get_crypto_providers(
    provider: CryptoProvider | type[CryptoProvider] | None = None,
) -> CryptoProvider:
    """Get the crypto provider.

    This is the main entry point for accessing crypto operations.

    Args:
        provider: Optional provider class or instance to use. Can be:
            - None: Auto-detect best available provider (default)
            - CryptoProvider subclass: Force the corresponding library
            - CryptoProvider instance: Reuse the supplied instance

    Returns:
        A CryptoProvider instance.

    Raises:
        ImportError: If specified provider is unavailable.

    Example:
        >>> from audible.crypto_provider import get_crypto_providers
        >>> providers = get_crypto_providers()  # Auto-detect
        >>> providers.provider_name in {"cryptography", "pycryptodome", "legacy"}
        True

        >>> from audible.crypto_provider import CryptographyProvider  # doctest: +SKIP
        >>> providers = get_crypto_providers(CryptographyProvider)  # doctest: +SKIP
        >>> providers.provider_name  # doctest: +SKIP
        'cryptography'
    """
    if provider is None:
        # Use global override if configured
        default_provider = _STATE["default"]
        if default_provider is not None:
            return default_provider

        # Use cached auto-detected instance
        auto_provider = _STATE["auto"]
        if auto_provider is None:
            provider_class = _auto_detect_provider_class()
            auto_provider = provider_class()
            _STATE["auto"] = auto_provider
        return auto_provider

    # Create new instance with specified provider
    try:
        return _coerce_provider(provider)
    except (ImportError, TypeError) as e:
        name = (
            provider.__name__ if isinstance(provider, type) else type(provider).__name__
        )
        raise ImportError(
            f"Failed to initialize {name}: {e}. "
            "Install the required extra (cryptography or pycryptodome) or let the system auto-detect "
            "in priority order (cryptography → pycryptodome → legacy)."
        ) from e


def set_default_crypto_provider(
    provider: CryptoProvider | type[CryptoProvider] | None = None,
) -> None:
    """Set or reset the global default crypto provider.

    Args:
        provider: Provider class or instance to enforce, or None to restore auto-detection.

    Raises:
        ImportError: If the requested provider cannot be initialized.

    Notes:
        When switching providers the cached instances are cleared so the next
        call to :func:`get_crypto_providers` returns a fresh instance.
    """
    if provider is None:
        _STATE["default"] = None
        _STATE["auto"] = None
        return

    try:
        _STATE["default"] = _coerce_provider(provider)
    except ImportError as e:
        name = (
            provider.__name__ if isinstance(provider, type) else type(provider).__name__
        )
        raise ImportError(
            f"Failed to initialize {name}: {e}. Install the required library or pass an instantiated provider."
        ) from e

    _STATE["auto"] = None
