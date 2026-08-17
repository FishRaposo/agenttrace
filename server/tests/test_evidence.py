"""Offline portfolio evidence contract tests."""

import hashlib
import json
from pathlib import Path

import pytest

from scripts.portfolio_demo import build_bundle
from scripts.verify_portfolio_evidence import verify_bundle


def _rewrite_checksum(bundle, name: str) -> None:
    checksum_file = bundle / "checksums.sha256"
    lines = checksum_file.read_text(encoding="utf-8").splitlines()
    digest = hashlib.sha256((bundle / name).read_bytes()).hexdigest()
    checksum_file.write_text(
        "\n".join(
            f"{digest}  {name}" if line.endswith(f"  {name}") else line
            for line in lines
        )
        + "\n",
        encoding="utf-8",
    )


def test_identical_evidence_runs_have_the_same_reproducibility_hash(tmp_path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    build_bundle(first)
    build_bundle(second)

    first_manifest = json.loads((first / "manifest.json").read_text())
    second_manifest = json.loads((second / "manifest.json").read_text())
    assert (
        first_manifest["reproducibility_hash"]
        == second_manifest["reproducibility_hash"]
    )
    assert (first / "report.json").read_bytes() == (second / "report.json").read_bytes()


def test_evidence_covers_dependency_free_issue_to_draft_pr_workflow(tmp_path) -> None:
    build_bundle(tmp_path)

    report = json.loads((tmp_path / "report.json").read_text())
    scenario = report["issue_pr"]

    assert scenario["issue"]["number"] == 101
    assert scenario["plan"]["summary"] == "Guard zero division"
    assert scenario["refusals"] == {
        "path_traversal": "path_escape",
        "protected_branch": "refusing to push protected branch 'main'",
    }
    assert scenario["safe_edit"]["changed_files"] == ["calculator.py"]
    assert scenario["test_transitions"] == ["failed", "passed"]
    assert scenario["failing_test_refusal"] == {
        "run_status": "failed",
        "draft_pr_intents": 0,
    }
    assert scenario["refusal_trace_events"] == scenario["refusal_audit_events"]
    refusal_actions = [event["action"] for event in scenario["refusal_audit_events"]]
    assert refusal_actions[:2] == ["path_refused", "protected_branch_refused"]
    assert refusal_actions[-2:] == ["tests_completed", "run_failed"]
    assert scenario["refusal_audit_events"][-2]["details"]["passed"] is False
    assert [event["sequence"] for event in scenario["refusal_audit_events"]] == list(
        range(1, len(scenario["refusal_audit_events"]) + 1)
    )
    assert scenario["approval_pause"] == "awaiting_approval"
    assert scenario["draft_pr_intent"]["draft"] is True
    assert scenario["draft_pr_intent"]["network_calls"] == 0
    assert scenario["replay"]["matches_original"] is True
    assert scenario["redaction"]["api_key"] == "[REDACTED]"
    assert scenario["trace_events"] == scenario["audit_events"]
    assert [event["sequence"] for event in scenario["audit_events"]] == list(
        range(1, len(scenario["audit_events"]) + 1)
    )


def test_evidence_verifier_rejects_tampering(tmp_path) -> None:
    build_bundle(tmp_path)
    report = tmp_path / "report.json"
    report.write_text(report.read_text().replace("agenttrace", "tampered"))

    try:
        verify_bundle(tmp_path)
    except ValueError as exc:
        assert "checksum" in str(exc).lower()
    else:
        raise AssertionError("tampered evidence should fail verification")


def test_evidence_verifier_rejects_missing_and_malformed_files(tmp_path) -> None:
    build_bundle(tmp_path)
    (tmp_path / "report.json").unlink()
    try:
        verify_bundle(tmp_path)
    except ValueError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("missing evidence should fail verification")

    build_bundle(tmp_path)
    (tmp_path / "checksums.sha256").write_text("not-a-checksum\n")
    try:
        verify_bundle(tmp_path)
    except ValueError as exc:
        assert "malformed checksum" in str(exc)
    else:
        raise AssertionError("malformed checksums should fail verification")


@pytest.mark.parametrize("extra_name", ["extra.json", "nested/extra.json"])
def test_evidence_verifier_rejects_extra_files(tmp_path, extra_name: str) -> None:
    build_bundle(tmp_path)
    extra = tmp_path / Path(extra_name)
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unexpected evidence files"):
        verify_bundle(tmp_path)


def test_evidence_verifier_rejects_malformed_json(tmp_path) -> None:
    build_bundle(tmp_path)
    (tmp_path / "manifest.json").write_text("{not-json", encoding="utf-8")

    with pytest.raises(ValueError, match="malformed evidence"):
        verify_bundle(tmp_path)


def test_evidence_verifier_requires_exact_checksum_coverage(tmp_path) -> None:
    build_bundle(tmp_path)
    checksums = (tmp_path / "checksums.sha256").read_text(encoding="utf-8")
    (tmp_path / "checksums.sha256").write_text(
        "\n".join(checksums.splitlines()[:-1]) + "\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="checksum coverage"):
        verify_bundle(tmp_path)


def test_evidence_verifier_rejects_self_consistent_markdown_tamper(tmp_path) -> None:
    build_bundle(tmp_path)
    report = tmp_path / "report.md"
    report.write_text(report.read_text() + "tampered\n", encoding="utf-8")
    _rewrite_checksum(tmp_path, "report.md")

    with pytest.raises(ValueError, match="report markdown"):
        verify_bundle(tmp_path)


def test_evidence_verifier_requires_canonical_json_bytes(tmp_path) -> None:
    build_bundle(tmp_path)
    manifest = tmp_path / "manifest.json"
    value = json.loads(manifest.read_text(encoding="utf-8"))
    manifest.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    _rewrite_checksum(tmp_path, "manifest.json")

    with pytest.raises(ValueError, match="canonical JSON"):
        verify_bundle(tmp_path)
