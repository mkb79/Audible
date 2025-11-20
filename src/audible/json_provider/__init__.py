"""JSON abstraction layer with support for multiple backends.

Note: This module is named 'json' (full path: audible.json) which shadows
the standard library 'json' module. This is intentional to provide a drop-in
replacement with automatic backend selection. Users import it as 'audible.json'
which avoids any actual shadowing in practice.

This module provides a clean abstraction layer for JSON operations,
supporting multiple backend libraries: orjson, ujson, python-rapidjson,
and stdlib json.

The provider is automatically selected at runtime based on availability:
1. orjson (preferred - Rust-accelerated, with smart fallback)
2. ujson (C-based, native indent=4 support)
3. rapidjson (C++, native indent=4 support)
4. stdlib (pure Python, always available)

Users can explicitly select a provider using the class-based API.

Example:
    >>> from audible.json_provider import get_json_provider
    >>> provider = get_json_provider()  # Auto-detect
    >>> data = {"name": "Audible", "version": "1.0"}
    >>> json_str = provider.dumps(data, indent=4)
    >>> provider.loads(json_str)
    {'name': 'Audible', 'version': '1.0'}

    >>> from audible.json_provider import OrjsonProvider  # doctest: +SKIP
    >>> provider = get_json_provider(OrjsonProvider)  # doctest: +SKIP
    >>> provider.provider_name  # doctest: +SKIP
    'orjson'
"""

from .exceptions import JSONDecodeError, JSONEncodeError
from .orjson_provider import OrjsonProvider
from .protocols import JSONProvider
from .rapidjson_provider import RapidjsonProvider
from .registry import get_json_provider, set_default_json_provider
from .stdlib_provider import StdlibProvider
from .ujson_provider import UjsonProvider


__all__ = [
    "JSONDecodeError",
    "JSONEncodeError",
    "JSONProvider",
    "OrjsonProvider",
    "RapidjsonProvider",
    "StdlibProvider",
    "UjsonProvider",
    "get_json_provider",
    "set_default_json_provider",
]
