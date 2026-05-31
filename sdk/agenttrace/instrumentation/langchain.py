"""LangChain auto-instrumentation.

Automatically traces LangChain chains, agents, and tool calls.
"""

from __future__ import annotations

from typing import Any

from agenttrace.instrumentation.base import Instrumentor
from agenttrace import Tracer


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
            from langchain.callbacks.base import BaseCallbackHandler
            from langchain.callbacks.manager import CallbackManager
        except ImportError:
            raise ImportError("LangChain not installed. Install with: pip install langchain")
        
        # Create callback handler
        handler = AgentTraceCallbackHandler(self.tracer)
        
        # Monkey-patch LangChain to use our handler
        # This is a simplified version - real implementation would be more thorough
        self._original_callback_manager = CallbackManager
        
        class InstrumentedCallbackManager(CallbackManager):
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                super().__init__(*args, **kwargs)
                self.add_handler(handler, inherit=True)
        
        # Replace in langchain module
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
    
    Implements LangChain's callback interface to trace all operations.
    """
    
    def __init__(self, tracer: Tracer) -> None:
        """Initialize handler.
        
        Args:
            tracer: Tracer instance.
        """
        self.tracer = tracer
        self._run_spans: dict[str, Any] = {}
    
    def on_chain_start(
        self,
        serialized: dict[str, Any] | None,
        inputs: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when chain starts."""
        run_id = kwargs.get("run_id")
        chain_name = serialized.get("name", "Chain") if serialized else "Chain"
        
        span = self.tracer.start_span(
            name=f"langchain.chain.{chain_name}",
            span_type="chain",
            inputs=inputs,
        )
        if run_id:
            self._run_spans[str(run_id)] = span
    
    def on_chain_end(
        self,
        outputs: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when chain ends."""
        run_id = kwargs.get("run_id")
        span = self._run_spans.pop(str(run_id), None) if run_id else None
        
        if span:
            span.finish(outputs=outputs)
    
    def on_chain_error(
        self,
        error: BaseException,
        **kwargs: Any,
    ) -> None:
        """Called when chain errors."""
        run_id = kwargs.get("run_id")
        span = self._run_spans.pop(str(run_id), None) if run_id else None
        
        if span:
            span.finish(error=str(error))
    
    def on_llm_start(
        self,
        serialized: dict[str, Any] | None,
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts."""
        run_id = kwargs.get("run_id")
        model_name = kwargs.get("invocation_params", {}).get("model_name", "llm")
        
        span = self.tracer.start_span(
            name=f"langchain.llm.{model_name}",
            span_type="llm",
            inputs={"prompts": prompts},
        )
        if run_id:
            self._run_spans[f"llm_{run_id}"] = span
    
    def on_llm_end(
        self,
        response: Any,
        **kwargs: Any,
    ) -> None:
        """Called when LLM ends."""
        run_id = kwargs.get("run_id")
        span = self._run_spans.pop(f"llm_{run_id}", None) if run_id else None
        
        if span:
            # Extract token usage if available
            outputs: dict[str, Any] = {"response": str(response)[:1000]}
            
            if hasattr(response, "llm_output") and response.llm_output:
                token_usage = response.llm_output.get("token_usage", {})
                outputs["token_usage"] = token_usage
            
            span.finish(outputs=outputs)
    
    def on_tool_start(
        self,
        serialized: dict[str, Any] | None,
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Called when tool starts."""
        run_id = kwargs.get("run_id")
        tool_name = serialized.get("name", "tool") if serialized else "tool"
        
        span = self.tracer.start_span(
            name=f"langchain.tool.{tool_name}",
            span_type="tool",
            inputs={"input": input_str},
        )
        if run_id:
            self._run_spans[f"tool_{run_id}"] = span
    
    def on_tool_end(
        self,
        output: str,
        observation: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Called when tool ends."""
        run_id = kwargs.get("run_id")
        span = self._run_spans.pop(f"tool_{run_id}", None) if run_id else None
        
        if span:
            span.finish(outputs={"output": output, "observation": observation})
    
    def on_agent_action(
        self,
        action: Any,
        **kwargs: Any,
    ) -> None:
        """Called on agent action."""
        self.tracer.add_event(
            "agent_action",
            {
                "tool": action.tool if hasattr(action, "tool") else None,
                "tool_input": action.tool_input if hasattr(action, "tool_input") else None,
            },
        )
    
    def on_agent_finish(
        self,
        finish: Any,
        **kwargs: Any,
    ) -> None:
        """Called on agent finish."""
        self.tracer.add_event(
            "agent_finish",
            {
                "return_values": finish.return_values if hasattr(finish, "return_values") else None,
            },
        )
