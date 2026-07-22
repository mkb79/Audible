"""Verify that the changelog manifest only ever grows.

``tests/test_changelog_integrity.py`` checks the manifest against the changelog.
Both files live in the repository, so a change that rewrites a published section
*and* recomputes its hash is internally consistent and passes that test. The
comparison has no reference outside the change under review.

This script supplies one: the manifest as it exists on the base branch. A pull
request cannot alter that, so entries recorded there must reappear unchanged and
in the same order. Only appending is allowed.

Usage::

    python tools/check_manifest_append_only.py <base-ref>

Limits worth stating. This closes the accidental rewrite and the same-pull-request
rehash. It does not stop someone who edits this script in the same change, and it
cannot bind a repository administrator at all. Guarding against those needs a
check running from content the pull request does not control -- a required
workflow held elsewhere -- or signed attestations.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


MANIFEST = ".changelog-manifest.json"


def load_from_ref(ref: str, path: str) -> list[dict[str, str]] | None:
    """Read the manifest as it exists at a git revision.

    Args:
        ref: Git revision to read from.
        path: Repository-relative path of the manifest.

    Returns:
        The recorded entries, or None if the file does not exist there.
    """
    result = subprocess.run(  # noqa: S603
        ["git", "show", f"{ref}:{path}"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    data: dict[str, list[dict[str, str]]] = json.loads(result.stdout)
    return data["sections"]


def load_current(path: str) -> list[dict[str, str]]:
    """Read the manifest from the working tree.

    Args:
        path: Repository-relative path of the manifest.

    Returns:
        The recorded entries.
    """
    data: dict[str, list[dict[str, str]]] = json.loads(
        Path(path).read_text(encoding="utf-8")
    )
    return data["sections"]


def compare(base: list[dict[str, str]], current: list[dict[str, str]]) -> list[str]:
    """Report every way the manifest failed to grow append-only.

    Args:
        base: Entries recorded on the base branch.
        current: Entries in the proposed change.

    Returns:
        Human-readable problems; empty when the manifest only grew.
    """
    problems = []

    if len(current) < len(base):
        problems.append(
            f"the manifest lost entries: {len(base)} on the base branch, "
            f"{len(current)} here"
        )

    for index, recorded in enumerate(base):
        if index >= len(current):
            problems.append(f"entry {index + 1} ({recorded['version']}) is missing")
            continue
        proposed = current[index]
        if proposed["version"] != recorded["version"]:
            problems.append(
                f"entry {index + 1} changed from {recorded['version']} to "
                f"{proposed['version']}; existing entries must keep their order"
            )
        elif proposed["sha256"] != recorded["sha256"]:
            problems.append(
                f"the hash recorded for {recorded['version']} was rewritten; "
                "a published section cannot be re-frozen with new wording"
            )

    return problems


def main(argv: list[str]) -> int:
    """Compare the manifest against the base branch.

    Args:
        argv: Command line arguments; the first is the base revision.

    Returns:
        Process exit code.
    """
    if len(argv) != 1:
        print(f"usage: {sys.argv[0]} <base-ref>", file=sys.stderr)
        return 2

    base_ref = argv[0]
    base = load_from_ref(base_ref, MANIFEST)
    if base is None:
        print(f"No manifest on {base_ref}; nothing to compare against.")
        return 0

    problems = compare(base, load_current(MANIFEST))
    if problems:
        print("The changelog manifest is not append-only:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(
            "\nEntries for published versions are frozen. Add a new entry; "
            "never edit or reorder an existing one.",
            file=sys.stderr,
        )
        return 1

    added = len(load_current(MANIFEST)) - len(base)
    print(f"Manifest is append-only ({len(base)} kept, {added} added).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
