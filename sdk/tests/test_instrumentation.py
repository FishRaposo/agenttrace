from unittest.mock import AsyncMock, MagicMock

from agenttrace.instrumentation.fastapi import FastAPIInstrumentor
from agenttrace.instrumentation.llamaindex import LlamaIndexInstrumentor
from agenttrace.instrumentation.openai import OpenAIInstrumentor


def test_openai_instrumentor_lifecycle(tracer):
    instrumentor = OpenAIInstrumentor(tracer=tracer)
    assert not instrumentor.is_instrumented()

    # Mock completions classes to avoid actual import/connection requirements
    import sys

    mock_openai = MagicMock()
    mock_openai.resources.chat.completions.Completions.create = MagicMock()
    mock_openai.resources.chat.completions.AsyncCompletions.create = AsyncMock()
    sys.modules["openai"] = mock_openai

    try:
        instrumentor.instrument()
        assert instrumentor.is_instrumented()
        instrumentor.uninstrument()
        assert not instrumentor.is_instrumented()
    finally:
        del sys.modules["openai"]


class MockFastAPI:
    def __init__(self, *args, **kwargs):
        pass

    def add_middleware(self, middleware_class, **kwargs):
        pass


def test_fastapi_instrumentor_lifecycle(tracer):
    instrumentor = FastAPIInstrumentor(tracer=tracer)
    assert not instrumentor.is_instrumented()

    # Mock fastapi and starlette
    import sys

    mock_fastapi = MagicMock()
    mock_fastapi.FastAPI = MockFastAPI
    sys.modules["fastapi"] = mock_fastapi

    mock_starlette = MagicMock()
    sys.modules["starlette"] = mock_starlette
    sys.modules["starlette.middleware.base"] = MagicMock()
    sys.modules["starlette.requests"] = MagicMock()
    sys.modules["starlette.responses"] = MagicMock()

    try:
        instrumentor.instrument()
        assert instrumentor.is_instrumented()
        instrumentor.uninstrument()
        assert not instrumentor.is_instrumented()
    finally:
        del sys.modules["fastapi"]
        del sys.modules["starlette"]
        del sys.modules["starlette.middleware.base"]
        del sys.modules["starlette.requests"]
        del sys.modules["starlette.responses"]


def test_llamaindex_instrumentor_lifecycle(tracer):
    instrumentor = LlamaIndexInstrumentor(tracer=tracer)
    assert not instrumentor.is_instrumented()

    import sys

    mock_llama = MagicMock()
    mock_llama.core.Settings = MagicMock()
    mock_llama.core.callbacks.CallbackManager = MagicMock()
    sys.modules["llama_index"] = mock_llama
    sys.modules["llama_index.core"] = mock_llama.core
    sys.modules["llama_index.core.callbacks"] = mock_llama.core.callbacks

    try:
        instrumentor.instrument()
        assert instrumentor.is_instrumented()
        instrumentor.uninstrument()
        assert not instrumentor.is_instrumented()
    finally:
        del sys.modules["llama_index"]
        del sys.modules["llama_index.core"]
        del sys.modules["llama_index.core.callbacks"]
