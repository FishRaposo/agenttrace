"""LangChain auto-instrumentation.

Automatically traces LangChain chains, agents, and tool calls.
"""

from __future__ import annotations

from typing import Any

from agenttrace.instrumentation.base import Instrumentor
from agenttrace.span import Span, SpanType
from agenttrace.tracer import Tracer


class LangChainInstrumentor(Instrumentor):
    """Instruments LangChain for automatic tracing.

    Traces:
    - Chain runs
    - LLM calls
    - Tool executions
    - Agent steps
    """

    def __init__(self, tracer: Tracer | None = None) -> None:
        """Initialize instrumentor.

        Args:
            tracer: Tracer instance. Creates default if None.
        """
        super().__init__()
        self.tracer = tracer or Tracer()
        self._original_callback_manager = None

    def instrument(self, **kwargs: Any) -> None:
        """Instrument LangChain.

        Args:
            **kwargs: Options (tracer, etc.).
        """
        try:
            from langchain.callbacks.base import (
                BaseCallbackHandler,  # noqa: F401  # availability probe
            )
            from langchain.callbacks.manager import CallbackManager
        except ImportError as err:
            raise ImportError(
                "LangChain not installed. Install with: pip install langchain"
            ) from err

        handler = AgentTraceCallbackHandler(self.tracer)
        self._original_callback_manager = CallbackManager

        class InstrumentedCallbackManager(CallbackManager):
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                super().__init__(*args, **kwargs)
                self.add_handler(handler, inherit=True)

        import langchain.callbacks.manager as manager_module

        manager_module.CallbackManager = InstrumentedCallbackManager
        self._instrumented = True

    def uninstrument(self) -> None:
        """Remove LangChain instrumentation."""
        if self._original_callback_manager:
            import langchain.callbacks.manager as manager_module

            manager_module.CallbackManager = self._original_callback_manager
            self._instrumented = False


class AgentTraceCallbackHandler:
    """LangChain callback handler for tracing.

    Maps LangChain lifecycle callbacks to AgentTrace spans using the
    real public SDK API.
    """

    def __init__(self, tracer: Tracer) -> None:
        self.tracer = tracer
        self._run_spans: dict[str, Span] = {}

    def _store_span(self, key: str, span: Span) -> None:
        self._run_spans[key] = span

    def _pop_span(self, key: str | None) -> Span | None:
        if key is None:
            return None
        return self._run_spans.pop(str(key), None)

    def on_chain_start(
        self,
        serialized: dict[str, Any] | None,
        inputs: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        run_id = kwargs.get("run_id")
        chain_name = serialized.get("name", "Chain") if serialized else "Chain"

        span = self.tracer.start_span(
            name=f"langchain.chain.{chain_name}",
            span_type=SpanType.CUSTOM,
            metadata={"inputs": inputs},
        )
        span.input_data = inputs
        if run_id:
            self._store_span(str(run_id), span)

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        run_id = kwargs.get("run_id")
        span = self._pop_span(run_id)
        if span:
            span.output_data = outputs
            span.end(output=outputs)
            self.tracer.end_span(span)

    def on_chain_error(
        self,
        error: BaseException,
        **kwargs: Any,
    ) -> None:
        run_id = kwargs.get("run_id")
        span = self._pop_span(run_id)
        if span:
            span.set_error(str(error))
            span.end()
            self.tracer.end_span(span)

    def on_llm_start(
        self,
        serialized: dict[str, Any] | None,
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        run_id = kwargs.get("run_id")
        model_name = kwargs.get("invocation_params", {}).get("model_name", "llm")

        span = self.tracer.start_span(
            name=f"langchain.llm.{model_name}",
            span_type=SpanType.LLM_CALL,
            metadata={"prompts": prompts, "model": model_name},
        )
        span.input_data = {"prompts": prompts}
        if run_id:
            self._store_span(f"llm_{run_id}", span)

    def on_llm_end(
        self,
        response: Any,
        **kwargs: Any,
    ) -> None:
        run_id = kwargs.get("run_id")
        span = self._pop_span(f"llm_{run_id}")
        if span:
            outputs: dict[str, Any] = {"response": str(response)[:1000]}
            if hasattr(response, "llm_output") and response.llm_output:
                token_usage = response.llm_output.get("token_usage", {})
                outputs["token_usage"] = token_usage
            span.output_data = outputs
            span.end(output=outputs)
            self.tracer.end_span(span)

    def on_tool_start(
        self,
        serialized: dict[str, Any] | None,
        input_str: str,
        **kwargs: Any,
    ) -> None:
        run_id = kwargs.get("run_id")
        tool_name = serialized.get("name", "tool") if serialized else "tool"

        span = self.tracer.start_span(
            name=f"langchain.tool.{tool_name}",
            span_type=SpanType.TOOL_CALL,
            metadata={"input": input_str},
        )
        span.input_data = {"input": input_str}
        if run_id:
            self._store_span(f"tool_{run_id}", span)

    def on_tool_end(
        self,
        output: str,
        observation: str | None = None,
        **kwargs: Any,
    ) -> None:
        run_id = kwargs.get("run_id")
        span = self._pop_span(f"tool_{run_id}")
        if span:
            span.output_data = {"output": output, "observation": observation}
            span.end(output=span.output_data)
            self.tracer.end_span(span)

    def on_agent_action(
        self,
        action: Any,
        **kwargs: Any,
    ) -> None:
        self.tracer.add_event(
            "agent_action",
            {
                "tool": action.tool if hasattr(action, "tool") else None,
                "tool_input": action.tool_input
                if hasattr(action, "tool_input")
                else None,
            },
        )

    def on_agent_finish(
        self,
        finish: Any,
        **kwargs: Any,
    ) -> None:
        self.tracer.add_event(
            "agent_finish",
            {
                "return_values": finish.return_values
                if hasattr(finish, "return_values")
                else None,
            },
        )
