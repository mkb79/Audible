"""Shared reading and writing of the changelog and its manifest.

Both the integrity test and the release preparation need to agree on what a
section is and how it is hashed. Two implementations would eventually disagree,
and the disagreement would surface as a released section that no longer matches
the hash recorded for it -- which is the exact failure this machinery exists to
prevent.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


# Two heading styles have to be recognised. Historical sections look like
# "## [0.11.0] - 2026-07-20", "## [Unreleased]" uses the same bracketed form,
# and the template in cliff.toml continues it for generated sections. The
# "## v0.12.0 (2026-07-22)" form is what commitizen would emit; it is kept
# recognised defensively, so a heading hand-written in that style would still
# be seen as a section boundary rather than becoming silently invisible --
# neither published nor unprotected.
#
# Neither alternative matches "## Bugfix", which older sections contain as a
# subheading at the same level and which is content, not a boundary.
SECTION_HEADING = re.compile(
    r"^## (?:\[(?P<bracketed>[^\]]+)\]|v(?P<generated>\d+\.\d+\.\d+))",
    re.MULTILINE,
)

UNRELEASED = "Unreleased"


def version_of(match: re.Match[str]) -> str:
    """Return the version a section heading refers to.

    Args:
        match: A match of :data:`SECTION_HEADING`.

    Returns:
        The version string, without the leading ``v`` of generated headings.
    """
    return match.group("bracketed") or match.group("generated")


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
    marks = [(m.start(), version_of(m)) for m in SECTION_HEADING.finditer(text)]
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


def load_manifest(path: Path) -> list[dict[str, str]]:
    """Read the recorded section hashes.

    Args:
        path: Location of the manifest.

    Returns:
        The entries, in file order.
    """
    data: dict[str, list[dict[str, str]]] = json.loads(path.read_text(encoding="utf-8"))
    return data["sections"]


def prepend_section(changelog: str, fragment: str) -> str:
    """Insert a new section above the first existing one.

    The header above the first section is preserved untouched, and no existing
    section is read or rewritten -- the new text is spliced in at the boundary.

    Args:
        changelog: Current contents of the changelog.
        fragment: The new section, heading included.

    Returns:
        The changelog with the fragment inserted.

    Raises:
        ValueError: If the changelog has no section to insert above, or the
            fragment is not exactly one section.
    """
    fragment = fragment.strip("\n") + "\n\n"
    sections = split_sections(fragment)
    if len(sections) != 1:
        raise ValueError(
            f"the fragment must contain exactly one section, found {len(sections)}"
        )
    # Without this, loose prose above the heading is carried into the file: the
    # fragment still parses as one section, because everything before the first
    # heading belongs to no section and is silently ignored.
    if not fragment.startswith("## "):
        raise ValueError("the fragment must begin with its section heading")

    existing = split_sections(changelog)
    if not existing:
        raise ValueError("the changelog contains no section to insert above")

    # Inserting above an Unreleased section would bury it beneath the release
    # and leave its hand-written entries describing a version that has already
    # gone out. Resolving that is a decision, not something to do silently.
    if any(version == UNRELEASED for version, _ in existing):
        raise ValueError(
            "the changelog still has an Unreleased section; fold it into the "
            "release or remove it before preparing one"
        )

    first = SECTION_HEADING.search(changelog)
    assert first is not None  # noqa: S101 - guaranteed by the check above
    return changelog[: first.start()] + fragment + changelog[first.start() :]
