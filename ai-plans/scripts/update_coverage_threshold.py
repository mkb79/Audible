#!/usr/bin/env python3
"""Update coverage threshold in pyproject.toml based on actual coverage.

This script automatically updates the fail_under value in pyproject.toml
to match the current code coverage percentage (rounded down).

Usage:
    python scripts/update_coverage_threshold.py

Requirements:
    - coverage must be installed
    - coverage report must exist (.coverage file)
"""

import re
import subprocess
import sys
from pathlib import Path


def get_current_coverage() -> float:
    """Get current coverage percentage from coverage report.

    Returns:
        Current coverage as float (e.g., 46.25)

    Raises:
        RuntimeError: If coverage report cannot be generated
    """
    try:
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "coverage", "report", "--precision=2"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Failed to generate coverage report: {exc}\n"
            "Make sure you've run tests with coverage first."
        ) from exc
    except FileNotFoundError as exc:
        raise RuntimeError(
            "coverage command not found. Install with: uv add --group=tests coverage"
        ) from exc

    # Parse TOTAL line: TOTAL  1417   1042    408     16    21.23%
    for line in result.stdout.split("\n"):
        if line.startswith("TOTAL"):
            parts = line.split()
            coverage_str = parts[-1].rstrip("%")
            return float(coverage_str)

    raise RuntimeError("Could not find TOTAL line in coverage report")


def update_fail_under(new_threshold: int) -> None:
    """Update fail_under value in pyproject.toml.

    Args:
        new_threshold: New threshold value (integer percentage)

    Raises:
        FileNotFoundError: If pyproject.toml not found
        RuntimeError: If fail_under not found in pyproject.toml
    """
    pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        raise FileNotFoundError(
            "pyproject.toml not found. "
            "Make sure you're running this from the project root."
        )

    content = pyproject_path.read_text()

    # Find and update fail_under value
    pattern = r"(fail_under\s*=\s*)\d+"

    if not re.search(pattern, content):
        raise RuntimeError(
            "fail_under setting not found in pyproject.toml. "
            "Make sure [tool.coverage.report] section exists."
        )

    new_content = re.sub(pattern, rf"\g<1>{new_threshold}", content)

    pyproject_path.write_text(new_content)
    print(f"✅ Updated fail_under to {new_threshold}% in pyproject.toml")


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Get current coverage
        current_coverage = get_current_coverage()

        # Round down to nearest integer
        new_threshold = int(current_coverage)

        print(f"📊 Current coverage: {current_coverage:.2f}%")
        print(f"🎯 Setting fail_under to: {new_threshold}%")

        # Update pyproject.toml
        update_fail_under(new_threshold)

        print("\n✨ Success! Don't forget to commit the change:")
        print("   git add pyproject.toml")
        print(f'   git commit -m "chore: update fail_under to {new_threshold}%"')

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
