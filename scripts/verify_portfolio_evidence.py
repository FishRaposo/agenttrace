"""Verify checksums and reproducibility of an AgentTrace evidence bundle."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_bundle(bundle_dir: Path) -> dict[str, Any]:
    bundle_dir = Path(bundle_dir)
    required = ["manifest.json", "report.json", "report.md", "checksums.sha256"]
    missing = [name for name in required if not (bundle_dir / name).is_file()]
    if missing:
        raise ValueError(f"missing evidence files: {', '.join(missing)}")
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
    for line in checksum_lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^/\\]+)", line)
        if match is None:
            raise ValueError("malformed checksum line")
        digest, name = match.groups()
        if _sha256(bundle_dir / name) != digest:
            raise ValueError(f"checksum mismatch: {name}")
    result_hash = hashlib.sha256(_canonical(report)).hexdigest()
    if manifest.get("result_hash") != result_hash:
        raise ValueError("result hash mismatch")
    if manifest.get("reproducibility_hash") != result_hash:
        raise ValueError("reproducibility hash mismatch")
    golden = (
        bundle_dir.parents[2]
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
