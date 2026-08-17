"""Deterministic offline adapters for tests, examples, and replay."""

from __future__ import annotations

from typing import Mapping, Sequence

from agenttrace.issue_pr.models import DraftPullRequest, FixPlan, Issue


class StaticIssueSource:
    """Return issues from an immutable in-process lookup."""

    def __init__(self, issues: Sequence[Issue]) -> None:
        self._issues = {(issue.repository, issue.number): issue for issue in issues}

    def get_issue(self, repository: str, number: int) -> Issue:
        try:
            return self._issues[(repository, number)]
        except KeyError as exc:
            raise KeyError(f"unknown issue {repository}#{number}") from exc


class DeterministicPlanProvider:
    """Return pre-approved structured plans keyed by issue number."""

    def __init__(self, plans: Mapping[int, FixPlan]) -> None:
        self._plans = dict(plans)

    def create_plan(self, issue: Issue) -> FixPlan:
        try:
            return self._plans[issue.number]
        except KeyError as exc:
            raise KeyError(f"no plan for issue #{issue.number}") from exc


class RecordingDraftPullRequestSink:
    """Draft-only sink that records calls and returns deterministic URLs."""

    def __init__(self, base_url: str = "https://example.test") -> None:
        self.base_url = base_url.rstrip("/")
        self.requests: list[dict[str, object]] = []
        self._receipts: dict[str, DraftPullRequest] = {}

    def create_draft_pull_request(
        self,
        repository: str,
        title: str,
        body: str,
        head: str,
        base: str,
        idempotency_key: str,
    ) -> DraftPullRequest:
        existing = self._receipts.get(idempotency_key)
        if existing is not None:
            return existing
        request: dict[str, object] = {
            "repository": repository,
            "title": title,
            "body": body,
            "head": head,
            "base": base,
            "draft": True,
            "idempotency_key": idempotency_key,
        }
        self.requests.append(request)
        url = f"{self.base_url}/{repository}/pull/{len(self.requests)}"
        receipt = DraftPullRequest(url, title, head, base)
        self._receipts[idempotency_key] = receipt
        return receipt
