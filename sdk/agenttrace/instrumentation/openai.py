"""OpenAI SDK auto-instrumentation.

Monkey-patches openai.resources.chat.completions.Completions.create
to automatically trace every chat completion call.
"""

from __future__ import annotations

from typing import Any

from agenttrace.instrumentation.base import Instrumentor
from agenttrace import Tracer


class OpenAIInstrumentor(Instrumentor):
    """Instruments the OpenAI SDK for automatic tracing.

    Usage:
        instrumentor = OpenAIInstrumentor(tracer=tracer)
        instrumentor.instrument()
    """

    def __init__(self, tracer: Tracer | None = None) -> None:
        """Initialize instrumentor.

        Args:
            tracer: Tracer instance. Creates default if None.
        """
        super().__init__()
        self.tracer = tracer or Tracer()
        self._original_create: Any = None

    def instrument(self, **kwargs: Any) -> None:
        """Instrument OpenAI chat completions."""
        try:
            import openai
        except ImportError:
            raise ImportError("openai not installed. Install with: pip install openai")

        completions = openai.resources.chat.completions.Completions
        self._original_create = completions.create

        original = self._original_create
        tracer = self.tracer

        async def _traced_create_async(self_, *args: Any, **kwargs: Any) -> Any:
            """Async wrapper that traces the completion call."""
            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
            prompt_tokens = sum(len(str(m.get("content", ""))) for m in messages) // 4

            span = tracer.start_span(name=f"openai.chat.completions.create", span_type="llm_call")
            span.input_data = {"model": model, "messages": messages}

            try:
                response = await original(self_, *args, **kwargs)
                choice = response.choices[0] if response.choices else None
                content = choice.message.content if choice and choice.message else ""
                span.output_data = {"content": content}

                usage = getattr(response, "usage", None)
                if usage:
                    span.token_usage = {
                        "prompt_tokens": getattr(usage, "prompt_tokens", prompt_tokens),
                        "completion_tokens": getattr(usage, "completion_tokens", 0),
                        "total_tokens": getattr(usage, "total_tokens", 0),
                    }
                span.end()
                tracer.end_span(span)
                return response
            except Exception as e:
                span.set_error(str(e))
                span.end()
                tracer.end_span(span)
                raise

        def _traced_create_sync(self_, *args: Any, **kwargs: Any) -> Any:
            """Sync wrapper that traces the completion call."""
            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
            prompt_tokens = sum(len(str(m.get("content", ""))) for m in messages) // 4

            span = tracer.start_span(name=f"openai.chat.completions.create", span_type="llm_call")
            span.input_data = {"model": model, "messages": messages}

            try:
                response = original(self_, *args, **kwargs)
                choice = response.choices[0] if response.choices else None
                content = choice.message.content if choice and choice.message else ""
                span.output_data = {"content": content}

                usage = getattr(response, "usage", None)
                if usage:
                    span.token_usage = {
                        "prompt_tokens": getattr(usage, "prompt_tokens", prompt_tokens),
                        "completion_tokens": getattr(usage, "completion_tokens", 0),
                        "total_tokens": getattr(usage, "total_tokens", 0),
                    }
                span.end()
                tracer.end_span(span)
                return response
            except Exception as e:
                span.set_error(str(e))
                span.end()
                tracer.end_span(span)
                raise

        # Patch both sync and async paths
        completions.create = _traced_create_sync
        if hasattr(completions, "create_async"):
            completions.create_async = _traced_create_async

        self._instrumented = True

    def uninstrument(self) -> None:
        """Remove OpenAI instrumentation."""
        if self._original_create is not None:
            try:
                import openai
                openai.resources.chat.completions.Completions.create = self._original_create
            except ImportError:
                pass
            self._original_create = None
        self._instrumented = False

    def is_instrumented(self) -> bool:
        return self._instrumented
