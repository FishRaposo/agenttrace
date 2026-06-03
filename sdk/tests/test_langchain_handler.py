"""Tests for LangChain callback handler using stub callbacks (no langchain dep required)."""

from __future__ import annotations


from agenttrace import Tracer
from agenttrace.instrumentation.langchain import AgentTraceCallbackHandler


class TestAgentTraceCallbackHandler:
    def test_on_chain_start_end(self) -> None:
        tracer = Tracer()
        handler = AgentTraceCallbackHandler(tracer)

        with tracer.run("test_run"):
            handler.on_chain_start(
                serialized={"name": "TestChain"},
                inputs={"query": "hello"},
                run_id="run-123",
            )
            handler.on_chain_end(
                outputs={"result": "world"},
                run_id="run-123",
            )

        run = tracer._current_run
        assert run is None  # run ended

    def test_on_llm_start_end(self) -> None:
        tracer = Tracer()
        handler = AgentTraceCallbackHandler(tracer)

        with tracer.run("test_run"):
            handler.on_llm_start(
                serialized=None,
                prompts=["hello"],
                run_id="run-456",
                invocation_params={"model_name": "gpt-4"},
            )
            handler.on_llm_end(
                response="world",
                run_id="run-456",
            )

    def test_on_tool_start_end(self) -> None:
        tracer = Tracer()
        handler = AgentTraceCallbackHandler(tracer)

        with tracer.run("test_run"):
            handler.on_tool_start(
                serialized={"name": "search"},
                input_str="python",
                run_id="run-789",
            )
            handler.on_tool_end(
                output="results",
                observation="ok",
                run_id="run-789",
            )

    def test_on_chain_error(self) -> None:
        tracer = Tracer()
        handler = AgentTraceCallbackHandler(tracer)

        with tracer.run("test_run"):
            handler.on_chain_start(
                serialized={"name": "FailingChain"},
                inputs={},
                run_id="run-err",
            )
            handler.on_chain_error(
                error=ValueError("simulated"),
                run_id="run-err",
            )

    def test_agent_action_event(self) -> None:
        tracer = Tracer()
        handler = AgentTraceCallbackHandler(tracer)

        with tracer.run("test_run"):
            handler.on_agent_action(
                action=None,
            )
            # Should not raise
