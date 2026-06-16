"""OpenAI SDK auto-instrumentation.

Monkey-patches openai.resources.chat.completions.Completions.create
and AsyncCompletions.create to automatically trace every chat completion call.
"""

from __future__ import annotations

from typing import Any

from agenttrace.cost_tracker import CostTracker
from agenttrace.instrumentation.base import Instrumentor
from agenttrace.span import SpanType
from agenttrace.tracer import Tracer


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
        self._original_create_async: Any = None

    def instrument(self, **kwargs: Any) -> None:  # noqa: C901
        """Instrument OpenAI chat completions."""
        try:
            import openai
        except ImportError as err:
            raise ImportError(
                "openai not installed. Install with: pip install openai"
            ) from err

        completions = openai.resources.chat.completions.Completions
        async_completions = openai.resources.chat.completions.AsyncCompletions

        self._original_create = completions.create
        self._original_create_async = async_completions.create

        original = self._original_create
        original_async = self._original_create_async
        tracer = self.tracer
        cost_tracker = CostTracker()

        async def _traced_create_async(self_, *args: Any, **kwargs: Any) -> Any:
            """Async wrapper that traces the completion call."""
            model = kwargs.get("model", "gpt-4o")
            messages = kwargs.get("messages", [])

            span = tracer.start_span(
                name="openai.chat.completions.create", span_type=SpanType.LLM_CALL
            )
            span.input_data = {"model": model, "messages": messages}
            if span.metadata is None:
                span.metadata = {}
            span.metadata.update({"provider": "openai", "model": model})

            try:
                response = await original_async(self_, *args, **kwargs)
                choice = (
                    response.choices[0] if getattr(response, "choices", None) else None
                )
                content = (
                    choice.message.content
                    if choice and getattr(choice, "message", None)
                    else ""
                )
                span.output_data = {"content": content}

                usage = getattr(response, "usage", None)
                if usage:
                    prompt_tokens = getattr(usage, "prompt_tokens", 0)
                    completion_tokens = getattr(usage, "completion_tokens", 0)
                    total_tokens = getattr(
                        usage, "total_tokens", prompt_tokens + completion_tokens
                    )
                    span.token_usage = {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                    }
                    pricing = cost_tracker.get_pricing("openai", model)
                    if pricing:
                        span.cost_usd = prompt_tokens * (
                            pricing["prompt"] / 1000
                        ) + completion_tokens * (pricing["completion"] / 1000)
                    else:
                        span.cost_usd = 0.0

                return response
            except Exception as e:
                span.set_error(str(e))
                raise
            finally:
                if span.end_time is None:
                    span.end()
                tracer.end_span(span)

        def _traced_create_sync(self_, *args: Any, **kwargs: Any) -> Any:
            """Sync wrapper that traces the completion call."""
            model = kwargs.get("model", "gpt-4o")
            messages = kwargs.get("messages", [])

            span = tracer.start_span(
                name="openai.chat.completions.create", span_type=SpanType.LLM_CALL
            )
            span.input_data = {"model": model, "messages": messages}
            if span.metadata is None:
                span.metadata = {}
            span.metadata.update({"provider": "openai", "model": model})

            try:
                response = original(self_, *args, **kwargs)
                choice = (
                    response.choices[0] if getattr(response, "choices", None) else None
                )
                content = (
                    choice.message.content
                    if choice and getattr(choice, "message", None)
                    else ""
                )
                span.output_data = {"content": content}

                usage = getattr(response, "usage", None)
                if usage:
                    prompt_tokens = getattr(usage, "prompt_tokens", 0)
                    completion_tokens = getattr(usage, "completion_tokens", 0)
                    total_tokens = getattr(
                        usage, "total_tokens", prompt_tokens + completion_tokens
                    )
                    span.token_usage = {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                    }
                    pricing = cost_tracker.get_pricing("openai", model)
                    if pricing:
                        span.cost_usd = prompt_tokens * (
                            pricing["prompt"] / 1000
                        ) + completion_tokens * (pricing["completion"] / 1000)
                    else:
                        span.cost_usd = 0.0

                return response
            except Exception as e:
                span.set_error(str(e))
                raise
            finally:
                if span.end_time is None:
                    span.end()
                tracer.end_span(span)

        completions.create = _traced_create_sync
        async_completions.create = _traced_create_async
        self._instrumented = True

    def uninstrument(self) -> None:
        """Remove OpenAI instrumentation."""
        try:
            import openai

            if self._original_create is not None:
                openai.resources.chat.completions.Completions.create = (
                    self._original_create
                )
                self._original_create = None
            if self._original_create_async is not None:
                openai.resources.chat.completions.AsyncCompletions.create = (
                    self._original_create_async
                )
                self._original_create_async = None
        except (ImportError, AttributeError):
            pass
        self._instrumented = False

    def is_instrumented(self) -> bool:
        return self._instrumented
