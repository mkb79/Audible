"""Guards the wording of already published changelog entries.

Released sections must never change. Once a version is on PyPI and its notes
are on the releases page, editing the corresponding changelog text rewrites
history that users have already read.

`.changelog-manifest.json` records a hash per published section. This test
recomputes them, so any edit to a released section fails the pull request
instead of being noticed later, or not at all.

This only compares the two files against each other. Rewriting a section *and*
its hash in the same change is self-consistent and passes here; that case is
caught by tools/check_manifest_append_only.py, which compares against the base
branch.
"""

from collections import Counter
from pathlib import Path

import pytest

from changelog import UNRELEASED, digest, load_manifest, split_sections


REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
MANIFEST = REPO_ROOT / ".changelog-manifest.json"


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
    return load_manifest(MANIFEST)


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
