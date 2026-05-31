"""Example: AgentTrace + LangChain integration.

This script demonstrates the fixed LangChain callback handler by creating
a simple chain and tracing its execution automatically.

Usage:
    AGENTTRACE_API_URL=http://localhost:8000/api python examples/langchain_example.py
"""

from __future__ import annotations

import os

# Optional: patch in simulated LLM responses for demo without API keys
os.environ.setdefault("AGENTTRACE_LLM_MODE", "sim")

from agenttrace import Tracer
from agenttrace.exporters.api_exporter import APIExporter
from agenttrace.instrumentation.langchain import LangChainInstrumentor


def main() -> None:
    api_url = os.getenv("AGENTTRACE_API_URL", "http://localhost:8000/api")
    exporter = APIExporter(endpoint=api_url)
    tracer = Tracer()
    tracer.set_exporter(exporter)

    # Instrument LangChain globally
    instrumentor = LangChainInstrumentor(tracer=tracer)
    instrumentor.instrument()

    # Create a simple mock "chain" for demonstration
    # (This avoids requiring langchain to be installed for the demo)
    try:
        from langchain_core.runnables import RunnableLambda  # type: ignore[import-untyped]

        chain = RunnableLambda(lambda x: f"Processed: {x}")
        result = chain.invoke("Hello, AgentTrace!")
        print(f"Result: {result}")
    except ImportError:
        print("langchain not installed; running manual simulation instead")
        # Manual simulation of what the callback handler would trace
        with tracer.start_run(name="langchain_demo", metadata={"workflow_id": "langchain-example"}) as run:
            span = tracer.start_span(name="LLMChain", span_type="llm_call")
            span.input_data = {"input": "Hello, AgentTrace!"}
            span.output_data = {"output": "Processed: Hello, AgentTrace!"}
            span.token_usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
            span.cost_usd = 0.0001
            span.end()
            tracer.end_span(span)
        print("Manual simulation completed — check dashboard for run.")

    tracer.flush()
    print("Traces flushed. Visit http://localhost:3000/runs to inspect.")


if __name__ == "__main__":
    main()
