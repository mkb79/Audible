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
- ensure_ascii=True -> escapes orjson's output in place (no re-encode)
"""

from __future__ import annotations

import json
import logging
import re
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


_NON_ASCII_PATTERN = re.compile(r"[^\x00-\x7f]")


def _escape_match(match: re.Match[str]) -> str:
    r"""Render a single non-ASCII character as ``\uXXXX``.

    Args:
        match: Match holding exactly one non-ASCII character.

    Returns:
        The ``\uXXXX`` escape sequence, or a UTF-16 surrogate pair for
        characters beyond the BMP.
    """
    code = ord(match.group())
    if code <= 0xFFFF:
        return f"\\u{code:04x}"
    # Astral plane: emit a UTF-16 surrogate pair like stdlib json does.
    code -= 0x10000
    return f"\\u{0xD800 + (code >> 10):04x}\\u{0xDC00 + (code & 0x3FF):04x}"


def _escape_non_ascii(text: str) -> str:
    r"""Escape every non-ASCII character in a JSON document as ``\uXXXX``.

    All structural characters of a JSON document are ASCII, so any non-ASCII
    code point necessarily sits inside a string literal. Escaping them
    individually therefore yields an equivalent, ASCII-only document.

    Only the matched characters are substituted, so contiguous ASCII runs are
    copied as-is instead of being buffered one object per character.

    Args:
        text: A valid JSON document.

    Returns:
        The same document with non-ASCII characters replaced by ``\uXXXX``
        escape sequences, matching the stdlib json encoder.
    """
    return _NON_ASCII_PATTERN.sub(_escape_match, text)


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
            - ensure_ascii=True with non-ASCII output -> orjson's output is
              escaped in place (orjson has no ensure_ascii option and always
              emits raw UTF-8)
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
        except (TypeError, ValueError) as e:
            raise JSONEncodeError(f"Object not JSON serializable: {e}") from e

        text = result.decode("utf-8")

        # orjson has no `ensure_ascii` option and always emits raw UTF-8. Escape
        # the serialized output instead of re-encoding ``obj`` through another
        # backend: that preserves orjson's formatting as well as its wider type
        # support (dataclasses, datetime, non-finite floats), which a fallback
        # provider would either reject or serialize with different semantics.
        # Pure-ASCII output needs no escaping, so the fast path is untouched.
        if ensure_ascii and not text.isascii():
            logger.debug("orjson: escaping non-ASCII output for ensure_ascii=True")
            return _escape_non_ascii(text)

        return text

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
