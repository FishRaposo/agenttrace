"""Structural ports used by the dependency-free issue/PR workflow."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from agenttrace.issue_pr.models import DraftPullRequest, FixPlan, Issue, TestResult


@runtime_checkable
class IssueSource(Protocol):
    """Fetch issues without binding the SDK to a hosting provider."""

    def get_issue(self, repository: str, number: int) -> Issue: ...


@runtime_checkable
class PlanProvider(Protocol):
    """Create a deterministic, structured fix plan."""

    def create_plan(self, issue: Issue) -> FixPlan: ...


@runtime_checkable
class TestExecutor(Protocol):
    """Execute a test argv within a bounded workspace."""

    def run(self, command: tuple[str, ...], cwd: str, timeout: float) -> TestResult: ...


@runtime_checkable
class DraftPullRequestSink(Protocol):
    """Create draft pull requests only; ready/merge APIs are intentionally absent."""

    def create_draft_pull_request(
        self,
        repository: str,
        title: str,
        body: str,
        head: str,
        base: str,
        idempotency_key: str,
    ) -> DraftPullRequest: ...


IssuePlanner = PlanProvider
PullRequestSink = DraftPullRequestSink
