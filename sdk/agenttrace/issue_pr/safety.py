"""Sandbox-contained, allowlisted, exact code edits."""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass
from pathlib import Path

from agenttrace.issue_pr.models import Edit

DEFAULT_ALLOWED = (
    "*.py",
    "*.txt",
    "*.md",
    "*.yaml",
    "*.yml",
    "*.json",
    "*.toml",
    "*.cfg",
    "*.ini",
)
DEFAULT_BLOCKED = (
    ".github/**",
    ".env*",
    "Makefile",
    "pyproject.toml",
    "docker-compose.yml",
    "requirements.txt",
    "alembic.ini",
    "**/secrets/**",
)


@dataclass(frozen=True)
class SafetyReport:
    """A path authorization decision with a stable machine-readable code."""

    allowed: bool
    code: str
    reason: str


@dataclass(frozen=True)
class EditResult:
    """Atomic outcome of applying a complete tuple of edits."""

    ok: bool
    changed_files: tuple[str, ...] = ()
    reason: str = ""


@dataclass(frozen=True)
class SandboxPolicy:
    """Serializable allow/block policy for workspace writes."""

    allowed_globs: tuple[str, ...] = DEFAULT_ALLOWED
    blocked_globs: tuple[str, ...] = DEFAULT_BLOCKED


class SafeEditor:
    """Apply exact replacements without permitting writes outside the workspace."""

    def __init__(
        self,
        workspace: str | Path,
        allowed_globs: tuple[str, ...] | list[str] | None = None,
        blocked_globs: tuple[str, ...] | list[str] | None = None,
        policy: SandboxPolicy | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        if policy is not None and (
            allowed_globs is not None or blocked_globs is not None
        ):
            raise ValueError("pass policy or explicit globs, not both")
        if policy is not None:
            allowed_globs = policy.allowed_globs
            blocked_globs = policy.blocked_globs
        self.allowed_globs = tuple(
            DEFAULT_ALLOWED if allowed_globs is None else allowed_globs
        )
        self.blocked_globs = tuple(
            DEFAULT_BLOCKED if blocked_globs is None else blocked_globs
        )

    def check_path(self, relative_path: str) -> SafetyReport:
        """Authorize a repository-relative path after resolving symlinks."""
        raw = Path(relative_path)
        if raw.is_absolute():
            return SafetyReport(False, "path_escape", "absolute paths are forbidden")
        candidate = (self.workspace / raw).resolve()
        try:
            relative = candidate.relative_to(self.workspace).as_posix()
        except ValueError:
            return SafetyReport(False, "path_escape", "path escapes the workspace")
        if not relative or relative == ".":
            return SafetyReport(
                False, "not_allowlisted", "workspace root is not a file"
            )
        for pattern in self.blocked_globs:
            if _matches(relative, pattern):
                return SafetyReport(
                    False,
                    "blocked",
                    f"path matches blocked pattern '{pattern}'",
                )
        if not any(_matches(relative, pattern) for pattern in self.allowed_globs):
            return SafetyReport(
                False,
                "not_allowlisted",
                "path does not match an allowlist pattern",
            )
        return SafetyReport(True, "allowed", "ok")

    def apply(self, edits: tuple[Edit, ...]) -> EditResult:
        """Validate every edit first, then write all affected files."""
        if not edits:
            return EditResult(False, reason="plan contains no edits")
        prepared: list[tuple[Path, str, str]] = []
        working: dict[Path, str] = {}
        display_paths: dict[Path, str] = {}

        for edit in edits:
            report = self.check_path(edit.path)
            if not report.allowed:
                return EditResult(False, reason=report.reason)
            target = (self.workspace / edit.path).resolve()
            if not target.is_file():
                return EditResult(False, reason=f"file not found: {edit.path}")
            current = working.get(target)
            if current is None:
                current = target.read_text(encoding="utf-8")
            matches = current.count(edit.find)
            if not edit.find or matches != 1:
                return EditResult(
                    False,
                    reason=(
                        f"edit search text must occur exactly once in {edit.path}; "
                        f"found {matches}"
                    ),
                )
            updated = current.replace(edit.find, edit.replace, 1)
            working[target] = updated
            display_paths[target] = edit.path.replace("\\", "/")

        for target, content in working.items():
            prepared.append((target, content, display_paths[target]))
        for target, content, _ in prepared:
            target.write_text(content, encoding="utf-8")
        return EditResult(
            True,
            tuple(path for _, _, path in prepared),
            "ok",
        )


def _matches(relative: str, pattern: str) -> bool:
    basename = os.path.basename(relative)
    if fnmatch.fnmatchcase(relative, pattern) or fnmatch.fnmatchcase(basename, pattern):
        return True
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        if relative == prefix or relative.startswith(prefix + "/"):
            return True
    if pattern.startswith("**/") and pattern.endswith("/**"):
        segment = pattern[3:-3]
        return segment in relative.split("/")
    return False


WorkspaceEditor = SafeEditor
