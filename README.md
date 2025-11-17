# Audible

[![image](https://img.shields.io/pypi/v/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/l/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/pyversions/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/status/audible.svg)](https://pypi.org/project/audible/)
[![image](https://img.shields.io/pypi/wheel/audible.svg)](https://pypi.org/project/audible/)
[![Travis](https://img.shields.io/travis/mkb79/audible/master.svg?logo=travis)](https://travis-ci.org/mkb79/audible)
[![CodeFactor](https://www.codefactor.io/repository/github/mkb79/audible/badge)](https://www.codefactor.io/repository/github/mkb79/audible)
[![image](https://img.shields.io/pypi/dm/audible.svg)](https://pypi.org/project/audible/)

**Audible is a Python low-level interface to communicate with the non-publicly
[Audible](<https://en.wikipedia.org/wiki/Audible_(service)>) API.**

It enables Python developers to create their own Audible services.
Asynchronous communication with the Audible API is supported.

For a basic command line interface take a look at my
[audible-cli](https://github.com/mkb79/audible-cli) package. This package
supports:

- downloading audiobooks (aax/aaxc), cover, PDF and chapter files
- export library to [csv](https://en.wikipedia.org/wiki/Comma-separated_values)
  files
- get activation bytes
- add own plugin commands

## Requirements

Python >= 3.10

## Installation

### Standard Installation

```bash
pip install audible
```

### Recommended: With Performance Optimizations

**Available in audible >= 0.11.0**

For significantly better performance (5-100x faster cryptographic operations),
install with optional high-performance crypto backends.

**Option 1: cryptography (recommended)**

Modern, actively maintained, Rust-accelerated library:

```bash
pip install audible[cryptography]
```

**Option 2: pycryptodome**

Mature, C-based cryptographic library:

```bash
pip install audible[pycryptodome]
```

**Option 3: Both (best for development/testing)**

```bash
pip install audible[cryptography,pycryptodome]
```

**Using uv:**

```bash
# With cryptography
uv pip install audible[cryptography]

# With pycryptodome
uv pip install audible[pycryptodome]

# With both
uv pip install audible[cryptography,pycryptodome]

# Or run with extras (in project context)
uv run --extra cryptography your_script.py
```

The library automatically selects the best available provider:

1. cryptography (preferred, Rust-accelerated)
2. pycryptodome (C-based)
3. legacy (pure Python fallback)

Performance improvements with optimized backends:

- **5-10x faster** AES encryption/decryption
- **10-20x faster** RSA operations
- **3-5x faster** key derivation (PBKDF2)
- **5-10x faster** hashing (SHA-256, SHA-1)

**Provider Overrides (advanced)**

Most applications do not need to interact with the crypto layer directly.
Prefer configuring providers through high-level APIs such as `Authenticator`:

```python
from audible import Authenticator
from audible.crypto_provider import CryptographyProvider, set_default_crypto_provider

# Force a specific provider for this authenticator instance
auth = Authenticator.from_file(
    "auth.json",
    password="secret",
    crypto_provider=CryptographyProvider,
)

# Optional: set a process-wide default provider, then reset to auto-detect
set_default_crypto_provider(CryptographyProvider)
...
set_default_crypto_provider()
```

`get_crypto_providers()` remains available for internal use, but it is not part of
the supported public API.

### Optional: High-Performance JSON Backends

**Available in audible >= 0.11.0**

For improved JSON serialization/deserialization performance (2-5x faster),
install with optional high-performance JSON backends.

**Option 1: json-full (recommended)**

Complete coverage with best performance for all use cases:

```bash
pip install audible[json-full]
```

Includes:

- `orjson`: 4-5x faster for compact JSON (API responses, metadata)
- `ujson`: 2-3x faster with indent=4 support (auth files, library exports)

**Option 2: json-fast**

Optimized for compact JSON only:

```bash
pip install audible[json-fast]
```

Includes:

- `orjson`: 4-5x faster for compact JSON

**Option 3: Individual providers**

```bash
# orjson (Rust-based, fastest for compact JSON)
pip install audible[orjson]

# ujson (C-based, excellent for pretty-printed output)
pip install audible[ujson]

# rapidjson (C++ based, alternative to ujson)
pip install audible[rapidjson]
```

**Using uv:**

```bash
# json-full (recommended)
uv pip install audible[json-full]

# json-fast
uv pip install audible[json-fast]

# Or run with extras (in project context)
uv run --extra json-full your_script.py
```

The library automatically selects the best available provider:

1. orjson (Rust-based, 4-5x faster for compact JSON)
2. ujson (C-based, 2-3x faster with indent support)
3. rapidjson (C++ based, 2-3x faster)
4. stdlib json (always available)

Performance improvements with optimized backends:

- **4-5x faster** compact JSON (orjson)
- **2-3x faster** pretty-printed JSON (ujson/rapidjson)
- **Smart fallback**: orjson automatically uses ujson/rapidjson for indent=4

**Provider Overrides (advanced)**

Most applications do not need to interact with the JSON layer directly.
The library automatically uses the best provider. However, you can override:

```python
from audible.json_provider import OrjsonProvider, get_json_provider, set_default_json_provider

# Get auto-detected provider
provider = get_json_provider()
print(f"Using: {provider.provider_name}")

# Force a specific provider
data = {"key": "value"}
orjson = get_json_provider(OrjsonProvider)
json_str = orjson.dumps(data)

# Optional: set a process-wide default provider
set_default_json_provider(OrjsonProvider)
```

## Read the Doc

The documentation can be found at [Read the Docs](https://audible.readthedocs.io/en/latest)

## Contributing

Contributions are very welcome.
To learn more, see the [Contributor Guide].

## License

Distributed under the terms of the [AGPL-3.0][license],
_Audible_ is free and open source software.

## Issues

If you encounter any problems,
please [file an issue] along with a detailed description.

## Credits

Thanks a lot JetBrains for supporting me with a free [license](https://www.jetbrains.com/community/opensource/#support)
This project was generated from [@cjolowicz]'s [Hypermodern Python Cookiecutter] template.

[@cjolowicz]: https://github.com/cjolowicz
[pypi]: https://pypi.org/
[hypermodern python cookiecutter]: https://github.com/cjolowicz/cookiecutter-hypermodern-python
[file an issue]: https://github.com/mkb79/Audible/issues
[pip]: https://pip.pypa.io/
[audible]: https://github.com/mkb79/Audible
[pipx]: https://pypa.github.io/pipx/

<!-- github-only -->

[license]: https://github.com/mkb79/Audible/blob/main/LICENSE
[contributor guide]: https://github.com/mkb79/Audible/blob/main/CONTRIBUTING.md
