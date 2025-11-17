"""JSON-specific exceptions for the audible library.

All JSON providers should raise these exceptions to ensure consistent
error handling throughout the codebase.
"""

from __future__ import annotations

import json


class JSONDecodeError(json.JSONDecodeError):
    """Exception raised when JSON decoding fails.

    This exception should be raised by all JSON providers when parsing
    invalid JSON data. It inherits from stdlib json.JSONDecodeError for
    backward compatibility.

    All provider implementations must wrap their library-specific decode
    exceptions in this exception type to ensure consistent error handling.

    Args:
        msg: Error message describing what went wrong.
        doc: The JSON document being parsed (default: empty string).
        pos: Position in document where error occurred (default: 0).

    Example:
        >>> from audible.json import JSONDecodeError
        >>> try:
        ...     raise JSONDecodeError("Invalid JSON syntax")
        ... except JSONDecodeError as e:
        ...     print(f"Caught: {type(e).__name__}")
        Caught: JSONDecodeError
    """

    def __init__(self, msg: str, doc: str = "", pos: int = 0) -> None:
        super().__init__(msg, doc, pos)


class JSONEncodeError(TypeError):
    """Exception raised when JSON encoding fails.

    This exception should be raised by all JSON providers when serializing
    objects that cannot be represented as JSON.

    All provider implementations must wrap their library-specific encode
    exceptions in this exception type to ensure consistent error handling.

    Args:
        msg: Error message describing what went wrong.

    Example:
        >>> from audible.json import JSONEncodeError
        >>> try:
        ...     raise JSONEncodeError("Object not serializable")
        ... except JSONEncodeError as e:
        ...     print(f"Caught: {type(e).__name__}")
        Caught: JSONEncodeError
    """

    def __init__(self, msg: str) -> None:
        super().__init__(msg)


__all__ = ["JSONDecodeError", "JSONEncodeError"]
