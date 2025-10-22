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

## Claude Code Integration

This repository is configured for use with [Claude Code](https://claude.ai/code), an AI-powered development assistant. The configuration enables Claude to assist with code reviews, pull request management, CI/CD monitoring, and repository analysis.

### Configuration File

The Claude Code configuration is stored in `.claude/settings.json` and defines permissions for GitHub CLI operations:

```json
{
  "permissions": {
    "allow": [...],  // Automatically permitted operations
    "ask": [...],    // Operations requiring user confirmation
    "deny": [...]    // Blocked operations
  }
}
```

### Prerequisites

Before using Claude Code with GitHub CLI integration:

1. **Install GitHub CLI**: Download and install from [cli.github.com](https://cli.github.com/)
2. **Authenticate**: Run `gh auth login` to authenticate with your GitHub account
3. **Verify Access**: Test with `gh repo view` to ensure proper authentication
4. **Claude Code**: Ensure you're running a recent version of Claude Code

### Rate Limits

GitHub CLI operations are subject to GitHub API rate limits:

- **Authenticated requests**: 5,000 requests per hour
- **Search API**: 30 requests per minute
- Rate limit status: Check with `gh api rate_limit`
- Most read operations count against your API quota

If you encounter rate limit errors, Claude Code will inform you and suggest waiting before retrying.

### Troubleshooting

**Common Issues:**

**`gh: command not found`**

- Install GitHub CLI from [cli.github.com](https://cli.github.com/)
- Verify installation: `gh --version`

**`gh: authentication required`**

- Run `gh auth login` and follow the prompts
- Verify authentication: `gh auth status`

**Permission denied errors**

- Check that your GitHub token has appropriate scopes
- Re-authenticate if necessary: `gh auth login --force`

**Claude Code not using settings**

- Verify settings file location: `.claude/settings.json`
- Check JSON syntax: `cat .claude/settings.json | jq .`
- Restart Claude Code session to reload settings

### Configured Permissions

#### Pull Request Operations

- **Read access (automatic)**:
  - `gh pr view` - View PR details and metadata
  - `gh pr list` - List all pull requests
  - `gh pr diff` - View code changes in PRs
  - `gh pr files` - **List modified files in PRs** (enables focused reviews and impact analysis)
  - `gh pr checks` - View CI/CD check status
  - `gh pr status` - View PR merge readiness
  - `gh pr reviews` - Read review comments and feedback
- **Write access (requires confirmation)**:
  - `gh pr create` - Create new pull requests
  - `gh pr comment` - Add comments to PRs

#### Issue Management

- **Read access**:
  - `gh issue view` - View issue details and discussions
  - `gh issue list` - List all issues with filtering options

#### CI/CD & Workflows

- **Read access**:
  - `gh run list` - List workflow runs with status
  - `gh run view` - View detailed workflow run logs and results
  - `gh workflow list` - List all workflows in the repository
  - `gh workflow view` - View workflow definitions and triggers
  - Enables Claude to analyze failed tests and CI/CD issues

#### Repository Information

- **Read access**:
  - `gh repo view` - View repository metadata and information
  - `gh release list` - List all releases and tags
  - `gh release view` - View release notes and assets
  - `gh search` - Search across repositories, code, issues, and PRs

#### API & Monitoring

- **Read access**:
  - `gh api rate_limit` - **Monitor GitHub API rate limits** (tracks remaining quota and prevents hitting limits during intensive operations)

### Security Model

The configuration follows the principle of least privilege:

- **Primarily read-only**: Most operations are for information gathering
- **Limited write access**: Only PR creation and commenting permitted
- **No destructive operations**: No force push, delete, merge, or branch manipulation
- **Auditable**: All GitHub CLI operations are logged in GitHub's audit trail

### Usage

Claude Code uses these permissions to:

1. **Automated Code Reviews**:

   - Analyze PRs and provide feedback
   - Use `gh pr files` to identify changed files for focused review
   - Check `gh pr checks` status to ensure tests pass
   - Read existing reviews with `gh pr reviews`

2. **CI/CD Monitoring**:

   - Check workflow status with `gh run view` and investigate failures
   - View workflow definitions with `gh workflow view`
   - Analyze test results and error logs

3. **Repository Analysis**:

   - Understand project structure and history
   - Browse releases with `gh release list`
   - Search codebase with `gh search`

4. **Issue Triage**:

   - Read and analyze issues for context
   - Identify patterns in bug reports
   - Understand feature requests

5. **Rate Limit Management**:
   - Monitor API usage with `gh api rate_limit`
   - Proactively prevent hitting GitHub API limits
   - Optimize operation frequency during intensive tasks

### Modifying Permissions

To adjust Claude Code permissions, edit `.claude/settings.json`:

1. **Choose permission level**:
   - `allow`: Operations run automatically without confirmation
   - `ask`: Operations require user confirmation before execution
   - `deny`: Operations are blocked entirely
2. **Add or remove entries** from the appropriate array
3. **Use glob patterns** for fine-grained control: `Bash(gh pr view:*)`
4. **Commit changes** to share with the team
5. **Restart Claude Code session** for changes to take effect

**Example:**

```json
{
  "permissions": {
    "allow": ["Bash(gh pr view:*)"], // Auto-approved
    "ask": ["Bash(gh pr create:*)"], // Requires confirmation
    "deny": ["Bash(gh repo delete:*)"] // Blocked
  }
}
```

For more information, see the [Claude Code documentation](https://docs.claude.com/en/docs/claude-code/settings).
