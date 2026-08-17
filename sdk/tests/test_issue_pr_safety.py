"""Filesystem, git, and subprocess safety boundaries."""

from __future__ import annotations

import subprocess
from math import inf
from pathlib import Path

import pytest
from agenttrace.issue_pr import Edit
from agenttrace.issue_pr.commands import (
    CommandResult,
    SubprocessExecutor,
    TestVerifier,
)
from agenttrace.issue_pr.git import GuardedGit
from agenttrace.issue_pr.safety import SafeEditor


def test_safe_editor_allows_exact_edit_and_blocks_sensitive_paths(
    tmp_path: Path,
) -> None:
    source = tmp_path / "calculator.py"
    source.write_text("def divide(a, b):\n    return a / b\n", encoding="utf-8")
    editor = SafeEditor(tmp_path)

    result = editor.apply((Edit("calculator.py", "return a / b", "return a // b"),))

    assert result.ok
    assert result.changed_files == ("calculator.py",)
    assert "return a // b" in source.read_text(encoding="utf-8")
    assert not editor.check_path("../outside.py").allowed
    assert not editor.check_path(".github/workflows/ci.yml").allowed
    assert not editor.check_path(".env.production").allowed
    assert not editor.check_path("app/secrets/key.py").allowed
    assert not editor.check_path("pyproject.toml").allowed


def test_safe_editor_rejects_symlink_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    link = tmp_path / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        original_resolve = Path.resolve

        def resolve_as_symlink_escape(path: Path, strict: bool = False) -> Path:
            if path.name == "escape.py":
                return outside / "escape.py"
            return original_resolve(path, strict=strict)

        monkeypatch.setattr(Path, "resolve", resolve_as_symlink_escape)

    report = SafeEditor(tmp_path).check_path("linked/escape.py")

    assert not report.allowed
    assert report.code == "path_escape"


def test_safe_editor_validates_all_edits_before_writing(tmp_path: Path) -> None:
    source = tmp_path / "ok.py"
    source.write_text("old\n", encoding="utf-8")
    editor = SafeEditor(tmp_path)

    result = editor.apply(
        (
            Edit("ok.py", "old", "new"),
            Edit(".github/workflows/ci.yml", "x", "y"),
        )
    )

    assert not result.ok
    assert source.read_text(encoding="utf-8") == "old\n"


def test_safe_editor_requires_exactly_one_match(tmp_path: Path) -> None:
    source = tmp_path / "duplicate.py"
    source.write_text("needle\nneedle\n", encoding="utf-8")

    result = SafeEditor(tmp_path).apply((Edit("duplicate.py", "needle", "value"),))

    assert not result.ok
    assert "exactly once" in result.reason
    assert source.read_text(encoding="utf-8") == "needle\nneedle\n"


def test_subprocess_executor_uses_argv_shell_false_and_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["argv"] = argv
        captured.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = SubprocessExecutor().run(("python", "-V"), tmp_path, timeout=7.5)

    assert result.ok
    assert captured["argv"] == ["python", "-V"]
    assert captured["shell"] is False
    assert captured["timeout"] == 7.5


def test_subprocess_executor_reports_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(["python"], 1)

    monkeypatch.setattr(subprocess, "run", timeout)

    result = SubprocessExecutor().run(("python",), tmp_path, timeout=1)

    assert not result.ok
    assert result.timed_out
    assert result.returncode == -1


@pytest.mark.parametrize("timeout", [0, -1, inf, None])
def test_subprocess_executor_rejects_unbounded_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, timeout: float | None
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("subprocess must not run"),
    )

    result = SubprocessExecutor().run(
        ("python", "-V"),
        tmp_path,
        timeout=timeout,  # type: ignore[arg-type]
    )

    assert not result.ok
    assert "timeout" in result.detail


@pytest.mark.parametrize(
    "command",
    [
        ("git", "push", "origin", "main"),
        ("cmd.exe", "/c", "git push origin main"),
        ("python", "-c", "print('unsafe')"),
        ("python", "-m", "pytest", "../../outside"),
    ],
)
def test_default_test_verifier_refuses_planner_controlled_commands(
    tmp_path: Path, command: tuple[str, ...]
) -> None:
    class NeverRuns:
        def run(
            self, command: tuple[str, ...], cwd: str, timeout: float
        ) -> CommandResult:
            pytest.fail("refused command must not reach subprocess")

    result = TestVerifier(executor=NeverRuns()).run(command, str(tmp_path), 10)  # type: ignore[arg-type]

    assert not result.passed
    assert "policy" in result.stderr


def test_default_test_verifier_runs_exact_pytest_command(tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    class RecordsRun:
        def run(
            self, command: tuple[str, ...], cwd: str, timeout: float
        ) -> CommandResult:
            calls.append(command)
            return CommandResult(True, 0, "1 passed", "")

    result = TestVerifier(executor=RecordsRun()).run(  # type: ignore[arg-type]
        ("python", "-m", "pytest", "-q"), str(tmp_path), 10
    )

    assert result.passed
    assert calls == [("python", "-m", "pytest", "-q")]


class RecordingExecutor:
    def __init__(self, branch: str = "main") -> None:
        self.branch = branch
        self.commands: list[tuple[str, ...]] = []

    def run(
        self, command: tuple[str, ...], cwd: str | Path, timeout: float
    ) -> CommandResult:
        self.commands.append(command)
        if command[-3:] == ("rev-parse", "--abbrev-ref", "HEAD"):
            return CommandResult(True, 0, f"{self.branch}\n")
        return CommandResult(True, 0)


def test_guarded_git_refuses_protected_branch_push_commit_and_merge(
    tmp_path: Path,
) -> None:
    executor = RecordingExecutor(branch="main")
    git = GuardedGit(tmp_path, executor=executor)

    create = git.create_branch("main")
    commit = git.commit("unsafe")
    push = git.push("master")
    refspec_push = git.push("agent/fix:refs/heads/main")
    merge = git.merge("agent/fix-1")

    assert not create.ok and "protected" in create.detail
    assert not commit.ok and "protected" in commit.detail
    assert not push.ok and "protected" in push.detail
    assert not refspec_push.ok and "protected" in refspec_push.detail
    assert not merge.ok and "disabled" in merge.detail
    assert executor.commands == [("git", "rev-parse", "--abbrev-ref", "HEAD")]


@pytest.mark.parametrize(
    "branch", ["--all", "--force-with-lease=main", "HEAD", "@", "agent/fix:main"]
)
def test_guarded_git_refuses_options_symbolic_refs_and_refspecs(
    tmp_path: Path, branch: str
) -> None:
    executor = RecordingExecutor(branch="agent/fix-1")

    result = GuardedGit(tmp_path, executor=executor).push(branch)

    assert not result.ok
    assert executor.commands == []


@pytest.mark.parametrize("remote", ["--all", "--mirror", "-c", "origin\n--all"])
def test_guarded_git_refuses_option_or_control_character_remote(
    tmp_path: Path, remote: str
) -> None:
    executor = RecordingExecutor(branch="agent/fix-1")

    result = GuardedGit(tmp_path, executor=executor).push("agent/fix-1", remote=remote)

    assert not result.ok
    assert executor.commands == []


def test_guarded_git_allows_only_feature_branch_commands(tmp_path: Path) -> None:
    executor = RecordingExecutor(branch="agent/fix-1")
    git = GuardedGit(tmp_path, executor=executor)

    assert git.create_branch("agent/fix-2").ok
    assert git.commit("fix", ("calculator.py",)).ok
    assert git.push("agent/fix-2").ok

    assert ("git", "switch", "-c", "agent/fix-2") in executor.commands
    assert ("git", "add", "--", "calculator.py") in executor.commands
    assert ("git", "push", "--", "origin", "agent/fix-2") in executor.commands
