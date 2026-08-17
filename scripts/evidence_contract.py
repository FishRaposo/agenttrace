"""Stable constants shared by AgentTrace evidence generation and verification."""

from __future__ import annotations

EXPECTED_BUNDLE_FILES = (
    "manifest.json",
    "report.json",
    "report.md",
    "checksums.sha256",
)

REPORT_MARKDOWN = (
    "# AgentTrace offline evidence\n\n"
    "This bundle exercises canonical ingestion, OTLP metadata, deterministic "
    "sampling, realtime publication, pricing, audit redaction, and the "
    "safety-bounded issue-to-draft-PR workflow without credentials or network access.\n"
)

MANIFEST_STATIC = {
    "schema_version": "1.1.0",
    "project": "agenttrace",
    "mode": "offline",
    "redaction": "credential-shaped keys are removed before serialization",
    "files": ["manifest.json", "report.json", "report.md"],
}
