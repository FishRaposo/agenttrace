"""ASGI lifecycle instrumentation; optional FastAPI import remains lazy."""

from __future__ import annotations

import asyncio
from typing import Any

from agenttrace.instrumentation.base import Instrumentor
from agenttrace.span import SpanStatus
from agenttrace.tracer import RunStatus, Tracer


class AgentTraceASGIMiddleware:
    def __init__(self, app: Any, *, tracer: Tracer, instrumentor: Any = None) -> None:
        self.app, self.tracer, self.instrumentor = app, tracer, instrumentor

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:  # noqa: C901 - one lifecycle owns receive/send/finalization
        if scope["type"] != "http" or (
            self.instrumentor is not None and not self.instrumentor.is_instrumented()
        ):
            await self.app(scope, receive, send)
            return
        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        correlation = headers.get(b"x-correlation-id", b"").decode("latin1") or None
        context = self.tracer.start_run(
            f"http.{scope.get('method', 'GET').lower()}.{scope.get('path', '/')}",
            correlation_id=correlation,
        )
        run = context.__enter__()
        span = self.tracer.start_span(
            "http.request",
            metadata={
                "http.method": scope.get("method"),
                "http.path": scope.get("path"),
            },
        )
        status, disconnected, complete = 200, False, False
        terminal = RunStatus.COMPLETED
        diagnostic = None

        async def traced_receive():
            nonlocal disconnected
            message = await receive()
            if message["type"] == "http.disconnect":
                disconnected = True
            return message

        async def traced_send(message):
            nonlocal status, complete, disconnected
            if message["type"] == "http.response.start":
                status = message["status"]
                message = dict(message)
                output_headers = list(message.get("headers", []))
                output_headers.append((b"x-run-id", run.id.encode()))
                if correlation:
                    output_headers.append(
                        (b"x-correlation-id", correlation.encode("latin1"))
                    )
                message["headers"] = output_headers
            try:
                await send(message)
            except OSError:
                # ASGI 2.4 response helpers may wrap this as ClientDisconnect.
                disconnected = True
                raise
            if message["type"] == "http.response.body" and not message.get(
                "more_body", False
            ):
                complete = True

        try:
            await self.app(scope, traced_receive, traced_send)
            if disconnected and not complete:
                terminal, diagnostic = (
                    RunStatus.CANCELLED,
                    "Client disconnected before response completed",
                )
            elif status >= 400 or not complete:
                terminal, diagnostic = (
                    RunStatus.FAILED,
                    f"HTTP {status}"
                    if complete
                    else "Response stream did not complete",
                )
        except asyncio.CancelledError:
            terminal, diagnostic = RunStatus.CANCELLED, "Request cancelled"
            raise
        except BaseException as exc:
            if disconnected and not complete:
                terminal, diagnostic = (
                    RunStatus.CANCELLED,
                    "Client disconnected before response completed",
                )
            else:
                terminal, diagnostic = (
                    RunStatus.FAILED,
                    str(exc) or f"Request failed with {type(exc).__name__}",
                )
            raise
        finally:
            if terminal != RunStatus.COMPLETED:
                span.set_error(diagnostic or "Request did not complete")
                if terminal == RunStatus.CANCELLED:
                    span.status = SpanStatus.CANCELLED
            else:
                span.end()
            if span.metadata is not None:
                span.metadata["http.status_code"] = status
                span.metadata["response_complete"] = complete
            try:
                self.tracer.end_span(span)
            finally:
                self.tracer.end_run(terminal)


class FastAPIInstrumentor(Instrumentor):
    def __init__(self, tracer: Tracer | None = None) -> None:
        super().__init__()
        self.tracer = tracer or Tracer()
        self._original_init: Any = None
        self._apps: set[int] = set()

    def instrument(self, **kwargs: Any) -> None:
        try:
            import fastapi
        except ImportError as err:
            raise ImportError("fastapi or starlette not installed.") from err
        self._prepare_delivery(self.tracer)
        self._instrumented = True

        def attach(app):
            if id(app) not in self._apps:
                app.add_middleware(
                    AgentTraceASGIMiddleware, tracer=self.tracer, instrumentor=self
                )
                self._apps.add(id(app))

        app = kwargs.get("app")
        if app is not None:
            attach(app)
            return
        if self._original_init is None:
            self._original_init = fastapi.FastAPI.__init__
            original = self._original_init

            def patched_init(app, *args, **kwargs):
                original(app, *args, **kwargs)
                attach(app)

            fastapi.FastAPI.__init__ = patched_init

    def uninstrument(self) -> None:
        if self._original_init is not None:
            import fastapi

            fastapi.FastAPI.__init__ = self._original_init
            self._original_init = None
        self._instrumented = False

    def is_instrumented(self) -> bool:
        return self._instrumented
