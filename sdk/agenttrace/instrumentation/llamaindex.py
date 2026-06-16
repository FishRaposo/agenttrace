"""LlamaIndex auto-instrumentation.

Automatically traces LlamaIndex operations using callback handlers.
"""

from __future__ import annotations

from typing import Any, Optional

from agenttrace.instrumentation.base import Instrumentor
from agenttrace.span import Span, SpanType
from agenttrace.tracer import Tracer

try:
    from llama_index.core.callbacks.base_handler import BaseCallbackHandler
    from llama_index.core.callbacks.schema import CBEventType
except ImportError:
    BaseCallbackHandler = object
    CBEventType = None


class AgentTraceLlamaIndexHandler(BaseCallbackHandler):
    """LlamaIndex callback handler for tracing."""

    def __init__(self, tracer: Tracer) -> None:
        if BaseCallbackHandler is not object:
            super().__init__(event_starts_to_ignore=[], event_ends_to_ignore=[])
        self.tracer = tracer
        self._spans: dict[str, Span] = {}

    def on_event_start(
        self,
        event_type: Any,
        payload: Optional[dict[str, Any]] = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        span_type = SpanType.CUSTOM
        if CBEventType is not None:
            if event_type == CBEventType.LLM:
                span_type = SpanType.LLM_CALL
            elif event_type == CBEventType.FUNCTION_CALL:
                span_type = SpanType.TOOL_CALL
            elif event_type == CBEventType.RETRIEVE:
                span_type = SpanType.RETRIEVAL
            elif event_type == CBEventType.SYNTHESIZE:
                span_type = SpanType.DECISION

        event_label = event_type.value if hasattr(event_type, "value") else event_type
        name = f"llamaindex.{event_label}"
        span = self.tracer.start_span(
            name=name,
            span_type=span_type,
            metadata={"payload": payload} if payload else None,
        )
        if payload:
            span.input_data = payload
        self._spans[event_id] = span
        return event_id

    def on_event_end(
        self,
        event_type: Any,
        payload: Optional[dict[str, Any]] = None,
        event_id: str = "",
        **kwargs: Any,
    ) -> None:
        span = self._spans.pop(event_id, None)
        if span:
            if payload:
                span.output_data = payload
            span.end()
            self.tracer.end_span(span)

    def start_trace(self, trace_id: Optional[str] = None) -> None:
        if self.tracer._current_run is None:
            self.tracer.start_run(name=f"llamaindex_trace_{trace_id or 'default'}")

    def end_trace(
        self,
        trace_id: Optional[str] = None,
        trace_map: Optional[dict[str, Any]] = None,
    ) -> None:
        if self.tracer._current_run is not None:
            self.tracer.end_run()


class LlamaIndexInstrumentor(Instrumentor):
    """Instruments LlamaIndex for automatic tracing.

    Usage:
        instrumentor = LlamaIndexInstrumentor(tracer=tracer)
        instrumentor.instrument()
    """

    def __init__(self, tracer: Tracer | None = None) -> None:
        super().__init__()
        self.tracer = tracer or Tracer()
        self._handler: Optional[AgentTraceLlamaIndexHandler] = None

    def instrument(self, **kwargs: Any) -> None:
        """Instrument LlamaIndex settings."""
        try:
            from llama_index.core import Settings
            from llama_index.core.callbacks import CallbackManager
        except ImportError as err:
            raise ImportError(
                "llama-index-core not installed. "
                "Install with: pip install llama-index-core"
            ) from err

        self._handler = AgentTraceLlamaIndexHandler(self.tracer)
        if (
            hasattr(Settings, "callback_manager")
            and Settings.callback_manager is not None
        ):
            Settings.callback_manager.add_handler(self._handler)
        else:
            Settings.callback_manager = CallbackManager([self._handler])
        self._instrumented = True

    def uninstrument(self) -> None:
        """Remove LlamaIndex instrumentation."""
        if self._handler is not None:
            try:
                from llama_index.core import Settings

                if (
                    hasattr(Settings, "callback_manager")
                    and Settings.callback_manager is not None
                ):
                    handlers = Settings.callback_manager.handlers
                    if self._handler in handlers:
                        handlers.remove(self._handler)
            except ImportError:
                pass
            self._handler = None
        self._instrumented = False

    def is_instrumented(self) -> bool:
        return self._instrumented
