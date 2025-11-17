"""Provider registry for JSON backend selection.

This module implements a registry that automatically detects and selects the best
available JSON provider at runtime, with support for explicit provider selection.

Auto-detection priority (optimized for real-world usage):
1. orjson (Rust-accelerated, fastest, with smart fallback)
2. ujson (C-based, indent=4 native support)
3. rapidjson (C++, indent=4 native support)
4. stdlib (pure Python, always available)

The registry supports both automatic detection and explicit provider selection via
type-safe class-based API. Custom providers can be created by implementing the
JSONProvider protocol.

Example:
    >>> from audible.json_provider import get_json_provider
    >>> provider = get_json_provider()  # Auto-detect
    >>> provider.provider_name in {"orjson", "ujson", "rapidjson", "stdlib"}
    True

    >>> from audible.json_provider import UjsonProvider  # doctest: +SKIP
    >>> provider = get_json_provider(UjsonProvider)  # doctest: +SKIP
    >>> provider.provider_name  # doctest: +SKIP
    'ujson'

    >>> from audible.json_provider import OrjsonProvider  # doctest: +SKIP
    >>> provider = get_json_provider(OrjsonProvider)  # doctest: +SKIP
    >>> provider.provider_name  # doctest: +SKIP
    'orjson'
"""

from __future__ import annotations

import inspect
import logging
import threading
from typing import TYPE_CHECKING, Any, cast


if TYPE_CHECKING:
    from .protocols import JSONProvider


logger = logging.getLogger("audible.json_provider")

# Registry state shared between helper functions
_STATE: dict[str, JSONProvider | None] = {"auto": None, "default": None}
# Thread lock for safe concurrent access to _STATE
_STATE_LOCK = threading.Lock()


def _validate_provider(candidate: Any) -> JSONProvider:
    """Validate that an object implements the JSONProvider protocol.

    Args:
        candidate: Object to validate.

    Returns:
        Validated JSONProvider instance.

    Raises:
        TypeError: If object doesn't implement required protocol methods.
    """
    required_attributes = ("dumps", "loads", "provider_name")
    missing = [attr for attr in required_attributes if not hasattr(candidate, attr)]
    if missing:
        joined = ", ".join(missing)
        raise TypeError(f"Object is not a JSONProvider; missing: {joined}")
    return cast("JSONProvider", candidate)


def _auto_detect_provider_class() -> type[JSONProvider]:
    """Auto-detect and select the best available JSON provider class.

    Priority order optimized for real-world usage:
    1. orjson - Fastest for compact JSON, smart fallback for indent=4
    2. ujson - Excellent fallback, native indent=4 support
    3. rapidjson - Alternative fallback, native indent=4 support
    4. stdlib - Always available baseline

    Returns:
        Provider class (OrjsonProvider, UjsonProvider, RapidjsonProvider, or StdlibProvider).
    """
    # Try orjson first (preferred - Rust-accelerated with smart fallback)
    try:
        from .orjson_provider import ORJSON_AVAILABLE

        if ORJSON_AVAILABLE:
            from .orjson_provider import OrjsonProvider

            logger.info(
                "Using orjson JSON provider (Rust-accelerated, with smart fallback)"
            )
            return OrjsonProvider
    except ImportError:
        pass

    # Try ujson second (C-based, native indent=4 support)
    try:
        from .ujson_provider import UJSON_AVAILABLE

        if UJSON_AVAILABLE:
            from .ujson_provider import UjsonProvider

            logger.info("Using ujson JSON provider (C-based, indent=4 native)")
            return UjsonProvider
    except ImportError:
        pass

    # Try rapidjson third (C++, native indent=4 support)
    try:
        from .rapidjson_provider import RAPIDJSON_AVAILABLE

        if RAPIDJSON_AVAILABLE:
            from .rapidjson_provider import RapidjsonProvider

            logger.info("Using rapidjson JSON provider (C++, indent=4 native)")
            return RapidjsonProvider
    except ImportError:
        pass

    # Fallback to stdlib (always available)
    from .stdlib_provider import StdlibProvider

    logger.info("Using stdlib JSON provider (pure Python)")
    return StdlibProvider


def _coerce_provider(
    provider: JSONProvider | type[JSONProvider],
) -> JSONProvider:
    """Instantiate provider classes to obtain a validated provider instance.

    Args:
        provider: Provider class or instance.

    Returns:
        Validated provider instance.
    """
    instance: object
    if inspect.isclass(provider):
        instance = provider()
    else:
        instance = provider
    return _validate_provider(instance)


def get_json_provider(
    provider: JSONProvider | type[JSONProvider] | None = None,
) -> JSONProvider:
    """Get the JSON provider.

    This is the main entry point for accessing JSON operations.

    Args:
        provider: Optional provider class or instance to use. Can be:
            - None: Auto-detect best available provider (default)
            - JSONProvider subclass: Force the corresponding library
            - JSONProvider instance: Reuse the supplied instance

    Returns:
        A JSONProvider instance.

    Raises:
        ImportError: If specified provider is unavailable.

    Note:
        This function is thread-safe. Concurrent calls will safely share cached
        provider instances.

    Example:
        >>> from audible.json_provider import get_json_provider
        >>> provider = get_json_provider()  # Auto-detect
        >>> provider.provider_name in {"orjson", "ujson", "rapidjson", "stdlib"}
        True

        >>> from audible.json_provider import OrjsonProvider  # doctest: +SKIP
        >>> provider = get_json_provider(OrjsonProvider)  # doctest: +SKIP
        >>> provider.provider_name  # doctest: +SKIP
        'orjson'
    """
    if provider is None:
        # Use global override if configured
        with _STATE_LOCK:
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
            "Install the required extra (orjson, ujson, rapidjson, or json-full) or let the system auto-detect "
            "in priority order (orjson -> ujson -> rapidjson -> stdlib)."
        ) from e


def set_default_json_provider(
    provider: JSONProvider | type[JSONProvider] | None = None,
) -> None:
    """Set or reset the global default JSON provider.

    Args:
        provider: Provider class or instance to enforce, or None to restore auto-detection.

    Raises:
        ImportError: If the requested provider cannot be initialized.

    Note:
        When switching providers the cached instances are cleared so the next
        call to :func:`get_json_provider` returns a fresh instance.
        This function is thread-safe.

    Example:
        >>> from audible.json_provider import set_default_json_provider, StdlibProvider
        >>> set_default_json_provider(StdlibProvider)  # Force stdlib
        >>> set_default_json_provider(None)  # Restore auto-detection
    """
    with _STATE_LOCK:
        if provider is None:
            _STATE["default"] = None
            _STATE["auto"] = None
            return

        try:
            _STATE["default"] = _coerce_provider(provider)
        except ImportError as e:
            name = (
                provider.__name__
                if isinstance(provider, type)
                else type(provider).__name__
            )
            raise ImportError(
                f"Failed to initialize {name}: {e}. Install the required library or pass an instantiated provider."
            ) from e

        _STATE["auto"] = None


__all__ = ["get_json_provider", "set_default_json_provider"]
