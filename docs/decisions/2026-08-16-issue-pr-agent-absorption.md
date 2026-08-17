# Issue-to-draft-PR safety absorption

Date: 2026-08-16

## Decision

Absorb the reusable, safety-bounded issue-to-draft-PR workflow from
`FishRaposo/github-issue-pr-agent@01a2404ecf2f6f2cea5ea873c37b63ed1b1dde20`
into the dependency-free AgentTrace SDK as `agenttrace.issue_pr`.

The implementation uses only Python's standard library and existing AgentTrace
SDK primitives. It adds no collector routes, top-level SDK exports, hosted
workflow, credential requirement, or external runtime dependency. Offline
adapters are deterministic and in-process; processing stops at
`awaiting_approval`; the only publish boundary is a draft-only sink.

## Source mapping

| Source module | AgentTrace destination |
| --- | --- |
| `editor.py` | `issue_pr.safety.SandboxPolicy`, `SafeEditor`, and `WorkspaceEditor` |
| `git_ops.py` | `issue_pr.git.BranchGuard` / `GuardedGit` |
| `test_runner.py` | `issue_pr.commands.TestVerifier` and bounded shell-free executor |
| `agent.py`, `planner.py` | `issue_pr.workflow.IssuePRWorkflow`, protocols, and deterministic planner |
| `audit.py`, `store.py` | `issue_pr.audit.AuditTrail`, `AgentTraceAuditSink`, and replay contracts |
| `github.py` | provider protocols plus `StaticIssueSource` and draft-only recording sink |
| `config.py`, `errors.py` | SDK-owned dataclasses, policies, validation, and standard exceptions |

## Preserved contracts

- existing AgentTrace spans, costs, exporters, collector routes, response keys,
  and dashboard behavior are unchanged;
- issue/plan/run/event serialization is deterministic and replayable;
- file writes remain workspace-contained with allow/block policies and symlink
  escape rejection;
- Git guards reject protected branches, unsafe refs/remotes, and every merge;
- tests use exact argv, `shell=False`, finite timeouts, and structured results;
- a passing run pauses for explicit approval before draft-only intent;
- audit events are append-only, ordered, recursively redacted, and forwardable
  into AgentTrace.

## Rejected alternatives

- **Restore the source product as a second standalone service.** Rejected because
  it duplicates the observability/approval narrative and retains unnecessary
  server and infrastructure dependencies.
- **Import or vendor the source `shared_core` dependency.** Rejected because the
  SDK must remain independently installable and dependency-free.
- **Add collector routes or real provider adapters now.** Rejected because GitHub,
  LLM planning, PostgreSQL, Redis, Celery, GitPython, and PyGithub are optional
  integration surfaces, not offline proof.
- **Copy the source persistence layer.** Rejected in favor of AgentTrace event
  emission and deterministic run/audit serialization.

The original repository and Git history remain the lineage reference. Its local
portfolio-queue copy is governed by the hub absorption receipt and owner QA gate.
