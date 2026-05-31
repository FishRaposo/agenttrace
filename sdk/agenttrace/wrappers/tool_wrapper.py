"""Tool call wrapper — automatically traces tool function calls."""

from __future__ import annotations

import functools
from typing import Any, Callable, Optional, TypeVar

from agenttrace.span import SpanType
from agenttrace.tracer import Tracer

F = TypeVar("F", bound=Callable[..., Any])


def trace_tool(
    tracer: Tracer,
    tool_name: Optional[str] = None,
) -> Callable[[F], F]:
    """Decorator that automatically traces tool function calls.

    Creates a span for each call, recording the function name, arguments,
    return value, latency, and any errors.

    Args:
        tracer: The Tracer instance to use for recording.
        tool_name: Override name for the tool. Defaults to the function name.

    Returns:
        A decorator function that wraps the target function.

    Example:
        >>> @trace_tool(tracer)
        ... def search_web(query: str) -> list:
        ...     return [{"title": "Result"}]
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            name = tool_name or func.__name__
            span = tracer.start_span(
                name=name,
                span_type=SpanType.TOOL_CALL,
                metadata={"function": func.__name__, "tool_name": name},
            )

            span.input_data = {"args": repr(args), "kwargs": repr(kwargs)}

            try:
                result = func(*args, **kwargs)
                span.end(output=result)
                if span.end_time is None:
                    tracer.end_span(span)
                return result
            except Exception as e:
                span.set_error(str(e))
                if span.end_time is None:
                    tracer.end_span(span)
                raise

        return wrapper  # type: ignore[return-value]

    return decorator
