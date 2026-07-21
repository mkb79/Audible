"""Nox sessions."""

import os
import shlex
import shutil
import sys
from pathlib import Path
from textwrap import dedent

import nox
from nox_uv import session


nox.needs_version = ">= 2023.04.22"
nox.options.default_venv_backend = "uv"
nox.options.error_on_external_run = True
nox.options.sessions = (
    "pre-commit",
    "audit",
    "mypy",
    "tests",
    "typeguard",
    "xdoctest",
    "docs-build",
)

# uv refuses to create a virtualenv where one already exists, so a plain
# `nox` run fails for every session once `.nox/` has been populated by an
# earlier run. Clearing on create keeps repeated local runs working, while
# `nox -R` still reuses the existing environments. CI starts from an empty
# `.nox/`, where this is a no-op.
os.environ.setdefault("UV_VENV_CLEAR", "1")

PACKAGE = "audible"
PROJECT = nox.project.load_toml("pyproject.toml")
PYTHON_VERSIONS = nox.project.python_versions(PROJECT)
DEFAULT_PYTHON_VERSION = PYTHON_VERSIONS[-1]

# Group declaration
DEV_GROUP = "dev"
DOCS_GROUP = "docs"
MYPY_GROUP = "mypy"
PRE_COMMIT_GROUP = "pre-commit"
AUDIT_GROUP = "audit"
TESTS_GROUP = "tests"
COVERAGE_GROUP = TESTS_GROUP
TYPEGUARD_GROUP = "typeguard"
XDOCTEST_GROUP = "xdocs"
EXTRA_DEPS_GROUP = "extra-deps"


def activate_virtualenv_in_precommit_hooks(s: nox.Session) -> None:
    """Activate virtualenv in hooks installed by pre-commit.

    This function patches git hooks installed by pre-commit to activate the
    session's virtual environment. This allows pre-commit to locate hooks in
    that environment when invoked from git.

    Args:
        s: The Session object.
    """
    assert s.bin is not None  # noqa: S101

    # Only patch hooks containing a reference to this session's bindir. Support
    # quoting rules for Python and bash, but strip the outermost quotes so we
    # can detect paths within the bindir, like <bindir>/python.
    bindirs = [
        bindir[1:-1] if bindir[0] in "'\"" else bindir
        for bindir in (repr(s.bin), shlex.quote(s.bin))
    ]

    virtualenv = s.env.get("VIRTUAL_ENV")
    if virtualenv is None:
        return

    headers = {
        # pre-commit < 2.16.0
        "python": f"""\
            import os
            os.environ["VIRTUAL_ENV"] = {virtualenv!r}
            os.environ["PATH"] = os.pathsep.join((
                {s.bin!r},
                os.environ.get("PATH", ""),
            ))
            """,
        # pre-commit >= 2.16.0
        "bash": f"""\
            VIRTUAL_ENV={shlex.quote(virtualenv)}
            PATH={shlex.quote(s.bin)}"{os.pathsep}$PATH"
            """,
        # pre-commit >= 2.17.0 on Windows forces sh shebang
        "/bin/sh": f"""\
            VIRTUAL_ENV={shlex.quote(virtualenv)}
            PATH={shlex.quote(s.bin)}"{os.pathsep}$PATH"
            """,
    }

    hookdir = Path(".git") / "hooks"
    if not hookdir.is_dir():
        return

    for hook in hookdir.iterdir():
        if hook.name.endswith(".sample") or not hook.is_file():
            continue

        if not hook.read_bytes().startswith(b"#!"):
            continue

        text = hook.read_text()

        if not any(
            (Path("A") == Path("a") and bindir.lower() in text.lower())
            or bindir in text
            for bindir in bindirs
        ):
            continue

        lines = text.splitlines()

        for executable, header in headers.items():
            if executable in lines[0].lower():
                lines.insert(1, dedent(header))
                hook.write_text("\n".join(lines))
                break


@session(name="pre-commit", python=DEFAULT_PYTHON_VERSION, uv_groups=[PRE_COMMIT_GROUP])
def precommit(s: nox.Session) -> None:
    """Lint using pre-commit."""
    default_args = [
        "run",
        "--all-files",
        "--hook-stage=manual",
        "--show-diff-on-failure",
    ]
    args = s.posargs or default_args

    s.run("pre-commit", *args)
    if args and args[0] == "install":
        activate_virtualenv_in_precommit_hooks(s)


@session(python=DEFAULT_PYTHON_VERSION, uv_groups=[AUDIT_GROUP])
def audit(s: nox.Session) -> None:
    """Scan the locked dependencies for known vulnerabilities.

    Args:
        s: The Session object.
    """
    lock_dir = Path(s.virtualenv.location) / "audit"
    lock_dir.mkdir(exist_ok=True)

    # Export as pylock.toml rather than requirements.txt. A requirements export
    # keeps environment markers, and pip-audit evaluates those against the
    # running interpreter -- so a vulnerable pin guarded by
    # `python_full_version < '3.12'` is silently skipped on 3.14. Verified: a
    # marked `ujson==5.11.0` reports nothing on 3.14, while the same pin without
    # the marker reports five advisories. pip-audit reads pylock.toml as a whole
    # instead, covering every locked resolution and platform in one run,
    # including the Windows-only and older-Python entries.
    #
    # --all-groups and --all-extras matter: the optional backends (cryptography,
    # orjson, ujson, python-rapidjson, pycryptodome) are published extras that
    # users install, and the development groups are what this repository runs on.
    # --no-emit-project drops the editable self-reference, which is not a
    # dependency. --frozen keeps the export tied to the lock.
    s.run_always(
        "uv",
        "export",
        "--frozen",
        "--all-groups",
        "--all-extras",
        "--no-emit-project",
        "--format",
        "pylock.toml",
        "-o",
        str(lock_dir / "pylock.toml"),
    )
    # --strict fails if any package could not be audited, so a gap cannot pass
    # silently.
    #
    # If an advisory ever has no fixed release, add `--ignore-vuln <ID>` here
    # together with a comment stating why and when to revisit it, rather than
    # weakening the session as a whole.
    s.run(
        "pip-audit",
        "--locked",
        "--strict",
        str(lock_dir),
        *s.posargs,
    )


@session(
    python=PYTHON_VERSIONS,
    uv_groups=[MYPY_GROUP, TESTS_GROUP, EXTRA_DEPS_GROUP],
)
def mypy(s: nox.Session) -> None:
    """Type-check using mypy."""
    default_args = ["src/audible", "tests", "docs/source/conf.py"]
    args = s.posargs or default_args

    s.run("mypy", *args)
    if not s.posargs:
        s.run("mypy", f"--python-executable={sys.executable}", "noxfile.py")


@session(
    python=PYTHON_VERSIONS,
    uv_groups=[TESTS_GROUP, EXTRA_DEPS_GROUP],
)
def tests(s: nox.Session) -> None:
    """Run the test suite."""
    try:
        s.run(
            "coverage",
            "run",
            "--parallel",
            "-m",
            "pytest",
            *s.posargs,
        )
    finally:
        if s.interactive:
            s.notify("coverage", posargs=[])


@session(python=DEFAULT_PYTHON_VERSION, uv_groups=[COVERAGE_GROUP])
def coverage(s: nox.Session) -> None:
    """Produce the coverage report."""
    default_args = ["report"]
    args = s.posargs or default_args
    if not s.posargs and any(Path().glob(".coverage.*")):
        s.run("coverage", "combine")

    s.run("coverage", *args)


@session(
    python=DEFAULT_PYTHON_VERSION,
    uv_groups=[TYPEGUARD_GROUP, EXTRA_DEPS_GROUP],
)
def typeguard(s: nox.Session) -> None:
    """Runtime type checking using Typeguard."""
    s.run("pytest", f"--typeguard-packages={PACKAGE}", *s.posargs)


@session(
    python=PYTHON_VERSIONS,
    uv_groups=[XDOCTEST_GROUP, EXTRA_DEPS_GROUP],
)
def xdoctest(s: nox.Session) -> None:
    """Run examples with xdoctest."""
    if s.posargs:
        args = [PACKAGE, *s.posargs]
    else:
        args = [f"--modname={PACKAGE}", "--command=all"]
        if "FORCE_COLOR" in os.environ:
            args.append("--colored=1")

    s.run("python", "-m", "xdoctest", *args)


@session(name="docs-build", python=DEFAULT_PYTHON_VERSION, uv_groups=[DOCS_GROUP])
def docs_build(s: nox.Session) -> None:
    """Build the documentation."""
    # -W turns warnings into errors, matching `fail_on_warning` in
    # .readthedocs.yaml. Catching them here gives feedback on the pull request
    # instead of only when Read the Docs builds.
    default_args = ["-W", "docs/source", "docs/_build"]
    args = s.posargs or default_args

    if not s.posargs and "FORCE_COLOR" in os.environ:
        args.insert(0, "--color")

    build_dir = Path("docs", "_build")
    if build_dir.exists():
        shutil.rmtree(build_dir)

    s.run("sphinx-build", *args)


@session(python=DEFAULT_PYTHON_VERSION, uv_groups=[DOCS_GROUP])
def docs(s: nox.Session) -> None:
    """Build and serve the documentation with live reloading on file changes."""
    default_args = ["--open-browser", "docs/source", "docs/_build"]
    args = s.posargs or default_args

    build_dir = Path("docs", "_build")
    if build_dir.exists():
        shutil.rmtree(build_dir)

    s.run("sphinx-autobuild", *args)
