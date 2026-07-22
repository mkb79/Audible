"""The rules by which commit messages become versions and changelog entries.

cliff.toml encodes decisions this repository depends on: the type is read only
from the subject line, a breaking change on 0.x raises the minor version, and
only four commit types reach a reader. git-cliff is a dependency like any
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
            # The four types that release, and where they land.
            ("feat(auth): add browser login", "v0.12.0"),
            ("fix(client): handle expired tokens", "v0.11.1"),
            ("perf(json): faster parsing", "v0.11.1"),
            ("refactor(cli): tidy up", "v0.11.1"),
            # Types that are recorded in git but release nothing.
            ("docs(readme): tidy", None),
            ("chore(deps): update pytest", None),
            ("ci(deps): update actions/checkout", None),
            ("revert: undo the auth change", None),
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

    def test_only_the_four_reader_facing_types_appear(self, repo: Path) -> None:
        """chore, ci, docs and friends stay out of the changelog."""
        _commit(repo, "feat(auth): add browser login")
        _commit(repo, "chore(deps): update pytest")
        _commit(repo, "ci(deps): update actions/checkout")
        _commit(repo, "docs(readme): tidy")
        fragment = self.fragment(repo)
        assert "Add browser login" in fragment
        for absent in ("pytest", "checkout", "Tidy"):
            assert absent not in fragment
