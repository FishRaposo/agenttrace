"""Dependency-free data contracts for issue-to-draft-PR workflows."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping, Sequence


class WorkflowStatus(str, Enum):
    """Lifecycle states enforced by :class:`IssuePRWorkflow`."""

    CREATED = "created"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    FAILED = "failed"
    COMPLETED = "completed"


class ApprovalState(str, Enum):
    """Explicit human-approval state, separate from execution status."""

    NOT_REQUESTED = "not_requested"
    REQUIRED = "required"
    APPROVED = "approved"


@dataclass(frozen=True)
class Issue:
    """Provider-neutral issue data."""

    repository: str
    number: int
    title: str
    body: str = ""
    labels: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Issue:
        return cls(
            repository=str(value["repository"]),
            number=int(value["number"]),
            title=str(value["title"]),
            body=str(value.get("body", "")),
            labels=tuple(str(label) for label in value.get("labels", ())),
        )


@dataclass(frozen=True)
class Edit:
    """One exact, auditable replacement in a repository-relative file."""

    path: str
    find: str
    replace: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Edit:
        return cls(
            path=str(value["path"]),
            find=str(value["find"]),
            replace=str(value["replace"]),
        )


@dataclass(frozen=True)
class FixPlan:
    """Deterministic edits and the argv used to validate them."""

    summary: str
    edits: tuple[Edit, ...]
    test_command: tuple[str, ...] = ("python", "-m", "pytest", "-q")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> FixPlan:
        raw_edits = value.get("edits", ())
        return cls(
            summary=str(value["summary"]),
            edits=tuple(Edit.from_dict(edit) for edit in raw_edits),
            test_command=tuple(
                str(part)
                for part in value.get("test_command", ("python", "-m", "pytest", "-q"))
            ),
        )


@dataclass(frozen=True)
class TestResult:
    """Structured result from an injected test executor."""

    __test__ = False

    passed: bool
    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> TestResult:
        return cls(
            passed=_boolean(value["passed"], "test_result.passed"),
            returncode=int(value["returncode"]),
            stdout=str(value.get("stdout", "")),
            stderr=str(value.get("stderr", "")),
            timed_out=_boolean(value.get("timed_out", False), "test_result.timed_out"),
        )


@dataclass(frozen=True)
class DraftPullRequest:
    """Receipt returned by a draft-only pull-request sink."""

    url: str
    title: str
    head: str
    base: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> DraftPullRequest:
        return cls(
            url=str(value["url"]),
            title=str(value["title"]),
            head=str(value["head"]),
            base=str(value["base"]),
        )


@dataclass(frozen=True)
class AuditEvent:
    """One ordered, redacted workflow audit event."""

    sequence: int
    action: str
    details: dict[str, Any]
    timestamp: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> AuditEvent:
        details = value.get("details", {})
        if not isinstance(details, Mapping):
            raise ValueError("audit event details must be an object")
        return cls(
            sequence=int(value["sequence"]),
            action=str(value["action"]),
            details=dict(details),
            timestamp=str(value["timestamp"]),
        )


@dataclass
class WorkflowRun:
    """Serializable snapshot of one issue-to-draft-PR execution."""

    run_id: str
    issue: Issue
    status: WorkflowStatus = WorkflowStatus.CREATED
    plan: FixPlan | None = None
    branch: str | None = None
    branch_pushed: bool = False
    changed_files: tuple[str, ...] = ()
    test_result: TestResult | None = None
    approval_state: ApprovalState = ApprovalState.NOT_REQUESTED
    approved_by: str | None = None
    draft_pull_request: DraftPullRequest | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible representation."""
        return {
            "run_id": self.run_id,
            "issue": asdict(self.issue),
            "status": self.status.value,
            "plan": asdict(self.plan) if self.plan is not None else None,
            "branch": self.branch,
            "branch_pushed": self.branch_pushed,
            "changed_files": list(self.changed_files),
            "test_result": (
                asdict(self.test_result) if self.test_result is not None else None
            ),
            "approval_state": self.approval_state.value,
            "approved_by": self.approved_by,
            "draft_pull_request": (
                asdict(self.draft_pull_request)
                if self.draft_pull_request is not None
                else None
            ),
            "error": self.error,
        }

    def to_json(self) -> str:
        """Serialize the run deterministically for storage or replay."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> WorkflowRun:
        plan_value = value.get("plan")
        test_value = value.get("test_result")
        pr_value = value.get("draft_pull_request")
        return cls(
            run_id=str(value["run_id"]),
            issue=Issue.from_dict(_mapping(value["issue"], "issue")),
            status=WorkflowStatus(str(value["status"])),
            plan=(
                FixPlan.from_dict(_mapping(plan_value, "plan"))
                if plan_value is not None
                else None
            ),
            branch=str(value["branch"]) if value.get("branch") is not None else None,
            branch_pushed=_boolean(value.get("branch_pushed", False), "branch_pushed"),
            changed_files=tuple(
                str(path) for path in _sequence(value.get("changed_files", ()))
            ),
            test_result=(
                TestResult.from_dict(_mapping(test_value, "test_result"))
                if test_value is not None
                else None
            ),
            approval_state=ApprovalState(
                str(value.get("approval_state", ApprovalState.NOT_REQUESTED.value))
            ),
            approved_by=(
                str(value["approved_by"])
                if value.get("approved_by") is not None
                else None
            ),
            draft_pull_request=(
                DraftPullRequest.from_dict(_mapping(pr_value, "draft_pull_request"))
                if pr_value is not None
                else None
            ),
            error=str(value["error"]) if value.get("error") is not None else None,
        )

    @classmethod
    def from_json(cls, payload: str) -> WorkflowRun:
        """Restore a run produced by :meth:`to_json`."""
        value = json.loads(payload)
        return cls.from_dict(_mapping(value, "workflow run"))


IssuePRRun = WorkflowRun
IssuePREvent = AuditEvent


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _sequence(value: object) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("value must be an array")
    return value


def _boolean(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a boolean")
    return value
