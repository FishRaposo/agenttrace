"""Deterministic issue-to-draft-PR workflow tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from agenttrace.issue_pr import (
    ApprovalState,
    AuditTrail,
    DeterministicPlanProvider,
    DraftPullRequest,
    Edit,
    FixPlan,
    Issue,
    IssuePRWorkflow,
    RecordingDraftPullRequestSink,
    StaticIssueSource,
    TestResult,
    WorkflowStatus,
)
from agenttrace.issue_pr.commands import CommandResult


class FakeGit:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def create_branch(self, branch: str) -> CommandResult:
        self.calls.append(("create_branch", branch))
        return CommandResult(True, 0)

    def commit(self, message: str, files: tuple[str, ...]) -> CommandResult:
        self.calls.append(("commit", files))
        return CommandResult(True, 0)

    def push(self, branch: str, remote: str = "origin") -> CommandResult:
        self.calls.append(("push", branch))
        return CommandResult(True, 0)

    def merge(self, branch: str) -> CommandResult:
        raise AssertionError("workflow must never merge")


class PassingTests:
    def run(self, command: tuple[str, ...], cwd: str, timeout: float) -> TestResult:
        return TestResult(True, 0, "1 passed", "")


class FailsOnceDraftSink(RecordingDraftPullRequestSink):
    def __init__(self) -> None:
        super().__init__()
        self.attempts = 0

    def create_draft_pull_request(
        self,
        repository: str,
        title: str,
        body: str,
        head: str,
        base: str,
        idempotency_key: str,
    ) -> DraftPullRequest:
        self.attempts += 1
        receipt = super().create_draft_pull_request(
            repository, title, body, head, base, idempotency_key
        )
        if self.attempts == 1:
            raise RuntimeError("sink unavailable")
        return receipt


def _workflow(
    tmp_path: Path,
) -> tuple[IssuePRWorkflow, FakeGit, RecordingDraftPullRequestSink]:
    (tmp_path / "calculator.py").write_text(
        "def divide(a, b):\n    return a / b\n", encoding="utf-8"
    )
    issue = Issue(
        "owner/repo",
        101,
        "divide() crashes on zero",
        "calculator.py needs a guard",
        ("bug",),
    )
    plan = FixPlan(
        "Guard zero division",
        (
            Edit(
                "calculator.py",
                "    return a / b",
                "    return None if b == 0 else a / b",
            ),
        ),
        ("python", "-m", "pytest", "-q"),
    )
    git = FakeGit()
    sink = RecordingDraftPullRequestSink()
    workflow = IssuePRWorkflow(
        workspace=tmp_path,
        issue_source=StaticIssueSource((issue,)),
        plan_provider=DeterministicPlanProvider({101: plan}),
        test_executor=PassingTests(),
        pull_request_sink=sink,
        git=git,
        audit=AuditTrail(),
        run_id_factory=lambda: "run-101",
    )
    return workflow, git, sink


def test_deterministic_workflow_pauses_before_approval(tmp_path: Path) -> None:
    workflow, git, sink = _workflow(tmp_path)

    run = workflow.process("owner/repo", 101)

    assert run.status is WorkflowStatus.AWAITING_APPROVAL
    assert run.changed_files == ("calculator.py",)
    assert run.test_result and run.test_result.passed
    assert run.draft_pull_request is None
    assert sink.requests == []
    assert git.calls == [
        ("create_branch", "agent/fix-issue-101"),
        ("commit", ("calculator.py",)),
    ]
    assert [event.action for event in workflow.audit.events] == [
        "run_started",
        "issue_fetched",
        "plan_created",
        "branch_created",
        "edits_applied",
        "changes_committed",
        "tests_completed",
        "approval_required",
    ]


def test_approval_pushes_feature_branch_and_uses_draft_only_sink(
    tmp_path: Path,
) -> None:
    workflow, git, sink = _workflow(tmp_path)
    run = workflow.process("owner/repo", 101)

    approved = workflow.approve(run, actor="human")

    assert approved.status is WorkflowStatus.COMPLETED
    assert approved.approved_by == "human"
    assert approved.draft_pull_request == DraftPullRequest(
        "https://example.test/owner/repo/pull/1",
        "fix: divide() crashes on zero",
        "agent/fix-issue-101",
        "main",
    )
    assert git.calls[-1] == ("push", "agent/fix-issue-101")
    assert len(sink.requests) == 1
    assert sink.requests[0]["draft"] is True
    assert [event.action for event in workflow.audit.events][-3:] == [
        "approved",
        "branch_pushed",
        "draft_pr_created",
    ]


def test_non_approved_or_failing_run_cannot_create_pr(tmp_path: Path) -> None:
    workflow, _git, sink = _workflow(tmp_path)
    run = workflow.process("owner/repo", 101)
    run.status = WorkflowStatus.FAILED

    with pytest.raises(PermissionError, match="awaiting approval"):
        workflow.approve(run)

    assert sink.requests == []


def test_workflow_rejects_blocked_edit_before_git_or_tests(tmp_path: Path) -> None:
    workflow, git, sink = _workflow(tmp_path)
    workflow.plan_provider = DeterministicPlanProvider(
        {
            101: FixPlan(
                "tamper with CI",
                (Edit(".github/workflows/ci.yml", "x", "y"),),
            )
        }
    )

    run = workflow.process("owner/repo", 101)

    assert run.status is WorkflowStatus.FAILED
    assert "blocked" in (run.error or "").lower()
    assert git.calls == [("create_branch", "agent/fix-issue-101")]
    assert sink.requests == []
    assert workflow.audit.events[-1].action == "run_failed"


def test_workflow_refuses_empty_plan_instead_of_staging_workspace(
    tmp_path: Path,
) -> None:
    workflow, git, sink = _workflow(tmp_path)
    workflow.plan_provider = DeterministicPlanProvider({101: FixPlan("no-op", ())})

    run = workflow.process("owner/repo", 101)

    assert run.status is WorkflowStatus.FAILED
    assert "no edits" in (run.error or "").lower()
    assert git.calls == [("create_branch", "agent/fix-issue-101")]
    assert sink.requests == []


def test_draft_sink_failure_is_audited_and_retry_does_not_repush(
    tmp_path: Path,
) -> None:
    workflow, git, _sink = _workflow(tmp_path)
    sink = FailsOnceDraftSink()
    workflow.pull_request_sink = sink
    run = workflow.process("owner/repo", 101)

    first = workflow.approve(run)

    assert first.status is WorkflowStatus.AWAITING_APPROVAL
    assert first.approval_state is ApprovalState.APPROVED
    assert first.branch_pushed is True
    assert "sink unavailable" in (first.error or "")
    assert workflow.audit.events[-1].action == "draft_pr_failed"

    retried = workflow.approve(first)

    assert retried.status is WorkflowStatus.COMPLETED
    assert retried.error is None
    assert len([call for call in git.calls if call[0] == "push"]) == 1
    assert sink.attempts == 2
    assert len(sink.requests) == 1
    assert sink.requests[0]["idempotency_key"] == "run-101"


@pytest.mark.parametrize("timeout", [0, -1, float("inf")])
def test_workflow_rejects_unbounded_test_timeout(
    tmp_path: Path, timeout: float
) -> None:
    workflow, _git, _sink = _workflow(tmp_path)

    with pytest.raises(ValueError, match="test_timeout"):
        IssuePRWorkflow(
            workspace=tmp_path,
            issue_source=workflow.issue_source,
            plan_provider=workflow.plan_provider,
            test_executor=workflow.test_executor,
            pull_request_sink=workflow.pull_request_sink,
            git=workflow.git,
            test_timeout=timeout,
        )
