"""Auto-instrumentation for popular frameworks.

Provides zero-code tracing for:
- LangChain
- LlamaIndex
- FastAPI
- OpenAI SDK
"""

from agenttrace.instrumentation.base import Instrumentor
from agenttrace.instrumentation.fastapi import FastAPIInstrumentor
from agenttrace.instrumentation.langchain import LangChainInstrumentor
from agenttrace.instrumentation.llamaindex import LlamaIndexInstrumentor
from agenttrace.instrumentation.openai import OpenAIInstrumentor


def auto_instrument(
    frameworks: list[str] | None = None,
    exclude: list[str] | None = None,
) -> dict[str, bool]:
    """Auto-instrument supported frameworks.

    Args:
        frameworks: List of frameworks to instrument. Auto-detect if None.
        exclude: List of frameworks to skip.

    Returns:
        Dict of {framework: success}.
    """
    results = {}
    exclude = exclude or []

    # Auto-detect if not specified
    if frameworks is None:
        frameworks = _detect_frameworks()

    instrumentors = {
        "langchain": LangChainInstrumentor,
        "llamaindex": LlamaIndexInstrumentor,
        "fastapi": FastAPIInstrumentor,
        "openai": OpenAIInstrumentor,
    }

    for name in frameworks:
        if name in exclude or name not in instrumentors:
            continue

        try:
            instrumentor = instrumentors[name]()
            instrumentor.instrument()
            results[name] = True
        except Exception:
            results[name] = False

    return results


def _detect_frameworks() -> list[str]:
    """Detect available frameworks."""
    detected = []

    try:
        import langchain  # noqa: F401  # availability probe

        detected.append("langchain")
    except ImportError:
        pass

    try:
        import llama_index  # noqa: F401  # availability probe

        detected.append("llamaindex")
    except ImportError:
        pass

    try:
        import fastapi  # noqa: F401  # availability probe

        detected.append("fastapi")
    except ImportError:
        pass

    try:
        import openai  # noqa: F401  # availability probe

        detected.append("openai")
    except ImportError:
        pass

    return detected


__all__ = [
    "Instrumentor",
    "LangChainInstrumentor",
    "LlamaIndexInstrumentor",
    "FastAPIInstrumentor",
    "OpenAIInstrumentor",
    "auto_instrument",
]
