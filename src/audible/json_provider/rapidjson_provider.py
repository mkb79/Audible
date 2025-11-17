"""python-rapidjson provider using the python-rapidjson library.

This module implements the JSON protocol using python-rapidjson, a Python
wrapper for the C++ RapidJSON library.

python-rapidjson characteristics:
- 2-3x faster than stdlib for serialization/deserialization
- Native support for custom indentation
- Good compatibility with stdlib json API
- No native separators support
- Excellent for both compact and pretty-printed output

This serves as an alternative fallback provider to ujson.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .exceptions import JSONDecodeError, JSONEncodeError


# Optional import - only available if python-rapidjson is installed
try:
    import rapidjson

    RAPIDJSON_AVAILABLE = True
except ImportError:
    RAPIDJSON_AVAILABLE = False


logger = logging.getLogger("audible.json_provider.rapidjson")


class RapidjsonProvider:
    r"""JSON provider using the python-rapidjson library.

    This provider implements JSON operations using python-rapidjson, a C++
    wrapper that provides excellent performance. It supports custom indentation
    natively, making it suitable for all common use cases.

    Performance characteristics:
    - 2-3x faster than stdlib (C++ implementation)
    - Native indent support
    - No separators customization
    - Robust error handling

    Limitations:
    - No custom separators support
    - Falls back to stdlib for separators

    Raises:
        ImportError: If python-rapidjson library is not installed.

    Example:
        >>> from audible.json import get_json_provider, RapidjsonProvider
        >>> provider = get_json_provider(RapidjsonProvider)
        >>> provider.provider_name
        'rapidjson'
        >>> print(provider.dumps({"key": "value"}, indent=4))
        {
            "key": "value"
        }
    """

    def __init__(self) -> None:
        if not RAPIDJSON_AVAILABLE:
            raise ImportError(
                "python-rapidjson is not installed. Install with: pip install "
                "audible[rapidjson] or audible[json-full] for complete coverage."
            )

    def dumps(
        self,
        obj: Any,
        *,
        indent: int | None = None,
        separators: tuple[str, str] | None = None,
        ensure_ascii: bool = True,
    ) -> str:
        """Serialize obj to JSON string using python-rapidjson.

        Args:
            obj: Python object to serialize.
            indent: Number of spaces for indentation.
            separators: If specified, falls back to stdlib (rapidjson doesn't support this).
            ensure_ascii: If True, escape non-ASCII characters.

        Returns:
            JSON string representation.

        Raises:
            JSONEncodeError: If obj cannot be serialized to JSON.

        Note:
            Falls back to stdlib json if separators are specified, as rapidjson
            doesn't support custom separators.
        """
        # Fallback to stdlib for separators (rapidjson doesn't support this)
        if separators is not None:
            logger.debug("rapidjson -> stdlib fallback (separators not supported)")
            try:
                return json.dumps(
                    obj,
                    indent=indent,
                    separators=separators,
                    ensure_ascii=ensure_ascii,
                )
            except (TypeError, ValueError) as e:
                raise JSONEncodeError(f"Object not JSON serializable: {e}") from e

        # rapidjson native handling
        # Note: rapidjson uses different parameter names
        try:
            if indent is not None:
                return rapidjson.dumps(obj, indent=indent, ensure_ascii=ensure_ascii)
            return rapidjson.dumps(obj, ensure_ascii=ensure_ascii)
        except (TypeError, ValueError, OverflowError) as e:
            raise JSONEncodeError(f"Object not JSON serializable: {e}") from e

    def loads(self, s: str | bytes) -> Any:
        """Deserialize JSON string using python-rapidjson.

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
            return rapidjson.loads(s)
        except (rapidjson.JSONDecodeError, ValueError) as e:
            raise JSONDecodeError(str(e)) from e

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "rapidjson"


__all__ = ["RAPIDJSON_AVAILABLE", "RapidjsonProvider"]
