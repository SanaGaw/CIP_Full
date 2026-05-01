"""WebSocket connection manager."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from fastapi import WebSocket


class ConnectionManager:
    """Manage WebSocket connections for participants, admin and facilitator."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: dict[str, dict[str, WebSocket]] = defaultdict(dict)
        self.admin_connections: List[WebSocket] = []
        self.facilitator_connections: List[WebSocket] = []

    async def connect(self, user_id: str, websocket: WebSocket, audience: str = "participant", session_id: str | None = None) -> None:
        await websocket.accept()
        if audience == "participant":
            self.active_connections[user_id] = websocket
            if session_id:
                self.session_connections[session_id][user_id] = websocket
        elif audience == "admin":
            self.admin_connections.append(websocket)
            self.active_connections[user_id] = websocket
        elif audience == "facilitator":
            self.facilitator_connections.append(websocket)
            self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str, audience: str = "participant", session_id: str | None = None) -> None:
        self.active_connections.pop(user_id, None)
        if session_id:
            self.session_connections.get(session_id, {}).pop(user_id, None)
        # stale role sockets are cleaned during broadcast failures

    async def send_to_user(self, user_id: str, message: dict) -> None:
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json(message)

    async def broadcast_participants(self, message: dict, session_id: str | None = None) -> None:
        if session_id:
            targets = list(self.session_connections.get(session_id, {}).items())
        else:
            targets = list(self.active_connections.items())
        stale: list[tuple[str, WebSocket]] = []
        for user_id, ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append((user_id, ws))
        for user_id, _ in stale:
            self.disconnect(user_id, session_id=session_id)

    async def broadcast_admin(self, message: dict) -> None:
        self.admin_connections = await self._broadcast_role(self.admin_connections, message)

    async def broadcast_facilitator(self, message: dict) -> None:
        self.facilitator_connections = await self._broadcast_role(self.facilitator_connections, message)

    async def _broadcast_role(self, sockets: List[WebSocket], message: dict) -> List[WebSocket]:
        alive: List[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(message)
                alive.append(ws)
            except Exception:
                pass
        return alive
