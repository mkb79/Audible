"""ujson provider using the ujson library.

This module implements the JSON protocol using ujson, a C-based JSON library
that provides excellent performance while maintaining good compatibility with
stdlib json.

ujson characteristics:
- 2-3x faster than stdlib for serialization/deserialization
- Native support for custom indentation (including indent=4)
- Good compatibility with stdlib json API
- No native separators support (uses default: ', ' and ': ')

This is the preferred fallback provider for orjson when indent=4 is needed.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .exceptions import JSONDecodeError, JSONEncodeError


# Optional import - only available if ujson is installed
try:
    import ujson

    UJSON_AVAILABLE = True
except ImportError:
    UJSON_AVAILABLE = False


logger = logging.getLogger("audible.json_provider.ujson")


class UjsonProvider:
    r"""JSON provider using the ujson library.

    This provider implements JSON operations using ujson, a C-based library
    that offers excellent performance. It supports custom indentation natively,
    making it an ideal fallback for orjson when indent=4 is required.

    Performance characteristics:
    - 2-3x faster than stdlib (C implementation)
    - Native indent support (any positive integer)
    - No separators customization (uses defaults)
    - Excellent for pretty-printed output

    Limitations:
    - No custom separators support
    - Falls back to stdlib for separators

    Raises:
        ImportError: If ujson library is not installed.

    Example:
        >>> from audible.json import get_json_provider, UjsonProvider
        >>> provider = get_json_provider(UjsonProvider)
        >>> provider.provider_name
        'ujson'
        >>> print(provider.dumps({"key": "value"}, indent=4))
        {
            "key": "value"
        }
    """

    def __init__(self) -> None:
        if not UJSON_AVAILABLE:
            raise ImportError(
                "ujson is not installed. Install with: pip install "
                "audible[ujson] or audible[json-full] for complete coverage."
            )

    def dumps(
        self,
        obj: Any,
        *,
        indent: int | None = None,
        separators: tuple[str, str] | None = None,
        ensure_ascii: bool = True,
    ) -> str:
        """Serialize obj to JSON string using ujson.

        Args:
            obj: Python object to serialize.
            indent: Number of spaces for indentation.
            separators: If specified, falls back to stdlib (ujson doesn't support this).
            ensure_ascii: If True, escape non-ASCII characters.

        Returns:
            JSON string representation.

        Raises:
            JSONEncodeError: If obj cannot be serialized to JSON.

        Note:
            Falls back to stdlib json if separators are specified, as ujson
            doesn't support custom separators.
        """
        # Fallback to stdlib for separators (ujson doesn't support this)
        if separators is not None:
            logger.debug("ujson -> stdlib fallback (separators not supported)")
            try:
                return json.dumps(
                    obj,
                    indent=indent,
                    separators=separators,
                    ensure_ascii=ensure_ascii,
                )
            except (TypeError, ValueError) as e:
                raise JSONEncodeError(f"Object not JSON serializable: {e}") from e

        # ujson native handling
        try:
            return ujson.dumps(
                obj,
                indent=indent if indent is not None else 0,
                ensure_ascii=ensure_ascii,
            )
        except (TypeError, ValueError, OverflowError) as e:
            raise JSONEncodeError(f"Object not JSON serializable: {e}") from e

    def loads(self, s: str | bytes) -> Any:
        """Deserialize JSON string using ujson.

        Args:
            s: JSON string or bytes to deserialize.

        Returns:
            Deserialized Python object.

        Raises:
            JSONDecodeError: If s contains invalid JSON or invalid UTF-8.
        """
        if isinstance(s, bytes):
            try:
                s = s.decode("utf-8")
            except UnicodeDecodeError as e:
                raise JSONDecodeError(f"Invalid UTF-8 in JSON bytes: {e}") from e

        try:
            return ujson.loads(s)
        except (ujson.JSONDecodeError, ValueError) as e:
            raise JSONDecodeError(str(e)) from e

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "ujson"


__all__ = ["UJSON_AVAILABLE", "UjsonProvider"]
