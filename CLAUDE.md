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
uv run nox --session=tests-3.14
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

Audit dependencies for known vulnerabilities:

```bash
uv run nox --session=audit
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
- audit
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

## Pre-Push Requirements

**CRITICAL: Before every `git push`, you MUST run the full test suite:**

```bash
uv run nox
```

This ensures all quality gates pass before code reaches the remote repository:

- ✅ **pre-commit**: Code formatting (ruff), linting, docstring validation (pydoclint)
- ✅ **mypy**: Type checking across Python 3.11-3.14
- ✅ **tests**: Unit tests with coverage across all supported Python versions
- ✅ **typeguard**: Runtime type validation
- ✅ **xdoctest**: Documentation example validation
- ✅ **docs-build**: Sphinx documentation builds without errors

### Failure Handling

**If `uv run nox` reports ANY failures:**

1. ❌ **DO NOT push** to the remote repository
2. 🔧 **Fix the failing tests** or code quality issues
3. ✅ **Re-run `uv run nox`** to verify fixes
4. 💬 **If you cannot fix the issue**, ask the repository maintainer for guidance before pushing

**Exception:** The `audit` session queries an external advisory service and may fail if that service is unavailable. A genuine finding must be fixed; a service outage does not block pushing.

Note that `audit` is not part of the `required` check. It runs in `security.yml`, which contributes its own `security` check.

### Why This Matters

- Prevents breaking changes from entering the repository
- Ensures consistent code quality across all contributors
- Catches issues early before CI/CD pipeline failures
- Maintains documentation accuracy (xdoctest validates all examples)

**This requirement applies to everyone working on the repository, including AI assistants like Claude.**

## Release Process

Releases are automated from Conventional Commit messages. The single manual step
is merging a release pull request; everything else follows from it.

### How a change becomes a release

1. **Merge a pull request to `master`.** The repository squash-merges only, and
   the **PR title becomes the commit subject** on `master`. `pr-title.yml`
   validates that title with `cz check` (commitizen) as a required check, so an
   unparseable title cannot merge. commitizen is used _only_ for this check.
2. **CI passes on `master`.** `release-pr.yml` then runs (via `workflow_run`)
   and asks **git-cliff** — using this repo's `cliff.toml` — what the next
   version and changelog section are. commitizen does **not** decide the
   version; git-cliff does, because it reads only the subject line, whereas
   commitizen scanned every body line and mis-released on quoted examples.
3. If there is something to release, a pull request titled
   `chore(release): vX.Y.Z` is opened/updated on branch `release/next`. Its diff
   is exactly the generated changelog section plus the version bump in
   `pyproject.toml`, `uv.lock`, and `.changelog-manifest.json`. **Edit the notes
   in that PR if they need sharpening** — editing stops auto-regeneration.
4. **Merge that release PR.** `release.yml` re-verifies the commit, builds
   reproducibly, smoke-tests wheel and sdist, tags `vX.Y.Z` (release GitHub App),
   publishes to PyPI (trusted publishing), and creates the GitHub release with
   the changelog section as its body. It is idempotent — a failed run can be
   retried by re-running the release commit's CI.

### Which commit types release

git-cliff (`cliff.toml`) releases on, and only on:

- `feat:` → **minor**
- `fix:`, `perf:` → **patch**
- a breaking change (`type!:` or a `BREAKING CHANGE:` footer) → **minor** while
  the version is `0.x` (`major_version_zero`), major after 1.0

Everything else — `refactor`, `docs`, `ci`, `build`, `chore`, `style`, `test`,
`revert` — is recorded in git but **does not release** and does not appear in
the changelog. "Valid commit" is not the same as "released": only the four
reader-facing types (feat/fix/perf, plus breaking) reach the changelog.

### The `Changelog:` footer override

A `Changelog:` footer on the **last line** of a commit message (i.e. the PR
description, since the body becomes the squash commit body) overrides the
type-based default in either direction:

- `Changelog: skip` — no changelog entry **and no release**, even for a `fix`.
  Use this for a deliberate, non-user-relevant edit (e.g. a routine dependency
  floor bump that does not warrant a release).
- `Changelog: added` / `changed` / `fixed` / `security` — force the entry into
  that section **and** release it, even for a `chore`/`docs`. Use `security` to
  surface a security fix that arrived as `chore(deps)`.

A breaking change cannot be skipped (`protect_breaking_commits`). What is skipped
releases nothing, so changelog visibility and release-worthiness are one
decision, made in the commit and reproducible from git alone.

### Dependency-update commit types (Renovate)

- `project.dependencies` / `project.optional-dependencies` (published install
  requirements) → `fix(deps)` → **releases**. A changed runtime floor is
  user-facing.
- `dependency-groups` (dev/docs/test tooling) → `chore(deps)` → no release.
- GitHub Actions and the pinned uv version → `ci(deps)`; the pinned build
  backend in `build-constraints.txt` → `build(deps)`. Neither releases.
- Renovate's default `rangeStrategy` does not widen `>=` floors, so routine
  updates touch only `uv.lock` (no release); only a security bump
  (`vulnerabilityAlerts` uses `rangeStrategy: 'bump'`) or a manual edit changes
  a floor. Both are user-facing and should release.

### The changelog is immutable once published

Every published section's SHA-256 is frozen in `.changelog-manifest.json`. CI
(`check_manifest_append_only.py`) fails a pull request that rewrites an existing
section's hash — a tripwire, not a lock (an admin can override for a deliberate
markup correction; see #885). New releases only ever prepend. Do not edit a
released section's wording.

### Other release facts

- **Docs preview:** the changelog page on Read the Docs (`latest`) shows an
  `## Unreleased (expected X.Y.Z)` block, generated at docs-build time by
  git-cliff from the commits since the last tag. It is suppressed on tagged and
  pull-request builds and never writes to the repo (`tools/unreleased_docs.py`).
- **Rehearsal:** `release.yml` via `workflow_dispatch` builds the current
  `master` as a `.dev` version and publishes it to **TestPyPI** only, touching
  no tags, PyPI, or releases.
- **The tracking issue for this whole system is #864.**

## Python Version Support

Requires Python 3.11-3.14 (per pyproject.toml: `>=3.11,<3.15`)

## Key Dependencies

- **httpx**: HTTP client library (sync/async)
- **Pillow**: Image processing (CAPTCHA handling)
- **beautifulsoup4**: HTML parsing (login flows)
- **rsa**: RSA encryption (legacy fallback)
- **pyaes**: AES encryption (legacy fallback)
- **pbkdf2**: Key derivation (legacy fallback)

**Optional (recommended for performance):**

- **cryptography**: Rust-accelerated crypto operations (preferred)
- **pycryptodome**: C-based crypto operations

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
