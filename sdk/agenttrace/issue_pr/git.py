"""Git operations guarded against protected branches, push, and merge hazards."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence

from agenttrace.issue_pr.commands import CommandResult, SubprocessExecutor


class CommandExecutor(Protocol):
    def run(
        self, command: Sequence[str], cwd: str | Path, timeout: float
    ) -> CommandResult: ...


class GuardedGit:
    """Small git adapter whose mutating operations enforce hard safety gates."""

    def __init__(
        self,
        workspace: str | Path,
        protected_branches: set[str] | frozenset[str] | None = None,
        executor: CommandExecutor | None = None,
        timeout: float = 20,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.protected_branches = frozenset(protected_branches or {"main", "master"})
        self.executor = executor or SubprocessExecutor()
        self.timeout = timeout

    def current_branch(self) -> str:
        result = self._run(("git", "rev-parse", "--abbrev-ref", "HEAD"))
        return result.stdout.strip() if result.ok and result.stdout.strip() else "main"

    def create_branch(self, branch: str) -> CommandResult:
        refusal = self._protected_refusal(branch, "create")
        return refusal or self._run(("git", "switch", "-c", branch))

    def commit(self, message: str, files: tuple[str, ...] = ()) -> CommandResult:
        branch = self.current_branch()
        refusal = self._protected_refusal(branch, "commit on")
        if refusal is not None:
            return refusal
        if files:
            staged = self._run(("git", "add", "--", *files))
            if not staged.ok:
                return staged
        else:
            staged = self._run(("git", "add", "-A"))
            if not staged.ok:
                return staged
        return self._run(("git", "commit", "-m", message))

    def push(self, branch: str, remote: str = "origin") -> CommandResult:
        refusal = self._protected_refusal(branch, "push")
        if refusal is not None:
            return refusal
        if not _is_literal_remote(remote):
            return CommandResult(
                False,
                -1,
                detail=f"refusing to push invalid remote '{remote}'",
            )
        return self._run(("git", "push", "--", remote, branch), timeout=30)

    def merge(self, _branch: str) -> CommandResult:
        """Hard refusal: this SDK never merges branches."""
        return CommandResult(False, -1, detail="merge is disabled")

    def _run(
        self, command: tuple[str, ...], timeout: float | None = None
    ) -> CommandResult:
        return self.executor.run(command, self.workspace, timeout or self.timeout)

    def _protected_refusal(self, branch: str, action: str) -> CommandResult | None:
        candidates = {
            candidate.lstrip("+").removeprefix("refs/heads/")
            for candidate in branch.split(":")
        }
        protected = candidates & self.protected_branches
        if protected:
            protected_branch = sorted(protected)[0]
            return CommandResult(
                False,
                -1,
                detail=(f"refusing to {action} protected branch '{protected_branch}'"),
            )
        if not _is_literal_branch(branch):
            return CommandResult(
                False,
                -1,
                detail=f"refusing to {action} invalid branch name '{branch}'",
            )
        return None


BranchGuard = GuardedGit


def _is_literal_branch(branch: str) -> bool:
    """Accept literal local branch names, never options, symbols, or refspecs."""
    if not branch or branch in {"@", "HEAD"} or branch.startswith(("-", "/")):
        return False
    if branch.endswith(("/", ".", ".lock")):
        return False
    if any(token in branch for token in (":", "..", "//", "@{", "\\", " ")):
        return False
    components = branch.split("/")
    return all(component and not component.startswith(".") for component in components)


def _is_literal_remote(remote: str) -> bool:
    return (
        bool(remote)
        and not remote.startswith("-")
        and not any(character.isspace() or ord(character) < 32 for character in remote)
    )
