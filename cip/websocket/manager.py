"""WebSocket connection manager for CIP."""
from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict, Dict, List

from fastapi import WebSocket


class ConnectionManager:
    """Manage WebSocket connections for participants, admins and facilitators."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: DefaultDict[str, Dict[str, WebSocket]] = defaultdict(dict)
        self.admin_connections: List[WebSocket] = []
        self.facilitator_connections: List[WebSocket] = []

    async def connect(self, user_id: str, websocket: WebSocket, audience: str = "participant") -> None:
        await websocket.accept()
        if audience == "admin":
            self.admin_connections.append(websocket)
        elif audience == "facilitator":
            self.facilitator_connections.append(websocket)
        else:
            self.active_connections[user_id] = websocket

    async def connect_session(self, session_id: str, participant_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        key = f"{session_id}:{participant_id}"
        self.active_connections[key] = websocket
        self.session_connections[session_id][participant_id] = websocket

    def disconnect(self, user_id: str, audience: str = "participant") -> None:
        if audience == "participant":
            self.active_connections.pop(user_id, None)
        # Admin/facilitator cleanup is handled defensively during broadcast.

    def disconnect_session(self, session_id: str, participant_id: str) -> None:
        key = f"{session_id}:{participant_id}"
        self.active_connections.pop(key, None)
        if session_id in self.session_connections:
            self.session_connections[session_id].pop(participant_id, None)
            if not self.session_connections[session_id]:
                self.session_connections.pop(session_id, None)

    async def send_to_user(self, user_id: str, message: dict) -> None:
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json(message)

    async def broadcast_session(self, session_id: str, message: dict) -> None:
        stale: list[str] = []
        for participant_id, ws in list(self.session_connections.get(session_id, {}).items()):
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(participant_id)
        for participant_id in stale:
            self.disconnect_session(session_id, participant_id)

    async def broadcast_participants(self, message: dict) -> None:
        stale: list[str] = []
        for key, ws in list(self.active_connections.items()):
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(key)
        for key in stale:
            self.active_connections.pop(key, None)

    async def broadcast_admin(self, message: dict) -> None:
        alive: list[WebSocket] = []
        for ws in self.admin_connections:
            try:
                await ws.send_json(message)
                alive.append(ws)
            except Exception:
                pass
        self.admin_connections = alive

    async def broadcast_facilitator(self, message: dict) -> None:
        alive: list[WebSocket] = []
        for ws in self.facilitator_connections:
            try:
                await ws.send_json(message)
                alive.append(ws)
            except Exception:
                pass
        self.facilitator_connections = alive
