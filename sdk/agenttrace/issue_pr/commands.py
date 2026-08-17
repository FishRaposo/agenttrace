"""Shell-free subprocess execution primitives."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Protocol, Sequence

from agenttrace.issue_pr.models import TestResult


@dataclass(frozen=True)
class CommandResult:
    """Outcome of an argv-based subprocess call."""

    ok: bool
    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    detail: str = ""


class CommandExecutor(Protocol):
    def run(
        self, command: Sequence[str], cwd: str | Path, timeout: float
    ) -> CommandResult: ...


@dataclass(frozen=True)
class TestCommandPolicy:
    """Exact trusted test argv accepted from an otherwise untrusted plan."""

    allowed_commands: tuple[tuple[str, ...], ...] = (
        ("python", "-m", "pytest", "-q"),
        ("python.exe", "-m", "pytest", "-q"),
        ("pytest", "-q"),
        ("pytest.exe", "-q"),
    )

    def allows(self, command: Sequence[str]) -> bool:
        return tuple(command) in self.allowed_commands


class SubprocessExecutor:
    """Run an argv with ``shell=False`` and a mandatory timeout."""

    def run(
        self,
        command: Sequence[str],
        cwd: str | Path,
        timeout: float,
    ) -> CommandResult:
        if not command or any(
            not isinstance(part, str) or not part for part in command
        ):
            return CommandResult(False, -1, detail="command must be non-empty argv")
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not isfinite(timeout)
            or timeout <= 0
        ):
            return CommandResult(
                False,
                -1,
                detail="timeout must be a positive finite number",
            )
        try:
            completed = subprocess.run(
                list(command),
                cwd=str(Path(cwd).resolve()),
                capture_output=True,
                text=True,
                shell=False,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                False,
                -1,
                stdout=_text(exc.stdout),
                stderr=_text(exc.stderr),
                timed_out=True,
                detail=f"timed out after {timeout:g}s",
            )
        except OSError as exc:
            return CommandResult(False, -1, stderr=str(exc), detail=str(exc))
        return CommandResult(
            completed.returncode == 0,
            completed.returncode,
            completed.stdout,
            completed.stderr,
            detail=completed.stderr.strip() if completed.returncode else "ok",
        )


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else value


class TestVerifier:
    """Convert bounded subprocess outcomes into workflow test receipts."""

    __test__ = False

    def __init__(
        self,
        executor: CommandExecutor | None = None,
        policy: TestCommandPolicy | None = None,
    ) -> None:
        self.executor = executor or SubprocessExecutor()
        self.policy = policy or TestCommandPolicy()

    def run(self, command: tuple[str, ...], cwd: str, timeout: float) -> TestResult:
        if not self.policy.allows(command):
            return TestResult(
                passed=False,
                returncode=-1,
                stderr="command refused by test policy",
            )
        result = self.executor.run(command, cwd, timeout)
        return TestResult(
            passed=result.ok,
            returncode=result.returncode,
            stdout=result.stdout[-4000:],
            stderr=result.stderr[-2000:],
            timed_out=result.timed_out,
        )
