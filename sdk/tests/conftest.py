"""Shared test fixtures for the SDK test suite."""

from __future__ import annotations

import os

import pytest
from agenttrace.exporters.jsonl import JSONLExporter
from agenttrace.tracer import Tracer


@pytest.fixture
def tracer() -> Tracer:
    """Create a fresh Tracer instance for testing."""
    return Tracer()


@pytest.fixture
def jsonl_path(tmp_path: os.PathLike) -> str:
    """Create a temporary JSONL file path for testing.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        Path to the temporary JSONL file.
    """
    return str(tmp_path / "test_traces.jsonl")


@pytest.fixture
def tracer_with_jsonl(tracer: Tracer, jsonl_path: str) -> Tracer:
    """Create a Tracer with a JSONLExporter for testing.

    Args:
        tracer: Fresh Tracer instance.
        jsonl_path: Path to temporary JSONL file.

    Returns:
        Tracer configured with JSONL exporter.
    """
    exporter = JSONLExporter(path=jsonl_path, buffer_size=1)
    tracer.set_exporter(exporter)
    return tracer
