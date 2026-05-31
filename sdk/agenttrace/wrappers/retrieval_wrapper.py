"""Retrieval wrapper — automatically traces retrieval operations."""

from __future__ import annotations

import functools
from typing import Any, Callable, Optional, TypeVar

from agenttrace.span import SpanType
from agenttrace.tracer import Tracer

F = TypeVar("F", bound=Callable[..., Any])


def trace_retrieval(
    tracer: Tracer,
    retriever_name: Optional[str] = None,
) -> Callable[[F], F]:
    """Decorator that automatically traces retrieval operations.

    Creates a span for each call, recording the query, retrieved documents,
    result count, and any errors.

    Args:
        tracer: The Tracer instance to use for recording.
        retriever_name: Override name for the retrieval. Defaults to the function name.

    Returns:
        A decorator function that wraps the target function.

    Example:
        >>> @trace_retrieval(tracer)
        ... def search_docs(query: str) -> list:
        ...     return [{"doc": "content"}]
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            name = retriever_name or func.__name__
            span = tracer.start_span(
                name=name,
                span_type=SpanType.RETRIEVAL,
                metadata={"function": func.__name__, "retriever_name": name},
            )

            span.input_data = {"args": repr(args), "kwargs": repr(kwargs)}

            try:
                result = func(*args, **kwargs)
                span.end(output=result)
            except Exception as e:
                span.set_error(str(e))
                raise
            finally:
                tracer.end_span(span)

            return result

        return wrapper  # type: ignore[return-value]

    return decorator
