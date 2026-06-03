"""Decision wrapper — automatically traces agent decision-making calls."""

from __future__ import annotations

import functools
from typing import Callable, Optional, ParamSpec, TypeVar

from agenttrace.span import SpanType
from agenttrace.tracer import Tracer

P = ParamSpec("P")
R = TypeVar("R")


def trace_decision(
    tracer: Tracer,
    decision_name: Optional[str] = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that automatically traces agent decision-making functions.

    Creates a span for each call, recording the decision context, chosen action,
    and any errors.

    Args:
        tracer: The Tracer instance to use for recording.
        decision_name: Override name for the decision. Defaults to the function name.

    Returns:
        A decorator function that wraps the target function.

    Example:
        >>> @trace_decision(tracer)
        ... def choose_action(state: dict) -> str:
        ...     return "call_search"
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            name = decision_name or func.__name__
            span = tracer.start_span(
                name=name,
                span_type=SpanType.DECISION,
                metadata={"function": func.__name__, "decision_name": name},
            )

            span.input_data = {"args": repr(args), "kwargs": repr(kwargs)}

            try:
                result = func(*args, **kwargs)
                span.end(output=result)
                return result
            except Exception as e:
                span.set_error(str(e))
                raise
            finally:
                if span.end_time is None:
                    tracer.end_span(span)

        return wrapper

    return decorator
