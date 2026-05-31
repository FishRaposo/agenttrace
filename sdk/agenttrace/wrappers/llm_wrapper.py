"""LLM call wrapper — automatically traces LLM API calls."""

from __future__ import annotations

import functools
import re
from typing import Any, Callable, Optional, ParamSpec, TypeVar

from agenttrace.span import SpanType
from agenttrace.tracer import Tracer
from agenttrace.cost_tracker import CostTracker

P = ParamSpec("P")
R = TypeVar("R")


def _extract_token_usage(result: Any) -> Optional[dict[str, int]]:
    """Extract token usage from an LLM response using multiple strategies.

    Attempts, in order:
        1. dict access (result["usage"])
        2. object attribute access (result.usage)
        3. string heuristic parsing

    Args:
        result: The result returned by the LLM call function.

    Returns:
        A dict with prompt_tokens, completion_tokens, total_tokens,
        or None if extraction fails.
    """

    usage_data: Optional[dict[str, int]] = None

    if isinstance(result, dict):
        usage_data = result.get("usage")

    if usage_data is None:
        usage_attr = getattr(result, "usage", None)
        usage_metadata_attr = getattr(result, "usage_metadata", None)
        if usage_attr is not None:
            if isinstance(usage_attr, dict):
                usage_data = usage_attr
            else:
                usage_data = {
                    k: v
                    for k, v in vars(usage_attr).items()
                    if isinstance(v, int)
                }
        elif usage_metadata_attr is not None:
            usage_data = {
                k: v
                for k, v in vars(usage_metadata_attr).items()
                if isinstance(v, int)
            }

    if usage_data is None and isinstance(result, str):
        usage_data = _parse_token_string(result)

    if usage_data is None:
        return None

    prompt_tokens = usage_data.get(
        "prompt_tokens",
        usage_data.get("input_tokens", usage_data.get("prompt_token_count", 0)),
    )
    completion_tokens = usage_data.get(
        "completion_tokens",
        usage_data.get("output_tokens", usage_data.get("candidates_token_count", 0)),
    )

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def _parse_token_string(text: str) -> Optional[dict[str, int]]:
    """Parse a string for token usage patterns.

    Handles separators like ':', '=', and whitespace around token counts.

    Args:
        text: String that may contain token usage information.

    Returns:
        Extracted token counts or None.
    """

    patterns: list[tuple[str, str]] = [
        (r"prompt_tokens[=:\s]*(\d+)", "prompt_tokens"),
        (r"completion_tokens[=:\s]*(\d+)", "completion_tokens"),
        (r"total_tokens[=:\s]*(\d+)", "total_tokens"),
        (r"input_tokens[=:\s]*(\d+)", "input_tokens"),
        (r"output_tokens[=:\s]*(\d+)", "output_tokens"),
    ]

    extracted: dict[str, int] = {}
    for pattern, key in patterns:
        match = re.search(pattern, text)
        if match:
            extracted[key] = int(match.group(1))

    if not extracted:
        return None

    return extracted


def trace_llm(
    tracer: Tracer,
    model: str = "unknown",
    provider: str = "openai",
    cost_per_prompt_token: float | None = None,
    cost_per_completion_token: float | None = None,
    feature: str | None = None,
    workflow_id: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that automatically traces LLM API calls.

    Creates a span for each call, recording the prompt, completion,
    token usage, cost, and latency.

    Args:
        tracer: The Tracer instance to use for recording.
        model: Name of the LLM model being called.
        provider: LLM provider name.
        cost_per_prompt_token: Cost in USD per prompt token.
        cost_per_completion_token: Cost in USD per completion token.
        feature: Optional feature/component name for cost attribution.
        workflow_id: Optional workflow identifier for cost aggregation.

    Returns:
        A decorator function that wraps the target function.

    Example:
        >>> @trace_llm(tracer, model="gpt-4", feature="summarization")
        ... def call_gpt(prompt: str) -> str:
        ...     return "response"
    """

    cost_tracker = CostTracker()

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Resolve pricing if not explicitly set
            prompt_rate = cost_per_prompt_token
            completion_rate = cost_per_completion_token
            if prompt_rate is None or completion_rate is None:
                pricing = cost_tracker.get_pricing(provider, model)
                if pricing:
                    prompt_rate = prompt_rate or pricing["prompt"]
                    completion_rate = completion_rate or pricing["completion"]
                else:
                    prompt_rate = prompt_rate or 0.0
                    completion_rate = completion_rate or 0.0

            metadata = {
                "model": model,
                "provider": provider,
                "function": func.__name__,
                "cost_per_prompt_token": prompt_rate,
                "cost_per_completion_token": completion_rate,
            }
            if feature:
                metadata["feature"] = feature
            if workflow_id:
                metadata["workflow_id"] = workflow_id

            span = tracer.start_span(
                name=f"{model}:{func.__name__}",
                span_type=SpanType.LLM_CALL,
                metadata=metadata,
            )

            input_data = {"args": repr(args), "kwargs": repr(kwargs)}
            span.input_data = input_data

            try:
                result = func(*args, **kwargs)
                span.output_data = result

                span.end(output=result)

                usage = _extract_token_usage(result)
                if usage is not None:
                    span.token_usage = usage
                    # Rates from CostTracker are per-1k tokens; divide by 1000
                    span.cost_usd = (
                        usage["prompt_tokens"] * (prompt_rate / 1000)
                        + usage["completion_tokens"] * (completion_rate / 1000)
                    )
                    cost_tracker.record_cost(
                        trace_id=getattr(span, "run_id", None) or span.id,
                        provider=provider,
                        model=model,
                        prompt_tokens=usage["prompt_tokens"],
                        completion_tokens=usage["completion_tokens"],
                        latency_ms=span.duration_ms or 0,
                        workflow_id=workflow_id,
                        feature=feature,
                    )
                elif isinstance(result, str):
                    estimated_tokens = max(1, len(result) // 4)
                    span.token_usage = {
                        "prompt_tokens": 0,
                        "completion_tokens": estimated_tokens,
                        "total_tokens": estimated_tokens,
                    }
                    if span.metadata is None:
                        span.metadata = {}
                    span.metadata["token_extraction"] = "heuristic"

                return result
            except Exception as e:
                span.set_error(str(e))
                raise
            finally:
                if span.end_time is None:
                    tracer.end_span(span)

        return wrapper

    return decorator
