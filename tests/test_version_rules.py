"""The rules by which commit messages become versions and changelog entries.

cliff.toml encodes decisions this repository depends on: the type is read only
from the subject line, a breaking change on 0.x raises the minor version, feat,
fix and perf reach a reader by default, and a ``Changelog:`` footer overrides
that default in either direction -- with the same footer deciding the release,
because what is skipped bumps nothing. git-cliff is a dependency like any
other, so an update could change any of this silently -- these tests pin the
measured behaviour, and a change fails in the update pull request rather than
in a release.

Every expectation was measured before it was written down. The cases that look
paranoid are the ones that real tools got wrong: commitizen raises the version
for a ``feat:`` line anywhere in the body, and release-please splits the body
on lines that merely look like commit subjects.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from changelog import split_sections


REPO_ROOT = Path(__file__).resolve().parent.parent

# The base the scratch repository is tagged with. Deliberately 0.x: several
# cases assert that a breaking change raises the minor version, which is the
# behaviour breaking_always_bump_major = false exists to provide.
BASE = "v0.11.0"


def _git_cliff() -> str:
    """Return the git-cliff executable to test against.

    Returns:
        Absolute path of the binary.
    """
    path = shutil.which("git-cliff")
    assert path is not None, (
        "git-cliff is not installed; the release dependency group provides it"
    )
    return path


def _run(args: list[str], cwd: Path) -> str:
    """Run a command and return its stdout.

    Args:
        args: Command and arguments.
        cwd: Working directory.

    Returns:
        Captured standard output.
    """
    result = subprocess.run(  # noqa: S603
        args, cwd=cwd, capture_output=True, text=True, check=True
    )
    return result.stdout


def _commit(repo: Path, message: str) -> None:
    """Create an empty commit with an exact message.

    Args:
        repo: Repository to commit in.
        message: Full commit message, subject and body.
    """
    message_file = repo.parent / "message.txt"
    message_file.write_text(message + "\n", encoding="utf-8")
    _run(
        [
            "git",
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "--allow-empty",
            "-F",
            str(message_file),
        ],
        repo,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A scratch repository carrying this project's cliff.toml.

    Args:
        tmp_path: Temporary directory supplied by pytest.

    Returns:
        Path of the repository, tagged v0.11.0.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "-q", "-b", "main"], repo)
    shutil.copy(REPO_ROOT / "cliff.toml", repo / "cliff.toml")
    _run(["git", "add", "cliff.toml"], repo)
    _run(
        [
            "git",
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "-m",
            "chore: base",
        ],
        repo,
    )
    _run(["git", "tag", BASE], repo)
    return repo


def bumped(repo: Path) -> str | None:
    """Return the version one commit would release, or None for no release.

    Args:
        repo: Repository whose head commit is judged.

    Returns:
        The bumped tag, or None when git-cliff answers with the current tag.
    """
    out = _run([_git_cliff(), "--bumped-version"], repo).strip()
    return None if out == BASE else out


class TestWhatBumpsAndToWhere:
    """Which commit subjects release, and which version they produce."""

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            # The three types that release by default, and where they land.
            ("feat(auth): add browser login", "v0.12.0"),
            ("fix(client): handle expired tokens", "v0.11.1"),
            ("perf(json): faster parsing", "v0.11.1"),
            # Types that are recorded in git but release nothing. refactor is
            # here on purpose: an internal restructuring is not something a
            # user needs to read about, and what is not changelog-worthy is
            # not release-worthy either. A refactor that *does* matter opts in
            # with a `Changelog:` footer, tested below.
            ("refactor(cli): tidy up", None),
            ("docs(readme): tidy", None),
            ("chore(deps): update pytest", None),
            ("ci(deps): update actions/checkout", None),
            ("revert: undo the auth change", None),
            # Words that merely begin with a releasing type. `^feat` alone
            # matched all four of these -- measured, each released 0.11.1
            # before the patterns were anchored at the type boundary.
            ("feature: accidental", None),
            ("fixup: accidental", None),
            ("refactoring: accidental", None),
            ("performance: accidental", None),
        ],
    )
    def test_subjects(self, repo: Path, message: str, expected: str | None) -> None:
        """The subject alone decides.

        Args:
            repo: Scratch repository.
            message: Commit subject.
            expected: Version, or None for no release.
        """
        _commit(repo, message)
        assert bumped(repo) == expected

    @pytest.mark.parametrize(
        "message",
        [
            # commitizen released a minor version for each of these. The type
            # belongs to the first line; a body line that merely starts like a
            # subject means nothing.
            "docs(readme): tidy\n\nfeat: add browser login",
            "docs(readme): tidy\n\n    feat: add browser login",
            "chore(deps): update pytest\n\nfix: upstream fixed something",
            # An embedded upstream changelog, the shape a dependency-update
            # body takes when release notes are quoted verbatim.
            (
                "chore(deps): update dependency foo to v2\n\n"
                "Release notes:\n\nfix: upstream crash\nfeat: upstream flag"
            ),
        ],
    )
    def test_body_lines_do_not_release(self, repo: Path, message: str) -> None:
        """No line of the body may influence the version.

        Args:
            repo: Scratch repository.
            message: Full commit message.
        """
        _commit(repo, message)
        assert bumped(repo) is None

    def test_a_code_block_does_not_release(self, repo: Path) -> None:
        """A fenced example must stay an example.

        commitizen raised the minor version for the feat line inside the
        fence -- there is no markdown in a commit message, only lines.
        """
        _commit(repo, "fix(client): a crash\n\n```\nfeat: add login\n```")
        assert bumped(repo) == "v0.11.1"

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            # Opting out: not worth telling users about means not worth a
            # release. The commit stays in git; the version does not move.
            ("fix(client): internal retry tweak\n\nChangelog: skip", None),
            ("perf(parser): cold-path allocation\n\nChangelog: skip", None),
            # Opting in: the footer puts the entry in the changelog and, by the
            # same act, makes the commit release-worthy -- a patch release.
            ("refactor(client): drop legacy pipeline\n\nChangelog: changed", "v0.11.1"),
            ("docs(auth): document browser auth\n\nChangelog: added", "v0.11.1"),
            ("chore(deps): raise cryptography floor\n\nChangelog: security", "v0.11.1"),
            # The footer token is matched case-insensitively.
            ("fix(client): internal only\n\nchangelog: skip", None),
            # The bump comes from the conventional type, not from the chosen
            # section: a feat filed under Fixed still releases a minor version.
            ("feat(auth): add login\n\nChangelog: fixed", "v0.12.0"),
            # And skipping a feat suppresses the minor bump entirely.
            ("feat(auth): internal scaffolding\n\nChangelog: skip", None),
            # A footer works next to the trailers squash commits routinely
            # carry; the rules match each trailer individually.
            (
                "fix(client): internal only\n\n"
                "Changelog: skip\n"
                "Co-authored-by: someone <s@example.com>",
                None,
            ),
            # A footer that is not the message's final paragraph is prose, per
            # the git trailer convention, and changes nothing.
            (
                "feat(auth): add login\n\nChangelog: skip\n\nMore prose after it.",
                "v0.12.0",
            ),
        ],
    )
    def test_a_changelog_footer_decides_both_ways(
        self, repo: Path, message: str, expected: str | None
    ) -> None:
        """The override changes the release along with the changelog.

        Args:
            repo: Scratch repository.
            message: Full commit message.
            expected: Version, or None for no release.
        """
        _commit(repo, message)
        assert bumped(repo) == expected

    def test_an_explicit_bang_is_trusted_even_on_an_unknown_type(
        self, repo: Path
    ) -> None:
        """`feature!: x` releases, although plain `feature:` does not.

        Deliberate: git-cliff bumps on the breaking marker itself, so a parser
        allowlist could only hide the entry, never stop the release. An
        explicit `!` is honoured -- dropping a real breaking change over a
        misspelt type would be the worse failure -- and the pull request title
        check rejects unknown types before they reach master anyway.
        """
        _commit(repo, "feature!: accidental but explicitly breaking")
        assert bumped(repo) == "v0.12.0"

    def test_a_breaking_change_cannot_be_skipped(self, repo: Path) -> None:
        """`Changelog: skip` loses against protect_breaking_commits.

        Whoever tries to skip a breaking change is wrong about one of the two
        labels, and the safe resolution is to release and show it.
        """
        _commit(
            repo,
            "feat(auth)!: drop the marketplace argument\n\nChangelog: skip",
        )
        assert bumped(repo) == "v0.12.0"
        # The entry survives too, under its raw type heading -- the skip rule
        # matched first, so the protected commit keeps no assigned group.
        fragment = _run([_git_cliff(), "--unreleased", "--tag", "v0.12.0"], repo)
        assert "**BREAKING**" in fragment
        assert "Drop the marketplace argument" in fragment

    @pytest.mark.parametrize(
        "message",
        [
            # Both spec-legitimate spellings of a breaking change.
            "feat(auth)!: require an explicit marketplace",
            "fix(client): new token header\n\nBREAKING CHANGE: header renamed",
            # protect_breaking_commits: the skip rule for chore must not be
            # able to swallow the break, or the version would silently not
            # move for the release that most needs it to.
            "chore(deps)!: drop support for Python 3.10",
        ],
    )
    def test_a_breaking_change_raises_the_minor_version(
        self, repo: Path, message: str
    ) -> None:
        """On 0.x a breaking change is a minor bump, never 1.0.0.

        Args:
            repo: Scratch repository.
            message: Full commit message.
        """
        _commit(repo, message)
        assert bumped(repo) == "v0.12.0"


class TestWhatTheChangelogContains:
    """The fragment handed to prepare_release.py."""

    def fragment(self, repo: Path, version: str = "v0.12.0") -> str:
        """Generate the unreleased section.

        Args:
            repo: Scratch repository.
            version: Tag the section is generated for.

        Returns:
            The generated fragment.
        """
        return _run([_git_cliff(), "--unreleased", "--tag", version], repo).strip("\n")

    def test_the_heading_is_the_historical_form(self, repo: Path) -> None:
        """One section, bracketed heading, the version prepare_release checks."""
        _commit(repo, "feat(auth): add browser login")
        sections = split_sections(self.fragment(repo))
        assert [version for version, _ in sections] == ["0.12.0"]

    def test_an_embedded_changelog_does_not_leak(self, repo: Path) -> None:
        """Entries quoted in a dependency-update body stay out.

        commitizen copied them in as our own: an upstream "fix: upstream
        crash" became a `### Fix` entry of this project.
        """
        _commit(
            repo,
            "chore(deps): update dependency foo to v2\n\n"
            "Release notes:\n\nfix: upstream crash\nfeat: upstream flag",
        )
        _commit(repo, "fix(client): our real fix")
        fragment = self.fragment(repo, "v0.11.1")
        assert "upstream" not in fragment
        assert "Our real fix" in fragment

    def test_a_breaking_change_carries_its_explanation(self, repo: Path) -> None:
        """The footer text lands next to the entry.

        The explanation exists only in the commit body; a changelog that shows
        a bare breaking marker sends every reader to the pull request.
        """
        _commit(
            repo,
            "fix(client): new token header\n\n"
            "BREAKING CHANGE: the x-adp-token header is gone",
        )
        fragment = self.fragment(repo)
        assert "**BREAKING**" in fragment
        assert "the x-adp-token header is gone" in fragment

    def test_only_reader_facing_commits_appear(self, repo: Path) -> None:
        """refactor, chore, ci, docs and friends stay out by default."""
        _commit(repo, "feat(auth): add browser login")
        _commit(repo, "chore(deps): update pytest")
        _commit(repo, "ci(deps): update actions/checkout")
        _commit(repo, "docs(readme): tidy")
        _commit(repo, "refactor(cli): shuffle internals")
        fragment = self.fragment(repo, "v0.12.0")
        assert "Add browser login" in fragment
        for absent in ("pytest", "checkout", "Tidy", "internals"):
            assert absent not in fragment

    def test_a_footer_override_lands_in_its_section(self, repo: Path) -> None:
        """The footer names the section the entry appears under."""
        _commit(
            repo,
            "refactor(client): drop the legacy pipeline\n\nChangelog: changed",
        )
        _commit(
            repo,
            "chore(deps): raise the cryptography floor\n\nChangelog: security",
        )
        fragment = self.fragment(repo, "v0.11.1")
        assert "### Changed" in fragment
        assert "Drop the legacy pipeline" in fragment
        assert "### Security" in fragment
        assert "Raise the cryptography floor" in fragment
        assert "Changelog:" not in fragment, "the footer itself must not leak"

    @pytest.mark.parametrize(
        "message",
        [
            # The bang form is caught by an explicit parser rule; the
            # footer-only form on a skipped type survives via
            # protect_breaking_commits. Either way the rule is the same: a
            # commit that raises the version must never be invisible in the
            # changelog -- a version that jumps with no entry explaining it is
            # exactly the silent failure this file exists to prevent.
            "docs(readme)!: restructure the guide\n\nBREAKING CHANGE: links changed",
            "docs(readme): restructure the guide\n\nBREAKING CHANGE: links changed",
            "chore(deps)!: drop support for Python 3.10",
        ],
    )
    def test_a_breaking_commit_of_a_skipped_type_stays_visible(
        self, repo: Path, message: str
    ) -> None:
        """Whatever raises the version must appear in the fragment.

        Args:
            repo: Scratch repository.
            message: Full commit message.
        """
        _commit(repo, message)
        assert bumped(repo) == "v0.12.0", "the version must move"
        fragment = self.fragment(repo)
        assert "**BREAKING**" in fragment, "and the entry must be readable"
