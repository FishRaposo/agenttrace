"""Verify checksums and reproducibility of an AgentTrace evidence bundle."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from scripts.evidence_contract import (
        EXPECTED_BUNDLE_FILES,
        MANIFEST_STATIC,
        REPORT_MARKDOWN,
    )
except ModuleNotFoundError:  # Direct execution from the repository root.
    from evidence_contract import (
        EXPECTED_BUNDLE_FILES,
        MANIFEST_STATIC,
        REPORT_MARKDOWN,
    )


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_bundle(bundle_dir: Path) -> dict[str, Any]:
    bundle_dir = Path(bundle_dir)
    required = list(EXPECTED_BUNDLE_FILES)
    missing = [name for name in required if not (bundle_dir / name).is_file()]
    if missing:
        raise ValueError(f"missing evidence files: {', '.join(missing)}")
    actual_files = sorted(
        path.relative_to(bundle_dir).as_posix()
        for path in bundle_dir.rglob("*")
        if path.is_file()
    )
    unexpected = sorted(set(actual_files) - set(required))
    if unexpected:
        raise ValueError(f"unexpected evidence files: {', '.join(unexpected)}")
    try:
        manifest = json.loads(
            (bundle_dir / "manifest.json").read_text(encoding="utf-8")
        )
        report = json.loads((bundle_dir / "report.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("malformed evidence manifest or report") from exc
    if not isinstance(manifest, dict) or not isinstance(report, dict):
        raise ValueError("manifest and report must be JSON objects")
    checksum_lines = (
        (bundle_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines()
    )
    if not checksum_lines:
        raise ValueError("checksums file is empty")
    checksum_names: list[str] = []
    for line in checksum_lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^/\\]+)", line)
        if match is None:
            raise ValueError("malformed checksum line")
        digest, name = match.groups()
        checksum_names.append(name)
        if name not in required[:-1]:
            raise ValueError(f"unexpected checksum target: {name}")
        if _sha256(bundle_dir / name) != digest:
            raise ValueError(f"checksum mismatch: {name}")
    if len(checksum_names) != len(set(checksum_names)) or set(checksum_names) != set(
        required[:-1]
    ):
        raise ValueError("checksum coverage must match the evidence files exactly")
    if (bundle_dir / "manifest.json").read_bytes() != _canonical(manifest) + b"\n":
        raise ValueError("manifest must use canonical JSON encoding")
    if (bundle_dir / "report.json").read_bytes() != _canonical(report) + b"\n":
        raise ValueError("report must use canonical JSON encoding")
    if (bundle_dir / "report.md").read_text(encoding="utf-8") != REPORT_MARKDOWN:
        raise ValueError("report markdown differs from the evidence contract")
    result_hash = hashlib.sha256(_canonical(report)).hexdigest()
    if manifest.get("result_hash") != result_hash:
        raise ValueError("result hash mismatch")
    if manifest.get("reproducibility_hash") != result_hash:
        raise ValueError("reproducibility hash mismatch")
    expected_manifest = {
        **MANIFEST_STATIC,
        "result_hash": result_hash,
        "reproducibility_hash": result_hash,
    }
    if manifest != expected_manifest:
        raise ValueError("manifest fields differ from the evidence contract")
    golden = (
        Path(__file__).resolve().parents[1]
        / "server"
        / "tests"
        / "fixtures"
        / "golden"
        / "portfolio-evidence.json"
    )
    if golden.is_file():
        expected = json.loads(golden.read_text(encoding="utf-8"))
        if report != expected:
            raise ValueError(
                "portfolio evidence differs from the committed golden fixture"
            )
    return manifest


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    bundle = root / "artifacts" / "portfolio" / "agenttrace-evidence"
    verify_bundle(bundle)
    print(f"verified AgentTrace evidence: {bundle}")


if __name__ == "__main__":
    main()
