"""Tests for the guards around commit messages.

These decide what reaches the changelog and what raises the version, so the cases
that matter are the ones where commitizen's behaviour is surprising. Each of the
expectations below was measured against commitizen before being written down --
an earlier hand-written pattern got several of them wrong in both directions.
"""

from __future__ import annotations

import pytest
from check_pr_message import check, increment_for


class TestIncrementForMirrorsCommitizen:
    """The increment must come from commitizen, not from a copy of its rules."""

    def test_a_fix_raises_the_patch_version(self) -> None:
        """The ordinary case."""
        assert increment_for("fix(client): a crash", "") == "PATCH"

    def test_a_feature_raises_the_minor_version(self) -> None:
        """The other ordinary case."""
        assert increment_for("feat(auth): browser login", "") == "MINOR"

    def test_refactor_and_perf_also_release(self) -> None:
        """Easy to overlook: these are not documentation-only types."""
        assert increment_for("refactor(cli): tidy up", "") == "PATCH"
        assert increment_for("perf(json): faster parsing", "") == "PATCH"

    def test_docs_release_nothing(self) -> None:
        """Recorded, but not a reason to publish."""
        assert increment_for("docs(readme): fix a typo", "") is None

    def test_an_unparsable_subject_releases_nothing(self) -> None:
        """The silent failure this machinery exists to surface."""
        assert increment_for("Update authentication", "") is None


class TestTheDescriptionCanRaiseTheVersion:
    """The description becomes the commit body, and footers there count."""

    @pytest.mark.parametrize(
        ("body", "escalates"),
        [
            ("BREAKING CHANGE: gone", True),
            # Indented, but the first line of the body: commitizen strips the
            # whole body before splitting it, so the indentation disappears.
            ("    BREAKING CHANGE: gone", True),
            # Indented and *not* first, so the indentation survives and the line
            # no longer looks like a footer. A hand-written pattern flagged this.
            ("Some prose.\n\n    BREAKING CHANGE: gone", False),
            # Any word followed by "!" matches, not only BREAKING CHANGE.
            ("NOTE!: gone", True),
            ("BREAKING CHANGE(api): gone", True),
            ("Mentioning BREAKING CHANGE: mid-sentence does nothing.", False),
            ("> BREAKING CHANGE: quoted", False),
            ("Ordinary prose about the change.", False),
            # Not only breaking footers: any type at the start of a line is read
            # as one. Measured -- a fix(...) commit with this description
            # released 0.12.0 instead of 0.11.2, and the changelog mentioned no
            # feature at all. A fenced code block is no protection, because
            # commitizen reads a commit message rather than markdown.
            ("Example:\n\n```\nfeat: add browser login\n```", True),
            # A list is safe: the line starts with the bullet, not the type.
            ("Changes:\n\n- feat: add a thing\n- fix: repair a thing", False),
        ],
    )
    def test_bodies_that_do_and_do_not_escalate(
        self, body: str, escalates: bool
    ) -> None:
        """Each case was measured against commitizen first.

        Args:
            body: The pull request description.
            escalates: Whether it should raise the version beyond the title.
        """
        problem = check("fix(client): a crash", body)
        assert (problem is not None) == escalates

    def test_a_title_that_already_declares_the_break_is_consistent(self) -> None:
        """Declaring it in both places is the correct way to write it."""
        assert (
            check("feat(auth)!: require a marketplace", "BREAKING CHANGE: yes") is None
        )

    def test_a_feature_hiding_a_break_in_the_description_is_caught(self) -> None:
        """The case an earlier version missed.

        This repository sets ``major_version_zero``, under which a breaking
        change and a feature both release a minor version. Comparing what would
        actually be released therefore scored these two identically and reported
        nothing, so a breaking change declared only in the description passed
        with a title that never admitted to it.
        """
        assert check("feat(auth): require a marketplace", "BREAKING CHANGE: yes")
