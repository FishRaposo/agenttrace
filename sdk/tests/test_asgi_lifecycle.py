"""The root must enclose streamed bytes, disconnects and overlapping ASGI requests."""

import asyncio

import pytest
from agenttrace.instrumentation.fastapi import (
    AgentTraceASGIMiddleware,
    FastAPIInstrumentor,
)
from agenttrace.tracer import Tracer

from tests.test_concurrent_lifecycle import Recorder


@pytest.mark.parametrize(
    "kind,status",
    [
        ("stream", "completed"),
        ("error", "failed"),
        ("disconnect", "cancelled"),
        ("cancel", "cancelled"),
        ("exception", "failed"),
        ("empty-exception", "failed"),
    ],
)
def test_asgi_terminal_state_covers_entire_response(kind, status):  # noqa: C901
    tracer, recorder = Tracer(), Recorder()
    tracer.set_exporter(recorder)

    async def app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 503 if kind == "error" else 200,
                "headers": [],
            }
        )
        await send({"type": "http.response.body", "body": b"first", "more_body": True})
        assert recorder.runs[-1]["status"] == "running"
        await asyncio.sleep(0)
        if kind == "disconnect":
            await receive()
            return
        if kind == "cancel":
            raise asyncio.CancelledError()
        if kind == "exception":
            raise RuntimeError("stream failed")
        if kind == "empty-exception":
            raise RuntimeError()
        await send({"type": "http.response.body", "body": b"last"})

    middleware = AgentTraceASGIMiddleware(app, tracer=tracer)

    async def request():
        async def receive():
            return {"type": "http.disconnect"}

        async def send(message):
            if message["type"] == "http.response.start":
                assert b"x-run-id" in dict(message["headers"])

        try:
            await middleware(
                {
                    "type": "http",
                    "method": "GET",
                    "path": "/stream",
                    "headers": [(b"x-correlation-id", b"caller")],
                },
                receive,
                send,
            )
        except (asyncio.CancelledError, RuntimeError):
            if kind not in ("cancel", "exception", "empty-exception"):
                raise

    async def main():
        await asyncio.gather(request(), request())

    asyncio.run(main())
    finals = [run for run in recorder.runs if run["end_time"]]
    assert len(finals) == 2 and all(run["status"] == status for run in finals)
    assert all(run["correlation_id"] == "caller" for run in finals)
    expected_span = {
        "completed": "completed",
        "failed": "error",
        "cancelled": "cancelled",
    }[status]
    assert all(span["status"] == expected_span for span in recorder.spans)
    if status != "completed":
        assert all(span["error"] for span in recorder.spans)


def test_actual_asgi_2_4_stream_send_disconnect_is_cancelled():
    pytest.importorskip("starlette")
    from starlette.requests import ClientDisconnect
    from starlette.responses import StreamingResponse

    tracer, recorder = Tracer(), Recorder()
    tracer.set_exporter(recorder)

    async def content():
        yield b"first"
        yield b"last"

    async def app(scope, receive, send):
        await StreamingResponse(content())(scope, receive, send)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        if message["type"] == "http.response.body":
            raise OSError("connection closed by client")

    async def main():
        with pytest.raises(ClientDisconnect):
            await AgentTraceASGIMiddleware(app, tracer=tracer)(
                {
                    "type": "http",
                    "method": "GET",
                    "path": "/stream",
                    "headers": [],
                    "asgi": {"spec_version": "2.4"},
                },
                receive,
                send,
            )

    asyncio.run(main())
    assert recorder.runs[-1]["status"] == "cancelled"
    assert recorder.spans[-1]["status"] == "cancelled"
    assert recorder.spans[-1]["error"]


def test_actual_fastapi_streaming_overlap():
    fastapi = pytest.importorskip("fastapi")
    httpx = pytest.importorskip("httpx")
    from fastapi.responses import StreamingResponse

    tracer, recorder = Tracer(), Recorder()
    tracer.set_exporter(recorder)
    app = fastapi.FastAPI()
    instrumentor = FastAPIInstrumentor(tracer)
    instrumentor.instrument(app=app)

    @app.get("/stream")
    async def stream():
        async def content():
            yield b"first"
            await asyncio.sleep(0.001)
            yield b"last"

        return StreamingResponse(content())

    async def main():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as client:
            responses = await asyncio.gather(
                *(client.get("/stream") for _ in range(20))
            )
        assert all(response.text == "firstlast" for response in responses)
        assert len({response.headers["x-run-id"] for response in responses}) == 20

    try:
        asyncio.run(main())
        tracer.flush()
    finally:
        instrumentor.uninstrument()
        tracer.close()
    assert len([run for run in recorder.runs if run["status"] == "completed"]) == 20
