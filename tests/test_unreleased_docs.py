"""Tests for the docs-time pending-changes block.

This renders what the next release would contain at documentation build time.
The one property that must never fail is that it cannot affect a release -- it
only reads git and returns a string -- so the tests focus on the pure rewrite
and on degrading to nothing rather than raising.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from unreleased_docs import fragment, last_release_tag, strip_v, to_unreleased


SECTION = (
    "\n## [0.13.0] - 2026-07-24\n\n"
    "### Added\n\n- **client**: A pending feature\n\n"
    "### Fixed\n\n- **json**: A pending fix\n"
)


class TestToUnreleased:
    """Rewriting a generated release section into the pending block."""

    def test_the_dated_heading_becomes_an_unreleased_heading(self) -> None:
        """The heading names the expected version but not a release date."""
        out = to_unreleased(SECTION, "0.13.0")
        assert out.startswith("## Unreleased (expected 0.13.0)\n")
        assert "] - 2026" not in out

    def test_the_groups_and_entries_are_left_alone(self) -> None:
        """Only the heading changes; git-cliff's grouping is preserved."""
        out = to_unreleased(SECTION, "0.13.0")
        assert "### Added" in out
        assert "### Fixed" in out
        assert "A pending feature" in out
        assert "A pending fix" in out

    def test_the_result_is_a_single_trailing_newline(self) -> None:
        """The block slots cleanly between the page heading and the include."""
        assert to_unreleased(SECTION, "0.13.0").endswith("fix\n")
        assert not to_unreleased(SECTION, "0.13.0").endswith("\n\n")


class TestStripV:
    """The helper both comparisons rely on."""

    @pytest.mark.parametrize(
        ("tag", "expected"),
        [("v0.13.0", "0.13.0"), ("0.13.0", "0.13.0"), ("v1.2.3", "1.2.3")],
    )
    def test_a_leading_v_is_removed_once(self, tag: str, expected: str) -> None:
        """A leading v is stripped; a bare version is left alone.

        Args:
            tag: The input tag.
            expected: The version without a leading v.
        """
        assert strip_v(tag) == expected


class TestFragmentDegrades:
    """Nothing about a docs build may fail because of this."""

    def test_a_tagged_build_shows_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The stable docs represent a shipped version, not master.

        Args:
            monkeypatch: pytest fixture for patching the environment.
        """
        monkeypatch.setenv("READTHEDOCS_VERSION_TYPE", "tag")
        assert fragment(Path(__file__).resolve().parent.parent) == ""

    def test_a_pull_request_build_shows_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A pull request build represents the pull request, not master.

        Args:
            monkeypatch: pytest fixture for patching the environment.
        """
        monkeypatch.setenv("READTHEDOCS_VERSION_TYPE", "external")
        assert fragment(Path(__file__).resolve().parent.parent) == ""

    def test_a_directory_without_git_shows_nothing(self, tmp_path: Path) -> None:
        """A missing repository degrades to the empty string, never an error.

        Args:
            tmp_path: Temporary directory supplied by pytest.
        """
        assert fragment(tmp_path) == ""


class TestLastReleaseTag:
    """Choosing the newest release tag from the repository's own history."""

    def test_the_newest_release_tag_of_this_repo(self) -> None:
        """Runs against the real repository, whose newest tag is at least 0.12.0."""
        tag = last_release_tag(Path(__file__).resolve().parent.parent)
        assert tag.startswith("v")
        assert [int(n) for n in strip_v(tag).split(".")] >= [0, 12, 0]
