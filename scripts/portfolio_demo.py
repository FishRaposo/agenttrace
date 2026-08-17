"""Build a deterministic, credential-free AgentTrace evidence bundle."""

from __future__ import annotations

import hashlib
import json
import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agenttrace.issue_pr import (
    AgentTraceAuditSink,
    AuditTrail,
    DeterministicPlanProvider,
    Edit,
    FixPlan,
    GuardedGit,
    Issue,
    IssuePRRun,
    IssuePRWorkflow,
    RecordingDraftPullRequestSink,
    SafeEditor,
    StaticIssueSource,
    TestResult,
)
from agenttrace.issue_pr.commands import CommandResult
from app.internal.realtime import InMemoryPublisher
from app.internal.sampling import SamplingPolicy
from app.internal.vendor_core.pricing import calculate_cost
from app.services.audit import redact_metadata

try:
    from scripts.evidence_contract import MANIFEST_STATIC, REPORT_MARKDOWN
except ModuleNotFoundError:  # Direct execution: `python scripts/portfolio_demo.py`.
    from evidence_contract import MANIFEST_STATIC, REPORT_MARKDOWN


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _report() -> dict[str, Any]:
    sampling = SamplingPolicy(mode="head", rate=1.0).decide(
        trace_id="portfolio-trace", status="completed", duration_ms=42.0
    )
    event = {"channel": "traces", "type": "trace", "span_id": "portfolio-span"}
    observed = asyncio.run(_publish_once(event))
    if observed != event:
        raise RuntimeError("in-memory realtime publisher returned an unexpected event")
    return {
        "scenario": "offline-canonical-trace",
        "trace": {
            "trace_id": "portfolio-trace",
            "span_id": "portfolio-span",
            "span_type": "llm_call",
            "status": "completed",
            "model": "gpt-4o-mini",
            "prompt_tokens": 120,
            "completion_tokens": 40,
            "cost_usd": calculate_cost("gpt-4o-mini", 120, 40),
        },
        "otlp": {
            "resource": {"service.name": "agenttrace-portfolio"},
            "scope": {"name": "agenttrace.demo", "version": "1.0.0"},
            "events": ["cache.hit"],
            "links": ["linked-trace"],
        },
        "sampling": {
            "sampled": sampling.sampled,
            "reason": sampling.reason,
            "score": round(sampling.score, 12),
        },
        "realtime": event,
        "audit": redact_metadata(
            {"actor": "offline", "action": "trace.ingest", "api_key": "redacted"}
        ),
        "issue_pr": _issue_pr_report(),
    }


class _RecordingGit:
    """Deterministic git boundary for an evidence run with no subprocesses."""

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
        self.calls.append(("merge_refused", branch))
        return CommandResult(False, -1, detail="merge is disabled")


class _FixedTests:
    def __init__(self, passed: bool) -> None:
        self.passed = passed

    def run(self, command: tuple[str, ...], cwd: str, timeout: float) -> TestResult:
        del command, cwd, timeout
        return TestResult(
            passed=self.passed,
            returncode=0 if self.passed else 1,
            stdout="1 passed" if self.passed else "1 failed",
        )


class _TraceRecorder:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def add_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append(
            {
                "sequence": payload["sequence"],
                "action": event_type.removeprefix("issue_pr."),
                "details": _normalized_event_details(payload["details"]),
            }
        )


def _fixed_clock() -> datetime:
    return datetime(2026, 1, 1, tzinfo=timezone.utc)


def _event_payloads(audit: AuditTrail) -> list[dict[str, Any]]:
    return [
        {
            "sequence": event.sequence,
            "action": event.action,
            "details": _normalized_event_details(event.details),
        }
        for event in audit.events
    ]


def _normalized_event_details(details: dict[str, Any]) -> dict[str, Any]:
    """Remove generated identifiers and provider receipts from evidence hashes."""
    normalized = dict(details)
    if "run_id" in normalized:
        normalized["run_id"] = "[NORMALIZED_RUN_ID]"
    normalized.pop("url", None)
    return normalized


def _issue_pr_report() -> dict[str, Any]:
    """Exercise the absorbed SDK workflow without GitHub, LLMs, or real git."""
    with tempfile.TemporaryDirectory(prefix="agenttrace-evidence-") as workspace_raw:
        workspace = Path(workspace_raw)
        calculator = workspace / "calculator.py"
        original = "def divide(a, b):\n    return a / b\n"
        calculator.write_text(original, encoding="utf-8")

        issue = Issue(
            "owner/repo",
            101,
            "divide() crashes on zero",
            "calculator.py needs a guard; api_key=sk-evidence-secret",
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
        source = StaticIssueSource((issue,))
        planner = DeterministicPlanProvider({101: plan})
        editor = SafeEditor(workspace)
        traversal = editor.check_path("../outside.py")
        protected = GuardedGit(workspace).push("main")

        refusal_trace = _TraceRecorder()
        refusal_audit = AuditTrail(
            clock=_fixed_clock,
            sinks=(AgentTraceAuditSink(refusal_trace),),
        )
        refusal_audit.record(
            "path_refused",
            {"code": traversal.code, "reason": traversal.reason},
        )
        refusal_audit.record(
            "protected_branch_refused",
            {"reason": protected.detail},
        )

        failing_sink = RecordingDraftPullRequestSink()
        failing = IssuePRWorkflow(
            workspace=workspace,
            issue_source=source,
            plan_provider=planner,
            pull_request_sink=failing_sink,
            test_executor=_FixedTests(False),
            git=_RecordingGit(),
            audit=refusal_audit,
            run_id_factory=lambda: "issue-pr-failing-run",
        ).process("owner/repo", 101)
        calculator.write_text(original, encoding="utf-8")

        trace = _TraceRecorder()
        audit = AuditTrail(
            clock=_fixed_clock,
            sinks=(AgentTraceAuditSink(trace),),
        )
        git = _RecordingGit()
        sink = RecordingDraftPullRequestSink()
        workflow = IssuePRWorkflow(
            workspace=workspace,
            issue_source=source,
            plan_provider=planner,
            pull_request_sink=sink,
            test_executor=_FixedTests(True),
            git=git,
            audit=audit,
            run_id_factory=lambda: "issue-pr-success-run",
        )
        run = workflow.process("owner/repo", 101)
        approval_pause = run.status.value
        paused_run_json = run.to_json()
        run_replay = IssuePRRun.from_json(paused_run_json)
        approved = workflow.approve(run, actor="portfolio-owner")
        redaction_event = audit.record(
            "metadata_redacted",
            {
                "api_key": "sk-evidence-secret",
                "authorization": "Bearer evidence-token",
            },
        )
        audit_replay = AuditTrail.from_json(audit.to_json())
        replayed_events: list[object] = []
        audit_replay.replay((replayed_events.append,))
        audit_events = _event_payloads(audit)

        return {
            "issue": {
                "repository": issue.repository,
                "number": issue.number,
                "title": issue.title,
            },
            "plan": {"summary": plan.summary, "edit_count": len(plan.edits)},
            "refusals": {
                "path_traversal": traversal.code,
                "protected_branch": protected.detail,
            },
            "safe_edit": {"changed_files": list(approved.changed_files)},
            "test_transitions": [
                "passed"
                if failing.test_result and failing.test_result.passed
                else "failed",
                "passed"
                if approved.test_result and approved.test_result.passed
                else "failed",
            ],
            "failing_test_refusal": {
                "run_status": failing.status.value,
                "draft_pr_intents": len(failing_sink.requests),
            },
            "refusal_audit_events": _event_payloads(refusal_audit),
            "refusal_trace_events": refusal_trace.events,
            "approval_pause": approval_pause,
            "draft_pr_intent": {
                "draft": bool(sink.requests and sink.requests[0]["draft"]),
                "branch": approved.branch,
                "network_calls": 0,
            },
            "audit_events": audit_events,
            "trace_events": trace.events,
            "replay": {
                "matches_original": run_replay.to_json() == paused_run_json,
                "audit_event_count": len(replayed_events),
            },
            "redaction": {
                "api_key": redaction_event.details["api_key"],
                "authorization": redaction_event.details["authorization"],
            },
        }


async def _publish_once(event: dict[str, Any]) -> dict[str, Any]:
    """Exercise realtime publication without a network or external service."""
    publisher = InMemoryPublisher()
    stream = publisher.subscribe("traces")
    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    await publisher.publish("traces", event)
    observed = await pending
    await stream.aclose()
    await publisher.close()
    return observed


def build_bundle(output_dir: Path) -> dict[str, Any]:
    """Write a deterministic bundle and return its manifest."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = _report()
    report_bytes = _canonical(report)
    result_hash = hashlib.sha256(report_bytes).hexdigest()
    manifest = {
        **MANIFEST_STATIC,
        "result_hash": result_hash,
        "reproducibility_hash": result_hash,
    }
    (output_dir / "report.json").write_bytes(report_bytes + b"\n")
    (output_dir / "report.md").write_text(REPORT_MARKDOWN, encoding="utf-8")
    (output_dir / "manifest.json").write_bytes(_canonical(manifest) + b"\n")
    checksum_paths = ["manifest.json", "report.json", "report.md"]
    (output_dir / "checksums.sha256").write_text(
        "".join(f"{_sha256(output_dir / name)}  {name}\n" for name in checksum_paths),
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    build_bundle(root / "artifacts" / "portfolio" / "agenttrace-evidence")


if __name__ == "__main__":
    main()
