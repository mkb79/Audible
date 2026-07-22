"""Tests for the changelog surgery performed during a release.

This edits a file whose older content must not change, so the failure modes are
exercised here rather than discovered while a release is half-finished. The
tests drive :func:`prepare` against temporary files, not only the splice helper,
because the ordering of validation and writing is itself part of the guarantee.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from changelog import digest, prepend_section, split_sections
from prepare_release import prepare


EXISTING = """# Changelog

Some introduction that belongs to no section.

## v0.11.0 (2026-07-20)

### Feat

- an entry whose wording must survive

## Bugfix

- a subheading that is content, not a boundary

## [0.10.0] - 2024-09-26

### Added

- an older entry
"""

FRAGMENT = """## v0.12.0 (2026-07-22)

### Feat

- something new
"""


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, Path]:
    """A changelog and manifest to operate on.

    Args:
        tmp_path: Temporary directory supplied by pytest.

    Returns:
        Paths to the changelog and the manifest.
    """
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(EXISTING, encoding="utf-8")
    manifest = tmp_path / ".changelog-manifest.json"
    entries = [
        {"version": version, "sha256": digest(section)}
        for version, section in split_sections(EXISTING)
    ]
    manifest.write_text(json.dumps({"sections": entries}, indent=2) + "\n")
    return changelog, manifest


def test_the_release_lands_above_the_previous_one(repo: tuple[Path, Path]) -> None:
    """The prepared release becomes the newest section."""
    changelog, manifest = repo
    prepare("0.12.0", FRAGMENT, changelog, manifest)
    versions = [v for v, _ in split_sections(changelog.read_text(encoding="utf-8"))]
    assert versions == ["0.12.0", "0.11.0", "0.10.0"]


def test_existing_sections_are_byte_identical_afterwards(
    repo: tuple[Path, Path],
) -> None:
    """Inserting must not disturb a single character of released text."""
    changelog, manifest = repo
    before = dict(split_sections(EXISTING))
    prepare("0.12.0", FRAGMENT, changelog, manifest)
    after = dict(split_sections(changelog.read_text(encoding="utf-8")))
    for version, section in before.items():
        assert after[version] == section, f"the section for {version} changed"


def test_the_recorded_hash_describes_the_file(repo: tuple[Path, Path]) -> None:
    """The manifest must match what actually landed, not the input text.

    Freezing the fragment instead would record something differing from the file
    by whitespace, and the mismatch would only appear on the next pull request.
    """
    changelog, manifest = repo
    prepare("0.12.0", FRAGMENT, changelog, manifest)

    written = dict(split_sections(changelog.read_text(encoding="utf-8")))["0.12.0"]
    recorded = {
        entry["version"]: entry["sha256"]
        for entry in json.loads(manifest.read_text())["sections"]
    }
    assert recorded["0.12.0"] == digest(written)
    assert digest(written) != digest(FRAGMENT), (
        "the test would not distinguish the two if they happened to be equal"
    )


def test_the_manifest_only_grows(repo: tuple[Path, Path]) -> None:
    """Existing entries keep their value and their position."""
    changelog, manifest = repo
    before = json.loads(manifest.read_text())["sections"]
    prepare("0.12.0", FRAGMENT, changelog, manifest)
    after = json.loads(manifest.read_text())["sections"]
    assert after[: len(before)] == before
    assert after[-1]["version"] == "0.12.0"


@pytest.mark.parametrize(
    ("version", "fragment", "expected"),
    [
        ("0.12.0", FRAGMENT.replace("v0.12.0", "v0.13.0"), "the fragment is for"),
        ("0.11.0", FRAGMENT.replace("v0.12.0", "v0.11.0"), "already contains"),
        ("0.10.0", FRAGMENT.replace("v0.12.0", "v0.10.0"), "already contains"),
        ("0.9.0", FRAGMENT.replace("v0.12.0", "v0.9.0"), "not newer than"),
        ("0.12.0", "loose prose\n\n" + FRAGMENT, "begin with its section heading"),
        ("0.12.0", FRAGMENT + "\n## v0.13.0 (2026-07-23)\n\n- oops\n", "exactly one"),
        ("0.12.0", "no heading at all\n", "exactly one"),
        ("0.12", FRAGMENT, "plain three-part version"),
    ],
)
def test_bad_input_is_refused_without_touching_anything(
    repo: tuple[Path, Path], version: str, fragment: str, expected: str
) -> None:
    """Every rejection must leave both files exactly as they were."""
    changelog, manifest = repo
    before_changelog = changelog.read_text(encoding="utf-8")
    before_manifest = manifest.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match=expected):
        prepare(version, fragment, changelog, manifest)

    assert changelog.read_text(encoding="utf-8") == before_changelog
    assert manifest.read_text(encoding="utf-8") == before_manifest


def test_an_unreleased_section_blocks_preparation(repo: tuple[Path, Path]) -> None:
    """Prepending above Unreleased would bury it beneath the release.

    Its hand-written entries would then describe a version that has already gone
    out, while appearing to be pending.
    """
    changelog, manifest = repo
    changelog.write_text(
        EXISTING.replace(
            "## v0.11.0 (2026-07-20)",
            "## [Unreleased]\n\n### Added\n\n- pending\n\n## v0.11.0 (2026-07-20)",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Unreleased"):
        prepare("0.12.0", FRAGMENT, changelog, manifest)


def test_preparing_the_same_release_twice_is_refused(
    repo: tuple[Path, Path],
) -> None:
    """A rerun must not append a second section or a second hash."""
    changelog, manifest = repo
    prepare("0.12.0", FRAGMENT, changelog, manifest)
    with pytest.raises(ValueError, match="already contains"):
        prepare("0.12.0", FRAGMENT, changelog, manifest)


def test_the_header_above_the_first_section_is_preserved() -> None:
    """Everything before the first section belongs to nobody and must remain."""
    result = prepend_section(EXISTING, FRAGMENT)
    assert result.startswith(
        "# Changelog\n\nSome introduction that belongs to no section.\n\n"
    )


def test_surrounding_blank_lines_do_not_change_the_result() -> None:
    """Whitespace around the fragment must not leak into the file."""
    assert prepend_section(EXISTING, "\n\n" + FRAGMENT + "\n\n\n") == prepend_section(
        EXISTING, FRAGMENT
    )
