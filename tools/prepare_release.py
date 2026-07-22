"""Insert a release section into the changelog and freeze it in the manifest.

Called by the release workflow after commitizen has determined the next version
and produced the section text. Kept out of the workflow so the part that edits
protected history can be tested rather than only observed in production.

Everything is validated in memory first. An earlier version wrote the changelog
and only then noticed a mismatched version, leaving the file dirty and the
manifest untouched -- a half-finished state in the middle of a release.

Usage::

    python tools/prepare_release.py <version> <fragment-file>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from changelog import (
    UNRELEASED,
    digest,
    prepend_section,
    split_sections,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
MANIFEST = REPO_ROOT / ".changelog-manifest.json"


def _as_tuple(version: str) -> tuple[int, ...]:
    """Return a comparable form of a plain version.

    Args:
        version: A version such as ``0.12.0``.

    Returns:
        Its numeric components.

    Raises:
        ValueError: If the version is not three plain numbers.
    """
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(
            f"{version!r} is not a plain three-part version; this path does "
            "not handle prereleases"
        )
    return tuple(int(p) for p in parts)


def validate(
    version: str, fragment: str, changelog: str, manifest: list[dict[str, str]]
) -> None:
    """Check every precondition before anything is written.

    Args:
        version: Version about to be released.
        fragment: The section text produced by commitizen.
        changelog: Current contents of the changelog.
        manifest: Recorded entries.

    Raises:
        ValueError: If the release must not be prepared.
    """
    target = _as_tuple(version)

    sections = split_sections(fragment)
    if len(sections) != 1:
        raise ValueError(
            f"the fragment must contain exactly one section, found {len(sections)}"
        )
    # The version is passed separately from the fragment, so they can disagree.
    # Catching that here rather than after writing keeps the tree clean.
    fragment_version = sections[0][0]
    if fragment_version != version:
        raise ValueError(
            f"the fragment is for {fragment_version}, but {version} was requested"
        )

    existing = [v for v, _ in split_sections(changelog)]
    if version in existing:
        raise ValueError(
            f"the changelog already contains a section for {version}; "
            "a released version is never written twice"
        )
    if any(entry["version"] == version for entry in manifest):
        raise ValueError(f"the manifest already records {version}")

    released = [v for v in existing if v != UNRELEASED]
    for previous in released:
        try:
            if _as_tuple(previous) >= target:
                raise ValueError(
                    f"{version} is not newer than {previous}, which the "
                    "changelog already contains"
                )
        except ValueError as error:
            if "not a plain three-part version" not in str(error):
                raise
            # Historic sections predate this scheme; they cannot be compared
            # and are not a reason to refuse a release.


def prepare(
    version: str,
    fragment: str,
    changelog_path: Path = CHANGELOG,
    manifest_path: Path = MANIFEST,
) -> str:
    """Insert the section and record its hash.

    Args:
        version: Version being released.
        fragment: The section text produced by commitizen.
        changelog_path: Location of the changelog.
        manifest_path: Location of the manifest.

    Returns:
        A short report of what was written.

    Raises:
        ValueError: If a precondition fails, or the result does not match what
            was intended. Nothing is written in either case.
    """
    changelog = changelog_path.read_text(encoding="utf-8")
    payload: dict[str, list[dict[str, str]]] = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    manifest = payload["sections"]

    validate(version, fragment, changelog, manifest)

    updated = prepend_section(changelog, fragment)

    # Verify the intended outcome on the in-memory result, before either file is
    # touched. Hashing the fragment instead would freeze text that differs from
    # the file by whitespace, and the mismatch would only surface later.
    written = dict(split_sections(updated)).get(version)
    if written is None:
        raise ValueError(
            f"the section for {version} is not present after insertion; "
            "its heading is probably not in a recognised format"
        )
    before = dict(split_sections(changelog))
    after = dict(split_sections(updated))
    for existing_version, section in before.items():
        if after.get(existing_version) != section:
            raise ValueError(
                f"the section for {existing_version} changed while inserting "
                f"{version}; refusing to write"
            )

    payload["sections"] = [*manifest, {"version": version, "sha256": digest(written)}]

    changelog_path.write_text(updated, encoding="utf-8")
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return (
        f"Inserted {version} and recorded its hash "
        f"({len(payload['sections'])} entries)."
    )


def main(argv: list[str]) -> int:
    """Run the preparation.

    Args:
        argv: Version and path to the fragment file.

    Returns:
        Process exit code.
    """
    if len(argv) != 2:
        print(f"usage: {sys.argv[0]} <version> <fragment-file>", file=sys.stderr)
        return 2

    version, fragment_path = argv
    try:
        print(prepare(version, Path(fragment_path).read_text(encoding="utf-8")))
    except ValueError as error:
        print(f"Refusing to prepare the release: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
