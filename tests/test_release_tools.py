"""Tests for the checks the publish workflow runs before anything irreversible.

These decide whether a tag is created and an upload happens, so every rejection
path is exercised here rather than discovered mid-release. The functions are
pure -- state in, problems out -- precisely so they can be.
"""

from __future__ import annotations

from typing import ClassVar

import pytest
from check_release_bodies import body_digest, compare, normalise, parse_api_pages
from print_section import section_for
from verify_release_commit import lock_version_of, problems_for

from changelog import digest


CHANGELOG = """# Changelog

## [0.12.0] - 2026-07-23

### Added

- **auth**: Browser login

## [0.11.0] - 2026-07-20

### Feat

- an entry whose wording must survive
"""

MANIFEST = [
    {
        "version": "0.11.0",
        "sha256": digest(
            "## [0.11.0] - 2026-07-20\n\n### Feat\n\n"
            "- an entry whose wording must survive\n"
        ),
    },
    {
        "version": "0.12.0",
        "sha256": digest(
            "## [0.12.0] - 2026-07-23\n\n### Added\n\n- **auth**: Browser login\n\n"
        ),
    },
]


class TestVerifyReleaseCommit:
    """The coherence check that gates tag, upload and release."""

    def test_a_coherent_release_has_no_problems(self) -> None:
        """The state the release pull request actually produces."""
        assert problems_for("0.12.0", "0.12.0", "0.12.0", CHANGELOG, MANIFEST) == []

    @pytest.mark.parametrize(
        ("version", "pyproject", "lock", "expected"),
        [
            ("0.12.0", "0.11.0", "0.12.0", "pyproject.toml carries"),
            ("0.12.0", "0.12.0", "0.11.0", "uv.lock records"),
            ("0.13.0", "0.13.0", "0.13.0", "exactly one is required"),
            # The section exists but is not the newest -- releasing an old
            # version out of order.
            ("0.11.0", "0.11.0", "0.11.0", "newest changelog section"),
            ("0.12.0rc1", "0.12.0rc1", "0.12.0rc1", "not a plain three-part"),
        ],
    )
    def test_disagreements_are_named(
        self, version: str, pyproject: str, lock: str, expected: str
    ) -> None:
        """Each inconsistency produces a problem naming it.

        Args:
            version: Version being released.
            pyproject: Version pyproject.toml claims.
            lock: Version uv.lock claims.
            expected: Substring of the expected problem.
        """
        problems = problems_for(version, pyproject, lock, CHANGELOG, MANIFEST)
        assert any(expected in problem for problem in problems), problems

    def test_a_tampered_published_section_blocks_the_release(self) -> None:
        """A manifest mismatch anywhere stops everything.

        The pull request checks catch this earlier; this is the last line,
        directly before the irreversible steps.
        """
        tampered = CHANGELOG.replace("wording must survive", "was rewritten")
        problems = problems_for("0.12.0", "0.12.0", "0.12.0", tampered, MANIFEST)
        assert any("does not match the hash" in problem for problem in problems)

    def test_a_duplicated_section_blocks_the_release(self) -> None:
        """Two sections for one version is the state a botched run leaves."""
        doubled = CHANGELOG.replace(
            "## [0.12.0] - 2026-07-23",
            "## [0.12.0] - 2026-07-23\n\n### Added\n\n- twice\n\n"
            "## [0.12.0] - 2026-07-23",
            1,
        )
        problems = problems_for("0.12.0", "0.12.0", "0.12.0", doubled, MANIFEST)
        assert any("exactly one is required" in problem for problem in problems)

    def test_lock_version_is_read_from_the_package_entry(self) -> None:
        """The right entry among a hundred dependencies."""
        lock = (
            '[[package]]\nname = "httpx"\nversion = "0.28.1"\n\n'
            '[[package]]\nname = "audible"\nversion = "0.12.0"\n'
        )
        assert lock_version_of(lock) == "0.12.0"
        assert lock_version_of('[[package]]\nname = "httpx"\nversion = "1"\n') == (
            "<absent>"
        )


class TestPrintSection:
    """The extraction that becomes the GitHub release body."""

    def test_the_section_is_returned_verbatim_minus_trailing_blanks(self) -> None:
        """Byte-for-byte except the file-layout blank lines at the end."""
        section = section_for("0.11.0", CHANGELOG)
        assert section == (
            "## [0.11.0] - 2026-07-20\n\n### Feat\n\n"
            "- an entry whose wording must survive\n"
        )

    def test_an_absent_version_returns_none(self) -> None:
        """Absence is an answer, not an error, for the caller to handle."""
        assert section_for("9.9.9", CHANGELOG) is None


class TestReleaseBodyDrift:
    """The audit that compares live release bodies with their recorded text."""

    BASELINE: ClassVar[dict[str, str]] = {
        "v0.11.0": body_digest("old body, written by hand")
    }

    def release(self, tag: str, body: str, *, draft: bool = False) -> dict[str, object]:
        """Build a release object as the API would return it.

        Args:
            tag: Tag name.
            body: Release body.
            draft: Whether the release is a draft.

        Returns:
            The release object.
        """
        return {"tag_name": tag, "body": body, "draft": draft}

    def test_a_clean_state_reports_nothing(self) -> None:
        """Old era matches its hash, new era matches its section."""
        releases = [
            self.release("v0.11.0", "old body, written by hand"),
            self.release(
                "v0.12.0",
                "## [0.12.0] - 2026-07-23\n\n### Added\n\n- **auth**: Browser login",
            ),
        ]
        assert compare(releases, self.BASELINE, CHANGELOG) == []

    def test_crlf_from_the_web_editor_is_not_drift(self) -> None:
        """GitHub's editor rewrites line endings; that is noise, not an edit."""
        releases = [
            self.release("v0.11.0", "old body, written by hand\r\n"),
            self.release(
                "v0.12.0",
                "## [0.12.0] - 2026-07-23\n\n### Added\n\n- **auth**: Browser login",
            ),
        ]
        assert compare(releases, self.BASELINE, CHANGELOG) == []

    @pytest.mark.parametrize(
        ("releases", "expected"),
        [
            # An edited pre-automation body.
            (
                [{"tag_name": "v0.11.0", "body": "reworded!", "draft": False}],
                "no longer matches its frozen hash",
            ),
            # An edited generated body.
            (
                [
                    {
                        "tag_name": "v0.11.0",
                        "body": "old body, written by hand",
                        "draft": False,
                    },
                    {"tag_name": "v0.12.0", "body": "reworded!", "draft": False},
                ],
                "differs from the changelog section",
            ),
            # A release nothing accounts for.
            (
                [
                    {
                        "tag_name": "v0.11.0",
                        "body": "old body, written by hand",
                        "draft": False,
                    },
                    {"tag_name": "v9.9.9", "body": "?", "draft": False},
                ],
                "an unexpected release",
            ),
            # A deleted pre-automation release.
            ([], "no longer published"),
            # A deleted generated release: v0.12.0 has a changelog section but
            # no baseline entry, so its absence must be flagged by the
            # changelog rule, not silently tolerated.
            (
                [
                    {
                        "tag_name": "v0.11.0",
                        "body": "old body, written by hand",
                        "draft": False,
                    },
                ],
                "a generated release was deleted",
            ),
        ],
    )
    def test_drift_is_named(
        self, releases: list[dict[str, object]], expected: str
    ) -> None:
        """Every kind of drift produces a problem naming it.

        Args:
            releases: Live releases as the API would return them.
            expected: Substring of the expected problem.
        """
        problems = compare(releases, self.BASELINE, CHANGELOG)
        assert any(expected in problem for problem in problems), problems

    def test_drafts_are_ignored(self) -> None:
        """Release Drafter's leftover draft is not a published body."""
        releases = [
            self.release("v0.11.0", "old body, written by hand"),
            self.release(
                "v0.12.0",
                "## [0.12.0] - 2026-07-23\n\n### Added\n\n- **auth**: Browser login",
            ),
            self.release("untagged-abc", "draft noise", draft=True),
        ]
        assert compare(releases, self.BASELINE, CHANGELOG) == []

    @pytest.mark.parametrize(
        ("text", "count"),
        [
            # One page, the only shape 37 releases produce today.
            ('[{"tag_name": "a"}, {"tag_name": "b"}]', 2),
            # Concatenated pages, what `gh api --paginate` emits from the 38th
            # release on -- json.loads rejects this outright (measured).
            ('[{"tag_name": "a"}]\n[{"tag_name": "b"}, {"tag_name": "c"}]', 3),
            # Slurped pages, the `--slurp` shape.
            ('[[{"tag_name": "a"}], [{"tag_name": "b"}]]', 2),
        ],
    )
    def test_every_pagination_shape_parses(self, text: str, count: int) -> None:
        """The audit must not break on the day the API grows a second page.

        Args:
            text: Raw API output in one of the three shapes.
            count: Releases it contains.
        """
        assert len(parse_api_pages(text)) == count

    def test_normalise_folds_only_line_endings_and_trailing_space(self) -> None:
        """Interior wording changes must never normalise away."""
        assert normalise("a\r\nb  \n") == "a\nb"
        assert normalise("a b") != normalise("ab")
