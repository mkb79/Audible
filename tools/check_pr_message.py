"""Report when a pull request description raises the release beyond its title.

This repository squash-merges with ``squash_merge_commit_message = PR_BODY``, so
the description becomes the commit body, and commitizen reads footers there when
deciding the next version. Any line that merely begins like one counts:
``BREAKING CHANGE:`` obviously, but also ``NOTE!:``, since the pattern accepts
any word followed by ``!``, and plain ``feat:`` or ``fix:``.

Fenced code blocks are not exempt -- commitizen sees a commit message, not
markdown. Measured: a ``fix(client): ...`` commit whose description contained

.. code-block:: text

    ```
    feat: add browser login
    ```

released 0.12.0 rather than 0.11.2, while the changelog listed only the fix. A
pull request that documents the commit convention does this to itself.

Mirroring commitizen's rules with a regular expression was tried first and got
them wrong in both directions: it flagged an indented line that commitizen
ignores, and missed ``BREAKING CHANGE(api):`` and ``NOTE!:``, which it does not.
So this does not mirror them. It asks commitizen for the increment of the title
alone and of the title with the description, and reports any difference.

Usage::

    PR_TITLE=... PR_BODY=... python tools/check_pr_message.py
"""

from __future__ import annotations

import os
import sys

# These are commitizen's own internals, not its public surface -- it exports
# only BaseCommitizen. Using them is a deliberate trade. The alternative is to
# simulate the commit in a scratch repository and shell out to `cz`, which needs
# a copied pyproject and lock file, a synthetic tag, and a second pass with
# major_version_zero disabled, because the real configuration cannot tell a
# breaking change from a feature. That is more machinery, not less.
#
# The risk this accepts is bounded: uv.lock pins commitizen exactly, so the
# import can only break when a dependency update proposes a new version, and the
# tests below fail in that pull request rather than silently on master.
from commitizen.bump import find_increment
from commitizen.defaults import BUMP_MAP, BUMP_PATTERN
from commitizen.git import GitCommit


# find_increment returns one of these or None. Ordered least to most severe so
# two results can be compared rather than merely tested for equality.
SEVERITY = {None: 0, "PATCH": 1, "MINOR": 2, "MAJOR": 3}


def increment_for(title: str, body: str) -> str | None:
    """Return the increment commitizen derives from one commit message.

    Deliberately uses the map that keeps MAJOR distinct, not the one this
    repository releases with. Under ``major_version_zero`` a breaking change and
    a feature both collapse to MINOR, so comparing what the repository would
    actually release cannot tell them apart: ``feat: x`` with a breaking footer
    in the body scores the same as ``feat: x`` alone, and an undeclared breaking
    change slips through. Asking the question in a scale that still separates
    them is what makes the comparison meaningful. The released version is
    unaffected -- commitizen computes that itself, from its own configuration.

    Args:
        title: Commit subject.
        body: Commit body, which may be empty.

    Returns:
        ``"MAJOR"``, ``"MINOR"``, ``"PATCH"`` or None when nothing is warranted.
    """
    commit = GitCommit(rev="0" * 40, title=title, body=body)
    return find_increment([commit], BUMP_PATTERN, BUMP_MAP)


def check(title: str, body: str) -> str | None:
    """Return a problem with the description, or None if there is none.

    Args:
        title: The pull request title, which becomes the commit subject.
        body: The pull request description, which becomes the commit body.

    Returns:
        A human-readable explanation, or None when the description does not
        change what the title alone would release.
    """
    from_title = increment_for(title, "")
    from_both = increment_for(title, body)

    if SEVERITY[from_both] <= SEVERITY[from_title]:
        return None

    # Deliberately not naming the two increments. They are measured on a scale
    # this repository does not release on -- under major_version_zero a breaking
    # change comes out as a minor version -- so reporting "MAJOR" would predict
    # a release that will not happen.
    return (
        "The description carries a release signal the title does not. Merged as "
        "written, it would change the version beyond what the title announces."
    )


def main() -> int:
    """Check the title and description named in the environment.

    Returns:
        Process exit code.
    """
    title = os.environ.get("PR_TITLE", "")
    body = os.environ.get("PR_BODY", "")

    if not title:
        print("PR_TITLE is empty.", file=sys.stderr)
        return 2

    problem = check(title, body)
    if problem is None:
        print("The description does not change what the title releases.")
        return 0

    print(f"::error::{problem}")
    print(
        "\nSomething in the description begins a line the way a commit footer\n"
        "does -- 'BREAKING CHANGE:', 'NOTE!:', or simply 'feat:' or 'fix:'.\n"
        "Fenced code blocks are not exempt: commitizen reads a commit message,\n"
        "not markdown.\n"
        "\n"
        "If the change really is breaking, say so in the title, which is where\n"
        "readers look:\n"
        "\n"
        "    feat(auth)!: require an explicit marketplace\n"
        "\n"
        "If the line is prose or an example, keep it away from the start of a\n"
        "line: quote it with '> ', keep it inside a sentence, or indent it\n"
        "anywhere except the very first line of the description.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
