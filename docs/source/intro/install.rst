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

Install with optional extras to enable high-performance crypto providers.

Using pip (choose one or both extras)::

    # cryptography (recommended)
    pip install audible[cryptography]

    # pycryptodome
    pip install audible[pycryptodome]

    # both
    pip install audible[cryptography,pycryptodome]

Using uv::

    uv pip install audible[cryptography]
    uv pip install audible[pycryptodome]
    uv pip install audible[cryptography,pycryptodome]

Or run with extras inside the project::

    uv run --extra cryptography your_script.py

Provider Overrides (advanced)
-----------------------------

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
    pip install .[cryptography,pycryptodome]

Using uv::

    uv pip install -e .[cryptography,pycryptodome]

Or when working in the project::

    uv sync --extra cryptography --extra pycryptodome

Alternatively, install it directly from the GitHub repository::

    pip install git+https://github.com/mkb79/audible.git

With optional dependencies::

    pip install "audible[cryptography] @ git+https://github.com/mkb79/audible.git"
    pip install "audible[pycryptodome] @ git+https://github.com/mkb79/audible.git"
