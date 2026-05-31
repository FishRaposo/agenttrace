"""Tests for the exporter implementations."""

from __future__ import annotations

import json
import os
from typing import Any

from agenttrace.exporters.jsonl import JSONLExporter
from agenttrace.exporters.api_exporter import APIExporter


class TestJSONLExporter:
    """Tests for the JSONL file exporter."""

    def test_export_run_creates_file(self, tmp_path: os.PathLike) -> None:
        path = str(tmp_path / "test.jsonl")
        exporter = JSONLExporter(path=path, buffer_size=1)
        exporter.export_run({"id": "run-1", "name": "test"})
        exporter.flush()

        assert os.path.exists(path)

    def test_export_span_writes_data(self, tmp_path: os.PathLike) -> None:
        path = str(tmp_path / "test.jsonl")
        exporter = JSONLExporter(path=path, buffer_size=1)
        exporter.export_span({"id": "span-1", "name": "test_span"})
        exporter.flush()

        with open(path, "r") as f:
            line = f.readline()
        data = json.loads(line)
        assert data["type"] == "span"
        assert data["data"]["id"] == "span-1"

    def test_buffering_delays_write(self, tmp_path: os.PathLike) -> None:
        path = str(tmp_path / "test.jsonl")
        exporter = JSONLExporter(path=path, buffer_size=5)
        exporter.export_run({"id": "run-1"})

        if os.path.exists(path):
            with open(path, "r") as f:
                assert f.read() == ""
        else:
            pass

        exporter.flush()
        assert os.path.exists(path)

    def test_multiple_entries(self, tmp_path: os.PathLike) -> None:
        path = str(tmp_path / "test.jsonl")
        exporter = JSONLExporter(path=path, buffer_size=1)
        exporter.export_run({"id": "run-1"})
        exporter.export_span({"id": "span-1"})
        exporter.export_span({"id": "span-2"})
        exporter.flush()

        with open(path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 3

    def test_creates_parent_directory(self, tmp_path: os.PathLike) -> None:
        path = str(tmp_path / "subdir" / "nested" / "test.jsonl")
        exporter = JSONLExporter(path=path, buffer_size=1)
        exporter.export_run({"id": "run-1"})
        exporter.flush()

        assert os.path.exists(path)


class TestAPIExporter:
    """Tests for the HTTP API exporter."""

    def test_buffering(self) -> None:
        exporter = APIExporter(
            endpoint="http://localhost:9999/api/traces",
            buffer_size=10,
        )
        exporter.export_run({"id": "run-1"})
        exporter.export_span({"id": "span-1"})

        assert len(exporter._run_buffer) == 1
        assert len(exporter._span_buffer) == 1

    def test_flush_clears_buffer(self) -> None:
        exporter = APIExporter(
            endpoint="http://localhost:9999/api/traces",
            buffer_size=100,
        )
        exporter.export_run({"id": "run-1"})
        exporter.flush()

        assert len(exporter._run_buffer) == 0
        assert len(exporter._span_buffer) == 0

    def test_flush_posts_runs_and_spans_to_explicit_api_paths(self) -> None:
        sent: list[tuple[str, dict[str, Any]]] = []
        exporter = APIExporter(endpoint="http://trace.test/api/traces")
        exporter._send_request = lambda url, data: sent.append((url, data)) or True  # type: ignore[method-assign]

        exporter.export_run({"id": "run-1", "name": "test"})
        exporter.export_span({"id": "span-1", "run_id": "run-1", "name": "call"})
        exporter.flush()

        assert sent == [
            ("http://trace.test/api/runs", {"id": "run-1", "name": "test"}),
            (
                "http://trace.test/api/traces",
                {"span_id": "span-1", "run_id": "run-1", "name": "call"},
            ),
        ]

    def test_endpoint_can_be_configured_as_api_base_url(self) -> None:
        sent: list[tuple[str, dict[str, Any]]] = []
        exporter = APIExporter(endpoint="http://trace.test/api")
        exporter._send_request = lambda url, data: sent.append((url, data)) or True  # type: ignore[method-assign]

        exporter.export_run({"id": "run-1", "name": "test"})
        exporter.export_span({"id": "span-1", "run_id": "run-1", "name": "call"})
        exporter.flush()

        assert sent[0][0] == "http://trace.test/api/runs"
        assert sent[1][0] == "http://trace.test/api/traces"
