"""Offline portfolio evidence contract tests."""

import json

from scripts.portfolio_demo import build_bundle
from scripts.verify_portfolio_evidence import verify_bundle


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
