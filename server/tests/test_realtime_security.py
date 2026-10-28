"""Legacy WebSocket readers enforce the collector's real authentication boundary."""

import asyncio
from datetime import timedelta

import pytest
from app.api import realtime
from app.auth import create_access_token
from app.config import settings
from app.db import Base
from app.models.user import User
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.websockets import WebSocketDisconnect


@pytest.fixture
def websocket_client(tmp_path, monkeypatch):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'websocket.db').as_posix()}",
        poolclass=NullPool,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def setup():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as session:
            session.add(
                User(
                    username="socket-viewer", hashed_password="synthetic", role="viewer"
                )
            )
            await session.commit()

    asyncio.run(setup())
    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
    monkeypatch.setattr(settings, "CORS_ORIGINS", ["http://localhost:19404"])
    monkeypatch.setattr(realtime, "async_session_factory", factory, raising=False)
    app = FastAPI()
    app.include_router(realtime.router)
    with TestClient(app) as client:
        yield client
    assert all(not sockets for sockets in realtime.connections.values())
    asyncio.run(engine.dispose())


@pytest.mark.parametrize("route", ["/ws/traces", "/ws/metrics"])
@pytest.mark.parametrize(
    "credential", ["missing", "malformed", "expired", "unknown-user", "query-only"]
)
def test_unauthorized_websocket_is_rejected_before_subscription(
    websocket_client, route, credential
):
    headers = {"Origin": "http://localhost:19404"}
    if credential == "malformed":
        headers["Authorization"] = "Bearer malformed"
    elif credential == "expired":
        headers["Authorization"] = "Bearer " + create_access_token(
            {"sub": "socket-viewer"}, expires_delta=timedelta(seconds=-1)
        )
    elif credential == "unknown-user":
        headers["Authorization"] = "Bearer " + create_access_token(
            {"sub": "missing-user"}
        )
    elif credential == "query-only":
        route += "?token=synthetic-not-a-jwt"
    with pytest.raises(WebSocketDisconnect) as rejected:
        with websocket_client.websocket_connect(route, headers=headers):
            pytest.fail("Unauthorized socket was accepted")
    assert rejected.value.code == 1008


@pytest.mark.parametrize("route", ["/ws/traces", "/ws/metrics"])
def test_authenticated_socket_rejects_unconfigured_origin(websocket_client, route):
    token = create_access_token({"sub": "socket-viewer"})
    with pytest.raises(WebSocketDisconnect) as rejected:
        with websocket_client.websocket_connect(
            route,
            headers={
                "Authorization": "Bearer " + token,
                "Origin": "https://untrusted.invalid",
            },
        ):
            pytest.fail("Untrusted browser origin was accepted")
    assert rejected.value.code == 1008


@pytest.mark.parametrize("origin", [None, "http://localhost:19404"])
def test_authenticated_viewer_receives_real_broadcast(websocket_client, origin):
    headers = {
        "Authorization": "Bearer " + create_access_token({"sub": "socket-viewer"})
    }
    if origin is not None:
        headers["Origin"] = origin
    with websocket_client.websocket_connect("/ws/traces", headers=headers) as socket:
        websocket_client.portal.call(
            realtime.broadcast_trace, {"run_id": "synthetic-private-run"}
        )
        assert socket.receive_json()["data"]["run_id"] == "synthetic-private-run"


def test_offline_no_token_legacy_socket_still_works(websocket_client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_REQUIRED", False)
    with websocket_client.websocket_connect("/ws/metrics") as socket:
        socket.send_json({"action": "ping"})
        assert socket.receive_json() == {"type": "pong"}
