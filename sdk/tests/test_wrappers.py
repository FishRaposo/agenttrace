"""Tests for decision_wrapper and retrieval_wrapper."""

from __future__ import annotations

from typing import Any

import pytest
from agenttrace.tracer import Tracer
from agenttrace.wrappers.decision_wrapper import trace_decision
from agenttrace.wrappers.retrieval_wrapper import trace_retrieval


class TestDecisionWrapper:
    """Tests for the trace_decision decorator."""

    def test_creates_span_with_correct_type(self, tracer: Tracer) -> None:
        @trace_decision(tracer)
        def choose_action(state: str) -> str:
            return "call_search"

        with tracer.run("test_run"):
            result = choose_action("initial_state")

        assert result == "call_search"

    def test_creates_span_with_correct_span_type(self, tracer: Tracer) -> None:
        @trace_decision(tracer)
        def decide() -> str:
            return "yes"

        with tracer.run("test_run"):
            decide()

    def test_records_output_correctly(self, tracer: Tracer) -> None:
        @trace_decision(tracer)
        def pick_option(options: list[str]) -> str:
            return options[0]

        with tracer.run("test_run"):
            output = pick_option(["a", "b", "c"])

        assert output == "a"

    def test_handles_exceptions(self, tracer: Tracer) -> None:
        @trace_decision(tracer)
        def failing_decision() -> None:
            raise ValueError("cannot decide")

        with pytest.raises(ValueError, match="cannot decide"):
            with tracer.run("test_run"):
                failing_decision()

    def test_works_with_tracer_context(self, tracer: Tracer) -> None:
        @trace_decision(tracer)
        def nested_decision(reason: str) -> str:
            return f"decided:{reason}"

        with tracer.run("test_run"):
            result = nested_decision("good_reason")

        assert result == "decided:good_reason"

    def test_uses_custom_decision_name(self, tracer: Tracer) -> None:
        @trace_decision(tracer, decision_name="route_selector")
        def router(query: str) -> str:
            return "/search"

        with tracer.run("test_run"):
            result = router("test query")

        assert result == "/search"


class TestRetrievalWrapper:
    """Tests for the trace_retrieval decorator."""

    def test_creates_span_with_correct_type(self, tracer: Tracer) -> None:
        @trace_retrieval(tracer)
        def fetch_docs(query: str) -> list[dict[str, Any]]:
            return [{"id": "1", "text": "hello"}]

        with tracer.run("test_run"):
            results = fetch_docs("test")

        assert len(results) == 1
        assert results[0]["id"] == "1"

    def test_creates_span_with_correct_span_type(self, tracer: Tracer) -> None:
        @trace_retrieval(tracer)
        def search(query: str) -> list[str]:
            return ["doc1", "doc2"]

        with tracer.run("test_run"):
            search("query")

    def test_records_output_correctly(self, tracer: Tracer) -> None:
        @trace_retrieval(tracer)
        def vector_search(embedding: list[float]) -> list[str]:
            return ["match1", "match2"]

        with tracer.run("test_run"):
            results = vector_search([0.1, 0.2])

        assert results == ["match1", "match2"]

    def test_handles_exceptions(self, tracer: Tracer) -> None:
        @trace_retrieval(tracer)
        def broken_retrieval() -> list[str]:
            raise RuntimeError("index not found")

        with pytest.raises(RuntimeError, match="index not found"):
            with tracer.run("test_run"):
                broken_retrieval()

    def test_works_with_tracer_context(self, tracer: Tracer) -> None:
        @trace_retrieval(tracer)
        def semantic_search(query: str) -> dict[str, Any]:
            return {"query": query, "hits": ["doc_a"]}

        with tracer.run("test_run"):
            result = semantic_search("what is ai")

        assert result["query"] == "what is ai"
        assert "doc_a" in result["hits"]

    def test_uses_custom_retriever_name(self, tracer: Tracer) -> None:
        @trace_retrieval(tracer, retriever_name="pinecone_search")
        def search_pinecone(query: str) -> list[str]:
            return ["result"]

        with tracer.run("test_run"):
            result = search_pinecone("test")

        assert result == ["result"]


class TestWrapperIntegration:
    """Integration tests combining multiple wrappers."""

    def test_decision_and_retrieval_together(self, tracer: Tracer) -> None:
        @trace_decision(tracer)
        def route(query: str) -> str:
            return "web_search"

        @trace_retrieval(tracer)
        def web_search(query: str) -> list[str]:
            return [f"result for {query}"]

        with tracer.run("test_run"):
            action = route("What is the weather?")
            results = web_search("weather today")

        assert action == "web_search"
        assert results == ["result for weather today"]
