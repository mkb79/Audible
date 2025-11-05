"""JSON abstraction layer with support for multiple backends.

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
    >>> from audible.json import get_json_provider
    >>> provider = get_json_provider()  # Auto-detect
    >>> data = {"name": "Audible", "version": "1.0"}
    >>> json_str = provider.dumps(data, indent=4)
    >>> provider.loads(json_str)
    {'name': 'Audible', 'version': '1.0'}

    >>> from audible.json import OrjsonProvider  # doctest: +SKIP
    >>> provider = get_json_provider(OrjsonProvider)  # doctest: +SKIP
    >>> provider.provider_name  # doctest: +SKIP
    'orjson'
"""

from .orjson_provider import OrjsonProvider
from .protocols import JSONProvider
from .rapidjson_provider import RapidjsonProvider
from .registry import get_json_provider, set_default_json_provider
from .stdlib_provider import StdlibProvider
from .ujson_provider import UjsonProvider


__all__ = [
    "JSONProvider",
    "OrjsonProvider",
    "RapidjsonProvider",
    "StdlibProvider",
    "UjsonProvider",
    "get_json_provider",
    "set_default_json_provider",
]
