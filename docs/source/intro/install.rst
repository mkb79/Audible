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

For significantly improved performance, you can optionally install:

* **pycryptodome** - High-performance cryptographic operations using native C extensions

The library automatically detects and uses ``pycryptodome`` if available, otherwise
it falls back to pure-Python implementations (``pyaes``, ``rsa``, ``pbkdf2``).

Performance Improvements with pycryptodome
------------------------------------------

Installing ``pycryptodome`` provides:

* **5-10x faster** AES encryption/decryption
* **10-20x faster** RSA signing operations
* **3-5x faster** PBKDF2 key derivation
* **5-10x faster** SHA-256 and SHA-1 hashing

This is especially beneficial for applications that:

* Make many API requests (RSA signing on each request)
* Handle authentication frequently (PBKDF2 key derivation)
* Encrypt/decrypt large amounts of data

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

To install with the optional ``pycryptodome`` backend for better performance.

Using pip::

    pip install audible[crypto]

Using uv::

    uv pip install audible[crypto]

Or in a project context, run with extras::

    uv run --extra crypto your_script.py

Or add to existing installation::

    # Using pip
    pip install pycryptodome

    # Using uv
    uv pip install pycryptodome

Development Installation
------------------------

You can also use Git to clone the repository from GitHub to install the latest
development version::

    git clone https://github.com/mkb79/audible.git
    cd Audible
    pip install .

With optional dependencies::

    pip install .[crypto]

Using uv::

    uv pip install -e .[crypto]

Or when working in the project::

    uv sync --extra crypto

Alternatively, install it directly from the GitHub repository::

    pip install git+https://github.com/mkb79/audible.git

With optional dependencies::

    pip install "audible[crypto] @ git+https://github.com/mkb79/audible.git"
