"""AgentTrace demo — trace a small agent run offline and export to JSONL.

Self-contained: no server, dashboard, or API keys required. Uses the AgentTrace SDK
to record a run with a tool span and an LLM span, exports to a JSONL file, and prints
a summary (the dashboard/server consume the same records in production).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from agenttrace import Tracer
from agenttrace.exporters.jsonl import JSONLExporter
from agenttrace.wrappers import trace_llm, trace_tool

OUTPUT = Path(__file__).resolve().parent.parent / "data" / "demo_traces.jsonl"

tracer = Tracer()
tracer.set_exporter(JSONLExporter(str(OUTPUT), buffer_size=1))


@trace_tool(tracer, tool_name="retrieve")
def retrieve(query: str) -> list[str]:
    """Simulate a retrieval tool call."""
    time.sleep(0.02)
    return [f"doc about {query}", "a related document"]


@trace_llm(
    tracer,
    model="gpt-4o-mini",
    cost_per_prompt_token=0.00000015,
    cost_per_completion_token=0.0000006,
)
def answer(query: str, docs: list[str]) -> dict[str, object]:
    """Simulate a grounded LLM answer over retrieved docs."""
    time.sleep(0.05)
    return {
        "answer": f"Based on {len(docs)} documents, here is the answer about {query}.",
        "usage": {
            "prompt_tokens": 320,
            "completion_tokens": 64,
            "total_tokens": 384,
        },
    }


def main() -> None:
    print("=== AgentTrace demo (offline, JSONL export) ===")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tracer.run("demo_agent", metadata={"query": "vector databases"}):
        docs = retrieve("vector databases")
        result = answer("vector databases", docs)
        print(f"answer: {result['answer']}")
    tracer.flush()

    records = [
        json.loads(line)
        for line in OUTPUT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    print(f"Exported {len(records)} record(s) to {OUTPUT}")
    print("=== Demo complete: run + tool span + LLM span traced and exported ===")


if __name__ == "__main__":
    main()
