"""Real-time WebSocket endpoints for trace streaming.

Provides live trace updates via WebSocket for real-time
observability dashboards.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.internal.realtime import RealtimePublisher, create_publisher

router = APIRouter()
publisher: RealtimePublisher = create_publisher(
    settings.REALTIME_BACKEND, settings.REDIS_URL
)

# Store active connections
connections: dict[str, list[WebSocket]] = {}


@router.websocket("/ws/traces")
async def traces_websocket(websocket: WebSocket) -> None:
    """WebSocket for real-time trace streaming.

    Clients connect here to receive live trace updates.
    """
    await websocket.accept()

    # Add to connections
    _client_id = str(id(websocket))
    if "traces" not in connections:
        connections["traces"] = []
    connections["traces"].append(websocket)

    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle subscription filters
            if message.get("action") == "subscribe":
                # Store subscription preferences
                await websocket.send_json(
                    {
                        "type": "ack",
                        "message": "Subscribed to traces",
                    }
                )

    except WebSocketDisconnect:
        # Remove from connections
        if websocket in connections.get("traces", []):
            connections["traces"].remove(websocket)


async def broadcast_trace(trace_data: dict[str, Any]) -> None:
    """Broadcast trace to all connected clients.

    Args:
        trace_data: Trace data to broadcast.
    """
    message = {
        "type": "trace",
        "timestamp": trace_data.get("timestamp"),
        "data": trace_data,
    }

    await publisher.publish("traces", message)

    disconnected = []
    for ws in connections.get("traces", []):
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)

    # Clean up disconnected clients
    for ws in disconnected:
        if ws in connections.get("traces", []):
            connections["traces"].remove(ws)


@router.websocket("/ws/metrics")
async def metrics_websocket(websocket: WebSocket) -> None:
    """WebSocket for real-time metrics streaming.

    Streams aggregated metrics (QPS, latency, cost) in real-time.
    """
    await websocket.accept()

    _client_id = str(id(websocket))
    if "metrics" not in connections:
        connections["metrics"] = []
    connections["metrics"].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # Handle ping/keepalive
            message = json.loads(data)
            if message.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        if websocket in connections.get("metrics", []):
            connections["metrics"].remove(websocket)


async def broadcast_metrics(metrics_data: dict[str, Any]) -> None:
    """Broadcast metrics to all connected clients.

    Args:
        metrics_data: Metrics data to broadcast.
    """
    message = {
        "type": "metrics",
        "timestamp": metrics_data.get("timestamp"),
        "data": metrics_data,
    }

    await publisher.publish("metrics", message)

    disconnected = []
    for ws in connections.get("metrics", []):
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)

    for ws in disconnected:
        if ws in connections.get("metrics", []):
            connections["metrics"].remove(ws)


async def close_all_connections() -> None:
    """Gracefully close all active WebSocket connections on shutdown."""
    for channel in list(connections.keys()):
        for ws in list(connections.get(channel, [])):
            try:
                await ws.send_json(
                    {"type": "shutdown", "message": "Server is shutting down"}
                )
                await ws.close()
            except Exception:
                pass
        connections[channel].clear()
    await publisher.close()
