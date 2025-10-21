# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Audible is a Python low-level interface library for communicating with the non-public Audible API. It supports both synchronous and asynchronous operations, allowing developers to build custom Audible services. The library handles authentication, device registration, and API requests to the Audible platform across multiple regions.

## Development Setup

This project uses `uv` for dependency management and `nox` for task automation.

### Initial Setup

```bash
uv sync
```

### Running Tests

Run full test suite:

```bash
uv run nox
```

Run only unit tests:

```bash
uv run nox --session=tests
```

Run tests for specific Python version:

```bash
uv run nox --session=tests-3.13
```

Run single test file or test:

```bash
uv run nox --session=tests -- tests/test_main.py
uv run pytest tests/test_main.py::test_specific_function
```

### Code Quality

Run pre-commit checks:

```bash
uv run nox --session=pre-commit
```

Install pre-commit hooks:

```bash
uv run nox --session=pre-commit -- install
```

Type checking with mypy:

```bash
uv run nox --session=mypy
```

Security check dependencies:

```bash
uv run nox --session=safety
```

Runtime type checking:

```bash
uv run nox --session=typeguard
```

### Documentation

Build documentation:

```bash
uv run nox --session=docs-build
```

Serve documentation with live reload:

```bash
uv run nox --session=docs
```

### Available Nox Sessions

List all available sessions:

```bash
uv run nox --list-sessions
```

Default sessions (run with `uv run nox`):

- pre-commit
- safety
- mypy
- tests
- typeguard
- xdoctest
- docs-build

## Architecture

### Core Components

**Authenticator (`auth.py`)**: Manages authentication lifecycle including login, device registration, token refresh, and credential storage. Supports encrypted file-based credential storage with AES encryption.

**Client (`client.py`)**: HTTP client wrapper providing both sync (`Client`) and async (`AsyncClient`) interfaces. Handles request/response lifecycle, error mapping, and automatic authentication. Uses httpx as the underlying HTTP library.

**Login (`login.py`)**: Implements OAuth2 authentication flow with Amazon/Audible. Handles CAPTCHA challenges, 2FA/OTP, and CVF (credential verification flows). Returns authorization codes used for device registration.

**Register (`register.py`)**: Performs device registration with Audible servers using authorization codes. Generates device credentials (access/refresh tokens, device info) needed for API access.

**Localization (`localization.py`)**: Defines region-specific configurations including country codes, domains, and marketplace IDs for supported Audible regions (US, UK, DE, FR, CA, IT, AU, IN, JP, ES).

### Authentication Flow

1. **Login**: User credentials → OAuth2 authorization → Authorization code
2. **Register**: Authorization code → Device registration → Tokens (access + refresh)
3. **API Access**: Access token → API requests (auto-refreshed when expired)
4. **Storage**: Credentials encrypted with AES and stored to file

### Client Architecture

The library provides two client types:

- `Client`: Synchronous HTTP client using httpx.Client
- `AsyncClient`: Asynchronous HTTP client using httpx.AsyncClient

Both clients:

- Accept an `Authenticator` instance
- Support context manager protocol
- Auto-refresh expired tokens
- Map HTTP errors to custom exceptions
- Support custom response callbacks

### API Request Pattern

Standard API request flow:

```python
client.get(path="library", params={...})
client.post(path="content/{asin}/licenserequest", body={...})
```

The client automatically:

- Constructs full URLs using the configured locale
- Adds authentication headers
- Handles token refresh if needed
- Converts responses to JSON or handles errors

### File Encryption

The library uses AES encryption for credential storage:

- Supports password-based encryption via `AESCipher`
- Detects encryption type from file headers
- Handles encrypted/unencrypted credential files

## Code Style

- **Type Hints**: Strict typing enforced via mypy
- **Docstrings**: Use Google-style docstrings for all functions, classes, and modules (enforced by ruff pydocstyle convention)
- **Line Length**: 88 characters (Black compatible)
- **Import Sorting**: isort with single-line imports, audible as first-party
- **Linting**: Ruff with comprehensive rule sets (see pyproject.toml)

## Testing Requirements

- 100% code coverage target (currently relaxed to 10% during refactoring)
- Tests located in `tests/` directory
- Use pytest framework
- Coverage tracking with `coverage.py`

## Python Version Support

Requires Python 3.10-3.13 (3.14 not yet supported per pyproject.toml)

## Key Dependencies

- **httpx**: HTTP client library (sync/async)
- **Pillow**: Image processing (CAPTCHA handling)
- **beautifulsoup4**: HTML parsing (login flows)
- **rsa**: RSA encryption (API authentication)
- **pyaes**: AES encryption (credential storage)
- **pbkdf2**: Key derivation (password-based encryption)
