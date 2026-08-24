"""WebSocket connection manager: per-run broadcast of graph events.

Each run has a pool of WebSocket connections (multiple tabs / reconnect).
The manager fan-outs JSON events to all connected clients for a run and
cleans up on disconnect.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket


class WebSocketManager:
    """Thread-safe WebSocket pool keyed by run_id."""

    def __init__(self) -> None:
        self._pools: dict[str, set[WebSocket]] = {}

    async def connect(self, run_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._pools.setdefault(run_id, set()).add(ws)

    def disconnect(self, run_id: str, ws: WebSocket) -> None:
        pool = self._pools.get(run_id)
        if pool:
            pool.discard(ws)
            if not pool:
                del self._pools[run_id]

    async def broadcast(self, run_id: str, event: dict[str, Any]) -> None:
        """Send a JSON event to every connected client for this run."""
        pool = self._pools.get(run_id)
        if not pool:
            return
        payload = json.dumps(event, default=str)
        stale: list[WebSocket] = []
        for ws in pool:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            pool.discard(ws)
        if pool and not pool:
            del self._pools[run_id]


# Singleton — used by both routers and the engine.
ws_manager = WebSocketManager()