# Repository Guidelines

## Project Structure & Module Organization

- `src/audible/` contains the core client, authentication helpers, and service adapters; mirror this layout when adding new modules.
- `tests/` holds the pytest suite and fixtures—keep test files alongside the feature area they cover (e.g., `tests/test_client.py`).
- `docs/source/` is the Sphinx documentation root; rebuild it before publishing API changes.
- `examples/` provides runnable samples; prefer adding new walkthroughs here rather than in `src/`.
- `utils/` and `noxfile.py` bundle maintenance scripts and automation sessions referenced below.

## Build, Test, and Development Commands

- `uv sync` installs development dependencies declared in `pyproject.toml`.
- `uv run nox --list-sessions` shows available automation (tests, lint, docs, type checks).
- `uv run nox --session=tests` runs pytest under coverage; pass `-- tests/path::TestCase` to target a subset.
- `uv run nox --session=pre-commit` executes the lint/format pipeline (ruff, docstring checks, etc.).
- `uv run nox --session=docs-build` builds the Sphinx site into `docs/_build`.

## Crypto Providers & Optional Dependencies

- Install high-performance backends with `uv pip install audible[cryptography]`, `audible[pycryptodome]`, or both.
- Auto-detection order is `cryptography` → `pycryptodome` → legacy (pure Python).
- Prefer provider overrides via high-level APIs (e.g. `Authenticator.from_file(..., crypto_provider=CryptographyProvider)`); `get_crypto_providers()` is internal and should not be exposed in docs.
- For global overrides use `set_default_crypto_provider(...)` and reset with `set_default_crypto_provider()`.

## Coding Style & Naming Conventions

- Follow 4-space indentation, keep lines ≤88 characters, and include type hints; `pyproject.toml` enforces these via Ruff and mypy.
- Module and function names stay in `snake_case`, classes in `PascalCase`, and constants in `UPPER_SNAKE_CASE`.
- Document public APIs with Google-style docstrings so `ruff`’s pydocstyle checks pass.
- Run `uv run nox --session=pre-commit -- install` once to wire lint checks into your local Git hooks.

## Testing Guidelines

- Tests use pytest with coverage; replicate package structure under `tests/` and name files `test_*.py`.
- Aim to keep coverage at or near 100%; the current threshold is temporarily relaxed but upstream CI expects comprehensive tests.
- Use parametrized tests or fixtures instead of duplicating setup code, and prefer high-level interaction tests over implementation details.
- Combine coverage after parallel runs with `uv run nox --session=coverage` when you split execution across interpreters.

## Commit & Pull Request Guidelines

- Follow the Conventional Commit style seen in history (`fix(register): handle missing fields (#797)`); scope names should match module directories.
- Group related changes per commit, keep subject lines ≤72 characters, and include a concise body when context is non-trivial.
- **CRITICAL: Before every `git push`, run `uv run nox` to execute the full test suite.** This includes:
  - pre-commit (formatting, linting)
  - mypy (type checking)
  - tests (unit tests across Python 3.10-3.13)
  - typeguard (runtime type validation)
  - xdoctest (documentation examples)
  - docs-build (Sphinx documentation)
- **If `uv run nox` reports failures, you MUST NOT push without explicit confirmation from the repository maintainer.** Fix the failures first or seek approval.
- The only acceptable exception is the `safety` session (dependency vulnerability checks), which may fail due to external API issues.
- Pull requests should summarize intent, list validation steps, and call out testing gaps or follow-up tasks so reviewers can respond quickly.
