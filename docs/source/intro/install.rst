==================
Installation Guide
==================

Requirements / Dependencies
===========================

Audible needs at least *Python 3.10*.

It depends on the following packages:

* beautifulsoup4
* httpx
* pbkdf2
* Pillow
* pyaes
* rsa

Optional Dependencies
=====================

**Available in audible >= 0.11.0**

For significantly improved performance, you can optionally install
high-performance cryptographic backends:

* **cryptography** - Modern, Rust-accelerated library (recommended)
* **pycryptodome** - Mature, C-based cryptographic library

The library automatically selects the best available provider:

1. ``cryptography`` (preferred, Rust-accelerated)
2. ``pycryptodome`` (C-based)
3. ``legacy`` fallback (pure Python: ``pyaes``, ``rsa``, ``pbkdf2``)

Performance improvements with optimized backends:

* **5-10x faster** AES encryption/decryption
* **10-20x faster** RSA signing operations
* **3-5x faster** PBKDF2 key derivation
* **5-10x faster** SHA-256 and SHA-1 hashing

These benefits are most noticeable when you:

* Make frequent API requests (RSA signing on each request)
* Handle authentication workflows often (PBKDF2 key derivation)
* Encrypt or decrypt larger payloads

For significantly improved JSON serialization performance, you can optionally
install high-performance JSON backends:

* **orjson** - Rust-based library (recommended for compact JSON)
* **ujson** - C-based library (supports pretty-printing with indent=4)
* **rapidjson** - C++ based library

The library automatically selects the best available provider:

1. ``orjson`` (preferred for compact JSON, Rust-based)
2. ``ujson`` (C-based, supports indent=4)
3. ``rapidjson`` (C++ based)
4. ``json`` (standard library fallback)

Performance improvements with optimized JSON backends:

* **4-5x faster** compact JSON serialization (orjson)
* **2-3x faster** pretty-printed JSON with indent=4 (ujson/rapidjson)
* Smart fallback: orjson automatically uses ujson/rapidjson for indent=4

These benefits are most noticeable when you:

* Load/save encrypted authentication credentials frequently
* Parse large API responses
* Work with JSON-heavy authentication flows

Installation
============

Standard Installation
---------------------

The easiest way to install the latest version from PyPI is by using pip::

    pip install audible

Using uv (faster alternative to pip)::

    uv pip install audible

Recommended: With Performance Optimizations
--------------------------------------------

**Available in audible >= 0.11.0**

Install with optional extras to enable high-performance crypto and JSON providers.

Using pip (choose one or more extras)::

    # Crypto providers
    pip install audible[cryptography]          # Rust-accelerated crypto (recommended)
    pip install audible[pycryptodome]          # C-based crypto

    # JSON providers
    pip install audible[json-full]             # Complete JSON coverage: orjson + ujson (recommended)
    pip install audible[json-fast]             # Fast compact JSON only: orjson
    pip install audible[orjson]                # Just orjson
    pip install audible[ujson]                 # Just ujson
    pip install audible[rapidjson]             # Just rapidjson

    # Combined (recommended for best performance)
    pip install audible[cryptography,json-full]

    # All performance optimizations
    pip install audible[cryptography,pycryptodome,json-full]

Using uv::

    uv pip install audible[cryptography,json-full]
    uv pip install audible[cryptography,pycryptodome,json-full]

Or run with extras inside the project::

    uv run --extra cryptography --extra json-full your_script.py

Provider Overrides (advanced)
-----------------------------

**Crypto Providers**

Most use cases do not need direct access to the crypto registry. Prefer wiring
providers through high-level APIs such as ``Authenticator``::

    from audible import Authenticator
    from audible.crypto import CryptographyProvider, set_default_crypto_provider

    auth = Authenticator.from_file(
        "auth.json",
        password="secret",
        crypto_provider=CryptographyProvider,
    )

    # Optional: set and later reset a process-wide default provider
    set_default_crypto_provider(CryptographyProvider)
    ...
    set_default_crypto_provider()

``get_crypto_providers()`` is considered an internal helper and is not intended
for general external use.

**JSON Providers**

The library automatically selects the best available JSON provider. For explicit
control, use ``set_default_json_provider()``::

    from audible.json import set_default_json_provider

    # Use orjson explicitly (if installed)
    set_default_json_provider("orjson")

    # Use ujson explicitly (if installed)
    set_default_json_provider("ujson")

    # Reset to auto-detection
    set_default_json_provider()

The JSON provider system is fully automatic. Explicit configuration is rarely
needed and mainly useful for testing or performance tuning specific use cases.

Development Installation
------------------------

You can also use Git to clone the repository from GitHub to install the latest
development version::

    git clone https://github.com/mkb79/audible.git
    cd Audible
    pip install .

With optional dependencies::

    pip install .[cryptography]
    pip install .[pycryptodome]
    pip install .[json-full]
    pip install .[cryptography,pycryptodome,json-full]

Using uv::

    uv pip install -e .[cryptography,pycryptodome,json-full]

Or when working in the project::

    uv sync --extra cryptography --extra pycryptodome --extra json-full

Alternatively, install it directly from the GitHub repository::

    pip install git+https://github.com/mkb79/audible.git

With optional dependencies::

    pip install "audible[cryptography,json-full] @ git+https://github.com/mkb79/audible.git"
    pip install "audible[cryptography,pycryptodome,json-full] @ git+https://github.com/mkb79/audible.git"
