"""FastAPI request auto-instrumentation.

Interceptors incoming HTTP requests to create a run trace per request,
propagating trace headers in response.
"""

from __future__ import annotations

from typing import Any, Optional

from agenttrace.instrumentation.base import Instrumentor
from agenttrace import Tracer

try:
    import fastapi
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
except ImportError:
    BaseHTTPMiddleware = object


class FastAPIInstrumentor(Instrumentor):
    """Instruments FastAPI for automatic run tracing per request.

    Usage:
        instrumentor = FastAPIInstrumentor(tracer=tracer)
        # Class-level patch (for auto_instrument)
        instrumentor.instrument()
        
        # Or explicit app instrument
        instrumentor.instrument(app=app)
    """

    def __init__(self, tracer: Tracer | None = None) -> None:
        super().__init__()
        self.tracer = tracer or Tracer()
        self._original_init: Any = None

    def instrument(self, **kwargs: Any) -> None:
        """Instrument FastAPI.

        Args:
            **kwargs: Can include `app` to instrument a specific FastAPI instance.
        """
        try:
            import fastapi
            from starlette.middleware.base import BaseHTTPMiddleware
            from starlette.requests import Request
            from starlette.responses import Response
        except ImportError:
            raise ImportError("fastapi or starlette not installed.")

        tracer = self.tracer
        instrumentor_instance = self

        class AgentTraceMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next: Any) -> Response:
                if not instrumentor_instance.is_instrumented():
                    return await call_next(request)

                correlation_id = request.headers.get("x-correlation-id")
                run_name = f"http.{request.method.lower()}.{request.url.path}"

                with tracer.start_run(name=run_name, correlation_id=correlation_id) as run:
                    response = await call_next(request)
                    response.headers["x-run-id"] = run.id
                    if correlation_id:
                        response.headers["x-correlation-id"] = correlation_id
                    return response

        # Add to explicit app if provided
        app = kwargs.get("app")
        if app is not None:
            app.add_middleware(AgentTraceMiddleware)

        # Monkey-patch FastAPI.__init__ for future apps
        if self._original_init is None:
            self._original_init = fastapi.FastAPI.__init__
            
            def patched_init(self_: fastapi.FastAPI, *args: Any, **kwargs_: Any) -> None:
                self._original_init(self_, *args, **kwargs_)
                self_.add_middleware(AgentTraceMiddleware)

            fastapi.FastAPI.__init__ = patched_init

        self._instrumented = True

    def uninstrument(self) -> None:
        """Remove FastAPI instrumentation."""
        if self._original_init is not None:
            try:
                import fastapi
                fastapi.FastAPI.__init__ = self._original_init
            except ImportError:
                pass
            self._original_init = None
        self._instrumented = False

    def is_instrumented(self) -> bool:
        return self._instrumented
