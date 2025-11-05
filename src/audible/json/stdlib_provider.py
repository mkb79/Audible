"""Stdlib JSON provider using Python's built-in json module.

This module implements the JSON protocol using Python's standard library json
module, which provides complete feature support and is always available.

The stdlib provider serves as:
- Fallback when no optimized libraries are installed
- Final fallback for features unsupported by optimized providers (e.g., separators)
- Reference implementation with guaranteed compatibility
"""

from __future__ import annotations

import json
import logging
from typing import Any


logger = logging.getLogger("audible.json.stdlib")

# stdlib is always available
STDLIB_AVAILABLE = True


class StdlibProvider:
    r"""JSON provider using Python's standard library.

    This provider implements all JSON operations using the built-in json module.
    It provides complete feature support including custom separators, arbitrary
    indentation levels, and all encoding options.

    Performance characteristics:
    - Baseline performance (pure Python)
    - Complete feature set
    - Always available (no external dependencies)
    - Guaranteed compatibility

    Example:
        >>> from audible.json import get_json_provider, StdlibProvider
        >>> provider = get_json_provider(StdlibProvider)
        >>> provider.provider_name
        'stdlib'
        >>> print(provider.dumps({"key": "value"}, indent=4))
        {
            "key": "value"
        }
    """

    def dumps(
        self,
        obj: Any,
        *,
        indent: int | None = None,
        separators: tuple[str, str] | None = None,
        ensure_ascii: bool = True,
    ) -> str:
        """Serialize obj to JSON string using stdlib json.

        Args:
            obj: Python object to serialize.
            indent: Number of spaces for indentation.
            separators: (item_separator, key_separator) tuple.
            ensure_ascii: If True, escape non-ASCII characters.

        Returns:
            JSON string representation.
        """
        return json.dumps(
            obj,
            indent=indent,
            separators=separators,
            ensure_ascii=ensure_ascii,
        )

    def loads(self, s: str | bytes) -> Any:
        """Deserialize JSON string using stdlib json.

        Args:
            s: JSON string or bytes to deserialize.

        Returns:
            Deserialized Python object.
        """
        if isinstance(s, bytes):
            s = s.decode("utf-8")
        return json.loads(s)

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "stdlib"


__all__ = ["STDLIB_AVAILABLE", "StdlibProvider"]
