"""FastAPI instrumentor stub."""

from agenttrace.instrumentation.base import Instrumentor


class FastAPIInstrumentor(Instrumentor):
    """Stub instrumentor for FastAPI."""

    def instrument(self) -> None:
        raise NotImplementedError("FastAPI instrumentor not yet implemented")

    def uninstrument(self) -> None:
        pass

    def is_instrumented(self) -> bool:
        return False
