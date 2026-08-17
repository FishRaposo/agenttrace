"""Safety-bounded issue-to-draft-PR orchestration."""

from __future__ import annotations

import uuid
from math import isfinite
from pathlib import Path
from typing import Callable, Protocol

from agenttrace.issue_pr.audit import AuditTrail
from agenttrace.issue_pr.commands import CommandResult, TestVerifier
from agenttrace.issue_pr.git import GuardedGit
from agenttrace.issue_pr.models import (
    ApprovalState,
    WorkflowRun,
    WorkflowStatus,
)
from agenttrace.issue_pr.protocols import (
    DraftPullRequestSink,
    IssueSource,
    PlanProvider,
    TestExecutor,
)
from agenttrace.issue_pr.safety import SafeEditor


class GitOperations(Protocol):
    def create_branch(self, branch: str) -> CommandResult: ...

    def commit(self, message: str, files: tuple[str, ...]) -> CommandResult: ...

    def push(self, branch: str, remote: str = "origin") -> CommandResult: ...

    def merge(self, branch: str) -> CommandResult: ...


class IssuePRWorkflow:
    """Run deterministic edits and stop before the sole draft-PR side effect."""

    def __init__(
        self,
        workspace: str | Path,
        issue_source: IssueSource,
        plan_provider: PlanProvider,
        pull_request_sink: DraftPullRequestSink,
        test_executor: TestExecutor | None = None,
        editor: SafeEditor | None = None,
        git: GitOperations | None = None,
        audit: AuditTrail | None = None,
        base_branch: str = "main",
        test_timeout: float = 60,
        run_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.issue_source = issue_source
        self.plan_provider = plan_provider
        self.pull_request_sink = pull_request_sink
        self.test_executor = test_executor or TestVerifier()
        self.editor = editor or SafeEditor(self.workspace)
        self.git = git or GuardedGit(self.workspace)
        self.audit = audit or AuditTrail()
        self.base_branch = base_branch
        if (
            isinstance(test_timeout, bool)
            or not isinstance(test_timeout, (int, float))
            or not isfinite(test_timeout)
            or test_timeout <= 0
        ):
            raise ValueError("test_timeout must be a positive finite number")
        self.test_timeout = test_timeout
        self.run_id_factory = run_id_factory or (lambda: uuid.uuid4().hex)

    def process(self, repository: str, issue_number: int) -> WorkflowRun:
        """Apply and verify a plan, then pause at explicit human approval."""
        issue = self.issue_source.get_issue(repository, issue_number)
        run = WorkflowRun(self.run_id_factory(), issue, WorkflowStatus.RUNNING)
        self.audit.record(
            "run_started",
            {"run_id": run.run_id, "repository": repository, "issue": issue_number},
        )
        self.audit.record("issue_fetched", {"run_id": run.run_id, "title": issue.title})
        try:
            plan = self.plan_provider.create_plan(issue)
            run.plan = plan
            self.audit.record(
                "plan_created",
                {
                    "run_id": run.run_id,
                    "summary": plan.summary,
                    "edits": len(plan.edits),
                },
            )

            branch = f"agent/fix-issue-{issue.number}"
            created = self.git.create_branch(branch)
            if not created.ok:
                return self._fail(run, f"branch creation refused: {created.detail}")
            run.branch = branch
            self.audit.record(
                "branch_created", {"run_id": run.run_id, "branch": branch}
            )

            edited = self.editor.apply(plan.edits)
            if not edited.ok:
                return self._fail(run, f"edit refused: {edited.reason}")
            run.changed_files = edited.changed_files
            self.audit.record(
                "edits_applied",
                {"run_id": run.run_id, "files": list(run.changed_files)},
            )

            committed = self.git.commit(
                f"fix: issue #{issue.number} - {issue.title[:60]}", run.changed_files
            )
            if not committed.ok:
                return self._fail(run, f"commit refused: {committed.detail}")
            self.audit.record(
                "changes_committed",
                {"run_id": run.run_id, "branch": branch},
            )

            tests = self.test_executor.run(
                plan.test_command, str(self.workspace), self.test_timeout
            )
            run.test_result = tests
            self.audit.record(
                "tests_completed",
                {
                    "run_id": run.run_id,
                    "passed": tests.passed,
                    "returncode": tests.returncode,
                    "timed_out": tests.timed_out,
                },
            )
            if not tests.passed:
                return self._fail(run, "tests failed")

            run.status = WorkflowStatus.AWAITING_APPROVAL
            run.approval_state = ApprovalState.REQUIRED
            self.audit.record("approval_required", {"run_id": run.run_id})
            return run
        except Exception as exc:
            return self._fail(run, f"{type(exc).__name__}: {exc}")

    def approve(self, run: WorkflowRun, actor: str = "human") -> WorkflowRun:
        """Publish a feature branch and invoke the draft-only PR sink."""
        if (
            run.status is not WorkflowStatus.AWAITING_APPROVAL
            or run.approval_state
            not in {ApprovalState.REQUIRED, ApprovalState.APPROVED}
        ):
            self.audit.record(
                "approval_refused",
                {"run_id": run.run_id, "status": run.status.value},
            )
            raise PermissionError("run is not awaiting approval")
        if run.test_result is None or not run.test_result.passed:
            raise PermissionError("passing tests are required before approval")
        if not run.branch or run.plan is None:
            raise PermissionError("run has no publishable branch or plan")

        if run.approval_state is ApprovalState.REQUIRED:
            run.approval_state = ApprovalState.APPROVED
            run.approved_by = actor
            self.audit.record("approved", {"run_id": run.run_id, "actor": actor})

        if not run.branch_pushed:
            pushed = self.git.push(run.branch)
            if not pushed.ok:
                return self._fail(run, f"push refused: {pushed.detail}")
            run.branch_pushed = True
            self.audit.record(
                "branch_pushed", {"run_id": run.run_id, "branch": run.branch}
            )

        title = f"fix: {run.issue.title}"
        body = self._pull_request_body(run)
        try:
            receipt = self.pull_request_sink.create_draft_pull_request(
                run.issue.repository,
                title,
                body,
                run.branch,
                self.base_branch,
                run.run_id,
            )
        except Exception as exc:
            run.error = f"draft PR creation failed: {type(exc).__name__}: {exc}"
            self.audit.record(
                "draft_pr_failed",
                {"run_id": run.run_id, "reason": run.error, "retryable": True},
            )
            return run
        run.draft_pull_request = receipt
        run.status = WorkflowStatus.COMPLETED
        run.error = None
        self.audit.record(
            "draft_pr_created",
            {"run_id": run.run_id, "url": receipt.url, "draft": True},
        )
        return run

    def _pull_request_body(self, run: WorkflowRun) -> str:
        files = ", ".join(run.changed_files) or "none"
        assert run.plan is not None
        return (
            f"Automated draft for issue #{run.issue.number}.\n\n"
            f"Plan: {run.plan.summary}\n\nFiles changed: {files}"
        )

    def _fail(self, run: WorkflowRun, reason: str) -> WorkflowRun:
        run.status = WorkflowStatus.FAILED
        run.error = reason
        self.audit.record("run_failed", {"run_id": run.run_id, "reason": reason})
        return run


IssuePRRun = WorkflowRun
