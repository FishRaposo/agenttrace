"""Public contracts and serialization for the issue-to-draft-PR SDK."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from agenttrace.issue_pr import (
    ApprovalState,
    AuditEvent,
    AuditTrail,
    BranchGuard,
    DraftPullRequest,
    Edit,
    FixPlan,
    Issue,
    IssuePlanner,
    IssuePREvent,
    IssuePRRun,
    PullRequestSink,
    SandboxPolicy,
    TestResult,
    TestVerifier,
    WorkflowRun,
    WorkflowStatus,
    WorkspaceEditor,
)
from agenttrace.issue_pr.audit import AgentTraceAuditSink
from agenttrace.issue_pr.protocols import (
    DraftPullRequestSink,
    IssueSource,
    PlanProvider,
)
from agenttrace.issue_pr.protocols import (
    TestExecutor as _TestExecutor,
)


def test_dataclass_contracts_round_trip_as_json() -> None:
    issue = Issue(
        repository="owner/repo",
        number=101,
        title="Fix divide",
        body="calculator.py fails",
        labels=("bug",),
    )
    plan = FixPlan(
        summary="Guard division by zero",
        edits=(
            Edit("calculator.py", "return a / b", "return None if b == 0 else a / b"),
        ),
        test_command=("python", "-m", "pytest", "-q"),
    )
    run = WorkflowRun(
        run_id="run-101",
        issue=issue,
        status=WorkflowStatus.AWAITING_APPROVAL,
        plan=plan,
        branch="agent/fix-issue-101",
        changed_files=("calculator.py",),
        test_result=TestResult(True, 0, "1 passed", ""),
        approval_state=ApprovalState.REQUIRED,
    )

    payload = run.to_json()
    restored = WorkflowRun.from_json(payload)

    assert restored == run
    assert json.loads(payload)["status"] == "awaiting_approval"
    assert json.loads(payload)["approval_state"] == "required"


@pytest.mark.parametrize(
    ("path", "value"),
    [("branch_pushed", "false"), ("test_result.passed", "false")],
)
def test_run_deserialization_requires_real_json_booleans(path: str, value: str) -> None:
    run = WorkflowRun(
        run_id="run",
        issue=Issue("owner/repo", 1, "title"),
        test_result=TestResult(True, 0),
    )
    payload = json.loads(run.to_json())
    if path == "branch_pushed":
        payload["branch_pushed"] = value
    else:
        payload["test_result"]["passed"] = value

    with pytest.raises(ValueError, match="boolean"):
        WorkflowRun.from_json(json.dumps(payload))


def test_absorbed_public_contract_names_are_exposed() -> None:
    assert IssuePlanner is PlanProvider
    assert PullRequestSink is DraftPullRequestSink
    assert IssuePRRun is WorkflowRun
    assert IssuePREvent is AuditEvent
    assert ApprovalState.REQUIRED.value == "required"
    assert SandboxPolicy().blocked_globs
    assert WorkspaceEditor.__name__ == "SafeEditor"
    assert BranchGuard.__name__ == "GuardedGit"
    assert TestVerifier.__name__ == "TestVerifier"


def test_runtime_protocols_accept_structural_implementations() -> None:
    class Source:
        def get_issue(self, repository: str, number: int) -> Issue:
            return Issue(repository, number, "title")

    class Planner:
        def create_plan(self, issue: Issue) -> FixPlan:
            return FixPlan("summary", ())

    class Runner:
        def run(self, command: tuple[str, ...], cwd: str, timeout: float) -> TestResult:
            return TestResult(True, 0)

    class Sink:
        def create_draft_pull_request(
            self,
            repository: str,
            title: str,
            body: str,
            head: str,
            base: str,
            idempotency_key: str,
        ) -> DraftPullRequest:
            return DraftPullRequest("https://example.test/1", title, head, base)

    assert isinstance(Source(), IssueSource)
    assert isinstance(Planner(), PlanProvider)
    assert isinstance(Runner(), _TestExecutor)
    assert isinstance(Sink(), DraftPullRequestSink)


def test_audit_serialization_replay_order_and_recursive_redaction() -> None:
    seen: list[AuditEvent] = []
    fixed = datetime(2026, 8, 16, tzinfo=timezone.utc)
    trail = AuditTrail(sinks=[seen.append], clock=lambda: fixed)
    trail.record(
        "issue_fetched",
        {
            "authorization": "Bearer ghp_secret",
            "nested": {"api_key": "sk-secret", "safe": "visible"},
            "text": "token=ghp_abcdefghijklmnopqrstuvwxyz123456",
        },
    )
    trail.record("plan_created", {"target": "calculator.py"})

    payload = trail.to_json()
    restored = AuditTrail.from_json(payload)
    replayed: list[AuditEvent] = []
    restored.replay([replayed.append])

    assert [event.sequence for event in replayed] == [1, 2]
    assert [event.action for event in replayed] == ["issue_fetched", "plan_created"]
    assert replayed[0].details == {
        "authorization": "[REDACTED]",
        "nested": {"api_key": "[REDACTED]", "safe": "visible"},
        "text": "token=[REDACTED]",
    }


def test_deserialized_audit_is_redacted_before_replay() -> None:
    payload = json.dumps(
        [
            {
                "sequence": 1,
                "action": "loaded",
                "details": {"token": "ghp_untrustedserializedsecret"},
                "timestamp": "2026-08-16T00:00:00+00:00",
            }
        ]
    )

    restored = AuditTrail.from_json(payload)

    assert restored.events[0].details == {"token": "[REDACTED]"}


def test_audit_events_are_defensive_against_caller_and_sink_mutation() -> None:
    sink_events: list[AuditEvent] = []
    trail = AuditTrail(sinks=[sink_events.append])
    returned = trail.record("safe", {"nested": {"value": "visible"}})

    returned.details["token"] = "ghp_returnedsecret"
    sink_events[0].details["authorization"] = "Bearer sinksecret"
    exposed = trail.events[0]
    exposed.details["password"] = "caller-secret"

    serialized = json.loads(trail.to_json())
    replayed: list[AuditEvent] = []
    trail.replay([replayed.append])
    assert serialized[0]["details"] == {"nested": {"value": "visible"}}
    assert replayed[0].details == {"nested": {"value": "visible"}}

    seeded_event = AuditEvent(1, "seeded", {"safe": "yes"}, "2026-08-16T00:00:00Z")
    seeded = AuditTrail(events=[seeded_event])
    seeded_event.details["token"] = "ghp_seedsecret"
    assert seeded.events[0].details == {"safe": "yes"}


def test_agenttrace_sink_preserves_audit_event_order() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class RecordingTracer:
        def add_event(self, event_type: str, payload: dict[str, object]) -> None:
            calls.append((event_type, payload))

    trail = AuditTrail(sinks=[AgentTraceAuditSink(RecordingTracer())])
    trail.record("run_started", {"run_id": "one"})
    trail.record("approval_required", {"run_id": "one"})

    assert [name for name, _ in calls] == [
        "issue_pr.run_started",
        "issue_pr.approval_required",
    ]
    assert [payload["sequence"] for _, payload in calls] == [1, 2]
