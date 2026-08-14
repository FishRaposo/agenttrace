"""Fail when the repository still relies on the retired external core package."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATTERNS = (
    re.compile(r"\.\./shared-core"),
    re.compile(r"git\+https://[^\s'\"]*operator-shared-core"),
    re.compile(r"(?:from|import)\s+shared_core\b"),
)
EXCLUDED_PARTS = {".git", "__pycache__", "node_modules", ".next", "artifacts"}
TARGETS = (
    "server",
    "sdk",
    "Makefile",
    ".github",
    "Dockerfile",
    "docker-compose.yml",
    "README.md",
    "docs",
    "AGENTS.md",
)


def iter_files(target: str):
    path = ROOT / target
    if path.is_file():
        yield path
        return
    if not path.exists():
        return
    for candidate in path.rglob("*"):
        if candidate.is_file() and not EXCLUDED_PARTS.intersection(candidate.parts):
            yield candidate


def main() -> int:
    violations: list[tuple[Path, int, str]] = []
    for target in TARGETS:
        for path in iter_files(target):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for line_number, line in enumerate(lines, start=1):
                if any(pattern.search(line) for pattern in PATTERNS):
                    violations.append(
                        (path.relative_to(ROOT), line_number, line.strip())
                    )

    if violations:
        print("Forbidden external shared-core dependency references found:")
        for path, line_number, line in violations:
            print(f"  {path}:{line_number}: {line}")
        return 1

    print("No actionable external shared-core dependencies found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
