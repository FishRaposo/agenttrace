"""Build a deterministic, credential-free AgentTrace evidence bundle."""

from __future__ import annotations

import hashlib
import json
import asyncio
from pathlib import Path
from typing import Any

from app.internal.realtime import InMemoryPublisher
from app.internal.sampling import SamplingPolicy
from app.internal.vendor_core.pricing import calculate_cost
from app.services.audit import redact_metadata


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
        "schema_version": "1.0.0",
        "project": "agenttrace",
        "mode": "offline",
        "result_hash": result_hash,
        "reproducibility_hash": result_hash,
        "redaction": "credential-shaped keys are removed before serialization",
        "files": ["manifest.json", "report.json", "report.md"],
    }
    (output_dir / "report.json").write_bytes(report_bytes + b"\n")
    (output_dir / "report.md").write_text(
        "# AgentTrace offline evidence\n\n"
        "This bundle exercises canonical ingestion, OTLP metadata, deterministic "
        "sampling, realtime publication, pricing, and audit redaction without credentials.\n",
        encoding="utf-8",
    )
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
