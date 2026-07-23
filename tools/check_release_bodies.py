"""Detect edits to the text of published GitHub releases.

Tokens cannot prevent this: the releases API is governed by the contents
permission, and no token able to push a branch can be denied it. So the
guarantee that published release notes stay untouched has to come from
detection -- this compares every live release body against what it is known to
have said.

Two sources of truth, by era. Releases up to v0.11.0 were written by hand or by
Release Drafter; their bodies are frozen as hashes in ``.release-bodies.json``.
Releases from 0.12.0 on are created by the publish workflow with the changelog
section as their body, so they are compared against the changelog itself --
whose sections the changelog manifest already freezes. No file needs updating
when a new release is published.

Bodies are normalised before comparison (CRLF to LF, trailing whitespace
stripped): GitHub's web editor rewrites line endings, and a hash difference
that says "someone pressed save in the browser" would drown the signal.

Usage::

    gh api --paginate repos/<owner>/<repo>/releases > releases.json
    python tools/check_release_bodies.py releases.json

    # one-time freeze of the pre-automation era (refuses to overwrite):
    python tools/check_release_bodies.py releases.json --snapshot
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from changelog import UNRELEASED, split_sections


REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE = REPO_ROOT / ".release-bodies.json"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"


def normalise(body: str) -> str:
    """Return a body in the canonical form used for comparison.

    Args:
        body: A release body or changelog section.

    Returns:
        The text with CRLF folded to LF and trailing whitespace removed.
    """
    lines = body.replace("\r\n", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip("\n")


def body_digest(body: str) -> str:
    """Return the hash recorded for a release body.

    Args:
        body: The release body.

    Returns:
        Hex-encoded SHA-256 of the normalised body.
    """
    return hashlib.sha256(normalise(body).encode("utf-8")).hexdigest()


def compare(
    releases: list[dict[str, object]],
    baseline: dict[str, str],
    changelog: str,
) -> list[str]:
    """Report every release whose body no longer says what it said.

    Args:
        releases: Release objects as the GitHub API returns them.
        baseline: Frozen hashes of the pre-automation era, by tag.
        changelog: Full contents of the changelog.

    Returns:
        Human-readable problems; empty when nothing drifted.
    """
    sections = {version: normalise(text) for version, text in split_sections(changelog)}
    problems = []
    seen = set()

    for release in releases:
        if release.get("draft"):
            continue
        tag = str(release.get("tag_name") or "")
        body = str(release.get("body") or "")
        seen.add(tag)

        if tag in baseline:
            if body_digest(body) != baseline[tag]:
                problems.append(f"{tag}: the body no longer matches its frozen hash")
            continue

        version = tag.removeprefix("v")
        section = sections.get(version)
        if section is None:
            problems.append(
                f"{tag}: not in the baseline and no changelog section exists "
                "for it -- an unexpected release"
            )
        elif normalise(body) != section:
            problems.append(
                f"{tag}: the body differs from the changelog section it was "
                "published from"
            )

    for tag in baseline:
        if tag not in seen:
            problems.append(
                f"{tag}: frozen in the baseline but no longer published -- "
                "a release was deleted"
            )

    # The generated era has no baseline entries -- its releases are accounted
    # for by the changelog itself. Every section outside the baseline must
    # therefore still be published, or a generated release was deleted and the
    # baseline loop above would never notice.
    for version in sections:
        if version == UNRELEASED:
            continue
        tag = f"v{version}"
        if tag not in baseline and tag not in seen:
            problems.append(
                f"{tag}: the changelog has this section but no release is "
                "published for it -- a generated release was deleted"
            )

    return problems


def snapshot(releases: list[dict[str, object]]) -> int:
    """Freeze the current bodies as the baseline. One-time.

    Args:
        releases: Release objects as the GitHub API returns them.

    Returns:
        Process exit code.
    """
    if BASELINE.exists():
        print(
            f"{BASELINE.name} already exists; refusing to overwrite it. "
            "Rewriting the baseline is exactly the edit it exists to detect.",
            file=sys.stderr,
        )
        return 1
    frozen = {
        str(release["tag_name"]): body_digest(str(release.get("body") or ""))
        for release in releases
        if not release.get("draft")
    }
    BASELINE.write_text(
        json.dumps(dict(sorted(frozen.items())), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Froze {len(frozen)} release bodies into {BASELINE.name}.")
    return 0


def parse_api_pages(text: str) -> list[dict[str, object]]:
    """Return the releases from any shape ``gh api`` produces.

    ``gh api --paginate`` writes the pages as *concatenated* JSON arrays --
    ``[...][...]`` -- which ``json.loads`` rejects outright. With 37 releases
    everything fits one page today, so a plain load works right up until the
    38th-plus release pushes the API onto a second page, and the audit would
    break on the exact day the repository grows. ``--slurp`` wraps the pages
    in an outer array instead. All three shapes are accepted here, so the
    caller cannot get this wrong.

    Args:
        text: Raw output of the releases API call.

    Returns:
        The release objects, flattened across pages.
    """
    decoder = json.JSONDecoder()
    pages = []
    index = 0
    while index < len(text):
        page, end = decoder.raw_decode(text, index)
        pages.append(page)
        index = end
        while index < len(text) and text[index].isspace():
            index += 1

    flat: list[dict[str, object]] = []
    for page in pages:
        for item in page:
            # --slurp nests the pages one level deeper.
            if isinstance(item, list):
                flat.extend(item)
            else:
                flat.append(item)
    return flat


def main(argv: list[str]) -> int:
    """Compare live release bodies against their recorded text.

    Args:
        argv: Path to a JSON dump of the releases API, and optionally
            ``--snapshot``.

    Returns:
        Process exit code.
    """
    if not argv or len(argv) > 2 or (len(argv) == 2 and argv[1] != "--snapshot"):
        print(
            f"usage: {sys.argv[0]} <releases.json> [--snapshot]",
            file=sys.stderr,
        )
        return 2

    releases = parse_api_pages(Path(argv[0]).read_text(encoding="utf-8"))

    if len(argv) == 2:
        return snapshot(releases)

    baseline: dict[str, str] = json.loads(BASELINE.read_text(encoding="utf-8"))
    problems = compare(releases, baseline, CHANGELOG.read_text(encoding="utf-8"))
    if problems:
        print("Published release bodies have drifted:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    checked = sum(1 for r in releases if not r.get("draft"))
    print(f"All {checked} release bodies match their recorded text.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
