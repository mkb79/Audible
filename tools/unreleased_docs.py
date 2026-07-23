"""Render, at documentation build time, what the next release would contain.

The changelog carries no Unreleased section on purpose -- the release machinery
generates one section per release, and prepare_release.py refuses to run while
an Unreleased section exists. That leaves a real gap for readers: someone
looking at the docs built from master cannot see what the next release will
contain.

This fills it with the same git-cliff configuration the release uses
(cliff.toml -- feat/fix/perf plus Changelog: footers). It only reads git; it
writes nothing to the repository and never touches CHANGELOG.md or the manifest,
so it cannot disturb a release. A Sphinx ``source-read`` handler in conf.py
injects the result into the changelog page in memory.

It degrades to an empty string on any failure -- a docs build must never break
because git-cliff is unavailable or the history is unexpected -- and shows
nothing on tagged (stable) or pull-request builds, which do not represent
master.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


# The heading git-cliff renders from cliff.toml, e.g. "## [0.13.0] - 2026-07-24".
_GENERATED_HEADING = re.compile(r"^## \[[^\]]+\][^\n]*", re.MULTILINE)

# Version types whose docs must not show master's pending changes: a tagged
# release represents a shipped version, and a pull request build represents the
# pull request, not master.
_SUPPRESSED_VERSION_TYPES = {"tag", "external", "unknown"}


def strip_v(tag: str) -> str:
    """Return a tag without its leading ``v``.

    Args:
        tag: A tag such as ``v0.13.0``.

    Returns:
        The version, ``0.13.0``.
    """
    return tag[1:] if tag.startswith("v") else tag


def to_unreleased(section: str, version: str) -> str:
    """Rewrite a generated release section into the pending block.

    Only the dated release heading changes; the group headings and entries are
    left exactly as git-cliff produced them, so the block reads like the
    released sections beside it.

    Args:
        section: git-cliff's unreleased section, heading included.
        version: The expected next version, without a leading ``v``.

    Returns:
        The section with its heading replaced by an Unreleased heading.
    """
    # A function replacement, not a string: a string would let a backslash in
    # version (there is none in a semver, but this is the boundary) be read as
    # a regex group reference.
    body = _GENERATED_HEADING.sub(
        lambda _: f"## Unreleased (expected {version})",
        section.strip("\n"),
        count=1,
    )
    return body.strip("\n") + "\n"


def _run(args: list[str], cwd: Path) -> str:
    """Run a command and return its stripped stdout.

    Args:
        args: Command and arguments.
        cwd: Working directory.

    Returns:
        Captured standard output, stripped.
    """
    result = subprocess.run(  # noqa: S603
        args, cwd=cwd, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def last_release_tag(repo_root: Path) -> str:
    """Return the newest release tag, or the empty string if there is none.

    Uses the same anchored form as cliff.toml's tag_pattern and the release
    workflow, so all three agree on what a release tag is.

    Args:
        repo_root: Repository root.

    Returns:
        The newest ``vX.Y.Z`` tag, or ``""``.
    """
    tags = _run(["git", "tag", "--list"], repo_root).splitlines()
    releases = sorted(
        (t for t in tags if re.fullmatch(r"v\d+\.\d+\.\d+", t)),
        key=lambda t: [int(n) for n in strip_v(t).split(".")],
    )
    return releases[-1] if releases else ""


def fragment(repo_root: Path) -> str:
    """Return the pending-changes Markdown for the current checkout.

    Args:
        repo_root: Repository root.

    Returns:
        A ``## Unreleased`` block, or the empty string when nothing is pending,
        the build is a tagged or pull-request build, or anything went wrong.
    """
    if os.environ.get("READTHEDOCS_VERSION_TYPE") in _SUPPRESSED_VERSION_TYPES:
        return ""

    try:
        last = last_release_tag(repo_root)
        if not last:
            return ""
        bumped = _run(["git-cliff", "--unreleased", "--bumped-version"], repo_root)
        if strip_v(bumped) == strip_v(last):
            return ""
        section = _run(["git-cliff", "--unreleased", "--tag", bumped], repo_root)
        # A thematic break sets the pending block off from the released
        # history that follows. It is part of the returned block, so it
        # appears only when there is a block -- never a rule floating above
        # nothing.
        return to_unreleased(section, strip_v(bumped)).rstrip("\n") + "\n\n---\n"
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        OSError,
        UnicodeDecodeError,
    ) as error:
        # UnicodeDecodeError is not an OSError: git output that is not valid
        # UTF-8 must degrade like any other failure, never break the build.
        print(f"unreleased_docs: showing nothing pending ({error})")
        return ""
