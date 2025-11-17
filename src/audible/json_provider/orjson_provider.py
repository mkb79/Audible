"""orjson provider using the orjson library with smart fallback.

This module implements the JSON protocol using orjson, a Rust-based JSON library
that provides the highest performance among all Python JSON libraries.

orjson characteristics:
- 4-5x faster than stdlib for serialization/deserialization
- Rust-accelerated implementation
- Limited formatting options (indent=2 only)
- No separators support
- Returns bytes (requires decoding)

This provider implements smart fallback logic:
- indent=4 or other -> falls back to ujson/rapidjson/stdlib
- separators specified -> falls back to stdlib
- indent=2 or None -> uses native orjson (maximum performance)
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from .exceptions import JSONDecodeError, JSONEncodeError


if TYPE_CHECKING:
    from .protocols import JSONProvider


# Optional import - only available if orjson is installed
try:
    import orjson

    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False


logger = logging.getLogger("audible.json_provider.orjson")


class OrjsonProvider:
    r"""JSON provider using orjson with smart fallback logic.

    This provider implements JSON operations using orjson, the fastest available
    JSON library for Python. When orjson cannot handle a specific feature
    (e.g., indent=4, custom separators), it automatically falls back to the
    next best available provider.

    Fallback chain for unsupported features:
    1. ujson (C-based, indent=4 support)
    2. rapidjson (C++, indent=4 support)
    3. stdlib (pure Python, all features)

    Performance characteristics:
    - 4-5x faster than stdlib for compact/indent=2 (Rust implementation)
    - Automatic fallback to 2-3x faster libraries for indent=4
    - Falls back to stdlib only for separators (rare use case)

    Raises:
        ImportError: If orjson library is not installed.

    Example:
        >>> from audible.json_provider import get_json_provider, OrjsonProvider
        >>> provider = get_json_provider(OrjsonProvider)
        >>> provider.provider_name
        'orjson'
        >>> provider.dumps({"key": "value"})  # Uses orjson
        '{"key":"value"}'
        >>> print(provider.dumps({"key": "value"}, indent=4))  # Falls back to ujson
        {
            "key": "value"
        }
    """

    def __init__(self) -> None:
        if not ORJSON_AVAILABLE:
            raise ImportError(
                "orjson is not installed. Install with: pip install "
                "audible[orjson] or audible[json-full] for complete coverage."
            )

        # Lazy-loaded fallback provider for indent=4 cases
        self._fallback_provider: JSONProvider | None = None

    def _get_fallback_provider(self) -> JSONProvider:
        """Get or create fallback provider for unsupported features.

        Returns:
            Best available fallback provider (ujson > rapidjson > stdlib).

        Note:
            The fallback provider is lazily initialized and cached for performance.
        """
        if self._fallback_provider is None:
            # Try ujson first (best balance: fast + indent=4 support)
            try:
                from .ujson_provider import UJSON_AVAILABLE

                if UJSON_AVAILABLE:
                    from .ujson_provider import UjsonProvider

                    self._fallback_provider = UjsonProvider()
                    logger.debug("orjson fallback chain: ujson (C-based)")
                    return self._fallback_provider
            except ImportError:
                pass

            # Try rapidjson second (C++ alternative)
            try:
                from .rapidjson_provider import RAPIDJSON_AVAILABLE

                if RAPIDJSON_AVAILABLE:
                    from .rapidjson_provider import RapidjsonProvider

                    self._fallback_provider = RapidjsonProvider()
                    logger.debug("orjson fallback chain: rapidjson (C++)")
                    return self._fallback_provider
            except ImportError:
                pass

            # Final fallback to stdlib (always available)
            from .stdlib_provider import StdlibProvider

            self._fallback_provider = StdlibProvider()
            logger.debug("orjson fallback chain: stdlib (pure Python)")

        return self._fallback_provider

    def dumps(
        self,
        obj: Any,
        *,
        indent: int | None = None,
        separators: tuple[str, str] | None = None,
        ensure_ascii: bool = True,
    ) -> str:
        """Serialize obj to JSON with smart fallback.

        Args:
            obj: Python object to serialize.
            indent: Number of spaces for indentation.
            separators: (item_separator, key_separator) tuple.
            ensure_ascii: If True, escape non-ASCII characters.

        Returns:
            JSON string representation.

        Raises:
            JSONEncodeError: If obj cannot be serialized to JSON.

        Note:
            - separators -> stdlib fallback (orjson doesn't support)
            - indent=4 or other -> ujson/rapidjson/stdlib fallback
            - indent=2 or None -> native orjson (maximum performance)
        """
        # Case 1: separators requested -> must use stdlib
        if separators is not None:
            logger.debug(
                "orjson -> stdlib fallback (separators requested, rare use case)"
            )
            try:
                return json.dumps(
                    obj,
                    indent=indent,
                    separators=separators,
                    ensure_ascii=ensure_ascii,
                )
            except (TypeError, ValueError) as e:
                raise JSONEncodeError(f"Object not JSON serializable: {e}") from e

        # Case 2: indent != 2 and indent != None -> use fallback provider
        if indent is not None and indent != 2:
            fallback = self._get_fallback_provider()
            logger.debug(
                "orjson -> %s fallback (indent=%s)", fallback.provider_name, indent
            )
            return fallback.dumps(obj, indent=indent, ensure_ascii=ensure_ascii)

        # Case 3: orjson can handle natively (None or indent=2)
        option = 0
        if indent == 2:
            option |= orjson.OPT_INDENT_2

        # orjson always returns bytes, decode to str
        try:
            result = orjson.dumps(obj, option=option)
            return result.decode("utf-8")
        except (TypeError, ValueError) as e:
            raise JSONEncodeError(f"Object not JSON serializable: {e}") from e

    def loads(self, s: str | bytes) -> Any:
        """Deserialize JSON string using orjson.

        Args:
            s: JSON string or bytes to deserialize.

        Returns:
            Deserialized Python object.

        Raises:
            JSONDecodeError: If s contains invalid JSON or invalid UTF-8.

        Note:
            orjson handles all deserialization cases natively (no fallback needed).
        """
        if isinstance(s, str):
            try:
                s = s.encode("utf-8")
            except UnicodeEncodeError as e:
                raise JSONDecodeError(f"Invalid UTF-8 in JSON string: {e}") from e

        try:
            return orjson.loads(s)
        except (orjson.JSONDecodeError, ValueError) as e:
            raise JSONDecodeError(str(e)) from e

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "orjson"


__all__ = ["ORJSON_AVAILABLE", "OrjsonProvider"]
