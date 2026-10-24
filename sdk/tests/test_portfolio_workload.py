"""Scenario outcomes reflect actual overlapping lifecycle events, not fixture counts."""

import asyncio
import uuid

import pytest
from agenttrace.portfolio import run_workload

from tests.test_concurrent_lifecycle import Recorder


@pytest.mark.parametrize(
    "scenario,completed,failed", [("incident", 17, 2), ("repaired", 18, 1)]
)
def test_workload_real_root_outcomes_and_cohort_metadata(scenario, completed, failed):
    recorder = Recorder()
    updates = []

    async def progress(count, run_id, outcome):
        updates.append((count, run_id, outcome))

    result = asyncio.run(run_workload(scenario, exporter=recorder, progress=progress))
    assert result["application_outcomes"] == {
        "completed": completed,
        "failed": failed,
        "cancelled": 1,
    }
    assert result["delivery"]["complete"]
    assert len(set(result["run_ids"])) == len(result["request_observations"]) == 20
    assert updates[-1][0] == 20
    finals = [run for run in recorder.runs if run["end_time"]]
    assert len(finals) == 20
    assert len([run for run in finals if run["status"] == "completed"]) == completed
    assert all(run["metadata"]["cohort_id"] == result["cohort_id"] for run in finals)
    assert len({span["id"] for span in recorder.spans}) == len(recorder.spans)


def test_tracing_disabled_has_no_telemetry_and_serial_benchmark_path():
    result = asyncio.run(run_workload("incident", tracing=False, concurrency=1))
    assert result["run_ids"] == [] and result["delivery"]["queued"] == 0
    assert result["application_outcomes"] == {
        "completed": 17,
        "failed": 2,
        "cancelled": 1,
    }
    assert len(result["request_observations"]) == 20


def test_invalid_scenario_never_starts():
    with pytest.raises(ValueError, match="Unknown"):
        asyncio.run(run_workload("arbitrary"))


def test_workload_correlation_ids_fit_the_collector_identifier_contract():
    """A cohort-prefixed string exceeds the collector's36-character column."""
    recorder = Recorder()
    asyncio.run(run_workload("incident", exporter=recorder))
    finals = [run for run in recorder.runs if run["end_time"]]
    assert len({run["correlation_id"] for run in finals}) == 20
    for run in finals:
        assert len(run["correlation_id"]) == 36
        assert str(uuid.UUID(run["correlation_id"])) == run["correlation_id"]
