"""Guards the wording of already published changelog entries.

Released sections must never change. Once a version is on PyPI and its notes
are on the releases page, editing the corresponding changelog text rewrites
history that users have already read.

`.changelog-manifest.json` records a hash per published section. This test
recomputes them, so any edit to a released section fails the pull request
instead of being noticed later, or not at all. The release tooling appends a
new entry when it publishes; nothing removes or rewrites existing ones.
"""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
MANIFEST = REPO_ROOT / ".changelog-manifest.json"

# Two heading styles have to be recognised. Sections written before releases
# were generated look like "## [0.11.0] - 2026-07-20", and "## [Unreleased]"
# uses the same bracketed form. Generated sections look like
# "## v0.12.0 (2026-07-22)".
#
# Matching only the bracketed form would make every future section invisible to
# this test: it would not appear as published, so nothing would report it as
# unprotected either. The gap would be silent.
#
# Neither alternative matches "## Bugfix", which older sections contain as a
# subheading at the same level and which is content, not a boundary.
SECTION_HEADING = re.compile(
    r"^## (?:\[(?P<bracketed>[^\]]+)\]|v(?P<generated>\d+\.\d+\.\d+))",
    re.MULTILINE,
)


def _version_of(match: re.Match[str]) -> str:
    """Return the version a section heading refers to.

    Args:
        match: A match of :data:`SECTION_HEADING`.

    Returns:
        The version string, without the leading ``v`` of generated headings.
    """
    return match.group("bracketed") or match.group("generated")


UNRELEASED = "Unreleased"


def split_sections(text: str) -> list[tuple[str, str]]:
    """Split a changelog into its sections.

    Returns a list rather than a mapping on purpose. A mapping would silently
    collapse two sections carrying the same version, which is exactly the state
    a botched release would leave behind, and it would hide it from every check
    built on top.

    Args:
        text: Full contents of the changelog.

    Returns:
        Pairs of version and the exact text of its section, heading included,
        in the order they appear.
    """
    marks = [(m.start(), _version_of(m)) for m in SECTION_HEADING.finditer(text)]
    sections = []
    for index, (start, version) in enumerate(marks):
        end = marks[index + 1][0] if index + 1 < len(marks) else len(text)
        sections.append((version, text[start:end]))
    return sections


def digest(section: str) -> str:
    """Return the hash recorded for a section.

    Args:
        section: Exact text of one changelog section.

    Returns:
        Hex-encoded SHA-256 of the section's UTF-8 bytes.
    """
    return hashlib.sha256(section.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def section_list() -> list[tuple[str, str]]:
    """Changelog sections in the order they appear.

    Returns:
        Pairs of version and section text.
    """
    return split_sections(CHANGELOG.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest_entries() -> list[dict[str, str]]:
    """Recorded manifest entries in file order.

    Returns:
        The raw entries, so duplicates stay visible.
    """
    data: dict[str, list[dict[str, str]]] = json.loads(
        MANIFEST.read_text(encoding="utf-8")
    )
    return data["sections"]


@pytest.fixture(scope="module")
def sections(section_list: list[tuple[str, str]]) -> dict[str, str]:
    """Changelog sections by version.

    Args:
        section_list: Sections in file order.

    Returns:
        Mapping of version to section text.
    """
    return dict(section_list)


@pytest.fixture(scope="module")
def manifest(manifest_entries: list[dict[str, str]]) -> dict[str, str]:
    """Recorded hashes by version.

    Args:
        manifest_entries: Raw manifest entries.

    Returns:
        Mapping of version to expected hash.
    """
    return {entry["version"]: entry["sha256"] for entry in manifest_entries}


def test_no_duplicate_changelog_sections(
    section_list: list[tuple[str, str]],
) -> None:
    """Two sections for one version would hide one of them from every check."""
    counts = Counter(version for version, _ in section_list)
    duplicates = sorted(version for version, n in counts.items() if n > 1)
    assert not duplicates, (
        f"The changelog contains more than one section for: "
        f"{', '.join(duplicates)}. A lookup by version would silently keep only "
        "one of them, so the others would never be verified."
    )


def test_no_duplicate_manifest_entries(
    manifest_entries: list[dict[str, str]],
) -> None:
    """A duplicated manifest version would let one hash shadow another."""
    counts = Counter(entry["version"] for entry in manifest_entries)
    duplicates = sorted(version for version, n in counts.items() if n > 1)
    assert not duplicates, (
        f"The manifest records more than one entry for: {', '.join(duplicates)}."
    )


def test_every_recorded_section_is_unchanged(
    sections: dict[str, str], manifest: dict[str, str]
) -> None:
    """Published sections must hash to the value recorded for them."""
    changed = [
        version
        for version, expected in manifest.items()
        if version in sections and digest(sections[version]) != expected
    ]
    assert not changed, (
        f"Published changelog sections were modified: {', '.join(changed)}. "
        "Entries for released versions must keep their wording; add a new "
        "section instead."
    )


def test_no_recorded_section_disappeared(
    sections: dict[str, str], manifest: dict[str, str]
) -> None:
    """A recorded section must not be removed or its heading rewritten."""
    missing = sorted(set(manifest) - set(sections))
    assert not missing, (
        f"Published changelog sections are missing: {', '.join(missing)}. "
        "They may have been deleted or their heading changed."
    )


def test_manifest_covers_every_published_section(
    sections: dict[str, str], manifest: dict[str, str]
) -> None:
    """A released section without a hash would be unprotected."""
    published = {v for v in sections if v != UNRELEASED}
    unprotected = sorted(published - set(manifest))
    assert not unprotected, (
        f"Published sections are not covered by the manifest: "
        f"{', '.join(unprotected)}. Add their hashes so they cannot be "
        "edited unnoticed."
    )


def test_unreleased_section_is_not_frozen(manifest: dict[str, str]) -> None:
    """The Unreleased section is worked on continuously and must stay editable."""
    assert UNRELEASED not in manifest
