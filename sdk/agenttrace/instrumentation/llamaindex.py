"""LlamaIndex instrumentor stub."""

from agenttrace.instrumentation.base import Instrumentor


class LlamaIndexInstrumentor(Instrumentor):
    """Stub instrumentor for LlamaIndex."""

    def instrument(self) -> None:
        raise NotImplementedError("LlamaIndex instrumentor not yet implemented")

    def uninstrument(self) -> None:
        pass

    def is_instrumented(self) -> bool:
        return False
