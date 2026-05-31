"""Example: Multi-agent workflow with distributed correlation ID.

Two agents (researcher + summarizer) share the same correlation_id so
their traces appear under a single distributed run in the dashboard.

Usage:
    AGENTTRACE_API_URL=http://localhost:8000/api python examples/multi_agent_demo.py
"""

from __future__ import annotations

import os
import time
import uuid

os.environ.setdefault("AGENTTRACE_LLM_MODE", "sim")

from agenttrace import HybridLLMClient, Tracer
from agenttrace.exporters.api_exporter import APIExporter


def researcher_agent(tracer: Tracer, correlation_id: str, topic: str) -> str:
    """Agent 1: researches a topic."""
    with tracer.start_run(
        name="researcher",
        correlation_id=correlation_id,
        metadata={"workflow_id": "multi-agent-pipeline", "agent": "researcher"},
    ) as run:
        client = HybridLLMClient(mode="sim", tracer=tracer)
        response = client.chat(
            provider="openai",
            model="gpt-4",
            messages=[{"role": "user", "content": f"Research this topic: {topic}"}],
        )
        print(f"[researcher] run={run.id} cost=${response.total_tokens * 0.00001:.4f}")
        time.sleep(0.05)
        return response.content


def summarizer_agent(tracer: Tracer, correlation_id: str, research: str) -> str:
    """Agent 2: summarizes research output."""
    with tracer.start_run(
        name="summarizer",
        correlation_id=correlation_id,
        metadata={"workflow_id": "multi-agent-pipeline", "agent": "summarizer"},
    ) as run:
        client = HybridLLMClient(mode="sim", tracer=tracer)
        response = client.chat(
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            messages=[{"role": "user", "content": f"Summarize: {research}"}],
        )
        print(f"[summarizer] run={run.id} cost=${response.total_tokens * 0.00001:.4f}")
        time.sleep(0.05)
        return response.content


def main() -> None:
    api_url = os.getenv("AGENTTRACE_API_URL", "http://localhost:8000/api")
    exporter = APIExporter(endpoint=api_url)
    tracer = Tracer()
    tracer.set_exporter(exporter)

    correlation_id = str(uuid.uuid4())
    print(f"Starting multi-agent pipeline with correlation_id={correlation_id}")

    research = researcher_agent(tracer, correlation_id, "AI observability trends 2026")
    summary = summarizer_agent(tracer, correlation_id, research)

    print(f"\nFinal summary: {summary}")
    tracer.flush()
    print(
        f"\nTraces flushed. Filter dashboard by correlation_id={correlation_id} to see both agents."
    )


if __name__ == "__main__":
    main()
