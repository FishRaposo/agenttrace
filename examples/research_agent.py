"""Example research agent demonstrating AgentTrace SDK usage."""

from __future__ import annotations

import argparse
import time

from agenttrace import Tracer
from agenttrace.exporters.api_exporter import APIExporter
from agenttrace.exporters.jsonl import JSONLExporter
from agenttrace.wrappers import trace_llm, trace_tool


def setup_tracer(exporter_type: str = "api") -> Tracer:
    tracer = Tracer()
    if exporter_type == "api":
        tracer.set_exporter(
            APIExporter(endpoint="http://localhost:8000/api/traces", buffer_size=1)
        )
    else:
        tracer.set_exporter(JSONLExporter("data/research_traces.jsonl", buffer_size=1))
    return tracer


tracer = setup_tracer()


@trace_tool(tracer, tool_name="web_search")
def web_search(query: str) -> list[dict[str, str]]:
    """Simulate a web search tool call.

    Args:
        query: Search query string.

    Returns:
        List of search result dictionaries.
    """
    time.sleep(0.1)
    return [
        {
            "title": f"Introduction to {query}",
            "url": "https://example.com/intro",
            "snippet": f"A comprehensive guide to {query}",
        },
        {
            "title": f"{query} in Practice",
            "url": "https://example.com/practice",
            "snippet": f"Real-world applications of {query}",
        },
        {
            "title": f"Advanced {query}",
            "url": "https://example.com/advanced",
            "snippet": f"Deep dive into {query} techniques",
        },
    ]


@trace_tool(tracer, tool_name="parse_content")
def parse_content(url: str) -> dict[str, str]:
    """Simulate parsing content from a URL.

    Args:
        url: URL to parse.

    Returns:
        Parsed content dictionary.
    """
    time.sleep(0.05)
    return {
        "url": url,
        "title": "Article Title",
        "content": (
            "This is the parsed content of the article. "
            "It contains relevant information."
        ),
        "word_count": 500,
    }


@trace_llm(
    tracer,
    model="gpt-4",
    cost_per_prompt_token=0.00003,
    cost_per_completion_token=0.00006,
)
def synthesize_findings(query: str, results: list[dict[str, str]]) -> dict[str, object]:
    """Simulate an LLM call to synthesize research findings.

    Args:
        query: The original research query.
        results: Search results to synthesize.

    Returns:
        Dictionary with synthesis output and usage metadata.
    """
    time.sleep(0.5)
    return {
        "answer": (
            f"Based on the research about {query}, here are the key findings: ..."
        ),
        "sources": [r["url"] for r in results[:3]],
        "confidence": 0.85,
        "usage": {
            "prompt_tokens": 450,
            "completion_tokens": 200,
            "total_tokens": 650,
        },
    }


@trace_llm(
    tracer,
    model="gpt-4",
    cost_per_prompt_token=0.00003,
    cost_per_completion_token=0.00006,
)
def generate_followup_questions(query: str, summary: str) -> dict[str, object]:
    """Simulate generating follow-up questions.

    Args:
        query: Original query.
        summary: Research summary.

    Returns:
        Dictionary with questions and usage metadata.
    """
    time.sleep(0.3)
    return {
        "questions": [
            f"What are the latest developments in {query}?",
            f"How does {query} compare to alternative approaches?",
            f"What are the ethical implications of {query}?",
        ],
        "usage": {
            "prompt_tokens": 200,
            "completion_tokens": 100,
            "total_tokens": 300,
        },
    }


def run_research_agent(query: str) -> None:
    """Run the example research agent with full tracing.

    Demonstrates the complete AgentTrace workflow:
    1. Start a traced run
    2. Use decorated tools and LLM calls
    3. View the results in the dashboard

    Args:
        query: The research query to investigate.
    """
    with tracer.run("research_agent", metadata={"query": query, "version": "1.0.0"}):
        search_results = web_search(query)
        print(f"Found {len(search_results)} search results")

        parsed = parse_content(search_results[0]["url"])
        print(f"Parsed content from {parsed['url']}")

        synthesis = synthesize_findings(query, search_results)
        print(f"Synthesis answer: {synthesis['answer'][:80]}...")

        followup = generate_followup_questions(query, synthesis["answer"])
        print(f"Generated {len(followup['questions'])} follow-up questions")

        for q in followup["questions"]:
            print(f"  - {q}")

    tracer.flush()
    exporter_name = (
        "API server" if isinstance(tracer._exporter, APIExporter) else "JSONL file"
    )
    print(f"\nTrace exported via {exporter_name}")
    print("Dashboard: http://localhost:3000")
    print("API docs:  http://localhost:8000/docs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentTrace research agent example")
    parser.add_argument("--query", default="quantum computing", help="Research query")
    parser.add_argument(
        "--exporter",
        choices=["api", "jsonl"],
        default="api",
        help="Export target: api (default) sends to server; jsonl writes to file",
    )
    args = parser.parse_args()

    tracer = setup_tracer(args.exporter)
    run_research_agent(args.query)
