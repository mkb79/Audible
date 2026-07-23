"""Print one changelog section, exactly as the file carries it.

The release workflow uses this for the GitHub release body: the body becomes a
byte-for-byte copy of the changelog section, which the manifest already
freezes. One text, one hash, one place drift can be detected against.

Usage::

    python tools/print_section.py <version> [changelog-path]
"""

from __future__ import annotations

import sys
from pathlib import Path

from changelog import split_sections


def section_for(version: str, changelog: str) -> str | None:
    """Return the exact text of one version's section.

    Args:
        version: The version whose section is wanted.
        changelog: Full contents of the changelog.

    Returns:
        The section including its heading, or None if absent. Trailing blank
        lines are trimmed -- they belong to the file layout, not the section.
    """
    for found, text in split_sections(changelog):
        if found == version:
            return text.rstrip("\n") + "\n"
    return None


def main(argv: list[str]) -> int:
    """Print the requested section to stdout.

    Args:
        argv: Version, and optionally the changelog path.

    Returns:
        Process exit code.
    """
    if len(argv) not in (1, 2):
        print(f"usage: {sys.argv[0]} <version> [changelog-path]", file=sys.stderr)
        return 2

    version = argv[0]
    path = Path(argv[1]) if len(argv) == 2 else Path("CHANGELOG.md")
    section = section_for(version, path.read_text(encoding="utf-8"))
    if section is None:
        print(f"No section for {version} in {path}.", file=sys.stderr)
        return 1
    sys.stdout.write(section)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
