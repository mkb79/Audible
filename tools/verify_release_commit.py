"""Verify that a commit is a coherent release of one exact version.

Run by the publish workflow before anything irreversible. The release pull
request already assembled these files, but assembling and publishing are
separated by a merge and by time -- this re-derives every claim from the
checkout instead of trusting that nothing happened in between.

Checks, all of which must hold:

* the version is a plain three-part release version
* pyproject.toml carries exactly that version
* uv.lock agrees with pyproject.toml about it
* the changelog's first section is that version, present exactly once
* every manifest entry matches its changelog section byte for byte
* the newest manifest entry is that version, and its hash matches the file

Usage::

    python tools/verify_release_commit.py <version>
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

from changelog import digest, load_manifest, split_sections


REPO_ROOT = Path(__file__).resolve().parent.parent

RELEASE_VERSION = re.compile(r"^\d+\.\d+\.\d+$")


def problems_for(
    version: str,
    pyproject_version: str,
    lock_version: str,
    changelog: str,
    manifest: list[dict[str, str]],
) -> list[str]:
    """Return every way this state fails to be a release of the version.

    Args:
        version: The version being released.
        pyproject_version: Version found in pyproject.toml.
        lock_version: Version uv.lock records for this package.
        changelog: Full contents of the changelog.
        manifest: Recorded section hashes.

    Returns:
        Human-readable problems; empty when everything holds.
    """
    problems = []

    if not RELEASE_VERSION.match(version):
        # Everything downstream assumes a plain release version; a prerelease
        # slipping in here means the workflow's own detection is broken.
        return [f"{version!r} is not a plain three-part release version"]

    if pyproject_version != version:
        problems.append(f"pyproject.toml carries {pyproject_version}, not {version}")
    if lock_version != version:
        problems.append(f"uv.lock records {lock_version}, not {version}")

    sections = split_sections(changelog)
    matches = [text for found, text in sections if found == version]
    if not sections:
        problems.append("the changelog has no sections at all")
    elif len(matches) != 1:
        problems.append(
            f"the changelog contains {len(matches)} sections for {version}; "
            "exactly one is required"
        )
    elif sections[0][0] != version:
        problems.append(
            f"the newest changelog section is {sections[0][0]}, not {version}"
        )

    by_version = dict(sections)
    for entry in manifest:
        text = by_version.get(entry["version"])
        if text is None:
            problems.append(
                f"the manifest records {entry['version']}, which the "
                "changelog no longer contains"
            )
        elif digest(text) != entry["sha256"]:
            problems.append(
                f"the section for {entry['version']} does not match the hash "
                "recorded for it"
            )

    if not manifest:
        problems.append("the manifest is empty")
    elif manifest[-1]["version"] != version:
        problems.append(
            f"the newest manifest entry is {manifest[-1]['version']}, not "
            f"{version}; the release pull request should have appended it"
        )

    return problems


def lock_version_of(lock_text: str) -> str:
    """Return the version uv.lock records for this package.

    Args:
        lock_text: Full contents of uv.lock.

    Returns:
        The recorded version, or ``"<absent>"`` if the package is missing.
    """
    lock = tomllib.loads(lock_text)
    for package in lock.get("package", []):
        if package.get("name") == "audible":
            return str(package.get("version", "<absent>"))
    return "<absent>"


def main(argv: list[str]) -> int:
    """Verify the working tree as a release of the given version.

    Args:
        argv: The version.

    Returns:
        Process exit code.
    """
    if len(argv) != 1:
        print(f"usage: {sys.argv[0]} <version>", file=sys.stderr)
        return 2
    version = argv[0]

    pyproject = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    problems = problems_for(
        version,
        pyproject_version=str(pyproject["project"]["version"]),
        lock_version=lock_version_of(
            (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
        ),
        changelog=(REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
        manifest=load_manifest(REPO_ROOT / ".changelog-manifest.json"),
    )

    if problems:
        print(f"This checkout is not a coherent release of {version}:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(
        f"Coherent release of {version}: pyproject, lock, changelog and manifest agree."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
