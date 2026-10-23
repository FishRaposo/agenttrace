"""Base class for instrumentors."""

from abc import ABC, abstractmethod
from typing import Any


class Instrumentor(ABC):
    """Base class for framework instrumentors."""

    def __init__(self) -> None:
        """Initialize instrumentor."""
        self._instrumented = False

    @abstractmethod
    def instrument(self, **kwargs: Any) -> None:
        """Instrument the target framework.

        Args:
            **kwargs: Framework-specific options.
        """
        pass

    @abstractmethod
    def uninstrument(self) -> None:
        """Remove instrumentation."""
        pass

    def is_instrumented(self) -> bool:
        """Check if instrumentation is active."""
        return self._instrumented

    @staticmethod
    def _prepare_delivery(tracer) -> None:
        """Framework interception must not perform blocking inline network export."""
        from agenttrace.exporters.bounded import BoundedExporter

        exporter = tracer._exporter
        if exporter is not None and not isinstance(exporter, BoundedExporter):
            tracer.set_exporter(
                BoundedExporter(exporter, capture_content=tracer.capture_content)
            )
