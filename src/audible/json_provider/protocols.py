"""Protocol definitions for JSON providers.

This module defines the contracts that all JSON provider implementations
must follow. Using Python's Protocol allows for type-safe duck typing and
enables static type checking with mypy.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class JSONProvider(Protocol):
    """Protocol for JSON serialization/deserialization operations.

    Implementations must provide JSON encoding/decoding with configurable
    formatting options. Providers may implement smart fallback logic for
    features they don't natively support.

    The protocol supports:
    - Custom indentation (for human-readable output)
    - Custom separators (for compact output)
    - ASCII vs Unicode output control

    Exception Handling:
        All implementations MUST raise :exc:`audible.json_provider.JSONDecodeError` when
        JSON parsing fails, and :exc:`audible.json_provider.JSONEncodeError` when
        serialization fails. This ensures consistent error handling across
        all providers and calling code.

        Custom providers should wrap library-specific exceptions::

            from audible.json_provider import JSONDecodeError, JSONEncodeError
            import some_json_lib

            def loads(self, s: str | bytes) -> Any:
                try:
                    return some_json_lib.loads(s)
                except some_json_lib.DecodeError as e:
                    raise JSONDecodeError(str(e)) from e

            def dumps(self, obj: Any, ...) -> str:
                try:
                    return some_json_lib.dumps(obj, ...)
                except some_json_lib.EncodeError as e:
                    raise JSONEncodeError(str(e)) from e
    """

    def dumps(
        self,
        obj: Any,
        *,
        indent: int | None = None,
        separators: tuple[str, str] | None = None,
        ensure_ascii: bool = True,
    ) -> str:
        """Serialize obj to JSON string.

        Args:
            obj: Python object to serialize.
            indent: Number of spaces for indentation. None for compact output.
            separators: (item_separator, key_separator) tuple for custom formatting.
            ensure_ascii: If True, escape non-ASCII characters.

        Returns:
            JSON string representation.

        Note:
            Some providers may fall back to alternative implementations for
            unsupported parameter combinations (e.g., orjson falls back for
            indent != 2 or when separators are specified).
        """
        ...

    def loads(self, s: str | bytes) -> Any:
        """Deserialize JSON string to Python object.

        Args:
            s: JSON string or bytes to deserialize.

        Returns:
            Deserialized Python object.
        """
        ...

    @property
    def provider_name(self) -> str:
        """Return the human-readable provider name.

        Returns:
            Provider identifier (e.g., "orjson", "ujson", "stdlib").
        """
        ...


__all__ = ["JSONProvider"]
