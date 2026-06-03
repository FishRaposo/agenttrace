"""Provider-specific convenience wrappers for OpenAI and Anthropic LLM calls.

These decorators automatically trace API calls and extract real token usage
and cost from provider-specific response objects.
"""

from __future__ import annotations

import functools
import os
from typing import Callable, ParamSpec, TypeVar

from agenttrace.cost_tracker import CostTracker
from agenttrace.span import SpanType
from agenttrace.tracer import Tracer

P = ParamSpec("P")
R = TypeVar("R")


def _resolve_model(default: str, override: str | None) -> str:
    return override or os.getenv("AGENTTRACE_LLM_MODEL", default)


def trace_openai(
    tracer: Tracer,
    model: str | None = None,
    feature: str | None = None,
    workflow_id: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that wraps OpenAI chat.completions.create() calls.

    Automatically extracts model name, token usage, and cost from the
    OpenAI response object. Falls back to the model parameter or
    AGENTTRACE_LLM_MODEL env var if the response doesn't specify one.

    Args:
        tracer: The Tracer instance.
        model: Default model name (e.g. "gpt-4"). Auto-detected from response if available.
        feature: Optional feature/component for cost attribution.
        workflow_id: Optional workflow ID for cost aggregation.

    Returns:
        A decorator that wraps the target function.
    """
    cost_tracker = CostTracker()
    default_model = _resolve_model("gpt-4o", model)

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            span = tracer.start_span(
                name=f"openai:{func.__name__}",
                span_type=SpanType.LLM_CALL,
                metadata={
                    "provider": "openai",
                    "function": func.__name__,
                    "feature": feature,
                    "workflow_id": workflow_id,
                },
            )
            span.input_data = {"kwargs": {k: v for k, v in kwargs.items() if k != "api_key"}}

            try:
                result = func(*args, **kwargs)
                span.output_data = {"choices_count": len(result.choices) if hasattr(result, "choices") else 0}
                span.end()

                # Extract model from response
                detected_model = getattr(result, "model", None) or default_model
                pricing = cost_tracker.get_pricing("openai", detected_model)

                # Extract token usage
                usage = getattr(result, "usage", None)
                if usage is not None:
                    prompt_tokens = getattr(usage, "prompt_tokens", 0)
                    completion_tokens = getattr(usage, "completion_tokens", 0)
                    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens)
                    span.token_usage = {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                    }

                    if pricing:
                        span.cost_usd = (
                            prompt_tokens * (pricing["prompt"] / 1000)
                            + completion_tokens * (pricing["completion"] / 1000)
                        )
                    else:
                        span.cost_usd = 0.0

                    cost_tracker.record_cost(
                        trace_id=span.run_id or span.id,
                        provider="openai",
                        model=detected_model,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        latency_ms=span.duration_ms or 0,
                        workflow_id=workflow_id,
                        feature=feature,
                    )

                if span.metadata is None:
                    span.metadata = {}
                span.metadata["model"] = detected_model

                return result
            except Exception as e:
                span.set_error(str(e))
                raise
            finally:
                if span.end_time is None:
                    tracer.end_span(span)

        return wrapper

    return decorator


def trace_anthropic(
    tracer: Tracer,
    model: str | None = None,
    feature: str | None = None,
    workflow_id: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that wraps Anthropic messages.create() calls.

    Automatically extracts model name, token usage, and cost from the
    Anthropic response object. Falls back to the model parameter or
    AGENTTRACE_LLM_MODEL env var if the response doesn't specify one.

    Args:
        tracer: The Tracer instance.
        model: Default model name (e.g. "claude-3-sonnet-20240229").
        feature: Optional feature/component for cost attribution.
        workflow_id: Optional workflow ID for cost aggregation.

    Returns:
        A decorator that wraps the target function.
    """
    cost_tracker = CostTracker()
    default_model = _resolve_model("claude-3-sonnet-20240229", model)

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            span = tracer.start_span(
                name=f"anthropic:{func.__name__}",
                span_type=SpanType.LLM_CALL,
                metadata={
                    "provider": "anthropic",
                    "function": func.__name__,
                    "feature": feature,
                    "workflow_id": workflow_id,
                },
            )
            span.input_data = {"kwargs": {k: v for k, v in kwargs.items() if k != "api_key"}}

            try:
                result = func(*args, **kwargs)
                span.output_data = {"content_blocks": len(result.content) if hasattr(result, "content") else 0}
                span.end()

                # Extract model from response
                detected_model = getattr(result, "model", None) or default_model
                pricing = cost_tracker.get_pricing("anthropic", detected_model)

                # Extract token usage
                usage = getattr(result, "usage", None)
                if usage is not None:
                    input_tokens = getattr(usage, "input_tokens", 0)
                    output_tokens = getattr(usage, "output_tokens", 0)
                    total_tokens = input_tokens + output_tokens
                    span.token_usage = {
                        "prompt_tokens": input_tokens,
                        "completion_tokens": output_tokens,
                        "total_tokens": total_tokens,
                    }

                    if pricing:
                        span.cost_usd = (
                            input_tokens * (pricing["prompt"] / 1000)
                            + output_tokens * (pricing["completion"] / 1000)
                        )
                    else:
                        span.cost_usd = 0.0

                    cost_tracker.record_cost(
                        trace_id=span.run_id or span.id,
                        provider="anthropic",
                        model=detected_model,
                        prompt_tokens=input_tokens,
                        completion_tokens=output_tokens,
                        latency_ms=span.duration_ms or 0,
                        workflow_id=workflow_id,
                        feature=feature,
                    )

                if span.metadata is None:
                    span.metadata = {}
                span.metadata["model"] = detected_model

                return result
            except Exception as e:
                span.set_error(str(e))
                raise
            finally:
                if span.end_time is None:
                    tracer.end_span(span)

        return wrapper

    return decorator
